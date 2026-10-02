import time
from collections import defaultdict, deque

class AntiRaid:
    """Distributed Redis-backed detector. Local fallback exists only for isolated unit tests."""
    def __init__(self, cache=None):
        self.cache=cache; self.local=defaultdict(deque)
    async def count(self,guild_id,window=10):
        if self.cache is not None:
            return await self.cache.anti_raid_size(guild_id,window)
        now=time.monotonic(); q=self.local[guild_id]
        while q and now-q[0]>window:q.popleft()
        return len(q)

    async def observe(self,guild_id,window=10,limit=8):
        if self.cache is not None:
            return await self.cache.anti_raid_count(guild_id,window,limit)
        now=time.monotonic(); q=self.local[guild_id]; q.append(now)
        while q and now-q[0]>window:q.popleft()
        return len(q)>=limit
