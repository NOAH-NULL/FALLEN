import pytest
from bot.cache.rate_limit import DistributedRateLimiter
class Fake:
    def __init__(self): self.n={}
    async def incr(self,k): self.n[k]=self.n.get(k,0)+1; return self.n[k]
    async def expire(self,*a): pass
class R:
    def __init__(self): self.client=Fake()
@pytest.mark.asyncio
async def test_limit():
    lim=DistributedRateLimiter(R()); assert await lim.allow('x',2,60); assert await lim.allow('x',2,60); assert not await lim.allow('x',2,60)
