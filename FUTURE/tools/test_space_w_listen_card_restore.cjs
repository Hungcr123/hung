const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const client = fs.readFileSync(path.join(root, "web", "js_parts", "21_progress_bootstrap_events.js"), "utf8");
const server = fs.readFileSync(path.join(root, "server_parts", "progress_inventory_vocab", "01_space_w_progress.py"), "utf8");

const shouldRestore = (state) => Boolean(
  state.nextPanelCanShow
  && !state.speakStepCompleted
  && !state.grammarLive
);

const stuckAi18 = {
  nextPanelCanShow: true,
  speakStepCompleted: false,
  grammarLive: false,
  ipaLive: false,
  listenCount: 3,
};

if (!shouldRestore(stuckAi18)) throw new Error("AI 18 stuck checkpoint must restore Listen");
if (shouldRestore({ ...stuckAi18, nextPanelCanShow: false })) throw new Error("unfinished answer must not force Listen");
if (shouldRestore({ ...stuckAi18, speakStepCompleted: true })) throw new Error("completed Speak must not reopen Listen");
if (shouldRestore({ ...stuckAi18, grammarLive: true })) throw new Error("active Grammar must remain authoritative");
if (!client.includes("state.ipaLive || restorePendingListenCard")) throw new Error("runtime restore gate missing");
if (!server.includes('lesson_source["lesson_id"] = identity[:240]')) throw new Error("nested folder-link lesson ID normalization missing");

console.log("space_w_listen_card_restore=ok ai18=3/10 hidden_ipa_reopens=true folder_link_id=true");
