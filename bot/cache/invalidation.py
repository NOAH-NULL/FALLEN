import asyncio, json
from bot.cache.keys import guild as guild_key
class CacheInvalidationSubscriber:
    def __init__(self, cache): self.cache, self.task = cache, None
    async def start(self): self.task = asyncio.create_task(self._run(), name='redis-invalidation-subscriber')
    async def _run(self):
        while True:
            try:
                async with self.cache.pubsub() as ps:
                    await ps.subscribe('guild-config-invalidated')
                    async for msg in ps.listen():
                        if msg.get('type') == 'message':
                            data = json.loads(msg['data'])
                            await self.cache.delete(guild_key(int(data['guild_id'])))
            except asyncio.CancelledError: raise
            except Exception: await asyncio.sleep(1)
    async def close(self):
        if self.task:
            self.task.cancel(); await asyncio.gather(self.task, return_exceptions=True)
