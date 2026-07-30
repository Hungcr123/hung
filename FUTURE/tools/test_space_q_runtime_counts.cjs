const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "web", "js_parts", "11_question_guidance_picture_reveal.js"), "utf8");
const start = source.indexOf("const currentQuestionItem =");
const end = source.indexOf("const updateQuestionProgressLabel =", start);
assert.ok(start >= 0 && end > start, "Space_Q runtime count block not found");

const questions = [
  { guidance_tree: { items: [
    { text: "a", children: [{ title: "1" }, { title: "2" }, { title: "3" }] },
    { text: "b", children: [{ title: "1" }, { title: "2" }, { title: "3" }] },
  ] } },
  { guidance_tree: { items: [
    { text: "a", children: [{ title: "1" }, { title: "2" }, { title: "3" }] },
    { text: "b", children: [{ title: "1" }, { title: "2" }] },
  ] } },
];
const context = {
  questionNodes: [
    { cards: { questions } },
    { cards: { questions: [{}] } },
  ],
  questionCurrentQuestions: questions,
  questionQuestionIndex: 0,
  questionPayload: { order: "sequence" },
  questionQueue: [0, 1],
  currentNodeIndex: 0,
  questionFirstTryCorrectKeys: new Set(),
  qNextButton: { disabled: true },
  questionPictureAnswerLayer: null,
  questionRootInfoPromptNode: () => null,
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nthis.stats = questionProgressStats;`, context);

assert.deepEqual([context.stats().done, context.stats().total], [0, 20]);
context.qNextButton.disabled = false;
assert.deepEqual([context.stats().done, context.stats().total], [9, 20]);
context.questionQuestionIndex = 1;
assert.deepEqual([context.stats().done, context.stats().total], [18, 20]);
console.log("space_q_runtime_counts=ok initial=0/20 first_question=9/20 first_topic=18/20");
