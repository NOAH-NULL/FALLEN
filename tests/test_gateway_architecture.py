import asyncio
from bot.core.event_queue import GatewayEventQueue

def test_gateway_queue_is_bounded_and_nonblocking():
    q=GatewayEventQueue(maxsize=1)
    assert q.put_nowait('member_join', 1)
    assert not q.put_nowait('member_join', 2)
    assert q.dropped == 1

def test_queue_get():
    async def run():
        q=GatewayEventQueue(2); q.put_nowait('message', 7); e=await q.get(); assert e.kind=='message' and e.payload==7
    asyncio.run(run())


def test_critical_flood_cannot_starve_normal_events():
    async def run():
        q=GatewayEventQueue(maxsize=16, critical_maxsize=8)
        for i in range(8):
            q.put_nowait('critical', i, critical=True)
        q.put_nowait('normal', 99)
        seen=[]
        for _ in range(9):
            e=await q.get(); seen.append(e.kind); q.task_done(e)
        assert seen[8] == 'normal'
    asyncio.run(run())
