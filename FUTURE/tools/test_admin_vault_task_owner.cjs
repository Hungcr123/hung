const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..", "..");
const ownerSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js"), "utf8");
const taskSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");
const panelSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");
const match = ownerSource.match(/function lessonVaultTaskOwnerForPath[\s\S]*?\n      }\n\n      \/\/ Home navigates/);
if (!match) throw new Error("lessonVaultTaskOwnerForPath not found");

const context = {
  clean: (value) => String(value || "").trim(),
  normalizeTaskPath: (value) => String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "").toLowerCase(),
  normalizeServerPathValue: (value) => String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
  authUsernameMatches: (left, right) => String(left || "").toLowerCase() === String(right || "").toLowerCase(),
  currentAuthIsAdmin: true,
  currentAuthUsername: "hung",
  serverTaskOwnerContext: "hung",
};
vm.createContext(context);
vm.runInContext(match[0].replace(/\n\n      \/\/ Home navigates[\s\S]*$/, ""), context);

const resolve = context.lessonVaultTaskOwnerForPath;
if (resolve("quynh", "hung", { admin: true, username: "hung" }) !== "quynh") {
  throw new Error("stale admin owner did not resolve to selected user folder");
}
if (resolve("common/Study", "quynh", { admin: true, username: "hung" }) !== "quynh") {
  throw new Error("Common did not retain selected target user");
}
if (resolve("hung", "hung", { admin: true, username: "hung" }) !== "hung") {
  throw new Error("admin self Vault owner changed");
}
if (!taskSource.includes('payload.task_owner = payloadTaskOwner;')) {
  throw new Error("render payload owner is not canonicalized");
}
if (!taskSource.includes('loadLessonTasks(targetOwner, { fresh: true })')) {
  throw new Error("deferred task hydration still relies on an empty local cache");
}
if (!taskSource.includes('clearLessonTaskPanelCacheForOwner(targetOwner)')) {
  throw new Error("task hydration still clears every user cache");
}
if (!panelSource.includes('if (localCacheOnly || (!fresh && cacheAge < LESSON_TASK_PANEL_REFRESH_MIN_MS))')) {
  throw new Error("fresh task hydration can still be satisfied by a stale empty cache");
}

console.log(JSON.stringify({
  ok: true,
  direct_user_folder_owner: resolve("quynh", "hung", { admin: true, username: "hung" }),
  common_target_owner: resolve("common/Study", "quynh", { admin: true, username: "hung" }),
  deferred_fetch: "fresh-target-only",
}, null, 2));
