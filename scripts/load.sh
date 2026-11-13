#!/usr/bin/env bash
# Tạo schema và nạp dữ liệu: ref_central (đối chứng, trong campus_a) + 3 trạm. Dùng: scripts/load.sh [mini|lab]
set -euo pipefail
export MSYS_NO_PATHCONV=1 COMPOSE_PROFILES=all   # Git Bash không đổi /sql thành đường dẫn Windows
SIZE=${1:-lab}
TABLES="course section student enrollment certificate cert_language cert_it cert_it_module cert_research cert_research_coauthor"
psqlc() { docker compose exec -T "$1" psql -U postgres -v ON_ERROR_STOP=1 -q "${@:2}"; }

copy_all() { # container db dir
  for t in $TABLES; do
    psqlc "$1" -d "$2" -c "\\copy $t FROM '/data/$4/$t.csv' WITH (FORMAT csv, HEADER true)"
  done
}

# --- CSDL đối chứng
psqlc campus_a -d postgres -c "DROP DATABASE IF EXISTS ref_central" -c "CREATE DATABASE ref_central"
psqlc campus_a -d ref_central -f /sql/schema_central.sql
copy_all campus_a ref_central central "central/$SIZE"

# --- Các trạm: container, db, site, khối id
i=0
for pair in campus_a:1000000 campus_b:2000000 campus_c:3000000; do
  site=${pair%%:*}; base=${pair##*:}
  psqlc "$site" -d postgres -c "DROP DATABASE IF EXISTS uni" -c "CREATE DATABASE uni"
  psqlc "$site" -d uni -v site="$site" -v idbase="$base" -f /sql/schema_site.sql
  copy_all "$site" uni "$site" "$SIZE/$site"
done
echo "OK: đã nạp $SIZE"
