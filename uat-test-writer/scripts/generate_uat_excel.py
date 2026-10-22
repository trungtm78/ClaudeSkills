#!/usr/bin/env python3
"""
generate_uat_excel.py — Sinh file Excel UAT chuẩn enterprise 4 sheets.

Usage:
    python generate_uat_excel.py <input_json> <output_xlsx>

Input JSON schema (xem schema chi tiết ở references/excel-schema.md):
{
    "feature_name": "...",
    "complexity": "simple|medium|complex",
    "test_cases": [
        {
            "tc_id": "TC-001",
            "type": "GREEN|RED|EDGE|BOUNDARY|EP|STATE|DECISION|SECURITY|DATA|PERFORMANCE|A11Y|COMPAT|INTEGRATION|REGRESSION|RECOVERY|AUDIT|USABILITY",
            "priority": "P0|P1|P2|P3",
            "module": "...",
            "title": "...",
            "requirement": "REQ-XXX",
            "risk_level": "Cao|TB|Thấp",
            "technique": "...",
            "preconditions": "...",
            "steps": "...",
            "test_data": "...",
            "expected_ui": "...",
            "expected_api": "...",
            "expected_side": "...",
            "severity_if_fail": "Critical|High|Medium|Low",
            "notes": "..."
        }
    ],
    "test_data": {
        "accounts": [...],
        "boundary_values": [...],
        "payloads": [...]
    },
    "scope": {
        "in_scope": [...],
        "out_of_scope": [...],
        "exit_criteria": "..."
    }
}

Output: file .xlsx 4 sheets:
    1. Test Cases — chi tiết TC, cột Kết quả thực tế + Trạng thái + Bug ID để runner điền
    2. Test Data — accounts, boundary, payloads
    3. Summary — dashboard với formula auto-tính
    4. Bug Tracker — Bug ID, TC liên kết, Status workflow
"""

import json
import sys
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.comments import Comment

# ============ STYLE CONSTANTS ============
FONT_FAMILY = "Arial"

# Colors
COLOR_HEADER = "1F4E78"        # Dark blue
COLOR_SUBHEADER = "2E75B6"     # Medium blue
COLOR_GREEN = "C6EFCE"          # Light green - Pass
COLOR_RED = "FFC7CE"            # Light red - Fail
COLOR_YELLOW = "FFEB9C"         # Light yellow - Blocked/Open
COLOR_GRAY = "D9D9D9"           # Gray - N/A
COLOR_BORDER = "BFBFBF"
COLOR_P0 = "C00000"             # Dark red
COLOR_P1 = "ED7D31"             # Orange
COLOR_P2 = "FFC000"             # Yellow
COLOR_P3 = "70AD47"             # Green

# TC type colors
TYPE_COLORS = {
    "GREEN": "C6EFCE",
    "RED": "FFC7CE",
    "EDGE": "FCE4D6",
    "BOUNDARY": "DDEBF7",
    "EP": "E2EFDA",
    "STATE": "FFF2CC",
    "DECISION": "D9E1F2",
    "SECURITY": "FFB6C1",
    "DATA": "F4B084",
    "PERFORMANCE": "FFD966",
    "A11Y": "B4A7D6",
    "COMPAT": "A9D08E",
    "INTEGRATION": "9BC2E6",
    "REGRESSION": "FFE699",
    "RECOVERY": "F8CBAD",
    "AUDIT": "C9C9C9",
    "USABILITY": "BDD7EE",
}

# Borders
thin_border = Border(
    left=Side(style="thin", color=COLOR_BORDER),
    right=Side(style="thin", color=COLOR_BORDER),
    top=Side(style="thin", color=COLOR_BORDER),
    bottom=Side(style="thin", color=COLOR_BORDER),
)


def apply_header_style(cell, color=COLOR_HEADER):
    """Style header cell."""
    cell.font = Font(name=FONT_FAMILY, bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill("solid", start_color=color)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = thin_border


def apply_data_style(cell, wrap=True, center=False):
    """Style data cell."""
    cell.font = Font(name=FONT_FAMILY, size=10)
    cell.alignment = Alignment(
        horizontal="center" if center else "left",
        vertical="top",
        wrap_text=wrap,
    )
    cell.border = thin_border


# ============ SHEET 1: TEST CASES ============

TC_COLUMNS = [
    ("TC-ID", 12),
    ("Loại", 11),
    ("Độ ưu tiên", 11),
    ("Module", 15),
    ("Tiêu đề", 35),
    ("Yêu cầu", 14),
    ("Kỹ thuật test", 18),
    ("Mức độ rủi ro", 13),
    ("Điều kiện tiên quyết", 30),
    ("Các bước kiểm thử", 40),
    ("Dữ liệu kiểm thử", 25),
    ("Data fixtures cần", 22),    # L+ MỚI: reference đến Data Matrix
    ("Kết quả mong đợi - UI", 35),
    ("Kết quả mong đợi - API", 30),
    ("Kết quả mong đợi - Side effects", 30),
    ("Severity nếu fail", 14),
    ("Kết quả thực tế", 35),     # Q
    ("Trạng thái API", 14),       # R - layer 1 (API smoke gate)
    ("Trạng thái E2E", 14),       # S - layer 2 (UI E2E)
    ("Bug ID", 14),               # T
    ("Lần chạy cuối", 16),         # U
    ("Lịch sử chạy", 22),       # V - run history
    ("Cờ regression", 14),       # W - regression flag
    ("Ghi chú", 25),              # X
    # === Handoff-schema v10 (✱) — APPEND CUỐI để không xê dịch cột runner (R/S/W) ===
    ("Platform", 12),             # Y
    ("Persona", 14),              # Z
    ("Journey ref", 16),          # AA
    ("Oracle type", 13),          # AB
    ("Rule ref", 18),             # AC
    ("Oracle source", 30),        # AD
    ("Bug bắt được", 30),        # AE (catches_bug)
    ("Coverage IDs", 20),         # AF
    ("Backend policy", 15),       # AG
]


def create_test_cases_sheet(wb, test_cases, feature_name):
    """Tạo sheet Test Cases."""
    ws = wb.active
    ws.title = "Test Cases"

    # Title row
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(TC_COLUMNS))
    title_cell = ws.cell(row=1, column=1, value=f"BỘ TEST CASE UAT: {feature_name}")
    title_cell.font = Font(name=FONT_FAMILY, bold=True, size=14, color="FFFFFF")
    title_cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # Metadata row
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(TC_COLUMNS))
    meta_cell = ws.cell(
        row=2,
        column=1,
        value=f"Tổng số TC: {len(test_cases)} | Ngày tạo: {datetime.now().strftime('%d/%m/%Y')} | Generated by uat-test-writer skill",
    )
    meta_cell.font = Font(name=FONT_FAMILY, italic=True, size=9, color="595959")
    meta_cell.alignment = Alignment(horizontal="center", vertical="center")

    # Header row at row 3
    header_row = 3
    for col_idx, (col_name, col_width) in enumerate(TC_COLUMNS, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=col_name)
        apply_header_style(cell)
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width

    ws.row_dimensions[header_row].height = 40

    # Data rows
    for row_idx, tc in enumerate(test_cases, start=header_row + 1):
        # Compose expected sub-columns
        # LEAN MODE: nếu TC có field 'expected' (gộp), dùng cho cả 3 cột UI/API/Side
        # FULL MODE: dùng expected_ui, expected_api, expected_side riêng
        combined_expected = tc.get("expected", "")
        if combined_expected:
            # Lean mode: gộp expected → cho vào cột UI, để trống 2 cột còn lại
            expected_ui = combined_expected
            expected_api = ""
            expected_side = ""
        else:
            expected_ui = tc.get("expected_ui", "")
            expected_api = tc.get("expected_api", "")
            expected_side = tc.get("expected_side", "")

        ws.cell(row=row_idx, column=1, value=tc.get("tc_id", ""))
        ws.cell(row=row_idx, column=2, value=tc.get("type", ""))
        ws.cell(row=row_idx, column=3, value=tc.get("priority", ""))
        ws.cell(row=row_idx, column=4, value=tc.get("module", ""))
        ws.cell(row=row_idx, column=5, value=tc.get("title", ""))
        ws.cell(row=row_idx, column=6, value=tc.get("requirement", ""))
        ws.cell(row=row_idx, column=7, value=tc.get("technique", ""))
        ws.cell(row=row_idx, column=8, value=tc.get("risk_level", ""))
        ws.cell(row=row_idx, column=9, value=tc.get("preconditions", ""))
        ws.cell(row=row_idx, column=10, value=tc.get("steps", ""))
        ws.cell(row=row_idx, column=11, value=tc.get("test_data", ""))
        # Cột 12: Data fixtures cần (list of fixture IDs hoặc CSV)
        data_required = tc.get("data_required", "")
        if isinstance(data_required, list):
            data_required = ", ".join(data_required)
        ws.cell(row=row_idx, column=12, value=data_required)
        ws.cell(row=row_idx, column=13, value=expected_ui)
        ws.cell(row=row_idx, column=14, value=expected_api)
        ws.cell(row=row_idx, column=15, value=expected_side)
        ws.cell(row=row_idx, column=16, value=tc.get("severity_if_fail", ""))
        # Cols 17-24: để trống cho runner điền
        ws.cell(row=row_idx, column=17, value="")  # Q: Kết quả thực tế
        ws.cell(row=row_idx, column=18, value="")  # R: Trạng thái API (smoke gate)
        ws.cell(row=row_idx, column=19, value="")  # S: Trạng thái E2E (UI layer)
        ws.cell(row=row_idx, column=20, value="")  # T: Bug ID
        ws.cell(row=row_idx, column=21, value="")  # U: Lần chạy cuối
        ws.cell(row=row_idx, column=22, value="")  # V: Lịch sử chạy
        ws.cell(row=row_idx, column=23, value="")  # W: Cờ regression
        ws.cell(row=row_idx, column=24, value=tc.get("notes", ""))  # X: Ghi chú
        # === Handoff-schema v10 columns (Y..AG) ===
        ws.cell(row=row_idx, column=25, value=tc.get("platform", ""))
        ws.cell(row=row_idx, column=26, value=tc.get("persona", ""))
        ws.cell(row=row_idx, column=27, value=tc.get("journey_ref", ""))
        ws.cell(row=row_idx, column=28, value=tc.get("oracle_type", ""))
        ws.cell(row=row_idx, column=29, value=tc.get("rule_ref", ""))
        ws.cell(row=row_idx, column=30, value=tc.get("oracle_source", ""))
        ws.cell(row=row_idx, column=31, value=tc.get("catches_bug", ""))
        coverage_ids = tc.get("coverage_ids", "")
        if isinstance(coverage_ids, list):
            coverage_ids = ", ".join(coverage_ids)
        ws.cell(row=row_idx, column=32, value=coverage_ids)
        ws.cell(row=row_idx, column=33, value=tc.get("backend_policy", ""))

        # Apply data style
        for col_idx in range(1, len(TC_COLUMNS) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            center_cols = [1, 2, 3, 6, 7, 8, 16, 18, 19, 20, 21, 23, 25, 26, 28, 33]
            apply_data_style(cell, center=col_idx in center_cols)

        # Color code by type (column 2)
        type_color = TYPE_COLORS.get(tc.get("type", ""), "FFFFFF")
        ws.cell(row=row_idx, column=2).fill = PatternFill("solid", start_color=type_color)

        # Color code by priority (column 3)
        priority_colors = {"P0": COLOR_P0, "P1": COLOR_P1, "P2": COLOR_P2, "P3": COLOR_P3}
        prio = tc.get("priority", "")
        if prio in priority_colors:
            ws.cell(row=row_idx, column=3).font = Font(
                name=FONT_FAMILY, bold=True, color=priority_colors[prio], size=10
            )

        ws.row_dimensions[row_idx].height = 80

    # Data validation cho cột Trạng thái API (col R = 18) + E2E (col S = 19)
    dv_status_api = DataValidation(
        type="list",
        formula1='"Chưa chạy,Đang chạy,Đạt,Không đạt,Bị chặn,Bỏ qua"',
        allow_blank=True,
    )
    dv_status_api.error = "Chọn một trạng thái hợp lệ"
    dv_status_api.prompt = "Layer 1 - API smoke gate"
    ws.add_data_validation(dv_status_api)
    dv_status_api.add(f"R{header_row+1}:R{header_row+len(test_cases)}")

    dv_status_e2e = DataValidation(
        type="list",
        formula1='"Chưa chạy,Đang chạy,Đạt,Không đạt,Bị chặn,Bỏ qua"',
        allow_blank=True,
    )
    dv_status_e2e.error = "Chọn một trạng thái hợp lệ"
    dv_status_e2e.prompt = "Layer 2 - UI E2E (Chromium). 'Bỏ qua' nếu API smoke fail"
    ws.add_data_validation(dv_status_e2e)
    dv_status_e2e.add(f"S{header_row+1}:S{header_row+len(test_cases)}")

    # Conditional formatting cho cả 2 cột R (API) và S (E2E)
    for col_letter in ["R", "S"]:
        status_range = f"{col_letter}{header_row+1}:{col_letter}{header_row+len(test_cases)}"
        ws.conditional_formatting.add(
            status_range,
            CellIsRule(operator="equal", formula=['"Đạt"'], fill=PatternFill("solid", start_color=COLOR_GREEN)),
        )
        ws.conditional_formatting.add(
            status_range,
            CellIsRule(operator="equal", formula=['"Không đạt"'], fill=PatternFill("solid", start_color=COLOR_RED)),
        )
        ws.conditional_formatting.add(
            status_range,
            CellIsRule(operator="equal", formula=['"Bị chặn"'], fill=PatternFill("solid", start_color=COLOR_YELLOW)),
        )
        ws.conditional_formatting.add(
            status_range,
            CellIsRule(operator="equal", formula=['"Bỏ qua"'], fill=PatternFill("solid", start_color=COLOR_GRAY)),
        )

    # === Conditional formatting cho cột W (Cờ regression — col 23) ===
    regression_range = f"W{header_row+1}:W{header_row+len(test_cases)}"
    # Khi có giá trị "⚠️ REGRESSION" → highlight đỏ chói + font bold
    ws.conditional_formatting.add(
        regression_range,
        CellIsRule(
            operator="equal",
            formula=['"⚠️ REGRESSION"'],
            fill=PatternFill("solid", start_color="C00000"),  # Đỏ đậm
            font=Font(name=FONT_FAMILY, bold=True, color="FFFFFF", size=10),
        ),
    )
    # Khi đã ổn định sau regression → "✓ Đã fix"
    ws.conditional_formatting.add(
        regression_range,
        CellIsRule(
            operator="equal",
            formula=['"✓ Đã fix"'],
            fill=PatternFill("solid", start_color=COLOR_GREEN),
        ),
    )

    # Data validation cho Cờ regression
    dv_reg = DataValidation(
        type="list",
        formula1='"⚠️ REGRESSION,✓ Đã fix"',
        allow_blank=True,
    )
    dv_reg.prompt = "Tự động đánh dấu nếu TC từng Đạt nay Không đạt"
    ws.add_data_validation(dv_reg)
    dv_reg.add(regression_range)

    # Freeze panes — giữ header + cột TC-ID khi scroll
    ws.freeze_panes = f"C{header_row+1}"

    # Auto filter
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(TC_COLUMNS))}{header_row+len(test_cases)}"

    return ws


# ============ SHEET 2: TEST DATA ============

def create_test_data_sheet(wb, test_data):
    """Tạo sheet Test Data."""
    ws = wb.create_sheet("Test Data")

    row = 1

    # === Section: Accounts ===
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
    cell = ws.cell(row=row, column=1, value="1. TÀI KHOẢN KIỂM THỬ")
    cell.font = Font(name=FONT_FAMILY, bold=True, size=12, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[row].height = 25
    row += 1

    headers = ["ID", "Email", "Mật khẩu", "Vai trò", "Trạng thái", "Mục đích", "Ghi chú"]
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=h)
        apply_header_style(cell, color=COLOR_SUBHEADER)
    row += 1

    accounts = test_data.get("accounts", [])
    for acc in accounts:
        ws.cell(row=row, column=1, value=acc.get("id", ""))
        ws.cell(row=row, column=2, value=acc.get("email", ""))
        ws.cell(row=row, column=3, value=acc.get("password", ""))
        ws.cell(row=row, column=4, value=acc.get("role", ""))
        ws.cell(row=row, column=5, value=acc.get("status", ""))
        ws.cell(row=row, column=6, value=acc.get("purpose", ""))
        ws.cell(row=row, column=7, value=acc.get("notes", ""))
        for col_idx in range(1, 8):
            apply_data_style(ws.cell(row=row, column=col_idx))
        row += 1

    row += 2  # Spacer

    # === Section: Boundary Values ===
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
    cell = ws.cell(row=row, column=1, value="2. BOUNDARY VALUES (BVA)")
    cell.font = Font(name=FONT_FAMILY, bold=True, size=12, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[row].height = 25
    row += 1

    bv_headers = ["Field", "Giá trị", "Loại", "Kỳ vọng", "Ghi chú"]
    for col_idx, h in enumerate(bv_headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=h)
        apply_header_style(cell, color=COLOR_SUBHEADER)
    row += 1

    boundary_values = test_data.get("boundary_values", [])
    for bv in boundary_values:
        ws.cell(row=row, column=1, value=bv.get("field", ""))
        ws.cell(row=row, column=2, value=str(bv.get("value", "")))
        ws.cell(row=row, column=3, value=bv.get("type", ""))  # min-1, min, max, max+1
        ws.cell(row=row, column=4, value=bv.get("expected", ""))
        ws.cell(row=row, column=5, value=bv.get("notes", ""))
        for col_idx in range(1, 6):
            apply_data_style(ws.cell(row=row, column=col_idx))
        row += 1

    row += 2

    # === Section: Security Payloads ===
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
    cell = ws.cell(row=row, column=1, value="3. SECURITY PAYLOADS (OWASP)")
    cell.font = Font(name=FONT_FAMILY, bold=True, size=12, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[row].height = 25
    row += 1

    pl_headers = ["Field/Endpoint", "Payload", "Loại tấn công", "Kỳ vọng", "OWASP Reference"]
    for col_idx, h in enumerate(pl_headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=h)
        apply_header_style(cell, color=COLOR_SUBHEADER)
    row += 1

    payloads = test_data.get("payloads", [])
    for pl in payloads:
        ws.cell(row=row, column=1, value=pl.get("target", ""))
        ws.cell(row=row, column=2, value=pl.get("payload", ""))
        ws.cell(row=row, column=3, value=pl.get("attack_type", ""))
        ws.cell(row=row, column=4, value=pl.get("expected", ""))
        ws.cell(row=row, column=5, value=pl.get("owasp_ref", ""))
        for col_idx in range(1, 6):
            apply_data_style(ws.cell(row=row, column=col_idx))
        row += 1

    # Column widths
    widths = [10, 30, 25, 15, 18, 35, 25]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    return ws


# ============ SHEET 3: SUMMARY DASHBOARD ============

def create_summary_sheet(wb, test_cases, scope):
    """Tạo sheet Summary với formula auto-tính."""
    ws = wb.create_sheet("Summary", 0)  # Put first - dashboard view

    # === Title ===
    ws.merge_cells("A1:F1")
    cell = ws.cell(row=1, column=1, value="📊 DASHBOARD - UAT EXECUTION SUMMARY")
    cell.font = Font(name=FONT_FAMILY, bold=True, size=16, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 35

    # === Overview metrics ===
    ws.cell(row=3, column=1, value="TỔNG QUAN").font = Font(name=FONT_FAMILY, bold=True, size=12)
    ws.merge_cells("A3:F3")
    ws.cell(row=3, column=1).fill = PatternFill("solid", start_color=COLOR_SUBHEADER)
    ws.cell(row=3, column=1).font = Font(name=FONT_FAMILY, bold=True, color="FFFFFF")
    ws.cell(row=3, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)

    total = len(test_cases)
    api_range = f"'Test Cases'!R4:R{4+total-1}"   # Cột Trạng thái API (col 18)
    e2e_range = f"'Test Cases'!S4:S{4+total-1}"   # Cột Trạng thái E2E (col 19)
    type_range = f"'Test Cases'!B4:B{4+total-1}"
    prio_range = f"'Test Cases'!C4:C{4+total-1}"

    # Combined "Đạt" = CẢ 2 layer đều Đạt
    combined_pass_formula = f'=SUMPRODUCT(({api_range}="Đạt")*({e2e_range}="Đạt"))'
    # "Không đạt" = ÍT NHẤT 1 layer fail
    combined_fail_formula = f'=SUMPRODUCT((({api_range}="Không đạt")+({e2e_range}="Không đạt"))>0)*1'

    metrics = [
        ("Tổng số TC", total, "Số test case đã viết"),
        ("✅ Đạt (cả 2 layer)", combined_pass_formula, "TC pass cả API VÀ E2E"),
        ("❌ Không đạt", combined_fail_formula, "TC fail ít nhất 1 layer"),
        ("API Đạt", f'=COUNTIF({api_range},"Đạt")', "Layer 1 — API smoke"),
        ("API Không đạt", f'=COUNTIF({api_range},"Không đạt")', "API fail"),
        ("E2E Đạt", f'=COUNTIF({e2e_range},"Đạt")', "Layer 2 — UI E2E"),
        ("E2E Không đạt", f'=COUNTIF({e2e_range},"Không đạt")', "E2E fail"),
        ("E2E Bỏ qua", f'=COUNTIF({e2e_range},"Bỏ qua")', "Skip do API smoke fail"),
        ("Chưa chạy", f'=COUNTBLANK({api_range})+COUNTIF({api_range},"Chưa chạy")', "Còn lại"),
    ]

    row = 4
    for label, val, desc in metrics:
        ws.cell(row=row, column=1, value=label).font = Font(name=FONT_FAMILY, bold=True, size=11)
        ws.cell(row=row, column=2, value=val).font = Font(name=FONT_FAMILY, bold=True, size=12, color=COLOR_HEADER)
        ws.cell(row=row, column=3, value=desc).font = Font(name=FONT_FAMILY, italic=True, size=9, color="595959")
        for c in range(1, 4):
            ws.cell(row=row, column=c).border = thin_border
        row += 1

    # === Pass rate (combined - cả 2 layer) ===
    row += 1
    ws.cell(row=row, column=1, value="Tỷ lệ đạt (cả 2 layer)").font = Font(name=FONT_FAMILY, bold=True, size=11)
    ws.cell(row=row, column=2, value=f'=IFERROR(SUMPRODUCT(({api_range}="Đạt")*({e2e_range}="Đạt"))/(SUMPRODUCT(({api_range}="Đạt")*({e2e_range}="Đạt"))+SUMPRODUCT((({api_range}="Không đạt")+({e2e_range}="Không đạt"))>0)),0)').number_format = "0.0%"
    ws.cell(row=row, column=2).font = Font(name=FONT_FAMILY, bold=True, size=14, color="009900")
    ws.cell(row=row, column=3, value="API+E2E đều Đạt / Tổng đã chạy").font = Font(name=FONT_FAMILY, italic=True, size=9)
    for c in range(1, 4):
        ws.cell(row=row, column=c).border = thin_border
    row += 1

    # Tỷ lệ pass theo từng layer riêng
    ws.cell(row=row, column=1, value="API pass rate").font = Font(name=FONT_FAMILY, bold=True, size=11)
    ws.cell(row=row, column=2, value=f'=IFERROR(COUNTIF({api_range},"Đạt")/(COUNTIF({api_range},"Đạt")+COUNTIF({api_range},"Không đạt")),0)').number_format = "0.0%"
    ws.cell(row=row, column=2).font = Font(name=FONT_FAMILY, bold=True, size=12)
    ws.cell(row=row, column=3, value="Layer 1").font = Font(name=FONT_FAMILY, italic=True, size=9)
    for c in range(1, 4):
        ws.cell(row=row, column=c).border = thin_border
    row += 1

    ws.cell(row=row, column=1, value="E2E pass rate").font = Font(name=FONT_FAMILY, bold=True, size=11)
    ws.cell(row=row, column=2, value=f'=IFERROR(COUNTIF({e2e_range},"Đạt")/(COUNTIF({e2e_range},"Đạt")+COUNTIF({e2e_range},"Không đạt")),0)').number_format = "0.0%"
    ws.cell(row=row, column=2).font = Font(name=FONT_FAMILY, bold=True, size=12)
    ws.cell(row=row, column=3, value="Layer 2 (UI Chromium)").font = Font(name=FONT_FAMILY, italic=True, size=9)
    for c in range(1, 4):
        ws.cell(row=row, column=c).border = thin_border
    row += 1

    ws.cell(row=row, column=1, value="Tỷ lệ hoàn thành").font = Font(name=FONT_FAMILY, bold=True, size=11)
    ws.cell(row=row, column=2, value=f'=IFERROR((COUNTIF({api_range},"Đạt")+COUNTIF({api_range},"Không đạt")+COUNTIF({api_range},"Bị chặn"))/{total},0)').number_format = "0.0%"
    ws.cell(row=row, column=2).font = Font(name=FONT_FAMILY, bold=True, size=14)
    ws.cell(row=row, column=3, value="API đã chạy / Tổng").font = Font(name=FONT_FAMILY, italic=True, size=9)
    for c in range(1, 4):
        ws.cell(row=row, column=c).border = thin_border
    row += 2

    # === Coverage by type ===
    ws.cell(row=row, column=1, value="ĐỘ PHỦ THEO LOẠI").font = Font(name=FONT_FAMILY, bold=True, size=12, color="FFFFFF")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    ws.cell(row=row, column=1).fill = PatternFill("solid", start_color=COLOR_SUBHEADER)
    ws.cell(row=row, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    row += 1

    type_headers = ["Loại", "Số TC", "Tỷ lệ", "Pass", "Fail", "Pass rate"]
    for col_idx, h in enumerate(type_headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=h)
        apply_header_style(cell, color=COLOR_SUBHEADER)
    row += 1

    all_types = ["GREEN", "RED", "EDGE", "BOUNDARY", "EP", "STATE", "DECISION",
                 "SECURITY", "DATA", "PERFORMANCE", "A11Y", "COMPAT",
                 "INTEGRATION", "REGRESSION", "RECOVERY", "AUDIT", "USABILITY"]

    for t in all_types:
        ws.cell(row=row, column=1, value=t).font = Font(name=FONT_FAMILY, bold=True, size=10)
        ws.cell(row=row, column=1).fill = PatternFill("solid", start_color=TYPE_COLORS.get(t, "FFFFFF"))
        ws.cell(row=row, column=2, value=f'=COUNTIF({type_range},"{t}")')
        ws.cell(row=row, column=3, value=f'=IFERROR(B{row}/{total},0)').number_format = "0.0%"
        ws.cell(row=row, column=4, value=f'=COUNTIFS({type_range},"{t}",{e2e_range},"Đạt")')
        ws.cell(row=row, column=5, value=f'=COUNTIFS({type_range},"{t}",{e2e_range},"Không đạt")')
        ws.cell(row=row, column=6, value=f'=IFERROR(D{row}/(D{row}+E{row}),0)').number_format = "0.0%"
        for c in range(1, 7):
            ws.cell(row=row, column=c).border = thin_border
            ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
        row += 1

    row += 1

    # === Breakdown by priority ===
    ws.cell(row=row, column=1, value="THEO ĐỘ ƯU TIÊN").font = Font(name=FONT_FAMILY, bold=True, size=12, color="FFFFFF")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    ws.cell(row=row, column=1).fill = PatternFill("solid", start_color=COLOR_SUBHEADER)
    ws.cell(row=row, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    row += 1

    prio_headers = ["Priority", "Số TC", "Tỷ lệ", "Pass", "Fail", "Pass rate"]
    for col_idx, h in enumerate(prio_headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=h)
        apply_header_style(cell, color=COLOR_SUBHEADER)
    row += 1

    priority_colors_map = {"P0": COLOR_P0, "P1": COLOR_P1, "P2": COLOR_P2, "P3": COLOR_P3}
    for p in ["P0", "P1", "P2", "P3"]:
        ws.cell(row=row, column=1, value=p).font = Font(name=FONT_FAMILY, bold=True, size=10, color=priority_colors_map[p])
        ws.cell(row=row, column=2, value=f'=COUNTIF({prio_range},"{p}")')
        ws.cell(row=row, column=3, value=f'=IFERROR(B{row}/{total},0)').number_format = "0.0%"
        ws.cell(row=row, column=4, value=f'=COUNTIFS({prio_range},"{p}",{e2e_range},"Đạt")')
        ws.cell(row=row, column=5, value=f'=COUNTIFS({prio_range},"{p}",{e2e_range},"Không đạt")')
        ws.cell(row=row, column=6, value=f'=IFERROR(D{row}/(D{row}+E{row}),0)').number_format = "0.0%"
        for c in range(1, 7):
            ws.cell(row=row, column=c).border = thin_border
            ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
        row += 1

    row += 1

    # === Exit Criteria check ===
    ws.cell(row=row, column=1, value="EXIT CRITERIA").font = Font(name=FONT_FAMILY, bold=True, size=12, color="FFFFFF")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    ws.cell(row=row, column=1).fill = PatternFill("solid", start_color=COLOR_SUBHEADER)
    ws.cell(row=row, column=1).alignment = Alignment(horizontal="left", vertical="center", indent=1)
    row += 1

    ec_headers = ["Tiêu chí", "Yêu cầu", "Thực tế", "Trạng thái"]
    for col_idx, h in enumerate(ec_headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=h)
        apply_header_style(cell, color=COLOR_SUBHEADER)
    row += 1

    # P0 pass rate ≥ 100%
    p0_pass_formula = f'=IFERROR(COUNTIFS({prio_range},"P0",{e2e_range},"Đạt")/COUNTIF({prio_range},"P0"),0)'
    ws.cell(row=row, column=1, value="P0 pass rate")
    ws.cell(row=row, column=2, value="≥ 100%")
    ws.cell(row=row, column=3, value=p0_pass_formula).number_format = "0.0%"
    ws.cell(row=row, column=4, value=f'=IF(C{row}>=1,"✅ Đạt","❌ Chưa đạt")')

    p0_row = row
    for c in range(1, 5):
        ws.cell(row=row, column=c).border = thin_border
        ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
    row += 1

    # P1 pass rate ≥ 95%
    p1_pass_formula = f'=IFERROR(COUNTIFS({prio_range},"P1",{e2e_range},"Đạt")/COUNTIF({prio_range},"P1"),0)'
    ws.cell(row=row, column=1, value="P1 pass rate")
    ws.cell(row=row, column=2, value="≥ 95%")
    ws.cell(row=row, column=3, value=p1_pass_formula).number_format = "0.0%"
    ws.cell(row=row, column=4, value=f'=IF(C{row}>=0.95,"✅ Đạt","❌ Chưa đạt")')
    for c in range(1, 5):
        ws.cell(row=row, column=c).border = thin_border
        ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
    row += 1

    # P2 pass rate ≥ 85%
    p2_pass_formula = f'=IFERROR(COUNTIFS({prio_range},"P2",{e2e_range},"Đạt")/MAX(COUNTIF({prio_range},"P2"),1),1)'
    ws.cell(row=row, column=1, value="P2 pass rate")
    ws.cell(row=row, column=2, value="≥ 85%")
    ws.cell(row=row, column=3, value=p2_pass_formula).number_format = "0.0%"
    ws.cell(row=row, column=4, value=f'=IF(C{row}>=0.85,"✅ Đạt","❌ Chưa đạt")')
    for c in range(1, 5):
        ws.cell(row=row, column=c).border = thin_border
        ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
    row += 1

    # Open Critical bugs = 0
    ws.cell(row=row, column=1, value="Bug Critical mở")
    ws.cell(row=row, column=2, value="= 0")
    ws.cell(row=row, column=3, value=f'=COUNTIFS(\'Bug Tracker\'!D:D,"Critical",\'Bug Tracker\'!E:E,"Open")+COUNTIFS(\'Bug Tracker\'!D:D,"Critical",\'Bug Tracker\'!E:E,"Fixing")+COUNTIFS(\'Bug Tracker\'!D:D,"Critical",\'Bug Tracker\'!E:E,"Fixed")')
    ws.cell(row=row, column=4, value=f'=IF(C{row}=0,"✅ Đạt","❌ Chưa đạt")')
    bug_critical_row = row
    for c in range(1, 5):
        ws.cell(row=row, column=c).border = thin_border
        ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
    row += 1

    # Số TC bị regression = 0 (MỚI)
    ws.cell(row=row, column=1, value="TC bị regression").font = Font(name=FONT_FAMILY, bold=True, color="C00000")
    ws.cell(row=row, column=2, value="= 0")
    ws.cell(row=row, column=3, value=f'=COUNTIF(\'Test Cases\'!U:U,"⚠️ REGRESSION")')
    ws.cell(row=row, column=4, value=f'=IF(C{row}=0,"✅ Không có","🚨 BLOCK RELEASE")')
    regression_row = row
    for c in range(1, 5):
        ws.cell(row=row, column=c).border = thin_border
        ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
    # Highlight nếu có regression
    ws.conditional_formatting.add(
        f"D{row}",
        CellIsRule(
            operator="equal",
            formula=['"🚨 BLOCK RELEASE"'],
            fill=PatternFill("solid", start_color="C00000"),
            font=Font(name=FONT_FAMILY, bold=True, color="FFFFFF"),
        ),
    )
    row += 1

    # Số regression bug chưa fix (từ Regression Log)
    ws.cell(row=row, column=1, value="Regression chưa fix").font = Font(name=FONT_FAMILY, bold=True, color="C00000")
    ws.cell(row=row, column=2, value="= 0")
    ws.cell(row=row, column=3, value=f'=COUNTIF(\'Regression Log\'!K:K,"No")+COUNTIF(\'Regression Log\'!K:K,"Verifying")')
    ws.cell(row=row, column=4, value=f'=IF(C{row}=0,"✅ Không có","🚨 BLOCK RELEASE")')
    regression_fix_row = row
    for c in range(1, 5):
        ws.cell(row=row, column=c).border = thin_border
        ws.cell(row=row, column=c).alignment = Alignment(horizontal="center" if c > 1 else "left")
    ws.conditional_formatting.add(
        f"D{row}",
        CellIsRule(
            operator="equal",
            formula=['"🚨 BLOCK RELEASE"'],
            fill=PatternFill("solid", start_color="C00000"),
            font=Font(name=FONT_FAMILY, bold=True, color="FFFFFF"),
        ),
    )
    row += 1

    # === Regression Alert Banner (chỉ hiện khi có regression) ===
    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    alert_formula = (
        f'=IF(OR(C{regression_row}>0,C{regression_fix_row}>0),'
        f'"🚨 CẢNH BÁO: Phát hiện {{}}TC bị regression và {{}}bug regression chưa fix - "&'
        f'C{regression_row}&" + "&C{regression_fix_row}&" — XEM SHEET ''Regression Log'' VÀ Test Cases (cột Cờ regression)",'
        f'"✅ Không có regression detected")'
    )
    # Simpler version without nested
    alert_formula_simple = (
        f'=IF(OR(C{regression_row}>0,C{regression_fix_row}>0),'
        f'"🚨 CẢNH BÁO REGRESSION: "&C{regression_row}&" TC level-down, "&C{regression_fix_row}&" bug regression chưa fix - XEM Regression Log sheet",'
        f'"")'
    )
    alert_cell = ws.cell(row=row, column=1, value=alert_formula_simple)
    alert_cell.font = Font(name=FONT_FAMILY, bold=True, size=12, color="FFFFFF")
    alert_cell.fill = PatternFill("solid", start_color="C00000")
    alert_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 40
    alert_row = row
    row += 1

    # Overall verdict (UPDATED: thêm điều kiện no regression)
    row += 1
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    cell = ws.cell(
        row=row,
        column=1,
        value=(
            f'=IF(AND('
            f'C{p0_row}>=1,'
            f'C{p0_row+1}>=0.95,'
            f'C{p0_row+2}>=0.85,'
            f'C{bug_critical_row}=0,'
            f'C{regression_row}=0,'
            f'C{regression_fix_row}=0'
            f'),"🎉 SẴN SÀNG RELEASE",'
            f'IF(OR(C{regression_row}>0,C{regression_fix_row}>0),'
            f'"⛔ BLOCK RELEASE — CÓ REGRESSION (LEVEL DOWN)",'
            f'"⛔ CHƯA SẴN SÀNG RELEASE"))'
        ),
    )
    cell.font = Font(name=FONT_FAMILY, bold=True, size=14, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[row].height = 30
    # Highlight ĐỎ CHÓI nếu có regression
    ws.conditional_formatting.add(
        f"A{row}",
        FormulaRule(
            formula=[f'OR(C{regression_row}>0,C{regression_fix_row}>0)'],
            fill=PatternFill("solid", start_color="C00000"),
            font=Font(name=FONT_FAMILY, bold=True, size=14, color="FFFFFF"),
        ),
    )

    # Column widths
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14

    return ws


# ============ SHEET 4: BUG TRACKER ============

BUG_COLUMNS = [
    ("Bug ID", 12),
    ("TC ID liên kết", 16),
    ("Mô tả bug", 50),
    ("Severity", 14),
    ("Status", 16),
    ("Ngày phát hiện", 16),
    ("Lần fix gần nhất", 16),
    ("Re-test kết quả", 16),
    ("Ghi chú", 30),
]


def create_bug_tracker_sheet(wb):
    """Tạo sheet Bug Tracker."""
    ws = wb.create_sheet("Bug Tracker")

    # Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(BUG_COLUMNS))
    cell = ws.cell(row=1, column=1, value="🐛 BUG TRACKER")
    cell.font = Font(name=FONT_FAMILY, bold=True, size=14, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # Instructions
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(BUG_COLUMNS))
    note = ws.cell(
        row=2,
        column=1,
        value="Workflow: Open → Fixing → Fixed → Verified → Closed. Mỗi lần TC fail tự động tạo bug record.",
    )
    note.font = Font(name=FONT_FAMILY, italic=True, size=9, color="595959")
    note.alignment = Alignment(horizontal="center")

    # Headers
    for col_idx, (col_name, col_width) in enumerate(BUG_COLUMNS, start=1):
        cell = ws.cell(row=3, column=col_idx, value=col_name)
        apply_header_style(cell)
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width
    ws.row_dimensions[3].height = 35

    # Add 50 empty data rows for runner to fill
    for row_idx in range(4, 54):
        for col_idx in range(1, len(BUG_COLUMNS) + 1):
            cell = ws.cell(row=row_idx, column=col_idx, value="")
            center_cols = [1, 2, 4, 5, 6, 7, 8]
            apply_data_style(cell, center=col_idx in center_cols)
        ws.row_dimensions[row_idx].height = 30

    # Data validation - Severity
    dv_sev = DataValidation(
        type="list",
        formula1='"Critical,High,Medium,Low"',
        allow_blank=True,
    )
    ws.add_data_validation(dv_sev)
    dv_sev.add("D4:D54")

    # Data validation - Status (workflow)
    dv_status = DataValidation(
        type="list",
        formula1='"Open,Fixing,Fixed,Verified,Closed,Reopened,Cannot Reproduce,Wont Fix"',
        allow_blank=True,
    )
    dv_status.prompt = "Open → Fixing → Fixed → Verified → Closed"
    ws.add_data_validation(dv_status)
    dv_status.add("E4:E54")

    # Data validation - Re-test
    dv_retest = DataValidation(
        type="list",
        formula1='"Pass,Fail,Pending"',
        allow_blank=True,
    )
    ws.add_data_validation(dv_retest)
    dv_retest.add("H4:H54")

    # Conditional formatting - Status
    status_range = "E4:E54"
    ws.conditional_formatting.add(
        status_range,
        CellIsRule(operator="equal", formula=['"Open"'], fill=PatternFill("solid", start_color=COLOR_RED)),
    )
    ws.conditional_formatting.add(
        status_range,
        CellIsRule(operator="equal", formula=['"Fixing"'], fill=PatternFill("solid", start_color=COLOR_YELLOW)),
    )
    ws.conditional_formatting.add(
        status_range,
        CellIsRule(operator="equal", formula=['"Fixed"'], fill=PatternFill("solid", start_color="B4C7E7")),
    )
    ws.conditional_formatting.add(
        status_range,
        CellIsRule(operator="equal", formula=['"Verified"'], fill=PatternFill("solid", start_color=COLOR_GREEN)),
    )
    ws.conditional_formatting.add(
        status_range,
        CellIsRule(operator="equal", formula=['"Closed"'], fill=PatternFill("solid", start_color="D9D9D9")),
    )
    ws.conditional_formatting.add(
        status_range,
        CellIsRule(operator="equal", formula=['"Reopened"'], fill=PatternFill("solid", start_color="FFB6C1")),
    )

    # Conditional formatting - Severity
    sev_range = "D4:D54"
    ws.conditional_formatting.add(
        sev_range,
        CellIsRule(operator="equal", formula=['"Critical"'], fill=PatternFill("solid", start_color="C00000"),
                   font=Font(name=FONT_FAMILY, bold=True, color="FFFFFF")),
    )
    ws.conditional_formatting.add(
        sev_range,
        CellIsRule(operator="equal", formula=['"High"'], fill=PatternFill("solid", start_color="ED7D31")),
    )
    ws.conditional_formatting.add(
        sev_range,
        CellIsRule(operator="equal", formula=['"Medium"'], fill=PatternFill("solid", start_color="FFC000")),
    )
    ws.conditional_formatting.add(
        sev_range,
        CellIsRule(operator="equal", formula=['"Low"'], fill=PatternFill("solid", start_color="70AD47")),
    )

    # Freeze panes
    ws.freeze_panes = "A4"

    # Auto filter
    ws.auto_filter.ref = f"A3:{get_column_letter(len(BUG_COLUMNS))}53"

    return ws


# ============ SHEET 5: REGRESSION LOG ============

REGRESSION_COLUMNS = [
    ("Reg ID", 12),
    ("TC ID", 14),
    ("Module", 18),
    ("Lần phát hiện", 16),
    ("Bug gốc gây regression", 22),  # BUG-XXX nào trigger ra regression này
    ("Status trước retest", 18),       # Trạng thái cũ (thường là Đạt)
    ("Status sau retest", 18),         # Trạng thái mới (Không đạt)
    ("Severity gốc", 14),              # Severity của TC này khi viết
    ("Severity regression", 18),       # Severity gốc +1 level (escalate)
    ("Mô tả regression", 50),
    ("Đã fix?", 12),                   # Yes/No
    ("Ngày verify lại", 16),
    ("Ghi chú", 30),
]


def create_regression_log_sheet(wb):
    """Tạo sheet Regression Log để track lỗi level down."""
    ws = wb.create_sheet("Regression Log")

    # Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(REGRESSION_COLUMNS))
    cell = ws.cell(
        row=1,
        column=1,
        value="⚠️ REGRESSION LOG — Theo dõi lỗi level down (TC từng Đạt nay Không đạt)",
    )
    cell.font = Font(name=FONT_FAMILY, bold=True, size=14, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color="C00000")  # Đỏ chói cho cảnh báo
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # Note
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(REGRESSION_COLUMNS))
    note = ws.cell(
        row=2,
        column=1,
        value=(
            "Auto-generated bởi runner khi phát hiện TC từng Đạt giờ Không đạt sau khi fix bug khác. "
            "Severity tự động ESCALATE +1 level (High→Critical, Medium→High...). "
            "BẤT KỲ regression nào còn open đều BLOCK release."
        ),
    )
    note.font = Font(name=FONT_FAMILY, italic=True, size=9, color="595959")
    note.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.row_dimensions[2].height = 35

    # Headers
    for col_idx, (col_name, col_width) in enumerate(REGRESSION_COLUMNS, start=1):
        cell = ws.cell(row=3, column=col_idx, value=col_name)
        apply_header_style(cell, color="C00000")
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width
    ws.row_dimensions[3].height = 35

    # 30 empty rows for runner to fill
    for row_idx in range(4, 34):
        for col_idx in range(1, len(REGRESSION_COLUMNS) + 1):
            cell = ws.cell(row=row_idx, column=col_idx, value="")
            center_cols = [1, 2, 4, 6, 7, 8, 9, 11, 12]
            apply_data_style(cell, center=col_idx in center_cols)
        ws.row_dimensions[row_idx].height = 35

    # Data validation - Severity gốc (col H = 8)
    dv_sev_orig = DataValidation(
        type="list", formula1='"Critical,High,Medium,Low"', allow_blank=True
    )
    ws.add_data_validation(dv_sev_orig)
    dv_sev_orig.add("H4:H34")

    # Data validation - Severity regression (col I = 9)
    dv_sev_reg = DataValidation(
        type="list", formula1='"Critical,High,Medium,Low"', allow_blank=True
    )
    ws.add_data_validation(dv_sev_reg)
    dv_sev_reg.add("I4:I34")

    # Data validation - Đã fix? (col K = 11)
    dv_fixed = DataValidation(type="list", formula1='"Yes,No,Verifying"', allow_blank=True)
    ws.add_data_validation(dv_fixed)
    dv_fixed.add("K4:K34")

    # Conditional formatting - Severity regression (highlight nặng)
    sev_reg_range = "I4:I34"
    ws.conditional_formatting.add(
        sev_reg_range,
        CellIsRule(
            operator="equal",
            formula=['"Critical"'],
            fill=PatternFill("solid", start_color="C00000"),
            font=Font(name=FONT_FAMILY, bold=True, color="FFFFFF"),
        ),
    )
    ws.conditional_formatting.add(
        sev_reg_range,
        CellIsRule(operator="equal", formula=['"High"'], fill=PatternFill("solid", start_color="ED7D31")),
    )
    ws.conditional_formatting.add(
        sev_reg_range,
        CellIsRule(operator="equal", formula=['"Medium"'], fill=PatternFill("solid", start_color="FFC000")),
    )

    # Conditional formatting - Đã fix?
    fixed_range = "K4:K34"
    ws.conditional_formatting.add(
        fixed_range,
        CellIsRule(operator="equal", formula=['"No"'], fill=PatternFill("solid", start_color="FFC7CE")),
    )
    ws.conditional_formatting.add(
        fixed_range,
        CellIsRule(operator="equal", formula=['"Yes"'], fill=PatternFill("solid", start_color=COLOR_GREEN)),
    )
    ws.conditional_formatting.add(
        fixed_range,
        CellIsRule(operator="equal", formula=['"Verifying"'], fill=PatternFill("solid", start_color=COLOR_YELLOW)),
    )

    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:{get_column_letter(len(REGRESSION_COLUMNS))}33"

    return ws


# ============ SHEET 6: DATA MATRIX ============

DATA_MATRIX_COLUMNS = [
    ("Fixture ID", 28),         # vd: user.pending.D0
    ("Entity", 14),              # User / Order / Subscription
    ("State", 16),               # Pending / Active / ...
    ("Lifecycle", 12),           # D0 / D7 / D30 / D-1
    ("Shape", 14),               # single / sparse / full / empty
    ("Mô tả", 40),               # Free text
    ("Setup type", 12),          # api / sql / factory
    ("Setup recipe", 50),        # JSON inline
    ("Cleanup recipe", 30),      # JSON inline
    ("Outputs", 25),             # field mapping
    ("TC sử dụng", 25),          # Back-reference list TC-IDs
]


def create_data_matrix_sheet(wb, data_fixtures, test_cases):
    """Sheet 6: Data Maturity Matrix — data fixtures cho mọi state/lifecycle/shape."""
    ws = wb.create_sheet("Data Matrix")

    # Title
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(DATA_MATRIX_COLUMNS))
    cell = ws.cell(
        row=1, column=1,
        value="🗂️ DATA MATURITY MATRIX — Fixtures runner seed tự động trước mỗi test",
    )
    cell.font = Font(name=FONT_FAMILY, bold=True, size=14, color="FFFFFF")
    cell.fill = PatternFill("solid", start_color=COLOR_HEADER)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # Note
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(DATA_MATRIX_COLUMNS))
    note = ws.cell(
        row=2, column=1,
        value=(
            "Mỗi fixture có ID format <entity>.<state>.<lifecycle>.<shape>. "
            "Runner đọc setup_recipe → tự seed data trước test, KHÔNG cần human chạy SQL. "
            "Cleanup tự động sau test."
        ),
    )
    note.font = Font(name=FONT_FAMILY, italic=True, size=9, color="595959")
    note.alignment = Alignment(horizontal="center", wrap_text=True)
    ws.row_dimensions[2].height = 35

    # Headers
    for col_idx, (col_name, col_width) in enumerate(DATA_MATRIX_COLUMNS, start=1):
        cell = ws.cell(row=3, column=col_idx, value=col_name)
        apply_header_style(cell)
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width
    ws.row_dimensions[3].height = 35

    # Build back-reference: fixture_id → list TC IDs sử dụng
    tc_by_fixture = {}
    for tc in test_cases:
        tc_id = tc.get("tc_id", "")
        data_req = tc.get("data_required", [])
        if isinstance(data_req, str):
            data_req = [x.strip() for x in data_req.split(",") if x.strip()]
        for fid in data_req:
            tc_by_fixture.setdefault(fid, []).append(tc_id)

    # Data rows
    if not data_fixtures:
        # Empty placeholder rows
        ws.cell(row=4, column=1, value="⚠️ Chưa có fixture nào define").font = Font(
            name=FONT_FAMILY, italic=True, color="C00000", size=11
        )
        ws.cell(row=4, column=2, value="Xem references/data-maturity-matrix.md để biết cách viết")
    else:
        for row_idx, fx in enumerate(data_fixtures, start=4):
            fid = fx.get("fixture_id", "")
            ws.cell(row=row_idx, column=1, value=fid)
            ws.cell(row=row_idx, column=2, value=fx.get("entity", ""))
            ws.cell(row=row_idx, column=3, value=fx.get("state", ""))
            ws.cell(row=row_idx, column=4, value=fx.get("lifecycle", ""))
            ws.cell(row=row_idx, column=5, value=fx.get("shape", "single"))
            ws.cell(row=row_idx, column=6, value=fx.get("description", ""))

            setup = fx.get("setup_recipe", {})
            cleanup = fx.get("cleanup_recipe", {})
            outputs = fx.get("outputs", {})

            ws.cell(row=row_idx, column=7, value=setup.get("type", "") if isinstance(setup, dict) else "")
            ws.cell(row=row_idx, column=8, value=json.dumps(setup, ensure_ascii=False) if setup else "")
            ws.cell(row=row_idx, column=9, value=json.dumps(cleanup, ensure_ascii=False) if cleanup else "")
            ws.cell(row=row_idx, column=10, value=json.dumps(outputs, ensure_ascii=False) if outputs else "")
            ws.cell(row=row_idx, column=11, value=", ".join(tc_by_fixture.get(fid, [])))

            for col_idx in range(1, len(DATA_MATRIX_COLUMNS) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                center_cols = [2, 3, 4, 5, 7]
                apply_data_style(cell, center=col_idx in center_cols)

            # Color code Entity (col B)
            entity_color = {
                "User": "DDEBF7",
                "Order": "FCE4D6",
                "Subscription": "E2EFDA",
                "Cart": "FFF2CC",
                "Product": "D9E1F2",
            }.get(fx.get("entity", ""), "FFFFFF")
            ws.cell(row=row_idx, column=2).fill = PatternFill("solid", start_color=entity_color)

            ws.row_dimensions[row_idx].height = 50

    # Data validation - Setup type
    if data_fixtures:
        last_row = 3 + len(data_fixtures)
        dv_type = DataValidation(
            type="list", formula1='"api,sql,factory"', allow_blank=True
        )
        ws.add_data_validation(dv_type)
        dv_type.add(f"G4:G{last_row}")

    ws.freeze_panes = "B4"
    if data_fixtures:
        ws.auto_filter.ref = f"A3:{get_column_letter(len(DATA_MATRIX_COLUMNS))}{3 + len(data_fixtures)}"

    return ws


# ============ MAIN ============

def create_v9_sheets(wb, data):
    """v9: sheet Coverage Ledger + Effectiveness (mutation) + E2E/UX. Additive — chỉ tạo nếu có key."""
    from openpyxl.styles import Font, PatternFill
    hdr_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    hdr_font = Font(bold=True, color="FFFFFF")

    def _sheet(title, headers, rows):
        ws = wb.create_sheet(title)
        for c, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=c, value=h)
            cell.fill = hdr_fill
            cell.font = hdr_font
        for r, row in enumerate(rows, 2):
            for c, val in enumerate(row, 1):
                ws.cell(row=r, column=c, value=val)
        for c in range(1, len(headers) + 1):
            ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = 28
        return ws

    tcm = data.get("tc_min", {})
    ledger = data.get("coverage_ledger", [])
    if ledger or tcm:
        rows = []
        if tcm:
            rows.append([f"TC_min ENSEMBLE", f"M1={tcm.get('M1','-')}", f"M2(ΣVG)={tcm.get('M2','-')}",
                         f"M3(FP^1.2)={tcm.get('M3','-')}", f"M4={tcm.get('M4','-')} → MAX={tcm.get('max','-')}"])
            rows.append(["", "", "", "", ""])
        for r in ledger:
            rows.append([r.get("cov_id", ""), r.get("technique", ""), r.get("item", ""),
                         r.get("tc", ""), r.get("status", "")])
        _sheet("Coverage Ledger", ["cov_id", "Kỹ thuật", "Coverage item", "TC phủ", "Trạng thái"], rows)

    muts = data.get("mutations", [])
    if muts:
        score = data.get("mutation_score", "manual (0 sống sót)")
        rows = [[m.get("mut_id", ""), m.get("mutation", ""), m.get("killed_by", ""), m.get("status", "")] for m in muts]
        rows.append(["", "", "Mutation score:", str(score)])
        _sheet("Effectiveness", ["mut_id", "Đột biến", "TC giết", "Trạng thái"], rows)

    ux = data.get("ux_findings", [])
    e2e = data.get("e2e", [])
    if ux or e2e:
        rows = [["E2E", j.get("journey", ""), j.get("spec", ""), j.get("status", "")] for j in e2e]
        rows += [["UX/" + u.get("cov_id", ""), u.get("heuristic", ""), u.get("note", ""), str(u.get("severity", ""))] for u in ux]
        _sheet("E2E + UI-UX", ["Loại", "Journey/Heuristic", "Spec/Quan sát", "Trạng thái/Severity"], rows)


def generate_uat_excel(input_json_path, output_xlsx_path):
    """Main entry point."""
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    feature_name = (data.get("feature_name") or data.get("feature") or "Untitled Feature")
    test_cases = data.get("test_cases", [])
    test_data = data.get("test_data", {})
    data_fixtures = data.get("data_fixtures", [])  # MỚI
    scope = data.get("scope", {})

    if not test_cases:
        print("⚠️  Warning: No test cases in input!")
        sys.exit(1)

    wb = Workbook()

    # Sheet: Test Cases (active sheet, becomes index 1 after Summary inserted at 0)
    create_test_cases_sheet(wb, test_cases, feature_name)

    # Sheet: Test Data (legacy - tài khoản, payloads, BVA tĩnh)
    create_test_data_sheet(wb, test_data)

    # Sheet: Data Matrix (MỚI - data fixtures dynamic)
    create_data_matrix_sheet(wb, data_fixtures, test_cases)

    # Sheet: Coverage Ledger + Effectiveness (v9 - chỉ tạo nếu có key)
    create_v9_sheets(wb, data)

    # Sheet: Summary (inserted at index 0 - becomes first sheet)
    create_summary_sheet(wb, test_cases, scope)

    # Sheet: Bug Tracker
    create_bug_tracker_sheet(wb)

    # Sheet: Regression Log
    create_regression_log_sheet(wb)

    # Set Summary as active sheet on open
    wb.active = 0

    wb.save(output_xlsx_path)
    print(f"✅ Đã tạo: {output_xlsx_path}")
    print(f"   - Tổng TC: {len(test_cases)}")
    print(f"   - Data fixtures: {len(data_fixtures)}")
    print(f"   - {len(wb.sheetnames)} sheets: {', '.join(wb.sheetnames)}")
    return output_xlsx_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_uat_excel.py <input.json> <output.xlsx>")
        sys.exit(1)
    generate_uat_excel(sys.argv[1], sys.argv[2])
