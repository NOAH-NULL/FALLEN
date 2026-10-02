import discord
from discord import app_commands
from discord.ext import commands


KIND_CHOICES = [
    app_commands.Choice(name='Welcome', value='welcome'),
    app_commands.Choice(name='Goodbye', value='goodbye'),
]


class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    group = app_commands.Group(name='greeting', description='Configure welcome and goodbye')

    async def _save(self, guild_id, **values):
        await self.bot.guild_config.update(guild_id, **values)

    @group.command(name='channel')
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel(self, i, kind: str, channel: discord.TextChannel):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        await self._save(i.guild_id, **{f'{kind}_channel_id': channel.id})
        await i.response.send_message(f'{kind.title()} channel set to {channel.mention}.')

    @group.command(name='message')
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, i, kind: str, text_value: str):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        await self._save(i.guild_id, **{f'{kind}_message': text_value[:1000]})
        await i.response.send_message('Saved.')

    @group.command(name='banner')
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def banner(self, i, kind: str, attachment: discord.Attachment = None, url: str = None):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        if attachment:
            try:
                data = self.bot.greetings.validate_upload(await attachment.read(), attachment.content_type)
            except ValueError as exc:
                return await i.response.send_message(str(exc), ephemeral=True)
            await self._save(
                i.guild_id,
                **{f'{kind}_background': f'assets/{kind}.gif', f'{kind}_background_data': data},
            )
        elif url and url.strip().startswith(('https://', 'http://')):
            await self._save(
                i.guild_id,
                **{f'{kind}_background': url.strip()[:2000], f'{kind}_background_data': None},
            )
        else:
            return await i.response.send_message('Upload an image/GIF or provide an image URL.', ephemeral=True)
        await i.response.send_message(f'Custom {kind} banner saved. GIFs remain animated.')

    @group.command(name='banner-reset')
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def banner_reset(self, i, kind: str):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        await self._save(
            i.guild_id,
            **{f'{kind}_background': f'assets/{kind}.gif', f'{kind}_background_data': None},
        )
        await i.response.send_message(f'{kind.title()} banner reset to the default.')

    @group.command(name='embed')
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(kind='welcome or goodbye', enabled='Show the embed alongside the banner', title='Embed title', description='Embed description', color='Hex color such as #5865F2')
    async def embed(self, i, kind: str, enabled: bool, title: str = None, description: str = None, color: str = None):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        await self._save(i.guild_id, **{f'{kind}_embed_enabled': enabled})
        if title is not None: await self._save(i.guild_id, **{f'{kind}_embed_title': title[:256]})
        if description is not None: await self._save(i.guild_id, **{f'{kind}_embed_description': description[:4096]})
        if color is not None:
            try: value=int(color.strip().lstrip('#'),16)
            except ValueError: return await i.response.send_message('Color must be hex, e.g. #5865F2.', ephemeral=True)
            if not 0 <= value <= 0xFFFFFF: return await i.response.send_message('Color must be between #000000 and #FFFFFF.', ephemeral=True)
            await self._save(i.guild_id, **{f'{kind}_embed_color': value})
        await i.response.send_message(f'{kind.title()} embed updated. The banner/GIF and embed will be sent together.')

    @group.command(name='test')
    @app_commands.choices(kind=KIND_CHOICES)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test(self, i, kind: str = 'welcome'):
        if kind not in ('welcome', 'goodbye'):
            return await i.response.send_message('kind must be welcome or goodbye', ephemeral=True)
        await i.response.defer()
        await self.bot.greeting_worker.submit(i.user, kind, force_channel=i.channel)
        await i.followup.send('Queued a test card.', ephemeral=True)


async def setup(bot):
    await bot.add_cog(Greeting(bot))
