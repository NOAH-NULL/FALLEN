import math
import re
import time
import collections

URL_RE = re.compile(r'(https?://|www\.)', re.I)
INVITE_RE = re.compile(r'(discord(?:\.gg|(?:app)?\.com/invite)/|bit\.ly/|tinyurl\.com/)', re.I)

HEAT_WEIGHTS = {
    'spam': 10.0,
    'link': 25.0,
    'mention_spam': 40.0,
    'invite_phishing': 60.0,
}

class AutoModService:
    """Redis-backed decaying multi-factor heat engine.

    The local deque remains as a cheap fallback for deployments without Redis.
    The Redis Lua path is atomic, cross-process and uses server time so pods do
    not disagree about elapsed decay time.
    """
    HEAT_SCRIPT = """
    local key = KEYS[1]
    local clock = redis.call('TIME')
    local now = tonumber(clock[1]) + (tonumber(clock[2]) / 1000000)
    local lambda = tonumber(ARGV[1])
    local weight = tonumber(ARGV[2])
    local ttl = tonumber(ARGV[3])
    local data = redis.call('HMGET', key, 'score', 'last_update')
    local score = tonumber(data[1]) or 0.0
    local last = tonumber(data[2]) or now
    local delta = math.max(0, now - last)
    score = score * math.exp(-lambda * delta) + weight
    redis.call('HSET', key, 'score', score, 'last_update', now)
    redis.call('EXPIRE', key, ttl)
    return score
    """

    def __init__(self, cache=None, decay_lambda=0.08, ttl=900):
        self.cache = cache
        self.decay_lambda = max(0.000001, float(decay_lambda))
        self.ttl = max(30, int(ttl))
        self._events = collections.defaultdict(collections.deque)
        self._heat_events = collections.defaultdict(collections.deque)
        self._local_configs = {}

    @staticmethod
    def classify(content, mention_count=0, attachment_count=0):
        text = content or ''
        factors = []
        if URL_RE.search(text) or attachment_count:
            factors.append('link')
        if INVITE_RE.search(text):
            factors.append('invite_phishing')
        if mention_count >= 5:
            factors.append('mention_spam')
        return factors

    async def add_heat(self, guild_id, user_id, weight, factor='unknown'):
        config = await self.get_heat_config(guild_id)
        if self.cache is not None:
            result = await self.cache.client.eval(
                self.HEAT_SCRIPT, 1, f'heat:{guild_id}:{user_id}',
                config['decay'], float(weight), config['ttl']
            )
            return float(result)

        now = time.monotonic()
        key = (guild_id, user_id)
        q = self._heat_events[key]
        while q and now - q[0][0] > config['ttl']:
            q.popleft()
        q.append((now, float(weight)))
        return sum(
            event_weight * math.exp(-config['decay'] * max(0.0, now - timestamp))
            for timestamp, event_weight in q
        )

    async def get_heat_config(self, guild_id):
        defaults = {'decay': self.decay_lambda, 'ttl': self.ttl, **HEAT_WEIGHTS}
        if self.cache is None:
            defaults.update(self._local_configs.get(guild_id, {}))
            return defaults
        raw = await self.cache.hgetall(f'heat-config:{guild_id}')
        for key in defaults:
            if key in raw:
                try: defaults[key] = float(raw[key]) if key != 'ttl' else int(raw[key])
                except (TypeError, ValueError): pass
        defaults['decay'] = max(0.000001, float(defaults['decay']))
        defaults['ttl'] = max(30, int(defaults['ttl']))
        return defaults

    async def configure_heat(self, guild_id, **changes):
        allowed = {'decay','ttl','spam','link','mention_spam','invite_phishing'}
        clean = {k: v for k, v in changes.items() if k in allowed and v is not None}
        if 'decay' in clean: clean['decay'] = max(0.000001, float(clean['decay']))
        if 'ttl' in clean: clean['ttl'] = max(30, int(clean['ttl']))
        for k in ('spam','link','mention_spam','invite_phishing'):
            if k in clean: clean[k] = max(0.0, float(clean[k]))
        if self.cache is not None and clean:
            await self.cache.client.hset(f'heat-config:{guild_id}', mapping={k: str(v) for k,v in clean.items()})
            await self.cache.expire(f'heat-config:{guild_id}', 86400 * 30)
        if 'decay' in clean: self.decay_lambda = float(clean['decay'])
        if 'ttl' in clean: self.ttl = int(clean['ttl'])
        HEAT_WEIGHTS.update({k: float(v) for k,v in clean.items() if k in HEAT_WEIGHTS})
        return await self.get_heat_config(guild_id)

    async def observe(self, guild_id, user_id, content, mention_count=0, attachment_count=0, spam=False):
        config = await self.get_heat_config(guild_id)
        factors = self.classify(content, mention_count, attachment_count)
        if spam:
            factors.append('spam')
        if not factors:
            return {'score': 0.0, 'factors': [], 'action': None}
        score = 0.0
        applied = []
        # Apply each factor atomically; one event can legitimately contribute
        # to multiple independent risk dimensions.
        for factor in factors:
            weight = float(config.get(factor, HEAT_WEIGHTS[factor]))
            if self.cache is not None:
                result = await self.cache.client.eval(self.HEAT_SCRIPT, 1, f'heat:{guild_id}:{user_id}', config['decay'], weight, config['ttl'])
                score = float(result)
            else:
                score = await self.add_heat(guild_id, user_id, weight, factor)
            applied.append(factor)
        if score >= 100:
            action = 'quarantine'
        elif score >= 80:
            action = 'timeout'
        elif score >= 50:
            action = 'purge_shadow_mute'
        else:
            action = None
        return {'score': score, 'factors': applied, 'action': action}

    async def get_heat(self, guild_id, user_id):
        if self.cache is None:
            return 0.0
        data = await self.cache.hgetall(f'heat:{guild_id}:{user_id}')
        if not data:
            return 0.0
        config = await self.get_heat_config(guild_id)
        clock = await self.cache.client.time()
        now = float(clock[0]) + float(clock[1]) / 1000000.0
        score = float(data.get('score', 0.0))
        last = float(data.get('last_update', now))
        return score * math.exp(-config['decay'] * max(0.0, now - last))

    def check(self, gid, uid, content, limit=6, window=8):
        now = time.monotonic(); q = self._events[(gid, uid)]
        while q and now-q[0] > window: q.popleft()
        q.append(now)
        return len(q) > limit or (len(content or '') > 12 and len(set((content or '').lower().split())) <= 2)
