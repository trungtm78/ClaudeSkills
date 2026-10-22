#!/usr/bin/env python3
"""run_perf.py — phần ĐO ĐƯỢC của hiệu năng: p50 / p95 / p99 so với ngân sách NGƯỜI đặt.

Tài liệu QA nói rõ vì sao không hỏi "trang có mở không": p50 cho biết trải nghiệm điển
hình, còn p95/p99 mới lộ ra một phần người dùng đang chậm. Một trung bình đẹp che được
đuôi phân phối xấu.

Luật cứng: **không có ngân sách do người đặt thì không đo**. Ca thiếu `perf_budget` trở
thành KHÔNG CHẠY và G17 hạ trần. Tự bịa một ngưỡng rồi tuyên bố đạt là tệ hơn không đo:
nó biến một câu hỏi chưa có lời đáp thành một lời khẳng định.

Ca khai:
  "perf_budget": { "url": "/api/v1/don", "method": "GET", "p95_ms": 800, "sample": 20,
                   "warmup": 3, "max_error_rate": 0.0 }

Đo ở tầng HTTP, không phải tầng trình duyệt: đây là độ trễ máy chủ. Chỉ số phía trình
duyệt (LCP, INP) thuộc G6 — CẦN NGƯỜI, vì ngân sách cho chúng là thoả thuận sản phẩm.

Đầu ra <OUT>/results/perf.json theo định dạng của run_cli_checks.py →
merge_results.py … --checks perf=<tệp>. Thoát: 0 đã ghi · 2 thiếu đầu vào.
"""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def pct(xs, q):
    """Phân vị kiểu "nearest-rank" — với mẫu nhỏ (20 lượt) nó trung thực hơn nội suy:
    p95 của 20 mẫu là mẫu chậm thứ nhì, chứ không phải một con số không ai từng gặp."""
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(1, min(len(s), int(-(-q * len(s) // 100))))
    return s[k - 1]


def one(url, method, headers, timeout):
    req = urlrequest.Request(url, method=method, headers=headers)
    t0 = time.perf_counter()
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            r.read()
            return (time.perf_counter() - t0) * 1000.0, r.status
    except urlerror.HTTPError as e:
        try:
            e.read()
        except Exception:  # noqa: BLE001
            pass
        return (time.perf_counter() - t0) * 1000.0, e.code
    except Exception:  # noqa: BLE001
        return (time.perf_counter() - t0) * 1000.0, 0


def main():
    ap = argparse.ArgumentParser(description="G17: hiệu năng p50/p95/p99 so ngân sách người đặt")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-url", default=os.environ.get("UAT_BASE_URL", ""))
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()
    try:
        cases = json.loads(Path(a.cases).read_text(encoding="utf-8-sig")).get("cases", [])
    except (OSError, ValueError) as e:
        print(f"run_perf: không đọc được {a.cases}: {e}", file=sys.stderr)
        return 2

    work = [c for c in cases if c.get("perf_budget") or c.get("type") == "PERFORMANCE"]
    outp = Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    if not work:
        outp.write_text(json.dumps({"checks": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("run_perf: không ca nào khai perf_budget — tầng hiệu năng không chạy")
        return 0

    checks = []
    for c in work:
        b = c.get("perf_budget") or {}
        tc = c["tc_id"]
        if not b.get("url") or not b.get("p95_ms"):
            checks.append({"tc_id": tc, "name": c.get("title", ""), "status": "KHONG_CHAY",
                           "reason": "thieu-ngan-sach",
                           "reasons": ["ca PERFORMANCE nhưng thiếu `perf_budget.url` hoặc "
                                       "`p95_ms` — không có ngân sách do người đặt thì không "
                                       "đo; bịa một ngưỡng rồi tuyên bố đạt còn tệ hơn"],
                           "duration_ms": 0})
            continue
        url = b["url"] if b["url"].startswith("http") else (a.base_url or "") + b["url"]
        method, n = (b.get("method") or "GET"), int(b.get("sample") or 20)
        headers = dict(b.get("headers") or {})
        t0 = time.time()
        for _ in range(int(b.get("warmup") or 3)):
            one(url, method, headers, a.timeout)   # làm nóng: không tính vào mẫu
        lat, codes = [], []
        for _ in range(n):
            ms, code = one(url, method, headers, a.timeout)
            lat.append(ms)
            codes.append(code)
        errs = [c2 for c2 in codes if c2 == 0 or c2 >= 500]
        rate = len(errs) / max(1, len(codes))
        p50, p95, p99 = pct(lat, 50), pct(lat, 95), pct(lat, 99)
        reasons = []
        if p95 > float(b["p95_ms"]):
            reasons.append(f"p95 = {p95:.0f} ms vượt ngân sách {b['p95_ms']} ms "
                           f"(p50 {p50:.0f} · p99 {p99:.0f} · {n} mẫu)")
        if rate > float(b.get("max_error_rate") or 0.0):
            reasons.append(f"tỷ lệ lỗi {rate:.0%} vượt ngưỡng "
                           f"{float(b.get('max_error_rate') or 0.0):.0%} (mã: {sorted(set(errs))})")
        checks.append({"tc_id": tc, "name": c.get("title", ""),
                       "status": "FAIL" if reasons else "PASS",
                       "reason": "vuot-ngan-sach" if reasons else "",
                       "reasons": reasons or [f"p50 {p50:.0f} · p95 {p95:.0f} · p99 {p99:.0f} ms "
                                              f"trong ngân sách {b['p95_ms']} ms ({n} mẫu)"],
                       "p50_ms": round(p50, 1), "p95_ms": round(p95, 1), "p99_ms": round(p99, 1),
                       "samples": n, "error_rate": round(rate, 4),
                       "duration_ms": int((time.time() - t0) * 1000)})

    outp.write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
    nf = sum(1 for x in checks if x["status"] == "FAIL")
    print(f"run_perf: {len(checks)} ca · FAIL {nf}")
    for x in checks:
        print(f"  {'x' if x['status'] != 'PASS' else '·'} {x['tc_id']}: {'; '.join(x['reasons'])[:160]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
