import pytest

from bot.cache.rate_limit import DistributedRateLimiter


class Fake:
    def __init__(self):
        self.n = {}
        self.keys = []

    async def eval(self, script, numkeys, key, ttl):
        # Simulate the atomic INCR/EXPIRE Lua operation for unit tests.
        self.keys.append(key)
        self.n[key] = self.n.get(key, 0) + 1
        return self.n[key]


class R:
    def __init__(self):
        self.client = Fake()


@pytest.mark.asyncio
async def test_limit():
    lim = DistributedRateLimiter(R())
    assert await lim.allow("x", 2, 60)
    assert await lim.allow("x", 2, 60)
    assert not await lim.allow("x", 2, 60)


@pytest.mark.asyncio
async def test_invalid_limits_are_handled():
    lim = DistributedRateLimiter(R())
    assert not await lim.allow("x", 0, 60)
    with pytest.raises(ValueError):
        await lim.allow("x", 1, 0)


@pytest.mark.asyncio
async def test_rate_limit_uses_a_stable_key_instead_of_wall_clock_buckets():
    redis = R()
    lim = DistributedRateLimiter(redis)
    assert await lim.allow("x", 1, 60)
    assert not await lim.allow("x", 1, 60)
    assert redis.client.keys == ["rl:x", "rl:x"]
