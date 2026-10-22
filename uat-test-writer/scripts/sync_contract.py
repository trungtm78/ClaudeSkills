#!/usr/bin/env python3
"""sync_contract.py — giữ hợp đồng handoff CHỈ CÓ MỘT nguồn sự thật.

Trước tệp này, `handoff-schema.md` tồn tại ba bản sao trong ba skill và đã trôi khác nhau
(4588 / 4810 / 4893 byte). Không ai cố tình làm thế: sửa một bên rồi quên hai bên kia là
chuyện sẽ xảy ra, nên cách chữa không phải là dặn nhau nhớ, mà là để máy kiểm.

  sync_contract.py            chép nguồn → các bản sao, chèn header cảnh báo
  sync_contract.py --check    thoát 1 nếu một bản sao đã trôi (dùng trong bộ test)
  sync_contract.py --dups     liệt kê tệp script trùng TÊN giữa ba skill kèm băm

Nguồn:     uat-test-writer/references/handoff-schema.md
Bản sao:   uat-test-runner/references/handoff-schema.md
           uat-test-only/references/handoff-schema.md

Về `--dups`: vài script trùng tên giữa runner và test-only (resolve_credentials.py,
detect_platform.py) và đã trôi. CỐ Ý không ép đồng bộ chúng: hai pipeline có hợp đồng khác
nhau, hợp nhất bừa sẽ phá một bên mà không ai thấy ngay. Việc của lệnh này là làm cho sự
trôi ấy HIỆN RA, thay vì để nó im lặng.
"""
import argparse
import hashlib
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SKILLS = Path(__file__).resolve().parents[2]
SRC = SKILLS / "uat-test-writer" / "references" / "handoff-schema.md"
COPIES = [SKILLS / "uat-test-runner" / "references" / "handoff-schema.md",
          SKILLS / "uat-test-only" / "references" / "handoff-schema.md"]
TRIO = ["uat-test-writer", "uat-test-runner", "uat-test-only"]

HEADER = """> **BẢN SAO — SINH TỰ ĐỘNG, ĐỪNG SỬA TỆP NÀY.**
> Nguồn sự thật: `uat-test-writer/references/handoff-schema.md`.
> Sửa ở nguồn rồi chạy `python uat-test-writer/scripts/sync_contract.py`.
> `sync_contract.py --check` sẽ đỏ nếu bản sao này trôi khỏi nguồn.

"""


def body(text: str) -> str:
    """Phần nội dung thật, bỏ header bản sao nếu có — để so nguồn với bản sao cho công bằng."""
    if text.startswith("> **BẢN SAO"):
        parts = text.split("\n\n", 1)
        return parts[1] if len(parts) > 1 else ""
    return text


def digest(text: str) -> str:
    return hashlib.sha256(body(text).encode("utf-8")).hexdigest()[:12]


def cmd_dups():
    seen = {}
    for sk in TRIO:
        d = SKILLS / sk / "scripts"
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.py")) + sorted(d.glob("*.mjs")):
            seen.setdefault(f.name, []).append((sk, hashlib.sha256(f.read_bytes()).hexdigest()[:12],
                                                f.stat().st_size))
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    if not dups:
        print("sync_contract: không có script nào trùng tên giữa ba skill")
        return 0
    print(f"sync_contract: {len(dups)} script trùng tên giữa các skill "
          f"(không ép đồng bộ — chỉ làm cho sự trôi hiện ra):")
    drift = 0
    for name, rows in dups.items():
        same = len({h for _, h, _ in rows}) == 1
        drift += 0 if same else 1
        print(f"  {'=' if same else '≠'} {name}")
        for sk, h, size in rows:
            print(f"      {sk:18} {h}  {size}B")
    print(f"  → {drift}/{len(dups)} tệp đã TRÔI khác nhau")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Một nguồn sự thật cho hợp đồng handoff")
    ap.add_argument("--check", action="store_true", help="chỉ kiểm, thoát 1 nếu trôi")
    ap.add_argument("--dups", action="store_true", help="liệt kê script trùng tên + băm")
    a = ap.parse_args()
    if a.dups:
        return cmd_dups()
    if not SRC.is_file():
        print(f"sync_contract: KHÔNG thấy nguồn {SRC}", file=sys.stderr)
        return 2
    src = SRC.read_text(encoding="utf-8")
    want = digest(src)
    drifted, missing, absent = [], [], []
    for c in COPIES:
        skill_dir = c.parent.parent
        if not skill_dir.is_dir():
            # Skill hàng xóm CHƯA CÀI ở máy này. Đó không phải hợp đồng trôi — không có
            # bản sao nào để trôi. Coi nó là lỗi thì một dự án chỉ cài một skill sẽ không
            # bao giờ tự qua được cổng của chính nó.
            absent.append(skill_dir.name)
            continue
        if not c.is_file():
            missing.append(c)
            continue
        if digest(c.read_text(encoding="utf-8")) != want:
            drifted.append(c)

    if a.check:
        if not drifted and not missing:
            n = len(COPIES) + 1 - len(absent)
            note = (f" · chưa cài: {', '.join(absent)}" if absent else "")
            print(f"sync_contract: hợp đồng khớp ở {n}/{len(COPIES) + 1} skill · "
                  f"nội dung {want}{note}")
            return 0
        for c in missing:
            print(f"sync_contract: THIẾU bản sao {c}")
        for c in drifted:
            print(f"sync_contract: TRÔI — {c.parent.parent.name} không khớp nguồn "
                  f"({digest(c.read_text(encoding='utf-8'))} ≠ {want})")
        print("  chạy `python sync_contract.py` để đồng bộ lại từ nguồn")
        return 1

    for c in COPIES:
        if not c.parent.parent.is_dir():
            print(f"sync_contract: bỏ qua {c.parent.parent.name} — skill chưa cài")
            continue
        c.parent.mkdir(parents=True, exist_ok=True)
        c.write_text(HEADER + src, encoding="utf-8")
        print(f"sync_contract: ghi {c.parent.parent.name}/references/handoff-schema.md")
    print(f"sync_contract: xong · nội dung {want} · {len(COPIES)} bản sao")
    return 0


if __name__ == "__main__":
    sys.exit(main())
