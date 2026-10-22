#!/usr/bin/env python3
"""
generate_mock_server.py — Sinh Express mock server từ UAT endpoints.

Mục đích: Khi app target chưa chạy, runner spawn mock này lên port mặc định
để test Playwright vẫn execute được — verify code chạy, không verify business logic.

Logic:
- Đọc UAT data → tìm endpoints trong test_cases (regex /api/...)
- Sinh handlers default: 
  - GET → 200 với mock data
  - POST/PUT → 200/201
  - DELETE → 204
  - Auth endpoint → check credentials
  - 404 cho unknown

Usage:
    python generate_mock_server.py \
        --uat-data /tmp/uat_data.json \
        --port 3000 \
        -o tests/mock-server.js
"""

import argparse
import json
import re
import sys
from pathlib import Path


def extract_endpoints(uat_data):
    """Extract API endpoints từ test_cases (regex /api/...)."""
    endpoints = set()
    tcs = uat_data.get("test_cases", [])

    for tc in tcs:
        # Search trong steps + expected
        searchable = " ".join([
            tc.get("steps", ""),
            tc.get("expected_api", ""),
            tc.get("expected", ""),
            tc.get("test_data", ""),
        ])

        # Patterns: POST /api/path, GET /api/path
        matches = re.findall(r"(GET|POST|PUT|PATCH|DELETE)\s+(/[a-zA-Z][\w/\-:_]+)", searchable)
        for method, path in matches:
            endpoints.add((method.upper(), path))

    return sorted(endpoints)


def extract_credentials(uat_data):
    """Extract test credentials. Support Vietnamese key names."""
    accounts = uat_data.get("test_data", {}).get("accounts", [])
    
    def _get(acc, *keys):
        for k in keys:
            if acc.get(k):
                return acc[k]
        return None
    
    result = []
    for a in accounts:
        email = _get(a, "email", "Email")
        password = _get(a, "password", "mật_khẩu", "Mật khẩu", "Password")
        role = _get(a, "role", "vai_trò", "Vai trò", "Role") or "Customer"
        if email and password:
            result.append({"email": email, "password": password, "role": role})
    return result


def generate_handler(method, path, credentials):
    """Sinh JS handler cho 1 endpoint."""
    # Special handling
    is_auth = "login" in path.lower() or "auth" in path.lower()
    is_register = "register" in path.lower() or "signup" in path.lower()

    if is_auth and method == "POST":
        creds_js = json.dumps(credentials or [
            {"email": "test@test.com", "password": "Test@1234", "role": "Customer"}
        ])
        return f"""
app.{method.lower()}('{path}', (req, res) => {{
  const credentials = {creds_js};
  const {{ email, password }} = req.body;
  const matched = credentials.find(c => c.email === email && c.password === password);
  if (matched) {{
    return res.status(200).json({{
      token: 'mock-jwt-token-' + Date.now(),
      user: {{ id: 1, email: matched.email, role: matched.role }}
    }});
  }}
  res.status(401).json({{ error: 'INVALID_CREDENTIALS', message: 'Email hoặc mật khẩu không đúng' }});
}});"""

    if is_register and method == "POST":
        return f"""
app.{method.lower()}('{path}', (req, res) => {{
  const {{ email, password }} = req.body;
  if (!email || !password) {{
    return res.status(400).json({{ error: 'MISSING_FIELDS' }});
  }}
  if (email === 'existing@test.com') {{
    return res.status(409).json({{ error: 'EMAIL_EXISTS', message: 'Email đã được đăng ký' }});
  }}
  res.status(201).json({{
    user_id: Date.now(),
    email: email,
    status: 'pending'
  }});
}});"""

    # SQL injection detection mock
    if method == "POST":
        return f"""
app.{method.lower()}('{path}', (req, res) => {{
  // Check for SQL injection patterns (mock security)
  const bodyStr = JSON.stringify(req.body);
  if (/(\\bOR\\s+['"]?1['"]?\\s*=\\s*['"]?1|DROP\\s+TABLE|UNION\\s+SELECT|--\\s*$)/i.test(bodyStr)) {{
    return res.status(400).json({{ error: 'INVALID_INPUT', message: 'Dữ liệu không hợp lệ' }});
  }}
  // Check for XSS
  if (/<script|javascript:|onerror=/i.test(bodyStr)) {{
    return res.status(400).json({{ error: 'INVALID_INPUT' }});
  }}
  res.status(201).json({{ id: Date.now(), ...req.body, _mock: true }});
}});"""

    if method == "GET":
        return f"""
app.{method.lower()}('{path}', (req, res) => {{
  res.status(200).json({{ data: [], _mock: true, path: '{path}' }});
}});"""

    if method == "PUT" or method == "PATCH":
        return f"""
app.{method.lower()}('{path}', (req, res) => {{
  res.status(200).json({{ updated: true, ...req.body, _mock: true }});
}});"""

    if method == "DELETE":
        return f"""
app.{method.lower()}('{path}', (req, res) => {{
  res.status(204).end();
}});"""

    return f"""
app.{method.lower()}('{path}', (req, res) => {{
  res.status(200).json({{ _mock: true }});
}});"""


def generate_mock_server(uat_data, port=3000):
    """Sinh full mock-server.js."""
    endpoints = extract_endpoints(uat_data)
    credentials = extract_credentials(uat_data)

    feature_name = uat_data.get("feature_name", "Mock UAT")

    # Auto-add common endpoints nếu UAT không có
    common = [
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/user/me"),
    ]
    existing_paths = {(m, p) for m, p in endpoints}
    for m, p in common:
        if (m, p) not in existing_paths:
            endpoints.append((m, p))

    handlers = "\n".join(generate_handler(m, p, credentials) for m, p in endpoints)

    js_code = f"""// Auto-generated mock server cho UAT
// Feature: {feature_name}
// Generated by uat-test-runner skill
// 
// ⚠️  WARNING: Đây là MOCK SERVER, không phải app thật.
// Test PASS không có nghĩa app thật cũng PASS.
// Dùng khi app target chưa lên/không accessible.

const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json({{ limit: '10mb' }}));

// Logging
app.use((req, res, next) => {{
  console.log(`[MOCK] ${{req.method}} ${{req.path}}`);
  next();
}});

// Health check
app.get('/', (req, res) => {{
  res.json({{ status: 'MOCK_SERVER_RUNNING', feature: '{feature_name}' }});
}});

app.get('/health', (req, res) => {{
  res.json({{ status: 'ok', _mock: true }});
}});

// === Auto-generated endpoints from UAT ===
{handlers}

// 404 fallback
app.use((req, res) => {{
  res.status(404).json({{ error: 'NOT_FOUND', path: req.path, _mock: true }});
}});

// Error handler
app.use((err, req, res, next) => {{
  console.error('[MOCK ERROR]', err);
  res.status(500).json({{ error: 'INTERNAL_ERROR', _mock: true }});
}});

const PORT = process.env.PORT || {port};
app.listen(PORT, () => {{
  console.log(`🎭 Mock server đang chạy tại http://localhost:${{PORT}}`);
  console.log(`   Endpoints: {len(endpoints)} routes`);
  console.log(`   Test credentials: {len(credentials)} accounts từ UAT`);
}});
"""

    return js_code, endpoints, credentials


def main():
    parser = argparse.ArgumentParser(description="Generate mock server từ UAT")
    parser.add_argument("--uat-data", required=True)
    parser.add_argument("--port", type=int, default=3000)
    parser.add_argument("-o", "--output", default="tests/mock-server.js")
    args = parser.parse_args()

    with open(args.uat_data, "r", encoding="utf-8") as f:
        uat_data = json.load(f)

    js_code, endpoints, credentials = generate_mock_server(uat_data, port=args.port)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(js_code, encoding="utf-8")

    print(f"✅ Mock server: {args.output}", file=sys.stderr)
    print(f"   Endpoints: {len(endpoints)}", file=sys.stderr)
    for m, p in endpoints:
        print(f"     {m} {p}", file=sys.stderr)
    print(f"   Credentials: {len(credentials)}", file=sys.stderr)
    print(f"\n💡 Để chạy mock server:", file=sys.stderr)
    print(f"   cd tests && npm install express cors", file=sys.stderr)
    print(f"   node {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
