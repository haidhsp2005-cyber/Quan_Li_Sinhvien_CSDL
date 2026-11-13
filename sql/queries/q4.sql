-- Q4: sinh viên có chứng chỉ ngoại ngữ overall >= 6.5 và speaking >= 6.0 (đọc từ jsonb)
SELECT DISTINCT student_id FROM all_certificate
WHERE cert_type = 'language'
  AND (detail->>'overall')::numeric >= 6.5
  AND (detail#>>'{skills,speaking}')::numeric >= 6.0
ORDER BY 1;
