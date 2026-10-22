# Coverage + Effectiveness Ledger (Sổ phủ + hiệu lực) — cơ chế CHỐNG LƯỜI minh bạch

## Vì sao cần

"Coverage-driven" **dễ bị lười tinh vi**: tự nhận *"đã phủ 100%"* mà không thật sự liệt kê; hoặc phủ bằng TC **tautology giết 0 bug**. Hai lớp chống:
1. **Coverage minh bạch:** PHƠI BÀY từng coverage item ra bảng công khai TRƯỚC khi viết TC; coverage% **TÍNH từ bảng**, không tự nhận.
2. **Effectiveness (hiệu lực) = FAULT-SEEDING:** coverage ≠ chất lượng. Thước đo GIÁ TRỊ THẬT là **suite có bắt được fault cố ý gieo vào không**. *"Coverage 90% line vẫn miss cả mảng defect"* (research). TC không bắt được seeded-fault nào = **vô giá trị dù phủ đủ** → đây là cách bắt by-pass/token-guzzler đúng nghĩa.

> Nguyên tắc: **"Show your enumeration AND prove it kills faults."** Không Ledger → không có quyền nói coverage; không fault-seeding → không có quyền nói "test tốt".

## Sàn `TC_min` (ghi đầu Ledger — ENSEMBLE MAX)
Bảng bắt buộc: `M1 (coverage items)=… · M2 (Σ V(G) cyclomatic)=… · M3 (FP^1.2)=… · M4 (risk-tier)=… → TC_min = MAX = …`. Tổng TC thật phải ≥ `TC_min` BẰNG coverage thật (không padding). → `coverage-calculator.md`.

## Quy tắc bắt buộc (5)

1. **Enumerate-before-write.** Sinh Ledger (liệt kê coverage item) **trước** khi viết TC. Mỗi input/điều kiện/state/AC/đặc tính 25010 phải xuất hiện; cái nào 0 item = phải giải trình (vì sao không có partition/boundary).
2. **1 dòng = 1 coverage item**, có `cov_id`, kỹ thuật, item cụ thể, nguồn (code line/AC/rule_ref), và **TC phủ** (hoặc `GAP` + lý do). Cấm gộp mơ hồ.
3. **Coverage% TÍNH, không NHẬN:** `coverage = (#item có TC) / (#item tổng) × 100%` per kỹ thuật + tổng. Self-audit chép con số này.
4. **Không drop ngầm:** item không phủ = 1 dòng `GAP` có lý do nghiệp vụ/kỹ thuật — KHÔNG được biến mất khỏi bảng.
5. **Mỗi TC trỏ ngược ≥1 cov_id** (RTM 2 chiều). TC không trỏ cov_id nào = TC mồ côi (nghi padding) → xoá hoặc gắn item thật.

## Schema bảng (lưu trong `docs/uat/<feature>/_coverage-ledger.md`)

| cov_id | Kỹ thuật | Coverage item (cụ thể) | Nguồn | TC phủ | Trạng thái |
|---|---|---|---|---|---|
| COV-AC-01 | AC/Requirement | "Mẫu thiếu trường bắt buộc → bị khoá + báo thiếu" | rule PET-READY-BARE | TC-003,004 | ✅ |
| COV-EP-01 | EP (email) | partition: email rỗng | dto:55 | TC-012 | ✅ |
| COV-EP-02 | EP (email) | partition: email sai định dạng | dto:56 | TC-013 | ✅ |
| COV-EP-03 | EP (email) | partition: email hợp lệ | dto:55 | TC-001 | ✅ |
| COV-BVA-01 | BVA (độ dài pw) | min−1 (7 ký tự) | service:88 | TC-031 | ✅ |
| COV-BVA-02 | BVA (độ dài pw) | min (8) | service:88 | TC-032 | ✅ |
| COV-DT-04 | Decision Table | rule: status=Locked ∧ cred đúng → chặn | service:40 | — | ⛔ GAP: chưa seed user Locked (data) |
| COV-ST-02 | State Transition | sneak: Suspended → truy cập tài nguyên | guard:21 | TC-049 | ✅ |
| COV-25010-SEC-01 | 25010 Security | SQLi field bổ sung | OWASP A03 | TC-060,061 | ✅ |

→ Cuối bảng: **bảng tổng coverage%** per kỹ thuật (vd `EP 12/12=100% · BVA 10/12=83% (2 GAP) · DT 7/8 · ST 9/9 · AC 18/18`).

## Anti-laziness gate (Self-audit BẮT BUỘC — kiểm chứng được)

```
✅/❌ _coverage-ledger.md tồn tại & sinh TRƯỚC test_cases
✅/❌ Mỗi input/điều kiện/state/AC có ≥1 dòng Ledger (0 dòng = đã giải trình)
✅/❌ coverage% được TÍNH từ Ledger (không phải câu "đã phủ đủ" trống)
✅/❌ AC coverage = 100% (RTM 0 hở)
✅/❌ Mọi coverage item chưa phủ = dòng GAP có lý do (0 drop ngầm)
✅/❌ Mọi TC trỏ ≥1 cov_id (0 TC mồ côi/padding)
✅/❌ 0 "tương tự như trên" / "..." / placeholder trong steps|expected|input
✅/❌ Completeness-critic đã chạy: liệt kê "coverage item suýt bỏ sót" + đã xử lý
```

## Red flags LƯỜI BIẾNG (bắt ý nghĩ hợp lý hoá → STOP, quay lại enumerate)

| Ý nghĩ | Sự thật |
|---|---|
| "Feature đơn giản, nhiêu đây đủ" | Đủ hay không do **Ledger** quyết, không do cảm giác. Liệt kê đi rồi tính. |
| "Các case còn lại tương tự" | "Tương tự" = chưa enumerate. Mỗi partition/boundary là 1 dòng cụ thể. |
| "Rủi ro thấp nên bỏ" | Chỉ được giảm độ sâu khi có **risk-assessment ghi rõ** (Bước 4), không phải bỏ ngầm. |
| "Đã phủ 100%" (không có bảng) | Không Ledger = không có quyền nói %. |
| "Thêm vài TC nữa cho chắc" | Chống chỉ định ngược lại: thêm TC không gắn cov_id = padding. Chỉ thêm khi có item thật chưa phủ. |
| "Chạy được là pass" | Oracle = rule, không phải status. Evidence trước kết luận. |

## Completeness critic (đối kháng — chạy cuối Bước 6, trước khi chốt)

Tự hỏi (mutation-thinking) và GHI kết quả:
1. Input nào còn partition/boundary chưa có dòng Ledger?
2. State nào còn transition hợp lệ/sneak-path chưa phủ?
3. Decision rule tổ hợp nào (status × cờ × quyền) còn thiếu?
4. Đặc tính 25010 nào áp dụng mà chưa có nhóm TC?
5. AC/Plan-task (PLAN-T*/FM*) nào chưa map TC?
6. "Nếu tôi cố ý làm hỏng 1 dòng code, có TC nào bắt được không?" (mutation) — chỗ không bắt được = thiếu coverage.

→ Mỗi câu trả lời "có thiếu" = thêm dòng Ledger + TC, hoặc dòng GAP có lý do. **Không câu nào được bỏ trống.**

## EFFECTIVENESS — Fault-Seeding (giá trị thật, chống tautology/by-pass)

> ⚠️ **Mutation testing CLASSIC trên suite E2E/UAT = KHÔNG KHẢ THI** (consensus 2025-2026): chạy cả suite E2E một lần per mutant tốn giờ→ngày. KHÔNG đặt gate "mutation score ≥ X% ở acceptance level". Thay bằng tổ hợp dưới đây.

**Cách A — SPEC-LEVEL FAULT SEEDING (chính, luôn làm được):** bảng **seeded-fault ↔ TC** cho mọi business rule / guard / biên quan trọng — gieo fault GIẢ ĐỊNH vào RULE (không cần sửa code) rồi hỏi "TC nào sẽ fail?":

| fault_id | Fault giả định (vào business rule) | TC bắt nó | TT |
|---|---|---|---|
| FLT-01 | đảo điều kiện "bắt buộc chứng từ" → không bắt buộc | TC-072 | ✅ caught |
| FLT-02 | bỏ guard RBAC scope | TC-049 | ✅ caught |
| FLT-03 | lệch biên off-by-one độ dài/ngày hạn | TC-031 | ✅ caught |
| FLT-04 | đổi rate/công thức tính | TC-060 | ✅ caught |
| FLT-05 | nuốt lỗi (fail im lặng) thay vì báo | TC-029 | ✅ caught |
| FLT-06 | bỏ side-effect (không gửi notification/không ghi audit) | TC-026 | ✅ caught |

→ **Fault SỐNG SÓT (không TC nào bắt) = oracle trang trí / thiếu assert** → sửa: thêm/siết TC. Loại fault tối thiểu: **đảo điều kiện · off-by-one biên · đổi rate/toán tử · bỏ guard/validation · nuốt lỗi · bỏ side-effect**.

**Cách B — Mutation tool trên tầng THẤP HƠN (bổ trợ, khi repo có unit/integration):** StrykerJS/PIT/mutmut chạy trên **unit/integration test của cùng code path** (nhanh, khả thi) — mutation score tầng đó là proxy; và mutation trên **E2E support code** (page objects/factories/custom assertions — bug ở đây âm thầm làm yếu mọi E2E). Incremental/differential: chỉ mutate changed lines per PR.

**Cách C — API CONTRACT MUTATION (kỹ thuật mutation DUY NHẤT hợp acceptance level):** biến đổi request/response (đổi shape, status code, format, thiếu field) → client/consumer phải xử lý đúng (không crash, báo lỗi có kiểm soát). Áp dụng cho API smoke layer.

**Oracle-minimizer:** duyệt lại assertion — assertion nào không bắt được fault nào trong bảng → XOÁ (chống Assertion Roulette; suite gọn và mạnh hơn).

## ADVERSARIAL VERIFY (lớp 2 — Generation ≠ Evaluation)
Sau khi EXECUTE: 1 lượt ĐỐI KHÁNG cố **refute** mỗi TC "PASS" (giống code-review verify): assert có thực sự ràng buộc hành vi? Hay chỉ trùng input? Oracle có đúng rule? TC nào không đứng vững → hạ xuống FAIL/GAP, không tính là phủ.
