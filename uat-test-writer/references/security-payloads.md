# Security Payload Library — OWASP Top 10 2021

Thư viện payload và pattern test bảo mật chuẩn enterprise cho web application. Tổ chức theo OWASP Top 10 2021 + thêm các pattern cho UAT.

## A01:2021 — Broken Access Control

### IDOR (Insecure Direct Object Reference)

**Test pattern (bắt buộc cho mọi resource có owner):**

1. Login user A → tạo resource → note ID
2. Logout, login user B
3. Truy cập resource của A qua URL/API:
   - `GET /api/orders/{A_id}` — phải 403 hoặc 404
   - `PATCH /api/orders/{A_id}` — phải 403
   - `DELETE /api/orders/{A_id}` — phải 403

**Pattern test cases bắt buộc**:
- Predictable ID (1, 2, 3) — phải có authz check
- UUID — vẫn phải có authz check (không dựa vào unguessability)
- Direct file URL (`/uploads/private/abc.pdf`) — phải check ownership
- Hidden form field (user_id) — không tin client

### Privilege Escalation

| Loại | Test |
|------|------|
| Horizontal | User A truy cập resource user B (cùng role) |
| Vertical | User role Customer truy cập endpoint Admin |
| Forced browsing | Truy cập `/admin/users` khi không phải admin |
| Mass assignment | PATCH user với field `role: admin` |

### Authentication bypass

- URL manipulation: `/admin?user_id=1`
- Token replay sau logout
- Session fixation: set session ID trước login

## A02:2021 — Cryptographic Failures

### Test cases

| Test | Expected |
|------|----------|
| Database lưu password | Phải hash bcrypt/argon2, KHÔNG plaintext |
| Password trong response API | KHÔNG có (kể cả hash) |
| Token JWT có expiry | Có `exp` claim, ≤24h cho session token |
| HTTPS bắt buộc | HTTP redirect sang HTTPS, có HSTS header |
| Cookie nhạy cảm | Flag `HttpOnly`, `Secure`, `SameSite` |
| TLS version | ≥ 1.2, không SSLv3 |
| Sensitive data trong URL | KHÔNG (query string bị log) |
| Sensitive data trong localStorage | KHÔNG (XSS-able) |

## A03:2021 — Injection

### SQL Injection

| Payload | Mục đích |
|---------|----------|
| `' OR '1'='1` | Boolean-based |
| `'; DROP TABLE users;--` | Statement chaining |
| `' UNION SELECT NULL, version(), NULL --` | Union-based |
| `admin'--` | Comment bypass |
| `1' AND SLEEP(5)--` | Time-based blind |
| `1; EXEC xp_cmdshell('whoami')--` | MSSQL command exec |
| `1' AND 1=CONVERT(int, @@version)--` | Error-based |

### NoSQL Injection (MongoDB)

| Payload | Mục đích |
|---------|----------|
| `{"$ne": null}` | Trả về mọi record |
| `{"$gt": ""}` | Tương tự |
| `{"$regex": ".*"}` | Match all |
| `{"$where": "1==1"}` | JS injection |
| `{"username": {"$ne": null}, "password": {"$ne": null}}` | Auth bypass |

### Command Injection

| Payload | Platform |
|---------|----------|
| `; ls -la` | Unix |
| `\| whoami` | Pipe |
| `` `id` `` | Backtick |
| `$(sleep 5)` | Subshell |
| `& dir` | Windows |
| `\|\| cat /etc/passwd` | OR command |

### LDAP Injection

| Payload | Mục đích |
|---------|----------|
| `*` | Wildcard match all |
| `*)(uid=*` | Filter bypass |
| `admin)(&(password=*)` | Auth bypass |

### XPath Injection

| Payload | Mục đích |
|---------|----------|
| `' or '1'='1` | Bypass |
| `' or 1=1 or ''='` | Boolean |
| `count(//user)` | Enumeration |

### XSS (Cross-Site Scripting)

**Reflected XSS:**
| Payload | Loại |
|---------|------|
| `<script>alert(1)</script>` | Basic |
| `<img src=x onerror=alert(1)>` | Event handler |
| `<svg/onload=alert(1)>` | SVG vector |
| `javascript:alert(1)` | URL/href |
| `"><script>alert(1)</script>` | Attribute breakout |
| `'><svg onload=alert(1)>` | Single quote breakout |

**Stored XSS** (lưu trong DB rồi render):
- Comment, profile name, blog post
- Admin panel render input của user

**DOM XSS:**
- `#<script>...` trong URL fragment
- `location.hash` được dùng innerHTML
- `eval()` của user input

**Framework-specific:**
| Framework | Payload |
|-----------|---------|
| AngularJS | `{{constructor.constructor('alert(1)')()}}` |
| Vue | `{{_c.constructor('alert(1)')()}}` |
| React (dangerouslySetInnerHTML) | `<img src=x onerror=alert(1)>` |

### Template Injection (SSTI)

| Engine | Payload |
|--------|---------|
| Jinja2 | `{{7*7}}`, `{{config}}` |
| Twig | `{{7*7}}`, `{{_self.env}}` |
| Velocity | `#set($x=7*7)$x` |
| Freemarker | `<#assign x=7*7>${x}` |

### XXE (XML External Entity)

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<foo>&xxe;</foo>
```

Test khi app có API/upload chấp nhận XML.

## A04:2021 — Insecure Design

### Rate Limiting

| Test case | Expected |
|-----------|----------|
| 100 login attempts/phút | Lock account hoặc CAPTCHA |
| 1000 API request/phút | 429 Too Many Requests |
| 50 password reset request | Throttle |
| 100 signup từ cùng IP | Block |

### Missing CAPTCHA

- Form signup không có CAPTCHA → bot signup
- Form login không có CAPTCHA sau N lần fail
- Form contact spam-able

### Missing MFA

- Login account quan trọng không có 2FA option
- Change password không cần verify password cũ
- Change email không cần verify
- Withdraw money không có 2FA

## A05:2021 — Security Misconfiguration

### Security Headers

| Header | Giá trị mong đợi |
|--------|------------------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | Set, không có `unsafe-inline` |
| `X-Frame-Options` | `DENY` hoặc `SAMEORIGIN` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | Set explicit |
| `X-XSS-Protection` | `1; mode=block` (legacy) |
| `Cache-Control` (sensitive) | `no-store, no-cache` |

### CORS

| Test | Expected |
|------|----------|
| Origin không trong whitelist | Block |
| `Access-Control-Allow-Origin: *` + credentials | KHÔNG được (phải specific origin) |
| Preflight OPTIONS | Handle đúng |
| Wildcard cho origin nhạy cảm | KHÔNG |

### Directory listing

- Truy cập `/uploads/` không có index → 403, không liệt kê file
- `.git/`, `.env`, `backup.sql` không accessible

### Default credentials

- Admin panel với `admin/admin`, `admin/password`
- Database UI exposed
- Debug endpoint còn enabled trên production

## A07:2021 — Identification and Authentication Failures

### Brute force protection

| Test | Expected |
|------|----------|
| 5 lần password sai | CAPTCHA xuất hiện |
| 10 lần password sai | Account lock 15 phút |
| Brute force username (timing attack) | Response time đồng nhất |
| Brute force OTP 6 số | Block sau 3 lần |

### Session management

| Test | Expected |
|------|----------|
| Logout → dùng lại token cũ | 401 |
| Session timeout | Auto-logout sau N phút idle |
| Multi-device login | Cho phép hoặc kick session cũ (theo spec) |
| Session ID predictable | KHÔNG, phải random ≥128 bit |
| Session ID trong URL | KHÔNG (phải cookie) |
| Concurrent session limit | Theo spec |

### Password policy

| Test | Expected |
|------|----------|
| Password yếu (`123456`) | Reject |
| Password trong blacklist common | Reject |
| Password trùng username/email | Reject |
| Password reset link dùng nhiều lần | Reject lần 2 |
| Password reset link expire | Sau 15-60 phút |
| Change password không cần password cũ | KHÔNG được |

### JWT-specific

| Test | Expected |
|------|----------|
| JWT `alg: none` | Server reject |
| JWT secret yếu (`secret`, `123456`) | Crack-able → fail |
| JWT không expire | Phải có `exp` |
| JWT signature giả | Reject |
| JWT từ user khác | Reject |

## A08:2021 — Software and Data Integrity Failures

### Deserialization

- Java/Python pickle deserialization của user input → RCE
- Test: gửi payload deserialize qua cookie, body

### File Upload bypass

| Payload | Mục đích |
|---------|----------|
| `shell.php.jpg` | Double extension |
| `shell.PhP` | Case bypass |
| `shell.php%00.jpg` | Null byte |
| `shell.php;.jpg` | Semicolon trick (IIS) |
| File `.jpg` chứa PHP code | Magic byte vs extension |
| Polyglot file (JPG + JS valid) | Multi-format |
| Zip bomb (42.zip) | Decompression DoS |
| File 10GB | Storage exhaustion |
| `<script>` in SVG file | SVG XSS |
| File với name `../../../etc/passwd` | Path traversal trong filename |

**Expected**: Server validate magic bytes, strip metadata, lưu ngoài web root, serve với `Content-Disposition: attachment`, sanitize filename.

## A09:2021 — Security Logging and Monitoring Failures

### Test cases

| Action | Có log không? | Log có gì? |
|--------|---------------|------------|
| Login success | Có | user_id, IP, timestamp, user-agent |
| Login fail | Có | username (literal), IP, reason |
| Password reset | Có | user_id, IP, success/fail |
| Privilege escalation attempt | Có | user_id, target, IP |
| Suspicious input (SQLi, XSS) | Có | payload, IP, endpoint |
| Admin action | Có | admin_id, target, change |

**Anti-pattern (BẮT BUỘC verify KHÔNG có):**
- Log chứa plaintext password
- Log chứa full credit card
- Log chứa session token đầy đủ
- Log chứa PII không cần thiết (SSN, full name + DOB)

## A10:2021 — Server-Side Request Forgery (SSRF)

Khi app có feature fetch URL từ user (vd: "preview link", "upload from URL", webhook):

| Payload | Mục đích |
|---------|----------|
| `http://127.0.0.1:8080` | Localhost scan |
| `http://169.254.169.254/latest/meta-data/` | AWS metadata |
| `file:///etc/passwd` | Local file |
| `gopher://...` | Protocol smuggling |
| `http://localhost:6379` | Redis access |
| `dict://...` | Dict protocol |

**Expected**: Whitelist domain, block private IP range, validate scheme.

## Path Traversal

| Payload | Mục đích |
|---------|----------|
| `../../../etc/passwd` | Unix |
| `..\..\..\windows\system32\config\sam` | Windows |
| `%2e%2e%2f%2e%2e%2fetc%2fpasswd` | URL-encoded |
| `....//....//etc/passwd` | Double-dot |
| `/etc/passwd%00.jpg` | Null byte |
| `....\/....\/etc/passwd` | Mixed slash |

## CSRF

**Test pattern:**

1. User A login vào webapp
2. Tạo HTML page tại attacker.com với form POST tự động tới endpoint nhạy cảm
3. Truy cập attacker.com khi đang login
4. Form auto-submit

**Expected:** Reject vì thiếu CSRF token / SameSite cookie / Origin check.

## Test case format mẫu cho SECURITY

```markdown
| TC-ID | TC-SEC-XXX |
|-------|------------|
| **Loại** | SECURITY |
| **Độ ưu tiên** | P0 |
| **Kỹ thuật test** | Security testing - OWASP A03 Injection |
| **Risk Level** | Cao |
| **Tiêu đề** | SQL Injection trong field tìm kiếm |
| **Threat model** | Attacker là user đã login, mục tiêu lấy data user khác |
| **Điều kiện tiên quyết** | 1. User đã login<br>2. DB có ≥1 user khác |
| **Các bước kiểm thử** | 1. Vào trang `/products`<br>2. Mở DevTools Network tab<br>3. Nhập payload: `' OR '1'='1` vào ô search<br>4. Click "Tìm kiếm"<br>5. Quan sát response và DB |
| **Dữ liệu kiểm thử** | Payload: `' OR '1'='1` |
| **Kết quả mong đợi** | **UI:**<br>1. Hiển thị 0 kết quả hoặc literal match<br>**API:**<br>2. HTTP 200 (parameterized) hoặc 400 (validation)<br>3. Response KHÔNG chứa SQL error, stack trace<br>4. Response time <500ms (không có SQLi thật)<br>**Side effects:**<br>5. Bảng users trong DB vẫn nguyên vẹn (verify count)<br>6. Audit log có sự kiện "suspicious_input" với IP user |
| **Severity nếu fail** | Critical (S1) — production blocker |
```
