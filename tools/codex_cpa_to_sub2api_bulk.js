const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const dir = process.argv[2] || "C:\\Users\\hungc\\Downloads\\K12-CPA-20260706";

function readString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function firstString(object, keys) {
  for (const key of keys) {
    if (object && Object.prototype.hasOwnProperty.call(object, key)) {
      const value = readString(object[key]);
      if (value) return value;
    }
  }
  return "";
}

function fingerprint(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function decodeJwtExpiry(token) {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    const claims = JSON.parse(Buffer.from(padded, "base64").toString("utf8"));
    return Number.isFinite(claims.exp) && claims.exp > 0 ? claims.exp : null;
  } catch {
    return null;
  }
}

const files = fs
  .readdirSync(dir)
  .filter((file) => file.toLowerCase().endsWith(".json") && !file.startsWith("sub2api_"))
  .sort();

const rows = [];
const accounts = [];
const issues = [];
const warnings = [];
const seenAccount = new Map();
const seenToken = new Map();

for (const file of files) {
  const fullPath = path.join(dir, file);
  const raw = fs.readFileSync(fullPath, "utf8");
  let item;
  try {
    item = JSON.parse(raw);
  } catch {
    issues.push({ file, issue: "invalid_json" });
    continue;
  }

  const accessToken = firstString(item, ["access_token", "accessToken", "token"]);
  const refreshToken = firstString(item, ["refresh_token", "refreshToken"]);
  const idToken = firstString(item, ["id_token", "idToken"]);
  const email = firstString(item, ["email"]);
  const accountId = firstString(item, [
    "chatgpt_account_id",
    "chatgptAccountId",
    "account_id",
    "accountId",
  ]);
  const planType = firstString(item, ["plan_type", "planType"]);
  const expiresAt = accessToken ? decodeJwtExpiry(accessToken) : null;

  if (!accessToken) issues.push({ file, issue: "missing_access_token" });
  if (accessToken && !expiresAt && !refreshToken) {
    issues.push({ file, issue: "missing_refresh_token_and_unreadable_access_token_expiry" });
  }
  if (accountId) {
    if (seenAccount.has(accountId)) {
      warnings.push({ file, warning: "shared_account_id", first_file: seenAccount.get(accountId) });
    } else {
      seenAccount.set(accountId, file);
    }
  }
  if (accessToken) {
    const tokenHash = fingerprint(accessToken);
    if (seenToken.has(tokenHash)) {
      issues.push({ file, issue: "duplicate_access_token", first_file: seenToken.get(tokenHash) });
    } else {
      seenToken.set(tokenHash, file);
    }
  }

  rows.push(JSON.stringify(item));

  const credentials = {};
  if (accessToken) credentials.access_token = accessToken;
  if (refreshToken) {
    credentials.refresh_token = refreshToken;
    credentials.client_id = "";
  }
  if (idToken) credentials.id_token = idToken;
  if (email) credentials.email = email;
  if (accountId) credentials.chatgpt_account_id = accountId;
  if (planType) credentials.plan_type = planType;
  if (expiresAt) credentials.expires_at = new Date(expiresAt * 1000).toISOString();

  const extra = {
    import_source: "cpa_k12_20260706",
    source_file: file,
  };
  if (readString(item.session_token) || readString(item.sessionToken)) {
    extra.session_token_present = true;
  }

  accounts.push({
    name: email ? "K12 " + email : "K12 " + path.basename(file, ".json"),
    notes: null,
    platform: "openai",
    type: "oauth",
    credentials,
    extra,
    concurrency: 3,
    priority: 50,
    rate_multiplier: 1,
    group_ids: [],
    expires_at: expiresAt,
    auto_pause_on_expired: true,
    confirm_mixed_channel_risk: true,
  });
}

const linesPath = path.join(dir, "sub2api_codex_session_bulk_lines.jsonl");
const requestPath = path.join(dir, "sub2api_codex_session_import_request.json");
const batchPath = path.join(dir, "sub2api_accounts_batch_create.json");
const summaryPath = path.join(dir, "sub2api_conversion_summary.json");

fs.writeFileSync(linesPath, rows.join("\n") + "\n", "utf8");
fs.writeFileSync(
  requestPath,
  JSON.stringify(
    {
      content: rows.join("\n"),
      name: "K12 CPA 20260706",
      concurrency: 3,
      priority: 50,
      rate_multiplier: 1,
      auto_pause_on_expired: true,
      update_existing: true,
      confirm_mixed_channel_risk: true,
    },
    null,
    2,
  ),
  "utf8",
);
fs.writeFileSync(batchPath, JSON.stringify({ accounts }, null, 2), "utf8");
fs.writeFileSync(
  summaryPath,
  JSON.stringify(
    {
      source_dir: dir,
      source_json_files: files.length,
      converted_entries: rows.length,
      batch_accounts: accounts.length,
      files: {
        jsonl: linesPath,
        codex_session_import_request: requestPath,
        accounts_batch_create: batchPath,
      },
      validation: {
        invalid_or_missing_issues: issues.length,
        issues_without_secrets: issues,
        warnings_without_secrets: warnings,
        unique_account_ids: seenAccount.size,
        unique_access_token_fingerprints: seenToken.size,
      },
    },
    null,
    2,
  ),
  "utf8",
);

console.log(
  JSON.stringify(
    {
      source_json_files: files.length,
      converted_entries: rows.length,
      issues: issues.length,
      output_dir: dir,
    },
    null,
    2,
  ),
);
