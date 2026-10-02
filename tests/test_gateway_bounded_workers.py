import asyncio
import pytest
from bot.core.event_queue import GatewayEventQueue
from bot.workers.gateway import GatewayWorkerPool

class Guild:
    def __init__(self, gid): self.id = gid
class Payload:
    def __init__(self, gid): self.guild = Guild(gid)

class FakeBot:
    def __init__(self):
        self.shard_leases = type('Lease', (), {'healthy': True})()
        self.active = 0
        self.max_active = 0
    async def process_message(self, message):
        self.active += 1; self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.001)
        self.active -= 1
    async def process_member_join(self, m): pass
    async def process_member_remove(self, m): pass

@pytest.mark.asyncio
async def test_worker_pool_never_spawns_one_task_per_event():
    q = GatewayEventQueue(1000)
    bot = FakeBot()
    pool = GatewayWorkerPool(bot, q, workers=4, guild_concurrency=1)
    await pool.start()
    for i in range(200): q.put_nowait('message', Payload(i % 20))
    await q.drain(5)
    assert len(pool.tasks) == 4
    assert bot.max_active <= 4
    await pool.close()


@pytest.mark.asyncio
async def test_critical_queue_has_reserved_capacity_and_priority():
    q = GatewayEventQueue(maxsize=8, critical_maxsize=2)
    for i in range(6):
        assert q.put_nowait('message', Payload(i))
    assert q.put_nowait('message', Payload(99), critical=True)
    assert q.put_nowait('message', Payload(100), critical=True)
    assert q.put_nowait('message', Payload(101), critical=True) is False
    first = await q.get()
    assert first.critical is True
    q.task_done(first)
    second = await q.get()
    assert second.critical is True
    q.task_done(second)
    while q.qsize:
        event = await q.get(); q.task_done(event)

@pytest.mark.asyncio
async def test_stale_normal_events_are_shed_without_blocking_workers():
    from bot.core.event_queue import GatewayEvent
    q = GatewayEventQueue(10)
    bot = FakeBot()
    pool = GatewayWorkerPool(bot, q, workers=1, guild_concurrency=1, max_event_age=0.5)
    await pool.start()
    stale = GatewayEvent('message', Payload(1), False, 0.0)
    q.normal.put_nowait(stale)
    await asyncio.wait_for(q.drain(2), 2)
    assert bot.max_active == 0
    await pool.close()
