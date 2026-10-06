from sqlalchemy import BigInteger, Boolean, DateTime, Integer, LargeBinary, String, Text, UniqueConstraint, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
class Base(DeclarativeBase): pass
class GuildConfig(Base):
    __tablename__='guild_configs'
    guild_id:Mapped[int]=mapped_column(BigInteger,primary_key=True)
    welcome_channel_id:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    goodbye_channel_id:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    log_channel_id:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    autorole_id:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    welcome_message:Mapped[str]=mapped_column(Text,default='Welcome {mention} to {server}! You are member #{count}.')
    goodbye_message:Mapped[str]=mapped_column(Text,default='Goodbye {name}!')
    welcome_background:Mapped[str]=mapped_column(Text,default='assets/welcome.gif')
    goodbye_background:Mapped[str]=mapped_column(Text,default='assets/goodbye.gif')
    welcome_background_data:Mapped[bytes|None]=mapped_column(LargeBinary,nullable=True)
    goodbye_background_data:Mapped[bytes|None]=mapped_column(LargeBinary,nullable=True)
    automod_enabled:Mapped[bool]=mapped_column(Boolean,default=False)
    spam_limit:Mapped[int]=mapped_column(Integer,default=6)
    spam_window:Mapped[int]=mapped_column(Integer,default=8)
    welcome_embed_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    goodbye_embed_enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    welcome_embed_title:Mapped[str]=mapped_column(Text,default='Welcome!')
    goodbye_embed_title:Mapped[str]=mapped_column(Text,default='Goodbye!')
    welcome_embed_description:Mapped[str]=mapped_column(Text,default='{mention} just joined {server}! 🎉')
    goodbye_embed_description:Mapped[str]=mapped_column(Text,default='{name} has left {server}. 👋')
    welcome_embed_color:Mapped[int]=mapped_column(BigInteger,default=5793266)
    goodbye_embed_color:Mapped[int]=mapped_column(BigInteger,default=9807270)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
    extreme_settings:Mapped[dict]=mapped_column(JSON,default=dict,nullable=False)
class Warning(Base):
    __tablename__='warnings'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id:Mapped[int]=mapped_column(BigInteger,index=True)
    user_id:Mapped[int]=mapped_column(BigInteger,index=True)
    moderator_id:Mapped[int]=mapped_column(BigInteger)
    reason:Mapped[str]=mapped_column(Text)
    points:Mapped[int]=mapped_column(Integer,default=1)
    expires_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class CustomCommand(Base):
    __tablename__='custom_commands'; __table_args__=(UniqueConstraint('guild_id','name'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id:Mapped[int]=mapped_column(BigInteger,index=True)
    name:Mapped[str]=mapped_column(String(64))
    response:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class Level(Base):
    __tablename__='levels'; __table_args__=(UniqueConstraint('guild_id','user_id'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id:Mapped[int]=mapped_column(BigInteger,index=True)
    user_id:Mapped[int]=mapped_column(BigInteger,index=True)
    xp:Mapped[int]=mapped_column(Integer,default=0)
    total_xp:Mapped[int]=mapped_column(BigInteger,default=0)
    level:Mapped[int]=mapped_column(Integer,default=0)
class ReactionRole(Base):
    __tablename__='reaction_roles'; __table_args__=(UniqueConstraint('guild_id','message_id','emoji'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id:Mapped[int]=mapped_column(BigInteger,index=True)
    message_id:Mapped[int]=mapped_column(BigInteger,index=True)
    emoji:Mapped[str]=mapped_column(String(64))
    role_id:Mapped[int]=mapped_column(BigInteger)

class LevelRole(Base):
    __tablename__='level_roles'; __table_args__=(UniqueConstraint('guild_id','level'), UniqueConstraint('guild_id','role_id'))
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id:Mapped[int]=mapped_column(BigInteger,index=True)
    level:Mapped[int]=mapped_column(Integer,index=True)
    role_id:Mapped[int]=mapped_column(BigInteger,index=True)


class LevelSettings(Base):
    __tablename__='level_settings'
    guild_id:Mapped[int]=mapped_column(BigInteger,primary_key=True)
    enabled:Mapped[bool]=mapped_column(Boolean,default=True)
    xp_min:Mapped[int]=mapped_column(Integer,default=8)
    xp_max:Mapped[int]=mapped_column(Integer,default=15)
    cooldown_seconds:Mapped[int]=mapped_column(Integer,default=45)
    announce:Mapped[bool]=mapped_column(Boolean,default=True)
    announcement_channel_id:Mapped[int|None]=mapped_column(BigInteger,nullable=True)
    no_xp_roles:Mapped[list]=mapped_column(JSON,default=list,nullable=False)
    no_xp_channels:Mapped[list]=mapped_column(JSON,default=list,nullable=False)
    bonus_roles:Mapped[dict]=mapped_column(JSON,default=dict,nullable=False)
    stack_awards:Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)
    message_xp_mode:Mapped[str]=mapped_column(String(24),default='per_character',nullable=False)
    xp_per_character:Mapped[float]=mapped_column(Integer,default=1,nullable=False)
    max_character_xp:Mapped[int]=mapped_column(Integer,default=75,nullable=False)
    xp_channels:Mapped[list]=mapped_column(JSON,default=list,nullable=False)
