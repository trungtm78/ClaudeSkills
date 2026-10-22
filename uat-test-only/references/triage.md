# Phân loại kết quả — không heal, không sửa

Nạp khi viết phần diễn giải của báo cáo. Kỹ năng **không** sửa gì; phân loại chỉ để người
đọc biết nên giao cho ai.

| Nhãn | Dấu hiệu | Báo cáo ghi | Tuyệt đối không |
|---|---|---|---|
| **lỗi sản phẩm** | assert giá trị sai; HTTP 4xx/5xx trái mong đợi; pageerror; sập | FAIL, mức theo `severity_if_fail` | sửa assert cho khớp app |
| **không tìm thấy phần tử** | timeout / element not found sau khi app đã lên | FAIL + "cần người xác minh: tính năng thiếu hay locator sai" | heal locator, nới timeout, `force: true` |
| **môi trường** | app không tới được lúc G0; thiếu thiết bị; thiếu tài khoản | NO-RUN (G0) hoặc KHÔNG CHẠY theo lớp | dùng tài khoản giả, mock app |
| **chập chờn** | FAIL lần đầu, ĐẠT khi chạy lại riêng (tái hiện 1/2) | vẫn **FAIL**, ghi "tái hiện 1/2" | tính là đạt, quarantine |

**"Không tìm thấy phần tử" là FAIL, không phải lỗi kịch bản mặc định.** Một tính năng bị
xoá mất trông y hệt một locator sai. Kỹ năng không phân xử được — nên nó không che đi, nó
nói rõ và để người quyết.

**5xx toàn cục không phải lỗi môi trường.** Máy chủ trả lời được nghĩa là kiểm được, và
máy chủ trả lỗi là phát hiện về sản phẩm. NO-RUN chỉ dành cho khi không tới được máy chủ.

## Khi viết báo cáo

- Nêu **mong đợi** (kèm nguồn oracle: `rule_ref` / `oracle_source`) · **thực tế** ·
  **tái hiện** · **bằng chứng** (ảnh/trace/log). Không nêu nguyên nhân mã nguồn, không đề
  xuất cách sửa: kỹ năng không đọc mã sản phẩm, nên mọi "nguyên nhân" đều là đoán.
- Thấy một lỗi hiển nhiên, sửa trong 30 giây được → **vẫn không sửa**. Người tìm ra lỗi mà
  cũng là người sửa lỗi thì không còn ai ở ngoài để nói rằng nó vẫn sai.
