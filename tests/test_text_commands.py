from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.commands.fun import Fun
from bot.commands.text import TextCommands


def test_text_command_surface_is_loaded_and_uses_comma_default():
    config = Path("bot/core/config.py").read_text()
    bot_source = Path("bot/core/bot.py").read_text()
    assert "command_prefix:str=','" in config
    assert "'bot.commands.text'" in bot_source
    assert "'bot.commands.fun'" in bot_source

    text_commands = {command.name for command in TextCommands(SimpleNamespace()).get_commands()}
    assert {"mute", "timeout", "unmute", "ban", "play", "stop"} <= text_commands

    action_commands = {
        command.name
        for command in Fun(SimpleNamespace(reactions=SimpleNamespace(get=AsyncMock()))).get_commands()
    }
    assert {"hug", "kill", "highfive"} <= action_commands
