#!/usr/bin/env sh
set -eu

log() {
  printf "%s\n" "$1"
}

DATABASE_URL="${DATABASE_URL:-}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
RUN_SEED="${RUN_SEED:-1}"

# Explicitly export so subprocesses (like python/alembic) definitely see them
export DATABASE_URL
export RUN_MIGRATIONS
export RUN_SEED

if [ -z "$DATABASE_URL" ]; then
  log "[entrypoint] ERROR: DATABASE_URL is not set"
  exit 1
fi

export PYTHONPATH="${PYTHONPATH:-/app}"

# Run centralized initialization
log "[entrypoint] Starting system initialization..."

# 1. Wait for DB
python -c "import asyncio; from backend.initialize import wait_for_db; asyncio.run(wait_for_db())"

# 2. Run migrations via CLI (Professional standard)
if [ "$RUN_MIGRATIONS" = "1" ]; then
  log "[entrypoint] Running database migrations..."
  alembic upgrade head
fi

# 3. Run seed if enabled
if [ "$RUN_SEED" = "1" ]; then
  log "[entrypoint] Checking seed requirement..."
  python -m backend.seed
fi

log "[entrypoint] Starting: $*"
exec "$@"

