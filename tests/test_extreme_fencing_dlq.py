import asyncio
import pytest
from bot.core.fencing import current_fence, push_fence, pop_fence, StaleLeaseError
from bot.core.shard_lease import ShardLeaseManager
from bot.workers.gateway import GatewayWorkerPool
from bot.core.event_queue import GatewayEventQueue


class LeaseCache:
    def __init__(self): self.leases={}; self.counters={}
    async def acquire_fenced_lock(self,k,t,fk,ttl):
        if k in self.leases: return 0
        self.counters[fk]=self.counters.get(fk,0)+1
        fence=self.counters[fk]; self.leases[k]=(t,fence); return fence
    async def renew_fenced_lock(self,k,t,f,ttl): return self.leases.get(k)==(t,f)
    async def release_fenced_lock(self,k,t,f):
        if self.leases.get(k)==(t,f): self.leases.pop(k); return True
        return False
    async def fenced_lock_is_current(self,k,t,f): return self.leases.get(k)==(t,f)
    async def publish(self,*a): pass

@pytest.mark.asyncio
async def test_shard_reacquire_gets_new_fencing_epoch():
    c=LeaseCache(); a=ShardLeaseManager(c,'a',10000); await a.acquire([0]); first=a.fences[0]
    await a.release()
    b=ShardLeaseManager(c,'b',10000); await b.acquire([0])
    assert b.fences[0] > first
    assert not await a.validate_fence(0, first)
    assert await b.validate_fence(0, b.fences[0])
    await b.release()


def test_fence_context_is_scoped():
    token=push_fence(type('C',(),{'shard_id':1,'fence':7,'token':'t'})())
    assert current_fence().fence == 7
    pop_fence(token)
    assert current_fence() is None


class Guild:
    def __init__(self,gid): self.id=gid
class Payload:
    def __init__(self,gid): self.guild=Guild(gid)
class Cache:
    def __init__(self): self.items=[]
    async def xadd(self,*args,**kwargs): self.items.append((args,kwargs)); return '1-0'
class BadBot:
    def __init__(self):
        self.cache=Cache(); self.shard_leases=type('Lease',(),{'healthy':True})(); self.failed=False
    async def process_message(self,m): self.failed=True; raise ValueError('poison')

@pytest.mark.asyncio
async def test_failed_event_is_dead_lettered_and_not_retried():
    q=GatewayEventQueue(10); bot=BadBot(); pool=GatewayWorkerPool(bot,q,workers=1)
    await pool.start(); q.put_nowait('message',Payload(1)); assert await q.drain(2)
    await pool.close()
    assert bot.failed and len(pool.dlq.items)==1 and len(bot.cache.items)==1
