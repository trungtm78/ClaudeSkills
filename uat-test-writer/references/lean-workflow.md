# Lean Workflow Quick Reference — Token Saver

## Khi nào dùng LEAN mode

- User nói "lean", "ngắn gọn", "tiết kiệm token", "compact"
- Feature đơn giản (CRUD đơn thuần, không có business rule phức tạp)
- User đã có nhiều context trước đó, không muốn lặp lại

## Khi nào KHÔNG dùng LEAN

- Feature critical (payment, auth, data privacy)
- User yêu cầu "full", "enterprise", "deep analysis"
- Compliance feature (GDPR, PCI-DSS, HIPAA)

## So sánh FULL vs LEAN

| Khía cạnh | FULL | LEAN |
|-----------|------|------|
| Bước 1 Codebase | Đọc 8 artifacts | Đọc 3 (routes, DTOs, services) |
| Bước 2 Thinking | 15 dimensions × 3-5 fact | 8 dimensions ưu tiên × 2 fact |
| Bước 3-6 | Bảng chi tiết | Compact 1 bảng combined |
| Bước 7 Detail TC | UI + API + Side (3 expected) | 1 combined `expected` field |
| Bước 7 Batch size | 20 TC/batch | 30 TC/batch |
| Bước 9 Self-audit | 10 checkpoints | 5 checkpoints |
| Token output cost | 100% | ~40-50% |
| TC count | Same (≥100) | Same (≥100) |

## LEAN: 8 Priority Dimensions (thay vì 15)

1. Input space (mọi loại giá trị)
2. State space (mọi trạng thái entity)
3. Security (OWASP Top 10)
4. Authorization (role boundaries)
5. Business logic edge (discount, refund, prorate)
6. Error handling (failure modes)
7. Data integrity (DB lifecycle)
8. Accessibility (WCAG core)

Bỏ qua trong LEAN: Time, Concurrency, Network, Performance, Compat, i18n, Side effects, Regulatory (cover bằng pattern lib).

## LEAN Schema TC

```json
{
  "tc_id": "TC-001",
  "type": "GREEN",
  "priority": "P0",
  "module": "Login",
  "title": "Login thành công",
  "requirement": "REQ-AUTH-01",
  "technique": "Use Case",
  "risk_level": "Cao",
  "preconditions": "/login loaded",
  "steps": "1. Email\n2. Password\n3. Submit",
  "test_data": "alice@test.com / Valid@123",
  "expected": "HTTP 200, redirect /dashboard, session created",
  "severity_if_fail": "Critical",
  "notes": ""
}
```

Field `expected` (gộp) thay cho `expected_ui` + `expected_api` + `expected_side`.

## LEAN Batch Workflow

```python
# Batch 1: 30 TC GREEN + RED chính
# Sinh inline → ghi /tmp/tc_batch_1.json → confirm "30/100"

# Batch 2: 30 TC SECURITY + BOUNDARY  
# Ghi /tmp/tc_batch_2.json → confirm "60/100"

# Batch 3: 30 TC EP + STATE + DECISION + DATA
# Ghi /tmp/tc_batch_3.json → confirm "90/100"

# Batch 4: 15 TC A11Y + COMPAT + PERFORMANCE + INTEGRATION
# Ghi /tmp/tc_batch_4.json → confirm "105/100" ✅ PASS

# Merge
python scripts/merge_batches.py /tmp/tc_batch_*.json \
  --meta /tmp/feature_meta.json \
  -o /tmp/input.json

# Generate
python scripts/generate_uat_excel.py /tmp/input.json \
  /mnt/user-data/outputs/uat_<feature>.xlsx
python scripts/generate_uat_markdown.py /tmp/input.json \
  /mnt/user-data/outputs/uat_<feature>.md
python $SKILL_SCRIPTS/recalc.py \
  /mnt/user-data/outputs/uat_<feature>.xlsx
```

## RED Auto-Multiplier (LEAN shortcut)

Khi sinh RED case, dùng template multiplier sau cho từng input:

### Text input → 14 RED case template

```
1. Empty: "" → reject
2. Whitespace: "   " → reject
3. Min-1 length: (n-1 chars) → reject
4. Max+1 length: (n+1 chars) → reject
5. Type wrong: number cho text → reject
6. SQLi: "' OR '1'='1" → reject + audit
7. XSS: "<script>alert(1)</script>" → encode khi render
8. Path traversal: "../../etc/passwd" → reject
9. Unicode emoji: "🎉🎊" → handle hoặc reject rõ
10. RTL text: "مرحبا" → handle layout
11. Null byte: "valid\0extra" → reject
12. 10K chars (length attack) → reject hoặc truncate
13. HTML entities: "&lt;script&gt;" → handle đúng
14. Homograph: "аdmin" (Cyrillic) → reject hoặc canonical
```

### Email field → +8 case (tổng 22)

```
15. Missing @: "noemail" → reject
16. Missing domain: "user@" → reject
17. Double @: "u@@d.com" → reject
18. Space inside: "u s@d.com" → reject
19. > 254 chars → reject
20. IDN: "tést@dömain.com" → handle
21. Plus addressing: "u+tag@d.com" → accept
22. Quotes: "\"u\"@d.com" → handle
```

### Password field → +5 case (tổng 19)

```
15-19. Common passwords, no upper, no special, no number, brute force throttle
```

### Number field → 16 case

```
1-3. 0, -0, -1
4-6. 0.1+0.2 precision, Infinity, NaN
7-9. MAX_SAFE_INTEGER+1, scientific 1e308, negative zero
10-12. Leading zeros, hex 0xFF, comma "1,000"
13-16. Empty, null, type wrong, whitespace
```

### Date field → 16 case

```
1-3. 29/02 leap/not-leap, year 9999, year 0000
4-6. DST transition, timezone extreme, sub-second
7-9. Past/future expectation, format DD/MM vs MM/DD
10-12. Empty, null, type wrong
13-16. Locale-aware parsing, Unicode digit, negative time, milliseconds overflow
```

### File upload → 16 case

```
1-3. Empty file, 0 byte, oversized
4-6. Wrong format, polyglot, embedded EICAR
7-9. Malicious filename (../etc/passwd), Unicode filename, > 255 chars
10-12. MIME mismatch (actual ≠ declared), upload limit
13-16. Concurrent upload, mid-upload network drop, resume support, virus signature
```

### Per endpoint → 13 case

```
1-3. Happy 2xx, missing required field, wrong type
4-6. 401 no auth, 403 wrong role, 404 not exist
7-9. 409 conflict, 429 rate limit, 5xx server error
10-13. Wrong method, invalid Content-Type, CORS, idempotency
```

### Per state → 5 case

```
1. Entry: vào state này
2-3. Valid exit transitions
4. Invalid exit attempt (forbidden)
5. Concurrent transitions
```

### Per role → 4 case

```
1. Allowed action OK
2. Forbidden action → 403
3. Privilege escalation attempt
4. Cross-tenant access attempt
```

## Self-Audit LEAN (5 checkpoints)

```
✅/❌ Coverage 100% (AC+EP+BVA+decision+state) & tổng ≥ TC_min=MAX(M1,M2,M3,M4)
✅/❌ Effectiveness: bảng seeded-fault↔TC phủ guard/branch/biên chính (spec-level fault seeding — xem coverage-ledger.md; mutation tool chỉ bổ trợ tầng unit/integration)
✅/❌ E2E journey chính PASS (UI feature) + đã execute live
✅/❌ Coverage Ledger: 0 TC mồ côi, 0 padding, GAP có lý do
✅/❌ Loại áp dụng có ≥1 case; loại không áp dụng = N/A có lý do (không ép đủ)
```

Nếu fail bất kỳ → quay lại batch tiếp theo.

## Verbose to LEAN conversion

Nếu user đưa TC sẵn (verbose) và muốn LEAN-ify:

```python
# Gộp expected_ui + expected_api + expected_side → expected
for tc in test_cases:
    parts = []
    if tc.get("expected_ui"): parts.append(f"UI: {tc['expected_ui']}")
    if tc.get("expected_api"): parts.append(f"API: {tc['expected_api']}")
    if tc.get("expected_side"): parts.append(f"Side: {tc['expected_side']}")
    tc["expected"] = " | ".join(parts)
    # Có thể xoá 3 field cũ hoặc giữ tùy schema generator
```

Token saving: 3 field × ~50 chars = 150 chars → 1 field ~80 chars (gộp) = **45-50% giảm output per TC**.

## Khi LEAN không đủ → fallback FULL

Tự động chuyển từ LEAN → FULL khi:
- Coverage thật < TC_min sau các batch (chưa enumerate đủ path/partition)
- Mutation score < ngưỡng / có mutant sống sót không giải trình
- Feature thực ra là tier CRITICAL/HIGH (cần deep-thinking + E2E + UX đầy đủ)
- User reply "thêm chi tiết" cho TC cụ thể

Khi đó: viết bổ sung TC với full 3-expected schema, KHÔNG xóa lean TC cũ.
