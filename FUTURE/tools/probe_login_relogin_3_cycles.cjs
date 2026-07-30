const childProcess = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT_DIR = "C:\\Users\\Admin\\.codex\\plans\\server2_postgres_full_audit";
const BASE = process.env.FUTURE_LOGIN_CPU_BASE || "http://127.0.0.1:8877";
const PORT = Number(process.env.FUTURE_LOGIN_CPU_PORT || new URL(BASE).port || 8877);
const BROWSER = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const USERNAME = process.env.FUTURE_LOGIN_CPU_USERNAME || "quynh";
const PASSWORD = process.env.FUTURE_TEST_PASSWORD || "";
const PREFIX = process.env.FUTURE_LOGIN_CPU_PREFIX || "login_relogin_3_cycles_20260727";
const profileDir = path.join(os.tmpdir(), "future-login-relogin-3-cycles");

if (!PASSWORD) throw new Error("Set FUTURE_TEST_PASSWORD for the active test account.");

const nowIso = () => new Date().toISOString();
const clean = (value) => String(value || "").trim();
const sha256 = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");

const psJson = (script) => JSON.parse(childProcess.execFileSync("powershell.exe", ["-NoProfile", "-Command", script], {
  encoding: "utf8",
  windowsHide: true,
  timeout: 15000,
}).trim() || "{}");

const serverSnapshot = () => psJson(`
$conn = Get-NetTCPConnection -LocalPort ${PORT} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $conn) { [pscustomobject]@{pid=0; cpu_seconds=0.0; working_set=0} | ConvertTo-Json -Compress; exit }
$p = Get-Process -Id $conn.OwningProcess
[pscustomobject]@{pid=[int]$conn.OwningProcess; cpu_seconds=[double]$p.CPU; working_set=[int64]$p.WorkingSet64} | ConvertTo-Json -Compress
`);

const cleanupBrowsers = () => {
  const escaped = profileDir.replace(/'/g, "''");
  return psJson(`
$profile='${escaped}'
$targets=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -match 'chrome|browser|msedge') -and ($_.CommandLine -match [regex]::Escape($profile)) })
foreach ($p in $targets) { try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {} }
Start-Sleep -Milliseconds 300
$remaining=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -match 'chrome|browser|msedge') -and ($_.CommandLine -match [regex]::Escape($profile)) })
[pscustomobject]@{killed=$targets.Count; remaining=$remaining.Count} | ConvertTo-Json -Compress
`);
};

const sourceFiles = [
  "FUTURE/tools/probe_login_relogin_3_cycles.cjs",
  "FUTURE/tools/probe_login_cold_cpu_routes.cjs",
  "FUTURE/web/js_parts/05_screen_motion_layout.js",
  "FUTURE/web/js_parts/16_notices_vocabulary_missions.js",
  "FUTURE/web/js_parts/20_pdf_page_progress.js",
  "FUTURE/web/js_parts/21_progress_bootstrap_events.js",
  "FUTURE/web/future.js",
];

const endpointKey = (url, method = "GET") => {
  try { return `${method} ${new URL(url).pathname}`; } catch (_error) { return `${method} ${url}`; }
};

const summarizeRequests = (requests) => {
  const summary = {};
  for (const row of requests) {
    const key = endpointKey(row.url, row.method);
    summary[key] = summary[key] || { count: 0, total_ms: 0, max_ms: 0, statuses: {}, cache_hits: {} };
    summary[key].count += 1;
    summary[key].total_ms = Number((summary[key].total_ms + Number(row.ms || 0)).toFixed(3));
    summary[key].max_ms = Math.max(summary[key].max_ms, Number(row.ms || 0));
    summary[key].statuses[row.status || 0] = (summary[key].statuses[row.status || 0] || 0) + 1;
    if (row.cacheHit) summary[key].cache_hits[row.cacheHit] = (summary[key].cache_hits[row.cacheHit] || 0) + 1;
  }
  return summary;
};

const summarizeBrowserCache = (responses) => {
  const summary = {};
  for (const row of responses || []) {
    const key = endpointKey(row.url, row.method || "GET");
    summary[key] = summary[key] || { count: 0, disk_cache: 0, prefetch_cache: 0, service_worker: 0, network: 0 };
    summary[key].count += 1;
    if (row.fromDiskCache) summary[key].disk_cache += 1;
    else if (row.fromPrefetchCache) summary[key].prefetch_cache += 1;
    else if (row.fromServiceWorker) summary[key].service_worker += 1;
    else summary[key].network += 1;
  }
  return summary;
};

const setAuthInput = async (page, selector, value) => {
  await page.locator(selector).click({ force: true });
  await page.evaluate(({ selector: sel, value: val }) => {
    const el = document.querySelector(sel);
    if (!el) return;
    el.readOnly = false;
    el.value = val;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, { selector, value });
};

const runCycle = async (context, cycle) => {
  const page = await context.newPage();
  const requests = [];
  const cdpResponses = [];
  const starts = new Map();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  cdp.on("Network.responseReceived", (event) => {
    const response = event && event.response ? event.response : {};
    const url = clean(response.url || "");
    if (!url.startsWith(BASE)) return;
    cdpResponses.push({
      method: clean(event.type || "GET"),
      url,
      status: Number(response.status || 0),
      fromDiskCache: Boolean(response.fromDiskCache),
      fromPrefetchCache: Boolean(response.fromPrefetchCache),
      fromServiceWorker: Boolean(response.fromServiceWorker),
      protocol: clean(response.protocol || ""),
      encodedDataLength: Number(response.encodedDataLength || 0),
    });
  });
  page.on("request", (request) => starts.set(request, performance.now()));
  page.on("response", (response) => {
    if (!response.url().startsWith(BASE)) return;
    const started = starts.get(response.request()) || 0;
    requests.push({
      at_ms: Number(performance.now().toFixed(3)),
      method: response.request().method(),
      url: response.url(),
      status: response.status(),
      ms: started ? Number((performance.now() - started).toFixed(3)) : 0,
      cacheHit: response.headers()["x-future-cache-hit"] || "",
      serverTiming: response.headers()["server-timing"] || "",
      contentLength: Number(response.headers()["content-length"] || 0),
    });
  });
  const phases = [];
  let last = { ...serverSnapshot(), wall: Date.now() };
  const mark = (name) => {
    const next = serverSnapshot();
    phases.push({
      name,
      cpu_ms_delta: Number(((next.cpu_seconds - last.cpu_seconds) * 1000).toFixed(3)),
      wall_ms_delta: Date.now() - last.wall,
      request_count: requests.length,
    });
    last = { ...next, wall: Date.now() };
  };
  try {
    await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.evaluate(() => {
      try { localStorage.removeItem("future_lesson_auth_token"); } catch (_error) {}
      try { sessionStorage.clear(); } catch (_error) {}
      try { document.cookie = "future_lesson_auth_token=; Max-Age=0; path=/"; } catch (_error) {}
    });
    await page.waitForTimeout(1400);
    mark("login_visible_idle");
    await setAuthInput(page, "#ft-auth-user", USERNAME);
    await page.waitForTimeout(500);
    mark("username_typed");
    await setAuthInput(page, "#ft-auth-pass", PASSWORD);
    await page.waitForTimeout(500);
    mark("password_typed");
    await page.locator("#ft-auth-submit").click({ force: true });
    await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(5200);
    mark("post_submit_settled");
    const dom = await page.evaluate(() => ({
      authGateHidden: (() => {
        const node = document.querySelector("#ft-auth-gate");
        if (!node) return true;
        const style = getComputedStyle(node);
        return node.hidden || style.display === "none" || style.visibility === "hidden" || node.classList.contains("is-hidden");
      })(),
      authUser: document.querySelector("#ft-auth-user") ? document.querySelector("#ft-auth-user").value : "",
      loginBackdropServerBrowser: Boolean(document.querySelector(".is-login-vault-backdrop")),
      warmupStats: window.__futureLoginVaultWarmupStats || {},
      cacheStats: window.__futureLoginVaultTreePreloadCacheStats || {},
    }));
    return {
      cycle,
      phases,
      requests,
      request_summary: summarizeRequests(requests),
      browser_cache_summary: summarizeBrowserCache(cdpResponses),
      cdp_responses: cdpResponses,
      dom,
    };
  } finally {
    await cdp.detach().catch(() => {});
    await page.close().catch(() => {});
  }
};

const main = async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.rmSync(profileDir, { recursive: true, force: true });
  fs.mkdirSync(profileDir, { recursive: true });
  cleanupBrowsers();
  const context = await chromium.launchPersistentContext(profileDir, {
    executablePath: BROWSER,
    headless: true,
    viewport: { width: 1366, height: 820 },
    args: ["--disable-gpu", "--disable-extensions", "--disable-sync", "--disable-background-networking", "--mute-audio"],
  });
  try {
    const cycles = [];
    for (let cycle = 1; cycle <= 3; cycle += 1) {
      cycles.push(await runCycle(context, cycle));
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
    const raw = {
      schema: "login-relogin-3-cycles-v1",
      started_at_utc: nowIso(),
      base: BASE,
      username: USERNAME,
      source_hashes: Object.fromEntries(sourceFiles.map((rel) => {
        const file = path.join(ROOT, rel);
        return [rel, { exists: fs.existsSync(file), sha256: fs.existsSync(file) ? sha256(file) : "", bytes: fs.existsSync(file) ? fs.statSync(file).size : 0 }];
      })),
      cycles,
    };
    const rawPath = path.join(OUT_DIR, `${PREFIX}_raw.json`);
    fs.writeFileSync(rawPath, JSON.stringify(raw, null, 2), "utf8");
    console.log(JSON.stringify({
      ok: true,
      raw: rawPath,
      cycles: cycles.map((row) => ({
        cycle: row.cycle,
        phases: row.phases,
        top_endpoints: Object.entries(row.request_summary)
          .sort((a, b) => Number(b[1].total_ms || 0) - Number(a[1].total_ms || 0))
          .slice(0, 8)
          .map(([endpoint, value]) => ({ endpoint, count: value.count, total_ms: value.total_ms, cache_hits: value.cache_hits })),
        browser_cache: Object.fromEntries(Object.entries(row.browser_cache_summary || {})
          .filter(([endpoint]) => /future-assets\/future\.js|server-data\/(common-tree|user-overlay|login-preload)|lesson-tasks$/.test(endpoint))),
      })),
    }, null, 2));
  } finally {
    await context.close().catch(() => {});
    cleanupBrowsers();
  }
};

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
