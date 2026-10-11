from bot.services.antiraid import AntiRaid
import pytest
@pytest.mark.asyncio
async def test_antiraid_threshold():
    a=AntiRaid()
    out=False
    for _ in range(8): out=await a.observe(1,window=10,limit=8)
    assert out is True


from types import SimpleNamespace
from unittest.mock import AsyncMock
import discord
from bot.workers.scheduler import Scheduler


@pytest.mark.asyncio
async def test_reminder_message_cannot_ping_everyone_roles_or_unrelated_users(monkeypatch):
    reminder = SimpleNamespace(
        id=1, channel_id=10, user_id=20,
        message="hello @everyone <@&123> <@999>",
    )
    platform = SimpleNamespace(
        due_reminders=AsyncMock(side_effect=[[reminder], []]),
        complete_reminder=AsyncMock(),
        release_reminder=AsyncMock(),
    )
    extreme = SimpleNamespace(due_actions=AsyncMock(return_value=[]))
    channel = SimpleNamespace(send=AsyncMock())
    bot = SimpleNamespace(
        platform=platform, extreme=extreme,
        get_channel=lambda _channel_id: channel,
    )
    scheduler = Scheduler(bot, interval=0)

    async def stop_sleep(_seconds):
        scheduler.stop.set()

    monkeypatch.setattr("bot.workers.scheduler.asyncio.sleep", stop_sleep)
    await scheduler.run()

    channel.send.assert_awaited_once()
    allowed = channel.send.await_args.kwargs["allowed_mentions"]
    assert allowed.everyone is False
    assert allowed.roles is False
    assert [user.id for user in allowed.users] == [20]
    platform.complete_reminder.assert_awaited_once_with(1)
