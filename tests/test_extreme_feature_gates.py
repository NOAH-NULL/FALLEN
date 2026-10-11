from types import SimpleNamespace

import pytest

from bot.services.extreme import (
    ALL_FEATURES,
    DEFAULTS,
    IMPLEMENTED_FEATURES,
    ExtremeService,
)


class FakeSession:
    def __init__(self, stored):
        self.row = SimpleNamespace(extreme_settings=stored)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, _model, _guild_id, **_kwargs):
        return self.row


class FakeDB:
    def __init__(self, stored):
        self.stored = stored

    def session(self):
        return FakeSession(self.stored)


@pytest.mark.asyncio
async def test_catalog_only_security_switch_cannot_be_enabled():
    service = ExtremeService(db=None)

    with pytest.raises(ValueError, match="not implemented yet"):
        await service.set(123, "anti_mass_ban", True)


@pytest.mark.asyncio
async def test_old_enabled_catalog_only_values_are_ignored():
    service = ExtremeService(FakeDB({
        "anti_permission_escalation": True,
        "member_profiles": False,
        "not_a_real_feature": True,
    }))

    state = await service.get(123)

    assert state["anti_permission_escalation"] is False
    assert state["member_profiles"] is False
    assert "not_a_real_feature" not in state


@pytest.mark.asyncio
async def test_validation_reports_stale_or_unknown_feature_values():
    service = ExtremeService(FakeDB({
        "anti_mass_ban": True,
        "unknown_feature": True,
    }))

    errors = await service.validate(123)

    assert any("anti_mass_ban" in error and "not implemented" in error for error in errors)
    assert any("unknown_feature" in error for error in errors)


def test_only_verified_capabilities_are_enabled_by_default():
    assert IMPLEMENTED_FEATURES <= ALL_FEATURES
    assert {key for key, enabled in DEFAULTS.items() if enabled} == {
        "server_reputation", "member_profiles", "personal_playlists"
    }
