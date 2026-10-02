import asyncio
import random
import secrets


class DistributedSingleFlight:
    """Cross-pod cache-miss coalescing using Redis fencing + completion signals.

    A local lock collapses callers inside one process. A Redis lease collapses
    callers across pods. The lease carries a monotonically increasing flight
    epoch so a delayed owner cannot publish a stale result after ownership has
    moved on. Completion notifications let remote waiters wake immediately;
    bounded jitter prevents synchronized retry bursts when Redis Pub/Sub is
    unavailable.
    """
    def __init__(self, cache, ttl_ms=30000, wait_seconds=35):
        self.cache = cache
        self.ttl_ms = max(5000, ttl_ms)
        self.wait_seconds = max(1.0, wait_seconds)
        self._local: dict[str, tuple[asyncio.Lock, int]] = {}
        self._guard = asyncio.Lock()

    async def _acquire_local(self, key):
        async with self._guard:
            entry = self._local.get(key)
            if entry is None:
                lock, refs = asyncio.Lock(), 0
            else:
                lock, refs = entry
            self._local[key] = (lock, refs + 1)
            return lock

    async def _release_local(self, key):
        async with self._guard:
            entry = self._local.get(key)
            if entry is None:
                return
            lock, refs = entry
            refs -= 1
            if refs <= 0 and not lock.locked():
                self._local.pop(key, None)
            else:
                self._local[key] = (lock, refs)

    async def run(self, key, loader, read_cache):
        local = await self._acquire_local(key)
        try:
            async with local:
                value = await read_cache()
                if value is not None:
                    return value

                token = secrets.token_urlsafe(24)
                lock_key = f'lock:{key}'
                fence_key = f'{lock_key}:epoch'
                notify_channel = f'{lock_key}:done'
                deadline = asyncio.get_running_loop().time() + self.wait_seconds
                backoff = 0.025

                while True:
                    if hasattr(self.cache, 'acquire_fenced_lock'):
                        flight_epoch = await self.cache.acquire_fenced_lock(
                            lock_key, token, fence_key, self.ttl_ms
                        )
                    else:
                        flight_epoch = 1 if await self.cache.acquire_lock(lock_key, token, self.ttl_ms) else 0
                    if flight_epoch:
                        renewer = asyncio.create_task(
                            self._renew(lock_key, token, flight_epoch),
                            name=f'cache-lock-renewer:{key}',
                        )
                        try:
                            # Recheck after winning the distributed lock.
                            value = await read_cache()
                            if value is not None:
                                return value
                            value = await loader()
                            # The cache adapter rejects this write if the flight
                            # epoch is no longer current.
                            if hasattr(self.cache, 'set_json_flight_fenced'):
                                await self.cache.set_json_flight_fenced(
                                    key, value, lock_key, token, flight_epoch, ttl=300
                                )
                            else:
                                await self.cache.set_json(key, value)
                            if hasattr(self.cache, 'publish'):
                                await self.cache.publish(
                                    notify_channel,
                                    {'key': key, 'epoch': flight_epoch},
                                )
                            return value
                        finally:
                            renewer.cancel()
                            await asyncio.gather(renewer, return_exceptions=True)
                            if hasattr(self.cache, 'release_fenced_lock'):
                                await self.cache.release_fenced_lock(lock_key, token, flight_epoch)
                            else:
                                await self.cache.release_lock(lock_key, token)

                    value = await read_cache()
                    if value is not None:
                        return value
                    if asyncio.get_running_loop().time() >= deadline:
                        # Never bypass the distributed lock on timeout: that
                        # would recreate the stampede this class prevents.
                        deadline = asyncio.get_running_loop().time() + self.wait_seconds

                    # Pub/Sub is an acceleration path, not a correctness
                    # dependency. If a subscriber cannot be created, the
                    # jittered polling fallback remains bounded and safe.
                    try:
                        await self._wait_for_completion(notify_channel, backoff)
                    except Exception:
                        await asyncio.sleep(backoff + random.random() * backoff)
                    backoff = min(0.5, backoff * 1.7)
        finally:
            await self._release_local(key)

    async def _wait_for_completion(self, channel, timeout):
        if not hasattr(self.cache, 'pubsub'):
            await asyncio.sleep(timeout + random.random() * timeout)
            return
        async with self.cache.pubsub() as ps:
            await ps.subscribe(channel)
            async def listen_once():
                async for msg in ps.listen():
                    if msg.get('type') == 'message':
                        return
            try:
                await asyncio.wait_for(listen_once(), timeout=timeout)
            finally:
                try:
                    await asyncio.wait_for(ps.unsubscribe(channel), timeout=0.25)
                except Exception:
                    pass

    async def _renew(self, key, token, fence):
        interval = max(1.0, self.ttl_ms / 3000)
        try:
            while True:
                await asyncio.sleep(interval)
                if hasattr(self.cache, 'renew_fenced_lock'):
                    current = await self.cache.renew_fenced_lock(key, token, fence, self.ttl_ms)
                else:
                    current = await self.cache.renew_lock(key, token, self.ttl_ms)
                if not current:
                    return
        except asyncio.CancelledError:
            raise
