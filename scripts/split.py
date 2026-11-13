#!/usr/bin/env python3
"""Chia CSV tập trung thành mảnh theo trạm (chỉ thư viện chuẩn).
Dùng: python split.py <thư mục csv> <thư mục ra>
 - course: nhân bản ra cả 3 trạm
 - student: theo home_campus; section: theo campus
 - enrollment, certificate: theo trạm của student
 - cert_*: theo trạm của certificate; cert_it_module / cert_research_coauthor: theo cert cha
"""
import csv, sys
from pathlib import Path

SITES = ["campus_a", "campus_b", "campus_c"]
src, dst = Path(sys.argv[1]), Path(sys.argv[2])

def rows(t):
    with open(src / f"{t}.csv", newline="", encoding="utf-8") as f:
        r = csv.reader(f); h = next(r); return h, list(r)

outs = {}
def out(site, t, header):
    if (site, t) not in outs:
        p = dst / site; p.mkdir(parents=True, exist_ok=True)
        f = open(p / f"{t}.csv", "w", newline="", encoding="utf-8"); w = csv.writer(f); w.writerow(header)
        outs[(site, t)] = (f, w)
    return outs[(site, t)][1]

stats = {}
def emit(site, t, h, row):
    out(site, t, h).writerow(row); stats[(t, site)] = stats.get((t, site), 0) + 1

h, data = rows("course")
for s in SITES:
    for r in data: emit(s, "course", h, r)

h, data = rows("student"); ci = h.index("home_campus"); st_site = {}
for r in data: st_site[r[0]] = r[ci]; emit(r[ci], "student", h, r)

h, data = rows("section"); ci = h.index("campus")
for r in data: emit(r[ci], "section", h, r)

h, data = rows("enrollment"); si = h.index("student_id")
for r in data: emit(st_site[r[si]], "enrollment", h, r)

h, data = rows("certificate"); si = h.index("student_id"); cert_site = {}
for r in data: cert_site[r[0]] = st_site[r[si]]; emit(cert_site[r[0]], "certificate", h, r)

for t in ["cert_language", "cert_it", "cert_it_module", "cert_research", "cert_research_coauthor"]:
    h, data = rows(t)
    for r in data: emit(cert_site[r[0]], t, h, r)

for f, _ in outs.values(): f.close()
for t in sorted({k[0] for k in stats}):
    print(f"{t:<24}" + "".join(f"{s}={stats.get((t, s), 0):>8}  " for s in SITES) + f"tổng={sum(stats.get((t, s), 0) for s in SITES)}")
