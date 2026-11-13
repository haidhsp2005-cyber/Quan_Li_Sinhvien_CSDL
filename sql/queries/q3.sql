-- Q3: danh sách sinh viên của một lớp học phần mở ở cơ sở B (lớp 2), gồm cả sinh viên cơ sở khác học ghép
SELECT s.student_id, s.full_name, s.home_campus
FROM all_enrollment e JOIN all_student s USING (student_id)
WHERE e.section_id = 2
ORDER BY 1, 2;
