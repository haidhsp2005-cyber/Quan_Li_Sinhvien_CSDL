#!/usr/bin/env python3
"""make check (D2): kiểm tra thiết kế phân tán trên toàn hệ.
  1. Ba quy tắc đúng đắn cho mọi bảng bị chia: ĐẦY ĐỦ, TÁI TẠO ĐƯỢC, RỜI NHAU
  2. Khoá chính duy nhất trên toàn hệ; bảng nhân bản (course) giống nhau ở mọi trạm
  3. Mảnh đúng vùng (CHECK) và dòng dẫn xuất nằm cùng trạm với cha
  4. Khoá ngoại: cục bộ không mồ côi; enrollment.section_id tồn tại ở một trạm nào đó
  5. jsonb ↔ bảng quan hệ tương đương
  6. Q1–Q5 trên trạm trung tâm giống CSDL đối chứng (Q1 không Foreign Scan; Q4 = Q5)
So với ref_central chỉ xét dòng nạp từ bộ sinh (id < 1.000.000); dòng thêm qua giao diện chỉ phải thoả quy tắc cấu trúc.
"""
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import common as c  # noqa: E402

NEW = 1_000_000                      # id từ khối này trở lên là dòng thêm mới
# bảng chia: (tên, cột khoá chính, cột id số để lọc dòng nạp)
FRAG = [("section", ["section_id"]), ("student", ["student_id"]), ("enrollment", ["enrollment_id"]),
        ("certificate", ["certificate_id"]), ("cert_language", ["certificate_id"]), ("cert_it", ["certificate_id"]),
        ("cert_it_module", ["certificate_id", "module"]), ("cert_research", ["certificate_id"]),
        ("cert_research_coauthor", ["certificate_id", "seq"])]
fails = 0


def report(ok, name, detail=""):
    global fails
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def fetch(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params); return cur.fetchall()


def load(conn, table, pk):
    cols = ", ".join(pk)
    return {tuple(str(x) for x in r[:-1]): r[-1] for r in fetch(conn, f"SELECT {cols}, t::text FROM {table} t")}


def main():
    try:
        conns = {s: c.connect(s) for s in c.SITES}
        ref = c.connect("campus_a", dbname="ref_central")
    except c.StationDown as e:
        print(f"FAIL  Không kết nối được: {e}"); return 1

    # ---------------------------------------------------------------- 1, 2. đầy đủ / tái tạo / rời nhau / PK duy nhất
    print("== 1-2. Ba quy tắc đúng đắn và khoá chính duy nhất")
    extra = {}
    for table, pk in FRAG:
        parts = {s: load(conns[s], table, pk) for s in c.SITES}
        rows_ref = load(ref, table, pk)
        # rời nhau (cũng là PK duy nhất toàn hệ)
        dup = sum(len(parts[a].keys() & parts[b].keys()) for a, b in combinations(c.SITES, 2))
        report(dup == 0, f"{table}: rời nhau, PK duy nhất toàn hệ", f"{dup} khoá trùng giữa các trạm" if dup else "")
        union = {}
        for s in c.SITES:
            union.update({k: v for k, v in parts[s].items() if int(k[0]) < NEW})
        orig_ref = {k: v for k, v in rows_ref.items()}
        missing = orig_ref.keys() - union.keys()
        report(not missing, f"{table}: đầy đủ (mọi dòng đối chứng có ở một trạm)", f"thiếu {len(missing)} dòng" if missing else f"{len(orig_ref)} dòng")
        same = all(union[k] == orig_ref[k] for k in orig_ref.keys() & union.keys())
        report(same and not (union.keys() - orig_ref.keys()), f"{table}: tái tạo được (hợp các mảnh = đối chứng, đúng nội dung)")
        extra[table] = sum(1 for s in c.SITES for k in parts[s] if int(k[0]) >= NEW)
    # course nhân bản
    rc = load(ref, "course", ["course_code"])
    for s in c.SITES:
        report(load(conns[s], "course", ["course_code"]) == rc, f"course nhân bản giống đối chứng ở {s}")
    news = {t: n for t, n in extra.items() if n}
    print(f"   (dòng thêm qua giao diện, không so với đối chứng: {news or 'không có'})")

    # ---------------------------------------------------------------- 3. mảnh đúng vùng
    print("== 3. Ràng buộc mảnh")
    for s in c.SITES:
        cn = conns[s]
        n = lambda sql: fetch(cn, sql)[0][0]
        report(n(f"SELECT count(*) FROM student WHERE home_campus <> '{s}'") == 0, f"{s}: student chỉ có sinh viên của cơ sở mình")
        report(n(f"SELECT count(*) FROM section WHERE campus <> '{s}'") == 0, f"{s}: section chỉ có lớp mở ở cơ sở mình")
        derived = {
            "enrollment→student": "SELECT count(*) FROM enrollment e LEFT JOIN student s USING(student_id) WHERE s.student_id IS NULL",
            "certificate→student": "SELECT count(*) FROM certificate e LEFT JOIN student s USING(student_id) WHERE s.student_id IS NULL",
            "cert_language→certificate": "SELECT count(*) FROM cert_language x LEFT JOIN certificate p USING(certificate_id) WHERE p.certificate_id IS NULL",
            "cert_it→certificate": "SELECT count(*) FROM cert_it x LEFT JOIN certificate p USING(certificate_id) WHERE p.certificate_id IS NULL",
            "cert_research→certificate": "SELECT count(*) FROM cert_research x LEFT JOIN certificate p USING(certificate_id) WHERE p.certificate_id IS NULL",
            "cert_it_module→cert_it": "SELECT count(*) FROM cert_it_module x LEFT JOIN cert_it p USING(certificate_id) WHERE p.certificate_id IS NULL",
            "coauthor→cert_research": "SELECT count(*) FROM cert_research_coauthor x LEFT JOIN cert_research p USING(certificate_id) WHERE p.certificate_id IS NULL",
            "section→course": "SELECT count(*) FROM section x LEFT JOIN course p USING(course_code) WHERE p.course_code IS NULL",
        }
        bad = {k: n(q) for k, q in derived.items() if n(q)}
        report(not bad, f"{s}: dòng dẫn xuất cùng trạm với cha, FK cục bộ không mồ côi", str(bad) if bad else "")

    # ---------------------------------------------------------------- 4. FK liên vùng
    print("== 4. Khoá ngoại liên vùng")
    secs = set()
    for s in c.SITES:
        secs |= {r[0] for r in fetch(conns[s], "SELECT section_id FROM section")}
    orphan = 0; cross = 0
    for s in c.SITES:
        sec_local = {r[0] for r in fetch(conns[s], "SELECT section_id FROM section")}
        for (sid,) in fetch(conns[s], "SELECT DISTINCT section_id FROM enrollment"):
            if sid not in secs: orphan += 1
            elif sid not in sec_local: cross += 1
    report(orphan == 0, "enrollment.section_id tồn tại ở một trạm nào đó", f"{orphan} lớp mồ côi" if orphan else f"có {cross} lớp ở trạm khác (liên vùng)")

    # ---------------------------------------------------------------- 5. jsonb ↔ quan hệ
    print("== 5. jsonb tương đương bảng quan hệ")
    for s in c.SITES:
        cn = conns[s]
        lang = fetch(cn, """SELECT count(*) FROM certificate c FULL JOIN cert_language l USING(certificate_id)
            WHERE (c.cert_type='language') IS DISTINCT FROM (l.certificate_id IS NOT NULL)
               OR (c.cert_type='language' AND (c.detail->>'test' IS DISTINCT FROM l.test
                    OR (c.detail->>'overall')::numeric IS DISTINCT FROM l.overall
                    OR (c.detail#>>'{skills,listening}')::numeric IS DISTINCT FROM l.listening
                    OR (c.detail#>>'{skills,reading}')::numeric IS DISTINCT FROM l.reading
                    OR (c.detail#>>'{skills,writing}')::numeric IS DISTINCT FROM l.writing
                    OR (c.detail#>>'{skills,speaking}')::numeric IS DISTINCT FROM l.speaking))""")[0][0]
        it = fetch(cn, """SELECT count(*) FROM certificate c FULL JOIN cert_it i USING(certificate_id)
            WHERE (c.cert_type='it') IS DISTINCT FROM (i.certificate_id IS NOT NULL)
               OR (c.cert_type='it' AND (c.detail->>'name' IS DISTINCT FROM i.name OR c.detail->>'level' IS DISTINCT FROM i.level
                    OR (SELECT coalesce(array_agg(m ORDER BY m),'{}') FROM jsonb_array_elements_text(c.detail->'modules') m)
                       IS DISTINCT FROM (SELECT coalesce(array_agg(module ORDER BY module),'{}') FROM cert_it_module WHERE certificate_id=c.certificate_id)))""")[0][0]
        rs = fetch(cn, """SELECT count(*) FROM certificate c FULL JOIN cert_research r USING(certificate_id)
            WHERE (c.cert_type='research') IS DISTINCT FROM (r.certificate_id IS NOT NULL)
               OR (c.cert_type='research' AND (c.detail->>'title' IS DISTINCT FROM r.title OR c.detail->>'venue' IS DISTINCT FROM r.venue
                    OR c.detail->>'role' IS DISTINCT FROM r.role
                    OR (SELECT coalesce(array_agg(n ORDER BY o),'{}') FROM jsonb_array_elements_text(c.detail->'coauthors') WITH ORDINALITY a(n,o))
                       IS DISTINCT FROM (SELECT coalesce(array_agg(name ORDER BY seq),'{}') FROM cert_research_coauthor WHERE certificate_id=c.certificate_id)))""")[0][0]
        report(lang == 0 and it == 0 and rs == 0, f"{s}: jsonb ↔ cert_language / cert_it(+module) / cert_research(+coauthor)",
               f"lệch language={lang} it={it} research={rs}" if (lang or it or rs) else "")

    # ---------------------------------------------------------------- 6. Q1–Q5
    print("== 6. Q1–Q5 trạm trung tâm so với CSDL đối chứng")
    cen = c.connect("campus_a")           # trạm trung tâm: bảng cục bộ + all_*
    pk1 = dict(section="section_id", student="student_id", enrollment="enrollment_id", certificate="certificate_id", cert_language="certificate_id")
    G = {t: f"(SELECT * FROM all_{t} WHERE {k} < {NEW})" for t, k in pk1.items()}          # toàn cục, chỉ dòng nạp
    L = {t: f"(SELECT * FROM {t} WHERE {k} < {NEW})" for t, k in pk1.items()}               # cục bộ, chỉ dòng nạp
    R = {t: t for t in pk1}                                                              # đối chứng
    sec_b = fetch(ref, "SELECT min(section_id) FROM section WHERE campus='campus_b'")[0][0]
    Q = {
        "Q1": ("SELECT s.major_code, round(avg(e.total),2) FROM {student} s JOIN {enrollment} e USING(student_id) "
               "WHERE s.home_campus='campus_a' AND e.semester='2025-2' GROUP BY 1 ORDER BY 1", L),
        "Q2": ("SELECT sec.course_code, round(count(*) FILTER (WHERE e.total>=5)::numeric/count(*),4) FROM {enrollment} e "
               "JOIN {section} sec USING(section_id) WHERE e.semester='2025-2' GROUP BY 1 ORDER BY 1", G),
        "Q3": (f"SELECT s.student_id, s.full_name FROM {{enrollment}} e JOIN {{student}} s USING(student_id) WHERE e.section_id={sec_b} ORDER BY 1", G),
        "Q4": ("SELECT DISTINCT c.student_id FROM {certificate} c WHERE c.cert_type='language' "
               "AND (c.detail->>'overall')::numeric>=6.5 AND (c.detail#>>'{{skills,speaking}}')::numeric>=6.0 ORDER BY 1", G),
        "Q5": ("SELECT DISTINCT c.student_id FROM {certificate} c JOIN {cert_language} l USING(certificate_id) "
               "WHERE l.overall>=6.5 AND l.speaking>=6.0 ORDER BY 1", G),
    }
    results = {}
    for name, (sql, src) in Q.items():
        a = fetch(ref, sql.format(**R)); b = fetch(cen, sql.format(**src)); results[name] = b
        report(a == b, f"{name}: giống đối chứng", f"{len(a)} dòng" if a == b else f"đối chứng {len(a)} dòng, phân tán {len(b)} dòng")
    report(results["Q4"] == results["Q5"], "Q4 (jsonb) = Q5 (bảng quan hệ)", f"{len(results['Q4'])} sinh viên")
    plan = "\n".join(r[0] for r in fetch(cen, "EXPLAIN " + Q["Q1"][0].format(**L)))
    report("Foreign Scan" not in plan, "Q1 chạy trọn tại một trạm (EXPLAIN không có Foreign Scan)")
    plan3 = "\n".join(r[0] for r in fetch(cen, "EXPLAIN " + Q["Q3"][0].format(**G)))
    print(f"   (Q3 liên vùng: {plan3.count('Foreign Scan')} Foreign Scan trong kế hoạch)")

    print(f"\n{'TẤT CẢ ĐẠT' if not fails else f'{fails} MỤC KHÔNG ĐẠT'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
