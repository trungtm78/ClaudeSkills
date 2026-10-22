#!/usr/bin/env python3
"""role_matrix.py — G14: ma trận quyền và IDOR. Đóng vai người KHÔNG được phép.

Tài liệu QA xếp nhóm này vào rủi ro CRITICAL và nói rõ: "không coi việc ẩn button ở UI là
security". Một ca chạy bằng vai ĐƯỢC phép chỉ chứng minh đường thuận đi được; nó không
chứng minh đường nghịch bị chặn. Phép đo thật là thử chéo: cùng tài nguyên ấy, token của
vai khác, và token rỗng.

Ca khai (type SECURITY hoặc PERMISSIONS):
  "access": {
    "url": "/api/v1/don/1", "method": "GET",
    "allow": ["ke-toan", "giam-doc"],        # vai ĐƯỢC phép — mọi vai khác phải bị chặn
    "deny_status": [401, 403],               # mặc định [401, 403]
    "must_not_contain": ["so_tien", "cccd"]  # thân phản hồi không được lộ định danh/nội dung
  }

Token lấy từ (không bao giờ tự chế tài khoản):
  * biến môi trường UAT_TOKEN_<ROLE> — vd UAT_TOKEN_KE_TOAN
  * tệp JSON {"<role>": "<token>"} trỏ bởi UAT_TOKEN_FILE, đặt NGOÀI repo
Dưới 2 vai → không dựng được ma trận → mọi ca thành KHÔNG CHẠY(thieu-vai) và G14 HẠ TRẦN.

Đầu ra <OUT>/results/idor.json theo định dạng của run_cli_checks.py → merge_results.py đọc
bằng --checks security=<tệp>.

Thoát: 0 = đã ghi · 2 = thiếu đầu vào · 4 = không đủ vai (mọi ca KHÔNG CHẠY).
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib import error as urlerror

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ANON = "(vô danh)"


def load_tokens():
    """{vai: token}. Chỉ lấy từ môi trường hoặc tệp NGOÀI repo — không bịa."""
    toks = {}
    fp = os.environ.get("UAT_TOKEN_FILE", "")
    if fp:
        try:
            d = json.loads(Path(fp).read_text(encoding="utf-8-sig"))
            toks.update({str(k): str(v) for k, v in d.items() if v})
        except (OSError, ValueError, AttributeError):
            pass
    for k, v in os.environ.items():
        if k.startswith("UAT_TOKEN_") and v and k != "UAT_TOKEN_FILE":
            toks[k[len("UAT_TOKEN_"):].lower().replace("_", "-")] = v
    return toks


def fetch(url, method, token, timeout=20):
    """Trả (mã, thân). Lỗi mạng cũng là dữ liệu: mã 0 kèm mô tả."""
    headers = {"Accept": "*/*"}
    if token:
        headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    req = urlrequest.Request(url, method=method or "GET", headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(65536).decode("utf-8", "replace")
    except urlerror.HTTPError as e:
        return e.code, (e.read(65536).decode("utf-8", "replace") if e.fp else "")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def norm_role(r):
    return re.sub(r"[^a-z0-9]+", "-", str(r or "").strip().lower()).strip("-")


def main():
    ap = argparse.ArgumentParser(description="G14: ma trận quyền và IDOR")
    ap.add_argument("--cases", required=True, help="<OUT>/cases.json")
    ap.add_argument("--out", required=True, help="vd <OUT>/results/idor.json")
    ap.add_argument("--base-url", default=os.environ.get("UAT_BASE_URL", ""))
    a = ap.parse_args()
    try:
        cases = json.loads(Path(a.cases).read_text(encoding="utf-8-sig")).get("cases", [])
    except (OSError, ValueError) as e:
        print(f"role_matrix: không đọc được {a.cases}: {e}", file=sys.stderr)
        return 2

    work = [c for c in cases if isinstance(c.get("access"), dict)]
    outp = Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    if not work:
        outp.write_text(json.dumps({"checks": [], "roles": []}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        print("role_matrix: không ca nào khai `access` — ma trận quyền không chạy")
        return 0

    tokens = load_tokens()
    checks = []
    if len(tokens) < 1:
        for c in work:
            checks.append({"tc_id": c["tc_id"], "name": c.get("title", ""),
                           "status": "KHONG_CHAY", "reason": "thieu-vai",
                           "reasons": ["không có token vai nào (đặt UAT_TOKEN_<ROLE> hoặc "
                                       "UAT_TOKEN_FILE) — tuyệt đối không tự chế tài khoản"],
                           "duration_ms": 0})
        outp.write_text(json.dumps({"checks": checks, "roles": []}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        print(f"role_matrix: KHÔNG CHẠY {len(work)} ca — không có token vai nào")
        return 4

    for c in work:
        t0 = time.time()
        spec = c["access"]
        allow = {norm_role(x) for x in (spec.get("allow") or [])}
        deny_ok = set(spec.get("deny_status") or [401, 403])
        secrets = [str(x) for x in (spec.get("must_not_contain") or [])]
        url = spec.get("url", "")
        url = url if url.startswith("http") else (a.base_url or "") + url
        method = spec.get("method") or "GET"

        # Ma trận: mọi vai KHÔNG nằm trong allow, cộng vai vô danh.
        probes = [(r, t) for r, t in tokens.items() if r not in allow] + [(ANON, "")]
        reasons, tried = [], []
        for role, tok in probes:
            code, body = fetch(url, method, tok)
            tried.append(f"{role}→{code}")
            if code == 0:
                reasons.append(f"vai {role}: không gọi được ({body[:80]})")
                continue
            if 200 <= code < 300:
                reasons.append(f"IDOR [S1] vai {role} KHÔNG được phép nhưng nhận {code} trên "
                               f"{method} {spec.get('url')} — kiểm soát truy cập ở máy chủ hỏng")
                continue
            if code not in deny_ok:
                reasons.append(f"vai {role}: mong đợi mã thuộc {sorted(deny_ok)}, thực tế {code}")
            lo = body.lower()
            leaked = [s for s in secrets if s.lower() in lo]
            if leaked:
                reasons.append(f"vai {role}: thân phản hồi lộ {leaked} dù đã chặn bằng mã {code}")
        if not allow:
            reasons.append("ca khai `access` nhưng không khai `allow` — không biết vai nào "
                           "được phép thì không dựng được ma trận")
        status = "FAIL" if reasons else "PASS"
        if not allow:
            status = "KHONG_CHAY"
        checks.append({"tc_id": c["tc_id"], "name": c.get("title", ""), "status": status,
                       "reason": {"FAIL": "quyen-sai", "KHONG_CHAY": "ca-khong-hop-le"}.get(status, ""),
                       "reasons": reasons or [f"mọi vai không được phép đều bị chặn ({', '.join(tried)})"],
                       "duration_ms": int((time.time() - t0) * 1000)})

    outp.write_text(json.dumps({"checks": checks, "roles": sorted(tokens)},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    n_fail = sum(1 for x in checks if x["status"] == "FAIL")
    print(f"role_matrix: {len(checks)} ca · FAIL {n_fail} · vai có token: {', '.join(sorted(tokens))}")
    for x in checks:
        if x["status"] != "PASS":
            print(f"  x {x['tc_id']}: {'; '.join(x['reasons'])[:220]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
