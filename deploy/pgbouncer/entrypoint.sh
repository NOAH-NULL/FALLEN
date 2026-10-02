#!/bin/sh
set -eu
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
cat > /etc/pgbouncer/generated.ini <<EOF
[databases]
${POSTGRES_DB} = host=postgres port=5432 dbname=${POSTGRES_DB} user=${POSTGRES_USER} password=${POSTGRES_PASSWORD}

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = plain
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 10
reserve_pool_timeout = 3
server_idle_timeout = 60
server_lifetime = 3600
ignore_startup_parameters = extra_float_digits
EOF
printf '"%s" "%s"\n' "$POSTGRES_USER" "$POSTGRES_PASSWORD" > /etc/pgbouncer/userlist.txt
exec pgbouncer /etc/pgbouncer/generated.ini
