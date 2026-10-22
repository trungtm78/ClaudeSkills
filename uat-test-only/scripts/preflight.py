#!/usr/bin/env python3
"""preflight.py — dự án này chạy UAT được tới đâu. Chạy TRƯỚC, không phát hiện giữa chừng.

Mỗi tầng của bộ UAT cần một thứ khác nhau, và thiếu thứ nào thì cổng tương ứng **hạ trần**
chứ không đỏ. Hệ quả: một dự án mới gần như chắc chắn ra `GO-CHỜ-KÝ-KÈM-KHUYẾT` ở lượt đầu
— đúng và trung thực, nhưng nếu không biết trước thì dễ đọc nhầm thành hỏng.

Tệp này trả lời trước một câu: **cổng nào đo được, cổng nào chưa, và thiếu chính xác cái gì.**

  preflight.py [--cwd .] [--url http://…]

Không sửa gì, không cài gì, không hỏi gì. Thoát 0 luôn — đây là bản đồ, không phải cổng.
"""
import argparse
import importlib.util
import json
import os
import shutil
import socket
import sys
from pathlib import Path
from urllib import request as urlrequest

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

OK, NO = "CÓ", "THIẾU"


def has_tool(n):
    return shutil.which(n) is not None


def has_lib(n):
    try:
        return importlib.util.find_spec(n) is not None
    except (ImportError, ValueError):
        return False


def reachable(url, timeout=3):
    if not url:
        return None
    try:
        with urlrequest.urlopen(url, timeout=timeout) as r:
            return r.status
    except Exception:  # noqa: BLE001
        return 0


def main():
    ap = argparse.ArgumentParser(description="Dự án này chạy UAT được tới đâu")
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--url", default=os.environ.get("UAT_BASE_URL", ""))
    ap.add_argument("-o", "--output", default="")
    a = ap.parse_args()
    root = Path(a.cwd).resolve()
    env = os.environ

    rows = []   # (cổng, đo được?, thiếu gì)

    def row(gate, ok, need=""):
        rows.append({"gate": gate, "ok": bool(ok), "need": need})

    core = has_tool("node") and has_tool("npm")
    row("G0-G3 · G8-G12 (lõi: web/api + monkey + chứng âm)", core,
        "" if core else "node + npm — Playwright tự tải Chromium sau")
    row("Rào không-sửa G9", has_tool("git") or True,
        "" if has_tool("git") else "không phải repo git → dùng hash-tree, vẫn kiểm được")

    roles = sorted(k[len("UAT_TOKEN_"):].lower().replace("_", "-")
                   for k in env if k.startswith("UAT_TOKEN_") and k != "UAT_TOKEN_FILE"
                   and env[k])
    if env.get("UAT_TOKEN_FILE"):
        roles.append("(từ UAT_TOKEN_FILE)")
    row("G14 Ma trận quyền · IDOR", bool(roles),
        "" if roles else "UAT_TOKEN_<VAI> hoặc UAT_TOKEN_FILE — KHÔNG tự chế tài khoản")

    dsn = env.get("UAT_DB_DSN", "")
    driver = True
    if dsn.startswith(("postgres://", "postgresql://")):
        driver = has_lib("psycopg") or has_lib("psycopg2")
    elif dsn.startswith("mysql://"):
        driver = has_lib("pymysql")
    row("G15 Dữ liệu · Audit · Idempotency", bool(dsn) and driver,
        "" if dsn and driver else ("UAT_DB_DSN (role CHỈ-ĐỌC)" if not dsn
                                   else "driver Python cho DSN này"))

    row("G16 A11y đo được (axe/WCAG 2.2)", core,
        "" if core else "node + npm; @axe-core/playwright cài cùng bộ")
    row("G17 Hiệu năng p95", True, "cần `perf_budget.p95_ms` do NGƯỜI đặt trong uat.json")
    row("G8 Monkey Android", has_tool("adb"), "" if has_tool("adb") else "adb (Android SDK)")
    row("Mobile E2E (Maestro)", has_tool("maestro"), "" if has_tool("maestro") else "maestro")
    row("Đường Excel", has_lib("openpyxl"), "" if has_lib("openpyxl") else "pip install openpyxl")

    creds = any(env.get(k) for k in ("UAT_USER", "TEST_USER", "E2E_USER")) or \
        any(k.startswith("UAT_USER_") and env[k] for k in env)
    row("Ca cần đăng nhập", creds, "" if creds else "UAT_USER_<VAI>/UAT_PASS_<VAI> ngoài repo")

    st = reachable(a.url)
    row("App đang chạy (G0)", st not in (0, None),
        "" if st not in (0, None) else (f"{a.url} không phản hồi" if a.url
                                        else "chưa cho --url / UAT_BASE_URL"))

    have = sum(1 for r in rows if r["ok"])
    print(f"preflight · {root.name}")
    print(f"  Đo được {have}/{len(rows)} nhóm cổng\n")
    for r in rows:
        mark = "  ✓" if r["ok"] else "  ·"
        note = "" if r["ok"] else f"  ← {r['need']}"
        print(f"{mark} {r['gate']}{note}")
    miss = [r for r in rows if not r["ok"]]
    print()
    if miss:
        print("  Thiếu thứ nào thì cổng ấy HẠ TRẦN, không đỏ: lượt chạy vẫn ra báo cáo, kết")
        print("  luận là GO-CHỜ-KÝ-KÈM-KHUYẾT kèm dòng `KHUYẾT PHÉP ĐO:` nói rõ chưa đo được gì.")
        print("  Đó là trạng thái ĐÚNG của một dự án chưa cấp đủ, không phải lỗi.")
    else:
        print("  Đủ cho mọi cổng đo được. Ba cổng G4/G6/G7 vẫn luôn CẦN NGƯỜI.")
    if a.output:
        Path(a.output).write_text(json.dumps({"rows": rows, "roles": roles},
                                             ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
