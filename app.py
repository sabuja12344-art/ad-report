import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml
import os
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from meta_api import get_ad_thumbnails
from supabase_client import get_client as get_supabase_client, fetch_rows as fetch_supabase_rows

load_dotenv()

st.set_page_config(page_title="광고 대시보드", layout="wide", page_icon="📊")

# ── 설정 로드 ──────────────────────────────────────────
@st.cache_resource
def load_config():
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# ── 인증 ───────────────────────────────────────────────
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def get_users():
    try:
        return dict(st.secrets["users"])
    except Exception:
        return config.get("users", {})

def do_login(username, password):
    users = get_users()
    u = users.get(username)
    if u and u["password"] == hash_pw(password):
        return u
    return None

if "logged_in" not in st.session_state:
    st.session_state.update(logged_in=False, username=None, user_info=None)

if not st.session_state.logged_in:
    _, col, _ = st.columns([1, 1, 1])
    with col:
        st.markdown("## 📊 광고 대시보드")
        st.divider()
        with st.form("login"):
            uname = st.text_input("아이디")
            pw    = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인", use_container_width=True):
                user = do_login(uname, pw)
                if user:
                    st.session_state.update(logged_in=True, username=uname, user_info=user)
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    st.stop()

# ── 권한별 광고주 목록 ─────────────────────────────────
user_info = st.session_state.user_info
is_admin  = user_info.get("role") == "admin"
adv_list  = config["advertisers"]
visible   = adv_list if is_admin else [a for a in adv_list if a["name"] == user_info.get("advertiser")]

if not visible:
    st.error("접근 가능한 광고주가 없습니다.")
    st.stop()

# ── 사이드바 ───────────────────────────────────────────
with st.sidebar:
    st.title("📊 광고 대시보드")
    st.caption(f"로그인: {st.session_state.username}")
    if st.button("로그아웃", use_container_width=True):
        st.session_state.update(logged_in=False, username=None, user_info=None)
        st.rerun()
    st.divider()

    if is_admin and len(visible) > 1:
        selected_name = st.selectbox("광고주", [a["name"] for a in visible])
    else:
        selected_name = visible[0]["name"]
        st.markdown(f"**{selected_name}**")

    adv = next(a for a in adv_list if a["name"] == selected_name)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("시작일", datetime.now() - timedelta(days=7))
    with c2:
        end_date = st.date_input("종료일", datetime.now() - timedelta(days=1))

    if (end_date - start_date).days > 30:
        st.warning("최대 30일까지 조회 가능합니다.")
        st.stop()
    if start_date > end_date:
        st.error("시작일이 종료일보다 늦을 수 없습니다.")
        st.stop()

    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()

# ── 데이터 수집 ────────────────────────────────────────
def get_token():
    try:
        if "META_ACCESS_TOKEN" in st.secrets:
            return st.secrets["META_ACCESS_TOKEN"]
    except Exception:
        pass
    return os.environ.get("META_ACCESS_TOKEN", "")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_thumbnails(ad_account_id):
    return get_ad_thumbnails(ad_account_id, get_token())

@st.cache_resource
def supabase_client():
    try:
        return get_supabase_client()
    except KeyError:
        available_keys = list(st.secrets.keys()) if hasattr(st, "secrets") else []
        st.error(
            f"Supabase 연결 실패: SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 Secrets에 없습니다.\n\n"
            f"현재 등록된 Secret 키 목록: `{available_keys}`\n\n"
            "Streamlit Cloud → Manage app → Settings → Secrets 에서 키 이름을 확인하세요."
        )
        st.stop()

@st.cache_data(ttl=60, show_spinner=False)
def load_combined_rows(advertiser_name, start_str, end_str):
    return fetch_supabase_rows(supabase_client(), advertiser_name, start_str, end_str)

with st.spinner("데이터 불러오는 중..."):
    rows = load_combined_rows(selected_name, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

if not rows:
    st.warning("해당 기간에 데이터가 없습니다.")
    st.stop()

df = pd.DataFrame(rows)
df["날짜"] = pd.to_datetime(df["날짜"]).dt.date
df["비용"] = df["비용"].astype(float)
for col in ("구매전환수", "구매전환매출액"):
    df[col] = df[col].fillna(0) if col in df.columns else 0
extra_cols = [e["name"] for e in (adv.get("meta_extra_events") or [])]

# ── 헬퍼 ───────────────────────────────────────────────
def build_agg(source_df, group_cols):
    agg = {"비용":"sum", "노출":"sum", "클릭":"sum", "전환수":"sum"}
    has_purchase = "구매전환매출액" in source_df.columns and source_df["구매전환매출액"].sum() > 0
    if has_purchase:
        agg["구매전환매출액"] = "sum"
    for ec in extra_cols:
        if ec in source_df.columns:
            agg[ec] = "sum"
    result = source_df.groupby(group_cols).agg(**{k:(k,v) for k,v in agg.items()}).reset_index()
    result["CPA"] = result.apply(lambda r: round(r["비용"]/r["전환수"]) if r["전환수"]>0 else 0, axis=1)
    result["CTR"] = result.apply(lambda r: round(r["클릭"]/r["노출"]*100,2) if r["노출"]>0 else 0, axis=1)
    if has_purchase:
        result["구매ROAS"] = result.apply(lambda r: round(r["구매전환매출액"]/r["비용"]*100,1) if r["비용"]>0 else 0, axis=1)
    return result.sort_values("비용", ascending=False)

def col_fmt():
    d = {"비용":"₩{:,.0f}", "CPA":"₩{:,.0f}", "노출":"{:,}", "클릭":"{:,}", "전환수":"{:,}", "CTR":"{:.2f}%",
         "구매전환매출액":"₩{:,.0f}", "구매ROAS":"{:.1f}%"}
    for ec in extra_cols:
        d[ec] = "{:,.0f}"
    return d

# ── KPI ────────────────────────────────────────────────
total_cost = df["비용"].sum()
total_cnv  = df["전환수"].sum()
total_clk  = df["클릭"].sum()
total_imp  = df["노출"].sum()
avg_cpa    = round(total_cost / total_cnv) if total_cnv > 0 else 0
ctr        = round(total_clk / total_imp * 100, 2) if total_imp > 0 else 0
total_purchase_amt = df["구매전환매출액"].sum()
total_purchase_cnt = df["구매전환수"].sum()
purchase_roas      = round(total_purchase_amt / total_cost * 100, 1) if total_cost > 0 else 0

daily = df.groupby("날짜").agg(비용=("비용","sum"), 전환수=("전환수","sum"), 클릭=("클릭","sum")).reset_index()
daily["CPA"] = daily.apply(lambda r: round(r["비용"]/r["전환수"]) if r["전환수"]>0 else 0, axis=1)

# ── 이전 기간 대비 ─────────────────────────────────────
period_days = (end_date - start_date).days + 1
prev_end    = start_date - timedelta(days=1)
prev_start  = prev_end - timedelta(days=period_days - 1)

with st.spinner("이전 기간 데이터 불러오는 중..."):
    prev_rows = load_combined_rows(selected_name, prev_start.strftime("%Y-%m-%d"), prev_end.strftime("%Y-%m-%d"))

df_prev = pd.DataFrame(prev_rows)
if not df_prev.empty:
    df_prev["비용"] = df_prev["비용"].astype(float)
    for col in ("구매전환수", "구매전환매출액"):
        df_prev[col] = df_prev[col].fillna(0) if col in df_prev.columns else 0

prev_cost = df_prev["비용"].sum()   if not df_prev.empty else 0
prev_cnv  = df_prev["전환수"].sum() if not df_prev.empty else 0
prev_clk  = df_prev["클릭"].sum()   if not df_prev.empty else 0
prev_imp  = df_prev["노출"].sum()   if not df_prev.empty else 0
prev_cpa  = round(prev_cost / prev_cnv) if prev_cnv > 0 else 0
prev_ctr  = round(prev_clk / prev_imp * 100, 2) if prev_imp > 0 else 0
prev_purchase_amt = df_prev["구매전환매출액"].sum() if not df_prev.empty else 0
prev_roas         = round(prev_purchase_amt / prev_cost * 100, 1) if prev_cost > 0 else 0

def fmt_delta(cur, prev):
    if df_prev.empty or prev == 0:
        return None
    return f"{(cur - prev) / prev * 100:+.1f}%"

def find_issues(df_cur, df_prev, cpa_threshold=1.2, cost_spike=1.5):
    if df_prev.empty:
        return []
    cur_agg  = df_cur.groupby(["매체", "캠페인이름"]).agg(비용=("비용","sum"), 전환수=("전환수","sum")).reset_index()
    prev_agg = df_prev.groupby(["매체", "캠페인이름"]).agg(비용=("비용","sum"), 전환수=("전환수","sum")).reset_index()
    merged = cur_agg.merge(prev_agg, on=["매체", "캠페인이름"], how="outer",
                            suffixes=("", "_전기간")).fillna(0)

    issues = []
    for _, r in merged.iterrows():
        cur_cost, cur_cnv   = r["비용"], r["전환수"]
        prev_cost_, prev_cnv_ = r["비용_전기간"], r["전환수_전기간"]
        cur_cpa_  = cur_cost / cur_cnv if cur_cnv > 0 else None
        prev_cpa_ = prev_cost_ / prev_cnv_ if prev_cnv_ > 0 else None
        label = f"**{r['캠페인이름']}** ({r['매체']})"

        if cur_cpa_ and prev_cpa_ and cur_cpa_ >= prev_cpa_ * cpa_threshold:
            pct = (cur_cpa_ / prev_cpa_ - 1) * 100
            issues.append(f"🔴 {label} — CPA 상승: ₩{prev_cpa_:,.0f} → ₩{cur_cpa_:,.0f} ({pct:+.0f}%)")
        elif cur_cost > 0 and cur_cnv == 0 and prev_cnv_ > 0:
            issues.append(f"🔴 {label} — 전환 0건 (비용 ₩{cur_cost:,.0f} 지출, 이전 기간 전환 {prev_cnv_:.0f}건)")
        elif prev_cost_ > 0 and cur_cost >= prev_cost_ * cost_spike and cur_cnv <= prev_cnv_:
            issues.append(f"🟡 {label} — 비용 급증: ₩{prev_cost_:,.0f} → ₩{cur_cost:,.0f} (전환수는 정체/감소)")
    return issues

# ── 헤더 + 탭 ──────────────────────────────────────────
st.title(f"{selected_name} 광고 성과")
st.caption(f"{start_date} ~ {end_date}")

tab1, tab2, tab3 = st.tabs(["📈 전체 성과", "🎯 캠페인별", "🖼️ 소재별"])

# ── Tab1: 전체 성과 ────────────────────────────────────
with tab1:
    if not df_prev.empty:
        st.caption(f"이전 기간({prev_start} ~ {prev_end}) 대비")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("총 비용",    f"₩{total_cost:,.0f}", delta=fmt_delta(total_cost, prev_cost))
    c2.metric("총 전환수",  f"{total_cnv:,}건",     delta=fmt_delta(total_cnv, prev_cnv))
    c3.metric("전환당비용", f"₩{avg_cpa:,}",        delta=fmt_delta(avg_cpa, prev_cpa), delta_color="inverse")
    c4.metric("총 클릭",    f"{total_clk:,}",       delta=fmt_delta(total_clk, prev_clk))
    c5.metric("CTR",        f"{ctr}%",              delta=fmt_delta(ctr, prev_ctr))

    if adv.get("naver_customer_id"):
        st.divider()
        p1, p2 = st.columns(2)
        p1.metric("구매전환매출액", f"₩{total_purchase_amt:,.0f}", delta=fmt_delta(total_purchase_amt, prev_purchase_amt))
        p2.metric("구매 ROAS",      f"{purchase_roas}%",           delta=fmt_delta(purchase_roas, prev_roas))

    if extra_cols:
        st.divider()
        ecols = st.columns(len(extra_cols))
        for i, ec in enumerate(extra_cols):
            if ec in df.columns:
                ecols[i].metric(ec, f"{int(df[ec].sum()):,}건")

    st.divider()
    ch1, ch2 = st.columns(2)
    with ch1:
        fig = px.bar(daily, x="날짜", y="비용", title="일별 비용",
                     color_discrete_sequence=["#4C8BF5"])
        fig.update_layout(showlegend=False, height=300, margin=dict(t=40,b=0))
        fig.update_yaxes(tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)
    with ch2:
        fig2 = go.Figure()
        fig2.add_bar(x=daily["날짜"], y=daily["전환수"], name="전환수", marker_color="#34A853")
        fig2.add_scatter(x=daily["날짜"], y=daily["CPA"], name="CPA", yaxis="y2",
                         line=dict(color="#EA4335", width=2), mode="lines+markers")
        fig2.update_layout(
            title="일별 전환수 / CPA",
            yaxis=dict(title="전환수"),
            yaxis2=dict(title="CPA(₩)", overlaying="y", side="right", tickformat=",.0f"),
            height=300, margin=dict(t=40,b=0),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig2, use_container_width=True)

    issues = find_issues(df, df_prev)
    if issues:
        st.divider()
        st.markdown(f"#### ⚠️ 주요 이슈 ({prev_start} ~ {prev_end} 대비)")
        for msg in issues:
            st.warning(msg)

# ── Tab2: 캠페인별 ─────────────────────────────────────
with tab2:
    st.subheader("캠페인별 성과")
    camp = build_agg(df, ["매체", "캠페인이름"])
    st.dataframe(camp.style.format(col_fmt()), use_container_width=True, hide_index=True)

    fig3 = px.bar(camp.head(10), x="비용", y="캠페인이름", orientation="h", color="매체",
                  title="캠페인별 비용", color_discrete_sequence=["#4C8BF5", "#34A853"])
    fig3.update_layout(height=350, margin=dict(t=40,b=0))
    fig3.update_xaxes(tickformat=",.0f")
    st.plotly_chart(fig3, use_container_width=True)

# ── Tab3: 소재별 ───────────────────────────────────────
with tab3:
    st.subheader("소재별 성과")
    st.caption("메타(Facebook/Instagram) 광고만 소재 단위 데이터가 제공됩니다. 네이버는 광고그룹 단위까지만 조회됩니다.")

    df_meta = df[df["매체"] == "메타"]
    camps = ["전체"] + sorted(df_meta["캠페인이름"].unique().tolist())
    sel_camp = st.selectbox("캠페인 선택", camps)
    df_f = df_meta if sel_camp == "전체" else df_meta[df_meta["캠페인이름"] == sel_camp]

    creative = build_agg(df_f, ["캠페인이름", "광고그룹(세트)이름", "광고이름"])

    # 광고주 전환 중 이전 광고주의 소재가 잠깐 비치지 않도록, 썸네일이 준비될 때까지
    # 이 블록 전체를 하나의 placeholder에 원자적으로 교체한다.
    content = st.empty()
    with content.container():
        st.info("소재 이미지 불러오는 중...")

    thumbnails = fetch_thumbnails(adv["meta_ad_account_id"])

    # 이미지가 있는 소재만 카드형으로 표시
    has_thumb = [(row, thumbnails.get(row["광고이름"], "")) for _, row in creative.iterrows()]
    with_img  = [(r, t) for r, t in has_thumb if t]

    with content.container():
        if with_img:
            st.markdown("#### 소재 미리보기")
            COLS = 5
            for i in range(0, len(with_img), COLS):
                cols = st.columns(COLS)
                for j, (row, thumb) in enumerate(with_img[i:i+COLS]):
                    with cols[j]:
                        name = row["광고이름"]
                        st.markdown(
                            f'<img src="{thumb}" style="'
                            f'width:100%;aspect-ratio:1/1;object-fit:cover;'
                            f'border-radius:8px;display:block;">',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"{name[:22]}{'…' if len(name)>22 else ''}")
                        st.markdown(
                            f"<small>💰 ₩{row['비용']:,.0f}<br>"
                            f"🎯 {row['전환수']:,}건 · CPA ₩{row['CPA']:,}</small>",
                            unsafe_allow_html=True,
                        )
            st.divider()

        # 전체 성과 테이블
        st.markdown("#### 소재별 성과 테이블")
        st.dataframe(creative.style.format(col_fmt()), use_container_width=True, hide_index=True)

        top10 = creative.nlargest(10, "비용")
        fig4 = px.bar(top10, x="비용", y="광고이름", orientation="h",
                      title="소재별 비용 상위 10개", color_discrete_sequence=["#4C8BF5"],
                      hover_data=["캠페인이름", "전환수", "CPA"])
        fig4.update_layout(height=max(300, len(top10)*40), margin=dict(t=40,b=0))
        fig4.update_xaxes(tickformat=",.0f")
        st.plotly_chart(fig4, use_container_width=True)

# ── 원본 데이터 ────────────────────────────────────────
with st.expander("원본 데이터 보기"):
    st.dataframe(df.sort_values(["날짜","캠페인이름"]), use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("CSV 다운로드", csv, f"{selected_name}_{start_date}_{end_date}.csv", "text/csv")
