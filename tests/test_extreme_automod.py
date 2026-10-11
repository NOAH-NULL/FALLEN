from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.core.bot import Bot
from bot.services.v16_runtime import V16Runtime


class FakeExtreme:
    def __init__(self, rules, settings=None):
        self.rules = rules
        self.settings = settings or {
            "regex_rules": True,
            "domain_blacklist": True,
            "domain_whitelist": False,
            "flood_detection": False,
            "duplicate_messages": False,
            "emoji_spam": False,
            "mention_spam": False,
        }
        self.record_security = AsyncMock()

    async def get(self, _guild_id):
        return dict(self.settings)

    async def automod_rules(self, _guild_id):
        return list(self.rules)


def make_message(content):
    return SimpleNamespace(
        guild=SimpleNamespace(id=123),
        author=SimpleNamespace(id=456, bot=False, roles=[]),
        channel=SimpleNamespace(id=789),
        id=999,
        content=content,
        mentions=[],
        role_mentions=[],
        delete=AsyncMock(),
        reply=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_custom_regex_rule_returns_its_configured_action():
    rule = SimpleNamespace(
        enabled=True, kind="regex", pattern="badword", name="test-word", action="log"
    )
    runtime = V16Runtime(SimpleNamespace(extreme=FakeExtreme([rule])))
    message = make_message("this contains BADWORD")

    matches = await runtime.custom_rule_matches(message)

    assert len(matches) == 1
    assert matches[0][0].action == "log"
    assert matches[0][1] == "regex:test-word"


@pytest.mark.asyncio
async def test_domain_blacklist_matches_subdomains_and_keeps_action():
    rule = SimpleNamespace(
        enabled=True, kind="domain_blacklist", pattern="bad.example", name="blocked", action="warn"
    )
    settings = {
        "regex_rules": False, "domain_blacklist": True, "domain_whitelist": False,
    }
    runtime = V16Runtime(SimpleNamespace(extreme=FakeExtreme([rule], settings)))
    message = make_message("visit https://sub.bad.example/path")

    matches = await runtime.custom_rule_matches(message)

    assert len(matches) == 1
    assert matches[0][0].action == "warn"
    assert matches[0][1] == "domain_blacklist:blocked"


@pytest.mark.asyncio
async def test_pathological_regex_is_timed_out_instead_of_blocking_worker():
    rule = SimpleNamespace(
        enabled=True, kind="regex", pattern="^(a|aa)+$", name="slow-pattern", action="delete"
    )
    runtime = V16Runtime(SimpleNamespace(extreme=FakeExtreme([rule])))
    message = make_message("a" * 5000 + "!")

    matches = await runtime.custom_rule_matches(message)

    assert matches == []


def make_processing_bot(rule):
    guild_config = SimpleNamespace(get=AsyncMock(return_value={}))
    uwuify = SimpleNamespace(transform_message=AsyncMock(return_value=None))
    v16 = SimpleNamespace(
        message_check=AsyncMock(return_value=[]),
        custom_rule_matches=AsyncMock(return_value=[(rule, "regex:configured-rule")]),
    )
    levels = SimpleNamespace(eligible=AsyncMock(return_value=(False, {})))
    bot = SimpleNamespace(
        command_prefix=",",
        guild_config=guild_config,
        uwuify=uwuify,
        v16=v16,
        automod=SimpleNamespace(check=lambda *args, **kwargs: False),
        levels=levels,
        extreme=SimpleNamespace(record_security=AsyncMock()),
    )
    return bot


@pytest.mark.asyncio
async def test_warn_action_warns_without_deleting_message():
    message = make_message("trigger")
    rule = SimpleNamespace(action="warn")
    await Bot.process_message(make_processing_bot(rule), message)

    message.reply.assert_awaited_once()
    message.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_log_action_records_match_without_deleting_message():
    message = make_message("trigger")
    rule = SimpleNamespace(action="log")
    bot = make_processing_bot(rule)
    await Bot.process_message(bot, message)

    message.delete.assert_not_awaited()
    bot.extreme.record_security.assert_awaited_once()
    assert bot.extreme.record_security.await_args.args[1] == "automod_rule_match"


@pytest.mark.asyncio
async def test_delete_action_deletes_message():
    message = make_message("trigger")
    rule = SimpleNamespace(action="delete")
    await Bot.process_message(make_processing_bot(rule), message)

    message.delete.assert_awaited_once()
    message.reply.assert_not_awaited()
