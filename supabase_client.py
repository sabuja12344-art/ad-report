import os
from supabase import create_client

TABLE = "ad_report_rows"
ON_CONFLICT = "advertiser,channel,date,campaign_name,adgroup_name,ad_name"


def get_client():
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    except Exception:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise KeyError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다.")

    return create_client(url, key)


def to_supabase_rows(rows, advertiser, channel, extra_event_names=None):
    extra_event_names = extra_event_names or []
    out = []
    for r in rows:
        out.append({
            "advertiser":     advertiser,
            "channel":        channel,
            "date":           r["날짜"],
            "campaign_name":  r.get("캠페인이름", ""),
            "adgroup_name":   r.get("광고그룹(세트)이름", ""),
            "ad_name":        r.get("광고이름", ""),
            "impressions":    r.get("노출", 0),
            "clicks":         r.get("클릭", 0),
            "cost":           r.get("비용", 0),
            "conversions":    r.get("전환수", 0),
            "extra_events":   {k: r[k] for k in extra_event_names if k in r},
        })
    return out


def upsert_rows(client, rows):
    if not rows:
        return
    client.table(TABLE).upsert(rows, on_conflict=ON_CONFLICT).execute()


def fetch_rows(client, advertiser, start_date, end_date):
    res = (
        client.table(TABLE)
        .select("*")
        .eq("advertiser", advertiser)
        .gte("date", start_date)
        .lte("date", end_date)
        .execute()
    )
    rows = []
    for r in res.data:
        row = {
            "날짜":                r["date"],
            "캠페인이름":          r["campaign_name"],
            "광고그룹(세트)이름":  r["adgroup_name"],
            "광고이름":            r["ad_name"],
            "노출":                r["impressions"],
            "클릭":                r["clicks"],
            "비용":                r["cost"],
            "전환수":              r["conversions"],
            "매체":                r["channel"],
        }
        row.update(r.get("extra_events") or {})
        rows.append(row)
    return rows
