#!/usr/bin/env python3
"""check_oracle_binding.py — chứng minh mỗi assert bám vào `expected` của ca, bằng MÁY.

`references/writing-tests.md` §3 cấm "mở app xem nó đang hiện gì rồi viết assert theo đó".
Đó là lời dặn, và lời dặn thì không ai đo được. Đây đúng nhóm lỗi mà mutation testing gọi
là assertion gap: một bộ test chạy hết mọi dòng mà không khẳng định gì vẫn xanh rực.

Ba phép đo, chạy NGAY TRƯỚC khi đóng băng (lúc kịch bản còn được sửa):

  1. Mỗi ca có kịch bản phải có >= 1 ASSERT GIÁ TRỊ. Assert chỉ kiểm sự tồn tại
     (toBeVisible, toBeOK, toBeTruthy...) không tính: "trang có tải" không phải oracle.
  2. Mỗi ca phải có ÍT NHẤT MỘT assert giá trị được neo oracle ở dòng ngay trên. Cố ý
     KHÔNG đòi neo cho mọi assert: assert điều hướng (toHaveURL) là giàn giáo, không phải
     oracle, và ép neo cho tất cả chỉ đẻ ra neo bịa. Nhưng mọi neo ĐÃ CÓ đều bị soi:
         // oracle: TC-012 · "đơn chuyển REJECTED"
     và chuỗi trong ngoặc kép phải là chuỗi con (đã chuẩn hoá) của `expected` trong
     cases.json. Neo sai ca, hoặc trích một câu không có trong `expected`, đều là vi phạm.
  3. Cảnh báo `oracle-yeu`: `expected` có literal đo được (số, chuỗi trong ngoặc, mã
     trạng thái) mà không literal nào xuất hiện trong khối test của ca.

Thoát: 0 = đạt · 1 = có vi phạm (sửa kịch bản rồi chạy lại) · 2 = thiếu đầu vào.
Ghi <OUT>/oracle_bind.json cho build_report.py tính cổng G10.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Matcher KHẲNG ĐỊNH GIÁ TRỊ — so một giá trị cụ thể với điều đã hứa trong `expected`.
VALUE_MATCHERS = {
    "toHaveText", "toContainText", "toHaveValue", "toHaveValues", "toHaveURL", "toHaveTitle",
    "toHaveAttribute", "toHaveClass", "toHaveCount", "toHaveId", "toHaveCSS", "toHaveScreenshot",
    "toBe", "toEqual", "toStrictEqual", "toMatch", "toMatchObject", "toContain", "toContainEqual",
    "toHaveProperty", "toHaveLength", "toBeCloseTo", "toBeGreaterThan", "toBeGreaterThanOrEqual",
    "toBeLessThan", "toBeLessThanOrEqual", "toHaveJSONProperty",
}
# Matcher chỉ kiểm SỰ TỒN TẠI / trạng thái hiển thị — cần, nhưng một mình thì không đủ.
EXISTENCE_MATCHERS = {
    "toBeVisible", "toBeHidden", "toBeAttached", "toBeEnabled", "toBeDisabled", "toBeChecked",
    "toBeEditable", "toBeEmpty", "toBeFocused", "toBeInViewport", "toBeTruthy", "toBeFalsy",
    "toBeDefined", "toBeUndefined", "toBeNull", "toBeOK",
}
RE_TEST = re.compile(r"\btest\s*\(")
RE_TAG = re.compile(r"@([A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)")
RE_EXPECT = re.compile(r"\bexpect(?:\.soft)?\s*\(")
RE_MATCHER = re.compile(r"\.(\w+)\s*\(")
RE_ORACLE = re.compile(r"//\s*oracle\s*:\s*([A-Za-z0-9_-]+)\s*[·|:-]\s*[\"“'](.+?)[\"”']")
RE_LITERAL = re.compile(r"[\"'“]([^\"'”]{2,})[\"'”]|\b(\d[\d.,]*)\b")


def fold(s: str) -> str:
    """Chuẩn hoá để so khớp: bỏ dấu, hạ chữ, gộp khoảng trắng, bỏ dấu câu ngoài rìa."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s%.,:/-]", " ", s)).strip()


def code_only(text: str) -> str:
    """Bỏ các dòng chỉ-là-chú-thích. Nếu tính cả chú thích thì chính dòng neo oracle sẽ tự
    thoả mãn phép đo literal — một vòng lập luận khép kín, đo mà không đo gì."""
    keep = [l for l in text.splitlines() if not re.match(r"^\s*(//|\*|/\*)", l)]
    return chr(10).join(keep)


def split_tests(text: str):
    """Cắt tệp spec thành các khối test theo vị trí của `test(`. Đủ dùng cho phép đo tĩnh:
    ta chỉ cần biết mỗi assert thuộc về ca nào."""
    starts = [m.start() for m in RE_TEST.finditer(text)]
    if not starts:
        return []
    blocks = []
    for i, st in enumerate(starts):
        en = starts[i + 1] if i + 1 < len(starts) else len(text)
        blocks.append((st, text[st:en]))
    return blocks


def tc_of(block: str, known):
    """ID kế hoạch của khối test: ưu tiên tag @TC-..., sau đó token trong tiêu đề."""
    head = block[:400]
    for m in RE_TAG.finditer(head):
        if m.group(1) in known:
            return m.group(1)
    for tid in sorted(known, key=len, reverse=True):
        if re.search(rf"(?<![A-Za-z0-9-]){re.escape(tid)}(?![A-Za-z0-9])", head):
            return tid
    return None


def asserts_in(block: str, base_line: int):
    """Mỗi assert trong khối → (dòng, tên matcher, là-giá-trị, nguyên văn dòng)."""
    out = []
    for m in RE_EXPECT.finditer(block):
        tail = block[m.end():m.end() + 400]
        mm = None
        for cand in RE_MATCHER.finditer(tail):
            if cand.group(1) in VALUE_MATCHERS or cand.group(1) in EXISTENCE_MATCHERS:
                mm = cand.group(1)
                break
        if mm is None:
            continue
        line_no = base_line + block[:m.start()].count("\n")
        raw = block[:m.start()].rsplit("\n", 1)[-1] + tail.split("\n", 1)[0]
        out.append((line_no, mm, mm in VALUE_MATCHERS, raw.strip()))
    return out


def oracle_above(lines, line_no):
    """Neo oracle ở dòng ngay trên assert (cho phép bỏ qua dòng trắng ở giữa)."""
    i = line_no - 2  # lines[] đánh số từ 0, assert ở lines[line_no-1]
    while i >= 0 and not lines[i].strip():
        i -= 1
    return RE_ORACLE.search(lines[i]) if i >= 0 else None


def literals(expected: str):
    vals = set()
    for m in RE_LITERAL.finditer(str(expected or "")):
        v = (m.group(1) or m.group(2) or "").strip()
        if len(fold(v)) >= 2:
            vals.add(v)
    return vals


def main():
    ap = argparse.ArgumentParser(description="Cổng G10: assert phải bám vào expected của ca")
    ap.add_argument("--cases", required=True, help="<OUT>/cases.json")
    ap.add_argument("--tests", action="append", required=True, help="thư mục kịch bản")
    ap.add_argument("--out", required=True, help="<OUT>")
    a = ap.parse_args()
    try:
        cdoc = json.loads(Path(a.cases).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        print(f"check_oracle_binding: không đọc được {a.cases}: {e}", file=sys.stderr)
        return 2
    cases = {c["tc_id"]: c for c in cdoc.get("cases", [])}
    known = set(cases)

    violations, weak, per_case = [], [], {}
    all_body = ""   # thân mọi kịch bản, đã chuẩn hoá — dùng cho phép đo "oracle yếu"
    for troot in a.tests:
        base = Path(troot)
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in (".ts", ".js", ".mjs"):
                continue
            if p.name.startswith("_canary") or p.name == "auth.setup.ts":
                continue  # chứng âm và bước đăng nhập không mang oracle nghiệp vụ
            text = p.read_text(encoding="utf-8", errors="replace")
            all_body += " " + fold(code_only(text))
            lines = text.splitlines()
            for start, block in split_tests(text):
                tc = tc_of(block, known)
                base_line = text[:start].count("\n") + 1
                items = asserts_in(block, base_line)
                if tc is None:
                    if any(v for _, _, v, _ in items):
                        violations.append(
                            f"{p.name}:{base_line}: khối test không mang ID kế hoạch nào — "
                            f"assert của nó sẽ không được tính cho ca nào")
                    continue
                st = per_case.setdefault(tc, {"value": 0, "exist": 0, "anchored": 0,
                                              "file": p.name})
                exp_fold = fold(cases[tc].get("expected", ""))
                for line_no, matcher, is_value, raw in items:
                    st["value" if is_value else "exist"] += 1
                    if not is_value:
                        continue
                    anc = oracle_above(lines, line_no)
                    if anc is None:
                        # Không bắt lỗi từng assert: assert điều hướng (toHaveURL) là giàn
                        # giáo, không phải oracle. Ép neo cho mọi assert chỉ đẻ ra neo bịa.
                        # Luật thật nằm ở dưới: mỗi ca phải có ÍT NHẤT MỘT neo thật.
                        continue
                    st["anchored"] += 1
                    anc_tc, quoted = anc.group(1), anc.group(2)
                    if anc_tc != tc:
                        violations.append(
                            f"{p.name}:{line_no}: neo oracle ghi {anc_tc} nhưng khối test là {tc}")
                    elif fold(quoted) not in exp_fold:
                        violations.append(
                            f'{p.name}:{line_no}: neo oracle trích "{quoted[:60]}" — câu này '
                            f"KHÔNG có trong `expected` của {tc}; oracle phải đến từ yêu cầu, "
                            f"không đến từ app")
                    else:
                        qlits = literals(quoted)
                        if qlits and not any(fold(v) in fold(raw) for v in qlits):
                            violations.append(
                                f'{p.name}:{line_no}: neo oracle hứa giá trị '
                                f'{", ".join(sorted(qlits))} nhưng assert không dùng giá trị ấy: '
                                f"`{raw[:90]}`")

    for tc, c in cases.items():
        st = per_case.get(tc)
        if st is None:
            continue  # ca không có kịch bản → merge_results đã tính là KHÔNG CHẠY
        if st["value"] == 0:
            violations.append(
                f"{st['file']}: ca {tc} chỉ có {st['exist']} assert kiểm sự tồn tại, không có "
                f"assert GIÁ TRỊ nào — 'trang có tải' không phải là oracle")
        elif st["anchored"] == 0:
            violations.append(
                f"{st['file']}: ca {tc} có {st['value']} assert giá trị nhưng KHÔNG cái nào "
                f'được neo vào `expected`. Thêm trên assert chính: // oracle: {tc} · '
                f'"<trích nguyên văn từ expected>"')
        lits = literals(c.get("expected", ""))
        if lits and st["value"] > 0 and not any(fold(v) in all_body for v in lits):
            weak.append(f"{tc}: `expected` có giá trị đo được ({', '.join(list(lits)[:3])}) "
                        f"nhưng không giá trị nào xuất hiện trong kịch bản")

    total = len(per_case)
    ok_cases = sum(1 for v in per_case.values() if v["value"] > 0)
    rep = {"ok": not violations, "cases_with_spec": total, "cases_with_value_assert": ok_cases,
           "violations": violations, "weak": weak}
    outp = Path(a.out)
    outp.mkdir(parents=True, exist_ok=True)
    (outp / "oracle_bind.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    if violations:
        print(f"oracle-binding: TỪ CHỐI — {len(violations)} vi phạm:")
        for v in violations[:30]:
            print("  x " + v)
        return 1
    print(f"oracle-binding: đạt — {ok_cases}/{total} ca có assert giá trị neo vào `expected`"
          + (f" · {len(weak)} cảnh báo oracle yếu" if weak else ""))
    for w in weak[:10]:
        print("  ! " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
