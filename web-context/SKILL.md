---
name: web-context
version: 1.0.0
description: |
  Context snapshot cho PC02 Web (NestJS + React). Đọc state project và output briefing
  compact — dùng ở đầu conversation mới để tiếp tục làm việc ngay.
voice-triggers:
  - "web context"
  - "load web context"
  - "pc02 web"
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
---

# /web-context: PC02 Web Context Snapshot

Tạo Context Brief đầy đủ cho PC02 Web. Chạy tất cả bước theo thứ tự, không bỏ bước nào.

---

## Bước 1: Chạy shell commands (song song)

```bash
git branch --show-current
git log --oneline -15
git status --porcelain
gh pr list --state open 2>/dev/null || echo "no gh or no PRs"
cat VERSION 2>/dev/null || echo "no VERSION file"
```

---

## Bước 2: Đọc docs (parallel)

Đọc đồng thời các file sau:
- `CLAUDE.md` — full file
- `CHANGELOG.md` — 80 dòng cuối
- `TODOS.md` — full file (security findings + open TODOs)
- `C:\Users\Than Minh Trung\.claude\projects\c--PC02-pc02-case-management\memory\session_progress.md`
- `C:\Users\Than Minh Trung\.claude\projects\c--PC02-pc02-case-management\memory\project_context.md`
- `C:\Users\Than Minh Trung\.claude\projects\c--PC02-pc02-case-management\memory\project_2fa_plan.md`

---

## Bước 3: Đọc key source files (parallel)

Đọc đồng thời (chỉ các file quan trọng, không toàn bộ codebase):

- `backend/src/app.module.ts` — registry của 34 modules
- `backend/prisma/schema.prisma` — 100 dòng đầu (data models overview)
- `backend/src/auth/unit-scope.service.ts` — DataScope/UnitScope pattern
- `frontend/src/lib/features.ts` — feature flag registry

```bash
# List modules (không đọc nội dung)
ls backend/src/ 2>/dev/null | sort
ls frontend/src/features/ 2>/dev/null | sort
# Test count
cd backend && npx jest --listTests 2>/dev/null | wc -l | awk '{print "Backend test suites: "$1}' || echo "jest not available"
```

---

## Bước 4: Synthesize → Context Brief

Viết Context Brief theo template cố định bên dưới. Điền đầy đủ, không để trống section nào.

```markdown
# PC02 Web — Context Brief [DATE]

## 1. System Overview
[1-2 đoạn: PC02 là gì, stack, mục đích, domain (TT28/2020/TT-BCA, BLTTHS 2015). Source từ CLAUDE.md + memory project_context.md]

**Version:** [VERSION file]  
**Stack:** NestJS 11 + Prisma 7.4 + PostgreSQL | React 19 + TypeScript 5 + Tailwind 4 + Vite 7  
**Deploy:** Render.com — auto-deploy on push to `main`  
**Dev login:** `<dev login: xem tai lieu noi bo cua du an>`

## 2. Branch & PR
- **Branch:** [git branch --show-current]
- **PR:** [gh pr list result — số PR, title, trạng thái]
- **Last commits:**
  [git log --oneline -10]
- **Working tree:** [clean / N files modified]

## 3. Backend Architecture

**NestJS** + **Prisma** + **PostgreSQL** | JWT RS256

Backend modules (`backend/src/`):
[list từ ls backend/src/ output — nhóm theo domain]

Key modules:
- `auth/` — JWT RS256, 2FA (TwoFaService TOTP+Email OTP), guards (JwtAuthGuard, TwoFaTokenGuard, PermissionsGuard, UserThrottlerGuard), UnitScopeService
- `cases/`, `petitions/`, `incidents/` — core legal domains
- `teams/`, `directory/` — org hierarchy (Tổ/Phường, Province/District/Ward)
- `kpi/`, `dashboard/`, `reports/` — analytics
- `scheduler/` — DeadlineScheduler cron 07:00 daily (FCM push + DB notification, 24h dedup)
- `push/`, `notifications/`, `email/` — real-time + SMTP

**Auth flow:**
1. POST /auth/login → JWT access (15m) + refresh (7d)
2. TwoFaTokenGuard → TOTP or Email OTP verify
3. DataScopeInterceptor → injects `dataScope` (teamIds, userIds, writeTeamIds) per request
4. UnitScopeService → computes scope from UserTeam + DataAccessGrant

**Database (Prisma):** 40+ models, 23 migrations
Key models: User, Role, Permission, Team, UserTeam, DataAccessGrant, Case, Incident, Petition, Subject, Lawyer, Document, SystemSetting, AuditLog, FeatureFlag, UserDevice, OverdueNotification, UserAbbreviation

## 4. Frontend Architecture

**React 19** + **TypeScript 5** + **Tailwind CSS 4** + **Vite 7**

Feature modules (`frontend/src/features/`):
[list từ ls frontend/src/features/ output]

**Feature flag system:**
- `feature_flags` table (DB) → `GET /api/v1/feature-flags` → `frontend/src/lib/features.ts`
- Each module has `feature.manifest.ts` → auto-discovered via Vite `import.meta.glob`
- Runtime on/off via `@FeatureFlag(key)` guard (backend) + context check (frontend)
- **CRITICAL:** `npm run db:seed` bắt buộc mỗi deploy — thiếu seed → sidebar blank

## 5. Key Services & Patterns

**DataScope enforcement (12 resources):**
- `scope-filter.util.ts`: `assertParentInScope()`, `assertCreatorInScope()`, `buildScopeFilter()`
- Tất cả Cases, Incidents, Petitions + 9 child resources đều enforce scope theo tổ/điều tra viên

**Feature architecture:**
- Backend: `feature.manifest.ts` per module → declares `key`, `label`, `domain`, `permissions[]`
- Frontend: `menu.ts`, `routes.tsx`, `index.ts`, `feature.manifest.ts` per feature folder

**KPI Dashboard (/kpi):** 4 chỉ tiêu TT28: Thụ lý 100%, Giải quyết >90%, Khám phá >80%, Án NT/ĐBNT >95%. Drill-down theo Tổ, biểu đồ 12 tháng.

**SystemSetting:** 8+ deadline configs (BLTTHS Điều 147-149 defaults) — auto-deadline khi tạo vụ việc.

## 6. Open Issues & TODOs

[Từ TODOS.md — chỉ phần chưa complete, format gọn]
[Từ project_2fa_plan.md — status 2FA implementation]
[Nếu không có TODOS.md, ghi: "TODOS.md không tồn tại — xem git log"]

Security findings backlog:
- ⚠️ FINDING-002: .env.test in git history (requires git filter-repo + force-push — P2)
- ⚠️ PERF-001: DataScopeInterceptor N+5 queries → cần in-memory cache TTL=60s (P3)
- ⚠️ PERF-002: KPI trend ~120 DB queries → cần raw SQL GROUP BY refactor (P3)

## 7. Recent Changes

[git log --oneline -10 formatted nicely]
[CHANGELOG latest version summary]

Key changes cuối session:
- [tóm tắt từ session_progress.md]

## 8. Quick Commands

**Backend dev:**
```
cd backend && npm run start:dev
cd backend && npx jest --no-coverage
cd backend && npx prisma studio
cd backend && npx prisma migrate dev
```

**Frontend dev:**
```
cd frontend && npm run dev
cd frontend && npm run build
```

**Testing:**
```
cd backend && npm test                    # 474 tests, 28 suites
cd backend && npx jest --no-coverage      # faster, no coverage report
npx playwright test                       # 34 E2E tests (if configured)
```

**Deploy (Render):**
```
git push origin main                      # triggers auto-deploy
# Build: cd backend && npm install && npm run build && npx prisma migrate deploy && npm run db:seed
# Start: cd backend && npm run start:prod
# Health: {PRODUCTION_URL}/api/v1/health
```

**Feature flags:**
```
cd backend && npm run db:seed             # re-populate feature_flags (idempotent)
cd backend && npm run db:seed:features    # seed only feature flags
```
```

---

## Bước 5: Save file + print

```bash
mkdir -p .gstack/context
DATE=$(date +%Y-%m-%d)
echo "Saving context brief to .gstack/context/pc02-web-${DATE}.md"
```

Dùng Write tool lưu toàn bộ Context Brief vào `.gstack/context/pc02-web-[DATE].md`.

Sau đó in toàn bộ brief ra chat để Claude và user đọc được ngay.
