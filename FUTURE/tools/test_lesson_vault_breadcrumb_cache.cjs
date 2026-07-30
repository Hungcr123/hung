const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "17_vocab_to_pdf_bootstrap.js"), "utf8");
const start = source.indexOf("function lessonVaultTaskOwnerForPath");
const end = source.indexOf("\n\n      // Home navigates only within Lesson Vault", start);
assert.ok(start >= 0 && end > start, "lessonVaultTaskOwnerForPath source not found");

function runtime({ username, admin, context = "" }) {
  const sandbox = {
    currentAuthUsername: username,
    currentAuthIsAdmin: admin,
    serverTaskOwnerContext: context,
    clean: (value) => String(value ?? "").trim(),
    normalizeTaskPath: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
    normalizeServerPathValue: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
    authUsernameMatches: (left, right) => String(left).toLowerCase() === String(right).toLowerCase(),
  };
  vm.createContext(sandbox);
  vm.runInContext(`${source.slice(start, end)}\n;globalThis.pickOwner = lessonVaultTaskOwnerForPath;`, sandbox);
  return sandbox.pickOwner;
}

const learner = runtime({ username: "vietanh", admin: false });
assert.equal(learner("", ""), "vietanh");
assert.equal(learner("common/Study", ""), "vietanh");
assert.equal(learner("common/Study", "teacher"), "teacher");

const admin = runtime({ username: "hung", admin: true, context: "vietanh" });
assert.equal(admin("", ""), "hung");
assert.equal(admin("common/Study", "vietanh"), "vietanh");
assert.equal(admin("hung/My Lessons", ""), "hung");

const cache = new Map([
  ["vietanh|user||vietanh", { path: "" }],
  ["vietanh|user|common/Study|vietanh", { path: "common/Study" }],
  ["vietanh|user|common/PDF/Destination|vietanh", { path: "common/PDF/Destination" }],
]);
let simulatedServerGets = 0;
for (let index = 0; index < 100; index += 1) {
  const targetPath = index % 2 ? "common/PDF/Destination" : "";
  const owner = learner(targetPath, "");
  const key = `vietanh|user|${targetPath}|${owner}`;
  if (!cache.has(key)) simulatedServerGets += 1;
}
assert.equal(simulatedServerGets, 0);

console.log("lesson_vault_breadcrumb_cache=ok path=common/PDF/Destination simulated_clicks=100 server_gets=0");
