"""Regression tests for high-risk V16 service behavior."""

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from bot.models import Playlist
from bot.services.extreme import IMPLEMENTED_FEATURES, ExtremeService


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
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
