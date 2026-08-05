"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const source = fs.readFileSync("FUTURE/web/js_parts/16_notices_vocabulary_missions.js", "utf8");
const start = source.indexOf("const hydrateVisibleLessonVaultFileProgress =");
const end = source.indexOf("const renderLessonTaskPanel =", start);
assert.ok(start >= 0 && end > start, "visible Lesson Vault hydration block not found");

const hydration = source.slice(start, end);
assert.match(hydration, /if \(localOverride\)/, "tree/login progress must patch the local override even with a canonical lesson ID");
assert.match(hydration, /authoritative New Run state/, "missing snapshot progress must remain an authoritative local New Run");
assert.doesNotMatch(
  hydration,
  /fetchServerProgressForEntry|refreshLessonVaultItemStudyFromServer|getCachedServerBrowserListRow|renderServerDataList|setTimeout\(/,
  "rendering visible Vault cards must not schedule per-file progress/item-study requests or a server-driven rerender",
);

console.log("lesson_vault_visible_progress_local_only=ok per_file_progress_gets=0 item_study_gets=0 render_source=login_tree_ram");
