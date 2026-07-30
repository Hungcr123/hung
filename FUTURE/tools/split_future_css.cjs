const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..", "..");
const sourcePath = path.join(root, "FUTURE", "web", "future.css");
const partsRoot = path.join(root, "FUTURE", "web", "css_parts");
const manifestPath = path.join(partsRoot, "manifest.json");
const targetBytes = 150 * 1024;

const sectionLabels = [
  "base_shell_layout",
  "auth_profile_controls",
  "chat_stream_screen",
  "paint_world_game",
  "question_core_cards",
  "question_guidance_motion",
  "vocab_panels_memory",
  "lesson_tasks_ai_focus",
  "server_browser_vault",
  "pdf_mode_core",
  "pdf_mode_training",
  "paragraph_runtime",
  "responsive_overrides",
];

function sha256(text) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

function assertFreshPartsFolder() {
  if (!fs.existsSync(partsRoot)) {
    return;
  }
  const existing = fs.readdirSync(partsRoot).filter((name) => name.endsWith(".css") || name === "manifest.json");
  if (existing.length) {
    throw new Error(`Refusing to overwrite existing css_parts files. Remove or archive ${path.relative(root, partsRoot)} first.`);
  }
}

function lineNumberAt(lineStarts, index) {
  let low = 0;
  let high = lineStarts.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (lineStarts[mid] <= index) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }
  return high + 1;
}

function lineStartsFor(source) {
  const starts = [0];
  for (let index = 0; index < source.length; index += 1) {
    if (source[index] === "\n") {
      starts.push(index + 1);
    }
  }
  return starts;
}

function topLevelRuleBoundaries(source) {
  const boundaries = [];
  let depth = 0;
  let quote = "";
  let escaped = false;
  let comment = false;
  let unmatchedCloseCount = 0;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1] || "";
    if (comment) {
      if (char === "*" && next === "/") {
        comment = false;
        index += 1;
      }
      continue;
    }
    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === quote) {
        quote = "";
      }
      continue;
    }
    if (char === "/" && next === "*") {
      comment = true;
      index += 1;
      continue;
    }
    if (char === "\"" || char === "'") {
      quote = char;
      continue;
    }
    if (char === "{") {
      depth += 1;
      continue;
    }
    if (char === "}") {
      if (depth === 0) {
        unmatchedCloseCount += 1;
        boundaries.push(index + 1);
        continue;
      }
      depth -= 1;
      if (depth === 0) {
        boundaries.push(index + 1);
      }
    }
  }
  if (comment) {
    throw new Error("CSS ended inside a comment.");
  }
  if (quote) {
    throw new Error("CSS ended inside a string.");
  }
  if (depth !== 0) {
    throw new Error(`CSS ended with brace depth ${depth}.`);
  }
  return { boundaries, unmatchedCloseCount };
}

function firstRuleLabel(text) {
  const match = text.match(/\S[\s\S]*?\{/);
  if (!match) {
    return "";
  }
  return match[0].slice(0, -1).replace(/\s+/g, " ").trim().slice(0, 96);
}

function lastRuleLabel(text) {
  const compact = text.replace(/\/\*[\s\S]*?\*\//g, " ");
  const matches = [...compact.matchAll(/(?:^|})\s*([^{}]+?)\s*\{/g)];
  if (!matches.length) {
    return "";
  }
  return matches[matches.length - 1][1].replace(/\s+/g, " ").trim().slice(0, 96);
}

function chunkBoundaries(boundaries, sourceLength) {
  const chunks = [];
  let start = 0;
  let previousBoundary = 0;
  for (const boundary of boundaries) {
    if (previousBoundary > start && boundary - start > targetBytes) {
      chunks.push([start, previousBoundary]);
      start = previousBoundary;
    }
    previousBoundary = boundary;
  }
  if (sourceLength > start) {
    chunks.push([start, sourceLength]);
  }
  return chunks;
}

assertFreshPartsFolder();

const source = fs.readFileSync(sourcePath, "utf8");
const boundaryInfo = topLevelRuleBoundaries(source);
const boundaries = boundaryInfo.boundaries;
if (!boundaries.length) {
  throw new Error("No top-level CSS rule boundaries were found.");
}

const lineStarts = lineStartsFor(source);
const chunks = chunkBoundaries(boundaries, source.length);

fs.mkdirSync(partsRoot, { recursive: true });

const parts = chunks.map(([start, end], index) => {
  const label = sectionLabels[index] || `section_${String(index + 1).padStart(2, "0")}`;
  const file = `${String(index + 1).padStart(2, "0")}_${label}.css`;
  const body = source.slice(start, end);
  fs.writeFileSync(path.join(partsRoot, file), body, "utf8");
  return {
    file,
    line_start: lineNumberAt(lineStarts, start),
    line_end: lineNumberAt(lineStarts, Math.max(start, end - 1)),
    bytes: Buffer.byteLength(body, "utf8"),
    sha256: sha256(body),
    first: firstRuleLabel(body),
    last: lastRuleLabel(body),
  };
});

const rebuilt = parts.map((part) => fs.readFileSync(path.join(partsRoot, part.file), "utf8")).join("");
if (rebuilt !== source) {
  throw new Error("Internal split check failed: rebuilt future.css does not match source.");
}

const manifest = {
  version: 1,
  source: "FUTURE/web/future.css",
  mode: "top_level_css_rule_parts",
  target_bytes: targetBytes,
  source_sha256: sha256(source),
  top_level_rule_count: boundaries.length,
  unmatched_top_level_close_count: boundaryInfo.unmatchedCloseCount,
  parts,
};

fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  ok: true,
  source: path.relative(root, sourcePath),
  partsRoot: path.relative(root, partsRoot),
  topLevelRules: boundaries.length,
  unmatchedTopLevelCloseCount: boundaryInfo.unmatchedCloseCount,
  parts: parts.map((part) => ({
    file: path.join("FUTURE", "web", "css_parts", part.file),
    lines: `${part.line_start}-${part.line_end}`,
    bytes: part.bytes,
  })),
  sha256: manifest.source_sha256,
}, null, 2));
