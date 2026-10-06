from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from .schema import Base

class ModCase(Base):
    __tablename__='mod_cases'
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    target_id: Mapped[int]=mapped_column(BigInteger,index=True)
    moderator_id: Mapped[int]=mapped_column(BigInteger,index=True)
    action: Mapped[str]=mapped_column(String(32),index=True)
    reason: Mapped[str]=mapped_column(Text,default='No reason provided')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class Reminder(Base):
    __tablename__='reminders'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    channel_id: Mapped[int]=mapped_column(BigInteger)
    message: Mapped[str]=mapped_column(Text)
    due_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    delivered: Mapped[bool]=mapped_column(Boolean,default=False,index=True)
    processing: Mapped[bool]=mapped_column(Boolean,default=False,index=True)
    claimed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True,index=True)

class Giveaway(Base):
    __tablename__='giveaways'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    channel_id: Mapped[int]=mapped_column(BigInteger)
    message_id: Mapped[int]=mapped_column(BigInteger,unique=True)
    prize: Mapped[str]=mapped_column(String(200))
    winner_count: Mapped[int]=mapped_column(Integer,default=1)
    ends_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    ended: Mapped[bool]=mapped_column(Boolean,default=False,index=True)

class Suggestion(Base):
    __tablename__='suggestions'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    channel_id: Mapped[int]=mapped_column(BigInteger)
    message_id: Mapped[int]=mapped_column(BigInteger,unique=True)
    content: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),default='pending',index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class RoleMenu(Base):
    __tablename__='role_menus'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    message_id: Mapped[int]=mapped_column(BigInteger,index=True)
    emoji: Mapped[str]=mapped_column(String(64))
    role_id: Mapped[int]=mapped_column(BigInteger)
    __table_args__=(UniqueConstraint('guild_id','message_id','emoji'),)

class Economy(Base):
    __tablename__='economy'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    balance: Mapped[int]=mapped_column(Integer,default=0)
    daily_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    __table_args__=(UniqueConstraint('guild_id','user_id'),)

class InviteStat(Base):
    __tablename__='invite_stats'
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    user_id: Mapped[int]=mapped_column(BigInteger,index=True)
    joins: Mapped[int]=mapped_column(Integer,default=0)
    leaves: Mapped[int]=mapped_column(Integer,default=0)
    __table_args__=(UniqueConstraint('guild_id','user_id'),)

class MemberInviteAttribution(Base):
    __tablename__='member_invite_attribution'
    id: Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int]=mapped_column(BigInteger,index=True)
    member_id: Mapped[int]=mapped_column(BigInteger,index=True)
    inviter_id: Mapped[int]=mapped_column(BigInteger,index=True)
    invite_code: Mapped[str|None]=mapped_column(String(128),nullable=True)
    joined_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    left_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    __table_args__=(UniqueConstraint('guild_id','member_id'),)
