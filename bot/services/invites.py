from __future__ import annotations
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from sqlalchemy import text, select
import discord
from bot.models import InviteStat

log = logging.getLogger('bot.invites')

@dataclass(slots=True)
class InviteSnapshot:
    code: str
    uses: int
    inviter_id: int | None
    max_uses: int
    temporary: bool

class InviteTracker:
    """Burst-resistant invite attribution.

    Redis is used for short-lived invite snapshots, per-member attribution,
    distributed refresh single-flight, and buffered statistics. PostgreSQL
    remains the source of truth; Redis is never required for correctness of
    the persistent leaderboard once buffered writes are flushed.
    """
    SNAPSHOT_TTL = 120
    ATTRIBUTION_TTL = 60 * 60 * 24 * 90
    FLUSH_INTERVAL = 1.0
    STAT_BATCH_SIZE = 500
    ATTR_BATCH_SIZE = 250

    def __init__(self, db, cache=None, join_queue_size=2000, flush_interval=1.0, bot=None):
        self.db = db
        self.cache = cache
        self.bot = bot
        self._snapshots: dict[int, dict[str, InviteSnapshot]] = {}
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._attr_task: asyncio.Task | None = None
        self._attr_queue: asyncio.Queue[tuple[int, int, int | None, str | None, str]] = asyncio.Queue(maxsize=5000)
        self._join_queue: asyncio.Queue[tuple[discord.Member, bool]] | None = None
        self._join_task: asyncio.Task | None = None
        self._closing = False
        self.join_queue_size = max(100, int(join_queue_size))
        self.flush_interval = max(0.1, float(flush_interval))

    @staticmethod
    def _snapshot_key(guild_id: int) -> str:
        return f'invite-snapshot:{guild_id}'

    @staticmethod
    def _buffer_key(guild_id: int) -> str:
        return f'invite-buffer:{guild_id}'

    @staticmethod
    def _member_key(guild_id: int, member_id: int) -> str:
        return f'invite-attribution:{guild_id}:{member_id}'

    @staticmethod
    def _encode(snap: dict[str, InviteSnapshot]):
        return {code: {'uses': v.uses, 'inviter_id': v.inviter_id, 'max_uses': v.max_uses, 'temporary': v.temporary} for code, v in snap.items()}

    @staticmethod
    def _decode(raw) -> dict[str, InviteSnapshot]:
        return {code: InviteSnapshot(code, int(v.get('uses', 0)), v.get('inviter_id'), int(v.get('max_uses', 0)), bool(v.get('temporary', False))) for code, v in (raw or {}).items()}

    async def start(self):
        if self.cache is None or self._flush_task:
            return
        self._closing = False
        self._flush_task = asyncio.create_task(self._flush_loop(), name='invite-stat-flusher')
        self._attr_task = asyncio.create_task(self._attribution_loop(), name='invite-attribution-flusher')

    async def close(self):
        self._closing = True
        if self._join_queue is not None:
            try:
                await asyncio.wait_for(self._join_queue.join(), 5.0)
            except asyncio.TimeoutError:
                log.warning('invite join queue did not drain before shutdown')
        for task in (self._join_task, self._flush_task, self._attr_task):
            if task:
                task.cancel()
        tasks = [t for t in (self._join_task, self._flush_task, self._attr_task) if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._join_task = self._flush_task = self._attr_task = None
        if self.cache is not None:
            try:
                await self._flush_once()
            except Exception:
                log.exception('invite stat flush during shutdown failed')
        deadline = asyncio.get_running_loop().time() + 5.0
        while not self._attr_queue.empty() and asyncio.get_running_loop().time() < deadline:
            try:
                await self._flush_attribution_batch()
            except Exception:
                log.exception('invite attribution flush during shutdown failed')
                break

    async def _fetch_guild(self, guild: discord.Guild) -> dict[str, InviteSnapshot] | None:
        try:
            invites = await guild.invites()
        except (discord.Forbidden, discord.HTTPException):
            log.warning('cannot read invites guild=%s', guild.id)
            return None
        return {
            inv.code: InviteSnapshot(inv.code, inv.uses or 0, inv.inviter.id if inv.inviter else None, inv.max_uses or 0, inv.temporary)
            for inv in invites
        }

    async def refresh_guild(self, guild: discord.Guild) -> None:
        key = self._snapshot_key(guild.id)
        # One pod refreshes a guild at a time. Other pods reuse the last
        # snapshot instead of stampeding Discord's invite endpoint.
        if self.cache is not None:
            token = uuid.uuid4().hex
            if not await self.cache.acquire_lock(f'{key}:lock', token, 8000):
                return
            try:
                snap = await self._fetch_guild(guild)
                if snap is not None:
                    payload = self._encode(snap)
                    async with self._lock:
                        self._snapshots[guild.id] = snap
                    await self.cache.set_json(key, payload, self.SNAPSHOT_TTL)
            finally:
                await self.cache.release_lock(f'{key}:lock', token)
            return
        snap = await self._fetch_guild(guild)
        if snap is not None:
            async with self._lock:
                self._snapshots[guild.id] = snap

    async def _cached_snapshot(self, guild_id: int) -> dict[str, InviteSnapshot]:
        if self.cache is not None:
            raw = await self.cache.get_json(self._snapshot_key(guild_id))
            if raw is not None:
                return self._decode(raw)
        async with self._lock:
            return dict(self._snapshots.get(guild_id, {}))

    async def _buffer_delta(self, guild_id: int, user_id: int, joins: int = 0, leaves: int = 0):
        if self.cache is None:
            async with self.db.session() as s:
                row = (await s.execute(select(InviteStat).where(InviteStat.guild_id == guild_id, InviteStat.user_id == user_id))).scalar_one_or_none()
                if row:
                    row.joins += joins; row.leaves += leaves
                else:
                    s.add(InviteStat(guild_id=guild_id, user_id=user_id, joins=joins, leaves=leaves))
                await s.commit()
            return
        key = self._buffer_key(guild_id)
        if joins: await self.cache.hincrby(key, str(user_id), joins)
        if leaves: await self.cache.hincrby(key, f'{user_id}:leaves', leaves)
        await self.cache.expire(key, 300)

    async def identify_join(self, member: discord.Member) -> tuple[int | None, int]:
        guild = member.guild
        before = await self._cached_snapshot(guild.id)
        if not before:
            await self.refresh_guild(guild)
            before = await self._cached_snapshot(guild.id)

        # Serialize refreshes across pods. If another worker owns the lock,
        # use the last snapshot rather than making a second HTTP request.
        after = None
        if self.cache is not None:
            key = self._snapshot_key(guild.id)
            token = uuid.uuid4().hex
            if await self.cache.acquire_lock(f'{key}:join-lock', token, 8000):
                try:
                    after = await self._fetch_guild(guild)
                    if after is not None:
                        async with self._lock:
                            self._snapshots[guild.id] = after
                        await self.cache.set_json(key, self._encode(after), self.SNAPSHOT_TTL)
                finally:
                    await self.cache.release_lock(f'{key}:join-lock', token)
        else:
            after = await self._fetch_guild(guild)

        if after is None:
            after = before

        candidates = [v for code, v in after.items() if v.uses > before.get(code, InviteSnapshot(code, 0, None, 0, False)).uses]
        inviter_id = candidates[0].inviter_id if len(candidates) == 1 else None
        invite_uses = candidates[0].uses if len(candidates) == 1 else 0
        if inviter_id:
            await self._buffer_delta(guild.id, inviter_id, joins=1)
            if self.cache is not None:
                await self.cache.set_json(self._member_key(guild.id, member.id), {
                    'inviter_id': inviter_id, 'invite_code': candidates[0].code, 'joined_at': __import__('time').time()
                }, self.ATTRIBUTION_TTL)
            try:
                self._attr_queue.put_nowait((guild.id, member.id, inviter_id, candidates[0].code, 'join'))
            except asyncio.QueueFull:
                log.warning('invite attribution queue full guild=%s member=%s', guild.id, member.id)
        return inviter_id, invite_uses

    async def submit_join(self, member: discord.Member, suppress_greeting: bool = False):
        """Schedule attribution without blocking the gateway join path."""
        await self._ensure_workers()
        try:
            self._join_queue.put_nowait((member, suppress_greeting))
            return True
        except asyncio.QueueFull:
            log.warning('invite join queue full guild=%s member=%s', member.guild.id, member.id)
            # The welcome can still be skipped safely; attribution is best effort.
            return False

    async def _ensure_workers(self):
        if self._join_queue is None:
            self._join_queue = asyncio.Queue(maxsize=self.join_queue_size)
            self._join_task = asyncio.create_task(self._join_loop(), name='invite-attribution-worker')
        if self.cache is not None and self._flush_task is None:
            await self.start()

    async def _join_loop(self):
        while not self._closing:
            member, suppress_greeting = await self._join_queue.get()
            greeting_queued = suppress_greeting
            try:
                inviter_id, invite_uses = await self.identify_join(member)
                if not suppress_greeting:
                    greeting_queued = await self.bot.greeting_worker.submit(
                        member,
                        'welcome',
                        invite_id=inviter_id,
                        invite_uses=invite_uses,
                    )
                    if not greeting_queued:
                        log.warning(
                            'welcome greeting queue full guild=%s member=%s',
                            member.guild.id, member.id,
                        )
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception(
                    'invite attribution failed guild=%s member=%s',
                    member.guild.id, member.id,
                )
            finally:
                # Attribution is best-effort; the greeting must not disappear
                # just because Discord's invite API or Redis temporarily failed.
                if not suppress_greeting and not greeting_queued:
                    try:
                        fallback = await self.bot.greeting_worker.submit(member, 'welcome')
                        if not fallback:
                            log.warning(
                                'welcome fallback queue full guild=%s member=%s',
                                member.guild.id, member.id,
                            )
                    except Exception:
                        log.exception(
                            'welcome fallback failed guild=%s member=%s',
                            member.guild.id, member.id,
                        )
                self._join_queue.task_done()

    async def record_leave(self, member: discord.Member) -> None:
        data = await self.cache.get_json(self._member_key(member.guild.id, member.id)) if self.cache is not None else None
        if data is None and self.cache is None:
            async with self.db.session() as s:
                row = (await s.execute(text('SELECT inviter_id, invite_code FROM member_invite_attribution WHERE guild_id=:g AND member_id=:m AND left_at IS NULL'), {'g':member.guild.id,'m':member.id})).mappings().first()
                data = dict(row) if row else None
        if not data:
            return
        inviter_id = data.get('inviter_id')
        if inviter_id:
            await self._buffer_delta(member.guild.id, int(inviter_id), leaves=1)
            try:
                self._attr_queue.put_nowait((member.guild.id, member.id, int(inviter_id), data.get('invite_code'), 'leave'))
            except asyncio.QueueFull:
                log.warning('invite attribution queue full on leave guild=%s member=%s', member.guild.id, member.id)
        if self.cache is not None:
            await self.cache.delete(self._member_key(member.guild.id, member.id))

    async def stats(self, guild_id: int, user_id: int | None = None):
        await self._flush_guild(guild_id)
        async with self.db.session() as s:
            q = select(InviteStat).where(InviteStat.guild_id == guild_id)
            if user_id is not None: q = q.where(InviteStat.user_id == user_id)
            q = q.order_by(InviteStat.joins.desc())
            return list((await s.execute(q)).scalars())

    async def _flush_loop(self):
        while not self._closing:
            await asyncio.sleep(self.flush_interval)
            try: await self._flush_once()
            except asyncio.CancelledError: raise
            except Exception: log.exception('invite stat flush failed')

    async def _flush_once(self):
        if self.cache is None: return
        async for key in self.cache.scan_iter('invite-buffer:*'):
            token = uuid.uuid4().hex
            if not await self.cache.acquire_lock(f'{key}:flush-lock', token, 10000): continue
            flush_key = f'{key}:processing:{token}'
            raw = {}
            try:
                if not await self.cache.rename_if_exists(key, flush_key): continue
                raw = await self.cache.hgetall(flush_key)
                await self.cache.delete(flush_key)
                if not raw: continue
                guild_id = int(key.rsplit(':', 1)[1])
                rows = []
                for field, value in raw.items():
                    if field.endswith(':leaves'): continue
                    user_id = int(field); leaves = int(raw.get(f'{field}:leaves', 0))
                    rows.append((guild_id, user_id, int(value), leaves))
                async with self.db.session() as s:
                    for gid, uid, joins, leaves in rows:
                        await s.execute(text('''INSERT INTO invite_stats (guild_id,user_id,joins,leaves) VALUES (:g,:u,:j,:l) ON CONFLICT (guild_id,user_id) DO UPDATE SET joins=invite_stats.joins + EXCLUDED.joins, leaves=invite_stats.leaves + EXCLUDED.leaves'''), {'g':gid,'u':uid,'j':joins,'l':leaves})
                    await s.commit()
            except Exception:
                log.exception('failed flushing invite buffer key=%s; restoring buffer', key)
                if 'raw' in locals() and raw:
                    for field, value in raw.items(): await self.cache.hincrby(key, field, int(value))
            finally:
                await self.cache.release_lock(f'{key}:flush-lock', token)

    async def _flush_guild(self, guild_id: int):
        if self.cache is None: return
        await self._flush_once()

    async def _attribution_loop(self):
        while not self._closing:
            try:
                await asyncio.sleep(0.5)
                await self._flush_attribution_batch()
            except asyncio.CancelledError: raise
            except Exception: log.exception('invite attribution persistence failed')

    async def _flush_attribution_batch(self):
        if not hasattr(self, '_attr_queue') or self._attr_queue.empty(): return
        rows=[]
        while len(rows) < self.ATTR_BATCH_SIZE:
            try: rows.append(self._attr_queue.get_nowait())
            except asyncio.QueueEmpty: break
        if not rows: return
        try:
            async with self.db.session() as s:
                for guild_id, member_id, inviter_id, invite_code, action in rows:
                    if action == 'join':
                        await s.execute(text('''INSERT INTO member_invite_attribution (guild_id,member_id,inviter_id,invite_code,joined_at,left_at) VALUES (:g,:m,:i,:c,now(),NULL) ON CONFLICT (guild_id,member_id) DO UPDATE SET inviter_id=EXCLUDED.inviter_id, invite_code=EXCLUDED.invite_code, joined_at=EXCLUDED.joined_at, left_at=NULL'''), {'g':guild_id,'m':member_id,'i':inviter_id,'c':invite_code})
                    else:
                        await s.execute(text('''UPDATE member_invite_attribution SET left_at=now() WHERE guild_id=:g AND member_id=:m'''), {'g':guild_id,'m':member_id})
                await s.commit()
        except Exception:
            # The rows were removed from the asyncio queue but not acknowledged.
            # Requeue them so a transient DB outage does not silently lose attribution.
            for row in rows:
                try:
                    self._attr_queue.put_nowait(row)
                except asyncio.QueueFull:
                    log.error('invite attribution retry queue full; dropping row guild=%s member=%s', row[0], row[1])
                else:
                    self._attr_queue.task_done()
            raise
        else:
            for _ in rows: self._attr_queue.task_done()
