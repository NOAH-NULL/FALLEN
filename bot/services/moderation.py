from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select, func
from bot.models import Warning

class ModerationService:
    def __init__(self,db): self.db=db
    async def warn(self,guild_id,user_id,moderator_id,reason,points=1,expires_at=None):
        async with self.db.session() as s:
            s.add(Warning(guild_id=guild_id,user_id=user_id,moderator_id=moderator_id,reason=reason,points=max(1,int(points)),expires_at=expires_at)); await s.commit()
    async def warnings(self,guild_id,user_id,include_expired=False):
        async with self.db.session() as s:
            q=select(Warning).where(Warning.guild_id==guild_id,Warning.user_id==user_id)
            if not include_expired: q=q.where((Warning.expires_at.is_(None)) | (Warning.expires_at>datetime.now(timezone.utc)))
            return list((await s.execute(q.order_by(Warning.id.desc()).limit(50))).scalars())
    async def count(self,guild_id,user_id):
        async with self.db.session() as s:
            q=select(func.coalesce(func.sum(Warning.points),0)).where(Warning.guild_id==guild_id,Warning.user_id==user_id,(Warning.expires_at.is_(None)) | (Warning.expires_at>datetime.now(timezone.utc)))
            return int((await s.execute(q)).scalar_one())
