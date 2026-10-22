#!/usr/bin/env python3
"""
resolve_credentials.py — Tier-based fallback chain để lấy credential test.

Tier 1: test_data.accounts trong UAT file (đã parse sẵn)
Tier 2: .env file của repo (TEST_USER_EMAIL, TEST_USER_PASSWORD, ADMIN_EMAIL...)
Tier 3: Mock default (test@test.com / Test@1234)

KHÔNG hỏi user. KHÔNG dừng. LUÔN trả về credential để runner có thể chạy.

Usage:
    # Lấy default account
    python resolve_credentials.py --uat-data /tmp/uat_data.json
    
    # Lấy account theo role
    python resolve_credentials.py --uat-data /tmp/uat_data.json --role admin
    
    # Output JSON file
    python resolve_credentials.py --uat-data /tmp/uat_data.json -o /tmp/creds.json
"""

import argparse
import json
import os
import sys
from pathlib import Path


# Common env var patterns
ENV_PATTERNS = {
    "email_keys": ["TEST_USER_EMAIL", "TEST_EMAIL", "E2E_EMAIL", "PLAYWRIGHT_EMAIL", "TEST_USERNAME"],
    "password_keys": ["TEST_USER_PASSWORD", "TEST_PASSWORD", "E2E_PASSWORD", "PLAYWRIGHT_PASSWORD"],
    "admin_email_keys": ["ADMIN_EMAIL", "TEST_ADMIN_EMAIL", "E2E_ADMIN_EMAIL"],
    "admin_password_keys": ["ADMIN_PASSWORD", "TEST_ADMIN_PASSWORD", "E2E_ADMIN_PASSWORD"],
}

MOCK_DEFAULTS = {
    "default": {"email": "test@test.com", "password": "Test@1234", "role": "Customer"},
    "admin": {"email": "admin@test.com", "password": "Admin@1234", "role": "Admin"},
    "user": {"email": "user@test.com", "password": "User@1234", "role": "Customer"},
}


def tier_1_from_uat_data(uat_data, role=None):
    """Lấy từ test_data.accounts. Support cả Vietnamese key (mật_khẩu) lẫn English (password)."""
    accounts = uat_data.get("test_data", {}).get("accounts", [])
    if not accounts:
        return None

    def _get_field(acc, *keys):
        """Try multiple key names, return first non-empty."""
        for k in keys:
            if acc.get(k):
                return acc[k]
        return ""

    def _email(acc):
        return _get_field(acc, "email", "Email")

    def _password(acc):
        return _get_field(acc, "password", "mật_khẩu", "Mật khẩu", "Password")

    def _role(acc):
        return _get_field(acc, "role", "vai_trò", "Vai trò", "Role")

    # Filter by role nếu có
    if role:
        filtered = [a for a in accounts if _role(a).lower() == role.lower()]
        if filtered:
            account = filtered[0]
        else:
            account = accounts[0]
    else:
        account = accounts[0]

    email_val = _email(account)
    pwd_val = _password(account)

    if email_val and pwd_val:
        return {
            "email": email_val,
            "password": pwd_val,
            "role": _role(account) or "Customer",
            "source": "tier_1_uat_file",
        }
    return None


def tier_2_from_dotenv(cwd=None, role=None):
    """Đọc .env hoặc .env.test trong repo."""
    cwd = Path(cwd or os.getcwd())

    # Search .env files
    env_files = [".env.test", ".env.local", ".env", ".env.example"]
    env_vars = {}

    for env_name in env_files:
        env_path = cwd / env_name
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            # Strip quotes
                            v = v.strip().strip('"').strip("'")
                            env_vars[k.strip()] = v
            except Exception as e:
                print(f"⚠️  Lỗi đọc {env_path}: {e}", file=sys.stderr)

    # Cũng include os.environ
    env_vars.update({k: v for k, v in os.environ.items()
                     if any(k.startswith(p) for p in ["TEST_", "E2E_", "PLAYWRIGHT_", "ADMIN_"])})

    if not env_vars:
        return None

    # Try keys theo role
    if role and role.lower() == "admin":
        email_keys = ENV_PATTERNS["admin_email_keys"]
        pwd_keys = ENV_PATTERNS["admin_password_keys"]
    else:
        email_keys = ENV_PATTERNS["email_keys"]
        pwd_keys = ENV_PATTERNS["password_keys"]

    email = next((env_vars[k] for k in email_keys if k in env_vars and env_vars[k]), None)
    pwd = next((env_vars[k] for k in pwd_keys if k in env_vars and env_vars[k]), None)

    if email and pwd:
        return {
            "email": email,
            "password": pwd,
            "role": role or "Customer",
            "source": "tier_2_dotenv",
        }
    return None


def tier_3_mock_default(role=None):
    """Mock credential mặc định."""
    key = (role or "default").lower()
    if key == "admin":
        cred = MOCK_DEFAULTS["admin"]
    else:
        cred = MOCK_DEFAULTS.get(key, MOCK_DEFAULTS["default"])

    return {
        **cred,
        "source": "tier_3_mock_default",
        "warning": "Mock credential - không phải user thật. Test PASS không guarantee real flow.",
    }


def resolve_credentials(uat_data=None, role=None, cwd=None):
    """3-tier fallback chain."""
    # Tier 1
    if uat_data:
        result = tier_1_from_uat_data(uat_data, role=role)
        if result:
            return result

    # Tier 2
    result = tier_2_from_dotenv(cwd=cwd, role=role)
    if result:
        return result

    # Tier 3
    return tier_3_mock_default(role=role)


def main():
    parser = argparse.ArgumentParser(description="Resolve credentials via 3-tier fallback")
    parser.add_argument("--uat-data", help="JSON file từ read_excel_uat.py")
    parser.add_argument("--role", help="Lọc theo role (admin, customer, ...)")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working dir để tìm .env")
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    args = parser.parse_args()

    uat_data = None
    if args.uat_data:
        try:
            with open(args.uat_data, "r", encoding="utf-8") as f:
                uat_data = json.load(f)
        except Exception as e:
            print(f"⚠️  Không đọc được {args.uat_data}: {e}", file=sys.stderr)

    result = resolve_credentials(uat_data=uat_data, role=args.role, cwd=args.cwd)

    print(f"🔑 Credential resolved via: {result['source']}", file=sys.stderr)
    print(f"   Email: {result['email']}", file=sys.stderr)
    print(f"   Role: {result.get('role', 'N/A')}", file=sys.stderr)
    if result.get("warning"):
        print(f"   ⚠️  {result['warning']}", file=sys.stderr)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"✅ Ghi: {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
