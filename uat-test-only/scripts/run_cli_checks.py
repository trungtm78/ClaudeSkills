#!/usr/bin/env python3
"""run_cli_checks.py — chạy các kiểm tra dòng lệnh đã ĐÓNG BĂNG và chấm bằng máy.

Ca kiểm của harness phần lớn là lệnh (`pnpm install`, `verify-gate.sh`…). Runner cũ không có
đường cho loại này nên phiên tự chạy tay rồi KỂ kết quả. Ở đây phép kiểm là dữ liệu:

<OUT>/tests/cli/checks.json
  { "checks": [ {
      "tc_id": "TC-G01", "name": "cài phụ thuộc sạch",
      "cmd": "pnpm install --frozen-lockfile",      # chạy bằng bash, cwd = --cwd (repo)
      "timeout_s": 600,
      "expect": {
         "exit_code": 0,                            # hoặc [0,1]
         "stdout_contains": ["Done"], "stdout_not_contains": [],
         "stderr_not_contains": ["ERR!"],
         "stdout_regex": [], "output_regex": []     # output = stdout+stderr
      } } ] }

Mỗi "expect" phải truy được về "Kết quả mong đợi" của ca — không được viết từ kết quả chạy thử.
Kết quả: <out> = { checks:[{tc_id,name,status,reasons,exit_code,duration_ms,log}] }
Thoát 0 luôn khi đã chạy (FAIL là kết quả, không phải lỗi); 2 nếu checks.json hỏng.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def find_bash():
    for c in ("bash", r"C:\Program Files\Git\bin\bash.exe", "/usr/bin/bash", "/bin/bash"):
        p = shutil.which(c) or (c if Path(c).is_file() else None)
        if p:
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checks", required=True)
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--out", required=True)
    ap.add_argument("--logs", default="")
    ap.add_argument("--only", default="", help="danh sách tc_id, phân tách bằng dấu phẩy (lượt chạy lại)")
    a = ap.parse_args()
    try:
        doc = json.loads(Path(a.checks).read_text(encoding="utf-8-sig"))
        checks = doc["checks"]
        assert isinstance(checks, list)
    except (OSError, ValueError, KeyError, AssertionError) as e:
        print(f"run_cli_checks: checks.json hỏng: {e}", file=sys.stderr)
        return 2
    bash = find_bash()
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    logs = Path(a.logs or (Path(a.out).parent / "cli-logs"))
    logs.mkdir(parents=True, exist_ok=True)
    out = []
    for c in checks:
        tc = str(c.get("tc_id") or "").strip()
        if only and tc not in only:
            continue
        exp = c.get("expect") or {}
        rec = {"tc_id": tc, "name": c.get("name") or tc, "status": "PASS", "reasons": [],
               "exit_code": None, "duration_ms": 0, "log": ""}
        if not bash:
            rec.update(status="KHONG_CHAY", reason="khong-co-bash", reasons=["không tìm thấy bash"])
            out.append(rec)
            continue
        if not exp:
            rec.update(status="FAIL", reasons=["phép kiểm không có 'expect' — không có oracle thì không chấm được"])
            out.append(rec)
            continue
        t0 = time.time()
        try:
            r = subprocess.run([bash, "-lc", c["cmd"]], cwd=a.cwd, capture_output=True,
                               timeout=int(c.get("timeout_s") or 300))
            so = r.stdout.decode("utf-8", "replace")
            se = r.stderr.decode("utf-8", "replace")
            rc = r.returncode
        except subprocess.TimeoutExpired as e:
            so = (e.stdout or b"").decode("utf-8", "replace")
            se = (e.stderr or b"").decode("utf-8", "replace")
            rc = None
            rec["reasons"].append(f"quá thời gian {c.get('timeout_s') or 300}s")
        except (OSError, KeyError) as e:
            so, se, rc = "", str(e), None
            rec["reasons"].append(f"không chạy được lệnh: {e}")
        rec["duration_ms"] = int((time.time() - t0) * 1000)
        rec["exit_code"] = rc
        lp = logs / f"{re.sub(r'[^A-Za-z0-9._-]', '_', tc)}.log"
        lp.write_text(f"$ {c.get('cmd')}\n# exit={rc}\n--- stdout ---\n{so}\n--- stderr ---\n{se}\n", encoding="utf-8")
        rec["log"] = str(lp)
        want = exp.get("exit_code", 0)
        wants = want if isinstance(want, list) else [want]
        if rc not in wants:
            rec["reasons"].append(f"mã thoát {rc}, mong đợi {want}")
        both = so + "\n" + se
        for s in exp.get("stdout_contains") or []:
            if s not in so:
                rec["reasons"].append(f"stdout thiếu «{s}»")
        for s in exp.get("stdout_not_contains") or []:
            if s in so:
                rec["reasons"].append(f"stdout có «{s}» (không được có)")
        for s in exp.get("stderr_not_contains") or []:
            if s in se:
                rec["reasons"].append(f"stderr có «{s}» (không được có)")
        for rx in exp.get("stdout_regex") or []:
            if not re.search(rx, so, re.M):
                rec["reasons"].append(f"stdout không khớp /{rx}/")
        for rx in exp.get("output_regex") or []:
            if not re.search(rx, both, re.M):
                rec["reasons"].append(f"đầu ra không khớp /{rx}/")
        if rec["reasons"]:
            rec["status"] = "FAIL"
        out.append(rec)
        print(f"  {'OK  ' if rec['status'] == 'PASS' else 'HỎNG'} {tc} ({rec['duration_ms']} ms)"
              + ("" if rec["status"] == "PASS" else " — " + "; ".join(rec["reasons"])[:160]))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"checks": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    n_fail = sum(1 for x in out if x["status"] != "PASS")
    print(f"run_cli_checks: {len(out)} phép kiểm · không đạt {n_fail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
