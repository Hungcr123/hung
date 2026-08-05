const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..", "..");
const loadSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const syncSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "14_vocab_sync_tasks.js"), "utf8");
const transportSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");
const eventSource = fs.readFileSync(path.join(root, "FUTURE", "web", "js_parts", "21_progress_bootstrap_events.js"), "utf8");

// Added 2026-07-20: couple Space_W payload/ETag, retry cache loss, and invalidate after writes.
assert.match(loadSource, /currentSpaceWCache\.serverPayload = payload/);
assert.match(loadSource, /currentSpaceWCache\.serverEtag = clean\(preloaded\.etag \|\| ""\)/);
assert.match(loadSource, /serverPayload: null/);
assert.match(loadSource, /serverEtag: ""/);
assert.match(syncSource, /fetchProgressJsonFast\(`\/space-w\/progress\?\$\{query\.toString\(\)\}`, cachedRow, timeoutMs\)/);
assert.match(syncSource, /currentSpaceWCache\.serverPayload = payload/);
assert.match(syncSource, /currentSpaceWCache\.serverEtag = clean\(result\.etag \|\| ""\)/);
assert.match(syncSource, /currentSpaceWCache\.serverPayload = null/);
assert.match(syncSource, /currentSpaceWCache\.serverEtag = ""/);
assert.match(transportSource, /headers\["If-None-Match"\] = clean\(cachedRow\.etag\)/);
assert.match(transportSource, /response\.status === 304/);
assert.match(transportSource, /delete headers\["If-None-Match"\]/);
assert.match(transportSource, /\^\\\/space-\(\?:v\|w\|q\)\\\/progress/);
assert.match(transportSource, /for \(const base of candidates\)/);
assert.match(transportSource, /space === "Space_W" && typeof spaceWProgressOverrideFromRecord === "function"/);
assert.match(transportSource, /compact Vault rings are display summaries, not resumable checkpoints/);
assert.match(eventSource, /continuePreparedLessonFromSavedProgress\(\{ skipAudioPrepare: true \}\)/);
// Added 2026-08-03: Continue reuses the click-time progress preload and never waits on a duplicate GET.
const continueStart = loadSource.indexOf("const continuePreparedLessonFromSavedProgress =");
const continueEnd = loadSource.indexOf("const waitPreparedReloadPayload =", continueStart);
const continueSource = loadSource.slice(continueStart, continueEnd);
assert.match(continueSource, /progress-preload-pending/);
assert.match(continueSource, /serverProgressResult/);
assert.doesNotMatch(continueSource, /await refreshSpaceWServerProgress/);
assert.match(loadSource, /deferInitialProgressSave/);
assert.match(eventSource, /if \(!state\.deferInitialProgressSave\)/);
assert.match(eventSource, /const createSpaceWProgressOperationId = \(\) =>/);
assert.match(eventSource, /snapshot\.syncOperationId = createSpaceWProgressOperationId\(\)/);
assert.match(syncSource, /syncOperationId: clean\(/);
assert.match(syncSource, /space-w\/progress\?client_source=space_w_progress_save&response=compact-v1/);
assert.match(syncSource, /canonicalRecord = record\.state/);
assert.match(loadSource, /space-w\/progress\?client_source=offline_outbox&response=compact-v1/);

console.log("space_w_progress_get_client=ok conditional_refresh=true cache_loss_retry=true post_invalidation=true sequential_origin=true continue_preload=true duplicate_wait=false deferred_stale_save=true vault_preload=true operation_id=true compact_ack=true");
