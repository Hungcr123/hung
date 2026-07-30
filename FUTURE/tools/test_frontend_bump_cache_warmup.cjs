const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "05_screen_motion_layout.js"),
  "utf8",
);
const fetchSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "16_notices_vocabulary_missions.js"),
  "utf8",
);
const preloadSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js"),
  "utf8",
);

const restoreStart = source.indexOf("const restoreAuthSession = async () =>");
const restoreEnd = source.indexOf("\n      const handleAuthSubmit", restoreStart);
assert.ok(restoreStart >= 0 && restoreEnd > restoreStart, "restoreAuthSession source not found");

const restoreSource = source.slice(restoreStart, restoreEnd);
assert.match(
  source,
  /startLoginVaultWarmup\("submit"\)/,
  "frontend reload must rebuild login and tree preload caches",
);
assert.equal(
  (restoreSource.match(/const cacheWarmup = warmReloadSessionCaches\(\);/g) || []).length,
  2,
  "both reload-token and stored-token restore branches must warm caches",
);
const routeRestoreSource = fs.readFileSync(
  path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"),
  "utf8",
);
assert.match(
  routeRestoreSource,
  /routeAlreadyInLessonVault[\s\S]*?routeAlreadyInLessonVault \? "" : reloadState\.selectedFile/,
  "Lesson Vault reload must not restore stale Space file/process params",
);
assert.match(
  source,
  /routeIsLessonVault[\s\S]*?file: routeIsLessonVault \? "" : selectedFile[\s\S]*?process: routeIsLessonVault \? "" : mode/,
  "reload state must keep Lesson Vault routes free of stale file/process params",
);
assert.equal(
  (restoreSource.match(/const restoreTask = cacheWarmup\.then\(\(\) => \(/g) || []).length,
  2,
  "route restoration must wait until the cache warmup finishes",
);
assert.match(
  fetchSource,
  /cache: requestCacheMode/,
  "fetchServerJson must preserve an explicit browser cache mode",
);
assert.match(
  preloadSource,
  /fetchServerJson\("\/server-data\/tree-preload", \{[\s\S]*?cache: "no-cache"/,
  "tree preload must revalidate the machine cache by ETag",
);

console.log("frontend_bump_cache_warmup=ok restore_branches=2 preload_before_navigation=true tree_cache=etag_revalidate");
