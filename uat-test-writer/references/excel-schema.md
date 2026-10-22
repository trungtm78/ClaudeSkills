# Excel UAT Schema — Cấu trúc file Excel

File `.xlsx` được sinh bởi `uat-test-writer` skill, dùng làm input cho `uat-test-runner` skill. Sau khi runner chạy xong, file được update tại chỗ.

## Cấu trúc tổng thể

```
file_uat.xlsx
├── 📊 Summary       (Sheet 1 - hiển thị đầu tiên khi mở)
├── ✅ Test Cases    (Sheet 2 - chi tiết TC + cột để runner điền)
├── 📦 Test Data     (Sheet 3 - tài khoản, boundary, payloads)
├── 🗂 Data Matrix    (fixtures)
├── 🧾 Coverage Ledger (v9 - nếu input có `coverage_ledger`/`tc_min`)
├── 🧬 Effectiveness  (v9 - nếu input có `mutations`)
├── 🎬 E2E + UI-UX    (v9 - nếu input có `e2e`/`ux_findings`)
├── 🐛 Bug Tracker
└── ♻ Regression Log
```

## (v9) Key input.json mới — OPTIONAL (additive, không có vẫn chạy như cũ)
```jsonc
"tc_min": { "M1":45, "M2":32, "M3":12, "M4":120, "max":120 },   // ENSEMBLE → sheet Coverage Ledger
"coverage_ledger": [ {"cov_id","technique","item","tc","status"} ],
"mutations": [ {"mut_id","mutation","killed_by","status"} ], "mutation_score": "85%",
"e2e": [ {"journey","spec","status"} ],
"ux_findings": [ {"cov_id","heuristic","note","severity"} ]
```
→ Markdown generator render thành section; Excel generator tạo 3 sheet tương ứng. Có key → render, không key → bỏ qua.

## Sheet 1: Summary

**Dashboard auto-tính bằng formula** — KHÔNG được hardcode số.

Bao gồm:
- **TỔNG QUAN** (row 4-9): Tổng TC, Đã thực thi, Đạt, Không đạt, Bị chặn, Chưa chạy
- **Tỷ lệ đạt** & **Tỷ lệ hoàn thành** (row 11-12): formula `COUNTIF` từ sheet Test Cases
- **ĐỘ PHỦ THEO LOẠI** (row 14+): bảng 17 loại × (Số TC, Tỷ lệ, Pass, Fail, Pass rate)
- **THEO ĐỘ ƯU TIÊN** (row sau): P0/P1/P2/P3 × (Số TC, Pass, Fail rate)
- **EXIT CRITERIA**: P0 ≥100%, P1 ≥95%, P2 ≥85%, Bug Critical mở = 0
- **VERDICT cuối cùng** (formula): "🎉 SẴN SÀNG RELEASE" hoặc "⛔ CHƯA SẴN SÀNG RELEASE"

**KHÔNG sửa sheet này thủ công** — formulas tự cập nhật khi Test Cases hoặc Bug Tracker đổi.

## Sheet 2: Test Cases

20 cột, mỗi row là 1 TC:

| # | Cột | Loại | Mô tả |
|---|-----|------|-------|
| A | TC-ID | Text | TC-001, TC-002... |
| B | Loại | Enum | GREEN/RED/EDGE/BOUNDARY/EP/STATE/DECISION/SECURITY/DATA/PERFORMANCE/A11Y/COMPAT/INTEGRATION/REGRESSION/RECOVERY/AUDIT/USABILITY |
| C | Độ ưu tiên | Enum | P0/P1/P2/P3 |
| D | Module | Text | Tên module/feature |
| E | Tiêu đề | Text | Mô tả cụ thể |
| F | Yêu cầu | Text | REQ-XXX |
| G | Kỹ thuật test | Text | BVA/EP/Decision Table/... |
| H | Mức độ rủi ro | Enum | Cao/TB/Thấp |
| I | Điều kiện tiên quyết | Text | Multi-line |
| J | Các bước kiểm thử | Text | Multi-line, đánh số |
| K | Dữ liệu kiểm thử | Text | Literal values |
| L | Kết quả mong đợi - UI | Text | Multi-line |
| M | Kết quả mong đợi - API | Text | Multi-line |
| N | Kết quả mong đợi - Side effects | Text | DB, email, log... |
| O | Severity nếu fail | Enum | Critical/High/Medium/Low |
| **P** | **Kết quả thực tế** | Text | **Runner điền** sau khi chạy |
| **Q** | **Trạng thái** | Enum | **Runner điền**: Chưa chạy/Đang chạy/Đạt/Không đạt/Bị chặn/Bỏ qua |
| **R** | **Bug ID** | Text | **Runner điền** nếu fail (link tới Bug Tracker) |
| **S** | **Lần chạy cuối** | DateTime | **Runner điền** timestamp |
| T | Ghi chú | Text | Free text |

**Cột P, Q, R, S là vùng runner ghi đè. Các cột khác là READ-ONLY cho runner.**

### Conditional formatting cột Q (Trạng thái):
- "Đạt" → xanh lá
- "Không đạt" → đỏ nhạt
- "Bị chặn" → vàng nhạt
- "Bỏ qua" → xám

### Data validation:
- Cột Q chỉ accept giá trị enum
- Khi user nhập tay vào file Excel, dropdown hiện ra

## Sheet 3: Test Data

3 section:

### 3.1. Tài khoản kiểm thử
| ID | Email | Mật khẩu | Vai trò | Trạng thái | Mục đích | Ghi chú |

Cấu trúc dữ liệu giống `accounts` trong JSON input.

### 3.2. Boundary Values (BVA)
| Field | Giá trị | Loại | Kỳ vọng | Ghi chú |

Loại: min-1, min, min+1, max-1, max, max+1.

### 3.3. Security Payloads (OWASP)
| Field/Endpoint | Payload | Loại tấn công | Kỳ vọng | OWASP Reference |

OWASP Ref: A01:2021, A02:2021, ..., A10:2021.

## Sheet 4: Bug Tracker

9 cột, max 50 row (có thể mở rộng):

| # | Cột | Loại | Mô tả |
|---|-----|------|-------|
| A | Bug ID | Text | BUG-001, BUG-002... |
| B | TC ID liên kết | Text | TC-XXX (TC nào trigger bug này) |
| C | Mô tả bug | Text | Chi tiết symptom + reproduction |
| D | Severity | Enum | Critical/High/Medium/Low |
| **E** | **Status** | Enum | **Workflow**: Open → Fixing → Fixed → Verified → Closed |
| F | Ngày phát hiện | Date | DD/MM/YYYY |
| G | Lần fix gần nhất | Date | DD/MM/YYYY (update khi dev fix) |
| H | Re-test kết quả | Enum | Pass/Fail/Pending |
| I | Ghi chú | Text | Free text |

### Status workflow

```
Open ──> Fixing ──> Fixed ──> Verified ──> Closed
  ↑                              │
  └──────── Reopened ←───────────┘ (nếu re-test FAIL)
```

Trạng thái khác:
- `Cannot Reproduce` — Dev không tái hiện được
- `Wont Fix` — Quyết định không fix (out of scope, low priority)

### Conditional formatting cột E (Status):
- Open → đỏ
- Fixing → vàng
- Fixed → xanh dương nhạt
- Verified → xanh lá
- Closed → xám
- Reopened → hồng

## JSON Schema (Input cho generator)

`uat-test-writer` skill sinh JSON này rồi gọi `generate_uat_excel.py`:

```json
{
  "feature_name": "string - tên feature",
  "complexity": "simple|medium|complex",
  "scope": {
    "in_scope": ["..."],
    "out_of_scope": ["..."],
    "exit_criteria": "string"
  },
  "test_cases": [
    {
      "tc_id": "TC-001",
      "type": "GREEN",
      "priority": "P0",
      "module": "string",
      "title": "string",
      "requirement": "REQ-XXX",
      "technique": "string",
      "risk_level": "Cao|TB|Thấp",
      "preconditions": "multi-line string",
      "steps": "multi-line string",
      "test_data": "multi-line string",
      "expected_ui": "multi-line string",
      "expected_api": "multi-line string",
      "expected_side": "multi-line string",
      "severity_if_fail": "Critical|High|Medium|Low",
      "notes": "string"
    }
  ],
  "test_data": {
    "accounts": [
      {
        "id": "U001",
        "email": "...",
        "password": "...",
        "role": "...",
        "status": "...",
        "purpose": "...",
        "notes": "..."
      }
    ],
    "boundary_values": [
      {
        "field": "...",
        "value": "...",
        "type": "min-1|min|min+1|max-1|max|max+1",
        "expected": "PASS|FAIL",
        "notes": "..."
      }
    ],
    "payloads": [
      {
        "target": "...",
        "payload": "...",
        "attack_type": "...",
        "expected": "...",
        "owasp_ref": "A01:2021"
      }
    ]
  }
}
```

## Cách runner đọc file (cho uat-test-runner skill)

```python
from openpyxl import load_workbook

wb = load_workbook('uat_feature.xlsx')
ws_tc = wb['Test Cases']

# Header ở row 3, data từ row 4
header_row = 3
for row in range(4, ws_tc.max_row + 1):
    tc_id = ws_tc.cell(row=row, column=1).value
    tc_type = ws_tc.cell(row=row, column=2).value
    priority = ws_tc.cell(row=row, column=3).value
    title = ws_tc.cell(row=row, column=5).value
    steps = ws_tc.cell(row=row, column=10).value
    test_data = ws_tc.cell(row=row, column=11).value
    # ... parse steps → tạo Playwright code
```

## Cách runner ghi kết quả

```python
from datetime import datetime

# Sau khi chạy xong 1 TC
ws_tc.cell(row=tc_row, column=16, value=actual_result)  # P: Kết quả thực tế
ws_tc.cell(row=tc_row, column=17, value=status)         # Q: Trạng thái
ws_tc.cell(row=tc_row, column=18, value=bug_id or "")   # R: Bug ID
ws_tc.cell(row=tc_row, column=19, value=datetime.now().strftime("%d/%m/%Y %H:%M"))  # S: Lần chạy

# Nếu fail → tạo bug record trong Bug Tracker
ws_bug = wb['Bug Tracker']
next_row = find_next_empty_row(ws_bug, start=4)
ws_bug.cell(row=next_row, column=1, value=f"BUG-{next_row-3:03d}")
ws_bug.cell(row=next_row, column=2, value=tc_id)
ws_bug.cell(row=next_row, column=3, value=bug_description)
ws_bug.cell(row=next_row, column=4, value=severity)
ws_bug.cell(row=next_row, column=5, value="Open")
ws_bug.cell(row=next_row, column=6, value=datetime.now().strftime("%d/%m/%Y"))

wb.save('uat_feature.xlsx')  # Ghi đè file gốc
```

## Re-run workflow

Khi user fix bug và muốn re-test:

1. Runner đọc file Excel
2. Filter Bug Tracker: `Status = "Fixed"` và `Re-test kết quả = "Pending"` hoặc trống
3. Lấy danh sách TC ID từ cột B
4. Chạy lại CHỈ các TC đó
5. Update kết quả:
   - Nếu pass → cập nhật Bug Tracker: Status → "Verified", Re-test → "Pass"
   - Nếu vẫn fail → Status → "Reopened", Re-test → "Fail"
6. Update timestamp "Lần chạy cuối" trong Test Cases
