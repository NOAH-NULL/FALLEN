from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import re
import time
from sqlalchemy import delete, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from bot.models import GuildConfig, FeatureRecord, SecurityEvent, ScheduledAction, AutoModRule, MemberProfile, Reputation, Playlist, Ticket, ConfigSnapshot

FEATURES = {
    "security": ["anti_bot_join","account_age_verification","suspicious_username","raid_join_rate","automatic_lockdown","lockdown_recovery","anti_channel_delete","anti_role_delete","anti_webhook_abuse","anti_permission_escalation","anti_mass_ban","security_timeline","trusted_admin_allowlist","owner_emergency_lockdown","security_backup"],
    "moderation": ["temporary_bans","temporary_timeouts","scheduled_punishments","warning_expiration","warning_points","punishment_escalation","mod_notes","case_search","case_edit","case_export","bulk_warning","message_reports","moderator_approval","anonymous_reports","mod_statistics"],
    "automod": ["regex_rules","duplicate_messages","flood_detection","emoji_spam","sticker_spam","attachment_filtering","domain_whitelist","domain_blacklist","mention_spam","custom_actions"],
    "leveling": ["voice_xp","activity_xp","xp_boosters","role_xp_multipliers","channel_xp_multipliers","xp_weekends","seasonal_levels","prestige_levels","rank_card_customization","levelup_animations"],
    "community": ["server_reputation","member_profiles","profile_badges","profile_colors","birthdays","server_anniversaries","member_milestones","welcome_challenges","community_quests","achievements"],
    "engagement": ["daily_rewards","streaks","trivia","word_games","number_games","reaction_games","mini_tournaments","voting_battles","community_challenges","random_events"],
    "music": ["dj_roles","music_permissions","saved_queues","queue_presets","personal_playlists","server_playlists","autoplay","queue_recovery","player_persistence","music_history"],
    "tickets": ["ticket_categories","ticket_forms","ticket_claiming","ticket_priority","ticket_transcripts","ticket_ratings","ticket_statistics","ticket_auto_close","staff_ticket_notes","ticket_reopening"],
    "administration": ["configuration_snapshots","configuration_import_export","setup_wizard","permission_templates","role_hierarchy_checker","channel_configuration_checker","bot_health_dashboard","module_diagnostics","configuration_validation","server_backup_restore"],
}
ALL_FEATURES = {x for values in FEATURES.values() for x in values}
DEFAULTS = {name: False for name in ALL_FEATURES}
# Non-destructive capabilities are enabled by default; destructive/security enforcement remains opt-in.
for _name in {"activity_xp","server_reputation","member_profiles","profile_badges","profile_colors","achievements","daily_rewards","streaks","trivia","word_games","number_games","reaction_games","personal_playlists","saved_queues","configuration_validation","bot_health_dashboard","module_diagnostics"}:
    DEFAULTS[_name] = True

class ExtremeService:
    """Durable implementation layer for the 100 V16 capabilities.

    Commands are adapters; this service owns validation, persistence and reusable
    operations so prefix and slash interfaces cannot drift apart.
    """
    def __init__(self, db):
        self.db = db
        self._settings_cache: dict[int, tuple[float, dict]] = {}
        self._settings_ttl = 1.0
        self._rules_cache: dict[int, tuple[float, list]] = {}
    @staticmethod
    def catalog(): return deepcopy(FEATURES)
    @classmethod
    def all_names(cls): return set(ALL_FEATURES)
    async def get(self, guild_id: int) -> dict:
        now=time.monotonic()
        cached=self._settings_cache.get(guild_id)
        if cached and now < cached[0]:
            return dict(cached[1])
        async with self.db.session() as s:
            row = await s.get(GuildConfig, guild_id)
            stored = dict(row.extreme_settings or {}) if row else {}
        out=dict(DEFAULTS)
        out.update(stored)
        self._settings_cache[guild_id]=(now+self._settings_ttl, dict(out))
        return out
    async def set(self, guild_id: int, key: str, value):
        key = key.strip().lower()
        if key not in ALL_FEATURES: raise ValueError(f"Unknown V16 feature: {key}")
        async with self.db.session() as s:
            row = await s.get(GuildConfig, guild_id, with_for_update=True)
            if not row:
                row = GuildConfig(guild_id=guild_id, extreme_settings={}); s.add(row); await s.flush()
            data = dict(row.extreme_settings or {}); data[key] = bool(value); row.extreme_settings = data; await s.commit()
        self._settings_cache.pop(guild_id, None)
        return bool(value)
    async def enabled(self, guild_id: int, key: str) -> bool:
        return bool((await self.get(guild_id)).get(key, False))
    async def snapshot(self, guild_id: int) -> dict:
        return {"guild_id": guild_id, "created_at": datetime.now(timezone.utc).isoformat(), "features": await self.get(guild_id)}
    async def validate(self, guild_id: int) -> list[str]:
        settings = await self.get(guild_id); errors=[]
        for key in settings:
            if key not in ALL_FEATURES: errors.append(f"Unknown stored feature: {key}")
        return errors
    async def record_security(self,guild_id,event_type,actor_id=None,target_id=None,details=None):
        async with self.db.session() as s:
            s.add(SecurityEvent(guild_id=guild_id,event_type=event_type,actor_id=actor_id,target_id=target_id,details=details or {})); await s.commit()
    async def security_events(self,guild_id,limit=25):
        async with self.db.session() as s:
            return list((await s.execute(select(SecurityEvent).where(SecurityEvent.guild_id==guild_id).order_by(SecurityEvent.id.desc()).limit(limit))).scalars())
    async def schedule(self,guild_id,target_id,action,run_at,payload=None):
        async with self.db.session() as s:
            row=ScheduledAction(guild_id=guild_id,target_id=target_id,action=action,run_at=run_at,payload=payload or {}); s.add(row); await s.commit(); return row.id
    async def due_actions(self,now=None,limit=100):
        """Atomically claim due actions for one scheduler instance.

        Claims are recoverable after a crash, so a second instance can take
        over stale work without allowing concurrent duplicate execution.
        """
        now=now or datetime.now(timezone.utc)
        stale=now-timedelta(minutes=10)
        async with self.db.session() as s:
            result=await s.execute(
                select(ScheduledAction)
                .where(
                    ScheduledAction.executed.is_(False),
                    ScheduledAction.run_at <= now,
                    (ScheduledAction.processing.is_(False) | (ScheduledAction.claimed_at < stale)),
                )
                .order_by(ScheduledAction.run_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            rows=list(result.scalars())
            for row in rows:
                row.processing=True
                row.claimed_at=now
            await s.commit()
            return rows

    async def complete_action(self, action_id: int):
        async with self.db.session() as s:
            result=await s.execute(
                select(ScheduledAction).where(
                    ScheduledAction.id == action_id,
                    ScheduledAction.executed.is_(False),
                ).with_for_update()
            )
            row=result.scalar_one_or_none()
            if row is None: return False
            row.executed=True
            row.processing=False
            row.claimed_at=None
            await s.commit()
            return True

    async def release_action(self, action_id: int):
        async with self.db.session() as s:
            result=await s.execute(
                select(ScheduledAction).where(
                    ScheduledAction.id == action_id,
                    ScheduledAction.executed.is_(False),
                ).with_for_update()
            )
            row=result.scalar_one_or_none()
            if row is None: return False
            row.processing=False
            row.claimed_at=None
            await s.commit()
            return True
    async def upsert_automod_rule(self,guild_id,name,kind,pattern='',action='delete',config=None,enabled=True):
        async with self.db.session() as s:
            row=(await s.execute(select(AutoModRule).where(AutoModRule.guild_id==guild_id,AutoModRule.name==name))).scalar_one_or_none()
            if not row: row=AutoModRule(guild_id=guild_id,name=name); s.add(row)
            row.kind=kind; row.pattern=pattern; row.action=action; row.config=config or {}; row.enabled=enabled; await s.commit()
            self._rules_cache.pop(guild_id, None)
            return row
    async def automod_rules(self,guild_id):
        now=time.monotonic()
        cached=self._rules_cache.get(guild_id)
        if cached and now < cached[0]:
            return list(cached[1])
        async with self.db.session() as s:
            rows=list((await s.execute(
                select(AutoModRule).where(AutoModRule.guild_id==guild_id).order_by(AutoModRule.name)
            )).scalars())
        self._rules_cache[guild_id]=(now+2.0, rows)
        return list(rows)
    async def profile(self,guild_id,user_id):
        async with self.db.session() as s: return (await s.execute(select(MemberProfile).where(MemberProfile.guild_id==guild_id,MemberProfile.user_id==user_id))).scalar_one_or_none()
    async def set_profile(self,guild_id,user_id,**changes):
        allowed={'bio','color','badges','birthday'}; changes={k:v for k,v in changes.items() if k in allowed}
        async with self.db.session() as s:
            row=(await s.execute(select(MemberProfile).where(MemberProfile.guild_id==guild_id,MemberProfile.user_id==user_id).with_for_update())).scalar_one_or_none()
            if not row: row=MemberProfile(guild_id=guild_id,user_id=user_id); s.add(row)
            for k,v in changes.items(): setattr(row,k,v)
            await s.commit(); return row
    async def reputation_change(self,guild_id,user_id,delta):
        delta=int(delta)
        async with self.db.session() as s:
            stmt=pg_insert(Reputation).values(
                guild_id=guild_id,
                user_id=user_id,
                score=max(-100000, delta),
            ).on_conflict_do_update(
                index_elements=['guild_id', 'user_id'],
                set_={'score': func.greatest(Reputation.score + delta, -100000)},
            ).returning(Reputation.score)
            result=await s.execute(stmt)
            score=result.scalar_one()
            await s.commit()
            return score
    async def reputation(self,guild_id,user_id):
        async with self.db.session() as s: return (await s.execute(select(Reputation).where(Reputation.guild_id==guild_id,Reputation.user_id==user_id))).scalar_one_or_none()
    async def playlist(self,guild_id,owner_id,name,server_wide=False):
        async with self.db.session() as s: return (await s.execute(select(Playlist).where(Playlist.guild_id==guild_id,Playlist.owner_id==owner_id,Playlist.name==name))).scalar_one_or_none()
    async def save_playlist(self,guild_id,owner_id,name,tracks,server_wide=False):
        if len(name)>64 or not name.strip(): raise ValueError('Invalid playlist name')
        async with self.db.session() as s:
            row=(await s.execute(select(Playlist).where(Playlist.guild_id==guild_id,Playlist.owner_id==owner_id,Playlist.name==name).with_for_update())).scalar_one_or_none()
            if not row: row=Playlist(guild_id=guild_id,owner_id=owner_id,name=name); s.add(row)
            row.tracks=list(tracks)[:100]; row.server_wide=server_wide; await s.commit(); return row
    async def playlists(self,guild_id,owner_id):
        async with self.db.session() as s: return list((await s.execute(select(Playlist).where(Playlist.guild_id==guild_id,Playlist.owner_id==owner_id).order_by(Playlist.name))).scalars())
    async def snapshot_save(self,guild_id,created_by,name,payload):
        async with self.db.session() as s:
            row=(await s.execute(select(ConfigSnapshot).where(ConfigSnapshot.guild_id==guild_id,ConfigSnapshot.name==name).with_for_update())).scalar_one_or_none()
            if not row: row=ConfigSnapshot(guild_id=guild_id,created_by=created_by,name=name,payload=payload); s.add(row)
            else: row.created_by=created_by; row.payload=payload
            await s.commit(); return row
    async def snapshots(self, guild_id, limit=50):
        async with self.db.session() as s:
            return list((await s.execute(select(ConfigSnapshot).where(ConfigSnapshot.guild_id==guild_id).order_by(ConfigSnapshot.id.desc()).limit(limit))).scalars())

    async def snapshot_get(self,guild_id,name):
        async with self.db.session() as s: return (await s.execute(select(ConfigSnapshot).where(ConfigSnapshot.guild_id==guild_id,ConfigSnapshot.name==name))).scalar_one_or_none()
    async def snapshot_delete(self,guild_id,name):
        async with self.db.session() as s:
            await s.execute(delete(ConfigSnapshot).where(ConfigSnapshot.guild_id==guild_id,ConfigSnapshot.name==name))
            await s.commit()
    async def ticket_create(self,guild_id,channel_id,opener_id,category='general'):
        async with self.db.session() as s:
            row=Ticket(guild_id=guild_id,channel_id=channel_id,opener_id=opener_id,category=category); s.add(row); await s.commit(); return row
    async def ticket_get(self,channel_id):
        async with self.db.session() as s: return (await s.execute(select(Ticket).where(Ticket.channel_id==channel_id))).scalar_one_or_none()
    async def ticket_update(self,channel_id,**changes):
        async with self.db.session() as s:
            row=(await s.execute(select(Ticket).where(Ticket.channel_id==channel_id).with_for_update())).scalar_one_or_none()
            if not row: return None
            for k,v in changes.items():
                if hasattr(row,k): setattr(row,k,v)
            if changes.get('status')=='closed': row.closed_at=datetime.now(timezone.utc)
            await s.commit(); return row
    async def tickets(self,guild_id,status=None):
        async with self.db.session() as s:
            q=select(Ticket).where(Ticket.guild_id==guild_id)
            if status:q=q.where(Ticket.status==status)
            return list((await s.execute(q.order_by(Ticket.id.desc()))).scalars())
