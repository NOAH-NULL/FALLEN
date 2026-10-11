from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import re
import time
from urllib.parse import urlparse
import regex as safe_regex
from sqlalchemy import delete, select, func, or_
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

# Only capabilities with a verified runtime implementation may be enabled.
# The rest remain in the catalog for future work, but must not masquerade as
# working security controls or silently report as active.
IMPLEMENTED_FEATURES = {
    # Join-screening signals are catalog-only until they have an explicit,
    # tested verification/quarantine workflow. Do not advertise detection-only
    # flags as complete security controls.
    "raid_join_rate", "automatic_lockdown", "anti_channel_delete",
    "anti_role_delete", "security_timeline",
    "temporary_bans", "temporary_timeouts", "scheduled_punishments",
    "regex_rules", "duplicate_messages", "flood_detection", "emoji_spam",
    "domain_whitelist", "domain_blacklist", "mention_spam",
    "server_reputation", "member_profiles", "personal_playlists",
}
DEFAULTS = {name: False for name in ALL_FEATURES}
for _name in {"server_reputation", "member_profiles", "personal_playlists"}:
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
        out = dict(DEFAULTS)
        # Ignore stale database values for catalog-only features until their
        # behavior exists and has dedicated tests.
        # Treat only actual JSON booleans as feature flags. In Python,
        # bool("false") is True, which could accidentally enable security
        # controls from malformed or legacy configuration.
        out.update({
            key: value
            for key, value in stored.items()
            if key in IMPLEMENTED_FEATURES and isinstance(value, bool)
        })
        self._settings_cache[guild_id] = (now + self._settings_ttl, dict(out))
        return out
    async def set(self, guild_id: int, key: str, value):
        key = key.strip().lower()
        if key not in ALL_FEATURES:
            raise ValueError(f"Unknown V16 feature: {key}")
        if not isinstance(value, bool):
            raise ValueError("Feature state must be a boolean")
        enabled = value
        if key not in IMPLEMENTED_FEATURES and enabled:
            raise ValueError(
                f"V16 feature '{key}' is catalog-only and is not implemented yet"
            )
        async with self.db.session() as s:
            row = await s.get(GuildConfig, guild_id, with_for_update=True)
            if not row:
                row = GuildConfig(guild_id=guild_id, extreme_settings={}); s.add(row); await s.flush()
            data = dict(row.extreme_settings or {}); data[key] = enabled; row.extreme_settings = data; await s.commit()
        self._settings_cache.pop(guild_id, None)
        return enabled
    async def enabled(self, guild_id: int, key: str) -> bool:
        return bool((await self.get(guild_id)).get(key, False))
    async def snapshot(self, guild_id: int) -> dict:
        return {"guild_id": guild_id, "created_at": datetime.now(timezone.utc).isoformat(), "features": await self.get(guild_id)}
    async def restore_features(self, guild_id: int, features) -> dict:
        """Atomically restore supported boolean feature flags from a snapshot."""
        if not isinstance(features, dict):
            raise ValueError("Snapshot features must be an object")
        clean = {}
        skipped = []
        for key, value in features.items():
            if key not in ALL_FEATURES:
                skipped.append(str(key))
            elif key not in IMPLEMENTED_FEATURES:
                skipped.append(str(key))
            elif not isinstance(value, bool):
                skipped.append(str(key))
            else:
                clean[key] = value

        async with self.db.session() as s:
            row = await s.get(GuildConfig, guild_id, with_for_update=True)
            if row is None:
                row = GuildConfig(guild_id=guild_id, extreme_settings={})
                s.add(row)
                await s.flush()
            data = dict(row.extreme_settings or {})
            data.update(clean)
            row.extreme_settings = data
            await s.commit()
        self._settings_cache.pop(guild_id, None)
        return {"restored": len(clean), "skipped": skipped}

    async def validate(self, guild_id: int) -> list[str]:
        errors = []
        async with self.db.session() as s:
            row = await s.get(GuildConfig, guild_id)
            stored = dict(row.extreme_settings or {}) if row else {}
        for key, value in stored.items():
            if key not in ALL_FEATURES:
                errors.append(f"Unknown stored feature: {key}")
            elif not isinstance(value, bool):
                errors.append(f"Stored feature '{key}' must be a boolean; its value is ignored")
            elif key not in IMPLEMENTED_FEATURES and value:
                errors.append(
                    f"Catalog-only feature '{key}' is stored as enabled but is not implemented; its value is ignored"
                )
        return errors
    async def record_security(self,guild_id,event_type,actor_id=None,target_id=None,details=None):
        async with self.db.session() as s:
            s.add(SecurityEvent(guild_id=guild_id,event_type=event_type,actor_id=actor_id,target_id=target_id,details=details or {})); await s.commit()
    async def security_events(self,guild_id,limit=25):
        async with self.db.session() as s:
            return list((await s.execute(select(SecurityEvent).where(SecurityEvent.guild_id==guild_id).order_by(SecurityEvent.id.desc()).limit(limit))).scalars())
    async def schedule(self,guild_id,target_id,action,run_at,payload=None):
        action = str(action).strip().lower()
        if action not in {"ban", "timeout"}:
            raise ValueError("Scheduled action must be 'ban' or 'timeout'")
        if not isinstance(run_at, datetime) or run_at.tzinfo is None or run_at.utcoffset() is None:
            raise ValueError("Scheduled action time must be timezone-aware")
        if int(guild_id) <= 0 or int(target_id) <= 0:
            raise ValueError("Scheduled action guild and target IDs must be positive")
        async with self.db.session() as s:
            row=ScheduledAction(guild_id=int(guild_id),target_id=int(target_id),action=action,run_at=run_at,payload=payload or {}); s.add(row); await s.commit(); return row.id
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
                    or_(
                        ScheduledAction.processing.is_(False),
                        ScheduledAction.claimed_at.is_(None),
                        ScheduledAction.claimed_at < stale,
                    ),
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
        name = str(name).strip()
        kind = str(kind).strip().lower()
        action = str(action).strip().lower()
        pattern = str(pattern or '').strip()
        if not name or len(name) > 64:
            raise ValueError('Rule name must contain 1–64 characters')
        if kind not in {'regex', 'domain_blacklist', 'domain_whitelist'}:
            raise ValueError('Unsupported AutoMod rule kind')
        if action not in {'delete', 'warn', 'log'}:
            raise ValueError('Action must be delete, warn, or log')
        if not pattern or len(pattern) > 1000:
            raise ValueError('Rule pattern must contain 1–1000 characters')
        if kind == 'regex':
            try:
                safe_regex.compile(pattern)
            except safe_regex.error as exc:
                raise ValueError(f'Invalid regular expression: {exc}') from exc
        else:
            parsed = urlparse(pattern if '://' in pattern else '//' + pattern)
            host = parsed.hostname
            if not host:
                raise ValueError('Domain rules require a valid hostname')
            pattern = host.rstrip('.').lower()
        async with self.db.session() as s:
            existing_result = await s.execute(
                select(AutoModRule).where(
                    AutoModRule.guild_id == guild_id,
                    AutoModRule.name == name,
                )
            )
            existing = existing_result.scalar_one_or_none()
            if existing is None:
                total_result = await s.execute(
                    select(func.count(AutoModRule.id)).where(
                        AutoModRule.guild_id == guild_id
                    )
                )
                if int(total_result.scalar_one() or 0) >= 100:
                    raise ValueError("A server can have at most 100 AutoMod rules")
            if kind == "regex" and (existing is None or existing.kind != "regex"):
                regex_result = await s.execute(
                    select(func.count(AutoModRule.id)).where(
                        AutoModRule.guild_id == guild_id,
                        AutoModRule.kind == "regex",
                    )
                )
                if int(regex_result.scalar_one() or 0) >= 50:
                    raise ValueError("A server can have at most 50 regex rules")
            stmt=pg_insert(AutoModRule).values(
                guild_id=guild_id,
                name=name,
                kind=kind,
                pattern=pattern,
                action=action,
                config=config or {},
                enabled=enabled,
            ).on_conflict_do_update(
                index_elements=['guild_id', 'name'],
                set_={
                    'kind': kind,
                    'pattern': pattern,
                    'action': action,
                    'config': config or {},
                    'enabled': enabled,
                },
            ).returning(AutoModRule.id)
            rule_id=(await s.execute(stmt)).scalar_one()
            await s.commit()
            self._rules_cache.pop(guild_id, None)
            result=await s.execute(select(AutoModRule).where(AutoModRule.id==rule_id))
            return result.scalar_one()
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
                score=max(-100000, min(100000, delta)),
            ).on_conflict_do_update(
                index_elements=['guild_id', 'user_id'],
                set_={'score': func.least(func.greatest(Reputation.score + delta, -100000), 100000)},
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
        name = str(name).strip()
        if len(name)>64 or not name: raise ValueError('Invalid playlist name')
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
    async def ticket_create(self, guild_id, channel_id, opener_id, category='general'):
        """Create one durable ticket row per channel, safely handling duplicate clicks."""
        async with self.db.session() as s:
            statement = pg_insert(Ticket).values(
                guild_id=guild_id,
                channel_id=channel_id,
                opener_id=opener_id,
                category=category,
            ).on_conflict_do_nothing(index_elements=[Ticket.channel_id])
            await s.execute(statement)
            await s.commit()
            result = await s.execute(
                select(Ticket).where(Ticket.channel_id == channel_id)
            )
            return result.scalar_one_or_none()
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
