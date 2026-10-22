# GĐ 3.5 — Sinh Data Factory (bước CÓ ĐIỀU KIỆN)

> Chỉ chạy khi `uat.json` có `data_fixtures`. Tách khỏi `SKILL.md` vì phần lớn lượt chạy không cần tới nó — nạp khi cần.

### GĐ 3.5: Sinh Data Factory (nếu UAT có data_fixtures)

Nếu UAT file có sheet "Data Matrix" với fixtures, BẮT BUỘC sinh `tests/fixtures/data-factory.ts`:

```bash
python "$SKILL_SCRIPTS/generate_data_factory.py" /tmp/uat_data.json \
  -o tests/fixtures/data-factory.ts
```

Script tự động sinh các function:
- `setupUserActiveD30(ctx)`, `setupUserPendingD0(ctx)`, ... (cho mỗi fixture)
- `cleanupUserActiveD30(ctx)`, ... (cleanup tương ứng)
- `setupFixtures([fid1, fid2])` — batch setup helper
- `cleanupFixtures([fid1, fid2], ctx)` — batch cleanup

Template variables được resolve runtime:
- `{{random}}` → `randomHex()` (8 chars hex)
- `{{D+N}}` / `{{D-N}}` → ISO date offset
- `{{user_id}}` → `ctx.user_id` (cross-fixture reference)
- `{{env.VAR}}` → `process.env.VAR`

**Trong spec dùng**:

```typescript
import { setupFixtures, cleanupFixtures, FixtureCtx } from '../fixtures/data-factory';

test.describe('Login E2E', () => {
  let ctx: FixtureCtx;
  
  test.beforeEach(async () => {
    // Đọc data_required từ UAT TC, setup ngay trước test
    ctx = await setupFixtures(['user.pending.D0']);
  });
  
  test.afterEach(async () => {
    await cleanupFixtures(['user.pending.D0'], ctx);
  });
  
  test('TC-005-E2E: Pending user không login được', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="email"]', ctx.email);  // từ fixture
    await page.fill('[name="password"]', ctx['user.pending.D0'].password);
    await page.click('button[type="submit"]');
    
    await expect(page.locator('[role="alert"]'))
      .toContainText('Vui lòng verify email');
  });
});
```

**Lưu ý**: Runner sinh code spec PHẢI tự động đọc `data_required` field từ TC trong UAT file và inject setup/cleanup vào spec tương ứng.

