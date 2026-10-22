#!/usr/bin/env python3
"""resolve_credentials.py — tìm tài khoản kiểm thử THẬT. Không bao giờ bịa tài khoản.

Thứ tự (nguồn đầu tiên có ĐỦ user + mật khẩu thắng):
  1. biến môi trường  UAT_USER_<ROLE>/UAT_PASS_<ROLE>, rồi UAT_USER/UAT_PASS
  2. <cwd>/.env.test
  3. <cwd>/.env
  4. ~/.harness-env.<project>   (quy ước harness: biến riêng từng dự án trên mỗi máy)
  KHÔNG BAO GIỜ đọc .env.example / .env.sample — đó là giá trị giữ chỗ (bản runner để nó THẮNG .env.test).

Khoá nhận ra trong tệp: UAT_USER, UAT_PASS, UAT_PASSWORD, TEST_USER, TEST_EMAIL, TEST_PASSWORD,
E2E_USER, E2E_PASSWORD (và bản có hậu tố _<ROLE>).

Không tìm thấy → thoát 3, KHÔNG mock. Tài khoản giả biến lỗi đăng nhập thành "lỗi sản phẩm".
Kết quả ghi vào tệp NGOÀI repo (mặc định ~/.cache/uat-test-only/<khoá>/credentials.json, quyền
0600) để không bao giờ bị commit; stdout chỉ in user + nguồn, KHÔNG in mật khẩu.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

USER_KEYS = ["UAT_USER", "TEST_USER", "TEST_EMAIL", "E2E_USER", "UAT_EMAIL"]
PASS_KEYS = ["UAT_PASS", "UAT_PASSWORD", "TEST_PASSWORD", "E2E_PASSWORD"]


def parse_env(p: Path) -> dict:
    d = {}
    try:
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
            if not m:
                continue
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            else:
                v = re.sub(r"\s+#.*$", "", v)
            d[m.group(1)] = v
    except OSError:
        pass
    return d


def pick(d: dict, role: str):
    sfx = [f"_{role.upper()}"] if role else []
    for s in sfx + [""]:
        u = next((d[k + s] for k in USER_KEYS if d.get(k + s)), "")
        p = next((d[k + s] for k in PASS_KEYS if d.get(k + s)), "")
        if u and p:
            return u, p
    return "", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--project", default="")
    ap.add_argument("--role", default="")
    ap.add_argument("--run-key", default="", help="khoá thư mục cache (mặc định: băm của --out-dir)")
    ap.add_argument("--out", default="", help="đường tệp kết quả (mặc định ngoài repo)")
    a = ap.parse_args()

    sources = [("env", dict(os.environ))]
    cwd = Path(a.cwd)
    for name in (".env.test", ".env"):
        if (cwd / name).is_file():
            sources.append((str(cwd / name), parse_env(cwd / name)))
    if a.project:
        hp = Path.home() / f".harness-env.{a.project}"
        if hp.is_file():
            sources.append((str(hp), parse_env(hp)))
    user = pw = src = ""
    for name, d in sources:
        user, pw = pick(d, a.role)
        if user and pw:
            src = name
            break
    key = a.run_key or hashlib.sha256(str(cwd.resolve()).encode()).hexdigest()[:12]
    out = Path(a.out) if a.out else Path.home() / ".cache" / "uat-test-only" / key / "credentials.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = {"found": bool(user and pw), "user": user, "password": pw, "role": a.role, "source": src}
    out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(out, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    if not doc["found"]:
        tried = ", ".join(n for n, _ in sources)
        print(f"credentials: KHÔNG tìm thấy tài khoản{(' vai ' + a.role) if a.role else ''} (đã thử: {tried}). "
              "KHÔNG dùng tài khoản giả — các ca cần đăng nhập sẽ KHÔNG CHẠY.")
        print(f"credentials: tệp {out}")
        return 3
    print(f"credentials: {user} (nguồn {src}) → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
