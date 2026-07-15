import requests, os
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()

token = os.environ["META_ACCESS_TOKEN"]
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

r = requests.get(
    "https://graph.facebook.com/v19.0/act_1080197689976095/insights",
    params={
        "fields": "campaign_name,ad_name,spend,actions",
        "time_range": f'{{"since":"{yesterday}","until":"{yesterday}"}}',
        "level": "ad",
        "access_token": token,
        "limit": 500,
    }
)

registration_totals = {}
for item in r.json().get("data", []):
    for action in item.get("actions", []):
        at = action["action_type"]
        if "registration" in at or "complete" in at.lower():
            registration_totals[at] = registration_totals.get(at, 0) + int(float(action.get("value", 0)))

print(f"[{yesterday}] 등록완료 관련 action_type 합계:")
for k, v in sorted(registration_totals.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}건")
