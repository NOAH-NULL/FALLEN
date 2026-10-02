from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from .schema import Base

class FeatureRecord(Base):
    __tablename__ = 'feature_records'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    subject_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    feature: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('guild_id', 'subject_id', 'feature'),)

class SecurityEvent(Base):
    __tablename__ = 'security_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    actor_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

class ScheduledAction(Base):
    __tablename__ = 'scheduled_actions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    executed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AutoModRule(Base):
    __tablename__ = 'automod_rules'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32), index=True)
    pattern: Mapped[str] = mapped_column(Text, default='')
    action: Mapped[str] = mapped_column(String(32), default='delete')
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (UniqueConstraint('guild_id', 'name'),)

class MemberProfile(Base):
    __tablename__ = 'member_profiles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    bio: Mapped[str] = mapped_column(Text, default='')
    color: Mapped[int | None] = mapped_column(Integer, nullable=True)
    badges: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    birthday: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('guild_id', 'user_id'),)

class Reputation(Base):
    __tablename__ = 'reputation'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint('guild_id', 'user_id'),)

class Playlist(Base):
    __tablename__ = 'playlists'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str] = mapped_column(String(64))
    tracks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    server_wide: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('guild_id', 'owner_id', 'name'),)

class Ticket(Base):
    __tablename__ = 'tickets_v16'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    opener_id: Mapped[int] = mapped_column(BigInteger, index=True)
    claimer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default='general')
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default='open', index=True)
    notes: Mapped[str] = mapped_column(Text, default='')
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ConfigSnapshot(Base):
    __tablename__ = 'config_snapshots'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_by: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('guild_id', 'name'),)
