# Ghi chú stack — đặc thù khi sinh/chạy test chuyên gia

## Odoo (Python ORM)
- **Chạy test:** `<venv>/python odoo-bin -c odoo.conf -d <db> -u <module> --test-enable --test-tags /<module> --stop-after-init --no-http`. Trên Windows đặt `PYTHONUTF8=1`, `MSYS_NO_PATHCONV=1`.
- **Lọc theo class:** `--test-tags "/<module>:<ClassName>"` (chạy nhanh 1 nhóm khi lặp).
- **Property (hypothesis) BÊN TRONG `TransactionCase`:** tạo record ở `setUpClass`, mỗi example GHI lại tham số rồi đọc field compute (đừng tạo record mới mỗi example — chậm + phình). `@settings(deadline=None, suppress_health_check=list(HealthCheck))` vì ORM chậm + dùng class fixture.
- **Skip mềm khi thiếu hypothesis:** `try: import hypothesis except ImportError:` để suite không vỡ trên máy chưa cài.
- **Mutation (cosmic-ray):** `test-command` phải là lệnh odoo-bin đầy đủ; mỗi mutant chạy lại cả suite (nặng) → giới hạn `module-path` vào 1 file engine, chạy nền. Proof-of-concept nhanh = đột biến tay 1 dòng → property đỏ → revert (đã minh hoạ trong example-aic.md).
- **Đánh giá UX live:** dùng browse tool đăng nhập (`input[name=login]`/`input[name=password]`), điều hướng `/<db>/odoo/action-<xmlid>`, `console --errors` để bắt OWL/RPC; đọc field compute qua JSON-RPC `/web/dataset/call_kw` (deterministic, không phụ thuộc DOM OWL mong manh).

## JS/TS
- Property: `fast-check` (`fc.assert(fc.property(...))`). Mutation: `Stryker` (`stryker run`). Perf: `k6`/`autocannon`. Test-runner: vitest/jest.

## Java
- Property: `jqwik` (`@Property`). Mutation: `PIT` (`mvn org.pitest:pitest-maven:mutationCoverage`). Perf: JMeter/Gatling.

## Nguyên tắc chung
- Luôn lấy **recipe chạy test của chính dự án** (từ CI/Makefile/memory) thay vì đoán.
- Mutation kill rate đo trên **module logic lõi**, không phải view/config/boilerplate.
