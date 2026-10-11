import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed

class Invites(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @staticmethod
    def _tracking_permission_warning(interaction):
        guild = getattr(interaction, "guild", None)
        me = getattr(guild, "me", None) if guild else None
        permissions = getattr(me, "guild_permissions", None)
        if permissions is not None and not getattr(permissions, "manage_guild", False):
            return (
                "Invite attribution needs the bot's **Manage Server** permission. "
                "Also enable **Server Members Intent** in the Discord Developer Portal."
            )
        return None

    @app_commands.command(name='invites', description='Show invite stats for a member')
    @app_commands.guild_only()
    async def invites(self, i, member: discord.Member | None = None):
        m = member or i.user
        rows = await self.bot.invites.stats(i.guild_id, m.id)
        joins = rows[0].joins if rows else 0
        embed=info_embed('Invite Stats', f'{m.mention} has **{joins:,}** tracked invite joins.', thumbnail=m.display_avatar.url)
        warning = self._tracking_permission_warning(i)
        if warning:
            embed.add_field(name="Tracking setup", value=warning, inline=False)
        embed.set_footer(text='Fallen • Invite tracking')
        await i.response.send_message(embed=embed)

    @app_commands.command(name='inviteleaderboard', description='Show the server invite leaderboard')
    @app_commands.guild_only()
    async def inviteleaderboard(self, i):
        rows = await self.bot.invites.stats(i.guild_id)
        if not rows:
            warning = self._tracking_permission_warning(i)
            message = 'No invite joins have been tracked yet.'
            if warning:
                message += f'\n\n⚠️ {warning}'
            return await i.response.send_message(message, ephemeral=bool(warning))
        lines = [f'**{n}.** <@{r.user_id}> — **{r.joins}** joins' for n, r in enumerate(rows[:10], 1)]
        embed=info_embed('🏆 Invite Leaderboard', '\n'.join(lines))
        warning = self._tracking_permission_warning(i)
        if warning:
            embed.add_field(name="Tracking setup", value=warning, inline=False)
        embed.set_footer(text='Fallen • Top 10 inviters')
        await i.response.send_message(embed=embed)

async def setup(bot): await bot.add_cog(Invites(bot))
