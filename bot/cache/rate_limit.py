class DistributedRateLimiter:
    LUA = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return count
    """

    def __init__(self, redis):
        self.redis = redis

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        if limit <= 0:
            return False
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        # Keep a stable key and let Redis expire it from the first hit. Fixed
        # wall-clock buckets allow bursts immediately before and after a boundary.
        bucket = f"rl:{key}"
        count = await self.redis.client.eval(self.LUA, 1, bucket, window_seconds + 2)
        return int(count) <= limit
