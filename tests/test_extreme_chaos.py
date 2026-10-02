import asyncio

import pytest

from bot.core.event_queue import GatewayEventQueue
from bot.core.health import start_health_server
from bot.core.shard_lease import ShardLeaseManager


class LeaseCache:
    def __init__(self):
        self.leases = {}
        self.counters = {}

    async def acquire_fenced_lock(self, key, token, fence_key, ttl):
        if key in self.leases:
            return 0
        self.counters[fence_key] = self.counters.get(fence_key, 0) + 1
        fence = self.counters[fence_key]
        self.leases[key] = (token, fence)
        return fence

    async def renew_fenced_lock(self, key, token, fence, ttl):
        return self.leases.get(key) == (token, fence)

    async def release_fenced_lock(self, key, token, fence):
        if self.leases.get(key) == (token, fence):
            self.leases.pop(key)
            return True
        return False

    async def fenced_lock_is_current(self, key, token, fence):
        return self.leases.get(key) == (token, fence)

    async def publish(self, *_args):
        return 1


@pytest.mark.asyncio
async def test_lease_loss_fails_closed_and_invalidates_fence():
    cache = LeaseCache()
    manager = ShardLeaseManager(cache, "a", 1000)
    await manager.acquire([0])
    fence = manager.fences[0]
    cache.leases.pop("shard-lease:0")
    assert not await manager.validate_fence(0, fence)
    manager.healthy = False
    await manager.release()


@pytest.mark.asyncio
async def test_queue_sheds_normal_but_preserves_critical_reserve():
    queue = GatewayEventQueue(maxsize=8, critical_maxsize=2)
    accepted_normal = sum(queue.put_nowait("normal", i) for i in range(20))
    accepted_critical = sum(queue.put_nowait("critical", i, critical=True) for i in range(20))
    assert accepted_normal == 6
    assert accepted_critical == 2
    assert queue.dropped > 0
    assert queue.dropped_critical > 0


class _DB:
    async def health(self):
        return False


class _Redis:
    async def health(self):
        return False


class _Bot:
    db = _DB()
    cache = _Redis()
    shard_leases = type("Lease", (), {"healthy": True})()

    def is_ready(self):
        return True


@pytest.mark.asyncio
async def test_liveness_stays_up_when_dependencies_are_down(unused_tcp_port):
    runner = await start_health_server(_Bot(), "127.0.0.1", unused_tcp_port)
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{unused_tcp_port}/healthz") as response:
                assert response.status == 200
            async with session.get(f"http://127.0.0.1:{unused_tcp_port}/readyz") as response:
                assert response.status == 503
    finally:
        await runner.cleanup()
