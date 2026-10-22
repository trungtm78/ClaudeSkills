# Triển khai bộ UAT cho một dự án mới

Ba skill nằm ở `~/.claude/skills/` — cấp **user**, nên **mọi dự án đã thấy sẵn**, không
phải cài gì cho từng dự án. Việc của một dự án mới chỉ là **cấp bí mật và công cụ**.

## Bước 0 — chạy preflight, 30 giây

```bash
UAT_BASE_URL=http://127.0.0.1:<cổng> \
  python "$HOME/.claude/skills/uat-test-only/scripts/preflight.py" --cwd .
```

Nó nói ngay cổng nào đo được, cổng nào chưa và **thiếu chính xác cái gì**. Chạy trước,
đừng phát hiện giữa lượt UAT.

## Đọc kết quả lượt đầu cho đúng

Một dự án chưa cấp đủ sẽ ra **`GO-CHỜ-KÝ-KÈM-KHUYẾT`**, kèm dòng `KHUYẾT PHÉP ĐO:`.
**Đó không phải lỗi** — đó là hệ thống nói thật rằng nó chưa đo được vài thứ. Cấp thêm thì
trần tự nâng lên. Điều duy nhất không bao giờ xảy ra là một cổng chưa đo được tự nhận là đạt.

## Bí mật — luôn ngoài repo, không bao giờ trong `uat.json`

| Biến | Cho cổng | Ghi chú |
|---|---|---|
| `UAT_BASE_URL` | G0 và mọi lớp | app phải đang chạy |
| `UAT_USER_<VAI>` · `UAT_PASS_<VAI>` | ca cần đăng nhập | thiếu → ca thành KHÔNG CHẠY, **không** chế tài khoản |
| `UAT_TOKEN_<VAI>` hoặc `UAT_TOKEN_FILE` | G14 quyền · IDOR | cần **≥2 vai** để dựng ma trận chéo |
| `UAT_DB_DSN` | G15 dữ liệu · audit · idempotency | role **CHỈ-ĐỌC**. PG18 `127.0.0.1:5433` là mặc định, ghi đè được |
| `UAT_EVIDENCE_PROFILE=ci` | G12 | hạ hồ sơ bằng chứng cho vòng CI |

`validate_uat_json.py` **chặn** nếu bí mật lọt vào `uat.json` — tệp ấy được commit.

## Công cụ

| Cần | Cho | Thiếu thì |
|---|---|---|
| `node` + `npm` | lõi web/api, monkey, chứng âm, a11y | **không chạy được** — đây là tối thiểu |
| `git` | rào không-sửa G9 | rơi sang hash-tree, vẫn kiểm được |
| `openpyxl` | đường Excel | bỏ qua Excel |
| `psycopg` / `pymysql` | G15 | hạ trần |
| `maestro` | mobile E2E | lớp mobile KHÔNG CHẠY |
| `adb` | monkey Android | hạ trần (monkey web vẫn bắt buộc) |

Windows: chạy bằng **Git Bash** — toàn bộ runbook là bash. Console hay là cp932, nên script
nào in tiếng Việt cũng đặt `PYTHONIOENCODING=utf-8`.

## Quy trình

```
uat-test-writer → uat.json ─┬→ uat-test-only    nghiệm thu · KHÔNG sửa · để KÝ
                            └→ uat-test-runner  vòng dev · ĐƯỢC sửa · fix→retest
```

Gõ **"chạy UAT"** rơi vào `uat-test-only` — mặc định phải là cái không sửa gì. Lấy kết quả
của `uat-test-runner` đi ký là sai: người tìm ra lỗi mà cũng là người sửa thì không còn ai
ở ngoài để nói nó vẫn sai.

## Tự kiểm bộ skill còn lành

```bash
cd "$HOME/.claude/skills"
python uat-test-writer/scripts/sync_contract.py --check   # hợp đồng khớp
python uat-test-writer/scripts/routing_lint.py            # mỗi cụm kích hoạt một chủ
for s in uat-test-writer uat-test-runner uat-test-only; do
  PYTHONIOENCODING=utf-8 python $s/tests/test_scripts.py
done
```

## Lùi về bản cũ

Bản sao nguyên trạng ở `~/.claude/skills-archive/uat-<thời-điểm>/`, kèm `_ARCHIVE.md` ghi
cách khôi phục. Hoặc dùng git trong `~/.claude/skills`.
