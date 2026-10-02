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

    def _trim(self,q,now,window):
        while q and now-q[0][0] > window: q.popleft()

    async def member_join(self, member):
        gid=member.guild.id; now=time.monotonic(); q=self.joins[gid]; q.append((now,member.id)); self._trim(q,now,15)
        suspicious = bool(re.search(r'[^\w\s.-]{3,}', member.display_name)) or len(member.display_name)>50
        if await self.bot.extreme.enabled(gid,'security_timeline'):
            await self.bot.extreme.record_security(gid,'member_join',target_id=member.id,details={'account_age_days':(member.created_at-member.created_at).days if False else 0,'suspicious_name':suspicious})
        actions=[]
        if await self.bot.extreme.enabled(gid,'anti_bot_join') and member.bot: actions.append('bot_join')
        if await self.bot.extreme.enabled(gid,'account_age_verification'):
            age=(member.guild.me.joined_at-member.created_at).total_seconds()/86400 if member.guild.me and member.guild.me.joined_at else 999
            # The bot's join date is not the member's age; use UTC now below.
            from discord.utils import utcnow
            age=(utcnow()-member.created_at).total_seconds()/86400
            if age < 7: actions.append('new_account')
        if await self.bot.extreme.enabled(gid,'suspicious_username') and suspicious: actions.append('suspicious_name')
        if await self.bot.extreme.enabled(gid,'raid_join_rate') and len(q)>=8: actions.append('raid')
        if actions and await self.bot.extreme.enabled(gid,'automatic_lockdown'):
            await self.bot.security_lockdown(gid, reason='V16 automatic lockdown: '+','.join(actions))
        return actions

    async def message_check(self,message):
        gid=message.guild.id; uid=message.author.id; now=time.monotonic(); key=(gid,uid)
        q=self.messages[key]; q.append((now,message.id)); self._trim(q,now,8)
        cq=self.content[key]; cq.append((now,message.content)); self._trim(cq,now,12)
        reasons=[]
        if await self.bot.extreme.enabled(gid,'flood_detection') and len(q)>6: reasons.append('flood')
        if await self.bot.extreme.enabled(gid,'duplicate_messages') and len(message.content)>3 and sum(1 for _,c in cq if c==message.content)>=3: reasons.append('duplicate')
        if await self.bot.extreme.enabled(gid,'emoji_spam') and len(re.findall(r'<a?:\w+:\d+>|[\U0001F300-\U0001FAFF]',message.content))>=12: reasons.append('emoji_spam')
        if await self.bot.extreme.enabled(gid,'mention_spam') and len(message.mentions)+len(message.role_mentions)>=8: reasons.append('mention_spam')
        if await self.bot.extreme.enabled(gid,'domain_blacklist') or await self.bot.extreme.enabled(gid,'domain_whitelist'):
            urls=re.findall(r'https?://[^\s>]+',message.content)
            if urls:
                rules=await self.bot.extreme.automod_rules(gid)
                blocked=set(); allowed=set()
                for r in rules:
                    if not r.enabled: continue
                    if r.kind=='domain_blacklist': blocked.add(r.pattern.lower())
                    if r.kind=='domain_whitelist': allowed.add(r.pattern.lower())
                for raw in urls:
                    host=urlparse(raw).hostname or ''
                    if host and any(host==d or host.endswith('.'+d) for d in blocked): reasons.append('domain_blacklist')
                    if allowed and not any(host==d or host.endswith('.'+d) for d in allowed): reasons.append('domain_whitelist')
        for rule in await self.bot.extreme.automod_rules(gid):
            if not rule.enabled: continue
            if rule.kind=='regex':
                try:
                    if re.search(rule.pattern,message.content,re.I): reasons.append('regex:'+rule.name)
                except re.error: pass
        return list(dict.fromkeys(reasons))
