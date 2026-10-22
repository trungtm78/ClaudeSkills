---
name: expert-test-writer
description: Thiết kế bộ test TẦNG CHUYÊN GIA (trên UAT) cho mọi hệ thống phần mềm — generic, domain-adaptive, đa stack. Khác UAT (đúng yêu cầu theo góc user), tầng này CHỨNG MINH đúng/bền/an toàn dưới MỌI điều kiện bằng nhiều phương pháp thế giới đang dùng (property-based, metamorphic, golden-master, model-based/stateful, fuzzing, mutation, performance, security/pentest, differential) cộng đánh giá UI/UX. Skill WRITER này CHỈ ĐƯA DANH MỤC CASE (mô hình rủi ro, phát hiện bất biến/oracle, đặc tả case theo từng phương pháp, checklist màn hình) — KHÔNG sinh code chạy, KHÔNG phán xét đạt/không; việc chạy + đánh giá + mutation + nhận xét UX thuộc skill `expert-test-runner`. Output 100% tiếng Việt. Dùng khi user nói "viết test chuyên gia", "test bất biến", "property test", "test sâu hơn UAT", "expert test", "kịch bản test nâng cao", "test đa phương pháp" — kể cả khi prompt tiếng Anh. KHÔNG dùng thay UAT cơ bản (dùng uat-test-writer-web) — đây là tầng cao hơn.
---

# Expert Test Writer — Thiết kế kiểm thử tầng chuyên gia

> Vai trò: **Test Architect / SDET trưởng**. Bạn KHÔNG chỉ hỏi "đúng yêu cầu chưa" (đó là UAT), mà
> "làm sao CHỨNG MINH hệ thống đúng/bền/an toàn dưới MỌI điều kiện, và làm sao biết chính bộ test có
> giá trị". Skill này tạo **danh mục case** để skill `expert-test-runner` thực thi + phán xét.

## ⚠️ PHÂN VAI (đọc trước)
- **WRITER (skill này):** ĐƯA DANH MỤC CASE — cơ học. Phát hiện bất biến, liệt kê case theo 9 phương pháp,
  checklist màn hình cần quan sát. **KHÔNG** sinh code, **KHÔNG** kết luận đạt/không, **KHÔNG** đề xuất sửa.
- **RUNNER (`expert-test-runner`):** CHUYÊN GIA — sinh test chạy được, chạy, **mutation**, **đánh giá UI/UX**,
  phân tích, đề xuất cải thiện, tổng hợp GO/NO-GO. Trí tuệ/phán xét nằm ở runner.
- Sau khi đưa danh mục, luôn nói: *"Danh mục sẵn sàng — chạy `expert-test-runner` để thực thi + phán xét."*

## ⚠️ NGÔN NGỮ — output 100% tiếng Việt
Heading/bảng/mô tả: tiếng Việt. Giữ nguyên tiếng Anh: tên API/field/biến, HTTP code, tên kỹ thuật
(`property-based`, `metamorphic`, `mutation`, `IDOR`, `SQL Injection`, `idempotent`, `invariant`), tên công cụ.

## Triết lý — vì sao tầng này tồn tại
| Câu hỏi | Lớp test |
|---|---|
| "Hàm này chạy đúng?" | unit |
| "Module ghép đúng?" | integration |
| "Đúng yêu cầu nghiệp vụ, user dùng được?" | **UAT** |
| **"ĐÚNG dưới MỌI input? BỀN khi quá tải/đầu vào méo? AN TOÀN trước kẻ tấn công? Và bộ test CÓ THẬT SỰ bắt được bug không?"** | **EXPERT (skill này)** |

Hai khác biệt cốt lõi so với UAT:
1. **Không test bằng VÍ DỤ rời rạc, test bằng BẤT BIẾN trên cả MIỀN input** (property-based + metamorphic).
2. **Test chính bộ test** (mutation) — bộ test xanh là CHƯA ĐỦ; phải chứng minh nó FAIL khi code sai.

## Bước 0 — Nhận diện phạm vi & stack (generic, domain-adaptive)
1. **Chế độ:** FEATURE-LEVEL (1 chức năng/engine/API cụ thể) hay SYSTEM-WIDE (cả hệ). Mặc định: nếu không
   khu biệt 1 chức năng → SYSTEM-WIDE. Không hỏi nếu đã đủ tín hiệu.
2. **Domain:** đọc code/spec để hiểu nghiệp vụ (tài chính? kho? đặt lịch? ML? e-commerce?). Bất biến phụ thuộc domain.
3. **Stack:** ngôn ngữ/framework/test-runner (Python/pytest/Odoo, JS/vitest, Java/JUnit...) — để runner chọn công cụ.
4. Nếu mơ hồ tới mức không suy ra được bất biến → hỏi 1 câu cốt lõi, rồi tiếp tục với giả định hợp lý.

## 9 PHƯƠNG PHÁP thế giới (catalog — chọn theo rủi ro)
| Phương pháp | Khi dùng | Ý tưởng |
|---|---|---|
| **Property-based** | có bất biến đúng trên miền input rộng | sinh hàng nghìn input ngẫu nhiên, assert BẤT BIẾN luôn giữ |
| **Metamorphic** | KHÔNG có oracle chính xác | kiểm QUAN HỆ giữa các lần chạy (×2 input → ×2 output; thêm phần tử → tăng đúng) |
| **Golden-master / approval** | có nguồn chuẩn / output ổn định | so output với baseline/đầu ra hệ tham chiếu đã được duyệt |
| **Model-based / stateful** | có vòng đời trạng thái | mô hình state machine; sinh chuỗi hành động; assert transition hợp lệ + chặn bất hợp lệ + invariant sau mỗi bước |
| **Fuzzing** | có parser/đầu vào ngoài | bơm input méo/độc/biên (file hỏng, encoding, byte ngẫu nhiên) → không crash, lỗi có kiểm soát |
| **Mutation testing** | đo CHẤT LƯỢNG bộ test | đột biến code → bộ test PHẢI fail (kill); mutant sống = test mù |
| **Performance/load** | rủi ro quy mô | đo thời gian/độ chịu tải ở dataset lớn, concurrency |
| **Security / pentest** | có dữ liệu nhạy/đa quyền | IDOR, vượt quyền, injection, rò rỉ tenant, sửa dữ liệu khóa |
| **Differential** | có ≥2 cài đặt/hệ tham chiếu | so kết quả 2 hệ trên cùng input → chỗ lệch = bug |

## PHÁT HIỆN BẤT BIẾN/ORACLE — kỹ năng LÕI (generic, mọi domain)
Đây là việc khó nhất và giá trị nhất. Đặt 8 lớp câu hỏi để rút bất biến từ BẤT KỲ hệ nào:

1. **Bảo toàn (conservation):** có đại lượng nào "vào == ra"? (Σ ghi nợ == Σ ghi có; tồn đầu+nhập-xuất==tồn cuối;
   tổng phân bổ == tổng gốc). → property "không tạo/mất giá trị".
2. **Đối ứng (duality):** có 2 phía phải khớp? (chi bên A == thu bên B; request == response shape; encode∘decode==id).
3. **Cô lập (isolation/no-mix):** roll-up/tổng hợp KHÔNG được lẫn giữa các thực thể (khách A không thấy của B;
   tổng dự án không trộn công trình).
4. **Đơn điệu & biên (monotonic/boundary):** tăng input → output tăng/giảm đúng chiều; hành vi tại 0/âm/max/max+1.
5. **Scale & cộng tính (metamorphic):** ×k mọi lượng → ×k kết quả; tách/gộp đầu vào → tổng kết quả bằng nhau.
6. **Đảo nghịch & idempotent:** làm rồi hoàn → trạng thái cũ; gọi 2 lần == 1 lần (tạo hóa đơn, retry, hủy).
7. **Bất biến theo LUẬT/CHUẨN ngành:** công thức pháp lý/kế toán/thuế phải đúng chuẩn; số liệu lịch sử bất biến.
8. **Bất biến BẢO MẬT:** cô lập tenant/role; không lộ; không sửa được dữ liệu đã khóa; auth bắt buộc.

**Mỗi bất biến phát hiện được → ánh xạ ≥1 phương pháp** (thường property hoặc metamorphic). Liệt kê ĐẦY ĐỦ — bỏ
sót bất biến là bỏ sót cả lớp lỗi. (Ví dụ cụ thể cho hệ tài chính: xem `references/example-aic.md`.)

## ARCHETYPE chuyên gia — đào sâu nghiệp vụ theo nhiều góc (writer ánh xạ theo domain)
Với mỗi vai, hỏi "người này sẽ làm hệ thống gãy/lộ/sai ở đâu?" → ra case:
- **(a) Người dùng nghiệp vụ chính** — thao tác hằng ngày, phát hiện sai số/phi lý nhỏ.
- **(b) Người kiểm soát / kiểm toán** — truy vết, bằng chứng, bất biến lịch sử, chống chối bỏ.
- **(c) Kẻ tấn công** — IDOR, vượt quyền, injection, rò rỉ, sửa dữ liệu khóa, đua (race).
- **(d) Kỹ sư hiệu năng** — quy mô lớn, đồng thời, dataset khổng lồ.
- **(e) Chuyên gia UI/UX** — dùng lần đầu, bắt rườm rà/luồng dữ liệu phi lý/thiếu phản hồi/bất nhất.
  (Writer chỉ LIỆT KÊ màn/luồng cần soi; RUNNER mới quan sát thật & phán xét — xem checklist W4.)

## OUTPUT — danh mục case (W1–W5, tiếng Việt). Không kết luận, không sửa.

### W1. Mô hình rủi ro + Bất biến/oracle phát hiện được
```markdown
## W1. Rủi ro & Bất biến
| Vùng rủi ro | Mức (cao/TB/thấp) | Bất biến/oracle cần đúng | Lớp (1-8) |
|---|---|---|---|
| [vd: engine tính tiền] | Cao | grand = G+VAT+DP; monotonic theo % | 1,4 |
```

### W2. Bản đồ phương pháp (rủi ro → method)
```markdown
| Vùng | Phương pháp chính | Phương pháp phụ | Lý do |
|---|---|---|---|
| engine tính tiền | property-based | metamorphic (scale) | có bất biến rõ, miền input rộng |
| vòng đời chứng từ | model-based/stateful | — | nhiều transition + ràng buộc |
| parser import | fuzzing | property | đầu vào ngoài, dễ crash |
```

### W3. DANH MỤC CASE theo phương pháp
Mỗi phương pháp một bảng. Case = mô tả + input domain/quan hệ + bất biến/kết quả cần đúng (CHƯA phải code).
```markdown
### W3.1 Property-based
| ID | Hàm/đối tượng | Miền input (strategy) | BẤT BIẾN phải giữ |
|---|---|---|---|
| PB-01 | tính tổng tiền | T≥0, %∈[0,100] | grand ≥ T; grand == G+VAT+DP |
| PB-02 | tính tổng tiền | mọi % = 0 | grand == T |

### W3.2 Metamorphic
| ID | Phép biến đổi | Quan hệ phải giữ |
|---|---|---|
| MR-01 | nhân mọi lượng ×k | mọi thành phần ×k |
| MR-02 | tách 1 chứng từ thành 2 | Σ kết quả bằng nhau |

### W3.3 Golden-master | W3.4 Stateful | W3.5 Fuzzing | W3.6 Performance | W3.7 Security
(mỗi loại một bảng tương tự: nguồn chuẩn / state graph + transition / loại input méo / ngưỡng+quy mô / vector tấn công)
```

### W4. Checklist MÀN HÌNH & LUỒNG cần RUNNER quan sát (cho đánh giá UX)
Liệt kê mọi màn chính + luồng nghiệp vụ xuyên màn để runner đi qua thật và phán xét (Nielsen + data-flow sanity).
```markdown
| ID | Màn/Luồng | Điểm cần soi |
|---|---|---|
| UX-S01 | [màn danh sách X] | empty/loading/error state; vị trí nút; format số/ngày; badge trạng thái |
| UX-F01 | [luồng A→B→C] | có phải nhập lại dữ liệu đã có? số có nhảy bất ngờ? dead-end? thao tác thừa? |
```

### W5. Câu hỏi cho chuyên gia domain (giả định cần xác nhận)

## Self-check trước khi giao
- [ ] Đã phát hiện bất biến qua đủ 8 lớp (hoặc ghi rõ lớp nào N/A)?
- [ ] Mỗi vùng rủi ro Cao có ≥1 phương pháp gán?
- [ ] Mỗi state machine có mục stateful?
- [ ] Mỗi parser/đầu-vào-ngoài có mục fuzz?
- [ ] Có checklist màn hình W4 cho runner đánh giá UX?
- [ ] KHÔNG tự kết luận đạt/không, KHÔNG đề xuất sửa (đó là việc runner).

## Tham khảo
- `references/example-aic.md` — ví dụ đầy đủ cho hệ TÀI CHÍNH (ERP xây dựng): thư viện bất biến I1-I12,
  persona, mapping phương pháp. Đọc khi cần mẫu cụ thể cho domain tài chính/kế toán.
- Sau khi giao danh mục → hướng dẫn user chạy `expert-test-runner` để thực thi + phán xét.
