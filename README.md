# CS5104 — Đề 2: Quản lý sinh viên liên cơ sở (3 trạm PostgreSQL 18)

Project nhóm môn Hệ cơ sở dữ liệu nâng cao. Seed đề: `284617`. Ba trạm: `campus_a` (trung tâm), `campus_b`, `campus_c`.
Thiết kế phân tán và lập luận: [docs/PLAN.md](docs/PLAN.md).

## Tình trạng

| Hạng mục | Trạng thái |
|---|---|
| 3 trạm Postgres 18 bằng Docker | Xong (thử trên 1 máy) |
| `schema_central.sql`, schema từng trạm (CHECK mảnh, CHECK jsonb, sequence khối id) | Xong |
| Sinh dữ liệu, chia mảnh, nạp 3 trạm + `ref_central` | Xong, số dòng khớp `summary.json` |
| `postgres_fdw` + `all_<bảng>` | Xong |
| Q1–Q5 | Đã kiểm kết quả Q2–Q5 giống đối chứng, Q1 không Foreign Scan; chưa đóng gói thành tệp `sql/queries/` |
| Tách 2 máy qua LAN | Code và hướng dẫn xong, đã mô phỏng bằng IP LAN (check đạt); **chưa thử trên máy B thật** |
| Giao diện nhập liệu (`app/entry.py`) | Xong, đã thử trên 1 máy: sinh viên, đăng ký (kể cả liên vùng), chứng chỉ jsonb (một giao dịch), thêm ngẫu nhiên N dòng, báo lỗi khi trạm mất kết nối |
| Dashboard (`app/dash.py`) | Xong, đã thử trên 1 máy: ô từng trạm, tổng hợp so với đối chứng, nhật ký sự kiện, làm mới 2 giây. Chưa kiểm hết nhật ký lúc tắt/bật trạm |
| `make check` đầy đủ (3 quy tắc, PK/FK, CHECK, jsonb, Q1–Q5) | Xong, đã thử: toàn PASS; cố ý phá dữ liệu (trùng PK, lớp mồ côi) thì báo FAIL đúng chỗ |
| `bench`, `delay-on/off` | Xong, đã chạy trên 1 máy (chưa có số "trạm máy B"); xem docs/KET_QUA_N1_N5.md |

## Yêu cầu

- Docker Desktop (WSL2 backend) hoặc Docker Engine; `docker compose` v2.
- `make`, `bash`, Python ≥ 3.11 (chỉ thư viện chuẩn). Trên Windows chạy trong WSL2 (`sudo apt install make`) hoặc Git Bash.
- Bộ sinh dữ liệu của giảng viên `CS5104_Project_DataGen` đã giải nén (**không sửa `generate.py`**; không đưa vào repo).

## Dựng lại hệ thống (thử trên 1 máy)

```bash
git clone https://github.com/haidhsp2005-cyber/Quan_Li_Sinhvien_CSDL.git
cd Quan_Li_Sinhvien_CSDL
export DATAGEN=/đường/dẫn/CS5104_Project_DataGen      # thư mục chứa de02_university/

make all SIZE=lab MACHINE=all    # = up + data + link + check
```

Từng bước:

| Lệnh | Việc làm |
|---|---|
| `make up MACHINE=all` | Dựng 3 container: `campus_a` :5432, `campus_b` :5433, `campus_c` :5434 |
| `make data SIZE=lab` | Sinh CSV (seed cố định), chia mảnh theo trạm (`data/<size>/<trạm>/`), tạo schema, nạp `ref_central` (CSDL đối chứng, trong container A) và 3 trạm |
| `make link` | Tạo `postgres_fdw` và các khung nhìn `all_<bảng>` ở trạm trung tâm |
| `make check` | Kiểm tra đầy đủ (~1 phút): 3 quy tắc đúng đắn (đầy đủ / tái tạo được / rời nhau) cho 9 bảng chia, PK duy nhất toàn hệ, `course` nhân bản giống nhau, mảnh đúng vùng, FK cục bộ và `enrollment.section_id` liên vùng, jsonb ↔ bảng quan hệ, Q1–Q5 giống `ref_central` (Q1 không Foreign Scan, Q4 = Q5). Chỉ so với đối chứng các dòng nạp (id < 1.000.000); dòng thêm qua giao diện chỉ phải thoả quy tắc cấu trúc. Cần `pip install -r requirements.txt` |
| `make check-counts` | Chỉ so tổng số dòng `all_*` với `ref_central` (sau khi nhập thêm dòng sẽ lệch, là bình thường) |
| `make down` | Xoá container và volume |

| `make entry` | Giao diện nhập liệu http://localhost:8501 |
| `make dash` | Dashboard http://localhost:8502 |

Cài thư viện cho giao diện: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`. Trạm, máy, IP, cổng cấu hình ở `deploy.toml`. Nếu cổng 5432–5434 hoặc 8501/8502 đã bị dự án khác dùng, đổi trong `docker-compose.yml`, `deploy.toml` và `Makefile`. Khi không dùng: `docker compose --profile all stop` (giữ dữ liệu).

Dùng `SIZE=mini` để kiểm tra bằng mắt. Mật khẩu Postgres `cs5104` chỉ dành cho môi trường thử.

Vào thử: `docker compose exec campus_a psql -U postgres -d uni` (bảng cục bộ `student`, … và `all_student`, …).

## Triển khai trên 2 máy (LAN)

Máy A: `campus_a` (trung tâm), `ref_central`, giao diện, dashboard, toxiproxy, thư mục `data/`. Máy B: `campus_b` + `campus_c`. **Máy B chỉ cần Docker và `docker-compose.yml`** (không cần dữ liệu hay Python): dữ liệu được nạp từ máy A qua LAN.

**Trên máy B**
1. Lấy IP LAN (`ipconfig` → IPv4). Mở tường lửa (PowerShell chạy Admin):
   ```powershell
   New-NetFirewallRule -DisplayName "csdl-pg" -Direction Inbound -Protocol TCP -LocalPort 5433,5434 -Action Allow
   ```
2. Dựng 2 trạm: `docker compose --profile B up -d --wait` (hoặc `make up MACHINE=B`). Docker Desktop công bố cổng ra IP của máy Windows. Nếu Docker chạy trực tiếp trong WSL2 (không qua Docker Desktop), cần `networkingMode=mirrored` trong `.wslconfig` hoặc `netsh interface portproxy`.

**Trên máy A**
1. `cp deploy.2machine.example.toml deploy.toml` rồi thay `<IP_MAY_B>` bằng IP máy B.
2. Kiểm tra thông mạng: `nc -vz <IP_MAY_B> 5433` (PowerShell: `Test-NetConnection <IP_MAY_B> -Port 5433`).
3. `make all MACHINE=A` (dựng A, nạp dữ liệu vào cả 3 trạm qua LAN, tạo fdw qua toxiproxy, `make check`).
4. `make dash` — mỗi ô trạm hiển thị đúng máy và IP; `make bench` để đo trạm ở máy B (N3).

**Lưu ý**
- Mật khẩu `cs5104` chỉ dùng trong mạng LAN thử nghiệm.
- Wi-Fi một số nơi cô lập các thiết bị với nhau (client isolation): dùng điểm phát Wi-Fi điện thoại hoặc cáp mạng làm phương án dự phòng cho buổi bảo vệ.
- Độ trễ 30 ms đặt ở máy A (toxiproxy đứng trước `postgres_fdw`), cộng thêm độ trễ LAN thật.
- Đã kiểm thử bằng cách trỏ `campus_b/c` tới IP LAN của chính máy A (đường mạng/IP thật): `make check` đạt toàn bộ. **Chưa thử trên máy B thật.**
- Cần đối chiếu với Phụ lục B / `cs5104_labs/lan/` của giảng viên khi có tài liệu đó.

## Cấu trúc

```
docker-compose.yml        3 trạm (profile A / B / all)
sql/schema_central.sql    lược đồ tập trung (đối chứng)
sql/schema_site.sql       lược đồ một trạm: CHECK mảnh, CHECK jsonb, sequence khối id
sql/fdw_central.sql       postgres_fdw + all_<bảng>
scripts/split.py          chia CSV theo trạm (student→home_campus, section→campus, còn lại dẫn xuất)
scripts/gen.sh, load.sh, check_counts.sh
app/common.py             kết nối trạm, ghi dữ liệu (jsonb + bảng quan hệ một giao dịch)
app/entry.py, dash.py     giao diện nhập liệu và dashboard (Streamlit)
deploy.toml               trạm → máy, IP, cổng
docs/PLAN.md              thiết kế phân tán và kế hoạch
```

## Thiết kế tóm tắt

`course` nhân bản; `student`/`section` chia ngang theo `home_campus`/`campus`; `enrollment`, `certificate` và các bảng con đi theo sinh viên (Q1 chạy trọn tại một trạm). Khoá chính mới lấy từ khối id riêng mỗi trạm (A 1.000.001+, B 2.000.001+, C 3.000.001+). `enrollment.section_id` không có FK thật cho ~7 % dòng liên vùng; kiểm tra ở tầng ghi và bằng `make check`.

## Công cụ AI

Mã và tài liệu được viết có hỗ trợ Claude (Anthropic); thành viên nhóm đọc và chịu trách nhiệm về toàn bộ hệ.

## Đo hiệu năng và độ trễ

| Lệnh | Việc làm |
|---|---|
| `make delay-on` / `make delay-off` | Bật/tắt trễ 30 ms khứ hồi giữa trạm trung tâm và các trạm xa (toxiproxy; `postgres_fdw` đi qua proxy :15433/:15434 nên `make link` tạo proxy trước) |
| `make bench` | Đo Q1–Q5 (5 lần, bỏ lần đầu, trung vị) không trễ và có trễ, thu số liệu N1–N5 → `results/results.csv`, `results/explain_*.txt`, `results/summary.md`, `results/metrics.json` |

Giải thích N1–N5 (nháp báo cáo): [docs/KET_QUA_N1_N5.md](docs/KET_QUA_N1_N5.md). Nên chạy `make data` để về dữ liệu sạch trước khi đo. Hiện mới đo trên 1 máy.

## Báo cáo, slide, demo

| Tệp | Nội dung |
|---|---|
| `report/BaoCao_De2.pdf` | Báo cáo (A4, ≤ 10 trang): thiết kế phân tán, triển khai, dữ liệu, cách chạy, N1–N5, hạn chế, phân công, tài liệu tham khảo |
| `report/Slide_De2.pdf` | Slide bảo vệ (11 trang, gồm phụ lục ảnh dự phòng) |
| `docs/DEMO.md` | Kịch bản demo D1–D8 và câu hỏi vấn đáp |

Tạo lại bằng `python3 report/build.py` (cần Chrome/Edge; sửa `GROUP`, `MEMBERS`, `MEASURED_ON` đầu file). Chạy truy vấn demo: `make q Q=1..5` (thêm `EXPLAIN=1` để xem kế hoạch).
