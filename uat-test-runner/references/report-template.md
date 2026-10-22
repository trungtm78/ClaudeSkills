# Mẫu báo cáo kết quả thực thi

> Tách từ `SKILL.md` để giảm lượng chữ phải nạp mỗi lần gọi skill. Nạp khi cần.

## Output Report bắt buộc

```markdown
## 📊 KẾT QUẢ THỰC THI UAT — <feature>

### Header (traceability)
Build SHA: <commit> · Env URL: <url> · Playwright: <ver> · Maestro: <ver hoặc N/A>
Evidence profile: signoff|ci · Workers: N · Bắt đầu/kết thúc: <timestamps>
Backend policy tổng quát: live (TC mock 3rd-party/error-injection liệt kê riêng)

### Tổng quan (4 trạng thái)
| Metric | Giá trị |
|--------|---------|
| Total TC | 25 |
| ✅ PASS (mọi layer áp dụng) | 16 |
| ❌ FAIL | 4 |
| ⏭️ SKIPPED (gate trước fail) | 2 |
| 🚫 NOT_EXECUTED (blocked — kèm lý do + remediation) | 3 |
| ⏱️ Thời gian | 3m 24s (API: 24s, Web E2E: 2m, Mobile: 1m) |

### Per-platform
| Platform | Pass | Fail | Skip | Not executed | Ghi chú |
|----------|------|------|------|--------------|---------|
| API | 23 | 2 | 0 | 0 | |
| WEB | 15 | 3 | 2 | 0 | |
| ANDROID | 8 | 1 | 0 | 0 | emulator-5554, API 34 |
| IOS | 0 | 0 | 0 | 9 | blocked: no macOS host → remediation: workflow macos-latest đã sinh sẵn |

### ⚠️ Regression (vs baseline <ngày>)
| TC | Trước | Sau | Severity gốc → escalate | Sign-off cũ |
|----|-------|-----|------------------------|-------------|
| TC-011 | Đạt | Không đạt | S3 → S2 | THU HỒI, cần re-approve |

### 🔶 Flaky (pass-on-retry — KHÔNG tính pass trong sign-off)
| TC | Root-cause bucket | Hành động |
|----|-------------------|-----------|

### 🔒 Quarantine (coverage chưa verify = risk)
| TC | Owner | Deadline (≤14 ngày) | Ticket |
|----|-------|---------------------|--------|

### Bug đã tạo (triage 4 nhãn)
| Bug ID | TC | Layer | Severity | Nhãn triage | Mô tả |
|--------|-----|-------|----------|-------------|-------|
| BUG-001 | TC-008 | [E2E] | S2 | product bug | Validation message không hiện sau submit |
| BUG-002 | TC-015 | [API] | S1 | product bug | API trả 500 với SQLi payload thay vì 400 |

### 🐢 Slowest 10 TC (theo dõi perf trend)

### Evidence
📂 HTML report: `playwright-report/index.html` · Traces/Videos/Screenshots: `test-results/...`
📂 Mobile: `.maestro/` flows + `test-results/mobile/<TC>/` (recording, screenshots, logcat, junit)
Mỗi TC FAIL: trace + screenshot + video/recording; profile signoff: evidence cả TC PASS.

### 🚦 GO/NO-GO — dán nguyên khối `runner-verdict.txt`

Không tự viết lại bảng cổng. Khối do `build_runner_report.py` sinh đã có đủ: verdict, trần,
nợ đã biết, khuyết phép đo, trạng thái từng cổng.
**Verdict đề xuất: <GO | CONDITIONAL GO (waivers: ...) | NO-GO | NO-RUN>**
Residual risk: <platform NOT_EXECUTED, quarantine, waiver...>
Người ký sign-off: __________ (skill không tự approve)

### Bàn giao cho Claude Code fix bug
- Đọc TC fail trong `.md` companion; nhãn layer + triage cho biết fix backend/frontend/mobile hay test
```

