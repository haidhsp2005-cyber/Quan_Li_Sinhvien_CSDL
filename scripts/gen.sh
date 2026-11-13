#!/usr/bin/env bash
# Sinh CSV tập trung bằng bộ sinh của giảng viên (KHÔNG sửa generate.py) rồi chia mảnh theo trạm.
# Dùng: DATAGEN=/đường/dẫn/CS5104_Project_DataGen scripts/gen.sh [mini|lab]
set -euo pipefail
SIZE=${1:-lab}
: "${DATAGEN:?Đặt DATAGEN tới thư mục CS5104_Project_DataGen đã giải nén}"
PY=${PY:-python3}
$PY -X utf8 "$DATAGEN/de02_university/generate.py" --size "$SIZE" --out "data/central/$SIZE" > /dev/null
rm -rf "data/$SIZE"
$PY -X utf8 scripts/split.py "data/central/$SIZE" "data/$SIZE"
