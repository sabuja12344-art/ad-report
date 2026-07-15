import sys
import requests

APP_ID     = "1024903666916145"
APP_SECRET = "949e0075b8e4a7c40414780deb631d75"
REDIRECT   = "https://localhost/"

if len(sys.argv) < 2:
    print("사용법: python get_token.py <코드값>")
    sys.exit(1)
code = sys.argv[1].strip()

# 1단계: code -> short-lived token
r1 = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
    "client_id":     APP_ID,
    "redirect_uri":  REDIRECT,
    "client_secret": APP_SECRET,
    "code":          code,
})
d1 = r1.json()
if "error" in d1:
    print("단계1 실패:", d1["error"]["message"])
    sys.exit(1)

short_token = d1["access_token"]
print(f"단기토큰 OK (길이={len(short_token)})")

# 2단계: short-lived -> long-lived (60일)
r2 = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
    "grant_type":      "fb_exchange_token",
    "client_id":       APP_ID,
    "client_secret":   APP_SECRET,
    "fb_exchange_token": short_token,
})
d2 = r2.json()
if "error" in d2:
    print("단계2 실패:", d2["error"]["message"])
    sys.exit(1)

long_token = d2["access_token"]
expires    = d2.get("expires_in", 0)
print(f"장기토큰 OK! 만료={int(expires)//86400}일 (길이={len(long_token)})")

# 3단계: .env 업데이트
env_path = ".env"
with open(env_path, encoding="utf-8") as f:
    lines = f.readlines()

with open(env_path, "w", encoding="utf-8") as f:
    for line in lines:
        if line.startswith("META_ACCESS_TOKEN="):
            f.write(f"META_ACCESS_TOKEN={long_token}\n")
        elif line.startswith("META_APP_ID="):
            f.write(f"META_APP_ID={APP_ID}\n")
        elif line.startswith("META_APP_SECRET="):
            f.write(f"META_APP_SECRET={APP_SECRET}\n")
        else:
            f.write(line)

print(".env 업데이트 완료!")
print(f"\nTOKEN (전체):\n{long_token}")
