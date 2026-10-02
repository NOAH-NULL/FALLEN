# Fallen v0.3 Extreme Hardening

This release strengthens the distributed cache path beyond process-local single-flight.

## Distributed single-flight

- Redis fencing epochs provide monotonically increasing ownership for every cache-miss flight.
- Cache writes are atomically rejected when the flight epoch is stale.
- Completion notifications use per-key Redis Pub/Sub channels so remote waiters wake immediately.
- Pub/Sub is an optimization only; jittered polling remains the correctness fallback.
- Lease renewal prevents long database loads from expiring the owner during normal operation.

## Resilience goals

The design targets bounded memory, stale-writer rejection, poison-event isolation, PgBouncer-safe async database connections, and cross-pod cache-miss coalescing. Actual production readiness still requires multi-process chaos tests against real Redis/PostgreSQL and controlled network partitions.


## v0.5 release hardening

- `/healthz` is a process liveness endpoint and does not restart pods during dependency outages.
- `/readyz` checks PostgreSQL, Redis, Discord readiness, and shard-lease health.
- Release packaging is generated from a clean staging tree and rejects `__pycache__`, `.pyc`, and coverage artifacts.
- `make chaos` runs deterministic failure-injection tests for lease loss, queue saturation, and dependency outages.
- Alembic migrations remain versioned and linear; migration execution is a deployment concern rather than an application-startup loop.
