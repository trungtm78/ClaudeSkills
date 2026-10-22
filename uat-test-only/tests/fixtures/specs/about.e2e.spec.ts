import { test, expect } from '@playwright/test';

test('TC-DEMO-004 trang giới thiệu hiện tiêu đề', { tag: ['@TC-DEMO-004'] }, async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Giới thiệu' }).click();
  await expect(page).toHaveURL(/\/about$/);
  // oracle: TC-DEMO-004 · "Giới thiệu"
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Giới thiệu');
});
