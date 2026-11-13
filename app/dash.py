"""Dashboard theo dõi (máy A). Chạy: streamlit run app/dash.py --server.port 8502
Đọc THẲNG từng trạm (không qua postgres_fdw), tự làm mới mỗi 2 giây."""
import datetime as dt
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

st.set_page_config(page_title="Dashboard — Sinh viên liên cơ sở", page_icon="📊", layout="wide")
st.title("📊 Dashboard — Quản lý sinh viên liên cơ sở")

COUNT_SQL = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in c.TABLES)


@st.cache_resource
def state():
    """Trạng thái dùng chung giữa các lần chạy lại: đếm trước đó, trạng thái trước đó, nhật ký, đối chứng."""
    return {"prev_counts": {}, "prev_up": {}, "events": [], "baseline": None}


def poll(site):
    t0 = time.perf_counter()
    try:
        conn = c.connect(site, timeout=1)
    except c.StationDown as e:
        return {"up": False, "err": str(e), "counts": None, "ms": None}
    try:
        with conn.cursor() as cur:
            cur.execute(COUNT_SQL)
            counts = dict(cur.fetchall())
        return {"up": True, "err": "", "counts": counts, "ms": round((time.perf_counter() - t0) * 1000)}
    except Exception as e:
        return {"up": False, "err": str(e).splitlines()[0], "counts": None, "ms": None}
    finally:
        conn.close()


def baseline():
    """Số dòng của CSDL đối chứng ref_central (tải một lần, giữ lại khi A mất kết nối)."""
    s = state()
    if s["baseline"] is None:
        try:
            conn = c.connect("campus_a", dbname="ref_central", timeout=1)
            with conn, conn.cursor() as cur:
                cur.execute(COUNT_SQL); s["baseline"] = dict(cur.fetchall())
            conn.close()
        except Exception:
            pass
    return s["baseline"]


def log(msg, level="info"):
    ev = state()["events"]
    ev.insert(0, {"giờ": dt.datetime.now().strftime("%H:%M:%S"), "mức": level, "sự kiện": msg})
    del ev[200:]


@st.fragment(run_every=2)
def live():
    s = state()
    with ThreadPoolExecutor(len(c.SITES)) as ex:
        res = dict(zip(c.SITES, ex.map(poll, c.SITES)))
    # --- phát hiện sự kiện
    for site, r in res.items():
        was = s["prev_up"].get(site)
        if was is not None and was != r["up"]:
            log(f"Trạm {site} {'KẾT NỐI LẠI' if r['up'] else 'MẤT KẾT NỐI'}", "ok" if r["up"] else "lỗi")
        if r["up"]:
            prev = s["prev_counts"].get(site)
            if prev:
                for t in c.TABLES:
                    d = r["counts"][t] - prev[t]
                    if d:
                        log(f"{site}.{t}: {'+' if d > 0 else ''}{d} dòng (nay {r['counts'][t]})")
            s["prev_counts"][site] = r["counts"]
        s["prev_up"][site] = r["up"]

    # --- ô từng trạm
    cols = st.columns(len(c.SITES))
    for col, site in zip(cols, c.SITES):
        r, cfg = res[site], c.STATIONS[site]
        with col, st.container(border=True):
            st.markdown(f"### {'🟢' if r['up'] else '🔴'} {site}")
            st.caption(f"Máy **{cfg['machine']}** · IP **{cfg['host']}:{cfg['port']}** · "
                       + (f"{r['ms']} ms" if r["up"] else "không kết nối"))
            if r["up"]:
                m = r["counts"]
                a, b, d = st.columns(3)
                a.metric("student", f"{m['student']:,}"); b.metric("enrollment", f"{m['enrollment']:,}"); d.metric("certificate", f"{m['certificate']:,}")
                st.dataframe(pd.DataFrame({"bảng": c.TABLES, "số dòng": [m[t] for t in c.TABLES]}),
                             hide_index=True, width="stretch", height=250)
            else:
                st.error(r["err"] or "Mất kết nối")

    # --- bảng tổng hợp so với đối chứng
    base = baseline()
    rows = []
    for t in c.TABLES:
        vals = {site: (res[site]["counts"][t] if res[site]["up"] else None) for site in c.SITES}
        known = [v for v in vals.values() if v is not None]
        replicated = t == "course"
        total = (max(known) if replicated else sum(known)) if known else None
        partial = len(known) < len(c.SITES)
        row = {"bảng": t + (" (nhân bản)" if replicated else "")}
        row.update({site: vals[site] for site in c.SITES})
        row["tổng"] = total if total is None or not partial else f"{total}+ (thiếu trạm)"
        row["đối chứng"] = base[t] if base else None
        row["chênh lệch"] = (total - base[t]) if (base and total is not None and not partial) else None
        rows.append(row)
    st.subheader("Tổng hợp so với CSDL đối chứng")
    st.caption("Đối chứng là `ref_central` lúc nạp. Chênh lệch = số dòng đã thêm qua giao diện nhập liệu kể từ đó (0 nếu chưa thêm gì).")
    st.dataframe(pd.DataFrame(rows).astype(object), hide_index=True, width="stretch")

    st.subheader("Nhật ký sự kiện")
    if s["events"]:
        st.dataframe(pd.DataFrame(s["events"][:40]), hide_index=True, width="stretch", height=260)
    else:
        st.caption("Chưa có sự kiện. Thêm dòng ở giao diện nhập liệu hoặc tắt/bật một trạm để thấy thay đổi.")
    st.caption(f"Làm mới lúc {dt.datetime.now():%H:%M:%S} · mỗi 2 giây")


live()
