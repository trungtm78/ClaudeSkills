#!/usr/bin/env python3
"""App mẫu cho diễn tập uat-test-only. Chế độ mặc định CỐ Ý có lỗi để chứng minh cổng biết ĐỎ:
  * nút "Lưu" gọi hàm không tồn tại → pageerror (monkey phải bắt)
  * nút "Đồng bộ" gọi /api/boom → HTTP 500 (monkey phải bắt)
  * nút "Xóa tất cả" dẫn tới /deleted — nằm trong danh sách CẤM BẤM; mọi lần truy cập ghi vào hits.log
--healthy: bỏ hai nút lỗi (lượt xanh).

Ba tầng sâu cũng được dựng ở đây để G14/G15/G17 đi qua đường ống thật, không chỉ qua unit test:
  /api/secret   quyền: healthy → 403 với vai sai và vai vô danh; CÓ LỖI → 200 cho tất cả (IDOR)
  app.db        dữ liệu: bảng don(id, trang_thai); healthy → REJECTED, CÓ LỖI → PENDING
  POST /api/don idempotency: healthy → cùng Idempotency-Key chỉ ghi MỘT dòng;
                CÓ LỖI → mỗi request ghi một dòng (duplicate-on-retry)
"""
import argparse
import json
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Console Windows hay là cp932/cp1252. Máy chủ mẫu in tiếng Việt, nên thiếu dòng này thì nó
# chết ngay lúc khởi động và diễn tập báo "app mẫu không lên" — một lỗi của giàn kiểm thử
# trông y hệt một lỗi của sản phẩm.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

INDEX = """<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Cửa hàng mẫu</title></head>
<body>
<h1>Cửa hàng mẫu</h1>
<p>Số lượng: <span id="dem" data-testid="dem">0</span></p>
<button id="tang">Tăng</button>
<label>Ghi chú <input id="ghichu" name="ghichu"></label>
<a href="/about">Giới thiệu</a>
{BROKEN}
<button id="xoa" onclick="location.href='/deleted'">Xóa tất cả</button>
<script>
document.getElementById('tang').onclick = () => {
  const e = document.getElementById('dem'); e.textContent = String(+e.textContent + 1);
};
</script>
</body></html>"""
BROKEN = ('<button id="luu" onclick="hamKhongTonTai()">Lưu</button>\n'
          '<button id="dongbo" onclick="fetch(\'/api/boom\')">Đồng bộ</button>')
ABOUT = """<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Giới thiệu</title></head>
<body><h1>Giới thiệu</h1><p>Cửa hàng mẫu dùng cho diễn tập.</p><a href="/">Về trang chủ</a></body></html>"""


TOKEN_OK = "T-KETOAN"     # vai ke-toan — vai duy nhất được phép xem /api/secret
DB_LOCK = threading.Lock()


def init_db(db: Path, healthy: bool):
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE don (id INTEGER PRIMARY KEY, trang_thai TEXT, idem_key TEXT)")
    # Lượt CÓ LỖI: máy chủ hiển thị "đã từ chối" nhưng dưới DB vẫn là PENDING — đúng nhóm
    # lỗi mà một phép đo chỉ nhìn màn hình sẽ bỏ sót.
    c.execute("INSERT INTO don (id, trang_thai, idem_key) VALUES (1, ?, NULL)",
              ("REJECTED" if healthy else "PENDING",))
    c.commit()
    c.close()


def make_handler(healthy: bool, hits: Path, db: Path):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="text/html; charset=utf-8"):
            b = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

        def do_POST(self):
            p = self.path.split("?")[0]
            if p != "/api/don":
                self._send(404, "<h1>404</h1>")
                return
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            key = self.headers.get("Idempotency-Key") or ""
            with DB_LOCK:
                c = sqlite3.connect(db, timeout=10)
                if healthy and key:
                    # Đúng: một khoá logic → tối đa một lần ghi có hiệu lực.
                    cur = c.execute("SELECT count(*) FROM don WHERE idem_key = ?", (key,))
                    if cur.fetchone()[0] == 0:
                        c.execute("INSERT INTO don (trang_thai, idem_key) VALUES ('NEW', ?)", (key,))
                else:
                    # Lỗi cố ý: bỏ qua khoá → gửi lại sinh bản ghi thừa.
                    c.execute("INSERT INTO don (trang_thai, idem_key) VALUES ('NEW', ?)", (key,))
                c.commit()
                c.close()
            self._json(201, {"ok": True})

        def do_GET(self):
            p = self.path.split("?")[0]
            if p == "/api/secret":
                auth = self.headers.get("Authorization", "")
                if healthy and auth != f"Bearer {TOKEN_OK}":
                    self._json(403, {"error": "forbidden"})
                else:
                    # Lượt CÓ LỖI: ai cũng xem được — đúng định nghĩa IDOR.
                    self._json(200, {"so_tien": 45000, "cccd": "0123456789"})
                return
            if p in ("/", "/index.html"):
                self._send(200, INDEX.replace("{BROKEN}", "" if healthy else BROKEN))
            elif p == "/about":
                self._send(200, ABOUT)
            elif p == "/api/health":
                self._send(200, json.dumps({"ok": True}), "application/json")
            elif p == "/api/boom":
                self._send(500, json.dumps({"error": "boom"}), "application/json")
            elif p == "/deleted":
                with open(hits, "a", encoding="utf-8") as f:
                    f.write("deleted\n")
                self._send(200, "<h1>Đã xoá</h1>")
            else:
                self._send(404, "<h1>404</h1>")
    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--healthy", action="store_true")
    ap.add_argument("--hits", default="hits.log")
    ap.add_argument("--db", default="app.db")
    a = ap.parse_args()
    db = Path(a.db)
    init_db(db, a.healthy)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port),
                              make_handler(a.healthy, Path(a.hits), db))
    print(f"app mẫu ở http://127.0.0.1:{a.port} ({'lành' if a.healthy else 'CÓ LỖI CỐ Ý'})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
