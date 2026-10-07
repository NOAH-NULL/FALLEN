import discord
from discord import app_commands
from discord.ext import commands


class Levels(commands.GroupCog, name='level'):
    """Leveling controls for viewing levels and configuring dedicated channels."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='show', description='Show a member level')
    @app_commands.guild_only()
    @app_commands.describe(member='Member to inspect')
    async def show(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        row = await self.bot.levels.get(interaction.guild.id, member.id)
        level = int(row.level) if row else 0
        xp = int(row.xp) if row else 0
        total = int(row.total_xp) if row else 0
        await interaction.response.send_message(
            f'🏆 {member.mention}: **Level {level}** · **{xp} XP** progress · **{total} total XP**.',
            ephemeral=True,
        )

    @app_commands.command(name='channel', description='Set the dedicated level-up announcement channel')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel='Channel where level-up announcements should be sent')
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        me = interaction.guild.me
        if me is None:
            return await interaction.response.send_message('❌ I cannot resolve my server member.', ephemeral=True)
        permissions = channel.permissions_for(me)
        missing = [
            name for name, ok in (
                ('View Channel', permissions.view_channel),
                ('Send Messages', permissions.send_messages),
                ('Embed Links', permissions.embed_links),
            ) if not ok
        ]
        if missing:
            return await interaction.response.send_message(
                f'❌ I cannot use {channel.mention}. Missing: **{", ".join(missing)}**.',
                ephemeral=True,
            )
        await self.bot.levels.update_settings(
            interaction.guild.id,
            announcement_channel_id=channel.id,
            announce=True,
        )
        await interaction.response.send_message(
            f'✅ Level-up announcements are now sent only in {channel.mention}.',
            ephemeral=True,
        )

    @app_commands.command(name='channel-reset', description='Send level-up announcements in the channel where the user levels up')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel_reset(self, interaction: discord.Interaction):
        await self.bot.levels.update_settings(
            interaction.guild.id,
            announcement_channel_id=None,
        )
        await interaction.response.send_message(
            '✅ Dedicated level-up channel disabled. Announcements use the current message channel again.',
            ephemeral=True,
        )

    @app_commands.command(name='xp-channel', description='Only award XP from this channel')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel='Only this channel will generate leveling XP')
    async def xp_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.levels.update_settings(
            interaction.guild.id,
            xp_channels=[channel.id],
        )
        await interaction.response.send_message(
            f'✅ Leveling XP is now earned only from {channel.mention}.',
            ephemeral=True,
        )

    @app_commands.command(name='xp-channel-reset', description='Allow XP in every channel except excluded channels')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def xp_channel_reset(self, interaction: discord.Interaction):
        await self.bot.levels.update_settings(
            interaction.guild.id,
            xp_channels=[],
        )
        await interaction.response.send_message(
            '✅ XP channel restriction removed. Leveling can use all normal channels again.',
            ephemeral=True,
        )

    async def _send_config(self, interaction: discord.Interaction):
        cfg = await self.bot.levels.settings(interaction.guild.id)
        announce_channel = (
            interaction.guild.get_channel(cfg['announcement_channel_id'])
            if cfg['announcement_channel_id']
            else None
        )
        xp_channels = [
            interaction.guild.get_channel(channel_id)
            for channel_id in cfg['xp_channels']
        ]
        xp_channels = [channel for channel in xp_channels if channel is not None]
        announcement_text = announce_channel.mention if announce_channel else 'message channel'
        xp_text = ', '.join(channel.mention for channel in xp_channels) if xp_channels else 'all eligible channels'
        await interaction.response.send_message(
            f'📈 **Leveling config**\n'
            f'Announcements: {announcement_text}\n'
            f'XP channels: {xp_text}\n'
            f'Announcements enabled: **{cfg["announce"]}**',
            ephemeral=True,
        )

    @app_commands.command(name='settings', description='Show current leveling settings')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings_cmd(self, interaction: discord.Interaction):
        await self._send_config(interaction)

    @app_commands.command(name='config', description='Show current leveling channel configuration')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(self, interaction: discord.Interaction):
        await self._send_config(interaction)


async def setup(bot):
    await bot.add_cog(Levels(bot))
