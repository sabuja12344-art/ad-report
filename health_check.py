"""
주간 헬스체크 — Meta 토큰 유효성 + Supabase 연결 확인
GitHub Actions health_check.yml 에서 실행
"""
import os
import sys
import requests

errors = []

# ── 1. Meta 토큰 확인 ──────────────────────────────────
try:
    token = os.environ["META_ACCESS_TOKEN"]
    r = requests.get(
        "https://graph.facebook.com/v22.0/me",
        params={"access_token": token, "fields": "id,name"},
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        code = data["error"].get("code")
        msg  = data["error"].get("message", str(data["error"]))
        raise RuntimeError(f"code={code}: {msg}")
    print(f"✅ Meta 토큰 유효 (id={data.get('id')}, name={data.get('name')})")
except Exception as e:
    print(f"❌ Meta 토큰 오류: {e}")
    errors.append("Meta 토큰")

# ── 2. Supabase 연결 확인 ──────────────────────────────
try:
    from supabase import create_client
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    res = sb.table("ad_report_rows").select("date").limit(1).execute()
    print(f"✅ Supabase 연결 정상")
except Exception as e:
    print(f"❌ Supabase 오류: {e}")
    errors.append("Supabase")

# ── 결과 ───────────────────────────────────────────────
if errors:
    print(f"\n🚨 헬스체크 실패: {', '.join(errors)}")
    sys.exit(1)

print("\n✅ 모든 시스템 정상")
