

      const warmEmbeddedSpaceWAudioCache = (nodes = [], token = spaceWAudioPreloadToken, startIndex = currentNodeIndex, selectedValue = "", options = {}) => {
        const sourceNodes = Array.isArray(nodes) ? nodes : [];
        if (!sourceNodes.length || offlineStoragePressure === "critical") {
          return;
        }
        const centerIndex = Math.max(0, Math.round(Number(startIndex) || 0));
        const selectedRaw = clean(selectedValue);
        const includeAllEmbedded = Boolean(options.includeAllEmbedded);
        const nodeLimit = Math.max(0, Math.floor(Number(options.nodeLimit || options.maxNodes || 0) || 0));
        const startDelayMs = Math.max(0, Math.floor(Number(options.startDelayMs || 0) || 0));
        void (async () => {
          if (startDelayMs) {
            await delay(startDelayMs);
          }
          const orderedNodes = orderNodesForCache(sourceNodes, centerIndex);
          const pressureLimit = offlineStoragePressure === "high" ? 2 : 0;
          const effectiveLimit = pressureLimit && (!nodeLimit || pressureLimit < nodeLimit) ? pressureLimit : nodeLimit;
          const rows = effectiveLimit ? orderedNodes.slice(0, effectiveLimit) : orderedNodes;
          for (const { node, index: nodeIndex } of rows) {
            if (token !== spaceWAudioPreloadToken) {
              return;
            }
            const assets = selectedRaw.startsWith("embedded:")
              ? [findEmbeddedAudioAssetForNode(node, selectedRaw)].filter(Boolean)
              : (includeAllEmbedded ? getEmbeddedAudioAssetsForNode(node) : []);
            for (const asset of assets) {
              if (token !== spaceWAudioPreloadToken) {
                return;
              }
              if (!asset || !asset.url) {
                continue;
              }
              try {
                const url = serverAssetUrl(asset.url);
                await getOrCreateSpaceWUrlAudio(url, asset.timings || [], {
                  nodeIndex,
                  voice: asset.voice || asset.id || "embedded",
                  timeoutMs: 16000,
                });
              } catch (error) {
                // Embedded URL cache is opportunistic; base64 assets already work offline.
              }
            }
          }
        })();
      };

      const warmSpaceWAudioCache = (nodes = [], selectedValue = "", options = {}) => {
        const voiceValue = normalizedCacheVoiceValue(selectedValue);
        const sourceNodes = Array.isArray(nodes) ? nodes : [];
        const token = ++spaceWAudioPreloadToken;
        const startIndex = Math.max(0, Math.round(Number(options.startIndex ?? currentNodeIndex) || 0));
        const configuredMaxItems = Math.max(0, Math.floor(Number(options.maxItems || options.maxTasks || options.nodeLimit || 0) || 0));
        const maxItems = offlineStoragePressure === "critical"
          ? 0
          : (offlineStoragePressure === "high" ? Math.min(configuredMaxItems || 2, 2) : configuredMaxItems);
        const startDelayMs = Math.max(0, Math.floor(Number(options.startDelayMs || 0) || 0));
        warmEmbeddedSpaceWAudioCache(sourceNodes, token, startIndex, selectedValue, {
          includeAllEmbedded: Boolean(options.includeAllEmbedded),
          nodeLimit: options.nodeLimit,
          startDelayMs,
        });
        if (!voiceValue || !sourceNodes.length || offlineStoragePressure === "critical") {
          return;
        }
        const allItems = orderNodesForCache(sourceNodes, startIndex)
          .map(({ node, index }) => ({ text: spaceWNodeEnglishText(node), index }))
          .filter((item) => item.text);
        const items = maxItems ? allItems.slice(0, maxItems) : allItems;
        if (!items.length) {
          return;
        }
        const showLoadStatus = Boolean(options.loadStatus && loadGate && !loadGate.classList.contains("is-hidden"));
        if (showLoadStatus) {
          setLoadStatus("Audio cache is warming in the background. Start or Review will verify it before study.");
        }
        void (async () => {
          if (startDelayMs) {
            await delay(startDelayMs);
          }
          let ready = 0;
          for (const item of items) {
            if (token !== spaceWAudioPreloadToken) {
              return;
            }
            try {
              const result = await getOrCreateSpaceWTtsAudio(item.text, voiceValue, { nodeIndex: item.index });
              if (result && result.blob instanceof Blob) {
                ready += 1;
              }
            } catch (error) {
              // Background cache should never block study.
            }
            await delay(120);
          }
          if (token === spaceWAudioPreloadToken && showLoadStatus && !lessonAudioPrepareBusy) {
            const savedActionText = pendingSpaceWHasTrainModeNodes && spaceWSavedProgressAllowsTrainReview
              ? (pendingSpaceWHasTrainModeNodes() && spaceWSavedProgressAllowsTrainReview(currentSpaceWCache.savedProgress, pendingLessonNodes)
                ? "Select New Study, Continue Previous, or Review Train."
                : "Select New Study or Continue Previous.")
              : "Select New Study or Continue Previous.";
            setLoadStatus(currentSpaceWCache.savedProgress
              ? `Audio cache ready for ${ready}/${items.length} nodes. ${savedActionText}`
              : `Audio cache ready for ${ready}/${items.length} nodes. Starting study now.`);
          }
        })();
      };

      const hasPendingLoadedLesson = () => Boolean(
        pendingVocabularyPayload ||
        pendingQuestionPayload ||
        pendingParagraphPayload ||
        (Array.isArray(pendingLessonNodes) && pendingLessonNodes.length)
      );

      const updateLoadEnterNowButton = () => {
        if (!loadEnterNowButton) {
          return;
        }
        const canEnter = Boolean(lessonAudioPrepareBusy && hasPendingLoadedLesson());
        loadEnterNowButton.hidden = !canEnter;
        loadEnterNowButton.disabled = !canEnter;
      };

      const setLessonAudioPrepareControls = (busy) => {
        lessonAudioPrepareBusy = Boolean(busy);
        [loadStartButton, loadReviewButton, loadReviewTrainButton].forEach((button) => {
          if (button) {
            button.disabled = Boolean(busy);
          }
        });
        if (voiceSelect) {
          voiceSelect.disabled = Boolean(busy);
        }
        updateLoadEnterNowButton();
      };

      const cancelLessonAudioPrepare = () => {
        lessonAudioPrepareToken += 1;
        lessonAudioPrepareMode = "";
        setLessonAudioPrepareControls(false);
      };

      const lessonAudioPrepareMessage = (label, done, total, failed = 0) => {
        const failText = failed ? `, ${failed} skipped` : "";
        return `${label}: preparing audio cache ${done}/${total}${failText}...`;
      };

      const runLessonAudioPrepareTasks = async (label, tasks = [], options = {}) => {
        const rows = Array.isArray(tasks) ? tasks.filter((task) => task && typeof task.run === "function") : [];
        const token = ++lessonAudioPrepareToken;
        if (!rows.length) {
          if (options.status !== false && loadGate && !loadGate.classList.contains("is-hidden")) {
            setLoadStatus(`${label}: audio cache already ready.`);
          }
          return { total: 0, ready: 0, failed: 0, canceled: false };
        }
        setLessonAudioPrepareControls(true);
        lessonAudioPrepareMode = clean(options.fastMode || options.mode || "start");
        let ready = 0;
        let failed = 0;
        try {
          if (options.status !== false) {
            setLoadStatus(lessonAudioPrepareMessage(label, 0, rows.length));
          }
          for (const task of rows) {
            if (token !== lessonAudioPrepareToken) {
              return { total: rows.length, ready, failed, canceled: true };
            }
            let ok = false;
            try {
              ok = await task.run();
            } catch (error) {
              ok = false;
            }
            if (token !== lessonAudioPrepareToken) {
              return { total: rows.length, ready, failed, canceled: true };
            }
            if (ok) {
              ready += 1;
            } else {
              failed += 1;
            }
            if (options.status !== false) {
              setLoadStatus(lessonAudioPrepareMessage(label, ready + failed, rows.length, failed));
            }
            await delay(20);
          }
          if (token !== lessonAudioPrepareToken) {
            return { total: rows.length, ready, failed, canceled: true };
          }
          if (options.status !== false) {
            setLoadStatus(failed
              ? `${label}: audio cache ready ${ready}/${rows.length}; ${failed} item(s) will use online fallback if needed.`
              : `${label}: audio cache ready ${ready}/${rows.length}.`);
          }
          return { total: rows.length, ready, failed, canceled: false };
        } finally {
          if (token === lessonAudioPrepareToken) {
            lessonAudioPrepareMode = "";
            setLessonAudioPrepareControls(false);
          }
        }
      };

      const warmAudioTasksInBackground = (label, tasks = [], options = {}) => {
        const orderedRows = prioritizedAudioTasks(
          Array.isArray(tasks) ? tasks.filter((task) => task && typeof task.run === "function") : [],
          options.startIndex ?? currentNodeIndex,
        );
        const maxTasks = Math.max(0, Math.floor(Number(options.maxTasks || options.taskLimit || 0) || 0));
        const configuredRows = maxTasks ? orderedRows.slice(0, maxTasks) : orderedRows;
        if (!configuredRows.length) {
          return;
        }
        const token = ++lessonAudioBackgroundToken;
        const delayMs = Math.max(40, Math.min(500, Number(options.delayMs || 140) || 140));
        const startDelayMs = Math.max(0, Math.floor(Number(options.startDelayMs || 0) || 0));
        void (async () => {
          if (startDelayMs) {
            await delay(startDelayMs);
          }
          const storageState = typeof ensureOfflineStoragePersistence === "function"
            ? await ensureOfflineStoragePersistence()
            : null;
          const pressure = clean(storageState && storageState.pressure || offlineStoragePressure).toLowerCase();
          if (token !== lessonAudioBackgroundToken || pressure === "critical") {
            return;
          }
          // 2026-07-21: Under quota pressure keep only current/next audio work; foreground playback remains local-first.
          const rows = pressure === "high" ? configuredRows.slice(0, 4) : configuredRows;
          const workerCount = Math.max(1, Math.min(rows.length, Math.floor(Number(options.workers || 1) || 1)));
          let ready = 0;
          let failed = 0;
          let cursor = 0;
          const runWorker = async () => {
            while (token === lessonAudioBackgroundToken && cursor < rows.length) {
              const task = rows[cursor];
              cursor += 1;
              try {
                const ok = await task.run();
                if (ok) {
                  ready += 1;
                } else {
                  failed += 1;
                }
              } catch (error) {
                failed += 1;
              }
              if (token === lessonAudioBackgroundToken && options.status && loadGate && !loadGate.classList.contains("is-hidden")) {
                setLoadStatus(`${label}: background cache ${ready + failed}/${rows.length}${failed ? `, ${failed} skipped` : ""}.`);
              }
              await delay(delayMs);
            }
          };
          await Promise.all(Array.from({ length: workerCount }, () => runWorker()));
        })();
      };

      const addUniqueAudioClip = (clips, seen, clip) => {
        const asset = normalizeAudioClip(clip);
        if (!asset || asset.kind === "speak") {
          return false;
        }
        const key = audioClipCacheKey(asset);
        if (!key || seen.has(key)) {
          return false;
        }
        seen.add(key);
        clips.push(asset);
        return false;
      };

      const addAudioSequenceClips = (clips, seen, sequence) => {
        normalizeAudioSequence(sequence).forEach((clip) => addUniqueAudioClip(clips, seen, clip));
      };

      const addEffectAudioClips = (clips, seen, effects = {}) => {
        Object.values(normalizeEffectSounds(effects)).forEach((clip) => addUniqueAudioClip(clips, seen, clip));
      };

      const vocabularyCanonicalAudioClips = (audio = {}) => {
        const source = audio && typeof audio === "object" ? audio : {};
        const findClip = (keys = []) => {
          for (const key of keys) {
            if (source[key]) {
              return source[key];
            }
          }
          const lowered = {};
          Object.entries(source).forEach(([key, value]) => {
            lowered[clean(key).toLowerCase()] = value;
          });
          for (const key of keys) {
            const clip = lowered[clean(key).toLowerCase()];
            if (clip) {
              return clip;
            }
          }
          return null;
        };
        return [
          findClip(["sot:en-GB", "en-GB", "uk"]),
          findClip(["sot:en-US", "en-US", "us"]),
          findClip(["sot:vi-VN", "vi-VN", "vi"]),
        ].filter(Boolean);
      };

      const vocabularyAudioClipsForItem = (item, selectedValue = "", options = {}) => {
        const audio = item && item.audio && typeof item.audio === "object" ? item.audio : {};
        const source = audio && typeof audio === "object" ? audio : {};
        const lowered = {};
        Object.entries(source).forEach(([key, value]) => {
          lowered[clean(key).toLowerCase()] = value;
        });
        const findClip = (keys = []) => {
          for (const key of keys) {
            if (source[key]) {
              return source[key];
            }
          }
          for (const key of keys) {
            const clip = lowered[clean(key).toLowerCase()];
            if (clip) {
              return clip;
            }
          }
          return null;
        };
        const selectedIsUs = /en-us/i.test(clean(selectedValue));
        const selectedKeys = selectedIsUs ? ["sot:en-US", "en-US", "us"] : ["sot:en-GB", "en-GB", "uk"];
        const alternateKeys = selectedIsUs ? ["sot:en-GB", "en-GB", "uk"] : ["sot:en-US", "en-US", "us"];
        const clips = [];
        const seen = new Set();
        const addClip = (clip) => addUniqueAudioClip(clips, seen, clip);
        if (options.includeMeaning !== false) {
          addClip(findClip(["sot:vi-VN", "vi-VN", "vi"]));
        }
        if (options.includeSelected !== false) {
          addClip(findClip(selectedKeys));
        }
        if (options.includeAlternates !== false) {
          addClip(findClip(alternateKeys));
        }
        if (options.includeAllCanonical) {
          vocabularyCanonicalAudioClips(source).forEach(addClip);
        }
        return clips;
      };

      const addQuestionAudioConfigClip = (clips, seen, config) => {
        const clip = questionCardAudioClip(config);
        if (clip) {
          addUniqueAudioClip(clips, seen, clip);
        }
      };

      const collectQuestionPayloadAudioClips = (payload = {}) => {
        const normalized = payload && payload.kind === "future_question_payload" ? payload : normalizeQuestionPayload(payload);
        const clips = [];
        const seen = new Set();
        addEffectAudioClips(clips, seen, normalized.effects || {});
        (Array.isArray(normalized.nodes) ? normalized.nodes : []).forEach((node) => {
          const audioCard = node && node.cards && node.cards.audio ? node.cards.audio : null;
          if (audioCard && audioCard.url) {
            addUniqueAudioClip(clips, seen, {
              mime: clean(audioCard.mime) || "audio/mpeg",
              url: audioCard.url,
            });
          }
          const questions = node && node.cards && Array.isArray(node.cards.questions) ? node.cards.questions : [];
          questions.forEach((question) => {
            addQuestionAudioConfigClip(clips, seen, question && question.audio);
            const answerAudio = question && question.answer_audio && typeof question.answer_audio === "object" ? question.answer_audio : {};
            addQuestionAudioConfigClip(clips, seen, answerAudio);
            (Array.isArray(answerAudio.items) ? answerAudio.items : []).forEach((entry) => {
              addQuestionAudioConfigClip(clips, seen, entry && typeof entry === "object" ? (entry.audio || entry.au || entry.clip || entry) : entry);
            });
            const answerInfo = question && question.answer_info && typeof question.answer_info === "object" ? question.answer_info : {};
            (Array.isArray(answerInfo.items) ? answerInfo.items : []).forEach((entry) => {
              addQuestionAudioConfigClip(clips, seen, entry && entry.audio);
            });
            if (question && question.root_notice) {
              questionRootNoticeTurns(question.root_notice).forEach((turn) => addQuestionAudioConfigClip(clips, seen, turn && turn.audio));
            }
          });
        });
        return clips;
      };

      const questionAudioCacheOrder = (payload = {}, options = {}) => {
        const normalized = payload && payload.kind === "future_question_payload" ? payload : normalizeQuestionPayload(payload);
        const total = Array.isArray(normalized.nodes) ? normalized.nodes.length : 0;
        const seen = new Set();
        const order = [];
        const addIndex = (value) => {
          const index = Math.floor(Number(value));
          if (!Number.isFinite(index) || index < 0 || index >= total || seen.has(index)) {
            return;
          }
          seen.add(index);
          order.push(index);
        };
        if (Array.isArray(options.nodeOrder)) {
          options.nodeOrder.forEach(addIndex);
        }
        addIndex(options.startIndex ?? currentNodeIndex);
        for (let index = Math.max(0, Math.floor(Number(options.startIndex ?? currentNodeIndex) || 0)); index < total; index += 1) {
          addIndex(index);
        }
        for (let index = 0; index < total; index += 1) {
          addIndex(index);
        }
        return order;
      };

      const collectQuestionAudioTasks = (payload = {}, options = {}) => {
        const normalized = payload && payload.kind === "future_question_payload" ? payload : normalizeQuestionPayload(payload);
        const tasks = [];
        const seen = new Set();
        const nodeOrder = questionAudioCacheOrder(normalized, options);
        const priorityByNode = new Map(nodeOrder.map((nodeIndex, priorityIndex) => [nodeIndex, priorityIndex]));
        const maxNodes = Math.max(0, Math.floor(Number(options.maxNodes || options.nodeLimit || 0) || 0));
        const allowedNodes = maxNodes ? new Set(nodeOrder.slice(0, maxNodes)) : null;
        const startNodeIndex = Math.max(0, Math.floor(Number(options.startIndex ?? currentNodeIndex) || 0));
        const startQuestionIndex = Math.max(0, Math.floor(Number(options.startQuestionIndex ?? questionQuestionIndex) || 0));
        const questionOrder = Array.isArray(options.questionOrder) ? options.questionOrder.map((index) => Math.max(0, Math.floor(Number(index) || 0))) : null;
        const currentQuestionOnly = Boolean(options.currentQuestionOnly);
        const questionAllowedForNode = (nodeIndex, questionIndex) => {
          if (nodeIndex !== startNodeIndex) {
            return !currentQuestionOnly;
          }
          if (questionOrder && questionOrder.length) {
            const orderedIndex = questionOrder.indexOf(questionIndex);
            if (orderedIndex < 0) {
              return false;
            }
            return currentQuestionOnly ? orderedIndex === startQuestionIndex : orderedIndex >= startQuestionIndex;
          }
          return currentQuestionOnly ? questionIndex === startQuestionIndex : questionIndex >= startQuestionIndex;
        };
        const questionPriorityForNode = (nodeIndex, questionIndex = 0) => {
          if (nodeIndex !== startNodeIndex) {
            return Math.max(0, questionIndex);
          }
          if (questionOrder && questionOrder.length) {
            const orderedIndex = questionOrder.indexOf(questionIndex);
            return orderedIndex >= 0 ? Math.max(0, orderedIndex - startQuestionIndex) : 999;
          }
          return Math.max(0, questionIndex - startQuestionIndex);
        };
        const addTask = (clip, nodeIndex = Number.MAX_SAFE_INTEGER, label = "Question audio", questionPriority = 0) => {
          const asset = normalizeAudioClip(clip);
          if (!asset || asset.kind === "speak") {
            return;
          }
          const key = audioClipCacheKey(asset);
          if (!key || seen.has(key)) {
            return;
          }
          seen.add(key);
          const nodePriority = priorityByNode.has(nodeIndex) ? priorityByNode.get(nodeIndex) : Number.MAX_SAFE_INTEGER;
          tasks.push({
            label,
            nodeIndex,
            priorityIndex: (nodePriority * 100000) + (Math.max(0, questionPriority) * 1000) + tasks.length,
            run: () => preloadAudioClip(asset, null),
          });
        };
        if (options.includeEffects !== false) {
          Object.values(normalizeEffectSounds(normalized.effects || {})).forEach((clip, index) => addTask(clip, Number.MAX_SAFE_INTEGER, `Question effect ${index + 1}`));
        }
        (Array.isArray(normalized.nodes) ? normalized.nodes : []).forEach((node, nodeIndex) => {
          if (allowedNodes && !allowedNodes.has(nodeIndex)) {
            return;
          }
          const audioCard = node && node.cards && node.cards.audio ? node.cards.audio : null;
          if (audioCard && audioCard.url) {
            addTask({
              mime: clean(audioCard.mime) || "audio/mpeg",
              url: audioCard.url,
            }, nodeIndex, `Question node ${nodeIndex + 1} audio card`, 0);
          }
          const questions = node && node.cards && Array.isArray(node.cards.questions) ? node.cards.questions : [];
          questions.forEach((question, questionIndex) => {
            if (!questionAllowedForNode(nodeIndex, questionIndex)) {
              return;
            }
            const questionPriority = questionPriorityForNode(nodeIndex, questionIndex);
            addTask(question && question.audio, nodeIndex, `Question ${nodeIndex + 1}.${questionIndex + 1}`, questionPriority);
            const answerAudio = question && question.answer_audio && typeof question.answer_audio === "object" ? question.answer_audio : {};
            addTask(answerAudio, nodeIndex, `Question ${nodeIndex + 1}.${questionIndex + 1} answer`, questionPriority);
            (Array.isArray(answerAudio.items) ? answerAudio.items : []).forEach((entry) => {
              addTask(entry && typeof entry === "object" ? (entry.audio || entry.au || entry.clip || entry) : entry, nodeIndex, `Question ${nodeIndex + 1}.${questionIndex + 1} answer item`, questionPriority);
            });
            const answerInfo = question && question.answer_info && typeof question.answer_info === "object" ? question.answer_info : {};
            (Array.isArray(answerInfo.items) ? answerInfo.items : []).forEach((entry) => {
              addTask(entry && entry.audio, nodeIndex, `Question ${nodeIndex + 1}.${questionIndex + 1} info`, questionPriority);
            });
            if (question && question.root_notice) {
              questionRootNoticeTurns(question.root_notice).forEach((turn, turnIndex) => {
                addTask(turn && turn.audio, nodeIndex, `Question ${nodeIndex + 1}.${questionIndex + 1} notice ${turnIndex + 1}`, questionPriority);
              });
            }
          });
        });
        return tasks;
      };

      const paragraphAudioCacheOrder = (payload = {}, options = {}) => {
        const normalized = payload && payload.kind === "future_paragraph_payload" ? payload : normalizeParagraphPayload(payload);
        const total = Array.isArray(normalized.nodes) ? normalized.nodes.length : 0;
        const seen = new Set();
        const order = [];
        const addIndex = (value) => {
          const index = Math.floor(Number(value));
          if (!Number.isFinite(index) || index < 0 || index >= total || seen.has(index)) {
            return;
          }
          seen.add(index);
          order.push(index);
        };
        if (Array.isArray(options.nodeOrder)) {
          options.nodeOrder.forEach(addIndex);
        }
        const startIndex = Math.max(0, Math.min(Math.max(0, total - 1), Math.floor(Number(options.startIndex ?? paragraphNodeIndex) || 0)));
        addIndex(startIndex);
        for (let index = startIndex; index < total; index += 1) {
          addIndex(index);
        }
        for (let index = 0; index < total; index += 1) {
          addIndex(index);
        }
        return order;
      };

      const collectParagraphAudioTasks = (payload = {}, options = {}) => {
        const normalized = payload && payload.kind === "future_paragraph_payload" ? payload : normalizeParagraphPayload(payload);
        const tasks = [];
        const seen = new Set();
        const nodeOrder = paragraphAudioCacheOrder(normalized, options);
        const priorityByNode = new Map(nodeOrder.map((nodeIndex, priorityIndex) => [nodeIndex, priorityIndex]));
        const maxNodes = Math.max(0, Math.floor(Number(options.maxNodes || options.nodeLimit || 0) || 0));
        const allowedNodes = maxNodes ? new Set(nodeOrder.slice(0, maxNodes)) : null;
        const startNodeIndex = Math.max(0, Math.min(Math.max(0, (normalized.nodes || []).length - 1), Math.floor(Number(options.startIndex ?? paragraphNodeIndex) || 0)));
        const startChildIndex = Math.max(0, Math.floor(Number(options.startChildIndex ?? paragraphChildIndex) || 0));
        const addTask = (clip, nodeIndex = Number.MAX_SAFE_INTEGER, childIndex = 0, wordIndex = 0, label = "Paragraph audio") => {
          const asset = normalizeAudioClip(clip);
          if (!asset || asset.kind === "speak") {
            return;
          }
          const key = audioClipCacheKey(asset);
          if (!key || seen.has(key)) {
            return;
          }
          seen.add(key);
          const nodePriority = priorityByNode.has(nodeIndex) ? priorityByNode.get(nodeIndex) : Number.MAX_SAFE_INTEGER;
          tasks.push({
            label,
            nodeIndex,
            priorityIndex: (nodePriority * 100000) + (Math.max(0, childIndex) * 1000) + Math.max(0, wordIndex) + tasks.length,
            run: () => preloadAudioClip(asset, null),
          });
        };
        if (options.includeEffects !== false) {
          Object.values(normalizeEffectSounds(normalized.effects || {})).forEach((clip, index) => {
            addTask(clip, Number.MAX_SAFE_INTEGER, 0, index, `Paragraph effect ${index + 1}`);
          });
        }
        (Array.isArray(normalized.nodes) ? normalized.nodes : []).forEach((node, nodeIndex) => {
          if (allowedNodes && !allowedNodes.has(nodeIndex)) {
            return;
          }
          const children = node && Array.isArray(node.children) ? node.children : [];
          const childIndexes = [];
          const addChildIndex = (value) => {
            const index = Math.floor(Number(value));
            if (Number.isFinite(index) && index >= 0 && index < children.length && !childIndexes.includes(index)) {
              childIndexes.push(index);
            }
          };
          if (nodeIndex === startNodeIndex) {
            addChildIndex(startChildIndex);
          }
          for (let index = 0; index < children.length; index += 1) {
            addChildIndex(index);
          }
          childIndexes.forEach((childIndex) => {
            const child = children[childIndex] || {};
            addTask(child.meaning_audio || child.vi_audio, nodeIndex, childIndex, 0, `Paragraph ${nodeIndex + 1}.${childIndex + 1} Vietnamese`);
            (Array.isArray(child.word_audio) ? child.word_audio : []).forEach((clip, wordIndex) => {
              addTask(clip, nodeIndex, childIndex, wordIndex + 1, `Paragraph ${nodeIndex + 1}.${childIndex + 1} word ${wordIndex + 1}`);
            });
            addTask(child.audio, nodeIndex, childIndex, 950, `Paragraph ${nodeIndex + 1}.${childIndex + 1} English`);
          });
        });
        return tasks;
      };

      const collectVocabularyPayloadAudioClips = (payload = {}) => {
        const normalized = payload && payload.kind === "future_vocabulary_payload" ? payload : normalizeCompactVocabPayload(payload);
        const clips = [];
        const seen = new Set();
        addEffectAudioClips(clips, seen, normalized.effects || {});
        (Array.isArray(normalized.words) ? normalized.words : []).forEach((item) => {
          const audio = item && item.audio && typeof item.audio === "object" ? item.audio : {};
          vocabularyCanonicalAudioClips(audio).forEach((clip) => addUniqueAudioClip(clips, seen, clip));
        });
        return clips;
      };

      const collectVocabularyAudioTasks = (payload = {}, selectedValue = "", options = {}) => {
        const normalized = payload && payload.kind === "future_vocabulary_payload" ? payload : normalizeCompactVocabPayload(payload);
        const tasks = [];
        const seen = new Set();
        const words = Array.isArray(normalized.words) ? normalized.words : [];
        const excludedAudioKeys = new Set(Array.isArray(options.excludeAudioKeys) ? options.excludeAudioKeys.map((value) => clean(value)).filter(Boolean) : []);
        const startIndex = Math.max(0, Math.min(Math.max(0, words.length - 1), Math.floor(Number(options.startIndex ?? vocabCurrentIndex) || 0)));
        const wordLimit = Math.max(0, Math.floor(Number(options.wordLimit || options.nodeLimit || options.maxWords || 0) || 0));
        const allowedIndexes = wordLimit
          ? new Set(lessonCachePriorityIndexes(words.length, startIndex).slice(0, wordLimit))
          : null;
        const addTask = (clip, nodeIndex = Number.MAX_SAFE_INTEGER, label = "Vocabulary clip", priorityIndex = null) => {
          const asset = normalizeAudioClip(clip);
          if (!asset || asset.kind === "speak") {
            return;
          }
          const key = audioClipCacheKey(asset);
          if (!key || seen.has(key) || excludedAudioKeys.has(key)) {
            return;
          }
          seen.add(key);
          const row = {
            label,
            nodeIndex,
            run: () => preloadAudioClip(asset, null),
          };
          const priority = Number(priorityIndex);
          if (Number.isFinite(priority)) {
            row.priorityIndex = priority;
          }
          tasks.push(row);
        };
        Object.values(normalizeEffectSounds(normalized.effects || {})).forEach((clip, index) => addTask(clip, -100000 + index, `Vocabulary effect ${index + 1}`, -100000 + index));
        words.forEach((item, nodeIndex) => {
          if (allowedIndexes && !allowedIndexes.has(nodeIndex)) {
            return;
          }
          vocabularyAudioClipsForItem(item, selectedValue, {
            includeAlternates: options.includeAlternates !== false,
            includeMeaning: options.includeMeaning !== false,
          }).forEach((clip, clipIndex) => addTask(clip, nodeIndex, `Vocabulary ${nodeIndex + 1}.${clipIndex + 1}`));
        });
        return tasks;
      };

      const collectSpaceWAudioTasks = (nodes = [], selectedValue = "", effects = {}, options = {}) => {
        const sourceNodes = Array.isArray(nodes) ? nodes : [];
        const tasks = [];
        const embeddedSeen = new Set();
        const ttsSeen = new Set();
        const clipSeen = new Set();
        const mode = clean(options.mode || "");
        const startIndex = Math.max(0, Math.min(Math.max(0, sourceNodes.length - 1), Math.round(Number(options.startIndex ?? currentNodeIndex) || 0)));
        const essentialOnly = Boolean(options.essentialOnly || mode === "essential" || mode === "start");
        const progressiveMode = Boolean(options.progressive || mode === "progressive");
        const includeQuestionAudio = options.includeQuestionAudio !== false;
        const includeSelectedEmbedded = options.includeSelectedEmbedded !== false;
        const includeAllNodes = options.includeAllNodes !== undefined ? Boolean(options.includeAllNodes) : !essentialOnly;
        const includeTts = options.includeTts !== false;
        const includeGrammar = options.includeGrammar !== undefined ? Boolean(options.includeGrammar) : !(essentialOnly || progressiveMode);
        const includeAllEmbedded = options.includeAllEmbedded !== undefined ? Boolean(options.includeAllEmbedded) : !(essentialOnly || progressiveMode);
        const includeEffects = options.includeEffects !== false;
        const nodeLimit = Math.max(0, Math.floor(Number(options.nodeLimit || options.maxNodes || 0) || 0));
        const selectedRaw = clean(selectedValue);
        const cachePriorityEntries = orderNodesForCache(sourceNodes, startIndex);
        const nodePriorityByIndex = new Map(cachePriorityEntries.map(({ index }, priorityIndex) => [index, priorityIndex]));
        let taskPriorityCursor = 0;
        const taskPriority = (nodeIndex = startIndex, slot = 90) => {
          const nodePriority = nodePriorityByIndex.has(nodeIndex)
            ? nodePriorityByIndex.get(nodeIndex)
            : Math.max(1, nodePriorityByIndex.size + 1);
          return (nodePriority * 100000) + (Math.max(0, Math.floor(Number(slot) || 0)) * 1000) + (taskPriorityCursor++);
        };
        const addClipTask = (clip, nodeIndex = startIndex, label = "Lesson clip", slot = 50) => {
          const asset = normalizeAudioClip(clip);
          if (!asset || asset.kind === "speak") {
            return;
          }
          const key = audioClipCacheKey(asset);
          if (!key || clipSeen.has(key)) {
            return;
          }
          clipSeen.add(key);
          tasks.push({
            label,
            nodeIndex,
            priorityIndex: taskPriority(nodeIndex, slot),
            run: () => preloadAudioClip(asset, null, { forceReload: Boolean(options.forceReload) }),
          });
        };
        const addSequenceTasks = (sequence, nodeIndex = startIndex, labelPrefix = "Lesson clip", slot = 50) => {
          normalizeAudioSequence(sequence).forEach((clip, clipIndex) => {
            addClipTask(clip, nodeIndex, `${labelPrefix} ${clipIndex + 1}`, slot);
          });
        };
        const allNodeEntries = includeAllNodes
          ? orderNodesForCache(sourceNodes, startIndex)
          : sourceNodes
            .map((node, index) => ({ node, index }))
            .filter((entry) => entry.node && entry.index === startIndex);
        const nodeEntries = (nodeLimit ? allNodeEntries.slice(0, nodeLimit) : allNodeEntries)
          .filter((entry) => entry.node);
        nodeEntries.forEach(({ node, index: nodeIndex }) => {
          if (includeQuestionAudio) {
            addSequenceTasks(
              node && (node.question_audio ?? node.questionAudio ?? node.vq),
              nodeIndex,
              `Node ${nodeIndex + 1} Vietnamese`,
              10,
            );
          }
          const selectedEmbeddedAsset = selectedRaw.startsWith("embedded:")
            ? findEmbeddedAudioAssetForNode(node, selectedRaw)
            : null;
          if (includeSelectedEmbedded && selectedEmbeddedAsset && selectedEmbeddedAsset.url) {
            const url = serverAssetUrl(selectedEmbeddedAsset.url);
            const key = spaceWUrlAudioCacheKey(url);
            if (key && !embeddedSeen.has(key)) {
              embeddedSeen.add(key);
              tasks.push({
                label: `Selected embedded audio ${nodeIndex + 1}`,
                nodeIndex,
                priorityIndex: taskPriority(nodeIndex, 20),
                run: () => getOrCreateSpaceWUrlAudio(url, selectedEmbeddedAsset.timings || [], {
                  nodeIndex,
                  voice: selectedEmbeddedAsset.voice || selectedEmbeddedAsset.id || "embedded",
                  timeoutMs: 22000,
                }).then((result) => Boolean(result && result.blob instanceof Blob)),
              });
            }
          }
          if (includeAllEmbedded) {
            getEmbeddedAudioAssetsForNode(node).forEach((asset) => {
              if (!asset || !asset.url) {
                return;
              }
              const url = serverAssetUrl(asset.url);
              const key = spaceWUrlAudioCacheKey(url);
              if (!key || embeddedSeen.has(key)) {
                return;
              }
              embeddedSeen.add(key);
              tasks.push({
                label: `Embedded audio ${nodeIndex + 1}`,
                nodeIndex,
                priorityIndex: taskPriority(nodeIndex, 40),
                run: () => getOrCreateSpaceWUrlAudio(url, asset.timings || [], {
                  nodeIndex,
                  voice: asset.voice || asset.id || "embedded",
                  timeoutMs: 22000,
                }).then((result) => Boolean(result && result.blob instanceof Blob)),
              });
            });
          }
          if (includeGrammar) {
            const grammarItems = Array.isArray(node && (node.grammar_questions ?? node.gq ?? node.grammarQuiz))
              ? (node.grammar_questions ?? node.gq ?? node.grammarQuiz)
              : [];
            grammarItems.forEach((item, grammarIndex) => {
              addSequenceTasks(
                item && (item.questionAudio ?? item.question_audio ?? item.qau ?? item.qa),
                nodeIndex,
                `Grammar ${nodeIndex + 1}.${grammarIndex + 1}`,
                50,
              );
              const optionAudio = item && (item.optionAudio ?? item.option_audio ?? item.oa);
              if (optionAudio && typeof optionAudio === "object") {
                Object.values(optionAudio).forEach((value, optionIndex) => {
                  addSequenceTasks(value, nodeIndex, `Grammar option ${nodeIndex + 1}.${grammarIndex + 1}.${optionIndex + 1}`, 60);
                });
              }
              const feedbackAudio = item && (item.feedbackAudio ?? item.feedback_audio ?? item.fb);
              if (feedbackAudio && typeof feedbackAudio === "object") {
                Object.values(feedbackAudio).forEach((value, feedbackIndex) => {
                  addSequenceTasks(value, nodeIndex, `Grammar feedback ${nodeIndex + 1}.${grammarIndex + 1}.${feedbackIndex + 1}`, 70);
                });
              }
            });
          }
        });
        if (includeEffects) {
          Object.values(normalizeEffectSounds(effects || {})).forEach((clip, index) => {
            addClipTask(clip, startIndex, `Lesson effect ${index + 1}`, 80);
          });
        }
        const voiceValue = normalizedCacheVoiceValue(selectedValue);
        if (includeTts && voiceValue) {
          nodeEntries
            .map(({ node, index }) => ({ text: spaceWNodeEnglishText(node), index }))
            .filter((item) => item.text)
            .forEach((item) => {
              const key = spaceWAudioCacheKey(item.text, voiceValue);
              if (!key || ttsSeen.has(key)) {
                return;
              }
              ttsSeen.add(key);
              tasks.push({
                label: `Voice ${item.index + 1}`,
                nodeIndex: item.index,
                priorityIndex: taskPriority(item.index, 30),
                run: () => getOrCreateSpaceWTtsAudio(item.text, voiceValue, { nodeIndex: item.index })
                  .then((result) => Boolean(result && result.blob instanceof Blob)),
              });
            });
        }
        return tasks;
      };

      const prepareSpaceWAudioCacheForStart = async (nodes = [], selectedValue = "", effects = {}, options = {}) => {
        const tasks = prioritizedAudioTasks(
          collectSpaceWAudioTasks(nodes, selectedValue, effects, {
            ...options,
            mode: "essential",
            includeQuestionAudio: true,
            includeSelectedEmbedded: false,
            includeAllNodes: false,
            includeTts: false,
            includeAllEmbedded: false,
            includeGrammar: false,
            includeEffects: false,
          }),
          options.startIndex ?? currentNodeIndex,
        );
        return runLessonAudioPrepareTasks(options.label || "Space_W", tasks, options);
      };

      const prepareQuestionAudioCacheForStart = async (payload = {}, options = {}) => {
        const tasks = prioritizedAudioTasks(
          collectQuestionAudioTasks(payload, {
            startIndex: options.startIndex ?? currentNodeIndex,
            nodeOrder: options.nodeOrder,
            maxNodes: options.maxNodes || 1,
            startQuestionIndex: options.startQuestionIndex,
            questionOrder: options.questionOrder,
            currentQuestionOnly: options.currentQuestionOnly,
            includeEffects: options.includeEffects,
          }),
          options.startIndex ?? currentNodeIndex,
        );
        return runLessonAudioPrepareTasks(options.label || "Space_Q", tasks, options);
      };

      const prepareVocabularyAudioCacheForStart = async (payload = {}, options = {}) => {
        const tasks = prioritizedAudioTasks(
          collectVocabularyAudioTasks(payload, options.selectedValue || selectedVocabVoiceKey(), {
            includeAlternates: false,
            includeMeaning: true,
            ...options,
          }),
          options.startIndex ?? vocabCurrentIndex,
        );
        const maxTasks = Math.max(0, Math.floor(Number(options.maxTasks) || 0));
        return runLessonAudioPrepareTasks(options.label || "Space_V", maxTasks ? tasks.slice(0, maxTasks) : tasks, options);
      };

      const warmSpaceWAudioCacheForLesson = (nodes = [], selectedValue = "", effects = {}, options = {}) => {
        warmAudioTasksInBackground(
          options.label || "Space_W",
          collectSpaceWAudioTasks(nodes, selectedValue, effects, {
            ...options,
            mode: options.mode || "progressive",
          }),
          {
            startIndex: options.startIndex ?? currentNodeIndex,
            delayMs: options.delayMs || 150,
            startDelayMs: options.startDelayMs,
            maxTasks: options.maxTasks || options.taskLimit,
            status: options.status,
          },
        );
      };

      const warmSpaceWAudioCacheForActiveLesson = (nodes = [], selectedValue = "", effects = {}, options = {}) => {
        warmSpaceWAudioCacheForLesson(nodes, selectedValue, effects, {
          ...options,
          mode: options.mode || "progressive",
          delayMs: options.delayMs || 160,
          status: options.status !== undefined ? options.status : false,
        });
      };

      const warmQuestionAudioCacheForLesson = (payload = {}, options = {}) => {
        warmAudioTasksInBackground(
          options.label || "Space_Q",
          collectQuestionAudioTasks(payload, {
            startIndex: options.startIndex ?? currentNodeIndex,
            nodeOrder: options.nodeOrder,
            maxNodes: options.maxNodes || options.nodeLimit,
            startQuestionIndex: options.startQuestionIndex,
            questionOrder: options.questionOrder,
            currentQuestionOnly: options.currentQuestionOnly,
            includeEffects: options.includeEffects,
          }),
          {
            startIndex: options.startIndex ?? currentNodeIndex,
            delayMs: options.delayMs || 150,
            startDelayMs: options.startDelayMs,
            maxTasks: options.maxTasks || options.taskLimit,
            workers: options.workers,
            status: options.status,
          },
        );
      };

      const warmParagraphAudioCacheForLesson = (payload = {}, options = {}) => {
        warmAudioTasksInBackground(
          options.label || "Space_P",
          collectParagraphAudioTasks(payload, {
            startIndex: options.startIndex ?? paragraphNodeIndex,
            startChildIndex: options.startChildIndex ?? paragraphChildIndex,
            nodeOrder: options.nodeOrder,
            maxNodes: options.maxNodes || options.nodeLimit,
            includeEffects: options.includeEffects,
          }),
          {
            startIndex: options.startIndex ?? paragraphNodeIndex,
            delayMs: options.delayMs || 90,
            startDelayMs: options.startDelayMs,
            maxTasks: options.maxTasks || options.taskLimit,
            status: options.status,
          },
        );
      };

      const warmVocabularyAudioCacheForLesson = (payload = {}, options = {}) => {
        warmAudioTasksInBackground(
          options.label || "Space_V",
          collectVocabularyAudioTasks(payload, options.selectedValue || selectedVocabVoiceKey(), {
            includeAlternates: false,
            includeMeaning: true,
            ...options,
          }),
          {
            startIndex: options.startIndex ?? vocabCurrentIndex,
            delayMs: options.delayMs || 55,
            startDelayMs: options.startDelayMs,
            maxTasks: options.maxTasks || options.taskLimit,
            workers: options.workers || 2,
            status: options.status,
          },
        );
      };

      const playBrowserVoice = (text) => {
        if (!("speechSynthesis" in window)) {
          setPlaybackState(false, "Trình duyệt này chưa hỗ trợ Browser Voice.", true);
          return;
        }
        const selectedVoice = getSelectedBrowserVoice();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = (selectedVoice && selectedVoice.lang) || "en-US";
        utterance.voice = selectedVoice;
        utterance.rate = browserSpeechRate();
        utterance.pitch = 1;
        utterance.volume = 1;

        setPlaybackState(true, "Đang phát Browser Voice...");
        const nodeTokens = getCurrentTokens();
        const durationMs = Math.max(Number(currentNode?.duration_ms || 0) || 0, estimateSpeechDuration(text, nodeTokens));
        let boundarySeen = false;
        let speechActive = true;
        highlightTimer = window.setTimeout(() => {
          if (speechActive && !boundarySeen) {
            startTimerHighlight(durationMs);
          }
        }, 220);

        utterance.onboundary = (event) => {
          if (!speechActive) {
            return;
          }
          if (!event || (event.name && event.name !== "word") || typeof event.charIndex !== "number") {
            return;
          }
          const index = tokenIndexForChar(event.charIndex);
          if (!boundarySeen) {
            clearHighlight();
            boundarySeen = true;
          }
          setActiveHighlightIndex(index);
        };

        utterance.onend = () => {
          speechActive = false;
          clearHighlight();
          registerCompletedListen();
          setPlaybackState(false);
        };
        utterance.onerror = () => {
          speechActive = false;
          clearHighlight();
          setPlaybackState(false, "Không phát được voice này, hãy chọn voice khác.", true);
        };

        window.setTimeout(() => window.speechSynthesis.speak(utterance), 40);
      };

      const playBrowserVoiceOnce = (text, options = {}) => new Promise((resolve) => {
        if (!("speechSynthesis" in window)) {
          resolve(false);
          return;
        }
        if (typeof options.shouldPlay === "function" && !options.shouldPlay()) {
          resolve(false);
          return;
        }
        try {
          const selectedVoice = getSelectedBrowserVoice();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = (selectedVoice && selectedVoice.lang) || "en-US";
          utterance.voice = selectedVoice;
          utterance.rate = browserSpeechRate();
          utterance.pitch = 1;
          utterance.volume = 1;
          utterance.onend = () => resolve(true);
          utterance.onerror = () => resolve(false);
          window.setTimeout(() => {
            if (typeof options.shouldPlay === "function" && !options.shouldPlay()) {
              resolve(false);
              return;
            }
            window.speechSynthesis.speak(utterance);
          }, 40);
        } catch (error) {
          resolve(false);
        }
      });

      const playSoundOfText = async (text, voice, options = {}) => {
        setPlaybackState(true, `Đang gọi Sound of Text (${voice})...`);
        let objectUrl = "";
        try {
          const audio = await getOrCreateSpaceWTtsAudio(text, `sot:${voice}`);
          if (!audio || !(audio.blob instanceof Blob)) {
            throw new Error("Sound of Text cache failed.");
          }
          if (typeof options.shouldPlay === "function" && !options.shouldPlay()) {
            setPlaybackState(false);
            return false;
          }
          objectUrl = URL.createObjectURL(audio.blob);
          setTtsStatus(audio.cached
            ? `Playing cached Sound of Text (${voice})...`
            : `Playing and caching Sound of Text (${voice})...`);
          const played = await playAudioUrl(objectUrl, audio.timings, options);
          setPlaybackState(false);
          return played !== false;
        } catch (error) {
          const serverExhausted = clean(error && error.reason).toLowerCase() === "tts_all_generation_failed";
          setPlaybackState(false, serverExhausted
            ? "Worker và Server 2 đều không tạo được audio; đang dùng Browser Voice cuối cùng."
            : "Audio thật đang tạm thời không khả dụng; không dùng giọng trình duyệt thay thế.", true);
          if (serverExhausted) {
            window.setTimeout(() => playBrowserVoice(text), 220);
          }
          return false;
        } finally {
          if (objectUrl) {
            window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
          }
        }
      };

      const playEdgeVoice = async (text, selectedValue, providerLabel = "Edge TTS") => {
        const voice = getEdgeVoiceInfo(selectedValue);
        setPlaybackState(true, `Dang goi ${providerLabel} (${voice ? edgePrettyName(voice.name) : "English"})...`);
        let objectUrl = "";
        try {
          const audio = await getOrCreateSpaceWTtsAudio(text, selectedValue);
          if (!audio || !(audio.blob instanceof Blob)) {
            throw new Error(`${providerLabel} cache failed.`);
          }
          objectUrl = URL.createObjectURL(audio.blob);
          setTtsStatus(audio.cached
            ? `Playing cached ${providerLabel} (${voice ? edgePrettyName(voice.name) : "English"})...`
            : `Playing and caching ${providerLabel} (${voice ? edgePrettyName(voice.name) : "English"})...`);
          await playAudioUrl(objectUrl, audio.timings);
          setPlaybackState(false);
        } catch (error) {
          const serverExhausted = clean(error && error.reason).toLowerCase() === "tts_all_generation_failed";
          setPlaybackState(false, serverExhausted
            ? `${providerLabel}: worker va Server 2 deu that bai; dang dung Browser Voice cuoi cung.`
            : `${providerLabel}: audio that dang tam thoi khong kha dung.`, true);
          if (serverExhausted) {
            window.setTimeout(() => playBrowserVoice(text), 260);
          }
        } finally {
          if (objectUrl) {
            window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
          }
        }
      };

      const selectedGrammarEnglishVoiceValue = () => {
        const selectedValue = clean(voiceSelect.value || "");
        if (selectedValue.startsWith("embedded:")) {
          const asset = findEmbeddedAudioAsset(selectedValue);
          const assetVoice = clean(asset && asset.voice);
          if (/^(sot|edge|microsoft):/i.test(assetVoice)) {
            return assetVoice;
          }
          return "";
        }
        return selectedValue;
      };

      const playGrammarExternalUrlOnce = (url) => new Promise((resolve) => {
        const source = clean(url);
        if (!source) {
          resolve(false);
          return;
        }
        let finished = false;
        const done = (ok = true) => {
          if (finished) {
            return;
          }
          finished = true;
          resolve(ok);
        };
        try {
          const audio = new Audio(source);
          audio.preload = "auto";
          normalizeAudioPlaybackSpeed(audio);
          audio.volume = 0.94;
          activeGrammarAudio = { audio, done };
          audio.onended = () => done(true);
          audio.onerror = () => done(false);
          const started = audio.play();
          if (started && typeof started.catch === "function") {
            started.catch(() => done(false));
          }
        } catch (error) {
          done(false);
        }
      });

      const speakGrammarBrowserText = (text) => new Promise((resolve) => {
        if (!("speechSynthesis" in window) || !clean(text)) {
          resolve(false);
          return;
        }
        let finished = false;
        const done = (ok = true) => {
          if (finished) {
            return;
          }
          finished = true;
          resolve(ok);
        };
        try {
          const selectedVoice = getSelectedBrowserVoice();
          const utterance = new SpeechSynthesisUtterance(clean(text));
          utterance.lang = (selectedVoice && selectedVoice.lang) || "en-US";
          utterance.voice = selectedVoice;
          utterance.rate = browserSpeechRate();
          utterance.pitch = 1;
          utterance.volume = 1;
          utterance.onend = () => done(true);
          utterance.onerror = () => done(false);
          activeGrammarAudio = {
            audio: {
              pause: () => window.speechSynthesis.cancel(),
              currentTime: 0,
            },
            done,
          };
          window.speechSynthesis.speak(utterance);
        } catch (error) {
          done(false);
        }
      });

      const playSelectedEnglishGrammarText = async (text, fallbackSequence = [], options = {}) => {
        const phrase = clean(text);
        if (!phrase) {
          return false;
        }
        const stopToken = Number(options.stopToken || 0) || 0;
        const currentStopToken = typeof options.currentStopToken === "function" ? options.currentStopToken : null;
        const isCancelled = () => Boolean(stopToken && currentStopToken && Number(currentStopToken() || 0) !== stopToken);
        const selectedValue = selectedGrammarEnglishVoiceValue();
        let ok = false;
        if (selectedValue.startsWith("sot:")) {
          let audioUrl = "";
          try {
            if (isCancelled()) {
              return false;
            }
            const audio = await getOrCreateSpaceWTtsAudio(phrase, selectedValue);
            if (!audio || !(audio.blob instanceof Blob)) {
              throw new Error("Sound of Text cache failed.");
            }
            if (isCancelled()) {
              return false;
            }
            audioUrl = URL.createObjectURL(audio.blob);
            ok = await playGrammarExternalUrlOnce(audioUrl);
          } catch (error) {
            ok = false;
          } finally {
            if (audioUrl) {
              window.setTimeout(() => URL.revokeObjectURL(audioUrl), 1000);
            }
          }
        } else if (selectedValue.startsWith("edge:") || selectedValue.startsWith("microsoft:")) {
          let audioUrl = "";
          try {
            if (isCancelled()) {
              return false;
            }
            const audio = await getOrCreateSpaceWTtsAudio(phrase, selectedValue);
            if (!audio || !(audio.blob instanceof Blob)) {
              throw new Error("Microsoft cache failed.");
            }
            if (isCancelled()) {
              return false;
            }
            audioUrl = URL.createObjectURL(audio.blob);
            ok = await playGrammarExternalUrlOnce(audioUrl);
          } catch (error) {
            ok = false;
          } finally {
            if (audioUrl) {
              window.setTimeout(() => URL.revokeObjectURL(audioUrl), 1000);
            }
          }
        } else {
          if (isCancelled()) {
            return false;
          }
          ok = await speakGrammarBrowserText(phrase);
        }
        if (!ok && Array.isArray(fallbackSequence) && fallbackSequence.length) {
          let fallbackOk = false;
          for (const clip of fallbackSequence) {
            fallbackOk = Boolean(await playAudioClipOnce(clip, { trackGrammar: true, volume: 0.94 })) || fallbackOk;
          }
          return fallbackOk;
        }
        return ok;
      };

      const playEnglish = async () => {
        const text = clean(englishNode.textContent);
        if (!text) {
          setTtsStatus("Chưa có câu tiếng Anh để phát.", true);
          return;
        }
        stopGrammarAudio();
        stopSpeakReplay();
        stopActiveAudio();
        const selectedValue = voiceSelect.value || "";
        if (selectedValue === "embedded" || selectedValue.startsWith("embedded:")) {
          const asset = selectedValue.startsWith("embedded:") ? findEmbeddedAudioAsset(selectedValue) : null;
          const audioUrl = getEmbeddedAudioUrl(asset);
          if (!audioUrl) {
            setTtsStatus("Node này chưa có audio nhúng.", true);
            return;
          }
          setPlaybackState(true, `Đang phát voice nhúng${asset && asset.label ? `: ${asset.label}` : ""}...`);
          let objectUrl = "";
          try {
            let timings = asset && Array.isArray(asset.timings) ? asset.timings : null;
            let playbackUrl = audioUrl;
            if (!/^data:|^blob:/i.test(audioUrl)) {
              const cached = await getOrCreateSpaceWUrlAudio(audioUrl, timings || [], {
                voice: asset && (asset.voice || asset.id),
                nodeIndex: currentNodeIndex,
                timeoutMs: 16000,
              });
              if (cached && cached.blob instanceof Blob) {
                objectUrl = URL.createObjectURL(cached.blob);
                playbackUrl = objectUrl;
                timings = cached.timings || timings;
                setTtsStatus(cached.cached ? "Playing cached embedded voice..." : "Playing and caching embedded voice...");
              }
            }
            await playAudioUrl(playbackUrl, timings);
            setPlaybackState(false);
          } catch (error) {
            setPlaybackState(false, "Không phát được audio nhúng trong file này.", true);
          } finally {
            if (objectUrl) {
              window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
            }
          }
          return;
        }
        if (selectedValue.startsWith("sot:")) {
          await playSoundOfText(text, selectedValue.slice(4) || "en-US");
          return;
        }
        if (selectedValue.startsWith("edge:")) {
          await playEdgeVoice(text, selectedValue);
          return;
        }
        if (selectedValue.startsWith("microsoft:")) {
          await playEdgeVoice(text, selectedValue, "Microsoft");
          return;
        }
        playBrowserVoice(text);
      };

      const triggerNextAttention = () => {
        if (!nextButton) {
          return;
        }
        if (nextAttentionTimer) {
          window.clearTimeout(nextAttentionTimer);
          nextAttentionTimer = 0;
        }
        nextButton.classList.remove("is-attention");
        void nextButton.offsetWidth;
        nextButton.classList.add("is-attention");
        nextAttentionTimer = window.setTimeout(() => {
          nextButton.classList.remove("is-attention");
          nextAttentionTimer = 0;
        }, 2600);
      };

      const updateNextButton = (canShow = nextPanelCanShow) => {
        nextPanelCanShow = Boolean(canShow);
        const wasVisible = !nextButton.classList.contains("is-hidden");
        const wasReady = nextButton.classList.contains("is-ready");
        const hasLesson = lessonNodes.length > 0 && !reviewFinished;
        const hasNext = hasNextNode();
        const required = requiredListenCount();
        const listenReady = completedListenCount >= required;
        const flowReady = nextPanelCanShow && listenReady;
        const speakReady = isReviewPhase() ? reviewSpeakCompleted : speakStepCompleted;
        const isStartingReview = reviewCanStart();
        const shouldShow = Boolean(nextPanelCanShow && hasLesson && flowReady);
        const canAdvance = Boolean(shouldShow && hasNext && listenReady && speakReady);
        nextButton.classList.toggle("is-hidden", !shouldShow);
        nextButton.classList.toggle("is-ready", canAdvance);
        nextButton.disabled = !canAdvance;
        if (shouldShow && (!wasVisible || (!wasReady && canAdvance))) {
          triggerNextAttention();
        } else if (!shouldShow) {
          nextButton.classList.remove("is-attention");
          if (nextAttentionTimer) {
            window.clearTimeout(nextAttentionTimer);
            nextAttentionTimer = 0;
          }
        }
        if (!hasNext) {
          nextButton.textContent = "Done";
        } else if (!listenReady) {
          nextButton.textContent = `Nghe ${Math.min(required, completedListenCount)}/${required}`;
        } else if (!speakReady) {
          nextButton.textContent = "Speak 0/1";
        } else if (isStartingReview) {
          nextButton.textContent = "Bắt đầu ôn";
        } else if (isReviewPhase() && !reviewQueue.length && !reviewCurrentHadError) {
          nextButton.textContent = "Hoàn tất";
        } else {
          nextButton.textContent = "Next";
        }
        nextButton.title = hasNext && (!listenReady || !speakReady) ? listenStatusText() : "";
        syncMobilePanelTabs();
        updateSpaceWProgressLabel();
        updateSpaceWTokenSupportVisibility();
      };

      const normalizeWord = (value) => clean(value)
        .toLowerCase()
        .replace(/[’']/g, "")
        .replace(/[^a-z0-9]+/g, "");

      const getNodeScoringWords = (node = currentNode) => {
        const explicit = node && (node.scoring ?? node.sc ?? node.score_words);
        if (Array.isArray(explicit) && explicit.length) {
          return explicit
            .map((item) => ({
              text: clean(item.t ?? item.text ?? ""),
              norm: normalizeWord(item.n ?? item.t ?? item.text ?? ""),
              ipa: tokenIpaForAccent(item, currentAccent),
              lemma: clean(item.l ?? item.lemma ?? ""),
              pos: clean(item.p ?? item.pos ?? ""),
              dep: clean(item.d ?? item.dep ?? ""),
              head: clean(item.h ?? item.head ?? ""),
              meaning: clean(item.m ?? item.meaning ?? item.viet ?? ""),
            }))
            .filter((item) => item.text && item.norm);
        }
        const en = clean(node && (node.en ?? node.e ?? englishNode.textContent));
        return Array.from(en.matchAll(/[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?/g))
          .map((match) => ({
            text: match[0],
            norm: normalizeWord(match[0]),
            ipa: "",
            lemma: match[0].toLowerCase(),
            pos: "",
            dep: "",
            head: "",
            meaning: "",
          }))
          .filter((item) => item.norm);
      };

      const SPACE_W_SCORING_TOKEN_VOICE = "sot:en-GB";

      const spaceWScoringAudioWordsForNode = (node = currentNode) => {
        const seen = new Set();
        return getNodeScoringWords(node)
          .map((item, index) => ({
            text: clean(item.text || ""),
            norm: normalizeWord(item.norm || item.text || ""),
            index,
          }))
          .filter((item) => {
            if (!item.text || !item.norm || seen.has(item.norm)) {
              return false;
            }
            seen.add(item.norm);
            return true;
          });
      };

      const prepareSpaceWScoringAudioToken = (chip, word = "", index = 0) => {
        const text = clean(word);
        if (!chip || !text) {
          return;
        }
        chip.classList.add("is-audio-token");
        chip.dataset.audioWord = text;
        chip.dataset.audioIndex = String(Number(index) || 0);
        chip.setAttribute("role", "button");
        chip.tabIndex = 0;
        chip.title = `${chip.title ? `${chip.title} | ` : ""}Click to hear UK audio.`;
        chip.onclick = (event) => {
          event.preventDefault();
          event.stopPropagation();
          void playSpaceWScoringTokenAudio(text, chip);
        };
        chip.onkeydown = (event) => {
          if (event.key !== "Enter" && event.key !== " ") {
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          void playSpaceWScoringTokenAudio(text, chip);
        };
      };

      const stopSpaceWScoringTokenAudio = () => {
        const audio = spaceWScoringTokenAudio;
        if ("speechSynthesis" in window) {
          try {
            window.speechSynthesis.cancel();
          } catch (error) {
          }
        }
        if (speakUserTokenClipAudio) {
          try {
            speakUserTokenClipAudio.pause();
            speakUserTokenClipAudio.onloadedmetadata = null;
            speakUserTokenClipAudio.onplay = null;
            speakUserTokenClipAudio.onended = null;
            speakUserTokenClipAudio.onerror = null;
            speakUserTokenClipAudio.removeAttribute("src");
            speakUserTokenClipAudio.load();
          } catch (error) {
          }
          speakUserTokenClipAudio = null;
        }
        if (!audio) {
          return;
        }
        try {
          audio.pause();
          audio.onended = null;
          audio.onerror = null;
          audio.removeAttribute("src");
          audio.load();
        } catch (error) {
        }
        spaceWScoringTokenAudio = null;
      };

      const playSpaceWScoringCachedUkAudio = (text = "", chip = null) => new Promise((resolve) => {
        const word = clean(text);
        if (!word) {
          resolve(false);
          return;
        }
        const url = spaceWScoringServerAudioUrl(word);
        void (async () => {
          let objectUrl = "";
          try {
            const cached = await getOrCreateSpaceWUrlAudio(url, [], {
              voice: SPACE_W_SCORING_TOKEN_VOICE,
              nodeIndex: currentNodeIndex,
              timeoutMs: 9000,
            });
            const playUrl = cached && cached.blob instanceof Blob
              ? URL.createObjectURL(cached.blob)
              : url;
            objectUrl = /^blob:/i.test(playUrl) ? playUrl : "";
            const player = new Audio(playUrl);
          spaceWScoringTokenAudio = player;
          player.preload = "auto";
          normalizeAudioPlaybackSpeed(player);
          let settled = false;
          const timeoutId = window.setTimeout(() => {
            if (settled) {
              return;
            }
            settled = true;
            try {
              player.pause();
              player.removeAttribute("src");
              player.load();
            } catch (error) {
            }
            if (spaceWScoringTokenAudio === player) {
              spaceWScoringTokenAudio = null;
            }
            if (objectUrl) {
              window.setTimeout(() => URL.revokeObjectURL(objectUrl), 500);
              objectUrl = "";
            }
            resolve(false);
          }, 4500);
          const finish = (ok) => {
            if (settled) {
              return;
            }
            settled = true;
            window.clearTimeout(timeoutId);
            if (spaceWScoringTokenAudio === player) {
              spaceWScoringTokenAudio = null;
            }
            if (chip) {
              chip.classList.remove("is-audio-loading", "is-audio-playing");
            }
            if (objectUrl) {
              window.setTimeout(() => URL.revokeObjectURL(objectUrl), 500);
              objectUrl = "";
            }
            resolve(Boolean(ok));
          };
          player.onplay = () => {
            if (chip) {
              chip.classList.remove("is-audio-loading");
              chip.classList.add("is-audio-playing");
            }
          };
          player.onended = () => finish(true);
          player.onerror = () => finish(false);
          const started = player.play();
          if (started && typeof started.catch === "function") {
            started.catch(() => finish(false));
          }
          } catch (error) {
          if (chip) {
            chip.classList.remove("is-audio-loading", "is-audio-playing");
          }
          resolve(false);
          }
        })();
      });

      // Added 2026-07-14: warms Space_W scoring word chips through Server 2's QMLearn audio index instead of generating SOT blobs.
      const spaceWScoringServerAudioUrl = (word = "") => {
        const text = clean(word);
        return text
          ? `/server-data/qm-sound?word=${encodeURIComponent(text)}&voice=${encodeURIComponent(SPACE_W_SCORING_TOKEN_VOICE)}`
          : "";
      };

      const prefetchSpaceWScoringServerAudio = (word = "") => {
        const url = spaceWScoringServerAudioUrl(word);
        if (!url) {
          return false;
        }
        try {
          void getOrCreateSpaceWUrlAudio(url, [], {
            voice: SPACE_W_SCORING_TOKEN_VOICE,
            nodeIndex: currentNodeIndex,
            timeoutMs: 9000,
          }).catch(() => {});
          return true;
        } catch (error) {
          return false;
        }
      };

      const warmSpaceWRemainingScoringTokenAudio = (clickedWord = "") => {
        const words = spaceWScoringAudioWordsForNode(currentNode);
        const clickedNorm = normalizeWord(clickedWord);
        const remaining = words.filter((item) => item.norm && item.norm !== clickedNorm);
        if (!remaining.length) {
          return;
        }
        const warmKey = [
          currentSpaceWCache.identity || hashSpaceWText(clean(currentLessonSource.title || currentLessonSource.name || "space-w")),
          currentNodeIndex,
          SPACE_W_SCORING_TOKEN_VOICE,
          remaining.map((item) => item.norm).join("|"),
        ].join(":");
        if (spaceWScoringTokenAudioWarmKey === warmKey) {
          return;
        }
        spaceWScoringTokenAudioWarmKey = warmKey;
        void (async () => {
          let cached = 0;
          for (const item of remaining.slice(0, 8)) {
            try {
              if (prefetchSpaceWScoringServerAudio(item.text)) {
                cached += 1;
              }
            } catch (error) {
            }
            await delay(35);
          }
          if (cached && speakPanel && speakPanel.classList.contains("is-live")) {
            setSpeakStatus(`Warmed UK audio index for ${cached}/${remaining.length} remaining token${remaining.length === 1 ? "" : "s"}.`, "ok");
          }
        })();
      };

      const warmSpaceWScoringTokenAudioSilently = (word = "") => {
        const text = clean(word);
        if (!text) {
          return;
        }
        prefetchSpaceWScoringServerAudio(text);
      };

      const clearSpeakReplayTokenHighlight = () => {
        if (speakReplayHighlightFrame) {
          window.cancelAnimationFrame(speakReplayHighlightFrame);
          speakReplayHighlightFrame = 0;
        }
        if (speakWordsNode) {
          speakWordsNode.querySelectorAll(".ft-speak-word.is-replay-highlight").forEach((node) => {
            node.classList.remove("is-replay-highlight");
          });
        }
      };

      const clearSpeakAutoReplayTimer = () => {
        if (speakAutoReplayTimer) {
          window.clearTimeout(speakAutoReplayTimer);
          speakAutoReplayTimer = 0;
        }
      };

      const speakBrowserPlaybackAnchorMs = (item = {}) => {
        const startMs = Math.max(0, Number(item.startMs || item.detectedMs || 0) || 0);
        const endMs = Math.max(startMs, Number(item.endMs || item.detectedMs || startMs) || startMs);
        if (item && item.source === "server") {
          return Math.max(0, startMs + ((endMs - startMs) * 0.5));
        }
        return Math.max(0, Number(item.detectedMs || startMs || 0) - 850);
      };

      const speakTimelineIsActive = (item = {}, ms = 0) => {
        if (item && item.source === "server") {
          const startMs = Math.max(0, Number(item.startMs || item.detectedMs || 0) || 0);
          const endMs = Math.max(startMs, Number(item.endMs || item.detectedMs || startMs) || startMs);
          return ms >= Math.max(0, startMs - 80) && ms <= endMs + 160;
        }
        const anchorMs = speakBrowserPlaybackAnchorMs(item);
        return ms >= Math.max(0, anchorMs - 160) && ms <= anchorMs + 860;
      };

      const speakBrowserTimelineFor = (word = "", index = null) => {
        const norm = normalizeWord(word);
        const wantedIndex = Number(index);
        return (speakBrowserTokenTimeline || []).find((item) => (
          Number.isFinite(wantedIndex) && Number(item.index) === wantedIndex
        )) || (speakBrowserTokenTimeline || []).find((item) => item.norm && item.norm === norm) || null;
      };

      const rememberBrowserSpeakTokenTimeline = (payload = {}, elapsedMs = 0) => {
        const rows = Array.isArray(payload.details) ? payload.details : [];
        const ms = Math.max(0, Math.round(Number(elapsedMs) || 0));
        rows.forEach((row) => {
          if (!row || !row.ok) {
            return;
          }
          const word = clean(row.expected || row.text || "");
          const norm = normalizeWord(word);
          const index = Number(row.index);
          if (!word || !norm || !Number.isFinite(index)) {
            return;
          }
          const existing = speakBrowserTokenTimeline.find((item) => Number(item.index) === index || item.norm === norm);
          if (existing) {
            const detectedMs = Number(existing.detectedMs || existing.startMs || 0);
            if (ms <= detectedMs + 1200) {
              existing.endMs = Math.max(Number(existing.endMs || 0), ms + 350);
            }
            return;
          }
          speakBrowserTokenTimeline.push({
            index,
            word,
            norm,
            source: "browser",
            startMs: Math.max(0, ms - 350),
            endMs: ms + 350,
            detectedMs: ms,
          });
        });
      };

      const rememberServerSpeakTokenTimeline = (payload = {}) => {
        const rows = Array.isArray(payload.details) ? payload.details : [];
        const next = [];
        rows.forEach((row, rowIndex) => {
          if (!row || !row.ok) {
            return;
          }
          const word = clean(row.expected || row.text || "");
          const norm = normalizeWord(word);
          const index = Number.isFinite(Number(row.index)) ? Number(row.index) : rowIndex;
          const startMs = Math.max(0, Number(row.start_ms ?? row.startMs ?? row.start ?? 0) || 0);
          const endMs = Math.max(startMs, Number(row.end_ms ?? row.endMs ?? row.end ?? startMs) || startMs);
          if (!word || !norm || !Number.isFinite(index) || (!startMs && !endMs)) {
            return;
          }
          next.push({
            index,
            word,
            norm,
            source: "server",
            startMs,
            endMs,
            detectedMs: speakBrowserPlaybackAnchorMs({ source: "server", startMs, endMs }),
          });
        });
        if (next.length) {
          speakBrowserTokenTimeline = next;
          clearSpeakReplayTokenHighlight();
        }
      };

      const syncSpeakReplayTokenHighlight = (audio) => {
        clearSpeakReplayTokenHighlight();
        if (!audio || !speakWordsNode || !speakBrowserTokenTimeline.length) {
          return;
        }
        const tick = () => {
          if (!audio || audio.paused || audio.ended) {
            clearSpeakReplayTokenHighlight();
            return;
          }
          const ms = Number(audio.currentTime || 0) * 1000;
          const active = speakBrowserTokenTimeline
            .filter((item) => speakTimelineIsActive(item, ms))
            .sort((a, b) => Math.abs(ms - speakBrowserPlaybackAnchorMs(a)) - Math.abs(ms - speakBrowserPlaybackAnchorMs(b)))[0];
          const activeIndex = active ? String(active.index) : "";
          speakWordsNode.querySelectorAll(".ft-speak-word").forEach((node) => {
            node.classList.toggle("is-replay-highlight", Boolean(activeIndex) && String(node.dataset.speakIndex || "") === activeIndex);
          });
          speakReplayHighlightFrame = window.requestAnimationFrame(tick);
        };
        speakReplayHighlightFrame = window.requestAnimationFrame(tick);
      };

      const playSpeakUserTimelineClip = (word = "", index = null) => new Promise((resolve) => {
        const item = speakBrowserTimelineFor(word, index);
        if (!item || !speakRecordedBlob) {
          resolve(false);
          return;
        }
        clearSpeakAutoReplayTimer();
        if (speakReplayAudio || speakReplayBufferSource) {
          stopSpeakReplay();
        }
        const anchorMs = speakBrowserPlaybackAnchorMs(item);
        const clipStartSec = Math.max(0, (anchorMs - 350) / 1000);
        const clipEndSec = Math.max(clipStartSec + 0.45, (anchorMs + 350) / 1000);
        try {
          if (speakUserTokenClipAudio) {
            try { speakUserTokenClipAudio.pause(); } catch (error) {}
            speakUserTokenClipAudio = null;
          }
          const url = ensureSpeakRecordingUrl();
          if (!url) {
            resolve(false);
            return;
          }
          const audio = new Audio(url);
          speakUserTokenClipAudio = audio;
          normalizeAudioPlaybackSpeed(audio);
          let stopTimer = 0;
          const cleanup = (ok) => {
            if (stopTimer) {
              window.clearTimeout(stopTimer);
              stopTimer = 0;
            }
            if (speakUserTokenClipAudio === audio) {
              speakUserTokenClipAudio = null;
            }
            resolve(Boolean(ok));
          };
          const stopAtClipEnd = () => {
            if (Number(audio.currentTime || 0) >= clipEndSec) {
              try { audio.pause(); } catch (error) {}
              cleanup(true);
            }
          };
          audio.onplay = () => {
            const ms = Math.max(550, (clipEndSec - clipStartSec) * 1000);
            stopTimer = window.setTimeout(() => {
              try { audio.pause(); } catch (error) {}
              cleanup(true);
            }, ms);
          };
          audio.ontimeupdate = stopAtClipEnd;
          audio.onended = () => cleanup(true);
          audio.onerror = () => cleanup(false);
          audio.onloadedmetadata = () => {
            try {
              const safeDuration = Math.max(0, Number(audio.duration || clipStartSec) - 0.05);
              audio.currentTime = Math.min(clipStartSec, safeDuration);
            } catch (error) {
            }
            const started = audio.play();
            if (started && typeof started.catch === "function") {
              started.catch(() => cleanup(false));
            }
          };
          audio.load();
        } catch (error) {
          resolve(false);
        }
      });

      const playSpaceWScoringTokenAudio = async (word = "", chip = null) => {
        const text = clean(word);
        if (!text) {
          return false;
        }
        const timelineIndex = chip && chip.dataset ? Number(chip.dataset.speakIndex ?? chip.dataset.audioIndex) : NaN;
        const isSpeakScoringToken = Boolean(chip && speakWordsNode && speakWordsNode.contains(chip));
        if (isSpeakScoringToken) {
          clearSpeakAutoReplayTimer();
          if (speakReplayAudio || speakReplayBufferSource) {
            stopSpeakReplay();
          }
        }
        stopSpaceWScoringTokenAudio();
        if (chip) {
          chip.classList.add("is-audio-loading");
          chip.classList.remove("is-audio-playing");
        }
        setSpeakStatus(`Preparing UK audio for "${text}"...`, "");
        const localPlayed = await playSpaceWScoringCachedUkAudio(text, chip);
        if (localPlayed) {
          warmSpaceWRemainingScoringTokenAudio(text);
          if (isSpeakScoringToken) {
            await playSpeakUserTimelineClip(text, timelineIndex);
          }
          setSpeakStatus(`Played UK audio for "${text}".`, "ok");
          return true;
        }
        warmSpaceWScoringTokenAudioSilently(text);
        warmSpaceWRemainingScoringTokenAudio(text);
        let objectUrl = "";
        try {
          const audioRecord = await getOrCreateSpaceWTtsAudio(text, SPACE_W_SCORING_TOKEN_VOICE, { nodeIndex: currentNodeIndex });
          if (!audioRecord || !(audioRecord.blob instanceof Blob)) {
            throw new Error("No token audio returned.");
          }
          objectUrl = URL.createObjectURL(audioRecord.blob);
          const player = new Audio(objectUrl);
          spaceWScoringTokenAudio = player;
          player.preload = "auto";
          normalizeAudioPlaybackSpeed(player);
          player.onplay = () => {
            if (chip) {
              chip.classList.remove("is-audio-loading");
              chip.classList.add("is-audio-playing");
            }
            warmSpaceWRemainingScoringTokenAudio(text);
          };
          const cleanup = () => {
            if (spaceWScoringTokenAudio === player) {
              spaceWScoringTokenAudio = null;
            }
            if (chip) {
              chip.classList.remove("is-audio-loading", "is-audio-playing");
            }
            if (objectUrl) {
              window.setTimeout(() => URL.revokeObjectURL(objectUrl), 500);
              objectUrl = "";
            }
          };
          player.onended = () => {
            cleanup();
            setSpeakStatus(`Played UK audio for "${text}".`, "ok");
          };
          player.onerror = () => {
            cleanup();
            setSpeakStatus(`Could not play UK audio for "${text}".`, "error");
          };
          setSpeakStatus(audioRecord.cached ? `Playing cached UK audio for "${text}"...` : `Playing and caching UK audio for "${text}"...`, "");
          if (isSpeakScoringToken) {
            player.addEventListener("ended", () => {
              void playSpeakUserTimelineClip(text, timelineIndex);
            }, { once: true });
          }
          const started = player.play();
          if (started && typeof started.catch === "function") {
            await started;
          }
          return true;
        } catch (error) {
          warmSpaceWRemainingScoringTokenAudio(text);
          if (chip) {
            chip.classList.remove("is-audio-loading", "is-audio-playing");
          }
          if (objectUrl) {
            URL.revokeObjectURL(objectUrl);
          }
          setSpeakStatus(error && error.message ? error.message : `Could not prepare UK audio for "${text}".`, "error");
          return false;
        }
      };

      const spaceWScoringAudioTokenFromEvent = (event) => {
        const target = event && event.target && event.target.closest
          ? event.target.closest(".ft-score-word.is-audio-token, .ft-speak-word.is-audio-token")
          : null;
        if (!target) {
          return null;
        }
        if (scoreWordsNode && scoreWordsNode.contains(target)) {
          return target;
        }
        if (speakWordsNode && speakWordsNode.contains(target)) {
          return target;
        }
        return null;
      };

      const handleSpaceWScoringAudioTokenClick = (event) => {
        const token = spaceWScoringAudioTokenFromEvent(event);
        if (!token) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        void playSpaceWScoringTokenAudio(token.dataset.audioWord || token.textContent || "", token);
      };

      const handleSpaceWScoringAudioTokenKeydown = (event) => {
        if (!event || (event.key !== "Enter" && event.key !== " ")) {
          return;
        }
        const token = spaceWScoringAudioTokenFromEvent(event);
        if (!token) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        void playSpaceWScoringTokenAudio(token.dataset.audioWord || token.textContent || "", token);
      };

      const spaceWTextNodesUnder = (root) => {
        const nodes = [];
        if (!root) {
          return nodes;
        }
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
          acceptNode: (node) => clean(node && node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT,
        });
        let node = walker.nextNode();
        while (node) {
          nodes.push(node);
          node = walker.nextNode();
        }
        return nodes;
      };

      const spaceWTextWordAtPoint = (event, root) => {
        if (!event || !root) {
          return "";
        }
        let textNode = null;
        let offset = 0;
        try {
          if (document.caretPositionFromPoint) {
            const position = document.caretPositionFromPoint(event.clientX, event.clientY);
            textNode = position && position.offsetNode;
            offset = Number(position && position.offset) || 0;
          } else if (document.caretRangeFromPoint) {
            const range = document.caretRangeFromPoint(event.clientX, event.clientY);
            textNode = range && range.startContainer;
            offset = Number(range && range.startOffset) || 0;
          }
        } catch (error) {
          textNode = null;
        }
        const nodes = spaceWTextNodesUnder(root);
        if (!nodes.length) {
          return "";
        }
        if (!textNode || !root.contains(textNode)) {
          const fallback = clean(event.target && event.target.textContent);
          const match = fallback.match(/[A-Za-z0-9]+(?:['\u2019][A-Za-z0-9]+)?/);
          return match ? match[0] : "";
        }
        let absolute = 0;
        for (const node of nodes) {
          if (node === textNode) {
            absolute += Math.max(0, Math.min(String(node.nodeValue || "").length, offset));
            break;
          }
          absolute += String(node.nodeValue || "").length;
        }
        const fullText = nodes.map((node) => String(node.nodeValue || "")).join("");
        if (!fullText) {
          return "";
        }
        const left = fullText.slice(0, absolute);
        const right = fullText.slice(absolute);
        const leftMatch = left.match(/[A-Za-z0-9]+(?:['\u2019][A-Za-z0-9]+)?$/);
        const rightMatch = right.match(/^[A-Za-z0-9]+(?:['\u2019][A-Za-z0-9]+)?/);
        return clean(`${leftMatch ? leftMatch[0] : ""}${rightMatch ? rightMatch[0] : ""}`);
      };

      const handleSpaceWUnlockedTextAudioClick = (event) => {
        const roots = [hintText, aboutQuestion, aboutAnswer].filter(Boolean);
        const root = roots.find((node) => node.contains(event.target));
        if (!root) {
          return;
        }
        const word = spaceWTextWordAtPoint(event, root);
        if (!word || !normalizeWord(word)) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        void playSpaceWScoringTokenAudio(word, null);
      };

      const currentSpaceWScoreHintWord = () => {
        const token = scoreWordsNode && (
          scoreWordsNode.querySelector(".ft-score-word.is-timeout-hint.is-audio-token") ||
          scoreWordsNode.querySelector(".ft-score-word.is-current") ||
          scoreWordsNode.querySelector(".ft-score-word.is-audio-token")
        );
        if (token) {
          return clean(token.dataset.audioWord || token.textContent || "");
        }
        const result = scoreInputWords(answerInput ? answerInput.value : "");
        const issue = result && result.firstIssue;
        return clean(issue && issue.text || "");
      };

      const handleSpaceWScoreHintAudioClick = (event) => {
        if (!event || !scorePanel || !scorePanel.classList.contains("is-live")) {
          return;
        }
        const target = event.target;
        if (
          !(scoreHint && scoreHint.contains(target)) &&
          !(scoreMessage && scoreMessage.contains(target))
        ) {
          return;
        }
        const word = currentSpaceWScoreHintWord();
        if (!word || !normalizeWord(word)) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        void playSpaceWScoringTokenAudio(word, null);
      };

      const scoreInputWords = (rawInput, words = getNodeScoringWords()) => {
        const typedWords = Array.from(clean(rawInput).matchAll(/[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?/g)).map((match) => ({
          text: match[0],
          norm: normalizeWord(match[0]),
          start: match.index,
          end: match.index + match[0].length,
        }));
        const details = words.map((word, index) => {
          const typed = typedWords[index] || null;
          const ok = Boolean(typed && typed.norm === word.norm);
          return { ...word, typed: typed ? typed.text : "", typedStart: typed ? typed.start : -1, typedEnd: typed ? typed.end : -1, ok, index };
        });
        const correct = details.filter((item) => item.ok).length;
        const score = words.length ? Math.round((correct / words.length) * 100) : 0;
        const firstIssue = details.find((item) => !item.ok) || null;
        return {
          words,
          typedWords,
          details,
          correct,
          score,
          firstIssue,
          complete: Boolean(words.length) && correct === words.length && typedWords.length === words.length,
          extraCount: Math.max(0, typedWords.length - words.length),
        };
      };

      const readSpeakAiCheckPreference = () => {
        try {
          const value = localStorage.getItem(SPACE_W_SPEAK_AI_CHECK_KEY);
          if (value === "0" || value === "off" || value === "browser") return false;
          if (value === "1" || value === "on" || value === "ai") return true;
        } catch (error) {
        }
        // Whisper is opt-in; a missing preference must never gate Record on server AI.
        return false;
      };

      const writeSpeakAiCheckPreference = (enabled) => {
        try {
          localStorage.setItem(SPACE_W_SPEAK_AI_CHECK_KEY, enabled ? "1" : "0");
        } catch (error) {
        }
      };

      const browserSpeechRecognitionCtor = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;

      const syncSpeakModeUi = () => {
        const browserMode = !speakAiCheckVoice;
        if (speakModeToggleButton) {
          speakModeToggleButton.classList.toggle("is-browser", browserMode);
          speakModeToggleButton.setAttribute("aria-pressed", speakAiCheckVoice ? "true" : "false");
          speakModeToggleButton.disabled = false;
          speakModeToggleButton.title = speakAiCheckVoice
            ? "AI check voice ON: send recording to server speech analysis."
            : (speakAiCheckVoiceFallbackActive ? "Whisper connection failed. This session is using browser live voice check." : (speakAiCheckVoiceServerManaged ? "Server setting: Space_W Whisper is OFF, so browser live check is forced." : "AI check voice OFF: use browser live speech recognition."));
        }
        if (speakModeLabel) {
          speakModeLabel.textContent = speakAiCheckVoice
            ? (speakAiCheckVoiceServerAllowsWhisper ? "ON - server analysis" : "SERVER BLOCKED")
            : (speakAiCheckVoiceFallbackActive ? "FALLBACK - browser live check" : (speakAiCheckVoiceServerManaged ? "SERVER OFF - browser live check" : "OFF - browser live check"));
        }
        if (speakReplayButton && browserMode && speakRecognitionActive) {
          speakReplayButton.disabled = true;
        }
      };

      const setSpeakAiCheckVoice = (enabled, persist = true) => {
        speakAiCheckVoice = Boolean(enabled);
        if (persist) {
          writeSpeakAiCheckPreference(speakAiCheckVoice);
        }
        syncSpeakModeUi();
      };

      const scoreSpeakLooseTranscript = (rawInput, words = getNodeScoringWords()) => {
        const spokenWords = Array.from(clean(rawInput).matchAll(/[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?/g)).map((match) => ({
          text: match[0],
          norm: normalizeWord(match[0]),
        })).filter((item) => item.norm);
        const counts = new Map();
        spokenWords.forEach((item) => {
          counts.set(item.norm, (counts.get(item.norm) || 0) + 1);
        });
        const details = words.map((word, index) => {
          const remaining = counts.get(word.norm) || 0;
          const ok = remaining > 0;
          if (ok) {
            counts.set(word.norm, remaining - 1);
          }
          return {
            ...word,
            expected: word.text,
            spoken: ok ? word.text : "",
            ok,
            similarity: ok ? 100 : 0,
            index,
          };
        });
        const correct = details.filter((item) => item.ok).length;
        const score = words.length ? Math.round((correct / words.length) * 100) : 0;
        return {
          words,
          spokenWords,
          details,
          correct,
          total: words.length,
          score,
          text: clean(rawInput),
          transcript: clean(rawInput),
          feedback: `Browser live check: ${correct}/${words.length} tokens detected.`,
          complete: Boolean(words.length) && correct === words.length,
        };
      };

      const browserSpeakPayload = (transcript = "") => {
        const result = scoreSpeakLooseTranscript(transcript, getNodeScoringWords());
        return {
          score: result.score,
          correct: result.correct,
          total: result.total,
          text: result.text,
          transcript: result.transcript,
          feedback: result.feedback,
          details: result.details,
          browser: true,
        };
      };

      speakAiCheckVoice = readSpeakAiCheckPreference();
      syncSpeakModeUi();

      const resizeAnswerInputHeight = () => {
        if (!answerInput || !answerInputWrap || !answerInputHighlight) {
          return;
        }
        const style = window.getComputedStyle(answerInput);
        const wrapStyle = window.getComputedStyle(answerInputWrap);
        const fontSize = parseFloat(style.fontSize) || 28;
        const lineHeight = parseFloat(style.lineHeight) || fontSize * 1.16;
        const minHeight = parseFloat(wrapStyle.minHeight) || 64;
        answerInput.style.height = "auto";
        const nextHeight = Math.max(minHeight, Math.ceil(answerInput.scrollHeight || lineHeight) + 2);
        const heightText = `${nextHeight}px`;
        answerInputWrap.style.height = heightText;
        answerInput.style.height = heightText;
        answerInputHighlight.style.height = heightText;
        answerInput.style.overflowY = "hidden";
      };

      const syncAnswerHighlightScroll = () => {
        if (!answerInput || !answerInputHighlight) {
          return;
        }
        answerInputHighlight.scrollLeft = answerInput.scrollLeft;
        answerInputHighlight.scrollTop = answerInput.scrollTop;
      };

      const renderAnswerHighlight = (result = null) => {
        if (!answerInputHighlight || !answerInput) {
          return;
        }
        const raw = answerInput.value || "";
        resizeAnswerInputHeight();
        answerInputHighlight.textContent = "";
        if (!raw) {
          syncAnswerHighlightScroll();
          return;
        }
        const ranges = [];
        const typedWords = result && Array.isArray(result.typedWords) ? result.typedWords : [];
        const details = result && Array.isArray(result.details) ? result.details : [];
        typedWords.forEach((typed, index) => {
          const detail = details[index];
          if (!detail || !detail.ok) {
            ranges.push({ start: typed.start, end: typed.end, className: "ft-input-highlight-error", priority: 2 });
          }
        });
        if (grammarFocusRange && Number.isFinite(grammarFocusRange.start) && Number.isFinite(grammarFocusRange.end)) {
          ranges.push({ start: grammarFocusRange.start, end: grammarFocusRange.end, className: "ft-input-highlight-focus", priority: 1 });
        }
        if (!ranges.length) {
          answerInputHighlight.textContent = raw;
          syncAnswerHighlightScroll();
          return;
        }
        ranges.sort((a, b) => (a.start - b.start) || (b.priority - a.priority));
        let cursor = 0;
        ranges.forEach((range) => {
          const start = Math.max(cursor, Math.min(raw.length, Number(range.start) || 0));
          const end = Math.max(start, Math.min(raw.length, Number(range.end) || start));
          if (end <= cursor) {
            return;
          }
          if (start > cursor) {
            answerInputHighlight.appendChild(document.createTextNode(raw.slice(cursor, start)));
          }
          const span = document.createElement("span");
          span.className = range.className;
          span.textContent = raw.slice(start, end);
          answerInputHighlight.appendChild(span);
          cursor = end;
        });
        if (cursor < raw.length) {
          answerInputHighlight.appendChild(document.createTextNode(raw.slice(cursor)));
        }
        syncAnswerHighlightScroll();
      };

      const maskedWordHint = (expected, typed = "") => {
        const source = String(expected || "");
        const typedChars = Array.from(String(typed || ""))
          .filter((char) => /[A-Za-z0-9]/.test(char));
        let cursor = 0;
        return Array.from(source).map((char) => {
          if (!/[A-Za-z0-9]/.test(char)) {
            return char;
          }
          const typedChar = typedChars[cursor] || "";
          cursor += 1;
          return typedChar && typedChar.toLowerCase() === char.toLowerCase() ? char : "*";
        }).join("");
      };

      const countWordLetters = (value) => Array.from(String(value || ""))
        .filter((char) => /[A-Za-z0-9]/.test(char))
        .length;

      const wordHintKeyForIssue = (issue) => issue
        ? `${currentNodeIndex}:${issue.index}:${issue.norm}`
        : "";

      const renderStarMeter = (container, percent = 0, active = false, title = "") => {
        if (!container) {
          return;
        }
        const safePercent = active ? clamp(Number(percent) || 0, 0, 100) : 0;
        container.classList.toggle("is-final", Boolean(active));
        if (title) {
          container.title = title;
        }
        Array.from(container.querySelectorAll(".ft-score-star")).forEach((star, index) => {
          const fill = clamp(safePercent - index * 20, 0, 20) * 5;
          star.style.setProperty("--star-fill", `${fill}%`);
          star.classList.toggle("is-earned", active && fill > 0);
        });
      };

      const hintedWordScore = (result = null) => {
        const words = result && Array.isArray(result.words) && result.words.length
          ? result.words
          : getNodeScoringWords();
        const total = words.length || 0;
        if (!total) {
          return { percent: 100, stars: 5, hinted: 0, total: 0 };
        }
        const hinted = Math.min(total, wordHintedKeys.size);
        const percent = Math.max(0, Math.round(100 - (hinted * 100 / total)));
        return {
          percent,
          stars: Math.max(0, Math.min(5, Math.floor(percent / 20))),
          hinted,
          total,
        };
      };

      const renderScoreStars = (result = null) => {
        if (!scoreStars) {
          return;
        }
        const complete = Boolean(result && result.complete);
        const { percent } = hintedWordScore(result);
        renderStarMeter(scoreStars, percent, complete, complete
          ? `Hint-adjusted score: ${percent}%`
          : "Stars unlock after the full sentence is complete.");
      };

      const renderIpaStars = () => {
        const percent = Math.min(100, Math.max(0, completedListenCount) / IPA_STAR_FULL_LISTENS * 100);
        renderStarMeter(
          ipaStars,
          percent,
          true,
          `Listen stars: ${Math.min(completedListenCount, IPA_STAR_FULL_LISTENS)}/${IPA_STAR_FULL_LISTENS}`,
        );
      };

      const renderSpeakStars = () => {
        renderStarMeter(
          speakStars,
          Math.min(100, Math.max(0, speakStarCount) * 20),
          true,
          `Speak stars: ${Math.min(speakStarCount, 5)}/5`,
        );
      };

      const renderGrammarStars = () => {
        const total = grammarState && Array.isArray(grammarState.items) ? grammarState.items.length : 0;
        const correct = Math.min(total, grammarFirstTryCorrect.size);
        const percent = total ? Math.round((correct / total) * 100) : 0;
        renderStarMeter(
          grammarStars,
          percent,
          Boolean(total),
          total
            ? `Grammar checkpoint first-try stars: ${correct}/${total} (${percent}%)`
            : "Grammar checkpoint stars unlock when checkpoint starts.",
        );
      };

      const hideWordHintCountdown = () => {
        if (scoreCountdown) {
          scoreCountdown.classList.add("is-hidden");
          scoreCountdown.classList.remove("is-running");
        }
      };

      const wordHintRemainingSeconds = () => wordHintDeadline
        ? Math.max(0, Math.ceil((wordHintDeadline - Date.now()) / 1000))
        : 0;

      const updateWordHintCountdown = () => {
        if (!scoreCountdown || !wordHintWatchKey || wordTimeoutHintKey) {
          hideWordHintCountdown();
          return;
        }
        const remaining = wordHintRemainingSeconds();
        const active = canRunWordHintWatch() && remaining > 0;
        scoreCountdown.classList.toggle("is-hidden", !active);
        scoreCountdown.classList.toggle("is-running", active);
      };

      const startWordHintClock = () => {
        if (!scoreCountdown) {
          return;
        }
        scoreCountdown.style.setProperty("--word-hint-duration", `${wordHintIdleMs}ms`);
        scoreCountdown.classList.remove("is-hidden", "is-running");
        if (scoreClockHand) {
          scoreClockHand.style.animation = "none";
          void scoreClockHand.offsetWidth;
          scoreClockHand.style.animation = "";
        } else {
          void scoreCountdown.offsetWidth;
        }
        scoreCountdown.classList.add("is-running");
      };

      const cancelWordHintTick = () => {
        if (wordHintTickTimer) {
          window.clearInterval(wordHintTickTimer);
          wordHintTickTimer = 0;
        }
      };

      const cancelWordHintTimer = () => {
        if (wordHintTimer) {
          window.clearTimeout(wordHintTimer);
          wordHintTimer = 0;
        }
        cancelWordHintTick();
        wordHintDeadline = 0;
        wordHintWatchKey = "";
        hideWordHintCountdown();
      };

      const clearWordTimeoutHint = () => {
        wordTimeoutHintKey = "";
      };

      const stopWordHintWatch = () => {
        cancelWordHintTimer();
        clearWordTimeoutHint();
      };

      const canRunWordHintWatch = () => Boolean(
        answerInput &&
        !answerInput.disabled &&
        !nextPanelCanShow &&
        currentNode &&
        !grammarState.active
      );

      const scheduleWordHintWatch = (result = null) => {
        cancelWordHintTimer();
        if (!canRunWordHintWatch()) {
          return;
        }
        const latestResult = result || scoreInputWords(answerInput.value);
        const issue = latestResult && latestResult.firstIssue;
        if (!issue || latestResult.complete) {
          return;
        }
        const expectedKey = wordHintKeyForIssue(issue);
        if (!expectedKey || wordTimeoutHintKey === expectedKey) {
          return;
        }
        wordHintWatchKey = expectedKey;
        wordHintDeadline = Date.now() + wordHintIdleMs;
        startWordHintClock();
        wordHintTickTimer = window.setInterval(() => {
          if (!canRunWordHintWatch()) {
            cancelWordHintTimer();
            return;
          }
          const freshResult = scoreInputWords(answerInput.value);
          const freshIssue = freshResult && freshResult.firstIssue;
          const freshKey = wordHintKeyForIssue(freshIssue);
          if (!freshIssue || freshResult.complete || freshKey !== wordHintWatchKey) {
            cancelWordHintTimer();
            return;
          }
          updateWordHintCountdown();
        }, 1000);
        wordHintTimer = window.setTimeout(() => {
          wordHintTimer = 0;
          cancelWordHintTick();
          hideWordHintCountdown();
          wordHintDeadline = 0;
          wordHintWatchKey = "";
          if (!canRunWordHintWatch()) {
            return;
          }
          const freshResult = scoreInputWords(answerInput.value);
          const freshIssue = freshResult && freshResult.firstIssue;
          const freshKey = wordHintKeyForIssue(freshIssue);
          if (!freshIssue || !freshKey || freshResult.complete) {
            return;
          }
          wordTimeoutHintKey = freshKey;
          wordHintedKeys.add(freshKey);
          renderAnswerHighlight(freshResult);
          renderScorePanel(freshResult, true);
          queueSpaceWProgressSave(120);
        }, wordHintIdleMs);
      };

      const normalizeWordHintMs = (value) => {
        const numeric = Number(value);
        if (!Number.isFinite(numeric) || numeric <= 0) {
          return DEFAULT_WORD_HINT_IDLE_MS;
        }
        return Math.max(5000, Math.min(180000, Math.round(numeric)));
      };

      const normalizeQuestionHudLines = (value) => {
        const raw = Array.isArray(value)
          ? value
          : String(value || "").split(/\r?\n|[|;]/);
        const lines = raw
          .map((item) => clean(item).replace(/\s+/g, " "))
          .filter(Boolean)
          .slice(0, 4);
        return lines.length ? lines : [...DEFAULT_Q_ROOT_HUD_LINES];
      };

      const renderQuestionRootHudLines = () => {
        if (!qRootHudLines) {
          return;
        }
        qRootHudLines.textContent = "";
        qRootHudLineValues.forEach((line) => {
          const row = document.createElement("span");
          row.className = "ft-q-root-hud-line";
          row.textContent = line;
          qRootHudLines.appendChild(row);
        });
      };

      renderQuestionRootHudLines();

      const applyServerSettings = (payload = {}) => {
        if (typeof applyWebRtcSettings === "function") {
          applyWebRtcSettings(payload);
        }
        qRootHudLineValues = normalizeQuestionHudLines(payload.question_hud_lines || payload.questionHudLines || payload.question_hud || "");
        renderQuestionRootHudLines();
        sharedWorldSkinSettings = normalizeSharedWorldSkins(payload.qm_city_skins || payload.qmCitySkins || sharedWorldSkinSettings);
        if (Object.prototype.hasOwnProperty.call(payload, "space_w_ai_check_voice_enabled") || Object.prototype.hasOwnProperty.call(payload, "spaceWAiCheckVoiceEnabled")) {
          const enabled = payload.space_w_ai_check_voice_enabled !== false && payload.spaceWAiCheckVoiceEnabled !== false;
          speakAiCheckVoiceServerAllowsWhisper = enabled;
          speakAiCheckVoiceServerManaged = !enabled;
          speakAiCheckVoiceFallbackActive = false;
          setSpeakAiCheckVoice(enabled ? readSpeakAiCheckPreference() : false, false);
        }
        const paragraphSeconds = Number(payload.paragraph_hint_seconds || 0);
        const paragraphMsSeconds = Number(payload.paragraph_hint_ms || 0) / 1000;
        const nextParagraphSeconds = Math.max(3, Math.min(300, Math.round(paragraphSeconds || paragraphMsSeconds || paragraphHintIdleSeconds || (DEFAULT_WORD_HINT_IDLE_MS / 1000))));
        paragraphHintIdleSeconds = nextParagraphSeconds;
        const secondsMs = Number(payload.word_hint_cycle_seconds || 0) * 1000;
        const nextMs = normalizeWordHintMs(payload.word_hint_cycle_ms || secondsMs);
        if (nextMs === wordHintIdleMs) {
          return;
        }
        wordHintIdleMs = nextMs;
        if (wordHintWatchKey && !wordTimeoutHintKey && canRunWordHintWatch()) {
          scheduleWordHintWatch(scoreInputWords(answerInput.value));
        }
      };

      let refreshServerSettingsBusy = false;
      let refreshServerSettingsPromise = null;
      const refreshServerSettings = async () => {
        if (refreshServerSettingsBusy) {
          return refreshServerSettingsPromise;
        }
        refreshServerSettingsBusy = true;
        refreshServerSettingsPromise = (async () => {
          try {
            const payload = await fetchPublicServerJson(`/settings?ts=${Date.now()}`);
            applyServerSettings(payload);
            return payload;
          } catch (error) {
            // File mode or offline use keeps the embedded default.
            return null;
          } finally {
            refreshServerSettingsBusy = false;
            refreshServerSettingsPromise = null;
          }
        })();
        return refreshServerSettingsPromise;
      };

      const updateScoreConnector = () => {
        if (!scorePanel || !scorePanel.classList.contains("is-live")) {
          return;
        }
        const activeConnector = connectorForPanel(scorePanel);
        activeConnector.classList.remove("is-complete", "is-dim");
        positionConnectorTo(scorePanel);
        activeConnector.classList.add("is-live");
        setActivePanel(scorePanel);
        autoPanToPanel(scorePanel);
      };

      const lockScorePanel = () => {
        if (!scorePanel || !scorePanel.classList.contains("is-live") || isMobilePanelFlow()) {
          return;
        }
        scorePanel.classList.add("is-locked");
        const node = connectorForPanel(scorePanel);
        if (node.classList.contains("is-live")) {
          node.classList.remove("is-active", "is-dim");
          node.classList.add("is-complete");
        }
      };

      const hideScorePanel = (force = false) => {
        if (scorePanel) {
          if (!force && !isMobilePanelFlow() && scorePanel.classList.contains("is-locked")) {
            return;
          }
          scorePanel.classList.remove("is-live", "is-locked", "is-mobile-hidden");
        }
        setMobilePanelUnlocked("score", false);
        syncMobilePanelTabs();
        if (connectorTargetPanel === scorePanel) {
          connectorTargetPanel = null;
        }
        hidePanelConnector(scorePanel);
        setActivePanel(connectorTargetPanel);
      };

      const clearHintTyping = () => {
        hintTypingToken += 1;
        if (hintTypingTimer) {
          window.clearTimeout(hintTypingTimer);
          hintTypingTimer = 0;
        }
      };

      const updateHintConnector = (makeActive = false) => {
        if (!hintPanel || !hintPanel.classList.contains("is-live")) {
          return;
        }
        const activeConnector = connectorForPanel(hintPanel);
        activeConnector.classList.remove("is-complete", "is-dim");
        positionConnectorTo(hintPanel);
        activeConnector.classList.add("is-live", "is-complete");
        if (makeActive || !connectorTargetPanel) {
          setActivePanel(hintPanel);
        } else {
          setActivePanel(connectorTargetPanel);
        }
        autoPanToPanel(hintPanel);
      };

      const typeHintText = (text) => {
        if (!hintText) {
          return;
        }
        clearHintTyping();
        const source = clean(text);
        hintText.textContent = "";
        if (!source) {
          return;
        }
        const chars = Array.from(source);
        const token = ++hintTypingToken;
        let index = 0;
        const cursor = document.createElement("span");
        cursor.className = "ft-hint-cursor";
        const paint = () => {
          if (token !== hintTypingToken) {
            return;
          }
          hintText.textContent = chars.slice(0, index).join("");
          if (index < chars.length) {
            hintText.appendChild(cursor);
            const previous = chars[Math.max(0, index - 1)] || "";
            const delay = /[.!?,;:]/.test(previous) ? 92 : (/\s/.test(previous) ? 32 : 24);
            index += 1;
            hintTypingTimer = window.setTimeout(paint, delay);
          } else {
            hintTypingTimer = 0;
          }
        };
        paint();
      };

      const spaceWNodeCandidates = (node = currentNode) => {
        const list = [
          node,
          currentNode,
          Array.isArray(lessonNodes) ? lessonNodes[currentNodeIndex] : null,
          Array.isArray(pendingLessonNodes) ? pendingLessonNodes[currentNodeIndex] : null,
        ].filter((item) => item && typeof item === "object");
        return list.filter((item, index) => list.indexOf(item) === index);
      };

      const nodeHintText = (node = currentNode) => {
        for (const candidate of spaceWNodeCandidates(node)) {
          const hint = clean(candidate.hint ?? candidate.ht ?? candidate.guide ?? candidate.note ?? candidate.tip ?? "");
          if (hint) {
            return hint;
          }
        }
        return "";
      };

      const syncHintAboutSwitchButtons = () => {
        const hasAbout = normalizeNodeAboutItems(currentNode).length > 0;
        const hasHint = Boolean(nodeHintText(currentNode));
        if (hintAboutToggle) {
          hintAboutToggle.hidden = !hasAbout;
        }
        if (aboutHintToggle) {
          aboutHintToggle.hidden = !hasHint;
        }
        if (translationAboutButton) {
          translationAboutButton.classList.add("is-hidden");
          translationAboutButton.classList.toggle("is-unavailable", !hasAbout);
          translationAboutButton.setAttribute("aria-disabled", hasAbout ? "false" : "true");
        }
      };

      const showHintPanel = (text, makeActive = true) => {
        const hint = clean(text);
        if (!hintPanel || !hintText || !hint) {
          hideHintPanel();
          return;
        }
        typeHintText(hint);
        syncHintAboutSwitchButtons();
        revealMobilePanel("hint");
        if (isMobilePanelFlow()) {
          hintPanel.classList.add("is-live");
          window.requestAnimationFrame(() => updateHintConnector(makeActive));
          return;
        }
        hintPanel.classList.add("is-live", "is-measuring");
        updateDesktopPanelLayout();
        positionConnectorTo(hintPanel);
        window.requestAnimationFrame(() => {
          updateDesktopPanelLayout();
          positionConnectorTo(hintPanel);
          hintPanel.classList.remove("is-measuring");
          updateHintConnector(makeActive);
          window.setTimeout(() => {
            if (hintPanel.classList.contains("is-live")) {
              updateDesktopPanelLayout();
              updateHintConnector(makeActive);
            }
          }, 160);
        });
      };

      const hideHintPanel = () => {
        clearHintTyping();
        if (hintText) {
          hintText.textContent = "";
        }
        if (hintPanel) {
          hintPanel.classList.remove("is-live", "is-mobile-hidden");
        }
        setMobilePanelUnlocked("hint", false);
        syncMobilePanelTabs();
        if (connectorTargetPanel === hintPanel) {
          connectorTargetPanel = null;
        }
        hidePanelConnector(hintPanel);
        setActivePanel(connectorTargetPanel);
      };

      const cleanAboutText = (value) => String(value == null ? "" : value)
        .replace(/\r\n?/g, "\n")
        .split("\n")
        .map((line) => clean(line))
        .filter(Boolean)
        .join("\n");

      const normalizeAboutColor = (value, fallback = "#ffff00") => {
        const raw = clean(value);
        if (/^#[0-9a-f]{6}$/i.test(raw)) {
          return raw.toLowerCase();
        }
        if (/^[0-9a-f]{6}$/i.test(raw)) {
          return `#${raw.toLowerCase()}`;
        }
        if (/^#[0-9a-f]{3}$/i.test(raw)) {
          return `#${raw.slice(1).split("").map((char) => char + char).join("").toLowerCase()}`;
        }
        return fallback;
      };

      const normalizeAboutHighlights = (rawHighlights, text = "") => {
        const sourceText = cleanAboutText(text);
        const textLength = Array.from(sourceText).length;
        const ranges = [];
        const used = new Set();
        (Array.isArray(rawHighlights) ? rawHighlights : []).forEach((raw) => {
          if (!raw || typeof raw !== "object") {
            return;
          }
          const color = normalizeAboutColor(raw.c ?? raw.color ?? raw.colour);
          let start = Number(raw.s ?? raw.start);
          let end = Number(raw.e ?? raw.end);
          const segment = cleanAboutText(raw.t ?? raw.text ?? raw.segment ?? "");
          if (!(Number.isFinite(start) && Number.isFinite(end) && end > start) && segment) {
            const occurrence = Math.max(1, Math.round(Number(raw.n ?? raw.occurrence ?? 1) || 1));
            let from = 0;
            let found = -1;
            for (let count = 0; count < occurrence; count += 1) {
              found = sourceText.indexOf(segment, from);
              if (found < 0) {
                break;
              }
              from = found + segment.length;
            }
            if (found < 0) {
              found = sourceText.indexOf(segment);
            }
            if (found >= 0) {
              start = Array.from(sourceText.slice(0, found)).length;
              end = start + Array.from(segment).length;
            }
          }
          if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
            return;
          }
          start = Math.max(0, Math.min(textLength, Math.round(start)));
          end = Math.max(start + 1, Math.min(textLength, Math.round(end)));
          const key = `${start}:${end}:${color}`;
          if (!used.has(key)) {
            used.add(key);
            ranges.push({ s: start, e: end, c: color });
          }
        });
        return ranges.sort((left, right) => left.s - right.s || right.e - left.e);
      };

      const aboutHighlightAt = (ranges = [], index = 0) => (
        ranges.find((range) => index >= range.s && index < range.e) || null
      );

      const aboutRawFromNode = (node = {}) => {
        if (!node || typeof node !== "object") {
          return null;
        }
        return node.ab ?? node.about ?? node.abouts ?? node.qa ?? node.qas ?? node.info ?? node.infos ?? node.expert ?? node.experts ?? node.expert_notes ?? node.expertNotes ?? null;
      };

      const normalizeNodeAboutItems = (node = currentNode) => {
        const candidates = [
          node,
          currentNode,
          Array.isArray(lessonNodes) ? lessonNodes[currentNodeIndex] : null,
          Array.isArray(pendingLessonNodes) ? pendingLessonNodes[currentNodeIndex] : null,
        ].filter(Boolean);
        let raw = null;
        for (const candidate of candidates) {
          const value = aboutRawFromNode(candidate);
          if ((Array.isArray(value) && value.length) || (value && typeof value === "object") || clean(value)) {
            raw = value;
            break;
          }
        }
        if (raw && typeof raw === "object" && !Array.isArray(raw)) {
          raw = raw.items || raw.list || raw.nodes || raw.entries || raw.qa || raw.qas || raw.about || [];
        }
        if (typeof raw === "string") {
          raw = raw
            .split(/\n{2,}|(?:\s*\|\|\s*)/)
            .map((part) => ({ a: part }));
        }
        if (!Array.isArray(raw)) {
          return [];
        }
        return raw
          .map((item) => {
            if (Array.isArray(item)) {
              return { q: cleanAboutText(item[0]), a: cleanAboutText(item[1]) };
            }
            if (item && typeof item === "object") {
              const answer = cleanAboutText(item.a ?? item.answer ?? item.explanation ?? item.body ?? "");
              return {
                q: cleanAboutText(item.q ?? item.question ?? item.title ?? ""),
                a: answer,
                ah: normalizeAboutHighlights(item.ah ?? item.answer_highlights ?? item.answerHighlights ?? item.hl ?? item.highlights, answer),
              };
            }
            return null;
          })
          .filter((item) => item && (item.q || item.a));
      };

      const rawPracticeNodesFrom = (node = {}) => {
        if (!node || typeof node !== "object") {
          return [];
        }
        const raw = node.xp ?? node.practice ?? node.extra_practice ?? node.extraPractice ?? node.supplemental ?? node.training ?? node.train ?? [];
        if (Array.isArray(raw)) {
          return raw;
        }
        if (raw && typeof raw === "object") {
          return raw.nodes || raw.items || raw.entries || [];
        }
        return [];
      };

      const normalizePracticeRuntimeNode = (node = {}, sourceIndex = currentNodeIndex) => {
        if (!node || typeof node !== "object") {
          return null;
        }
        const en = clean(node.en ?? node.e ?? node.text ?? node.sentence ?? "");
        const vi = clean(node.vi ?? node.q ?? node.mn ?? node.meaning ?? "");
        if (!en || !vi) {
          return null;
        }
        return {
          ...node,
          vi,
          en,
          ipa: clean(node.ipa ?? node.i ?? ""),
          tr: true,
          src: Number.isFinite(Number(node.src)) ? Number(node.src) : sourceIndex,
        };
      };

      const practiceNodesForNode = (node = currentNode, sourceIndex = currentNodeIndex) => {
        const explicit = rawPracticeNodesFrom(node)
          .map((item) => normalizePracticeRuntimeNode(item, sourceIndex))
          .filter(Boolean);
        if (explicit.length) {
          return explicit;
        }
        const en = clean(node && (node.en ?? node.e ?? node.text ?? node.sentence ?? ""));
        const vi = clean(node && (node.vi ?? node.q ?? node.mn ?? node.meaning ?? ""));
        const fallback = normalizePracticeRuntimeNode({
          ...(node && typeof node === "object" ? node : {}),
          en,
          vi,
          generatedTrain: true,
        }, sourceIndex);
        return fallback ? [fallback] : [];
      };

      const isSpaceWTrainingNode = (node = currentNode) => Boolean(
        node && typeof node === "object" && (node.tr || node.trainMode || node.trainingNode || node.__spaceWTrain)
      );

      const resetSpaceWTrainMode = () => {
        spaceWTrainModeLocked = false;
        spaceWTrainModeBuffer = [];
        spaceWTrainModeOriginalCount = 0;
        spaceWTrainModeRootCount = 0;
        spaceWTrainModeExpanded = false;
        spaceWTrainModeBatch = 0;
        updateAboutTrainButton();
      };

      const spaceWRootNodeCount = () => (Array.isArray(lessonNodes) ? lessonNodes : [])
        .filter((node) => !isSpaceWTrainingNode(node)).length;

      const spaceWTrainingNodeCount = () => (Array.isArray(lessonNodes) ? lessonNodes : [])
        .filter((node) => isSpaceWTrainingNode(node)).length;

      const spaceWNodeOrdinal = (targetIndex = currentNodeIndex, training = false) => {
        const maxIndex = Math.max(0, Math.min((lessonNodes.length || 1) - 1, Number(targetIndex) || 0));
        let count = 0;
        for (let index = 0; index <= maxIndex; index += 1) {
          if (Boolean(isSpaceWTrainingNode(lessonNodes[index])) === Boolean(training)) {
            count += 1;
          }
        }
        return Math.max(1, count);
      };

      const spaceWProgressText = (index = currentNodeIndex) => {
        if (isReviewPhase()) {
          return `Ôn ${Math.min(lessonNodes.length, reviewMasteredIndexes.size + 1)} / ${lessonNodes.length}`;
        }
        if (lessonNodes.length <= 1) {
          return "";
        }
        const node = lessonNodes[index] || currentNode;
        const trainTotal = spaceWTrainingNodeCount();
        if (isSpaceWTrainingNode(node)) {
          return `Train ${spaceWNodeOrdinal(index, true)} / ${Math.max(1, trainTotal)} · Node ${index + 1} / ${lessonNodes.length}`;
        }
        if (trainTotal) {
          return `Root ${spaceWNodeOrdinal(index, false)} / ${spaceWRootNodeCount()} · Node ${index + 1} / ${lessonNodes.length}`;
        }
        return `Node ${index + 1} / ${lessonNodes.length}`;
      };

      const spaceWCurrentNodeCanCountComplete = () => Boolean(
        nextButton
        && !nextButton.classList.contains("is-hidden")
        && !nextButton.disabled
        && nextPanelCanShow
      );

      const spaceWNodeProgressStats = () => {
        const total = Math.max(0, Array.isArray(lessonNodes) ? lessonNodes.length : 0);
        if (!total) {
          return { done: 0, total: 0, label: "Nodes", value: "Nodes 0/0", detail: "0%" };
        }
        if (isReviewPhase()) {
          const mastered = Math.max(0, Math.min(total, reviewMasteredIndexes.size));
          const currentReady = spaceWCurrentNodeCanCountComplete() && !reviewCurrentHadError ? 1 : 0;
          const done = Math.max(0, Math.min(total, mastered + currentReady));
          return {
            done,
            total,
            label: "Review progress",
            value: `Nodes ${done}/${total}`,
            detail: `${Math.round((done / total) * 100)}%`,
          };
        }
        const done = Math.max(0, Math.min(total, currentNodeIndex + (spaceWCurrentNodeCanCountComplete() ? 1 : 0)));
        const rootTotal = spaceWRootNodeCount();
        const trainTotal = spaceWTrainingNodeCount();
        if (trainTotal) {
          const completedNodes = lessonNodes.slice(0, done);
          const rootDone = completedNodes.filter((node) => !isSpaceWTrainingNode(node)).length;
          const trainDone = completedNodes.filter((node) => isSpaceWTrainingNode(node)).length;
          return {
            done,
            total,
            label: "Space_W progress",
            value: `Nodes ${done}/${total}`,
            detail: `Root ${rootDone}/${rootTotal} | Train ${trainDone}/${trainTotal}`,
          };
        }
        return {
          done,
          total,
          label: "Space_W progress",
          value: `Nodes ${done}/${total}`,
          detail: `${Math.round((done / total) * 100)}%`,
        };
      };

      const updateSpaceWProgressLabel = () => {
        if (progressNode) {
          if (!lessonNodes.length) {
            clearRuntimeProgress(progressNode, spaceWProgressText());
            return;
          }
          const stats = spaceWNodeProgressStats();
          renderRuntimeProgress(progressNode, {
            done: stats.done,
            total: stats.total,
            label: stats.label,
            value: stats.value,
            detail: stats.detail,
            className: "is-space-w",
          });
        }
      };

      const collectSpaceWTrainModeNodesFrom = (sourceNodes = lessonNodes) => {
        const out = [];
        const seen = new Set();
        (Array.isArray(sourceNodes) ? sourceNodes : []).forEach((node, sourceIndex) => {
          if (!node || isSpaceWTrainingNode(node)) {
            return;
          }
          practiceNodesForNode(node, sourceIndex).forEach((item) => {
            const key = `${sourceIndex}\0${clean(item.en ?? item.e)}\0${clean(item.vi ?? item.q ?? item.mn)}`;
            if (!key || seen.has(key)) {
              return;
            }
            seen.add(key);
            out.push({
              ...item,
              src: sourceIndex,
            });
          });
        });
        return out;
      };

      const collectSpaceWTrainModeNodes = () => collectSpaceWTrainModeNodesFrom(lessonNodes);

      const updateAboutTrainButton = () => {
        if (!aboutTrainButton) {
          return;
        }
        const extraCount = practiceNodesForNode(currentNode).length;
        const totalTrainCount = spaceWTrainModeExpanded ? spaceWTrainingNodeCount() : collectSpaceWTrainModeNodes().length;
        aboutTrainButton.hidden = !lessonNodes.length && !currentNode;
        aboutTrainButton.disabled = false;
        if (spaceWTrainModeExpanded || spaceWTrainModeLocked) {
          aboutTrainButton.textContent = totalTrainCount ? `Train mode on (${totalTrainCount})` : "Train mode on";
          aboutTrainButton.title = totalTrainCount
            ? "Train mode đã bật. Câu luyện thêm nằm ở cuối bài và đang được cache dần."
            : "Train mode đã bật.";
        } else {
          aboutTrainButton.textContent = extraCount ? `Train mode (${extraCount})` : "Train mode";
          aboutTrainButton.title = extraCount
            ? "Bật Train mode. Tất cả câu luyện thêm sẽ được nối vào cuối bài sau các câu root."
            : "Turn on Train mode for all sentences in this file.";
        }
      };

      const expandSpaceWTrainModeNodes = () => {
        if (spaceWTrainModeExpanded || spaceWTrainingNodeCount()) {
          spaceWTrainModeExpanded = true;
          spaceWTrainModeRootCount = spaceWRootNodeCount();
          updateAboutTrainButton();
          updateSpaceWProgressLabel();
          return 0;
        }
        const trainNodes = collectSpaceWTrainModeNodes();
        if (!trainNodes.length) {
          return 0;
        }
        spaceWTrainModeBatch += 1;
        spaceWTrainModeRootCount = spaceWRootNodeCount();
        const insertAt = lessonNodes.length;
        const batchNodes = trainNodes.map((node, offset) => ({
          ...node,
          tr: true,
          trainMode: true,
          __spaceWTrain: true,
          trainBatch: spaceWTrainModeBatch,
          trainOrder: offset + 1,
        }));
        lessonNodes.push(...batchNodes);
        spaceWTrainModeExpanded = true;
        spaceWTrainModeBuffer = [];
        spaceWTrainModeOriginalCount = spaceWTrainModeRootCount;
        warmSpaceWAudioCacheForLesson(batchNodes, "", {}, {
          label: "Train mode",
          startIndex: 0,
          includeAllNodes: true,
          includeAllEmbedded: true,
          includeGrammar: true,
          delayMs: 220,
          status: false,
        });
        updateAboutTrainButton();
        updateSpaceWProgressLabel();
        queueSpaceWProgressSave(100);
        return batchNodes.length;
      };

      const enableSpaceWTrainMode = () => {
        const wasReviewPhase = isReviewPhase();
        if (spaceWTrainModeExpanded || spaceWTrainingNodeCount()) {
          spaceWTrainModeLocked = true;
          setPlaybackState(false, "Train mode is already active.");
          if (wasReviewPhase && spaceWTrainingNodeCount()) {
            beginReviewMode();
          }
          updateAboutTrainButton();
          return;
        }
        const extraCount = collectSpaceWTrainModeNodes().length;
        if (!extraCount) {
          setPlaybackState(false, "Bài này chưa có câu luyện thêm.");
          return;
        }
        spaceWTrainModeLocked = true;
        spaceWTrainModeBuffer = [];
        spaceWTrainModeOriginalCount = 0;
        const added = expandSpaceWTrainModeNodes();
        updateAboutTrainButton();
        if (wasReviewPhase && (added || spaceWTrainingNodeCount())) {
          beginReviewMode();
          setPlaybackState(false, "Train mode review started with all root and training sentences.");
          queueSpaceWProgressSave(100);
          return;
        }
        setPlaybackState(false, `Train mode đã bật: đã thêm ${added || extraCount} câu luyện vào cuối bài và bắt đầu cache dần.`);
        if (feedbackNode) {
          feedbackNode.textContent = "Train mode đã bật: học hết các câu root trước, sau đó bài sẽ chuyển sang các câu luyện thêm.";
          feedbackNode.classList.remove("is-error");
          feedbackNode.classList.add("is-ok");
        }
        queueSpaceWProgressSave(100);
      };

      const flushSpaceWTrainModeBuffer = () => {
        const added = expandSpaceWTrainModeNodes();
        return added > 0;
      };

      const recordSpaceWTrainModeNodeComplete = (options = {}) => {
        if (spaceWTrainModeLocked && !spaceWTrainModeExpanded) {
          expandSpaceWTrainModeNodes();
        }
        updateAboutTrainButton();
        return false;
      };

      const clearAboutTyping = () => {
        aboutTypingToken += 1;
        if (aboutTypingTimer) {
          window.clearTimeout(aboutTypingTimer);
          aboutTypingTimer = 0;
        }
      };

      const updateAboutConnector = (makeActive = false) => {
        if (!aboutPanel || !aboutPanel.classList.contains("is-live")) {
          return;
        }
        const activeConnector = connectorForPanel(aboutPanel);
        activeConnector.classList.remove("is-complete", "is-dim");
        positionConnectorTo(aboutPanel);
        activeConnector.classList.add("is-live", "is-complete");
        if (makeActive || !connectorTargetPanel) {
          setActivePanel(aboutPanel);
        } else {
          setActivePanel(connectorTargetPanel);
        }
        autoPanToPanel(aboutPanel);
      };

      const typeAboutInto = (target, source, token, done, highlights = []) => {
        if (!target) {
          if (typeof done === "function") {
            done();
          }
          return;
        }
        target.textContent = "";
        const text = cleanAboutText(source);
        if (!text) {
          if (typeof done === "function") {
            done();
          }
          return;
        }
        const chars = Array.from(text);
        const ranges = normalizeAboutHighlights(highlights, text);
        const hotSpans = [];
        const cursor = document.createElement("span");
        cursor.className = "ft-hint-cursor";
        let index = 0;
        const paint = () => {
          if (token !== aboutTypingToken) {
            return;
          }
          if (cursor.parentNode) {
            cursor.remove();
          }
          if (index >= chars.length) {
            aboutTypingTimer = 0;
            if (typeof done === "function") {
              done();
            }
            return;
          }
          const char = chars[index];
          if (char === "\n") {
            target.appendChild(document.createElement("br"));
          } else {
            const span = document.createElement("span");
            span.className = "ft-about-char is-hot";
            const mark = aboutHighlightAt(ranges, index);
            if (mark) {
              span.classList.add("is-marked");
              span.style.setProperty("--about-mark-color", mark.c);
            }
            span.textContent = char;
            target.appendChild(span);
            hotSpans.push(span);
            while (hotSpans.length > 5) {
              const old = hotSpans.shift();
              if (old) {
                old.classList.remove("is-hot");
              }
            }
          }
          target.appendChild(cursor);
          index += 1;
          const delay = /[.!?,;:]/.test(char) ? 84 : (/\s/.test(char) ? 24 : 16);
          aboutTypingTimer = window.setTimeout(paint, delay);
        };
        paint();
      };

      const renderAboutItem = (index = aboutIndex) => {
        if (!aboutPanel || !aboutQuestion || !aboutAnswer || !aboutItems.length) {
          return;
        }
        aboutIndex = ((Number(index) || 0) % aboutItems.length + aboutItems.length) % aboutItems.length;
        const item = aboutItems[aboutIndex] || {};
        if (aboutCount) {
          aboutCount.textContent = `${aboutIndex + 1} / ${aboutItems.length}`;
        }
        updateAboutTrainButton();
        clearAboutTyping();
        const token = ++aboutTypingToken;
        typeAboutInto(aboutQuestion, item.q || "Expert note", token, () => {
          typeAboutInto(aboutAnswer, item.a || "No explanation provided.", token, null, item.ah || []);
        });
      };

      const showAboutPanel = (node = currentNode, makeActive = true) => {
        const items = normalizeNodeAboutItems(node);
        if (!items.length || !aboutPanel) {
          hideAboutPanel();
          return false;
        }
        aboutUnlockedForCurrentNode = true;
        aboutItems = items;
        aboutIndex = 0;
        hideHintPanel();
        if (stageNode) {
          stageNode.classList.add("is-spacew-about-open");
        }
        syncHintAboutSwitchButtons();
        renderAboutItem(0);
        aboutPanel.classList.add("is-live", "is-measuring");
        aboutPanel.classList.remove("is-mobile-hidden");
        updateDesktopPanelLayout();
        if (isMobilePanelFlow()) {
          aboutPanel.classList.remove("is-measuring");
        }
        revealMobilePanel("about");
        window.requestAnimationFrame(() => {
          updateDesktopPanelLayout();
          aboutPanel.classList.remove("is-measuring");
          updateAboutConnector(makeActive);
          if (makeActive) {
            setActivePanel(aboutPanel);
          }
          window.setTimeout(() => {
            if (aboutPanel.classList.contains("is-live")) {
              updateDesktopPanelLayout();
              updateAboutConnector(makeActive);
              if (makeActive) {
                setActivePanel(aboutPanel);
              }
            }
          }, 180);
        });
        return true;
      };

      const showAboutPanelAfterCorrect = () => {
        const shown = showAboutPanel(currentNode, true);
        if (!shown || !aboutPanel) {
          return false;
        }
        aboutPanel.classList.add("is-live");
        aboutPanel.classList.remove("is-mobile-hidden", "is-measuring");
        setMobilePanelUnlocked("about", true);
        revealMobilePanel("about");
        updateDesktopPanelLayout();
        updateAboutConnector(true);
        setActivePanel(aboutPanel);
        autoPanToPanel(aboutPanel);
        return true;
      };

      const hideAboutPanel = (options = {}) => {
        clearAboutTyping();
        aboutItems = [];
        aboutIndex = 0;
        if (aboutQuestion) {
          aboutQuestion.textContent = "";
        }
        if (aboutAnswer) {
          aboutAnswer.textContent = "";
        }
        if (aboutCount) {
          aboutCount.textContent = "0 / 0";
        }
        updateAboutTrainButton();
        if (aboutPanel) {
          aboutPanel.classList.remove("is-live", "is-mobile-hidden");
        }
        if (stageNode && (!hintPanel || !hintPanel.classList.contains("is-live"))) {
          stageNode.classList.remove("is-spacew-about-open");
        }
        if (options && options.resetUnlock) {
          aboutUnlockedForCurrentNode = false;
        }
        syncHintAboutSwitchButtons();
        setMobilePanelUnlocked("about", false);
        syncMobilePanelTabs();
        if (connectorTargetPanel === aboutPanel) {
          connectorTargetPanel = null;
        }
        hidePanelConnector(aboutPanel);
        setActivePanel(connectorTargetPanel);
      };

      const switchHintToAbout = () => {
        if (!normalizeNodeAboutItems(currentNode).length) {
          return;
        }
        aboutUnlockedForCurrentNode = true;
        showAboutPanel(currentNode, true);
        syncHintAboutSwitchButtons();
        queueSpaceWProgressSave(120);
      };

      const switchAboutToHint = () => {
        const hint = nodeHintText(currentNode);
        if (!hint) {
          return;
        }
        hideAboutPanel();
        showHintPanel(hint, true);
      };

      const openAboutFromTranslationNode = () => {
        if (!normalizeNodeAboutItems(currentNode).length) {
          feedbackNode.textContent = "No About data for this node.";
          feedbackNode.classList.add("is-error");
          feedbackNode.classList.remove("is-ok");
          return;
        }
        aboutUnlockedForCurrentNode = true;
        showAboutPanel(currentNode, true);
        syncHintAboutSwitchButtons();
        queueSpaceWProgressSave(120);
      };

      const renderScorePanel = (result, force = false) => {
        if (!scorePanel || !scoreValue || !scoreMessage || !scoreWordsNode || !scoreHint) {
          return;
        }
        if (!isMobilePanelFlow() && scorePanel.classList.contains("is-locked")) {
          return;
        }
        if (!force && !clean(answerInput.value)) {
          hideScorePanel();
          return;
        }
        const words = result && Array.isArray(result.details) ? result.details : [];
        scoreValue.textContent = `${result ? result.score : 0}%`;
        renderScoreStars(result);
        if (!words.length) {
          scoreMessage.textContent = "Bài này chưa có dữ liệu chấm từng từ.";
          scoreWordsNode.textContent = "";
          scoreHint.textContent = "";
          scorePanel.classList.add("is-live");
          revealMobilePanel("score");
          updateScoreConnector();
          return;
        }
        const issue = result.firstIssue;
        if (result.complete) {
          scoreMessage.textContent = "Đúng toàn bộ từng từ. Có thể mở IPA và nghe lại.";
        } else if (issue) {
          const letterCount = countWordLetters(issue.text);
          scoreMessage.textContent = wordTimeoutHintKey === wordHintKeyForIssue(issue)
            ? `Đúng ${result.correct}/${words.length} từ. Gợi ý đã mở, nhập từ đang nhấp nháy.`
            : `Đúng ${result.correct}/${words.length} từ. Từ tiếp theo có ${letterCount} chữ cái.`;
        } else if (result.extraCount) {
          scoreMessage.textContent = `Đúng ${result.correct}/${words.length} từ. Có ${result.extraCount} từ dư ở cuối.`;
        } else {
          scoreMessage.textContent = `Đúng ${result.correct}/${words.length} từ.`;
        }
        scoreWordsNode.textContent = "";
        words.forEach((word) => {
          const chip = document.createElement("span");
          chip.className = "ft-score-word";
          const showTimeoutHint = Boolean(result.firstIssue && result.firstIssue.index === word.index && wordTimeoutHintKey === wordHintKeyForIssue(word));
          chip.classList.toggle("is-ok", Boolean(word.ok));
          chip.classList.toggle("is-miss", Boolean(word.typed && !word.ok));
          chip.classList.toggle("is-current", result.firstIssue && result.firstIssue.index === word.index);
          chip.classList.toggle("is-timeout-hint", showTimeoutHint);
          chip.textContent = word.ok || showTimeoutHint ? word.text : maskedWordHint(word.text, word.typed);
          if (word.ok || showTimeoutHint) {
            prepareSpaceWScoringAudioToken(chip, word.text, word.index);
          }
          scoreWordsNode.appendChild(chip);
        });
        scoreHint.textContent = "";
        const appendHintLine = (label, value) => {
          const line = document.createElement("span");
          const strong = document.createElement("strong");
          strong.textContent = label;
          line.appendChild(strong);
          line.appendChild(document.createTextNode(` ${value}`));
          scoreHint.appendChild(line);
        };
        if (issue) {
          if (issue.pos) {
            appendHintLine("Loại từ:", grammarDisplayValue("pos", issue.pos));
          }
          if (issue.dep) {
            appendHintLine("Vai trò:", grammarDisplayValue("dep", issue.dep));
          }
        } else if (result.extraCount) {
          appendHintLine("Dư từ:", `bỏ ${result.extraCount} từ cuối.`);
        } else {
          appendHintLine("Hoàn tất:", "câu đã khớp từng từ.");
        }
        scorePanel.classList.add("is-live");
        revealMobilePanel("score");
        updateScoreConnector();
      };

      const updateLiveScoring = (force = false) => {
        const result = scoreInputWords(answerInput.value);
        renderAnswerHighlight(result);
        renderScorePanel(result, force);
        scheduleWordHintWatch(result);
        if (isCurrentSpaceWAnswerComplete(result)) {
          hideSpaceWTokenSupport(true);
        } else {
          updateSpaceWTokenSupportVisibility();
        }
        return result;
      };

      const updateLiveScoringWithInputSound = (force = false) => {
        const result = updateLiveScoring(force);
        const nextOk = Array.isArray(result.details) ? result.details.map((item) => Boolean(item.ok)) : [];
        nextOk.forEach((ok, index) => {
          if (ok && previousWordOk[index] !== true) {
            playEffectSound("true");
          }
        });
        previousWordOk = nextOk;
        return result;
      };

      const playFalseForCompletedWord = (result) => {
        const typedWords = result && Array.isArray(result.typedWords) ? result.typedWords : [];
        if (!typedWords.length || !/\s$/.test(answerInput.value || "")) {
          return;
        }
        const typedIndex = typedWords.length - 1;
        const typed = typedWords[typedIndex];
        const detail = result.details && result.details[typedIndex];
        const isWrong = !detail || !detail.ok;
        if (!isWrong) {
          return;
        }
        const key = `${currentNodeIndex}:${typedIndex}:${typed.start}:${typed.end}:${typed.norm}`;
        if (key === lastFalseWordKey) {
          return;
        }
        lastFalseWordKey = key;
        if (isReviewPhase()) {
          reviewCurrentHadError = true;
          updateNextButton();
        }
        playEffectSound("false");
      };

      const setSpeakMotionState = (mode = "idle") => {
        speakWaveMode = mode || "idle";
        if (speakPanel) {
          speakPanel.classList.toggle("is-recording", mode === "recording");
          speakPanel.classList.toggle("is-playing", mode === "playing");
          speakPanel.classList.toggle("is-processing", mode === "processing");
        }
        if (speakReplayButton) {
          speakReplayButton.classList.toggle("is-playing", mode === "playing");
          speakReplayButton.textContent = mode === "playing" ? "Stop" : "Replay";
        }
        if (speakWaveLabel) {
          const labels = {
            recording: "Recording signal",
            processing: "Speech analysis",
            playing: "Replay signal",
            ready: "Captured signal",
            idle: "Signal idle",
          };
          speakWaveLabel.textContent = labels[mode] || labels.idle;
        }
        scheduleMobileInfiniteMotionSync();
      };

      const resizeSpeakWaveCanvas = () => {
        if (!speakWaveCanvas) {
          return null;
        }
        const rect = speakWaveCanvas.getBoundingClientRect();
        const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
        const width = Math.max(260, Math.round((rect.width || 320) * dpr));
        const height = Math.max(70, Math.round((rect.height || 86) * dpr));
        if (speakWaveCanvas.width !== width || speakWaveCanvas.height !== height) {
          speakWaveCanvas.width = width;
          speakWaveCanvas.height = height;
        }
        const ctx = speakWaveCanvas.getContext("2d");
        if (!ctx) {
          return null;
        }
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        return { ctx, width: width / dpr, height: height / dpr };
      };

      const sampleSpeakStaticRows = (rows, count) => {
        const source = Array.isArray(rows) ? rows : [];
        if (!source.length) {
          return [];
        }
        const out = [];
        for (let index = 0; index < count; index += 1) {
          const start = Math.floor((index / count) * source.length);
          const end = Math.max(start + 1, Math.floor(((index + 1) / count) * source.length));
          let peak = 0;
          for (let item = start; item < end; item += 1) {
            const raw = source[item];
            const value = typeof raw === "number" ? raw : Number(raw && raw.level || 0);
            peak = Math.max(peak, Math.max(0, Math.min(1, value || 0)));
          }
          out.push(peak);
        }
        return out;
      };

      const drawSpeakWave = (progress = -1) => {
        const target = resizeSpeakWaveCanvas();
        if (!target) {
          return;
        }
        const { ctx, width, height } = target;
        const mode = speakWaveMode || "idle";
        const barCount = Math.max(36, Math.min(74, Math.floor(width / 6)));
        const gap = 3;
        const barWidth = Math.max(2, (width - gap * (barCount - 1) - 28) / barCount);
        const left = 14;
        const center = height / 2 + 7;
        const maxBar = Math.max(12, height * 0.34);
        let values = [];
        ctx.clearRect(0, 0, width, height);
        const bg = ctx.createLinearGradient(0, 0, width, height);
        bg.addColorStop(0, "rgba(70, 240, 215, 0.08)");
        bg.addColorStop(0.52, "rgba(216, 108, 255, 0.045)");
        bg.addColorStop(1, "rgba(3, 13, 14, 0.18)");
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, width, height);
        if (speakWaveAnalyser && speakWaveFrequencyData && (mode === "recording" || mode === "playing")) {
          speakWaveAnalyser.getByteTimeDomainData(speakWaveFrequencyData);
          const chunk = Math.max(1, Math.floor(speakWaveFrequencyData.length / barCount));
          for (let index = 0; index < barCount; index += 1) {
            let peak = 0;
            const start = index * chunk;
            const end = Math.min(speakWaveFrequencyData.length, start + chunk);
            for (let item = start; item < end; item += 1) {
              peak = Math.max(peak, Math.abs((speakWaveFrequencyData[item] || 128) - 128) / 128);
            }
            values.push(Math.max(0.06, Math.min(1, peak * 2.8)));
          }
        } else if (speakWaveStaticRows.length) {
          values = sampleSpeakStaticRows(speakWaveStaticRows, barCount).map((value) => Math.max(0.06, value));
        } else {
          const now = performance.now() / 1000;
          for (let index = 0; index < barCount; index += 1) {
            const phase = now * (mode === "processing" ? 6.2 : 2.1) + index * 0.42;
            const pulse = (Math.sin(phase) + Math.sin(phase * 0.43 + 1.7)) * 0.5;
            values.push(mode === "idle" ? 0.08 + Math.max(0, pulse) * 0.08 : 0.18 + Math.abs(pulse) * 0.56);
          }
        }
        const playbackProgress = progress >= 0
          ? Math.max(0, Math.min(1, progress))
          : (speakReplayAudio && Number.isFinite(speakReplayAudio.duration) && speakReplayAudio.duration > 0
            ? Math.max(0, Math.min(1, speakReplayAudio.currentTime / speakReplayAudio.duration))
            : -1);
        ctx.save();
        ctx.globalCompositeOperation = "lighter";
        values.forEach((value, index) => {
          const x = left + index * (barWidth + gap);
          const active = playbackProgress >= 0 && index / Math.max(1, barCount - 1) <= playbackProgress;
          const high = Math.max(3, value * maxBar);
          const gradient = ctx.createLinearGradient(x, center - high, x, center + high);
          if (mode === "recording") {
            gradient.addColorStop(0, "rgba(255, 97, 116, 0.9)");
            gradient.addColorStop(0.52, "rgba(216, 108, 255, 0.78)");
            gradient.addColorStop(1, "rgba(70, 240, 215, 0.72)");
          } else if (mode === "playing" || active) {
            gradient.addColorStop(0, "rgba(126, 255, 235, 0.96)");
            gradient.addColorStop(0.55, "rgba(108, 240, 164, 0.82)");
            gradient.addColorStop(1, "rgba(216, 108, 255, 0.64)");
          } else {
            gradient.addColorStop(0, "rgba(216, 108, 255, 0.52)");
            gradient.addColorStop(1, "rgba(70, 240, 215, 0.32)");
          }
          ctx.fillStyle = gradient;
          ctx.shadowColor = mode === "recording" ? "rgba(255, 97, 116, 0.42)" : "rgba(70, 240, 215, 0.38)";
          ctx.shadowBlur = mode === "idle" ? 4 : 14;
          const radius = Math.min(barWidth / 2, 4);
          const y = center - high;
          const h = high * 2;
          if (typeof ctx.roundRect === "function") {
            ctx.beginPath();
            ctx.roundRect(x, y, barWidth, h, radius);
            ctx.fill();
          } else {
            ctx.fillRect(x, y, barWidth, h);
          }
        });
        ctx.restore();
        ctx.strokeStyle = "rgba(70, 240, 215, 0.18)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(12, center);
        ctx.lineTo(width - 12, center);
        ctx.stroke();
        if (mode === "recording" || mode === "playing" || mode === "processing") {
          speakWaveFrame = window.requestAnimationFrame(() => drawSpeakWave());
        }
      };

      const closeSpeakWaveAudioContext = () => {
        if (speakReplayBufferSource) {
          try {
            speakReplayBufferSource.onended = null;
            speakReplayBufferSource.stop(0);
          } catch (error) {
          }
          speakReplayBufferSource = null;
        }
        if (speakWaveSource) {
          try {
            speakWaveSource.disconnect();
          } catch (error) {
          }
        }
        speakWaveSource = null;
        speakWaveAnalyser = null;
        speakWaveFrequencyData = null;
        const closingContext = speakWaveAudioContext;
        if (speakWaveAudioContext && typeof speakWaveAudioContext.close === "function") {
          const closed = speakWaveAudioContext.close();
          if (closed && typeof closed.catch === "function") {
            closed.catch(() => {});
          }
        }
        if (speakReplayUnlockContext && speakReplayUnlockContext === closingContext) {
          speakReplayUnlockContext = null;
        }
        speakWaveAudioContext = null;
      };

      const stopSpeakWave = (nextMode = "idle") => {
        if (speakWaveFrame) {
          window.cancelAnimationFrame(speakWaveFrame);
          speakWaveFrame = 0;
        }
        closeSpeakWaveAudioContext();
        setSpeakMotionState(nextMode);
        drawSpeakWave(nextMode === "ready" ? 0 : -1);
      };

      const startSpeakWave = (mode, analyser = null) => {
        if (speakWaveFrame) {
          window.cancelAnimationFrame(speakWaveFrame);
          speakWaveFrame = 0;
        }
        speakWaveStartedAt = performance.now();
        speakWaveAnalyser = analyser;
        speakWaveFrequencyData = analyser ? new Uint8Array(analyser.fftSize || analyser.frequencyBinCount || 1024) : null;
        setSpeakMotionState(mode);
        drawSpeakWave();
      };

      const startSpeakProcessingWave = () => {
        closeSpeakWaveAudioContext();
        startSpeakWave("processing", null);
      };

      const startSpeakStreamWave = async (stream) => {
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor || !stream) {
          startSpeakWave("recording", null);
          return;
        }
        closeSpeakWaveAudioContext();
        speakWaveAudioContext = new AudioContextCtor();
        if (speakWaveAudioContext.state === "suspended" && typeof speakWaveAudioContext.resume === "function") {
          await speakWaveAudioContext.resume().catch(() => {});
        }
        speakWaveAnalyser = speakWaveAudioContext.createAnalyser();
        speakWaveAnalyser.fftSize = 1024;
        speakWaveAnalyser.smoothingTimeConstant = 0.7;
        speakWaveSource = speakWaveAudioContext.createMediaStreamSource(stream);
        speakWaveSource.connect(speakWaveAnalyser);
        startSpeakWave("recording", speakWaveAnalyser);
      };

      const primeSpeakReplayAutoplay = async () => {
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
          return false;
        }
        try {
          if (!speakReplayUnlockContext || speakReplayUnlockContext.state === "closed") {
            speakReplayUnlockContext = new AudioContextCtor();
          }
          if (speakReplayUnlockContext.state === "suspended" && typeof speakReplayUnlockContext.resume === "function") {
            await speakReplayUnlockContext.resume();
          }
          return speakReplayUnlockContext.state === "running";
        } catch (error) {
          return false;
        }
      };

      const stopSpeakReplay = () => {
        if (speakReplayAudio) {
          try {
            speakReplayAudio.pause();
            speakReplayAudio.onended = null;
            speakReplayAudio.onerror = null;
            speakReplayAudio.onpause = null;
            speakReplayAudio.removeAttribute("src");
            speakReplayAudio.load();
          } catch (error) {
          }
        }
        speakReplayAudio = null;
        clearSpeakReplayTokenHighlight();
        if (speakReplayBufferSource) {
          try {
            speakReplayBufferSource.onended = null;
            speakReplayBufferSource.stop(0);
          } catch (error) {
          }
          speakReplayBufferSource = null;
        }
        if (speakReplayButton) {
          speakReplayButton.classList.remove("is-playing");
          speakReplayButton.textContent = "Replay";
        }
        if (speakWaveMode === "playing") {
          stopSpeakWave(speakRecordedBlob ? "ready" : "idle");
        } else {
          closeSpeakWaveAudioContext();
        }
      };

      const revokeSpeakRecordingUrl = () => {
        if (speakRecordedUrl) {
          try {
            URL.revokeObjectURL(speakRecordedUrl);
          } catch (error) {
          }
        }
        speakRecordedUrl = "";
      };

      const ensureSpeakRecordingUrl = () => {
        if (!speakRecordedBlob) {
          return "";
        }
        if (!speakRecordedUrl) {
          speakRecordedUrl = URL.createObjectURL(speakRecordedBlob);
        }
        return speakRecordedUrl;
      };

      const updateSpeakReplayButton = () => {
        if (!speakReplayButton) {
          return;
        }
        const isRecording = Boolean(speakRecorder && speakRecorder.state === "recording");
        const isBrowserRecording = Boolean(speakRecognitionActive);
        speakReplayButton.disabled = !speakRecordedBlob || speakBusy || isRecording || isBrowserRecording;
      };

      const clearSpeakRecording = () => {
        clearSpeakAutoReplayTimer();
        stopSpeakReplay();
        revokeSpeakRecordingUrl();
        speakRecordedBlob = null;
        speakBrowserRecordingStartedAt = 0;
        speakBrowserTokenTimeline = [];
        clearSpeakReplayTokenHighlight();
        speakWaveStaticRows = [];
        updateSpeakReplayButton();
        stopSpeakWave("idle");
      };

      const prepareSpeakWaveFromBlob = async (blob) => {
        speakWaveStaticRows = [];
        if (!blob || !blob.size) {
          drawSpeakWave();
          return;
        }
        try {
          const buffer = await decodeAudioBlob(blob);
          speakWaveStaticRows = audioRmsRows(buffer).map((row) => Number(row.level || 0));
        } catch (error) {
          speakWaveStaticRows = [];
        }
        if (speakWaveMode !== "recording" && speakWaveMode !== "playing" && speakWaveMode !== "processing") {
          setSpeakMotionState("ready");
          drawSpeakWave(0);
        }
      };

      const setSpeakRecordedBlob = (blob) => {
        stopSpeakReplay();
        revokeSpeakRecordingUrl();
        speakRecordedBlob = blob && blob.size ? blob : null;
        updateSpeakReplayButton();
        if (speakRecordedBlob) {
          void prepareSpeakWaveFromBlob(speakRecordedBlob);
        } else {
          speakWaveStaticRows = [];
          drawSpeakWave();
        }
      };

      const playSpeakReplayWithBuffer = async (auto = false) => {
        if (!speakRecordedBlob) {
          return false;
        }
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor) {
          return false;
        }
        try {
          stopSpeakReplay();
          if (!speakReplayUnlockContext || speakReplayUnlockContext.state === "closed") {
            speakReplayUnlockContext = new AudioContextCtor();
          }
          if (speakReplayUnlockContext.state === "suspended" && typeof speakReplayUnlockContext.resume === "function") {
            await speakReplayUnlockContext.resume();
          }
          if (speakReplayUnlockContext.state !== "running") {
            return false;
          }
          const buffer = await speakReplayUnlockContext.decodeAudioData(await speakRecordedBlob.arrayBuffer());
          const analyser = speakReplayUnlockContext.createAnalyser();
          analyser.fftSize = 1024;
          analyser.smoothingTimeConstant = 0.72;
          const source = speakReplayUnlockContext.createBufferSource();
          source.buffer = buffer;
          source.connect(analyser);
          analyser.connect(speakReplayUnlockContext.destination);
          speakWaveAudioContext = speakReplayUnlockContext;
          speakWaveSource = source;
          speakReplayBufferSource = source;
          const replayStartedAt = Number(speakReplayUnlockContext.currentTime || 0);
          const replayClock = {
            paused: false,
            ended: false,
            get currentTime() {
              return Math.max(0, Number(speakReplayUnlockContext.currentTime || 0) - replayStartedAt);
            },
          };
          source.onended = () => {
            replayClock.ended = true;
            if (speakReplayBufferSource === source) {
              speakReplayBufferSource = null;
            }
            clearSpeakReplayTokenHighlight();
            stopSpeakWave("ready");
            updateSpeakReplayButton();
          };
          setSpeakStatus("Đang phát lại bản ghi của bạn...", "");
          startSpeakWave("playing", analyser);
          source.start(0);
          syncSpeakReplayTokenHighlight(replayClock);
          return true;
        } catch (error) {
          clearSpeakReplayTokenHighlight();
          if (!auto) {
            setSpeakStatus(`Không phát lại được bản ghi: ${error && error.message ? error.message : error}`, "error");
          }
          stopSpeakWave("ready");
          updateSpeakReplayButton();
          return false;
        }
      };

      const playSpeakReplay = async (auto = false) => {
        if (!speakRecordedBlob) {
          if (!auto) {
            setSpeakStatus("Chưa có bản ghi để phát lại.", "error");
          }
          return;
        }
        if (speakReplayAudio && !speakReplayAudio.paused) {
          stopSpeakReplay();
          return;
        }
        stopSpeakReplay();
        const url = ensureSpeakRecordingUrl();
        if (!url) {
          return;
        }
        const audio = new Audio(url);
        speakReplayAudio = audio;
        audio.preload = "auto";
        normalizeAudioPlaybackSpeed(audio);
        try {
          const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
          if (AudioContextCtor) {
            speakWaveAudioContext = new AudioContextCtor();
            if (speakWaveAudioContext.state === "suspended" && typeof speakWaveAudioContext.resume === "function") {
              await speakWaveAudioContext.resume().catch(() => {});
            }
            speakWaveAnalyser = speakWaveAudioContext.createAnalyser();
            speakWaveAnalyser.fftSize = 1024;
            speakWaveAnalyser.smoothingTimeConstant = 0.72;
            speakWaveSource = speakWaveAudioContext.createMediaElementSource(audio);
            speakWaveSource.connect(speakWaveAnalyser);
            speakWaveAnalyser.connect(speakWaveAudioContext.destination);
          }
        } catch (error) {
          closeSpeakWaveAudioContext();
        }
        audio.onended = () => {
          speakReplayAudio = null;
          clearSpeakReplayTokenHighlight();
          if (speakReplayButton) {
            speakReplayButton.classList.remove("is-playing");
            speakReplayButton.textContent = "Replay";
          }
          stopSpeakWave("ready");
          updateSpeakReplayButton();
        };
        audio.onerror = () => {
          speakReplayAudio = null;
          clearSpeakReplayTokenHighlight();
          if (speakReplayButton) {
            speakReplayButton.classList.remove("is-playing");
            speakReplayButton.textContent = "Replay";
          }
          stopSpeakWave("ready");
          updateSpeakReplayButton();
          setSpeakStatus("Không phát lại được bản ghi.", "error");
        };
        setSpeakStatus("Đang phát lại bản ghi của bạn...", "");
        if (speakReplayButton) {
          speakReplayButton.classList.add("is-playing");
          speakReplayButton.textContent = "Stop replay";
        }
        updateSpeakReplayButton();
        startSpeakWave("playing", speakWaveAnalyser);
        syncSpeakReplayTokenHighlight(audio);
        try {
          const started = audio.play();
          if (started && typeof started.catch === "function") {
            await started;
          }
        } catch (error) {
          speakReplayAudio = null;
          clearSpeakReplayTokenHighlight();
          if (speakReplayButton) {
            speakReplayButton.classList.remove("is-playing");
            speakReplayButton.textContent = "Replay";
          }
          stopSpeakWave("ready");
          updateSpeakReplayButton();
          if (auto && await playSpeakReplayWithBuffer(true)) {
            return;
          }
          if (auto) {
            setSpeakStatus("Đã chấm xong. Bấm Replay để nghe lại bản ghi.", "");
          } else {
            setSpeakStatus(`Không phát lại được bản ghi: ${error && error.message ? error.message : error}`, "error");
          }
        }
      };

      const setSpeakStatus = (message, kind = "") => {
        if (!speakStatus) {
          return;
        }
        speakStatus.textContent = message || "";
        speakStatus.classList.toggle("is-error", kind === "error");
        speakStatus.classList.toggle("is-ok", kind === "ok");
        scheduleDesktopPanelLayout();
      };

      const setSpeakReportButtonState = (state = "idle") => {
        if (!speakReportButton) {
          return;
        }
        if (state === "sending") {
          speakReportButton.disabled = true;
          speakReportButton.textContent = "Sending report...";
        } else if (state === "pending") {
          speakReportButton.disabled = true;
          speakReportButton.textContent = "Waiting admin";
        } else if (state === "accepted") {
          speakReportButton.disabled = true;
          speakReportButton.textContent = "Skip approved";
        } else {
          speakReportButton.disabled = speakBusy;
          speakReportButton.textContent = "Report error";
        }
      };

      const clearSpeakSkipPolling = () => {
        if (speakSkipPollTimer) {
          window.clearTimeout(speakSkipPollTimer);
          speakSkipPollTimer = 0;
        }
        speakSkipRequestPending = false;
      };

      const speakSkipRequestBody = () => ({
        sessionId: spaceWSpeakSkipSessionId,
        path: currentSpaceWServerPath(),
        identity: clean(currentSpaceWCache && currentSpaceWCache.identity),
        title: clean(currentLessonSource.title || currentLessonSource.name || "Space_W"),
        nodeIndex: currentNodeIndex,
        nodeCount: lessonNodes.length,
        expected: clean(englishNode.textContent),
        reason: "Learner reported a Speak scoring error.",
        review: isReviewPhase(),
      });

      const speakSkipMatchesCurrentNode = (request = {}) => {
        if (!request || typeof request !== "object") {
          return false;
        }
        const requestIdentity = clean(request.identity || request.lesson_identity || "");
        const currentIdentity = clean(currentSpaceWCache && currentSpaceWCache.identity);
        const requestNodeIndex = Math.max(0, Number(request.nodeIndex ?? request.node_index ?? 0) || 0);
        return (!requestIdentity || !currentIdentity || requestIdentity === currentIdentity) && requestNodeIndex === currentNodeIndex;
      };

      const speakSkipMatchesCurrentFile = (request = {}) => {
        if (!request || typeof request !== "object") {
          return false;
        }
        const requestIdentity = clean(request.identity || request.lesson_identity || "");
        const currentIdentity = clean(currentSpaceWCache && currentSpaceWCache.identity);
        const requestSessionId = clean(request.sessionId || request.session_id || "");
        if (requestSessionId && requestSessionId !== spaceWSpeakSkipSessionId) {
          return false;
        }
        const requestProgressKey = clean(request.progressKey || request.progress_key || "");
        const currentProgressKey = clean(currentSpaceWCache && currentSpaceWCache.progressKey);
        const requestPath = clean(request.path || "");
        const currentPath = currentSpaceWServerPath();
        if (requestProgressKey && currentProgressKey && requestProgressKey === currentProgressKey) {
          return true;
        }
        if (requestIdentity && currentIdentity) {
          return requestIdentity === currentIdentity;
        }
        if (requestPath && currentPath) {
          return requestPath === currentPath;
        }
        return Boolean(!requestProgressKey && !requestIdentity && !requestPath && (currentIdentity || currentPath));
      };

      const approveSpeakSkipForCurrentFile = (request = {}) => {
        if (!speakSkipMatchesCurrentFile(request)) {
          return false;
        }
        spaceWSpeakSkipSessionApproved = true;
        speakStepCompleted = true;
        reviewSpeakCompleted = true;
        clearSpeakSkipPolling();
        setSpeakReportButtonState("accepted");
        if (nextPanelCanShow || (speakPanel && speakPanel.classList.contains("is-live"))) {
          showSpeakPanel(true);
          setSpeakStatus("Admin approved Speak skip for this file. Speak is skipped for this session.", "ok");
        }
        updateNextButton(nextPanelCanShow);
        queueSpaceWProgressSave(100);
        return true;
      };

      const applySpeakSkipApproval = (request = {}) => {
        if (clean(request.status).toLowerCase() !== "accepted") {
          return false;
        }
        return approveSpeakSkipForCurrentFile(request);
      };

      const pollSpeakSkipState = async () => {
        if (!authToken || !currentAuthUsername || !currentSpaceWCache || !currentSpaceWCache.identity) {
          return null;
        }
        const query = new URLSearchParams();
        const pathValue = currentSpaceWServerPath();
        if (pathValue) {
          query.set("path", pathValue);
        }
        query.set("sessionId", spaceWSpeakSkipSessionId);
        query.set("identity", currentSpaceWCache.identity);
        query.set("nodeIndex", String(currentNodeIndex));
        const result = await fetchAuthJson(`/space-w/speak-skip/state?${query.toString()}`);
        const request = result && result.payload ? result.payload.request : null;
        if (applySpeakSkipApproval(request || {})) {
          return request;
        }
        if (request && clean(request.status).toLowerCase() === "pending" && speakSkipMatchesCurrentNode(request)) {
          setSpeakReportButtonState("pending");
          setSpeakStatus("Speak error report sent. Waiting for admin approval.", "");
        }
        return request;
      };

      const scheduleSpeakSkipPolling = (delayMs = 2500) => {
        if (speakSkipPollTimer) {
          window.clearTimeout(speakSkipPollTimer);
        }
        speakSkipRequestPending = true;
        speakSkipPollTimer = window.setTimeout(async () => {
          speakSkipPollTimer = 0;
          try {
            const request = await pollSpeakSkipState();
            if (speakSkipRequestPending && (!request || clean(request.status).toLowerCase() === "pending")) {
              scheduleSpeakSkipPolling(3500);
            }
          } catch (error) {
            if (speakSkipRequestPending) {
              scheduleSpeakSkipPolling(5000);
            }
          }
        }, Math.max(400, Number(delayMs) || 2500));
      };

      const requestSpeakSkip = async () => {
        showSpeakPanel(true);
        if (spaceWSpeakSkipSessionApproved) {
          setSpeakReportButtonState("accepted");
          setSpeakStatus("Speak skip is already approved for this file session.", "ok");
          updateNextButton(nextPanelCanShow);
          return;
        }
        if (!authToken || !currentAuthUsername) {
          setSpeakStatus("Please sign in through the server before reporting a Speak error.", "error");
          return;
        }
        if (!currentSpaceWCache || !currentSpaceWCache.identity) {
          setSpeakStatus("This lesson is not ready for server Speak skip approval yet.", "error");
          return;
        }
        setSpeakReportButtonState("sending");
        setSpeakStatus("Sending Speak error report to admin...", "");
        try {
          const result = await fetchAuthJson("/space-w/speak-skip/request", {
            method: "POST",
            body: JSON.stringify(speakSkipRequestBody()),
          });
          const request = result && result.payload ? result.payload.request : null;
          if (!applySpeakSkipApproval(request || {})) {
            setSpeakReportButtonState("pending");
            setSpeakStatus("Speak error report sent. Waiting for admin approval.", "");
            scheduleSpeakSkipPolling(1800);
          }
        } catch (error) {
          setSpeakReportButtonState("idle");
          setSpeakStatus(`Could not send Speak error report: ${error && error.message ? error.message : error}`, "error");
        }
      };

      const setSpeakBusy = (busy) => {
        speakBusy = Boolean(busy);
        if (speakRecordButton) {
          speakRecordButton.disabled = speakBusy;
        }
        if (speakModeToggleButton) {
          speakModeToggleButton.disabled = speakBusy || Boolean(speakRecorder && speakRecorder.state === "recording") || Boolean(speakRecognitionActive);
        }
        if (speakClearButton) {
          speakClearButton.disabled = speakBusy;
        }
        if (!speakSkipRequestPending) {
          setSpeakReportButtonState(spaceWSpeakSkipSessionApproved ? "accepted" : "idle");
        }
        updateSpeakReplayButton();
      };

      const resetSpeakScoringDisplay = () => {
        if (speakScore) {
          speakScore.textContent = "0%";
        }
        if (speakMessage) {
          speakMessage.textContent = "Record the English sentence. Speech analysis will score each word.";
        }
        if (speakTranscript) {
          speakTranscript.textContent = "Your transcript will appear here.";
        }
        if (speakWordsNode) {
          speakWordsNode.textContent = "";
        }
      };

      const resetSpeakResult = () => {
        clearSpeakRecording();
        resetSpeakScoringDisplay();
        if (!speakSkipRequestPending) {
          setSpeakReportButtonState(spaceWSpeakSkipSessionApproved ? "accepted" : "idle");
        }
        setSpeakStatus(spaceWSpeakSkipSessionApproved ? "Speak skip is approved for this file session." : "");
      };

      const updateSpeakConnector = (makeActive = false) => {
        if (!speakPanel || !speakPanel.classList.contains("is-live")) {
          return;
        }
        const activeConnector = connectorForPanel(speakPanel);
        activeConnector.classList.remove("is-complete", "is-dim");
        positionConnectorTo(speakPanel);
        if (!isMobilePanelFlow() && scorePanel && scorePanel.classList.contains("is-live")) {
          positionConnectorTo(scorePanel);
        }
        activeConnector.classList.add("is-live", "is-complete");
        if (makeActive || !connectorTargetPanel) {
          setActivePanel(speakPanel);
        } else {
          setActivePanel(connectorTargetPanel);
        }
        autoPanToPanel(speakPanel);
      };

      const showSpeakPanel = (makeActive = false) => {
        if (!speakPanel) {
          return;
        }
        speakPanel.classList.add("is-live");
        revealMobilePanel("speak");
        window.requestAnimationFrame(() => updateSpeakConnector(makeActive));
        queueSpaceWProgressSave(120);
      };

      const cleanupSpeakStream = () => {
        if (speakStream) {
          speakStream.getTracks().forEach((track) => {
            try {
              track.stop();
            } catch (error) {
            }
          });
        }
        speakStream = null;
      };

      const cancelSpeakRecording = () => {
        clearSpeakAutoReplayTimer();
        stopSpeakReplay();
        if (speakRecognition) {
          stopSpeakBrowserRecognition(false);
        }
        speakRecognitionActive = false;
        speakRecognitionManualStop = false;
        speakRecognitionTranscript = "";
        speakRecognitionChunkText = "";
        speakBrowserRecordingStartedAt = 0;
        speakBrowserTokenTimeline = [];
        clearSpeakReplayTokenHighlight();
        if (speakRecorder && speakRecorder.state !== "inactive") {
          try {
            speakRecorder.onstop = null;
            speakRecorder.stop();
          } catch (error) {
          }
        }
        speakRecorder = null;
        speakChunks = [];
        cleanupSpeakStream();
        stopSpeakWave(speakRecordedBlob ? "ready" : "idle");
        if (speakRecordButton) {
          speakRecordButton.classList.remove("is-recording");
          speakRecordButton.textContent = "Record";
        }
        if (speakModeToggleButton) {
          speakModeToggleButton.disabled = false;
        }
        updateSpeakReplayButton();
      };

      const hideSpeakPanel = () => {
        cancelSpeakRecording();
        if (speakPanel) {
          speakPanel.classList.remove("is-live", "is-recording", "is-playing", "is-processing", "is-mobile-hidden");
        }
        setMobilePanelUnlocked("speak", false);
        syncMobilePanelTabs();
        if (connectorTargetPanel === speakPanel) {
          connectorTargetPanel = null;
        }
        hidePanelConnector(speakPanel);
        setActivePanel(connectorTargetPanel);
        scheduleDesktopPanelLayout();
        resetSpeakResult();
      };

      const speakAudioExtension = (mime) => {
        const lower = clean(mime).toLowerCase();
        if (lower.includes("mp4")) return "m4a";
        if (lower.includes("ogg")) return "ogg";
        if (lower.includes("wav")) return "wav";
        return "webm";
      };

      const selectedRecorderMime = () => {
        if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== "function") {
          return "";
        }
        return [
          "audio/webm;codecs=opus",
          "audio/webm",
          "audio/mp4",
          "audio/ogg;codecs=opus",
        ].find((mime) => MediaRecorder.isTypeSupported(mime)) || "";
      };
