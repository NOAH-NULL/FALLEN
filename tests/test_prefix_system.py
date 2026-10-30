import types

import discord
import pytest
from discord.ext import commands

from bot.core.bot import Bot
from bot.services.guild_config import GuildConfigService
from bot.commands.prefix import Prefix


class FakeConfig:
    def __init__(self, value):
        self.value = value
        self.calls = []

    async def get(self, guild_id):
        self.calls.append(guild_id)
        return {"command_prefix": self.value}


class FakeMessage:
    def __init__(self, guild_id=None):
        self.guild = types.SimpleNamespace(id=guild_id) if guild_id else None


@pytest.mark.asyncio
async def test_dynamic_prefix_uses_guild_setting(monkeypatch):
    seen = {}

    def fake_when_mentioned_or(*prefixes):
        def resolve(bot, message):
            seen["prefixes"] = prefixes
            return list(prefixes)
        return resolve

    monkeypatch.setattr(commands, "when_mentioned_or", fake_when_mentioned_or)
    bot = types.SimpleNamespace(guild_config=FakeConfig("!!"))
    result = await Bot._command_prefix(bot, FakeMessage(123))

    assert result == ["!!"]
    assert seen["prefixes"] == ("!!",)
    assert bot.guild_config.calls == [123]


@pytest.mark.asyncio
async def test_dynamic_prefix_falls_back_for_dm(monkeypatch):
    seen = {}

    def fake_when_mentioned_or(*prefixes):
        def resolve(bot, message):
            seen["prefixes"] = prefixes
            return list(prefixes)
        return resolve

    monkeypatch.setattr(commands, "when_mentioned_or", fake_when_mentioned_or)
    config = FakeConfig("!!")
    bot = types.SimpleNamespace(guild_config=config)
    result = await Bot._command_prefix(bot, FakeMessage())

    assert result == [","]
    assert seen["prefixes"] == (",",)
    assert config.calls == []


@pytest.mark.asyncio
async def test_dynamic_prefix_falls_back_when_config_lookup_fails(monkeypatch):
    seen = {}

    def fake_when_mentioned_or(*prefixes):
        def resolve(bot, message):
            seen["prefixes"] = prefixes
            return list(prefixes)
        return resolve

    monkeypatch.setattr(commands, "when_mentioned_or", fake_when_mentioned_or)

    class BrokenConfig:
        async def get(self, guild_id):
            raise RuntimeError("database unavailable")

    bot = types.SimpleNamespace(guild_config=BrokenConfig())
    result = await Bot._command_prefix(bot, FakeMessage(456))

    assert result == [","]
    assert seen["prefixes"] == (",",)


def test_guild_config_default_prefix_is_comma():
    service = GuildConfigService(db=None, cache=None)
    assert service._default(123)["command_prefix"] == ","


@pytest.mark.asyncio
async def test_prefix_cog_registers_hybrid_commands():
    bot = commands.Bot(command_prefix=",", intents=discord.Intents.none())
    bot.guild_config = types.SimpleNamespace(get=None, update=None)
    await bot.add_cog(Prefix(bot))

    group = bot.get_command("prefix")
    assert group is not None
    assert group.get_command("set") is not None
    assert group.get_command("reset") is not None

    slash_group = bot.tree.get_command("prefix")
    assert slash_group is not None
    assert {item.name for item in slash_group.commands} == {"set", "reset"}
    await bot.close()


def test_help_uses_dynamic_prefix_placeholder():
    from bot.commands.help import _prefix_inventory

    bot = commands.Bot(command_prefix=",", intents=discord.Intents.none())
    async def probe(ctx):\n        return None\n\n    bot.add_command(commands.Command(probe, name="probe"))
    entries = _prefix_inventory(bot)
    assert any(syntax == "<prefix>probe" for _, syntax, _ in entries)
