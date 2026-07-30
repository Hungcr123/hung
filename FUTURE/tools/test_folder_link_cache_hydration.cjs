const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const start = source.indexOf("const serverBrowserLinkedFolderSnapshotNeedsHydration");
const end = source.indexOf("\n\n      const patchLessonVaultCachedProgress", start);
assert.ok(start >= 0 && end > start, "linked-folder hydration helper not found");

const rows = new Map([
  ["hung", { payload: { entries: [{ type: "folder", path: "hung/Empower A1", linked: true, link_target: "common/Study/Empower A1" }] } }],
]);
const sandbox = {
  clean: (value) => String(value ?? "").trim(),
  normalizeServerPathValue: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
  normalizeTaskPath: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "").toLowerCase(),
  serverParentPathForFile: (value) => {
    const parts = String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "").split("/").filter(Boolean);
    parts.pop();
    return parts.join("/");
  },
  getCachedServerBrowserListRow: (relativePath) => rows.get(String(relativePath ?? "")) || null,
};
vm.createContext(sandbox);
vm.runInContext(`${source.slice(start, end)}\n;globalThis.needsHydration = serverBrowserLinkedFolderSnapshotNeedsHydration;`, sandbox);

const emptySnapshot = { manifest_snapshot: true, entries: [] };
assert.equal(sandbox.needsHydration("hung/Empower A1", "hung", emptySnapshot), true);
assert.equal(sandbox.needsHydration("hung/Empower A1/Unit 01", "hung", emptySnapshot), true);
assert.equal(sandbox.needsHydration("hung/Normal Empty", "hung", emptySnapshot), false);
assert.equal(sandbox.needsHydration("hung/Empower A1", "hung", { manifest_snapshot: false, entries: [] }), false);
assert.equal(sandbox.needsHydration("hung/Empower A1", "hung", { manifest_snapshot: true, entries: [{ path: "x" }] }), false);

console.log("folder_link_cache_hydration=ok empty_link_snapshot=fetch real_empty_payload=cache nested_link=fetch");
