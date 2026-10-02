import base64
import json
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from bot.commands.greeting import Greeting
from bot.commands.text import TextCommands
from bot.services.guild_config import GuildConfigService
from bot.services.greeting import GreetingRenderer


def make_gif():
    image = Image.new('RGB', (8, 8), 'red')
    output = BytesIO()
    image.save(output, format='GIF')
    return output.getvalue()


def make_animated_gif():
    frames = [Image.new('RGB', (8, 8), color) for color in ('red', 'blue')]
    output = BytesIO()
    frames[0].save(output, format='GIF', save_all=True, append_images=frames[1:], duration=100, loop=0)
    return output.getvalue()


def test_greeting_embed_defaults_are_enabled_and_have_placeholders():
    from pathlib import Path
    src=Path('bot/services/guild_config.py').read_text()
    assert "welcome_embed_enabled':True" in src
    assert "goodbye_embed_enabled':True" in src
    assert "welcome_embed_description" in src
    assert "goodbye_embed_description" in src

def test_greeting_worker_sends_embed_with_banner_attachment():
    from pathlib import Path
    src=Path('bot/workers/greetings.py').read_text()
    assert "discord.Embed" in src
    assert "attachment://{filename}" in src
    assert "embed=embed" in src
    assert "file=discord.File(buf,filename=filename)" in src


@pytest.mark.asyncio
async def test_uploaded_gif_is_validated_and_can_be_rendered_from_bytes():
    data = make_gif()
    renderer = GreetingRenderer()

    assert renderer.validate_upload(data, 'image/gif') == data
    assert await renderer._background_bytes(data) == data
    encoded = 'base64:' + base64.b64encode(data).decode('ascii')
    assert await renderer._background_bytes(encoded) == data


def test_static_card_is_png_and_animated_background_stays_gif():
    renderer = GreetingRenderer()
    member = SimpleNamespace(
        mention='<@1>', display_name='Member', name='member',
        guild=SimpleNamespace(name='Server'),
    )
    avatar = Image.new('RGBA', renderer.AVATAR_SIZE, 'white')
    static = Image.new('RGB', (16, 16), 'green')
    static_bytes = BytesIO()
    static.save(static_bytes, format='PNG')
    static_card = renderer._render_sync(member, static_bytes.getvalue(), 'Welcome {name}', 1, avatar)
    animated_card = renderer._render_sync(member, make_animated_gif(), 'Welcome {name}', 1, avatar)

    assert GreetingRenderer.output_extension(static_card) == 'png'
    assert GreetingRenderer.output_extension(animated_card) == 'gif'
    with Image.open(animated_card) as result:
        assert result.n_frames == 2


def test_stored_banner_bytes_are_safe_for_json_cache():
    service = GuildConfigService(SimpleNamespace(), SimpleNamespace())
    created_at = datetime(2026, 10, 2, tzinfo=timezone.utc)
    encoded = service._cache_safe({'welcome_background_data': b'GIF89a', 'created_at': created_at})

    assert encoded['welcome_background_data'].startswith('base64:')
    assert encoded['created_at'] == created_at.isoformat()
    json.dumps(encoded)


@pytest.mark.asyncio
async def test_slash_greeting_message_is_saved():
    config = SimpleNamespace(update=AsyncMock())
    cog = Greeting(SimpleNamespace(guild_config=config))
    interaction = SimpleNamespace(
        guild_id=42,
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await Greeting.message.callback(cog, interaction, 'welcome', 'Welcome, {name}!')

    config.update.assert_awaited_once_with(42, welcome_message='Welcome, {name}!')


@pytest.mark.asyncio
async def test_slash_banner_upload_saves_gif_bytes():
    data = make_gif()
    attachment = SimpleNamespace(content_type='image/gif', read=AsyncMock(return_value=data))
    config = SimpleNamespace(update=AsyncMock())
    cog = Greeting(SimpleNamespace(guild_config=config, greetings=GreetingRenderer()))
    interaction = SimpleNamespace(
        guild_id=42,
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await Greeting.banner.callback(cog, interaction, 'welcome', attachment)

    config.update.assert_awaited_once_with(
        42,
        welcome_background='assets/welcome.gif',
        welcome_background_data=data,
    )


@pytest.mark.asyncio
async def test_prefix_banner_upload_saves_gif_bytes():
    data = make_gif()
    attachment = SimpleNamespace(content_type='image/gif', read=AsyncMock(return_value=data))
    config = SimpleNamespace(update=AsyncMock())
    cog = TextCommands(SimpleNamespace(guild_config=config, greetings=GreetingRenderer()))
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=42),
        send=AsyncMock(),
    )

    await TextCommands.greeting_banner.callback(cog, ctx, 'goodbye', attachment)

    config.update.assert_awaited_once_with(
        42,
        goodbye_background='assets/goodbye.gif',
        goodbye_background_data=data,
    )


@pytest.mark.asyncio
async def test_prefix_greeting_message_is_saved():
    config = SimpleNamespace(update=AsyncMock())
    cog = TextCommands(SimpleNamespace(guild_config=config))
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=42),
        send=AsyncMock(),
    )

    await TextCommands.greeting_message.callback(cog, ctx, 'goodbye', message='See you, {name}!')

    config.update.assert_awaited_once_with(42, goodbye_message='See you, {name}!')
