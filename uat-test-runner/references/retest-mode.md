# Retest Mode — chạy lại chỉ TC lỗi

> Tách từ `SKILL.md` để giảm lượng chữ phải nạp mỗi lần gọi skill. Nạp khi cần.

## Retest Mode — Chạy lại CHỈ TC bị lỗi sau khi fix

> Dùng khi: user đã fix bug và muốn chạy lại để verify. **KHÔNG chạy lại toàn bộ suite**.

### Trigger tự động detect Retest Mode

Khi user nói:
- "chạy lại" / "retest" / "test lại sau fix" / "verify fix" / "run failed" / bất kỳ biến thể nào
→ Runner tự chuyển sang Retest Mode, **KHÔNG** quay lại Full Run.
→ **KHÔNG HỎI gì thêm** — tự dùng `scope=module` và chạy luôn.

Scope chỉ thay đổi khi user nói rõ trong prompt:
- "retest verify" / "chỉ chạy lại TC fail" → scope=verify
- "retest full" / "chạy lại tất cả" → scope=full
- Mặc định (không nói gì thêm) → **scope=module** (tự động)

### 3 Retest Scope (ISTQB standard)

| Scope | Khi nào dùng | TC chạy lại |
|-------|-------------|-------------|
| `module` | **DEFAULT** — fix bug thông thường | TC fail (confirmation) + **tất cả TC cùng module** (regression) |
| `verify` | Fix nhỏ, chắc chắn isolated | Chỉ đúng TC bị fail (dùng `--last-failed` khi Playwright ≥1.44) |
| `full` | Refactor lớn, đổi schema/auth/shared-infra, release candidate | Toàn bộ suite |

> **ISTQB: LUÔN cả hai** — *confirmation testing* (TC fail cũ đã fix chưa) **và** *regression testing* (fix có phá gì không) — retest đơn thuần KHÔNG đủ vì fix là nguồn defect mới hàng đầu. `module` là default vì cân bằng 2 việc đó.
> **Fix bug S1/S2**: thêm 1 phiên **exploratory ngắn quanh vùng fix** (bug nặng = vùng đó under-tested) — ghi charter + findings vào report.
> **`--only-changed` CHỈ là pre-check** (nó chọn theo test-file thay đổi, KHÔNG theo source code thay đổi — backend fix thuần chọn 0 test) — không dùng làm gate regression duy nhất; chọn TC theo module/risk-tag từ RTM + `--grep`.

### Retest Pipeline

```bash
# RT-1: Xác định scope — KHÔNG HỎI, tự detect từ prompt user
# "retest"           → module (default)
# "retest verify"    → verify
# "retest full"      → full

RETEST_SCOPE="module"  # ghi đè nếu user nói rõ verify/full

# RT-2: Build grep pattern theo scope (module map từ uat.json — KHÔNG dùng Excel)
GREP_PATTERN=$(python "$SKILL_SCRIPTS/extract_failed_tcs.py" \
  "test-results/$FEATURE-run/results_flat.json" \
  --uat-json "$UAT_JSON" \
  --scope "$RETEST_SCOPE" \
  --grep)
# Stderr sẽ in: "📋 Retest scope=module: 8 TC (3 fail + 5 cùng module)"
# Stderr sẽ in: "   Modules bị ảnh hưởng: Tạo vụ việc, Phân quyền"

echo "🔁 Retest: $GREP_PATTERN"

# RT-3: Chạy lại — API layer
npx playwright test --project=api \
  --grep "$GREP_PATTERN" \
  --reporter=json,line \
  --output=test-results \
  2>&1 | tee test-results/api-retest.log
true

# RT-4: Chạy lại — E2E layer
npx playwright test --project=e2e-chromium \
  --grep "$GREP_PATTERN" \
  --reporter=json,line \
  --output=test-results \
  2>&1 | tee test-results/e2e-retest.log
true

# RT-5: Flatten + ghi kết quả retest
python "$SKILL_SCRIPTS/flatten_pw_results.py" \
  "test-results/$FEATURE-run/api-results.json" \
  "test-results/$FEATURE-run/e2e-results.json" \
  "test-results/$FEATURE-run/results_flat.json"

# Cập nhật Excel nếu có (optional)
if [ -n "$EXCEL_FILE" ] && [ -f "$EXCEL_FILE" ]; then
  python "$SKILL_SCRIPTS/write_results_to_excel.py" \
    --excel-file "$EXCEL_FILE" \
    --results-file "test-results/$FEATURE-run/results_flat.json" \
    --mode retest
  python "$SKILL_SCRIPTS/recalc.py" "$EXCEL_FILE"
fi

# RT-6: Cập nhật retest-tc-ids.txt (chỉ giữ TC vẫn còn fail)
python "$SKILL_SCRIPTS/extract_failed_tcs.py" \
  "test-results/$FEATURE-run/results_flat.json" \
  --uat-json "$UAT_JSON" \
  --scope "$RETEST_SCOPE" \
  --output test-results/retest-tc-ids.txt

REMAINING=$(wc -l < test-results/retest-tc-ids.txt 2>/dev/null || echo 0)
echo "📊 Retest xong: $REMAINING TC vẫn còn fail"
```

### Retest Output Report

```markdown
## 🔁 KẾT QUẢ RETEST — [Ngày giờ] | scope=module

### Scope chạy lại
- **3 TC fail** cần verify fix
- **5 TC cùng module** "Tạo vụ việc" kiểm tra regression
- **Tổng**: 8 TC retest (không chạy lại 92 TC không liên quan)

| TC ID | Vai trò | Layer | Trước | Sau | Kết quả |
|-------|---------|-------|-------|-----|---------|
| TC-008 | fail→verify | E2E | Không đạt | Đạt | ✅ Fixed |
| TC-015 | fail→verify | API | Không đạt | Không đạt | ❌ Vẫn lỗi |
| TC-023 | fail→verify | E2E | Không đạt | Đạt | ✅ Fixed |
| TC-010 | same-module | E2E | Đạt | Đạt | ✅ Không regression |
| TC-011 | same-module | E2E | Đạt | Không đạt | ⚠️ REGRESSION! (severity +1; nếu TC-011 đã sign-off → thu hồi sign-off, cần re-approve) |

**TC vẫn còn fail**: 2 (TC-015, TC-011) → test-results/retest-tc-ids.txt
```

### Quy trình lặp Fix → Retest

```
Full Run (100 TC) → 3 fail: TC-008, TC-015, TC-023
           ↓
        Fix bug
           ↓
  Retest scope=module (8 TC = 3 fail + 5 cùng module)
           ↓
  TC-008 ✅ TC-023 ✅ | TC-015 ❌ TC-011 ⚠️ REGRESSION
           ↓
        Fix TC-015 + TC-011
           ↓
  Retest scope=module (TC-015 + cùng module TC-011)
           ↓
        All pass → Done ✅
```

> Mỗi vòng retest thu hẹp dần. TC đã pass và không cùng module không bị chạy lại.

