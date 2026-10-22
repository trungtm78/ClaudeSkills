#!/usr/bin/env python3
"""self_audit.py — Self-Audit Gate (Bước 10) do MÁY tính phần tính được.

Bảng `✅/❌` của Bước 10 trước đây do chính LLM tự tích. Một bản tự đánh giá mà người bị
đánh giá cầm bút thì không phải là cổng. Tệp này tách làm hai, đúng cách `uat-test-only`
xử G4/G6/G7:

  TÍNH ĐƯỢC  → script chạy thật và lấy kết quả:
               W1 validate_uat_json · W2 coverage_calc (TC_min, TC mồ côi, item bỏ ngầm)
               · sync_contract --check (hợp đồng khớp 3 skill)
  CẦN NGƯỜI  → giữ nguyên nhãn, in rõ: fault-seeding, adversarial-verify, đánh giá UX.
               Không ai được tự tích thay.

Và một trục thứ hai — TRẦN: mục **không đo được** thì KHÔNG BAO GIỜ được coi là đạt.
Kết luận: SẴN SÀNG BÀN GIAO · SẴN SÀNG-KÈM-KHUYẾT · CHƯA BÀN GIAO ĐƯỢC.

Thoát: 0 sẵn sàng · 1 chưa · 2 thiếu đầu vào.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent
NEED_HUMAN = [
    ("Fault-seeding", "mỗi business rule quan trọng có ≥1 fault giả định, và chỉ ra TC nào "
                      "bắt được — fault không TC nào bắt = oracle trang trí"),
    ("Adversarial-verify", "mỗi TC đã bị thử bác bỏ ở ngữ cảnh mới (0 tautology lọt)"),
    ("Đánh giá UX / End-user", "người đóng vai persona thật đi hết journey, không chỉ đọc TC"),
]


def sh(*cmd):
    r = subprocess.run([sys.executable, *map(str, cmd)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Self-Audit Gate của uat-test-writer")
    ap.add_argument("--uat", required=True)
    ap.add_argument("--ledger", default="")
    ap.add_argument("-o", "--output", default="")
    a = ap.parse_args()
    if not Path(a.uat).is_file():
        print(f"❌ không thấy {a.uat}", file=sys.stderr)
        return 2

    gates, blocked, degraded = [], [], []

    def gate(name, state, detail, effect=""):
        gates.append({"name": name, "state": state, "detail": detail, "effect": effect})
        if effect == "CHẶN":
            blocked.append(name)
        elif effect == "HẠ TRẦN":
            degraded.append(name)

    rc, log = sh(HERE / "validate_uat_json.py", a.uat)
    # Lấy dòng VI PHẠM đầu tiên, không lấy dòng cuối (dòng cuối chỉ là lời nhắc chung).
    first = next((l.strip() for l in log.splitlines() if "✗" in l), "")
    head = next((l.strip() for l in log.splitlines() if l.startswith(("✅", "❌"))), "")
    gate("W1 · uat.json hợp lệ theo handoff-schema",
         "ĐẠT" if rc == 0 else "HỎNG", (first or head)[:200], "" if rc == 0 else "CHẶN")

    if not a.ledger:
        gate("W2 · TC_min và độ phủ", "KHÔNG ĐO ĐƯỢC",
             "chưa chỉ định Coverage Ledger (--ledger) — không biết mẫu số thật", "HẠ TRẦN")
    else:
        rc, log = sh(HERE / "coverage_calc.py", "--ledger", a.ledger, "--uat", a.uat, "--write")
        head = next((l for l in log.splitlines() if l.startswith("coverage_calc:")), "")
        if rc == 0:
            gate("W2 · TC_min và độ phủ", "ĐẠT", head[14:].strip()[:200])
        elif "KHÔNG ĐO ĐƯỢC" in log:
            gate("W2 · TC_min và độ phủ", "KHÔNG ĐO ĐƯỢC",
                 "không đọc được Ledger — KHÔNG lấy số nào thay thế", "HẠ TRẦN")
        elif "THIẾU ĐẦU VÀO" in log or "chưa phải ENSEMBLE" in log:
            gate("W2 · TC_min và độ phủ", "KHÔNG ĐO ĐƯỢC",
                 "thiếu M2/M3/M4 — TC_min đang tính từ một nguồn, chưa phải ENSEMBLE", "HẠ TRẦN")
        else:
            gate("W2 · TC_min và độ phủ", "HỎNG",
                 "; ".join(l.strip(" ✗") for l in log.splitlines() if "✗" in l)[:300], "CHẶN")

    rc, log = sh(HERE / "sync_contract.py", "--check")
    gate("Hợp đồng handoff khớp ở 3 skill", "ĐẠT" if rc == 0 else "HỎNG",
         log.strip().splitlines()[-1][:160] if log else "", "" if rc == 0 else "CHẶN")

    for name, why in NEED_HUMAN:
        gate(name, "CẦN NGƯỜI", why, "HẠ TRẦN")

    if blocked:
        verdict = "CHƯA BÀN GIAO ĐƯỢC"
    elif degraded:
        verdict = "SẴN SÀNG-KÈM-KHUYẾT"
    else:
        verdict = "SẴN SÀNG BÀN GIAO"

    lines = [f"SELF-AUDIT: {verdict}"]
    for g in gates:
        lines.append(f"  [{g['state']:14}] {g['name']} — {g['detail']}")
    if degraded:
        lines.append("  KHUYẾT PHÉP ĐO: " + ", ".join(degraded)
                     + " — không đo được nên KHÔNG được coi là đạt.")
    print("\n".join(lines))
    if a.output:
        Path(a.output).write_text(json.dumps(
            {"verdict": verdict, "gates": gates, "degraded": degraded, "blocked": blocked},
            ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if verdict == "SẴN SÀNG BÀN GIAO" else 1


if __name__ == "__main__":
    sys.exit(main())
