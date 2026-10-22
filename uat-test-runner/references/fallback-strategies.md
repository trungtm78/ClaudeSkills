# Fallback Strategies — Resolve Blockers without Stopping

## Triết lý

Runner **KHÔNG ĐƯỢC DỪNG** khi gặp blocker. Mọi tình huống đều có fallback. Báo cáo transparency các fallback đã dùng, không che giấu.

## 5 Fallback Categories

### Fallback 1: Credential Resolution — 3 tiers

```
┌──────────────────────────────────────┐
│ Tier 1: UAT file test_data.accounts  │  ← Ưu tiên cao nhất
└──────────────┬───────────────────────┘
               ↓ (nếu không có)
┌──────────────────────────────────────┐
│ Tier 2: .env / .env.test / .env.local │
│ Keys: TEST_USER_EMAIL, TEST_PASSWORD, │
│       ADMIN_EMAIL, ADMIN_PASSWORD     │
└──────────────┬───────────────────────┘
               ↓ (nếu không có)
┌──────────────────────────────────────┐
│ Tier 3: Mock default                  │
│ test@test.com / Test@1234             │
│ admin@test.com / Admin@1234           │
└──────────────────────────────────────┘
```

**Implementation**: `scripts/resolve_credentials.py`

**Usage trong Playwright code**:
```typescript
// tests/fixtures/credentials.ts
import { test as base } from '@playwright/test';

// Load resolved credentials (đã chạy script Python trước khi test)
import credentials from '../../.resolved/credentials.json';

export const test = base.extend<{ creds: typeof credentials }>({
  creds: async ({}, use) => {
    await use(credentials);
  },
});

// Trong spec:
test('TC-001', async ({ page, creds }) => {
  await page.fill('input[name="email"]', creds.email);
  await page.fill('input[name="password"]', creds.password);
});
```

### Fallback 2: URL Resolution — 3 tiers

```
┌──────────────────────────────────────┐
│ Tier 1: ENV BASE_URL / PLAYWRIGHT_BASE_URL │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Tier 2: Parse package.json scripts   │
│ - "dev": "next dev -p 3001" → 3001  │
│ - "start": "vite --port 5173" → 5173 │
│ - Framework defaults (Next 3000,     │
│   Vue 8080, Angular 4200, ...)       │
└──────────────┬───────────────────────┘
               ↓
┌──────────────────────────────────────┐
│ Tier 3: http://localhost:3000        │
└──────────────────────────────────────┘
```

**Implementation**: `scripts/resolve_url.py`

### Fallback 3: App Not Running → KHỞI ĐỘNG APP THẬT; không được → NO-RUN

> ⛔ **NGUYÊN TẮC UAT: KHÔNG BAO GIỜ mock hệ thống đang test.** Test PASS trên mock không nói lên GÌ về app thật — kết quả đó không phải UAT.

Khi URL resolved nhưng port không listen, theo thứ tự:

1. **Khởi động app thật** qua `webServer` trong playwright.config (`npm run dev` / lệnh từ `_platform.json.buildCmds`) — Playwright tự poll URL tới khi sẵn sàng.
2. **Multi-server** (backend + frontend): khởi động tuần tự từng process, poll từng port, `finally` kill cả hai (pattern with_server).
3. Vẫn không lên → **verdict NO-RUN** cho các TC liên quan (lỗi MÔI TRƯỜNG, không phải verdict sản phẩm) + remediation cụ thể trong report (lệnh cần chạy, port, env var thiếu). **Tiếp tục các gate không phụ thuộc app** (vd validate schema, sinh spec).

**Mock policy — CHỈ 3 loại mock được phép trong UAT (qua `page.route`/`routeWebSocket`, per TC, khai báo `backend_policy`):**
| Loại | Ví dụ | Ghi vào report |
|------|-------|----------------|
| `mocked-3p` | payment sandbox, maps, analytics, email/SMS provider | per TC |
| non-deterministic / destructive | endpoint xoá thật, random bên thứ ba | per TC |
| `mocked-error-injection` | ép 500/429/timeout cho RED case khó tái hiện | per TC |

**`generate_mock_server.py` chỉ còn 1 công dụng**: user yêu cầu rõ "dry-run validate spec" → chạy với nhãn `[MOCK MODE — KHÔNG PHẢI KẾT QUẢ UAT]`, không ghi Excel/report chính, không tính GO/NO-GO.

### Fallback 4: Selector Missing → Locator user-facing + reconnaissance

```typescript
// ❌ KHÔNG dùng smart-CSS-array (che giấu testability defect, match nhầm element):
// this.page.locator('[data-testid="email"], input[type="email"], #email').first()

// ✅ Locator user-facing, có fallback CÓ CHỦ ĐÍCH bằng .or():
emailField = this.page.getByLabel(/email/i).or(this.page.getByTestId('email'));
```

Quy trình khi locator fail:
1. **Reconnaissance**: mở page thật → đọc aria snapshot / DOM đã render → rút locator từ cái THẬT SỰ tồn tại (không đoán).
2. Dùng `locator_hint` trong uat.json (writer đã khai) làm gợi ý đầu tiên.
3. Heal ≤2 lần, log diff (locator cũ → mới) vào report.
4. Không có gì ổn định để bám → mark TC = `Bị chặn` + **file TESTABILITY DEFECT** (đề xuất thêm data-testid/testID vào source), **tiếp tục TC khác**.

### Fallback 5: Network/DB Failure → Mark Blocked, Continue

```typescript
// excelReporter.ts logic
onTestEnd(test, result) {
  let status = result.status;
  let actualResult = '';
  
  // Detect blockers vs test failures
  if (result.error?.message.includes('ECONNREFUSED')) {
    status = 'blocked';
    actualResult = '[BLOCKED] Backend connection refused';
  } else if (result.error?.message.includes('Timeout')) {
    status = 'blocked';
    actualResult = '[BLOCKED] Timeout - app slow or unreachable';
  } else if (result.error?.message.includes('Selector failed')) {
    status = 'blocked';  
    actualResult = '[BLOCKED] UI element not found';
  } else if (result.status === 'failed') {
    status = 'failed';
    actualResult = result.error?.message;
  }
  
  this.results.push({ tc_id, status, actualResult });
}
```

**Không abort suite** dù bị blocker — chạy hết tất cả TC còn lại.

## Decision Matrix — Khi nào dùng fallback nào?

| Blocker | Detection | Fallback | Continue? |
|---------|-----------|----------|-----------|
| Missing URL | `process.env.BASE_URL` empty | Tier 2 → Tier 3 | ✅ |
| Missing credential | UAT no accounts + no .env | Tier 3 mock | ✅ |
| App not running | `socket connect_ex != 0` | Mock server | ✅ (báo MOCK MODE) |
| Selector missing | `.count() == 0` | Smart locator → TC blocked | ✅ |
| DB connection refused | `ECONNREFUSED` | Mark blocked | ✅ |
| Network timeout | `Timeout 30s` | Mark blocked | ✅ |
| 5xx server error | Status 500+ | Treat as TC fail (expected for security TC) | ✅ |
| Playwright not installed | `check-env.sh fail` | Auto install | ✅ |
| Out of memory | OOM kill | **DỪNG** (system) | ❌ |
| Disk full | `ENOSPC` | **DỪNG** (system) | ❌ |

## Pipeline tự động — không ngắt giữa

Skill chạy 6 giai đoạn liên tục:

```bash
# 1. Read UAT
python scripts/read_excel_uat.py uat.xlsx > /tmp/uat_data.json

# 2. Install (nếu cần)
bash scripts/check-env.sh || bash scripts/install-playwright.sh

# 3. Resolve blockers (Bước 4 trong SKILL.md)
python scripts/resolve_credentials.py --uat-data /tmp/uat_data.json -o tests/.resolved/credentials.json
python scripts/resolve_url.py -o /tmp/url_info.json

# 4. App chưa chạy → khởi động app THẬT (webServer / buildCmds); không lên được → NO-RUN
URL_INFO=$(cat /tmp/url_info.json)
if echo "$URL_INFO" | grep -q '"app_running": false'; then
  export START_DEV=1        # playwright.config webServer sẽ tự start + poll
  # Nếu vẫn không lên sau timeout → verdict NO-RUN + remediation, KHÔNG mock thay app
fi

# 5. CHẠY
npx playwright test --reporter=json --output=test-results/

# 6. Ghi kết quả
python scripts/write_results_to_excel.py \
  --excel-file uat.xlsx \
  --results-file test-results/results.json

python $SKILL_SCRIPTS/recalc.py uat.xlsx
```

KHÔNG hỏi user giữa các bước. KHÔNG có break point. Chỉ output cuối cùng.

## Transparency reporting

Report cuối CÓ BẮT BUỘC ghi tất cả fallbacks đã dùng:

```markdown
## Fallback Report
- 🔑 Credential: Tier 1 (UAT file) — alice@test.com
- 🌐 URL: Tier 2 (parsed package.json) — http://localhost:3001
- 🚀 App: tự khởi động qua webServer (npm run dev) — sẵn sàng sau 18s
- 🎭 Backend policy: live; 2 TC mocked-3p (TC-030 payment sandbox, TC-031 email), 1 TC error-injection (TC-041 ép 500)
- 🎯 Locator heal: 3 TC (TC-005, TC-012, TC-018) — chuyển sang getByLabel; diff trong report
- ⏹️ NO-RUN: 1 TC (TC-024) — DB connection refused (environment, không tính defect)
```

User PHẢI biết test chạy trên app thật hay có mock biên nào, credential thật hay mock — để đánh giá độ tin cậy kết quả.

## Anti-pattern — Tuyệt đối tránh

### ❌ Anti-pattern 1: Stop and ask
```
Claude: "Tôi cần URL của app để chạy test. Bạn cung cấp được không?"
```
→ **SAI**: phải dùng fallback chain ngay, không hỏi.

### ❌ Anti-pattern 2: Generate code rồi dừng
```
Claude: "Đã sinh xong 25 spec files. Bạn chạy lệnh `npx playwright test` để test nhé."
```
→ **SAI**: phải tự chạy `npx playwright test` luôn.

### ❌ Anti-pattern 3: Skip vì thiếu credential
```
Claude: "Vì không có credential test, tôi sẽ skip các TC require login."
```
→ **SAI**: dùng mock credential, chạy hết.

### ❌ Anti-pattern 4: Mock thay app để "vẫn có kết quả"
```
Claude: "App không chạy nên tôi đã dựng mock server và test PASS 100%."
```
→ **SAI**: PASS trên mock không phải kết quả UAT. Đúng: tự khởi động app thật; không được → NO-RUN + remediation.

### ❌ Anti-pattern 5: Provide commands instead of running
```
Claude: "Chạy lệnh sau: `npx playwright test --headed`"
```
→ **SAI**: tự execute, return kết quả.

## Quick reference — Pseudo-code execution flow

```python
def run_uat_skill(uat_source):
    # KHÔNG hỏi user gì cả
    uat_data = read_json_or_md(uat_source)      # INPUT = .json/.md — KHÔNG Excel
    validate_handoff_schema(uat_data)           # thiếu field ✱ → báo lỗi từng TC
    platform = load_or_detect_platform()        # Gate 0
    ensure_tools(platform)                      # Playwright / Maestro+Java17 / adb

    creds = resolve_credentials(uat_data)       # fallback 1
    url_info = resolve_url(platform)            # fallback 2 (+10.0.2.2 cho emulator)

    if not url_info['app_running']:
        started = start_real_app(platform)      # fallback 3: webServer/buildCmds
        if not started:
            return report_no_run(remediation)   # NO-RUN ≠ NO-GO; KHÔNG mock thay app

    generate_seed_spec()                        # style exemplar trước
    generate_specs_and_flows(uat_data, platform)  # web spec + maestro flows theo platform TC

    results = run_gates_foreground(platform)    # Gate 1 → 2/2b → 3
    triage_failures(results)                    # 4 nhãn; heal locator ≤2; KHÔNG sửa assertion
    diff_baseline(results)                      # regression → severity +1

    write_results_to_excel_if_exists(results)   # Excel = OUTPUT optional
    return generate_report(results, gates_g0_g7, verdict)   # người ký sign-off
```

KHÔNG có code branch `if ask_user(): ...`. KHÔNG có `if has_credential else stop`.
