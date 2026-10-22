#!/usr/bin/env python3
"""
parse-test-cases.py - Parse bảng Markdown UAT test cases sang JSON.

Input: file Markdown chứa các bảng TC theo format của uat-test-writer skill.
Output: JSON array các test case structured để Claude convert sang Playwright.

Usage:
    python parse-test-cases.py <input.md> [--output tc.json]
    cat tc.md | python parse-test-cases.py - --output tc.json
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional


# 28 loại TC theo handoff-schema.md v10 (uat-test-writer).
# QUAN TRỌNG: sắp xếp token DÀI trước token NGẮN để match substring không nhầm
# (vd 'MOBILE-A11Y' phải thử trước 'A11Y'; 'MOBILE-SEC' trước 'SECURITY' không đụng
#  nhưng 'SCREENSIZE' vs 'STATE' không giao — vẫn sort dài→ngắn cho an toàn).
TC_TYPES = sorted(
    [
        # Core (web + api)
        'GREEN', 'RED', 'EDGE', 'BOUNDARY', 'EP', 'STATE', 'DECISION',
        'SECURITY', 'DATA', 'PERFORMANCE', 'A11Y', 'COMPAT', 'UX', 'E2E',
        'EXPLORATORY', 'METAMORPHIC',
        # Mobile-only (Bước 0.7)
        'PERMISSIONS', 'DEEPLINK', 'PUSH', 'OFFLINE', 'LIFECYCLE', 'GESTURE',
        'SCREENSIZE', 'BIOMETRIC', 'INTERRUPT', 'INSTALL',
        'MOBILE-A11Y', 'MOBILE-SEC',
    ],
    key=len,
    reverse=True,
)
PRIORITIES = ['P0', 'P1', 'P2', 'P3']

# Mapping label tiếng Việt → key chuẩn
LABEL_MAP = {
    'loại': 'type',
    'type': 'type',
    'độ ưu tiên': 'priority',
    'priority': 'priority',
    'tiêu đề': 'title',
    'title': 'title',
    'yêu cầu': 'requirement',
    'requirement': 'requirement',
    'điều kiện tiên quyết': 'preconditions',
    'preconditions': 'preconditions',
    'các bước kiểm thử': 'steps',
    'test steps': 'steps',
    'steps': 'steps',
    'dữ liệu kiểm thử': 'test_data',
    'test data': 'test_data',
    'kết quả mong đợi': 'expected',
    'expected result': 'expected',
    'expected': 'expected',
    'kết quả thực tế': 'actual',
    'actual result': 'actual',
    'trạng thái': 'status',
    'status': 'status',
    'ghi chú': 'notes',
    'notes': 'notes',
    'module': 'module',
    # === v10 handoff-schema fields (uat-test-writer) ===
    'platform': 'platform',
    'persona': 'persona',
    'journey': 'journey_ref',
    'journey_ref': 'journey_ref',
    'severity nếu fail': 'severity_if_fail',
    'severity': 'severity_if_fail',
    'oracle type': 'oracle_type',
    'oracle_type': 'oracle_type',
    'rule ref': 'rule_ref',
    'rule_ref': 'rule_ref',
    'oracle source': 'oracle_source',
    'oracle_source': 'oracle_source',
    'nguồn oracle': 'oracle_source',
    'bug bắt được': 'catches_bug',
    'catches_bug': 'catches_bug',
    'coverage ids': 'coverage_ids',
    'coverage_ids': 'coverage_ids',
    'backend policy': 'backend_policy',
    'backend_policy': 'backend_policy',
    'data fixtures cần': 'data_required',
    'data_required': 'data_required',
    'locator hint': 'locator_hint',
    'locator_hint': 'locator_hint',
    'gherkin': 'gherkin',
    'evidence required': 'evidence_required',
    'evidence_required': 'evidence_required',
    'kỹ thuật test': 'technique',
    'kỹ thuật': 'technique',
    'technique': 'technique',
    'mức độ rủi ro': 'risk_level',
    'risk': 'risk_level',
}

# Field dạng CSV list trong Markdown → parse thành list
LIST_FIELDS = {'coverage_ids', 'data_required', 'evidence_required'}


def normalize_label(label: str) -> Optional[str]:
    """Normalize label về key chuẩn (lowercase, strip bold, strip space)."""
    clean = label.strip().lower()
    # Strip markdown bold/italic
    clean = re.sub(r'\*+', '', clean).strip()
    # Strip trailing colon
    clean = clean.rstrip(':').strip()
    return LABEL_MAP.get(clean)


def split_numbered_list(text: str) -> List[str]:
    """Tách text 'Step 1<br>Step 2<br>Step 3' hoặc '1. X 2. Y' thành list."""
    if not text:
        return []

    # Replace <br>, <br/>, <br /> với newline
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # Split theo pattern "1. " hoặc "1) " ở đầu line
    items = re.split(r'(?:^|\n)\s*\d+[\.\)]\s+', text)
    items = [item.strip() for item in items if item.strip()]

    # Nếu không có numbered list, split theo newline
    if len(items) <= 1:
        items = [line.strip() for line in text.split('\n') if line.strip()]

    return items


def parse_tc_id(text: str) -> Optional[str]:
    """Extract TC-ID từ text như 'TC-001', '**TC-001**', 'TC001'."""
    match = re.search(r'TC[-_]?(\d{1,4})', text, re.IGNORECASE)
    if match:
        return f"TC-{match.group(1).zfill(3)}"
    return None


def parse_tc_table(table_text: str) -> Optional[Dict]:
    """
    Parse 1 bảng TC dạng:
    | TC-ID | TC-001 |
    | Loại | GREEN |
    | ...
    """
    lines = [ln.strip() for ln in table_text.strip().split('\n') if ln.strip()]
    if not lines:
        return None

    tc = {
        'id': None,
        'type': None,
        'priority': None,
        'title': None,
        'module': None,
        'requirement': None,
        'preconditions': [],
        'steps': [],
        'test_data': '',
        'expected': [],
        'notes': '',
    }

    for line in lines:
        # Skip separator row | --- | --- |
        if re.match(r'^\|\s*[-:]+\s*\|', line):
            continue

        # Parse row dạng | label | value |
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 2:
            continue

        label_raw = cells[0]
        value = '|'.join(cells[1:]).strip() if len(cells) > 2 else cells[1].strip()

        # Check nếu cell đầu là TC-ID
        if 'tc-id' in label_raw.lower() or 'tc id' in label_raw.lower():
            tc['id'] = parse_tc_id(value)
            continue

        key = normalize_label(label_raw)
        if not key:
            continue

        if key in ['preconditions', 'steps', 'expected']:
            tc[key] = split_numbered_list(value)
        elif key == 'type':
            # Extract type keyword
            upper_val = value.upper()
            for t in TC_TYPES:
                if t in upper_val:
                    tc['type'] = t
                    break
        elif key == 'priority':
            for p in PRIORITIES:
                if p in value.upper():
                    tc['priority'] = p
                    break
        elif key in LIST_FIELDS:
            clean = re.sub(r'`', '', value)
            tc[key] = [v.strip() for v in clean.split(',') if v.strip()]
        else:
            tc[key] = value

    # Validate: phải có ít nhất id và title
    if not tc['id'] or not tc['title']:
        return None

    return tc


def parse_traceability_matrix(text: str) -> List[Dict]:
    """
    Parse bảng tổng dạng:
    | TC-ID | Loại | Module | Tiêu đề | Độ ưu tiên | Yêu cầu |
    | TC-001 | GREEN | Login | ... | P0 | REQ-01 |
    """
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
    if len(lines) < 2:
        return []

    # Parse header
    header_cells = [c.strip().lower() for c in lines[0].strip('|').split('|')]
    header_keys = [normalize_label(h) or h for h in header_cells]

    results = []
    for line in lines[2:]:  # skip header + separator
        if re.match(r'^\|\s*[-:]+\s*\|', line):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 2:
            continue

        row = {}
        for key, val in zip(header_keys, cells):
            if key == 'tc-id':
                row['id'] = parse_tc_id(val)
            elif key in ['type', 'priority', 'title', 'module', 'requirement']:
                row[key] = val
        if row.get('id'):
            results.append(row)

    return results


def extract_tables(markdown: str) -> List[str]:
    """Tìm tất cả markdown tables trong document."""
    tables = []
    current = []
    in_table = False

    for line in markdown.split('\n'):
        if line.strip().startswith('|') and line.strip().endswith('|'):
            current.append(line)
            in_table = True
        elif in_table and not line.strip():
            if current:
                tables.append('\n'.join(current))
            current = []
            in_table = False
        elif in_table:
            # Line không phải table format, kết thúc bảng
            if current:
                tables.append('\n'.join(current))
            current = []
            in_table = False

    if current:
        tables.append('\n'.join(current))

    return tables


def is_tc_detail_table(table: str) -> bool:
    """Check nếu là bảng chi tiết của 1 TC (cell đầu là TC-ID hoặc Loại)."""
    first_lines = table.split('\n')[:3]
    text = '\n'.join(first_lines).lower()
    return 'tc-id' in text or '**loại**' in text or '| loại ' in text


def is_traceability_matrix(table: str) -> bool:
    """Check nếu là bảng ma trận truy vết (header có nhiều cột)."""
    first_line = table.split('\n')[0].lower()
    # Bảng truy vết có ≥4 cột header
    cells = [c.strip() for c in first_line.strip('|').split('|') if c.strip()]
    if len(cells) < 4:
        return False
    has_id = any('tc-id' in c or 'tc id' in c or c == 'id' for c in cells)
    has_type = any('loại' in c or 'type' in c for c in cells)
    has_title = any('tiêu đề' in c or 'title' in c for c in cells)
    return has_id and has_type and has_title


TC_HEADING_RE = re.compile(r'^##\s+(TC-[A-Za-z0-9-]+)\s*$', re.MULTILINE)
BULLET_META_RE = re.compile(r'^-\s+\*{0,2}([^:*]+)\*{0,2}\s*:\s*(.*)$')
SECTION_RE = re.compile(r'^###\s+(.*)$')

SECTION_MAP = {
    'điều kiện tiên quyết': 'preconditions',
    'các bước kiểm thử': 'steps',
    'dữ liệu kiểm thử': 'test_data',
    'kết quả mong đợi': 'expected',
}


def parse_tc_heading_blocks(markdown: str) -> List[Dict]:
    """
    Parse format CHÍNH THỨC của generate_uat_markdown.py (uat-test-writer):
    heading `## TC-XXX` + bullet meta (`- Label: value`) + section `### ...`
    (checklist `- [ ]`, code fence) + gherkin fence.
    """
    matches = list(TC_HEADING_RE.finditer(markdown))
    results: List[Dict] = []

    for i, m in enumerate(matches):
        tc_id = m.group(1).upper()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        block = markdown[start:end]

        tc: Dict = {'id': tc_id, 'title': ''}
        current_section: Optional[str] = None
        section_lines: Dict[str, List[str]] = {}
        in_fence = False
        fence_target: Optional[str] = None
        pending_gherkin = False

        for raw in block.split('\n'):
            line = raw.rstrip()
            stripped = line.strip()

            # Code fence toggle (test_data / gherkin)
            if stripped.startswith('```'):
                if not in_fence:
                    in_fence = True
                    if pending_gherkin or 'gherkin' in stripped.lower():
                        fence_target = 'gherkin'
                        pending_gherkin = False
                    elif current_section == 'test_data':
                        fence_target = 'test_data'
                    else:
                        fence_target = None
                else:
                    in_fence = False
                    fence_target = None
                continue
            if in_fence:
                if fence_target:
                    section_lines.setdefault(fence_target, []).append(line)
                continue

            # Section heading `### ...`
            sec_m = SECTION_RE.match(stripped)
            if sec_m:
                sec_key = None
                sec_name = sec_m.group(1).strip().lower()
                for label, key in SECTION_MAP.items():
                    if label in sec_name:
                        sec_key = key
                        break
                current_section = sec_key
                continue

            # Bold labels như **Gherkin**: / **Tiêu đề**: xxx / **Meta**:
            if stripped.startswith('**'):
                bold_m = re.match(r'^\*\*([^*]+)\*\*\s*:\s*(.*)$', stripped)
                if bold_m:
                    label = bold_m.group(1).strip().lower()
                    value = bold_m.group(2).strip()
                    if label == 'tiêu đề' or label == 'title':
                        tc['title'] = value
                    elif label == 'gherkin':
                        pending_gherkin = True
                    # 'Meta', 'Oracle', 'Runner contract' = header nhóm bullet — bỏ qua
                current_section = None if stripped.rstrip(':').lower() not in (
                    '**meta**', '**oracle**', '**runner contract**'
                ) else current_section
                continue

            # Checklist / bullet trong section
            if current_section and (stripped.startswith('- [ ]') or stripped.startswith('- [x]')):
                section_lines.setdefault(current_section, []).append(
                    stripped[5:].strip()
                )
                continue
            if current_section and stripped.startswith('- '):
                section_lines.setdefault(current_section, []).append(stripped[2:].strip())
                continue
            if current_section and stripped:
                section_lines.setdefault(current_section, []).append(stripped)
                continue

            # Bullet meta `- Label: value` (Meta/Oracle/Runner contract blocks)
            meta_m = BULLET_META_RE.match(stripped)
            if meta_m:
                label_raw = meta_m.group(1)
                value = meta_m.group(2).strip().strip('`')
                key = normalize_label(label_raw)
                if not key:
                    continue
                if key == 'type':
                    upper_val = value.upper()
                    for t in TC_TYPES:
                        if t in upper_val:
                            tc['type'] = t
                            break
                elif key == 'priority':
                    for p in PRIORITIES:
                        if p in value.upper():
                            tc['priority'] = p
                            break
                elif key in LIST_FIELDS:
                    clean = re.sub(r'`', '', value)
                    tc[key] = [v.strip() for v in clean.split(',') if v.strip()]
                else:
                    tc[key] = value

        # Gộp section lines vào tc
        for key, lines_ in section_lines.items():
            content = [ln for ln in lines_ if ln]
            if not content:
                continue
            if key in ('preconditions', 'steps', 'expected'):
                tc[key] = content
            else:
                tc[key] = '\n'.join(content)

        if tc.get('id'):
            results.append(tc)

    return results


def parse_markdown(markdown: str) -> Dict:
    """Parse full markdown document và trả về structure đầy đủ."""
    tables = extract_tables(markdown)

    matrix = []
    for table in tables:
        if is_traceability_matrix(table):
            matrix = parse_traceability_matrix(table)
            break

    # FORMAT CHÍNH: heading blocks `## TC-XXX` (output của generate_uat_markdown.py)
    test_cases = parse_tc_heading_blocks(markdown)

    # FALLBACK legacy: per-TC detail tables
    if not test_cases:
        for table in tables:
            if is_traceability_matrix(table):
                continue
            if is_tc_detail_table(table):
                tc = parse_tc_table(table)
                if tc:
                    test_cases.append(tc)

    # Merge matrix info vào test_cases (nếu detail table không có type/priority)
    matrix_dict = {row['id']: row for row in matrix if row.get('id')}
    for tc in test_cases:
        if tc['id'] in matrix_dict:
            matrix_row = matrix_dict[tc['id']]
            for key in ['type', 'priority', 'module', 'requirement', 'title']:
                if not tc.get(key) and matrix_row.get(key):
                    tc[key] = matrix_row[key]

    # Statistics
    stats = {
        'total': len(test_cases),
        'by_type': {},
        'by_priority': {},
    }
    for tc in test_cases:
        t = tc.get('type', 'UNKNOWN')
        p = tc.get('priority', 'UNKNOWN')
        stats['by_type'][t] = stats['by_type'].get(t, 0) + 1
        stats['by_priority'][p] = stats['by_priority'].get(p, 0) + 1

    return {
        'test_cases': test_cases,
        'matrix': matrix,
        'statistics': stats,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Parse bảng Markdown UAT test cases sang JSON'
    )
    parser.add_argument('input', help='File Markdown input, dùng "-" để đọc stdin')
    parser.add_argument(
        '-o', '--output',
        help='File JSON output (default: in ra stdout)',
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        default=True,
        help='Pretty-print JSON (default: True)',
    )

    args = parser.parse_args()

    # Read input
    if args.input == '-':
        markdown = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ Không tìm thấy file: {args.input}", file=sys.stderr)
            sys.exit(1)
        markdown = input_path.read_text(encoding='utf-8')

    # Đầu vào KHÔNG phải Markdown thì nói ra, đừng trả 0 ca. Một tệp .json đưa nhầm vào
    # đây từng cho ra "đã parse 0 test cases" và thoát 0 — phía sau đọc thành "không có ca
    # nào để chạy" thay vì "tôi đọc sai định dạng". Im lặng trả 0 là một màu xanh giả.
    if markdown.lstrip()[:1] in ('{', '['):
        print("❌ Đầu vào trông như JSON, không phải Markdown. Script này chỉ parse .md." 
              "\n   Với uat.json, runner dùng thẳng tệp ấy (xem SKILL.md GĐ 1), không qua parse-test-cases.py.",
              file=sys.stderr)
        sys.exit(2)

    # Parse
    result = parse_markdown(markdown)

    if result['statistics']['total'] == 0:
        print("❌ Không parse được test case nào từ Markdown — sai bố cục, hoặc tệp rỗng."
              "\n   Thoát khác 0 để phía sau không đọc nhầm thành 'không có ca nào để chạy'.",
              file=sys.stderr)
        sys.exit(3)

    # Print stats to stderr
    stats = result['statistics']
    print(f"📊 Đã parse {stats['total']} test cases:", file=sys.stderr)
    print(f"   Theo loại: {stats['by_type']}", file=sys.stderr)
    print(f"   Theo độ ưu tiên: {stats['by_priority']}", file=sys.stderr)

    # Output JSON
    indent = 2 if args.pretty else None
    json_str = json.dumps(result, ensure_ascii=False, indent=indent)

    if args.output:
        Path(args.output).write_text(json_str, encoding='utf-8')
        print(f"✅ Đã lưu kết quả vào: {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == '__main__':
    main()
