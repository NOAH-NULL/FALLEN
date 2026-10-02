import discord, random
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed, success_embed, error_embed


class Engagement(commands.GroupCog, name='engage'):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='poll', description='Create a simple poll')
    async def poll(self, interaction: discord.Interaction, question: str):
        if len(question) > 250:
            return await interaction.response.send_message(embed=error_embed('Poll too long', 'Keep the question under 250 characters.'), ephemeral=True)
        embed = info_embed('📊 Community Poll', question)
        embed.add_field(name='Vote', value='👍 Yes\n👎 No', inline=False)
        embed.set_footer(text=f'Created by {interaction.user.display_name}')
        message = await interaction.channel.send(embed=embed)
        for emoji in ('👍', '👎'):
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                pass
        await interaction.response.send_message(embed=success_embed('Poll created', f'Your poll is live in {interaction.channel.mention}.'), ephemeral=True)

    @app_commands.command(name='8ball', description='Ask the magic 8-ball')
    async def eightball(self, interaction: discord.Interaction, question: str):
        if not question.strip():
            return await interaction.response.send_message(embed=error_embed('Question required', 'Ask the 8-ball something first.'), ephemeral=True)
        answer = random.choice(('Yes.', 'No.', 'Maybe.', 'Ask again later.', 'Definitely.'))
        embed = info_embed('🎱 Magic 8-Ball', f'**Question:** {question[:500]}\n\n**Answer:** {answer}')
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='choose', description='Choose between options separated by |')
    async def choose(self, interaction: discord.Interaction, options: str):
        vals = [x.strip() for x in options.split('|') if x.strip()]
        if len(vals) < 2:
            return await interaction.response.send_message(embed=error_embed('Not enough options', 'Give at least two options separated by `|`.'), ephemeral=True)
        if len(vals) > 20:
            return await interaction.response.send_message(embed=error_embed('Too many options', 'Keep the choice list to 20 options or fewer.'), ephemeral=True)
        selected = random.choice(vals)
        embed = success_embed('Choice made', f'🎯 I choose **{selected[:200]}**.')
        embed.add_field(name='Options', value=' • '.join(f'`{v[:80]}`' for v in vals), inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Engagement(bot))
