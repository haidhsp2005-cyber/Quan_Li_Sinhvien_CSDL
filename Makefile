# Makefile (chạy trong WSL/Git Bash). Biến: SIZE=mini|lab, DATAGEN=<thư mục bộ sinh>
SIZE ?= lab
export COMPOSE_PROFILES

up:      ## make up MACHINE=A|B|all  (thử 1 máy: MACHINE=all)
	COMPOSE_PROFILES=$(or $(MACHINE),all) docker compose up -d --wait
data:    ## sinh CSV, chia mảnh, tạo schema, nạp ref_central + 3 trạm
	DATAGEN=$(DATAGEN) bash scripts/gen.sh $(SIZE)
	bash scripts/load.sh $(SIZE)
link:    ## postgres_fdw + all_* ở trạm trung tâm (campus_a)
	MSYS_NO_PATHCONV=1 COMPOSE_PROFILES=all docker compose exec -T campus_a psql -U postgres -d uni -v ON_ERROR_STOP=1 -q \
	  -v hostb=$(or $(HOSTB),campus_b) -v portb=$(or $(PORTB),5432) -v hostc=$(or $(HOSTC),campus_c) -v portc=$(or $(PORTC),5432) \
	  -f /sql/fdw_central.sql
check:   ## so số dòng all_* với ref_central
	bash scripts/check_counts.sh
down:
	COMPOSE_PROFILES=all docker compose down -v
all: up data link check
.PHONY: up data link check down all
