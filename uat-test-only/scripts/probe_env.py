#!/usr/bin/env python3
"""probe_env.py — Cổng G0: môi trường có sẵn sàng để KIỂM không. Chỉ đọc, không sửa gì.

Khác bản runner (resolve_url.py + check-env.sh):
  * Gửi HTTP thật (không chỉ mở cổng TCP); phân giải cả IPv4 lẫn IPv6 (dev server Node ≥17
    thường chỉ nghe ::1 — bản cũ chấm "app không chạy" và gợi ý mock).
  * KHÔNG bao giờ gợi ý mock server. App không tới được → NO-RUN, dừng, báo đúng như vậy.
  * Tìm trình duyệt Playwright đúng chỗ theo hệ điều hành (%LOCALAPPDATA%, ~/Library/Caches,
    ~/.cache) — bản cũ luôn tìm ~/.cache nên trên Windows luôn "thiếu", rồi tự cài đè package.json.
  * 5xx ở trang gốc KHÔNG phải lỗi môi trường: máy chủ trả lời được nghĩa là kiểm được, và
    5xx là một phát hiện về sản phẩm (ghi lại để báo cáo, không chặn G0).

Ghi <out>/probe.json: {ok, checks:{…}, problems:[…], http:{status, ms, url}}
Thoát 0 = G0 đạt · 3 = G0 hỏng (NO-RUN) · 1 = dùng sai.
"""
import argparse
import json
import os
import platform
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def browsers_dir() -> Path:
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env and env != "0":
        return Path(env)
    sysname = platform.system()
    if sysname == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "ms-playwright"
    if sysname == "Darwin":
        return Path.home() / "Library/Caches/ms-playwright"
    return Path.home() / ".cache/ms-playwright"


def http_probe(url: str, timeout: float):
    t0 = time.time()
    ctx = ssl.create_default_context()
    if os.environ.get("UAT_INSECURE_TLS") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "uat-test-only/probe"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return {"reachable": True, "status": r.status, "ms": int((time.time() - t0) * 1000), "error": ""}
    except urllib.error.HTTPError as e:  # máy chủ TRẢ LỜI — tới được
        return {"reachable": True, "status": e.code, "ms": int((time.time() - t0) * 1000), "error": ""}
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        return {"reachable": False, "status": None, "ms": int((time.time() - t0) * 1000),
                "error": str(getattr(e, "reason", e))}


def resolve_all(host: str):
    fams = set()
    try:
        for fam, *_ in socket.getaddrinfo(host, None):
            fams.add("IPv6" if fam == socket.AF_INET6 else "IPv4")
    except socket.gaierror:
        pass
    return sorted(fams)


def main():
    ap = argparse.ArgumentParser(description="G0 — kiểm môi trường trước khi chạy UAT")
    ap.add_argument("--url", default="", help="URL app (web/api). Bỏ trống nếu chỉ có ca cli.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--need", action="append", default=[],
                    help="browser | node | android | ios | maestro | bash (lặp được)")
    ap.add_argument("--timeout", type=float, default=15)
    a = ap.parse_args()

    checks, problems = {}, []
    http = {}
    if a.url:
        u = urllib.parse.urlparse(a.url)
        if u.scheme not in ("http", "https") or not u.hostname:
            problems.append(f"URL không hợp lệ: {a.url}")
        else:
            http = http_probe(a.url, a.timeout)
            http["url"] = a.url
            http["families"] = resolve_all(u.hostname)
            checks["app"] = http["reachable"]
            if not http["reachable"]:
                problems.append(f"app không tới được ở {a.url}: {http['error']} "
                                f"(đã thử {', '.join(http['families']) or 'không phân giải được tên'})")
            elif http["status"] and http["status"] >= 500:
                http["note"] = "máy chủ trả 5xx ở trang gốc — ghi nhận là PHÁT HIỆN sản phẩm, không phải lỗi môi trường"
    for need in a.need:
        if need == "node":
            ok = bool(shutil.which("node")) and bool(shutil.which("npm") or shutil.which("npm.cmd"))
            checks["node"] = ok
            if not ok:
                problems.append("thiếu node/npm")
        elif need == "browser":
            d = browsers_dir()
            found = sorted(p.name for p in d.glob("chromium*")) if d.is_dir() else []
            checks["browser"] = bool(found)
            checks["browser_dir"] = str(d)
            if not found:
                # Không phải lỗi chặn: bước cài trong thư mục kết quả sẽ tải Chromium về đúng chỗ.
                checks["browser_note"] = "chưa có Chromium — `npx playwright install chromium` trong <OUT> sẽ tải"
        elif need == "android":
            adb = shutil.which("adb")
            devs = []
            if adb:
                r = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=20)
                devs = [l.split()[0] for l in r.stdout.splitlines()[1:] if l.strip().endswith("device")]
            checks["android_devices"] = devs
            if not devs:
                problems.append("không có thiết bị/emulator Android (adb devices rỗng) — ca android sẽ KHÔNG CHẠY")
        elif need == "ios":
            ok = platform.system() == "Darwin" and bool(shutil.which("xcrun"))
            checks["ios"] = ok
            if not ok:
                problems.append("iOS cần macOS + Xcode — ca ios sẽ KHÔNG CHẠY")
        elif need == "maestro":
            ok = bool(shutil.which("maestro"))
            checks["maestro"] = ok
            if not ok:
                problems.append("thiếu Maestro CLI — ca mobile sẽ KHÔNG CHẠY")
        elif need == "bash":
            ok = bool(shutil.which("bash"))
            checks["bash"] = ok
            if not ok:
                problems.append("thiếu bash — ca cli sẽ KHÔNG CHẠY")
    # G0 chặn toàn cục CHỈ khi app web/api không tới được, hoặc thiếu node cho lớp Playwright.
    blocking = [p for p in problems if p.startswith(("app không tới", "URL không hợp lệ", "thiếu node"))]
    doc = {"ok": not blocking, "blocking": blocking, "problems": problems, "checks": checks, "http": http,
           "host_os": platform.system()}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "probe.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if http:
        print(f"probe: {a.url} → {'HTTP ' + str(http['status']) if http['reachable'] else 'KHÔNG TỚI ĐƯỢC'} "
              f"({http['ms']} ms, {', '.join(http.get('families') or [])})")
    for p in problems:
        print(("  ✗ " if p in blocking else "  ! ") + p)
    print("probe: G0 " + ("ĐẠT" if doc["ok"] else "HỎNG → NO-RUN"))
    return 0 if doc["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())
