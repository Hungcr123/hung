"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const syncSource = fs.readFileSync("FUTURE/web/js_parts/13_translation_vocab_sync.js", "utf8");
const noticesSource = fs.readFileSync("FUTURE/web/js_parts/16_notices_vocabulary_missions.js", "utf8");
const routeSource = fs.readFileSync("FUTURE/server_parts/http_server/post_route_parts/05_vocab_progress_leaderboard.pyfrag", "utf8");
const repositorySource = fs.readFileSync("FUTURE/postgres/repositories/vocabulary.py", "utf8");

const fetchStart = syncSource.indexOf("const fetchVocabFileKeyMap = async");
const fetchEnd = syncSource.indexOf("const loadVocabLessonIndex = async", fetchStart);
const fetchSource = syncSource.slice(fetchStart, fetchEnd);
assert.ok(fetchStart >= 0 && fetchEnd > fetchStart);
assert.match(fetchSource, /user: clean\(user \|\| currentAuthUsername/);
assert.match(fetchSource, /vocab_stats/);
assert.match(fetchSource, /Date\.now\(\) - cachedStatsAt < 15000/);

const announceStart = noticesSource.indexOf("const announceSpaceVFileStats = async");
const announceEnd = noticesSource.indexOf("const questionInventoryUserKey =", announceStart);
const announceSource = noticesSource.slice(announceStart, announceEnd);
assert.ok(announceStart >= 0 && announceEnd > announceStart);
assert.match(announceSource, /learnerStats \|\| \(resolvedEntry\.vocab_stats/);
assert.match(announceSource, /renderSpaceVFileStatsChip\(rowNode, resolvedStats/);
assert.doesNotMatch(announceSource, /fetchSpaceVFileStatsForUser\(/, "file clicks must not fall back to the lesson-decoding stats route");

assert.match(routeSource, /server_database_vocab_file_key_stats/);
assert.match(routeSource, /target_user != viewer and not admin_view/);
assert.match(repositorySource, /def file_key_stats/);
assert.match(repositorySource, /word_key=ANY\(%s\)/);

console.log("lesson_vault_earn_chip_user=ok compact-key-stats=enabled stale-cache=15s");
