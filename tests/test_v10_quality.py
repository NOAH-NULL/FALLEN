from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.commands.fun import Fun, SAFE_ACTIONS


def test_hybrid_commands_are_available_in_both_prefix_and_slash_surfaces():
    cog = Fun(SimpleNamespace(reactions=SimpleNamespace(get=AsyncMock(return_value=None))))
    prefix_names = {command.name for command in cog.get_commands()}
    slash_names = {command.name for command in cog.get_app_commands()}
    expected = {"hug", "highfive", "pat", "poke", "bonk", "wave", "dance", "smile", "cry", "shrug", "sleep", "boop", "tickle", "punch"}
    assert expected <= prefix_names
    assert expected <= slash_names


def test_reaction_surface_has_bounded_http_and_provider_caches():
    src = Path("bot/services/reactions.py").read_text()
    assert "_failure_cache" in src
    assert "_gif_pool" in src
    assert "_provider_backoff" in src
    assert "asyncio.Lock" in src
    assert "ClientTimeout(total=3.0, connect=1.0)" in src
    assert "_mark_provider_failed" in src


def test_action_surface_uses_shared_safe_action_registry():
    cog = Fun(SimpleNamespace(reactions=SimpleNamespace(get=AsyncMock(return_value=None))))
    names = {command.name for command in cog.get_commands()}
    assert set(SAFE_ACTIONS) <= names
    assert "fuck" not in names


def test_release_excludes_runtime_artifacts():
    ignore = Path(".gitignore").read_text() + Path(".dockerignore").read_text()
    assert "__pycache__/" in ignore
    assert "*.pyc" in ignore
    assert ".pytest_cache/" in ignore
