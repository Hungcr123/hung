"use strict";

const fs = require("fs");
const { chromium } = require("playwright");

const base = process.env.FUTURE_DOM_BASE || "http://127.0.0.1:18877";
const username = process.env.FUTURE_DOM_USER || "codexgate000";
const password = process.env.FUTURE_LOAD_TEST_PASSWORD || process.env.FUTURE_TEST_PASSWORD || "";
const fixturePath = process.env.FUTURE_DOM_FIXTURES || "";
const outputPath = process.env.FUTURE_DOM_OUTPUT || "";
const samplesPerSpace = Math.max(1, Math.min(50, Number(process.env.FUTURE_DOM_SAMPLES_PER_SPACE || 20)));
const domConcurrency = Math.max(1, Math.min(10, Number(process.env.FUTURE_DOM_CONCURRENCY || 5)));
const browserPath = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

if (!password) throw new Error("FUTURE_LOAD_TEST_PASSWORD is required");
if (!fixturePath || !outputPath) throw new Error("FUTURE_DOM_FIXTURES and FUTURE_DOM_OUTPUT are required");

const percentile = (values, ratio) => {
  const sorted = values.map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return 0;
  const index = Math.max(0, Math.min(sorted.length - 1, Math.ceil(sorted.length * ratio) - 1));
  return Number(sorted[index].toFixed(3));
};

const distribution = (values) => ({
  count: values.length,
  p50: percentile(values, 0.50),
  p95: percentile(values, 0.95),
  p99: percentile(values, 0.99),
  max: values.length ? Number(Math.max(...values).toFixed(3)) : 0,
});

const setInput = async (page, selector, value) => {
  await page.evaluate(({ selector: target, value: nextValue }) => {
    const input = document.querySelector(target);
    if (!input) throw new Error(`Missing ${target}`);
    input.readOnly = false;
    input.value = nextValue;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }, { selector, value });
};

const waitForVaultRow = async (page, selector, targetPath, timeout = 60000) => {
  await page.waitForFunction(({ selector: rowSelector, targetPath: wanted }) => (
    Array.from(document.querySelectorAll(rowSelector)).some((item) => [
      item.dataset.path,
      item.dataset.effectivePath,
      item.dataset.linkTarget,
      item.dataset.linkedPath,
    ].some((value) => String(value || "") === wanted))
  ), { selector, targetPath }, { timeout });
  return page.locator(selector).evaluateAll((items, wanted) => items.findIndex((item) => [
    item.dataset.path,
    item.dataset.effectivePath,
    item.dataset.linkTarget,
    item.dataset.linkedPath,
  ].some((value) => String(value || "") === wanted)), targetPath);
};

const openVaultFolderPath = async (page, treePath) => {
  const parts = String(treePath || "").split("/").filter(Boolean);
  let cumulative = "";
  for (const part of parts) {
    cumulative = cumulative ? `${cumulative}/${part}` : part;
    let index = -1;
    for (let attempt = 0; attempt < 8 && index < 0; attempt += 1) {
      try {
        index = await waitForVaultRow(page, ".ft-server-item.is-folder", cumulative, 1500);
      } catch (_error) {
        const back = page.locator("#ft-server-back");
        if (await back.count() !== 1) break;
        if (await back.isVisible()) {
          await back.click({ force: true });
        } else {
          await back.evaluate((button) => button.click());
        }
        await page.waitForTimeout(220);
      }
    }
    if (index < 0) throw new Error(`Lesson Vault folder not found: ${cumulative}`);
    const row = page.locator(".ft-server-item.is-folder").nth(index);
    await row.click({ force: true });
    await page.waitForTimeout(300);
    await row.click({ force: true });
    await page.waitForTimeout(800);
  }
};

const vaultFileRowIndex = async (page, lessonPath, timeout = 15000) => {
  try {
    return await waitForVaultRow(page, ".ft-server-item.is-file", lessonPath, timeout);
  } catch (_error) {
    return -1;
  }
};

const summarize = (rows) => {
  const bySpace = {};
  for (const spaceType of ["space_q", "space_w", "space_p", "space_l", "space_s"]) {
    const selected = rows.filter((row) => row.space_type === spaceType && row.ok);
    bySpace[spaceType] = {
      samples: selected.length,
      completion_wall_ms: distribution(selected.map((row) => row.completion_response_ms)),
      completion_to_top_api_ms: distribution(selected.map((row) => row.completion_to_top_api_ms)),
      completion_to_top_dom_ms: distribution(selected.map((row) => row.completion_to_top_dom_ms)),
      response_bytes: distribution(selected.map((row) => row.top_response_bytes)),
      failures: rows.filter((row) => row.space_type === spaceType && !row.ok),
    };
  }
  return bySpace;
};

(async () => {
  const fixtureDocument = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
  const fixtureSource = fixtureDocument.workload && fixtureDocument.workload.lessons
    ? fixtureDocument.workload.lessons
    : fixtureDocument;
  const fixtures = Object.fromEntries(Object.entries(fixtureSource).map(([spaceType, value]) => [spaceType, Array.isArray(value) ? value[0] : value]));
  const userPrefix = process.env.FUTURE_DOM_USER_PREFIX || username.replace(/\d+$/, "");
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const rows = [];
  const allFrontendErrors = [];
  const allNetworkErrors = [];
  const runSample = async (spaceType, lesson, sample, userIndex) => {
    const sampleUser = `${userPrefix}${String(userIndex).padStart(3, "0")}`;
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    const frontendErrors = [];
    const networkErrors = [];
    page.on("pageerror", (error) => frontendErrors.push(`page:${error.message}`));
    page.on("console", (message) => { if (message.type() === "error") frontendErrors.push(`console:${message.text()}`); });
    page.on("response", (response) => { if (response.status() >= 400) networkErrors.push({ status: response.status(), url: response.url() }); });
    try {
      process.stderr.write(`DOM_STAGE ${spaceType} sample=${sample} user=${sampleUser} login\n`);
      await page.goto(`${base}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
      await setInput(page, "#ft-auth-user", sampleUser);
      await setInput(page, "#ft-auth-pass", password);
      await page.locator("#ft-auth-submit").click({ force: true });
      await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
      await page.waitForFunction(() => Boolean(localStorage.getItem("future_lesson_auth_token")), null, { timeout: 60000 });
      const treePath = lesson.path.includes("/") ? lesson.path.slice(0, lesson.path.lastIndexOf("/")) : "common";
      await page.goto(`${base}/lesson_vault?tree=${encodeURIComponent(treePath)}&task_owner=${encodeURIComponent(sampleUser)}&ft_completion_probe=1`, { waitUntil: "domcontentloaded", timeout: 60000 });
      await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
      let matchingIndex = await vaultFileRowIndex(page, lesson.path);
      if (matchingIndex < 0) {
        await page.goto(`${base}/lesson_vault?task_owner=${encodeURIComponent(sampleUser)}&ft_completion_probe=1`, { waitUntil: "domcontentloaded", timeout: 60000 });
        await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
        await openVaultFolderPath(page, treePath);
        matchingIndex = await waitForVaultRow(page, ".ft-server-item.is-file", lesson.path);
      }
      if (matchingIndex < 0) throw new Error(`Lesson Vault row not found: ${lesson.path}`);
      const row = page.locator(".ft-server-item.is-file").nth(matchingIndex);
      const openButton = row.locator('button[aria-label="Open this lesson"]');
      if (await openButton.count() !== 1) throw new Error(`Open button missing for ${lesson.path}`);
      await openButton.click({ force: true });
      await page.locator("#ft-node-completion-dom-probe").waitFor({ state: "attached", timeout: 30000 });
      await page.waitForFunction(() => Boolean(window.__ftNodeCompletionDomProbeReady && window.__ftNodeCompletionDomProbeReady()), null, { timeout: 60000 });
      await page.locator("#ft-node-completion-dom-probe").click({ force: true });
      await page.waitForFunction(() => Boolean(window.__ftNodeCompletionDomProbeResult), null, { timeout: 30000 });
      const result = await page.evaluate(() => window.__ftNodeCompletionDomProbeResult);
      return { space_type: spaceType, sample, user: sampleUser, ...result, frontend_errors: frontendErrors, network_errors: networkErrors };
    } finally {
      allFrontendErrors.push(...frontendErrors);
      allNetworkErrors.push(...networkErrors);
      await context.close();
    }
  };
  try {
    const jobs = [];
    let userIndex = 0;
    for (const spaceType of ["space_q", "space_w", "space_p", "space_l", "space_s"]) {
      const lesson = fixtures[spaceType];
      if (!lesson || !lesson.path) throw new Error(`Missing DOM fixture for ${spaceType}`);
      for (let sample = 1; sample <= samplesPerSpace; sample += 1) {
        jobs.push({ spaceType, lesson, sample, userIndex });
        userIndex += 1;
      }
    }
    for (let index = 0; index < jobs.length; index += domConcurrency) {
      const batch = jobs.slice(index, index + domConcurrency);
      rows.push(...await Promise.all(batch.map((job) => runSample(job.spaceType, job.lesson, job.sample, job.userIndex))));
    }
  } finally {
    await browser.close();
  }
  const blockingFrontendErrors = allFrontendErrors.filter((message) => !/console:Failed to load resource:/i.test(message));
  const result = {
    ok: rows.length === samplesPerSpace * 5 && rows.every((row) => row.ok && row.user_visible) && blockingFrontendErrors.length === 0,
    base, username, user_prefix: userPrefix, samples_per_space: samplesPerSpace, concurrency: domConcurrency, total_samples: rows.length,
    by_space: summarize(rows), frontend_errors: allFrontendErrors, blocking_frontend_errors: blockingFrontendErrors,
    network_errors: allNetworkErrors, rows,
  };
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  process.stdout.write(JSON.stringify({ ok: result.ok, total_samples: result.total_samples, by_space: result.by_space, frontend_errors: result.frontend_errors.length, blocking_frontend_errors: result.blocking_frontend_errors.length }));
  if (!result.ok) process.exitCode = 1;
})().catch((error) => {
  process.stderr.write(error && error.stack ? error.stack : String(error));
  process.exitCode = 1;
});
