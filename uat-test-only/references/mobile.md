# Mobile (Android / iOS) bằng Maestro

Nạp khi danh mục có ca `platform: android|ios`. Chuyển thể từ `uat-test-runner/references/mobile-runner.md`,
bỏ mọi chỗ "dừng và sửa root cause".

## Điều kiện (G0 theo lớp)

- `probe_env.py --need android --need maestro` (hoặc `--need ios`). Thiếu thiết bị/emulator hay
  Maestro → lớp mobile **KHÔNG CHẠY** (`merge_results.py --not-run mobile=ngoai-thiet-bi`), các lớp
  khác vẫn chạy. iOS cần macOS + Xcode; trên Windows luôn KHÔNG CHẠY.
- Dựng/cài app là **môi trường**, không phải sửa mã: dùng đúng `buildCmds` trong
  `_platform.json` (`flutter build apk`, `./gradlew assembleDebug`…) rồi `adb install -r`.
  Lệnh dựng hỏng → KHÔNG CHẠY kèm log, không vá cấu hình dựng.
- Emulator gọi máy chủ local qua `10.0.2.2`, không phải `localhost`.

## Flow

Mỗi ca một tệp `<OUT>/.maestro/<tc_id>.yaml` (tên tệp = ID, để JUnit mang đúng ID):

```yaml
appId: com.vidu.app
name: TC-M-012 đổi giá giờ vàng
---
- launchApp: { clearState: true }
- tapOn: { text: "Giờ vàng" }
- assertVisible: { text: "Giá 45.000đ" }      # giá trị chép từ expected của ca
```

Cùng luật oracle với web: assert lấy từ `expected`, không từ màn hình đang hiện.
Cấm `optional: true` trên bước kiểm (đó là skip trá hình) — guard không quét YAML theo ngữ
nghĩa này, nên đây là luật người viết phải giữ.

## Chạy

```bash
maestro test --format junit --output <OUT>/results/mobile.xml <OUT>/.maestro
```

Sau lượt: `adb logcat -d -b crash` — có `FATAL EXCEPTION` trong lúc chạy thì ca đang chạy là
FAIL dù UI qua (oracle sập). Chạy lại riêng ca FAIL một lần để ghi tái hiện; kết quả vẫn FAIL.

`merge_results.py --junit <OUT>/results/mobile.xml --junit-layer mobile`.
