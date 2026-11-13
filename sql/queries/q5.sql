-- Q5: như Q4, đọc từ bảng quan hệ cert_language
SELECT DISTINCT c.student_id FROM all_certificate c JOIN all_cert_language l USING (certificate_id)
WHERE l.overall >= 6.5 AND l.speaking >= 6.0
ORDER BY 1;
