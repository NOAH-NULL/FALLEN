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


@pytest.mark.asyncio
async def test_recovery_skips_recreation_when_trusted_baseline_is_missing():
    resource = MagicMock(spec=discord.VoiceChannel)
    resource.id = 12
    resource.name = "untrusted-name"
    resource.category_id = None
    resource.position = 4
    resource.overwrites = {}

    guild = MagicMock()
    guild.id = 123
    guild.get_channel.return_value = None
    guild.create_voice_channel = AsyncMock()

    extreme = SimpleNamespace(snapshot_get=AsyncMock(return_value=None))
    restored_id = await Bot.restore_deleted_resource(
        SimpleNamespace(extreme=extreme), guild, resource, "channel_delete"
    )

    assert restored_id is None
    guild.create_voice_channel.assert_not_awaited()



@pytest.mark.asyncio
async def test_text_channel_recovery_uses_baseline_metadata_not_modified_event_object():
    resource = MagicMock(spec=discord.TextChannel)
    resource.id = 13
    resource.name = "attacker-renamed"
    resource.category_id = 88
    resource.position = 19
    resource.topic = "attacker-controlled topic"
    resource.nsfw = True
    resource.slowmode_delay = 21600
    resource.overwrites = {}
    resource.is_news.return_value = False

    category = SimpleNamespace(id=77, name="original-category")
    guild = MagicMock()
    guild.id = 123
    guild.get_channel.side_effect = lambda channel_id: category if channel_id == 77 else None
    guild.get_role.return_value = None
    guild.get_member.return_value = None
    guild.create_text_channel = AsyncMock(return_value=SimpleNamespace(id=101))

    extreme = SimpleNamespace(snapshot_get=AsyncMock(return_value=SimpleNamespace(payload={
        "channels": {
            "13": {
                "name": "original-channel",
                "position": 2,
                "category_id": 77,
                "topic": "trusted topic",
                "nsfw": False,
                "slowmode_delay": 5,
                "overwrites": {},
            }
        }
    })))

    restored_id = await Bot.restore_deleted_resource(
        SimpleNamespace(extreme=extreme), guild, resource, "channel_delete"
    )

    assert restored_id == 101
    kwargs = guild.create_text_channel.await_args.kwargs
    assert guild.create_text_channel.await_args.args[0] == "original-channel"
    assert kwargs["category"] is category
    assert kwargs["position"] == 2
    assert kwargs["topic"] == "trusted topic"
    assert kwargs["nsfw"] is False
    assert kwargs["slowmode_delay"] == 5


@pytest.mark.asyncio
async def test_deleted_channel_recovery_fetches_uncached_member_overwrite_targets():
    member = MagicMock(spec=discord.Member)
    member.id = 555
    member.name = "uncached-member"
    resource = MagicMock(spec=discord.TextChannel)
    resource.id = 14
    resource.name = "attacker-name"
    resource.category_id = None
    resource.position = 8
    resource.topic = None
    resource.nsfw = False
    resource.slowmode_delay = 0
    resource.overwrites = {}
    resource.is_news.return_value = False

    guild = MagicMock()
    guild.id = 123
    guild.get_channel.return_value = None
    guild.get_role.return_value = None
    guild.get_member.return_value = None
    guild.fetch_member = AsyncMock(return_value=member)
    guild.create_text_channel = AsyncMock(return_value=SimpleNamespace(id=102))

    extreme = SimpleNamespace(snapshot_get=AsyncMock(return_value=SimpleNamespace(payload={
        "channels": {
            "14": {
                "name": "trusted-channel",
                "position": 1,
                "overwrites": {"555": {"allow": discord.Permissions(view_channel=True).value, "deny": 0}},
            }
        }
    })))

    restored_id = await Bot.restore_deleted_resource(
        SimpleNamespace(extreme=extreme), guild, resource, "channel_delete"
    )

    assert restored_id == 102
    guild.fetch_member.assert_awaited_once_with(555)
    assert member in guild.create_text_channel.await_args.kwargs["overwrites"]


@pytest.mark.asyncio
async def test_security_state_restore_recreates_all_missing_baseline_text_channels():
    baseline = SimpleNamespace(payload={
        "roles": {},
        "channels": {
            "201": {
                "type": "TextChannel", "is_news": False, "name": "rules",
                "position": 1, "category_id": None, "topic": "Server rules",
                "nsfw": False, "slowmode_delay": 0, "overwrites": {},
            },
            "202": {
                "type": "TextChannel", "is_news": False, "name": "announcements",
                "position": 2, "category_id": None, "topic": None,
                "nsfw": False, "slowmode_delay": 5, "overwrites": {},
            },
        },
    })
    extreme = SimpleNamespace(snapshot_get=AsyncMock(return_value=baseline), snapshot_save=AsyncMock())

    class RecoveryHarness:
        def __init__(self):
            self.extreme = extreme

        _recreate_missing_security_resource = Bot._recreate_missing_security_resource

    guild = MagicMock()
    guild.id = 123
    guild.get_channel.return_value = None
    guild.get_role.return_value = None
    guild.get_member.return_value = None
    guild.create_text_channel = AsyncMock(side_effect=[
        SimpleNamespace(id=301), SimpleNamespace(id=302)
    ])

    restored = await Bot.restore_security_state(RecoveryHarness(), guild)

    assert restored["channels"] == 2
    assert [call.args[0] for call in guild.create_text_channel.await_args_list] == [
        "rules", "announcements"
    ]
    assert guild.create_text_channel.await_args_list[0].kwargs["topic"] == "Server rules"
    assert guild.create_text_channel.await_args_list[1].kwargs["slowmode_delay"] == 5


@pytest.mark.asyncio
async def test_security_state_restore_recreates_missing_baseline_role():
    baseline = SimpleNamespace(payload={
        "roles": {
            "401": {
                "name": "Moderator", "position": 3, "permissions": 8,
                "colour": 123, "hoist": True, "mentionable": False,
            },
        },
        "channels": {},
    })
    extreme = SimpleNamespace(snapshot_get=AsyncMock(return_value=baseline), snapshot_save=AsyncMock())

    class RecoveryHarness:
        def __init__(self):
            self.extreme = extreme

        _recreate_missing_security_resource = Bot._recreate_missing_security_resource

    created_role = MagicMock()
    created_role.edit = AsyncMock()
    guild = MagicMock()
    guild.id = 123
    guild.me.top_role.position = 10
    guild.get_role.return_value = None
    guild.create_role = AsyncMock(return_value=created_role)
    guild.edit_role_positions = AsyncMock()

    restored = await Bot.restore_security_state(RecoveryHarness(), guild)

    assert restored["roles"] == 1
    guild.create_role.assert_awaited_once()
    assert guild.create_role.await_args.kwargs["name"] == "Moderator"
    assert guild.create_role.await_args.kwargs["permissions"].value == 8


@pytest.mark.asyncio
async def test_security_state_restore_recreates_category_before_its_children():
    baseline = SimpleNamespace(payload={
        "roles": {},
        "channels": {
            "502": {
                "type": "TextChannel", "is_news": False, "name": "inside-category",
                "position": 2, "category_id": 501, "topic": None,
                "nsfw": False, "slowmode_delay": 0, "overwrites": {},
            },
            "501": {
                "type": "CategoryChannel", "is_news": False, "name": "restored-category",
                "position": 1, "category_id": None, "overwrites": {},
            },
        },
    })
    extreme = SimpleNamespace(snapshot_get=AsyncMock(return_value=baseline), snapshot_save=AsyncMock())

    class RecoveryHarness:
        def __init__(self):
            self.extreme = extreme

        _recreate_missing_security_resource = Bot._recreate_missing_security_resource

    category = SimpleNamespace(id=601)
    text_channel = SimpleNamespace(id=602)
    guild = MagicMock()
    guild.id = 123
    guild.get_channel.return_value = None
    guild.get_role.return_value = None
    guild.get_member.return_value = None
    guild.create_category = AsyncMock(return_value=category)
    guild.create_text_channel = AsyncMock(return_value=text_channel)

    restored = await Bot.restore_security_state(RecoveryHarness(), guild)

    assert restored["channels"] == 2
    guild.create_category.assert_awaited_once()
    guild.create_text_channel.assert_awaited_once()
    assert guild.create_text_channel.await_args.kwargs["category"] is category
