#!/usr/bin/env python3
"""test_scripts.py — kiểm HÀNH VI các script của uat-test-only (không cần Playwright/Node).

Mỗi ca dựng dữ liệu giả trong thư mục tạm rồi chạy script THẬT bằng subprocess — không grep mã.
Nhiều ca tái hiện đúng một lỗi báo-xanh đã đo được ở uat-test-runner (rà soát 2026-09-19).
In "✓ …" / "✗ …" từng ca, dòng cuối "test_scripts: N đạt, M trượt". Thoát 0 khi 0 trượt.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SK = Path(__file__).resolve().parent.parent
SC = SK / "scripts"
PY = sys.executable
OK = FAIL = 0


def check(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


def run(script, *args, cwd=None, env_extra=None, strip_io_env=False):
    env = dict(os.environ)
    if strip_io_env:  # mô phỏng console cp932 của Windows: không ép UTF-8 từ ngoài
        env.pop("PYTHONIOENCODING", None)
        env.pop("PYTHONUTF8", None)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run([PY, str(SC / script), *map(str, args)], cwd=cwd, capture_output=True,
                       env=env, timeout=120)
    return r.returncode, r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def tc(i, **kw):
    base = {"tc_id": i, "title": f"ca {i}", "type": "GREEN", "platform": "web", "persona": "P", "journey_ref": "J",
            "priority": "P1", "severity_if_fail": "S2", "oracle_type": "Claim", "rule_ref": "AC-1",
            "oracle_source": "BRD §1", "catches_bug": "x", "coverage_ids": ["C1"], "backend_policy": "live",
            "steps": "mở trang", "expected": "thấy tiêu đề"}
    base.update(kw)
    return base


def pw_doc(tests, errors=None):
    """Dựng JSON reporter Playwright tối thiểu: tests = [(title, tags, project, [status…], expectedStatus)]."""
    specs = []
    for title, tags, proj, statuses, exp in tests:
        specs.append({"title": title, "tags": tags, "file": "x.e2e.spec.ts", "tests": [{
            "projectName": proj, "expectedStatus": exp, "annotations": [],
            "results": [{"status": s, "duration": 10, "error": {"message": "Expected: 1\nReceived: 2"} if s != "passed" else {},
                         "attachments": [{"name": "screenshot", "path": "a.png"}]} for s in statuses]}]})
    return {"suites": [{"title": "x", "file": "x.e2e.spec.ts", "specs": specs, "suites": []}],
            "errors": errors or [], "stats": {}}


def main():
    root = Path(tempfile.mkdtemp(prefix="uto-"))
    try:
        # ── hợp đồng handoff: MỘT nguồn sự thật ──
        print("── hop dong handoff")
        sync = Path.home() / ".claude" / "skills" / "uat-test-writer" / "scripts" / "sync_contract.py"
        if not sync.is_file():
            sync = SC.parents[1].parent / "uat-test-writer" / "scripts" / "sync_contract.py"
        if sync.is_file():
            r = subprocess.run([PY, str(sync), "--check"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            check("handoff-schema khop o ca 3 skill (writer la nguon su that)",
                  r.returncode == 0, (r.stdout + r.stderr)[-300:])
        else:
            # KHONG tinh la dat: khong tim thay writer thi phep kiem nay chua he chay.
            check("tim thay sync_contract.py cua writer de kiem hop dong", False,
                  f"khong thay {sync}")

        # ── validate_cases ──
        print("── validate_cases")
        d = root / "v"
        d.mkdir()
        (d / "u.json").write_text(json.dumps({"test_cases": [
            tc("TC-AUTH-LOGIN-001"), tc("TC-2", oracle_source=""), tc("TC-3", expected="đúng như hành vi hiện tại"),
            tc("TC-4", backend_policy="mocked-3p"), tc("TC-5", coverage_ids=[])]}, ensure_ascii=False), encoding="utf-8-sig")
        rc, out = run("validate_cases.py", "--cases", d / "u.json", "--out", d / "o1")
        c = jl(d / "o1" / "cases.json")
        check("uat.json: đọc được, BOM không làm hỏng", rc == 0 and c["stats"]["total"] == 5, out)
        check("ID nhiều đoạn TC-AUTH-LOGIN-001 giữ nguyên", c["cases"][0]["tc_id"] == "TC-AUTH-LOGIN-001")
        bad = {x["tc_id"]: " ".join(x["reasons"]) for x in c["invalid"]}
        check("oracle_source rỗng → ca không hợp lệ", "TC-2" in bad)
        check("expected là 'hành vi hiện tại' → không hợp lệ", "TC-3" in bad)
        check("mocked-* không lý do → không hợp lệ", "TC-4" in bad)
        check("coverage_ids rỗng → không hợp lệ", "TC-5" in bad)
        (d / "empty.md").write_text("# không có ca nào\n", encoding="utf-8")
        rc, _ = run("validate_cases.py", "--cases", d / "empty.md", "--out", d / "o2")
        check("0 ca → thoát 2 (0/0 không phải đạt)", rc == 2)
        md = ("### 5.1 GREEN\n\n| ID | Ưu tiên | Nghiêm trọng | Oracle | Kiểu | Bước (lệnh chạy) | Kết quả mong đợi | Kết quả thực tế | Trạng thái |\n"
              "|---|---|---|---|---|---|---|---|---|\n"
              "| TC-G01 | P0 | S1 | AC1 | Claim | `pnpm -r build` | thoát mã 0 | | |\n"
              "| TC-G02 | P1 | S2 |  | Claim | `pnpm test` | thoát mã 0 | | |\n"
              "### 5.4 BOUNDARY\n\n| ID | Ưu tiên | Nghiêm trọng | Oracle | Kiểu | Biên kiểm | Kết quả mong đợi | Kết quả thực tế | Trạng thái |\n"
              "|---|---|---|---|---|---|---|---|---|\n| TC-B01 | P0 | S2 | AC2 | Claim | số dòng ∈ {0,1} | đúng 1 | | |\n")
        (d / "h.md").write_text(md, encoding="utf-8")
        rc, out = run("validate_cases.py", "--cases", d / "h.md", "--out", d / "o3", "--default-platform", "cli")
        c = jl(d / "o3" / "cases.json")
        ids = {x["tc_id"]: x for x in c["cases"]}
        check("bảng harness: loại lấy từ tiêu đề mục", ids.get("TC-G01", {}).get("type") == "GREEN" and ids.get("TC-B01", {}).get("type") == "BOUNDARY", out)
        check("bảng harness: cột 'Biên kiểm' là bước", bool(ids.get("TC-B01", {}).get("steps")))
        check("bảng harness: thiếu cột Oracle → không hợp lệ", any(x["tc_id"] == "TC-G02" for x in c["invalid"]))
        wmd = ("## TC-W-01\n\n**Meta**:\n- Priority: `P0` 🔴\n- Platform: `web`\n\n**Oracle**:\n- Rule_ref: `R-1`\n"
               "- Oracle_source: BRD §2\n\n**Tiêu đề**: Đổi giá\n\n### Các bước kiểm thử\n- [ ] Mở màn giá\n\n"
               "### Kết quả mong đợi\n**UI**:\n- Giá hiện 45.000đ\n**API**:\n- trả 200\n\n### 🔧 Fix Context\n- Source code module: sửa ở đây\n")
        (d / "w.md").write_text(wmd, encoding="utf-8")
        run("validate_cases.py", "--cases", d / "w.md", "--out", d / "o4")
        w = jl(d / "o4" / "cases.json")["cases"]
        exp = w[0]["expected"] if w else ""
        check("khối writer: mong đợi giữ cả phần UI lẫn API", "45.000" in exp and "200" in exp, exp)
        check("khối writer: mục 'Fix Context' KHÔNG lọt vào oracle", "sửa ở đây" not in exp)
        rc, out = run("validate_cases.py", "--cases", d / "w.md", "--out", d / "o5", strip_io_env=True)
        check("console cp932 (không ép UTF-8): không sập", rc == 0, out[-200:])

        # ── merge_results ──
        print("── merge_results")
        m = root / "m"
        m.mkdir()
        (m / "cases.json").write_text(json.dumps({"cases": [
            {"tc_id": i, "priority": "P1", "platform": "web", "title": i} for i in
            ("TC-01", "TC-011", "TC-DUP", "TC-RETRY", "TC-SKIP", "TC-FAILX", "TC-MISS")],
            "invalid": [{"tc_id": "TC-INV", "reasons": ["x"], "priority": "P2"}]}), encoding="utf-8")
        (m / "pw.json").write_text(json.dumps(pw_doc([
            ("TC-011 chỉ là ca 011", ["@TC-011"], "e2e", ["passed"], "passed"),
            ("TC-01 ca 01", [], "e2e", ["failed"], "passed"),
            ("TC-DUP a", ["@TC-DUP"], "e2e", ["failed"], "passed"),
            ("TC-DUP b", ["@TC-DUP"], "e2e", ["passed"], "passed"),
            ("TC-RETRY", ["@TC-RETRY"], "e2e", ["failed", "passed"], "passed"),
            ("TC-SKIP", ["@TC-SKIP"], "e2e", ["skipped"], "skipped"),
            ("TC-FAILX", ["@TC-FAILX"], "e2e", ["failed"], "failed"),
            ("không có ID", [], "e2e", ["passed"], "passed"),
        ])), encoding="utf-8")
        (m / "rerun.json").write_text(json.dumps(pw_doc([("TC-DUP a", ["@TC-DUP"], "e2e", ["passed"], "passed")])), encoding="utf-8")
        rc, out = run("merge_results.py", "--cases", m / "cases.json", "--pw", m / "pw.json", "--rerun", m / "rerun.json", "--out", m / "r.json")
        r = {x["tc_id"]: x for x in jl(m / "r.json")["results"]}
        check("TC-01 hỏng KHÔNG bị gán nhầm sang TC-011 (khớp biên token)", r["TC-01"]["status"] == "FAIL" and r["TC-011"]["status"] == "PASS", out)
        check("trùng ca: đỏ + xanh → FAIL (xấu nhất thắng, không phải bản cuối)", r["TC-DUP"]["status"] == "FAIL")
        check("chạy lại riêng: xanh → tái hiện 1/2, trạng thái VẪN FAIL", r["TC-DUP"]["repro"] == "1/2" and r["TC-DUP"]["status"] == "FAIL")
        check("pass-on-retry → FAIL (chập chờn), không phải đạt", r["TC-RETRY"]["status"] == "FAIL" and r["TC-RETRY"]["reason"] == "chap-chon")
        check("test.skip → KHÔNG CHẠY (bị bỏ qua)", r["TC-SKIP"]["status"] == "KHONG_CHAY")
        check("test.fail() → FAIL (bị cấm)", r["TC-FAILX"]["status"] == "FAIL")
        check("ca kế hoạch vắng mặt → KHÔNG CHẠY (không có kịch bản)", r["TC-MISS"]["reason"] == "khong-co-kich-ban")
        check("ca không hợp lệ vẫn có trong mẫu số", r["TC-INV"]["reason"] == "ca-khong-hop-le")
        check("test không có ID → vào 'test lạc', không được tính", len(jl(m / "r.json")["unmatched_tests"]) == 1)
        (m / "err.json").write_text(json.dumps(pw_doc([], errors=[{"message": "SyntaxError: Unexpected token in x.e2e.spec.ts"}])), encoding="utf-8")
        run("merge_results.py", "--cases", m / "cases.json", "--pw", m / "err.json", "--out", m / "r2.json")
        lay = jl(m / "r2.json")["layers"].get("e2e", {})
        check("lỗi cấp cao (spec không biên dịch) → lớp ERROR, không phải '0 test đạt'", lay.get("status") == "error", str(lay))
        (m / "cut.json").write_text('{"suites": [', encoding="utf-8")
        run("merge_results.py", "--cases", m / "cases.json", "--pw", m / "cut.json", "--out", m / "r3.json")
        check("tệp JSON cụt → lớp ERROR", jl(m / "r3.json")["layers"].get("e2e", {}).get("status") == "error")

        # Quy lỗi ĐÚNG lớp: một tệp kết quả web hỏng không được làm lớp cli mang tiếng.
        (m / "mix.json").write_text(json.dumps({"cases": [
            {"tc_id": "TC-W1", "priority": "P1", "platform": "web", "title": "w"},
            {"tc_id": "TC-C1", "priority": "P1", "platform": "cli", "title": "c"}]}),
            encoding="utf-8")
        (m / "cli.json").write_text(json.dumps({"checks": [
            {"tc_id": "TC-C1", "status": "PASS", "name": "c"}]}), encoding="utf-8")
        run("merge_results.py", "--cases", m / "mix.json", "--pw", m / "cut.json",
            "--cli", m / "cli.json", "--out", m / "r4.json")
        lays = jl(m / "r4.json")["layers"]
        check("tệp web hỏng → lớp e2e ERROR", lays.get("e2e", {}).get("status") == "error",
              str(lays))
        check("tệp web hỏng KHÔNG làm lớp cli mang tiếng lỗi (v1: quy sai nguyên nhân)",
              lays.get("cli", {}).get("status") == "ok", str(lays))
        r4 = {x["tc_id"]: x for x in jl(m / "r4.json")["results"]}
        check("ca cli vẫn được chấm bình thường khi lớp khác hỏng",
              r4["TC-C1"]["status"] == "PASS" and r4["TC-W1"]["reason"] == "lop-loi", str(r4))

        # ── build_report ──
        print("── build_report")
        def scenario(name, rows, probe_ok=True, guard_ok=True, monkey=None, guard_mode="git",
                     oracle=True, canary=True, evidence=True, ledger="", a11y=True,
                     registry=None):
            o = root / "b" / name
            (o / "guard").mkdir(parents=True)
            counts = {"total": len(rows), "PASS": sum(1 for x in rows if x["status"] == "PASS"),
                      "FAIL": sum(1 for x in rows if x["status"] == "FAIL"),
                      "KHONG_CHAY": sum(1 for x in rows if x["status"] == "KHONG_CHAY")}
            full = [{"tc_id": x["tc_id"], "priority": x["priority"], "status": x["status"], "platform": "web",
                     "severity_if_fail": "S2", "title": "", "reason": x.get("reason", ""), "error": "", "evidence": [],
                     "expected": "e", "rule_ref": "AC", "repro": None} for x in rows]
            (o / "results.json").write_text(json.dumps({"results": full, "counts": counts,
                                                        "layers": {"e2e": {"status": "ok", "tests": len(rows)}}}), encoding="utf-8")
            (o / "cases.json").write_text(json.dumps(
                {"feature": "f", "coverage_ledger": ledger,
                 "cases": [dict({"tc_id": x["tc_id"]}, **(x.get("case") or {})) for x in rows]}),
                encoding="utf-8")
            (o / "probe.json").write_text(json.dumps({"ok": probe_ok, "blocking": [] if probe_ok else ["app không tới được"],
                                                      "http": {"reachable": probe_ok, "status": 200, "url": "http://x"}}), encoding="utf-8")
            (o / "guard" / "guard.json").write_text(json.dumps({"ok": guard_ok, "mode": guard_mode,
                                                                "product_changes": [] if guard_ok else ["đổi thêm: src/a.py"],
                                                                "test_changes": []}), encoding="utf-8")
            # Ba hien vat cua chang B. True = dat, None = thieu hien vat (ha tran),
            # dict = noi dung tu dung de dung thu truong hop hong.
            def art(name, val, good):
                if val is None:
                    return
                (o / name).write_text(json.dumps(good if val is True else val), encoding="utf-8")
            art("oracle_bind.json", oracle,
                {"ok": True, "cases_with_spec": len(rows), "cases_with_value_assert": len(rows),
                 "violations": [], "weak": []})
            art("canary.json", canary, {"ok": True, "found": {}, "green": [], "missing": []})
            art("a11y.json", a11y,
                {"not_run": False, "scanned": ["http://x/"], "violations": [], "blocking": [],
                 "incomplete": []})
            art("registry.json", registry, {"untrusted": []})
            art("evidence.json", evidence,
                {"ok": True, "profile": "signoff", "degrade": False, "checked": len(rows),
                 "missing": []})
            if monkey is not None:
                (o / "monkey").mkdir()
                (o / "monkey" / "web-1.json").write_text(json.dumps(monkey), encoding="utf-8")
            run("build_report.py", "--out", o, "--repo", root)
            return jl(o / "verdict.json"), (o / "verdict.txt").read_text(encoding="utf-8")

        ok_rows = [{"tc_id": "A", "priority": "P0", "status": "PASS"}, {"tc_id": "B", "priority": "P2", "status": "FAIL"}]
        v, t = scenario("xanh", ok_rows, monkey={"seed": 1, "actions_done": 50, "anomalies": [
            {"type": "console.error", "severity": "S3", "message": "x", "step": 3}]})
        check("P2 hỏng + console.error → GO-CHỜ-KÝ, VERDICT: PASS", v["verdict"] == "GO-CHỜ-KÝ" and "VERDICT: PASS" in t)
        check("P2 hỏng vẫn có trong FINDINGS", "B [P2]" in t)
        check("G4/G6/G7 luôn CẦN NGƯỜI", all(g["state"] == "CẦN NGƯỜI" for g in v["gates"] if g["gate"] in ("G4", "G6", "G7")))
        v, t = scenario("p0", [{"tc_id": "A", "priority": "P0", "status": "FAIL"}])
        check("P0 hỏng → NO-GO, VERDICT: FAIL", v["verdict"] == "NO-GO" and "VERDICT: FAIL" in t)
        # Cô lập G2: 20 ca đạt + 1 ca P1 KHÔNG CHẠY → độ phủ 20/21 = 95,2% ≥ 95% nên G3 ĐẠT;
        # chỉ G2 có thể làm kết luận thành NO-GO. (Bản đầu dùng 1 ca duy nhất → độ phủ 0% và G3
        # chặn thay — đối chứng âm cho thấy ca ấy vẫn xanh khi G2 bị làm hỏng.)
        rows_g2 = [{"tc_id": f"G{i}", "priority": "P3", "status": "PASS"} for i in range(20)] +                   [{"tc_id": "P1X", "priority": "P1", "status": "KHONG_CHAY", "reason": "khong-co-kich-ban"}]
        v, _ = scenario("p1-khong-chay", rows_g2)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("P1 KHÔNG CHẠY → G2 HỎNG → NO-GO, dù độ phủ đạt", v["verdict"] == "NO-GO" and g["G2"] == "HỎNG" and g["G3"] == "ĐẠT", str(g))
        v, _ = scenario("g0", ok_rows, probe_ok=False)
        check("G0 hỏng → NO-RUN", v["verdict"] == "NO-RUN")
        v, t = scenario("guard", ok_rows, guard_ok=False)
        check("rào vi phạm → BÁO CÁO VÔ HIỆU (đè mọi thứ)", v["verdict"] == "BÁO CÁO VÔ HIỆU" and "VERDICT: FAIL" in t)
        v, _ = scenario("monkey", ok_rows, monkey={"seed": 2, "actions_done": 9, "anomalies": [
            {"type": "pageerror", "severity": "S2", "message": "ReferenceError", "step": 4}]})
        check("monkey pageerror (S2) → NO-GO", v["verdict"] == "NO-GO")
        many = [{"tc_id": f"T{i}", "priority": "P3", "status": "PASS"} for i in range(19)] + \
               [{"tc_id": "T19", "priority": "P3", "status": "KHONG_CHAY", "reason": "khong-co-kich-ban"},
                {"tc_id": "T20", "priority": "P3", "status": "KHONG_CHAY", "reason": "khong-co-kich-ban"}]
        v, _ = scenario("phu", many)
        check("độ phủ 19/21 = 90% < 95% → NO-GO", v["verdict"] == "NO-GO")

        # --- Monkey test la BUOC BAT BUOC (v1: bo han van cho ket qua y het) ---
        v, t = scenario("khong-monkey", ok_rows)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("app toi duoc ma khong co ket qua monkey → G8 HỎNG → NO-GO",
              v["verdict"] == "NO-GO" and g["G8"] == "HỎNG", str(g))
        check("verdict.txt noi ro monkey KHONG CHAY", "monkey: KHÔNG CHẠY" in t, t)

        # --- Tran ket luan: rao khong kiem duoc thi KHONG duoc coi la dat ---
        v, t = scenario("rao-mu", ok_rows, guard_mode="khong-kiem-duoc",
                        monkey={"seed": 3, "actions_done": 30, "anomalies": []})
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("rao khong kiem duoc → G9 KHONG DO DUOC → ha tran, VERDICT: FAIL",
              v["verdict"] == "GO-CHỜ-KÝ-KÈM-KHUYẾT" and g["G9"] == "KHÔNG ĐO ĐƯỢC"
              and "VERDICT: FAIL" in t, str(g))
        check("khuyet phep do di vao khoi verdict.txt", "KHUYẾT PHÉP ĐO: G9" in t, t)
        check("dong BUILD mang theo trang thai rao", "rào: KHÔNG KIỂM ĐƯỢC" in t, t)

        # --- Chang B: ba cong chung minh PHEP DO dung ---
        mk = {"seed": 9, "actions_done": 40, "anomalies": []}
        v, _ = scenario("oracle-hong", ok_rows, monkey=mk,
                        oracle={"ok": False, "cases_with_spec": 2, "cases_with_value_assert": 1,
                                "violations": ["a.e2e.spec.ts: ca B khong co assert gia tri"],
                                "weak": []})
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("assert rong / khong neo vao expected → G10 HỎNG → NO-GO",
              v["verdict"] == "NO-GO" and g["G10"] == "HỎNG", str(g))

        v, t = scenario("canary-xanh", ok_rows, monkey=mk,
                        canary={"ok": False, "green": ["CANARY-HTTP"], "missing": [],
                                "reason": "menh de chac chan sai lai khong do"})
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("chung am lai XANH → thuoc hong → BÁO CÁO VÔ HIỆU (de moi cong khac)",
              v["verdict"] == "BÁO CÁO VÔ HIỆU" and g["G11"] == "HỎNG", str(g))
        check("rao van duoc ghi nhan la sach, khong bi quy oan", "rào: git" in t, t)

        v, _ = scenario("thieu-canary", ok_rows, monkey=mk, canary=None)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("khong chay chung am → G11 KHONG DO DUOC → ha tran",
              v["verdict"] == "GO-CHỜ-KÝ-KÈM-KHUYẾT" and g["G11"] == "KHÔNG ĐO ĐƯỢC", str(g))

        # Ca DAT ma thieu hien vat thi bi HA xuong KHONG CHAY, khong duoc tinh dat.
        v, t = scenario("thieu-bang-chung",
                        [{"tc_id": "A", "priority": "P0", "status": "PASS"}], monkey=mk,
                        evidence={"ok": False, "profile": "signoff", "degrade": False,
                                  "checked": 1,
                                  "missing": [{"tc_id": "A", "need": "trace", "priority": "P0",
                                               "have": []}]})
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("ca DAT thieu bang chung → G12 HỎNG va ca bi ha xuong KHONG CHAY",
              g["G12"] == "HỎNG" and v["counts"]["PASS"] == 0
              and v["counts"]["KHONG_CHAY"] == 1, str(v["counts"]))
        check("ca bi ha keo theo G2 hong (P0 khong con dat)",
              g["G2"] == "HỎNG" and v["verdict"] == "NO-GO", str(g))
        check("ly do thieu bang chung di vao FINDINGS", "thieu-bang-chung" in t, t)

        v, _ = scenario("ho-so-ci", ok_rows, monkey=mk,
                        evidence={"ok": False, "profile": "ci", "degrade": True, "checked": 2,
                                  "missing": [{"tc_id": "A", "need": "trace", "priority": "P0",
                                               "have": []}]})
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("ho so ci: thieu hien vat chi HA TRAN, khong chan",
              v["verdict"] == "GO-CHỜ-KÝ-KÈM-KHUYẾT" and g["G12"] == "KHÔNG ĐO ĐƯỢC"
              and v["counts"]["PASS"] == 1, str(g))

        # --- Doi chung duong: moi cong do duoc va dat → GO-CHO-KY tran ---
        v, t = scenario("tron-ven", [{"tc_id": "A", "priority": "P0", "status": "PASS"}],
                        monkey={"seed": 4, "actions_done": 200, "anomalies": []})
        check("moi cong do duoc va dat → GO-CHỜ-KÝ, VERDICT: PASS",
              v["verdict"] == "GO-CHỜ-KÝ" and "VERDICT: PASS" in t, t)
        check("khong co khuyet thi khong in dong KHUYET", "KHUYẾT PHÉP ĐO" not in t)

        # --- Chang C: phu yeu cau, ma tran quyen, tang du lieu ---
        mk2 = {"seed": 11, "actions_done": 50, "anomalies": []}
        cov = [{"tc_id": "A", "priority": "P0", "status": "PASS",
                "case": {"coverage_ids": ["COV-1"]}},
               {"tc_id": "B", "priority": "P2", "status": "KHONG_CHAY",
                "reason": "khong-co-kich-ban", "case": {"coverage_ids": ["COV-2"]}}]
        v, _ = scenario("phu-tren-giay", cov, monkey=mk2)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("yeu cau chi duoc phu boi ca KHONG CHAY → G13 HỎNG (phu tren giay)",
              g["G13"] == "HỎNG" and v["verdict"] == "NO-GO", str(g))

        v, _ = scenario("ledger-gay", [cov[0]], monkey=mk2, ledger="khong/ton/tai.md")
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("nguon khai ledger ma khong doc duoc → G13 KHONG DO DUOC → ha tran",
              g["G13"] == "KHÔNG ĐO ĐƯỢC" and v["verdict"] == "GO-CHỜ-KÝ-KÈM-KHUYẾT", str(g))

        v, _ = scenario("khong-truy-vet", ok_rows, monkey=mk2)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("danh muc khong khai coverage_ids → G13 KHONG AP, khong phat oan",
              g["G13"] == "KHÔNG ÁP", str(g))

        idor = [{"tc_id": "S1", "priority": "P0", "status": "FAIL",
                 "case": {"access": {"url": "/x", "allow": ["a"]}}}]
        v, _ = scenario("idor", idor, monkey=mk2)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("vai khong du quyen nhan 2xx → G14 HỎNG → NO-GO",
              g["G14"] == "HỎNG" and v["verdict"] == "NO-GO", str(g))

        thieu_vai = [{"tc_id": "S1", "priority": "P2", "status": "KHONG_CHAY",
                      "reason": "thieu-vai", "case": {"access": {"url": "/x", "allow": ["a"]}}}]
        v, _ = scenario("thieu-vai", thieu_vai, monkey=mk2)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("thieu token vai thu hai → G14 KHONG DO DUOC → ha tran, KHONG che tai khoan",
              g["G14"] == "KHÔNG ĐO ĐƯỢC", str(g))

        db = [{"tc_id": "D1", "priority": "P0", "status": "FAIL",
               "case": {"db_assert": {"query": "SELECT 1", "expect": {"rows": 1}}}}]
        v, _ = scenario("db-sai", db, monkey=mk2)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("UI xanh nhung DB sai → G15 HỎNG → NO-GO", g["G15"] == "HỎNG", str(g))

        db2 = [{"tc_id": "D1", "priority": "P2", "status": "KHONG_CHAY",
                "reason": "thieu-ket-noi-db",
                "case": {"idempotency": {"url": "/x", "count_query": "SELECT 1"}}}]
        v, _ = scenario("thieu-db", db2, monkey=mk2)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("khong noi duoc DB → G15 KHONG DO DUOC → ha tran", g["G15"] == "KHÔNG ĐO ĐƯỢC", str(g))

        # Mau xanh gia: ca DA KHAI tang sau ma tang ay khong he chay (vd script db khong
        # sinh ra tep ket qua) tung duoc tinh la DAT vi ly do "khong-co-kich-ban" khong nam
        # trong danh sach ly do duoc doi chieu. Nay moi trang thai khac PASS/FAIL deu la CHUA DO.
        # 20 ca dat + 1 ca sau chua do → do phu 20/21 = 95,2% nen G3 DAT; chi G15 co the
        # ha tran. (Khong co 20 ca kia thi G3 chan truoc va ca kiem nay van xanh ke ca khi
        # G15 bi lam hong — doi chung am, giong cach da lam voi G2.)
        chua_do = ([{"tc_id": f"OK{i}", "priority": "P3", "status": "PASS"} for i in range(20)]
                   + [{"tc_id": "D9", "priority": "P2", "status": "KHONG_CHAY",
                       "reason": "khong-co-kich-ban",
                       "case": {"db_assert": {"query": "SELECT 1", "expect": {"rows": 1}}}}])
        v, _ = scenario("tang-sau-im-lang", chua_do,
                        monkey={"seed": 13, "actions_done": 40, "anomalies": []})
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("ca khai db_assert ma tang db khong chay → G15 KHONG DO DUOC, KHONG phai DAT",
              g["G15"] == "KHÔNG ĐO ĐƯỢC" and g["G3"] == "ĐẠT"
              and v["verdict"] == "GO-CHỜ-KÝ-KÈM-KHUYẾT", str(g))
        det = [x["detail"] for x in v["gates"] if x["gate"] == "G15"][0]
        check("G15 noi ro ly do chua do la gi", "khong-co-kich-ban" in det, det[:120])

        # --- Chang D: a11y, hieu nang, so loi ---
        mk3 = {"seed": 12, "actions_done": 60, "anomalies": []}
        v, _ = scenario("a11y-serious", ok_rows, monkey=mk3,
                        a11y={"not_run": False, "scanned": ["http://x/"], "incomplete": [],
                              "violations": [{"id": "color-contrast", "impact": "serious",
                                              "url": "http://x/a", "nodes": 3}],
                              "blocking": [{"id": "color-contrast", "impact": "serious",
                                            "url": "http://x/a", "nodes": 3}]})
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("axe tra 1 vi pham serious → G16 HỎNG → NO-GO",
              g["G16"] == "HỎNG" and v["verdict"] == "NO-GO", str(g))
        det = [x["detail"] for x in v["gates"] if x["gate"] == "G16"][0]
        check("G16 luon in TRAN do luong (29,5% WCAG 2.2 tu dong hoa duoc)",
              "29,5%" in det and "KHÔNG phải là tuyên bố tuân thủ" in det, det[:120])

        v, _ = scenario("a11y-chua-quet", ok_rows, monkey=mk3, a11y=None)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("chua quet a11y → G16 KHONG DO DUOC → ha tran", g["G16"] == "KHÔNG ĐO ĐƯỢC", str(g))

        perf = [{"tc_id": "P1", "priority": "P2", "status": "KHONG_CHAY",
                 "reason": "thieu-ngan-sach", "case": {"type": "PERFORMANCE"}}]
        v, _ = scenario("perf-khong-ngan-sach", perf, monkey=mk3)
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("ca PERFORMANCE khong co ngan sach nguoi dat → ha tran, KHONG bia nguong",
              g["G17"] == "KHÔNG ĐO ĐƯỢC", str(g))

        v, t = scenario("chap-chon", ok_rows, monkey=mk3,
                        registry={"untrusted": ["TC-9 (chập chờn 67% trên 3 lượt đỏ)"]})
        check("ca chap chon → nhan KHONG DANG TIN vao verdict.txt, KHONG bi skip",
              "KHÔNG ĐÁNG TIN (sổ lỗi)" in t and "TC-9" in t, t)

        # --- registry.py: chay that tren du lieu 3 luot ---
        print("── registry")
        rg = root / "rg"
        (rg / "out").mkdir(parents=True)
        reg = rg / "_registry"
        for i, (st, repro) in enumerate([("FAIL", "1/2"), ("FAIL", "1/2"), ("FAIL", "2/2")]):
            o = rg / "out"
            (o / "results.json").write_text(json.dumps({
                "counts": {"total": 1, "PASS": 0, "FAIL": 1, "KHONG_CHAY": 0},
                "results": [{"tc_id": "TC-F", "priority": "P1", "status": st, "repro": repro,
                             "severity_if_fail": "S2", "error": "sai", "evidence": [],
                             "expected": "x", "reason": ""}]}), encoding="utf-8")
            (o / "cases.json").write_text(json.dumps(
                {"cases": [{"tc_id": "TC-F", "steps": "b1", "coverage_ids": ["COV-9"]}]}),
                encoding="utf-8")
            run("registry.py", "--registry", reg, "record", "--out", o, "--repo", rg,
                "--run-id", f"r{i}")
        doc = jl(reg / "tc" / "TC-F.json")
        check("so loi giu lich su qua nhieu luot", len(doc["runs"]) == 3, str(doc.get("runs")))
        check("ty le chap chon 2/3 > 20% → nhan KHONG DANG TIN",
              doc["untrusted"] is True and abs(doc["flake_rate"] - 0.667) < 0.01, str(doc))
        fd = jl(reg / "findings" / "r2.json")["findings"][0]
        check("phat hien theo mau defect toi thieu, KHONG co root cause / cach sua",
              set(fd) >= {"precondition", "action", "expected", "actual", "severity", "evidence"}
              and "root_cause" not in fd and "fix" not in fd, str(sorted(fd)))
        check("regression_hint lay tu coverage_ids", fd["regression_hint"] == ["COV-9"])
        rc, out = run("registry.py", "--registry", reg, "suggest")
        check("chua co luot XANH → suggest noi that, khong bia baseline", rc == 1, out)

        # ── guard_repo ──
        print("── guard_repo")
        g = root / "g"
        g.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=g)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "0"], cwd=g)
        (g / "app.py").write_text("x=1\n", encoding="utf-8")
        (g / "pre.txt").write_text("bẩn có sẵn\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=g)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "a"], cwd=g)
        (g / "out" / "tests").mkdir(parents=True)
        (g / "out" / "tests" / "a.e2e.spec.ts").write_text("test('TC-1', async()=>{ await expect(x).toBe(1) })\n", encoding="utf-8")
        st = g / "out" / "guard" / "s.json"
        run("guard_repo.py", "snapshot", "--repo", g, "--allow", g / "out", "--state", st)
        rc, _ = run("guard_repo.py", "freeze-tests", "--state", st, "--tests", g / "out" / "tests")
        check("kịch bản sạch → đóng băng được", rc == 0)
        (g / "out" / "report.md").write_text("ok", encoding="utf-8")
        rc, out = run("guard_repo.py", "verify", "--state", st)
        check("chỉ ghi trong vùng cho phép + bẩn có sẵn không đổi → sạch", rc == 0, out)
        (g / "pre.txt").write_text("bẩn có sẵn — đổi thêm\n", encoding="utf-8")
        rc, _ = run("guard_repo.py", "verify", "--state", st)
        check("tệp bẩn có sẵn bị đổi thêm → vi phạm", rc == 1)
        (g / "pre.txt").write_text("bẩn có sẵn\n", encoding="utf-8")
        (g / "app.py").write_text("x=2\n", encoding="utf-8")
        rc, _ = run("guard_repo.py", "verify", "--state", st)
        check("sửa tệp sản phẩm → vi phạm", rc == 1)
        subprocess.run(["git", "checkout", "-q", "--", "app.py"], cwd=g)
        (g / "out" / "tests" / "b.e2e.spec.ts").write_text("test.fixme('TC-2', async()=>{})\n", encoding="utf-8")
        rc, out = run("guard_repo.py", "freeze-tests", "--state", st, "--tests", g / "out" / "tests")
        check("kịch bản có .fixme( → TỪ CHỐI đóng băng", rc == 1 and "fixme" in out)
        (g / "out" / "tests" / "b.e2e.spec.ts").write_text("// test.skip( chỉ là chú thích\ntest('TC-2', async()=>{})\n", encoding="utf-8")
        rc, _ = run("guard_repo.py", "freeze-tests", "--state", st, "--tests", g / "out" / "tests")
        check("mẫu cấm nằm trong CHÚ THÍCH → không bị bắt oan", rc == 0)

        # ── guard_repo v2: ba đường thoát đã bịt ──
        print("── guard_repo v2")
        # (1) Tệp bị .gitignore nằm ngoài <OUT> bị sửa → vi phạm. Trước v2 đây là điểm mù, và
        #     .env / config.local / sqlite đúng là nhóm bị cám dỗ "chỉnh tí cho chạy được".
        (g / ".gitignore").write_text("secret.env\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=g)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                        "-m", "ignore"], cwd=g)
        (g / "secret.env").write_text("TOKEN=cu\n", encoding="utf-8")
        st2 = g / "out" / "guard" / "s2.json"
        run("guard_repo.py", "snapshot", "--repo", g, "--allow", g / "out", "--state", st2)
        rc, _ = run("guard_repo.py", "verify", "--state", st2)
        check("gitignore: chưa đổi gì → sạch", rc == 0)
        (g / "secret.env").write_text("TOKEN=moi\n", encoding="utf-8")
        rc, out = run("guard_repo.py", "verify", "--state", st2)
        check("tệp bị .gitignore ngoài <OUT> bị sửa → VI PHẠM (v1: điểm mù)", rc == 1, out)

        # (2) Thư mục KHÔNG phải repo git: v1 trả ok=true, kết luận vẫn có thể là GO-CHỜ-KÝ.
        #     v2 băm cả cây nên vẫn bắt được.
        ng = root / "ng"
        (ng / "out").mkdir(parents=True)
        (ng / "app.py").write_text("x=1\n", encoding="utf-8")
        st3 = ng / "out" / "guard" / "s.json"
        rc, out = run("guard_repo.py", "snapshot", "--repo", ng, "--allow", ng / "out",
                      "--state", st3)
        check("không phải repo git → mode hash-tree, KHÔNG bỏ cuộc",
              rc == 0 and jl(st3)["mode"] == "hash-tree", out)
        (ng / "out" / "report.md").write_text("ok", encoding="utf-8")
        rc, _ = run("guard_repo.py", "verify", "--state", st3)
        check("hash-tree: chỉ ghi trong <OUT> → sạch", rc == 0)
        (ng / "app.py").write_text("x=2\n", encoding="utf-8")
        rc, out = run("guard_repo.py", "verify", "--state", st3)
        check("hash-tree: sửa tệp sản phẩm → VI PHẠM (v1: lọt hoàn toàn)", rc == 1, out)

        # (3) Mẫu cấm nằm SAU một URL trên cùng một dòng. Mẫu //.*$ của v1 lột luôn phần sau
        #     https:// nên dòng này từng lọt cổng đóng băng.
        (g / "out" / "tests" / "c.e2e.spec.ts").write_text(
            "test('TC-3', async ({ page }) => {\n"
            "  await page.goto('https://x.test/a'); await page.waitForTimeout(500);\n"
            "});\n", encoding="utf-8")
        rc, out = run("guard_repo.py", "freeze-tests", "--state", st, "--tests",
                      g / "out" / "tests")
        check("waitForTimeout sau https:// trên MỘT dòng → TỪ CHỐI đóng băng",
              rc == 1 and "waitForTimeout" in out, out)
        (g / "out" / "tests" / "c.e2e.spec.ts").unlink()

        # ── run_cli_checks ──
        print("── run_cli_checks")
        c = root / "c"
        c.mkdir()
        (c / "checks.json").write_text(json.dumps({"checks": [
            {"tc_id": "TC-C1", "cmd": "echo xin chao", "expect": {"exit_code": 0, "stdout_contains": ["xin chao"]}},
            {"tc_id": "TC-C2", "cmd": "exit 3", "expect": {"exit_code": 0}},
            {"tc_id": "TC-C3", "cmd": "echo ERR! 1>&2", "expect": {"exit_code": 0, "stderr_not_contains": ["ERR!"]}},
            {"tc_id": "TC-C4", "cmd": "echo x", "expect": {}},
        ]}), encoding="utf-8")
        run("run_cli_checks.py", "--checks", c / "checks.json", "--cwd", c, "--out", c / "cli.json")
        res = {x["tc_id"]: x["status"] for x in jl(c / "cli.json")["checks"]}
        check("cli: đúng mong đợi → PASS", res.get("TC-C1") == "PASS", str(res))
        check("cli: sai mã thoát → FAIL", res.get("TC-C2") == "FAIL")
        check("cli: stderr có chuỗi cấm → FAIL", res.get("TC-C3") == "FAIL")
        check("cli: không có 'expect' → FAIL (không có oracle thì không chấm)", res.get("TC-C4") == "FAIL")

        # ── monkey_android (đọc lại log) ──
        print("── monkey_android")
        a = root / "a"
        a.mkdir()
        (a / "m.log").write_text(":Monkey: seed=5 count=500\n// CRASH: com.vd.app (pid 123)\n// Short Msg: java.lang.NullPointerException\n"
                                 "// Long Msg: java.lang.NullPointerException: x\n// NOT RESPONDING: com.vd.app (pid 124)\n"
                                 "Events injected: 312\n// Monkey finished\n", encoding="utf-8")
        run("monkey_android.py", "--parse-only", a / "m.log", "--seed", "5", "--out", a)
        ma = jl(a / "android-5.json")
        types = sorted(x["type"] for x in ma["anomalies"])
        check("android: bắt CRASH và ANR, mức S1", types == ["anr", "crash"] and all(x["severity"] == "S1" for x in ma["anomalies"]), str(types))
        check("android: đọc được số sự kiện đã bơm", ma["events_injected"] == 312)
        rc, _ = run("monkey_android.py", "--app-id", "com.vd.app", "--seed", "6", "--out", a, env_extra={"PATH": ""})
        check("android: không có adb → KHÔNG CHẠY (thoát 4), không giả đạt", rc == 4 and jl(a / "android-6.json").get("not_run") is True)

        # ── preflight ──
        print("── preflight")
        pf = root / "pf"
        pf.mkdir()
        blank = {k: "" for k in ("UAT_TOKEN_FILE", "UAT_DB_DSN", "UAT_USER", "TEST_USER",
                                 "E2E_USER", "UAT_BASE_URL")}
        rc, out = run("preflight.py", "--cwd", pf, "--output", pf / "pf.json",
                      env_extra=blank)
        check("preflight chay duoc va luon thoat 0 (ban do, khong phai cong)", rc == 0, out[-200:])
        rows = {r["gate"]: r for r in jl(pf / "pf.json")["rows"]}
        g14 = [k for k in rows if k.startswith("G14")][0]
        check("khong co token vai → bao thieu G14, va noi ro KHONG tu che tai khoan",
              rows[g14]["ok"] is False and "chế tài khoản" in rows[g14]["need"], str(rows[g14]))
        g15 = [k for k in rows if k.startswith("G15")][0]
        check("khong co DSN → bao thieu G15 kem yeu cau role CHI-DOC",
              rows[g15]["ok"] is False and "CHỈ-ĐỌC" in rows[g15]["need"], str(rows[g15]))
        check("noi ro thieu thi HA TRAN chu khong do", "HẠ TRẦN" in out, out[-300:])
        rc, out2 = run("preflight.py", "--cwd", pf,
                       env_extra=dict(blank, UAT_TOKEN_KE_TOAN="T-1",
                                      UAT_DB_DSN="sqlite:x.db"))
        check("cap token va DSN → hai nhom cong do duoc tang len",
              out2.count("  ✓") > out.count("  ✓"), f"{out.count('  ✓')} → {out2.count('  ✓')}")

        # ── probe_env ──
        print("── probe_env")
        rc, out = run("probe_env.py", "--url", "http://127.0.0.1:9", "--out", root / "p", "--timeout", "3")
        check("app không tới được → G0 hỏng (thoát 3), không gợi ý mock", rc == 3 and "mock" not in out.lower(), out[-200:])

        # ── resolve_credentials ──
        print("── resolve_credentials")
        e = root / "e"
        e.mkdir()
        (e / ".env.example").write_text("UAT_USER=placeholder\nUAT_PASS=changeme\n", encoding="utf-8")
        envx = {k: "" for k in ("UAT_USER", "UAT_PASS", "TEST_USER", "TEST_PASSWORD", "E2E_USER", "E2E_PASSWORD", "TEST_EMAIL", "UAT_PASSWORD")}
        rc, out = run("resolve_credentials.py", "--cwd", e, "--out", e / "c.json", env_extra=envx)
        check("chỉ có .env.example → KHÔNG dùng (thoát 3), không mock", rc == 3 and jl(e / "c.json")["found"] is False, out)
        (e / ".env.test").write_text("UAT_USER=that@vd.vn\nUAT_PASS=bi-mat-123\n", encoding="utf-8")
        rc, out = run("resolve_credentials.py", "--cwd", e, "--out", e / "c.json", env_extra=envx)
        check(".env.test thắng; mật khẩu KHÔNG in ra màn hình", rc == 0 and jl(e / "c.json")["user"] == "that@vd.vn" and "bi-mat-123" not in out)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\ntest_scripts: {OK} đạt, {FAIL} trượt")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
