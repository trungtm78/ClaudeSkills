# UI E2E Assertion Patterns — Bắt buộc cho Layer 2

## Triết lý

E2E test phải **act như real user** — không call API trực tiếp. Mọi verify đi qua DOM/UI:
- User CLICK button → assertion: page navigate, modal open, element visible
- User FILL form → assertion: validation message, button state, server response qua UI
- User scroll → assertion: lazy-loaded content xuất hiện

## Mỗi TC E2E PHẢI có ≥3 assertion

3 loại assertion bắt buộc:

1. **Navigation/URL assertion** — `await expect(page).toHaveURL(...)`
2. **Visual element assertion** — `await expect(...).toBeVisible()`
3. **Content/text assertion** — `await expect(...).toContainText(...)` hoặc `toHaveText`

Lý do: 1 assertion không đủ tin cậy. Vd: navigate đến /dashboard nhưng dashboard trắng tinh do JS lỗi → assertion duy nhất "URL match" sẽ false-positive PASS.

## Cấu trúc test hiện đại (BẮT BUỘC với spec sinh mới)

1. **`test.step()` map 1:1 bước TC** — title `"TC-xx.N — <expected của bước>"`; fail trace chỉ thẳng bước nào của TC.
2. **`expect.soft()` cho CỤM assertion trong 1 step** (thấy mọi sai lệch trong 1 lần chạy); `expect()` cứng cho precondition chặn bước sau.
3. **Locator ưu tiên user-facing** (đúng cách End User nhìn): `getByRole` → `getByLabel` → `getByText` → `getByTestId` → CSS. Cấm XPath/nth-child.
4. **Expected value phải trace về uat.json** — không tự chế giá trị từ "trí nhớ"; 1 TC nguồn = đúng 1 `test()`.
5. **`toMatchAriaSnapshot()`** cho structural regression của màn hình quan trọng; **axe scan per page-state** cho TC A11Y (mở modal/error state rồi scan lại — xem `playwright-config.md`).
6. **Cấm `if` trong test** (Conditional Logic smell — 2 nhánh không được test); cấm assert giá trị vừa set vào (tautology).

## 7 categories of UI Assertion

### 1. Visibility & Existence

```typescript
// Element hiện diện trong DOM và visible
await expect(page.locator('h1')).toBeVisible();
await expect(page.getByRole('button', { name: 'Submit' })).toBeVisible();

// Element KHÔNG visible (hide/remove)
await expect(page.locator('.error-banner')).toBeHidden();
await expect(page.locator('.spinner')).toHaveCount(0);

// Element exists trong DOM nhưng có thể hidden (vd: aria-hidden)
await expect(page.locator('[data-testid="hidden-input"]')).toBeAttached();
```

### 2. Text Content

```typescript
// Exact text
await expect(page.locator('h1')).toHaveText('Đăng nhập');

// Contains substring (more flexible)
await expect(page.locator('h1')).toContainText('Đăng nhập');

// Regex pattern
await expect(page.locator('.welcome')).toHaveText(/chào mừng .+/i);

// Text trong nhiều elements
await expect(page.locator('.menu-item')).toHaveText(['Trang chủ', 'Sản phẩm', 'Liên hệ']);
```

### 3. URL & Navigation

```typescript
// Exact URL
await expect(page).toHaveURL('https://app.com/dashboard');

// Pattern (recommended)
await expect(page).toHaveURL(/\/dashboard$/);
await expect(page).toHaveURL(/\/user\/\d+/);

// Title
await expect(page).toHaveTitle(/Trang chủ/);

// Wait for navigation explicit
await page.waitForURL(/\/dashboard/);
```

### 4. Form State

```typescript
// Input value
await expect(page.locator('input[name="email"]')).toHaveValue('alice@test.com');

// Empty input
await expect(page.locator('input[name="password"]')).toBeEmpty();

// Checkbox state
await expect(page.locator('input[name="remember"]')).toBeChecked();
await expect(page.locator('input[name="terms"]')).not.toBeChecked();

// Disabled / Enabled
await expect(page.locator('button[type="submit"]')).toBeEnabled();
await expect(page.locator('button[type="submit"]')).toBeDisabled();

// Focused
await expect(page.locator('input[name="email"]')).toBeFocused();
```

### 5. Validation Messages

```typescript
// HTML5 validation
const emailInput = page.locator('input[type="email"]');
await expect(emailInput).toHaveAttribute('aria-invalid', 'true');

// Custom error message
await expect(page.locator('.field-error')).toContainText('Email không hợp lệ');

// Error appears near specific field
const emailGroup = page.locator('.form-group:has(input[name="email"])');
await expect(emailGroup.locator('.error')).toBeVisible();
await expect(emailGroup.locator('.error')).toContainText(/bắt buộc|required/i);

// Toast/Snackbar
await expect(page.locator('[role="alert"]')).toContainText('Đăng nhập thành công');
```

### 6. Loading States

```typescript
// Spinner visible khi submit
await page.click('button[type="submit"]');
await expect(page.locator('.spinner')).toBeVisible();

// Spinner disappears after load
await expect(page.locator('.spinner')).toBeHidden({ timeout: 10_000 });

// Button text changes during loading
await page.click('button[type="submit"]');
await expect(page.locator('button[type="submit"]')).toHaveText('Đang xử lý...');
```

### 7. Style & Attribute

```typescript
// CSS property
await expect(page.locator('.error')).toHaveCSS('color', 'rgb(220, 38, 38)');

// Class
await expect(page.locator('button')).toHaveClass(/active/);

// Attribute
await expect(page.locator('a.download')).toHaveAttribute('href', '/files/report.pdf');

// Data attribute
await expect(page.locator('[data-status]')).toHaveAttribute('data-status', 'success');

// Element count
await expect(page.locator('.todo-item')).toHaveCount(5);
```

## Pattern theo TC type

### GREEN — Happy path

```typescript
test('TC-001-E2E: Đăng nhập thành công', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="email"]', 'alice@test.com');
  await page.fill('[data-testid="password"]', 'Valid@123');
  await page.click('button[type="submit"]');
  
  // 3 assertions
  await expect(page).toHaveURL(/\/dashboard/);              // 1. Navigation
  await expect(page.getByText(/chào mừng/i)).toBeVisible(); // 2. Welcome msg
  await expect(page.locator('[data-testid="user-menu"]'))   // 3. Logged-in UI
    .toBeVisible();
});
```

### RED — Negative path

```typescript
test('TC-002-E2E: Email empty hiện validation', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="email"]', '');
  await page.fill('[data-testid="password"]', 'something');
  await page.click('button[type="submit"]');
  
  // 3 assertions
  await expect(page).toHaveURL(/\/login/);                     // 1. Stay on page
  await expect(page.locator('.field-error'))                   // 2. Error visible
    .toContainText(/email.*bắt buộc/i);
  await expect(page.locator('button[type="submit"]'))          // 3. Button enabled
    .toBeEnabled();
});
```

### BOUNDARY

```typescript
test('TC-003-E2E: Password 7 ký tự (min-1) bị reject', async ({ page }) => {
  await page.goto('/register');
  await page.fill('[data-testid="email"]', 'new@test.com');
  await page.fill('[data-testid="password"]', 'Pas@12!');  // 7 chars
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL(/\/register/);                   // 1. Stay
  await expect(page.locator('.password-strength'))              // 2. Strength meter
    .toContainText(/yếu|weak/i);
  await expect(page.locator('.field-error[data-for="password"]')) // 3. Inline error
    .toContainText(/ít nhất 8/i);
});
```

### SECURITY

```typescript
test('TC-005-E2E: SQL injection không bypass + không leak', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="email"]', "' OR '1'='1");
  await page.fill('[data-testid="password"]', 'x');
  await page.click('button[type="submit"]');
  
  // 4 assertions cho SECURITY (nghiêm ngặt hơn)
  await expect(page).toHaveURL(/\/login/);                      // 1. Không bypass
  
  const errorText = await page.locator('[role="alert"]').textContent();
  expect(errorText).not.toMatch(/sql|syntax|exception|stack/i); // 2. Không leak
  
  await expect(page.locator('[role="alert"]')).toContainText(/không hợp lệ|invalid/i); // 3. Generic msg
  
  // 4. Trang vẫn render đầy đủ (không crash)
  await expect(page.locator('[data-testid="email"]')).toBeVisible();
});
```

### A11Y

```typescript
test('TC-006-E2E: Keyboard navigation đầy đủ', async ({ page }) => {
  await page.goto('/login');
  
  // Tab qua các field theo thứ tự
  await page.keyboard.press('Tab');
  await expect(page.locator('[data-testid="email"]')).toBeFocused();   // 1.
  
  await page.keyboard.press('Tab');
  await expect(page.locator('[data-testid="password"]')).toBeFocused(); // 2.
  
  await page.keyboard.press('Tab');
  await expect(page.locator('button[type="submit"]')).toBeFocused();    // 3.
  
  // Enter submit
  await page.fill('[data-testid="email"]', 'alice@test.com');
  await page.fill('[data-testid="password"]', 'Valid@123');
  await page.locator('button[type="submit"]').focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/dashboard/);  // 4. Submit hoạt động qua keyboard
});
```

### STATE

```typescript
test('TC-XXX-E2E: User Pending không login được', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="email"]', 'pending@test.com');
  await page.fill('[data-testid="password"]', 'Pending@123');
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL(/\/login/);                            // 1.
  await expect(page.locator('[role="alert"]'))                        // 2.
    .toContainText(/xác thực email|verify your email/i);
  await expect(page.getByRole('button', { name: /gửi lại email/i })) // 3. CTA verify
    .toBeVisible();
});
```

### DATA / i18n

```typescript
test('TC-008-E2E: Họ tên tiếng Việt có dấu', async ({ page }) => {
  await page.goto('/register');
  await page.fill('[data-testid="email"]', 'nguyendat@test.com');
  await page.fill('[data-testid="full_name"]', 'Nguyễn Văn Đạt');
  await page.fill('[data-testid="password"]', 'Valid@123');
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL(/\/email-sent/);                      // 1.
  await expect(page.locator('[data-testid="user-name-display"]'))    // 2. Tên render đúng
    .toHaveText('Nguyễn Văn Đạt');
  // Không bị mangled encoding
  await expect(page.locator('body'))                                 // 3.
    .not.toContainText(/Nguy\?n V\?n/);
});
```

## ⚠️ ANTI-PATTERNS trong E2E

### ❌ Anti-pattern 1: Call API trực tiếp trong E2E
```typescript
// ❌ KHÔNG
test('TC-001-E2E: Login', async ({ page, request }) => {
  const response = await request.post('/api/login', { ... });
  expect(response.status()).toBe(200);
});
```
→ Đây là API test, không phải E2E. Dùng layer API thay vì.

### ❌ Anti-pattern 2: Chỉ 1 assertion
```typescript
// ❌ KHÔNG đủ
test('TC-001', async ({ page }) => {
  await loginPage.login('alice', 'Valid@123');
  await expect(page).toHaveURL(/\/dashboard/);  // Chỉ 1 assertion!
});
```
→ Có thể false-positive (page navigate nhưng blank). Cần ≥3 assertion.

### ❌ Anti-pattern 3: Hard wait
```typescript
// ❌ KHÔNG
await page.click('button');
await page.waitForTimeout(3000);  // Magic number
await expect(page.locator('.result')).toBeVisible();
```
→ Flaky. Dùng auto-wait của Playwright (`expect().toBeVisible()` tự retry).

### ❌ Anti-pattern 4: Test runs in order dependency
```typescript
// ❌ KHÔNG
test('TC-001: Login', async ({ page }) => { /* logged in */ });
test('TC-002: Goto profile', async ({ page }) => {
  // Phụ thuộc TC-001 đã login → khi chạy isolated sẽ fail
  await page.goto('/profile');
});
```
→ Mỗi test phải tự setup state. Dùng `beforeEach` để login lại hoặc dùng storageState.

### ❌ Anti-pattern 5: Check screenshot pixel-perfect cho mọi test
```typescript
// ❌ Quá nghiêm ngặt
await expect(page).toHaveScreenshot();
```
→ Chỉ dùng cho visual regression cụ thể, không cho mọi TC. Dễ flaky do font/animation.

## Multi-step E2E pattern

```typescript
test('TC-100-E2E: Full checkout flow', async ({ page }) => {
  // Step 1: Login
  await loginPage.goto();
  await loginPage.login('alice@test.com', 'Valid@123');
  await expect(page).toHaveURL(/\/dashboard/);
  
  // Step 2: Add to cart
  await productPage.goto('PRD-001');
  await productPage.clickAddToCart();
  await expect(page.locator('[data-testid="cart-badge"]')).toHaveText('1');
  
  // Step 3: Checkout
  await cartPage.goto();
  await cartPage.clickCheckout();
  await expect(page).toHaveURL(/\/checkout/);
  
  // Step 4: Fill shipping
  await checkoutPage.fillShipping({
    address: '123 Phố Huế',
    city: 'Hà Nội',
    phone: '0901234567',
  });
  await expect(page.locator('[data-testid="shipping-summary"]'))
    .toContainText('123 Phố Huế');
  
  // Step 5: Submit + verify
  await checkoutPage.clickPay();
  await expect(page).toHaveURL(/\/order\/confirmation/);
  await expect(page.locator('h1')).toContainText(/đặt hàng thành công/i);
  await expect(page.locator('[data-testid="order-id"]')).toBeVisible();
});
```

## Tóm tắt — 3-assertion rule

Mọi E2E test PHẢI có **≥3 assertion** đa dạng:

| Assertion type | Mục đích |
|----------------|---------|
| Navigation/URL | Verify routing hoạt động |
| Visibility | Verify element render |
| Content/Text | Verify nội dung đúng (không blank) |

Nếu chỉ verify được 1-2 → bổ sung thêm: check button state, check counter, check toast, check class active...
