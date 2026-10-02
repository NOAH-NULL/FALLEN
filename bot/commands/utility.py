import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed, success_embed, error_embed


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='ping', description='Show bot latency and API responsiveness')
    async def ping(self, i: discord.Interaction):
        embed = info_embed('Pong!', 'Fallen is online and responding.')
        embed.add_field(name='Gateway', value=f'`{self.bot.latency * 1000:.0f} ms`', inline=True)
        embed.add_field(name='Shard', value=f'`{i.guild.shard_id if i.guild else "DM"}`', inline=True)
        embed.set_footer(text='Fallen • Live connection status')
        await i.response.send_message(embed=embed)

    @app_commands.command(name='health', description='Show database, Redis and bot health')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def health(self, i: discord.Interaction):
        try:
            db = await self.bot.db.health()
        except Exception:
            db = False
        try:
            redis = await self.bot.cache.health()
        except Exception:
            redis = False
        ready = self.bot.is_ready()
        overall = db and redis and ready
        embed = success_embed('System healthy', 'All core dependencies are responding.') if overall else error_embed('Degraded services', 'At least one core dependency is unavailable.')
        embed.add_field(name='PostgreSQL', value='🟢 Online' if db else '🔴 Offline', inline=True)
        embed.add_field(name='Redis', value='🟢 Online' if redis else '🔴 Offline', inline=True)
        embed.add_field(name='Discord Gateway', value='🟢 Ready' if ready else '🔴 Not ready', inline=True)
        embed.set_footer(text='Fallen • Restricted to server managers')
        await i.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Utility(bot))
