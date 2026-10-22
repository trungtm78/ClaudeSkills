#!/usr/bin/env python3
"""
generate_data_factory.py — Sinh TypeScript data factory từ data_fixtures.

Đầu vào: file JSON từ read_excel_uat.py (có field data_fixtures[])
Đầu ra: tests/fixtures/data-factory.ts với các function setup/cleanup
        + tests/fixtures/fixture-types.ts (type definitions)

Mỗi fixture được map sang 2 functions:
- setup<FixtureId>() — chạy setup_recipe, trả về output object
- cleanup<FixtureId>(ctx) — chạy cleanup_recipe với context

Runner dùng trong beforeEach/afterEach của spec.

Usage:
    python generate_data_factory.py /tmp/uat_data.json -o tests/fixtures/data-factory.ts
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def to_camel_case(fixture_id: str) -> str:
    """user.pending.D0 → userPendingD0"""
    parts = re.split(r'[._-]+', fixture_id)
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def to_pascal_case(fixture_id: str) -> str:
    """user.pending.D0 → UserPendingD0"""
    name = to_camel_case(fixture_id)
    return name[0].upper() + name[1:] if name else ""


def render_template_value(value):
    """Convert Python value → JavaScript literal với template substitution."""
    if isinstance(value, str):
        # Process templates BEFORE escaping the string
        # The result will have backtick-string interpolations like ${randomHex()}
        processed = value
        
        # {{random}} → ${randomHex()}
        processed = re.sub(r'\{\{random\}\}', '${randomHex()}', processed)
        # {{uuid}} → ${randomUuid()}
        processed = re.sub(r'\{\{uuid\}\}', '${randomUuid()}', processed)
        # {{now}} → ${nowISO()}
        processed = re.sub(r'\{\{now\}\}', '${nowISO()}', processed)
        # {{today}} → ${todayStr()}
        processed = re.sub(r'\{\{today\}\}', '${todayStr()}', processed)
        # {{D+N}} or {{D-N}}
        processed = re.sub(r'\{\{D([+\-])(\d+)\}\}', r'${daysOffsetISO(\1\2)}', processed)
        # {{user_id}} or {{any_id}} → ctx variables
        processed = re.sub(r'\{\{([a-zA-Z_]+)\}\}', r'${ctx.\1}', processed)
        # {{env.VARNAME}}
        processed = re.sub(r'\{\{env\.([A-Z_]+)\}\}', r'${process.env.\1}', processed)
        
        # If processed contains ${...} use backtick string
        if '${' in processed:
            # Escape any backticks in the original
            escaped = processed.replace('`', '\\`').replace('\\', '\\\\').replace('\\${', '${')
            # Re-fix escaped ${
            return f"`{processed}`"
        else:
            # Plain string
            return json.dumps(value)
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif value is None:
        return "null"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, list):
        items = [render_template_value(v) for v in value]
        return f"[{', '.join(items)}]"
    elif isinstance(value, dict):
        return render_payload(value)
    return json.dumps(value)


def render_payload(payload: dict) -> str:
    """Render dict thành JS object literal với template substitution."""
    if not payload:
        return "{}"
    parts = []
    for k, v in payload.items():
        parts.append(f'    "{k}": {render_template_value(v)}')
    return "{\n" + ",\n".join(parts) + "\n  }"


def generate_setup_function(fixture: dict) -> str:
    """Generate setup function for 1 fixture."""
    fid = fixture["fixture_id"]
    name = to_pascal_case(fid)
    setup = fixture.get("setup_recipe", {})
    # Chấp nhận shorthand string "POST /api/xxx" → normalize về dict {type:api, endpoint}
    if isinstance(setup, str):
        setup = {"type": "api", "endpoint": setup.strip()}
    setup_type = setup.get("type", "api") if isinstance(setup, dict) else "api"
    outputs = fixture.get("outputs", {})

    lines = []
    lines.append(f"/**")
    lines.append(f" * Setup fixture: {fid}")
    lines.append(f" * {fixture.get('description', '')}")
    lines.append(f" * State: {fixture.get('state')} | Lifecycle: {fixture.get('lifecycle')} | Shape: {fixture.get('shape')}")
    lines.append(f" */")
    lines.append(f"export async function setup{name}(ctx: FixtureCtx = {{}}): Promise<FixtureResult> {{")

    if setup_type == "api":
        endpoint = setup.get("endpoint", "")
        method_match = re.match(r"(GET|POST|PUT|PATCH|DELETE)\s+(.+)", endpoint)
        if method_match:
            method, path = method_match.group(1).lower(), method_match.group(2)
        else:
            method, path = "post", endpoint

        # Template substitute path
        path_processed = re.sub(r'\{\{([a-zA-Z_]+)\}\}', r'${ctx.\1}', path)
        if '${' in path_processed:
            path_js = f"`{path_processed}`"
        else:
            path_js = json.dumps(path)

        payload = setup.get("payload", {})
        headers = setup.get("headers", {})

        lines.append(f"  const path = {path_js};")
        if headers:
            lines.append(f"  const headers = {render_payload(headers)};")
            lines.append(f"  const response = await apiRequest('{method}', path, {render_payload(payload)}, headers);")
        else:
            lines.append(f"  const response = await apiRequest('{method}', path, {render_payload(payload)});")
        lines.append(f"  if (!response.ok) {{")
        lines.append(f"    throw new Error(`Setup fixture {fid} failed: ${{response.status}} ${{response.body}}`);")
        lines.append(f"  }}")
        lines.append(f"  const body = response.body;")

    elif setup_type == "sql":
        connection_env = setup.get("connection_env", "TEST_DATABASE_URL")
        queries = setup.get("queries", [])
        lines.append(f"  const db = await getDbConnection(process.env.{connection_env});")
        for i, q in enumerate(queries):
            q_processed = re.sub(r'\{\{([a-zA-Z_]+)\}\}', r'${ctx.\1}', q)
            if '${' in q_processed:
                q_js = f"`{q_processed}`"
            else:
                q_js = json.dumps(q)
            lines.append(f"  const result{i} = await db.query({q_js});")
        lines.append(f"  const body = result0.rows ? result0.rows[0] : result0;")

    else:  # factory
        lines.append(f"  // Factory mode — pure JS object, no real API/DB call")
        args = setup.get("args", {})
        lines.append(f"  const body = {render_payload(args)};")

    # Extract outputs
    lines.append(f"  const fixture: FixtureResult = {{")
    lines.append(f'    fixture_id: "{fid}",')
    for out_key, json_path in outputs.items():
        # $.field → body.field
        if json_path.startswith("$."):
            access = json_path[2:]
            lines.append(f'    {out_key}: body.{access},')
        else:
            lines.append(f'    {out_key}: body,  // raw fallback')
    lines.append(f"    _raw: body,")
    lines.append(f"  }};")
    lines.append(f"  console.log(`✅ Setup fixture: {fid} →`, fixture);")
    lines.append(f"  return fixture;")
    lines.append(f"}}")
    return "\n".join(lines)


def generate_cleanup_function(fixture: dict) -> str:
    """Generate cleanup function for 1 fixture."""
    fid = fixture["fixture_id"]
    name = to_pascal_case(fid)
    cleanup = fixture.get("cleanup_recipe", {})

    # Chấp nhận shorthand string "DELETE /api/xxx" → normalize về dict
    if isinstance(cleanup, str) and cleanup.strip():
        cleanup = {"type": "api", "endpoint": cleanup.strip()}
    if not cleanup or not isinstance(cleanup, dict):
        return ""

    cleanup_type = cleanup.get("type", "api")

    lines = []
    lines.append(f"/** Cleanup fixture: {fid} */")
    lines.append(f"export async function cleanup{name}(ctx: FixtureCtx): Promise<void> {{")
    lines.append(f"  try {{")

    if cleanup_type == "api":
        endpoint = cleanup.get("endpoint", "")
        method_match = re.match(r"(GET|POST|PUT|PATCH|DELETE)\s+(.+)", endpoint)
        if method_match:
            method, path = method_match.group(1).lower(), method_match.group(2)
        else:
            method, path = "delete", endpoint

        path_processed = re.sub(r'\{\{([a-zA-Z_]+)\}\}', r'${ctx.\1}', path)
        if '${' in path_processed:
            path_js = f"`{path_processed}`"
        else:
            path_js = json.dumps(path)

        lines.append(f"    await apiRequest('{method}', {path_js});")
        lines.append(f"    console.log(`🧹 Cleanup fixture: {fid}`);")

    elif cleanup_type == "sql":
        queries = cleanup.get("queries", [])
        for q in queries:
            q_processed = re.sub(r'\{\{([a-zA-Z_]+)\}\}', r'${ctx.\1}', q)
            if '${' in q_processed:
                q_js = f"`{q_processed}`"
            else:
                q_js = json.dumps(q)
            lines.append(f"    await db.query({q_js});")

    lines.append(f"  }} catch (e) {{")
    lines.append(f"    console.warn(`⚠️ Cleanup fixture {fid} failed:`, e);")
    lines.append(f"  }}")
    lines.append(f"}}")
    return "\n".join(lines)


def generate_data_factory(uat_data, output_path):
    """Generate full data-factory.ts file."""
    fixtures = uat_data.get("data_fixtures", [])

    # CHUẨN HOÁ MỘT LẦN, ngay lúc nạp. Trước đây bốn chỗ khác nhau cùng đọc
    # fixture["fixture_id"], nên một mục thiếu khoá làm script sập bằng KeyError ở một
    # dòng ngẫu nhiên — người đọc tưởng script hỏng, thật ra là dữ liệu thiếu khoá.
    for fx in fixtures:
        if not isinstance(fx, dict):
            print(f"❌ data_fixtures có phần tử không phải object: {type(fx).__name__}",
                  file=sys.stderr)
            sys.exit(2)
        fid = fx.get("fixture_id") or fx.get("id")
        if not fid:
            print("❌ Một mục data_fixtures thiếu 'fixture_id' (hoặc 'id'). Khoá đang có: "
                  f"{list(fx)[:8]}", file=sys.stderr)
            sys.exit(2)
        fx["fixture_id"] = fid


    if not fixtures:
        print("⚠️  Không có data_fixtures trong input. Skip generate.", file=sys.stderr)
        return

    # Build dispatch map (fixture_id → setupFn)
    dispatch_setup = []
    dispatch_cleanup = []
    for fx in fixtures:
        fid = fx["fixture_id"]
        name = to_pascal_case(fid)
        dispatch_setup.append(f'  "{fid}": setup{name},')
        if fx.get("cleanup_recipe"):
            dispatch_cleanup.append(f'  "{fid}": cleanup{name},')

    # Build TS code
    ts_code = f'''// Auto-generated data factory by uat-test-runner skill
// Generated: {datetime.now().isoformat()}
// Total fixtures: {len(fixtures)}

import {{ request, APIRequestContext }} from '@playwright/test';

const API_BASE = process.env.BASE_URL || 'http://localhost:3000';

export interface FixtureCtx {{
  [key: string]: any;
}}

export interface FixtureResult {{
  fixture_id: string;
  [key: string]: any;
}}

// === Helper functions ===

function randomHex(len = 8): string {{
  return Array.from({{ length: len }}, () =>
    Math.floor(Math.random() * 16).toString(16)
  ).join('');
}}

function randomUuid(): string {{
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {{
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  }});
}}

function nowISO(): string {{
  return new Date().toISOString();
}}

function todayStr(): string {{
  return new Date().toISOString().slice(0, 10);
}}

function daysOffsetISO(offsetDays: number): string {{
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString();
}}

// Shared API request context
let _apiContext: APIRequestContext | null = null;

async function apiRequest(method: string, path: string, payload?: any, headers?: any) {{
  if (!_apiContext) {{
    _apiContext = await request.newContext({{ baseURL: API_BASE }});
  }}
  const url = path.startsWith('http') ? path : path;
  const options: any = {{ headers: headers || {{}} }};
  if (payload && ['post', 'put', 'patch'].includes(method)) {{
    options.data = payload;
  }}
  // @ts-ignore — dynamic method dispatch
  const response = await _apiContext[method](url, options);
  let body: any = null;
  try {{
    body = await response.json();
  }} catch {{
    body = await response.text();
  }}
  return {{
    ok: response.ok(),
    status: response.status(),
    body,
  }};
}}

// SQL helper (stub — implement nếu cần)
async function getDbConnection(connStr?: string): Promise<any> {{
  throw new Error('SQL fixture setup requires DB driver. Install pg/mysql2 và implement getDbConnection.');
}}

// === Setup functions ===

{chr(10).join(generate_setup_function(fx) for fx in fixtures)}

// === Cleanup functions ===

{chr(10).join(filter(None, [generate_cleanup_function(fx) for fx in fixtures]))}

// === Dispatch map ===

export const setupFixture: Record<string, (ctx?: FixtureCtx) => Promise<FixtureResult>> = {{
{chr(10).join(dispatch_setup)}
}};

export const cleanupFixture: Record<string, (ctx: FixtureCtx) => Promise<void>> = {{
{chr(10).join(dispatch_cleanup)}
}};

// === Convenience: setup multi fixtures + return combined context ===

export async function setupFixtures(fixtureIds: string[]): Promise<FixtureCtx> {{
  const ctx: FixtureCtx = {{}};
  for (const fid of fixtureIds) {{
    const fn = setupFixture[fid];
    if (!fn) {{
      console.warn(`⚠️ Unknown fixture: ${{fid}}`);
      continue;
    }}
    const result = await fn(ctx);
    // Merge result fields into ctx (without overwriting prefix conflict)
    Object.assign(ctx, result);
    // Also expose nested by fixture_id
    ctx[fid] = result;
  }}
  return ctx;
}}

export async function cleanupFixtures(fixtureIds: string[], ctx: FixtureCtx): Promise<void> {{
  // Cleanup in reverse order (last setup, first cleanup)
  for (const fid of [...fixtureIds].reverse()) {{
    const fn = cleanupFixture[fid];
    if (!fn) continue;
    await fn(ctx[fid] || ctx);
  }}
}}
'''

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(ts_code, encoding="utf-8")

    print(f"✅ Đã tạo data factory: {output_path}", file=sys.stderr)
    print(f"   Tổng fixtures: {len(fixtures)}", file=sys.stderr)
    for fx in fixtures:
        name = to_pascal_case(fx["fixture_id"])
        print(f"     - setup{name} / cleanup{name}", file=sys.stderr)
    print(f"\n💡 Cách dùng trong spec:", file=sys.stderr)
    print(f"   import {{ setupFixtures, cleanupFixtures }} from './fixtures/data-factory';", file=sys.stderr)
    print(f"   test.beforeEach(async () => {{ ctx = await setupFixtures(['user.pending.D0']); }});", file=sys.stderr)
    print(f"   test.afterEach(async () => {{ await cleanupFixtures(['user.pending.D0'], ctx); }});", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Sinh TS data factory từ UAT data_fixtures")
    parser.add_argument("uat_data", help="JSON file từ read_excel_uat.py")
    parser.add_argument("-o", "--output", default="tests/fixtures/data-factory.ts")
    args = parser.parse_args()

    with open(args.uat_data, "r", encoding="utf-8") as f:
        uat_data = json.load(f)

    generate_data_factory(uat_data, args.output)


if __name__ == "__main__":
    main()
