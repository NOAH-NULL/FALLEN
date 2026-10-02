import asyncio, pytest
from sqlalchemy.dialects.postgresql import dialect
from bot.services.guild_config import GuildConfigService
class Cache:
    def __init__(self): self.data={}; self.locks={}
    async def get_json(self,k): return self.data.get(k)
    async def set_json(self,k,v,ttl=0): self.data[k]=v
    async def delete(self,k): self.data.pop(k,None)
    async def publish(self,*a): pass
    async def acquire_lock(self,k,t,ttl):
        if k in self.locks: return False
        self.locks[k]=t; return True
    async def release_lock(self,k,t): self.locks.pop(k,None); return True
class Result:
    def mappings(self): return self
    def first(self): return None
class Session:
    async def __aenter__(self): return self
    async def __aexit__(self,*a): pass
    async def execute(self,*a,**k): return Result()
class DB:
    def session(self): return Session()

class CaptureSession:
    def __init__(self): self.statement=None
    async def __aenter__(self): return self
    async def __aexit__(self,*a): pass
    async def execute(self,statement): self.statement=statement
    async def commit(self): pass

class CaptureDB:
    def __init__(self): self.captured=CaptureSession()
    def session(self): return self.captured

@pytest.mark.asyncio
async def test_concurrent_cache_misses_are_coalesced():
    c=Cache(); s=GuildConfigService(DB(),c,ttl=60)
    await asyncio.gather(*[s.get(1) for _ in range(50)])
    assert any(v['guild_id']==1 for v in c.data.values())

@pytest.mark.asyncio
async def test_update_inserts_required_defaults_and_updates_only_requested_fields():
    db=CaptureDB(); cache=Cache(); service=GuildConfigService(db,cache)
    await service.update(42,welcome_channel_id=123)

    statement=db.captured.statement
    params=statement.compile(dialect=dialect()).params
    sql=str(statement.compile(dialect=dialect()))
    assert params['guild_id']==42
    assert params['welcome_channel_id']==123
    assert params['welcome_message'].startswith('Welcome ')
    assert params['extreme_settings']=={}
    assert 'welcome_channel_id = excluded.welcome_channel_id' in sql
    assert 'welcome_message = excluded.welcome_message' not in sql
