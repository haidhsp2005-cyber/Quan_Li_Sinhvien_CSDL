# Makefile (chạy trong WSL/Git Bash). Biến: SIZE=mini|lab, DATAGEN=<thư mục bộ sinh>, PY=python3
SIZE ?= lab
PY ?= python3
export COMPOSE_PROFILES PY

up:      ## make up MACHINE=A|B|all  (thử 1 máy: MACHINE=all)
	COMPOSE_PROFILES=$(or $(MACHINE),all) docker compose up -d --wait
data:    ## sinh CSV, chia mảnh, tạo schema, nạp ref_central + 3 trạm
	DATAGEN=$(DATAGEN) bash scripts/gen.sh $(SIZE)
	bash scripts/load.sh $(SIZE)
link:    ## proxy độ trễ + postgres_fdw + all_* ở trạm trung tâm (fdw đi qua toxiproxy :15433/:15434)
	bash scripts/delay.sh setup
	MSYS_NO_PATHCONV=1 COMPOSE_PROFILES=all docker compose exec -T campus_a psql -U postgres -d uni -v ON_ERROR_STOP=1 -q \
	  -v hostb=$(or $(HOSTB),toxiproxy) -v portb=$(or $(PORTB),15433) -v hostc=$(or $(HOSTC),toxiproxy) -v portc=$(or $(PORTC),15434) \
	  -f /sql/fdw_central.sql
check:   ## kiểm tra đầy đủ: 3 quy tắc, PK/FK, CHECK, jsonb, Q1-Q5 vs đối chứng
	$(PY) -X utf8 scripts/check.py
check-counts: ## chỉ so số dòng all_* với ref_central
	bash scripts/check_counts.sh
bench:   ## đo Q1-Q5 (không trễ / trễ 30 ms), N1-N5 -> results/
	$(PY) -X utf8 scripts/bench.py
q:       ## chạy truy vấn demo: make q Q=1..5   (thêm EXPLAIN=1 để xem kế hoạch)
	bash scripts/q.sh $(Q) $(if $(EXPLAIN),explain)
delay-on:  ## trễ 30 ms giữa trạm trung tâm và trạm xa
	bash scripts/delay.sh on
delay-off:
	bash scripts/delay.sh off
down:
	COMPOSE_PROFILES=$(or $(MACHINE),all) docker compose down -v
all: up data link check
.PHONY: up data link check check-counts bench q delay-on delay-off down all

entry:   ## giao diện nhập liệu http://localhost:8501
	streamlit run app/entry.py --server.port 8501
dash:    ## dashboard http://localhost:8502
	streamlit run app/dash.py --server.port 8502
.PHONY: entry dash
