import pytest

from bot.cache.rate_limit import DistributedRateLimiter


class Fake:
    def __init__(self):
        self.n = {}
        self.keys = []
        self.values = {}

    async def eval(self, script, numkeys, key, *args):
        self.keys.append(key)
        if 'INCR' in script:
            self.n[key] = self.n.get(key, 0) + 1
            return self.n[key]
        token = args[0]
        if self.values.get(key) == token:
            del self.values[key]
            return 1
        return 0

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True


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


@pytest.mark.asyncio
async def test_reservation_can_only_be_released_by_its_owner():
    redis = R()
    lim = DistributedRateLimiter(redis)
    first = await lim.reserve('daily:1:2', 86400)
    assert first
    assert await lim.reserve('daily:1:2', 86400) is None
    assert not await lim.release_reservation('daily:1:2', 'not-the-owner')
    assert await lim.release_reservation('daily:1:2', first)
    assert await lim.reserve('daily:1:2', 86400)
