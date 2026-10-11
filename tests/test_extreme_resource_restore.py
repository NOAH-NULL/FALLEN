from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from bot.core.bot import Bot


@pytest.mark.asyncio
async def test_voice_channel_recovery_does_not_create_a_text_channel():
    resource = MagicMock(spec=discord.VoiceChannel)
    resource.id = 10
    resource.name = "voice-lounge"
    resource.category_id = None
    resource.position = 3
    resource.overwrites = {}
    resource.bitrate = 64000
    resource.user_limit = 0
    resource.rtc_region = None

    guild = MagicMock()
    guild.id = 123
    guild.get_channel.return_value = None
    guild.create_voice_channel = AsyncMock(return_value=SimpleNamespace(id=99))
    guild.create_text_channel = AsyncMock(return_value=SimpleNamespace(id=100))

    restored_id = await Bot.restore_deleted_resource(
        SimpleNamespace(), guild, resource, "channel_delete"
    )

    assert restored_id == 99
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
