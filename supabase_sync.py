"""
Supabase 대시보드 동기화
매일 어제 데이터를 Supabase(ad_report_rows)에 upsert.
구글시트로 가는 main.py 파이프라인과는 완전히 독립적으로 동작한다.
"""

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import yaml

KST = ZoneInfo("Asia/Seoul")

from naver_api import get_report as naver_report
from meta_api import get_report as meta_report
from supabase_client import get_client, upsert_rows, to_supabase_rows

load_dotenv()


def main():
    default_naver_api_key    = os.environ["NAVER_API_KEY"]
    default_naver_secret_key = os.environ["NAVER_SECRET_KEY"]
    meta_token                = os.environ["META_ACCESS_TOKEN"]

    yesterday = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")

    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sb = get_client()

    print("=" * 55)
    print(f"  Supabase 대시보드 동기화  {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  대상 날짜: {yesterday}")
    print("=" * 55)

    for adv in config["advertisers"]:
        name = adv["name"]
        print(f"\n[{name}]")
        db_rows = []

        if adv.get("naver_customer_id"):
            print(f"  네이버 수집 중...")
            naver_api_key    = os.environ[adv["naver_api_key_env"]] if adv.get("naver_api_key_env") else default_naver_api_key
            naver_secret_key = os.environ[adv["naver_secret_key_env"]] if adv.get("naver_secret_key_env") else default_naver_secret_key
            rows = naver_report(
                naver_api_key,
                naver_secret_key,
                adv["naver_customer_id"],
                yesterday,
            )
            print(f"  → {len(rows)}행")
            db_rows.extend(to_supabase_rows(rows, name, "네이버"))

        if adv.get("meta_ad_account_id"):
            print(f"  메타 수집 중...")
            extra_events = adv.get("meta_extra_events")
            extra_names  = [e["name"] for e in (extra_events or [])]
            rows = meta_report(
                adv["meta_ad_account_id"],
                meta_token,
                yesterday,
                conversion_event=adv.get("meta_conversion_event", "purchase"),
                campaign_exclude=adv.get("meta_campaign_exclude"),
                extra_events=extra_events,
            )
            print(f"  → {len(rows)}행")
            db_rows.extend(to_supabase_rows(rows, name, "메타", extra_names))

        if db_rows:
            try:
                upsert_rows(sb, db_rows)
                print(f"  Supabase upsert 완료: 총 {len(db_rows)}행")
            except Exception as e:
                print(f"  [Supabase 오류] {e}")
        else:
            print(f"  수집된 데이터 없음")

    print("\n" + "=" * 55)
    print("  완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
