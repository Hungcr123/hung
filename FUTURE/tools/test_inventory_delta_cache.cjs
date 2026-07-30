"use strict";

const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("FUTURE/web/js_parts/16_notices_vocabulary_missions.js", "utf8");
const start = source.indexOf("      const normalizeQuestionInventoryState =");
const end = source.indexOf("      const ensureQuestionInventoryHud =", start);
if (start < 0 || end < 0) {
  throw new Error("Inventory cache helpers not found");
}

const context = {
  clean: (value) => String(value || "").trim(),
  preserveQuestionText: (value) => String(value || ""),
  questionRewardConfig: { crystal: { name: "Crystal", use: "Reward" } },
};
vm.createContext(context);
vm.runInContext(`${source.slice(start, end)}\nthis.normalize = normalizeQuestionInventoryState; this.applyDelta = applyQuestionInventoryDelta;`, context);

const oldEvents = Array.from({ length: 600 }, (_, index) => `event-${index}`);
const base = context.normalize({
  items: { gold: { id: "gold", quantity: 11 } },
  events: oldEvents,
  pending: [{ event_id: "pending-1" }],
});
if (base.events.length !== 512) {
  throw new Error(`Expected 512 local event keys, got ${base.events.length}`);
}

const duplicate = context.applyDelta(base, {
  items: { gold: { id: "gold", quantity: 10 } },
  events: [],
  updated_at: "2026-07-20T02:50:00Z",
});
if (duplicate.items.gold.quantity !== 10 || duplicate.pending.length !== 1) {
  throw new Error("Duplicate delta did not restore canonical quantity while preserving the outbox");
}

const accepted = context.applyDelta(duplicate, {
  items: { gold: { id: "gold", quantity: 12 } },
  events: ["accepted-event"],
});
if (accepted.items.gold.quantity !== 12 || !accepted.events.includes("accepted-event")) {
  throw new Error("Accepted delta did not apply the canonical item and event key");
}

console.log("inventory_delta_cache=ok local_events=512 duplicate_quantity=canonical pending=preserved");
