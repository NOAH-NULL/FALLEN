import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed

# The 'fuck' action is intentionally a non-sexual, emphatic cartoon reaction.
SAFE_ACTIONS = {
    'hug': ('hug', '🤗', 'gave a friendly hug to'),
    'highfive': ('highfive', '✋', 'gave a high-five to'),
    'fistbump': ('fistbump', '👊', 'fist-bumped'),
    'pat': ('pat', '🫳', 'gave a friendly pat to'),
    'poke': ('poke', '👉', 'poked'),
    'bonk': ('bonk', '🔨', 'bonked'),
    'wave': ('wave', '👋', 'waved at'),
    'dance': ('dance', '💃', 'started dancing with'),
    'smile': ('smile', '😊', 'shared a smile with'),
    'cry': ('cry', '😢', 'cried dramatically near'),
    'shrug': ('shrug', '🤷', 'shrugged at'),
    'sleep': ('sleep', '😴', 'fell asleep near'),
    'boop': ('boop', '👉', 'booped'),
    'tickle': ('tickle', '✨', 'tickled'),
    'punch': ('punch', '👊', 'landed a cartoon punch on'),
    'slap': ('slap', '🖐️', 'landed a cartoon slap on'),
    'bite': ('bite', '🦷', 'gave a cartoon nibble to'),
    'hold': ('hold', '🫶', 'held onto'),
    'attack': ('punch', '⚔️', 'launched a cartoon attack at'),
    'shoot': ('punch', '💥', 'fired a cartoon confetti blaster at'),
    'bully': ('bonk', '😤', 'playfully bullied'),
    'pout': ('pout', '😗', 'pouted at'),
    'blush': ('blush', '😊', 'blushed at'),
    'kill': ('punch', '💀', 'cartoonishly defeated'),
    'wreck': ('punch', '💥', 'absolutely wrecked'),
}
SELF_ACTIONS = {'dance','smile','cry','shrug','sleep','pout','blush'}

class Fun(commands.Cog):
    def __init__(self, bot): self.bot = bot

    async def _action(self, interaction, action, member=None):
        target = member or interaction.user
        key, emoji, verb = SAFE_ACTIONS[action]
        url = await self.bot.reactions.get(key) if key else None
        if target.id == interaction.user.id:
            text = f'{interaction.user.mention} {verb} themselves!'
        else:
            text = f'{interaction.user.mention} {verb} {target.mention}!'
        embed = info_embed(f'{emoji} {action.title()}', text)
        if url: embed.set_image(url=url)
        embed.set_footer(text='Fallen • Fun & community')
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='kill', description='A cartoon action with GIF')
    async def kill(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'kill', member)

    @app_commands.command(name='hug', description='A polished Fallen community action')
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'hug', member)

    @app_commands.command(name='fistbump', description='A friendly cartoon fist-bump action')
    async def fistbump(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'fistbump', member)

    @app_commands.command(name='highfive', description='A polished Fallen community action')
    async def highfive(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'highfive', member)

    @app_commands.command(name='pat', description='A polished Fallen community action')
    async def pat(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'pat', member)

    @app_commands.command(name='poke', description='A polished Fallen community action')
    async def poke(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'poke', member)

    @app_commands.command(name='bonk', description='A polished Fallen community action')
    async def bonk(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'bonk', member)

    @app_commands.command(name='wave', description='A polished Fallen community action')
    async def wave(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'wave', member)

    @app_commands.command(name='dance', description='A polished Fallen community action')
    async def dance(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._action(interaction, 'dance', member)

    @app_commands.command(name='smile', description='A polished Fallen community action')
    async def smile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._action(interaction, 'smile', member)

    @app_commands.command(name='cry', description='A polished Fallen community action')
    async def cry(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._action(interaction, 'cry', member)

    @app_commands.command(name='shrug', description='A polished Fallen community action')
    async def shrug(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._action(interaction, 'shrug', member)

    @app_commands.command(name='sleep', description='A polished Fallen community action')
    async def sleep(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._action(interaction, 'sleep', member)

    @app_commands.command(name='boop', description='A polished Fallen community action')
    async def boop(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'boop', member)

    @app_commands.command(name='tickle', description='A polished Fallen community action')
    async def tickle(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'tickle', member)

    @app_commands.command(name='punch', description='A polished Fallen community action')
    async def punch(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'punch', member)

    @app_commands.command(name='slap', description='A polished Fallen community action')
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'slap', member)

    @app_commands.command(name='bite', description='A polished Fallen community action')
    async def bite(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'bite', member)

    @app_commands.command(name='hold', description='A polished Fallen community action')
    async def hold(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'hold', member)

    @app_commands.command(name='attack', description='A polished Fallen community action')
    async def attack(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'attack', member)

    @app_commands.command(name='shoot', description='A polished Fallen community action')
    async def shoot(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'shoot', member)

    @app_commands.command(name='bully', description='A polished Fallen community action')
    async def bully(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'bully', member)

    @app_commands.command(name='pout', description='A polished Fallen community action')
    async def pout(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._action(interaction, 'pout', member)

    @app_commands.command(name='blush', description='A polished Fallen community action')
    async def blush(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._action(interaction, 'blush', member)

    @app_commands.command(name='wreck', description='A cartoon action with a GIF')
    async def wreck(self, interaction: discord.Interaction, member: discord.Member):
        await self._action(interaction, 'wreck', member)

async def setup(bot): await bot.add_cog(Fun(bot))
