import { test, expect } from '@playwright/test';

test('TC-DEMO-002 health trả ok', { tag: ['@TC-DEMO-002'] }, async ({ request }) => {
  const r = await request.get('/api/health');
  // oracle: TC-DEMO-002 · "HTTP 200"
  expect(r.status()).toBe(200);
  expect(r.headers()['content-type']).toContain('application/json');
  expect(await r.json()).toEqual({ ok: true });
});
