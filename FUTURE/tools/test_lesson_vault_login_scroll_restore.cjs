"use strict";

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { chromium } = require("playwright");

const repo = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(repo, "FUTURE", "web", "js_parts", "16_notices_vocabulary_missions.js");
const source = fs.readFileSync(sourcePath, "utf8");
const start = source.indexOf("      let lessonVaultRestoreWaitCleanup = null;");
const end = source.indexOf("      // Added 2026-07-22: a Space Task card click", start);
assert.ok(start >= 0 && end > start, "restore state-machine source block must exist");
const runtimeBlock = source.slice(start, end);

const main = async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  });
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
  await page.setContent(`<!doctype html><style>
    #browser { display:block; width:500px; height:260px; }
    #list { height:200px; overflow:auto; }
    .ft-server-item { display:block; box-sizing:border-box; width:460px; height:36px; }
  </style><div id="browser"><div id="list"></div></div>`);
  await page.addScriptTag({ content: `
    const clean = (value = "") => String(value == null ? "" : value).trim();
    const normalizeServerPathValue = (value = "") => clean(value).replace(/\\\\/g, "/").replace(/^\\/+|\\/+$/g, "");
    const normalizeTaskPath = (value = "") => normalizeServerPathValue(value).toLowerCase();
    const serverListNode = document.getElementById("list");
    const serverBrowser = document.getElementById("browser");
    let serverBrowserPath = "folder";
    let serverBrowserFocusedFilePath = "";
    let currentState = null;
    const traces = [];
    const currentLessonVaultRestoreState = (generation = 0) => currentState && !currentState.cancelled && (!generation || generation === currentState.generation) ? currentState : null;
    const recordLessonVaultRestorePhase = (phase, extra = {}) => traces.push({ phase, ...extra });
    const setSelectedTaskPath = (path = "") => { serverBrowserFocusedFilePath = normalizeServerPathValue(path); };
    const cancelLessonVaultLoginRestore = (_reason, options = {}) => {
      if (!currentState || (options.generation && options.generation !== currentState.generation)) return false;
      currentState.cancelled = true;
      currentState.userInteracted = Boolean(options.userInteracted);
      return true;
    };
    ${runtimeBlock}
    window.restoreTest = {
      setState(state) { currentState = state; traces.length = 0; serverBrowserFocusedFilePath = state.targetFile || ""; },
      state() { return currentState; },
      traces() { return traces.slice(); },
      render(paths) {
        serverListNode.textContent = "";
        paths.forEach((filePath) => {
          const row = document.createElement("button");
          row.className = "ft-server-item is-file";
          row.dataset.path = filePath;
          row.textContent = filePath;
          serverListNode.appendChild(row);
        });
        return { path: "folder", entries: paths.map((filePath) => ({ type: "file", path: filePath })) };
      },
      schedule: scheduleLessonVaultLoginRestore,
      scrollTop() { return serverListNode.scrollTop; },
      setScrollTop(value) { serverListNode.scrollTop = Number(value || 0); },
      userWheel() { serverListNode.dispatchEvent(new WheelEvent("wheel", { bubbles: true })); },
      waitFrames(count = 8) { return new Promise((resolve) => { let left = count; const tick = () => --left <= 0 ? resolve() : requestAnimationFrame(tick); requestAnimationFrame(tick); }); },
    };
  ` });

  const result = await page.evaluate(async () => {
    const cases = [];
    // Reproduce the old production failure: the one-shot 80ms timer fires before the async row exists.
    serverListNode.textContent = "";
    let oldTimerCalls = 0;
    setTimeout(() => {
      const oldTarget = serverListNode.querySelector('[data-path="folder/File 120.Space_V"]');
      if (oldTarget) { oldTarget.scrollIntoView({ block: "center" }); oldTimerCalls += 1; }
    }, 80);
    await new Promise((resolve) => setTimeout(resolve, 140));
    restoreTest.render(Array.from({ length: 120 }, (_, index) => `folder/File ${String(index + 1).padStart(3, "0")}.Space_V`));
    const oldTimerRace = { calls: oldTimerCalls, targetAppearedAfterTimer: true, scrollTop: restoreTest.scrollTop() };
    let generation = 0;
    const makeState = (targetFile, extra = {}) => ({
      generation: ++generation,
      username: extra.username || "hung",
      targetFile,
      targetTree: "folder",
      targetPaths: [targetFile],
      candidates: [{ path: targetFile }],
      lastFileReady: extra.lastFileReady !== false,
      treeReady: false,
      targetRendered: false,
      scrolled: false,
      cancelled: false,
      userInteracted: false,
      restoreCalls: 0,
      completedScrollTop: null,
      startedAt: Date.now(),
      timeline: [],
    });
    const run = async (name, target, rows, options = {}) => {
      const state = makeState(target, options);
      restoreTest.setState(state);
      const before = restoreTest.scrollTop();
      const payload = restoreTest.render(rows);
      if (options.userBeforeRestore) restoreTest.userWheel();
      if (options.treeBeforeLastFile) {
        restoreTest.schedule(payload, name);
        state.lastFileReady = true;
      }
      restoreTest.schedule(payload, name);
      await restoreTest.waitFrames();
      const selected = document.querySelector(".ft-server-item.is-task-focus") || document.querySelector(".ft-server-item.is-selected");
      const actual = selected && selected.dataset.path || state.targetFile || "";
      const row = {
        name,
        expected: options.expected || target,
        actual,
        scrollTopBefore: before,
        scrollTopAfter: restoreTest.scrollTop(),
        restoreCalls: state.restoreCalls,
        elapsedMs: Math.max(0, Date.now() - state.startedAt),
        rerenderLostPosition: false,
        cancelled: state.cancelled,
      };
      if (options.rerender) {
        const preserved = restoreTest.scrollTop();
        const rerenderPayload = restoreTest.render(rows);
        restoreTest.schedule(rerenderPayload, `${name}-rerender`);
        await restoreTest.waitFrames();
        row.rerenderLostPosition = state.restoreCalls !== 1 || restoreTest.scrollTop() !== preserved;
      }
      cases.push(row);
      return state;
    };

    await run("last-at-start", "folder/File 001.Space_V", ["folder/File 001.Space_V", "folder/File 002.Space_V"]);
    const longRows = Array.from({ length: 120 }, (_, index) => `folder/File ${String(index + 1).padStart(3, "0")}.Space_V`);
    await run("last-at-end", longRows[119], longRows);
    await run("closed-parent-opened", "folder/File 078.Space_V", longRows);
    await run("tree-after-progress", "folder/File 090.Space_V", longRows);
    await run("progress-after-tree", "folder/File 091.Space_V", longRows, { lastFileReady: false, treeBeforeLastFile: true });
    await run("refresh-route", "folder/File 078.Space_V", longRows);

    const stateA = makeState("folder/File 110.Space_V", { username: "user-a" });
    restoreTest.setState(stateA);
    const payloadA = restoreTest.render(longRows);
    restoreTest.schedule(payloadA, "user-a");
    const stateB = makeState("folder/File 005.Space_V", { username: "user-b" });
    restoreTest.setState(stateB);
    const payloadB = restoreTest.render(longRows);
    restoreTest.schedule(payloadB, "user-b");
    await restoreTest.waitFrames();
    cases.push({ name: "logout-a-login-b", expected: stateB.targetFile, actual: serverBrowserFocusedFilePath, scrollTopBefore: 0, scrollTopAfter: restoreTest.scrollTop(), restoreCalls: stateB.restoreCalls, oldRestoreCalls: stateA.restoreCalls, elapsedMs: Date.now() - stateB.startedAt, rerenderLostPosition: false });

    await run("deleted-last-file", "folder/Missing.Space_V", ["folder/File 040.Space_V", "folder/File 041.Space_V"], { expected: "folder/File 040.Space_V" });
    await run("version-rerender", "folder/File 080.Space_V", longRows, { rerender: true });
    await run("user-scroll-before-restore", "folder/File 100.Space_V", longRows, { userBeforeRestore: true });
    return { cases, oldTimerRace };
  });
  await browser.close();

  assert.strictEqual(result.oldTimerRace.calls, 0, "old one-shot timer must reproduce the missed-row failure");
  for (const row of result.cases) {
    if (row.name === "user-scroll-before-restore") {
      assert.strictEqual(row.cancelled, true, `${row.name}: user action must cancel pending restore`);
      assert.strictEqual(row.restoreCalls, 0, `${row.name}: restore must not fight the learner`);
      continue;
    }
    assert.strictEqual(row.actual, row.expected, `${row.name}: wrong restored file`);
    assert.strictEqual(row.restoreCalls, 1, `${row.name}: restore must run exactly once`);
    assert.strictEqual(Boolean(row.rerenderLostPosition), false, `${row.name}: rerender lost restored position`);
    if (row.name === "logout-a-login-b") assert.strictEqual(row.oldRestoreCalls, 0, "old user generation must not scroll");
  }
  console.log(JSON.stringify({ ok: true, oldTimerRace: result.oldTimerRace, cases: result.cases }, null, 2));
};

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
