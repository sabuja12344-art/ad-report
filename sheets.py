import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMNS = [
    "날짜", "캠페인이름", "광고그룹(세트)이름",
    "광고이름", "노출", "클릭", "비용", "전환수", "전환당비용",
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

def append_rows(client, sheet_id, tab_name, rows):
    if not rows:
        return

    ws = client.open_by_key(sheet_id).worksheet(tab_name)

    # 1행에서 "메타" 헤더가 있는 열 찾기 (없으면 1열 = A열)
    first_row = ws.row_values(1)
    start_col = 1
    for i, v in enumerate(first_row):
        if "메타" in str(v):
            start_col = i + 1
            break

    # 해당 열의 마지막 데이터 행 찾기
    col_vals = ws.col_values(start_col)
    last_row = len(col_vals)  # gspread가 빈 행 자동 제거

    next_row = last_row + 1
    range_name = f"{_col_letter(start_col)}{next_row}"

    columns = _build_columns(rows)
    data = [[row.get(col, "") for col in columns] for row in rows]
    ws.update(range_name, data, value_input_option="USER_ENTERED")
