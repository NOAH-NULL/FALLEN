# Fallen architecture

Fallen keeps one repository but separates responsibilities by runtime layer. This is deliberate: a monorepo is not itself the problem; coupling unrelated responsibilities inside command handlers is.

## Request flow

`Discord event/command -> command adapter -> service -> repository/model -> PostgreSQL/Redis`

Commands should validate permissions and arguments, then call services. Durable state belongs in SQLAlchemy models and migrations. Redis is coordination/cache, never the source of truth.

## Runtime boundaries

- `bot/core/` — process configuration, database, telemetry, health, shard ownership and gateway queueing.
- `bot/commands/` — Discord-facing adapters. V16 uses a hybrid command group so `/v16` and `,v16` share one implementation.
- `bot/services/` — business logic and persistence operations.
- `bot/models/` — durable schema.
- `bot/workers/` — scheduled/background work.
- `bot/cache/` — Redis cache, rate limiting, invalidation and single-flight.
- `bot/web/` — HTTP health/dashboard boundary.

## V16 capability implementation

The previous V16 layer only stored 100 booleans. It now has:

- durable capability defaults and validation;
- security event timeline;
- scheduled moderation actions;
- warning points and expiration;
- persistent AutoMod rules;
- member profiles, reputation and playlists;
- ticket persistence, claiming, priority and notes;
- named configuration snapshots and restore;
- real join/message runtime enforcement for enabled security and AutoMod capabilities;
- one shared hybrid command surface for prefix/slash V16 administration.

Not every capability is enabled by default. Destructive enforcement remains opt-in; non-destructive profile/engagement/diagnostic capabilities are enabled by default.

## Secrets

Database credentials are no longer stored in the PgBouncer config or userlist. Docker generates both from `POSTGRES_*` environment variables at container startup. `.env` remains local-only and is ignored by Git.

## Migrations

The migration chain is intentionally append-only. Multiple small migrations are acceptable when each migration is reproducible. Alembic now loads `.env`, uses SQLAlchemy metadata for autogeneration/comparison, and executes migrations rather than silently calling `create_all()`.
