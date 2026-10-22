# Ví dụ instantiation — hệ TÀI CHÍNH (ERP xây dựng AIC trên Odoo 19)

> Đây là **ví dụ áp dụng** skill expert-test cho một domain tài chính cụ thể. KHÔNG phải một phần
> bắt buộc của skill — dùng làm mẫu để thấy "phát hiện bất biến generic" cho ra gì với hệ thực.

## Thư viện bất biến đã phát hiện (qua 8 lớp câu hỏi generic)
| ID | Lớp | Bất biến | Phương pháp |
|----|-----|----------|-------------|
| I1 | Bảo toàn | Σ analytic_line == −Σ GL theo `analytic_distribution` | property |
| I2 | Đối ứng | chi phí CĐT == doanh thu NTH (trước thuế) cùng nghiệm thu | property (2-company) |
| I3 | Cô lập | roll-up planned/actual/profit KHÔNG trộn giữa công trình | property |
| I4 | Đơn điệu | T ≤ G ≤ grand_total; grand == G+VAT+DP (mọi %≥0) | property |
| I5 | Scale | ×k mọi khối lượng → T,GC,TL,G,VAT,DP,grand đều ×k | metamorphic |
| I6 | Cộng tính | tách 1 dự toán thành 2 (cùng %) → Σ grand bằng nhau | metamorphic |
| I7 | Đơn điệu | NPV(rate=0)==Σ net; NPV giảm khi rate tăng | property |
| I8 | Nghiệp vụ | |NPV(IRR)| ≈ 0 | property |
| I9 | Bảo toàn | Σ share_for_project == baseline (mọi phương pháp allocation) | property |
| I10 | Nghiệp vụ/lịch sử | đổi khung pháp lý → dự toán cũ giữ số | golden/regression |
| I11 | Nghiệp vụ | loss_warning ⇔ forecast_profit < 0 | property |
| I12 | Bảo mật | write field tài chính khi locked → UserError | stateful/security |

## Persona cụ thể (ánh xạ từ archetype)
- (a) **Kế toán công trình Mai** → I1 (đối chiếu cuối tháng lệch 1 đồng).
- (b) **Kiểm toán/thẩm tra Lan** → I10, I12 (ai đổi giá, dự toán cũ tính lại).
- (c) **Kẻ tấn công** → I12 + cô lập đa công ty (CĐT không thấy giá vốn NTH).
- (d) **Kỹ sư hiệu năng** → BOQ 50k dòng.
- (e) **Chuyên gia UX Trang** → checklist 10 màn PDCA (xem UAT_chu_dau_tu.md).

## Mẫu code Odoo (runner dùng)
### Property trong TransactionCase + hypothesis
```python
from hypothesis import given, strategies as st, settings, HealthCheck
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestPropertyEngine(TransactionCase):
    # tạo 1 record ở setUpClass, mỗi example GHI lại tham số rồi đọc compute (nhanh, không tạo N record)
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(gc=st.floats(0,100), vat=st.floats(0,100))
    def test_i4(self, gc, vat):
        self.est.write({'gc_percent': gc, 'vat_percent': vat})
        # assert bất biến I4 ...
```
> Lưu ý Odoo: hypothesis chạy thân test nhiều lần TRONG 1 transaction của TransactionCase (rollback ở cuối).
> Mutate lại cùng record qua mỗi example — KHÔNG tạo record mới mỗi lần (tránh phình + chậm).

### Mutation (cosmic-ray) — cấu hình `cosmic-ray.toml`
```toml
[cosmic-ray]
module-path = "addons/aic_construction_base/models/aic_estimate.py"
test-command = "C:/AIConnect/venv/Scripts/python.exe odoo-bin -c odoo.conf -d aic_mut -u aic_construction_base --test-enable --test-tags /aic_construction_base --stop-after-init --no-http"
timeout = 300.0
[cosmic-ray.distributor]
name = "local"
```
> Mutation trên Odoo nặng (mỗi mutant chạy lại cả suite). Giới hạn `module-path` vào 1 file engine lõi;
> chạy nền. Cách NHANH để chứng minh giá trị bộ test (proof-of-concept): **đột biến tay** 1 dòng engine
> (vd bỏ `/100`) → chạy property test → phải ĐỎ → revert. Đó là 1 mutant bị "kill" minh hoạ.
