#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/migrate_sqlite_to_postgres.sh main <sqlite-db-path> <postgres-url>
  scripts/migrate_sqlite_to_postgres.sh chatbot <sqlite-db-path> <postgres-url>
  SQLITE_PATH=<sqlite-db-path> POSTGRES_URL=<postgres-url> scripts/migrate_sqlite_to_postgres.sh main

Examples:
  scripts/migrate_sqlite_to_postgres.sh main data/maplewind.db.bak postgresql://user:pass@localhost:5432/maplewind
  scripts/migrate_sqlite_to_postgres.sh chatbot data/chatbot.db.bak postgresql://user:pass@localhost:5432/chatbot

The PostgreSQL URL must be a synchronous libpq URL (postgresql://...), not postgresql+asyncpg://.
EOF
}

if [[ $# -ne 1 && $# -ne 3 ]]; then
  usage >&2
  exit 2
fi

SERVICE="$1"
SQLITE_DB="${2:-${SQLITE_PATH:-}}"
POSTGRES_URL="${3:-${POSTGRES_URL:-}}"

if [[ "$SERVICE" != "main" && "$SERVICE" != "chatbot" ]]; then
  echo "SERVICE must be 'main' or 'chatbot'" >&2
  exit 2
fi
if [[ -z "$SQLITE_DB" || -z "$POSTGRES_URL" ]]; then
  usage >&2
  exit 2
fi
if [[ ! -f "$SQLITE_DB" ]]; then
  echo "SQLite DB not found: $SQLITE_DB" >&2
  exit 1
fi
if [[ "$POSTGRES_URL" == postgresql+asyncpg://* ]]; then
  echo "Use postgresql:// for pgloader, not postgresql+asyncpg://" >&2
  exit 1
fi

SQLITE_ABS="$(cd "$(dirname "$SQLITE_DB")" && pwd)/$(basename "$SQLITE_DB")"

echo "==> Migrating $SERVICE SQLite -> PostgreSQL"
echo "    source: $SQLITE_ABS"
echo "    target: $POSTGRES_URL"

if command -v pgloader >/dev/null 2>&1; then
  pgloader "sqlite:///$SQLITE_ABS" "$POSTGRES_URL"
elif command -v docker >/dev/null 2>&1; then
  DOCKER_MOUNT_DIR="$(dirname "$SQLITE_ABS")"
  if docker version --format '{{.Client.Os}}' 2>/dev/null | grep -qi '^windows$'; then
    DOCKER_MOUNT_DIR="$(wslpath -w "$DOCKER_MOUNT_DIR")"
  fi
  docker run --rm \
    -v "$DOCKER_MOUNT_DIR:/data:ro" \
    dimitri/pgloader:latest \
    pgloader "sqlite:////data/$(basename "$SQLITE_ABS")" "$POSTGRES_URL"
else
  echo "pgloader or docker is required" >&2
  exit 1
fi

echo "==> Comparing row counts"
if command -v uv >/dev/null 2>&1; then
  uv run python -m scripts.verify_postgres_counts "$SERVICE" "$SQLITE_ABS" "$POSTGRES_URL"
else
  python -m scripts.verify_postgres_counts "$SERVICE" "$SQLITE_ABS" "$POSTGRES_URL"
fi

echo "==> Done. Row counts match."
