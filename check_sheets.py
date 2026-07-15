import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
load_dotenv()

creds = Credentials.from_service_account_file(
    os.environ.get("GOOGLE_JSON_PATH", "google_credentials.json"),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(creds)

sheet_id = "1hS3OwMWh_cPXWwO4chs1SOn_j7EflgeHUE0idRu9Yp4"
ws = gc.open_by_key(sheet_id).worksheet("(RAW)")
rows = ws.get_all_values()

print(f"총 {len(rows)}행, {len(rows[0]) if rows else 0}열")

# 1행 (헤더 확인)
print("\n=== 1행 (헤더) ===")
for i, v in enumerate(rows[0]):
    if v.strip():
        print(f"  열{i+1}({chr(65+i) if i<26 else chr(64+i//26)+chr(65+i%26)}): {v}")

# 마지막 3행
print(f"\n=== 마지막 3행 (행{len(rows)-2}~{len(rows)}) ===")
for row in rows[-3:]:
    non_empty = [(i+1, v) for i, v in enumerate(row) if v.strip()]
    print(f"  데이터 있는 열: {non_empty[:15]}")
