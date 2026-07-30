const crypto = require("crypto");
const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT_DIR = "C:\\Users\\Admin\\.codex\\plans\\server2_postgres_full_audit";
const BASE = process.env.FUTURE_LOGIN_TIMELINE_BASE || "http://127.0.0.1:18877";
const BROWSER = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\CocCoc\\Browser\\Application\\browser.exe";
const profileDir = path.join(os.tmpdir(), "future-login-end-to-end-timeline");
const accounts = {
  hung: process.env.FUTURE_LOGIN_BENCH_PASSWORD_HUNG || "",
  quynh: process.env.FUTURE_LOGIN_BENCH_PASSWORD_QUYNH || "",
};
const args = Object.fromEntries(process.argv.slice(2).map((part) => {
  const [key, ...rest] = part.replace(/^--/, "").split("=");
  return [key, rest.join("=") || "1"];
}));
const warmupRounds = Number(args["warmup-rounds"] || 5);
const rounds = Number(args.rounds || 30);
const flowTimeoutMs = Number(args["flow-timeout-ms"] || 45000);
const prefix = String(args.prefix || "checkpoint_login_end_to_end_timeline_20260727").trim();

if (!accounts.hung || !accounts.quynh) {
  throw new Error("Set FUTURE_LOGIN_BENCH_PASSWORD_HUNG and FUTURE_LOGIN_BENCH_PASSWORD_QUYNH");
}

const sourceFiles = [
  "FUTURE/tools/probe_login_end_to_end_timeline.cjs",
  "FUTURE/tools/probe_common_overlay_browser_cache_timing.cjs",
  "FUTURE/web/js_parts/20_pdf_page_progress.js",
  "FUTURE/web/js_parts/13_translation_vocab_sync.js",
  "FUTURE/web/js_parts/16_notices_vocabulary_missions.js",
  "FUTURE/web/future.js",
  "FUTURE/server_parts/http_server/03_handler_get_routes.py",
  "FUTURE/server_parts/http_server/04_handler_post_routes.py",
  "FUTURE/tools/run_server2_postgres_test_port.py",
];

const nowIso = () => new Date().toISOString();
const clean = (value) => String(value || "").trim();
const sha256 = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const percentile = (values, ratio) => {
  const nums = values.map(Number).filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  if (!nums.length) return 0;
  return Number(nums[Math.min(nums.length - 1, Math.max(0, Math.floor(nums.length * ratio) - 1))].toFixed(3));
};
const summarize = (values) => ({
  count: values.length,
  p50: percentile(values, 0.5),
  p95: percentile(values, 0.95),
  p99: percentile(values, 0.99),
  total: Number(values.reduce((sum, value) => sum + Number(value || 0), 0).toFixed(3)),
});

const snapshotBrowserProcesses = () => {
  if (process.platform !== "win32") return { total: 0, owned: 0, profileDir: 0, harness: 0 };
  const escapedProfile = profileDir.replace(/'/g, "''");
  const script = `
$profile = '${escapedProfile}'
$procs = @(Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'chrome|browser|msedge') -and
  (
    $_.CommandLine -match [regex]::Escape($profile) -or
    $_.CommandLine -match 'future-login-end-to-end-timeline' -or
    $_.CommandLine -match 'future-common-overlay-browser-cache-timing'
  )
})
[pscustomobject]@{
  total = @(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'chrome|browser|msedge' })).Count
  owned = $procs.Count
  profileDir = @($procs | Where-Object { $_.CommandLine -match [regex]::Escape($profile) }).Count
  harness = @($procs | Where-Object { $_.CommandLine -match 'future-login-end-to-end-timeline|future-common-overlay-browser-cache-timing' }).Count
} | ConvertTo-Json -Compress
`;
  try {
    const stdout = childProcess.execFileSync("powershell.exe", ["-NoProfile", "-Command", script], {
      encoding: "utf8",
      windowsHide: true,
      timeout: 15000,
    }).trim();
    return JSON.parse(stdout || "{}");
  } catch (_error) {
    return { total: -1, owned: -1, profileDir: -1, harness: -1 };
  }
};

const cleanupBrowserProcesses = () => {
  if (process.platform !== "win32") return { killed: 0, remaining: 0, error: "" };
  const escapedProfile = profileDir.replace(/'/g, "''");
  const script = `
$profile = '${escapedProfile}'
$pattern = [regex]::Escape($profile)
$seeds = @(Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'chrome|browser|msedge') -and
  ($_.CommandLine -match $pattern -or $_.CommandLine -match 'future-login-end-to-end-timeline') -and
  ($_.CommandLine -match '--headless|--remote-debugging-pipe|--enable-automation|--user-data-dir|--no-startup-window')
})
function Get-DescendantProcessIds([int]$rootPid) {
  $queue = New-Object System.Collections.Generic.Queue[int]
  $seen = New-Object 'System.Collections.Generic.HashSet[int]'
  $queue.Enqueue($rootPid)
  [void]$seen.Add($rootPid)
  while ($queue.Count -gt 0) {
    $current = $queue.Dequeue()
    foreach ($child in @(Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $current })) {
      if ($seen.Add([int]$child.ProcessId)) {
        $queue.Enqueue([int]$child.ProcessId)
      }
    }
  }
  return @($seen)
}
$targets = @()
foreach ($seed in $seeds) {
  foreach ($pid in @(Get-DescendantProcessIds ([int]$seed.ProcessId))) {
    $proc = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $pid) -ErrorAction SilentlyContinue
    if ($proc -and ($proc.Name -match 'chrome|browser|msedge')) {
      $targets += $proc
    }
  }
}
$targets = @($targets | Sort-Object ProcessId -Unique)
foreach ($p in $targets) {
  try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {}
}
Start-Sleep -Milliseconds 500
$remaining = @(Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'chrome|browser|msedge') -and
  ($_.CommandLine -match $pattern -or $_.CommandLine -match 'future-login-end-to-end-timeline') -and
  ($_.CommandLine -match '--headless|--remote-debugging-pipe|--enable-automation|--user-data-dir|--no-startup-window')
})
[pscustomobject]@{ killed = $targets.Count; remaining = $remaining.Count } | ConvertTo-Json -Compress
`;
  try {
    const stdout = childProcess.execFileSync("powershell.exe", ["-NoProfile", "-Command", script], {
      encoding: "utf8",
      windowsHide: true,
      timeout: 15000,
    }).trim();
    return JSON.parse(stdout || "{}");
  } catch (error) {
    return { killed: 0, remaining: -1, error: clean(error && error.message) };
  }
};

const closeOwnedContext = async (context) => {
  if (!context) return;
  const browser = typeof context.browser === "function" ? context.browser() : null;
  await context.close().catch(() => {});
  if (browser && typeof browser.close === "function") {
    await browser.close().catch(() => {});
  }
};

const launch = () => chromium.launchPersistentContext(profileDir, {
  executablePath: BROWSER,
  headless: true,
  viewport: { width: 1366, height: 820 },
  args: [
    "--disable-gpu",
    "--disable-extensions",
    "--disable-sync",
    "--disable-background-networking",
    "--mute-audio",
  ],
});

const getHealth = async (context) => {
  const page = await context.newPage();
  try {
    const payload = await page.evaluate(async (base) => {
      const response = await fetch(`${base}/health`, { cache: "no-store" });
      return response.json();
    }, BASE);
    return payload || {};
  } finally {
    await page.close().catch(() => {});
  }
};

const installTimeline = async (context) => {
  await context.addInitScript(() => {
    const events = [];
    const now = () => Number((performance.now()).toFixed(3));
    window.__ftTimelineEvents = events;
    window.__ftImportantFetchPending = 0;
    window.__ftImportantFetchLastAt = 0;
    window.__ftMark = (name, data = {}) => {
      events.push({ kind: "mark", name, t: now(), data });
      try { performance.mark(name); } catch (_error) {}
    };
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          events.push({ kind: "longtask", name: entry.name || "longtask", t: Number(entry.startTime.toFixed(3)), dur: Number(entry.duration.toFixed(3)) });
        }
      }).observe({ entryTypes: ["longtask"] });
    } catch (_error) {}
    const originalFetch = window.fetch;
    window.fetch = async (...fetchArgs) => {
      const url = String((fetchArgs[0] && fetchArgs[0].url) || fetchArgs[0] || "");
      const method = String((fetchArgs[1] && fetchArgs[1].method) || "GET").toUpperCase();
      const cid = window.__ftCorrelationId || "";
      const id = `${cid}:${events.length}:${Math.random().toString(16).slice(2)}`;
      const important = /\/auth\/login|\/auth\/me|\/server-data\/login-preload|\/server-data\/common-tree|\/server-data\/user-overlay/.test(url);
      if (important) {
        window.__ftImportantFetchPending += 1;
        window.__ftImportantFetchLastAt = performance.now();
        window.__ftMark("fetch_start", { id, cid, method, url });
      }
      try {
        const response = await originalFetch(...fetchArgs);
        if (important) {
          window.__ftImportantFetchLastAt = performance.now();
          window.__ftMark("fetch_headers", {
            id,
            cid,
            method,
            url,
            status: response.status,
            etag: response.headers.get("ETag") || "",
            cacheHit: response.headers.get("X-Future-Cache-Hit") || "",
            serverTiming: response.headers.get("Server-Timing") || "",
            contentLength: response.headers.get("Content-Length") || "",
          });
          response.clone().arrayBuffer()
            .then((buffer) => window.__ftMark("fetch_body_ready", { id, cid, url, bytes: buffer.byteLength }))
            .catch(() => {});
        }
        return response;
      } catch (error) {
        if (important) window.__ftMark("fetch_error", { id, cid, method, url, error: String(error && error.message || error) });
        throw error;
      } finally {
        if (important) {
          window.__ftImportantFetchPending = Math.max(0, window.__ftImportantFetchPending - 1);
          window.__ftImportantFetchLastAt = performance.now();
        }
      }
    };
  });
};

const clearAuth = async (page) => {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.evaluate(() => {
    try { localStorage.removeItem("future_lesson_auth_token"); } catch (_error) {}
    try { sessionStorage.clear(); } catch (_error) {}
    try { document.cookie = "future_lesson_auth_token=; Max-Age=0; path=/"; } catch (_error) {}
  });
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
};

const readRuntimeStats = async (page) => page.evaluate(() => ({
  cacheStats: { ...(window.__futureLoginVaultTreePreloadCacheStats || {}) },
  warmupStats: { ...(window.__futureLoginVaultWarmupStats || {}) },
  timelineMetrics: { ...(window.__ftLoginTimelineMetrics || {}) },
  taskMetrics: typeof window.__ftSpaceTaskMetricsSnapshot === "function" ? window.__ftSpaceTaskMetricsSnapshot() : {},
  dom: {
    title: document.title,
    authGateHidden: (() => {
      const gate = document.querySelector("#ft-auth-gate");
      if (!gate) return true;
      const style = window.getComputedStyle(gate);
      return style.display === "none" || style.visibility === "hidden" || gate.hidden;
    })(),
    serverRows: document.querySelectorAll(".ft-server-row,.ft-server-entry,.server-data-row,[data-server-path]").length,
    serverListChildren: (() => {
      const list = document.querySelector("#ft-server-list,#server-data-list,.ft-server-list,.server-data-list");
      return list ? list.children.length : 0;
    })(),
    bodyTextLength: document.body ? document.body.innerText.length : 0,
  },
  events: Array.isArray(window.__ftTimelineEvents) ? window.__ftTimelineEvents.slice() : [],
  pendingFetches: Number(window.__ftImportantFetchPending || 0),
}));

const loginFlow = async (context, username, scenario, measured) => {
  const page = await context.newPage();
  const cid = `${scenario}-${username}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const errors = [];
  const requests = [];
  const requestStartedAt = new Map();
  let started = performance.now();
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error" && !/Failed to load resource/i.test(message.text())) {
      errors.push(`console:${message.text()}`);
    }
  });
  page.on("request", (request) => {
    const url = request.url();
    if (/\/auth\/login|\/auth\/me|\/server-data\/login-preload|\/server-data\/common-tree|\/server-data\/user-overlay|\/space-v\/progress/.test(url)) {
      requestStartedAt.set(request, performance.now());
    }
  });
  page.on("response", async (response) => {
    const url = response.url();
    if (/\/auth\/login|\/auth\/me|\/server-data\/login-preload|\/server-data\/common-tree|\/server-data\/user-overlay|\/space-v\/progress/.test(url)) {
      const startedAt = requestStartedAt.get(response.request()) || 0;
      requests.push({
        url,
        method: response.request().method(),
        status: response.status(),
        ms: startedAt ? Number((performance.now() - startedAt).toFixed(3)) : 0,
        serverTiming: response.headers()["server-timing"] || "",
        cacheHit: response.headers()["x-future-cache-hit"] || "",
        etag: response.headers()["etag"] || "",
        contentLength: Number(response.headers()["content-length"] || 0),
      });
    }
  });
  try {
    await clearAuth(page);
    await page.evaluate((nextCid) => {
      window.__ftCorrelationId = nextCid;
      window.__ftMark && window.__ftMark("login_handler_ready", { cid: nextCid });
    }, cid);
    started = performance.now();
    await page.locator("#ft-auth-user").click();
    await page.locator("#ft-auth-user").fill(username);
    await page.locator("#ft-auth-pass").click();
    await page.locator("#ft-auth-pass").fill(accounts[username]);
    await page.evaluate(() => window.__ftMark && window.__ftMark("login_click"));
    await page.locator("#ft-auth-submit").click();
    await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: flowTimeoutMs });
    await page.evaluate(() => window.__ftMark && window.__ftMark("auth_gate_hidden"));
    await page.waitForFunction(() => Boolean(localStorage.getItem("future_lesson_auth_token")), null, { timeout: flowTimeoutMs });
    await page.evaluate(() => window.__ftMark && window.__ftMark("session_installed"));
    await page.waitForFunction(() => {
      const events = Array.isArray(window.__ftTimelineEvents) ? window.__ftTimelineEvents : [];
      return events.some((event) => event.name === "fetch_start" && /\/server-data\/(login-preload|common-tree|user-overlay)/.test(String(event.data && event.data.url || "")));
    }, null, { timeout: 5000 }).catch(() => {});
    await page.waitForFunction(() => {
      const pending = Number(window.__ftImportantFetchPending || 0);
      const lastAt = Number(window.__ftImportantFetchLastAt || 0);
      return pending === 0 && (!lastAt || performance.now() - lastAt >= 150);
    }, null, { timeout: flowTimeoutMs }).catch(() => {});
    await page.evaluate(() => window.__ftMark && window.__ftMark("network_idle_probe"));
    await page.evaluate(() => window.__ftMark && window.__ftMark("vault_usable_probe"));
    await page.waitForTimeout(50);
    const runtime = await readRuntimeStats(page);
    const elapsedMs = Number((performance.now() - started).toFixed(3));
    const identity = await page.evaluate(async () => {
      const token = localStorage.getItem("future_lesson_auth_token") || "";
      const response = await fetch("/auth/me", { headers: { Authorization: `Bearer ${token}` } });
      return response.json();
    }).catch(() => ({}));
    return { cid, scenario, measured, username, identity: clean(identity && identity.username).toLowerCase(), elapsedMs, requests, runtime, errors };
  } catch (error) {
    errors.push(`flow:${clean(error && error.message) || String(error)}`);
    let runtime = { cacheStats: {}, warmupStats: {}, taskMetrics: {}, dom: {}, events: [], pendingFetches: 0 };
    try {
      await page.evaluate((message) => window.__ftMark && window.__ftMark("flow_error", { message }), errors[errors.length - 1]);
      runtime = await readRuntimeStats(page);
    } catch (_readError) {
    }
    return {
      cid,
      scenario,
      measured,
      username,
      identity: "",
      elapsedMs: Number((performance.now() - started).toFixed(3)),
      requests,
      runtime,
      errors,
      failed: true,
    };
  } finally {
    await page.close().catch(() => {});
  }
};

const phaseFromEvents = (row) => {
  const events = row.runtime.events || [];
  const first = events.find((event) => event.name === "login_click");
  const last = events.find((event) => event.name === "vault_usable_probe");
  const total = row.elapsedMs;
  const requests = row.requests || [];
  const sumReq = (pattern) => requests.filter((req) => pattern.test(req.url)).reduce((sum, req) => sum + Number(req.ms || 0), 0);
  const cache = row.runtime.cacheStats || {};
  const warmup = row.runtime.warmupStats || {};
  const longTasks = events.filter((event) => event.kind === "longtask").reduce((sum, event) => sum + Number(event.dur || 0), 0);
  const serverKnown = sumReq(/\/auth\/login/) + sumReq(/\/server-data\/login-preload/) + sumReq(/\/server-data\/common-tree/) + sumReq(/\/server-data\/user-overlay/);
  const browserKnown = Number(cache.indexedDbReadMs || 0) + Number(cache.cacheStorageReadMs || 0) + Number(cache.sessionStorageReadMs || 0) + Number(cache.jsonParseMs || 0) + Number(warmup.rowSyncMs || 0);
  return {
    total,
    authServer: sumReq(/\/auth\/login/),
    loginPreload: sumReq(/\/server-data\/login-preload/),
    commonTree: sumReq(/\/server-data\/common-tree/),
    userOverlay: sumReq(/\/server-data\/user-overlay/),
    indexedDbCacheRead: Number(cache.indexedDbReadMs || 0) + Number(cache.cacheStorageReadMs || 0) + Number(cache.sessionStorageReadMs || 0),
    jsonParse: Number(cache.jsonParseMs || 0),
    warmupFetch: Number(warmup.fetchMs || 0),
    warmupRowSync: Number(warmup.rowSyncMs || 0),
    longTasks,
    unattributed: Math.max(0, total - serverKnown - browserKnown - longTasks),
    eventWindow: first && last ? Number((last.t - first.t).toFixed(3)) : total,
  };
};

const main = async () => {
  const cleanupBefore = cleanupBrowserProcesses();
  const browserBefore = snapshotBrowserProcesses();
  fs.rmSync(profileDir, { recursive: true, force: true });
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.mkdirSync(profileDir, { recursive: true });
  fs.writeFileSync(path.join(profileDir, "codex-owned-profile.txt"), `probe_login_end_to_end_timeline ${nowIso()}\n`, "utf8");
  const sourceHashes = Object.fromEntries(sourceFiles.map((rel) => {
    const file = path.join(ROOT, rel);
    return [rel, { exists: fs.existsSync(file), sha256: fs.existsSync(file) ? sha256(file) : "", bytes: fs.existsSync(file) ? fs.statSync(file).size : 0 }];
  }));
  let context = null;
  let beforeHealth = {};
  const rows = [];
  let afterHealth = {};
  let cleanupAfter = { killed: 0, remaining: 0, error: "" };
  try {
    context = await launch();
    await installTimeline(context);
    beforeHealth = await getHealth(context);
    for (let i = 0; i < warmupRounds; i += 1) {
      rows.push(await loginFlow(context, i % 2 ? "quynh" : "hung", "warmup", false));
    }
    for (const scenario of ["login_persistent_cache_warm", "tab_new", "user_switch"]) {
      for (let i = 0; i < rounds; i += 1) {
        rows.push(await loginFlow(context, i % 2 ? "quynh" : "hung", scenario, true));
      }
    }
    await closeOwnedContext(context);
    context = null;
    context = await launch();
    await installTimeline(context);
    for (let i = 0; i < rounds; i += 1) {
      rows.push(await loginFlow(context, i % 2 ? "quynh" : "hung", "browser_reopen", true));
    }
  } finally {
    if (context) await closeOwnedContext(context);
    cleanupAfter = cleanupBrowserProcesses();
    await new Promise((resolve) => setTimeout(resolve, 1000));
    cleanupAfter = cleanupBrowserProcesses();
  }
  const browserAfter = snapshotBrowserProcesses();
  const verifyContext = await launch();
  afterHealth = await getHealth(verifyContext);
  await closeOwnedContext(verifyContext);
  const cleanupFinal = cleanupBrowserProcesses();
  const browserFinal = snapshotBrowserProcesses();
  const measured = rows.filter((row) => row.measured);
  const phases = measured.map((row) => ({ ...phaseFromEvents(row), scenario: row.scenario, username: row.username, cid: row.cid }));
  const scenarios = [...new Set(measured.map((row) => row.scenario))];
  const summaryByScenario = {};
  for (const scenario of scenarios) {
    const scenarioRows = measured.filter((row) => row.scenario === scenario);
    const scenarioPhases = phases.filter((row) => row.scenario === scenario);
    summaryByScenario[scenario] = {
      elapsedMs: summarize(scenarioRows.map((row) => row.elapsedMs)),
      authServer: summarize(scenarioPhases.map((row) => row.authServer)),
      loginPreload: summarize(scenarioPhases.map((row) => row.loginPreload)),
      commonTree: summarize(scenarioPhases.map((row) => row.commonTree)),
      userOverlay: summarize(scenarioPhases.map((row) => row.userOverlay)),
      cacheRead: summarize(scenarioPhases.map((row) => row.indexedDbCacheRead)),
      jsonParse: summarize(scenarioPhases.map((row) => row.jsonParse)),
      warmupFetch: summarize(scenarioPhases.map((row) => row.warmupFetch)),
      warmupRowSync: summarize(scenarioPhases.map((row) => row.warmupRowSync)),
      longTasks: summarize(scenarioPhases.map((row) => row.longTasks)),
      unattributed: summarize(scenarioPhases.map((row) => row.unattributed)),
      requests: scenarioRows.reduce((sum, row) => sum + row.requests.length, 0),
      errors: scenarioRows.reduce((sum, row) => sum + row.errors.length + (row.identity !== row.username ? 1 : 0), 0),
    };
  }
  const cpuBefore = Number(beforeHealth && beforeHealth.postgres ? beforeHealth.postgres.sql_execute : 0);
  const cpuAfter = Number(afterHealth && afterHealth.postgres ? afterHealth.postgres.sql_execute : 0);
  const raw = {
    schema: "login-end-to-end-timeline-v1",
    workload: "browser-login-common-overlay-etag-v1",
    startedAtUtc: nowIso(),
    base: BASE,
    profileDir,
    browserBefore,
    warmupRounds,
    measuredRounds: rounds,
    sourceHashes,
    cleanupBefore,
    cleanupAfter,
    cleanupFinal,
    browserAfter,
    browserFinal,
    beforeHealth: {
      pid: beforeHealth.pid,
      sqlite_writer: beforeHealth.sqlite_writer,
      postgres: beforeHealth.postgres,
      tunnel_status: beforeHealth.tunnel_status,
    },
    afterHealth: {
      pid: afterHealth.pid,
      sqlite_writer: afterHealth.sqlite_writer,
      postgres: afterHealth.postgres,
      tunnel_status: afterHealth.tunnel_status,
    },
    postgresDelta: {
      sql_execute: Number((afterHealth.postgres && afterHealth.postgres.sql_execute) || 0) - Number((beforeHealth.postgres && beforeHealth.postgres.sql_execute) || 0),
      transactions: Number((afterHealth.postgres && afterHealth.postgres.transactions) || 0) - Number((beforeHealth.postgres && beforeHealth.postgres.transactions) || 0),
      pool_wait_ms_total: Number(((afterHealth.postgres && afterHealth.postgres.pool_wait_ms_total) || 0) - ((beforeHealth.postgres && beforeHealth.postgres.pool_wait_ms_total) || 0)).toFixed(3),
    },
    rows,
    phases,
    summaryByScenario,
    errors: rows.flatMap((row) => row.errors).concat(rows.filter((row) => row.measured && row.identity !== row.username).map((row) => `identity mismatch ${row.cid}: ${row.identity}`)),
    cpuProxyNote: "Server process CPU is not sampled in this browser harness yet; use API harness for CPU/request and this harness for browser phase attribution.",
  };
  const rawPath = path.join(OUT_DIR, `${prefix}_raw.json`);
  const summaryPath = path.join(OUT_DIR, `${prefix}_summary.md`);
  fs.writeFileSync(rawPath, JSON.stringify(raw, null, 2), "utf8");
  const lines = [
    `# ${prefix}`,
    "",
    `- schema: \`${raw.schema}\``,
    `- workload: \`${raw.workload}\``,
    `- base: \`${BASE}\``,
    `- server_pid: \`${beforeHealth.pid}\``,
    `- postgres_only: \`${Boolean(beforeHealth.sqlite_writer && beforeHealth.sqlite_writer.postgres_only)}\``,
    `- browser_before_owned: \`${browserBefore.owned ?? -1}\``,
    `- browser_after_owned: \`${browserAfter.owned ?? -1}\``,
    `- browser_final_owned: \`${browserFinal.owned ?? -1}\``,
    `- warmup_rounds: \`${warmupRounds}\``,
    `- measured_rounds: \`${rounds}\``,
    `- flow_timeout_ms: \`${flowTimeoutMs}\``,
    `- cleanup_before_killed: \`${cleanupBefore.killed || 0}\``,
    `- cleanup_after_killed: \`${cleanupAfter.killed || 0}\``,
    `- cleanup_final_remaining: \`${cleanupFinal.remaining ?? -1}\``,
    `- errors: \`${raw.errors.length}\``,
    `- pg_sql_execute_delta: \`${raw.postgresDelta.sql_execute}\``,
    `- pg_transactions_delta: \`${raw.postgresDelta.transactions}\``,
    `- decision: \`INSUFFICIENT EVIDENCE\``,
    "",
    "| Scenario | Total P95 | Auth P95 | Preload P95 | Common P95 | Overlay P95 | Cache read P95 | JSON parse P95 | Warm fetch P95 | Row sync P95 | Long tasks P95 | Unattributed P95 | Errors |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
  ];
  for (const [scenario, item] of Object.entries(summaryByScenario)) {
    lines.push(`| ${scenario} | ${item.elapsedMs.p95} | ${item.authServer.p95} | ${item.loginPreload.p95} | ${item.commonTree.p95} | ${item.userOverlay.p95} | ${item.cacheRead.p95} | ${item.jsonParse.p95} | ${item.warmupFetch.p95} | ${item.warmupRowSync.p95} | ${item.longTasks.p95} | ${item.unattributed.p95} | ${item.errors} |`);
  }
  lines.push("", "## Notes", "- This harness does not modify production runtime code.", "- Unattributed remains a blocker if it is above 5% of total P95.", "- Server CPU/request evidence remains in the API harness until per-flow process CPU sampling is added here.");
  fs.writeFileSync(summaryPath, `${lines.join("\n")}\n`, "utf8");
  console.log(JSON.stringify({ ok: raw.errors.length === 0, raw: rawPath, summary: summaryPath, errors: raw.errors.slice(0, 5) }));
  process.exitCode = raw.errors.length ? 2 : 0;
};

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
