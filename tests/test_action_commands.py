from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.commands.fun import SAFE_ACTIONS
from bot.commands.text import TextCommands
from bot.services.reactions import ReactionGifService


def test_prefix_is_comma_only():
    src = Path('bot/core/config.py').read_text()
    assert "command_prefix:str=','" in src


def test_required_action_commands_exist_in_slash_surface():
    src = Path('bot/commands/fun.py').read_text()
    for name in ('hug','highfive','pat','poke','slap','bite','tickle','hold','boop','wave','punch','attack','shoot','bully','cry','dance','blush','smile','pout','shrug','sleep','fuck'):
        assert f"name='{name}'" in src


def test_required_action_commands_exist_in_prefix_surface():
    src = Path('bot/commands/text.py').read_text()
    for name in ('hug','highfive','pat','poke','slap','bite','tickle','hold','boop','wave','punch','attack','shoot','bully','cry','dance','blush','smile','pout','shrug','sleep','fuck'):
        assert f"name='{name}'" in src or f'name="{name}"' in src


def test_fuck_action_is_non_sexual():
    src = Path('bot/commands/fun.py').read_text().lower()
    assert 'non-sexual' in src


def test_every_action_has_gif_key():
    src = Path('bot/commands/fun.py').read_text()
    for name in ('hug','highfive','pat','poke','slap','bite','tickle','hold','boop','wave','kill','punch','attack','shoot','bully','cry','dance','blush','smile','pout','shrug','sleep','fuck'):
        line = next(x for x in src.splitlines() if f"'{name}':" in x)
        assert "(None," not in line


@pytest.mark.asyncio
async def test_every_prefix_action_attaches_its_gif():
    gif_url = 'https://example.com/action.gif'
    reactions = SimpleNamespace(get=AsyncMock(return_value=gif_url))
    cog = TextCommands(SimpleNamespace(reactions=reactions))
    commands = {command.name: command for command in cog.get_commands()}
    author = SimpleNamespace(id=1, mention='<@1>')
    member = SimpleNamespace(id=2, mention='<@2>')

    for action, (gif_key, _, _) in SAFE_ACTIONS.items():
        ctx = SimpleNamespace(author=author, send=AsyncMock(), prefix=',')
        await commands[action].callback(cog, ctx, member)

        reactions.get.assert_awaited_with(gif_key)
        embed = ctx.send.await_args.kwargs['embed']
        assert embed.image.url == gif_url


def test_grouped_and_standalone_levelrole_commands_are_registered():
    cog = TextCommands(SimpleNamespace())
    commands = {command.name: command for command in cog.get_commands()}

    assert 'levelrole' in commands
    assert 'remove' in {command.name for command in commands['levelrole'].commands}
    assert 'levelrole-remove' in commands


class FakeGifResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self):
        return self.data


class FakeGifSession:
    closed = False

    def __init__(self, responses):
        self.calls = []
        self.responses = iter(responses)

    def get(self, url, params=None):
        self.calls.append((url, params))
        return next(self.responses)

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_gif_service_parses_provider_urls_and_supported_aliases():
    service = ReactionGifService()
    session = FakeGifSession([
        FakeGifResponse({'url': 'https://example.com/action.gif'})
        for _ in range(4)
    ])
    service._session = session

    for action in ('hug', 'highfive', 'bonk', 'boop', 'hold'):
        assert await service.get(action) == 'https://example.com/action.gif'

    assert session.calls == [
        ('https://api.otakugifs.xyz/gif', {'reaction': 'hug'}),
        ('https://api.otakugifs.xyz/gif', {'reaction': 'wave'}),
        ('https://api.otakugifs.xyz/gif', {'reaction': 'punch'}),
        ('https://api.otakugifs.xyz/gif', {'reaction': 'poke'}),
    ]


@pytest.mark.asyncio
async def test_giphy_provider_is_used_when_configured():
    service = ReactionGifService(giphy_api_key='giphy-key')
    session = FakeGifSession([
        FakeGifResponse({'data': [{'images': {'original': {'url': 'https://giphy.com/action.gif'}}}]})
    ])
    service._session = session

    assert await service.get('hug') == 'https://giphy.com/action.gif'
    assert session.calls == [(
        service.GIPHY_URL,
        {'api_key': 'giphy-key', 'q': 'anime hug reaction', 'limit': 10, 'rating': 'pg'},
    )]


@pytest.mark.asyncio
async def test_tenor_and_existing_provider_are_fallbacks():
    service = ReactionGifService(giphy_api_key='giphy-key', tenor_api_key='tenor-key')
    session = FakeGifSession([
        FakeGifResponse({}, status=403),
        FakeGifResponse({'results': [{'media_formats': {'gif': {'url': 'https://tenor.com/action.gif'}}}]}),
    ])
    service._session = session

    assert await service.get('hug') == 'https://tenor.com/action.gif'
    assert [url for url, _ in session.calls] == [service.GIPHY_URL, service.TENOR_URL]

    service = ReactionGifService(giphy_api_key='giphy-key', tenor_api_key='tenor-key')
    session = FakeGifSession([
        FakeGifResponse({}, status=403),
        FakeGifResponse({}, status=403),
        FakeGifResponse({'url': 'https://otakugifs.xyz/action.gif'}),
    ])
    service._session = session

    assert await service.get('hug') == 'https://otakugifs.xyz/action.gif'
    assert [url for url, _ in session.calls] == [
        service.GIPHY_URL, service.TENOR_URL, service.OTAKU_GIFS_URL,
    ]
