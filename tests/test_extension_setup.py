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


@pytest.mark.asyncio
async def test_critical_slash_and_prefix_command_surfaces_are_registered():
    bot = Bot(Settings(token="test-token"))
    try:
        for extension in EXTENSIONS:
            await bot.load_extension(extension)

        slash = {command.name: command for command in bot.tree.get_commands()}
        expected_slash = {
            "greeting", "rules", "invites", "inviteleaderboard", "play",
            "uwuify", "rank", "leaderboard", "level", "custom", "config",
            "settings", "ticket", "ping", "health", "help",
        }
        assert expected_slash <= set(slash)

        rules_children = {command.name for command in slash["rules"].commands}
        assert {
            "setup", "add", "edit", "remove", "button", "publish",
            "edit-panel", "image", "image-url", "remove-image", "status",
        } <= rules_children

        greeting_children = {command.name for command in slash["greeting"].commands}
        assert {
            "edit", "toggle", "embed", "color", "image", "preview",
            "test", "channel", "roles", "reset", "status",
        } <= greeting_children

        expected_prefix = {
            "help", "uwuify", "invites", "inviteleaderboard", "fuck",
            "hug", "greet", "ping", "health", "welcome-channel",
            "goodbye-channel", "ticket", "play",
        }
        assert all(bot.get_command(name) is not None for name in expected_prefix)
    finally:
        await bot.cache.close()
        await bot.db.close()
