#!/usr/bin/env node
// monkey_web.mjs — monkey test cho web: chuỗi thao tác NGẪU NHIÊN CÓ SEED, chỉ QUAN SÁT và GHI.
//
// Chạy từ thư mục kết quả <OUT> (nơi đã `npm install` @playwright/test), để import tìm đúng chỗ:
//   cd <OUT> && node <skill>/scripts/monkey_web.mjs --url http://localhost:8170 --seed 42 \
//        --actions 200 --max-seconds 180 --out monkey
//
// Oracle (thứ được coi là BẤT THƯỜNG):
//   S1  trang sập (page 'crash')
//   S2  lỗi JS không bắt (pageerror) · phản hồi 5xx cùng origin · trang trắng · thao tác treo > 15 s
//   S3  console.error (ghi nhận, KHÔNG chặn kết luận)
// Rào an toàn:
//   * chỉ bấm phần tử nhìn thấy, không disabled, cùng origin; lạc ra origin khác → lùi lại
//   * DANH SÁCH CẤM BẤM (xóa/delete/đăng xuất/logout/thanh toán/pay/hủy/remove/drop…) + --deny thêm
//   * không tải tệp lên, hộp thoại alert/confirm tự ĐÓNG (dismiss — không bao giờ "đồng ý")
//   * chỉ chạy trên máy chủ local/staging/dev/test/uat, trừ khi UAT_MONKEY_ALLOW_HOST=<host>
// Tái hiện: cùng --seed + cùng trạng thái dữ liệu ⇒ cùng chuỗi thao tác. Mỗi bất thường ghi
// số bước; `--actions <bước>` dừng đúng chỗ ấy.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(path.join(process.cwd(), 'package.json'));
let pw;
try {
  pw = require('@playwright/test');
} catch (e) {
  console.error('monkey_web: không tìm thấy @playwright/test trong ' + process.cwd() +
    ' — chạy từ thư mục <OUT> sau khi npm install');
  process.exit(2);
}
const { chromium } = pw;

// ── tham số ──
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, arr) => {
  if (v.startsWith('--')) acc.push([v.slice(2), (arr[i + 1] && !arr[i + 1].startsWith('--')) ? arr[i + 1] : 'true']);
  return acc;
}, []));
const START = args.url;
const SEED = parseInt(args.seed || String(Date.now() % 100000), 10);
const MAX_ACTIONS = parseInt(args.actions || '200', 10);
const MAX_SECONDS = parseInt(args['max-seconds'] || '180', 10);
const OUTDIR = args.out || 'monkey';
const STORAGE = args['storage-state'] || process.env.UAT_STORAGE_STATE || '';
const HANG_MS = parseInt(args['hang-ms'] || '15000', 10);
const EXTRA_DENY = (args.deny || '').split(',').map(s => s.trim()).filter(Boolean);
if (!START) { console.error('monkey_web: thiếu --url'); process.exit(1); }

const origin = new URL(START).origin;
const host = new URL(START).hostname;
const SAFE_HOST = /^(localhost|127\.0\.0\.1|\[?::1\]?|0\.0\.0\.0)$|\.local$|\.test$|(^|[.-])(staging|stg|dev|test|uat|qa|sandbox)([.-]|$)/i;
if (!SAFE_HOST.test(host) && process.env.UAT_MONKEY_ALLOW_HOST !== host) {
  const out = { seed: SEED, url: START, not_run: true,
    reason: `máy chủ '${host}' không phải local/staging — monkey có thể tạo/xoá dữ liệu thật. ` +
            `Đặt UAT_MONKEY_ALLOW_HOST=${host} nếu chắc chắn đây là môi trường kiểm thử.`, anomalies: [] };
  fs.mkdirSync(OUTDIR, { recursive: true });
  fs.writeFileSync(path.join(OUTDIR, `web-${SEED}.json`), JSON.stringify(out, null, 2));
  console.log('monkey_web: KHÔNG CHẠY — ' + out.reason);
  process.exit(4);
}

const DENY = new RegExp([
  'xo[áa]', 'x[óo]a', 'delete', 'remove', 'drop', 'truncate', 'destroy', 'purge', 'wipe',
  'đăng xuất', 'dang xuat', 'logout', 'log out', 'sign out', 'signout',
  'thanh to[áa]n', 'pay', 'checkout', 'purchase', 'mua ngay', 'đặt hàng',
  'h[ủu]y t[àa]i kho[ảa]n', 'deactivate', 'reset', 'kh[ôo]i ph[ụu]c c[àa]i đ[ặa]t',
  'g[ửu]i email', 'send email', 'publish', 'xu[ấa]t b[ảa]n',
  ...EXTRA_DENY,
].join('|'), 'i');

// mulberry32 — PRNG có seed, đủ cho tái hiện.
function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const R = rng(SEED);
const pick = (arr) => arr[Math.floor(R() * arr.length)];

const PAYLOADS = [
  '', ' ', 'a', 'Nguyễn Văn Á', 'Đặng Thị Ổi ỹ ự', '😀🔥🧪', '0', '-1', '1e9', '999999999999',
  '3.14159', '1,5', '<script>alert(1)</script>', '" onmouseover="x', "' OR '1'='1", '../../etc/passwd',
  '%00', '{{7*7}}', '${7*7}', 'x'.repeat(300), 'A'.repeat(5000), '  khoảng trắng  ', '\t\n',
  'test@example.com', 'khong-phai-email', '2026-02-30', '31/12/9999', '+84 912 345 678',
];

fs.mkdirSync(path.join(OUTDIR, 'shots'), { recursive: true });
const anomalies = new Map();   // chữ ký → bất thường (đếm số lần)
const log = [];                 // mọi thao tác
let step = 0;
let consoleErrors = 0;

function record(type, severity, message, url) {
  const msg = String(message || '').replace(/\s+/g, ' ').slice(0, 400);
  let p = '';
  try { p = new URL(url || START).pathname; } catch { p = String(url || ''); }
  const sig = `${type}|${p}|${msg.slice(0, 120)}`;
  if (anomalies.has(sig)) { anomalies.get(sig).count++; return null; }
  const a = { type, severity, message: msg, url: url || '', step, count: 1,
    last_actions: log.slice(-20), screenshot: '' };
  anomalies.set(sig, a);
  return a;
}

const browser = await chromium.launch();
const context = await browser.newContext({
  ...(STORAGE && fs.existsSync(STORAGE) ? { storageState: STORAGE } : {}),
  acceptDownloads: false, viewport: { width: 1366, height: 800 },
});
const page = await context.newPage();
page.on('dialog', d => { log.push({ step, action: 'dialog', text: d.message().slice(0, 120) }); d.dismiss().catch(() => {}); });
page.on('filechooser', fc => { log.push({ step, action: 'filechooser-bo-qua' }); });
page.on('pageerror', e => { record('pageerror', 'S2', e.message || String(e), page.url()); });
page.on('console', m => {
  if (m.type() === 'error') { consoleErrors++; record('console.error', 'S3', m.text(), page.url()); }
});
page.on('response', r => {
  try {
    if (r.status() >= 500 && new URL(r.url()).origin === origin) {
      record('http5xx', 'S2', `${r.status()} ${r.request().method()} ${new URL(r.url()).pathname}`, page.url());
    }
  } catch { /* URL lạ */ }
});
page.on('crash', () => { record('crash', 'S1', 'trang sập (renderer crash)', page.url()); });

async function snap(a) {
  if (!a || a.screenshot) return;
  const f = path.join(OUTDIR, 'shots', `s${SEED}-b${a.step}-${a.type}.png`);
  try { await page.screenshot({ path: f, fullPage: false, timeout: 5000 }); a.screenshot = f; } catch { /* trang sập */ }
}

async function candidates() {
  return page.evaluate((denySrc) => {
    const deny = new RegExp(denySrc, 'i');
    const sel = 'a[href],button,input,textarea,select,[role=button],[role=link],[role=tab],[role=menuitem],' +
      '[role=checkbox],[role=switch],[role=option],[onclick],summary,label[for]';
    const out = [];
    const els = Array.from(document.querySelectorAll(sel));
    els.forEach((el, idx) => {
      const r = el.getBoundingClientRect();
      const st = getComputedStyle(el);
      if (r.width < 2 || r.height < 2 || st.visibility === 'hidden' || st.display === 'none') return;
      if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) return;
      if (el.disabled || el.getAttribute('aria-disabled') === 'true') return;
      const text = ((el.innerText || el.value || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' +
        (el.getAttribute('title') || '') + ' ' + (el.getAttribute('name') || '') + ' ' + (el.id || '')).trim();
      if (deny.test(text)) return;
      const tag = el.tagName.toLowerCase();
      const type = (el.getAttribute('type') || '').toLowerCase();
      if (type === 'file') return;
      if (tag === 'a') {
        const h = el.getAttribute('href') || '';
        if (/^(mailto:|tel:|javascript:)/i.test(h)) return;
        if (deny.test(h)) return;
        try { if (new URL(h, location.href).origin !== location.origin) return; } catch { return; }
        if (el.getAttribute('target') === '_blank') return;
      }
      if (tag === 'form' || (tag === 'button' && el.form && el.form.action &&
          new URL(el.form.action, location.href).origin !== location.origin)) return;
      el.setAttribute('data-monkey-i', String(idx));
      out.push({ i: idx, tag, type, text: text.slice(0, 60) });
    });
    return out;
  }, DENY.source);
}

async function act() {
  const roll = R();
  if (roll < 0.06) {
    const dy = Math.floor(R() * 1600) - 400;
    log.push({ step, action: 'scroll', dy });
    await page.mouse.wheel(0, dy);
    return;
  }
  if (roll < 0.11) {
    const k = pick(['Tab', 'Enter', 'Escape', 'ArrowDown', 'ArrowUp', 'Space']);
    log.push({ step, action: 'key', key: k });
    await page.keyboard.press(k);
    return;
  }
  if (roll < 0.13) {
    log.push({ step, action: 'back' });
    await page.goBack({ timeout: HANG_MS }).catch(() => {});
    return;
  }
  if (roll < 0.14) {
    const vp = pick([{ width: 390, height: 844 }, { width: 820, height: 1180 }, { width: 1366, height: 800 }]);
    log.push({ step, action: 'viewport', ...vp });
    await page.setViewportSize(vp);
    return;
  }
  const cs = await candidates();
  if (!cs.length) {
    log.push({ step, action: 'no-candidate' });
    await page.goto(START, { timeout: HANG_MS }).catch(() => {});
    return;
  }
  const c = pick(cs);
  const loc = page.locator(`[data-monkey-i="${c.i}"]`).first();
  if (c.tag === 'select') {
    const n = await loc.locator('option').count().catch(() => 0);
    const idx = n ? Math.floor(R() * n) : 0;
    log.push({ step, action: 'select', target: c.text, index: idx });
    await loc.selectOption({ index: idx }, { timeout: 3000 }).catch(() => {});
  } else if ((c.tag === 'input' && !['checkbox', 'radio', 'submit', 'button', 'reset', 'image'].includes(c.type)) || c.tag === 'textarea') {
    const v = pick(PAYLOADS);
    log.push({ step, action: 'fill', target: c.text || c.tag, value: v.slice(0, 40) });
    await loc.fill(v, { timeout: 3000 }).catch(() => {});
    if (R() < 0.3) await page.keyboard.press('Enter').catch(() => {});
  } else {
    log.push({ step, action: 'click', target: c.text || c.tag });
    await loc.click({ timeout: 3000, noWaitAfter: false }).catch(() => {});
  }
}

const t0 = Date.now();
let ended = 'du-so-thao-tac';
await page.goto(START, { timeout: 30000 }).catch(e => record('khong-mo-duoc', 'S2', String(e), START));
for (step = 1; step <= MAX_ACTIONS; step++) {
  if ((Date.now() - t0) / 1000 > MAX_SECONDS) { ended = 'het-thoi-gian'; break; }
  if (page.isClosed()) { ended = 'trang-dong'; break; }
  const before = anomalies.size;
  const a0 = Date.now();
  let timer;
  const hang = new Promise(res => { timer = setTimeout(() => res('treo'), HANG_MS); });
  const r = await Promise.race([act().then(() => 'ok').catch(() => 'loi'), hang]);
  clearTimeout(timer);
  if (r === 'treo') { record('treo', 'S2', `thao tác không xong sau ${HANG_MS} ms: ${JSON.stringify(log.at(-1))}`, page.url()); }
  await page.waitForLoadState('domcontentloaded', { timeout: 5000 }).catch(() => {});
  // lạc khỏi origin → lùi lại (không tính lỗi)
  try {
    if (new URL(page.url()).origin !== origin) {
      log.push({ step, action: 'lac-origin', url: page.url() });
      await page.goBack({ timeout: 5000 }).catch(() => {});
      if (new URL(page.url()).origin !== origin) await page.goto(START, { timeout: 15000 }).catch(() => {});
    }
  } catch { /* about:blank */ }
  // trang trắng — kiểm mỗi 10 bước
  if (step % 10 === 0) {
    const blank = await page.evaluate(() => {
      const t = (document.body && document.body.innerText || '').trim();
      const media = document.querySelectorAll('img,svg,canvas,video,iframe').length;
      return t.length === 0 && media === 0;
    }).catch(() => false);
    if (blank) record('trang-trang', 'S2', 'trang không có chữ lẫn hình', page.url());
  }
  if (anomalies.size > before) {
    for (const a of anomalies.values()) await snap(a);
  }
  log.at(-1) && (log.at(-1).ms = Date.now() - a0);
}
await browser.close().catch(() => {});

const list = [...anomalies.values()];
const out = {
  seed: SEED, url: START, actions_done: Math.min(step, MAX_ACTIONS), ended,
  duration_s: Math.round((Date.now() - t0) / 1000), console_errors: consoleErrors,
  anomalies: list, blocking: list.filter(a => a.severity === 'S1' || a.severity === 'S2').length,
  replay: `node <skill>/scripts/monkey_web.mjs --url ${START} --seed ${SEED} --actions <bước>`,
};
fs.writeFileSync(path.join(OUTDIR, `web-${SEED}.json`), JSON.stringify(out, null, 2));
fs.writeFileSync(path.join(OUTDIR, `web-${SEED}.actions.json`), JSON.stringify(log, null, 1));
console.log(`monkey_web: seed ${SEED} · ${out.actions_done} thao tác · ${out.duration_s}s · ` +
  `bất thường ${list.length} (chặn ${out.blocking}) · console.error ${consoleErrors}`);
for (const a of list.slice(0, 15)) console.log(`  ${a.severity} ${a.type} @bước ${a.step} ×${a.count}: ${a.message.slice(0, 120)}`);
process.exit(0);
