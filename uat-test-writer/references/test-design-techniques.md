# Test Design Techniques — Chuẩn ISTQB

Tài liệu tham chiếu các kỹ thuật thiết kế test case chuẩn ISTQB Foundation Level. Đọc khi cần áp dụng đúng kỹ thuật cho từng loại input/feature.

## 1. Equivalence Partitioning (EP) — Phân lớp tương đương

### Nguyên lý
Chia input domain thành các "class" mà các giá trị trong cùng class được xử lý như nhau. Test 1 đại diện/class là đủ.

### Cách áp dụng

**Ví dụ: Field "Tuổi" (yêu cầu: 18-100)**

| Class | Đại diện test | Kỳ vọng |
|-------|---------------|---------|
| Hợp lệ: 18-100 | 50 | Pass |
| Invalid: <18 | 10, 17 | Fail |
| Invalid: >100 | 101, 150 | Fail |
| Invalid: âm | -5 | Fail |
| Invalid: 0 | 0 | Fail |
| Invalid: không phải số | "abc" | Fail |
| Invalid: decimal | 25.5 | Fail (nếu yêu cầu nguyên) |
| Invalid: trống | (empty) | Fail |

→ **8 class × 1 đại diện = 8 TC tối thiểu**

### Pattern bắt buộc cho EP

Mọi field input phải có TC cho:
1. ≥1 class hợp lệ
2. ≥1 class invalid format
3. ≥1 class invalid value
4. ≥1 class boundary (sẽ test sâu hơn ở BVA)

## 2. Boundary Value Analysis (BVA)

### Nguyên lý
Bug thường nằm ở ranh giới. Mỗi giới hạn cần test ±1.

### Pattern 6 điểm cho mỗi giới hạn

Cho range [min, max]:

```
min-1  |  min  |  min+1  |  ...  |  max-1  |  max  |  max+1
 FAIL  | PASS  |  PASS   |       |  PASS   | PASS  |  FAIL
```

### Ví dụ: Password length 8-128

| Giá trị | Loại | Kỳ vọng |
|---------|------|---------|
| 7 ký tự | min-1 | FAIL |
| 8 ký tự | min | PASS |
| 9 ký tự | min+1 | PASS |
| 127 ký tự | max-1 | PASS |
| 128 ký tự | max | PASS |
| 129 ký tự | max+1 | FAIL |

→ **6 TC bắt buộc cho 1 field có range**

### BVA cho non-numeric

| Field | Boundary |
|-------|----------|
| Email length | 0, 1, 254, 255 (RFC) |
| Date | hôm qua, hôm nay, ngày mai, 1900-01-01, 9999-12-31 |
| Time | 00:00:00, 23:59:59, leap second 23:59:60 |
| File size | 0 byte, 1 byte, max, max+1 |
| Array length | 0 items, 1 item, max items, max+1 |
| Decimal precision | 0.001, 0.01, 99.99, 100.00 |

## 3. Decision Table Testing

### Nguyên lý
Khi business rule có nhiều điều kiện kết hợp, dùng decision table để cover mọi combination.

### Cách xây dựng

**Ví dụ: Rule "Áp dụng giảm giá VIP 20%"**

Điều kiện:
- C1: User là VIP member
- C2: Đơn hàng ≥ 500k
- C3: Trong thời gian promo

Decision Table:

| # | C1 (VIP) | C2 (≥500k) | C3 (promo) | Action: Giảm 20% |
|---|----------|------------|------------|------------------|
| 1 | T | T | T | ✅ Có |
| 2 | T | T | F | ❌ Không |
| 3 | T | F | T | ❌ Không |
| 4 | T | F | F | ❌ Không |
| 5 | F | T | T | ❌ Không |
| 6 | F | T | F | ❌ Không |
| 7 | F | F | T | ❌ Không |
| 8 | F | F | F | ❌ Không |

→ **2^n combinations với n điều kiện = 8 TC cho 3 điều kiện**

Có thể rút gọn bằng "Don't care" khi 1 điều kiện không ảnh hưởng kết quả, nhưng **mặc định nên test full**.

### Khi nào BẮT BUỘC dùng Decision Table

- Feature có ≥2 điều kiện boolean kết hợp
- Pricing rule, discount rule, eligibility rule
- Permission/access control
- Approval workflow

## 4. State Transition Testing

### Nguyên lý
Feature có "state" → mỗi transition cần test, mỗi action không hợp lệ ở mỗi state cần test.

### Cách xây dựng

**Ví dụ: Order lifecycle**

```
[Draft] --submit--> [Pending] --approve--> [Approved] --pay--> [Paid] --ship--> [Shipped] --deliver--> [Delivered]
   |                    |                                                                      |
   |                    +--reject--> [Rejected]                                                |
   |                                                                                          |
   +--cancel--> [Cancelled]                                                                   |
                                                                                              |
                                                                          [Returned] <--return--+
```

### TC bắt buộc

#### A. Valid transitions
| TC | Từ state | Action | Tới state |
|----|----------|--------|-----------|
| 1 | Draft | submit | Pending |
| 2 | Pending | approve | Approved |
| 3 | Pending | reject | Rejected |
| 4 | Approved | pay | Paid |
| ... | ... | ... | ... |

→ Mỗi mũi tên = 1 TC. Với 10 mũi tên = 10 TC.

#### B. Invalid transitions (Quan trọng — thường bị miss)
| TC | Từ state | Action không hợp lệ | Kỳ vọng |
|----|----------|---------------------|---------|
| ... | Draft | approve | Lỗi: chưa submit |
| ... | Draft | pay | Lỗi: chưa approve |
| ... | Delivered | cancel | Lỗi: đã giao |
| ... | Cancelled | submit | Lỗi: đã hủy |

→ Với N state × M action = N×M combinations, trừ valid → tất cả còn lại là invalid.

#### C. Edge state cases
- Race condition: 2 user cùng approve 1 order
- Idempotency: gọi `pay` 2 lần liên tiếp
- Compensation: refund sau Delivered

## 5. Use Case Testing

### Nguyên lý
Test theo flow nghiệp vụ end-to-end, không phải từng function.

### Pattern

Mỗi use case có:
- **Main success scenario** (happy path)
- **Alternative flow** (rẽ nhánh)
- **Exception flow** (lỗi)

**Ví dụ: Use case "Đặt hàng"**

Main success scenario:
1. User vào trang sản phẩm → 2. Thêm vào giỏ → 3. Vào giỏ → 4. Checkout → 5. Nhập địa chỉ → 6. Chọn phương thức thanh toán → 7. Confirm → 8. Nhận đơn hàng

Alternative flows:
- A1 (sau bước 2): User tiếp tục mua thêm
- A2 (sau bước 5): User dùng địa chỉ đã lưu
- A3 (sau bước 6): User apply coupon

Exception flows:
- E1 (sau bước 4): Sản phẩm hết hàng giữa flow
- E2 (sau bước 6): Thẻ bị từ chối
- E3 (sau bước 7): Server timeout

→ Mỗi flow = 1 TC.

## 6. Error Guessing

### Nguyên lý
Dùng kinh nghiệm để đoán "chỗ nào dễ bug". Không có pattern cứng, nhưng có checklist common errors.

### Checklist Error Guessing

#### Boundary "không rõ ràng"
- Tháng có 28/29/30/31 ngày
- Năm nhuận (29/02)
- Giờ chuyển DST
- Cuối tuần / ngày lễ
- Số 0 (zero), negative, infinity
- Empty array/string/object

#### Concurrent action
- 2 user cùng edit
- User logout ở tab này, action ở tab kia
- Submit nhanh 2 lần liên tiếp
- Network slow + user click nhiều lần

#### Input "lạ"
- Whitespace only
- Hidden character (zero-width space, BOM)
- Right-to-left text mark
- Combining diacritical marks
- Emoji
- Long string copy-paste

#### Recovery
- Refresh giữa flow
- Back button browser
- Close tab giữa upload
- Mất mạng giữa submit
- Browser cache cũ

#### Time-related
- Phiên hết hạn ngay khi dùng
- Token vừa expire vừa được dùng
- Schedule cho thời gian quá khứ
- Date cuối tháng + 1 tháng (31/01 → ?)

## 7. Exploratory Testing (cho EDGE cases)

### Nguyên lý
Test mà không có script cứng — dựa vào tò mò và kinh nghiệm.

### Heuristic "FEW HICCUPPS" của James Bach

| Chữ | Heuristic |
|-----|-----------|
| **F** | Familiar — đã gặp bug tương tự ở đâu? |
| **E** | Explainability — có thể giải thích cho user? |
| **W** | World — phù hợp với common sense? |
| **H** | History — version trước hoạt động sao? |
| **I** | Image — phù hợp brand/image? |
| **C** | Comparable products — đối thủ làm sao? |
| **C** | Claims — đúng với marketing/spec? |
| **U** | User expectations — user muốn gì? |
| **P** | Product — nhất quán trong product? |
| **P** | Purpose — đáp ứng mục đích? |
| **S** | Standards — chuẩn ngành? |

→ Mỗi heuristic có thể sinh ra ý tưởng EDGE case.

## 8. Pairwise / Combinatorial Testing

### Nguyên lý
Khi có nhiều input combination, không thể test full (combinatorial explosion). Pairwise test phủ mọi cặp 2 input.

### Ví dụ

Feature có 3 input, mỗi input có 3 giá trị:
- Browser: Chrome, Firefox, Safari
- OS: Windows, macOS, Linux
- Resolution: 1920, 1366, 768

Full combination: 3³ = 27 TC.
Pairwise: 9 TC (vẫn cover mọi cặp).

Tool: PICT (Microsoft), Allpairs.

### Khi nào BẮT BUỘC pairwise
- Compatibility testing với >3 browser/OS/resolution
- Feature config với nhiều toggle
- Multi-language × multi-currency × multi-timezone

## 9. Risk-Based Testing

### Nguyên lý
Test nặng vào khu vực rủi ro cao, ít vào khu vực rủi ro thấp.

### Risk matrix

```
                    Tác động nếu fail
                Thấp    TB      Cao
            +-------+-------+-------+
Xác suất    | P3    | P2    | P1    |  Cao
xảy ra      +-------+-------+-------+
            | P3    | P2    | P1    |  TB
            +-------+-------+-------+
            | P3    | P3    | P2    |  Thấp
            +-------+-------+-------+
```

### Risk drivers (yếu tố tăng risk)
- Code mới (chưa stable)
- Code complex (cyclomatic complexity cao)
- Code thay đổi nhiều gần đây
- Tính năng quan trọng business
- Liên quan tiền/data nhạy cảm
- Có legal/compliance impact
- Có history nhiều bug

## ⭐ Example Mapping (Three Amigos) — chạy TRƯỚC mọi kỹ thuật trên

Workshop 4 loại thẻ cho mỗi story: **vàng** = story · **xanh** = business rule · **lục** = example minh hoạ rule · **đỏ** = câu hỏi/không rõ.

Quy trình: liệt kê rules → mỗi rule ≥1 example cụ thể (data thật) → điều gì không trả lời được ghi thẻ đỏ.
- **Thẻ đỏ = requirement-defect được ngăn TRƯỚC khi code** — ĐẾM và BÁO CÁO số thẻ đỏ (leading ROI metric; ~56% defect gốc từ requirement phase).
- Mỗi example (lục) → 1 Gherkin scenario; mỗi rule (xanh) → 1 nhóm scenario.

## ⭐ DMN / BPMN — mô hình hoá để derive TC cơ học (CT-AcT ch.4)

- **Business rule → Decision Table (DMN)**: mỗi rule combination khả thi = 1 coverage item đếm được → "đã nghĩ đủ chưa?" thành câu hỏi ĐẾM được.
- **Business process → BPMN path**: happy path + mọi exception path + compensation → mỗi path = 1 coverage item (`COV-BP-*`).
- Đây là cầu nối sạch nhất giữa BA và tester — bảng/diagram review được trước khi TC tồn tại.

## ⭐ Gherkin declarative — format TC nghiệp vụ

Quy tắc cứng:
1. **1 rule / 1 scenario** — rule phức hợp thì tách.
2. **Declarative, KHÔNG UI mechanics**: "Given đơn hàng đã thanh toán" ✅ / "Given click nút Pay rồi đợi 2s" ❌. (UI mechanics thuộc về runner/locator_hint.)
3. `Scenario Outline` + `Examples` cho bộ EP/BVA — mỗi hàng Examples map 1 coverage item.
4. Tag: `@P0 @S2 @journey-checkout @android @COV-DT-04` — risk/severity/journey/platform/coverage đều filter được.
5. Then phải đo được + trỏ oracle_source — không "Then hệ thống hoạt động đúng".

## ⭐ Metamorphic Testing — khi KHÔNG có expected value chính xác

Dùng cho search/ranking/pricing/report tổng hợp/gợi ý/AI feature: thay vì expected tuyệt đối, assert **QUAN HỆ giữa 2 lần chạy** khi biến đổi input.

| Biến đổi input | Quan hệ output phải giữ (metamorphic relation) |
|---|---|
| Thêm filter vào search | kết quả mới ⊆ kết quả cũ |
| Đổi thứ tự input list | output không đổi (tính giao hoán) |
| Nhân đôi số lượng item | tổng tiền × 2 (tuyến tính) |
| Đổi đơn vị tiền tệ | tổng quy đổi tương đương (± rounding rule) |
| Thu hẹp khoảng ngày báo cáo | tổng con ≤ tổng cha |

TC METAMORPHIC khai báo `metamorphic_relation` trong handoff schema. Với feature AI/non-deterministic: assert **behavioural bounds qua N lần chạy** (khoảng chấp nhận), không phải single-run equality.

## Summary checklist khi áp dụng techniques

Cho mỗi feature, đảm bảo đã apply:

- [ ] **Example Mapping** trước tiên (rules/examples/questions — báo cáo số thẻ đỏ)
- [ ] **DMN/BPMN** khi có business rule/process đa nhánh
- [ ] **EP** cho mọi field input (mỗi class ≥1 TC)
- [ ] **BVA** cho mọi field có giới hạn (±1 boundary — giá trị biên HAND-CODE, không Faker)
- [ ] **Decision Table** nếu có ≥2 condition kết hợp
- [ ] **State Transition** nếu feature có state
- [ ] **Use Case** cho flow nghiệp vụ chính
- [ ] **Gherkin declarative** cho TC nghiệp vụ (1 rule/scenario, Scenario Outline cho EP/BVA)
- [ ] **Metamorphic** nếu không có expected chính xác
- [ ] **Error Guessing** dựa checklist trên
- [ ] **Exploratory** áp dụng FEW HICCUPPS (charter-scoped + evidence)
- [ ] **Pairwise** nếu có >3 combination dimension
- [ ] **Risk-based** để assign priority
