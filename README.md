# Fallen v0.9 — Peak Control Plane & Adaptive Security

Fallen v6 expands the v5 foundation into a broader community platform while keeping gateway work bounded and durable state in PostgreSQL.

## Major capabilities
- Moderation + persistent case history
- AutoMod + raid-burst detection + lockdown
- Welcome/goodbye animated cards rendered off the gateway loop
- Autorole + audit foundation
- Custom commands
- XP/levels
- Tickets
- Suggestions + polls
- Reminders with durable scheduler
- Economy primitives (balance/daily)
- Utility/fun commands
- External music-node boundary
- Dashboard API (`/api/health`, `/api/stats`)
- PostgreSQL + Redis, cache single-flight, distributed invalidation/rate limits
- AutoShardedBot with explicit shard assignment
- Prometheus + optional OpenTelemetry
- Docker/Helm/CI/Alembic

## Quick start
1. Copy `.env.example` to `.env`.
2. Put your Discord token in `.env`; never commit it.
3. Start local infrastructure: `docker compose up -d postgres redis`.
4. Create/activate your Python virtual environment and run `pip install -r requirements.txt`.
5. Run `alembic upgrade head`.
6. Start the bot with `python -m bot`.

### Windows helper
If the project is in a normal Windows folder with a `venv`, run `powershell -ExecutionPolicy Bypass -File .\scripts\start_windows.ps1`. It runs migrations and then starts the bot.

### Local dependency note
The local Python process expects PostgreSQL on `localhost:5432` and Redis on `localhost:6379`. The example environment is configured for the Docker Compose development credentials. The Compose bot container uses the internal PostgreSQL/PgBouncer and Redis service names automatically.

### Optional action GIF providers
Action GIFs try Giphy first when `GIPHY_API_KEY` is set, then Tenor when `TENOR_API_KEY` is set, and finally the existing OtakuGIFs provider. Giphy and Tenor require their own API keys; add either or both to `.env`. Without keys, the existing provider remains available.



## v0.8 Peak Product Pass
- Persistent lockdown snapshots restore each channel's exact @everyone send-message state instead of blindly resetting permissions.
- Anti-nuke destructive-action bursts are observed through Discord audit logs and can trigger the existing automatic-lockdown safety path.
- Automatic and manual lockdowns share the same state-preserving recovery engine.
- Added a polished operator dashboard at `/dashboard` with API-key protected runtime statistics.
- Dashboard statistics are no longer exposed without the configured `DASHBOARD_API_KEY`.
- Shared embed styling now carries a consistent Fallen footer across command responses.
- Added regression coverage for dashboard access, state-preserving lockdown recovery, and anti-nuke event wiring.

## v0.7 Product Quality Pass
- Centralized prefix-command error handling for missing arguments, bad member/role/channel values, permissions, cooldowns, and unexpected failures.
- Fixed the community embed helper to support thumbnails used by `/level`, `/warnings`, and profile-style commands.
- Prefix `daily` now uses the same distributed 24-hour rate limit as the slash command.
- Economy and XP updates use PostgreSQL conflict-safe row creation plus row locks, preventing lost updates under concurrent pods.
- Ticket channels now grant access to configured Manage Channels roles and the bot while recording the ticket owner for safe closure.
- Ticket closure is restricted to the creator or channel managers.
- Lockdown/unlockdown use bounded parallelism instead of serial channel edits, while reporting partial success.
- Custom command output suppresses accidental mentions.
- Moderation actions now consistently emit audit-log entries after successful actions.
- Added product-quality regression tests covering these real command paths.

## V15.2 runtime fixes
- Complete Alembic lineage through `0007_runtime_schema`.
- Guild configuration model and database schema are aligned, including embed settings and timestamps.
- Prefix command registration no longer collides on `levelrole`/duplicate utility commands.
- Moderation audit logging and security raid-status use valid service APIs.
- Invite attribution retries queued persistence after transient database errors.
- Reminder claiming uses PostgreSQL row locking to avoid duplicate delivery across workers.

## Scale discipline
No source-code project can honestly promise a server count. Capacity depends on gateway traffic, event mix, database hardware, Redis topology, shard count, API rate limits, image workload, and deployment design. Load-test before production.

## v7 architecture hardening
- Gateway callbacks are bounded O(1) producers into a local queue; database, image rendering, moderation workflows, and XP writes execute in workers.
- Anti-raid uses an atomic Redis sorted-set window, so join bursts are visible across pods/shards.
- Guild config uses local single-flight plus a Redis distributed lock and Pub/Sub invalidation to prevent cache stampedes.
- Every shard has a Redis lease; duplicate shard ownership fails fast. In multi-pod deployments, assign non-overlapping `SHARD_IDS` per pod.
- Redis Streams are available for durable background-event extensions; Pub/Sub remains notification-only.
- Generated `__pycache__`, `.pyc`, and `.pytest_cache` artifacts are excluded from the release.

## V7 Enterprise hardening
- Gateway processing uses a fixed worker pool; inbound events never create one asyncio Task each.
- Guild work is serialized through fixed lock stripes to bound memory while allowing cross-guild concurrency.
- Redis shard leases fail closed: a renewal failure marks the instance unhealthy and initiates shutdown.
- PgBouncer support is included for transaction-pooled PostgreSQL connections; enable `DB_USE_PGBOUNCER=true` and point `DATABASE_URL` at the PgBouncer service.
- Guild configuration reads use local single-flight plus a Redis distributed lock, so concurrent cache misses do not fan out into PostgreSQL queries.

## Extreme failure hardening (v0.3)
- Cross-pod guild cache misses use a Redis distributed single-flight lock with lock renewal; local single-flight only reduces same-process contention.
- Shard ownership now uses monotonically increasing Redis fencing epochs. Workers validate the epoch before dispatch and the database session rejects stale fenced commits; fenced cache writes are checked atomically in Redis.
- Gateway ingestion remains bounded and non-blocking, with reserved critical capacity, stale-event shedding, and an 8-event fairness window so critical floods cannot starve normal traffic forever.
- Worker exceptions become bounded dead-letter records and are also persisted to a capped Redis Stream (`gateway-dlq`) when Redis is available. Poison events are not retried indefinitely.
- PgBouncer transaction pooling disables asyncpg prepared-statement caching when `DB_USE_PGBOUNCER=true`.
- Helm health/metrics ports are explicitly wired to the application (`8080` health, `9100` metrics), avoiding probe/service drift.
- The test suite includes cross-instance single-flight, lease epoch replacement, stale-fence rejection paths, bounded worker behavior, fairness, and DLQ handling.

## Prefix / text commands
The default text-command prefix is `,` and can be changed with `COMMAND_PREFIX`.

- `,hug @member` / `,Hug @member`
- `,kill @member` — harmless cartoon gag
- `,ban @member [reason]`
- `,mute @member [minutes] [reason]` / `,m`
- `,unmute @member` / `,un`
- `,play <query>` / `,p`
- `,stop` / `,s`

Moderation commands respect Discord permissions and role hierarchy. Music playback uses Wavelink with an external Lavalink v4 node. Set `LAVALINK_URL` and `LAVALINK_PASSWORD` in `.env` to connect; the node must be reachable by the bot and have plugins configured for the media sources you want. The player stays connected while the bot process is running, including when its queue is empty. Queue state and voice sessions are not restored after a process restart. Playback latency and source availability depend on the Lavalink host, network, and its plugins.

Music commands: `/play`, `/skip`, `/pause`, `/resume`, `/queue`, `/stop` and `,play`, `,skip`, `,pause`, `,resume`, `,queue`, `,stop`.

## Prefix commands
Every user-facing slash command also has a prefix/text equivalent using `COMMAND_PREFIX` (default `,`). Grouped slash commands keep their grouped text form too, for example:

- `,ping`, `,health`, `,level`, `,serverinfo`, `,avatar`
- `,warn`, `,warnings`, `,timeout`, `,ban`, `,kick`, `,clear`, `,slowmode`, `,lock`, `,unlock`
- `,mute` / `,m`, `,unmute` / `,un`, `,play` / `,p`, `,stop` / `,s`
- `,config autorole|logs|automod`
- `,settings welcome-channel|goodbye-channel|automod|autorole`
- `,greeting channel|message|test`
- `,custom set|remove`
- `,engage poll|8ball|choose`
- `,security raid-status|lockdown|unlockdown`

Friendly/OwO-style interaction commands such as `,hug`, `,pat`, `,poke`, `,bonk`, `,slap`, `,cuddle`, `,wave`, and `,highfive` use GIF responses. The GIF provider is external and has a text-safe fallback if it is unavailable.

### V10 leveling and UwU
- Use `,uwu @member` or `/uwu @member` for a GIF-based UwU interaction targeting a real member.
- XP is persisted per guild/member. Use `,level [@member]` or `/level [member]` to view progress.
- Configure automatic level rewards with `,levelrole add <level> @role`, `,levelrole remove <level>`, or `,levelrole list`.
- The corresponding slash commands are `/levelrole`, `/levelrole-remove`, and `/levelroles`.
- The bot only assigns roles below its highest role and ignores managed roles.

## Custom welcome/goodbye banners

Greeting cards support per-server custom static images and animated GIFs. Configure them with either slash commands or the `,` prefix commands:

- `/greeting banner welcome` with an image/GIF attachment or URL
- `/greeting banner goodbye` with an image/GIF attachment or URL
- `/greeting banner-reset welcome`
- `,greeting banner welcome` with an attached image/GIF
- `,greeting banner welcome https://example.com/banner.gif`
- `,greeting banner-reset welcome`

Animated GIF backgrounds are preserved frame-by-frame when the member avatar and custom message are rendered onto the card.

### Welcome / Goodbye embed cards
Fallen can send the rendered welcome/goodbye banner or GIF together with a customizable Discord embed. Embed title, description, color, and enabled state are stored per guild. The embed can use `{mention}`, `{name}`, `{username}`, `{server}`, `{count}`, and `{membercount}` placeholders.

## V13 concurrency hardening

V13 adds explicit high-load protections:
- Cross-pod cache single-flight uses a Redis lease with renewal; local lock entries are reference-counted and garbage-collected when idle.
- Shard leases use a fresh random ownership token on every acquisition/release cycle, so a restarted instance cannot accidentally renew a previous lease token.
- Gateway events carry enqueue timestamps; stale normal-priority events are shed instead of allowing unbounded latency. Critical command/security events retain reserved capacity.
- Gateway workers remain fixed-size and per-guild serialized; no task-per-event fanout is used.
- PgBouncer transaction pooling remains compatible with the current codebase because asyncpg statement caching is disabled when enabled, and the bot does not depend on LISTEN/NOTIFY or session advisory locks.

These controls improve failure behavior but do not claim mathematical distributed consensus or automatic shard assignment. A production 100k+ guild deployment still requires real multi-pod load/chaos testing.

## V13 concurrency hardening

V13 adds explicit high-load protections:
- Cross-pod cache single-flight uses a Redis lease with renewal; local lock entries are reference-counted and removed when idle.
- Shard leases use a fresh random ownership token on every acquisition cycle, preventing an old instance from renewing a later lease.
- Gateway events carry enqueue timestamps; stale normal-priority events are shed instead of allowing unbounded latency. Critical events retain reserved capacity.
- Gateway workers remain fixed-size and per-guild serialized; no task-per-event fanout is used.
- PgBouncer transaction pooling remains compatible with the current codebase because asyncpg statement caching is disabled when enabled, and the bot does not use LISTEN/NOTIFY or session advisory locks.
- This is hardened failure behavior, not a claim of mathematical distributed consensus; 100k+ guild deployments still require real multi-pod load and chaos tests.

## V14 user-facing features
V14 adds persistent invite tracking, invite leaderboard commands, inviter placeholders for welcome/goodbye cards, and a broader prefix-command mirror. Welcome cards can combine a custom static/animated banner with a Discord embed. Friendly interaction commands remain GIF-based.

## V15 burst-resilience hardening
V15 focuses on high-volume join and raid behavior rather than only adding commands:
- Invite attribution is removed from the critical member-join path and handled by a bounded worker queue.
- Redis-backed invite snapshots use distributed single-flight refresh locks to avoid per-pod `guild.invites()` stampedes.
- Invite join/leave statistics are buffered in Redis hashes and periodically flushed to PostgreSQL with batched upserts.
- Member-to-inviter attribution is retained in Redis immediately and persisted to PostgreSQL through a bounded batch writer, allowing accurate leave accounting.
- Anti-raid detection runs before expensive welcome rendering; when a raid threshold is reached, welcome work is automatically shed.
- Greeting jobs have a bounded queue and stale-event expiry so a backlog cannot grow without limit.
- Redis remains a cache/buffer; PostgreSQL remains the durable source of truth.

## Fallen V16 development notes

V16 adds a dynamic help directory in both interfaces:

- `,help` (aliases: `,commands`, `,cmds`) displays registered prefix commands in button-paginated pages.
- `,help <command>` displays usage, aliases, parent group and description.
- `/help` displays registered application commands in an ephemeral paginated menu.
- `/help <command>` displays details for a registered slash command.
- The directory is generated from commands actually loaded at runtime. It does not count roadmap items or advertise placeholder commands as implemented.

The 600+ command target is a product scope, not a reason to generate hundreds of empty command stubs. Each command must be implemented and tested before it is exposed in help. Existing modules are being retained as the base and expanded incrementally.


## Product Hardening (v0.6)

- Consistent embed-based success, warning, info and error responses.
- Global application-command error handling with permission, cooldown and validation messages.
- Moderation actions now create moderation cases for auditability.
- Custom commands support set/use/remove/list flows and suppress accidental mass mentions.
- Daily rewards are rate-limited across pods.
- Unsupported music playback no longer pretends a request was executed.
- Release packaging excludes Python bytecode and local test artifacts.


## v0.9 Peak Control Plane
- Redis Lua exponential-decay multi-factor moderation heat engine.
- Configurable per-guild heat weights, decay and TTL through the authenticated control plane.
- Rogue-staff quarantine with permission stripping and best-effort resource restoration.
- Baseline security snapshots plus recovery endpoints.
- Authenticated `/api/v1/guilds/{guild_id}/audit-logs`, `/snapshots`, `/snapshots/restore`, and `/automod/rules` endpoints.
- Dashboard accepts the configured credential as a Bearer token or `X-Dashboard-Key`.
- 63 automated tests passing in the release build.
