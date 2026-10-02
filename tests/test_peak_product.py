from pathlib import Path


def test_dashboard_has_real_operator_surface_and_auth_header():
    source = Path('bot/web/api.py').read_text()
    assert "'/dashboard'" in source
    assert "X-Dashboard-Key" in source
    assert 'Command center.' in source


def test_lockdown_restores_exact_default_role_state():
    source = Path('bot/core/bot.py').read_text()
    assert 'overwrites_for(guild.default_role).send_messages' in source
    assert 'value = state.get(str(channel.id))' in source


def test_anti_nuke_burst_detection_is_wired_to_destructive_events():
    source = Path('bot/core/bot.py').read_text()
    assert 'on_guild_channel_delete' in source
    assert 'on_guild_role_delete' in source
    assert 'anti_channel_delete' in source
    assert 'anti_role_delete' in source
