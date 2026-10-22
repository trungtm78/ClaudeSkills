# Ma trận quyền và IDOR (G14)

Nạp khi bộ ca có `type` thuộc `SECURITY` · `PERMISSIONS`, hoặc có ca khai `access`.

Một ca chạy bằng vai **được phép** chỉ chứng minh đường thuận đi được. Nó không chứng minh
đường nghịch bị chặn. Phép đo thật là **thử chéo**: cùng tài nguyên ấy, token của vai khác,
và token rỗng.

Và: **không coi việc ẩn nút ở giao diện là bảo mật.** Nút bị ẩn không ngăn ai gọi thẳng API.
Vì thế ma trận chạy ở tầng HTTP, không qua giao diện.

## Khai báo

```jsonc
"access": {
  "url": "/api/v1/don/1",              // tương đối theo UAT_BASE_URL, hoặc URL đầy đủ
  "method": "GET",
  "allow": ["ke-toan", "giam-doc"],    // BẮT BUỘC — mọi vai khác phải bị chặn
  "deny_status": [401, 403],           // mặc định [401, 403]
  "must_not_contain": ["so_tien", "cccd"]   // thân phản hồi không được lộ nội dung
}
```

Thiếu `allow` → ca thành `KHONG_CHAY(ca-khong-hop-le)`: không biết vai nào được phép thì
không dựng được ma trận, và đoán bừa thì tệ hơn không đo.

## Nguồn token — không bao giờ tự chế tài khoản

| Nguồn | Dạng |
|---|---|
| biến môi trường | `UAT_TOKEN_<ROLE>` — vd `UAT_TOKEN_KE_TOAN` → vai `ke-toan` |
| tệp JSON **ngoài repo** | `UAT_TOKEN_FILE` trỏ tới `{"ke-toan": "…", "dieu-duong": "…"}` |

Không có token vai nào → mọi ca `access` thành `KHONG_CHAY(thieu-vai)` và **G14 hạ trần**.
Có một vai thì vẫn đo được vai **vô danh**, nhưng ma trận chéo giữa các vai thì không.
Bịa một tài khoản để "cho chạy được" biến một lỗ quyền thật thành màu xanh.

## Điều gì bị tính là hỏng

| Quan sát | Kết luận |
|---|---|
| vai không được phép nhận `2xx` | **IDOR · S1** — kiểm soát truy cập ở máy chủ hỏng |
| vai vô danh nhận `2xx` | **IDOR · S1** — tài nguyên công khai ngoài ý muốn |
| mã trả về ngoài `deny_status` (vd `500`) | FAIL — chặn bằng cách sập không phải là chặn |
| đã chặn nhưng thân phản hồi vẫn lộ `must_not_contain` | FAIL — rò rỉ qua thông điệp lỗi |

## Lệnh

```bash
. uat/run/<id>/run.env
$PY "$SK/scripts/role_matrix.py" --cases "$OUT/cases.json" --out "$OUT/results/idor.json"
# rồi:  merge_results.py … --checks security="$OUT/results/idor.json"
```
