# Excel Workflow — Chi tiết đọc/ghi file Excel UAT

## Vị trí file Excel UAT

```
<project-root>/
  test-results/
    UAT/
      uat_<feature>.xlsx   ← nơi lưu trữ mặc định
      uat_login.xlsx
      uat_document_numbers.xlsx
```

`uat-test-writer` xuất vào đây. `uat-test-runner` đọc và ghi vào cùng file.

## Tổng quan workflow

```
┌─────────────────────┐
│  uat-test-writer    │ → test-results/UAT/uat_<feature>.xlsx
└─────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│ uat-test-runner — Lần 1 (initial)                       │
│ GĐ 0. mkdir -p test-results/UAT                         │
│ GĐ 1. $SKILL_SCRIPTS/read_excel_uat.py                  │
│ GĐ 2-6. Generate + Run Playwright (API → E2E)           │
│ GĐ 7a. $SKILL_SCRIPTS/write_results_to_excel.py         │ ← GHI Excel
│        --excel-file test-results/UAT/<f>.xlsx           │
│        --results-file test-results/results.json         │
│ GĐ 7b. $SKILL_SCRIPTS/recalc.py                         │ ← CẬP NHẬT Summary
│        test-results/UAT/<f>.xlsx                        │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────┐
│ Dev fix bug                      │
│ Update Status="Fixed" trong       │
│ Bug Tracker (manual)             │
└──────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────┐
│ uat-test-runner — Retest                                 │
│ GĐ 7a. write_results_to_excel.py --mode retest          │
│ GĐ 7b. recalc.py                                        │
└──────────────────────────────────────────────────────────┘
```

> ⚠️ `$SKILL_SCRIPTS = $HOME/.claude/skills/uat-test-runner/scripts`

## Schema chi tiết

### Sheet "Test Cases" — Column mapping

| Col | Letter | Tên | Loại | Ai ghi |
|-----|--------|-----|------|--------|
| 1 | A | TC-ID | Text | Writer |
| 2 | B | Loại | Enum | Writer |
| 3 | C | Độ ưu tiên | Enum | Writer |
| 4 | D | Module | Text | Writer |
| 5 | E | Tiêu đề | Text | Writer |
| 6 | F | Yêu cầu | Text | Writer |
| 7 | G | Kỹ thuật test | Text | Writer |
| 8 | H | Mức độ rủi ro | Enum | Writer |
| 9 | I | Điều kiện tiên quyết | Multiline | Writer |
| 10 | J | Các bước kiểm thử | Multiline | Writer |
| 11 | K | Dữ liệu kiểm thử | Multiline | Writer |
| 12 | L | Kết quả mong đợi - UI | Multiline | Writer |
| 13 | M | Kết quả mong đợi - API | Multiline | Writer |
| 14 | N | Kết quả mong đợi - Side effects | Multiline | Writer |
| 15 | O | Severity nếu fail | Enum | Writer |
| **16** | **P** | **Kết quả thực tế** | Text | **Runner** |
| **17** | **Q** | **Trạng thái** | Enum (DV) | **Runner** |
| **18** | **R** | **Bug ID** | Text | **Runner** |
| **19** | **S** | **Lần chạy cuối** | Date | **Runner** |
| 20 | T | Ghi chú | Text | Both |

Header ở **row 3**, data từ **row 4** trở đi.

### Sheet "Bug Tracker" — Column mapping

| Col | Letter | Tên | Loại | Ai ghi |
|-----|--------|-----|------|--------|
| 1 | A | Bug ID | Text | Runner (auto-gen) |
| 2 | B | TC ID liên kết | Text | Runner |
| 3 | C | Mô tả bug | Multiline | Runner |
| 4 | D | Severity | Enum (DV) | Runner |
| 5 | E | Status | Enum (DV) | Runner + Dev manual |
| 6 | F | Ngày phát hiện | Date | Runner |
| 7 | G | Lần fix gần nhất | Date | Runner (retest mode) |
| 8 | H | Re-test kết quả | Enum (DV) | Runner (retest) |
| 9 | I | Ghi chú | Text | All |

Header ở **row 3**, data từ **row 4**, có sẵn 50 row trống.

### Status workflow trong Bug Tracker

```
Open → Fixing → Fixed → Verified → Closed
  ↑                       │
  └─────── Reopened ←─────┘ (nếu retest FAIL)
```

Trạng thái khác:
- `Cannot Reproduce` — Dev không tái hiện được
- `Wont Fix` — Quyết định không fix

## Code mẫu — Reader

```python
from openpyxl import load_workbook

wb = load_workbook('uat_feature.xlsx', data_only=True)
ws_tc = wb['Test Cases']

test_cases = []
for row in range(4, ws_tc.max_row + 1):
    tc_id = ws_tc.cell(row=row, column=1).value
    if not tc_id:
        continue

    tc = {
        'tc_id': tc_id,
        'type': ws_tc.cell(row=row, column=2).value,
        'priority': ws_tc.cell(row=row, column=3).value,
        'title': ws_tc.cell(row=row, column=5).value,
        'steps': ws_tc.cell(row=row, column=10).value,
        'test_data': ws_tc.cell(row=row, column=11).value,
        'expected_ui': ws_tc.cell(row=row, column=12).value,
        'expected_api': ws_tc.cell(row=row, column=13).value,
        'severity_if_fail': ws_tc.cell(row=row, column=15).value,
        'current_status': ws_tc.cell(row=row, column=17).value,  # Đã chạy chưa
        'current_bug_id': ws_tc.cell(row=row, column=18).value,
        'row_index': row,  # Lưu để writer ghi đè
    }
    test_cases.append(tc)
```

## Code mẫu — Writer (initial mode)

```python
from openpyxl import load_workbook
from datetime import datetime

wb = load_workbook('uat_feature.xlsx')  # KHÔNG data_only để giữ formula
ws_tc = wb['Test Cases']
ws_bug = wb['Bug Tracker']

now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

for test_result in playwright_results['tests']:
    tc_id = test_result['tc_id']

    # Find TC row
    tc_row = find_tc_row(ws_tc, tc_id)

    # Update Test Cases
    ws_tc.cell(row=tc_row, column=16, value=format_actual_result(test_result))  # P
    ws_tc.cell(row=tc_row, column=17, value=map_status(test_result['status']))  # Q
    ws_tc.cell(row=tc_row, column=19, value=now_str)  # S

    # Nếu fail → tạo bug record
    if test_result['status'] in ('failed', 'timedOut'):
        bug_id = generate_next_bug_id(ws_bug)
        next_bug_row = find_next_empty_bug_row(ws_bug)

        severity = ws_tc.cell(row=tc_row, column=15).value  # Lấy từ cột O

        ws_bug.cell(row=next_bug_row, column=1, value=bug_id)  # Bug ID
        ws_bug.cell(row=next_bug_row, column=2, value=tc_id)  # TC ID
        ws_bug.cell(row=next_bug_row, column=3, value=build_bug_desc(test_result))
        ws_bug.cell(row=next_bug_row, column=4, value=severity)
        ws_bug.cell(row=next_bug_row, column=5, value="Open")
        ws_bug.cell(row=next_bug_row, column=6, value=datetime.now().strftime("%d/%m/%Y"))

        # Link Bug ID về Test Cases cột R
        ws_tc.cell(row=tc_row, column=18, value=bug_id)

wb.save('uat_feature.xlsx')
```

## Code mẫu — Writer (retest mode)

```python
# Retest: TC pass → bug Verified, TC fail → bug Reopened
# KHÔNG tạo bug mới

for test_result in playwright_results['tests']:
    tc_id = test_result['tc_id']

    # Find existing bug
    bug_row = find_bug_by_tc_id(ws_bug, tc_id)
    if not bug_row:
        continue  # Không có bug để retest

    # Update Test Cases (như cũ)
    tc_row = find_tc_row(ws_tc, tc_id)
    ws_tc.cell(row=tc_row, column=17, value=map_status(test_result['status']))
    ws_tc.cell(row=tc_row, column=19, value=now_str)

    if test_result['status'] == 'passed':
        ws_bug.cell(row=bug_row, column=5, value="Verified")  # Status
        ws_bug.cell(row=bug_row, column=8, value="Pass")      # Re-test
        ws_bug.cell(row=bug_row, column=7, value=today_str)   # Last fix
    elif test_result['status'] in ('failed', 'timedOut'):
        ws_bug.cell(row=bug_row, column=5, value="Reopened")
        ws_bug.cell(row=bug_row, column=8, value="Fail")
```

## Edge cases & gotchas

### 1. File đang được mở trong Excel desktop app
→ `PermissionError` khi save. Bắt exception, báo user đóng Excel.

### 2. Sheet không có sẵn
→ Check `if 'Sheet Name' not in wb.sheetnames` trước khi access. Báo lỗi rõ ràng.

### 3. TC không tìm thấy trong sheet
→ Log warning, continue. Có thể TC đã bị xoá hoặc tc_id sai format.

### 4. Bug Tracker đầy 50 row
→ openpyxl tự mở rộng được. Hoặc gợi ý user delete bug Closed cũ.

### 5. Re-test mà không có bug
→ TC pass nhưng không có bug record → có thể là re-test sai TC. Log warning, không tạo gì.

### 6. data_only=True vs False
- **Reader**: `data_only=True` để lấy giá trị formula đã tính (Summary metrics)
- **Writer**: `data_only=False` (default) để **GIỮ formula** — quan trọng!
- Nếu vô tình save với `data_only=True`, formula sẽ bị thay bằng value → mất dynamic dashboard

### 7. Formula bị stale sau khi runner ghi
→ openpyxl không tự recalc. **BẮT BUỘC chạy** `recalc.py` sau mỗi lần save.

### 8. Status "Bị chặn" vs "Bỏ qua"
- **Bị chặn**: Không chạy được do dependency (vd: app không lên)
- **Bỏ qua**: Cố tình skip (vd: tag `test.skip` hoặc `--grep` không match)

## Integration với Playwright reporter

Tạo custom reporter để output `results.json` đúng format:

```typescript
// tests/helpers/excelReporter.ts
import type { Reporter, TestCase, TestResult, FullResult } from '@playwright/test/reporter';
import fs from 'fs';
import path from 'path';

class ExcelJsonReporter implements Reporter {
  private results: any[] = [];
  private startTime = new Date().toISOString();

  onTestEnd(test: TestCase, result: TestResult) {
    // Parse TC-ID từ test title
    const tcMatch = test.title.match(/^(TC-\d+)/);
    const tcId = tcMatch ? tcMatch[1] : '';

    this.results.push({
      tc_id: tcId,
      title: test.title,
      status: result.status,
      duration_ms: result.duration,
      error_message: result.error?.message || '',
      error_stack: result.error?.stack || '',
      screenshot_path: result.attachments
        .find(a => a.name === 'screenshot')?.path || '',
    });
  }

  onEnd(result: FullResult) {
    const output = {
      tests: this.results,
      start_time: this.startTime,
      end_time: new Date().toISOString(),
      total: this.results.length,
      passed: this.results.filter(r => r.status === 'passed').length,
      failed: this.results.filter(r => r.status === 'failed' || r.status === 'timedOut').length,
      skipped: this.results.filter(r => r.status === 'skipped').length,
    };

    const outPath = 'test-results/results.json';
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, JSON.stringify(output, null, 2));
    console.log(`✅ Đã ghi: ${outPath}`);
  }
}

export default ExcelJsonReporter;
```

Đăng ký trong `playwright.config.ts`:
```typescript
export default defineConfig({
  reporter: [
    ['html'],
    ['./tests/helpers/excelReporter.ts'],
  ],
  // ...
});
```

## Naming convention cho TC ID trong test title

Để runner parse được TC ID, mỗi `test()` BẮT BUỘC bắt đầu bằng `TC-XXX:`:

```typescript
// ✅ ĐÚNG
test('TC-001: Đăng nhập thành công với credential hợp lệ', ...);
test('TC-042: SQL Injection trong field email', ...);

// ❌ SAI
test('Login success', ...);  // Không có TC-XXX
test('Test 1', ...);          // Không có TC-XXX
```
