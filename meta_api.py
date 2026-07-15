import requests

API_VERSION = "v19.0"
BASE_URL    = f"https://graph.facebook.com/{API_VERSION}"

FIELDS = "campaign_name,adset_name,ad_name,impressions,clicks,spend,actions"

def get_report(ad_account_id, access_token, date, conversion_event="purchase", campaign_exclude=None, extra_events=None):
    url = f"{BASE_URL}/act_{ad_account_id}/insights"
    params = {
        "fields":      FIELDS,
        "time_range":  f'{{"since":"{date}","until":"{date}"}}',
        "level":       "ad",
        "access_token": access_token,
        "limit":       500,
    }

    rows = []
    try:
        while url:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()

            if "error" in data:
                print(f"    [메타 API 오류] {data['error'].get('message', data)}")
                break

            for item in data.get("data", []):
                campaign_name = item.get("campaign_name", "")
                if campaign_exclude and any(ex in campaign_name for ex in campaign_exclude):
                    continue
                cnv = 0
                extra_cnv = {e["name"]: 0 for e in (extra_events or [])}
                for action in item.get("actions", []):
                    at = action.get("action_type", "")
                    v  = int(float(action.get("value", 0)))
                    if at == conversion_event:
                        cnv += v
                    for e in (extra_events or []):
                        if at == e["event"]:
                            extra_cnv[e["name"]] += v

                cost = float(item.get("spend", 0))
                cpa  = round(cost / cnv) if cnv > 0 else 0

                row = {
                    "날짜":          date,
                    "캠페인이름":    item.get("campaign_name", ""),
                    "광고그룹(세트)이름": item.get("adset_name", ""),
                    "광고이름":      item.get("ad_name", ""),
                    "노출":          int(item.get("impressions", 0)),
                    "클릭":          int(item.get("clicks", 0)),
                    "비용":          cost,
                    "전환수":        cnv,
                    "전환당비용":    cpa,
                }
                row.update(extra_cnv)
                rows.append(row)

            # 다음 페이지
            next_url = data.get("paging", {}).get("next")
            url    = next_url
            params = {}

    except Exception as e:
        print(f"    [메타 오류] {e}")

    return rows
