#!/usr/bin/env python3
"""test_scripts.py — kiểm HÀNH VI các script của uat-test-writer.

Trước tệp này, writer có 4 script và KHÔNG một ca kiểm nào. Kiểm khói (cú pháp, khởi động
được) không đủ: thứ cần chứng minh là **đầu ra của writer thật sự đi lọt vào miệng của bên
thực thi**, và hai bên hiểu cùng một danh mục theo cùng một luật.

Ca quan trọng nhất ở đây là PARITY: cùng một `uat.json`, đi thẳng và đi vòng qua `.md` do
writer sinh, `uat-test-only/scripts/validate_cases.py` phải cho ra **cùng số ca hợp lệ và
cùng danh sách ca không hợp lệ**. Lệch nhau nghĩa là một trong hai đường đang tẩy trắng ca
xấu — và đó đúng là lỗi đã tìm thấy ngày 2026-09-20: ca thiếu `oracle_source` bị `.json`
chặn lại nhưng đi qua `.md` thì thành hợp lệ.

Chạy: python tests/test_scripts.py     Thoát 0 khi 0 trượt.
"""
import json
import os
import re
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
SKILLS = SK.parent
ONLY = SKILLS / "uat-test-only"
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
    r = subprocess.run([PY, str(script), *map(str, args)], cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def jl(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def tc(i, **kw):
    """Một TC hợp lệ tối thiểu theo handoff-schema."""
    base = {
        "tc_id": i, "title": f"Ca {i}", "type": "GREEN", "platform": "web",
        "persona": "P-1", "journey_ref": "J-1", "priority": "P1", "severity_if_fail": "S2",
        "oracle_type": "Claim", "rule_ref": f"AC-{i}",
        "oracle_source": f"Tài liệu §{i}: điều khoản cụ thể",
        "catches_bug": "bug cụ thể", "coverage_ids": [f"COV-{i}"], "backend_policy": "live",
        "steps": "1. mở màn; 2. bấm", "expected": "Hiện đúng giá trị 42",
    }
    base.update(kw)
    return base


def validate(src, out):
    """Chạy validate_cases.py của uat-test-only trên một danh mục → (hợp lệ, {id: lý do})."""
    rc, log = run(ONLY / "scripts" / "validate_cases.py", "--cases", src, "--out", out)
    if not (Path(out) / "cases.json").is_file():
        return None, {}, log
    d = jl(Path(out) / "cases.json")
    return ([c["tc_id"] for c in d["cases"]],
            {c["tc_id"]: "; ".join(c.get("reasons") or []) for c in d.get("invalid", [])}, log)


def main():
    root = Path(tempfile.mkdtemp(prefix="utw-"))
    try:
        if not (ONLY / "scripts" / "validate_cases.py").is_file():
            check("tìm thấy uat-test-only để kiểm parity", False, f"không có {ONLY}")
            print(f"\ntest_scripts: {OK} đạt, {FAIL} trượt")
            return 1

        # ── PARITY: json thẳng vs .md do writer sinh ──
        print("── parity json ↔ md (hợp đồng writer → test-only)")
        d = root / "p"
        d.mkdir()
        doc = {"feature": "demo", "evidence_profile": "signoff", "test_cases": [
            tc("TC-01"), tc("TC-02"),
            tc("TC-03", oracle_source=""),                 # thiếu nguồn oracle → phải bị chặn
            tc("TC-04", expected="đúng như hành vi hiện tại"),   # tautology → phải bị chặn
        ]}
        (d / "uat.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        rc, log = run(SK / "scripts" / "generate_uat_markdown.py", d / "uat.json", d / "uat.md")
        check("generate_uat_markdown: json → md chạy được", rc == 0 and (d / "uat.md").is_file(), log)

        ok_j, bad_j, lj = validate(d / "uat.json", d / "oj")
        ok_m, bad_m, lm = validate(d / "uat.md", d / "om")
        check("md giữ đủ số ca của json", ok_j is not None and ok_m is not None
              and len(ok_j) + len(bad_j) == len(ok_m) + len(bad_m) == 4,
              f"json={ok_j}/{list(bad_j)} md={ok_m}/{list(bad_m)}")
        check("PARITY: cùng tập ca HỢP LỆ qua cả hai đường",
              sorted(ok_j or []) == sorted(ok_m or []), f"json={sorted(ok_j or [])} md={sorted(ok_m or [])}")
        check("PARITY: cùng tập ca KHÔNG HỢP LỆ (md không tẩy trắng ca xấu)",
              sorted(bad_j) == sorted(bad_m), f"json={sorted(bad_j)} md={sorted(bad_m)}")
        check("ca thiếu oracle_source bị CHẶN ở cả hai đường",
              "TC-03" in bad_j and "TC-03" in bad_m, f"{bad_j} | {bad_m}")
        check("ca 'đúng như hành vi hiện tại' bị CHẶN ở cả hai đường",
              "TC-04" in bad_j and "TC-04" in bad_m, f"{bad_j} | {bad_m}")

        # ── validate_uat_json: writer tự kiểm hàng ──
        print("── validate_uat_json (W1)")
        v = root / "v"
        v.mkdir()

        def vjson(name, cases, **top):
            f = v / f"{name}.json"
            f.write_text(json.dumps(dict({"feature": "demo", "test_cases": cases}, **top),
                                    ensure_ascii=False), encoding="utf-8")
            return run(SK / "scripts" / "validate_uat_json.py", f)

        rc, log = vjson("ok", [tc("TC-01"), tc("TC-02")])
        check("bộ ca hợp lệ → thoát 0", rc == 0, log)

        rc, log = vjson("sec", [tc("TC-01", type="SECURITY")])
        check("type SECURITY thiếu khối `access` → chặn, nêu tên khối",
              rc == 1 and "access" in log and "TC-01" in log, log)

        rc, log = vjson("half", [tc("TC-01", type="SECURITY",
                                    access={"url": "/x"})])   # thiếu `allow`
        check("khối `access` khai nửa vời (thiếu allow) → chặn",
              rc == 1 and "nửa vời" in log, log)

        rc, log = vjson("allow", [tc("TC-01", type="SECURITY",
                                     access={"url": "/x", "allow": []})])
        check("access.allow rỗng → chặn, không đoán bừa vai nào được phép",
              rc == 1 and "allow" in log, log)

        rc, log = vjson("write", [tc("TC-01", type="DATA",
                                     db_assert={"query": "UPDATE don SET x=1",
                                                "expect": {"rows": 1}})])
        check("db_assert chứa câu GHI → chặn (tầng dữ liệu chỉ được ĐỌC)",
              rc == 1 and "SELECT" in log, log)

        rc, log = vjson("dsn", [tc("TC-01", db_assert={
            "query": "SELECT 1", "expect": {"rows": 1},
            "dsn": "postgresql://uatuser:MatKhau123@127.0.0.1:5433/db"})])
        check("DSN có user:password lọt vào uat.json → CHẶN (tệp này được commit)",
              rc == 1 and "BÍ MẬT" in log, log)

        rc, log = vjson("dem", [tc("TC-01")], tc_count=5)
        check("khai 5 ca nhưng mảng có 1 → chặn", rc == 1 and "khai 5" in log, log)

        rc, log = vjson("trung", [tc("TC-01"), tc("TC-01")])
        check("trùng tc_id → chặn", rc == 1 and "trùng" in log, log)

        rc, log = vjson("taut", [tc("TC-01", oracle_source="as-is, theo hành vi hiện tại")])
        check("oracle_source là 'hành vi hiện tại' → chặn (lấy sản phẩm đo chính nó)",
              rc == 1, log)

        # ĐỐI CHIẾU CHÉO: W1 và uat-test-only phải hiểu hợp đồng GIỐNG HỆT nhau.
        fx = ONLY / "tests" / "fixtures" / "uat.json"
        if fx.is_file():
            rc_w, log_w = run(SK / "scripts" / "validate_uat_json.py", fx)
            ok_o, bad_o, _ = validate(fx, v / "o")
            bad_w = set(re.findall(r"✗ (TC-[A-Za-z0-9-]+):", log_w))
            check("PARITY: writer và test-only chặn CÙNG một tập ca trên cùng tệp",
                  bad_w == set(bad_o), f"writer={sorted(bad_w)} only={sorted(bad_o)}")
        else:
            check("tìm thấy fixture của uat-test-only để đối chiếu chéo", False, str(fx))

        # ── coverage_calc (W2) + self_audit (W3) ──
        print("── coverage_calc (W2)")
        c = root / "c"
        c.mkdir()
        HEAD = "# Ledger\nM2=4 · FP=8 · risk=LOW\n\n"
        COLS = "| cov_id | K | I | N | TC | S |\n|---|---|---|---|---|---|\n"
        LEDGER = (HEAD + COLS
                  + "| COV-01 | AC | a | r1 | TC-01 | dat |\n"
                  + "| COV-02 | EP | b | r2 | TC-02 | dat |\n"
                  + "| COV-03 | BVA | c | r3 | GAP — chưa có môi trường đo | GAP |\n")
        (c / "ledger.md").write_text(LEDGER, encoding="utf-8")

        def uat(name, cases, **top):
            f = c / (name + ".json")
            f.write_text(json.dumps(dict({"feature": "d", "test_cases": cases}, **top),
                                    ensure_ascii=False), encoding="utf-8")
            return f

        # LLM ghi tc_min.max=999; script phai GHI DE bang so tinh duoc.
        f = uat("bia", [tc("TC-01", coverage_ids=["COV-01"]),
                        tc("TC-02", coverage_ids=["COV-02"])],
                tc_min={"max": 999, "M1": 999})
        rc, log = run(SK / "scripts" / "coverage_calc.py", "--ledger", c / "ledger.md",
                      "--uat", f, "--write")
        got = jl(f)["tc_min"]
        check("TC_min do MAY tinh, GHI DE con so LLM tu ghi (999 -> 25)",
              got["max"] == 25 and got["computed_by"] == "coverage_calc.py", str(got))
        check("M1 dem tu bang Ledger, M3 = ceil(FP^1.2)",
              got["M1"] == 3 and got["M3"] == 13, str(got))
        check("tong TC < TC_min -> bao thieu, KHONG cho padding",
              rc == 1 and "padding" in log, log[-200:])

        f = uat("mocoi", [tc("TC-01", coverage_ids=["COV-99"])])
        rc, log = run(SK / "scripts" / "coverage_calc.py", "--ledger", c / "ledger.md", "--uat", f)
        check("TC tro cov_id khong co trong Ledger -> TC mo coi",
              rc == 1 and "mồ côi" in log, log[-200:])

        (c / "ngam.md").write_text(
            HEAD + COLS + "| COV-01 | AC | a | r1 | TC-01 | dat |\n"
            + "| COV-03 | BVA | c | r3 |  |  |\n", encoding="utf-8")
        f = uat("ngam", [tc("TC-01", coverage_ids=["COV-01"])])
        rc, log = run(SK / "scripts" / "coverage_calc.py", "--ledger", c / "ngam.md", "--uat", f)
        check("item khong TC nao phu ma cung khong co dong GAP -> bao lo",
              rc == 1 and "GAP" in log, log[-200:])

        f = uat("noledger", [tc("TC-01", coverage_ids=["COV-01"])])
        rc, log = run(SK / "scripts" / "coverage_calc.py", "--ledger", c / "khong-co.md",
                      "--uat", f, "--write")
        check("khong doc duoc Ledger -> TC_min KHONG DO DUOC, khong lay so nao thay the",
              rc == 1 and jl(f)["tc_min"].get("status") == "KHÔNG ĐO ĐƯỢC", log[-200:])

        (c / "thieu.md").write_text("# Ledger\n\n" + COLS
                                    + "| COV-01 | AC | a | r1 | TC-01 | dat |\n",
                                    encoding="utf-8")
        f = uat("thieu", [tc("TC-01", coverage_ids=["COV-01"])])
        rc, log = run(SK / "scripts" / "coverage_calc.py", "--ledger", c / "thieu.md", "--uat", f)
        check("thieu M2/M3/M4 -> noi ro chua phai ENSEMBLE, khong im lang lay M1",
              "ENSEMBLE" in log, log[-200:])

        print("── self_audit (W3)")
        (c / "big.md").write_text(HEAD + COLS + "| COV-01 | AC | a | r | TC-01 | dat |\n",
                                  encoding="utf-8")
        good = uat("tot", [tc("TC-%02d" % i, coverage_ids=["COV-01"]) for i in range(1, 31)])
        rc, log = run(SK / "scripts" / "self_audit.py", "--uat", good, "--ledger", c / "big.md")
        check("W3: moi muc tinh duoc deu dat -> van SAN SANG-KEM-KHUYET (3 muc CAN NGUOI)",
              "SẴN SÀNG-KÈM-KHUYẾT" in log and "KHUYẾT PHÉP ĐO" in log, log[-300:])
        check("W3: ba muc CAN NGUOI khong ai duoc tu tich",
              log.count("CẦN NGƯỜI") >= 3, log[-300:])
        rc, log = run(SK / "scripts" / "self_audit.py", "--uat", good)
        check("W3: khong chi dinh Ledger -> W2 KHONG DO DUOC -> ha tran",
              "KHÔNG ĐO ĐƯỢC" in log, log[-300:])

        # Canh: thu self_audit.py DA TINH thi khong duoc quay lai dang o tu tich.
        skill = (SK / "SKILL.md").read_text(encoding="utf-8")
        audit_zone = skill[skill.index("Self-Audit Gate"):]
        ticks = [l for l in audit_zone.splitlines() if "✅/❌" in l]
        computed = ("_coverage-ledger.md` tồn tại", "TC_min = MAX", "coverage% được TÍNH",
                    "dòng GAP có lý do", "0 TC mồ côi", "KHỐI TẦNG SÂU", "0 bí mật trong",
                    "sync_contract.py --check")
        back = [k for k in computed if any(k in l for l in ticks)]
        check("khong con o TU TICH cho thu self_audit.py da tinh duoc",
              not back, f"quay lai: {back}")
        check("phan con lai duoc dan nhan may KHONG tinh duoc",
              "máy KHÔNG tính được" in audit_zone, "thieu nhan")

        # ── merge_batches ──
        print("── merge_batches")
        b = root / "b"
        b.mkdir()
        for k, ids in (("b1", ["TC-01", "TC-02"]), ("b2", ["TC-02", "TC-03"])):
            (b / f"{k}.json").write_text(json.dumps(
                {"feature": "demo", "test_cases": [tc(i) for i in ids]}, ensure_ascii=False),
                encoding="utf-8")
        rc, log = run(SK / "scripts" / "merge_batches.py", b / "b1.json", b / "b2.json",
                      "--feature", "demo", "--dedupe", "--no-renumber", "-o", b / "m.json")
        merged = jl(b / "m.json") if (b / "m.json").is_file() else {}
        ids = [t.get("tc_id") for t in merged.get("test_cases", [])]
        check("merge_batches: gộp được nhiều mẻ", rc == 0 and len(ids) > 0, log)
        check("merge_batches: --dedupe bỏ ca trùng ID", len(ids) == len(set(ids)), str(ids))
        check("merge_batches: không đánh rơi ca nào", set(ids) >= {"TC-01", "TC-03"}, str(ids))

        # ── sync_contract: một nguồn sự thật ──
        print("── sync_contract")
        rc, log = run(SK / "scripts" / "sync_contract.py", "--check")
        check("hợp đồng đang khớp ở cả 3 skill", rc == 0, log)
        copy = SKILLS / "uat-test-only" / "references" / "handoff-schema.md"
        if copy.is_file():
            keep = copy.read_text(encoding="utf-8")
            try:
                copy.write_text(keep + "\n<!-- cố ý làm trôi -->\n", encoding="utf-8")
                rc2, log2 = run(SK / "scripts" / "sync_contract.py", "--check")
                check("--check BẮT ĐƯỢC khi một bản sao bị trôi", rc2 == 1, log2)
                rc3, _ = run(SK / "scripts" / "sync_contract.py")
                rc4, log4 = run(SK / "scripts" / "sync_contract.py", "--check")
                check("sync khôi phục lại từ nguồn", rc3 == 0 and rc4 == 0, log4)
            finally:
                if copy.read_text(encoding="utf-8") != keep:
                    copy.write_text(keep, encoding="utf-8")
        # Cai LE mot skill: hang xom chua cai KHONG phai hop dong troi. Neu tinh la loi
        # thi mot du an chi cai uat-test-writer se khong bao gio tu qua duoc cong cua chinh
        # no — day la loi chan duong trien khai, phat hien khi dem ap cho moi du an.
        solo = root / "solo" / "skills" / "uat-test-writer"
        solo.parent.mkdir(parents=True)
        shutil.copytree(SK, solo)
        r = subprocess.run([PY, str(solo / "scripts" / "sync_contract.py"), "--check"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=ENV, timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
        check("cai le mot skill → --check van XANH, bao ro 'chua cai'",
              r.returncode == 0 and "chưa cài" in out, out[-200:])

        # ── routing_lint: moi cum kich hoat dung MOT chu ──
        print("── routing_lint")
        rc, log = run(SK / "scripts" / "routing_lint.py")
        check("khong cum kich hoat nao bi hai skill tranh nhau", rc == 0, log[-300:])
        check('"chạy UAT" thuoc ve uat-test-only (mac dinh phai la cai KHONG sua ma)',
              "uat-test-only" in (SK.parent / "uat-test-only" / "SKILL.md").read_text(
                  encoding="utf-8").split("Dùng khi user nói")[0]
              and '"chạy UAT"' in (SK.parent / "uat-test-only" / "SKILL.md").read_text(
                  encoding="utf-8"), "")
        # Doi chung am: dung hai skill gia cung khai mot cum -> lint PHAI do.
        fake = root / "fam" / "skills"
        (fake / "uat-test-writer" / "scripts").mkdir(parents=True)
        shutil.copy(SK / "scripts" / "routing_lint.py",
                    fake / "uat-test-writer" / "scripts" / "routing_lint.py")
        for name in ("uat-test-writer", "uat-test-runner"):
            d = fake / name
            d.mkdir(exist_ok=True)
            (d / "SKILL.md").write_text(
                "---" + chr(10) + "name: " + name + chr(10)
                + 'description: Dung khi user noi "chay uat bia dat".' + chr(10)
                + "---" + chr(10) + "# x" + chr(10), encoding="utf-8")
        r = subprocess.run([PY, str(fake / "uat-test-writer" / "scripts" / "routing_lint.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", env=ENV, timeout=120)
        check("hai skill cung khai mot cum → lint PHAI do (cong nay co the do that)",
              r.returncode == 1 and "TRANH CHẤP" in (r.stdout + r.stderr),
              (r.stdout + r.stderr)[-200:])

        rc, log = run(SK / "scripts" / "sync_contract.py", "--dups")
        check("--dups liệt kê được script trùng tên giữa các skill", rc == 0 and "script" in log, log)

        # ── generate_uat_excel ──
        print("── generate_uat_excel")
        x = root / "x"
        x.mkdir()
        (x / "uat.json").write_text(json.dumps(
            {"feature": "demo", "test_cases": [tc("TC-01"), tc("TC-02")]}, ensure_ascii=False),
            encoding="utf-8")
        rc, log = run(SK / "scripts" / "generate_uat_excel.py", x / "uat.json", x / "uat.xlsx")
        if "openpyxl" in log and rc != 0:
            # Thiếu thư viện KHÔNG được tính là đạt — ghi là chưa chạy được để thấy rõ.
            check("generate_uat_excel: có openpyxl để chạy", False, "thiếu openpyxl")
        else:
            check("generate_uat_excel: sinh được tệp xlsx khác rỗng",
                  rc == 0 and (x / "uat.xlsx").is_file() and (x / "uat.xlsx").stat().st_size > 0, log)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\ntest_scripts: {OK} đạt, {FAIL} trượt")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
