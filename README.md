# FALLEN v0.1

A modular Discord bot focused on moderation, security, community management, automation, and reliable infrastructure.

FALLEN is a Python-based Discord bot built with discord.py, PostgreSQL, Redis, and optional Lavalink music support.



The project uses a service-based architecture with bounded gateway processing, background workers, distributed coordination, persistent server data, and administrative controls.

# Features

🛡️ # Moderation

Ban

Kick

Timeout / mute

Unmute

Warnings

Moderation cases

Message cleanup

Slowmode

Channel lockdown / unlock

Moderation logging

Permission and role-hierarchy checks

🔐 Security

Anti-raid tracking

Raid status

Automatic lockdown

Manual lockdown

Destructive-action detection

Member quarantine

Security snapshots

Best-effort resource recovery

Security event handling

Redis-backed moderation/security state

👋 Welcome & Goodbye

Welcome messages

Goodbye messages

Custom welcome channels

Custom goodbye channels

Custom static banners

Custom animated GIF banners

Custom embeds

Member/server placeholders

Background greeting workers

Invite attribution support



Supported placeholders include:

{mention}
{name}
{username}
{server}
{count}
{membercount}


🎖️ # Leveling

Per-guild XP

Member levels

Level progress

Automatic level-role rewards

Level-role configuration

💰 Economy

Member balances

Daily rewards

Persistent PostgreSQL storage

Distributed daily rate limiting

🎫 Tickets

Ticket creation

Ticket closure

Ticket ownership

Staff access

Configurable management permissions

💡 Community

Suggestions

Polls

8ball

Choose

Coin flip

Custom commands

Server information

Avatar lookup

Ping

Health status

🎉 Friendly Interaction Commands

FALLEN includes harmless interaction commands such as:

,hug
,pat
,poke
,bonk
,slap
,cuddle
,wave
,highfive


These commands use GIF responses when an available GIF provider can respond.

🎵 # Music

FALLEN currently includes optional music support through:



Wavelink

Lavalink v4

Queue management

Play

Skip

Pause

Resume

Queue

Stop

Music status



Music requires an externally hosted Lavalink v4 node.



Without a reachable Lavalink node, music remains unavailable while the rest of the bot can continue operating.

# Command Prefix

FALLEN's current prefix command system uses:

,


Examples:

,help
,ping
,health
,ban @user
,kick @user
,timeout @user 10
,warn @user reason
,level
,balance
,daily
,ticket
,play song


The repository contains COMMAND_PREFIX in .env.example, but the current Settings implementation uses a hardcoded comma.



Therefore, , is the actual prefix in the current codebase.



If configurable prefixes are added later, this README should be updated at the same time.

Slash Commands

FALLEN also provides application/slash commands.



Examples include:

/ping
/health
/level
/serverinfo
/avatar

/warn
/warnings
/timeout
/ban
/kick
/clear
/slowmode
/lock
/unlock

/play
/skip
/pause
/resume
/queue
/stop


Grouped commands are also available for configuration, security, greetings, leveling, and other systems.



Use:

/help


or:

,help


to view commands available in the running bot.

# Requirements

FALLEN requires:



Python 3.12+

PostgreSQL

Redis

Discord Bot Token



Optional:



Lavalink v4 for music

OpenTelemetry collector for telemetry



The repository currently targets:

Python >= 3.11 and < 3.15


The included Docker image uses Python 3.12.

Installation

Clone the repository:

git clone https://github.com/NOAH-NULL/FALLEN.git


Enter the project:

cd FALLEN


 Create a virtual environment:

Linux / macOS

python3 -m venv .venv
source .venv/bin/activate


Windows

python -m venv .venv
.venv\Scripts\activate

# Install dependencies:

pip install -r requirements.txt


Configuration

Create a .env file in the repository root.



A starting point can be copied from:

.env.example


Required values include:

DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN

DATABASE_URL=postgresql+asyncpg://discordbot:discordbot@localhost:5432/discordbot

REDIS_URL=redis://localhost:6379/0


For Docker Compose, also configure:

POSTGRES_USER=discordbot
POSTGRES_PASSWORD=CHANGE_THIS
POSTGRES_DB=discordbot


Optional music configuration:

LAVALINK_URL=
LAVALINK_PASSWORD=


Optional dashboard configuration:

DASHBOARD_API_KEY=
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8081


Do not commit .env or any secret credentials.

Database Migration

Before starting the bot for the first time, run:

alembic upgrade head


This applies the current database migrations.



When the database schema changes in a future release, run the migration command again before starting the updated bot.

Minimal Local Startup

For a local development setup, PostgreSQL and Redis must be available.



If Docker is installed, start the required services:

docker compose up -d postgres redis


Check them:

docker compose ps


Then run the migrations:

alembic upgrade head


Finally start FALLEN:

python main.py


The complete basic startup is:

docker compose up -d postgres redis
alembic upgrade head
python main.py


Alternative Startup

The package also provides a module entrypoint:

python -m bot


The root main.py is the recommended simple entrypoint:

python main.py


Docker

The repository includes a complete Docker Compose environment.



The Compose stack contains:

FALLEN bot
PostgreSQL
PgBouncer
Redis
OpenTelemetry Collector


Start the full stack:

docker compose up -d


View status:

docker compose ps


View bot logs:

docker compose logs -f bot


View all logs:

docker compose logs -f


Stop the stack:

docker compose down


Persistent PostgreSQL and Redis volumes are defined by the Compose configuration.

Architecture

FALLEN separates gateway ingestion, command handling, services, background workers, and persistence.

                    Discord
                       │
                       ▼
              Discord Gateway
                       │
                       ▼
             Gateway Event Queue
                       │
                       ▼
                 Worker Pool
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
      Commands     Security     Community
          │            │            │
          └────────────┼────────────┘
                       │
                       ▼
                   Services
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
        PostgreSQL             Redis


The gateway layer uses bounded queues and worker processing rather than creating an unlimited task for every incoming event.



Guild work can be serialized to prevent conflicting operations from the same guild from running concurrently.

Redis

Redis is used for several runtime systems, including:



Caching

Distributed locks

Rate limiting

Pub/Sub invalidation

Anti-raid tracking

Shard leases

Distributed coordination

Temporary state

Background-event buffering



# Redis is not intended to replace PostgreSQL as the durable source of truth.

PostgreSQL

# PostgreSQL stores persistent application data such as:



Guild configuration

Moderation cases

Warnings

Economy balances

XP and levels

Level-role configuration

Tickets

Suggestions

Reminders

Invite information

Security data

Other persistent bot state



Alembic is used for schema migrations.

Distributed Gateway Safety

# FALLEN includes infrastructure for running gateway workers safely.



# Important mechanisms include:



Shard leases

Fencing epochs

Redis coordination

Bounded event queues

Critical-event capacity

Normal-event shedding

Worker pools

Per-guild concurrency control

Dead-letter handling

Graceful shutdown



In multi-instance deployments, shard ownership must be configured carefully.



The environment supports:

INSTANCE_ID=
SHARD_IDS=
SHARD_COUNT=


Each instance must use appropriate, non-overlapping shard ownership when manually assigning shards.

Gateway Overload Protection

The gateway queue has separate capacity for critical events.



Critical events can include command and security-related work.



Normal events can be shed when the system is overloaded instead of allowing the queue to grow without bound.



This is intended to keep the bot responsive during high traffic.

# Dashboard

FALLEN includes an HTTP dashboard/control API.



The current implementation exposes endpoints for areas such as:

/api/health
/api/stats


and authenticated guild/security operations.



Dashboard authentication uses the configured:

DASHBOARD_API_KEY=


The dashboard should not be exposed publicly without appropriate authentication and network protection.

Health & Metrics

The application provides health and metrics configuration.



Defaults include:

HEALTH_PORT=8080
METRICS_PORT=9100


Prometheus metrics are supported.



OpenTelemetry can optionally be enabled:

OTEL_ENABLED=true


and configured with:

OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_SERVICE_NAME=


Music Setup

Music requires an external Lavalink v4 server.



Configure:

LAVALINK_URL=YOUR_LAVALINK_URL
LAVALINK_PASSWORD=YOUR_LAVALINK_PASSWORD


The Lavalink server must be reachable by FALLEN.



Music availability depends on the Lavalink server, network connection, and its configured plugins/sources.



FALLEN does not run Lavalink as part of the Docker Compose stack.



Music state is currently in-memory.



A bot restart does not restore:



Music queues

Active voice sessions

Current playback state

Discloud Deployment

The repository includes:

discloud.config


The current configuration uses:

NAME=Fallen
TYPE=bot
MAIN=main.py
RAM=512
VERSION=latest


Discloud runs the bot process but does not provide this repository's PostgreSQL, Redis, or Lavalink services.



These services must be hosted separately.



Required Discloud environment variables include:

DISCORD_TOKEN=
DATABASE_URL=
REDIS_URL=
LAVALINK_URL=
LAVALINK_PASSWORD=


# The PostgreSQL URL should use:

postgresql+asyncpg://


Run the database migration against the hosted database before starting the bot:

alembic upgrade head


See:

docs/DISCLOUD.md


for the repository's deployment-specific instructions.

Project Structure

FALLEN/
│
├── bot/
│   ├── commands/
│   │   ├── ...
│   │   └── text.py
│   │
│   ├── core/
│   │   ├── bot.py
│   │   ├── config.py
│   │   ├── event_queue.py
│   │   ├── shard_lease.py
│   │   └── ...
│   │
│   ├── services/
│   ├── workers/
│   ├── web/
│   └── ...
│
├── alembic/
├── deploy/
├── docs/
├── observability/
├── scripts/
├── tests/
│
├── .env.example
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── discloud.config
├── main.py
├── pyproject.toml
├── requirements.txt
└── README.md


Testing

Run the test suite with:

pytest


The repository configures pytest with coverage reporting.



Tests cover areas including:



Commands

Gateway processing

Worker behavior

Redis coordination

Distributed locking

Shard leases

Fencing

Rate limiting

Security

Moderation

Failure handling

Shutdown behavior

Database/service behavior

Development

Recommended development flow:

git clone https://github.com/NOAH-NULL/FALLEN.git
cd FALLEN

python -m venv .venv


Activate the environment, then:

pip install -r requirements.txt


Start PostgreSQL and Redis:

docker compose up -d postgres redis


Apply migrations:

alembic upgrade head


Run the bot:

python main.py


Run tests:

pytest


Troubleshooting

Bot does not start

Check that .env exists and contains:

DISCORD_TOKEN=
DATABASE_URL=
REDIS_URL=


Then verify PostgreSQL and Redis are reachable.

Database connection error

Check:

docker compose ps


and verify:

DATABASE_URL=postgresql+asyncpg://...


If using Docker locally, make sure PostgreSQL is running.

Redis connection error

Verify Redis is running:

docker compose ps


and check:

REDIS_URL=redis://localhost:6379/0


for a local Python process.

Migration error

Run:

alembic upgrade head


against the correct database.



Make sure DATABASE_URL points to the database you actually intend to modify.

Music does not work

Music requires a reachable Lavalink v4 node.



Check:

LAVALINK_URL=
LAVALINK_PASSWORD=


If these are empty or incorrect, the music system will not be available.



The rest of FALLEN does not require music to function.

Prefix commands do not work

# The current prefix is:

,


Try:

,ping


The current code uses a hardcoded comma in bot/core/config.py.



Although .env.example contains:

COMMAND_PREFIX=,


the current configuration class does not read that variable.

Security

Never commit:

.env
Discord bot tokens
Database passwords
Redis credentials
Lavalink passwords
Dashboard API keys


Use environment variables or your deployment provider's secret-management system.



If a secret is accidentally committed, rotate it immediately.

Production Notes

FALLEN contains infrastructure intended for larger deployments, but infrastructure alone does not guarantee a specific guild count or traffic capacity.



Actual capacity depends on:



Discord gateway traffic

Number of shards

Event volume

PostgreSQL performance

Redis performance

Network latency

Discord API rate limits

Worker configuration

Image/GIF workload

Deployment topology



Load-test the actual deployment before relying on it at large scale.

Current Limitations

FALLEN v0.1 is an active development release.



Known architectural limitations include:



Discord resource recovery is best-effort.

Music state is not restored after restart.

Music requires an external Lavalink service.

Dashboard authentication currently uses an API-key model.

Prefix configuration is currently hardcoded to ,.

Large multi-instance deployments require careful shard configuration.

Production-scale capacity must be validated through real load testing.



These limitations are documented intentionally rather than hidden behind feature claims.

Version

This project is being maintained as:

FALLEN v0.1


# The public project version should remain consistent across:



README.md

pyproject.toml

release tags

deployment documentation



If the repository is being reset to v0.1, set the package version in pyproject.toml to:

version = "0.1.0"


Do not keep older v0.9, v1.x, v3.x, or historical version sections in the README.

Roadmap

v0.1

Focus on making the existing systems reliable and usable:



Moderation

Security

Community features

Leveling

Economy

Tickets

Suggestions

Welcome/goodbye

Reminders

Music

Dashboard

PostgreSQL persistence

Redis infrastructure

Gateway reliability

Testing

Deployment support



Future versions should prioritize reliability, usability, and polishing existing systems before adding unnecessary feature sprawl.

License

See the repository license file for the current licensing terms.

FALLEN v0.1

Moderation. Security. Community. Reliability.
