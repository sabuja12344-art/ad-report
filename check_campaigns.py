import requests, hashlib, hmac, base64, time, os
from dotenv import load_dotenv
load_dotenv()

api_key    = os.environ["NAVER_API_KEY"]
secret_key = os.environ["NAVER_SECRET_KEY"]

def get_headers(method, path, customer_id="1924452"):
    ts  = str(int(time.time() * 1000))
    msg = f"{ts}.{method}.{path}".encode("utf-8")
    sig = base64.b64encode(hmac.new(secret_key.encode("utf-8"), msg, hashlib.sha256).digest()).decode()
    return {"Content-Type":"application/json; charset=UTF-8","X-Timestamp":ts,"X-API-KEY":api_key,"X-Customer":customer_id,"X-Signature":sig}

r = requests.get("https://api.searchad.naver.com/ncc/campaigns", headers=get_headers("GET","/ncc/campaigns"), timeout=30)
campaigns = r.json()
print(f"에이전시(1924452) 캠페인 {len(campaigns)}개:")
for c in campaigns:
    print(f"  {c.get('name','?')} | ID={c['nccCampaignId']} | status={c.get('status','?')}")
