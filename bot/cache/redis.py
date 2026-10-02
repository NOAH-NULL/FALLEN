import json
from redis.asyncio import Redis
from bot.core.fencing import current_fence
from bot.core.metrics import CACHE


class RedisCache:
    def __init__(self, url: str, max_connections: int = 200):
        self.client = Redis.from_url(
            url, max_connections=max_connections, decode_responses=True,
            health_check_interval=30, socket_connect_timeout=3,
            socket_timeout=3, retry_on_timeout=True,
        )

    async def get_json(self, key):
        value = await self.client.get(key)
        CACHE.labels('get', 'hit' if value else 'miss').inc()
        return json.loads(value) if value else None

    async def set_json_flight_fenced(self, key, value, lock_key, token, fence, ttl=300):
        """Write cache state only while this distributed single-flight epoch owns the lock."""
        encoded = json.dumps(value, separators=(',', ':'))
        expected = f'{token}:{fence}'
        script = """
        if redis.call('get', KEYS[1]) ~= ARGV[1] then return 0 end
        redis.call('set', KEYS[2], ARGV[2], 'EX', ARGV[3])
        return 1
        """
        ok = await self.client.eval(script, 2, lock_key, key, expected, encoded, ttl)
        if not ok:
            raise RuntimeError('stale distributed single-flight epoch rejected')
        CACHE.labels('set', 'flight_fenced').inc()

    async def set_json(self, key, value, ttl=300):
        fence = current_fence()
        encoded = json.dumps(value, separators=(',', ':'))
        if fence is None:
            await self.client.set(key, encoded, ex=ttl)
        else:
            # The lease check and write are one Redis-side operation. A stale
            # gateway worker therefore cannot repopulate cache state after its
            # fencing epoch has been superseded.
            script = """
            if redis.call('get', KEYS[1]) ~= ARGV[1] then return 0 end
            redis.call('set', KEYS[2], ARGV[2], 'EX', ARGV[3])
            return 1
            """
            lease_key = f'shard-lease:{fence.shard_id}'
            lease_value = f'{fence.token}:{fence.fence}'
            ok = await self.client.eval(script, 2, lease_key, key, lease_value, encoded, ttl)
            if not ok:
                raise RuntimeError(f'stale shard fence for cache write shard={fence.shard_id}')
        CACHE.labels('set', 'ok').inc()

    async def delete(self, key):
        await self.client.delete(key); CACHE.labels('delete', 'ok').inc()
    async def hincrby(self, key, field, amount=1): return await self.client.hincrby(key, field, amount)
    async def hgetall(self, key): return await self.client.hgetall(key)
    def scan_iter(self, match): return self.client.scan_iter(match=match)
    async def rename_if_exists(self, source, dest):
        script = "if redis.call('exists',KEYS[1]) == 1 then redis.call('rename',KEYS[1],KEYS[2]); return 1 else return 0 end"
        return bool(await self.client.eval(script, 2, source, dest))
    async def publish(self, channel, payload):
        return await self.client.publish(channel, json.dumps(payload, separators=(',', ':')))
    def pubsub(self): return self.client.pubsub()
    async def incr(self, key): return await self.client.incr(key)
    async def expire(self, key, seconds): return await self.client.expire(key, seconds)
    async def acquire_lock(self, key, token, ttl_ms):
        return bool(await self.client.set(key, token, nx=True, px=ttl_ms))
    async def release_lock(self, key, token):
        script = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end"
        return bool(await self.client.eval(script, 1, key, token))
    async def renew_lock(self, key, token, ttl_ms):
        script = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('pexpire',KEYS[1],ARGV[2]) else return 0 end"
        return bool(await self.client.eval(script, 1, key, token, ttl_ms))

    async def acquire_fenced_lock(self, key, token, fence_key, ttl_ms):
        """Atomically claim a lease and advance its monotonically increasing fence."""
        script = """
        if redis.call('exists', KEYS[1]) == 1 then return 0 end
        local fence = redis.call('incr', KEYS[2])
        redis.call('set', KEYS[1], ARGV[1] .. ':' .. fence, 'PX', ARGV[2])
        return fence
        """
        return int(await self.client.eval(script, 2, key, fence_key, token, ttl_ms))

    async def renew_fenced_lock(self, key, token, fence, ttl_ms):
        value = f'{token}:{fence}'
        script = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('pexpire',KEYS[1],ARGV[2]) else return 0 end"
        return bool(await self.client.eval(script, 1, key, value, ttl_ms))

    async def release_fenced_lock(self, key, token, fence):
        value = f'{token}:{fence}'
        script = "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end"
        return bool(await self.client.eval(script, 1, key, value))

    async def fenced_lock_is_current(self, key, token, fence):
        return (await self.client.get(key)) == f'{token}:{fence}'

    async def xadd(self, stream, payload, maxlen=10000):
        return await self.client.xadd(stream, payload, maxlen=maxlen, approximate=True)
    async def anti_raid_size(self, guild_id, window_seconds):
        key=f'anti-raid:{guild_id}'
        cutoff=__import__('time').time()-window_seconds
        await self.client.zremrangebyscore(key, 0, cutoff)
        return int(await self.client.zcard(key))
    async def anti_raid_count(self, guild_id, window_seconds, limit):
        key=f'anti-raid:{guild_id}'
        now=__import__('time').time()
        member=f'{now}:{__import__("uuid").uuid4().hex}'
        script = "local k=KEYS[1]; local now=tonumber(ARGV[1]); local cutoff=now-tonumber(ARGV[2]); redis.call('ZREMRANGEBYSCORE',k,0,cutoff); redis.call('ZADD',k,now,ARGV[3]); redis.call('EXPIRE',k,tonumber(ARGV[2])+2); return redis.call('ZCARD',k)"
        count=await self.client.eval(script,1,key,now,window_seconds,member)
        return int(count)>=limit
    async def health(self): return bool(await self.client.ping())
    async def close(self): await self.client.aclose()
