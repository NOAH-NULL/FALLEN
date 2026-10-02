from pathlib import Path


def test_text_command_surface_is_loaded_and_uses_comma_default():
    config = Path('bot/core/config.py').read_text()
    bot = Path('bot/core/bot.py').read_text()
    text = Path('bot/commands/text.py').read_text()
    assert "command_prefix:str=','" in config
    assert "'bot.commands.text'" in bot
    for command in ('name="hug"', 'name="kill"', 'name="ban"', 'name="mute"', 'name="unmute"', 'name="play"', 'name="stop"'):
        assert command in text
    for alias in ('aliases=["Hug"]', 'aliases=["m", "Mute"]', 'aliases=["un", "Unmute"]', 'aliases=["p", "Play"]', 'aliases=["s", "Stop"]'):
        assert alias in text
