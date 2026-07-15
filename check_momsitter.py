import gspread, requests, os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()

# 1. 맘시터 시트 구조 확인
creds = Credentials.from_service_account_file(
    os.environ.get("GOOGLE_JSON_PATH", "google_credentials.json"),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(creds)
ws = gc.open_by_key("1hzYm9cYQUJFb2l1BpCp3kZN2SC5mYfIwxlKx-XzmvB8").worksheet("(RAW)")
first_row = ws.row_values(1)

print("=== 맘시터 (RAW) 1행 헤더 ===")
for i, v in enumerate(first_row):
    if v.strip():
        col = ""
        n = i + 1
        while n > 0:
            n, r = divmod(n - 1, 26)
            col = chr(65 + r) + col
        print(f"  {col}열({i+1}): {v}")

# 2. 맘시터 Meta 전환 이벤트 확인
token = os.environ["META_ACCESS_TOKEN"]
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

r = requests.get(
    "https://graph.facebook.com/v19.0/act_10204539929520373/insights",
    params={
        "fields": "campaign_name,actions",
        "time_range": f'{{"since":"{yesterday}","until":"{yesterday}"}}',
        "level": "ad",
        "access_token": token,
        "limit": 500,
    }
)

print(f"\n=== 맘시터 Meta 캠페인 목록 ({yesterday}) ===")
campaigns = set()
all_actions = {}
for item in r.json().get("data", []):
    campaigns.add(item.get("campaign_name", "?"))
    for action in item.get("actions", []):
        at = action["action_type"]
        all_actions[at] = all_actions.get(at, 0) + int(float(action.get("value", 0)))

for c in sorted(campaigns):
    print(f"  {c}")

print("\n=== 전환 관련 action_type ===")
keywords = ["complete", "register", "lead", "purchase", "submit", "conversion", "subscribe"]
for at, v in sorted(all_actions.items(), key=lambda x: -x[1]):
    if any(k in at for k in keywords):
        print(f"  {at}: {v}건")
