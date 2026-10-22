#!/usr/bin/env python3
"""validate_cases.py — đọc danh mục ca UAT và kiểm tra hợp lệ TRƯỚC khi viết kịch bản.

Đầu vào (một trong ba):
  * uat.json theo handoff-schema (tệp có khoá "test_cases")
  * .md bố cục WRITER: khối "## TC-…" với các dòng "- Trường: giá trị"
  * .md bố cục HARNESS: bảng "| ID | Ưu tiên | Nghiêm trọng | Oracle | Kiểu | Bước | Kết quả mong đợi | …"
    với loại ca lấy từ tiêu đề mục gần nhất ("### 5.1 GREEN — …")

Đầu ra: <out>/cases.json
  { source, format, feature, cases:[…hợp lệ…], invalid:[{tc_id, title, reasons}],
    warnings:[…], stats:{total, valid, invalid} }

Luật:
  * uat.json áp ĐỦ 6 luật của handoff-schema §3.
  * .md áp LUẬT CỐT LÕI của oracle: có tc_id, có bước, có kết quả mong đợi không rỗng
    và không phải "hành vi hiện tại", có nguồn oracle. Thiếu trường phụ → cảnh báo + mặc định.
  * Ca không hợp lệ KHÔNG bị bỏ im lặng: nằm trong "invalid" để báo cáo tính là KHÔNG CHẠY.
  * 0 ca đọc được → thoát 2 (một danh mục rỗng không được biến thành "0/0 đạt").

Thoát: 0 = đọc được ≥1 ca · 2 = không đọc được ca nào / đầu vào hỏng · 1 = lỗi dùng sai.
"""
import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

# Console Windows mặc định cp932: in tiếng Việt ra stdout sẽ sập. Ép UTF-8, thay ký tự lỗi.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REQUIRED_JSON = [
    "tc_id", "title", "type", "platform", "persona", "journey_ref", "priority",
    "severity_if_fail", "oracle_type", "rule_ref", "oracle_source", "catches_bug",
    "coverage_ids", "backend_policy", "steps", "expected",
]
VALID_PLATFORMS = {"web", "android", "ios", "api", "hybrid-webview", "cli"}
# "hành vi hiện tại" làm oracle = lấy chính sản phẩm làm thước đo cho chính nó.
CURRENT_BEHAVIOUR = re.compile(r"(hành vi hiện tại|hanh vi hien tai|current behavio(u)?r|as[- ]is|như hiện tại)", re.I)
TC_ID = re.compile(r"\bTC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b")


def _empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def _as_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "\n".join(str(x).strip() for x in v if str(x).strip())
    return str(v).strip()


def _as_list(v) -> list:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [x.strip() for x in re.split(r"[,;\n]+", v.replace("`", "")) if x.strip()]
    return []


def _norm_priority(v: str) -> str:
    m = re.search(r"P\s*([0-3])", str(v or ""), re.I)
    return f"P{m.group(1)}" if m else ""


def _norm_severity(v: str) -> str:
    m = re.search(r"S\s*([1-4])", str(v or ""), re.I)
    return f"S{m.group(1)}" if m else ""


def _norm_platform(v: str, default: str) -> str:
    s = str(v or "").strip().lower()
    alias = {"mobile": "android", "hybrid": "hybrid-webview", "shell": "cli", "command": "cli",
             "lệnh": "cli", "backend": "api", "rest": "api", "ui": "web", "e2e": "web"}
    s = alias.get(s, s)
    return s if s in VALID_PLATFORMS else default


# ─────────────────────────── uat.json ───────────────────────────
def load_json(path: Path, platforms_declared):
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        tcs, meta = raw, {}
    elif isinstance(raw, dict):
        tcs = raw.get("test_cases")
        meta = raw
        if not isinstance(tcs, list):
            raise ValueError("uat.json không có mảng 'test_cases'")
    else:
        raise ValueError("uat.json không phải object/array")
    cases, invalid, warnings = [], [], []
    declared = int(meta.get("tc_count") or meta.get("total") or 0)
    for i, tc in enumerate(tcs):
        if not isinstance(tc, dict):
            invalid.append({"tc_id": f"#{i+1}", "title": "", "reasons": ["phần tử không phải object"]})
            continue
        tc = dict(tc)
        if _empty(tc.get("tc_id")) and not _empty(tc.get("id")):
            tc["tc_id"] = tc["id"]
        reasons = [f"thiếu trường bắt buộc '{k}'" for k in REQUIRED_JSON if _empty(tc.get(k))]
        src = _as_text(tc.get("oracle_source"))
        if src and CURRENT_BEHAVIOUR.search(src):
            reasons.append("oracle_source là 'hành vi hiện tại' — lấy sản phẩm đo chính nó")
        exp = _as_text(tc.get("expected"))
        if exp and CURRENT_BEHAVIOUR.search(exp):
            reasons.append("expected là 'hành vi hiện tại'")
        pol = str(tc.get("backend_policy") or "")
        if pol.startswith("mocked") and _empty(tc.get("mock_reason")) and _empty(tc.get("backend_policy_reason")):
            reasons.append(f"backend_policy '{pol}' không kèm lý do")
        plat = str(tc.get("platform") or "").strip().lower()
        if plat and platforms_declared and plat not in platforms_declared:
            warnings.append(f"{tc.get('tc_id')}: platform '{plat}' không có trong _platform.json")
        rec = _record(tc, fmt="json", default_platform="web")
        if reasons:
            invalid.append({"tc_id": rec["tc_id"] or f"#{i+1}", "title": rec["title"], "reasons": reasons,
                            "priority": rec["priority"], "platform": rec["platform"]})
        else:
            cases.append(rec)
    if declared and declared != len(tcs):
        warnings.append(f"uat.json khai {declared} ca nhưng mảng có {len(tcs)} ca")
    return cases, invalid, warnings, (meta.get("feature") or path.stem)


def _record(tc: dict, fmt: str, default_platform: str) -> dict:
    return {
        "tc_id": str(tc.get("tc_id") or "").strip(),
        "title": _as_text(tc.get("title")),
        "type": str(tc.get("type") or "").strip().upper(),
        "platform": _norm_platform(tc.get("platform"), default_platform),
        "persona": _as_text(tc.get("persona")),
        "journey_ref": _as_text(tc.get("journey_ref")),
        "priority": _norm_priority(tc.get("priority")) or "P2",
        "severity_if_fail": _norm_severity(tc.get("severity_if_fail")) or "S3",
        "oracle_type": _as_text(tc.get("oracle_type")),
        "rule_ref": _as_text(tc.get("rule_ref")),
        "oracle_source": _as_text(tc.get("oracle_source")),
        "coverage_ids": _as_list(tc.get("coverage_ids")),
        "catches_bug": _as_text(tc.get("catches_bug")),
        "module": _as_text(tc.get("module")),
        "backend_policy": _as_text(tc.get("backend_policy")) or "live",
        "data_required": _as_list(tc.get("data_required")),
        "evidence_required": _as_list(tc.get("evidence_required")),
        "seeding_method": _as_text(tc.get("seeding_method")),
        "locator_hint": _as_text(tc.get("locator_hint")),
        "steps": _as_text(tc.get("steps")),
        "expected": _as_text(tc.get("expected")),
        # --- v2: các khai báo cho tầng sâu. Giữ NGUYÊN VĂN, không suy diễn: script tương
        # ứng tự hiểu, và ca không khai gì thì tầng ấy đơn giản là không chạy cho ca đó. ---
        "determinism": tc.get("determinism") if isinstance(tc.get("determinism"), dict) else {},
        "access": tc.get("access") if isinstance(tc.get("access"), dict) else None,
        "db_assert": tc.get("db_assert") if isinstance(tc.get("db_assert"), dict) else None,
        "audit_assert": tc.get("audit_assert") if isinstance(tc.get("audit_assert"), dict) else None,
        "idempotency": tc.get("idempotency") if isinstance(tc.get("idempotency"), dict) else None,
        "transition": tc.get("transition") if isinstance(tc.get("transition"), dict) else None,
        "perf_budget": tc.get("perf_budget") if isinstance(tc.get("perf_budget"), dict) else None,
        "format": fmt,
    }


# ─────────────────────────── .md — bảng harness ───────────────────────────
HEADER_MAP = {
    "id": "tc_id", "tc-id": "tc_id", "tc id": "tc_id", "mã": "tc_id",
    "ưu tiên": "priority", "pri": "priority", "priority": "priority", "độ ưu tiên": "priority",
    "nghiêm trọng": "severity_if_fail", "severity": "severity_if_fail", "severity nếu fail": "severity_if_fail",
    "oracle": "rule_ref", "căn cứ": "rule_ref", "nguồn oracle": "oracle_source",
    "kiểu": "oracle_type", "kiểu oracle": "oracle_type",
    "bước": "steps", "bước (lệnh chạy)": "steps", "các bước": "steps", "các bước kiểm thử": "steps",
    "kết quả mong đợi": "expected", "mong đợi": "expected", "expected": "expected",
    "tiêu đề": "title", "title": "title", "loại": "type", "nền tảng": "platform", "platform": "platform",
    "module": "module", "persona": "persona", "journey_ref": "journey_ref", "hành trình": "journey_ref",
    # bảng harness: cột thao tác có ba tên khác nhau tuỳ nhóm ca
    "biên kiểm": "steps", "phép đo": "steps", "thao tác": "steps",
    # trường của khối writer (- Khoá: `giá trị`)
    "oracle_type": "oracle_type", "rule_ref": "rule_ref", "oracle_source": "oracle_source",
    "catches_bug": "catches_bug", "coverage_ids": "coverage_ids", "backend_policy": "backend_policy",
    "locator_hint": "locator_hint", "evidence_required": "evidence_required",
    "seeding_method": "seeding_method", "data_required": "data_required",
}
# Tiêu đề mục trong khối ca: chỉ hai mục này mang nội dung ca; mục khác (vd "🔧 Fix Context")
# là hướng dẫn SỬA LỖI — kỹ năng chỉ-báo-cáo không được đọc nó làm oracle.
STEP_HEAD = re.compile(r"(các bước|bước kiểm|^bước|steps)", re.I)
EXP_HEAD = re.compile(r"(kết quả mong đợi|mong đợi|expected)", re.I)
TYPE_WORDS = ["GREEN", "RED", "EDGE", "BOUNDARY", "EP", "STATE", "DECISION", "SECURITY", "DATA",
              "PERFORMANCE", "A11Y", "COMPAT", "UX", "E2E", "EXPLORATORY", "METAMORPHIC", "PERMISSIONS"]


def _split_row(line: str):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    # Không tách ở '\|' (ô có ký tự | được thoát)
    parts = re.split(r"(?<!\\)\|", s)
    return [p.strip().replace("\\|", "|") for p in parts]


def _strip_md(v: str) -> str:
    v = re.sub(r"\*\*(.+?)\*\*", r"\1", v)
    v = v.replace("`", "")
    v = re.sub(r"<br\s*/?>", "\n", v)
    return v.strip()


def parse_md(text: str, default_platform: str):
    lines = text.splitlines()
    cases, invalid, warnings = [], [], []
    seen = set()
    section_type = ""
    i = 0
    # 1) bảng
    while i < len(lines):
        ln = lines[i]
        h = re.match(r"^#{1,6}\s+(.*)$", ln)
        if h:
            t = h.group(1).upper()
            section_type = next((w for w in TYPE_WORDS if re.search(rf"\b{w}\b", t)), section_type)
        if ln.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            header = [_strip_md(c).lower() for c in _split_row(ln)]
            cols = [HEADER_MAP.get(c) for c in header]
            if "tc_id" in cols and ("expected" in cols or "steps" in cols):
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    cells = _split_row(lines[j])
                    row = {}
                    for k, key in enumerate(cols):
                        if key and k < len(cells):
                            row[key] = _strip_md(cells[k])
                    j += 1
                    m = TC_ID.search(row.get("tc_id", ""))
                    if not m:
                        continue
                    row["tc_id"] = m.group(0)
                    row.setdefault("type", section_type)
                    _md_case(row, cases, invalid, warnings, seen, default_platform)
                i = j
                continue
        i += 1
    # 2) khối "## TC-…"
    block_rows = []
    blocks = list(re.finditer(r"^#{2,4}\s+(TC-[A-Za-z0-9-]+)\b[^\n]*$", text, re.M))
    for bi, bm in enumerate(blocks):
        start = bm.end()
        end = blocks[bi + 1].start() if bi + 1 < len(blocks) else len(text)
        body = text[start:end]
        row = {"tc_id": bm.group(1).rstrip("-")}
        title = re.sub(r"^#{2,4}\s+TC-[A-Za-z0-9-]+\s*[—:\-–]?\s*", "", bm.group(0)).strip()
        if title:
            row["title"] = _strip_md(title)
        cur = None
        buf = {}
        for bl in body.splitlines():
            # Tiêu đề mục (### …): chỉ "bước" và "mong đợi" mở mục; mục khác ĐÓNG mục đang đọc.
            hm = re.match(r"^#{3,6}\s+(.*)$", bl)
            if hm:
                lk = hm.group(1).strip().lower()
                cur = "steps" if STEP_HEAD.search(lk) else ("expected" if EXP_HEAD.search(lk) else None)
                if cur:
                    buf.setdefault(cur, [])
                continue
            # Nhãn đậm trên một dòng: "**Tiêu đề**: nội dung" hoặc "**Meta**:"
            bm2 = re.match(r"^\s*\*\*([^*]{2,40})\*\*\s*:?\s*(.*)$", bl)
            if bm2:
                lk = bm2.group(1).strip().lower()
                key = HEADER_MAP.get(lk)
                if key is None and STEP_HEAD.search(lk):
                    key = "steps"
                elif key is None and EXP_HEAD.search(lk):
                    key = "expected"
                if key:
                    buf.setdefault(key, [])
                    if bm2.group(2).strip():
                        buf[key].append(_strip_md(bm2.group(2)))
                    cur = key if key in ("steps", "expected") else None
                # Nhãn phụ trong mục mong đợi ("**UI**:", "**API**:") giữ nguyên mục đang đọc —
                # bản runner reset ở đây và mất toàn bộ kết quả mong đợi dạng đầy đủ.
                continue
            # Trường "- Khoá: giá trị" — chỉ khi khoá NHẬN RA; không thì là một dòng nội dung
            # có dấu hai chấm (một gạch đầu dòng mong đợi không được đóng mục).
            fm = re.match(r"^\s*[-*]\s*\*{0,2}([^:*`]{2,40})\*{0,2}\s*:\s*(.*)$", bl)
            if fm and HEADER_MAP.get(fm.group(1).strip().lower()):
                key = HEADER_MAP[fm.group(1).strip().lower()]
                buf.setdefault(key, [])
                if fm.group(2).strip():
                    buf[key].append(_strip_md(fm.group(2)))
                continue
            if cur and bl.strip():
                t = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", bl)
                t = re.sub(r"^\[[ xX]\]\s*", "", t).strip()
                if t and t != "---":
                    buf[cur].append(_strip_md(t))
        for k, v in buf.items():
            row.setdefault(k, "\n".join(v))
        if row["tc_id"] in seen:
            continue
        block_rows.append(row)

    # Luật THÍCH ỨNG THEO TỆP: chỉ đòi trường nào mà chính tệp này chứng minh là nó mang
    # được (>=1 ca có). Nếu không có dòng nào khai `oracle_source` thì đây là bố cục rút
    # gọn, cứ theo luật cốt lõi. Nhưng khi tệp ĐÃ mang được trường ấy thì một ca bỏ trống
    # là một LỖ, không phải giới hạn của định dạng — và đó chính là đường tẩy trắng: cùng
    # một danh mục, đi bằng .json thì ca ấy không hợp lệ, đi vòng qua .md lại thành hợp lệ.
    strict_on = {f for f in ("oracle_source", "coverage_ids")
                 if any(not _empty(r.get(f)) for r in block_rows)}
    for row in block_rows:
        _md_case(row, cases, invalid, warnings, seen, default_platform, strict=strict_on)
    return cases, invalid, warnings


def _md_case(row, cases, invalid, warnings, seen, default_platform, strict=frozenset()):
    tc = row["tc_id"]
    if tc in seen:
        warnings.append(f"{tc}: trùng ID trong tệp — giữ bản đầu")
        return
    seen.add(tc)
    reasons = []
    if _empty(row.get("steps")):
        reasons.append("thiếu bước")
    exp = row.get("expected", "")
    if _empty(exp):
        reasons.append("thiếu kết quả mong đợi")
    elif CURRENT_BEHAVIOUR.search(exp):
        reasons.append("kết quả mong đợi là 'hành vi hiện tại'")
    if _empty(row.get("rule_ref")) and _empty(row.get("oracle_source")):
        reasons.append("không có nguồn oracle (cột Oracle / oracle_source)")
    if "oracle_source" in strict and _empty(row.get("oracle_source")):
        reasons.append("thiếu 'oracle_source' — tệp này có khai nguồn oracle cho ca khác, "
                       "nên ca bỏ trống là một lỗ, không phải giới hạn định dạng")
    if "coverage_ids" in strict and not _as_list(row.get("coverage_ids")):
        reasons.append("thiếu 'coverage_ids' — TC mồ côi, không trỏ Coverage Ledger")
    src = _as_text(row.get("oracle_source"))
    if src and CURRENT_BEHAVIOUR.search(src):
        reasons.append("oracle_source là 'hành vi hiện tại' — lấy sản phẩm đo chính nó")
    missing_opt = [k for k in ("platform", "persona", "journey_ref", "priority") if _empty(row.get(k))]
    if missing_opt:
        warnings.append(f"{tc}: thiếu {', '.join(missing_opt)} — dùng mặc định")
    rec = _record(row, fmt="md", default_platform=default_platform)
    if not rec["title"]:
        rec["title"] = (rec["steps"].splitlines() or [tc])[0][:80]
    if reasons:
        invalid.append({"tc_id": tc, "title": rec["title"], "reasons": reasons,
                        "priority": rec["priority"], "platform": rec["platform"]})
    else:
        cases.append(rec)


def _ledger_path(src) -> str:
    """Đường dẫn Coverage Ledger nếu nguồn có KHAI. Khai mà không đọc được là lời hứa gãy —
    build_report.py hạ trần vì khi ấy không biết mẫu số thật của phép phủ yêu cầu."""
    try:
        raw = Path(src).read_text(encoding="utf-8-sig")
    except OSError:
        return ""
    if str(src).lower().endswith(".json"):
        try:
            return str(json.loads(raw).get("coverage_ledger") or "")
        except ValueError:
            return ""
    m = re.search(r"coverage[_-]ledger\s*[:=]\s*[`\"']?([^\s`\"'|]+)", raw, re.I)
    return m.group(1) if m else ""


def main():
    ap = argparse.ArgumentParser(description="Đọc + kiểm hợp lệ danh mục ca UAT")
    ap.add_argument("--cases", required=True, help="uat.json hoặc .md")
    ap.add_argument("--out", required=True, help="thư mục kết quả của lượt chạy")
    ap.add_argument("--platform-json", default="", help="docs/uat/_platform.json (tuỳ chọn)")
    ap.add_argument("--default-platform", default="web", choices=sorted(VALID_PLATFORMS))
    a = ap.parse_args()

    src = Path(a.cases)
    if not src.is_file():
        print(f"validate_cases: không thấy tệp ca {src}", file=sys.stderr)
        return 2
    declared = set()
    if a.platform_json and Path(a.platform_json).is_file():
        try:
            pj = json.loads(Path(a.platform_json).read_text(encoding="utf-8-sig"))
            declared = {str(p).lower() for p in (pj.get("platforms") or [])}
        except (ValueError, OSError) as e:
            print(f"validate_cases: bỏ qua _platform.json hỏng: {e}", file=sys.stderr)
    try:
        if src.suffix.lower() == ".json":
            cases, invalid, warnings, feature = load_json(src, declared)
            fmt = "json"
        else:
            cases, invalid, warnings = parse_md(src.read_text(encoding="utf-8-sig"), a.default_platform)
            feature, fmt = src.stem, "md"
    except (ValueError, OSError) as e:
        print(f"validate_cases: không đọc được {src}: {e}", file=sys.stderr)
        return 2

    total = len(cases) + len(invalid)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "source": str(src), "format": fmt, "feature": feature,
        "coverage_ledger": _ledger_path(src),
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "cases": cases, "invalid": invalid, "warnings": warnings,
        "stats": {"total": total, "valid": len(cases), "invalid": len(invalid)},
    }
    (out / "cases.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"validate_cases: {total} ca · hợp lệ {len(cases)} · không hợp lệ {len(invalid)} · cảnh báo {len(warnings)}")
    for iv in invalid[:20]:
        print(f"  ✗ {iv['tc_id']}: {'; '.join(iv['reasons'])}")
    if total == 0:
        print("validate_cases: KHÔNG đọc được ca nào — dừng (0/0 không phải là đạt)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
