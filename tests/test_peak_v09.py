from pathlib import Path

def test_heat_engine_has_atomic_decay_and_factors():
    s=Path('bot/services/automod.py').read_text()
    assert 'math.exp' in s and 'HEAT_SCRIPT' in s
    assert 'mention_spam' in s and 'invite_phishing' in s
    assert 'configure_heat' in s

def test_control_plane_endpoints_exist():
    s=Path('bot/web/api.py').read_text()
    for x in ('audit-logs','snapshots','snapshots/restore','automod/rules'):
        assert x in s
    assert 'Authorization' in s

def test_quarantine_and_restore_wiring():
    s=Path('bot/core/bot.py').read_text()
    assert 'quarantine_member' in s
    assert 'restore_security_state' in s
    assert 'rogue_staff_quarantine' in s
