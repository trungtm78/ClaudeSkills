---
name: uat-test-writer
description: Viết test case UAT world-class cho web VÀ mobile app (REST API + UI; Flutter / React Native / native Android-iOS / hybrid — TỰ NHẬN DIỆN platform từ codebase). Tư duy End-User thật (persona × journey × platform), neo chuẩn ISTQB (CTFL 4.0, CT-AcT, CTAL-TA v4.0), ISO/IEC/IEEE 29119-3:2021/29119-4:2021, ISO 25010:2023 + 25019:2023, FEW HICCUPPS oracle, BDD/Gherkin/Example Mapping, OWASP (web + MASVS/MASTG mobile), WCAG 2.2 AA. PHỔ QUÁT mọi domain, KHÔNG hardcode nghiệp vụ. Dùng khi user yêu cầu "viết test case", "viết UAT", "test plan", "kịch bản kiểm thử", "acceptance criteria", "UAT đầy đủ", "nâng cấp UAT", "research nghiệp vụ test", "data fixtures", "xuất Excel UAT", "test mobile app", hoặc mô tả feature cần kiểm thử chấp nhận. Prompt tiếng Anh vẫn output tiếng Việt.
---

# uat-test-writer — UAT Enterprise World-Class (v10, web + mobile)

> **THƯỚC ĐO GIÁ TRỊ (đọc trước):** chất lượng UAT = **bug thật bắt được + hành vi verify LIVE + fault-seeding survival + coverage minh bạch** — **KHÔNG** phải số TC / kích thước Excel. 40 TC bắt được mọi seeded-fault > 200 TC bắt 30%. Luận cứ định lượng bổ sung: flakiness compound theo size suite (4.000 test × 0.01% flake/test ⇒ ~33% xác suất pipeline đỏ oan) — suite UAT NHỎ chọn theo rủi ro là yêu cầu kỹ thuật, không phải sở thích. Mọi quy tắc dưới đây phục vụ giá trị này; cái gì chỉ tốn token mà không tăng bug-bắt-được → cắt.

> **ĐỊNH VỊ UAT ĐÚNG:** UAT ≠ system-test lần 2. UAT xác nhận **fitness-for-purpose theo góc nhìn End User**. Nếu UAT phát hiện nhiều critical functional bug ⇒ quy trình upstream hỏng (báo cáo như 1 finding). Metric sức khoẻ: **severity-mix của bug UAT** — kỳ vọng chủ yếu là usability / fit-for-purpose / hiểu-sai-requirement, gần 0 functional critical.

## ⚠️ Triết lý cốt lõi (world-class — neo chuẩn quốc tế)

**3 trụ (PHỔ QUÁT, đúng mọi domain):**
1. **Oracle là QUY TẮC NGUỒN CHÂN LÝ của domain, KHÔNG phải `status 200`** (FEW HICCUPPS). Mỗi TC khai báo `oracle_type` + `rule_ref` + **`oracle_source` (trích dẫn cụ thể: "Claims → SRS §4.2.1")**. Không oracle áp được → `oracle_type:"GAP"`, KHÔNG giả vờ pass. ⛔ CẤM oracle "as per current behaviour" — **expected sinh từ SPEC/requirement, KHÔNG từ implementation** (đọc code để tìm điểm neo/edge, nhưng chân lý phải độc lập với code — chống tautology oracle-từ-code). → `references/oracle-catalog.md`.
2. **Test như END USER thật = Persona × Journey × Platform, LIVE, KHÔNG mock cái mình sở hữu** (Testing Trophy "resemble real usage"). EU dùng app qua UI (browser/smartphone) — TC viết bằng ngôn ngữ nghiệp vụ (business outcome), không phải thao tác kỹ thuật API. UAT ở ĐỈNH pyramid: ít, giá trị cao, đi trọn vòng đời; API thật + DB seed thật; chỉ mock biên ngoài có lý do. Coverage ưu tiên **high-churn critical journeys** (đăng ký/đăng nhập/thanh toán/onboarding) trước, không breadth đồng đều.
3. **Generation ≠ Evaluation; bằng chứng trước khi kết luận** (verification-before-completion). Viết TC ≠ TC đúng; reject rate thật ~25% — KHÔNG hứa "100% dùng được". Người/agent sinh TC KHÔNG tự chấm — adversarial verify fresh-context với **severity filter** (chỉ flag gap ảnh hưởng correctness/requirements).
4. **MINH BẠCH chống lười — "Show your enumeration"**: coverage KHÔNG được tự nhận; phải PHƠI BÀY từng coverage item ra **Coverage Ledger** (Bước 6) rồi coverage% được TÍNH từ bảng. Không Ledger → không có quyền tuyên bố "đã phủ". Bỏ "sàn 100 TC" KHÔNG có nghĩa được test nông — thay bằng gate kiểm chứng được (enumerate-before-write, 0 drop ngầm, 0 TC mồ côi, completeness-critic đối kháng). → `references/coverage-ledger.md`.

5. **Bằng chứng phải ở ĐÚNG TẦNG mà mệnh đề nói về — "layer parity"**. Đây là trụ thứ năm vì
   bốn trụ trên đều xanh khi nó gãy. Một dòng ledger là một MỆNH ĐỀ; mệnh đề có tầng của nó.
   *"Mã khôi phục dùng được khi mất máy"* nói về **sản phẩm**, nên bằng chứng phải đi qua
   HTTP hoặc giao diện. Nếu bằng chứng là một ca gọi thẳng hàm, thì hoặc **đổi bằng chứng**,
   hoặc **thu hẹp mệnh đề** thành *"hàm X xử lý đúng"* — không được để mệnh đề rộng đứng
   trên bằng chứng hẹp.

   Ca thật, `Lumina_Approve` 03·08·2026: mười mã khôi phục sinh đúng, băm đúng, tiêu đúng,
   ghi danh lại thì huỷ đúng — và **không ai dùng được một mã nào**, vì lược đồ của endpoint
   duy nhất đọc được chúng khai `/^\d{6}$/`. Ca kiểm phủ nó gọi thẳng hàm, tức đúng tầng mà
   lược đồ không tồn tại. Ledger ghi *"dùng được khi mất máy"*, phủ 66/66, và cửa thoát hiểm
   cho người mất điện thoại là một tờ giấy không mở được gì.

   **Cách kiểm nhanh mệnh đề ↔ tầng:** đọc to dòng ledger rồi hỏi *"ai là chủ ngữ?"*. Chủ
   ngữ là **người dùng** → bằng chứng phải là E2E/HTTP. Chủ ngữ là **một hàm/bảng/ràng
   buộc** → ca đơn vị/tích hợp là đủ, và câu phải nói ra chủ ngữ ấy.

**Vận hành:**
- **Research-driven domain**: nghiệp vụ KHÔNG đoán/hardcode — **RESEARCH theo từng dự án** (Bước 0) rồi neo vào code. → `references/domain-research-discovery.md`.
- **COVERAGE-DRIVEN, KHÔNG con số cố định** (ISO/IEC/IEEE 29119-4 + ISTQB): số TC = **hệ quả** của phủ đủ coverage item (AC/EP/BVA/decision/state/pairwise) + độ sâu theo **rủi ro**; *nảy sinh từ dưới lên*. Tiêu chí "đủ" = **completion/exit criteria** (100% AC + 100% coverage kỹ thuật đã chọn + đặc tính 25010 áp dụng), KHÔNG phải "đạt N TC". → `references/coverage-calculator.md`.
- **Token discipline**: Load reference khi CẦN, viết TC theo batch, output compact.
- **Code-grounded + standards-grounded**: đọc codebase + neo điều luật/chuẩn, không tưởng tượng.
- **Multi-format output**: Excel (lifecycle) + Markdown (cho Claude Code fix bug).

## ⚠️ Quy ước ngôn ngữ

**100% tiếng Việt**, kể cả prompt tiếng Anh. Giữ tiếng Anh: API paths (`POST /api/login`), HTTP codes (`200`), tên tấn công (`SQL Injection`), mã loại TC (`GREEN`, `RED`), tech names (`JWT`, `JSON`).

## ⛔ NGHIÊM CẤM

1. **Bỏ sót coverage item** (AC/partition/boundary/decision-rule/state-transition/đặc tính 25010 áp dụng mà không có TC) — completion criteria FAIL. *(Số TND ít KHÔNG phải vi phạm nếu coverage đã 100%; số nhiều mà thiếu coverage VẪN vi phạm.)*
2. Skip loại TC nào không ghi N/A có lý do
3. Viết "tương tự cho các case khác", "..."
4. Hỏi "có muốn viết tiếp không"
5. **Chèn TC để "đạt con số/tỷ lệ"** (padding) — tautology/trùng lặp. Thiếu RED = thiếu invalid-partition/boundary → ĐẾM LẠI coverage, không chèn bừa.
6. **Lấy "≥100 TC" hay "RED ≥40%" làm MỆNH LỆNH** — đó chỉ là smell-test heuristic, KHÔNG phải tiêu chuẩn quốc tế. Tiêu chí thật = coverage + risk + exit criteria.
7. Bỏ qua Codebase Analysis (Bước 1) khi user có code
8. **TC có `expected` = chỉ HTTP code, không nêu hành vi nghiệp vụ** (oracle nghèo) — phải có `oracle_type` + `rule_ref` hoặc `GAP`
9. **Mock module nội bộ (DB/service mình sở hữu) trong UA/run** — chỉ mock biên ngoài (payment/email/3rd-party), có lý do
10. **Assert tautology** (`assert true`, assert lại đúng input vừa set) — pass nhưng bắt 0 bug
11. **Hardcode nghiệp vụ vào SKILL/reference** — domain knowledge phải đến từ Bước 0 Domain Research → `_domain-pack.md` của repo đích
12. **Có plan đang thực thi mà task/failure-mode của plan KHÔNG có TC phủ** (Plan↔UAT gap) mà không giải trình — xem Bước 0.5
13. **Feature có UI mà THIẾU ≥1 E2E browser chạy PASS cho journey chính** (Playwright/Cypress, real backend/DB) — E2E **cứng tuyệt đối**, không ngoại lệ.
14. **Kết luận UAT khi chưa EXECUTE LIVE** (chỉ viết TC trên giấy) — UAT phải chạy thật + có evidence; "viết xong = pass" là vi phạm.
15. **Feature có UI mà KHÔNG đánh giá UI/UX** (ISO 9241-11 + Nielsen 10 + WCAG 2.2) — xem `ui-ux-evaluation.md`.
16. **Tuyên bố "test tốt" mà KHÔNG có effectiveness** (bảng seeded-fault ↔ TC bắt được — xem Bước 7b) — coverage ≠ chất lượng.
17. **Bloat tốn token vô giá trị**: xuất Excel 100+ TC-trên-giấy khi chưa execute; sinh TC chỉ để nhiều; verbosity không tăng bug-bắt-được. Giá trị đo bằng **bug thật + fault-seeding + coverage minh bạch**, KHÔNG bằng số TC/size file.
18. **Oracle "as per current behaviour"** / expected chép từ hành vi code hiện tại — tautology; expected phải đến từ SPEC/rule/luật/chuẩn (nguồn độc lập code).
19. **Codebase có platform mobile mà TC bỏ qua danh mục mobile-only** (PERMISSIONS/DEEPLINK/PUSH/OFFLINE/LIFECYCLE/GESTURE/SCREENSIZE/BIOMETRIC/INSTALL/MOBILE-A11Y/MOBILE-SEC) không có N/A lý do — xem Bước 0.7.
20. **Boundary value do Faker/random sinh** — giá trị chứng minh requirement phải HAND-CODE; Faker chỉ cho filler data.
21. **Assertion chưa từng execute mà được chấp nhận** — TC chứng minh bug phải fail-then-pass; assertion sinh từ "trí nhớ" LLM không căn cứ = reject.

22. **Bằng chứng lấy từ TẦNG THẤP HƠN tầng mà mệnh đề nói về** — vi phạm nặng, và là loại
    trượt khó thấy nhất. Một dòng ledger viết *"mã khôi phục **dùng được** khi mất máy"* mà
    bằng chứng là một ca kiểm gọi thẳng hàm `verifySecondFactor` thì **không chứng minh gì
    về sản phẩm**: nó chứng minh một hàm. Luật: mệnh đề nói về **sản phẩm** thì bằng chứng
    phải đi qua **HTTP hoặc giao diện**; mệnh đề nói về một **hàm** thì mới được dùng ca đơn
    vị, và câu chữ của dòng ledger phải thu hẹp lại cho khớp.
23. **Hiện vật sản phẩm PHÁT RA mà không có TC đưa nó QUAY LẠI** — mã khôi phục, mã một lần,
    khoá thủ công của QR, link tải, mã mời, id mẫu bước chèn. Mỗi hiện vật cần đúng một ca:
    *lấy đúng chuỗi sản phẩm đưa cho người dùng, gửi ngược vào cái cửa nó mở*. Đây là loại
    lỗi mà mọi tầng đều xanh: sinh đúng, lưu đúng, đổi đúng — và cái cửa từ chối hình dạng
    ấy ở lớp validate, trước khi chạm vào bất cứ thứ gì.
24. **Kết luận từ một lượt chạy CÓ CACHE** — `turbo`/`nx`/`jest --ci` băm tệp nguồn và
    KHÔNG nhìn thấy cơ sở dữ liệu. Một migration ở gói khác đổi hành vi mà gói này không
    đổi dòng nào → cache phát lại một lượt xanh cũ. Lượt chạy dùng để kết luận UAT phải
    **tắt cache** (`TURBO_FORCE=1`), và báo cáo phải ghi ra `0 cached`.

## 📤 Output — DEFAULT gọn (chống token-guzzler)

**Default = Markdown gọn + `_coverage-ledger.md` + bug list + kết quả EXECUTE.** Excel `.xlsx` **chỉ khi user yêu cầu** ("xuất Excel", "lifecycle tracking") — Excel 100+ TC-trên-giấy chưa execute là token-guzzler điển hình.

| User nói | Output |
|----------|------|
| "Viết/UAT cho..." (default) | Markdown + Ledger + bug list + evidence execute |
| "Xuất Excel..." | thêm `.xlsx` 6 sheets |

Lệnh xuất (portable — `OUT` = thư mục thật của repo, vd `docs/uat/<feature>/`):
```bash
export PYTHONUTF8=1                       # Windows cp932 lỗi emoji nếu thiếu
python scripts/generate_uat_markdown.py input.json "$OUT/uat_<feature>.md"
python scripts/generate_uat_excel.py    input.json "$OUT/uat_<feature>.xlsx"   # chỉ khi cần Excel
# recalc.py (/mnt/...) chỉ có trên môi trường claude.ai — bỏ qua trên máy local
```

## 🚀 Lean Mode — Giảm token

Trigger: user nói "lean", "ngắn gọn", "tiết kiệm token", hoặc feature đơn giản.

Khác biệt FULL vs LEAN:

| Yếu tố | FULL mode | LEAN mode |
|--------|-----------|------------|
| Codebase Analysis | Đọc 8 artifacts đầy đủ | Đọc 3 artifacts chính (routes, DTOs, services) |
| Deep Thinking | Fill đủ 15 dimensions, mỗi ≥3 fact | Quick scan 8 dimensions ưu tiên cao |
| Per-TC fields | Steps + UI + API + Side effects (3 expected) | Steps + 1 combined Expected (gộp) |
| Pattern library | Áp dụng manual có suy luận | Auto-multiply theo template |
| Self-audit | Full (mọi gate: completion + anti-laziness + effectiveness + E2E/UX) | Quick (coverage + mutation + E2E core) |
| Token cost | ~100% | ~40-50% |
| TC count | Same (coverage đủ) | Same (coverage đủ) |

Lean KHÔNG giảm coverage — chỉ giảm verbosity. **Tuyệt đối không hạ coverage/completion criteria** (vẫn 100% AC + coverage kỹ thuật + đặc tính 25010 áp dụng).

## 14 loại TC (áp dụng theo rủi ro — không ép đủ)

| Mã | Mục đích |
|----|----------|
| **GREEN** | Happy path, input hợp lệ |
| **RED** | Negative — input sai, system phản ứng có kiểm soát |
| **EDGE** | Trường hợp hợp lệ nhưng ít gặp |
| **BOUNDARY** | min-1, min, max, max+1 |
| **EP** | Equivalence Partitioning |
| **STATE** | State Transition |
| **DECISION** | Decision Table |
| **SECURITY** | OWASP Top 10, AuthN/AuthZ, IDOR |
| **DATA** | Validation, i18n, special char |
| **PERFORMANCE** | Response time, concurrent |
| **A11Y** | WCAG 2.2 AA |
| **COMPAT** | Browser/device/OS |
| **UX** | UI/UX — Nielsen 10 heuristics + ISO 9241-11 (effectiveness/efficiency/satisfaction) + visual/interaction states |
| **E2E** | Journey end-to-end như user thật (Testing Trophy) — luồng chính, real backend/DB |

Loại phụ tùy feature: INTEGRATION, REGRESSION, RECOVERY, AUDIT, **EXPLORATORY** (charter-scoped, evidence-based — hợp lệ theo FDA CSA 2025), **METAMORPHIC** (feature không có expected value chính xác: search/ranking/pricing/report/AI — assert QUAN HỆ giữa outputs khi biến đổi input).

**12 loại MOBILE-ONLY (BẮT BUỘC xét khi platform có mobile — Bước 0.7; N/A phải có lý do):**

| Mã | Kiểm gì (oracle mẫu) |
|----|------|
| **PERMISSIONS** | grant / deny / deny-forever / revoke-khi-background; app KHÔNG BAO GIỜ crash khi deny, có rationale + deep link Settings |
| **DEEPLINK** | cold/warm start, logged-out → đúng màn hình sau login, malformed link không crash, app-not-installed → web fallback |
| **PUSH** | foreground banner / background tray / killed vẫn nhận; tap → đúng route + payload; denied-permission path |
| **OFFLINE** | offline banner, đọc cache được, write được queue không mất, tự resync khi reconnect, không spinner vô hạn |
| **LIFECYCLE** | background→foreground giữ state; killed→cold start khôi phục sạch; không mất token; không double-submit khi resume |
| **GESTURE** | swipe/long-press/pinch/pull-to-refresh/scroll-to-element; **hardware back (Android) không thoát bất ngờ, không mất data đã nhập** |
| **SCREENSIZE** | small phone ≤360dp / large / tablet / font-scale max / RTL — không clip text, CTA không nằm ngoài tầm với |
| **BIOMETRIC** | pass/fail/lockout sau N lần, fallback passcode, chưa enroll |
| **INTERRUPT** | cuộc gọi đến, rotate giữa form, keyboard che CTA |
| **INSTALL** | fresh install, upgrade giữ data (migrate DB), onboarding chỉ 1 lần |
| **MOBILE-A11Y** | TalkBack/VoiceOver tới mọi nội dung, touch target ≥48dp/44pt, contentDescription đủ |
| **MOBILE-SEC** | OWASP MASVS/MASTG: secrets không lộ logcat, screenshot-block màn nhạy cảm, cert pinning, deep-link không bypass auth |

> **Áp dụng theo rủi ro, KHÔNG ép đủ mọi loại:** loại không áp dụng → ghi **N/A có lý do** (vd PERFORMANCE cho read-only nhẹ). Ép cho đủ mọi loại = padding.

## 📊 Test Quantity — COVERAGE 100% **VÀ** SÀN THEO RỦI RO (cả hai BẮT BUỘC)

> Số TC phải thoả **ĐỒNG THỜI (A) coverage 100%** *và* **(B) ≥ sàn theo tier rủi ro**. Lấy ràng buộc CHẶT hơn. (A) là tiêu chí CHUẨN; (B) là **lưới chống-lười** để (A) không bị tuyên bố nông.

**(A) COVERAGE CRITERIA = 100%** (ISO/IEC/IEEE 29119-4 + ISTQB) — đếm bottom-up qua **Coverage Ledger** (Bước 6):
1. 100% AC/requirement (RTM 2 chiều) — mỗi AC ≥1 xác nhận + ≥1 negative.
2. 100% coverage item kỹ thuật: EP (mọi partition valid+invalid) · BVA (3-value khi rủi ro cao) · Decision Table (mọi rule khả thi) · State Transition (0-switch + sneak path; N-switch khi rủi ro cao) · Pairwise.
3. Mỗi đặc tính **ISO 25010 áp dụng** ≥1 nhóm TC, hoặc N/A có lý do.
4. **E2E + UI/UX là coverage area BẮT BUỘC** cho feature có UI (mục dưới).
5. Risk-based depth: rủi ro cao → kỹ thuật mạnh hơn (3-value BVA, MC/DC, combinatorial cao).

**(B) SÀN TỐI THIỂU `TC_min` = ENSEMBLE → lấy MAX 4 phương pháp** (tính nhiều cách, phương pháp khắt khe nhất quyết định → đảm bảo chất lượng). KHÔNG dùng LOC:

| Mã | Phương pháp | Cách tính | Neo chuẩn |
|---|---|---|---|
| **M1** | Spec coverage items (black-box) | Σ(AC×2) + EP partitions + BVA boundaries + decision rules + state transitions + pairwise | ISO/IEC/IEEE 29119-4 |
| **M2** | Cyclomatic V(G) (white-box) | Σ V(G) các hàm logic dưới test (sàn branch/basis-path). Tool: `lizard`/`eslintcc`/`radon` | McCabe basis-path |
| **M3** | Functional size | `ceil(FP^1.2)` nếu ước được Function Points | Capers Jones / ISBSG |
| **M4** | Risk-tier backstop (policy) | CRITICAL 120 · HIGH 80 · STANDARD 50 · LOW 25 (chỉ bind nếu là MAX) | forcing-function chống lười |

→ **`TC_min = MAX(M1, M2, M3, M4)`**. Ghi M1..M4 + MAX vào Ledger (minh bạch). Lấy MAX = phủ trường-hợp-xấu-nhất của mọi cách đo.

**Hoà giải (A)+(B) — KHÔNG mâu thuẫn, KHÔNG padding:**
- Nếu coverage thật (A) cho ra < `TC_min` → đó là tín hiệu **đã under-enumerate** (thường thiếu path so với V(G) M2) → quay lại Ledger đào sâu (boundary 3-value, sneak path, decision combo, pairwise, security/UX/E2E) cho tới khi coverage THẬT đạt → số TC tự lên tới/vượt sàn. **`TC_min` là báo động "đào chưa đủ"; coverage là cách lấp HỢP LỆ (cấm chèn TC tautology cho đủ số).**
- (A) ≥ `TC_min` → đạt.

**Completion/exit criteria (29119-2)** = (A) coverage 100% + tổng ≥ `TC_min` + **effectiveness đạt ngưỡng (mutation, mục dưới)** + residual risk chấp nhận + 0 defect High/Critical mở.

**Smell-test tỷ lệ (heuristic, KHÔNG mệnh lệnh):** GREEN ≤20% / RED ≥40%… chỉ để *phát hiện thiếu sót* — lệch thì ĐẾM LẠI coverage, KHÔNG chèn bừa.

→ Chi tiết + ví dụ: `references/coverage-calculator.md`.

## 🎬 Test như END USER THẬT — E2E **cứng tuyệt đối** + đánh giá UI/UX

**Triết lý (Testing Trophy — K.C. Dodds):** *"Test càng giống cách user dùng → càng tin cậy."* Stop over-mocking.

**Feature có UI ⇒ BẮT BUỘC:**
1. **E2E cho JOURNEY CHÍNH trên platform tương ứng** (web = Playwright browser; mobile = Maestro trên emulator/device; real backend + DB, KHÔNG mock nội bộ) — đi trọn vòng persona: đăng nhập → thao tác → kết quả → side-effect, có **evidence** (trace/screenshot/recording). Mỗi journey chính ≥1 E2E chạy **PASS** trên MỖI platform áp dụng (platform bị chặn — vd iOS trên Windows — ghi `NOT_EXECUTED (blocked)` + remediation, KHÔNG được tính là pass). Coverage area `COV-E2E-*` trong Ledger.
2. **KHÔNG nhồi E2E cho mọi edge** (đúng Trophy — E2E chậm/giòn): edge/negative đẩy xuống integration/component/API; E2E chỉ phủ **luồng quan trọng** (như sign-up/checkout/payment). 
3. **Persona × Journey matrix** (Screenplay): liệt kê vai trò thật × luồng end-to-end → mỗi ô = 1 E2E hoặc N/A có lý do.
4. **Đánh giá UI/UX** (không chỉ chức năng): **ISO 9241-11** (effectiveness·efficiency·satisfaction) + **Nielsen 10 heuristics** + visual/interaction states (loading/empty/error/disabled/responsive/focus/contrast) + **WCAG 2.2 A/AA**. Coverage area `COV-UX-*`. → `references/ui-ux-evaluation.md`.

**Service API thuần (không UI)** → E2E/UX = N/A có lý do; thay bằng integration test end-to-end qua API thật.

## 📋 Quy trình bắt buộc (Bước 0, 0.5, **0.7**, 1→7, **7b EXECUTE+E2E+UX+Fault-Seeding**, 8→10)

Không skip. Không reorder. Không gộp.

| Bước | Tên | Output | Reference |
|------|-----|--------|-----------|
| **0** | **★ Domain Research & Discovery** | `docs/uat/_domain-pack.md` (Authority Brief + Oracle table + Personas + State-map + Journeys + Mock-allowlist) | ⭐ `domain-research-discovery.md` |
| **0.5** | **★ Plan Grounding (CÓ ĐIỀU KIỆN)** | `docs/uat/_plan-scope.md` (nếu có plan đang thực thi) | ⭐ `plan-analysis.md` |
| **0.7** | **★ Platform & EU Persona Detection** | `docs/uat/_platform.json` (multi-label + appId + buildCmds + blockers) + Persona×Journey×Platform matrix trong `_domain-pack.md` | ⭐ `platform-detection.md` |
| 1 | Codebase Analysis | `/tmp/codebase_map.md` | `codebase-analysis-framework.md` |
| 2 | Deep Thinking | `/tmp/thinking_notes.md` | `deep-thinking-checklist.md` |
| 3 | Capture & Recap | Bảng recap feature | — |
| 4 | Risk Assessment | Risk matrix (Likelihood×Impact theo domain; pre-populate từ plan Failure modes + P0/P1 nếu có) + scope | — |
| 5 | Thiết kế shift-left: Example Mapping → DMN/BPMN → EP/BVA/Decision → **Gherkin** | Rules/examples/questions + partition + Gherkin scenarios | `test-design-techniques.md` |
| 6 | **Coverage Ledger + RTM (Sổ phủ — CHỐNG LƯỜI)** | `_coverage-ledger.md`: liệt kê MỌI coverage item (AC/EP/BVA/decision/state/pairwise/25010) → cov_id ↔ TC ↔ rule_ref, coverage% TÍNH từ bảng, item chưa phủ = GAP có lý do, 0 TC mồ côi. + Completeness-critic đối kháng. | ⭐ `coverage-ledger.md` + `oracle-catalog.md` |
| 7 | Test Cases Detail (mỗi TC có `oracle_type`+`rule_ref`+`oracle_source`, theo **handoff schema**) | **Batch sinh + save** | `red-pattern-library.md` + `oracle-catalog.md` + ⭐ `handoff-schema.md` |
| **7b** | **★ EXECUTE LIVE + E2E + UI/UX + Fault-Seeding** | Chạy thật (API live + **E2E journey chính** PASS trên platform tương ứng) + đánh giá UI/UX + **bảng seeded-fault↔TC** + adversarial-verify | ⭐ `ui-ux-evaluation.md` + `coverage-ledger.md` |
| 8 | **Data Maturity Matrix** | `data_fixtures[]` JSON | ⭐ `data-maturity-matrix.md` |
| 9 | Test Data Bundle | Accounts, BV, payloads | `security-payloads.md` |
| 10 | Self-Audit Gate + Entry/Exit criteria + Sign-off package | Pass/Fail checklist + GO/NO-GO đề xuất | — |

### Bước 0.7: Platform & EU Persona Detection (MỚI — chạy trước khi thiết kế TC)
- **Detect multi-label** từ codebase (KHÔNG BAO GIỜ đơn nhãn; monorepo → recurse từng package rồi union): FLUTTER (pubspec.yaml) / RN±EXPO (react-native, app.json/eas.json) / ANDROID (settings.gradle+AndroidManifest) / IOS (xcodeproj) / HYBRID_WEBVIEW (capacitor.config, config.xml — đồng thời gắn WEB) / WEB (next/vite/react/vue/angular) / API (openapi, backend markers). Ghi **evidence file marker** cho mỗi label.
- Xuất `_platform.json` (JSON contract chung với runner): `platforms`, `packages[]`, `appId` (android applicationId / iOS PRODUCT_BUNDLE_IDENTIFIER), `buildCmds`, `apiBaseUrl` (+ biến thể emulator `10.0.2.2`), `host` (OS, iosPossible), `blockers[]` (vd iOS trên Windows → NOT_EXECUTED + remediation).
- **EU Persona × Journey × Platform matrix** vào `_domain-pack.md` — mỗi ô = journey của persona đó trên platform đó (hoặc N/A lý do). TC nào cũng trỏ về 1 ô.
- **Hybrid (Capacitor/Ionic)**: sinh 2 bộ TC LIÊN KẾT — web-layer set (Playwright chạy) + native-shell set (Maestro chạy: plugins/permissions/deep-link/lifecycle) — cross-reference, không double-count coverage.
- **Testability defect = output hạng nhất**: nếu source thiếu stable test ID (`testID` RN / `testTag` Compose / `Semantics(identifier:)` Flutter / `accessibilityIdentifier` iOS / `data-testid` web) → file defect đề xuất bổ sung (selector maintenance = chi phí #1 dài hạn của automation).
- **Device matrix tối thiểu** khi có mobile: {small phone, large phone, tablet} × {OS mới nhất, OS min-supported} × {font scale mặc định, max} — kèm rationale chọn.
- → Chi tiết ma trận detect + schema: `references/platform-detection.md`.

### Bước 0: Domain Research & Discovery (CHẠY TRƯỚC khi viết bất kỳ TC nào)
- **Pha A — RESEARCH** domain của dự án (WebSearch/`deep-research`/tải refs): nhận diện domain → research nguồn chân lý (luật/chuẩn ngành/business rule kinh điển) → trích rule kiểm chứng được → **Authority Brief có citation**.
- **Pha B — GROUND** vào repo: neo mỗi rule vào code (D1 oracle, D2 personas, D3 state-map, D4 journeys, D5 builders, D6 mock-allowlist). Mỗi oracle có **2 neo: nguồn research + vị trí code**.
- Output `_domain-pack.md` lưu trong repo đích; mọi TC ở Bước 7 trỏ vào 1 `rule_id` của pack.
- Domain regulated (pháp lý/y tế/thanh toán/dữ liệu cá nhân) → research SÂU; CRUD nội bộ → research NHẸ. Đã có pack mới → tái dùng.
- → Chi tiết: `references/domain-research-discovery.md`.

### Bước 0.5: Plan Grounding — phân tích sâu PLAN đang thực thi (CÓ ĐIỀU KIỆN)
Nếu dự án **đang triển khai một plan** → UAT phải **cột vào plan đó**. 4 pha:
- **P1 Detect:** env `CLAUDE_PLAN_FILE` → fallback `GSTACK_PLAN_MODE=active` + quét `~/.claude/plans/*.md` mới nhất → + artifacts `/plan-eng-review` (`~/.gstack/projects/<slug>/tasks-eng-review-*.jsonl`, `*eng-review-test-plan-*.md`) → + `gh pr view --json body`. **Không có plan → ghi "no active plan, skip", tiếp Bước 1.**
- **P2 Deep-read (SÂU):** ý định (Context), root cause + **decisions** mỗi PR, Implementation Tasks (`T<n> P0–P3` + Files + Verify), **Failure modes**, **NOT in scope**, GSTACK REVIEW REPORT (**unresolved** = rủi ro mở), test-plan hints.
- **P3 Extract:** mỗi task/FM/decision → `rule_ref` `PLAN-T*`/`PLAN-FM*`/`PLAN-AC*` (oracle_type Claim/Purpose) mà UAT BẮT BUỘC phủ; gộp `Files:` → changed-files.
- **P4 Cross-check & output:** đối chiếu **plan-claim vs CODE THẬT** (plan ghi "đã fix" ≠ chắc đã fix → grep/Read xác nhận; lệch = drift finding). Xuất `docs/uat/_plan-scope.md` + **Plan↔UAT coverage matrix** (T/FM không có TC = gap).
- Tích hợp: Bước 4 (risk pre-populate từ FM + P0/P1) · Bước 6 (RTM gộp plan-derived) · Bước 7 (verify từng claim LIVE).
- → Chi tiết: `references/plan-analysis.md`.

### Bước 5: Thiết kế shift-left — Example Mapping → DMN/BPMN → Gherkin

1. **Example Mapping (Three Amigos)**: story → rules (xanh) → examples (lục) → **questions (đỏ)**. **Đếm và báo cáo số thẻ đỏ** — mỗi câu hỏi = 1 requirement-defect được ngăn TRƯỚC khi code = leading ROI metric của UAT.
2. **Mô hình hoá cơ học**: business rule → **decision table (DMN)** (mọi rule combination = coverage item đếm được); business process → **BPMN path** (happy + exception + compensation path). "Đã nghĩ đủ chưa?" trở thành câu hỏi ĐẾM ĐƯỢC.
3. **Derive TC cơ học** từ bảng/paths + EP/BVA/state-transition/pairwise (như cũ — `test-design-techniques.md`).
4. **Format Gherkin declarative** cho TC nghiệp vụ (bên cạnh bảng chi tiết):
   - 1 rule / 1 scenario (rule phức tạp → tách); **declarative** — mô tả nghiệp vụ, KHÔNG UI mechanics ("Given đơn hàng đã thanh toán" chứ không "click nút X");
   - `Scenario Outline` + Examples cho bộ EP/BVA;
   - tag theo risk-tier + journey (`@P0 @journey-checkout @android`).
5. **Metamorphic** cho feature không có expected value chính xác: khai báo quan hệ (vd "thêm filter ⇒ kết quả ⊆ kết quả cũ", "đổi đơn vị tiền ⇒ tổng quy đổi tương đương") làm oracle.

### Bước 8: Data Maturity Matrix — sinh data fixtures độc lập

**Mục đích**: Tạo data test theo độ trưởng thành (state × lifecycle × shape), runner tự seed trước test, KHÔNG dùng data tĩnh.

**3 chiều của fixture**:
1. **STATE**: User {New/Pending/Active/Trial/Suspended/Locked/Deleted/Banned}
2. **LIFECYCLE**: D0/D7/D30/D90/D365 (relative time)
3. **SHAPE**: empty/single/sparse/normal/full/large/with_holes/with_orphans

**Fixture ID format**: `<entity>.<state>.<lifecycle>.<shape>`
- Vd: `user.pending.D0`, `order.draft.D0.with_holes`, `subscription.trial.D14`

**Mỗi fixture có 3 recipe**:
- `setup_recipe`: API endpoint / SQL / factory để runner tạo data
- `cleanup_recipe`: cleanup sau test
- `outputs`: field mapping ($.id → user_id) để TC reference

**Template variables**:
- `{{now}}`, `{{today}}`, `{{random}}`, `{{uuid}}`
- `{{D+N}}`, `{{D-N}}` (offset days)
- `{{user_id}}`, `{{env.VARNAME}}`

**Mỗi TC link fixture qua field `data_required`**:
```json
{
  "tc_id": "TC-005",
  "title": "User pending không login được",
  "platform": "web",
  "target": "simulator-ok",
  "persona": "user-moi-chua-verify",
  "journey_ref": "J-AUTH-01",
  "oracle_type": "Purpose",
  "rule_ref": "<rule_id trong _domain-pack, vd AUTH-PENDING-BLOCK>",
  "oracle_source": "Claims → SRS §3.1 / rule AUTH-PENDING-BLOCK trong _domain-pack",
  "backend_policy": "live",
  "data_required": ["user.pending.D0"],
  "steps": "1. Login với credentials từ fixture\n2. Submit",
  "expected": "Bị chặn + thông báo theo rule; KHÔNG chỉ 'status 401'"
}
```
> Đầy đủ field bắt buộc/tuỳ chọn: `references/handoff-schema.md` — **nguồn sự thật duy nhất**
> của hợp đồng, có **ba** bên: writer sinh · `uat-test-only` thực thi-và-phán-xét (không sửa
> gì) · `uat-test-runner` vòng sửa→chạy lại. Sửa schema xong phải chạy
> `python scripts/sync_contract.py`; `--check` chạy trong bộ test của `uat-test-only` nên trôi
> là đỏ ngay.

### Khối tầng sâu — BẮT BUỘC theo `type` (handoff-schema §5)

Sáu khối dưới đây là thứ bật các cổng sâu của `uat-test-only`. **Không khai = cổng KHÔNG ÁP**
— tức là một vùng rủi ro không ai đo. Writer khai theo đúng `type`, không rải bừa:

| `type` | Khối phải kèm | Không khai thì mất |
|---|---|---|
| `SECURITY` · `PERMISSIONS` | `access` (url · `allow` · deny_status · must_not_contain) | G14 — không ai thử vai không được phép và vai vô danh |
| `DATA` | `db_assert` và/hoặc `audit_assert` | G15 — màn hình xanh không chứng minh dữ liệu đã ghi đúng |
| `STATE` | `transition` (+ `db_assert` để chứng minh trạng thái không đổi) | G15 — chỉ kiểm đường hợp lệ, bỏ sót đúng nửa nguy hiểm |
| `E2E` có ghi / gửi lại được | `idempotency` (gửi ĐỒNG THỜI, `count_query`) | G15 — double-submit sinh bản ghi thừa mà không ai thấy |
| `PERFORMANCE` | `perf_budget` (`p95_ms` do NGƯỜI đặt) | G17 |
| mọi TC | `evidence_required` | G12 — PASS không bằng chứng thì không truy ngược được |

**Ba điều cấm khi khai khối:**
1. **Không bịa `p95_ms`.** Ngân sách là thoả thuận sản phẩm. Không biết thì để trống — TC
   thành KHÔNG CHẠY và báo cáo nói rõ thiếu ngân sách. Bịa ngưỡng rồi tuyên bố đạt là biến
   một câu hỏi chưa có lời đáp thành một lời khẳng định.
2. **Không viết câu ghi vào `db_assert.query`.** Chỉ `SELECT`/`WITH`; mồi dữ liệu bằng SQL
   vẫn cấm. Runner sẽ từ chối chạy và TC thành KHÔNG CHẠY.
3. **Không khai `allow` rỗng**, và không bao giờ khai giá trị bí mật (token, mật khẩu, DSN)
   vào `uat.json` — chỉ khai **tên vai**; bí mật nằm ở biến môi trường ngoài repo.
> `oracle_type` ∈ {Statute, Claim, Purpose, Product, History, World, User, Image, Comparable, Familiarity, Explainability, GAP} — xem `oracle-catalog.md`.

**Quy tắc bắt buộc**:
- ≥1 fixture cho mỗi state của entity (User: ít nhất 6-8 fixtures)
- ≥1 fixture cho mỗi lifecycle critical (trial_end, expiry, dormancy)
- ≥1 fixture cho mỗi shape extreme (empty + full/large) với list entities
- Mọi fixture phải có cleanup_recipe

→ Chi tiết: `references/data-maturity-matrix.md`.

### Batch Generation (Bước 7) — Token saver

**KHÔNG sinh hết TC trong 1 response**. Chia thành batches:

```
Batch 1: Sinh 30 TC P0 GREEN+RED chính → ghi vào /tmp/tc_batch_1.json
Batch 2: Sinh 30 TC SECURITY + BOUNDARY → ghi vào /tmp/tc_batch_2.json
Batch 3: Sinh 30 TC DATA + STATE + DECISION → /tmp/tc_batch_3.json
Batch 4: Sinh 20 TC A11Y + COMPAT + PERFORMANCE → /tmp/tc_batch_4.json
...
Final: merge tất cả batch → input.json → generate Excel + MD
```

Mỗi batch:
1. Sinh JSON với 20-30 TC
2. Ghi vào `/tmp/tc_batch_N.json`
3. Báo "Batch N: [X] TC. Total so far: [Y]/[required]"
4. Continue batch tiếp theo (KHÔNG hỏi user "tiếp tục?")

Khi coverage đã đủ (đạt completion criteria), merge:
```python
# scripts/merge_batches.py — đã có sẵn
python scripts/merge_batches.py /tmp/tc_batch_*.json > input.json
```

→ Lợi ích: giữ context của Claude nhỏ + có thể recover nếu interrupt.

## 🎯 Priority & Severity (2 trục ĐỘC LẬP — gate theo severity, xếp lịch theo priority)

**Severity chuẩn 4 mức (kỹ thuật — mức độ ảnh hưởng):**

| Mức | Định nghĩa |
|-----|-----------|
| **S1 Critical** | Chức năng không dùng được, KHÔNG có cách thay thế chấp nhận được |
| **S2 Major** | Không dùng được/crash/hỏng data NHƯNG có workaround chấp nhận được |
| **S3 Moderate** | Chạy nhưng kết quả sai / thiếu / không nhất quán |
| **S4 Minor** | Cosmetic, vòng qua dễ dàng |

**Priority (nghiệp vụ — thứ tự xử lý):**

| Pri | Tiêu chí | Tỷ lệ |
|-----|----------|-------|
| **P0** | Blocker: core GREEN, mọi SECURITY, money/data integrity | ≥30%, ≤50% |
| **P1** | Bug khó workaround, RED chính, A11y level A | ≥30%, ≤45% |
| **P2** | Có workaround | ≤30% |
| **P3** | Nice-to-have | ≤10% |

Severity ⊥ Priority: crash ở feature hiếm dùng = S1/P2; typo trang chủ = S4/P0 — cả hai hợp lệ. Severity Critical + High ≥ 60% tổng TC.

## 🚦 Entry / Exit Criteria + Sign-off (thoả thuận TRƯỚC khi UAT bắt đầu — ISO 29119-2)

**Entry (8 vùng — thiếu vùng nào ghi rõ):** upstream test xong có evidence · 0 critical/high đang mở trong scope · môi trường UAT production-like riêng (formal sign-off cần **named env ổn định**, không dùng preview ephemeral) · test data sẵn (synthetic mặc định) · AC baselined · TC đã review · tester/persona sẵn sàng · stakeholder xác nhận.

**Exit (số cụ thể — điều chỉnh theo dự án nhưng phải CÓ SỐ):** 95-100% TC kế hoạch đã execute (100% critical path) · 100% S1 resolved, ≥95% S2 resolved · 0 critical mở, ≤3 high có workaround văn bản · 100% AC trace tới TC pass · sign-off văn bản của người có thẩm quyền.

**Waiver (khi không đạt 1 tiêu chí mà vẫn muốn GO):** BẮT BUỘC đủ 3 phần — (1) named approver ký, (2) risk acceptance tường minh, (3) remediation date cam kết. Không waiver = không GO. **"Looks good" không phải sign-off; AI KHÔNG BAO GIỜ tự approve** — skill chỉ đề xuất verdict + evidence package.

**Effectiveness scorecard (báo cáo cùng kết quả):**
- Số "thẻ đỏ" Example Mapping (requirement-defect ngăn được — leading indicator)
- Severity-mix bug UAT (kỳ vọng: chủ yếu usability/fit-for-purpose; nhiều S1 functional = upstream hỏng)
- **DDP/DRE có cửa sổ đo khai báo** (30/60/90 ngày) — ghi `provisional` tới khi cửa sổ đóng; target DRE >95%, leakage <5%
- First-pass sign-off rate; escaped defects trong cửa sổ
- Bảng seeded-fault↔TC (effectiveness thay mutation-score)

## 🚪 Self-Audit Gate (Bước 10)

### Cổng 0 — TỰ KIỂM HÀNG bằng máy, chạy TRƯỚC mọi thứ khác

```bash
python "$HOME/.claude/skills/uat-test-writer/scripts/validate_uat_json.py" docs/uat/<feature>/uat.json
```

Thoát khác 0 → **sửa rồi sinh lại, đừng bàn giao**. Script áp đủ luật handoff-schema §3
(1-7) · §5 (khối tầng sâu theo `type`) · §6 (bí mật không được nằm trong `uat.json` vì tệp
này được commit).

### Cổng 1 — `TC_min` và độ phủ do MÁY tính

```bash
python "$SK/scripts/coverage_calc.py" --ledger docs/uat/<feature>/_coverage-ledger.md        --uat docs/uat/<feature>/uat.json --write
```

`TC_min = MAX(M1,M2,M3,M4)` **tính từ Ledger**, rồi **ghi đè** vào `uat.json`. Trước đây
con số này do LLM tự ghi và script chỉ hiển thị lại — một cái sàn do chính người bị đo đặt
thì không phải là sàn. Thiếu `M2=` / `FP=` / `risk=` ở đầu Ledger → báo **chưa phải
ENSEMBLE**; không đọc được Ledger → `TC_min: KHÔNG ĐO ĐƯỢC`, **không lấy số nào thay thế**.

### Cổng 2 — chạy cả bảng Self-Audit bằng máy

```bash
python "$SK/scripts/self_audit.py" --uat docs/uat/<feature>/uat.json        --ledger docs/uat/<feature>/_coverage-ledger.md
```

Ba mục **CẦN NGƯỜI** (fault-seeding · adversarial-verify · đánh giá UX) giữ nguyên nhãn và
**không ai được tự tích thay** — chúng hạ trần kết luận xuống `SẴN SÀNG-KÈM-KHUYẾT`. Đây là
trạng thái bình thường và trung thực của một bộ UAT vừa sinh xong.

Vì sao ba cổng này tồn tại: trước đây writer **không kiểm gì** đầu ra của chính nó — phép kiểm
đầu tiên nằm ở `uat-test-only`. Người sản xuất không kiểm hàng của mình thì lỗi chỉ lộ ra
sau khi đã bàn giao, và lúc ấy sửa tốn gấp nhiều lần.


Bắt buộc fill bảng này, fail bất kỳ checkpoint → quay lại viết bổ sung:

```
ANTI-LAZINESS / MINH BẠCH / HIỆU LỰC (Coverage+Effectiveness Ledger; → coverage-ledger.md):
> 9 mục của nhóm này (Ledger · TC_min · coverage% · GAP · TC mồ côi · khối tầng sâu · bí
> mật · hợp đồng) **đã chuyển thành máy tính** — chạy Cổng 0/1/2 ở trên, đừng tự tích.
> Ba mục còn lại dưới đây máy KHÔNG tính được, và `self_audit.py` đã **hạ trần** vì chúng.

✅/❌ **EFFECTIVENESS = FAULT-SEEDING** (mutation classic trên E2E KHÔNG khả thi — consensus): bảng **seeded-fault ↔ TC** ở SPEC level — mỗi business rule quan trọng seed ≥1 fault giả định (đảo điều kiện·lệch biên·đổi rate·bỏ guard·nuốt lỗi) → chỉ ra TC NÀO fail; fault không TC nào bắt = oracle trang trí → sửa TC. Bổ trợ (khi có unit/integration): mutation tool (Stryker/PIT/mutmut) trên code path tương ứng + **API contract mutation** (đổi shape/status/format response → client phải xử lý đúng) + mutation trên E2E support code (page objects/factories)
✅/❌ Oracle-minimizer: mỗi assertion nêu được bug nó bắt; assertion không đóng góp → đã xoá (0 Assertion Roulette)
✅/❌ Adversarial-verify đã chạy fresh-context với severity filter: mỗi TC PASS đã bị thử refute (0 tautology lọt)


> **Từ đây trở xuống: máy KHÔNG tính được.** Người tự tích, và chính vì thế kết luận
> của `self_audit.py` dừng ở `SẴN SÀNG-KÈM-KHUYẾT` — tự tích không phải là đo.

END-USER / E2E / UI-UX (BẮT BUỘC cho feature có UI):
✅/❌ Mỗi journey chính có ≥1 E2E chạy PASS trên MỖI platform áp dụng (web=Playwright / mobile=Maestro; real backend/DB) + evidence; platform bị chặn = NOT_EXECUTED có remediation, KHÔNG tính pass
✅/❌ Đã EXECUTE LIVE (không kết luận trên giấy)
✅/❌ UI/UX đã quét: Nielsen 10 heuristics + ISO 9241-11 (3 trục) + visual states (loading/empty/error/disabled/responsive/focus) + WCAG 2.2 A/AA (gồm 6 tiêu chí mới: target size 24px, focus not obscured, dragging alternative, consistent help, redundant entry, accessible auth); phát hiện severity ≥3 → vào Bug Tracker
✅/❌ A11y tự động (axe) đã ghi rõ giới hạn ~57% + liệt kê named manual checks còn lại; axe `incomplete` đã triage
✅/❌ (có đo SUS) UX gate định lượng dạng "≥80% participants SUS > 68" — hoặc N/A lý do
✅/❌ (không UI) E2E/UX ghi N/A có lý do + có integration end-to-end qua API thật

PLATFORM (Bước 0.7 — khi codebase có mobile):
✅/❌ `_platform.json` tồn tại, multi-label + evidence marker; Persona×Journey×Platform matrix có trong domain-pack
✅/❌ 12 loại TC mobile-only đã xét (mỗi loại có TC hoặc N/A lý do)
✅/❌ Hybrid: 2 bộ TC web-layer + native-shell liên kết, không double-count
✅/❌ Testability defect đã file nếu thiếu stable test ID
✅/❌ Device matrix tối thiểu có trong plan (kèm rationale)

COMPLETION / EXIT CRITERIA (chuẩn — BẮT BUỘC đạt; ISO/IEC/IEEE 29119-2):
✅/❌ 100% AC/requirement có ≥1 TC & đã execute (RTM 0 hở, 2 chiều)
✅/❌ 100% coverage item của kỹ thuật đã chọn: EP partitions (valid+invalid) / BVA boundaries / Decision rules khả thi / State transitions hợp lệ + sneak path / Pairwise
✅/❌ Mỗi đặc tính ISO 25010 ÁP DỤNG có ≥1 nhóm TC (security/perf/compat/a11y/reliability…) hoặc N/A có lý do
✅/❌ Risk-based: item rủi ro cao dùng kỹ thuật mạnh hơn (3-value BVA / decision đầy đủ / N-switch / MC/DC)
✅/❌ Residual risk chấp nhận được; 0 defect High/Critical còn mở
✅/❌ Mọi TC có oracle_type + rule_ref (hoặc GAP) — 0 "status 200" trần
✅/❌ 0 TC padding/tautology (không chèn để đủ số/tỷ lệ)

SMELL TEST (heuristic phát hiện thiếu sót — KHÔNG phải ngưỡng chuẩn; lệch → ĐẾM LẠI coverage, đừng chèn bừa):
ℹ️ Tổng TC: [X] (nảy sinh từ coverage; feature rủi ro thấp ~30–40 vẫn đạt nếu coverage đủ)
ℹ️ GREEN [%] / RED [%] / BOUNDARY+EP [%] / SECURITY [%] / A11Y [%] / COMPAT [%] — RED thấp ⇒ nghi thiếu invalid-partition/boundary/sneak-path
ℹ️ P0/P1 phân bổ theo risk assessment (không hạn ngạch cứng)
✅/❌ Đã đi qua 15 dimensions thinking (full) / 8 dimensions (lean)
✅/❌ Đã quét 8 category red-pattern-library

PLAN GROUNDING (Bước 0.5 — nếu có plan đang thực thi):
✅/❌ Đã detect plan (CLAUDE_PLAN_FILE / plans / eng-review artifacts / PR); không có → ghi "no active plan"
✅/❌ 100% Implementation Task (T*) & Failure mode (FM*) của plan có ≥1 TC (Plan↔UAT matrix 0 gap)
✅/❌ Tôn trọng NOT-in-scope của plan (không test cái plan hoãn)
✅/❌ Đã cross-check plan-claim vs CODE THẬT; drift (plan nói có, code chưa/khác) đã báo cáo

ORACLE & DOMAIN (world-class):
✅/❌ Bước 0 đã chạy: `_domain-pack.md` tồn tại (Authority Brief có citation cho domain regulated)
✅/❌ MỌI TC có `oracle_type` + `rule_ref` (hoặc `GAP` có chú thích) — 0 TC "status 200" trần trụi
✅/❌ RTM: 100% `rule_ref`/AC có ≥1 TC; AC HỞ = 0 *(phần TC mồ côi đã do `coverage_calc.py` tính — đừng tích lại)*
✅/❌ 0 mock module nội bộ; mock chỉ ở Mock-allowlist (D6), có lý do
✅/❌ 0 assert tautology (assert true / assert lại input)
✅/❌ Acceptance types: có nhóm OAT (deploy/health/rollback) + RAT (nếu domain regulated)
✅/❌ ISO 25010:2023 (9 đặc tính) — mỗi đặc tính áp dụng có ≥1 nhóm TC

DATA MATURITY MATRIX:
✅/❌ ≥1 fixture cho mỗi state của entity (Active/Pending/Locked/Suspended/Deleted/...)
✅/❌ ≥1 fixture cho mỗi lifecycle critical (trial_end, expiry, dormancy)
✅/❌ ≥1 fixture với shape extreme (empty + full) cho list entities
✅/❌ Mọi TC có data_required → fixture tồn tại trong matrix
✅/❌ Mọi fixture có setup_recipe + cleanup_recipe runnable bởi runner
✅/❌ Setup dùng {{random}} để tránh email collision
```

## Scripts

- **`scripts/generate_uat_excel.py`** — Sinh Excel 6 sheets (Summary, Test Cases, Test Data, Data Matrix, Bug Tracker, Regression Log)
- **`scripts/generate_uat_markdown.py`** — Sinh Markdown tối ưu Claude Code
- **`scripts/merge_batches.py`** — Merge multiple batch JSON files thành 1 input.json

## Reference files (load on-demand)

KHÔNG load tất cả. Chỉ đọc khi cần ở bước tương ứng:

| File | Khi nào ĐỌC |
|------|--------------|
| ⭐ `domain-research-discovery.md` | **Bước 0 — research + discovery nghiệp vụ (mọi dự án)** |
| ⭐ `plan-analysis.md` | **Bước 0.5 — phân tích sâu plan đang thực thi (nếu có)** |
| ⭐ `platform-detection.md` | **Bước 0.7 — detect platform multi-label + JSON contract (chung với runner)** |
| ⭐ `handoff-schema.md` | **Bước 7 — schema TC bàn giao cho uat-test-runner** |
| ⭐ `coverage-ledger.md` | **Bước 6 — Coverage+Effectiveness Ledger (enumerate + TC_min MAX + mutation + critic)** |
| ⭐ `ui-ux-evaluation.md` | **Bước 7b — đánh giá UI/UX (ISO 9241-11 + Nielsen 10 + WCAG 2.2) cho UI feature** |
| ⭐ `oracle-catalog.md` | **Bước 6+7 — gán oracle_type/rule_ref + RTM + acceptance types + ISO 25010:2023** |
| `coverage-calculator.md` | Bước 1 — coverage criteria + ước lượng TC (coverage-driven) |
| `codebase-analysis-framework.md` | Bước 1 — khi có codebase |
| `deep-thinking-checklist.md` | Bước 2 — gate trước viết case |
| `red-pattern-library.md` | Bước 7 — khi viết RED case |
| **`data-maturity-matrix.md`** | **Bước 8 — sinh data fixtures** |
| `excel-schema.md` | Trước khi gọi generate_uat_excel.py |
| `test-design-techniques.md` | Bước 5 — khi áp BVA/EP/DT |
| `security-payloads.md` | Bước 8 — khi build test data security |
| `accessibility-wcag.md` | Bước 7 — khi viết A11y case |
| `compatibility-matrix.md` | Bước 7 — khi viết COMPAT case |
| `example-full-uat.md` | Tham khảo cuối, không bắt buộc |
| `anti-patterns.md` | Khi self-audit phát hiện vấn đề |
| `compliance-checklists.md` | Khi feature liên quan GDPR/PCI |

## Khi user follow-up

| User nói | Hành động |
|----------|-----------|
| "Thêm case X" | Add vào JSON, regenerate Excel+MD |
| "Sửa case TC-XXX" | Edit JSON, regenerate |
| "Convert sang Gherkin" | Translate sang Given-When-Then |
| "Review test case của tôi" | So với 14 loại + Coverage Ledger + completion criteria, chỉ ra gap CỤ THỂ |
| "Rút gọn" | TỪ CHỐI — giải thích vì sao không nên rút gọn UAT |
| "Chỉ happy path" | TỪ CHỐI — coverage chuẩn đòi phủ partition KHÔNG hợp lệ + boundary + đường lỗi (29119-4); bỏ negative = fail completion criteria |
| "Lean mode" | Chuyển sang LEAN (xem section trên) |
