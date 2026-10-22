# Mobile Runner — Gate 3 (Maestro) — Android/iOS/Flutter/RN/hybrid

> Đọc khi `_platform.json` có label ANDROID / IOS / FLUTTER / RN / HYBRID_WEBVIEW. Stack mặc định: **Maestro** (YAML flow, framework-agnostic, drive qua accessibility layer). Gate 3b (Patrol/Detox) chỉ khi Maestro không diễn đạt được AC (biometrics sâu, native dialog phức tạp).

## 1. Preflight (không hỏi user — tự cài)

```bash
# Java 17+ bắt buộc (JAVA_HOME phải set)
java -version 2>&1 | head -1

# Maestro CLI
maestro --version 2>/dev/null && echo "MAESTRO_OK" || echo "MAESTRO_MISSING"
# Cài: macOS/Linux/GitBash:  curl -fsSL "https://get.maestro.dev" | bash
# Windows native: tải maestro.zip từ GitHub releases → giải nén C:\maestro → add C:\maestro\bin vào PATH
# ⛔ KHÔNG dùng WSL cho Maestro (chính chủ khuyến cáo — lỗi port configuration)

# Android SDK / adb — tái dùng auto-detect từ skill qa-mobile (LOCALAPPDATA/Android/Sdk, ...)
```

## 2. Device ladder (thứ tự thử)

```
1. maestro list-devices / adb devices          → có device/emulator đang chạy? dùng luôn
2. maestro start-device --platform android     → hoặc emulator thủ công:
   emulator @<avd> -no-window -no-audio -no-boot-anim -no-snapshot
   adb wait-for-device shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done'
3. Chưa có AVD → sdkmanager "platform-tools" "system-images;android-34;google_apis;x86_64"
                 avdmanager create avd -n uat_api34 -k "..." -d pixel_6
4. Không SDK / không tăng tốc (cần WHPX/HAXM) → cloud device farm nếu có credentials
   (Maestro Cloud / BrowserStack / Firebase Test Lab)
5. Hết đường → NOT_EXECUTED (blocked) + remediation — KHÔNG fail lặng lẽ
```

**iOS**: simulator CHỈ trên macOS (`xcodebuild`/`simctl`); Maestro không hỗ trợ iOS real device. **Trên Windows: iOS = NOT_EXECUTED (blocked: no macOS host)** — deliverable khi blocked:
1. Vẫn sinh YAML flows (platform-agnostic, chạy được sau).
2. Sinh sẵn workflow GitHub Actions `macos-latest` chạy Maestro iOS (ready-to-commit).
3. Nêu option Maestro Cloud / BrowserStack nếu user có tài khoản.

## 3. Build + install app TRƯỚC khi chạy flow (Maestro giả định app đã cài)

| Codebase | Build | Install |
|----------|-------|---------|
| Flutter | `flutter build apk --debug` | `adb install -r build/app/outputs/flutter-apk/app-debug.apk` |
| RN bare | `cd android && ./gradlew assembleDebug` | `adb install -r app/build/outputs/apk/debug/app-debug.apk` |
| Expo | `npx expo run:android` (managed cần dev-client build) | tự install |
| Native Android | `./gradlew assembleDebug` | `adb install -r ...` |
| iOS (macOS) | `xcodebuild -sdk iphonesimulator ...` / `flutter build ios --simulator` | `xcrun simctl install booted <app>` |

`appId` + buildCmds lấy từ `_platform.json`.

## 4. Localhost rewrite (lỗi phổ biến #1: "network error trong emulator")

- Emulator Android KHÔNG thấy `localhost` của host → dùng `http://10.0.2.2:<port>` (Genymotion: `10.0.3.2`), hoặc `adb reverse tcp:<port> tcp:<port>` khi app hardcode localhost.
- iOS simulator dùng chung localhost với host — không cần rewrite.
- API smoke gate (Gate 1) vẫn chạy từ host bằng URL thường.

## 5. Quy tắc sinh flow YAML (1 TC = 1 file `.maestro/<feature>/TC-xxx.yaml`)

```yaml
# TC-021: Kế toán từ chối đơn thiếu chứng từ (persona: ke-toan, journey: J-APPROVE-02)
appId: com.acme.app
tags: [P0, S2, journey-approve]
---
- clearState                       # cách ly: mỗi TC bắt đầu sạch
- launchApp:
    permissions: { all: allow }    # khai báo EXPLICIT — TC PERMISSIONS thì deny từng quyền
- startRecording: TC-021           # ⚠️ recording cap ~3 phút — journey dài chia chunk
- runFlow: ../common/login.yaml    # login qua UI như EU (hoặc onFlowStart hook trong config.yaml)
- takeScreenshot: TC-021-given     # ranh giới Given

- tapOn: "Đơn chờ duyệt"           # ưu tiên accessibility label/text — không tìm thấy = a11y defect
- assertVisible: "DON-2026-0012"
- tapOn:
    id: "btn-reject"               # testID khi có (locator_hint từ uat.json)
- inputText: "Thiếu chứng từ theo quy định"
- tapOn: "Xác nhận"
- takeScreenshot: TC-021-when      # ranh giới When

# ≥3 assertion: screen identity + visibility + text/data (mirror rule web)
- assertVisible: "Đã từ chối"                      # 1. trạng thái màn hình
- assertVisible:
    id: "status-badge"                             # 2. element nghiệp vụ
- assertVisible: "Thiếu chứng từ theo quy định"    # 3. data đúng (lý do lưu lại)
- takeScreenshot: TC-021-then
- stopRecording
```

Quy tắc cứng:
- `clearState` + `launchApp.permissions` EXPLICIT ở MỌI flow (cách ly + tái lập).
- KHÔNG sleep/`waitForAnimationToEnd` bừa — dùng `extendedWaitUntil`/`assertVisible` (tự settle) chờ đúng state.
- `takeScreenshot` tại ranh giới Given/When/Then.
- TC PERMISSIONS: `permissions: { camera: deny, ... }` per case; TC OFFLINE: `setAirplaneMode`; TC DEEPLINK: `openLink`; TC LIFECYCLE: `pressKey: Home` + `launchApp` (không clearState để giữ state).
- `config.yaml` của workspace: `appId`, `onFlowStart` (login/seed hooks), tags.

## 6. Chạy + thu kết quả

```bash
# Foreground, JUnit output — cùng shape parser với Playwright
adb logcat -c                                    # xoá log trước run (crash oracle)
maestro test .maestro/<feature> \
  --format JUNIT --output test-results/mobile/junit.xml \
  --debug-output test-results/mobile/debug      # auto screenshot khi fail
adb logcat -d > test-results/mobile/logcat.txt  # thu log sau run
```

**Crash oracle (BẮT BUỘC):** grep logcat `FATAL EXCEPTION` / `ANR in` / `Force finishing activity` → có crash = TC **FAIL kể cả khi UI assertion pass**. Ghi nhãn `[MOBILE] product bug (crash)`.

**Retry policy mobile**: ≤1 retry/TC, log lại; **pass-on-retry = AMBER** (không phải PASS sign-off). Flakiness budget mobile 2-5% (cao hơn web 1-2%) — vượt → dừng và sửa root cause (device contention/network/timing), không tăng retry.

## 7. Maestro MCP — CHỈ authoring/debug

```bash
claude mcp add maestro -- maestro mcp   # cần JAVA_HOME + path tuyệt đối tới maestro binary
```
- Vòng lặp: `list_devices` → `inspect_screen` (view hierarchy JSON — rẻ hơn screenshot nhiều) → `run` với **inline YAML** thử từng step → step nào ăn thì persist vào file flow.
- Enumerate tool names lúc runtime (tên tool drift giữa version — gọi `cheat_sheet` để lấy syntax).
- **Gate chính thức LUÔN chạy CLI từ YAML đã persist** — reproducible, không phụ thuộc model.
- `assertWithAI`/`assertNoDefectsWithAI` (experimental, cần LLM key): chỉ dùng BỔ TRỢ quét visual-defect, không bao giờ là oracle duy nhất.

## 8. Hybrid (Capacitor/Ionic/Cordova) — DUAL GATE

- Gate 2b: Playwright test web layer (serve `webDir`/dev server) — phủ 80-90% business logic, nhanh.
- Gate 3: Maestro trên app build thật — CHỈ phủ native shell: plugins (camera/push/biometric), permission prompts, deep link, lifecycle, safe area, hardware back.
- 2 bộ TC đã được writer cross-reference — report cộng gộp coverage, không double-count.

## 9. Evidence layout mobile

```
test-results/mobile/
  junit.xml                      # kết quả máy đọc (flatten chung với Playwright)
  logcat.txt                     # crash oracle
  debug/                         # screenshot fail tự động (--debug-output)
  <TC-id>/
    TC-xxx.mp4                   # recording (chunk <3 phút)
    TC-xxx-given|when|then.png   # screenshot ranh giới bước
    hierarchy.json               # view hierarchy khi cần (maestro hierarchy)
```
