import asyncio
import time
from io import BytesIO

import discord

from bot.core.metrics import WORK_QUEUE
from bot.services.welcome_engine import DEFAULT_SETTINGS


DEFAULT_MESSAGES = {
    "welcome": "Welcome {mention} to {server}! You are member #{count}.",
    "goodbye": "Goodbye {name}!",
}
DEFAULT_TITLES = {
    "welcome": "Welcome!",
    "goodbye": "Goodbye!",
}
DEFAULT_DESCRIPTIONS = {
    "welcome": "{mention} just joined {server}! 🎉",
    "goodbye": "{name} has left {server}. 👋",
}
DEFAULT_COLORS = {
    "welcome": 5793266,
    "goodbye": 9807270,
}


class GreetingWorker:
    """Resilient welcome/goodbye delivery pipeline."""

    def __init__(self, bot, size=256, workers=4, max_event_age=30.0):
        self.bot = bot
        self.queue = asyncio.Queue(maxsize=size)
        self.workers = workers
        self.max_event_age = max(1.0, max_event_age)
        self.tasks = []

    async def start(self):
        self.tasks = [
            asyncio.create_task(self._run(), name=f"greeting-worker-{i}")
            for i in range(self.workers)
        ]

    async def submit(self, member, kind, force_channel=None, invite_id=None, invite_uses=0):
        try:
            self.queue.put_nowait(
                (time.monotonic(), member, kind, force_channel, invite_id, invite_uses)
            )
            WORK_QUEUE.labels("greetings").set(self.queue.qsize())
            return True
        except asyncio.QueueFull:
            WORK_QUEUE.labels("greetings").set(self.queue.qsize())
            return False

    @staticmethod
    def _format(value, member, count, inviter_id=None, invite_uses=0):
        from bot.services.greeting import GreetingRenderer

        try:
            return GreetingRenderer.format_template(
                member, value or "", count, inviter_id, invite_uses
            )
        except (KeyError, ValueError, AttributeError, TypeError):
            return value or ""

    @staticmethod
    def _button_view(settings):
        from bot.services.welcome_engine import WelcomeEngine

        return WelcomeEngine.button_view(settings)

    @staticmethod
    def _color(cfg, kind):
        try:
            return int(cfg.get(f"{kind}_embed_color") or DEFAULT_COLORS[kind])
        except (TypeError, ValueError):
            return DEFAULT_COLORS[kind]

    async def _send_public(self, channel, *, embed, rendered, filename, view, settings):
        attempts = int(settings.get("retry_attempts", 2))
        backoff = float(settings.get("retry_backoff", 0.75))

        async def operation():
            return await channel.send(
                content=None,
                embed=embed,
                file=discord.File(BytesIO(rendered), filename=filename),
                view=view,
                allowed_mentions=discord.AllowedMentions(
                    users=True, roles=False, everyone=False
                ),
            )

        return await self.bot.welcome_engine.retry(operation, attempts, backoff)

    async def _send_dm(self, member, *, embed, rendered, filename, view, settings):
        attempts = int(settings.get("dm_retry", 1))
        backoff = float(settings.get("retry_backoff", 0.75))

        async def operation():
            return await member.send(
                embed=embed,
                file=discord.File(BytesIO(rendered), filename=filename),
                view=view,
            )

        return await self.bot.welcome_engine.retry(operation, attempts, backoff)

    def _build_embed(
        self,
        cfg,
        settings,
        member,
        kind,
        count,
        invite_id,
        invite_uses,
        filename,
        risk=None,
    ):
        if not cfg.get(f"{kind}_embed_enabled", True):
            return None

        title = self._format(
            cfg.get(f"{kind}_embed_title") or DEFAULT_TITLES[kind],
            member,
            count,
            invite_id,
            invite_uses,
        )[:256]
        description = self._format(
            cfg.get(f"{kind}_embed_description") or DEFAULT_DESCRIPTIONS[kind],
            member,
            count,
            invite_id,
            invite_uses,
        )[:4096]
        embed = discord.Embed(
            title=title or None,
            description=description or None,
            color=self._color(cfg, kind),
            timestamp=discord.utils.utcnow(),
        )

        if getattr(member, "display_avatar", None):
            embed.set_thumbnail(url=member.display_avatar.url)
        if getattr(member.guild, "icon", None):
            embed.set_author(name=member.guild.name, icon_url=member.guild.icon.url)

        if kind == "welcome":
            if settings.get("show_details", True):
                embed.add_field(name="Member", value=f"#{count}", inline=True)

            if settings.get("show_joined_at", True) and getattr(member, "joined_at", None):
                embed.add_field(
                    name="Joined",
                    value=discord.utils.format_dt(member.joined_at, style="R"),
                    inline=True,
                )

            if settings.get("show_account_created", True):
                created = getattr(member, "created_at", None)
                value = (
                    discord.utils.format_dt(created, style="R")
                    if created
                    else "Unknown"
                )
                embed.add_field(name="Account", value=value, inline=True)

            inviter_member = (
                member.guild.get_member(invite_id) if invite_id else None
            )
            if settings.get("show_inviter", True) and inviter_member:
                value = inviter_member.mention
                if settings.get("show_invites", True):
                    value += f"\n{int(invite_uses or 0)} tracked uses"
                embed.add_field(name="Invited by", value=value, inline=True)

            if settings.get("show_risk", True) and risk:
                if risk["is_new"]:
                    risk_value = f"⚠️ **{risk['label']}** • {risk['age_days']}d old • {risk['score']}/100"
                else:
                    risk_value = "✅ Normal account age"
                embed.add_field(name="Account check", value=risk_value, inline=True)

        embed.set_image(url=f"attachment://{filename}")
        if kind == "welcome":
            footer = f"{member.guild.name} • Member #{count}"
        else:
            footer = f"{member.guild.name} • Goodbye"
        embed.set_footer(text=footer)
        return embed

    async def deliver(
        self,
        member,
        kind,
        force_channel=None,
        invite_id=None,
        invite_uses=0,
    ):
        if kind not in ("welcome", "goodbye"):
            raise ValueError("Unknown greeting kind.")
        if getattr(member, "guild", None) is None:
            raise ValueError("Greetings can only be sent in a server.")

        cfg = await self.bot.guild_config.get(member.guild.id)
        settings = (
            await self.bot.welcome_engine.get(member.guild.id, cfg)
            if kind == "welcome"
            else dict(DEFAULT_SETTINGS, enabled=True, public_enabled=True, dm_enabled=False)
        )

        if kind == "welcome":
            if not self.bot.welcome_engine.should_deliver(member, kind, settings):
                return False
            if not self.bot.welcome_engine.claim(
                member, kind, settings.get("dedupe_seconds", 90)
            ):
                self.bot.log.info(
                    "suppressed duplicate welcome guild=%s member=%s",
                    member.guild.id,
                    member.id,
                )
                return False

        public_enabled = kind == "goodbye" or bool(settings.get("public_enabled", True))
        dm_enabled = kind == "welcome" and bool(settings.get("dm_enabled"))

        channel = force_channel
        if channel is None and public_enabled:
            channel_id = cfg.get(f"{kind}_channel_id")
            channel = (
                member.guild.get_channel(channel_id)
                if channel_id
                else None
            )

        if public_enabled and channel is None:
            if not dm_enabled:
                raise ValueError(f"No {kind} channel is configured.")
            self.bot.log.warning(
                "welcome public channel missing; continuing with DM only guild=%s member=%s",
                member.guild.id,
                member.id,
            )

        background = cfg.get(f"{kind}_background_data") or cfg.get(f"{kind}_background")
        message_template = (
            cfg.get(f"{kind}_message") or DEFAULT_MESSAGES[kind]
        )
        count = member.guild.member_count or 0

        # One render is reused for public + DM so the two surfaces are identical.
        buf = await self.bot.greetings.render(
            member,
            kind,
            background,
            message_template,
            count,
            inviter_id=invite_id,
            invite_uses=invite_uses,
        )
        rendered = buf.getvalue()
        filename = (
            f"{kind}.{self.bot.greetings.output_extension(BytesIO(rendered))}"
        )

        risk = (
            self.bot.welcome_engine.risk(member, settings)
            if kind == "welcome"
            else None
        )
        embed = self._build_embed(
            cfg,
            settings,
            member,
            kind,
            count,
            invite_id,
            invite_uses,
            filename,
            risk=risk,
        )
        view = self._button_view(settings) if kind == "welcome" else None

        if public_enabled and channel is not None:
            if embed is not None:
                require_embed = True
            else:
                require_embed = False
            me = member.guild.me
            if me:
                permissions = channel.permissions_for(me)
                missing = [
                    name for name, ok in (
                        ("Send Messages", permissions.send_messages),
                        ("Attach Files", permissions.attach_files),
                        ("Embed Links", permissions.embed_links if require_embed else True),
                    ) if not ok
                ]
                if missing:
                    raise ValueError(
                        f"Missing permissions in {channel.mention}: {', '.join(missing)}"
                    )
            await self._send_public(
                channel,
                embed=embed,
                rendered=rendered,
                filename=filename,
                view=view,
                settings=settings,
            )

        # Auto-role belongs to the welcome transaction and is attempted after
        # successful public delivery so a broken role never blocks the greeting.
        if kind == "welcome":
            await self.bot.welcome_engine.apply_roles(member, settings)
            await self.bot.welcome_engine.alert(member, settings, risk, kind)

        if dm_enabled:
            dm_template = (
                cfg.get("welcome_dm_message") or DEFAULT_MESSAGES["welcome"]
            )
            dm_text = self._format(
                dm_template, member, count, invite_id, invite_uses
            )[:1900]
            dm_embed = discord.Embed(
                title=self._format(
                    cfg.get("welcome_embed_title") or "Welcome!",
                    member,
                    count,
                    invite_id,
                    invite_uses,
                )[:256],
                description=dm_text,
                color=self._color(cfg, "welcome"),
                timestamp=discord.utils.utcnow(),
            )
            if getattr(member.guild, "icon", None):
                dm_embed.set_author(
                    name=member.guild.name,
                    icon_url=member.guild.icon.url,
                )
            if risk and settings.get("show_risk", True):
                dm_embed.add_field(
                    name="Account check",
                    value=(
                        f"⚠️ New account ({risk['age_days']}d)"
                        if risk["is_new"]
                        else "✅ Normal account age"
                    ),
                    inline=False,
                )

            try:
                await self._send_dm(
                    member,
                    embed=dm_embed,
                    rendered=rendered,
                    filename=filename,
                    view=view,
                    settings=settings,
                )
            except (discord.Forbidden, discord.HTTPException):
                # DMs are optional and must never break the public welcome.
                self.bot.log.info(
                    "welcome DM unavailable guild=%s member=%s",
                    member.guild.id,
                    member.id,
                )

        return True

    async def _run(self):
        while True:
            enqueued, member, kind, force, invite_id, invite_uses = await self.queue.get()
            try:
                age = time.monotonic() - enqueued
                if age > self.max_event_age:
                    self.bot.log.warning(
                        "dropping stale greeting age=%.2fs guild=%s kind=%s",
                        age,
                        member.guild.id,
                        kind,
                    )
                    continue
                await self.deliver(
                    member,
                    kind,
                    force_channel=force,
                    invite_id=invite_id,
                    invite_uses=invite_uses,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.bot.log.exception(
                    "greeting worker failed guild=%s kind=%s member=%s",
                    getattr(getattr(member, "guild", None), "id", None),
                    kind,
                    getattr(member, "id", None),
                )
            finally:
                self.queue.task_done()
                WORK_QUEUE.labels("greetings").set(self.queue.qsize())

    async def close(self):
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
