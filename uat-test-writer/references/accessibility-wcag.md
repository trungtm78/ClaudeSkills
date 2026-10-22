# Accessibility Testing — WCAG 2.2 Level AA

Checklist chi tiết để viết A11Y test cases. Tuân thủ WCAG 2.2 Level AA là **bắt buộc về pháp lý** ở nhiều nước (ADA Mỹ, **EAA EU — enforceable từ 28/06/2025 qua EN 301 549**; sàn pháp lý hiện là WCAG 2.1 AA, **target kỹ thuật đúng = WCAG 2.2 AA** vì EN 301 549 v4.1.1 sẽ nhập 2.2). Bỏ qua = rủi ro kiện tụng + loại bỏ ~15% users.

> **WCAG 3.0 = awareness-only**: vẫn là Working Draft (scoring model, ~174 outcomes), Candidate Recommendation sớm nhất cuối 2027, không tool nào hỗ trợ — KHÔNG plan/claim conformance theo 3.0.

## ⭐ WCAG 2.2 — 9 tiêu chí MỚI so với 2.1 (phải kiểm thêm)
| SC | Mức | Kiểm |
|---|---|---|
| **2.4.11 Focus Not Obscured (Min)** | AA | Phần tử nhận focus KHÔNG bị che hoàn toàn (sticky header/footer/cookie banner). |
| 2.4.12 Focus Not Obscured (Enhanced) | AAA | …không bị che dù một phần. |
| 2.4.13 Focus Appearance | AAA | Vùng focus đủ to + tương phản. |
| **2.5.7 Dragging Movements** | AA | Mọi thao tác kéo-thả có cách thay thế single-pointer (nút/click). |
| **2.5.8 Target Size (Minimum)** | AA | Target chạm ≥ **24×24 CSS px** (hoặc có khoảng cách bù). |
| **3.2.6 Consistent Help** | A | Cơ chế trợ giúp (liên hệ/chat) ở vị trí NHẤT QUÁN giữa các trang. |
| **3.3.7 Redundant Entry** | A | Không bắt nhập lại thông tin đã nhập trong cùng quy trình (autofill/chọn lại). |
| **3.3.8 Accessible Authentication (Min)** | AA | KHÔNG bắt giải đố nhận thức (nhớ mật khẩu/CAPTCHA chữ) — cho copy-paste/quản lý mật khẩu. |
| 3.3.9 Accessible Authentication (Enhanced) | AAA | …không cả nhận diện đối tượng. |
> (Lưu ý: 4.1.1 Parsing đã **bị gỡ** trong 2.2.)

## 4 nguyên tắc WCAG (POUR)

| Nguyên tắc | Ý nghĩa | Test gì |
|------------|---------|---------|
| **P**erceivable | Cảm nhận được | Alt text, caption, contrast, text size |
| **O**perable | Vận hành được | Keyboard, time limit, navigation |
| **U**nderstandable | Hiểu được | Language, predictable, error help |
| **R**obust | Đa nền tảng | Valid HTML, ARIA correct |

## A. Test cases bắt buộc cho mọi feature

### A1. Keyboard Navigation

| TC | Test step | Expected |
|----|-----------|----------|
| 1 | Tab qua mọi interactive element theo thứ tự logic | Tab order trùng visual order |
| 2 | Shift+Tab quay lại | Đi ngược đúng |
| 3 | Tất cả button/link focus được bằng Tab | Có outline rõ ràng khi focus |
| 4 | Enter trên button = click | Trigger action |
| 5 | Space trên button = click | Trigger action |
| 6 | Esc đóng modal/dropdown | Đóng và return focus về trigger |
| 7 | Arrow key trên radio/select | Chọn được không cần chuột |
| 8 | Không có "keyboard trap" | Tab thoát ra được mọi element |
| 9 | Skip link "Skip to content" | Hoạt động + visible khi focus |
| 10 | Focus visible (outline ≥2px) | KHÔNG được `outline: none` |

**TC mẫu:**

```markdown
| TC-ID | TC-A11Y-001 |
|-------|-------------|
| **Loại** | A11Y |
| **Độ ưu tiên** | P0 |
| **Kỹ thuật test** | WCAG 2.2.1 Keyboard |
| **Tiêu đề** | Form đăng ký điều hướng đầy đủ bằng phím Tab |
| **Điều kiện tiên quyết** | 1. Trang `/register` đã load<br>2. Focus đang ở body |
| **Các bước kiểm thử** | 1. Nhấn Tab liên tục từ đầu trang<br>2. Quan sát focus indicator di chuyển qua từng element<br>3. Đếm số lần Tab để tới nút "Đăng ký"<br>4. Nhấn Shift+Tab để quay lại |
| **Kết quả mong đợi** | **UI:**<br>1. Focus indicator (outline) visible trên mọi element<br>2. Tab order: Logo → Menu → Email → Password → Confirm → Terms checkbox → Đăng ký button<br>3. Không có element nào "nhảy cóc" (focus order không logic)<br>4. Shift+Tab di chuyển ngược chính xác<br>5. Không có keyboard trap (Tab thoát ra được) |
| **Severity nếu fail** | High (S2) — vi phạm WCAG 2.2.1 |
```

### A2. Screen Reader Support

| TC | Test step | Expected |
|----|-----------|----------|
| 1 | Mọi ảnh có alt text | `<img alt="...">` không trống (trừ decorative thì `alt=""`) |
| 2 | Icon-only button có aria-label | `<button aria-label="Đóng">×</button>` |
| 3 | Input có label associated | `<label for="email">` hoặc `aria-label` |
| 4 | Heading hierarchy đúng (h1→h2→h3) | Không skip level |
| 5 | Landmark regions | `<header>`, `<nav>`, `<main>`, `<footer>` |
| 6 | Form error gắn với input | `aria-describedby` trỏ tới error message |
| 7 | Dynamic content announce | `aria-live="polite"` cho notification |
| 8 | Modal trap focus + announce | `role="dialog"`, `aria-modal="true"` |
| 9 | Loading state announce | `aria-busy="true"` khi load |
| 10 | Decorative element ẩn khỏi screen reader | `aria-hidden="true"` |

**Tool test:**
- NVDA (Windows, miễn phí)
- JAWS (Windows, có phí)
- VoiceOver (macOS/iOS, built-in)
- TalkBack (Android, built-in)
- Browser extension: axe DevTools, WAVE

### A3. Color Contrast (WCAG 1.4.3 AA)

| Element | Tỷ lệ tối thiểu |
|---------|------------------|
| Text thường (<18pt) | **4.5:1** |
| Text lớn (≥18pt hoặc ≥14pt bold) | **3:1** |
| UI component (button border, icon) | **3:1** |
| Focus indicator | **3:1** |

**TC mẫu:**

```markdown
| TC-ID | TC-A11Y-005 |
|-------|-------------|
| **Loại** | A11Y |
| **Độ ưu tiên** | P1 |
| **Kỹ thuật test** | WCAG 1.4.3 Contrast Minimum |
| **Tiêu đề** | Contrast ratio của text và button đạt WCAG AA |
| **Điều kiện tiên quyết** | Trang `/dashboard` load với theme mặc định |
| **Các bước kiểm thử** | 1. Mở Chrome DevTools → Lighthouse → Accessibility audit<br>2. Hoặc dùng tool axe DevTools<br>3. Đo contrast của: heading, body text, button label, link, placeholder text<br>4. Test cả light mode và dark mode (nếu có) |
| **Kết quả mong đợi** | 1. Body text contrast ≥ 4.5:1<br>2. Heading contrast ≥ 4.5:1<br>3. Button label/icon contrast ≥ 4.5:1<br>4. Focus indicator contrast ≥ 3:1<br>5. Lighthouse Accessibility score ≥ 95<br>6. axe DevTools: 0 contrast violation |
| **Severity nếu fail** | High (S2) |
```

### A4. Form Accessibility

| TC | Test |
|----|------|
| 1 | Input có visible label (không chỉ placeholder) |
| 2 | Required field có `aria-required="true"` và indicator visual |
| 3 | Error message gắn với input qua `aria-describedby` |
| 4 | Error xuất hiện ngay sau input lỗi (DOM order) |
| 5 | Submit fail: focus về input đầu tiên có lỗi |
| 6 | Autocomplete attributes (`autocomplete="email"`) |
| 7 | Input type đúng (`type="email"`, `type="tel"`, `type="number"`) |
| 8 | Group related input bằng `<fieldset>` + `<legend>` |

### A5. Zoom & Responsive

| TC | Test |
|----|------|
| 1 | Zoom 200% (Ctrl+Plus 6 lần) | Layout không vỡ, không cần scroll ngang |
| 2 | Zoom text-only 200% | Vẫn đọc được, không clip |
| 3 | Reflow ở viewport 320px width | Mobile-friendly, không scroll ngang |
| 4 | Text resize qua browser setting | Hoạt động |

### A6. Motion & Animation (WCAG 2.3.3, 2.2.2)

| TC | Test |
|----|------|
| 1 | `prefers-reduced-motion: reduce` | Animation tắt/giảm |
| 2 | Auto-play video/animation | Có nút pause |
| 3 | Animation chớp >3 lần/giây | KHÔNG được (gây co giật) |
| 4 | Carousel/slider auto-rotate | Có nút pause |

### A7. Time Limits (WCAG 2.2.1)

| TC | Test |
|----|------|
| 1 | Session timeout | Cảnh báo trước khi expire, cho extend |
| 2 | Form auto-save | Nếu timeout, data không mất |
| 3 | Countdown timer | Cho phép extend hoặc disable |

### A8. Language (WCAG 3.1.1, 3.1.2)

| TC | Test |
|----|------|
| 1 | `<html lang="vi">` | Khai báo đúng ngôn ngữ trang |
| 2 | Phần khác ngôn ngữ | `<span lang="en">English text</span>` |
| 3 | Text dịch | Hoàn toàn, không lẫn tiếng Anh không cần thiết |

### A9. Predictable Navigation (WCAG 3.2)

| TC | Test |
|----|------|
| 1 | Nav giống nhau ở mọi trang | Position, order consistent |
| 2 | Component giống nhau (vd: search box) | Hoạt động giống nhau ở mọi trang |
| 3 | Form không tự submit khi đổi field | User phải explicit submit |
| 4 | Focus không tự thay đổi context | (Trừ khi user explicit) |

### A10. Error Identification (WCAG 3.3)

| TC | Test |
|----|------|
| 1 | Error có icon + text (không chỉ màu đỏ) | Color-blind users vẫn thấy |
| 2 | Error specific, không generic | "Email phải có @" không phải "Sai" |
| 3 | Gợi ý cách sửa | "Định dạng: user@example.com" |
| 4 | Confirmation cho action quan trọng | Confirm trước khi xóa |

## B. Test cases theo component type

### B1. Modal/Dialog

- Focus chuyển vào modal khi mở
- Focus trap trong modal (Tab không thoát ra background)
- Esc đóng modal
- Click outside đóng (nếu spec yêu cầu)
- Focus return về trigger button khi đóng
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` trỏ về title

### B2. Dropdown / Combobox

- Arrow Down mở dropdown
- Arrow Up/Down navigate option
- Enter chọn option
- Esc đóng dropdown
- Type-ahead search
- `role="combobox"`, `aria-expanded`, `aria-activedescendant`

### B3. Toast / Notification

- `aria-live="polite"` cho info
- `aria-live="assertive"` cho error
- Đủ thời gian đọc (≥5s hoặc dismissible)
- Không auto-dismiss action button

### B4. Data Table

- `<th>` với `scope="col"` hoặc `scope="row"`
- `<caption>` mô tả bảng
- Sort indicator có `aria-sort`
- Pagination announce thay đổi

### B5. Tab/Tabpanel

- `role="tablist"`, `role="tab"`, `role="tabpanel"`
- Arrow Left/Right navigate tab
- Home/End đi đầu/cuối
- `aria-selected="true"` cho tab active
- `aria-controls` trỏ về tabpanel

## C. Audit tool checklist

Khi viết A11Y test case, yêu cầu chạy đủ các tool sau:

| Tool | Coverage |
|------|----------|
| **axe DevTools** (browser extension) | Automated check, 57% issues |
| **Lighthouse** (Chrome) | Score + recommendations |
| **WAVE** (browser extension) | Visual feedback |
| **NVDA + Chrome** | Screen reader actual test |
| **Keyboard only (no mouse)** | Manual nav test |
| **Color contrast analyzer** | Detailed contrast |

⚠️ **Lưu ý quan trọng (số liệu Deque xác nhận)**: axe-core bắt được **~57%** vấn đề WCAG của một audit điển hình — **~43% còn lại BẮT BUỘC kiểm thủ công**. Một run axe xanh KHÔNG PHẢI là conformance; báo cáo phải ghi rõ giới hạn này.

**Named manual checks cho 43% máy không bắt được** (liệt kê tường minh trong test plan, không được ngầm bỏ):
- Alt text có **thực sự mô tả đúng** không (máy chỉ biết có/không có alt)
- Focus order có **logic theo nghiệp vụ** không
- Caption/transcript có **chính xác nội dung** không
- Error message có **hữu ích, chỉ cách sửa** không
- Screen-reader traversal (NVDA/VoiceOver/TalkBack) tới được **mọi nội dung**
- Ngôn ngữ dễ hiểu, nhất quán thuật ngữ

**Quy tắc scan**: chạy axe **per page STATE** (modal mở, error hiển thị, menu expand, empty/loading state) — đa số violation nằm ở state mà 1 lần scan trang tĩnh không chạm tới. Kết quả `incomplete` của axe PHẢI được triage và disposition — im lặng bỏ `incomplete` là lỗi tích hợp phổ biến nhất. Widget 3rd-party có vi phạm → allow-list tường minh có ticket + time-box, KHÔNG hạ ngưỡng chung.

## D. Coverage tối thiểu cho A11Y trong UAT

Mỗi feature web app cần có **≥5 A11Y test cases**:

1. ✅ Keyboard navigation đầy đủ
2. ✅ Screen reader (NVDA/VoiceOver) đọc đúng
3. ✅ Color contrast WCAG AA
4. ✅ Form error accessible
5. ✅ Focus management (modal, dynamic content)

Cho feature phức tạp (dashboard, table, multi-step form): thêm:

6. Skip link
7. Heading hierarchy
8. Landmark regions
9. Zoom 200%
10. Reduced motion

## E. Severity của A11Y bug

| Vi phạm | Severity |
|---------|----------|
| Keyboard trap (không thoát được) | Critical (S1) |
| Form không submit được bằng keyboard | High (S2) |
| Screen reader không đọc được nội dung chính | High (S2) |
| Contrast text body < 4.5:1 | High (S2) |
| Thiếu alt text trên ảnh quan trọng | High (S2) |
| Focus không visible | Medium (S3) |
| Heading order skip | Medium (S3) |
| Decorative image có alt text thừa | Low (S4) |
