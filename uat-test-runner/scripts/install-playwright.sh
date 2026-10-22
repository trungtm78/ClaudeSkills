#!/bin/bash
# install-playwright.sh - Cài đặt Playwright đầy đủ + tạo cấu trúc dự án
# Script này idempotent: chạy nhiều lần không gây lỗi.

set -e

echo "🚀 Bắt đầu cài đặt Playwright..."
echo ""

# 1. Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js chưa được cài. Vui lòng cài Node.js >= 18 trước."
    echo "   Linux/Mac: https://nodejs.org/ hoặc dùng nvm"
    echo "   Windows: tải installer từ https://nodejs.org/"
    exit 1
fi
echo "✅ Node.js: $(node -v)"

# 2. Tạo package.json nếu chưa có
if [ ! -f "package.json" ]; then
    echo "📦 Đang khởi tạo package.json..."
    npm init -y > /dev/null
    echo "✅ Đã tạo package.json"
else
    echo "✅ package.json: đã tồn tại"
fi

# 3. Cài @playwright/test + typescript
echo ""
echo "📦 Đang cài @playwright/test, typescript, @types/node..."
echo "   (Có thể mất 1-2 phút lần đầu)"
npm install -D @playwright/test typescript @types/node dotenv 2>&1 | tail -5
echo "✅ Đã cài npm packages"

# 4. Cài browsers
echo ""
echo "🌐 Đang cài browsers (chromium, firefox, webkit)..."
echo "   (Lần đầu mất 3-5 phút, browser size ~300MB)"
npx playwright install --with-deps 2>&1 | tail -3
echo "✅ Đã cài đặt browsers"

# 5. Tạo cấu trúc thư mục
echo ""
echo "📁 Đang tạo cấu trúc thư mục..."
mkdir -p tests/pages
mkdir -p tests/specs
mkdir -p tests/fixtures
mkdir -p tests/helpers
echo "✅ Đã tạo: tests/{pages,specs,fixtures,helpers}"

# 6. Tạo playwright.config.ts nếu chưa có
if [ ! -f "playwright.config.ts" ] && [ ! -f "playwright.config.js" ]; then
    echo ""
    echo "⚙️  Đang tạo playwright.config.ts mặc định..."
    cat > playwright.config.ts << 'CONFIGEOF'
import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

// Load env variables từ file .env
dotenv.config();

/**
 * Playwright config cho UAT testing
 * Tham khảo: https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/specs',

  // Chạy test trong file song song
  fullyParallel: true,

  // Cấm test.only trên CI
  forbidOnly: !!process.env.CI,

  // Retry 2 lần trên CI, 0 lần local
  retries: process.env.CI ? 2 : 0,

  // Số worker chạy song song
  workers: process.env.CI ? 1 : undefined,

  // Reporter: HTML + list (cho terminal)
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],

  // Cấu hình chung cho mọi test
  use: {
    // URL gốc của app - lấy từ .env hoặc default localhost
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // Lưu trace khi retry để debug
    trace: 'on-first-retry',

    // Screenshot khi fail
    screenshot: 'only-on-failure',

    // Video khi fail
    video: 'retain-on-failure',

    // Action timeout (mỗi click/fill)
    actionTimeout: 10_000,

    // Navigation timeout
    navigationTimeout: 30_000,
  },

  // Test timeout tổng
  timeout: 30_000,

  // Cấu hình expect
  expect: {
    timeout: 5_000,
  },

  // Multi-browser projects
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Bỏ comment để test thêm browser khác
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
  ],

  // Bỏ comment nếu muốn Playwright tự start app
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: !process.env.CI,
  // },
});
CONFIGEOF
    echo "✅ Đã tạo playwright.config.ts"
else
    echo "✅ playwright.config: đã tồn tại (không ghi đè)"
fi

# 7. Tạo .env.example
if [ ! -f ".env.example" ]; then
    cat > .env.example << 'ENVEOF'
# URL gốc của app cần test
BASE_URL=http://localhost:3000

# Test credentials (KHÔNG commit .env thật vào git!)
TEST_USER_EMAIL=alice@test.com
TEST_USER_PASSWORD=Valid@123
TEST_ADMIN_EMAIL=admin@test.com
TEST_ADMIN_PASSWORD=Admin@123

# API base URL (nếu khác với BASE_URL)
API_BASE_URL=http://localhost:3000/api

# Database test (cho seed/cleanup)
TEST_DB_URL=postgresql://...
ENVEOF
    echo "✅ Đã tạo .env.example"
fi

# 8. Tạo .gitignore entries
if [ -f ".gitignore" ]; then
    # Append nếu chưa có
    if ! grep -q "playwright-report" .gitignore; then
        cat >> .gitignore << 'GITEOF'

# Playwright
node_modules/
test-results/
playwright-report/
playwright/.cache/
.env
GITEOF
        echo "✅ Đã update .gitignore"
    fi
else
    cat > .gitignore << 'GITEOF'
# Node
node_modules/

# Playwright
test-results/
playwright-report/
playwright/.cache/

# Env
.env
GITEOF
    echo "✅ Đã tạo .gitignore"
fi

# 9. Update package.json scripts
echo ""
echo "📝 Đang thêm scripts vào package.json..."
node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
pkg.scripts = pkg.scripts || {};
pkg.scripts['test'] = 'playwright test';
pkg.scripts['test:headed'] = 'playwright test --headed';
pkg.scripts['test:debug'] = 'playwright test --debug';
pkg.scripts['test:ui'] = 'playwright test --ui';
pkg.scripts['test:p0'] = 'playwright test --grep @P0';
pkg.scripts['test:smoke'] = 'playwright test --grep @smoke';
pkg.scripts['test:report'] = 'playwright show-report';
pkg.scripts['test:codegen'] = 'playwright codegen';
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
"
echo "✅ Đã thêm test scripts"

# 10. Verify
echo ""
echo "═══════════════════════════════════════════"
echo "🎉 CÀI ĐẶT HOÀN TẤT!"
echo "═══════════════════════════════════════════"
echo ""
echo "📋 Các lệnh hữu ích:"
echo "   npm test              - Chạy tất cả test"
echo "   npm run test:headed   - Chạy với browser hiển thị"
echo "   npm run test:debug    - Debug mode"
echo "   npm run test:ui       - UI mode (recommended cho dev)"
echo "   npm run test:p0       - Chỉ chạy P0 tests"
echo "   npm run test:report   - Xem HTML report sau khi chạy"
echo ""
echo "📁 Cấu trúc dự án:"
echo "   tests/pages/    - Page Object Models"
echo "   tests/specs/    - Test spec files"
echo "   tests/fixtures/ - Test data"
echo "   tests/helpers/  - Utility functions"
echo ""
echo "⚙️  Nhớ tạo file .env từ .env.example trước khi chạy test!"
exit 0
