import requests
import hashlib
import hmac
import base64
import time
import json

BASE_URL = "https://api.searchad.naver.com"

def _signature(timestamp, method, path, secret_key):
    message = f"{timestamp}.{method}.{path}".encode("utf-8")
    sig     = hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).digest()
    return base64.b64encode(sig).decode()

def _headers(method, path, api_key, secret_key, customer_id):
    ts = str(int(time.time() * 1000))
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp":  ts,
        "X-API-KEY":    api_key,
        "X-Customer":   str(customer_id),
        "X-Signature":  _signature(ts, method, path, secret_key),
    }

def _get(path, api_key, secret_key, customer_id, params=None):
    r = requests.get(
        BASE_URL + path,
        headers=_headers("GET", path, api_key, secret_key, customer_id),
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def _get_stats(api_key, secret_key, customer_id, ids, date):
    path = "/stats"
    r = requests.get(
        BASE_URL + path,
        headers=_headers("GET", path, api_key, secret_key, customer_id),
        params={
            "ids":           ",".join(ids),
            "fields":        json.dumps(["impCnt", "clkCnt", "salesAmt", "ccnt"]),
            "timeRange":     json.dumps({"since": date, "until": date}),
            "timeIncrement": "day",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("data", [])

def get_report(api_key, secret_key, customer_id, date):
    try:
        # 1. 캠페인 목록
        campaigns = _get("/ncc/campaigns", api_key, secret_key, customer_id)
        campaign_map = {c["nccCampaignId"]: c.get("name", "") for c in campaigns}
        if not campaign_map:
            return []

        # 2. 광고그룹 목록 (campaignIds[] 필터는 서버에서 무시되므로 전체 조회)
        adgroups = _get("/ncc/adgroups", api_key, secret_key, customer_id)
        adgroup_map = {
            ag["nccAdgroupId"]: {
                "name":        ag.get("name", ""),
                "campaign_id": ag.get("nccCampaignId", ""),
            }
            for ag in adgroups
        }

        if not adgroup_map:
            return []

        # 3. 광고그룹 단위 통계
        stats = _get_stats(api_key, secret_key, customer_id, list(adgroup_map), date)

        rows = []
        for stat in stats:
            ag_id = stat.get("id", "")
            if ag_id not in adgroup_map:
                continue

            ag   = adgroup_map[ag_id]
            cost = float(stat.get("salesAmt", 0))
            cnv  = int(stat.get("ccnt", 0))
            cpa  = round(cost / cnv) if cnv > 0 else 0

            rows.append({
                "날짜":              date,
                "캠페인이름":        campaign_map.get(ag["campaign_id"], ""),
                "광고그룹(세트)이름": ag["name"],
                "광고이름":          "",
                "노출":              int(stat.get("impCnt", 0)),
                "클릭":              int(stat.get("clkCnt", 0)),
                "비용":              cost,
                "전환수":            cnv,
                "전환당비용":        cpa,
            })

        return rows

    except Exception as e:
        print(f"    [네이버 오류] {e}")
        return []
