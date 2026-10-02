import asyncio
import pytest
from bot.services.guild_config import GuildConfigService

class Cache:
    def __init__(self): self.data = {}; self.locked = False; self.sets = 0
    async def get_json(self, key): return self.data.get(key)
    async def acquire_lock(self, key, token, ttl):
        if self.locked: return False
        self.locked = True; return True
    async def release_lock(self, key, token): self.locked = False; return True
    async def set_json(self, key, value, ttl=300): self.data[key] = value; self.sets += 1
    async def renew_lock(self, key, token, ttl): return self.locked

class Session:
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass
    async def execute(self, query):
        await asyncio.sleep(.01)
        class R:
            def mappings(self): return self
            def first(self): return {'guild_id': 123}
        return R()
class DB:
    def __init__(self): self.calls = 0
    def session(self):
        self.calls += 1
        return Session()

@pytest.mark.asyncio
async def test_same_process_cache_miss_is_single_flight():
    cache, db = Cache(), DB()
    svc = GuildConfigService(db, cache)
    results = await asyncio.gather(*(svc.get(123) for _ in range(100)))
    assert len(results) == 100
    assert db.calls == 1
    assert cache.sets == 1
