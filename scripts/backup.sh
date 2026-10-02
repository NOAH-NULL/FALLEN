#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL required}"
pg_dump "$DATABASE_URL" --format=custom --file="${1:-titan-$(date +%Y%m%d-%H%M%S).dump}"
