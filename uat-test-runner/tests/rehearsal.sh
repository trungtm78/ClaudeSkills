#!/usr/bin/env bash
# rehearsal.sh — diễn tập ĐẦU-CUỐI THẬT của chuỗi uat-test-writer → uat-test-runner.
#
# Vì sao cần: mọi script mới của hai skill (validate_uat_json, coverage_calc, self_audit,
# build_runner_report, heal_log) trước đó CHỈ thấy dữ liệu giả trong unit test. Theo đúng
# luật của chính bộ này — "một cổng chưa từng đỏ vì lý do thật là một cổng chưa từng chạy"
# — chúng chưa thật sự chạy.
#
#   Lượt 1 (app CÓ LỖI)  → runner phải ra NO-GO; writer phải chặn ca thiếu oracle_source
#   Lượt 2 (app lành)    → runner phải ra GO; ca P2 hỏng vẫn hiện tên trong khối kết quả
#   Lượt 3 (có heal)     → GO bị hạ xuống CONDITIONAL GO, vì thước đã chỉnh giữa lúc đo
#
# Dùng app mẫu và spec của uat-test-only (cùng một app, cùng Chromium thật). Cấu hình
# Playwright cũng lấy từ đó — thứ đang được kiểm ở đây là CÁC SCRIPT của runner biến một
# lượt chạy thật thành verdict đúng hay không, việc ấy độc lập với cấu hình của ai.
#
# Chạy: bash tests/rehearsal.sh      Thoát 0 = mọi khẳng định đúng.
set -uo pipefail
SK="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS="$(cd "$SK/.." && pwd)"
WR="$SKILLS/uat-test-writer"
ONLY="$SKILLS/uat-test-only"
FX="$ONLY/tests/fixtures"; export FX
PORT="${REHEARSAL_PORT:-8811}"
URL="http://127.0.0.1:$PORT"
PY="$(command -v python || command -v python3)"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✗ %s\n' "$1"; }
chk() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
# Console Windows hay là cp932 — mọi giá trị cần so đều có dấu.
v() { PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(eval(sys.argv[2]))" "$1" "$2"; }

[ -d "$ONLY/tests/fixtures" ] || { echo "rehearsal: cần uat-test-only/tests/fixtures — BỎ QUA"; exit 3; }
command -v node >/dev/null && command -v npm >/dev/null || { echo "rehearsal: thiếu node/npm — BỎ QUA (không phải đạt)"; exit 3; }

W="$(mktemp -d)"
SRV=""
# REHEARSAL_KEEP=<thư mục> → giữ lại hiện vật để đọc báo cáo thật.
trap 'kill $SRV 2>/dev/null; if [ -n "${REHEARSAL_KEEP:-}" ]; then rm -rf "$REHEARSAL_KEEP"; cp -r "$W" "$REHEARSAL_KEEP"; echo "rehearsal: giữ hiện vật ở $REHEARSAL_KEEP"; fi; rm -rf "$W"' EXIT
cd "$W" || exit 1

start_app() {
  kill $SRV 2>/dev/null; sleep 0.5
  PYTHONIOENCODING=utf-8 "$PY" "$FX/app_server.py" --port "$PORT" $1 --hits "$W/hits.log" --db "$W/app.db" >/dev/null 2>&1 &
  SRV=$!
  for _ in $(seq 1 40); do "$PY" -c "import urllib.request;urllib.request.urlopen('$URL/api/health',timeout=1)" 2>/dev/null && return 0; sleep 0.25; done
  echo "rehearsal: app mẫu không lên"; exit 1
}

echo "── chuẩn bị không gian chạy (npm + chromium)"
mkdir -p run/tests results
cp "$ONLY/assets/package.json" "$ONLY/assets/playwright.config.ts" run/
cp "$FX/specs/demo.e2e.spec.ts" "$FX/specs/demo.api.spec.ts" "$FX/specs/about.e2e.spec.ts" run/tests/
cat > run/tests/guard.api.spec.ts <<'SPEC'
import { test, expect } from '@playwright/test';

// Ca PHAN BIET hai luot: app CO LOI tra 200 cho moi vai (IDOR), app lanh tra 403.
test('TC-DEMO-011 tai nguyen nhay cam phai bi chan voi vai vo danh',
  { tag: ['@TC-DEMO-011'] }, async ({ request }) => {
  const r = await request.get('/api/secret');
  // oracle: TC-DEMO-011 · "bi chan voi ma 403"
  expect(r.status()).toBe(403);
});
SPEC
( cd run && npm install --no-audit --no-fund --loglevel=error >/dev/null 2>&1 ) || { echo "npm install hỏng"; exit 1; }
( cd run && npx playwright install chromium >/dev/null 2>&1 ) || { echo "không cài được chromium"; exit 1; }

# Kế hoạch: chỉ giữ những TC có kịch bản thật, để độ phủ là 100% và G3 không che mất G1/G2.
"$PY" - <<'PYEOF'
import json, pathlib, os
fx = pathlib.Path(os.environ["FX"]) / "uat.json"
d = json.loads(fx.read_text(encoding="utf-8-sig"))
keep = {"TC-DEMO-001", "TC-DEMO-002", "TC-DEMO-003", "TC-DEMO-004"}
guard = dict(next(t for t in d["test_cases"] if t["tc_id"] == "TC-DEMO-002"))
guard.update(tc_id="TC-DEMO-011", title="Tai nguyen nhay cam bi chan voi vai vo danh",
             type="RED", platform="api", priority="P0", severity_if_fail="S1",
             rule_ref="AC-SEC-2", oracle_source="Dien tap SEC-2: /api/secret chi mo cho ke-toan",
             catches_bug="may chu bo kiem quyen", coverage_ids=["COV-11"],
             steps="Goi /api/secret khong kem token", expected="Bi chan voi ma 403")
d["test_cases"].append(guard)
keep.add("TC-DEMO-011")
full = d["test_cases"]
pathlib.Path("uat-full.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
d["test_cases"] = [t for t in full if t["tc_id"] in keep]
pathlib.Path("uat.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
ledger = ["# Coverage Ledger — diễn tập", "M2=3 · FP=3", "",
          "| cov_id | Kỹ thuật | Item | Nguồn | TC phủ | Trạng thái |",
          "|---|---|---|---|---|---|"]
for t in d["test_cases"]:
    ledger.append(f"| {t['coverage_ids'][0]} | AC | {t['title'][:30]} | {t['rule_ref']} | {t['tc_id']} | dat |")
pathlib.Path("_coverage-ledger.md").write_text("\n".join(ledger) + "\n", encoding="utf-8")
PYEOF

echo "── writer: tự kiểm hàng trước khi bàn giao"
"$PY" "$WR/scripts/validate_uat_json.py" uat-full.json >/tmp/w1.txt 2>&1; RC=$?
chk "W1 chặn đúng ca thiếu oracle_source trong bộ đầy đủ" '[ $RC -eq 1 ] && grep -q "TC-DEMO-005" /tmp/w1.txt'
"$PY" "$WR/scripts/validate_uat_json.py" uat.json >/dev/null 2>&1; RC=$?
chk "W1 cho qua bộ kế hoạch đã sạch"                     '[ $RC -eq 0 ]'
"$PY" "$WR/scripts/coverage_calc.py" --ledger _coverage-ledger.md --uat uat.json --write >/tmp/w2.txt 2>&1
chk "W2 tính được TC_min từ Ledger và ghi vào uat.json"  '[ "$(v uat.json "d[\"tc_min\"][\"computed_by\"]")" = coverage_calc.py ]'
chk "W2: M1 đếm từ bảng Ledger = 5 item"                 '[ "$(v uat.json "d[\"tc_min\"][\"M1\"]")" = 5 ]'
chk "W2 thiếu M4 → nói rõ CHƯA PHẢI ENSEMBLE"           'grep -q ENSEMBLE /tmp/w2.txt'
"$PY" "$WR/scripts/self_audit.py" --uat uat.json --ledger _coverage-ledger.md >/tmp/w3.txt 2>&1
chk "W3 ra SẴN SÀNG-KÈM-KHUYẾT (3 mục CẦN NGƯỜI hạ trần)" 'grep -q "SẴN SÀNG-KÈM-KHUYẾT" /tmp/w3.txt'
chk "W3 không ai tự tích thay 3 mục CẦN NGƯỜI"            '[ "$(grep -c "CẦN NGƯỜI" /tmp/w3.txt)" -ge 3 ]'

run_round() {   # $1 = thư mục kết quả
  local OUT="$1"
  mkdir -p "$OUT"
  ( cd run && UAT_BASE_URL="$URL" PLAYWRIGHT_JSON_OUTPUT_NAME="../$OUT/pw.json" \
      npx playwright test --reporter=json >/dev/null 2>&1 ); true
  "$PY" "$SK/scripts/flatten_pw_results.py" "$OUT/pw.json" "$OUT/flat.json" >/dev/null 2>&1
  "$PY" "$SK/scripts/resolve_url.py" --cwd . -o "$OUT/url.json" >/dev/null 2>&1
  "$PY" "$SK/scripts/extract_failed_tcs.py" "$OUT/flat.json" --scope verify \
        --output "$OUT/failed.txt" >/dev/null 2>&1
  "$PY" "$SK/scripts/build_runner_report.py" --results "$OUT/flat.json" --uat uat.json \
        --url "$OUT/url.json" --s2-budget 0 "${@:2}" -o "$OUT" >/dev/null 2>&1
}

echo "── lượt 1: app CÓ LỖI"
start_app ""
printf 'BASE_URL=%s\n' "$URL" > .env
run_round r1
R1=r1
chk "flatten gộp được kết quả Playwright thật"        '[ -s $R1/flat.json ]'
chk "kết luận NO-GO"                                  '[ "$(v $R1/runner-verdict.json "d[\"verdict\"]")" = NO-GO ]'
chk "G0 ĐẠT — app tới được nên vẫn kiểm được"         '[ "$(v $R1/runner-verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G0\"][0]")" = ĐẠT ]'
chk "G1 API smoke HỎNG — ca quyền ở lớp api đỏ"       '[ "$(v $R1/runner-verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G1\"][0]")" = HỎNG ]'
chk "ca hỏng được NÊU TÊN, không chỉ đếm"             'grep -q "^HỎNG: TC-DEMO" $R1/runner-verdict.txt'
chk "extract_failed_tcs liệt được ca đỏ để chạy lại"  '[ -s $R1/failed.txt ]'

echo "── lượt 2: app lành"
start_app --healthy
run_round r2
R2=r2
chk "kết luận GO"                                     '[ "$(v $R2/runner-verdict.json "d[\"verdict\"]")" = GO ]'
chk "G1 API smoke ĐẠT khi máy chủ chặn đúng"          '[ "$(v $R2/runner-verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G1\"][0]")" = ĐẠT ]'
chk "G2 đường găng ĐẠT"                               '[ "$(v $R2/runner-verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G2\"][0]")" = ĐẠT ]'
chk "G3 độ phủ ĐẠT (mẫu số là kế hoạch)"              '[ "$(v $R2/runner-verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G3\"][0]")" = ĐẠT ]'
chk "ca P2 cố ý sai vẫn hiện tên trong khối kết quả"  'grep -q "TC-DEMO-003" $R2/runner-verdict.txt'

echo "── lượt 3: có heal thì không còn là GO"
"$PY" "$SK/scripts/heal_log.py" --file heal.json reset >/dev/null 2>&1
"$PY" "$SK/scripts/heal_log.py" --file heal.json add --tc TC-DEMO-003 \
      --what "doi locator sang getByRole" --why "nut doi aria-label sau refactor" >/dev/null 2>&1
run_round r3 --heal heal.json
chk "sổ heal ghi được 1 dòng"                         '[ "$(v heal.json "len(d[\"entries\"])")" = 1 ]'
chk "đã heal → hạ xuống CONDITIONAL GO"               '[ "$(v r3/runner-verdict.json "d[\"verdict\"]")" = "CONDITIONAL GO" ]'
chk "số lần heal hiện trong khối verdict"             'grep -q "HEAL: 1" r3/runner-verdict.txt'
"$PY" "$SK/scripts/heal_log.py" --file heal.json add --tc TC-X --what y --why "cho test xanh" >/dev/null 2>&1; RC=$?
chk "lý do 'cho test xanh' bị từ chối"                '[ $RC -eq 2 ]'

echo
echo "rehearsal: $PASS đạt, $FAIL trượt"
[ "$FAIL" -eq 0 ]
