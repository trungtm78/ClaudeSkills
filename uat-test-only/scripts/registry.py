#!/usr/bin/env python3
"""registry.py — SỔ LỖI liên lượt: trí nhớ duy nhất của kỹ năng này.

Mỗi lượt UAT ở bản cũ là một hòn đảo: không biết ca này từng đỏ mấy lần, không biết nó
chập chờn hay hỏng thật, không biết lượt xanh gần nhất là lượt nào. Sổ lỗi vá đúng chỗ đó.

Nguyên tắc về test chập chờn — lý do sổ này KHÔNG bao giờ skip ca nào:
  Một chính sách chạy-lại biến mọi lỗi chập chờn thành ĐẠT, kể cả lỗi do đúng một tranh
  chấp thật trong sản phẩm. Cách ly (quarantine) ít nhất còn GHI LẠI rằng ca ấy không đáng
  tin; chạy lại thì không ghi gì cả. Ở đây: ca vượt ngưỡng chập chờn bị gắn nhãn KHÔNG
  ĐÁNG TIN trong báo cáo và bị loại khỏi cơ sở tính hồi quy — nhưng vẫn chạy, vẫn đỏ, vẫn
  vào FINDINGS.

  record  --out <OUT> --repo .   Ghi lượt này vào sổ, in tóm tắt lịch sử + tỷ lệ chập chờn
  suggest --repo .               In lượt XANH gần nhất để NGƯỜI cân nhắc làm baseline

Sổ nằm ở `uat/_registry/` (vùng ghi thứ hai, phải khai trong --allow của guard_repo).
Mẫu phát hiện theo tài liệu QA §13.1: Precondition · Action · Expected · Actual · Severity
· Evidence. CỐ Ý không có `Root cause` và không có `Fix` — luật 6 nguyên vẹn: kỹ năng này
tìm và ghi, người khác sửa.
"""
import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

FLAKE_LIMIT = 0.20   # > 20% số lượt đỏ là chập chờn → nhãn KHÔNG ĐÁNG TIN
KEEP_RUNS = 50       # mỗi ca giữ 50 lượt gần nhất; sổ là trí nhớ, không phải kho lưu trữ


def jload(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return d


def git_sha(repo):
    try:
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short=10", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def flake_rate(hist):
    """Tỷ lệ chập chờn = số lượt FAIL mà chạy lại lại xanh, trên tổng số lượt FAIL."""
    fails = [h for h in hist if h.get("status") == "FAIL"]
    if not fails:
        return 0.0, 0
    flaky = [h for h in fails if h.get("repro") == "1/2"]
    return len(flaky) / len(fails), len(fails)


def cmd_record(a):
    out, reg = Path(a.out), Path(a.registry)
    res = jload(out / "results.json")
    if res is None:
        print(f"registry: thiếu {out}/results.json — không ghi sổ", file=sys.stderr)
        return 2
    cases = {c["tc_id"]: c for c in (jload(out / "cases.json", {}) or {}).get("cases", [])}
    sha = git_sha(a.repo)
    run_id = a.run_id or out.name or _dt.datetime.now().strftime("run-%Y%m%d-%H%M%S")
    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    (reg / "tc").mkdir(parents=True, exist_ok=True)
    (reg / "findings").mkdir(parents=True, exist_ok=True)

    untrusted, findings = [], []
    for r in res.get("results", []):
        tc = r["tc_id"]
        f = reg / "tc" / f"{tc}.json"
        doc = jload(f, {"tc_id": tc, "runs": []}) or {"tc_id": tc, "runs": []}
        doc["runs"] = [x for x in doc["runs"] if x.get("run_id") != run_id]
        doc["runs"].append({"run_id": run_id, "at": now, "build": sha, "status": r["status"],
                            "reason": r.get("reason", ""), "repro": r.get("repro"),
                            "duration_ms": r.get("duration_ms", 0)})
        doc["runs"] = doc["runs"][-KEEP_RUNS:]
        rate, nfail = flake_rate(doc["runs"])
        doc["flake_rate"] = round(rate, 3)
        doc["fail_runs"] = nfail
        doc["untrusted"] = rate > FLAKE_LIMIT and nfail >= 3
        f.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        if doc["untrusted"]:
            untrusted.append(f"{tc} (chập chờn {rate:.0%} trên {nfail} lượt đỏ)")
        if r["status"] == "FAIL":
            c = cases.get(tc, {})
            # Mẫu defect tối thiểu. KHÔNG có root cause, KHÔNG có cách sửa.
            findings.append({
                "tc_id": tc, "run_id": run_id, "at": now, "build": sha,
                "priority": r.get("priority"), "severity": r.get("severity_if_fail"),
                "precondition": c.get("data_required") or c.get("steps", "")[:200],
                "action": c.get("steps", "")[:400],
                "expected": r.get("expected", ""),
                "actual": (r.get("error") or r.get("reason") or "")[:600],
                "evidence": r.get("evidence", []),
                "repro": r.get("repro"),
                "regression_hint": c.get("coverage_ids") or [],
            })
    (reg / "findings" / f"{run_id}.json").write_text(
        json.dumps({"run_id": run_id, "at": now, "build": sha, "findings": findings},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    counts = res.get("counts", {})
    idx = jload(reg / "runs.json", {"runs": []}) or {"runs": []}
    idx["runs"] = [x for x in idx["runs"] if x.get("run_id") != run_id]
    idx["runs"].append({"run_id": run_id, "at": now, "build": sha, "out": out.as_posix(),
                        "counts": counts,
                        "green": counts.get("FAIL", 1) == 0 and counts.get("KHONG_CHAY", 1) == 0})
    idx["runs"] = idx["runs"][-KEEP_RUNS:]
    (reg / "runs.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")

    (out / "registry.json").write_text(json.dumps(
        {"run_id": run_id, "registry": reg.as_posix(), "untrusted": untrusted,
         "findings": len(findings), "history_runs": len(idx["runs"]),
         "green_runs": [x["run_id"] for x in idx["runs"] if x["green"]]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"registry: ghi lượt {run_id} @ {sha} · {len(findings)} phát hiện · "
          f"{len(idx['runs'])} lượt trong sổ")
    for u in untrusted:
        print("  ! KHÔNG ĐÁNG TIN: " + u)
    return 0


def cmd_suggest(a):
    """In lượt XANH gần nhất. CỐ Ý chỉ gợi ý: kỹ năng không bao giờ tự chọn baseline."""
    idx = jload(Path(a.registry) / "runs.json", {"runs": []}) or {"runs": []}
    greens = [x for x in idx["runs"] if x.get("green")]
    if not greens:
        print("registry: sổ chưa có lượt XANH nào — chưa có gì để làm baseline")
        return 1
    g = greens[-1]
    print(f"registry: lượt XANH gần nhất là {g['run_id']} @ {g['build']} ({g['at']})")
    print(f"  người muốn dùng làm baseline thì thêm:  --baseline {g['out']}/results.json")
    print("  kỹ năng KHÔNG tự chọn baseline: chọn mốc so sánh là một quyết định, không phải "
          "một phép tính.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Sổ lỗi liên lượt: lịch sử, chập chờn, phát hiện")
    ap.add_argument("--registry", default="uat/_registry")
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("record")
    r.add_argument("--out", required=True)
    r.add_argument("--repo", default=".")
    r.add_argument("--run-id", default="")
    sp.add_parser("suggest")
    a = ap.parse_args()
    return cmd_record(a) if a.cmd == "record" else cmd_suggest(a)


if __name__ == "__main__":
    sys.exit(main())
