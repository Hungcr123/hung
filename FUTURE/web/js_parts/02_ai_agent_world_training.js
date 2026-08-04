

      async function runAiAgentVocabQuick(kind = "usage") {
        if (aiAgentCurrentSpaceName() !== "space_v") {
          setAiAgentStatus("Space_V quick asks are available while learning vocabulary.", true);
          return;
        }
        setAiAgentMode("detailed");
        const context = aiAgentContextPayload();
        const runtime = context && context.runtime && typeof context.runtime === "object" ? context.runtime : {};
        const contextPatch = {
          kind: "space_v_quick_ask",
          quick_kind: clean(kind).toLowerCase() === "context" ? "context" : "usage",
          current_vocabulary_word: preserveQuestionText(runtime.current_vocabulary_word || ""),
          meaning_prompt: preserveQuestionText(runtime.meaning_prompt || ""),
          phase: preserveQuestionText(runtime.phase || ""),
        };
        await submitAiAgentQuestion({
          message: buildAiAgentVocabQuickPrompt(kind),
          contextPatch,
          autoSaveTitle: contextPatch.current_vocabulary_word || "Space_V vocabulary",
          clearInput: false,
        });
      }

      function aiAgentModeUserKey() {
        return clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";
      }

      function aiAgentModeStorageKey() {
        return `future_ai_agent_answer_mode:${aiAgentModeUserKey()}`;
      }

      function vietnameseTypingStorageKey(scope = "agent") {
        return `future_vietnamese_typing:${clean(scope) || "agent"}:${aiAgentModeUserKey()}`;
      }

      const VIETNAMESE_TONE_TABLE = {
        a: ["a", "á", "à", "ả", "ã", "ạ"],
        ă: ["ă", "ắ", "ằ", "ẳ", "ẵ", "ặ"],
        â: ["â", "ấ", "ầ", "ẩ", "ẫ", "ậ"],
        e: ["e", "é", "è", "ẻ", "ẽ", "ẹ"],
        ê: ["ê", "ế", "ề", "ể", "ễ", "ệ"],
        i: ["i", "í", "ì", "ỉ", "ĩ", "ị"],
        o: ["o", "ó", "ò", "ỏ", "õ", "ọ"],
        ô: ["ô", "ố", "ồ", "ổ", "ỗ", "ộ"],
        ơ: ["ơ", "ớ", "ờ", "ở", "ỡ", "ợ"],
        u: ["u", "ú", "ù", "ủ", "ũ", "ụ"],
        ư: ["ư", "ứ", "ừ", "ử", "ữ", "ự"],
        y: ["y", "ý", "ỳ", "ỷ", "ỹ", "ỵ"],
      };
      const VIETNAMESE_TONE_KEYS = { s: 1, f: 2, r: 3, x: 4, j: 5 };
      const VIETNAMESE_TONE_KEY_BY_INDEX = ["", "s", "f", "r", "x", "j"];
      const VIETNAMESE_BASE_BY_CHAR = (() => {
        const map = {};
        Object.entries(VIETNAMESE_TONE_TABLE).forEach(([base, chars]) => {
          chars.forEach((ch) => {
            map[ch] = base;
            map[ch.toUpperCase()] = base.toUpperCase();
          });
        });
        return map;
      })();
      const VIETNAMESE_VOWEL_BASES = new Set(["a", "ă", "â", "e", "ê", "i", "o", "ô", "ơ", "u", "ư", "y"]);
      const vietnameseRemoveToneChar = (ch = "") => VIETNAMESE_BASE_BY_CHAR[ch] || ch;
      const vietnameseLowerBaseChar = (ch = "") => vietnameseRemoveToneChar(ch).toLowerCase();
      const vietnameseHasNativeMark = (text = "") => /[\u00c0-\u1ef9\u0110\u0111]/u.test(String(text || ""));
      const vietnameseIsVowel = (ch = "") => VIETNAMESE_VOWEL_BASES.has(vietnameseLowerBaseChar(ch));
      const vietnameseRestoreWordCase = (word = "", pattern = "") => {
        if (!word) return "";
        if (pattern && pattern === pattern.toUpperCase() && /[A-ZĐ]/.test(pattern)) {
          return word.toUpperCase();
        }
        if (pattern && pattern[0] === pattern[0].toUpperCase() && pattern.slice(1) === pattern.slice(1).toLowerCase()) {
          return word.charAt(0).toUpperCase() + word.slice(1);
        }
        return word;
      };
      const vietnameseToneIndexForChar = (ch = "") => {
        const lower = ch.toLowerCase();
        for (const chars of Object.values(VIETNAMESE_TONE_TABLE)) {
          const idx = chars.indexOf(lower);
          if (idx >= 0) return idx;
        }
        return 0;
      };
      const vietnameseToneKeyForText = (text = "") => {
        for (const ch of Array.from(text)) {
          const toneIndex = vietnameseToneIndexForChar(ch);
          if (toneIndex > 0) return VIETNAMESE_TONE_KEY_BY_INDEX[toneIndex] || "";
        }
        return "";
      };
      const vietnameseToneIndexForText = (text = "") => {
        for (const ch of Array.from(text)) {
          const toneIndex = vietnameseToneIndexForChar(ch);
          if (toneIndex > 0) return toneIndex;
        }
        return 0;
      };
      const vietnameseApplyToneChar = (ch = "", toneIndex = 0) => {
        const base = vietnameseLowerBaseChar(ch);
        const chars = VIETNAMESE_TONE_TABLE[base];
        if (!chars || toneIndex < 0 || toneIndex > 5) return ch;
        const next = chars[toneIndex] || chars[0];
        return ch === ch.toUpperCase() && ch !== ch.toLowerCase() ? next.toUpperCase() : next;
      };
      const vietnameseRestoreRawShapeCase = (raw = "", sourceCh = "") => {
        return sourceCh === sourceCh.toUpperCase() && sourceCh !== sourceCh.toLowerCase() ? raw.toUpperCase() : raw;
      };
      const vietnameseRawShapeWithToneKey = (raw = "", sourceCh = "") => {
        const toneKey = VIETNAMESE_TONE_KEY_BY_INDEX[vietnameseToneIndexForChar(sourceCh)] || "";
        return vietnameseRestoreRawShapeCase(raw, sourceCh) + toneKey;
      };
      const vietnameseRemoveToneFromWord = (word = "") => Array.from(word).map((ch) => {
        const base = vietnameseLowerBaseChar(ch);
        return VIETNAMESE_TONE_TABLE[base] ? vietnameseApplyToneChar(ch, 0) : ch;
      }).join("");
      const vietnameseExtractVowelCluster = (word = "") => {
        let best = null;
        let start = -1;
        for (let i = 0; i < word.length; i += 1) {
          if (vietnameseIsVowel(word[i])) {
            if (start < 0) start = i;
          } else if (start >= 0) {
            best = { start, end: i, cluster: word.slice(start, i) };
            start = -1;
          }
        }
        if (start >= 0) {
          best = { start, end: word.length, cluster: word.slice(start) };
        }
        return best;
      };
      const vietnameseReplaceLastPlainPair = (word = "", pair = "", replacement = "") => {
        const index = word.lastIndexOf(pair);
        return index >= 0 ? word.slice(0, index) + replacement + word.slice(index + pair.length) : word;
      };
      const vietnameseProcessShapeToggle = (word = "") => {
        if (word.length < 2) return word;
        const last = word[word.length - 1];
        const prev = word[word.length - 2];
        const lowerLast = last.toLowerCase();
        const prevBase = vietnameseLowerBaseChar(prev);
        if (lowerLast === "d" && prev.toLowerCase() === "đ") {
          return word.slice(0, -2) + vietnameseRestoreRawShapeCase("dd", prev);
        }
        const directShapeToggles = {
          a: { "â": "aa" },
          e: { "ê": "ee" },
          o: { "ô": "oo" },
          w: { "ă": "aw", "ơ": "ow", "ư": "uw" },
        };
        const rawShape = directShapeToggles[lowerLast] && directShapeToggles[lowerLast][prevBase];
        if (rawShape) {
          return word.slice(0, -2) + vietnameseRawShapeWithToneKey(rawShape, prev);
        }
        if (lowerLast === "w") {
          const core = word.slice(0, -1);
          const cluster = vietnameseExtractVowelCluster(core);
          if (cluster) {
            const lowerCluster = Array.from(cluster.cluster).map(vietnameseLowerBaseChar).join("");
            const clusterToggles = { "ươ": "uow", "ưa": "uaw", "ưi": "uiw", "ưe": "uew", "ơi": "oiw" };
            const replacement = clusterToggles[lowerCluster];
            if (replacement) {
              return core.slice(0, cluster.start) + replacement + core.slice(cluster.end) + vietnameseToneKeyForText(cluster.cluster);
            }
          }
        }
        return word;
      };
      const vietnameseProcessWModifier = (word = "") => {
        if (!word.endsWith("w")) return word;
        const core = word.slice(0, -1);
        const cluster = vietnameseExtractVowelCluster(core);
        if (!cluster) return word;
        const toneIndex = vietnameseToneIndexForText(cluster.cluster);
        const plainCluster = Array.from(cluster.cluster).map((ch) => vietnameseApplyToneChar(ch, 0)).join("");
        const lowerCluster = Array.from(plainCluster).map(vietnameseLowerBaseChar).join("");
        const replacements = [
          ["uoi", "ươi"],
          ["uo", "ươ"],
          ["uô", "ươ"],
          ["ua", "ưa"],
          ["oi", "ơi"],
          ["ui", "ưi"],
          ["ue", "ưe"],
          ["â", "ă"],
          ["a", "ă"],
          ["ô", "ơ"],
          ["o", "ơ"],
          ["u", "ư"],
        ];
        let nextCluster = "";
        for (const [from, to] of replacements) {
          const index = lowerCluster.indexOf(from);
          if (index >= 0) {
            nextCluster = plainCluster.slice(0, index) + to + plainCluster.slice(index + from.length);
            break;
          }
        }
        if (!nextCluster) return word;
        let nextCore = core.slice(0, cluster.start) + nextCluster + core.slice(cluster.end);
        if (toneIndex) {
          const nextClusterInfo = { start: cluster.start, end: cluster.start + nextCluster.length, cluster: nextCluster };
          const targetIndex = vietnameseToneTargetIndex(nextCore, nextClusterInfo);
          if (targetIndex >= 0) {
            nextCore = nextCore.slice(0, targetIndex) + vietnameseApplyToneChar(nextCore[targetIndex], toneIndex) + nextCore.slice(targetIndex + 1);
          }
        }
        return nextCore;
      };
      const vietnameseProcessToneAwareShapeKey = (word = "") => {
        if (word.length < 2) return word;
        const last = word[word.length - 1].toLowerCase();
        const prev = word[word.length - 2];
        const shapeMap = {
          a: { base: "a", shaped: "â" },
          e: { base: "e", shaped: "ê" },
          o: { base: "o", shaped: "ô" },
        };
        const rule = shapeMap[last];
        if (!rule || vietnameseLowerBaseChar(prev) !== rule.base) return word;
        const toneIndex = vietnameseToneIndexForChar(prev);
        if (!toneIndex) return word;
        const shaped = prev === prev.toUpperCase() && prev !== prev.toLowerCase() ? rule.shaped.toUpperCase() : rule.shaped;
        return word.slice(0, -2) + vietnameseApplyToneChar(shaped, toneIndex);
      };
      const vietnameseProcessDelayedShapeKey = (word = "") => {
        if (word.length < 2) return word;
        const shapeRules = {
          a: { base: "a", shaped: "â" },
          e: { base: "e", shaped: "ê" },
          o: { base: "o", shaped: "ô" },
        };
        const last = word[word.length - 1].toLowerCase();
        const rule = shapeRules[last];
        if (!rule) return word;
        const core = word.slice(0, -1);
        const cluster = vietnameseExtractVowelCluster(core);
        if (!cluster) return word;
        const targetOffset = Array.from(cluster.cluster).findIndex((ch) => vietnameseLowerBaseChar(ch) === rule.base);
        if (targetOffset < 0 && last === "e" && cluster.end < core.length) {
          const lowerCluster = Array.from(cluster.cluster).map(vietnameseLowerBaseChar).join("");
          const expansions = { uy: "uyê", i: "iê", y: "yê", u: "uê" };
          const expansion = expansions[lowerCluster];
          if (expansion) {
            const toneIndex = vietnameseToneIndexForText(cluster.cluster);
            let nextCore = core.slice(0, cluster.start) + expansion + core.slice(cluster.end);
            if (toneIndex) {
              const nextClusterInfo = { start: cluster.start, end: cluster.start + expansion.length, cluster: expansion };
              const targetIndex = vietnameseToneTargetIndex(nextCore, nextClusterInfo);
              if (targetIndex >= 0) {
                nextCore = nextCore.slice(0, targetIndex) + vietnameseApplyToneChar(nextCore[targetIndex], toneIndex) + nextCore.slice(targetIndex + 1);
              }
            }
            return nextCore;
          }
        }
        if (targetOffset < 0) return word;
        const targetIndex = cluster.start + targetOffset;
        const source = core[targetIndex];
        const shaped = source === source.toUpperCase() && source !== source.toLowerCase() ? rule.shaped.toUpperCase() : rule.shaped;
        return core.slice(0, targetIndex) + vietnameseApplyToneChar(shaped, vietnameseToneIndexForChar(source)) + core.slice(targetIndex + 1);
      };
      const vietnameseNormalizeCoreBeforeTone = (core = "") => {
        const cluster = vietnameseExtractVowelCluster(core);
        if (!cluster) return core;
        const after = core.slice(cluster.end);
        if (after) {
          if (cluster.cluster === "uye") return core.slice(0, cluster.start) + "uyê" + core.slice(cluster.end);
          if (cluster.cluster === "ie") return core.slice(0, cluster.start) + "iê" + core.slice(cluster.end);
          if (cluster.cluster === "ye") return core.slice(0, cluster.start) + "yê" + core.slice(cluster.end);
          if (cluster.cluster === "ue") return core.slice(0, cluster.start) + "uê" + core.slice(cluster.end);
        }
        return core;
      };
      const vietnameseToneTargetIndex = (core = "", clusterInfo) => {
        if (!clusterInfo) return -1;
        const cluster = clusterInfo.cluster;
        const lowerCluster = Array.from(cluster).map(vietnameseLowerBaseChar).join("");
        const hasFinalConsonant = clusterInfo.end < core.length;
        const previousChar = core.slice(0, clusterInfo.start).toLowerCase().slice(-1);
        const preferredClusterTargets = [
          ["uyê", 2],
          ["iê", 1],
          ["yê", 1],
          ["uê", 1],
          ["uô", 1],
          ["ươ", 1],
        ];
        for (const [preferred, offset] of preferredClusterTargets) {
          const preferredIndex = lowerCluster.indexOf(preferred);
          if (preferredIndex >= 0) return clusterInfo.start + preferredIndex + offset;
        }
        if (previousChar === "q" && lowerCluster.startsWith("u") && cluster.length > 1) {
          return clusterInfo.start + 1;
        }
        if (previousChar === "g" && lowerCluster.startsWith("i") && cluster.length > 1) {
          return clusterInfo.start + 1;
        }
        const strongIndex = Array.from(cluster).findIndex((ch) => ["ă", "â", "ê", "ô", "ơ", "ư"].includes(vietnameseLowerBaseChar(ch)));
        if (strongIndex >= 0) return clusterInfo.start + strongIndex;
        if (cluster.length >= 3) return clusterInfo.start + 1;
        if (cluster.length === 2) {
          if (!hasFinalConsonant) return clusterInfo.start;
          return clusterInfo.start + 1;
        }
        return clusterInfo.start;
      };
      const vietnameseNormalizeTonePlacement = (word = "") => {
        const cluster = vietnameseExtractVowelCluster(word);
        if (!cluster) return word;
        let toneIndex = 0;
        for (const ch of Array.from(cluster.cluster)) {
          toneIndex = vietnameseToneIndexForChar(ch);
          if (toneIndex) break;
        }
        if (!toneIndex) return word;
        const plainCluster = Array.from(cluster.cluster).map((ch) => vietnameseApplyToneChar(ch, 0)).join("");
        const plainWord = word.slice(0, cluster.start) + plainCluster + word.slice(cluster.end);
        const plainInfo = {
          start: cluster.start,
          end: cluster.start + plainCluster.length,
          cluster: plainCluster,
        };
        const targetIndex = vietnameseToneTargetIndex(plainWord, plainInfo);
        if (targetIndex < 0) return word;
        return plainWord.slice(0, targetIndex) + vietnameseApplyToneChar(plainWord[targetIndex], toneIndex) + plainWord.slice(targetIndex + 1);
      };
      const processVietnameseTelexWord = (rawWord = "") => {
        if (!rawWord) return "";
        const casePattern = rawWord;
        let word = rawWord.toLowerCase();
        let next = vietnameseProcessShapeToggle(word);
        if (next !== word) return vietnameseRestoreWordCase(next, casePattern);
        next = vietnameseProcessToneAwareShapeKey(word);
        if (next !== word) return vietnameseRestoreWordCase(vietnameseNormalizeTonePlacement(next), casePattern);
        next = vietnameseProcessDelayedShapeKey(word);
        if (next !== word) return vietnameseRestoreWordCase(vietnameseNormalizeTonePlacement(next), casePattern);
        next = vietnameseProcessWModifier(word);
        if (next !== word) return vietnameseRestoreWordCase(vietnameseNormalizeTonePlacement(next), casePattern);
        if (word.endsWith("dd")) return vietnameseRestoreWordCase(word.slice(0, -2) + "đ", casePattern);
        const pairRules = [
          ["aa", "â"], ["aw", "ă"], ["ee", "ê"], ["oo", "ô"], ["ow", "ơ"], ["uw", "ư"],
        ];
        for (const [pair, replacement] of pairRules) {
          if (word.endsWith(pair)) {
            next = vietnameseReplaceLastPlainPair(word, pair, replacement);
            if (next !== word) return vietnameseRestoreWordCase(vietnameseNormalizeTonePlacement(next), casePattern);
          }
        }
        const key = word.slice(-1);
        if (key === "z") {
          return vietnameseRestoreWordCase(vietnameseRemoveToneFromWord(word.slice(0, -1)), casePattern);
        }
        const toneIndex = VIETNAMESE_TONE_KEYS[key];
        if (!toneIndex) {
          const normalized = vietnameseNormalizeTonePlacement(word);
          return vietnameseRestoreWordCase(normalized, casePattern);
        }
        let core = vietnameseNormalizeCoreBeforeTone(word.slice(0, -1));
        const cluster = vietnameseExtractVowelCluster(core);
        const targetIndex = vietnameseToneTargetIndex(core, cluster);
        if (targetIndex < 0) return vietnameseRestoreWordCase(word, casePattern);
        const currentTone = vietnameseToneIndexForChar(core[targetIndex]);
        if (currentTone === toneIndex) {
          return vietnameseRestoreWordCase(vietnameseRemoveToneFromWord(core) + key, casePattern);
        }
        const nextTone = toneIndex;
        core = core.slice(0, targetIndex) + vietnameseApplyToneChar(core[targetIndex], nextTone) + core.slice(targetIndex + 1);
        return vietnameseRestoreWordCase(core, casePattern);
      };

      const vietnameseIsToneToggleEscapeInput = (rawWord = "") => {
        const word = String(rawWord || "").toLowerCase();
        const key = word.slice(-1);
        const toneIndex = VIETNAMESE_TONE_KEYS[key];
        if (!toneIndex) return false;
        let core = vietnameseNormalizeCoreBeforeTone(word.slice(0, -1));
        const cluster = vietnameseExtractVowelCluster(core);
        const targetIndex = vietnameseToneTargetIndex(core, cluster);
        return targetIndex >= 0 && vietnameseToneIndexForChar(core[targetIndex]) === toneIndex;
      };

      const vietnameseIsShapeToggleEscapeInput = (rawWord = "") => {
        const word = String(rawWord || "").toLowerCase();
        if (word.length < 2) return false;
        const last = word[word.length - 1];
        const prev = word[word.length - 2];
        const prevBase = vietnameseLowerBaseChar(prev);
        if (last === "d" && prev === "đ") return true;
        if (last === "a" && prevBase === "â") return true;
        if (last === "e" && prevBase === "ê") return true;
        if (last === "o" && prevBase === "ô") return true;
        if (last === "w" && ["ă", "ơ", "ư"].includes(prevBase)) return true;
        if (last === "w") {
          const core = word.slice(0, -1);
          const cluster = vietnameseExtractVowelCluster(core);
          const lowerCluster = cluster ? Array.from(cluster.cluster).map(vietnameseLowerBaseChar).join("") : "";
          return ["ươ", "ưa", "ưi", "ưe", "ơi"].includes(lowerCluster);
        }
        return false;
      };

      const vietnameseTypingControllers = [];
      function setVietnameseTypingToggleState(button, active) {
        if (!button) return;
        button.classList.toggle("is-active", Boolean(active));
        button.setAttribute("aria-pressed", active ? "true" : "false");
        button.title = active ? "Vietnamese typing support: on" : "Vietnamese typing support: off";
      }
      function attachVietnameseTypingSupport(input, button, scope = "agent") {
        if (!input || !button) return null;
        let active = false;
        let internal = false;
        let escapedStart = -1;
        let escapedValue = "";
        let rawWordStart = -1;
        let rawWordValue = "";
        let renderedWordValue = "";
        let rawWordMemory = [];
        let ctrlRestorePending = false;
        let compositionJustEnded = false;
        const read = () => {
          try {
            const saved = localStorage.getItem(vietnameseTypingStorageKey(scope));
            return saved == null ? true : saved === "1";
          } catch (error) {
            return true;
          }
        };
        const write = (value) => {
          try {
            localStorage.setItem(vietnameseTypingStorageKey(scope), value ? "1" : "0");
          } catch (error) {
          }
        };
        const sync = () => {
          active = read();
          setVietnameseTypingToggleState(button, active);
        };
        const clearRawWordCache = () => {
          rawWordStart = -1;
          rawWordValue = "";
          renderedWordValue = "";
          rawWordMemory = [];
        };
        const clearVietnameseTypingEditCache = () => {
          clearRawWordCache();
          escapedStart = -1;
          escapedValue = "";
          ctrlRestorePending = false;
          compositionJustEnded = false;
        };
        const lockExternalVietnameseWord = (wordStart, word) => {
          clearRawWordCache();
          escapedStart = wordStart;
          escapedValue = word;
          renderedWordValue = word;
        };
        const rememberRawWord = (wordStart, rendered, raw) => {
          if (!raw || wordStart < 0) return;
          rawWordMemory = rawWordMemory
            .filter((item) => item && item.start !== wordStart)
            .filter((item) => item && Math.abs(item.start - wordStart) < 10000);
          rawWordMemory.push({ start: wordStart, rendered: String(rendered || ""), raw: String(raw || "") });
          if (rawWordMemory.length > 80) rawWordMemory = rawWordMemory.slice(-80);
        };
        const findRawWordMemory = (wordStart, rendered) => {
          const wanted = String(rendered || "");
          for (let i = rawWordMemory.length - 1; i >= 0; i -= 1) {
            const item = rawWordMemory[i];
            if (item && item.start === wordStart && (!item.rendered || item.rendered === wanted || wanted.startsWith(item.rendered) || item.rendered.startsWith(wanted))) {
              return item.raw || "";
            }
          }
          return "";
        };
        const shiftRawWordMemory = (fromIndex, delta) => {
          if (!delta) return;
          rawWordMemory = rawWordMemory.map((item) => {
            if (!item || item.start <= fromIndex) return item;
            return { ...item, start: item.start + delta };
          });
        };
        const updateRawWordTracker = (event, wordStart, word) => {
          const inputType = String(event && event.inputType || "");
          const data = typeof (event && event.data) === "string" ? event.data : "";
          if (inputType.startsWith("delete")) {
            clearVietnameseTypingEditCache();
            return;
          }
          if (inputType === "insertFromPaste" || inputType === "insertFromDrop" || inputType === "insertReplacementText") {
            clearVietnameseTypingEditCache();
            return;
          }
          if (wordStart !== rawWordStart || !rawWordValue) {
            rawWordStart = wordStart;
            rawWordValue = word;
            renderedWordValue = word;
            rememberRawWord(wordStart, word, word);
            return;
          }
          if (data && inputType.startsWith("insert") && renderedWordValue && word === renderedWordValue + data) {
            rawWordValue += data;
            rememberRawWord(wordStart, word, rawWordValue);
            return;
          }
          if (data && inputType.startsWith("insert") && word.endsWith(data)) {
            rawWordValue += data;
            rememberRawWord(wordStart, word, rawWordValue);
            return;
          }
          rawWordValue = word;
          renderedWordValue = word;
          rememberRawWord(wordStart, word, rawWordValue);
        };
        const restoreCurrentWordToRaw = () => {
          if (!active || internal) return false;
          const start = Number(input.selectionStart);
          const end = Number(input.selectionEnd);
          if (!Number.isFinite(start) || start !== end) return false;
          const value = String(input.value || "");
          const leftPart = (value.slice(0, start).match(/([\p{L}]+)$/u) || ["", ""])[1] || "";
          const rightPart = (value.slice(start).match(/^([\p{L}]+)/u) || ["", ""])[1] || "";
          const wordStart = start - leftPart.length;
          const word = leftPart + rightPart;
          if (!word) return false;
          const raw = wordStart === rawWordStart && rawWordValue ? rawWordValue : findRawWordMemory(wordStart, word);
          if (!raw || raw === word) return false;
          const delta = raw.length - word.length;
          internal = true;
          try {
            input.value = value.slice(0, wordStart) + raw + value.slice(wordStart + word.length);
            input.setSelectionRange(wordStart + raw.length, wordStart + raw.length);
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } finally {
            internal = false;
          }
          escapedStart = wordStart;
          escapedValue = raw;
          clearRawWordCache();
          return true;
        };
        const apply = (event = null) => {
          if (!active || internal || input.isComposing) return;
          if (input.dataset && input.dataset.vietnameseTypingActive === "0") return;
          const start = Number(input.selectionStart);
          const end = Number(input.selectionEnd);
          if (!Number.isFinite(start) || start !== end) return;
          const value = String(input.value || "");
          const left = value.slice(0, start);
          const right = value.slice(start);
          const match = left.match(/([\p{L}]+)$/u);
          if (!match) {
            compositionJustEnded = false;
            return;
          }
          const word = match[1] || "";
          const wordStart = left.length - word.length;
          if (escapedValue && wordStart === escapedStart && word.startsWith(escapedValue)) {
            renderedWordValue = word;
            return;
          }
          if (escapedValue) {
            escapedStart = -1;
            escapedValue = "";
          }
          const inputType = String(event && event.inputType || "");
          const data = typeof (event && event.data) === "string" ? event.data : "";
          const nativeInputFromExternalIme = Boolean(
            (compositionJustEnded || inputType === "insertCompositionText" || vietnameseHasNativeMark(data))
            && vietnameseHasNativeMark(word)
          );
          compositionJustEnded = false;
          if (nativeInputFromExternalIme) {
            lockExternalVietnameseWord(wordStart, word);
            return;
          }
          updateRawWordTracker(event, wordStart, word);
          const nextWord = processVietnameseTelexWord(word);
          if (!nextWord || nextWord === word) {
            renderedWordValue = word;
            rememberRawWord(wordStart, word, rawWordValue || word);
            return;
          }
          const nextLeft = left.slice(0, left.length - word.length) + nextWord;
          internal = true;
          try {
            input.value = nextLeft + right;
            input.setSelectionRange(nextLeft.length, nextLeft.length);
            input.dispatchEvent(new Event("change", { bubbles: true }));
          } finally {
            internal = false;
          }
          if (vietnameseIsShapeToggleEscapeInput(word) || vietnameseIsToneToggleEscapeInput(word)) {
            escapedStart = nextLeft.length - nextWord.length;
            escapedValue = nextWord;
            rawWordStart = escapedStart;
            rawWordValue = nextWord;
            renderedWordValue = nextWord;
            rememberRawWord(rawWordStart, nextWord, nextWord);
          } else {
            rawWordStart = nextLeft.length - nextWord.length;
            renderedWordValue = nextWord;
            rememberRawWord(rawWordStart, nextWord, rawWordValue || word);
          }
        };
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          active = !active;
          write(active);
          setVietnameseTypingToggleState(button, active);
          input.focus({ preventScroll: true });
        });
        input.addEventListener("compositionstart", () => { input.isComposing = true; });
        input.addEventListener("compositionend", () => {
          input.isComposing = false;
          compositionJustEnded = true;
          window.setTimeout(apply, 0);
        });
        input.addEventListener("future:speech-input-mutated", clearVietnameseTypingEditCache);
        input.addEventListener("input", (event) => apply(event));
        input.addEventListener("keydown", (event) => {
          if (event.key === "Control" && !event.altKey && !event.metaKey && !event.shiftKey) {
            ctrlRestorePending = true;
            return;
          }
          if (ctrlRestorePending && event.ctrlKey && event.key !== "Control") {
            ctrlRestorePending = false;
          }
        });
        input.addEventListener("keyup", (event) => {
          if (event.key !== "Control") return;
          const shouldRestore = ctrlRestorePending;
          ctrlRestorePending = false;
          if (shouldRestore && !event.altKey && !event.metaKey && !event.shiftKey) {
            if (restoreCurrentWordToRaw()) {
              event.preventDefault();
              event.stopPropagation();
            }
          }
        });
        input.addEventListener("blur", () => {
          ctrlRestorePending = false;
        });
        const controller = { sync };
        vietnameseTypingControllers.push(controller);
        sync();
        return controller;
      }
      function syncVietnameseTypingSupportForUser() {
        vietnameseTypingControllers.forEach((controller) => {
          try {
            controller.sync();
          } catch (error) {
          }
        });
      }

      function normalizeAiAgentMode(value = "") {
        const mode = clean(value).toLowerCase();
        return mode === "detailed" ? "detailed" : "spoken";
      }

      function getAiAgentMode() {
        try {
          const saved = clean(localStorage.getItem(aiAgentModeStorageKey()) || "");
          return saved ? normalizeAiAgentMode(saved) : "detailed";
        } catch (error) {
          return "detailed";
        }
      }

      function setAiAgentMode(mode = "detailed", persist = true) {
        const nextMode = normalizeAiAgentMode(mode);
        if (persist) {
          try {
            localStorage.setItem(aiAgentModeStorageKey(), nextMode);
          } catch (error) {
          }
        }
        aiAgentModeButtons.forEach((button) => {
          const active = normalizeAiAgentMode(button.dataset.aiAgentMode || "") === nextMode;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        });
        setAiAgentStatus(nextMode === "detailed"
          ? "Detailed mode: full text panels, only a short Michael voice signal."
          : "Talk mode: one spoken paragraph with bilingual panels.");
      }

      function triggerAiAgentBootAnimation() {
        if (aiAgentButton) {
          aiAgentButton.classList.remove("is-booting");
          void aiAgentButton.offsetWidth;
          aiAgentButton.classList.add("is-booting");
          window.setTimeout(() => aiAgentButton.classList.remove("is-booting"), 2600);
        }
      }

      function isAiAgentPopupOpen() {
        return Boolean(aiAgentPopup && aiAgentPopup.classList.contains("is-open"));
      }

      function openAiAgentPopup() {
        if (!authToken) {
          showLoginGate("Hay dang nhap de dung AI agent.");
          return;
        }
        if (aiAgentPopup) {
          aiAgentPopup.classList.add("is-open");
          aiAgentPopup.setAttribute("aria-hidden", "false");
        }
        renderAiAgentSuggestion();
        renderAiAgentVocabQuick();
        renderAiAgentParagraphQuick();
        if (aiAgentButton) {
          aiAgentButton.classList.add("is-active");
          aiAgentButton.setAttribute("aria-expanded", "true");
        }
        triggerAiAgentBootAnimation();
        setAiAgentMode(getAiAgentMode(), false);
        syncVietnameseTypingSupportForUser();
        window.setTimeout(() => {
          if (aiAgentInput) {
            aiAgentInput.focus({ preventScroll: true });
          }
        }, 320);
      }

      function closeAiAgentPopup() {
        if (aiAgentInput && typeof stopFutureSpeechInputForTarget === "function") {
          stopFutureSpeechInputForTarget(aiAgentInput);
        }
        setAiAgentThinking(false);
        if (aiAgentPopup) {
          aiAgentPopup.classList.remove("is-open", "is-booting");
          aiAgentPopup.setAttribute("aria-hidden", "true");
        }
        if (aiAgentButton) {
          aiAgentButton.classList.remove("is-active", "is-booting");
          aiAgentButton.setAttribute("aria-expanded", "false");
        }
        closeAiAgentGhostEnPopup();
      }

      // Added 2026-06-30: normalizes Ghost EN hover tokens for Vietnamese detail lookup.
      function aiAgentGhostEnWordKey(value = "") {
        return clean(value)
          .replace(/[\u2018\u2019`´]/g, "'")
          .replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, "")
          .toLowerCase()
          .replace(/\b([a-z]+)'s\b/g, "$1")
          .replace(/\s+/g, " ")
          .trim();
      }

      // Added 2026-06-30: keeps Ghost EN popup status independent from the main Send flow.
      function setAiAgentGhostEnStatus(message = "", isError = false) {
        if (!aiAgentGhostEnStatus) return;
        aiAgentGhostEnStatus.textContent = clean(message);
        aiAgentGhostEnStatus.classList.toggle("is-error", Boolean(isError));
      }

      const AI_AGENT_GHOST_EN_PLAYBACK_RATES = [0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.4, 1.5];

      // Added 2026-06-30: normalizes Ghost EN voice playback speed for the header spin control.
      function normalizeAiAgentGhostEnPlaybackRate(value = 1) {
        const rate = Number(value || 1) || 1;
        return Math.max(0.5, Math.min(1.5, rate));
      }

      // Added 2026-06-30: returns the nearest Ghost EN playback speed step.
      function aiAgentGhostEnPlaybackRateIndex(rate = aiAgentGhostEnPlaybackRate) {
        const value = normalizeAiAgentGhostEnPlaybackRate(rate);
        const index = AI_AGENT_GHOST_EN_PLAYBACK_RATES.findIndex((item) => Math.abs(item - value) < 0.001);
        if (index >= 0) return index;
        let bestIndex = 5;
        let bestDistance = Infinity;
        AI_AGENT_GHOST_EN_PLAYBACK_RATES.forEach((item, itemIndex) => {
          const distance = Math.abs(item - value);
          if (distance < bestDistance) {
            bestDistance = distance;
            bestIndex = itemIndex;
          }
        });
        return bestIndex;
      }

      // Added 2026-06-30: updates the Ghost EN speed spin button and its animated face.
      function syncAiAgentGhostEnSpeedBadge() {
        const percent = Math.round(normalizeAiAgentGhostEnPlaybackRate(aiAgentGhostEnPlaybackRate) * 100);
        if (aiAgentGhostEnSpeedValue) {
          aiAgentGhostEnSpeedValue.textContent = `${percent}%`;
          aiAgentGhostEnSpeedValue.classList.remove("is-turning");
          void aiAgentGhostEnSpeedValue.offsetWidth;
          aiAgentGhostEnSpeedValue.classList.add("is-turning");
        }
        if (aiAgentGhostEnSpeed) {
          const index = aiAgentGhostEnPlaybackRateIndex();
          const offset = (5 - index) * 2.4;
          aiAgentGhostEnSpeed.setAttribute("aria-valuenow", String(percent));
          aiAgentGhostEnSpeed.title = `Ghost EN reading speed ${percent}%`;
          aiAgentGhostEnSpeed.style.setProperty("--ghost-en-speed-index", String(index));
          aiAgentGhostEnSpeed.style.setProperty("--ghost-en-speed-offset", `${offset}px`);
        }
      }

      // Added 2026-06-30: changes Ghost EN read speed from the header spin button.
      function setAiAgentGhostEnPlaybackRateByIndex(index = aiAgentGhostEnPlaybackRateIndex(), options = {}) {
        const opts = options && typeof options === "object" ? options : {};
        const nextIndex = Math.max(0, Math.min(AI_AGENT_GHOST_EN_PLAYBACK_RATES.length - 1, Math.round(Number(index || 0) || 0)));
        const nextRate = AI_AGENT_GHOST_EN_PLAYBACK_RATES[nextIndex] || 1;
        const changed = Math.abs(nextRate - aiAgentGhostEnPlaybackRate) >= 0.001;
        aiAgentGhostEnPlaybackRate = nextRate;
        syncAiAgentGhostEnSpeedBadge();
        if (opts.status !== false && changed) {
          setAiAgentGhostEnStatus(`Ghost EN reading speed ${Math.round(nextRate * 100)}%.`);
        }
        if (opts.persist !== false && changed) {
          scheduleAiAgentGhostEnVoicePreferenceSave();
        }
        return changed;
      }

      // Added 2026-06-30: applies the selected Ghost EN reading speed without changing pitch.
      function applyAiAgentGhostEnPlaybackRate(audio = null) {
        if (!audio) return;
        if (typeof normalizeAudioPlaybackSpeed === "function") {
          normalizeAudioPlaybackSpeed(audio);
        }
        try {
          const rate = normalizeAiAgentGhostEnPlaybackRate(aiAgentGhostEnPlaybackRate);
          audio.defaultPlaybackRate = rate;
          audio.playbackRate = rate;
          if ("preservesPitch" in audio) audio.preservesPitch = true;
          if ("mozPreservesPitch" in audio) audio.mozPreservesPitch = true;
          if ("webkitPreservesPitch" in audio) audio.webkitPreservesPitch = true;
        } catch (error) {
        }
      }

      // Added 2026-06-30: maps Ghost EN accent buttons to cached Sound of Text server-data voices.
      function aiAgentGhostEnVoiceKey(accent = aiAgentGhostEnVoiceAccent) {
        return clean(accent).toLowerCase() === "us" ? "sot:en-US" : "sot:en-GB";
      }

      // Added 2026-06-30: keeps Ghost EN UK/US buttons in sync with the word-click voice.
      function setAiAgentGhostEnVoiceAccent(accent = "uk", announce = true, options = {}) {
        const opts = options && typeof options === "object" ? options : {};
        const nextAccent = clean(accent).toLowerCase() === "us" ? "us" : "uk";
        aiAgentGhostEnVoiceAccent = nextAccent;
        aiAgentGhostEnVoiceButtons.forEach((button) => {
          const active = clean(button.dataset.ghostEnVoice || "").toLowerCase() === nextAccent;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        });
        if (announce) {
          setAiAgentGhostEnStatus(`Ghost EN voice: ${nextAccent.toUpperCase()} Sound of Text.`);
        }
        if (opts.persist !== false) {
          scheduleAiAgentGhostEnVoicePreferenceSave();
        }
      }

      // Added 2026-06-30: selects a Ghost EN paragraph voice even before the async catalog has loaded.
      function setAiAgentGhostEnVoiceSelectValue(voice = "", label = "") {
        const value = clean(voice);
        if (!aiAgentGhostEnVoiceSelect || !value) return;
        const lowered = value.toLowerCase();
        let option = Array.from(aiAgentGhostEnVoiceSelect.options || []).find((item) => clean(item.value).toLowerCase() === lowered);
        if (!option) {
          option = document.createElement("option");
          option.value = value;
          option.textContent = clean(label) || value;
          aiAgentGhostEnVoiceSelect.appendChild(option);
        }
        aiAgentGhostEnVoiceSelect.value = option.value;
      }

      // Added 2026-06-30: builds the per-user Ghost EN voice preference payload.
      function aiAgentGhostEnVoicePreferencePayload() {
        return {
          ghost_en_voice: {
            voice: selectedAiAgentGhostEnParagraphVoice(),
            label: selectedAiAgentGhostEnParagraphVoiceLabel(),
            accent: aiAgentGhostEnVoiceAccent,
            rate: normalizeAiAgentGhostEnPlaybackRate(aiAgentGhostEnPlaybackRate),
          },
        };
      }

      // Added 2026-06-30: stores the learner's Ghost EN voice/rate preference on the server.
      function scheduleAiAgentGhostEnVoicePreferenceSave(delayMs = 360) {
        if (aiAgentGhostEnPreferenceSaveTimer) {
          window.clearTimeout(aiAgentGhostEnPreferenceSaveTimer);
          aiAgentGhostEnPreferenceSaveTimer = 0;
        }
        aiAgentGhostEnPreferenceSaveTimer = window.setTimeout(async () => {
          aiAgentGhostEnPreferenceSaveTimer = 0;
          if (!authToken || typeof fetchAuthJson !== "function") return;
          try {
            await fetchAuthJson("/auth/preferences", {
              method: "POST",
              body: JSON.stringify(aiAgentGhostEnVoicePreferencePayload()),
            });
          } catch (error) {
          }
        }, Math.max(0, Number(delayMs || 0) || 0));
      }

      // Added 2026-06-30: applies saved Ghost EN voice/rate preferences after login/profile load.
      function applyAiAgentGhostEnVoicePayload(preferences = {}) {
        const source = preferences && typeof preferences === "object"
          ? (preferences.ghost_en_voice || preferences.ghostEnVoice || preferences.ghost_en || {})
          : {};
        if (!source || typeof source !== "object") {
          syncAiAgentGhostEnSpeedBadge();
          return;
        }
        const voice = clean(source.voice || source.value || source.key || "");
        const label = clean(source.label || source.name || "");
        if (voice) {
          aiAgentGhostEnPreferredVoice = voice;
          aiAgentGhostEnPreferredVoiceLabel = label;
          setAiAgentGhostEnVoiceSelectValue(voice, label);
        }
        const accent = clean(source.accent || source.voice_accent || source.voiceAccent || "").toLowerCase();
        if (accent === "uk" || accent === "us") {
          setAiAgentGhostEnVoiceAccent(accent, false, { persist: false });
        } else if (voice.toLowerCase() === "sot:en-us") {
          setAiAgentGhostEnVoiceAccent("us", false, { persist: false });
        } else if (voice.toLowerCase() === "sot:en-gb") {
          setAiAgentGhostEnVoiceAccent("uk", false, { persist: false });
        }
        const rate = normalizeAiAgentGhostEnPlaybackRate(source.rate || source.playback_rate || source.playbackRate || 1);
        const rateIndex = aiAgentGhostEnPlaybackRateIndex(rate);
        setAiAgentGhostEnPlaybackRateByIndex(rateIndex, { persist: false, status: false, force: true });
      }

      // Added 2026-07-31: every QmSound consumer resolves through the shared AudioCacheManager.
      async function cachedQmSoundPlaybackUrl(url = "", voice = "", nodeIndex = 0) {
        const source = clean(url);
        if (!source) return { url: "", objectUrl: "" };
        try {
          if (window.__futureAudioCacheManager && typeof window.__futureAudioCacheManager.resolveAudioUrl === "function") {
            return { url: await window.__futureAudioCacheManager.resolveAudioUrl(source), objectUrl: "" };
          }
        } catch (error) {
        }
        return { url: source, objectUrl: "" };
      }

      // Added 2026-06-30: plays clicked Ghost EN words from cached server-data SOT audio.
      async function playAiAgentGhostEnWordAudio(word = "", tokenNode = null) {
        const text = clean(word);
        if (!text) {
          setAiAgentGhostEnStatus("No English word to read.", true);
          return false;
        }
        if (aiAgentGhostEnRecognizing) {
          stopAiAgentGhostEnMic({ replay: false, announce: false });
        }
        stopAiAgentGhostEnMicReplay({ clearHighlights: true });
        stopAiAgentGhostEnParagraphAudio({ clearStatus: false });
        const accent = clean(aiAgentGhostEnVoiceAccent).toLowerCase() === "us" ? "us" : "uk";
        const voiceKey = aiAgentGhostEnVoiceKey(accent);
        const accentLabel = accent.toUpperCase();
        const url = `/server-data/qm-sound?word=${encodeURIComponent(text)}&voice=${encodeURIComponent(voiceKey)}`;
        if (aiAgentGhostEnAudioPlayer) {
          try {
            aiAgentGhostEnAudioPlayer.pause();
            aiAgentGhostEnAudioPlayer.currentTime = 0;
          } catch (error) {
          }
        }
        if (tokenNode) {
          tokenNode.classList.add("is-audio-loading");
          tokenNode.classList.remove("is-audio-playing");
        }
        setAiAgentGhostEnStatus(`Reading "${text}" with ${accentLabel} voice...`);
        return new Promise(async (resolve) => {
          let settled = false;
          let player = null;
          const finish = (ok, message = "", isError = false) => {
            if (settled) return;
            settled = true;
            if (tokenNode) {
              tokenNode.classList.remove("is-audio-loading", "is-audio-playing");
            }
            if (message) {
              setAiAgentGhostEnStatus(message, isError);
            }
            resolve(ok);
          };
          try {
            const playback = await cachedQmSoundPlaybackUrl(url, voiceKey, 0);
            player = new Audio(playback.url || url);
            aiAgentGhostEnAudioPlayer = player;
            player.preload = "auto";
            applyAiAgentGhostEnPlaybackRate(player);
            player.onplay = () => {
              if (tokenNode) {
                tokenNode.classList.remove("is-audio-loading");
                tokenNode.classList.add("is-audio-playing");
              }
              setAiAgentGhostEnStatus(`Playing "${text}" (${accentLabel}).`);
            };
            const cleanupObjectUrl = () => {
              if (playback.objectUrl) {
                try {
                  URL.revokeObjectURL(playback.objectUrl);
                } catch (error) {
                }
              }
            };
            player.onended = () => {
              cleanupObjectUrl();
              finish(true, `Played "${text}" (${accentLabel}).`);
            };
            player.onerror = () => {
              cleanupObjectUrl();
              finish(false, `No cached ${accentLabel} SOT audio for "${text}".`, true);
            };
            const playPromise = player.play();
            if (playPromise && typeof playPromise.catch === "function") {
              playPromise.catch((error) => {
                finish(false, clean(error && error.message) || `Could not play "${text}".`, true);
              });
            }
          } catch (error) {
            finish(false, clean(error && error.message) || `Could not play "${text}".`, true);
          }
        });
      }

      // Added 2026-06-30: normalizes Ghost EN voice rows from server and fallback lists.
      function normalizeAiAgentGhostEnVoiceRow(item = {}) {
        const source = item && typeof item === "object" ? item : {};
        const key = clean(source.key || source.voice || source.value || "");
        const label = clean(source.label || source.name || source.title || key);
        return key ? { key, label: label || key } : null;
      }

      // Added 2026-06-30: builds the pinned Ghost EN voice order requested for paragraph reading.
      function aiAgentGhostEnPriorityVoiceRows(rows = []) {
        const available = Array.isArray(rows) ? rows.filter(Boolean) : [];
        const findVoice = (fallback, matcher) => {
          const match = available.find((row) => {
            const haystack = `${clean(row.key)} ${clean(row.label)}`.toLowerCase();
            return matcher(haystack, row);
          });
          return match || fallback;
        };
        return [
          { key: "sot:en-GB", label: "Sound of Text | Female UK" },
          { key: "sot:en-US", label: "Sound of Text | Female US" },
          findVoice({ key: "kokoro:am_adam", label: "People | Male Adam" }, (text) => text.includes("am_adam") || text.includes(" adam")),
          findVoice({ key: "kokoro:af_jessica", label: "People | Female Jessica" }, (text) => text.includes("af_jessica") || text.includes("jessica")),
          findVoice({ key: "kokoro:am_michael", label: "People | Male Michael" }, (text) => text.includes("am_michael") || text.includes("michael")),
          findVoice({ key: "kokoro:bf_maisie", label: "People | Female Maisie" }, (text) => text.includes("maisie") || text.includes("maise")),
        ];
      }

      // Added 2026-06-30: renders Ghost EN paragraph voices with SOT/people voices pinned above the full server list.
      function renderAiAgentGhostEnVoiceOptions(voicePayload = {}) {
        if (!aiAgentGhostEnVoiceSelect) return;
        const payloadRows = (Array.isArray(voicePayload.en) ? voicePayload.en : [])
          .map(normalizeAiAgentGhostEnVoiceRow)
          .filter(Boolean);
        const priorityRows = aiAgentGhostEnPriorityVoiceRows(payloadRows);
        const current = clean(aiAgentGhostEnPreferredVoice || aiAgentGhostEnVoiceSelect.value) || "sot:en-GB";
        const seen = new Set();
        const appendOption = (group, row, priority = false) => {
          const item = normalizeAiAgentGhostEnVoiceRow(row);
          if (!item) return;
          const lowered = item.key.toLowerCase();
          if (seen.has(lowered)) return;
          seen.add(lowered);
          const option = document.createElement("option");
          option.value = item.key;
          option.textContent = item.label;
          if (priority) option.className = "is-priority";
          group.appendChild(option);
        };
        aiAgentGhostEnVoiceSelect.textContent = "";
        const topGroup = document.createElement("optgroup");
        topGroup.label = "Top voices";
        priorityRows.forEach((row) => appendOption(topGroup, row, true));
        const moreGroup = document.createElement("optgroup");
        moreGroup.label = "More voices";
        payloadRows.forEach((row) => appendOption(moreGroup, row, false));
        if (topGroup.children.length) aiAgentGhostEnVoiceSelect.appendChild(topGroup);
        if (moreGroup.children.length) aiAgentGhostEnVoiceSelect.appendChild(moreGroup);
        if (current && !seen.has(current.toLowerCase())) {
          appendOption(moreGroup, { key: current, label: aiAgentGhostEnPreferredVoiceLabel || current }, false);
          if (!moreGroup.parentElement) aiAgentGhostEnVoiceSelect.appendChild(moreGroup);
        }
        aiAgentGhostEnVoiceSelect.value = Array.from(aiAgentGhostEnVoiceSelect.options || []).some((option) => clean(option.value).toLowerCase() === current.toLowerCase())
          ? current
          : "sot:en-GB";
      }

      // Added 2026-06-30: loads the server voice catalog for Ghost EN paragraph audio.
      async function loadAiAgentGhostEnVoiceOptions(force = false) {
        if (!aiAgentGhostEnVoiceSelect) return;
        if (aiAgentGhostEnVoicesLoaded && !force) return;
        aiAgentGhostEnVoicesLoaded = true;
        renderAiAgentGhostEnVoiceOptions({});
        try {
          const { payload } = await fetchSharedChatVoices({ force });
          renderAiAgentGhostEnVoiceOptions(payload || {});
        } catch (error) {
          aiAgentGhostEnVoicesLoaded = false;
          setAiAgentGhostEnStatus("Voice list is using local defaults until the server catalog is ready.", true);
        }
      }

      // Added 2026-06-30: returns the selected Ghost EN paragraph voice key.
      function selectedAiAgentGhostEnParagraphVoice() {
        return clean(aiAgentGhostEnVoiceSelect && aiAgentGhostEnVoiceSelect.value || "") || "sot:en-GB";
      }

      // Added 2026-06-30: returns the visible label for the current Ghost EN paragraph voice.
      function selectedAiAgentGhostEnParagraphVoiceLabel() {
        if (!aiAgentGhostEnVoiceSelect) return selectedAiAgentGhostEnParagraphVoice();
        const option = aiAgentGhostEnVoiceSelect.selectedOptions && aiAgentGhostEnVoiceSelect.selectedOptions[0];
        return clean(option && option.textContent || aiAgentGhostEnPreferredVoiceLabel || selectedAiAgentGhostEnParagraphVoice());
      }

      // Added 2026-06-30: handles dropdown changes and persists the selected Ghost EN paragraph voice.
      function handleAiAgentGhostEnVoiceSelectionChanged() {
        const voice = selectedAiAgentGhostEnParagraphVoice();
        aiAgentGhostEnPreferredVoice = voice;
        aiAgentGhostEnPreferredVoiceLabel = selectedAiAgentGhostEnParagraphVoiceLabel();
        const lowered = voice.toLowerCase();
        if (lowered === "sot:en-us") {
          setAiAgentGhostEnVoiceAccent("us", false, { persist: false });
        } else if (lowered === "sot:en-gb") {
          setAiAgentGhostEnVoiceAccent("uk", false, { persist: false });
        }
        scheduleAiAgentGhostEnVoicePreferenceSave();
        setAiAgentGhostEnStatus(`Ghost EN paragraph voice: ${aiAgentGhostEnPreferredVoiceLabel || voice}.`);
      }

      // Added 2026-06-30: stops any single-word Ghost EN audio before mic or paragraph playback starts.
      function stopAiAgentGhostEnWordAudio() {
        const player = aiAgentGhostEnAudioPlayer;
        aiAgentGhostEnAudioPlayer = null;
        if (player) {
          try {
            player.pause();
            player.currentTime = 0;
          } catch (error) {
          }
        }
        if (aiAgentGhostEnText) {
          aiAgentGhostEnText.querySelectorAll(".ft-ai-ghost-en-token.is-audio-loading, .ft-ai-ghost-en-token.is-audio-playing").forEach((node) => {
            node.classList.remove("is-audio-loading", "is-audio-playing");
          });
        }
      }

      // Added 2026-06-30: toggles the Ghost EN reading badge and brain-style animation.
      function setAiAgentGhostEnReading(active = false, label = "") {
        const isActive = Boolean(active);
        if (aiAgentGhostEnPopup) {
          aiAgentGhostEnPopup.classList.toggle("is-reading", isActive);
        }
        if (aiAgentGhostEnReading) {
          aiAgentGhostEnReading.classList.toggle("is-active", isActive);
          aiAgentGhostEnReading.setAttribute("aria-hidden", isActive ? "false" : "true");
        }
        if (aiAgentGhostEnReadingLabel) {
          aiAgentGhostEnReadingLabel.textContent = clean(label) || "Ghost EN is reading";
        }
        if (aiAgentGhostEnRead) {
          aiAgentGhostEnRead.classList.toggle("is-active", isActive);
          aiAgentGhostEnRead.textContent = isActive ? "Stop" : "Create voice";
        }
      }

      // Added 2026-06-30: clears full-paragraph Ghost EN voice token highlighting.
      function clearAiAgentGhostEnVoiceHighlight() {
        if (aiAgentGhostEnVoiceHighlightFrame) {
          window.cancelAnimationFrame(aiAgentGhostEnVoiceHighlightFrame);
          aiAgentGhostEnVoiceHighlightFrame = 0;
        }
        aiAgentGhostEnTokenNodes().forEach((node) => node.classList.remove("is-voice-reading"));
      }

      // Added 2026-06-30: maps server-created Space_P timing rows onto Ghost EN token nodes.
      function buildAiAgentGhostEnVoiceTimingsFromPayload(tokenNodes = [], timingPayload = null) {
        const nodes = Array.isArray(tokenNodes) ? tokenNodes.filter(Boolean) : [];
        const payload = timingPayload && typeof timingPayload === "object" ? timingPayload : {};
        const audioPayload = payload.audio && typeof payload.audio === "object" ? payload.audio : {};
        const rows = Array.isArray(payload.timings)
          ? payload.timings
          : (Array.isArray(audioPayload.timings) ? audioPayload.timings : []);
        if (!nodes.length || !rows.length) return [];
        const tokens = Array.isArray(payload.timing_tokens)
          ? payload.timing_tokens
          : (Array.isArray(payload.timingTokens)
            ? payload.timingTokens
            : (Array.isArray(audioPayload.timing_tokens)
              ? audioPayload.timing_tokens
              : (Array.isArray(audioPayload.timingTokens) ? audioPayload.timingTokens : [])));
        const usedNodes = new Set();
        let searchCursor = 0;
        const findNodeForTiming = (row, rowIndex) => {
          const serverIndexValue = row ? (row.i ?? row.index ?? row.word ?? rowIndex) : rowIndex;
          const serverIndex = Math.max(0, Math.floor(Number(serverIndexValue) || 0));
          const tokenInfo = tokens[serverIndex] && typeof tokens[serverIndex] === "object" ? tokens[serverIndex] : {};
          const rowTokenText = row ? (row.t || row.word || row.text || "") : "";
          const tokenKey = aiAgentGhostEnWordKey(tokenInfo.t || tokenInfo.text || rowTokenText);
          if (tokenKey) {
            for (let index = searchCursor; index < nodes.length; index += 1) {
              const node = nodes[index];
              if (usedNodes.has(node)) continue;
              const nodeKey = aiAgentGhostEnWordKey(node.dataset.wordKey || node.dataset.word || node.textContent || "");
              if (nodeKey === tokenKey) {
                searchCursor = index + 1;
                usedNodes.add(node);
                return node;
              }
            }
          }
          const indexedNode = nodes[serverIndex] || nodes[rowIndex] || null;
          if (indexedNode && !usedNodes.has(indexedNode)) {
            usedNodes.add(indexedNode);
            searchCursor = Math.max(searchCursor, nodes.indexOf(indexedNode) + 1);
            return indexedNode;
          }
          return null;
        };
        return rows.map((row, rowIndex) => {
          const startValue = row ? (row.s ?? row.start ?? row.startMs ?? 0) : 0;
          const endValue = row ? (row.e ?? row.end ?? row.endMs ?? 0) : 0;
          const start = Math.max(0, Number(startValue) || 0);
          const end = Math.max(start + 1, Number(endValue) || 0);
          const node = findNodeForTiming(row, rowIndex);
          if (!node) return null;
          return {
            node,
            index: Number(node.dataset.ghostEnIndex || rowIndex) || rowIndex,
            start: Math.round(start),
            end: Math.round(end),
          };
        }).filter(Boolean).sort((a, b) => a.start - b.start);
      }

      // Added 2026-06-30: highlights full Ghost EN voice playback with server Space_P timings when available.
      function startAiAgentGhostEnVoiceHighlight(audio = null, timingPayload = null) {
        clearAiAgentGhostEnVoiceHighlight();
        const player = audio && typeof audio === "object" ? audio : null;
        const nodes = aiAgentGhostEnTokenNodes();
        if (!player || !nodes.length) return;
        const durationMs = Number.isFinite(player.duration) && player.duration > 0 ? player.duration * 1000 : 0;
        const serverTimings = buildAiAgentGhostEnVoiceTimingsFromPayload(nodes, timingPayload || aiAgentGhostEnParagraphTimingPayload);
        const timings = serverTimings.length
          ? serverTimings
          : buildAiAgentGhostEnReplayTimings(nodes, durationMs, { fitToDuration: Boolean(durationMs) });
        const setActive = (activeNode = null) => {
          nodes.forEach((node) => node.classList.toggle("is-voice-reading", node === activeNode));
        };
        const activeForMs = (ms) => timings.find((item) => ms >= item.start && ms < item.end);
        const tick = () => {
          if (!player || player.paused || player.ended) {
            clearAiAgentGhostEnVoiceHighlight();
            return;
          }
          const active = activeForMs(Number(player.currentTime || 0) * 1000);
          setActive(active ? active.node : null);
          aiAgentGhostEnVoiceHighlightFrame = window.requestAnimationFrame(tick);
        };
        aiAgentGhostEnVoiceHighlightFrame = window.requestAnimationFrame(tick);
      }

      // Added 2026-06-30: stops paragraph audio and invalidates pending Ghost EN voice creation when needed.
      function stopAiAgentGhostEnParagraphAudio(options = {}) {
        const opts = options && typeof options === "object" ? options : {};
        if (opts.invalidate !== false) {
          aiAgentGhostEnParagraphRequestId += 1;
        }
        aiAgentGhostEnParagraphTimingPayload = null;
        clearAiAgentGhostEnVoiceHighlight();
        const player = aiAgentGhostEnParagraphPlayer;
        aiAgentGhostEnParagraphPlayer = null;
        if (player) {
          try {
            player.pause();
            player.currentTime = 0;
          } catch (error) {
          }
        }
        setAiAgentGhostEnReading(false);
        if (aiAgentGhostEnText) {
          aiAgentGhostEnText.classList.remove("is-paragraph-reading");
        }
        if (opts.clearStatus !== false && opts.message) {
          setAiAgentGhostEnStatus(opts.message, Boolean(opts.isError));
        }
      }

      // Added 2026-06-30: creates server audio for the full Ghost EN paragraph and plays it with reading animation.
      async function playAiAgentGhostEnParagraphVoice() {
        const text = clean(aiAgentGhostEnLastTranslation);
        if (!text) {
          setAiAgentGhostEnStatus("No English translation to read.", true);
          return;
        }
        if (aiAgentGhostEnParagraphPlayer && !aiAgentGhostEnParagraphPlayer.paused && !aiAgentGhostEnParagraphPlayer.ended) {
          stopAiAgentGhostEnParagraphAudio({ message: "Stopped Ghost EN voice." });
          return;
        }
        const requestId = aiAgentGhostEnParagraphRequestId + 1;
        aiAgentGhostEnParagraphRequestId = requestId;
        aiAgentGhostEnParagraphTimingPayload = null;
        if (aiAgentGhostEnRecognizing) {
          stopAiAgentGhostEnMic({ replay: false, announce: false });
        }
        stopAiAgentGhostEnWordAudio();
        stopAiAgentGhostEnMicReplay();
        clearAiAgentGhostEnSpeechReplay();
        stopAiAgentGhostEnParagraphAudio({ invalidate: false, clearStatus: false });
        await loadAiAgentGhostEnVoiceOptions(false);
        const voice = selectedAiAgentGhostEnParagraphVoice();
        const voiceLabel = selectedAiAgentGhostEnParagraphVoiceLabel();
        setAiAgentGhostEnReading(true, "Creating Ghost EN voice");
        setAiAgentGhostEnStatus(`Creating ${voiceLabel} for the English paragraph...`);
        try {
          const { payload } = await fetchAuthJson("/pdf/speak", {
            method: "POST",
            body: JSON.stringify({ text, voice }),
          });
          if (requestId !== aiAgentGhostEnParagraphRequestId) return;
          const audio = payload && payload.audio && typeof payload.audio === "object" ? payload.audio : {};
          const audioPath = clean(audio.path || payload.audio_path || "");
          if (!audioPath) {
            throw new Error("No voice file returned.");
          }
          aiAgentGhostEnParagraphTimingPayload = payload && typeof payload === "object" ? payload : null;
          const player = new Audio(serverAssetUrl(audioPath));
          aiAgentGhostEnParagraphPlayer = player;
          applyAiAgentGhostEnPlaybackRate(player);
          player.onplay = () => {
            if (requestId !== aiAgentGhostEnParagraphRequestId) return;
            if (aiAgentGhostEnText) aiAgentGhostEnText.classList.add("is-paragraph-reading");
            startAiAgentGhostEnVoiceHighlight(player, aiAgentGhostEnParagraphTimingPayload);
            setAiAgentGhostEnReading(true, "Ghost EN is reading");
            setAiAgentGhostEnStatus(`Playing ${clean(payload.voice_label || audio.label || voiceLabel || "Ghost EN voice")}.`);
          };
          player.onended = () => {
            if (aiAgentGhostEnParagraphPlayer === player) aiAgentGhostEnParagraphPlayer = null;
            clearAiAgentGhostEnVoiceHighlight();
            if (aiAgentGhostEnText) aiAgentGhostEnText.classList.remove("is-paragraph-reading");
            setAiAgentGhostEnReading(false);
            setAiAgentGhostEnStatus("Ghost EN voice finished.");
          };
          player.onerror = () => {
            if (requestId !== aiAgentGhostEnParagraphRequestId) return;
            if (aiAgentGhostEnParagraphPlayer === player) aiAgentGhostEnParagraphPlayer = null;
            clearAiAgentGhostEnVoiceHighlight();
            if (aiAgentGhostEnText) aiAgentGhostEnText.classList.remove("is-paragraph-reading");
            setAiAgentGhostEnReading(false);
            setAiAgentGhostEnStatus("Could not play Ghost EN voice.", true);
          };
          await player.play();
        } catch (error) {
          if (requestId !== aiAgentGhostEnParagraphRequestId) return;
          setAiAgentGhostEnReading(false);
          clearAiAgentGhostEnVoiceHighlight();
          if (aiAgentGhostEnText) aiAgentGhostEnText.classList.remove("is-paragraph-reading");
          setAiAgentGhostEnStatus(clean(error && error.message) || "Could not create Ghost EN voice.", true);
        }
      }

      // Added 2026-06-30: returns the current Ghost EN token nodes for speech scoring.
      function aiAgentGhostEnTokenNodes() {
        return aiAgentGhostEnText ? Array.from(aiAgentGhostEnText.querySelectorAll(".ft-ai-ghost-en-token")) : [];
      }

      // Added 2026-06-30: builds normalized word counts from browser speech transcripts.
      function aiAgentGhostEnWordCounts(text = "") {
        const counts = new Map();
        const words = String(text || "").match(/[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?/g) || [];
        words.forEach((word) => {
          const key = aiAgentGhostEnWordKey(word);
          if (!key) return;
          counts.set(key, (counts.get(key) || 0) + 1);
        });
        return counts;
      }

      // Added 2026-06-30: normalizes Ghost EN replay tokens using the Space_W timing approach.
      function normalizeAiAgentGhostEnTimingToken(value = "") {
        return clean(value).replace(/[^0-9A-Za-z']/g, "");
      }

      // Added 2026-06-30: weights Ghost EN replay spans like the Space_W speak card highlighter.
      function aiAgentGhostEnTokenTimingWeight(tokenNode = null) {
        const tokenText = clean(tokenNode && (tokenNode.dataset.word || tokenNode.textContent) || "");
        const normalized = normalizeAiAgentGhostEnTimingToken(tokenText);
        let weight = Math.max(0.45, (normalized || tokenText).length || 1);
        const nextText = clean(tokenNode && tokenNode.nextSibling && tokenNode.nextSibling.textContent || "");
        if (/[.,!?;:]$/.test(tokenText) || /^[.,!?;:]/.test(nextText)) {
          weight += 0.36;
        }
        return Math.max(0.45, weight);
      }

      // Added 2026-06-30: estimates Ghost EN speech duration with the same token/length basis as Space_W.
      function estimateAiAgentGhostEnSpeechDuration(tokenNodes = []) {
        const nodes = Array.isArray(tokenNodes) ? tokenNodes.filter(Boolean) : [];
        const text = nodes.map((node) => clean(node && (node.dataset.word || node.textContent) || "")).join(" ");
        const tokenCount = Math.max(1, nodes.length || clean(text).split(/\s+/).filter(Boolean).length);
        const compactLength = Math.max(1, clean(text).replace(/\s+/g, "").length);
        const estimate = (tokenCount * 420) + (compactLength * 18) + 160;
        return Math.max(720, Math.min(18000, estimate));
      }

      // Added 2026-06-30: builds weighted Ghost EN replay timings instead of equal per-token steps.
      function buildAiAgentGhostEnReplayTimings(tokenNodes = [], durationMs = 0, options = {}) {
        const nodes = Array.isArray(tokenNodes) ? tokenNodes.filter(Boolean) : [];
        if (!nodes.length) return [];
        const opts = options && typeof options === "object" ? options : {};
        const requestedDuration = Math.max(0, Number(durationMs || 0) || 0);
        const estimatedDuration = estimateAiAgentGhostEnSpeechDuration(nodes);
        const baseDuration = opts.fitToDuration && requestedDuration > 0
          ? Math.max(360, requestedDuration)
          : Math.max(requestedDuration, estimatedDuration);
        const weights = nodes.map((node) => aiAgentGhostEnTokenTimingWeight(node));
        const totalWeight = Math.max(0.01, weights.reduce((sum, value) => sum + Number(value || 0), 0));
        let leadMs = Math.min(90, baseDuration * 0.06);
        let tailMs = Math.min(120, baseDuration * 0.08);
        if (baseDuration <= leadMs + tailMs + 90) {
          leadMs = 0;
          tailMs = 0;
        }
        const usableMs = Math.max(80, baseDuration - leadMs - tailMs);
        const minSpan = 45;
        const lastIndex = nodes.length - 1;
        let cursor = leadMs;
        let cumulative = 0;
        return nodes.map((node, index) => {
          const start = cursor;
          let end;
          if (index >= lastIndex) {
            end = Math.max(baseDuration - tailMs, start + 1);
          } else {
            cumulative += Number(weights[index] || 0);
            const predicted = leadMs + (usableMs * cumulative / totalWeight);
            const remaining = Math.max(1, lastIndex - index);
            const maxEnd = baseDuration - tailMs - (remaining * minSpan);
            end = Math.max(start + minSpan, predicted);
            if (maxEnd > start) {
              end = Math.min(end, maxEnd);
            }
          }
          end = Math.min(baseDuration, Math.max(start + 1, end));
          cursor = end;
          return {
            node,
            index: Number(node && node.dataset && node.dataset.ghostEnIndex || index) || index,
            start: Math.round(start),
            end: Math.round(end),
          };
        });
      }

      // Added 2026-06-30: clears the replay pulse over matched Ghost EN speech tokens.
      function clearAiAgentGhostEnSpeechReplay() {
        if (aiAgentGhostEnReplayTimer) {
          window.clearTimeout(aiAgentGhostEnReplayTimer);
          aiAgentGhostEnReplayTimer = 0;
        }
        if (aiAgentGhostEnReplayFrame) {
          window.cancelAnimationFrame(aiAgentGhostEnReplayFrame);
          aiAgentGhostEnReplayFrame = 0;
        }
        if (aiAgentGhostEnPopup) {
          aiAgentGhostEnPopup.classList.remove("is-replaying");
        }
        aiAgentGhostEnTokenNodes().forEach((node) => node.classList.remove("is-speech-replay"));
      }

      // Added 2026-06-30: clears Ghost EN mic scoring highlights.
      function clearAiAgentGhostEnSpeechMatches() {
        aiAgentGhostEnMatchedTokenIndexes = new Set();
        aiAgentGhostEnMatchedTokenTimes = new Map();
        aiAgentGhostEnTokenNodes().forEach((node) => {
          node.classList.remove("is-speech-matched", "is-speech-replay");
        });
        syncAiAgentGhostEnReplayButton();
      }

      // Added 2026-06-30: keeps the Ghost EN replay button aligned with the last mic recording.
      function syncAiAgentGhostEnReplayButton() {
        if (!aiAgentGhostEnReplay) return;
        const hasRecording = Boolean(aiAgentGhostEnLastMicReplayBlob && aiAgentGhostEnLastMicReplayBlob.size);
        const blocked = Boolean(aiAgentGhostEnRecognizing || aiAgentGhostEnRecognition);
        aiAgentGhostEnReplay.disabled = !hasRecording || blocked;
        aiAgentGhostEnReplay.setAttribute("aria-disabled", aiAgentGhostEnReplay.disabled ? "true" : "false");
        aiAgentGhostEnReplay.classList.toggle("is-ready", hasRecording);
        aiAgentGhostEnReplay.classList.toggle("is-active", Boolean(aiAgentGhostEnMicReplaying));
        aiAgentGhostEnReplay.title = hasRecording
          ? (blocked ? "Stop mic before replaying your voice" : "Replay your last mic recording")
          : "Record once with Mic before replaying";
      }

      // Added 2026-06-30: offsets delayed browser recognition events so mic replay follows the user's actual voice.
      const AI_AGENT_GHOST_EN_RECOGNITION_REPLAY_LEAD_MS = 520;

      // Added 2026-06-30: applies live speech-recognition token matches to the translated English text.
      function applyAiAgentGhostEnSpeechMatches(transcript = "") {
        const counts = aiAgentGhostEnWordCounts(transcript);
        const used = new Map();
        const matchedIndexes = new Set();
        const nodes = aiAgentGhostEnTokenNodes();
        const newlyMatched = [];
        nodes.forEach((node, index) => {
          const key = aiAgentGhostEnWordKey(node.dataset.wordKey || node.textContent || "");
          const usedCount = used.get(key) || 0;
          const available = key ? (counts.get(key) || 0) : 0;
          const matched = Boolean(key && usedCount < available);
          if (matched) {
            used.set(key, usedCount + 1);
            matchedIndexes.add(index);
            if (!aiAgentGhostEnMatchedTokenTimes.has(index)) {
              newlyMatched.push(index);
            }
          }
          node.classList.toggle("is-speech-matched", matched);
        });
        if (newlyMatched.length) {
          const startedAt = Number(aiAgentGhostEnMicStartedAt || 0) || performance.now();
          const eventMs = Math.max(0, performance.now() - startedAt - AI_AGENT_GHOST_EN_RECOGNITION_REPLAY_LEAD_MS);
          const spacingMs = newlyMatched.length > 1 ? 165 : 0;
          const firstMs = Math.max(0, eventMs - (spacingMs * (newlyMatched.length - 1)));
          newlyMatched.forEach((index, order) => {
            aiAgentGhostEnMatchedTokenTimes.set(index, firstMs + (order * spacingMs));
          });
        }
        aiAgentGhostEnMatchedTokenIndexes = matchedIndexes;
        return { matched: matchedIndexes.size, total: nodes.length };
      }

      // Added 2026-06-30: reuses the actual live-match timestamps for mic replay highlighting.
      function buildAiAgentGhostEnMatchedReplayTimings(matchedNodes = [], durationMs = 0) {
        const nodes = Array.isArray(matchedNodes) ? matchedNodes.filter(Boolean) : [];
        if (!nodes.length || !aiAgentGhostEnMatchedTokenTimes || !aiAgentGhostEnMatchedTokenTimes.size) return [];
        const duration = Math.max(0, Number(durationMs || 0) || 0);
        const rows = nodes.map((node, fallbackIndex) => {
          const index = Number(node && node.dataset && node.dataset.ghostEnIndex || fallbackIndex) || fallbackIndex;
          const start = Number(aiAgentGhostEnMatchedTokenTimes.get(index));
          if (!Number.isFinite(start)) return null;
          return { node, index, start: Math.max(0, start) };
        }).filter(Boolean).sort((a, b) => a.start - b.start);
        if (!rows.length) return [];
        return rows.map((row, order) => {
          const next = rows[order + 1] || null;
          const start = Math.max(0, row.start);
          let end = next ? Math.max(start + 95, next.start - 35) : start + 520;
          if (duration > 0) {
            end = Math.min(Math.max(start + 95, end), duration);
          }
          return {
            node: row.node,
            index: row.index,
            start: Math.round(start),
            end: Math.round(Math.max(start + 95, end)),
          };
        });
      }

      // Added 2026-06-30: replays Ghost EN matched tokens on a Space_W-style weighted timeline.
      function replayAiAgentGhostEnSpeechMatches(options = {}) {
        clearAiAgentGhostEnSpeechReplay();
        const opts = options && typeof options === "object" ? options : {};
        const nodes = aiAgentGhostEnTokenNodes();
        const matchedNodes = nodes.filter((node, index) => aiAgentGhostEnMatchedTokenIndexes.has(index));
        if (!matchedNodes.length) {
          setAiAgentGhostEnStatus("No matched English tokens to replay.", true);
          return;
        }
        const audio = opts.audio && typeof opts.audio === "object" ? opts.audio : null;
        const audioDurationMs = audio && Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration * 1000 : 0;
        const requestedDuration = Math.max(0, Number(opts.durationMs || audioDurationMs || 0) || 0);
        const matchedTimings = opts.useMatchedTimeline !== false
          ? buildAiAgentGhostEnMatchedReplayTimings(matchedNodes, requestedDuration)
          : [];
        const timings = matchedTimings.length
          ? matchedTimings
          : buildAiAgentGhostEnReplayTimings(matchedNodes, requestedDuration, { fitToDuration: Boolean(requestedDuration) });
        const totalMs = Math.max(...timings.map((item) => Number(item.end || 0) || 0), 0);
        if (aiAgentGhostEnPopup) {
          aiAgentGhostEnPopup.classList.add("is-replaying");
        }
        setAiAgentGhostEnMicReplayActive(true);
        nodes.forEach((node) => node.classList.remove("is-speech-matched", "is-speech-replay"));
        const setReplayActive = (activeNode = null) => {
          matchedNodes.forEach((node) => node.classList.toggle("is-speech-replay", node === activeNode));
        };
        const finish = () => {
          clearAiAgentGhostEnSpeechReplay();
          setAiAgentGhostEnMicReplayActive(false);
          if (opts.clearMatchedOnEnd !== false) {
            aiAgentGhostEnTokenNodes().forEach((node) => node.classList.remove("is-speech-matched", "is-speech-replay"));
          }
          setAiAgentGhostEnStatus(`Replayed ${matchedNodes.length}/${nodes.length} matched tokens.`);
        };
        const activeForMs = (ms) => timings.find((item) => ms >= item.start && ms < item.end);
        if (audio) {
          const tickAudio = () => {
            if (!audio || audio.paused || audio.ended) {
              finish();
              return;
            }
            const active = activeForMs(Number(audio.currentTime || 0) * 1000);
            setReplayActive(active ? active.node : null);
            aiAgentGhostEnReplayFrame = window.requestAnimationFrame(tickAudio);
          };
          aiAgentGhostEnReplayFrame = window.requestAnimationFrame(tickAudio);
          return;
        }
        const startedAt = performance.now();
        const tickSynthetic = () => {
          const ms = performance.now() - startedAt;
          if (ms >= totalMs) {
            finish();
            return;
          }
          const active = activeForMs(ms);
          setReplayActive(active ? active.node : null);
          aiAgentGhostEnReplayFrame = window.requestAnimationFrame(tickSynthetic);
        };
        aiAgentGhostEnReplayFrame = window.requestAnimationFrame(tickSynthetic);
      }

      // Added 2026-06-30: stops Ghost EN local mic replay audio and releases its blob URL.
      function stopAiAgentGhostEnMicReplay(options = {}) {
        const opts = options && typeof options === "object" ? options : {};
        const player = aiAgentGhostEnMicReplayAudio;
        aiAgentGhostEnMicReplayAudio = null;
        if (player) {
          try {
            player.pause();
            player.currentTime = 0;
          } catch (error) {
          }
        }
        if (aiAgentGhostEnMicReplayUrl) {
          URL.revokeObjectURL(aiAgentGhostEnMicReplayUrl);
          aiAgentGhostEnMicReplayUrl = "";
        }
        if (aiAgentGhostEnPopup) {
          aiAgentGhostEnPopup.classList.remove("is-mic-replay");
        }
        clearAiAgentGhostEnSpeechReplay();
        setAiAgentGhostEnMicReplayActive(false);
        if (opts.clearHighlights) {
          aiAgentGhostEnTokenNodes().forEach((node) => node.classList.remove("is-speech-matched", "is-speech-replay"));
        }
        if (opts.message) {
          setAiAgentGhostEnStatus(opts.message, Boolean(opts.isError));
        }
      }

      // Added 2026-06-30: releases Ghost EN microphone stream tracks after recording.
      function cleanupAiAgentGhostEnMicStream() {
        const stream = aiAgentGhostEnMicStream;
        aiAgentGhostEnMicStream = null;
        if (stream && typeof stream.getTracks === "function") {
          stream.getTracks().forEach((track) => {
            try {
              track.stop();
            } catch (error) {
            }
          });
        }
      }

      // Added 2026-06-30: starts a local MediaRecorder clip so Ghost EN can replay the user's voice.
      async function startAiAgentGhostEnLocalRecorder() {
        aiAgentGhostEnMicChunks = [];
        if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function" || !window.MediaRecorder) {
          return false;
        }
        try {
          aiAgentGhostEnMicStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          });
          const mimeType = typeof selectedRecorderMime === "function" ? selectedRecorderMime() : "";
          const recorder = new MediaRecorder(aiAgentGhostEnMicStream, mimeType ? { mimeType } : undefined);
          aiAgentGhostEnMicRecorder = recorder;
          recorder.ondataavailable = (event) => {
            if (event.data && event.data.size) {
              aiAgentGhostEnMicChunks.push(event.data);
            }
          };
          recorder.onerror = () => {
            setAiAgentGhostEnStatus("Mic is listening, but local replay recording had an error.", true);
          };
          recorder.start(250);
          aiAgentGhostEnMicStartedAt = performance.now();
          return true;
        } catch (error) {
          aiAgentGhostEnMicRecorder = null;
          aiAgentGhostEnMicChunks = [];
          cleanupAiAgentGhostEnMicStream();
          return false;
        }
      }

      // Added 2026-06-30: stops the Ghost EN MediaRecorder and returns the captured voice blob.
      function stopAiAgentGhostEnLocalRecorder() {
        const recorder = aiAgentGhostEnMicRecorder;
        aiAgentGhostEnMicRecorder = null;
        return new Promise((resolve) => {
          if (!recorder) {
            aiAgentGhostEnMicChunks = [];
            cleanupAiAgentGhostEnMicStream();
            resolve(null);
            return;
          }
          let settled = false;
          const finish = () => {
            if (settled) return;
            settled = true;
            const chunks = aiAgentGhostEnMicChunks.slice();
            const type = clean(recorder.mimeType || (chunks[0] && chunks[0].type) || "audio/webm");
            const blob = chunks.length ? new Blob(chunks, { type }) : null;
            aiAgentGhostEnMicChunks = [];
            cleanupAiAgentGhostEnMicStream();
            resolve(blob);
          };
          recorder.onstop = finish;
          recorder.onerror = finish;
          try {
            if (recorder.state && recorder.state !== "inactive") {
              recorder.stop();
            } else {
              finish();
            }
          } catch (error) {
            finish();
          }
        });
      }

      // Added 2026-06-30: replays the user's Ghost EN mic recording while pulsing recognized tokens.
      async function playAiAgentGhostEnMicReplayBlob(blob = null) {
        if (!blob || !blob.size) {
          replayAiAgentGhostEnSpeechMatches({ clearMatchedOnEnd: true });
          return;
        }
        aiAgentGhostEnLastMicReplayBlob = blob;
        syncAiAgentGhostEnReplayButton();
        stopAiAgentGhostEnMicReplay();
        aiAgentGhostEnTokenNodes().forEach((node) => node.classList.remove("is-speech-matched", "is-speech-replay"));
        aiAgentGhostEnMicReplayUrl = URL.createObjectURL(blob);
        const player = new Audio(aiAgentGhostEnMicReplayUrl);
        aiAgentGhostEnMicReplayAudio = player;
        if (typeof normalizeAudioPlaybackSpeed === "function") {
          normalizeAudioPlaybackSpeed(player);
        }
        let visualStarted = false;
        const startVisualReplay = () => {
          if (visualStarted) return;
          visualStarted = true;
          const durationMs = Number.isFinite(player.duration) && player.duration > 0 ? player.duration * 1000 : 0;
          replayAiAgentGhostEnSpeechMatches({ audio: player, durationMs, clearMatchedOnEnd: true });
        };
        player.onplay = () => {
          if (aiAgentGhostEnPopup) aiAgentGhostEnPopup.classList.add("is-mic-replay");
          setAiAgentGhostEnMicReplayActive(true);
          syncAiAgentGhostEnReplayButton();
          setAiAgentGhostEnStatus("Replaying your mic and matched English tokens.");
          startVisualReplay();
        };
        player.onended = () => {
          if (aiAgentGhostEnPopup) aiAgentGhostEnPopup.classList.remove("is-mic-replay");
          aiAgentGhostEnMicReplayAudio = null;
          if (aiAgentGhostEnMicReplayUrl) {
            URL.revokeObjectURL(aiAgentGhostEnMicReplayUrl);
            aiAgentGhostEnMicReplayUrl = "";
          }
          setAiAgentGhostEnMicReplayActive(false);
          syncAiAgentGhostEnReplayButton();
          clearAiAgentGhostEnSpeechReplay();
          aiAgentGhostEnTokenNodes().forEach((node) => node.classList.remove("is-speech-matched", "is-speech-replay"));
          setAiAgentGhostEnStatus(`Replayed ${aiAgentGhostEnMatchedTokenIndexes.size}/${aiAgentGhostEnTokenNodes().length} matched tokens.`);
        };
        player.onerror = () => {
          if (aiAgentGhostEnPopup) aiAgentGhostEnPopup.classList.remove("is-mic-replay");
          aiAgentGhostEnMicReplayAudio = null;
          if (aiAgentGhostEnMicReplayUrl) {
            URL.revokeObjectURL(aiAgentGhostEnMicReplayUrl);
            aiAgentGhostEnMicReplayUrl = "";
          }
          setAiAgentGhostEnMicReplayActive(false);
          syncAiAgentGhostEnReplayButton();
          setAiAgentGhostEnStatus("Could not replay mic audio; replaying token highlights.", true);
          replayAiAgentGhostEnSpeechMatches({ clearMatchedOnEnd: true });
        };
        try {
          await player.play();
        } catch (error) {
          aiAgentGhostEnMicReplayAudio = null;
          if (aiAgentGhostEnMicReplayUrl) {
            URL.revokeObjectURL(aiAgentGhostEnMicReplayUrl);
            aiAgentGhostEnMicReplayUrl = "";
          }
          syncAiAgentGhostEnReplayButton();
          setAiAgentGhostEnStatus("Could not play mic recording; replaying token highlights.", true);
          replayAiAgentGhostEnSpeechMatches({ clearMatchedOnEnd: true });
        }
      }

      // Added 2026-06-30: replays the last Ghost EN mic recording from a dedicated Replay button.
      async function replayAiAgentGhostEnMicSample() {
        if (aiAgentGhostEnRecognizing || aiAgentGhostEnRecognition) {
          setAiAgentGhostEnStatus("Stop mic before replaying your voice.", true);
          syncAiAgentGhostEnReplayButton();
          return;
        }
        const blob = aiAgentGhostEnLastMicReplayBlob;
        if (!blob || !blob.size) {
          setAiAgentGhostEnStatus("Record once with Mic before replaying your voice.", true);
          syncAiAgentGhostEnReplayButton();
          return;
        }
        await playAiAgentGhostEnMicReplayBlob(blob);
      }

      // Added 2026-06-30: toggles Ghost EN mic button state for pronunciation testing.
      function setAiAgentGhostEnMicActive(active = false) {
        const isActive = Boolean(active);
        if (aiAgentGhostEnPopup) {
          aiAgentGhostEnPopup.classList.toggle("is-recording", isActive);
        }
        if (aiAgentGhostEnMic) {
          aiAgentGhostEnMic.classList.toggle("is-active", isActive);
          aiAgentGhostEnMic.setAttribute("aria-pressed", isActive ? "true" : "false");
          if (!isActive && aiAgentGhostEnMicReplaying) {
            aiAgentGhostEnMic.classList.add("is-active");
            aiAgentGhostEnMic.setAttribute("aria-pressed", "true");
            aiAgentGhostEnMic.textContent = "Stop";
          } else {
            aiAgentGhostEnMic.textContent = isActive ? "Stop mic" : "Mic";
          }
        }
        syncAiAgentGhostEnReplayButton();
      }

      // Added 2026-06-30: lets the Mic button stop Ghost EN replay instead of starting a new recording.
      function setAiAgentGhostEnMicReplayActive(active = false) {
        aiAgentGhostEnMicReplaying = Boolean(active);
        if (aiAgentGhostEnPopup) {
          aiAgentGhostEnPopup.classList.toggle("is-mic-replay", aiAgentGhostEnMicReplaying);
        }
        if (aiAgentGhostEnMic && !aiAgentGhostEnRecognizing && !aiAgentGhostEnRecognition) {
          aiAgentGhostEnMic.classList.toggle("is-active", aiAgentGhostEnMicReplaying);
          aiAgentGhostEnMic.setAttribute("aria-pressed", aiAgentGhostEnMicReplaying ? "true" : "false");
          aiAgentGhostEnMic.textContent = aiAgentGhostEnMicReplaying ? "Stop" : "Mic";
        }
        syncAiAgentGhostEnReplayButton();
      }

      // Added 2026-06-30: chooses a browser recognition locale from the selected Ghost EN voice.
      function aiAgentGhostEnRecognitionLanguage() {
        const voice = selectedAiAgentGhostEnParagraphVoice().toLowerCase();
        if (voice.includes("en-gb") || voice.includes("kokoro:bf_") || voice.includes("kokoro:bm_") || voice.includes("british") || voice.includes("uk")) {
          return "en-GB";
        }
        return "en-US";
      }

      // Added 2026-06-30: finishes Ghost EN speech scoring and starts replay if requested.
      function finishAiAgentGhostEnMic(options = {}) {
        const opts = options && typeof options === "object" ? options : {};
        const transcript = clean(`${aiAgentGhostEnRecognitionTranscript} ${aiAgentGhostEnRecognitionChunk}`);
        aiAgentGhostEnRecognitionChunk = "";
        const score = applyAiAgentGhostEnSpeechMatches(transcript);
        aiAgentGhostEnRecognizing = false;
        aiAgentGhostEnRecognition = null;
        setAiAgentGhostEnMicActive(false);
        if (opts.announce !== false) {
          setAiAgentGhostEnStatus(score.matched
            ? `Mic stopped. Matched ${score.matched}/${score.total} English tokens.`
            : "Mic stopped. No English tokens matched yet.",
            !score.matched);
        }
        if (opts.replay !== false) {
          const replayPromise = opts.replayBlobPromise && typeof opts.replayBlobPromise.then === "function"
            ? opts.replayBlobPromise
            : Promise.resolve(null);
          replayPromise.then((blob) => {
            if (blob) {
              void playAiAgentGhostEnMicReplayBlob(blob);
            } else {
              replayAiAgentGhostEnSpeechMatches();
            }
          }).catch(() => replayAiAgentGhostEnSpeechMatches());
        }
      }

      // Added 2026-06-30: starts Ghost EN pronunciation recognition and live token highlighting.
      async function startAiAgentGhostEnMic() {
        const text = clean(aiAgentGhostEnLastTranslation);
        if (!text) {
          setAiAgentGhostEnStatus("No English translation to test.", true);
          return;
        }
        const RecognitionCtor = typeof browserSpeechRecognitionCtor === "function"
          ? browserSpeechRecognitionCtor()
          : (window.SpeechRecognition || window.webkitSpeechRecognition || null);
        if (!RecognitionCtor) {
          setAiAgentGhostEnStatus("Browser speech recognition is unavailable here.", true);
          return;
        }
        stopAiAgentGhostEnParagraphAudio({ clearStatus: false });
        stopAiAgentGhostEnWordAudio();
        stopAiAgentGhostEnMicReplay();
        clearAiAgentGhostEnSpeechReplay();
        clearAiAgentGhostEnSpeechMatches();
        aiAgentGhostEnRecognitionTranscript = "";
        aiAgentGhostEnRecognitionChunk = "";
        aiAgentGhostEnMatchedTokenTimes = new Map();
        aiAgentGhostEnMicStartedAt = 0;
        aiAgentGhostEnLastMicReplayBlob = null;
        syncAiAgentGhostEnReplayButton();
        aiAgentGhostEnRecognitionManualStop = false;
        const localRecording = await startAiAgentGhostEnLocalRecorder();
        if (!localRecording) {
          aiAgentGhostEnMicStartedAt = performance.now();
        }
        const recognition = new RecognitionCtor();
        aiAgentGhostEnRecognition = recognition;
        aiAgentGhostEnRecognizing = true;
        setAiAgentGhostEnMicActive(true);
        recognition.lang = aiAgentGhostEnRecognitionLanguage();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.onresult = (event) => {
          if (aiAgentGhostEnRecognition !== recognition || !aiAgentGhostEnRecognizing) return;
          let finalText = "";
          let interim = "";
          const startIndex = Number(event && event.resultIndex || 0) || 0;
          const results = event && event.results ? event.results : [];
          for (let index = startIndex; index < results.length; index += 1) {
            const result = results[index];
            const textPart = clean(result && result[0] && result[0].transcript || "");
            if (!textPart) continue;
            if (result.isFinal) {
              finalText = clean(`${finalText} ${textPart}`);
            } else {
              interim = clean(`${interim} ${textPart}`);
            }
          }
          if (finalText) {
            aiAgentGhostEnRecognitionTranscript = clean(`${aiAgentGhostEnRecognitionTranscript} ${finalText}`);
          }
          aiAgentGhostEnRecognitionChunk = interim;
          const score = applyAiAgentGhostEnSpeechMatches(`${aiAgentGhostEnRecognitionTranscript} ${aiAgentGhostEnRecognitionChunk}`);
          setAiAgentGhostEnStatus(`Mic listening... matched ${score.matched}/${score.total} English tokens.`);
        };
        recognition.onerror = (event) => {
          const code = clean(event && event.error || "");
          if (code && code !== "no-speech") {
            setAiAgentGhostEnStatus(`Mic check: ${code}`, true);
          }
          if (code === "not-allowed" || code === "service-not-allowed") {
            aiAgentGhostEnRecognitionManualStop = true;
            aiAgentGhostEnRecognizing = false;
          }
        };
        recognition.onend = () => {
          if (aiAgentGhostEnRecognition !== recognition) return;
          if (aiAgentGhostEnRecognizing && !aiAgentGhostEnRecognitionManualStop) {
            window.setTimeout(() => {
              if (aiAgentGhostEnRecognition !== recognition || !aiAgentGhostEnRecognizing || aiAgentGhostEnRecognitionManualStop) return;
              try {
                recognition.start();
              } catch (error) {
                aiAgentGhostEnRecognitionManualStop = true;
                aiAgentGhostEnRecognizing = false;
                const replayBlobPromise = stopAiAgentGhostEnLocalRecorder();
                finishAiAgentGhostEnMic({ replay: true, replayBlobPromise });
              }
            }, 120);
            return;
          }
          const replayBlobPromise = stopAiAgentGhostEnLocalRecorder();
          finishAiAgentGhostEnMic({ replay: true, replayBlobPromise });
        };
        try {
          recognition.start();
          setAiAgentGhostEnStatus(`Mic listening with ${recognition.lang}. Read the English tokens.`);
        } catch (error) {
          aiAgentGhostEnRecognizing = false;
          aiAgentGhostEnRecognition = null;
          setAiAgentGhostEnMicActive(false);
          void stopAiAgentGhostEnLocalRecorder();
          setAiAgentGhostEnStatus(clean(error && error.message) || "Could not start Ghost EN mic.", true);
        }
      }

      // Added 2026-06-30: stops Ghost EN mic recognition and replays the recognized tokens.
      function stopAiAgentGhostEnMic(options = {}) {
        const opts = options && typeof options === "object" ? options : {};
        const recognition = aiAgentGhostEnRecognition;
        aiAgentGhostEnRecognitionManualStop = true;
        aiAgentGhostEnRecognizing = false;
        aiAgentGhostEnRecognition = null;
        const replayBlobPromise = stopAiAgentGhostEnLocalRecorder();
        if (recognition) {
          try {
            recognition.stop();
          } catch (error) {
            try {
              recognition.abort();
            } catch (_error) {
            }
          }
        }
        finishAiAgentGhostEnMic({
          replay: opts.replay !== false,
          announce: opts.announce !== false,
          replayBlobPromise,
        });
      }

      // Added 2026-06-30: toggles Ghost EN mic pronunciation mode from the popup button.
      async function toggleAiAgentGhostEnMic() {
        if (aiAgentGhostEnMicReplaying || aiAgentGhostEnMicReplayAudio) {
          stopAiAgentGhostEnMicReplay({ clearHighlights: true, message: "Stopped mic replay." });
          return;
        }
        if (aiAgentGhostEnRecognizing || aiAgentGhostEnRecognition) {
          stopAiAgentGhostEnMic({ replay: true });
          return;
        }
        await startAiAgentGhostEnMic();
      }

      // Added 2026-06-30: positions the translated Ghost EN popup above the Ghost AI composer.
      function positionAiAgentGhostEnPopup() {
        if (!aiAgentGhostEnPopup) return;
        const margin = 18;
        let left = margin;
        let bottom = 430;
        if (aiAgentPopup) {
          const rect = aiAgentPopup.getBoundingClientRect();
          if (rect && rect.width) {
            left = Math.max(margin, rect.left);
            bottom = Math.max(margin, window.innerHeight - rect.top + 12);
          }
        }
        const maxBottom = Math.max(margin, window.innerHeight - 210);
        const safeBottom = Math.min(bottom, maxBottom);
        const maxHeight = Math.max(190, Math.min(360, window.innerHeight - safeBottom - margin));
        aiAgentGhostEnPopup.style.left = `${left}px`;
        aiAgentGhostEnPopup.style.bottom = `${safeBottom}px`;
        aiAgentGhostEnPopup.style.maxHeight = `${maxHeight}px`;
        positionAiAgentGhostEnDetail();
      }

      // Added 2026-06-30: places the word detail panel to the right of the Ghost AI/Ghost EN stack when space allows.
      function positionAiAgentGhostEnDetail() {
        if (!aiAgentGhostEnDetail) return;
        const margin = 18;
        const gap = 16;
        const rects = [aiAgentPopup, aiAgentGhostEnPopup]
          .filter(Boolean)
          .map((node) => node.getBoundingClientRect())
          .filter((rect) => rect && rect.width && rect.height);
        const stackRight = rects.reduce((value, rect) => Math.max(value, rect.right), margin);
        const stackTop = rects.reduce((value, rect) => Math.min(value, rect.top), window.innerHeight - 340);
        const availableRight = window.innerWidth - stackRight - gap - margin;
        if (availableRight >= 300) {
          aiAgentGhostEnDetail.style.left = `${stackRight + gap}px`;
          aiAgentGhostEnDetail.style.right = "auto";
          aiAgentGhostEnDetail.style.width = `${Math.min(390, availableRight)}px`;
        } else {
          aiAgentGhostEnDetail.style.left = "auto";
          aiAgentGhostEnDetail.style.right = `${margin}px`;
          aiAgentGhostEnDetail.style.width = "";
        }
        aiAgentGhostEnDetail.style.top = `${Math.max(72, Math.min(stackTop, window.innerHeight - 260))}px`;
        aiAgentGhostEnDetail.style.bottom = "auto";
      }

      // Added 2026-06-30: builds compact Vietnamese dictionary detail maps for translated Ghost EN tokens.
      function buildAiAgentGhostEnDetailMap(stats = {}) {
        const source = stats && typeof stats === "object" ? stats : {};
        const rows = []
          .concat(Array.isArray(source.words) ? source.words : [])
          .concat(Array.isArray(source.unknown_words) ? source.unknown_words : [])
          .concat(Array.isArray(source.known_words) ? source.known_words : [])
          .concat(Array.isArray(source.phrases) ? source.phrases : [])
          .concat(Array.isArray(source.unknown_phrases) ? source.unknown_phrases : [])
          .concat(Array.isArray(source.known_phrases) ? source.known_phrases : [])
          .concat(Array.isArray(source.phrasal_verbs) ? source.phrasal_verbs : [])
          .concat(Array.isArray(source.unknown_phrasal_verbs) ? source.unknown_phrasal_verbs : []);
        const map = {};
        const cleanList = (value) => {
          const list = Array.isArray(value) ? value : [];
          const seen = new Set();
          return list.map((item) => clean(item)).filter((item) => {
            const key = aiAgentGhostEnWordKey(item);
            if (!key || seen.has(key)) return false;
            seen.add(key);
            return true;
          }).slice(0, 10);
        };
        const cleanExamples = (value, fallbackEn = "", fallbackVi = "") => {
          const list = Array.isArray(value) ? value : [];
          const out = [];
          list.forEach((item) => {
            if (!item) return;
            if (typeof item === "object") {
              const en = clean(item.en || item.english || item.example || "");
              const vi = clean(item.vi || item.vietnamese || item.translation || "");
              if (en || vi) out.push({ en, vi });
            } else {
              const en = clean(item);
              if (en) out.push({ en, vi: "" });
            }
          });
          if (!out.length && (clean(fallbackEn) || clean(fallbackVi))) {
            out.push({ en: clean(fallbackEn), vi: clean(fallbackVi) });
          }
          return out.slice(0, 6);
        };
        const mergeDetail = (base = {}, incoming = {}) => {
          const next = { ...(base && typeof base === "object" ? base : {}) };
          const item = incoming && typeof incoming === "object" ? incoming : {};
          [
            "word", "surface", "meaning", "pron", "type", "pron_us", "pron_uk",
            "ipa", "ipa_us", "ipa_uk", "usage", "context", "note", "kind",
          ].forEach((field) => {
            const value = clean(item[field] || "");
            if (!clean(next[field] || "") && value) next[field] = value;
          });
          ["collocations", "examples", "notes"].forEach((field) => {
            const value = Array.isArray(item[field]) ? item[field] : [];
            if (!Array.isArray(next[field]) || !next[field].length) next[field] = value;
          });
          return next;
        };
        const addDetail = (keyValue, item) => {
          const key = aiAgentGhostEnWordKey(keyValue);
          if (!key || !item || typeof item !== "object") return;
          const detail = {
            word: clean(item.word || item.w || keyValue || ""),
            surface: clean(item.surface || item.token || item.original || keyValue || ""),
            meaning: clean(item.meaning || item.m || ""),
            pron: clean(item.pron || item.p || ""),
            type: clean(item.type || item.ty || item.pos || ""),
            pron_us: clean(item.pron_us || item.pronUS || ""),
            pron_uk: clean(item.pron_uk || item.pronUK || ""),
            ipa: clean(item.ipa || item.surface_ipa || item.surfaceIpa || ""),
            ipa_us: clean(item.ipa_us || item.ipaUS || item.surface_ipa_us || item.surfaceIpaUS || ""),
            ipa_uk: clean(item.ipa_uk || item.ipaUK || item.surface_ipa_uk || item.surfaceIpaUK || ""),
            usage: clean(item.usage || ""),
            context: clean(item.context || ""),
            note: clean(item.note || item.notes_text || ""),
            kind: clean(item.kind || ""),
            collocations: cleanList(item.collocations),
            examples: cleanExamples(item.examples, item.example || "", item.example_vi || item.exampleVi || ""),
            notes: cleanList(item.notes),
          };
          if (!detail.word) detail.word = keyValue;
          if (!Array.isArray(map[key])) map[key] = [];
          const detailKey = aiAgentGhostEnWordKey(detail.word);
          const existingIndex = map[key].findIndex((existing) => aiAgentGhostEnWordKey(existing.word) === detailKey);
          if (existingIndex >= 0) {
            map[key][existingIndex] = mergeDetail(map[key][existingIndex], detail);
          } else {
            map[key].push(detail);
          }
        };
        rows.forEach((item) => {
          if (!item || typeof item !== "object") return;
          addDetail(item.word || item.w || "", item);
          addDetail(item.surface || item.token || item.original || "", item);
        });
        const tokenDetails = source.token_details && typeof source.token_details === "object"
          ? source.token_details
          : (source.tokenDetails && typeof source.tokenDetails === "object" ? source.tokenDetails : {});
        Object.entries(tokenDetails).forEach(([token, details]) => {
          const list = Array.isArray(details) ? details : [details];
          list.forEach((item) => {
            addDetail(token, item);
            addDetail(item && (item.word || item.w), item);
          });
        });
        return map;
      }

      // Added 2026-06-30: renders translated English as hoverable words without losing line breaks.
      function renderAiAgentGhostEnText(text = "", vocabulary = {}) {
        if (!aiAgentGhostEnText) return;
        aiAgentGhostEnLastTranslation = String(text || "");
        aiAgentGhostEnParagraphTimingPayload = null;
        aiAgentGhostEnDetailMap = buildAiAgentGhostEnDetailMap(vocabulary);
        aiAgentGhostEnText.innerHTML = "";
        const parts = aiAgentGhostEnLastTranslation.match(/[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?|\s+|[^\sA-Za-z0-9]+/g) || [];
        let tokenCount = 0;
        parts.forEach((part) => {
          if (/^[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?$/.test(part)) {
            const key = aiAgentGhostEnWordKey(part);
            const token = document.createElement("span");
            token.className = "ft-ai-ghost-en-token";
            token.tabIndex = 0;
            token.dataset.wordKey = key;
            token.dataset.word = part;
            token.dataset.ghostEnIndex = String(tokenCount);
            token.textContent = part;
            if (key && aiAgentGhostEnDetailMap[key]) {
              token.classList.add("has-detail");
            }
            aiAgentGhostEnText.appendChild(token);
            tokenCount += 1;
            return;
          }
          aiAgentGhostEnText.appendChild(document.createTextNode(part));
        });
        setAiAgentGhostEnStatus(tokenCount
          ? "Hover any English word for Vietnamese detail. Click a word to hear it."
          : "Translation ready.");
        clearAiAgentGhostEnSpeechReplay();
        clearAiAgentGhostEnSpeechMatches();
      }

      // Added 2026-06-30: opens the Ghost EN translation popup above the Ghost AI input.
      function openAiAgentGhostEnPopup() {
        if (!aiAgentGhostEnPopup) return;
        aiAgentGhostEnPopup.classList.add("is-open");
        aiAgentGhostEnPopup.setAttribute("aria-hidden", "false");
        setAiAgentGhostEnVoiceAccent(aiAgentGhostEnVoiceAccent, false, { persist: false });
        syncAiAgentGhostEnSpeedBadge();
        renderAiAgentGhostEnVoiceOptions({});
        void loadAiAgentGhostEnVoiceOptions(false);
        positionAiAgentGhostEnPopup();
        syncAiAgentGhostEnReplayButton();
        try {
          if (!aiAgentGhostEnPopup.contains(document.activeElement)) {
            aiAgentGhostEnPopup.focus({ preventScroll: true });
          }
        } catch (error) {
        }
      }

      // Added 2026-06-30: closes Ghost EN and its right-side Vietnamese detail panel.
      function closeAiAgentGhostEnPopup() {
        window.clearTimeout(aiAgentGhostEnHoverTimer);
        stopAiAgentGhostEnWordAudio();
        stopAiAgentGhostEnParagraphAudio({ clearStatus: false });
        if (aiAgentGhostEnRecognizing || aiAgentGhostEnRecognition) {
          stopAiAgentGhostEnMic({ replay: false, announce: false });
        }
        stopAiAgentGhostEnMicReplay();
        clearAiAgentGhostEnSpeechReplay();
        if (aiAgentGhostEnPopup) {
          aiAgentGhostEnPopup.classList.remove("is-open", "is-loading", "is-reading", "is-recording", "is-replaying", "is-mic-replay");
          aiAgentGhostEnPopup.setAttribute("aria-hidden", "true");
        }
        if (aiAgentGhostEnDetail) {
          aiAgentGhostEnDetail.classList.add("is-hidden");
          aiAgentGhostEnDetail.setAttribute("aria-hidden", "true");
        }
        if (aiAgentGhostEnText) {
          aiAgentGhostEnText.classList.remove("is-paragraph-reading");
          aiAgentGhostEnText.querySelectorAll(".ft-ai-ghost-en-token.is-active, .ft-ai-ghost-en-token.is-speech-matched, .ft-ai-ghost-en-token.is-speech-replay, .ft-ai-ghost-en-token.is-voice-reading").forEach((node) => {
            node.classList.remove("is-active", "is-speech-matched", "is-speech-replay", "is-voice-reading");
          });
        }
      }

      // Added 2026-06-30: shows Vietnamese meaning detail for a hovered Ghost EN word.
      function showAiAgentGhostEnWordDetail(tokenNode) {
        if (!tokenNode || !aiAgentGhostEnText || !aiAgentGhostEnDetail) return;
        const key = aiAgentGhostEnWordKey(tokenNode.dataset.wordKey || tokenNode.textContent || "");
        const surface = clean(tokenNode.dataset.word || tokenNode.textContent || key);
        const details = key && Array.isArray(aiAgentGhostEnDetailMap[key]) ? aiAgentGhostEnDetailMap[key] : [];
        aiAgentGhostEnText.querySelectorAll(".ft-ai-ghost-en-token.is-active").forEach((node) => node.classList.remove("is-active"));
        tokenNode.classList.add("is-active");
        aiAgentGhostEnDetail.innerHTML = "";
        const head = document.createElement("div");
        head.className = "ft-ai-ghost-en-detail-head";
        const kicker = document.createElement("span");
        kicker.textContent = "Vietnamese detail";
        const title = document.createElement("strong");
        title.textContent = surface || key || "Word";
        head.append(kicker, title);
        aiAgentGhostEnDetail.appendChild(head);
        if (!details.length) {
          const empty = document.createElement("p");
          empty.className = "ft-ai-ghost-en-detail-empty";
          empty.textContent = "Chua co detail trong tu dien cho tu nay.";
          aiAgentGhostEnDetail.appendChild(empty);
        }
        details.slice(0, 3).forEach((detail) => {
          const row = document.createElement("article");
          row.className = "ft-ai-ghost-en-detail-card";
          const rowTitle = document.createElement("div");
          rowTitle.className = "ft-ai-ghost-en-detail-title";
          const word = document.createElement("b");
          word.textContent = clean(detail.word || surface || key);
          rowTitle.appendChild(word);
          [detail.type, detail.pron || detail.ipa || detail.pron_us || detail.ipa_us].map(clean).filter(Boolean).slice(0, 2).forEach((meta) => {
            const chip = document.createElement("span");
            chip.textContent = meta;
            rowTitle.appendChild(chip);
          });
          row.appendChild(rowTitle);
          const meaning = clean(detail.meaning || detail.usage || detail.note || "");
          if (meaning) {
            const meaningNode = document.createElement("p");
            meaningNode.className = "ft-ai-ghost-en-detail-meaning";
            meaningNode.textContent = meaning;
            row.appendChild(meaningNode);
          }
          const context = clean(detail.context || detail.usage || "");
          if (context && context !== meaning) {
            const contextNode = document.createElement("p");
            contextNode.className = "ft-ai-ghost-en-detail-note";
            contextNode.textContent = context;
            row.appendChild(contextNode);
          }
          const examples = Array.isArray(detail.examples) ? detail.examples : [];
          examples.slice(0, 2).forEach((example) => {
            if (!example) return;
            const ex = document.createElement("p");
            ex.className = "ft-ai-ghost-en-detail-example";
            const en = clean(example.en || example.english || "");
            const vi = clean(example.vi || example.vietnamese || example.translation || "");
            ex.textContent = [en, vi].filter(Boolean).join(" - ");
            if (ex.textContent) row.appendChild(ex);
          });
          const collocations = Array.isArray(detail.collocations) ? detail.collocations.map(clean).filter(Boolean) : [];
          if (collocations.length) {
            const chips = document.createElement("div");
            chips.className = "ft-ai-ghost-en-detail-chips";
            collocations.slice(0, 5).forEach((item) => {
              const chip = document.createElement("span");
              chip.textContent = item;
              chips.appendChild(chip);
            });
            row.appendChild(chips);
          }
          aiAgentGhostEnDetail.appendChild(row);
        });
        aiAgentGhostEnDetail.classList.remove("is-hidden");
        aiAgentGhostEnDetail.setAttribute("aria-hidden", "false");
        positionAiAgentGhostEnDetail();
      }

      // Added 2026-06-30: translates Ghost EN with a dedicated 2-minute request instead of fetchAuthJson.
      function aiAgentTranslateAbortError() {
        const error = new Error("Ghost EN translate canceled.");
        error.name = "AbortError";
        error.isAbortError = true;
        return error;
      }

      function isAiAgentTranslateAbort(error) {
        return Boolean(error && (error.isAbortError || clean(error.name).toLowerCase() === "aborterror"));
      }

      async function fetchAiAgentTranslateToEnglish(payload = {}, options = {}) {
        const errors = [];
        const requestSignal = options && options.signal ? options.signal : null;
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        for (const base of candidates) {
          try {
            if (requestSignal && requestSignal.aborted) {
              throw aiAgentTranslateAbortError();
            }
            const headers = await antiRobotHeaders(base, {
              "Content-Type": "application/json",
            });
            if (!authToken) {
              authToken = getStoredAuthToken();
            }
            if (authToken) {
              headers.Authorization = `Bearer ${authToken}`;
            }
            const response = await fetchWithTimeout(`${base}/ai-agent/translate`, {
              method: "POST",
              headers,
              mode: "cors",
              cache: "no-store",
              ...(requestSignal ? { signal: requestSignal } : {}),
              body: JSON.stringify(payload || {}),
            }, 120000);
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.ok === false) {
              const reason = clean(data.reason || data.code || "").toLowerCase();
              const message = response.status === 401 && authToken && isAuthSessionFailureReason(reason)
                ? invalidateAuthSession(reason)
                : (clean(data.error) || `Translate server error ${response.status}.`);
              const error = new Error(message);
              error.status = response.status;
              error.reason = reason;
              error.fromTranslateServer = true;
              throw error;
            }
            return { base, payload: data };
          } catch (error) {
            if (isAiAgentTranslateAbort(error)) {
              throw error;
            }
            if (error && error.fromTranslateServer && error.status >= 400 && error.status < 500) {
              throw error;
            }
            errors.push(`${base}: ${error && error.message ? error.message : error}`);
          }
        }
        throw new Error(`Khong ket noi duoc Ghost EN translate trong 2 phut. Da thu: ${errors.join(" | ")}`);
      }

      function aiAgentTranslateEnCooldownRemainingMs() {
        const elapsed = Date.now() - Number(aiAgentTranslateEnLastStartedAt || 0);
        return Math.max(0, AI_AGENT_TRANSLATE_EN_COOLDOWN_MS - elapsed);
      }

      function setAiAgentTranslateEnButtonState(state = "idle") {
        if (!aiAgentTranslateEn) return;
        aiAgentTranslateEn.disabled = false;
        if (state === "cancel") {
          aiAgentTranslateEn.textContent = "Cancel";
          aiAgentTranslateEn.title = "Cancel current translate request";
        } else {
          aiAgentTranslateEn.textContent = "Translate to En";
          aiAgentTranslateEn.title = "";
        }
      }

      // Added 2026-06-30: sends Ghost AI input to the server and paints the hoverable English translation.
      async function translateAiAgentInputToEnglish(options = {}) {
        let forceTranslate = Boolean(options && options.force);
        const activeController = aiAgentTranslateEnAbortController;
        if (activeController && !activeController.signal.aborted) {
          try { activeController.abort(); } catch (abortError) {}
          aiAgentTranslateEnAbortController = null;
          setAiAgentTranslateEnButtonState("idle");
          forceTranslate = true;
          setAiAgentGhostEnStatus("Restarting Ghost EN translate...");
          setAiAgentStatus("Restarting Ghost EN translate...");
        }
        const cooldownMs = aiAgentTranslateEnCooldownRemainingMs();
        forceTranslate = Boolean(forceTranslate || cooldownMs > 0);
        if (!authToken) {
          showLoginGate("Hay dang nhap de dung Ghost AI translate.");
          return;
        }
        const message = String((aiAgentInput && aiAgentInput.value) || "").replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
        if (!message) {
          setAiAgentStatus("Type text first, then Translate to En.", true);
          if (aiAgentInput) aiAgentInput.focus({ preventScroll: true });
          return;
        }
        openAiAgentGhostEnPopup();
        if (aiAgentGhostEnPopup) aiAgentGhostEnPopup.classList.add("is-loading");
        if (aiAgentGhostEnText) aiAgentGhostEnText.textContent = "Translating...";
        if (aiAgentGhostEnSource) aiAgentGhostEnSource.textContent = message.length > 220 ? `${message.slice(0, 220)}...` : message;
        setAiAgentGhostEnStatus(forceTranslate ? "Forcing a fresh English translation..." : "Sending to server for English translation...");
        const requestId = aiAgentTranslateEnRequestId + 1;
        aiAgentTranslateEnRequestId = requestId;
        aiAgentTranslateEnLastStartedAt = Date.now();
        const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        aiAgentTranslateEnAbortController = controller;
        setAiAgentTranslateEnButtonState("cancel");
        try {
          const { payload } = await fetchAiAgentTranslateToEnglish({
            text: message,
            target: "en",
            source: "auto",
            force: forceTranslate,
          }, controller ? { signal: controller.signal } : {});
          if (requestId !== aiAgentTranslateEnRequestId) {
            return;
          }
          const translation = String((payload && (payload.translation || payload.translated)) || "").trim();
          if (!translation) {
            throw new Error("Server returned an empty translation.");
          }
          renderAiAgentGhostEnText(translation, payload && payload.vocabulary);
          openAiAgentGhostEnPopup();
          setAiAgentStatus("Translated to English. Hover words in Ghost EN for Vietnamese detail.");
        } catch (error) {
          if (isAiAgentTranslateAbort(error)) {
            if (requestId === aiAgentTranslateEnRequestId) {
              if (aiAgentGhostEnText) aiAgentGhostEnText.textContent = "";
              setAiAgentGhostEnStatus("Ghost EN translate canceled.", true);
              setAiAgentStatus("Ghost EN translate canceled.", true);
            }
            return;
          }
          const rawMessage = clean(error && error.message ? error.message : "");
          const friendlyMessage = ((error && Number(error.status) === 404) || /^not found$/i.test(rawMessage))
            ? "Ghost AI translate route is not active yet. Please restart Server 2 and try again."
            : (rawMessage || "Could not translate through Ghost AI.");
          if (aiAgentGhostEnText) aiAgentGhostEnText.textContent = "";
          setAiAgentGhostEnStatus(friendlyMessage, true);
          setAiAgentStatus(friendlyMessage, true);
        } finally {
          if (requestId === aiAgentTranslateEnRequestId) {
            if (aiAgentGhostEnPopup) aiAgentGhostEnPopup.classList.remove("is-loading");
            if (aiAgentTranslateEnAbortController === controller) {
              aiAgentTranslateEnAbortController = null;
            }
            setAiAgentTranslateEnButtonState("idle");
            positionAiAgentGhostEnPopup();
          }
        }
      }

      function aiAgentCurrentSpaceName() {
        if (document.documentElement.classList.contains("ft-space-pdf-mode")) return pdfState && pdfState.mode === "picture" ? "space_picture" : "space_pdf";
        if (document.documentElement.classList.contains("ft-space-p-mode")) return "space_p";
        if (stageNode && stageNode.classList.contains("is-question-mode")) return "space_q";
        if (stageNode && stageNode.classList.contains("is-vocab-mode")) return "space_v";
        if (stageNode && stageNode.classList.contains("is-lesson-mode")) return "space_w";
        const pathRoute = clean((location.pathname || "").replace(/^\/+/, "").split("/").pop() || "");
        return pathRoute || "future";
      }

      function aiAgentClipText(value = "", limit = 1200) {
        const text = clean(value);
        const max = Math.max(80, Number(limit) || 1200);
        return text.length > max ? `${text.slice(0, max - 3)}...` : text;
      }

      function aiAgentVisibleText(node, limit = 1200) {
        if (!node) {
          return "";
        }
        return aiAgentClipText(node.innerText || node.textContent || "", limit);
      }

      function aiAgentObjectText(source = {}, keys = [], limit = 900) {
        if (!source || typeof source !== "object") {
          return "";
        }
        for (const key of keys) {
          const value = source[key];
          if (typeof value === "string" || typeof value === "number") {
            const text = aiAgentClipText(value, limit);
            if (text) {
              return text;
            }
          }
        }
        return "";
      }

      function aiAgentRuntimeContext(spaceName = "") {
        const context = {
          support_policy: "Do not reveal the exact answer, correct option, hidden target word, or full completed translation. Give hints, explain concepts, and guide the learner step by step.",
        };
        try {
          if (spaceName === "space_pdf" || spaceName === "space_picture") {
            const isPicture = spaceName === "space_picture";
            context.activity = isPicture ? "Space_Picture Ghost Eye image support" : "Space_PDF Ghost Eye reading support";
            context.pdf_title = pdfState && (pdfState.title || pdfState.name) ? aiAgentClipText(pdfState.title || pdfState.name, 240) : "";
            context.pdf_path = pdfState && pdfState.path ? aiAgentClipText(pdfState.path, 420) : "";
            context.pdf_page = pdfState && pdfState.page ? pdfState.page : 1;
            context.pdf_pages = pdfState && pdfState.pages ? pdfState.pages : 0;
            context.selected_ghost_eye_text = pdfState && pdfState.ocrText ? aiAgentClipText(pdfState.ocrText, 2200) : "";
            context.text_to_explore = pdfEls && pdfEls.exploreInput ? aiAgentClipText(pdfEls.exploreInput.value, 2200) : "";
            context.selected_translation_vi = pdfState && pdfState.translation ? aiAgentClipText(pdfState.translation, 1600) : "";
            context.support_policy = isPicture
              ? "Use only the selected Ghost Eye text and current picture context. Explain, translate, summarize, and guide the learner. Do not invent text outside the selected region."
              : "Use the selected Ghost Eye text and current PDF page as reading context. Explain, translate, summarize, and guide the learner. Do not invent text outside the selected region.";
            return context;
          }
          if (spaceName === "space_q") {
            const item = typeof currentQuestionItem === "function" ? currentQuestionItem() : null;
            let highlightCount = 0;
            try {
              if (item && typeof questionRootHighlightRangesForItem === "function") {
                highlightCount = (questionRootHighlightRangesForItem(item) || []).length;
              }
            } catch (error) {
              highlightCount = 0;
            }
            context.activity = "Space_Q question practice";
            context.root_text_visible = aiAgentVisibleText(qRootText, 1800);
            context.current_question = aiAgentVisibleText(qQuestionText, 1000) || aiAgentObjectText(item, ["question", "prompt", "title", "text", "q"], 1000);
            context.question_type = aiAgentObjectText(item, ["type", "kind", "mode", "question_type", "questionType"], 80);
            context.question_counter = aiAgentVisibleText(qQuestionCount, 80);
            context.node_index = Math.max(0, Math.floor(Number(currentNodeIndex || 0) || 0)) + 1;
            context.node_count = Array.isArray(questionNodes) ? questionNodes.length : 0;
            context.question_index = Math.max(0, Math.floor(Number(questionQuestionIndex || 0) || 0)) + 1;
            context.question_count = Array.isArray(questionCurrentQuestions) ? questionCurrentQuestions.length : 0;
            context.highlight_regions_visible = highlightCount;
            context.visible_feedback = aiAgentVisibleText(qRootChoiceSignalState, 120) || aiAgentVisibleText(qRootChoiceSignalText, 320);
            context.support_policy = "In Space_Q, root text and current question are context for understanding only. Do not give the full sentence as a hint, do not list all tokens/phrases the learner must choose, and do not reveal hidden or locked words. Give small conceptual hints, grammar-role hints, or one-step reasoning only.";
            context.hidden_fields_omitted = "answers, correct choices, and solution keys are intentionally omitted";
            return context;
          }
          if (spaceName === "space_p") {
            const node = typeof currentParagraphNode === "function" ? currentParagraphNode() : null;
            const child = typeof currentParagraphChild === "function" ? currentParagraphChild() : null;
            const paragraphRoot = paragraphEls && paragraphEls.root ? paragraphEls.root : document;
            const revealedNodes = Array.from(paragraphRoot.querySelectorAll(".ft-paragraph-token.is-active-segment.is-revealed"));
            const revealedText = Array.from(paragraphRoot.querySelectorAll(".ft-paragraph-token.is-active-segment.is-revealed, .ft-paragraph-punct.is-active-segment.is-revealed"))
              .map((item) => clean(item.innerText || item.textContent || ""))
              .filter(Boolean)
              .join(" ");
            const revealedWords = revealedNodes
              .map((item) => clean(item.innerText || item.textContent || ""))
              .filter(Boolean)
              .slice(-32);
            const expectedWords = typeof currentParagraphWords === "function" ? currentParagraphWords() : [];
            const revealedCount = Math.max(0, Number(paragraphRevealed && paragraphRevealed[paragraphChildIndex] || 0) || 0);
            const nextWordLength = expectedWords[revealedCount] ? Array.from(expectedWords[revealedCount]).length : 0;
            const nodeChildren = node && Array.isArray(node.children) ? node.children : [];
            const nodeFullText = nodeChildren
              .map((entry) => preserveQuestionText(entry && entry.text ? entry.text : ""))
              .filter(Boolean)
              .join(" ");
            context.activity = "Space_P paragraph rewrite";
            context.node_title = aiAgentObjectText(node, ["title", "name", "id"], 180) || aiAgentVisibleText(paragraphEls && paragraphEls.title, 180);
            context.vietnamese_prompt = aiAgentVisibleText(paragraphEls && paragraphEls.meaning, 1000) || aiAgentObjectText(child, ["meaning", "vi", "vietnamese", "translation"], 1000);
            context.current_segment_full_internal = aiAgentClipText(child && child.text ? child.text : "", 1200);
            context.node_full_text_internal = aiAgentClipText(nodeFullText, 2200);
            context.typed_input = aiAgentVisibleText(paragraphEls && paragraphEls.input, 600) || (paragraphEls && paragraphEls.input ? aiAgentClipText(paragraphEls.input.value, 600) : "");
            context.revealed_text_only = aiAgentClipText(revealedText, 900);
            context.revealed_words = revealedWords;
            context.revealed_word_count = revealedCount;
            context.segment_word_count = expectedWords.length;
            context.next_hidden_word = nextWordLength ? `${nextWordLength} letters` : "";
            context.word_type_hint = aiAgentVisibleText(paragraphEls && paragraphEls.posLabel, 160);
            context.word_meaning_hint_visible = aiAgentVisibleText(paragraphEls && paragraphEls.posMeaning, 260);
            context.status = aiAgentVisibleText(paragraphEls && paragraphEls.status, 260);
            context.node_index = Math.max(0, Math.floor(Number(paragraphNodeIndex || 0) || 0)) + 1;
            context.node_count = Array.isArray(paragraphNodes) ? paragraphNodes.length : 0;
            context.segment_index = Math.max(0, Math.floor(Number(paragraphChildIndex || 0) || 0)) + 1;
            context.segment_count = node && Array.isArray(node.children) ? node.children.length : 0;
            context.support_policy = "In Space_P, full node and current segment text are provided only so Ghost AI understands context. Revealed English words are unlocked and may be used directly. Unrevealed English tokens may be read internally but must not be quoted, completed, listed, or exposed; give only part-of-speech, meaning, spelling-shape, grammar, word-order, or translation-strategy hints for unopened words.";
            context.hidden_fields_omitted = "full Space_P text is internal context; unrevealed tokens must not be surfaced in the answer";
            return context;
          }
          if (spaceName === "space_v") {
            const item = typeof currentVocabItem === "function" ? currentVocabItem() : null;
            const phase = clean(vocabPhase || "probe");
            const canExplainCurrentWord = phase === "drill" || phase === "shuffle";
            context.activity = "Space_V vocabulary practice";
            context.phase = phase;
            context.meaning_prompt = aiAgentObjectText(item, ["meaning", "vi", "vietnamese", "translation", "definition"], 900);
            context.part_of_speech = aiAgentObjectText(item, ["pos", "type", "part_of_speech", "partOfSpeech"], 160);
            if (canExplainCurrentWord) {
              context.current_vocabulary_word = aiAgentObjectText(item, ["word", "en", "english", "text", "term"], 180);
              context.allow_current_vocabulary_word = true;
              context.support_policy = "This is Space_V 10-repetition or 5-shuffle vocabulary training. The current vocabulary word is allowed, so Ghost AI may say it directly and use it in explanations, examples, spelling support, and pronunciation guidance.";
            }
            context.typed_input = vocabAnswer ? aiAgentClipText(vocabAnswer.value, 240) : "";
            context.feedback = aiAgentVisibleText(vocabFeedback, 320);
            context.meta_visible = aiAgentVisibleText(vocabMeta, 260);
            context.word_index = Math.max(0, Math.floor(Number(vocabCurrentIndex || 0) || 0)) + 1;
            context.word_count = Array.isArray(vocabItems) ? vocabItems.length : 0;
            context.hidden_fields_omitted = canExplainCurrentWord
              ? "unrelated hidden answers are omitted; the current Space_V vocabulary word is intentionally available in this training phase"
              : "the target word is intentionally omitted";
            return context;
          }
          if (spaceName === "space_w") {
            const vietnamesePrompt = aiAgentVisibleText(document.getElementById("ft-question-title"), 900)
              || aiAgentObjectText(currentNode, ["vi", "vietnamese", "prompt"], 900);
            context.activity = "Space_W translation and speaking practice";
            context.vietnamese_prompt = vietnamesePrompt;
            context.typed_input = answerInput ? aiAgentClipText(answerInput.value, 700) : "";
            context.progress = aiAgentVisibleText(document.getElementById("ft-progress"), 160);
            context.feedback = aiAgentVisibleText(document.getElementById("ft-feedback"), 320);
            context.score_feedback = aiAgentVisibleText(scoreMessage, 360);
            context.hint_visible = hintPanel && hintPanel.classList.contains("is-live") ? aiAgentVisibleText(hintText, 400) : "";
            context.ipa_visible = ipaPanel && ipaPanel.classList.contains("is-live") ? aiAgentVisibleText(ipaNode, 220) : "";
            context.node_index = Math.max(0, Math.floor(Number(currentNodeIndex || 0) || 0)) + 1;
            context.node_count = Array.isArray(lessonNodes) ? lessonNodes.length : 0;
            context.hidden_fields_omitted = "the exact English answer is intentionally omitted";
            return context;
          }
        } catch (error) {
          context.context_error = "Context capture failed safely without answer fields.";
        }
        context.activity = spaceName || "Future learning app";
        return context;
      }

      function aiAgentContextPayload() {
        const source = typeof currentLessonSource === "object" && currentLessonSource ? currentLessonSource : {};
        const title = clean(source.title || source.name || "");
        const path = clean(source.path || "").replace(/\\/g, "/");
        const spaceName = aiAgentCurrentSpaceName();
        const runtime = aiAgentRuntimeContext(spaceName);
        const answerPolicy = runtime && runtime.allow_current_vocabulary_word
          ? "For Space_V drill or shuffle training, the current vocabulary word is allowed. Use it directly to explain meaning, spelling, pronunciation, and usage. Do not expose unrelated hidden answers from other exercises."
          : (spaceName === "space_pdf" || spaceName === "space_picture"
            ? "For Space_PDF or Space_Picture, use only the selected Ghost Eye text and current document/image context. Explain, translate, summarize, or answer questions about that selected text without inventing unavailable content."
            : (spaceName === "space_p"
              ? "For Space_P paragraph rewrite, full sentence and node text are internal context only. Use them to understand the learner's question, but only revealed English words may be quoted. Never reveal unrevealed hidden English tokens or finish the remaining translation; give hints only for unopened words."
              : (spaceName === "space_q"
              ? "For Space_Q, root text and current question are internal context only. Never give the full sentence, never list all words or phrases to select, and never reveal hidden or locked words. Give compact hints only."
              : "Use the runtime context only for support. Do not expose hidden answers, correct options, target vocabulary words, or completed translations.")));
        return {
          space: spaceName,
          lesson: title || path,
          file: path || title,
          route: clean((location.pathname || "").replace(/^\/+/, "")),
          runtime,
          answer_policy: answerPolicy,
        };
      }

      function aiAgentAutoSaveTitle(context = {}, message = "", explicitTitle = "") {
        const explicit = preserveQuestionText(explicitTitle);
        if (explicit) {
          return explicit.slice(0, 120);
        }
        const quick = context && typeof context.quick_ask === "object" ? context.quick_ask : {};
        const runtime = context && typeof context.runtime === "object" ? context.runtime : {};
        const tokenTitle = preserveQuestionText(
          quick.hinted_word
          || quick.current_vocabulary_word
          || runtime.current_vocabulary_word
          || ""
        );
        if (tokenTitle) {
          return tokenTitle.slice(0, 120);
        }
        const activity = preserveQuestionText(runtime.activity || context.space || "Ghost AI");
        const compactMessage = preserveQuestionText(message).replace(/\s+/g, " ");
        if (compactMessage) {
          return `${activity}: ${compactMessage.slice(0, 72)}`.slice(0, 120);
        }
        return `${activity}: AI answer`.slice(0, 120);
      }

      async function autoSaveAiAgentNotice(notice = {}, context = {}, message = "", explicitTitle = "") {
        if (!authToken || !notice || !notice._ai_agent) {
          return false;
        }
        const title = aiAgentAutoSaveTitle(context, message, explicitTitle);
        const english = preserveQuestionText(notice.translation_en || notice.english || notice.en || notice.text || "");
        const vietnamese = preserveQuestionText(notice.translation_vi || notice.vietnamese || notice.vi || "");
        if (!title || (!english && !vietnamese)) {
          return false;
        }
        try {
          const runtime = context && typeof context.runtime === "object" ? context.runtime : {};
          const quick = context && typeof context.quick_ask === "object" ? context.quick_ask : {};
          const { payload } = await fetchAuthJson("/ai-agent/history", {
            method: "POST",
            body: JSON.stringify({
              action: "save",
              title,
              english,
              vietnamese,
              user_prompt: preserveQuestionText(message),
              space: context.space || "",
              file: context.file || context.lesson || "",
              word: preserveQuestionText(quick.hinted_word || quick.current_vocabulary_word || runtime.current_vocabulary_word || ""),
              context,
            }),
          });
          const entry = payload && payload.entry && typeof payload.entry === "object" ? payload.entry : null;
          if (entry) {
            aiAgentHistoryCache = [entry, ...aiAgentHistoryCache.filter((item) => clean(item.id || "") !== clean(entry.id || ""))].filter((item) => item && clean(item.title || ""));
          }
          if (aiNoticeSaveStatus && aiAgentActiveNotice && clean(aiAgentActiveNotice.id || "") === clean(notice.id || "")) {
            setAiNoticeSaveStatus(`Auto-saved as "${title}".`);
          }
          return true;
        } catch (error) {
          if (aiNoticeSaveStatus && aiAgentActiveNotice && clean(aiAgentActiveNotice.id || "") === clean(notice.id || "")) {
            setAiNoticeSaveStatus(error && error.message ? error.message : "Auto-save failed.", true);
          }
          return false;
        }
      }

      async function submitAiAgentQuestion(options = {}) {
        if (!authToken) {
          showLoginGate("Hay dang nhap de dung AI agent.");
          return;
        }
        const hasHiddenMessage = Object.prototype.hasOwnProperty.call(options || {}, "message");
        const message = clean(hasHiddenMessage ? options.message : (aiAgentInput && aiAgentInput.value || ""));
        if (!message) {
          setAiAgentStatus("Type a question first.", true);
          if (aiAgentInput) aiAgentInput.focus({ preventScroll: true });
          return;
        }
        if (aiAgentSubmit) {
          aiAgentSubmit.disabled = true;
          aiAgentSubmit.textContent = "Thinking";
        }
        setAiAgentThinking(true);
        const answerMode = getAiAgentMode();
        const suggestionForRequest = !options.skipSuggestion && aiAgentPendingSuggestion && typeof aiAgentPendingSuggestion === "object"
          ? aiAgentPendingSuggestion
          : null;
        const suggestionQuestion = preserveQuestionText(suggestionForRequest && (
          suggestionForRequest.question_vi
          || suggestionForRequest.question
          || suggestionForRequest.text
        ) || "");
        const outgoingMessage = suggestionQuestion
          ? `Space_P tutor follow-up question:\n${suggestionQuestion}\n\nLearner response or request:\n${message}`
          : message;
        const outgoingContext = aiAgentContextPayload();
        if (suggestionForRequest) {
          outgoingContext.followup = {
            kind: "space_p_auto_hint_followup",
            question_vi: suggestionQuestion,
            source: suggestionForRequest.context || {},
          };
          outgoingContext.answer_policy = `${outgoingContext.answer_policy || ""} The learner is responding to a Space_P tutor follow-up. Explain the completed sentence in detail, but do not expose future locked content.`;
        }
        const oneShotPatch = options.contextPatch && typeof options.contextPatch === "object"
          ? options.contextPatch
          : (aiAgentOneShotContextPatch && typeof aiAgentOneShotContextPatch === "object" ? aiAgentOneShotContextPatch : null);
        if (oneShotPatch) {
          outgoingContext.quick_ask = oneShotPatch;
          if (clean(oneShotPatch.kind) === "space_p_hinted_word_quick_ask") {
            outgoingContext.answer_policy = `${outgoingContext.answer_policy || ""} The learner tapped a Space_P hinted-word quick ask. The hinted word may be discussed directly, but unrevealed Space_P words must stay hidden.`;
          }
          if (clean(oneShotPatch.kind) === "space_v_quick_ask") {
            outgoingContext.answer_policy = `${outgoingContext.answer_policy || ""} The learner tapped a Space_V quick ask. Use the current vocabulary word directly when it is available in context.`;
          }
          aiAgentOneShotContextPatch = null;
        }
        setAiAgentStatus(answerMode === "detailed"
          ? "Ghost AI is preparing detailed text panels..."
          : "Ghost AI is preparing an English answer...");
        try {
          const { payload } = await fetchAuthJson("/ai-agent/ask", {
            method: "POST",
            body: JSON.stringify({
              message: outgoingMessage,
              mode: answerMode,
              context: outgoingContext,
            }),
          });
          const notice = payload && payload.notice && typeof payload.notice === "object" ? payload.notice : null;
          if (!notice) {
            throw new Error("AI agent returned no notice payload.");
          }
          notice._immediate = true;
          notice._ai_agent = true;
          notice.notice_style = notice.notice_style || notice.noticeStyle || "face1";
          notice.require_ack = true;
          if (!notice.translation_vi && payload.answer_vi) {
            notice.translation_vi = payload.answer_vi;
          }
          if (!notice.translation_en && payload.answer_en) {
            notice.translation_en = payload.answer_en;
          }
          notice._resume_ai_popup = isAiAgentPopupOpen();
          if (notice._resume_ai_popup) {
            aiAgentPopupResumeAfterNotice = true;
            closeAiAgentPopup();
          }
          taskUserNoticeQueue = taskUserNoticeQueue.filter((item) => !item || !item._ai_agent);
          taskUserNoticeQueue.push(notice);
          void pumpTaskUserNoticeQueue();
          void autoSaveAiAgentNotice(notice, outgoingContext, outgoingMessage, options.autoSaveTitle || "");
          setAiAgentStatus("Answer received. Opening AI face notice.");
          if (aiAgentInput && options.clearInput !== false) {
            aiAgentInput.value = "";
          }
          if (suggestionForRequest) {
            clearAiAgentSuggestion();
          }
        } catch (error) {
          const rawMessage = clean(error && error.message ? error.message : "");
          let friendlyMessage = rawMessage || "Could not reach AI agent.";
          if ((error && Number(error.status) === 404) || /^not found$/i.test(rawMessage)) {
            friendlyMessage = "Ghost AI route is not active yet. Please restart future_whisper_server and try again.";
          } else if (/quota|rate limit|resource exhausted|retry/i.test(rawMessage)) {
            friendlyMessage = "Ghost AI is busy on the free channel. Please wait a moment and try again.";
          } else if (/gemini/i.test(rawMessage) && /not found|unsupported|generatecontent/i.test(rawMessage)) {
            friendlyMessage = "The AI model was not accepted by this key. The server will try available free fallback models after restart.";
          } else if (/gemini/i.test(rawMessage)) {
            friendlyMessage = "Ghost AI could not answer through the current AI channel. Please try again shortly.";
          }
          setAiAgentStatus(friendlyMessage, true);
        } finally {
          setAiAgentThinking(false);
          if (aiAgentSubmit) {
            aiAgentSubmit.disabled = false;
            aiAgentSubmit.textContent = "Send";
          }
        }
      }

      const setLearnerChatVisible = (visible) => {
        const shouldShow = Boolean(visible && (authToken || currentAuthUsername));
        const pdfToolsSurface = Boolean(typeof pdfModeActive !== "undefined" && pdfModeActive && document.documentElement.classList.contains("ft-space-pdf-mode"));
        if (aiAgentButton) {
          aiAgentButton.classList.toggle("is-visible", shouldShow);
        }
        if (chatButton) {
          chatButton.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        if (streamButton) {
          streamButton.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        if (screenButton) {
          screenButton.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        if (webRecordButton) {
          webRecordButton.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        if (paintButton) {
          paintButton.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        if (mobileAnimationButton) {
          mobileAnimationButton.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        if (clearAudioCacheButton) {
          clearAudioCacheButton.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        if (mobileToolsToggle) {
          mobileToolsToggle.classList.toggle("is-visible", shouldShow || pdfToolsSurface);
        }
        const adminToolsVisible = Boolean(shouldShow && currentAuthIsAdmin);
        document.documentElement.classList.toggle("ft-admin-tools-visible", adminToolsVisible);
        if (adminScreenButton) {
          adminScreenButton.classList.toggle("is-visible", adminToolsVisible);
        }
        if (speakSkipAdminButton) {
          speakSkipAdminButton.classList.toggle("is-visible", adminToolsVisible);
        }
        if (gameButton) {
          gameButton.classList.toggle("is-visible", shouldShow);
        }
        if (portalButton) {
          portalButton.classList.toggle("is-visible", shouldShow);
        }
        if (vaultButton) {
          vaultButton.classList.toggle("is-visible", shouldShow);
        }
        if (cupButton) {
          cupButton.classList.toggle("is-visible", shouldShow);
        }
        if (workerToolbarButton) {
          workerToolbarButton.classList.toggle("is-visible", false);
        }
        if (npcSwitchButton) {
          npcSwitchButton.classList.toggle("is-visible", adminToolsVisible);
        }
        if (!shouldShow) {
          document.documentElement.classList.remove("ft-mobile-tools-open");
          if (mobileToolsToggle) {
            mobileToolsToggle.classList.remove("is-active");
            mobileToolsToggle.setAttribute("aria-expanded", "false");
          }
          learnerChatOpen = false;
          stopLearnerChatPolling();
          learnerPaintOpen = false;
          learnerChatUnread = 0;
          updateLearnerChatBadge();
          document.documentElement.classList.remove("ft-paint-performance-mode");
          stopLearnerStreamPolling();
          stopLearnerScreenPolling();
          stopLearnerPaintPolling();
          stopGamePolling();
          stopGameBattleLoop();
          closeSharedWorld();
          closeSpeakSkipAdminModal();
          if (chatModal) {
            chatModal.classList.remove("is-open");
            chatModal.setAttribute("aria-hidden", "true");
          }
          if (cupModal) {
            cupModal.classList.remove("is-open");
            cupModal.setAttribute("aria-hidden", "true");
          }
          if (paintModal) {
            paintModal.classList.remove("is-open");
            paintModal.setAttribute("aria-hidden", "true");
          }
          if (gameModal) {
            gameModal.classList.remove("is-open");
            gameModal.setAttribute("aria-hidden", "true");
          }
          closeAiAgentPopup();
        } else if (learnerPaintAutoOpen && !learnerPaintAutoOpenDone) {
          learnerPaintAutoOpenDone = true;
          window.setTimeout(() => {
            openLearnerPaint();
          }, 120);
        }
      };

      const openLearnerChat = () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de gui tin nhan.");
          return;
        }
        learnerChatOpen = true;
        learnerChatUnread = 0;
        updateLearnerChatBadge();
        renderLearnerChatMessages();
        window.setTimeout(playLatestLearnerChatAudio, 140);
        if (chatModal) {
          chatModal.classList.add("is-open");
          chatModal.setAttribute("aria-hidden", "false");
        }
        setLearnerChatStatus("");
        startLearnerChatPolling();
        window.setTimeout(() => {
          if (chatInput) {
            chatInput.focus({ preventScroll: true });
          }
        }, 80);
      };

      const closeLearnerChat = () => {
        learnerChatOpen = false;
        stopLearnerChatPolling();
        cancelLearnerChatVoice();
        if (chatModal) {
          chatModal.classList.remove("is-open");
          chatModal.setAttribute("aria-hidden", "true");
        }
      };

      const learnerPaintClamp = (value, min, max) => Math.max(min, Math.min(max, value));

      const learnerPaintCtx = () => paintCanvas ? paintCanvas.getContext("2d") : null;

      const learnerPaintObjectById = (id) => learnerPaintObjects.find((item) => item && item.id === id) || null;

      const learnerPaintTextLines = (text) => {
        const raw = String(text == null ? "" : text).replace(/\r/g, "");
        const lines = raw.split("\n").slice(0, 8);
        return lines.length ? lines : ["Text"];
      };

      const learnerPaintTextBounds = (object) => {
        const ctx = learnerPaintCtx();
        const size = Math.max(10, Number(object.size || 28));
        const lines = learnerPaintTextLines(object.text || "Text");
        let width = 24;
        if (ctx) {
          ctx.save();
          ctx.font = `900 ${size}px Inter, Segoe UI, system-ui, sans-serif`;
          lines.forEach((line) => {
            width = Math.max(width, ctx.measureText(line || " ").width);
          });
          ctx.restore();
        } else {
          lines.forEach((line) => {
            width = Math.max(width, String(line || " ").length * size * 0.62);
          });
        }
        const lineHeight = size * 1.24;
        return {
          x: Number(object.x || 0) - 7,
          y: Number(object.y || 0) - size - 8,
          w: width + 14,
          h: lineHeight * lines.length + 14,
        };
      };

      const learnerPaintObjectBounds = (object) => {
        if (!object) {
          return { x: 0, y: 0, w: 0, h: 0 };
        }
        if (object.type === "text") {
          return learnerPaintTextBounds(object);
        }
        const points = Array.isArray(object.points) ? object.points : [];
        if (!points.length) {
          return { x: 0, y: 0, w: 0, h: 0 };
        }
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;
        points.forEach((point) => {
          const x = Number(point.x || 0);
          const y = Number(point.y || 0);
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
        });
        const pad = Math.max(10, Number(object.width || 6) * 0.65 + 6);
        return {
          x: minX - pad,
          y: minY - pad,
          w: Math.max(18, maxX - minX + pad * 2),
          h: Math.max(18, maxY - minY + pad * 2),
        };
      };

      const learnerPaintPointInBounds = (point, bounds, pad = 0) => (
        point.x >= bounds.x - pad &&
        point.y >= bounds.y - pad &&
        point.x <= bounds.x + bounds.w + pad &&
        point.y <= bounds.y + bounds.h + pad
      );

      const learnerPaintHandleBounds = (bounds) => ({
        x: bounds.x + bounds.w - 12,
        y: bounds.y + bounds.h - 12,
        w: 24,
        h: 24,
      });

      const learnerPaintPointDistanceToSegment = (point, a, b) => {
        const ax = Number(a.x || 0);
        const ay = Number(a.y || 0);
        const bx = Number(b.x || 0);
        const by = Number(b.y || 0);
        const dx = bx - ax;
        const dy = by - ay;
        const lengthSq = dx * dx + dy * dy;
        if (!lengthSq) {
          return Math.hypot(point.x - ax, point.y - ay);
        }
        const t = learnerPaintClamp(((point.x - ax) * dx + (point.y - ay) * dy) / lengthSq, 0, 1);
        return Math.hypot(point.x - (ax + t * dx), point.y - (ay + t * dy));
      };

      const learnerPaintHitObject = (point) => {
        for (let index = learnerPaintObjects.length - 1; index >= 0; index -= 1) {
          const object = learnerPaintObjects[index];
          const bounds = learnerPaintObjectBounds(object);
          if (object.type === "text") {
            if (learnerPaintPointInBounds(point, bounds, 2)) {
              return object;
            }
            continue;
          }
          const points = Array.isArray(object.points) ? object.points : [];
          const hitPad = Math.max(10, Number(object.width || 6) * 0.6 + 7);
          if (points.length < 2) {
            if (points[0] && Math.hypot(point.x - points[0].x, point.y - points[0].y) <= hitPad) {
              return object;
            }
            continue;
          }
          for (let pointIndex = 1; pointIndex < points.length; pointIndex += 1) {
            if (learnerPaintPointDistanceToSegment(point, points[pointIndex - 1], points[pointIndex]) <= hitPad) {
              return object;
            }
          }
          if (learnerPaintPointInBounds(point, bounds, 0) && Math.min(bounds.w, bounds.h) <= 36) {
            return object;
          }
        }
        return null;
      };

      const learnerPaintCanvasPoint = (event) => {
        learnerPaintEnsureBuffer();
        const rect = paintCanvas.getBoundingClientRect();
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        return {
          x: learnerPaintClamp((event.clientX - rect.left) * boardWidth / Math.max(1, rect.width), 0, boardWidth),
          y: learnerPaintClamp((event.clientY - rect.top) * boardHeight / Math.max(1, rect.height), 0, boardHeight),
        };
      };

      const ensureLearnerPaintRemoteCursorNode = () => {
        if (learnerPaintRemoteCursorNode && learnerPaintRemoteCursorNode.isConnected) {
          return learnerPaintRemoteCursorNode;
        }
        const stage = paintCanvas && paintCanvas.parentElement;
        if (!stage) {
          return null;
        }
        const node = document.createElement("div");
        node.className = "ft-paint-remote-cursor";
        node.setAttribute("aria-hidden", "true");
        const label = document.createElement("span");
        label.className = "ft-paint-remote-label";
        label.textContent = "Admin";
        node.appendChild(label);
        stage.appendChild(node);
        learnerPaintRemoteCursorNode = node;
        return node;
      };

      const hideLearnerPaintRemoteCursor = () => {
        if (learnerPaintRemoteCursorNode) {
          learnerPaintRemoteCursorNode.classList.remove("is-visible");
        }
      };

      const positionLearnerPaintRemoteCursor = () => {
        const cursor = learnerPaintRemoteCursor;
        const node = ensureLearnerPaintRemoteCursorNode();
        if (!node || !paintCanvas || !cursor || !cursor.visible) {
          hideLearnerPaintRemoteCursor();
          return;
        }
        const canvasRect = paintCanvas.getBoundingClientRect();
        if (canvasRect.width < 2 || canvasRect.height < 2) {
          hideLearnerPaintRemoteCursor();
          return;
        }
        const boardWidth = Number(cursor.width || 0) || (learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH);
        const boardHeight = Number(cursor.height || 0) || (learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT);
        const x = learnerPaintClamp(Number(cursor.x || 0), 0, boardWidth) * canvasRect.width / Math.max(1, boardWidth);
        const y = learnerPaintClamp(Number(cursor.y || 0), 0, boardHeight) * canvasRect.height / Math.max(1, boardHeight);
        const left = paintCanvas.offsetLeft + x;
        const top = paintCanvas.offsetTop + y;
        const label = node.querySelector(".ft-paint-remote-label");
        if (label) {
          const mode = clean(cursor.mode || "");
          label.textContent = `${clean(cursor.label || "Admin") || "Admin"}${mode ? " | " + mode : ""}`;
        }
        node.style.transform = `translate3d(${left.toFixed(1)}px, ${top.toFixed(1)}px, 0)`;
        node.classList.add("is-visible");
      };

      const renderLearnerPaintRemoteCursor = (cursor = null) => {
        learnerPaintRemoteCursor = cursor && cursor.visible ? cursor : null;
        positionLearnerPaintRemoteCursor();
      };

      const learnerPaintCursorPayload = (point, visible = true) => {
        learnerPaintEnsureBuffer();
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        return {
          x: learnerPaintClamp(Number(point && point.x || 0), 0, boardWidth),
          y: learnerPaintClamp(Number(point && point.y || 0), 0, boardHeight),
          width: boardWidth,
          height: boardHeight,
          visible: Boolean(visible),
          mode: learnerPaintMode || "paint",
          label: currentAuthUsername || "User",
        };
      };

      const sendLearnerPaintCursor = async () => {
        const isHidingCursor = learnerPaintLocalCursor && learnerPaintLocalCursor.visible === false;
        if (!authToken || (!learnerPaintOpen && !isHidingCursor) || !learnerPaintServerConnected || !learnerPaintLocalCursor || learnerPaintCursorSending) {
          return;
        }
        learnerPaintCursorSending = true;
        learnerPaintLastCursorSentAt = Date.now();
        try {
          await fetchAuthJson("/paint/cursor", {
            method: "POST",
            body: JSON.stringify({ cursor: learnerPaintLocalCursor }),
          });
        } catch (error) {
        } finally {
          learnerPaintCursorSending = false;
        }
      };

      const scheduleLearnerPaintCursorSync = (delay = 20) => {
        const isHidingCursor = learnerPaintLocalCursor && learnerPaintLocalCursor.visible === false;
        if (!authToken || (!learnerPaintOpen && !isHidingCursor) || !learnerPaintServerConnected || !learnerPaintLocalCursor) {
          return;
        }
        const elapsed = Date.now() - learnerPaintLastCursorSentAt;
        const wait = Math.max(delay, LEARNER_PAINT_CURSOR_SYNC_INTERVAL_MS - elapsed, 0);
        window.clearTimeout(learnerPaintCursorTimer);
        learnerPaintCursorTimer = window.setTimeout(() => {
          void sendLearnerPaintCursor();
        }, wait);
      };

      const updateLearnerPaintLocalCursor = (event, visible = true) => {
        if (!paintCanvas || !authToken) {
          return;
        }
        const point = visible ? learnerPaintCanvasPoint(event) : (learnerPaintLocalCursor || { x: 0, y: 0 });
        learnerPaintLocalCursor = learnerPaintCursorPayload(point, visible);
        scheduleLearnerPaintCursorSync(visible ? 16 : 0);
      };

      const hideLearnerPaintToolCursor = () => {
        if (paintToolCursor) {
          paintToolCursor.classList.remove("is-visible");
          paintToolCursor.classList.remove("is-erasing");
          paintToolCursor.style.transform = "translate3d(-9999px, -9999px, 0)";
        }
        document.documentElement.classList.remove("ft-paint-tool-cursor-active");
      };

      const setLearnerPaintEraserCursorActive = (active = false) => {
        if (!paintToolCursor) {
          return;
        }
        paintToolCursor.classList.toggle("is-erasing", Boolean(active) && learnerPaintMode === "eraser");
      };

      const updateLearnerPaintToolCursor = (event, visible = true) => {
        if (!paintCanvas || !paintToolCursor || !visible || !learnerPaintOpen) {
          hideLearnerPaintToolCursor();
          return;
        }
        if (event && event.pointerType && event.pointerType !== "mouse" && event.pointerType !== "pen") {
          hideLearnerPaintToolCursor();
          return;
        }
        const stage = paintCanvas.parentElement;
        if (!stage) {
          hideLearnerPaintToolCursor();
          return;
        }
        const rect = paintCanvas.getBoundingClientRect();
        if (rect.width < 2 || rect.height < 2) {
          hideLearnerPaintToolCursor();
          return;
        }
        const x = paintCanvas.offsetLeft + learnerPaintClamp(Number(event.clientX || 0) - rect.left, 0, rect.width);
        const y = paintCanvas.offsetTop + learnerPaintClamp(Number(event.clientY || 0) - rect.top, 0, rect.height);
        const mode = ["select", "pen", "eraser", "text"].includes(learnerPaintMode) ? learnerPaintMode : "pen";
        paintToolCursor.dataset.mode = mode;
        if (mode === "eraser") {
          const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
          const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
          const scale = Math.min(rect.width / Math.max(1, boardWidth), rect.height / Math.max(1, boardHeight));
          const diameter = Math.max(14, learnerPaintStrokeSize(true) * scale);
          paintToolCursor.style.setProperty("--paint-eraser-diameter", `${diameter.toFixed(1)}px`);
        } else {
          setLearnerPaintEraserCursorActive(false);
        }
        paintToolCursor.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
        paintToolCursor.classList.add("is-visible");
        document.documentElement.classList.add("ft-paint-tool-cursor-active");
      };

      const learnerPaintDisplayPoint = (point) => {
        if (!paintCanvas || !point) {
          return null;
        }
        learnerPaintEnsureBuffer();
        const canvasRect = paintCanvas.getBoundingClientRect();
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        return {
          x: paintCanvas.offsetLeft + learnerPaintClamp(Number(point.x || 0), 0, boardWidth) * canvasRect.width / Math.max(1, boardWidth),
          y: paintCanvas.offsetTop + learnerPaintClamp(Number(point.y || 0), 0, boardHeight) * canvasRect.height / Math.max(1, boardHeight),
        };
      };

      const learnerPaintDisplayRect = (rect) => {
        if (!paintCanvas || !rect) {
          return null;
        }
        learnerPaintEnsureBuffer();
        const canvasRect = paintCanvas.getBoundingClientRect();
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        const x = paintCanvas.offsetLeft + learnerPaintClamp(Number(rect.x || 0), 0, boardWidth) * canvasRect.width / Math.max(1, boardWidth);
        const y = paintCanvas.offsetTop + learnerPaintClamp(Number(rect.y || 0), 0, boardHeight) * canvasRect.height / Math.max(1, boardHeight);
        const w = learnerPaintClamp(Number(rect.w || 0), 0, boardWidth) * canvasRect.width / Math.max(1, boardWidth);
        const h = learnerPaintClamp(Number(rect.h || 0), 0, boardHeight) * canvasRect.height / Math.max(1, boardHeight);
        return { x, y, w, h };
      };

      const clearLearnerPaintSelectAnchor = () => {
        learnerPaintSelectFirstPoint = null;
        if (learnerPaintSelectMarkerNode) {
          learnerPaintSelectMarkerNode.remove();
          learnerPaintSelectMarkerNode = null;
        }
      };

      const spawnLearnerPaintSelectPoint = (point, index = 1, keep = false) => {
        const stage = paintCanvas && paintCanvas.parentElement;
        const displayPoint = learnerPaintDisplayPoint(point);
        if (!stage || !displayPoint) {
          return null;
        }
        const node = document.createElement("div");
        node.className = `ft-paint-select-point${keep ? " is-anchor" : ""}`;
        node.dataset.point = String(index);
        node.setAttribute("aria-hidden", "true");
        node.style.transform = `translate3d(${displayPoint.x.toFixed(1)}px, ${displayPoint.y.toFixed(1)}px, 0)`;
        node.appendChild(document.createElement("span"));
        stage.appendChild(node);
        if (!keep) {
          window.setTimeout(() => node.remove(), 760);
        }
        return node;
      };

      const spawnLearnerPaintSelectFrameCast = (rect) => {
        const stage = paintCanvas && paintCanvas.parentElement;
        const displayRect = learnerPaintDisplayRect(rect);
        if (!stage || !displayRect || displayRect.w < 2 || displayRect.h < 2) {
          return null;
        }
        const node = document.createElement("div");
        node.className = "ft-paint-select-frame-cast";
        node.setAttribute("aria-hidden", "true");
        node.style.setProperty("--frame-x", `${displayRect.x.toFixed(1)}px`);
        node.style.setProperty("--frame-y", `${displayRect.y.toFixed(1)}px`);
        node.style.setProperty("--frame-w", `${displayRect.w.toFixed(1)}px`);
        node.style.setProperty("--frame-h", `${displayRect.h.toFixed(1)}px`);
        stage.appendChild(node);
        window.setTimeout(() => node.remove(), 900);
        return node;
      };

      const spawnLearnerPaintToolBurst = (point, mode = learnerPaintMode) => {
        const stage = paintCanvas && paintCanvas.parentElement;
        const displayPoint = learnerPaintDisplayPoint(point);
        if (!stage || !displayPoint) {
          return;
        }
        const safeMode = ["pen", "eraser", "text"].includes(mode) ? mode : "pen";
        const node = document.createElement("div");
        node.className = `ft-paint-click-burst is-${safeMode}`;
        node.setAttribute("aria-hidden", "true");
        node.style.transform = `translate3d(${displayPoint.x.toFixed(1)}px, ${displayPoint.y.toFixed(1)}px, 0)`;
        const count = safeMode === "text" ? 4 : safeMode === "eraser" ? 7 : 10;
        for (let index = 0; index < count; index += 1) {
          const piece = document.createElement("span");
          if (safeMode === "text") {
            const corners = [
              { x: "-54px", y: "-34px" },
              { x: "36px", y: "-34px" },
              { x: "36px", y: "18px" },
              { x: "-54px", y: "18px" },
            ];
            const corner = corners[index] || corners[0];
            piece.style.setProperty("--corner-x", corner.x);
            piece.style.setProperty("--corner-y", corner.y);
            piece.style.setProperty("--burst-delay", `${index * 70}ms`);
          } else {
            const baseAngle = safeMode === "eraser" ? -32 : -10;
            const spread = safeMode === "eraser" ? 360 / count : 360 / count;
            piece.style.setProperty("--burst-angle", `${baseAngle + index * spread}deg`);
            piece.style.setProperty("--burst-delay", `${index * (safeMode === "eraser" ? 35 : 22)}ms`);
          }
          node.appendChild(piece);
        }
        stage.appendChild(node);
        window.setTimeout(() => {
          node.remove();
        }, safeMode === "text" ? 2100 : safeMode === "eraser" ? 1500 : 1000);
      };

      const spawnLearnerPaintPenDust = (point) => {
        const now = performance.now();
        if (now - learnerPaintLastDustAt < 62) {
          return;
        }
        learnerPaintLastDustAt = now;
        const stage = paintCanvas && paintCanvas.parentElement;
        const displayPoint = learnerPaintDisplayPoint(point);
        if (!stage || !displayPoint) {
          return;
        }
        const node = document.createElement("div");
        node.className = "ft-paint-chalk-dust";
        node.setAttribute("aria-hidden", "true");
        node.style.transform = `translate3d(${displayPoint.x.toFixed(1)}px, ${displayPoint.y.toFixed(1)}px, 0)`;
        node.style.setProperty("--dust-color", paintColor && paintColor.value ? paintColor.value : "rgba(255, 209, 102, 0.86)");
        const count = 4;
        for (let index = 0; index < count; index += 1) {
          const dust = document.createElement("span");
          const side = index % 2 === 0 ? -1 : 1;
          const driftX = side * (5 + Math.random() * 10);
          const driftY = 4 + Math.random() * 12;
          dust.style.setProperty("--dust-x", `${driftX.toFixed(1)}px`);
          dust.style.setProperty("--dust-y", `${driftY.toFixed(1)}px`);
          dust.style.setProperty("--dust-size", `${(2.2 + Math.random() * 3.2).toFixed(1)}px`);
          dust.style.setProperty("--dust-delay", `${index * 28}ms`);
          node.appendChild(dust);
        }
        stage.appendChild(node);
        window.setTimeout(() => node.remove(), 980);
      };

      const learnerPaintBufferCtx = () => {
        if (!learnerPaintBufferCanvas) {
          learnerPaintBufferCanvas = document.createElement("canvas");
          learnerPaintBufferCanvas.width = LEARNER_PAINT_BOARD_WIDTH;
          learnerPaintBufferCanvas.height = LEARNER_PAINT_BOARD_HEIGHT;
        }
        return learnerPaintBufferCanvas.getContext("2d");
      };

      const learnerPaintEnsureBuffer = () => {
        const safeWidth = LEARNER_PAINT_BOARD_WIDTH;
        const safeHeight = LEARNER_PAINT_BOARD_HEIGHT;
        if (!learnerPaintBufferCanvas) {
          learnerPaintBufferCanvas = document.createElement("canvas");
        }
        if (learnerPaintBufferCanvas.width === safeWidth && learnerPaintBufferCanvas.height === safeHeight) {
          return;
        }
        const previous = learnerPaintBufferCanvas;
        const next = document.createElement("canvas");
        next.width = safeWidth;
        next.height = safeHeight;
        const ctx = next.getContext("2d");
        if (ctx && previous.width && previous.height) {
          ctx.drawImage(previous, 0, 0, previous.width, previous.height, 0, 0, safeWidth, safeHeight);
        }
        learnerPaintBufferCanvas = next;
      };

      const learnerPaintSelectionCanvas = (imageData) => {
        const canvas = document.createElement("canvas");
        canvas.width = imageData.width;
        canvas.height = imageData.height;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.putImageData(imageData, 0, 0);
        }
        return canvas;
      };

      const learnerPaintRect = (start, end) => {
        const x = Math.min(start.x, end.x);
        const y = Math.min(start.y, end.y);
        const w = Math.abs(end.x - start.x);
        const h = Math.abs(end.y - start.y);
        return { x, y, w, h };
      };

      const learnerPaintSelectionBounds = () => {
        if (!learnerPaintSelection) {
          return null;
        }
        return {
          x: learnerPaintSelection.x,
          y: learnerPaintSelection.y,
          w: learnerPaintSelection.w,
          h: learnerPaintSelection.h,
        };
      };

      const commitLearnerPaintSelection = () => {
        if (!learnerPaintSelection || (!learnerPaintSelection.imageData && !learnerPaintSelection.canvas)) {
          learnerPaintSelection = null;
          return;
        }
        const ctx = learnerPaintBufferCtx();
        if (ctx) {
          if (learnerPaintSelection.canvas) {
            ctx.drawImage(
              learnerPaintSelection.canvas,
              Math.round(learnerPaintSelection.x),
              Math.round(learnerPaintSelection.y),
              Math.round(learnerPaintSelection.w),
              Math.round(learnerPaintSelection.h)
            );
          } else {
            ctx.putImageData(learnerPaintSelection.imageData, Math.round(learnerPaintSelection.x), Math.round(learnerPaintSelection.y));
          }
        }
        learnerPaintSelection = null;
      };

      const drawLearnerPaintGrid = (ctx, width, height) => {
        ctx.fillStyle = "#f7fff9";
        ctx.fillRect(0, 0, width, height);
        ctx.strokeStyle = "rgba(15, 23, 42, 0.055)";
        ctx.lineWidth = 1;
        for (let x = 24; x < width; x += 24) {
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
          ctx.stroke();
        }
        for (let y = 24; y < height; y += 24) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(width, y);
          ctx.stroke();
        }
      };

      const learnerPaintCanvasCssSize = () => {
        if (!paintCanvas || !paintCanvas.parentElement) {
          return { width: LEARNER_PAINT_BOARD_WIDTH, height: LEARNER_PAINT_BOARD_HEIGHT, scale: 1 };
        }
        const stage = paintCanvas.parentElement;
        const rect = stage.getBoundingClientRect();
        if (rect.width < 20 || rect.height < 20) {
          return { width: LEARNER_PAINT_BOARD_WIDTH, height: LEARNER_PAINT_BOARD_HEIGHT, scale: 1 };
        }
        const style = window.getComputedStyle ? window.getComputedStyle(stage) : null;
        const padX = style ? (parseFloat(style.paddingLeft || "0") + parseFloat(style.paddingRight || "0")) : 0;
        const padY = style ? (parseFloat(style.paddingTop || "0") + parseFloat(style.paddingBottom || "0")) : 0;
        const availableWidth = Math.max(1, Number(rect.width || 0) - padX);
        const availableHeight = Math.max(1, Number(rect.height || 0) - padY);
        const scale = Math.max(0.01, Number(learnerPaintZoom || 1));
        return {
          width: Math.max(1, Math.ceil(availableWidth * scale) + 2),
          height: Math.max(1, Math.ceil(availableHeight * scale) + 2),
          scale,
        };
      };

      const fitLearnerPaintCanvasElement = () => {
        if (!paintCanvas || !paintCanvas.parentElement) {
          return;
        }
        const size = learnerPaintCanvasCssSize();
        paintCanvas.style.width = `${size.width}px`;
        paintCanvas.style.height = `${size.height}px`;
      };

      const updateLearnerPaintZoomLabel = () => {
        if (paintZoomLabel) {
          paintZoomLabel.textContent = `${Math.round(learnerPaintZoom * 100)}%`;
        }
      };

      const setLearnerPaintZoom = (nextZoom) => {
        learnerPaintZoom = learnerPaintClamp(Number(nextZoom || 1), 0.35, 3);
        updateLearnerPaintZoomLabel();
        resizeLearnerPaintCanvas();
        if (paintCanvas && paintCanvas.parentElement) {
          const stage = paintCanvas.parentElement;
          stage.scrollLeft = Math.max(0, (stage.scrollWidth - stage.clientWidth) / 2);
          stage.scrollTop = Math.max(0, (stage.scrollHeight - stage.clientHeight) / 2);
        }
      };

      const learnerPaintExportCanvas = () => {
        learnerPaintEnsureBuffer();
        if (!learnerPaintBufferCanvas) {
          return null;
        }
        const canvas = document.createElement("canvas");
        canvas.width = learnerPaintBufferCanvas.width;
        canvas.height = learnerPaintBufferCanvas.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          return null;
        }
        ctx.drawImage(learnerPaintBufferCanvas, 0, 0);
        if (learnerPaintSelection && learnerPaintSelection.canvas) {
          ctx.drawImage(
            learnerPaintSelection.canvas,
            Math.round(learnerPaintSelection.x),
            Math.round(learnerPaintSelection.y),
            Math.round(learnerPaintSelection.w),
            Math.round(learnerPaintSelection.h)
          );
        }
        return canvas;
      };

      const renderLearnerPaintSelection = (ctx) => {
        const selection = learnerPaintSelection;
        if (!selection) {
          return;
        }
        if (selection.canvas) {
          ctx.drawImage(selection.canvas, selection.x, selection.y, selection.w, selection.h);
        }
        ctx.save();
        const x = Number(selection.x || 0);
        const y = Number(selection.y || 0);
        const w = Math.max(1, Number(selection.w || 0));
        const h = Math.max(1, Number(selection.h || 0));
        const radius = Math.min(16, Math.max(7, Math.min(w, h) * 0.08));
        const strokeRounded = (sx, sy, sw, sh, sr) => {
          ctx.beginPath();
          if (typeof ctx.roundRect === "function") {
            ctx.roundRect(sx, sy, sw, sh, sr);
          } else {
            ctx.moveTo(sx + sr, sy);
            ctx.lineTo(sx + sw - sr, sy);
            ctx.quadraticCurveTo(sx + sw, sy, sx + sw, sy + sr);
            ctx.lineTo(sx + sw, sy + sh - sr);
            ctx.quadraticCurveTo(sx + sw, sy + sh, sx + sw - sr, sy + sh);
            ctx.lineTo(sx + sr, sy + sh);
            ctx.quadraticCurveTo(sx, sy + sh, sx, sy + sh - sr);
            ctx.lineTo(sx, sy + sr);
            ctx.quadraticCurveTo(sx, sy, sx + sr, sy);
          }
        };
        const gradient = ctx.createLinearGradient(x, y, x + w, y + h);
        gradient.addColorStop(0, "#0ddfd4");
        gradient.addColorStop(0.42, "#ffbb4d");
        gradient.addColorStop(0.72, "#ff4a84");
        gradient.addColorStop(1, "#0ddfd4");
        ctx.fillStyle = "rgba(13, 223, 212, 0.055)";
        strokeRounded(x, y, w, h, radius);
        ctx.fill();
        ctx.shadowColor = "rgba(2, 11, 14, 0.34)";
        ctx.shadowBlur = 12;
        ctx.shadowOffsetY = 3;
        ctx.setLineDash([]);
        ctx.lineWidth = 5;
        ctx.strokeStyle = "rgba(2, 11, 14, 0.42)";
        strokeRounded(x, y, w, h, radius);
        ctx.stroke();
        ctx.shadowColor = "rgba(13, 223, 212, 0.5)";
        ctx.shadowBlur = 13;
        ctx.shadowOffsetY = 0;
        ctx.lineWidth = 2.4;
        ctx.strokeStyle = gradient;
        strokeRounded(x, y, w, h, radius);
        ctx.stroke();
        ctx.shadowBlur = 0;
        ctx.setLineDash([12, 9]);
        ctx.lineWidth = 1.3;
        ctx.strokeStyle = "rgba(2, 11, 14, 0.42)";
        strokeRounded(x + 5, y + 5, Math.max(1, w - 10), Math.max(1, h - 10), Math.max(4, radius - 4));
        ctx.stroke();
        ctx.setLineDash([]);
        const corner = Math.min(48, Math.max(18, Math.min(w, h) * 0.24));
        const drawCorner = (sx, sy, flipX, flipY) => {
          ctx.beginPath();
          ctx.moveTo(sx, sy + flipY * corner);
          ctx.lineTo(sx, sy);
          ctx.lineTo(sx + flipX * corner, sy);
          ctx.stroke();
        };
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.lineWidth = 5;
        ctx.strokeStyle = "rgba(2, 11, 14, 0.52)";
        drawCorner(x, y, 1, 1);
        drawCorner(x + w, y, -1, 1);
        drawCorner(x, y + h, 1, -1);
        drawCorner(x + w, y + h, -1, -1);
        ctx.lineWidth = 2.4;
        ctx.strokeStyle = gradient;
        drawCorner(x, y, 1, 1);
        drawCorner(x + w, y, -1, 1);
        drawCorner(x, y + h, 1, -1);
        drawCorner(x + w, y + h, -1, -1);
        const handle = learnerPaintHandleBounds(selection);
        const cx = handle.x + handle.w / 2;
        const cy = handle.y + handle.h / 2;
        const r = Math.max(10, handle.w / 2);
        const handleGradient = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.35, 1, cx, cy, r * 1.35);
        handleGradient.addColorStop(0, "rgba(255,255,255,0.98)");
        handleGradient.addColorStop(0.22, "#ffbb4d");
        handleGradient.addColorStop(0.56, "#0ddfd4");
        handleGradient.addColorStop(1, "rgba(2, 11, 14, 0.92)");
        ctx.shadowColor = "rgba(2, 11, 14, 0.35)";
        ctx.shadowBlur = 14;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fillStyle = handleGradient;
        ctx.fill();
        ctx.lineWidth = 2.5;
        ctx.strokeStyle = "rgba(255, 255, 255, 0.92)";
        ctx.stroke();
        ctx.shadowColor = "rgba(255, 187, 77, 0.64)";
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(cx, cy, r * 0.58, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(2, 11, 14, 0.62)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(cx - r * 0.35, cy);
        ctx.lineTo(cx + r * 0.35, cy);
        ctx.moveTo(cx, cy - r * 0.35);
        ctx.lineTo(cx, cy + r * 0.35);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
        ctx.lineWidth = 1.4;
        ctx.stroke();
        ctx.restore();
      };

      const renderLearnerPaintDraftRect = (ctx) => {
        if (!learnerPaintPointer || learnerPaintPointer.type !== "select-region") {
          return;
        }
        const rect = learnerPaintRect(learnerPaintPointer.start, learnerPaintPointer.current || learnerPaintPointer.start);
        if (rect.w < 2 || rect.h < 2) {
          return;
        }
        ctx.save();
        const gradient = ctx.createLinearGradient(rect.x, rect.y, rect.x + rect.w, rect.y + rect.h);
        gradient.addColorStop(0, "#0ddfd4");
        gradient.addColorStop(0.55, "#ffbb4d");
        gradient.addColorStop(1, "#ff4a84");
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(13, 223, 212, 0.075)";
        ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
        ctx.lineWidth = 4;
        ctx.strokeStyle = "rgba(2, 11, 14, 0.44)";
        ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
        ctx.setLineDash([10, 7]);
        ctx.lineWidth = 1.7;
        ctx.strokeStyle = gradient;
        ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
        ctx.restore();
      };

      const renderLearnerPaint = () => {
        if (!paintCanvas) {
          return;
        }
        const ctx = learnerPaintCtx();
        if (!ctx) {
          return;
        }
        fitLearnerPaintCanvasElement();
        const rect = paintCanvas.getBoundingClientRect();
        const dpr = Math.max(1, window.devicePixelRatio || 1);
        const cssWidth = Math.max(1, rect.width || paintCanvas.clientWidth || 800);
        const cssHeight = Math.max(1, rect.height || paintCanvas.clientHeight || 520);
        const nextWidth = Math.max(1, Math.round(cssWidth * dpr));
        const nextHeight = Math.max(1, Math.round(cssHeight * dpr));
        if (paintCanvas.width !== nextWidth || paintCanvas.height !== nextHeight) {
          paintCanvas.width = nextWidth;
          paintCanvas.height = nextHeight;
        }
        learnerPaintEnsureBuffer();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, paintCanvas.width, paintCanvas.height);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        const boardWidth = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.width : LEARNER_PAINT_BOARD_WIDTH;
        const boardHeight = learnerPaintBufferCanvas ? learnerPaintBufferCanvas.height : LEARNER_PAINT_BOARD_HEIGHT;
        ctx.save();
        ctx.scale(cssWidth / Math.max(1, boardWidth), cssHeight / Math.max(1, boardHeight));
        drawLearnerPaintGrid(ctx, boardWidth, boardHeight);
        if (learnerPaintBufferCanvas) {
          ctx.drawImage(learnerPaintBufferCanvas, 0, 0, boardWidth, boardHeight);
        }
        renderLearnerPaintSelection(ctx);
        renderLearnerPaintDraftRect(ctx);
        ctx.restore();
        positionLearnerPaintRemoteCursor();
      };

      const resizeLearnerPaintCanvas = () => {
        if (!paintCanvas) {
          return;
        }
        fitLearnerPaintCanvasElement();
        const rect = paintCanvas.getBoundingClientRect();
        const dpr = Math.max(1, window.devicePixelRatio || 1);
        const cssWidth = Math.max(1, rect.width || paintCanvas.clientWidth || 800);
        const cssHeight = Math.max(1, rect.height || paintCanvas.clientHeight || 520);
        const nextWidth = Math.max(1, Math.round(cssWidth * dpr));
        const nextHeight = Math.max(1, Math.round(cssHeight * dpr));
        if (paintCanvas.width !== nextWidth || paintCanvas.height !== nextHeight) {
          paintCanvas.width = nextWidth;
          paintCanvas.height = nextHeight;
        }
        learnerPaintEnsureBuffer();
        renderLearnerPaint();
        positionLearnerPaintRemoteCursor();
      };

      const setLearnerPaintSyncStatus = (message) => {
        const text = clean(message || "");
        if (paintSyncStatus) {
          paintSyncStatus.textContent = text;
        }
        const shouldShowTop = Boolean(
          text
          && !/^Paint synced rev\b/i.test(text)
          && !/^Paint rev \d+$/i.test(text)
        );
        if (!shouldShowTop || !topLoading || !topLoadingText) {
          return;
        }
        if (learnerPaintTopStatusTimer) {
          window.clearTimeout(learnerPaintTopStatusTimer);
          learnerPaintTopStatusTimer = 0;
        }
        const isError = /error|failed|waiting|blocked|not available|could not|choose|select/i.test(text);
        topLoadingText.textContent = text;
        topLoading.classList.add("is-visible");
        topLoading.classList.remove("is-working");
        topLoading.classList.toggle("is-error", isError);
        topLoading.style.removeProperty("--ft-working-progress");
        topLoading.setAttribute("aria-hidden", "false");
        learnerPaintTopStatusTimer = window.setTimeout(() => {
          if (topLoadingText && clean(topLoadingText.textContent || "") === text) {
            topLoading.classList.remove("is-visible", "is-error", "is-working");
            topLoading.setAttribute("aria-hidden", "true");
          }
        }, isError ? 4200 : 2600);
      };

      const learnerPaintSnapshotPayload = () => {
        const exportCanvas = learnerPaintExportCanvas();
        if (!exportCanvas) {
          return null;
        }
        return {
          data: exportCanvas.toDataURL("image/png"),
          width: exportCanvas.width,
          height: exportCanvas.height,
        };
      };

      const applyLearnerPaintState = (state = {}) => {
        const revision = Number(state.revision || 0);
        if (!revision || revision <= learnerPaintRevision || learnerPaintPointer || learnerPaintTextEditor || learnerPaintSelection || learnerPaintClearAnimating) {
          return;
        }
        learnerPaintRevision = revision;
        learnerPaintApplyingRemote = true;
        const data = String(state.data || "");
        if (!data) {
          const ctx = learnerPaintBufferCtx();
          if (ctx && learnerPaintBufferCanvas) {
            ctx.clearRect(0, 0, learnerPaintBufferCanvas.width, learnerPaintBufferCanvas.height);
          }
          learnerPaintApplyingRemote = false;
          renderLearnerPaint();
          setLearnerPaintSyncStatus(`Paint rev ${revision}`);
          return;
        }
        const image = new Image();
        image.onload = () => {
          learnerPaintEnsureBuffer();
          const ctx = learnerPaintBufferCtx();
          if (ctx && learnerPaintBufferCanvas) {
            ctx.clearRect(0, 0, learnerPaintBufferCanvas.width, learnerPaintBufferCanvas.height);
            ctx.drawImage(image, 0, 0, learnerPaintBufferCanvas.width, learnerPaintBufferCanvas.height);
          }
          learnerPaintApplyingRemote = false;
          renderLearnerPaint();
          setLearnerPaintSyncStatus(`Paint rev ${revision} from ${state.updated_by || "admin"}`);
        };
        image.onerror = () => {
          learnerPaintApplyingRemote = false;
          setLearnerPaintSyncStatus("Paint sync image error");
        };
        image.src = data;
      };

      const syncLearnerPaintSnapshot = async () => {
        if (!authToken || !learnerPaintOpen || !learnerPaintServerConnected || learnerPaintApplyingRemote || learnerPaintSyncing || learnerPaintClearAnimating) {
          return;
        }
        const payload = learnerPaintSnapshotPayload();
        if (!payload) {
          return;
        }
        learnerPaintSyncing = true;
        try {
          const result = await fetchAuthJson("/paint/sync", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          learnerPaintServerConnected = Boolean(learnerPaintOpen);
          const state = result.payload && result.payload.state || {};
          learnerPaintRevision = Math.max(learnerPaintRevision, Number(state.revision || 0));
          if (learnerPaintServerConnected && !learnerPaintPollTimer) {
            scheduleLearnerPaintPoll(LEARNER_PAINT_POLL_INTERVAL_MS);
          }
          setLearnerPaintSyncStatus(`Paint synced rev ${learnerPaintRevision || 0}`);
        } catch (error) {
          learnerPaintServerConnected = false;
          setLearnerPaintSyncStatus(error && error.message ? error.message : "Paint sync failed");
        } finally {
          learnerPaintSyncing = false;
        }
      };

      const scheduleLearnerPaintSync = (delay = 220) => {
        if (!authToken || !learnerPaintOpen || learnerPaintApplyingRemote) {
          return;
        }
        if (!learnerPaintServerConnected) {
          learnerPaintPendingSyncAfterConnect = true;
          return;
        }
        learnerPaintPendingSyncAfterConnect = false;
        window.clearTimeout(learnerPaintSyncTimer);
        learnerPaintSyncTimer = window.setTimeout(() => {
          void syncLearnerPaintSnapshot();
        }, delay);
      };

      const scheduleLearnerPaintPoll = (delay = LEARNER_PAINT_POLL_INTERVAL_MS) => {
        if (!authToken || !learnerPaintOpen || !learnerPaintServerConnected) {
          return;
        }
        window.clearTimeout(learnerPaintPollTimer);
        learnerPaintPollTimer = window.setTimeout(() => {
          void pollLearnerPaint({ scheduleNext: true });
        }, Math.max(1000, Number(delay) || LEARNER_PAINT_POLL_INTERVAL_MS));
      };

      const pollLearnerPaint = async (options = {}) => {
        const scheduleNext = Boolean(options.scheduleNext);
        if (!authToken || !learnerPaintOpen || learnerPaintPollInFlight) {
          return;
        }
        learnerPaintPollInFlight = true;
        try {
          const result = await fetchAuthJson(`/paint/state?after=${encodeURIComponent(String(learnerPaintRevision || 0))}`);
          learnerPaintServerConnected = Boolean(learnerPaintOpen);
          if (!learnerPaintOpen) {
            return;
          }
          const state = result.payload && result.payload.state || {};
          renderLearnerPaintRemoteCursor(state.cursors && state.cursors.admin);
          if (Number(state.revision || 0) > learnerPaintRevision && state.data !== undefined) {
            applyLearnerPaintState(state);
          }
          if (learnerPaintPendingSyncAfterConnect) {
            scheduleLearnerPaintSync(900);
          }
        } catch (error) {
          learnerPaintServerConnected = false;
          if (learnerPaintOpen) {
            setLearnerPaintSyncStatus(error && error.message ? error.message : "Paint sync waiting");
          }
        } finally {
          learnerPaintPollInFlight = false;
          if (scheduleNext && learnerPaintServerConnected) {
            scheduleLearnerPaintPoll(LEARNER_PAINT_POLL_INTERVAL_MS);
          }
        }
      };

      const stopLearnerPaintPolling = () => {
        if (learnerPaintPollTimer) {
          window.clearTimeout(learnerPaintPollTimer);
          learnerPaintPollTimer = 0;
        }
        if (learnerPaintSyncTimer) {
          window.clearTimeout(learnerPaintSyncTimer);
          learnerPaintSyncTimer = 0;
        }
        learnerPaintServerConnected = false;
        learnerPaintPollInFlight = false;
        learnerPaintPendingSyncAfterConnect = false;
      };

      const startLearnerPaintPolling = () => {
        stopLearnerPaintPolling();
        if (!authToken || !learnerPaintOpen) {
          return;
        }
        void pollLearnerPaint({ scheduleNext: true });
      };

      const learnerPaintSizePreferenceKey = (mode = "pen") => `future.paint.${mode}.size`;

      const learnerPaintReadSizePreference = (mode = "pen", fallback = 6) => {
        try {
          const value = Number(localStorage.getItem(learnerPaintSizePreferenceKey(mode)));
          return Number.isFinite(value) ? learnerPaintClamp(value, 1, 30) : fallback;
        } catch (error) {
          return fallback;
        }
      };

      const learnerPaintSaveSizePreference = (mode = "pen", value = 6) => {
        try {
          localStorage.setItem(learnerPaintSizePreferenceKey(mode), String(learnerPaintClamp(value, 1, 30)));
        } catch (error) {
        }
      };

      const loadLearnerPaintToolSizes = () => {
        learnerPaintPenSize = learnerPaintReadSizePreference("pen", learnerPaintPenSize);
        learnerPaintEraserSize = learnerPaintReadSizePreference("eraser", learnerPaintEraserSize);
        learnerPaintTextSizeLevel = learnerPaintReadSizePreference("text", learnerPaintTextSizeLevel);
      };

      const learnerPaintModeSize = (mode = learnerPaintMode) => {
        if (mode === "eraser") {
          return learnerPaintEraserSize;
        }
        if (mode === "text") {
          return learnerPaintTextSizeLevel;
        }
        return learnerPaintPenSize;
      };

      const syncLearnerPaintSizeControlToMode = (mode = learnerPaintMode) => {
        if (!paintSize) {
          return;
        }
        const value = learnerPaintModeSize(mode);
        paintSize.value = String(Math.round(value));
        const label = mode === "eraser" ? "Eraser size" : mode === "text" ? "Text size" : "Pen size";
        paintSize.title = `${label}: ${Math.round(value)}`;
        paintSize.setAttribute("aria-label", label);
      };

      const syncLearnerPaintSizeFromControl = () => {
        const value = learnerPaintClamp(Number(paintSize && paintSize.value || 6), 1, 30);
        if (learnerPaintMode === "eraser") {
          learnerPaintEraserSize = value;
          learnerPaintSaveSizePreference("eraser", value);
        } else if (learnerPaintMode === "text") {
          learnerPaintTextSizeLevel = value;
          learnerPaintSaveSizePreference("text", value);
        } else {
          learnerPaintPenSize = value;
          learnerPaintSaveSizePreference("pen", value);
        }
        syncLearnerPaintSizeControlToMode(learnerPaintMode);
      };

      loadLearnerPaintToolSizes();

      const setLearnerPaintMode = (mode) => {
        const nextMode = ["select", "pen", "eraser", "text"].includes(mode) ? mode : "select";
        if (learnerPaintTextEditor && nextMode !== "text") {
          commitLearnerPaintTextEditor();
        }
        if (learnerPaintSelection && nextMode !== "select") {
          commitLearnerPaintSelection();
          scheduleLearnerPaintSync(120);
        }
        if (nextMode !== "select") {
          clearLearnerPaintSelectAnchor();
        }
        learnerPaintMode = nextMode;
        paintModeButtons.forEach((button) => {
          const active = button.dataset.paintMode === nextMode;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-pressed", active ? "true" : "false");
        });
        if (paintCanvas) {
          paintCanvas.classList.toggle("is-selecting", nextMode === "select");
          paintCanvas.classList.toggle("has-tool-cursor", true);
          paintCanvas.dataset.paintMode = nextMode;
        }
        if (paintToolCursor) {
          paintToolCursor.dataset.mode = nextMode;
          paintToolCursor.classList.toggle("is-erasing", false);
        }
        syncLearnerPaintSizeControlToMode(nextMode);
        renderLearnerPaint();
      };

      const syncLearnerPaintFullscreenButton = () => {
        if (!paintFullscreen) {
          return;
        }
        const isFullscreen = Boolean(document.fullscreenElement);
        paintFullscreen.dataset.paintIcon = isFullscreen ? "↙" : "⛶︎";
        paintFullscreen.title = isFullscreen ? "Exit fullscreen" : "Fullscreen";
        paintFullscreen.setAttribute("aria-label", isFullscreen ? "Exit fullscreen" : "Fullscreen");
        paintFullscreen.setAttribute("aria-pressed", isFullscreen ? "true" : "false");
      };

      const scheduleLearnerPaintViewportRefresh = () => {
        window.requestAnimationFrame(() => {
          resizeLearnerPaintCanvas();
          window.setTimeout(resizeLearnerPaintCanvas, 90);
          window.setTimeout(resizeLearnerPaintCanvas, 240);
        });
      };

      const openLearnerPaint = () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de mo bang nhap.");
          return;
        }
        learnerPaintOpen = true;
        document.documentElement.classList.add("ft-paint-performance-mode");
        if (paintModal) {
          paintModal.classList.add("is-open");
          paintModal.setAttribute("aria-hidden", "false");
        }
        setLearnerPaintMode(learnerPaintMode);
        syncLearnerPaintFullscreenButton();
        startLearnerPaintPolling();
        if (typeof requestAnyFullscreen === "function" && !document.fullscreenElement) {
          void Promise.resolve(requestAnyFullscreen())
            .catch(() => false)
            .finally(() => {
              syncLearnerPaintFullscreenButton();
              scheduleLearnerPaintViewportRefresh();
            });
        } else {
          scheduleLearnerPaintViewportRefresh();
        }
      };

      const closeLearnerPaint = () => {
        if (learnerPaintTextEditor) {
          commitLearnerPaintTextEditor();
        }
        commitLearnerPaintSelection();
        learnerPaintOpen = false;
        document.documentElement.classList.remove("ft-paint-performance-mode");
        learnerPaintPointer = null;
        clearLearnerPaintSelectAnchor();
        learnerPaintLocalCursor = learnerPaintCursorPayload(learnerPaintLocalCursor || { x: 0, y: 0 }, false);
        if (learnerPaintServerConnected) {
          void sendLearnerPaintCursor();
        }
        hideLearnerPaintRemoteCursor();
        hideLearnerPaintToolCursor();
        if (paintModal) {
          paintModal.classList.remove("is-open");
          paintModal.setAttribute("aria-hidden", "true");
        }
        stopLearnerPaintPolling();
      };

      let sharedWorldPollingTimer = 0;
      let sharedWorldLoading = false;
      let sharedWorldLoadingAt = 0;
      let sharedWorldRequestSeq = 0;
      let sharedWorldReconnectTimer = 0;
      let sharedWorldReconnectAttempts = 0;
      let sharedWorldStatusHideTimer = 0;
      let sharedWorldMapMode = "city";
      const sharedWorldNodes = new Map();
      const sharedWorldPositions = new Map();
      const sharedWorldRoster = new Map();
      const sharedWorldPathQueues = new Map();
      let sharedWorldMotionFrame = 0;
      let sharedWorldMotionLastAt = 0;
      let sharedWorldStageDrag = null;
      let sharedWorldSuppressNextMapClick = false;
      let sharedWorldMoveMarkerPoint = null;
      let sharedWorldMoveMarkerHideTimer = 0;
      let sharedWorldSelectedTargetKey = "";
      let sharedWorldSelectedPoint = null;
      let sharedWorldPickingPosition = false;
      let sharedWorldNeedInitialCenter = false;
      let sharedWorldFollowSelf = false;
      let sharedWorldFollowFrame = 0;
      let sharedWorldAutoLocateAt = 0;
      let sharedWorldFollowTargetKey = "";
      let sharedWorldFollowMoveAt = 0;
      let sharedWorldKeyboardMoveAt = 0;
      let sharedWorldLocalMoveAt = 0;
      const sharedWorldHeldArrows = new Set();
      let sharedWorldKeyboardFrame = 0;
      let sharedWorldKeyboardLastAt = 0;
      let sharedWorldKeyboardSyncAt = 0;
      let sharedWorldKeyboardSyncStartedAt = 0;
      let sharedWorldKeyboardSyncing = false;
      let sharedWorldKeyboardQueuedPoint = null;
      let sharedWorldKeyboardPass = { enabled: false, expires_at: "", remaining_seconds: 0, cost: 10 };
      let sharedWorldKeyboardPassTimer = 0;
      let sharedWorldKeyboardPassBuying = false;
      let sharedWorldWitchBubbleTimer = 0;
      let sharedWorldShopOpenTimer = 0;
      let sharedWorldInventory = null;
      let sharedWorldSkinSettings = [];
      let sharedWorldBattleState = null;
      let sharedWorldActiveBattlePairs = [];
      const sharedWorldBattleLinkNodes = new Map();
      let sharedWorldBattleInviteId = "";
      let sharedWorldBattleTimer = 0;
      let sharedWorldBattleLastLogKey = "";
      let sharedWorldBattleLastTurnKey = "";
      let sharedWorldBattleFinishing = false;
      let sharedWorldBattleDismissedFinishedId = "";
      let sharedWorldBattleLoading = false;
      let sharedWorldBattleLoadingAt = 0;
      let sharedWorldBattleRequestSeq = 0;
      let sharedWorldBattlePollingTimer = 0;
      const sharedWorldBattleVisualTimers = new Set();
      let sharedWorldTrainingState = null;
      let sharedWorldTrainingLoading = false;
      let sharedWorldTrainingRequestSeq = 0;
      let sharedWorldTrainingLastEventKey = "";
      let sharedWorldTrainingPollTimer = 0;
      let sharedWorldTrainingLocalMotionTimer = 0;
      let sharedWorldTrainingExitArmed = true;
      let sharedWorldTrainingAutoSpeechKey = "";
      let sharedWorldTrainingAudioKey = "";
      let sharedWorldTrainingAudioPlayer = null;
      let sharedWorldTrainingAnchorSyncAt = 0;
      let sharedWorldTrainingSkillCooldownTimer = 0;
      const sharedWorldTrainingSkillCooldownUntil = new Map();
      const sharedWorldTrainingLootDrops = new Map();
      let sharedWorldTrainingLootTimer = 0;
      let sharedWorldTrainingSpeech = {
        active: false,
        recognition: null,
        timer: 0,
        settleTimer: 0,
        deadline: 0,
        slimeId: "",
        questionId: "",
        expectedText: "",
        passRatio: 1,
        transcript: "",
        chunk: "",
        historyKey: "",
        hideTarget: false,
        posted: false,
        passed: false,
      };
      let sharedWorldTrainingServerSpeech = {
        active: false,
        recorder: null,
        stream: null,
        chunks: [],
        timer: 0,
        startedAt: 0,
        slimeId: "",
        questionId: "",
        transcript: "",
        message: "",
        busy: false,
        cancel: false,
      };
      let sharedWorldTrainingServerSpeechCtrlCandidate = "";
      const sharedWorldActions = ["jump", "spin", "wave", "dance"];
      const sharedWorldMoveStep = 0.055;
      const sharedWorldVocabularyCrystalId = "leaderboard_space_v_crystal";
      const sharedWorldCityTrainingGatePoint = { x: 0.88, y: 0.53 };
      const sharedWorldTrainingEntryPoint = { x: 0.155, y: 0.5 };
      const defaultSharedWorldSkins = () => ([
        { id: "slime", name: "Slime", price: 35, image: "", description: "A soft crystal slime form with elastic motion." },
        { id: "cloud", name: "Cloud", price: 45, image: "", description: "A floating cloud spirit form with vapor trails." },
        { id: "star-fox", name: "Star Fox", price: 60, image: "", description: "A quick cosmic fox form for bright movement." },
        { id: "crystal-golem", name: "Crystal Golem", price: 80, image: "", description: "A heavy prism golem form with strong crystal armor." },
        { id: "moon-cat", name: "Moon Cat", price: 55, image: "", description: "A quiet moon cat form with soft neon ears." },
        { id: "ember-dragon", name: "Ember Dragon", price: 95, image: "", description: "A small dragon form with ember wings." },
        { id: "aqua-sprite", name: "Aqua Sprite", price: 50, image: "", description: "A water sprite form with flowing blue light." },
        { id: "thunder-cub", name: "Thunder Cub", price: 70, image: "", description: "A storm cub form with electric sparks." },
        { id: "leaf-spirit", name: "Leaf Spirit", price: 42, image: "", description: "A forest spirit form with living leaf marks." },
        { id: "neon-orb", name: "Neon Orb", price: 65, image: "", description: "A clean neon orb form with a hologram core." },
      ]);

      const normalizeSharedWorldSkins = (items = []) => {
        const source = Array.isArray(items) && items.length ? items : defaultSharedWorldSkins();
        return source.map((item, index) => {
          const raw = item && typeof item === "object" ? item : {};
          const name = clean(raw.name || raw.title || `Skin ${index + 1}`).slice(0, 80);
          if (!name) return null;
          const id = clean(raw.id || name).toLowerCase().replace(/[^a-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 64) || `skin-${index + 1}`;
          const price = Math.max(0, Math.min(999999, Math.round(Number(raw.price ?? raw.cost ?? 50) || 0)));
          return {
            id,
            name,
            price,
            image: clean(raw.image || raw.image_url || raw.imageUrl || "").slice(0, 600),
            description: clean(raw.description || raw.desc || "").slice(0, 300),
          };
        }).filter(Boolean).slice(0, 24);
      };

      sharedWorldSkinSettings = normalizeSharedWorldSkins(defaultSharedWorldSkins());

      const hideSharedWorldStatus = () => {
        if (sharedWorldStatusHideTimer) {
          window.clearTimeout(sharedWorldStatusHideTimer);
          sharedWorldStatusHideTimer = 0;
        }
        if (!worldStatus) {
          return;
        }
        worldStatus.classList.remove("is-visible", "is-error", "is-ok");
        worldStatus.setAttribute("aria-hidden", "true");
      };

      const setSharedWorldStatus = (message = "", tone = "") => {
        if (!worldStatus) {
          return;
        }
        if (sharedWorldStatusHideTimer) {
          window.clearTimeout(sharedWorldStatusHideTimer);
          sharedWorldStatusHideTimer = 0;
        }
        if (worldStatusText) {
          worldStatusText.textContent = message || "";
        } else {
          worldStatus.textContent = message || "";
        }
        worldStatus.classList.toggle("is-error", tone === "error");
        worldStatus.classList.toggle("is-ok", tone === "ok");
        worldStatus.classList.add("is-visible");
        worldStatus.setAttribute("aria-hidden", "false");
        sharedWorldStatusHideTimer = window.setTimeout(hideSharedWorldStatus, 3000);
      };

      const setSharedWorldCloseMenuOpen = (open = false) => {
        const active = Boolean(open);
        if (worldCloseMenu) {
          worldCloseMenu.classList.toggle("is-open", active);
          worldCloseMenu.setAttribute("aria-hidden", active ? "false" : "true");
        }
        if (worldMenuTrigger) {
          worldMenuTrigger.setAttribute("aria-expanded", active ? "true" : "false");
        }
        if (worldClose) {
          worldClose.setAttribute("aria-expanded", active ? "true" : "false");
        }
      };

      const toggleSharedWorldCloseMenu = () => {
        setSharedWorldCloseMenuOpen(!(worldCloseMenu && worldCloseMenu.classList.contains("is-open")));
      };

      const sharedWorldClamp = (value, fallback = 0.5) => {
        const number = Number(value);
        if (!Number.isFinite(number)) {
          return fallback;
        }
        return Math.max(0.04, Math.min(0.96, number));
      };

      const sharedWorldRecent = (value = "", maxAgeMs = 12000) => {
        const stamp = Date.parse(value || "");
        return Number.isFinite(stamp) && Date.now() - stamp < maxAgeMs;
      };

      const sharedWorldTrainingPercent = (value, maxValue) => {
        const current = Math.max(0, Number(value || 0) || 0);
        const total = Math.max(1, Number(maxValue || 0) || 1);
        return `${Math.max(0, Math.min(100, (current / total) * 100)).toFixed(1)}%`;
      };

      const setSharedWorldTrainingBusy = (busy = false) => {
        sharedWorldTrainingLoading = Boolean(busy);
        if (worldTrainingAnswerForm) {
          worldTrainingAnswerForm.classList.toggle("is-busy", sharedWorldTrainingLoading);
        }
        if (worldTrainingSubmit) {
          const selected = worldTrainingSelectedSlime();
          const question = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
          const legacySpeechQuestion = (
            sharedWorldTrainingQuestionIsSpeech(question)
            || sharedWorldTrainingQuestionIsServerSpeech(question)
          ) && !sharedWorldTrainingUsesBrowserSpeechInput(question);
          worldTrainingSubmit.disabled = sharedWorldTrainingLoading || legacySpeechQuestion;
        }
        if (worldTrainingReset) {
          worldTrainingReset.disabled = sharedWorldTrainingLoading;
        }
        renderSharedWorldTrainingQuickSkill();
      };

      const setSharedWorldTrainingQuestionOpen = (open = false) => {
        if (worldTrainingModal) {
          worldTrainingModal.classList.toggle("is-question-open", Boolean(open));
        }
        if (!open) {
          sharedWorldTrainingAutoSpeechKey = "";
          sharedWorldTrainingAudioKey = "";
          stopSharedWorldTrainingAudio();
          cancelSharedWorldTrainingServerSpeech();
          if (sharedWorldTrainingSpeech.active) {
            stopSharedWorldTrainingSpeech();
          } else {
            sharedWorldTrainingSpeech.expectedText = "";
            sharedWorldTrainingSpeech.passRatio = 1;
            sharedWorldTrainingSpeech.transcript = "";
            sharedWorldTrainingSpeech.chunk = "";
            sharedWorldTrainingSpeech.hideTarget = false;
            clearSharedWorldTrainingSpeechOverhead();
          }
        }
      };

      const sharedWorldTrainingIsActive = () => Boolean(
        sharedWorldMapMode === "training"
        && worldTrainingModal
        && worldTrainingModal.classList.contains("is-open")
      );

      const sharedWorldTrainingSlimeHost = () => (
        sharedWorldMapMode === "training" && worldTrainingMapSlimes
          ? worldTrainingMapSlimes
          : worldTrainingSlimes
      );

      const sharedWorldTrainingEffectHost = () => {
        const parent = sharedWorldMapMode === "training" && worldTrainingField ? worldTrainingField : worldArena;
        if (!parent) {
          return null;
        }
        let host = parent.querySelector("#ft-world-training-effects");
        if (!host) {
          host = document.createElement("div");
          host.id = "ft-world-training-effects";
          host.className = "ft-world-training-effects";
          host.setAttribute("aria-hidden", "true");
          parent.appendChild(host);
        }
        return host;
      };

      const ensureSharedWorldSelfNode = (point = null) => {
        if (!worldPlayers) {
          return null;
        }
        const username = clean(activeWorldUsername() || currentAuthUsername || "learner") || "learner";
        const key = username.toLowerCase();
        let node = sharedWorldNodes.get(key);
        if (!node) {
          node = createSharedWorldNode(username);
          sharedWorldNodes.set(key, node);
          worldPlayers.appendChild(node);
        }
        const fallbackPoint = point && typeof point === "object" ? point : { x: 0.18, y: 0.72 };
        let pos = sharedWorldPositions.get(key);
        if (!pos) {
          pos = {
            x: sharedWorldClamp(fallbackPoint.x),
            y: sharedWorldClamp(fallbackPoint.y),
            tx: sharedWorldClamp(fallbackPoint.x),
            ty: sharedWorldClamp(fallbackPoint.y),
          };
          sharedWorldPositions.set(key, pos);
        }
        node.dataset.username = username;
        node.classList.add("is-me");
        node.classList.remove("is-playing", "is-target-selected");
        const displayName = clean(currentAuthProfile && (currentAuthProfile.display_name || currentAuthProfile.displayName || currentAuthProfile.full_name || currentAuthProfile.fullName))
          || clean(currentAuthUsername)
          || username;
        const gender = clean(currentAuthProfile && (currentAuthProfile.gender || currentAuthProfile.sex || "")) || "other";
        renderSharedWorldName(node, displayName, gender);
        renderSharedWorldLevel(node, {});
        renderSharedWorldTopMeta(node, {});
        sharedWorldRoster.set(key, {
          username,
          displayName,
          gender,
          x: pos.x,
          y: pos.y,
          tx: pos.tx,
          ty: pos.ty,
        });
        applySharedWorldNodePosition(node, pos.x, pos.y);
        return { key, node, pos };
      };

      const setSharedWorldSelfPosition = (point = {}, options = {}) => {
        const fallback = point && typeof point === "object" ? point : { x: 0.5, y: 0.5 };
        const self = ensureSharedWorldSelfNode(fallback);
        if (!self || !self.pos) {
          return null;
        }
        const x = sharedWorldClamp(fallback.x);
        const y = sharedWorldClamp(fallback.y);
        self.pos.x = x;
        self.pos.y = y;
        self.pos.tx = x;
        self.pos.ty = y;
        applySharedWorldNodePosition(self.node, x, y);
        if (options.center !== false) {
          window.requestAnimationFrame(() => centerSharedWorldViewportOn(x, y, Boolean(options.smooth)));
        }
        return { ...self, point: { x, y } };
      };

      const maybeExitSharedWorldTrainingByGate = () => {
        if (sharedWorldMapMode !== "training" || !sharedWorldTrainingExitArmed) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        const dx = sharedWorldClamp(self.x) - 0.065;
        const dy = sharedWorldClamp(self.y) - 0.5;
        if (Math.hypot(dx, dy) > 0.07) {
          return;
        }
        sharedWorldTrainingExitArmed = false;
        setSharedWorldStatus("Passing back through the QM-City gate...", "ok");
        window.setTimeout(() => {
          closeSharedWorldTraining({ returnToCityGate: true });
          sharedWorldTrainingExitArmed = true;
        }, 120);
      };

      const sharedWorldTrainingQuestionMeta = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.kind || "").toLowerCase();
        const meaning = clean(row.meaning || row.translation || "");
        const type = clean(row.type || "");
        const prompt = clean(row.prompt || "");
        const sentenceLike = kind === "sentence" || /sentence|space_w|space_p|câu/i.test(type) || meaning.length > 80;
        return {
          kind,
          sentenceLike,
          main: meaning || prompt || "Select this slime to answer.",
          meta: sentenceLike ? "Sentence meaning" : (type || "Vocabulary"),
        };
      };

      const sharedWorldTrainingQuestionVisualMeta = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const base = sharedWorldTrainingQuestionMeta(row);
        const kind = clean(row.kind || "").toLowerCase();
        const trainingKind = clean(row.training_kind || row.trainingKind || kind).toLowerCase();
        const type = clean(row.type || "");
        const readText = clean(row.read_text || row.readText || "");
        const ipa = clean(row.ipa || row.ipa_uk || row.ipaUk || row.ipa_us || row.ipaUs || "");
        const audioLike = sharedWorldTrainingQuestionIsSpeech(row);
        const audioInput = sharedWorldTrainingQuestionIsAudioInput(row);
        const viPromptSpeech = sharedWorldTrainingQuestionIsViPromptSpeech(row);
        const serverSpeech = sharedWorldTrainingQuestionIsServerSpeech(row);
        const sentenceLike = Boolean(base.sentenceLike || kind === "read_sentence" || readText.split(/\s+/).filter(Boolean).length >= 4);
        if (serverSpeech) {
          const passPercent = Math.max(1, Math.min(100, Math.round(Number(row.accept_percent ?? row.acceptPercent ?? 60) || 60)));
          return {
            ...base,
            kindClass: "is-kind-translate",
            enemyClass: "is-enemy-fangbeast",
            main: clean(row.source_text || row.sourceText || row.prompt || "") || "Speak the Vietnamese translation",
            meta: `Speak Vietnamese - pass ${passPercent}%`,
          };
        }
        if (trainingKind === "translate_vi" || kind === "translate_vi") {
          return {
            ...base,
            kindClass: "is-kind-translate",
            enemyClass: "is-enemy-fangbeast",
            main: clean(row.source_text || row.sourceText || row.prompt || "") || "Translate this sentence",
            meta: "Translate to Vietnamese · 70%",
          };
        }
        if (audioInput) {
          return {
            ...base,
            kindClass: "is-kind-audio",
            main: clean(row.prompt || "") || "Listen and type the answer",
            meta: sentenceLike ? "Audio dictation sentence" : "Audio dictation word",
          };
        }
        if (audioLike) {
          return {
            ...base,
            kindClass: "is-kind-audio",
            main: viPromptSpeech ? (clean(row.meaning || row.prompt || "") || "Speak the English answer") : (readText || clean(row.prompt || "") || "Read aloud"),
            meta: viPromptSpeech ? "Vietnamese cue - speak English" : (ipa || (sentenceLike ? "Read sentence aloud" : "Read word aloud")),
          };
        }
        return {
          ...base,
          kindClass: sentenceLike ? "is-kind-sentence" : "is-kind-word",
          main: base.main,
          meta: sentenceLike ? "Sentence meaning" : (type || base.meta || "Vocabulary"),
        };
      };

      const worldTrainingSelectedSlime = () => {
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : {};
        const selectedId = clean(arena.selected_id || arena.selectedId || "");
        const slimes = Array.isArray(arena.slimes) ? arena.slimes : [];
        return selectedId ? (slimes.find((item) => clean(item && item.id) === selectedId) || null) : null;
      };

      const sharedWorldTrainingQuestionIsServerSpeech = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        return kind === "translate_vi_speech" || Boolean(row.server_speech || row.serverSpeech);
      };

      const sharedWorldTrainingQuestionSupportsVietnameseSpeech = (question = {}) => (
        sharedWorldTrainingQuestionIsServerSpeech(question) || sharedWorldTrainingQuestionIsTranslateVi(question)
      );

      const sharedWorldTrainingQuestionIsSpeech = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        return Boolean(row.local_speech || row.localSpeech || kind.startsWith("read_") || kind.startsWith("speak_vi") || clean(row.read_text || row.readText));
      };

      const sharedWorldTrainingQuestionIsTranslateVi = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        return kind === "translate_vi";
      };

      const sharedWorldTrainingQuestionIsAudioInput = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        return kind === "audio_word" || kind === "audio_sentence" || Boolean(clean(row.audio_text || row.audioText));
      };

      const sharedWorldTrainingQuestionIsViPromptSpeech = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        return kind === "speak_vi_word" || kind === "speak_vi_sentence" || Boolean(row.hide_read_text || row.hideReadText);
      };

      const sharedWorldTrainingSpeechInputMode = () => (
        clean(worldTrainingSpeechMode && worldTrainingSpeechMode.value).toLowerCase() === "zipformer"
          ? "zipformer"
          : "browser"
      );

      const sharedWorldTrainingUsesBrowserSpeechInput = (question = {}) => (
        sharedWorldTrainingSpeechInputMode() === "browser"
        && sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)
      );

      const sharedWorldTrainingSpeechText = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        if (sharedWorldTrainingQuestionSupportsVietnameseSpeech(row)) {
          return clean(row.answer_text || row.answerText || row.meaning || row.translation || row.vietnamese || row.answer || "");
        }
        return clean(row.read_text || row.readText || row.answer_text || row.answerText || "");
      };

      const stopSharedWorldTrainingAudio = () => {
        if (sharedWorldTrainingAudioPlayer) {
          try {
            sharedWorldTrainingAudioPlayer.pause();
            sharedWorldTrainingAudioPlayer.currentTime = 0;
          } catch (error) {}
        }
        sharedWorldTrainingAudioPlayer = null;
      };

      const speakSharedWorldTrainingAudioFallback = (text = "") => {
        const value = clean(text);
        if (!value || !("speechSynthesis" in window)) {
          return false;
        }
        try {
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(value);
          utterance.lang = "en-GB";
          utterance.rate = 0.92;
          utterance.pitch = 1;
          window.speechSynthesis.speak(utterance);
          return true;
        } catch (error) {
          return false;
        }
      };

      const playSharedWorldTrainingAudioQuestion = async (question = {}, options = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const text = clean(row.audio_text || row.audioText || row.read_text || row.readText || "");
        if (!text) {
          return false;
        }
        stopSharedWorldTrainingAudio();
        const voice = clean(row.audio_voice || row.audioVoice || row.voice || "sot:en-GB") || "sot:en-GB";
        const url = `/server-data/qm-sound?word=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}`;
        try {
          const playback = await cachedQmSoundPlaybackUrl(url, voice, 0);
          const audio = new Audio(playback.url || url);
          sharedWorldTrainingAudioPlayer = audio;
          audio.preload = "auto";
          const cleanupObjectUrl = () => {
            if (playback.objectUrl) {
              try {
                URL.revokeObjectURL(playback.objectUrl);
              } catch (error) {
              }
            }
          };
          audio.addEventListener("error", () => {
            if (sharedWorldTrainingAudioPlayer === audio) {
              sharedWorldTrainingAudioPlayer = null;
            }
            cleanupObjectUrl();
            speakSharedWorldTrainingAudioFallback(text);
          }, { once: true });
          audio.addEventListener("ended", () => {
            if (sharedWorldTrainingAudioPlayer === audio) {
              sharedWorldTrainingAudioPlayer = null;
            }
            cleanupObjectUrl();
          }, { once: true });
          await audio.play();
          return true;
        } catch (error) {
          sharedWorldTrainingAudioPlayer = null;
          return speakSharedWorldTrainingAudioFallback(text);
        }
      };

      const maybePlaySharedWorldTrainingAudioQuestion = (question = {}, slimeId = "") => {
        if (!sharedWorldTrainingQuestionIsAudioInput(question)) {
          sharedWorldTrainingAudioKey = "";
          return false;
        }
        const row = question && typeof question === "object" ? question : {};
        const key = `${clean(slimeId)}:${clean(row.id || row.question_id || row.questionId || row.audio_text || row.audioText)}`;
        if (!key || key === sharedWorldTrainingAudioKey) {
          return false;
        }
        sharedWorldTrainingAudioKey = key;
        void playSharedWorldTrainingAudioQuestion(row, { auto: true });
        return true;
      };

      const sharedWorldTrainingServerSpeechQuestionKey = (question = {}, slimeId = "") => {
        const row = question && typeof question === "object" ? question : {};
        const id = clean(slimeId || row.slime_id || row.slimeId || "");
        const questionId = clean(row.id || row.question_id || row.questionId || "");
        const sourceText = clean(row.source_text || row.sourceText || row.prompt || "");
        return id && (questionId || sourceText) ? `${id}:${questionId || sourceText}` : "";
      };

      const sharedWorldTrainingServerSpeechStatusNode = () => (
        worldTrainingQuestion && worldTrainingQuestion.querySelector
          ? worldTrainingQuestion.querySelector("[data-training-server-speech-status]")
          : null
      );

      const resetSharedWorldTrainingServerSpeech = (options = {}) => {
        const keepTranscript = Boolean(options && options.keepTranscript);
        if (sharedWorldTrainingServerSpeech.timer) {
          window.clearInterval(sharedWorldTrainingServerSpeech.timer);
        }
        const stream = sharedWorldTrainingServerSpeech.stream;
        if (stream && typeof stream.getTracks === "function") {
          stream.getTracks().forEach((track) => {
            try { track.stop(); } catch (error) {}
          });
        }
        sharedWorldTrainingServerSpeech = {
          active: false,
          recorder: null,
          stream: null,
          chunks: [],
          timer: 0,
          startedAt: 0,
          slimeId: "",
          questionId: "",
          transcript: keepTranscript ? clean(sharedWorldTrainingServerSpeech.transcript || "") : "",
          message: "",
          busy: false,
          cancel: false,
        };
        setSharedWorldTrainingMicEnergy(false);
      };

      const renderSharedWorldTrainingServerSpeechStatus = (question = {}, slimeId = "") => {
        const statusNode = sharedWorldTrainingServerSpeechStatusNode();
        if (!statusNode) {
          return;
        }
        const row = question && typeof question === "object" ? question : {};
        if (sharedWorldTrainingUsesBrowserSpeechInput(row)) {
          const expectedText = sharedWorldTrainingSpeechText(row);
          const transcript = clean(`${sharedWorldTrainingSpeech.transcript || ""} ${sharedWorldTrainingSpeech.chunk || ""}`) || clean(worldTrainingAnswer && worldTrainingAnswer.value);
          const passRatio = sharedWorldTrainingSpeechPassRatio(row, expectedText);
          const result = sharedWorldTrainingSpeechScoreBundle(row, transcript, expectedText, passRatio);
          const review = result.review || sharedWorldTrainingSpeechReview(transcript, expectedText, passRatio);
          const liveRows = review.spokenLines;
          const active = Boolean(sharedWorldTrainingSpeech.active);
          const passPercent = Math.max(1, Math.min(100, Math.round(Number(row.accept_percent ?? row.acceptPercent ?? result.passPercent ?? 60) || 60)));
          statusNode.innerHTML = `
          <span class="ft-world-training-mic-pulse" aria-hidden="true"></span>
          <span class="ft-world-training-countdown">${active ? "Live" : "Mic"}</span>
          <span class="ft-world-training-read-score">${Math.max(0, Number(result.correct || 0))}/${Math.max(0, Number(result.total || 0))} tokens · pass ${passPercent}%</span>
          <span class="ft-world-training-transcript">
            ${
              liveRows.length
                ? liveRows.map((line) => `<b>${sharedWorldTrainingSpeechTokenHtml(line, { empty: "Listening..." })}</b>`).join("")
                : `<b>${sharedWorldTrainingSpeechTokenHtml([], { empty: transcript || "Speak Vietnamese..." })}</b>`
            }
          </span>
        `;
          return;
        }
        const selectedId = clean(slimeId || (worldTrainingSelectedSlime() || {}).id || "");
        const active = Boolean(sharedWorldTrainingServerSpeech.active && selectedId && sharedWorldTrainingServerSpeech.slimeId === selectedId);
        const elapsed = active ? Math.max(0, Math.round((Date.now() - Number(sharedWorldTrainingServerSpeech.startedAt || Date.now())) / 1000)) : 0;
        const passPercent = Math.max(1, Math.min(100, Math.round(Number(row.accept_percent ?? row.acceptPercent ?? 60) || 60)));
        const transcript = clean(sharedWorldTrainingServerSpeech.transcript || (worldTrainingAnswer && worldTrainingAnswer.value) || "");
        const message = clean(sharedWorldTrainingServerSpeech.message)
          || (active ? "Recording Vietnamese... press Ctrl to stop." : "Press Ctrl to record Vietnamese translation.");
        statusNode.innerHTML = `
          <span class="ft-world-training-mic-pulse" aria-hidden="true"></span>
          <span class="ft-world-training-countdown">${active ? `${elapsed}s` : "Ctrl"}</span>
          <span class="ft-world-training-read-score">${escapeHtml(message)} Pass ${passPercent}%.</span>
          <span class="ft-world-training-transcript"><b>${escapeHtml(transcript || "Zipformer transcript will appear here.")}</b></span>
        `;
      };

      const cancelSharedWorldTrainingServerSpeech = () => {
        sharedWorldTrainingServerSpeechCtrlCandidate = "";
        const recorder = sharedWorldTrainingServerSpeech.recorder;
        sharedWorldTrainingServerSpeech.cancel = true;
        if (recorder && recorder.state === "recording") {
          try {
            recorder.stop();
            return true;
          } catch (error) {
          }
        }
        resetSharedWorldTrainingServerSpeech();
        return false;
      };

      const stopSharedWorldTrainingServerSpeech = () => {
        const recorder = sharedWorldTrainingServerSpeech.recorder;
        if (!recorder || recorder.state !== "recording") {
          return false;
        }
        try {
          recorder.stop();
          return true;
        } catch (error) {
          resetSharedWorldTrainingServerSpeech();
          setSharedWorldStatus("Could not stop the Vietnamese recorder.", "error");
          return false;
        }
      };

      const finishSharedWorldTrainingServerSpeech = async (blob, question = {}, slimeId = "") => {
        const id = clean(slimeId);
        if (!blob || !blob.size || !id) {
          setSharedWorldStatus("No Vietnamese audio was captured.", "error");
          setSharedWorldTrainingBusy(false);
          renderSharedWorldTrainingServerSpeechStatus(question, id);
          return;
        }
        setSharedWorldTrainingBusy(true);
        sharedWorldTrainingServerSpeech.busy = true;
        sharedWorldTrainingServerSpeech.message = "Recognizing Vietnamese with local Zipformer...";
        renderSharedWorldTrainingServerSpeechStatus(question, id);
        try {
          const file = await learnerChatVoiceUploadFile(blob);
          const form = new FormData();
          form.append("audio", file, file.name || `qm-city-vi-${Date.now()}.wav`);
          form.append("source", "qm_city_translate_vi_speech");
          form.append("language", "vi");
          const response = await fetchAuthForm("/transcribe-zipformer-vi", form, 60000);
          const payload = response && response.payload ? response.payload : response;
          const transcript = clean(payload && (payload.text || payload.transcript || "")).toLocaleLowerCase("vi-VN");
          sharedWorldTrainingServerSpeech.transcript = transcript;
          if (worldTrainingAnswer) {
            worldTrainingAnswer.value = transcript;
          }
          if (!transcript) {
            sharedWorldTrainingServerSpeech.message = "Zipformer did not hear clear Vietnamese text.";
            setSharedWorldStatus(sharedWorldTrainingServerSpeech.message, "error");
            renderSharedWorldTrainingServerSpeechStatus(question, id);
            return;
          }
          sharedWorldTrainingServerSpeech.message = "Server is scoring the Vietnamese translation...";
          renderSharedWorldTrainingServerSpeechStatus(question, id);
          await postSharedWorldTraining("/world/training/answer", {
            answer: transcript,
            slime_id: id,
            server_speech: true,
            speech_language: "vi",
          }, false);
        } catch (error) {
          const message = error && error.message ? error.message : "Vietnamese speech translation failed.";
          sharedWorldTrainingServerSpeech.message = message;
          setSharedWorldStatus(message, "error");
          renderSharedWorldTrainingServerSpeechStatus(question, id);
        } finally {
          sharedWorldTrainingServerSpeech.busy = false;
          setSharedWorldTrainingBusy(false);
        }
      };

      const startSharedWorldTrainingServerSpeech = async (question = {}, slimeId = "") => {
        const id = clean(slimeId);
        const row = question && typeof question === "object" ? question : {};
        if (!id || !sharedWorldTrainingQuestionSupportsVietnameseSpeech(row)) {
          return false;
        }
        if (!authToken) {
          showLoginGate("Hay dang nhap de dung ghi am QM City.");
          return false;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
          setSharedWorldStatus("This browser cannot record microphone audio here.", "error");
          return false;
        }
        if (sharedWorldTrainingServerSpeech.active) {
          if (sharedWorldTrainingServerSpeech.slimeId === id) {
            return stopSharedWorldTrainingServerSpeech();
          }
          cancelSharedWorldTrainingServerSpeech();
          await new Promise((resolve) => window.setTimeout(resolve, 120));
        }
        if (sharedWorldTrainingSpeech.active) {
          stopSharedWorldTrainingSpeech();
        }
        stopSharedWorldTrainingAudio();
        try {
          if (typeof cancelZipformerViInputDictation === "function") {
            cancelZipformerViInputDictation();
          }
        } catch (error) {
        }
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
          });
          const mimeType = typeof learnerChatRecorderMimeType === "function" ? learnerChatRecorderMimeType() : "";
          const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
          const questionId = clean(row.id || row.question_id || row.questionId || "");
          sharedWorldTrainingServerSpeech = {
            active: true,
            recorder,
            stream,
            chunks: [],
            timer: 0,
            startedAt: Date.now(),
            slimeId: id,
            questionId,
            transcript: "",
            message: "Recording Vietnamese... press Ctrl to stop.",
            busy: false,
            cancel: false,
          };
          recorder.addEventListener("dataavailable", (event) => {
            if (event.data && event.data.size) {
              sharedWorldTrainingServerSpeech.chunks.push(event.data);
            }
          });
          recorder.addEventListener("stop", () => {
            const canceled = Boolean(sharedWorldTrainingServerSpeech.cancel);
            const chunks = sharedWorldTrainingServerSpeech.chunks.slice();
            const activeQuestion = { ...row };
            const activeSlimeId = id;
            const type = recorder.mimeType || mimeType || "audio/webm";
            const blob = new Blob(chunks, { type });
            resetSharedWorldTrainingServerSpeech({ keepTranscript: true });
            if (!canceled) {
              void finishSharedWorldTrainingServerSpeech(blob, activeQuestion, activeSlimeId);
            } else {
              renderSharedWorldTrainingServerSpeechStatus(activeQuestion, activeSlimeId);
            }
          });
          recorder.start();
          setSharedWorldTrainingMicEnergy(true);
          sharedWorldTrainingServerSpeech.timer = window.setInterval(() => {
            renderSharedWorldTrainingServerSpeechStatus(row, id);
          }, 500);
          setSharedWorldStatus("QM City Vietnamese recorder is live. Press Ctrl again to score.", "ok");
          renderSharedWorldTrainingServerSpeechStatus(row, id);
          return true;
        } catch (error) {
          resetSharedWorldTrainingServerSpeech();
          setSharedWorldStatus(error && error.message ? error.message : "Could not open the microphone.", "error");
          renderSharedWorldTrainingServerSpeechStatus(row, id);
          return false;
        }
      };

      const toggleSharedWorldTrainingServerSpeech = async () => {
        const selected = worldTrainingSelectedSlime();
        const question = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        const slimeId = clean(selected && selected.id || "");
        if (!selected || !sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)) {
          return false;
        }
        if (sharedWorldTrainingServerSpeech.active && sharedWorldTrainingServerSpeech.slimeId === slimeId) {
          return stopSharedWorldTrainingServerSpeech();
        }
        setSharedWorldTrainingQuestionOpen(true);
        return startSharedWorldTrainingServerSpeech(question, slimeId);
      };

      const sharedWorldTrainingServerSpeechCtrlKey = () => {
        if (!sharedWorldTrainingIsActive()) {
          return "";
        }
        const questionOpen = Boolean(worldTrainingModal && worldTrainingModal.classList.contains("is-question-open"));
        const selected = worldTrainingSelectedSlime();
        const question = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        const alive = Boolean(selected && Math.max(0, Math.floor(Number(selected.hp || 0) || 0)) > 0);
        return questionOpen && alive && sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)
          ? sharedWorldTrainingServerSpeechQuestionKey(question, selected.id)
          : "";
      };

      const handleSharedWorldTrainingServerSpeechCtrlKeyDown = (event) => {
        if (!event) return;
        if (sharedWorldTrainingSpeechInputMode() === "browser") {
          sharedWorldTrainingServerSpeechCtrlCandidate = "";
          return;
        }
        if (event.key === "Control" && !event.repeat && !event.altKey && !event.shiftKey && !event.metaKey) {
          sharedWorldTrainingServerSpeechCtrlCandidate = sharedWorldTrainingServerSpeechCtrlKey();
          return;
        }
        if (event.ctrlKey && sharedWorldTrainingServerSpeechCtrlCandidate) {
          sharedWorldTrainingServerSpeechCtrlCandidate = "";
        }
      };

      const handleSharedWorldTrainingServerSpeechCtrlKeyUp = (event) => {
        if (!event || event.key !== "Control") return;
        if (sharedWorldTrainingSpeechInputMode() === "browser") {
          sharedWorldTrainingServerSpeechCtrlCandidate = "";
          return;
        }
        const candidate = sharedWorldTrainingServerSpeechCtrlCandidate;
        sharedWorldTrainingServerSpeechCtrlCandidate = "";
        if (!candidate || candidate !== sharedWorldTrainingServerSpeechCtrlKey()) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        void toggleSharedWorldTrainingServerSpeech();
      };

      const sharedWorldTrainingSpeechQuestionKey = (question = {}, slimeId = "") => {
        const row = question && typeof question === "object" ? question : {};
        const id = clean(slimeId || row.slime_id || row.slimeId || "");
        const questionId = clean(row.id || row.question_id || row.questionId || "");
        const expectedText = sharedWorldTrainingSpeechText(row);
        return id && (questionId || expectedText) ? `${id}:${questionId || expectedText}` : "";
      };

      const sharedWorldTrainingSpeechHistoryLines = (text = "") => {
        const words = clean(text).split(/\s+/).filter(Boolean);
        if (!words.length) {
          return [];
        }
        const maxWordsPerLine = 7;
        const lines = [];
        for (let end = words.length; end > 0 && lines.length < 3; end -= maxWordsPerLine) {
          const start = Math.max(0, end - maxWordsPerLine);
          lines.unshift(words.slice(start, end).join(" "));
        }
        return lines;
      };

      const sharedWorldTrainingNormalizeSpeechToken = (value = "") => clean(value)
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[\u0111\u0110]/g, "d")
        .toLowerCase()
        .replace(/['\u2019]/g, "")
        .replace(/[^a-z0-9]+/g, "");

      const sharedWorldTrainingSpeechExpectedWords = (text = "") => Array.from(clean(text).matchAll(/[\p{L}\p{N}]+(?:['\u2019][\p{L}\p{N}]+)?/gu))
        .map((match) => ({ text: match[0], norm: sharedWorldTrainingNormalizeSpeechToken(match[0]) }))
        .filter((item) => item.norm);

      const sharedWorldTrainingSpeechPassRatio = (question = {}, expectedText = "") => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        const typeText = clean(row.type || "").toLowerCase();
        const tokenCount = sharedWorldTrainingSpeechExpectedWords(expectedText).length;
        const configuredPercent = Number(row.accept_percent ?? row.acceptPercent ?? 0);
        if (Number.isFinite(configuredPercent) && configuredPercent > 0) {
          return Math.max(0.05, Math.min(1, configuredPercent / 100));
        }
        const sentenceLike = kind === "read_sentence" || typeText.includes("sentence") || tokenCount >= 8;
        return sentenceLike ? 0.7 : 1;
      };

      const sharedWorldTrainingSpeechIsSingleWord = (question = {}, expectedText = "") => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        const typeText = clean(row.type || "").toLowerCase();
        const tokenCount = sharedWorldTrainingSpeechExpectedWords(expectedText).length;
        if (kind === "read_word" || kind === "speak_vi_word") {
          return true;
        }
        if (kind === "read_sentence" || kind === "speak_vi_sentence" || typeText.includes("sentence")) {
          return false;
        }
        return tokenCount <= 1;
      };

      const scoreSharedWorldTrainingSpeech = (transcript = "", expectedText = "", passRatio = 1) => {
        const expected = sharedWorldTrainingSpeechExpectedWords(expectedText);
        const spoken = sharedWorldTrainingSpeechExpectedWords(transcript);
        const ratio = Math.max(0.05, Math.min(1, Number(passRatio) || 1));
        let correct = 0;
        if (ratio < 1) {
          const spokenCounts = new Map();
          spoken.forEach((word) => {
            spokenCounts.set(word.norm, (spokenCounts.get(word.norm) || 0) + 1);
          });
          expected.forEach((word) => {
            const count = spokenCounts.get(word.norm) || 0;
            if (count > 0) {
              correct += 1;
              spokenCounts.set(word.norm, count - 1);
            }
          });
        } else {
          let cursor = 0;
          expected.forEach((word) => {
            while (cursor < spoken.length && spoken[cursor].norm !== word.norm) {
              cursor += 1;
            }
            if (cursor < spoken.length && spoken[cursor].norm === word.norm) {
              correct += 1;
              cursor += 1;
            }
          });
        }
        const requiredCorrect = expected.length ? Math.max(1, Math.ceil(expected.length * ratio)) : 0;
        const score = expected.length ? Math.round((correct / expected.length) * 100) : 0;
        return {
          correct,
          total: expected.length,
          requiredCorrect,
          passPercent: Math.round(ratio * 100),
          passed: Boolean(expected.length) && correct >= requiredCorrect,
          score,
        };
      };

      const sharedWorldTrainingSpeechReview = (transcript = "", expectedText = "", passRatio = 1) => {
        const expected = sharedWorldTrainingSpeechExpectedWords(expectedText);
        const spoken = sharedWorldTrainingSpeechExpectedWords(transcript);
        const expectedRows = expected.map((word) => ({ text: word.text, norm: word.norm, status: "missing" }));
        const spokenRows = [];
        const ratio = Math.max(0.05, Math.min(1, Number(passRatio) || 1));
        if (ratio < 1) {
          const spokenCounts = new Map();
          spoken.forEach((word) => {
            spokenCounts.set(word.norm, (spokenCounts.get(word.norm) || 0) + 1);
          });
          expectedRows.forEach((row) => {
            const count = spokenCounts.get(row.norm) || 0;
            if (count > 0) {
              row.status = "correct";
              spokenCounts.set(row.norm, count - 1);
            }
          });
          const expectedCounts = new Map();
          expected.forEach((word) => {
            expectedCounts.set(word.norm, (expectedCounts.get(word.norm) || 0) + 1);
          });
          spoken.forEach((word) => {
            const count = expectedCounts.get(word.norm) || 0;
            if (count > 0) {
              spokenRows.push({ text: word.text, status: "correct" });
              expectedCounts.set(word.norm, count - 1);
            } else {
              spokenRows.push({ text: word.text, status: "wrong" });
            }
          });
        } else {
          let expectedCursor = 0;
          spoken.forEach((word) => {
            let matchedIndex = -1;
            for (let index = expectedCursor; index < expected.length; index += 1) {
              if (expected[index].norm === word.norm) {
                matchedIndex = index;
                break;
              }
            }
            if (matchedIndex >= 0) {
              expectedRows[matchedIndex].status = "correct";
              expectedCursor = matchedIndex + 1;
              spokenRows.push({ text: word.text, status: "correct" });
            } else {
              spokenRows.push({ text: word.text, status: "wrong" });
            }
          });
        }
        const spokenLines = [];
        const maxTokensPerLine = 7;
        for (let end = spokenRows.length; end > 0 && spokenLines.length < 3; end -= maxTokensPerLine) {
          const start = Math.max(0, end - maxTokensPerLine);
          spokenLines.unshift(spokenRows.slice(start, end));
        }
        return { expected: expectedRows, spokenLines };
      };

      const sharedWorldTrainingQuestionUsesVietnameseSpeechScoring = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || "").toLowerCase();
        return kind === "translate_vi" || kind === "translate_vi_speech" || Boolean(row.server_speech || row.serverSpeech);
      };

      const scoreSharedWorldTrainingVietnameseSpeech = (transcript = "", expectedText = "", passRatio = 0.6) => {
        const expected = sharedWorldTrainingSpeechExpectedWords(expectedText);
        const spoken = sharedWorldTrainingSpeechExpectedWords(transcript);
        const ratio = Math.max(0.05, Math.min(1, Number(passRatio) || 0.6));
        if (!expected.length || !spoken.length) {
          return {
            correct: 0,
            total: expected.length,
            requiredCorrect: expected.length ? Math.max(1, Math.ceil(expected.length * ratio)) : 0,
            passPercent: Math.round(ratio * 100),
            passed: false,
            score: 0,
            coverage: 0,
            precision: 0,
            exact: false,
          };
        }
        const spokenCounts = new Map();
        spoken.forEach((word) => {
          spokenCounts.set(word.norm, (spokenCounts.get(word.norm) || 0) + 1);
        });
        let matched = 0;
        expected.forEach((word) => {
          const count = spokenCounts.get(word.norm) || 0;
          if (count > 0) {
            matched += 1;
            spokenCounts.set(word.norm, count - 1);
          }
        });
        const coverage = matched / Math.max(1, expected.length);
        const precision = matched / Math.max(1, spoken.length);
        const expectedCounts = new Map();
        const spokenExactCounts = new Map();
        expected.forEach((word) => expectedCounts.set(word.norm, (expectedCounts.get(word.norm) || 0) + 1));
        spoken.forEach((word) => spokenExactCounts.set(word.norm, (spokenExactCounts.get(word.norm) || 0) + 1));
        const exact = expected.length === spoken.length
          && expected.length === matched
          && expected.every((word) => expectedCounts.get(word.norm) === spokenExactCounts.get(word.norm));
        return {
          correct: matched,
          total: expected.length,
          requiredCorrect: expected.length ? Math.max(1, Math.ceil(expected.length * ratio)) : 0,
          passPercent: Math.round(ratio * 100),
          passed: coverage >= ratio && precision >= 0.45,
          score: Math.round(Math.min(coverage, precision) * 100),
          coverage,
          precision,
          exact,
        };
      };

      const sharedWorldTrainingVietnameseSpeechReview = (transcript = "", expectedText = "") => {
        const expected = sharedWorldTrainingSpeechExpectedWords(expectedText);
        const spoken = sharedWorldTrainingSpeechExpectedWords(transcript);
        const expectedRows = expected.map((word) => ({ text: word.text, norm: word.norm, status: "missing" }));
        const spokenRows = [];
        const spokenCounts = new Map();
        spoken.forEach((word) => {
          spokenCounts.set(word.norm, (spokenCounts.get(word.norm) || 0) + 1);
        });
        expectedRows.forEach((row) => {
          const count = spokenCounts.get(row.norm) || 0;
          if (count > 0) {
            row.status = "correct";
            spokenCounts.set(row.norm, count - 1);
          }
        });
        const expectedCounts = new Map();
        expected.forEach((word) => {
          expectedCounts.set(word.norm, (expectedCounts.get(word.norm) || 0) + 1);
        });
        spoken.forEach((word) => {
          const count = expectedCounts.get(word.norm) || 0;
          if (count > 0) {
            spokenRows.push({ text: word.text, status: "correct" });
            expectedCounts.set(word.norm, count - 1);
          } else {
            spokenRows.push({ text: word.text, status: "wrong" });
          }
        });
        const spokenLines = [];
        const maxTokensPerLine = 7;
        for (let end = spokenRows.length; end > 0 && spokenLines.length < 3; end -= maxTokensPerLine) {
          const start = Math.max(0, end - maxTokensPerLine);
          spokenLines.unshift(spokenRows.slice(start, end));
        }
        return { expected: expectedRows, spokenLines };
      };

      const sharedWorldTrainingSpeechScoreBundle = (question = {}, transcript = "", expectedText = "", passRatio = 1) => {
        if (sharedWorldTrainingQuestionUsesVietnameseSpeechScoring(question)) {
          const score = scoreSharedWorldTrainingVietnameseSpeech(transcript, expectedText, passRatio);
          return {
            ...score,
            language: "vi",
            review: sharedWorldTrainingVietnameseSpeechReview(transcript, expectedText),
          };
        }
        const score = scoreSharedWorldTrainingSpeech(transcript, expectedText, passRatio);
        return {
          ...score,
          language: "en",
          review: sharedWorldTrainingSpeechReview(transcript, expectedText, passRatio),
        };
      };

      const sharedWorldTrainingSpeechTokenHtml = (tokens = [], options = {}) => {
        const rows = Array.isArray(tokens) ? tokens : [];
        if (!rows.length) {
          return clean(options && options.empty) ? `<span class="ft-world-training-token is-waiting">${escapeHtml(clean(options.empty))}</span>` : "";
        }
        const mask = Boolean(options && options.mask);
        return rows.map((token) => {
          const row = token && typeof token === "object" ? token : { text: token, status: "" };
          const status = clean(row.status || "").toLowerCase();
          const className = status === "correct" ? "is-correct" : status === "wrong" ? "is-wrong" : "is-missing";
          const label = mask ? "•••" : escapeHtml(clean(row.text || ""));
          return `<span class="ft-world-training-token ${className}${mask ? " is-masked" : ""}">${label}</span>`;
        }).join("");
      };

      const sharedWorldTrainingAnswerTokenParts = (text = "") => {
        const source = clean(text);
        const tokenPattern = /[\p{L}\p{N}]+(?:['\u2019][\p{L}\p{N}]+)?/gu;
        return Array.from(source.matchAll(tokenPattern)).map((match) => {
          const raw = clean(match[0]);
          const norm = raw
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[\u0111\u0110]/g, "d")
            .toLowerCase()
            .replace(/['\u2019]/g, "")
            .replace(/[^a-z0-9]+/g, "");
          return { text: raw, norm, index: match.index || 0, end: (match.index || 0) + match[0].length };
        }).filter((item) => item.norm);
      };

      const sharedWorldTrainingAnswerTokenHtml = (answer = "", expected = "") => {
        const source = clean(answer);
        if (!source) {
          return escapeHtml("No typed answer");
        }
        const expectedCounts = new Map();
        sharedWorldTrainingAnswerTokenParts(expected).forEach((part) => {
          expectedCounts.set(part.norm, (expectedCounts.get(part.norm) || 0) + 1);
        });
        if (!expectedCounts.size) {
          return escapeHtml(source);
        }
        let cursor = 0;
        const chunks = [];
        sharedWorldTrainingAnswerTokenParts(source).forEach((part) => {
          if (part.index > cursor) {
            chunks.push(escapeHtml(source.slice(cursor, part.index)));
          }
          const remaining = expectedCounts.get(part.norm) || 0;
          const status = remaining > 0 ? "is-correct" : "is-wrong";
          if (remaining > 0) {
            expectedCounts.set(part.norm, remaining - 1);
          }
          chunks.push(`<span class="ft-world-training-token ${status}">${escapeHtml(part.text)}</span>`);
          cursor = part.end;
        });
        if (cursor < source.length) {
          chunks.push(escapeHtml(source.slice(cursor)));
        }
        return `<span class="ft-world-training-answer-tokens">${chunks.join("")}</span>`;
      };

      const setSharedWorldTrainingMicEnergy = (active = false) => {
        const username = clean(activeWorldUsername() || currentAuthUsername || "learner").toLowerCase();
        const node = sharedWorldNodes.get(username) || (() => {
          try {
            return (ensureSharedWorldSelfNode() || {}).node || null;
          } catch (error) {
            return null;
          }
        })();
        if (!node) {
          return;
        }
        node.classList.toggle("is-training-mic-live", Boolean(active));
        node.classList.toggle("is-chatting", Boolean(active));
      };

      const sharedWorldTrainingSelfNode = () => {
        const username = clean(activeWorldUsername() || currentAuthUsername || "learner").toLowerCase();
        const node = sharedWorldNodes.get(username);
        if (node) {
          return node;
        }
        try {
          return (ensureSharedWorldSelfNode() || {}).node || null;
        } catch (error) {
          return null;
        }
      };

      const sharedWorldTrainingSpeechLayer = () => {
        if (!worldCard) {
          return null;
        }
        let layer = worldCard.querySelector("#ft-world-training-speech-layer");
        if (!layer) {
          layer = document.createElement("div");
          layer.id = "ft-world-training-speech-layer";
          layer.className = "ft-world-training-speech-layer";
          layer.setAttribute("aria-hidden", "true");
          worldCard.appendChild(layer);
        }
        return layer;
      };

      const sharedWorldTrainingSpeechAnchorPoint = (node = null, layer = null) => {
        if (!node || !layer || !node.getBoundingClientRect || !layer.getBoundingClientRect) {
          return null;
        }
        const anchor = node.querySelector && (node.querySelector(".ft-world-fireball") || node);
        const layerRect = layer.getBoundingClientRect();
        const rect = (anchor || node).getBoundingClientRect();
        const x = Math.max(12, Math.min(Math.max(12, layerRect.width - 12), rect.left + rect.width * 0.5 - layerRect.left));
        const y = Math.max(24, Math.min(Math.max(24, layerRect.height - 12), rect.top - layerRect.top));
        return { x, y };
      };

      const positionSharedWorldTrainingSpeechBubble = (bubble = null, node = null, layer = null) => {
        const point = sharedWorldTrainingSpeechAnchorPoint(node, layer);
        if (!bubble || !point) {
          return false;
        }
        const { x, y } = point;
        bubble.style.setProperty("--speech-x", `${Math.round(x)}px`);
        bubble.style.setProperty("--speech-y", `${Math.round(y)}px`);
        return true;
      };

      const sharedWorldTrainingSpeechFlatTokenRows = (transcript = "", expectedText = "") => {
        const spoken = sharedWorldTrainingSpeechExpectedWords(transcript);
        const expected = sharedWorldTrainingSpeechExpectedWords(expectedText);
        const expectedCounts = new Map();
        expected.forEach((word) => {
          expectedCounts.set(word.norm, (expectedCounts.get(word.norm) || 0) + 1);
        });
        return spoken.map((word) => {
          const count = expectedCounts.get(word.norm) || 0;
          if (count > 0) {
            expectedCounts.set(word.norm, count - 1);
            return { text: word.text, norm: word.norm, status: "correct" };
          }
          return { text: word.text, norm: word.norm, status: "wrong" };
        });
      };

      const spawnSharedWorldTrainingSpeechTokenBlock = (token = {}, index = 0) => {
        const layer = sharedWorldTrainingSpeechLayer();
        const node = sharedWorldTrainingSelfNode();
        const point = sharedWorldTrainingSpeechAnchorPoint(node, layer);
        const text = clean(token && token.text || "");
        if (!layer || !point || !text) {
          return false;
        }
        const status = clean(token.status || "").toLowerCase() === "correct" ? "correct" : "wrong";
        const block = document.createElement("span");
        block.className = `ft-world-training-speech-token-flight is-${status}`;
        block.textContent = text.length > 18 ? `${text.slice(0, 16)}...` : text;
        const drift = ((index % 5) - 2) * 12;
        block.style.setProperty("--token-x", `${Math.round(point.x)}px`);
        block.style.setProperty("--token-y", `${Math.round(point.y - 8)}px`);
        block.style.setProperty("--token-drift-small", `${Math.round(drift * 0.18)}px`);
        block.style.setProperty("--token-drift-mid", `${Math.round(drift * 0.78)}px`);
        block.style.setProperty("--token-drift", `${drift}px`);
        layer.appendChild(block);
        window.setTimeout(() => block.remove(), 1350);
        return true;
      };

      const renderSharedWorldTrainingSpeechTokenFlights = (transcript = "", expectedText = "") => {
        if (!(typeof sharedWorldTrainingIsActive === "function" && sharedWorldTrainingIsActive())) {
          return false;
        }
        const rows = sharedWorldTrainingSpeechFlatTokenRows(transcript, expectedText);
        const previousCount = Math.max(0, Math.floor(Number(sharedWorldTrainingSpeech.flightTokenCount || 0) || 0));
        if (rows.length < previousCount) {
          sharedWorldTrainingSpeech.flightTokenCount = rows.length;
          return false;
        }
        rows.slice(previousCount).forEach((row, offset) => {
          spawnSharedWorldTrainingSpeechTokenBlock(row, previousCount + offset);
        });
        sharedWorldTrainingSpeech.flightTokenCount = rows.length;
        return rows.length > previousCount;
      };

      const clearSharedWorldTrainingSpeechOverhead = () => {
        const node = sharedWorldTrainingSelfNode();
        const bubble = node && node.querySelector ? node.querySelector(".ft-world-training-speech-live") : null;
        if (bubble) {
          bubble.remove();
        }
        const layer = worldCard && worldCard.querySelector ? worldCard.querySelector("#ft-world-training-speech-layer") : null;
        const layerBubble = layer && layer.querySelector ? layer.querySelector(".ft-world-training-speech-live") : null;
        if (layerBubble) {
          layerBubble.remove();
        }
        if (layer && layer.querySelectorAll) {
          layer.querySelectorAll(".ft-world-training-speech-token-flight").forEach((item) => item.remove());
        }
      };

      const renderSharedWorldTrainingSpeechOverhead = (text = "", result = null) => {
        const node = sharedWorldTrainingSelfNode();
        const value = clean(text);
        if (!node) {
          return;
        }
        const expectedText = clean(sharedWorldTrainingSpeech.expectedText || "");
        if (!value && !sharedWorldTrainingSpeech.active && !expectedText) {
            clearSharedWorldTrainingSpeechOverhead();
          return;
        }
        const useMapLayer = typeof sharedWorldTrainingIsActive === "function" && sharedWorldTrainingIsActive() && worldCard;
        const layer = useMapLayer ? sharedWorldTrainingSpeechLayer() : null;
        const host = layer || node;
        const staleBubble = layer
          ? (node.querySelector ? node.querySelector(".ft-world-training-speech-live") : null)
          : (worldCard && worldCard.querySelector ? worldCard.querySelector("#ft-world-training-speech-layer .ft-world-training-speech-live") : null);
        if (staleBubble) {
          staleBubble.remove();
        }
        let bubble = host.querySelector(".ft-world-training-speech-live");
        if (!bubble) {
          bubble = document.createElement("div");
          bubble.className = "ft-world-training-speech-live";
          bubble.setAttribute("aria-hidden", "true");
          host.appendChild(bubble);
        }
        bubble.classList.toggle("is-map-overhead", Boolean(layer));
        if (layer) {
          positionSharedWorldTrainingSpeechBubble(bubble, node, layer);
        } else {
          bubble.style.removeProperty("--speech-x");
          bubble.style.removeProperty("--speech-y");
        }
        const review = result && result.review
          ? result.review
          : sharedWorldTrainingSpeechReview(value, expectedText, sharedWorldTrainingSpeech.passRatio || 1);
        const shownLines = review.spokenLines.length ? review.spokenLines : [[{ text: "Listening...", status: "missing" }]];
        const correct = Math.max(0, Math.floor(Number(result && result.correct || 0) || 0));
        const total = Math.max(0, Math.floor(Number(result && result.total || 0) || 0));
        const targetRows = sharedWorldTrainingSpeech.hideTarget
          ? review.expected.map((token) => clean(token && token.status).toLowerCase() === "correct" ? token : { ...token, text: "..." })
          : review.expected;
        const key = `${targetRows.map((token) => `${token.text}:${token.status}`).join("|")}|${shownLines.map((line) => line.map((token) => `${token.text}:${token.status}`).join(" ")).join("|")}|${correct}/${total}|${sharedWorldTrainingSpeech.active ? "live" : "hold"}|${sharedWorldTrainingSpeech.hideTarget ? "masked" : "open"}`;
        if (bubble.dataset.liveKey !== key) {
          bubble.dataset.liveKey = key;
          bubble.innerHTML = `
            <b><i aria-hidden="true"></i>Speech combat log</b>
            <div class="ft-world-training-speech-target">
              <small>Target</small>
              <div>${sharedWorldTrainingSpeechTokenHtml(targetRows, { empty: expectedText || "Waiting for target..." })}</div>
            </div>
            <div class="ft-world-training-speech-lines">
              ${shownLines.map((line, index) => {
                const age = Math.max(0, shownLines.length - 1 - index);
                const opacity = Math.max(0.48, 1 - age * 0.22).toFixed(2);
                const border = Math.max(0.18, 0.38 - age * 0.08).toFixed(2);
                const hot = Math.max(0.06, 0.16 - age * 0.04).toFixed(2);
                const cyan = Math.max(0.04, 0.12 - age * 0.03).toFixed(2);
                const glow = Math.max(0.06, 0.18 - age * 0.04).toFixed(2);
                return `
                <span class="${index === shownLines.length - 1 ? "is-live" : ""}" style="--line-age:${age};--line-opacity:${opacity};--line-border:${border};--line-hot:${hot};--line-cyan:${cyan};--line-glow:${glow}">
                  <em>${String(index + 1).padStart(2, "0")}</em>
                  <strong>${sharedWorldTrainingSpeechTokenHtml(line, { empty: "Listening..." })}</strong>
                </span>
              `; }).join("")}
            </div>
            ${total ? `<small>${correct}/${total} tokens · pass ${Math.max(1, Number(result && result.requiredCorrect || total))}/${total} (${Math.max(1, Number(result && result.passPercent || 100))}%)</small>` : ""}
          `;
        }
      };

      const stopSharedWorldTrainingSpeech = (options = {}) => {
        const shouldClearOverhead = !(options && options.clearOverhead === false);
        window.clearInterval(sharedWorldTrainingSpeech.timer);
        window.clearTimeout(sharedWorldTrainingSpeech.settleTimer);
        sharedWorldTrainingSpeech.timer = 0;
        sharedWorldTrainingSpeech.settleTimer = 0;
        const recognition = sharedWorldTrainingSpeech.recognition;
        sharedWorldTrainingSpeech.recognition = null;
        sharedWorldTrainingSpeech.active = false;
        sharedWorldTrainingSpeech.passed = false;
        setSharedWorldTrainingMicEnergy(false);
        if (shouldClearOverhead) {
          clearSharedWorldTrainingSpeechOverhead();
        }
        if (recognition) {
          try {
            recognition.onresult = null;
            recognition.onerror = null;
            recognition.onend = null;
            recognition.stop();
          } catch (error) {
            try { recognition.abort(); } catch (innerError) {}
          }
        }
      };

      const renderSharedWorldTrainingSpeechStatus = (question = {}, slimeId = "") => {
        const expectedText = sharedWorldTrainingSpeechText(question);
        const selectedForKey = clean(slimeId || sharedWorldTrainingSpeech.slimeId || (worldTrainingSelectedSlime() || {}).id || "");
        const questionKey = sharedWorldTrainingSpeechQuestionKey(question, selectedForKey);
        const questionId = clean(question && (question.id || question.question_id || question.questionId) || "");
        if (!sharedWorldTrainingSpeech.active && questionKey && sharedWorldTrainingSpeech.historyKey !== questionKey) {
          sharedWorldTrainingSpeech.transcript = "";
          sharedWorldTrainingSpeech.chunk = "";
        }
        if (!sharedWorldTrainingSpeech.active || !sharedWorldTrainingSpeech.expectedText || sharedWorldTrainingSpeech.historyKey !== questionKey) {
          sharedWorldTrainingSpeech.expectedText = expectedText;
          sharedWorldTrainingSpeech.questionId = questionId;
          sharedWorldTrainingSpeech.slimeId = selectedForKey;
          sharedWorldTrainingSpeech.historyKey = questionKey;
          sharedWorldTrainingSpeech.hideTarget = sharedWorldTrainingQuestionIsViPromptSpeech(question);
        }
        const liveText = clean(`${sharedWorldTrainingSpeech.transcript || ""} ${sharedWorldTrainingSpeech.chunk || ""}`);
        const passRatio = sharedWorldTrainingSpeechPassRatio(question, expectedText);
        sharedWorldTrainingSpeech.passRatio = passRatio;
        const result = scoreSharedWorldTrainingSpeech(liveText, expectedText, passRatio);
        renderSharedWorldTrainingSpeechOverhead(liveText, result);
        const statusNode = worldTrainingQuestion ? worldTrainingQuestion.querySelector("[data-training-read-status]") : null;
        if (!statusNode) {
          return;
        }
        const configuredLimit = Math.max(3, Math.floor(Number(question.time_limit_seconds || question.timeLimitSeconds || 10) || 10));
        const left = sharedWorldTrainingSpeech.active
          ? Math.max(0, Math.ceil((sharedWorldTrainingSpeech.deadline - Date.now()) / 1000))
          : configuredLimit;
        const transcript = clean(liveText);
        const expectedTokens = sharedWorldTrainingSpeechExpectedWords(expectedText);
        const liveRows = sharedWorldTrainingSpeechReview(transcript, expectedText, passRatio).spokenLines;
        statusNode.innerHTML = `
          <span class="ft-world-training-mic-pulse" aria-hidden="true"></span>
          <span class="ft-world-training-countdown">${left}s</span>
          <span>${result.correct}/${result.total} tokens · pass ${result.passPercent}%</span>
          <span class="ft-world-training-transcript">${escapeHtml(transcript || "Listening...")}</span>
        `;
        statusNode.innerHTML = `
          <span class="ft-world-training-mic-pulse" aria-hidden="true"></span>
          <span class="ft-world-training-countdown">${left}s</span>
          <span class="ft-world-training-read-score">${result.correct}/${result.total || expectedTokens.length} tokens · pass ${result.passPercent}%</span>
          <span class="ft-world-training-transcript">
            ${
              liveRows.length
                ? liveRows.map((line) => `<b>${sharedWorldTrainingSpeechTokenHtml(line, { empty: "Listening..." })}</b>`).join("")
                : `<b>${sharedWorldTrainingSpeechTokenHtml([], { empty: transcript || "Listening..." })}</b>`
            }
          </span>
        `;
      };

      const armSharedWorldTrainingSpeechSettle = (reason = "matched") => {
        if (!sharedWorldTrainingSpeech.active || sharedWorldTrainingSpeech.posted) {
          return;
        }
        sharedWorldTrainingSpeech.passed = true;
        window.clearTimeout(sharedWorldTrainingSpeech.settleTimer);
        const settleDelay = Math.max(250, Math.floor(Number(sharedWorldTrainingSpeech.settleDelayMs || 1450) || 1450));
        sharedWorldTrainingSpeech.settleTimer = window.setTimeout(() => {
          if (!sharedWorldTrainingSpeech.active || sharedWorldTrainingSpeech.posted) {
            return;
          }
          const transcript = clean(`${sharedWorldTrainingSpeech.transcript || ""} ${sharedWorldTrainingSpeech.chunk || ""}`);
          const expectedText = clean(sharedWorldTrainingSpeech.expectedText || "");
          const score = scoreSharedWorldTrainingSpeech(transcript, expectedText, sharedWorldTrainingSpeech.passRatio || 1);
          finishSharedWorldTrainingSpeech(Boolean(score.passed), score.passed ? reason : "settled");
        }, settleDelay);
      };

      const finishSharedWorldTrainingSpeech = (passed = false, reason = "") => {
        if (!sharedWorldTrainingSpeech.active || sharedWorldTrainingSpeech.posted) {
          return;
        }
        window.clearTimeout(sharedWorldTrainingSpeech.settleTimer);
        sharedWorldTrainingSpeech.settleTimer = 0;
        const slimeId = clean(sharedWorldTrainingSpeech.slimeId);
        const transcript = clean(`${sharedWorldTrainingSpeech.transcript || ""} ${sharedWorldTrainingSpeech.chunk || ""}`);
        const expectedText = clean(sharedWorldTrainingSpeech.expectedText || "");
        const score = scoreSharedWorldTrainingSpeech(transcript, expectedText, sharedWorldTrainingSpeech.passRatio || 1);
        sharedWorldTrainingSpeech.posted = true;
        stopSharedWorldTrainingSpeech({ clearOverhead: false });
        void postSharedWorldTraining("/world/training/answer", {
          answer: transcript,
          slime_id: slimeId,
          local_speech_passed: Boolean(passed),
          local_speech_percent: Math.max(0, Math.min(100, Number(score && score.score || 0) || 0)),
          local_speech_correct: Math.max(0, Number(score && score.correct || 0) || 0),
          local_speech_total: Math.max(0, Number(score && score.total || 0) || 0),
          local_speech_reason: clean(reason),
          local_speech_expected: expectedText,
        }, false);
      };

      const startSharedWorldTrainingSpeech = (question = {}, slimeId = "") => {
        const expectedText = sharedWorldTrainingSpeechText(question);
        const id = clean(slimeId);
        const questionId = clean(question && question.id || "");
        if (!id || !expectedText) {
          return false;
        }
        if (sharedWorldTrainingSpeech.active) {
          return true;
        }
        const passRatio = sharedWorldTrainingSpeechPassRatio(question, expectedText);
        const singleWord = sharedWorldTrainingSpeechIsSingleWord(question, expectedText);
        const RecognitionCtor = browserSpeechRecognitionCtor();
        if (!RecognitionCtor) {
          setSharedWorldStatus("Browser live speech recognition is unavailable here. Type practice still works.", "error");
          return false;
        }
        sharedWorldTrainingSpeech = {
          active: true,
          recognition: null,
          timer: 0,
          settleTimer: 0,
          deadline: Date.now() + Math.max(3, Math.floor(Number(question.time_limit_seconds || question.timeLimitSeconds || 10) || 10)) * 1000,
          slimeId: id,
          questionId,
          expectedText,
          passRatio,
          singleWord,
          settleDelayMs: singleWord ? 1000 : 1450,
          transcript: "",
          chunk: "",
          historyKey: "",
          hideTarget: sharedWorldTrainingQuestionIsViPromptSpeech(question),
          scoringLanguage: "en",
          posted: false,
          passed: false,
        };
        const recognition = new RecognitionCtor();
        sharedWorldTrainingSpeech.recognition = recognition;
        recognition.lang = "en-US";
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.onresult = (event) => {
          let finalText = "";
          let interim = "";
          for (let index = event.resultIndex; index < event.results.length; index += 1) {
            const result = event.results[index];
            const text = clean(result && result[0] && result[0].transcript || "");
            if (!text) continue;
            if (result.isFinal) finalText = clean(`${finalText} ${text}`);
            else interim = clean(`${interim} ${text}`);
          }
          if (finalText) {
            sharedWorldTrainingSpeech.transcript = clean(`${sharedWorldTrainingSpeech.transcript} ${finalText}`);
          }
          sharedWorldTrainingSpeech.chunk = interim;
          renderSharedWorldTrainingSpeechStatus(question);
          const score = scoreSharedWorldTrainingSpeech(clean(`${sharedWorldTrainingSpeech.transcript} ${sharedWorldTrainingSpeech.chunk}`), expectedText, sharedWorldTrainingSpeech.passRatio || passRatio);
          if (score.passed) {
            armSharedWorldTrainingSpeechSettle("matched_pause");
          }
        };
        recognition.onerror = (event) => {
          const code = clean(event && event.error || "");
          if (code && code !== "no-speech") {
            setSharedWorldStatus(`Mic check: ${code}`, "error");
          }
        };
        recognition.onend = () => {
          if (sharedWorldTrainingSpeech.active && !sharedWorldTrainingSpeech.posted && Date.now() < sharedWorldTrainingSpeech.deadline) {
            try { recognition.start(); } catch (error) {}
          }
        };
        try {
          recognition.start();
        } catch (error) {
          sharedWorldTrainingSpeech.active = false;
          setSharedWorldTrainingMicEnergy(false);
          setSharedWorldStatus("Could not start the browser microphone checker.", "error");
          return false;
        }
        setSharedWorldTrainingMicEnergy(true);
        sharedWorldTrainingSpeech.timer = window.setInterval(() => {
          renderSharedWorldTrainingSpeechStatus(question);
          if (Date.now() >= sharedWorldTrainingSpeech.deadline) {
            const liveText = clean(`${sharedWorldTrainingSpeech.transcript || ""} ${sharedWorldTrainingSpeech.chunk || ""}`);
            const score = scoreSharedWorldTrainingSpeech(liveText, expectedText, sharedWorldTrainingSpeech.passRatio || passRatio);
            if (score.passed) {
              if (!sharedWorldTrainingSpeech.settleTimer) {
                armSharedWorldTrainingSpeechSettle("matched_timeout");
              }
            } else {
              finishSharedWorldTrainingSpeech(false, "timeout");
            }
          }
        }, 250);
        renderSharedWorldTrainingSpeechStatus(question);
        return true;
      };

      const maybeStartSharedWorldTrainingSpeech = (question = {}, slimeId = "", options = {}) => {
        if (!sharedWorldTrainingQuestionIsSpeech(question)) {
          return false;
        }
        const key = sharedWorldTrainingSpeechQuestionKey(question, slimeId);
        if (!key) {
          return false;
        }
        const force = Boolean(options && options.force);
        if (sharedWorldTrainingSpeech.active) {
          const activeKey = sharedWorldTrainingSpeechQuestionKey({
            id: sharedWorldTrainingSpeech.questionId,
            read_text: sharedWorldTrainingSpeech.expectedText,
          }, sharedWorldTrainingSpeech.slimeId);
          if (!force && activeKey === key) {
            return true;
          }
          stopSharedWorldTrainingSpeech({ clearOverhead: false });
        }
        const started = startSharedWorldTrainingSpeech(question, slimeId);
        if (started) {
          sharedWorldTrainingAutoSpeechKey = key;
        }
        return started;
      };

      const restartSharedWorldTrainingSpeech = (question = {}, slimeId = "") => {
        stopSharedWorldTrainingSpeech({ clearOverhead: false });
        sharedWorldTrainingAutoSpeechKey = "";
        const started = maybeStartSharedWorldTrainingSpeech(question, slimeId, { force: true });
        if (started) {
          setSharedWorldStatus("Mic cache cleared. Listening again.", "ok");
        }
        return started;
      };

      const sharedWorldTrainingStatRows = (stats = {}) => [
        ["strength", "Strength", stats.strength || 1, "Training damage and future world attack power"],
        ["defense", "Defense", stats.defense || 1, "Future world defense and toughness"],
        ["hp", "HP Core", stats.hp_bonus || stats.hpBonus || 0, "Adds 10 max HP"],
        ["mana", "Mana Core", stats.mana_bonus || stats.manaBonus || 0, "Adds 10 max mana"],
      ];

      const renderSharedWorldTrainingLoadoutPanel = () => {
        if (!worldTrainingLoadoutPanel) {
          return;
        }
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const stats = training.stats && typeof training.stats === "object" ? training.stats : {};
        const points = Math.max(0, Math.floor(Number(stats.available_points || stats.availablePoints || 0) || 0));
        const skillPoints = Math.max(0, Math.floor(Number(stats.skill_points || stats.skillPoints || 0) || 0));
        const level = Math.max(1, Math.floor(Number(stats.level || 1) || 1));
        const exp = Math.max(0, Math.floor(Number(stats.exp || 0) || 0));
        const nextExp = Math.max(exp, Math.floor(Number(stats.next_exp || stats.nextExp || exp) || exp));
        const progress = `${Math.max(0, Math.min(100, Math.round(Number(stats.progress || 0) * 100)))}%`;
        const trainingWords = Math.max(0, Math.floor(Number(stats.training_words || stats.trainingWords || 0) || 0));
        const skills = Array.isArray(stats.skills) ? stats.skills : [];
        const earthquake = skills.find((skill) => clean(skill && skill.id).toLowerCase() === "earthquake") || skills[0] || {};
        const skillLevel = Math.max(0, Math.floor(Number(earthquake.current_level || earthquake.currentLevel || earthquake.level || 0) || 0));
        const skillMax = Math.max(skillLevel, Math.floor(Number(earthquake.max_level || earthquake.maxLevel || skillLevel) || skillLevel));
        const skillDamage = Math.max(0, Math.floor(Number(earthquake.damage_percent || earthquake.damagePercent || 100) || 100));
        const skillMana = Math.max(0, Math.floor(Number(earthquake.mana_cost || earthquake.manaCost || 0) || 0));
        const skillRadius = Math.max(1, Math.floor(Number(earthquake.radius_px || earthquake.radiusPx || 400) || 400));
        const mana = Math.max(0, Math.floor(Number((training.arena && (training.arena.player_mana || training.arena.playerMana)) || 0) || 0));
        worldTrainingLoadoutPanel.innerHTML = `
          <div class="ft-world-training-loadout-head">
            <span>
              <b>Training Core</b>
              <small>${trainingWords} field EXP · ${points} stat point${points === 1 ? "" : "s"} · ${skillPoints} skill point${skillPoints === 1 ? "" : "s"}</small>
            </span>
            <span class="ft-world-training-loadout-level">Lv ${level}<br><small>${exp}${nextExp > exp ? `/${nextExp}` : ""}</small></span>
          </div>
          <div class="ft-world-training-loadout-xp" title="Character EXP"><i style="--bar:${progress}"></i></div>
          <div class="ft-world-training-loadout-grid">
            ${sharedWorldTrainingStatRows(stats).map(([key, label, value]) => `
              <div class="ft-world-training-loadout-stat">
                <span>${label}<br><b>${Math.max(0, Math.floor(Number(value || 0) || 0))}</b></span>
                <button type="button" data-world-training-stat="${key}" ${points <= 0 ? "disabled" : ""}>+</button>
              </div>
            `).join("")}
          </div>
          <div class="ft-world-training-skill-card">
            <div class="ft-world-training-skill-head">
              <span class="ft-world-training-skill-icon" aria-hidden="true"></span>
              <span><b>${escapeHtml(clean(earthquake.name || "Earthquake"))}</b><small>${escapeHtml(clean(earthquake.description || "Stomp the ground and damage nearby slimes."))}</small></span>
              <span class="ft-world-training-skill-level">Lv ${skillLevel}/${skillMax}</span>
            </div>
            <div class="ft-world-training-skill-meta">
              <span>${skillDamage}% dmg</span>
              <span>${skillRadius}px</span>
              <span>${skillMana} MP</span>
            </div>
            <div class="ft-world-training-skill-actions">
              <button type="button" data-world-training-skill-upgrade="${escapeHtml(clean(earthquake.id || "earthquake"))}" ${skillPoints <= 0 || skillLevel >= skillMax ? "disabled" : ""}>Upgrade</button>
              <button type="button" data-world-training-skill-cast="${escapeHtml(clean(earthquake.id || "earthquake"))}" ${mana < skillMana ? "disabled" : ""}>Cast</button>
            </div>
          </div>
        `;
      };

      const sharedWorldTrainingSkillById = (skillId = "earthquake") => {
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const stats = training.stats && typeof training.stats === "object" ? training.stats : {};
        const skills = Array.isArray(stats.skills) ? stats.skills : [];
        const id = clean(skillId || "earthquake").toLowerCase() || "earthquake";
        return skills.find((skill) => clean(skill && skill.id).toLowerCase() === id) || skills[0] || {};
      };

      const renderSharedWorldTrainingQuickSkill = () => {
        if (!worldTrainingQuickSkill) {
          return;
        }
        const skill = sharedWorldTrainingSkillById("earthquake");
        const skillId = clean(skill.id || "earthquake") || "earthquake";
        const name = clean(skill.name || "Earthquake");
        const level = Math.max(0, Math.floor(Number(skill.current_level || skill.currentLevel || skill.level || 0) || 0));
        const manaCost = Math.max(0, Math.floor(Number(skill.mana_cost || skill.manaCost || 0) || 0));
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : {};
        const mana = Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0));
        const serverCooldowns = arena.skill_cooldowns && typeof arena.skill_cooldowns === "object" ? arena.skill_cooldowns : (arena.skillCooldowns && typeof arena.skillCooldowns === "object" ? arena.skillCooldowns : {});
        const rawServerUntil = Number(serverCooldowns[skillId] || 0);
        const serverUntilMs = rawServerUntil > 0 && rawServerUntil < 100000000000 ? rawServerUntil * 1000 : rawServerUntil;
        if (serverUntilMs > Date.now() && serverUntilMs > Number(sharedWorldTrainingSkillCooldownUntil.get(skillId) || 0)) {
          sharedWorldTrainingSkillCooldownUntil.set(skillId, serverUntilMs);
        }
        const cooldownUntil = Number(sharedWorldTrainingSkillCooldownUntil.get(skillId) || 0);
        const remaining = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
        const disabled = sharedWorldMapMode !== "training" || !level || sharedWorldTrainingLoading || mana < manaCost || remaining > 0;
        worldTrainingQuickSkill.dataset.worldTrainingSkillCast = skillId;
        worldTrainingQuickSkill.disabled = disabled;
        worldTrainingQuickSkill.classList.toggle("is-cooling", remaining > 0);
        worldTrainingQuickSkill.classList.toggle("is-locked", !level);
        worldTrainingQuickSkill.classList.toggle("is-low-mana", Boolean(level && mana < manaCost && remaining <= 0));
        worldTrainingQuickSkill.style.setProperty("--skill-mana-fill", `${manaCost > 0 ? Math.max(0, Math.min(100, Math.round((mana / manaCost) * 100))) : 100}%`);
        worldTrainingQuickSkill.style.setProperty("--skill-level-fill", `${Math.max(0, Math.min(100, Math.round((level / Math.max(1, Number(skill.max_level || skill.maxLevel || level || 1))) * 100)))}%`);
        worldTrainingQuickSkill.setAttribute("aria-label", `Cast ${name}`);
        worldTrainingQuickSkill.title = remaining > 0 ? `${name} cooldown ${remaining}s` : `${name} - ${manaCost} MP`;
        const titleNode = worldTrainingQuickSkill.querySelector(".ft-world-training-quick-skill-copy b");
        if (titleNode) {
          titleNode.textContent = name;
        }
        if (worldTrainingQuickSkillMeta) {
          worldTrainingQuickSkillMeta.textContent = remaining > 0
            ? `Cooldown ${remaining}s`
            : (level ? `${mana}/${manaCost} MP · Lv ${level}` : "Locked");
        }
        if (worldTrainingQuickSkillCooldown) {
          worldTrainingQuickSkillCooldown.textContent = remaining > 0 ? `${remaining}` : "";
        }
        if (remaining > 0 && !sharedWorldTrainingSkillCooldownTimer) {
          sharedWorldTrainingSkillCooldownTimer = window.setInterval(() => {
            renderSharedWorldTrainingQuickSkill();
            const stillCooling = Array.from(sharedWorldTrainingSkillCooldownUntil.values()).some((time) => Number(time || 0) > Date.now());
            if (!stillCooling && sharedWorldTrainingSkillCooldownTimer) {
              window.clearInterval(sharedWorldTrainingSkillCooldownTimer);
              sharedWorldTrainingSkillCooldownTimer = 0;
            }
          }, 250);
        }
      };
