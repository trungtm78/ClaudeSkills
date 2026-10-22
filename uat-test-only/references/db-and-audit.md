# Tầng dữ liệu, audit, idempotency và trạng thái (G15)

Nạp khi bộ ca có `type` thuộc `DATA` · `STATE`, hoặc có ca khai `db_assert` /
`audit_assert` / `idempotency` / `transition`.

Lý do tầng này tồn tại: một màn hình xanh chứng minh **tầng hiển thị** đúng, không chứng
minh **cái đã ghi xuống** đúng. Phải assert ở từng chặng `UI → API → Domain → DB → Audit`,
không chỉ ở chặng cuối.

## Rào cứng — không cờ nào mở được

| | |
|---|---|
| `db_assert` chỉ được **ĐỌC** | `SELECT` / `WITH`. Dấu `;` thứ hai, hay từ khoá ghi/DDL → `db_assert.py` **từ chối chạy** ca đó |
| Mồi dữ liệu bằng SQL vẫn **CẤM** | `writing-tests.md §8` nguyên vẹn. Ở đây chỉ mở phần đọc — đọc không phải ghi |
| Kết nối bằng role **chỉ-đọc** | DSN qua `UAT_DB_DSN`, **ngoài repo**. PostgreSQL 18 mặc định `127.0.0.1:5433` |
| Không nối được DB | mọi ca có khai → `KHONG_CHAY(thieu-ket-noi-db)`, G15 **hạ trần**. Không ai giả vờ là đã đo |

## Bốn khối khai báo

```jsonc
// a) Dữ liệu: cái hiện ra có đúng cái đã ghi không
"db_assert": { "query": "SELECT trang_thai FROM don WHERE id=1",
               "expect": { "value": "REJECTED", "rows": 1 } }
//   expect: rows | min_rows | max_rows | value (ô đầu tiên) | contains (chuỗi hoặc mảng)

// b) Audit: thao tác nhạy cảm có để lại dấu vết không
"audit_assert": { "entity": "don", "entity_id": "1", "action": "reject",
                  "fields": ["user_id","created_at","entity_id","action","old_value","new_value"],
                  "expect_rows": 1 }
//   Thiếu dòng audit → FAIL S1: không truy được ai làm gì, lúc nào, đổi từ gì sang gì.
//   Dòng audit có trường rỗng cũng FAIL: audit thiếu trường thì không tái dựng được thay đổi.

// c) Idempotency: gửi lại có sinh bản ghi thừa không
"idempotency": { "url": "/api/v1/don", "method": "POST", "key_header": "Idempotency-Key",
                 "concurrency": 5, "body": {...},
                 "count_query": "SELECT count(*) FROM don WHERE idem_key = ?",
                 "expect_rows": 1 }
//   Gửi ĐỒNG THỜI, không tuần tự. Gửi lại tuần tự không chứng minh được gì: tính chất cần
//   chứng minh là một thao tác logic → tối đa MỘT lần ghi có hiệu lực, kể cả khi các
//   request chồng nhau. Đây là ca kinh điển: request đầu đã thành công nhưng giao diện
//   timeout, người dùng bấm lại.

// d) Trạng thái: đường BẤT HỢP LỆ có bị chặn không
"transition": { "from": "CANCELLED", "to": "RESULTED", "allowed": false }
```

## Ca `type: STATE` — kịch bản phải làm gì

Ca `allowed: false` thì kịch bản **phải cố thực hiện** chuyển trạng thái ấy và khẳng định
ba điều: thao tác **bị chặn**, mã lỗi là **lỗi nghiệp vụ chứ không phải 500**, và trạng
thái sau đó **không đổi** (kiểm bằng `db_assert` khi có DB). Chuyển được → FAIL `S1`.

Chỉ kiểm đường hợp lệ là bỏ sót đúng nửa nguy hiểm: `VERIFIED → DRAFT`,
`CANCELLED → RESULTED`, phôi đã huỷ lại rã đông được, phôi đã chuyển lại chuyển lần nữa.

## Lệnh

```bash
. uat/run/<id>/run.env
$PY "$SK/scripts/db_assert.py" --cases "$OUT/cases.json" --out "$OUT/results/db.json"
# rồi đưa vào bảng chung:  merge_results.py … --checks db="$OUT/results/db.json"
```
