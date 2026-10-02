from bot.services.antiraid import AntiRaid
import pytest
@pytest.mark.asyncio
async def test_antiraid_threshold():
    a=AntiRaid()
    out=False
    for _ in range(8): out=await a.observe(1,window=10,limit=8)
    assert out is True
