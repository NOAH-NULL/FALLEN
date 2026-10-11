"""Exercise extension setup and command registration without connecting to Discord."""

import discord
import pytest
from discord.ext import commands

from bot.core.bot import EXTENSIONS


@pytest.mark.asyncio
async def test_all_registered_extensions_load_together():
    bot = commands.Bot(command_prefix=",", intents=discord.Intents.none(), help_command=None)
    try:
        loaded = []
        for extension in EXTENSIONS:
            await bot.load_extension(extension)
            loaded.append(extension)
        assert loaded == list(EXTENSIONS)
        assert bot.tree.get_commands(), "Expected slash commands to be registered"
        assert bot.commands, "Expected prefix commands to be registered"
    finally:
        await bot.close()
