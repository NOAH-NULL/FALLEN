import asyncio
import logging
import secrets
from bot.core.fencing import FenceContext

log = logging.getLogger('bot.shard_lease')


class ShardLeaseManager:
    """Redis shard ownership with monotonically increasing fencing epochs.

    Every lease acquisition advances a Redis-side epoch. Workers carry that
    epoch with the event they process; stale epochs are rejected before and
    during durable/cache writes. Losing a lease also fail-closes the process.
    """
    def __init__(self, cache, owner, ttl_ms=60000):
        self.cache, self.owner, self.ttl_ms = cache, owner, ttl_ms
        self.keys=[]; self.task=None; self.healthy=True; self.token=secrets.token_urlsafe(32)
        self.fences: dict[int, int] = {}

    async def acquire(self, shard_ids):
        self.healthy = True
        self.token = secrets.token_urlsafe(32)
        self.keys=[f'shard-lease:{i}' for i in shard_ids]
        self.fences={}
        acquired=[]
        try:
            for shard_id, key in zip(shard_ids, self.keys):
                fence = await self.cache.acquire_fenced_lock(
                    key, self.token, f'shard-fence:{shard_id}', self.ttl_ms
                )
                if not fence:
                    raise RuntimeError(f'shard already leased: {key}')
                self.fences[int(shard_id)] = fence
                acquired.append((key, fence))
        except Exception:
            for key, fence in acquired:
                await self.cache.release_fenced_lock(key, self.token, fence)
            self.keys=[]; self.fences={}
            raise
        self.task=asyncio.create_task(self._renew(), name='shard-lease-renewer')

    def context_for(self, shard_id: int) -> FenceContext | None:
        fence = self.fences.get(int(shard_id))
        if not self.healthy or fence is None:
            return None
        return FenceContext(int(shard_id), fence, self.token)

    async def validate_fence(self, shard_id: int, fence: int) -> bool:
        ctx = self.context_for(shard_id)
        if ctx is None or ctx.fence != fence:
            return False
        return await self.cache.fenced_lock_is_current(
            f'shard-lease:{shard_id}', self.token, fence
        )

    async def _renew(self):
        interval=max(1.0, self.ttl_ms/3000)
        try:
            while True:
                await asyncio.sleep(interval)
                for shard_id, fence in list(self.fences.items()):
                    key=f'shard-lease:{shard_id}'
                    if not await self.cache.renew_fenced_lock(key, self.token, fence, self.ttl_ms):
                        self.healthy=False
                        log.critical('lost shard lease shard=%s fence=%s; entering fail-closed mode', shard_id, fence)
                        asyncio.create_task(self._terminate_bot(), name='lost-shard-lease-shutdown')
                        return
        except asyncio.CancelledError:
            raise

    async def _terminate_bot(self):
        try:
            await self.cache.publish('shard-lease-lost', {'owner': self.owner})
        finally:
            close = getattr(self.cache, '_bot_close_callback', None)
            if close:
                await close()

    def bind_shutdown(self, callback):
        self.cache._bot_close_callback = callback

    async def release(self):
        self.healthy=False
        if self.task:
            self.task.cancel(); await asyncio.gather(self.task, return_exceptions=True); self.task=None
        for shard_id, fence in list(self.fences.items()):
            await self.cache.release_fenced_lock(f'shard-lease:{shard_id}', self.token, fence)
        self.keys=[]; self.fences={}
        self.token = secrets.token_urlsafe(32)
