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
| Tách 2 máy qua LAN, `deploy.toml` | **Chưa** |
| Giao diện nhập liệu, dashboard | **Chưa** |
| `make check` đầy đủ (3 quy tắc đúng đắn, PK/FK), `bench`, `delay-on/off`, `entry`, `dash` | **Chưa** (hiện `make check` mới so số dòng) |

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
| `make check` | So tổng số dòng `all_*` với `ref_central` |
| `make down` | Xoá container và volume |

Dùng `SIZE=mini` để kiểm tra bằng mắt. Mật khẩu Postgres `cs5104` chỉ dành cho môi trường thử.

Vào thử: `docker compose exec campus_a psql -U postgres -d uni` (bảng cục bộ `student`, … và `all_student`, …).

## Triển khai trên 2 máy (dự kiến, chưa kiểm thử)

Máy A: `make up MACHINE=A` (chạy `campus_a`). Máy B: `make up MACHINE=B` (chạy `campus_b`, `campus_c`).
Máy B cần công bố cổng 5433/5434 ra LAN (Windows + WSL2: chuyển tiếp cổng hoặc `networkingMode=mirrored` trong `.wslconfig`, mở tường lửa). Tạo link bằng IP máy B:

```bash
make link HOSTB=<IP máy B> PORTB=5433 HOSTC=<IP máy B> PORTC=5434
```

Cần đối chiếu với Phụ lục B / `cs5104_labs/lan/` của giảng viên khi có tài liệu đó.

## Cấu trúc

```
docker-compose.yml        3 trạm (profile A / B / all)
sql/schema_central.sql    lược đồ tập trung (đối chứng)
sql/schema_site.sql       lược đồ một trạm: CHECK mảnh, CHECK jsonb, sequence khối id
sql/fdw_central.sql       postgres_fdw + all_<bảng>
scripts/split.py          chia CSV theo trạm (student→home_campus, section→campus, còn lại dẫn xuất)
scripts/gen.sh, load.sh, check_counts.sh
docs/PLAN.md              thiết kế phân tán và kế hoạch
```

## Thiết kế tóm tắt

`course` nhân bản; `student`/`section` chia ngang theo `home_campus`/`campus`; `enrollment`, `certificate` và các bảng con đi theo sinh viên (Q1 chạy trọn tại một trạm). Khoá chính mới lấy từ khối id riêng mỗi trạm (A 1.000.001+, B 2.000.001+, C 3.000.001+). `enrollment.section_id` không có FK thật cho ~7 % dòng liên vùng; kiểm tra ở tầng ghi và bằng `make check`.

## Công cụ AI

Mã và tài liệu được viết có hỗ trợ Claude (Anthropic); thành viên nhóm đọc và chịu trách nhiệm về toàn bộ hệ.
