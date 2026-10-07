from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import discord


DEFAULT_SETTINGS = {
    "enabled": True,
    "include_bots": False,
    "public_enabled": True,
    "dm_enabled": False,
    "log_enabled": False,
    "log_channel_id": None,
    "show_details": True,
    "show_joined_at": True,
    "show_account_created": True,
    "show_inviter": True,
    "show_invites": True,
    "show_risk": True,
    "new_account_days": 7,
    "alert_new_accounts": True,
    "auto_role_ids": [],
    "retry_attempts": 2,
    "retry_backoff": 0.75,
    "dedupe_seconds": 90,
    "dm_retry": 1,
    "buttons": [],
    "preset": "full",
}


class WelcomeEngine:
    """High-reliability welcome orchestration.

    The DB column stores only server-level policy; the engine owns validation,
    normalization, risk classification, role application, link-button layout,
    and duplicate-event protection.
    """

    def __init__(self, bot):
        self.bot = bot
        self._seen: dict[tuple[int, int, str], float] = {}

    @staticmethod
    def defaults() -> dict:
        return dict(DEFAULT_SETTINGS)

    @classmethod
    def normalize(cls, raw: dict | None, legacy: dict | None = None) -> dict:
        out = cls.defaults()
        if isinstance(raw, dict):
            out.update(raw)
        legacy = legacy or {}

        # Preserve the older controls while making the advanced settings the
        # single source of truth for new behavior.
        if not raw:
            out["dm_enabled"] = bool(legacy.get("welcome_dm_enabled", False))
            out["show_details"] = bool(legacy.get("welcome_show_details", True))
            if legacy.get("welcome_button_enabled") and legacy.get("welcome_button_url"):
                out["buttons"] = [{
                    "enabled": True,
                    "label": (legacy.get("welcome_button_label") or "Read the Rules")[:80],
                    "url": str(legacy.get("welcome_button_url")).strip(),
                }]

        out["new_account_days"] = max(0, min(3650, int(out.get("new_account_days", 7) or 7)))
        out["retry_attempts"] = max(0, min(4, int(out.get("retry_attempts", 2) or 0)))
        out["dm_retry"] = max(0, min(2, int(out.get("dm_retry", 1) or 0)))
        out["dedupe_seconds"] = max(0, min(600, float(out.get("dedupe_seconds", 90) or 0)))
        out["retry_backoff"] = max(0.1, min(5.0, float(out.get("retry_backoff", 0.75) or 0.75)))

        role_ids = []
        for value in out.get("auto_role_ids") or []:
            try:
                value = int(value)
            except (TypeError, ValueError):
                continue
            if value > 0 and value not in role_ids:
                role_ids.append(value)
        legacy_role = legacy.get("autorole_id")
        if legacy_role:
            try:
                legacy_role = int(legacy_role)
                if legacy_role not in role_ids:
                    role_ids.insert(0, legacy_role)
            except (TypeError, ValueError):
                pass
        out["auto_role_ids"] = role_ids[:10]

        buttons = []
        for item in out.get("buttons") or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url.startswith("https://"):
                continue
            label = str(item.get("label") or "Open").strip()[:80] or "Open"
            buttons.append({
                "enabled": bool(item.get("enabled", True)),
                "label": label,
                "url": url[:2000],
            })
        out["buttons"] = buttons[:5]
        out["preset"] = str(out.get("preset") or "full")[:24]
        return out

    async def get(self, guild_id: int, cfg: dict | None = None) -> dict:
        cfg = cfg if cfg is not None else await self.bot.guild_config.get(guild_id)
        return self.normalize(cfg.get("welcome_settings"), cfg)

    async def save(self, guild_id: int, **changes) -> dict:
        current = await self.get(guild_id)
        current.update(changes)
        current["preset"] = "custom"
        current = self.normalize(current)
        await self.bot.guild_config.update(guild_id, welcome_settings=current)
        return current

    def should_deliver(self, member, kind: str, settings: dict) -> bool:
        if not settings.get("enabled", True):
            return False
        if kind == "welcome":
            if getattr(member, "bot", False) and not settings.get("include_bots", False):
                return False
            return bool(settings.get("public_enabled") or settings.get("dm_enabled"))
        return True

    def claim(self, member, kind: str, seconds: float) -> bool:
        seconds = max(0.0, float(seconds))
        if seconds <= 0:
            return True
        now = time.monotonic()
        key = (member.guild.id, member.id, kind)
        last = self._seen.get(key)
        if last is not None and now - last < seconds:
            return False
        self._seen[key] = now
        # Cheap bounded cleanup.
        if len(self._seen) > 4096:
            cutoff = now - max(seconds, 60.0)
            self._seen = {k: v for k, v in self._seen.items() if v >= cutoff}
        return True

    @staticmethod
    def account_age_days(member) -> int | None:
        created = getattr(member, "created_at", None)
        if not created:
            return None
        try:
            return max(0, (datetime.now(timezone.utc) - created).days)
        except (TypeError, ValueError):
            return None

    def risk(self, member, settings: dict) -> dict:
        age_days = self.account_age_days(member)
        threshold = int(settings.get("new_account_days", 7) or 0)
        is_new = age_days is not None and threshold > 0 and age_days < threshold
        score = 0
        if is_new and threshold:
            score = max(1, min(100, int(100 * (threshold - age_days) / threshold)))
        return {
            "age_days": age_days,
            "threshold_days": threshold,
            "is_new": is_new,
            "score": score,
            "label": "NEW ACCOUNT" if is_new else "NORMAL",
        }

    @staticmethod
    def button_view(settings: dict):
        buttons = [b for b in settings.get("buttons", []) if b.get("enabled")]
        if not buttons:
            return None
        view = discord.ui.View(timeout=None)
        for item in buttons[:5]:
            view.add_item(
                discord.ui.Button(
                    label=item["label"],
                    style=discord.ButtonStyle.link,
                    url=item["url"],
                )
            )
        return view

    async def apply_roles(self, member, settings: dict) -> int:
        guild = member.guild
        me = guild.me
        if not me:
            return 0
        roles = []
        for role_id in settings.get("auto_role_ids", []):
            role = guild.get_role(int(role_id))
            if role and role < me.top_role and role not in member.roles:
                roles.append(role)
        if not roles:
            return 0
        try:
            await member.add_roles(*roles, reason="Fallen advanced welcome auto-role")
            return len(roles)
        except discord.HTTPException:
            self.bot.log.warning("advanced welcome auto-role failed guild=%s member=%s", guild.id, member.id, exc_info=True)
            return 0

    async def retry(self, operation, attempts: int, backoff: float):
        last = None
        for attempt in range(max(1, attempts + 1)):
            try:
                return await operation()
            except discord.Forbidden:
                raise
            except discord.HTTPException as exc:
                last = exc
                if attempt >= attempts:
                    raise
                await asyncio.sleep(backoff * (2 ** attempt))
        if last:
            raise last

    async def alert(self, member, settings: dict, risk: dict, kind: str):
        if kind != "welcome" or not settings.get("log_enabled") or not settings.get("alert_new_accounts"):
            return False
        if not risk["is_new"]:
            return False
        channel_id = settings.get("log_channel_id")
        channel = member.guild.get_channel(int(channel_id)) if channel_id else None
        if channel is None:
            return False
        age = f"{risk['age_days']} day(s)" if risk["age_days"] is not None else "unknown"
        embed = discord.Embed(
            title="⚠️ New account joined",
            description=f"{member.mention} joined **{member.guild.name}** with a very new account.",
            color=discord.Colour.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Account age", value=age, inline=True)
        embed.add_field(name="Risk score", value=f"{risk['score']}/100", inline=True)
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=False)
        try:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
            return True
        except (discord.Forbidden, discord.HTTPException):
            self.bot.log.warning("welcome security alert failed guild=%s member=%s", member.guild.id, member.id)
            return False
