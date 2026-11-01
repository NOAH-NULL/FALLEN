import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed, success_embed, error_embed


class Custom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    group = app_commands.Group(name='custom', description='Create and use server custom commands')

    async def _prefix(self, guild_id):
        config = await self.bot.guild_config.get(guild_id)
        return (config or {}).get('command_prefix') or ','

    @group.command(name='set', description='Create or update a custom prefix command')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set(self, i, name: str, response: str):
        clean = name.lower().strip().replace(' ', '-')[:64]
        prefix = await self._prefix(i.guild_id)
        if not clean or clean.startswith('/') or clean.startswith(prefix):
            return await i.response.send_message(embed=error_embed('Invalid command name', 'Use a simple name such as `rules` or `socials`.'), ephemeral=True)
        await self.bot.custom_commands.set(i.guild_id, clean, response[:1900])
        await i.response.send_message(embed=success_embed('Custom command saved', f'Use `{prefix}{clean}` to run it.'))

    @group.command(name='use', description='Run a saved custom command')
    @app_commands.guild_only()
    async def use(self, i, name: str):
        clean = name.lower().strip().replace(' ', '-')[:64]
        response = await self.bot.custom_commands.get(i.guild_id, clean)
        if not response:
            return await i.response.send_message(embed=error_embed('Command not found', f'No custom command named `{clean}` exists.'), ephemeral=True)
        await i.response.send_message(response[:1900], allowed_mentions=discord.AllowedMentions.none())

    @group.command(name='remove', description='Delete a custom prefix command')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, i, name: str):
        clean = name.lower().strip().replace(' ', '-')[:64]
        prefix = await self._prefix(i.guild_id)
        await self.bot.custom_commands.remove(i.guild_id, clean)
        await i.response.send_message(embed=success_embed('Custom command removed', f'`{prefix}{clean}` has been removed.'))

    @group.command(name='list', description='List saved custom commands')
    @app_commands.guild_only()
    async def list_commands(self, i):
        # Keep this read-only command intentionally lightweight; the service owns persistence.
        from sqlalchemy import select
        from bot.models import CustomCommand
        async with self.bot.db.session() as session:
            result = await session.execute(select(CustomCommand.name).where(CustomCommand.guild_id == i.guild_id).order_by(CustomCommand.name))
            names = list(result.scalars())
        embed = info_embed('Custom Commands', 'Saved custom prefix commands for this server.')
        if names:
            prefix = await self._prefix(i.guild_id)
            embed.description = '\n'.join(f'`{prefix}{name}`' for name in names[:50])
            embed.set_footer(text=f'{len(names)} command(s) configured')
        else:
            embed.description = 'No custom commands have been created yet.'
        await i.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Custom(bot))
