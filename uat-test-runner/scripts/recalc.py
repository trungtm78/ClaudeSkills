#!/usr/bin/env python3
"""
recalc.py — Cập nhật sheet 'UAT Result' (Summary) trong file Excel UAT.
Đọc Test Cases sheet, tính metrics 2 layer (API + E2E), ghi vào sheet mới.

Usage:
    python recalc.py <uat_file.xlsx>
"""
import sys
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else ''

STATUS_PASS = 'Đạt'
STATUS_FAIL = 'Không đạt'
STATUS_SKIP = 'Bỏ qua'

# FALLBACK — khớp generate_uat_excel.py hiện tại (bản cũ 17/18 bị lệch 1 cột).
# resolve_columns() đọc header row 3 làm nguồn chân lý.
COL_TC_ID     = 1
COL_PRIORITY  = 3
COL_MODULE    = 4
COL_STATUS_API = 18   # R — Trạng thái API
COL_STATUS_E2E = 19   # S — Trạng thái E2E

HEADER_ROW = 3
_HEADER_TO_CONST = {
    'tc-id': 'COL_TC_ID',
    'độ ưu tiên': 'COL_PRIORITY',
    'module': 'COL_MODULE',
    'trạng thái api': 'COL_STATUS_API',
    'trạng thái e2e': 'COL_STATUS_E2E',
}


def resolve_columns(ws_tc):
    """Override COL_* theo header thật ở row 3 — chống lệch cột giữa version."""
    for col in range(1, ws_tc.max_column + 1):
        val = ws_tc.cell(row=HEADER_ROW, column=col).value
        if not val:
            continue
        const = _HEADER_TO_CONST.get(str(val).strip().lower())
        if const:
            globals()[const] = col


def main():
    if not EXCEL_PATH:
        print('Usage: python recalc.py <file.xlsx>', file=sys.stderr)
        sys.exit(1)

    path = Path(EXCEL_PATH)
    if not path.exists():
        print(f'❌ File không tồn tại: {path}', file=sys.stderr)
        sys.exit(1)

    try:
        wb = load_workbook(path)
    except PermissionError:
        print('❌ File đang mở trong Excel. Đóng rồi thử lại.', file=sys.stderr)
        sys.exit(3)

    if 'Test Cases' not in wb.sheetnames:
        print('❌ Sheet "Test Cases" không tồn tại.', file=sys.stderr)
        sys.exit(2)

    ws_tc = wb['Test Cases']
    resolve_columns(ws_tc)

    total = 0
    api_pass = api_fail = api_skip = 0
    e2e_pass = e2e_fail = e2e_skip = 0
    both_pass = 0
    p0_fail = p1_fail = 0
    modules_seen = set()

    for row in range(4, ws_tc.max_row + 1):
        tc_id = ws_tc.cell(row=row, column=COL_TC_ID).value
        if not tc_id:
            continue
        total += 1

        priority   = str(ws_tc.cell(row=row, column=COL_PRIORITY).value or '').strip()
        module     = str(ws_tc.cell(row=row, column=COL_MODULE).value or '').strip()
        api_status = str(ws_tc.cell(row=row, column=COL_STATUS_API).value or '').strip()
        e2e_status = str(ws_tc.cell(row=row, column=COL_STATUS_E2E).value or '').strip()

        if module:
            modules_seen.add(module)

        if api_status == STATUS_PASS:
            api_pass += 1
        elif api_status == STATUS_FAIL:
            api_fail += 1
        elif api_status == STATUS_SKIP:
            api_skip += 1

        if e2e_status == STATUS_PASS:
            e2e_pass += 1
        elif e2e_status == STATUS_FAIL:
            e2e_fail += 1
        elif e2e_status == STATUS_SKIP:
            e2e_skip += 1

        if api_status == STATUS_PASS and e2e_status == STATUS_PASS:
            both_pass += 1

        if e2e_status == STATUS_FAIL or api_status == STATUS_FAIL:
            if priority in ('P0', 'Critical', 'Blocker'):
                p0_fail += 1
            elif priority in ('P1', 'High'):
                p1_fail += 1

    api_rate  = round(api_pass  / total * 100, 1) if total else 0
    e2e_rate  = round(e2e_pass  / total * 100, 1) if total else 0
    both_rate = round(both_pass / total * 100, 1) if total else 0

    sheet_name = 'UAT Result'
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws_sum = wb.create_sheet(sheet_name, 0)

    today = datetime.now().strftime('%d/%m/%Y %H:%M')
    feature_name = path.stem.replace('uat_', '').replace('_', ' ').title()

    rows = [
        (f'TỔNG KẾT UAT — {feature_name}', '', ''),
        (f'Cập nhật lúc: {today}', '', ''),
        (f'Modules: {", ".join(sorted(modules_seen)) or "(tất cả)"}', '', ''),
        ('', '', ''),
        ('Chỉ tiêu', 'Giá trị', 'Ghi chú'),
        ('Tổng số TC', total, ''),
        ('✅ Đạt (cả 2 layer)', both_pass, f'{both_rate}%'),
        ('', '', ''),
        ('Layer 1 — API smoke', '', ''),
        ('  API Pass', api_pass, f'{api_rate}%'),
        ('  API Fail', api_fail, ''),
        ('  API Skip/Blocked', api_skip, ''),
        ('', '', ''),
        ('Layer 2 — UI E2E', '', ''),
        ('  E2E Pass', e2e_pass, f'{e2e_rate}%'),
        ('  E2E Fail', e2e_fail, ''),
        ('  E2E Skip (API gate)', e2e_skip, ''),
        ('', '', ''),
        ('Bug phát hiện', '', ''),
        ('  P0/Critical fail', p0_fail, '🚨 BLOCKER' if p0_fail > 0 else ''),
        ('  P1/High fail', p1_fail, '⚠️ High priority' if p1_fail > 0 else ''),
        ('', '', ''),
        ('Exit Criteria', '', ''),
        ('  P0 100% pass', 'PASS' if p0_fail == 0 else '❌ FAIL', ''),
        ('  P1 >= 95% pass', 'PASS' if p1_fail == 0 else '❌ FAIL', ''),
        ('  Overall >= 80%', 'PASS' if both_rate >= 80 else '❌ FAIL', f'{both_rate}%'),
    ]

    for i, (a, b, c) in enumerate(rows, 1):
        ws_sum.cell(row=i, column=1, value=a)
        ws_sum.cell(row=i, column=2, value=b)
        ws_sum.cell(row=i, column=3, value=c)

    ws_sum.column_dimensions['A'].width = 35
    ws_sum.column_dimensions['B'].width = 12
    ws_sum.column_dimensions['C'].width = 22

    wb.save(path)
    print(f'✅ UAT Result updated: {total} TC | API {api_pass}/{total} ({api_rate}%) | E2E {e2e_pass}/{total} ({e2e_rate}%) | Both {both_pass}/{total} ({both_rate}%)')
    print(f'   P0 fail={p0_fail} | P1 fail={p1_fail}')
    print(f'   Saved: {path}')


if __name__ == '__main__':
    main()
