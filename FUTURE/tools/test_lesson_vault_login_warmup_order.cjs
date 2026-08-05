const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const authSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "05_screen_motion_layout.js"), "utf8");
const warmupStart = authSource.indexOf("const authVaultWarmupPromise =");
const openStart = authSource.indexOf("const openVaultAfterAuth =", warmupStart);
assert.ok(warmupStart >= 0 && openStart > warmupStart, "warmup must start before the first Vault open is scheduled");
assert.match(authSource.slice(openStart, openStart + 900), /await waitForLoginVaultWarmup\(username, 900\)/);

const renderSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");
const start = renderSource.indexOf("const schedulePostAuthLessonVaultHydration =");
const end = renderSource.indexOf("const handleFutureRouteNavigation =", start);
assert.ok(start >= 0 && end > start, "post-auth hydration function not found");

let resolveWarmup;
const warmupPromise = new Promise((resolve) => {
  resolveWarmup = resolve;
});
const calls = [];
const context = {
  clean: (value) => String(value ?? "").trim(),
  currentAuthUsername: "hungcr",
  serverBrowserPath: "common/PDF",
  shouldHydrateDeferredTaskBoardImmediately: () => false,
  scheduleDeferredTaskBoardHydrate: () => calls.push("task"),
  hydrateDeferredTaskBoardNow: () => calls.push("task-now"),
  prefetchServerBrowserChildFolders: () => calls.push("prefetch"),
  loadServerDataPath: async (_path, _keepOpen, _owner, options) => calls.push(options),
  Promise,
  window: {
    requestIdleCallback: (callback) => callback(),
    setTimeout: (callback) => callback(),
  },
};
vm.createContext(context);
vm.runInContext(`${renderSource.slice(start, end)}\nglobalThis.__schedule = schedulePostAuthLessonVaultHydration;`, context);

context.__schedule({ path: "common/PDF", entries: [] }, "hungcr", warmupPromise);
assert.deepEqual(calls, [], "cached Vault payload must not rerender before the login snapshot warmup settles");
resolveWarmup({ status: "ready" });

setImmediate(() => {
  const localReload = calls.find((row) => row && typeof row === "object" && row.localCacheOnly === true);
  assert.ok(localReload, "warmup completion must trigger one local-cache Vault merge/render");
  assert.equal(localReload.skipBackgroundVerify, true);
  assert.equal(localReload.skipTaskBoardHydrate, true);
  console.log("lesson_vault_login_warmup_order=ok first_paint_waits=true late_snapshot_rerender=true network_progress_gets=0");
});
