# RED Pattern Library — 200+ Patterns

## ⚠️ CÁCH DÙNG

Library này chứa các pattern để **MULTIPLY** số RED case nhanh chóng. Quy tắc:

```
Total RED cases = Σ (input field × applicable patterns)
                + Σ (state × invalid transitions)
                + Σ (endpoint × HTTP edge cases)
                + Σ (role × forbidden action)
```

Skill writer khi viết RED case PHẢI quét qua từng category để **không sót pattern**. Anti-pattern: chỉ viết 2-3 RED case generic (vd: "email sai format", "password ngắn") rồi nghĩ là đủ.

---

## CATEGORY 1: INPUT VALIDATION (40+ patterns)

### 1.1 Empty / Null
- [ ] Empty string ""
- [ ] Null
- [ ] Undefined
- [ ] Whitespace only " "
- [ ] Tab "\t"
- [ ] Newline "\n"
- [ ] Multiple spaces "    "
- [ ] Zero-width space "\u200B"
- [ ] Non-breaking space "\u00A0"

### 1.2 Length attacks
- [ ] 1 char less than min
- [ ] Min - 1 boundary
- [ ] Max + 1 boundary
- [ ] 10x max length
- [ ] 1000x max length (DoS)
- [ ] Empty array []
- [ ] 10K item array

### 1.3 Type confusion
- [ ] Number cho text field ("12345")
- [ ] Text cho number field ("abc")
- [ ] Object cho primitive
- [ ] Array cho object
- [ ] Boolean cho number
- [ ] Date string cho timestamp number
- [ ] Object instead of array

### 1.4 Format violations
- [ ] Wrong email format ("notanemail")
- [ ] Email without @
- [ ] Email without domain
- [ ] Email starting with .
- [ ] Email with double @
- [ ] Email with space inside
- [ ] Email > 254 chars
- [ ] IDN email (`tést@dömain.com`)
- [ ] Phone without country code
- [ ] Phone with letters
- [ ] URL without protocol
- [ ] URL with javascript: scheme
- [ ] URL with data: scheme

### 1.5 Unicode tricks
- [ ] Emoji in name field 🎉
- [ ] RTL text "مرحبا"
- [ ] Mixed scripts "中文english"
- [ ] Homograph attack "аdmin" (Cyrillic 'а')
- [ ] Combining diacritics "ñ" as "n + ◌̃"
- [ ] BOM character "\uFEFF"
- [ ] Null byte "valid\0malicious"
- [ ] Zero-width joiner "\u200D"
- [ ] Bidi override "\u202E"

### 1.6 Number edge
- [ ] 0
- [ ] -0
- [ ] -1 (nếu expect positive)
- [ ] 0.1 + 0.2 ≠ 0.3 (float precision)
- [ ] Infinity
- [ ] -Infinity
- [ ] NaN
- [ ] Number.MAX_SAFE_INTEGER + 1
- [ ] Scientific notation "1e308"
- [ ] Negative zero
- [ ] Leading zeros "0123"
- [ ] Hex notation "0xFF"
- [ ] Currency comma "1,000.50"

### 1.7 Date/Time edge
- [ ] 29/02 năm thường
- [ ] 29/02 năm nhuận
- [ ] Date trong quá khứ (nếu expect future)
- [ ] Date trong tương lai (nếu expect past)
- [ ] Year 0000
- [ ] Year 9999
- [ ] Y2K38 problem (32-bit unix timestamp)
- [ ] Daylight saving transition
- [ ] Timezone offset extreme (UTC+14, UTC-12)
- [ ] Sub-second precision

---

## CATEGORY 2: SECURITY (60+ patterns)

### 2.1 SQL Injection
- [ ] `' OR '1'='1`
- [ ] `'; DROP TABLE users;--`
- [ ] `' UNION SELECT password FROM users--`
- [ ] `admin'--`
- [ ] `' OR 1=1#`
- [ ] `1' AND SLEEP(5)--` (time-based)
- [ ] `1' AND (SELECT COUNT(*) FROM users) > 0--` (boolean blind)
- [ ] `'; EXEC xp_cmdshell('whoami')--` (MSSQL)
- [ ] Stacked queries `; INSERT INTO ...`
- [ ] NoSQL: `{"$ne": null}`
- [ ] NoSQL: `{"$gt": ""}`
- [ ] MongoDB JS injection: `'; return true; var x='`

### 2.2 XSS (Cross-site scripting)
- [ ] `<script>alert(1)</script>`
- [ ] `<img src=x onerror=alert(1)>`
- [ ] `<svg onload=alert(1)>`
- [ ] `javascript:alert(1)`
- [ ] `<iframe src=javascript:alert(1)>`
- [ ] `"><script>alert(1)</script>`
- [ ] HTML entities `&lt;script&gt;`
- [ ] Mixed case `<ScRiPt>`
- [ ] Polyglot: `'"><img src=x onerror=alert(1)>`
- [ ] Stored XSS in user profile
- [ ] DOM XSS via location.hash
- [ ] CSP bypass attempts

### 2.3 Command Injection
- [ ] `; ls -la`
- [ ] `| cat /etc/passwd`
- [ ] `$(whoami)`
- [ ] `` `id` ``
- [ ] `&& rm -rf /`
- [ ] `%0Acommand`

### 2.4 Path Traversal
- [ ] `../../../etc/passwd`
- [ ] `..\\..\\..\\windows\\system32`
- [ ] `....//etc/passwd`
- [ ] `%2e%2e%2f` (URL encoded)
- [ ] `/proc/self/environ`

### 2.5 SSRF
- [ ] `http://localhost:6379` (Redis)
- [ ] `http://169.254.169.254/` (AWS metadata)
- [ ] `http://127.0.0.1:22` (SSH)
- [ ] `file:///etc/passwd`
- [ ] `gopher://` scheme
- [ ] DNS rebinding attack

### 2.6 IDOR
- [ ] Truy cập `/api/order/124` của user khác
- [ ] Đổi user_id trong request body
- [ ] Đổi tenant_id (multi-tenancy)
- [ ] Numeric ID enumeration (1, 2, 3...)
- [ ] UUID guessing (sequential)

### 2.7 Authentication
- [ ] Brute force login (100 lần wrong password)
- [ ] Credential stuffing (common password list)
- [ ] Session fixation
- [ ] Session hijack (steal cookie)
- [ ] JWT tampering — alg: none
- [ ] JWT alg confusion (RS256 → HS256)
- [ ] JWT signature strip
- [ ] Expired token reuse
- [ ] Replay attack
- [ ] CSRF without token

### 2.8 Authorization
- [ ] Customer thực hiện admin endpoint
- [ ] Admin của tenant A access tenant B
- [ ] User suspended cố login
- [ ] Read-only role thực hiện write
- [ ] Privilege escalation: PUT /api/user/me { role: "admin" }
- [ ] Role downgrade refusal

### 2.9 Rate limit / DoS
- [ ] 1000 request/sec
- [ ] Slowloris (slow header)
- [ ] Large request body (1GB POST)
- [ ] Deep JSON nesting (1000 level)
- [ ] Regex DoS (ReDoS): `(a+)+$`
- [ ] Hash collision DoS
- [ ] XML billion laughs

---

## CATEGORY 3: BUSINESS LOGIC (50+ patterns)

### 3.1 Money / Pricing
- [ ] Price = 0
- [ ] Price < 0 (negative)
- [ ] Price = 0.001 (sub-cent)
- [ ] Discount > 100%
- [ ] Coupon stack max exceed
- [ ] Coupon dùng quá số lần cho phép
- [ ] Coupon expired vẫn được apply
- [ ] Currency mismatch in checkout
- [ ] Tiền VAT round half-up vs half-even

### 3.2 Inventory
- [ ] Mua khi stock = 0
- [ ] 2 user mua last item cùng lúc
- [ ] Add to cart quantity > stock
- [ ] Stock âm sau xử lý
- [ ] Backorder logic
- [ ] Reservation timeout
- [ ] Pre-sale before launch date

### 3.3 Subscription
- [ ] Upgrade mid-cycle (proration)
- [ ] Downgrade mid-cycle
- [ ] Cancel during trial
- [ ] Cancel after grace period
- [ ] Re-subscribe after cancel
- [ ] Trial extension abuse (multiple accounts)
- [ ] Payment fail in renewal

### 3.4 User lifecycle
- [ ] Register với email đã existed
- [ ] Register với email đã soft-deleted
- [ ] Login khi account chưa verify email
- [ ] Login khi account suspended
- [ ] Reset password 2 lần trong 1 phút
- [ ] Reset password với link expired
- [ ] Email update không xác nhận
- [ ] Username squatting

### 3.5 Order workflow
- [ ] Cancel order sau khi Shipped
- [ ] Refund chỉ 1 phần (partial)
- [ ] Refund > số tiền paid
- [ ] Duplicate payment (idempotency)
- [ ] Order Submitted nhưng Payment Failed
- [ ] Address change after Shipped

---

## CATEGORY 4: STATE TRANSITION INVALID (30+ patterns)

Cho mỗi state pair (A, B) mà transition KHÔNG được phép:

- [ ] Cố tình move Deleted → Active
- [ ] Cố tình move Closed Order → Submitted
- [ ] Skip state (Pending → Shipped không qua Paid)
- [ ] Reverse transition (Shipped → Submitted)
- [ ] Self-loop khi không cho (Locked → Locked manually)
- [ ] Concurrent transitions từ 2 actor

---

## CATEGORY 5: NETWORK / API (40+ patterns)

### 5.1 HTTP method
- [ ] POST endpoint nhận GET
- [ ] PUT endpoint nhận PATCH
- [ ] DELETE endpoint nhận GET (CSRF)
- [ ] Method override header `X-HTTP-Method-Override`

### 5.2 Headers
- [ ] Missing Content-Type
- [ ] Wrong Content-Type (XML khi expect JSON)
- [ ] Missing Authorization
- [ ] Malformed Authorization (`Bearer ` empty)
- [ ] Wrong Accept (`Accept: text/csv` khi server only JSON)
- [ ] Accept-Language unsupported
- [ ] Origin header mismatch (CORS)
- [ ] Referer spoofing
- [ ] User-Agent empty / suspicious bot

### 5.3 Body
- [ ] Empty body
- [ ] Malformed JSON `{"a":}`
- [ ] Trailing comma `{"a":1,}`
- [ ] Duplicate keys `{"a":1,"a":2}`
- [ ] Extra unexpected fields
- [ ] Missing required fields
- [ ] Null required fields
- [ ] Wrong types
- [ ] Nested object too deep
- [ ] Array instead of object
- [ ] Binary data in JSON

### 5.4 Connection
- [ ] Timeout (slow response)
- [ ] Premature close
- [ ] Chunked encoding malformed
- [ ] HTTP/1.0 client
- [ ] WebSocket disconnect mid-stream
- [ ] Long polling timeout

### 5.5 Status code expectations
- [ ] Endpoint return 200 nhưng body `{"error": "..."}` (anti-pattern)
- [ ] Endpoint return 500 thay vì 400 cho validation
- [ ] Endpoint return 200 cho delete (should 204)
- [ ] Missing Location header for 201

---

## CATEGORY 6: UI / UX (30+ patterns)

### 6.1 Form interaction
- [ ] Submit form 2 lần trước response (double-click)
- [ ] Submit form, đổi field, back button
- [ ] Tab key trong field disabled
- [ ] Paste text dài hơn maxlength
- [ ] Autofill từ browser invalid value
- [ ] Drag-drop file vào non-upload area
- [ ] Right-click context menu trong sensitive field

### 6.2 Navigation
- [ ] Back button sau khi submit
- [ ] Forward button sau back
- [ ] Reload trang giữa multi-step flow
- [ ] Direct URL access (bypass step)
- [ ] Bookmark URL với expired session
- [ ] Open in new tab from middle of flow
- [ ] Browser refresh during file upload

### 6.3 Responsive
- [ ] Modal overflow viewport mobile
- [ ] Sticky element conflict với keyboard mobile
- [ ] Zoom in 200% — layout broken
- [ ] Horizontal scroll trên mobile
- [ ] Click target < 44px mobile
- [ ] Hover state stuck on touch device

### 6.4 Loading / Empty state
- [ ] Slow response — UI no feedback
- [ ] Empty list không có empty state
- [ ] Skeleton mismatch với real layout
- [ ] Loading state hiển thị quá lâu
- [ ] Error state không có retry

---

## CATEGORY 7: DATA INTEGRITY (20+ patterns)

- [ ] Submit form A, server save, then GET A → data lost
- [ ] Update entity từ 2 device khác — last-write-wins?
- [ ] Soft delete entity then re-create với same unique key
- [ ] Cascade delete unexpected (mất related data)
- [ ] Floating point error in money calculation
- [ ] Date stored timezone-aware vs naive
- [ ] DST forward gap (vd: 02:30 ngày DST start không tồn tại)
- [ ] DST backward duplicate (01:30 xảy ra 2 lần)
- [ ] String trim leading/trailing space inconsistent
- [ ] Case-sensitive vs case-insensitive comparison
- [ ] Collation order (Spanish "ñ", German "ö")
- [ ] Pagination off-by-one
- [ ] Pagination missing record at boundary
- [ ] Pagination duplicate record at boundary
- [ ] Cursor pagination với data update giữa request

---

## CATEGORY 8: INTEGRATION & SIDE EFFECT (20+ patterns)

- [ ] Email service down — user thấy gì?
- [ ] Email gửi nhưng record DB rollback (orphan email)
- [ ] DB save thành công nhưng email không gửi (silent failure)
- [ ] Payment gateway timeout — order status?
- [ ] Webhook không deliver → có retry không?
- [ ] Webhook duplicate (đến 2 lần)
- [ ] Audit log fail — main action vẫn commit?
- [ ] Cache invalidation miss → stale data
- [ ] Search index ko sync với DB
- [ ] Analytics event fire ngược order (ack trước user action)
- [ ] Push notification cho user đã uninstall app
- [ ] SMS gửi cho số đã unsubscribe
- [ ] Background job worker crash mid-task

---

## AUTO-MULTIPLIER QUY TẮC

### Per text input field (≥14 case)
- 9 cases từ Category 1.1-1.3 (empty, length, type)
- 5 cases từ Category 1.5 (Unicode tricks)

### Per email field (thêm 8 case)
- Category 1.4 format violations: 8

### Per password field (thêm 5 case)
- Brute force, common password, length, complexity, history

### Per number field (thêm 8 case)
- Category 1.6 entire

### Per date field (thêm 8 case)
- Category 1.7 entire

### Per file upload (thêm 8 case)
- Wrong format, oversize, zero-byte, malicious name, polyglot, EICAR signature, max files exceeded, mime type mismatch

### Per money field (thêm 9 case)
- Category 3.1 entire

### Per public endpoint (thêm 13 case)
- Category 5.2-5.5 selection

### Per state (thêm 5 case)
- Category 4

### Per role boundary (thêm 6 case)
- Category 2.8 + 2.6

---

## HƯỚNG DẪN ÁP DỤNG

### Step 1: Inventory inputs
List tất cả input field, endpoint, state, role.

### Step 2: Apply multiplier
Cho mỗi item, áp dụng pattern tương ứng từ library trên.

### Step 3: Combinatorial (tier 2)
2-way combinations giữa các field — vd: email + password combo:
- Email valid + Password empty
- Email valid + Password XSS
- Email SQLi + Password valid
- Email Unicode + Password 0 char
- ...

### Step 4: Reduce duplicates
Có thể nhiều case test cùng 1 root cause (vd: invalid email format) — gộp thành EP (Equivalence Partitioning).

### Step 5: Risk-prioritize
Sắp xếp theo severity. P0 = Critical impact (data loss, security breach). P1 = High (broken core flow). P2 = Medium (UX issue). P3 = Low (cosmetic).

---

## VÍ DỤ MULTIPLIER — Login feature

**Inputs**: email (1), password (1), remember_me (1), captcha (1) = 4 inputs

**Apply multiplier**:
- Email (text + format): 14 + 8 = 22 case
- Password (text + complexity): 14 + 5 = 19 case
- Boolean remember_me: 4 case (true/false/null/string)
- Captcha: 6 case (valid/invalid/expired/missing/replay/spam)

**Endpoint**: POST /api/auth/login: 13 case

**States**: User has 5 states × 5 = 25 case

**Roles**: 4 roles × 4 = 16 case

**Combinatorial** (2-way): chọn 10 combination quan trọng = 10 case

**Total RED**: 22+19+4+6+13+25+16+10 = 115 RED case

**Plus**:
- GREEN ~ 25 case (smoke + happy variants)
- Security additional: 30 case
- A11y: 15 case
- Performance: 10 case
- Compat: 12 case

**TOTAL**: ~210 case → khớp với formula calculator!
