import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed, success_embed, error_embed


class Community(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='level', description="Show a member's server level and XP")
    @app_commands.guild_only()
    async def level(self, i, member: discord.Member | None = None):
        m = member or i.user
        row = await self.bot.levels.get(i.guild_id, m.id)
        level = row.level if row else 0
        xp = row.xp if row else 0
        needed = self.bot.levels.xp_needed(level)
        embed = info_embed(f'Level • {m.display_name}', f'{m.mention} is progressing through the server.', thumbnail=m.display_avatar.url)
        embed.add_field(name='Level', value=f'**{level}**', inline=True)
        embed.add_field(name='XP', value=f'**{xp:,} / {needed:,}**', inline=True)
        progress = min(10, int((xp / needed) * 10)) if needed else 10
        embed.add_field(name='Progress', value='▰' * progress + '▱' * (10 - progress), inline=False)
        await i.response.send_message(embed=embed)

    @app_commands.command(name='uwuify', description='Enable or disable real-time UwUify for a member')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def uwuify(self, i, member: discord.Member, enabled: bool = True):
        if member.bot:
            return await i.response.send_message(embed=error_embed('UwUify unavailable', 'Bot messages are ignored by the transformer.'), ephemeral=True)
        await self.bot.uwuify.set_enabled(i.guild_id, member.id, enabled)
        state = 'enabled' if enabled else 'disabled'
        await i.response.send_message(embed=success_embed(f'UwUify {state}', f'Real-time UwUify is now **{state}** for {member.mention}.'))

    @app_commands.command(name='levelrole', description='Assign a role automatically when members reach a level')
    @app_commands.guild_only()
    @app_commands.describe(level='Level that unlocks the role', role='Role awarded at that level')
    @app_commands.checks.has_permissions(manage_roles=True)
    async def levelrole(self, i, level: app_commands.Range[int, 1, 10000], role: discord.Role):
        if role.is_default() or role.managed or role >= i.guild.me.top_role:
            return await i.response.send_message(embed=error_embed('Role cannot be assigned', 'Choose a normal role below my highest role.'), ephemeral=True)
        await self.bot.levels.set_role(i.guild_id, level, role.id)
        await i.response.send_message(embed=success_embed('Level reward saved', f'Reaching level **{level}** now awards {role.mention}.'))

    @app_commands.command(name='levelrole-remove', description='Remove an automatic level-role reward')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_roles=True)
    async def levelrole_remove(self, i, level: app_commands.Range[int, 1, 10000]):
        await self.bot.levels.remove_role(i.guild_id, level)
        await i.response.send_message(embed=success_embed('Level reward removed', f'No role will be awarded at level **{level}**.'))

    @app_commands.command(name='levelroles', description='List configured level-role rewards')
    @app_commands.guild_only()
    async def levelroles(self, i):
        rows = await self.bot.levels.configured_roles(i.guild_id)
        embed = info_embed('Level Roles', 'Automatic role rewards configured for this server.')
        if rows:
            for row in rows[:25]:
                embed.add_field(name=f'Level {row.level}', value=f'<@&{row.role_id}>', inline=True)
        else:
            embed.description = 'No level-role rewards are configured yet.'
        await i.response.send_message(embed=embed)

    @app_commands.command(name='serverinfo', description='Show server information')
    @app_commands.guild_only()
    async def serverinfo(self, i):
        g = i.guild
        embed = info_embed(g.name, f'Created <t:{int(g.created_at.timestamp())}:R>')
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name='Members', value=f'**{g.member_count:,}**', inline=True)
        embed.add_field(name='Channels', value=f'**{len(g.channels):,}**', inline=True)
        embed.add_field(name='Roles', value=f'**{len(g.roles):,}**', inline=True)
        embed.add_field(name='Owner', value=g.owner.mention if g.owner else 'Unknown', inline=True)
        embed.add_field(name='Server ID', value=f'`{g.id}`', inline=True)
        embed.set_footer(text=f'Fallen • {g.name}')
        await i.response.send_message(embed=embed)

    @app_commands.command(name='avatar', description='Show a member avatar')
    @app_commands.guild_only()
    async def avatar(self, i, member: discord.Member | None = None):
        m = member or i.user
        embed = info_embed(f'{m.display_name} • Avatar', f'Viewing the current avatar for {m.mention}.')
        embed.set_image(url=m.display_avatar.url)
        embed.set_footer(text='Fallen • Avatar viewer')
        await i.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Community(bot))
