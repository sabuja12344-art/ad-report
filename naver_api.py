import requests
import hashlib
import hmac
import base64
import time

BASE_URL = "https://api.searchad.naver.com"

def _signature(timestamp, method, path, secret_key):
    message = f"{timestamp}.{method}.{path}".encode("utf-8")
    sig     = hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).digest()
    return base64.b64encode(sig).decode()

def _headers(method, path, api_key, secret_key, customer_id):
    ts = str(int(time.time() * 1000))
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": ts,
        "X-API-KEY":   api_key,
        "X-Customer":  str(customer_id),
        "X-Signature": _signature(ts, method, path, secret_key),
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

def _get_all_campaigns(api_key, secret_key, customer_id):
    data = _get("/ncc/campaigns", api_key, secret_key, customer_id)
    return {c["nccCampaignId"]: c.get("campaignName", "") for c in data}

def _get_all_adgroups(api_key, secret_key, customer_id, campaign_ids):
    params = [("campaignIds[]", cid) for cid in campaign_ids]
    data = _get("/ncc/adgroups", api_key, secret_key, customer_id, params)
    return {
        ag["nccAdgroupId"]: {
            "name":        ag.get("adgroupName", ""),
            "campaign_id": ag.get("nccCampaignId", ""),
        }
        for ag in data
    }

def _get_all_ads(api_key, secret_key, customer_id, adgroup_ids):
    params = [("adgroupIds[]", agid) for agid in adgroup_ids]
    data = _get("/ncc/ads", api_key, secret_key, customer_id, params)
    return {
        ad["nccAdId"]: {
            "name":       ad.get("adName", ""),
            "adgroup_id": ad.get("nccAdgroupId", ""),
        }
        for ad in data
    }

def _get_stats(api_key, secret_key, customer_id, ids, date):
    r = requests.get(
        BASE_URL + "/ncc/stats",
        headers=_headers(api_key, secret_key, customer_id),
        params={
            "ids":               ",".join(ids),
            "fields":            "impCnt,clkCnt,salesAmt,cnvCnt",
            "timeRange.since":   date,
            "timeRange.until":   date,
            "timeIncrement":     1,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

def get_report(api_key, secret_key, customer_id, date):
    try:
        campaign_map = _get_all_campaigns(api_key, secret_key, customer_id)
        if not campaign_map:
            return []

        adgroup_map = _get_all_adgroups(api_key, secret_key, customer_id, list(campaign_map))
        if not adgroup_map:
            return []

        ad_map = _get_all_ads(api_key, secret_key, customer_id, list(adgroup_map))
        if not ad_map:
            return []

        stats = _get_stats(api_key, secret_key, customer_id, list(ad_map), date)

        rows = []
        for stat in stats:
            ad_id = stat.get("id", "")
            if ad_id not in ad_map:
                continue

            ad  = ad_map[ad_id]
            ag  = adgroup_map.get(ad["adgroup_id"], {})
            imp  = stat.get("data", {}).get("impCnt", 0)
            clk  = stat.get("data", {}).get("clkCnt", 0)
            cost = stat.get("data", {}).get("salesAmt", 0)
            cnv  = stat.get("data", {}).get("cnvCnt", 0)
            cpa  = round(cost / cnv) if cnv > 0 else 0

            rows.append({
                "날짜":          date,
                "매체":          "네이버SA",
                "캠페인이름":    campaign_map.get(ag.get("campaign_id", ""), ""),
                "광고그룹(세트)이름": ag.get("name", ""),
                "광고이름":      ad["name"],
                "노출":          imp,
                "클릭":          clk,
                "비용":          cost,
                "전환수":        cnv,
                "전환당비용":    cpa,
            })

        return rows

    except Exception as e:
        print(f"    [네이버 오류] {e}")
        return []
