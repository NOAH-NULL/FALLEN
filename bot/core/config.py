from dataclasses import dataclass
import os, uuid
from dotenv import load_dotenv
load_dotenv()

def _i(k,d):
    try:return int(os.getenv(k,str(d)))
    except ValueError:return d

def _b(k,d=False): return os.getenv(k,str(d)).lower() in {'1','true','yes','on'}

@dataclass(frozen=True)
class Settings:
    log_level: str=os.getenv('LOG_LEVEL','INFO')
    environment: str=os.getenv('ENVIRONMENT','development')
    otel_enabled: bool=_b('OTEL_ENABLED',False)
    otel_exporter_endpoint: str=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT','')
    otel_service_name: str=os.getenv('OTEL_SERVICE_NAME','titan-discord-bot')
    token:str=os.getenv('DISCORD_TOKEN','')
    guild_id:int|None=_i('GUILD_ID',0) or None
    command_prefix:str=os.getenv('COMMAND_PREFIX',',')
    database_url:str=os.getenv('DATABASE_URL','postgresql+asyncpg://bot:bot@localhost:5432/discordbot')
    redis_url:str=os.getenv('REDIS_URL','redis://localhost:6379/0')
    redis_max_connections:int=_i('REDIS_MAX_CONNECTIONS',100)
    cache_ttl_seconds:int=_i('CACHE_TTL_SECONDS',600)
    redis_lock_ttl_ms:int=_i('REDIS_LOCK_TTL_MS',5000)
    db_pool_size:int=_i('DB_POOL_SIZE',5)
    db_max_overflow:int=_i('DB_MAX_OVERFLOW',5)
    db_use_pgbouncer:bool=_b('DB_USE_PGBOUNCER',False)
    db_pool_timeout:float=float(os.getenv('DB_POOL_TIMEOUT','10'))
    db_pool_recycle:int=_i('DB_POOL_RECYCLE',1800)
    db_statement_timeout_ms:int=_i('DB_STATEMENT_TIMEOUT_MS',5000)
    metrics_host:str=os.getenv('METRICS_HOST','0.0.0.0')
    metrics_port:int=_i('METRICS_PORT',9100)
    health_port:int=_i('HEALTH_PORT',8080)
    dashboard_host:str=os.getenv('DASHBOARD_HOST','0.0.0.0')
    dashboard_port:int=_i('DASHBOARD_PORT',8081)
    greeting_queue_size:int=_i('GREETING_QUEUE_SIZE',1000)
    greeting_workers:int=_i('GREETING_WORKERS',4)
    greeting_max_event_age:float=float(os.getenv('GREETING_MAX_EVENT_AGE','30'))
    invite_join_queue_size:int=_i('INVITE_JOIN_QUEUE_SIZE',2000)
    invite_stat_flush_interval:float=float(os.getenv('INVITE_STAT_FLUSH_INTERVAL','1.0'))
    shard_count:int|None=_i('SHARD_COUNT',0) or None
    shard_ids:str=os.getenv('SHARD_IDS','')
    gateway_queue_size:int=_i('GATEWAY_QUEUE_SIZE',4096)
    gateway_critical_queue_size:int=_i('GATEWAY_CRITICAL_QUEUE_SIZE',1024)
    gateway_workers:int=_i('GATEWAY_WORKERS',8)
    gateway_guild_concurrency:int=_i('GATEWAY_GUILD_CONCURRENCY',1)
    gateway_max_event_age:float=float(os.getenv('GATEWAY_MAX_EVENT_AGE','10'))
    shard_lease_ttl_ms:int=_i('SHARD_LEASE_TTL_MS',60000)
    gateway_shutdown_timeout:float=float(os.getenv('GATEWAY_SHUTDOWN_TIMEOUT','15'))
    gateway_dlq_maxsize:int=_i('GATEWAY_DLQ_MAXSIZE',2048)
    instance_id:str=os.getenv('INSTANCE_ID',os.getenv('HOSTNAME',str(uuid.uuid4())))
    public_base_url:str=os.getenv('PUBLIC_BASE_URL','http://localhost:8080')
    dashboard_api_key:str=os.getenv('DASHBOARD_API_KEY','')
    automod_heat_decay:float=float(os.getenv('AUTOMOD_HEAT_DECAY','0.08'))
    automod_heat_ttl:int=_i('AUTOMOD_HEAT_TTL',900)
    music_url:str=os.getenv('LAVALINK_URL','')
    music_password:str=os.getenv('LAVALINK_PASSWORD','')
    @property
    def parsed_shard_ids(self):
        if not self.shard_ids:return None
        return [int(x.strip()) for x in self.shard_ids.split(',') if x.strip()]

settings=Settings()
