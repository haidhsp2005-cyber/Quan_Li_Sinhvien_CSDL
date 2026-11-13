-- Q1: điểm TB theo ngành của sinh viên cơ sở A, học kỳ 2025-2 (chạy trọn tại trạm A, không Foreign Scan)
SELECT s.major_code, round(avg(e.total), 2) AS diem_tb
FROM student s JOIN enrollment e USING (student_id)
WHERE s.home_campus = 'campus_a' AND e.semester = '2025-2'
GROUP BY 1 ORDER BY 1;
