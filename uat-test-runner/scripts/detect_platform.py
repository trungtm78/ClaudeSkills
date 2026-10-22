#!/usr/bin/env python3
"""Detect platform multi-label cho UAT (Gate 0) -> docs/uat/_platform.json.

Cung logic voi uat-test-writer/references/platform-detection.md.
Multi-label: mot repo co the vua WEB vua ANDROID vua API. Monorepo -> recurse per package.

Usage:
    python detect_platform.py [repo_root] [-o docs/uat/_platform.json]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WEB_FRAMEWORKS = ("next", "vite", "react", "vue", "angular", "svelte", "nuxt", "remix", "astro")
API_MARKERS = ("openapi.yaml", "openapi.json", "swagger.yaml", "swagger.json",
               "nest-cli.json", "manage.py", "pom.xml", "go.mod")
MONOREPO_MARKERS = ("pnpm-workspace.yaml", "turbo.json", "nx.json", "lerna.json")


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_text(path):
    try:
        # utf-8-sig: tu strip BOM (file .env tao tren Windows hay co BOM)
        return Path(path).read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""


def detect_package(pkg_dir: Path):
    """Tra ve (labels, evidence, extras) cho MOT package/thu muc."""
    labels, evidence, extras = [], [], {}

    # 1. FLUTTER
    pubspec = pkg_dir / "pubspec.yaml"
    if pubspec.exists() and re.search(r"^\s*flutter\s*:", read_text(pubspec), re.M):
        labels.append("FLUTTER")
        evidence.append(str(pubspec))

    # 2. HYBRID_WEBVIEW (Capacitor / Cordova / Tauri mobile)
    for marker in ("capacitor.config.ts", "capacitor.config.json", "capacitor.config.js", "config.xml"):
        p = pkg_dir / marker
        if p.exists():
            labels.extend(["HYBRID_WEBVIEW", "WEB"])
            evidence.append(str(p))
            break

    # 3. RN / EXPO
    pkg_json = read_json(pkg_dir / "package.json")
    deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}
    if "react-native" in deps:
        labels.append("RN")
        evidence.append(str(pkg_dir / "package.json") + " (react-native)")
        if "expo" in deps or (pkg_dir / "app.json").exists() or (pkg_dir / "eas.json").exists():
            labels.append("EXPO")

    # 4. IOS native (bo qua thu muc ios/ cua Flutter/RN — chi tinh khi khong co label tren)
    if not any(l in labels for l in ("FLUTTER", "RN", "HYBRID_WEBVIEW")):
        xcode = list(pkg_dir.glob("*.xcodeproj")) + list(pkg_dir.glob("*.xcworkspace")) \
            + list(pkg_dir.glob("ios/*.xcodeproj"))
        if xcode:
            labels.append("IOS")
            evidence.append(str(xcode[0]))

    # 5. ANDROID native
    if not any(l in labels for l in ("FLUTTER", "RN", "HYBRID_WEBVIEW")):
        settings = next((p for p in (pkg_dir / "settings.gradle", pkg_dir / "settings.gradle.kts")
                         if p.exists()), None)
        manifest = list(pkg_dir.glob("app/src/main/AndroidManifest.xml"))
        if settings and manifest:
            labels.append("ANDROID")
            evidence.append(str(settings))

    # Flutter/RN co app mobile that -> them ANDROID/IOS target
    if any(l in labels for l in ("FLUTTER", "RN")):
        if (pkg_dir / "android").is_dir() or "FLUTTER" in labels or "EXPO" in labels:
            labels.append("ANDROID")
        if (pkg_dir / "ios").is_dir() or "FLUTTER" in labels or "EXPO" in labels:
            labels.append("IOS")

    # 6. WEB thuan
    if "WEB" not in labels and not any(l in labels for l in ("FLUTTER", "RN")):
        if any(k in deps for k in WEB_FRAMEWORKS) or (pkg_dir / "index.html").exists():
            labels.append("WEB")
            evidence.append(str(pkg_dir / "package.json") + " (web framework)")

    # 7. API (label doc lap, cong them)
    for marker in API_MARKERS:
        p = pkg_dir / marker
        if p.exists():
            labels.append("API")
            evidence.append(str(p))
            break
    if "API" not in labels and (pkg_dir / "prisma" / "schema.prisma").exists():
        labels.append("API")
        evidence.append(str(pkg_dir / "prisma" / "schema.prisma"))

    # appId
    app_id = {}
    gradle = read_text(pkg_dir / "android" / "app" / "build.gradle") or \
        read_text(pkg_dir / "app" / "build.gradle") or \
        read_text(pkg_dir / "android" / "app" / "build.gradle.kts")
    m = re.search(r'applicationId\s*[=(]?\s*["\']([\w.]+)["\']', gradle)
    if m:
        app_id["android"] = m.group(1)
    for pbx in list(pkg_dir.glob("ios/*.xcodeproj/project.pbxproj")) + \
            list(pkg_dir.glob("*.xcodeproj/project.pbxproj")):
        m = re.search(r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*([\w.\-]+)', read_text(pbx))
        if m:
            app_id["ios"] = m.group(1)
            break
    if app_id:
        extras["appId"] = app_id

    # buildCmds goi y
    build_cmds = {}
    if "FLUTTER" in labels:
        build_cmds = {"android": "flutter build apk --debug",
                      "ios": "flutter build ios --simulator"}
        extras["artifacts"] = {"android": "build/app/outputs/flutter-apk/app-debug.apk"}
    elif "EXPO" in labels:
        build_cmds = {"android": "npx expo run:android"}
    elif "RN" in labels:
        build_cmds = {"android": "cd android && gradlew assembleDebug"}
        extras["artifacts"] = {"android": "android/app/build/outputs/apk/debug/app-debug.apk"}
    elif "ANDROID" in labels:
        build_cmds = {"android": "gradlew assembleDebug"}
    if build_cmds:
        extras["buildCmds"] = build_cmds

    return sorted(set(labels)), evidence, extras


def detect_host():
    host = {"os": sys.platform,
            "hasAdb": shutil.which("adb") is not None,
            "hasJava17": False,
            "hasMaestro": shutil.which("maestro") is not None,
            "hasXcode": shutil.which("xcodebuild") is not None,
            "iosPossible": sys.platform == "darwin"}
    try:
        out = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=15)
        m = re.search(r'version "(\d+)', out.stderr or out.stdout)
        host["hasJava17"] = bool(m and int(m.group(1)) >= 17)
    except Exception:
        pass
    return host


def list_devices():
    devices = []
    if shutil.which("adb"):
        try:
            out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=15)
            for line in out.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append({"id": parts[0], "platform": "android"})
        except Exception:
            pass
    return devices


def api_base_url(repo: Path):
    for env_file in (".env", ".env.test", ".env.local"):
        content = read_text(repo / env_file)
        m = re.search(r'^(?:API_URL|BASE_URL|API_BASE_URL)\s*=\s*(\S+)', content, re.M)
        if m:
            return m.group(1).strip('"\'')
    return "http://localhost:3000"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("-o", "--output", default="docs/uat/_platform.json")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    # Monorepo: recurse per package roi union
    package_dirs = [root]
    if any((root / m).exists() for m in MONOREPO_MARKERS) or read_json(root / "package.json").get("workspaces"):
        for sub in ("apps", "packages", "services"):
            d = root / sub
            if d.is_dir():
                package_dirs.extend(p for p in d.iterdir() if p.is_dir())

    packages, all_labels, merged_extras = [], set(), {}
    for pkg in package_dirs:
        labels, evidence, extras = detect_package(pkg)
        if labels:
            packages.append({"path": str(pkg.relative_to(root)) or ".",
                             "labels": labels, "evidence": evidence})
            all_labels.update(labels)
            for k, v in extras.items():
                merged_extras.setdefault(k, {}).update(v if isinstance(v, dict) else {})

    host = detect_host()
    base = api_base_url(root)
    blockers = []
    if "IOS" in all_labels and not host["iosPossible"]:
        blockers.append({"platform": "ios", "reason": "no macOS host",
                         "remediation": ["github-actions macos-latest workflow",
                                         "maestro cloud", "browserstack app automate"]})
    if any(l in all_labels for l in ("ANDROID", "FLUTTER", "RN")) and not host["hasAdb"]:
        blockers.append({"platform": "android", "reason": "adb not found (Android SDK missing)",
                         "remediation": ["install Android SDK platform-tools",
                                         "cloud device farm"]})

    contract = {
        "platforms": sorted(all_labels),
        "packages": packages,
        "appId": merged_extras.get("appId", {}),
        "buildCmds": merged_extras.get("buildCmds", {}),
        "artifacts": merged_extras.get("artifacts", {}),
        "apiBaseUrl": base,
        "apiBaseUrlForAndroidEmulator": re.sub(r"//(localhost|127\.0\.0\.1)", "//10.0.2.2", base),
        "recommendedStack": {
            "web": "playwright" if {"WEB", "HYBRID_WEBVIEW"} & all_labels else None,
            "mobile": "maestro" if {"ANDROID", "IOS", "FLUTTER", "RN"} & all_labels else None,
            "api": "playwright-request" if "API" in all_labels else None,
        },
        "host": host,
        "devices": list_devices(),
        "blockers": blockers,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK: {out} -> platforms={contract['platforms']} blockers={len(blockers)}")


if __name__ == "__main__":
    main()
