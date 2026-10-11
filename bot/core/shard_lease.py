import asyncio
import logging
import secrets
import signal
from bot.core.fencing import FenceContext


def resolve_shard_ids(configured_ids=None, configured_count=None, recommended_count=None):
    """Return the exact shard IDs this process must lease before connecting."""
    if configured_ids is not None:
        shard_ids = [int(shard_id) for shard_id in configured_ids]
        if not shard_ids or any(shard_id < 0 for shard_id in shard_ids):
            raise ValueError("SHARD_IDS must contain non-negative shard IDs")
        if len(set(shard_ids)) != len(shard_ids):
            raise ValueError("SHARD_IDS must not contain duplicates")
        return shard_ids

    count = configured_count if configured_count is not None else recommended_count
    if count is None:
        count = 1
    count = int(count)
    if count < 1:
        raise ValueError("Shard count must be at least 1")
    return list(range(count))


log = logging.getLogger('bot.shard_lease')


class ShardLeaseManager:
    """Redis shard ownership with monotonically increasing fencing epochs.

    Every lease acquisition advances a Redis-side epoch. Workers carry that
    epoch with the event they process; stale epochs are rejected before and
    during durable/cache writes. Losing a lease also fail-closes the process.
    """
    def __init__(self, cache, owner, ttl_ms=60000):
        self.cache, self.owner, self.ttl_ms = cache, owner, ttl_ms
        self.keys = []
        self.task = None
        self.healthy = True
        self.token = secrets.token_urlsafe(32)
        self.fences: dict[int, int] = {}

    async def acquire(self, shard_ids):
        self.healthy = True
        self.token = secrets.token_urlsafe(32)
        self.keys = [f'shard-lease:{i}' for i in shard_ids]
        self.fences = {}
        acquired = []
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
            self.keys = []
            self.fences = {}
            raise
        self.task = asyncio.create_task(self._renew(), name='shard-lease-renewer')
        self._register_signal_handlers()

    def _register_signal_handlers(self):
        """Register SIGTERM and SIGINT handlers to gracefully release leases on container termination."""
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
        except (NotImplementedError, RuntimeError):
            # Signals might not be supported on certain loops/platforms (e.g. Windows)
            pass

    async def _handle_signal(self, sig):
        log.warning(f"Received shutdown signal {sig.name}. Releasing shard leases immediately...")
        try:
            await self.release()
        except Exception as e:
            log.error(f"Error releasing shard leases during signal handling: {e}")

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
        interval = max(1.0, self.ttl_ms / 3000)
        try:
            while True:
                await asyncio.sleep(interval)
                for shard_id, fence in list(self.fences.items()):
                    key = f'shard-lease:{shard_id}'
                    if not await self.cache.renew_fenced_lock(key, self.token, fence, self.ttl_ms):
                        self.healthy = False
                        log.critical('lost shard lease shard=%s fence=%s; entering fail-closed mode', shard_id, fence)
                        asyncio.create_task(self._terminate_bot(), name='lost-shard-lease-shutdown')
                        return
        except asyncio.CancelledError:
            raise
        except Exception:
            # A failed renewal is indistinguishable from lost ownership. Never
            # keep processing events after the lease-renewer has failed.
            self.healthy = False
            log.exception(
                'shard lease renewal failed; entering fail-closed shutdown owner=%s',
                self.owner,
            )
            await self._terminate_bot()

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
        self.healthy = False
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
        for shard_id, fence in list(self.fences.items()):
            await self.cache.release_fenced_lock(f'shard-lease:{shard_id}', self.token, fence)
        self.keys = []
        self.fences = {}
        self.token = secrets.token_urlsafe(32)
