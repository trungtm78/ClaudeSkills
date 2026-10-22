# Compatibility Testing Matrix

Hướng dẫn viết COMPAT test cases. Web app phải hoạt động trên đa nền tảng — bug compatibility là loại bug khó tái hiện nhất ở dev local.

## A. Browser Support Matrix (mặc định enterprise)

| Browser | Phiên bản | Priority | Lý do |
|---------|-----------|----------|-------|
| **Chrome** | Latest, Latest-1 | P0 | ~65% market share |
| **Safari** | Latest, Latest-1 | P0 | iOS + macOS bắt buộc |
| **Firefox** | Latest | P1 | ~3-5% nhưng technical user |
| **Edge** | Latest | P1 | Default Windows |
| **Samsung Internet** | Latest | P2 | Mobile Samsung |
| **IE 11** | - | P3 (chỉ nếu spec yêu cầu) | Enterprise legacy |
| **Opera** | Latest | P3 | Niche |

**Quy tắc:** Hỏi PO/client browser matrix ngay từ đầu. Nếu chưa rõ → assume P0-P1 ở trên.

## B. Device & Resolution Matrix

| Device class | Resolution | Priority |
|--------------|------------|----------|
| **Desktop FHD** | 1920x1080 | P0 |
| **Desktop HD** | 1366x768 | P0 |
| **Laptop** | 1440x900 | P1 |
| **Tablet landscape** | 1024x768 | P1 |
| **Tablet portrait** | 768x1024 | P1 |
| **Mobile L** | 414x896 (iPhone 11) | P0 |
| **Mobile M** | 375x667 (iPhone SE) | P0 |
| **Mobile S** | 320x568 (legacy) | P2 |
| **Ultra-wide** | 2560x1440, 3440x1440 | P2 |

## C. OS Matrix

| OS | Version | Browser hỗ trợ chính |
|----|---------|----------------------|
| Windows 11 | Latest | Chrome, Edge, Firefox |
| Windows 10 | Latest | Chrome, Edge, Firefox |
| macOS | Sonoma+ | Safari, Chrome, Firefox |
| iOS | 16+ | Safari, Chrome |
| Android | 12+ | Chrome, Samsung Internet |
| Linux Ubuntu | 22.04+ | Chrome, Firefox |

## D. Network Condition Matrix

| Loại mạng | Latency | Throughput | Test gì |
|-----------|---------|------------|---------|
| **Fast 4G** | 170ms | 9 Mbps | Default test |
| **Slow 3G** | 400ms | 400 Kbps | Loading state, timeout |
| **Offline** | - | - | Error message, retry |
| **Flaky** | varies | drops | Recovery handling |

DevTools → Network → Throttling để simulate.

## E. Test cases bắt buộc cho COMPAT

### Tối thiểu 5 TC compat cho mỗi feature

1. **TC-COMPAT-001**: Chrome desktop (latest, FHD) — Happy path
2. **TC-COMPAT-002**: Safari iOS mobile — Happy path
3. **TC-COMPAT-003**: Firefox desktop — Happy path
4. **TC-COMPAT-004**: Chrome Android — Touch interaction
5. **TC-COMPAT-005**: Tablet portrait — Layout responsive

### Mở rộng (nếu feature có UI phức tạp)

6. Edge desktop — Happy path
7. Safari macOS — Happy path
8. Resolution 1366x768 — Layout không vỡ
9. Resolution 320px — Layout không vỡ
10. Slow 3G — Loading state đúng

## F. TC mẫu cho COMPAT

```markdown
| TC-ID | TC-COMPAT-002 |
|-------|---------------|
| **Loại** | COMPAT |
| **Độ ưu tiên** | P0 |
| **Kỹ thuật test** | Compatibility testing - Cross browser |
| **Risk Level** | Cao |
| **Tiêu đề** | Form đăng ký hoạt động đúng trên Safari iOS mobile |
| **Điều kiện tiên quyết** | 1. iPhone 13 (iOS 17), Safari latest<br>2. Resolution 390x844<br>3. Mạng 4G stable |
| **Các bước kiểm thử** | 1. Mở Safari, truy cập `/register`<br>2. Tap vào ô Email — verify keyboard email-type xuất hiện<br>3. Nhập email, password, full name<br>4. Tap ô Date of Birth — verify native date picker xuất hiện<br>5. Tick Terms checkbox — verify tap area đủ lớn (≥44x44px)<br>6. Tap "Đăng ký"<br>7. Verify keyboard tự đóng khi submit |
| **Dữ liệu kiểm thử** | Email: alice@test.com<br>Password: Valid@123 |
| **Kết quả mong đợi** | **UI:**<br>1. Layout responsive đúng (không scroll ngang)<br>2. Tất cả button có touch target ≥44x44px<br>3. Keyboard iOS hiển thị đúng type (email keyboard cho email field, numeric cho phone)<br>4. Native iOS date picker (không phải custom)<br>5. Không có element bị che bởi keyboard<br>6. Tap delay <300ms<br>**API:**<br>7. POST /register thành công như desktop<br>**Side effects:**<br>8. Đăng ký thành công, user mới được tạo<br>9. Không có CSS render bug (font, color, spacing) |
| **Severity nếu fail** | Critical (S1) — iOS chiếm ≥50% mobile traffic |
```

## G. Pattern test thường gặp theo browser

### Safari-specific quirks (hay bug)

| Issue | Test |
|-------|------|
| Date input không support hoàn toàn | Format date display đúng |
| `position: sticky` khác Chrome | Sticky header hoạt động |
| Flexbox gap chưa support cũ | Layout không vỡ |
| `localStorage` ở Private mode | Graceful degradation |
| Cookie SameSite default khác | Login work |
| `<input type="number">` rendering | UX OK |
| Smooth scrolling | Hoạt động |

### Firefox-specific quirks

| Issue | Test |
|-------|------|
| File input styling khác Chrome | Upload UX OK |
| Print preview khác | Print page đúng |
| Mixed content blocking strict | HTTPS-only |

### Mobile-specific

| Issue | Test |
|-------|------|
| Viewport meta tag | Layout responsive |
| Touch event vs click | Tap delay |
| Virtual keyboard che input | Auto-scroll vào view |
| Pull-to-refresh | Không trigger ở giữa form |
| Network unstable | Retry logic |
| Battery low → animation off | Vẫn dùng được |
| Landscape ↔ Portrait | Layout reflow đúng |
| 3D touch / haptic | Optional but nice |
| Notch (iPhone X+) | Safe area inset |

### Tablet-specific

| Issue | Test |
|-------|------|
| Split screen (iPad) | Layout adapt |
| External keyboard | Shortcut work |
| Apple Pencil input | Signature pad work |
| Hover state (mouse-less) | Không stuck |

## H. Touch interaction (Mobile)

| Test | Expected |
|------|----------|
| Tap target ≥44x44px (Apple HIG) / ≥48x48dp (Material) | Đủ lớn |
| Tap delay <300ms | Không lag |
| Long press | Trigger context menu (nếu có) |
| Swipe (carousel, drawer) | Smooth |
| Pinch zoom | Allowed cho ảnh, disabled cho UI |
| Double-tap | Không zoom UI |
| Scroll momentum | Native feel |

## I. Print Stylesheet (nếu yêu cầu)

Một số feature cần print (invoice, receipt, report):

| Test | Expected |
|------|----------|
| Print preview hiển thị đúng | Layout không cần điều chỉnh |
| Background color preserved | (nếu nghiệp vụ cần) |
| Page break ở chỗ logic | Không cắt giữa row table |
| URL của link in dưới text | (tùy spec) |
| Hide navigation/sidebar | Chỉ in content chính |

## J. Email Client Compatibility (nếu app gửi email)

| Client | Quirks |
|--------|--------|
| Gmail | Strip CSS không phổ biến |
| Outlook desktop | Word-based render, kém CSS |
| Outlook web | OK với inline CSS |
| Apple Mail | Tốt nhất |
| Mobile mail apps | Dark mode |

Test:
- Email render đúng trong ≥3 client
- Link clickable
- Image có alt text + fallback nếu block
- Dark mode trên iOS Mail
- Unsubscribe link work

## K. Output verification checklist

Khi sinh COMPAT cases, đảm bảo cover:

- [ ] ≥1 case Chrome desktop
- [ ] ≥1 case Safari (iOS hoặc macOS)
- [ ] ≥1 case Firefox hoặc Edge
- [ ] ≥1 case mobile (responsive)
- [ ] ≥1 case tablet (responsive)
- [ ] Mọi case có cụ thể: browser version, OS version, resolution
- [ ] Có note về touch vs mouse interaction
- [ ] Có note về network condition nếu áp dụng
