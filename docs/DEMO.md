# Kịch bản demo D1–D8 (12 phút) + giải thích N1–N5 (4 phút)

Chuẩn bị trước buổi bảo vệ (không tính vào 12 phút): máy B đã `docker compose --profile B up -d`; máy A đã `cp deploy.2machine.example.toml deploy.toml` và điền IP; có sẵn phương án Wi-Fi điện thoại; mở sẵn 3 cửa sổ: terminal ở thư mục repo, `http://localhost:8502` (dashboard), `http://localhost:8501` (nhập liệu). **Ảnh dự phòng** ở phụ lục slide nếu demo lỗi.

| Mã | Phút | Làm gì | Phải nói / thấy |
|---|---|---|---|
| D1 | 2 | `make down` rồi `make all MACHINE=A` (nếu đang chạy máy B thì giữ nguyên máy B); mở `make dash` | k = 3 trạm chạy; số dòng khớp dự kiến (student 7.548 / 4.784 / 2.668); dashboard đủ 3 ô xanh, ô B/C ghi “Máy B · IP” |
| D2 | 1 | `make check` | PASS cho ba quy tắc (đầy đủ / tái tạo được / rời nhau), PK duy nhất toàn hệ, FK, jsonb ↔ quan hệ, Q1–Q5 = đối chứng |
| D3 | 1,5 | `make q Q=1`, `make q Q=2`; `make q Q=1 EXPLAIN=1` | Q1 = đối chứng và **không có Foreign Scan** (nói: vì enrollment đi theo sinh viên); Q2 gộp 3 trạm |
| D4 | 1,5 | `make q Q=3`; `make q Q=3 EXPLAIN=1` | Q3 chạm cả 3 trạm vì sinh viên học ghép nằm ở trạm của họ (4 Foreign Scan, `Remote SQL` có `section_id = 2`) |
| D5 | 1 | `make q Q=4`, `make q Q=5` | cùng kết quả (cùng số dòng); nói thêm: Q4 gồm cả TOEIC nên đạt ngưỡng dễ |
| D6 | 1,5 | `make delay-on`; chạy lại Q1, Q2, Q3; `make delay-off` | Q1 gần như không đổi; Q2, Q3 tăng ≈ số vòng × 30 ms (~1 s) |
| D7 | 2 | Ở giao diện nhập liệu: (1) thêm sinh viên vào `campus_b`; (2) đăng ký liên vùng (sinh viên 1, lớp 2); (3) “thêm ngẫu nhiên 100 dòng”; rồi `make q Q=3` và `make check` | dashboard đổi ≤ 2 s đúng ô trạm; nhật ký ghi sự kiện; Q3 thấy dòng liên vùng mới; `make check` vẫn đạt |
| D8 | 1,5 | Trên máy B: `docker compose stop campus_c`; ở A: thử nhập vào campus_c, `make q Q=1`, `make q Q=2`; rồi `docker compose start campus_c` | dashboard đỏ rồi xanh; nhập báo lỗi (không ghi sang trạm khác); Q1 vẫn chạy; Q2 lỗi rồi chạy lại được khi trạm bật |

## N1–N5 (4 phút, 5 slide)
Xem `docs/KET_QUA_N1_N5.md` và `results/summary.md`. Trước buổi bảo vệ chạy lại `make data` (dữ liệu sạch) rồi `make bench` **trên 2 máy** để có số N3 giữa trạm cùng máy và trạm ở máy B, sau đó `python3 report/build.py` để cập nhật báo cáo và slide (sửa `MEASURED_ON` thành “2 máy”).

## Vấn đáp (9 phút) — mọi thành viên phải trả lời được
- Vì sao `enrollment` dẫn xuất theo student, không theo section? (Q1 buộc chạy 1 trạm.)
- `enrollment.section_id` chéo trạm xử lý thế nào, vì sao không dùng FK? (~7 %, kiểm ở tầng ghi + `make check`.)
- Khoá chính toàn hệ? (khối id riêng mỗi trạm.)
- Vì sao điều kiện jsonb của Q4 không đẩy xuống trạm xa còn Q5 thì được?
- Vì sao Q2, Q3 chậm gần 1 s khi trễ 30 ms dù ít dữ liệu? (số vòng khứ hồi, `use_remote_estimate`.)
- GIN có giúp Q4 không? (Không: `>=` trên số; chỉ giúp `@>`.)
