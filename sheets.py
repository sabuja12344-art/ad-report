import time
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _col_letter(n):
    result = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result

def get_client(json_key_path):
    creds = Credentials.from_service_account_file(json_key_path, scopes=SCOPES)
    return gspread.authorize(creds)

def _build_columns(rows):
    base = ["날짜", "캠페인이름", "광고그룹(세트)이름", "광고이름", "노출", "클릭", "비용", "전환수", "전환당비용"]
    extra = [k for k in (rows[0].keys() if rows else []) if k not in base]
    return base + extra

def _with_retry(fn, retries=4):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f"    [구글 시트 재시도 {attempt+1}/{retries}] {wait}초 후 재시도...")
                time.sleep(wait)
            else:
                raise

def append_rows(client, sheet_id, tab_name, rows, section_keyword="메타", columns=None):
    if not rows:
        return

    ws = _with_retry(lambda: client.open_by_key(sheet_id).worksheet(tab_name))

    first_row = _with_retry(lambda: ws.row_values(1))
    start_col = 1
    for i, v in enumerate(first_row):
        if section_keyword in str(v):
            start_col = i + 1
            break

    col_vals = _with_retry(lambda: ws.col_values(start_col))
    last_row  = len(col_vals)
    next_row  = last_row + 1
    range_name = f"{_col_letter(start_col)}{next_row}"

    columns = columns or _build_columns(rows)
    data    = [[row.get(col, "") for col in columns] for row in rows]
    _with_retry(lambda: ws.update(range_name, data, value_input_option="USER_ENTERED"))
