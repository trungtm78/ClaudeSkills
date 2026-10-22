# Plan Grounding — Phân tích sâu PLAN đang thực thi (Bước 0.5, CÓ ĐIỀU KIỆN)

> Khi dự án **đang triển khai một plan** (plan-mode plan file hoặc output `/plan-eng-review`), UAT phải **cột vào plan đó**: verify từng acceptance-criterion/task, test từng failure-mode, tôn trọng "NOT in scope", và **đối chiếu plan-claim vs code thật**. Đây là ATDD đúng nghĩa (acceptance test bám kế hoạch/story, không chỉ code + domain).
> CÓ điều kiện: không có plan → ghi "no active plan" và bỏ qua, tiếp Bước 1. PHỔ QUÁT cho mọi dự án.
> Nền tảng: ATDD/Three Amigos · Specification-by-Example · RTM (ISO/IEC/IEEE 29119-3:2021) · Risk-Based.

## Mục lục
- P1 Detect — phát hiện plan đang thực thi
- P2 Deep-read — phân tích SÂU (không chỉ liệt kê)
- P3 Extract — sinh plan-derived oracles/AC (`PLAN-T*` / `PLAN-FM*`)
- P4 Cross-check & Output — plan-claim vs code + `_plan-scope.md` + Plan↔UAT matrix
- Tích hợp vào các bước sau

---

## P1 — DETECT (phát hiện plan đang thực thi)
Thứ tự ưu tiên:
```bash
# 1) Plan-mode plan file (harness set env khi ở plan mode)
PLAN_FILE="${CLAUDE_PLAN_FILE:-}"
# 2) Fallback: gstack đánh dấu plan mode → lấy plan mới nhất
[ -z "$PLAN_FILE" ] && [ "${GSTACK_PLAN_MODE:-}" = "active" ] && \
  PLAN_FILE=$(ls -t ~/.claude/plans/*.md 2>/dev/null | head -1)
# 3) Artifacts /plan-eng-review (kể cả khi không ở plan mode)
SLUG=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)")
TASKS_JSONL=$(ls -t ~/.gstack/projects/$SLUG/tasks-eng-review-*.jsonl 2>/dev/null | head -1)
TEST_PLAN=$(ls -t ~/.gstack/projects/$SLUG/*eng-review-test-plan-*.md 2>/dev/null | head -1)
# 4) PR đang mở trên nhánh hiện tại (acceptance + scope)
PR_BODY=$(gh pr view --json body -q .body 2>/dev/null)
```
Không có nguồn nào → **ghi "Bước 0.5: no active plan — skip"**, tiếp Bước 1. Có ≥1 nguồn → tiếp P2.

## P2 — DEEP-READ (phân tích SÂU, không chỉ liệt kê)
Đọc & hiểu (đọc nội dung, không grep máy móc):
- **Ý ĐỊNH** (`## Context`): vấn đề gì, kết quả mong đợi gì → là "Purpose oracle".
- **Mỗi `## PR<N>`**: root cause + **decisions đã chốt** + "Test kỹ local" notes → mỗi decision là một claim phải verify.
- **`## Implementation Tasks`**: `- [ ] **T<n> (P0–P3)**` + `Files:` + `Verify:` (hoặc fields JSONL `id/priority/files/title/source_finding`). P0/P1 = rủi ro cao.
- **`## Failure modes`**: mỗi dòng = một kịch bản hỏng cần TC negative + kiểm "có handling + user thấy lỗi rõ".
- **`## NOT in scope`**: kế thừa thẳng vào "NOT in scope" của UAT (đừng test cái plan cố tình hoãn).
- **`## GSTACK REVIEW REPORT`**: `VERDICT` + **`UNRESOLVED DECISIONS`** = rủi ro mở → TC thăm dò + flag.
- **test-plan artifact** (nếu có): `## Affected Pages/Routes · Key Interactions · Edge Cases · Critical Paths` → hint trực tiếp cho journey/E2E.

## P3 — EXTRACT → plan-derived oracles/AC
Biến plan thành rule kiểm chứng được, gắn `rule_ref` riêng:
| Nguồn trong plan | rule_ref sinh ra | oracle_type | TC bắt buộc |
|---|---|---|---|
| Implementation Task T\<n\> | `PLAN-T<n>` | Claim | hành vi task tạo ra hoạt động đúng (live) |
| Failure mode #\<n\> | `PLAN-FM<n>` | Purpose | kịch bản hỏng → có handling + user thấy lỗi |
| Decision/AC trong PR | `PLAN-AC<k>` | Claim | đúng quyết định đã chốt |
| Unresolved decision | `PLAN-UNRES<k>` | GAP | TC thăm dò + ghi rủi ro mở |
- Gộp mọi `Files:` → **changed-files set** để khu trú scope (đừng đi lạc ngoài cái plan đụng).
- Mỗi `PLAN-*` ⇒ tối thiểu 1 GREEN (đúng) + (với FM) 1 RED (hỏng có kiểm soát).

## P4 — CROSS-CHECK & OUTPUT
**Đối chiếu plan-claim vs CODE THẬT** (bài học: plan ghi "đã fix" ≠ chắc đã fix):
- Mỗi task/decision → grep/Read code xác nhận đã hiện thực ở `Files:` đã nêu. Khớp → TC verify live. **Lệch (plan nói có, code chưa/khác) = finding giá trị cao** (drift), báo cáo — KHÔNG im lặng.
- Mỗi `Verify:` của task → biến thành bước assert thật trong TC (live, không mock).

**Output `docs/uat/_plan-scope.md`:**
```markdown
# Plan Scope (Bước 0.5) — nguồn: <PLAN_FILE / tasks JSONL / PR>
## In scope (tasks)   | T<n> · P<x> · component · files · verify
## Changed files      | <dedup list>
## Plan-derived AC     | PLAN-T*/PLAN-FM*/PLAN-AC* → quy tắc đo được
## Failure modes        | PLAN-FM* → kịch bản hỏng
## NOT in scope (kế thừa từ plan)
## Unresolved/Drift     | rủi ro mở + chỗ plan-claim ≠ code
## Plan↔UAT coverage matrix
| rule_ref | mô tả | TC phủ | trạng thái |
| PLAN-T1  | ...   | TC-0xx | ✅ / ❌ GAP |
```
**Quy tắc:** mỗi `PLAN-T*`/`PLAN-FM*` phải có ≥1 TC. **Plan-item không TC = gap → bổ sung hoặc giải trình** (vào self-audit).

---

## TÍCH HỢP vào các bước sau
- **Bước 4 Risk:** pre-populate từ Failure modes + task P0/P1 + unresolved (Likelihood×Impact).
- **Bước 6 RTM:** RTM gộp `rule_ref` **domain (Bước 0) + plan-derived (Bước 0.5)**; flag mọi AC/plan-item hở.
- **Bước 7 Test Cases:** mỗi TC trỏ `rule_ref` (domain hoặc `PLAN-*`); ưu tiên phủ changed-files + verify từng claim **live**.
- **Bước 10 Self-Audit:** "Plan Grounding đã chạy; 100% T-task & FM có ≥1 TC; tôn trọng NOT-in-scope; đã cross-check plan-claim vs code".
