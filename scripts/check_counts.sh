#!/usr/bin/env bash
# Kiểm tra nhanh: tổng dòng 3 trạm (qua all_*) bằng CSDL đối chứng ref_central.
set -euo pipefail
export MSYS_NO_PATHCONV=1 COMPOSE_PROFILES=all
q() { docker compose exec -T campus_a psql -U postgres -d "$1" -At -c "select count(*) from $2"; }
fail=0
for t in section student enrollment certificate cert_language cert_it cert_it_module cert_research cert_research_coauthor; do
  a=$(q ref_central "$t"); b=$(q uni "all_$t")
  if [ "$a" = "$b" ]; then echo "OK   $t $a"; else echo "FAIL $t ref=$a all=$b"; fail=1; fi
done
exit $fail
