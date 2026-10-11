"""Regression tests for high-risk V16 service behavior."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import discord
import pytest
from sqlalchemy.dialects import postgresql

from bot.models import Playlist
from bot.services.extreme import IMPLEMENTED_FEATURES, ExtremeService
from bot.services.platform import PlatformService


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def __iter__(self):
        return iter([])


class FakeSession:
    def __init__(self):
        self.added = []
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return FakeResult()

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        return None


class FakeDB:
    def __init__(self):
        self.session_obj = FakeSession()

    @asynccontextmanager
    async def session(self):
        yield self.session_obj


@pytest.mark.asyncio
async def test_due_actions_can_reclaim_processing_rows_with_null_claim_time():
    db = FakeDB()
    service = ExtremeService(db)

    await service.due_actions()

    sql = str(db.session_obj.statement.compile(dialect=postgresql.dialect()))
    assert "scheduled_actions.claimed_at IS NULL" in sql


@pytest.mark.asyncio
async def test_playlist_names_are_trimmed_before_persistence():
    db = FakeDB()
    service = ExtremeService(db)

    row = await service.save_playlist(1, 2, "  focus  ", ["track-a"])

    assert row.name == "focus"
    assert row.tracks == ["track-a"]
    assert row in db.session_obj.added


def test_incomplete_join_screening_is_not_advertised_as_implemented():
    # These settings previously only produced internal detection labels; there
    # is no completed verification/quarantine flow for them yet.
    assert "anti_bot_join" not in IMPLEMENTED_FEATURES
    assert "account_age_verification" not in IMPLEMENTED_FEATURES
    assert "suspicious_username" not in IMPLEMENTED_FEATURES


def test_automod_error_responses_do_not_echo_internal_exceptions():
    source = Path("bot/commands/extreme.py").read_text()
    assert "Could not save the AutoMod rule because of an internal error" in source
    assert "except Exception as exc: return await ctx.send(f'❌ Could not save rule: {exc}')" not in source

def test_reputation_grants_are_rate_limited_and_scores_are_bounded():
    command_source = Path("bot/commands/extreme.py").read_text()
    service_source = Path("bot/services/extreme.py").read_text()
    assert "v16-rep:{ctx.guild.id}:{ctx.author.id}:{member.id}" in command_source
    assert "86400" in command_source
    assert "func.least(func.greatest(Reputation.score + delta, -100000), 100000)" in service_source

def test_user_supplied_v16_text_disables_mentions():
    source = Path("bot/commands/extreme.py").read_text()
    assert source.count("allowed_mentions=discord.AllowedMentions.none()") >= 4

def test_user_snapshots_cannot_overwrite_reserved_recovery_keys():
    source = Path("bot/commands/extreme.py").read_text()
    assert 'name.startswith("__")' in source
    assert "reserved for internal recovery data" in source

@pytest.mark.asyncio
async def test_schedule_rejects_unsupported_actions_before_database_access():
    service = ExtremeService(FakeDB())
    with pytest.raises(ValueError, match="must be 'ban' or 'timeout'"):
        await service.schedule(1, 2, "delete_everything", datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_schedule_rejects_naive_timestamps():
    service = ExtremeService(FakeDB())
    with pytest.raises(ValueError, match="timezone-aware"):
        await service.schedule(1, 2, "ban", datetime(2030, 1, 1))


class QueuedSession(FakeSession):
    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    async def execute(self, statement):
        self.statement = statement
        return FakeResult(self.values.pop(0))


class QueuedDB(FakeDB):
    def __init__(self, values):
        self.session_obj = QueuedSession(values)


@pytest.mark.asyncio
async def test_automod_rejects_rules_over_total_limit():
    service = ExtremeService(QueuedDB([None, 100]))
    with pytest.raises(ValueError, match="at most 100 AutoMod rules"):
        await service.upsert_automod_rule(1, "new-rule", "domain_blacklist", "bad.example")


@pytest.mark.asyncio
async def test_automod_rejects_regex_rules_over_runtime_limit():
    service = ExtremeService(QueuedDB([None, 10, 50]))
    with pytest.raises(ValueError, match="at most 50 regex rules"):
        await service.upsert_automod_rule(1, "new-regex", "regex", "spam")


class ConfigSession:
    def __init__(self, settings):
        self.settings = settings

    async def get(self, model, guild_id):
        return type("ConfigRow", (), {"extreme_settings": self.settings})()


class ConfigDB:
    def __init__(self, settings):
        self.settings = settings

    @asynccontextmanager
    async def session(self):
        yield ConfigSession(self.settings)


@pytest.mark.asyncio
async def test_string_false_cannot_enable_a_security_feature():
    service = ExtremeService(ConfigDB({"automatic_lockdown": "false"}))
    settings = await service.get(1)
    assert settings["automatic_lockdown"] is False


@pytest.mark.asyncio
async def test_set_rejects_non_boolean_feature_values():
    service = ExtremeService(FakeDB())
    with pytest.raises(ValueError, match="must be a boolean"):
        await service.set(1, "automatic_lockdown", "false")


@pytest.mark.asyncio
async def test_validate_reports_malformed_feature_flag_types():
    service = ExtremeService(ConfigDB({"automatic_lockdown": "false"}))
    errors = await service.validate(1)
    assert any("must be a boolean" in error for error in errors)


@pytest.mark.asyncio
async def test_due_reminders_can_reclaim_rows_with_null_claim_time():
    db = FakeDB()
    service = PlatformService(db)

    await service.due_reminders()

    sql = str(db.session_obj.statement.compile(dialect=postgresql.dialect()))
    assert "reminders.claimed_at IS NULL" in sql
