# Codebase Analysis Framework — Đọc code để hiểu nghiệp vụ trước khi viết TC

## ⚠️ TẠI SAO BƯỚC NÀY BẮT BUỘC

Không đọc codebase trước khi viết UAT = viết UAT bằng tưởng tượng. Hậu quả:
- Bỏ qua nhiều edge case mà chỉ code mới reveal
- Sai validation rules (chữ thường vs HOA, regex thực tế)
- Sai HTTP status code thực tế (200 vs 201, 400 vs 422)
- Bỏ qua business rules ẩn (vd: discount chỉ apply cho VIP)
- Không biết error codes thực tế → không assert được response.error.code

**Quy tắc**: Nếu có codebase → bắt buộc đọc TRƯỚC khi viết. Không có codebase → đọc spec PRD/design doc, và viết case dựa trên giả định + ghi rõ giả định để dev xác nhận.

## QUY TRÌNH ĐỌC CODEBASE — 8 ARTIFACTS BẮT BUỘC

### 1. Routes / Endpoints

**Tìm**:
- Backend: `routes/`, `controllers/`, `api/`, `*.controller.ts`, FastAPI `@router`, Express `router.get/post`
- Frontend: `pages/`, `app/`, React Router config, Next.js file-based routing

**Hỏi từ code**:
- Endpoint nào public? Endpoint nào internal?
- HTTP method nào dùng?
- Path params, query params?
- Middleware applied (auth, rate-limit, cors)?

**Output**: Bảng `endpoints.csv`:
```
METHOD | PATH | AUTH | PARAMS | RESPONSE_CODES
POST | /api/auth/login | none | email, password | 200, 400, 401, 429
POST | /api/auth/2fa | session | code | 200, 400, 401
GET | /api/user/me | bearer | - | 200, 401
```

### 2. DTOs / Schemas / Validators

**Tìm**:
- `*.dto.ts`, `*.schema.ts`, `validators/`, `class-validator` decorators, Pydantic models, Zod schemas, Joi schemas
- DB schema: `migrations/`, `*.entity.ts`, `prisma.schema`, SQL DDL

**Hỏi từ code**:
- Mỗi field có constraints gì? (min/max length, regex, required/optional)
- Default values?
- Unique constraints?
- Foreign keys?
- Enum types?

**Output**: Bảng `input_constraints.md`:
```
FIELD       | TYPE   | REQUIRED | MIN | MAX | REGEX             | DEFAULT
email       | string | yes      | 5   | 254 | RFC5322           | -
password    | string | yes      | 8   | 128 | ≥1 upper, special | -
remember_me | bool   | no       | -   | -   | -                 | false
```

### 3. Business Rules / Service Layer

**Tìm**:
- `services/`, `use-cases/`, `*.service.ts`, domain logic
- Đọc method chính (`login()`, `register()`, `checkout()`)

**Hỏi từ code**:
- Logic chính gì? (if/else, switch, loops)
- External calls? (DB, queue, email, payment gateway, S3)
- Transactions? Rollback logic?
- Side effects? (audit log, notification, cache invalidation)
- Time-dependent logic? (expiry, cron, scheduling)

**Output**: Bảng `business_logic.md`:
```
RULE_ID  | DESCRIPTION                                    | CODE_REF
BR-01    | Email phải unique, case-insensitive            | user.service.ts:45
BR-02    | Password hash bcrypt rounds=12                 | auth.service.ts:78
BR-03    | Sau 5 lần fail liên tiếp, lock account 15 min | auth.service.ts:120
BR-04    | Trial user expire sau 14 ngày                  | subscription.service.ts:34
```

### 4. State Machines / Workflows

**Tìm**:
- Enum status fields trong entity
- Switch/case theo status
- State machine library (XState, Stately)
- Workflow engine (Temporal, Camunda)

**Hỏi từ code**:
- Entity nào có status field?
- Tất cả các state là gì?
- Transition nào hợp lệ?
- Transition nào CẤM?

**Output**: State diagram + transition table:
```
USER STATES: {Pending, Active, Suspended, Deleted, Locked}

ALLOWED TRANSITIONS:
- Pending → Active (verify email)
- Pending → Deleted (timeout 7 ngày)
- Active → Suspended (admin action)
- Active → Locked (5 fail logins)
- Suspended → Active (admin restore)
- Locked → Active (15 min timeout OR admin unlock)

FORBIDDEN:
- Deleted → * (terminal state)
- Locked → Suspended (must go through Active first)
```

### 5. Error Handling

**Tìm**:
- Exception classes: `*Exception.ts`, `*Error.ts`
- Error codes: enums `ERROR_CODES`, `ErrorCode`
- HTTP exception filters / middleware

**Hỏi từ code**:
- Code define những error type gì?
- HTTP status code mapping?
- Error response format?
- Có expose stack trace không? (security)
- Localization messages?

**Output**: `error_catalog.md`:
```
ERROR_CODE              | HTTP_STATUS | I18N_KEY              | THROWN_AT
INVALID_CREDENTIALS     | 401         | auth.invalid_creds    | auth.service.ts:65
EMAIL_ALREADY_EXISTS    | 409         | user.email_exists     | user.service.ts:30
RATE_LIMIT_EXCEEDED     | 429         | common.rate_limit     | guards/throttle.ts:18
SESSION_EXPIRED         | 401         | auth.session_expired  | auth.guard.ts:55
```

### 6. Authentication / Authorization

**Tìm**:
- Guards / Middleware: `*.guard.ts`, `auth.middleware.ts`
- Role definitions: enum `Role`, `Permission`
- Policy classes

**Hỏi từ code**:
- Bao nhiêu role?
- Mỗi endpoint require role gì?
- Permission granular (RBAC) hay role-based?
- Token format? (JWT, session, OAuth)
- Token expiry?

**Output**: `access_matrix.md`:
```
ENDPOINT              | ANONYMOUS | CUSTOMER | ADMIN | SUPERADMIN
POST /auth/login      | ✓ (creates) | -      | -     | -
GET /user/me          | ✗         | ✓        | ✓     | ✓
DELETE /user/:id      | ✗         | self only| any   | any
POST /admin/users     | ✗         | ✗        | ✓     | ✓
```

### 7. External Dependencies

**Tìm**:
- API clients: `*.client.ts`, `axios.create`, `fetch wrappers`
- SDK: `aws-sdk`, `stripe`, `sendgrid`, `redis`
- Background jobs / queues: BullMQ, Celery, sidekiq

**Hỏi từ code**:
- Service nào dùng external service?
- Timeout / retry policy?
- Fallback behavior khi service fail?
- Circuit breaker?

**Output**: `external_deps.md`:
```
SERVICE  | USE_CASE             | TIMEOUT | RETRY | FALLBACK
SendGrid | Email verification    | 5s      | 3x    | Queue for later
Stripe   | Payment processing    | 10s     | 0     | Show error to user
Redis    | Session storage       | 1s      | 1x    | In-memory fallback
S3       | Avatar upload         | 30s     | 2x    | Show "try later"
```

### 8. Tests hiện có (để biết gì đã được cover)

**Tìm**:
- `*.spec.ts`, `*.test.ts`, `__tests__/`, `tests/`
- E2E tests: `cypress/`, `playwright/`

**Đếm**:
- LOC test / LOC code ratio
- Coverage report nếu có (`coverage/lcov.info`)

**Quyết định**: nếu code đã có nhiều unit test → UAT focus vào integration + UI + edge case mà unit test không catch. Nếu zero test → UAT phải phủ cả basic.

## CÔNG CỤ HỖ TRỢ

### Đo LOC nhanh

```bash
# Cài đặt
brew install cloc  # Mac
apt install cloc   # Linux

# Đo
cloc src/  --exclude-dir=node_modules,dist,coverage

# Hoặc tokei (nhanh hơn)
brew install tokei
tokei src/
```

### Đếm branches / complexity

```bash
# JavaScript/TypeScript
npx eslint . --rule 'complexity: [error, 1]' 2>&1 | grep -c "complexity"

# Python
pip install radon
radon cc src/ -s -a

# Java
# Sonarqube cyclomatic complexity
```

### Tìm endpoints nhanh

```bash
# Express
grep -rE "router\.(get|post|put|delete|patch)" src/

# NestJS
grep -rE "@(Get|Post|Put|Delete|Patch)\(" src/

# FastAPI
grep -rE "@(app|router)\.(get|post|put|delete|patch)" src/

# Next.js (file-based)
find pages/api app/api -type f -name "*.ts" -o -name "*.js"
```

### Tìm enum (states, error codes)

```bash
# TypeScript
grep -rE "^export enum" src/

# Python
grep -rE "class.*Enum" src/
```

## OUTPUT CUỐI CỦA BƯỚC ANALYSIS

Tạo file `/tmp/codebase_map.md` chứa:

```markdown
# Codebase Map — Feature: Đăng nhập

## Metrics
- LOC total: 230
- LOC test: 180 (78% coverage)
- Cyclomatic complexity: avg 4.2, max 12

## Endpoints (4)
[...bảng từ section 1]

## Inputs (5)
[...bảng từ section 2]

## Business Rules (8)
[...bảng từ section 3]

## States (8)
[...diagram từ section 4]

## Errors (8)
[...catalog từ section 5]

## Access Matrix
[...bảng từ section 6]

## External Deps (3)
[...từ section 7]

## TC_min (ENSEMBLE — coverage-calculator.md)
M1 spec coverage items = Σ(AC×2)+EP+BVA+decision+state+pairwise = …
M2 Σ cyclomatic V(G) (đo bằng lizard/eslintcc) = …
M3 ceil(FP^1.2) (nếu có FP) = …
M4 risk-tier backstop = …
TC_min = MAX(M1,M2,M3,M4) = …   # KHÔNG dùng LOC
```

→ Đem file này làm input cho bước "Detail TC" và "Self-Audit".

## KHI KHÔNG CÓ CODEBASE

User chưa có code (greenfield project) hoặc không cho access:

1. **Hỏi spec / PRD / wireframe** — đọc kỹ
2. **Đề xuất assumption** rõ ràng:
   ```
   Tôi giả định:
   - Email validation theo RFC 5322
   - Password min 8 chars, có upper + special
   - JWT token, expire 1h
   - Rate limit 5 requests/phút
   
   Confirm hay sửa giả định trước khi tôi viết TC.
   ```
3. **Đánh dấu TC nào dựa trên assumption**: trong cột Ghi chú ghi `[ASSUMED]`.
4. **TC_min vẫn tính từ spec/assumption** (M1 coverage items + M4 risk-tier; M2 V(G) không có code thì bỏ) — coverage-driven, không số tròn tùy tiện.
