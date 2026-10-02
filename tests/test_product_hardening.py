from pathlib import Path


def test_release_ignores_runtime_artifacts():
    script = Path('scripts/build_release.py').read_text()
    gitignore = Path('.gitignore').read_text()
    for artifact in ('__pycache__', '.pytest_cache', '.coverage', '*.pyc'):
        assert artifact in script or artifact in gitignore


def test_global_app_command_error_handler_exists():
    source = Path('bot/core/bot.py').read_text()
    handler = Path('bot/core/app_errors.py').read_text()
    assert 'self.tree.on_error = handle_app_command_error' in source
    assert 'MissingPermissions' in handler
    assert 'BotMissingPermissions' in handler
    assert 'TransformerError' in handler


def test_custom_commands_are_real_user_flows():
    source = Path('bot/commands/custom.py').read_text()
    for name in ('name=\'set\'', 'name=\'use\'', 'name=\'remove\'', 'name=\'list\''):
        assert name in source
    assert 'AllowedMentions.none' in Path('bot/core/bot.py').read_text()


def test_fake_music_ack_is_not_present():
    source = Path('bot/commands/text.py').read_text()
    assert 'Music request received' not in source
