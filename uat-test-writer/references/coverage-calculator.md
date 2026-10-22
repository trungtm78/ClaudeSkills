# Coverage & Test Quantity — theo TIÊU CHUẨN QUỐC TẾ

## ⚠️ NGUYÊN LÝ CỐT LÕI (chuẩn quốc tế, KHÔNG phải con số tự đặt)

> **Số lượng test case KHÔNG phải mục tiêu — nó là HỆ QUẢ của độ phủ (coverage) đạt được trên không gian đặc tả/rủi ro thực tế.**

Không một tiêu chuẩn quốc tế nào quy định "tối thiểu N test case". Chúng quy định **tiêu chí phủ (coverage criteria)** + **mức độ theo rủi ro (risk-based)** + **tiêu chí hoàn thành (completion/exit criteria)**. Số TC **nảy sinh từ dưới lên (bottom-up)** khi ta liệt kê và phủ hết các *coverage item*.

**Neo chuẩn:**
- **ISO/IEC/IEEE 29119-4:2021** — *Test design techniques* + **coverage measures** cho từng kỹ thuật (mỗi kỹ thuật có công thức `coverage% = items covered / total items`).
- **ISO/IEC/IEEE 29119-1/-2 (2022/2021)** — risk-based testing; test completion criteria do dự án định nghĩa theo coverage + rủi ro.
- **ISTQB CTFL v4.0 (2023)** — `Coverage = (coverage items đã test / tổng coverage items) × 100%`; risk-based testing scale độ sâu theo mức rủi ro; exit criteria = coverage đạt + residual risk chấp nhận được.
- **ISO/IEC 25010:2023** — 9 đặc tính chất lượng = *cái gì cần phủ* (functional suitability, security, performance efficiency, compatibility, interaction capability/usability, reliability, maintainability, safety, flexibility).

→ **Bỏ "HARD FLOOR 100 TC" như một mệnh lệnh.** Thay bằng: phủ đủ coverage item → đếm xem ra bao nhiêu. Nếu một feature thật mà coverage-derived ra quá ít (vd < ~25–30), đó là **dấu hiệu under-analysis** (chưa liệt kê đủ partition/boundary/transition/rule) → đếm lại coverage item, KHÔNG phải "thêm TC cho đủ số".

---

## QUY TRÌNH ĐẾM TC (bottom-up, coverage-driven)

### Bước 1 — Requirement / AC coverage (xương sống UAT)
**Mục tiêu chuẩn: 100% acceptance criteria / requirement có ≥1 TC, truy vết 2 chiều (RTM).**
- Mỗi AC/requirement (gồm cả AC suy ra từ plan: `PLAN-T*`, `PLAN-FM*`) → ≥1 TC GREEN xác nhận + ≥1 TC negative cho điều kiện sai của AC đó.
- Đây là tiêu chí *bắt buộc đạt 100%* — UAT mà có AC không TC nào = **fail completion criteria** (29119-2).

### Bước 2 — Coverage item theo KỸ THUẬT THIẾT KẾ (ISO/IEC/IEEE 29119-4)
Với từng input/điều kiện/trạng thái, chọn kỹ thuật phù hợp và phủ **100% coverage item của kỹ thuật đó**:

| Kỹ thuật (29119-4) | Coverage item | Mục tiêu phủ | Số TC nảy sinh |
|---|---|---|---|
| **Equivalence Partitioning (EP)** | Mỗi phân vùng hợp lệ + KHÔNG hợp lệ | 100% partitions | = số partition (1 valid + nhiều invalid) |
| **Boundary Value Analysis (BVA)** | 2-value {min,max} ; **3-value {min−1,min,min+1,max−1,max,max+1}** | 100% boundaries (3-value khi rủi ro cao) | 2–3 điểm/biên × số biên |
| **Decision Table** | Mỗi rule/cột khả thi | 100% feasible rules | = số rule khả thi |
| **State Transition** | **0-switch** (mỗi transition hợp lệ) + transition KHÔNG hợp lệ (sneak path); rủi ro cao → **Chow N-switch** | 100% valid transitions + sneak paths | = #transitions + #cặp invalid |
| **Classification Tree / Combinatorial** | **Pairwise (all-pairs)** cho nhiều tham số; strength cao hơn khi rủi ro cao | t-wise coverage | tổ hợp all-pairs (≪ tích Descartes) |
| **Cause-Effect / Use-case / Scenario** | Mỗi luồng use-case / nhánh cause-effect | 100% main + alternate + exception | = số luồng |
| **Structure-based** (nếu có white-box) | Statement / Branch-Decision / **MC/DC** (hệ trọng yếu) | theo integrity yêu cầu | tùy độ phủ mục tiêu |

> **Mỗi input KHÔNG có "8 case cứng".** Số case/input = (số partition EP) + (số điểm biên BVA) + biến thể bảo mật/dữ liệu **nếu rủi ro yêu cầu**. Boolean có thể chỉ cần 2; field tiền tệ có range + định dạng + âm/0/overflow có thể cần 15+. **Coverage quyết định, không phải multiplier.**

### Bước 3 — Quality characteristics coverage (ISO/IEC 25010:2023)
Với MỖI đặc tính chất lượng *áp dụng được*, có ≥1 nhóm TC; độ sâu theo rủi ro:
- Functional suitability (correctness/completeness) — luôn áp dụng.
- **Security** — phủ theo OWASP ASVS/Top-10 *các mục liên quan* (không phải "10% cứng").
- **Compatibility / Interaction (a11y)** — phủ theo ma trận thiết bị/trình duyệt rủi ro + WCAG 2.2 A/AA *cho thành phần UI có trong feature*.
- Performance efficiency, Reliability — khi có SLA/timeout/đồng thời.
- Đặc tính KHÔNG áp dụng → ghi **N/A có lý do** (không bịa TC để đủ tỷ lệ).

### Bước 4 — Risk-based depth (ISO 29119-1 + ISTQB RBT)
Độ rộng & sâu test **tỷ lệ thuận mức rủi ro** = Likelihood × Impact:
- **Rủi ro cao** (tiền/dữ liệu/pháp lý/bảo mật): nâng kỹ thuật → BVA 3-value, Decision Table đầy đủ, N-switch, combinatorial strength cao, MC/DC.
- **Rủi ro thấp** (CRUD nội bộ, cosmetic): EP + happy + vài negative chính là đủ — KHÔNG ép thêm.

### Bước 5 — Completion / Exit criteria (ISO/IEC/IEEE 29119-2)
UAT "đủ" khi (KHÔNG phải khi "đạt N TC"):
1. **100% AC/requirement** có TC **và** đã execute (RTM 0 hở).
2. **Coverage target của các kỹ thuật đã chọn đạt 100%** (EP partitions, BVA boundaries, decision rules, valid state transitions, pairwise).
3. Các đặc tính 25010 áp dụng đều có TC (hoặc N/A có lý do).
4. **Residual risk** ở mức chấp nhận; **0 defect severity High/Critical mở**.
5. Mọi TC có **oracle** (rule/luật/AC) — không "status 200" trần.

---

## TỶ LỆ LOẠI TC — là HỆ QUẢ, không phải mục tiêu

Phân bố GREEN/RED/… **nảy sinh** từ coverage, KHÔNG cố định cứng:
- Vì *số partition KHÔNG hợp lệ + đường lỗi + transition sai* thường **nhiều hơn** happy path, nên RED **thường tự nhiên áp đảo** (hay gặp 40–70%).
- **RED thấp bất thường → KHÔNG "thêm RED cho đủ %"; mà là đã BỎ SÓT partition không hợp lệ / boundary / sneak path** → quay lại Bước 2. Tỷ lệ tự đúng.
- GREEN cao bất thường = thiếu negative coverage.
- Các con số "GREEN ≤20%, RED ≥40%…" chỉ là **SMELL TEST** phát hiện thiếu sót — **không phải ngưỡng tiêu chuẩn quốc tế** và KHÔNG được dùng để biện minh chèn TC tautology.

## PHÂN BỔ PRIORITY (risk-based, ISTQB)
P0/P1 thường chiếm phần lớn vì UAT là gate rủi ro cao — nhưng đây là **hệ quả của risk assessment**, không phải hạn ngạch áp đặt.

---

## SÀN TỐI THIỂU `TC_min` — ENSEMBLE: tính NHIỀU cách → lấy **MAX** (KHÔNG dùng LOC)

> Tính bằng nhiều phương pháp độc lập → **lấy số LỚN NHẤT** làm sàn (phương pháp khắt khe nhất quyết định → đảm bảo chất lượng, phủ trường-hợp-xấu-nhất). **"Test case per LOC" KHÔNG phải chuẩn — đã bỏ.**

```
TC_min = MAX(M1, M2, M3, M4)
```

- **M1 — Spec coverage items (black-box, nguồn CHÍNH; ISO/IEC/IEEE 29119-4):**
  `Σ(AC×2) + Σ(input·#partition EP) + Σ(boundary·{2|6} BVA) + Σ(decision rule khả thi) + Σ(state transition hợp lệ + sneak) + pairwise + Σ(đặc tính 25010 áp dụng·nhóm TC)`
- **M2 — Cyclomatic V(G) (white-box; McCabe basis-path):** `Σ V(G)` các hàm logic dưới test = **số TC tối thiểu để phủ branch/independent-path**. Đo bằng tool, KHÔNG đoán:
  - đa ngôn ngữ: `lizard <path>` · JS/TS: `npx eslintcc <path>` hoặc `ts` complexity rule · Python: `radon cc -s <path>` · Java: PMD/`metrics`.
  - V(G)=10 cho 1 hàm ⇒ ≥10 TC cho hàm đó. Tổng các hàm = sàn path-coverage.
- **M3 — Functional size (Capers Jones / ISBSG):** `ceil(FP^1.2)` nếu ước được Function Points (ISO/IEC 20926 IFPUG / 19761 COSMIC / 24570 NESMA). Bỏ qua nếu không có FP.
- **M4 — Risk-tier backstop (policy chống lười):** CRITICAL 120 · HIGH 80 · STANDARD 50 · LOW 25 — chỉ ràng buộc nếu nó là MAX.

**Bắt buộc ghi vào Ledger:** bảng `M1=… · M2=… · M3=… · M4=… · TC_min=MAX=…`. Minh bạch, ai cũng kiểm chứng được.

**Nếu coverage thật < `TC_min`:** KHÔNG padding — đào sâu coverage item (thường thiếu path so với M2/V(G)) cho tới khi đạt. `TC_min` là **báo động "đào chưa đủ"**, coverage là cách lấp HỢP LỆ.

### Ví dụ
- **"Đăng nhập" (CRITICAL):** M1≈150–220 (AC+EP+BVA 3-value+decision+state+OWASP) · M2=Σ V(G) auth ~80–120 · M4=120 → **TC_min=MAX≈150–220**. Auth nhiều path ⇒ tự nhiều TC.
- **"Đổi avatar" (LOW):** M1≈30 · M2 (1 handler) ~8–12 · M4=25 → **TC_min=MAX≈30**. Đủ coverage ở ~30 TC vẫn ĐẠT — ép lên 100 = padding.

---

## TÓM TẮT (điều phải nhớ)
1. **Đếm coverage item → ra số TC; `TC_min`=MAX(M1..M4).** Không đặt số tròn tùy tiện, không dùng LOC.
2. **100% AC + 100% coverage kỹ thuật + đặc tính 25010 áp dụng + tổng ≥ `TC_min` + effectiveness (mutation)** = tiêu chí hoàn thành.
3. **Rủi ro cao → kỹ thuật mạnh hơn → V(G) lớn → nhiều TC hơn** (hợp lý).
4. **Tỷ lệ loại/priority là hệ quả** — smell test, không phải mục tiêu để game.
5. **Thiếu TC = thiếu coverage item/path → đếm lại**, không chèn TC tautology.
