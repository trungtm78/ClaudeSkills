#!/usr/bin/env python3
"""
merge_batches.py — Merge nhiều file batch JSON thành 1 input.json hợp nhất.

Token-saving workflow:
1. Claude sinh batch 1 (20-30 TC) → ghi /tmp/tc_batch_1.json
2. Claude sinh batch 2 → ghi /tmp/tc_batch_2.json
3. ... (lặp đến đủ TC_required)
4. Merge tất cả batch → input.json để feed vào Excel/Markdown generator

Lợi ích:
- Mỗi batch < 30 TC → token output trong 1 turn nhỏ
- Có thể recover khi interrupt (đã ghi file)
- Không cần giữ toàn bộ TC trong context

Usage:
    python merge_batches.py /tmp/tc_batch_*.json --feature "Login" -o input.json

    # Hoặc với metadata file
    python merge_batches.py /tmp/tc_batch_*.json --meta /tmp/feature_meta.json -o input.json

Batch JSON schema (mỗi file):
{
    "batch_id": 1,
    "test_cases": [
        { "tc_id": "TC-001", "type": "GREEN", ... },
        ...
    ]
}

Meta JSON schema (optional):
{
    "feature_name": "...",
    "complexity": "...",
    "scope": { "in_scope": [...], "out_of_scope": [...], "exit_criteria": "..." },
    "test_data": { "accounts": [...], "boundary_values": [...], "payloads": [...] }
}
"""

import argparse
import glob
import json
import sys
from pathlib import Path


def load_batch(file_path):
    """Load 1 file batch JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # Trường hợp batch chỉ là list of TC, không có wrapper
            return data
        return data.get("test_cases", [])
    except Exception as e:
        print(f"⚠️  Lỗi đọc {file_path}: {e}", file=sys.stderr)
        return []


def dedupe_by_tc_id(test_cases):
    """Loại bỏ TC trùng tc_id, ưu tiên giữ TC sau (override)."""
    seen = {}
    for tc in test_cases:
        tc_id = tc.get("tc_id", "")
        if tc_id:
            seen[tc_id] = tc
        else:
            # No tc_id → vẫn giữ với key tạm
            seen[id(tc)] = tc

    return list(seen.values())


def renumber_tc_ids(test_cases, prefix="TC"):
    """Đánh số lại TC IDs để liên tục TC-001, TC-002, ..."""
    for i, tc in enumerate(test_cases, start=1):
        tc["tc_id"] = f"{prefix}-{i:03d}"
    return test_cases


def merge_test_data(meta_test_data, batch_test_data_list):
    """Merge test_data từ meta + tất cả batch."""
    merged = {
        "accounts": [],
        "boundary_values": [],
        "payloads": [],
    }

    if meta_test_data:
        for key in merged.keys():
            merged[key].extend(meta_test_data.get(key, []))

    for td in batch_test_data_list:
        for key in merged.keys():
            merged[key].extend(td.get(key, []))

    # Dedupe by id/value
    def _dedupe_dicts(items, key):
        seen = set()
        result = []
        for item in items:
            k = str(item.get(key, ""))
            if k and k not in seen:
                seen.add(k)
                result.append(item)
        return result

    merged["accounts"] = _dedupe_dicts(merged["accounts"], "id")
    merged["boundary_values"] = _dedupe_dicts(
        merged["boundary_values"], "value"
    )
    merged["payloads"] = _dedupe_dicts(merged["payloads"], "payload")
    return merged


def main():
    parser = argparse.ArgumentParser(description="Merge UAT batch files")
    parser.add_argument(
        "batch_files",
        nargs="+",
        help="Danh sách file batch JSON (hoặc glob pattern)",
    )
    parser.add_argument("--feature", help="Feature name (override meta)")
    parser.add_argument("--complexity", default="medium",
                        help="Complexity: simple/medium/complex")
    parser.add_argument("--meta", help="File meta JSON (feature_name, scope, test_data)")
    parser.add_argument("-o", "--output", required=True, help="File output input.json")
    parser.add_argument("--no-renumber", action="store_true",
                        help="Không tự đánh số lại TC IDs")
    parser.add_argument("--dedupe", action="store_true",
                        help="Loại bỏ TC trùng tc_id")
    args = parser.parse_args()

    # Resolve glob patterns
    all_files = []
    for pattern in args.batch_files:
        if "*" in pattern or "?" in pattern:
            all_files.extend(sorted(glob.glob(pattern)))
        else:
            all_files.append(pattern)

    if not all_files:
        print(f"❌ Không tìm thấy batch file nào.", file=sys.stderr)
        sys.exit(1)

    print(f"📦 Sẽ merge {len(all_files)} batch files:", file=sys.stderr)
    for f in all_files:
        print(f"   - {f}", file=sys.stderr)

    # Load meta
    meta = {}
    if args.meta:
        try:
            with open(args.meta, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            print(f"⚠️  Lỗi đọc meta {args.meta}: {e}", file=sys.stderr)

    # Load all batches
    all_tcs = []
    batch_test_data = []
    for f in all_files:
        tcs = load_batch(f)
        all_tcs.extend(tcs)
        # Cũng cố lấy test_data nếu batch có
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "test_data" in data:
                batch_test_data.append(data["test_data"])
        except Exception:
            pass

        print(f"   ✓ {f}: {len(tcs)} TC", file=sys.stderr)

    print(f"\n📊 Total trước dedupe: {len(all_tcs)} TC", file=sys.stderr)

    if args.dedupe:
        all_tcs = dedupe_by_tc_id(all_tcs)
        print(f"📊 Sau dedupe: {len(all_tcs)} TC", file=sys.stderr)

    if not args.no_renumber:
        all_tcs = renumber_tc_ids(all_tcs)
        print(f"📊 Đã renumber TC-001 đến TC-{len(all_tcs):03d}", file=sys.stderr)

    # Build final
    output = {
        "feature_name": args.feature or meta.get("feature_name", "Unnamed Feature"),
        "complexity": args.complexity or meta.get("complexity", "medium"),
        "scope": meta.get("scope", {}),
        "test_cases": all_tcs,
        "test_data": merge_test_data(meta.get("test_data"), batch_test_data),
    }

    # Stats
    by_type = {}
    by_prio = {}
    for tc in all_tcs:
        t = tc.get("type", "")
        p = tc.get("priority", "")
        by_type[t] = by_type.get(t, 0) + 1
        by_prio[p] = by_prio.get(p, 0) + 1

    print(f"\n📈 Phân bố loại:", file=sys.stderr)
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {k}: {v}", file=sys.stderr)

    print(f"\n🎯 Phân bố priority:", file=sys.stderr)
    for k, v in sorted(by_prio.items()):
        print(f"   {k}: {v}", file=sys.stderr)

    # Quick ratio check
    total = len(all_tcs)
    if total > 0:
        green_pct = (by_type.get("GREEN", 0) / total) * 100
        red_pct = (by_type.get("RED", 0) / total) * 100
        sec_pct = (by_type.get("SECURITY", 0) / total) * 100
        print(f"\n⚖️  Ratio check:", file=sys.stderr)
        print(f"   GREEN: {green_pct:.1f}% {'✅' if green_pct <= 20 else '❌ vượt 20%'}", file=sys.stderr)
        print(f"   RED:   {red_pct:.1f}% {'✅' if red_pct >= 40 else '❌ dưới 40%'}", file=sys.stderr)
        print(f"   SEC:   {sec_pct:.1f}% {'✅' if sec_pct >= 10 else '❌ dưới 10%'}", file=sys.stderr)
        print(f"   Total: {total} {'✅' if total >= 100 else '❌ dưới HARD FLOOR 100'}", file=sys.stderr)

    # Write
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Đã ghi: {args.output}", file=sys.stderr)
    print(f"   Total TC: {len(all_tcs)}", file=sys.stderr)


if __name__ == "__main__":
    main()
