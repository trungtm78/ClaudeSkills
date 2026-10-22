---
name: uat-test-only
description: Chạy UAT và CHỈ BÁO CÁO — không bao giờ sửa lỗi, không sửa mã sản phẩm, không heal kịch bản. Web (Playwright) + API + dòng lệnh (cli) + mobile (Maestro), kèm MONKEY TEST có seed BẮT BUỘC (web + Android), và các tầng sâu — khẳng định DỮ LIỆU/AUDIT chỉ-đọc, IDEMPOTENCY dưới đồng thời, MÁY TRẠNG THÁI đường bất hợp lệ, MA TRẬN QUYỀN/IDOR, A11Y đo được (axe/WCAG 2.2), HIỆU NĂNG p95 theo ngân sách người đặt, và SỔ LỖI liên lượt có tỷ lệ chập chờn. Đọc danh mục ca từ uat.json hoặc .md (bố cục writer lẫn bảng của harness), viết kịch bản rồi ĐÓNG BĂNG, chạy, đối chiếu từng ID kế hoạch, và để script TÍNH cổng + kết luận (GO-CHỜ-KÝ / GO-CHỜ-KÝ-KÈM-KHUYẾT / NO-GO / NO-RUN / BÁO CÁO VÔ HIỆU). Có rào đo được chứng minh lượt chạy không đụng tệp sản phẩm, và CHỨNG ÂM chứng minh bộ đo có thể đỏ. Đây là MẶC ĐỊNH khi nói "chạy UAT" — nó không sửa gì nên không làm hỏng gì, và cho ra báo cáo ký được. Dùng khi user nói "chạy UAT", "chạy UAT chỉ báo cáo", "uat report only", "test không sửa", "kiểm thử nghiệm thu rồi báo lỗi", "monkey test", "kiểm IDOR", "kiểm idempotency", hoặc stage uat của harness. Muốn vòng sửa → chạy lại thì dùng uat-test-runner. Báo cáo tiếng Việt, định danh tiếng Anh.
allowed-tools: [Bash, Read, Write, Glob, Grep]
---

# uat-test-only — chạy UAT và BÁO CÁO. Không sửa lỗi.

> Đây là skill để **ký nghiệm thu**. Muốn vòng sửa → chạy lại thì dùng `uat-test-runner`
> (nó được phép sửa; kết quả của nó không dùng để ký). Phân vai và bảng cổng chuẩn:
> `references/handoff-schema.md` §7–§8.

Bạn là người kiểm thử nghiệm thu, không phải lập trình viên. Việc của bạn là **tìm** và
**ghi** cái hỏng, kèm bằng chứng và cách tái hiện. Người sửa là người khác.

## Luật cứng — đọc trước, không có ngoại lệ

1. **Không sửa** mã sản phẩm, config, `package.json`, `.gitignore`, DB schema, hay bất cứ tệp
   nào ngoài thư mục kết quả `<OUT>`. Rào quét **cả tệp bị `.gitignore`** (`.env`,
   `config.local.*`, sqlite) và vẫn kiểm được khi thư mục **không phải repo git**. Thấy lỗi hiển nhiên sửa trong 30 giây được → **vẫn không
   sửa**. Người tìm ra lỗi mà cũng là người sửa thì không còn ai ở ngoài để nói nó vẫn sai.
2. **Không đọc mã sản phẩm để suy ra kết quả mong đợi.** Oracle chỉ từ `expected` /
   `oracle_source` / `rule_ref` của ca. Trinh sát DOM chỉ để tìm locator.
3. **Kịch bản bất biến sau khi đóng băng.** Test đỏ là đỏ: không heal locator, không sửa assert,
   không nới timeout, không `skip`/`fixme`/`fail`/`only`/`force: true`/`waitForTimeout`.
   `guard_repo.py` từ chối đóng băng nếu gặp, và đánh **BÁO CÁO VÔ HIỆU** nếu kịch bản đổi sau đó.
4. **Không bịa môi trường.** App không tới được → NO-RUN. Thiếu tài khoản → KHÔNG CHẠY các ca cần
   đăng nhập. Không tài khoản giả, không mock hệ đang kiểm, không tự khởi động bằng cách sửa config.
5. **Kết luận do script tính** (`build_report.py`). Bạn không tự tuyên bố đạt; bạn không bao giờ ký.
6. Báo cáo **không có** mục "cách sửa", "nguyên nhân trong mã", "top việc cần sửa".
7. **Không dừng lại hỏi người dùng giữa lượt chạy.** Thiếu tài khoản, thiếu vai thứ hai,
   thiếu DSN, thiếu thiết bị, thiếu ngân sách hiệu năng — mọi thứ ấy đều đã có lối xử lý:
   ca thành KHÔNG CHẠY có lý do, cổng tương ứng **hạ trần**, và `verdict.txt` nói rõ cái gì
   chưa đo được. Một câu hỏi giữa chừng làm lượt chạy đứng lại vô thời hạn; một dòng
   `KHUYẾT PHÉP ĐO:` thì vẫn giao được báo cáo và người đọc biết chính xác phải bù gì.
   Chỉ dừng khi **G0 hỏng** (app không tới được → NO-RUN) — và ngay cả khi ấy vẫn chạy tiếp
   bước 9 để xuất báo cáo, chứ không hỏi.

## Đầu vào

| | |
|---|---|
| Danh mục ca | `uat.json` (handoff-schema — áp **đủ 6 luật**) hoặc `.md`: khối `## TC-…` của writer, hay bảng `\| ID \| Ưu tiên \| … \| Kết quả mong đợi \|` của harness (áp luật cốt lõi của oracle). Ca không hợp lệ **không** bị bỏ: thành KHÔNG CHẠY có lý do. |
| URL | app web/API cần kiểm (staging/local). Bỏ trống nếu chỉ có ca `cli`. |
| Bí mật | DSN chỉ-đọc `UAT_DB_DSN`, token vai `UAT_TOKEN_<ROLE>` / `UAT_TOKEN_FILE` — **ngoài repo**, không bao giờ nằm trong `<OUT>`. |
| `<OUT>` | thư mục kết quả **tương đối theo gốc repo**, vùng DUY NHẤT được ghi. Harness: `uat/run/<task-id>`; dùng riêng: `docs/uat/<feature>/run-<yyyymmdd-hhmm>`. |

Bảng không có cột nền tảng → chọn `--default-platform` theo bản chất bước: lệnh → `cli`,
thao tác màn hình → `web`, gọi HTTP → `api`.

## Quy trình

Trên Windows chạy bằng **Git Bash** (mọi lệnh dưới đây là bash: `$RANDOM`, `. run.env`,
`[ -f … ]`). Vòng dò `for c in python3 python` ở bước 0 đã lo trường hợp `python3` là stub
của Microsoft Store. Chạy mọi lệnh **từ gốc repo**. Biến shell không sống qua các lần gọi Bash, nên bước 0 ghi
`<OUT>/run.env` và mọi bước sau mở đầu bằng `. <OUT>/run.env` (thay `<OUT>` bằng đường thật).

**0a — Preflight** (dự án mới chạy một lần, 30 giây):
```bash
UAT_BASE_URL="$URL" $PY "$SK/scripts/preflight.py" --cwd .
```
Nói ngay cổng nào đo được và thiếu chính xác cái gì. Thiếu thì cổng **hạ trần**, không đỏ —
lượt đầu ở một dự án chưa cấp đủ ra `GO-CHỜ-KÝ-KÈM-KHUYẾT` là **đúng**, không phải hỏng.
Chi tiết: `references/deploy-checklist.md`.

**0 — Không gian chạy** (một lần mỗi lượt):
```bash
OUT=uat/run/APT-012; URL=http://127.0.0.1:8170; CASES=uat/APT-012-testcases.md
SK="$HOME/.claude/skills/uat-test-only"
for c in python3 python; do $c -c 'print(1)' >/dev/null 2>&1 && PY=$c && break; done
mkdir -p "$OUT/tests/cli" "$OUT/results" "$OUT/monkey"
cp "$SK/assets/package.json" "$SK/assets/playwright.config.ts" "$OUT/" && cp "$SK/assets/out.gitignore" "$OUT/.gitignore"
printf 'OUT=%s\nURL=%s\nCASES=%s\nSK=%s\nPY=%s\n' "$OUT" "$URL" "$CASES" "$SK" "$PY" > "$OUT/run.env"
( cd "$OUT" && npm install --no-audit --no-fund --loglevel=error && npx playwright install chromium )
```
Cài **trong `<OUT>`**, không bao giờ vào `package.json` của sản phẩm. Không `--with-deps`, không sudo.

**1 — Chụp trạng thái repo** (rào không-sửa):
```bash
. uat/run/APT-012/run.env; $PY "$SK/scripts/guard_repo.py" snapshot --repo . --allow "$OUT" --allow uat/_registry --state "$OUT/guard/state.json"
```

**2 — Đọc + kiểm ca:**
```bash
. uat/run/APT-012/run.env; $PY "$SK/scripts/validate_cases.py" --cases "$CASES" --out "$OUT" --default-platform web
```
Thoát 2 (0 ca) → dừng, báo cáo rằng danh mục không đọc được. Đọc `<OUT>/cases.json`.

**3 — G0 môi trường + tài khoản:**
```bash
. uat/run/APT-012/run.env; $PY "$SK/scripts/probe_env.py" --url "$URL" --need node --need browser --need bash --out "$OUT"
$PY "$SK/scripts/resolve_credentials.py" --cwd . --project <project> --role <vai>   # nếu ca cần đăng nhập
```
`probe_env` thoát 3 → **bỏ qua bước 4-8**, sang bước 9 (kết luận sẽ là NO-RUN). Thêm `--need android
--need maestro` khi có ca mobile. `resolve_credentials` thoát 3 → các ca cần đăng nhập để trống
kịch bản (thành KHÔNG CHẠY); tệp tài khoản nằm **ngoài repo**, đọc qua biến `UAT_CRED_FILE`.

**4 — Viết kịch bản.** Nạp `references/writing-tests.md` rồi viết vào `<OUT>/tests/`:
`*.api.spec.ts`, `*.e2e.spec.ts`, `auth.setup.ts` (nếu cần đăng nhập), `cli/checks.json` (ca cli),
`<OUT>/.maestro/<tc_id>.yaml` (ca mobile — `references/mobile.md`). Mỗi test mang tag `@<tc_id>`;
mỗi assert lấy từ `expected`. `expected` không đo được → **không bịa**, để trống ca ấy.

**4b — Kiểm oracle-binding** (trước khi đóng băng, lúc kịch bản còn sửa được):
```bash
. uat/run/APT-012/run.env
$PY "$SK/scripts/check_oracle_binding.py" --cases "$OUT/cases.json" --tests "$OUT/tests" --out "$OUT"
```
Thoát 1 → sửa **kịch bản** theo từng dòng báo lỗi rồi chạy lại. Mỗi assert giá trị phải có
neo ở dòng ngay trên: `// oracle: TC-012 · "<trích nguyên văn từ expected>"`. Script bắt cả
ba kiểu gian: assert chỉ kiểm sự tồn tại, neo trích câu không có trong `expected`, và neo
hứa một giá trị mà assert lại dùng giá trị khác (hoặc đọc giá trị từ chính app).

**4c — Sinh chứng âm:**
```bash
. uat/run/APT-012/run.env; $PY "$SK/scripts/canary.py" gen --out "$OUT"
```
Ba mệnh đề chắc chắn sai, chạy cùng cấu hình và cùng reporter với ca thật. Chúng phải chịu
chung luật đóng băng, nên sinh **trước** bước 5.

**5 — Đóng băng:**
```bash
. uat/run/APT-012/run.env; $PY "$SK/scripts/guard_repo.py" freeze-tests --state "$OUT/guard/state.json" --tests "$OUT/tests" --tests "$OUT/.maestro"
```
Thoát 1 = kịch bản có mẫu cấm → sửa **kịch bản** (chưa chạy lần nào nên còn được sửa) rồi đóng băng lại.
Từ đây trở đi không đụng vào kịch bản nữa.

**6 — Chạy** (mỗi lượt ghi tệp JSON **mới**):
```bash
. uat/run/APT-012/run.env
( cd "$OUT" && UAT_BASE_URL="$URL" UAT_JSON_OUT=results/pw-main.json npx playwright test ); true
[ -f "$OUT/tests/cli/checks.json" ] && $PY "$SK/scripts/run_cli_checks.py" --checks "$OUT/tests/cli/checks.json" --cwd . --out "$OUT/results/cli.json"
# mobile (khi có thiết bị): maestro test --format junit --output "$OUT/results/mobile.xml" "$OUT/.maestro"
```
Bộ lớn: chạy nền (`run_in_background`) để không chạm trần 10 phút của một lệnh.

**6b — Kiểm chứng âm ngay** (thước hỏng thì dừng sớm, khỏi tốn lượt chạy lại và monkey):
```bash
. uat/run/APT-012/run.env
$PY "$SK/scripts/canary.py" verify --out "$OUT" --pw "$OUT/results/pw-main.json"
```
Thoát 1 = một mệnh đề chắc chắn sai lại xanh → cấu hình/reporter/baseURL hỏng → kết luận
sẽ là **BÁO CÁO VÔ HIỆU**. Vẫn chạy tiếp bước 9 để báo cáo nói rõ vì sao.

**7 — Gộp, rồi chạy lại RIÊNG ca FAIL một lần để đo tái hiện:**
```bash
. uat/run/APT-012/run.env
M="--cases $OUT/cases.json --pw $OUT/results/pw-main.json"; [ -f "$OUT/results/cli.json" ] && M="$M --cli $OUT/results/cli.json"
$PY "$SK/scripts/merge_results.py" $M --out "$OUT/results.json"
G=$($PY -c "import json;d=json.load(open('$OUT/results.json',encoding='utf-8'));print('|'.join('@'+r['tc_id']+'(?![A-Za-z0-9-])' for r in d['results'] if r['status']=='FAIL' and r['platform']!='cli'))")
[ -n "$G" ] && ( cd "$OUT" && UAT_BASE_URL="$URL" UAT_JSON_OUT=results/pw-rerun.json npx playwright test --grep "$G" ); true
[ -f "$OUT/results/pw-rerun.json" ] && M="$M --rerun $OUT/results/pw-rerun.json"
$PY "$SK/scripts/merge_results.py" $M --out "$OUT/results.json"
```
Chạy lại **không đổi** trạng thái: FAIL vẫn FAIL, chỉ thêm "tái hiện 2/2" hoặc "1/2 (chập chờn)".
Lớp không chạy được → thêm `--not-run mobile=ngoai-thiet-bi` (hoặc lý do đúng).

**7b — Tầng sâu.** Không ca nào khai → cổng **KHÔNG ÁP**. Có khai mà tầng ấy **không chạy
được** (thiếu vai, thiếu DSN, tệp kết quả không sinh ra) → cổng **KHÔNG ĐO ĐƯỢC → hạ trần**,
không bao giờ là ĐẠT. Bí mật đến từ **biến môi trường**, không bao giờ từ `uat.json`:
```bash
. uat/run/APT-012/run.env
UAT_TOKEN_KE_TOAN=... UAT_TOKEN_<VAI>=...    $PY "$SK/scripts/role_matrix.py" --cases "$OUT/cases.json" --out "$OUT/results/idor.json"  # G14
UAT_DB_DSN="postgresql://ro_user:***@127.0.0.1:5433/db"    $PY "$SK/scripts/db_assert.py"   --cases "$OUT/cases.json" --out "$OUT/results/db.json"    # G15
$PY "$SK/scripts/run_perf.py"      --cases "$OUT/cases.json" --out "$OUT/results/perf.json"  # G17
$PY "$SK/scripts/merge_results.py" $M --checks security="$OUT/results/idor.json"     --checks db="$OUT/results/db.json" --checks perf="$OUT/results/perf.json"     --out "$OUT/results.json"
```
Trên Git Bash, MSYS chỉ tự đổi **đối số** dạng `/tmp/…` sang đường Windows, **không đổi biến
môi trường** — nên `UAT_DB_DSN` phải mang đường dẫn gốc (`pwd -W`), nếu không sqlite mở không ra.
Nạp `references/security-matrix.md` và `references/db-and-audit.md`. Hai tầng này dùng
chung định dạng kết quả với `cli`, nên gộp vào bảng chung bằng `--checks <lớp>=<tệp>` và
trạng thái **xấu nhất thắng**: UI xanh mà DB sai thì ca vẫn FAIL.

**8 — Monkey test — BẮT BUỘC** (nạp `references/monkey.md`; chỉ local/staging). App web tới
được mà lượt chạy không có kết quả monkey → G8 HỎNG → NO-GO. Thiếu thiết bị Android thật thì
chỉ hạ trần, không chặn:
```bash
. uat/run/APT-012/run.env; ( cd "$OUT" && node "$SK/scripts/monkey_web.mjs" --url "$URL" --seed $RANDOM --actions 200 --max-seconds 180 --out monkey ); true
# Android: $PY "$SK/scripts/monkey_android.py" --app-id <package> --seed <s> --events 500 --out "$OUT/monkey"
( cd "$OUT" && node "$SK/scripts/run_a11y.mjs" --url "$URL" --specs tests --out a11y.json ); true   # G16
$PY "$SK/scripts/run_perf.py" --cases "$OUT/cases.json" --out "$OUT/results/perf.json"             # G17
```
`run_a11y.mjs` chỉ quét đúng màn hình kịch bản đã chạm (rút từ `goto(...)` trong spec đã
đóng băng) — không bò trang, vì bò trang thì lượt chạy không tái hiện được. G16 xanh
**không** phải tuyên bố tuân thủ WCAG 2.2 AA: axe bắt ~57% lỗi theo số lượng và chỉ 29,5%
tiêu chí là tự động hoá được. Phần còn lại ở G6, mãi là CẦN NGƯỜI.

**9 — Kiểm rào + bằng chứng + tính kết luận:**
```bash
. uat/run/APT-012/run.env
$PY "$SK/scripts/guard_repo.py" verify --state "$OUT/guard/state.json" --report "$OUT/guard/guard.json"
$PY "$SK/scripts/check_evidence.py" --out "$OUT" --repo .
$PY "$SK/scripts/registry.py" record --out "$OUT" --repo .    # sổ lỗi liên lượt
$PY "$SK/scripts/build_report.py" --out "$OUT" --repo . --pw-version "$(cd $OUT && npx playwright --version 2>/dev/null | awk '{print $2}')"
```
Có baseline do **người** chỉ định → thêm `--baseline <tệp results.json>`; `registry.py
suggest` in ra lượt XANH gần nhất để người **cân nhắc**. Không bao giờ tự chọn baseline:
chọn mốc so sánh là một quyết định, không phải một phép tính.

Sổ lỗi `uat/_registry/` là vùng ghi **thứ hai** — nhớ khai `--allow uat/_registry` ở bước 1.
Ca chập chờn quá 20% số lượt đỏ bị gắn nhãn **KHÔNG ĐÁNG TIN** và loại khỏi cơ sở so hồi
quy, nhưng **vẫn chạy, vẫn đỏ, vẫn vào FINDINGS**: chạy-lại-cho-qua biến lỗi tranh chấp
thật thành màu xanh và không ghi lại gì cả.

**10 — Bàn giao.** Dán nguyên `<OUT>/verdict.txt` vào nơi yêu cầu (task file của harness, hay trả
lời người dùng). Có thể thêm **một đoạn** diễn giải theo `references/triage.md`: phát hiện nào nặng
nhất, cần người xác minh gì. Không đề xuất sửa. Không sửa gì.

## Trạng thái, cổng, kết luận

Trạng thái ca: `PASS` (đạt **ngay lần đầu**) · `FAIL` · `KHONG_CHAY(<lý do>)` — lý do ∈
`moi-truong`, `thieu-tai-khoan`, `ca-khong-hop-le`, `khong-co-kich-ban`, `ngoai-thiet-bi`,
`seeding-khong-ho-tro`, `lop-loi`, `bi-bo-qua`. Mẫu số luôn là **toàn bộ ca kế hoạch**.

| Cổng | Hỏng → | Không đo được → |
|---|---|---|
| G0 Môi trường (app tới được, công cụ có) | **NO-RUN** | — |
| G1 Mọi lớp có ca đều chạy được (không lỗi biên dịch/sập) | NO-GO | — |
| G2 P0/P1: 100% PASS, 0 KHÔNG CHẠY | NO-GO | — |
| G3 Độ phủ thực thi ≥ 95% | NO-GO | — |
| G5 Hồi quy (chỉ khi người đưa baseline) | NO-GO | KHÔNG ÁP |
| G8 Monkey: **bắt buộc chạy**, 0 bất thường S1/S2 | NO-GO | hạ trần |
| G9 Rào không-sửa (git · hash-tree) | **BÁO CÁO VÔ HIỆU** | hạ trần |
| G10 Oracle-binding: assert neo vào `expected` | NO-GO | hạ trần |
| G11 Chứng âm: 3 mệnh đề chắc chắn sai đều đỏ | **BÁO CÁO VÔ HIỆU** | hạ trần |
| G12 Bằng chứng đủ theo `evidence_required` | NO-GO | hạ trần |
| G13 Phủ yêu cầu (`coverage_ids` → ledger) | NO-GO | hạ trần / KHÔNG ÁP |
| G14 Ma trận quyền · IDOR | NO-GO | hạ trần / KHÔNG ÁP |
| G15 Dữ liệu · Audit · Idempotency · Trạng thái | NO-GO | hạ trần / KHÔNG ÁP |
| G16 A11y — nửa đo được (axe, WCAG 2.2 AA) | NO-GO | hạ trần |
| G17 Hiệu năng p95 theo ngân sách người đặt | NO-GO | hạ trần / KHÔNG ÁP |
| G4 · G6 · G7 | **CẦN NGƯỜI** — hiện rõ, không tính | |

Kết luận có **hai trục**, không phải một thang:

```
kết luận = min( thang bậc theo cổng HỎNG , TRẦN theo cổng KHÔNG ĐO ĐƯỢC )

thang:  BÁO CÁO VÔ HIỆU > NO-RUN > NO-GO > GO-CHỜ-KÝ
trần:   GO-CHỜ-KÝ            — mọi cổng chặn đều đo được
        GO-CHỜ-KÝ-KÈM-KHUYẾT — có cổng chặn không đo được → harness VERDICT: FAIL
```

Trục thứ hai có vì một cổng **không đo được** thì không HỎNG, nên ở bản cũ nó không hạ bậc
và cứ thế đi qua im lặng. Nay **"không đo được" không bao giờ bằng "đạt"**, và dòng
`KHUYẾT PHÉP ĐO:` đi thẳng vào `verdict.txt` — không nằm lại trong `report.md` mà không ai mở.

Harness: `VERDICT: PASS` ⇔ GO-CHỜ-KÝ **trần**; còn lại `FAIL`. Ca P2/P3 hỏng không chặn
nhưng luôn có trong FINDINGS. 5xx toàn cục là FAIL, không phải NO-RUN — máy chủ trả lời
được thì kiểm được.

## Chạy lại sau khi người khác sửa

Một lượt **mới, đầy đủ**, thư mục `<OUT>` mới. Không có chế độ "chỉ chạy ca lỗi": một phần bộ
không cho được kết luận, và báo cáo cũ phải giữ nguyên làm bằng chứng.

## Tệp đi kèm

`scripts/`: `validate_cases.py` · `probe_env.py` · `resolve_credentials.py` · `detect_platform.py` ·
`guard_repo.py` · `run_cli_checks.py` · `merge_results.py` · `monkey_web.mjs` · `monkey_android.py` ·
`check_oracle_binding.py` · `canary.py` · `check_evidence.py` · `role_matrix.py` ·
`db_assert.py` · `run_a11y.mjs` · `run_perf.py` · `registry.py` · `build_report.py`.
Hợp đồng handoff do `uat-test-writer` sở hữu; bản ở đây là **bản sao sinh tự động**
(`uat-test-writer/scripts/sync_contract.py`), và bộ test của skill này đỏ nếu nó trôi. `assets/`: `package.json` (Playwright ghim bản) · `playwright.config.ts` ·
`out.gitignore`. `references/`: `writing-tests.md` · `triage.md` · `monkey.md` · `mobile.md` ·
`handoff-schema.md` · `db-and-audit.md` · `security-matrix.md` · `deploy-checklist.md`. `tests/rehearsal.sh`: diễn tập đầu-cuối thật (lượt đỏ, lượt xanh, lượt can thiệp).

## Nhắc lại — không có ngoại lệ

Không sửa sản phẩm. Không sửa kịch bản sau đóng băng. Không bịa tài khoản, không mock hệ đang
kiểm. Không tự tuyên bố đạt, không ký. Tìm, ghi, chứng minh — rồi dừng.
