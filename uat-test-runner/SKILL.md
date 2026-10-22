---
name: uat-test-runner
description: Thực thi UAT đa platform theo GATE ORCHESTRATOR - API smoke gate (Playwright request, chạy trước) rồi Web E2E (Playwright Chromium) và/hoặc Mobile E2E (Maestro cho Flutter/React Native/native Android-iOS/hybrid — tự nhận diện từ _platform.json hoặc codebase). Input PRIMARY là .md/.json do uat-test-writer sinh (docs/uat/<feature>/) theo handoff-schema. Excel chỉ để GHI KẾT QUẢ, không phải input. Full evidence + GO/NO-GO 8 gate, 4 verdict (GO/CONDITIONAL GO/NO-GO/NO-RUN). KHÔNG dùng để ký nghiệm thu — việc ấy thuộc `uat-test-only`. Dùng khi user yêu cầu "test rồi fix luôn", "execute test", "automate test", "Playwright test", "Maestro test", "E2E test", "UI test", "verify bug fix", "retest", "chạy lại test đã lỗi". Thiếu tool thì tự cài. Comments tiếng Việt, keyword kỹ thuật tiếng Anh.
---

# uat-test-runner — Gate Orchestrator v5 (web + mobile)

> **Skill này dành cho VÒNG DEV, không dành cho ký duyệt.** Nó được phép sửa mã, heal
> locator, tạo bug và chạy lại — đúng việc của nó. Nhưng chính vì thế, kết quả của nó
> **không dùng để ký nghiệm thu**: người tìm ra lỗi mà cũng là người sửa thì không còn ai ở
> ngoài để nói nó vẫn sai.
>
> Cần một lượt để **ký** → dùng `uat-test-only` (không sửa gì, có rào đo được, có chứng âm).
> Bảng phân vai và bảng cổng chuẩn: `references/handoff-schema.md` §7–§8.
>
> Lưu ý ký hiệu: **G1 ở đây là "API smoke 100% pass"**, khác với G1 của `uat-test-only`
> ("mọi lớp có ca đều chạy được"). Các cổng còn lại G0·G2–G7 trùng nghĩa.

Skill thực thi UAT theo **chuỗi gate fail-fast, đa driver**:

```
Gate 0  ENV/DETECT   → đọc docs/uat/_platform.json (writer sinh) hoặc tự detect
                       (references/platform-detection.md của uat-test-writer);
                       kiểm tool/device/app; fail ⇒ NO-RUN (lỗi môi trường ≠ verdict sản phẩm)
Gate 1  API SMOKE    → Playwright request (platform-agnostic); fail ⇒ SKIP mọi gate sau
Gate 2  WEB E2E      → Playwright Chromium (label WEB)
Gate 2b HYBRID WEB   → Playwright trên dev server/webDir (label HYBRID_WEBVIEW)
Gate 3  MOBILE E2E   → Maestro YAML flows (label ANDROID/IOS/FLUTTER/RN) — references/mobile-runner.md
Gate 3b NATIVE DEEP  → Patrol (Flutter) / Detox (RN) — CHỈ khi Gate 3 không diễn đạt được AC
Gate 4  REPORT       → GO/NO-GO per-platform; 4 trạng thái TC: PASS / FAIL / SKIPPED / NOT_EXECUTED
```

- Nguyên tắc: **Intent above, determinism below** — AI (MCP) chỉ dùng khi authoring/debug; gate chính thức chạy CODE/YAML đã persist, reproducible.
- **Layer sau SKIP nếu gate trước của cùng TC fail**. Excel có cột status riêng per layer.
- **EU-first**: E2E thao tác đúng như End User (qua UI, locator user-facing), không đi tắt API.

## ⛔ NGHIÊM CẤM

### Forbidden phrases

| ❌ KHÔNG nói | ✅ THAY BẰNG |
|-------------|---------------|
| "Tôi cần thêm thông tin trước khi chạy" | Áp dụng fallback chain → chạy |
| "Bạn muốn tôi chạy không?" | Chạy luôn, báo cáo sau |
| "Bạn muốn chạy mode nào?" | Default headless, chạy luôn |
| "Đã sinh code, bạn run nhé" | Đã sinh = chạy ngay |
| "Vui lòng cung cấp credential" | Dùng fallback + báo trong report |
| "App chưa chạy nên không test được" | Tự khởi động app thật (webServer/server-lifecycle); không được → verdict **NO-RUN** kèm remediation |
| "Tôi chỉ sinh code thôi" | KHÔNG được — phải chạy |
| "Cần config thêm trước" | Generate config mặc định → chạy |

### Forbidden actions

1. ❌ Dừng sau khi sinh code mà chưa chạy
2. ❌ Hỏi user mode chạy → default headless
3. ❌ **Dùng `run_in_background: true` cho lệnh Playwright/Maestro** — PHẢI chạy foreground để user thấy tiến độ live
4. ❌ Sinh chỉ 1 layer — PHẢI sinh API spec + E2E spec (web) / Maestro flows (mobile) theo platform của TC
5. ❌ E2E test gọi API trực tiếp (`request.post(...)`) — phải qua UI như End User
6. ❌ Skip evidence capture (trace/screenshot/video/recording)
7. ❌ Run Firefox/WebKit khi user không nói rõ → Chromium only
8. ❌ Bỏ qua API layer vì "feature chỉ có UI" — vẫn cần smoke
9. ❌ Bỏ qua E2E vì "API đủ rồi" — phải verify end-to-end
10. ❌ **Sinh code tất cả TC một lần** → PHẢI batch 25 TC, write file, tiếp tục
11. ❌ **Dừng pipeline khi Playwright exit code != 0** → thêm `true` sau lệnh playwright
12. ❌ **Báo cáo "xong" khi số TC chạy < số TC trong .md/.json** → phải verify count match
13. ❌ **Dùng Excel làm input để thực thi test** → Excel CHỈ nhận kết quả sau khi chạy xong
14. ❌ **MOCK HỆ THỐNG ĐANG TEST** — app không chạy = NO-RUN, KHÔNG dựng mock server giả UAT. Mock chỉ 3 loại được phép: 3rd-party ngoài kiểm soát / endpoint non-deterministic-destructive / error-injection cho RED case — ghi `backend_policy` per TC vào report
15. ❌ **AUTO-SỬA ASSERTION khi test fail** — assertion fail = bug thật hoặc data đổi → escalate người. Auto-heal CHỈ cho locator-resolution failure (timeout/not-found), ≤2 lần, có log diff
16. ❌ **Selector CSS chain/XPath/nth-child** trong spec mới → locator user-facing: `getByRole` → `getByLabel` → `getByText` → `getByTestId`
17. ❌ **`waitForTimeout` / `waitForLoadState('networkidle')` / `if (await isVisible())`** → web-first assertions (`await expect(...).toBeVisible()`)
18. ❌ **Tính pass-on-retry là PASS trong sign-off run** → sign-off: retries 0 + failOnFlakyTests; pass-on-retry = AMBER/flaky, báo cáo riêng
19. ❌ **Blanket GO khi có platform NOT_EXECUTED** — GO chỉ tính trên platform đã chạy; platform bị chặn (vd iOS trên Windows) = residual risk ghi rõ + remediation

20. ❌ **Kết luận từ một lượt chạy CÓ CACHE.** `turbo`/`nx` băm TỆP NGUỒN và không nhìn thấy
    cơ sở dữ liệu. Một migration ở gói khác đổi hành vi mà gói này không đổi dòng nào → cache
    phát lại một lượt xanh **có từ trước migration ấy**. Lượt chạy dùng để kết luận UAT phải
    tắt cache và **báo cáo phải in ra `0 cached`**:
    ```
    TURBO_FORCE=1 pnpm test:ci        # rồi grep "Cached:" trong output, phải là 0
    ```
    Đo thật `Lumina_Approve` 03·08·2026: cổng báo *23/23 successful, 20 cached* trong khi
    **hai ca đang đỏ trên chính cây đã commit**. Lượt chạy đầu tiên không cache trong ngày
    là lượt tìm ra chúng.
21. ❌ **Ghi PASS cho một mệnh đề mà ca kiểm nằm ở TẦNG THẤP HƠN mệnh đề.** Khi thu kết quả,
    mỗi dòng ledger phải ghi kèm **tầng của bằng chứng** (`E2E` / `API` / `unit`). Mệnh đề
    có chủ ngữ là **người dùng** mà bằng chứng là `unit` → ghi **`NOT_EXECUTED (layer)`**,
    không ghi PASS. Đây là dạng trượt duy nhất mà mọi tầng đều xanh trong khi tính năng
    không dùng được — xem trụ 5 "layer parity" ở `uat-test-writer`.
22. ❌ **Kết thúc lượt chạy mà chưa thử VÒNG LẶP HIỆN VẬT.** Với mỗi thứ sản phẩm PHÁT RA cho
    người dùng — mã khôi phục, mã một lần, khoá thủ công QR, link tải, mã mời — phải có đúng
    một ca lấy **chính chuỗi ấy** gửi ngược vào cửa nó mở. Không có ca ấy thì hiện vật chưa
    được kiểm, dù mọi thứ sinh ra nó đều xanh.

### Chỉ 3 case được dừng

1. User explicit "chỉ sinh code, không chạy"
2. Test PASS hết → dừng tự nhiên
3. System error: OOM, disk full

### ⛔ NGHIÊM CẤM DỪNG VÌ

- Context window dài → chia batch, viết file ngay, tiếp tục
- Test fail → Playwright vẫn chạy hết, không abort toàn suite
- Sinh code quá nhiều → batch 25 TC/lần, ghi file sau mỗi batch
- Bất kỳ lý do "không chắc" nào → tiếp tục với fallback, ghi kết quả sau

## Đường dẫn chuẩn (KHÔNG THAY ĐỔI)

```bash
# Skill scripts — resolve theo môi trường, dùng $SKILL_SCRIPTS trong MỌI lệnh python
if [ -d "/mnt/skills/user/uat-test-runner/scripts" ]; then
  SKILL_SCRIPTS="/mnt/skills/user/uat-test-runner/scripts"      # claude.ai
elif [ -d "$HOME/.claude/skills/uat-test-runner/scripts" ]; then
  SKILL_SCRIPTS="$HOME/.claude/skills/uat-test-runner/scripts"  # Claude Code (Linux/macOS)
else
  SKILL_SCRIPTS="$USERPROFILE/.claude/skills/uat-test-runner/scripts"  # Windows
fi

# UAT source files (PRIMARY INPUT)
UAT_MD_DIR="<project-root>/docs/uat"
# Ví dụ: docs/uat/cases/uat_cases.md  hoặc  docs/uat/cases/uat.json

# Excel results output (OPTIONAL — chỉ để ghi kết quả, không phải input)
UAT_EXCEL_DIR="<project-root>/test-results/UAT"
# Ví dụ: test-results/UAT/uat_quan_ly_cases.xlsx
```

> ⚠️ **Windows**: dùng `$USERPROFILE/.claude/skills/uat-test-runner/scripts` nếu bash không resolve `$HOME`.

## Architecture — Gate Orchestrator Pipeline

```
[Gate 0 ENV/DETECT]       docs/uat/_platform.json (writer sinh; thiếu → detect_platform.py)
                          + validate handoff schema (đủ field ✱, đếm TC khớp)
                          + tool check (Playwright / Maestro+Java17 / adb / device)
                          + app THẬT chạy được?  ──Không──→ verdict NO-RUN (+remediation), DỪNG
        ↓
[Read UAT .md / .json]    docs/uat/<feature>/uat.json (ưu tiên) / uat_<feature>.md  ← PRIMARY INPUT
        ↓
[Generate theo platform]  tests/api/<f>.api.spec.ts                 ← mọi TC có API
                          tests/e2e/<f>.e2e.spec.ts                 ← TC platform=web|hybrid (fixtures+POM)
                          .maestro/<f>/TC-xxx.yaml                  ← TC platform=android|ios
                          tests/uat.seed.spec.ts                    ← seed test (style exemplar + env init)
        ↓
[Gate 1 API smoke]        npx playwright test --project=api-smoke   ──fail──→ SKIP các gate sau (per TC/toàn cục)
        ↓
[Gate 2/2b Web E2E]       npx playwright test --project=e2e-chromium
[Gate 3 Mobile E2E]       maestro test .maestro/<f> --format JUNIT  (Android trước; iOS nếu chạy được)
        ↓
[Gate 4 Thu kết quả]      flatten (Playwright JSON + Maestro JUnit) → results_flat.json
                          + crash oracle logcat (mobile)
                          + [OPTIONAL] write_results_to_excel.py (CHỈ NẾU Excel tồn tại)
                          + [⛔ BẮT BUỘC] extract_failed_tcs.py → failed-tc-ids.txt
                          + baseline diff (regression) + GO/NO-GO 8 gate
        ↓
[Output Report]           4 trạng thái TC: PASS / FAIL / SKIPPED / NOT_EXECUTED (blocked)
```

> ⚠️ **INPUT RULE**: Excel KHÔNG BAO GIỜ là input để thực thi test. Chỉ dùng `.md` / `.json`. Excel chỉ nhận kết quả sau khi test xong.
> ⚠️ **Schema validate trước khi sinh** (references/handoff-schema.md của uat-test-writer): thiếu field bắt buộc / oracle_source trống / TC mồ côi coverage → báo lỗi từng TC, không lặng lẽ bỏ.

## 2 Evidence Profile (chọn theo `evidence_profile` trong uat.json; default `signoff`)

| | Profile CI (chạy lặp thường ngày) | Profile SIGN-OFF (nghiệm thu) |
|---|---|---|
| trace | `on-first-retry` | `on` (evidence cả khi PASS — governance cần) |
| screenshot | `only-on-failure` | `on` |
| video | `retain-on-failure` | `on` |
| retries | 2 (kèm `retryStrategy: 'isolated'` nếu Playwright ≥1.62) | **0** |
| failOnFlakyTests | false | **true** — pass-nhờ-retry không phải pass nghiệm thu |
| Mobile (Maestro) | screenshot khi fail (--debug-output) | `startRecording` + `takeScreenshot` tại mỗi Given/When/Then |

> Version-detect Playwright (`npx playwright --version`) và degrade tính năng theo version (test.abort ≥1.60, screencast ≥1.59, --last-failed ≥1.44...). Ghi version vào report header.

## ⚠️ Quy ước ngôn ngữ

- Comments code, `test('...')`: tiếng Việt
- Keyword Playwright, hàm/biến: tiếng Anh
- Console output, report: tiếng Việt
- File names: `<feature>.api.spec.ts`, `<feature>.e2e.spec.ts`

## Naming convention

| Loại | File | Title |
|------|------|-------|
| API smoke | `tests/api/*.api.spec.ts` | `TC-XXX-API: ...` |
| UI E2E | `tests/e2e/*.e2e.spec.ts` | `TC-XXX-E2E: ...` |

## Execution Pipeline — 7 giai đoạn

### GĐ 0: Thiết lập đường dẫn (BẮT BUỘC đầu tiên)

```bash
# Xác định skill scripts directory
SKILL_SCRIPTS="$HOME/.claude/skills/uat-test-runner/scripts"
# Windows fallback: $USERPROFILE/.claude/skills/uat-test-runner/scripts

# Tạo thư mục output nếu chưa có
mkdir -p test-results/UAT

# === PRIMARY: Tìm .md hoặc .json (input để thực thi test) ===
FEATURE="cases"  # thay bằng feature cụ thể

UAT_JSON="docs/uat/$FEATURE/uat.json"
UAT_MD="docs/uat/$FEATURE/uat_${FEATURE}.md"

if [ -f "$UAT_JSON" ]; then
  echo "Input: $UAT_JSON (JSON)"
elif [ -f "$UAT_MD" ]; then
  echo "Input: $UAT_MD (Markdown)"
else
  echo "ERROR: Không tìm thấy docs/uat/$FEATURE/uat.json hoặc uat_$FEATURE.md"
  exit 1
fi

# === OPTIONAL: Excel để ghi kết quả (không phải input) ===
EXCEL_FILE=$(find test-results/UAT -name "uat_*$FEATURE*.xlsx" 2>/dev/null | head -1)
if [ -n "$EXCEL_FILE" ]; then
  echo "Excel found (kết quả sẽ được ghi vào): $EXCEL_FILE"
else
  echo "Excel không tìm thấy — kết quả chỉ ghi vào test-results/$FEATURE-run/results_flat.json"
fi
```

### GĐ 1: Đọc UAT file (.json hoặc .md)

```bash
# Ưu tiên .json (parse nhanh hơn)
if [ -f "$UAT_JSON" ]; then
  cp "$UAT_JSON" /tmp/uat_data.json
  echo "Loaded from JSON: $(python -c "import json; d=json.load(open('/tmp/uat_data.json')); print(len(d['test_cases']), 'TC')")"
else
  # Fallback: parse .md → JSON
  python "$SKILL_SCRIPTS/parse-test-cases.py" "$UAT_MD" > /tmp/uat_data.json
  echo "Parsed from Markdown"
fi
```

### GĐ 2: Install Playwright nếu thiếu (không hỏi)

```bash
bash "$SKILL_SCRIPTS/check-env.sh" || bash "$SKILL_SCRIPTS/install-playwright.sh"
```

### GĐ 3: Sinh CẢ 2 spec layers — BATCH MODE (BẮT BUỘC)

> ⚠️ **BATCH RULE**: Mỗi batch tối đa **25 TC**. Viết file ngay sau mỗi batch. KHÔNG sinh toàn bộ 100+ TC một lần.

#### Protocol sinh batch:

```
Batch 1: TC-001 → TC-025  → Write tests/api/<f>.api.spec.ts (append)
                           → Write tests/e2e/<f>.e2e.spec.ts (append)
                           → Confirm: "Đã sinh batch 1/N (TC-001~TC-025)"
Batch 2: TC-026 → TC-050  → Append vào 2 file trên
                           → Confirm: "Đã sinh batch 2/N"
...
Batch N: TC-076 → TC-100  → Append
                           → Confirm: "Đã sinh batch N/N — HOÀN TẤT code generation"
```

> ⛔ **KHÔNG ĐƯỢC DỪNG** giữa các batch dù context dài. Nếu cần, dùng smaller batch (15 TC).

**`tests/uat.seed.spec.ts`** — SINH ĐẦU TIÊN (style exemplar):
- 1 test duy nhất: env init + auth (storageState) + demo phong cách fixture/locator/step chuẩn
- Mọi spec sinh sau PHẢI bắt chước phong cách seed test này (đòn bẩy chất lượng số 1 — pattern Playwright Test Agents)

**`tests/api/<feature>.api.spec.ts`** — Gate 1:
- Dùng `request.post/get/...` của Playwright (APIRequestContext)
- Verify status code + response body theo oracle (KHÔNG chỉ status)
- KHÔNG mở browser; mỗi TC ≥ 2 assertion

**`tests/e2e/<feature>.e2e.spec.ts`** — Gate 2 (web):
- **Fixture-composition**: page objects inject qua fixtures (`fixtures/index.ts`, `mergeTests`), KHÔNG `new LoginPage(page)` trong test
- **Locator ưu tiên**: `getByRole` → `getByLabel` → `getByText` → `getByTestId` → CSS cuối cùng; CẤM XPath/nth-child/CSS chain
- **`test.step()` map 1:1 bước TC** — title = "TC-xx.N — <expected của bước>"; `expect.soft()` cho cụm assertion trong step, `expect()` cứng cho precondition chặn
- 100% UI interaction — KHÔNG `request.*` trong E2E; **assertion phải verify qua DOM**, không gọi API để xác nhận
- Mỗi TC PHẢI ≥ 3 UI assertion (URL + visibility + text/value)
- Tag từ handoff schema: `{ tag: ['@TC-012', '@P0', '@S2', '@journey-approve'] }` → --grep filter được
- **Assertion expected value phải trace về dòng trong uat.json** — không tự chế giá trị; 1 TC nguồn = đúng 1 `test()` (chống test explosion)
- A11y: thêm `@axe-core/playwright` scan per page-state cho TC A11Y + `toMatchAriaSnapshot` cho structural regression
- Xem `references/ui-e2e-patterns.md`

**`.maestro/<feature>/TC-xxx.yaml`** — Gate 3 (mobile) → quy tắc sinh flow: `references/mobile-runner.md`

**`playwright.config.ts`** — chuẩn mới (chi tiết: `references/playwright-config.md`):
- Projects chain: `api-smoke` → `setup` (login 1 lần/role, lưu storageState) → `e2e-chromium` (dependencies: ['setup'], dùng storageState) → `cleanup` (teardown: true — LUÔN chạy kể cả fail)
- Chromium only default; evidence theo profile (bảng 2 Evidence Profile ở trên)
- KHÔNG `bypassCSP`/`ignoreHTTPSErrors` mặc định (UAT phải giống production; chỉ bật khi user xác nhận dev env kèm ghi chú report)
- `captureGitInfo: { commit: true }` (≥1.51) — report gắn build SHA

#### Sau khi sinh xong TẤT CẢ batch:
```bash
# Kiểm tra số TC đã sinh khớp với .json/.md source (KHÔNG dùng Excel)
TC_IN_SOURCE=$(python -c "import json; d=json.load(open('/tmp/uat_data.json')); print(len(d['test_cases']))")
TC_IN_API=$(grep -c "^  test(" tests/api/*.api.spec.ts 2>/dev/null || echo 0)
TC_IN_E2E=$(grep -c "^  test(" tests/e2e/*.e2e.spec.ts 2>/dev/null || echo 0)
echo "📊 TC count — Source: $TC_IN_SOURCE | API spec: $TC_IN_API | E2E spec: $TC_IN_E2E"
```
> Nếu số không khớp → sinh thêm batch cho phần còn thiếu. KHÔNG chạy Playwright khi chưa đủ TC.

### GĐ 3.5: Sinh Data Factory — CÓ ĐIỀU KIỆN

Chỉ khi `uat.json` có `data_fixtures`. Chi tiết: `references/data-factory-stage.md`.

### GĐ 4: Resolve blockers (fallback chain — không hỏi user)

#### 4.1 Credential (3-tier)
```
Tier 1: UAT test_data.accounts (legacy)
Tier 1.5: Data Matrix fixture (NEW - ưu tiên cao nhất nếu TC có data_required)
Tier 2: .env / .env.test
Tier 3: Mock test@test.com / Test@1234
```
→ `python "$SKILL_SCRIPTS/resolve_credentials.py"`

#### 4.2 URL (3-tier)
```
Tier 1: ENV BASE_URL
Tier 2: Parse package.json scripts
Tier 3: localhost:3000
```
→ `python "$SKILL_SCRIPTS/resolve_url.py"`

#### 4.3 App not running → KHỞI ĐỘNG APP THẬT, không mock
1. Thử `webServer` trong playwright.config (`npm run dev` / lệnh từ `_platform.json.buildCmds`) — poll port tới khi sẵn sàng.
2. Multi-server (backend + frontend): khởi động tuần tự, poll từng port (pattern with_server: start → poll → chạy test → finally kill).
3. Vẫn không lên được → **verdict NO-RUN** cho các TC liên quan (lỗi môi trường ≠ verdict sản phẩm) + remediation cụ thể (lệnh cần chạy, port, env thiếu). KHÔNG dựng mock server thay app.
4. `generate_mock_server.py` CHỈ dùng khi user yêu cầu rõ "dry-run validate spec" — output gắn nhãn `[MOCK MODE — KHÔNG PHẢI KẾT QUẢ UAT]`, không ghi vào Excel/report chính.

#### 4.4 Selector missing → Locator user-facing + testability defect
- Ưu tiên sửa bằng `getByRole/getByLabel/getByText` từ những gì THẬT SỰ render (reconnaissance: mở page, đọc aria snapshot/DOM rồi mới viết locator — không đoán).
- `locator_hint` trong uat.json là gợi ý đầu tiên.
- Không có gì ổn định để bám → ghi **TESTABILITY DEFECT** (đề xuất thêm data-testid/testID) thay vì CSS chain mong manh.

#### 4.5 Network/DB fail → mark blocked (NO-RUN cho TC đó), continue

### GĐ 5: CHẠY API smoke (Layer 1) — FOREGROUND, live output

> ⚠️ **CHẠY FOREGROUND (không background)** — user cần nhìn thấy tiến độ. KHÔNG dùng `run_in_background`.

```bash
# --reporter=line: hiển thị từng test PASS/FAIL live trên terminal
# --reporter=json: đồng thời ghi kết quả JSON để GĐ 7 dùng
# PLAYWRIGHT_JSON_OUTPUT_NAME: ghi JSON ra file riêng, không lẫn với stdout line reporter
PLAYWRIGHT_JSON_OUTPUT_NAME="test-results/$FEATURE-run/api-results.json" \
npx playwright test tests/api/$FEATURE-uat.api.spec.ts \
  --project=api \
  --reporter=line,json \
  --workers=4
# Exit code != 0 bình thường nếu có TC fail — pipeline tiếp tục
echo "API exit=$?"
```

**Live output user thấy:**
```
  ✓ TC-CASE-001-API [P0] Tạo vụ án DIRECT_DISCOVERY hợp lệ (1.2s)
  ✓ TC-CASE-002-API [P0] Tạo vụ án FROM_PETITION (0.8s)
  ✗ TC-CASE-017-API [P0] Thiếu caseProvenance → 400 (0.5s)
  47 passed, 69 skipped, 0 failed (83s)
```

### GĐ 6: CHẠY E2E (Layer 2) — FOREGROUND, Chromium

> ⚠️ **CHẠY FOREGROUND** — user theo dõi tiến độ, biết E2E đang test màn hình nào.

```bash
PLAYWRIGHT_JSON_OUTPUT_NAME="test-results/$FEATURE-run/e2e-results.json" \
npx playwright test tests/e2e/$FEATURE-uat.e2e.spec.ts \
  --project=e2e-chromium \
  --reporter=line,json \
  --workers=2
echo "E2E exit=$?"
```

E2E chạy độc lập, không dùng `dependencies: ['api']` (tránh skip toàn suite khi API project lỗi).

> ⚠️ Sau GĐ 5 và GĐ 6: kiểm tra tổng số test CHẠY khớp với source TC count. Nếu thiếu → debug spec, KHÔNG báo cáo xong.

### GĐ 7: Lưu kết quả + Cập nhật Excel (nếu có) ⛔ extract_failed_tcs NGHIÊM CẤM BỎ QUA

```bash
# 7a: Flatten results → results_flat.json (LUÔN chạy)
# Mobile: thêm --maestro-junit test-results/mobile/report.xml nếu có Gate 3
python "$SKILL_SCRIPTS/flatten_pw_results.py" \
  "test-results/$FEATURE-run/api-results.json" \
  "test-results/$FEATURE-run/e2e-results.json" \
  "test-results/$FEATURE-run/results_flat.json"

# 7b: Cập nhật Excel NẾU file đã tồn tại (OPTIONAL)
if [ -n "$EXCEL_FILE" ] && [ -f "$EXCEL_FILE" ]; then
  python "$SKILL_SCRIPTS/write_results_to_excel.py" \
    --excel-file "$EXCEL_FILE" \
    --results-file "test-results/$FEATURE-run/results_flat.json"
  python "$SKILL_SCRIPTS/recalc.py" "$EXCEL_FILE"
  echo "✅ Excel updated: $EXCEL_FILE"
else
  echo "ℹ️  Không có Excel → kết quả lưu tại test-results/$FEATURE-run/results_flat.json"
fi

# 7c: Xuất danh sách TC fail ⛔ BẮT BUỘC — để Retest Mode dùng
# --uat-json cung cấp module map (KHÔNG dùng Excel làm input)
python "$SKILL_SCRIPTS/extract_failed_tcs.py" \
  "test-results/$FEATURE-run/results_flat.json" \
  --uat-json "$UAT_JSON" \
  --output "test-results/failed-tc-ids.txt"

echo "📋 TC fail: $(cat test-results/failed-tc-ids.txt 2>/dev/null | wc -l) cases → test-results/failed-tc-ids.txt"
```

> ⚠️ **Bắt buộc**: flatten + extract_failed_tcs PHẢI chạy sau mỗi lần test.
> **Optional**: write_results_to_excel chỉ chạy khi `$EXCEL_FILE` tồn tại — không cần tạo Excel mới.

Logic:
- Cột "Trạng thái API" (R): Từ test có suffix `-API` hoặc file `*.api.spec.ts`
- Cột "Trạng thái E2E" (S): Từ test có suffix `-E2E` / `*.e2e.spec.ts` / Maestro JUnit (mobile)
- Vị trí cột được resolve THEO TÊN HEADER (row 3) — không hardcode chữ cái cột
- Bug tracker tự tạo bug với prefix `[API]` / `[E2E]` / `[MOBILE]` trong description
- **Baseline store**: sau run xanh, copy `results_flat.json` → `test-results/baseline/results_baseline.json` (theo tc_id). Run sau diff với baseline → TC từng PASS nay FAIL = **REGRESSION** → severity +1 level (Medium→High, High→Critical) vì chứng minh thay đổi làm hỏng hành vi đang chạy; TC đó nếu đã sign-off → **thu hồi sign-off, yêu cầu re-approve**.

---

## Triage & Self-healing CÓ KỶ LUẬT (chạy trước khi báo cáo bug)

> **Mỗi lần heal phải ghi sổ**, nếu không thì một lượt xanh sau heal không giải thích được —
> người đọc không phân biệt nổi "sản phẩm đúng" với "thước đã chỉnh cho vừa sản phẩm".
>
> ```bash
> python "$SKILL_SCRIPTS/heal_log.py" reset            # đầu mỗi lượt
> python "$SKILL_SCRIPTS/heal_log.py" add --tc TC-012 >    --what "đổi locator sang getByRole" --why "nút đổi aria-label sau refactor"
> ```
>
> `--why` là **nguyên nhân thật**; "cho test xanh" bị script từ chối. `heal > 0` thì verdict
> không bao giờ là `GO` trần. Đây là bản đối xứng của `guard_repo.py` bên `uat-test-only`:
> bên kia cấm sửa và chứng minh không sửa; bên này cho sửa và bắt khai đã sửa gì.

Mỗi test FAIL phải được PHÂN LOẠI trước khi làm bất cứ gì (thu thập: error message, trace qua `npx playwright trace` CLI nếu ≥1.59, console/pageErrors/requests, logcat với mobile):

| Nhãn | Dấu hiệu | Hành động |
|------|----------|-----------|
| **product bug** | assertion fail, hành vi ≠ oracle | Tạo bug + evidence; KHÔNG đụng test |
| **locator drift** | timeout/element-not-found, UI đổi cấu trúc | Auto-heal ≤2 lần (locator mới từ DOM thật) + log diff; quá 2 lần → escalate |
| **environment** | ECONNREFUSED, 5xx toàn cục, device offline | verdict NO-RUN cho TC đó, không tính defect sản phẩm |
| **flaky** | pass/fail không ổn định cùng code | Quarantine (dưới) |

Quy tắc cứng:
- **KHÔNG BAO GIỜ auto-sửa assertion/expected** — chỉ heal locator. "Sửa assertion cho khớp app" = che giấu regression.
- Timing fail → sửa bằng web-first assertion/wait-for-state, KHÔNG nới timeout mù, KHÔNG thêm sleep. (Cẩn trọng: heal selector mà thêm delay có thể che perf regression — flag nghi vấn.)
- Mọi heal có: diff, phân loại, confidence — vào report.

**Quarantine flaky**: tag `@flaky` + chạy suite với `--grep-invert @flaky`; báo cáo MỤC RIÊNG (không phải PASS/FAIL — là coverage chưa verify = risk item); mỗi TC quarantine có owner + deadline **14 ngày fix-or-delete**. KPI: flaky <1%, quarantine <5% suite.

## GO/NO-GO — 8 gate + 4 verdict

> **CỔNG DO MÁY TÍNH, KHÔNG TỰ ĐIỀN.** Bảng dưới là *định nghĩa*, không phải chỗ để điền tay.
>
> ```bash
> python "$SKILL_SCRIPTS/build_runner_report.py" >   --results test-results/UAT/results_flat.json --uat "$UAT_JSON" --url /tmp/url.json >   --a11y test-results/UAT/a11y.json --perf test-results/UAT/perf.json >   --heal test-results/UAT/heal_log.json --s2-budget <ngưỡng NGƯỜI đặt> >   --baseline <lượt XANH người chỉ định> --signoff <hồ sơ ký> -o test-results/UAT
> ```
>
> Rồi **dán nguyên** `test-results/UAT/runner-verdict.txt` vào báo cáo.
>
> Hai trục, không phải một thang:
> `verdict = min( thang bậc theo cổng HỎNG , TRẦN theo cổng KHÔNG ĐO ĐƯỢC )`.
> `CONDITIONAL GO` chỉ dành cho **nợ đã biết** (S2 trong ngân sách, đã heal). Cổng **chưa đo
> được** thì hạ trần và in `KHUYẾT PHÉP ĐO:` — không đo được không bao giờ bằng đạt.
>
> `G1` ở đây là **API smoke**, khác nghĩa `G1` của `uat-test-only` — xem
> `references/handoff-schema.md` §7.

| Gate | Điều kiện | Fail → |
|------|-----------|--------|
| G0 Entry | env reachable, build SHA ghi nhận, seed data ok, credentials ok, app thật chạy | **NO-RUN** (không phải NO-GO) |
| G1 API smoke | 100% TC smoke pass | NO-GO, UI/mobile skip |
| G2 Critical path | 100% TC P0/S1-S2 pass, 0 flake trong nhóm này | NO-GO |
| G3 Coverage | ≥95% TC kế hoạch đã EXECUTE (quarantine + NOT_EXECUTED tính là CHƯA execute) | CONDITIONAL GO |
| G4 Defect budget | 0 S1 mở; S2 ≤ thoả thuận có workaround văn bản | CONDITIONAL GO |
| G5 Regression | 0 regression vs baseline xanh gần nhất | NO-GO |
| G6 Non-functional | axe critical = 0 (per page-state), perf budget đạt (nếu có TC PERFORMANCE) | CONDITIONAL GO |
| G7 Sign-off record | named approver + evidence links + timestamp đủ | NO-GO (thủ tục) |

**Verdict:** `GO` (mọi gate xanh) · `CONDITIONAL GO` (gate NO-GO đều xanh; gate mềm fail có **waiver**: named approver + risk acceptance + remediation date) · `NO-GO` · `NO-RUN` (lỗi môi trường — không phải verdict sản phẩm).
- **GO/NO-GO chỉ tính trên platform ĐÃ execute** — platform NOT_EXECUTED (vd iOS trên Windows) liệt kê là residual risk + remediation (workflow macos CI/cloud device farm), KHÔNG bao giờ blanket GO.
- Skill ĐỀ XUẤT verdict + evidence package; **người có thẩm quyền ký** — AI không tự approve.

---


## Phần đã tách sang `references/` (nạp khi cần)

- `references/retest-mode.md` — Retest Mode — chạy lại chỉ TC lỗi
- `references/excel-workflow-extra.md` — Excel hai cột status dual-layer
- `references/report-template.md` — Mẫu báo cáo kết quả thực thi
- `references/browser-and-mobile.md` — Chọn trình duyệt · viewport emulation vs app thật
- `references/troubleshooting-extra.md` — Lỗi thường gặp khi chạy

## Scripts

`build_runner_report.py` (tính cổng + verdict) · `heal_log.py` (sổ heal) — hai tệp này là chỗ ra quyết định; đừng tự điền tay.

Tất cả scripts ở `$HOME/.claude/skills/uat-test-runner/scripts/` (dùng `$SKILL_SCRIPTS` variable từ GĐ 0):

- `flatten_pw_results.py` — ⭐ Gộp Playwright JSON (+ Maestro JUnit `--maestro-junit`) → `results_flat.json` (BẮT BUỘC sau mỗi run — GĐ 7a / RT-5)
- `check-env.sh` — Check Node/Playwright
- `install-playwright.sh` — Cài Playwright + Chromium
- `detect_platform.py` — ⭐ Detect platform multi-label → `docs/uat/_platform.json` (Gate 0; cùng logic `platform-detection.md` của writer)
- `generate_maestro_flows.py` — ⭐ Sinh `.maestro/<feature>/TC-xxx.yaml` từ uat.json (TC platform=android|ios)
- `parse-test-cases.py` — Parse Markdown TC → JSON
- `read_excel_uat.py` — Đọc Excel UAT → JSON (gồm data_fixtures)
- `resolve_credentials.py` — Credential fallback
- `resolve_url.py` — URL fallback (+ rewrite `10.0.2.2` cho Android emulator)
- `generate_mock_server.py` — Sinh mock server (CHỈ dry-run validate spec khi user yêu cầu rõ — KHÔNG thay app trong UAT)
- `generate_data_factory.py` — ⭐ Sinh `tests/fixtures/data-factory.ts` từ Data Matrix
- `write_results_to_excel.py` — Ghi kết quả dual-layer vào Excel
- `recalc.py` — ⭐ Cập nhật sheet 'UAT Result' (Summary metrics)
- `extract_failed_tcs.py` — ⭐ Xuất danh sách TC fail → `failed-tc-ids.txt` + `--grep` pattern cho Retest Mode (module map từ `--uat-json`; Excel chỉ là legacy fallback)

## Reference files

- `references/playwright-config.md` — Config chuẩn mới: projects chain (api-smoke→setup→e2e→cleanup), fixture-composition, 2 evidence profile
- `references/ui-e2e-patterns.md` — ⭐ Pattern UI assertion (≥3 rule) + web-first + test.step + expect.soft
- `references/pom-template.md` — Page object dạng fixture + locator user-facing
- `references/mobile-runner.md` — ⭐ Gate 3 Maestro: preflight, device ladder, flow YAML rules, evidence, crash oracle, iOS blocked protocol
- `references/excel-workflow.md` — Excel I/O schema (Excel = OUTPUT only)
- `references/fallback-strategies.md` — Fallback rules + mock policy 3 loại + NO-RUN
- `references/troubleshooting.md` — Debug flaky tests + triage taxonomy
- `references/handoff-schema.md` — ⭐ MIRROR hợp đồng writer→runner (nguồn chân lý gốc ở `uat-test-writer/references/handoff-schema.md`; đổi schema = sync CẢ HAI bản)
- `../uat-test-writer/references/platform-detection.md` — dùng khi writer cài cùng máy; không có → `detect_platform.py` tự chạy (cùng logic)

## Lưu ý cuối — UNCONDITIONAL RULES

1. **MỌI invoke = chạy đủ các gate áp dụng theo platform** (trừ 3 case dừng)
1a. **PLAYWRIGHT/MAESTRO LUÔN CHẠY FOREGROUND** — `--reporter=line,json` / live output. KHÔNG `run_in_background`.
2. **KHÔNG hỏi user mode** — default headless Chromium / emulator headless
3. **KHÔNG dừng vì thiếu URL/credential** — fallback chain
4. **App không chạy → khởi động app thật; không được → NO-RUN + remediation. KHÔNG mock thay app.**
5. **SINH ĐỦ layer theo platform TC** — API spec + (web: e2e spec / mobile: Maestro flow); seed test sinh đầu tiên
6. **E2E ≥ 3 UI assertion** (URL/screen identity + visibility + text/value) — web LẪN mobile
7. **API trước, E2E/mobile sau** (smoke gate logic)
8. **Evidence theo profile** — sign-off: trace+screenshot+video 'on', retries 0, failOnFlakyTests; CI: on-first-retry/on-failure
9. **Chromium only default** — multi-browser khi user yêu cầu rõ
10. **Bug tracker phân biệt layer + nhãn triage** — `[API]`/`[E2E]`/`[MOBILE]` × product-bug/locator-drift/environment/flaky
11. **⛔ INPUT = .md/.json — KHÔNG BAO GIỜ dùng Excel để thực thi test.** Excel chỉ nhận kết quả.
12. **flatten + extract_failed_tcs PHẢI chạy** sau mỗi lần test — bắt buộc.
13. **write_results_to_excel OPTIONAL** — chỉ chạy khi `$EXCEL_FILE` tồn tại.
14. **Dùng `$SKILL_SCRIPTS` variable** — KHÔNG hardcode path
15. **Sinh code THEO BATCH 25 TC** — không sinh toàn bộ 100+ TC một lần
16. **Verify TC count sau generate** — Source = spec/flow count per platform, lệch → sinh thêm batch
17. **`bail: 0`** — không để Playwright dừng khi TC fail
18. **Projects chain dùng `dependencies` ĐÚNG semantics**: api-smoke → setup → e2e (+ `cleanup` teardown:true luôn chạy); E2E bị SKIP khi smoke đỏ là hành vi ĐÚNG — report ghi SKIPPED, không phải lỗi
19. **Sau Full Run PHẢI có `failed-tc-ids.txt`** + cập nhật baseline khi run xanh
20. **Retest DEFAULT = `scope=module`** (confirmation + regression); fix S1/S2 thêm exploratory quanh vùng fix
21. **Mỗi vòng Retest cập nhật `retest-tc-ids.txt`** — chỉ giữ TC vẫn fail
22. **Regression** = TC từng PASS (baseline/cùng module) nay fail → nhãn "⚠️ REGRESSION" + severity +1 + thu hồi sign-off nếu có
23. **KHÔNG auto-sửa assertion; heal locator ≤2 lần có log** — phân loại triage trước khi làm gì
24. **GO/NO-GO 8 gate, 4 verdict; chỉ tính platform đã execute; người ký sign-off — AI không tự approve**
25. **MCP (Playwright/Maestro) chỉ dùng authoring/debug** — gate chính thức chạy code/YAML đã persist
