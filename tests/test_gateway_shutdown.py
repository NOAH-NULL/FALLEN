import asyncio
import pytest
from bot.core.event_queue import GatewayEventQueue

@pytest.mark.asyncio
async def test_queue_stops_accepting_and_drains():
    q = GatewayEventQueue(2)
    assert q.put_nowait('message', 1)
    q.stop_accepting()
    assert not q.put_nowait('message', 2)
    event = await q.get()
    q.task_done(event)
    assert event.payload == 1
    assert await q.drain(0.1)

@pytest.mark.asyncio
async def test_full_queue_is_bounded():
    q = GatewayEventQueue(1)
    assert q.put_nowait('message', 1)
    assert not q.put_nowait('message', 2)
    assert q.dropped == 1
