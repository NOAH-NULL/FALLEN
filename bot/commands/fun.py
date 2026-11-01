import inspect
import logging
import random
import time
from urllib.parse import urlparse

import discord
from discord.ext import commands

from bot.ui import info_embed


log = logging.getLogger(__name__)


SAFE_ACTIONS = {
    "hug": ("hug", "🤗", "gave a hug to", "hugged back"),
    "highfive": ("highfive", "✋", "gave a high-five to", "high-fived back"),
    "fistbump": ("fistbump", "👊", "fist-bumped", "fist-bumped back"),
    "pat": ("pat", "🫳", "gave a friendly pat to", "patted back"),
    "poke": ("poke", "👉", "poked", "poked back"),
    "bonk": ("bonk", "🔨", "bonked", "bonked back"),
    "wave": ("wave", "👋", "waved at", "waved back at"),
    "dance": ("dance", "💃", "started dancing with", "danced along with"),
    "smile": ("smile", "😊", "shared a smile with", "smiled back"),
    "cry": ("cry", "😢", "cried dramatically near", "cried along with"),
    "shrug": ("shrug", "🤷", "shrugged at", "shrugged back at"),
    "sleep": ("sleep", "😴", "fell asleep near", "slept near"),
    "boop": ("boop", "👉", "booped", "booped back"),
    "tickle": ("tickle", "✨", "tickled", "tickled back"),
    "punch": ("punch", "👊", "landed a playful punch on", "playfully punched back"),
    "slap": ("slap", "🖐️", "playfully slapped", "playfully slapped back"),
    "bite": ("bite", "🦷", "gave a nibble to", "bit back"),
    "hold": ("hold", "🫶", "held onto", "held back"),
    "attack": ("punch", "⚔️", "launched a playful attack at", "playfully attacked back"),
    "shoot": ("punch", "💥", "fired a confetti blaster at", "fired back"),
    "bully": ("bonk", "😤", "playfully bullied", "bullied back"),
    "pout": ("pout", "😗", "pouted at", "pouted back at"),
    "blush": ("blush", "😊", "blushed at", "blushed back at"),
    "kill": ("punch", "💀", "defeated", "retaliated against"),
    "wreck": ("punch", "💥", "absolutely wrecked", "wrecked back"),
    "kiss": ("kiss", "💋", "gave an affectionate kiss to", "returned the kiss"),
    "flirt": ("flirt", "😏", "flirted with", "flirted back with"),
    "yeet": ("yeet", "🚀", "yeeted", "yeeted back"),
    "roast": ("roast", "🔥", "roasted", "roasted back"),
    "stare": ("stare", "👀", "stared at", "stared back at"),
    "facepalm": ("facepalm", "🤦", "facepalmed at", "facepalmed back at"),
    "cheer": ("cheer", "🎉", "cheered for", "cheered back for"),
    "clap": ("clap", "👏", "clapped for", "clapped back for"),
    "laugh": ("laugh", "😂", "laughed with", "laughed back with"),
    "salute": ("salute", "🎖️", "saluted", "saluted back"),
    "feed": ("feed", "🍪", "fed a cookie to", "fed a cookie back to"),
    "nom": ("nom", "😋", "nommed on", "nommed back on"),
    "comfort": ("comfort", "🫂", "comforted", "comforted back"),
    "bow": ("bow", "🙇", "bowed to", "bowed back to"),
}


GIF_FALLBACKS = {
    "flirt": "blush",
    "kiss": "hug",
    "pout": "cry",
    "blush": "smile",
    "yeet": "punch",
    "roast": "slap",
    "stare": "poke",
    "facepalm": "cry",
    "cheer": "wave",
    "clap": "highfive",
    "laugh": "smile",
    "salute": "wave",
    "feed": "hug",
    "nom": "bite",
    "comfort": "hug",
    "bow": "wave",
}


GIF_POOL_MIN = 10
GIF_POOL_MAX = 30
GIF_MISS_TTL = 300
GIF_URL_TTL = 6 * 3600


def _is_valid_url(value) -> bool:
    """Validate a well-formed HTTP(S) URL."""
    if (
        not isinstance(value, str)
        or len(value) > 2000
        or any(c.isspace() for c in value)
    ):
        return False

    try:
        parts = urlparse(value)
        return (
            parts.scheme in ("http", "https")
            and bool(parts.hostname)
        )
    except ValueError:
        return False


class ActionView(discord.ui.View):
    def __init__(
        self,
        cog,
        action: str,
        initiator: discord.Member,
        target: discord.Member,
    ):
        super().__init__(timeout=180)
        self.cog = cog
        self.action = action
        self.initiator = initiator
        self.target = target
        self.used = False
        self.message: discord.Message | None = None

        action_data = SAFE_ACTIONS[action]
        emoji = action_data[1]

        self.reciprocate_button = discord.ui.Button(
            label=f"{action.capitalize()} back!",
            style=discord.ButtonStyle.primary,
            emoji=emoji,
        )
        self.reciprocate_button.callback = self.reciprocate_callback
        self.add_item(self.reciprocate_button)

    async def reciprocate_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                f"Only {self.target.mention} can use this button!",
                ephemeral=True,
            )
            return

        if self.used:
            await interaction.response.send_message("Already used!", ephemeral=True)
            return

        self.used = True

        try:
            self.reciprocate_button.disabled = True
            await interaction.response.edit_message(view=self)

            await self.cog._execute_action(
                ctx_or_interaction=interaction,
                action=self.action,
                target=self.initiator,
                is_reciprocal=True,
            )
        except Exception:
            log.exception(
                "Reciprocal %r failed (initiator=%s, target=%s)",
                self.action,
                self.initiator.id,
                self.target.id,
            )
            self.used = False
            self.reciprocate_button.disabled = False
            error_text = "Something went wrong sending that. Please try the button again."
            try:
                if interaction.response.is_done():
                    await interaction.edit_original_response(view=self)
                    await interaction.followup.send(error_text, ephemeral=True)
                else:
                    await interaction.response.send_message(error_text, ephemeral=True)
            except discord.HTTPException:
                log.warning("Could not report reciprocal failure", exc_info=True)
            return

        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        log.error("ActionView error (action=%r)", self.action, exc_info=error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send("Something went wrong. Please try again.", ephemeral=True)
            else:
                await interaction.response.send_message("Something went wrong. Please try again.", ephemeral=True)
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        self.reciprocate_button.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ConsentView(discord.ui.View):
    """Accept / Decline prompt with reaction GIF integration."""

    def __init__(self, cog, initiator: discord.Member, target: discord.Member):
        super().__init__(timeout=120)
        self.cog = cog
        self.initiator = initiator
        self.target = target
        self.message: discord.Message | None = None

    def _disable_all(self):
        for item in self.children:
            item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message(
                f"Only {self.target.mention} can answer this!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._disable_all()

        gif_url = await self.cog._get_reaction_url("fuck")
        if not gif_url:
            gif_url = await self.cog._get_reaction_url("kiss")

        embed = info_embed(
            "🔞 Fuck",
            f"{self.target.mention} accepted! {self.initiator.mention} fucked {self.target.mention}!"
        )
        if gif_url:
            embed.set_image(url=gif_url)

        embed.set_footer(text="Fallen • Fun & community")
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="✖️")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        self._disable_all()
        embed = info_embed("🔞 Fuck", f"{self.target.mention} declined.")
        embed.set_footer(text="Fallen • Fun & community")
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        log.error("ConsentView error", exc_info=error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send("Something went wrong. Please try again.", ephemeral=True)
            else:
                await interaction.response.send_message("Something went wrong. Please try again.", ephemeral=True)
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        self._disable_all()
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._counts: dict[tuple[int, int, str], int] = {}
        self._gif_pool: dict[str, dict[str, float]] = {}
        self._gif_miss: dict[str, float] = {}

        cog_commands = list(getattr(self, "__cog_commands__", []))

        # Dynamically register hybrid commands for standard actions
        for action_name in SAFE_ACTIONS:
            def make_callback(action):
                async def dynamic_command(
                    self_cog,
                    ctx: commands.Context,
                    member: discord.Member | None = None,
                ):
                    await self_cog._handle_cmd(ctx, action, member)
                return dynamic_command

            callback = make_callback(action_name)
            callback.__name__ = action_name
            callback.__doc__ = f"Playfully {action_name} someone"

            hybrid_cmd = commands.hybrid_command(
                name=action_name,
                description=f"Playfully {action_name} someone",
            )(callback)

            cog_commands.append(hybrid_cmd)

        self.__cog_commands__ = cog_commands

    def _resolve_target(
        self,
        ctx_or_interaction: commands.Context | discord.Interaction,
        member: discord.Member | None,
    ) -> discord.Member | None:
        if member:
            return member

        if isinstance(ctx_or_interaction, commands.Context):
            message = ctx_or_interaction.message
            if message and message.reference:
                resolved_msg = message.reference.resolved
                if isinstance(resolved_msg, discord.Message):
                    author = resolved_msg.author
                    if isinstance(author, discord.Member):
                        return author
                    guild = ctx_or_interaction.guild
                    return guild.get_member(author.id) if guild else None

        return None

    async def _get_reaction_url(self, key: str) -> str | None:
        if not key or not hasattr(self.bot, "reactions"):
            return None

        miss_until = self._gif_miss.get(key)
        if miss_until and time.monotonic() < miss_until:
            return None

        pool = self._gif_pool.setdefault(key, {})
        now = time.monotonic()
        stale_urls = [url for url, seen in pool.items() if now - seen > GIF_URL_TTL]
        for url in stale_urls:
            del pool[url]

        if len(pool) >= GIF_POOL_MIN and (len(pool) >= GIF_POOL_MAX or random.random() > 0.2):
            return random.choice(list(pool))

        try:
            result = self.bot.reactions.get(key)
            result = await result if inspect.isawaitable(result) else result
        except Exception:
            log.warning("Reaction provider failed for key %r", key, exc_info=True)
            self._gif_miss[key] = time.monotonic() + GIF_MISS_TTL
            return None

        if _is_valid_url(result):
            self._gif_miss.pop(key, None)
            if result in pool or len(pool) < GIF_POOL_MAX:
                pool[result] = time.monotonic()
            return result

        self._gif_miss[key] = time.monotonic() + GIF_MISS_TTL
        return None

    async def _bump_count(
        self,
        guild_id: int,
        user_id: int,
        action: str,
        delta: int = 1,
    ) -> tuple[int, bool]:
        redis = getattr(self.bot, "redis", None)
        if redis is not None:
            try:
                result = redis.hincrby(
                    f"fun:counts:{guild_id}:{user_id}",
                    action,
                    delta,
                )
                result = await result if inspect.isawaitable(result) else result
                return int(result), True
            except Exception:
                log.exception(
                    "Redis counter update failed; refusing to split counter storage"
                )
                raise
        key = (guild_id, user_id, action)
        self._counts[key] = max(
            0,
            self._counts.get(key, 0) + delta,
        )
        return self._counts[key], False

    async def _rollback_count(
        self,
        guild_id: int,
        user_id: int,
        action: str,
        used_redis: bool,
    ) -> None:
        if used_redis:
            redis = getattr(self.bot, "redis", None)
            if redis is None:
                log.error("Cannot roll back Redis counter: Redis unavailable")
                return
            try:
                result = redis.hincrby(f"fun:counts:{guild_id}:{user_id}", action, -1)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                log.exception("Redis counter rollback failed")
            return

        key = (guild_id, user_id, action)
        self._counts[key] = max(0, self._counts.get(key, 0) - 1)

    async def _execute_action(
        self,
        ctx_or_interaction: commands.Context | discord.Interaction,
        action: str,
        target: discord.Member | None,
        is_reciprocal: bool = False,
    ):
        is_interaction = isinstance(
            ctx_or_interaction,
            discord.Interaction,
        )

        user = (
            ctx_or_interaction.user
            if is_interaction
            else ctx_or_interaction.author
        )

        target_member = target or user
        action_data = SAFE_ACTIONS[action]

        if len(action_data) == 3:
            key, emoji, initial_verb = action_data
            reciprocate_verb = initial_verb
        else:
            key, emoji, initial_verb, reciprocate_verb = action_data

        url = await self._get_reaction_url(key)

        if not url:
            fallback_key = GIF_FALLBACKS.get(key, "")

            if fallback_key:
                url = await self._get_reaction_url(
                    fallback_key
                )

        if target_member.id == user.id:
            text = (
                f"{user.mention} {initial_verb} themselves!\n"
                "*Tip: mention someone or reply to their message to target them.*"
            )
            view = None
        elif is_reciprocal:
            text = (
                f"{user.mention} {reciprocate_verb} "
                f"{target_member.mention}!"
            )
            view = None
        else:
            text = (
                f"{user.mention} {initial_verb} "
                f"{target_member.mention}!"
            )
            view = ActionView(
                self,
                action,
                user,
                target_member,
            )

        guild = ctx_or_interaction.guild
        guild_id = guild.id if guild else 0

        count, used_redis = await self._bump_count(
            guild_id,
            user.id,
            action,
        )

        embed = info_embed(
            f"{emoji} {action.title()}",
            text,
        )

        if url:
            embed.set_image(url=url)

        embed.set_footer(
            text=(
                f"{user.display_name} has used {action} "
                f"{count} time{'s' if count != 1 else ''} "
                "• Fallen"
            )
        )

        kwargs = {"embed": embed}

        if view is not None:
            kwargs["view"] = view

        message = None
        delivered = False

        try:
            if is_interaction:
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.defer()

                message = await ctx_or_interaction.followup.send(
                    wait=True,
                    **kwargs,
                )
                delivered = True
            else:
                message = await ctx_or_interaction.send(
                    **kwargs,
                )
                delivered = True

        except Exception:
            if not delivered:
                await self._rollback_count(
                    guild_id,
                    user.id,
                    action,
                    used_redis,
                )

            raise

        if view is not None and message is not None:
            view.message = message

    async def _handle_cmd(
        self,
        ctx_or_interaction: commands.Context | discord.Interaction,
        action: str,
        member: discord.Member | None = None,
    ):
        ctx = ctx_or_interaction
        if ctx.guild is None:
            await ctx.send("These commands only work in servers.", ephemeral=True)
            return

        target = self._resolve_target(ctx, member)
        replied = bool(ctx.message and ctx.message.reference)

        if member is None and replied and target is None:
            await ctx.send("I couldn't find that person in this server.", ephemeral=True)
            return

        if target is not None and (
            not isinstance(target, discord.Member) or target.guild.id != ctx.guild.id
        ):
            await ctx.send("I couldn't find that person in this server.", ephemeral=True)
            return

        if target is not None and target.bot:
            await ctx.send("You can't do that to a bot!", ephemeral=True)
            return

        await self._execute_action(ctx, action, target)

    @commands.hybrid_command(name="fuck", description="NSFW channels only - the other person must accept")
    @commands.guild_only()
    @commands.is_nsfw()
    async def fuck(self, ctx: commands.Context, member: discord.Member | None = None):
        target = self._resolve_target(ctx, member)
        if (
            target is None
            or not isinstance(target, discord.Member)
            or target.guild.id != ctx.guild.id
            or target.id == ctx.author.id
            or target.bot
        ):
            await ctx.send("Mention someone else (or reply to their message)!", ephemeral=True)
            return

        view = ConsentView(self, ctx.author, target)
        embed = info_embed(
            "🔞 Fuck",
            f"{ctx.author.mention} wants to fuck {target.mention}.\n"
            f"{target.mention}, do you accept?"
        )
        embed.set_footer(text="Fallen • Fun & community")
        view.message = await ctx.send(
            content=target.mention,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(users=[target]),
        )

    @fuck.error
    async def fuck_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.NSFWChannelRequired):
            await ctx.send("This command only works in age-restricted (NSFW) channels.", ephemeral=True)
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command only works in servers.", ephemeral=True)
        else:
            raise error


async def setup(bot):
    await bot.add_cog(Fun(bot))
