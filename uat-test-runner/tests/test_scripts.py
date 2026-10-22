#!/usr/bin/env python3
"""test_scripts.py — kiểm HÀNH VI các script của uat-test-runner.

Trước tệp này, runner có 12 script và KHÔNG một ca kiểm nào. Bộ này dựng dữ liệu giả trong
thư mục tạm rồi chạy script THẬT bằng subprocess — không grep mã nguồn.

Trọng tâm là các đường mà hỏng thì CHO RA MÀU XANH GIẢ, chứ không phải cho ra lỗi:
  * parse-test-cases nhận nhầm .json → từng trả "0 test cases" và thoát 0; phía sau đọc
    thành "không có ca nào để chạy" thay vì "tôi đọc sai định dạng".
  * flatten_pw_results phải tính pass-on-retry là CHẬP CHỜN, không phải đạt.
  * extract_failed_tcs phải liệt đúng ca đỏ — sót một ca là lần chạy lại bỏ qua nó.

Chạy: python tests/test_scripts.py     Thoát 0 khi 0 trượt.
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

HERE = Path(__file__).resolve().parent
SK = HERE.parent
SC = SK / "scripts"
PY = sys.executable
OK = FAIL = 0
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def check(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {str(detail)[:300]}" if detail else ""))


def run(script, *args, cwd=None):
    r = subprocess.run([PY, str(SC / script), *map(str, args)], cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def spec(title, project, statuses):
    """Một spec trong JSON reporter của Playwright."""
    return {"title": title, "tags": [], "file": f"x.{project}.spec.ts", "tests": [{
        "projectName": project, "expectedStatus": "passed", "annotations": [],
        "results": [{"status": s, "duration": 10, "error": {} if s == "passed"
                     else {"message": "Expected 1 Received 2"}} for s in statuses]}]}


def main():
    NL = chr(10)   # xuong dong that, dung khi dung noi dung tep .env
    root = Path(tempfile.mkdtemp(prefix="utr-"))
    try:
        # ── parse-test-cases: phải NÓI THẬT khi đọc sai ──
        print("── parse-test-cases")
        d = root / "p"
        d.mkdir()
        md = ("## TC-01\n\n**Meta**:\n- Priority: `P0`\n- Platform: `web`\n\n**Oracle**:\n"
              "- Rule_ref: `AC-1`\n- Oracle_source: Tài liệu §1\n\n**Tiêu đề**: Ca một\n\n"
              "### Các bước kiểm thử\n- [ ] mở màn\n\n### Kết quả mong đợi\n- Hiện 42\n")
        (d / "uat.md").write_text(md, encoding="utf-8")
        (d / "uat.json").write_text(json.dumps({"test_cases": [{"tc_id": "TC-01"}]}),
                                    encoding="utf-8")
        (d / "empty.md").write_text("# không có ca nào\n", encoding="utf-8")

        rc, log = run("parse-test-cases.py", d / "uat.md", "-o", d / "out.json")
        n = len(jl(d / "out.json")["test_cases"]) if (d / "out.json").is_file() else 0
        check("md hợp lệ → parse được và thoát 0", rc == 0 and n == 1, f"rc={rc} n={n} {log[-150:]}")
        rc, log = run("parse-test-cases.py", d / "uat.json", "-o", d / "j.json")
        check("đưa nhầm .json → THOÁT KHÁC 0, không im lặng trả 0 ca", rc != 0, f"rc={rc} {log[-150:]}")
        rc, log = run("parse-test-cases.py", d / "empty.md", "-o", d / "e.json")
        check("md không có ca nào → THOÁT KHÁC 0", rc != 0, f"rc={rc} {log[-150:]}")

        # ── flatten_pw_results ──
        print("── flatten_pw_results")
        f = root / "f"
        f.mkdir()
        doc = {"suites": [{"title": "s", "file": "x.spec.ts", "suites": [], "specs": [
            spec("TC-01-API: đạt", "api", ["passed"]),
            spec("TC-02-E2E: hỏng", "e2e", ["failed"]),
            spec("TC-03-E2E: chập chờn", "e2e", ["failed", "passed"]),
        ]}], "errors": [], "stats": {}}
        (f / "pw.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        rc, log = run("flatten_pw_results.py", f / "pw.json", f / "flat.json")
        flat = jl(f / "flat.json") if (f / "flat.json").is_file() else {}
        by = {t["tc_id"]: t for t in flat.get("tests", [])}
        check("gộp được kết quả Playwright thành bảng phẳng", rc == 0 and len(by) == 3, log[-200:])
        check("ca đạt được ghi là passed", by.get("TC-01", {}).get("status") == "passed", str(by))
        check("ca hỏng được ghi là failed", by.get("TC-02", {}).get("status") == "failed", str(by))
        check("pass-on-retry bị đánh dấu CHẬP CHỜN, không lặng lẽ thành đạt",
              by.get("TC-03", {}).get("pass_on_retry") is True, str(by.get("TC-03")))
        check("tóm tắt đếm đúng số ca hỏng",
              flat.get("summary", {}).get("failed", -1) >= 1, str(flat.get("summary")))

        # ── extract_failed_tcs ──
        print("── extract_failed_tcs")
        rc, log = run("extract_failed_tcs.py", f / "flat.json", "--scope", "verify",
                      "--output", f / "failed.txt")
        got = [x.strip() for x in (f / "failed.txt").read_text(encoding="utf-8").splitlines()
               if x.strip()] if (f / "failed.txt").is_file() else []
        check("liệt đúng ca đỏ để chạy lại (scope verify)", rc == 0 and "TC-02" in got, f"{got} {log[-150:]}")
        fl = flat.get("summary", {})
        flaky = fl.get("flaky_passed", fl.get("flaky_pass", fl.get("flaky")))
        check("ca chập chờn KHÔNG bị mất dấu — vẫn được đếm riêng trong tóm tắt",
              flaky not in (None, 0) or by.get("TC-03", {}).get("pass_on_retry") is True,
              str(fl))
        check("ca đạt KHÔNG bị lôi vào danh sách chạy lại", "TC-01" not in got, str(got))

        # ── duong Excel: writer -> xlsx -> runner -> ghi ket qua -> doc lai ──
        print("── duong Excel (read/write/recalc)")
        x = root / "x"
        x.mkdir()
        WR = SK.parent / "uat-test-writer"
        try:
            import openpyxl  # noqa: F401
            has_xl = True
        except ImportError:
            has_xl = False
        if not has_xl:
            # Thieu thu vien KHONG duoc tinh la dat.
            check("co openpyxl de kiem duong Excel", False, "thieu openpyxl")
        else:
            cases = [{"tc_id": "TC-01", "title": "Ca mot", "type": "GREEN", "platform": "web",
                      "persona": "P", "journey_ref": "J", "priority": "P0",
                      "severity_if_fail": "S1", "oracle_type": "Claim", "rule_ref": "AC-1",
                      "oracle_source": "TL §1", "catches_bug": "b", "coverage_ids": ["COV-01"],
                      "backend_policy": "live", "steps": "1. x", "expected": "y"},
                     {"tc_id": "TC-02", "title": "Ca hai", "type": "RED", "platform": "api",
                      "persona": "P", "journey_ref": "J", "priority": "P2",
                      "severity_if_fail": "S3", "oracle_type": "Claim", "rule_ref": "AC-2",
                      "oracle_source": "TL §2", "catches_bug": "b", "coverage_ids": ["COV-02"],
                      "backend_policy": "live", "steps": "1. x", "expected": "y"}]
            (x / "uat.json").write_text(json.dumps(
                {"feature": "cua-hang-mau", "test_cases": cases}, ensure_ascii=False),
                encoding="utf-8")
            r = subprocess.run([PY, str(WR / "scripts" / "generate_uat_excel.py"),
                                str(x / "uat.json"), str(x / "uat.xlsx")],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=ENV, timeout=300)
            check("writer sinh duoc xlsx tu uat.json",
                  (x / "uat.xlsx").is_file() and (x / "uat.xlsx").stat().st_size > 0,
                  (r.stdout + r.stderr)[-200:])

            rc, log = run("read_excel_uat.py", x / "uat.xlsx", "-o", x / "back.json")
            back = jl(x / "back.json") if (x / "back.json").is_file() else {}
            check("runner doc lai duoc xlsx cua writer, khong mat ca nao",
                  rc == 0 and len(back.get("test_cases", [])) == 2, log[-200:])
            check("ten feature di tron vong writer -> xlsx -> runner",
                  back.get("feature_name") == "cua-hang-mau", str(back.get("feature_name")))

            (x / "flat.json").write_text(json.dumps({"tests": [
                {"tc_id": "TC-01", "status": "passed", "layer": "e2e"},
                {"tc_id": "TC-02", "status": "failed", "layer": "api", "error": "sai"}],
                "summary": {"total": 2, "passed": 1, "failed": 1, "skipped": 0,
                            "by_layer": {}, "flaky_pass_on_retry": 0}}), encoding="utf-8")
            rc, log = run("write_results_to_excel.py", "--excel-file", x / "uat.xlsx",
                          "--results-file", x / "flat.json")
            check("ghi duoc ket qua nguoc vao xlsx", rc == 0, log[-200:])
            check("huong dan recalc KHONG tro vao duong dan cua moi truong khac",
                  "/mnt/skills/" not in log, log[-200:])

            rc, log = run("read_excel_uat.py", x / "uat.xlsx", "-o", x / "back2.json")
            blob = json.dumps(jl(x / "back2.json"), ensure_ascii=False).lower()
            check("doc lai thay trang thai da ghi (TC-02 hong)",
                  "fail" in blob or "không đạt" in blob, blob[:200])

            rc, log = run("recalc.py", x / "uat.xlsx")
            check("recalc chay duoc tren xlsx that", rc == 0, log[-200:])

        # ── resolve_credentials ──
        print("── resolve_credentials")
        e = root / "e"
        e.mkdir()
        (e / ".env.example").write_text("UAT_USER=placeholder@x" + NL + "UAT_PASS=changeme" + NL,
                                        encoding="utf-8")
        blank = {k: "" for k in ("UAT_USER", "UAT_PASS", "UAT_PASSWORD", "TEST_USER",
                                 "TEST_PASSWORD", "E2E_USER", "E2E_PASSWORD", "TEST_EMAIL")}
        r = subprocess.run([PY, str(SC / "resolve_credentials.py"), "--cwd", str(e),
                            "-o", str(e / "c.json")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env=dict(ENV, **blank), timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
        check("chi co .env.example -> KHONG dung lam tai khoan that",
              r.returncode != 0 or "placeholder" not in out, out[-200:])
        (e / ".env.test").write_text("UAT_USER=that@vd.vn" + NL + "UAT_PASS=bi-mat-123" + NL,
                                     encoding="utf-8")
        r = subprocess.run([PY, str(SC / "resolve_credentials.py"), "--cwd", str(e),
                            "-o", str(e / "c2.json")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env=dict(ENV, **blank), timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
        check("mat khau KHONG bao gio in ra man hinh", "bi-mat-123" not in out, out[-200:])

        # ── generate_mock_server ──
        print("── generate_mock_server")
        m2 = root / "m2"
        m2.mkdir()
        (m2 / "uat.json").write_text(json.dumps({"feature": "d", "test_cases": [
            {"tc_id": "TC-01", "platform": "api", "steps": "GET /api/don", "expected": "200"}]}),
            encoding="utf-8")
        rc, log = run("generate_mock_server.py", "--uat-data", m2 / "uat.json",
                      "-o", m2 / "mock.js")
        check("sinh duoc mock server tu danh muc ca",
              rc == 0 and (m2 / "mock.js").is_file() and (m2 / "mock.js").stat().st_size > 0,
              log[-200:])

        # ── hai script shell: chi kiem CU PHAP (cai dat that qua nang cho unit test) ──
        print("── script shell")
        for sh_name in ("check-env.sh", "install-playwright.sh"):
            r = subprocess.run(["bash", "-n", sh_name], cwd=str(SC), capture_output=True,
                               text=True)
            check(f"{sh_name}: cu phap bash hop le (chua kiem hanh vi cai dat)",
                  r.returncode == 0, r.stderr[-200:])

        # ── build_runner_report: CONG do MAY tinh (R1+R2) ──
        print("── build_runner_report")
        r = root / "r"
        r.mkdir()

        def scen(name, tests_, planned_, **kw):
            o = r / name
            o.mkdir()
            by = {}
            for t in tests_:
                L = by.setdefault(t["layer"], {"total": 0, "passed": 0, "failed": 0, "skipped": 0})
                L["total"] += 1
                L["passed" if t["status"] == "passed" else "failed"] += 1
            (o / "flat.json").write_text(json.dumps({"tests": tests_, "summary": {
                "total": len(tests_),
                "passed": sum(1 for t in tests_ if t["status"] == "passed"),
                "failed": sum(1 for t in tests_ if t["status"] == "failed"),
                "skipped": 0, "by_layer": by,
                "flaky_pass_on_retry": sum(1 for t in tests_ if t.get("pass_on_retry"))}}),
                encoding="utf-8")
            (o / "uat.json").write_text(json.dumps({"test_cases": planned_}), encoding="utf-8")
            (o / "url.json").write_text(json.dumps({"url": "http://x", "app_running": True}),
                                        encoding="utf-8")
            (o / "a11y.json").write_text(json.dumps({"blocking": [], "violations": []}),
                                         encoding="utf-8")
            (o / "signoff.txt").write_text("nguoi duyet A", encoding="utf-8")
            args = ["--results", o / "flat.json", "--uat", o / "uat.json",
                    "--url", o / "url.json", "--a11y", o / "a11y.json",
                    "--signoff", o / "signoff.txt", "--s2-budget", "0", "-o", o]
            for k, v in kw.items():
                args += [f"--{k.replace('_', '-')}", str(v)]
            rc, log = run("build_runner_report.py", *args)
            return jl(o / "runner-verdict.json"), (o / "runner-verdict.txt").read_text(
                encoding="utf-8"), log

        def T(i, st="passed", layer="e2e", retry=False):
            return {"tc_id": i, "title": i, "status": st, "layer": layer,
                    "duration_ms": 10, "retries": 0, "pass_on_retry": retry}

        def P(i, pri="P1", sev="S3", **kw):
            return dict({"tc_id": i, "priority": pri, "severity_if_fail": sev}, **kw)

        v, t, _ = scen("go", [T("A", layer="api"), T("B")], [P("A"), P("B")])
        check("moi cong dat → VERDICT: GO (thang cong toi duoc dich)",
              v["verdict"] == "GO" and "VERDICT: GO" in t, str(v.get("gates")))

        v, _, _ = scen("api", [T("A", "failed", "api"), T("B")], [P("A"), P("B")])
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("API smoke co 1 fail → G1 HỎNG → NO-GO",
              g["G1"] == "HỎNG" and v["verdict"] == "NO-GO", str(g))

        v, _, _ = scen("flaky", [T("A", layer="api"), T("B", retry=True)],
                       [P("A"), P("B", pri="P0", sev="S1")])
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("ca P0 pass-on-retry → G2 HỎNG (chap chon KHONG phai dat)",
              g["G2"] == "HỎNG" and v["verdict"] == "NO-GO", str(g))

        v, _, _ = scen("phu", [T("A", layer="api")], [P("A"), P("B"), P("C")])
        g = {x["gate"]: x["state"] for x in v["gates"]}
        check("mau so la KE HOACH: chay 1/3 ca → G3 HỎNG", g["G3"] == "HỎNG", str(g))

        o = r / "nobudget"
        v2, t2, _ = scen("nobudget2", [T("A", layer="api"), T("B", "failed")],
                         [P("A"), P("B", sev="S2")])
        g = {x["gate"]: x["state"] for x in v2["gates"]}
        check("co loi S2 ma nguong do nguoi dat = 0 → G4 HỎNG", g["G4"] == "HỎNG", str(g))

        v, t, _ = scen("heal", [T("A", layer="api"), T("B")], [P("A"), P("B")],
                       heal=(r / "hl.json"))
        (r / "hl.json").write_text(json.dumps({"entries": [{"tc": "A", "what": "x"}]}),
                                   encoding="utf-8")
        v, t, _ = scen("heal2", [T("A", layer="api"), T("B")], [P("A"), P("B")],
                       heal=(r / "hl.json"))
        check("da heal → KHONG BAO GIO la GO tran (thuoc bi chinh giua luc do)",
              v["verdict"] == "CONDITIONAL GO" and v["heal_count"] == 1, str(v["verdict"]))
        check("so lan heal hien ngay trong khoi verdict", "HEAL: 1" in t, t)

        # ── heal_log (R3) ──
        print("── heal_log")
        hl = r / "log.json"
        rc, log = run("heal_log.py", "--file", hl, "add", "--tc", "TC-01",
                      "--what", "doi locator", "--why", "cho test xanh")
        check("ly do 'cho test xanh' bi TU CHOI — heal phai co nguyen nhan that",
              rc == 2, log[-150:])
        rc, log = run("heal_log.py", "--file", hl, "add", "--tc", "TC-01",
                      "--what", "doi locator", "--why", "nut doi aria-label sau refactor")
        check("ly do that → ghi duoc vao so",
              rc == 0 and hl.is_file() and len(jl(hl)["entries"]) == 1, log[-150:])

        # ── B1: thang verdict phai khop hop dong §7 ──
        print("── hop dong §7")
        sch = SK / "references" / "handoff-schema.md"
        if sch.is_file():
            txt = sch.read_text(encoding="utf-8")
            src = (SK / "scripts" / "build_runner_report.py").read_text(encoding="utf-8")
            check("hop dong §7 va ma dung CUNG bo verdict cua runner",
                  all(k in txt and k in src
                      for k in ("CONDITIONAL GO", "NO-GO", "NO-RUN")),
                  "hop dong doi ma ma khong doi la do")
            check("hop dong ghi ro G1 hai ben KHAC NGHIA",
                  "KHÁC NGHĨA" in txt or "API smoke" in txt, "thieu canh bao G1")
        else:
            check("tim thay ban sao hop dong trong runner", False, str(sch))

        # ── detect_platform ──
        print("── detect_platform")
        pr = root / "proj"
        (pr / "src").mkdir(parents=True)
        (pr / "package.json").write_text(
            json.dumps({"name": "demo", "dependencies": {"react": "18.0.0"}}), encoding="utf-8")
        rc, log = run("detect_platform.py", pr, "-o", pr / "plat.json")
        plat = jl(pr / "plat.json") if (pr / "plat.json").is_file() else {}
        check("nhận ra dự án web từ package.json",
              rc == 0 and "WEB" in (plat.get("platforms") or []), f"{plat.get('platforms')} {log[-150:]}")

        # ── resolve_url ──
        print("── resolve_url")
        (pr / ".env").write_text("BASE_URL=http://127.0.0.1:39999\n", encoding="utf-8")
        rc, log = run("resolve_url.py", "--cwd", pr, "-o", pr / "url.json")
        u = jl(pr / "url.json") if (pr / "url.json").is_file() else {}
        check("đọc được URL từ .env", u.get("url") == "http://127.0.0.1:39999", str(u)[:200])
        check("cổng chết → app_running = false, KHÔNG báo là đang chạy",
              u.get("app_running") is False, str(u)[:200])

        # ── generate_maestro_flows ──
        print("── generate_maestro_flows")
        m = root / "m"
        m.mkdir()
        cases = {"feature": "demo", "test_cases": [
            {"tc_id": "TC-M1", "title": "Mở app", "type": "GREEN", "platform": "android",
             "priority": "P0", "steps": "1. mở app", "expected": "Hiện màn chính",
             "locator_hint": "testID=man-chinh"},
            {"tc_id": "TC-W1", "title": "Web thôi", "type": "GREEN", "platform": "web",
             "priority": "P1", "steps": "1. mở trang", "expected": "Hiện tiêu đề"}]}
        (m / "uat.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
        rc, log = run("generate_maestro_flows.py", m / "uat.json", "--app-id", "com.demo",
                      "-o", m / "flows")
        yamls = sorted(p.name for p in (m / "flows").glob("*.y*ml")) if (m / "flows").is_dir() else []
        check("sinh flow Maestro cho ca mobile", rc == 0 and any("TC-M1" in y for y in yamls),
              f"{yamls} {log[-150:]}")
        check("KHÔNG sinh flow cho ca web (sai nền tảng)",
              not any("TC-W1" in y for y in yamls), str(yamls))

        # ── generate_data_factory ──
        print("── generate_data_factory")
        g = root / "g"
        g.mkdir()
        (g / "uat.json").write_text(json.dumps({"feature": "demo", "test_cases": [],
            "data_fixtures": [{"fixture_id": "user.pending.D0", "entity": "user", "state": "pending",
                               "cleanup_recipe": "xoá theo id"}]}, ensure_ascii=False),
            encoding="utf-8")
        rc, log = run("generate_data_factory.py", g / "uat.json", "-o", g / "factory.ts")
        check("sinh được data factory từ data_fixtures",
              rc == 0 and (g / "factory.ts").is_file() and (g / "factory.ts").stat().st_size > 0,
              log[-200:])
        # Thieu khoa dinh danh phai NOI RO, khong duoc sap bang KeyError o mot dong ngau nhien.
        (g / "thieu.json").write_text(json.dumps(
            {"feature": "demo", "test_cases": [], "data_fixtures": [{"entity": "user"}]}),
            encoding="utf-8")
        rc, log = run("generate_data_factory.py", g / "thieu.json", "-o", g / "x.ts")
        check("fixture thiếu khoá định danh → báo lỗi rõ, không KeyError",
              rc == 2 and "fixture_id" in log and "KeyError" not in log, log[-200:])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\ntest_scripts: {OK} đạt, {FAIL} trượt")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
