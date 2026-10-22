#!/usr/bin/env python3
"""
write_results_to_excel.py — Ghi kết quả Playwright vào file Excel UAT + DETECT REGRESSION.

Usage:
    # Lần chạy đầu (initial)
    python write_results_to_excel.py \
        --excel-file uat_feature.xlsx \
        --results-file test-results/results.json

    # Retest sau khi fix bug — chế độ này TỰ DETECT regression
    python write_results_to_excel.py \
        --excel-file uat_feature.xlsx \
        --results-file test-results/results.json \
        --mode retest

Logic regression detection:
- So sánh trạng thái MỚI với LẦN CHẠY GẦN NHẤT (từ cột Lịch sử chạy).
- Nếu TC từng "Đạt" mà giờ "Không đạt" → REGRESSION!
- Auto-tạo record REG-XXX trong sheet Regression Log với severity ESCALATE +1 level.
- Đánh dấu cờ "⚠️ REGRESSION" vào cột U của Test Cases.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook


# ============ STATUS MAPPING ============
STATUS_MAP = {
    "passed": "Đạt",
    "failed": "Không đạt",
    "skipped": "Bỏ qua",
    "timedOut": "Không đạt",
    "interrupted": "Bị chặn",
    "blocked": "Bị chặn",
}

# ============ COLUMN INDEXES (Test Cases sheet, 1-based) ============
# FALLBACK constants — khớp generate_uat_excel.py hiện tại (24+ cột, header row 3).
# LƯU Ý lịch sử: bản cũ dùng 15..22 (thiếu cột 12 "Data fixtures cần") → ghi lệch 1 cột.
# Từ bản này, resolve_tc_columns() đọc HEADER THẬT ở row 3 làm nguồn chân lý;
# constants dưới chỉ dùng khi header không khớp (Excel do tay người sửa).
COL_TC_ID = 1
COL_TYPE = 2
COL_PRIORITY = 3
COL_MODULE = 4
COL_TITLE = 5
COL_REQUIREMENT = 6
COL_SEVERITY_IF_FAIL = 16
COL_ACTUAL_RESULT = 17    # Q — Kết quả thực tế
COL_STATUS_API = 18       # R — Trạng thái API (Layer 1)
COL_STATUS_E2E = 19       # S — Trạng thái E2E (Layer 2)
COL_BUG_ID = 20           # T
COL_LAST_RUN = 21         # U
COL_RUN_HISTORY = 22      # V — lịch sử R1:API/E2E|R2:...
COL_REGRESSION_FLAG = 23  # W — ⚠️ REGRESSION
# Backward compat alias (cũ dùng COL_STATUS, mặc định map sang E2E vì E2E là final layer)
COL_STATUS = COL_STATUS_E2E
COL_NOTES = 24            # X

HEADER_ROW = 3
# header text (lowercase, strip) → tên biến global cần override
_HEADER_TO_CONST = {
    "tc-id": "COL_TC_ID",
    "loại": "COL_TYPE",
    "độ ưu tiên": "COL_PRIORITY",
    "module": "COL_MODULE",
    "tiêu đề": "COL_TITLE",
    "yêu cầu": "COL_REQUIREMENT",
    "severity nếu fail": "COL_SEVERITY_IF_FAIL",
    "kết quả thực tế": "COL_ACTUAL_RESULT",
    "trạng thái api": "COL_STATUS_API",
    "trạng thái e2e": "COL_STATUS_E2E",
    "bug id": "COL_BUG_ID",
    "lần chạy cuối": "COL_LAST_RUN",
    "lịch sử chạy": "COL_RUN_HISTORY",
    "cờ regression": "COL_REGRESSION_FLAG",
    "ghi chú": "COL_NOTES",
}


def resolve_tc_columns(ws_tc):
    """
    Đọc header row 3 của sheet Test Cases, override các COL_* global theo tên cột thật.
    Chống lệch cột khi schema Excel thay đổi giữa các version generator.
    """
    global COL_STATUS
    found = 0
    for col in range(1, ws_tc.max_column + 1):
        val = ws_tc.cell(row=HEADER_ROW, column=col).value
        if not val:
            continue
        key = str(val).strip().lower()
        const_name = _HEADER_TO_CONST.get(key)
        if const_name:
            globals()[const_name] = col
            found += 1
    COL_STATUS = COL_STATUS_E2E  # giữ alias đồng bộ sau override
    if found < 5:
        print(
            f"⚠️  Chỉ nhận diện được {found} header — dùng fallback constants "
            "(kiểm tra Excel có đúng schema uat-test-writer không)",
            file=sys.stderr,
        )
    return found

# Bug Tracker columns
BUG_COL_ID = 1
BUG_COL_TC_ID = 2
BUG_COL_DESCRIPTION = 3
BUG_COL_SEVERITY = 4
BUG_COL_STATUS = 5
BUG_COL_DISCOVERED = 6
BUG_COL_LAST_FIX = 7
BUG_COL_RETEST = 8
BUG_COL_NOTES = 9

# Regression Log columns
REG_COL_ID = 1
REG_COL_TC_ID = 2
REG_COL_MODULE = 3
REG_COL_DISCOVERED = 4
REG_COL_TRIGGER_BUG = 5      # BUG-XXX nào trigger ra regression này
REG_COL_PREV_STATUS = 6
REG_COL_NEW_STATUS = 7
REG_COL_SEV_ORIG = 8
REG_COL_SEV_REGRESSION = 9   # Severity gốc +1 level
REG_COL_DESCRIPTION = 10
REG_COL_FIXED = 11
REG_COL_VERIFY_DATE = 12
REG_COL_NOTES = 13

# Severity escalation ladder
SEVERITY_LADDER = ["Low", "Medium", "High", "Critical"]


def escalate_severity(severity):
    """Escalate severity +1 level. Critical đã max thì giữ nguyên."""
    if not severity:
        return "Medium"  # Default escalation
    sev_clean = str(severity).strip()
    try:
        idx = SEVERITY_LADDER.index(sev_clean)
        return SEVERITY_LADDER[min(idx + 1, len(SEVERITY_LADDER) - 1)]
    except ValueError:
        return "High"  # Unknown severity → escalate to High


# ============ FINDERS ============

def find_tc_row(ws, tc_id):
    """Tìm row index của TC trong sheet Test Cases (data từ row 4)."""
    for row in range(4, ws.max_row + 1):
        cell_value = ws.cell(row=row, column=COL_TC_ID).value
        if cell_value and str(cell_value).strip() == tc_id:
            return row
    return None


def find_existing_bug_row(ws, tc_id):
    """Tìm bug record đã có cho TC này."""
    for row in range(4, ws.max_row + 1):
        existing_tc = ws.cell(row=row, column=BUG_COL_TC_ID).value
        if existing_tc and str(existing_tc).strip() == tc_id:
            return row
    return None


def find_next_bug_row(ws):
    """Tìm row trống đầu tiên trong Bug Tracker."""
    for row in range(4, ws.max_row + 2):
        if not ws.cell(row=row, column=BUG_COL_ID).value:
            return row
    return ws.max_row + 1


def find_next_regression_row(ws):
    """Tìm row trống đầu tiên trong Regression Log."""
    for row in range(4, ws.max_row + 2):
        if not ws.cell(row=row, column=REG_COL_ID).value:
            return row
    return ws.max_row + 1


def get_next_bug_id(ws):
    """Sinh Bug ID tiếp theo BUG-XXX."""
    max_num = 0
    for row in range(4, ws.max_row + 1):
        bug_id = ws.cell(row=row, column=BUG_COL_ID).value
        if bug_id and isinstance(bug_id, str) and bug_id.startswith("BUG-"):
            try:
                num = int(bug_id.split("-")[1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
    return f"BUG-{max_num + 1:03d}"


def get_next_regression_id(ws):
    """Sinh Regression ID REG-XXX."""
    max_num = 0
    for row in range(4, ws.max_row + 1):
        reg_id = ws.cell(row=row, column=REG_COL_ID).value
        if reg_id and isinstance(reg_id, str) and reg_id.startswith("REG-"):
            try:
                num = int(reg_id.split("-")[1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass
    return f"REG-{max_num + 1:03d}"


# ============ HISTORY MANAGEMENT ============

def parse_run_history(history_str):
    """Parse 'R1:Đạt|R2:Không đạt|R3:Đạt' → list ['Đạt', 'Không đạt', 'Đạt']."""
    if not history_str:
        return []
    runs = []
    for item in str(history_str).split("|"):
        item = item.strip()
        if ":" in item:
            _, status = item.split(":", 1)
            runs.append(status.strip())
        elif item:
            runs.append(item)
    return runs


def append_to_history(current_history, new_status):
    """Append status mới vào history string."""
    runs = parse_run_history(current_history)
    runs.append(new_status)
    # Giữ tối đa 10 lần chạy gần nhất
    runs = runs[-10:]
    return "|".join(f"R{i+1}:{s}" for i, s in enumerate(runs))


def detect_regression(history_runs, new_status):
    """
    Detect regression: TC từng "Đạt" mà giờ "Không đạt".
    Trả về True nếu là regression.
    """
    if new_status not in ("Không đạt",):
        return False

    # Kiểm tra có lần Đạt nào trước đây không
    for past_status in history_runs:
        if past_status == "Đạt":
            return True
    return False


# ============ TEXT BUILDERS ============

def build_actual_result_text(test_result):
    """Format cột Kết quả thực tế."""
    status = test_result.get("status", "")

    if status == "passed":
        return f"Đạt như expected. Thời gian: {test_result.get('duration_ms', 0)}ms"

    if status in ("failed", "timedOut"):
        parts = []
        err = test_result.get("error_message", "").strip()
        if err:
            parts.append(f"Lỗi: {err[:300]}")
        if test_result.get("screenshot_path"):
            parts.append(f"Screenshot: {test_result['screenshot_path']}")
        if test_result.get("duration_ms"):
            parts.append(f"Thời gian: {test_result['duration_ms']}ms")
        return " | ".join(parts) if parts else "Không đạt - xem HTML report"

    if status == "skipped":
        return "Test đã bị skip"

    return f"Status: {status}"


def build_bug_description(test_result, layer=""):
    """Format Mô tả bug. Include layer (api/e2e) if specified."""
    parts = []
    layer_prefix = f"[{layer.upper()}] " if layer else ""
    parts.append(f"{layer_prefix}Test fail: {test_result.get('title', test_result.get('tc_id', ''))}")
    err = test_result.get("error_message", "").strip()
    if err:
        parts.append(f"Error: {err[:500]}")
    if test_result.get("screenshot_path"):
        parts.append(f"Screenshot: {test_result['screenshot_path']}")
    if test_result.get("video_path"):
        parts.append(f"Video: {test_result['video_path']}")
    if test_result.get("trace_path"):
        parts.append(f"Trace: {test_result['trace_path']}")
    return "\n".join(parts)


def build_regression_description(test_result, prev_status, history_runs, trigger_bug_ids):
    """Format Mô tả regression."""
    parts = []
    parts.append(f"⚠️ REGRESSION: TC từng {prev_status} giờ Không đạt sau khi fix bug khác.")
    if trigger_bug_ids:
        parts.append(f"Có thể do fix các bug: {', '.join(trigger_bug_ids)}")
    err = test_result.get("error_message", "").strip()
    if err:
        parts.append(f"Error mới: {err[:300]}")
    parts.append(f"Lịch sử: {' → '.join(history_runs[-5:])} → Không đạt")
    return "\n".join(parts)


# ============ MAIN UPDATE LOGIC ============

def write_test_cases_results(wb, results, mode="initial"):
    """
    Update sheet Test Cases với kết quả mới.
    Trả về:
        - update_count
        - fail_results: list TC fail (để tạo bug)
        - regression_results: list TC bị regression (để tạo REG record)
    """
    ws_tc = wb["Test Cases"]
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    update_count = 0
    fail_results = []
    regression_results = []

    for test_result in results.get("tests", []):
        tc_id = test_result.get("tc_id", "").strip()
        if not tc_id:
            continue

        tc_row = find_tc_row(ws_tc, tc_id)
        if not tc_row:
            print(f"⚠️  Không tìm thấy {tc_id} trong sheet Test Cases", file=sys.stderr)
            continue

        # Lấy status mới
        new_status_vi = STATUS_MAP.get(test_result.get("status"), test_result.get("status", ""))

        # Detect layer: từ test_result.layer (do reporter set), hoặc fallback từ spec file path
        layer = test_result.get("layer", "").lower()
        if not layer:
            file_path = test_result.get("file", "").lower()
            if ".e2e." in file_path or "/e2e/" in file_path:
                layer = "e2e"
            elif ".api." in file_path or "/api/" in file_path:
                layer = "api"
            else:
                layer = "e2e"  # default

        # Determine which column to update
        if layer == "api":
            target_col = COL_STATUS_API
        else:
            target_col = COL_STATUS_E2E

        # === REGRESSION DETECTION (chỉ check trên E2E layer — final user-facing) ===
        is_regression = False
        prev_status = ""
        if layer == "e2e":
            old_history = ws_tc.cell(row=tc_row, column=COL_RUN_HISTORY).value
            history_runs = parse_run_history(old_history)
            is_regression = detect_regression(history_runs, new_status_vi)
            prev_status = history_runs[-1] if history_runs else (
                ws_tc.cell(row=tc_row, column=COL_STATUS_E2E).value or ""
            )

        # === UPDATE Test Cases ===
        # Append layer info vào actual_result (đỡ ghi đè khi cả 2 layer chạy)
        prefix = "[API]" if layer == "api" else "[E2E]"
        new_actual = f"{prefix} {build_actual_result_text(test_result)}"
        existing_actual = ws_tc.cell(row=tc_row, column=COL_ACTUAL_RESULT).value or ""
        if existing_actual and prefix not in existing_actual:
            combined = f"{existing_actual}\n{new_actual}"
        else:
            combined = new_actual
        ws_tc.cell(row=tc_row, column=COL_ACTUAL_RESULT, value=combined)

        # Update status cột tương ứng
        ws_tc.cell(row=tc_row, column=target_col, value=new_status_vi)
        ws_tc.cell(row=tc_row, column=COL_LAST_RUN, value=now_str)

        # Update history chỉ khi layer=e2e (history track final result của user-facing)
        if layer == "e2e":
            old_history = ws_tc.cell(row=tc_row, column=COL_RUN_HISTORY).value
            new_history = append_to_history(old_history, new_status_vi)
            ws_tc.cell(row=tc_row, column=COL_RUN_HISTORY, value=new_history)

            # Set regression flag
            existing_flag = ws_tc.cell(row=tc_row, column=COL_REGRESSION_FLAG).value
            if is_regression:
                ws_tc.cell(row=tc_row, column=COL_REGRESSION_FLAG, value="⚠️ REGRESSION")
            elif new_status_vi == "Đạt" and existing_flag == "⚠️ REGRESSION":
                ws_tc.cell(row=tc_row, column=COL_REGRESSION_FLAG, value="✓ Đã fix")

        update_count += 1

        # Lưu thông tin TC fail để tạo bug
        if test_result.get("status") in ("failed", "timedOut"):
            severity = ws_tc.cell(row=tc_row, column=COL_SEVERITY_IF_FAIL).value or "Medium"
            module = ws_tc.cell(row=tc_row, column=COL_MODULE).value or ""
            requirement = ws_tc.cell(row=tc_row, column=COL_REQUIREMENT).value or ""

            fail_info = {
                "test_result": test_result,
                "tc_row": tc_row,
                "tc_id": tc_id,
                "severity": severity,
                "module": module,
                "requirement": requirement,
                "layer": layer,
                "is_regression": is_regression,
                "prev_status": prev_status,
                "history": parse_run_history(
                    ws_tc.cell(row=tc_row, column=COL_RUN_HISTORY).value
                ),
            }
            fail_results.append(fail_info)

            if is_regression:
                regression_results.append(fail_info)

    return update_count, fail_results, regression_results


def write_bugs_initial_mode(wb, fail_results):
    """Mode initial: tạo bug record mới (KHÔNG xử lý regression riêng vì lần đầu chưa có history)."""
    ws_bug = wb["Bug Tracker"]
    ws_tc = wb["Test Cases"]
    today_str = datetime.now().strftime("%d/%m/%Y")
    bugs_created = []

    for fail_info in fail_results:
        existing_row = find_existing_bug_row(ws_bug, fail_info["tc_id"])

        if existing_row:
            # Update existing
            ws_bug.cell(row=existing_row, column=BUG_COL_STATUS, value="Open")
            ws_bug.cell(row=existing_row, column=BUG_COL_DISCOVERED, value=today_str)
            bug_id = ws_bug.cell(row=existing_row, column=BUG_COL_ID).value
        else:
            new_row = find_next_bug_row(ws_bug)
            bug_id = get_next_bug_id(ws_bug)

            ws_bug.cell(row=new_row, column=BUG_COL_ID, value=bug_id)
            ws_bug.cell(row=new_row, column=BUG_COL_TC_ID, value=fail_info["tc_id"])
            ws_bug.cell(row=new_row, column=BUG_COL_DESCRIPTION, value=build_bug_description(fail_info["test_result"], layer=fail_info.get("layer", "")))
            ws_bug.cell(row=new_row, column=BUG_COL_SEVERITY, value=fail_info["severity"])
            ws_bug.cell(row=new_row, column=BUG_COL_STATUS, value="Open")
            ws_bug.cell(row=new_row, column=BUG_COL_DISCOVERED, value=today_str)

        # Link Bug ID
        ws_tc.cell(row=fail_info["tc_row"], column=COL_BUG_ID, value=bug_id)

        bugs_created.append({
            "bug_id": bug_id,
            "tc_id": fail_info["tc_id"],
            "severity": fail_info["severity"],
        })

    return bugs_created


def write_regression_records(wb, regression_results, trigger_bug_ids):
    """Tạo record trong sheet Regression Log cho mỗi TC bị regression."""
    if "Regression Log" not in wb.sheetnames:
        print("⚠️  Sheet 'Regression Log' không tồn tại. Bỏ qua bước này.", file=sys.stderr)
        return []

    ws_reg = wb["Regression Log"]
    today_str = datetime.now().strftime("%d/%m/%Y")
    reg_records = []

    for reg_info in regression_results:
        # Check xem TC này đã có record regression đang mở chưa
        existing_reg_row = None
        for row in range(4, ws_reg.max_row + 1):
            tc_in_reg = ws_reg.cell(row=row, column=REG_COL_TC_ID).value
            fixed_status = ws_reg.cell(row=row, column=REG_COL_FIXED).value
            if (tc_in_reg and str(tc_in_reg).strip() == reg_info["tc_id"]
                and fixed_status != "Yes"):
                existing_reg_row = row
                break

        if existing_reg_row:
            # Đã có regression mở cho TC này, không tạo mới
            continue

        new_row = find_next_regression_row(ws_reg)
        reg_id = get_next_regression_id(ws_reg)
        escalated_sev = escalate_severity(reg_info["severity"])

        ws_reg.cell(row=new_row, column=REG_COL_ID, value=reg_id)
        ws_reg.cell(row=new_row, column=REG_COL_TC_ID, value=reg_info["tc_id"])
        ws_reg.cell(row=new_row, column=REG_COL_MODULE, value=reg_info["module"])
        ws_reg.cell(row=new_row, column=REG_COL_DISCOVERED, value=today_str)
        ws_reg.cell(row=new_row, column=REG_COL_TRIGGER_BUG, value=", ".join(trigger_bug_ids))
        ws_reg.cell(row=new_row, column=REG_COL_PREV_STATUS, value=reg_info["prev_status"])
        ws_reg.cell(row=new_row, column=REG_COL_NEW_STATUS, value="Không đạt")
        ws_reg.cell(row=new_row, column=REG_COL_SEV_ORIG, value=reg_info["severity"])
        ws_reg.cell(row=new_row, column=REG_COL_SEV_REGRESSION, value=escalated_sev)
        ws_reg.cell(row=new_row, column=REG_COL_DESCRIPTION, value=build_regression_description(
            reg_info["test_result"], reg_info["prev_status"], reg_info["history"], trigger_bug_ids
        ))
        ws_reg.cell(row=new_row, column=REG_COL_FIXED, value="No")

        reg_records.append({
            "reg_id": reg_id,
            "tc_id": reg_info["tc_id"],
            "severity_orig": reg_info["severity"],
            "severity_escalated": escalated_sev,
        })

    return reg_records


def write_bugs_retest_mode(wb, results):
    """Mode retest: update bug Status Verified/Reopened, KHÔNG tạo bug mới."""
    ws_bug = wb["Bug Tracker"]
    today_str = datetime.now().strftime("%d/%m/%Y")
    updates = {"verified": [], "reopened": []}

    results_by_tc = {t.get("tc_id"): t for t in results.get("tests", [])}

    for tc_id, test_result in results_by_tc.items():
        bug_row = find_existing_bug_row(ws_bug, tc_id)
        if not bug_row:
            continue

        bug_id = ws_bug.cell(row=bug_row, column=BUG_COL_ID).value

        if test_result.get("status") == "passed":
            ws_bug.cell(row=bug_row, column=BUG_COL_STATUS, value="Verified")
            ws_bug.cell(row=bug_row, column=BUG_COL_RETEST, value="Pass")
            ws_bug.cell(row=bug_row, column=BUG_COL_LAST_FIX, value=today_str)
            updates["verified"].append({"bug_id": bug_id, "tc_id": tc_id})
        elif test_result.get("status") in ("failed", "timedOut"):
            ws_bug.cell(row=bug_row, column=BUG_COL_STATUS, value="Reopened")
            ws_bug.cell(row=bug_row, column=BUG_COL_RETEST, value="Fail")
            updates["reopened"].append({"bug_id": bug_id, "tc_id": tc_id})

    return updates


def get_recently_fixed_bug_ids(wb):
    """Lấy danh sách Bug ID có Status='Fixed' (để truy vết nguyên nhân regression)."""
    if "Bug Tracker" not in wb.sheetnames:
        return []
    ws_bug = wb["Bug Tracker"]
    fixed_bugs = []
    for row in range(4, ws_bug.max_row + 1):
        status = ws_bug.cell(row=row, column=BUG_COL_STATUS).value
        bug_id = ws_bug.cell(row=row, column=BUG_COL_ID).value
        if status in ("Fixed", "Verified") and bug_id:
            fixed_bugs.append(str(bug_id))
    return fixed_bugs


# ============ MAIN ============

def main():
    parser = argparse.ArgumentParser(description="Ghi kết quả Playwright vào Excel UAT + Detect regression")
    parser.add_argument("--excel-file", required=True)
    parser.add_argument("--results-file", required=True)
    parser.add_argument("--mode", choices=["initial", "retest"], default="initial")
    args = parser.parse_args()

    excel_path = Path(args.excel_file)
    results_path = Path(args.results_file)

    if not excel_path.exists():
        print(f"❌ File Excel không tồn tại: {excel_path}", file=sys.stderr)
        sys.exit(1)
    if not results_path.exists():
        print(f"❌ File results không tồn tại: {results_path}", file=sys.stderr)
        sys.exit(1)

    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    try:
        wb = load_workbook(excel_path)
    except PermissionError:
        print(f"❌ File đang bị mở trong Excel. Đóng rồi thử lại.", file=sys.stderr)
        sys.exit(3)

    if "Test Cases" not in wb.sheetnames or "Bug Tracker" not in wb.sheetnames:
        print(f"❌ File phải có sheet 'Test Cases' và 'Bug Tracker'", file=sys.stderr)
        sys.exit(2)

    # === Step 0: Resolve cột theo HEADER THẬT (chống off-by-one giữa các version) ===
    resolve_tc_columns(wb["Test Cases"])

    # === Step 1: Update Test Cases + detect regression ===
    print(f"📝 Đang update Test Cases (mode={args.mode})...", file=sys.stderr)
    update_count, fail_results, regression_results = write_test_cases_results(wb, results, mode=args.mode)
    print(f"   Updated {update_count} TC rows", file=sys.stderr)

    # === Step 2: Process bugs/regression theo mode ===
    if args.mode == "retest":
        print(f"🔄 Retest mode: cập nhật bug status...", file=sys.stderr)
        bug_updates = write_bugs_retest_mode(wb, results)
        print(f"   ✅ Verified: {len(bug_updates['verified'])}", file=sys.stderr)
        print(f"   ❌ Reopened: {len(bug_updates['reopened'])}", file=sys.stderr)

        # === REGRESSION HANDLING (chỉ trong retest mode) ===
        if regression_results:
            # Lấy danh sách bug đã fix gần đây để truy vết nguyên nhân
            recently_fixed = get_recently_fixed_bug_ids(wb)
            print(f"\n🚨 PHÁT HIỆN REGRESSION: {len(regression_results)} TC", file=sys.stderr)
            reg_records = write_regression_records(wb, regression_results, recently_fixed)

            for r in reg_records:
                print(f"   {r['reg_id']} ← {r['tc_id']} ({r['severity_orig']} → {r['severity_escalated']})", file=sys.stderr)

            print(f"\n⛔ BLOCK RELEASE — Xem sheet 'Regression Log' để xử lý!", file=sys.stderr)
    else:
        print(f"🆕 Initial mode: tạo bug record mới...", file=sys.stderr)
        bugs_created = write_bugs_initial_mode(wb, fail_results)
        print(f"   Created {len(bugs_created)} bug records:", file=sys.stderr)
        for b in bugs_created:
            print(f"     {b['bug_id']} ← {b['tc_id']} ({b['severity']})", file=sys.stderr)

    # === Step 3: Save ===
    try:
        wb.save(excel_path)
    except PermissionError:
        print(f"❌ Không ghi được - file đang mở. Đóng rồi thử lại.", file=sys.stderr)
        sys.exit(3)

    print(f"\n✅ Đã ghi đè: {excel_path}", file=sys.stderr)
    print(f"   ⚠️  Chạy recalc.py để cập nhật Summary:", file=sys.stderr)
    print(f"   python $SKILL_SCRIPTS/recalc.py {excel_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
