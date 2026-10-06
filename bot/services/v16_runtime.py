from __future__ import annotations
import re, time
from collections import defaultdict, deque
from urllib.parse import urlparse


class V16Runtime:
    """Fast, in-memory decision engine backed by ExtremeService persistence."""

    def __init__(self, bot):
        self.bot = bot
        self.messages = defaultdict(deque)
        self.content = defaultdict(deque)
        self.joins = defaultdict(deque)
        self._last_prune = 0.0

    def _trim(self, q, now, window):
        while q and now - q[0][0] > window:
            q.popleft()

    def _prune(self, now):
        # Runtime keys are user/guild-cardinality driven. Remove inactive keys
        # periodically so a long-lived bot does not retain every historical user.
        if now - self._last_prune < 60:
            return
        self._last_prune = now
        for store, window in (
            (self.messages, 8),
            (self.content, 12),
            (self.joins, 15),
        ):
            stale = [
                key for key, q in store.items()
                if not q or now - q[-1][0] > window
            ]
            for key in stale:
                store.pop(key, None)

    async def member_join(self, member):
        gid = member.guild.id
        now = time.monotonic()
        self._prune(now)
        q = self.joins[gid]
        q.append((now, member.id))
        self._trim(q, now, 15)

        settings = await self.bot.extreme.get(gid)
        suspicious = bool(re.search(r'[^\w\s.-]{3,}', member.display_name)) or len(member.display_name) > 50
        actions = []

        if settings.get('security_timeline'):
            # discord.py timestamps are timezone-aware. Calculate age from
            # the current UTC time rather than the bot's join timestamp.
            from discord.utils import utcnow
            account_age_days = max(0.0, (utcnow() - member.created_at).total_seconds() / 86400)
            await self.bot.extreme.record_security(
                gid,
                'member_join',
                target_id=member.id,
                details={'account_age_days': round(account_age_days, 2), 'suspicious_name': suspicious},
            )

        if settings.get('anti_bot_join') and member.bot:
            actions.append('bot_join')
        if settings.get('account_age_verification'):
            from discord.utils import utcnow
            age = (utcnow() - member.created_at).total_seconds() / 86400
            if age < 7:
                actions.append('new_account')
        if settings.get('suspicious_username') and suspicious:
            actions.append('suspicious_name')
        if settings.get('raid_join_rate') and len(q) >= 8:
            actions.append('raid')
        if actions and settings.get('automatic_lockdown'):
            await self.bot.security_lockdown(gid, reason='V16 automatic lockdown: ' + ','.join(actions))
        return actions

    async def message_check(self, message):
        gid = message.guild.id
        uid = message.author.id
        now = time.monotonic()
        self._prune(now)
        key = (gid, uid)

        q = self.messages[key]
        q.append((now, message.id))
        self._trim(q, now, 8)

        cq = self.content[key]
        cq.append((now, message.content))
        self._trim(cq, now, 12)

        settings = await self.bot.extreme.get(gid)
        rules = await self.bot.extreme.automod_rules(gid)
        reasons = []
        content = message.content or ""
        # Bound regex work so a malicious rule cannot monopolize a worker.
        regex_rules = [r for r in rules if r.enabled and r.kind == 'regex']

        if settings.get('flood_detection') and len(q) > 6:
            reasons.append('flood')
        if settings.get('duplicate_messages') and len(content) > 3:
            if sum(1 for _, c in cq if c == content) >= 3:
                reasons.append('duplicate')
        if settings.get('emoji_spam') and len(re.findall(r'<a?:\w+:\d+>|[\U0001F300-\U0001FAFF]', content)) >= 12:
            reasons.append('emoji_spam')
        if settings.get('mention_spam') and len(message.mentions) + len(message.role_mentions) >= 8:
            reasons.append('mention_spam')

        urls = re.findall(r'https?://[^\s>]+', content)
        if urls and (settings.get('domain_blacklist') or settings.get('domain_whitelist')):
            blocked = {r.pattern.lower() for r in rules if r.enabled and r.kind == 'domain_blacklist'}
            allowed = {r.pattern.lower() for r in rules if r.enabled and r.kind == 'domain_whitelist'}
            for raw in urls:
                host = (urlparse(raw).hostname or '').lower()
                if host and any(host == d or host.endswith('.' + d) for d in blocked):
                    reasons.append('domain_blacklist')
                if allowed and not any(host == d or host.endswith('.' + d) for d in allowed):
                    reasons.append('domain_whitelist')

        if settings.get('regex_rules'):
            for rule in regex_rules[:50]:
                try:
                    if re.search(rule.pattern, content, re.I):
                        reasons.append('regex:' + rule.name)
                except re.error:
                    # A malformed rule must not break message processing.
                    continue

        return list(dict.fromkeys(reasons))
