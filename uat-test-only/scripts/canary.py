#!/usr/bin/env python3
"""canary.py — CHỨNG ÂM: chứng minh bộ đo của lượt này CÓ THỂ đỏ.

Bài toán: một lượt UAT toàn màu xanh có hai cách giải thích — sản phẩm đúng, hoặc thước
hỏng. Cả hai trông giống hệt nhau trong báo cáo. Kịch bản không được gán vào project nào,
reporter ghi nhầm tệp, baseURL trỏ sang chỗ khác, --grep nuốt mất spec: mọi lỗi ấy đều cho
ra "0 test thất bại".

Cách phân biệt duy nhất là bơm lỗi. Không được bơm vào sản phẩm (luật 1), nên bơm vào
CHÍNH THƯỚC ĐO: ba mệnh đề chắc chắn sai, chạy cùng bộ, cùng cấu hình, cùng reporter.

  gen    --out <OUT> --url <URL>   Sinh <OUT>/tests/_canary.spec.ts + <OUT>/canary.expect.json
  verify --out <OUT> --pw <tệp JSON reporter>   Cả ba PHẢI đỏ; xanh một mệnh đề = thước hỏng

Ba mệnh đề chọn sao cho KHÔNG phụ thuộc hành vi sản phẩm:
  1. tiêu đề trang phải bằng một nonce ngẫu nhiên 32 ký tự — không app nào có tiêu đề ấy;
  2. một request bất kỳ phải trả mã 599 — không máy chủ nào trả mã ấy;
  3. một testid ngẫu nhiên phải hiện ra — không DOM nào có phần tử ấy.
Cố ý KHÔNG dùng "đường dẫn lạ phải trả 404": SPA trả 200 cho mọi đường dẫn, mệnh đề ấy sẽ
xanh ở một sản phẩm hoàn toàn bình thường và ta sẽ báo động nhầm.

Thoát: 0 = ổn · 1 = thước hỏng (báo cáo VÔ HIỆU) · 2 = thiếu đầu vào.
"""
import argparse
import json
import secrets
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

CANARY_IDS = ["CANARY-TITLE", "CANARY-HTTP", "CANARY-DOM"]

SPEC = '''// _canary.spec.ts — CHỨNG ÂM của lượt chạy. SINH TỰ ĐỘNG, KHÔNG sửa tay.
//
// Ba mệnh đề dưới đây PHẢI đỏ. Nếu một mệnh đề xanh thì thước đo của lượt này hỏng và
// canary.py đánh cả báo cáo là VÔ HIỆU — vì khi ấy màu xanh của các ca thật không còn
// chứng minh được điều gì.
//
// Các ca này KHÔNG mang tag @TC- nào, chạy ở project riêng "canary", nên không vào mẫu số
// và không bị lượt chạy lại --grep đụng tới.
import { test, expect } from '@playwright/test';

const NONCE = '__NONCE__';

test('CANARY-TITLE tieu de trang khong the bang nonce', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(NONCE, { timeout: 3000 });
});

test('CANARY-HTTP khong may chu nao tra ma 599', async ({ request }) => {
  const r = await request.get('/');
  expect(r.status()).toBe(599);
});

test('CANARY-DOM testid ngau nhien khong the ton tai', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId(NONCE)).toBeVisible({ timeout: 3000 });
});
'''


def cmd_gen(a):
    out = Path(a.out)
    nonce = a.nonce or secrets.token_hex(16)
    (out / "tests").mkdir(parents=True, exist_ok=True)
    spec = out / "tests" / "_canary.spec.ts"
    spec.write_text(SPEC.replace("__NONCE__", nonce), encoding="utf-8")
    (out / "canary.expect.json").write_text(json.dumps(
        {"nonce": nonce, "ids": CANARY_IDS, "must_fail": True}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"canary: sinh {spec.as_posix()} · {len(CANARY_IDS)} mệnh đề phải đỏ · nonce "
          f"{nonce[:8]}…")
    return 0


def collect(doc):
    """Gom kết quả các test thuộc project 'canary' → {id: trạng thái lần chạy đầu}."""
    found = {}

    def walk(suite):
        for spec in suite.get("specs") or []:
            title = spec.get("title") or ""
            for t in spec.get("tests") or []:
                if (t.get("projectName") or "") != "canary":
                    continue
                res = (t.get("results") or [{}])[0]
                for cid in CANARY_IDS:
                    if title.startswith(cid):
                        found[cid] = res.get("status") or "khong-chay"
        for sub in suite.get("suites") or []:
            walk(sub)

    for s in doc.get("suites") or []:
        walk(s)
    return found


def cmd_verify(a):
    out = Path(a.out)
    rep = {"ok": False, "found": {}, "green": [], "missing": [], "reason": ""}
    try:
        doc = json.loads(Path(a.pw).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        rep["reason"] = f"không đọc được kết quả Playwright ({a.pw}): {e}"
        (out / "canary.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
        print("canary: " + rep["reason"], file=sys.stderr)
        return 1

    found = collect(doc)
    rep["found"] = found
    rep["missing"] = [c for c in CANARY_IDS if c not in found]
    # "passed" = mệnh đề chắc chắn sai lại xanh → thước hỏng. "skipped" cũng không chấp nhận:
    # một chứng âm bị bỏ qua thì không chứng minh được gì.
    rep["green"] = [c for c, st in found.items() if st != "failed"]
    if rep["missing"]:
        rep["reason"] = ("không tìm thấy chứng âm trong kết quả: " + ", ".join(rep["missing"]) +
                         " — project 'canary' chưa chạy, hoặc reporter ghi sang tệp khác")
    elif rep["green"]:
        rep["reason"] = ("mệnh đề chắc chắn sai lại KHÔNG đỏ: " +
                         ", ".join(f"{c}={found[c]}" for c in rep["green"]) +
                         " — thước đo của lượt này hỏng, màu xanh của các ca thật vô nghĩa")
    else:
        rep["ok"] = True
    (out / "canary.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    if rep["ok"]:
        print(f"canary: đạt — cả {len(CANARY_IDS)} mệnh đề chứng âm đều đỏ, bộ đo có thể bắt lỗi")
        return 0
    print("canary: HỎNG — " + rep["reason"])
    return 1


def main():
    ap = argparse.ArgumentParser(description="Chứng âm: chứng minh bộ đo của lượt này có thể đỏ")
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gen")
    g.add_argument("--out", required=True)
    g.add_argument("--nonce", default="", help="chỉ dùng khi tự kiểm; mặc định sinh ngẫu nhiên")
    v = sp.add_parser("verify")
    v.add_argument("--out", required=True)
    v.add_argument("--pw", required=True)
    a = ap.parse_args()
    return cmd_gen(a) if a.cmd == "gen" else cmd_verify(a)


if __name__ == "__main__":
    sys.exit(main())
