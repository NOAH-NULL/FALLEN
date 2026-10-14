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


import pytest


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", None),
        ("0", [0]),
        ("0, 2,3", [0, 2, 3]),
    ],
)
def test_shard_ids_parse_valid_values(raw, expected):
    assert Settings(shard_ids=raw).parsed_shard_ids == expected


@pytest.mark.parametrize("raw", ["1,,2", ",1", "1,", "abc", "-1", "1,1"])
def test_shard_ids_reject_malformed_or_unsafe_values(raw):
    with pytest.raises(ValueError, match="SHARD_IDS"):
        Settings(shard_ids=raw).parsed_shard_ids


def test_shard_ids_must_fit_configured_shard_count():
    with pytest.raises(ValueError, match="SHARD_COUNT"):
        Settings(shard_count=2, shard_ids="0,2").parsed_shard_ids
