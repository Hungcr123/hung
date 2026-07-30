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
  throw new Error("Server 2 did not become healthy after restart");
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
  const identity = await page.evaluate(async () => {
    const token = localStorage.getItem("future_lesson_auth_token") || "";
    const response = await fetch("/auth/me", { headers: { Authorization: `Bearer ${token}` } });
    return response.json();
  });
  if (String(identity.username || "").toLowerCase() !== String(username).toLowerCase()) {
    throw new Error(`DOM login identity mismatch: expected ${username}, received ${identity.username || "missing"}`);
  }
  await page.locator("#ft-chat-button.is-visible").waitFor({ state: "attached", timeout: 30000 });
};

const openChat = async (page) => {
  await page.locator("#ft-chat-button").evaluate((button) => button.click());
  await page.locator("#ft-chat-modal[aria-hidden='false']").waitFor({ state: "attached", timeout: 30000 });
};

const hasMessage = async (page, text) => {
  await page.locator("#ft-chat-log .ft-chat-text", { hasText: text }).waitFor({ state: "attached", timeout: 30000 });
};

const main = async () => {
  const browser = await chromium.launch({ executablePath: BROWSER, headless: true });
  const errors = [];
  let suppressExpectedRestartErrors = false;
  const prefix = `codex-chat-dom-${Date.now()}`;
  try {
    if (process.env.CHAT_DOM_VERIFY_ONLY === "1") {
      const context = await browser.newContext();
      const page = await context.newPage();
      page.on("pageerror", (error) => errors.push(`page:${error.message}`));
      page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
      await login(page, "hungcr");
      errors.length = 0;
      await openChat(page);
      await page.waitForTimeout(1000);
      if (errors.length) throw new Error(`Frontend errors: ${errors.join(" | ")}`);
      await context.close();
      console.log(JSON.stringify({ chat_dom_verify_only: "ok", real_hungcr_login: true, chat_open: true, frontend_errors: 0 }));
      return;
    }
    const context = await browser.newContext();
    const page = await context.newPage();
    page.on("pageerror", (error) => { if (!suppressExpectedRestartErrors) errors.push(`page:${error.message}`); });
    page.on("console", (message) => { if (!suppressExpectedRestartErrors && message.type() === "error") errors.push(`console:${message.text()}`); });
    await login(page, "codexload100");
    errors.length = 0;
    await openChat(page);
    await page.locator("#ft-chat-input").fill(prefix);
    const sendResponse = page.waitForResponse(
      (response) => response.url().includes("/chat/send") && response.request().method() === "POST",
      { timeout: 30000 },
    );
    await page.locator("#ft-chat-input").press("Enter");
    const sent = await sendResponse;
    if (!sent.ok()) throw new Error(`DOM chat send failed with HTTP ${sent.status()}: ${await sent.text()}`);
    await hasMessage(page, prefix);
    await page.locator("#ft-chat-close").click();
    await openChat(page);
    await hasMessage(page, prefix);
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.locator("#ft-chat-button.is-visible").waitFor({ state: "attached", timeout: 60000 });
    await openChat(page);
    await hasMessage(page, prefix);

    suppressExpectedRestartErrors = true;
    const restarted = await restartServer();
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.locator("#ft-chat-button.is-visible").waitFor({ state: "attached", timeout: 60000 });
    await openChat(page);
    await hasMessage(page, prefix);
    suppressExpectedRestartErrors = false;
    await context.close();

    const freshContext = await browser.newContext();
    const freshPage = await freshContext.newPage();
    freshPage.on("pageerror", (error) => errors.push(`fresh-page:${error.message}`));
    freshPage.on("console", (message) => { if (message.type() === "error") errors.push(`fresh-console:${message.text()}`); });
    await login(freshPage, "codexload100");
    errors.length = 0;
    await openChat(freshPage);
    await hasMessage(freshPage, prefix);
    await freshContext.close();

    const realContext = await browser.newContext();
    const realPage = await realContext.newPage();
    await login(realPage, "hungcr");
    await openChat(realPage);
    const realChatVisible = await realPage.locator("#ft-chat-modal").getAttribute("aria-hidden") === "false";
    await realContext.close();
    if (!realChatVisible) throw new Error("Real hungcr chat DOM did not open");
    if (errors.length) throw new Error(`Frontend errors: ${errors.join(" | ")}`);

    console.log(JSON.stringify({
      chat_dom_runtime: "ok",
      prefix,
      close_reopen: true,
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
