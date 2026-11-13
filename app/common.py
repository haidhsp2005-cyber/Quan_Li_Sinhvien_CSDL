"""Dùng chung cho giao diện nhập liệu và dashboard: cấu hình trạm, kết nối, ghi dữ liệu."""
import datetime as dt
import json
import random
import tomllib
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

ROOT = Path(__file__).resolve().parent.parent
CFG = tomllib.loads((ROOT / "deploy.toml").read_text(encoding="utf-8"))
STATIONS = CFG["stations"]
SITES = list(STATIONS)
TABLES = ["course", "section", "student", "enrollment", "certificate", "cert_language", "cert_it",
          "cert_it_module", "cert_research", "cert_research_coauthor"]
SEMESTERS = ["2025-1", "2025-2", "2026-1"]
MAJORS = ["CNTT", "KHMT", "HTTT", "KTPM", "ATTT", "KHDL"]
IT_CERTS = {"MOS": ["Word", "Excel", "PowerPoint", "Access"],
            "IC3": ["Computing Fundamentals", "Key Applications", "Living Online"],
            "AWS": ["Cloud Concepts", "Security", "Technology", "Billing"]}
VENUES = ["Hội nghị FAIR", "Tạp chí Khoa học ĐH Tân Tạo", "Hội nghị KSE", "Hội nghị SoICT", "Tạp chí Tin học và Điều khiển"]


class StationDown(Exception):
    """Trạm không kết nối được; không bao giờ ghi sang trạm khác."""
    def __init__(self, site, reason=""):
        super().__init__(f"Trạm {site} không kết nối được. {reason}".strip())
        self.site = site


def where(site):
    s = STATIONS[site]
    return f"{site} · máy {s['machine']} · {s['host']}:{s['port']}"


def connect(site, dbname=None, timeout=2):
    s, d = STATIONS[site], CFG["db"]
    try:
        return psycopg2.connect(host=s["host"], port=s["port"], dbname=dbname or d["name"], user=d["user"],
                                password=d["password"], connect_timeout=timeout)
    except psycopg2.OperationalError as e:
        raise StationDown(site, str(e).strip().splitlines()[0])


def find_row(query, params):
    """Tìm một dòng ở các trạm: trả về (site, row) hoặc (None, None).
    Nếu không thấy mà có trạm mất kết nối thì báo lỗi (không kết luận 'không tồn tại')."""
    down = []
    for site in SITES:
        try:
            conn = connect(site)
        except StationDown as e:
            down.append(e); continue
        try:
            with conn, conn.cursor() as cur:
                cur.execute(query, params); row = cur.fetchone()
        finally:
            conn.close()
        if row:
            return site, row
    if down:
        raise StationDown(down[0].site, "Không tra được dòng vì có trạm mất kết nối: " + ", ".join(e.site for e in down))
    return None, None


# ---------------------------------------------------------------- ghi dữ liệu
def insert_student(cur, site, full_name, birth_year, major, intake_year):
    cur.execute("INSERT INTO student(student_id,full_name,birth_year,major_code,home_campus,intake_year) "
                "VALUES (nextval('student_id_seq'),%s,%s,%s,%s,%s) RETURNING student_id",
                (full_name, birth_year, major, site, intake_year))
    return cur.fetchone()[0]


def insert_enrollment(cur, student_id, section_id, semester, midterm, final):
    total = round(0.3 * midterm + 0.7 * final, 2)
    cur.execute("INSERT INTO enrollment(enrollment_id,student_id,section_id,semester,midterm,final,total) "
                "VALUES (nextval('enrollment_id_seq'),%s,%s,%s,%s,%s,%s) RETURNING enrollment_id",
                (student_id, section_id, semester, midterm, final, total))
    return cur.fetchone()[0]


def language_detail(test, listening, reading, writing, speaking):
    """Cùng quy tắc với bộ sinh: IELTS overall = trung bình làm tròn 0,5; TOEIC overall = nghe + đọc."""
    sk = {"listening": float(listening), "reading": float(reading), "writing": float(writing), "speaking": float(speaking)}
    if test == "IELTS":
        ov = round(round(sum(sk.values()) / 4 * 2) / 2, 1)
    else:
        ov = float(sk["listening"] + sk["reading"])
    return {"test": test, "overall": ov, "skills": sk}


def insert_certificate(cur, student_id, cert_type, issued_date, detail):
    """Ghi certificate (jsonb) và bản quan hệ tương đương trong CÙNG giao dịch của cursor."""
    cur.execute("INSERT INTO certificate(certificate_id,student_id,cert_type,issued_date,detail) "
                "VALUES (nextval('certificate_id_seq'),%s,%s,%s,%s) RETURNING certificate_id",
                (student_id, cert_type, issued_date, Json(detail, dumps=lambda o: json.dumps(o, ensure_ascii=False))))
    cid = cur.fetchone()[0]
    if cert_type == "language":
        k = detail["skills"]
        cur.execute("INSERT INTO cert_language VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (cid, detail["test"], detail["overall"], k["listening"], k["reading"], k["writing"], k["speaking"]))
    elif cert_type == "it":
        cur.execute("INSERT INTO cert_it VALUES (%s,%s,%s)", (cid, detail["name"], detail["level"]))
        for m in detail["modules"]:
            cur.execute("INSERT INTO cert_it_module VALUES (%s,%s)", (cid, m))
    else:
        cur.execute("INSERT INTO cert_research VALUES (%s,%s,%s,%s)", (cid, detail["title"], detail["venue"], detail["role"]))
        for i, n in enumerate(detail["coauthors"], 1):
            cur.execute("INSERT INTO cert_research_coauthor VALUES (%s,%s,%s)", (cid, i, n))
    return cid


# ---------------------------------------------------------------- ngẫu nhiên
def _pool(site):
    conn = connect(site)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT student_id FROM student ORDER BY random() LIMIT 300")
            st = [r[0] for r in cur.fetchall()]
            cur.execute("SELECT section_id, semester FROM section ORDER BY random() LIMIT 300")
            sec = cur.fetchall()
        return st, sec
    finally:
        conn.close()


def random_rows(n, rng=None):
    """Thêm n dòng ngẫu nhiên (sinh viên 15%, đăng ký 65% — ~7% liên vùng, chứng chỉ 20%).
    Mỗi dòng ghi đúng trạm của nó; trạm mất kết nối thì dòng đó thất bại, không chuyển sang trạm khác.
    Trả về (số dòng đã ghi theo trạm, lỗi theo trạm)."""
    rng = rng or random.Random()
    weights = [STATIONS[s]["weight"] for s in SITES]
    plan = {s: [] for s in SITES}          # công việc theo trạm đích
    for _ in range(n):
        site = rng.choices(SITES, weights)[0]
        kind = rng.choices(["student", "enrollment", "certificate"], [15, 65, 20])[0]
        plan[site].append(kind)
    pools, errors, written = {}, {}, {s: 0 for s in SITES}

    def pool(site):
        if site not in pools:
            pools[site] = _pool(site)
        return pools[site]

    for site, kinds in plan.items():
        if not kinds:
            continue
        try:
            conn = connect(site)
        except StationDown as e:
            errors[site] = f"{len(kinds)} dòng không ghi được: {e}"; continue
        try:
            with conn, conn.cursor() as cur:
                st_ids, _ = pool(site)
                for kind in kinds:
                    if kind == "student":
                        name = f"Ngẫu nhiên {rng.randint(1, 99999)}"
                        insert_student(cur, site, name, rng.randint(1998, 2007), rng.choice(MAJORS), rng.randint(2021, 2025))
                    elif kind == "enrollment":
                        osite = site
                        if rng.random() < 0.07:                         # liên vùng
                            osite = rng.choice([s for s in SITES if s != site])
                        try:
                            _, secs = pool(osite)
                        except StationDown as e:
                            errors[osite] = f"không đọc được lớp để ghi đăng ký liên vùng: {e}"; continue
                        sec, sem = rng.choice(secs)
                        insert_enrollment(cur, rng.choice(st_ids), sec, sem, round(rng.uniform(3, 10), 1), round(rng.uniform(3, 10), 1))
                    else:
                        t = rng.choices(["language", "it", "research"], [45, 35, 20])[0]
                        if t == "language":
                            test = rng.choice(["IELTS", "TOEIC"])
                            pick = (lambda: rng.choice([4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0])) if test == "IELTS" else (lambda: rng.randint(10, 99) * 5)
                            d = language_detail(test, pick(), pick(), pick(), pick())
                        elif t == "it":
                            nm = rng.choice(list(IT_CERTS))
                            d = {"name": nm, "level": rng.choice(["core", "expert", "associate"]),
                                 "modules": rng.sample(IT_CERTS[nm], rng.randint(1, len(IT_CERTS[nm])))}
                        else:
                            d = {"title": f"Nghiên cứu ngẫu nhiên {rng.randint(1, 99)}", "venue": rng.choice(VENUES),
                                 "role": rng.choice(["first_author", "coauthor"]),
                                 "coauthors": [f"Tác giả {rng.randint(1, 99)}" for _ in range(rng.randint(0, 3))]}
                        insert_certificate(cur, rng.choice(st_ids), t, dt.date(2025, 1, 1) + dt.timedelta(days=rng.randrange(545)), d)
                    written[site] += 1
        finally:
            conn.close()
    return written, errors
