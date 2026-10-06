from __future__ import annotations

import random
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from bot.models import Level, LevelRole, LevelSettings


class LevelService:
    DEFAULTS = {
        "enabled": True,
        "xp_min": 8,
        "xp_max": 15,
        "cooldown_seconds": 45,
        "announce": True,
        "announcement_channel_id": None,
        "no_xp_roles": [],
        "no_xp_channels": [],
        "bonus_roles": {},
    }

    def __init__(self, db):
        self.db = db

    @staticmethod
    def xp_needed(level: int) -> int:
        level = max(0, int(level))
        # Progressive curve: each level takes more XP than the previous one.
        return max(100, (level + 1) * 100)

    @classmethod
    def level_from_total_xp(cls, total_xp: int) -> int:
        total_xp = max(0, int(total_xp))
        level = 0
        remaining = total_xp
        while remaining >= cls.xp_needed(level):
            remaining -= cls.xp_needed(level)
            level += 1
        return level

    async def _ensure_settings(self, gid: int):
        async with self.db.session() as s:
            stmt = pg_insert(LevelSettings).values(guild_id=gid, **self.DEFAULTS).on_conflict_do_nothing(
                index_elements=["guild_id"]
            )
            await s.execute(stmt)
            await s.commit()

    async def settings(self, gid: int) -> dict:
        await self._ensure_settings(gid)
        async with self.db.session() as s:
            row = (await s.execute(
                select(LevelSettings).where(LevelSettings.guild_id == gid)
            )).scalar_one()
            return {
                "enabled": bool(row.enabled),
                "xp_min": max(1, min(1000, int(row.xp_min))),
                "xp_max": max(1, min(1000, int(row.xp_max))),
                "cooldown_seconds": max(1, min(86400, int(row.cooldown_seconds))),
                "announce": bool(row.announce),
                "announcement_channel_id": row.announcement_channel_id,
                "no_xp_roles": [int(x) for x in (row.no_xp_roles or [])],
                "no_xp_channels": [int(x) for x in (row.no_xp_channels or [])],
                "bonus_roles": {str(k): max(1, min(10, int(v))) for k, v in (row.bonus_roles or {}).items()},
            }

    async def update_settings(self, gid: int, **values) -> dict:
        allowed = set(self.DEFAULTS)
        clean = {k: v for k, v in values.items() if k in allowed}
        if "xp_min" in clean:
            clean["xp_min"] = max(1, min(1000, int(clean["xp_min"])))
        if "xp_max" in clean:
            clean["xp_max"] = max(clean.get("xp_min", 1), min(1000, int(clean["xp_max"])))
        if "cooldown_seconds" in clean:
            clean["cooldown_seconds"] = max(1, min(86400, int(clean["cooldown_seconds"])))
        if "no_xp_roles" in clean:
            clean["no_xp_roles"] = [int(x) for x in clean["no_xp_roles"]][:100]
        if "no_xp_channels" in clean:
            clean["no_xp_channels"] = [int(x) for x in clean["no_xp_channels"]][:100]
        if "bonus_roles" in clean:
            clean["bonus_roles"] = {str(k): max(1, min(10, int(v))) for k, v in clean["bonus_roles"].items()} 
        async with self.db.session() as s:
            await s.execute(
                pg_insert(LevelSettings)
                .values(guild_id=gid, **self.DEFAULTS, **clean)
                .on_conflict_do_update(
                    index_elements=["guild_id"],
                    set_=clean,
                )
            )
            await s.commit()
        return await self.settings(gid)

    async def eligible(self, guild_id: int, channel_id: int, role_ids: set[int]) -> tuple[bool, dict]:
        cfg = await self.settings(guild_id)
        if not cfg["enabled"] or channel_id in set(cfg["no_xp_channels"]):
            return False, cfg
        if role_ids.intersection(cfg["no_xp_roles"]):
            return False, cfg
        return True, cfg

    async def add_xp(self, gid: int, uid: int, amount: int | None = None):
        cfg = await self.settings(gid)
        if amount is None:
            amount = random.randint(cfg["xp_min"], cfg["xp_max"])
        amount = max(0, min(10000, int(amount)))
        async with self.db.session() as s:
            seed = pg_insert(Level).values(
                guild_id=gid, user_id=uid, xp=0, total_xp=0, level=0
            ).on_conflict_do_nothing(index_elements=["guild_id", "user_id"])
            await s.execute(seed)
            row = (await s.execute(
                select(Level).where(Level.guild_id == gid, Level.user_id == uid).with_for_update()
            )).scalar_one()
            old_level = row.level
            row.xp += amount
            row.total_xp += amount
            while row.xp >= self.xp_needed(row.level):
                row.xp -= self.xp_needed(row.level)
                row.level += 1
            await s.commit()
            return row.level, row.level > old_level, row.xp, row.total_xp

    async def get(self, gid: int, uid: int):
        async with self.db.session() as s:
            return (await s.execute(
                select(Level).where(Level.guild_id == gid, Level.user_id == uid)
            )).scalar_one_or_none()

    async def rank(self, gid: int, uid: int) -> int | None:
        row = await self.get(gid, uid)
        if not row:
            return None
        async with self.db.session() as s:
            ahead = await s.scalar(
                select(func.count(Level.id)).where(
                    Level.guild_id == gid,
                    Level.total_xp > row.total_xp,
                )
            )
            return int(ahead or 0) + 1

    async def leaderboard(self, gid: int, limit: int = 10):
        limit = max(1, min(100, int(limit)))
        async with self.db.session() as s:
            result = await s.execute(
                select(Level)
                .where(Level.guild_id == gid)
                .order_by(Level.total_xp.desc(), Level.user_id.asc())
                .limit(limit)
            )
            return list(result.scalars())

    async def set_role(self, gid: int, level: int, role_id: int):
        async with self.db.session() as s:
            row = (await s.execute(
                select(LevelRole).where(LevelRole.guild_id == gid, LevelRole.level == level)
            )).scalar_one_or_none()
            if row:
                row.role_id = role_id
            else:
                s.add(LevelRole(guild_id=gid, level=level, role_id=role_id))
            await s.commit()

    async def remove_role(self, gid: int, level: int):
        async with self.db.session() as s:
            await s.execute(delete(LevelRole).where(
                LevelRole.guild_id == gid, LevelRole.level == level
            ))
            await s.commit()

    async def role_for_level(self, gid: int, level: int):
        async with self.db.session() as s:
            result = await s.execute(
                select(LevelRole)
                .where(LevelRole.guild_id == gid, LevelRole.level <= level)
                .order_by(LevelRole.level.desc())
            )
            return result.scalars().first()

    async def configured_roles(self, gid: int):
        async with self.db.session() as s:
            result = await s.execute(
                select(LevelRole)
                .where(LevelRole.guild_id == gid)
                .order_by(LevelRole.level)
            )
            return list(result.scalars())
