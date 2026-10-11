from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot.services.welcome_engine import WelcomeEngine


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
    slash_source = Path('bot/commands/greeting.py').read_text()
    prefix_source = Path('bot/commands/greeting_prefix.py').read_text()
    for name in ('edit', 'toggle', 'embed', 'color', 'image', 'preview', 'test', 'channel', 'roles', 'reset', 'status'):
        assert f"name='{name}'" in slash_source
    for name in ('status', 'placeholders', 'dm', 'button', 'details', 'preset', 'mode', 'roles', 'log', 'security', 'button-set', 'bots', 'reliability', 'advanced'):
        assert f"name='{name}'" in prefix_source


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



def test_greeting_delivery_has_one_owner_and_no_legacy_duplicate_listeners():
    slash_source = Path('bot/commands/greeting.py').read_text()
    worker_source = Path('bot/workers/greetings.py').read_text()
    assert 'async def on_member_join' not in slash_source
    assert 'async def on_member_remove' not in slash_source
    assert 'self.bot.greeting_worker.deliver(' in slash_source
    assert 'test_mode=True' in slash_source
    assert 'and not test_mode' in worker_source


def test_greeting_test_commands_do_not_trigger_welcome_side_effects():
    prefix_source = Path('bot/commands/greeting_prefix.py').read_text()
    worker_source = Path('bot/workers/greetings.py').read_text()
    assert 'test_mode=True' in prefix_source
    assert 'if kind == "welcome" and not test_mode:' in worker_source
    assert 'and not test_mode' in worker_source



def test_zero_new_account_threshold_really_disables_new_account_flag():
    engine = WelcomeEngine(None)
    settings = engine.normalize({"new_account_days": 0})
    member = SimpleNamespace(created_at=datetime.now(timezone.utc) - timedelta(days=1))

    assert settings["new_account_days"] == 0
    assert engine.risk(member, settings)["is_new"] is False


def test_partial_advanced_settings_preserve_legacy_welcome_options():
    settings = WelcomeEngine.normalize(
        {"welcome_image_url": "https://example.com/banner.gif"},
        {
            "welcome_dm_enabled": True,
            "welcome_show_details": False,
            "welcome_button_enabled": True,
            "welcome_button_label": "Read rules",
            "welcome_button_url": "https://example.com/rules",
            "autorole_id": 12345,
        },
    )

    assert settings["dm_enabled"] is True
    assert settings["show_details"] is False
    assert settings["buttons"] == [{
        "enabled": True, "label": "Read rules", "url": "https://example.com/rules",
    }]
    assert settings["auto_role_ids"] == [12345]
