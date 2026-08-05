const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const readPart = (name) => fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", name), "utf8");
const vocabSource = readPart("14_vocab_sync_tasks.js");
const translationSource = readPart("13_translation_vocab_sync.js");
const vaultSource = readPart("17_vocab_to_pdf_bootstrap.js");
const browserSource = readPart("20_pdf_page_progress.js");
const htmlSource = fs.readFileSync(path.join(__dirname, "..", "web", "future_split.html"), "utf8");

assert.match(htmlSource, /id="ft-vault-button"[^>]+aria-label="Exit"[^>]+title="Exit"/);
assert.match(htmlSource, /ft-server-back-label">Home</);

const flushStart = vocabSource.indexOf("window.__ftFlushSpaceVProgressBeforeBack =");
const flushEnd = vocabSource.indexOf("window.__ftKeepaliveSpaceVProgress =", flushStart);
assert.ok(flushStart >= 0 && flushEnd > flushStart, "Space_V back flush source not found");
const flushSource = vocabSource.slice(flushStart, flushEnd);
assert.match(flushSource, /saveVocabProgressNow\(\{ queueServerSync: false \}\)/);
assert.equal((flushSource.match(/sendVocabServerProgress\(/g) || []).length, 1, "Back must send one direct progress delta");
const saveStart = vocabSource.indexOf("const saveVocabProgressNow =");
const saveEnd = vocabSource.indexOf("const saveVocabProgressCheckpointNow =", saveStart);
const saveSource = vocabSource.slice(saveStart, saveEnd);
assert.doesNotMatch(saveSource, /loadGate\.classList\.contains\("is-hidden"\)/, "Active Space_V progress must not depend on load-gate CSS state");

const loadStart = browserSource.indexOf("const loadServerDataPath = async");
const loadEnd = browserSource.indexOf("const openServerBrowserAfterAuth =", loadStart);
assert.ok(loadStart >= 0 && loadEnd > loadStart, "loadServerDataPath source not found");
const loadSource = browserSource.slice(loadStart, loadEnd);
const routeFlushStart = loadSource.indexOf("__ftFlushSpaceVProgressBeforeBack");
const routeFlushEnd = loadSource.indexOf("const loadKey =", routeFlushStart);
const routeFlushSource = loadSource.slice(routeFlushStart, routeFlushEnd);
assert.doesNotMatch(routeFlushSource, /forceFresh\s*=\s*true|clearServerBrowserListCache/);

const returnStart = vaultSource.indexOf("const returnToServerFileSelection =");
const returnEnd = vaultSource.indexOf("const setServerBrowserBackControl", returnStart);
assert.ok(returnStart >= 0 && returnEnd > returnStart, "group Back source not found");
const returnSource = vaultSource.slice(returnStart, returnEnd);
assert.doesNotMatch(returnSource, /openServerBrowserAfterAuth\(/, "group Back must not race a second folder restore");
assert.match(returnSource, /updateFutureAppRoute\("lesson_vault"/);
assert.doesNotMatch(returnSource, /clearVocabAudioCache\(/, "Exit must not call the removed audio-cache helper");
assert.doesNotMatch(translationSource, /clearVocabAudioCache\(/, "Space transitions must invalidate audio preload by token");
assert.ok(
  returnSource.indexOf('updateFutureAppRoute("lesson_vault"') < returnSource.indexOf("hideCompletionGate()"),
  "Exit must switch to Lesson Vault before optional Space cleanup can throw",
);
assert.match(returnSource, /options\.vocabProgressRecord/);
assert.match(returnSource, /vocabProgressOverrideFromRecord\(vocabProgressRecordForReturn\)/);
assert.ok((returnSource.match(/\{ force: true \}/g) || []).length >= 2, "Exit snapshot must force-replace stale completion cache");
assert.match(returnSource, /localCacheOnly: hasReturnFolderCache/);
assert.match(returnSource, /space_v_group_back_cache_miss/);
assert.match(returnSource, /const forceFreshProgress = Boolean\(options\.forceFreshProgress\)/);
assert.match(returnSource, /loadServerDataPath\(refreshTree, false/);
assert.match(returnSource, /fresh: forceFreshProgress/);
assert.doesNotMatch(returnSource, /setTimeout\([\s\S]*finalReturnOverride[\s\S]*900\)/, "Exit must not replay a mutable delayed progress snapshot");
assert.ok((returnSource.match(/rememberFile: false/g) || []).length >= 3, "Back highlighting must not rewrite last-file");
assert.ok((returnSource.match(/updateRoute: false/g) || []).length >= 3, "Back highlighting must not restore file/process route params");

const eventsSource = readPart("21_progress_bootstrap_events.js");
const vaultStart = eventsSource.indexOf("if (vaultButton)");
const vaultEnd = eventsSource.indexOf("if (cupButton)", vaultStart);
const vaultBackSource = eventsSource.slice(vaultStart, vaultEnd);
assert.match(vaultBackSource, /__ftFlushSpaceVProgressBeforeBack/);
assert.match(vaultBackSource, /__ftPeekSpaceVProgressBeforeBack/);
assert.ok(
  vaultBackSource.indexOf("__ftPeekSpaceVProgressBeforeBack") < vaultBackSource.indexOf("__ftFlushSpaceVProgressBeforeBack"),
  "Exit must capture the local run before the durable POST response merges history",
);
assert.match(vaultBackSource, /void window\.__ftFlushSpaceVProgressBeforeBack/);
assert.doesNotMatch(vaultBackSource, /await window\.__ftFlushSpaceVProgressBeforeBack/);
assert.match(vaultBackSource, /returnToServerFileSelection\(\{ vocabProgressRecord, questionProgressRecord \}\)/);
assert.doesNotMatch(vaultBackSource, /refreshLessonVaultItemStudyFromServer/);
assert.doesNotMatch(vaultBackSource, /forceFreshProgress/);

console.log("space_v_group_back_cache=ok progress_posts=1 exit_server_gets=0 normal_cache_first=true");
