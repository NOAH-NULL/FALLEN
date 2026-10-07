import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed, success_embed, error_embed


class Community(commands.Cog):
    def __init__(self, bot):
        self.bot = bot




    @app_commands.command(name='rank', description='Show your XP rank in this server')
    @app_commands.guild_only()
    async def rank(self, i, member: discord.Member | None = None):
        m = member or i.user
        row = await self.bot.levels.get(i.guild_id, m.id)
        rank = await self.bot.levels.rank(i.guild_id, m.id) if row else None
        level = row.level if row else 0
        xp = row.xp if row else 0
        total = row.total_xp if row else 0
        needed = self.bot.levels.xp_needed(level)
        embed = info_embed(f'Rank • {m.display_name}', f'{m.mention} progress')
        embed.add_field(name='Rank', value=f'**#{rank}**' if rank else '**Unranked**', inline=True)
        embed.add_field(name='Level', value=f'**{level}**', inline=True)
        embed.add_field(name='Total XP', value=f'**{total:,}**', inline=True)
        embed.add_field(name='Progress', value=f'**{xp:,} / {needed:,}**', inline=False)
        await i.response.send_message(embed=embed)

    @app_commands.command(name='leaderboard', description='Show the server XP leaderboard')
    @app_commands.guild_only()
    @app_commands.describe(limit='Number of members to show')
    async def leaderboard(self, i, limit: app_commands.Range[int, 1, 25] = 10):
        rows = await self.bot.levels.leaderboard(i.guild_id, limit)
        if not rows:
            return await i.response.send_message(embed=info_embed('Leaderboard', 'No XP has been earned yet.'))
        lines = []
        for position, row in enumerate(rows, 1):
            member = i.guild.get_member(row.user_id)
            name = member.display_name if member else f'User {row.user_id}'
            lines.append(f'**#{position}** {name} — Level **{row.level}** • **{row.total_xp:,} XP**')
        embed = info_embed(f'{i.guild.name} • XP Leaderboard', '\n'.join(lines))
        await i.response.send_message(embed=embed)

    @app_commands.choices(mode=[
        app_commands.Choice(name='Letters / characters', value='per_character'),
        app_commands.Choice(name='Random per message', value='random'),
    ])
    @app_commands.command(name='level-settings', description='Configure the server leveling system')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        enabled='Enable XP gain',
        announce='Announce level-ups',
        xp_min='Minimum XP per eligible message',
        xp_max='Maximum XP per eligible message',
        cooldown='Cooldown between XP awards in seconds',
        channel='Optional dedicated level-up announcement channel',
        stack_awards='Keep previous level roles when earning a new reward',
        mode='XP mode: per_character or random',
        xp_per_letter='XP earned for each letter in per-character mode',
        max_letter_xp='Maximum XP from one message in per-character mode',
    )
    async def level_settings(self, i, enabled: bool | None = None, announce: bool | None = None,
                             xp_min: app_commands.Range[int, 1, 1000] | None = None,
                             xp_max: app_commands.Range[int, 1, 1000] | None = None,
                             cooldown: app_commands.Range[int, 1, 86400] | None = None,
                             channel: discord.TextChannel | None = None,
                             stack_awards: bool | None = None,
                             mode: str | None = None,
                             xp_per_letter: app_commands.Range[int, 1, 100] | None = None,
                             max_letter_xp: app_commands.Range[int, 1, 10000] | None = None):
        values = {}
        if enabled is not None: values['enabled'] = enabled
        if announce is not None: values['announce'] = announce
        if xp_min is not None: values['xp_min'] = xp_min
        if xp_max is not None: values['xp_max'] = xp_max
        if cooldown is not None: values['cooldown_seconds'] = cooldown
        if channel is not None: values['announcement_channel_id'] = channel.id
        if stack_awards is not None: values['stack_awards'] = stack_awards
        if mode is not None: values['message_xp_mode'] = mode
        if xp_per_letter is not None: values['xp_per_character'] = xp_per_letter
        if max_letter_xp is not None: values['max_character_xp'] = max_letter_xp
        if values:
            cfg = await self.bot.levels.update_settings(i.guild_id, **values)
        else:
            cfg = await self.bot.levels.settings(i.guild_id)
        embed = info_embed('Level Settings', 'Current leveling configuration.')
        embed.add_field(name='Enabled', value=str(cfg['enabled']), inline=True)
        mode = 'Letters' if cfg['message_xp_mode'] == 'per_character' else 'Random'
        xp_value = f"{cfg['xp_per_character']} XP/letter, max {cfg['max_character_xp']} XP" if cfg['message_xp_mode'] == 'per_character' else f"{cfg['xp_min']}–{cfg['xp_max']} XP/message"
        embed.add_field(name='Message XP', value=f"**{mode}** • {xp_value}", inline=True)
        embed.add_field(name='XP Channels', value=str(len(cfg['xp_channels'])) + (' configured' if cfg['xp_channels'] else ' • all allowed'), inline=True)
        embed.add_field(name='Cooldown', value=f"{cfg['cooldown_seconds']}s", inline=True)
        embed.add_field(name='Announcements', value=str(cfg['announce']), inline=True)
        embed.add_field(name='Stack rewards', value=str(cfg['stack_awards']), inline=True)
        target = cfg['announcement_channel_id']
        embed.add_field(name='Level-up Channel', value=f'<#{target}>' if target else 'Message channel', inline=True)
        await i.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='level-channel', description='Allow leveling XP in a specific channel')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def level_channel(self, i, channel: discord.TextChannel):
        cfg = await self.bot.levels.settings(i.guild_id)
        channels = set(cfg['xp_channels'])
        channels.add(channel.id)
        await self.bot.levels.update_settings(i.guild_id, xp_channels=list(channels))
        await i.response.send_message(embed=success_embed('Leveling channel added', f'{channel.mention} is now an XP channel. If any XP channels are configured, XP is earned only there.'), ephemeral=True)

    @app_commands.command(name='level-channel-remove', description='Remove a channel from the leveling XP whitelist')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def level_channel_remove(self, i, channel: discord.TextChannel):
        cfg = await self.bot.levels.settings(i.guild_id)
        channels = [x for x in cfg['xp_channels'] if x != channel.id]
        await self.bot.levels.update_settings(i.guild_id, xp_channels=channels)
        await i.response.send_message(embed=success_embed('Leveling channel removed', f'{channel.mention} is no longer a dedicated XP channel.'), ephemeral=True)

    @app_commands.command(name='level-channels', description='Show the dedicated leveling XP channels')
    @app_commands.guild_only()
    async def level_channels(self, i):
        cfg = await self.bot.levels.settings(i.guild_id)
        value = ', '.join(f'<#{x}>' for x in cfg['xp_channels']) if cfg['xp_channels'] else 'All channels except excluded channels.'
        await i.response.send_message(embed=info_embed('Leveling XP Channels', value), ephemeral=True)

    @app_commands.command(name='xp-add', description='Add XP to a member')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(member='Member receiving XP', amount='Amount of XP to add')
    async def xp_add(self, i, member: discord.Member, amount: app_commands.Range[int, 1, 1000000]):
        old_level, new_level, xp, total = await self.bot.levels.modify_xp(i.guild_id, member.id, amount)
        await i.response.send_message(embed=success_embed('XP added', f'{member.mention} received **{amount:,} XP**.\nLevel: **{new_level}** • Total XP: **{total:,}**'), ephemeral=True)

    @app_commands.command(name='xp-remove', description='Remove XP from a member')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(member='Member losing XP', amount='Amount of XP to remove')
    async def xp_remove(self, i, member: discord.Member, amount: app_commands.Range[int, 1, 1000000]):
        old_level, new_level, xp, total = await self.bot.levels.modify_xp(i.guild_id, member.id, -amount)
        await i.response.send_message(embed=success_embed('XP removed', f'{member.mention} lost **{amount:,} XP**.\nLevel: **{new_level}** • Total XP: **{total:,}**'), ephemeral=True)

    @app_commands.command(name='xp-set', description='Set a member total XP value')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(member='Member to update', amount='New total XP value')
    async def xp_set(self, i, member: discord.Member, amount: app_commands.Range[int, 0, 10000000]):
        old_level, new_level, xp, total = await self.bot.levels.modify_xp(i.guild_id, member.id, amount, set_value=True)
        await i.response.send_message(embed=success_embed('XP set', f'{member.mention} now has **{total:,} total XP**.\nLevel: **{new_level}**'), ephemeral=True)

    @app_commands.command(name='level-bonus', description='Give a role a leveling XP multiplier')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(role='Role receiving bonus XP', multiplier='XP multiplier from 1x to 10x')
    async def level_bonus(self, i, role: discord.Role, multiplier: app_commands.Range[int, 1, 10]):
        cfg = await self.bot.levels.settings(i.guild_id)
        bonuses = dict(cfg['bonus_roles'])
        bonuses[str(role.id)] = int(multiplier)
        await self.bot.levels.update_settings(i.guild_id, bonus_roles=bonuses)
        await i.response.send_message(
            embed=success_embed('XP bonus saved', f'{role.mention} now earns **{multiplier}x XP** per eligible award.'),
            ephemeral=True,
        )

    @app_commands.command(name='level-bonus-remove', description='Remove a role XP multiplier')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def level_bonus_remove(self, i, role: discord.Role):
        cfg = await self.bot.levels.settings(i.guild_id)
        bonuses = dict(cfg['bonus_roles'])
        bonuses.pop(str(role.id), None)
        await self.bot.levels.update_settings(i.guild_id, bonus_roles=bonuses)
        await i.response.send_message(
            embed=success_embed('XP bonus removed', f'{role.mention} no longer receives a leveling multiplier.'),
            ephemeral=True,
        )

    @app_commands.command(name='level-exclude-channel', description='Exclude a channel from XP')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def level_exclude_channel(self, i, channel: discord.TextChannel):
        cfg = await self.bot.levels.settings(i.guild_id)
        channels = set(cfg['no_xp_channels'])
        channels.add(channel.id)
        await self.bot.levels.update_settings(i.guild_id, no_xp_channels=list(channels))
        await i.response.send_message(embed=success_embed('Level exclusion added', f'{channel.mention} will no longer award XP.'), ephemeral=True)

    @app_commands.command(name='level-exclude-role', description='Exclude a role from XP')
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def level_exclude_role(self, i, role: discord.Role):
        cfg = await self.bot.levels.settings(i.guild_id)
        roles = set(cfg['no_xp_roles'])
        roles.add(role.id)
        await self.bot.levels.update_settings(i.guild_id, no_xp_roles=list(roles))
        await i.response.send_message(embed=success_embed('Level exclusion added', f'{role.mention} will no longer earn XP.'), ephemeral=True)

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
