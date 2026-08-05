"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const sourcePath = path.join(__dirname, "..", "web", "js_parts", "19_pdf_speak_chrome.js");
const sourceText = fs.readFileSync(sourcePath, "utf8");
assert.match(
  sourceText,
  /fetchAuthBlob\(`\/pdf\/file\?\$\{query\.toString\(\)\}`,[\s\S]{0,500}?progressTransport:\s*["']xhr["']/,
  "PDF source Range requests must use XHR so Gate 1 receives real network byte progress",
);

const upstreamBase = process.env.FUTURE_GATE_DOM_BASE || "http://127.0.0.1:8877";
const browserPath = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const state = {
  totalBytes: 0,
  slowMs: 0,
  noLength: false,
  failChunkOnce: 0,
  failed: false,
  requests: [],
};

const readRange = (value, total) => {
  const match = /^bytes=(\d+)-(\d+)$/.exec(value || "");
  if (!match) return { start: 0, end: Math.max(0, total - 1) };
  return { start: Number(match[1]), end: Math.min(total - 1, Number(match[2])) };
};

const serveProbePdf = (req, res, url) => {
  const range = readRange(req.headers.range, state.totalBytes);
  const chunkIndex = Number(url.searchParams.get("chunk_index") || 0) || 0;
  const attempt = Number(url.searchParams.get("attempt") || 1) || 1;
  const row = { at: Date.now(), chunkIndex, attempt, start: range.start, end: range.end };
  state.requests.push(row);
  if (state.failChunkOnce === chunkIndex && !state.failed && attempt === 1) {
    state.failed = true;
    res.writeHead(503, { "Content-Type": "application/json", "Content-Length": "20" });
    res.end(JSON.stringify({ error: "probe retry" }));
    return;
  }
  const length = Math.max(0, range.end - range.start + 1);
  const headers = {
    "Content-Type": "application/pdf",
    "Content-Range": `bytes ${range.start}-${range.end}/${state.totalBytes}`,
    "Accept-Ranges": "bytes",
    "Cache-Control": "no-store",
  };
  if (!state.noLength) headers["Content-Length"] = String(length);
  res.writeHead(206, headers);
  let sent = 0;
  const send = () => {
    if (sent >= length) {
      res.end();
      row.completedAt = Date.now();
      row.bytes = length;
      return;
    }
    const size = Math.min(64 * 1024, length - sent);
    const body = Buffer.alloc(size, (range.start + sent) % 251);
    sent += size;
    res.write(body);
    if (state.slowMs > 0) setTimeout(send, state.slowMs);
    else setImmediate(send);
  };
  send();
};

const proxyRequest = (req, res, targetUrl) => {
  const target = new URL(targetUrl, upstreamBase);
  const upstream = http.request({
    hostname: target.hostname,
    port: target.port,
    path: `${target.pathname}${target.search}`,
    method: req.method,
    headers: { ...req.headers, host: target.host },
  }, (response) => {
    res.writeHead(response.statusCode || 502, response.headers);
    response.pipe(res);
  });
  upstream.on("error", (error) => {
    res.writeHead(502, { "Content-Type": "text/plain" });
    res.end(String(error.message || error));
  });
  req.pipe(upstream);
};

(async () => {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    if (url.pathname === "/__probe_pdf_config") {
      state.totalBytes = Number(url.searchParams.get("bytes") || 0) || 0;
      state.slowMs = Number(url.searchParams.get("slow") || 0) || 0;
      state.noLength = url.searchParams.get("no_length") === "1";
      state.failChunkOnce = Number(url.searchParams.get("fail_chunk") || 0) || 0;
      state.failed = false;
      state.requests = [];
      res.writeHead(204);
      res.end();
      return;
    }
    if (url.pathname === "/pdf/file") {
      serveProbePdf(req, res, url);
      return;
    }
    proxyRequest(req, res, `${upstreamBase}${req.url}`);
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const base = `http://127.0.0.1:${port}`;
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() !== "error") return;
      const value = message.text();
      if (state.failChunkOnce && value.includes("Failed to load resource")) return;
      errors.push(value);
    });
    await page.goto(`${base}/login?ft_gate_probe=1`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(() => Boolean(window.__ftLessonEntryGateProbe), null, { timeout: 30000 });
    const clearCache = async (key) => page.evaluate(async (value) => {
      const deletedCaches = [];
      for (const name of await caches.keys()) {
        if (!/future-space-pdf-(files|pages)/i.test(name)) continue;
        if (await caches.delete(name)) deletedCaches.push(name);
      }
      const deletedDatabases = [];
      if (indexedDB && typeof indexedDB.databases === "function") {
        const databases = await indexedDB.databases();
        for (const row of databases) {
          const name = String(row && row.name || "");
          if (!/future.*pdf|pdf.*future/i.test(name)) continue;
          await new Promise((resolve, reject) => {
            const request = indexedDB.deleteDatabase(name);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error || new Error(`Could not delete ${name}`));
            request.onblocked = () => reject(new Error(`IndexedDB deletion blocked: ${name}`));
          });
          deletedDatabases.push(name);
        }
      }
      window.__ftPdfSourceNetworkTrace = [];
      const remainingCaches = (await caches.keys()).filter((name) => /future-space-pdf-(files|pages)/i.test(name));
      const remainingDatabases = indexedDB && typeof indexedDB.databases === "function"
        ? (await indexedDB.databases()).map((row) => String(row && row.name || "")).filter((name) => /future.*pdf|pdf.*future/i.test(name))
        : [];
      return { key: value, deletedCaches, deletedDatabases, remainingCaches, remainingDatabases };
    }, key);
    const configure = async (bytes, options = {}) => {
      await page.evaluate(async (url) => {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) throw new Error(`probe config failed: ${response.status}`);
      }, `${base}/__probe_pdf_config?bytes=${bytes}&slow=${options.slow || 0}&no_length=${options.noLength ? 1 : 0}&fail_chunk=${options.failChunk || 0}`);
      await page.goto(`${base}/login?ft_gate_probe=1`, { waitUntil: "domcontentloaded", timeout: 60000 });
      await page.waitForFunction(() => Boolean(window.__ftLessonEntryGateProbe), null, { timeout: 30000 });
    };
    const download = (bytes, key) => page.evaluate(({ value, cacheKey }) => window.__ftLessonEntryGateProbe.pdfSourceDownload({ bytes: value, key: cacheKey }), { value: bytes, cacheKey: key });

    const normalBytes = 5 * 1024 * 1024 + 123;
    const normalKey = "runtime-normal-20260803";
    await configure(normalBytes, { slow: 5 });
    await clearCache(normalKey);
    const recoveryToken = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Space_PDF lost progress state"));
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    const recovered = await page.evaluate(() => window.__ftLessonEntryGateProbe.recoverPdfProgressState(37));
    assert.equal(recovered, true, "visible Gate 1 rejected a real PDF source progress event after state loss");
    await page.waitForFunction(() => document.querySelector("#ft-entry-pdf-stream-percent")?.textContent === "37%", null, { timeout: 3000 });
    const recoveryHud = await page.evaluate(() => ({
      active: Boolean(window.__ftLessonEntryPdfProgressActive?.()),
      hidden: Boolean(document.querySelector("#ft-entry-pdf-stream")?.hidden),
      percent: document.querySelector("#ft-entry-pdf-stream-percent")?.textContent || "",
      chunk: document.querySelector("#ft-entry-pdf-stream-chunk")?.textContent || "",
    }));
    assert.deepEqual(recoveryHud, { active: true, hidden: false, percent: "37%", chunk: "CHUNK 1/15 · 37%" });
    await page.evaluate((token) => window.__ftLessonEntryGateProbe.cancel(token, "state recovery probe complete"), recoveryToken);
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 5000 });

    const backgroundKey = "runtime-background-single-flight-20260803";
    await configure(normalBytes, { slow: 5 });
    await clearCache(backgroundKey);
    const backgroundToken = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Space_PDF background single-flight"));
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    await page.evaluate(() => window.__ftLessonEntryGateProbe.previewPdfProgress(0));
    await page.evaluate(({ bytes, key }) => {
      window.__ftBackgroundPdfProbeDone = false;
      window.__ftBackgroundPdfProbeResult = null;
      window.__ftLessonEntryGateProbe.pdfSourceDownload({ bytes, key, trackProgress: false }).then((result) => {
        window.__ftBackgroundPdfProbeResult = result;
        window.__ftBackgroundPdfProbeDone = true;
      });
    }, { bytes: normalBytes, key: backgroundKey });
    await page.waitForFunction(() => {
      const text = document.querySelector("#ft-entry-pdf-stream-percent")?.textContent || "";
      return /^\d+%$/.test(text) && text !== "0%" && text !== "100%";
    }, null, { timeout: 10000 });
    const backgroundHud = await page.evaluate(() => ({
      percent: document.querySelector("#ft-entry-pdf-stream-percent")?.textContent || "",
      chunk: document.querySelector("#ft-entry-pdf-stream-chunk")?.textContent || "",
    }));
    assert.match(backgroundHud.chunk, /CHUNK 1\//, "background single-flight did not route chunk 1 into Gate 1");
    await page.waitForFunction(() => window.__ftBackgroundPdfProbeDone === true, null, { timeout: 30000 });
    await page.evaluate((token) => window.__ftLessonEntryGateProbe.cancel(token, "background single-flight probe complete"), backgroundToken);
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 5000 });

    const gateKey = "runtime-gate-uncached-20260803";
    const gateColdReset = await clearCache(gateKey);
    assert.deepEqual(gateColdReset.remainingCaches, [], "PDF Cache Storage was not empty before the cold Gate DOM test");
    assert.deepEqual(gateColdReset.remainingDatabases, [], "PDF IndexedDB was not empty before the cold Gate DOM test");
    const gateToken = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Space_PDF uncached DOM network"));
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    await page.evaluate(({ token, bytes, key }) => window.__ftLessonEntryGateProbe.armMediaDecision(token, 7, { bytes, key }), { token: gateToken, bytes: normalBytes, key: gateKey });
    const gateSamples = [];
    const gateStartedAt = Date.now();
    while (Date.now() - gateStartedAt < 30000) {
      gateSamples.push(await page.evaluate(() => ({
        hidden: Boolean(document.querySelector("#ft-entry-pdf-stream")?.hidden),
        percent: document.querySelector("#ft-entry-pdf-stream-percent")?.textContent || "",
        graph: document.querySelector("#ft-entry-pdf-stream-graph")?.style.getPropertyValue("--ft-entry-pdf-progress") || "",
        chunk: document.querySelector("#ft-entry-pdf-stream-chunk")?.textContent || "",
        byteText: document.querySelector("#ft-entry-pdf-stream-bytes")?.textContent || "",
        bytes: Number(window.__ftLessonEntryMediaProbe?.bytes || 0) || 0,
      })));
      if (gateSamples.at(-1).bytes === normalBytes) break;
      await page.waitForTimeout(50);
    }
    const visibleGateSamples = gateSamples.filter((sample) => !sample.hidden);
    const gatePercentSeries = [...new Set(visibleGateSamples.map((sample) => sample.percent).filter((value) => /^\d+%$/.test(value)))];
    const chunkOneByteSeries = [...new Set(visibleGateSamples
      .filter((sample) => sample.chunk.includes("CHUNK 1/"))
      .map((sample) => sample.byteText)
      .filter((value) => value && !value.startsWith("0 B /")))];
    assert(visibleGateSamples.length >= 3, "uncached PDF Gate HUD did not become visible during source download");
    assert(visibleGateSamples.some((sample) => /^\d+%$/.test(sample.percent) && sample.percent !== "0%"), "uncached PDF Gate HUD stayed at its initial value");
    assert(gatePercentSeries.length >= 5, `uncached PDF Gate HUD emitted too few visible percentages: ${gatePercentSeries.join(", ")}`);
    assert(visibleGateSamples.some((sample) => sample.chunk.includes("CHUNK 1/")), "uncached PDF Gate HUD did not expose chunk 1");
    assert(chunkOneByteSeries.length >= 4, `uncached Gate DOM exposed too few chunk-1 KB updates: ${chunkOneByteSeries.join(", ")}`);
    assert(chunkOneByteSeries.some((value) => /KB|MB/.test(value)), "uncached Gate DOM never displayed real downloaded KB/MB");
    assert(gateSamples.at(-1).bytes === normalBytes, "uncached PDF Gate source download did not complete");
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 10000 });

    const warmIdentityKey = "runtime-warm-identity-20260803";
    await configure(normalBytes, { slow: 2 });
    await clearCache(warmIdentityKey);
    const warmIdentity = await page.evaluate(({ bytes, key }) => window.__ftLessonEntryGateProbe.pdfSourceWarmDownload({ bytes, key }), { bytes: normalBytes, key: warmIdentityKey });
    assert.equal(warmIdentity.bytes, normalBytes, "actual warm path rejected the asset path mapped from the .space_pdf source");
    assert(warmIdentity.trace.some((event) => event.event === "progress" && event.chunkIndex === 1 && event.loaded > 0), "actual warm path emitted no chunk-1 byte progress");

    await configure(normalBytes, { slow: 5 });
    await clearCache(normalKey);
    const normal = await download(normalBytes, normalKey);
    assert.equal(normal.bytes, normalBytes);
    assert.equal(normal.chunks, 3);
    const chunkOneProgress = normal.trace.filter((event) => event.event === "progress" && event.chunkIndex === 1);
    assert(chunkOneProgress.length >= 4, `chunk 1 emitted too few progress events: ${chunkOneProgress.length}`);
    assert(chunkOneProgress.some((event) => event.loaded > 0 && event.loaded < 2 * 1024 * 1024), "chunk 1 had no intermediate byte progress");
    assert.equal(state.requests.length, 3, `unexpected normal request count: ${state.requests.length}`);
    await new Promise((resolve) => setTimeout(resolve, 500));
    const requestCountAfterNormal = state.requests.length;

    const cached = await download(normalBytes, normalKey);
    assert.equal(cached.bytes, normalBytes);
    assert.equal(state.requests.length, requestCountAfterNormal, "cached reopen issued a PDF request");
    assert.equal(cached.trace.filter((event) => event.event === "cache_hit").length, 3);

    await page.evaluate(async (key) => {
      const cache = await caches.open("future-space-pdf-files-v1");
      await cache.delete(`${window.location.origin}/__future_pdf_file_chunk_cache__/${encodeURIComponent(key)}/1`);
    }, normalKey);
    const partial = await download(normalBytes, normalKey);
    assert.equal(partial.trace.filter((event) => event.event === "cache_hit").length, 2);
    assert.equal(state.requests.length, requestCountAfterNormal + 1, "partial cache did not request exactly one missing chunk");

    const retryKey = "runtime-retry-20260803";
    await configure(4 * 1024 * 1024, { slow: 2, failChunk: 2 });
    await clearCache(retryKey);
    const retried = await download(4 * 1024 * 1024, retryKey);
    assert.equal(retried.bytes, 4 * 1024 * 1024);
    assert(state.requests.some((row) => row.chunkIndex === 2 && row.attempt === 1));
    assert(state.requests.some((row) => row.chunkIndex === 2 && row.attempt === 2));
    assert(retried.trace.some((event) => event.event === "request_error" && event.chunkIndex === 2));

    const noLengthKey = "runtime-no-length-20260803";
    await configure(2 * 1024 * 1024, { slow: 2, noLength: true });
    await clearCache(noLengthKey);
    const noLength = await download(2 * 1024 * 1024, noLengthKey);
    assert.equal(noLength.bytes, 2 * 1024 * 1024);
    assert(noLength.trace.some((event) => event.event === "progress" && event.loaded > 0), "no-Length response did not expose byte progress");

    assert.deepEqual(errors, [], `browser errors: ${errors.join(" | ")}`);
    console.log(JSON.stringify({
      ok: true,
      backgroundGate: backgroundHud,
      gate: { coldReset: gateColdReset, samples: visibleGateSamples.length, percentSeries: gatePercentSeries, chunkOneByteSeries, firstNonZero: visibleGateSamples.find((sample) => sample.percent !== "0%") || null },
      normal: { requests: requestCountAfterNormal, chunkOneProgress: chunkOneProgress.length, cachedRequests: state.requests.length },
      warmIdentity: { traceEvents: warmIdentity.trace.length },
      retry: { requests: state.requests.length, traceEvents: retried.trace.length },
      noLength: { traceEvents: noLength.trace.length },
    }));
    await context.close();
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
