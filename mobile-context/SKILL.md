---
name: mobile-context
version: 1.0.0
description: |
  Context snapshot cho PC02 Mobile. Đọc state project và output briefing
  compact — dùng ở đầu conversation mới để tiếp tục làm việc ngay.
voice-triggers:
  - "mobile context"
  - "load mobile context"
  - "pc02 mobile"
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
---

# /mobile-context: PC02 Mobile Context Snapshot

Tạo Context Brief đầy đủ cho PC02 Mobile. Chạy tất cả bước theo thứ tự, không bỏ bước nào.

---

## Bước 1: Chạy shell commands (song song)

```bash
git branch --show-current
git log --oneline -15
git status --porcelain
gh pr list --state open 2>/dev/null || echo "no gh or no PRs"
```

---

## Bước 2: Đọc docs (parallel)

Đọc đồng thời các file sau:
- `TODOS.md` — full file
- `CHANGELOG.md` — 80 dòng cuối
- `CLAUDE.md` — full file
- `C:\Users\Than Minh Trung\.claude\projects\c--PC02-pc02-case-management\memory\session_progress.md`
- `C:\Users\Than Minh Trung\.claude\projects\c--PC02-pc02-case-management\memory\project_context.md`

---

## Bước 3: Đọc key source files

Đọc đồng thời (chỉ các file quan trọng, không toàn bộ codebase):

- `mobile/lib/core/api/api_client.dart` — auth/refresh pattern
- `mobile/lib/core/auth/auth_provider.dart` — AuthNotifier, biometric
- `mobile/lib/features/dashboard/dashboard_screen.dart` — dashboard layout
- `backend/src/scheduler/deadline.scheduler.ts` — scheduler logic
- `backend/src/petitions/dto/query-petitions.dto.ts` — overdue filter

```bash
# List Maestro flows (không đọc nội dung)
ls maestro/flows/ 2>/dev/null || echo "no maestro/flows"
# List mobile screens
find mobile/lib/features -name "*_screen.dart" 2>/dev/null | sort
# Backend test count
cd backend && npx jest --listTests 2>/dev/null | wc -l | awk '{print "Test suites: "$1}' || true
```

---

## Bước 4: Synthesize → Context Brief

Viết Context Brief theo template cố định bên dưới. Điền đầy đủ, không để trống section nào.

```markdown
# PC02 Mobile — Context Brief [DATE]

## 1. System Overview
[1-2 đoạn: PC02 là gì, stack, mục đích, domain (TT28/2020/TT-BCA, BCA). Source từ CLAUDE.md + memory project_context.md]

## 2. Branch & PR
- **Branch:** [git branch --show-current]
- **PR:** [gh pr list result — số PR, title, trạng thái]
- **Last commits:**
  [git log --oneline -10]
- **Working tree:** [clean / N files modified]

## 3. Mobile Architecture

**Flutter app:** `mobile/lib/`
- `core/api/` — API clients + interceptors (JWT refresh tự động)
- `core/auth/` — AuthNotifier (Riverpod), BiometricService, TokenStorage
- `features/` — màn hình theo feature
  [list screens từ find output]

**Flow:** Screen → Provider/Notifier → API Client → NestJS backend
**Base URL:** `http://localhost:3000/api/v1` (dev)
**Auth:** JWT access token (15m) + refresh token (7d), auto-rotate

## 4. Backend Integration

**NestJS** + **Prisma** + **PostgreSQL**

Key endpoints:
- `POST /auth/login` — login (throttle: 15 req/min per IP)
- `GET /cases` — danh sách vụ án (scope-filtered)
- `GET /incidents` — vụ việc TT28 (4 giai đoạn, 15 trạng thái)
- `GET /petitions?overdue=true` — đơn thư quá hạn (ISSUE-M001 fixed)
- `GET /notifications` — thông báo
- `GET /dashboard/stats` — 4 KPI stats
- `POST /auth/logout` — xóa refresh token

Scheduler: runs 07:00 daily (`deadline.scheduler.ts`)
- `CANH_BAO_SAP_HAN` setting (default 7 ngày) controls warning threshold
- Notifies via FCM push + DB notification record
- Dedup: 24h window per resource/user pair

## 5. Open Issues

[Từ TODOS.md — chỉ phần chưa complete, format gọn]
[Nếu không có TODOS.md, ghi: "TODOS.md không tồn tại — xem git log và memory"]

## 6. Recent Changes

[git log --oneline -10 formatted nicely]
[CHANGELOG latest version summary nếu có]

Key changes cuối session:
- [tóm tắt từ session_progress.md]

## 7. Quick Commands

**Mobile build & deploy:**
```
cd mobile && flutter build apk --debug
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

**Backend dev:**
```
cd backend && npm run start:dev
cd backend && npm test
cd backend && npx prisma studio
```

**Maestro E2E:**
```
# Run all flows (Windows Java 11 workaround):
java -cp "$HOME/.maestro/maestro_139/maestro/lib/*" maestro.cli.AppKt test maestro/flows/
# Or standard:
maestro test maestro/flows/
```

**Maestro flows có sẵn:**
[list từ ls maestro/flows/]

**Known workarounds:**
- Vietnamese text in Maestro tapOn → dùng coordinate `tapOn: { point: "X%,Y%" }`
- Maestro 2.x cần Java 17, Java 11 installed → dùng classpath invocation
```

---

## Bước 5: Save file + print

```bash
mkdir -p .gstack/context
DATE=$(date +%Y-%m-%d)
echo "Saving context brief to .gstack/context/pc02-mobile-${DATE}.md"
```

Dùng Write tool lưu toàn bộ Context Brief vào `.gstack/context/pc02-mobile-[DATE].md`.

Sau đó in toàn bộ brief ra chat để Claude và user đọc được ngay.
