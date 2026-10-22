---
name: ui-runtime-audit
description: |
  Runtime UI audit that MEASURES the running screen instead of reading the source or
  proposing designs. Catches the failure class where a screen LOOKS right and IS wrong:
  content scrolled out of reach, layout decided by translation length, screens nobody
  can click to, buttons that do nothing, empty states that all look the same. Use for
  "review the UI", "check the screens", "UX audit", "audit the running app", or before
  shipping a screen anyone will sign against. NOT for choosing styles, colors, fonts or
  building new UI — that is the ui-ux-pro-max plugin skill.
---

# /ui-runtime-audit — soát giao diện bằng phép đo, không bằng mắt

Kỹ năng này không đi tìm lỗi thẩm mỹ. Nó đi tìm **lỗi mà màn hình vẫn trông đúng** — lớp
lỗi duy nhất không ai bắt được bằng cách nhìn, và là lớp đã ship thật trong kho này nhiều
lần.

**Luật số một:** mọi khẳng định phải đến từ **trình duyệt đang chạy** ở một kích thước cụ
thể. Đọc mã nguồn để biết chỗ nào ĐÁNG đo; đừng đọc mã nguồn để kết luận.

---

## Trước khi bắt đầu

```bash
_BRANCH=$(git branch --show-current 2>/dev/null || echo unknown); echo "BRANCH: $_BRANCH"
_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo .); echo "ROOT: $_ROOT"
```

Cần một bản đang chạy. Không có thì **dừng và nói ra** — sáu pha dưới đây đều là phép đo,
và một lượt soát chỉ đọc mã sẽ xanh đúng ở những chỗ đáng đỏ nhất.

---

## Pha 1 — Nội dung cuộn tới được (lỗi im lặng số một)

`overflow-y-auto` cạnh `justify-center` trên **cùng một hộp** là một lỗi im lặng.
`justify-content: center` chia phần tràn ra **cả hai đầu**, nhưng gốc cuộn của hộp là **mép
trên** — nên phần bị đẩy lên trên gốc **không cách nào cuộn tới**, `scrollTop` kẹp ở 0.

Đo thật trên một sản phẩm đang chạy: 1280×640, cuộn hết cỡ lên, tiêu đề vẫn ở `top: -55`.
Ở 1280×360 mất **153px ở MỖI đầu**. Người dùng báo bằng câu *"phóng 100% thì mất luôn chữ
Sign in"* — vì 1920×1080 ở mức phóng 150% cộng thanh công cụ chỉ còn khoảng **600px CSS**.

```
Tìm chỗ đáng đo:
  grep -rn "overflow-y-auto\|overflow-auto\|overflow-y-scroll" <FE>/src --include=*.tsx \
    | grep -E "justify-center|items-center|place-content-center"
```

**Phép kiểm ĐÚNG** (ba chiều cao thấp là đủ: 900 · 640 · 360):

1. Cuộn hết cỡ **LÊN** → khẳng định **đỉnh** nội dung nằm trong hộp.
2. Cuộn hết cỡ **XUỐNG** → khẳng định **đáy** nội dung nằm trong hộp.

**`toBeVisible()` KHÔNG bắt được lỗi này.** Playwright chỉ đòi hộp bao khác rỗng và không
`visibility: hidden`; một phần tử ở `top: -55` thoả cả hai. Nút đăng nhập báo *hiển thị*
trên màn hình không ai nhìn thấy nó.

**Bẫy đi kèm:** phép kiểm cũ hỏi *"trang có cuộn không"* và luôn xanh, vì `h-screen` +
`overflow-hidden` bảo đảm trang không bao giờ cuộn. Một bản vá dời phần tràn **từ trang vào
trong cột** sẽ đi qua phép kiểm ấy nguyên vẹn. Viết lại câu hỏi theo lỗi mới, đừng theo
triệu chứng cũ.

**Cách sửa:** căn giữa bằng `m-auto` trên **con**, không bằng `justify-center` trên hộp
cuộn. Lề `auto` căn giữa khi còn chỗ và **thu về 0** khi hết chỗ.

---

## Pha 2 — Bố cục do bản dịch quyết định

Một sản phẩm đa ngữ có **ba màn hình**, không phải một. Soát ảnh chụp bằng một thứ tiếng
rồi kết luận là thói quen mặc định, và nó **không nói được gì** về hai thứ tiếng kia.

Đo thật, cùng một hàng "ghi nhớ / quên mật khẩu":

| Ngôn ngữ | Vị trí liên kết |
|---|---|
| VI | `x=321`, **cùng hàng** với ô ghi nhớ |
| EN | `x=64`, **hàng riêng** |
| JP | `x=64`, **hàng riêng** |

Không ai viết ra luật ấy — nó rơi ra từ độ dài bản dịch.

**Việc phải làm:** với mỗi màn có `justify-between`, `flex-wrap`, hoặc chiều rộng suy từ nội
dung — chụp ở **cả ba** thứ tiếng, cùng một khung nhìn, rồi so **toạ độ**, không so cảm giác.

**Cách sửa:** chọn bố cục **cố định** thay vì "xuống dòng khi cần". Tốn một hàng chiều cao,
đổi lại màn hình giống nhau ở mọi nơi.

**Tiếng Nhật không có dấu cách** — chỗ ngắt rơi vào giữa từ. Kiểm riêng.

---

## Pha 3 — Bấm tới được, không phải mở được bằng URL

**Mở một màn bằng cách gõ địa chỉ không nói lên điều gì** về việc người dùng tới được nó.
Một lượt soát mở cả 49 màn bằng URL đã xanh trong khi **23 màn không có đường bấm nào**.

Phép đo đúng là **bao đóng bắc cầu** từ trang chủ: đi theo mọi liên kết và mọi `navigate()`,
lặp cho tới khi không thêm được màn nào. Màn nấp sau màn mồ côi **cũng là màn mồ côi**.

```
- Route khai báo:      grep -rn "path:" <FE>/src/routes
- Đích bấm được:       grep -rn "to=\"\|navigate(\|href=\"/" <FE>/src --include=*.tsx
- Chênh lệch giữa hai tập = danh sách màn mồ côi
```

Kèm theo: **liên kết trỏ vào route không tồn tại**. Cùng một phép đo, chiều ngược lại.

---

## Pha 4 — Nút có làm gì không

Chỉ đếm là **P1** khi thân xử lý **không có tác dụng phụ nào**:

| Dấu hiệu | Mức |
|---|---|
| `<button>` không `onClick`, không `type="submit"` | P1 |
| Thân xử lý chỉ có `alert()` / `console.log`, không gọi API | P1 |
| `confirm()` + `alert()` mà không gọi API — **báo thành công giả** | P2 |

**KHÔNG phải lỗi:** `alert()` để báo lỗi nhập liệu · `alert()` trong `catch` · xử lý chỉ
điều hướng.

Và chiều ngược lại, thứ hay bị bỏ sót hơn: **endpoint máy chủ đã trả lời mà không màn nào
gọi**. Đếm số nơi ĐỌC, đừng đếm số nơi GHI.

---

## Pha 5 — Trạng thái rỗng phải phân biệt được

Một hộp trống thường có **nhiều hơn một nghĩa**, và chỉ một nghĩa là đáng yên tâm:

- chưa cấu hình tính năng
- đã chạy và không có gì để nói
- đã chạy, có kết quả, và **tất cả đều bị loại**
- không tải được

Gộp chúng vào một hộp trống là nói với người dùng rằng mọi thứ sạch, trong khi thứ đã xảy ra
có thể là tầng ấy không sinh ra được gì dùng được.

**Đây là lớp lỗi "đầu ra không phân biệt được với câu trả lời đúng"** — không soi màn mà
thấy được. Tách phép quyết định ra một hàm thuần để ca kiểm với tới, đừng để inline.

Biểu đồ bảy ngày của kho này trả về **toàn số không trên mọi hồ sơ suốt nhiều tuần**, được
che bởi một chú thích trung thực nói rằng bảy cột bằng không là câu trả lời hợp lệ. Đúng
thật — vào một tuần vắng.

---

## Pha 6 — Chữ hiển thị không bao giờ là khoá

So sánh với **nhãn hiển thị** đã mắc sáu lần trong kho này, một lần là cổng bảo mật. Nhãn
đổi theo ngôn ngữ, theo bản dịch, theo một lượt sửa chính tả — khoá thì không.

```
grep -rn "=== '[^']*[À-ỹ]" <FE>/src --include=*.tsx     # so với chữ tiếng Việt
grep -rn "\.includes('[^']*[À-ỹ]" <FE>/src --include=*.tsx
```

Cùng họ: `split(' ')` trên một mốc **ISO** không có dấu cách nào → khoá tra là `undefined`,
không ô nào khớp, **mọi cột bằng không mãi mãi**.

---

## Báo cáo

```
╔══════════════════════════════════════════════════════════╗
║  UI RUNTIME AUDIT — {ngày} — {nhánh}                     ║
╚══════════════════════════════════════════════════════════╝

ĐO TRÊN: {URL} · khung nhìn {W×H} · ngôn ngữ {vi|en|ja}

P1 — nội dung không tới được / nút không làm gì
P2 — báo thành công giả / màn mồ côi
P3 — bố cục lệch giữa các ngôn ngữ (kèm toạ độ đo được)
P4 — trạng thái rỗng không phân biệt được

KHÔNG ĐO ĐƯỢC: {mục nào, vì sao}
```

**Mục cuối là bắt buộc.** Một phép kiểm không chạy được là **đỏ**, không phải bỏ qua: mọi
lần bộ đọc của một cổng sai đều lệch về phía xanh, nên im lặng phải được kể ra.

---

## Luật kết

1. **Không sửa khi chưa hỏi** — mặc định là báo cáo. Trừ khi người dùng nói rõ "sửa đi".
2. **Số đo đi kèm mọi khẳng định.** "Tiêu đề bị cắt" là ý kiến; "`top: -55` ở 1280×640" là
   phép đo.
3. **Ba khung nhìn, ba ngôn ngữ.** Một cấu hình không nói được gì về hai cấu hình kia.
4. **Chữ hiện cho người dùng đi qua danh mục dịch**, không viết cứng ở bất kỳ thứ tiếng nào.
