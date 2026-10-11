import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.web.api import DashboardAPI


class FakeRequest:
    def __init__(self, guild_id="123", body=None, headers=None):
        self.match_info = {"guild_id": guild_id}
        self._body = body if body is not None else {}
        self.headers = headers or {"X-Dashboard-Key": "secret"}

    async def json(self):
        return self._body


@pytest.mark.asyncio
async def test_dashboard_snapshot_restore_restores_feature_values():
    snapshot = SimpleNamespace(payload={"features": {"automatic_lockdown": False}})
    extreme = SimpleNamespace(
        snapshot_get=AsyncMock(return_value=snapshot),
        restore_features=AsyncMock(return_value={"restored": 1, "skipped": []}),
        record_security=AsyncMock(),
    )
    bot = SimpleNamespace(
        settings=SimpleNamespace(dashboard_api_key="secret"),
        get_guild=lambda guild_id: SimpleNamespace(id=guild_id),
        extreme=extreme,
    )
    api = DashboardAPI(bot)

    response = await api.restore_snapshot(FakeRequest(body={"name": "safe-snapshot"}))

    assert response.status == 200
    assert json.loads(response.text)["result"]["restored"] == 1
    extreme.restore_features.assert_awaited_once_with(
        123, {"automatic_lockdown": False}
    )
    extreme.record_security.assert_awaited_once()


@pytest.mark.asyncio
async def test_dashboard_restore_rejects_reserved_recovery_snapshots():
    extreme = SimpleNamespace(
        snapshot_get=AsyncMock(),
        restore_features=AsyncMock(),
        record_security=AsyncMock(),
    )
    bot = SimpleNamespace(
        settings=SimpleNamespace(dashboard_api_key="secret"),
        get_guild=lambda guild_id: SimpleNamespace(id=guild_id),
        extreme=extreme,
    )
    api = DashboardAPI(bot)

    response = await api.restore_snapshot(FakeRequest(body={"name": "__lockdown__"}))

    assert response.status == 400
    extreme.snapshot_get.assert_not_awaited()
    extreme.restore_features.assert_not_awaited()


@pytest.mark.asyncio
async def test_dashboard_restore_rejects_non_object_json():
    bot = SimpleNamespace(
        settings=SimpleNamespace(dashboard_api_key="secret"),
        get_guild=lambda guild_id: SimpleNamespace(id=guild_id),
        extreme=SimpleNamespace(),
    )
    api = DashboardAPI(bot)

    response = await api.restore_snapshot(FakeRequest(body=["not", "an", "object"]))

    assert response.status == 400
