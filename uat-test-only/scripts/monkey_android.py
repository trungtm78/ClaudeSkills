#!/usr/bin/env python3
"""monkey_android.py — monkey test Android bằng `adb shell monkey`, chỉ QUAN SÁT và GHI.

  python monkey_android.py --app-id com.vd.app --seed 42 --events 500 --out <OUT>/monkey
  python monkey_android.py --parse-only <tệp log monkey> --seed 42 --out <OUT>/monkey   (kiểm/đọc lại)

Oracle: "// CRASH:" → S1 · "// NOT RESPONDING:" (ANR) → S1 · khối FATAL EXCEPTION trong
`logcat -b crash` → S1. Rào: -p giới hạn trong app, --pct-syskeys 0 (không bấm Home/Back hệ thống),
--pct-appswitch 0. Tái hiện: cùng --seed + cùng --events ⇒ cùng chuỗi sự kiện.
Ghi <out>/android-<seed>.json cùng khuôn với monkey_web. Thoát 0 khi chạy xong; 4 khi không có
thiết bị (KHÔNG CHẠY — ghi rõ, không phải lỗi sản phẩm); 1 khi dùng sai.
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


def parse(text: str, crash_log: str = ""):
    anomalies = []
    for m in re.finditer(r"^// CRASH: (.*?)$(.*?)(?=^// (?:CRASH|NOT RESPONDING)|^:Monkey|\Z)", text, re.M | re.S):
        body = m.group(2)
        msg = next((l[3:].strip() for l in body.splitlines() if l.startswith("// Long Msg:")), "")
        anomalies.append({"type": "crash", "severity": "S1",
                          "message": f"{m.group(1).strip()} {msg}".strip()[:400], "count": 1})
    for m in re.finditer(r"^// NOT RESPONDING: (.*?)$", text, re.M):
        anomalies.append({"type": "anr", "severity": "S1", "message": m.group(1).strip()[:400], "count": 1})
    for m in re.finditer(r"FATAL EXCEPTION: ([^\n]*)\n(?:.*\n){0,3}?.*?([A-Za-z.]+(?:Exception|Error)[^\n]*)", crash_log):
        msg = f"FATAL {m.group(1).strip()}: {m.group(2).strip()}"[:400]
        if not any(msg[:80] in a["message"] for a in anomalies):
            anomalies.append({"type": "crash", "severity": "S1", "message": msg, "count": 1})
    inj = re.search(r"Events injected:\s*(\d+)", text)
    return anomalies, int(inj.group(1)) if inj else None, bool(re.search(r"// Monkey finished", text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-id", default="")
    ap.add_argument("--seed", type=int, default=int(time.time()) % 100000)
    ap.add_argument("--events", type=int, default=500)
    ap.add_argument("--throttle", type=int, default=150)
    ap.add_argument("--out", required=True)
    ap.add_argument("--parse-only", default="")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"android-{a.seed}.json"

    if a.parse_only:
        text = Path(a.parse_only).read_text(encoding="utf-8", errors="replace")
        anomalies, injected, finished = parse(text)
        doc = {"seed": a.seed, "app_id": a.app_id, "events_injected": injected, "finished": finished,
               "anomalies": anomalies, "blocking": len(anomalies), "source": "parse-only"}
        dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"monkey_android: đọc lại {a.parse_only} → bất thường {len(anomalies)}")
        return 0

    if not a.app_id:
        print("monkey_android: thiếu --app-id", file=sys.stderr)
        return 1
    adb = shutil.which("adb")
    devs = []
    if adb:
        r = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=20)
        devs = [l.split()[0] for l in r.stdout.splitlines()[1:] if l.strip().endswith("device")]
    if not devs:
        doc = {"seed": a.seed, "app_id": a.app_id, "not_run": True,
               "reason": "không có adb hoặc không có thiết bị/emulator", "anomalies": []}
        dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print("monkey_android: KHÔNG CHẠY — " + doc["reason"])
        return 4
    subprocess.run([adb, "logcat", "-b", "crash", "-c"], capture_output=True, timeout=20)
    cmd = [adb, "shell", "monkey", "-p", a.app_id, "-s", str(a.seed), "--throttle", str(a.throttle),
           "--pct-syskeys", "0", "--pct-appswitch", "0", "-v", "-v", str(a.events)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=max(120, a.events * a.throttle // 1000 * 3))
    crash = subprocess.run([adb, "logcat", "-d", "-b", "crash"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30).stdout
    (out / f"android-{a.seed}.log").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr + "\n--- crash buffer ---\n" + crash,
                                                encoding="utf-8")
    anomalies, injected, finished = parse(r.stdout, crash)
    doc = {"seed": a.seed, "app_id": a.app_id, "device": devs[0], "events_requested": a.events,
           "events_injected": injected, "finished": finished, "duration_s": int(time.time() - t0),
           "anomalies": anomalies, "blocking": len(anomalies),
           "replay": " ".join(cmd[1:]).replace(adb, "adb")}
    dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"monkey_android: seed {a.seed} · {injected} sự kiện · bất thường {len(anomalies)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
