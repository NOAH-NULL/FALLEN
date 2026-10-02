import discord
from discord import app_commands
from discord.ext import commands
class Admin(commands.Cog):
    def __init__(self,bot):self.bot=bot
    group=app_commands.Group(name='config',description='Configure the server')
    @group.command(name='autorole')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def autorole(self,i,role:discord.Role|None):
        await self.bot.guild_config.update(i.guild_id, autorole_id=role.id if role else None)
        await i.response.send_message(f'Autorole: {role.mention if role else "disabled"}.')
    @group.command(name='logs')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def logs(self,i,channel:discord.TextChannel|None):
        await self.bot.guild_config.update(i.guild_id, log_channel_id=channel.id if channel else None)
        await i.response.send_message(f'Log channel: {channel.mention if channel else "disabled"}.')
    @group.command(name='automod')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod(self,i,enabled:bool,spam_limit:app_commands.Range[int,3,20]=6,window:app_commands.Range[int,2,60]=8):
        await self.bot.guild_config.update(i.guild_id, automod_enabled=enabled, spam_limit=spam_limit, spam_window=window)
        await i.response.send_message(f'AutoMod **{"enabled" if enabled else "disabled"}** — {spam_limit} messages/{window}s.')
async def setup(bot):await bot.add_cog(Admin(bot))
