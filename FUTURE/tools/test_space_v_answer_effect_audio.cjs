const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const scheduler = fs.readFileSync(path.join(root, "web", "js_parts", "06_spacew_audio_scheduler.js"), "utf8");
const vocab = fs.readFileSync(path.join(root, "web", "js_parts", "12_question_translation_loader.js"), "utf8");

for (const marker of [
  "Sound/fx-true_a76ad961cb10db7ab6c8a928b2581711b5ae65b9.mp3",
  "Sound/fx-false_1ee7795e2be3b283e45d8f6b3e1a0e166bb6d4cc.mp3",
  "const lessonEffectClip = (name) =>",
  "const effect = lessonEffectClip(key);",
  "void playEffectSoundAsync(name);",
  "immediateUserGesture: true",
  "{ ...DEFAULT_LESSON_EFFECTS, ...(lessonEffects || {}) }",
]) {
  if (!scheduler.includes(marker)) {
    throw new Error(`Missing answer-effect fallback marker: ${marker}`);
  }
}

const drillStart = vocab.indexOf("const checkVocabDrillAnswer = async");
const shuffleStart = vocab.indexOf("const checkVocabShuffleAnswer = async", drillStart);
const drillBody = vocab.slice(drillStart, shuffleStart);
if (!vocab.includes("const playVocabFeedbackSound = (name) => playGeneratedEffectTone(name)")) {
  throw new Error("Space_V must start answer feedback without waiting for MP3/cache fetches.");
}
if (!vocab.includes("played ? true : playEffectSoundAsync(name)")) {
  throw new Error("Space_V immediate feedback must retain the authenticated MP3 fallback.");
}
if (!drillBody.includes('playVocabFeedbackSound("false")') || !drillBody.includes('playVocabFeedbackSound("true")')) {
  throw new Error("Space_V Drill must play both false and true feedback effects.");
}
if ((vocab.match(/playVocabFeedbackSound\("(?:true|false)"\)/g) || []).length < 8) {
  throw new Error("Space_V Probe, Drill, and Shuffle feedback paths are incomplete.");
}

console.log("space_v_answer_effect_audio=ok immediate_tone=true mp3_fallback=true probe_drill_shuffle=true");
