const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"),
  "utf8",
);
const start = source.indexOf("const rememberLessonVaultFolder =");
const end = source.indexOf("\n\n      const formatServerFileSize", start);
assert.ok(start >= 0 && end > start, "rememberLessonVaultFolder source not found");

let storedFolder = null;
let queuedWrites = 0;
const sandbox = {
  serverLastFolderState: null,
  serverLastFileState: {},
  serverTaskOwnerContext: "hung",
  currentAuthUsername: "hung",
  normalizeServerPathValue: (value) => String(value ?? "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
  clean: (value) => String(value ?? "").trim(),
  normalizeLessonVaultFolderState: (value, owner) => {
    const row = value && typeof value === "object" ? value : {};
    const rowPath = String(row.path || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
    if (!rowPath) return null;
    return { ...row, path: rowPath, task_owner: String(row.task_owner || owner || "") };
  },
  getStoredLessonVaultFolderState: () => storedFolder,
  rememberLessonVaultFolderState: (value) => {
    storedFolder = { ...value };
    sandbox.serverLastFolderState = storedFolder;
    return storedFolder;
  },
  queueServerLastFileSync: () => { queuedWrites += 1; },
};
vm.createContext(sandbox);
vm.runInContext(`${source.slice(start, end)}\n;globalThis.rememberFolder = rememberLessonVaultFolder;`, sandbox);

sandbox.rememberFolder("common/PDF/Destination", "hung", "breadcrumb");
sandbox.rememberFolder("common/PDF/Destination", "hung", "breadcrumb");
sandbox.rememberFolder("common/PDF/Destination", "hung", "breadcrumb");
assert.equal(queuedWrites, 1, "same Destination breadcrumb must write only once");

sandbox.rememberFolder("common/PDF", "hung", "breadcrumb");
assert.equal(queuedWrites, 2, "a real folder change must persist once");

console.log("lesson_vault_folder_sync_dedupe=ok destination_clicks=3 writes=1 changed_folder_writes=1");
