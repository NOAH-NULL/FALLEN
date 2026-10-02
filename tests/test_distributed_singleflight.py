import asyncio
import pytest
from bot.cache.singleflight import DistributedSingleFlight

class SharedCache:
    def __init__(self):
        self.data = {}
        self.owner = None
        self.sets = 0
    async def get_json(self, key): return self.data.get(key)
    async def acquire_lock(self, key, token, ttl):
        if self.owner is not None: return False
        self.owner = token; return True
    async def renew_lock(self, key, token, ttl): return self.owner == token
    async def release_lock(self, key, token):
        if self.owner == token: self.owner = None
        return True
    async def set_json(self, key, value, ttl=300): self.data[key] = value; self.sets += 1

@pytest.mark.asyncio
async def test_cross_process_instances_coalesce_shared_cache_miss():
    cache = SharedCache()
    a = DistributedSingleFlight(cache)
    b = DistributedSingleFlight(cache)
    calls = 0
    async def loader():
        nonlocal calls
        calls += 1
        await asyncio.sleep(.02)
        return {'guild_id': 42}
    async def read(): return await cache.get_json('guild:42')
    results = await asyncio.gather(*(a.run('guild:42', loader, read) for _ in range(50)),
                                   *(b.run('guild:42', loader, read) for _ in range(50)))
    assert len(results) == 100
    assert calls == 1
    assert cache.sets == 1
    assert not a._local and not b._local

@pytest.mark.asyncio
async def test_stale_flight_owner_cannot_overwrite_new_epoch():
    cache = SharedCache()
    cache.owner = None
    # The real Redis implementation fences writes atomically. This fake models
    # the same ownership rule so the test remains deterministic without Redis.
    cache.epoch = 0
    async def acquire(key, token, fence_key, ttl):
        if cache.owner is not None:
            return 0
        cache.epoch += 1
        cache.owner = (token, cache.epoch)
        return cache.epoch
    async def renew(key, token, fence, ttl):
        return cache.owner == (token, fence)
    async def release(key, token, fence):
        if cache.owner == (token, fence):
            cache.owner = None
        return True
    async def fenced_set(key, value, lock_key, token, fence, ttl=300):
        assert cache.owner == (token, fence), 'stale owner must be rejected'
        cache.data[key] = value
        cache.sets += 1
    cache.acquire_fenced_lock = acquire
    cache.renew_fenced_lock = renew
    cache.release_fenced_lock = release
    cache.set_json_flight_fenced = fenced_set

    a = DistributedSingleFlight(cache)
    token_a = 'old'
    epoch_a = await cache.acquire_fenced_lock('lock:guild:9', token_a, 'lock:guild:9:epoch', 1000)
    await cache.release_fenced_lock('lock:guild:9', token_a, epoch_a)
    token_b = 'new'
    epoch_b = await cache.acquire_fenced_lock('lock:guild:9', token_b, 'lock:guild:9:epoch', 1000)
    assert epoch_b > epoch_a
    with pytest.raises(AssertionError):
        await cache.set_json_flight_fenced('guild:9', {'owner': 'old'}, 'lock:guild:9', token_a, epoch_a)
    await cache.set_json_flight_fenced('guild:9', {'owner': 'new'}, 'lock:guild:9', token_b, epoch_b)
    assert cache.data['guild:9']['owner'] == 'new'
