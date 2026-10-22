# Anti-patterns — 18 lỗi thường gặp khi viết UAT

Đọc khi review test case của user hoặc self-check trước khi gửi.

## NHÓM 1: COVERAGE GAPS (Lỗi nghiêm trọng nhất)

### Anti-pattern 1: Chỉ test happy path

❌ **Triệu chứng:** Bộ UAT 20 case, 15 GREEN, 3 RED, 2 EDGE.

✅ **Fix:** Tỷ lệ healthy: GREEN 10-15%, RED 30-40%, còn lại các loại khác.

**Lý do:** Bug ở production hầu hết là negative case mà QA không nghĩ tới. Happy path thường được dev test rồi.

---

### Anti-pattern 2: Boundary chỉ có "happy boundary"

❌ **Sai:**
```
TC: Test với 50 ký tự (trong range 10-100)
TC: Test với 80 ký tự (trong range 10-100)
TC: Test với 90 ký tự (trong range 10-100)
```

✅ **Đúng:**
```
TC: 9 ký tự (min-1, fail)
TC: 10 ký tự (min, pass)
TC: 11 ký tự (min+1, pass)
TC: 99 ký tự (max-1, pass)
TC: 100 ký tự (max, pass)
TC: 101 ký tự (max+1, fail)
```

**Lý do:** Bug ở off-by-one logic so sánh. `>` vs `>=` là source of countless bugs.

---

### Anti-pattern 3: Miss Security cases

❌ **Triệu chứng:** Bộ UAT cho login form không có:
- IDOR test
- Rate limit
- SQL injection
- Password hash verification
- Brute force protection

✅ **Fix:** Mỗi feature có form/API có user data PHẢI có ≥5 SECURITY case.

---

### Anti-pattern 4: Miss Accessibility hoàn toàn

❌ **Triệu chứng:** Bộ UAT cho form không có TC nào về keyboard, screen reader, contrast.

✅ **Fix:** Mỗi feature có UI PHẢI có ≥3 A11Y case (keyboard nav, screen reader, contrast).

**Lý do:** Vi phạm WCAG = rủi ro pháp lý (ADA Mỹ, EAA EU). Mất ~15% users.

---

### Anti-pattern 5: Miss Compatibility

❌ **Triệu chứng:** Test chỉ trên Chrome desktop.

✅ **Fix:** ≥3 COMPAT case (≥2 browser, ≥1 mobile).

---

### Anti-pattern 6: Không có Performance threshold cụ thể

❌ **Sai:**
> Expected: Response time đủ nhanh.

✅ **Đúng:**
> Expected: p50 <500ms, p95 <1.5s, p99 <3s với load 10 concurrent user.

---

## NHÓM 2: VIẾT TC LỜI BIẾNG

### Anti-pattern 7: "Tương tự cho các case khác"

❌ **Sai:**
```
TC-001: Test với email valid
TC-002: Test với email invalid (...tương tự cho các định dạng khác)
```

✅ **Đúng:** Viết HẾT mọi case, không ellipsis.

```
TC-002: Email thiếu @
TC-003: Email thiếu domain
TC-004: Email có space
TC-005: Email rỗng
TC-006: Email > 254 ký tự
...
```

---

### Anti-pattern 8: Test Steps vague

❌ **Sai:**
| Test Steps |
|------------|
| 1. Login<br>2. Tạo đơn<br>3. Verify |

✅ **Đúng:**
| Test Steps |
|------------|
| 1. Truy cập `/login`<br>2. Nhập "alice@test.com" vào ô Email<br>3. Nhập "Valid@123" vào ô Password<br>4. Click nút "Đăng nhập"<br>5. Verify redirect tới `/dashboard`<br>6. Click menu "Sản phẩm"<br>7. Chọn sản phẩm "iPhone 15" (ID: P001)<br>8. Click "Thêm vào giỏ"<br>9. Click icon giỏ hàng → "Thanh toán"<br>10. Nhập địa chỉ "123 Lê Lợi, Q1, HCM"<br>11. Chọn "Thanh toán COD"<br>12. Click "Đặt hàng" |

---

### Anti-pattern 9: Expected mơ hồ

❌ **Sai:**
- "Hệ thống xử lý đúng"
- "UI hiển thị phù hợp"
- "Có thông báo cho user"

✅ **Đúng:**
- "Popup hiển thị với title 'Thành công' và message 'Đơn hàng #DH-12345 đã được tạo'"
- "Nút 'Đặt hàng' chuyển sang state disabled, color #CCCCCC"
- "Email gửi tới địa chỉ đã đăng ký trong 60s với subject 'Xác nhận đơn hàng #DH-12345'"

---

### Anti-pattern 10: Thiếu Preconditions

❌ **Sai:**
| Preconditions |
|---------------|
| User đã login |

✅ **Đúng:**
| Preconditions |
|---------------|
| 1. User "alice@test.com" đã login với role Customer<br>2. Account có saved address "123 Lê Lợi, Q1, HCM"<br>3. Saved payment: VISA ending 1234<br>4. Giỏ hàng đang trống<br>5. DB có sản phẩm "iPhone 15" stock ≥1, price 25,000,000đ<br>6. Promotion "WELCOME10" active, Alice chưa dùng<br>7. Browser: Chrome 120, resolution 1920x1080 |

---

### Anti-pattern 11: Test Data placeholder

❌ **Sai:**
| Test Data |
|-----------|
| Email hợp lệ, password đủ tiêu chí |

✅ **Đúng:**
| Test Data |
|-----------|
| Email: alice.nguyễn@test.com<br>Password: Valid@Pass123 |

---

### Anti-pattern 12: Một TC test nhiều thứ

❌ **Sai:**
```
TC: Test toàn bộ flow checkout
Steps:
1. Login
2. Thêm sản phẩm
3. Apply coupon sai → báo lỗi
4. Apply coupon đúng → discount
5. Thanh toán fail → error
6. Retry → thành công
```

✅ **Đúng:** Tách thành ≥4 TC riêng:
- TC-001: Apply coupon hợp lệ (GREEN)
- TC-002: Apply coupon hết hạn (RED)
- TC-003: Thanh toán fail khi thẻ hết hạn (RED)
- TC-004: Retry thanh toán sau khi fail (RECOVERY)

**Lý do:** Mỗi TC test 1 concept. Fail thì biết ngay bug ở đâu.

---

## NHÓM 3: VẤN ĐỀ CẤU TRÚC

### Anti-pattern 13: TC phụ thuộc thứ tự chạy

❌ **Sai:**
```
TC-001: Tạo user mới
TC-002: Login với user vừa tạo (phụ thuộc TC-001)
TC-003: Tạo order với user (phụ thuộc TC-002)
```

✅ **Đúng:** Mỗi TC độc lập. Dùng Preconditions để setup state.

```
TC-002: Login với user hợp lệ
Preconditions: User "alice" đã tồn tại trong DB với status active (seed qua API admin)
```

---

### Anti-pattern 14: Không có Priority hoặc gán cảm tính

❌ **Sai:** 30 TC đều P1 hoặc không có Priority.

✅ **Đúng:** Risk-based:
- P0: ≥30% tổng (core flow, security)
- P1: ~40-50%
- P2: phần còn lại

---

### Anti-pattern 15: Không phân biệt UI vs API trong Expected

❌ **Sai:**
| Expected | Đặt hàng thành công |

✅ **Đúng (3 tầng):**
| Expected |
|----------|
| **UI:**<br>1. Redirect tới `/orders/{id}`<br>2. Toast "Đặt hàng thành công"<br>**API:**<br>3. `POST /api/orders` trả về 201<br>4. Response body khớp schema OrderResponse<br>**Side effects:**<br>5. Email confirmation gửi trong 60s<br>6. DB: 1 record mới trong `orders`<br>7. Inventory giảm 1 |

---

### Anti-pattern 16: Test data hardcode lặp lại

❌ **Sai:** 20 TC đều có cột Test Data viết đầy đủ "alice@test.com / Pass@123 / ..." → sửa email phải sửa 20 chỗ.

✅ **Đúng:** Define ở section Test Data, reference theo ID.

```
| Test Data | User U001 (xem mục 6.1)<br>Sản phẩm P001 (xem mục 6.2) |
```

---

## NHÓM 4: LẪN LỘN PHẠM VI

### Anti-pattern 17: Lẫn UAT với Unit/Integration test

❌ **Sai (Unit test):**
> Verify hàm `calculateTax(100, 0.1)` trả về 10

❌ **Sai (Integration test):**
> Verify message publish tới Kafka topic `orders.created`

✅ **Đúng (UAT):**
> Khi user đặt đơn hàng 100đ với thuế 10%, popup xác nhận hiển thị "Tổng: 110đ (đã bao gồm 10đ VAT)"

**Lý do:** UAT verify business outcome user-facing. Internal mechanism là integration test.

---

### Anti-pattern 18: Performance test sai loại

❌ **Sai (Load test - không phải UAT):**
> Test với 10,000 concurrent user trong 1 giờ

✅ **Đúng (Performance trong UAT):**
> Test với 10-20 concurrent user, verify response time <3s. Load test chuyên sâu (>100 user) dùng JMeter/k6 riêng.

---

## Template review test case của user

Khi user yêu cầu "Review test case tôi đã viết", dùng template này:

```markdown
## Review Summary

### A. Coverage Gap
| Loại bắt buộc | Hiện có | Đề xuất bổ sung |
|---------------|---------|------------------|
| GREEN | 5 TC | ✓ Đủ |
| RED | 3 TC | ❌ Thiếu — cần ≥8 TC. Đề xuất:<br>- Email rỗng<br>- Email không tồn tại<br>- Password sai 5 lần (account lock)<br>- Email > 254 ký tự<br>- ... |
| BOUNDARY | 0 TC | ❌ Thiếu hoàn toàn. Cần min-1/min/max/max+1 cho:<br>- Email length<br>- Password length |
| EP | 0 TC | ❌ Thiếu. Cần đại diện class:<br>- Email valid, invalid format, không tồn tại, đã verify, chưa verify |
| STATE | N/A | OK (feature không có state) |
| SECURITY | 1 TC | ❌ Thiếu nghiêm trọng. Cần thêm:<br>- IDOR test<br>- SQL injection<br>- XSS<br>- Rate limit<br>- Brute force protection<br>- Password hash verify |
| DATA | 0 TC | ❌ Thiếu. Cần:<br>- Email có dấu tiếng Việt<br>- Email viết HOA mixed<br>- Whitespace trim<br>- Emoji trong name |
| PERFORMANCE | 0 TC | ❌ Thiếu. Cần:<br>- Response time login <2s<br>- 10 concurrent login |
| A11Y | 0 TC | ❌ Thiếu hoàn toàn. Cần:<br>- Keyboard navigation<br>- Screen reader<br>- Contrast WCAG AA |
| COMPAT | 0 TC | ❌ Thiếu. Cần:<br>- Chrome desktop<br>- Safari iOS mobile<br>- Firefox |

**Tổng kết Coverage:** 9/55 case (16% coverage) — KHÔNG ĐẠT chuẩn enterprise. Cần bổ sung 46 case.

### B. Issues trong TC hiện có
| TC-ID | Vấn đề | Đề xuất sửa |
|-------|--------|--------------|
| TC-005 | Expected mơ hồ "hoạt động đúng" | Sửa thành 3 tầng (UI/API/Side effects) |
| TC-008 | Phụ thuộc TC-007 | Thêm precondition để chạy độc lập |
| TC-012 | Test data hardcode | Move vào section Test Data, reference theo ID |

### C. Điểm tốt
- Format bảng đầy đủ cột
- Có cột Requirement traceability
- ...

### D. Recommended Additions (CRITICAL)
1. [TC mới P0 SECURITY] IDOR ...
2. [TC mới P0 SECURITY] SQL injection ...
3. ... [list đầy đủ]

### E. Mức độ tin cậy của bộ UAT
**Đánh giá**: 🔴 KHÔNG ĐẠT chuẩn enterprise — chưa thể dùng cho release production.

**Lý do cụ thể**:
- Thiếu hoàn toàn 5 loại bắt buộc (BOUNDARY, A11Y, COMPAT, SECURITY đầy đủ, DATA)
- Tỷ lệ GREEN/total = 55% (chuẩn: ≤20%)
- Không có Risk Assessment
- Không có Exit Criteria

**Cần thiết để đạt chuẩn**: +46 TC, ~6-8 giờ làm việc.
```
