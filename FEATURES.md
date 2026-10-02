# Fallen V16 capability matrix

Fallen V16 contains exactly 100 additional Discord capabilities across nine domains. Unlike the original V16 snapshot, these are backed by durable services/models and runtime hooks where applicable; the catalog is not a list of empty commands.

See `docs/FEATURE_MATRIX.md` for the complete 1–100 list and `docs/ARCHITECTURE.md` for implementation boundaries.

## Implemented foundations

- Shared `/v16` + `,v16` hybrid command surface.
- Persistent per-guild capability configuration with safe defaults.
- Security event timeline and automatic lockdown hook.
- Join-time anti-bot/account-age/suspicious-name/raid decisions.
- Message-time flood, duplicate, emoji, mention, domain and regex AutoMod decisions.
- Scheduled temporary timeout/ban execution.
- Warning points and expiration-aware warning counts.
- Persistent member profiles, reputation and playlists.
- Persistent V16 ticket metadata: claim, priority, notes, status and rating fields.
- Named configuration snapshots and restore.
- Database-backed models and Alembic migrations.
- Secret-safe PgBouncer container bootstrap.
- Regression tests for architecture and the full 100-feature catalog.
