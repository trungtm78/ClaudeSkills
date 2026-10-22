#!/usr/bin/env node
// run_a11y.mjs — G16: phần ĐO ĐƯỢC của khả năng tiếp cận (axe-core, rule set WCAG 2.2 AA).
//
// Chạy từ <OUT> (nơi đã npm install):
//   cd <OUT> && node <skill>/scripts/run_a11y.mjs --url http://127.0.0.1:8170 \
//        --specs tests --out a11y.json
//
// TRẦN ĐO LƯỜNG — báo cáo bắt buộc in ra, đừng bỏ:
//   axe-core bắt khoảng 57% lỗi a11y theo SỐ LƯỢNG, nhưng chỉ 29,5% tiêu chí WCAG 2.2 là
//   tự động hoá được; 60,2% buộc kiểm thủ công. G16 xanh KHÔNG phải là tuyên bố tuân thủ
//   WCAG 2.2 AA. Phần còn lại — thứ tự focus, bàn phím, trình đọc màn hình, vùng chạm —
//   nằm ở G6 và mãi là CẦN NGƯỜI.
//
// Chặn: vi phạm mức critical/serious. Ghi nhận không chặn: moderate/minor và mọi mục
// "incomplete" (chỗ axe không dám kết luận — đó đúng là chỗ cần người nhìn).
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(path.join(process.cwd(), 'package.json'));
let chromium, AxeBuilder;
try {
  chromium = require('@playwright/test').chromium;
} catch {
  console.error('run_a11y: không tìm thấy @playwright/test trong ' + process.cwd() +
    ' — chạy từ thư mục <OUT> sau khi npm install');
  process.exit(2);
}
try {
  AxeBuilder = require('@axe-core/playwright').default;
} catch {
  // Thiếu thư viện là chuyện có thật (mạng, bản offline). Nói thật và để G16 HẠ TRẦN,
  // tuyệt đối không ghi "0 vi phạm" cho một lượt chưa hề quét.
  const out = process.argv.includes('--out') ? process.argv[process.argv.indexOf('--out') + 1] : 'a11y.json';
  fs.writeFileSync(out, JSON.stringify({
    not_run: true, reason: 'thiếu @axe-core/playwright trong ' + process.cwd(),
    scanned: [], violations: [], incomplete: [],
  }, null, 2), 'utf-8');
  console.error('run_a11y: KHÔNG CHẠY — thiếu @axe-core/playwright');
  process.exit(4);
}

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, arr) => {
  if (v.startsWith('--')) acc.push([v.slice(2), (arr[i + 1] && !arr[i + 1].startsWith('--')) ? arr[i + 1] : 'true']);
  return acc;
}, []));
const BASE = (args.url || process.env.UAT_BASE_URL || '').replace(/\/+$/, '');
const OUT = args.out || 'a11y.json';
const SPECS = args.specs || 'tests';
const TAGS = (args.tags || 'wcag2a,wcag2aa,wcag21a,wcag21aa,wcag22aa').split(',');
const STORAGE = args['storage-state'] || process.env.UAT_STORAGE_STATE || '';

// Quét đúng những màn hình kịch bản ĐÃ chạm: rút mọi goto('...') trong spec đã đóng băng.
// Không tự đi lang thang: một lượt UAT phải tái hiện được, mà bò trang thì không.
function urlsFromSpecs(dir) {
  const found = new Set();
  const walk = (d) => {
    let ents = [];
    try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) { walk(p); continue; }
      if (!/\.(ts|js|mjs)$/.test(e.name) || e.name.startsWith('_canary')) continue;
      const txt = fs.readFileSync(p, 'utf-8');
      for (const m of txt.matchAll(/\.goto\(\s*['"`]([^'"`]+)['"`]/g)) {
        const u = m[1];
        if (u.startsWith('http')) found.add(u);
        else found.add(BASE + (u.startsWith('/') ? u : '/' + u));
      }
    }
  };
  walk(dir);
  return [...found];
}

const targets = (args.only ? [args.only] : urlsFromSpecs(SPECS));
if (BASE && !targets.length) targets.push(BASE + '/');

const report = { not_run: false, tags: TAGS, scanned: [], failed_to_scan: [],
                 violations: [], incomplete: [],
                 ceiling: 'axe-core bắt ~57% lỗi a11y theo số lượng; chỉ 29,5% tiêu chí WCAG 2.2 ' +
                          'tự động hoá được, 60,2% buộc kiểm thủ công. G16 xanh KHÔNG phải là ' +
                          'tuyên bố tuân thủ WCAG 2.2 AA.' };

const browser = await chromium.launch();
const ctx = await browser.newContext(STORAGE ? { storageState: STORAGE } : {});
for (const u of targets) {
  const page = await ctx.newPage();
  try {
    await page.goto(u, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const res = await new AxeBuilder({ page }).withTags(TAGS).analyze();
    report.scanned.push(u);
    for (const v of res.violations) {
      report.violations.push({
        url: u, id: v.id, impact: v.impact || 'minor', help: v.help,
        helpUrl: v.helpUrl, nodes: v.nodes.length,
        sample: (v.nodes[0]?.target || []).join(' '),
      });
    }
    for (const v of res.incomplete) {
      report.incomplete.push({ url: u, id: v.id, help: v.help, nodes: v.nodes.length });
    }
  } catch (e) {
    report.failed_to_scan.push({ url: u, error: String(e).slice(0, 200) });
  } finally {
    await page.close();
  }
}
await browser.close();

const BLOCK = new Set(['critical', 'serious']);
report.blocking = report.violations.filter((v) => BLOCK.has(v.impact));
report.ok = report.blocking.length === 0 && report.scanned.length > 0;
if (!report.scanned.length) {
  report.not_run = true;
  report.reason = 'không quét được màn hình nào (kịch bản không có goto, hoặc app không tới được)';
}
fs.writeFileSync(OUT, JSON.stringify(report, null, 2), 'utf-8');
console.log(`run_a11y: quét ${report.scanned.length} màn · vi phạm chặn ` +
  `${report.blocking.length} (critical/serious) · ghi nhận ${report.violations.length - report.blocking.length}` +
  ` · chưa kết luận được ${report.incomplete.length}`);
for (const v of report.blocking.slice(0, 10)) {
  console.log(`  x [${v.impact}] ${v.id} — ${v.help} (${v.nodes} phần tử) @ ${v.url}`);
}
process.exit(report.not_run ? 4 : (report.ok ? 0 : 1));
