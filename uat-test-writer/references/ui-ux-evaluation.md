# UI/UX Evaluation — chuẩn quốc tế (ISO 9241-11 + Nielsen 10 + WCAG 2.2)

> Feature có UI: ngoài chức năng, BẮT BUỘC đánh giá **trải nghiệm**. Mỗi phát hiện → 1 dòng `COV-UX-*` trong Ledger (heuristic vi phạm + severity + đề xuất). Đánh giá khi đang chạy E2E live (Bước 7b).

## 1. ISO 9241-11:2018 — 3 trục usability (khung tổng)
Usability = mức product giúp user đạt mục tiêu với:
- **Effectiveness** — hoàn thành task ĐÚNG & ĐỦ? (task success rate). TC: persona thực hiện journey → đạt mục tiêu không lỗi?
- **Efficiency** — tốn bao nhiêu công/bước/thời gian? (số click, time-on-task, đường vòng). TC: đếm bước thừa, loading chặn.
- **Satisfaction** — dễ chịu/tin tưởng? Đo bằng **SUS (System Usability Scale)** khi có user thật; nếu không, đánh giá heuristic.

**SUS gate ĐỊNH LƯỢNG (khi đo được):** 10 câu Likert 5 điểm; chuẩn diễn giải: <50 không chấp nhận · 50-70 marginal · **>68 = trên trung bình (ngưỡng chuẩn)** · 80+ xuất sắc. Tiêu chí acceptance viết dạng kiểm chứng được: **"≥80% participants đạt SUS > 68"** — không viết "UX tốt". Heuristic evaluation đúng phương pháp (NN/g): **nhiều evaluator độc lập rồi tổng hợp** — bắt được ~75% vấn đề major; 1 người quét = kết quả yếu, ghi rõ giới hạn.

## 2. Nielsen 10 Usability Heuristics — checklist đánh giá (heuristic evaluation)
Mỗi heuristic → quan sát trên UI thật, ghi vi phạm:

| # | Heuristic | Kiểm gì (ví dụ quan sát) |
|---|---|---|
| H1 | **Visibility of system status** | Có loading/spinner/progress? Sau hành động có phản hồi (toast/đổi state)? Không "im lặng". |
| H2 | **Match system ↔ real world** | Ngôn ngữ/icon đúng nghiệp vụ user (không jargon kỹ thuật); thứ tự hợp logic thực tế. |
| H3 | **User control & freedom** | Có Undo/Cancel/đóng (X)? Thoát được khỏi state lỡ vào? Không bẫy. |
| H4 | **Consistency & standards** | Nút/label/màu nhất quán toàn app; theo convention nền tảng. |
| H5 | **Error prevention** | Confirm cho hành động phá hủy; validate trước khi submit; disable nút khi chưa đủ điều kiện. |
| H6 | **Recognition over recall** | Thông tin/lựa chọn hiển thị sẵn, không bắt user nhớ; placeholder/label rõ. |
| H7 | **Flexibility & efficiency** | Shortcut/bulk/ghi nhớ lựa chọn cho user thạo; vẫn đơn giản cho người mới. |
| H8 | **Aesthetic & minimalist** | Không nhồi thông tin thừa làm loãng cái quan trọng. |
| H9 | **Help users with errors** | Thông báo lỗi bằng ngôn ngữ NGƯỜI (không mã/stacktrace), nói RÕ cách sửa. |
| H10 | **Help & documentation** | Hint/tooltip/hướng dẫn tại chỗ khi cần. |

**Severity (Nielsen scale):** 0=không phải vấn đề · 1=cosmetic · 2=minor · 3=major · 4=catastrophe. Ưu tiên sửa ≥3.

## 3. Visual / Interaction states — phải kiểm đủ (rất hay sót)
| State | Kiểm |
|---|---|
| **Loading** | skeleton/spinner; không nhấp nháy; không chặn toàn trang vô cớ |
| **Empty** | màn hình rỗng có hướng dẫn (không trắng trơn) |
| **Error** | thông báo rõ + cách khôi phục (H9) + role="alert" |
| **Disabled** | nút/field disabled có lý do thị giác rõ; không "chết câm" |
| **Success** | xác nhận sau hành động (H1) |
| **Responsive** | breakpoint mobile/tablet/desktop; không vỡ layout/tràn ngang |
| **Focus & keyboard** | focus order hợp lý; thao tác được bằng bàn phím; focus visible |
| **Contrast/typo** | tương phản đạt WCAG; cỡ chữ đọc được |

## 4. WCAG 2.2 A/AA — accessibility (gộp với a11y)
Tối thiểu: text alternatives, keyboard operable, focus visible (2.4.7), target size (2.5.8 — 24×24px), contrast 1.4.3 (4.5:1 text), labels/name-role-value (4.1.2 — role/aria/label), error identification (3.3.1). → kết hợp `accessibility-wcag.md`.

## 5. Cách CHẤM (Bước 7b) → ghi Ledger
1. Mở UI thật trong E2E/browser, thực hiện journey của từng persona.
2. Quét **10 heuristic + 8 state + WCAG** → mỗi vi phạm = 1 dòng `COV-UX-NN`: `{heuristic/state, vị trí, severity, mô tả, đề xuất sửa}`.
3. Đo (khi được): task success rate, số bước/journey, lỗi gặp.
4. `COV-UX` không vi phạm vẫn ghi "đã kiểm — đạt" (chứng minh đã quét, không bỏ qua).
5. Phát hiện severity ≥3 → báo như **defect UX** (vào Bug Tracker), không nuốt.

## 6. Mobile (khi platform android/ios)
- Neo thêm: **Material 3** (Android) / **Apple HIG** (iOS) — pattern điều hướng, spacing, touch target ≥48dp/44pt.
- Quét bằng TalkBack/VoiceOver cho journey chính; Maestro không tìm thấy element qua accessibility layer = **a11y defect** (thiếu label), không phải test bug.
- State bổ sung phải kiểm: keyboard che CTA, safe area/notch, landscape, font-scale max không vỡ layout.

> UI/UX KHÔNG phải "ý kiến cá nhân": neo vào heuristic/ISO/WCAG/HIG có tên → kiểm chứng được, không cảm tính.
