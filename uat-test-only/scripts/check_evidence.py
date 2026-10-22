#!/usr/bin/env python3
"""check_evidence.py — cổng G12: một ca ĐẠT mà không có bằng chứng thì không được tính ĐẠT.

`evidence_required` đã nằm trong handoff-schema từ đầu và chưa bao giờ được kiểm. Tài liệu
QA gọi thẳng tên vấn đề: "Em test rồi, OK" không phải bằng chứng đủ mạnh. Một PASS không
kèm hiện vật thì không truy ngược được yêu cầu → ca kiểm → kết quả, tức là không ký được.

Đọc  <OUT>/cases.json + <OUT>/results.json
Ghi  <OUT>/evidence.json  — build_report.py dùng để HẠ ca thiếu bằng chứng xuống
     KHONG_CHAY(thieu-bang-chung). Script này KHÔNG sửa results.json: results.json là sự
     thật thô của lượt chạy, còn phán xét thuộc về build_report.py.

Hồ sơ bằng chứng:
  signoff (mặc định) — trace/screenshot/video luôn bật, đòi đủ hiện vật kể cả khi ca ĐẠT.
  ci                 — cấu hình nhẹ, ca ĐẠT không có hiện vật là bình thường → G12 HẠ TRẦN
                       chứ không chặn. Đặt bằng UAT_EVIDENCE_PROFILE=ci hoặc --profile ci.

Thoát: 0 = đủ · 1 = có ca thiếu bằng chứng · 2 = thiếu đầu vào.
"""
import argparse
import json
import os
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Mỗi mục trong `evidence_required` → cách nhận ra hiện vật tương ứng.
KINDS = {
    "screenshot-final": (".png", ".jpg", ".jpeg"),
    "screenshot": (".png", ".jpg", ".jpeg"),
    "trace": (".zip",),
    "video": (".webm", ".mp4"),
    "har": (".har",),
    "log": (".log", ".txt"),
    "db-snapshot": (".db.json",),
    "audit-row": (".audit.json",),
}


def has_kind(paths, kind, repo: Path) -> bool:
    exts = KINDS.get(kind)
    if exts is None:
        return True  # mục lạ: không bịa luật cho nó, ghi vào cảnh báo ở nơi khác
    for p in paths:
        fp = repo / p
        name = str(p).lower()
        if not name.endswith(tuple(exts)):
            continue
        try:
            if fp.is_file() and fp.stat().st_size > 0:
                return True
        except OSError:
            continue
    return False


def main():
    ap = argparse.ArgumentParser(description="Cổng G12: ca ĐẠT phải kèm bằng chứng theo hợp đồng")
    ap.add_argument("--out", required=True, help="<OUT>")
    ap.add_argument("--repo", default=".", help="gốc repo — đường bằng chứng tính theo đây")
    ap.add_argument("--profile", default="", help="signoff | ci (mặc định: biến UAT_EVIDENCE_PROFILE)")
    a = ap.parse_args()
    out, repo = Path(a.out), Path(a.repo)
    profile = a.profile or os.environ.get("UAT_EVIDENCE_PROFILE") or "signoff"

    try:
        cases = {c["tc_id"]: c for c in json.loads(
            (out / "cases.json").read_text(encoding="utf-8-sig")).get("cases", [])}
        rows = json.loads((out / "results.json").read_text(encoding="utf-8-sig")).get("results", [])
    except (OSError, ValueError, KeyError) as e:
        print(f"check_evidence: không đọc được cases.json / results.json: {e}", file=sys.stderr)
        return 2

    missing, checked, unknown = [], 0, set()
    for r in rows:
        tc = r.get("tc_id")
        need = (cases.get(tc) or {}).get("evidence_required") or []
        if not need:
            continue
        # Chỉ chặn ca đang được tính là ĐẠT. Ca đã FAIL/KHÔNG CHẠY thì thiếu hiện vật không
        # đổi được gì — nó đã nằm trong FINDINGS rồi.
        if r.get("status") != "PASS":
            continue
        checked += 1
        paths = r.get("evidence") or []
        for kind in need:
            if kind not in KINDS:
                unknown.add(kind)
                continue
            if not has_kind(paths, kind, repo):
                missing.append({"tc_id": tc, "need": kind, "priority": r.get("priority", "P2"),
                                "have": paths[:4]})

    degrade = profile == "ci" and bool(missing)
    rep = {"ok": not missing, "profile": profile, "degrade": degrade, "checked": checked,
           "missing": missing, "unknown_kinds": sorted(unknown)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "evidence.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    if unknown:
        print(f"check_evidence: mục bằng chứng không nhận ra (bỏ qua, không bịa luật): "
              f"{', '.join(sorted(unknown))}")
    if not missing:
        print(f"check_evidence: đủ — {checked} ca ĐẠT đều kèm đúng hiện vật đã khai (hồ sơ {profile})")
        return 0
    print(f"check_evidence: {len(missing)} ca ĐẠT thiếu bằng chứng (hồ sơ {profile})"
          + (" — hồ sơ ci nên chỉ HẠ TRẦN, không chặn" if degrade else ""))
    for m in missing[:20]:
        print(f"  x {m['tc_id']} [{m['priority']}] thiếu `{m['need']}`")
    return 1


if __name__ == "__main__":
    sys.exit(main())
