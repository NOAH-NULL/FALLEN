from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.workers.scheduler import Scheduler


@pytest.mark.asyncio
async def test_scheduled_punishment_retries_when_guild_is_not_cached():
    action = SimpleNamespace(id=1, guild_id=123, target_id=456, action="ban")
    platform = SimpleNamespace(due_reminders=AsyncMock(return_value=[]))
    extreme = SimpleNamespace(
        due_actions=AsyncMock(return_value=[action]),
        release_action=AsyncMock(),
        complete_action=AsyncMock(),
    )
    bot = SimpleNamespace(platform=platform, extreme=extreme, get_guild=lambda _gid: None)
    scheduler = Scheduler(bot, interval=0)

    async def release_and_stop(action_id):
        scheduler.stop.set()
        return True

    extreme.release_action.side_effect = release_and_stop

    await scheduler.run()

    extreme.release_action.assert_awaited_once_with(action.id)
    extreme.complete_action.assert_not_awaited()
