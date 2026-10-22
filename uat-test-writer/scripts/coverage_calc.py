#!/usr/bin/env python3
"""coverage_calc.py — TÍNH `TC_min` và độ phủ từ Coverage Ledger. Không nhận số LLM ghi.

`TC_min` là căn cứ DUY NHẤT để nói "đã đủ ca". Trước tệp này, nó chỉ là
`data.get("tc_min", {})` ở generate_uat_excel.py:1181 và generate_uat_markdown.py:525 —
script **hiển thị** con số mà LLM đã ghi sẵn vào uat.json. Một cái sàn do chính người bị
đo tự đặt thì không phải là sàn.

Công thức (references/coverage-calculator.md): `TC_min = MAX(M1, M2, M3, M4)`
  M1  số coverage item — ĐẾM từ bảng Ledger
  M2  Σ V(G) cyclomatic — khai ở đầu Ledger (`M2=…`)
  M3  ceil(FP^1.2) — khai `FP=…`
  M4  sàn theo risk-tier: CRITICAL 120 · HIGH 80 · STANDARD 50 · LOW 25 (`risk=…`)

Chỉ M1 tính được từ bảng; M2/M3/M4 phải do người khai. Thiếu cái nào thì **nói là thiếu**,
không lấy M1 rồi tuyên bố đó là TC_min — một sàn tính từ một nguồn không phải là ENSEMBLE.

Ba phép đo đi kèm, mỗi phép chặn một đường "đủ ca trên giấy":
  * TC mồ côi — TC trỏ `cov_id` không có trong Ledger
  * item bị bỏ ngầm — item không TC nào phủ mà cũng không có dòng GAP kèm lý do
  * tổng TC < TC_min — thiếu coverage thật, KHÔNG được padding cho đủ số

Thoát: 0 đạt · 1 có vi phạm · 2 không đọc được đầu vào.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

RISK_TIER = {"CRITICAL": 120, "HIGH": 80, "STANDARD": 50, "LOW": 25}
COV_ID = re.compile(r"\bCOV-[A-Za-z0-9_-]+")
TC_ID = re.compile(r"\bTC-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b")
GAP = re.compile(r"\bGAP\b", re.I)


def parse_ledger(text: str):
    """Trả (rows, declared) — rows: [{cov_id, tcs, is_gap, reason}], declared: M2/FP/risk."""
    rows, declared = [], {}
    m = re.search(r"\bM2\s*[=:]\s*(\d+)", text)
    if m:
        declared["M2"] = int(m.group(1))
    m = re.search(r"\bFP\s*[=:]\s*(\d+(?:\.\d+)?)", text)
    if m:
        declared["FP"] = float(m.group(1))
    m = re.search(r"\brisk(?:[_-]?tier)?\s*[=:]\s*(CRITICAL|HIGH|STANDARD|LOW)", text, re.I)
    if m:
        declared["risk"] = m.group(1).upper()

    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not COV_ID.match(cells[0]):
            continue
        blob = " ".join(cells[1:])
        rows.append({"cov_id": cells[0], "tcs": TC_ID.findall(blob),
                     "is_gap": bool(GAP.search(blob)),
                     "reason": cells[-1] if cells else ""})
    return rows, declared


def main():
    ap = argparse.ArgumentParser(description="Tính TC_min và độ phủ từ Coverage Ledger")
    ap.add_argument("--ledger", required=True, help="_coverage-ledger.md")
    ap.add_argument("--uat", required=True, help="uat.json")
    ap.add_argument("--write", action="store_true",
                    help="ghi tc_min ĐÃ TÍNH đè lên uat.json")
    ap.add_argument("-o", "--output", default="")
    a = ap.parse_args()

    try:
        doc = json.loads(Path(a.uat).read_text(encoding="utf-8-sig"))
        cases = doc.get("test_cases", [])
    except (OSError, ValueError) as e:
        print(f"❌ không đọc được {a.uat}: {e}", file=sys.stderr)
        return 2

    lp = Path(a.ledger)
    if not lp.is_file():
        # KHÔNG bịa một con số. Ghi rõ là chưa đo được để self_audit hạ trần.
        tc_min = {"status": "KHÔNG ĐO ĐƯỢC", "reason": f"không đọc được Ledger {a.ledger}"}
        if a.write:
            doc["tc_min"] = tc_min
            Path(a.uat).write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
        print(f"❌ coverage_calc: không đọc được Ledger {a.ledger} — TC_min KHÔNG ĐO ĐƯỢC. "
              f"Không lấy số nào thay thế.")
        return 1

    rows, declared = parse_ledger(lp.read_text(encoding="utf-8-sig"))
    ledger_ids = {r["cov_id"] for r in rows}

    M = {"M1": len(rows)}
    if "M2" in declared:
        M["M2"] = declared["M2"]
    if "FP" in declared:
        M["M3"] = math.ceil(declared["FP"] ** 1.2)
    if "risk" in declared:
        M["M4"] = RISK_TIER[declared["risk"]]
    missing = [k for k in ("M2", "M3", "M4") if k not in M]
    tc_min_val = max(M.values()) if M else 0

    problems = []
    # 1) TC mồ côi
    orphan = []
    for c in cases:
        ids = c.get("coverage_ids") or []
        bad = [i for i in ids if i not in ledger_ids]
        if not ids or bad:
            orphan.append(f"{c.get('tc_id')}({','.join(bad) or 'không khai'})")
    if orphan:
        problems.append(f"{len(orphan)} TC mồ côi — trỏ cov_id không có trong Ledger: "
                        f"{', '.join(orphan[:8])}")
    # 2) item bị bỏ ngầm
    silent = [r["cov_id"] for r in rows if not r["tcs"] and not r["is_gap"]]
    if silent:
        problems.append(f"{len(silent)} coverage item không TC nào phủ mà KHÔNG có dòng GAP "
                        f"kèm lý do: {', '.join(silent[:8])}")
    # 3) tổng TC < TC_min
    if tc_min_val and len(cases) < tc_min_val:
        problems.append(f"tổng TC {len(cases)} < TC_min {tc_min_val} — đào sâu coverage item, "
                        f"KHÔNG padding cho đủ số")

    covered = sum(1 for r in rows if r["tcs"])
    pct = (100.0 * covered / len(rows)) if rows else 0.0
    tc_min = {"M1": M.get("M1"), "M2": M.get("M2"), "M3": M.get("M3"), "M4": M.get("M4"),
              "max": tc_min_val, "computed_by": "coverage_calc.py",
              "coverage_pct": round(pct, 1), "items": len(rows), "covered": covered,
              "missing_inputs": missing,
              "status": "ĐỦ ENSEMBLE" if not missing else "THIẾU ĐẦU VÀO"}
    if a.write:
        doc["tc_min"] = tc_min
        Path(a.uat).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.output:
        Path(a.output).write_text(json.dumps(
            {"tc_min": tc_min, "problems": problems}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    print(f"coverage_calc: M1={M.get('M1')} · M2={M.get('M2', '—')} · M3={M.get('M3', '—')} "
          f"· M4={M.get('M4', '—')} → TC_min=MAX={tc_min_val} · tổng TC={len(cases)}")
    print(f"  độ phủ: {covered}/{len(rows)} item = {pct:.1f}%")
    if missing:
        print(f"  ! THIẾU ĐẦU VÀO {', '.join(missing)} — TC_min đang tính từ một nguồn, "
              f"chưa phải ENSEMBLE. Khai `M2=` / `FP=` / `risk=` ở đầu Ledger.")
    for x in problems:
        print(f"  ✗ {x}")
    return 1 if (problems or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
