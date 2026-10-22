# Playwright Config — Gate Orchestrator (API smoke → setup → E2E → cleanup)

## Triết lý

- **Projects chain với `dependencies` đúng semantics**: smoke đỏ → E2E bị SKIP (đúng, không phải lỗi); `cleanup` là teardown project LUÔN chạy kể cả khi fail.
- **Fixture-composition thay POM cổ điển**: page objects inject qua fixtures, không `new` trong test.
- **Locator user-facing**: `getByRole` → `getByLabel` → `getByText` → `getByTestId` → CSS (cấm XPath/nth-child).
- **Web-first assertions** — không `waitForTimeout`, không `networkidle`, không `if (await isVisible())`.
- **2 evidence profile**: CI (nhẹ) vs SIGN-OFF (đầy đủ, retries 0, failOnFlakyTests).
- **Auth 1 lần/role** qua `setup` project + `storageState` — không login UI mỗi test.
- **Version-detect**: `npx playwright --version` → degrade tính năng theo version, ghi version vào report.

## Cấu trúc folder

```
tests/
├── uat.seed.spec.ts              # ⭐ seed test — env init + auth + style exemplar (sinh ĐẦU TIÊN)
├── api/                          # Gate 1 — API smoke
│   └── <feature>.api.spec.ts
├── e2e/                          # Gate 2 — UI E2E (Chromium)
│   └── <feature>.e2e.spec.ts
├── setup/
│   └── auth.setup.ts             # login 1 lần/role → .auth/<role>.json
├── cleanup/
│   └── global.teardown.ts        # dọn data namespace uat-* (LIFO theo ID)
├── fixtures/
│   ├── index.ts                  # mergeTests() các fixture module + inject page objects
│   ├── data.fixture.ts           # worker-scoped: seed qua API, namespace uat-w{workerIndex}, cleanup LIFO
│   └── credentials.ts            # từ resolve_credentials.py
├── pages/                        # page objects (class thuần, inject qua fixture)
│   ├── LoginPage.ts
│   └── ...
.auth/                            # storageState (gitignore)
.maestro/<feature>/               # Gate 3 mobile flows (xem mobile-runner.md)
```

## playwright.config.ts — template chuẩn

```typescript
import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const API_BASE_URL = process.env.API_BASE_URL || BASE_URL;
// Evidence profile: 'signoff' (nghiệm thu — evidence cả khi PASS) | 'ci' (chạy lặp)
const PROFILE = process.env.UAT_PROFILE || 'signoff';
const IS_SIGNOFF = PROFILE === 'signoff';

export default defineConfig({
  testDir: './tests',

  timeout: 30_000,
  expect: { timeout: 10_000 },

  // Parallel-safe nhờ unique-data-per-test (namespace per worker) — KHÔNG tắt parallel
  fullyParallel: true,
  workers: process.env.CI ? 4 : 2,       // cap load trên staging chung
  forbidOnly: !!process.env.CI,
  // SIGN-OFF: retries 0 — pass-nhờ-retry không phải pass nghiệm thu
  retries: IS_SIGNOFF ? 0 : 2,
  // Playwright >=1.52: fail run nếu có test flaky (chỉ có nghĩa khi retries > 0)
  ...(IS_SIGNOFF ? {} : { failOnFlakyTests: false }),

  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['line'],
    ['./tests/helpers/excelReporter.ts'],
    ['json', { outputFile: 'test-results/raw-results.json' }],
    // Khi shard: thay html bằng ['blob'] rồi `npx playwright merge-reports`
  ],
  // >=1.51: gắn build SHA vào report — traceability sign-off
  captureGitInfo: { commit: true },

  use: {
    baseURL: BASE_URL,
    // 2 evidence profile
    trace:      IS_SIGNOFF ? 'on' : 'on-first-retry',
    screenshot: IS_SIGNOFF ? 'on' : 'only-on-failure',
    video:      IS_SIGNOFF ? 'on' : 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
    // Giảm flake do animation
    reducedMotion: 'reduce',
    // KHÔNG bypassCSP / ignoreHTTPSErrors mặc định — UAT phải giống production.
    // Chỉ bật khi user xác nhận dev env, và ghi chú vào report.
  },

  projects: [
    // Gate 1 — API smoke (không browser)
    { name: 'api-smoke',
      testMatch: '**/*.api.spec.ts',
      use: { baseURL: API_BASE_URL } },

    // Auth setup — login 1 lần mỗi role, lưu storageState
    { name: 'setup',
      testMatch: '**/auth.setup.ts',
      dependencies: ['api-smoke'] },      // smoke đỏ → setup + e2e SKIP (gate cứng, ĐÚNG semantics)

    // Gate 2 — E2E Chromium
    { name: 'e2e-chromium',
      testMatch: '**/*.e2e.spec.ts',
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'],
             viewport: { width: 1440, height: 900 },
             storageState: '.auth/user.json' } },

    // Cleanup — teardown project: LUÔN chạy kể cả khi test fail (đáng tin hơn afterAll)
    { name: 'cleanup',
      testMatch: '**/global.teardown.ts',
      teardown: undefined },
  ],

  // Tự khởi động app thật khi chưa chạy (KHÔNG mock thay app — không lên được → NO-RUN)
  webServer: process.env.START_DEV === '1' ? {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 60_000,
  } : undefined,
});
```

> **Ghi chú teardown đúng chuẩn**: cách chính tắc là khai `teardown: 'cleanup'` NGAY TRONG project `setup` (`{ name: 'setup', testMatch: ..., teardown: 'cleanup' }`) và project `cleanup` chỉ cần `testMatch` — Playwright sẽ chạy cleanup sau khi mọi dependent kết thúc, kể cả fail. Sinh config theo cách đó khi Playwright ≥1.34.

## Auth setup — login 1 lần/role

```typescript
// tests/setup/auth.setup.ts
import { test as setup, expect } from '@playwright/test';
import { credentials } from '../fixtures/credentials';

setup('đăng nhập role user — lưu storageState', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(credentials.email);
  await page.getByLabel(/mật khẩu|password/i).fill(credentials.password);
  await page.getByRole('button', { name: /đăng nhập|login/i }).click();
  // Web-first assertion — chờ đúng trạng thái đăng nhập xong, không networkidle
  await expect(page.getByTestId('user-menu')).toBeVisible();
  await page.context().storageState({ path: '.auth/user.json' });
});
```

## Fixture composition — page objects inject qua fixture

```typescript
// tests/fixtures/index.ts
import { test as base, expect, mergeTests } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { dataTest } from './data.fixture';

type PageFixtures = { loginPage: LoginPage };

const pagesTest = base.extend<PageFixtures>({
  loginPage: async ({ page }, use) => { await use(new LoginPage(page)); },
});

// Gộp fixture modules — spec chỉ import 1 chỗ
export const test = mergeTests(pagesTest, dataTest);
export { expect };
```

```typescript
// tests/fixtures/data.fixture.ts — worker-scoped, seed qua API, cleanup LIFO
import { test as base } from '@playwright/test';

type DataFixtures = { dataNamespace: string };

export const dataTest = base.extend<DataFixtures, { workerNamespace: string }>({
  workerNamespace: [async ({}, use, workerInfo) => {
    // Namespace duy nhất per worker — parallel-safe, không đụng data nhau
    const ns = `uat-w${workerInfo.workerIndex}-${Date.now().toString(36)}`;
    const created: Array<{ type: string; id: string }> = [];
    await use(ns);
    // Cleanup LIFO đúng ID đã capture (tôn trọng FK) — CẤM DELETE WHERE LIKE
    for (const item of created.reverse()) {
      // await api.delete(`/${item.type}/${item.id}`)
    }
  }, { scope: 'worker' }],
  dataNamespace: async ({ workerNamespace }, use) => { await use(workerNamespace); },
});
```

## API spec template (Gate 1)

```typescript
// tests/api/login.api.spec.ts
import { test, expect } from '@playwright/test';
import { credentials } from '../fixtures/credentials';

test.describe('Login API — Gate 1 smoke', () => {
  test('TC-001-API: Đăng nhập thành công @P0 @GREEN @TC-001', async ({ request }) => {
    const response = await request.post('/api/auth/login', {
      data: { email: credentials.email, password: credentials.password },
    });
    // Oracle: theo rule AUTH-LOGIN (uat.json oracle_source) — không chỉ status
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('token');
    expect(body.user).toHaveProperty('email', credentials.email);
  });

  test('TC-005-API: SQL injection bị reject có kiểm soát @P0 @SECURITY @TC-005', async ({ request }) => {
    const response = await request.post('/api/auth/login', {
      data: { email: "' OR '1'='1", password: 'x' },
    });
    expect(response.status()).toBe(400);
    expect(JSON.stringify(await response.json())).not.toMatch(/sql|database|exception/i);
  });
});
```

## E2E spec template (Gate 2) — test.step 1:1 bước TC + expect.soft

```typescript
// tests/e2e/login.e2e.spec.ts
import { test, expect } from '../fixtures';
import { credentials } from '../fixtures/credentials';

test.describe('Login E2E — Gate 2 UI', () => {
  test('TC-001-E2E: Đăng nhập thành công @P0 @GREEN @TC-001 @journey-auth',
      async ({ page, loginPage }) => {
    await test.step('TC-001.1 — Mở trang login, form hiển thị', async () => {
      await loginPage.goto();
      await expect(loginPage.emailInput).toBeVisible();
    });

    await test.step('TC-001.2 — Nhập thông tin hợp lệ và submit', async () => {
      await loginPage.login(credentials.email, credentials.password);
    });

    await test.step('TC-001.3 — Vào dashboard, hiển thị đúng user', async () => {
      // ≥3 UI assertion: URL + visibility + text; expect.soft để thấy MỌI sai lệch 1 lần chạy
      await expect(page).toHaveURL(/\/dashboard/);
      await expect.soft(page.getByRole('heading', { name: /chào mừng|welcome/i })).toBeVisible();
      await expect.soft(page.getByTestId('user-menu')).toContainText(credentials.email);
    });
  });

  test('TC-002-E2E: Email trống hiển thị validation @P0 @RED @TC-002',
      async ({ page, loginPage }) => {
    await loginPage.goto();
    await loginPage.login('', 'something');
    await expect(page).toHaveURL(/\/login/);                                  // không navigate
    await expect.soft(page.getByText(/email.*bắt buộc|required/i)).toBeVisible(); // lỗi hiển thị
    await expect.soft(loginPage.submitButton).toBeEnabled();                  // không kẹt loading
  });
});
```

## Page object — locator user-facing, KHÔNG smart-CSS-array

```typescript
// tests/pages/LoginPage.ts
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;

  constructor(private page: Page) {
    // Ưu tiên: getByRole/getByLabel (đúng cách EU nhìn thấy UI + ép a11y đúng) → getByTestId
    this.emailInput = page.getByLabel(/email/i).or(page.getByTestId('email'));
    this.passwordInput = page.getByLabel(/mật khẩu|password/i).or(page.getByTestId('password'));
    this.submitButton = page.getByRole('button', { name: /đăng nhập|login/i });
  }

  async goto() {
    await this.page.goto('/login');
    // Web-first: chờ đúng element sẵn sàng — KHÔNG waitForLoadState('networkidle')
    await this.emailInput.waitFor();
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}
```

> Không tìm được locator user-facing ổn định → đó là **testability defect** (đề xuất thêm `data-testid`), không phải chỗ để viết CSS chain `'[data-testid=x], input[type=y]'`.

## A11y scan per page-state (TC A11Y)

```typescript
import AxeBuilder from '@axe-core/playwright';  // page.accessibility đã BỊ XOÁ từ 1.57

await test.step('A11y: trang login (default + error state)', async () => {
  const scan = async (label: string) => {
    const res = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze();
    expect.soft(res.violations, `axe violations @ ${label}`).toEqual([]);
    // res.incomplete PHẢI triage — attach vào report, không im lặng bỏ
    test.info().attach(`axe-incomplete-${label}`, { body: JSON.stringify(res.incomplete), contentType: 'application/json' });
  };
  await scan('default');
  await loginPage.login('', '');          // mở error state rồi scan lại
  await scan('error-state');
});
```

## Custom reporter (excelReporter.ts) — giữ nguyên logic layer-aware; bổ sung field `triage_label`, `platform`, `retry_count` (pass-on-retry → đánh dấu flaky/AMBER).

## Naming convention

| Loại spec | File pattern | Title pattern |
|-----------|---------------|----------------|
| API smoke | `*.api.spec.ts` | `TC-XXX-API: ...` + tag `@TC-XXX` |
| UI E2E | `*.e2e.spec.ts` | `TC-XXX-E2E: ...` + tag `@TC-XXX @P0 @journey-*` |
| Mobile | `.maestro/<f>/TC-XXX.yaml` | JUnit name = `TC-XXX` |

## Chạy lệnh

```bash
npx playwright test --project=api-smoke        # Gate 1
npx playwright test --project=e2e-chromium     # Gate 2 (tự chạy setup theo dependencies)
npx playwright test --grep "@P0"               # theo risk tag
npx playwright test --grep "@TC-001"           # 1 TC
npx playwright test --last-failed              # retest scope=verify (>=1.44)
UAT_PROFILE=ci npx playwright test             # profile CI
npx playwright merge-reports --reporter=html ./all-blob-reports   # khi shard
```
