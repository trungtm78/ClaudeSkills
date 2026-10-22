# Platform Detection — multi-label + JSON contract (CHUNG cho writer & runner)

> Mục đích: Bước 0.7 (writer) và Gate 0 (runner) cùng dùng MỘT logic detect và MỘT file output `docs/uat/_platform.json`. **Multi-label, không bao giờ đơn nhãn** — monorepo web+mobile là chuyện bình thường.

## 1. Ma trận detect (marker file → label)

Quét theo THỨ TỰ sau (tránh nhầm — Flutter/RN cũng có android/ios dir):

| # | Label | Marker chính | Marker xác nhận | Ghi chú |
|---|-------|--------------|-----------------|---------|
| 1 | `FLUTTER` | `pubspec.yaml` có `flutter:` | `lib/main.dart`, `.metadata` | `integration_test/` → đã dùng integration_test; `patrol` trong dev_dependencies → Patrol sẵn |
| 2 | `HYBRID_WEBVIEW` (+`WEB`) | `capacitor.config.{ts,json,js}` / `config.xml` (Cordova) / `src-tauri/tauri.conf.json` mobile | `@capacitor/core`, `ionic.config.json`, `webDir` | webDir cho biết Playwright serve gì; DUAL GATE web+native |
| 3 | `RN` (+`EXPO` nếu có) | `react-native` trong package.json deps | `metro.config.js`, `ios/Podfile`, `android/settings.gradle` | EXPO: `expo` dep + `app.json`/`app.config.*`; managed (không có ios/android dir) ⇒ phải build dev-client trước E2E |
| 4 | `IOS` | `*.xcodeproj` / `*.xcworkspace` | `Info.plist`, `Podfile` | appId = `PRODUCT_BUNDLE_IDENTIFIER` trong project.pbxproj |
| 5 | `ANDROID` | `settings.gradle(.kts)` + `AndroidManifest.xml` | `gradlew`, plugin `com.android.application` | appId = `applicationId` trong build.gradle |
| 6 | `WEB` | next/vite/react/vue/angular/svelte trong package.json + không rơi vào 1-3 | `index.html`, framework config | PWA: manifest.webmanifest + service worker → thêm check offline/installability |
| 7 | `API` | `openapi.*`/`swagger.*`, nest-cli.json, manage.py, pom.xml, go.mod, prisma/schema | `.env` có API_URL/BASE_URL | Label ĐỘC LẬP, cộng thêm — quyết định API smoke gate |
| 8 | Monorepo | pnpm-workspace.yaml, turbo.json, nx.json, lerna.json, workspaces | `apps/` + `packages/` | **Recurse từng package, label riêng, rồi UNION** |

**Mỗi label PHẢI ghi kèm evidence** (file nào khớp) — để report giải trình được quyết định.

## 2. Stack khuyến nghị per label

| Label | E2E mặc định | Lựa chọn 2 / bổ sung |
|-------|--------------|----------------------|
| FLUTTER | **Maestro** (black-box, YAML) | **Patrol** khi AC có permissions/biometrics/WebView-OAuth/native dialog; `integration_test` làm pre-gate nhanh |
| RN / EXPO | **Maestro** | Detox nếu RN-only + reliability tối đa (lưu ý New Arch còn issue) |
| ANDROID | **Maestro** | Espresso+UIAutomator khi cần sâu |
| IOS | **Maestro** (simulator, CHỈ macOS) | XCUITest |
| HYBRID_WEBVIEW | **DUAL**: Playwright (web layer — chính) + Maestro (app build — native shell/plugins) | Appium webview context nếu cần DOM trong WebView thật |
| WEB | **Playwright** (như cũ) | device descriptors cho responsive |
| API | **Playwright request** (APIRequestContext) | — |

## 3. JSON contract — `docs/uat/_platform.json`

```jsonc
{
  "platforms": ["FLUTTER", "API"],              // union các label
  "packages": [
    { "path": "apps/mobile", "labels": ["FLUTTER"], "evidence": ["apps/mobile/pubspec.yaml"] },
    { "path": "apps/web",    "labels": ["WEB"],     "evidence": ["apps/web/next.config.js"] },
    { "path": "services/api","labels": ["API"],     "evidence": ["services/api/openapi.yaml"] }
  ],
  "appId":    { "android": "com.acme.app", "ios": "com.acme.app" },
  "buildCmds":{ "android": "flutter build apk --debug",
                "ios": "flutter build ios --simulator" },
  "artifacts":{ "android": "build/app/outputs/flutter-apk/app-debug.apk" },
  "apiBaseUrl": "http://localhost:3000",
  "apiBaseUrlForAndroidEmulator": "http://10.0.2.2:3000",   // BẮT BUỘC sinh kèm
  "recommendedStack": { "mobile": "maestro", "web": "playwright", "api": "playwright-request" },
  "host": { "os": "win32", "hasAdb": true, "hasJava17": true,
            "hasXcode": false, "iosPossible": false },
  "devices": [ { "id": "emulator-5554", "platform": "android", "api": 34 } ],
  "blockers": [ { "platform": "ios", "reason": "no macOS host",
                  "remediation": ["github-actions macos-latest workflow", "maestro cloud", "browserstack"] } ]
}
```

Quy tắc:
- `unknown` = câu hỏi cho user, KHÔNG đoán bừa.
- `blockers[]` bắt buộc liệt kê platform không chạy được trên host hiện tại + remediation — runner dùng để báo `NOT_EXECUTED` thay vì im lặng bỏ.
- `apiBaseUrlForAndroidEmulator`: emulator Android không thấy `localhost` của host — rewrite `10.0.2.2` (Genymotion `10.0.3.2`) hoặc dùng `adb reverse tcp:PORT tcp:PORT`. iOS simulator dùng chung localhost với host.

## 4. Persona × Journey × Platform matrix (ghi vào `_domain-pack.md`)

```
| Persona          | Journey            | WEB | ANDROID | IOS |
|------------------|--------------------|-----|---------|-----|
| Nhân viên duyệt  | Duyệt đơn chi tiêu | J1  | J1-m    | N/A (chưa phát hành iOS) |
| Kế toán          | Đối soát cuối kỳ   | J2  | N/A (chỉ web) | N/A |
```
- Mỗi ô ≠ N/A phải có ≥1 TC E2E trỏ về (`journey_ref`).
- N/A phải có lý do — đây là coverage claim kiểm chứng được.

## 5. Testability gate

Khi platform mobile: grep source tìm stable test ID (`testID` RN · `testTag` Compose · `Semantics(identifier:)` Flutter · `accessibilityIdentifier` SwiftUI/UIKit · `resource-id` XML · `data-testid` web). Thiếu → **file TESTABILITY DEFECT** đề xuất vị trí cần thêm (form inputs, nút submit, list items của journey chính). Locator ưu tiên: accessibility label/role > test ID > text > index/XPath (cấm).
