"""Giao diện nhập liệu (máy A). Chạy: streamlit run app/entry.py --server.port 8501"""
import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

st.set_page_config(page_title="Nhập liệu — Sinh viên liên cơ sở", page_icon="🎓", layout="wide")
st.title("🎓 Nhập liệu — Quản lý sinh viên liên cơ sở")
st.caption("Mỗi dòng được ghi thẳng vào đúng trạm theo thiết kế phân tán. Trạm đích mất kết nối thì báo lỗi, không ghi sang trạm khác.")


def ping(site):
    try:
        c.connect(site, timeout=1).close(); return True
    except c.StationDown:
        return False


@st.fragment(run_every=3)
def station_status():
    with ThreadPoolExecutor(len(c.SITES)) as ex:
        res = dict(zip(c.SITES, ex.map(ping, c.SITES)))
    for s, ok in res.items():
        st.markdown(f"{'🟢' if ok else '🔴'} **{s}**  \n<small>máy {c.STATIONS[s]['machine']} · {c.STATIONS[s]['host']}:{c.STATIONS[s]['port']}</small>",
                    unsafe_allow_html=True)


with st.sidebar:
    st.subheader("Trạng thái trạm")
    station_status()


def write(site, fn):
    """Mở giao dịch ở đúng trạm `site`, chạy fn(cur); lỗi thì rollback và báo, không chuyển trạm."""
    conn = c.connect(site)
    try:
        with conn, conn.cursor() as cur:
            return fn(cur)
    finally:
        conn.close()


def report(ok_msg=None, err=None):
    if err:
        st.error(f"❌ {err}")
    else:
        st.success(ok_msg)


tab_st, tab_en, tab_ce, tab_rd = st.tabs(["Sinh viên", "Đăng ký học phần (kể cả liên vùng)", "Chứng chỉ (jsonb)", "Thêm ngẫu nhiên"])

# ------------------------------------------------------------------ Sinh viên
with tab_st:
    with st.form("f_student", clear_on_submit=True):
        c1, c2 = st.columns(2)
        site = c1.selectbox("Cơ sở theo học (trạm đích)", c.SITES)
        name = c2.text_input("Họ tên")
        c3, c4, c5 = st.columns(3)
        birth = c3.number_input("Năm sinh", 1990, 2010, 2003)
        major = c4.selectbox("Mã ngành", c.MAJORS)
        intake = c5.number_input("Năm nhập học", 2015, 2026, 2024)
        if st.form_submit_button("Thêm sinh viên", type="primary"):
            try:
                if not name.strip():
                    raise ValueError("Cần nhập họ tên.")
                sid = write(site, lambda cur: c.insert_student(cur, site, name.strip(), int(birth), major, int(intake)))
                report(f"✅ Đã ghi sinh viên **{sid}** vào trạm **{c.where(site)}**.")
            except (c.StationDown, ValueError) as e:
                report(err=str(e))
            except Exception as e:  # lỗi ràng buộc
                report(err=f"Trạm {site} từ chối: {e}")

# ------------------------------------------------------------------ Đăng ký
with tab_en:
    st.caption("Dòng đăng ký nằm ở trạm của **sinh viên**; lớp có thể mở ở cơ sở khác (liên vùng). Học kỳ lấy theo lớp.")
    with st.form("f_enroll", clear_on_submit=False):
        c1, c2 = st.columns(2)
        sid = c1.number_input("Mã sinh viên", 1, step=1, value=1)
        secid = c2.number_input("Mã lớp học phần", 1, step=1, value=1)
        c3, c4 = st.columns(2)
        mid = c3.number_input("Điểm giữa kỳ", 0.0, 10.0, 6.5, 0.1)
        fin = c4.number_input("Điểm cuối kỳ", 0.0, 10.0, 6.5, 0.1)
        if st.form_submit_button("Thêm đăng ký", type="primary"):
            try:
                st_site, _ = c.find_row("SELECT 1 FROM student WHERE student_id=%s", (int(sid),))
                if not st_site:
                    raise ValueError(f"Không có sinh viên {int(sid)}.")
                sec_site, row = c.find_row("SELECT semester FROM section WHERE section_id=%s", (int(secid),))
                if not sec_site:
                    raise ValueError(f"Không có lớp học phần {int(secid)}.")
                sem = row[0]
                eid = write(st_site, lambda cur: c.insert_enrollment(cur, int(sid), int(secid), sem, float(mid), float(fin)))
                cross = " · **liên vùng**" if st_site != sec_site else ""
                report(f"✅ Đã ghi đăng ký **{eid}** (kỳ {sem}) vào trạm **{c.where(st_site)}**. "
                       f"Sinh viên ở {st_site}, lớp ở {sec_site}{cross}.")
            except (c.StationDown, ValueError) as e:
                report(err=str(e))
            except Exception as e:
                report(err=f"Trạm từ chối: {e}")

# ------------------------------------------------------------------ Chứng chỉ
with tab_ce:
    st.caption("Chọn loại chứng chỉ → form hiện đúng các trường của loại đó. Cột `detail` (jsonb) và bảng quan hệ tương đương được ghi trong **một giao dịch**.")
    c1, c2 = st.columns(2)
    sid2 = c1.number_input("Mã sinh viên", 1, step=1, value=1, key="cert_sid")
    ctype = c2.selectbox("Loại chứng chỉ", ["language", "it", "research"], key="cert_type")
    with st.form("f_cert", clear_on_submit=False):
        issued = st.date_input("Ngày cấp", dt.date(2026, 1, 15))
        detail = None
        if ctype == "language":
            test = st.selectbox("Kỳ thi", ["IELTS", "TOEIC"])
            if test == "IELTS":
                cols = st.columns(4)
                sk = [cols[i].number_input(n, 0.0, 9.0, 6.0, 0.5, key=f"i_{n}") for i, n in enumerate(["Nghe", "Đọc", "Viết", "Nói"])]
            else:
                cols = st.columns(4)
                sk = [cols[i].number_input(n, 0, 495, 300, 5, key=f"t_{n}") for i, n in enumerate(["Nghe", "Đọc", "Viết", "Nói"])]
            detail = c.language_detail(test, *sk)
            st.caption(f"Điểm tổng tự tính: **{detail['overall']}**")
        elif ctype == "it":
            nm = st.selectbox("Tên chứng chỉ", list(c.IT_CERTS))
            lvl = st.selectbox("Cấp độ", ["core", "expert", "associate"])
            mods = st.multiselect("Mô-đun", c.IT_CERTS[nm], default=c.IT_CERTS[nm][:1])
            detail = {"name": nm, "level": lvl, "modules": mods}
        else:
            title = st.text_input("Tên công trình")
            venue = st.selectbox("Nơi công bố", c.VENUES)
            role = st.selectbox("Vai trò", ["first_author", "coauthor"])
            co = st.text_area("Đồng tác giả (mỗi dòng một tên)")
            detail = {"title": title, "venue": venue, "role": role, "coauthors": [x.strip() for x in co.splitlines() if x.strip()]}
        if st.form_submit_button("Thêm chứng chỉ", type="primary"):
            try:
                st_site, _ = c.find_row("SELECT 1 FROM student WHERE student_id=%s", (int(sid2),))
                if not st_site:
                    raise ValueError(f"Không có sinh viên {int(sid2)}.")
                if ctype == "it" and not detail["modules"]:
                    raise ValueError("Chọn ít nhất một mô-đun.")
                if ctype == "research" and not detail["title"].strip():
                    raise ValueError("Cần nhập tên công trình.")
                cid = write(st_site, lambda cur: c.insert_certificate(cur, int(sid2), ctype, issued, detail))
                report(f"✅ Đã ghi chứng chỉ **{cid}** ({ctype}) vào trạm **{c.where(st_site)}** (jsonb + bảng quan hệ, một giao dịch).")
                st.json(detail)
            except (c.StationDown, ValueError) as e:
                report(err=str(e))
            except Exception as e:
                report(err=f"Trạm từ chối: {e}")

# ------------------------------------------------------------------ Ngẫu nhiên
with tab_rd:
    n = st.number_input("Số dòng", 1, 5000, 100, 10)
    st.caption("Trộn: 15 % sinh viên, 65 % đăng ký (≈ 7 % liên vùng), 20 % chứng chỉ; chia theo tỉ lệ cơ sở 50/32/18.")
    if st.button("Thêm ngẫu nhiên N dòng", type="primary"):
        with st.spinner("Đang ghi…"):
            written, errors = c.random_rows(int(n))
        st.success("Đã ghi: " + " · ".join(f"{s}: {v}" for s, v in written.items()) + f" (tổng {sum(written.values())})")
        for s, e in errors.items():
            st.error(f"❌ {s}: {e}")
