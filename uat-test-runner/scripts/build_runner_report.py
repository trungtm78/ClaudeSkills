#!/usr/bin/env python3
"""build_runner_report.py — TÍNH 8 cổng G0–G7 và verdict từ hiện vật. LLM không tự kể.

Trước tệp này, runner có 14 script và KHÔNG script nào in ra NO-GO / CONDITIONAL GO /
NO-RUN: bảng cổng chỉ nằm trong SKILL.md dạng văn xuôi, LLM đọc rồi tự điền. Một quyết
định phát hành do người kể lại thì không kiểm chứng được, và không so được giữa hai lượt.

Đầu vào (đều đã có sẵn, chưa ai gộp):
  --results  results_flat.json      từ flatten_pw_results.py
  --uat      uat.json               danh mục KẾ HOẠCH (mẫu số thật)
  --url      url.json               từ resolve_url.py (G0)
  --baseline <results_flat.json>    lượt XANH do NGƯỜI chỉ định (G5) — không bao giờ tự chọn
  --heal     heal_log.json          từ heal_log.py (xem R3)
  --s2-budget N                     ngưỡng S2 do NGƯỜI đặt (G4); thiếu = CẦN NGƯỜI
  --a11y / --perf                   hiện vật phi chức năng (G6)
  --signoff  <tệp>                  hồ sơ ký duyệt (G7)

HAI TRỤC, không phải một thang — giống uat-test-only:
    verdict = min( thang bậc theo cổng HỎNG , TRẦN theo cổng KHÔNG ĐO ĐƯỢC )
    thang: NO-RUN > NO-GO > CONDITIONAL GO > GO
`CONDITIONAL GO` ở bản cũ là một chỗ mờ: nó vừa nghĩa "đạt nhưng có nợ đã biết", vừa nghĩa
"chưa đo được". Nay tách hẳn — nợ đã biết thì liệt kê, chưa đo được thì HẠ TRẦN và in
`KHUYẾT PHÉP ĐO:`. Không đo được không bao giờ bằng đạt.
"""
import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

COVERAGE_MIN = 95.0
LADDER = ["GO", "CONDITIONAL GO", "NO-GO", "NO-RUN"]   # càng sau càng nặng


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return default


def crit(tc):
    """Ca đường găng: P0, hoặc severity S1/S2."""
    return (str(tc.get("priority") or "").upper() == "P0"
            or str(tc.get("severity_if_fail") or "").upper() in ("S1", "S2"))


def main():
    ap = argparse.ArgumentParser(description="Tính 8 cổng G0-G7 và verdict của uat-test-runner")
    ap.add_argument("--results", required=True)
    ap.add_argument("--uat", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--baseline", default="")
    ap.add_argument("--heal", default="")
    ap.add_argument("--s2-budget", default="", help="ngưỡng S2 do NGƯỜI đặt; thiếu = CẦN NGƯỜI")
    ap.add_argument("--a11y", default="")
    ap.add_argument("--perf", default="")
    ap.add_argument("--signoff", default="")
    ap.add_argument("-o", "--out", default="test-results/UAT")
    a = ap.parse_args()

    res = jload(a.results)
    if res is None:
        print(f"❌ không đọc được {a.results}", file=sys.stderr)
        return 2
    tests = {t["tc_id"]: t for t in res.get("tests", []) if t.get("tc_id")}
    summary = res.get("summary", {})
    planned = {t["tc_id"]: t for t in (jload(a.uat, {}) or {}).get("test_cases", [])
               if isinstance(t, dict) and t.get("tc_id")}
    url = jload(a.url, {}) or {}
    heal = jload(a.heal, {}) or {}
    heal_n = len(heal.get("entries", [])) if isinstance(heal, dict) else 0

    gates, nogo, degraded, debts = [], [], [], []

    def gate(code, name, state, detail, effect=""):
        gates.append({"gate": code, "name": name, "state": state, "detail": detail,
                      "effect": effect})
        if effect == "HẠ TRẦN":
            degraded.append(code)
        elif effect == "NO-GO":
            nogo.append(code)
        elif effect == "NỢ":
            debts.append(f"{code} {name}: {detail[:120]}")

    # G0 — môi trường
    if not a.url:
        gate("G0", "Entry", "KHÔNG ĐO ĐƯỢC", "không có url.json (resolve_url.py)", "HẠ TRẦN")
        g0 = True
    elif not url.get("app_running"):
        gate("G0", "Entry", "HỎNG",
             f"app tại {url.get('url', '?')} không phản hồi — không kiểm được thì không "
             f"kết luận được", "NO-RUN")
        g0 = False
    else:
        gate("G0", "Entry", "ĐẠT", f"{url.get('url')} phản hồi · nguồn {url.get('source', '?')}")
        g0 = True

    # G1 — API smoke (NGHĨA RIÊNG của runner; uat-test-only dùng G1 cho việc khác)
    api = (summary.get("by_layer") or {}).get("api")
    if not api or not api.get("total"):
        gate("G1", "API smoke", "KHÔNG ÁP", "bộ ca không có lớp api")
    elif api.get("failed") or api.get("skipped"):
        gate("G1", "API smoke", "HỎNG",
             f"{api.get('failed', 0)} fail / {api.get('skipped', 0)} skip trên "
             f"{api['total']} ca api", "NO-GO")
    else:
        gate("G1", "API smoke", "ĐẠT", f"{api['passed']}/{api['total']} ca api đạt")

    # G2 — đường găng: P0/S1-S2 phải đạt NGAY LẦN ĐẦU (chập chờn không phải đạt)
    crits = [i for i, t in planned.items() if crit(t)] if planned else list(tests)
    bad = []
    for i in crits:
        t = tests.get(i)
        if t is None:
            bad.append(f"{i}(không chạy)")
        elif t.get("status") != "passed":
            bad.append(f"{i}({t.get('status')})")
        elif t.get("pass_on_retry"):
            bad.append(f"{i}(chập chờn)")
    if not crits:
        gate("G2", "Critical path", "KHÔNG ÁP", "không xác định được ca P0/S1-S2")
    elif bad:
        gate("G2", "Critical path", "HỎNG",
             f"{len(bad)}/{len(crits)} ca đường găng không đạt: {', '.join(bad[:10])}", "NO-GO")
    else:
        gate("G2", "Critical path", "ĐẠT", f"{len(crits)}/{len(crits)} ca P0/S1-S2 đạt lần đầu")

    # G3 — độ phủ: mẫu số là KẾ HOẠCH, không phải "những gì đã chạy"
    total_planned = len(planned) or summary.get("total", 0)
    executed = sum(1 for t in tests.values() if t.get("status") in ("passed", "failed"))
    cov = (100.0 * executed / total_planned) if total_planned else 0.0
    if not total_planned:
        gate("G3", "Coverage", "KHÔNG ĐO ĐƯỢC", "không biết tổng ca kế hoạch (thiếu --uat)",
             "HẠ TRẦN")
    elif cov < COVERAGE_MIN:
        gate("G3", "Coverage", "HỎNG",
             f"{executed}/{total_planned} = {cov:.1f}% < {COVERAGE_MIN:.0f}%", "NO-GO")
    else:
        gate("G3", "Coverage", "ĐẠT", f"{executed}/{total_planned} = {cov:.1f}%")

    # G4 — ngân sách lỗi: ngưỡng S2 là THOẢ THUẬN của người, không suy ra được từ hiện vật
    s1_open = [i for i, t in tests.items()
               if t.get("status") == "failed"
               and str((planned.get(i) or {}).get("severity_if_fail", "")).upper() == "S1"]
    s2_open = [i for i, t in tests.items()
               if t.get("status") == "failed"
               and str((planned.get(i) or {}).get("severity_if_fail", "")).upper() == "S2"]
    if s1_open:
        gate("G4", "Defect budget", "HỎNG", f"{len(s1_open)} lỗi S1 còn mở: "
             f"{', '.join(s1_open[:8])} — S1 không có ngân sách", "NO-GO")
    elif a.s2_budget == "":
        gate("G4", "Defect budget", "CẦN NGƯỜI",
             f"{len(s2_open)} lỗi S2 mở, nhưng ngưỡng S2 chưa do người đặt (--s2-budget) — "
             f"không bịa ngưỡng rồi tuyên bố đạt", "HẠ TRẦN")
    elif len(s2_open) > int(a.s2_budget):
        gate("G4", "Defect budget", "HỎNG",
             f"{len(s2_open)} lỗi S2 > ngưỡng {a.s2_budget}", "NO-GO")
    elif s2_open:
        gate("G4", "Defect budget", "CÓ NỢ",
             f"{len(s2_open)}/{a.s2_budget} lỗi S2 trong ngân sách: {', '.join(s2_open[:8])}",
             "NỢ")
    else:
        gate("G4", "Defect budget", "ĐẠT", "0 lỗi S1/S2 mở")

    # G5 — hồi quy. Chưa từng có lượt xanh thì đây là cổng KHÔNG ÁP, không phải rủi ro chưa đo.
    if not a.baseline:
        gate("G5", "Regression", "KHÔNG ÁP",
             "không có baseline do người chỉ định (kỹ năng không bao giờ tự chọn baseline)")
    else:
        base = jload(a.baseline, {}) or {}
        was = {t["tc_id"]: t.get("status") for t in base.get("tests", []) if t.get("tc_id")}
        reg = [i for i, t in tests.items()
               if was.get(i) == "passed" and t.get("status") == "failed"]
        if reg:
            gate("G5", "Regression", "HỎNG",
                 f"{len(reg)} ca từng đạt nay hỏng: {', '.join(reg[:10])}", "NO-GO")
        else:
            gate("G5", "Regression", "ĐẠT", f"0 hồi quy so với {a.baseline}")

    # G6 — phi chức năng
    a11y = jload(a.a11y) if a.a11y else None
    perf = jload(a.perf) if a.perf else None
    wants_perf = any(str(t.get("type", "")).upper() == "PERFORMANCE" for t in planned.values())
    if a11y is None and perf is None:
        gate("G6", "Non-functional", "KHÔNG ĐO ĐƯỢC",
             "chưa có hiện vật a11y/perf (--a11y/--perf)", "HẠ TRẦN")
    else:
        bad6 = []
        if isinstance(a11y, dict):
            blk = a11y.get("blocking") or [v for v in (a11y.get("violations") or [])
                                           if v.get("impact") in ("critical", "serious")]
            if blk:
                bad6.append(f"{len(blk)} vi phạm a11y critical/serious")
        if wants_perf and perf is None:
            bad6.append("có ca PERFORMANCE nhưng không có hiện vật perf")
        if isinstance(perf, dict):
            over = [c for c in (perf.get("checks") or []) if c.get("status") == "FAIL"]
            if over:
                bad6.append(f"{len(over)} ca vượt ngân sách hiệu năng")
        if bad6:
            gate("G6", "Non-functional", "HỎNG", " · ".join(bad6), "NO-GO")
        else:
            gate("G6", "Non-functional", "ĐẠT", "a11y/perf trong ngưỡng")

    # G7 — hồ sơ ký duyệt: AI không bao giờ tự ký
    if not a.signoff or not Path(a.signoff).is_file():
        gate("G7", "Sign-off record", "CẦN NGƯỜI",
             "chưa có hồ sơ ký duyệt (người duyệt + bằng chứng + thời điểm)", "HẠ TRẦN")
    else:
        gate("G7", "Sign-off record", "ĐẠT", f"hồ sơ: {a.signoff}")

    # ── Kết luận: hai trục ──
    if not g0:
        verdict = "NO-RUN"
    elif nogo:
        verdict = "NO-GO"
    elif debts:
        verdict = "CONDITIONAL GO"
    else:
        verdict = "GO"

    # Heal: runner ĐƯỢC sửa, nhưng thước đã bị chỉnh giữa lúc đo thì không thể là GO trần.
    if heal_n and verdict == "GO":
        verdict = "CONDITIONAL GO"
        debts.append(f"đã heal {heal_n} lần trong lượt này — xem heal_log.json")

    ceiling = ""
    if degraded and verdict in ("GO", "CONDITIONAL GO"):
        ceiling = "KÈM KHUYẾT"

    flaky = summary.get("flaky_pass_on_retry", 0)
    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    full = f"{verdict} {ceiling}".strip()
    lines = [
        "## Kết quả UAT (uat-test-runner)",
        f"VERDICT: {full}",
        f"TỔNG: {summary.get('total', 0)} | ĐẠT: {summary.get('passed', 0)} | "
        f"HỎNG: {summary.get('failed', 0)} | BỎ QUA: {summary.get('skipped', 0)} | "
        f"CHẬP CHỜN: {flaky} | HEAL: {heal_n}",
    ]
    failed_ids = [i for i, t in tests.items() if t.get("status") == "failed"]
    flaky_ids = [i for i, t in tests.items() if t.get("pass_on_retry")]
    if failed_ids:
        # Đếm thôi là chưa đủ: người đọc báo cáo phải biết CA NÀO hỏng mà không phải mở
        # thêm tệp. Ca P2/P3 hỏng không chặn kết luận, nhưng vẫn phải hiện ra.
        lines.append(f"HỎNG: {', '.join(failed_ids[:20])}"
                     + (f" … và {len(failed_ids) - 20} ca khác" if len(failed_ids) > 20 else ""))
    if flaky_ids:
        lines.append(f"CHẬP CHỜN (đạt nhờ chạy lại — KHÔNG tính là đạt): "
                     f"{', '.join(flaky_ids[:20])}")
    if debts:
        lines.append("NỢ ĐÃ BIẾT: " + " · ".join(debts[:6]))
    if degraded:
        lines.append("KHUYẾT PHÉP ĐO: " + ", ".join(
            f"{g['gate']} ({g['name']})" for g in gates if g["gate"] in degraded)
            + " — không đo được nên KHÔNG được coi là đạt; cần người xác nhận.")
    lines.append("CỔNG: " + " · ".join(f"{g['gate']}={g['state']}" for g in gates))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "runner-verdict.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "runner-verdict.json").write_text(json.dumps(
        {"verdict": verdict, "ceiling": ceiling, "verdict_full": full, "gates": gates,
         "debts": debts, "degraded": degraded, "heal_count": heal_n,
         "summary": summary, "generated_at": now}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    md = [f"# Báo cáo UAT — uat-test-runner", "", f"Chạy lúc {now}", "", "```",
          *lines[1:], "```", "", "| Cổng | Tên | Trạng thái | Chi tiết | Hệ quả |",
          "|---|---|---|---|---|"]
    for g in gates:
        md.append(f"| {g['gate']} | {g['name']} | {g['state']} | "
                  f"{g['detail'].replace('|', '/')} | {g['effect']} |")
    md += ["", "> G1 ở đây là **API smoke**, khác nghĩa G1 của `uat-test-only` "
           "(\"mọi lớp có ca đều chạy được\") — xem handoff-schema §7.",
           "> Kết quả của `uat-test-runner` **không dùng để ký nghiệm thu**: skill này được "
           "phép sửa mã. Muốn ký thì chạy `uat-test-only` trên một lượt mới."]
    (out / "runner-report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"build_runner_report: {out.as_posix()}/runner-report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
