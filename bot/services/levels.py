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
        "stack_awards": True,
        "message_xp_mode": "per_character",
        "xp_per_character": 1,
        "max_character_xp": 75,
        "xp_channels": [],
    }

    def __init__(self, db):
        self.db = db

    XP_THRESHOLDS = (0, 100, 255, 475, 770, 1150, 1625, 2205, 2900, 3720, 4675, 5775, 7030, 8450, 10045, 11825, 13800, 15980, 18375, 20995, 23850, 26950, 30305, 33925, 37820, 42000, 46475, 51255, 56350, 61770, 67525, 73625, 80080, 86900, 94095, 101675, 109650, 118030, 126825, 136045, 145700, 155800, 166355, 177375, 188870, 200850, 213325, 226305, 239800, 253820, 268375, 283475, 299130, 315350, 332145, 349525, 367500, 386080, 405275, 425095, 445550, 466650, 488405, 510825, 533920, 557700, 582175, 607355, 633250, 659870, 687225, 715325, 744180, 773800, 804195, 835375, 867350, 900130, 933725, 968145, 1003400, 1039500, 1076455, 1114275, 1152970, 1192550, 1233025, 1274405, 1316700, 1359920, 1404075, 1449175, 1495230, 1542250, 1590245, 1639225, 1689200, 1740180, 1792175, 1845195, 1899250)
    MAX_LEVEL = 100
    MAX_MESSAGE_XP = 75

    @classmethod
    def xp_needed(cls, level: int) -> int:
        """Return cumulative XP required to reach a level, matching the reference system."""
        level = max(0, min(cls.MAX_LEVEL, int(level)))
        return int(cls.XP_THRESHOLDS[level])

    @classmethod
    def xp_for_next_level(cls, level: int) -> int:
        level = max(0, min(cls.MAX_LEVEL, int(level)))
        if level >= cls.MAX_LEVEL:
            return cls.XP_THRESHOLDS[-1]
        return cls.XP_THRESHOLDS[level + 1]

    @classmethod
    def level_from_total_xp(cls, total_xp: int) -> int:
        """Return the highest level whose cumulative threshold is <= total XP."""
        total_xp = max(0, int(total_xp))
        lo, hi = 0, cls.MAX_LEVEL
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if cls.XP_THRESHOLDS[mid] <= total_xp:
                lo = mid
            else:
                hi = mid - 1
        return lo

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
                "xp_min": max(1, min(1000, min(int(row.xp_min), int(row.xp_max)))),
                "xp_max": max(1, min(1000, int(row.xp_max))),
                "cooldown_seconds": max(1, min(86400, int(row.cooldown_seconds))),
                "announce": bool(row.announce),
                "announcement_channel_id": row.announcement_channel_id,
                "no_xp_roles": [int(x) for x in (row.no_xp_roles or [])],
                "no_xp_channels": [int(x) for x in (row.no_xp_channels or [])],
                "bonus_roles": {str(k): max(1, min(10, int(v))) for k, v in (row.bonus_roles or {}).items()},
                "stack_awards": bool(row.stack_awards),
                "message_xp_mode": row.message_xp_mode if row.message_xp_mode in {"random", "per_character"} else "per_character",
                "xp_per_character": max(1, min(100, int(row.xp_per_character))),
                "max_character_xp": max(1, min(10000, int(row.max_character_xp))),
                "xp_channels": [int(x) for x in (row.xp_channels or [])],
            }

    async def update_settings(self, gid: int, **values) -> dict:
        allowed = set(self.DEFAULTS)
        clean = {k: v for k, v in values.items() if k in allowed}
        if "xp_min" in clean:
            clean["xp_min"] = max(1, min(1000, int(clean["xp_min"])))
        if "xp_max" in clean:
            clean["xp_max"] = max(clean.get("xp_min", 1), min(1000, int(clean["xp_max"])))
        elif "xp_min" in clean:
            current = await self.settings(gid)
            clean["xp_min"] = min(clean["xp_min"], current["xp_max"])
        if "cooldown_seconds" in clean:
            clean["cooldown_seconds"] = max(1, min(86400, int(clean["cooldown_seconds"])))
        if "no_xp_roles" in clean:
            clean["no_xp_roles"] = [int(x) for x in clean["no_xp_roles"]][:100]
        if "no_xp_channels" in clean:
            clean["no_xp_channels"] = [int(x) for x in clean["no_xp_channels"]][:100]
        if "bonus_roles" in clean:
            clean["bonus_roles"] = {str(k): max(1, min(10, int(v))) for k, v in clean["bonus_roles"].items()}
        if "stack_awards" in clean:
            clean["stack_awards"] = bool(clean["stack_awards"])
        if "message_xp_mode" in clean:
            clean["message_xp_mode"] = clean["message_xp_mode"] if clean["message_xp_mode"] in {"random", "per_character"} else "per_character"
        if "xp_per_character" in clean:
            clean["xp_per_character"] = max(1, min(100, int(clean["xp_per_character"])))
        if "max_character_xp" in clean:
            clean["max_character_xp"] = max(1, min(10000, int(clean["max_character_xp"])))
        if "xp_channels" in clean:
            clean["xp_channels"] = [int(x) for x in clean["xp_channels"]][:100]
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
        if cfg["xp_channels"] and channel_id not in set(cfg["xp_channels"]):
            return False, cfg
        if role_ids.intersection(cfg["no_xp_roles"]):
            return False, cfg
        return True, cfg

    @staticmethod
    def character_count(content: str) -> int:
        return sum(1 for ch in content if ch.isalpha())

    async def calculate_message_xp(self, gid: int, content: str) -> int:
        cfg = await self.settings(gid)
        if cfg["message_xp_mode"] == "per_character":
            letters = self.character_count(content)
            return min(cfg["max_character_xp"], letters * cfg["xp_per_character"])
        return random.randint(cfg["xp_min"], cfg["xp_max"])

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
            old_level = int(row.level)
            row.total_xp = max(0, int(row.total_xp)) + amount
            row.level = self.level_from_total_xp(row.total_xp)
            # xp is progress since the cumulative threshold for the current level.
            row.xp = max(0, int(row.total_xp) - self.xp_needed(row.level))
            await s.commit()
            return row.level, row.level > old_level, row.xp, row.total_xp

    async def modify_xp(self, gid: int, uid: int, delta: int, *, set_value: bool = False):
        delta = int(delta)
        async with self.db.session() as s:
            seed = pg_insert(Level).values(guild_id=gid, user_id=uid, xp=0, total_xp=0, level=0).on_conflict_do_nothing(index_elements=["guild_id", "user_id"])
            await s.execute(seed)
            row = (await s.execute(select(Level).where(Level.guild_id == gid, Level.user_id == uid).with_for_update())).scalar_one()
            old_level = int(row.level)
            target_total = max(0, delta) if set_value else max(0, int(row.total_xp) + delta)
            row.total_xp = target_total
            row.level = self.level_from_total_xp(target_total)
            row.xp = max(0, target_total - self.xp_needed(row.level))
            await s.commit()
            return old_level, row.level, row.xp, row.total_xp

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
            # Match the reference system's ordered leaderboard semantics while
            # making ties deterministic: higher XP ranks first, then lower user ID.
            ahead = await s.scalar(
                select(func.count(Level.id)).where(
                    Level.guild_id == gid,
                    (Level.total_xp > row.total_xp)
                    | ((Level.total_xp == row.total_xp) & (Level.user_id < uid)),
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
