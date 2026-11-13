-- Lược đồ tập trung Đề 2 (đúng sơ đồ Hình 2.1) — dùng cho CSDL đối chứng ref_central
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
  lecturer    text
);
CREATE TABLE student (
  student_id  integer PRIMARY KEY,
  full_name   text NOT NULL,
  birth_year  smallint,
  major_code  text,
  home_campus text NOT NULL,
  intake_year smallint
);
CREATE TABLE enrollment (
  enrollment_id integer PRIMARY KEY,
  student_id    integer NOT NULL REFERENCES student(student_id),
  section_id    integer NOT NULL REFERENCES section(section_id),
  semester      text NOT NULL,
  midterm       numeric,
  final         numeric,
  total         numeric
);
CREATE TABLE certificate (
  certificate_id integer PRIMARY KEY,
  student_id     integer NOT NULL REFERENCES student(student_id),
  cert_type      text NOT NULL,
  issued_date    date,
  detail         jsonb NOT NULL
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
