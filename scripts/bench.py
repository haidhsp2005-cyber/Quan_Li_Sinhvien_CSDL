#!/usr/bin/env python3
"""make bench: đo Q1–Q5 (không trễ / trễ 30 ms khứ hồi), thu số liệu N1–N5.
Mỗi truy vấn chạy 5 lần, bỏ lần đầu, lấy trung vị 4 lần còn lại.
Kết quả: results/results.csv, results/explain_<Q>.txt (EXPLAIN ANALYZE VERBOSE), results/metrics.json, results/summary.md
Chạy trên máy A (cùng máy với campus_a, toxiproxy và đã `make link`).
"""
import csv, json, os, re, statistics, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import common as c  # noqa: E402

RES = ROOT / "results"; RES.mkdir(exist_ok=True)
RUNS, DELAY_MS = 5, int(os.environ.get("DELAY_MS", 30))
API = os.environ.get("TOXIPROXY", "http://localhost:8474")


# ------------------------------------------------------------------ độ trễ (toxiproxy)
def _req(method, path, body=None):
    r = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None)
    try:
        return urllib.request.urlopen(r, timeout=5).read()
    except Exception:
        return b""


def set_delay(on):
    for p in ("b", "c"):
        for stream in ("upstream", "downstream"):
            _req("DELETE", f"/proxies/{p}/toxics/lat_{stream}")
            if on:
                _req("POST", f"/proxies/{p}/toxics", {"name": f"lat_{stream}", "type": "latency", "stream": stream,
                                                      "toxicity": 1.0, "attributes": {"latency": DELAY_MS // 2, "jitter": 0}})


def central():
    conn = c.connect("campus_a"); conn.autocommit = True; return conn


# ------------------------------------------------------------------ truy vấn
ENR = "enrollment"
def per_site(tpl):   # ghép một mẫu SQL cho 3 trạm: bảng cục bộ + remote_b + remote_c
    parts = []
    for pre in ("", "remote_b.", "remote_c."):
        parts.append(tpl.replace("{p}", pre))
    return parts

def build(sec_b):
    Q = {}
    Q["Q1"] = ("SELECT s.major_code, round(avg(e.total),2) FROM student s JOIN enrollment e USING(student_id) "
               "WHERE s.home_campus='campus_a' AND e.semester='2025-2' GROUP BY 1 ORDER BY 1")
    Q["Q2"] = ("SELECT sec.course_code, round(count(*) FILTER (WHERE e.total>=5)::numeric/count(*),4) FROM all_enrollment e "
               "JOIN all_section sec USING(section_id) WHERE e.semester='2025-2' GROUP BY 1 ORDER BY 1")
    pa = " UNION ALL ".join(f"SELECT section_id, count(*) n, count(*) FILTER (WHERE total>=5) ok FROM {p}enrollment "
                            f"WHERE semester='2025-2' GROUP BY section_id" for p in ("", "remote_b.", "remote_c."))
    Q["Q2_opt"] = (f"WITH pa AS ({pa}) SELECT sec.course_code, round(sum(ok)::numeric/sum(n),4) FROM pa "
                   f"JOIN all_section sec USING(section_id) GROUP BY 1 ORDER BY 1")
    Q["Q3"] = (f"SELECT s.student_id, s.full_name FROM all_enrollment e JOIN all_student s USING(student_id) "
               f"WHERE e.section_id={sec_b} ORDER BY 1,2")
    j = " UNION ALL ".join(f"SELECT s.student_id, s.full_name FROM {p}enrollment e JOIN {p}student s USING(student_id) "
                           f"WHERE e.section_id={sec_b}" for p in ("", "remote_b.", "remote_c."))
    Q["Q3_opt"] = f"SELECT * FROM ({j}) t ORDER BY 1,2"
    Q["Q4"] = ("SELECT DISTINCT student_id FROM all_certificate WHERE cert_type='language' AND (detail->>'overall')::numeric>=6.5 "
               "AND (detail#>>'{skills,speaking}')::numeric>=6.0 ORDER BY 1")
    Q["Q5"] = ("SELECT DISTINCT c.student_id FROM all_certificate c JOIN all_cert_language l USING(certificate_id) "
               "WHERE l.overall>=6.5 AND l.speaking>=6.0 ORDER BY 1")
    j5 = " UNION ".join(f"SELECT c.student_id FROM {p}certificate c JOIN {p}cert_language l USING(certificate_id) "
                        f"WHERE l.overall>=6.5 AND l.speaking>=6.0" for p in ("", "remote_b.", "remote_c."))
    Q["Q5_opt"] = f"SELECT * FROM ({j5}) t ORDER BY 1"
    return Q

EXTRA = {   # dùng cho N5 (GIN)
    "Q4b": "SELECT DISTINCT student_id FROM all_certificate WHERE detail @> '{\"test\":\"IELTS\",\"skills\":{\"speaking\":8.0}}' ORDER BY 1",
    "Q5b": ("SELECT DISTINCT c.student_id FROM all_certificate c JOIN all_cert_language l USING(certificate_id) "
            "WHERE l.test='IELTS' AND l.speaking=8.0 ORDER BY 1"),
}
PRIMARY = ["Q1", "Q2", "Q3", "Q4", "Q5"]


def timed(conn, sql):
    ts, rows = [], None
    with conn.cursor() as cur:
        for _ in range(RUNS):
            t0 = time.perf_counter(); cur.execute(sql); rows = cur.fetchall(); ts.append((time.perf_counter() - t0) * 1000)
    return ts, rows


def plan_of(conn, sql):
    with conn.cursor() as cur:
        cur.execute("EXPLAIN (ANALYZE, VERBOSE) " + sql); return [r[0] for r in cur.fetchall()]


def remote_info(plan):
    stations = set()
    for line in plan:
        if "Foreign Scan" in line or "Relations:" in line:
            stations |= set(re.findall(r"remote_([bc])\.", line))
    sqls = [l.split("Remote SQL:", 1)[1].strip() for l in plan if "Remote SQL:" in l]
    return sorted(stations), sum("Foreign Scan" in l for l in plan), sqls


def med(ts):
    return round(statistics.median(ts[1:]), 2)     # bỏ lần đầu


def measure(sql_map):
    conn = central(); out = {}
    for name, sql in sql_map.items():
        ts, rows = timed(conn, sql); out[name] = (ts, rows)
    conn.close(); return out


def main():
    ref = c.connect("campus_a", dbname="ref_central"); ref.autocommit = True
    with ref.cursor() as cur:
        cur.execute("SELECT min(section_id) FROM section WHERE campus='campus_b'"); sec_b = cur.fetchone()[0]
    Q = build(sec_b)
    print(f"Q3 dùng lớp học phần {sec_b} (mở ở campus_b). {RUNS} lần/truy vấn, bỏ lần đầu, trung vị.")

    # ---------------- đo hai kịch bản
    scen = {}
    for label, on in (("no_delay", False), (f"delay_{DELAY_MS}ms", True)):
        set_delay(on); time.sleep(0.5)
        scen[label] = measure(Q); print(f"đã đo: {label}")
    set_delay(False)

    # kết quả các biến thể phải bằng bản gốc
    base = scen["no_delay"]
    same = {"Q2_opt": base["Q2"][1] == base["Q2_opt"][1], "Q3_opt": base["Q3"][1] == base["Q3_opt"][1],
            "Q5_opt": base["Q5"][1] == base["Q5_opt"][1], "Q4=Q5": base["Q4"][1] == base["Q5"][1]}
    print("kết quả giống nhau:", same)

    # ---------------- EXPLAIN (ANALYZE, VERBOSE) không trễ
    conn = central(); info = {}
    for name, sql in Q.items():
        plan = plan_of(conn, sql)
        (RES / f"explain_{name}.txt").write_text(f"-- {name}\n-- {sql}\n\n" + "\n".join(plan) + "\n", encoding="utf-8")
        st, nfs, sqls = remote_info(plan); info[name] = {"remote_stations": st, "foreign_scans": nfs, "remote_sql": sqls}
    conn.close()

    # ---------------- results.csv
    with open(RES / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["query", "scenario", "run1_ms", "run2_ms", "run3_ms", "run4_ms", "run5_ms", "median_ms_runs2to5", "result_rows", "remote_stations", "foreign_scans"])
        for label, data in scen.items():
            for name, (ts, rows) in data.items():
                w.writerow([name, label] + [round(t, 2) for t in ts] + [med(ts), len(rows), "".join(info[name]["remote_stations"]) or "-", info[name]["foreign_scans"]])

    M = {"runs": RUNS, "delay_ms_rtt": DELAY_MS, "q3_section": sec_b, "variants_equal": same,
         "queries": {n: {"no_delay_ms": med(scen["no_delay"][n][0]), "delay_ms": med(scen[f"delay_{DELAY_MS}ms"][n][0]),
                         "rows": len(scen["no_delay"][n][1]), **info[n]} for n in Q}}
    for n, v in M["queries"].items():
        v["extra_ms"] = round(v["delay_ms"] - v["no_delay_ms"], 1)
        v["est_round_trips"] = round(v["extra_ms"] / DELAY_MS, 1)

    # ---------------- N1: số dòng mỗi mảnh
    n1 = {}
    for s in c.SITES:
        conn = c.connect(s)
        with conn.cursor() as cur:
            cur.execute(" UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in c.TABLES)); n1[s] = dict(cur.fetchall())
        conn.close()
    with ref.cursor() as cur:
        cur.execute(" UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in c.TABLES)); n1["ref"] = dict(cur.fetchall())
    M["N1"] = n1

    # ---------------- N4: tỉ lệ liên vùng và hàng của Q3 theo trạm
    with ref.cursor() as cur:
        cur.execute("SELECT count(*), count(*) FILTER (WHERE s.campus <> st.home_campus) FROM enrollment e "
                    "JOIN section s USING(section_id) JOIN student st USING(student_id)")
        tot, cr = cur.fetchone()
        cur.execute("SELECT st.home_campus, count(*) FROM enrollment e JOIN student st USING(student_id) WHERE e.section_id=%s GROUP BY 1 ORDER BY 1", (sec_b,))
        q3_by = dict(cur.fetchall())
        cur.execute("SELECT count(*) FILTER (WHERE st.home_campus <> s.campus), count(*) FROM enrollment e JOIN section s USING(section_id) "
                    "JOIN student st USING(student_id) WHERE s.campus='campus_b'")
        remote_b, all_b = cur.fetchone()
    rate = cr / tot
    M["N4"] = {"cross_rows": cr, "total": tot, "rate": round(rate, 4), "q3_rows_by_station": q3_by,
               "q3_remote_rows": sum(v for k, v in q3_by.items() if k != "campus_b"), "q3_rows": sum(q3_by.values()),
               "campus_b_sections_remote_share": round(remote_b / all_b, 4),
               "pred_30pct_scale": round(0.30 / rate, 2)}

    # ---------------- N5: dung lượng jsonb vs quan hệ, có/không GIN
    kids = ["cert_language", "cert_it", "cert_it_module", "cert_research", "cert_research_coauthor"]
    size = {"certificate_total": 0, "certificate_heap": 0, "detail_bytes": 0, "relational_total": 0, "relational_heap": 0}
    for s in c.SITES:
        conn = c.connect(s)
        with conn.cursor() as cur:
            cur.execute("SELECT pg_total_relation_size('certificate'), pg_table_size('certificate'), (SELECT sum(pg_column_size(detail)) FROM certificate)")
            a, b, d = cur.fetchone(); size["certificate_total"] += a; size["certificate_heap"] += b; size["detail_bytes"] += d
            for k in kids:
                cur.execute(f"SELECT pg_total_relation_size('{k}'), pg_table_size('{k}')"); a, b = cur.fetchone()
                size["relational_total"] += a; size["relational_heap"] += b
        conn.close()
    gin = {}
    def gin_state(create):
        for s in c.SITES:
            conn = c.connect(s); conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("DROP INDEX IF EXISTS bench_gin")
                if create:
                    cur.execute("CREATE INDEX bench_gin ON certificate USING gin (detail jsonb_path_ops)")
                cur.execute("ANALYZE certificate")
            conn.close()
    sub = {k: v for k, v in EXTRA.items()}; sub["Q4"] = Q["Q4"]
    gin["without"] = {n: (med(t), len(r)) for n, (t, r) in measure(sub).items()}
    gin_state(True)
    idx = 0
    for s in c.SITES:
        conn = c.connect(s)
        with conn.cursor() as cur:
            cur.execute("SELECT pg_relation_size('bench_gin')"); idx += cur.fetchone()[0]
        conn.close()
    gin["with"] = {n: (med(t), len(r)) for n, (t, r) in measure(sub).items()}
    conn = central()
    gin["with_plan_Q4b"] = [l.strip() for l in plan_of(conn, EXTRA["Q4b"]) if "bench_gin" in l or "Bitmap" in l][:4]
    gin["with_plan_Q4"] = [l.strip() for l in plan_of(conn, Q["Q4"]) if "bench_gin" in l]
    conn.close()
    gin_state(False)
    size["gin_index_total"] = idx
    M["N5"] = {"size_bytes": size, "gin": gin}

    (RES / "metrics.json").write_text(json.dumps(M, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_summary(M)
    print("Đã ghi results/results.csv, explain_*.txt, metrics.json, summary.md")


def mb(x): return f"{x / 1048576:.2f} MB"


def write_summary(M):
    L = [f"# Kết quả đo — Đề 2\n", f"Mỗi truy vấn {M['runs']} lần, bỏ lần đầu, trung vị. Trễ = {M['delay_ms_rtt']} ms khứ hồi (toxiproxy). "
         f"Q3 dùng lớp {M['q3_section']} (mở ở campus_b). Biến thể `_opt` đẩy gom nhóm/nối xuống từng trạm; kết quả giống bản gốc: {M['variants_equal']}.\n",
         "## Q1–Q5\n", "| Truy vấn | Không trễ (ms) | Trễ (ms) | Chênh (ms) | Vòng khứ hồi ước tính | Dòng | Trạm xa | Foreign Scan |", "|---|---|---|---|---|---|---|---|"]
    for n, v in M["queries"].items():
        L.append(f"| {n} | {v['no_delay_ms']} | {v['delay_ms']} | {v['extra_ms']} | {v['est_round_trips']} | {v['rows']} | {''.join(v['remote_stations']) or '-'} | {v['foreign_scans']} |")
    L += ["\n## N1 — Số dòng mỗi mảnh\n", "| Bảng | campus_a | campus_b | campus_c | Tổng | Đối chứng |", "|---|---|---|---|---|---|"]
    for t in c.TABLES:
        tot = M["N1"]["campus_a"][t] + M["N1"]["campus_b"][t] + M["N1"]["campus_c"][t]
        L.append(f"| {t} | {M['N1']['campus_a'][t]} | {M['N1']['campus_b'][t]} | {M['N1']['campus_c'][t]} | {tot if t != 'course' else 'nhân bản'} | {M['N1']['ref'][t]} |")
    n4 = M["N4"]
    L += ["\n## N4 — Liên vùng\n", f"- Dòng đăng ký liên vùng: {n4['cross_rows']} / {n4['total']} = {n4['rate'] * 100:.2f} %",
          f"- Q3 ({M['q3_section']}): {n4['q3_rows']} dòng, theo trạm của sinh viên: {n4['q3_rows_by_station']} → {n4['q3_remote_rows']} dòng phải lấy từ trạm khác",
          f"- Với các lớp mở ở campus_b: {n4['campus_b_sections_remote_share'] * 100:.1f} % đăng ký đến từ sinh viên cơ sở khác. Dự đoán tỉ lệ 30 %: số dòng xa ≈ ×{n4['pred_30pct_scale']}"]
    s = M["N5"]["size_bytes"]; g = M["N5"]["gin"]
    L += ["\n## N5 — Dung lượng jsonb và GIN\n", f"- `certificate` (có cột jsonb): {mb(s['certificate_total'])} gồm index; riêng bảng {mb(s['certificate_heap'])}; riêng cột detail {mb(s['detail_bytes'])}",
          f"- 5 bảng quan hệ tương đương: {mb(s['relational_total'])} gồm index; riêng bảng {mb(s['relational_heap'])}",
          f"- GIN `jsonb_path_ops` trên detail (3 trạm): {mb(s['gin_index_total'])}", "",
          "| Truy vấn | Không GIN (ms) | Có GIN (ms) | Dòng |", "|---|---|---|---|"]
    for n in ("Q4", "Q4b", "Q5b"):
        L.append(f"| {n} | {g['without'][n][0]} | {g['with'][n][0]} | {g['with'][n][1]} |")
    L.append(f"\nKế hoạch Q4b có GIN: {g['with_plan_Q4b']}  \nKế hoạch Q4 có GIN dùng bench_gin: {bool(g['with_plan_Q4'])}")
    (RES / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
