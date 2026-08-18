import requests
import time
from urllib.parse import urlsplit, parse_qs

API_VERSION = "v19.0"
BASE_URL    = f"https://graph.facebook.com/{API_VERSION}"

def _fetch_ads_page(base_url, params, retries=2, backoff=0.7):
    for attempt in range(retries):
        try:
            r = requests.get(base_url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(backoff)

def get_ad_thumbnails(ad_account_id, access_token):
    base_url = f"{BASE_URL}/act_{ad_account_id}/ads"
    fields   = "name,creative{thumbnail_url,image_url}"
    after    = None
    thumbnails = {}

    while True:
        params = {"fields": fields, "access_token": access_token, "limit": 100}
        if after:
            params["after"] = after

        try:
            data = _fetch_ads_page(base_url, params)
        except Exception:
            # 이 배치의 소재 정보를 가져오다 계속 실패하면(일부 소재의 서버측 오류로
            # 추정), 최소 필드로 재시도해 커서만 얻어 다음 페이지로 계속 진행한다.
            try:
                data = _fetch_ads_page(base_url, {**params, "fields": "name"})
            except Exception as e:
                print(f"[썸네일 오류] {e}")
                break

        for ad in data.get("data", []):
            name     = ad.get("name", "")
            creative = ad.get("creative", {})
            thumb    = creative.get("image_url") or creative.get("thumbnail_url") or ""
            if name and thumb:
                thumbnails[name] = thumb

        next_url = data.get("paging", {}).get("next")
        if not next_url:
            break
        after = parse_qs(urlsplit(next_url).query).get("after", [None])[0]
        if not after:
            break

    return thumbnails

FIELDS = "campaign_name,adset_name,ad_name,impressions,clicks,spend,actions"

def get_report(ad_account_id, access_token, start_date, end_date=None, conversion_event="purchase", campaign_exclude=None, extra_events=None):
    if end_date is None:
        end_date = start_date

    url = f"{BASE_URL}/act_{ad_account_id}/insights"
    params = {
        "fields":       FIELDS,
        "time_range":   f'{{"since":"{start_date}","until":"{end_date}"}}',
        "time_increment": 1,
        "level":        "ad",
        "access_token": access_token,
        "limit":        500,
    }

    def _fetch_page(page_url, page_params, retries=3):
        for attempt in range(retries):
            try:
                r = requests.get(page_url, params=page_params, timeout=60)
                r.raise_for_status()
                data = r.json()
                if "error" in data:
                    code = data["error"].get("code")
                    msg  = data["error"].get("message", str(data["error"]))
                    # 17: rate limit — 재시도, 그 외는 즉시 중단
                    if code == 17 and attempt < retries - 1:
                        wait = 2 ** (attempt + 2)
                        print(f"    [메타 레이트 리밋] {wait}초 후 재시도...")
                        time.sleep(wait)
                        continue
                    raise RuntimeError(f"Meta API 오류: {msg}")
                return data
            except RuntimeError:
                raise
            except Exception as e:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    print(f"    [메타 페이지 재시도 {attempt+1}/{retries}] {wait}초 후 재시도... ({e})")
                    time.sleep(wait)
                else:
                    raise

    rows = []
    page_num = 0
    try:
        while url:
            page_num += 1
            data = _fetch_page(url, params)

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
                    "날짜":          item.get("date_start", start_date),
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

            next_url = data.get("paging", {}).get("next")
            url    = next_url
            params = {}

    except Exception as e:
        print(f"    [메타 오류] 페이지 {page_num}에서 중단: {e} (수집된 행: {len(rows)})")

    return rows
