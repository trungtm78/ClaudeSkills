---
name: expert-test-runner
description: Skill CHUYÊN GIA thực thi + ĐÁNH GIÁ + PHÂN TÍCH kiểm thử tầng chuyên gia (trên UAT) cho mọi hệ thống — generic, domain-adaptive, đa stack. Nhận danh mục case từ `expert-test-writer` (hoặc tự suy nếu thiếu), rồi: (1) phát hiện stack và chọn công cụ phù hợp (property-based hypothesis/fast-check/jqwik; mutation mutmut/cosmic-ray/Stryker/PIT; perf k6/locust; fuzz atheris/jazzer); (2) SINH test asset chạy được (property, metamorphic, golden-master, model-based/stateful, fuzzing, performance, security); (3) CHẠY và thu kết quả; (4) chạy MUTATION TESTING đo bộ test có thật sự bắt bug (kill rate) và chỉ ra mutant sống = lỗ hổng test; (5) QUAN SÁT hệ chạy thật để ĐÁNH GIÁ UI/UX — phát hiện bất thường thao tác màn hình, vô lý luồng dữ liệu (Nielsen + cognitive walkthrough + data-flow sanity) kèm ĐỀ XUẤT CẢI THIỆN cụ thể; (6) phân tích độ phủ bất biến; (7) tổng hợp NHẬN ĐỊNH CHUYÊN GIA + GO/NO-GO + sinh CI. Đây là nơi đặt trí tuệ/phán xét. Output 100% tiếng Việt. Dùng khi user nói "chạy expert test", "test chuyên gia", "mutation test", "đánh giá chất lượng test", "phân tích UX chuyên gia", "kiểm thử sâu" — kể cả prompt tiếng Anh.
---

# Expert Test Runner — Thực thi & Đánh giá tầng chuyên gia

> Vai trò: **Test Architect / SDET trưởng + UX expert + Security reviewer** gộp lại. Đây là nơi đặt
> TRÍ TUỆ và PHÁN XÉT. Writer chỉ giao danh mục; runner CHẠY, ĐO, QUAN SÁT, PHÂN TÍCH, ĐỀ XUẤT, KẾT LUẬN.

## ⚠️ NGÔN NGỮ — báo cáo 100% tiếng Việt. Code/locator/biến: tiếng Anh.

## Nguyên tắc bất di
1. **Bộ test xanh CHƯA ĐỦ.** Phải chạy MUTATION để chứng minh bộ test FAIL khi code sai. Không mutation = không kết luận chất lượng.
2. **Property > ví dụ.** Ưu tiên chứng minh bất biến trên hàng nghìn input, không vài case tay.
3. **Quan sát THẬT.** Đánh giá UX bằng cách đi qua màn hình chạy thật (browse/trình duyệt), không suy diễn từ code.
4. **Mỗi nhận xét UX kèm ĐỀ XUẤT cụ thể, khả thi.** Không chê suông.
5. **Không có oracle → metamorphic.** Không bỏ test chỉ vì khó tính kết quả đúng tuyệt đối.

## Quy trình 7 bước

### A. Phát hiện stack + chọn công cụ (generic)
- Nhận diện ngôn ngữ/framework/test-runner (đọc manifest, config, CI, memory/CLAUDE.md). Lấy **recipe chạy test của chính dự án**.
- Chọn bộ công cụ theo stack:

| Mục | Python | JS/TS | Java | Ghi chú |
|---|---|---|---|---|
| Property-based | `hypothesis` | `fast-check` | `jqwik` | sinh input ngẫu nhiên có shrink |
| Mutation | `mutmut` / `cosmic-ray` | `Stryker` | `PIT` | đo kill rate |
| Fuzzing | `atheris` / `hypothesis` | `fast-check` | `jazzer` | đầu vào méo |
| Performance | `locust` / seed-script | `k6` / `autocannon` | `JMeter`/`Gatling` | tải + đo thời gian |
| Golden-master | snapshot tự code | `jest --ci` snapshot | approvaltests | so baseline |

- Cài công cụ thiếu (pip/npm/maven). Nếu không cài được → ghi BLOCKED phương pháp đó, tiếp tục cái khác.
- **Lưu ý ORM/framework đặc thù** (vd Odoo: test chạy qua `odoo-bin --test-enable`, property dùng `@given` BÊN TRONG
  `TransactionCase`; không chạy hypothesis độc lập). Đọc `references/stack-notes.md` nếu có.

### B. Sinh & chạy test asset (map danh mục W3 → code chạy được)
- **Property:** mỗi PB → `@given(strategy)` + assert bất biến. Strategy đúng miền (vd `floats(min,max)`, `integers`).
- **Metamorphic:** chạy f(x) và f(T(x)), assert quan hệ (vd `f(k*x) == k*f(x)` trong tolerance làm tròn).
- **Golden-master:** đọc nguồn chuẩn / baseline đã duyệt → so output. Lần đầu chưa có baseline → tạo + cảnh báo "cần người duyệt baseline".
- **Stateful:** `RuleBasedStateMachine` (hypothesis) / model-based — rule = các hành động (action_*), `@invariant`
  kiểm bất biến sau mỗi bước, assert transition bất hợp lệ bị chặn (raise đúng).
- **Fuzzing:** bơm input méo (byte ngẫu nhiên, file hỏng, encoding lạ, ô rỗng, ký tự đặc biệt) vào parser → không crash, lỗi có kiểm soát.
- **Performance:** seed dataset lớn (N dòng) → đo thời gian thao tác chính < ngưỡng; concurrency nhẹ.
- **Security:** kịch bản tấn công (IDOR/vượt quyền/rò tenant/sửa dữ liệu khóa) → assert bị chặn.
- Chạy suite theo recipe dự án. Thu pass/fail + thời gian + shrunk counterexample khi property fail.

### C. MUTATION TESTING — đo chất lượng CHÍNH bộ test (chuyên gia)
- Chạy tool mutation trên **module logic lõi** (engine tính toán, máy trạng thái, kiểm tra quyền). Không mutate view/config.
- Thu **mutation kill rate** = mutant bị test giết / tổng mutant.
- **PHÂN TÍCH mutant SỐNG SÓT** (survivors): mỗi survivor = một thay đổi code mà bộ test KHÔNG phát hiện → lỗ hổng.
  Phân loại: (i) test còn thiếu → đề xuất test bổ sung cụ thể; (ii) mutant tương đương (equivalent) → ghi chú bỏ qua.
- Mục tiêu mặc định **kill rate ≥ 80%** trên module lõi; thấp hơn → liệt kê việc cần làm.

### D. ĐÁNH GIÁ UI/UX + LUỒNG DỮ LIỆU — quan sát hệ CHẠY THẬT (chuyên gia, lens thứ 10)
- Dùng browse tool / trình duyệt: đăng nhập, đi qua từng màn & luồng trong checklist W4 (writer giao) hoặc tự lập nếu thiếu.
- Đối chiếu **10 Nielsen heuristics + cognitive walkthrough + data-flow sanity**. Tự phát hiện:
  - **Bất thường thao tác màn hình:** nút đổi vị trí giữa màn; thiếu loading/spinner khi submit (rủi ro double-submit);
    thiếu empty/error/loading state; field bắt buộc không đánh dấu; statusbar/badge/màu không nhất quán; thiếu xác nhận
    trước thao tác phá hủy; thiếu tooltip icon; format số/ngày/tiền lệch nhau giữa màn.
  - **Vô lý luồng dữ liệu:** phải nhập lại dữ liệu đã có ở bước trước; số nhảy bất ngờ (giá lúc xem ≠ lúc duyệt);
    thao tác thừa; dead-end (không rõ bước tiếp); dữ liệu 2 độ sâu gây mất niềm tin; menu/màn trùng lặp.
- Chụp ảnh bằng chứng mỗi phát hiện (xem được bởi user).
- Bảng phát hiện: **mỗi dòng = mức độ (Cao/TB/Thấp) · loại · quan sát như user thật · tác động · ĐỀ XUẤT CẢI THIỆN cụ thể.**
- Tách bạch khỏi pass/fail chức năng — đây là *đánh giá*; nhưng lỗi UX nặng (gây sai nghiệp vụ/mất tiền) có thể chặn release.

### E. Phân tích ĐỘ PHỦ BẤT BIẾN
Bảng: mỗi bất biến (từ W1) → đã có property/metamorphic test chạy xanh chưa → cái nào HỔNG (chưa được kiểm).

### F. TỔNG HỢP NHẬN ĐỊNH CHUYÊN GIA + GO/NO-GO
```markdown
## Nhận định chuyên gia
- **Điểm mạnh:** [bất biến chứng minh được, mutation cao ở đâu]
- **Điểm yếu/rủi ro còn lại:** [mutant sống, bất biến hổng, UX nặng, perf]
- **Ưu tiên vá (xếp rủi ro):** 1... 2... 3...

## Bảng quyết định release
| Tiêu chí | Ngưỡng | Thực tế | Đạt? |
|---|---|---|---|
| Property mọi bất biến lõi xanh | 100% | …/… | … |
| Mutation kill rate (module lõi) | ≥80% | …% | … |
| Stateful: transition bất hợp lệ bị chặn | 100% | … | … |
| Fuzz parser không crash | 0 crash | … | … |
| Perf thao tác chính < ngưỡng (quy mô lớn) | đạt | … | … |
| UX: không lỗi nặng chặn nghiệp vụ | 0 | … | … |
| **Khuyến nghị** | | | **GO / NO-GO / GO có điều kiện** |
```

### G. CI gate
Sinh workflow CI (GitHub Actions/GitLab) chạy suite + (định kỳ) mutation; chặn merge nếu property/mutation tụt ngưỡng.

## Tiêu chí EXPERT-GRADE (self-audit — KHÔNG kết thúc nếu chưa đạt)
- [ ] Mỗi bất biến phát hiện có ≥1 property/metamorphic test chạy xanh.
- [ ] Mỗi state machine có stateful test (transition hợp lệ chạy + bất hợp lệ bị chặn + invariant giữ).
- [ ] Mỗi parser/đầu-vào-ngoài có fuzz (không crash).
- [ ] **Mutation kill rate ≥ 80%** trên module lõi; mỗi survivor đã phân tích (thiếu test / tương đương).
- [ ] Perf đo ở quy mô lớn, có số liệu.
- [ ] Golden-master vs nguồn chuẩn (nếu có; nếu chưa có dữ liệu chuẩn → BLOCKED, nêu rõ cần gì).
- [ ] **Mọi màn/luồng trong checklist đã quan sát thật; mỗi phát hiện UX có đề xuất cải thiện.**
- Chưa đạt ô nào → báo CHƯA HOÀN THÀNH + việc cần làm, KHÔNG nói "xong".

## Quan trọng
- **Property fail → in counterexample đã shrink** (input nhỏ nhất gây sai) — đó là bug thật, không phải nhiễu.
- **Đừng tăng kill rate bằng test rỗng.** Test bổ sung phải assert hành vi thật, không `assertTrue(True)`.
- **Mutation tốn thời gian** — chạy nền/giới hạn module lõi; báo "đang chạy" thay vì chặn.
- Tham khảo `references/example-aic.md` cho mẫu hệ tài chính (Odoo): cách viết property trong `TransactionCase`,
  stateful cho máy trạng thái nghiệm thu/hợp đồng, cosmic-ray cho models/.
