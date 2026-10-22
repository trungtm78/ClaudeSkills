#!/bin/bash
# check-env.sh - Kiểm tra môi trường Playwright
# Exit codes:
#   0 = Tất cả đã sẵn sàng
#   1 = Thiếu Node.js
#   2 = Chưa có package.json (cần npm init)
#   3 = Chưa cài @playwright/test
#   4 = Chưa cài browsers

set -e

echo "🔍 Đang kiểm tra môi trường Playwright..."
echo ""

# 1. Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js chưa được cài đặt"
    echo "   Vui lòng cài Node.js >= 18: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠️  Node.js version hiện tại: $(node -v)"
    echo "   Khuyến nghị Node.js >= 18 cho Playwright"
fi
echo "✅ Node.js: $(node -v)"

# 2. Check npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm chưa được cài đặt"
    exit 1
fi
echo "✅ npm: $(npm -v)"

# 3. Check package.json
if [ ! -f "package.json" ]; then
    echo "❌ Chưa có package.json trong thư mục hiện tại"
    echo "   Cần chạy: npm init -y"
    exit 2
fi
echo "✅ package.json: tồn tại"

# 4. Check @playwright/test
if ! grep -q '"@playwright/test"' package.json 2>/dev/null; then
    echo "❌ @playwright/test chưa được cài"
    echo "   Cần chạy: npm install -D @playwright/test"
    exit 3
fi

# Check thực tế trong node_modules
if [ ! -d "node_modules/@playwright/test" ]; then
    echo "⚠️  @playwright/test có trong package.json nhưng chưa cài"
    echo "   Cần chạy: npm install"
    exit 3
fi
PLAYWRIGHT_VERSION=$(node -e "console.log(require('@playwright/test/package.json').version)" 2>/dev/null || echo "unknown")
echo "✅ @playwright/test: v$PLAYWRIGHT_VERSION"

# 5. Check browsers đã install
BROWSER_CACHE="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.cache/ms-playwright}"
if [ ! -d "$BROWSER_CACHE" ]; then
    echo "❌ Browsers Playwright chưa được cài"
    echo "   Cần chạy: npx playwright install"
    exit 4
fi

CHROMIUM_FOUND=$(find "$BROWSER_CACHE" -maxdepth 1 -type d -name "chromium-*" 2>/dev/null | head -1)
if [ -z "$CHROMIUM_FOUND" ]; then
    echo "❌ Chromium browser chưa được cài"
    echo "   Cần chạy: npx playwright install chromium"
    exit 4
fi
echo "✅ Chromium browser: đã cài"

FIREFOX_FOUND=$(find "$BROWSER_CACHE" -maxdepth 1 -type d -name "firefox-*" 2>/dev/null | head -1)
if [ -n "$FIREFOX_FOUND" ]; then
    echo "✅ Firefox browser: đã cài"
fi

WEBKIT_FOUND=$(find "$BROWSER_CACHE" -maxdepth 1 -type d -name "webkit-*" 2>/dev/null | head -1)
if [ -n "$WEBKIT_FOUND" ]; then
    echo "✅ Webkit browser: đã cài"
fi

# 6. Check config file
if [ -f "playwright.config.ts" ] || [ -f "playwright.config.js" ]; then
    echo "✅ playwright.config: tồn tại"
else
    echo "⚠️  Chưa có playwright.config.ts (sẽ được tạo nếu cần)"
fi

# 7. Check tests folder
if [ -d "tests" ] || [ -d "e2e" ]; then
    echo "✅ Thư mục tests: tồn tại"
else
    echo "ℹ️  Chưa có thư mục tests (sẽ được tạo)"
fi

echo ""
echo "🎉 Môi trường Playwright đã sẵn sàng!"
exit 0
