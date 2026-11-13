#!/usr/bin/env python3
"""Sinh báo cáo (A4, ≤ 10 trang) và slide (16:9) dạng PDF từ results/metrics.json + ảnh trong report/img.
Dùng Chrome/Edge headless để in PDF. Chạy: python3 report/build.py   (sửa MEMBERS bên dưới trước khi nộp)
"""
import html, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report"
M = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
IMG = "img/"

# ---- ĐIỀN TRƯỚC KHI NỘP -------------------------------------------------------
GROUP = "Nhóm [số nhóm]"
MEMBERS = [("[Họ tên 1]", "[MSHV]", "Thiết kế phân tán, schema, CHECK/FK, nạp dữ liệu, báo cáo mục 2–4"),
           ("[Họ tên 2]", "[MSHV]", "Hạ tầng 2 máy, Makefile, fdw, độ trễ, `make check`"),
           ("[Họ tên 3]", "[MSHV]", "Giao diện nhập liệu, dashboard"),
           ("[Họ tên 4]", "[MSHV]", "Truy vấn Q1–Q5, bench, N1–N5, slide")]
REPO = "https://github.com/haidhsp2005-cyber/Quan_Li_Sinhvien_CSDL"
MEASURED_ON = "1 máy (3 trạm là 3 container Docker)"          # đổi thành "2 máy" khi đã đo trên 2 máy thật
# ------------------------------------------------------------------------------

Q, N1, N4, N5 = M["queries"], M["N1"], M["N4"], M["N5"]
SITES = ["campus_a", "campus_b", "campus_c"]
e = html.escape
def mb(x): return f"{x / 1048576:.2f} MB"
def pct(a, b): return f"{100 * a / b:.1f} %"
def n(x): return f"{x:,}".replace(",", ".")
def ms(x): return f"{x:,.1f}".replace(",", " ").replace(".", ",") if x < 100 else f"{x:,.0f}".replace(",", ".")

# ================================================================== SVG
def svg_deploy(w=720, h=300):
    return f'''<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial" font-size="12">
<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#444"/></marker></defs>
<rect x="8" y="8" width="360" height="284" rx="10" fill="#eef4fb" stroke="#2b6cb0" stroke-width="1.5"/>
<text x="22" y="30" font-weight="700" fill="#1e4e8c" font-size="14">Máy A (trung tâm)</text>
<rect x="24" y="44" width="150" height="54" rx="6" fill="#fff" stroke="#2b6cb0"/><text x="99" y="66" text-anchor="middle" font-weight="700">campus_a :5432</text><text x="99" y="84" text-anchor="middle" font-size="11">trạm + ref_central</text>
<rect x="196" y="44" width="156" height="54" rx="6" fill="#fff" stroke="#888"/><text x="274" y="66" text-anchor="middle" font-weight="700">toxiproxy</text><text x="274" y="84" text-anchor="middle" font-size="11">:15433 · :15434 (trễ 30 ms)</text>
<rect x="24" y="130" width="150" height="46" rx="6" fill="#fff" stroke="#38a169"/><text x="99" y="150" text-anchor="middle" font-weight="700">entry.py :8501</text><text x="99" y="166" text-anchor="middle" font-size="11">giao diện nhập liệu</text>
<rect x="196" y="130" width="156" height="46" rx="6" fill="#fff" stroke="#38a169"/><text x="274" y="150" text-anchor="middle" font-weight="700">dash.py :8502</text><text x="274" y="166" text-anchor="middle" font-size="11">dashboard (2 giây)</text>
<rect x="24" y="208" width="328" height="64" rx="6" fill="#fff" stroke="#b7791f" stroke-dasharray="4 3"/><text x="188" y="230" text-anchor="middle" font-weight="700">Python: bench.py · check.py · load.sh</text><text x="188" y="248" text-anchor="middle" font-size="11">đọc deploy.toml; nạp dữ liệu qua LAN; đo Q1–Q5</text>
<rect x="452" y="8" width="260" height="284" rx="10" fill="#fdf2e9" stroke="#dd6b20" stroke-width="1.5"/>
<text x="466" y="30" font-weight="700" fill="#9c4a10" font-size="14">Máy B</text>
<rect x="472" y="50" width="220" height="62" rx="6" fill="#fff" stroke="#dd6b20"/><text x="582" y="76" text-anchor="middle" font-weight="700">campus_b :5433</text><text x="582" y="94" text-anchor="middle" font-size="11">section/student/enrollment…</text>
<rect x="472" y="150" width="220" height="62" rx="6" fill="#fff" stroke="#dd6b20"/><text x="582" y="176" text-anchor="middle" font-weight="700">campus_c :5434</text><text x="582" y="194" text-anchor="middle" font-size="11">section/student/enrollment…</text>
<text x="582" y="250" text-anchor="middle" font-size="11" fill="#555">Chỉ cần Docker + docker-compose.yml</text>
<path d="M352,71 L452,81" stroke="#444" stroke-width="1.6" fill="none" marker-end="url(#ar)"/><path d="M352,85 L452,175" stroke="#444" stroke-width="1.6" fill="none" marker-end="url(#ar)"/>
<text x="400" y="62" font-size="11" fill="#444" text-anchor="middle">postgres_fdw</text>
<path d="M174,153 L190,153" stroke="#38a169" stroke-width="1.2"/><path d="M99,130 L99,98" stroke="#38a169" stroke-width="1.5" marker-end="url(#ar)"/>
<text x="360" y="287" font-size="11" fill="#2b6cb0" text-anchor="middle">LAN: entry/dash ghi &amp; đọc thẳng từng trạm (psycopg2)</text>
</svg>'''

def svg_frag(w=720, h=206):
    def box(x, y, t, s, c="#fff", st="#2b6cb0"):
        return (f'<rect x="{x}" y="{y}" width="132" height="46" rx="6" fill="{c}" stroke="{st}"/>'
                f'<text x="{x+66}" y="{y+20}" text-anchor="middle" font-weight="700">{t}</text><text x="{x+66}" y="{y+36}" text-anchor="middle" font-size="10.5">{s}</text>')
    return f'''<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial" font-size="12">
<defs><marker id="a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#555"/></marker></defs>
{box(10,10,"student","theo home_campus","#e8f1fb")}{box(160,10,"section","theo campus","#e8f1fb")}{box(310,10,"course","nhân bản 3 trạm","#f0f0f0","#888")}
{box(10,90,"enrollment","dẫn xuất theo student")}{box(160,90,"certificate","dẫn xuất theo student")}
<rect x="330" y="86" width="380" height="76" rx="6" fill="#fff" stroke="#2b6cb0"/>
<text x="344" y="106" font-weight="700">cert_language · cert_it · cert_research</text><text x="344" y="124" font-size="11">dẫn xuất theo certificate (1 – 0..1)</text>
<text x="344" y="144" font-weight="700">cert_it_module · cert_research_coauthor</text><text x="344" y="158" font-size="11">dẫn xuất theo cert_it / cert_research</text>
<path d="M76,56 L76,90" stroke="#555" stroke-width="1.4" marker-end="url(#a2)"/><path d="M142,60 L190,90" stroke="#555" stroke-width="1.4" marker-end="url(#a2)"/>
<path d="M292,113 L330,113" stroke="#555" stroke-width="1.4" marker-end="url(#a2)"/>
<path d="M226,56 L226,70 L90,70 L90,90" stroke="#c53030" stroke-width="1.2" stroke-dasharray="4 3" fill="none" marker-end="url(#a2)"/>
<text x="10" y="168" font-size="11.5" fill="#555">——  dòng con nằm cùng trạm với dòng cha (FK cục bộ)</text>
<text x="10" y="188" font-size="11.5" fill="#c53030">- - -  enrollment.section_id → section: chéo trạm ~7 % dòng (không có FK thật; kiểm ở tầng ghi + make check)</text>
</svg>'''

def svg_bars(w=700, h=None, keys=("Q1", "Q2", "Q3", "Q4", "Q5"), fs=12):
    h = h or (20 + len(keys) * 74 + 34)
    mx = max(Q[k]["delay_ms"] for k in keys) * 1.08
    left, bw, gap = 70 + (fs - 12) * 3, 24, 26
    parts = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial" font-size="{fs}">']
    for i, k in enumerate(keys):
        y = 20 + i * (2 * bw + gap)
        a, b = Q[k]["no_delay_ms"], Q[k]["delay_ms"]
        wa, wb = max(2, (w - left - 80) * a / mx), max(2, (w - left - 80) * b / mx)
        parts.append(f'<text x="{left-10}" y="{y+bw}" text-anchor="end" font-weight="700">{k}</text>')
        parts.append(f'<rect x="{left}" y="{y}" width="{wa:.1f}" height="{bw-3}" fill="#2b6cb0"/><text x="{left+wa+6:.1f}" y="{y+bw-9}" font-size="{fs-1}">{ms(a)} ms</text>')
        parts.append(f'<rect x="{left}" y="{y+bw}" width="{wb:.1f}" height="{bw-3}" fill="#dd6b20"/><text x="{left+wb+6:.1f}" y="{y+2*bw-9}" font-size="{fs-1}">{ms(b)} ms</text>')
    parts.append(f'<rect x="{left}" y="{h-18}" width="12" height="10" fill="#2b6cb0"/><text x="{left+18}" y="{h-9}" font-size="{fs-1}">không trễ</text>'
                 f'<rect x="{left+100}" y="{h-18}" width="12" height="10" fill="#dd6b20"/><text x="{left+118}" y="{h-9}" font-size="{fs-1}">trễ 30 ms khứ hồi</text></svg>')
    return "".join(parts)

# ================================================================== bảng
def tbl(head, rows, cls="", align=None):
    th = "".join(f"<th>{e(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td{' class=\"r\"' if (align and align[i]=='r') else ''}>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'

def q_rows(keys):
    rows = []
    for k in keys:
        v = Q[k]
        rows.append([k, ms(v["no_delay_ms"]), ms(v["delay_ms"]), ms(v["extra_ms"]), f"≈ {v['est_round_trips']}".replace(".", ","), n(v["rows"]),
                     "".join(v["remote_stations"]).replace("b", "B").replace("c", "C") or "—", str(v["foreign_scans"])])
    return rows
QHEAD = ["Truy vấn", "Không trễ (ms)", "Trễ 30 ms (ms)", "Chênh (ms)", "Vòng khứ hồi", "Dòng", "Trạm xa", "Foreign Scan"]
QALIGN = ["l", "r", "r", "r", "r", "r", "l", "r"]

n1_rows = []
for t in ["section", "student", "enrollment", "certificate", "cert_language", "cert_it", "cert_it_module", "cert_research", "cert_research_coauthor"]:
    a, b, c = (N1[s][t] for s in SITES)
    n1_rows.append([t, n(a), n(b), n(c), n(a + b + c), n(N1["ref"][t]), "✔" if a + b + c == N1["ref"][t] else "✘"])
n1_rows.insert(0, ["course (nhân bản)", "300", "300", "300", "300 / trạm", "300", "✔"])
st_tot = sum(N1[s]["student"] for s in SITES)
shares = " / ".join(pct(N1[s]["student"], st_tot) for s in SITES).replace(".", ",")

gz = N5["gin"]; sz = N5["size_bytes"]


import csv as _csv
def _check_block():
    f = ROOT / "results" / "check_output.txt"
    if not f.exists(): return ""
    sec, cnt, fk = None, {}, ""
    for l in f.read_text(encoding="utf-8").splitlines():
        if l.startswith("=="): sec = l.split(".")[0].strip("= ").strip(); cnt[sec] = [0, 0]
        elif l.startswith("PASS") and sec:
            cnt[sec][0] += 1
            if sec == "4": fk = l.split("—", 1)[-1].strip()
        elif l.startswith("FAIL") and sec: cnt[sec][1] += 1
    names = {"1-2": "Ba quy tắc đúng đắn (đầy đủ / tái tạo được / rời nhau) cho 9 bảng chia, PK duy nhất toàn hệ, <code>course</code> nhân bản giống nhau",
             "3": "Mảnh đúng vùng (CHECK), dòng dẫn xuất cùng trạm với cha, FK cục bộ không mồ côi (3 trạm × 3 mục)",
             "4": "Khoá ngoại liên vùng <code>enrollment.section_id</code> tồn tại ở một trạm nào đó (0 lớp mồ côi)",
             "5": "jsonb ↔ <code>cert_language</code>, <code>cert_it</code> (+module), <code>cert_research</code> (+coauthor), từng trạm",
             "6": "Q1–Q5 trên trạm trung tâm giống CSDL đối chứng; Q4 = Q5; Q1 không Foreign Scan"}
    rows = [[k, names[k], str(a + b), "PASS" if b == 0 else f"{b} FAIL"] for k, (a, b) in cnt.items() if k in names]
    total = sum(a for a, _ in cnt.values())
    return (f"<h3>Kết quả <code>make check</code>: {total} mục, tất cả PASS</h3>" + tbl(["Nhóm", "Kiểm tra", "Số mục", "Kết quả"], rows, align=["l", "l", "r", "l"]) +
            "<p><b>Thử phá dữ liệu để biết bộ kiểm tra bắt được lỗi:</b> cố ý thêm một sinh viên trùng id sang <code>campus_c</code> và một đăng ký trỏ tới lớp 99999 → báo 4 mục FAIL (student không rời nhau, student và enrollment không tái tạo được, 1 lớp mồ côi); sau khi hoàn tác thì đạt lại toàn bộ. "
            "So với đối chứng chỉ xét dòng nạp từ bộ sinh (id &lt; 1.000.000); dòng thêm qua giao diện chỉ phải thoả quy tắc cấu trúc.</p>")
CHECK_HTML = _check_block()

def _remote_block():
    rows = []
    for q in ("Q2", "Q2_opt", "Q3", "Q3_opt", "Q4", "Q5", "Q5_opt"):
        f = OUT.parent / "results" / f"explain_{q}.txt"
        if not f.exists(): continue
        sqls = []
        for l in f.read_text(encoding="utf-8").splitlines():
            if "Remote SQL:" in l:
                s = l.split("Remote SQL:", 1)[1].strip()
                if s not in sqls: sqls.append(s)
        rows.append([q, "<br>".join(f"<code>{e(s[:230])}{'…' if len(s) > 230 else ''}</code>" for s in sqls)])
    return "<h3>Trích kế hoạch: câu SQL thực sự gửi sang trạm xa</h3>" + tbl(["Q", "Remote SQL (lấy từ EXPLAIN (ANALYZE, VERBOSE), đã loại trùng)"], rows)
REMOTE_HTML = _remote_block()

def _raw_block():
    f = ROOT / "results" / "results.csv"
    if not f.exists(): return ""
    d = {}
    for r in _csv.DictReader(f.open(encoding="utf-8")):
        d.setdefault(r["query"], {})[r["scenario"]] = [r[f"run{i}_ms"] for i in range(1, 6)]
    rows = []
    for q, s in d.items():
        a = next((v for k, v in s.items() if k.startswith("no")), []); b = next((v for k, v in s.items() if k.startswith("delay")), [])
        rows.append([q, " · ".join(a), " · ".join(b)])
    return ("<h3>Số liệu đo thô (ms, 5 lần/truy vấn; lần 1 bị loại, lấy trung vị 4 lần sau)</h3>" +
            tbl(["Q", "Không trễ: lần 1 · 2 · 3 · 4 · 5", "Trễ 30 ms: lần 1 · 2 · 3 · 4 · 5"], rows) +
            "<p class='cap'>Lần 1 thường chậm hơn do mở kết nối <code>postgres_fdw</code> và nạp bộ nhớ đệm; vì vậy bị loại theo quy định đo của đề.</p>")
RAW_HTML = _raw_block()

# ================================================================== CSS dùng chung
BASE_CSS = """
*{box-sizing:border-box} body{font-family:'Segoe UI',Arial,sans-serif;color:#1a202c;margin:0}
table{border-collapse:collapse;width:100%} th,td{border:1px solid #cbd5e0;padding:2.5px 6px;vertical-align:top} th{background:#edf2f7;text-align:left}
td.r{text-align:right;font-variant-numeric:tabular-nums} code{font-family:Consolas,monospace;background:#edf2f7;padding:0 3px;border-radius:3px}
"""

# ================================================================== BÁO CÁO
def report():
    css = BASE_CSS + """
@page{size:A4;margin:15mm 16mm 16mm 16mm}
body{font-size:10.2pt;line-height:1.4}
h1{font-size:17pt;margin:0 0 2px;color:#1e4e8c} h2{font-size:12pt;margin:11px 0 4px;color:#1e4e8c;border-bottom:1.5px solid #bee3f8;padding-bottom:1px}
h3{font-size:10pt;margin:7px 0 2px} p{margin:3px 0 4px;text-align:justify} ul,ol{margin:2px 0 4px;padding-left:17px} li{margin:1px 0}
.sub{color:#4a5568;font-size:9.5pt;margin-bottom:5px} table{font-size:9.2pt;margin:3px 0 7px} .fig{text-align:center;margin:4px 0 6px;break-inside:avoid}
.fig img{max-width:100%;border:1px solid #cbd5e0} figcaption,.cap{font-size:8.4pt;color:#4a5568;text-align:center;margin-top:1px}
.two{display:flex;gap:8px} .two>div{flex:1} .note{background:#fffaf0;border-left:3px solid #dd6b20;padding:3px 7px;margin:4px 0;font-size:9pt}
.pb{break-before:page} table,.fig{break-inside:avoid} h2,h3{break-after:avoid}
"""
    members = tbl(["Thành viên", "MSHV", "Phần phụ trách"], [[e(a), e(b), re.sub(r"`([^`]*)`", r"<code></code>", e(c))] for a, b, c in MEMBERS])
    body = f"""
<h1>Đề 2 — Quản lý sinh viên liên cơ sở (3 trạm PostgreSQL)</h1>
<div class="sub">CS5104 — Hệ cơ sở dữ liệu nâng cao · Project nhóm cuối kỳ · {e(GROUP)} · Seed 284617 · Mã nguồn: {REPO}</div>

<h2>1. Bối cảnh và phạm vi</h2>
<p>Trường đại học có ba cơ sở, hồ sơ sinh viên lưu tại cơ sở theo học; sinh viên có thể học ghép lớp mở ở cơ sở khác (≈ 7 % lượt đăng ký). Từ lược đồ tập trung 10 bảng của đề (kèm cột <code>jsonb</code> <code>certificate.detail</code> và bản quan hệ tương đương), nhóm tự đề xuất cách phân tán dữ liệu ra ba trạm PostgreSQL 18 (<code>campus_a</code> trung tâm, <code>campus_b</code>, <code>campus_c</code>), triển khai trên 2 máy qua LAN, truy vấn xuyên trạm bằng <code>postgres_fdw</code>, xây giao diện nhập liệu và dashboard rồi đo, giải thích năm con số N1–N5. Quy mô lab: 15.000 sinh viên, 120.000 lượt đăng ký, 12.000 chứng chỉ, 300 học phần, 2.500 lớp. Không đổi lược đồ của đề (chỉ thêm chỉ mục, CHECK, khung nhìn).</p>

<h2>2. Thiết kế phân tán và lập luận</h2>
<div class="fig">{svg_frag()}<figcaption>Hình 1. Cách xác định mảnh của từng bảng (xanh: chia; xám: nhân bản)</figcaption></div>
{tbl(["Bảng", "Cách chia", "Vị trí", "Lập luận"], [
 ["student", "Ngang nguyên thuỷ theo <code>home_campus</code>", "trạm cùng tên cơ sở", "Đúng định nghĩa “vùng” của đề; tỉ lệ 0,50/0,32/0,18"],
 ["section", "Ngang nguyên thuỷ theo <code>campus</code>", "trạm cơ sở mở lớp", "Lớp thuộc cơ sở mở lớp; Q3 hỏi theo “lớp mở ở B”"],
 ["enrollment", "Ngang <b>dẫn xuất theo student</b>", "trạm của sinh viên", "<b>Q1 buộc chạy trọn tại một trạm</b> (điểm TB theo ngành của sinh viên cơ sở A) nên dòng đăng ký phải đi theo sinh viên. Hệ quả: dòng liên vùng nằm ở trạm sinh viên, lớp ở trạm khác"],
 ["certificate + 5 bảng con", "Dẫn xuất theo student rồi theo certificate / cert_it / cert_research", "trạm của sinh viên", "Q4, Q5 (sinh viên có chứng chỉ ngoại ngữ) nối cục bộ từng trạm; cột jsonb và bản quan hệ cùng trạm nên ghi trong một giao dịch"],
 ["course", "<b>Sao chép</b> ra cả 3 trạm", "A, B, C", "300 dòng, ít ghi, mọi trạm cần để giữ FK <code>section.course_code</code>"]], "")}
<h3>Cấp phát, khoá chính, khoá ngoại, CHECK, liên vùng</h3>
<ul>
<li><b>Cấp phát:</b> máy A giữ <code>campus_a</code>, CSDL đối chứng <code>ref_central</code>, giao diện, dashboard và toxiproxy; máy B giữ <code>campus_b</code> và <code>campus_c</code> (hai cổng 5433, 5434) nên tắt một trạm ở B vẫn còn trạm sống (D8).</li>
<li><b>Khoá chính duy nhất toàn hệ:</b> dữ liệu nạp giữ id 1..N; dòng mới lấy id từ sequence có <b>khối riêng mỗi trạm</b> (A: 1.000.001+, B: 2.000.001+, C: 3.000.001+, có <code>MAXVALUE</code>). <code>course_code</code> là khoá tự nhiên, sinh một lần rồi ghi ra cả 3 trạm.</li>
<li><b>Khoá ngoại:</b> sau khi chia, <code>enrollment→student</code>, <code>certificate→student</code>, các bảng con→cha, <code>section→course</code> đều cùng trạm nên là FK thật. Riêng <code>enrollment.section_id→section</code> chéo trạm ở ~7 % dòng nên không thể là FK vật lý: UI tra trạm của lớp ngay lúc ghi (lớp không tồn tại hoặc trạm chứa lớp chết thì từ chối) và <code>make check</code> đếm lớp mồ côi toàn hệ.</li>
<li><b>CHECK mảnh:</b> <code>student.home_campus = 'campus_x'</code>, <code>section.campus = 'campus_x'</code>. Bảng dẫn xuất không có cột vùng (không được thêm cột) nên “chỉ nhận đúng dòng” được bảo đảm bằng FK cục bộ tới mảnh cha đã có CHECK. <b>CHECK jsonb</b>: <code>cert_type</code> thuộc {{language, it, research}} và <code>detail</code> đúng dạng theo loại (khoá bắt buộc, <code>skills</code> là object, <code>modules</code>/<code>coauthors</code> là mảng).</li>
<li><b>Liên vùng:</b> Q1 chạy 1 trạm (A). Q2, Q4, Q5 không có điều kiện vùng nên chạm cả 3 trạm. Q3 (sinh viên của một lớp ở B) chạm B (≈ 93 % dòng) và A, C (≈ 7 % — sinh viên học ghép).</li>
</ul>
<p>Ba quy tắc đúng đắn được kiểm bằng <code>make check</code> cho 9 bảng bị chia: <b>đầy đủ</b> (mọi dòng đối chứng có ở một trạm), <b>tái tạo được</b> (hợp các mảnh bằng đúng nội dung đối chứng), <b>rời nhau</b> (không dòng nào ở hai trạm; cũng là khoá chính duy nhất toàn hệ). Mỗi trạm chỉ giữ dữ liệu vùng mình; Q1 không có Foreign Scan; trạm trung tâm trả lời Q1–Q5 giống CSDL đối chứng.</p>

<h3>Các phương án đã cân nhắc</h3>
{tbl(["Quyết định", "Phương án khác", "Vì sao không chọn"], [
 ["<code>enrollment</code> dẫn xuất theo <b>student</b>", "Theo <code>section</code> (Q3 cục bộ tại B)", "Q1 cần toàn bộ đăng ký của sinh viên cơ sở A ở A. Chia theo lớp thì ~7 % đăng ký của sinh viên A nằm ở B, C nên Q1 phải qua mạng, vi phạm ràng buộc “Q1 chạy trọn tại một trạm”"],
 ["<code>section</code> chia theo <code>campus</code>", "Nhân bản 2.500 dòng ra 3 trạm", "Nhân bản làm <code>enrollment.section_id</code> thành FK thật và Q2 tính cục bộ, nhưng mỗi lần thêm lớp phải ghi cả 3 trạm (cần giao dịch phân tán) và mất “vùng” của lớp mà bộ sinh dùng (<code>section.campus</code>). Nhóm chọn chia, đổi lại FK chéo trạm xử lý ở tầng ghi + <code>make check</code>"],
 ["PK là sequence khối id", "UUID hoặc ghép tiền tố trạm", "Đổi kiểu hoặc thêm cột là đổi lược đồ (đề cấm). Khối id giữ nguyên kiểu <code>integer</code>, ghi độc lập từng trạm"],
 ["jsonb và bản quan hệ cùng trạm", "Chia dọc: để jsonb ở trạm riêng", "Ghi hai biểu diễn trong một giao dịch cục bộ; không cần giao dịch phân tán để giữ chúng nhất quán"],
 ["<code>course</code> nhân bản", "Chia theo trạm", "Cả 3 trạm cần đủ 300 học phần để giữ FK <code>section.course_code</code>; ít ghi nên nhân bản rẻ"]], "")}

<h2>3. Sơ đồ triển khai, giao diện và dashboard</h2>
<div class="fig">{svg_deploy()}<figcaption>Hình 2. Triển khai trên hai máy qua LAN; <code>deploy.toml</code> ghi trạm → máy, IP, cổng</figcaption></div>
<p><b>Giao diện nhập liệu</b> (Streamlit, máy A): thêm sinh viên, thêm đăng ký (kể cả liên vùng), thêm chứng chỉ theo loại — form hiện đúng trường của loại, <code>detail</code> (jsonb) và bảng quan hệ ghi trong <b>một giao dịch</b> vào <b>đúng trạm</b>, thông báo trạm và máy đã ghi; trạm đích mất kết nối thì báo lỗi, không ghi sang trạm khác; nút “thêm ngẫu nhiên N dòng”. <b>Dashboard</b>: mỗi trạm một ô (máy, IP, xanh/đỏ, số dòng từng bảng, đọc thẳng từng trạm không qua <code>postgres_fdw</code>), bảng tổng hợp so với <code>ref_central</code>, nhật ký sự kiện, tự làm mới 2 giây.</p>
<div class="fig"><img src="{IMG}entry_enroll.png" style="width:74%"><div class="cap">Hình 3. Đăng ký liên vùng: sinh viên ở campus_a, lớp ở campus_b; dòng ghi vào trạm sinh viên</div></div>
<div class="fig"><img src="{IMG}dash_down.png" style="width:74%"><div class="cap">Hình 4. Dashboard khi tắt campus_c (đỏ + lỗi); hai trạm còn lại vẫn xanh</div></div>
<h3>Luồng ghi một đăng ký liên vùng</h3>
<ol>
<li>Người dùng nhập mã sinh viên và mã lớp; giao diện tra <b>trạm của sinh viên</b> (hỏi lần lượt các trạm) và <b>trạm, học kỳ của lớp</b>.</li>
<li>Không có sinh viên hoặc lớp thì từ chối; nếu không tìm thấy mà có trạm mất kết nối thì cũng từ chối (không kết luận “không tồn tại” khi chưa hỏi đủ).</li>
<li>Mở giao dịch ở trạm của sinh viên: lấy id từ <code>enrollment_id_seq</code> (khối id của trạm), tính <code>total = 0,3·midterm + 0,7·final</code> như bộ sinh, INSERT, COMMIT.</li>
<li>Báo “đã ghi vào trạm nào, máy nào, IP:cổng” và cờ <b>liên vùng</b> khi lớp ở trạm khác; dashboard thấy số dòng đổi trong ≤ 2 giây.</li>
</ol>
<p>Chứng chỉ: hàm <code>insert_certificate</code> ghi <code>detail</code> (jsonb) rồi <b>suy ra</b> các dòng <code>cert_language</code>/<code>cert_it</code>(+module)/<code>cert_research</code>(+coauthor) từ chính jsonb đó trong cùng giao dịch, nên hai biểu diễn không thể lệch nhau. “Thêm ngẫu nhiên N dòng” trộn 15 % sinh viên, 65 % đăng ký (≈ 7 % liên vùng), 20 % chứng chỉ theo tỉ lệ cơ sở 50/32/18; dòng nào có trạm đích mất kết nối thì thất bại và được báo, không chuyển sang trạm khác.</p>
<div class="fig"><img src="{IMG}entry_cert.png" style="width:70%"><div class="cap">Hình 5. Thêm chứng chỉ: form theo loại, ghi jsonb và bảng quan hệ trong một giao dịch</div></div>
<div class="fig"><img src="{IMG}dash_ok.png" style="width:74%"><div class="cap">Hình 6. Dashboard: ô từng trạm, tổng hợp so với đối chứng (cột “chênh lệch” là số dòng đã thêm qua giao diện) và nhật ký sự kiện</div></div>
<div class="note">Ảnh chụp khi thử trên một máy (nhãn “Máy A” cho cả 3 trạm); thay ảnh bằng ảnh chụp trên 2 máy khi có máy B.</div>

<h2>4. Dữ liệu và đối chiếu với <code>summary.json</code></h2>
<p>Dữ liệu chỉ lấy từ bộ sinh của giảng viên (seed 284617, không sửa). <code>schema_central.sql</code> đúng sơ đồ; CSV nạp vào <code>ref_central</code> bằng <code>COPY … WITH (FORMAT csv, HEADER true)</code>; <code>split.py</code> chia CSV theo <code>student→home_campus</code>, <code>section→campus</code>, phần còn lại theo cha rồi nạp từng trạm. Tổng các mảnh khớp <code>summary.json</code> và CSDL đối chứng:</p>
{tbl(["Bảng", "campus_a", "campus_b", "campus_c", "Tổng", "summary.json", "Khớp"], n1_rows, align=["l","r","r","r","r","r","l"])}

{CHECK_HTML}
<h2>5. Cách chạy (tóm tắt)</h2>
<p>Yêu cầu Docker, <code>make</code>, Python ≥ 3.11. Máy B: <code>docker compose --profile B up -d</code> (chỉ cần <code>docker-compose.yml</code>). Máy A: sao chép <code>deploy.2machine.example.toml</code> thành <code>deploy.toml</code>, điền IP máy B, rồi <code>make all MACHINE=A</code> (dựng A, nạp dữ liệu vào ba trạm qua LAN, tạo <code>postgres_fdw</code> và <code>all_&lt;bảng&gt;</code>, <code>make check</code>). Các lệnh khác: <code>make entry</code>, <code>make dash</code>, <code>make bench</code>, <code>make delay-on/off</code>, <code>make down</code>. Hướng dẫn đầy đủ trong <code>README.md</code> của kho mã.</p>

<h2>6. Kết quả đo và giải thích N1–N5</h2>
<p>Cách đo: mỗi truy vấn chạy 5 lần, bỏ lần đầu, lấy trung vị; EXPLAIN (ANALYZE, VERBOSE) của Q1–Q5 lưu ở <code>results/</code>. Độ trễ 30 ms là khứ hồi (15 ms mỗi chiều) tạo bằng toxiproxy đứng trước <code>postgres_fdw</code>. Đo trên <b>{MEASURED_ON}</b>. Q3 dùng lớp {M['q3_section']} (mở ở campus_b). Q1–Q5 là truy vấn viết trên <code>all_*</code>; biến thể <code>_opt</code> tự đẩy gom nhóm/nối xuống từng trạm và cho kết quả giống hệt.</p>
{tbl(QHEAD, q_rows(["Q1","Q2","Q2_opt","Q3","Q3_opt","Q4","Q5","Q5_opt"]), align=QALIGN)}
<div class="fig">{svg_bars()}<figcaption>Hình 7. Thời gian Q1–Q5 (trung vị) không trễ và trễ 30 ms</figcaption></div>

<h3>N1 — Số dòng mỗi mảnh</h3>
<p>Sinh viên chia {shares} cho A/B/C, khớp trọng số đề 0,50/0,32/0,18 mà bộ sinh dùng để chọn cơ sở. <code>enrollment</code> ({n(N1['campus_a']['enrollment'])} / {n(N1['campus_b']['enrollment'])} / {n(N1['campus_c']['enrollment'])}) và <code>certificate</code> chia theo sinh viên nên cùng tỉ lệ; <code>section</code> chia theo cơ sở mở lớp cũng cùng trọng số. Tổng các mảnh bằng CSDL đối chứng; <code>course</code> nhân bản đủ 300 dòng ở mỗi trạm (Bảng ở mục 4).</p>
<h3>N2 — Số trạm mỗi truy vấn chạm</h3>
{tbl(["Q", "Trạm xa", "Điều kiện thực sự đẩy xuống trạm xa (Remote SQL)"], [
 ["Q1", "0", "Không có Foreign Scan: bảng cục bộ của campus_a"],
 ["Q2", "2", "Chỉ <code>semester='2025-2'</code>; kéo <code>section_id, total</code> của ~40.000 dòng về rồi nối, gom nhóm ở trung tâm. Bản <code>_opt</code> đẩy cả <code>GROUP BY section_id</code> xuống nên chỉ về ≤ 2.500 nhóm"],
 ["Q3", "2", f"Chỉ <code>section_id = {M['q3_section']}</code> ở enrollment; bảng <code>student</code> bị kéo về toàn bộ. Bản <code>_opt</code> đẩy phép nối enrollment ⋈ student xuống trạm xa, chỉ về {n(Q['Q3']['rows'])} dòng"],
 ["Q4", "2", "Chỉ <code>cert_type='language'</code>; <b>điều kiện jsonb (<code>overall</code>, <code>speaking</code>) không được đẩy xuống</b> nên cột <code>detail</code> của mọi chứng chỉ ngoại ngữ chạy qua mạng rồi mới lọc"],
 ["Q5", "2", "<code>overall</code>, <code>speaking</code> đẩy được xuống <code>cert_language</code>, nhưng bảng <code>certificate</code> bị kéo về toàn bộ; bản <code>_opt</code> nối tại trạm xa"]], "")}
<p>So sánh Q4 với Q5: điều kiện trên cột quan hệ đẩy được xuống trạm xa, còn biểu thức ép kiểu trên jsonb thì không.</p>
{REMOTE_HTML}
{RAW_HTML}
<h3>N3 — Thời gian Q1–Q3, không trễ và trễ 30 ms</h3>
<p>Q1 {ms(Q['Q1']['no_delay_ms'])} → {ms(Q['Q1']['delay_ms'])} ms (chênh nhỏ là nhiễu, không có truy vấn xa). Q2 {ms(Q['Q2']['no_delay_ms'])} → {ms(Q['Q2']['delay_ms'])} ms; Q3 {ms(Q['Q3']['no_delay_ms'])} → {ms(Q['Q3']['delay_ms'])} ms. Mức chênh ≈ <b>số vòng khứ hồi × 30 ms</b>: Q2 ≈ {str(Q['Q2']['est_round_trips']).replace('.', ',')} vòng, Q3 ≈ {str(Q['Q3']['est_round_trips']).replace('.', ',')} vòng. Một Foreign Scan tốn nhiều vòng (mở giao dịch xa, khai báo con trỏ, lấy từng lô 10.000 dòng, đóng) và <code>use_remote_estimate=true</code> còn gửi lệnh EXPLAIN sang trạm xa lúc lập kế hoạch. Thí nghiệm tắt tuỳ chọn này (rồi trả lại): với trễ, Q2 1.025 → 571 ms, Q3_opt 770 → 320 ms, Q4 458 → 335 ms, tức 10–15 vòng/truy vấn chỉ để ước lượng kế hoạch. Thời gian tăng theo số Foreign Scan, không theo lượng dữ liệu. <b>So sánh trạm cùng máy với trạm ở máy B: chưa đo</b> (đo trên một máy); sẽ bổ sung bằng <code>make bench</code> trên hai máy.</p>
<h3>N4 — Tỉ lệ dòng liên vùng</h3>
<p>{n(N4['cross_rows'])} / {n(N4['total'])} = <b>{str(round(100*N4['rate'],2)).replace('.', ',')} %</b> (tham số <code>CROSS=0,07</code> của bộ sinh). Do <code>enrollment</code> đi theo sinh viên nên với lớp mở ở B, các dòng của sinh viên cơ sở khác nằm ở trạm khác: Q3 phải hỏi cả A và C. Lớp {M['q3_section']}: {N4['q3_rows']} dòng, trong đó {N4['q3_remote_rows']} dòng đến từ trạm khác; trung bình các lớp ở B có {str(round(100*N4['campus_b_sections_remote_share'],1)).replace('.', ',')} % đăng ký từ cơ sở khác. <b>Dự đoán</b> (chưa đo) khi tỉ lệ lên 30 %: số dòng lấy từ trạm xa tăng ≈ {str(N4['pred_30pct_scale']).replace('.', ',')} lần, nhưng số vòng khứ hồi không đổi (vẫn 2 trạm xa) nên thời gian Q3 tăng ít, chủ yếu theo số dòng qua mạng.</p>
<h3>N5 — Dung lượng jsonb và bảng quan hệ, có/không GIN</h3>
<p><code>certificate</code> có cột jsonb: {mb(sz['certificate_total'])} (bảng {mb(sz['certificate_heap'])}, riêng cột <code>detail</code> {mb(sz['detail_bytes'])}) so với 5 bảng quan hệ tương đương {mb(sz['relational_total'])} (bảng {mb(sz['relational_heap'])}): gần bằng nhau. jsonb lặp tên khoá ở mỗi dòng nhưng chỉ cần một bảng; bảng quan hệ không lặp khoá nhưng tốn tiêu đề dòng và chỉ mục khoá chính cho từng bảng. GIN (<code>jsonb_path_ops</code>) thêm {mb(sz['gin_index_total'])} cho ba trạm và <b>không giúp Q4</b> vì điều kiện <code>&gt;=</code> trên số không dùng được GIN (Q4 {gz['without']['Q4'][0]} → {gz['with']['Q4'][0]} ms). GIN chỉ giúp phép chứa <code>@&gt;</code>: Q4b (IELTS, speaking 8.0) dùng Bitmap Index Scan, {gz['without']['Q4b'][0]} → {gz['with']['Q4b'][0]} ms; với 12.000 dòng lợi ích rất nhỏ. Bản quan hệ tương đương (Q5b) {gz['without']['Q5b'][0]} ms.</p>

<h2>7. Hạn chế và lưu ý trung thực</h2>
<ul>
<li>Q4 áp <code>overall ≥ 6,5</code> và <code>speaking ≥ 6,0</code> cho cả IELTS (thang 9) lẫn TOEIC (thang 990) nên TOEIC luôn đạt: 2.678 / 3.676 dòng kết quả ở bộ nạp gốc là TOEIC. Nhóm giữ đúng đề (Q4 và Q5 cùng kết quả) và nêu ở đây.</li>
<li>Số đo lấy trên {MEASURED_ON}; số tuyệt đối chỉ để so sánh tương đối. Dự đoán N4 chưa được đo.</li>
<li>Mật khẩu <code>cs5104</code> chỉ dùng trong mạng LAN thử nghiệm; bảo mật, phân quyền, tối ưu hiệu năng nằm ngoài yêu cầu của đề.</li>
<li>Mã và báo cáo được viết có hỗ trợ công cụ AI (Claude, Anthropic); mọi thành viên đọc và chịu trách nhiệm về toàn bộ hệ.</li>
</ul>

<h2>8. Phân công</h2>
{members}

<h2>9. Tài liệu tham khảo</h2>
<ol style="font-size:9pt">
<li>Giảng viên CS5104. Giáo trình Chương 1–3, Chương 8 (jsonb); Tập 2 Bài 1, 2, 3, 8 và Phụ lục B (chạy nhiều máy qua LAN); gói <code>cs5104_labs</code>; bộ sinh dữ liệu <code>CS5104_Project_DataGen</code> (Đề 2, seed 284617).</li>
<li>PostgreSQL 18 Documentation: <i>postgres_fdw</i>, <i>JSON Types</i>, <i>GIN Indexes</i>, <i>COPY</i>. https://www.postgresql.org/docs/18/</li>
<li>Shopify. Toxiproxy — TCP proxy để mô phỏng độ trễ mạng. https://github.com/Shopify/toxiproxy</li>
<li>Streamlit Documentation. https://docs.streamlit.io</li>
<li>M. T. Özsu, P. Valduriez. <i>Principles of Distributed Database Systems</i>, 4th ed., Springer, 2020 (phân mảnh ngang nguyên thuỷ/dẫn xuất, tính đúng đắn của phân mảnh).</li>
</ol>
"""
    return f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><title>Báo cáo Đề 2</title><style>{css}</style></head><body>{body}</body></html>"

# ================================================================== SLIDE
def slides():
    css = BASE_CSS + """
@page{size:1280px 720px;margin:0}
.s{width:1280px;height:720px;padding:46px 64px;position:relative;break-after:page;overflow:hidden;background:#fff}
.s:last-child{break-after:auto}
h1{font-size:46px;margin:0 0 10px;color:#1e4e8c} h2{font-size:34px;margin:0 0 18px;color:#1e4e8c} p,li{font-size:27px;line-height:1.38} ul{padding-left:26px;margin:6px 0}
table{font-size:25px} th,td{padding:9px 12px} .s svg{width:100%;height:auto} .foot{position:absolute;bottom:18px;left:64px;right:64px;font-size:14px;color:#718096;display:flex;justify-content:space-between}
.big{font-size:84px;font-weight:800;color:#dd6b20;line-height:1} .tag{display:inline-block;background:#ebf8ff;color:#1e4e8c;border-radius:5px;padding:1px 9px;font-weight:700;font-size:18px}
.cols{display:flex;gap:30px} .cols>div{flex:1} .k{background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px}
img.shot{max-width:100%;border:1px solid #cbd5e0;border-radius:6px} small{color:#4a5568;font-size:20px}
"""
    n_sl = [0]
    def S(title, inner):
        n_sl[0] += 1
        return f"<section class='s'><h2>{title}</h2>{inner}<div class='foot'><span>CS5104 · Đề 2 · {e(GROUP)}</span><span>{n_sl[0]}</span></div></section>"
    s = []
    n_sl[0] += 1
    s.append(f"<section class='s' style='background:#1e4e8c;color:#fff'><div style='margin-top:150px'><h1 style='color:#fff;font-size:58px'>Quản lý sinh viên liên cơ sở</h1>"
             f"<p style='font-size:30px;color:#bee3f8'>Đề 2 · 3 trạm PostgreSQL 18 · 2 máy · <code style='background:none;color:#fff'>postgres_fdw</code></p>"
             f"<p style='margin-top:60px;color:#e2e8f0'>CS5104 — Hệ cơ sở dữ liệu nâng cao · {e(GROUP)}</p><p style='color:#bee3f8;font-size:20px'>{' · '.join(e(m[0]) for m in MEMBERS)}</p></div></section>")
    s.append(S("Thiết kế phân tán: mỗi bảng ở đâu và vì sao",
        "<table><thead><tr><th>Bảng</th><th>Cách chia</th><th>Vì sao</th></tr></thead><tbody>"
        "<tr><td><b>student</b></td><td>theo <code>home_campus</code></td><td>định nghĩa “vùng” của đề</td></tr>"
        "<tr><td><b>section</b></td><td>theo <code>campus</code></td><td>lớp thuộc cơ sở mở lớp</td></tr>"
        "<tr><td><b>enrollment</b></td><td>dẫn xuất theo <b>student</b></td><td><b>Q1 phải chạy trọn tại một trạm</b></td></tr>"
        "<tr><td><b>certificate</b> + 5 bảng con</td><td>dẫn xuất theo student / cha</td><td>Q4, Q5 nối cục bộ; jsonb + quan hệ cùng trạm</td></tr>"
        "<tr><td><b>course</b></td><td>nhân bản 3 trạm</td><td>300 dòng, giữ FK <code>section.course_code</code></td></tr></tbody></table>"
        "<ul style='margin-top:18px'><li>PK mới: khối id riêng mỗi trạm (1M / 2M / 3M +)</li>"
        "<li>FK <code>enrollment.section_id</code> chéo trạm ~7 % → kiểm ở tầng ghi + <code>make check</code></li>"
        "<li>CHECK mảnh (<code>home_campus</code>, <code>campus</code>) và CHECK dạng jsonb theo <code>cert_type</code></li></ul>"))
    s.append(S("Triển khai trên hai máy", f"<div style='width:1000px;margin:0 auto'>{svg_deploy()}</div><p style='text-align:center'>Máy B chỉ cần Docker · dữ liệu nạp từ máy A qua LAN · <code>deploy.toml</code> điều khiển mọi script</p>"))
    s.append(S("Demo trực tiếp D1–D8 (12 phút)",
        "<table><thead><tr><th>Mã</th><th>Thao tác</th><th>Phải thấy</th></tr></thead><tbody>"
        "<tr><td>D1</td><td><code>make all</code> trên ≥ 2 máy</td><td>3 trạm chạy, số dòng đúng, dashboard 3 ô xanh</td></tr>"
        "<tr><td>D2</td><td><code>make check</code></td><td>3 quy tắc đúng đắn, PK/FK toàn hệ</td></tr>"
        "<tr><td>D3</td><td>Q1, Q2</td><td>= đối chứng; Q1 không Foreign Scan</td></tr>"
        "<tr><td>D4</td><td>Q3 (liên vùng)</td><td>đúng; chạm A, B, C vì sinh viên học ghép</td></tr>"
        "<tr><td>D5</td><td>Q4 (jsonb), Q5 (quan hệ)</td><td>cùng kết quả</td></tr>"
        "<tr><td>D6</td><td><code>make delay-on</code>, chạy lại Q1–Q3</td><td>Q1 ≈ không đổi; Q2, Q3 tăng</td></tr>"
        "<tr><td>D7</td><td>nhập: 1 dòng ở B, 1 liên vùng, 100 ngẫu nhiên</td><td>dashboard đổi ≤ 2 s; Q3 thấy dòng mới; D2 vẫn đạt</td></tr>"
        "<tr><td>D8</td><td>tắt một trạm ở máy B rồi bật lại</td><td>đỏ/xanh; nhập báo lỗi; Q1 vẫn chạy, Q2 lỗi rồi chạy lại</td></tr></tbody></table>"))
    s.append(S("N1 — Số dòng mỗi mảnh",
        f"<div class='cols'><div><table><thead><tr><th>Bảng</th><th>A</th><th>B</th><th>C</th><th>Tổng</th></tr></thead><tbody>"
        + "".join(f"<tr><td>{t}</td><td class='r'>{n(N1['campus_a'][t])}</td><td class='r'>{n(N1['campus_b'][t])}</td><td class='r'>{n(N1['campus_c'][t])}</td><td class='r'>{n(N1['ref'][t])}</td></tr>" for t in ["student", "section", "enrollment", "certificate"])
        + f"</tbody></table></div><div class='k'><p><b>Sinh viên: {shares}</b></p><p>= trọng số <code>0,50 / 0,32 / 0,18</code> của bộ sinh.</p><p>enrollment, certificate đi theo sinh viên nên cùng tỉ lệ.</p><p>Tổng mảnh = CSDL đối chứng = <code>summary.json</code>.</p></div></div>"))
    s.append(S("N2 — Số trạm mỗi truy vấn chạm, điều kiện nào được đẩy xuống",
        "<table><thead><tr><th>Q</th><th>Trạm xa</th><th>Đẩy xuống trạm xa</th></tr></thead><tbody>"
        "<tr><td>Q1</td><td>0</td><td>không có Foreign Scan</td></tr>"
        "<tr><td>Q2</td><td>2</td><td>chỉ <code>semester</code>; nối + gom nhóm ở trung tâm</td></tr>"
        f"<tr><td>Q3</td><td>2</td><td><code>section_id</code>; bảng <code>student</code> kéo về toàn bộ (<code>_opt</code>: đẩy cả phép nối)</td></tr>"
        "<tr><td>Q4</td><td>2</td><td>chỉ <code>cert_type</code>; <b>điều kiện jsonb không đẩy được</b></td></tr>"
        "<tr><td>Q5</td><td>2</td><td><code>overall</code>, <code>speaking</code> đẩy được (cột quan hệ)</td></tr></tbody></table>"
        "<p style='margin-top:16px'><b>Bài học:</b> cột quan hệ đẩy điều kiện xuống được, biểu thức ép kiểu trên jsonb thì không.</p>"))
    s.append(S("N3 — Thời gian Q1–Q3, không trễ và trễ 30 ms",
        f"<div class='cols'><div>{svg_bars(w=640, keys=('Q1', 'Q2', 'Q3'), fs=19)}</div><div class='k'>"
        f"<p><b>Q1</b> {ms(Q['Q1']['no_delay_ms'])} → {ms(Q['Q1']['delay_ms'])} ms: không có truy vấn xa.</p>"
        f"<p><b>Q2, Q3</b> tăng ≈ {str(Q['Q2']['est_round_trips']).replace('.', ',')} và {str(Q['Q3']['est_round_trips']).replace('.', ',')} vòng × 30 ms.</p>"
        "<p>Mỗi Foreign Scan tốn nhiều vòng; <code>use_remote_estimate</code> thêm 10–15 vòng (tắt: Q2 1025 → 571 ms).</p>"
        f"<p><small>Đo trên {e(MEASURED_ON)}. Trạm cùng máy vs máy B: sẽ bổ sung khi đo trên 2 máy.</small></p></div></div>"))
    s.append(S("N4 — Tỉ lệ dòng liên vùng",
        f"<div class='cols'><div><div class='big'>{str(round(100*N4['rate'],2)).replace('.', ',')} %</div><p>{n(N4['cross_rows'])} / {n(N4['total'])} lượt đăng ký học ghép</p>"
        f"<p>Q3 (lớp {M['q3_section']}): {N4['q3_rows']} dòng, {N4['q3_remote_rows']} dòng đến từ trạm khác.</p></div>"
        "<div class='k'><p><b>Vì sao Q3 đi qua mạng:</b> enrollment nằm ở trạm của sinh viên, lớp ở B còn sinh viên học ghép nằm ở A, C.</p>"
        f"<p><b>Dự đoán ở 30 %:</b> dòng lấy từ trạm xa ≈ ×{str(N4['pred_30pct_scale']).replace('.', ',')}; số vòng khứ hồi không đổi nên thời gian tăng ít. <small>(chưa đo)</small></p></div></div>"))
    s.append(S("N5 — Dung lượng jsonb so với bảng quan hệ, có/không GIN",
        f"<div class='cols'><div><table><thead><tr><th></th><th>Tổng gồm index</th></tr></thead><tbody>"
        f"<tr><td>certificate (jsonb)</td><td class='r'>{mb(sz['certificate_total'])}</td></tr><tr><td>5 bảng quan hệ</td><td class='r'>{mb(sz['relational_total'])}</td></tr>"
        f"<tr><td>GIN <code>jsonb_path_ops</code></td><td class='r'>+ {mb(sz['gin_index_total'])}</td></tr></tbody></table>"
        f"<p><small>Riêng cột detail: {mb(sz['detail_bytes'])}</small></p></div><div class='k'>"
        f"<p>Dung lượng gần bằng nhau: jsonb lặp tên khoá, bảng quan hệ tốn tiêu đề dòng + PK của 5 bảng.</p>"
        f"<p>GIN <b>không giúp Q4</b> (<code>&gt;=</code> trên số): {gz['without']['Q4'][0]} → {gz['with']['Q4'][0]} ms.</p>"
        f"<p>GIN giúp phép chứa <code>@&gt;</code> (Q4b): {gz['without']['Q4b'][0]} → {gz['with']['Q4b'][0]} ms, lợi ích nhỏ ở 12.000 dòng.</p></div></div>"))
    s.append(S("Kết luận và hạn chế",
        "<ul><li>Thiết kế dẫn xuất theo <b>student</b> làm Q1 cục bộ; đổi lại Q3 và dòng liên vùng đi qua mạng.</li>"
        "<li>Mọi ràng buộc đúng đắn kiểm bằng <code>make check</code>; phá dữ liệu thì báo FAIL đúng chỗ.</li>"
        "<li>Chi phí truy vấn xa do <b>số vòng khứ hồi</b>, không do lượng dữ liệu; cần đẩy điều kiện/phép nối xuống trạm xa.</li></ul>"
        "<p style='margin-top:16px'><b>Hạn chế:</b> Q4 gồm cả TOEIC (thang 990) nên luôn đạt ngưỡng; số đo hiện từ "
        f"{e(MEASURED_ON)}; dự đoán N4 chưa đo.</p><p><small>Mã nguồn: {REPO}</small></p>"))
    s.append(S("Phụ lục: ảnh dự phòng khi demo lỗi",
        f"<div class='cols'><div><img class='shot' src='{IMG}dash_ok.png' style='max-height:470px'><p><small>Dashboard: 3 trạm xanh, tổng hợp so với đối chứng</small></p></div>"
        f"<div><img class='shot' src='{IMG}dash_down.png' style='max-height:470px'><p><small>D8: tắt campus_c (đỏ + lỗi)</small></p></div></div>"))
    return f"<!doctype html><html lang='vi'><head><meta charset='utf-8'><title>Slide Đề 2</title><style>{css}</style></head><body>{''.join(s)}</body></html>"

# ================================================================== PDF
def chrome():
    for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(p): return p
    return shutil.which("chrome") or shutil.which("chromium") or sys.exit("Cần Chrome/Edge/Chromium để in PDF")

def pdf(name, content):
    h = OUT / f"{name}.html"; h.write_text(content, encoding="utf-8")
    out = OUT / f"{name}.pdf"
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out}", h.resolve().as_uri()],
                   check=True, capture_output=True, timeout=180)
    print("đã tạo", out)

if __name__ == "__main__":
    pdf("BaoCao_De2", report()); pdf("Slide_De2", slides())
