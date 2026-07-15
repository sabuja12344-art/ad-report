import os, requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
token = os.environ["META_ACCESS_TOKEN"]

perms = requests.get(f"https://graph.facebook.com/v19.0/me/permissions?access_token={token}").json()
granted = [p["permission"] for p in perms.get("data", []) if p["status"] == "granted"]
print("보유 권한:", granted)

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

for name, account_id in [("샐러디", "1080197689976095"), ("맘시터", "10204539929520373")]:
    r = requests.get(
        f"https://graph.facebook.com/v19.0/act_{account_id}/insights",
        params={
            "fields": "campaign_name,impressions,clicks,spend",
            "time_range": f'{{"since":"{yesterday}","until":"{yesterday}"}}',
            "level": "campaign",
            "access_token": token,
            "limit": 3,
        }
    )
    print(f"{name} ({yesterday}): status={r.status_code}")
    data = r.json()
    if "error" in data:
        print("  오류:", data["error"]["message"])
    else:
        items = data.get("data", [])
        print(f"  캠페인 {len(items)}개")
        for item in items:
            print(f"  - {item.get('campaign_name','?')} | 노출:{item.get('impressions',0)} 클릭:{item.get('clicks',0)} 비용:{item.get('spend',0)}")
