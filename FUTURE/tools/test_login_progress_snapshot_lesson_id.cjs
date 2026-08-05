const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "13_translation_vocab_sync.js"), "utf8");
const start = source.indexOf("const applyLessonVaultProgressSnapshotToEntry =");
const end = source.indexOf("const applyLessonVaultProgressSnapshotToPayload =", start);
assert.ok(start >= 0 && end > start, "snapshot entry merge function not found");
const mergeSource = source.slice(start, end);
assert.match(mergeSource, /lessonVaultEntryProgressSpace\(entry\)/);
assert.match(mergeSource, /entry\.lesson_id, entry\.lessonId, entry\.file_id, entry\.fileId/);
assert.match(mergeSource, /`space:\$\{entrySpace\.toLowerCase\(\)\}:id:\$\{value\}`/);
assert.match(mergeSource, /lessonVaultProgressSnapshotForPaths\(paths, entrySpace\)/);

const lookupStart = source.indexOf("const lessonVaultProgressSnapshotForPaths =");
assert.ok(lookupStart >= 0 && lookupStart < start, "snapshot lookup function not found");
const lookupSource = source.slice(lookupStart, start);
assert.match(lookupSource, /lessonVaultProgressSnapshotSpace\(candidate\) === normalizedExpectedSpace/);
assert.match(source, /itemSpace \? `space:\$\{itemSpace\.toLowerCase\(\)\}:id:\$\{value\}`/);
assert.match(source, /let lessonVaultProgressSnapshotGeneration = 0/);
assert.match(source, /lessonVaultProgressSnapshotGeneration \+= 1/);
assert.match(source, /source\.__ftLessonVaultProgressSnapshotGeneration === lessonVaultProgressSnapshotGeneration/);
assert.match(source, /value: lessonVaultProgressSnapshotGeneration/);

const renderSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "20_pdf_page_progress.js"), "utf8");
const authSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "05_screen_motion_layout.js"), "utf8");
assert.match(renderSource, /if \(typeof applyLessonVaultProgressSnapshotToPayload === "function"\) \{/);
assert.doesNotMatch(renderSource, /&& !\(payload && payload\.__ftLessonVaultProgressSnapshotApplied\)/);
assert.match(authSource, /const authVaultWarmupPromise = typeof startLoginVaultWarmup === "function"/);
assert.match(authSource, /await waitForLoginVaultWarmup\(username, 900\)/);
assert.match(renderSource, /const schedulePostAuthLessonVaultHydration = \(payload = null, targetOwner = "", warmupPromise = null\)/);
assert.match(renderSource, /await Promise\.resolve\(warmupPromise\)\.catch\(\(\) => null\)/);

const taskSource = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "16_notices_vocabulary_missions.js"), "utf8");
assert.match(taskSource, /`space:\$\{space\.toLowerCase\(\)\}:id:\$\{lessonId\.toLowerCase\(\)\}`/);
assert.match(taskSource, /\], space\);/);
assert.doesNotMatch(taskSource, /lessonVaultProgressSnapshotForPaths\(\[\s*lessonId \? `id:/);

console.log("login_progress_snapshot_lesson_id=ok space_namespaced=true cross_space_guard=true generation_reapply=true");
