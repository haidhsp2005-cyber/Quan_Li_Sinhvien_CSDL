# Kết quả đo — Đề 2

Mỗi truy vấn 5 lần, bỏ lần đầu, trung vị. Trễ = 30 ms khứ hồi (toxiproxy). Q3 dùng lớp 2 (mở ở campus_b). Biến thể `_opt` đẩy gom nhóm/nối xuống từng trạm; kết quả giống bản gốc: {'Q2_opt': True, 'Q3_opt': True, 'Q5_opt': True, 'Q4=Q5': True}.

## Q1–Q5

| Truy vấn | Không trễ (ms) | Trễ (ms) | Chênh (ms) | Vòng khứ hồi ước tính | Dòng | Trạm xa | Foreign Scan |
|---|---|---|---|---|---|---|---|
| Q1 | 8.13 | 12.89 | 4.8 | 0.2 | 6 | - | 0 |
| Q2 | 40.47 | 1029.98 | 989.5 | 33.0 | 232 | bc | 4 |
| Q2_opt | 32.66 | 986.47 | 953.8 | 31.8 | 232 | bc | 4 |
| Q3 | 12.8 | 972.3 | 959.5 | 32.0 | 49 | bc | 4 |
| Q3_opt | 9.29 | 770.16 | 760.9 | 25.4 | 49 | bc | 2 |
| Q4 | 17.59 | 459.27 | 441.7 | 14.7 | 3248 | bc | 2 |
| Q5 | 19.4 | 974.7 | 955.3 | 31.8 | 3248 | bc | 4 |
| Q5_opt | 19.54 | 912.91 | 893.4 | 29.8 | 3248 | bc | 2 |

## N1 — Số dòng mỗi mảnh

| Bảng | campus_a | campus_b | campus_c | Tổng | Đối chứng |
|---|---|---|---|---|---|
| course | 300 | 300 | 300 | nhân bản | 300 |
| section | 1248 | 819 | 433 | 2500 | 2500 |
| student | 7548 | 4784 | 2668 | 15000 | 15000 |
| enrollment | 60304 | 38158 | 21538 | 120000 | 120000 |
| certificate | 6085 | 3854 | 2061 | 12000 | 12000 |
| cert_language | 2719 | 1747 | 973 | 5439 | 5439 |
| cert_it | 2167 | 1330 | 681 | 4178 | 4178 |
| cert_it_module | 5059 | 3134 | 1532 | 9725 | 9725 |
| cert_research | 1199 | 777 | 407 | 2383 | 2383 |
| cert_research_coauthor | 1792 | 1176 | 619 | 3587 | 3587 |

## N4 — Liên vùng

- Dòng đăng ký liên vùng: 8423 / 120000 = 7.02 %
- Q3 (2): 49 dòng, theo trạm của sinh viên: {'campus_a': 1, 'campus_b': 47, 'campus_c': 1} → 2 dòng phải lấy từ trạm khác
- Với các lớp mở ở campus_b: 7.3 % đăng ký đến từ sinh viên cơ sở khác. Dự đoán tỉ lệ 30 %: số dòng xa ≈ ×4.27

## N5 — Dung lượng jsonb và GIN

- `certificate` (có cột jsonb): 3.07 MB gồm index; riêng bảng 2.43 MB; riêng cột detail 1.67 MB
- 5 bảng quan hệ tương đương: 3.09 MB gồm index; riêng bảng 2.16 MB
- GIN `jsonb_path_ops` trên detail (3 trạm): 0.57 MB

| Truy vấn | Không GIN (ms) | Có GIN (ms) | Dòng |
|---|---|---|---|
| Q4 | 23.75 | 30.94 | 3248 |
| Q4b | 7.31 | 6.5 | 329 |
| Q5b | 13.37 | 17.7 | 329 |

Kế hoạch Q4b có GIN: ['->  Bitmap Heap Scan on public.certificate  (cost=22.51..182.95 rows=193 width=4) (actual time=0.070..0.259 rows=176.00 loops=1)', '->  Bitmap Index Scan on bench_gin  (cost=0.00..22.47 rows=193 width=0) (actual time=0.046..0.047 rows=176.00 loops=1)']  
Kế hoạch Q4 có GIN dùng bench_gin: False
