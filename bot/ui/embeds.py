import discord

COLOURS = {
    'success': discord.Colour.green(),
    'error': discord.Colour.red(),
    'warning': discord.Colour.orange(),
    'info': discord.Colour.blurple(),
    'moderation': discord.Colour.from_rgb(237, 93, 93),
    'security': discord.Colour.from_rgb(170, 62, 255),
}


def _base(title: str, description: str, kind: str = 'info') -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        colour=COLOURS.get(kind, COLOURS['info']),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text='Fallen • Intelligent server protection')
    return embed


def success_embed(title: str, description: str) -> discord.Embed:
    return _base(f'✓ {title}', description, 'success')


def error_embed(title: str, description: str) -> discord.Embed:
    return _base(f'✕ {title}', description, 'error')


def warning_embed(title: str, description: str) -> discord.Embed:
    return _base(f'⚠ {title}', description, 'warning')


def info_embed(title: str, description: str, *, thumbnail: str | None = None) -> discord.Embed:
    embed = _base(title, description, 'info')
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed


def command_embed(title: str, description: str, *, kind: str = 'info', thumbnail: str | None = None) -> discord.Embed:
    embed = _base(title, description, kind)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed
