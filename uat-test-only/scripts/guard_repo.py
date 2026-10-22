#!/usr/bin/env python3
"""guard_repo.py — bằng chứng ĐO ĐƯỢC rằng lượt UAT không sửa sản phẩm và không sửa kịch bản.

Lời cam kết "chỉ báo cáo, không sửa" trong SKILL.md là lời dặn; tệp này biến nó thành phép đo.

  snapshot     --repo R --allow <OUT> [--allow uat/_registry] --state <OUT>/guard/state.json
               Ghi HEAD + danh sách tệp bẩn (tracked sửa + untracked + tệp bị .gitignore)
               ngoài vùng cho phép, kèm băm từng tệp. Bẩn có sẵn trước lượt chạy được dung
               thứ — nhưng không được đổi thêm.
  freeze-tests --state ... --tests <OUT>/tests [--tests <khac>]
               Quét luật cấm trong kịch bản (skip/fixme/fail/only/force/waitForTimeout) →
               thoát 1 nếu vi phạm; rồi băm mọi tệp kịch bản.
  verify       --state ... [--report <OUT>/guard/guard.json]
               So lại: HEAD không đổi; không tệp sản phẩm nào đổi/thêm/xoá ngoài vùng cho
               phép; kịch bản đã đóng băng không đổi. Vi phạm → thoát 1, báo cáo VÔ HIỆU.

Ba đường thoát đã bịt ở v2:
  * Tệp bị .gitignore — .env, config.local.*, sqlite, seed — là đúng nhóm tệp bị cám dỗ
    "chỉnh tí cho chạy được". Nay git status --ignored=matching đưa chúng vào tầm mắt.
  * Không phải repo git thì KHÔNG bỏ cuộc: băm cả cây tệp (mode "hash-tree"). Chỉ khi cây
    vượt --max-files mới ghi "khong-kiem-duoc" — và khi ấy báo cáo HẠ TRẦN kết luận.
  * Lột chú thích theo DÒNG. Mẫu //.*$ ăn luôn phần sau https:// nên câu
    goto('https://x'); waitForTimeout(5000) trên MỘT dòng từng lọt cổng đóng băng.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Mẫu cấm trong kịch bản. Mỗi mẫu là một cách làm test XANH mà không kiểm gì.
BANNED = [
    (r"\btest\.skip\s*\(|\bit\.skip\s*\(|\bdescribe\.skip\s*\(", "skip — bỏ qua ca"),
    (r"\.fixme\s*\(", "fixme — bỏ qua ca"),
    (r"\btest\.fail\s*\(", "test.fail() — đảo nghĩa đạt/không đạt"),
    (r"\.only\s*\(", ".only() — chỉ chạy một phần"),
    (r"force\s*:\s*true", "force: true — bấm xuyên lớp phủ, che lỗi giao diện"),
    (r"waitForTimeout\s*\(", "waitForTimeout() — chờ mù thay cho chờ trạng thái"),
    (r"test\.slow\s*\(", "test.slow() — nới timeout"),
    (r"expect\.soft\s*\(\s*true\s*\)|expect\s*\(\s*true\s*\)\s*\.toBe\s*\(\s*true\s*\)", "assert rỗng"),
    (r"route\s*\(\s*['\"]\*\*", "chặn/giả mọi request của hệ đang kiểm"),
]
TEST_EXT = {".ts", ".js", ".mjs", ".cjs", ".json", ".yaml", ".yml", ".sh", ".py"}

# Thư mục SINH RA (phụ thuộc tải về, kết quả biên dịch, cache). Loại khỏi tầm quét vì chúng
# được tạo lại từ nguồn — sửa ở đấy không qua mặt được ai. Mọi thứ khác, KỂ CẢ tệp bị
# .gitignore, đều nằm trong tầm mắt của rào.
IGNORE_DIRS = {
    "node_modules", ".git", "dist", ".next", ".nuxt", ".svelte-kit",
    ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "target", "coverage", ".turbo", ".cache", ".gradle", "Pods", ".dart_tool",
    ".terraform", ".tox", ".parcel-cache",
}
MAX_FILES_DEFAULT = 50000
# Khi đóng băng kịch bản chỉ bỏ qua thư mục phụ thuộc. KHÔNG dùng IGNORE_DIRS ở đây:
# <OUT> thường tên là "out" và kịch bản nằm ngay trong đó.
FREEZE_SKIP = {"node_modules", ".git", "__pycache__"}
# Dòng chỉ-là-chú-thích. Mẫu cấm trong chú thích không bị bắt oan; mẫu cấm nằm SAU mã trên
# cùng một dòng thì vẫn bị bắt.
COMMENT_LINE = re.compile(r"^\s*(//|\*|#|/\*)")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def norm(p: str) -> str:
    return p.replace("\\", "/").strip().strip('"')


def in_allow(path: str, allow) -> bool:
    return any(path == a or path.startswith(a + "/") for a in allow)


def generated(path: str) -> bool:
    """Đường dẫn có đi qua một thư mục sinh ra không."""
    return bool(set(path.split("/")[:-1]) & IGNORE_DIRS)


def rel_allow(root: Path, allows):
    out = []
    for al in allows:
        try:
            out.append(norm(str(Path(al).resolve().relative_to(root))))
        except ValueError:
            pass  # vùng cho phép nằm ngoài repo → không cần loại
    return out


def dirty(repo: Path, allow):
    """Tệp bẩn ngoài vùng cho phép → {đường dẫn: băm hoặc '<xoa>'}.

    --ignored=matching để tệp bị .gitignore KHÔNG còn là điểm mù. Loại thư mục sinh ra bằng
    pathspec để git khỏi phải liệt kê hàng vạn tệp node_modules.
    """
    pathspec = []
    for d in sorted(IGNORE_DIRS):
        pathspec += [f":(exclude,glob){d}/**", f":(exclude,glob)**/{d}/**"]
    rc, out = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all",
                  "--ignored=matching", "--", ".", *pathspec)
    if rc != 0:
        return None
    res = {}
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        ent = parts[i]
        i += 1
        if len(ent) < 4:
            continue
        code, path = ent[:2], norm(ent[3:])
        if code.startswith("R") or code.startswith("C"):
            i += 1  # bỏ đường dẫn cũ đi kèm
        if in_allow(path, allow) or generated(path):
            continue
        fp = repo / path
        res[path] = sha(fp) if fp.is_file() else "<xoa>"
    return res


def hash_tree(root: Path, allow, max_files: int):
    """Phương án khi không có git: băm cả cây tệp. None = cây quá lớn, không kiểm được."""
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel_dir = norm(str(Path(dirpath).relative_to(root)))
        rel_dir = "" if rel_dir == "." else rel_dir
        if rel_dir and in_allow(rel_dir, allow):
            dirnames[:] = []
            continue
        for fn in filenames:
            p = f"{rel_dir}/{fn}" if rel_dir else fn
            if in_allow(p, allow):
                continue
            if len(files) >= max_files:
                return None
            try:
                files[p] = sha(root / p)
            except OSError:
                continue  # tệp bị khoá hoặc biến mất giữa chừng
    return files


def load(state):
    return json.loads(Path(state).read_text(encoding="utf-8"))


def save(state, doc):
    Path(state).parent.mkdir(parents=True, exist_ok=True)
    Path(state).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_snapshot(a):
    repo = Path(a.repo).resolve()
    rc, top = git(repo, "rev-parse", "--show-toplevel")
    if rc == 0:
        root = Path(top.strip())
        allow = rel_allow(root, a.allow)
        _, head = git(root, "rev-parse", "HEAD")
        d = dirty(root, allow)
        if d is not None:
            save(a.state, {"repo": str(root), "mode": "git", "head": head.strip(),
                           "allow": allow, "dirty_before": d, "frozen": {}})
            print(f"guard: chụp trạng thái git {root.name} @ {head.strip()[:10]} · {len(d)} tệp "
                  f"bẩn có sẵn (dung thứ, nhưng không được đổi thêm; đã tính cả tệp bị "
                  f".gitignore) · vùng cho phép: {', '.join(allow) or '(ngoài repo)'}")
            return 0

    # Không phải repo git, hoặc git status hỏng → băm cả cây, đừng bỏ cuộc.
    root = repo
    allow = rel_allow(root, a.allow)
    tree = hash_tree(root, allow, a.max_files)
    if tree is None:
        save(a.state, {"repo": str(root), "mode": "khong-kiem-duoc", "allow": allow, "frozen": {}})
        print(f"guard: KHÔNG KIỂM ĐƯỢC — cây tệp vượt {a.max_files} tệp và không phải repo "
              f"git. Báo cáo sẽ HẠ TRẦN kết luận.")
        return 0
    save(a.state, {"repo": str(root), "mode": "hash-tree", "allow": allow,
                   "tree_before": tree, "frozen": {}})
    print(f"guard: chụp trạng thái hash-tree {root.name} · {len(tree)} tệp đã băm (không phải "
          f"repo git) · vùng cho phép: {', '.join(allow) or '(ngoài cây)'}")
    return 0


def cmd_freeze(a):
    doc = load(a.state)
    frozen, violations = {}, []
    for t in a.tests:
        base = Path(t)
        if not base.exists():
            continue
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for p in files:
            if set(p.parts) & FREEZE_SKIP or p.suffix.lower() not in TEST_EXT:
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for ln, line in enumerate(txt.splitlines(), 1):
                if COMMENT_LINE.match(line):
                    continue  # dòng chỉ-là-chú-thích: không bắt oan
                for pat, why in BANNED:
                    if re.search(pat, line):
                        violations.append(f"{p}:{ln}: {why} — `{line.strip()[:100]}`")
            frozen[str(p.resolve())] = sha(p)
    if violations:
        print("guard: TỪ CHỐI ĐÓNG BĂNG — kịch bản có mẫu bị cấm:")
        for v in violations:
            print("  x " + v)
        return 1
    if not frozen:
        print("guard: không có tệp kịch bản nào để đóng băng", file=sys.stderr)
        return 1
    doc["frozen"] = frozen
    doc["spec_hash"] = hashlib.sha256("".join(sorted(frozen.values())).encode()).hexdigest()[:12]
    save(a.state, doc)
    print(f"guard: đóng băng {len(frozen)} tệp kịch bản · spec-hash {doc['spec_hash']}")
    return 0


def cmd_verify(a):
    doc = load(a.state)
    mode = doc.get("mode")
    rep = {"ok": True, "mode": mode, "product_changes": [], "test_changes": [],
           "head_changed": False, "spec_hash": doc.get("spec_hash", "")}
    root = Path(doc["repo"])

    def diff(before, now):
        for p, h in now.items():
            if p not in before:
                rep["product_changes"].append(f"mới bẩn: {p}")
            elif before[p] != h:
                rep["product_changes"].append(f"đổi thêm: {p}")
        for p in before:
            if p not in now:
                rep["product_changes"].append(f"bị hoàn nguyên hoặc xoá: {p}")

    if mode == "git":
        _, head = git(root, "rev-parse", "HEAD")
        if head.strip() != doc.get("head"):
            rep["head_changed"] = True
            rep["product_changes"].append(
                f"HEAD đổi {doc.get('head','')[:10]} → {head.strip()[:10]} trong lúc chạy")
        diff(doc.get("dirty_before", {}), dirty(root, doc.get("allow", [])) or {})
    elif mode == "hash-tree":
        now = hash_tree(root, doc.get("allow", []), a.max_files)
        if now is None:
            rep["product_changes"].append("cây tệp phình quá ngưỡng giữa lượt chạy — không so được")
        else:
            diff(doc.get("tree_before", {}), now)

    for p, h in (doc.get("frozen") or {}).items():
        fp = Path(p)
        if not fp.is_file():
            rep["test_changes"].append(f"kịch bản bị xoá sau đóng băng: {p}")
        elif sha(fp) != h:
            rep["test_changes"].append(f"kịch bản bị SỬA sau đóng băng: {p}")

    rep["ok"] = not rep["product_changes"] and not rep["test_changes"]
    if a.report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    if mode == "khong-kiem-duoc":
        print("guard: KHÔNG KIỂM ĐƯỢC việc sửa sản phẩm — báo cáo sẽ HẠ TRẦN kết luận")
    if rep["ok"]:
        print(f"guard: sạch ({mode}) — không tệp sản phẩm nào đổi, kịch bản giữ nguyên từ lúc "
              f"đóng băng")
        return 0
    print("guard: VI PHẠM — báo cáo lượt này VÔ HIỆU")
    for x in rep["product_changes"] + rep["test_changes"]:
        print("  x " + x)
    return 1


def main():
    ap = argparse.ArgumentParser(
        description="Rào đo được: UAT không sửa sản phẩm, không sửa kịch bản")
    sp = ap.add_subparsers(dest="cmd", required=True)
    s1 = sp.add_parser("snapshot")
    s1.add_argument("--repo", default=".")
    s1.add_argument("--allow", action="append", default=[])
    s1.add_argument("--state", required=True)
    s1.add_argument("--max-files", type=int, default=MAX_FILES_DEFAULT)
    s2 = sp.add_parser("freeze-tests")
    s2.add_argument("--state", required=True)
    s2.add_argument("--tests", action="append", required=True)
    s3 = sp.add_parser("verify")
    s3.add_argument("--state", required=True)
    s3.add_argument("--report", default="")
    s3.add_argument("--max-files", type=int, default=MAX_FILES_DEFAULT)
    a = ap.parse_args()
    return {"snapshot": cmd_snapshot, "freeze-tests": cmd_freeze, "verify": cmd_verify}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
