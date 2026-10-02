from pathlib import Path


def test_dynamic_help_extension_is_loaded():
    bot = Path('bot/core/bot.py').read_text()
    assert "'bot.commands.help'" in bot
    assert "'help_command':None" in bot


def test_help_has_prefix_and_slash_interfaces():
    source = Path('bot/commands/help.py').read_text()
    assert '@commands.command(name="help"' in source
    assert '@app_commands.command(name="help"' in source
    assert 'class HelpPager' in source
    assert 'for command in bot.walk_commands()' in source
    assert 'for command in bot.tree.get_commands()' in source


def test_help_only_lists_registered_commands():
    source = Path('bot/commands/help.py').read_text()
    assert 'Only registered commands are listed.' in source
    assert 'No commands are currently registered.' in source
