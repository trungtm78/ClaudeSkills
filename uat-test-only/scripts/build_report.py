#!/usr/bin/env python3
"""build_report.py — TÍNH cổng và kết luận từ hiện vật; LLM không được tự kể kết luận.

Đầu vào (trong <OUT>): cases.json · results.json · probe.json · guard/guard.json ·
                        monkey/*.json (tuỳ chọn) · --baseline <tệp results.json do NGƯỜI đặt> (tuỳ chọn)
Đầu ra: <OUT>/report.md · <OUT>/verdict.json · <OUT>/verdict.txt (khối dán vào task file)

Cổng:
  G0 Môi trường   probe.json ok                                  hỏng → NO-RUN
  G1 Lớp chạy     mọi lớp có ca kế hoạch đều chạy được            lỗi  → NO-GO
  G2 Đường găng   P0/P1: 100% PASS, 0 KHÔNG CHẠY                  hỏng → NO-GO
  G3 Độ phủ       (PASS+FAIL)/tổng ca kế hoạch ≥ 95%              hỏng → NO-GO
  G5 Hồi quy      chỉ khi NGƯỜI đưa baseline; không bao giờ ghi baseline   hỏng → NO-GO
  G8 Độ bền       monkey: 0 bất thường S1/S2                      hỏng → NO-GO
  G4 Ngân sách lỗi · G6 Phi chức năng · G7 Ký duyệt → CẦN NGƯỜI (không tính được từ hiện vật)
  Rào guard vi phạm → BÁO CÁO VÔ HIỆU (đè mọi thứ).

Kết luận: BÁO CÁO VÔ HIỆU > NO-RUN > NO-GO > GO-CHỜ-KÝ. AI không bao giờ ký.
Harness: VERDICT: PASS ⇔ GO-CHỜ-KÝ; còn lại FAIL.
"""
import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

COVERAGE_MIN = 95.0
LABEL = {"PASS": "ĐẠT", "FAIL": "KHÔNG ĐẠT", "KHONG_CHAY": "KHÔNG CHẠY"}


def jload(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def git_sha(repo: str) -> str:
    try:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "--short=10", "HEAD"], capture_output=True,
                           text=True, timeout=10)
        return r.stdout.strip() or "?"
    except (OSError, subprocess.SubprocessError):
        return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="thư mục kết quả của lượt chạy")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--baseline", default="", help="results.json của một lượt XANH do người chỉ định")
    ap.add_argument("--pw-version", default="")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    out = Path(a.out)

    cases = jload(out / "cases.json", {}) or {}
    results = jload(out / "results.json", None)
    probe = jload(out / "probe.json", None)
    guard = jload(out / "guard" / "guard.json", None)
    oracle = jload(out / "oracle_bind.json", None)
    canary = jload(out / "canary.json", None)
    evid = jload(out / "evidence.json", None)
    a11y = jload(out / "a11y.json", None)
    regi = jload(out / "registry.json", None)
    monkeys = []
    for mp in sorted((out / "monkey").glob("*.json")) if (out / "monkey").is_dir() else []:
        if mp.name.endswith(".actions.json"):
            continue
        d = jload(mp, None)
        if isinstance(d, dict) and "anomalies" in d:
            d["_file"] = str(mp)
            monkeys.append(d)

    gates = []
    degraded = []  # cổng CHẶN nhưng không đo được → hạ TRẦN kết luận

    def gate(code, name, state, detail, effect=""):
        gates.append({"gate": code, "name": name, "state": state, "detail": detail,
                      "effect": effect})
        if effect == "HẠ TRẦN":
            degraded.append(code)

    cases_by_id = {c["tc_id"]: c for c in cases.get("cases", [])}
    rows = (results or {}).get("results", [])
    counts = (results or {}).get("counts", {"total": 0, "PASS": 0, "FAIL": 0, "KHONG_CHAY": 0})
    layers = (results or {}).get("layers", {})

    # Hạ ca ĐẠT-nhưng-thiếu-bằng-chứng TRƯỚC khi tính cổng. Ở hồ sơ ci thì chỉ hạ trần
    # (cấu hình nhẹ, ca đạt vốn không sinh hiện vật) — xem check_evidence.py.
    ev_missing = {m["tc_id"]: m["need"] for m in (evid or {}).get("missing", [])}
    if ev_missing and not (evid or {}).get("degrade"):
        for r in rows:
            if r["tc_id"] in ev_missing and r["status"] == "PASS":
                r["status"] = "KHONG_CHAY"
                r["reason"] = "thieu-bang-chung"
                r["error"] = (f"ca báo ĐẠT nhưng thiếu hiện vật đã khai "
                              f"`{ev_missing[r['tc_id']]}` — không truy ngược được")
        counts = {"total": len(rows), "PASS": sum(1 for r in rows if r["status"] == "PASS"),
                  "FAIL": sum(1 for r in rows if r["status"] == "FAIL"),
                  "KHONG_CHAY": sum(1 for r in rows if r["status"] == "KHONG_CHAY")}

    # Rào
    invalid_report = False
    if guard is None:
        invalid_report = True
        guard_detail = "thiếu guard/guard.json — không chứng minh được lượt chạy không sửa sản phẩm"
    elif not guard.get("ok"):
        invalid_report = True
        guard_detail = "; ".join((guard.get("product_changes") or []) + (guard.get("test_changes") or []))[:600]
    else:
        guard_detail = "sạch" + (" (⚠ không phải repo git — không kiểm được)" if guard.get("mode") != "git" else "")

    # G0
    if probe is None:
        g0 = False
        gate("G0", "Môi trường", "HỎNG", "thiếu probe.json", "NO-RUN")
    else:
        g0 = bool(probe.get("ok"))
        h = probe.get("http") or {}
        det = (f"{h.get('url','')} → HTTP {h.get('status')}" if h.get("reachable") else
               "; ".join(probe.get("blocking") or []) or "không có URL (chỉ ca cli)")
        if h.get("note"):
            det += " — " + h["note"]
        gate("G0", "Môi trường", "ĐẠT" if g0 else "HỎNG", det, "" if g0 else "NO-RUN")

    nogo = []
    # G1
    bad_layers = {k: v for k, v in layers.items() if v.get("status") == "error"}
    if results is None:
        gate("G1", "Lớp chạy", "HỎNG", "thiếu results.json", "NO-GO")
        nogo.append("G1")
    elif bad_layers:
        gate("G1", "Lớp chạy", "HỎNG",
             "; ".join(f"{k}: {' | '.join(v.get('errors', [])[:2])}" for k, v in bad_layers.items())[:600], "NO-GO")
        nogo.append("G1")
    else:
        skipped = {k: v.get("reason", "") for k, v in layers.items() if v.get("status") == "khong-chay"}
        det = ", ".join(f"{k} ({v.get('tests', 0)} test)" for k, v in layers.items() if v.get("status") == "ok")
        if skipped:
            det += " · không chạy: " + ", ".join(f"{k}={r}" for k, r in skipped.items())
        gate("G1", "Lớp chạy", "ĐẠT", det or "—")
    # G2
    crit = [r for r in rows if r.get("priority") in ("P0", "P1")]
    crit_bad = [r for r in crit if r["status"] != "PASS"]
    if crit_bad:
        gate("G2", "Đường găng P0/P1", "HỎNG",
             f"{len(crit_bad)}/{len(crit)} ca P0/P1 không đạt: " +
             ", ".join(f"{r['tc_id']}({LABEL[r['status']]})" for r in crit_bad[:12]), "NO-GO")
        nogo.append("G2")
    else:
        gate("G2", "Đường găng P0/P1", "ĐẠT", f"{len(crit)}/{len(crit)} ca P0/P1 đạt")
    # G3
    total = len(rows)
    executed = sum(1 for r in rows if r["status"] in ("PASS", "FAIL"))
    cov = (100.0 * executed / total) if total else 0.0
    if total == 0 or cov < COVERAGE_MIN:
        gate("G3", "Độ phủ thực thi", "HỎNG", f"{executed}/{total} ca đã chạy = {cov:.1f}% < {COVERAGE_MIN:.0f}%", "NO-GO")
        nogo.append("G3")
    else:
        gate("G3", "Độ phủ thực thi", "ĐẠT", f"{executed}/{total} ca đã chạy = {cov:.1f}%")
    # G5
    if a.baseline:
        base = jload(Path(a.baseline), {}) or {}
        was = {r["tc_id"]: r["status"] for r in base.get("results", [])}
        regress = [r["tc_id"] for r in rows if was.get(r["tc_id"]) == "PASS" and r["status"] == "FAIL"]
        if regress:
            gate("G5", "Hồi quy", "HỎNG", f"{len(regress)} ca từng đạt nay hỏng: {', '.join(regress[:12])}", "NO-GO")
            nogo.append("G5")
        else:
            gate("G5", "Hồi quy", "ĐẠT", f"0 hồi quy so với {a.baseline}")
    else:
        # KHÔNG hạ trần: chưa từng có lượt XANH nào thì hồi quy là cổng KHÔNG ÁP DỤNG, không
        # phải rủi ro chưa đo. Trần dành cho thứ đáng lẽ đo được mà không đo. Khi sổ lỗi
        # (registry) có lịch sử mà người vẫn không chỉ baseline thì lúc ấy mới hạ trần.
        gate("G5", "Hồi quy", "KHÔNG ÁP",
             "không có baseline do người chỉ định (kỹ năng không bao giờ tự ghi baseline)")
    # G8 — Monkey test là BƯỚC BẮT BUỘC, không phải tuỳ chọn.
    # Ở v1, bỏ hẳn bước 8 cho kết quả y hệt lượt có chạy monkey: G8 ghi "KHÔNG CHẠY" và
    # không chặn gì. Nay: app web tới được mà không có kết quả monkey → HỎNG → NO-GO.
    # Chỉ lớp mobile thiếu thiết bị thật mới được hạ trần thay vì chặn.
    runs = [m for m in monkeys if not m.get("not_run")]
    notrun = [m.get("reason", "") for m in monkeys if m.get("not_run")]
    blocking = [x for m in runs for x in m.get("anomalies", []) if x.get("severity") in ("S1", "S2")]
    web_runs = [m for m in runs if "events_injected" not in m]
    droid_runs = [m for m in runs if "events_injected" in m]
    has_url = bool(((probe or {}).get("http") or {}).get("url")) and g0
    wants_mobile = any(r.get("platform") in ("android", "ios") for r in rows)
    if blocking:
        gate("G8", "Độ bền (monkey)", "HỎNG",
             f"{len(blocking)} bất thường S1/S2: " +
             "; ".join(f"{x['type']}@bước{x.get('step','?')}" for x in blocking[:8]), "NO-GO")
        nogo.append("G8")
    elif has_url and not web_runs:
        gate("G8", "Độ bền (monkey)", "HỎNG",
             "monkey web là bước BẮT BUỘC khi app tới được, nhưng lượt này không có kết quả "
             "monkey nào" + (f" · {'; '.join(notrun)}" if notrun else ""), "NO-GO")
        nogo.append("G8")
    elif runs:
        det = " · ".join(
            f"seed {m.get('seed')}: {m.get('actions_done', m.get('events_injected', '?'))} thao tác"
            for m in runs)
        if wants_mobile and not droid_runs:
            gate("G8", "Độ bền (monkey)", "THIẾU MỘT PHẦN",
                 det + " · monkey Android chưa chạy: " + ("; ".join(notrun) or "không có thiết bị"),
                 "HẠ TRẦN")
        else:
            gate("G8", "Độ bền (monkey)", "ĐẠT",
                 det + (f" · không chạy: {'; '.join(notrun)}" if notrun else ""))
    else:
        gate("G8", "Độ bền (monkey)", "KHÔNG ĐO ĐƯỢC",
             "; ".join(notrun)[:300] or "không có URL để chạy monkey (bộ ca chỉ có cli)",
             "HẠ TRẦN")

    # G9 — Rào không-sửa phải HIỆN DIỆN như một cổng. Ở v1 nó chỉ là một dấu ⚠ trong
    # report.md: repo không-git thì rào biến mất mà kết luận vẫn có thể là GO-CHỜ-KÝ.
    gmode = (guard or {}).get("mode")
    if invalid_report:
        gate("G9", "Rào không-sửa", "HỎNG", guard_detail[:400], "BÁO CÁO VÔ HIỆU")
    elif gmode == "khong-kiem-duoc":
        gate("G9", "Rào không-sửa", "KHÔNG ĐO ĐƯỢC",
             "không phải repo git và cây tệp quá lớn để băm — không chứng minh được lượt chạy "
             "này không sửa sản phẩm", "HẠ TRẦN")
    else:
        gate("G9", "Rào không-sửa", "ĐẠT",
             f"sạch · phương thức {gmode} · tệp bị .gitignore cũng nằm trong tầm quét")

    # G10 — Oracle-binding: assert có bám vào `expected` không. Không có hiện vật nghĩa là
    # phép đo này đã bị bỏ qua, mà nó là cổng duy nhất chặn được assert rỗng.
    if oracle is None:
        gate("G10", "Oracle-binding", "KHÔNG ĐO ĐƯỢC",
             "thiếu oracle_bind.json — chưa chạy check_oracle_binding.py trước khi đóng băng",
             "HẠ TRẦN")
    elif not oracle.get("ok"):
        gate("G10", "Oracle-binding", "HỎNG",
             "; ".join(oracle.get("violations") or [])[:600], "NO-GO")
        nogo.append("G10")
    else:
        d = (f"{oracle.get('cases_with_value_assert', 0)}/{oracle.get('cases_with_spec', 0)} ca "
             f"có assert giá trị neo vào `expected`")
        w = oracle.get("weak") or []
        gate("G10", "Oracle-binding", "ĐẠT", d + (f" · {len(w)} cảnh báo oracle yếu" if w else ""))

    # G11 — Chứng âm. Đây là cổng duy nhất phân biệt "sản phẩm đúng" với "thước hỏng":
    # cả hai đều cho ra một bộ test toàn xanh.
    if canary is None:
        gate("G11", "Chứng âm (negative control)", "KHÔNG ĐO ĐƯỢC",
             "thiếu canary.json — chưa chạy canary.py verify sau lượt chạy chính", "HẠ TRẦN")
    elif not canary.get("ok"):
        gate("G11", "Chứng âm (negative control)", "HỎNG",
             canary.get("reason", "")[:400], "BÁO CÁO VÔ HIỆU")
        invalid_report = True
        guard_detail += " · chứng âm hỏng: " + canary.get("reason", "")[:200]
    else:
        gate("G11", "Chứng âm (negative control)", "ĐẠT",
             "cả 3 mệnh đề chắc chắn sai đều đỏ — bộ đo của lượt này có thể bắt lỗi")

    # G12 — Bằng chứng đủ theo hợp đồng `evidence_required`.
    if evid is None:
        gate("G12", "Bằng chứng đủ", "KHÔNG ĐO ĐƯỢC",
             "thiếu evidence.json — chưa chạy check_evidence.py", "HẠ TRẦN")
    elif evid.get("ok"):
        gate("G12", "Bằng chứng đủ", "ĐẠT",
             f"{evid.get('checked', 0)} ca ĐẠT đều kèm đúng hiện vật đã khai "
             f"(hồ sơ {evid.get('profile', '?')})")
    elif evid.get("degrade"):
        gate("G12", "Bằng chứng đủ", "KHÔNG ĐO ĐƯỢC",
             f"hồ sơ ci: {len(evid.get('missing', []))} ca ĐẠT không sinh hiện vật — không "
             f"chặn, nhưng cũng không ký được bằng lượt này", "HẠ TRẦN")
    else:
        miss = evid.get("missing", [])
        gate("G12", "Bằng chứng đủ", "HỎNG",
             f"{len(miss)} ca ĐẠT thiếu bằng chứng: " +
             ", ".join(f"{m['tc_id']}({m['need']})" for m in miss[:10]), "NO-GO")
        nogo.append("G12")

    # G13 — Phủ yêu cầu: truy vết COV → TC → trạng thái. Ba trạng thái có ý nghĩa khác nhau
    # và không được gộp: chưa khai truy vết (KHÔNG ÁP) · khai ledger mà không đọc được
    # (lời hứa gãy → hạ trần) · ledger đọc được nhưng có yêu cầu không ca nào phủ (HỎNG).
    cov_case = {}
    for r in rows:
        for cid in (cases_by_id.get(r["tc_id"], {}).get("coverage_ids") or []):
            cov_case.setdefault(cid, []).append(r)
    ledger_decl = cases.get("coverage_ledger") or ""
    ledger_ids, ledger_read = set(), False
    if ledger_decl:
        try:
            ledger_ids = set(re.findall(r"COV-[A-Za-z0-9_-]+",
                                        Path(ledger_decl).read_text(encoding="utf-8-sig")))
            ledger_read = True
        except OSError:
            ledger_read = False
    paper = sorted(cid for cid, rs in cov_case.items()
                   if all(r["status"] not in ("PASS", "FAIL") for r in rs))
    orphan = sorted(ledger_ids - set(cov_case)) if ledger_read else []
    if not cov_case:
        gate("G13", "Phủ yêu cầu", "KHÔNG ÁP", "danh mục ca không khai `coverage_ids`")
    elif ledger_decl and not ledger_read:
        gate("G13", "Phủ yêu cầu", "KHÔNG ĐO ĐƯỢC",
             f"nguồn khai Coverage Ledger `{ledger_decl}` nhưng không đọc được — không biết "
             f"mẫu số thật, một yêu cầu không có ca nào sẽ vô hình", "HẠ TRẦN")
    elif paper or orphan:
        det = []
        if orphan:
            det.append(f"{len(orphan)} yêu cầu không ca nào phủ: {', '.join(orphan[:8])}")
        if paper:
            det.append(f"{len(paper)} yêu cầu chỉ được phủ bởi ca KHÔNG CHẠY (phủ trên giấy): "
                       f"{', '.join(paper[:8])}")
        gate("G13", "Phủ yêu cầu", "HỎNG", " · ".join(det), "NO-GO")
        nogo.append("G13")
    else:
        gate("G13", "Phủ yêu cầu", "ĐẠT",
             f"{len(cov_case)} yêu cầu đều có ít nhất một ca đã chạy"
             + (f" · đối chiếu với ledger `{ledger_decl}`" if ledger_read
                else " · nguồn không khai ledger nên chưa biết mẫu số thật"))

    def deep_gate(code, name, picker, notrun_reasons, empty_msg, notrun_msg):
        """Khung chung cho G14/G15: ca nào khai tầng ấy thì tầng ấy phải có kết luận.

        Ba trạng thái tách bạch: không ca nào khai (KHÔNG ÁP) · có khai nhưng tầng không
        chạy được, vd thiếu vai hoặc thiếu kết nối DB (KHÔNG ĐO ĐƯỢC → hạ trần) · chạy
        được và có ca hỏng (HỎNG → NO-GO). Gộp ba thứ này làm một là cách im lặng bỏ qua
        đúng nhóm rủi ro nặng nhất."""
        ids = [tc for tc, c in cases_by_id.items() if picker(c)]
        if not ids:
            gate(code, name, "KHÔNG ÁP", empty_msg)
            return
        mine = [r for r in rows if r["tc_id"] in ids]
        # Ca ĐÃ KHAI tầng sâu mà không chạy được thì tầng ấy CHƯA ĐO, bất kể lý do gì —
        # kể cả "khong-co-kich-ban". Chỉ đếm `notrun_reasons` thì một tầng im lặng không
        # chạy sẽ được tính là ĐẠT, đúng loại màu xanh giả mà cả v2 sinh ra để chống.
        blocked = [r for r in mine if r["status"] != "PASS" and r["status"] != "FAIL"]
        bad = [r for r in mine if r["status"] == "FAIL"]
        if bad:
            gate(code, name, "HỎNG",
                 f"{len(bad)}/{len(ids)} ca hỏng: " +
                 ", ".join(f"{r['tc_id']}({(r.get('error') or '')[:60]})" for r in bad[:6]),
                 "NO-GO")
            nogo.append(code)
        elif blocked:
            reasons = {r.get("reason") or "?" for r in blocked}
            why = ", ".join(sorted(reasons))
            # Gợi ý cố định chỉ đúng khi lý do ĐÚNG là lý do cổng này lường trước. Một ca
            # không chạy vì thiếu bằng chứng mà lại được khuyên "thiếu token vai" thì người
            # đọc đi sửa nhầm chỗ.
            hint = f" — {notrun_msg}" if reasons & set(notrun_reasons) else ""
            gate(code, name, "KHÔNG ĐO ĐƯỢC",
                 f"{len(blocked)}/{len(ids)} ca không chạy được ({why}){hint}", "HẠ TRẦN")
        else:
            gate(code, name, "ĐẠT", f"{len(ids)} ca đều đạt")

    # G14 — Ma trận quyền và IDOR. Ca chạy bằng vai ĐƯỢC phép chỉ chứng minh đường thuận đi
    # được; nó không chứng minh đường nghịch bị chặn.
    deep_gate("G14", "Ma trận quyền · IDOR",
              lambda c: isinstance(c.get("access"), dict),
              {"thieu-vai"},
              "không ca nào khai `access` (ma trận quyền)",
              "thiếu token vai thứ hai — không tự chế tài khoản, xem role_matrix.py")

    # G15 — Dữ liệu · Audit · Idempotency · Trạng thái. Cả bốn trả lời chung một câu hỏi:
    # cái hiện trên màn hình có đúng với cái đã ghi xuống không.
    deep_gate("G15", "Dữ liệu · Audit · Idempotency · Trạng thái",
              lambda c: bool(c.get("db_assert") or c.get("audit_assert") or c.get("idempotency")
                             or c.get("transition") or c.get("type") == "STATE"),
              {"thieu-ket-noi-db"},
              "không ca nào khai db_assert / audit_assert / idempotency / transition",
              "thiếu kết nối DB chỉ-đọc (đặt UAT_DB_DSN) — xem db_assert.py")

    # G16 — Khả năng tiếp cận, NỬA ĐO ĐƯỢC. Nửa còn lại ở G6 và mãi là CẦN NGƯỜI.
    A11Y_CEILING = ("axe-core bắt ~57% lỗi a11y theo số lượng; chỉ 29,5% tiêu chí WCAG 2.2 "
                    "tự động hoá được, 60,2% buộc kiểm thủ công — G16 xanh KHÔNG phải là "
                    "tuyên bố tuân thủ WCAG 2.2 AA")
    if a11y is None:
        gate("G16", "Khả năng tiếp cận (đo được)", "KHÔNG ĐO ĐƯỢC",
             "thiếu a11y.json — chưa chạy run_a11y.mjs", "HẠ TRẦN")
    elif a11y.get("not_run"):
        gate("G16", "Khả năng tiếp cận (đo được)", "KHÔNG ĐO ĐƯỢC",
             a11y.get("reason", "")[:300], "HẠ TRẦN")
    elif a11y.get("blocking"):
        b = a11y["blocking"]
        gate("G16", "Khả năng tiếp cận (đo được)", "HỎNG",
             f"{len(b)} vi phạm critical/serious: " +
             ", ".join(f"{x['id']}@{x['url'].rsplit('/', 1)[-1] or '/'}" for x in b[:8])
             + " · " + A11Y_CEILING, "NO-GO")
        nogo.append("G16")
    else:
        nb = len(a11y.get("violations", [])) - len(a11y.get("blocking", []))
        gate("G16", "Khả năng tiếp cận (đo được)", "ĐẠT",
             f"quét {len(a11y.get('scanned', []))} màn · 0 vi phạm critical/serious · "
             f"{nb} ghi nhận không chặn · {len(a11y.get('incomplete', []))} mục axe chưa kết "
             f"luận được (đúng chỗ cần người nhìn) · " + A11Y_CEILING)

    # G17 — Hiệu năng theo ngân sách NGƯỜI đặt, cộng sổ lỗi liên lượt.
    deep_gate("G17", "Hiệu năng (ngân sách người đặt)",
              lambda c: bool(c.get("perf_budget")) or c.get("type") == "PERFORMANCE",
              {"thieu-ngan-sach"},
              "không ca nào khai `perf_budget`",
              "ca PERFORMANCE thiếu ngân sách p95 do người đặt — không bịa ngưỡng")

    for code, name, why in (("G4", "Ngân sách lỗi", "ngưỡng S2 cho phép là thoả thuận của người, không có trong hiện vật"),
                            ("G6", "Phi chức năng", "a11y/hiệu năng cần ngân sách do người đặt"),
                            ("G7", "Ký duyệt", "cần người có thẩm quyền ký — AI không bao giờ tự duyệt")):
        gate(code, name, "CẦN NGƯỜI", why)

    # Kết luận = min( thang bậc theo cổng HỎNG , TRẦN theo cổng KHÔNG ĐO ĐƯỢC ).
    # Trục thứ hai là điểm khác v1: ở v1 một cổng không đo được không HỎNG nên không hạ bậc,
    # và cứ thế đi qua im lặng. Nay "không đo được" không bao giờ còn bằng "đạt".
    if invalid_report:
        verdict = "BÁO CÁO VÔ HIỆU"
    elif not g0:
        verdict = "NO-RUN"
    elif nogo:
        verdict = "NO-GO"
    elif degraded:
        verdict = "GO-CHỜ-KÝ-KÈM-KHUYẾT"
    else:
        verdict = "GO-CHỜ-KÝ"
    harness = "PASS" if verdict == "GO-CHỜ-KÝ" else "FAIL"

    # Phát hiện: mọi FAIL + KHÔNG CHẠY + bất thường monkey (S1-S3)
    findings = []
    for r in rows:
        if r["status"] == "PASS":
            continue
        if r["status"] == "FAIL":
            txt = (f"{r['tc_id']} [{r['priority']}][{r['severity_if_fail']}] {r.get('title','')[:70]}: "
                   f"mong đợi «{(r.get('expected') or '').replace(chr(10), ' ')[:140]}»"
                   + (f" (nguồn: {r.get('rule_ref') or r.get('oracle_source','')[:60]})" if (r.get('rule_ref') or r.get('oracle_source')) else "")
                   + f" — thực tế: {(r.get('error') or r.get('reason') or '').replace(chr(10), ' ')[:220]}"
                   + (f" — tái hiện {r['repro']}" if r.get("repro") else "")
                   + (f" — bằng chứng: {r['evidence'][0]}" if r.get("evidence") else ""))
        else:
            txt = (f"{r['tc_id']} [{r['priority']}] KHÔNG CHẠY ({r.get('reason','')})"
                   + (f": {r.get('error','')[:200]}" if r.get("error") else ""))
        findings.append({"kind": r["status"], "priority": r["priority"], "text": txt})
    for m in monkeys:
        for x in m.get("anomalies", []):
            findings.append({"kind": "MONKEY", "priority": x.get("severity"),
                             "text": f"MONKEY {x.get('severity')} {x.get('type')} seed {m.get('seed')} bước {x.get('step','?')} "
                                     f"×{x.get('count',1)}: {x.get('message','')[:200]}"
                                     + (f" — ảnh: {x['screenshot']}" if x.get('screenshot') else "")})
    order = {"P0": 0, "S1": 0, "P1": 1, "S2": 1, "P2": 2, "S3": 2, "P3": 3, "S4": 3}
    findings.sort(key=lambda f: (order.get(f["priority"], 9), f["kind"] != "FAIL"))

    sha = git_sha(a.repo)
    url = ((probe or {}).get("http") or {}).get("url", "")
    spec_hash = (guard or {}).get("spec_hash", "")
    now = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    rao_txt = {"git": "git", "hash-tree": "hash-tree",
               "khong-kiem-duoc": "KHÔNG KIỂM ĐƯỢC"}.get(gmode, "?")
    if guard is None or not guard.get("ok"):
        rao_txt = "VI PHẠM"
    monkey_txt = ("KHÔNG CHẠY" if not runs else
                  " + ".join(filter(None, [f"web×{len(web_runs)}" if web_runs else "",
                                           f"android×{len(droid_runs)}" if droid_runs else ""])))
    verdict_lines = [
        "## Kết quả UAT",
        f"VERDICT: {harness}",
        f"KẾT LUẬN: {verdict}",
        f"TỔNG: {counts.get('total', total)} | PASS: {counts.get('PASS', 0)} | FAIL: {counts.get('FAIL', 0)} | "
        f"KHÔNG CHẠY: {counts.get('KHONG_CHAY', 0)}",
        f"BUILD: {sha} · URL: {url or '—'} · Playwright {a.pw_version or '—'} · spec-hash "
        f"{spec_hash or '—'} · rào: {rao_txt} · monkey: {monkey_txt}",
        f"FILE: {out.as_posix()}/report.md",
    ]
    untrusted = (regi or {}).get("untrusted") or []
    if untrusted:
        verdict_lines.append(
            "KHÔNG ĐÁNG TIN (sổ lỗi): " + "; ".join(untrusted[:6])
            + " — vẫn chạy và vẫn tính, nhưng đã bị loại khỏi cơ sở so hồi quy.")
    if degraded:
        verdict_lines.append(
            "KHUYẾT PHÉP ĐO: " + ", ".join(
                f"{g['gate']} ({g['name']})" for g in gates if g["gate"] in degraded)
            + " — không đo được nên KHÔNG được coi là đạt; cần người xác nhận.")
    if findings:
        verdict_lines.append("FINDINGS:")
        verdict_lines += [f"  - {f['text']}" for f in findings[:40]]
        if len(findings) > 40:
            verdict_lines.append(f"  - … và {len(findings) - 40} phát hiện khác trong report.md")
    (out / "verdict.txt").write_text("\n".join(verdict_lines) + "\n", encoding="utf-8")

    md = [f"# Báo cáo UAT — {a.title or cases.get('feature', '')}", "",
          f"Chạy lúc {now} · nguồn ca `{cases.get('source', '')}` · kỹ năng `uat-test-only` (chỉ kiểm và báo cáo, không sửa)", "",
          "```", *verdict_lines[1:6], "```", "",
          f"**Rào không-sửa:** {guard_detail}", "", "## Cổng", "",
          "| Cổng | Tên | Trạng thái | Chi tiết | Hệ quả |", "|---|---|---|---|---|"]
    for g in gates:
        md.append(f"| {g['gate']} | {g['name']} | {g['state']} | {g['detail'].replace('|', '/')} | {g['effect']} |")
    md += ["", "## Kết quả theo ca", "",
           "| Ca | Ưu tiên | Nền tảng | Trạng thái | Lý do / lỗi | Tái hiện | Bằng chứng |", "|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (order.get(r["priority"], 9), r["tc_id"])):
        why = (r.get("error") or r.get("reason") or "").replace("\n", " ").replace("|", "/")[:160]
        ev = r["evidence"][0] if r.get("evidence") else ""
        md.append(f"| {r['tc_id']} | {r['priority']} | {r['platform']} | {LABEL[r['status']]} | {why} | "
                  f"{r.get('repro') or ''} | {ev} |")
    if monkeys:
        md += ["", "## Monkey test", ""]
        for m in monkeys:
            if m.get("not_run"):
                md.append(f"- `{Path(m['_file']).name}`: KHÔNG CHẠY — {m.get('reason','')}")
                continue
            md.append(f"- `{Path(m['_file']).name}`: seed {m.get('seed')} · {m.get('actions_done', m.get('events_injected', '?'))} "
                      f"thao tác · bất thường {len(m.get('anomalies', []))} · tái hiện: `{m.get('replay', '')}`")
            for x in m.get("anomalies", [])[:20]:
                md.append(f"  - {x.get('severity')} **{x.get('type')}** bước {x.get('step','?')} ×{x.get('count',1)}: "
                          f"{x.get('message','')[:200]}" + (f" — ảnh `{x['screenshot']}`" if x.get("screenshot") else ""))
    un = (results or {}).get("unmatched_tests") or []
    if un:
        md += ["", f"## Test không khớp ID kế hoạch ({len(un)}) — không được tính", ""]
        md += [f"- `{u.get('title','')[:90]}` ({u.get('project','')})" for u in un[:30]]
    if cases.get("warnings"):
        md += ["", f"## Cảnh báo khi đọc ca ({len(cases['warnings'])})", ""]
        md += [f"- {w}" for w in cases["warnings"][:30]]
    md += ["", "---", "",
           "Kỹ năng này **không** đề xuất cách sửa và **không** sửa gì. Phát hiện được bàn giao cho",
           "người hoặc cho stage `fix` của harness; người có thẩm quyền quyết định ký duyệt (G7)."]
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "verdict.json").write_text(json.dumps({
        "verdict": verdict, "harness_verdict": harness, "gates": gates, "counts": counts,
        "findings": findings, "build": sha, "url": url, "spec_hash": spec_hash, "generated_at": now,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(verdict_lines[:6]))
    print(f"build_report: {out.as_posix()}/report.md · {len(findings)} phát hiện")
    return 0


if __name__ == "__main__":
    sys.exit(main())
