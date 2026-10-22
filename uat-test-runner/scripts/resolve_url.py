#!/usr/bin/env python3
"""
resolve_url.py — Tier-based fallback chain để xác định URL base của app.

Tier 1: ENV BASE_URL hoặc PLAYWRIGHT_BASE_URL
Tier 2: Parse package.json scripts (next dev -p, vite --port, react-scripts start)
Tier 3: Default http://localhost:3000

Sau khi resolve, ping URL để check app có listen không.
Nếu không → return suggest_mock=True để runner biết cần spawn mock.

Usage:
    python resolve_url.py
    python resolve_url.py --cwd /path/to/repo -o /tmp/url.json
"""

import argparse
import json
import os
import re
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse


def tier_1_env(cwd=None):
    """Đọc env BASE_URL / PLAYWRIGHT_BASE_URL."""
    for key in ["BASE_URL", "PLAYWRIGHT_BASE_URL", "APP_URL", "TEST_URL", "E2E_BASE_URL"]:
        val = os.getenv(key)
        if val:
            return {"url": val, "source": f"tier_1_env_{key}"}

    # Cũng đọc từ .env files
    for env_name in [".env.test", ".env.local", ".env"]:
        env_path = Path(cwd or os.getcwd()) / env_name
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k in ["BASE_URL", "PLAYWRIGHT_BASE_URL", "APP_URL", "NEXT_PUBLIC_API_URL"]:
                                if v:
                                    return {"url": v, "source": f"tier_1_dotenv_{k}"}
            except Exception:
                pass
    return None


def tier_2_package_json(cwd=None):
    """Parse package.json scripts để tìm port."""
    cwd = Path(cwd or os.getcwd())
    pkg = cwd / "package.json"
    if not pkg.exists():
        return None

    try:
        with open(pkg, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    scripts = data.get("scripts", {})
    # Patterns to extract port
    port_patterns = [
        r"-p\s+(\d+)",                # next dev -p 3001
        r"--port[=\s]+(\d+)",         # vite --port=3001
        r"PORT=(\d+)",                 # PORT=3001 next dev
        r"--port=(\d+)",
    ]

    # Look for dev/start/serve scripts
    candidates = ["dev", "start", "serve", "start:dev", "dev:server"]
    for cmd_name in candidates:
        if cmd_name in scripts:
            cmd = scripts[cmd_name]
            for pattern in port_patterns:
                m = re.search(pattern, cmd)
                if m:
                    port = m.group(1)
                    return {
                        "url": f"http://localhost:{port}",
                        "source": f"tier_2_package_json_{cmd_name}",
                    }

    # Framework defaults
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    if "next" in deps:
        return {"url": "http://localhost:3000", "source": "tier_2_next_default"}
    if "vite" in deps:
        return {"url": "http://localhost:5173", "source": "tier_2_vite_default"}
    if "vue" in deps or "@vue/cli-service" in deps:
        return {"url": "http://localhost:8080", "source": "tier_2_vue_default"}
    if "react-scripts" in deps:
        return {"url": "http://localhost:3000", "source": "tier_2_cra_default"}
    if "@angular/core" in deps:
        return {"url": "http://localhost:4200", "source": "tier_2_angular_default"}
    if "svelte" in deps or "@sveltejs/kit" in deps:
        return {"url": "http://localhost:5173", "source": "tier_2_svelte_default"}

    return None


def tier_3_default():
    """Default mặc định."""
    return {"url": "http://localhost:3000", "source": "tier_3_default"}


def check_port_listening(url, timeout=2):
    """Check xem URL có app listen không."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def resolve_url(cwd=None):
    """Run 3-tier fallback + check liveness."""
    result = tier_1_env(cwd)
    if not result:
        result = tier_2_package_json(cwd)
    if not result:
        result = tier_3_default()

    # Check app alive
    is_alive = check_port_listening(result["url"])
    result["app_running"] = is_alive
    result["suggest_mock"] = not is_alive

    if not is_alive:
        result["warning"] = (
            f"App tại {result['url']} không response. "
            "Runner sẽ auto-spawn mock server để vẫn chạy test."
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="Resolve app URL via 3-tier fallback")
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    result = resolve_url(cwd=args.cwd)

    print(f"🌐 URL resolved via: {result['source']}", file=sys.stderr)
    print(f"   URL: {result['url']}", file=sys.stderr)
    print(f"   App running: {'✅ Yes' if result['app_running'] else '❌ No'}", file=sys.stderr)
    if result.get("warning"):
        print(f"   ⚠️  {result['warning']}", file=sys.stderr)
    if result.get("suggest_mock"):
        print(f"   💡 Runner should spawn mock server", file=sys.stderr)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"✅ Ghi: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
