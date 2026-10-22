# ClaudeSkills

Bộ skill Claude Code đang dùng (snapshot 22/10/2026), sao chép từ `~/.claude/skills`.

## Cách dùng
Chép từng thư mục skill vào `~/.claude/skills/` (mỗi skill có `SKILL.md`).

## Lưu ý
- **Nhóm gstack** (autoplan, ship, review, qa, codex, office-hours, plan-*-review, …) là bản sinh ra từ gstack: phần `SKILL.md` đọc thêm các tệp trong `~/.gstack/render/claude/<skill>/sections/` và dùng `~/.claude/skills/gstack/bin/*`. Cần cài gstack (thư mục `gstack/` 1,4 GB **không** nằm trong repo này) thì các skill này mới chạy đủ.
- **Nhóm riêng**: `implement`, `deploy`, `uat-test-writer`, `uat-test-runner`, `uat-test-only`, `expert-test-writer`, `expert-test-runner`, `ui-runtime-audit`, `stub-check`, `web-context`, `mobile-context`, `qa-mobile` (một phần viết cho dự án PC02).
- `hallmark` được chép nội dung thật từ `~/.agents/skills/hallmark` (ở máy gốc nó là liên kết).
- Đã **che** thông tin nhạy cảm: tài khoản dev, địa chỉ máy chủ prod (`<PROD_HOST>`), email tài khoản thử. Không có khoá/token thật. Tài khoản/mật khẩu mẫu trong các tệp test của skill UAT là giá trị giả.
- Không đưa lên: `gstack/` và `gstack.bak/`, `synced/`, `.trash/`, `.harness-sync/`, `_luu-tru/` (lưu trữ), `oc-pipeline/` (không còn là skill).
