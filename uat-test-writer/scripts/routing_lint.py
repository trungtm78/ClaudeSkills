#!/usr/bin/env python3
"""routing_lint.py — mỗi cụm kích hoạt phải có ĐÚNG MỘT chủ.

Người dùng không gọi tên skill; họ gõ một câu, và hệ thống tự chọn dựa trên `description`.
Nếu hai skill cùng khai một cụm thì lựa chọn thành ra may rủi — và chọn sai có hậu quả
thật: gõ "chạy UAT" mà rơi vào một *writer* thì không có gì được chạy cả; rơi vào
`uat-test-runner` (được phép sửa mã) thì kết quả không dùng để ký nghiệm thu được.

Phân vai vẫn được viết trong THÂN mỗi skill — nhưng thân chỉ được đọc SAU khi đã chọn.
Trọng tài phải nằm ở `description`. Tệp này canh đúng chỗ đó.

  routing_lint.py            thoát 1 nếu có cụm bị tranh chấp
  routing_lint.py --list     in bảng ai sở hữu cụm nào

Chỉ soi các skill trong FAMILY; skill ngoài họ không liên quan.
"""
import argparse
import collections
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SKILLS = Path(__file__).resolve().parents[2]
FAMILY = ["uat-test-writer", "uat-test-runner", "uat-test-only",
          "uat-test-writer-web", "uat-test-runner-web",
          "expert-test-writer", "expert-test-runner"]
# Cụm quá chung, ai cũng có thể nhắc tới — không tính là tranh chấp.
TOO_GENERIC = {"test", "uat", "qa", "e2e", "test case", "playwright test"}


def description(skill: str) -> str:
    p = SKILLS / skill / "SKILL.md"
    if not p.is_file():
        return ""
    m = re.search(r"^description:(.*?)(?=^[a-z-]+:\s|^---\s*$)",
                  p.read_text(encoding="utf-8", errors="replace"), re.S | re.M)
    return m.group(1) if m else ""


def phrases(desc: str):
    out = set()
    for q in re.findall(r"[\"“]([^\"”]{4,40})[\"”]", desc):
        q = q.strip().lower()
        if q and q not in TOO_GENERIC:
            out.add(q)
    return out


def main():
    ap = argparse.ArgumentParser(description="Mỗi cụm kích hoạt đúng một chủ")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    owner = collections.defaultdict(list)
    present = []
    for sk in FAMILY:
        d = description(sk)
        if not d:
            continue
        present.append(sk)
        for q in phrases(d):
            owner[q].append(sk)

    clashes = {q: v for q, v in owner.items() if len(v) > 1}
    if a.list:
        print(f"routing_lint: {len(present)} skill · {len(owner)} cụm kích hoạt")
        for q, v in sorted(owner.items()):
            mark = "  ✗" if len(v) > 1 else "   "
            print(f"{mark} {q!r:38} → {', '.join(v)}")
        return 1 if clashes else 0

    if not clashes:
        print(f"routing_lint: {len(owner)} cụm kích hoạt, mỗi cụm đúng một chủ "
              f"({len(present)} skill trong họ)")
        return 0
    print(f"routing_lint: {len(clashes)} cụm BỊ TRANH CHẤP — gõ câu ấy thì rơi vào đâu là "
          f"may rủi:")
    for q, v in sorted(clashes.items(), key=lambda x: -len(x[1])):
        print(f"  ✗ {q!r} ← {', '.join(v)}")
    print("  → sửa `description` để mỗi cụm chỉ còn một chủ; skill nhường thì bỏ cụm ấy đi "
          "và nói rõ 'việc ấy thuộc <skill kia>'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
