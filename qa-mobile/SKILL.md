---
name: qa-mobile
version: 1.0.0
description: |
  Tự động QA test ứng dụng smartphone (Android/iOS) bằng Maestro.
  Phát hiện thiết bị/emulator, generate Maestro flow YAML, chạy test,
  fix bug trong source code với atomic commit, re-verify sau mỗi fix.
  Dùng khi test Flutter/React Native/native app trên thiết bị thật hoặc emulator.
voice-triggers:
  - "test app mobile"
  - "qa mobile"
  - "test android"
  - "test ios"
  - "maestro test"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

## Preamble (chạy trước)

```bash
_UPD=$(~/.claude/skills/gstack/bin/gstack-update-check 2>/dev/null || true)
[ -n "$_UPD" ] && echo "$_UPD" || true
_PROACTIVE=$(~/.claude/skills/gstack/bin/gstack-config get proactive 2>/dev/null || echo "true")
_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "BRANCH: $_BRANCH"
_TEL=$(~/.claude/skills/gstack/bin/gstack-config get telemetry 2>/dev/null || true)
_TEL_START=$(date +%s)
_SESSION_ID="$$-$(date +%s)"
echo "TELEMETRY: ${_TEL:-off}"
mkdir -p ~/.gstack/analytics
if [ "$_TEL" != "off" ]; then
  echo '{"skill":"qa-mobile","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","repo":"'$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "unknown")'"}'  >> ~/.gstack/analytics/skill-usage.jsonl 2>/dev/null || true
fi
eval "$(~/.claude/skills/gstack/bin/gstack-slug 2>/dev/null)" 2>/dev/null || true
~/.claude/skills/gstack/bin/gstack-timeline-log '{"skill":"qa-mobile","event":"started","branch":"'"$_BRANCH"'","session":"'"$_SESSION_ID"'"}' 2>/dev/null &
```

---

# /qa-mobile: Test → Fix → Verify trên Smartphone

QA engineer chuyên mobile. Test ứng dụng smartphone như user thật — tap từng button, điền form, kiểm tra mọi trạng thái. Khi tìm thấy bug thì fix trong source code với atomic commit, rồi re-verify. Sinh report có evidence trước/sau.

---

## Thiết lập (Setup)

**Parse request của user:**

| Tham số | Mặc định | Ví dụ override |
|---------|----------|----------------|
| App ID | (tự detect) | `com.pc02.mobile`, `--app-id com.example.app` |
| Platform | Android | `--ios`, `--android` |
| Tier | Standard | `--quick`, `--exhaustive` |
| Device | (tự detect) | `--device emulator-5554` |
| Flow dir | `maestro/flows/` | `--flows tests/e2e/` |
| Scope | Toàn app | `Focus on login screen` |
| Auth | Không | `username=admin password=123` |

**Tiers quyết định fix gì:**
- **Quick:** Chỉ fix critical + high
- **Standard:** + medium (mặc định)
- **Exhaustive:** + tất cả kể cả cosmetic

---

## Bước 0: Kiểm tra môi trường

### 0-pre. Auto-detect Android SDK

Chạy trước mọi bước khác. Tự tìm Android SDK ở các vị trí phổ biến trên Windows/macOS/Linux:

```bash
# Auto-detect ANDROID_HOME
if [ -z "$ANDROID_HOME" ]; then
  for _CANDIDATE in \
    "$LOCALAPPDATA/Android/Sdk" \
    "$HOME/AppData/Local/Android/Sdk" \
    "$HOME/Library/Android/sdk" \
    "$HOME/Android/Sdk" \
    "/usr/local/lib/android/sdk" \
    "/opt/android-sdk"; do
    if [ -d "$_CANDIDATE/platform-tools" ]; then
      export ANDROID_HOME="$_CANDIDATE"
      echo "ANDROID_HOME auto-detected: $ANDROID_HOME"
      break
    fi
  done
fi
[ -z "$ANDROID_HOME" ] && echo "ANDROID_HOME_MISSING" || echo "ANDROID_HOME: $ANDROID_HOME"

# Resolve full binary paths with .exe fallback (Windows)
_ADB="$ANDROID_HOME/platform-tools/adb"
[ -f "${_ADB}.exe" ] && _ADB="${_ADB}.exe"
_EMU="$ANDROID_HOME/emulator/emulator"
[ -f "${_EMU}.exe" ] && _EMU="${_EMU}.exe"

echo "ADB: $_ADB"
echo "EMULATOR: $_EMU"
[ -f "$_ADB" ] && echo "ADB_OK" || echo "ADB_MISSING"
[ -f "$_EMU" ] && echo "EMU_OK" || echo "EMU_MISSING"
```

Nếu `ANDROID_HOME_MISSING` → cảnh báo nhưng tiếp tục (có thể dùng USB device không cần SDK).

### 0a. Kiểm tra Maestro CLI

```bash
# Detect platform
_OS="$(uname -s 2>/dev/null || echo Windows)"
case "$_OS" in
  MINGW*|CYGWIN*|MSYS*) _IS_WIN=true ;;
  *) [ "$OS" = "Windows_NT" ] && _IS_WIN=true || _IS_WIN=false ;;
esac

maestro --version 2>/dev/null && echo "MAESTRO_OK" || echo "MAESTRO_MISSING"
java -version 2>&1 | head -1
echo "JAVA_HOME: $JAVA_HOME"
```

**Nếu `MAESTRO_MISSING`:** Tự động thử cài (Java 11+ là đủ — Maestro không cần Java 17):

```bash
# Cài Maestro (hoạt động trên Git Bash/WSL/macOS/Linux)
curl -Ls "https://get.maestro.dev" | bash
export PATH="$HOME/.maestro/bin:$PATH"
maestro --version 2>/dev/null && echo "MAESTRO_INSTALLED" || echo "MAESTRO_INSTALL_FAILED"
```

Nếu `MAESTRO_INSTALL_FAILED` → hỏi user:

Options:
- A) Cài thủ công: paste lệnh trên vào terminal, thông báo khi xong
- B) Dùng WSL: `wsl curl -Ls "https://get.maestro.dev" | bash`
- C) Bỏ qua — chỉ generate flow files mà không chạy test

### 0b. Kiểm tra device/emulator

```bash
# Android — dùng full path $_ADB (đã set ở 0-pre)
"$_ADB" devices 2>/dev/null | grep -v "List of devices" | grep -v "^$" | grep -v "^[[:space:]]*$" \
  && echo "DEVICE_FOUND" || echo "NO_DEVICE"
# iOS simulator (macOS only)
xcrun simctl list devices 2>/dev/null | grep "Booted" || true
```

**Nếu `NO_DEVICE`:** Tự động tìm và khởi động AVD:

```bash
# List AVDs có sẵn
_AVD=$("$_EMU" -list-avds 2>/dev/null | head -1)
echo "AVD: ${_AVD:-NONE}"
```

Nếu `_AVD` có giá trị → tự động start (không cần hỏi):

```bash
echo "Starting AVD: $_AVD"
"$_EMU" -avd "$_AVD" -no-snapshot-load -no-boot-anim -no-audio &
_EMU_PID=$!

# Wait for device to appear in adb
"$_ADB" wait-for-device 2>/dev/null || true

# Wait for full boot (timeout 120s)
_BOOT_START=$(date +%s)
echo "Waiting for sys.boot_completed..."
until "$_ADB" shell getprop sys.boot_completed 2>/dev/null | grep -q "^1"; do
  sleep 3
  _NOW=$(date +%s)
  if [ $(( _NOW - _BOOT_START )) -gt 120 ]; then
    echo "BOOT_TIMEOUT — emulator may need more time"
    break
  fi
done
"$_ADB" shell getprop sys.boot_completed 2>/dev/null | grep -q "^1" \
  && echo "EMULATOR_READY: $_AVD" || echo "EMULATOR_BOOT_INCOMPLETE"
```

Nếu `_AVD` trống (không có AVD nào) → hỏi user:

Options:
- A) Tôi sẽ tạo AVD trong Android Studio và chạy lại
- B) Tôi đã cắm device qua USB, nhận diện lại
- C) Chỉ generate test flows, chạy sau

### 0c. Detect App ID từ project

```bash
# Flutter
grep -r "applicationId\|bundleId\|package" */android/app/build.gradle */pubspec.yaml 2>/dev/null | grep -v "//\|#" | head -5
# React Native
cat ios/*.xcodeproj/project.pbxproj 2>/dev/null | grep "PRODUCT_BUNDLE_IDENTIFIER" | head -3
cat android/app/build.gradle 2>/dev/null | grep "applicationId" | head -3
# Native Android
cat android/app/build.gradle 2>/dev/null | grep "applicationId" | head -3
```

Ưu tiên: user cung cấp > gradle/pubspec > hỏi lại.

### 0d. Kiểm tra working tree

```bash
git status --porcelain
```

Nếu có uncommitted changes → hỏi user:

Options:
- A) Commit ngay
- B) Stash rồi test, pop sau
- C) Bỏ qua

---

## Bước 1: Cài đặt thư mục output

```bash
mkdir -p maestro/flows
mkdir -p .gstack/qa-mobile-reports/screenshots
REPORT_DIR=".gstack/qa-mobile-reports"
FLOWS_DIR="maestro/flows"
```

---

## Bước 2: Phân tích diff để xác định scope test

```bash
git diff main...HEAD --name-only
git log main..HEAD --oneline
```

Từ các file thay đổi, xác định:
- Screen nào bị ảnh hưởng (login_screen.dart → test login flow)
- API nào thay đổi (cases_api.dart → test cases list + detail)
- Model nào thay đổi → test các screen dùng model đó
- Business logic thay đổi → test flow liên quan

**Mapping file → flow test:**
| Loại file thay đổi | Flow cần test |
|-------------------|---------------|
| `*_screen.dart` / `*Screen.tsx` | Screen tương ứng |
| `*_api.dart` / `*Api.ts` | Mọi screen gọi API đó |
| `*_provider.dart` | State management flows |
| `main.dart` / `App.tsx` | Smoke test toàn app |
| Auth files | Login + logout + error state |
| Notification/push files | Notification trigger + receive |
| Theme/style files | Visual check toàn app |

---

## Bước 3: Generate Maestro Flows

Với mỗi scope đã xác định, tạo flow YAML trong `maestro/flows/`.

**Cấu trúc file flow:**

```yaml
# maestro/flows/login_flow.yaml
appId: ${APP_ID}
tags:
  - smoke
  - auth

---
# Bước 1: Mở app
- launchApp

# Bước 2: Kiểm tra login screen load đúng
- assertVisible:
    text: "Đăng nhập"
    
- assertVisible:
    id: "email_field"

# Bước 3: Điền credentials
- tapOn:
    id: "email_field"
- inputText: "${TEST_USERNAME}"

- tapOn:
    id: "password_field"
- inputText: "${TEST_PASSWORD}"

# Bước 4: Submit và verify navigate
- tapOn: "Đăng nhập"
- waitForAnimationToEnd
- assertVisible:
    text: "Dashboard"
    timeout: 5000

# Screenshot kết quả
- takeScreenshot: login_success
```

**Template cho từng loại test:**

### 3a. Login Flow Template

```yaml
# maestro/flows/01_login.yaml
appId: ${APP_ID}
tags: [smoke, auth]

---
- launchApp
- assertVisible: "Đăng nhập"
- tapOn: "Email"
- inputText: "${TEST_USERNAME}"
- tapOn: "Mật khẩu"
- inputText: "${TEST_PASSWORD}"
- hideKeyboard
- tapOn: "Đăng nhập"
- waitForAnimationToEnd
- takeScreenshot: login_result
- assertNotVisible: "Email hoặc mật khẩu không đúng"
```

### 3b. Login Error State Template

```yaml
# maestro/flows/02_login_error.yaml
appId: ${APP_ID}
tags: [auth, error-handling]

---
- launchApp
- tapOn: "Email"
- inputText: "wrong@email.com"
- tapOn: "Mật khẩu"
- inputText: "wrongpassword"
- hideKeyboard
- tapOn: "Đăng nhập"
- waitForAnimationToEnd
- takeScreenshot: login_error
- assertVisible: "Email hoặc mật khẩu không đúng"
- assertNotVisible: "e.toString()"
- assertNotVisible: "Exception:"
- assertNotVisible: "Error:"
```

### 3c. List Screen Template

```yaml
# maestro/flows/03_cases_list.yaml
appId: ${APP_ID}
tags: [cases, data]

---
- runFlow: 01_login.yaml
- assertVisible: "Vụ việc"
- tapOn: "Vụ việc"
- waitForAnimationToEnd
- takeScreenshot: cases_list
- assertNotVisible: "Không có dữ liệu"
- assertNotVisible: "null"
- assertNotVisible: "undefined"
```

### 3d. Detail Screen Template

```yaml
# maestro/flows/04_case_detail.yaml
appId: ${APP_ID}
tags: [cases, detail]

---
- runFlow: 01_login.yaml
- tapOn: "Vụ việc"
- waitForAnimationToEnd
- tapOn:
    index: 0  # First item in list
- waitForAnimationToEnd
- takeScreenshot: case_detail
- assertNotVisible: "null"
- assertNotVisible: "N/A"
- assertNotVisible: "undefined"
# Verify data fields show real values
- assertVisible:
    id: "case_id_field"
```

### 3e. Logout Flow Template

```yaml
# maestro/flows/99_logout.yaml
appId: ${APP_ID}
tags: [smoke, auth]

---
- runFlow: 01_login.yaml
- tapOn: "Menu"
- tapOn: "Đăng xuất"
- waitForAnimationToEnd
- takeScreenshot: logged_out
- assertVisible: "Đăng nhập"
```

**Quy tắc generate flows:**
1. Đặt tên `NN_tên_flow.yaml` (số để control thứ tự chạy)
2. Tag `smoke` = critical path, chạy đầu tiên
3. Luôn `takeScreenshot` sau mỗi action quan trọng
4. Dùng `waitForAnimationToEnd` sau tap/swipe
5. `assertNotVisible` với các string lỗi phổ biến: "null", "undefined", "Exception:", "Error:", "e.toString()"
6. Dùng env var `${APP_ID}`, `${TEST_USERNAME}`, `${TEST_PASSWORD}` thay vì hardcode

---

## Bước 4: Tạo file env cho Maestro

```bash
cat > maestro/.env << 'EOF'
APP_ID=com.pc02.mobile
TEST_USERNAME=<test-account-email>
TEST_PASSWORD=[REDACTED - set from environment]
EOF
```

> KHÔNG bao giờ commit credentials vào file này. Thêm `maestro/.env` vào `.gitignore`.

```bash
grep -q "maestro/.env" .gitignore 2>/dev/null || echo "maestro/.env" >> .gitignore
```

---

## Bước 5: Chạy Test

### 5a. Quick smoke test trước

```bash
# Truyền ANDROID_HOME để Maestro tìm đúng adb
ANDROID_HOME="$ANDROID_HOME" \
maestro test --include-tags=smoke \
  --env APP_ID="${APP_ID}" \
  --env TEST_USERNAME="${TEST_USERNAME}" \
  --env TEST_PASSWORD="${TEST_PASSWORD}" \
  maestro/flows/ 2>&1 | tee "$REPORT_DIR/smoke-run.log"
```

### 5b. Full test suite

```bash
ANDROID_HOME="$ANDROID_HOME" \
maestro test \
  --format JUNIT \
  --output "$REPORT_DIR/maestro-results.xml" \
  --env APP_ID="${APP_ID}" \
  --env TEST_USERNAME="${TEST_USERNAME}" \
  --env TEST_PASSWORD="${TEST_PASSWORD}" \
  maestro/flows/ 2>&1 | tee "$REPORT_DIR/full-run.log"
```

### 5c. Lấy screenshots

Maestro tự lưu screenshots theo tên trong `takeScreenshot`. Copy về report dir:

```bash
# Screenshots thường ở ~/.maestro/tests/latest/ hoặc thư mục temp
find ~/.maestro -name "*.png" -newer "$REPORT_DIR/smoke-run.log" 2>/dev/null \
  | xargs -I{} cp {} "$REPORT_DIR/screenshots/" 2>/dev/null || true
```

### 5d. ADB screenshot verification (smarter testing)

Sau mỗi flow run, chụp màn hình thực tế qua ADB và đọc bằng Read tool để verify trạng thái:

```bash
# Chụp màn hình hiện tại
FLOW_NAME="post_smoke"
"$_ADB" exec-out screencap -p > "$REPORT_DIR/screenshots/${FLOW_NAME}.png" 2>/dev/null || true
```

Sau khi chụp → dùng **Read tool** đọc file PNG để xem màn hình thực tế. So sánh với kỳ vọng của flow. Nếu có dấu hiệu lỗi (spinner kẹt, dialog lỗi, màn hình trắng) → ghi issue ngay dù Maestro báo PASSED.

---

## Bước 6: Parse kết quả và tạo Issue list

Đọc output từ Maestro, phân loại kết quả:

```bash
# Parse JUnit XML
cat "$REPORT_DIR/maestro-results.xml" 2>/dev/null | grep -E "testcase|failure|error" | head -30
# Parse console log
grep -E "PASSED|FAILED|ERROR|✓|✗|×" "$REPORT_DIR/full-run.log" | head -30
```

Với mỗi **FAILED** flow, tạo issue:

```
ISSUE-M001: [Flow name] — [mô tả ngắn]
Severity: Critical / High / Medium / Low
Category: Functional / UX / Data / Auth / Navigation
Evidence: Screenshot path + log excerpt
Repro: Steps từ flow YAML
```

**Phân loại severity:**
- **Critical:** App crash, không đăng nhập được, mất dữ liệu
- **High:** Feature chính không hoạt động (list rỗng, detail không load)
- **Medium:** UX bad (lỗi hiển thị sai ngôn ngữ, field null hiển thị "null")
- **Low:** Cosmetic (khoảng cách sai, màu không đúng)

---

## Bước 7: Health Score

Tính điểm:

| Category | Weight | Score |
|----------|--------|-------|
| Auth (login/logout) | 25% | 100 − (Critical×25 + High×15 + Medium×8 + Low×3) |
| Core features | 30% | 100 − ... |
| Data display | 20% | 100 − ... |
| Navigation | 15% | 100 − ... |
| Error handling | 10% | 100 − ... |

`Health Score = Σ (category_score × weight)`

---

## Bước 8: Fix Loop

Với mỗi issue cần fix (theo tier đã chọn):

### 8a. Locate source

```bash
# Tìm screen/widget liên quan
grep -r "screen_name\|ClassName\|route_path" mobile/lib/ --include="*.dart" -l
# Flutter
grep -rn "null\|\.toString()\|e\.toString" mobile/lib/features/ --include="*.dart" | head -10
```

### 8b. Fix

Đọc source, hiểu context, fix **minimal** — đúng vấn đề, không refactor thêm.

**Các fix pattern phổ biến:**

```dart
// TRƯỚC: lỗi hiển thị raw error
setState(() => _error = e.toString());

// SAU: user-friendly message
setState(() => _error = 'Email hoặc mật khẩu không đúng');
```

```dart
// TRƯỚC: null display
Text(data['field'] ?? 'null')  

// SAU: fallback đúng
Text(data['field'] ?? 'Chưa có thông tin')
```

```dart
// TRƯỚC: API response không unwrap
final data = resp.data as Map<String, dynamic>;

// SAU: unwrap envelope
final body = resp.data as Map<String, dynamic>;
final data = (body['data'] as Map<String, dynamic>?) ?? body;
```

### 8c. Commit

```bash
git add <only-changed-files>
git commit -m "fix(mobile-qa): ISSUE-MXXX — mô tả ngắn"
```

### 8d. Update Flow và Re-test

Sau khi fix, update flow nếu cần, rồi chạy lại chỉ flow đó:

```bash
ANDROID_HOME="$ANDROID_HOME" \
maestro test \
  --env APP_ID="${APP_ID}" \
  --env TEST_USERNAME="${TEST_USERNAME}" \
  --env TEST_PASSWORD="${TEST_PASSWORD}" \
  maestro/flows/NN_flow_vừa_fix.yaml 2>&1

# Chụp ADB screenshot để verify trực quan
"$_ADB" exec-out screencap -p > "$REPORT_DIR/screenshots/after_fix_MXXX.png" 2>/dev/null || true
```

### 8e. Classify

- **verified**: re-test pass, không có lỗi mới
- **best-effort**: fix xong nhưng không verify được (cần device thật)
- **reverted**: `git revert HEAD`, đánh dấu deferred

### 8f. Self-Regulation

Sau mỗi 5 fix:
```
WTF-LIKELIHOOD:
  Mỗi revert:            +15%
  Fix chạm >3 files:     +5%
  Sau fix thứ 15:        +1%/fix
```

Nếu > 20% → STOP, hỏi user có tiếp tục không.

---

## Bước 9: Final Test Run

Chạy lại toàn bộ suite sau khi fix xong:

```bash
ANDROID_HOME="$ANDROID_HOME" \
maestro test \
  --format JUNIT \
  --output "$REPORT_DIR/final-results.xml" \
  --env APP_ID="${APP_ID}" \
  --env TEST_USERNAME="${TEST_USERNAME}" \
  --env TEST_PASSWORD="${TEST_PASSWORD}" \
  maestro/flows/ 2>&1 | tee "$REPORT_DIR/final-run.log"
```

Tính final health score. **Nếu final < baseline → WARN**.

---

## Bước 10: UAT Phase (User Acceptance Testing)

UAT là giai đoạn **nghiệm thu nghiệp vụ** trong SDLC — verify hệ thống đáp ứng đúng yêu cầu từ góc nhìn người dùng cuối / business owner, không phải developer.

### 10a. Thu thập Yêu cầu Nghiệp vụ

Đọc tài liệu project theo thứ tự ưu tiên:

```bash
# Đọc business context
cat CLAUDE.md 2>/dev/null || true
cat README.md 2>/dev/null | head -100 || true
find docs/ wiki/ -name "*.md" 2>/dev/null | head -5 | xargs cat 2>/dev/null || true

# Suy ra features từ git history
git log --oneline -30

# Suy ra màn hình từ code
find mobile/lib/features -name "*_screen.dart" 2>/dev/null | head -20
```

Từ đó derive **Business Acceptance Criteria (BAC)** — tối thiểu 10 BAC:

```
BAC-001: [Tên tiêu chí]
Mô tả: [Điều kiện nghiệp vụ cụ thể, đo được]
Loại: Functional / Data Integrity / Compliance / UX
Ưu tiên: Must-Have / Should-Have / Nice-to-Have
Cách kiểm tra: [Thao tác cụ thể để verify trên thiết bị]
```

Nếu tài liệu quá ít để derive 10 BAC → AskUserQuestion để user bổ sung yêu cầu.

### 10b. Thực thi UAT Test Cases

Với mỗi BAC, thực hiện kiểm tra trên device đang chạy:
- Điều hướng đến màn hình liên quan
- Chụp ADB screenshot làm evidence: `"$_ADB" exec-out screencap -p > "$REPORT_DIR/screenshots/uat_BAC001.png"`
- Đọc screenshot bằng Read tool để đánh giá
- Ghi kết quả:

```
BAC-001: [Tên]
Kết quả: PASS / FAIL / PARTIAL / BLOCKED
Evidence: screenshots/uat_BAC001.png
Ghi chú: [Chi tiết nếu FAIL/PARTIAL — mô tả theo góc nhìn user]
```

### 10c. Benchmark Research

WebSearch để so sánh với hệ thống tương tự trong ngành:

```
# Bước 1: Xác định domain từ CLAUDE.md / README
# Bước 2: WebSearch "[domain] mobile app best practices", "similar [app type] features"
# Bước 3: So sánh — feature nào phổ biến mà app thiếu? flow nào app làm khác chuẩn?
```

Với mỗi gap tìm được:

```
GAP-001: [Tên]
Hệ thống hiện tại: [mô tả từ góc nhìn user]
Chuẩn / Reference: [hệ thống X / standard Y — citation cụ thể]
Tác động: [user bị ảnh hưởng thế nào]
Đề xuất: [cải thiện cụ thể, implementable]
Ưu tiên: High / Medium / Low
```

### 10d. UAT Sign-off Report

Lưu vào `.gstack/uat-reports/uat-{app}-{YYYY-MM-DD}.md`:

```markdown
# UAT Report — {app-name} — {YYYY-MM-DD}

## Tóm tắt nghiệm thu
- Tổng BAC: N | PASS: X | FAIL: Y | PARTIAL: Z | BLOCKED: W
- Kết luận: ✅ ĐẠT / ⚠️ ĐẠT CÓ ĐIỀU KIỆN / ❌ CHƯA ĐẠT

## Acceptance Criteria Results
| ID | Tiêu chí | Kết quả | Evidence |
|----|----------|---------|---------|
| BAC-001 | ... | PASS | ... |

## Gap Analysis
[Danh sách GAP với citation nguồn]

## Defects cần fix trước go-live
[Chỉ FAIL items — reference ISSUE-MXXX tương ứng]

## Recommendation
[Go-live được chưa, điều kiện nếu có]
```

```bash
mkdir -p .gstack/uat-reports
```

---

## Bước 11: Report (QA Technical)

Tạo report:

```markdown
# QA Mobile Report — {app-name} — {YYYY-MM-DD}

## Metadata
- App ID: com.example.app
- Platform: Android / iOS
- Device: emulator-5554 / iPhone 15 Simulator
- Branch: feat/mobile
- Duration: Xs
- Flows run: N
- Framework: Flutter / React Native / Native

## Health Score
- Baseline: N/A (first run)
- Final: XX/100

## Summary
| Severity | Found | Fixed | Deferred |
|----------|-------|-------|----------|
| Critical | X | X | 0 |
| High | X | X | 0 |
| Medium | X | X | X |
| Low | X | X | X |

## Issues

### ISSUE-M001 — [Tên issue]
- **Severity:** High
- **Category:** Data Display
- **Flow:** 03_cases_list.yaml
- **Status:** ✅ Verified Fixed
- **Commit:** abc1234
- **Repro:**
  1. Login
  2. Tap "Vụ việc"
  3. Tap vào vụ việc đầu tiên
  4. Màn hình detail hiển thị "null" ở trường tên
- **Before:** [screenshot path]
- **After:** [screenshot path]

## Flows Generated
- `maestro/flows/01_login.yaml` — Login happy path
- `maestro/flows/02_login_error.yaml` — Login error state
- `maestro/flows/03_cases_list.yaml` — Cases list
...

## PR Summary
> "QA Mobile: N issues found, M fixed, health score X/100. Generated N Maestro flows."
```

Lưu report:
- Local: `.gstack/qa-mobile-reports/qa-mobile-{app}-{YYYY-MM-DD}.md`
- Project: `~/.gstack/projects/{slug}/{branch}-mobile-test-outcome-{datetime}.md`

---

## Bước 12: Commit flows vào repo

Nếu các flow mới là lần đầu được tạo:

```bash
git add maestro/flows/ maestro/.env.example
git commit -m "test(mobile): add Maestro E2E flows for {feature/branch}"
```

> `maestro/.env` không commit (có credentials). Chỉ commit `maestro/.env.example` với placeholder.

---

## Quy tắc quan trọng

1. **Không hardcode credentials.** Dùng `${VAR}` trong flows, truyền qua `--env`.
2. **Mỗi fix một commit.** Không bundle nhiều fix.
3. **takeScreenshot sau mọi action quan trọng.** Không có ảnh = không có evidence.
4. **assertNotVisible với error strings.** "null", "undefined", "Exception:", "e.toString()" phải absent.
5. **waitForAnimationToEnd sau mọi tap/navigate.** Mobile animation chậm hơn web.
6. **Revert ngay nếu fix gây regression.**
7. **Không commit `.env` có credentials thật.**
8. **Nếu device offline:** Vẫn generate flows, đánh dấu status "pending-device".

---

## Telemetry (chạy cuối)

```bash
_TEL_END=$(date +%s)
_TEL_DUR=$(( _TEL_END - _TEL_START ))
~/.claude/skills/gstack/bin/gstack-timeline-log '{"skill":"qa-mobile","event":"completed","branch":"'$(git branch --show-current 2>/dev/null || echo unknown)'","outcome":"OUTCOME","duration_s":"'"$_TEL_DUR"'","session":"'"$_SESSION_ID"'"}' 2>/dev/null || true
if [ "$_TEL" != "off" ]; then
  echo '{"skill":"qa-mobile","duration_s":"'"$_TEL_DUR"'","outcome":"OUTCOME","session":"'"$_SESSION_ID"'","ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' >> ~/.gstack/analytics/skill-usage.jsonl 2>/dev/null || true
fi
```
