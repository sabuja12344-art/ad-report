"""
광고 보고서 자동 수집기
실행 시 어제 데이터를 각 광고주 구글 시트 (RAW) 탭에 자동 기입합니다.
"""

import os
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv

from naver_api import get_report as naver_report
from meta_api  import get_report as meta_report
from sheets    import get_client, append_rows

load_dotenv()


def main():
    # 인증 정보
    naver_api_key    = os.environ["NAVER_API_KEY"]
    naver_secret_key = os.environ["NAVER_SECRET_KEY"]
    meta_token       = os.environ["META_ACCESS_TOKEN"]
    google_json      = os.environ.get("GOOGLE_JSON_PATH", "google_credentials.json")

    # 어제 날짜
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 광고주 설정
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 구글 시트 클라이언트
    gc = get_client(google_json)

    print("=" * 55)
    print(f"  광고 보고서 수집  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  대상 날짜: {yesterday}")
    print("=" * 55)

    for adv in config["advertisers"]:
        name = adv["name"]
        print(f"\n[{name}]")
        all_rows = []

        # 네이버 검색광고
        if adv.get("naver_customer_id"):
            print(f"  네이버 수집 중...")
            rows = naver_report(
                naver_api_key,
                naver_secret_key,
                adv["naver_customer_id"],
                yesterday,
            )
            print(f"  → {len(rows)}행")
            all_rows.extend(rows)

        # 메타
        if adv.get("meta_ad_account_id"):
            print(f"  메타 수집 중...")
            extra_events = adv.get("meta_extra_events")
            rows = meta_report(
                adv["meta_ad_account_id"],
                meta_token,
                yesterday,
                adv.get("meta_conversion_event", "purchase"),
                adv.get("meta_campaign_exclude"),
                extra_events,
            )
            print(f"  → {len(rows)}행")
            all_rows.extend(rows)

        # 구글 시트 기입
        if all_rows:
            try:
                append_rows(gc, adv["sheet_id"], adv["raw_tab"], all_rows)
                print(f"  구글 시트 기입 완료: 총 {len(all_rows)}행")
            except Exception as e:
                print(f"  [시트 오류] {e}")
        else:
            print(f"  수집된 데이터 없음")

    print("\n" + "=" * 55)
    print("  완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
