from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from bot.core.bot import Bot


@pytest.mark.asyncio
async def test_voice_channel_recovery_does_not_create_a_text_channel():
    resource = MagicMock(spec=discord.VoiceChannel)
    resource.id = 10
    resource.name = "attacker-renamed"
    resource.category_id = None
    resource.position = 9
    resource.overwrites = {"compromised": "permissions"}
    resource.bitrate = 64000
    resource.user_limit = 0
    resource.rtc_region = None

    guild = MagicMock()
    guild.id = 123
    guild.get_channel.return_value = None
    guild.get_role.return_value = None
    guild.get_member.return_value = None
    guild.create_voice_channel = AsyncMock(return_value=SimpleNamespace(id=99))
    guild.create_text_channel = AsyncMock(return_value=SimpleNamespace(id=100))

    extreme = SimpleNamespace(snapshot_get=AsyncMock(return_value=SimpleNamespace(payload={
        "channels": {"10": {"name": "voice-lounge", "position": 3, "overwrites": {}}}
    })))
    restored_id = await Bot.restore_deleted_resource(
        SimpleNamespace(extreme=extreme), guild, resource, "channel_delete"
    )

    assert restored_id == 99
    kwargs = guild.create_voice_channel.await_args.kwargs
    assert guild.create_voice_channel.await_args.args[0] == "voice-lounge"
    assert kwargs["position"] == 3
    assert kwargs["overwrites"] == {}
    guild.create_voice_channel.assert_awaited_once()
    guild.create_text_channel.assert_not_awaited()


@pytest.mark.asyncio
async def test_unsupported_channel_type_is_not_misrepresented_as_text():
    resource = SimpleNamespace(id=11, name="forum", overwrites={}, position=0)
    guild = MagicMock()
    guild.id = 123
    guild.create_text_channel = AsyncMock()

    restored_id = await Bot.restore_deleted_resource(
        SimpleNamespace(), guild, resource, "channel_delete"
    )

    assert restored_id is None
    guild.create_text_channel.assert_not_awaited()
