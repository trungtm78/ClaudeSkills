---
name: deploy
description: Use when deploying completed work end-to-end. Chains /ship → /verification-before-completion → /land-and-deploy → /qa → /codex review (post-deploy audit). Auto-fix + redeploy trivial bugs (typo, null check, format), STOP + recommend rollback on major bugs (schema/auth/500/missing asset). Use when user asks "deploy X", "ship + deploy", "push + merge + deploy", "land and verify production", "deploy chính xác chất lượng cao", or chains "ship → land → qa → audit". For local code work use /implement first.
---

# /deploy — Ship + Verify + Land + QA + Codex Audit Orchestrator

## Mục đích

Skill orchestrate 5 skill có sẵn để deploy end-to-end an toàn:

1. **`/ship`** — push branch + create PR.
2. **`superpowers:verification-before-completion`** — hard gate verify CI + tests.
3. **`/land-and-deploy`** — merge PR + deploy production + health check.
4. **`/qa`** — test live production.
5. **`/codex review`** — independent post-deploy audit.

Bản thân skill KHÔNG chứa logic deploy — chỉ orchestrate, định severity bug post-deploy, và quyết auto-fix hay STOP.

**Workflow song song với `/implement`**: `/implement` lo correctness pre-commit (TDD + review + codex). `/deploy` lo shipping + production verification post-commit.

**Nguồn gốc rule**: memory `feedback_review_and_codex_per_step` (codex per step), `feedback_full_auto_ship_chain` (auto chain khi anh đã chốt). Bài học v0.47.0.2 (missed asset bundling) → cần production audit sau deploy.

## Tiền điều kiện

### Working tree state

BẮT BUỘC check ngay đầu workflow:

```bash
git status --porcelain    # phải empty hoặc chỉ tracked changes intentional
git log @{u}..HEAD --oneline   # check commits ahead of remote
```

- Có uncommitted changes → REFUSE workflow + recommend `/implement` hoặc commit trước.
- Working tree clean + không có commit ahead → REFUSE + báo "không có gì để deploy".
- Working tree clean + có commit ahead → OK, tiếp tục.

### Deploy config

Đọc CLAUDE.md project tìm section "Deploy Configuration" / "Deploy" / "Production":

- Production URL.
- Health check endpoint.
- Pipeline trigger (GitHub Actions tag/push, manual command).
- Rollback command (nếu có).

Fallback nếu CLAUDE.md không có section deploy:
- Check `.github/workflows/deploy.yml` exists → OK.
- Check `.github/workflows/*.yml` có trigger `push: branches: [main]` → OK.
- Không có gì → STOP, recommend anh chạy `/setup-deploy` trước.

### Skill availability

Verify 5 skill con tồn tại (best-effort check):

- `/ship` ở `~/.claude/skills/ship/SKILL.md`
- `superpowers:verification-before-completion` (qua Skill tool list)
- `/land-and-deploy` ở `~/.claude/skills/land-and-deploy/SKILL.md`
- `/qa` ở `~/.claude/skills/qa/SKILL.md`
- `/codex` ở `~/.claude/skills/codex/SKILL.md`

Skill nào thiếu → STOP, báo anh cài skill đó trước.

### Memory load

Tự xác định memory folder theo cwd → `~/.claude/projects/<slugified-cwd>/memory/MEMORY.md`. Đọc nếu tồn tại, respect feedback liên quan:

- `feedback_xung_ho` — quy tắc xưng hô.
- `feedback_no_mid_flight_questions` — không AskUserQuestion mid-flight.
- `feedback_no_sleep_while_running` — không sleep loop; dùng `run_in_background` + Monitor.
- `feedback_full_auto_ship_chain` — auto chain merge → deploy → next.
- `feedback_review_and_codex_per_step` — codex per step rule.
- `feedback_skip_not_pass` — skip test ≠ PASS.
- `reference_deploy_*` / `project_v*_ship.md` — lịch sử deploy/version pattern.

Memory không tồn tại → workflow vẫn chạy, áp dụng default behavior.

## Phase counters

- `ship_retries = 0` (max 1)
- `verify_retries = 0` (max 3)
- `deploy_retries = 0` (max 1)
- `redeploy_count = 0` (max 2 — số lần chain lại toàn bộ sau trivial fix)

## TodoWrite tracking (BẮT BUỘC)

Tạo todo list đầu workflow:

1. Phase 1 — /ship (PR created)
2. Phase 2 — verification-before-completion (CI green)
3. Phase 3 — /land-and-deploy (deploy live + health check)
4. Phase 4 — /qa (production test pass)
5. Phase 5 — /codex review (post-deploy audit clean)

Mark complete từng task xong, không batch.

---

## Phase 1 — `/ship` (push + create PR)

**Action**: invoke `ship` skill via `Skill` tool.

`/ship` lo: detect base branch, run pre-ship tests local, review diff, bump VERSION + CHANGELOG (theo project convention), commit remaining changes, push branch, create PR via `gh pr create`.

**Capture output**:
- PR number (cần ở Phase 2-3).
- PR URL.
- Branch name.

**Pass criteria**: PR exists, URL hiển thị, `gh pr view <PR>` trả về JSON valid.

**Fail handling**:
- /ship fail → STOP, KHÔNG auto-retry. `ship_retries++` chỉ khi anh explicit retry.
- Report root cause (test fail / push reject / PR template missing).

---

## Phase 2 — `/verification-before-completion`

**Action**: invoke `superpowers:verification-before-completion` via `Skill` tool.

Hard gate verify mọi claim "đã xong" có evidence:

- CI checks trên PR đang green: `gh pr checks <PR>`.
- Tests local pass (theo stack detect trong CLAUDE.md hoặc manifest).
- Build pass.
- Working tree không có file untracked unexpected.

**Wait policy cho CI**:
- CI đang pending → dùng `Bash run_in_background` chạy `gh pr checks <PR> --watch`, KHÔNG sleep loop.
- Hoặc dùng `Monitor` với until-loop check `gh pr checks <PR> --json state -q '.[]|.state'`.
- Timeout 15 phút → STOP với "CI watch timeout".

**Fail handling**:
- CI red → STOP, fetch `gh run view <run-id> --log-failed` cho failed job, report cho anh.
- Local verify red → quay về Phase 1 fix workflow của /ship, `verify_retries++`. Quá 3 → STOP.

---

## Phase 3 — `/land-and-deploy` (merge + deploy)

**Action**: invoke `land-and-deploy` skill via `Skill` tool, pass PR number từ Phase 1.

`/land-and-deploy` lo: merge PR (squash mặc định theo Conventional Commits convention), trigger deploy (GitHub Actions auto qua push `main`, hoặc manual command theo CLAUDE.md), watch deploy progress, health check sau deploy.

**Watch policy**:
- Dùng `gh run watch <run-id>` qua `run_in_background` hoặc `Monitor`.
- KHÔNG sleep loop.

**Health check**:
- URL từ CLAUDE.md Deploy Configuration.
- Fallback: `<production_url>/health`, `<production_url>/api/health`, `<production_url>/api/v1/health`.
- Expect HTTP 200 + body chứa `"ok"` hoặc `"healthy"` (case-insensitive).
- Retry 3 lần cách nhau 30s nếu deploy mới (cold start). Vẫn fail → treat as deploy fail.

**Pass criteria**: deploy job green, health check 200 OK.

**Fail handling**:
- Deploy job fail mid-flight → STOP, report job ID + failed step log + recommendation.
- Health check fail sau retry → kiểm tra CLAUDE.md có rollback command không:
  - Có → đề xuất rollback (KHÔNG auto-run trừ khi memory có `feedback_full_auto_ship_chain` allow), STOP report.
  - Không có → STOP report `BLOCKED — health check fail, no rollback command defined`.
- `deploy_retries++` quá 1 → STOP.

---

## Phase 4 — `/qa` (test live production)

**Action**: invoke `qa` skill via `Skill` tool. Target = production URL từ CLAUDE.md.

`/qa` lo: systematically test golden path + edge cases trên live site, screenshot evidence, detect bugs theo severity.

**Pass criteria**: không có P0/P1 bug.

**Bug detected** → đi qua **Phase Triage** (xem dưới) trước khi tiếp tục Phase 5.

---

## Phase 5 — `/codex review` (post-deploy audit)

**Action**: invoke `codex` skill via `Skill` tool với args `review`.

Mục đích **hậu kiểm**: Codex review final state có gì lệch không — vd config drift, missing migration step, env mismatch, asset thiếu, breaking change chưa flag.

Codex Review mode (Step 2A) chạy trên diff commit gần nhất với base. Sau deploy thì diff = PR vừa merge.

**Pass criteria**: Codex output "LGTM" / "No issues" / "Pass" → DONE.

**Finding detected** → đi qua **Phase Triage**.

---

## Phase Triage — Bug Severity Decision

Khi Phase 4 hoặc Phase 5 tìm bug, phân loại trước khi action.

### Trivial bug (auto-fix + redeploy)

Trigger pattern (any match):

| Loại | Ví dụ |
|------|-------|
| Text/copy | Typo, label sai, copy lỗi chính tả, sai từ ngữ |
| UI null-guard | Missing null/undefined check ở UI hiển thị, fallback "—" thiếu |
| Debug leftover | `console.log`, `print`, `debugger` quên xoá |
| Format | Date/number format sai theo locale |
| Style edge | CSS responsive break nhỏ, overflow text, padding lệch |
| A11y | Image alt thiếu, label form thiếu, aria attribute thiếu |

**Action**:
1. Báo anh 1 dòng: "Phát hiện trivial bug `<one-line>`. Auto-fix + redeploy."
2. Quay về workflow `/implement` (TDD + review + codex + commit) cho fix.
3. Sau commit, chạy lại toàn bộ `/deploy` chain từ Phase 1.
4. `redeploy_count++`. Quá 2 → escalate thành major (không tiếp tục auto-fix).

### Major bug (STOP, không auto-fix)

Trigger pattern (any match):

| Loại | Ví dụ |
|------|-------|
| Data integrity | Schema migration broken, data corruption, FK constraint sai |
| Security | Auth bypass, RBAC sai role, SQL injection, XSS, exposed secret |
| Critical error | 500 trên endpoint chính, app không boot, infinite loop |
| Breaking change | API contract change không backward compat, breaking enum value |
| Missing asset | Template/migration/seed thiếu trong deploy (kiểu v0.47.0.2) |
| Performance | Regression > 2x latency, OOM, memory leak |
| New security finding | OWASP top 10 mới, CVE mới trong dependency |

**Action**: STOP ngay, KHÔNG auto-rollback. Report:

```
STATUS: BLOCKED + DEPLOY_NEEDS_ROLLBACK
SEVERITY: MAJOR
BUG: <one-line description>
PHASE: <4 hoặc 5>
EVIDENCE: <screenshot path / log snippet / codex finding>
ROLLBACK_COMMAND: <từ CLAUDE.md, hoặc "N/A — CLAUDE.md không định nghĩa">
RECOMMENDATION: 
  1. Chạy rollback command nếu có.
  2. Hoặc hotfix qua /implement + /deploy mới.
  3. Hoặc accept + plan fix follow-up nếu user impact thấp.
```

KHÔNG tự gọi rollback command trừ khi memory `feedback_full_auto_ship_chain` explicit allow VÀ CLAUDE.md có rollback command well-defined. An toàn mặc định: STOP.

### Ambiguous bug (ask anh)

Không match rõ trivial/major (vd UX issue, business logic edge case, performance acceptable hay không):
- STOP, summary bug 2-3 dòng, đề xuất 2-3 hướng (auto-fix / accept / hotfix manual), AskUserQuestion.
- Đây là genuine blocker → được phép ask (không vi phạm `feedback_no_mid_flight_questions`).

---

## STOP Conditions

Workflow dừng ngay khi:

1. Working tree không clean lúc start.
2. CLAUDE.md không có Deploy Configuration AND `.github/workflows/deploy.yml` không tồn tại.
3. Bất kỳ skill con thiếu / fail authentication (vd Codex CLI auth).
4. Counter bất kỳ vượt max.
5. Major bug detected.
6. CI watch timeout > 15 phút.
7. Health check fail kéo dài > 5 phút (sau retry).
8. Anh interrupt mid-flight.

Format report standard:

```
STATUS: BLOCKED | DONE | DONE_WITH_CONCERNS | DEPLOY_NEEDS_ROLLBACK
PHASE: <số phase đang stop>
REASON: <one line nguyên nhân>
ATTEMPTED: <tóm tắt retry đã thử>
EVIDENCE: <link PR / run ID / screenshot path>
RECOMMENDATION: <next step cụ thể>
```

---

## Anti-patterns (KHÔNG làm)

- Chạy `/deploy` khi working tree có uncommitted changes → REFUSE.
- Auto-rollback khi gặp bug mà không có rollback command well-defined → unsafe.
- Sleep loop chờ CI / deploy → dùng `run_in_background` + Monitor.
- Hỏi anh "có ok không" giữa phase khi không có genuine blocker → vi phạm `feedback_no_mid_flight_questions`.
- Skip Phase 5 vì "deploy đã xanh rồi" → Codex hậu kiểm là phần value lớn của chuỗi này.
- Override severity classification để "đẩy nhanh deploy" → trivial/major table là contract, không bend.
- Tự bump VERSION / tạo tag → đó là việc /ship, không reimplement.
- Auto chain sang task kế tiếp (vd PR thứ 2) trừ khi `feedback_full_auto_ship_chain` allow.
- Modify source 5 skill con để "fix workflow" → root cause, không bypass.

---

## Ví dụ workflow run

### Ví dụ A — PC02 deploy (production VM Viettel)

User: `/deploy` (sau khi `/implement fix typo CaseFormPage` đã commit local)

Stack detect: GitHub Actions deploy.yml exists, CLAUDE.md có "Deploy Configuration" + production URL `http://<PROD_HOST>/`.

1. Pre-check: working tree clean ✓, 1 commit ahead origin/main ✓.
2. TodoWrite 5 task.
3. Phase 1 (`/ship`): tests pass local, push branch `fix/case-form-typo`, create PR #128. Capture PR#.
4. Phase 2 (verification): `gh pr checks 128 --watch` background → 12 phút CI green ✓.
5. Phase 3 (`/land-and-deploy`): squash merge, watch deploy run, health check `http://<PROD_HOST>/api/v1/health` → 200 ✓.
6. Phase 4 (`/qa`): /qa skill test golden path trên production → 0 P0/P1 bug ✓.
7. Phase 5 (`/codex review`): Codex audit PR #128 diff post-merge → "LGTM" ✓.
8. Report: `STATUS: DONE`, PR #128 deployed.

### Ví dụ B — Trivial bug Phase 4 → redeploy

Sau Phase 4, /qa phát hiện label "Hôs sơ" (typo "Hồ sơ"):
1. Triage classify trivial (text/copy).
2. Báo anh "Phát hiện typo 'Hôs sơ' → 'Hồ sơ'. Auto-fix + redeploy."
3. Workflow `/implement`: TDD test verify label, fix CaseFormPage.tsx, /review pass, /codex pass, commit.
4. Chạy lại `/deploy` chain từ Phase 1. `redeploy_count=1`.
5. Lần 2 chain: PASS toàn bộ. Report `STATUS: DONE` (2 PRs deployed).

### Ví dụ C — Major bug Phase 3 → STOP

Phase 3 health check fail (deploy lên nhưng backend crash do thiếu env var mới):
1. Severity classify major (critical error: app không boot).
2. CLAUDE.md có rollback command `ssh pc02vm 'bash /home/pc02/bin/rollback.sh'`.
3. STOP report:
   ```
   STATUS: DEPLOY_NEEDS_ROLLBACK
   SEVERITY: MAJOR
   BUG: backend crash sau deploy, thiếu env var NEW_FEATURE_KEY
   PHASE: 3
   EVIDENCE: deploy run 26440612922, systemctl status pc02-backend fail
   ROLLBACK_COMMAND: ssh pc02vm 'bash /home/pc02/bin/rollback.sh'
   RECOMMENDATION:
     1. Chạy rollback command để khôi phục release trước.
     2. Setup env var qua /home/pc02/shared/.env.
     3. Re-deploy qua /deploy chain lại.
   ```

### Ví dụ D — Project không có CLAUDE.md deploy section

User chạy `/deploy` ở project mới:
1. Pre-check: CLAUDE.md không có "Deploy Configuration", `.github/workflows/` không có file deploy.
2. STOP: `BLOCKED — no deploy config found. Run /setup-deploy first.`

---

## Out of scope

- KHÔNG auto-create release tag (`/ship` đã làm hoặc CI làm).
- KHÔNG chain sang task kế tiếp (1 lần chạy = 1 PR).
- KHÔNG handle pre-production environments (staging) — chỉ production.
- KHÔNG override /ship's version bump logic.
- KHÔNG auto-rollback nếu CLAUDE.md không có rollback command well-defined.
- KHÔNG modify source 5 skill con.
