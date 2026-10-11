"""Regression tests for Discord shard routing fallback."""

from bot.workers.gateway import GatewayWorkerPool


def test_fallback_shard_id_uses_guild_snowflake_high_bits():
    guild_id = 175928847299117063
    shard_count = 7
    assert GatewayWorkerPool._fallback_shard_id(guild_id, shard_count) == (
        (guild_id >> 22) % shard_count
    )


def test_fallback_shard_id_handles_zero_or_missing_count_safely():
    assert GatewayWorkerPool._fallback_shard_id(175928847299117063, 0) == (
        175928847299117063 >> 22
    ) % 1
