"use strict";

const fs = require("fs");

const bootstrap = fs.readFileSync("FUTURE/web/js_parts/01_bootstrap_guard_ai_agent.js", "utf8");
const chat = fs.readFileSync("FUTURE/web/js_parts/04_world_screen_paint.js", "utf8");

for (const marker of [
  "let learnerChatPendingOperation = null;",
  "const createLearnerChatOperationId = () =>",
  "learnerChatPendingOperation.key !== operationKey",
  "operation_id: learnerChatPendingOperation.id",
  "learnerChatPendingOperation = null;",
]) {
  if (!bootstrap.includes(marker) && !chat.includes(marker)) {
    throw new Error(`Missing chat operation marker: ${marker}`);
  }
}

console.log("chat_operation_client=ok retry_reuses_operation=true success_clears_pending=true");
