# Ví dụ UAT v9 — "Đăng ký tài khoản Web" (feature CRITICAL)

> Mẫu tham chiếu **đúng v9**: coverage-driven + TC_min ENSEMBLE + Coverage+Effectiveness Ledger + E2E + UI/UX + mutation. **KHÔNG** chạy theo "đủ N loại / ≥100 TC". Số TC = hệ quả coverage; giá trị = mutation + bug thật.

## 0. Authority Brief (oracle neo — Bước 0)
| rule_id | Quy tắc (nguồn) | Neo code |
|---|---|---|
| AUTH-EMAIL-FORMAT | Email hợp lệ RFC 5322 | `validators/email.ts` |
| AUTH-PW-STRENGTH | Mật khẩu ≥8, có hoa+ký tự đặc biệt (NIST 800-63B) | `validators/password.ts` |
| AUTH-DUP-EMAIL | Email trùng → 409, không lộ tồn tại (OWASP: chống user-enumeration) | `signup.service.ts` |
| AUTH-VERIFY | Tạo xong = trạng thái `Pending` tới khi verify email | `user.state` |
| AUTH-RATE | Chống spam đăng ký (rate-limit) | `guards/throttle` |

## 0.5 Plan Grounding
(Nếu có plan) — map mỗi `PLAN-T*`/`PLAN-FM*` vào TC. Ví dụ này: no active plan.

## TC_min — ENSEMBLE MAX (Bước 1)
- **M1** coverage items = AC(5)×2 + EP(email 4, pw 5) + BVA(pw-len 3-value 6) + decision(status×verify) + state(Anonymous→Pending→Active + sneak) + pairwise ≈ **~45**
- **M2** Σ cyclomatic V(G) (đo `lizard signup.service.ts validators/`) = controller 6 + service 14 + validators 12 ≈ **~32**
- **M3** FP^1.2: ~8 FP → 8^1.2 ≈ **~12**
- **M4** risk-tier = **CRITICAL 120** (auth/dữ liệu cá nhân)
- **TC_min = MAX(45, 32, 12, 120) = 120.** Auth rủi ro cao → sàn CRITICAL chi phối; phải đào coverage tới ~120 bằng 3-value BVA + decision đầy đủ + sneak path + security ASVS + E2E + UX (KHÔNG padding).

## Coverage+Effectiveness Ledger (Bước 6) — trích
| cov_id | Kỹ thuật | Coverage item | TC | TT |
|---|---|---|---|---|
| COV-AC-01 | AC | đăng ký hợp lệ → Pending + gửi verify | TC-001, TC-020 | ✅ |
| COV-EP-01..04 | EP email | rỗng / sai định dạng / hợp lệ / >254 ký tự | TC-010..013 | ✅ |
| COV-BVA-01..06 | BVA pw-len | 7/8/9 · (max-1)/max/(max+1) | TC-030..035 | ✅ |
| COV-DT-01..n | Decision | (email mới/trùng) × (pw mạnh/yếu) × (rate ok/quá) | TC-040..047 | ✅ |
| COV-ST-01 | State | Anonymous→Pending; sneak: login khi Pending → chặn | TC-050, TC-051 | ✅ |
| COV-SEC-01 | 25010 Security | user-enumeration: email trùng trả thông điệp TRUNG TÍNH | TC-060 | ✅ |
| COV-E2E-01 | E2E | journey: mở form → nhập → submit → thấy "kiểm tra email" → record Pending | e2e/signup.spec | ✅ |
| COV-UX-01..n | UX | Nielsen H5/H9 + states | (mục UI/UX) | ✅ |
→ coverage% = covered/total mỗi kỹ thuật (TÍNH từ bảng). 0 TC mồ côi.

## TC tiêu biểu (mỗi TC có oracle_type + rule_ref — KHÔNG "status 200" trần)
| tc_id | loại | title | oracle_type | rule_ref | expected (hành vi) |
|---|---|---|---|---|---|
| TC-001 | GREEN | Đăng ký email+pw hợp lệ | Purpose | AUTH-VERIFY | 201 + user `Pending` + email verify gửi (KHÔNG Active ngay) |
| TC-012 | EP/RED | Email sai định dạng | Statute | AUTH-EMAIL-FORMAT | 400 "email không hợp lệ" — không tạo user |
| TC-031 | BOUNDARY | pw đúng 8 ký tự (min) | Product | AUTH-PW-STRENGTH | 201 (biên min hợp lệ) |
| TC-030 | BOUNDARY | pw 7 ký tự (min-1) | Product | AUTH-PW-STRENGTH | 400 "tối thiểu 8" |
| TC-060 | SECURITY | Đăng ký email đã tồn tại | World | AUTH-DUP-EMAIL | 409 thông điệp TRUNG TÍNH (không "email đã tồn tại" lộ enumeration) |
| TC-051 | STATE | Login khi user `Pending` | Purpose | AUTH-VERIFY | chặn + "vui lòng xác minh email" |

## EFFECTIVENESS — Fault-Seeding (Bước 7b)
Bảng seeded-fault↔TC (spec-level — bổ trợ: `npx stryker run` trên unit test của `signup.service.ts validators/` nếu có):
| fault | Fault giả định vào rule | TC bắt |
|---|---|---|
| FLT-1 | đảo `if(pw.length>=8)` | TC-030/031 |
| FLT-2 | bỏ check email-trùng | TC-060 |
| FLT-3 | set status=Active thay Pending | TC-001/051 |
| FLT-4 | email-trùng trả message lộ enumeration | TC-060 (assert message trung tính) |
→ 0 fault sống sót.

## E2E + UI/UX (Bước 7b — feature có UI ⇒ BẮT BUỘC)
- **E2E** (Playwright, real backend/DB): journey đăng ký thành công → màn "kiểm tra email" → DB có user Pending. ≥1 PASS + evidence. Edge (email sai/pw yếu) → đẩy xuống API TC, KHÔNG nhồi E2E.
- **UI/UX** (`ui-ux-evaluation.md`): H5 error-prevention (disable Submit tới khi pw đạt), H9 error rõ ("thiếu ký tự đặc biệt", không mã lỗi), state loading/error, WCAG 2.2 (2.5.8 nút ≥24px, 3.3.8 cho dán mật khẩu). Severity ≥3 → Bug Tracker.

## Self-Audit (Bước 10) — trích
✅ Ledger có TC_min=MAX=120; tổng đạt 120 bằng coverage thật (0 padding) · ✅ 100% AC có TC, RTM 0 hở · ✅ mutation ≥80%/0 mutant sống · ✅ E2E journey PASS + UI/UX quét · ✅ mọi TC có oracle_type+rule_ref · ✅ security ASVS (enumeration/rate-limit) phủ.

> **Bài học mẫu:** auth ra ~120 TC vì **rủi ro cao + nhiều path (V(G))**, KHÔNG vì "phải ≥100". Một feature read-only đổi avatar tương tự chỉ ~30 TC mà vẫn đạt — coverage + mutation quyết định, không phải con số.
