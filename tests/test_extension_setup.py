"""Exercise extension setup and command registration without connecting to Discord."""

import pytest

from bot.core.bot import Bot, EXTENSIONS
from bot.core.config import Settings


@pytest.mark.asyncio
async def test_all_registered_extensions_load_together():
    # Use the real bot constructor so extension setup sees its expected services.
    # No login/start call is made, so this test does not connect to Discord.
    bot = Bot(Settings(token="test-token"))
    try:
        loaded = []
        for extension in EXTENSIONS:
            await bot.load_extension(extension)
            loaded.append(extension)
        assert loaded == list(EXTENSIONS)
        assert bot.tree.get_commands(), "Expected slash commands to be registered"
        assert bot.commands, "Expected prefix commands to be registered"
    finally:
        await bot.cache.close()
        await bot.db.close()
