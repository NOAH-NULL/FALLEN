from prometheus_client import Counter, Gauge, Histogram, start_http_server

COMMANDS = Counter("discord_commands_total", "Commands executed", ["command", "status"])
COMMAND_LATENCY = Histogram("discord_command_duration_seconds", "Command latency", ["command"])
DB_LATENCY = Histogram("discord_db_duration_seconds", "Database operation latency", ["operation"])
CACHE = Counter("discord_cache_total", "Cache operations", ["operation", "result"])
EVENTS = Counter("discord_events_total", "Discord events", ["event"])
GUILDS = Gauge("discord_guilds", "Connected guild count")
GATEWAY_LATENCY = Gauge("discord_gateway_latency_seconds", "Gateway latency")
WORK_QUEUE = Gauge("discord_work_queue_depth", "Bounded worker queue depth", ["queue"])


def start_metrics(host: str, port: int) -> None:
    start_http_server(port, addr=host)
