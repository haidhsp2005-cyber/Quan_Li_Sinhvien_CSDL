# Kế hoạch Đề 2 — Quản lý sinh viên liên cơ sở (3 trạm)

Seed 284617 · trạm: `campus_a` (trung tâm, 0,50) · `campus_b` (0,32) · `campus_c` (0,18)
Bộ sinh: `datagen/CS5104_Project_DataGen/de02_university/generate.py` (không sửa)

## 0. Số liệu thật từ bộ sinh (chạy `--size lab`)

| Bảng | Dòng | | Theo vùng | A | B | C |
|---|---|---|---|---|---|---|
| course | 300 | | student.home_campus | 7.548 | 4.784 | 2.668 |
| section | 2.500 | | section.campus | 1.248 | 819 | 433 |
| student | 15.000 | | enrollment liên vùng | 8.423 / 120.000 = 7,02 % | | |
| enrollment | 120.000 | | certificate language / it / research | 5.439 / 4.178 / 2.383 | | |
| certificate | 12.000 | | cert_it_module 9.725 · cert_research_coauthor 3.587 | | | |

**Phát hiện cần lưu ý**
1. Máy này chạy được `py -3` nhưng phải đặt `PYTHONUTF8=1`, nếu không `print` lỗi `cp1252` (CSV vẫn ghi xong trước đó). Máy chưa có `make`, `psql`; có Docker và WSL.
2. **Q4 có bẫy dữ liệu**: `overall >= 6.5 AND speaking >= 6.0` trên cả IELTS (thang 9) lẫn TOEIC (overall tới 990, speaking tới 495). Trong 3.676 dòng kết quả, **2.678 là TOEIC** (đương nhiên đạt). Cứ giữ đúng đề (Q4 và Q5 phải cùng kết quả) nhưng nêu rõ trong báo cáo; có thể đo thêm biến thể `test='IELTS'`.

## 1. Thiết kế phân tán (M1 – 1,5 điểm)

| Bảng | Cách chia | Mảnh/ vị trí | Lập luận |
|---|---|---|---|
| `course` | **Sao chép** ra cả 3 trạm | giống nhau | 300 dòng, ít ghi, mọi trạm cần để join; không chia |
| `student` | **Ngang nguyên thuỷ** theo `home_campus` | `student_x` ở trạm x | đúng định nghĩa "vùng" của đề |
| `section` | **Ngang nguyên thuỷ** theo `campus` | ở trạm x | lớp thuộc cơ sở mở lớp (đề ghi sẵn `section.campus` trong summary) |
| `enrollment` | **Ngang dẫn xuất theo `student`** (qua `student_id`) | cùng trạm sinh viên | **Q1 buộc chạy trọn tại một trạm** → enrollment phải đi theo sinh viên. Hệ quả: dòng liên vùng (7 %) nằm ở trạm sinh viên, còn lớp ở trạm khác |
| `certificate` | Dẫn xuất theo `student` | cùng trạm sinh viên | Q4/Q5 join student ⋈ certificate chạy cục bộ từng trạm |
| `cert_language/it/research` | Dẫn xuất theo `certificate` | cùng trạm | quan hệ 1–0..1 giữ cùng chỗ cha |
| `cert_it_module`, `cert_research_coauthor` | Dẫn xuất theo cha tương ứng | cùng trạm | |

**Cấp phát máy:** Máy A = `campus_a` (cổng 5432) + CSDL đối chứng `ref_central` + giao diện + dashboard. Máy B = `campus_b` (5432) + `campus_c` (5433). B có 2 trạm nên D8 tắt 1 trạm mà trạm còn lại vẫn sống; N3 so được "trạm cùng máy" với "trạm máy B".

**Khoá chính duy nhất toàn hệ:** dữ liệu nạp giữ id 1..N. Dòng thêm mới lấy id từ **khối riêng mỗi trạm** bằng sequence (A: 1.000.001+, B: 2.000.001+, C: 3.000.001+, có `MAXVALUE`) cho `section_id, student_id, enrollment_id, certificate_id`. `course_code` là khoá tự nhiên, sinh ở A rồi ghi ra cả 3. Tương lai có thể thêm `CHECK` khoảng id theo trạm.

**Khoá ngoại sau khi chia**
| FK | Cùng trạm? | Xử lý |
|---|---|---|
| enrollment.student_id → student, certificate.student_id → student | Có (dẫn xuất) | FK thật |
| cert_*.certificate_id → certificate, module/coauthor → cha | Có | FK thật |
| section.course_code → course | Có (course nhân bản) | FK thật |
| **enrollment.section_id → section** | **Chỉ ~93 %** | Không có FK thật cho 7 % liên vùng. Kiểm tra lúc ghi (UI tra trạm của lớp trong cùng giao dịch) + `make check` đếm mồ côi qua `all_*` = 0 |

**CHECK mảnh:** `student: CHECK (home_campus='campus_x')`, `section: CHECK (campus='campus_x')`. Bảng dẫn xuất không có cột vùng và không thêm cột → "chỉ nhận đúng dòng" được bảo đảm bằng FK cục bộ tới `student`/`certificate` (mảnh cha đã có CHECK). **CHECK jsonb** trên `certificate`: `cert_type IN ('language','it','research')` và dạng `detail` khớp loại (language: có `test`, `overall`, `skills` với 4 khoá; it: `name`, `level`, `modules` là mảng; research: `title`, `venue`, `role`, `coauthors` là mảng).

**Liên vùng:** Q1 = 1 trạm (A); Q2, Q4, Q5 = cả 3 trạm (không có điều kiện vùng); Q3 = lớp mở ở B nhưng sinh viên học ghép nằm ở A/C → chạm cả B (≈93 % dòng) lẫn A, C (≈7 %), chi phí tăng theo tỉ lệ liên vùng (N4).

**Cách viết truy vấn tập trung** (trạm trung tâm = `campus_a`, bảng cục bộ tên `student`, `enrollment`, …; foreign table `*_b`, `*_c` trong schema `remote_b/remote_c`; `all_<bảng>` = `UNION ALL`):
- Q1: dùng bảng cục bộ → `EXPLAIN` không có Foreign Scan.
- Q2: gom trước theo `section_id` ở từng trạm (≤ 2.500 nhóm) rồi ghép với `all_section` → map ra `course_code`; nhờ vậy dòng liên vùng vẫn đúng và ít dữ liệu qua mạng.
- Q3: lọc `section_id = <lớp cố định ở B>` đẩy xuống từng trạm, join `student` cục bộ.
- Q4/Q5: join student ⋈ certificate (hoặc `cert_language`) chạy cục bộ rồi gộp; Q4 `(detail->'skills'->>'speaking')::numeric`, thêm GIN `jsonb_path_ops` cho N5.

## 2. Việc cần làm (theo thứ tự)

| # | Việc | Sản phẩm | Kiểm tra |
|---|---|---|---|
| 1 | Môi trường: Docker Desktop trên cả 2 máy (hoặc PG 18 native), LAN, mở cổng, phương án Wi-Fi điện thoại | `deploy.toml`, `docker-compose.yml` | máy A `psql` được vào B |
| 2 | `schema_central.sql` đúng sơ đồ (10 bảng, kiểu smallint/numeric/date/jsonb) + `ref_central` nạp COPY CSV mini & lab | `sql/schema_central.sql` | số dòng khớp `summary.json` |
| 3 | `schema_site.sql` (CHECK, FK, sequence theo trạm) + script chia CSV → mảnh (`split_load.py`, tách theo `student→home_campus`, theo `section.campus`) và nạp từng trạm bằng `COPY` | `scripts/split_load.py` | tổng 3 trạm = đối chứng |
| 4 | `postgres_fdw` ở trung tâm + `all_<bảng>` cho 10 bảng; `make link` | `sql/fdw_central.sql`, `views_all.sql` | `SELECT count(*) FROM all_student` = 15.000 |
| 5 | `make check` (D2): đầy đủ / tái tạo được / rời nhau, PK duy nhất toàn hệ, FK mồ côi, jsonb ↔ bảng quan hệ khớp, so Q1–Q5 với `ref_central` | `scripts/check.py` | toàn xanh |
| 6 | Q1–Q5 trên `all_*`, kiểm kết quả giống `ref_central` (D3–D5) | `sql/queries/` | Q1 không Foreign Scan |
| 7 | Giao diện nhập liệu (Streamlit): thêm student / enrollment (kể cả **liên vùng**) / certificate theo loại (form động); ghi `certificate.detail` + bảng quan hệ trong **1 transaction** thẳng vào đúng trạm; báo "trạm / máy"; trạm chết → báo lỗi, không ghi sang trạm khác; nút "thêm ngẫu nhiên N dòng" | `app/entry.py` | D7, D8 |
| 8 | Dashboard (≤ 2 s): ô mỗi trạm (máy, IP, xanh/đỏ, số dòng từng bảng, đọc **thẳng từng trạm**), bảng tổng hợp so với đối chứng, nhật ký sự kiện (dòng mới, mất/kết nối lại; lưu RAM/tệp, **không thêm bảng**) | `app/dash.py` | D1, D7, D8 |
| 9 | Độ trễ 30 ms: proxy/toxiproxy đứng trước trạm B-C, `delay-on/off`; fdw trỏ qua proxy | `make delay-on` | Q2, Q3 tăng, Q1 không |
| 10 | `make bench`: mỗi truy vấn 5 lần bỏ lần đầu lấy trung vị → `results/results.csv` + `EXPLAIN (ANALYZE, VERBOSE)` Q1–Q5; N1–N5 (kể cả dung lượng jsonb vs quan hệ, có/không GIN) | `results/` | |
| 11 | `make all` chạy từ máy sạch; `make down`; README dựng lại | `Makefile` | thử từ đầu trên 2 máy |
| 12 | Báo cáo PDF ≤ 10 trang, slide, GitHub tag `final`, tập demo D1–D8 | | |

Lệnh bắt buộc: `up MACHINE=A|B · data · link · check · bench · delay-on/off · entry · dash · all · down`. Windows không có `make` → dùng WSL2 hoặc `choco install make`; chốt sớm để cả nhóm cùng chạy được.

## 3. Giải thích N1–N5 cần chuẩn bị

- **N1** tỉ lệ 50/32/18 từ `WEIGHTS`; enrollment/certificate chia theo sinh viên nên cũng ≈ 50/32/18 (≈ 60k/38k/22k); section tách riêng nhưng cùng trọng số; tổng = đối chứng.
- **N2** Q1 = 0 trạm xa; Q2/Q4/Q5 = 2 trạm xa (+ trung tâm); Q3 = 2 trạm xa. Đọc `EXPLAIN (VERBOSE)`: điều kiện nào vào `Remote SQL`.
- **N3** thời gian Q1–Q3 không trễ và có 30 ms; = số vòng khứ hồi × 30 ms; so trạm cùng máy với trạm máy B.
- **N4** 7,02 % liên vùng; vì enrollment đi theo sinh viên nên Q3 phải sang trạm khác lấy phần này; dự đoán và đo khi nâng lên 30 % (cần tự dựng thêm dữ liệu mà không sửa generator — chỉ để thí nghiệm, hoặc dự đoán bằng mô hình).
- **N5** jsonb nén TOAST vs bảng quan hệ; GIN làm Q4 nhanh hơn nhưng tăng dung lượng và chậm ghi.

## 4. Phân công gợi ý (4 người; 3 người gộp 3 và 4)

| Người | Phần | Việc # |
|---|---|---|
| 1 | Thiết kế, SQL schema, CHECK/FK, báo cáo mục (i) | 2, 3, 5 |
| 2 | Hạ tầng 2 máy, Makefile, fdw, độ trễ | 1, 4, 9, 11 |
| 3 | Giao diện nhập + dashboard | 7, 8 |
| 4 | Truy vấn, bench, N1–N5, slide | 6, 10, 12 |

Mọi thành viên phải hiểu toàn hệ (vấn đáp chỉ định người trả lời) → chéo kiểm tra code ở mốc 5 và 8.

## 5. Mốc thời gian (hạn do giảng viên thông báo; tuần tính lùi từ hạn)

T-5: #1–3 · T-4: #4–6 · T-3: #7–8 · T-2: #9–10 · T-1: #11–12, tập dượt D1–D8 hai máy · bảo vệ: 25 phút (demo 12 / slide N1–N5 4 / vấn đáp 9).

## 6. Rủi ro

- Hệ chỉ chạy trên 1 máy → M2 tối đa 1,75; không dựng được tại buổi bảo vệ → 0,75. Chuẩn bị Wi-Fi điện thoại và thử `make all` từ máy sạch.
- Phụ lục B / `cs5104_labs/lan/` (chạy nhiều máy qua LAN) chưa có trong tệp đã nhận — cần lấy từ giảng viên.
- Ghi rõ vào README việc dùng công cụ AI (đề cho phép nhưng bắt buộc khai báo).
