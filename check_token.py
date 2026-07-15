import os, requests, smtplib
from datetime import datetime
from email.mime.text import MIMEText

def main():
    token        = os.environ["META_ACCESS_TOKEN"]
    app_id       = os.environ["META_APP_ID"]
    app_secret   = os.environ["META_APP_SECRET"]
    gmail_user   = os.environ["GMAIL_USER"]
    gmail_pw     = os.environ["GMAIL_APP_PASSWORD"]

    r = requests.get(
        "https://graph.facebook.com/debug_token",
        params={
            "input_token":  token,
            "access_token": f"{app_id}|{app_secret}",
        },
        timeout=15,
    )
    data = r.json().get("data", {})
    expires_at = data.get("expires_at", 0)

    if expires_at == 0:
        print("만료일 없음 (영구 토큰 또는 오류)")
        return

    expires_dt = datetime.fromtimestamp(expires_at)
    days_left  = (expires_dt - datetime.now()).days
    print(f"토큰 만료일: {expires_dt.strftime('%Y-%m-%d')}  ({days_left}일 남음)")

    if days_left <= 30:
        body = f"""안녕하세요.

광고 보고서 자동화에 사용 중인 메타 액세스 토큰이 곧 만료됩니다.

- 만료일: {expires_dt.strftime('%Y-%m-%d')}
- 남은 기간: {days_left}일

[갱신 방법]
1. 로컬에서 get_token.py 실행 → 새 토큰 발급
2. GitHub → Settings → Secrets → META_ACCESS_TOKEN 수정

ad-report 자동화 시스템
"""
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"[광고 보고서] 메타 토큰 만료 {days_left}일 전 - 갱신 필요"
        msg["From"]    = gmail_user
        msg["To"]      = gmail_user

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_pw)
            smtp.send_message(msg)

        print("만료 알림 이메일 발송 완료")

if __name__ == "__main__":
    main()
