import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed

class Invites(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @app_commands.command(name='invites', description='Show invite stats for a member')
    async def invites(self, i, member: discord.Member | None = None):
        m = member or i.user
        rows = await self.bot.invites.stats(i.guild_id, m.id)
        joins = rows[0].joins if rows else 0
        embed=info_embed('Invite Stats', f'{m.mention} has **{joins:,}** tracked invite joins.', thumbnail=m.display_avatar.url); embed.set_footer(text='Fallen • Invite tracking'); await i.response.send_message(embed=embed)

    @app_commands.command(name='inviteleaderboard', description='Show the server invite leaderboard')
    async def inviteleaderboard(self, i):
        rows = await self.bot.invites.stats(i.guild_id)
        if not rows: return await i.response.send_message('No invite joins have been tracked yet.')
        lines = [f'**{n}.** <@{r.user_id}> — **{r.joins}** joins' for n, r in enumerate(rows[:10], 1)]
        embed=info_embed('🏆 Invite Leaderboard', '\n'.join(lines)); embed.set_footer(text='Fallen • Top 10 inviters'); await i.response.send_message(embed=embed)

async def setup(bot): await bot.add_cog(Invites(bot))
