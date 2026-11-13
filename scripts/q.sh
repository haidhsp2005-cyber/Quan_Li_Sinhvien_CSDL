#!/usr/bin/env bash
# Chạy một truy vấn demo ở trạm trung tâm. Dùng: scripts/q.sh <1..5> [explain]
set -euo pipefail
export MSYS_NO_PATHCONV=1 COMPOSE_PROFILES=all
f="sql/queries/q$1.sql"
if [ "${2:-}" = "explain" ]; then
  sql="EXPLAIN (ANALYZE, VERBOSE) $(grep -v '^--' "$f")"
  docker compose exec -T campus_a psql -U postgres -d uni -c "$sql"
else
  docker compose exec -T campus_a psql -U postgres -d uni -c '\timing on' -f "/sql/queries/q$1.sql"
fi
