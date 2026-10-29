from types import SimpleNamespace

from bot.services.automod import AutoModService
from bot.services.greeting import GreetingRenderer


def test_greeting_template_rejects_huge_format_spec_without_expanding():
    member = SimpleNamespace(
        guild=SimpleNamespace(name="Server", id=1, premium_subscription_count=0, get_member=lambda _id: None, icon=None),
        mention="<@1>", display_name="User", name="user", created_at=None, joined_at=None,
        id=1, display_avatar=SimpleNamespace(url="https://example.invalid/avatar.png"),
    )
    rendered = GreetingRenderer.format_template(member, "{count:>999999999}", 3)
    assert len(rendered) <= 120
    assert "999999999" in rendered


def test_greeting_template_rejects_unknown_fields_and_bounds_expansion():
    member = SimpleNamespace(
        guild=SimpleNamespace(name="Server", id=1, premium_subscription_count=0, get_member=lambda _id: None, icon=None),
        mention="<@1>", display_name="U" * 2000, name="user", created_at=None, joined_at=None,
        id=1, display_avatar=SimpleNamespace(url=""),
    )
    rendered = GreetingRenderer.format_template(member, "{name}{unknown}", 1)
    assert len(rendered) <= 120


def test_automod_does_not_flag_a_single_simple_message_as_spam():
    service = AutoModService()
    assert service.check(1, 2, "Congratulations!") is False
    assert service.check(1, 2, "https://example.com") is False
    assert service.check(1, 3, "Hello everyone!!!") is False


def test_automod_still_flags_rate_based_flooding():
    service = AutoModService()
    assert [service.check(1, 2, "hello", limit=2, window=8) for _ in range(3)] == [False, False, True]
