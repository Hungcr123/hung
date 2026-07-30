const { spawn } = require("child_process");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const BASE = "http://127.0.0.1:8877";
const BROWSER = "C:\\Program Files\\CocCoc\\Browser\\Application\\browser.exe";
const password = process.env.FUTURE_TEST_PASSWORD || "";
if (!password) throw new Error("Set FUTURE_TEST_PASSWORD for this DOM test only");

const waitHealth = async (differentFrom = 0) => {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${BASE}/health`);
      const payload = await response.json();
      if (payload.ok && Number(payload.pid || 0) !== Number(differentFrom || 0)) return payload;
    } catch (_error) {}
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error("Server 2 did not become healthy after preference DOM restart");
};

const restartServer = async () => {
  const current = await waitHealth();
  process.kill(Number(current.pid), "SIGKILL");
  spawn("python", [path.join(ROOT, "FUTURE_SERVER_2.py"), "--replace-old"], {
    cwd: ROOT,
    detached: true,
    stdio: "ignore",
    windowsHide: true,
  }).unref();
  return waitHealth(Number(current.pid));
};

const login = async (page, username) => {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator("#ft-auth-user").click();
  await page.locator("#ft-auth-user").fill(username);
  await page.locator("#ft-auth-pass").click();
  await page.locator("#ft-auth-pass").fill(password);
  await page.locator("#ft-auth-submit").click();
  await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
  await page.waitForFunction(() => Boolean(localStorage.getItem("future_lesson_auth_token")), null, { timeout: 60000 });
  await page.locator("#ft-chat-button.is-visible").waitFor({ state: "attached", timeout: 30000 });
};

const openChat = async (page) => {
  await page.locator("#ft-chat-button").evaluate((button) => button.click());
  await page.locator("#ft-chat-modal[aria-hidden='false']").waitFor({ state: "attached", timeout: 30000 });
};

const audioState = async (page) => (await page.locator("#ft-chat-audio-toggle").getAttribute("aria-pressed")) === "true";

const main = async () => {
  const browser = await chromium.launch({ executablePath: BROWSER, headless: true });
  const errors = [];
  let suppressRestartErrors = false;
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on("pageerror", (error) => { if (!suppressRestartErrors) errors.push(`page:${error.message}`); });
    page.on("console", (message) => { if (!suppressRestartErrors && message.type() === "error") errors.push(`console:${message.text()}`); });
    await login(page, "codexload100");
    errors.length = 0;
    await openChat(page);
    const initial = await audioState(page);
    const responsePromise = page.waitForResponse(
      (response) => response.url().includes("/auth/preferences") && response.request().method() === "POST",
      { timeout: 30000 },
    );
    await page.locator("#ft-chat-audio-toggle").click();
    const response = await responsePromise;
    const ack = await response.json();
    if (!response.ok() || ack.preferences || Number(ack.server_revision || 0) <= 0) {
      throw new Error(`Preference DOM did not receive compact ACK: ${JSON.stringify(ack)}`);
    }
    const expected = !initial;
    if (await audioState(page) !== expected) throw new Error("Chat audio toggle did not update immediately");

    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.locator("#ft-chat-button.is-visible").waitFor({ state: "attached", timeout: 60000 });
    await openChat(page);
    if (await audioState(page) !== expected) throw new Error("Preference did not restore after page reload");

    suppressRestartErrors = true;
    const restarted = await restartServer();
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.locator("#ft-chat-button.is-visible").waitFor({ state: "attached", timeout: 60000 });
    await openChat(page);
    if (await audioState(page) !== expected) throw new Error("Preference did not restore after Server 2 restart");
    suppressRestartErrors = false;
    await context.close();

    const freshContext = await browser.newContext();
    const freshPage = await freshContext.newPage();
    await login(freshPage, "codexload100");
    await openChat(freshPage);
    if (await audioState(freshPage) !== expected) throw new Error("Preference did not restore on a fresh device context");
    await freshContext.close();

    const realContext = await browser.newContext();
    const realPage = await realContext.newPage();
    realPage.on("pageerror", (error) => errors.push(`real-page:${error.message}`));
    realPage.on("console", (message) => { if (message.type() === "error") errors.push(`real-console:${message.text()}`); });
    await login(realPage, "hungcr");
    errors.length = 0;
    await openChat(realPage);
    await realPage.waitForTimeout(1000);
    if (errors.length) throw new Error(`Frontend errors: ${errors.join(" | ")}`);
    await realContext.close();

    console.log(JSON.stringify({
      user_preferences_dom_runtime: "ok",
      compact_ack: true,
      reload_restore: true,
      restart_pid: Number(restarted.pid || 0),
      fresh_device_restore: true,
      real_hungcr_login: true,
      frontend_errors: 0,
    }));
  } finally {
    await browser.close();
  }
};

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exitCode = 1;
});
