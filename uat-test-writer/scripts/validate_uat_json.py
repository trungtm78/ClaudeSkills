#!/usr/bin/env python3
"""validate_uat_json.py — writer TỰ KIỂM hàng trước khi giao.

Trước tệp này, phép kiểm đầu tiên nằm ở skill khác: chú thích trong
generate_uat_markdown.py nói thẳng "runner validate trước khi sinh spec". Nghĩa là người
sản xuất không kiểm hàng của mình, đẩy sang người dùng hàng — và một `uat.json` hỏng chỉ
lộ ra sau khi đã bàn giao, khi sửa thì tốn gấp nhiều lần.

Áp ĐỦ luật của references/handoff-schema.md:
  §3 luật 1-7  field ✱ · oracle_source không rỗng/không tautology · coverage_ids không rỗng
               · backend_policy mocked-* phải kèm lý do · đếm TC khớp khai báo
               · khối tầng sâu khai nửa vời
  §5           type nào đòi khối ấy: SECURITY|PERMISSIONS→access · DATA→db_assert|
               audit_assert · STATE→transition · PERFORMANCE→perf_budget
  §6           bí mật KHÔNG được nằm trong uat.json (tệp này được commit)

Luật ở đây là BẢN SAO có chủ đích của uat-test-only/scripts/validate_cases.py. Hai bên phải
cho cùng kết quả trên cùng một tệp; bộ test của writer có ca đối chiếu chéo, lệch là đỏ.

Thoát: 0 hợp lệ · 1 có vi phạm · 2 không đọc được đầu vào.
"""
import argparse
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REQUIRED = [
    "tc_id", "title", "type", "platform", "persona", "journey_ref", "priority",
    "severity_if_fail", "oracle_type", "rule_ref", "oracle_source", "catches_bug",
    "coverage_ids", "backend_policy", "steps", "expected",
]
CURRENT_BEHAVIOUR = re.compile(
    r"(hành vi hiện tại|hanh vi hien tai|current behavio(u)?r|as[- ]is|như hiện tại)", re.I)

# §5 — type nào thì khối ấy. Giá trị là danh sách "chấp nhận một trong số".
DEEP_BLOCKS = {
    "SECURITY": [("access",)],
    "PERMISSIONS": [("access",)],
    "DATA": [("db_assert", "audit_assert", "idempotency")],
    "STATE": [("transition",)],
    "PERFORMANCE": [("perf_budget",)],
}
# Field bắt buộc bên trong từng khối — khai nửa vời là phép đo tưởng đã chạy (luật 7).
BLOCK_REQUIRED = {
    "access": ["url", "allow"],
    "db_assert": ["query", "expect"],
    "audit_assert": ["entity", "entity_id", "action"],
    "idempotency": ["url", "count_query"],
    "transition": ["from", "to"],
    "perf_budget": ["url", "p95_ms"],
}
# §6 — dấu hiệu bí mật lọt vào tệp sẽ được commit.
SECRET_PATTERNS = [
    (re.compile(r"[a-z+]+://[^\s:/@]+:[^\s:/@]+@", re.I), "DSN có user:password"),
    (re.compile(r"\b(password|passwd|mật\s*khẩu)\b\s*[:=]\s*\S+", re.I), "mật khẩu ghi thẳng"),
    (re.compile(r"\b(secret|api[_-]?key|access[_-]?token|bearer)\b\s*[:=]\s*\S{8,}", re.I),
     "khoá hoặc token"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JWT"),
]


def empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def check_case(tc, idx):
    """Trả danh sách lý do KHÔNG hợp lệ của một TC (rỗng = hợp lệ)."""
    reasons = [f"thiếu trường bắt buộc '{k}'" for k in REQUIRED if empty(tc.get(k))]

    src = str(tc.get("oracle_source") or "")
    if src and CURRENT_BEHAVIOUR.search(src):
        reasons.append("oracle_source là 'hành vi hiện tại' — lấy sản phẩm đo chính nó")
    exp = str(tc.get("expected") or "")
    if exp and CURRENT_BEHAVIOUR.search(exp):
        reasons.append("expected là 'hành vi hiện tại'")

    pol = str(tc.get("backend_policy") or "")
    if pol.startswith("mocked") and empty(tc.get("mock_reason")) \
            and empty(tc.get("backend_policy_reason")):
        reasons.append(f"backend_policy '{pol}' không kèm lý do")

    # §5 — type nào đòi khối ấy
    typ = str(tc.get("type") or "").strip().upper()
    for group in DEEP_BLOCKS.get(typ, []):
        if not any(isinstance(tc.get(b), dict) and tc.get(b) for b in group):
            reasons.append(
                f"type '{typ}' nhưng thiếu khối {' hoặc '.join(group)} (handoff-schema §5) — "
                f"không khai thì cổng tương ứng báo KHÔNG ÁP, tức một vùng rủi ro không ai đo")

    # Luật 7 — khối đã khai thì phải khai đủ
    for name, need in BLOCK_REQUIRED.items():
        blk = tc.get(name)
        if isinstance(blk, dict) and blk:
            miss = [k for k in need if empty(blk.get(k))]
            if miss:
                reasons.append(f"khối '{name}' khai nửa vời, thiếu {', '.join(miss)} — "
                               f"một phép đo tưởng đã chạy còn nguy hơn một phép đo biết là chưa chạy")

    # db_assert / idempotency chỉ được ĐỌC
    for name in ("db_assert", "idempotency"):
        blk = tc.get(name)
        if isinstance(blk, dict):
            for key in ("query", "count_query"):
                q = str(blk.get(key) or "")
                if q and not re.match(r"^\s*(SELECT|WITH)\b", q, re.I):
                    reasons.append(f"{name}.{key} không bắt đầu bằng SELECT/WITH — "
                                   f"tầng dữ liệu chỉ được phép ĐỌC")
    acc = tc.get("access")
    if isinstance(acc, dict) and acc and empty(acc.get("allow")):
        reasons.append("access.allow rỗng — không biết vai nào được phép thì không dựng "
                       "được ma trận quyền; đoán bừa tệ hơn không đo")
    return reasons


def find_secrets(raw: str):
    out = []
    for pat, what in SECRET_PATTERNS:
        for m in pat.finditer(raw):
            frag = m.group(0)
            out.append(f"{what}: …{frag[:48]}…")
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Writer tự kiểm uat.json theo handoff-schema trước khi bàn giao")
    ap.add_argument("uat_json")
    ap.add_argument("-o", "--output", default="", help="ghi báo cáo JSON (tuỳ chọn)")
    ap.add_argument("--allow-secrets", action="store_true",
                    help="CHỈ dùng khi tệp chắc chắn không được commit")
    a = ap.parse_args()

    p = Path(a.uat_json)
    try:
        raw = p.read_text(encoding="utf-8-sig")
        doc = json.loads(raw)
    except (OSError, ValueError) as e:
        print(f"❌ Không đọc được {p}: {e}", file=sys.stderr)
        return 2

    tcs = doc.get("test_cases") if isinstance(doc, dict) else doc
    if not isinstance(tcs, list):
        print("❌ uat.json không có mảng 'test_cases'", file=sys.stderr)
        return 2

    invalid, seen = [], {}
    for i, tc in enumerate(tcs):
        if not isinstance(tc, dict):
            invalid.append({"tc_id": f"#{i+1}", "reasons": ["phần tử không phải object"]})
            continue
        tid = str(tc.get("tc_id") or f"#{i+1}")
        reasons = check_case(tc, i)
        if tid in seen:
            reasons.append(f"trùng tc_id với ca thứ {seen[tid] + 1}")
        seen[tid] = i
        if reasons:
            invalid.append({"tc_id": tid, "title": str(tc.get("title") or "")[:60],
                            "reasons": reasons})

    # Luật 6 — đếm TC phải khớp con số đã khai
    declared = 0
    if isinstance(doc, dict):
        declared = int(doc.get("tc_count") or doc.get("total") or 0)
    count_mismatch = declared and declared != len(tcs)

    secrets = [] if a.allow_secrets else find_secrets(raw)

    rep = {"source": str(p), "total": len(tcs), "valid": len(tcs) - len(invalid),
           "invalid": invalid, "secrets": secrets,
           "count_declared": declared, "count_mismatch": bool(count_mismatch)}
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                  encoding="utf-8")

    bad = bool(invalid) or bool(secrets) or bool(count_mismatch)
    if not bad:
        print(f"✅ validate_uat_json: {len(tcs)} ca, tất cả hợp lệ theo handoff-schema "
              f"(§3 luật 1-7 · §5 khối tầng sâu · §6 bí mật)")
        return 0

    print(f"❌ validate_uat_json: {len(invalid)}/{len(tcs)} ca KHÔNG hợp lệ")
    for iv in invalid[:30]:
        print(f"  ✗ {iv['tc_id']}: {'; '.join(iv['reasons'])}")
    if count_mismatch:
        print(f"  ✗ khai {declared} ca nhưng mảng có {len(tcs)} ca")
    for s in secrets[:10]:
        print(f"  ✗ BÍ MẬT trong uat.json — {s}")
    if secrets:
        print("     uat.json được commit; bí mật phải nằm ở biến môi trường ngoài repo "
              "(handoff-schema §6). Chỉ khai TÊN vai.")
    print("  → sửa ở nguồn rồi sinh lại; đừng bàn giao bản này.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
