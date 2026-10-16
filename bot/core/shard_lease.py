import asyncio
import logging
import secrets
import signal

from bot.core.fencing import FenceContext

log = logging.getLogger("bot.shard_lease")


def resolve_shard_ids(
    configured_ids=None,
    configured_count=None,
    recommended_count=None,
):
    """Return the exact shard IDs this process must lease."""
    if configured_ids is not None:
        shard_ids = [int(value) for value in configured_ids]

        if not shard_ids or any(value < 0 for value in shard_ids):
            raise ValueError(
                "SHARD_IDS must contain non-negative shard IDs"
            )

        if len(set(shard_ids)) != len(shard_ids):
            raise ValueError("SHARD_IDS must not contain duplicates")

        known_count = (
            configured_count
            if configured_count is not None
            else recommended_count
        )

        if known_count is not None:
            known_count = int(known_count)
            if known_count < 1:
                raise ValueError("Shard count must be at least 1")
            if any(value >= known_count for value in shard_ids):
                raise ValueError(
                    "SHARD_IDS entries must be smaller than SHARD_COUNT"
                )

        return shard_ids

    count = (
        configured_count
        if configured_count is not None
        else recommended_count
    )

    if count is None:
        count = 1

    count = int(count)
    if count < 1:
        raise ValueError("Shard count must be at least 1")

    return list(range(count))


class ShardLeaseManager:
    """Manage Redis shard leases with fencing tokens."""

    def __init__(self, cache, owner, ttl_ms=60000):
        if int(ttl_ms) < 3000:
            raise ValueError("Shard lease TTL must be at least 3000 ms")

        self.cache = cache
        self.owner = owner
        self.ttl_ms = int(ttl_ms)
        self.keys = []
        self.task = None
        self.healthy = False
        self.token = secrets.token_urlsafe(32)
        self.fences: dict[int, int] = {}
        self._acquiring = False
        self._shutdown_lock = asyncio.Lock()
        self._signal_handlers_registered = False

    async def acquire(self, shard_ids):
        if self._acquiring or self.fences or self.task is not None:
            raise RuntimeError("Shard lease manager is already active")

        shard_ids = [int(value) for value in shard_ids]

        if not shard_ids or any(value < 0 for value in shard_ids):
            raise ValueError("Shard IDs must be non-negative and non-empty")

        if len(set(shard_ids)) != len(shard_ids):
            raise ValueError("Shard IDs must not contain duplicates")

        self._acquiring = True
        self.token = secrets.token_urlsafe(32)
        acquired = []

        try:
            for shard_id in shard_ids:
                key = f"shard-lease:{shard_id}"

                fence = await self.cache.acquire_fenced_lock(
                    key,
                    self.token,
                    f"shard-fence:{shard_id}",
                    self.ttl_ms,
                )

                if not fence:
                    raise RuntimeError(
                        f"Shard lease unavailable: {key}. "
                        "Another owner may be active, or its lease "
                        "has not expired. Refusing unsafe takeover."
                    )

                fence = int(fence)
                acquired.append((shard_id, key, fence))

            self.fences = {
                shard_id: fence
                for shard_id, _, fence in acquired
            }
            self.keys = [key for _, key, _ in acquired]
            self.healthy = True

            self.task = asyncio.create_task(
                self._renew(),
                name="shard-lease-renewer",
            )

            self._register_signal_handlers()

        except BaseException:
            self.healthy = False

            if self.task is not None:
                self.task.cancel()
                await asyncio.gather(
                    self.task,
                    return_exceptions=True,
                )
                self.task = None

            # Attempt every release, even if one fails.
            for _, key, fence in reversed(acquired):
                try:
                    await self.cache.release_fenced_lock(
                        key, self.token, fence
                    )
                except Exception:
                    log.exception(
                        "Lease cleanup failed for %s; "
                        "the lease must expire naturally if necessary",
                        key,
                    )

            self.keys = []
            self.fences = {}
            raise

        finally:
            self._acquiring = False

    def _register_signal_handlers(self):
        if self._signal_handlers_registered:
            return

        try:
            loop = asyncio.get_running_loop()

            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(
                        self._handle_signal(s)
                    ),
                )

            self._signal_handlers_registered = True

        except (NotImplementedError, RuntimeError):
            log.debug("Signal handlers unavailable on this event loop")

    async def _handle_signal(self, sig):
        log.warning(
            "Received %s; shutting down the bot and releasing leases",
            sig.name,
        )

        callback = getattr(
            self.cache, "_bot_close_callback", None
        )

        try:
            if callback is not None:
                await callback()
            else:
                await self.release()
        except Exception:
            log.exception("Graceful shutdown failed for %s", sig.name)

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
            f"shard-lease:{shard_id}",
            self.token,
            fence,
        )

    async def _renew(self):
        interval = max(1.0, self.ttl_ms / 3000)

        try:
            while True:
                await asyncio.sleep(interval)

                for shard_id, fence in list(self.fences.items()):
                    key = f"shard-lease:{shard_id}"

                    renewed = await self.cache.renew_fenced_lock(
                        key,
                        self.token,
                        fence,
                        self.ttl_ms,
                    )

                    if not renewed:
                        self.healthy = False
                        log.critical(
                            "Lost shard lease shard=%s fence=%s; "
                            "stopping the bot",
                            shard_id,
                            fence,
                        )
                        await self._terminate_bot()
                        return

        except asyncio.CancelledError:
            raise

        except Exception:
            self.healthy = False
            log.exception(
                "Shard lease renewal failed; stopping bot owner=%s",
                self.owner,
            )
            await self._terminate_bot()

    async def _terminate_bot(self):
        self.healthy = False

        try:
            await self.cache.publish(
                "shard-lease-lost",
                {"owner": self.owner},
            )
        except Exception:
            log.exception("Could not publish shard lease loss")

        callback = getattr(
            self.cache, "_bot_close_callback", None
        )

        if callback is not None:
            await callback()

    def bind_shutdown(self, callback):
        self.cache._bot_close_callback = callback

    async def release(self):
        async with self._shutdown_lock:
            self.healthy = False

            current_task = asyncio.current_task()

            if self.task is not None:
                task = self.task
                self.task = None

                if task is not current_task:
                    task.cancel()
                    await asyncio.gather(
                        task,
                        return_exceptions=True,
                    )

            fences = list(self.fences.items())
            self.fences = {}
            self.keys = []

            for shard_id, fence in fences:
                try:
                    released = await self.cache.release_fenced_lock(
                        f"shard-lease:{shard_id}",
                        self.token,
                        fence,
                    )

                    if not released:
                        log.warning(
                            "Lease was not released because ownership "
                            "could not be confirmed: shard=%s",
                            shard_id,
                        )

                except Exception:
                    log.exception(
                        "Failed to release shard lease shard=%s; "
                        "Redis TTL will provide eventual expiry",
                        shard_id,
                    )

            self.token = secrets.token_urlsafe(32)
