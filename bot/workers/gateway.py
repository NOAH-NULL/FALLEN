import asyncio
import logging
import time
from collections import deque
from bot.core.event_queue import GatewayEventQueue
from bot.core.fencing import push_fence, pop_fence, current_fence
from bot.core.metrics import EVENTS

log = logging.getLogger('bot.gateway_worker')


class GatewayDeadLetterQueue:
    """Bounded local DLQ; Redis stream persistence is best-effort."""
    def __init__(self, bot, maxsize: int = 2048, redis_stream: str = 'gateway-dlq'):
        self.bot = bot
        self.maxsize = max(1, maxsize)
        self.redis_stream = redis_stream
        self.items = deque(maxlen=self.maxsize)
        self.dropped = 0

    async def put(self, event, error):
        if len(self.items) >= self.maxsize:
            self.dropped += 1
        self.items.append({
            'kind': event.kind,
            'guild_id': getattr(getattr(event.payload, 'guild', None), 'id', None),
            'error': type(error).__name__,
            'message': str(error)[:500],
            'queued_at': event.enqueued_at,
            'failed_at': time.time(),
        })
        try:
            await self.bot.cache.xadd(self.redis_stream, {
                'kind': event.kind,
                'guild_id': str(getattr(getattr(event.payload, 'guild', None), 'id', '') or ''),
                'error': type(error).__name__,
                'message': str(error)[:500],
                'failed_at': str(time.time()),
            }, maxlen=self.maxsize)
        except Exception:
            log.exception('failed to persist gateway DLQ item')
        EVENTS.labels('gateway_dlq').inc()


class GatewayWorkerPool:
    """Bounded workers with guild serialization, fencing, supervision and DLQ."""
    def __init__(self, bot, queue: GatewayEventQueue, workers: int = 8,
                 guild_concurrency: int = 1, max_event_age: float = 10.0,
                 dlq_maxsize: int = 2048):
        self.bot, self.queue = bot, queue
        self.workers = max(1, workers)
        self.guild_concurrency = max(1, guild_concurrency)
        self.max_event_age = max(0.5, max_event_age)
        self.tasks: list[asyncio.Task] = []
        self._supervisor: asyncio.Task | None = None
        self._closing = False
        self.dlq = GatewayDeadLetterQueue(bot, dlq_maxsize)
        self._guild_locks = [asyncio.Semaphore(self.guild_concurrency) for _ in range(256)]

    async def start(self):
        self._closing = False
        self.tasks = [self._spawn(i) for i in range(self.workers)]
        self._supervisor = asyncio.create_task(self._supervise(), name='gateway-worker-supervisor')

    def _spawn(self, index: int) -> asyncio.Task:
        return asyncio.create_task(self._run(index), name=f'gateway-worker-{index}')

    @staticmethod
    def _guild_id(event) -> int | None:
        payload = event.payload
        guild = getattr(payload, 'guild', None)
        return getattr(guild, 'id', None)

    @staticmethod
    def _shard_id(event) -> int | None:
        payload = event.payload
        guild = getattr(payload, 'guild', None)
        return getattr(guild, 'shard_id', None)

    async def _dispatch(self, event):
        if event.kind == 'member_join':
            await self.bot.process_member_join(event.payload)
        elif event.kind == 'member_remove':
            await self.bot.process_member_remove(event.payload)
        elif event.kind == 'message':
            await self.bot.process_message(event.payload)
        else:
            raise ValueError(f'unknown gateway event kind: {event.kind}')

    async def _run(self, index: int):
        while True:
            event = await self.queue.get()
            fence_token = None
            try:
                now = asyncio.get_running_loop().time()
                if not event.critical and self.max_event_age > 0 and (now - event.enqueued_at) > self.max_event_age:
                    log.warning('dropping stale gateway event age=%.2fs kind=%s', now - event.enqueued_at, event.kind)
                    continue
                guild_id = self._guild_id(event)
                shard_id = self._shard_id(event)
                if guild_id is not None:
                    lease_mgr = self.bot.shard_leases
                    if hasattr(lease_mgr, 'context_for'):
                        if shard_id is None:
                            shard_count = max(1, getattr(self.bot, 'shard_count', 1) or 1)
                            shard_id = guild_id % shard_count
                        ctx = lease_mgr.context_for(shard_id)
                        if ctx is None or not await lease_mgr.validate_fence(shard_id, ctx.fence):
                            log.warning('rejecting gateway event with stale/missing fence guild=%s shard=%s', guild_id, shard_id)
                            continue
                        fence_token = push_fence(ctx)
                        async with self._guild_locks[guild_id % len(self._guild_locks)]:
                            if not await lease_mgr.validate_fence(shard_id, ctx.fence):
                                continue
                            await self._dispatch(event)
                            if not await lease_mgr.validate_fence(shard_id, ctx.fence):
                                raise RuntimeError(f'shard fence lost during event shard={shard_id}')
                    else:
                        if not getattr(lease_mgr, 'healthy', False):
                            continue
                        async with self._guild_locks[guild_id % len(self._guild_locks)]:
                            await self._dispatch(event)
                else:
                    await self._dispatch(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception('gateway worker event failed kind=%s; moved to DLQ', event.kind)
                await self.dlq.put(event, exc)
            finally:
                if fence_token is not None:
                    pop_fence(fence_token)
                self.queue.task_done(event)

    async def _supervise(self):
        while not self._closing:
            await asyncio.sleep(1)
            for i, task in enumerate(list(self.tasks)):
                if task.done() and not self._closing:
                    exc = task.exception() if not task.cancelled() else None
                    if exc:
                        log.error('gateway worker %d exited unexpectedly; restarting: %r', i, exc)
                    else:
                        log.warning('gateway worker %d exited unexpectedly; restarting', i)
                    self.tasks[i] = self._spawn(i)

    async def close(self, drain_timeout: float = 15.0):
        self._closing = True
        self.queue.stop_accepting()
        drained = await self.queue.drain(drain_timeout)
        if not drained:
            log.error('gateway queue did not drain within %.1fs; cancelling workers with %d pending events', drain_timeout, self.queue.qsize)
        if self._supervisor:
            self._supervisor.cancel()
            await asyncio.gather(self._supervisor, return_exceptions=True)
            self._supervisor = None
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        return drained
