"use strict";

const { chromium } = require("playwright");

const base = process.env.FUTURE_FRONTEND_PROBE_BASE || "http://127.0.0.1:8877";
const username = process.env.FUTURE_FRONTEND_PROBE_USER || "hung";
const password = process.env.FUTURE_TEST_PASSWORD || "";
const browserPath = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

if (!password) throw new Error("Set FUTURE_TEST_PASSWORD");

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

(async () => {
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 820 } });
  const requests = [];
  page.on("request", (request) => {
    if (request.url().startsWith(base)) {
      requests.push({ at: Date.now(), method: request.method(), path: new URL(request.url()).pathname });
    }
  });
  try {
    await page.goto(`${base}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await setInput(page, "#ft-auth-user", username);
    await setInput(page, "#ft-auth-pass", password);
    const loginRequestStart = requests.length;
    const loginStartedAt = performance.now();
    await page.locator("#ft-auth-submit").click({ force: true });
    await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
    const loginGateMs = performance.now() - loginStartedAt;
    await page.locator(".ft-server-item.is-file").first().waitFor({ state: "visible", timeout: 30000 });
    await page.waitForTimeout(6000);
    const firstFile = page.locator(".ft-server-item.is-file:not(.is-selected)").first();
    const clickRequestStart = requests.length;
    const clickStartedWall = Date.now();
    const clickStartedAt = performance.now();
    await firstFile.click({ force: true });
    await page.waitForFunction(() => Boolean(document.querySelector(".ft-server-item.is-file.is-selected")), null, { timeout: 5000 });
    const clickDomMs = performance.now() - clickStartedAt;
    await page.waitForTimeout(900);
    const clickRequests = requests.slice(clickRequestStart).filter((row) => row.at >= clickStartedWall && (
      /server-data\/list|server-data\/last-file|space-v\/progress|space-w\/progress|space-q\/progress|vocab\/file-stats|lesson-tasks/.test(row.path)
    ));
    const loginRequests = requests.slice(loginRequestStart);
    console.log(JSON.stringify({
      ok: true,
      login_gate_ms: Number(loginGateMs.toFixed(1)),
      login_vocab_index_requests: loginRequests.filter((row) => row.path === "/vocab/lesson-index").length,
      click_dom_ms: Number(clickDomMs.toFixed(1)),
      click_server_reads: clickRequests,
      selected: await page.locator(".ft-server-item.is-file.is-selected").count(),
    }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
