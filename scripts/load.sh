#!/usr/bin/env bash
# Tạo schema và nạp dữ liệu: ref_central (đối chứng, trong campus_a) + 3 trạm, KỂ CẢ trạm ở máy khác.
# Mọi lệnh chạy từ máy A: dùng psql trong container campus_a nối tới từng trạm theo deploy.toml (qua LAN nếu ở máy B);
# \copy đọc CSV phía client, tức từ thư mục data/ của máy A — máy B không cần giữ dữ liệu.
# Dùng: scripts/load.sh [mini|lab]
set -euo pipefail
export MSYS_NO_PATHCONV=1 COMPOSE_PROFILES=all   # Git Bash không đổi /sql thành đường dẫn Windows
PY=${PY:-python3}
SIZE=${1:-lab}
TABLES="course section student enrollment certificate cert_language cert_it cert_it_module cert_research cert_research_coauthor"

# psqlr <host:port> <db> [đối số psql...]
psqlr() { local a=$1 db=$2; shift 2
  docker compose exec -T -e PGPASSWORD=cs5104 campus_a psql -h "${a%%:*}" -p "${a##*:}" -U postgres -d "$db" -v ON_ERROR_STOP=1 -q "$@"; }
copy_all() { # host:port db thư_mục_trong_/data
  for t in $TABLES; do psqlr "$1" "$2" -c "\\copy $t FROM '/data/$3/$t.csv' WITH (FORMAT csv, HEADER true)"; done
}

A=$($PY -X utf8 scripts/site.py upstream campus_a)

# --- CSDL đối chứng (trong trạm A)
psqlr "$A" postgres -c "DROP DATABASE IF EXISTS ref_central" -c "CREATE DATABASE ref_central"
psqlr "$A" ref_central -f /sql/schema_central.sql
copy_all "$A" ref_central "central/$SIZE"

# --- Các trạm: schema + khối id riêng + dữ liệu mảnh
for pair in campus_a:1000000 campus_b:2000000 campus_c:3000000; do
  site=${pair%%:*}; base=${pair##*:}
  addr=$($PY -X utf8 scripts/site.py upstream "$site")
  echo "== $site ($addr, máy $($PY -X utf8 scripts/site.py machine "$site"))"
  psqlr "$addr" postgres -c "DROP DATABASE IF EXISTS uni" -c "CREATE DATABASE uni" 2>&1 | grep -v NOTICE || true
  psqlr "$addr" uni -v site="$site" -v idbase="$base" -f /sql/schema_site.sql
  copy_all "$addr" uni "$SIZE/$site"
done
echo "OK: đã nạp $SIZE"
