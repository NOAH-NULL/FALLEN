from bot.core.config import Settings
def test_settings(monkeypatch):
    monkeypatch.setenv('DISCORD_TOKEN','abcdefghij123456'); monkeypatch.setenv('DATABASE_URL','postgresql+asyncpg://x:y@localhost/x'); s=Settings(); assert s.db_pool_size==5 and s.db_max_overflow==5


def test_float_environment_setting_falls_back_for_invalid_and_nonfinite_values(monkeypatch):
    from bot.core.config import _f

    monkeypatch.setenv("FALLEN_TEST_FLOAT", "not-a-number")
    assert _f("FALLEN_TEST_FLOAT", 2.5) == 2.5
    monkeypatch.setenv("FALLEN_TEST_FLOAT", "nan")
    assert _f("FALLEN_TEST_FLOAT", 2.5) == 2.5
    monkeypatch.setenv("FALLEN_TEST_FLOAT", "inf")
    assert _f("FALLEN_TEST_FLOAT", 2.5) == 2.5
    monkeypatch.setenv("FALLEN_TEST_FLOAT", "1.25")
    assert _f("FALLEN_TEST_FLOAT", 2.5) == 1.25
