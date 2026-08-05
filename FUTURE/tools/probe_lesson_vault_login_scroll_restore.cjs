"use strict";

const { chromium } = require("playwright");

const base = process.argv[2] || "http://127.0.0.1:18877";
const username = process.argv[3] || "quynh";
const password = process.env.FUTURE_TEST_PASSWORD || "";
if (!password) throw new Error("FUTURE_TEST_PASSWORD is required");

const main = async () => {
  const browser = await chromium.launch({ headless: true, executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" });
  const context = await browser.newContext({ viewport: { width: 1280, height: 860 } });
  const page = await context.newPage();
  const setInput = async (selector, value) => page.evaluate(({ selector: target, value: nextValue }) => {
    const input = document.querySelector(target);
    if (!input) throw new Error(`missing ${target}`);
    input.readOnly = false;
    input.value = nextValue;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }, { selector, value });
  const requests = [];
  const started = new Map();
  page.on("request", (request) => {
    if (/\/auth\/(login|me)|\/server-data\/(login-preload|last-file|list|common-tree|user-overlay)|\/frontend-version/.test(request.url())) {
      started.set(request, Date.now());
    }
  });
  page.on("response", (response) => {
    if (!started.has(response.request())) return;
    requests.push({
      method: response.request().method(),
      url: response.url().replace(base, ""),
      status: response.status(),
      at: Date.now(),
      ms: Date.now() - started.get(response.request()),
      cache: response.headers()["x-future-cache-hit"] || "",
    });
  });
  await page.goto(`${base}/login`, { waitUntil: "domcontentloaded" });
  await setInput("#ft-auth-user", username);
  await setInput("#ft-auth-pass", password);
  const loginClickedAt = Date.now();
  await page.locator("#ft-auth-submit").click({ force: true });
  await page.waitForFunction(() => {
    const manager = window.__futureLessonVaultRestoreManager;
    const state = manager && manager.current && manager.current();
    return Boolean(state && (state.scrolled || state.cancelled));
  }, null, { timeout: 45000 });

  const capture = async (label) => page.evaluate(async (captureLabel) => {
    const manager = window.__futureLessonVaultRestoreManager;
    const state = manager && manager.current ? manager.current() : null;
    const token = localStorage.getItem("future_lesson_auth_token") || "";
    const lastResponse = await fetch("/server-data/last-file", { headers: { Authorization: `Bearer ${token}` } });
    const lastPayload = await lastResponse.json();
    const list = document.getElementById("ft-server-list");
    const selected = list && list.querySelector(".ft-server-item.is-file.is-selected, .ft-server-item.is-file.is-task-focus");
    const selectedRect = selected && selected.getBoundingClientRect();
    const listRect = list && list.getBoundingClientRect();
    return {
      label: captureLabel,
      identity: localStorage.getItem("future_lesson_auth_user") || "",
      route: location.pathname + location.search + location.hash,
      expectedFile: lastPayload && lastPayload.state && lastPayload.state.file && lastPayload.state.file.path || "",
      expectedParent: lastPayload && lastPayload.state && lastPayload.state.file && lastPayload.state.file.parentPath || "",
      actualFile: selected && selected.dataset.path || "",
      elementExists: Boolean(selected),
      elementHasSize: Boolean(selectedRect && selectedRect.width > 0 && selectedRect.height > 0),
      targetVisibleInList: Boolean(selectedRect && listRect && selectedRect.bottom > listRect.top && selectedRect.top < listRect.bottom),
      scrollTop: list ? list.scrollTop : 0,
      restoreCalls: state ? state.restoreCalls : 0,
      generation: state ? state.generation : 0,
      elapsedMs: state && state.completedAt ? state.completedAt - state.startedAt : 0,
      cancelled: Boolean(state && state.cancelled),
      timeline: manager && manager.trace ? manager.trace() : [],
    };
  }, label);

  const first = await capture("fresh-login");
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => {
    const manager = window.__futureLessonVaultRestoreManager;
    const state = manager && manager.current && manager.current();
    return Boolean(state && state.generation >= 1 && state.scrolled);
  }, null, { timeout: 45000 });
  const refreshed = await capture("authenticated-refresh");
  const output = {
    ok: Boolean(
      first.identity.toLowerCase() === username.toLowerCase()
      && first.expectedFile && first.actualFile === first.expectedFile
      && first.elementHasSize && first.targetVisibleInList && first.restoreCalls === 1 && !first.cancelled
      && refreshed.actualFile === refreshed.expectedFile
      && refreshed.elementHasSize && refreshed.targetVisibleInList && refreshed.restoreCalls === 1 && !refreshed.cancelled
    ),
    loginClickedAt,
    first,
    refreshed,
    requests,
  };
  console.log(JSON.stringify(output, null, 2));
  await browser.close();
  if (!output.ok) process.exitCode = 1;
};

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
