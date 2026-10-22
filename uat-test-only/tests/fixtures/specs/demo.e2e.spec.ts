import { test, expect } from '@playwright/test';

test('TC-DEMO-001 bấm Tăng thì số lượng thành 1', { tag: ['@TC-DEMO-001'] }, async ({ page }) => {
  await test.step('mở trang chủ', async () => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });
  await test.step('bấm Tăng', async () => {
    await page.getByRole('button', { name: 'Tăng' }).click();
  });
  await test.step('ô số lượng hiện 1 (AC-1)', async () => {
    // oracle: TC-DEMO-001 · "Ô số lượng hiện 1"
    await expect(page.getByTestId('dem')).toHaveText('1');
  });
});

test('TC-DEMO-003 tiêu đề trang là Cửa hàng mẫu v2', { tag: ['@TC-DEMO-003'] }, async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/$/);
  // oracle: TC-DEMO-003 · "Cửa hàng mẫu v2"
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Cửa hàng mẫu v2');
});
