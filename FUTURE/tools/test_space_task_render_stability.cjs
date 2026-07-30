"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const source = fs.readFileSync("FUTURE/web/js_parts/16_notices_vocabulary_missions.js", "utf8");
const oldSource = fs.readFileSync("FUTURE/_backups/space_task_stability_20260724_1515/16_notices_vocabulary_missions.js", "utf8");
const css = fs.readFileSync("FUTURE/web/css_parts/05_question_core_cards.css", "utf8");

const oldHydrationStart = oldSource.indexOf("const hydrateLessonTaskProgress =");
const oldHydrationEnd = oldSource.indexOf("const hydrateVisibleLessonVaultFileProgress =", oldHydrationStart);
const oldHydration = oldSource.slice(oldHydrationStart, oldHydrationEnd);
assert.match(oldHydration, /lessonTaskPanelLastSignature = "";\s*renderLessonTaskPanel\(currentTaskPayload\);/);

const hydrationStart = source.indexOf("const hydrateLessonTaskProgress =");
const hydrationEnd = source.indexOf("const hydrateVisibleLessonVaultFileProgress =", hydrationStart);
const hydration = source.slice(hydrationStart, hydrationEnd);
assert.match(hydration, /lessonTaskProgressHydrationInflight\.has\(key\)/);
assert.match(hydration, /lessonTaskProgressHydrationFreshUntil\.get\(key\)/);
assert.match(hydration, /patchVisibleLessonTaskProgress\(task, taskStudy, override\)/);
assert.doesNotMatch(hydration, /lessonTaskPanelLastSignature = "";\s*renderLessonTaskPanel\(currentTaskPayload\);/);
assert.doesNotMatch(hydration, /renderLessonTaskPanel\(/, "progress hydration must never rebuild the task list");
assert.match(source, /lessonTaskRuntimeMetrics\.fullRenders \+= 1/);
assert.match(source, /lessonTaskRuntimeMetrics\.hydrationPatches \+= 1/);

const cardStart = source.indexOf('card.addEventListener("click", (event) => {', source.indexOf("const goButton = createLessonGoButton"));
const cardEnd = source.indexOf("serverTaskListNode.appendChild(card);", cardStart);
const cardClick = source.slice(cardStart, cardEnd);
assert.match(cardClick, /focusLessonVaultOnTask\(task, owner\)/);
assert.doesNotMatch(cardClick, /announceSpaceVFileStats/, "Space Task selection must not fetch/render Earn chips");

assert.match(css, /\.ft-task-list\s*\{[\s\S]*?overflow-anchor:\s*none;/);
assert.match(css, /\.ft-task-card\.is-pending\s*\{[\s\S]*?animation:\s*taskPendingElectric/);

console.log("space_task_render_stability=ok hydration_full_render=0 card_patch=in-place earn_request_on_card_click=0 original_motion=preserved");
