import time

class DistributedRateLimiter:
    def __init__(self, redis):
        self.redis = redis

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = int(time.time())
        bucket = f"rl:{key}:{now // window_seconds}"
        count = await self.redis.client.incr(bucket)
        if count == 1:
            await self.redis.client.expire(bucket, window_seconds + 2)
        return count <= limit
