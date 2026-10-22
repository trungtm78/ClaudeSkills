#!/usr/bin/env python3
"""Sinh Maestro flow YAML tu uat.json (TC co platform=android|ios) -> .maestro/<feature>/.

Moi TC = 1 file TC-xxx.yaml (skeleton dung chuan mobile-runner.md):
clearState -> launchApp(permissions explicit) -> startRecording -> steps (TODO comment
tu steps cua TC de Claude dien locator that sau reconnaissance) -> >=3 assertion -> stopRecording.

Usage:
    python generate_maestro_flows.py uat.json --app-id com.acme.app -o .maestro/<feature>
"""
import argparse
import json
import re
from pathlib import Path

HEADER_KEYS = ("PERMISSIONS", "OFFLINE", "DEEPLINK", "LIFECYCLE")


def slug(s: str) -> str:
    return re.sub(r"[^\w\-]", "-", s)[:60]


def yaml_quote(s: str) -> str:
    s = (s or "").replace('"', "'").strip()
    return f'"{s}"'


def build_flow(tc: dict, app_id: str) -> str:
    tc_id = tc.get("tc_id", "TC-XXX")
    tc_type = (tc.get("type") or "").upper()
    tags = [t for t in (tc.get("priority"), tc.get("severity_if_fail"),
                        tc.get("journey_ref")) if t]

    lines = [
        f"# {tc_id}: {tc.get('title', '')}",
        f"# persona: {tc.get('persona', '?')} | oracle: {tc.get('oracle_type', '?')} -> {tc.get('rule_ref', '?')}",
        f"# catches_bug: {tc.get('catches_bug', '(chua khai bao)')}",
        f"appId: {app_id}",
    ]
    if tags:
        lines.append(f"tags: [{', '.join(slug(str(t)) for t in tags)}]")
    lines.append("---")

    # LIFECYCLE giu state -> khong clearState
    if tc_type != "LIFECYCLE":
        lines.append("- clearState")

    # Permissions explicit theo loai TC
    if tc_type == "PERMISSIONS":
        lines += ["- launchApp:",
                  "    permissions: { all: deny }   # TODO: chinh grant/deny theo tung case"]
    else:
        lines += ["- launchApp:",
                  "    permissions: { all: allow }"]

    lines.append(f"- startRecording: {tc_id}   # cap ~3 phut, journey dai chia chunk")

    if tc_type == "OFFLINE":
        lines.append("- setAirplaneMode: enabled   # TODO: bat/tat theo buoc TC")
    if tc_type == "DEEPLINK":
        lines.append("- openLink: myapp://TODO-path   # TODO: link tu TC")

    lines.append(f"- takeScreenshot: {tc_id}-given")

    # Steps: dat TODO comment tu steps cua TC — Claude dien lenh that
    # (tapOn/inputText voi locator tu locator_hint + reconnaissance; KHONG doan selector)
    steps = (tc.get("steps") or "").strip().splitlines()
    hint = tc.get("locator_hint") or ""
    if hint:
        lines.append(f"# locator_hint: {hint}")
    for step in steps:
        step = step.strip()
        if step:
            lines.append(f"# TODO step: {step}")
    lines.append("# TODO: thay TODO step bang tapOn/inputText/scrollUntilVisible... "
                 "(uu tien accessibility label/text; khong tim thay = a11y defect)")

    lines.append(f"- takeScreenshot: {tc_id}-when")

    # >=3 assertion tu expected
    expected = (tc.get("expected") or "").strip().replace("\n", " ")[:120]
    lines += [
        "# >=3 assertion: screen identity + element + text/data (mirror rule web)",
        f"- assertVisible: {yaml_quote(expected[:60] or 'TODO-man-hinh-ket-qua')}   # TODO 1: screen identity",
        "# TODO 2: assertVisible element nghiep vu (id: tu testID neu co)",
        "# TODO 3: assertVisible text/data dung theo oracle_source",
        f"- takeScreenshot: {tc_id}-then",
        "- stopRecording",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("uat_json")
    ap.add_argument("--app-id", default=None, help="override appId (mac dinh doc _platform.json)")
    ap.add_argument("--platform-json", default="docs/uat/_platform.json")
    ap.add_argument("-o", "--output-dir", default=".maestro/uat")
    args = ap.parse_args()

    data = json.loads(Path(args.uat_json).read_text(encoding="utf-8-sig"))
    tcs = data.get("test_cases", data if isinstance(data, list) else [])

    app_id = args.app_id
    if not app_id:
        try:
            plat = json.loads(Path(args.platform_json).read_text(encoding="utf-8-sig"))
            app_id = plat.get("appId", {}).get("android") or plat.get("appId", {}).get("ios")
        except Exception:
            pass
    if not app_id:
        raise SystemExit("ERROR: khong co appId — truyen --app-id hoac chay detect_platform.py truoc")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mobile_tcs = [tc for tc in tcs if (tc.get("platform") or "").lower() in ("android", "ios", "mobile")]
    if not mobile_tcs:
        print("Khong co TC platform=android|ios trong uat.json — bo qua Gate 3")
        return

    count = 0
    for tc in mobile_tcs:
        tc_id = tc.get("tc_id") or f"TC-{count + 1:03d}"
        (out_dir / f"{slug(tc_id)}.yaml").write_text(build_flow(tc, app_id), encoding="utf-8")
        count += 1

    # config.yaml cua workspace (hooks login/seed dung chung)
    config = out_dir / "config.yaml"
    if not config.exists():
        config.write_text(f"appId: {app_id}\n# onFlowStart:\n#   - runFlow: common/login.yaml\n",
                          encoding="utf-8")

    print(f"OK: {count} flow YAML -> {out_dir} (appId={app_id})")
    print("LUU Y: cac flow chua TODO — dien locator that sau reconnaissance "
          "(maestro mcp inspect_screen / maestro hierarchy), roi moi chay gate.")


if __name__ == "__main__":
    main()
