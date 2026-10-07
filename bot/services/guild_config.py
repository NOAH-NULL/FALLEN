import base64
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from bot.models import GuildConfig
from bot.cache.keys import guild as guild_key
from bot.cache.singleflight import DistributedSingleFlight

class GuildConfigService:
    def __init__(self, db, cache, ttl=600, lock_ttl_ms=30000):
        self.db, self.cache, self.ttl = db, cache, ttl
        self.singleflight = DistributedSingleFlight(cache, lock_ttl_ms)

    def _default(self, gid):
        return {'guild_id':gid,'welcome_channel_id':None,'goodbye_channel_id':None,'log_channel_id':None,'autorole_id':None,'welcome_message':'Welcome {mention} to {server}! You are member #{count}.','goodbye_message':'Goodbye {name}!','welcome_background':'assets/welcome.gif','goodbye_background':'assets/goodbye.gif','welcome_background_data':None,'goodbye_background_data':None,'welcome_embed_enabled':True,'goodbye_embed_enabled':True,'welcome_embed_title':'Welcome!','goodbye_embed_title':'Goodbye!','welcome_embed_description':'{mention} just joined {server}! 🎉','goodbye_embed_description':'{name} has left {server}. 👋','welcome_embed_color':5793266,'goodbye_embed_color':9807270,'welcome_dm_enabled':False,'welcome_dm_message':'Welcome to {server}, {name}! We are glad to have you here.','welcome_button_enabled':False,'welcome_button_label':'Read the Rules','welcome_button_url':None,'welcome_show_details':True,'welcome_settings':{},'automod_enabled':False,'spam_limit':6,'spam_window':8,'extreme_settings':{}}

    @staticmethod
    def _cache_safe(config):
        for name in ('welcome_background_data', 'goodbye_background_data'):
            value = config.get(name)
            if isinstance(value, (bytes, bytearray, memoryview)):
                config[name] = 'base64:' + base64.b64encode(value).decode('ascii')
        for name, value in config.items():
            if isinstance(value, (date, datetime)):
                config[name] = value.isoformat()
        return config

    async def update(self, gid, **values):
        columns = GuildConfig.__table__.columns
        if not values or 'guild_id' in values or any(name not in columns for name in values):
            raise ValueError('Provide valid guild configuration fields to update.')

        insert_values = self._default(gid)
        insert_values.update(values)
        statement = pg_insert(GuildConfig).values(**insert_values)
        statement = statement.on_conflict_do_update(
            index_elements=[GuildConfig.guild_id],
            set_={name: statement.excluded[name] for name in values},
        )
        async with self.db.session() as session:
            await session.execute(statement)
            await session.commit()
        await self.invalidate(gid)

    async def get(self, gid):
        key = guild_key(gid)
        async def read():
            return await self.cache.get_json(key)
        async def load():
            async with self.db.session() as s:
                result = await s.execute(select(*GuildConfig.__table__.c).where(GuildConfig.guild_id == gid))
                row = result.mappings().first()
                return self._cache_safe(dict(row) if row else self._default(gid))
        return await self.singleflight.run(key, load, read)

    async def invalidate(self, gid):
        key = guild_key(gid)
        await self.cache.delete(key)
        # Pub/Sub is only a latency optimization; the cache TTL remains the
        # correctness fallback if a subscriber is disconnected.
        await self.cache.publish('guild-config-invalidated', {'guild_id': gid})
