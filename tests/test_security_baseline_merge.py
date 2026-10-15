from types import SimpleNamespace

import pytest

from bot.services.extreme import ExtremeService


class Result:
    def __init__(self, row):
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class Session:
    def __init__(self, row):
        self.row = row
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def execute(self, statement):
        return Result(self.row)

    def add(self, row):
        self.row = row

    async def commit(self):
        self.committed = True


class DB:
    def __init__(self, row):
        self.current_session = Session(row)

    def session(self):
        return self.current_session


@pytest.mark.asyncio
async def test_legacy_upgrade_adds_type_without_overwriting_trusted_metadata():
    row = SimpleNamespace(payload={
        "channels": {
            "1": {"name": "trusted-name", "position": 1},
            "2": {"name": "deleted-legacy-channel", "position": 2},
        },
        "roles": {},
    }, created_by=1)
    db = DB(row)
    service = ExtremeService(db)
    current = {
        "channels": {
            "1": {
                "type": "TextChannel", "is_news": False,
                "name": "attacker-current-name", "position": 99,
            },
            "3": {"type": "VoiceChannel", "is_news": False, "name": "new-channel"},
        },
        "roles": {"4": {"name": "new-role", "position": 2}},
    }

    await service.snapshot_upgrade_baseline(10, 20, "__security_state__", current)

    payload = row.payload
    assert payload["channels"]["1"]["name"] == "trusted-name"
    assert payload["channels"]["1"]["type"] == "TextChannel"
    assert payload["channels"]["2"]["name"] == "deleted-legacy-channel"
    assert payload["channels"]["3"]["name"] == "new-channel"
    assert payload["roles"]["4"]["name"] == "new-role"
    assert db.current_session.committed


@pytest.mark.asyncio
async def test_new_resource_merge_does_not_replace_other_trusted_entries():
    row = SimpleNamespace(payload={
        "channels": {"1": {"name": "trusted-name", "position": 1}},
        "roles": {},
    }, created_by=1)
    db = DB(row)
    service = ExtremeService(db)
    current = {
        "channels": {
            "1": {"name": "attacker-current-name"},
            "2": {"name": "new-channel", "type": "TextChannel"},
        },
        "roles": {},
    }

    await service.snapshot_merge_resource(
        10, 20, "__security_state__", current, "channels", 2
    )

    assert row.payload["channels"]["1"]["name"] == "trusted-name"
    assert row.payload["channels"]["2"]["name"] == "new-channel"
    assert db.current_session.committed
