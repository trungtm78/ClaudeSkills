# Lỗi thường gặp khi chạy

> Tách từ `SKILL.md` để giảm lượng chữ phải nạp mỗi lần gọi skill. Nạp khi cần.

## Lỗi thường gặp

### 1. E2E test pass nhưng app render sai
→ E2E chỉ check URL. Bổ sung assertion text/visibility (≥3 rule).

### 2. API pass nhưng E2E fail
→ Đây là **frontend bug**. Bug được tạo với `[E2E]` tag.

### 3. API fail
→ E2E của TC đó tự skip (Playwright dependencies). Bug `[API]` tag.

### 4. Selector flaky
→ Đổi sang locator user-facing (`getByRole`/`getByLabel`) từ DOM thật; vẫn không có gì bám → testability defect (thêm data-testid), KHÔNG dùng CSS chain array.

### 5. Test timeout
→ KHÔNG dùng `waitForLoadState('networkidle')` (Playwright docs discourage — flaky với app polling/websocket). Dùng web-first assertion vào đúng element/state cần chờ: `await expect(page.getByRole('heading', { name: '...' })).toBeVisible()`. Timeout config chỉ tăng khi có căn cứ (thao tác thật sự chậm — kèm ghi chú perf).

### 6. App không chạy
→ Khởi động app thật (webServer/buildCmds). Không lên được → NO-RUN + remediation. KHÔNG mock thay app.

