# Troubleshooting - Debug test flaky / fail bất thường

Đọc khi test fail mơ hồ, flaky, hoặc gặp lỗi môi trường.

## ⭐ Bước 0 LUÔN LÀM TRƯỚC: phân loại triage (4 nhãn)

Thu thập bằng chứng: error message + trace (`npx playwright trace` CLI khi ≥1.59) + console/pageErrors/requests + logcat (mobile), rồi gán nhãn:

| Nhãn | Dấu hiệu | Xử lý |
|------|----------|-------|
| **product bug** | assertion fail, hành vi ≠ oracle | tạo bug + evidence — KHÔNG sửa test |
| **locator drift** | timeout/element-not-found do UI đổi | heal locator từ DOM thật ≤2 lần, log diff |
| **environment** | ECONNREFUSED/5xx toàn cục/device offline | NO-RUN — không tính defect |
| **flaky** | pass/fail thất thường cùng code | quarantine @flaky, owner + deadline 14 ngày |

⛔ KHÔNG BAO GIỜ "sửa assertion cho khớp app" — đó là che giấu regression. ⛔ Heal selector mà thêm delay → nghi che perf regression, flag lại.

## ❌ Vấn đề 0: Skill dừng giữa chừng, không chạy hết TC

### Triệu chứng
- Chỉ sinh được 30-50 TC dù Excel có 100+
- Playwright chạy xong một phần rồi dừng
- Report thiếu nhiều TC so với Excel

### Nguyên nhân & fix

| Nguyên nhân | Dấu hiệu | Fix |
|-------------|----------|-----|
| Sinh code quá nhiều một lần → context overflow | Spec file cắt đột ngột | Dùng batch 25 TC, write file sau mỗi batch |
| `bail` không set → dừng khi 1 TC fail | Log: "stopping after first failure" | Thêm `bail: 0` trong playwright.config.ts |
| `dependencies` skip E2E khi smoke đỏ | "0 E2E tests ran" + api-smoke có fail | Đây là GATE ĐÚNG semantics — fix API trước; report ghi SKIPPED. Chỉ khi api-smoke XANH mà E2E vẫn 0 → check TS error/testMatch |
| Playwright exit code != 0 → pipeline abort | Pipeline stop sau GĐ 5 | Thêm `true` sau mỗi lệnh playwright test |
| TypeScript error trong spec → project bị skip | "0 tests found" | Fix TS error, chạy `npx tsc --noEmit` trước |

### Checklist khi bị thiếu TC

```bash
# 1. Đếm TC trong Excel
python "$SKILL_SCRIPTS/read_excel_uat.py" "$EXCEL_FILE" \
  | python -c "import json,sys; d=json.load(sys.stdin); print('Excel TC:', len(d['test_cases']))"

# 2. Đếm test() trong spec files
echo "API spec TC:" $(grep -c "^\s*test(" tests/api/*.api.spec.ts 2>/dev/null || echo 0)
echo "E2E spec TC:" $(grep -c "^\s*test(" tests/e2e/*.e2e.spec.ts 2>/dev/null || echo 0)

# 3. Xem Playwright đã chạy bao nhiêu
echo "API ran:"  $(grep '"status"' test-results/raw-results.json 2>/dev/null | wc -l)
echo "E2E ran:"  $(grep '"status"' test-results/raw-results.json 2>/dev/null | wc -l)

# 4. Nếu spec file thiếu → sinh thêm batch cho TC còn thiếu
# 5. Nếu Playwright thiếu → check xem có TS error không
npx tsc --noEmit 2>&1 | head -30
```

---

## Quy trình debug chung

Khi 1 test fail, đi theo 5 bước:

1. **Xem error message + screenshot** trong `test-results/<test-name>/`
2. **Mở trace viewer**: `npx playwright show-trace test-results/<test-name>/trace.zip`
3. **Chạy lại với debug**: `npx playwright test <file> --debug` (mở Playwright Inspector)
4. **Run headed mode**: `--headed --slow-mo=500` để xem hoạt động chậm
5. **Add console.log + page.pause()** ở chỗ nghi ngờ

## Vấn đề 1: "Element not found" / Timeout

### Triệu chứng
```
Error: locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator('[data-testid="submit"]')
```

### Nguyên nhân & fix

| Nguyên nhân | Cách kiểm tra | Fix |
|-------------|---------------|-----|
| Selector sai | Mở DevTools, query thử | Sửa selector trong Page Object |
| Element load chậm | Check Network tab | Tăng timeout: `await locator.click({ timeout: 60_000 })` |
| Element bị hide bởi modal/overlay | Screenshot | Đóng modal trước, hoặc dùng `.click({ force: true })` |
| Element trong iframe | Inspect HTML | Dùng `page.frameLocator('iframe').locator(...)` |
| Element trong shadow DOM | Inspect | Playwright auto-pierce, nhưng selector cần đúng |
| Race condition (click trước khi render) | Trace viewer | Thêm `await expect(locator).toBeVisible()` trước click |

### Debug command
```bash
npx playwright test --debug
# Trong Inspector: click "Explore" → hover element trên page → copy selector
```

## Vấn đề 2: Test flaky (lúc pass lúc fail)

### Triệu chứng
Test pass local, fail trên CI. Hoặc chạy 10 lần thì fail 2 lần.

### Nguyên nhân & fix

```typescript
// ❌ Flaky: hard-coded wait
await page.waitForTimeout(2000);

// ❌ Flaky luôn: networkidle — app có polling/websocket không bao giờ "idle" (docs discourage)
// await page.waitForLoadState('networkidle');

// ✅ Stable: chờ điều kiện CỤ THỂ (web-first)
await expect(page.getByTestId('result')).toBeVisible();
await page.waitForResponse('**/api/data');
```
> Ghi nhớ: **~45% flakiness toàn ngành là async-wait** — sửa wait đúng cách là can thiệp ROI cao nhất.

```typescript
// ❌ Flaky: assertion không retry
const text = await page.locator('h1').textContent();
expect(text).toBe('Welcome');

// ✅ Stable: web-first assertion (tự retry)
await expect(page.locator('h1')).toHaveText('Welcome');
```

```typescript
// ❌ Flaky: animation chưa xong
await page.click('.modal-trigger');
await page.click('.modal-close');  // Có thể fail vì modal chưa fully open

// ✅ Stable: chờ animation
await page.click('.modal-trigger');
await expect(page.locator('.modal')).toBeVisible();
await page.click('.modal-close');
await expect(page.locator('.modal')).not.toBeVisible();
```

### Detection
```bash
# Chạy 1 test 10 lần để check flaky
npx playwright test login.spec.ts --repeat-each=10
```

## Vấn đề 3: "Browser not installed"

### Triệu chứng
```
Error: Executable doesn't exist at /home/user/.cache/ms-playwright/chromium-1234/chrome-linux/chrome
```

### Fix
```bash
npx playwright install              # Cài tất cả browsers
npx playwright install chromium     # Chỉ Chromium
npx playwright install --with-deps  # Cài cả system deps (Linux)
```

Nếu Docker container:
```dockerfile
FROM mcr.microsoft.com/playwright:v1.49.0-noble
# Browser đã có sẵn trong image này
```

## Vấn đề 4: "Connection refused" / "ECONNREFUSED"

### Triệu chứng
```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:3000
```

### Nguyên nhân
App chưa start.

### Fix
- Start app thủ công: `npm run dev` ở terminal khác
- Hoặc dùng `webServer` config:
```typescript
webServer: {
  command: 'npm run dev',
  url: 'http://localhost:3000',
  reuseExistingServer: !process.env.CI,
  timeout: 120_000,
},
```

## Vấn đề 5: Test pass local, fail CI

### Checklist

- [ ] Env vars set đầy đủ trên CI? (kiểm tra secrets)
- [ ] CI dùng đúng Node version? (`node -v` check)
- [ ] Headless mode khác nhau? Thử `--headed` local để reproduce
- [ ] CI machine yếu hơn? Tăng timeout cho CI:
  ```typescript
  use: {
    actionTimeout: process.env.CI ? 30_000 : 10_000,
  }
  ```
- [ ] Animation/transition khác browser? Disable animation:
  ```typescript
  await page.addStyleTag({
    content: `*, *::before, *::after { animation: none !important; transition: none !important; }`
  });
  ```
- [ ] Date/timezone khác? Set explicit:
  ```typescript
  use: { timezoneId: 'Asia/Ho_Chi_Minh' }
  ```

## Vấn đề 6: "Cannot find module"

### Triệu chứng
```
Cannot find module '../pages/LoginPage'
```

### Fix
- Check `tsconfig.json` có `"baseUrl": "."` và `"paths"` đúng không
- Hoặc dùng relative path chính xác (Playwright không hỗ trợ alias mặc định)

`tsconfig.json` mẫu:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "baseUrl": ".",
    "paths": {
      "@pages/*": ["tests/pages/*"],
      "@fixtures/*": ["tests/fixtures/*"],
      "@helpers/*": ["tests/helpers/*"]
    }
  },
  "include": ["tests/**/*"]
}
```

## Vấn đề 7: Test nhanh quá / chậm quá

### Quá nhanh (chưa kịp render)
```typescript
// Slow down toàn bộ test
use: { launchOptions: { slowMo: 500 } }

// Hoặc per-action
await page.locator('button').click({ delay: 200 });
```

### Quá chậm (timeout)
```typescript
// Tăng timeout chỗ chậm
await page.goto('/heavy-page', { timeout: 60_000 });

// Skip animation
await page.evaluate(() => {
  document.body.style.setProperty('--transition-duration', '0s');
});
```

## Vấn đề 8: "Storage state not found"

### Triệu chứng
```
Error: ENOENT: no such file or directory, 'auth.json'
```

### Fix
Chạy global setup trước:
```bash
# Manual
npx playwright test --project=setup
# Hoặc thêm dependency vào config:
projects: [
  { name: 'setup', testMatch: 'global.setup.ts' },
  { name: 'tests', dependencies: ['setup'] },
],
```

## Vấn đề 9: Mock route không work

### Nguyên nhân
- Route được set SAU khi request đã được gọi
- URL pattern không match

### Fix
```typescript
// ❌ Sai: set route sau khi navigate
await page.goto('/products');
await page.route('**/api/products', ...);  // Quá muộn!

// ✅ Đúng: set route TRƯỚC khi trigger request
await page.route('**/api/products', ...);
await page.goto('/products');
```

Debug route matching:
```typescript
await page.route('**/api/**', route => {
  console.log('Intercepted:', route.request().url());
  route.continue();
});
```

## Vấn đề 10: Memory leak / browser không close

### Triệu chứng
Sau N test, máy bị chậm dần, RAM cao.

### Fix
- Đảm bảo context.close() trong afterEach nếu tạo manual:
```typescript
test.afterEach(async ({ context }) => {
  await context.close();
});
```
- Giảm workers: `workers: 2`
- Disable video nếu không cần: `video: 'off'`

## Tools debug hữu ích

### 1. Playwright Inspector
```bash
npx playwright test --debug
```
GUI cho phép step-by-step, edit selector, copy code.

### 2. Trace Viewer
```bash
npx playwright show-trace trace.zip
```
Timeline đầy đủ: network, console, screenshot từng action.

### 3. UI Mode (recommended cho dev)
```bash
npx playwright test --ui
```
Watch mode, re-run nhanh, pick test, time-travel debugging.

### 4. Codegen
```bash
npx playwright codegen http://localhost:3000
```
Record action trên browser → generate code.

### 5. Pause in test
```typescript
test('debug test', async ({ page }) => {
  await page.goto('/login');
  await page.pause();  // Mở Inspector tại đây
  await page.fill('[name="email"]', 'alice@test.com');
});
```

## Khi nào báo user (vs tự fix)

| Tình huống | Hành động |
|-----------|-----------|
| Selector chắc chắn sai (HTML thay đổi) | Tự fix Page Object |
| App không có data-testid | Hỏi user: dùng selector tạm hay đề xuất dev add testid |
| Timeout do app chậm | Hỏi user xác nhận trước khi tăng timeout |
| Test fail do bug app thật | Báo user, KHÔNG sửa expected để pass |
| Env var missing | Hỏi user, gợi ý setup .env |
| Browser chưa cài | Tự chạy `npx playwright install` |
