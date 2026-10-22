# Chọn trình duyệt · viewport emulation vs app thật

> Tách từ `SKILL.md` để giảm lượng chữ phải nạp mỗi lần gọi skill. Nạp khi cần.

## Khi nào dùng Firefox/WebKit?

Chỉ khi user nói explicit:
- "Test trên Firefox"
- "Multi-browser support"
- "Cross-browser test"

Lúc đó bật thêm project trong config:
```typescript
{ name: 'e2e-firefox', testMatch: '**/*.e2e.spec.ts', use: { ...devices['Desktop Firefox'] }},
{ name: 'e2e-webkit', testMatch: '**/*.e2e.spec.ts', use: { ...devices['Desktop Safari'] }},
```

## Mobile: viewport emulation vs app THẬT — phân biệt rõ

**App mobile thật (Flutter/RN/native/hybrid — label từ `_platform.json`)** → Gate 3 **Maestro** trên emulator/device thật: `references/mobile-runner.md` (preflight Java17+Maestro, device ladder, build+install app, localhost→10.0.2.2, flow YAML per TC, crash oracle logcat, JUnit output). iOS trên Windows = NOT_EXECUTED + remediation.

**Web responsive / TC COMPAT mention mobile** → chỉ cần Playwright device descriptor (KHÔNG phải test app mobile thật — không engine iOS Safari thật, không gesture inertia):
```typescript
{ name: 'e2e-mobile-viewport', testMatch: '**/*.e2e.spec.ts', use: { ...devices['Pixel 7'] }},
```

