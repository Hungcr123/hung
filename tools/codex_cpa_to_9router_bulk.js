const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const dir = process.argv[2] || "C:\\Users\\hungc\\Downloads\\K12-CPA-20260706";

function stringValue(value) {
  return typeof value === "string" ? value.trim() : "";
}

function firstString(object, keys) {
  for (const key of keys) {
    const value = stringValue(object?.[key]);
    if (value) return value;
  }
  return "";
}

function decodeJwtPayload(token) {
  const parts = String(token || "").split(".");
  if (parts.length !== 3) return null;
  try {
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    return JSON.parse(Buffer.from(padded, "base64").toString("utf8"));
  } catch {
    return null;
  }
}

function tokenFingerprint(token) {
  return crypto.createHash("sha256").update(token).digest("hex");
}

function jwtIsoExpiry(token) {
  const payload = decodeJwtPayload(token);
  return Number.isFinite(payload?.exp) && payload.exp > 0
    ? new Date(payload.exp * 1000).toISOString()
    : null;
}

function extractJwtInfo(token) {
  const payload = decodeJwtPayload(token) || {};
  const auth = payload["https://api.openai.com/auth"] || {};
  const profile = payload["https://api.openai.com/profile"] || {};
  return {
    email: stringValue(profile.email) || stringValue(payload.email) || stringValue(payload.preferred_username),
    chatgptAccountId: stringValue(auth.chatgpt_account_id),
    chatgptUserId: stringValue(auth.chatgpt_user_id) || stringValue(auth.user_id),
    chatgptPlanType: stringValue(auth.chatgpt_plan_type),
  };
}

const files = fs
  .readdirSync(dir)
  .filter((file) => file.toLowerCase().endsWith(".json") && !file.startsWith("sub2api_") && !file.startsWith("9router_"))
  .sort();

const accounts = [];
const cpaShapeAccounts = [];
const dualKeyAccounts = [];
const issues = [];
const warnings = [];
const seenToken = new Map();

for (const file of files) {
  let source;
  try {
    source = JSON.parse(fs.readFileSync(path.join(dir, file), "utf8"));
  } catch {
    issues.push({ file, issue: "invalid_json" });
    continue;
  }

  const accessToken = firstString(source, ["access_token", "accessToken", "token"]);
  const refreshToken = firstString(source, ["refresh_token", "refreshToken"]);
  const idToken = firstString(source, ["id_token", "idToken"]);
  const jwtInfo = extractJwtInfo(idToken || accessToken);
  const email = firstString(source, ["email"]) || jwtInfo.email;
  const chatgptAccountId =
    firstString(source, ["chatgpt_account_id", "chatgptAccountId", "account_id", "accountId"]) ||
    jwtInfo.chatgptAccountId;
  const chatgptUserId = firstString(source, ["chatgpt_user_id", "chatgptUserId", "user_id", "userId"]) || jwtInfo.chatgptUserId;
  const chatgptPlanType = firstString(source, ["chatgpt_plan_type", "chatgptPlanType", "plan_type", "planType"]) || jwtInfo.chatgptPlanType;
  const expiresAt = firstString(source, ["expired", "expires_at", "expiresAt"]) || jwtIsoExpiry(accessToken);

  if (!accessToken) {
    issues.push({ file, issue: "missing_accessToken" });
    continue;
  }

  const accessHash = tokenFingerprint(accessToken);
  if (seenToken.has(accessHash)) {
    warnings.push({ file, warning: "duplicate_accessToken", first_file: seenToken.get(accessHash) });
  } else {
    seenToken.set(accessHash, file);
  }

  const providerSpecificData = {
    authMethod: refreshToken ? "oauth" : "access_token",
    importSource: "cpa_k12_20260706",
    sourceFile: file,
  };
  if (chatgptAccountId) {
    providerSpecificData.chatgptAccountId = chatgptAccountId;
    providerSpecificData.workspaceId = chatgptAccountId;
    providerSpecificData.accountId = chatgptAccountId;
  }
  if (chatgptUserId) providerSpecificData.chatgptUserId = chatgptUserId;
  if (chatgptPlanType) providerSpecificData.chatgptPlanType = chatgptPlanType;

  const account = {
    name: email ? `K12 ${email}` : `K12 ${path.basename(file, ".json")}`,
    email: email || null,
    accessToken,
    idToken: idToken || undefined,
    expiresAt: expiresAt || undefined,
    tokenType: "Bearer",
    testStatus: "active",
    isActive: true,
    providerSpecificData,
  };
  if (refreshToken) account.refreshToken = refreshToken;

  for (const key of Object.keys(account)) {
    if (account[key] === undefined) delete account[key];
  }
  accounts.push(account);

  const cpaShape = {
    access_token: accessToken,
    account_id: firstString(source, ["account_id", "accountId"]) || chatgptAccountId || "",
    chatgpt_account_id: chatgptAccountId || "",
    chatgpt_plan_type: chatgptPlanType || "",
    disabled: source.disabled === true,
    email: email || "",
    expired: expiresAt || "",
    id_token: idToken || "",
    id_token_synthetic: source.id_token_synthetic === true,
    last_refresh: firstString(source, ["last_refresh", "lastRefresh"]) || "",
    name: firstString(source, ["name"]) || (email ? `K12 ${email}` : `K12 ${path.basename(file, ".json")}`),
    plan_type: firstString(source, ["plan_type", "planType"]) || chatgptPlanType || "",
    refresh_token: refreshToken || "",
    session_token: firstString(source, ["session_token", "sessionToken"]),
    type: firstString(source, ["type"]) || "codex",
  };
  cpaShapeAccounts.push(cpaShape);

  dualKeyAccounts.push({
    ...cpaShape,
    accessToken,
    idToken: idToken || undefined,
    refreshToken: refreshToken || undefined,
    expiresAt: expiresAt || undefined,
    tokenType: "Bearer",
    testStatus: "active",
    isActive: true,
    providerSpecificData,
  });
}

const arrayPath = path.join(dir, "9router_codex_bulk_add.json");
const wrappedPath = path.join(dir, "9router_codex_bulk_add_wrapped.json");
const accessOnlyPath = path.join(dir, "9router_codex_access_tokens_only.txt");
const cpaShapePath = path.join(dir, "9router_codex_bulk_add_cpa_shape.json");
const cpaShapeJsonlPath = path.join(dir, "9router_codex_bulk_add_cpa_shape.jsonl");
const dualKeyPath = path.join(dir, "9router_codex_bulk_add_dual_keys.json");
const summaryPath = path.join(dir, "9router_conversion_summary.json");

fs.writeFileSync(arrayPath, JSON.stringify(accounts, null, 2), "utf8");
fs.writeFileSync(wrappedPath, JSON.stringify({ accounts }, null, 2), "utf8");
fs.writeFileSync(accessOnlyPath, accounts.map((item) => item.accessToken).join("\n") + "\n", "utf8");
fs.writeFileSync(cpaShapePath, JSON.stringify(cpaShapeAccounts, null, 2), "utf8");
fs.writeFileSync(cpaShapeJsonlPath, cpaShapeAccounts.map((item) => JSON.stringify(item)).join("\n") + "\n", "utf8");
fs.writeFileSync(dualKeyPath, JSON.stringify(dualKeyAccounts, null, 2), "utf8");
fs.writeFileSync(
  summaryPath,
  JSON.stringify(
    {
      source_dir: dir,
      source_json_files: files.length,
      converted_accounts: accounts.length,
      files: {
        bulk_add_array: arrayPath,
        bulk_add_wrapped: wrappedPath,
        access_tokens_only: accessOnlyPath,
        cpa_shape_array: cpaShapePath,
        cpa_shape_jsonl: cpaShapeJsonlPath,
        dual_keys_array: dualKeyPath,
      },
      validation: {
        issues_count: issues.length,
        warnings_count: warnings.length,
        issues_without_secrets: issues,
        warnings_without_secrets: warnings,
        unique_access_token_fingerprints: seenToken.size,
        with_email: accounts.filter((item) => item.email).length,
        with_idToken: accounts.filter((item) => item.idToken).length,
        with_expiresAt: accounts.filter((item) => item.expiresAt).length,
        with_workspaceId: accounts.filter((item) => item.providerSpecificData?.workspaceId).length,
        with_refreshToken: accounts.filter((item) => item.refreshToken).length,
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
      converted_accounts: accounts.length,
      issues: issues.length,
      warnings: warnings.length,
      output: arrayPath,
    },
    null,
    2,
  ),
);
