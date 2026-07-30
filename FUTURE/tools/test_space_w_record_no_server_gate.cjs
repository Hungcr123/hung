"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const layout = fs.readFileSync("FUTURE/web/js_parts/05_screen_motion_layout.js", "utf8");
const runtime = fs.readFileSync("FUTURE/web/js_parts/07_audio_speak_runtime.js", "utf8");
const source = fs.readFileSync("FUTURE/web/js_parts/08_speak_question_input.js", "utf8");
const start = source.indexOf("const toggleSpeakRecording = async");
const end = source.indexOf("const grammarPosLabels =", start);
const toggle = source.slice(start, end);

assert.ok(start >= 0 && end > start);
assert.match(layout, /let speakAiCheckVoice = false/);
assert.match(runtime, /const readSpeakAiCheckPreference = \(\) =>/);
assert.match(runtime, /if \(value === "1" \|\| value === "on" \|\| value === "ai"\) return true;/);
assert.match(runtime, /\/\/ Whisper is opt-in; a missing preference must never gate Record on server AI\.\s+return false;/);
assert.doesNotMatch(toggle, /refreshServerSettings\(/, "Record must not wait for a live server settings request");
assert.match(toggle, /await startSpeakBrowserRecognition\(\)/);
assert.match(toggle, /await startSpeakRecording\(\)/);
assert.match(toggle, /speakAiCheckVoiceServerManaged/);

console.log("space_w_record_no_server_gate=ok default=whisper-off record=never-waits-for-settings");
