import base64
import json
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import discord
from PIL import Image

from bot.commands.greeting import Greeting
from bot.commands.text import TextCommands
from bot.commands.greeting_prefix import GreetingPrefix
from bot.services.guild_config import GuildConfigService
from bot.services.greeting import GreetingRenderer
from bot.workers.greetings import GreetingWorker


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


def test_prefix_greeting_alias_is_on_text_surface_only():
    greeting_source = __import__('pathlib').Path('bot/commands/greeting.py').read_text()
    prefix_source = __import__('pathlib').Path('bot/commands/greeting_prefix.py').read_text()
    text_source = __import__('pathlib').Path('bot/commands/text.py').read_text()
    assert "name='greet'" not in greeting_source
    assert "name='greeting', aliases=['greet']" in prefix_source
    assert "name='greeting', aliases=['greet']" not in text_source


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
    assert "file=discord.File(BytesIO(rendered), filename=filename)" in src


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

    # Binary greeting media is intentionally excluded from the Redis JSON cache.
    assert encoded['welcome_background_data'] is None
    assert encoded['created_at'] == created_at.isoformat()
    json.dumps(encoded)


@pytest.mark.asyncio
async def test_slash_greeting_image_url_is_saved():
    config = SimpleNamespace(
        get=AsyncMock(return_value={"welcome_settings": {}}),
        update=AsyncMock(),
    )
    cog = Greeting(SimpleNamespace(guild_config=config))
    interaction = SimpleNamespace(
        guild_id=42,
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await Greeting.set_image.callback(cog, interaction, 'welcome', 'https://example.com/banner.gif')

    config.update.assert_awaited_once_with(
        42, welcome_settings={"welcome_image_url": "https://example.com/banner.gif"}
    )


@pytest.mark.asyncio
async def test_greeting_toggle_persists_in_supported_settings_json():
    config = SimpleNamespace(
        get=AsyncMock(return_value={"welcome_settings": {}}),
        update=AsyncMock(),
    )
    cog = Greeting(SimpleNamespace(guild_config=config))
    interaction = SimpleNamespace(
        guild_id=42,
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await Greeting.toggle.callback(cog, interaction, "welcome", False)
    config.update.assert_awaited_once_with(42, welcome_settings={"enabled": False})


@pytest.mark.asyncio
async def test_goodbye_toggle_persists_in_supported_settings_json():
    config = SimpleNamespace(
        get=AsyncMock(return_value={"welcome_settings": {}}),
        update=AsyncMock(),
    )
    cog = Greeting(SimpleNamespace(guild_config=config))
    interaction = SimpleNamespace(
        guild_id=42,
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await Greeting.toggle.callback(cog, interaction, "goodbye", False)
    config.update.assert_awaited_once_with(42, welcome_settings={"goodbye_enabled": False})


@pytest.mark.asyncio
async def test_slash_greeting_embed_toggle_is_saved():
    config = SimpleNamespace(update=AsyncMock())
    cog = Greeting(SimpleNamespace(guild_config=config))
    interaction = SimpleNamespace(
        guild_id=42,
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await Greeting.toggle_embed.callback(cog, interaction, 'welcome', False)

    config.update.assert_awaited_once_with(42, welcome_embed_enabled=False)


@pytest.mark.asyncio
async def test_prefix_banner_upload_saves_gif_bytes():
    data = make_gif()
    attachment = SimpleNamespace(content_type='image/gif', read=AsyncMock(return_value=data))
    config = SimpleNamespace(update=AsyncMock())
    cog = GreetingPrefix(SimpleNamespace(guild_config=config, greetings=GreetingRenderer()))
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=42),
        send=AsyncMock(),
    )

    await GreetingPrefix.greeting_banner.callback(cog, ctx, 'goodbye', attachment)

    config.update.assert_awaited_once_with(
        42,
        goodbye_background='assets/goodbye.gif',
        goodbye_background_data=data,
    )


@pytest.mark.asyncio
async def test_prefix_greeting_message_is_saved():
    config = SimpleNamespace(update=AsyncMock())
    cog = GreetingPrefix(SimpleNamespace(guild_config=config))
    ctx = SimpleNamespace(
        guild=SimpleNamespace(id=42),
        send=AsyncMock(),
    )

    await GreetingPrefix.greeting_message.callback(cog, ctx, 'goodbye', message='See you, {name}!')

    config.update.assert_awaited_once_with(42, goodbye_message='See you, {name}!')


@pytest.mark.asyncio
async def test_forced_welcome_test_bypasses_normal_dedupe_and_delivery_settings():
    me = SimpleNamespace(id=99)
    permissions = SimpleNamespace(view_channel=True, send_messages=True, attach_files=True, embed_links=True)
    channel = SimpleNamespace(permissions_for=MagicMock(return_value=permissions))
    guild = SimpleNamespace(
        id=42, name="Test Server", member_count=3, me=me, icon=None,
        get_member=MagicMock(return_value=None),
    )
    member = SimpleNamespace(id=7, bot=False, guild=guild)
    config = SimpleNamespace(get=AsyncMock(return_value={
        "welcome_embed_enabled": True,
        "welcome_message": "Welcome!",
        "welcome_background": "assets/welcome.gif",
        "welcome_background_data": None,
    }))
    welcome = SimpleNamespace(
        get=AsyncMock(return_value={
            "public_enabled": False, "dm_enabled": False, "dedupe_seconds": 90,
            "retry_attempts": 0, "retry_backoff": 0.1, "show_details": False,
        }),
        should_deliver=MagicMock(return_value=False),
        claim=MagicMock(return_value=False),
        risk=MagicMock(return_value=None),
        apply_roles=AsyncMock(return_value=0),
        alert=AsyncMock(return_value=False),
    )
    greetings = SimpleNamespace(
        render=AsyncMock(return_value=BytesIO(b"image")),
        output_extension=MagicMock(return_value="png"),
    )
    bot = SimpleNamespace(
        guild_config=config,
        welcome_engine=welcome,
        greetings=greetings,
        log=SimpleNamespace(info=MagicMock(), warning=MagicMock()),
    )
    worker = GreetingWorker(bot)
    worker._build_embed = lambda *args, **kwargs: None
    worker._send_public = AsyncMock()

    delivered = await worker.deliver(member, "welcome", force_channel=channel)

    assert delivered is True
    welcome.should_deliver.assert_not_called()
    welcome.claim.assert_not_called()
    worker._send_public.assert_awaited_once()


@pytest.mark.asyncio
async def test_disabled_goodbye_is_not_delivered():
    cfg = {"welcome_settings": {"goodbye_enabled": False}}
    bot = SimpleNamespace(
        guild_config=SimpleNamespace(get=AsyncMock(return_value=cfg)),
        welcome_engine=SimpleNamespace(get=AsyncMock(return_value={"goodbye_enabled": False})),
        greetings=SimpleNamespace(render=AsyncMock()),
        log=SimpleNamespace(info=MagicMock(), warning=MagicMock()),
    )
    worker = GreetingWorker(bot)
    member = SimpleNamespace(guild=SimpleNamespace(id=42))

    delivered = await worker.deliver(member, "goodbye")

    assert delivered is False
    bot.greetings.render.assert_not_awaited()


@pytest.mark.asyncio
async def test_plain_text_greeting_mode_sends_message_content():
    guild = SimpleNamespace(
        id=42, member_count=3, name="Test Server", icon=None, me=None,
        get_member=MagicMock(return_value=None),
    )
    member = SimpleNamespace(
        id=7, bot=False, guild=guild, mention="<@7>", display_name="Member",
        name="member", created_at=discord.utils.utcnow(), joined_at=None,
        display_avatar=None,
    )
    channel = SimpleNamespace(permissions_for=MagicMock(return_value=SimpleNamespace(
        view_channel=True, send_messages=True, attach_files=True, embed_links=True,
    )))
    cfg = {
        "welcome_embed_enabled": False,
        "welcome_message": "Welcome {mention}!",
        "welcome_background": None,
        "welcome_background_data": None,
    }
    welcome = SimpleNamespace(
        get=AsyncMock(return_value={
            "enabled": True, "public_enabled": True, "dm_enabled": False,
            "buttons": [], "dedupe_seconds": 90, "show_details": False,
        }),
        should_deliver=MagicMock(return_value=True),
        claim=MagicMock(return_value=True),
        risk=MagicMock(return_value=None),
        apply_roles=AsyncMock(return_value=0),
        alert=AsyncMock(return_value=False),
    )
    greetings = SimpleNamespace(
        render=AsyncMock(return_value=BytesIO(b"image")),
        output_extension=MagicMock(return_value="png"),
    )
    bot = SimpleNamespace(
        guild_config=SimpleNamespace(get=AsyncMock(return_value=cfg)),
        welcome_engine=welcome,
        greetings=greetings,
        log=SimpleNamespace(info=MagicMock(), warning=MagicMock()),
    )
    worker = GreetingWorker(bot)
    worker._send_public = AsyncMock()

    delivered = await worker.deliver(
        member, "welcome", force_channel=channel, test_mode=True
    )

    assert delivered is True
    assert worker._send_public.await_args.kwargs["content"] == "Welcome <@7>!"
    assert worker._send_public.await_args.kwargs["embed"] is None


@pytest.mark.asyncio
async def test_greeting_reset_uses_existing_columns_and_json_settings():
    config = SimpleNamespace(
        get=AsyncMock(return_value={"welcome_settings": {"custom_option": "keep"}}),
        update=AsyncMock(),
    )
    cog = Greeting(SimpleNamespace(guild_config=config))
    interaction = SimpleNamespace(
        guild_id=42,
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await Greeting.reset.callback(cog, interaction, "goodbye")

    kwargs = config.update.await_args.kwargs
    assert config.update.await_args.args == (42,)
    assert kwargs["goodbye_message"] == "Goodbye {name}!"
    assert kwargs["goodbye_embed_title"] == "Goodbye!"
    assert kwargs["goodbye_embed_color"] == 0x95A5A6
    assert kwargs["welcome_settings"]["custom_option"] == "keep"
    assert kwargs["welcome_settings"]["goodbye_enabled"] is True
    assert kwargs["welcome_settings"]["goodbye_image_url"] == ""
    assert kwargs["welcome_settings"]["goodbye_footer_text"] == "User ID: {user_id}"


def test_worker_uses_saved_custom_image_and_footer_options():
    guild = SimpleNamespace(
        id=42, name="Test Server", icon=None, premium_subscription_count=0,
        get_member=MagicMock(return_value=None),
    )
    member = SimpleNamespace(
        id=7, guild=guild, mention="<@7>", display_name="Member", name="member",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), joined_at=None,
        display_avatar=SimpleNamespace(url="https://example.com/avatar.png"),
    )
    worker = GreetingWorker(SimpleNamespace())
    embed = worker._build_embed(
        {"welcome_embed_enabled": True, "welcome_embed_title": "Hello", "welcome_embed_description": "Welcome"},
        {
            "welcome_image_url": "https://example.com/custom.gif",
            "welcome_footer_text": "User {user_id} on {server}",
            "welcome_show_thumbnail": False,
            "welcome_show_footer": True,
            "show_details": False,
            "show_joined_at": False,
            "show_account_created": False,
            "show_inviter": False,
            "show_risk": False,
        },
        member, "welcome", 3, None, 0, "welcome.png",
    )

    assert embed.image.url == "https://example.com/custom.gif"
    assert embed.footer.text == "User 7 on Test Server"
    assert embed.thumbnail.url is None


@pytest.mark.asyncio
async def test_slash_greeting_image_rejects_non_url_without_saving():
    config = SimpleNamespace(
        get=AsyncMock(return_value={"welcome_settings": {}}),
        update=AsyncMock(),
    )
    response = SimpleNamespace(send_message=AsyncMock())
    cog = Greeting(SimpleNamespace(guild_config=config))
    interaction = SimpleNamespace(guild_id=42, response=response)

    await Greeting.set_image.callback(cog, interaction, "welcome", "not a URL")

    config.update.assert_not_awaited()
    response.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_welcome_reports_missing_view_channel_permission():
    me = SimpleNamespace(id=99)
    permissions = SimpleNamespace(
        view_channel=False, send_messages=True, attach_files=True, embed_links=True
    )
    channel = SimpleNamespace(
        mention="#welcome",
        permissions_for=MagicMock(return_value=permissions),
    )
    guild = SimpleNamespace(
        id=42, name="Test Server", member_count=3, me=me, icon=None,
        get_member=MagicMock(return_value=None),
    )
    member = SimpleNamespace(id=7, bot=False, guild=guild)
    config = SimpleNamespace(get=AsyncMock(return_value={
        "welcome_embed_enabled": False,
        "welcome_message": "Welcome!",
        "welcome_background": None,
        "welcome_background_data": None,
    }))
    welcome = SimpleNamespace(
        get=AsyncMock(return_value={
            "public_enabled": True, "dm_enabled": False, "dedupe_seconds": 90,
            "retry_attempts": 0, "retry_backoff": 0.1, "show_details": False,
        }),
        should_deliver=MagicMock(return_value=True),
        claim=MagicMock(return_value=True),
        risk=MagicMock(return_value=None),
        apply_roles=AsyncMock(return_value=0),
        alert=AsyncMock(return_value=False),
    )
    greetings = SimpleNamespace(
        render=AsyncMock(return_value=BytesIO(b"image")),
        output_extension=MagicMock(return_value="png"),
    )
    bot = SimpleNamespace(
        guild_config=config,
        welcome_engine=welcome,
        greetings=greetings,
        log=SimpleNamespace(info=MagicMock(), warning=MagicMock()),
    )
    worker = GreetingWorker(bot)
    worker._build_embed = lambda *args, **kwargs: None
    worker._send_public = AsyncMock()

    with pytest.raises(ValueError, match="View Channel"):
        await worker.deliver(member, "welcome", force_channel=channel)

    worker._send_public.assert_not_awaited()
