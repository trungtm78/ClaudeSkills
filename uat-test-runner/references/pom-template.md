# Page Object Model (POM) - Template chi tiết (bản fixture-composition)

Hướng dẫn sinh code POM chuẩn cho Playwright TypeScript. Đọc khi cần sinh class POM mới.

## Nguyên tắc POM (cập nhật 2025-2026)

1. **Mỗi screen/page = 1 class** trong `tests/pages/`
2. **Class không assert** — assertion ở trong spec file
3. **Page object INJECT QUA FIXTURE, không `new` trong test** — khai báo trong `tests/fixtures/index.ts` (`test.extend` + `mergeTests`); spec nhận `{ loginPage }` từ fixture. Xem `playwright-config.md` §Fixture composition.
4. **Locator ưu tiên user-facing**: `getByRole` → `getByLabel` → `getByText` → `getByTestId` → CSS cuối cùng. ⛔ CẤM XPath, `nth-child`, CSS-chain-array kiểu `'[data-testid=x], input[type=y]'` — không tìm được locator ổn định = TESTABILITY DEFECT (đề xuất thêm data-testid), không phải chỗ chồng selector.
5. **Locator là property readonly**, expose method có nghĩa nghiệp vụ (theo hành động của End User)
6. **Không expose Page object** ra spec — chỉ expose action methods + locator cần assert

## Template BasePage (parent class)

```typescript
// tests/pages/BasePage.ts
import { Page, Locator, expect } from '@playwright/test';

/**
 * Base class cho tất cả Page Objects.
 * Chứa common methods mà mọi page đều dùng.
 */
export abstract class BasePage {
  protected page: Page;
  protected url: string;

  constructor(page: Page, url: string = '/') {
    this.page = page;
    this.url = url;
  }

  /**
   * Điều hướng tới page này.
   */
  async goto(): Promise<void> {
    await this.page.goto(this.url);
    await this.waitForReady();
  }

  /**
   * Chờ page sẵn sàng — web-first: chờ ĐÚNG element đặc trưng của page.
   * KHÔNG dùng waitForLoadState('networkidle') — Playwright docs discourage
   * (flaky với app có polling/websocket/analytics). Override trong subclass
   * và chờ element cụ thể.
   */
  async waitForReady(): Promise<void> {
    await this.readyMarker.waitFor();   // subclass khai báo readyMarker (getByRole/getByTestId)
  }

  /**
   * Lấy URL hiện tại.
   */
  async getCurrentUrl(): Promise<string> {
    return this.page.url();
  }

  /**
   * Chụp screenshot với tên custom (cho debug).
   */
  async takeScreenshot(name: string): Promise<void> {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  }

  /**
   * Helper: chờ và verify text trong element.
   */
  protected async expectText(locator: Locator, expected: string | RegExp): Promise<void> {
    await expect(locator).toHaveText(expected);
  }

  /**
   * Helper: chờ và verify URL.
   */
  protected async expectUrl(pattern: string | RegExp): Promise<void> {
    await expect(this.page).toHaveURL(pattern);
  }
}
```

## Template LoginPage (example concrete)

```typescript
// tests/pages/LoginPage.ts
import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';
import { DashboardPage } from './DashboardPage';

export class LoginPage extends BasePage {
  // Locators - dùng readonly + assignment trong constructor
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;
  readonly forgotPasswordLink: Locator;
  readonly rememberMeCheckbox: Locator;

  constructor(page: Page) {
    super(page, '/login');

    // Ưu tiên data-testid > role > text > CSS
    this.emailInput = page.locator('[data-testid="email-input"]');
    this.passwordInput = page.locator('[data-testid="password-input"]');
    this.loginButton = page.getByRole('button', { name: 'Đăng nhập' });
    this.errorMessage = page.locator('[data-testid="error-message"]');
    this.forgotPasswordLink = page.getByRole('link', { name: 'Quên mật khẩu?' });
    this.rememberMeCheckbox = page.locator('[data-testid="remember-me"]');
  }

  // Action methods - tên rõ ý nghiệp vụ

  /**
   * Nhập email vào ô input.
   */
  async fillEmail(email: string): Promise<this> {
    await this.emailInput.fill(email);
    return this;
  }

  /**
   * Nhập password vào ô input.
   */
  async fillPassword(password: string): Promise<this> {
    await this.passwordInput.fill(password);
    return this;
  }

  /**
   * Tick checkbox "Remember me".
   */
  async checkRememberMe(): Promise<this> {
    await this.rememberMeCheckbox.check();
    return this;
  }

  /**
   * Click nút đăng nhập (không assert kết quả - assertion ở spec).
   */
  async clickLogin(): Promise<void> {
    await this.loginButton.click();
  }

  /**
   * Click link Quên mật khẩu, trả về ForgotPasswordPage để chain.
   */
  async clickForgotPassword(): Promise<void> {
    await this.forgotPasswordLink.click();
    // return new ForgotPasswordPage(this.page);
  }

  /**
   * Helper composite: thực hiện toàn bộ flow login với credentials cho trước.
   * Hữu ích khi cần login làm precondition cho test khác.
   */
  async loginAs(email: string, password: string): Promise<DashboardPage> {
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.clickLogin();
    return new DashboardPage(this.page);
  }

  /**
   * Lấy text của error message (cho assertion ở spec).
   */
  async getErrorText(): Promise<string> {
    return (await this.errorMessage.textContent()) || '';
  }

  /**
   * Check nút Login đang disabled hay không.
   */
  async isLoginButtonDisabled(): Promise<boolean> {
    return await this.loginButton.isDisabled();
  }
}
```

## Pattern locator - thứ tự ưu tiên

```typescript
// ✅ TỐT NHẤT: data-testid (stable, không phụ thuộc UI changes)
page.locator('[data-testid="submit-button"]')

// ✅ TỐT: role-based (accessibility-friendly)
page.getByRole('button', { name: 'Đăng nhập' })
page.getByRole('textbox', { name: 'Email' })
page.getByLabel('Email')

// ⚠️ OK: text-based (phụ thuộc i18n)
page.getByText('Đăng nhập')
page.locator('text="Đăng nhập"')

// ⚠️ TRÁNH: CSS class (dễ vỡ khi refactor)
page.locator('.login-button')
page.locator('#email')  // ID OK nếu stable

// ❌ TỆ: XPath (last resort)
page.locator('//div[@class="login"]//button[1]')
```

**Khi HTML chưa có data-testid:** đề xuất dev thêm, hoặc dùng combination:
```typescript
page.locator('form#login').getByRole('button', { name: 'Đăng nhập' })
```

## Pattern wait strategies

```typescript
// ✅ Chờ element appear
await expect(locator).toBeVisible();

// ✅ Chờ URL change
await expect(page).toHaveURL(/.*\/dashboard/);

// ❌ TRÁNH: networkidle — flaky với app có polling/websocket (docs discourage)
// await page.waitForLoadState('networkidle');
// ✅ THAY BẰNG: chờ element/URL cụ thể (2 pattern trên)

// ✅ Chờ response cụ thể
const responsePromise = page.waitForResponse('**/api/login');
await loginPage.clickLogin();
const response = await responsePromise;
expect(response.status()).toBe(200);

// ❌ TRÁNH: hard-coded wait
await page.waitForTimeout(3000);  // Flaky!
```

## Pattern fixtures (test data)

```typescript
// tests/fixtures/users.ts
export const testUsers = {
  valid: {
    email: process.env.TEST_USER_EMAIL || 'alice@test.com',
    password: process.env.TEST_USER_PASSWORD || 'Valid@123',
    name: 'Alice Nguyễn',
  },
  admin: {
    email: process.env.TEST_ADMIN_EMAIL || 'admin@test.com',
    password: process.env.TEST_ADMIN_PASSWORD || 'Admin@123',
    name: 'Admin',
  },
  locked: {
    email: 'locked@test.com',
    password: 'Valid@123',
  },
  invalid: {
    email: 'wrong@test.com',
    password: 'wrong_password',
  },
};

export const boundaryValues = {
  password: {
    belowMin: 'Pas@12!',         // 7 chars - fail
    atMin: 'Pas@123!',           // 8 chars - pass
    atMax: 'A'.repeat(127) + '@1', // 128 chars - pass
    aboveMax: 'A'.repeat(128) + '@1', // 129 chars - fail
  },
  email: {
    invalid: ['alice@', '@test.com', 'no-at-sign', '', '   '],
  },
};

export const securityPayloads = {
  sqlInjection: [
    "' OR '1'='1",
    "'; DROP TABLE users;--",
    "admin'--",
  ],
  xss: [
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>',
    '<svg/onload=alert(1)>',
  ],
};
```

## Pattern test spec đầy đủ

```typescript
// tests/specs/login.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { testUsers, boundaryValues, securityPayloads } from '../fixtures/users';

test.describe('Login Module', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  // ============================================================
  // GREEN - Happy Path
  // ============================================================
  test.describe('GREEN - Happy Path', () => {
    test('TC-001: Đăng nhập thành công với credential hợp lệ @P0 @smoke', async ({ page }) => {
      await loginPage.fillEmail(testUsers.valid.email);
      await loginPage.fillPassword(testUsers.valid.password);
      await loginPage.clickLogin();

      // Verify UI
      await expect(page).toHaveURL(/.*\/dashboard/);
      await expect(page.locator('[data-testid="user-name"]')).toHaveText(testUsers.valid.name);

      // Verify cookie (security)
      const cookies = await page.context().cookies();
      const sessionCookie = cookies.find(c => c.name === 'session');
      expect(sessionCookie).toBeDefined();
      expect(sessionCookie?.httpOnly).toBe(true);
      expect(sessionCookie?.secure).toBe(true);
    });
  });

  // ============================================================
  // RED - Negative cases
  // ============================================================
  test.describe('RED - Negative', () => {
    test('TC-002: Sai password @P0', async ({ page }) => {
      await loginPage.fillEmail(testUsers.valid.email);
      await loginPage.fillPassword('WrongPassword!');
      await loginPage.clickLogin();

      await expect(loginPage.errorMessage).toHaveText(/Email hoặc mật khẩu không đúng/);
      await expect(page).toHaveURL(/.*\/login/);  // Vẫn ở trang login
    });

    test('TC-003: Email không tồn tại @P0', async () => {
      await loginPage.fillEmail('notexist@test.com');
      await loginPage.fillPassword('AnyPassword123!');
      await loginPage.clickLogin();

      const errorText = await loginPage.getErrorText();
      // Quan trọng: error message KHÔNG tiết lộ email tồn tại hay không (chống enumeration)
      expect(errorText).toMatch(/Email hoặc mật khẩu không đúng/);
      expect(errorText).not.toContain('Email không tồn tại');
    });

    test('TC-004: Submit form trống @P0', async () => {
      await loginPage.clickLogin();
      // Validation client kích hoạt, không gọi API
      expect(await loginPage.isLoginButtonDisabled()).toBeFalsy();
      await expect(loginPage.errorMessage).toBeVisible();
    });
  });

  // ============================================================
  // BOUNDARY
  // ============================================================
  test.describe('BOUNDARY - Giá trị biên', () => {
    test('TC-010: Password 7 ký tự (dưới min) @P0', async () => {
      await loginPage.fillEmail(testUsers.valid.email);
      await loginPage.fillPassword(boundaryValues.password.belowMin);
      await loginPage.clickLogin();
      await expect(loginPage.errorMessage).toContainText('ít nhất 8 ký tự');
    });
  });

  // ============================================================
  // SECURITY
  // ============================================================
  test.describe('SECURITY - Bảo mật', () => {
    for (const payload of securityPayloads.sqlInjection) {
      test(`TC-SEC: SQL injection trong email - "${payload}" @P0 @security`, async ({ page }) => {
        const startTime = Date.now();

        await loginPage.fillEmail(payload);
        await loginPage.fillPassword('AnyPassword!');
        await loginPage.clickLogin();

        const responseTime = Date.now() - startTime;

        // Response time không vượt 1s (chống time-based SQLi)
        expect(responseTime).toBeLessThan(1000);

        // Không có data leak, không có SQL error
        const pageContent = await page.content();
        expect(pageContent).not.toMatch(/SQL|syntax error|table|database/i);

        // Vẫn ở trang login với error generic
        await expect(page).toHaveURL(/.*\/login/);
      });
    }
  });

  // ============================================================
  // PERFORMANCE
  // ============================================================
  test.describe('PERFORMANCE - Hiệu năng', () => {
    test('TC-PERF: Response time login < 2s @P1 @performance', async () => {
      await loginPage.fillEmail(testUsers.valid.email);
      await loginPage.fillPassword(testUsers.valid.password);

      const startTime = Date.now();
      await loginPage.clickLogin();
      // Chờ chuyển sang dashboard
      await loginPage.page.waitForURL(/.*\/dashboard/);
      const duration = Date.now() - startTime;

      expect(duration).toBeLessThan(2000);
      console.log(`✅ Login response time: ${duration}ms`);
    });
  });
});
```

## Mẹo refactor

- Khi 1 spec >300 lines → tách thành nhiều file theo loại TC.
- Khi 1 Page class >200 lines → tách thành sub-components (vd: `LoginForm.ts`, `LoginHeader.ts`).
- Common login → `tests/helpers/auth.ts` để reuse trong beforeEach của nhiều spec.
