# Oracle Catalog & Traceability — "ĐÚNG là gì" (PHỔ QUÁT)

> Oracle = cơ chế nhận ra "có gì đó sai". Tester chuyên nghiệp KHÔNG chấm pass bằng `status 200` — họ chấm bằng **sự nhất quán với một nguồn chân lý**. Mỗi TC PHẢI khai báo `oracle_type` + `rule_ref`.
> Nền tảng: FEW HICCUPPS (Michael Bolton/James Bach), oracle problem, ISTQB acceptance types (CT-AcT v1.0; CTAL-TA v4.0/2025 cho risk-based), ISO/IEC 25010:2023 + ISO/IEC 25019:2023 (quality-in-use), **ISO/IEC/IEEE 29119-3:2021** traceability (chuẩn hiện hành — IEEE 829 đã bị THAY THẾ/superseded, không trích dẫn làm authority).

## Mục lục
- FEW HICCUPPS — 11 loại oracle
- Gán `oracle_type` cho từng TC + ví dụ
- Requirements Traceability Matrix (RTM)
- ISTQB acceptance types (UAT/OAT/RAT/CAT)
- ISO 25010:2023 — 9 đặc tính (checklist non-functional)
- Anti-pattern oracle (cấm)

---

## FEW HICCUPPS — 11 loại oracle (sản phẩm phải NHẤT QUÁN với…)

| Mã | Oracle | Nhất quán với… | Khi nào mạnh |
|----|--------|----------------|--------------|
| **F** | Familiarity | KHÔNG giống mẫu lỗi đã biết | regression |
| **E** | Explainability | giải thích mạch lạc được | hành vi lạ |
| **W** | World | sự thật thế giới thực | dữ liệu/định danh thật |
| **H** | History | phiên bản trước | regression, nâng cấp |
| **I** | Image | uy tín/thương hiệu | UX, ngôn từ |
| **C** | Comparable products | sản phẩm tương đương | so chuẩn |
| **C** | Claims | đặc tả/tài liệu/lời hứa | **spec, business rule** |
| **U** | User desires | điều user hợp lý mong | usability |
| **P** | Product | nhất quán nội bộ sản phẩm | dữ liệu sync, format |
| **P** | Purpose | mục đích tường minh/ngầm | hành vi cốt lõi |
| **S** | Standards & Statutes | **luật, quy định, chuẩn ngoài** | **regulated domain** |

**3 oracle mạnh & codify được nhất cho UAT** (ưu tiên dùng):
- **S (Standards/Statutes)** — oracle hạng nhất cho domain regulated. `rule_ref` = số điều luật/chuẩn (từ Domain Authority Brief).
- **C (Claims) + P (Purpose)** — business rule/đặc tả → sinh case "thử vi phạm", oracle = "hệ phải CHẶN".
- **P (Product)** — nhất quán nội bộ (sync 2 chiều, format mã `XX-YYYY-NNNNN`, tổng = các phần).

---

## GÁN `oracle_type` CHO TỪNG TC

Mỗi TC (trong JSON/Excel) thêm 2 field:
```json
{ "tc_id":"TC-018", "title":"...", "oracle_type":"Statute",
  "rule_ref":"<điều luật/chuẩn/rule_id trong _domain-pack>",
  "expected":"<hành vi đo được>" }
```
Quy tắc:
- TC business/luồng chính → `Claim`/`Purpose`/`Statute`.
- TC regulated (thời hạn, tuân thủ) → `Statute` + `rule_ref` = điều khoản.
- TC sync/format/toàn vẹn → `Product`.
- TC regression → `History`.
- TC usability/ngôn từ → `User`/`Image`.
- **Không oracle nào áp được → `oracle_type:"GAP"`** + ghi lý do. KHÔNG đặt expected = "status 200" trần trụi.

**Oracle declaration — 3 phần BẮT BUỘC** (bộ lọc hallucination cơ học):
1. `oracle_type` (1 trong 11 FEW HICCUPPS hoặc GAP)
2. `rule_ref` (id rule trong `_domain-pack.md` / AC id / điều luật)
3. `oracle_source` — **trích dẫn nguồn cụ thể**: `"Claims → SRS §4.2.1 bảng 3"`, `"Statutes → GDPR Art.17"`, `"Comparable → <sản phẩm> màn hình X"`. Assertion không trỏ được về requirement/rule/luật/chuẩn/sản-phẩm-so-sánh/mong-muốn-user-đã-nêu → REJECT.

⛔ **CẤM TUYỆT ĐỐI oracle "as per current behaviour" / "giống hành vi hiện tại"** — đó là tautology: lấy implementation làm chân lý thì mọi bug hiện hữu đều pass. Hệ quả: **sinh TC từ SPEC/requirement, KHÔNG sinh từ code implementation** (đọc code để tìm điểm neo/edge, nhưng expected phải đến từ nguồn chân lý độc lập với code).

**Kiểm tra sức oracle — mỗi TC phải trả lời được: "Bug CỤ THỂ nào TC này sẽ bắt được?"** Không trả lời được = TC trang trí → sửa hoặc bỏ. (Oracle-minimizer: assertion không đóng góp khả năng bắt bug nào → xoá; chống Assertion Roulette.)

Ví dụ (đo được, không hời hợt):
- ❌ "Tạo bản ghi → 201"
- ✅ `oracle_type:Statute, rule_ref:"<deadline rule>"` → "Tạo → thời hạn auto = N ngày theo <điều>, đúng ngày đáo hạn"
- ✅ `oracle_type:Purpose, rule_ref:"transition-map"` → "Trạng thái A KHÔNG được nhảy thẳng C → 422 nêu căn cứ"
- ✅ `oracle_type:Product` → "Sửa field X ở entity cha → sync sang entity con đã liên kết"

---

## REQUIREMENTS TRACEABILITY MATRIX (RTM) — tiêu chí "ĐỦ" mạnh nhất

Sinh 1 sheet/mục RTM: **mỗi AC / rule_ref ↔ ≥1 TC**.
```
| rule_ref / AC | nguồn | TC phủ | trạng thái |
| THOIHAN-A     | Đ.x   | TC-018, TC-061 | ✅ |
| SCOPE-B       | rule  | (chưa) | ❌ AC HỞ |
```
- **AC hở (0 TC) = chưa đủ** → bắt buộc bổ sung TC. Đây là gate "đủ" thay cho việc chỉ đếm số case.
- Mỗi AC tối thiểu: 1 happy + 1 negative + biên.
- TC mồ côi (không trỏ rule_ref nào) = nghi ngờ → review hoặc bỏ.

---

## ISTQB ACCEPTANCE TYPES — mở rộng ngoài UAT thuần

| Nhóm | Mục tiêu | Sinh case gì |
|------|----------|--------------|
| **UAT** | đáp ứng nhu cầu user/nghiệp vụ | persona-journey, business scenario |
| **OAT** (Operational) | sẵn sàng vận hành | backup/restore, **deploy→health**, seed, rollback, monitoring, phân quyền vận hành |
| **RAT** (Regulatory) | tuân thủ quy định | **đúng luật/chuẩn từ Authority Brief** — nhóm giá trị cao nhất cho regulated domain |
| **CAT** (Contractual) | đáp ứng hợp đồng | criteria nghiệm thu theo contract/SLA |

UAT đúng nghĩa là về **value & fit-for-use**, không chỉ bug-hunt → đảm bảo **100% journey nghiệp vụ chính có GREEN happy-path đại diện** (sign-off được), song song giữ RED ≥40% cho robustness.

---

## ISO/IEC 25010:2023 — 9 đặc tính (checklist non-functional, BẢN MỚI)

⚠️ Bản 2023 = **9 đặc tính** (2011 là 8): thêm **Safety**; đổi **Usability→Interaction Capability**, **Portability→Flexibility**. Chi tiết sub-characteristics đổi tên đáng chú ý:
1. Functional Suitability (completeness/correctness/appropriateness)
2. Performance Efficiency (time behaviour/resource/capacity)
3. Compatibility (co-existence/interoperability)
4. **Interaction Capability** (thay Usability) — thêm **inclusivity**, **self-descriptiveness**, **user engagement** (thay UI aesthetics), user assistance
5. Reliability — **faultlessness** (thay maturity), availability, fault tolerance, recoverability
6. Security — thêm **resistance** (chống tấn công) bên cạnh confidentiality/integrity/non-repudiation/accountability/authenticity
7. Maintainability (modularity/reusability/analysability/modifiability/testability)
8. **Flexibility** (thay Portability) — adaptability, **scalability**, installability, replaceability
9. **Safety** (MỚI, top-level) — operational constraint, risk identification, fail safe, hazard warning

Mỗi đặc tính áp dụng → ≥1 nhóm TC: Security→authz/scope/2FA + resistance; Reliability→recoverability (OAT); Safety→thao tác nguy hiểm có confirm/rollback; Interaction Capability→error message rõ, inclusivity/a11y.

⚠️ **Quality-in-use KHÔNG còn nằm trong 25010** — bản 2023 tách sang **ISO/IEC 25019:2023** (3 đặc tính). Câu hỏi UAT cốt lõi "*có dùng được cho NHÓM USER NÀY trong BỐI CẢNH NÀY không*" chấm theo 25019, đừng ghi "25010 quality-in-use" (cấu trúc đã withdrawn).

---

## ANTI-PATTERN ORACLE (lint cấm)

- `assert(true)` / assert lại đúng input vừa set (**tautology** — pass nhưng bắt 0 bug).
- expected = chỉ HTTP code, không nêu hành vi nghiệp vụ.
- assert state nội bộ trùng giả định code (tautological với implementation) thay vì outcome user thấy.
- TC không có `rule_ref` và không phải `GAP` có chú thích.
→ Mọi expected phải **trỏ nguồn** (rule/spec/observed run); ưu tiên assert **outcome quan sát được** (URL + text + DOM/giá trị trả về).
