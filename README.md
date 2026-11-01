# FALLEN

**Version:** 0.1.0  
**License:** MIT  
**Python:** 3.11–3.14

FALLEN is a modular Discord bot built with `discord.py`, PostgreSQL, and Redis. It focuses on moderation, server security, community management, and reliable background processing.

## Features

### Moderation and AutoMod
- Ban, kick, timeout, and untimeout commands
- Warning records with active warning-point totals and optional expiry
- Scheduled temporary timeouts and temporary bans
- Moderation cases, message cleanup, slowmode, and channel lockdown controls
- Message-flood detection and configurable AutoMod rule matching
- Moderation logging and permission/role-hierarchy checks

AutoMod behavior depends on the server's configuration and enabled rules. It should not be interpreted as a guarantee that every link, phrase, or attachment is automatically blocked.

### Security
- Anti-raid tracking and raid status
- Automatic and manual lockdown
- Destructive-action detection and member quarantine
- Security event handling and snapshots
- Redis-backed coordination and temporary state

### Community
- Welcome and goodbye messages, embeds, and banners
- Per-server leveling and level-role rewards
- Tickets, suggestions, polls, and custom commands
- Economy and daily rewards
- Reminders and lightweight interaction commands

### Optional music
Music uses Wavelink and an externally hosted Lavalink v4 node. Music is unavailable when that node is not configured or reachable. Queue and active playback state are currently in-memory and do not survive a bot restart.

## Requirements

- Python 3.11–3.14 (the included Docker image uses Python 3.12)
- PostgreSQL
- Redis
- A Discord bot token

Optional:
- Lavalink v4 for music
- OpenTelemetry collector for telemetry
- FastAPI dependencies for the Control Center API

## Installation

Clone the repository and enter it:

```bash
git clone https://github.com/NOAH-NULL/FALLEN.git
cd FALLEN
```

Create and activate a virtual environment.

**Windows**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project and its runtime dependencies:

```bash
python -m pip install .
```

For development and tests:

```bash
python -m pip install ".[dev]"
```

For the optional dashboard API dependencies:

```bash
python -m pip install ".[dashboard]"
```

The existing `requirements.txt` remains available for deployments that use the pinned requirements workflow.

## Configuration

Copy `.env.example` to `.env` and set at least:

```env
DISCORD_TOKEN=your_discord_bot_token
DATABASE_URL=postgresql+asyncpg://discordbot:password@localhost:5432/discordbot
REDIS_URL=redis://localhost:6379/0
```

The current text-command prefix is a comma (`,`). Per-guild prefix configuration is supported by the bot's guild configuration; `COMMAND_PREFIX` is not currently read as a global environment setting and has therefore been removed from the example configuration.

Never commit `.env` or secret credentials.

## Database setup and startup

Run migrations before starting the bot:

```bash
alembic upgrade head
python main.py
```

Alternatively, start the bot as a module:

```bash
python -m bot
```

For local PostgreSQL and Redis services, Docker Compose can start the dependencies:

```bash
docker compose up -d postgres redis
alembic upgrade head
python main.py
```

## Docker

The repository includes a Docker Compose environment for the bot and supporting services.

```bash
docker compose up -d
docker compose ps
docker compose logs -f bot
```

Stop the stack with:

```bash
docker compose down
```

## Architecture

The bot separates Discord gateway ingestion, command handling, services, background workers, and persistence. PostgreSQL is the durable store for application data. Redis supports caching, rate limiting, distributed locks, shard leases, and temporary coordination state.

For multi-instance deployments, configure non-overlapping shard ownership. Production capacity and failover behavior should be validated with deployment-specific load tests.

## Control Center API and Vercel

The repository contains a separate FastAPI Control Center API configured for Vercel through the `[tool.vercel]` entrypoint in `pyproject.toml`. This is an HTTP API deployment, not the Discord gateway process: the bot must continue running in a long-lived service such as Railway or another suitable host.

The current API is an early-stage OAuth/session scaffold. Its session store is process-local, so it is not suitable for horizontally scaled or restart-resilient production use without moving session state to a shared persistent store. Do not expose the API publicly until authentication, session persistence, rate limiting, and deployment configuration have been reviewed.

The API does not replace the bot's PostgreSQL/Redis services or run the Discord gateway.

## License

FALLEN is distributed under the MIT License. See [LICENSE](LICENSE).
