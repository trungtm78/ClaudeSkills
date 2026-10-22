#!/usr/bin/env python3
"""merge_results.py — gộp kết quả thực thi thành MỘT bảng theo ca, đối chiếu với kế hoạch.

Đầu vào:
  --cases  <OUT>/cases.json            (từ validate_cases.py — danh sách ID KẾ HOẠCH)
  --pw     <tệp JSON reporter Playwright>   (lặp được; lượt chính)
  --rerun  <tệp JSON reporter Playwright>   (lặp được; lượt chạy lại riêng các ca FAIL)
  --junit  <tệp JUnit XML> [--junit-layer mobile]  (Maestro)
  --cli    <OUT>/results/cli.json      (từ run_cli_checks.py)
  --checks <lớp>=<tệp>                 (lặp được; lớp bất kỳ dùng chung định dạng ấy:
                                        db=…/db.json, security=…/idor.json, perf=…/perf.json)
  --not-run <lớp>=<lý do>              (lặp được; vd mobile=ngoai-thiet-bi — lớp không chạy được)
  --out    <OUT>/results.json

Bảy luật, mỗi luật chặn một đường runner cũ báo XANH khi sản phẩm hỏng:
  1. Lỗi cấp cao của Playwright (spec không biên dịch, globalSetup sập) → lớp ERROR,
     không phải "0 test, đạt".
  2. Tệp JSON thiếu/rỗng/cụt/không phải object → lớp ERROR, không bỏ qua bằng một dòng cảnh báo.
  3. Trùng ca (nhiều test/nhiều project/nhiều tệp) → trạng thái XẤU NHẤT thắng, không phải bản cuối.
  4. Chỉ ĐẠT khi đạt NGAY LẦN ĐẦU; pass-on-retry vẫn là FAIL (chập chờn).
  5. test.skip / fixme → KHONG_CHAY(bi-bo-qua); expectedStatus 'failed' (test.fail) → FAIL (cấm).
  6. Mọi ID kế hoạch phải có mặt: vắng → KHONG_CHAY(khong-co-kich-ban); ca không hợp lệ →
     KHONG_CHAY(ca-khong-hop-le). Mẫu số là KẾ HOẠCH, không phải "những gì đã chạy".
  7. Gán ID bằng tag "@<tc_id>" trước, rồi tới token nguyên vẹn trong tiêu đề, và LUÔN khớp
     với danh sách kế hoạch (TC-001 không bao giờ khớp TC-0010).

Thoát: 0 = đã ghi results.json (kể cả khi có FAIL) · 2 = không đọc được cases.json.
"""
import argparse
import datetime as _dt
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

RANK = {"FAIL": 3, "KHONG_CHAY": 2, "PASS": 1}
PLATFORM_LAYER = {"web": "e2e", "hybrid-webview": "e2e", "api": "api",
                  "android": "mobile", "ios": "mobile", "cli": "cli"}


def worst(a, b):
    if a is None:
        return b
    return a if RANK[a["status"]] >= RANK[b["status"]] else b


class Matcher:
    """Gán kết quả vào ID kế hoạch. Dài nhất thắng; biên token chặt."""

    def __init__(self, ids):
        self.ids = sorted(set(ids), key=len, reverse=True)
        self.lower = {i.lower(): i for i in self.ids}

    def match(self, title: str, tags):
        for t in tags or []:
            t = str(t).lstrip("@").strip()
            if t.lower() in self.lower:
                return self.lower[t.lower()]
        for i in self.ids:
            # không có chữ/số/gạch ngay trước; ngay sau không được là chữ/số
            if re.search(rf"(?<![A-Za-z0-9-]){re.escape(i)}(?![A-Za-z0-9])", title or "", re.I):
                return i
        return None


def infer_layers(path) -> set:
    """Tệp kết quả hỏng thì không còn bản ghi nào để biết nó thuộc lớp nào — suy từ tên tệp.

    Không suy được thì trả {"e2e", "api"} (hai lớp Playwright), KHÔNG trả mọi lớp: một spec
    web không biên dịch không được phép làm lớp cli mang tiếng lỗi.
    """
    n = Path(str(path)).name.lower()
    if n.endswith(".xml"):
        return {"mobile"}
    if "cli" in n:
        return {"cli"}
    return {"e2e", "api"}


def layer_of(project: str, file: str) -> str:
    p = (project or "").lower()
    f = (file or "").replace("\\", "/").lower()
    if "api" in p or ".api.spec." in f or "/api/" in f:
        return "api"
    if "setup" in p or "auth.setup" in f:
        return "setup"
    return "e2e"


def _rel(p: str) -> str:
    """Đường bằng chứng tương đối theo gốc repo (cwd): đường tuyệt đối của thư mục tạm trên máy
    chạy vô nghĩa với người đọc báo cáo ở máy khác."""
    try:
        return Path(p).resolve().relative_to(Path.cwd().resolve()).as_posix()
    except (ValueError, OSError):
        return p.replace("\\", "/")


def _attachments(res):
    out = []
    for a in res.get("attachments") or []:
        if a.get("path"):
            out.append(_rel(a["path"]))
    return out


def _err_text(res):
    e = res.get("error") or {}
    msg = e.get("message") or ""
    if not msg:
        errs = res.get("errors") or []
        msg = "\n".join((x.get("message") or "") for x in errs if isinstance(x, dict))
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)  # bỏ mã màu ANSI
    return msg.strip()[:1200]


def read_pw(path: Path, matcher: Matcher, layers: dict, unmatched: list):
    """Trả danh sách bản ghi {tc_id, layer, status, reason, error, evidence, duration_ms}."""
    recs = []
    label = str(path)
    try:
        raw = path.read_text(encoding="utf-8-sig")
        if not raw.strip():
            raise ValueError("tệp rỗng (Playwright có thể đã bị giết giữa chừng)")
        doc = json.loads(raw)
        if not isinstance(doc, dict):
            raise ValueError("gốc JSON không phải object")
    except (OSError, ValueError) as e:
        layers.setdefault("_files_bad", []).append(
            {"file": label, "error": str(e), "layers": infer_layers(path)})
        return recs, False
    top = [re.sub(r"\x1b\[[0-9;]*m", "", (x.get("message") or "")).strip()[:600]
           for x in (doc.get("errors") or []) if isinstance(x, dict)]

    def walk(suite, file_hint):
        f = suite.get("file") or file_hint
        for spec in suite.get("specs") or []:
            title = spec.get("title") or ""
            tags = spec.get("tags") or []
            sfile = spec.get("file") or f
            for t in spec.get("tests") or []:
                proj = t.get("projectName") or ""
                lay = layer_of(proj, sfile)
                results = t.get("results") or []
                tc = matcher.match(title, tags)
                if proj == "canary":
                    continue  # chứng-âm của lượt chạy, do canary.py chấm riêng — không vào mẫu số
                if lay == "setup":
                    if results and results[0].get("status") != "passed":
                        top.append(f"auth setup hỏng: {_err_text(results[0])[:300]}")
                    continue
                if tc is None:
                    unmatched.append({"title": title, "file": sfile, "project": proj})
                    continue
                exp_status = t.get("expectedStatus") or "passed"
                ann = [a.get("type") for a in (t.get("annotations") or []) if isinstance(a, dict)]
                first = results[0] if results else {}
                st0 = first.get("status")
                rec = {"tc_id": tc, "layer": lay, "project": proj, "file": sfile, "title": title,
                       "duration_ms": int(first.get("duration") or 0), "attempts": len(results),
                       "evidence": _attachments(first), "error": "", "reason": ""}
                if exp_status == "skipped" or st0 == "skipped" or "skip" in ann or "fixme" in ann:
                    rec.update(status="KHONG_CHAY", reason="bi-bo-qua",
                               error="test bị skip/fixme — kỹ năng cấm bỏ qua ca")
                elif exp_status == "failed" or "fail" in ann:
                    rec.update(status="FAIL", reason="test-fail-bi-cam",
                               error="test.fail() đảo nghĩa kết quả — bị cấm, tính là FAIL")
                elif st0 == "passed":
                    rec.update(status="PASS")
                elif not results:
                    rec.update(status="KHONG_CHAY", reason="khong-bat-dau",
                               error="test không bắt đầu (lượt chạy bị ngắt)")
                else:
                    later_pass = any(r.get("status") == "passed" for r in results[1:])
                    rec.update(status="FAIL", reason=("chap-chon" if later_pass else st0 or "failed"),
                               error=_err_text(first))
                recs.append(rec)
        for sub in suite.get("suites") or []:
            walk(sub, f)

    for s in doc.get("suites") or []:
        walk(s, s.get("file"))
    if top:
        touched = {r["layer"] for r in recs} or infer_layers(path)
        layers.setdefault("_top_errors", []).extend(
            {"file": label, "error": m, "layers": touched} for m in top)
    return recs, True


def read_junit(path: Path, matcher: Matcher, layer: str, layers: dict, unmatched: list):
    recs = []
    try:
        root = ET.parse(str(path)).getroot()
    except (OSError, ET.ParseError) as e:
        layers.setdefault("_files_bad", []).append(
            {"file": str(path), "error": str(e), "layers": {layer}})
        return recs, False
    for tcase in root.iter("testcase"):
        name = (tcase.get("name") or "") + " " + (tcase.get("classname") or "")
        tc = matcher.match(name, [])
        if tc is None:
            unmatched.append({"title": name.strip(), "file": str(path), "project": layer})
            continue
        fail = tcase.find("failure") if tcase.find("failure") is not None else tcase.find("error")
        skip = tcase.find("skipped")
        rec = {"tc_id": tc, "layer": layer, "project": layer, "file": str(path), "title": name.strip(),
               "duration_ms": int(float(tcase.get("time") or 0) * 1000), "attempts": 1,
               "evidence": [], "error": "", "reason": ""}
        if fail is not None:
            rec.update(status="FAIL", reason="failed",
                       error=((fail.get("message") or "") + "\n" + (fail.text or "")).strip()[:1200])
        elif skip is not None:
            rec.update(status="KHONG_CHAY", reason="bi-bo-qua", error="flow bị bỏ qua")
        else:
            rec.update(status="PASS")
        recs.append(rec)
    return recs, True


def read_checks(path: Path, matcher: Matcher, layers: dict, unmatched: list,
                layer: str = "cli"):
    recs = []
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        checks = doc["checks"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        layers.setdefault("_files_bad", []).append(
            {"file": str(path), "error": str(e), "layers": {layer}})
        return recs, False
    for c in checks:
        tc = matcher.match(str(c.get("tc_id") or ""), [c.get("tc_id")])
        if tc is None:
            unmatched.append({"title": str(c.get("tc_id")), "file": str(path),
                              "project": layer})
            continue
        st = c.get("status")
        rec = {"tc_id": tc, "layer": layer, "project": layer, "file": str(path),
               "title": c.get("name") or tc, "duration_ms": int(c.get("duration_ms") or 0),
               "attempts": 1, "evidence": [_rel(c["log"])] if c.get("log") else [],
               "error": "; ".join(c.get("reasons") or [])[:1200], "reason": ""}
        if st == "PASS":
            rec["status"] = "PASS"
        elif st == "KHONG_CHAY":
            rec.update(status="KHONG_CHAY", reason=c.get("reason") or "khong-chay")
        else:
            rec.update(status="FAIL", reason=c.get("reason") or "failed")
        recs.append(rec)
    return recs, True


def main():
    ap = argparse.ArgumentParser(description="Gộp kết quả UAT theo ca, đối chiếu kế hoạch")
    ap.add_argument("--cases", required=True)
    ap.add_argument("--pw", action="append", default=[])
    ap.add_argument("--rerun", action="append", default=[])
    ap.add_argument("--junit", action="append", default=[])
    ap.add_argument("--junit-layer", default="mobile")
    ap.add_argument("--cli", action="append", default=[])
    ap.add_argument("--checks", action="append", default=[],
                    help="<lớp>=<tệp> — lớp bất kỳ dùng chung định dạng của run_cli_checks "
                         "(db, audit, security, perf...)")
    ap.add_argument("--not-run", action="append", default=[], help="<lớp>=<lý do>")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    try:
        cdoc = json.loads(Path(a.cases).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        print(f"merge_results: không đọc được {a.cases}: {e}", file=sys.stderr)
        return 2
    planned = {c["tc_id"]: c for c in cdoc.get("cases", [])}
    invalid = {c["tc_id"]: c for c in cdoc.get("invalid", [])}
    matcher = Matcher(list(planned) + list(invalid))

    layers = {}
    unmatched = []
    per_layer = {}  # (tc, layer) -> worst record
    seen_layers = {}

    def absorb(recs, src_layer_hint):
        for r in recs:
            key = (r["tc_id"], r["layer"])
            per_layer[key] = worst(per_layer.get(key), r)
            seen_layers.setdefault(r["layer"], 0)
            seen_layers[r["layer"]] += 1

    file_state = {}
    for f in a.pw:
        recs, ok = read_pw(Path(f), matcher, layers, unmatched)
        file_state[f] = ok
        absorb(recs, None)
    for f in a.junit:
        recs, ok = read_junit(Path(f), matcher, a.junit_layer, layers, unmatched)
        file_state[f] = ok
        absorb(recs, a.junit_layer)
    for f in a.cli:
        recs, ok = read_checks(Path(f), matcher, layers, unmatched, "cli")
        file_state[f] = ok
        absorb(recs, "cli")
    for spec in a.checks:
        if "=" not in spec:
            print(f"merge_results: bỏ qua --checks '{spec}' (thiếu dạng <lớp>=<tệp>)",
                  file=sys.stderr)
            continue
        lay, f = spec.split("=", 1)
        recs, ok = read_checks(Path(f.strip()), matcher, layers, unmatched, lay.strip())
        file_state[f] = ok
        absorb(recs, lay.strip())

    # Lượt chạy lại: KHÔNG đổi trạng thái, chỉ ghi độ tái hiện.
    rerun = {}
    for f in a.rerun:
        tmp_layers, tmp_un = {}, []
        recs, ok = read_pw(Path(f), matcher, tmp_layers, tmp_un)
        for r in recs:
            rerun[(r["tc_id"], r["layer"])] = worst(rerun.get((r["tc_id"], r["layer"])), r)

    not_run = {}
    for nr in a.not_run:
        if "=" in nr:
            k, v = nr.split("=", 1)
            not_run[k.strip()] = v.strip()

    # Trạng thái lớp
    bad_files = layers.get("_files_bad", [])
    top_errors = layers.get("_top_errors", [])
    layer_status = {}
    expected_layers = {PLATFORM_LAYER.get(c.get("platform", "web"), "e2e") for c in planned.values()}
    for lay in sorted(expected_layers | set(seen_layers) | set(not_run)):
        st = {"status": "ok", "tests": seen_layers.get(lay, 0), "errors": []}
        if lay in not_run:
            st.update(status="khong-chay", reason=not_run[lay])
        # Lỗi chỉ thuộc về lớp đã sinh ra nó. v1 gán cho MỌI lớp, nên một spec web không
        # biên dịch làm lớp cli cũng mang tiếng lỗi — kết luận vẫn an toàn nhưng quy sai nguyên nhân.
        mine_top = [e["error"] for e in top_errors if lay in e.get("layers", set())]
        mine_bad = [f"tệp kết quả hỏng: {b['file']} — {b['error']}"
                    for b in bad_files if lay in b.get("layers", set())]
        st["errors"] += mine_top + mine_bad
        if st["status"] == "ok" and (mine_top or mine_bad):
            st["status"] = "error"
        if st["status"] == "ok" and lay in expected_layers and seen_layers.get(lay, 0) == 0:
            st.update(status="error")
            st["errors"].append(f"lớp '{lay}' có ca kế hoạch nhưng KHÔNG có kết quả nào")
        layer_status[lay] = st

    # Tổng hợp theo ca: trạng thái xấu nhất qua các lớp; vắng mặt → KHONG_CHAY có lý do.
    rows = []
    for tc, c in planned.items():
        lays = {k[1]: v for k, v in per_layer.items() if k[0] == tc}
        want = PLATFORM_LAYER.get(c.get("platform", "web"), "e2e")
        agg = None
        for lay, r in lays.items():
            agg = worst(agg, r)
        if agg is None:
            reason = "khong-co-kich-ban"
            if want in not_run:
                reason = not_run[want]
            elif layer_status.get(want, {}).get("status") == "error":
                reason = "lop-loi"
            agg = {"status": "KHONG_CHAY", "reason": reason, "error": "", "evidence": [],
                   "layer": want, "duration_ms": 0, "attempts": 0}
        repro = None
        if agg["status"] == "FAIL":
            rr = rerun.get((tc, agg["layer"]))
            if rr is not None:
                repro = "2/2" if rr["status"] == "FAIL" else "1/2"
        rows.append({
            "tc_id": tc, "title": c.get("title", ""), "priority": c.get("priority", "P2"),
            "severity_if_fail": c.get("severity_if_fail", "S3"), "platform": c.get("platform", "web"),
            "type": c.get("type", ""), "rule_ref": c.get("rule_ref", ""),
            "oracle_source": c.get("oracle_source", ""), "expected": c.get("expected", ""),
            "status": agg["status"], "reason": agg.get("reason", ""), "error": agg.get("error", ""),
            "evidence": agg.get("evidence", []), "layers": {k: v["status"] for k, v in lays.items()},
            "repro": repro, "duration_ms": agg.get("duration_ms", 0),
        })
    for tc, c in invalid.items():
        rows.append({
            "tc_id": tc, "title": c.get("title", ""), "priority": c.get("priority", "P2"),
            "severity_if_fail": "S3", "platform": c.get("platform", "web"), "type": "",
            "rule_ref": "", "oracle_source": "", "expected": "",
            "status": "KHONG_CHAY", "reason": "ca-khong-hop-le",
            "error": "; ".join(c.get("reasons") or []), "evidence": [], "layers": {},
            "repro": None, "duration_ms": 0,
        })

    counts = {"PASS": 0, "FAIL": 0, "KHONG_CHAY": 0}
    for r in rows:
        counts[r["status"]] += 1
    doc = {
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "sources": {"pw": a.pw, "rerun": a.rerun, "junit": a.junit, "cli": a.cli,
                    "checks": a.checks},
        "layers": layer_status, "results": rows, "unmatched_tests": unmatched,
        "counts": {"total": len(rows), **counts},
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"merge_results: {len(rows)} ca · PASS {counts['PASS']} · FAIL {counts['FAIL']} · "
          f"KHÔNG CHẠY {counts['KHONG_CHAY']} · test lạc (không khớp ID) {len(unmatched)}")
    for lay, st in layer_status.items():
        if st["status"] != "ok":
            print(f"  ! lớp {lay}: {st['status']} {st.get('reason','')} {' | '.join(st['errors'][:2])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
