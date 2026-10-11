import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from bot.commands.rules import Rules, RulesPanelView


def test_rules_embed_uses_admin_supplied_content_and_all_rules():
    panel = {
        "title": "A custom title",
        "description": "An admin-written description.",
        "rules": [
            {"title": "Be respectful", "text": "Treat members fairly."},
            {"title": "Keep channels relevant", "text": "Use the right channel."},
            {"title": "A fully custom rule", "text": "This content is not predefined."},
        ],
        "buttons": [],
        "image_url": None,
        "image_filename": None,
    }
    embed = Rules._embed(panel)
    assert embed.title == "A custom title"
    assert "An admin-written description." in embed.description
    assert "**1. Be respectful**" in embed.description
    assert "**3. A fully custom rule**" in embed.description
    assert "This content is not predefined." in embed.description


def test_rules_panel_has_standard_companion_embed():
    embed = Rules._companion_embed({})
    assert embed.title == "Rules & Access"
    assert "Please read the rules in the panel above" in embed.description
    assert "**Role buttons**" in embed.description
    assert "**Need help?**" in embed.description
    assert embed.footer.text == "FALLEN • Server information"



def test_rules_reply_sends_initial_response_without_recursion():
    interaction = SimpleNamespace(
        response=SimpleNamespace(is_done=lambda: False, send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )
    rules = Rules(bot=None)

    asyncio.run(rules._reply(interaction, "ok", ephemeral=True))

    interaction.response.send_message.assert_awaited_once_with("ok", ephemeral=True)
    interaction.followup.send.assert_not_awaited()

def test_rules_panel_has_exactly_four_buttons_and_unconfigured_slots_are_disabled():
    panel = {
        "buttons": [
            {"label": "Custom One", "role_id": 123},
            {"label": "Button 2", "role_id": None},
            {"label": "Custom Three", "role_id": 456},
            {"label": "Button 4", "role_id": None},
        ]
    }
    cog = SimpleNamespace(bot=SimpleNamespace(log=SimpleNamespace(exception=lambda *a, **k: None)))
    view = RulesPanelView(cog, 987, panel)
    assert len(view.children) == 4
    assert [item.label for item in view.children] == ["Custom One", "Button 2", "Custom Three", "Button 4"]
    assert [item.disabled for item in view.children] == [False, True, False, True]
    assert [item.custom_id for item in view.children] == [
        "fallen:rules:987:1", "fallen:rules:987:2",
        "fallen:rules:987:3", "fallen:rules:987:4",
    ]


def test_rules_embed_rejects_discord_description_overflow():
    panel = {
        "title": "Too much text",
        "description": "x" * 3000,
        "rules": [{"title": "Large rule", "text": "y" * 1100}],
        "buttons": [],
    }
    try:
        Rules._embed(panel)
    except ValueError as exc:
        assert "4,096-character" in str(exc)
    else:
        raise AssertionError("oversized embed should be rejected")
