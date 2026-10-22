#!/usr/bin/env python3
"""
generate_uat_markdown.py — Sinh file .md từ cùng JSON input như Excel generator.

Output file được TỐI ƯU CHO CLAUDE CODE đọc và fix bug, không cho human reader.

Tính chất:
- TC ID là H2 heading (## TC-001) để Claude Code dễ grep theo TC
- Mỗi TC có "fix context block" gợi ý vị trí fix
- Checklist machine-readable `- [ ] ...` để Claude Code tick
- Test data riêng section trên cùng (để Claude Code load context nhanh)
- Bug report template empty cho Claude Code fill khi cần
- Cross-reference TC ↔ Bug

Usage:
    python generate_uat_markdown.py <input.json> <output.md>
"""

import json
import sys
from datetime import datetime
from pathlib import Path


SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def emoji_for_priority(p):
    return {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(p, "⚪")


def emoji_for_severity(s):
    return {"Critical": "🚨", "High": "⚠️", "Medium": "⚡", "Low": "📌"}.get(s, "")


def render_test_data_section(test_data):
    """Render section Test Data — đặt trên đầu để Claude Code load context một lần."""
    lines = []
    lines.append("## 📦 Test Data\n")
    lines.append("> Dữ liệu chia sẻ giữa các TC. Claude Code đọc 1 lần, reference bằng ID khi fix.\n")

    # Accounts
    accounts = test_data.get("accounts", [])
    if accounts:
        lines.append("### 1. Tài khoản kiểm thử\n")
        lines.append("| ID | Email | Mật khẩu | Vai trò | Trạng thái | Mục đích |")
        lines.append("|----|-------|----------|---------|------------|----------|")
        for a in accounts:
            lines.append(
                f"| `{a.get('id','')}` | `{a.get('email','')}` | `{a.get('password','')}` "
                f"| {a.get('role','')} | {a.get('status','')} | {a.get('purpose','')} |"
            )
        lines.append("")

    # Boundary values
    bv = test_data.get("boundary_values", [])
    if bv:
        lines.append("### 2. Boundary Values (BVA)\n")
        lines.append("| Field | Giá trị | Loại | Kỳ vọng | Ghi chú |")
        lines.append("|-------|---------|------|---------|---------|")
        for b in bv:
            lines.append(
                f"| {b.get('field','')} | `{b.get('value','')}` | `{b.get('type','')}` "
                f"| **{b.get('expected','')}** | {b.get('notes','')} |"
            )
        lines.append("")

    # Payloads
    payloads = test_data.get("payloads", [])
    if payloads:
        lines.append("### 3. Security Payloads (OWASP)\n")
        lines.append("| Target | Payload | Loại tấn công | Kỳ vọng | OWASP Ref |")
        lines.append("|--------|---------|---------------|---------|-----------|")
        for p in payloads:
            payload_str = str(p.get('payload',''))
            # Escape pipe and newline in markdown table
            payload_str = payload_str.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {p.get('target','')} | `{payload_str}` | {p.get('attack_type','')} "
                f"| {p.get('expected','')} | `{p.get('owasp_ref','')}` |"
            )
        lines.append("")

    return "\n".join(lines)


def render_test_matrix(test_cases):
    """Render matrix tổng — Claude Code dùng để tìm TC nhanh."""
    lines = []
    lines.append("## 📋 Test Matrix\n")
    lines.append("> Bảng tóm tắt tất cả TC. Format: `priority | type | module | title`.\n")
    lines.append("| TC-ID | Pri | Loại | Module | Tiêu đề | Severity nếu fail |")
    lines.append("|-------|-----|------|--------|---------|-------------------|")

    for tc in test_cases:
        prio = tc.get("priority", "")
        lines.append(
            f"| [{tc.get('tc_id','')}](#{tc.get('tc_id','').lower()}) "
            f"| {emoji_for_priority(prio)} {prio} "
            f"| `{tc.get('type','')}` "
            f"| {tc.get('module','')} "
            f"| {tc.get('title','')} "
            f"| {emoji_for_severity(tc.get('severity_if_fail',''))} {tc.get('severity_if_fail','')} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_test_case(tc):
    """Render 1 TC ở format dày dạn cho Claude Code parse + actionable."""
    lines = []
    tc_id = tc.get("tc_id", "")
    prio = tc.get("priority", "")
    sev = tc.get("severity_if_fail", "")

    # Heading
    lines.append(f"## {tc_id}\n")

    # Meta block (machine-readable)
    lines.append("**Meta**:")
    lines.append(f"- Loại: `{tc.get('type','')}`")
    lines.append(f"- Priority: `{prio}` {emoji_for_priority(prio)}")
    lines.append(f"- Module: `{tc.get('module','')}`")
    lines.append(f"- Yêu cầu: `{tc.get('requirement','')}`")
    lines.append(f"- Kỹ thuật: `{tc.get('technique','')}`")
    lines.append(f"- Risk: `{tc.get('risk_level','')}`")
    lines.append(f"- Severity nếu fail: `{sev}` {emoji_for_severity(sev)}")
    # === Handoff-schema v10 (✱ = bắt buộc — runner validate trước khi sinh spec) ===
    if tc.get("platform"):
        lines.append(f"- Platform: `{tc.get('platform','')}`")
    if tc.get("persona"):
        lines.append(f"- Persona: `{tc.get('persona','')}`")
    if tc.get("journey_ref"):
        lines.append(f"- Journey_ref: `{tc.get('journey_ref','')}`")
    lines.append("")

    # Oracle block (✱ — trái tim của TC, chống tautology)
    oracle_type = tc.get("oracle_type", "")
    if oracle_type or tc.get("rule_ref") or tc.get("oracle_source"):
        lines.append("**Oracle**:")
        lines.append(f"- Oracle_type: `{oracle_type}`")
        lines.append(f"- Rule_ref: `{tc.get('rule_ref','')}`")
        lines.append(f"- Oracle_source: {tc.get('oracle_source','')}")
        if tc.get("catches_bug"):
            lines.append(f"- Catches_bug: {tc.get('catches_bug','')}")
        lines.append("")

    # Traceability + runner contract
    cov = tc.get("coverage_ids", [])
    if isinstance(cov, str):
        cov = [c.strip() for c in cov.split(",") if c.strip()]
    if cov or tc.get("backend_policy") or tc.get("locator_hint"):
        lines.append("**Runner contract**:")
        if cov:
            lines.append(f"- Coverage_ids: {', '.join(f'`{c}`' for c in cov)}")
        if tc.get("backend_policy"):
            lines.append(f"- Backend_policy: `{tc.get('backend_policy','')}`")
        if tc.get("locator_hint"):
            lines.append(f"- Locator_hint: `{tc.get('locator_hint','')}`")
        ev = tc.get("evidence_required", [])
        if isinstance(ev, str):
            ev = [e.strip() for e in ev.split(",") if e.strip()]
        if ev:
            lines.append(f"- Evidence_required: {', '.join(f'`{e}`' for e in ev)}")
        lines.append("")

    # Gherkin (nếu writer sinh — BDD trace về Bước 5)
    gherkin = (tc.get("gherkin") or "").strip()
    if gherkin:
        lines.append("**Gherkin**:")
        lines.append("```gherkin")
        lines.append(gherkin)
        lines.append("```")
        lines.append("")

    # Title
    lines.append(f"**Tiêu đề**: {tc.get('title','')}\n")

    # Preconditions
    pre = tc.get("preconditions", "").strip()
    if pre:
        lines.append("### Điều kiện tiên quyết")
        for line in pre.split("\n"):
            line = line.strip()
            if line:
                lines.append(f"- {line.lstrip('123456789. ')}")
        lines.append("")

    # Steps as checklist (machine-readable, Claude Code có thể tick)
    steps = tc.get("steps", "").strip()
    if steps:
        lines.append("### Các bước kiểm thử")
        for line in steps.split("\n"):
            line = line.strip()
            if line:
                # Remove số đầu nếu có (1. 2. 3.) để chuyển thành checkbox
                clean = line.lstrip("0123456789. ").strip()
                if clean:
                    lines.append(f"- [ ] {clean}")
        lines.append("")

    # Test data
    test_data = tc.get("test_data", "").strip()
    if test_data:
        lines.append("### Dữ liệu kiểm thử")
        lines.append("```")
        lines.append(test_data)
        lines.append("```")
        lines.append("")

    # Expected results — support compact 'expected' field (lean mode) or full 3-layer
    lines.append("### Kết quả mong đợi")

    combined_expected = tc.get("expected", "").strip()
    if combined_expected:
        # LEAN MODE: single expected field
        for line in combined_expected.split("\n"):
            line = line.strip()
            if line:
                clean = line.lstrip("0123456789. ").strip()
                if clean:
                    lines.append(f"- {clean}")
        lines.append("")
    else:
        # FULL MODE: separate UI/API/Side
        eui = tc.get("expected_ui", "").strip()
        if eui:
            lines.append("**UI**:")
            for line in eui.split("\n"):
                line = line.strip()
                if line:
                    clean = line.lstrip("0123456789. ").strip()
                    if clean:
                        lines.append(f"- {clean}")
            lines.append("")

        eapi = tc.get("expected_api", "").strip()
        if eapi:
            lines.append("**API**:")
            for line in eapi.split("\n"):
                line = line.strip()
                if line:
                    clean = line.lstrip("0123456789. ").strip()
                    if clean:
                        lines.append(f"- {clean}")
            lines.append("")

        eside = tc.get("expected_side", "").strip()
        if eside and eside.lower() not in ("n/a", "không có"):
            lines.append("**Side effects** (DB, email, log, queue...):")
            for line in eside.split("\n"):
                line = line.strip()
                if line:
                    clean = line.lstrip("0123456789. ").strip()
                    if clean:
                        lines.append(f"- {clean}")
            lines.append("")

    # Fix context block (cho Claude Code khi cần fix bug)
    lines.append("### 🔧 Fix Context (cho Claude Code khi TC này fail)")
    lines.append("")
    lines.append("**Khu vực có thể cần kiểm tra:**")

    # Suggest area from module + type
    module = tc.get("module", "").lower()
    tc_type = tc.get("type", "").upper()
    suggestions = []

    if module:
        suggestions.append(f"- Source code module `{tc.get('module','')}`: tìm component/page tương ứng")
        suggestions.append(f"- API route handler: tìm endpoint cho `{tc.get('module','')}`")

    if tc_type == "GREEN":
        suggestions.append("- Happy path flow: check business logic chính")
    elif tc_type == "RED":
        suggestions.append("- Error handling: check validation, exception handler")
    elif tc_type == "BOUNDARY":
        suggestions.append("- Validation rules: check min/max constraints trong schema/DTO")
    elif tc_type == "SECURITY":
        suggestions.append("- Input sanitization: check ORM parameterization, escaping")
        suggestions.append("- Authentication/Authorization middleware")
    elif tc_type == "A11Y":
        suggestions.append("- Component template/JSX: check semantic HTML, ARIA attrs")
        suggestions.append("- CSS focus styles, tab order")
    elif tc_type == "PERFORMANCE":
        suggestions.append("- DB queries: check N+1, missing indexes")
        suggestions.append("- API caching, payload size")
    elif tc_type == "DATA":
        suggestions.append("- Encoding handling (UTF-8), validation regex")
    elif tc_type == "COMPAT":
        suggestions.append("- CSS prefixes, polyfills, browser API checks")

    if not suggestions:
        suggestions.append("- Refer to source code structure cho module này")

    for s in suggestions:
        lines.append(s)
    lines.append("")

    lines.append("**Bug report template** (Claude Code fill khi TC này fail):")
    lines.append("```yaml")
    lines.append(f"bug_id: BUG-XXX")
    lines.append(f"tc_id: {tc_id}")
    lines.append(f"severity: {sev}")
    lines.append(f"module: {tc.get('module','')}")
    lines.append(f"reproduce_steps: |  # copy từ Các bước kiểm thử ở trên")
    lines.append(f"actual_behavior: |  # observed sau khi chạy")
    lines.append(f"root_cause: |       # Claude Code phân tích")
    lines.append(f"files_changed:")
    lines.append(f"  - path/to/file.ts")
    lines.append(f"fix_summary: |")
    lines.append(f"verified_by_retest: false  # đặt true sau khi chạy lại pass")
    lines.append("```")
    lines.append("")

    # Notes
    notes = tc.get("notes", "").strip()
    if notes:
        lines.append(f"**Ghi chú**: {notes}\n")

    lines.append("---\n")
    return "\n".join(lines)


def render_bug_section(test_cases):
    """Render section trống cho Claude Code điền bug report khi fix."""
    lines = []
    lines.append("## 🐛 Bug Reports (Claude Code điền khi fix bug)\n")
    lines.append("> Mỗi bug được phát hiện sẽ thêm 1 block ở đây. Reference TC bằng ID.\n")
    lines.append("> Template (copy + fill):\n")
    lines.append("")
    lines.append("````markdown")
    lines.append("### BUG-XXX")
    lines.append("")
    lines.append("- **TC**: TC-XXX")
    lines.append("- **Severity**: Critical | High | Medium | Low")
    lines.append("- **Status**: Open | Fixing | Fixed | Verified | Closed | Reopened")
    lines.append("- **Phát hiện**: DD/MM/YYYY")
    lines.append("- **Module**: module name")
    lines.append("")
    lines.append("**Reproduce**:")
    lines.append("1. step 1")
    lines.append("2. step 2")
    lines.append("")
    lines.append("**Expected**: ...")
    lines.append("**Actual**: ...")
    lines.append("")
    lines.append("**Root cause**:")
    lines.append("> Phân tích nguyên nhân gốc bởi Claude Code")
    lines.append("")
    lines.append("**Fix**:")
    lines.append("- [ ] File: `path/to/file.ts` line X-Y — thay đổi: ...")
    lines.append("- [ ] Add test case mới nếu cần")
    lines.append("- [ ] Update doc nếu cần")
    lines.append("")
    lines.append("**Verify**: chạy lại TC-XXX → đặt Status = Verified")
    lines.append("````")
    lines.append("")
    return "\n".join(lines)


def render_checklist(test_cases):
    """Final checklist machine-readable cho Claude Code."""
    lines = []
    lines.append("## ✅ Execution Checklist\n")
    lines.append("> Claude Code tick khi hoàn thành từng TC. Mỗi line là 1 trạng thái có thể chuyển đổi.\n")

    for tc in test_cases:
        tc_id = tc.get("tc_id", "")
        title = tc.get("title", "")
        prio = tc.get("priority", "")
        lines.append(f"- [ ] **{tc_id}** [{prio}] {title}")

    lines.append("")
    return "\n".join(lines)


def render_self_audit(test_cases):
    """Render self-audit summary."""
    lines = []
    lines.append("## 🔍 Self-Audit\n")

    # Count by type
    by_type = {}
    by_prio = {}
    by_sev = {}
    for tc in test_cases:
        t = tc.get("type", "")
        p = tc.get("priority", "")
        s = tc.get("severity_if_fail", "")
        by_type[t] = by_type.get(t, 0) + 1
        by_prio[p] = by_prio.get(p, 0) + 1
        by_sev[s] = by_sev.get(s, 0) + 1

    lines.append(f"**Tổng số TC**: {len(test_cases)}\n")

    lines.append("**Phân bố loại**:")
    for t in sorted(by_type, key=lambda x: -by_type[x]):
        lines.append(f"- `{t}`: {by_type[t]}")
    lines.append("")

    lines.append("**Phân bố priority**:")
    for p in sorted(by_prio, key=lambda x: PRIORITY_ORDER.get(x, 99)):
        lines.append(f"- {emoji_for_priority(p)} `{p}`: {by_prio[p]}")
    lines.append("")

    lines.append("**Phân bố severity nếu fail**:")
    for s in sorted(by_sev, key=lambda x: SEVERITY_ORDER.get(x, 99)):
        lines.append(f"- {emoji_for_severity(s)} `{s}`: {by_sev[s]}")
    lines.append("")

    return "\n".join(lines)


def render_data_matrix_section(data_fixtures, test_cases):
    """Render section Data Maturity Matrix - data fixtures cho runner tự seed."""
    lines = []
    lines.append("## 🗂️ Data Maturity Matrix\n")

    if not data_fixtures:
        lines.append("> _Chưa có data fixture nào. Xem `data-maturity-matrix.md` để biết cách thêm._\n")
        return "\n".join(lines)

    lines.append("> Data fixtures được runner tự động seed trước test, KHÔNG cần human chạy SQL.")
    lines.append("> Mỗi fixture có ID format `<entity>.<state>.<lifecycle>.<shape>`.\n")

    # Back-reference TC by fixture
    tc_by_fixture = {}
    for tc in test_cases:
        tc_id = tc.get("tc_id", "")
        data_req = tc.get("data_required", [])
        if isinstance(data_req, str):
            data_req = [x.strip() for x in data_req.split(",") if x.strip()]
        for fid in data_req:
            tc_by_fixture.setdefault(fid, []).append(tc_id)

    # Render từng fixture
    for fx in data_fixtures:
        fid = fx.get("fixture_id", "")
        lines.append(f"### `{fid}`\n")
        lines.append(f"**Mô tả**: {fx.get('description', '')}")
        lines.append(f"**Entity**: `{fx.get('entity', '')}` | **State**: `{fx.get('state', '')}` "
                     f"| **Lifecycle**: `{fx.get('lifecycle', '')}` | **Shape**: `{fx.get('shape', 'single')}`")
        lines.append("")

        setup = fx.get("setup_recipe", {})
        if setup:
            lines.append(f"**Setup** ({setup.get('type', 'api') if isinstance(setup, dict) else 'api'}):")
            lines.append("```json")
            lines.append(json.dumps(setup, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

        cleanup = fx.get("cleanup_recipe", {})
        if cleanup:
            lines.append(f"**Cleanup**:")
            lines.append("```json")
            lines.append(json.dumps(cleanup, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

        outputs = fx.get("outputs", {})
        if outputs:
            output_keys = ", ".join(f"`{k}`" for k in outputs.keys())
            lines.append(f"**Outputs**: {output_keys}")
            lines.append("")

        used_by = tc_by_fixture.get(fid, [])
        if used_by:
            lines.append(f"**Dùng bởi**: {', '.join(used_by)}")
            lines.append("")

        lines.append("---\n")

    # Quick reference table
    lines.append("### 📋 Bảng tóm tắt\n")
    lines.append("| Fixture ID | Entity | State | Lifecycle | TC dùng |")
    lines.append("|------------|--------|-------|-----------|---------|")
    for fx in data_fixtures:
        fid = fx.get("fixture_id", "")
        used_by = tc_by_fixture.get(fid, [])
        lines.append(
            f"| `{fid}` | {fx.get('entity', '')} | {fx.get('state', '')} "
            f"| {fx.get('lifecycle', '')} | {', '.join(used_by[:3])}{'...' if len(used_by) > 3 else ''} |"
        )
    lines.append("")

    return "\n".join(lines)


def generate_uat_markdown(input_json_path, output_md_path):
    """Main entry."""
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    feature_name = (data.get("feature_name") or data.get("feature") or "Untitled Feature")
    complexity = data.get("complexity", "medium")
    test_cases = data.get("test_cases", [])
    test_data = data.get("test_data", {})
    data_fixtures = data.get("data_fixtures", [])
    scope = data.get("scope", {})

    if not test_cases:
        print("⚠️  Warning: No test cases in input!")
        sys.exit(1)

    # Sort TC by priority then by id
    test_cases_sorted = sorted(
        test_cases,
        key=lambda x: (PRIORITY_ORDER.get(x.get("priority", ""), 99), x.get("tc_id", "")),
    )

    # Build markdown
    md = []

    # Header
    md.append(f"# UAT Test Cases — {feature_name}\n")
    md.append(f"**Generated**: {datetime.now().strftime('%d/%m/%Y %H:%M')}  ")
    md.append(f"**Complexity**: `{complexity}`  ")
    md.append(f"**Total TC**: {len(test_cases)}  ")
    md.append(f"**Companion Excel**: file `.xlsx` cùng tên trong thư mục này\n")

    # === v9: TC_min ensemble + Coverage+Effectiveness Ledger + Mutation + E2E/UX (optional keys) ===
    tcm = data.get("tc_min", {})
    if tcm:
        md.append("## 📊 TC_min — ENSEMBLE MAX (v9)\n")
        md.append(f"M1 coverage-items={tcm.get('M1','-')} · M2 ΣV(G)={tcm.get('M2','-')} · "
                  f"M3 FP^1.2={tcm.get('M3','-')} · M4 risk-tier={tcm.get('M4','-')} → "
                  f"**TC_min=MAX={tcm.get('max','-')}** · Tổng TC thật={len(test_cases)} "
                  f"({'≥' if isinstance(tcm.get('max'),(int,float)) and len(test_cases)>=tcm.get('max',0) else '<'} TC_min)\n")
    ledger = data.get("coverage_ledger", [])
    if ledger:
        md.append("## 🧾 Coverage+Effectiveness Ledger (v9)\n")
        md.append("| cov_id | Kỹ thuật | Coverage item | TC phủ | Trạng thái |")
        md.append("|---|---|---|---|---|")
        for r in ledger:
            md.append(f"| {r.get('cov_id','')} | {r.get('technique','')} | {r.get('item','')} "
                      f"| {r.get('tc','')} | {r.get('status','')} |")
        md.append("")
    muts = data.get("mutations", [])
    if muts:
        md.append("## 🧬 Effectiveness — Mutation (mutant↔TC) (v9)\n")
        md.append("| mut_id | Đột biến | TC giết | Trạng thái |")
        md.append("|---|---|---|---|")
        for m in muts:
            md.append(f"| {m.get('mut_id','')} | {m.get('mutation','')} | {m.get('killed_by','')} "
                      f"| {m.get('status','')} |")
        score = data.get("mutation_score")
        md.append(f"\n**Mutation score**: {score if score is not None else 'manual (0 mutant sống sót)'}\n")
    e2e = data.get("e2e", [])
    if e2e:
        md.append("## 🎬 E2E — journey chính (Testing Trophy) (v9)\n")
        for j in e2e:
            md.append(f"- **{j.get('journey','')}** → `{j.get('spec','')}` — {j.get('status','')}")
        md.append("")
    ux = data.get("ux_findings", [])
    if ux:
        md.append("## 🎨 UI/UX (Nielsen + ISO 9241-11 + WCAG 2.2) (v9)\n")
        md.append("| cov_id | Heuristic/state | Quan sát | Severity |")
        md.append("|---|---|---|---|")
        for u in ux:
            md.append(f"| {u.get('cov_id','')} | {u.get('heuristic','')} | {u.get('note','')} "
                      f"| {u.get('severity','')} |")
        md.append("")

    # How Claude Code dùng file này
    md.append("## 🤖 Hướng dẫn cho Claude Code\n")
    md.append("File này được thiết kế để Claude Code đọc khi cần **fix bug** từ kết quả UAT.\n")
    md.append("**Workflow**:")
    md.append("1. Đọc section `## TC-XXX` của TC bị fail để hiểu context")
    md.append("2. Đọc `### 🔧 Fix Context` để biết khu vực code cần kiểm tra")
    md.append("3. Edit code → chạy lại test → đánh dấu `**Status**: Verified` trong Bug Report")
    md.append("4. File `.xlsx` companion được update bởi runner — KHÔNG edit thủ công")
    md.append("")
    md.append("**Quy ước parsing**:")
    md.append("- TC ID nằm trong heading `## TC-XXX` (anchor-able)")
    md.append("- Bug report ở format YAML trong code fence")
    md.append("- Checklist `- [ ]` có thể tick bằng cách thay thành `- [x]`")
    md.append("- Test Data ở section riêng — load 1 lần dùng cho nhiều TC\n")

    # Scope — chấp nhận cả dict {"in_scope": [...]} lẫn string mô tả gọn
    if isinstance(scope, str) and scope.strip():
        md.append("## 📐 Scope\n")
        md.append(f"{scope.strip()}\n")
        scope = {}
    if scope:
        md.append("## 📐 Scope\n")
        in_scope = scope.get("in_scope", [])
        if in_scope:
            md.append("**In scope**:")
            for s in in_scope:
                md.append(f"- {s}")
            md.append("")
        out_scope = scope.get("out_of_scope", [])
        if out_scope:
            md.append("**Out of scope**:")
            for s in out_scope:
                md.append(f"- {s}")
            md.append("")
        ec = scope.get("exit_criteria", "")
        if ec:
            md.append(f"**Exit Criteria**: {ec}\n")

    # Self-audit
    md.append(render_self_audit(test_cases_sorted))

    # Test data (load context first for Claude Code)
    md.append(render_test_data_section(test_data))

    # Data Maturity Matrix (NEW - fixtures cho runner tự seed)
    if data_fixtures:
        md.append(render_data_matrix_section(data_fixtures, test_cases_sorted))

    # Matrix
    md.append(render_test_matrix(test_cases_sorted))

    # Detail TC
    md.append("## 📝 Test Cases chi tiết\n")
    md.append("---\n")
    for tc in test_cases_sorted:
        md.append(render_test_case(tc))

    # Bug report section
    md.append(render_bug_section(test_cases_sorted))

    # Checklist
    md.append(render_checklist(test_cases_sorted))

    # Footer
    md.append("---\n")
    md.append(f"_Generated by `uat-test-writer` skill on {datetime.now().strftime('%d/%m/%Y %H:%M')}_")

    # Write
    Path(output_md_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_md_path).write_text("\n".join(md), encoding="utf-8")

    print(f"✅ Đã tạo: {output_md_path}")
    print(f"   - Tổng TC: {len(test_cases)}")
    print(f"   - Size: {Path(output_md_path).stat().st_size:,} bytes")
    return output_md_path


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_uat_markdown.py <input.json> <output.md>")
        sys.exit(1)
    generate_uat_markdown(sys.argv[1], sys.argv[2])
