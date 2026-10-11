import inspect
import discord
from discord import app_commands
from discord.ext import commands
from bot.ui import info_embed

SAFE_ACTIONS = {
    'hug': ('hug', '🤗', 'gave a friendly hug to', 'hugged back'),
    'fuck': ('fuck', '💋', 'fuck'),
    'highfive': ('highfive', '✋', 'gave a high-five to', 'high-fived back'),
    'fistbump': ('fistbump', '👊', 'fist-bumped', 'fist-bumped back'),
    'pat': ('pat', '🫳', 'gave a friendly pat to', 'patted back'),
    'poke': ('poke', '👉', 'poked', 'poked back'),
    'bonk': ('bonk', '🔨', 'bonked', 'bonked back'),
    'wave': ('wave', '👋', 'waved at', 'waved back at'),
    'dance': ('dance', '💃', 'started dancing with', 'danced along with'),
    'smile': ('smile', '😊', 'shared a smile with', 'smiled back at'),
    'cry': ('cry', '😢', 'cried dramatically near', 'cried along with'),
    'shrug': ('shrug', '🤷', 'shrugged at', 'shrugged back at'),
    'sleep': ('sleep', '😴', 'fell asleep near', 'slept near'),
    'boop': ('boop', '👉', 'booped', 'booped back'),
    'tickle': ('tickle', '✨', 'tickled', 'tickled back'),
    'punch': ('punch', '👊', 'landed a punch on', 'punched back'),
    'slap': ('slap', '🖐️', 'landed a slap on', 'slapped back'),
    'bite': ('bite', '🦷', 'gave a nibble to', 'bit back'),
    'hold': ('hold', '🫶', 'held onto', 'held back'),
    'attack': ('punch', '⚔️', 'launched an attack at', 'attacked back'),
    'shoot': ('punch', '💥', 'fired a confetti blaster at', 'shot back'),
    'bully': ('bonk', '😤', 'playfully bullied', 'bullied back'),
    'pout': ('pout', '😗', 'pouted at', 'pouted back at'),
    'blush': ('blush', '😊', 'blushed at', 'blushed back at'),
    'kill': ('punch', '💀', 'defeated', 'retaliated against'),
    'wreck': ('punch', '💥', 'absolutely wrecked', 'wrecked back'),
    'kiss': ('kiss', '💋', 'kissed affectionately', 'kissed back'),
    'flirt': ('flirt', '🫦', 'flirted with', 'flirted back with'),
}


class ActionView(discord.ui.View):
    def __init__(self, cog, action: str, initiator: discord.Member, target: discord.Member):
        super().__init__(timeout=180)
        self.cog = cog
        self.action = action
        self.initiator = initiator
        self.target = target

        action_data = SAFE_ACTIONS[action]
        emoji = action_data[1]

        button_label = f"{action.capitalize()} back!"
        self.reciprocate_button = discord.ui.Button(
            label=button_label,
            style=discord.ButtonStyle.primary,
            emoji=emoji
        )
        self.reciprocate_button.callback = self.reciprocate_callback
        self.add_item(self.reciprocate_button)

    async def reciprocate_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                f"Only {self.target.mention} can use this button!",
                ephemeral=True
            )
            return

        await self.cog._execute_action(
            ctx_or_interaction=interaction,
            action=self.action,
            target=self.initiator,
            is_reciprocal=True
        )


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _resolve_target(self, ctx_or_interaction, member: discord.Member | None) -> discord.Member | None:
        if member:
            return member

        if isinstance(ctx_or_interaction, commands.Context):
            if ctx_or_interaction.message and ctx_or_interaction.message.reference:
                resolved_msg = ctx_or_interaction.message.reference.resolved
                if isinstance(resolved_msg, discord.Message):
                    return resolved_msg.author

        return None

    async def _get_reaction_url(self, key: str) -> str | None:
        if not key or not hasattr(self.bot, 'reactions'):
            return None
        res = self.bot.reactions.get(key)
        return await res if inspect.isawaitable(res) else res

    async def _execute_action(
        self, 
        ctx_or_interaction, 
        action: str, 
        target: discord.Member | None, 
        is_reciprocal: bool = False
    ):
        is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
        user = ctx_or_interaction.user if is_interaction else ctx_or_interaction.author

        target_member = target or user
        action_data = SAFE_ACTIONS[action]
        
        if len(action_data) == 3:
            key, emoji, initial_verb = action_data
            reciprocate_verb = initial_verb
        else:
            key, emoji, initial_verb, reciprocate_verb = action_data

        url = await self._get_reaction_url(key)

        # Explicit branch separation between self-action and target-action
        if target_member.id == user.id:
            text = f"{user.mention} {initial_verb} themselves!"
            view = None
        else:
            active_verb = reciprocate_verb if is_reciprocal else initial_verb
            text = f"{user.mention} {active_verb} {target_member.mention}!"
            view = ActionView(self, action, user, target_member)

        embed = info_embed(f"{emoji} {action.title()}", text)
        if url:
            embed.set_image(url=url)
        embed.set_footer(text="Fallen • Fun & community")

        if is_interaction:
            if ctx_or_interaction.response.is_done():
                await ctx_or_interaction.followup.send(embed=embed, view=view)
            else:
                await ctx_or_interaction.response.send_message(embed=embed, view=view)
        else:
            await ctx_or_interaction.send(embed=embed, view=view)

    async def _handle_cmd(self, ctx_or_interaction, action: str, member: discord.Member | None = None):
        target = self._resolve_target(ctx_or_interaction, member)
        await self._execute_action(ctx_or_interaction, action, target)
        
    @commands.hybrid_command(name="fuck", description="fuck")
    async def fuck(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "fuck", member)

    @commands.hybrid_command(name="kill", description="kill")
    async def kill(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "kill", member)

    @commands.hybrid_command(name="hug", description="hugs")
    async def hug(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "hug", member)

    @commands.hybrid_command(name="highfive", description="highfive")
    async def highfive(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "highfive", member)

    @commands.hybrid_command(name="fistbump", description="firstbump")
    async def fistbump(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "fistbump", member)

    @commands.hybrid_command(name="pat", description="pat")
    async def pat(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "pat", member)

    @commands.hybrid_command(name="poke", description="poke")
    async def poke(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "poke", member)

    @commands.hybrid_command(name="bonk", description="bonk!")
    async def bonk(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "bonk", member)

    @commands.hybrid_command(name="wave", description="wave")
    async def wave(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "wave", member)

    @commands.hybrid_command(name="dance", description="dance")
    async def dance(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "dance", member)

    @commands.hybrid_command(name="smile", description="smile")
    async def smile(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "smile", member)

    @commands.hybrid_command(name="cry", description="cry")
    async def cry(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "cry", member)

    @commands.hybrid_command(name="shrug", description="shrug")
    async def shrug(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "shrug", member)

    @commands.hybrid_command(name="sleep", description="sleep")
    async def sleep(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "sleep", member)

    @commands.hybrid_command(name="boop", description="boop")
    async def boop(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "boop", member)

    @commands.hybrid_command(name="tickle", description="tickle")
    async def tickle(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "tickle", member)

    @commands.hybrid_command(name="punch", description="punch")
    async def punch(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "punch", member)

    @commands.hybrid_command(name="slap", description="slap")
    async def slap(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "slap", member)

    @commands.hybrid_command(name="bite", description="bites")
    async def bite(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "bite", member)

    @commands.hybrid_command(name="hold", description="hold")
    async def hold(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "hold", member)

    @commands.hybrid_command(name="attack", description="attack")
    async def attack(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "attack", member)

    @commands.hybrid_command(name="shoot", description="shoot")
    async def shoot(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "shoot", member)

    @commands.hybrid_command(name="bully", description="bully")
    async def bully(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "bully", member)

    @commands.hybrid_command(name="pout", description="pout")
    async def pout(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "pout", member)

    @commands.hybrid_command(name="blush", description="blushes")
    async def blush(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "blush", member)

    @commands.hybrid_command(name="wreck", description="wreck")
    async def wreck(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "wreck", member)

    @commands.hybrid_command(name="kiss", description="kisses")
    async def kiss(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "kiss", member)

    @commands.hybrid_command(name="flirt", description="flirt")
    async def flirt(self, ctx: commands.Context, member: discord.Member | None = None):
        await self._handle_cmd(ctx, "flirt", member)


async def setup(bot):
    await bot.add_cog(Fun(bot))
