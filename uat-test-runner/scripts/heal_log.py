#!/usr/bin/env python3
"""heal_log.py — runner ĐƯỢC sửa, nhưng phải KHAI đã sửa gì.

Đây là bản đối xứng của `guard_repo.py` bên `uat-test-only`: bên kia CẤM sửa và chứng minh
không sửa; bên này CHO sửa — đó là việc của vòng dev — và bắt ghi lại từng lần.

Vì sao cần: một lượt xanh sau khi heal mà không có sổ thì không giải thích được. Người đọc
báo cáo không phân biệt nổi "sản phẩm đúng" với "thước đã được chỉnh cho vừa sản phẩm".
`build_runner_report.py` đọc sổ này và hạ `GO` xuống `CONDITIONAL GO` khi heal > 0 — thước
bị chỉnh giữa lúc đo thì không thể là một lượt sạch.

  add   --tc TC-012 --what "đổi locator" --why "nút đổi aria-label sau refactor" [--who ...]
  show  in tóm tắt
  reset bắt đầu sổ mới cho một lượt chạy mới

Sổ mặc định: test-results/UAT/heal_log.json
"""
import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

DEFAULT = "test-results/UAT/heal_log.json"


def load(p: Path):
    try:
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        if isinstance(d, dict) and isinstance(d.get("entries"), list):
            return d
    except (OSError, ValueError):
        pass
    return {"entries": []}


def save(p: Path, doc):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Sổ heal của uat-test-runner")
    ap.add_argument("--file", default=DEFAULT)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a1 = sp.add_parser("add")
    a1.add_argument("--tc", required=True, help="TC bị ảnh hưởng")
    a1.add_argument("--what", required=True, help="đã đổi cái gì")
    a1.add_argument("--why", required=True, help="vì sao — 'cho test xanh' KHÔNG phải lý do")
    a1.add_argument("--who", default="uat-test-runner")
    sp.add_parser("show")
    sp.add_parser("reset")
    a = ap.parse_args()
    p = Path(a.file)

    if a.cmd == "reset":
        save(p, {"entries": [], "reset_at": _dt.datetime.now().astimezone().isoformat(
            timespec="seconds")})
        print(f"heal_log: sổ mới tại {p.as_posix()}")
        return 0

    doc = load(p)
    if a.cmd == "show":
        print(f"heal_log: {len(doc['entries'])} lần heal trong lượt này")
        for e in doc["entries"][:50]:
            print(f"  · {e.get('tc')}: {e.get('what')} — {e.get('why')}")
        return 0

    if a.why.strip().lower() in ("cho test xanh", "cho qua", "de pass", "để pass"):
        print("❌ 'cho test xanh' không phải lý do — heal phải có nguyên nhân thật "
              "(sản phẩm đổi, locator đổi, dữ liệu đổi).", file=sys.stderr)
        return 2
    doc["entries"].append({
        "at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "tc": a.tc, "what": a.what, "why": a.why, "who": a.who})
    save(p, doc)
    print(f"heal_log: ghi lần thứ {len(doc['entries'])} · {a.tc} · {a.what}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
