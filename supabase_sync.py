"""
Supabase 대시보드 동기화
최근 3일(어제·그제·그그제)을 upsert — 하루 실패해도 다음 실행에서 자동 복구.
구글시트로 가는 main.py 파이프라인과 완전히 독립적으로 동작한다.
"""

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import yaml

KST = ZoneInfo("Asia/Seoul")

from naver_api import get_report as naver_report
from meta_api import get_report as meta_report
from supabase_client import get_client, upsert_rows, to_supabase_rows

load_dotenv()

SYNC_DAYS = 3  # 실패 복구를 위해 최근 N일을 항상 재동기화


def main():
    default_naver_api_key    = os.environ["NAVER_API_KEY"]
    default_naver_secret_key = os.environ["NAVER_SECRET_KEY"]
    meta_token                = os.environ["META_ACCESS_TOKEN"]

    today = datetime.now(KST).date()
    end_date   = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (today - timedelta(days=SYNC_DAYS)).strftime("%Y-%m-%d")

    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sb = get_client()

    print("=" * 55)
    print(f"  Supabase 대시보드 동기화  {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  대상 기간: {start_date} ~ {end_date} ({SYNC_DAYS}일)")
    print("=" * 55)

    has_error = False

    for adv in config["advertisers"]:
        name = adv["name"]
        print(f"\n[{name}]")
        db_rows = []

        try:
            if adv.get("naver_customer_id"):
                print(f"  네이버 수집 중 ({start_date} ~ {end_date})...")
                naver_api_key    = os.environ[adv["naver_api_key_env"]] if adv.get("naver_api_key_env") else default_naver_api_key
                naver_secret_key = os.environ[adv["naver_secret_key_env"]] if adv.get("naver_secret_key_env") else default_naver_secret_key
                rows = naver_report(
                    naver_api_key,
                    naver_secret_key,
                    adv["naver_customer_id"],
                    start_date,
                    end_date,
                )
                print(f"  → {len(rows)}행")
                db_rows.extend(to_supabase_rows(rows, name, "네이버"))

            if adv.get("meta_ad_account_id"):
                print(f"  메타 수집 중 ({start_date} ~ {end_date})...")
                rows = meta_report(
                    adv["meta_ad_account_id"],
                    meta_token,
                    start_date,
                    end_date,
                    conversion_event=adv.get("meta_conversion_event", "purchase"),
                    campaign_exclude=adv.get("meta_campaign_exclude"),
                    extra_events=adv.get("meta_extra_events"),
                )
                print(f"  → {len(rows)}행")
                db_rows.extend(to_supabase_rows(rows, name, "메타"))

            if db_rows:
                upsert_rows(sb, db_rows)
                print(f"  Supabase upsert 완료: 총 {len(db_rows)}행")
            else:
                print(f"  수집된 데이터 없음")

        except Exception as e:
            print(f"  [오류] {name} 동기화 실패 (다른 광고주는 계속 진행): {e}")
            has_error = True

    print("\n" + "=" * 55)
    print("  완료!")
    print("=" * 55)

    if has_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
