import discord
from discord import app_commands
from discord.ext import commands

class Control(commands.GroupCog, name='settings'):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='welcome-channel',description='Set welcome channel')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome_channel(self,interaction:discord.Interaction,channel:discord.TextChannel):
        async with self.bot.db.session() as s:
            from bot.models import GuildConfig
            row=await s.get(GuildConfig,interaction.guild.id)
            if not row: row=GuildConfig(guild_id=interaction.guild.id); s.add(row)
            row.welcome_channel_id=channel.id; await s.commit()
        await self.bot.guild_config.invalidate(interaction.guild.id); await interaction.response.send_message(f'✅ Welcome channel: {channel.mention}')
    @app_commands.command(name='goodbye-channel',description='Set goodbye channel')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def goodbye_channel(self,interaction:discord.Interaction,channel:discord.TextChannel):
        async with self.bot.db.session() as s:
            from bot.models import GuildConfig
            row=await s.get(GuildConfig,interaction.guild.id)
            if not row: row=GuildConfig(guild_id=interaction.guild.id); s.add(row)
            row.goodbye_channel_id=channel.id; await s.commit()
        await self.bot.guild_config.invalidate(interaction.guild.id); await interaction.response.send_message(f'✅ Goodbye channel: {channel.mention}')
    @app_commands.command(name='automod',description='Enable or disable AutoMod')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod(self,interaction:discord.Interaction,enabled:bool):
        async with self.bot.db.session() as s:
            from bot.models import GuildConfig
            row=await s.get(GuildConfig,interaction.guild.id)
            if not row: row=GuildConfig(guild_id=interaction.guild.id); s.add(row)
            row.automod_enabled=enabled; await s.commit()
        await self.bot.guild_config.invalidate(interaction.guild.id); await interaction.response.send_message(f'🛡️ AutoMod: **{enabled}**')
    @app_commands.command(name='autorole',description='Set or clear the autorole')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def autorole(self,interaction:discord.Interaction,role:discord.Role|None=None):
        async with self.bot.db.session() as s:
            from bot.models import GuildConfig
            row=await s.get(GuildConfig,interaction.guild.id)
            if not row: row=GuildConfig(guild_id=interaction.guild.id); s.add(row)
            row.autorole_id=role.id if role else None; await s.commit()
        await self.bot.guild_config.invalidate(interaction.guild.id); await interaction.response.send_message(f'🎭 Autorole: **{role.name if role else "disabled"}**')

async def setup(bot): await bot.add_cog(Control(bot))
