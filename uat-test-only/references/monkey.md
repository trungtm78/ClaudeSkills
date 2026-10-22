# Monkey test — chỉ quan sát và ghi

Nạp ở Bước 8. Monkey test đúng tinh thần chỉ-báo-cáo: tạo thao tác ngẫu nhiên có seed,
**quan sát** app phản ứng, **ghi** mọi bất thường kèm cách tái hiện. Không sửa gì.

## Khi nào chạy

- Sau các ca kịch bản, chỉ khi G0 đạt.
- Chỉ trên máy chủ **local/staging/dev/test/uat/qa** (nhận theo tên máy chủ). Máy chủ khác →
  KHÔNG CHẠY, trừ khi người đặt `UAT_MONKEY_ALLOW_HOST=<host>` — monkey bấm thật, gõ thật,
  và có thể tạo dữ liệu.
- Có tài khoản → chạy **cả hai** lượt: chưa đăng nhập và đã đăng nhập
  (`--storage-state <OUT>/.auth/state.json`, tệp do `auth.setup.ts` ghi).

## Web

```bash
cd <OUT> && node <SKILL>/scripts/monkey_web.mjs --url <URL> --seed <số> \
     --actions 200 --max-seconds 180 --out monkey [--storage-state .auth/state.json] [--deny "từ1,từ2"]
```

Thao tác: bấm phần tử tương tác nhìn thấy (~86%) · cuộn · phím Tab/Enter/Esc/mũi tên ·
lùi trang · đổi khung nhìn điện thoại/tablet/máy bàn. Ô nhập nhận payload biên: rỗng,
Unicode tiếng Việt, emoji, số âm/khổng lồ, 5000 ký tự, chuỗi XSS/SQL/template.

Rào: chỉ cùng origin (lạc ra ngoài → lùi lại, không tính lỗi) · **không bấm** phần tử có chữ
xoá/delete/đăng xuất/logout/thanh toán/pay/checkout/reset/publish… (`--deny` thêm) · không tải
tệp lên · hộp thoại luôn **dismiss**, không bao giờ "OK".

| Bất thường | Mức | Chặn G8? |
|---|---|---|
| trang sập (`crash`) | S1 | có |
| lỗi JS không bắt (`pageerror`) | S2 | có |
| HTTP 5xx cùng origin | S2 | có |
| trang trắng (không chữ, không hình) | S2 | có |
| một thao tác treo > 15 giây | S2 | có |
| `console.error` | S3 | không — ghi nhận |

Mỗi bất thường: ảnh chụp, 20 thao tác cuối, số bước. Trùng chữ ký (loại + đường dẫn + thông
điệp) → gộp, đếm số lần.

## Android

```bash
python <SKILL>/scripts/monkey_android.py --app-id <package> --seed <số> --events 500 --out <OUT>/monkey
```

`adb shell monkey -p <package> --pct-syskeys 0 --pct-appswitch 0`. Bắt `// CRASH` (S1),
`// NOT RESPONDING` (ANR, S1), `FATAL EXCEPTION` trong `logcat -b crash` (S1).
Không có thiết bị → KHÔNG CHẠY (thoát 4), ghi rõ lý do.

**iOS:** không có công cụ monkey chuẩn → KHÔNG CHẠY, báo cáo nói rõ.

## Tái hiện

Cùng seed + cùng trạng thái dữ liệu ⇒ cùng chuỗi thao tác. Bất thường ở bước *k* →
chạy lại với `--seed <s> --actions <k>` để dừng đúng chỗ. Tệp `web-<seed>.actions.json`
ghi đủ chuỗi thao tác cho người đọc lại.
