import discord, random
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed, success_embed, error_embed

class Platform(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='case',description='View moderation cases for a member')
    @app_commands.guild_only()
    @app_commands.describe(member='Member')
    async def case(self,interaction:discord.Interaction,member:discord.Member):
        rows=await self.bot.platform.cases(interaction.guild.id,member.id)
        if not rows: return await interaction.response.send_message('No cases found.',ephemeral=True)
        e=discord.Embed(title=f'Cases • {member}',color=discord.Color.orange())
        e.description='\n'.join(f'`#{r.id}` **{r.action}** — {r.reason} (<@{r.moderator_id}>)' for r in rows)
        await interaction.response.send_message(embed=e,ephemeral=True)
    @app_commands.command(name='remind',description='Create a reminder')
    @app_commands.guild_only()
    async def remind(self,interaction:discord.Interaction,seconds:app_commands.Range[int,1,2592000],message:str):
        if not interaction.guild: return
        await self.bot.platform.add_reminder(interaction.guild.id,interaction.user.id,interaction.channel.id,seconds,message)
        embed = success_embed('Reminder scheduled', f"I'll remind you in **{seconds} seconds** in {interaction.channel.mention}.")
        embed.add_field(name='Message', value=message[:1024], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    @app_commands.command(name='suggest',description='Submit a suggestion')
    @app_commands.guild_only()
    async def suggest(self,interaction:discord.Interaction,content:str):
        await interaction.response.defer(ephemeral=True)
        row=await self.bot.platform.suggestion(interaction.guild.id,interaction.user.id,interaction.channel.id,interaction.id,content)
        await interaction.followup.send(embed=success_embed('Suggestion submitted', f'Your suggestion is **#{row.id}**.'), ephemeral=True)
    @app_commands.command(name='balance',description='Show your server balance')
    @app_commands.guild_only()
    async def balance(self,interaction:discord.Interaction):
        b=await self.bot.platform.balance(interaction.guild.id,interaction.user.id); embed=info_embed('Wallet', f'{interaction.user.mention} has **{b:,}** coins.'); await interaction.response.send_message(embed=embed,ephemeral=True)
    @app_commands.command(name='daily',description='Claim daily coins')
    @app_commands.guild_only()
    async def daily(self,interaction:discord.Interaction):
        allowed=await self.bot.limiter.allow(f'daily:{interaction.guild.id}:{interaction.user.id}',1,86400)
        if not allowed:
            return await interaction.response.send_message(embed=error_embed('Daily already claimed', 'You can claim the daily reward again after the cooldown resets.'),ephemeral=True)
        b=await self.bot.platform.change_balance(interaction.guild.id,interaction.user.id,100); embed=success_embed('Daily reward', f'You received **100 coins**.'); embed.add_field(name='New balance',value=f'**{b:,}**',inline=True); await interaction.response.send_message(embed=embed)
    @app_commands.command(name='coinflip',description='Flip a coin')
    @app_commands.guild_only()
    async def coinflip(self,interaction:discord.Interaction): await interaction.response.send_message(embed=info_embed('🪙 Coin flip', f'**{random.choice(("Heads","Tails"))}**'))
async def setup(bot):
    bot.platform_cog=Platform(bot); await bot.add_cog(bot.platform_cog)
