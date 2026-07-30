const childProcess = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT_DIR = "C:\\Users\\Admin\\.codex\\plans\\server2_postgres_full_audit";
const BASE = process.env.FUTURE_LOGIN_CPU_BASE || "http://127.0.0.1:8877";
const BROWSER = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const USERNAME = process.env.FUTURE_LOGIN_CPU_USERNAME || "hung";
const PASSWORD = process.env.FUTURE_TEST_PASSWORD || "";
const PREFIX = process.env.FUTURE_LOGIN_CPU_PREFIX || "login_cold_cpu_routes_20260727";
const SERVER_LOG = "C:\\server data\\server_log\\future_whisper_stt_debug.log";
const profileDir = path.join(os.tmpdir(), "future-login-cold-cpu-routes");

if (!PASSWORD) {
  throw new Error("Set FUTURE_TEST_PASSWORD for the active test account.");
}

const nowIso = () => new Date().toISOString();
const clean = (value) => String(value || "").trim();
const sha256 = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");

const runPsJson = (script, timeout = 15000) => {
  const stdout = childProcess.execFileSync("powershell.exe", ["-NoProfile", "-Command", script], {
    encoding: "utf8",
    windowsHide: true,
    timeout,
  }).trim();
  return JSON.parse(stdout || "{}");
};

const serverProcessSnapshot = () => runPsJson(`
$conn = Get-NetTCPConnection -LocalPort 8877 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $conn) {
  [pscustomobject]@{ listening = $false; pid = 0; cpu_seconds = 0.0; working_set = 0; command = "" } | ConvertTo-Json -Compress
  exit
}
$p = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
$cmd = (Get-CimInstance Win32_Process -Filter ("ProcessId=" + $conn.OwningProcess) -ErrorAction SilentlyContinue).CommandLine
[pscustomobject]@{
  listening = $true
  pid = [int]$conn.OwningProcess
  cpu_seconds = [double]($p.CPU)
  working_set = [int64]($p.WorkingSet64)
  command = (($cmd -replace 'postgresql://[^\\s]+', 'postgresql://***REDACTED***') -replace 'password=[^\\s;]+', 'password=***')
} | ConvertTo-Json -Compress
`);

const browserProcessSnapshot = () => {
  const escapedProfile = profileDir.replace(/'/g, "''");
  return runPsJson(`
$profile = '${escapedProfile}'
$owned = @(Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'chrome|browser|msedge') -and ($_.CommandLine -match [regex]::Escape($profile))
})
[pscustomobject]@{ owned = $owned.Count } | ConvertTo-Json -Compress
`);
};

const cleanupBrowserProcesses = () => {
  const escapedProfile = profileDir.replace(/'/g, "''");
  return runPsJson(`
$profile = '${escapedProfile}'
$pattern = [regex]::Escape($profile)
$targets = @(Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'chrome|browser|msedge') -and ($_.CommandLine -match $pattern)
})
foreach ($p in $targets) {
  try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {}
}
Start-Sleep -Milliseconds 300
$remaining = @(Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'chrome|browser|msedge') -and ($_.CommandLine -match $pattern)
})
[pscustomobject]@{ killed = $targets.Count; remaining = $remaining.Count } | ConvertTo-Json -Compress
`);
};

const phaseRows = [];
let lastCpu = null;
const markPhase = (name, extra = {}) => {
  const snapshot = serverProcessSnapshot();
  const cpuMs = lastCpu ? Number(((snapshot.cpu_seconds - lastCpu.cpu_seconds) * 1000).toFixed(3)) : 0;
  const wallMs = lastCpu ? Date.now() - lastCpu.wall : 0;
  phaseRows.push({ name, at: nowIso(), cpu_ms_delta: cpuMs, wall_ms_delta: wallMs, snapshot, ...extra });
  lastCpu = { ...snapshot, wall: Date.now() };
};

const makeSummary = (requests) => {
  const byPath = {};
  for (const row of requests) {
    const pathname = (() => {
      try { return new URL(row.url).pathname; } catch (_error) { return row.url; }
    })();
    const key = `${row.method || "GET"} ${pathname}`;
    byPath[key] = byPath[key] || { count: 0, statuses: {}, total_ms: 0, max_ms: 0, cache_hits: {}, server_timing: [] };
    byPath[key].count += 1;
    byPath[key].statuses[row.status || 0] = (byPath[key].statuses[row.status || 0] || 0) + 1;
    byPath[key].total_ms = Number((byPath[key].total_ms + Number(row.ms || 0)).toFixed(3));
    byPath[key].max_ms = Math.max(byPath[key].max_ms, Number(row.ms || 0));
    if (row.cacheHit) byPath[key].cache_hits[row.cacheHit] = (byPath[key].cache_hits[row.cacheHit] || 0) + 1;
    if (row.serverTiming) byPath[key].server_timing.push(row.serverTiming);
  }
  return byPath;
};

const readNewLogLines = (offset) => {
  try {
    const stat = fs.statSync(SERVER_LOG);
    const start = Math.max(0, Math.min(Number(offset || 0), stat.size));
    const fd = fs.openSync(SERVER_LOG, "r");
    try {
      const length = Math.max(0, stat.size - start);
      const buffer = Buffer.alloc(Math.min(length, 2 * 1024 * 1024));
      fs.readSync(fd, buffer, 0, buffer.length, start);
      return buffer.toString("utf8").split(/\r?\n/).filter(Boolean).slice(-500);
    } finally {
      fs.closeSync(fd);
    }
  } catch (_error) {
    return [];
  }
};

const setAuthInput = async (page, selector, value) => {
  await page.locator(selector).click({ force: true });
  await page.waitForTimeout(80);
  await page.evaluate(({ selector: sel, value: val }) => {
    const el = document.querySelector(sel);
    if (!el) return;
    el.readOnly = false;
    el.value = val;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, { selector, value });
};

const main = async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.rmSync(profileDir, { recursive: true, force: true });
  fs.mkdirSync(profileDir, { recursive: true });
  cleanupBrowserProcesses();

  const sourceFiles = [
    "FUTURE/tools/probe_login_cold_cpu_routes.cjs",
    "FUTURE/web/js_parts/05_screen_motion_layout.js",
    "FUTURE/web/js_parts/20_pdf_page_progress.js",
    "FUTURE/web/js_parts/21_progress_bootstrap_events.js",
    "FUTURE/web/future.js",
    "FUTURE/server_parts/http_server/03_handler_get_routes.py",
    "FUTURE/server_parts/http_server/04_handler_post_routes.py",
  ];
  const sourceHashes = Object.fromEntries(sourceFiles.map((rel) => {
    const file = path.join(ROOT, rel);
    return [rel, { exists: fs.existsSync(file), sha256: fs.existsSync(file) ? sha256(file) : "", bytes: fs.existsSync(file) ? fs.statSync(file).size : 0 }];
  }));
  const logOffset = (() => {
    try { return fs.statSync(SERVER_LOG).size; } catch (_error) { return 0; }
  })();

  const requests = [];
  const consoleRows = [];
  const starts = new Map();
  const browserBefore = browserProcessSnapshot();
  const context = await chromium.launchPersistentContext(profileDir, {
    executablePath: BROWSER,
    headless: true,
    viewport: { width: 1366, height: 820 },
    args: ["--disable-gpu", "--disable-extensions", "--disable-sync", "--disable-background-networking", "--mute-audio"],
  });
  const page = await context.newPage();
  page.on("request", (request) => starts.set(request, performance.now()));
  page.on("console", (message) => {
    const text = clean(message.text());
    if (!text.includes("SPACE_V_PROGRESS_DEBUG")) return;
    consoleRows.push({
      type: message.type(),
      text,
    });
  });
  page.on("response", (response) => {
    const url = response.url();
    if (!url.startsWith(BASE)) return;
    const started = starts.get(response.request()) || 0;
    requests.push({
      at_ms: Number(performance.now().toFixed(3)),
      phase: phaseRows.length ? phaseRows[phaseRows.length - 1].name : "startup",
      method: response.request().method(),
      url,
      status: response.status(),
      ms: started ? Number((performance.now() - started).toFixed(3)) : 0,
      cacheHit: response.headers()["x-future-cache-hit"] || "",
      serverTiming: response.headers()["server-timing"] || "",
      contentLength: Number(response.headers()["content-length"] || 0),
    });
  });

  try {
    markPhase("server_warm_baseline");
    await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.evaluate(() => {
      try { localStorage.removeItem("future_lesson_auth_token"); } catch (_error) {}
      try { sessionStorage.clear(); } catch (_error) {}
      try { document.cookie = "future_lesson_auth_token=; Max-Age=0; path=/"; } catch (_error) {}
    });
    await page.waitForTimeout(1800);
    markPhase("login_page_visible_idle", { request_count: requests.length });

    await page.locator("#ft-auth-user").click({ force: true });
    await page.waitForTimeout(700);
    markPhase("username_focus_idle", { request_count: requests.length });

    await setAuthInput(page, "#ft-auth-user", USERNAME);
    await page.waitForTimeout(900);
    markPhase("username_typed_idle", { request_count: requests.length });

    await page.locator("#ft-auth-pass").click({ force: true });
    await page.waitForTimeout(700);
    markPhase("password_focus_idle", { request_count: requests.length });

    await setAuthInput(page, "#ft-auth-pass", PASSWORD);
    await page.waitForTimeout(700);
    markPhase("password_typed_idle", { request_count: requests.length });

    await page.locator("#ft-auth-submit").click({ force: true });
    await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(5500);
    markPhase("post_submit_settled", { request_count: requests.length });

    const dom = await page.evaluate(() => ({
      authGateHidden: (() => {
        const node = document.querySelector("#ft-auth-gate");
        if (!node) return true;
        const style = getComputedStyle(node);
        return node.hidden || style.display === "none" || style.visibility === "hidden" || node.classList.contains("is-hidden");
      })(),
      authUser: document.querySelector("#ft-auth-user") ? document.querySelector("#ft-auth-user").value : "",
      serverRows: document.querySelectorAll(".ft-server-row,.ft-server-entry,.server-data-row,[data-server-path]").length,
      loginBackdropServerBrowser: Boolean(document.querySelector(".is-login-vault-backdrop")),
      warmupStats: window.__futureLoginVaultWarmupStats || {},
      cacheStats: window.__futureLoginVaultTreePreloadCacheStats || {},
    }));

    const raw = {
      schema: "login-cold-cpu-routes-v1",
      started_at_utc: nowIso(),
      base: BASE,
      username: USERNAME,
      server_pid: phaseRows[0] && phaseRows[0].snapshot && phaseRows[0].snapshot.pid,
      browser_before: browserBefore,
      browser_after_open: browserProcessSnapshot(),
      source_hashes: sourceHashes,
      phase_rows: phaseRows,
      request_summary: makeSummary(requests),
      requests,
      dom,
      consoleRows,
      server_log: {
        path: SERVER_LOG,
        start_offset: logOffset,
        lines: readNewLogLines(logOffset),
      },
    };
    const rawPath = path.join(OUT_DIR, `${PREFIX}_raw.json`);
    fs.writeFileSync(rawPath, JSON.stringify(raw, null, 2), "utf8");
    console.log(JSON.stringify({ ok: true, raw: rawPath, phase_rows: phaseRows.map((row) => ({ name: row.name, cpu_ms_delta: row.cpu_ms_delta, wall_ms_delta: row.wall_ms_delta, request_count: row.request_count })), request_summary: raw.request_summary }, null, 2));
  } finally {
    await context.close().catch(() => {});
    cleanupBrowserProcesses();
  }
};

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
