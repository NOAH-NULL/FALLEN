import discord
from discord import app_commands
from discord.ext import commands

class Security(commands.GroupCog,name='security'):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='raid-status',description='Show recent join burst status')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def raid_status(self,interaction:discord.Interaction):
        count=await self.bot.antiraid.count(interaction.guild.id); from bot.ui import info_embed
        await interaction.response.send_message(embed=info_embed('Raid status', f'**{count}** recent joins are currently tracked.'),ephemeral=True)
    @app_commands.command(name='lockdown',description='Lock every text channel')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self,interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channels = list(interaction.guild.text_channels)
        changed = await self.bot.security_lockdown(interaction.guild.id, reason=f'Lockdown by {interaction.user}')
        from bot.ui import success_embed
        await interaction.followup.send(embed=success_embed('Server locked', f'Locked **{changed}/{len(channels)}** text channels.'),ephemeral=True)
    @app_commands.command(name='unlockdown',description='Unlock every text channel')
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def unlockdown(self,interaction:discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channels = list(interaction.guild.text_channels)
        changed = await self.bot.security_unlockdown(interaction.guild.id, reason=f'Unlockdown by {interaction.user}')
        from bot.ui import success_embed
        await interaction.followup.send(embed=success_embed('Server unlocked', f'Unlocked **{changed}/{len(channels)}** text channels.'),ephemeral=True)
async def setup(bot): await bot.add_cog(Security(bot))
