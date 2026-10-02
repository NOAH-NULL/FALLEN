from sqlalchemy import select,delete
from bot.models import CustomCommand
class CustomCommandService:
    def __init__(self,db,cache):self.db,self.cache=db,cache
    async def set(self,gid,name,response):
        async with self.db.session() as s:
            row=(await s.execute(select(CustomCommand).where(CustomCommand.guild_id==gid,CustomCommand.name==name))).scalar_one_or_none()
            if row:row.response=response
            else:s.add(CustomCommand(guild_id=gid,name=name,response=response))
            await s.commit()
    async def get(self,gid,name):
        async with self.db.session() as s:return (await s.execute(select(CustomCommand.response).where(CustomCommand.guild_id==gid,CustomCommand.name==name))).scalar_one_or_none()
    async def remove(self,gid,name):
        async with self.db.session() as s:await s.execute(delete(CustomCommand).where(CustomCommand.guild_id==gid,CustomCommand.name==name));await s.commit()
