"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const syncSource = fs.readFileSync("FUTURE/web/js_parts/13_translation_vocab_sync.js", "utf8");
const taskSource = fs.readFileSync("FUTURE/web/js_parts/16_notices_vocabulary_missions.js", "utf8");
const vaultSource = fs.readFileSync("FUTURE/web/js_parts/20_pdf_page_progress.js", "utf8");

const focusStart = taskSource.indexOf("const focusLessonVaultOnTask =");
const focusEnd = taskSource.indexOf("const getStoredServerRecentFile =", focusStart);
const focusSource = taskSource.slice(focusStart, focusEnd);
const cardStart = taskSource.indexOf('card.addEventListener("click", (event) => {', taskSource.indexOf("const goButton = createLessonGoButton"));
const cardEnd = taskSource.indexOf("serverTaskListNode.appendChild(card);", cardStart);
const cardSource = taskSource.slice(cardStart, cardEnd);

assert.ok(focusStart >= 0 && cardStart >= 0);
assert.doesNotMatch(focusSource, /rememberServerFile\(/, "selecting a task must not change the last opened lesson");
assert.match(focusSource, /parentAlreadyRendered/);
assert.match(focusSource, /setSelectedTaskPath[\s\S]*is-task-focus-burst/);
assert.match(taskSource, /renderSpaceVFileStatsChip[\s\S]*replayTaskFocusedStatsChipBurst\(rowNode\)/, "dynamic New/Earn chips must replay the task-focus burst after rendering");
assert.match(focusSource, /skipTaskBoardHydrate: true/);
assert.match(focusSource, /skipBackgroundVerify: true/);
assert.match(focusSource, /skipChildPrefetch: true/);
assert.match(focusSource, /skipFolderPersist: true/);
assert.match(focusSource, /task\.effective_path/);
assert.match(focusSource, /task\.link_target/);
assert.match(
  focusSource,
  /const learningPath = taskLearningPath\(task\) \|\| filePath;[\s\S]*const parentPath = serverParentPathForFile\(learningPath\) \|\| canonicalFolder/,
  "nested task files must open their direct Lesson Vault folder before falling back to the assigned task folder",
);
assert.match(focusSource, /lessonTaskRowIsPdf\(task\)[\s\S]*\.space_pdf/, "PDF task paths must match the canonical .space_pdf vault row");
assert.match(focusSource, /selectServerLessonVaultEntryFromPayload/);
assert.match(focusSource, /replayFocusedVaultRow/);
assert.match(focusSource, /rememberFile: false/);
assert.match(focusSource, /skipProgressPrefetch: true/);
assert.match(focusSource, /skipFileStats: false/, "task focus should render cached local chips without a server stats read");
assert.match(focusSource, /loadServerDataPath\(parentPath[\s\S]*localCacheOnly: true/, "task focus must open the target folder from the login tree cache");
assert.match(focusSource, /serverLessonProgressPrefetchTimer[\s\S]*__ftLessonVaultProgressHydrationPausedUntil/, "task focus must cancel stale delayed progress reads");
assert.match(taskSource, /setSelectedTaskPath[\s\S]*__ftLessonVaultLocalRouteUntil/, "row selection must mark route replay local-only");
assert.match(vaultSource, /loginVaultTreeFolderPayloadFromCache[\s\S]*rememberServerBrowserList/, "local-cache folder navigation must reuse login tree rows");
const homeStart = vaultSource.indexOf("const openServerBrowser =");
const homeEnd = vaultSource.indexOf("const openServerBrowserAfterAuth =", homeStart);
assert.ok(homeStart >= 0 && homeEnd > homeStart);
assert.match(vaultSource.slice(homeStart, homeEnd), /localCacheOnly:\s*true/);
assert.doesNotMatch(vaultSource.slice(homeStart, homeEnd), /syncServerLastFileFromServer/);
assert.match(fs.readFileSync("FUTURE/web/js_parts/20_pdf_page_progress.js", "utf8"), /is-task-focus-burst/, "vault selection should trigger the chip burst");
const vaultCss = fs.readFileSync("FUTURE/web/css_parts/05_question_core_cards.css", "utf8");
assert.match(vaultCss, /ft-lesson-vault-motion-off[\s\S]*is-task-focus-burst[\s\S]*animation:\s*serverPinFloat[^;]*!important/, "task chip animation must override Lesson Vault motion suppression");
assert.match(vaultCss, /is-task-focus-burst \.ft-server-chip:nth-child\(n \+ 5\)/, "all appended Earn chips must receive the task-focus stagger");
assert.match(fs.readFileSync("FUTURE/web/js_parts/20_pdf_page_progress.js", "utf8"), /if \(!entry\)[\s\S]*document\.querySelectorAll\("\.ft-server-item\.is-file"\)/, "focus must fall back to the rendered row when compact payload omits the entry");
assert.doesNotMatch(cardSource, /rememberServerFile\(/, "card selection must stay local-only");
const rowSelectionStart = vaultSource.indexOf('item.addEventListener("click", (event) => {');
const rowSelectionEnd = vaultSource.indexOf('item.addEventListener("contextmenu"', rowSelectionStart);
assert.ok(rowSelectionStart >= 0 && rowSelectionEnd > rowSelectionStart);
assert.doesNotMatch(vaultSource.slice(rowSelectionStart, rowSelectionEnd), /rememberServerFile\(/, "Lesson Vault row selection must not update last-file state");

const scrollStart = taskSource.indexOf("const serverFileNodeForPaths =");
const scrollEnd = taskSource.indexOf("const highlightLessonVaultTaskFolder =", scrollStart);
const scrollSource = taskSource.slice(scrollStart, scrollEnd);
assert.ok(scrollStart >= 0 && scrollEnd > scrollStart);
assert.match(scrollSource, /item\.dataset\.effectivePath/);
assert.match(scrollSource, /item\.dataset\.linkTarget/);
assert.match(scrollSource, /item\.dataset\.linkedPath/);

const vaultSelectMarker = 'setLoadStatus("File selected. Use Let\'s go to open this lesson.");';
const vaultSelectAt = vaultSource.lastIndexOf(vaultSelectMarker);
const vaultSelectStart = vaultSource.lastIndexOf('setSelectedTaskPath(entry.path);', vaultSelectAt);
const vaultSelectSource = vaultSource.slice(vaultSelectStart, vaultSelectAt + vaultSelectMarker.length);
const vaultGoStart = vaultSource.indexOf('const goButton = createLessonGoButton();');
const vaultGoEnd = vaultSource.indexOf('fileActions.appendChild(goButton);', vaultGoStart);
const vaultGoSource = vaultSource.slice(vaultGoStart, vaultGoEnd);
const vaultLoaderStart = vaultSource.indexOf('const loadServerLessonFile =');
const vaultLoaderEnd = vaultSource.indexOf('const closeServerBrowser =', vaultLoaderStart);
const vaultLoaderSource = vaultSource.slice(vaultLoaderStart, vaultLoaderEnd);
assert.ok(vaultSelectStart >= 0 && vaultSelectAt > vaultSelectStart && vaultGoStart >= 0 && vaultGoEnd > vaultGoStart);
assert.doesNotMatch(vaultSelectSource, /rememberServerFile\(/, "Vault selection must not update last-file state");
assert.doesNotMatch(vaultSelectSource, /syncNow:\s*true/, "Vault selection must not POST last-file");
assert.doesNotMatch(vaultSelectSource, /scheduleServerLessonProgressPrefetch/, "Vault selection must not GET progress");
assert.doesNotMatch(vaultSelectSource, /announceSpaceVFileStats/, "Vault selection must not request reward stats");
assert.doesNotMatch(vaultGoSource, /rememberServerFile\(/, "Let's go must not duplicate the loader's last-file sync");
assert.match(vaultGoSource, /loadServerLessonFile\(entry\)/, "Let's go must delegate the actual open");
assert.match(vaultLoaderSource, /entryOpenOwnsLastFileSync/, "PDF/Picture openers must own their single last-file sync");
assert.match(vaultLoaderSource, /if \(!entryOpenOwnsLastFileSync\)[\s\S]*rememberServerFile\(/, "other lesson loaders must still sync once");
assert.match(syncSource, /serverLastFileSemanticSignature/);
assert.match(syncSource, /serverLastFilePostPromise/);
assert.match(syncSource, /serverLastFileRetryAfter = Date\.now\(\) \+ 5000/);
assert.match(syncSource, /folder focus is instant locally[\s\S]*queueServerLastFileSync\(900\)/);

const queueStart = syncSource.indexOf("const queueServerLastFileSync =");
const queueEnd = syncSource.indexOf("const getStoredServerPath =", queueStart);
const queueSource = syncSource.slice(queueStart, queueEnd).replace(
  "const queueServerLastFileSync =",
  "queueServerLastFileSync =",
);
assert.ok(queueStart >= 0 && queueEnd > queueStart);

let nextTimerId = 0;
const timers = new Map();
const window = {
  clearTimeout(id) {
    timers.delete(id);
  },
  setTimeout(callback, delay) {
    nextTimerId += 1;
    timers.set(nextTimerId, { callback, delay });
    return nextTimerId;
  },
};
let serverLastFileSyncTimer = 0;
let serverLastFileRetryAfter = 0;
let postCount = 0;
let queueServerLastFileSync;
const postServerLastFileState = async () => {
  postCount += 1;
};
eval(queueSource);

for (let index = 0; index < 100; index += 1) {
  queueServerLastFileSync(900);
}
assert.equal(timers.size, 1, "rapid folder changes must retain only the final sync timer");
const [{ callback, delay }] = timers.values();
assert.equal(delay, 900);
callback();
assert.equal(postCount, 1, "the settled folder selection must POST once");

console.log("space_task_click_cache=ok task_card=0-server vault_select=0-server lets_go=open+sync manual_folder_debounce=100-to-1 last_file=actual-open-only");
