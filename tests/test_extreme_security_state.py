import copy
from types import SimpleNamespace

import discord
import pytest

from bot.core.bot import Bot


class FakeExtreme:
    def __init__(self):
        self.snapshots = {}
        self.events = []

    async def snapshot_get(self, guild_id, name):
        return self.snapshots.get((guild_id, name))

    async def snapshot_save(self, guild_id, created_by, name, payload):
        row = SimpleNamespace(payload=copy.deepcopy(payload))
        self.snapshots[(guild_id, name)] = row
        return row

    async def snapshot_delete(self, guild_id, name):
        self.snapshots.pop((guild_id, name), None)

    async def record_security(self, *args, **kwargs):
        self.events.append((args, kwargs))


class FakeChannel:
    def __init__(self, channel_id, overwrite):
        self.id = channel_id
        self.overwrite = overwrite
        self.fail_updates = False

    def overwrites_for(self, _target):
        return copy.copy(self.overwrite)

    async def set_permissions(self, _target, *, overwrite, reason):
        if self.fail_updates:
            raise ValueError("simulated partial restore failure")
        self.overwrite = copy.copy(overwrite)


class FakeGuild:
    def __init__(self, channels):
        self.id = 123
        self.default_role = object()
        self.me = SimpleNamespace(id=999)
        self.text_channels = channels


def fake_bot(guild, extreme):
    return SimpleNamespace(get_guild=lambda _guild_id: guild, extreme=extreme)


@pytest.mark.asyncio
async def test_lockdown_preserves_unrelated_everyone_permissions():
    original = discord.PermissionOverwrite(
        view_channel=True,
        read_message_history=True,
        send_messages=True,
        add_reactions=False,
    )
    channel = FakeChannel(456, original)
    guild = FakeGuild([channel])
    extreme = FakeExtreme()
    bot = fake_bot(guild, extreme)

    await Bot.security_lockdown(bot, guild.id)

    assert channel.overwrite.send_messages is False
    assert channel.overwrite.view_channel is True
    assert channel.overwrite.read_message_history is True
    assert channel.overwrite.add_reactions is False

    await Bot.security_unlockdown(bot, guild.id)

    assert channel.overwrite.send_messages is True
    assert channel.overwrite.view_channel is True
    assert channel.overwrite.read_message_history is True
    assert channel.overwrite.add_reactions is False
    assert (guild.id, "__lockdown__") not in extreme.snapshots


@pytest.mark.asyncio
async def test_partial_lockdown_recovery_keeps_snapshot_for_retry():
    channel = FakeChannel(
        456,
        discord.PermissionOverwrite(view_channel=True, send_messages=True),
    )
    guild = FakeGuild([channel])
    extreme = FakeExtreme()
    bot = fake_bot(guild, extreme)

    await Bot.security_lockdown(bot, guild.id)
    channel.fail_updates = True

    await Bot.security_unlockdown(bot, guild.id)

    assert (guild.id, "__lockdown__") in extreme.snapshots
    assert extreme.events[-1][1]["details"]["complete"] is False
    assert extreme.events[-1][1]["details"]["snapshot_retained"] is True


@pytest.mark.asyncio
async def test_legacy_lockdown_snapshot_restores_send_messages_without_erasing_other_bits():
    channel = FakeChannel(
        456,
        discord.PermissionOverwrite(view_channel=True, send_messages=False),
    )
    guild = FakeGuild([channel])
    extreme = FakeExtreme()
    extreme.snapshots[(guild.id, "__lockdown__")] = SimpleNamespace(
        payload={"channels": {str(channel.id): True}}
    )
    bot = fake_bot(guild, extreme)

    await Bot.security_unlockdown(bot, guild.id)

    assert channel.overwrite.send_messages is True
    assert channel.overwrite.view_channel is True
