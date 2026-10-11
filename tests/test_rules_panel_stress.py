"""100-case regression matrix for rules-panel content and persistent buttons."""

from types import SimpleNamespace

import pytest

from bot.commands.rules import Rules, RulesPanelView


@pytest.mark.parametrize("case", range(100))
def test_rules_panel_content_and_button_state_matrix(case):
    """Exercise 100 distinct admin-configured panels without Discord/network calls."""
    title = f"Server rules {case:03d}"
    description = f"Custom description for case {case:03d}."
    rule_title = f"Rule {case:03d}"
    rule_text = f"Admin-defined rule text for case {case:03d}."

    panel = {
        "title": title,
        "description": description,
        "rules": [{"title": rule_title, "text": rule_text}],
        "buttons": [
            {"label": f"Role {case:03d}", "role_id": 10000 + case},
            {"label": "Button 2", "role_id": None},
            {"label": f"Extra {case:03d}", "role_id": 20000 + case},
            {"label": "Button 4", "role_id": None},
        ],
        "image_url": None,
        "image_filename": None,
    }

    embed = Rules._embed(panel)
    assert embed.title == title
    assert description in embed.description
    assert f"**1. {rule_title}**" in embed.description
    assert rule_text in embed.description

    cog = SimpleNamespace(
        bot=SimpleNamespace(log=SimpleNamespace(exception=lambda *args, **kwargs: None))
    )
    view = RulesPanelView(cog, 50000 + case, panel)
    assert len(view.children) == 4
    assert [button.disabled for button in view.children] == [False, True, False, True]
    assert [button.custom_id for button in view.children] == [
        f"fallen:rules:{50000 + case}:1",
        f"fallen:rules:{50000 + case}:2",
        f"fallen:rules:{50000 + case}:3",
        f"fallen:rules:{50000 + case}:4",
    ]
    assert view.children[0].label == f"Role {case:03d}"
    assert view.children[2].label == f"Extra {case:03d}"
