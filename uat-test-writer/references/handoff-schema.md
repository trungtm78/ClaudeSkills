# Handoff Schema v2 — hợp đồng writer → {runner | test-only}

> **TỆP NÀY LÀ NGUỒN SỰ THẬT DUY NHẤT.** Hai bản trong `uat-test-runner/references/` và
> `uat-test-only/references/` là **bản sao sinh tự động** — đừng sửa tay ở đó.
> Sửa ở đây rồi chạy:
>
> ```bash
> python "$HOME/.claude/skills/uat-test-writer/scripts/sync_contract.py"          # đồng bộ
> python "$HOME/.claude/skills/uat-test-writer/scripts/sync_contract.py" --check   # kiểm trôi
> ```
>
> Hợp đồng có **ba** bên, không phải hai:
>
> | Bên | Vai | Được sửa mã sản phẩm? |
> |---|---|---|
> | `uat-test-writer` | thiết kế ca, sinh `uat.json` | không — không chạy gì |
> | `uat-test-only` | thực thi + **phán xét**, chỉ báo cáo | **không bao giờ** |
> | `uat-test-runner` | vòng sửa → chạy lại cho dev | có, đó là việc của nó |
>
> Đổi schema = đổi **cả ba** cùng lúc. `sync_contract.py --check` là cái cưỡng chế điều đó,
> và nó chạy trong bộ test của `uat-test-only`.

## 1. File-level

```jsonc
{
  "feature": "quan-ly-don",
  "generated_at": "<ISO datetime>",
  "platform_contract": "docs/uat/_platform.json",   // Bước 0.7
  "domain_pack": "docs/uat/_domain-pack.md",
  "coverage_ledger": "docs/uat/quan-ly-don/_coverage-ledger.md",
  "evidence_profile": "signoff",                     // "ci" | "signoff" — runner chọn cấu hình evidence
  "test_cases": [ /* xem §2 */ ],
  "data_fixtures": [ /* Data Maturity Matrix — như cũ */ ]
}
```

## 2. Test case — field bắt buộc (✱) và tuỳ chọn

```jsonc
{
  "tc_id": "TC-012",                          // ✱ duy nhất, ổn định giữa các run (baseline diff)
  "title": "Kế toán từ chối đơn thiếu chứng từ",   // ✱ business outcome, không phải thao tác UI
  "type": "RED",                              // ✱ GREEN|RED|EDGE|BOUNDARY|EP|STATE|DECISION|SECURITY|DATA|PERFORMANCE|A11Y|COMPAT|UX|E2E|EXPLORATORY|METAMORPHIC|PERMISSIONS|DEEPLINK|PUSH|OFFLINE|LIFECYCLE|GESTURE|SCREENSIZE|BIOMETRIC|INTERRUPT|INSTALL|MOBILE-A11Y|MOBILE-SEC
  "platform": "android",                      // ✱ web|android|ios|api|hybrid-webview
  "target": "simulator-ok",                   // mobile: simulator-ok | real-device-required
  "persona": "ke-toan",                       // ✱ từ Persona matrix
  "journey_ref": "J-APPROVE-02",              // ✱ ô trong Persona×Journey×Platform matrix
  "priority": "P0",                           // ✱ P0-P3 (nghiệp vụ)
  "severity_if_fail": "S2",                   // ✱ S1-S4 (kỹ thuật)

  "oracle_type": "Statute",                   // ✱ FEW HICCUPPS hoặc GAP
  "rule_ref": "APPROVE-EVIDENCE-REQ",         // ✱ id trong _domain-pack / AC id
  "oracle_source": "Statutes → Thông tư XX §5.2",  // ✱ trích dẫn cụ thể — thiếu = reject
  "catches_bug": "Server bỏ guard chứng từ → đơn thiếu chứng từ vẫn duyệt được",  // ✱ bug cụ thể TC bắt

  "coverage_ids": ["COV-DT-04", "COV-E2E-02"],// ✱ trỏ Coverage Ledger — 0 TC mồ côi
  "backend_policy": "live",                   // ✱ live | mocked-3p | mocked-error-injection (+ lý do nếu mock)
  "data_required": ["don.pending.D0.thieu-chungtu"],  // fixture id từ Data Matrix
  "determinism": {                             // khai báo để runner setup — thiếu = runner tự suy + ghi chú
    "auth_role": "ke-toan",
    "clock_freeze": null,                      // ISO datetime nếu TC phụ thuộc thời gian
    "network_stubs": [],                       // chỉ 3rd-party / error-injection
    "serial": false                            // true = mutate shared singleton, chạy tuần tự (kèm lý do)
  },
  "locator_hint": "role=button[name='Từ chối'] / testID=btn-reject",  // a11y-label-first; mobile bắt buộc
  "seeding_method": "api",                    // api | sql | snapshot (+ justification khi sql)

  "gherkin": "Given đơn ở trạng thái chờ duyệt và thiếu chứng từ\nWhen kế toán thao tác từ chối\nThen đơn chuyển REJECTED và người nộp nhận thông báo kèm lý do",
  "steps": "1. ...\n2. ...",                  // ✱ bước business-level, declarative
  "expected": "…",                            // ✱ hành vi đo được — KHÔNG chỉ HTTP code
  "evidence_required": ["screenshot-final", "trace"],  // runner phải capture tối thiểu các mục này
  "metamorphic_relation": null                 // chỉ TC METAMORPHIC: quan hệ input↔output
}
```

## 3. Quy tắc validate (runner PHẢI check trước khi sinh spec)

1. Thiếu field ✱ → báo lỗi từng TC, KHÔNG lặng lẽ bỏ qua.
2. `oracle_source` trống hoặc = "current behaviour" → reject TC (tautology).
3. `platform` không nằm trong `_platform.json.platforms` → cảnh báo mismatch.
4. `coverage_ids` rỗng → TC mồ côi → reject.
5. `backend_policy` = mocked-* mà thiếu lý do → reject.
6. Đếm TC parse được phải = đếm TC trong file nguồn — lệch = dừng báo lỗi.
7. Khối tầng sâu (§5) khai thiếu field bắt buộc của chính nó → TC thành KHÔNG CHẠY có lý
   do, **không** lặng lẽ bỏ khối ấy đi. Một khối khai nửa vời là một phép đo tưởng đã chạy.

## 4. Markdown tương đương

File `uat_<feature>.md` (sinh bởi `generate_uat_markdown.py`) chứa các field trên dạng bảng per-TC; `uat.json` là nguồn chân lý — khi có cả hai, runner ưu tiên JSON.

## 5. Khối tầng sâu — chỉ khai khi `type` đòi hỏi

Sáu khối dưới đây là phần **`uat-test-only` v2** đọc để bật các cổng G13–G17. Không khai
thì cổng tương ứng báo **KHÔNG ÁP** — không bị phạt, nhưng cũng không đo được gì. Khai nửa
vời thì TC thành KHÔNG CHẠY (luật 7), vì một phép đo tưởng đã chạy còn nguy hơn một phép đo
biết là chưa chạy.

Quy tắc chọn: **`type` nào thì khối ấy**. Writer không rải khối bừa cho mọi TC.

| `type` | Khối bắt buộc kèm | Cổng bật |
|---|---|---|
| `SECURITY` · `PERMISSIONS` | `access` | G14 |
| `DATA` | `db_assert` · `audit_assert` · `idempotency` — ít nhất một | G15 |
| `STATE` | `transition` (+ `db_assert` để chứng minh trạng thái không đổi) | G15 |
| `E2E` có ghi / gửi lại được | `idempotency` | G15 |
| `PERFORMANCE` | `perf_budget` | G17 |
| mọi `type` | `coverage_ids` (đã ✱), `evidence_required` | G13, G12 |

```jsonc
// a) Ma trận quyền · IDOR — type SECURITY | PERMISSIONS
"access": {
  "url": "/api/v1/don/1",                  // ✱ tương đối theo base URL, hoặc URL đầy đủ
  "method": "GET",
  "allow": ["ke-toan", "giam-doc"],        // ✱ vai ĐƯỢC phép — mọi vai khác phải bị chặn
  "deny_status": [401, 403],               // mặc định [401, 403]
  "must_not_contain": ["so_tien", "cccd"]  // thân phản hồi không được lộ nội dung này
},

// b) Dữ liệu — type DATA. CHỈ ĐỌC: SELECT | WITH, một câu lệnh.
"db_assert": {
  "query": "SELECT trang_thai FROM don WHERE id = 1",   // ✱
  "expect": { "value": "REJECTED", "rows": 1 }          // ✱ rows|min_rows|max_rows|value|contains
},

// c) Audit — thao tác nhạy cảm phải để lại dấu vết
"audit_assert": {
  "entity": "don", "entity_id": "1", "action": "reject",   // ✱
  "fields": ["user_id", "created_at", "entity_id", "action", "old_value", "new_value"],
  "expect_rows": 1
},

// d) Idempotency — gửi lại có sinh bản ghi thừa không
"idempotency": {
  "url": "/api/v1/don", "method": "POST",                  // ✱ url
  "key_header": "Idempotency-Key", "concurrency": 5,
  "body": { },
  "count_query": "SELECT count(*) FROM don WHERE idem_key = ?",  // ✱
  "expect_rows": 1
},

// e) Máy trạng thái — type STATE. allowed:false = đường BẤT HỢP LỆ phải bị chặn.
"transition": { "from": "CANCELLED", "to": "RESULTED", "allowed": false },

// f) Hiệu năng — type PERFORMANCE
"perf_budget": {
  "url": "/api/v1/don", "method": "GET",                   // ✱ url
  "p95_ms": 800,                                           // ✱ ngân sách do NGƯỜI đặt
  "sample": 20, "warmup": 3, "max_error_rate": 0.0
}
```

**Ba điều writer tuyệt đối không được làm với khối tầng sâu:**

1. **Không bịa `p95_ms`.** Ngân sách hiệu năng là thoả thuận sản phẩm. Không biết thì để
   trống — TC thành KHÔNG CHẠY và báo cáo nói rõ là thiếu ngân sách. Bịa một ngưỡng rồi
   tuyên bố đạt là biến câu hỏi chưa có lời đáp thành một lời khẳng định.
2. **Không viết câu ghi vào `db_assert.query` / `count_query`.** `db_assert.py` từ chối mọi
   thứ không phải `SELECT`/`WITH`, và mồi dữ liệu bằng SQL vẫn bị cấm — chỉ phần ĐỌC được mở.
3. **Không khai `allow` rỗng.** Không biết vai nào được phép thì không dựng được ma trận;
   đoán bừa tệ hơn không đo.

## 6. Bí mật — không bao giờ nằm trong repo

| Thứ | Nơi đặt |
|---|---|
| tài khoản UAT | `UAT_USER_<ROLE>` / `UAT_PASS_<ROLE>`, hoặc tệp ngoài repo |
| token theo vai | `UAT_TOKEN_<ROLE>`, hoặc `UAT_TOKEN_FILE` trỏ JSON `{vai: token}` |
| DSN chỉ-đọc | `UAT_DB_DSN` (PostgreSQL 18 mặc định `127.0.0.1:5433`) |

Writer **chỉ khai tên vai** (`allow`, `determinism.auth_role`), không bao giờ khai giá trị
bí mật vào `uat.json`. Thiếu bí mật lúc chạy → cổng tương ứng **hạ trần**, và không bên nào
được tự chế tài khoản để "cho chạy được".

## 7. Bảng cổng chuẩn — ai tính cổng nào

Hai skill thực thi dùng **chung một dòng dõi cổng**, nhưng không cùng độ sâu. Bảng này là
từ điển chính thức; đừng đọc một báo cáo của bên này bằng nghĩa của bên kia.

| Cổng | `uat-test-only` (phán xét) | `uat-test-runner` (vòng sửa) |
|---|---|---|
| G0 Môi trường | app tới được, công cụ có → hỏng = **NO-RUN** | như vậy |
| G1 | **Mọi lớp có ca đều chạy được** (không lỗi biên dịch/sập) | **API smoke 100% pass** ← **KHÁC NGHĨA, đọc kỹ** |
| G2 Đường găng | P0/P1 100% PASS, 0 KHÔNG CHẠY | P0/S1-S2 100% pass, 0 flake |
| G3 Độ phủ | (PASS+FAIL)/tổng ca kế hoạch ≥ 95% | ≥95% TC đã EXECUTE |
| G4 Ngân sách lỗi | **CẦN NGƯỜI** — ngưỡng S2 là thoả thuận, không có trong hiện vật | CONDITIONAL GO |
| G5 Hồi quy | chỉ khi NGƯỜI đưa baseline | vs baseline xanh gần nhất |
| G6 Phi chức năng | **CẦN NGƯỜI** (phần đo được đã tách sang G16) | CONDITIONAL GO |
| G7 Ký duyệt | **CẦN NGƯỜI** — AI không bao giờ tự duyệt | thủ tục |
| G8 Monkey | **bắt buộc chạy**; 0 bất thường S1/S2 | — |
| G9 Rào không-sửa | git · hash-tree; vi phạm = **BÁO CÁO VÔ HIỆU** | — (runner được phép sửa) |
| G10 Oracle-binding | assert neo vào `expected` | — |
| G11 Chứng âm | 3 mệnh đề chắc chắn sai đều đỏ | — |
| G12 Bằng chứng | theo `evidence_required` | — |
| G13 Phủ yêu cầu | `coverage_ids` → Coverage Ledger | — |
| G14 Quyền · IDOR | `access` | — |
| G15 Dữ liệu·Audit·Idempotency·Trạng thái | `db_assert`·`audit_assert`·`idempotency`·`transition` | — |
| G16 A11y đo được | axe/WCAG 2.2, trần 29,5% | — |
| G17 Hiệu năng | `perf_budget.p95_ms` | — |

`uat-test-only` còn có **trục thứ hai**: cổng chặn nào **không đo được** thì hạ TRẦN kết
luận xuống `GO-CHỜ-KÝ-KÈM-KHUYẾT` (harness `FAIL`) thay vì im lặng đi qua. `uat-test-runner`
không có trục này — nó dùng 4 verdict GO / CONDITIONAL GO / NO-GO / NO-RUN.

## 8. Chọn skill nào để chạy

```
uat-test-writer  →  uat.json  →  ┬→  uat-test-only    (nghiệm thu · KHÔNG sửa · để ký)
                                 └→  uat-test-runner  (vòng dev · ĐƯỢC sửa · fix→retest)
```

| Câu hỏi | Dùng |
|---|---|
| "chạy UAT rồi báo lỗi", stage `uat` của harness, cần bằng chứng để **ký duyệt** | `uat-test-only` |
| "test rồi fix luôn", "retest sau khi sửa", vòng lặp của lập trình viên | `uat-test-runner` |

Chạy `uat-test-runner` rồi lấy kết quả ấy đi ký là **sai**: người tìm ra lỗi mà cũng là
người sửa thì không còn ai ở ngoài để nói nó vẫn sai. Muốn ký thì chạy lại bằng
`uat-test-only` trên một lượt mới, thư mục kết quả mới.
