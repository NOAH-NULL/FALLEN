from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.commands.fun import Fun, SAFE_ACTIONS
from bot.commands.text import TextCommands
from bot.services.reactions import ReactionGifService


EXPECTED_ACTIONS = (
    "hug", "highfive", "fistbump", "pat", "poke", "bonk", "wave",
    "dance", "smile", "cry", "shrug", "sleep", "boop", "tickle",
    "punch", "slap", "bite", "hold", "attack", "shoot", "bully",
    "pout", "blush", "kill", "wreck", "kiss", "flirt",
)


def test_prefix_is_comma_only():
    src = Path("bot/core/config.py").read_text()
    assert "command_prefix:str=','" in src


def test_social_actions_are_registered_as_hybrid_commands():
    cog = Fun(SimpleNamespace(reactions=SimpleNamespace(get=AsyncMock(return_value=None))))
    prefix_names = {command.name for command in cog.get_commands()}
    slash_names = {command.name for command in cog.get_app_commands()}
    assert set(EXPECTED_ACTIONS) <= prefix_names
    assert set(EXPECTED_ACTIONS) <= slash_names


def test_explicit_sexual_action_is_not_exposed_in_sfw_command_surface():
    src = Path("bot/commands/fun.py").read_text().lower()
    assert "fuck" not in SAFE_ACTIONS
    assert 'name="fuck"' not in src
    assert "'fuck': 'fuck'" not in Path("bot/services/reactions.py").read_text()


def test_every_action_has_a_gif_key():
    for name, (gif_key, _emoji, _verb, _reciprocate) in SAFE_ACTIONS.items():
        assert gif_key, f"{name} must map to a GIF key"


@pytest.mark.asyncio
async def test_every_hybrid_action_attaches_its_gif():
    gif_url = "https://example.com/action.gif"
    reactions = SimpleNamespace(get=AsyncMock(return_value=gif_url))
    cog = Fun(SimpleNamespace(reactions=reactions))
    commands = {command.name: command for command in cog.get_commands()}
    author = SimpleNamespace(id=1, mention="<@1>")
    member = SimpleNamespace(id=2, mention="<@2>")

    for action in EXPECTED_ACTIONS:
        ctx = SimpleNamespace(author=author, send=AsyncMock(), prefix=",")
        await commands[action].callback(cog, ctx, member)
        embed = ctx.send.await_args.kwargs["embed"]
        assert embed.image.url == gif_url
    assert reactions.get.await_count == len(EXPECTED_ACTIONS)


def test_grouped_and_standalone_levelrole_commands_are_registered():
    cog = TextCommands(SimpleNamespace())
    commands = {command.name: command for command in cog.get_commands()}
    assert "levelrole" in commands
    assert "remove" in {command.name for command in commands["levelrole"].commands}
    assert "levelrole-remove" in commands


class FakeGifResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def json(self):
        return self.data


class FakeGifSession:
    closed = False

    def __init__(self, responses):
        self.calls = []
        self.responses = responses

    def get(self, url, params=None):
        self.calls.append((url, params))
        return self.responses[url]

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_gif_service_aliases_and_free_provider():
    service = ReactionGifService()
    session = FakeGifSession({
        service.OTAKU_GIFS_URL: FakeGifResponse({"url": "https://example.com/action.gif"}),
    })
    service._session = session

    for action in ("hug", "highfive", "bonk", "boop", "hold"):
        assert await service.get(action) == "https://example.com/action.gif"

    reactions = [params["reaction"] for url, params in session.calls if url == service.OTAKU_GIFS_URL]
    assert reactions == ["hug", "wave", "punch", "poke", "hug"]


@pytest.mark.asyncio
async def test_configured_giphy_provider_is_used():
    service = ReactionGifService(giphy_api_key="giphy-key")
    session = FakeGifSession({
        service.OTAKU_GIFS_URL: FakeGifResponse({}, status=403),
        service.GIPHY_URL: FakeGifResponse({
            "data": [{"images": {"original": {"url": "https://giphy.com/action.gif"}}}],
        }),
    })
    service._session = session

    assert await service.get("hug") == "https://giphy.com/action.gif"
    giphy_calls = [params for url, params in session.calls if url == service.GIPHY_URL]
    assert giphy_calls == [{
        "api_key": "giphy-key",
        "q": "anime hug reaction",
        "limit": 15,
        "rating": "pg",
    }]
    assert "otakugifs" in service._provider_backoff


@pytest.mark.asyncio
async def test_tenor_and_otakugifs_are_fallback_providers():
    service = ReactionGifService(giphy_api_key="giphy-key", tenor_api_key="tenor-key")
    session = FakeGifSession({
        service.OTAKU_GIFS_URL: FakeGifResponse({}, status=403),
        service.TENOR_URL: FakeGifResponse({
            "results": [{"media_formats": {"gif": {"url": "https://tenor.com/action.gif"}}}],
        }),
        service.GIPHY_URL: FakeGifResponse({}, status=403),
    })
    service._session = session

    assert await service.get("hug") == "https://tenor.com/action.gif"
    assert {url for url, _ in session.calls} == {
        service.OTAKU_GIFS_URL, service.TENOR_URL, service.GIPHY_URL,
    }
