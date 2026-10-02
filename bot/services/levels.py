from __future__ import annotations
import random
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from bot.models import Level, LevelRole

class LevelService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def xp_needed(level: int) -> int:
        return max(100, (level + 1) * 100)

    async def add_xp(self, gid: int, uid: int, amount: int | None = None):
        amount = amount or random.randint(8, 15)
        async with self.db.session() as s:
            seed = pg_insert(Level).values(guild_id=gid, user_id=uid, xp=0, level=0).on_conflict_do_nothing(
                index_elements=['guild_id', 'user_id']
            )
            await s.execute(seed)
            row = (await s.execute(
                select(Level).where(Level.guild_id == gid, Level.user_id == uid).with_for_update()
            )).scalar_one()
            old_level = row.level
            row.xp += amount
            while row.xp >= self.xp_needed(row.level):
                row.xp -= self.xp_needed(row.level)
                row.level += 1
            await s.commit()
            return row.level, row.level > old_level, row.xp

    async def get(self, gid: int, uid: int):
        async with self.db.session() as s:
            return (await s.execute(select(Level).where(Level.guild_id == gid, Level.user_id == uid))).scalar_one_or_none()

    async def set_role(self, gid: int, level: int, role_id: int):
        async with self.db.session() as s:
            row = (await s.execute(select(LevelRole).where(LevelRole.guild_id == gid, LevelRole.level == level))).scalar_one_or_none()
            if row:
                row.role_id = role_id
            else:
                s.add(LevelRole(guild_id=gid, level=level, role_id=role_id))
            await s.commit()

    async def remove_role(self, gid: int, level: int):
        async with self.db.session() as s:
            await s.execute(delete(LevelRole).where(LevelRole.guild_id == gid, LevelRole.level == level))
            await s.commit()

    async def role_for_level(self, gid: int, level: int):
        async with self.db.session() as s:
            result = await s.execute(select(LevelRole).where(LevelRole.guild_id == gid, LevelRole.level <= level).order_by(LevelRole.level.desc()))
            return result.scalars().first()

    async def configured_roles(self, gid: int):
        async with self.db.session() as s:
            result = await s.execute(select(LevelRole).where(LevelRole.guild_id == gid).order_by(LevelRole.level))
            return list(result.scalars())
