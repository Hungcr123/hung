const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "09_vocab_world_game.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "vocab_world_game");

const partSpecs = [
  ["01_leaderboard_period_npc.py", "def load_vocab_leaderboard_period_state() -> dict:"],
  ["02_leaderboard_social_chat.py", "def load_vocab_leaderboard_reward_state() -> dict:"],
  ["03_shared_world_core.py", "def flush_shared_world_state_cache(force: bool = False) -> None:"],
  ["04_shared_world_battle.py", "def flush_shared_world_battle_state_cache(force: bool = False) -> None:"],
  ["05_qm_city_training.py", "def load_qm_city_training_state() -> dict:"],
  ["06_leaderboard_rewards_rank.py", "def vocab_leaderboard_period_rows(period_state: dict, scope: str, bucket: str, limit: int = 3) -> list[dict]:"],
  ["07_game_rooms.py", "def game_room_code() -> str:"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("VOCAB_WORLD_GAME_PART_FILES = (")) {
  throw new Error("09_vocab_world_game.py already appears to use nested runtime parts.");
}

const starts = partSpecs.map(([fileName, marker]) => {
  const index = source.indexOf(marker);
  if (index < 0) {
    throw new Error(`Missing split marker for ${fileName}: ${marker}`);
  }
  if (index > 0 && source[index - 1] !== "\n") {
    throw new Error(`Split marker is not at the beginning of a line for ${fileName}.`);
  }
  return index;
});

for (let index = 1; index < starts.length; index += 1) {
  if (starts[index] <= starts[index - 1]) {
    throw new Error(`Split markers are out of order at ${partSpecs[index][0]}.`);
  }
}

const header = source.slice(0, starts[0]).trimEnd();
const parts = partSpecs.map(([fileName], index) => {
  const start = starts[index];
  const end = index + 1 < starts.length ? starts[index + 1] : source.length;
  const body = source.slice(start, end).trimEnd() + "\n";
  return [fileName, body];
});

const loaderLines = [
  "",
  "",
  "VOCAB_WORLD_GAME_PARTS_ROOT = SERVER_PARTS_ROOT / \"vocab_world_game\"",
  "VOCAB_WORLD_GAME_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_vocab_world_game_part(part_name: str) -> None:",
  "    part_path = VOCAB_WORLD_GAME_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _vocab_world_game_part_name in VOCAB_WORLD_GAME_PART_FILES:",
  "    _load_vocab_world_game_part(_vocab_world_game_part_name)",
  "del _vocab_world_game_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.",
    "# This is a nested transitional split; do not import directly yet.",
    "",
    body,
  ].join("\n");
  fs.writeFileSync(filePath, text, "utf8");
}

fs.writeFileSync(sourcePath, `${header}${loaderLines.join("\n")}`, "utf8");

console.log(JSON.stringify({
  loader: path.relative(root, sourcePath),
  partsRoot: path.relative(root, partsRoot),
  parts: parts.map(([fileName, body]) => ({
    file: path.join("FUTURE", "server_parts", "vocab_world_game", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
