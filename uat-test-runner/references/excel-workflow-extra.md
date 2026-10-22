# Excel hai cột status dual-layer

> Tách từ `SKILL.md` để giảm lượng chữ phải nạp mỗi lần gọi skill. Nạp khi cần.

## Excel có 2 cột status dual-layer

| Col | Tên | Mô tả |
|-----|-----|-------|
| R | Trạng thái API | Layer 1 smoke result |
| S | Trạng thái E2E | Layer 2 UI result. "Bỏ qua" nếu API fail |

> Script resolve cột theo TÊN HEADER (row 3), không theo chữ cái — Excel version cũ/mới đều ghi đúng.

Summary Dashboard có metrics riêng:
- **✅ Đạt (cả 2 layer)** — TC pass CẢ API VÀ E2E
- **API pass rate** vs **E2E pass rate** riêng
- **E2E Bỏ qua** — số TC skip do API smoke fail

