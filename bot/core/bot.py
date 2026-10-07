import asyncio
import random
import logging
from collections import defaultdict, deque
import discord
from discord.ext import commands
from bot.core.db import Database
from bot.core.health import start_health_server
from bot.core.metrics import GATEWAY_LATENCY,GUILDS,EVENTS,start_metrics
from bot.core.telemetry import setup_telemetry
from bot.cache.redis import RedisCache
from bot.cache.rate_limit import DistributedRateLimiter
from bot.cache.invalidation import CacheInvalidationSubscriber
from bot.services.guild_config import GuildConfigService
from bot.services.greeting import GreetingRenderer
from bot.services.music import MusicService
from bot.services.automod import AutoModService
from bot.services.custom_commands import CustomCommandService
from bot.services.levels import LevelService
from bot.services.tickets import TicketService
from bot.services.platform import PlatformService
from bot.services.antiraid import AntiRaid
from bot.services.reactions import ReactionGifService
from bot.services.uwuify import UwuifyService
from bot.services.invites import InviteTracker
from bot.services.extreme import ExtremeService
from bot.services.v16_runtime import V16Runtime
from bot.workers.greetings import GreetingWorker
from bot.workers.gateway import GatewayWorkerPool
from bot.workers.scheduler import Scheduler
from bot.web.api import DashboardAPI
from bot.core.event_queue import GatewayEventQueue
from bot.core.shard_lease import ShardLeaseManager
from bot.core.app_errors import handle_app_command_error
from bot.core.prefix_errors import handle_prefix_command_error
from bot.ui import info_embed
log=logging.getLogger('bot')
EXTENSIONS=('bot.commands.greeting','bot.commands.moderation','bot.commands.fun','bot.commands.utility','bot.commands.invites','bot.commands.music','bot.commands.admin','bot.commands.community','bot.commands.custom','bot.commands.tickets','bot.commands.platform','bot.commands.control','bot.commands.engagement','bot.commands.security','bot.commands.text','bot.commands.help','bot.commands.extreme','bot.commands.levels')
class Bot(commands.AutoShardedBot):
    def __init__(self,settings):
        intents=discord.Intents.default(); intents.members=True; intents.message_content=True
        kwargs={'command_prefix':settings.command_prefix,'intents':intents,'chunk_guilds_at_startup':False,'help_command':None}
        if settings.shard_count is not None: kwargs['shard_count']=settings.shard_count
        if settings.parsed_shard_ids is not None: kwargs['shard_ids']=settings.parsed_shard_ids
        super().__init__(**kwargs); self.settings=settings; self.log=log
        self.tree.on_error = handle_app_command_error
        self.add_listener(handle_prefix_command_error, 'on_command_error')
        self.db=Database(settings); self.cache=RedisCache(settings.redis_url,settings.redis_max_connections)
        self.limiter=DistributedRateLimiter(self.cache); self.guild_config=GuildConfigService(self.db,self.cache,settings.cache_ttl_seconds,settings.redis_lock_ttl_ms)
        self.greetings=GreetingRenderer(); self.music=MusicService(self,settings.music_url,settings.music_password); self.greeting_worker=GreetingWorker(self,settings.greeting_queue_size,settings.greeting_workers,settings.greeting_max_event_age)
        self.invalidation=CacheInvalidationSubscriber(self.cache); self.scheduler=Scheduler(self); self.dashboard=DashboardAPI(self,settings.dashboard_host,settings.dashboard_port)
        self.automod=AutoModService(self.cache, settings.automod_heat_decay, settings.automod_heat_ttl); self.custom_commands=CustomCommandService(self.db,self.cache); self.levels=LevelService(self.db); self.tickets=TicketService(); self.platform=PlatformService(self.db); self.extreme=ExtremeService(self.db); self.v16=V16Runtime(self); self.antiraid=AntiRaid(self.cache); self.reactions=ReactionGifService(); self.uwuify=UwuifyService(self.cache); self.invites=InviteTracker(self.db,self.cache,settings.invite_join_queue_size,settings.invite_stat_flush_interval,bot=self)
        self.gateway_queue=GatewayEventQueue(settings.gateway_queue_size, settings.gateway_critical_queue_size); self.gateway_workers=GatewayWorkerPool(self,self.gateway_queue,settings.gateway_workers,settings.gateway_guild_concurrency,settings.gateway_max_event_age,settings.gateway_dlq_maxsize)
        self.shard_leases=ShardLeaseManager(self.cache, settings.instance_id, settings.shard_lease_ttl_ms); self.shard_leases.bind_shutdown(self.close); self.db.set_fence_guard(self.shard_leases.validate_fence)
        self._xp_cooldown={}; self._xp_cap=200000; self.health_runner=None
        self._destructive_actions = defaultdict(deque)
    async def setup_hook(self):
        setup_telemetry(self.settings); start_metrics(self.settings.metrics_host,self.settings.metrics_port); self.health_runner=await start_health_server(self,self.settings.metrics_host,self.settings.health_port)
        shard_ids=self.settings.parsed_shard_ids or list(range(self.settings.shard_count or 1))
        await self.shard_leases.acquire(shard_ids)
        await self.music.start(); await self.greetings.start(); await self.reactions.start(); await self.greeting_worker.start(); await self.invites.start(); await self.gateway_workers.start(); await self.invalidation.start(); await self.scheduler.start(); await self.dashboard.start()
        for ext in EXTENSIONS: await self.load_extension(ext)
        if self.settings.guild_id: g=discord.Object(id=self.settings.guild_id); self.tree.copy_global_to(guild=g); await self.tree.sync(guild=g)
        else: await self.tree.sync()
    async def security_lockdown(self, guild_id: int, reason: str = "V16 lockdown"):
        guild = self.get_guild(guild_id)
        if not guild:
            return 0
        existing = await self.extreme.snapshot_get(guild_id, "__lockdown__")
        if not existing:
            state = {str(ch.id): ch.overwrites_for(guild.default_role).send_messages for ch in guild.text_channels}
            await self.extreme.snapshot_save(guild_id, guild.me.id if guild.me else 0, "__lockdown__", {"channels": state, "created_at": discord.utils.utcnow().isoformat()})
        changed = 0
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(guild.default_role, send_messages=False, reason=reason[:512])
                changed += 1
            except discord.HTTPException:
                continue
        await self.extreme.record_security(guild_id, "automatic_lockdown", details={"reason": reason, "channels": changed})
        return changed

    async def security_unlockdown(self, guild_id: int, reason: str = "V16 lockdown recovery"):
        guild = self.get_guild(guild_id)
        if not guild:
            return 0
        snapshot = await self.extreme.snapshot_get(guild_id, "__lockdown__")
        state = snapshot.payload.get("channels", {}) if snapshot else {}
        changed = 0
        for channel in guild.text_channels:
            try:
                if str(channel.id) not in state:
                    continue
                value = state[str(channel.id)]
                await channel.set_permissions(guild.default_role, send_messages=value, reason=reason[:512])
                changed += 1
            except discord.HTTPException:
                continue
        if snapshot:
            await self.extreme.snapshot_delete(guild_id, "__lockdown__")
        await self.extreme.record_security(guild_id, "lockdown_recovery", details={"reason": reason, "channels": changed, "restored_snapshot": bool(snapshot)})
        return changed

    async def snapshot_security_state(self, guild, created_by=0, name="__security_state__"):
        payload = {
            "channels": {str(ch.id): {"name": ch.name, "position": ch.position,
                "overwrites": {str(target.id): {"allow": ow.pair()[0].value, "deny": ow.pair()[1].value}
                    for target, ow in ch.overwrites.items()}} for ch in guild.channels},
            "roles": {str(role.id): {"name": role.name, "position": role.position, "permissions": role.permissions.value,
                "colour": role.colour.value, "hoist": role.hoist, "mentionable": role.mentionable}
                for role in guild.roles if not role.is_default()},
        }
        return await self.extreme.snapshot_save(guild.id, created_by, name, payload)

    async def restore_security_state(self, guild, name="__security_state__"):
        snapshot = await self.extreme.snapshot_get(guild.id, name)
        if not snapshot:
            return {"roles": 0, "channels": 0}
        restored = {"roles": 0, "channels": 0}
        role_data = snapshot.payload.get("roles", {})
        for role_id, data in role_data.items():
            role = guild.get_role(int(role_id))
            if not role or role >= guild.me.top_role:
                continue
            try:
                await role.edit(
                    name=data.get("name", role.name),
                    permissions=discord.Permissions(data.get("permissions", role.permissions.value)),
                    colour=discord.Colour(data.get("colour", role.colour.value)),
                    hoist=data.get("hoist", role.hoist),
                    mentionable=data.get("mentionable", role.mentionable),
                    reason="Fallen anti-nuke restoration",
                )
                restored["roles"] += 1
            except discord.HTTPException:
                continue

        role_positions = {
            guild.get_role(int(role_id)): int(data.get("position", 0))
            for role_id, data in role_data.items()
            if guild.get_role(int(role_id)) and guild.get_role(int(role_id)) < guild.me.top_role
        }
        if role_positions:
            try:
                await guild.edit_role_positions(
                    positions=role_positions,
                    reason="Fallen anti-nuke restoration",
                )
            except discord.HTTPException:
                pass

        # Restore overwrites for channels that still exist. Missing targets are
        # skipped because their Discord object no longer exists.
        channel_data = snapshot.payload.get("channels", {})
        for channel_id, data in channel_data.items():
            channel = guild.get_channel(int(channel_id))
            if channel is None:
                continue
            try:
                await channel.edit(
                    name=data.get("name", channel.name),
                    position=data.get("position", channel.position),
                    reason="Fallen anti-nuke restoration",
                )
            except discord.HTTPException:
                pass
            for target_id, overwrite_data in (data.get("overwrites") or {}).items():
                target = guild.get_role(int(target_id)) or guild.get_member(int(target_id))
                if target is None:
                    continue
                try:
                    allow = discord.Permissions(overwrite_data.get("allow", 0))
                    deny = discord.Permissions(overwrite_data.get("deny", 0))
                    overwrite = discord.PermissionOverwrite.from_pair(allow, deny)
                    await channel.set_permissions(
                        target,
                        overwrite=overwrite,
                        reason="Fallen anti-nuke restoration",
                    )
                    restored["channels"] += 1
                except (discord.HTTPException, discord.Forbidden):
                    continue
        return restored

    async def quarantine_member(self, guild, member, reason="Fallen anti-nuke quarantine"):
        if not member or not guild.me or member.id in {guild.owner_id, guild.me.id}:
            return False
        quarantine = discord.utils.get(guild.roles, name="Fallen Quarantine")
        if quarantine is None:
            try:
                quarantine = await guild.create_role(name="Fallen Quarantine", permissions=discord.Permissions.none(), reason=reason)
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(quarantine, view_channel=False, send_messages=False, reason=reason)
                    except discord.HTTPException:
                        pass
            except discord.HTTPException:
                return False
        try:
            removable = [r for r in member.roles[1:] if r < guild.me.top_role and r != quarantine]
            if removable:
                await self.extreme.snapshot_save(
                    guild.id,
                    guild.me.id if guild.me else 0,
                    f"__quarantine__:{member.id}",
                    {"member_id": member.id, "role_ids": [r.id for r in removable]},
                )
                await member.remove_roles(*removable, reason=reason)
            await member.add_roles(quarantine, reason=reason)
            await self.extreme.record_security(guild.id, "rogue_staff_quarantine", actor_id=member.id, details={"reason": reason})
            return True
        except discord.HTTPException:
            return False

    async def restore_quarantined_member(self, guild, member_id: int):
        snapshot = await self.extreme.snapshot_get(guild.id, f"__quarantine__:{member_id}")
        if not snapshot:
            return 0
        member = guild.get_member(member_id)
        if member is None:
            return 0
        restored = 0
        try:
            roles = [
                guild.get_role(int(role_id))
                for role_id in snapshot.payload.get("role_ids", [])
            ]
            roles = [r for r in roles if r and r < guild.me.top_role]
            if roles:
                await member.add_roles(*roles, reason="Fallen anti-nuke quarantine recovery")
                restored = len(roles)
            await self.extreme.snapshot_delete(guild.id, f"__quarantine__:{member_id}")
        except discord.HTTPException:
            return restored
        return restored

    async def restore_deleted_resource(self, guild, resource, action):
        """Best-effort recreation of a freshly deleted channel/role."""
        try:
            if action == 'channel_delete' and hasattr(resource, 'name'):
                category = guild.get_channel(resource.category_id) if getattr(resource, 'category_id', None) else None
                overwrites = resource.overwrites
                created = await guild.create_text_channel(resource.name, category=category, position=resource.position, overwrites=overwrites, reason='Fallen anti-nuke restoration')
                return created.id
            if action == 'role_delete' and hasattr(resource, 'name'):
                role = await guild.create_role(name=resource.name, permissions=resource.permissions, colour=resource.colour, hoist=resource.hoist, mentionable=resource.mentionable, reason='Fallen anti-nuke restoration')
                try:
                    await role.edit(position=min(resource.position, guild.me.top_role.position - 1), reason='Fallen anti-nuke restoration')
                except discord.HTTPException:
                    pass
                return role.id
        except discord.HTTPException:
            return None
        return None

    async def _observe_destructive_action(self, guild, actor_id: int | None, action: str, target_id: int | None = None, resource=None):
        if actor_id is None or not guild:
            return
        now = asyncio.get_running_loop().time()
        key = (guild.id, actor_id, action)
        q = self._destructive_actions[key]
        q.append(now)
        while q and now - q[0] > 12:
            q.popleft()
        await self.extreme.record_security(guild.id, action, actor_id=actor_id, target_id=target_id, details={"burst_count": len(q)})
        if len(q) >= 3:
            member = guild.get_member(actor_id)
            if member and await self.extreme.enabled(guild.id, "automatic_lockdown"):
                # Keep the durable baseline captured at startup. Taking a
                # new snapshot after the destructive event would snapshot the
                # compromised state and make restoration ineffective.
                await self.quarantine_member(guild, member, reason=f"Fallen anti-nuke: {action} burst")
                await self.restore_deleted_resource(guild, resource, action) if resource else None
                await self.restore_security_state(guild)
                await self.security_lockdown(guild.id, reason=f"Fallen anti-nuke containment: {action} burst by {actor_id}")
                q.clear()

    async def _audit_actor_for(self, guild, action, target_id):
        # Audit-log entries can lag the gateway event by a short interval.
        # Retry briefly before treating attribution as unknown.
        for attempt in range(3):
            try:
                async for entry in guild.audit_logs(limit=8, action=action):
                    if getattr(entry.target, "id", None) == target_id:
                        return entry.user.id if entry.user else None
            except discord.HTTPException:
                if attempt == 2:
                    return None
            if attempt < 2:
                await asyncio.sleep(0.35 * (attempt + 1))
        return None

    async def on_ready(self):
        GUILDS.set(len(self.guilds)); GATEWAY_LATENCY.set(self.latency); log.info('ready guilds=%d shards=%s ids=%s',len(self.guilds),self.shard_count,self.shard_ids)
        for guild in self.guilds:
            await self.invites.refresh_guild(guild)
            if await self.extreme.snapshot_get(guild.id, '__security_state__') is None:
                try: await self.snapshot_security_state(guild, guild.me.id if guild.me else 0)
                except Exception: log.exception('security baseline snapshot failed guild=%s', guild.id)
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        actor = await self._audit_actor_for(guild, discord.AuditLogAction.channel_delete, channel.id)
        if await self.extreme.enabled(guild.id, "anti_channel_delete"):
            await self._observe_destructive_action(guild, actor, "channel_delete", channel.id, channel)

    async def on_guild_role_delete(self, role):
        guild = role.guild
        actor = await self._audit_actor_for(guild, discord.AuditLogAction.role_delete, role.id)
        if await self.extreme.enabled(guild.id, "anti_role_delete"):
            await self._observe_destructive_action(guild, actor, "role_delete", role.id, role)

    async def on_guild_join(self,guild): GUILDS.set(len(self.guilds)); EVENTS.labels('guild_join').inc(); await self.guild_config.invalidate(guild.id)
    async def on_guild_remove(self,guild): GUILDS.set(len(self.guilds)); EVENTS.labels('guild_remove').inc()
    # Gateway callbacks are intentionally O(1): enqueue and return immediately.
    async def on_member_join(self,m): self.gateway_queue.put_nowait('member_join',m,critical=True)
    async def on_member_remove(self,m): self.gateway_queue.put_nowait('member_remove',m)
    async def on_message(self,message):
        if message.author.bot or not message.guild:return
        critical = message.content.startswith(self.command_prefix)
        self.gateway_queue.put_nowait('message',message,critical=critical)
    async def process_member_join(self,m):
        legacy_raid = await self.antiraid.observe(m.guild.id)
        actions = await self.v16.member_join(m)
        raid = legacy_raid or "raid" in actions
        if raid: log.warning('V16 anti-raid threshold reached guild=%s; shedding welcome work',m.guild.id)
        cfg=await self.guild_config.get(m.guild.id)
        role_id=cfg.get('autorole_id')
        if role_id:
            role=m.guild.get_role(role_id)
            if role and role < (m.guild.me.top_role if m.guild.me else role):
                try:
                    await m.add_roles(role,reason='Configured autorole')
                except discord.HTTPException:
                    log.warning('autorole failed guild=%s member=%s',m.guild.id,m.id)

        # Welcome/goodbye delivery has one owner: GreetingWorker.
        # Keeping welcome sending out of this gateway worker prevents duplicate
        # welcome messages and keeps invite attribution + banner rendering in
        # the same pipeline.
        try:
            queued = await self.invites.submit_join(m, suppress_greeting=raid)
            if not queued and not raid:
                fallback = await self.greeting_worker.submit(m, 'welcome')
                if not fallback:
                    log.warning('welcome queue full guild=%s member=%s', m.guild.id, m.id)
        except Exception:
            log.exception('welcome scheduling failed guild=%s member=%s', m.guild.id, m.id)
            if not raid:
                try:
                    fallback = await self.greeting_worker.submit(m, 'welcome')
                    if not fallback:
                        log.warning('welcome fallback queue full guild=%s member=%s', m.guild.id, m.id)
                except Exception:
                    log.exception('welcome fallback failed guild=%s member=%s', m.guild.id, m.id)
    async def process_member_remove(self,m):
        await self.invites.record_leave(m)
        await self.greeting_worker.submit(m,'goodbye')
    async def process_message(self,message):
        # Prefix commands take the fast lane: parse/invoke before non-critical
        # XP, invite and moderation bookkeeping. This keeps command latency
        # independent of background engagement work.
        if message.content.startswith(self.command_prefix):
            ctx = await self.get_context(message)
            if ctx.command:
                await self.invoke(ctx)
                return
            raw = message.content[len(self.command_prefix):].strip().split(maxsplit=1)
            if raw:
                response = await self.custom_commands.get(message.guild.id, raw[0].lower())
                if response:
                    await message.channel.send(response[:1900], allowed_mentions=discord.AllowedMentions.none())
                    return

        cfg=await self.guild_config.get(message.guild.id)

        # Real-time UwUify: transform the exact incoming message for users who
        # opted into the feature. Discord does not allow bots to edit another
        # user's message, so the safe implementation deletes and reposts the
        # transformed content. Bot messages are already ignored in on_message.
        uwu = await self.uwuify.transform_message(message.guild.id, message.author.id, message.content)
        if uwu is not None and uwu != message.content:
            try:
                await message.delete(reason='Fallen UwUify transformation')
                await message.channel.send(uwu, allowed_mentions=discord.AllowedMentions.none(), reference=message, mention_author=False)
            except discord.HTTPException:
                log.warning('UwUify failed guild=%s user=%s message=%s', message.guild.id, message.author.id, message.id)
            return

        reasons = await self.v16.message_check(message)
        if cfg.get('automod_enabled') and self.automod.check(message.guild.id,message.author.id,message.content,cfg.get('spam_limit',6),cfg.get('spam_window',8)):
            reasons.append('legacy_automod')
        if reasons:
            try: await message.delete(); EVENTS.labels('automod_delete').inc(); await self.extreme.record_security(message.guild.id,'automod_action',actor_id=message.author.id,details={'reasons':reasons,'message_id':message.id})
            except discord.HTTPException: pass
            return
        try:
            eligible, level_cfg = await self.levels.eligible(
                message.guild.id,
                message.channel.id,
                {r.id for r in message.author.roles},
            )
            if not eligible:
                return
            allowed = await self.limiter.allow(
                f"xp:{message.guild.id}:{message.author.id}",
                1,
                level_cfg["cooldown_seconds"],
            )
            if not allowed:
                return

            amount = await self.levels.calculate_message_xp(
                message.guild.id,
                message.content,
            )
            if amount <= 0:
                return

            bonus_roles = level_cfg.get("bonus_roles") or {}
            member_role_ids = {r.id for r in message.author.roles}
            multipliers = [
                int(multiplier) for role_id, multiplier in bonus_roles.items()
                if int(role_id) in member_role_ids
            ]
            if multipliers:
                amount *= max(multipliers)

            key = (message.guild.id, message.author.id)
            new_level, leveled_up, _, total_xp = await self.levels.add_xp(*key, amount=amount)
            if not leveled_up:
                return

            member = message.guild.get_member(message.author.id)
            reward = await self.levels.role_for_level(message.guild.id, new_level)
            if member and reward:
                role = message.guild.get_role(reward.role_id)
                if role and message.guild.me and role < message.guild.me.top_role:
                    configured = await self.levels.configured_roles(message.guild.id)
                    if not level_cfg.get("stack_awards", True):
                        old_roles = [
                            message.guild.get_role(r.role_id)
                            for r in configured
                            if r.role_id != role.id and r.level < new_level
                        ]
                        remove = [
                            r for r in old_roles
                            if r and r in member.roles and r < message.guild.me.top_role
                        ]
                        if remove:
                            await member.remove_roles(*remove, reason=f"Level {new_level} reward replacement")
                    if role not in member.roles:
                        await member.add_roles(role, reason=f"Reached level {new_level}")

            if level_cfg["announce"]:
                target = message.guild.get_channel(level_cfg["announcement_channel_id"]) if level_cfg["announcement_channel_id"] else message.channel
                if target:
                    embed = info_embed(
                        "Level Up!",
                        f"{message.author.mention} reached **Level {new_level}**!\n\nTotal XP: **{total_xp:,}**",
                    )
                    try:
                        await target.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
                    except discord.HTTPException:
                        log.warning("level-up announcement failed guild=%s user=%s", message.guild.id, message.author.id)
        except Exception:
            log.exception("level update failed")
    async def close(self):
        if self.health_runner: await self.health_runner.cleanup()
        await self.music.close()
        # Drain accepted gateway work before releasing shard ownership or closing dependencies.
        await self.gateway_workers.close(self.settings.gateway_shutdown_timeout)
        await self.invites.close(); await self.shard_leases.release(); await self.invalidation.close(); await self.scheduler.close(); await self.dashboard.close(); await self.greeting_worker.close(); await self.greetings.close(); await self.reactions.close(); await self.cache.close(); await self.db.close(); await super().close()
