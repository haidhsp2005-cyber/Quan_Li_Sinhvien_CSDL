-- Q2: tỉ lệ đạt (total >= 5) theo học phần, toàn trường, học kỳ 2025-2 (gộp 3 trạm)
SELECT sec.course_code, round(count(*) FILTER (WHERE e.total >= 5)::numeric / count(*), 4) AS ti_le_dat
FROM all_enrollment e JOIN all_section sec USING (section_id)
WHERE e.semester = '2025-2'
GROUP BY 1 ORDER BY 1;
