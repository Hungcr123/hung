const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT_DIR = "C:\\Users\\Admin\\.codex\\plans\\server2_postgres_full_audit";
const BASE = process.env.FUTURE_BROWSER_CACHE_BASE || "http://127.0.0.1:18877";
const BROWSER = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\CocCoc\\Browser\\Application\\browser.exe";
const profileDir = path.join(os.tmpdir(), "future-common-overlay-browser-cache-timing");
const accounts = {
  hung: process.env.FUTURE_LOGIN_BENCH_PASSWORD_HUNG || "",
  quynh: process.env.FUTURE_LOGIN_BENCH_PASSWORD_QUYNH || "",
};

const nowIso = () => new Date().toISOString();
const sha256 = (file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
const clean = (value) => String(value || "").trim();
const args = Object.fromEntries(process.argv.slice(2).map((part) => {
  const [key, ...rest] = part.replace(/^--/, "").split("=");
  return [key, rest.join("=") || "1"];
}));
const warmupRounds = Number(args["warmup-rounds"] || 2);
const rounds = Number(args.rounds || 5);
const prefix = clean(args.prefix) || "checkpoint_007_browser_cache_timing_current";

if (!accounts.hung || !accounts.quynh) {
  throw new Error("Set FUTURE_LOGIN_BENCH_PASSWORD_HUNG and FUTURE_LOGIN_BENCH_PASSWORD_QUYNH for this browser timing probe");
}

const statKeys = [
  "indexedDbHits",
  "cacheStorageHits",
  "corruptRows",
  "removedRows",
  "writeFailures",
  "quotaFailures",
  "sessionStorageReadMs",
  "indexedDbReadMs",
  "cacheStorageReadMs",
  "jsonParseMs",
  "sessionStorageWriteMs",
  "indexedDbWriteMs",
  "cacheStorageWriteMs",
  "jsonStringifyMs",
];

const statsOf = (payload) => {
  const stats = payload && typeof payload === "object" ? payload : {};
  const out = {};
  for (const key of statKeys) out[key] = Number(stats[key] || 0);
  return out;
};

const deltaStats = (before, after) => {
  const out = {};
  for (const key of statKeys) out[key] = Number((Number(after[key] || 0) - Number(before[key] || 0)).toFixed(3));
  return out;
};

const percentile = (values, ratio) => {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.floor(sorted.length * ratio) - 1));
  return Number(sorted[index].toFixed(3));
};

const summarize = (rows, key) => {
  const values = rows.map((row) => Number(row[key] || 0));
  return {
    count: values.length,
    p50: percentile(values, 0.5),
    p95: percentile(values, 0.95),
    p99: percentile(values, 0.99),
    total: Number(values.reduce((sum, value) => sum + value, 0).toFixed(3)),
  };
};

const snapshotBrowserProcesses = () => {
  if (process.platform !== "win32") return { total: 0, owned: 0, profileDir: 0, harness: 0 };
  const escapedProfile = profileDir.replace(/'/g, "''");
  const script = `
$profile = '${escapedProfile}'
$procs = @(Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'chrome|browser|msedge') -and
  (
    $_.CommandLine -match [regex]::Escape($profile) -or
    $_.CommandLine -match 'future-common-overlay-browser-cache-timing'
  )
})
[pscustomobject]@{
  total = @(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'chrome|browser|msedge' })).Count
  owned = $procs.Count
  profileDir = @($procs | Where-Object { $_.CommandLine -match [regex]::Escape($profile) }).Count
  harness = @($procs | Where-Object { $_.CommandLine -match 'future-common-overlay-browser-cache-timing' }).Count
} | ConvertTo-Json -Compress
`;
  try {
    const stdout = require("child_process").execFileSync("powershell.exe", ["-NoProfile", "-Command", script], {
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
  ($_.CommandLine -match $pattern -or $_.CommandLine -match 'future-common-overlay-browser-cache-timing')
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
  ($_.CommandLine -match $pattern -or $_.CommandLine -match 'future-common-overlay-browser-cache-timing')
})
[pscustomobject]@{ killed = $targets.Count; remaining = $remaining.Count } | ConvertTo-Json -Compress
`;
  try {
    const stdout = require("child_process").execFileSync("powershell.exe", ["-NoProfile", "-Command", script], {
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
});

const clearAuth = async (page) => {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.evaluate(() => {
    try { localStorage.removeItem("future_lesson_auth_token"); } catch (_error) {}
    try { sessionStorage.clear(); } catch (_error) {}
    try { document.cookie = "future_lesson_auth_token=; Max-Age=0; path=/"; } catch (_error) {}
  });
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
};

const readStats = async (page) => statsOf(await page.evaluate(() => window.__futureLoginVaultTreePreloadCacheStats || {}));
const readWarmupStats = async (page) => await page.evaluate(() => window.__futureLoginVaultWarmupStats || {});

const loginAndMeasure = async (context, username, scenario) => {
  const page = await context.newPage();
  const errors = [];
  const requests = [];
  const requestStartedAt = new Map();
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") {
      const text = message.text();
      if (!/Failed to load resource/i.test(text) && !/ERR_CONNECTION_REFUSED/i.test(text)) {
        errors.push(`console:${text}`);
      }
    }
  });
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/auth/login") || url.includes("/server-data/login-preload") || url.includes("/server-data/common-tree") || url.includes("/server-data/user-overlay")) {
      requestStartedAt.set(request, performance.now());
    }
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/auth/login") || url.includes("/server-data/login-preload") || url.includes("/server-data/common-tree") || url.includes("/server-data/user-overlay")) {
      const startedAt = requestStartedAt.get(response.request()) || 0;
      requests.push({
        url,
        status: response.status(),
        ms: startedAt ? Number((performance.now() - startedAt).toFixed(3)) : 0,
      });
    }
  });
  await clearAuth(page);
  const before = await readStats(page);
  const started = performance.now();
  await page.locator("#ft-auth-user").click();
  await page.locator("#ft-auth-user").fill(username);
  await page.locator("#ft-auth-pass").click();
  await page.locator("#ft-auth-pass").fill(accounts[username]);
  await page.locator("#ft-auth-submit").click();
  await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 90000 });
  await page.waitForFunction(() => Boolean(localStorage.getItem("future_lesson_auth_token")), null, { timeout: 60000 });
  await page.waitForTimeout(700);
  const after = await readStats(page);
  const warmup = await readWarmupStats(page);
  const identity = await page.evaluate(async () => {
    const token = localStorage.getItem("future_lesson_auth_token") || "";
    const response = await fetch("/auth/me", { headers: { Authorization: `Bearer ${token}` } });
    return response.json();
  });
  await page.close();
  return {
    scenario,
    username,
    elapsedMs: Number((performance.now() - started).toFixed(3)),
    statDelta: deltaStats(before, after),
    finalStats: after,
    warmup,
    identity: clean(identity && identity.username).toLowerCase(),
    requests,
    errors,
  };
};

const main = async () => {
  fs.rmSync(profileDir, { recursive: true, force: true });
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.mkdirSync(profileDir, { recursive: true });
  fs.writeFileSync(path.join(profileDir, "codex-owned-profile.txt"), `probe_common_overlay_browser_cache_timing ${nowIso()}\n`, "utf8");
  const sourceFiles = [
    "FUTURE/web/js_parts/20_pdf_page_progress.js",
    "FUTURE/web/future.js",
    "FUTURE/tools/probe_common_overlay_browser_cache_timing.cjs",
  ];
  const sourceHashes = Object.fromEntries(sourceFiles.map((rel) => {
    const file = path.join(ROOT, rel);
    return [rel, { sha256: sha256(file), bytes: fs.statSync(file).size }];
  }));

  const browserBefore = snapshotBrowserProcesses();
  let context = await launch();
  const rows = [];
  try {
    for (let index = 0; index < warmupRounds; index += 1) {
      rows.push(await loginAndMeasure(context, index % 2 ? "quynh" : "hung", "warmup"));
    }
    for (let index = 0; index < rounds; index += 1) {
      rows.push(await loginAndMeasure(context, index % 2 ? "quynh" : "hung", "login_persistent_cache_warm"));
    }
    for (let index = 0; index < rounds; index += 1) {
      rows.push(await loginAndMeasure(context, index % 2 ? "quynh" : "hung", "tab_new"));
    }
    await context.close();
    context = await launch();
    for (let index = 0; index < rounds; index += 1) {
      rows.push(await loginAndMeasure(context, index % 2 ? "quynh" : "hung", "browser_reopen"));
    }
  } finally {
    await closeOwnedContext(context);
    cleanupBrowserProcesses();
    await new Promise((resolve) => setTimeout(resolve, 1000));
    cleanupBrowserProcesses();
  }
  const browserAfter = snapshotBrowserProcesses();

  const measured = rows.filter((row) => row.scenario !== "warmup");
  const errors = rows.flatMap((row) => row.errors).concat(
    rows.filter((row) => row.identity !== row.username).map((row) => `identity mismatch ${row.scenario}/${row.username}: ${row.identity}`),
  );
  const summaryByScenario = {};
  for (const scenario of [...new Set(measured.map((row) => row.scenario))]) {
    const scenarioRows = measured.filter((row) => row.scenario === scenario);
    summaryByScenario[scenario] = {
      elapsedMs: summarize(scenarioRows, "elapsedMs"),
      sessionStorageReadMs: summarize(scenarioRows.map((row) => row.statDelta), "sessionStorageReadMs"),
      indexedDbReadMs: summarize(scenarioRows.map((row) => row.statDelta), "indexedDbReadMs"),
      cacheStorageReadMs: summarize(scenarioRows.map((row) => row.statDelta), "cacheStorageReadMs"),
      jsonParseMs: summarize(scenarioRows.map((row) => row.statDelta), "jsonParseMs"),
      jsonStringifyMs: summarize(scenarioRows.map((row) => row.statDelta), "jsonStringifyMs"),
      indexedDbHits: summarize(scenarioRows.map((row) => row.statDelta), "indexedDbHits"),
      cacheStorageHits: summarize(scenarioRows.map((row) => row.statDelta), "cacheStorageHits"),
      loginPreloadMs: summarize(scenarioRows.flatMap((row) => row.requests.filter((req) => req.url.includes("/server-data/login-preload")).map((req) => ({ value: req.ms }))), "value"),
      commonTreeMs: summarize(scenarioRows.flatMap((row) => row.requests.filter((req) => req.url.includes("/server-data/common-tree")).map((req) => ({ value: req.ms }))), "value"),
      userOverlayMs: summarize(scenarioRows.flatMap((row) => row.requests.filter((req) => req.url.includes("/server-data/user-overlay")).map((req) => ({ value: req.ms }))), "value"),
      authLoginMs: summarize(scenarioRows.flatMap((row) => row.requests.filter((req) => req.url.includes("/auth/login")).map((req) => ({ value: req.ms }))), "value"),
      warmupFetchMs: summarize(scenarioRows.map((row) => ({ value: Number(row.warmup && row.warmup.fetchMs || 0) })), "value"),
      warmupRowSyncMs: summarize(scenarioRows.map((row) => ({ value: Number(row.warmup && row.warmup.rowSyncMs || 0) })), "value"),
      errors: scenarioRows.reduce((sum, row) => sum + row.errors.length, 0),
    };
  }

  const raw = {
    schema: "common-overlay-browser-cache-timing-v1",
    startedAtUtc: nowIso(),
    base: BASE,
    warmupRounds,
    measuredRounds: rounds,
    sourceHashes,
    profileDir,
    browserBefore,
    browserAfter,
    rows,
    summaryByScenario,
    errors,
  };
  const rawPath = path.join(OUT_DIR, `${prefix}_raw.json`);
  const summaryPath = path.join(OUT_DIR, `${prefix}_summary.md`);
  fs.writeFileSync(rawPath, JSON.stringify(raw, null, 2), "utf8");
  const lines = [
    `# ${prefix}`,
    "",
    `- schema: \`${raw.schema}\``,
    `- base: \`${BASE}\``,
    `- warmup_rounds: \`${warmupRounds}\``,
    `- measured_rounds: \`${rounds}\``,
    `- browser_before_owned: \`${browserBefore.owned ?? -1}\``,
    `- browser_after_owned: \`${browserAfter.owned ?? -1}\``,
    `- errors: \`${errors.length}\``,
    "",
    "| Scenario | Elapsed P95 ms | warmup-fetch P95 ms | warmup-row-sync P95 ms | login-preload P95 ms | common-tree P95 ms | user-overlay P95 ms | auth-login P95 ms | IDB read P95 ms | CacheStorage read P95 ms |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
  ];
  for (const [scenario, value] of Object.entries(summaryByScenario)) {
    lines.push(`| ${scenario} | ${value.elapsedMs.p95} | ${value.warmupFetchMs.p95} | ${value.warmupRowSyncMs.p95} | ${value.loginPreloadMs.p95} | ${value.commonTreeMs.p95} | ${value.userOverlayMs.p95} | ${value.authLoginMs.p95} | ${value.indexedDbReadMs.p95} | ${value.cacheStorageReadMs.p95} |`);
  }
  if (errors.length) {
    lines.push("", "## Errors", ...errors.map((error) => `- ${error}`));
  }
  fs.writeFileSync(summaryPath, `${lines.join("\n")}\n`, "utf8");
  console.log(JSON.stringify({ ok: errors.length === 0, raw: rawPath, summary: summaryPath, errors: errors.slice(0, 5) }));
  process.exitCode = errors.length === 0 ? 0 : 2;
};

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
