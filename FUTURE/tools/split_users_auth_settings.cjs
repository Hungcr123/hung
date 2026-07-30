const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "server_parts", "02_users_auth_settings.py");
const partsRoot = path.join(root, "FUTURE", "server_parts", "users_auth_settings");

const partSpecs = [
  ["01_users_admin_listing.py", "def normalize_username(value: str) -> str:"],
  ["02_user_delete_cleanup.py", "def safe_delete_user_path(path: Path, allowed_roots: tuple[Path, ...], result: dict) -> None:"],
  ["03_server_data_profile.py", "def server_data_user_folder_path(username: str) -> Path:"],
  ["04_user_preferences.py", "def normalize_motion_mode(value: object) -> str:"],
  ["05_auth_registration.py", "def check_user_login(username: str, password: str) -> tuple[bool, str, dict]:"],
  ["06_announcements.py", "def sentence_case_first(value: str) -> str:"],
  ["07_server_settings.py", "def normalize_leaderboard_rewards(payload: object = None) -> dict:"],
];

const source = fs.readFileSync(sourcePath, "utf8");
if (source.includes("USERS_AUTH_SETTINGS_PART_FILES = (")) {
  throw new Error("02_users_auth_settings.py already appears to use nested runtime parts.");
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
  "USERS_AUTH_SETTINGS_PARTS_ROOT = SERVER_PARTS_ROOT / \"users_auth_settings\"",
  "USERS_AUTH_SETTINGS_PART_FILES = (",
  ...partSpecs.map(([fileName]) => `    \"${fileName}\",`),
  ")",
  "",
  "",
  "def _load_users_auth_settings_part(part_name: str) -> None:",
  "    part_path = USERS_AUTH_SETTINGS_PARTS_ROOT / part_name",
  "    source = part_path.read_text(encoding=\"utf-8-sig\", errors=\"replace\")",
  "    exec(compile(source, str(part_path), \"exec\"), globals())",
  "",
  "",
  "for _users_auth_settings_part_name in USERS_AUTH_SETTINGS_PART_FILES:",
  "    _load_users_auth_settings_part(_users_auth_settings_part_name)",
  "del _users_auth_settings_part_name",
  "",
];

fs.mkdirSync(partsRoot, { recursive: true });
for (const [fileName, body] of parts) {
  const filePath = path.join(partsRoot, fileName);
  const text = [
    "# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.",
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
    file: path.join("FUTURE", "server_parts", "users_auth_settings", fileName),
    bytes: Buffer.byteLength(body, "utf8"),
    lines: body.split(/\n/).length,
  })),
}, null, 2));
