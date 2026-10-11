from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.commands.invites import Invites


@pytest.mark.asyncio
async def test_invites_command_reports_tracked_join_count():
    member = SimpleNamespace(
        id=123,
        mention="<@123>",
        display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
    )
    interaction = SimpleNamespace(
        guild_id=456,
        user=member,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(
        invites=SimpleNamespace(
            stats=AsyncMock(return_value=[SimpleNamespace(joins=7, leaves=1)])
        )
    )

    await Invites.invites.callback(Invites(bot), interaction, None)

    bot.invites.stats.assert_awaited_once_with(456, 123)
    interaction.response.send_message.assert_awaited_once()
    embed = interaction.response.send_message.await_args.kwargs["embed"]
    assert embed.title == "Invite Stats"
    assert "7" in embed.description
    assert "<@123>" in embed.description


@pytest.mark.asyncio
async def test_invites_command_handles_member_with_no_tracked_joins():
    member = SimpleNamespace(
        id=123,
        mention="<@123>",
        display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
    )
    interaction = SimpleNamespace(
        guild_id=456,
        user=member,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(
        invites=SimpleNamespace(stats=AsyncMock(return_value=[]))
    )

    await Invites.invites.callback(Invites(bot), interaction, None)

    embed = interaction.response.send_message.await_args.kwargs["embed"]
    assert "0" in embed.description


@pytest.mark.asyncio
async def test_inviteleaderboard_handles_empty_server():
    interaction = SimpleNamespace(
        guild_id=456,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(
        invites=SimpleNamespace(stats=AsyncMock(return_value=[]))
    )

    await Invites.inviteleaderboard.callback(Invites(bot), interaction)

    interaction.response.send_message.assert_awaited_once_with(
        "No invite joins have been tracked yet."
    )


@pytest.mark.asyncio
async def test_inviteleaderboard_shows_top_ten_in_order():
    rows = [
        SimpleNamespace(user_id=1000 + i, joins=20 - i)
        for i in range(12)
    ]
    interaction = SimpleNamespace(
        guild_id=456,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(
        invites=SimpleNamespace(stats=AsyncMock(return_value=rows))
    )

    await Invites.inviteleaderboard.callback(Invites(bot), interaction)

    bot.invites.stats.assert_awaited_once_with(456)
    embed = interaction.response.send_message.await_args.kwargs["embed"]
    assert "**1.** <@1000> — **20** joins" in embed.description
    assert "**10.** <@1009> — **11** joins" in embed.description
    assert "<@1010>" not in embed.description


@pytest.mark.asyncio
async def test_invites_warns_when_manage_server_permission_is_missing():
    member = SimpleNamespace(
        id=123,
        mention="<@123>",
        display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
    )
    guild = SimpleNamespace(
        me=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=False))
    )
    interaction = SimpleNamespace(
        guild_id=456,
        guild=guild,
        user=member,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(
        invites=SimpleNamespace(stats=AsyncMock(return_value=[]))
    )

    await Invites.invites.callback(Invites(bot), interaction, None)

    embed = interaction.response.send_message.await_args.kwargs["embed"]
    warning = next(field for field in embed.fields if field.name == "Tracking setup")
    assert "Manage Server" in warning.value
    assert "Server Members Intent" in warning.value


@pytest.mark.asyncio
async def test_empty_invite_leaderboard_explains_missing_permission():
    guild = SimpleNamespace(
        me=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=False))
    )
    interaction = SimpleNamespace(
        guild_id=456,
        guild=guild,
        response=SimpleNamespace(send_message=AsyncMock()),
    )
    bot = SimpleNamespace(
        invites=SimpleNamespace(stats=AsyncMock(return_value=[]))
    )

    await Invites.inviteleaderboard.callback(Invites(bot), interaction)

    args = interaction.response.send_message.await_args
    assert "No invite joins have been tracked yet." in args.args[0]
    assert "Manage Server" in args.args[0]
    assert args.kwargs["ephemeral"] is True
