-- Lược đồ một trạm. Chạy: psql -v site=campus_a -v idbase=1000000 -f schema_site.sql
-- Khác lược đồ tập trung: CHECK mảnh, CHECK jsonb, bỏ FK enrollment.section_id (xem PLAN), sequence theo khối id.
CREATE TABLE course (
  course_code text PRIMARY KEY,
  name        text NOT NULL,
  credits     smallint NOT NULL
);
CREATE TABLE section (
  section_id  integer PRIMARY KEY,
  course_code text NOT NULL REFERENCES course(course_code),
  campus      text NOT NULL,
  semester    text NOT NULL,
  lecturer    text,
  CONSTRAINT section_fragment CHECK (campus = :'site')
);
CREATE TABLE student (
  student_id  integer PRIMARY KEY,
  full_name   text NOT NULL,
  birth_year  smallint,
  major_code  text,
  home_campus text NOT NULL,
  intake_year smallint,
  CONSTRAINT student_fragment CHECK (home_campus = :'site')
);
CREATE TABLE enrollment (
  enrollment_id integer PRIMARY KEY,
  student_id    integer NOT NULL REFERENCES student(student_id),   -- FK cục bộ => dòng thuộc mảnh của trạm
  section_id    integer NOT NULL,                                  -- lớp có thể ở trạm khác (liên vùng): kiểm tra ở tầng ghi + make check
  semester      text NOT NULL,
  midterm       numeric,
  final         numeric,
  total         numeric,
  CONSTRAINT enr_semester CHECK (semester IN ('2025-1','2025-2','2026-1'))
);
CREATE TABLE certificate (
  certificate_id integer PRIMARY KEY,
  student_id     integer NOT NULL REFERENCES student(student_id),
  cert_type      text NOT NULL,
  issued_date    date,
  detail         jsonb NOT NULL,
  CONSTRAINT cert_type_ok CHECK (cert_type IN ('language','it','research')),
  CONSTRAINT detail_shape CHECK (
    (cert_type = 'language' AND jsonb_typeof(detail) = 'object'
        AND detail ?& ARRAY['test','overall','skills']
        AND jsonb_typeof(detail->'skills') = 'object'
        AND detail->'skills' ?& ARRAY['listening','reading','writing','speaking'])
 OR (cert_type = 'it' AND detail ?& ARRAY['name','level','modules']
        AND jsonb_typeof(detail->'modules') = 'array')
 OR (cert_type = 'research' AND detail ?& ARRAY['title','venue','role','coauthors']
        AND jsonb_typeof(detail->'coauthors') = 'array'))
);
CREATE TABLE cert_language (
  certificate_id integer PRIMARY KEY REFERENCES certificate(certificate_id),
  test text, overall numeric, listening numeric, reading numeric, writing numeric, speaking numeric
);
CREATE TABLE cert_it (
  certificate_id integer PRIMARY KEY REFERENCES certificate(certificate_id),
  name text, level text
);
CREATE TABLE cert_it_module (
  certificate_id integer REFERENCES cert_it(certificate_id),
  module text,
  PRIMARY KEY (certificate_id, module)
);
CREATE TABLE cert_research (
  certificate_id integer PRIMARY KEY REFERENCES certificate(certificate_id),
  title text, venue text, role text
);
CREATE TABLE cert_research_coauthor (
  certificate_id integer REFERENCES cert_research(certificate_id),
  seq  smallint,
  name text,
  PRIMARY KEY (certificate_id, seq)
);

-- Khối id riêng mỗi trạm cho dòng thêm mới (dữ liệu nạp có id 1..N, không đụng khối này)
\set lo :idbase
SELECT (:idbase + 1) AS lo, (:idbase + 999999) AS hi \gset
CREATE SEQUENCE section_id_seq     START :lo MINVALUE :lo MAXVALUE :hi OWNED BY section.section_id;
CREATE SEQUENCE student_id_seq     START :lo MINVALUE :lo MAXVALUE :hi OWNED BY student.student_id;
CREATE SEQUENCE enrollment_id_seq  START :lo MINVALUE :lo MAXVALUE :hi OWNED BY enrollment.enrollment_id;
CREATE SEQUENCE certificate_id_seq START :lo MINVALUE :lo MAXVALUE :hi OWNED BY certificate.certificate_id;

-- Chỉ mục phục vụ truy vấn
CREATE INDEX enrollment_student_idx ON enrollment(student_id);
CREATE INDEX enrollment_section_idx ON enrollment(section_id);
CREATE INDEX enrollment_sem_idx     ON enrollment(semester);
CREATE INDEX certificate_student_idx ON certificate(student_id);
CREATE INDEX section_course_idx     ON section(course_code);
