# Deep Thinking Checklist — 15 Dimensions

## ⚠️ TRIẾT LÝ

UAT không phải là copy-paste từ requirement. UAT đòi hỏi **thinking sâu** về 15 dimension của hệ thống để tìm ra các góc khuất mà spec/requirement không nói. Một UAT tốt phải tự hỏi từng câu hỏi sau và trả lời CỤ THỂ trước khi viết case.

**Cách dùng**: Trước khi viết bất kỳ TC chi tiết nào, **fill đầy** checklist này. Mỗi dimension cần ít nhất 3-5 câu trả lời cụ thể từ feature đang phân tích. Câu trả lời chung chung như "có validate input" KHÔNG đủ — phải cụ thể "email regex là RFC5322, max 254 chars, không cho phép dấu cách đầu/cuối".

---

## DIMENSION 1: INPUT SPACE — Mỗi input có bao nhiêu loại giá trị?

Cho TỪNG input field, liệt kê:
- ✅ Valid values (range hợp lệ)
- ❌ Empty, null, undefined
- ❌ Whitespace only
- ❌ Below min length / value
- ❌ Above max length / value
- ❌ Wrong type (number cho text)
- ❌ Special chars not allowed
- ❌ Unicode/emoji edge cases (đặc biệt RTL languages: Arabic, Hebrew)
- ❌ HTML/script injection
- ❌ SQL injection patterns
- ❌ Command injection
- ❌ Path traversal (`../../etc/passwd`)
- ❌ Format string attacks (`%s%s%s`)
- ❌ Number parsing edge: `0`, `-0`, `Infinity`, `NaN`, `0.1 + 0.2`, scientific notation
- ❌ Date edge: leap year, DST transition, year 9999, timezone offset
- ❌ String length attacks: 10K, 100K, 1M chars
- ❌ Null byte: `valid\0malicious`
- ❌ BOM characters: `\uFEFF`
- ❌ Mixed encoding (Latin-1 trong UTF-8 field)
- ❌ Homograph attack (Cyrillic 'а' vs Latin 'a')

Câu hỏi tự kiểm: "Nếu user paste random emoji/Chinese/SQL vào field này, code có crash không?"

---

## DIMENSION 2: STATE SPACE — Entity có bao nhiêu trạng thái?

Cho TỪNG entity (User, Order, Product, Subscription...):
- Liệt kê **tất cả** state có thể (từ enum trong DB schema)
- Diagram chuyển trạng thái: từ A → B nào hợp lệ?
- Diagram chuyển CẤM: A → C nào không được?
- Terminal states (không thể ra khỏi): vd `Deleted`, `Refunded`
- Hỗn hợp state (entity có nhiều status field độc lập): User.status × User.email_verified × User.payment_status

Câu hỏi tự kiểm:
- "Nếu user.status = Deleted nhưng vẫn còn session active, login sẽ thế nào?"
- "Order trong state Shipped có thể bị Cancel không? Refund đi qua state nào?"
- "Có race condition khi 2 admin cùng change status?"

---

## DIMENSION 3: TIME — Logic phụ thuộc thời gian

- Token/session expiry (1h, 24h, sliding/absolute)
- Cron jobs / scheduled tasks
- Time-based discounts (sale chỉ ngày 11/11)
- Subscription billing cycles
- Trial period expiry
- Cooldown / rate limit windows
- Timezone differences (server UTC vs user local)
- DST transitions (clock skip/repeat)
- Year boundary (year-end financial closing)
- Leap year (29/02)
- Daylight saving time bugs

Câu hỏi tự kiểm:
- "Nếu user login từ Hawaii (UTC-10) lúc 1pm thứ 7 → server log thứ 7 hay chủ nhật?"
- "Token expire lúc 23:59:59 — user login lúc 23:59:58 và request hoàn thành 23:59:60?"
- "Birthday/anniversary feature trên 29/02 năm thường thì là 28/02 hay 1/3?"

---

## DIMENSION 4: CONCURRENCY — Race condition & competition

- 2 users đồng thời update cùng resource (last-write-wins? optimistic lock?)
- User submit form 2 lần liên tiếp (idempotency?)
- Stock decrement race (2 users mua sản phẩm cuối)
- Payment + order status sync (payment success nhưng order vẫn pending)
- Distributed lock (Redis lock fail mid-operation)
- Async job duplication (2 workers pick same job)
- WebSocket reconnect → duplicate event delivery
- Queue at-least-once vs exactly-once

Câu hỏi tự kiểm:
- "Có 100 ticket VIP, 200 user click 'Buy' cùng lúc — outcome?"
- "Refund + Cancel order đồng thời — final state là gì?"
- "Login từ device A và logout từ device B — session vẫn valid?"

---

## DIMENSION 5: NETWORK — Connectivity failures

- Slow network (3G, edge connection)
- Offline → online transition
- Request timeout (client vs server side)
- Partial response (server crash mid-stream)
- DNS failures
- TLS handshake failure
- CORS preflight failure
- Proxy/firewall blocking
- IPv6 vs IPv4
- WebSocket disconnect/reconnect
- HTTP/2 → HTTP/1.1 fallback
- Mid-upload network drop (chunked upload)
- Browser tab suspend (mobile)
- Service Worker offline mode

Câu hỏi tự kiểm:
- "Nếu user submit form và mất mạng giữa chừng — bị duplicate khi reconnect?"
- "Page chạy 3G — UI có disable button để tránh double-click?"
- "Mobile lock screen 5 phút → resume → session còn alive?"

---

## DIMENSION 6: SECURITY — OWASP Top 10 + AuthN/AuthZ

Cho mọi input + endpoint:
- A01 Broken Access Control: IDOR — user A truy cập resource user B
- A02 Crypto Failures: password storage, token entropy, TLS version
- A03 Injection: SQL, NoSQL, LDAP, OS command, ORM, XPath
- A04 Insecure Design: business logic flaws (negative price, infinite coupon)
- A05 Misconfig: default password, debug mode, info disclosure in errors
- A06 Vulnerable Components: lib với CVE
- A07 Auth Failures: brute force, weak password, session fixation
- A08 Data Integrity: deserialization, missing signature verification
- A09 Logging Failures: log injection, missing audit
- A10 SSRF: server fetch user-supplied URL

Authorization specific:
- Horizontal (user A đọc data user B)
- Vertical (customer thực hiện admin action)
- Privilege escalation chain
- JWT tampering (none algorithm, key confusion)
- Session fixation, hijacking
- CSRF tokens

Câu hỏi tự kiểm:
- "Endpoint `/api/order/123` — user khác đoán 124, có truy cập được order người khác?"
- "Password reset link gửi email — có thể đoán được không? Expire bao lâu?"
- "Có throttle login attempt theo IP + theo username?"

---

## DIMENSION 7: DATA INTEGRITY — Database & data lifecycle

- Required vs nullable fields — code có handle null đúng?
- Cascade delete (xóa user → tag, order, comment?)
- Soft delete (deleted_at) vs hard delete
- Unique constraint violation handling
- Foreign key violation (referenced row deleted)
- Migration backward compatible?
- Index strategy (slow query với big data?)
- Encoding mixed (DB latin1 nhưng app UTF-8)
- Timezone storage (UTC in DB?)
- Decimal precision (money phải Decimal, không Float)
- Sort stability (ORDER BY name có deterministic không?)
- Pagination boundaries (off-by-one, missing/duplicate items)

Câu hỏi tự kiểm:
- "Delete user A — comment của A trong post user B còn không?"
- "User update email → email cũ có thể dùng login luôn không?"
- "Pagination page 100 với 1M record — performance?"

---

## DIMENSION 8: PERFORMANCE — Latency, throughput, scaling

- Cold start time
- p50, p95, p99 response time SLA
- N+1 queries
- Missing index
- Memory leak (long-running request)
- Cache hit/miss ratio
- CDN caching headers
- Image lazy loading
- Bundle size (TTI on slow device)
- Database connection pool exhaustion
- Background job queue backlog
- WebSocket connection limit
- File upload streaming vs loading full to memory

Câu hỏi tự kiểm:
- "10K user đăng ký cùng lúc — DB connection pool có chịu được?"
- "User scroll 1M item list — backend pagination strategy?"
- "Image profile 10MB upload — server có buffer hết vào RAM?"

---

## DIMENSION 9: ACCESSIBILITY — WCAG 2.2 AA

- Keyboard navigation full
- Focus visible (≥2px outline, contrast ≥3:1)
- Tab order logic
- Screen reader (VoiceOver, NVDA, JAWS)
- ARIA labels chính xác
- Color contrast ≥4.5:1 (text), ≥3:1 (UI)
- Color not sole indicator (red error + icon + text)
- Touch target ≥44×44px (mobile)
- Form errors associated với field
- Time-based content có pause/extend
- Auto-play media có disable
- Motion reduce (prefers-reduced-motion)
- Captions cho video

Câu hỏi tự kiểm:
- "User không dùng chuột — có hoàn thành flow 100% bằng keyboard không?"
- "User mù dùng VoiceOver — có biết submit button đang loading?"
- "Color-blind user (Deuteranopia) — phân biệt được error vs success?"

---

## DIMENSION 10: COMPATIBILITY — Multi-browser, device, OS

- Chrome, Firefox, Safari, Edge (last 2 versions)
- iOS Safari, Android Chrome (mobile-first)
- IE11 (nếu enterprise yêu cầu)
- Tablet vs phone vs desktop
- Touch vs mouse vs keyboard
- Light mode vs dark mode
- Different DPI (retina, 4K)
- Different OS fonts available
- Cookie policies (Safari ITP)
- Service Worker support
- WebGL/Canvas support
- File API limits per browser

Câu hỏi tự kiểm:
- "Safari iOS — date input có hiện picker native không?"
- "Firefox in private mode — localStorage có disable không?"
- "Android Chrome Lite mode — JavaScript có chạy đầy đủ không?"

---

## DIMENSION 11: INTERNATIONALIZATION — i18n + l10n

- Multiple languages (text translated, plurals, gender)
- RTL languages (Arabic, Hebrew, Persian) — layout mirror
- Date format (DD/MM/YYYY vs MM/DD/YYYY vs YYYY-MM-DD)
- Number format (1,000.50 vs 1.000,50 vs 1 000,50)
- Currency (symbol position, decimal places — JPY no decimal)
- Address format (US vs UK vs JP)
- Phone format (+84 vs 0 prefix)
- Name format (first/last vs single field)
- Sorting (Locale-aware: ñ in Spanish, ö in German)
- Truncation in narrow language vs verbose (German extends 30%)
- Unicode normalization (NFC vs NFD)

Câu hỏi tự kiểm:
- "Tiếng Đức có từ dài 40 chars — UI có overflow không?"
- "User Arabic → form layout có flip không?"
- "Search case-insensitive với 'İ' (Turkish) vs 'i'?"

---

## DIMENSION 12: ERROR HANDLING — Failure modes & recovery

- Form validation: client-side, server-side
- Inline error vs toast vs modal
- Error message i18n
- Retry logic (auto vs manual)
- Partial failure (some items in batch fail)
- Graceful degradation (3rd-party API down)
- Fallback UI (skeleton, empty state)
- Error logging (Sentry, Datadog)
- Error monitoring SLA

Câu hỏi tự kiểm:
- "Payment gateway timeout — user thấy gì? Có thể retry không?"
- "Form 10 fields, 3 fields invalid — UI show từng cái hay tất cả?"
- "Network drop khi đang submit — data có lost không?"

---

## DIMENSION 13: SIDE EFFECTS — Notifications, logs, integrations

- Email: gửi correct template, correct timing
- SMS: rate limit, cost optimization
- Push notification: opt-in, badge count
- Audit log: action recorded, immutable
- Analytics events fired
- Webhook triggered (with retry)
- Cache invalidation
- Search index update
- Background job spawned
- Slack/Discord notification

Câu hỏi tự kiểm:
- "User register — 4 side effects: email verify, audit log, analytics, marketing list. Tất cả async?"
- "Order cancelled — email + SMS + Slack + accounting export. Có guarantee tất cả deliver?"

---

## DIMENSION 14: BUSINESS LOGIC EDGE CASES

- Discount edge: 100% off, negative price, exceed cart total
- Stock: oversold, backorder, presale
- Subscription: prorate when upgrade/downgrade mid-cycle
- Refund: partial, full, after cancel period
- Loyalty point: race condition between earn + redeem
- Currency conversion timing (fixed-at-purchase vs current rate)
- Tax: VAT, GST, sales tax, exemption
- Shipping: zone-based, weight-based, free over threshold
- Promo code: combinable? per-user limit? expired?
- Trial → paid conversion logic

Câu hỏi tự kiểm:
- "Coupon 50% off + buy-one-get-one — stack được không?"
- "User cancel subscription giữa chu kỳ — service ngừng ngay hay end of period?"
- "Refund 30 ngày — case ngày 30 lúc 23:59 → tính ngày 30 hay 31?"

---

## DIMENSION 15: REGULATORY / COMPLIANCE

- GDPR: data export, right to be forgotten, consent
- PCI-DSS (nếu xử lý thẻ): không log card number
- HIPAA (nếu health): PHI protection
- SOX (nếu listed company): audit trail
- COPPA (nếu underage user)
- CCPA (California)
- accessibility legal (ADA in US, EN 301 549 in EU)
- Data residency (data phải nằm trong EU?)
- Right of withdrawal (EU consumer law)

Câu hỏi tự kiểm:
- "User EU yêu cầu xóa data — workflow trong bao lâu? Có hard-delete không?"
- "Export data — format CSV/JSON? Có cả audit log không?"

---

## SỬ DỤNG CHECKLIST

Trước khi viết TC chi tiết, mở Notion/Google Doc và **fill 15 dimension này**. Mỗi dimension viết ra ≥3 fact cụ thể từ feature đang phân tích.

**Output cuối**: `thinking_notes.md` với 15 section, mỗi section có 3-7 bullet points cụ thể.

**Gate trước khi viết TC**: nếu 1 dimension chỉ có 0-2 bullet hoặc bullet quá chung chung → quay lại đào sâu thêm. Không cho phép skip dimension nào.

## VÍ DỤ — Feature "Đăng nhập"

### Dimension 1 — Input space:
- Email: regex RFC5322, max 254, lowercase trước check unique
- Password: 8-128 chars, ≥1 upper, ≥1 special, ≥1 number
- remember_me: boolean default false
- captcha (nếu fail ≥3 lần): reCAPTCHA v3 token
- Cases: empty, whitespace, unicode email (`tést@domain.com`), 10K char password, null byte, SQL injection patterns

### Dimension 2 — State space:
- User: {Pending, Active, Suspended, Deleted, Locked, Trial_expired}
- Session: {None, Active, Expired, Revoked}
- Combine: Pending+None vs Active+Expired vs ... = 24 combinations

### Dimension 3 — Time:
- Token expire: access 1h, refresh 30 ngày
- Locked status: tự unlock sau 15 min
- Brute force window: 5 fail trong 10 min → lock
- Remember me: thêm 30 ngày
- Edge: login lúc 23:59 ngày 28/02 năm nhuận

### ... (12 dimension còn lại)

→ Từ 15 dimension này, ta extract ra ≥210 case (đạt formula calculator).
