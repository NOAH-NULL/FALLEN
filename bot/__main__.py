import asyncio
import logging
from urllib.parse import urlparse

from bot.core.bot import Bot
from bot.core.config import Settings
from bot.core.logging import configure_logging

log = logging.getLogger("bot.startup")


def validate_startup_settings(settings: Settings) -> None:
    """Fail early with actionable, secret-safe messages for invalid deployment config."""
    if not settings.token.strip():
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Set it in the Railway bot service Variables."
        )

    if settings.environment.lower() in {"production", "prod"}:
        database = urlparse(settings.database_url)
        redis = urlparse(settings.redis_url)

        if not database.hostname or database.hostname in {"localhost", "127.0.0.1", "::1"}:
            raise RuntimeError(
                "DATABASE_URL points to localhost in production. Set the Railway PostgreSQL "
                "service reference; the URL value is intentionally not logged."
            )
        if not redis.hostname or redis.hostname in {"localhost", "127.0.0.1", "::1"}:
            raise RuntimeError(
                "REDIS_URL points to localhost in production. Set the Railway Redis "
                "service reference; the URL value is intentionally not logged."
            )

        if settings.shard_count is not None and settings.shard_count < 1:
            raise RuntimeError("SHARD_COUNT must be a positive integer when configured.")

        # Validate SHARD_IDS before opening any connections or acquiring leases.
        _ = settings.parsed_shard_ids


async def main():
    settings = Settings()
    configure_logging(settings.log_level)
    validate_startup_settings(settings)
    log.info(
        "Starting FALLEN environment=%s instance_id=%s configured_shard_count=%s "
        "explicit_shard_ids=%s",
        settings.environment,
        settings.instance_id,
        settings.shard_count if settings.shard_count is not None else "auto",
        bool(settings.shard_ids.strip()),
    )
    async with Bot(settings) as bot:
        await bot.start(settings.token)


if __name__ == "__main__":
    asyncio.run(main())
