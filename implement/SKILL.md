---
name: implement
description: Use when implementing any feature, bugfix, or behavior change end-to-end. Chains TDD (Red-Green-Refactor) → /review (internal diff review) → /codex review (independent GPT review) → verification gate (tsc + full test suite) → auto-commit per task. Defense-in-depth 3 review layers, auto-fix + retry up to 3 times per phase, auto-commit Conventional Commits but NEVER push. Use when user asks "implement X", "fix bug Y", "thêm feature Z", "code chính xác chất lượng tốt nhất", "đầy đủ TDD review codex", or chains "test + review + codex". For ship/deploy use /ship instead.
---

# /implement — TDD + Review + Codex Orchestrator

## Mục đích

Skill này orchestrate 3 skill có sẵn theo workflow defense-in-depth, đảm bảo **implement chính xác, chất lượng source tốt nhất**. Bản thân skill KHÔNG chứa logic TDD/review/codex — chỉ gọi 3 skill con và quản lý retry/commit.

**Nguồn gốc rule**: memory `feedback_review_and_codex_per_step` — sau v0.47.0.2 rollback (missed asset bundling), anh đã chốt mỗi step BẮT BUỘC /review + /codex review trước khi merge.

## Tiền điều kiện (đọc memory trước khi chạy)

Bước 1: Tìm memory folder của project hiện tại.

Claude Code auto-tạo memory folder theo cwd ở `~/.claude/projects/<slugified-cwd>/memory/MEMORY.md`. Tự xác định path bằng:
- Đọc cwd hiện tại.
- Tìm folder match ở `~/.claude/projects/` (case-insensitive, dash-separated).
- Nếu không tìm thấy → skip memory check, không block workflow.

Bước 2: Nếu `MEMORY.md` tồn tại, đọc và respect các feedback liên quan.

**Feedback chung (áp dụng mọi project nếu có entry tương ứng)**:

- `feedback_xung_ho` (nếu có) — quy tắc xưng hô em/anh hoặc tương đương.
- `feedback_no_mid_flight_questions` (nếu có) — KHÔNG AskUserQuestion mid-flight.
- `feedback_no_sleep_while_running` (nếu có) — KHÔNG `Start-Sleep`/sleep loop.
- `feedback_pick_10_of_10` (nếu có) — auto-pick max-completeness option.
- `feedback_skip_not_pass` (nếu có) — skip test ≠ PASS.
- `feedback_autonomous_commit_per_task` (nếu có) — tự commit, không hỏi.
- `feedback_post_merge_tsc` (nếu có) — BẮT BUỘC `tsc --noEmit` riêng sau merge.
- `feedback_autonomous_pr_execution` (nếu có) — autonomous trong session đã chốt plan.
- `feedback_review_and_codex_per_step` (nếu có) — rationale của chính skill này.

**Project-specific reference** (deployment, schema, env): scan toàn bộ `reference_*.md` trong memory folder, đọc các file mà filename gợi liên quan đến verification gate (vd `reference_deploy_*`, `reference_assets_*`, `reference_db_seed_*`).

Nếu memory folder không tồn tại hoặc trống → workflow vẫn chạy được, chỉ áp dụng anti-patterns default ở cuối file này.

## Workflow tổng quan

```
┌─────────────┐
│ Phase 1: TDD│ ← invoke superpowers:test-driven-development
└──────┬──────┘
       │ all tests green
       ↓
┌─────────────┐
│Phase 2:     │ ← invoke /review
│ Internal    │
│  Review     │ ← auto-fix P0/P1, retry ≤ 3
└──────┬──────┘
       │ findings = 0
       ↓
┌─────────────┐
│Phase 3:     │ ← invoke /codex review
│ Codex       │
│  Review     │ ← auto-fix, retry ≤ 3
└──────┬──────┘
       │ pass
       ↓
┌─────────────┐
│Phase 4:     │ ← tsc --noEmit + full jest + full vitest
│ Verify Gate │ ← retry ≤ 3
└──────┬──────┘
       │ all green
       ↓
┌─────────────┐
│Phase 5:     │ ← git add <files> + git commit (Conventional)
│ Auto-commit │ ← KHÔNG push
└─────────────┘
```

## Phase counters

Khởi tạo đầu workflow, tăng mỗi lần retry trong phase tương ứng:

- `tdd_retries = 0` (max 3)
- `review_retries = 0` (max 3)
- `codex_retries = 0` (max 3)
- `verify_retries = 0` (max 3)

Quá max → STOP theo format ở cuối file.

## TodoWrite tracking (BẮT BUỘC)

Tạo todo list ngay đầu workflow:

1. Phase 1 — TDD: viết test → verify red → minimal code → verify green → refactor
2. Phase 2 — /review pass (no P0/P1)
3. Phase 3 — /codex review pass
4. Phase 4 — tsc + jest + vitest all green
5. Phase 5 — git commit (Conventional Commits + Co-Authored-By)

Mark complete từng task xong, không batch.

---

## Phase 1 — TDD

**Action**: invoke `superpowers:test-driven-development` via `Skill` tool.

Cycle bắt buộc theo skill đó (Red-Green-Refactor):
1. RED: write 1 minimal failing test → run `npx jest <path>` → verify fail correctly (not typo).
2. GREEN: minimal code → `npx jest <path>` → verify pass.
3. REFACTOR: cleanup → tests still green.
4. Repeat cho mỗi behavior trong task.

**Fail handling**:
- Test red không pass sau fix → auto-fix logic + re-run jest.
- `tdd_retries++` mỗi loop.
- `tdd_retries > 3` → STOP với `BLOCKED — TDD loop exceeded 3 attempts`.

**Pass criteria**: all new tests green + existing tests vẫn green (jest output không có FAIL).

---

## Phase 2 — Internal Review (`/review`)

**Action**: invoke `review` skill via `Skill` tool.

Skill `/review` ở `~/.claude/skills/review/SKILL.md` chạy diff review nội bộ.

**Pass/fail detection** (parse output text):
- Output chứa "Findings: 0" / "No findings" / "Clean" → PASS, sang Phase 3.
- Output chứa "P0" hoặc "P1" → FAIL, cần auto-fix.
- P2 / cleanup → áp dụng nếu safe + không thay đổi behavior; skip nếu ambiguous (note lại trong commit message).

**Auto-fix loop**:
1. Đọc finding → identify file + line.
2. Apply fix (Edit tool).
3. Re-run jest path/to/affected_test để verify regression không xảy ra.
4. Re-invoke `review` skill.
5. `review_retries++`.
6. `review_retries > 3` → STOP với `BLOCKED — review loop > 3 attempts on <finding>`.

**Security-sensitive findings** (auth, RBAC, SQL injection, secrets): KHÔNG auto-fix, STOP và ask anh — theo `feedback_autonomous_pr_execution`.

---

## Phase 3 — Independent Review (`/codex review`)

**Action**: invoke `codex` skill via `Skill` tool với args `review`.

Skill `/codex` ở `~/.claude/skills/codex/SKILL.md` chạy Step 2A (Review mode). Codex CLI gọi `codex review` với `model_reasoning_effort="high"`, 5-min timeout.

**Pre-check**:
- Nếu skill báo `NOT_FOUND` (Codex CLI chưa cài) → STOP với recommendation `npm install -g @openai/codex`.
- Nếu báo `AUTH_FAILED` → STOP với recommendation `codex login`.

**Pass/fail detection**:
- Codex output thường kết bằng "PASS" / "LGTM" / "No issues" → PASS.
- Có "bug", "issue", "concern", "should fix" → FAIL.

**Auto-fix loop**:
1. Đọc Codex finding.
2. Đánh giá: có hợp lệ không? Memory `project_twinkly_crescent_pr1` cho thấy Codex đôi khi có 1-2 false positive (architecture choice đã chốt). Skip false positive, document trong commit.
3. Real finding → fix + re-run jest + re-invoke `codex review`.
4. `codex_retries++`.
5. `codex_retries > 3` → STOP.

**Security-sensitive**: tương tự Phase 2 — STOP và ask.

---

## Phase 4 — Pre-commit Verification Gate

**Action**: chạy full type check + full test suite (KHÔNG chỉ file vừa edit). Stack detection tự động, không hardcode commands.

### Bước 4.1: Detect project stack

Đọc CLAUDE.md project (nếu có) tìm section "Testing" / "Verification" / "Build" — đó là source of truth. Nếu không có, fallback theo manifest files:

| Manifest file detect | Stack | Verification commands mặc định |
|----------------------|-------|---------------------------------|
| `package.json` (root) + có `tsconfig.json` | Node monorepo TS | `npx tsc --noEmit` ở mỗi sub-package có `tsconfig.json` |
| `package.json` + có `jest.config.*` | Jest | `npx jest --no-coverage` |
| `package.json` + có `vitest.config.*` | Vitest | `npx vitest run --no-coverage` |
| `package.json` + script `test` định nghĩa | Generic Node | `npm test` |
| `pyproject.toml` / `setup.py` | Python | `pytest -q` ; nếu có `mypy.ini`/`pyrightconfig.json` thì + `mypy .` hoặc `pyright` |
| `Cargo.toml` | Rust | `cargo test` + `cargo check` |
| `go.mod` | Go | `go test ./...` + `go vet ./...` |
| `pubspec.yaml` | Flutter / Dart | `flutter test` + `flutter analyze` |
| `*.csproj` / `*.sln` | .NET | `dotnet test` + `dotnet build --no-restore` |
| `Gemfile` | Ruby | `bundle exec rspec` hoặc `bundle exec rake test` |

**Monorepo handling**: nếu phát hiện nhiều sub-package (vd PC02 có `backend/` + `frontend/`), chạy verification ở MỌI sub-package mà task vừa touch file. Detect "touched packages" bằng `git diff --name-only` so với HEAD trước phase 1.

**Override**: nếu CLAUDE.md có section "Testing" liệt kê command cụ thể (vd "Backend tests: `cd backend && npx jest`"), DÙNG command đó, không suy đoán từ manifest.

### Bước 4.2: Chạy verification commands

Theo thứ tự: typecheck → unit test → build (nếu cần). Mỗi command exit 0 mới chạy command kế tiếp.

```
1. Typecheck (tsc / mypy / cargo check / go vet / ...)
2. Test suite (jest / vitest / pytest / cargo test / go test / ...)
3. Build (chỉ chạy nếu Bước 4.3 cần asset check)
```

### Bước 4.3: Asset/bundle check (conditional)

Skip toàn bộ bước này nếu task không touch file build config / asset directory.

Trigger điều kiện (chạy build + verify dist):
- Touch `nest-cli.json`, `webpack.config.*`, `vite.config.*`, `rollup.config.*`, `tsup.config.*`.
- Touch file trong directory pattern: `**/templates/**`, `**/assets/**`, `**/static/**`, `**/public/**`.
- Touch `*.docx`, `*.xlsx`, `*.html` template files.

Khi trigger:
1. Chạy build command từ CLAUDE.md hoặc `npm run build` mặc định.
2. List output directory (`dist/`, `build/`, `out/`) so sánh với source file đã touch.
3. Nếu source file thiếu trong output → fix build config (vd nest-cli.json `assets` section, Vite `publicDir`), không phải lỗi runtime.

Quy tắc tổng quát: **mọi file template/asset trong source phải có mặt trong build output**.

### Fail handling

- Any step fail → log error + quay về Phase 2 (auto-fix bug), KHÔNG restart từ TDD.
- `verify_retries++` mỗi vòng.
- `verify_retries > 3` → STOP với `BLOCKED — verification gate failed > 3 attempts`.

### Pass criteria

Tất cả command exit 0, output không có "FAIL" / "error TS" / "ERR!" / runtime exception.

---

## Phase 5 — Auto-commit per Task

**Action**: tạo commit Conventional Commits, KHÔNG push.

```bash
git status   # verify chỉ files của task
git diff --stat   # verify scope
git add <file1> <file2> ...   # KHÔNG git add -A
git commit -m "$(cat <<'EOF'
<type>(<scope>): <description>

<optional body — nêu Codex finding skipped + lý do nếu có>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git status   # verify clean
```

**Type (Conventional Commits chuẩn)**: `feat | fix | refactor | chore | test | docs | perf | style | build | ci`.

**Scope**: tự suy ra từ path file touch (vd touch `src/auth/` → scope `auth`; touch `frontend/src/features/cases/` → scope `cases`). Nếu CLAUDE.md project có convention scope cụ thể (vd PC02 CLAUDE.md liệt kê `cases`, `petitions`, `incidents`...), ưu tiên list đó.

**NEVER**:
- `git add -A` / `git add .` — chỉ add files thuộc task.
- `git push` — anh quyết định push riêng (qua `/ship` hoặc thủ công).
- `git commit --no-verify` — không skip hooks.
- `git commit --amend` — luôn tạo commit mới.
- Commit `.env`, `keys/`, credentials.

**Verify sau commit**:
- `git status` clean (no untracked file ngoài task).
- `git log -1 --oneline` hiển thị commit vừa tạo.

---

## STOP Conditions

Bất kỳ điều kiện sau → dừng workflow ngay, báo anh theo format dưới:

1. Phase counter bất kỳ > 3.
2. Security-sensitive finding cần manual confirm.
3. Schema/migration conflict.
4. API key / credential missing.
5. Codex CLI auth fail / not installed.
6. Test khó viết do design unclear → ask anh clarify (genuine blocker, không phải mid-flight question).
7. Anh interrupt mid-flight.

**Format report**:

```
STATUS: BLOCKED | DONE_WITH_CONCERNS | DONE
REASON: <one line nguyên nhân>
PHASE: <số phase đang fail>
ATTEMPTED: <tóm tắt các retry đã thử>
RECOMMENDATION: <next step cụ thể anh cần làm>
```

---

## Anti-patterns (KHÔNG làm)

- Viết code trước test → vi phạm TDD Iron Law. Delete code, restart.
- Skip Phase 2/3 vì "diff nhỏ" → toàn bộ giá trị skill là defense-in-depth.
- Auto-push hoặc auto-create PR → đó là việc `/ship`.
- `git commit -a` hoặc `git add -A` → dễ commit nhầm `.env`, secrets.
- Sleep loop chờ test → dùng `run_in_background` nếu cần.
- Hỏi anh "có ok không" / "tiếp tục chứ" giữa phase → vi phạm `feedback_no_mid_flight_questions`.
- Claim "PASS" khi test skip → vi phạm `feedback_skip_not_pass`.
- Sửa skill `/review` hoặc `/codex` để hợp lý hoá fail → root cause, không bypass.

---

## Ví dụ workflow run

### Ví dụ A — Node monorepo (PC02-like)

User: `/implement thêm validation email empty cho CaseFormPage`

Stack detect: `package.json` + `tsconfig.json` ở `frontend/`, vitest config tồn tại.

1. TodoWrite tạo 5 phase tasks.
2. Phase 1 (TDD): RED `rejects empty email` ở `CaseFormPage.test.tsx` → vitest fail → GREEN thêm `if (!email?.trim())` → vitest pass.
3. Phase 2 (`/review`): output "Findings: 0" → PASS.
4. Phase 3 (`/codex review`): "LGTM" → PASS.
5. Phase 4 (verify): `cd frontend && npx tsc --noEmit && npx vitest run --no-coverage` → green. Backend chưa touch → skip backend.
6. Phase 5 (commit): `feat(cases): validate empty email trong CaseFormPage`.
7. Report: `STATUS: DONE`.

### Ví dụ B — Python project

User: `/implement fix off-by-one trong pagination helper`

Stack detect: `pyproject.toml`, `pytest.ini`, `mypy.ini`.

1. Phase 1 (TDD): RED test pytest reproduce bug → fail → GREEN fix `range(start, end + 1)` → pass.
2. Phase 2-3: review skills pass.
3. Phase 4 (verify): `mypy .` → green, `pytest -q` → green.
4. Phase 5 (commit): `fix(pagination): off-by-one in helper`.

### Ví dụ C — Project KHÔNG có CLAUDE.md / không có memory

Skill vẫn chạy được. Detect stack từ manifest, dùng default Conventional Commits scope từ path, không áp dụng project-specific feedback.

---

## Out of scope

- KHÔNG chain sang deploy / push / PR → dùng `/ship` riêng.
- KHÔNG modify source 3 skill con (TDD/review/codex).
- KHÔNG support plan-mode (skill này chạy execute mode).
- KHÔNG handle multi-task batching — gọi `/implement` lại cho task kế tiếp.
