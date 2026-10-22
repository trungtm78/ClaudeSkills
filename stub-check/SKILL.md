---
name: stub-check
description: Audit frontend and backend for unimplemented stub handlers (alert, console.log, missing onClick) and missing test cases. Generates a prioritized fix list.
---

# /stub-check: Completeness Audit

You are a **completeness auditor**. Scan the codebase for unimplemented handlers and missing tests. Report issues by priority. This skill is READ-ONLY by default — it only reports, does not fix.

**HARD GATE:** Do not implement fixes unless the user explicitly says "fix them" or "implement". Your default output is a prioritized report.

---

## Preamble

```bash
_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "BRANCH: $_BRANCH"
_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
echo "ROOT: $_ROOT"
```

---

## Phase 1: Frontend Stub Scan

Search for unimplemented handlers in all frontend .tsx/.ts files.

### 1a. Alert-only stubs

```bash
echo "=== alert() stubs ==="
grep -rn "onClick.*alert(\|=> alert(" "$_ROOT/frontend/src" --include="*.tsx" --include="*.ts" \
  | grep -v "node_modules" \
  | grep -v "window.confirm\|// " \
  | sed 's/.*src\//src\//' \
  | head -50
```

### 1b. Handler functions that ONLY contain alert()

```bash
echo "=== alert-only handler bodies ==="
grep -rn -A2 "const handle.*= () =>" "$_ROOT/frontend/src" --include="*.tsx" \
  | grep -B1 "alert(" \
  | grep -v "^--$" \
  | grep "handle" \
  | sed 's/.*src\//src\//' \
  | head -30
```

### 1c. Buttons missing onClick handler

```bash
echo "=== buttons without onClick ==="
grep -rn "<button " "$_ROOT/frontend/src" --include="*.tsx" \
  | grep -v "onClick\|disabled\|type=\"submit\"\|type='submit'" \
  | grep -v "node_modules\|//\s*<button" \
  | sed 's/.*src\//src\//' \
  | head -20
```

### 1d. console.log stubs (debug logging in handlers)

```bash
echo "=== console.log in handlers ==="
grep -rn "console\.log" "$_ROOT/frontend/src" --include="*.tsx" --include="*.ts" \
  | grep -v "node_modules\|// \|\.spec\." \
  | sed 's/.*src\//src\//' \
  | head -20
```

### 1e. TODO/FIXME markers

```bash
echo "=== TODO/FIXME ==="
grep -rn "TODO\|FIXME\|HACK\|XXX" "$_ROOT/frontend/src" --include="*.tsx" --include="*.ts" \
  | grep -v "node_modules" \
  | sed 's/.*src\//src\//' \
  | head -20
```

---

## Phase 2: Backend Stub Scan

```bash
echo "=== Backend TODO/NotImplemented ==="
grep -rn "TODO\|FIXME\|throw new Error('Not implemented')\|// stub\|placeholder" \
  "$_ROOT/backend/src" --include="*.ts" \
  | grep -v "node_modules\|\.spec\." \
  | sed 's/.*src\//src\//' \
  | head -30
```

---

## Phase 3: Test Coverage Gaps

### 3a. Backend: service files without spec files

```bash
echo "=== Services missing .spec.ts ==="
find "$_ROOT/backend/src" -name "*.service.ts" | grep -v "\.spec\." | while read f; do
  specfile="${f%.service.ts}.service.spec.ts"
  [ ! -f "$specfile" ] && echo "MISSING SPEC: $(echo $f | sed 's/.*src\//src\//') → $(echo $specfile | sed 's/.*src\//src\///')"
done
```

### 3b. Backend: controllers without spec files

```bash
echo "=== Controllers missing .spec.ts ==="
find "$_ROOT/backend/src" -name "*.controller.ts" | grep -v "\.spec\." | while read f; do
  specfile="${f%.controller.ts}.controller.spec.ts"
  [ ! -f "$specfile" ] && echo "MISSING SPEC: $(echo $f | sed 's/.*src\//src\///')"
done
```

### 3c. Frontend: pages/components without test coverage

```bash
echo "=== Frontend pages (no tests exist) ==="
echo "NOTE: Frontend has no test framework set up — 0 test files found"
find "$_ROOT/frontend/src" -name "*.test.tsx" -o -name "*.spec.tsx" 2>/dev/null | head -5 || echo "(no test files)"
```

---

## Phase 4: API Contract Risks

Scan for `res.data` directly assigned to typed state (axios bypass pattern):

```bash
echo "=== axios res.data direct to typed state ==="
grep -rn "setReportData(res\.data\|setState(res\.data\|set.*Data(res\.data\|set.*Data(response\.data" \
  "$_ROOT/frontend/src" --include="*.tsx" --include="*.ts" \
  | grep -v "as any\|: any\|node_modules" \
  | sed 's/.*src\//src\//' \
  | head -20
```

---

## Phase 5: Report

Format findings into a prioritized table:

```
╔══════════════════════════════════════════════════════════════╗
║  STUB-CHECK REPORT — {date}                                  ║
╠══════════════════════════════════════════════════════════════╣
║  Branch: {branch}                                            ║
╚══════════════════════════════════════════════════════════════╝

## P1 — Critical (broken UX, button does nothing)
[List each alert-only handler or missing onClick with file:line]

## P2 — High (fake success, no API call)
[List handlers that show success but don't call API]

## P3 — Medium (missing tests)
[List service/controller files without spec]

## P4 — Low (code quality)
[console.log stubs, TODO markers]

## API Contract Risks
[res.data direct assignments]

## Summary
- P1 Critical: N
- P2 High: N
- P3 Medium: N
- P4 Low: N
- Total: N issues
```

---

## Phase 6: Decision Gate

Use AskUserQuestion:

> Stub-check found N issues across P1/P2/P3/P4. What should we do?

Options:
- A) Fix all P1+P2 now (broken UX + fake success handlers)
- B) Fix only P1 now (buttons that do nothing)
- C) Generate TODOS.md entries for all issues
- D) Report only — I'll fix manually

If A or B: implement fixes using the CSV export pattern from `ActivityLogPage.tsx` and navigation pattern from `CaseListPage.tsx`. Commit each fix atomically.
If C: append findings to TODOS.md with priority tags.
If D: output the full report and stop.

---

## Important Rules

- **Never fix without user approval** from Phase 6 gate.
- **alert() for validation** (e.g., "Vui lòng chọn hồ sơ gốc") is NOT a stub — only `alert()` as the entire handler body counts.
- **alert() inside catch blocks** is acceptable UX (error feedback), not a stub.
- **Navigation-only handlers** (`navigate('/somewhere')`) are NOT stubs.
- Stub severity:
  - P1 = button with no onClick OR handler that only calls alert() with NO side effect
  - P2 = handler with confirm()+alert() that never calls API
  - P3 = missing test file
  - P4 = console.log debug left in production code
