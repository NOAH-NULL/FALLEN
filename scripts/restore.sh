#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL required}"
: "${1:?dump file required}"
pg_restore --clean --if-exists --dbname="$DATABASE_URL" "$1"
