"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const source = fs.readFileSync("FUTURE/web/js_parts/20_pdf_page_progress.js", "utf8");
const start = source.indexOf("const serverEntryIsAdminRoot =");
const end = source.indexOf("const lastFilePath = getStoredServerFile();", start);
const section = source.slice(start, end);

assert.ok(start >= 0 && end > start);
assert.match(section, /payload\.admin && currentAuthIsAdmin && adminTargetOwner/);
assert.match(section, /const isCommonFolder = Boolean\(/);
assert.match(section, /entryPath\.endsWith\("\/common"\)/);
assert.match(section, /return Boolean\(payload\.admin && currentAuthIsAdmin\)/);

console.log("lesson_vault_common_visibility=ok learner-nested-common=hidden admin-task-view=preserved");
