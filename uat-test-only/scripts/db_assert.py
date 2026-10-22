#!/usr/bin/env python3
"""db_assert.py — khẳng định ở tầng DỮ LIỆU và AUDIT. CHỈ ĐỌC, không bao giờ ghi.

Tài liệu QA nói thẳng: "Không coi dữ liệu hiển thị đúng là dữ liệu đúng nếu chưa kiểm tra
identity và nguồn dữ liệu." Một màn hình xanh chứng minh tầng hiển thị đúng, không chứng
minh cái đã ghi xuống đúng. Cần assert ở từng chặng, không chỉ ở chặng cuối.

Hai rào cứng, không có cờ nào mở được:
  * Chỉ SELECT / WITH. Câu lệnh khác, hoặc có dấu ; thứ hai, đều bị TỪ CHỐI chạy.
  * Mồi dữ liệu bằng SQL vẫn CẤM (writing-tests.md §8). Ở đây chỉ mở phần ĐỌC. Đọc không
    phải ghi: đây là tăng phạm vi ĐO, không phải nới lỏng quản trị.

Ca khai một trong ba khối (xem references/db-and-audit.md):
  db_assert   {dsn?, query, expect:{rows?|value?|contains?}}
  audit_assert{dsn?, table?, entity, entity_id, action, fields:[...], expect_rows: 1}
  idempotency {url, method?, key_header, concurrency?, count_query, expect_rows}

Đầu ra <OUT>/results/db.json theo đúng định dạng của run_cli_checks.py, nên
merge_results.py nuốt được bằng --checks db=<tệp>. Ca nào không khai gì thì không có bản
ghi — tầng này không chạy cho ca đó, và không ai giả vờ là đã chạy.

Thoát: 0 = đã ghi kết quả · 2 = thiếu đầu vào · 4 = không có driver / không nối được DB
(khi ấy mọi ca có khai đều là KHÔNG CHẠY, không phải ĐẠT).
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib import request as urlrequest

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

READ_ONLY = re.compile(r"^\s*(SELECT|WITH)\b", re.I)


def guard_sql(q: str):
    """None = an toàn; ngược lại trả lý do từ chối."""
    q = (q or "").strip().rstrip(";")
    if not READ_ONLY.match(q):
        return "câu lệnh không bắt đầu bằng SELECT/WITH — db_assert chỉ được phép ĐỌC"
    if ";" in q:
        return "có dấu ; thứ hai — nhiều câu lệnh trong một chuỗi là đường vòng để ghi"
    if re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|COPY|CALL|DO)\b",
                 q, re.I):
        return "chứa từ khoá ghi/DDL — db_assert chỉ được phép ĐỌC"
    return None


def connect(dsn: str):
    """Trả (hàm chạy-truy-vấn, mô tả) hoặc (None, lý do). Không có driver thì nói thật."""
    if dsn.startswith("sqlite:"):
        import sqlite3
        conn = sqlite3.connect(dsn.split(":", 1)[1])

        def run(q, params=None):
            cur = conn.execute(q, params or [])
            return [tuple(r) for r in cur.fetchall()]
        return run, f"sqlite {dsn.split(':', 1)[1]}"
    if dsn.startswith(("postgres://", "postgresql://")):
        try:
            import psycopg
        except ImportError:
            try:
                import psycopg2 as psycopg
            except ImportError:
                return None, "thiếu driver PostgreSQL (psycopg hoặc psycopg2)"
        conn = psycopg.connect(dsn)
        conn.set_session(readonly=True) if hasattr(conn, "set_session") else None

        def run(q, params=None):
            with conn.cursor() as cur:
                cur.execute(q, params or [])
                return [tuple(r) for r in cur.fetchall()]
        return run, "postgresql"
    if dsn.startswith("mysql://"):
        try:
            import pymysql
        except ImportError:
            return None, "thiếu driver MySQL (pymysql)"
        m = re.match(r"mysql://([^:]+):([^@]*)@([^:/]+):?(\d+)?/(.+)", dsn)
        if not m:
            return None, "DSN mysql không đúng dạng mysql://user:pass@host:port/db"
        conn = pymysql.connect(user=m.group(1), password=m.group(2), host=m.group(3),
                               port=int(m.group(4) or 3306), database=m.group(5))

        def run(q, params=None):
            with conn.cursor() as cur:
                cur.execute(q, params or [])
                return [tuple(r) for r in cur.fetchall()]
        return run, "mysql"
    return None, f"DSN không nhận ra: {dsn[:40]}"


def judge(rows, expect):
    """So kết quả truy vấn với `expect` của ca. Trả danh sách lý do KHÔNG ĐẠT (rỗng = đạt)."""
    bad = []
    if "rows" in expect and len(rows) != int(expect["rows"]):
        bad.append(f"mong đợi {expect['rows']} dòng, thực tế {len(rows)}")
    if "min_rows" in expect and len(rows) < int(expect["min_rows"]):
        bad.append(f"mong đợi >= {expect['min_rows']} dòng, thực tế {len(rows)}")
    if "max_rows" in expect and len(rows) > int(expect["max_rows"]):
        bad.append(f"mong đợi <= {expect['max_rows']} dòng, thực tế {len(rows)}")
    if "value" in expect:
        got = rows[0][0] if rows and rows[0] else None
        if str(got) != str(expect["value"]):
            bad.append(f"ô đầu tiên: mong đợi «{expect['value']}», thực tế «{got}»")
    if "contains" in expect:
        blob = " ".join(str(c) for r in rows for c in r)
        for needle in ([expect["contains"]] if isinstance(expect["contains"], str)
                       else expect["contains"]):
            if str(needle) not in blob:
                bad.append(f"kết quả không chứa «{needle}»")
    if not expect:
        bad.append("ca khai db_assert nhưng không có `expect` — không có oracle thì không chấm")
    return bad


def fire(url, method, headers, body):
    req = urlrequest.Request(url, method=method,
                             data=(body.encode("utf-8") if body else None), headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=20) as r:
            return r.status
    except Exception as e:  # noqa: BLE001 — mọi lỗi mạng đều là dữ liệu của phép đo
        return getattr(e, "code", 0)


def do_idempotency(spec, run, base_url):
    """Gửi ĐỒNG THỜI N request cùng một khoá rồi đếm bản ghi bền vững.

    Gửi lại tuần tự KHÔNG chứng minh được idempotent: tính chất cần chứng minh là một thao
    tác logic, một khoá, tối đa một lần ghi có hiệu lực — kể cả khi các request chồng nhau.
    """
    from concurrent.futures import ThreadPoolExecutor
    import uuid
    n = int(spec.get("concurrency") or 5)
    url = spec["url"] if spec["url"].startswith("http") else (base_url or "") + spec["url"]
    key = spec.get("key_value") or str(uuid.uuid4())
    headers = dict(spec.get("headers") or {})
    headers[spec.get("key_header") or "Idempotency-Key"] = key
    headers.setdefault("Content-Type", "application/json")
    body = spec.get("body")
    if isinstance(body, (dict, list)):
        body = json.dumps(body)
    with ThreadPoolExecutor(max_workers=n) as ex:
        codes = list(ex.map(lambda _: fire(url, spec.get("method") or "POST", headers, body),
                            range(n)))
    q = spec["count_query"]
    bad = guard_sql(q)
    if bad:
        return None, [bad], codes
    rows = run(q, [key] if "%s" in q or "?" in q else None)
    got = int(rows[0][0]) if rows and rows[0] else 0
    want = int(spec.get("expect_rows", 1))
    reasons = []
    if got > want:
        reasons.append(f"duplicate-on-retry: {n} request đồng thời cùng khoá idempotency tạo "
                       f"{got} bản ghi, mong đợi tối đa {want} (mã trả về: {codes})")
    elif got < want:
        reasons.append(f"mong đợi {want} bản ghi, thực tế {got} (mã trả về: {codes})")
    return got, reasons, codes


def do_audit(spec, run):
    """Khẳng định có đúng số dòng audit, và dòng ấy mang đủ trường truy vết."""
    q = spec.get("query")
    if not q:
        tbl = spec.get("table") or "audit_log"
        cols = ", ".join(spec.get("fields") or
                         ["user_id", "created_at", "entity_id", "action", "old_value", "new_value"])
        q = (f"SELECT {cols} FROM {tbl} WHERE entity = '{spec['entity']}' "
             f"AND entity_id = '{spec['entity_id']}' AND action = '{spec['action']}'")
    bad = guard_sql(q)
    if bad:
        return [bad]
    rows = run(q)
    want = int(spec.get("expect_rows", 1))
    if len(rows) != want:
        return [f"mong đợi {want} dòng audit cho {spec.get('action')} trên "
                f"{spec.get('entity')}#{spec.get('entity_id')}, thực tế {len(rows)} — "
                f"thao tác nhạy cảm không có audit thì không truy được ai làm gì"]
    empty = [i for i, v in enumerate(rows[0]) if v is None or str(v).strip() == ""]
    if empty:
        return [f"dòng audit có {len(empty)} trường rỗng (vị trí {empty}) — audit thiếu "
                f"trường thì không tái dựng được thay đổi"]
    return []


def main():
    ap = argparse.ArgumentParser(description="G15: khẳng định tầng dữ liệu, audit, idempotency")
    ap.add_argument("--cases", required=True, help="<OUT>/cases.json")
    ap.add_argument("--out", required=True, help="tệp kết quả, vd <OUT>/results/db.json")
    ap.add_argument("--dsn", default="", help="mặc định lấy biến UAT_DB_DSN; ca có thể ghi đè")
    ap.add_argument("--base-url", default=os.environ.get("UAT_BASE_URL", ""))
    a = ap.parse_args()
    try:
        cases = json.loads(Path(a.cases).read_text(encoding="utf-8-sig")).get("cases", [])
    except (OSError, ValueError) as e:
        print(f"db_assert: không đọc được {a.cases}: {e}", file=sys.stderr)
        return 2

    work = [c for c in cases if c.get("db_assert") or c.get("audit_assert") or c.get("idempotency")]
    checks = []
    if not work:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"checks": []}, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print("db_assert: không ca nào khai db_assert/audit_assert/idempotency — tầng này "
              "không chạy (và không ai giả vờ là đã chạy)")
        return 0

    dsn = a.dsn or os.environ.get("UAT_DB_DSN", "")
    if not dsn:
        run, why = None, "không có DSN (đặt UAT_DB_DSN hoặc --dsn)"
    else:
        try:
            run, why = connect(dsn)
        except Exception as e:  # noqa: BLE001
            # Mở không được thì NÓI RA, đừng sập: sập giữa chừng làm tệp kết quả không
            # sinh ra, và một tầng không có kết quả dễ bị đọc nhầm thành "không có ca nào".
            run, why = None, f"không mở được DSN ({type(e).__name__}: {e})"
    if run is None:
        for c in work:
            checks.append({"tc_id": c["tc_id"], "name": c.get("title", ""),
                           "status": "KHONG_CHAY", "reason": "thieu-ket-noi-db",
                           "reasons": [why], "duration_ms": 0})
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(f"db_assert: KHÔNG CHẠY {len(work)} ca — {why}")
        return 4

    for c in work:
        t0 = time.time()
        reasons, status = [], "PASS"
        try:
            if c.get("db_assert"):
                spec = c["db_assert"]
                bad = guard_sql(spec.get("query", ""))
                if bad:
                    status, reasons = "KHONG_CHAY", [f"db_assert bị TỪ CHỐI: {bad}"]
                else:
                    reasons += judge(run(spec["query"]), spec.get("expect") or {})
            if status == "PASS" and c.get("audit_assert"):
                reasons += do_audit(c["audit_assert"], run)
            if status == "PASS" and c.get("idempotency"):
                _, r, _ = do_idempotency(c["idempotency"], run, a.base_url)
                reasons += r
        except Exception as e:  # noqa: BLE001
            status, reasons = "KHONG_CHAY", [f"lỗi khi chạy khẳng định: {type(e).__name__}: {e}"]
        if status == "PASS" and reasons:
            status = "FAIL"
        checks.append({"tc_id": c["tc_id"], "name": c.get("title", ""), "status": status,
                       "reason": "" if status == "PASS" else (
                           "thieu-ket-noi-db" if status == "KHONG_CHAY" else "du-lieu-sai"),
                       "reasons": reasons, "duration_ms": int((time.time() - t0) * 1000)})

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"checks": checks, "dsn_kind": why},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    n_fail = sum(1 for x in checks if x["status"] == "FAIL")
    print(f"db_assert: {len(checks)} ca · FAIL {n_fail} · nguồn {why}")
    for x in checks:
        if x["status"] != "PASS":
            print(f"  x {x['tc_id']}: {'; '.join(x['reasons'])[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
