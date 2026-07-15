"""잘못 들어간 2026-07-14 데이터 삭제 후 다시 삽입"""
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

for name, sheet_id in [
    ("샐러디", "1hS3OwMWh_cPXWwO4chs1SOn_j7EflgeHUE0idRu9Yp4"),
    ("맘시터", "1hzYm9cYQUJFb2l1BpCp3kZN2SC5mYfIwxlKx-XzmvB8"),
]:
    ws = gc.open_by_key(sheet_id).worksheet("(RAW)")
    first_row = ws.row_values(1)

    start_col = 1
    for i, v in enumerate(first_row):
        if "메타" in str(v):
            start_col = i + 1
            break

    col_vals = ws.col_values(start_col)
    print(f"\n{name}: 메타 시작열={start_col}, 현재 마지막행={len(col_vals)}")

    # 2026-07-14 데이터 행 번호 찾아서 삭제
    rows_to_delete = []
    for i, v in enumerate(col_vals):
        if v == "2026-07-14":
            rows_to_delete.append(i + 1)

    print(f"  삭제할 행(2026-07-14): {rows_to_delete}")
    for row_num in reversed(rows_to_delete):
        ws.delete_rows(row_num)
        print(f"  행 {row_num} 삭제 완료")

print("\n정리 완료!")
