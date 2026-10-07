import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed, success_embed, error_embed


class Levels(commands.GroupCog, name='level'):
    """Complete leveling command group."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _channel_permission_error(channel, member, *, embed_links=False):
        if member is None:
            return 'I cannot resolve my server member.'
        permissions = channel.permissions_for(member)
        missing = [
            name for name, ok in (
                ('View Channel', permissions.view_channel),
                ('Send Messages', permissions.send_messages),
                ('Embed Links', permissions.embed_links if embed_links else True),
            ) if not ok
        ]
        return f'Missing: **{", ".join(missing)}**.' if missing else None

    async def _send_settings(self, interaction: discord.Interaction):
        cfg = await self.bot.levels.settings(interaction.guild.id)
        announce_channel = (
            interaction.guild.get_channel(cfg['announcement_channel_id'])
            if cfg['announcement_channel_id'] else None
        )
        xp_channels = [
            interaction.guild.get_channel(cid)
            for cid in cfg['xp_channels']
        ]
        xp_channels = [channel for channel in xp_channels if channel is not None]

        embed = info_embed('Level Settings', 'Current leveling configuration.')
        embed.add_field(name='Enabled', value=f'**{cfg["enabled"]}**', inline=True)
        embed.add_field(name='Announcements', value=f'**{cfg["announce"]}**', inline=True)
        embed.add_field(name='Cooldown', value=f'**{cfg["cooldown_seconds"]}s**', inline=True)
        embed.add_field(
            name='Message XP',
            value=(
                f'**{cfg["xp_per_character"]} XP/letter** · max **{cfg["max_character_xp"]}**'
                if cfg['message_xp_mode'] == 'per_character'
                else f'**{cfg["xp_min"]}–{cfg["xp_max"]} XP/message**'
            ),
            inline=False,
        )
        embed.add_field(
            name='XP Channels',
            value=', '.join(channel.mention for channel in xp_channels) if xp_channels else 'All eligible channels',
            inline=False,
        )
        embed.add_field(
            name='Level-up Channel',
            value=announce_channel.mention if announce_channel else 'Message channel',
            inline=False,
        )
        embed.add_field(name='Stack Rewards', value=f'**{cfg["stack_awards"]}**', inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='show', description='Show a member level and XP')
    @app_commands.guild_only()
    @app_commands.describe(member='Member to inspect')
    async def show(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        row = await self.bot.levels.get(interaction.guild.id, member.id)
        level = int(row.level) if row else 0
        xp = int(row.xp) if row else 0
        total = int(row.total_xp) if row else 0
        needed = self.bot.levels.xp_for_next_level(level)
        await interaction.response.send_message(
            embed=info_embed(
                f'Level • {member.display_name}',
                f'{member.mention} is **Level {level}** with **{xp:,} XP** progress and **{total:,} total XP**.\n'
                f'Next level threshold: **{needed:,} XP** total.'
            ),
            ephemeral=True,
        )

    @app_commands.command(name='rank', description='Show a member XP rank')
    @app_commands.guild_only()
    @app_commands.describe(member='Member to inspect')
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        row = await self.bot.levels.get(interaction.guild.id, member.id)
        rank = await self.bot.levels.rank(interaction.guild.id, member.id) if row else None
        total = int(row.total_xp) if row else 0
        await interaction.response.send_message(
            embed=info_embed(
                f'Rank • {member.display_name}',
                f'{member.mention} is **#{rank}** with **{total:,} total XP**.' if rank else f'{member.mention} is currently unranked.'
            ),
            ephemeral=True,
        )

    @app_commands.command(name='leaderboard', description='Show the server XP leaderboard')
    @app_commands.guild_only()
    @app_commands.describe(limit='Number of members to show')
    async def leaderboard(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 25] = 10):
        rows = await self.bot.levels.leaderboard(interaction.guild.id, limit)
        if not rows:
            return await interaction.response.send_message(embed=info_embed('Leaderboard', 'No XP has been earned yet.'), ephemeral=True)
        lines = []
        for position, row in enumerate(rows, 1):
            member = interaction.guild.get_member(row.user_id)
            name = member.display_name if member else f'User {row.user_id}'
            lines.append(f'**#{position}** {name} — Level **{row.level}** • **{row.total_xp:,} XP**')
        await interaction.response.send_message(
            embed=info_embed(f'{interaction.guild.name} • XP Leaderboard', '\n'.join(lines)),
            ephemeral=True,
        )

    @app_commands.command(name='settings', description='View or configure leveling settings')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(mode=[
        app_commands.Choice(name='Letters / characters', value='per_character'),
        app_commands.Choice(name='Random per message', value='random'),
    ])
    @app_commands.describe(
        enabled='Enable or disable XP gain',
        announce='Enable or disable level-up announcements',
        xp_min='Minimum random XP per message',
        xp_max='Maximum random XP per message',
        cooldown='Cooldown between XP awards in seconds',
        channel='Dedicated level-up announcement channel',
        stack_awards='Keep previous level roles',
        mode='Message XP mode',
        xp_per_letter='XP per letter in character mode',
        max_letter_xp='Maximum character-mode XP from one message',
    )
    async def settings(
        self,
        interaction: discord.Interaction,
        enabled: bool | None = None,
        announce: bool | None = None,
        xp_min: app_commands.Range[int, 1, 1000] | None = None,
        xp_max: app_commands.Range[int, 1, 1000] | None = None,
        cooldown: app_commands.Range[int, 1, 86400] | None = None,
        channel: discord.TextChannel | None = None,
        stack_awards: bool | None = None,
        mode: str | None = None,
        xp_per_letter: app_commands.Range[int, 1, 100] | None = None,
        max_letter_xp: app_commands.Range[int, 1, 10000] | None = None,
    ):
        values = {}
        if enabled is not None:
            values['enabled'] = enabled
        if announce is not None:
            values['announce'] = announce
        if xp_min is not None:
            values['xp_min'] = xp_min
        if xp_max is not None:
            values['xp_max'] = xp_max
        if cooldown is not None:
            values['cooldown_seconds'] = cooldown
        if channel is not None:
            error = self._channel_permission_error(channel, interaction.guild.me, embed_links=True)
            if error:
                return await interaction.response.send_message(
                    f'❌ I cannot use {channel.mention}. {error}',
                    ephemeral=True,
                )
            values['announcement_channel_id'] = channel.id
        if stack_awards is not None:
            values['stack_awards'] = stack_awards
        if mode is not None:
            values['message_xp_mode'] = mode
        if xp_per_letter is not None:
            values['xp_per_character'] = xp_per_letter
        if max_letter_xp is not None:
            values['max_character_xp'] = max_letter_xp

        if values:
            await self.bot.levels.update_settings(interaction.guild.id, **values)
        await self._send_settings(interaction)

    @app_commands.command(name='channel', description='Set the dedicated level-up announcement channel')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel='Channel where level-up announcements should be sent')
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        error = self._channel_permission_error(channel, interaction.guild.me, embed_links=True)
        if error:
            return await interaction.response.send_message(
                f'❌ I cannot use {channel.mention}. {error}',
                ephemeral=True,
            )
        await self.bot.levels.update_settings(
            interaction.guild.id,
            announcement_channel_id=channel.id,
            announce=True,
        )
        await interaction.response.send_message(
            embed=success_embed('Level-up channel set', f'Announcements will now be sent only in {channel.mention}.'),
            ephemeral=True,
        )

    @app_commands.command(name='channel-reset', description='Use the channel where the level-up happened')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel_reset(self, interaction: discord.Interaction):
        await self.bot.levels.update_settings(
            interaction.guild.id,
            announcement_channel_id=None,
        )
        await interaction.response.send_message(
            embed=success_embed('Level-up channel reset', 'Announcements will use the channel where the level-up happened.'),
            ephemeral=True,
        )

    @app_commands.command(name='xp-channel', description='Restrict XP to one channel')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel='Only this channel will generate XP')
    async def xp_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.levels.update_settings(interaction.guild.id, xp_channels=[channel.id])
        await interaction.response.send_message(
            embed=success_embed('XP channel set', f'XP is now earned only from {channel.mention}.'),
            ephemeral=True,
        )

    @app_commands.command(name='xp-channel-reset', description='Allow XP in all eligible channels')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def xp_channel_reset(self, interaction: discord.Interaction):
        await self.bot.levels.update_settings(interaction.guild.id, xp_channels=[])
        await interaction.response.send_message(
            embed=success_embed('XP channel reset', 'XP can now be earned in all eligible channels.'),
            ephemeral=True,
        )

    @app_commands.command(name='xp-channels', description='Show configured XP channels')
    @app_commands.guild_only()
    async def xp_channels(self, interaction: discord.Interaction):
        cfg = await self.bot.levels.settings(interaction.guild.id)
        value = ', '.join(f'<#{cid}>' for cid in cfg['xp_channels']) if cfg['xp_channels'] else 'All eligible channels'
        await interaction.response.send_message(embed=info_embed('XP Channels', value), ephemeral=True)

    @app_commands.command(name='xp-add', description='Add XP to a member')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def xp_add(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 1000000]):
        _, level, xp, total = await self.bot.levels.modify_xp(interaction.guild.id, member.id, amount)
        await interaction.response.send_message(
            embed=success_embed('XP added', f'{member.mention} received **{amount:,} XP**.\nLevel **{level}** · Total **{total:,} XP**.'),
            ephemeral=True,
        )

    @app_commands.command(name='xp-remove', description='Remove XP from a member')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def xp_remove(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1, 1000000]):
        _, level, xp, total = await self.bot.levels.modify_xp(interaction.guild.id, member.id, -amount)
        await interaction.response.send_message(
            embed=success_embed('XP removed', f'{member.mention} lost **{amount:,} XP**.\nLevel **{level}** · Total **{total:,} XP**.'),
            ephemeral=True,
        )

    @app_commands.command(name='xp-set', description='Set a member total XP value')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def xp_set(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 0, 10000000]):
        _, level, xp, total = await self.bot.levels.modify_xp(interaction.guild.id, member.id, amount, set_value=True)
        await interaction.response.send_message(
            embed=success_embed('XP set', f'{member.mention} now has **{total:,} total XP**.\nLevel **{level}**.'),
            ephemeral=True,
        )

    @app_commands.command(name='level-bonus', description='Give a role a leveling XP multiplier')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def level_bonus(self, interaction: discord.Interaction, role: discord.Role, multiplier: app_commands.Range[int, 1, 10]):
        cfg = await self.bot.levels.settings(interaction.guild.id)
        bonuses = dict(cfg['bonus_roles'])
        bonuses[str(role.id)] = int(multiplier)
        await self.bot.levels.update_settings(interaction.guild.id, bonus_roles=bonuses)
        await interaction.response.send_message(
            embed=success_embed('XP bonus saved', f'{role.mention} now receives **{multiplier}x XP**.'),
            ephemeral=True,
        )

    @app_commands.command(name='level-bonus-remove', description='Remove a role XP multiplier')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def level_bonus_remove(self, interaction: discord.Interaction, role: discord.Role):
        cfg = await self.bot.levels.settings(interaction.guild.id)
        bonuses = dict(cfg['bonus_roles'])
        bonuses.pop(str(role.id), None)
        await self.bot.levels.update_settings(interaction.guild.id, bonus_roles=bonuses)
        await interaction.response.send_message(
            embed=success_embed('XP bonus removed', f'{role.mention} no longer receives a leveling multiplier.'),
            ephemeral=True,
        )

    @app_commands.command(name='exclude-channel', description='Exclude a channel from XP')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def exclude_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        cfg = await self.bot.levels.settings(interaction.guild.id)
        channels = set(cfg['no_xp_channels'])
        channels.add(channel.id)
        await self.bot.levels.update_settings(interaction.guild.id, no_xp_channels=list(channels))
        await interaction.response.send_message(
            embed=success_embed('XP exclusion added', f'{channel.mention} will no longer award XP.'),
            ephemeral=True,
        )

    @app_commands.command(name='exclude-role', description='Exclude a role from XP')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def exclude_role(self, interaction: discord.Interaction, role: discord.Role):
        cfg = await self.bot.levels.settings(interaction.guild.id)
        roles = set(cfg['no_xp_roles'])
        roles.add(role.id)
        await self.bot.levels.update_settings(interaction.guild.id, no_xp_roles=list(roles))
        await interaction.response.send_message(
            embed=success_embed('XP exclusion added', f'{role.mention} will no longer award XP.'),
            ephemeral=True,
        )

    @app_commands.command(name='config', description='Alias for level settings')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(self, interaction: discord.Interaction):
        await self._send_settings(interaction)


async def setup(bot):
    await bot.add_cog(Levels(bot))
