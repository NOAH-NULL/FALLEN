import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.commands.extreme import Extreme


class FakeMember:
    id = 456

    def __ge__(self, _other):
        return False

    async def __str__(self):
        return "test-member"


def make_context():
    guild = SimpleNamespace(id=123, me=object(), unban=AsyncMock())
    author = SimpleNamespace(id=789)
    ctx = SimpleNamespace(guild=guild, author=author, send=AsyncMock())
    return ctx


@pytest.mark.asyncio
async def test_temp_ban_schedule_failure_rolls_back_and_reports_failure():
    extreme_service = SimpleNamespace(
        enabled=AsyncMock(return_value=True),
        schedule=AsyncMock(side_effect=RuntimeError("database unavailable")),
        record_security=AsyncMock(),
    )
    bot = SimpleNamespace(extreme=extreme_service, log=logging.getLogger("test.extreme"))
    cog = Extreme(bot)
    ctx = make_context()
    member = FakeMember()
    member.ban = AsyncMock()

    await Extreme.temp_ban.callback(cog, ctx, member, 60, reason="test")

    member.ban.assert_awaited_once()
    ctx.guild.unban.assert_awaited_once()
    ctx.send.assert_awaited_once()
    assert "ban was rolled back" in ctx.send.await_args.args[0]
