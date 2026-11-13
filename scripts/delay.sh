#!/usr/bin/env bash
# Độ trễ mạng giữa trạm trung tâm và các trạm xa, qua toxiproxy (API :8474).
#   scripts/delay.sh setup   tạo proxy b -> :15433, c -> :15434 (làm lại được, không lỗi nếu đã có)
#   scripts/delay.sh on      trễ 30 ms khứ hồi (15 ms mỗi chiều)
#   scripts/delay.sh off     bỏ trễ
#   scripts/delay.sh status
# Upstream mặc định là container cùng mạng compose; khi 2 máy thật: UPSTREAM_B=<IP máy B>:5433 UPSTREAM_C=<IP máy B>:5434
set -euo pipefail
API=${TOXIPROXY:-http://localhost:8474}
UB=${UPSTREAM_B:-campus_b:5432}; UC=${UPSTREAM_C:-campus_c:5432}
MS=${DELAY_MS:-30}; HALF=$((MS / 2))

mk() { curl -sf -X POST "$API/proxies" -d "{\"name\":\"$1\",\"listen\":\"0.0.0.0:$2\",\"upstream\":\"$3\",\"enabled\":true}" >/dev/null || true; }
tox() { # proxy stream
  curl -sf -X POST "$API/proxies/$1/toxics" -d "{\"name\":\"lat_$2\",\"type\":\"latency\",\"stream\":\"$2\",\"toxicity\":1.0,\"attributes\":{\"latency\":$HALF,\"jitter\":0}}" >/dev/null
}
untox() { curl -s -X DELETE "$API/proxies/$1/toxics/lat_$2" >/dev/null || true; }

case "${1:-status}" in
  setup) mk b 15433 "$UB"; mk c 15434 "$UC"; echo "proxy: b->$UB (15433), c->$UC (15434)";;
  on)  for p in b c; do for s in upstream downstream; do untox $p $s; tox $p $s; done; done; echo "độ trễ BẬT: ${MS} ms khứ hồi";;
  off) for p in b c; do for s in upstream downstream; do untox $p $s; done; done; echo "độ trễ TẮT";;
  status) curl -s "$API/proxies" | python3 -c "import sys,json; [print(k, [ (t['name'],t['attributes']['latency']) for t in v['toxics']]) for k,v in json.load(sys.stdin).items()]" 2>/dev/null || curl -s "$API/proxies";;
esac
