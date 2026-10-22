# Data Maturity Matrix — Framework Tạo Data Test Độc Lập

## ⚠️ Triết lý cốt lõi

Mỗi nghiệp vụ cần test trên **nhiều stage trưởng thành của entity**. Một tài khoản test tĩnh KHÔNG đủ phủ các kịch bản như:

- "User chưa verify email" → cần user state = `Pending`
- "Trial sắp hết hạn còn 2 ngày" → cần user có `trial_ends_at = now() + 2 days`
- "Order rỗng" vs "Order 100 items" vs "Order chứa item đã xóa" → cần 3 shape khác nhau
- "Account vừa tạo 5 phút trước" vs "Account 1 năm chưa login" → cần thời gian khác nhau

**Quy tắc**: Khi viết TC, KHÔNG dùng data có sẵn nếu kịch bản đó cần state đặc thù. Phải **define data fixture riêng** + ghi cách seed.

## ⭐ Quy tắc data 2025-2026 (BẮT BUỘC)

1. **Synthetic-by-construction mặc định** (EDPB 01/2025: masked production data VẪN là personal data → môi trường giữ nó vẫn trong scope GDPR). Cần masked-prod vì độ chân thực → flag `data_classification: personal-data` trên fixture + ghi nhận môi trường in-scope. KHÔNG BAO GIỜ đưa production/PII vào LLM.
2. **Seeding method khai báo per fixture**: `api` (mặc định — đi qua validation/hooks/derived fields, sống sót qua migration) | `sql` (CHỈ 2 lý do hợp lệ: state không thể tạo qua API cho negative/legacy test, hoặc bulk volume cho perf — phải ghi justification) | `snapshot` (baseline versioned, restore nhanh hơn re-seed).
3. **Namespace + cleanup LIFO**: mọi entity tạo ra mang prefix `uat-<run>-<worker>-<uuid>`; cleanup theo **stack LIFO đúng ID đã capture** (tôn trọng FK) — CẤM `DELETE WHERE name LIKE` (có thể xoá data chung). Janitor sweep định kỳ dọn `uat-*` cũ >N giờ = lưới an toàn, không thay thế cleanup theo ID. Data chung/reference = READ-ONLY tuyệt đối.
4. **KHÔNG dùng DB transaction rollback cho E2E** (lock table, hỏng async, không hợp app process riêng).
5. **Factory > Faker thô**: bọc Faker trong domain factory (default hợp lệ, override đúng 1 field đang test). **Boundary value HAND-CODE** — Faker sinh boundary = defect thiết kế test.
6. **Determinism flags per TC** (handoff schema): auth_role, clock_freeze, network_stubs (chỉ 3rd-party/error-injection), serial (mutate shared singleton — kèm lý do).

## 3 chiều của Data Maturity

### Chiều 1: STATE (Trạng thái entity)

State đến từ enum trong DB schema. Ví dụ:

**User**:
- `New` — vừa register, chưa verify
- `Pending` — đã verify, chờ activation
- `Active` — bình thường
- `Trial` — trong trial period
- `Suspended` — admin lock
- `Locked` — auto lock do brute force
- `Deleted` (soft) — vẫn còn record
- `Banned` — vĩnh viễn

**Order**:
- `Draft`, `Submitted`, `Paid`, `Shipped`, `Delivered`, `Cancelled`, `Refunded`, `Disputed`

**Subscription**:
- `Trial`, `Active`, `Past_due`, `Cancelled`, `Paused`, `Expired`

### Chiều 2: LIFECYCLE (Thời gian)

Time-relative data — cần data có `created_at`, `last_login_at`, `trial_ends_at` ở thời điểm khác nhau:

| Code | Mô tả | Use case |
|------|-------|----------|
| `D0` | Mới tạo trong session hiện tại | "Vừa register" flow |
| `D1` | 1 ngày trước | "Welcome email D+1" |
| `D7` | 7 ngày trước | "Trial reminder" |
| `D14` | 14 ngày trước | "Trial expired" (nếu trial = 14 days) |
| `D29` | 1 ngày trước expire | "Renewal reminder" |
| `D30` | Tròn 30 ngày | "Monthly active user" |
| `D90` | 3 tháng | "Dormant warning" |
| `D365` | 1 năm | "Stale account" |
| `D-1` | Tương lai 1 ngày | "Scheduled activation" |
| `D-30` | Tương lai 30 ngày | "Future subscription" |

### Chiều 3: SHAPE (Hình dạng dữ liệu)

Quantity / cardinality / completeness:

| Code | Mô tả |
|------|-------|
| `empty` | 0 record (trống) |
| `single` | 1 record |
| `sparse` | 2-5 records (ít) |
| `normal` | ~10-50 records (bình thường) |
| `full` | ~100 records |
| `large` | ~1000 records |
| `huge` | ~10K-100K records (stress test) |
| `with_holes` | Có records bị soft-deleted xen kẽ |
| `with_orphans` | Có references đến record không tồn tại |
| `with_duplicates` | Có records trùng key (test dedupe) |

### Kết hợp 3 chiều → Fixture ID

Format: `<entity>.<state>.<lifecycle>.<shape>`

Ví dụ:
- `user.active.D30.normal` — User active, 30 ngày tuổi, có ~20 records liên quan
- `user.pending.D0` — User vừa register chưa verify (no shape needed - là single entity)
- `order.draft.D0.with_holes` — Order draft mới tạo, cart có item bị soft-deleted
- `subscription.trial.D14` — Subscription trial vừa hết hạn

## Data Matrix Schema cho UAT

Trong UAT file (Excel sheet "Data Matrix" + JSON `data_fixtures[]`):

```json
{
  "fixture_id": "user.pending.D0",
  "entity": "User",
  "state": "Pending",
  "lifecycle": "D0",
  "shape": "single",
  "description": "User vừa register, chưa verify email",
  "setup_recipe": {
    "type": "api",
    "endpoint": "POST /api/test/seed/user",
    "payload": {
      "email": "test.pending.{{random}}@test.com",
      "password": "Test@1234",
      "state": "Pending",
      "email_verified": false,
      "created_at": "{{now}}"
    }
  },
  "cleanup_recipe": {
    "type": "api",
    "endpoint": "DELETE /api/test/seed/user/{{user_id}}"
  },
  "outputs": {
    "user_id": "$.id",
    "email": "$.email",
    "verification_token": "$.verification_token"
  }
}
```

3 trường quan trọng:
- **`setup_recipe`** — Cách runner tạo data (API/SQL/factory)
- **`cleanup_recipe`** — Cách runner xóa data sau test
- **`outputs`** — Mapping field trả về để TC reference

## Setup recipe — 3 loại supported

### Loại 1: API seeding (RECOMMENDED — runner thực thi tự động)

```json
{
  "type": "api",
  "endpoint": "POST /api/test/seed/user",
  "headers": { "X-Seed-Token": "${SEED_TOKEN}" },
  "payload": { ... },
  "extract": {
    "user_id": "$.id",
    "auth_token": "$.token"
  }
}
```

Runner gọi endpoint trước test, lấy `user_id` để dùng trong TC.

**Yêu cầu app**: Phải có endpoint admin/seed dùng cho test (gated bằng `X-Seed-Token` hoặc env `NODE_ENV=test`).

### Loại 2: SQL seeding (khi không có API)

```json
{
  "type": "sql",
  "engine": "postgres",
  "connection_env": "TEST_DATABASE_URL",
  "queries": [
    "INSERT INTO users(email, status, created_at) VALUES('{{email}}', 'Pending', NOW()) RETURNING id"
  ],
  "extract": {
    "user_id": "row[0].id"
  }
}
```

Runner connect DB trực tiếp, execute SQL, lấy result.

### Loại 3: Factory function (in-memory, mock mode)

```json
{
  "type": "factory",
  "function": "createUser",
  "args": {
    "state": "Pending",
    "email_pattern": "pending.{{random}}@test.com"
  }
}
```

Cho mock mode — runner tạo object trong memory, intercept API call.

## Bảng "Data Matrix" sheet trong Excel

Sheet 6 mới trong file UAT, 11 columns:

| Col | Tên | Mô tả |
|-----|-----|-------|
| A | Fixture ID | `user.pending.D0` |
| B | Entity | User / Order / Subscription |
| C | State | Pending / Active / ... |
| D | Lifecycle | D0 / D7 / D30 |
| E | Shape | single / sparse / full |
| F | Mô tả | Free text |
| G | Setup type | api / sql / factory |
| H | Setup recipe | JSON inline hoặc reference |
| I | Cleanup recipe | JSON inline |
| J | Outputs | user_id, email, ... |
| K | TC sử dụng | TC-001, TC-005, ... (back-reference) |

## TC reference cách dùng

Trong Test Cases sheet, thêm cột mới **"Data required"** (sau cột Test data):

```
TC-005 | RED | P0 | Login | Login với user chưa verify
       | data_required: [user.pending.D0]
       | steps: 1. Login với user_id từ fixture
                2. Submit form
       | expected: Error "Vui lòng verify email"
```

Runner đọc `data_required` → trước test, gọi setup_recipe cho fixture đó → inject `user_id` vào test context → test dùng credential từ fixture.

## Ví dụ thực tế — Feature Login với 8 data fixtures

```json
[
  {
    "fixture_id": "user.active.D30",
    "description": "User active bình thường, 30 ngày tuổi",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Active", "email_verified": true, "created_at": "30 days ago" }
    }
  },
  {
    "fixture_id": "user.pending.D0",
    "description": "User vừa register chưa verify",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Pending", "email_verified": false }
    }
  },
  {
    "fixture_id": "user.suspended.D7",
    "description": "User bị admin lock 7 ngày trước",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Suspended", "suspended_at": "7 days ago" }
    }
  },
  {
    "fixture_id": "user.locked.D0",
    "description": "User bị auto-lock do brute force (5 fail trong 10 min)",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Active", "failed_login_count": 5, "locked_until": "15 min from now" }
    }
  },
  {
    "fixture_id": "user.deleted.D0",
    "description": "User soft-deleted vẫn còn trong DB",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Active", "deleted_at": "now" }
    }
  },
  {
    "fixture_id": "user.trial.D13",
    "description": "User trial sắp hết hạn còn 1 ngày",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Trial", "trial_ends_at": "1 day from now" }
    }
  },
  {
    "fixture_id": "user.trial_expired.D14",
    "description": "User trial vừa hết hạn 1 phút trước",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Trial", "trial_ends_at": "1 minute ago" }
    }
  },
  {
    "fixture_id": "user.dormant.D90",
    "description": "User active nhưng 90 ngày không login",
    "setup_recipe": { "type": "api", "endpoint": "POST /api/test/seed/user",
      "payload": { "state": "Active", "last_login_at": "90 days ago" }
    }
  }
]
```

**TC reference** (vd trong Test Cases sheet):
- TC-005 (Login pending fails) → `data_required: user.pending.D0`
- TC-010 (Locked account msg) → `data_required: user.locked.D0`
- TC-015 (Trial ending banner) → `data_required: user.trial.D13`
- TC-020 (Trial expired upgrade prompt) → `data_required: user.trial_expired.D14`
- TC-030 (Dormant reactivation flow) → `data_required: user.dormant.D90`

## Quy tắc bắt buộc khi viết UAT

### Rule 1: ≥1 fixture per state

Cho mỗi state của entity, BẮT BUỘC có ≥1 fixture trong matrix.

### Rule 2: ≥1 fixture per critical lifecycle stage

Cho mỗi mốc lifecycle quan trọng (trial_end, subscription_renewal, dormancy_threshold), có ≥1 fixture với `D` đúng.

### Rule 3: ≥1 shape extreme

Cho mỗi list-based entity (cart, orders, notifications), có ≥1 fixture với shape `empty` + ≥1 `full`/`large`.

### Rule 4: KHÔNG hardcode fixture data trong TC steps

❌ SAI:
```
TC-005 steps: 1. Tạo user pending bằng tay
              2. Login
```

✅ ĐÚNG:
```
TC-005 data_required: user.pending.D0
TC-005 steps: 1. Login với credentials từ fixture
              2. Verify error message
```

### Rule 5: Setup phải idempotent

Run setup 2 lần liên tiếp → cùng kết quả (không tạo duplicate). Dùng `email_pattern: "pending.{{random}}@test.com"` để unique.

### Rule 6: Cleanup BẮT BUỘC

Mỗi fixture phải có `cleanup_recipe`. Runner gọi cleanup sau test (afterEach). Tránh DB pollution.

## Template variables trong recipe

| Template | Value |
|----------|-------|
| `{{now}}` | Current timestamp ISO 8601 |
| `{{today}}` | YYYY-MM-DD |
| `{{random}}` | 8-char hex |
| `{{uuid}}` | UUID v4 |
| `{{D+7}}` | now + 7 days |
| `{{D-30}}` | now - 30 days |
| `{{user_id}}` | Reference output từ fixture trước (cross-fixture) |
| `{{env.VARNAME}}` | Env var |

## Multi-step fixture (compose từ nhiều fixture nhỏ)

Một số TC cần data phức tạp (vd: User Active + có 50 orders + 1 order pending refund). Compose:

```json
{
  "fixture_id": "user_with_pending_refund",
  "compose": [
    {"fixture_id": "user.active.D30"},
    {"fixture_id": "orders.normal.D7", "args": {"user_id": "{{user.active.D30.user_id}}", "count": 50}},
    {"fixture_id": "order.refund_pending", "args": {"user_id": "{{user.active.D30.user_id}}"}}
  ]
}
```

## Self-Audit checklist

Khi viết UAT, check:

- [ ] Mỗi state của entity có ≥1 fixture
- [ ] Lifecycle quan trọng (trial_end, expiry, etc.) có fixture với `D` đúng
- [ ] Shape extreme (empty + full) cho list entities
- [ ] Mỗi TC có `data_required` field reference fixture
- [ ] Mọi fixture có `setup_recipe` runnable bởi script
- [ ] Mọi fixture có `cleanup_recipe`
- [ ] `email_pattern` dùng `{{random}}` để tránh collision
- [ ] Compose fixtures cho TC phức tạp
