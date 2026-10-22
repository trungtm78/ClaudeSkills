#!/usr/bin/env bash
# rehearsal.sh — diễn tập ĐẦU-CUỐI THẬT của uat-test-only trên app mẫu (Playwright + Chromium thật).
#
# Luật của harness: "một cổng chưa từng đỏ vì lý do thật là một cổng chưa từng chạy".
#   Lượt 1 (app CÓ LỖI, kế hoạch có ca thiếu kịch bản + ca không hợp lệ) → phải NO-GO / FAIL,
#          monkey phải bắt pageerror + HTTP 500, và KHÔNG được bấm nút "Xóa tất cả".
#   Lượt 2 (app lành, đủ kịch bản)                                       → phải GO-CHỜ-KÝ / PASS,
#          dù ca P2 cố ý sai vẫn hiện trong FINDINGS.
#   Lượt 2 cũng chứng minh: chứng âm đỏ đủ ba mệnh đề, oracle-binding đạt, sổ lỗi ghi được.
#   Lượt 3 (can thiệp)  spec có test.skip → đóng băng bị TỪ CHỐI;
#          sửa spec sau đóng băng / sửa tệp sản phẩm → BÁO CÁO VÔ HIỆU.
# Chạy: bash rehearsal.sh            (cần node, npm, python; lần đầu tải @playwright/test)
# Thoát 0 = mọi khẳng định đúng.
set -uo pipefail
SK="$(cd "$(dirname "$0")/.." && pwd)"
FX="$SK/tests/fixtures"
PORT="${REHEARSAL_PORT:-8791}"
URL="http://127.0.0.1:$PORT"
PY="$(command -v python || command -v python3)"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  ✗ %s\n' "$1"; }
chk()  { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

command -v node >/dev/null && command -v npm >/dev/null || { echo "rehearsal: thiếu node/npm — BỎ QUA (không phải đạt)"; exit 3; }

W="$(mktemp -d)"
# REHEARSAL_KEEP=<thư mục> → giữ lại toàn bộ hiện vật để người đọc báo cáo thật.
trap 'kill $SRV 2>/dev/null; if [ -n "${REHEARSAL_KEEP:-}" ]; then rm -rf "$REHEARSAL_KEEP"; cp -r "$W" "$REHEARSAL_KEEP"; echo "rehearsal: giữ hiện vật ở $REHEARSAL_KEEP"; fi; rm -rf "$W"' EXIT
SRV=""
# MSYS tự đổi ĐỐI SỐ dạng /tmp/... sang đường Windows, nhưng KHÔNG đổi BIẾN MÔI TRƯỜNG.
# DSN đi qua biến UAT_DB_DSN nên phải tự đổi, nếu không sqlite mở không ra tệp.
WNAT="$(cd "$W" && { pwd -W 2>/dev/null || pwd; })"
cd "$W" || exit 1
git init -q product && cd product && git config user.email t@t && git config user.name t
mkdir -p src && echo "mã sản phẩm" > src/app.txt && git add -A && git commit -qm base

start_app() {  # $1 = --healthy hoặc rỗng
  kill $SRV 2>/dev/null; sleep 0.5
  "$PY" "$FX/app_server.py" --port "$PORT" $1 --hits "$W/hits.log" --db "$W/app.db" >/dev/null 2>&1 &
  SRV=$!
  for _ in $(seq 1 40); do "$PY" -c "import urllib.request;urllib.request.urlopen('$URL/api/health',timeout=1)" 2>/dev/null && return 0; sleep 0.25; done
  echo "rehearsal: app mẫu không lên"; exit 1
}

prepare_out() {  # $1 = OUT (tương đối theo repo)
  mkdir -p "$1/tests/cli" "$1/results" "$1/monkey"
  cp "$SK/assets/package.json" "$SK/assets/playwright.config.ts" "$1/"
  cp "$SK/assets/out.gitignore" "$1/.gitignore"
  ( cd "$1" && npm install --no-audit --no-fund --loglevel=error >/dev/null 2>&1 ) || { echo "rehearsal: npm install hỏng"; exit 1; }
  ( cd "$1" && npx playwright install chromium >/dev/null 2>&1 ) || { echo "rehearsal: không cài được chromium"; exit 1; }
}

run_round() {  # $1 = OUT, $2 = tệp ca, $3.. = spec cần chép
  local OUT="$1" CASES="$2"; shift 2
  "$PY" "$SK/scripts/guard_repo.py" snapshot --repo . --allow "$OUT" --allow uat/_registry --state "$OUT/guard/state.json" >/dev/null
  "$PY" "$SK/scripts/validate_cases.py" --cases "$CASES" --out "$OUT" >/dev/null
  "$PY" "$SK/scripts/probe_env.py" --url "$URL" --need node --need browser --need bash --out "$OUT" >/dev/null
  for s in "$@"; do cp "$FX/specs/$s" "$OUT/tests/"; done
  cp "$FX/checks.json" "$OUT/tests/cli/checks.json"
  "$PY" "$SK/scripts/check_oracle_binding.py" --cases "$OUT/cases.json" --tests "$OUT/tests" --out "$OUT" >/dev/null || return 2
  "$PY" "$SK/scripts/canary.py" gen --out "$OUT" >/dev/null
  "$PY" "$SK/scripts/guard_repo.py" freeze-tests --state "$OUT/guard/state.json" --tests "$OUT/tests" >/dev/null || return 1
  ( cd "$OUT" && UAT_BASE_URL="$URL" UAT_JSON_OUT=results/pw-main.json npx playwright test >/dev/null 2>&1 ); true
  "$PY" "$SK/scripts/canary.py" verify --out "$OUT" --pw "$OUT/results/pw-main.json" >/dev/null; true
  "$PY" "$SK/scripts/run_cli_checks.py" --checks "$OUT/tests/cli/checks.json" --cwd . --out "$OUT/results/cli.json" >/dev/null
  "$PY" "$SK/scripts/merge_results.py" --cases "$OUT/cases.json" --pw "$OUT/results/pw-main.json" \
        --cli "$OUT/results/cli.json" --out "$OUT/results.json" >/dev/null
  # chạy lại RIÊNG các ca FAIL (khớp tag neo hai đầu) để đo độ tái hiện
  local G
  G=$("$PY" -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));ids=[r['tc_id'] for r in d['results'] if r['status']=='FAIL' and r['platform'] in ('web','api','hybrid-webview')];print('|'.join('@'+i+'(?![A-Za-z0-9-])' for i in ids))" "$OUT/results.json")
  if [ -n "$G" ]; then
    ( cd "$OUT" && UAT_BASE_URL="$URL" UAT_JSON_OUT=results/pw-rerun.json npx playwright test --grep "$G" >/dev/null 2>&1 ); true
  fi
  ( cd "$OUT" && node "$SK/scripts/monkey_web.mjs" --url "$URL" --seed 7 --actions 80 --max-seconds 90 --out monkey >/dev/null 2>&1 ); true
  # Tầng sâu: quyền/IDOR (G14) · dữ liệu+audit+idempotency (G15) · hiệu năng (G17).
  # Token vai và DSN đến từ MÔI TRƯỜNG, không bao giờ từ uat.json.
  UAT_TOKEN_KE_TOAN=T-KETOAN UAT_TOKEN_DIEU_DUONG=T-DD UAT_BASE_URL="$URL" "$PY" "$SK/scripts/role_matrix.py" --cases "$OUT/cases.json" --out "$OUT/results/idor.json" >/dev/null 2>&1; true
  UAT_DB_DSN="sqlite:$WNAT/app.db" UAT_BASE_URL="$URL" "$PY" "$SK/scripts/db_assert.py" --cases "$OUT/cases.json" --out "$OUT/results/db.json" >/dev/null 2>&1; true
  UAT_BASE_URL="$URL" "$PY" "$SK/scripts/run_perf.py" --cases "$OUT/cases.json" --out "$OUT/results/perf.json" >/dev/null 2>&1; true
  local RR=(); [ -f "$OUT/results/pw-rerun.json" ] && RR=(--rerun "$OUT/results/pw-rerun.json")
  "$PY" "$SK/scripts/merge_results.py" --cases "$OUT/cases.json" --pw "$OUT/results/pw-main.json" "${RR[@]}" \
        --cli "$OUT/results/cli.json" --checks security="$OUT/results/idor.json" \
        --checks db="$OUT/results/db.json" --checks perf="$OUT/results/perf.json" \
        --out "$OUT/results.json" >/dev/null
  ( cd "$OUT" && node "$SK/scripts/run_a11y.mjs" --url "$URL" --specs tests --out a11y.json >/dev/null 2>&1 ); true
  "$PY" "$SK/scripts/guard_repo.py" verify --state "$OUT/guard/state.json" --report "$OUT/guard/guard.json" >/dev/null
  "$PY" "$SK/scripts/check_evidence.py" --out "$OUT" --repo . >/dev/null; true
  "$PY" "$SK/scripts/registry.py" --registry uat/_registry record --out "$OUT" --repo . >/dev/null; true
  "$PY" "$SK/scripts/build_report.py" --out "$OUT" --repo . --pw-version 1.62.1 --title "diễn tập" >/dev/null
}

# PYTHONIOENCODING: console Windows hay là cp932, mà mọi giá trị cần so đều có dấu
# (ĐẠT, CẦN NGƯỜI, GO-CHỜ-KÝ). Thiếu dòng này thì khẳng định nào cũng trượt vì lỗi in,
# chứ không phải vì phép đo sai — một lỗi của giàn kiểm thử đội lốt lỗi của sản phẩm.
v() { PYTHONIOENCODING=utf-8 "$PY" -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));print(eval(sys.argv[2]))" "$1" "$2"; }

echo "── chuẩn bị không gian chạy (npm + chromium)"
prepare_out uat/run/r1
mkdir -p uat/run/r2 && cp -r uat/run/r1/node_modules uat/run/r1/package.json uat/run/r1/playwright.config.ts uat/run/r1/.gitignore uat/run/r2/ 2>/dev/null
mkdir -p uat/run/r2/tests/cli uat/run/r2/results uat/run/r2/monkey

echo "── lượt 1: app CÓ LỖI, kế hoạch thiếu kịch bản + một ca không hợp lệ"
start_app ""
run_round uat/run/r1 "$FX/uat.json" demo.e2e.spec.ts demo.api.spec.ts
R1=uat/run/r1
chk "kết luận NO-GO"                                  '[ "$(v $R1/verdict.json "d[\"verdict\"]")" = NO-GO ]'
chk "harness VERDICT: FAIL"                            'grep -q "^VERDICT: FAIL" $R1/verdict.txt'
chk "TC-DEMO-001 (P0) ĐẠT"                             '[ "$(v $R1/results.json "[r[\"status\"] for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-001\"][0]")" = PASS ]'
chk "TC-DEMO-002 (api) ĐẠT"                            '[ "$(v $R1/results.json "[r[\"status\"] for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-002\"][0]")" = PASS ]'
chk "TC-DEMO-003 KHÔNG ĐẠT, tái hiện 2/2"              '[ "$(v $R1/results.json "[r[\"status\"]+r.get(\"repro\",\"\") for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-003\"][0]")" = FAIL2/2 ]'
chk "TC-DEMO-004 KHÔNG CHẠY (không có kịch bản)"       '[ "$(v $R1/results.json "[r[\"reason\"] for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-004\"][0]")" = khong-co-kich-ban ]'
chk "TC-DEMO-005 KHÔNG CHẠY (ca không hợp lệ)"         '[ "$(v $R1/results.json "[r[\"reason\"] for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-005\"][0]")" = ca-khong-hop-le ]'
chk "TC-DEMO-006 (cli) ĐẠT"                            '[ "$(v $R1/results.json "[r[\"status\"] for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-006\"][0]")" = PASS ]'
chk "G2 hỏng vì P1 không chạy"                         '[ "$(v $R1/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G2\"][0]")" = HỎNG ]'
chk "monkey bắt pageerror"                             'grep -q "\"type\": \"pageerror\"" $R1/monkey/web-7.json'
chk "monkey bắt HTTP 5xx"                              'grep -q "\"type\": \"http5xx\"" $R1/monkey/web-7.json'
chk "G8 hỏng"                                          '[ "$(v $R1/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G8\"][0]")" = HỎNG ]'
chk "monkey KHÔNG bấm nút cấm «Xóa tất cả»"            '[ ! -s "$W/hits.log" ]'
chk "rào: repo sản phẩm sạch"                          '[ "$(v $R1/guard/guard.json "d[\"ok\"]")" = True ]'
chk "G11 chứng âm ĐẠT — bộ đo có thể bắt lỗi"          '[ "$(v $R1/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G11\"][0]")" = ĐẠT ]'
chk "cả 3 mệnh đề chứng âm đều đỏ"                     '[ "$(v $R1/canary.json "len(d[\"green\"])==0 and len(d[\"found\"])==3")" = True ]'
chk "G10 oracle-binding ĐẠT"                           '[ "$(v $R1/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G10\"][0]")" = ĐẠT ]'
chk "G9 rào ĐẠT bằng phương thức git"                  '[ "$(v $R1/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G9\"][0]")" = ĐẠT ]'
chk "chứng âm KHÔNG lọt vào mẫu số"                    '[ "$(v $R1/results.json "d[\"counts\"][\"total\"]")" = 10 ]'
chk "chứng âm KHÔNG bị tính là test lạc"               '[ "$(v $R1/results.json "len(d[\"unmatched_tests\"])")" = 0 ]'
chk "sổ lỗi ghi được lượt này"                         '[ -f uat/_registry/runs.json ]'
chk "G14 bắt IDOR: vai sai và vai vô danh đều nhận 200" '[ "$(v $R1/results.json "[r[\"status\"] for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-007\"][0]")" = FAIL ]'
chk "G15 bắt dữ liệu sai dưới DB dù màn hình xanh"      '[ "$(v $R1/results.json "[r[\"status\"] for r in d[\"results\"] if r[\"tc_id\"]==\"TC-DEMO-008\"][0]")" = FAIL ]'
chk "G15 bắt duplicate-on-retry (5 request → 5 đơn)"    'grep -q duplicate-on-retry $R1/results.json'
chk "G17 hiệu năng chạy và ghi được số đo p95"          'grep -q p95_ms $R1/results/perf.json'
chk "G4/G6/G7 = CẦN NGƯỜI"                             '[ "$(v $R1/verdict.json "\",\".join(g[\"state\"] for g in d[\"gates\"] if g[\"gate\"] in (\"G4\",\"G6\",\"G7\"))")" = "CẦN NGƯỜI,CẦN NGƯỜI,CẦN NGƯỜI" ]'
chk "git status repo sản phẩm không có gì ngoài uat/" '[ -z "$(git status --porcelain --untracked-files=all | grep -v " uat/")" ]'

echo "── lượt 2: app lành, đủ kịch bản (ca P2 cố ý sai vẫn còn)"
"$PY" -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));d['test_cases']=[t for t in d['test_cases'] if t['tc_id']!='TC-DEMO-005'];json.dump(d,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)" "$FX/uat.json" "$W/uat2.json"
start_app --healthy
run_round uat/run/r2 "$W/uat2.json" demo.e2e.spec.ts demo.api.spec.ts about.e2e.spec.ts
R2=uat/run/r2
chk "kết luận GO-CHỜ-KÝ"                               '[ "$(v $R2/verdict.json "d[\"verdict\"]")" = GO-CHỜ-KÝ ]'
chk "harness VERDICT: PASS"                            'grep -q "^VERDICT: PASS" $R2/verdict.txt'
chk "ca P2 sai vẫn nằm trong FINDINGS"                 'grep -q "TC-DEMO-003" $R2/verdict.txt'
chk "G8 đạt khi app lành"                              '[ "$(v $R2/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G8\"][0]")" = ĐẠT ]'


chk "G14 ĐẠT khi máy chủ chặn đúng"                        '[ "$(v $R2/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G14\"][0]")" = ĐẠT ]'
chk "G15 ĐẠT khi DB đúng và idempotency đúng"             '[ "$(v $R2/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G15\"][0]")" = ĐẠT ]'
chk "G17 ĐẠT trong ngân sách người đặt"                   '[ "$(v $R2/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G17\"][0]")" = ĐẠT ]'
chk "G13 phủ yêu cầu ĐẠT"                                 '[ "$(v $R2/verdict.json "[g[\"state\"] for g in d[\"gates\"] if g[\"gate\"]==\"G13\"][0]")" = ĐẠT ]'

echo "── lượt 3: can thiệp phải bị bắt"
mkdir -p uat/run/r3/tests
"$PY" "$SK/scripts/guard_repo.py" snapshot --repo . --allow uat/run/r3 --state uat/run/r3/guard/state.json >/dev/null
printf "import { test } from '@playwright/test';\ntest.skip('TC-DEMO-001 x', async () => {});\n" > uat/run/r3/tests/x.e2e.spec.ts
"$PY" "$SK/scripts/guard_repo.py" freeze-tests --state uat/run/r3/guard/state.json --tests uat/run/r3/tests >/dev/null; RC=$?
chk "spec có test.skip → TỪ CHỐI đóng băng"            '[ $RC -eq 1 ]'
printf "import { test, expect } from '@playwright/test';\ntest('TC-DEMO-001 y', async ({page}) => { expect(1).toBe(1); });\n" > uat/run/r3/tests/x.e2e.spec.ts
"$PY" "$SK/scripts/guard_repo.py" freeze-tests --state uat/run/r3/guard/state.json --tests uat/run/r3/tests >/dev/null
echo "// sửa sau đóng băng" >> uat/run/r3/tests/x.e2e.spec.ts
"$PY" "$SK/scripts/guard_repo.py" verify --state uat/run/r3/guard/state.json --report uat/run/r3/guard/guard.json >/dev/null; RC=$?
chk "sửa spec sau đóng băng → verify thoát 1"          '[ $RC -eq 1 ]'
"$PY" "$SK/scripts/guard_repo.py" snapshot --repo . --allow uat/run/r3 --state uat/run/r3/guard/state2.json >/dev/null
echo "sửa lén" >> src/app.txt
"$PY" "$SK/scripts/guard_repo.py" verify --state uat/run/r3/guard/state2.json --report uat/run/r3/guard/guard.json >/dev/null; RC=$?
chk "sửa tệp sản phẩm → verify thoát 1"                '[ $RC -eq 1 ]'
cp uat/run/r2/cases.json uat/run/r2/results.json uat/run/r2/probe.json uat/run/r3/ 2>/dev/null
"$PY" "$SK/scripts/build_report.py" --out uat/run/r3 --repo . >/dev/null
chk "rào vi phạm → BÁO CÁO VÔ HIỆU, VERDICT: FAIL"     '[ "$(v uat/run/r3/verdict.json "d[\"verdict\"]")" = "BÁO CÁO VÔ HIỆU" ] && grep -q "^VERDICT: FAIL" uat/run/r3/verdict.txt'

echo
echo "rehearsal: $PASS đạt, $FAIL trượt"
[ "$FAIL" -eq 0 ]
