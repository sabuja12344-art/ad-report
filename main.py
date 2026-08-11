"""
광고 보고서 자동 수집기
실행 시 어제 데이터를 각 광고주 구글 시트 (RAW) 탭에 자동 기입합니다.
"""

import os
import yaml
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")

from naver_api import get_report as naver_report
from meta_api  import get_report as meta_report
from sheets    import get_client, append_rows

load_dotenv()

# 네이버SA 섹션은 시트에 광고그룹/광고이름 열이 없고 날짜·캠페인·노출·클릭·비용·전환·DB단가 7열만 존재함
NAVER_SHEET_COLUMNS = ["날짜", "캠페인이름", "노출", "클릭", "비용", "전환수", "전환당비용"]


def main():
    # 인증 정보
    default_naver_api_key    = os.environ["NAVER_API_KEY"]
    default_naver_secret_key = os.environ["NAVER_SECRET_KEY"]
    meta_token                = os.environ["META_ACCESS_TOKEN"]
    google_json      = os.environ.get("GOOGLE_JSON_PATH", "google_credentials.json")

    # 어제 날짜 (KST 기준 - GitHub Actions 서버는 UTC라서 명시적으로 지정해야 함)
    yesterday = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")

    # 광고주 설정
    with open("config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 구글 시트 클라이언트
    gc = get_client(google_json)

    print("=" * 55)
    print(f"  광고 보고서 수집  {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  대상 날짜: {yesterday}")
    print("=" * 55)

    for adv in config["advertisers"]:
        name = adv["name"]
        print(f"\n[{name}]")
        naver_rows = []
        meta_rows  = []

        # 네이버 검색광고
        if adv.get("naver_customer_id"):
            print(f"  네이버 수집 중...")
            naver_api_key    = os.environ[adv["naver_api_key_env"]] if adv.get("naver_api_key_env") else default_naver_api_key
            naver_secret_key = os.environ[adv["naver_secret_key_env"]] if adv.get("naver_secret_key_env") else default_naver_secret_key
            naver_rows = naver_report(
                naver_api_key,
                naver_secret_key,
                adv["naver_customer_id"],
                yesterday,
            )
            print(f"  → {len(naver_rows)}행")

        # 메타
        if adv.get("meta_ad_account_id"):
            print(f"  메타 수집 중...")
            extra_events = adv.get("meta_extra_events")
            meta_rows = meta_report(
                adv["meta_ad_account_id"],
                meta_token,
                yesterday,
                conversion_event=adv.get("meta_conversion_event", "purchase"),
                campaign_exclude=adv.get("meta_campaign_exclude"),
                extra_events=extra_events,
            )
            print(f"  → {len(meta_rows)}행")

        # 구글 시트 기입 (네이버/메타 섹션에 각각 기입)
        if naver_rows:
            try:
                append_rows(gc, adv["sheet_id"], adv["raw_tab"], naver_rows, section_keyword="네이버", columns=NAVER_SHEET_COLUMNS)
                print(f"  구글 시트 기입 완료(네이버): {len(naver_rows)}행")
            except Exception as e:
                print(f"  [시트 오류-네이버] {e}")

        if meta_rows:
            try:
                append_rows(gc, adv["sheet_id"], adv["raw_tab"], meta_rows, section_keyword="메타")
                print(f"  구글 시트 기입 완료(메타): {len(meta_rows)}행")
            except Exception as e:
                print(f"  [시트 오류-메타] {e}")

        if not naver_rows and not meta_rows:
            print(f"  수집된 데이터 없음")

    print("\n" + "=" * 55)
    print("  완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
