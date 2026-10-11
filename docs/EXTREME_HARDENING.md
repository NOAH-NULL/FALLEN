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

## V16 capability honesty and recovery safety

The 100-entry V16 list is a catalog, not proof that all 100 capabilities are implemented.
Only entries in `IMPLEMENTED_FEATURES` can be enabled. Stale database values for catalog-only
entries are ignored and reported by `/v16 validate`. Do not describe catalog-only entries as
active security controls.

Currently implemented toggles cover join heuristics and lockdown triggers, channel/role-delete
burst detection, selected message AutoMod checks and custom rules, temporary punishments, member
profiles, reputation, and personal text playlists. Permission-escalation detection, mass-ban
detection, webhook-abuse detection, trusted-admin allowlists, and many other catalog entries are
not implemented and must remain unavailable until they have runtime handlers and regression tests.

Lockdown stores the full @everyone permission overwrite and restores it without replacing unrelated
permission bits. A failed recovery keeps its snapshot for retry. Older snapshots stored only the
send_messages value, so they cannot reconstruct unrelated permission bits that may already have
been lost by an older release.

Anti-nuke recreation is best-effort. Categories, text channels, voice channels, and stage channels
can be recreated with their supported settings. Announcement and other unsupported channel types
are deliberately skipped rather than recreated as the wrong type. A recreated role receives a new
Discord ID; role assignments and overwrites referencing the deleted role cannot be transparently
rebound by this recovery path.

Administrators can use `/v16 unlockdown` to retry a saved lockdown recovery and
`/v16 unquarantine <member>` to restore a quarantined member's saved roles. If role hierarchy,
missing roles, or permissions prevent a complete recovery, FALLEN keeps the recovery snapshot and
the quarantine role so the partial result is not mistaken for success.

