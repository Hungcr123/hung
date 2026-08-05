"use strict";

const assert = require("node:assert/strict");
const { chromium } = require("playwright");

const base = process.env.FUTURE_DOM_BASE || "http://127.0.0.1:18877";
const username = process.env.FUTURE_DOM_USER || "codexspaceqsurface";
const password = process.env.FUTURE_DOM_PASSWORD || process.env.FUTURE_TEST_PASSWORD || "";
const lessonPath = process.env.FUTURE_SPACE_Q_PATH || "";
const lessonId = process.env.FUTURE_SPACE_Q_ID || "";
const treePath = lessonPath.includes("/") ? lessonPath.slice(0, lessonPath.lastIndexOf("/")) : "common";
if (!password || !lessonPath || !lessonId) throw new Error("Space_Q DOM probe requires password, path, and lesson ID");

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

const progressForTarget = (page) => page.evaluate(({ wantedPath, wantedId }) => {
  const visibleProgress = (node) => {
    const text = String(node?.textContent || "");
    const match = text.match(/\d+\/48/);
    return match ? match[0] : String(node?.dataset.progressText || "");
  };
  const matches = (node) => {
    if (!node) return false;
    const values = [node.dataset.path, node.dataset.effectivePath, node.dataset.linkTarget, node.dataset.lessonId, node.dataset.fileId]
      .map((value) => String(value || "").toLowerCase());
    return values.includes(String(wantedPath || "").toLowerCase()) || values.includes(String(wantedId || "").toLowerCase());
  };
  const rows = Array.from(document.querySelectorAll(".ft-server-item.is-file"));
  const tasks = Array.from(document.querySelectorAll("[data-task-id]"));
  const row = rows.find(matches) || null;
  const task = tasks.find((node) => matches(node) && node.dataset.assignmentSource === "system") || null;
  return {
    row: row ? { path: row.dataset.path || "", lessonId: row.dataset.lessonId || "", progressText: visibleProgress(row), text: row.textContent || "" } : null,
    task: task ? { path: task.dataset.path || "", lessonId: task.dataset.lessonId || "", progressText: task.dataset.progressText || "", progressPercent: task.dataset.progressPercent || "", text: task.textContent || "" } : null,
  };
}, { wantedPath: lessonPath, wantedId: lessonId });

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("console", (message) => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  try {
    await page.goto(`${base}/login`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await setInput(page, "#ft-auth-user", username);
    await setInput(page, "#ft-auth-pass", password);
    const submit = page.locator("#ft-auth-submit");
    assert.equal(await submit.count(), 1);
    await submit.click({ force: true });
    await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
    await page.waitForFunction(() => Boolean(localStorage.getItem("future_lesson_auth_token")), null, { timeout: 60000 });
    await page.waitForTimeout(250);
    await page.goto(`${base}/lesson_vault?tree=${encodeURIComponent(treePath)}&task_owner=${encodeURIComponent(username)}`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
    await page.waitForFunction(({ wantedPath, wantedId }) => Array.from(document.querySelectorAll('[data-task-id][data-assignment-source="system"]')).some((node) => {
      const values = [node.dataset.path, node.dataset.effectivePath, node.dataset.linkTarget, node.dataset.lessonId, node.dataset.fileId].map((v) => String(v || "").toLowerCase());
      return values.includes(String(wantedPath || "").toLowerCase()) || values.includes(String(wantedId || "").toLowerCase());
    }), { wantedPath: lessonPath, wantedId: lessonId }, { timeout: 120000 });
    const targetTask = page.locator(`[data-task-id][data-assignment-source="system"][data-path="${lessonPath.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"]`);
    if (await targetTask.count() !== 1) throw new Error("Target Space_Q task card is ambiguous");
    await targetTask.click({ force: true });
    try {
      await page.waitForFunction(({ wantedPath, wantedId }) => Array.from(document.querySelectorAll(".ft-server-item.is-file")).some((node) => {
        const values = [node.dataset.path, node.dataset.effectivePath, node.dataset.linkTarget, node.dataset.lessonId, node.dataset.fileId].map((v) => String(v || "").toLowerCase());
        return values.includes(String(wantedPath || "").toLowerCase()) || values.includes(String(wantedId || "").toLowerCase());
      }), { wantedPath: lessonPath, wantedId: lessonId }, { timeout: 120000 });
    } catch (error) {
      const diagnostics = await page.evaluate(() => ({
        url: location.href,
        status: document.querySelector("#ft-load-status")?.textContent || "",
        paths: Array.from(document.querySelectorAll(".ft-server-item")).slice(0, 30).map((node) => node.dataset.path || ""),
        taskPaths: Array.from(document.querySelectorAll("[data-task-id]")).slice(0, 30).map((node) => node.dataset.path || ""),
      }));
      throw new Error(`Lesson Vault target wait failed: ${JSON.stringify(diagnostics)}; ${error.message}`);
    }
    const before = await progressForTarget(page);
    assert(before.row && before.task, `target row/task missing before open: ${JSON.stringify(before)}`);
    assert.equal(before.row.progressText, "2/48", `Lesson Vault DOM stale before open: ${JSON.stringify(before)}`);
    assert.equal(before.task.progressText, "2/48", `Space Task DOM stale before open: ${JSON.stringify(before)}`);

    // Optional interactive gate: open the real Space_Q, advance one node through
    // its rendered answer controls, then use the real Exit button before re-reading DOM.
    let interactive = null;
    if (process.env.FUTURE_DOM_INTERACTIVE === "1") {
      await page.evaluate(({ wantedPath }) => {
        const row = Array.from(document.querySelectorAll(".ft-server-item.is-file")).find((node) => String(node.dataset.path || "").toLowerCase() === String(wantedPath || "").toLowerCase());
        const open = row && row.querySelector(".ft-lesson-go-button");
        if (!open) throw new Error("Space_Q Lesson Vault Open button not found");
        open.click();
      }, { wantedPath: lessonPath });
      const continueButton = page.locator("#ft-entry-gate-continue");
      const openButton = page.locator("#ft-entry-gate-open");
      await page.waitForFunction(() => Boolean(document.querySelector("#ft-entry-gate-continue:not([hidden])") || document.querySelector("#ft-entry-gate-open:not([hidden])")), null, { timeout: 60000 });
      if (await continueButton.count() === 1 && await continueButton.isVisible() && await continueButton.isEnabled()) {
        await continueButton.click({ force: true });
      } else {
        assert.equal(await openButton.count(), 1);
        await openButton.click({ force: true });
      }
      const vocabSkip = page.locator("#ft-vocab-preflight-skip");
      if (await vocabSkip.count() === 1) {
        await page.waitForFunction(() => document.querySelector(".ft-stage")?.classList.contains("is-question-mode") || document.querySelector("#ft-vocab-preflight-gate")?.hidden === false, null, { timeout: 60000 });
        if (await vocabSkip.isVisible() && await vocabSkip.isEnabled()) {
          await vocabSkip.click({ force: true });
        }
      }
      await page.waitForFunction(() => document.querySelector(".ft-stage")?.classList.contains("is-question-mode"), null, { timeout: 120000 });
      const nextButton = page.locator("#ft-q-next");
      let answerAttempts = 0;
      for (let round = 0; round < 12; round += 1) {
        const options = page.locator("button.ft-q-picture-answer-card:not(.is-guide)");
        const optionCount = await options.count();
        if (!optionCount) break;
        let advanced = false;
        for (let index = 0; index < optionCount; index += 1) {
          await options.nth(index).click({ force: true });
          answerAttempts += 1;
          await page.waitForTimeout(180);
          if (await nextButton.count() === 1 && await nextButton.isEnabled()) {
            advanced = true;
            break;
          }
        }
        if (advanced) break;
        const input = page.locator("#ft-q-answer");
        if (await input.count() === 1 && await input.isVisible()) {
          await input.fill("the");
          await input.press("Enter");
          await page.waitForTimeout(300);
          if (await nextButton.isEnabled()) break;
        }
      }
      assert.equal(await nextButton.count(), 1, "Space_Q next control missing after opening");
      if (await nextButton.isEnabled()) await nextButton.click({ force: true });
      await page.waitForTimeout(500);
      const exitButton = page.locator("#ft-vault-button");
      assert.equal(await exitButton.count(), 1, "Lesson Vault Exit button missing inside Space_Q");
      await exitButton.click({ force: true });
      await page.waitForFunction(() => !document.querySelector(".ft-stage")?.classList.contains("is-question-mode"), null, { timeout: 120000 });
      await page.waitForTimeout(700);
      const afterInteractive = await progressForTarget(page);
      assert(afterInteractive.row && afterInteractive.task, `target row/task missing after interactive Exit: ${JSON.stringify(afterInteractive)}`);
      assert.notEqual(afterInteractive.row.progressText, "0/48", `Lesson Vault stayed at zero after real Space_Q Exit: ${JSON.stringify(afterInteractive)}`);
      assert.equal(afterInteractive.row.progressText, afterInteractive.task.progressText, `Lesson Vault/Space Task diverged after real Space_Q Exit: ${JSON.stringify(afterInteractive)}`);
      interactive = { answerAttempts, afterExit: afterInteractive };
    }

    // Reload exercises the same authenticated DOM hydration used after Exit without
    // depending on unrelated vocabulary-preflight assets in the isolated fixture.
    await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await page.locator("#ft-auth-gate").waitFor({ state: "hidden", timeout: 60000 });
    await page.waitForFunction(({ wantedPath, wantedId }) => Array.from(document.querySelectorAll('[data-task-id][data-assignment-source="system"]')).some((node) => {
      const values = [node.dataset.path, node.dataset.effectivePath, node.dataset.linkTarget, node.dataset.lessonId, node.dataset.fileId].map((v) => String(v || "").toLowerCase());
      return values.includes(String(wantedPath || "").toLowerCase()) || values.includes(String(wantedId || "").toLowerCase());
    }), { wantedPath: lessonPath, wantedId: lessonId }, { timeout: 120000 });
    await page.waitForFunction(({ wantedPath, wantedId }) => Array.from(document.querySelectorAll(".ft-server-item.is-file")).some((node) => {
      const values = [node.dataset.path, node.dataset.effectivePath, node.dataset.linkTarget, node.dataset.lessonId, node.dataset.fileId].map((v) => String(v || "").toLowerCase());
      return values.includes(String(wantedPath || "").toLowerCase()) || values.includes(String(wantedId || "").toLowerCase());
    }), { wantedPath: lessonPath, wantedId: lessonId }, { timeout: 120000 });
    await page.waitForFunction(({ wantedPath, wantedId }) => Array.from(document.querySelectorAll('[data-task-id][data-assignment-source="system"]')).some((node) => {
      const values = [node.dataset.path, node.dataset.effectivePath, node.dataset.linkTarget, node.dataset.lessonId, node.dataset.fileId].map((v) => String(v || "").toLowerCase());
      return values.includes(String(wantedPath || "").toLowerCase()) || values.includes(String(wantedId || "").toLowerCase());
    }), { wantedPath: lessonPath, wantedId: lessonId }, { timeout: 90000 });
    const after = await progressForTarget(page);
    assert(after.row && after.task, `target row/task missing after Exit: ${JSON.stringify(after)}`);
    const expectedAfter = interactive?.afterExit?.row?.progressText || "2/48";
    assert.equal(after.row.progressText, expectedAfter, `Lesson Vault DOM stale after Exit: ${JSON.stringify(after)}`);
    assert.equal(after.task.progressText, expectedAfter, `Space Task DOM stale after Exit: ${JSON.stringify(after)}`);
    const blockingErrors = errors.filter((item) => !item.includes("Failed to load resource"));
    if (blockingErrors.length) throw new Error(`frontend errors: ${blockingErrors.join(" | ")}`);
    console.log(JSON.stringify({ ok: true, before, interactive, after, errors, blockingErrors }));
  } finally {
    await context.close();
    await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
