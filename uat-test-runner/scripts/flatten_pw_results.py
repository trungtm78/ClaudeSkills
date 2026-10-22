#!/usr/bin/env python3
"""
flatten_pw_results.py — Gộp kết quả Playwright JSON (+ Maestro JUnit XML nếu có)
thành 1 file results_flat.json chuẩn cho toàn pipeline.

Đây là bước BẮT BUỘC sau mỗi lần chạy test (GĐ 7a / RT-5 trong SKILL.md).
Output là NGUỒN CHÂN LÝ duy nhất cho:
  - extract_failed_tcs.py  (Retest Mode)
  - write_results_to_excel.py  (ghi Excel — optional)
  - baseline diff (regression detection)

Usage:
    python flatten_pw_results.py <input1.json> [<input2.json> ...] <output.json>
    python flatten_pw_results.py api-results.json e2e-results.json results_flat.json
    # Kèm Maestro JUnit (mobile):
    python flatten_pw_results.py api.json e2e.json results_flat.json \\
        --maestro-junit test-results/mobile/report.xml

Quy tắc:
  - Input file không tồn tại → cảnh báo + bỏ qua (layer đó chưa chạy), KHÔNG fail.
    Ít nhất 1 input hợp lệ mới ghi output; 0 input hợp lệ → exit 1.
  - TC ID lấy từ title theo pattern TC-xxx (khớp naming convention của runner).
  - Layer: từ suffix title (-API/-E2E) → từ path file spec → từ tên file input.
  - Status chuẩn hoá: passed | failed | skipped | timedOut | interrupted
    (timedOut/interrupted được extract_failed_tcs coi là fail).

Schema output:
{
  "generated_at": "<ISO>",
  "sources": [{"file": "...", "kind": "playwright|maestro-junit", "tests": N}],
  "tests": [
    {"tc_id": "TC-001", "title": "TC-001-API: ...", "status": "passed",
     "layer": "api", "file": "tests/api/x.api.spec.ts",
     "duration_ms": 812, "retries": 0, "pass_on_retry": false, "error": ""}
  ],
  "summary": {"total": N, "passed": n1, "failed": n2, "skipped": n3,
              "by_layer": {"api": {...}, "e2e": {...}, "mobile": {...}}}
}
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

TC_ID_PATTERN = re.compile(r"\b(TC-[A-Z0-9]*-?\d+)\b", re.IGNORECASE)
FAILED_STATUSES = {"failed", "timedOut", "interrupted"}


def extract_tc_id(title: str) -> str:
    m = TC_ID_PATTERN.search(title or "")
    return m.group(1).upper() if m else ""


def detect_layer(title: str, file_path: str, source_name: str) -> str:
    t = (title or "").upper()
    if "-API" in t or t.endswith("API"):
        pass  # kiểm tra kỹ hơn bên dưới bằng file path — title dễ nhiễu
    fp = (file_path or "").lower()
    if ".api." in fp or "/api/" in fp or "\\api\\" in fp:
        return "api"
    if ".e2e." in fp or "/e2e/" in fp or "\\e2e\\" in fp:
        return "e2e"
    if "-API:" in (title or "").upper():
        return "api"
    if "-E2E:" in (title or "").upper():
        return "e2e"
    src = source_name.lower()
    if "api" in src:
        return "api"
    if "e2e" in src:
        return "e2e"
    if "maestro" in src or "mobile" in src or src.endswith(".xml"):
        return "mobile"
    return "e2e"  # default: E2E là final user-facing layer


def flatten_suites(suites: list) -> list:
    """Đệ quy gom mọi test spec trong cây suites của Playwright JSON reporter."""
    out = []
    for suite in suites or []:
        for spec in suite.get("specs", []):
            out.append(spec)
        if suite.get("suites"):
            out.extend(flatten_suites(suite["suites"]))
    return out


def parse_playwright_json(path: Path) -> list[dict]:
    """
    Parse Playwright JSON reporter output → list test record chuẩn.
    Hỗ trợ cả 2 shape: {"suites": [...]} (reporter chuẩn) và {"tests": [...]} (đã flat).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records: list[dict] = []

    # Shape 1: file đã flat sẵn (idempotent — cho phép flatten lại results_flat.json)
    if "tests" in data and "suites" not in data:
        for t in data["tests"]:
            if t.get("tc_id") or extract_tc_id(t.get("title", "")):
                records.append(dict(t))
        return records

    # Shape 2: Playwright JSON reporter chuẩn
    specs = flatten_suites(data.get("suites", []))
    for spec in specs:
        title = spec.get("title", "")
        file_path = spec.get("file", "")
        for test in spec.get("tests", []):
            results = test.get("results", [])
            # Status cuối cùng = result của attempt cuối
            final_status = results[-1].get("status", "") if results else test.get(
                "status", ""
            )
            # expectedStatus xử lý test.fixme/skip
            if test.get("status") == "skipped" or final_status == "skipped":
                final_status = "skipped"
            retries = max(0, len(results) - 1)
            pass_on_retry = (
                final_status == "passed"
                and retries > 0
                and any(r.get("status") in FAILED_STATUSES for r in results[:-1])
            )
            duration = sum(int(r.get("duration", 0) or 0) for r in results)
            error = ""
            for r in results:
                if r.get("status") in FAILED_STATUSES:
                    err = r.get("error") or {}
                    error = (err.get("message") or "")[:500]
            records.append(
                {
                    "tc_id": extract_tc_id(title),
                    "title": title,
                    "status": final_status,
                    "layer": detect_layer(title, file_path, path.name),
                    "file": file_path,
                    "duration_ms": duration,
                    "retries": retries,
                    "pass_on_retry": pass_on_retry,
                    "error": error,
                }
            )
    return records


def parse_maestro_junit(path: Path) -> list[dict]:
    """Parse Maestro JUnit XML (--format JUNIT) → list test record layer=mobile."""
    tree = ET.parse(path)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
    records: list[dict] = []
    for suite in suites:
        for case in suite.findall("testcase"):
            name = case.get("name", "")
            failure = case.find("failure")
            error_el = case.find("error")
            skipped = case.find("skipped")
            if skipped is not None:
                status = "skipped"
            elif failure is not None or error_el is not None:
                status = "failed"
            else:
                status = "passed"
            err_node = failure if failure is not None else error_el
            error = ""
            if err_node is not None:
                error = ((err_node.get("message") or "") + " " + (err_node.text or ""))[
                    :500
                ].strip()
            try:
                duration_ms = int(float(case.get("time", "0")) * 1000)
            except ValueError:
                duration_ms = 0
            records.append(
                {
                    "tc_id": extract_tc_id(name),
                    "title": name,
                    "status": status,
                    "layer": "mobile",
                    "file": str(path),
                    "duration_ms": duration_ms,
                    "retries": 0,
                    "pass_on_retry": False,
                    "error": error,
                }
            )
    return records


def build_summary(tests: list[dict]) -> dict:
    def bucket(subset):
        return {
            "total": len(subset),
            "passed": sum(1 for t in subset if t["status"] == "passed"),
            "failed": sum(1 for t in subset if t["status"] in FAILED_STATUSES),
            "skipped": sum(1 for t in subset if t["status"] == "skipped"),
        }

    summary = bucket(tests)
    summary["by_layer"] = {
        layer: bucket([t for t in tests if t.get("layer") == layer])
        for layer in sorted({t.get("layer", "") for t in tests})
        if layer
    }
    summary["flaky_pass_on_retry"] = sum(1 for t in tests if t.get("pass_on_retry"))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Gộp Playwright JSON (+ Maestro JUnit) → results_flat.json"
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Các file input Playwright JSON, file CUỐI CÙNG là output path",
    )
    parser.add_argument(
        "--maestro-junit",
        action="append",
        default=[],
        help="File JUnit XML từ Maestro (dùng nhiều lần được)",
    )
    args = parser.parse_args()

    if len(args.files) < 2:
        print(
            "❌ Cần ít nhất 1 input + 1 output: flatten_pw_results.py <in...> <out>",
            file=sys.stderr,
        )
        sys.exit(1)

    inputs = [Path(p) for p in args.files[:-1]]
    output = Path(args.files[-1])

    all_tests: list[dict] = []
    sources: list[dict] = []

    for p in inputs:
        if not p.exists():
            print(f"⚠️  Bỏ qua (không tồn tại — layer chưa chạy?): {p}", file=sys.stderr)
            continue
        try:
            recs = parse_playwright_json(p)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Bỏ qua (không parse được Playwright JSON): {p} — {e}", file=sys.stderr)
            continue
        sources.append({"file": str(p), "kind": "playwright", "tests": len(recs)})
        all_tests.extend(recs)

    for xml_path in args.maestro_junit:
        p = Path(xml_path)
        if not p.exists():
            print(f"⚠️  Bỏ qua Maestro JUnit (không tồn tại): {p}", file=sys.stderr)
            continue
        try:
            recs = parse_maestro_junit(p)
        except ET.ParseError as e:
            print(f"⚠️  Bỏ qua Maestro JUnit (XML lỗi): {p} — {e}", file=sys.stderr)
            continue
        sources.append({"file": str(p), "kind": "maestro-junit", "tests": len(recs)})
        all_tests.extend(recs)

    if not sources:
        print("❌ Không có input hợp lệ nào — không ghi output.", file=sys.stderr)
        sys.exit(1)

    # Dedup: cùng (tc_id, layer) giữ record cuối (run sau ghi đè run trước)
    seen: dict[tuple, dict] = {}
    no_id: list[dict] = []
    for t in all_tests:
        key = (t.get("tc_id", ""), t.get("layer", ""))
        if t.get("tc_id"):
            seen[key] = t
        else:
            no_id.append(t)  # giữ lại nhưng không dedup — cảnh báo bên dưới
    tests = list(seen.values()) + no_id

    if no_id:
        print(
            f"⚠️  {len(no_id)} test không có TC-ID trong title — "
            "kiểm tra naming convention 'TC-XXX-API/E2E: ...'",
            file=sys.stderr,
        )

    out_data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sources": sources,
        "tests": tests,
        "summary": build_summary(tests),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    s = out_data["summary"]
    print(
        f"✅ results_flat.json: {s['total']} TC "
        f"(pass {s['passed']} / fail {s['failed']} / skip {s['skipped']}) "
        f"→ {output}"
    )
    for layer, b in s["by_layer"].items():
        print(f"   {layer}: {b['passed']}/{b['total']} pass")
    if s.get("flaky_pass_on_retry"):
        print(
            f"   🔶 {s['flaky_pass_on_retry']} TC pass-on-retry (KHÔNG tính pass khi sign-off)"
        )


if __name__ == "__main__":
    main()
