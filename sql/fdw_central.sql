-- Chạy trên campus_a / uni. psql -v hostb=campus_b -v portb=5432 -v hostc=campus_c -v portc=5432 -f fdw_central.sql
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

DROP SCHEMA IF EXISTS remote_b CASCADE; DROP SCHEMA IF EXISTS remote_c CASCADE;
DROP SERVER IF EXISTS srv_b CASCADE;    DROP SERVER IF EXISTS srv_c CASCADE;
CREATE SCHEMA remote_b; CREATE SCHEMA remote_c;

CREATE SERVER srv_b FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host :'hostb', port :'portb', dbname 'uni', use_remote_estimate 'true', fetch_size '10000');
CREATE SERVER srv_c FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host :'hostc', port :'portc', dbname 'uni', use_remote_estimate 'true', fetch_size '10000');
CREATE USER MAPPING FOR postgres SERVER srv_b OPTIONS (user 'postgres', password 'cs5104');
CREATE USER MAPPING FOR postgres SERVER srv_c OPTIONS (user 'postgres', password 'cs5104');

IMPORT FOREIGN SCHEMA public FROM SERVER srv_b INTO remote_b;
IMPORT FOREIGN SCHEMA public FROM SERVER srv_c INTO remote_c;

-- Khung nhìn toàn cục. course nhân bản nên all_course chỉ cần bản cục bộ.
CREATE OR REPLACE VIEW all_course AS SELECT * FROM public.course;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['section','student','enrollment','certificate','cert_language','cert_it',
                           'cert_it_module','cert_research','cert_research_coauthor'] LOOP
    EXECUTE format('CREATE OR REPLACE VIEW all_%1$s AS
                      SELECT * FROM public.%1$s UNION ALL SELECT * FROM remote_b.%1$s UNION ALL SELECT * FROM remote_c.%1$s', t);
  END LOOP;
END $$;
