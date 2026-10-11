from pathlib import Path


def test_advanced_greeting_schema_exists():
    schema = Path('bot/models/schema.py').read_text()
    for field in (
        'welcome_dm_enabled',
        'welcome_dm_message',
        'welcome_button_enabled',
        'welcome_button_label',
        'welcome_button_url',
        'welcome_show_details',
        'welcome_settings',
    ):
        assert field in schema


def test_advanced_greeting_migration_exists():
    migration = Path('alembic/versions/0016_greeting_advanced.py').read_text()
    assert 'revision = "0016_greeting_advanced"' in migration
    assert 'down_revision = "0015_leveling_message_xp"' in migration
    migration2 = Path('alembic/versions/0017_welcome_engine.py').read_text()
    assert 'revision = "0017_welcome_engine"' in migration2
    assert 'down_revision = "0016_greeting_advanced"' in migration2


def test_advanced_greeting_commands_exist():
    source = Path('bot/commands/greeting.py').read_text()
    for name in ('status', 'placeholders', 'dm', 'button', 'details', 'preset', 'mode', 'roles', 'log', 'security', 'button-set', 'bots', 'reliability', 'advanced'):
        assert f"name='{name}'" in source


def test_advanced_greeting_prefix_commands_exist():
    source = Path('bot/commands/greeting_prefix.py').read_text()
    for name in ('status', 'placeholders', 'dm', 'button', 'details'):
        assert f"name='{name}'" in source


def test_advanced_placeholders_are_supported():
    renderer = Path('bot/services/greeting.py').read_text()
    for name in (
        'inviter_name',
        'account_age',
        'account_created',
        'joined_at',
        'boosts',
        'server_id',
        'user_id',
    ):
        assert name in renderer



def test_welcome_engine_source_exists():
    source = Path('bot/services/welcome_engine.py').read_text()
    for name in (
        'new_account_days',
        'auto_role_ids',
        'retry_attempts',
        'dedupe_seconds',
        'button_view',
        'apply_roles',
        'alert',
    ):
        assert name in source
