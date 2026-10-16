from types import SimpleNamespace

import pytest

from bot.__main__ import validate_startup_settings


def settings(**overrides):
    values = {
        "token": "test-token",
        "environment": "production",
        "database_url": "postgresql+asyncpg://user:pass@postgres.railway.internal:5432/app",
        "redis_url": "redis://default:pass@redis.railway.internal:6379/0",
        "shard_count": None,
        "parsed_shard_ids": None,
        "shard_ids": "",
        "instance_id": "test-instance",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_valid_production_settings_pass():
    validate_startup_settings(settings())


def test_missing_discord_token_fails_without_echoing_secrets():
    with pytest.raises(RuntimeError, match="DISCORD_TOKEN is missing"):
        validate_startup_settings(settings(token=""))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "database_url",
            "postgresql+asyncpg://user:secret@localhost:5432/app",
            "DATABASE_URL points to localhost",
        ),
        (
            "redis_url",
            "redis://localhost:6379/0",
            "REDIS_URL points to localhost",
        ),
    ],
)
def test_production_local_dependencies_fail_fast(field, value, message):
    with pytest.raises(RuntimeError, match=message):
        validate_startup_settings(settings(**{field: value}))


def test_development_can_use_local_dependencies():
    validate_startup_settings(
        settings(
            environment="development",
            database_url="postgresql+asyncpg://user:pass@localhost:5432/app",
            redis_url="redis://localhost:6379/0",
        )
    )

