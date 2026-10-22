# Viết kịch bản cho uat-test-only

Nạp tệp này ở Bước 4 (viết kịch bản). Mọi luật dưới đây có một lý do: kịch bản do chính
người kiểm viết, nên nó là **chỗ lỗi dễ trốn nhất** — một assert yếu cho màu xanh mà không
kiểm gì. `guard_repo.py freeze-tests` bắt được một phần bằng máy; phần còn lại là luật này.

## 1. Mỗi test mang đúng một ID kế hoạch

```ts
test('TC-012 thu ngân đổi giá theo giờ vàng', { tag: ['@TC-012'] }, async ({ page }) => { … });
```

- Tag `@<tc_id>` là khoá gán kết quả (`merge_results.py` khớp tag trước, tiêu đề sau, và
  **luôn** khớp với danh sách kế hoạch — `TC-01` không bao giờ khớp `TC-011`).
- Một ca có thể có nhiều test (api + e2e); ca ĐẠT chỉ khi **mọi** test của nó đạt lần đầu.
- Test không khớp ID nào → mục "test không khớp ID" trong báo cáo, **không** được tính.

## 2. Tệp và dự án

| Loại ca (`platform`) | Tệp | Dự án Playwright |
|---|---|---|
| `api` | `<OUT>/tests/<tên>.api.spec.ts` (fixture `request`) | `api-smoke` |
| `web`, `hybrid-webview` | `<OUT>/tests/<tên>.e2e.spec.ts` | `e2e` |
| đăng nhập dùng chung | `<OUT>/tests/auth.setup.ts` → ghi `UAT_STORAGE_STATE` | `setup` |
| `cli` | `<OUT>/tests/cli/checks.json` (xem `run_cli_checks.py`) | — |
| `android`, `ios` | `<OUT>/.maestro/<tc_id>.yaml` (xem `mobile.md`) | — |

`baseURL` lấy từ biến `UAT_BASE_URL`; không viết cứng URL trong test.

## 3. Oracle: assert lấy từ "Kết quả mong đợi", không lấy từ app

**Mỗi assert giá trị phải có NEO ORACLE ở dòng ngay trên nó** — đây không còn là lời dặn,
`check_oracle_binding.py` (bước 4b) từ chối đóng băng nếu thiếu:

```ts
// oracle: TC-012 · "đơn chuyển REJECTED"
await expect(page.getByTestId('trang-thai')).toHaveText('REJECTED');
// oracle: TC-012 · "hiện số tiền 45.000"
await expect(page.getByTestId('tien')).toHaveText('45.000');
```

Chuỗi trong ngoặc kép phải **trích từ `expected` của ca** (so khớp sau khi bỏ dấu và gộp
khoảng trắng). Máy bắt được cả bốn kiểu gian:

| Gian | Máy nói gì |
|---|---|
| ca chỉ có `toBeVisible` | "không có assert GIÁ TRỊ nào — 'trang có tải' không phải là oracle" |
| neo ghi ca khác | "neo oracle ghi TC-A nhưng khối test là TC-B" |
| neo trích câu không có trong `expected` | "oracle phải đến từ yêu cầu, không đến từ app" |
| neo hứa `200` mà assert dùng `201`, hoặc assert đọc giá trị từ chính app | "neo oracle hứa giá trị 200 nhưng assert không dùng giá trị ấy" |

- **Cấm** mở app xem nó đang hiện gì rồi viết assert theo đó — đó là lấy sản phẩm đo chính
  nó, và mọi lỗi đang có sẽ được "chứng nhận đúng".
- Trinh sát DOM (mở trang, đọc `page.getByRole(...)`/aria snapshot) **chỉ để tìm locator**,
  không để tìm kết quả mong đợi.
- `expected` mơ hồ, không viết được assert đo được → **đừng bịa**: bỏ trống test của ca ấy;
  ca sẽ thành KHÔNG CHẠY (`khong-co-kich-ban`) và báo cáo nói rõ vì sao. Bịa một neo oracle
  cho qua cổng còn tệ hơn để trống, vì nó biến một chỗ trống thành một lời khẳng định sai.

Tối thiểu cho một test E2E: URL/màn đúng · phần tử kết quả hiện ra · **giá trị** đúng như
mong đợi. Một assert "trang có tải" không đủ.

## 4. Locator hướng người dùng

Thứ tự: `getByRole` → `getByLabel` → `getByText` → `getByPlaceholder` → `getByTestId`.
CSS/XPath chỉ khi không còn cách nào, và ghi chú lý do. `locator_hint` của ca là gợi ý,
không phải mệnh lệnh.

## 5. Chờ theo trạng thái, không chờ theo giờ

Dùng assert web-first (`await expect(x).toHaveText(...)`) — nó tự chờ. Cấm `waitForTimeout`.
Không nới `timeout` của từng test để "cho qua".

## 6. Bị cấm — guard từ chối đóng băng nếu gặp

| Mẫu | Vì sao |
|---|---|
| `test.skip(` `describe.skip(` `.fixme(` | bỏ qua ca = báo cáo thiếu mà trông như đủ |
| `test.fail(` | đảo nghĩa đạt/không đạt |
| `.only(` | chỉ chạy một phần bộ |
| `force: true` | bấm xuyên lớp phủ — che đúng lỗi giao diện người dùng gặp |
| `waitForTimeout(` `test.slow(` | chờ mù / nới giờ |
| `route('**'` | giả mọi request của chính hệ đang kiểm |
| `expect(true).toBe(true)` | assert rỗng |

Mock chỉ được cho **bên thứ ba** khi ca khai `backend_policy: mocked-3p` kèm lý do.

## 6b. Bằng chứng phải có thật

Ca khai `evidence_required` (`screenshot-final`, `trace`, `video`, `har`…) thì hiện vật ấy
phải có thật trên đĩa và khác rỗng. `check_evidence.py` hạ mọi ca ĐẠT-mà-thiếu-hiện-vật
xuống KHÔNG CHẠY: một PASS không truy ngược được yêu cầu → kết quả thì không ký được.
Cấu hình mặc định đã bật `trace`/`screenshot`/`video`; đừng tắt.

## 7. Sau khi đóng băng

Kịch bản **bất biến**. Test đỏ vì locator sai, vì assert sai, vì bất cứ điều gì → vẫn là
đỏ, ghi vào báo cáo. Không "sửa cho khớp", không heal. Một lượt sau (lượt mới, thư mục
kết quả mới) mới được viết lại kịch bản — và báo cáo của lượt này vẫn giữ nguyên.

## 8. Dữ liệu mồi

Chỉ qua **API công khai** của app, trong `beforeEach`, và dọn trong `afterEach`. Ca đòi mồi
bằng SQL/snapshot DB → để trống test; ca thành KHÔNG CHẠY (`seeding-khong-ho-tro`).
Không bao giờ chạy trên production.
