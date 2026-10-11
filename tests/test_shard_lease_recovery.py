"""Regression tests for fail-closed shard ownership and shutdown ordering."""

import asyncio
from pathlib import Path

import pytest

from bot.core.shard_lease import ShardLeaseManager


class FailingRenewCache:
    def __init__(self):
        self.published = False
        self._bot_close_callback = None

    async def renew_fenced_lock(self, *args):
        raise ConnectionError("redis unavailable")

    async def publish(self, *args):
        self.published = True


@pytest.mark.asyncio
async def test_lease_renewal_error_marks_unhealthy_and_shuts_down():
    cache = FailingRenewCache()
    closed = asyncio.Event()
    manager = ShardLeaseManager(cache, "test-owner", ttl_ms=3000)
    manager.fences = {0: 7}
    manager.token = "token"
    manager.bind_shutdown(lambda: closed.set())

    await manager._renew()

    assert manager.healthy is False
    assert cache.published is True
    assert closed.is_set()


def test_shutdown_stops_scheduler_before_releasing_leases():
    source = Path("bot/core/bot.py").read_text()
    close_body = source[source.rfind("    async def close(self):"):]
    assert close_body.index('close_step("scheduler"') < close_body.index('close_step("shard_leases"')
    assert 'close_step("database"' in close_body
    assert 'close_step("discord_client"' in close_body
