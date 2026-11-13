# Giải thích N1–N5 (nháp cho báo cáo)

Số liệu từ `make bench` (xem `results/summary.md`, `results/results.csv`, `results/explain_*.txt`). Đo trên **1 máy** (3 trạm là 3 container, cùng máy A): chưa có số "trạm máy B" thật; chạy lại `make bench` sau khi tách 2 máy để bổ sung N3. Đo 5 lần, bỏ lần đầu, lấy trung vị; trễ 30 ms = khứ hồi (toxiproxy, 15 ms mỗi chiều).

## N1 — Số dòng mỗi mảnh
`student` 7.548 / 4.784 / 2.668 = 50,3 % / 31,9 % / 17,8 % ≈ tỉ lệ đề `0,50 / 0,32 / 0,18` (bộ sinh chọn cơ sở theo trọng số này). `enrollment` (60.304 / 38.158 / 21.538) và `certificate` (6.085 / 3.854 / 2.061) chia theo sinh viên nên có cùng tỉ lệ. `section` (1.248 / 819 / 433) chia theo cơ sở mở lớp, cũng cùng trọng số. Tổng các mảnh = CSDL đối chứng; `course` nhân bản 300 dòng ở mỗi trạm.

## N2 — Số trạm mỗi truy vấn chạm
| Q | Trạm xa | Foreign Scan | Điều kiện đẩy xuống trạm xa |
|---|---|---|---|
| Q1 | 0 | 0 | không cần: bảng cục bộ của campus_a |
| Q2 | 2 | 4 (enrollment, section × b, c) | chỉ `semester='2025-2'` (kéo `section_id, total` của ~40.000 dòng về); nối và gom nhóm làm ở trung tâm. Bản `_opt` đẩy cả `GROUP BY section_id` xuống nên chỉ về ≤ 2.500 nhóm, nhưng vẫn 4 Foreign Scan vì còn đọc `section` |
| Q3 | 2 | 4 (bản `_opt`: 2) | chỉ `section_id = 2` ở `enrollment`; **bảng `student` bị kéo về toàn bộ** (`SELECT student_id, full_name FROM student`). Bản `_opt` đẩy phép nối enrollment ⋈ student xuống trạm xa (join pushdown), chỉ về 49 dòng |
| Q4 | 2 | 2 | chỉ `cert_type = 'language'` được đẩy xuống; **các điều kiện jsonb (`overall`, `speaking`) KHÔNG được đẩy**, nên cột `detail` của mọi chứng chỉ language (~5.400 dòng) chạy qua mạng rồi lọc ở trung tâm |
| Q5 | 2 | 4 (bản `_opt`: 2) | `overall >= 6.5 AND speaking >= 6.0` đẩy xuống `cert_language`, nhưng `certificate` bị kéo về toàn bộ (`certificate_id, student_id`). Bản `_opt` nối tại trạm xa và chỉ trả `student_id` |

Xem `Remote SQL:` trong `results/explain_*.txt`. Q1 duy nhất không có Foreign Scan. So sánh Q4 và Q5: điều kiện trên cột quan hệ đẩy được xuống trạm xa, còn biểu thức jsonb ép kiểu thì không.

## N3 — Thời gian Q1–Q3, không trễ / trễ 30 ms
Q1 8,1 → 12,9 ms (chênh 4,8 ms là nhiễu). Q2 40 → 1.030 ms, Q3 13 → 972 ms (bản `_opt` 9 → 770 ms). Chênh ≈ **số vòng khứ hồi × 30 ms**: Q2 ≈ 33 vòng, Q3 ≈ 32 vòng. Mỗi Foreign Scan tốn nhiều vòng (mở giao dịch xa, khai báo con trỏ, lấy từng lô 10.000 dòng, đóng), cộng thêm các lệnh `EXPLAIN` gửi sang trạm xa lúc lập kế hoạch vì `use_remote_estimate = true`.
Thí nghiệm (tắt `use_remote_estimate`, rồi trả lại giá trị cũ): có trễ, Q2 1.025 → 571 ms, Q3_opt 770 → 320 ms, Q4 458 → 335 ms; tức khoảng 10–15 vòng/truy vấn chỉ để ước lượng kế hoạch. Không đổi mặc định để giữ bản đo ban đầu.
Q4 chạm ít Foreign Scan nhất nên tăng ít nhất (+442 ms ≈ 15 vòng). Số vòng tăng theo số Foreign Scan, không theo lượng dữ liệu: Q1 không có Foreign Scan nên gần như không đổi.
Trạm cùng máy với trạm ở máy B: **chưa đo được** (đang chạy 1 máy).

## N4 — Tỉ lệ dòng liên vùng
8.423 / 120.000 = **7,02 %** (`CROSS = 0,07` trong bộ sinh). Theo thiết kế, `enrollment` đi theo sinh viên nên dòng liên vùng nằm ở trạm của sinh viên còn lớp ở trạm khác; do đó Q3 (sinh viên của một lớp ở campus_b) phải hỏi cả campus_a và campus_c. Lớp 2: 49 dòng, trong đó 47 ở campus_b và 2 dòng ở trạm khác (≈ 4 %; trung bình các lớp ở campus_b là 7,3 %).
Dự đoán khi tỉ lệ lên 30 %: số dòng lấy từ trạm xa tăng ≈ 4,3 lần (0,30 / 0,0702) nhưng số vòng khứ hồi không đổi (vẫn 2 trạm xa) nên thời gian Q3 tăng rất ít, chủ yếu theo số dòng chuyển qua mạng; đây là **dự đoán, chưa đo**.

## N5 — Dung lượng jsonb và bảng quan hệ, có/không GIN
`certificate` có cột jsonb: 3,07 MB (bảng 2,43 MB, riêng cột `detail` 1,67 MB) so với 5 bảng quan hệ tương đương 3,09 MB (bảng 2,16 MB): chênh lệch nhỏ. jsonb lưu lặp tên khoá ở mỗi dòng nhưng chỉ cần một bảng; bảng quan hệ không lặp khoá nhưng tốn tiêu đề dòng và chỉ mục khoá chính cho từng bảng trong 5 bảng.
GIN (`jsonb_path_ops`) thêm 0,57 MB (3 trạm). GIN **không giúp Q4** (điều kiện `>=` trên số không dùng được GIN; kế hoạch không chọn `bench_gin`, Q4 23,8 → 30,9 ms). GIN chỉ giúp phép chứa (`@>`): Q4b (IELTS, speaking 8.0) dùng Bitmap Index Scan, 7,3 → 6,5 ms; với 12.000 dòng thì lợi ích rất nhỏ. Bảng quan hệ cho Q5b 13,4 ms.

## Lưu ý trung thực
- Q4 gồm cả TOEIC (thang 990) nên `overall >= 6.5` luôn đúng với TOEIC: 2.678 / 3.676 dòng kết quả ở bộ nạp gốc là TOEIC.
- Đo trên 1 máy qua Docker Desktop, số tuyệt đối chỉ để so sánh tương đối.
