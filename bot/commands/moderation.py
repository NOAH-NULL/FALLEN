import discord
from datetime import timedelta
from discord import app_commands
from discord.ext import commands
from bot.services.audit import send_log
from bot.ui import success_embed, error_embed, warning_embed, info_embed


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _check(self, interaction, member):
        guild = interaction.guild
        me = guild.me
        if member == interaction.user or member == guild.owner or member == me:
            return False
        return interaction.user.top_role > member.top_role and me.top_role > member.top_role

    async def _case(self, i, member, action, reason):
        try:
            await self.bot.platform.case(i.guild_id, member.id, i.user.id, action, reason)
        except Exception:
            # Moderation action must not be rolled back just because case logging failed.
            self.bot.log.exception('failed to create moderation case')

    @app_commands.command(name='warn', description='Warn a member and record it permanently')
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, i, member: discord.Member, reason: str = 'No reason provided'):
        if not self._check(i, member):
            return await i.response.send_message(embed=error_embed('Action blocked', 'Role hierarchy prevents that action.'), ephemeral=True)
        await self.bot.moderation.warn(i.guild_id, member.id, i.user.id, reason)
        await self._case(i, member, 'warn', reason)
        count = await self.bot.moderation.count(i.guild_id, member.id)
        embed = warning_embed('Member warned', f'{member.mention} has received a moderation warning.')
        embed.add_field(name='Reason', value=reason[:1024], inline=False)
        embed.add_field(name='Active warning points', value=f'`{count}`', inline=True)
        embed.set_footer(text=f'Moderator: {i.user.display_name}')
        await i.response.send_message(embed=embed)
        await send_log(i.guild, await self.bot.guild_config.get(i.guild_id), 'Member warned', f'{member.mention} — {reason}')

    @app_commands.command(name='warnings', description='Show a member’s active warnings')
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, i, member: discord.Member):
        rows = await self.bot.moderation.warnings(i.guild_id, member.id)
        embed = info_embed(f'Warnings • {member.display_name}', f'{len(rows)} active warning record(s).', thumbnail=member.display_avatar.url)
        if rows:
            for row in rows[:10]:
                embed.add_field(name=f'#{row.id} • {row.created_at:%d %b %Y}', value=f'<@{row.moderator_id}> — {row.reason[:500]}', inline=False)
        else:
            embed.description = 'No active warnings were found for this member.'
        await i.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='timeout', description='Timeout a member')
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, i, member: discord.Member, minutes: app_commands.Range[int, 1, 10080], reason: str = 'No reason provided'):
        if not self._check(i, member):
            return await i.response.send_message(embed=error_embed('Action blocked', 'Role hierarchy prevents that action.'), ephemeral=True)
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
        await self._case(i, member, 'timeout', reason)
        embed = success_embed('Member timed out', f'{member.mention} was timed out successfully.')
        embed.add_field(name='Duration', value=f'`{minutes}` minutes', inline=True)
        embed.add_field(name='Reason', value=reason[:1024], inline=False)
        await i.response.send_message(embed=embed)
        await send_log(i.guild, await self.bot.guild_config.get(i.guild_id), 'Member timed out', f'{member.mention} — {reason} ({minutes}m)')

    @app_commands.command(name='ban', description='Ban a member')
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, i, member: discord.Member, reason: str = 'No reason provided'):
        if not self._check(i, member):
            return await i.response.send_message(embed=error_embed('Action blocked', 'Role hierarchy prevents that action.'), ephemeral=True)
        await member.ban(reason=reason)
        await self._case(i, member, 'ban', reason)
        embed = success_embed('Member banned', f'{member.mention} was banned successfully.')
        embed.add_field(name='Reason', value=reason[:1024], inline=False)
        await i.response.send_message(embed=embed)
        await send_log(i.guild, await self.bot.guild_config.get(i.guild_id), 'Member banned', f'{member.mention} — {reason}')

    @app_commands.command(name='kick', description='Kick a member')
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, i, member: discord.Member, reason: str = 'No reason provided'):
        if not self._check(i, member):
            return await i.response.send_message(embed=error_embed('Action blocked', 'Role hierarchy prevents that action.'), ephemeral=True)
        await member.kick(reason=reason)
        await self._case(i, member, 'kick', reason)
        embed = success_embed('Member kicked', f'{member.mention} was kicked successfully.')
        embed.add_field(name='Reason', value=reason[:1024], inline=False)
        await i.response.send_message(embed=embed)
        await send_log(i.guild, await self.bot.guild_config.get(i.guild_id), 'Member kicked', f'{member.mention} — {reason}')

    @app_commands.command(name='clear', description='Bulk delete recent messages')
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, i, amount: app_commands.Range[int, 1, 100]):
        await i.response.defer(ephemeral=True)
        try:
            deleted = await i.channel.purge(limit=amount)
        except discord.Forbidden:
            return await i.followup.send(embed=error_embed('Clear failed', 'I need Manage Messages and Read Message History in this channel.'), ephemeral=True)
        except discord.HTTPException:
            return await i.followup.send(embed=error_embed('Clear failed', 'Discord rejected the bulk delete request. Try a smaller amount.'), ephemeral=True)
        embed = success_embed('Messages cleared', f'Cleaned **{len(deleted)}** recent messages from this channel.')
        await i.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='slowmode', description='Set channel slowmode')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, i, seconds: app_commands.Range[int, 0, 21600]):
        await i.channel.edit(slowmode_delay=seconds)
        embed = success_embed('Slowmode updated', f'Slowmode is now **{seconds} seconds**.')
        await i.response.send_message(embed=embed)

    @app_commands.command(name='lock', description='Lock the current channel')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=False)
        await i.response.send_message(embed=success_embed('Channel locked', f'{i.channel.mention} is now locked for @everyone.'))

    @app_commands.command(name='unlock', description='Unlock the current channel')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, i):
        await i.channel.set_permissions(i.guild.default_role, send_messages=None)
        await i.response.send_message(embed=success_embed('Channel unlocked', f'{i.channel.mention} has returned to its inherited permissions.'))


async def setup(bot):
    bot.moderation = __import__('bot.services.moderation', fromlist=['ModerationService']).ModerationService(bot.db)
    await bot.add_cog(Moderation(bot))
