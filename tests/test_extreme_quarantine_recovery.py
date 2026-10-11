from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.core.bot import Bot


class FakeRole:
    def __init__(self, role_id, name, position):
        self.id = role_id
        self.name = name
        self.position = position

    def __lt__(self, other):
        return self.position < other.position

    def __ge__(self, other):
        return self.position >= other.position


class FakeExtreme:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.snapshot_delete = AsyncMock()

    async def snapshot_get(self, _guild_id, _name):
        return self.snapshot


@pytest.mark.asyncio
async def test_unquarantine_restores_roles_and_removes_quarantine_role():
    saved_role = FakeRole(1, "Moderator", 2)
    quarantine_role = FakeRole(2, "Fallen Quarantine", 3)
    top_role = FakeRole(3, "Fallen", 10)
    member = SimpleNamespace(
        id=456,
        roles=[quarantine_role],
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=123,
        me=SimpleNamespace(top_role=top_role),
        roles=[saved_role, quarantine_role, top_role],
        get_member=lambda _member_id: member,
        get_role=lambda role_id: {1: saved_role, 2: quarantine_role, 3: top_role}.get(role_id),
    )
    extreme = FakeExtreme(SimpleNamespace(payload={"role_ids": [1]}))
    bot = SimpleNamespace(extreme=extreme)

    restored = await Bot.restore_quarantined_member(bot, guild, member.id)

    assert restored == 1
    member.add_roles.assert_awaited_once_with(
        saved_role, reason="Fallen anti-nuke quarantine recovery"
    )
    member.remove_roles.assert_awaited_once_with(
        quarantine_role, reason="Fallen anti-nuke quarantine recovery"
    )
    extreme.snapshot_delete.assert_awaited_once_with(guild.id, "__quarantine__:456")


@pytest.mark.asyncio
async def test_partial_unquarantine_keeps_snapshot_and_quarantine_role():
    quarantine_role = FakeRole(2, "Fallen Quarantine", 3)
    top_role = FakeRole(3, "Fallen", 10)
    member = SimpleNamespace(
        id=456,
        roles=[quarantine_role],
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=123,
        me=SimpleNamespace(top_role=top_role),
        roles=[quarantine_role, top_role],
        get_member=lambda _member_id: member,
        get_role=lambda _role_id: None,
    )
    extreme = FakeExtreme(SimpleNamespace(payload={"role_ids": [999]}))
    bot = SimpleNamespace(extreme=extreme)

    restored = await Bot.restore_quarantined_member(bot, guild, member.id)

    assert restored == 0
    member.remove_roles.assert_not_awaited()
    extreme.snapshot_delete.assert_not_awaited()
