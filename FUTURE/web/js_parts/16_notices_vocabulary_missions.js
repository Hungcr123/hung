

      const hideTaskUserNotice = async (notice = {}, options = {}) => {
        const nativeFaceFrame = taskUserNoticeFace && taskUserNoticeFace.classList.contains("is-native-face")
          ? taskUserNoticeFace.querySelector("iframe")
          : null;
        const noticeStyle = normalizeTaskNoticeStyle(notice.notice_style || notice.noticeStyle || notice.style);
        const nativeExitDelay = noticeStyle === "face1" ? 2450 : 1180;
        postTaskNoticeNativeFaceMessage({ type: "ft-face-speaking", value: false });
        if (nativeFaceFrame && nativeFaceFrame.contentWindow) {
          try {
            nativeFaceFrame.contentWindow.postMessage({ type: "ft-face-exit" }, "*");
          } catch (error) {
          }
        } else {
          stopTaskNoticeFaceGaze();
        }
        if (!options.preview) {
          if (notice && clean(notice.mode || "once") !== "always") {
            await markTaskUserNoticeRead(notice);
          } else if (options.forceRead) {
            await markTaskUserNoticeRead(notice);
          }
        }
        if (taskUserNotice) {
          taskUserNotice.classList.remove("is-speaking");
          if (nativeFaceFrame) {
            await delay(nativeExitDelay);
            postTaskNoticeNativeFaceMessage({ type: "ft-face-destroy" });
            await delay(80);
          }
          taskUserNotice.classList.add("is-hiding");
          await delay(nativeFaceFrame ? (noticeStyle === "face1" ? 260 : 180) : 360);
          taskUserNotice.classList.remove("is-live", "is-hiding", "has-avatar", "is-face-style", "is-hologram-style", "is-compact-hologram", "is-language-en", "is-language-vi", "is-ai-agent-notice", "is-speaking", "has-vi-translation");
        }
        if (nativeFaceFrame) {
          stopTaskNoticeFaceGaze();
        }
        if (taskUserNoticeFace) {
          taskUserNoticeFace.textContent = "";
          taskUserNoticeFace.classList.remove("is-native-face");
        }
        if (taskUserNoticeTextCopy) {
          taskUserNoticeTextCopy.textContent = "";
        } else if (taskUserNoticeText) {
          taskUserNoticeText.textContent = "";
        }
        if (taskUserNoticeTranslationCopy) {
          taskUserNoticeTranslationCopy.textContent = "";
        } else if (taskUserNoticeTranslationText) {
          taskUserNoticeTranslationText.textContent = "";
        }
        if (taskUserNoticeTranslation) {
          taskUserNoticeTranslation.setAttribute("aria-hidden", "true");
        }
        taskAiMetricMeters.forEach((meter) => {
          if (!meter) return;
          meter.hidden = true;
          meter.setAttribute("aria-hidden", "true");
        });
        renderAiNoticeMemoryControls({});
        if (notice && notice._ai_agent) {
          setGhostAiFocusMode(false);
        }
      };

      const settleTaskUserNoticeSpeaking = async (notice = {}, noticeStyle = "hologram", holdMs = 0) => {
        const waitMs = Math.max(0, Number(holdMs) || 0);
        if (waitMs) {
          await delay(waitMs);
        }
        if (taskUserNotice) {
          taskUserNotice.classList.remove("is-speaking");
        }
        const idleHoldMs = notice && notice._ai_agent ? 0 : (noticeStyle === "face1" ? 2200 : 1100);
        postTaskNoticeNativeFaceMessage({ type: "ft-face-speaking", value: false, idleHoldMs });
      };

      const showTaskUserNotice = async (notice = {}, options = {}) => {
        if (!taskUserNotice) {
          return;
        }
        const token = ++taskUserNoticeToken;
        const isPreview = Boolean(options.preview || notice._preview);
        const text = preserveQuestionText(notice.text || "");
        if (!text) {
          return;
        }
        const noticeStyle = normalizeTaskNoticeStyle(notice.notice_style || notice.noticeStyle || notice.style);
        const isFaceStyle = noticeStyle === "face" || noticeStyle === "face1";
        const isHologramStyle = !isFaceStyle;
        const isEnglishNotice = clean(notice.language || "").toLowerCase() === "en";
        const requiresAck = Boolean(notice.require_ack || notice.requireAck || notice._ai_agent);
        const translationVi = isEnglishNotice
          ? (taskNoticeVietnameseTranslation(notice) || (isPreview ? "Bản dịch tiếng Việt sẽ được tạo khi lưu thông báo." : ""))
          : "";
        const taskNoticeEnglishVisualText = taskNoticeEnglishTranslation(notice) || (isEnglishNotice ? text : "");
        const taskNoticeVietnameseVisualText = taskNoticeVietnameseTranslation(notice) || (!isEnglishNotice ? text : "") || translationVi;
        const taskNoticeMainVisualText = isHologramStyle
          ? (isEnglishNotice ? (taskNoticeEnglishVisualText || text) : (taskNoticeVietnameseVisualText || text))
          : (taskNoticeEnglishVisualText || text);
        const taskNoticeMirrorVisualText = isHologramStyle ? "" : taskNoticeVietnameseVisualText;
        const speaker = clean(notice.speaker_name || "Teacher notice");
        const voiceLabel = clean(notice.voice_label || notice.voice || (notice.audio_enabled ? "Voice notice" : "Text notice"));
        if (taskUserNoticeName) taskUserNoticeName.textContent = speaker;
        if (taskUserNoticeVoice) taskUserNoticeVoice.textContent = voiceLabel;
        if (taskUserNoticeTextCopy) {
          taskUserNoticeTextCopy.textContent = taskNoticeMainVisualText;
          taskUserNoticeTextCopy.scrollTop = 0;
        } else if (taskUserNoticeText) {
          taskUserNoticeText.textContent = taskNoticeMainVisualText;
          taskUserNoticeText.scrollTop = 0;
        }
        if (taskUserNoticeTranslationCopy) {
          taskUserNoticeTranslationCopy.textContent = taskNoticeMirrorVisualText;
          taskUserNoticeTranslationCopy.scrollTop = 0;
        } else if (taskUserNoticeTranslationText) {
          taskUserNoticeTranslationText.textContent = taskNoticeMirrorVisualText;
          taskUserNoticeTranslationText.scrollTop = 0;
        }
        if (taskUserNoticeTranslation) {
          taskUserNoticeTranslation.setAttribute("aria-hidden", taskNoticeMirrorVisualText ? "false" : "true");
        }
        updateTaskAiNoticeHud(notice, taskNoticeEnglishVisualText || text, taskNoticeVietnameseVisualText);
        renderAiNoticeMemoryControls(notice);
        if (taskUserNoticeSub) {
          const mode = clean(notice.mode || "once");
          taskUserNoticeSub.hidden = isHologramStyle;
          taskUserNoticeSub.textContent = isHologramStyle
            ? ""
            : notice._ai_agent
            ? "Ghost AI response. English voice is generated on the server."
            : notice._immediate
            ? "Immediate teacher notice."
            : notice._return_replay
            ? "Task reminder: unfinished assigned lessons are still open."
            : mode === "always"
            ? "This notice can appear again when you log in."
            : (mode === "day" ? "This notice can appear for 24 hours after you first see it." : "This notice will be marked as read after it closes.");
        }
        const avatarUrl = isFaceStyle ? "" : taskNoticeAvatarUrl(notice.avatar || "");
        if (taskUserNoticeAvatar) {
          const image = taskUserNoticeAvatar.querySelector("img");
          if (image) {
            image.src = avatarUrl || "";
          }
          taskUserNotice.classList.toggle("has-avatar", !isFaceStyle && Boolean(avatarUrl));
        }
        if (taskUserNoticeRead) {
          taskUserNoticeRead.textContent = notice._ai_agent ? "I understand" : "I have read";
          taskUserNoticeRead.hidden = isPreview || !requiresAck;
        }
        if (!isFaceStyle && taskUserNoticeFace) {
          taskUserNoticeFace.textContent = "";
          taskUserNoticeFace.classList.remove("is-native-face");
        }
        if (!isPreview) {
          recordTaskNoticeDeliveryShown(notice);
          void markTaskUserNoticeSeen(notice);
        }
        if (notice._ai_agent) {
          setGhostAiFocusMode(true);
        }
        taskUserNotice.classList.remove("is-speaking", "is-hiding", "is-face-style", "is-hologram-style", "is-compact-hologram", "is-language-en", "is-language-vi", "has-vi-translation", "is-ai-agent-notice");
        taskUserNotice.classList.toggle("is-face-style", isFaceStyle);
        taskUserNotice.classList.toggle("is-hologram-style", isHologramStyle);
        taskUserNotice.classList.toggle("is-compact-hologram", isHologramStyle);
        taskUserNotice.classList.toggle("is-language-en", isEnglishNotice);
        taskUserNotice.classList.toggle("is-language-vi", !isEnglishNotice);
        taskUserNotice.classList.toggle("has-vi-translation", Boolean(taskNoticeMirrorVisualText));
        taskUserNotice.classList.toggle("is-ai-agent-notice", Boolean(notice._ai_agent));
        taskUserNotice.classList.add("is-live");
        if (isFaceStyle) {
          buildTaskNoticeFaceBlocks(noticeStyle);
        }
        let ackPromise = null;
        if (!isPreview && requiresAck) {
          ackPromise = new Promise((resolve) => {
            if (!taskUserNoticeRead) {
              resolve();
              return;
            }
            const done = () => {
              taskUserNoticeRead.removeEventListener("click", done);
              taskUserNoticeRead.removeEventListener("pointerup", done);
              resolve();
            };
            taskUserNoticeRead.addEventListener("click", done);
            taskUserNoticeRead.addEventListener("pointerup", done);
          });
        }
        await delay(noticeStyle === "face1" ? 2300 : 420);
        const clip = notice && notice.audio ? normalizeAudioClip(notice.audio) : null;
        const audioPromise = clip && notice.audio_enabled
          ? playAudioClipOnce(clip, { volume: 0.96 }).then(() => true).catch(() => false)
          : Promise.resolve(false);
        const animateSpeaking = Boolean(notice._ai_agent && isFaceStyle) || (clip && notice.audio_enabled) || (isPreview && isFaceStyle);
        if (animateSpeaking) {
          taskUserNotice.classList.add("is-speaking");
          postTaskNoticeNativeFaceMessage({ type: "ft-face-speaking", value: true });
        }
        if (!isPreview && requiresAck) {
          if (clip && notice.audio_enabled) {
            await Promise.race([audioPromise, delay(24000)]);
            await settleTaskUserNoticeSpeaking(notice, noticeStyle, notice._ai_agent ? 2000 : 0);
          } else {
            await delay(notice._ai_agent && animateSpeaking ? 2000 : 620);
            if (notice._ai_agent && animateSpeaking) {
              await settleTaskUserNoticeSpeaking(notice, noticeStyle, 0);
            }
          }
          await ackPromise;
          if (token === taskUserNoticeToken) {
            await hideTaskUserNotice(notice, { forceRead: true });
            if (notice._ai_agent && (notice._resume_ai_popup || aiAgentPopupResumeAfterNotice)) {
              aiAgentPopupResumeAfterNotice = false;
              window.setTimeout(() => openAiAgentPopup(), 160);
            }
          }
          return;
        }
        if (clip && notice.audio_enabled) {
          await Promise.race([audioPromise, delay(24000)]);
          taskUserNotice.classList.remove("is-speaking");
          const idleHoldMs = noticeStyle === "face1" ? 2200 : 1100;
          postTaskNoticeNativeFaceMessage({ type: "ft-face-speaking", value: false, idleHoldMs });
          await delay(noticeStyle === "face1" ? 2000 : 900);
        } else {
          await delay(5000);
        }
        if (token === taskUserNoticeToken) {
          await hideTaskUserNotice(notice, { preview: isPreview });
        }
      };

      const pumpTaskUserNoticeQueue = async () => {
        if (taskUserNoticePlaying) {
          return;
        }
        taskUserNoticePlaying = true;
        try {
          while (taskUserNoticeQueue.length) {
            const notice = taskUserNoticeQueue.shift();
            await showTaskUserNotice(notice);
            await delay(500);
          }
        } finally {
          taskUserNoticePlaying = false;
        }
      };

      const taskNoticeDeliveryStorageKey = () => `ft-task-notice-delivery:${clean(currentAuthUsername || "guest").toLowerCase() || "guest"}`;

      const readTaskNoticeDeliveryMap = () => {
        try {
          const parsed = JSON.parse(localStorage.getItem(taskNoticeDeliveryStorageKey()) || "{}");
          return parsed && typeof parsed === "object" ? parsed : {};
        } catch (error) {
          return {};
        }
      };

      const writeTaskNoticeDeliveryMap = (map = {}) => {
        try {
          localStorage.setItem(taskNoticeDeliveryStorageKey(), JSON.stringify(map || {}));
        } catch (error) {
        }
      };

      const taskNoticeDeliveryStats = (noticeId = "") => {
        const id = clean(noticeId);
        if (!id) {
          return { shown: 0, back_count: 0, last_shown_at: 0 };
        }
        const map = readTaskNoticeDeliveryMap();
        const row = map[id] && typeof map[id] === "object" ? map[id] : {};
        return {
          shown: Math.max(0, Number(row.shown || 0) || 0),
          back_count: Math.max(0, Number(row.back_count || row.backCount || 0) || 0),
          last_shown_at: Math.max(0, Number(row.last_shown_at || row.lastShownAt || 0) || 0),
        };
      };

      const updateTaskNoticeDeliveryStats = (noticeId = "", updater = null) => {
        const id = clean(noticeId);
        if (!id) {
          return { shown: 0, back_count: 0, last_shown_at: 0 };
        }
        const map = readTaskNoticeDeliveryMap();
        const previous = taskNoticeDeliveryStats(id);
        const next = typeof updater === "function" ? updater(previous) : previous;
        map[id] = {
          shown: Math.max(0, Number(next.shown || 0) || 0),
          back_count: Math.max(0, Number(next.back_count || next.backCount || 0) || 0),
          last_shown_at: Math.max(0, Number(next.last_shown_at || next.lastShownAt || 0) || 0),
        };
        writeTaskNoticeDeliveryMap(map);
        return map[id];
      };

      const taskNoticeRepeatLimit = (notice = {}) => Math.max(0, Math.min(999, Number(notice.repeat_limit || notice.repeatLimit || notice.max_shows || notice.maxShows || 0) || 0));
      const taskNoticeBackInterval = (notice = {}) => Math.max(1, Math.min(99, Number(notice.back_interval || notice.backInterval || notice.back_gap || notice.backGap || 1) || 1));
      const taskNoticeUntilTasksComplete = (notice = {}) => Boolean(notice.until_tasks_complete || notice.untilTasksComplete || notice.until_complete || notice.untilComplete);

      const taskNoticeCanQueueByDelivery = (notice = {}, options = {}) => {
        const id = clean(notice && notice.id);
        if (!id || options.immediate) {
          return Boolean(id);
        }
        const hasPendingTasks = options.pendingTasks !== undefined ? Boolean(options.pendingTasks) : taskPayloadHasPendingLessons(currentTaskPayload);
        if (taskNoticeUntilTasksComplete(notice) && !hasPendingTasks) {
          return false;
        }
        const stats = taskNoticeDeliveryStats(id);
        const limit = taskNoticeRepeatLimit(notice);
        if (limit > 0 && stats.shown >= limit) {
          return false;
        }
        if (options.replay) {
          const interval = taskNoticeBackInterval(notice);
          const nextBackCount = stats.back_count + 1;
          if (nextBackCount < interval) {
            updateTaskNoticeDeliveryStats(id, (row) => ({ ...row, back_count: nextBackCount }));
            return false;
          }
          updateTaskNoticeDeliveryStats(id, (row) => ({ ...row, back_count: 0 }));
        }
        return true;
      };

      const recordTaskNoticeDeliveryShown = (notice = {}, options = {}) => {
        const id = clean(notice && notice.id);
        if (!id || options.preview || notice._preview || notice._immediate) {
          return;
        }
        updateTaskNoticeDeliveryStats(id, (row) => ({
          ...row,
          shown: Math.max(0, Number(row.shown || 0) || 0) + 1,
          last_shown_at: Date.now(),
        }));
      };

      const isRepeatableTaskNotice = (notice = {}) => {
        const mode = clean(notice && notice.mode).toLowerCase();
        return mode === "always" || mode === "day" || taskNoticeRepeatLimit(notice) > 1 || taskNoticeBackInterval(notice) > 1 || taskNoticeUntilTasksComplete(notice);
      };

      const taskPayloadHasPendingLessons = (payload = {}) => {
        const tasks = lessonTaskDisplayRows(payload);
        return tasks.some((task) => task && !task.completed);
      };

      const lessonTaskSpaceRows = (payload = {}) => {
        const spaceTask = payload.space_task && typeof payload.space_task === "object" ? payload.space_task : {};
        if (Array.isArray(payload.space_tasks)) {
          return payload.space_tasks;
        }
        return Array.isArray(spaceTask.tasks) ? spaceTask.tasks : [];
      };

      // Added 2026-07-28: keep a locally identified unfinished run ahead of untouched task rows.
      const lessonTaskHasActiveRun = (task = {}) => {
        const source = task && typeof task === "object" ? task : {};
        const study = source.study && typeof source.study === "object" ? source.study : {};
        const progress = study.progress && typeof study.progress === "object" ? study.progress : {};
        return [
          source.activeRun ?? source.active_run,
          study.activeRun ?? study.active_run,
          progress.activeRun ?? progress.active_run,
        ].some((value) => value === true || (value && typeof value === "object" && (value.active || value.in_progress)))
          || Boolean(source.in_progress || study.in_progress || progress.in_progress);
      };

      const normalizeLessonTaskActiveRun = (task = {}) => (
        lessonTaskHasActiveRun(task) && task.completed
          ? { ...task, completed: false, complete: false }
          : task
      );

      // Added 2026-07-22: canonical folder identity is shared by sorting, hover metadata, color, and group removal.
      const lessonTaskFolderGroupFromTask = (task = {}) => {
        const path = normalizeServerPathValue(task.path || task.normalized_path || task.effective_path || "");
        const folderId = clean(task.folder_id || task.folderId || "");
        let folderPath = normalizeServerPathValue(task.folder_path || task.folder || "");
        if (!folderPath && path) {
          const parts = path.split("/").filter(Boolean);
          if (parts.length >= 3) {
            folderPath = parts.slice(0, -1).join("/");
          }
        }
        const folderParts = folderPath.split("/").filter(Boolean);
        if (folderPath && (folderParts.length < 2 || (path && !normalizeTaskPath(path).startsWith(`${normalizeTaskPath(folderPath).replace(/\/$/, "")}/`)))) {
          folderPath = "";
        }
        const finalParts = folderPath.split("/").filter(Boolean);
        const folderName = clean(task.folder_name || "") || (finalParts.length ? finalParts[finalParts.length - 1] : "");
        const folderChain = normalizeServerPathValue(task.folder_chain || "") || folderPath;
        const key = clean(task.folder_group_key || "")
          || (folderId ? `folder-id:${folderId.toLowerCase()}` : (folderPath ? `folder-path:${folderPath.toLowerCase()}` : ""));
        return {
          key,
          folderId,
          folderPath,
          folderName,
          folderChain,
          folderBacked: Boolean(key),
        };
      };

      const lessonTaskFolderColor = (groupKey = "") => {
        const value = clean(groupKey || "");
        if (!value) {
          return null;
        }
        let hash = 2166136261;
        for (let index = 0; index < value.length; index += 1) {
          hash ^= value.charCodeAt(index);
          hash = Math.imul(hash, 16777619);
        }
        const unsigned = hash >>> 0;
        return {
          hue: unsigned % 360,
          saturation: 66 + ((unsigned >>> 9) % 18),
          lightness: 48 + ((unsigned >>> 17) % 10),
        };
      };

      const lessonTaskRowIsPdf = (task = {}) => {
        const extension = clean(task.extension || "").toLowerCase();
        const fileType = clean(task.file_type || "").toLowerCase();
        const mimeType = clean(task.mime_type || "").toLowerCase();
        const path = normalizeServerPathValue(task.path || task.effective_path || "").toLowerCase();
        return Boolean(
          task.is_pdf
          || extension === ".pdf"
          || fileType === "pdf"
          || mimeType === "application/pdf"
          || path.endsWith(".space_pdf")
          || path.endsWith(".pdf")
        );
      };

      const lessonTaskTypeKey = (task = {}) => {
        if (lessonTaskRowIsPdf(task)) {
          return "Space_PDF";
        }
        const space = clean(task.space || "");
        if (space) {
          return space;
        }
        const extension = clean(task.extension || "").toLowerCase();
        const fileType = clean(task.file_type || "").toLowerCase();
        const extensionSpace = {
          ".space_v": "Space_V",
          ".space_w": "Space_W",
          ".space_q": "Space_Q",
          ".space_p": "Space_P",
          ".space_s": "Space_S",
          ".space_l": "Space_L",
          ".space_picture": "Space_Picture",
        }[extension];
        return extensionSpace || fileType || extension || "lesson";
      };

      const lessonTaskTypeRank = (typeKey = "") => {
        const ranks = {
          Space_PDF: 0,
          Space_V: 1,
          Space_W: 2,
          Space_Q: 3,
          Space_P: 4,
          Space_S: 5,
          Space_L: 6,
          Space_Picture: 7,
        };
        return Object.prototype.hasOwnProperty.call(ranks, typeKey) ? ranks[typeKey] : 100;
      };

      const lessonTaskMergedSpaceRows = (payload = {}) => {
        const manualTasks = Array.isArray(payload.tasks) ? payload.tasks : [];
        const spaceTasks = lessonTaskSpaceRows(payload);
        const rows = [];
        const seen = new Set();
        [...manualTasks, ...spaceTasks].forEach((rawTask) => {
          const task = normalizeLessonTaskActiveRun(rawTask);
          if (!task || typeof task !== "object") {
            return;
          }
          const key = normalizeTaskPath(task.path || task.effective_path || task.id || "");
          if (key && seen.has(key)) {
            const existingIndex = rows.findIndex((row) => normalizeTaskPath(row.path || row.effective_path || row.id || "") === key);
            if (existingIndex >= 0 && lessonTaskHasActiveRun(task) && !lessonTaskHasActiveRun(rows[existingIndex])) {
              rows[existingIndex] = task;
            }
            return;
          }
          if (key) {
            seen.add(key);
          }
          rows.push(task);
        });
        // Updated 2026-07-22: one global folder rank keeps A/B/C in the same order inside every file-type bucket.
        const folderRanks = new Map();
        rows.forEach((task, index) => {
          const group = lessonTaskFolderGroupFromTask(task);
          const groupKey = group.key || `standalone:${index}`;
          if (!folderRanks.has(groupKey)) {
            folderRanks.set(groupKey, folderRanks.size);
          }
        });
        const typeBuckets = new Map();
        rows.forEach((task, index) => {
          const typeKey = lessonTaskTypeKey(task);
          if (!typeBuckets.has(typeKey)) {
            typeBuckets.set(typeKey, { typeKey, firstIndex: index, groups: new Map() });
          }
          const bucket = typeBuckets.get(typeKey);
          const group = lessonTaskFolderGroupFromTask(task);
          const groupKey = group.key || `standalone:${index}`;
          if (!bucket.groups.has(groupKey)) {
            bucket.groups.set(groupKey, {
              firstIndex: index,
              folderRank: folderRanks.get(groupKey) ?? index,
              rows: [],
            });
          }
          bucket.groups.get(groupKey).rows.push(task);
        });
        const ordered = Array.from(typeBuckets.values())
          .sort((left, right) => lessonTaskTypeRank(left.typeKey) - lessonTaskTypeRank(right.typeKey) || left.firstIndex - right.firstIndex)
          .flatMap((bucket) => Array.from(bucket.groups.values())
            .sort((left, right) => left.folderRank - right.folderRank || left.firstIndex - right.firstIndex)
            .flatMap((group) => group.rows));
        return [
          ...ordered.filter((task) => lessonTaskHasActiveRun(task) && !task.completed),
          ...ordered.filter((task) => !(lessonTaskHasActiveRun(task) && !task.completed)),
        ];
      };

      const authUsernameMatches = (left = "", right = "") => {
        return Boolean(clean(left) && clean(left).toLowerCase() === clean(right).toLowerCase());
      };

      const canManageSpaceTaskFolders = (owner = "") => {
        const targetUser = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        return Boolean(targetUser && (currentAuthIsAdmin || authUsernameMatches(targetUser, currentAuthUsername)));
      };

      const lessonTaskDisplayUsesSpace = (payload = {}) => {
        return true;
      };

      const lessonTaskDisplayRows = (payload = {}) => {
        return lessonTaskDisplayUsesSpace(payload)
          ? lessonTaskMergedSpaceRows(payload)
          : (Array.isArray(payload.tasks) ? payload.tasks : []);
      };

      const taskNoticeReplayText = (notice = {}) => preserveQuestionText(
        notice.text || notice.message || notice.translation_en || notice.translationEn || notice.translation_vi || notice.translationVi || ""
      );

      const taskNoticeReplayOrderValue = (notice = {}, index = 0) => {
        const numericKeys = ["_replay_received_at", "_instant_id", "immediate_event_id", "event_id", "version", "order"];
        const dateKeys = ["sent_at", "sentAt", "updated_at", "updatedAt", "created_at", "createdAt"];
        let value = Number(index) || 0;
        numericKeys.forEach((key) => {
          const numberValue = Number(notice && notice[key]);
          if (Number.isFinite(numberValue) && numberValue > value) {
            value = numberValue;
          }
        });
        dateKeys.forEach((key) => {
          const parsed = Date.parse(clean(notice && notice[key]));
          if (Number.isFinite(parsed) && parsed > value) {
            value = parsed;
          }
        });
        return value;
      };

      const latestTaskNoticeFromList = (notices = []) => {
        if (!Array.isArray(notices) || !notices.length) {
          return null;
        }
        return notices.reduce((latest, notice, index) => {
          if (!notice || !taskNoticeReplayText(notice)) {
            return latest;
          }
          const value = taskNoticeReplayOrderValue(notice, index);
          if (!latest || value >= latest.value) {
            return { notice, value };
          }
          return latest;
        }, null)?.notice || null;
      };

      const rememberLatestTaskNoticeForReplay = (notice = null, options = {}) => {
        if (!notice || !taskNoticeReplayText(notice)) {
          return;
        }
        const replayNotice = options.received ? { ...notice, _replay_received_at: Date.now() } : { ...notice };
        const currentValue = latestReplayableTaskNotice
          ? taskNoticeReplayOrderValue(latestReplayableTaskNotice, 0)
          : -1;
        const nextValue = taskNoticeReplayOrderValue(replayNotice, 0);
        if (!latestReplayableTaskNotice || nextValue >= currentValue) {
          latestReplayableTaskNotice = replayNotice;
        }
      };

      const latestTaskNoticeForReplay = (payload = currentTaskPayload) => {
        const payloadLatest = latestTaskNoticeFromList(Array.isArray(payload && payload.task_notices) ? payload.task_notices : []);
        return latestTaskNoticeFromList([latestReplayableTaskNotice, payloadLatest].filter(Boolean));
      };

      const updateTaskNoticeReplayButtonState = (payload = currentTaskPayload, displayUsesSpace = true) => {
        if (!taskSpaceFoldersButton) {
          return;
        }
        const owner = clean(payload && payload.task_owner || serverTaskOwnerContext || currentAuthUsername);
        const canManageFolders = canManageSpaceTaskFolders(owner);
        taskSpaceFoldersButton.hidden = !displayUsesSpace;
        taskSpaceFoldersButton.disabled = !displayUsesSpace || !canManageFolders;
        taskSpaceFoldersButton.textContent = "Folder task";
        taskSpaceFoldersButton.title = canManageFolders
          ? "Edit automatic Space Task folders. Remove a line to unregister that folder."
          : "Only this learner or an admin can edit automatic Space Task folders.";
        taskSpaceFoldersButton.setAttribute("aria-label", "Edit automatic Space Task folders");
        taskSpaceFoldersButton.classList.toggle("is-task-notice-replay", false);
      };

      const replayLatestTaskNotice = () => {
        const latestNotice = latestTaskNoticeForReplay(currentTaskPayload);
        if (!latestNotice) {
          setLoadStatus("No admin Task Notice is available to replay yet.", true);
          return;
        }
        rememberLatestTaskNoticeForReplay(latestNotice);
        void showTaskUserNotice({
          ...latestNotice,
          _preview: true,
          _return_replay: true,
          _immediate: true,
        }, { preview: true });
        setLoadStatus("Replaying latest Task Notice.");
      };

      const futureFileTypeInfo = (path = "", extension = "", space = "") => {
        const ext = clean(extension).toLowerCase() || ((String(path || "").match(/\.[^.\\/]+$/) || [""])[0] || "").toLowerCase();
        const normalizedSpace = clean(space);
        if (ext === ".space_v" || ext === ".space_b" || normalizedSpace === "Space_V" || normalizedSpace === "Space_B") return { label: ext === ".space_b" ? "B" : "V", className: "is-v", name: "Vocabulary" };
        if (ext === ".space_w" || normalizedSpace === "Space_W") return { label: "W", className: "is-w", name: "Space_W" };
        if (ext === ".space_q" || normalizedSpace === "Space_Q") return { label: "Q", className: "is-q", name: "Question" };
        if (ext === ".space_p" || normalizedSpace === "Space_P") return { label: "P", className: "is-p", name: "Paragraph" };
        if (ext === ".space_s" || normalizedSpace === "Space_S") return { label: "S", className: "is-s", name: "Speaking" };
        if (ext === ".space_l" || normalizedSpace === "Space_L") return { label: "L", className: "is-l", name: "Listening" };
        if (ext === ".pdf" || normalizedSpace === "Space_PDF") return { label: "PDF", className: "is-pdf", name: "PDF" };
        if (isSpacePictureExtension(ext) || normalizedSpace === "Space_Picture") return { label: "PIC", className: "is-pic", name: "Picture" };
        if (ext === ".txt") return { label: "TXT", className: "is-txt", name: "Text" };
        return { label: "FILE", className: "is-file", name: "File" };
      };

      const createFutureFileTypeLogo = (path = "", extension = "", space = "", extraClass = "") => {
        const info = futureFileTypeInfo(path, extension, space);
        const logo = document.createElement("span");
        logo.className = `ft-file-type-logo ${info.className} ${clean(extraClass)}`.trim();
        logo.title = info.name;
        logo.setAttribute("role", "img");
        logo.setAttribute("aria-label", info.name);
        const orbits = document.createElement("span");
        orbits.className = "ft-file-logo-orbits";
        orbits.setAttribute("aria-hidden", "true");
        ["a", "b", "c"].forEach((name) => {
          const orbit = document.createElement("span");
          orbit.className = `ft-file-logo-orbit is-${name}`;
          orbits.appendChild(orbit);
        });
        const label = document.createElement("span");
        label.className = "ft-file-logo-label";
        label.textContent = info.label;
        label.setAttribute("aria-hidden", "true");
        logo.append(orbits, label);
        return logo;
      };

      const queueTaskUserNotices = (notices = [], options = {}) => {
        const immediateMode = Boolean(options.immediate);
        if ((currentAuthIsAdmin && !immediateMode) || !Array.isArray(notices) || !notices.length) {
          return;
        }
        const latestImmediateNotice = (items = []) => items.reduce((latest, notice, index) => {
          const value = Math.max(
            Number(notice && notice._instant_id || 0) || 0,
            Number(notice && notice.immediate_event_id || 0) || 0,
            Number(notice && notice.event_id || 0) || 0,
            index,
          );
          const latestValue = latest
            ? Math.max(
              Number(latest.notice && latest.notice._instant_id || 0) || 0,
              Number(latest.notice && latest.notice.immediate_event_id || 0) || 0,
              Number(latest.notice && latest.notice.event_id || 0) || 0,
              latest.index,
            )
            : -1;
          return value >= latestValue ? { notice, index } : latest;
        }, null);
        const queueSource = immediateMode
          ? [latestImmediateNotice(notices)].filter(Boolean).map((row) => row.notice)
          : notices;
        if (immediateMode) {
          taskUserNoticeQueue = taskUserNoticeQueue.filter((item) => !item || !item._immediate);
        }
        const replayKey = clean(options.replayKey || "");
        const replayMode = Boolean(options.replay && replayKey);
        const pendingTasks = options.pendingTasks !== undefined ? Boolean(options.pendingTasks) : taskPayloadHasPendingLessons(currentTaskPayload);
        queueSource.forEach((notice) => {
          const id = clean(notice && notice.id);
          rememberLatestTaskNoticeForReplay(notice, { received: immediateMode });
          if (replayMode && !immediateMode && !isRepeatableTaskNotice(notice)) {
            return;
          }
          if (!taskNoticeCanQueueByDelivery(notice, {
            immediate: immediateMode,
            replay: replayMode,
            pendingTasks,
          })) {
            return;
          }
          const itemReplayKey = clean((notice && (notice._instant_id || notice.immediate_event_id || notice.event_id)) || replayKey);
          const sessionKey = replayMode
            ? `${id}:replay:${itemReplayKey}`
            : `${id}:${clean(notice && notice.mode) === "always" ? "session" : "once"}`;
          if (!id || taskUserNoticeShownThisSession.has(sessionKey)) {
            return;
          }
          taskUserNoticeShownThisSession.add(sessionKey);
          taskUserNoticeQueue.push(replayMode ? { ...notice, _return_replay: !immediateMode, _immediate: immediateMode || Boolean(notice && notice._immediate) } : notice);
        });
        updateTaskNoticeReplayButtonState(currentTaskPayload, lessonTaskDisplayUsesSpace(currentTaskPayload));
        void pumpTaskUserNoticeQueue();
      };

      const queueTaskNoticeReturnReminder = (payload = {}) => {
        const trigger = pendingTaskNoticeReturnTrigger;
        if (!trigger || currentAuthIsAdmin || payload.admin) {
          pendingTaskNoticeReturnTrigger = null;
          return;
        }
        const notices = (Array.isArray(payload.task_notices) ? payload.task_notices : [])
          .filter(isRepeatableTaskNotice);
        const hasPendingTasks = taskPayloadHasPendingLessons(payload);
        if (!hasPendingTasks || !notices.length) {
          pendingTaskNoticeReturnTrigger = null;
          return;
        }
        queueTaskUserNotices(notices, {
          replay: true,
          replayKey: `return-${trigger.id}`,
          pendingTasks: hasPendingTasks,
        });
        pendingTaskNoticeReturnTrigger = null;
      };

      const taskNoticeImmediateStorageKey = () => `ft-task-notice-immediate:${clean(currentAuthUsername || "guest").toLowerCase() || "guest"}`;

      const storeTaskNoticeImmediateLastId = (id = 0) => {
        taskNoticeImmediateLastId = Math.max(0, Number(id) || 0);
        try {
          localStorage.setItem(taskNoticeImmediateStorageKey(), String(taskNoticeImmediateLastId));
        } catch (error) {
        }
      };

      const readTaskNoticeImmediateLastId = () => {
        try {
          return Math.max(0, Number(localStorage.getItem(taskNoticeImmediateStorageKey()) || 0) || 0);
        } catch (error) {
          return 0;
        }
      };

      const stopTaskNoticeImmediatePolling = () => {
        if (taskNoticeImmediatePollTimer) {
          window.clearTimeout(taskNoticeImmediatePollTimer);
          taskNoticeImmediatePollTimer = 0;
        }
      };

      // Added 2026-07-01: keeps task notice polling lightweight even outside Lesson Vault.
      const shouldPollTaskNoticeImmediate = () => {
        return Boolean(authToken);
      };

      const consumeTaskNoticeImmediatePayload = (payload = {}) => {
        const serverLatestId = Math.max(0, Number(payload.immediate_latest_id || 0) || 0);
        const latestId = Math.max(taskNoticeImmediateLastId, serverLatestId);
        const currentUserKey = clean(currentAuthUsername || "").toLowerCase();
        const notices = (Array.isArray(payload.immediate_notices) ? payload.immediate_notices : [])
          .filter((notice) => {
            const noticeUser = clean(notice && notice.user || "").toLowerCase();
            return !noticeUser || !currentUserKey || noticeUser === currentUserKey;
          });
        if (!taskNoticeImmediatePrimed) {
          taskNoticeImmediatePrimed = true;
          if (!notices.length) {
            storeTaskNoticeImmediateLastId(serverLatestId);
            return;
          }
        }
        if (!notices.length && serverLatestId < taskNoticeImmediateLastId) {
          storeTaskNoticeImmediateLastId(serverLatestId);
          return;
        }
        if (notices.length) {
          const noticeMax = notices.reduce((max, notice) => Math.max(max, Number(notice && notice._instant_id || 0) || 0), serverLatestId);
          storeTaskNoticeImmediateLastId(noticeMax);
          queueTaskUserNotices(notices, {
            replay: true,
            immediate: true,
            replayKey: `instant-${noticeMax}`,
          });
        } else if (latestId > taskNoticeImmediateLastId) {
          storeTaskNoticeImmediateLastId(latestId);
        }
      };

      const pollTaskNoticeImmediate = async () => {
        if (!authToken || !shouldPollTaskNoticeImmediate() || taskNoticeImmediatePollInFlight) {
          return;
        }
        const now = Date.now();
        const minGap = document.visibilityState === "hidden"
          ? TASK_NOTICE_IMMEDIATE_HIDDEN_MS
          : TASK_NOTICE_IMMEDIATE_ACTIVE_MS;
        const waitMs = minGap - (now - Number(taskNoticeImmediateLastPollAt || 0));
        if (taskNoticeImmediateLastPollAt && waitMs > 0) {
          scheduleTaskNoticeImmediatePolling(waitMs);
          return;
        }
        taskNoticeImmediatePollInFlight = true;
        taskNoticeImmediateLastPollAt = now;
        try {
          const result = await fetchAuthJson(`/lesson-task-notices?immediate_after=${encodeURIComponent(String(taskNoticeImmediateLastId || 0))}`);
          consumeTaskNoticeImmediatePayload(result.payload || {});
        } catch (error) {
        } finally {
          taskNoticeImmediatePollInFlight = false;
        }
      };

      const scheduleTaskNoticeImmediatePolling = (delayMs = TASK_NOTICE_IMMEDIATE_ACTIVE_MS) => {
        stopTaskNoticeImmediatePolling();
        if (!authToken || !shouldPollTaskNoticeImmediate()) {
          return;
        }
        const activeDelay = Math.max(TASK_NOTICE_IMMEDIATE_ACTIVE_MS, Number(delayMs) || TASK_NOTICE_IMMEDIATE_ACTIVE_MS);
        const nextDelay = document.visibilityState === "hidden"
          ? Math.max(TASK_NOTICE_IMMEDIATE_HIDDEN_MS, activeDelay)
          : activeDelay;
        taskNoticeImmediatePollTimer = window.setTimeout(async () => {
          taskNoticeImmediatePollTimer = 0;
          await pollTaskNoticeImmediate();
          if (shouldPollTaskNoticeImmediate()) {
            scheduleTaskNoticeImmediatePolling();
          }
        }, nextDelay);
      };

      const startTaskNoticeImmediatePolling = () => {
        stopTaskNoticeImmediatePolling();
        taskNoticeImmediateLastId = readTaskNoticeImmediateLastId();
        taskNoticeImmediatePrimed = false;
        if (!authToken || !shouldPollTaskNoticeImmediate()) {
          return;
        }
        const minGap = document.visibilityState === "hidden"
          ? TASK_NOTICE_IMMEDIATE_HIDDEN_MS
          : TASK_NOTICE_IMMEDIATE_ACTIVE_MS;
        const waitMs = taskNoticeImmediateLastPollAt
          ? minGap - (Date.now() - Number(taskNoticeImmediateLastPollAt || 0))
          : 0;
        if (waitMs > 0) {
          scheduleTaskNoticeImmediatePolling(waitMs);
          return;
        }
        void pollTaskNoticeImmediate().finally(() => scheduleTaskNoticeImmediatePolling());
      };

      const taskSeverityLabel = (value = "") => {
        const severity = clean(value).toLowerCase();
        if (severity === "critical") return "Critical";
        if (severity === "high") return "High priority";
        return "Normal";
      };

      const taskPackLabel = (path = "") => {
        const raw = clean(path).toLowerCase();
        if (raw.endsWith(".space_w")) return "W Pack";
        if (raw.endsWith(".space_b")) return "B Pack";
        if (raw.endsWith(".space_v")) return "V Pack";
        if (raw.endsWith(".space_q")) return "Q Pack";
        if (raw.endsWith(".space_p")) return "P Pack";
        return "Task";
      };

      const taskLearningPath = (task = {}) => normalizeServerPathValue(task && (task.link_target || task.effective_path || task.path) || "");

      const taskLearningEntry = (task = {}) => {
        const learningPath = taskLearningPath(task);
        return learningPath && learningPath !== normalizeServerPathValue(task.path || "")
          ? { ...task, effective_path: learningPath, linked_path: normalizeServerPathValue(task.path || "") }
          : task;
      };

      const taskAssignedAt = (task = {}) => clean(task.assigned_at || task.assignedAt || task.added_at || task.addedAt || "");

      const taskAgeHours = (task = {}) => {
        const raw = taskAssignedAt(task);
        if (!raw) {
          return 0;
        }
        const date = new Date(raw);
        if (!Number.isFinite(date.getTime())) {
          return 0;
        }
        return Math.max(0, (Date.now() - date.getTime()) / 3600000);
      };

      const isTaskOverdue = (task = {}) => !task.completed && taskAgeHours(task) >= 24;

      let taskAssignedChipTimer = 0;
      let lessonTaskPanelAutoRefreshTimer = 0;
      let lessonTaskPanelAutoRefreshBusy = false;
      let lessonTaskPanelPendingRefreshTimer = 0;
      let lessonTaskPanelPendingRefreshTries = 0;
      let lessonTaskPanelLastSignature = "";
      let lessonTaskPanelLastOwnerKey = "";
      const lessonTaskProgressHydrationSignatures = new Map();
      const lessonTaskProgressHydrationInflight = new Set();
      const lessonTaskProgressHydrationFreshUntil = new Map();
      const lessonTaskRuntimeMetrics = { fullRenders: 0, hydrationPatches: 0, hydrationSkips: 0 };
      let lessonTaskPanelMotionSettleTimer = 0;
      const settleLessonTaskPanelMotion = () => {
        if (!serverTaskListNode) {
          return;
        }
        serverTaskListNode.classList.add("is-hydrating");
        if (lessonTaskPanelMotionSettleTimer) {
          window.clearTimeout(lessonTaskPanelMotionSettleTimer);
        }
        lessonTaskPanelMotionSettleTimer = window.setTimeout(() => {
          lessonTaskPanelMotionSettleTimer = 0;
          if (serverTaskListNode) {
            serverTaskListNode.classList.remove("is-hydrating");
          }
        }, 850);
      };
      const lessonVaultFileProgressHydrationSignatures = new Map();
      let taskHoverPreviewTimer = 0;
      let taskHoverPreviewCard = null;
      let taskHoverPreviewNode = null;
      let taskHoverPreviewConnectorNode = null;
      let taskHoverPreviewGuardRaf = 0;
      let taskHoverPreviewGuardBound = false;
      let taskHoverPreviewHideTimer = 0;
      let taskHoverPreviewLastKey = "";
      let taskHoverPreviewLastHiddenAt = 0;
      let taskHoverPreviewSuppressSegmentAnimation = false;
      let lessonVaultTaskFolderHighlightTimer = 0;
      const LESSON_TASK_PANEL_AUTO_REFRESH_MS = 10 * 60 * 1000;
      const LESSON_TASK_PANEL_PENDING_REFRESH_MS = 1200;
      const LESSON_TASK_PANEL_PENDING_REFRESH_MAX_TRIES = 12;

      const taskAssignedAgeInfo = (raw = "") => {
        const date = new Date(clean(raw));
        if (!Number.isFinite(date.getTime())) {
          return null;
        }
        const ageMs = Math.max(0, Date.now() - date.getTime());
        const totalMinutes = Math.max(0, Math.floor(ageMs / 60000));
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        const days = Math.floor(hours / 24);
        const dayHours = hours % 24;
        let label = "Assigned now";
        if (days > 0) {
          label = `Assigned ${days}d${dayHours ? ` ${dayHours}h` : ""}`;
        } else if (hours > 0) {
          label = `Assigned ${hours}h${minutes ? ` ${minutes}m` : ""}`;
        } else if (minutes > 0) {
          label = `Assigned ${minutes}m`;
        }
        return {
          label,
          hours: ageMs / 3600000,
          title: `Assigned at ${date.toLocaleString()}`,
        };
      };

      const syncTaskAssignedChip = (chip) => {
        if (!chip) {
          return false;
        }
        const info = taskAssignedAgeInfo(chip.dataset.assignedAt || "");
        if (!info) {
          return false;
        }
        if (chip.textContent !== info.label) {
          chip.textContent = info.label;
        }
        if (chip.title !== info.title) {
          chip.title = info.title;
        }
        const overdue = info.hours >= 24;
        if (chip.classList.contains("is-overdue") !== overdue) {
          chip.classList.toggle("is-overdue", overdue);
        }
        return true;
      };

      const createTaskAssignedChip = (task = {}) => {
        const raw = taskAssignedAt(task);
        if (!raw) {
          return null;
        }
        const chip = createServerChip("", "assigned-time");
        chip.classList.add("ft-task-assigned-chip");
        chip.dataset.assignedAt = raw;
        syncTaskAssignedChip(chip);
        return chip;
      };

      const taskHoverUsesVietnamese = () => {
        const stats = currentTaskPayload && currentTaskPayload.learning_stats && typeof currentTaskPayload.learning_stats === "object"
          ? currentTaskPayload.learning_stats
          : {};
        const count = Number(stats.vocabulary_words ?? stats.vocabularyWords ?? stats.words ?? 0) || 0;
        return count < 1000;
      };

      const taskHoverKindLabel = (path = "", space = "", useVi = true) => {
        const info = futureFileTypeInfo(path, "", space);
        if (!useVi) {
          if (info.className === "is-v") return "Vocabulary file";
          if (info.className === "is-q") return "Question file";
          if (info.className === "is-p") return "Paragraph file";
          if (info.className === "is-s") return "Speaking file";
          if (info.className === "is-l") return "Listening file";
          if (info.className === "is-w") return "Space_W lesson";
          if (info.className === "is-pdf") return "PDF file";
          if (info.className === "is-pic") return "Picture file";
          return "Lesson file";
        }
        if (info.className === "is-v") return "file tu vung";
        if (info.className === "is-q") return "file cau hoi";
        if (info.className === "is-p") return "file doan van";
        if (info.className === "is-s") return "file noi";
        if (info.className === "is-l") return "file nghe";
        if (info.className === "is-w") return "bai Space_W";
        if (info.className === "is-pdf") return "file PDF";
        if (info.className === "is-pic") return "file hinh anh";
        return "file bai hoc";
      };

      const taskHoverAgeLabel = (hours = 0, useVi = true) => {
        const value = Math.max(0, Number(hours || 0) || 0);
        if (value < 1 / 12) {
          return useVi ? "vua duoc giao" : "just assigned";
        }
        if (value < 1) {
          const minutes = Math.max(1, Math.round(value * 60));
          return useVi ? `${minutes} phut` : `${minutes} min`;
        }
        if (value < 24) {
          const rounded = Math.round(value * 10) / 10;
          return useVi ? `${rounded} gio` : `${rounded}h`;
        }
        const days = Math.floor(value / 24);
        const dayHours = Math.round(value - (days * 24));
        if (useVi) {
          return `${days} ngay${dayHours ? ` ${dayHours} gio` : ""}`;
        }
        return `${days}d${dayHours ? ` ${dayHours}h` : ""}`;
      };

      const taskHoverAssignedLabel = (raw = "", useVi = true) => {
        const date = new Date(clean(raw || ""));
        if (!Number.isFinite(date.getTime())) {
          return useVi ? "vua duoc giao" : "recently assigned";
        }
        return date.toLocaleString(useVi ? "vi-VN" : "en-US", {
          hour: "2-digit",
          minute: "2-digit",
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        });
      };

      const taskHoverDataFromCard = (card) => {
        const useVi = taskHoverUsesVietnamese();
        const title = clean(card?.dataset.hoverTitle || card?.dataset.name || "Lesson task");
        const path = normalizeServerPathValue(card?.dataset.effectivePath || card?.dataset.path || "");
        const relativePath = normalizeServerPathValue(card?.dataset.path || card?.dataset.effectivePath || "");
        const fileName = clean(card?.dataset.filename || "") || (relativePath.split("/").filter(Boolean).pop() || title);
        const fileType = clean(card?.dataset.fileType || card?.dataset.extension || "") || "lesson";
        const folderName = clean(card?.dataset.folderName || "");
        const folderPath = normalizeServerPathValue(card?.dataset.folderPath || "");
        const folderChain = normalizeServerPathValue(card?.dataset.folderChain || "") || folderPath;
        const space = clean(card?.dataset.hoverSpace || "");
        const kind = taskHoverKindLabel(path, space, useVi);
        const assignedAt = clean(card?.dataset.assignedAt || "");
        const date = new Date(assignedAt);
        const ageHours = Number.isFinite(date.getTime()) ? Math.max(0, (Date.now() - date.getTime()) / 3600000) : 0;
        const overdue = ageHours >= 24 && card?.dataset.completed !== "1";
        const autoAssigned = card?.dataset.assignmentSource === "system";
        const source = useVi
          ? (autoAssigned ? "he thong tu dong giao cho ban" : "admin giao cho ban")
          : (autoAssigned ? "automatically assigned by the system" : "assigned to you by admin");
        const assignedLabel = taskHoverAssignedLabel(assignedAt, useVi);
        const ageLabel = taskHoverAgeLabel(ageHours, useVi);
        const remainingHours = Math.max(0, 24 - ageHours);
        const remainingLabel = taskHoverAgeLabel(remainingHours, useVi);
        const progressText = clean(card?.dataset.progressText || "");
        const progressPercent = Math.max(0, Math.min(100, Number(card?.dataset.progressPercent || 0) || 0));
        const status = overdue
          ? (useVi ? "Da vuot 24h" : "Over 24h")
          : (useVi ? `Con khoang ${remainingLabel}` : `About ${remainingLabel} left`);
        const body = overdue
          ? (useVi
            ? `Day la ${kind} ${source} luc ${assignedLabel}. Hien tai da qua ${ageLabel}, vuot muc mong doi 24h. Ban nen hoan thanh som de hang doi Space Task khong bi don lai.`
            : `This ${kind} was ${source} at ${assignedLabel}. It has been ${ageLabel}, past the 24h target. Please finish it soon so your Space Task queue stays clear.`)
          : (useVi
            ? `Day la ${kind} ${source} luc ${assignedLabel}. Mong doi hoan thanh trong 24h; hien tai da qua ${ageLabel}.`
            : `This ${kind} was ${source} at ${assignedLabel}. The expected finish window is 24h; ${ageLabel} has passed.`);
        return {
          useVi,
          title,
          path,
          space,
          kind,
          body,
          status,
          progressText,
          progressPercent,
          overdue,
          autoAssigned,
          kicker: useVi ? "Tin hieu tu file dang giao" : "Signal from assigned file",
          sourceLabel: useVi ? (autoAssigned ? "He thong" : "Admin") : (autoAssigned ? "System" : "Admin"),
          fileName,
          fileType,
          relativePath,
          folderName,
          folderPath,
          folderChain,
        };
      };

      const ensureTaskHoverPreviewNode = () => {
        if (taskHoverPreviewNode) {
          return taskHoverPreviewNode;
        }
        const node = document.createElement("aside");
        node.className = "ft-task-hover-preview";
        node.setAttribute("aria-hidden", "true");

        const panel = document.createElement("div");
        panel.className = "ft-task-hover-panel";
        const kicker = document.createElement("span");
        kicker.className = "ft-task-hover-kicker";
        const title = document.createElement("strong");
        title.className = "ft-task-hover-title";
        const body = document.createElement("span");
        body.className = "ft-task-hover-body";
        const fileMeta = document.createElement("span");
        fileMeta.className = "ft-task-hover-file-meta";
        ["file", "type", "path", "folder", "parents"].forEach((name) => {
          const row = document.createElement("span");
          row.className = `ft-task-hover-file-row is-${name}`;
          const label = document.createElement("span");
          label.className = "ft-task-hover-file-label";
          const value = document.createElement("span");
          value.className = "ft-task-hover-file-value";
          row.append(label, value);
          fileMeta.appendChild(row);
        });
        const chips = document.createElement("span");
        chips.className = "ft-task-hover-chips";
        ["source", "status", "progress"].forEach((name) => {
          const chip = document.createElement("span");
          chip.className = `ft-task-hover-chip is-${name}`;
          chips.appendChild(chip);
        });
        panel.append(kicker, title, body, fileMeta, chips);
        node.append(panel);
        document.body.appendChild(node);
        taskHoverPreviewNode = node;
        ensureTaskHoverPreviewConnectorNode();
        bindTaskHoverPreviewGuard();
        return node;
      };

      const ensureTaskHoverPreviewConnectorNode = () => {
        if (taskHoverPreviewConnectorNode) {
          return taskHoverPreviewConnectorNode;
        }
        const screenConnector = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        screenConnector.setAttribute("class", "ft-task-hover-screen-connector");
        screenConnector.setAttribute("aria-hidden", "true");
        ["glow", "core", "trace"].forEach((kind) => {
          const screenPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
          screenPath.setAttribute("class", `ft-task-hover-screen-path is-${kind}`);
          screenPath.setAttribute("pathLength", "1");
          screenConnector.appendChild(screenPath);
        });
        const segmentGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        segmentGroup.setAttribute("class", "ft-task-hover-screen-segments");
        screenConnector.appendChild(segmentGroup);
        ["source", "target"].forEach((kind) => {
          const node = document.createElementNS("http://www.w3.org/2000/svg", "circle");
          node.setAttribute("class", `ft-task-hover-screen-node is-${kind}`);
          node.setAttribute("r", kind === "source" ? "5.8" : "4.8");
          screenConnector.appendChild(node);
        });
        const endCap = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
        endCap.setAttribute("class", "ft-task-hover-screen-cap is-end");
        screenConnector.appendChild(endCap);
        document.body.appendChild(screenConnector);
        taskHoverPreviewConnectorNode = screenConnector;
        return screenConnector;
      };

      const isTaskHoverPreviewCardLive = (card) => Boolean(
        card &&
        card.isConnected &&
        serverTaskListNode &&
        serverTaskListNode.contains(card) &&
        card.getClientRects &&
        card.getClientRects().length &&
        (
          (card.matches && card.matches(":hover")) ||
          card === document.activeElement ||
          (card.contains && card.contains(document.activeElement))
        )
      );

      const requestTaskHoverPreviewValidation = () => {
        if (!taskHoverPreviewCard || taskHoverPreviewGuardRaf) {
          return;
        }
        taskHoverPreviewGuardRaf = window.requestAnimationFrame(() => {
          taskHoverPreviewGuardRaf = 0;
          const card = taskHoverPreviewCard;
          if (!isTaskHoverPreviewCardLive(card)) {
            hideTaskHoverPreview(card);
            return;
          }
          if (taskHoverPreviewNode && taskHoverPreviewNode.classList.contains("is-visible")) {
            positionTaskHoverPreview(card);
          }
        });
      };

      const bindTaskHoverPreviewGuard = () => {
        if (taskHoverPreviewGuardBound) {
          return;
        }
        taskHoverPreviewGuardBound = true;
        window.addEventListener("scroll", requestTaskHoverPreviewValidation, { passive: true, capture: true });
        window.addEventListener("resize", requestTaskHoverPreviewValidation, { passive: true });
        document.addEventListener("pointermove", requestTaskHoverPreviewValidation, { passive: true });
      };

      const positionTaskHoverPreview = (card) => {
        if (!isTaskHoverPreviewCardLive(card)) {
          hideTaskHoverPreview(card);
          return;
        }
        const node = ensureTaskHoverPreviewNode();
        const logo = card && card.querySelector ? card.querySelector(".ft-task-type-logo") : null;
        const cardRect = card?.getBoundingClientRect ? card.getBoundingClientRect() : null;
        const logoRect = logo?.getBoundingClientRect ? logo.getBoundingClientRect() : null;
        const rect = cardRect || logoRect;
        const browserRect = serverBrowser && serverBrowser.getBoundingClientRect ? serverBrowser.getBoundingClientRect() : null;
        const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
        const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1);
        const popupWidth = Math.max(260, Math.min(420, viewportWidth - 32));
        const leftBoundary = Math.max(16, (browserRect ? browserRect.left : 0) + 18);
        const rightBoundary = Math.min(viewportWidth - 16, (browserRect ? browserRect.right : viewportWidth) - 18);
        const popupGap = 46;
        const canPlaceLeft = rect ? (rect.left - popupWidth - popupGap >= leftBoundary) : true;
        const canPlaceRight = rect ? (rect.right + popupWidth + popupGap <= rightBoundary) : false;
        const popupSide = (canPlaceLeft || !canPlaceRight) ? "left" : "right";
        const rawLeft = rect
          ? (popupSide === "left" ? rect.left - popupWidth - popupGap : rect.right + popupGap)
          : leftBoundary;
        const left = Math.max(leftBoundary, Math.min(rawLeft, rightBoundary - popupWidth));
        const centerY = cardRect ? (cardRect.top + (cardRect.height / 2)) : (logoRect ? (logoRect.top + (logoRect.height / 2)) : 150);
        const topBoundary = Math.max(82, (browserRect ? browserRect.top : 0) + 64);
        const fallbackTop = Math.max(topBoundary, Math.min(
          Math.min(viewportHeight - 172, (browserRect ? browserRect.bottom : viewportHeight) - 172),
          centerY - 206
        ));
        node.style.setProperty("--task-hover-left", `${left}px`);
        node.style.setProperty("--task-hover-top", `${fallbackTop}px`);
        node.style.setProperty("--task-hover-width", `${popupWidth}px`);
        node.style.setProperty("--task-hover-enter-x", popupSide === "left" ? "-10px" : "10px");
        const panelNode = node.querySelector(".ft-task-hover-panel");
        const panelRect = panelNode && panelNode.getBoundingClientRect ? panelNode.getBoundingClientRect() : null;
        const panelHeight = Math.max(
          126,
          Math.ceil(
            Math.max(
              panelNode && panelNode.scrollHeight ? panelNode.scrollHeight : 0,
              panelRect && panelRect.height ? panelRect.height : 0
            )
          )
        );
        const screenConnector = ensureTaskHoverPreviewConnectorNode();
        const connectorPaths = screenConnector ? Array.from(screenConnector.querySelectorAll(".ft-task-hover-screen-path")) : [];
        if (screenConnector && connectorPaths.length && rect) {
          const listRect = serverTaskListNode && serverTaskListNode.getBoundingClientRect ? serverTaskListNode.getBoundingClientRect() : null;
          const visibleRect = cardRect && listRect
            ? {
              left: Math.max(cardRect.left, listRect.left),
              right: Math.min(cardRect.right, listRect.right),
              top: Math.max(cardRect.top, listRect.top),
              bottom: Math.min(cardRect.bottom, listRect.bottom),
            }
            : null;
          const visibleCard = Boolean(visibleRect && visibleRect.right > visibleRect.left && visibleRect.bottom > visibleRect.top);
          const sourceRect = logoRect || (visibleCard ? visibleRect : rect);
          const startX = logoRect
            ? (popupSide === "left" ? (logoRect.left + 2) : (logoRect.right - 2))
            : (popupSide === "left" ? (sourceRect.left + 10) : (sourceRect.right - 10));
          const startY = logoRect
            ? (logoRect.top + (logoRect.height / 2))
            : (visibleCard
              ? Math.max(visibleRect.top + 8, Math.min(visibleRect.bottom - 8, cardRect.top + (cardRect.height / 2)))
              : (sourceRect.top + (sourceRect.height / 2)));
          const iconOffset = Math.max(8, Math.min(24, viewportWidth * 0.01));
          const sourceRailX = popupSide === "left"
            ? ((logoRect ? logoRect.left : sourceRect.left) - iconOffset)
            : ((logoRect ? logoRect.right : sourceRect.right) + iconOffset);
          const sourceRailHeight = Math.max(30, Math.min(58, logoRect ? logoRect.height : sourceRect.height));
          const sourceRailTopY = startY - (sourceRailHeight / 2);
          const sourceRailBottomY = startY + (sourceRailHeight / 2);
          const railLength = popupWidth * 0.8;
          const railInset = Math.max(10, Math.min(18, popupWidth * 0.04));
          const railPlateHeight = 19;
          const popupRailClearance = railPlateHeight / 2;
          const popupBottomToRailCenter = (railPlateHeight / 2) + popupRailClearance;
          const maxPopupTop = Math.max(topBoundary, Math.min(
            viewportHeight - panelHeight - 22,
            (browserRect ? browserRect.bottom : viewportHeight) - panelHeight - 22
          ));
          const minRailY = topBoundary + panelHeight + popupBottomToRailCenter;
          const maxRailY = maxPopupTop + panelHeight + popupBottomToRailCenter;
          const preferredRailY = startY - 42;
          const endY = Math.max(minRailY, Math.min(maxRailY, preferredRailY));
          const top = Math.max(topBoundary, Math.min(maxPopupTop, endY - panelHeight - popupBottomToRailCenter));
          node.style.setProperty("--task-hover-top", `${top}px`);
          const railNearX = popupSide === "left" ? (left + popupWidth - railInset) : (left + railInset);
          const railFarX = popupSide === "left" ? (railNearX - railLength) : (railNearX + railLength);
          const railDirection = popupSide === "left" ? -1 : 1;
          const pathD = [
            `M ${sourceRailX.toFixed(1)} ${sourceRailTopY.toFixed(1)}`,
            `L ${sourceRailX.toFixed(1)} ${sourceRailBottomY.toFixed(1)}`,
            `M ${sourceRailX.toFixed(1)} ${startY.toFixed(1)}`,
            `L ${railNearX.toFixed(1)} ${endY.toFixed(1)}`,
            `L ${railFarX.toFixed(1)} ${endY.toFixed(1)}`,
          ].join(" ");
          screenConnector.setAttribute("viewBox", `0 0 ${viewportWidth} ${viewportHeight}`);
          connectorPaths.forEach((path) => path.setAttribute("d", pathD));
          const segmentGroup = screenConnector.querySelector(".ft-task-hover-screen-segments");
          if (segmentGroup) {
            const stableConnectorUpdate = Boolean(
              taskHoverPreviewCard === card
              && card.classList.contains("is-hover-preview-live")
              && screenConnector.classList.contains("is-visible")
            );
            const segmentGeometryKey = [
              Math.round(railNearX),
              Math.round(endY),
              Math.round(railFarX),
              Math.round(popupWidth),
              popupSide,
            ].join("|");
            const rebuildSegments = !(stableConnectorUpdate && segmentGroup.dataset.geometryKey === segmentGeometryKey);
            const makeSegmentPlatePoints = (x1, y1, x2, y2, t, options = {}) => {
              const dx = x2 - x1;
              const dy = y2 - y1;
              const length = Math.hypot(dx, dy);
              if (!Number.isFinite(length) || length < 24) {
                return null;
              }
              const ux = dx / length;
              const uy = dy / length;
              const px = -uy;
              const py = ux;
              const plateLength = options.plateLength || 38;
              const plateHeight = options.plateHeight || 14;
              const slant = options.slant || 12;
              const cx = x1 + (dx * t);
              const cy = y1 + (dy * t);
              const halfLength = plateLength / 2;
              const halfHeight = plateHeight / 2;
              const topShift = slant / 2;
              const bottomShift = -slant / 2;
              return [
                [cx - (ux * halfLength) - (px * halfHeight) + (ux * topShift), cy - (uy * halfLength) - (py * halfHeight) + (uy * topShift)],
                [cx + (ux * halfLength) - (px * halfHeight) + (ux * topShift), cy + (uy * halfLength) - (py * halfHeight) + (uy * topShift)],
                [cx + (ux * halfLength) + (px * halfHeight) + (ux * bottomShift), cy + (uy * halfLength) + (py * halfHeight) + (uy * bottomShift)],
                [cx - (ux * halfLength) + (px * halfHeight) + (ux * bottomShift), cy - (uy * halfLength) + (py * halfHeight) + (uy * bottomShift)],
              ];
            };
            const appendSegmentPlate = (points, className, delay = 0) => {
              if (!points || !points.length) {
                return;
              }
              const plate = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
              plate.setAttribute("class", `ft-task-hover-screen-segment ${className}`);
              plate.setAttribute("points", points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "));
              plate.style.setProperty("--seg-delay", `${Math.min(220, delay)}ms`);
              if (stableConnectorUpdate || taskHoverPreviewSuppressSegmentAnimation) {
                plate.style.animation = "none";
                plate.style.opacity = "1";
              }
              segmentGroup.appendChild(plate);
            };
            const addRailModules = (x1, y, x2, className, options = {}) => {
              const length = Math.abs(x2 - x1);
              if (!Number.isFinite(length) || length < 72) {
                return;
              }
              const direction = x2 >= x1 ? 1 : -1;
              const gap = options.gap || 14;
              const count = Math.max(3, Math.min(options.maxCount || 5, length >= 300 ? 5 : (length >= 230 ? 4 : 3)));
              const rawModuleLength = (length - (gap * (count - 1))) / count;
              const moduleLength = Math.max(options.minLength || 26, Math.min(options.maxLength || 34, rawModuleLength));
              const totalLength = (moduleLength * count) + (gap * (count - 1));
              const startCenter = x1 + (direction * ((length - totalLength) / 2 + (moduleLength / 2)));
              for (let index = 0; index < count; index += 1) {
                const centerX = startCenter + (direction * index * (moduleLength + gap));
                const leftX = centerX - (direction * (moduleLength / 2));
                const rightX = centerX + (direction * (moduleLength / 2));
                const delay = index * 48;
                appendSegmentPlate(makeSegmentPlatePoints(leftX, y, rightX, y, 0.5, {
                  plateLength: moduleLength,
                  plateHeight: options.plateHeight || 19,
                  slant: options.slant || 11,
                }), `${className} is-module`, delay);
                appendSegmentPlate(makeSegmentPlatePoints(leftX, y - 1, rightX, y - 1, 0.5, {
                  plateLength: Math.max(16, moduleLength - 11),
                  plateHeight: options.highlightHeight || 4,
                  slant: Math.max(5, (options.slant || 11) - 4),
                }), `${className} is-highlight`, delay + 18);
              }
            };
            if (rebuildSegments) {
              while (segmentGroup.firstChild) {
                segmentGroup.removeChild(segmentGroup.firstChild);
              }
              segmentGroup.dataset.geometryKey = segmentGeometryKey;
              addRailModules(railNearX, endY, railFarX, "is-rail", {
                maxCount: 4,
                gap: 14,
                minLength: 28,
                maxLength: 34,
                plateHeight: railPlateHeight,
                highlightHeight: 4,
                slant: 11,
              });
            }
          }
          const sourceNode = screenConnector.querySelector(".ft-task-hover-screen-node.is-source");
          const targetNode = screenConnector.querySelector(".ft-task-hover-screen-node.is-target");
          if (sourceNode) {
            sourceNode.setAttribute("cx", startX.toFixed(1));
            sourceNode.setAttribute("cy", startY.toFixed(1));
          }
          if (targetNode) {
            targetNode.setAttribute("cx", railFarX.toFixed(1));
            targetNode.setAttribute("cy", endY.toFixed(1));
          }
          const endCap = screenConnector.querySelector(".ft-task-hover-screen-cap.is-end");
          if (endCap) {
            const capWidth = 30;
            const capHeight = 14;
            const capSlant = 8;
            const capOuterX = railFarX + (railDirection * 2);
            const capInnerX = railFarX - (railDirection * capWidth);
            const capTopY = endY - (capHeight / 2);
            const capBottomY = endY + (capHeight / 2);
            const capPoints = railDirection < 0
              ? [
                [capOuterX, capTopY],
                [capInnerX + capSlant, capTopY],
                [capInnerX, capBottomY],
                [capOuterX - capSlant, capBottomY],
              ]
              : [
                [capInnerX, capTopY],
                [capOuterX - capSlant, capTopY],
                [capOuterX, capBottomY],
                [capInnerX + capSlant, capBottomY],
              ];
            endCap.setAttribute("points", capPoints.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "));
          }
        }
      };

      const renderTaskHoverPreview = (card) => {
        if (taskHoverPreviewHideTimer) {
          window.clearTimeout(taskHoverPreviewHideTimer);
          taskHoverPreviewHideTimer = 0;
        }
        if (!isTaskHoverPreviewCardLive(card)) {
          hideTaskHoverPreview(card);
          return;
        }
        const previewKey = normalizeTaskPath(card.dataset.effectivePath || card.dataset.path || card.dataset.hoverTitle || "");
        const steadyReconnect = Boolean(
          previewKey
          && previewKey === taskHoverPreviewLastKey
          && Date.now() - taskHoverPreviewLastHiddenAt < 2200
        );
        const data = taskHoverDataFromCard(card);
        const node = ensureTaskHoverPreviewNode();
        const kicker = node.querySelector(".ft-task-hover-kicker");
        const title = node.querySelector(".ft-task-hover-title");
        const body = node.querySelector(".ft-task-hover-body");
        const fileMeta = node.querySelector(".ft-task-hover-file-meta");
        const sourceChip = node.querySelector(".ft-task-hover-chip.is-source");
        const statusChip = node.querySelector(".ft-task-hover-chip.is-status");
        const progressChip = node.querySelector(".ft-task-hover-chip.is-progress");
        if (kicker) kicker.textContent = data.kicker;
        if (title) title.textContent = data.title;
        if (body) body.textContent = data.body;
        if (fileMeta) {
          const metaRows = {
            file: [data.useVi ? "File" : "File", data.fileName],
            type: [data.useVi ? "Loai" : "Type", data.fileType],
            path: [data.useVi ? "QM Home" : "QM Home", data.relativePath],
            folder: [data.useVi ? "Folder" : "Folder", data.folderName],
            parents: [data.useVi ? "Thu muc cha" : "Parents", data.folderChain],
          };
          Object.entries(metaRows).forEach(([name, values]) => {
            const row = fileMeta.querySelector(`.ft-task-hover-file-row.is-${name}`);
            if (!row) {
              return;
            }
            const label = row.querySelector(".ft-task-hover-file-label");
            const value = row.querySelector(".ft-task-hover-file-value");
            if (label) label.textContent = values[0];
            if (value) value.textContent = values[1] || "-";
            row.hidden = !values[1] || (name === "parents" && values[1] === data.folderName);
          });
        }
        if (sourceChip) sourceChip.textContent = data.sourceLabel;
        if (statusChip) {
          statusChip.textContent = data.status;
          statusChip.classList.toggle("is-overdue", data.overdue);
        }
        if (progressChip) {
          progressChip.textContent = data.progressText || (data.progressPercent ? `${Math.round(data.progressPercent)}%` : data.kind);
        }
        const wasVisibleForCard = Boolean(
          taskHoverPreviewCard === card
          && card.classList.contains("is-hover-preview-live")
          && node.classList.contains("is-visible")
        );
        taskHoverPreviewSuppressSegmentAnimation = steadyReconnect;
        try {
          positionTaskHoverPreview(card);
        } finally {
          taskHoverPreviewSuppressSegmentAnimation = false;
        }
        card.classList.add("is-hover-preview-live");
        if (!wasVisibleForCard) {
          node.classList.remove("is-visible");
          if (taskHoverPreviewConnectorNode) {
            taskHoverPreviewConnectorNode.classList.remove("is-visible");
          }
          void node.offsetWidth;
          node.classList.add("is-visible");
          if (taskHoverPreviewConnectorNode) {
            void taskHoverPreviewConnectorNode.getBoundingClientRect();
            taskHoverPreviewConnectorNode.classList.add("is-visible");
          }
        } else {
          node.classList.add("is-visible");
          if (taskHoverPreviewConnectorNode) {
            taskHoverPreviewConnectorNode.classList.add("is-visible");
          }
        }
        node.setAttribute("aria-hidden", "false");
      };

      const hideTaskHoverPreview = (card = null) => {
        if (taskHoverPreviewHideTimer) {
          window.clearTimeout(taskHoverPreviewHideTimer);
          taskHoverPreviewHideTimer = 0;
        }
        if (taskHoverPreviewTimer) {
          window.clearTimeout(taskHoverPreviewTimer);
          taskHoverPreviewTimer = 0;
        }
        const lastCard = taskHoverPreviewCard || card;
        if (lastCard && lastCard.dataset) {
          taskHoverPreviewLastKey = normalizeTaskPath(lastCard.dataset.effectivePath || lastCard.dataset.path || lastCard.dataset.hoverTitle || "");
          taskHoverPreviewLastHiddenAt = Date.now();
        }
        if (taskHoverPreviewCard) {
          taskHoverPreviewCard.classList.remove("is-hover-preview-arming", "is-hover-preview-live");
        }
        if (card) {
          card.classList.remove("is-hover-preview-arming", "is-hover-preview-live");
        }
        taskHoverPreviewCard = null;
        if (taskHoverPreviewNode) {
          taskHoverPreviewNode.classList.remove("is-visible");
          taskHoverPreviewNode.setAttribute("aria-hidden", "true");
        }
        if (taskHoverPreviewConnectorNode) {
          taskHoverPreviewConnectorNode.classList.remove("is-visible");
          taskHoverPreviewConnectorNode.setAttribute("aria-hidden", "true");
        }
      };

      const scheduleHideTaskHoverPreview = (card = null, event = null) => {
        if (event && card && typeof card.contains === "function" && card.contains(event.relatedTarget)) {
          return;
        }
        if (taskHoverPreviewHideTimer) {
          window.clearTimeout(taskHoverPreviewHideTimer);
        }
        taskHoverPreviewHideTimer = window.setTimeout(() => {
          taskHoverPreviewHideTimer = 0;
          hideTaskHoverPreview(card);
        }, 180);
      };

      const scheduleTaskHoverPreview = (card) => {
        if (!card || !card.classList || !card.classList.contains("ft-task-card")) {
          return;
        }
        if (taskHoverPreviewHideTimer) {
          window.clearTimeout(taskHoverPreviewHideTimer);
          taskHoverPreviewHideTimer = 0;
        }
        if (taskHoverPreviewCard === card && (taskHoverPreviewTimer || card.classList.contains("is-hover-preview-arming") || card.classList.contains("is-hover-preview-live"))) {
          return;
        }
        hideTaskHoverPreview();
        taskHoverPreviewCard = card;
        card.classList.add("is-hover-preview-arming");
        taskHoverPreviewTimer = window.setTimeout(() => {
          taskHoverPreviewTimer = 0;
          if (taskHoverPreviewCard === card && card.isConnected) {
            if (isTaskHoverPreviewCardLive(card)) {
              renderTaskHoverPreview(card);
            } else {
              hideTaskHoverPreview(card);
            }
          }
        }, 1000);
      };

      const stopTaskAssignedChipTimer = () => {
        if (taskAssignedChipTimer) {
          window.clearTimeout(taskAssignedChipTimer);
          taskAssignedChipTimer = 0;
        }
      };

      const refreshTaskAssignedChips = () => {
        if (!serverTaskListNode) {
          stopTaskAssignedChipTimer();
          return;
        }
        const chips = Array.from(serverTaskListNode.querySelectorAll(".ft-task-assigned-chip"));
        chips.forEach(syncTaskAssignedChip);
        if (!chips.length || !serverBrowser || serverBrowser.hidden || document.visibilityState === "hidden") {
          stopTaskAssignedChipTimer();
          return;
        }
        stopTaskAssignedChipTimer();
        taskAssignedChipTimer = window.setTimeout(refreshTaskAssignedChips, 60000);
      };

      const stopLessonTaskPanelAutoRefresh = () => {
        if (lessonTaskPanelAutoRefreshTimer) {
          window.clearTimeout(lessonTaskPanelAutoRefreshTimer);
          lessonTaskPanelAutoRefreshTimer = 0;
        }
      };

      const canAutoRefreshLessonTaskPanel = () => Boolean(
        authToken &&
        taskModal &&
        !taskModal.hidden &&
        serverBrowserActivePanel === "task" &&
        document.visibilityState !== "hidden"
      );

      const scheduleLessonTaskPanelAutoRefresh = (delayMs = LESSON_TASK_PANEL_AUTO_REFRESH_MS) => {
        stopLessonTaskPanelAutoRefresh();
        if (!canAutoRefreshLessonTaskPanel()) {
          return;
        }
        lessonTaskPanelAutoRefreshTimer = window.setTimeout(async () => {
          lessonTaskPanelAutoRefreshTimer = 0;
          if (!canAutoRefreshLessonTaskPanel() || lessonTaskPanelAutoRefreshBusy) {
            scheduleLessonTaskPanelAutoRefresh();
            return;
          }
          lessonTaskPanelAutoRefreshBusy = true;
          try {
            await loadLessonTasks(serverTaskOwnerContext || currentAuthUsername);
          } catch (error) {
          } finally {
            lessonTaskPanelAutoRefreshBusy = false;
            scheduleLessonTaskPanelAutoRefresh();
          }
        }, Math.max(1200, Number(delayMs || LESSON_TASK_PANEL_AUTO_REFRESH_MS)));
      };

      const schedulePendingLessonTaskRefresh = (owner = "", delayMs = LESSON_TASK_PANEL_PENDING_REFRESH_MS) => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        if (!authToken || !targetOwner) {
          return;
        }
        if (lessonTaskPanelPendingRefreshTimer) {
          window.clearTimeout(lessonTaskPanelPendingRefreshTimer);
          lessonTaskPanelPendingRefreshTimer = 0;
        }
        lessonTaskPanelPendingRefreshTimer = window.setTimeout(async () => {
          lessonTaskPanelPendingRefreshTimer = 0;
          if (!authToken || !targetOwner) {
            return;
          }
          try {
            const query = new URLSearchParams();
            query.set("user", targetOwner);
            const statusResult = await fetchServerJson(`/lesson-tasks/status?${query.toString()}`, { cache: "no-store" });
            const status = statusResult && statusResult.payload && typeof statusResult.payload === "object" ? statusResult.payload : {};
            if (status.ready) {
              const statusRev = clean(status.updated_rev || status.revision || "");
              const cachedRow = getLessonTaskPanelCacheRow(targetOwner);
              const cachedPayload = cachedRow && cachedRow.payload && typeof cachedRow.payload === "object" ? cachedRow.payload : null;
              const cachedSpaceTask = cachedPayload && cachedPayload.space_task && typeof cachedPayload.space_task === "object" ? cachedPayload.space_task : {};
              const cachedRev = clean(cachedSpaceTask.updated_rev || cachedPayload && cachedPayload.updated_rev || "");
              if (statusRev && cachedRev && statusRev === cachedRev) {
                lessonTaskPanelPendingRefreshTries = 0;
                if (cachedPayload) {
                  renderLessonTaskPanel(cachedPayload);
                }
                return;
              }
              await loadLessonTasks(targetOwner, { fresh: true });
              lessonTaskPanelPendingRefreshTries = 0;
            } else if (lessonTaskPanelPendingRefreshTries < LESSON_TASK_PANEL_PENDING_REFRESH_MAX_TRIES) {
              lessonTaskPanelPendingRefreshTries += 1;
              schedulePendingLessonTaskRefresh(targetOwner, Math.min(4000, Math.max(900, Number(delayMs || LESSON_TASK_PANEL_PENDING_REFRESH_MS) * 1.5)));
            } else {
              lessonTaskPanelPendingRefreshTries = 0;
            }
          } catch (error) {
          }
        }, Math.max(300, Number(delayMs || LESSON_TASK_PANEL_PENDING_REFRESH_MS)));
      };

      const normalizeTaskPath = (value = "") => normalizeServerPathValue(value).toLowerCase();

      const taskIdentityMatches = (task = {}, id = "", path = "") => {
        const targetId = clean(id);
        const targetPath = normalizeTaskPath(path);
        const taskPaths = [
          task.path,
          task.effective_path,
          task.link_target,
        ].map((value) => normalizeTaskPath(value)).filter(Boolean);
        return Boolean(
          (targetId && clean(task.id || "") === targetId) ||
          (targetPath && taskPaths.includes(targetPath))
        );
      };

      const setSelectedTaskPath = (path = "") => {
        serverBrowserFocusedFilePath = normalizeServerPathValue(path || "");
        // Added 2026-07-28: selecting a Lesson Vault row updates the route from RAM; route replay must not re-fetch or sync last-file.
        window.__ftLessonVaultLocalRouteUntil = Date.now() + 15000;
        const targetPath = normalizeTaskPath(serverBrowserFocusedFilePath);
        if (serverTaskListNode) {
          Array.from(serverTaskListNode.querySelectorAll(".ft-task-card")).forEach((card) => {
            const cardPaths = [
              card.dataset.path || "",
              card.dataset.effectivePath || "",
              card.dataset.linkTarget || "",
            ].map((value) => normalizeTaskPath(value)).filter(Boolean);
            card.classList.toggle("is-selected", Boolean(targetPath && cardPaths.includes(targetPath)));
          });
        }
        if (serverListNode) {
          Array.from(serverListNode.querySelectorAll(".ft-server-item")).forEach((item) => {
            const itemPaths = [
              item.dataset.path || "",
              item.dataset.effectivePath || "",
              item.dataset.linkTarget || "",
            ].map((value) => normalizeTaskPath(value)).filter(Boolean);
            const itemMatches = Boolean(targetPath && itemPaths.includes(targetPath));
            item.classList.toggle("is-selected", itemMatches);
            item.classList.toggle("is-task-focus", item.classList.contains("is-file") && itemMatches);
            if (item.classList.contains("is-file") && itemMatches) {
              window.clearTimeout(item._futureTaskFocusBurstTimer || 0);
              item.classList.remove("is-task-focus-burst");
              void item.offsetWidth;
              item.classList.add("is-task-focus-burst");
              item._futureTaskFocusBurstTimer = window.setTimeout(() => {
                item.classList.remove("is-task-focus-burst");
                item._futureTaskFocusBurstTimer = 0;
              }, 2400);
              if (typeof announceSpaceVFileStats === "function") {
                void announceSpaceVFileStats({
                  type: "file",
                  path: normalizeServerPathValue(item.dataset.path || ""),
                  effective_path: normalizeServerPathValue(item.dataset.effectivePath || ""),
                  link_target: normalizeServerPathValue(item.dataset.linkTarget || ""),
                }, item, serverTaskOwnerContext || currentAuthUsername || "");
              }
            }
          });
        }
      };

      const scrollFocusedServerFileIntoView = () => {
        const targetPath = normalizeTaskPath(serverBrowserFocusedFilePath);
        if (!serverListNode || !targetPath) {
          return;
        }
        const targetNode = Array.from(serverListNode.querySelectorAll(".ft-server-item.is-file"))
          .find((item) => [
            item.dataset.path,
            item.dataset.effectivePath,
            item.dataset.linkTarget,
            item.dataset.linkedPath,
            item.dataset.sourcePath,
            item.dataset.originalPath,
          ].some((value) => normalizeTaskPath(value || "") === targetPath));
        if (!targetNode) {
          return;
        }
        try {
          targetNode.scrollIntoView({ block: "center", behavior: "smooth" });
        } catch (error) {
          targetNode.scrollIntoView({ block: "center" });
        }
      };

      // Added 2026-07-22: a Space Task card click marks its direct Lesson Vault folder for five seconds.
      const highlightLessonVaultTaskFolder = (folderPath = "", folderBacked = false) => {
        if (!serverPathNode) {
          return;
        }
        const targetPath = normalizeTaskPath(folderPath);
        const blocks = Array.from(serverPathNode.querySelectorAll(".ft-server-path-block"));
        if (lessonVaultTaskFolderHighlightTimer) {
          window.clearTimeout(lessonVaultTaskFolderHighlightTimer);
          lessonVaultTaskFolderHighlightTimer = 0;
        }
        blocks.forEach((block) => {
          const focused = Boolean(
            targetPath
            && normalizeTaskPath(block.dataset.path || "") === targetPath
          );
          block.classList.toggle("is-task-folder-focus", focused);
          block.classList.toggle("is-folder-backed-task-focus", focused && Boolean(folderBacked));
        });
        if (!targetPath) {
          return;
        }
        lessonVaultTaskFolderHighlightTimer = window.setTimeout(() => {
          lessonVaultTaskFolderHighlightTimer = 0;
          if (serverPathNode) {
            serverPathNode.querySelectorAll(".ft-server-path-block.is-task-folder-focus")
              .forEach((block) => block.classList.remove("is-task-folder-focus", "is-folder-backed-task-focus"));
          }
        }, 5000);
      };

      const focusLessonVaultOnTask = async (task = {}, owner = "") => {
        const filePath = normalizeServerPathValue(task.path || "");
        if (!filePath) {
          return;
        }
        if (serverLessonProgressPrefetchTimer) {
          window.clearTimeout(serverLessonProgressPrefetchTimer);
          serverLessonProgressPrefetchTimer = 0;
        }
        // Added 2026-07-28: task-card focus is a local navigation action; suppress stale delayed progress reads while it replays the row.
        window.__ftLessonVaultProgressHydrationPausedUntil = Date.now() + 15000;
        const targetOwner = clean(owner || currentTaskPayload.task_owner || serverTaskOwnerContext || currentAuthUsername);
        const taskFolderGroup = lessonTaskFolderGroupFromTask(task);
        const canonicalFolder = taskFolderGroup.folderPath;
        const learningPath = taskLearningPath(task) || filePath;
        const parentPath = serverParentPathForFile(learningPath) || canonicalFolder || serverParentPathForFile(filePath);
        highlightLessonVaultTaskFolder("");
        const focusPaths = Array.from(new Set([
          filePath,
          learningPath,
          task.effective_path,
          task.link_target,
          task.linked_path,
          task.canonical_path,
        ].flatMap((path) => {
          const normalized = normalizeServerPathValue(path || "");
          if (!normalized) {
            return [];
          }
          const lower = normalized.toLowerCase();
          if (lessonTaskRowIsPdf(task) && lower.endsWith(".pdf") && !lower.endsWith(".space_pdf")) {
            return [normalized, `${normalized.slice(0, -4)}.space_pdf`];
          }
          return [normalized];
        })));
        // Added 2026-07-28: replay the selected row visuals even when a compact folder payload omits its file entry.
        const replayFocusedVaultRow = () => {
          const wanted = new Set(focusPaths.map((path) => normalizeTaskPath(path)).filter(Boolean));
          const row = Array.from(document.querySelectorAll(".ft-server-item.is-file")).find((node) => [
            node.dataset.path,
            node.dataset.effectivePath,
            node.dataset.linkTarget,
            node.dataset.linkedPath,
            node.dataset.sourcePath,
            node.dataset.originalPath,
          ].some((value) => wanted.has(normalizeTaskPath(value || ""))));
          if (!row) {
            return;
          }
          setSelectedTaskPath(row.dataset.path || focusPaths[0] || filePath);
          // Reuse the normal row-selection handler so its full local entry metadata renders earn chips.
          row.click();
          triggerServerWorkspaceMotionBurst(row, null, { source: "select" });
          window.clearTimeout(row._futureTaskFocusBurstTimer || 0);
          row.classList.remove("is-task-focus-burst");
          void row.offsetWidth;
          row.classList.add("is-task-focus-burst");
          row._futureTaskFocusBurstTimer = window.setTimeout(() => {
            row.classList.remove("is-task-focus-burst");
            row._futureTaskFocusBurstTimer = 0;
          }, 2400);
          if (typeof announceSpaceVFileStats === "function") {
            const rowEntry = (Array.isArray(serverCurrentEntries) ? serverCurrentEntries : []).find((entry) => [
              entry && entry.path,
              entry && entry.effective_path,
              entry && entry.link_target,
              entry && entry.linked_path,
            ].some((value) => wanted.has(normalizeTaskPath(value || "")))) || {
              type: "file",
              path: normalizeServerPathValue(row.dataset.path || ""),
              effective_path: normalizeServerPathValue(row.dataset.effectivePath || ""),
              link_target: normalizeServerPathValue(row.dataset.linkTarget || ""),
            };
            void announceSpaceVFileStats(rowEntry, row, targetOwner);
          }
          window.setTimeout(scrollFocusedServerFileIntoView, 0);
        };
        setSelectedTaskPath(focusPaths[0] || filePath);
        if (serverBrowser) {
          serverBrowser.hidden = false;
          syncServerWorkspaceOpenState();
        }
        if (taskModal) {
          taskModal.hidden = false;
        }
        setServerBrowserPanel("vault");
        const parentAlreadyRendered = Boolean(
          normalizeTaskPath(serverBrowserPath || "") === normalizeTaskPath(parentPath)
          && serverListNode
          && serverListNode.querySelector(".ft-server-item.is-file")
        );
        if (parentAlreadyRendered) {
          setLoadStatus("Task selected from the current Lesson Vault folder. Use Let's go to open it.");
          let parentPayload = { entries: serverCurrentEntries || [] };
          try {
            parentPayload = await loadServerDataPath(parentPath, false, targetOwner, {
              silent: true,
              localCacheOnly: true,
              skipTaskBoardHydrate: true,
              skipBackgroundVerify: true,
              skipChildPrefetch: true,
              skipFolderPersist: true,
              skipRouteLeaveFlush: true,
            }) || parentPayload;
          } catch (error) {
          }
          if (typeof selectServerLessonVaultEntryFromPayload === "function") {
            selectServerLessonVaultEntryFromPayload(parentPayload, focusPaths, {
              rememberFile: false,
              updateRoute: true,
              skipProgressPrefetch: true,
              skipFileStats: false,
              motion: true,
            });
          }
          replayFocusedVaultRow();
          highlightLessonVaultTaskFolder(parentPath, taskFolderGroup.folderBacked);
          window.setTimeout(scrollFocusedServerFileIntoView, 0);
          return;
        }
        setLoadStatus("Opening Lesson Vault at the selected task...");
        try {
          const payload = await loadServerDataPath(parentPath, false, targetOwner, {
            localCacheOnly: true,
            skipTaskBoardHydrate: true,
            skipBackgroundVerify: true,
            skipChildPrefetch: true,
            skipFolderPersist: true,
          });
          if (typeof selectServerLessonVaultEntryFromPayload === "function") {
            selectServerLessonVaultEntryFromPayload(payload || { entries: serverCurrentEntries || [] }, focusPaths, {
            rememberFile: false,
            updateRoute: true,
            skipProgressPrefetch: true,
            skipFileStats: false,
              motion: true,
            });
          } else {
            setSelectedTaskPath(focusPaths[0] || filePath);
          }
          replayFocusedVaultRow();
          window.setTimeout(() => {
            highlightLessonVaultTaskFolder(parentPath, taskFolderGroup.folderBacked);
            replayFocusedVaultRow();
            scrollFocusedServerFileIntoView();
          }, 120);
        } catch (error) {
          replayFocusedVaultRow();
          highlightLessonVaultTaskFolder(parentPath, taskFolderGroup.folderBacked);
          window.setTimeout(scrollFocusedServerFileIntoView, 0);
          setLoadStatus(error && error.message ? error.message : "Could not open Lesson Vault at this task.", true);
        }
      };

      const getStoredServerRecentFile = () => {
        const firstRecent = typeof readStoredServerRecentFiles === "function" ? readStoredServerRecentFiles()[0] : null;
        const path = normalizeServerPathValue(firstRecent && firstRecent.path || getStoredServerFile());
        if (!path) {
          return null;
        }
        const parts = path.split("/").filter(Boolean);
        const name = parts.length ? parts[parts.length - 1] : path;
        const extMatch = name.match(/(\.[^.]+)$/);
        const extension = clean(extMatch && extMatch[1] || "").toLowerCase();
        const typeInfo = extension === ".space_w"
          ? { label: "W", className: "is-recent-w", title: "Space W" }
          : (extension === ".space_v" || extension === ".space_b"
            ? { label: "V", className: "is-recent-v", title: "Space V" }
            : (extension === ".space_q"
              ? { label: "Q", className: "is-recent-q", title: "Space Q" }
              : (extension === ".space_l"
                ? { label: "L", className: "is-recent-l", title: "Space L" }
                : (extension === ".space_s"
                  ? { label: "S", className: "is-recent-s", title: "Space S" }
                  : (extension === ".space_p"
                    ? { label: "P", className: "is-recent-p", title: "Space P" }
                    : (extension === ".pdf"
                      ? { label: "PDF", className: "is-recent-pdf", title: "PDF" }
                      : (isSpacePictureExtension(extension)
                        ? { label: "PIC", className: "is-recent-pic", title: "Picture" }
                        : { label: "FILE", className: "is-recent-file", title: "Lesson file" })))))));
        const displayName = typeof futureFriendlyDisplayName === "function"
          ? futureFriendlyDisplayName(name)
          : name
            .replace(/\.(space_w|space_v|space_b|space_q|space_p|space_s|space_l|pdf|txt|png|jpe?g|jfif|webp|bmp|gif|tiff?)$/i, "")
            .replace(/[_-]+/g, " ")
            .trim() || "Recent lesson";
        return {
          path,
          name,
          displayName,
          extension,
          accessedAt: clean(firstRecent && firstRecent.accessedAt || ""),
          typeInfo,
          parent: serverParentPathForFile(path),
        };
      };

      const formatServerRecentAccessTime = (value = "") => {
        const raw = clean(value);
        if (!raw) {
          return "Chua co thoi gian";
        }
        const date = new Date(raw);
        if (!Number.isFinite(date.getTime())) {
          return raw;
        }
        try {
          return new Intl.DateTimeFormat("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
          }).format(date);
        } catch (error) {
          return date.toLocaleString();
        }
      };

      const describeStoredServerRecentFile = (row = {}) => {
        const path = normalizeServerPathValue(row && row.path || "");
        if (!path) {
          return null;
        }
        const parts = path.split("/").filter(Boolean);
        const name = parts.length ? parts[parts.length - 1] : path;
        const extMatch = name.match(/(\.[^.]+)$/);
        const extension = clean(extMatch && extMatch[1] || "").toLowerCase();
        const typeInfo = extension === ".space_w"
          ? { label: "W", className: "is-recent-w", title: "Space W" }
          : (extension === ".space_v" || extension === ".space_b"
            ? { label: "V", className: "is-recent-v", title: "Space V" }
            : (extension === ".space_q"
              ? { label: "Q", className: "is-recent-q", title: "Space Q" }
              : (extension === ".space_l"
                ? { label: "L", className: "is-recent-l", title: "Space L" }
                : (extension === ".space_s"
                  ? { label: "S", className: "is-recent-s", title: "Space S" }
                  : (extension === ".space_p"
                    ? { label: "P", className: "is-recent-p", title: "Space P" }
                    : (extension === ".pdf"
                      ? { label: "PDF", className: "is-recent-pdf", title: "PDF" }
                      : (isSpacePictureExtension(extension)
                        ? { label: "PIC", className: "is-recent-pic", title: "Picture" }
                        : { label: "FILE", className: "is-recent-file", title: "Lesson file" })))))));
        const displayName = typeof futureFriendlyDisplayName === "function"
          ? futureFriendlyDisplayName(name)
          : name
            .replace(/\.(space_w|space_v|space_b|space_q|space_p|space_s|space_l|pdf|txt|png|jpe?g|jfif|webp|bmp|gif|tiff?)$/i, "")
            .replace(/[_-]+/g, " ")
            .trim() || "Recent lesson";
        return {
          path,
          name,
          displayName,
          extension,
          accessedAt: clean(row && row.accessedAt || ""),
          typeInfo,
          parent: serverParentPathForFile(path),
        };
      };

      const hideServerRecentFilePopover = () => {
        if (!serverRecentFilePopover) {
          return;
        }
        serverRecentFilePopover.classList.remove("is-open");
        serverRecentFilePopover.setAttribute("aria-hidden", "true");
      };

      const openServerRecentHistoryFile = (pathValue = "") => {
        const targetPath = normalizeServerPathValue(pathValue);
        if (!targetPath) {
          return;
        }
        const targetParent = serverParentPathForFile(targetPath);
        setSelectedTaskPath(targetPath);
        rememberServerFile(targetPath, { syncNow: true });
        rememberServerPath(targetParent);
        setLoadStatus("Locating recent lesson in Lesson Vault...");
        loadServerDataPath(targetParent, false, "");
        window.setTimeout(scrollFocusedServerFileIntoView, 120);
      };

      const renderServerRecentFilePopover = (event = null) => {
        if (!serverRecentFilePopover || typeof readStoredServerRecentFiles !== "function") {
          return false;
        }
        const recentRows = readStoredServerRecentFiles()
          .map(describeStoredServerRecentFile)
          .filter(Boolean)
          .slice(0, 20);
        serverRecentFilePopover.innerHTML = "";
        const title = document.createElement("div");
        title.className = "ft-server-recent-popover-title";
        title.textContent = "Recent files";
        serverRecentFilePopover.appendChild(title);
        if (!recentRows.length) {
          const empty = document.createElement("div");
          empty.className = "ft-server-recent-popover-empty";
          empty.textContent = "No recent files yet.";
          serverRecentFilePopover.appendChild(empty);
        } else {
          recentRows.forEach((recent) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "ft-server-recent-popover-item";
            if (recent.typeInfo && recent.typeInfo.className) {
              item.classList.add(recent.typeInfo.className);
            }
            item.dataset.path = recent.path;
            item.title = recent.parent ? serverDisplayPathLabel(recent.parent) : recent.path;
            const orb = document.createElement("span");
            orb.className = "ft-server-recent-orb";
            orb.textContent = recent.typeInfo && recent.typeInfo.label ? recent.typeInfo.label : "FILE";
            const main = document.createElement("span");
            main.className = "ft-server-recent-popover-main";
            const name = document.createElement("span");
            name.className = "ft-server-recent-popover-name";
            name.textContent = recent.displayName || recent.name || "Recent lesson";
            const meta = document.createElement("span");
            meta.className = "ft-server-recent-popover-meta";
            meta.textContent = `${formatServerRecentAccessTime(recent.accessedAt)} | ${recent.parent ? serverDisplayPathLabel(recent.parent) : "Lesson Vault"}`;
            main.append(name, meta);
            item.append(orb, main);
            item.addEventListener("click", (clickEvent) => {
              clickEvent.preventDefault();
              clickEvent.stopPropagation();
              hideServerRecentFilePopover();
              openServerRecentHistoryFile(recent.path);
            });
            serverRecentFilePopover.appendChild(item);
          });
        }
        const viewportWidth = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
        const viewportHeight = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
        const width = Math.min(420, Math.max(280, viewportWidth - 24));
        const x = event && Number.isFinite(event.clientX) ? event.clientX : (serverRecentFileButton ? serverRecentFileButton.getBoundingClientRect().left : 12);
        const y = event && Number.isFinite(event.clientY) ? event.clientY : (serverRecentFileButton ? serverRecentFileButton.getBoundingClientRect().bottom + 8 : 12);
        serverRecentFilePopover.style.width = `${width}px`;
        serverRecentFilePopover.style.left = `${Math.max(12, Math.min(x, viewportWidth - width - 12))}px`;
        serverRecentFilePopover.style.top = `${Math.max(12, Math.min(y, viewportHeight - 120))}px`;
        serverRecentFilePopover.classList.add("is-open");
        serverRecentFilePopover.setAttribute("aria-hidden", "false");
        return true;
      };

      const renderServerRecentFileShortcut = () => {
        const recent = getStoredServerRecentFile();
        if (!serverRecentFileButton) {
          return Boolean(recent);
        }
        if (!recent || !recent.path) {
          if (serverNavNode) {
            serverNavNode.classList.remove("has-recent-file");
          }
          serverRecentFileButton.hidden = true;
          serverRecentFileButton.onclick = null;
          return false;
        }
        if (serverNavNode) {
          serverNavNode.classList.add("has-recent-file");
        }
        serverRecentFileButton.hidden = false;
        serverRecentFileButton.dataset.path = recent.path;
        serverRecentFileButton.title = recent.parent ? `Locate in ${serverDisplayPathLabel(recent.parent)}` : "Locate last accessed lesson";
        serverRecentFileButton.setAttribute("aria-label", `Last accessed file: ${recent.displayName || "Recent lesson"}`);
        serverRecentFileButton.classList.remove("is-recent-w", "is-recent-v", "is-recent-q", "is-recent-p", "is-recent-s", "is-recent-l", "is-recent-pdf", "is-recent-pic", "is-recent-file");
        if (recent.typeInfo && recent.typeInfo.className) {
          serverRecentFileButton.classList.add(recent.typeInfo.className);
        }
        const recentOrb = serverRecentFileButton.querySelector(".ft-server-recent-orb");
        if (recentOrb) {
          recentOrb.textContent = recent.typeInfo && recent.typeInfo.label ? recent.typeInfo.label : "FILE";
          recentOrb.title = recent.typeInfo && recent.typeInfo.title ? recent.typeInfo.title : "Lesson file";
        }
        if (serverRecentFileNameNode) {
          serverRecentFileNameNode.textContent = recent.displayName || "Recent lesson";
        }
        serverRecentFileButton.onclick = () => {
          const targetPath = normalizeServerPathValue(serverRecentFileButton.dataset.path || recent.path);
          if (!targetPath) {
            return;
          }
          openServerRecentHistoryFile(targetPath);
        };
        serverRecentFileButton.oncontextmenu = (event) => {
          event.preventDefault();
          event.stopPropagation();
          renderServerRecentFilePopover(event);
        };
        if (!serverRecentFileButton.dataset.recentPopoverBound) {
          serverRecentFileButton.dataset.recentPopoverBound = "1";
          document.addEventListener("pointerdown", (event) => {
            if (!serverRecentFilePopover || !serverRecentFilePopover.classList.contains("is-open")) {
              return;
            }
            if (serverRecentFilePopover.contains(event.target) || serverRecentFileButton.contains(event.target)) {
              return;
            }
            hideServerRecentFilePopover();
          }, true);
          document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
              hideServerRecentFilePopover();
            }
          }, true);
          window.addEventListener("resize", hideServerRecentFilePopover);
        }
        return true;
      };

      const addTaskChipClass = (chip) => {
        if (chip) {
          chip.classList.add("ft-server-task-chip");
        }
        return chip;
      };

      const createLessonGoButton = () => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "ft-lesson-go-button";
        button.setAttribute("aria-label", "Open this lesson");
        const label = document.createElement("span");
        label.className = "ft-lesson-go-label";
        label.textContent = "Let's go";
        const icon = document.createElement("span");
        icon.className = "ft-lesson-go-icon";
        icon.setAttribute("aria-hidden", "true");
        button.append(label, icon);
        return button;
      };

      const setLessonTaskAddButtonState = (button, task = null) => {
        if (!button) {
          return;
        }
        const inTask = Boolean(task);
        const completed = Boolean(task && task.completed);
        const creatorRole = clean(task && task.creator_role || "").toLowerCase();
        const canRemoveTask = Boolean(task && task.can_remove);
        const taskLabel = creatorRole === "user" && canRemoveTask
          ? "My task"
          : (creatorRole === "user" ? "User task" : "Admin task");
        button.textContent = completed ? "Completed" : (inTask ? taskLabel : "Add task");
        button.disabled = inTask;
        button.classList.toggle("is-add-task", !inTask);
        button.classList.toggle("is-in-task", inTask && !completed);
        button.classList.toggle("is-task-done", completed);
        button.classList.toggle("is-user-task", inTask && creatorRole === "user");
        button.classList.toggle("is-admin-task", inTask && creatorRole !== "user");
        button.setAttribute("aria-label", completed ? "This lesson task is completed" : (inTask ? "This lesson is already in tasks" : "Add this lesson to tasks"));
        button.title = completed ? "Completed task" : (inTask ? `${taskLabel} already exists` : "Add this lesson to your task board");
      };

      const setFolderTaskChooseButtonState = (button, selected = false, options = {}) => {
        if (!button) {
          return;
        }
        const busy = clean(options.busy || "");
        const active = Boolean(selected);
        const label = busy || (active ? "Remove task folder" : "Choose folder task");
        button.classList.toggle("is-folder-task-selected", active);
        button.classList.toggle("is-folder-task-busy", Boolean(busy));
        button.disabled = Boolean(options.disabled);
        button.title = active
          ? "Remove this folder from automatic Space Task."
          : "Use this folder as an automatic Space Task folder.";
        button.setAttribute("aria-label", active ? "Remove automatic Space Task folder" : "Choose automatic Space Task folder");
        button.textContent = label;
      };

      const findVisibleFolderTaskChooseButton = (path = "") => {
        const targetPath = normalizeTaskPath(path);
        if (!serverListNode || !targetPath) {
          return null;
        }
        const row = Array.from(serverListNode.querySelectorAll(".ft-server-item.is-folder")).find(
          (item) => normalizeTaskPath(item.dataset.path || "") === targetPath
        );
        return row ? row.querySelector(".ft-server-folder-task-choose") : null;
      };

      const syncVisibleFolderTaskChooseState = (path = "", selected = false, options = {}) => {
        const targetPath = normalizeTaskPath(path);
        if (!serverListNode || !targetPath) {
          return;
        }
        Array.from(serverListNode.querySelectorAll(".ft-server-item.is-folder")).forEach((item) => {
          if (normalizeTaskPath(item.dataset.path || "") !== targetPath) {
            return;
          }
          item.classList.toggle("is-space-task-folder", Boolean(selected));
          setFolderTaskChooseButtonState(item.querySelector(".ft-server-folder-task-choose"), selected, options);
        });
      };

      const folderTaskPreferredFoldersForOwner = (owner = "") => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        const visibleOwner = clean(serverBrowserPreferredTaskFolderOwner || "");
        if (
          Array.isArray(serverBrowserPreferredTaskFolders)
          && targetOwner
          && visibleOwner
          && authUsernameMatches(targetOwner, visibleOwner)
        ) {
          return serverBrowserPreferredTaskFolders
            .map((item) => normalizeServerPathValue(item))
            .filter(Boolean);
        }
        const spaceTask = currentTaskPayload.space_task && typeof currentTaskPayload.space_task === "object" ? currentTaskPayload.space_task : {};
        return (Array.isArray(spaceTask.preferred_folders) ? spaceTask.preferred_folders : [])
          .map((item) => normalizeServerPathValue(item))
          .filter(Boolean);
      };

      const rememberFolderTaskPreferredFoldersForOwner = (owner = "", folders = []) => {
        serverBrowserPreferredTaskFolderOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        serverBrowserPreferredTaskFolders = Array.isArray(folders)
          ? folders.map((item) => normalizeServerPathValue(item)).filter(Boolean)
          : [];
      };

      // Added 2026-07-28: keep late cached list/task payloads from replacing a newer Space Task folder revision.
      const spaceTaskRevisionOrderValue = (value = "") => {
        const text = clean(value);
        if (!text) {
          return 0;
        }
        const parsed = Date.parse(text);
        return Number.isFinite(parsed) ? parsed : 0;
      };

      const spaceTaskPayloadIsStaleForOwner = (owner = "", incomingSpaceTask = {}) => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        const visibleOwner = clean(serverBrowserPreferredTaskFolderOwner || "");
        if (!targetOwner || !visibleOwner || !authUsernameMatches(targetOwner, visibleOwner)) {
          return false;
        }
        const currentSpaceTask = currentTaskPayload && currentTaskPayload.space_task && typeof currentTaskPayload.space_task === "object"
          ? currentTaskPayload.space_task
          : {};
        const incomingRev = spaceTaskRevisionOrderValue(incomingSpaceTask && incomingSpaceTask.updated_rev);
        const currentRev = spaceTaskRevisionOrderValue(currentSpaceTask && currentSpaceTask.updated_rev);
        return Boolean(incomingRev && currentRev && incomingRev < currentRev);
      };

      const rememberFreshFolderTaskPreferredFoldersForOwner = (owner = "", folders = [], spaceTask = {}) => {
        if (spaceTaskPayloadIsStaleForOwner(owner, spaceTask)) {
          return false;
        }
        rememberFolderTaskPreferredFoldersForOwner(owner, folders);
        return true;
      };

      const spaceTaskFolderMutationOwnerKey = (owner = "") => clean(owner || "").toLowerCase();

      const folderTaskBelongsToFolder = (task = {}, folderPath = "") => {
        const targetFolder = normalizeTaskPath(folderPath);
        if (!targetFolder || !task || typeof task !== "object") {
          return false;
        }
        const taskFolder = normalizeTaskPath(task.folder || "");
        if (taskFolder && taskFolder === targetFolder) {
          return true;
        }
        const prefixes = [
          normalizeTaskPath(task.path || ""),
          normalizeTaskPath(task.effective_path || ""),
          normalizeTaskPath(task.link_target || ""),
        ].filter(Boolean);
        return prefixes.some((value) => value === targetFolder || value.startsWith(`${targetFolder}/`));
      };

      const folderTaskHasVisibleSpaceTaskEntries = (folderPath = "", payload = currentTaskPayload) => {
        const rows = lessonTaskSpaceRows(payload);
        return rows.some((task) => folderTaskBelongsToFolder(task, folderPath));
      };

      const folderTaskActiveFolderSet = (payload = currentTaskPayload) => {
        const spaceTask = payload && payload.space_task && typeof payload.space_task === "object" ? payload.space_task : {};
        return new Set(
          (Array.isArray(spaceTask.active_folders) ? spaceTask.active_folders : [])
            .map((item) => normalizeTaskPath(item))
            .filter(Boolean)
        );
      };

      const folderTaskPendingButtonStateForOwner = (owner = "", folderPath = "", payload = currentTaskPayload) => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        const targetFolderPath = normalizeServerPathValue(folderPath || "");
        const payloadOwner = clean(payload && payload.task_owner || "");
        const spaceTask = payload && payload.space_task && typeof payload.space_task === "object" ? payload.space_task : {};
        if (
          !targetOwner
          || !targetFolderPath
          || !payloadOwner
          || !authUsernameMatches(targetOwner, payloadOwner)
          || !spaceTask.pending
        ) {
          return null;
        }
        const folderKey = normalizeTaskPath(targetFolderPath);
        const preferredSet = new Set(
          folderTaskPreferredFoldersForOwner(targetOwner)
            .map((item) => normalizeTaskPath(item))
            .filter(Boolean)
        );
        const selected = preferredSet.has(folderKey);
        const active = folderTaskActiveFolderSet(payload).has(folderKey) || folderTaskHasVisibleSpaceTaskEntries(targetFolderPath, payload);
        if (selected && !active) {
          return {
            selected: true,
            busy: "",
            disabled: false,
          };
        }
        if (!selected && active) {
          return {
            selected: true,
            busy: "Removing...",
            disabled: true,
          };
        }
        return null;
      };

      const getSpaceTaskFolderMutationState = (owner = "") => {
        const key = spaceTaskFolderMutationOwnerKey(owner || serverTaskOwnerContext || currentAuthUsername);
        return key ? (spaceTaskFolderOwnerMutations.get(key) || null) : null;
      };

      const beginSpaceTaskFolderMutation = (owner = "", state = {}) => {
        const key = spaceTaskFolderMutationOwnerKey(owner || serverTaskOwnerContext || currentAuthUsername);
        if (!key) {
          return null;
        }
        const nextState = {
          pending: true,
          owner: clean(owner || serverTaskOwnerContext || currentAuthUsername),
          folderPath: normalizeServerPathValue(state.folderPath || ""),
          busy: clean(state.busy || ""),
          selectedBefore: Boolean(state.selectedBefore),
          mode: clean(state.mode || ""),
          scope: clean(state.scope || "folder") || "folder",
          refreshTries: Math.max(0, Number(state.refreshTries || 0) || 0),
        };
        spaceTaskFolderOwnerMutations.set(key, nextState);
        return nextState;
      };

      const clearSpaceTaskFolderMutationRefreshTimer = (owner = "") => {
        const key = spaceTaskFolderMutationOwnerKey(owner || serverTaskOwnerContext || currentAuthUsername);
        if (!key) {
          return;
        }
        const timer = spaceTaskFolderMutationRefreshTimers.get(key);
        if (timer) {
          window.clearTimeout(timer);
        }
        spaceTaskFolderMutationRefreshTimers.delete(key);
      };

      const endSpaceTaskFolderMutation = (owner = "") => {
        const key = spaceTaskFolderMutationOwnerKey(owner || serverTaskOwnerContext || currentAuthUsername);
        if (key) {
          spaceTaskFolderOwnerMutations.delete(key);
        }
        clearSpaceTaskFolderMutationRefreshTimer(owner);
      };

      const spaceTaskFolderMutationResolved = (owner = "", payload = currentTaskPayload) => {
        const mutation = getSpaceTaskFolderMutationState(owner);
        if (!mutation) {
          return true;
        }
        const folderPath = normalizeServerPathValue(mutation.folderPath || "");
        const preferredFolders = folderTaskPreferredFoldersForOwner(owner);
        const preferredSet = new Set(preferredFolders.map((item) => normalizeTaskPath(item)).filter(Boolean));
        const activeFolderSet = folderTaskActiveFolderSet(payload);
        const hasVisibleTasks = folderTaskHasVisibleSpaceTaskEntries(folderPath, payload);
        const spaceTask = payload && payload.space_task && typeof payload.space_task === "object" ? payload.space_task : {};
        const pending = Boolean(spaceTask.pending);
        const isSelected = preferredSet.has(normalizeTaskPath(folderPath));
        const isActive = activeFolderSet.has(normalizeTaskPath(folderPath)) || hasVisibleTasks;
        if (clean(mutation.mode) === "save") {
          return !pending;
        }
        if (clean(mutation.mode) === "remove") {
          return !pending && !isSelected && !isActive;
        }
        return !pending && isSelected && isActive;
      };

      const scheduleSpaceTaskFolderMutationRefresh = (owner = "", delayMs = 1200) => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        const key = spaceTaskFolderMutationOwnerKey(targetOwner);
        const mutation = getSpaceTaskFolderMutationState(targetOwner);
        if (!key || !mutation || spaceTaskFolderMutationRefreshTimers.get(key)) {
          return;
        }
        const nextTry = Math.max(1, Math.min(24, Number(mutation.refreshTries || 0) + 1));
        spaceTaskFolderOwnerMutations.set(key, {
          ...mutation,
          refreshTries: nextTry,
        });
        const timer = window.setTimeout(async () => {
          spaceTaskFolderMutationRefreshTimers.delete(key);
          try {
            const query = new URLSearchParams();
            query.set("user", targetOwner);
            const statusResult = await fetchServerJson(`/lesson-tasks/status?${query.toString()}`, { cache: "no-store" });
            const status = statusResult && statusResult.payload && typeof statusResult.payload === "object" ? statusResult.payload : {};
            if (status.ready) {
              await loadLessonTasks(targetOwner, { fresh: true });
            }
          } catch (error) {
          }
          const latestMutation = getSpaceTaskFolderMutationState(targetOwner);
          if (!latestMutation) {
            return;
          }
          if (spaceTaskFolderMutationResolved(targetOwner)) {
            endSpaceTaskFolderMutation(targetOwner);
            syncVisibleFolderTaskChooseButtonsForOwner(targetOwner);
            return;
          }
          if (Number(latestMutation.refreshTries || 0) >= 24) {
            endSpaceTaskFolderMutation(targetOwner);
            syncVisibleFolderTaskChooseButtonsForOwner(targetOwner);
            return;
          }
          syncVisibleFolderTaskChooseButtonsForOwner(targetOwner);
          const retryDelay = Math.min(5000, Math.max(
            1200,
            Math.round(900 * Math.pow(1.35, Math.max(1, Number(latestMutation.refreshTries || 1)))),
          ));
          scheduleSpaceTaskFolderMutationRefresh(targetOwner, retryDelay);
        }, Math.max(300, Number(delayMs || 0)));
        spaceTaskFolderMutationRefreshTimers.set(key, timer);
      };

      const finalizeSpaceTaskFolderMutation = (owner = "") => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        if (spaceTaskFolderMutationResolved(targetOwner)) {
          endSpaceTaskFolderMutation(targetOwner);
        } else {
          scheduleSpaceTaskFolderMutationRefresh(targetOwner, 900);
        }
      };

      const syncVisibleFolderTaskChooseButtonsForOwner = (owner = "") => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        const mutation = getSpaceTaskFolderMutationState(targetOwner);
        const preferredFolderSet = new Set(
          folderTaskPreferredFoldersForOwner(targetOwner)
            .map((item) => normalizeTaskPath(item))
            .filter(Boolean)
        );
        if (!serverListNode || !targetOwner) {
          return;
        }
        Array.from(serverListNode.querySelectorAll(".ft-server-item.is-folder")).forEach((item) => {
          const button = item.querySelector(".ft-server-folder-task-choose");
          if (!button) {
            return;
          }
          const itemPath = normalizeTaskPath(item.dataset.path || "");
          const selected = preferredFolderSet.has(itemPath);
          const pendingState = folderTaskPendingButtonStateForOwner(targetOwner, item.dataset.path || "");
          const isActiveMutation = Boolean(
            mutation
            && itemPath
            && (
              clean(mutation.scope || "folder") === "owner"
              || normalizeTaskPath(mutation.folderPath || "") === itemPath
            )
          );
          const isOwnerWideMutation = Boolean(isActiveMutation && clean(mutation.scope || "folder") === "owner");
          const displaySelected = isOwnerWideMutation
            ? selected
            : (isActiveMutation ? Boolean(mutation.selectedBefore) : Boolean(pendingState ? pendingState.selected : selected));
          const busyLabel = isOwnerWideMutation
            ? ""
            : (isActiveMutation ? clean(mutation.busy || "") : clean(pendingState && pendingState.busy || ""));
          setFolderTaskChooseButtonState(
            button,
            displaySelected,
            {
              busy: busyLabel,
              disabled: Boolean(
                (isActiveMutation && mutation && mutation.pending)
                || (pendingState && pendingState.disabled)
              ),
            }
          );
          item.classList.toggle("is-space-task-folder", displaySelected);
        });
      };

      // Added 2026-06-30: refreshes Lesson Vault circular progress when deferred task hydration updates a visible file.
      const applyVisibleServerProgressState = (item = null, task = null, owner = "", adminView = false) => {
        if (!item || !task || !task.study || typeof task.study !== "object") {
          return;
        }
        const iconColumn = item.querySelector(".ft-server-icon-column");
        if (!iconColumn) {
          return;
        }
        const taskProgressPaths = [
          item.dataset.path || task.path,
          item.dataset.effectivePath || task.effective_path,
          item.dataset.linkTarget || task.link_target,
          item.dataset.linkedPath || task.linked_path,
          item.dataset.sourcePath || task.sourcePath || task.source_path,
          item.dataset.originalPath || task.original_path,
          taskLearningPath(task),
        ];
        const progressView = splitLessonProgressForViewer(task.study || {}, taskProgressPaths, owner);
        const taskStudy = progressView.study || {};
        const taskProgress = taskStudy && taskStudy.progress && typeof taskStudy.progress === "object" ? taskStudy.progress : null;
        const taskProgressPartial = lessonProgressIsActivePartial(taskProgress);
        const adminProgress = adminView ? progressView.adminProgress : null;
        const adminProgressPartial = lessonProgressIsActivePartial(adminProgress);
        const suppressStaleAdminProgress = Boolean(taskProgressPartial && !adminProgressPartial);
        const adminPriorCompletion = adminView && !taskProgressPartial ? adminProgressHasPriorCompletion(task.study || {}, adminProgress) : false;
        const progressNode = createLessonProgressNode(taskStudy, "ft-vault-progress") ||
          (taskProgress ? createLessonProgressNode(taskStudy, "ft-vault-progress", { progress: taskProgress }) : null);
        const adminProgressNode = adminView && adminProgress && !suppressStaleAdminProgress
          ? createLessonProgressNode(task.study || {}, "ft-vault-progress ft-vault-progress-admin", {
            progress: adminProgress,
            variantClass: "is-admin-progress",
            ownerBadge: "AD",
            ownerLabel: "Admin progress",
            labelText: "Admin in progress",
            title: `Admin progress: ${clean(adminProgress.text || "")} - ${Number(adminProgress.percent || 0)}%`,
          })
          : null;
        if (!progressNode && !adminProgressNode) {
          return;
        }
        Array.from(iconColumn.children).forEach((child) => {
          if (child && child.classList && child.classList.contains("ft-vault-progress")) {
            child.remove();
          }
        });
        if (progressNode) {
          iconColumn.appendChild(progressNode);
        }
        if (adminProgressNode) {
          iconColumn.appendChild(adminProgressNode);
        }
        item.classList.toggle("has-progress", Boolean(progressNode || adminProgressNode));
        item.classList.toggle("has-admin-progress", Boolean(adminProgressNode));
        item.classList.toggle("is-studied", Boolean(!taskProgressPartial && Number(taskStudy && taskStudy.mine || 0) > 0));
        item.classList.toggle("is-admin-studied", Boolean(
          adminView &&
          !taskProgressPartial &&
          (
            adminPriorCompletion ||
            (
              adminProgress &&
              !adminProgress.reviewing &&
              (
                adminProgress.completed ||
                adminProgress.complete ||
                Number(adminProgress.percent || 0) >= 100
              )
            )
          )
        ));
      };

      const applyVisibleServerTaskState = (item = null, task = null, owner = "", adminView = false) => {
        if (!item) {
          return;
        }
        const hadTask = item.classList.contains("has-task");
        item.classList.toggle("has-task", Boolean(task));
        item.classList.toggle("is-task-complete", Boolean(task && task.completed));
        applyVisibleServerProgressState(item, task, owner, adminView);
        const addButton = item.querySelector(".ft-server-task-add");
        if (addButton) {
          setLessonTaskAddButtonState(addButton, task);
        }
        const chips = item.querySelector(".ft-server-chip-row");
        if (chips) {
          chips.querySelectorAll(".ft-server-task-chip").forEach((chip) => chip.remove());
          if (task) {
            const taskOwnerLabel = clean(task.creator_role || "").toLowerCase() === "user" ? "My task" : "Admin task";
            chips.appendChild(addTaskChipClass(createServerChip(task.completed ? "Task completed" : taskOwnerLabel, task.completed ? "learned" : "date")));
            if (!task.completed) {
              chips.appendChild(addTaskChipClass(createServerChip(taskSeverityLabel(task.severity), clean(task.severity).toLowerCase() === "critical" ? "total" : "date")));
            }
          }
        }
        // Added 2026-07-28: newly added folder/task files replay the same staggered chip burst as a direct click.
        if (
          task
          && !hadTask
          && chips
          && chips.querySelector(".ft-server-chip")
          && Number(window.__ftLessonTaskMutationBurstUntil || 0) > Date.now()
        ) {
          window.clearTimeout(item._futureTaskFocusBurstTimer || 0);
          item.classList.remove("is-task-focus-burst");
          void item.offsetWidth;
          item.classList.add("is-task-focus-burst");
          item._futureTaskFocusBurstTimer = window.setTimeout(() => {
            item.classList.remove("is-task-focus-burst");
            item._futureTaskFocusBurstTimer = 0;
          }, 2400);
        }
      };

      const findVisibleServerTaskMatch = (item = null, payload = currentTaskPayload) => {
        if (!item || !payload || typeof payload !== "object") {
          return null;
        }
        const tasks = Array.isArray(payload.tasks) ? payload.tasks : [];
        if (!tasks.length) {
          return null;
        }
        const itemPaths = [
          item.dataset.path || "",
          item.dataset.effectivePath || "",
          item.dataset.linkTarget || "",
        ].map((value) => normalizeTaskPath(value)).filter(Boolean);
        return tasks.find((task) => (
          itemPaths.some((pathValue) => taskIdentityMatches(task, "", pathValue))
        )) || null;
      };

      const syncVisibleServerTaskRows = (payload = currentTaskPayload) => {
        if (!serverListNode || !payload || typeof payload !== "object") {
          return;
        }
        const payloadOwner = clean(payload.task_owner || "");
        const visibleOwner = clean(serverBrowserPreferredTaskFolderOwner || serverTaskOwnerContext || currentAuthUsername);
        if (payloadOwner && visibleOwner && !authUsernameMatches(payloadOwner, visibleOwner)) {
          return;
        }
        Array.from(serverListNode.querySelectorAll(".ft-server-item.is-file")).forEach((item) => {
          applyVisibleServerTaskState(item, findVisibleServerTaskMatch(item, payload), payloadOwner || visibleOwner, Boolean(payload.admin));
        });
      };

      const updateVisibleServerTaskState = (path = "", task = null) => {
        const targetPath = normalizeTaskPath(path);
        if (!serverListNode || !targetPath) {
          return;
        }
        Array.from(serverListNode.querySelectorAll(".ft-server-item.is-file")).forEach((item) => {
          if (normalizeTaskPath(item.dataset.path || "") !== targetPath) {
            return;
          }
          applyVisibleServerTaskState(item, task);
        });
      };

      const applyLessonTaskMutation = (payload = {}, owner = "", mode = "upsert") => {
        const targetOwner = clean(payload.task_owner || owner || serverTaskOwnerContext || currentAuthUsername);
        // Keep a mutation for another admin-selected learner out of the visible viewer panel.
        // The target cache is still updated so switching to that learner is immediate.
        const visibleOwner = clean(currentTaskPayload && currentTaskPayload.task_owner || serverTaskOwnerContext || currentAuthUsername);
        const renderTarget = !targetOwner || !visibleOwner || authUsernameMatches(targetOwner, visibleOwner);
        const targetCacheRow = !renderTarget && typeof getLessonTaskPanelCacheRow === "function"
          ? getLessonTaskPanelCacheRow(targetOwner)
          : null;
        const basePayload = renderTarget
          ? currentTaskPayload
          : (targetCacheRow && targetCacheRow.payload && typeof targetCacheRow.payload === "object"
            ? targetCacheRow.payload
            : { task_owner: targetOwner, tasks: [], space_tasks: [] });
        const incomingTasks = Array.isArray(payload.tasks) ? payload.tasks : null;
        let tasks = incomingTasks ? [...incomingTasks] : (Array.isArray(basePayload.tasks) ? [...basePayload.tasks] : []);
        let spaceTasks = Array.isArray(payload.space_tasks)
          ? [...payload.space_tasks]
          : (Array.isArray(basePayload.space_tasks) ? [...basePayload.space_tasks] : []);
        const task = payload.task && typeof payload.task === "object" ? payload.task : null;
        if (mode === "remove") {
          const removed = payload.removed && typeof payload.removed === "object" ? payload.removed : (task || {});
          const removedRows = Array.isArray(payload.removed_tasks) && payload.removed_tasks.length ? payload.removed_tasks : [removed];
          const removedIds = new Set(removedRows.map((item) => clean(item && item.id || "")).filter(Boolean));
          const removedPaths = new Set(removedRows.map((item) => normalizeTaskPath(item && item.path || "")).filter(Boolean));
          const removedGroupKey = clean(payload.folder_group_key || "");
          const shouldRemove = (item = {}) => {
            const itemId = clean(item.id || "");
            const itemPath = normalizeTaskPath(item.path || "");
            const itemGroupKey = lessonTaskFolderGroupFromTask(item).key;
            return Boolean(
              (itemPath && removedPaths.has(itemPath))
              || (!itemPath && itemId && removedIds.has(itemId))
              || (removedGroupKey && itemGroupKey === removedGroupKey)
            );
          };
          tasks = tasks.filter((item) => !shouldRemove(item));
          spaceTasks = spaceTasks.filter((item) => !shouldRemove(item));
          removedRows.forEach((item) => updateVisibleServerTaskState(item && item.path || "", null));
        } else if (task) {
          const taskId = clean(task.id || "");
          const taskPath = normalizeTaskPath(task.path || "");
          const index = tasks.findIndex((item) => taskIdentityMatches(item, taskId, taskPath));
          if (index >= 0) {
            tasks[index] = { ...tasks[index], ...task };
          } else {
            tasks.push(task);
          }
          if (renderTarget) {
            updateVisibleServerTaskState(task.path || "", task);
          }
        }
        // Updated 2026-07-22: persist the same merged mutation payload that is rendered so reload/login cannot restore a stale task schema.
        const nextPayload = {
          ...basePayload,
          ...payload,
          task_owner: targetOwner,
          tasks,
          space_tasks: spaceTasks,
          space_task: payload.space_task || basePayload.space_task || null,
          admin: typeof payload.admin === "boolean" ? payload.admin : (basePayload.admin || currentAuthIsAdmin),
          learning_stats: payload.learning_stats || basePayload.learning_stats || null,
        };
        if (renderTarget) {
          renderLessonTaskPanel(nextPayload);
        }
        rememberLessonTaskPanelCache(targetOwner, nextPayload);
        return task;
      };

      const lessonTaskPanelSignatureTask = (task = {}, owner = "", adminView = false) => {
        const taskProgressPaths = [
          task.path,
          task.effective_path,
          task.link_target,
          taskLearningPath(task),
        ];
        const taskProgressView = splitLessonProgressForViewer(task.study || {}, taskProgressPaths, owner);
        const taskStudy = taskProgressView.study || {};
        const taskAdminProgress = taskProgressView.adminProgress || null;
        const taskProgressInfo = taskStudy.progress && typeof taskStudy.progress === "object" ? taskStudy.progress : {};
        return {
          id: clean(task.id || ""),
          path: normalizeServerPathValue(task.path || ""),
          effectivePath: normalizeServerPathValue(task.effective_path || ""),
          linkTarget: normalizeServerPathValue(task.link_target || ""),
          learningPath: normalizeServerPathValue(taskLearningPath(task) || ""),
          folder: normalizeServerPathValue(task.folder || ""),
          title: typeof futureFriendlyDisplayName === "function" ? futureFriendlyDisplayName(task.title || task.name || task.path || "Lesson task") : clean(task.title || task.name || task.path || "Lesson task"),
          name: typeof futureFriendlyDisplayName === "function" ? futureFriendlyDisplayName(task.name || "") : clean(task.name || ""),
          space: clean(task.space || ""),
          severity: clean(task.severity || "normal").toLowerCase() || "normal",
          completed: Boolean(task.completed),
          available: task.available === false ? false : true,
          spaceTask: Boolean(task.space_task),
          canRemove: Boolean(task.can_remove),
          assignedAt: taskAssignedAt(task),
          userCount: Math.max(0, Number(task.user_count || 0) || 0),
          progressText: clean(taskStudy.progress_text || taskProgressInfo.text || ""),
          progressPercent: Math.max(0, Math.min(100, Number(taskStudy.progress_percent ?? taskProgressInfo.percent ?? 0) || 0)),
          adminProgressText: adminView ? clean(taskAdminProgress && (taskAdminProgress.text || taskAdminProgress.progress_text || "") || "") : "",
          adminProgressPercent: adminView ? Math.max(0, Math.min(100, Number(taskAdminProgress && (taskAdminProgress.percent ?? taskAdminProgress.progress_percent ?? 0) || 0))) : 0,
          adminPriorCompletion: adminView ? adminProgressHasPriorCompletion(task.study || {}, taskAdminProgress) : false,
        };
      };

      const lessonTaskPanelRenderSignature = (payload = {}, tasks = []) => {
        const owner = clean(payload.task_owner || "");
        const spaceTask = payload && payload.space_task && typeof payload.space_task === "object" ? payload.space_task : {};
        return hashSpaceWText(JSON.stringify({
          owner,
          admin: Boolean(payload.admin),
          displayUsesSpace: lessonTaskDisplayUsesSpace(payload),
          pending: Boolean(spaceTask.pending),
          preferredFolders: (Array.isArray(spaceTask.preferred_folders) ? spaceTask.preferred_folders : [])
            .map((item) => normalizeServerPathValue(item))
            .filter(Boolean),
          activeFolders: (Array.isArray(spaceTask.active_folders) ? spaceTask.active_folders : [])
            .map((item) => normalizeServerPathValue(item))
            .filter(Boolean),
          tasks: (Array.isArray(tasks) ? tasks : []).map((task) => lessonTaskPanelSignatureTask(task, owner, Boolean(payload.admin))),
        }));
      };

      const lessonTaskProgressHydrationKey = (paths = [], owner = "", lessonId = "") => [
        clean(owner || currentAuthUsername || ""),
        clean(lessonId || ""),
        ...paths.map((path) => normalizeServerPathValue(path)).filter(Boolean),
      ].join("|").toLowerCase();

      const progressHydrationSignature = (progress = null) => {
        const source = progress && typeof progress === "object" ? progress : {};
        return [
          clean(source.space || ""),
          clean(source.text || ""),
          Number(source.done ?? source.review_done ?? 0) || 0,
          Number(source.total ?? source.review_total ?? 0) || 0,
          Number(source.percent ?? source.review_percent ?? 0) || 0,
          source.reviewing ? "review" : "",
          source.completed ? "done" : "",
        ].join("|");
      };

      const progressRecordFromHydrationPayload = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        if (source.progress && typeof source.progress === "object") {
          return source.progress;
        }
        if (source.record && typeof source.record === "object") {
          return source.record;
        }
        return source.state && typeof source.state === "object" ? source : null;
      };

      // Added 2026-07-24: hydrate one task ring in place instead of rebuilding the whole Space Task list.
      const patchVisibleLessonTaskProgress = (task = {}, taskStudy = {}, progress = null) => {
        if (!serverTaskListNode || !serverTaskListNode.isConnected || !progress || typeof progress !== "object") {
          return false;
        }
        const lessonId = clean(task.lesson_id || task.file_id || "").toLowerCase();
        const paths = [task.path, task.effective_path, task.link_target, taskLearningPath(task)]
          .map((value) => normalizeTaskPath(value))
          .filter(Boolean);
        const card = Array.from(serverTaskListNode.querySelectorAll(".ft-task-card")).find((item) => {
          const cardId = clean(item.dataset.lessonId || item.dataset.fileId || "").toLowerCase();
          if (lessonId && cardId === lessonId) {
            return true;
          }
          return [item.dataset.path, item.dataset.effectivePath, item.dataset.linkTarget]
            .map((value) => normalizeTaskPath(value))
            .some((value) => value && paths.includes(value));
        });
        if (!card) {
          lessonTaskRuntimeMetrics.hydrationSkips += 1;
          return false;
        }
        let stack = card.querySelector(".ft-task-progress-stack");
        if (!stack) {
          stack = document.createElement("span");
          stack.className = "ft-task-progress-stack";
          card.insertBefore(stack, card.querySelector(".ft-task-type-logo"));
        }
        const previous = Array.from(stack.children).find((node) => node.classList && node.classList.contains("ft-task-progress") && !node.classList.contains("ft-task-progress-admin"));
        const next = createLessonProgressNode(taskStudy || {}, "ft-task-progress", { progress });
        if (!next) {
          lessonTaskRuntimeMetrics.hydrationSkips += 1;
          return false;
        }
        if (previous) {
          previous.replaceWith(next);
        } else {
          stack.insertBefore(next, stack.firstChild || null);
        }
        card.dataset.progressText = clean(progress.text || "");
        card.dataset.progressPercent = String(Math.max(0, Math.min(100, Number(progress.percent || 0) || 0)));
        card.classList.add("has-progress");
        lessonTaskRuntimeMetrics.hydrationPatches += 1;
        return true;
      };

      // Added 2026-07-24: canonical server summaries must outrank contradictory legacy record flags during hydration.
      const canonicalProgressSummaryFromHydration = (space = "", payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        const summary = source.summary && typeof source.summary === "object" ? source.summary : null;
        if (!summary || !Object.prototype.hasOwnProperty.call(summary, "done") || !Object.prototype.hasOwnProperty.call(summary, "total")) {
          return null;
        }
        const expectedSpace = clean(space);
        const summarySpace = clean(summary.space || expectedSpace);
        if (expectedSpace && summarySpace && summarySpace !== expectedSpace) {
          return null;
        }
        const total = Math.max(0, Math.floor(Number(summary.total) || 0));
        if (!total) {
          return null;
        }
        const done = Math.max(0, Math.min(total, Math.floor(Number(summary.done) || 0)));
        const percent = Math.max(0, Math.min(100, Math.floor(Number(summary.percent) || Math.round((done / total) * 100))));
        const completed = Boolean(summary.completed ?? summary.complete);
        const activeRun = Boolean(summary.activeRun ?? summary.active_run);
        const completedRuns = Math.max(0, Math.floor(Number(summary.completedRuns ?? summary.completed_runs ?? 0) || 0));
        const previouslyCompleted = Boolean(summary.previously_completed ?? summary.previouslyCompleted);
        return {
          ...summary,
          space: summarySpace || expectedSpace,
          done,
          total,
          percent,
          text: clean(summary.text) || `${done}/${total}`,
          completed,
          complete: completed,
          activeRun,
          active_run: activeRun,
          in_progress: Boolean(summary.in_progress ?? (!completed && (done > 0 || activeRun))),
          previously_completed: previouslyCompleted,
          previouslyCompleted,
          completed_runs: completedRuns,
          completedRuns,
          syncing: true,
        };
      };

      const progressOverrideFromHydration = (space = "", payload = {}) => {
        const canonicalSummary = canonicalProgressSummaryFromHydration(space, payload);
        if (canonicalSummary) {
          return canonicalSummary;
        }
        const record = progressRecordFromHydrationPayload(payload);
        if (!record) {
          return null;
        }
        if (space === "Space_V") {
          return vocabProgressOverrideFromRecord(record);
        }
        if (space === "Space_Q") {
          return questionProgressOverrideFromRecord(record);
        }
        if (space === "Space_P" || space === "Space_S" || space === "Space_L") {
          return paragraphProgressOverrideFromRecord(record);
        }
        if (space === "Space_W" && typeof spaceWProgressOverrideFromRecord === "function") {
          return spaceWProgressOverrideFromRecord(record);
        }
        return null;
      };

      const hydrateLessonTaskProgress = (task = {}, paths = [], owner = "", taskStudy = {}) => {
        const learningPath = taskLearningPath(task) || task.path;
        const entry = taskLearningEntry({ ...task, path: learningPath || task.path });
        const space = serverLessonProgressSpaceForPath(learningPath || task.path, task.extension);
        if (!entry.path || (space !== "Space_V" && space !== "Space_W" && space !== "Space_Q" && space !== "Space_P" && space !== "Space_S" && space !== "Space_L")) {
          return;
        }
        const lessonId = clean(task.lesson_id || task.lessonId || task.file_id || task.fileId || "");
        const hydratePaths = [
          learningPath,
          task.path,
          task.effective_path,
          task.link_target,
          ...(Array.isArray(paths) ? paths : []),
        ];
        const key = lessonTaskProgressHydrationKey(hydratePaths, owner, lessonId);
        if (!key) {
          return;
        }
        const existingProgress = taskStudy && taskStudy.progress && typeof taskStudy.progress === "object" ? taskStudy.progress : {};
        const existingTotal = Math.max(
          0,
          Number(existingProgress.total ?? existingProgress.nodeTotal ?? existingProgress.node_total ?? taskStudy.total_nodes ?? taskStudy.nodes ?? task.node_count ?? task.nodes ?? 0) || 0,
        );
        if (existingTotal > 0 || clean(taskStudy.progress_text || existingProgress.text || "")) {
          lessonTaskProgressHydrationFreshUntil.set(key, Date.now() + 15000);
          lessonTaskRuntimeMetrics.hydrationSkips += 1;
          return;
        }
        if (lessonTaskProgressHydrationInflight.has(key) || Date.now() < Number(lessonTaskProgressHydrationFreshUntil.get(key) || 0)) {
          lessonTaskRuntimeMetrics.hydrationSkips += 1;
          return;
        }
        lessonTaskProgressHydrationInflight.add(key);
        const fetchCandidates = Array.from(new Set([
          entry.path,
          learningPath,
          task.path,
          task.effective_path,
          task.link_target,
        ].map((path) => normalizeServerPathValue(path)).filter(Boolean)));
        const readNextProgress = (index = 0) => {
          const candidatePath = fetchCandidates[index] || entry.path;
          console.info("[SPACE_V_PROGRESS_DEBUG] hydrateLessonTaskProgress fetch", {
            owner,
            space,
            candidatePath,
            index,
            fetchCandidates,
          });
          return fetchServerProgressForEntry({ ...entry, path: candidatePath })
            .then((result) => {
              const resultSpace = clean(result && result.space) || space;
              const override = progressOverrideFromHydration(resultSpace, result && result.payload);
              console.info("[SPACE_V_PROGRESS_DEBUG] hydrateLessonTaskProgress result", {
                owner,
                requestedPath: candidatePath,
                resultSpace,
                hasOverride: Boolean(override),
                override,
                payloadProgress: result && result.payload && result.payload.progress ? {
                  path: result.payload.progress.path,
                  nodeIndex: result.payload.progress.nodeIndex,
                  nodeCount: result.payload.progress.nodeCount,
                  updatedAt: result.payload.progress.updatedAt,
                  learned: result.payload.progress.state && Array.isArray(result.payload.progress.state.learned)
                    ? result.payload.progress.state.learned.length
                    : 0,
                } : null,
              });
              if (override || index >= fetchCandidates.length - 1) {
                return { resultSpace, override };
              }
              return readNextProgress(index + 1);
            });
        };
        void readNextProgress()
          .then((result) => {
            const override = result && result.override;
            if (!override) {
              return;
            }
            const signature = progressHydrationSignature(override);
            lessonTaskProgressHydrationFreshUntil.set(key, Date.now() + 15000);
            if (!signature || lessonTaskProgressHydrationSignatures.get(key) === signature) {
              return;
            }
            lessonTaskProgressHydrationSignatures.set(key, signature);
            setLessonProgressOverride(hydratePaths, override, 45000);
            patchVisibleLessonTaskProgress(task, taskStudy, override);
          })
          .catch(() => {})
          .finally(() => lessonTaskProgressHydrationInflight.delete(key));
      };

      // Added 2026-07-06: hydrates visible Lesson Vault file chips from server progress after login/list render.
      const hydrateVisibleLessonVaultFileProgress = (entry = {}, rowNode = null, owner = "") => {
        if (!entry || entry.type !== "file" || !rowNode || !rowNode.isConnected) {
          return;
        }
        if (Date.now() < Number(window.__ftLessonVaultProgressHydrationPausedUntil || 0)) {
          return;
        }
        const filePath = normalizeServerPathValue(entry.path || "");
        const space = serverLessonProgressSpaceForPath(filePath, entry.extension);
        if (!filePath || !["Space_V", "Space_W", "Space_Q", "Space_P", "Space_S", "Space_L"].includes(space)) {
          return;
        }
        const hydratePaths = [
          entry.path,
          entry.effective_path,
          entry.link_target,
          entry.linked_path,
          entry.sourcePath,
          entry.source_path,
          entry.original_path,
          serverLearningPathForEntry(entry),
        ].map((path) => normalizeServerPathValue(path)).filter(Boolean);
        const canonicalLessonId = clean(entry.lesson_id || entry.lessonId || entry.file_id || entry.fileId || "");
        const key = lessonTaskProgressHydrationKey(hydratePaths, owner || currentAuthUsername || "", canonicalLessonId);
        if (!key) {
          return;
        }
        const localProgressSource = entry.study && typeof entry.study === "object"
          ? entry.study
          : (entry.progress && typeof entry.progress === "object" ? entry.progress : null);
        const localOverride = progressOverrideFromHydration(space, localProgressSource || {});
        if (localOverride && !canonicalLessonId) {
          const localSignature = progressHydrationSignature(localOverride);
          if (localSignature && lessonVaultFileProgressHydrationSignatures.get(key) !== localSignature) {
            lessonVaultFileProgressHydrationSignatures.set(key, localSignature);
            setLessonProgressOverride(hydratePaths, localOverride, 120000);
          }
          return;
        }
        if (localProgressSource && !canonicalLessonId) {
            return;
        }
        // Updated 2026-07-21: tree/login preload is authoritative for all lesson progress spaces.
        if (!canonicalLessonId && ["Space_W", "Space_Q", "Space_P", "Space_S", "Space_L"].includes(space)) {
            return;
        }
        const fetchEntry = {
          ...entry,
          lesson_id: canonicalLessonId,
          file_id: canonicalLessonId,
          path: serverLearningPathForEntry(entry) || entry.effective_path || entry.link_target || entry.path,
        };
        window.setTimeout(() => {
          fetchServerProgressForEntry(fetchEntry)
            .then((result) => {
              const resultSpace = clean(result && result.space) || space;
              const override = progressOverrideFromHydration(resultSpace, result && result.payload);
              if (!override) {
                return;
              }
              const signature = progressHydrationSignature(override);
              if (!signature || lessonVaultFileProgressHydrationSignatures.get(key) === signature) {
                return;
              }
              lessonVaultFileProgressHydrationSignatures.set(key, signature);
              setLessonProgressOverride(hydratePaths, override, 120000);
              if (typeof refreshLessonVaultItemStudyFromServer === "function") {
                void refreshLessonVaultItemStudyFromServer(hydratePaths, owner || currentAuthUsername || "", { render: true }).catch(() => {});
                return;
              }
              if (typeof renderServerDataList === "function") {
                const cachedRow = getCachedServerBrowserListRow(serverBrowserPath || "", owner || serverTaskOwnerContext || "");
                if (cachedRow && cachedRow.payload) {
                  renderServerDataList(cachedRow.payload);
                }
              }
            })
            .catch(() => {});
        }, 80 + Math.min(900, Math.max(0, Number(rowNode.dataset.vaultIndex || 0) || 0) * 35));
      };

      const renderLessonTaskPanel = (payload = {}) => {
        if (!serverTaskListNode) {
          return;
        }
        const timelineStartedAt = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
        if (typeof window !== "undefined") {
          const metrics = window.__ftLoginTimelineMetrics = window.__ftLoginTimelineMetrics || { counts: {}, totalMs: {}, maxMs: {} };
          if (typeof window.__ftRecordLoginTimelinePhase !== "function") {
            window.__ftRecordLoginTimelinePhase = (phase = "", ms = 0) => {
              const key = String(phase || "").trim();
              if (!key) return;
              const duration = Math.max(0, Number(ms) || 0);
              metrics.counts[key] = Number(metrics.counts[key] || 0) + 1;
              metrics.totalMs[key] = Number((Number(metrics.totalMs[key] || 0) + duration).toFixed(3));
              metrics.maxMs[key] = Math.max(Number(metrics.maxMs[key] || 0), duration);
            };
          }
        }
        settleLessonTaskPanelMotion();
        // 2026-07-24: expose counters after the live task panel has mounted.
        if (typeof window !== "undefined") {
          window.__ftSpaceTaskMetricsSnapshot = () => ({ ...lessonTaskRuntimeMetrics });
        }
        if (typeof applyLessonVaultProgressSnapshotToPayload === "function") {
          payload = applyLessonVaultProgressSnapshotToPayload(payload);
        }
        if (taskHoverPreviewCard && !isTaskHoverPreviewCardLive(taskHoverPreviewCard)) {
          hideTaskHoverPreview(taskHoverPreviewCard);
        }
        let owner = clean(payload.task_owner || "");
        let manualTasks = Array.isArray(payload.tasks) ? payload.tasks : [];
        let spaceTask = payload.space_task && typeof payload.space_task === "object" ? payload.space_task : null;
        let spaceTaskPending = Boolean(spaceTask && spaceTask.pending);
        let spaceTasks = lessonTaskSpaceRows(payload);
        let displayUsesSpace = lessonTaskDisplayUsesSpace(payload);
        let tasks = displayUsesSpace ? lessonTaskMergedSpaceRows(payload) : manualTasks;
        // Added 2026-07-15: Back/local-cache deferred payloads must not wipe an already populated Space Task panel.
        const currentOwner = clean(currentTaskPayload && currentTaskPayload.task_owner || "");
        const currentRows = currentTaskPayload ? lessonTaskDisplayRows(currentTaskPayload) : [];
        const fallbackOwner = owner || clean(serverTaskOwnerContext || currentAuthUsername);
        const cachedTaskRow = fallbackOwner && typeof getLessonTaskPanelCacheRow === "function" ? getLessonTaskPanelCacheRow(fallbackOwner) : null;
        const cachedTaskPayload = cachedTaskRow && cachedTaskRow.payload && typeof cachedTaskRow.payload === "object" ? cachedTaskRow.payload : null;
        const cachedRows = cachedTaskPayload ? lessonTaskDisplayRows(cachedTaskPayload) : [];
        const currentMatchesOwner = Boolean(currentRows.length && fallbackOwner && authUsernameMatches(fallbackOwner, currentOwner));
        const cachedMatchesOwner = Boolean(cachedRows.length && fallbackOwner && authUsernameMatches(fallbackOwner, clean(cachedTaskPayload.task_owner || fallbackOwner)));
        const reusableTaskPayload = currentMatchesOwner ? currentTaskPayload : (cachedMatchesOwner ? cachedTaskPayload : null);
        // Added 2026-07-24: never resurrect a stale Space Task selection while the
        // server is rebuilding after folder/progress changes. The old payload can
        // point at a lesson that is already learned; wait for the canonical build.
        const spaceTaskAwaitingRefresh = Boolean(
          displayUsesSpace
          && spaceTask
          && (spaceTask.pending || spaceTask.deferred || spaceTask.local_cache_only || payload.task_board_deferred)
        );
        if (!tasks.length && reusableTaskPayload && !spaceTaskAwaitingRefresh) {
          const reusableSpaceTask = reusableTaskPayload.space_task && typeof reusableTaskPayload.space_task === "object" ? reusableTaskPayload.space_task : {};
          payload = {
            ...reusableTaskPayload,
            ...payload,
            task_owner: fallbackOwner,
            tasks: Array.isArray(reusableTaskPayload.tasks) ? reusableTaskPayload.tasks : [],
            space_tasks: Array.isArray(reusableTaskPayload.space_tasks) ? reusableTaskPayload.space_tasks : [],
            space_task: {
              ...reusableSpaceTask,
              ...(spaceTask || {}),
              deferred: Boolean(reusableSpaceTask.deferred || (spaceTask && spaceTask.deferred) || payload.task_board_deferred || payload.local_cache_only),
            },
            learning_stats: payload.learning_stats || reusableTaskPayload.learning_stats || null,
            task_notices: Array.isArray(payload.task_notices) && payload.task_notices.length
              ? payload.task_notices
              : (Array.isArray(reusableTaskPayload.task_notices) ? reusableTaskPayload.task_notices : []),
          };
          owner = clean(payload.task_owner || "");
          manualTasks = Array.isArray(payload.tasks) ? payload.tasks : [];
          spaceTask = payload.space_task && typeof payload.space_task === "object" ? payload.space_task : null;
          spaceTaskPending = Boolean(spaceTask && spaceTask.pending);
          spaceTasks = lessonTaskSpaceRows(payload);
          displayUsesSpace = lessonTaskDisplayUsesSpace(payload);
          tasks = displayUsesSpace ? lessonTaskMergedSpaceRows(payload) : manualTasks;
        }
        if (typeof window !== "undefined" && typeof window.__ftRecordLoginTimelinePhase === "function") {
          const timelineEndedAt = typeof performance !== "undefined" && typeof performance.now === "function" ? performance.now() : Date.now();
          window.__ftRecordLoginTimelinePhase("renderLessonTaskPanel", timelineEndedAt - timelineStartedAt);
        }
        const renderOwnerKey = [owner, displayUsesSpace ? "space" : "task", payload.admin ? "admin" : "user"].join("|");
        const nextRenderSignature = lessonTaskPanelRenderSignature(payload, tasks);
        // Added 2026-07-27: login preview cards must not become the authoritative task payload for the real auth flow.
        const existingCurrentSpaceTask = currentTaskPayload && currentTaskPayload.space_task && typeof currentTaskPayload.space_task === "object"
          ? currentTaskPayload.space_task
          : null;
        const payloadSpaceTask = payload.space_task && typeof payload.space_task === "object"
          ? payload.space_task
          : null;
        const payloadSpaceTaskOwner = clean(payload.task_owner || "");
        const canPreservePreferredFolders = Boolean(
          existingCurrentSpaceTask
          && payloadSpaceTaskOwner
          && authUsernameMatches(payloadSpaceTaskOwner, clean(currentTaskPayload && currentTaskPayload.task_owner || ""))
        );
        const mergedSpaceTask = payload && payload.login_preview
          ? null
          : (payloadSpaceTask
            ? {
              ...(canPreservePreferredFolders && Array.isArray(existingCurrentSpaceTask.preferred_folders) ? existingCurrentSpaceTask : {}),
              ...payloadSpaceTask,
              preferred_folders: Array.isArray(payloadSpaceTask.preferred_folders)
                ? [...payloadSpaceTask.preferred_folders]
                : (canPreservePreferredFolders && Array.isArray(existingCurrentSpaceTask.preferred_folders)
                  ? [...existingCurrentSpaceTask.preferred_folders]
                  : []),
            }
            : (canPreservePreferredFolders ? {
              ...existingCurrentSpaceTask,
              preferred_folders: Array.isArray(existingCurrentSpaceTask.preferred_folders)
                ? [...existingCurrentSpaceTask.preferred_folders]
                : [],
            } : null));
        currentTaskPayload = payload && payload.login_preview
          ? {
            task_owner: owner,
            tasks: [],
            space_tasks: [],
            space_task: null,
            admin: Boolean(payload.admin),
            learning_stats: null,
            task_notices: [],
          }
          : {
            task_owner: owner,
            tasks: Array.isArray(payload.tasks) ? payload.tasks : [],
            space_tasks: lessonTaskSpaceRows(payload),
            space_task: mergedSpaceTask,
            admin: Boolean(payload.admin),
            learning_stats: payload.learning_stats || null,
            task_notices: Array.isArray(payload.task_notices) ? payload.task_notices : [],
          };
        syncVisibleServerTaskRows(currentTaskPayload);
        rememberLatestTaskNoticeForReplay(latestTaskNoticeFromList(currentTaskPayload.task_notices));
        renderLearningSummary(taskLearningSummaryNode, payload.learning_stats || {});
        if (owner) {
          serverTaskOwnerContext = owner;
        }
        renderTaskNoticeAdmin({ ...payload, task_owner: owner, admin: Boolean(payload.admin) });
        if (!payload.admin) {
          queueTaskUserNotices(payload.task_notices || [], { pendingTasks: taskPayloadHasPendingLessons(payload) });
          queueTaskNoticeReturnReminder(currentTaskPayload);
        }
        const completed = tasks.filter((task) => task && task.completed).length;
        const critical = tasks.filter((task) => task && clean(task.severity).toLowerCase() === "critical" && !task.completed).length;
        if (serverTaskOwnerNode) {
          serverTaskOwnerNode.textContent = owner
            ? `${displayUsesSpace ? "Space Task" : "Learner channel"}: ${owner}`
            : (displayUsesSpace ? "Space Task channel" : "Learner task channel");
        }
        if (taskTitleNode) {
          taskTitleNode.textContent = displayUsesSpace ? "Space Task" : "Task board";
        }
        if (taskSummaryNode) {
          taskSummaryNode.hidden = displayUsesSpace;
        }
        if (taskModeSwitchButton) {
          taskModeSwitchButton.hidden = true;
          taskModeSwitchButton.disabled = true;
        }
        if (taskSpaceFoldersButton) {
          updateTaskNoticeReplayButtonState(currentTaskPayload, displayUsesSpace);
        }
        if (taskTotalNode) taskTotalNode.textContent = String(tasks.length);
        if (taskCriticalNode) taskCriticalNode.textContent = String(critical);
        if (taskCompleteNode) taskCompleteNode.textContent = String(completed);
        if (taskEffectTestPendingButton) {
          taskEffectTestPendingButton.hidden = true;
          taskEffectTestPendingButton.disabled = true;
        }
        if (taskEffectTestOverdueButton) {
          taskEffectTestOverdueButton.hidden = true;
          taskEffectTestOverdueButton.disabled = true;
        }
        if (taskStatsRefreshButton) {
          taskStatsRefreshButton.hidden = !owner || displayUsesSpace;
          taskStatsRefreshButton.disabled = !owner || displayUsesSpace;
        }
        if (spaceTaskPending && owner) {
          schedulePendingLessonTaskRefresh(owner);
        }
        const shouldReuseList = Boolean(
          serverTaskListNode.childElementCount
          && lessonTaskPanelLastOwnerKey === renderOwnerKey
          && lessonTaskPanelLastSignature === nextRenderSignature
        );
        if (shouldReuseList) {
          requestTaskHoverPreviewValidation();
          refreshTaskAssignedChips();
          scheduleLessonTaskPanelAutoRefresh();
          return;
        }
        hideTaskHoverPreview();
        lessonTaskRuntimeMetrics.fullRenders += 1;
        serverTaskListNode.textContent = "";
        lessonTaskPanelLastOwnerKey = renderOwnerKey;
        lessonTaskPanelLastSignature = nextRenderSignature;
        if (!tasks.length) {
          stopTaskAssignedChipTimer();
          scheduleLessonTaskPanelAutoRefresh();
          const empty = document.createElement("div");
          empty.className = "ft-task-empty";
          empty.textContent = spaceTaskPending
            ? "Preparing Space Task from folders in background..."
            : (displayUsesSpace
              ? (payload.admin
                ? "No Space Task file is waiting. Set priority folders or add lesson files to this learner folder."
                : "No Space Task file is waiting yet. Finish the current queue or wait for new files in your folder.")
              : "Open a learner folder in Lesson Vault, add lesson files as tasks, then manage severity here.");
          serverTaskListNode.appendChild(empty);
          return;
        }
        tasks.forEach((task, index) => {
          const taskProgressPaths = [
            task.path,
            task.effective_path,
            task.link_target,
            taskLearningPath(task),
          ];
          const taskProgressView = splitLessonProgressForViewer(task.study || {}, taskProgressPaths, owner);
          const taskStudy = taskProgressView.study || {};
          const taskAdminProgress = taskProgressView.adminProgress || null;
          const taskAdminPriorCompletion = payload.admin ? adminProgressHasPriorCompletion(task.study || {}, taskAdminProgress) : false;
          const taskEntry = taskLearningEntry(task);
          const taskPath = normalizeServerPathValue(task.path || "");
          const taskExtension = clean(taskEntry.extension || task.extension || "").toLowerCase();
          const taskIsPdf = Boolean(taskEntry.is_pdf || task.is_pdf || taskExtension === ".pdf" || taskPath.toLowerCase().endsWith(".space_pdf"));
          const taskLessonId = clean(taskEntry.lesson_id || taskEntry.file_id || task.lesson_id || task.file_id || "");
          const taskFileId = clean(taskEntry.file_id || taskEntry.lesson_id || task.file_id || task.lesson_id || "");
          const taskFolderGroup = lessonTaskFolderGroupFromTask({ ...task, ...taskEntry, path: taskPath });
          const taskFolderColor = lessonTaskFolderColor(taskFolderGroup.key);
          const severity = clean(task.severity || "normal").toLowerCase() || "normal";
          const overdue = isTaskOverdue(task);
          const card = document.createElement("button");
          card.type = "button";
          card.className = "ft-task-card";
          card.dataset.taskId = clean(task.id || "");
          card.dataset.lessonId = taskLessonId;
          card.dataset.fileId = taskFileId;
          card.dataset.path = taskPath;
          card.dataset.normalizedPath = normalizeServerPathValue(task.normalized_path || task.path || "");
          card.dataset.effectivePath = taskLearningPath(task) || normalizeServerPathValue(task.path || "");
          card.dataset.linkTarget = normalizeServerPathValue(task.link_target || "");
          card.dataset.filename = clean(task.filename || task.name || "");
          card.dataset.extension = taskExtension;
          card.dataset.mimeType = clean(task.mime_type || (taskIsPdf ? "application/pdf" : ""));
          card.dataset.fileType = clean(task.file_type || (taskIsPdf ? "pdf" : "lesson"));
          card.dataset.sourceType = clean(task.source_type || (task.package_backed ? "package" : "lesson"));
          card.dataset.isPdf = taskIsPdf ? "1" : "0";
          card.dataset.icon = clean(task.icon || (taskIsPdf ? "pdf" : "file"));
          card.dataset.openAction = clean(task.open_action || (taskIsPdf ? "space_pdf" : "lesson"));
          card.dataset.folderId = taskFolderGroup.folderId;
          card.dataset.folderPath = taskFolderGroup.folderPath;
          card.dataset.folderName = taskFolderGroup.folderName;
          card.dataset.folderChain = taskFolderGroup.folderChain;
          card.dataset.folderGroupKey = taskFolderGroup.key;
          card.dataset.folderBacked = taskFolderGroup.folderBacked ? "1" : "0";
          card.dataset.assignmentSource = task.space_task ? "system" : "admin";
          card.dataset.assignedAt = taskAssignedAt(task);
          card.dataset.completed = task.completed ? "1" : "0";
          card.style.setProperty("--task-delay", `${(index % 7) * 170}ms`);
          if (taskFolderColor) {
            card.style.setProperty("--task-remove-hue", String(taskFolderColor.hue));
            card.style.setProperty("--task-remove-saturation", `${taskFolderColor.saturation}%`);
            card.style.setProperty("--task-remove-lightness", `${taskFolderColor.lightness}%`);
          }
          card.classList.toggle("is-complete", Boolean(task.completed));
          card.classList.toggle("is-high", severity === "high");
          card.classList.toggle("is-critical", severity === "critical");
          card.classList.toggle("is-overdue", overdue);
          card.classList.toggle("is-pending", !task.completed && !overdue);
          const taskSelectedPaths = [
            task.path,
            task.effective_path,
            task.link_target,
          ].map((value) => normalizeTaskPath(value)).filter(Boolean);
          card.classList.toggle("is-selected", Boolean(serverBrowserFocusedFilePath && taskSelectedPaths.includes(normalizeTaskPath(serverBrowserFocusedFilePath))));
          const taskHoverPath = taskLearningPath(task) || task.path;
          const typeLogo = createFutureFileTypeLogo(taskHoverPath, taskExtension, task.space || "", "ft-task-type-logo");
          typeLogo.removeAttribute("title");
          const main = document.createElement("span");
          main.className = "ft-task-main";
          const name = document.createElement("span");
          name.className = "ft-task-card-name";
          const taskDisplayName = typeof futureFriendlyDisplayName === "function" ? futureFriendlyDisplayName(task.title || task.name || task.path || "Lesson task") : clean(task.title || task.name || task.path || "Lesson task");
          name.textContent = taskDisplayName;
          card.dataset.hoverTitle = taskDisplayName;
          card.dataset.hoverSpace = clean(task.space || "");
          const meta = document.createElement("span");
          meta.className = "ft-task-meta";
          if (task.space_task) {
            meta.appendChild(createServerChip("Auto", "filetype"));
          } else {
            meta.appendChild(createServerChip(taskSeverityLabel(severity), severity === "critical" ? "total" : (severity === "high" ? "date" : "filetype")));
          }
          if (task.completed || (overdue && !task.space_task)) {
            meta.appendChild(createServerChip(task.completed ? "Completed" : "Over 24h", task.completed ? "learned" : "total"));
          }
          if (task.available === false) {
            meta.appendChild(createServerChip("File moved", "total"));
          }
          if (Number(task.user_count || 0) > 0) {
            meta.appendChild(createServerChip(formatLessonTimes(task.user_count), "learned"));
          }
          if (taskAdminPriorCompletion) {
            const count = adminViewerCompletionCount(task.study || {});
            meta.appendChild(createServerChip(count ? `Admin ${formatLessonTimes(count)}` : "Admin Learned", "admin learned"));
          }
          appendLessonTimeChip(meta, taskStudy);
          const taskProgressInfo = taskStudy.progress && typeof taskStudy.progress === "object" ? taskStudy.progress : {};
          card.dataset.progressText = clean(taskStudy.progress_text || taskProgressInfo.text || "");
          card.dataset.progressPercent = String(Math.max(0, Math.min(100, Number(taskStudy.progress_percent ?? taskProgressInfo.percent ?? 0) || 0)));
          const assignedChip = createTaskAssignedChip(task);
          if (assignedChip) {
            meta.appendChild(assignedChip);
          }
          main.append(name, meta);
          const controls = document.createElement("span");
          controls.className = "ft-task-controls";
          const energy = document.createElement("span");
          energy.className = "ft-task-energy";
          energy.setAttribute("aria-hidden", "true");
          const sparks = document.createElement("span");
          sparks.className = "ft-task-sparks";
          sparks.setAttribute("aria-hidden", "true");
          const mirrorSweep = document.createElement("span");
          mirrorSweep.className = "ft-click-mirror-sweep";
          mirrorSweep.setAttribute("aria-hidden", "true");
          const progressNode = createLessonProgressNode(taskStudy, "ft-task-progress", {
            emptyProgress: true,
            emptyLabel: "Not started",
            emptyTotal: taskStudy.total_nodes || task.total_nodes || taskStudy.questions || task.questions || taskStudy.nodes || task.nodes || task.node_count || 1,
          });
          const adminProgressNode = taskAdminProgress
            ? createLessonProgressNode(task.study || {}, "ft-task-progress ft-task-progress-admin", {
              progress: taskAdminProgress,
              variantClass: "is-admin-progress",
              ownerBadge: "AD",
              ownerLabel: "Admin progress",
              labelText: "Admin in progress",
              title: `Admin progress: ${clean(taskAdminProgress.text || "")} - ${Number(taskAdminProgress.percent || 0)}%`,
            })
            : null;
          const progressStack = progressNode || adminProgressNode ? document.createElement("span") : null;
          if (progressStack) {
            progressStack.className = "ft-task-progress-stack";
            if (progressNode) {
              progressStack.appendChild(progressNode);
            }
            if (adminProgressNode) {
              progressStack.appendChild(adminProgressNode);
            }
          }
          const quickActions = document.createElement("span");
          quickActions.className = "ft-task-quick-actions";
          card.classList.toggle("has-progress", Boolean(progressNode || adminProgressNode));
          card.classList.toggle("has-admin-progress", Boolean(adminProgressNode));
          if (payload.admin && owner && !task.space_task) {
            ["normal", "high", "critical"].forEach((level) => {
              const button = document.createElement("button");
              button.type = "button";
              button.className = "ft-task-severity-button";
              button.classList.toggle("is-active", severity === level);
              button.textContent = level === "critical" ? "Critical" : (level === "high" ? "High" : "Normal");
              button.addEventListener("click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                hideTaskHoverPreview(card);
                void updateLessonTaskSeverity(owner, task, level);
              });
              controls.appendChild(button);
            });
          }
          const canRemoveFromTaskBoard = Boolean(owner && (payload.admin || task.can_remove || authUsernameMatches(owner, currentAuthUsername)));
          if (canRemoveFromTaskBoard) {
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "ft-task-remove";
            remove.classList.toggle("is-folder-group", taskFolderGroup.folderBacked);
            remove.dataset.folderGroupKey = taskFolderGroup.key;
            remove.title = taskFolderGroup.folderBacked
              ? `Remove folder group: ${taskFolderGroup.folderPath}`
              : "Remove this task";
            remove.textContent = payload.admin ? "Remove" : "Remove task";
            remove.addEventListener("click", (event) => {
              event.preventDefault();
              event.stopPropagation();
              hideTaskHoverPreview(card);
              void removeLessonTask(owner, task);
            });
            controls.appendChild(remove);
          }
          const openTaskLesson = () => {
            const learningPath = taskLearningPath(task) || taskPath;
            if (taskPath) {
              setSelectedTaskPath(learningPath || taskPath);
            }
            loadServerLessonFile({
              type: "file",
              path: learningPath || task.path,
              effective_path: taskEntry.effective_path || "",
              link_target: taskEntry.link_target || "",
              linked_path: taskPath && learningPath && normalizeTaskPath(taskPath) !== normalizeTaskPath(learningPath) ? taskPath : "",
              name: taskEntry.name || taskEntry.path || task.path,
              extension: clean(taskEntry.extension || task.extension || ""),
              lesson_id: clean(taskEntry.lesson_id || taskEntry.file_id || task.lesson_id || task.file_id || ""),
              file_id: clean(taskEntry.file_id || taskEntry.lesson_id || task.file_id || task.lesson_id || ""),
              document_id: clean(taskEntry.document_id || task.document_id || ""),
              package_path: normalizeServerPathValue(taskEntry.package_path || task.package_path || ""),
              package_backed: Boolean(taskEntry.package_backed || task.package_backed),
              mime_type: clean(taskEntry.mime_type || task.mime_type || ""),
              file_type: clean(taskEntry.file_type || task.file_type || ""),
              source_type: clean(taskEntry.source_type || task.source_type || ""),
              is_pdf: taskIsPdf,
              open_action: clean(taskEntry.open_action || task.open_action || ""),
              study: task.study || null,
            });
          };
          const goButton = createLessonGoButton();
          goButton.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            hideTaskHoverPreview(card);
            triggerFutureFileLogoMotion(card, { source: "go" });
            openTaskLesson();
          });
          quickActions.appendChild(goButton);
          if ("PointerEvent" in window) {
            card.addEventListener("pointerenter", () => scheduleTaskHoverPreview(card));
            card.addEventListener("pointerleave", (event) => scheduleHideTaskHoverPreview(card, event));
          } else {
            card.addEventListener("mouseenter", () => scheduleTaskHoverPreview(card));
            card.addEventListener("mouseleave", (event) => scheduleHideTaskHoverPreview(card, event));
          }
          card.addEventListener("focus", () => scheduleTaskHoverPreview(card));
          card.addEventListener("blur", () => hideTaskHoverPreview(card));
          card.append(energy, sparks, mirrorSweep);
          if (progressStack) {
            card.appendChild(progressStack);
          }
          card.append(typeLogo, main, quickActions);
          if (controls.childElementCount) {
            card.appendChild(controls);
          }
          card.addEventListener("click", (event) => {
            event.preventDefault();
            hideTaskHoverPreview(card);
            const taskPath = normalizeServerPathValue(task.path || "");
            triggerServerWorkspaceMotionBurst(card, null, { source: "select" });
            setLoadStatus("Syncing Lesson Vault to the selected Space Task folder. Use Let's go to open the lesson.");
            void focusLessonVaultOnTask(task, owner);
          });
          serverTaskListNode.appendChild(card);
          hydrateLessonTaskProgress(task, taskProgressPaths, owner, taskStudy);
        });
        refreshTaskAssignedChips();
        scheduleLessonTaskPanelAutoRefresh();
        scheduleLearningStatsMotionCycle(1000);
      };

      const patchLessonTaskPanelProgress = (paths = [], progress = null) => {
        if (!progress || typeof progress !== "object" || typeof applyLessonVaultProgressSnapshotToPayload !== "function") {
          return false;
        }
        let changed = false;
        if (currentTaskPayload && typeof currentTaskPayload === "object") {
          currentTaskPayload = applyLessonVaultProgressSnapshotToPayload(currentTaskPayload);
          changed = true;
        }
        const cachedPayloads = [];
        lessonTaskPanelCache.forEach((row) => {
          if (!row || !row.payload || typeof row.payload !== "object") {
            return;
          }
          const nextPayload = applyLessonVaultProgressSnapshotToPayload(row.payload);
          row.payload = nextPayload;
          row.at = Date.now();
          cachedPayloads.push(nextPayload);
          changed = true;
        });
        cachedPayloads.forEach((payload) => {
          rememberLessonTaskPanelCache(clean(payload.task_owner || serverTaskOwnerContext || currentAuthUsername), payload);
        });
        if (changed && serverTaskListNode && serverTaskListNode.isConnected && currentTaskPayload) {
          lessonTaskPanelLastSignature = "";
          renderLessonTaskPanel(currentTaskPayload);
        }
        return changed;
      };

      if (typeof window !== "undefined") {
        window.__ftPatchLessonTaskPanelProgress = patchLessonTaskPanelProgress;
        window.__ftSpaceTaskMetricsSnapshot = () => ({ ...lessonTaskRuntimeMetrics });
      }

      const loadLessonTasks = async (owner = "", options = {}) => {
        const targetOwner = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        const fresh = Boolean(options && options.fresh);
        const localCacheOnly = Boolean(options && options.localCacheOnly);
        const cachedRow = getLessonTaskPanelCacheRow(targetOwner);
        if (cachedRow) {
          const cacheAge = Date.now() - Number(cachedRow.at || 0);
          if (localCacheOnly || (!fresh && cacheAge < LESSON_TASK_PANEL_REFRESH_MIN_MS)) {
            renderLessonTaskPanel(cachedRow.payload);
            const cachedSpaceTask = cachedRow.payload && cachedRow.payload.space_task && typeof cachedRow.payload.space_task === "object"
              ? cachedRow.payload.space_task
              : {};
            if (targetOwner && Array.isArray(cachedSpaceTask.preferred_folders)) {
              rememberFreshFolderTaskPreferredFoldersForOwner(targetOwner, cachedSpaceTask.preferred_folders, cachedSpaceTask);
              syncVisibleFolderTaskChooseButtonsForOwner(targetOwner);
            }
            return cachedRow.payload;
          }
        }
        if (localCacheOnly) {
          const localPayload = currentTaskPayload && typeof currentTaskPayload === "object"
            ? currentTaskPayload
            : { ok: true, task_owner: targetOwner, tasks: [], space_tasks: [], space_task: { enabled: Boolean(targetOwner), tasks: [], local_cache_only: true } };
          renderLessonTaskPanel(localPayload);
          return localPayload;
        }
        const inflightKey = lessonTaskPanelCacheKey(targetOwner);
        if (lessonTaskPanelInflight.has(inflightKey)) {
          return await lessonTaskPanelInflight.get(inflightKey);
        }
        const query = targetOwner ? `?user=${encodeURIComponent(targetOwner)}` : "";
        const cachedPayload = cachedRow && cachedRow.payload && typeof cachedRow.payload === "object" ? cachedRow.payload : null;
        const request = (async () => {
          const result = await fetchServerJson(`/lesson-tasks${query}`, {
            ifNoneMatch: cachedPayload ? clean(cachedRow && cachedRow.etag || "") : "",
            notModifiedPayload: cachedPayload,
          });
          rememberLessonTaskPanelCache(targetOwner, result.payload, result.etag);
          renderLessonTaskPanel(result.payload);
          const spaceTask = result.payload && result.payload.space_task && typeof result.payload.space_task === "object"
            ? result.payload.space_task
            : {};
          if (targetOwner && Array.isArray(spaceTask.preferred_folders)) {
            rememberFreshFolderTaskPreferredFoldersForOwner(targetOwner, spaceTask.preferred_folders, spaceTask);
            syncVisibleFolderTaskChooseButtonsForOwner(targetOwner);
          }
          if (spaceTask.pending) {
            schedulePendingLessonTaskRefresh(targetOwner);
          } else {
            lessonTaskPanelPendingRefreshTries = 0;
          }
          return result.payload;
        })();
        lessonTaskPanelInflight.set(inflightKey, request);
        try {
          return await request;
        } finally {
          if (lessonTaskPanelInflight.get(inflightKey) === request) {
            lessonTaskPanelInflight.delete(inflightKey);
          }
        }
      };

      const refreshCurrentServerTaskPanel = async () => {
        if (taskModal && !taskModal.hidden) {
          await loadLessonTasks(serverTaskOwnerContext, { fresh: true });
        }
        if (serverBrowser && !serverBrowser.hidden) {
          await loadServerDataPath(serverBrowserPath, true);
        }
      };

      const openLessonTaskBoard = async (owner = "") => {
        if (taskModal) {
          taskModal.hidden = false;
        }
        try {
          await loadLessonTasks(owner, { fresh: true });
        } catch (error) {
          renderLessonTaskPanel({ task_owner: clean(owner || serverTaskOwnerContext || currentAuthUsername), tasks: [], admin: currentAuthIsAdmin });
          setLoadStatus(error && error.message ? error.message : "Could not load lesson tasks.", true);
        }
      };

      const closeLessonTaskBoard = () => {
        if (taskModal) {
          taskModal.hidden = true;
        }
      };

      const refreshLearningStats = async (owner = "") => {
        const targetUser = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        if (!targetUser) {
          return;
        }
        if (taskStatsRefreshButton) {
          taskStatsRefreshButton.disabled = true;
          taskStatsRefreshButton.textContent = "Refreshing";
        }
        try {
          try {
            const vocabParams = new URLSearchParams({
              force: "1",
              reason: "taskboard-refresh",
              user: targetUser,
            });
            await fetchServerJson(`/vocab/sync-main-offline?${vocabParams.toString()}`);
          } catch (syncError) {
            console.warn("[Future] Could not sync QMLearn offline vocabulary before refreshing stats.", syncError);
          }
          const result = await fetchServerJson("/lesson-stats/refresh", {
            method: "POST",
            body: JSON.stringify({ user: targetUser }),
            headers: { "Content-Type": "application/json" },
          });
          const stats = result.payload && result.payload.learning_stats ? result.payload.learning_stats : {};
          currentTaskPayload.learning_stats = stats;
          clearLessonTaskPanelCache();
          renderLearningSummary(taskLearningSummaryNode, stats);
          setLoadStatus("Learning stats refreshed.");
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "Could not refresh learning stats.", true);
        } finally {
          if (taskStatsRefreshButton) {
            taskStatsRefreshButton.disabled = false;
            taskStatsRefreshButton.textContent = "Refresh stats";
          }
        }
      };

      const editSpaceTaskFolders = async (owner = "") => {
        const targetUser = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        if (!targetUser || !canManageSpaceTaskFolders(targetUser)) {
          return;
        }
        if (getSpaceTaskFolderMutationState(targetUser)) {
          syncVisibleFolderTaskChooseButtonsForOwner(targetUser);
          return;
        }
        const currentFolders = folderTaskPreferredFoldersForOwner(targetUser);
        const text = window.prompt(
          "Space Task folders. Put one folder per line in priority order. Leave blank to remove all chosen folders and use the normal learner-folder order.",
          currentFolders.join("\n"),
        );
        if (text === null) {
          return;
        }
        if (taskSpaceFoldersButton) {
          taskSpaceFoldersButton.disabled = true;
          taskSpaceFoldersButton.textContent = "Saving";
        }
        try {
          const folders = text.split(/\r?\n|,|;/).map((item) => clean(item)).filter(Boolean);
          beginSpaceTaskFolderMutation(targetUser, {
            busy: "Saving...",
            selectedBefore: false,
            mode: "save",
            scope: "owner",
          });
          syncVisibleFolderTaskChooseButtonsForOwner(targetUser);
          const result = await fetchServerJson("/lesson-tasks", {
            method: "POST",
            body: JSON.stringify({
              action: "space-folders",
              user: targetUser,
              folders,
              baseRevision: clean(currentTaskPayload.space_task && currentTaskPayload.space_task.updated_rev || ""),
            }),
            headers: { "Content-Type": "application/json" },
          });
          const savedFolders = result.payload
            && result.payload.space_task
            && Array.isArray(result.payload.space_task.preferred_folders)
            ? result.payload.space_task.preferred_folders
            : folders;
          const mergedSpaceTask = {
            ...(currentTaskPayload.space_task && typeof currentTaskPayload.space_task === "object" ? currentTaskPayload.space_task : {}),
            ...(result.payload && result.payload.space_task && typeof result.payload.space_task === "object" ? result.payload.space_task : {}),
            preferred_folders: [...savedFolders],
          };
          clearServerBrowserListCache();
          rememberFreshFolderTaskPreferredFoldersForOwner(targetUser, savedFolders, mergedSpaceTask);
          if (typeof clearLoginVaultPreloadCacheForUser === "function") {
            clearLoginVaultPreloadCacheForUser(targetUser);
          }
          clearLessonTaskPanelCache();
          serverTaskOwnerContext = targetUser;
          renderLessonTaskPanel({
            ...currentTaskPayload,
            ...result.payload,
            space_task: mergedSpaceTask,
            task_owner: targetUser,
            admin: typeof result.payload.admin === "boolean" ? result.payload.admin : currentAuthIsAdmin,
          });
          setLoadStatus("Space Task priority folders saved.");
        } catch (error) {
          rememberFolderTaskPreferredFoldersForOwner(targetUser, currentFolders);
          setLoadStatus(error && error.message ? error.message : "Could not save Space Task folders.", true);
        } finally {
          if (spaceTaskFolderMutationResolved(targetUser)) {
            endSpaceTaskFolderMutation(targetUser);
          } else {
            finalizeSpaceTaskFolderMutation(targetUser);
          }
          syncVisibleFolderTaskChooseButtonsForOwner(targetUser);
          if (taskSpaceFoldersButton) {
            taskSpaceFoldersButton.disabled = false;
            taskSpaceFoldersButton.textContent = "Folder task";
          }
        }
      };

      const chooseSpaceTaskFolder = async (owner = "", entry = {}, triggerButton = null, options = {}) => {
        const targetUser = clean(owner || serverTaskOwnerContext || currentAuthUsername);
        const folderPath = normalizeServerPathValue(entry && entry.path);
        if (!targetUser || !folderPath || !canManageSpaceTaskFolders(targetUser)) {
          return;
        }
        if (getSpaceTaskFolderMutationState(targetUser)) {
          syncVisibleFolderTaskChooseButtonsForOwner(targetUser);
          return;
        }
        const currentFolders = folderTaskPreferredFoldersForOwner(targetUser);
        const folderKey = normalizeTaskPath(folderPath);
        const listedRegistered = currentFolders.some((item) => normalizeTaskPath(item) === folderKey);
        const isRegistered = listedRegistered;
        const nextFolders = isRegistered
          ? currentFolders.filter((item) => normalizeTaskPath(item) !== folderKey)
          : (listedRegistered ? [...currentFolders] : [...currentFolders, folderPath]);
        if (triggerButton && triggerButton.classList.contains("is-folder-task-selected") !== isRegistered) {
          setFolderTaskChooseButtonState(triggerButton, isRegistered);
        }
        if (!isRegistered && options.skipConfirm !== true) {
          const approved = await confirmSpaceTaskMutation({
            title: "Add Space Task Folder",
            body: `Use ${clean(entry.name || folderPath)} as an automatic Space Task folder for ${targetUser}?`,
            confirmLabel: "Add folder",
          });
          if (!approved) {
            return;
          }
        }
        let saved = false;
        const selectedAfter = !isRegistered;
        beginSpaceTaskFolderMutation(targetUser, {
          folderPath,
          busy: isRegistered ? "Removing..." : "Adding...",
          selectedBefore: isRegistered,
          mode: isRegistered ? "remove" : "add",
          scope: "folder",
        });
        if (triggerButton) {
          setFolderTaskChooseButtonState(triggerButton, isRegistered, {
            busy: isRegistered ? "Removing..." : "Adding...",
            disabled: true,
          });
        }
        syncVisibleFolderTaskChooseButtonsForOwner(targetUser);
        try {
          const postFolderSelection = async (folders) => fetchServerJson("/lesson-tasks", {
            method: "POST",
            body: JSON.stringify({
              action: "space-folders",
              user: targetUser,
              folders,
              baseRevision: clean(currentTaskPayload.space_task && currentTaskPayload.space_task.updated_rev || ""),
            }),
            headers: { "Content-Type": "application/json" },
          });
          let result;
          let finalFolders = nextFolders;
          try {
            result = await postFolderSelection(finalFolders);
          } catch (error) {
            const message = clean(error && error.message || "");
            if (!/Space Task folders changed on another device/i.test(message)) {
              throw error;
            }
            clearLessonTaskPanelCacheForOwner(targetUser);
            await loadLessonTasks(targetUser, { fresh: true });
            const latestFolders = folderTaskPreferredFoldersForOwner(targetUser);
            const latestRegistered = latestFolders.some((item) => normalizeTaskPath(item) === folderKey);
            finalFolders = latestRegistered
              ? latestFolders.filter((item) => normalizeTaskPath(item) !== folderKey)
              : [...latestFolders, folderPath];
            result = await postFolderSelection(finalFolders);
          }
          const serverFolders = result.payload
            && result.payload.space_task
            && Array.isArray(result.payload.space_task.preferred_folders)
            ? result.payload.space_task.preferred_folders
            : finalFolders;
          const mergedSpaceTask = {
            ...(currentTaskPayload.space_task && typeof currentTaskPayload.space_task === "object" ? currentTaskPayload.space_task : {}),
            ...(result.payload && result.payload.space_task && typeof result.payload.space_task === "object" ? result.payload.space_task : {}),
            preferred_folders: [...serverFolders],
          };
          clearServerBrowserListCache();
          rememberFreshFolderTaskPreferredFoldersForOwner(targetUser, serverFolders, mergedSpaceTask);
          if (typeof clearLoginVaultPreloadCacheForUser === "function") {
            clearLoginVaultPreloadCacheForUser(targetUser);
          }
          clearLessonTaskPanelCache();
          serverTaskOwnerContext = targetUser;
          renderLessonTaskPanel({
            ...currentTaskPayload,
            ...result.payload,
            space_task: mergedSpaceTask,
            task_owner: targetUser,
            admin: typeof result.payload.admin === "boolean" ? result.payload.admin : currentAuthIsAdmin,
          });
          rememberFreshFolderTaskPreferredFoldersForOwner(targetUser, serverFolders, mergedSpaceTask);
          saved = true;
          setLoadStatus(`Space Task folder ${isRegistered ? "removed" : "chosen"}: ${clean(entry.name || folderPath)}.`);
        } catch (error) {
          rememberFolderTaskPreferredFoldersForOwner(targetUser, currentFolders);
          setLoadStatus(error && error.message ? error.message : "Could not update Space Task folder.", true);
        } finally {
          endSpaceTaskFolderMutation(targetUser);
          if (saved) {
            const pendingSpaceTask = currentTaskPayload.space_task && typeof currentTaskPayload.space_task === "object"
              ? currentTaskPayload.space_task
              : {};
            if (pendingSpaceTask.pending) {
              schedulePendingLessonTaskRefresh(targetUser);
            }
          }
          syncVisibleFolderTaskChooseButtonsForOwner(targetUser);
        }
      };

      if (taskSpaceFoldersButton && !taskSpaceFoldersButton.dataset.spaceFolderEditBound) {
        taskSpaceFoldersButton.dataset.spaceFolderEditBound = "1";
        taskSpaceFoldersButton.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          void editSpaceTaskFolders(serverTaskOwnerContext || currentAuthUsername);
        });
      }

      const testLessonTaskEffects = (mode = "pending") => {
        if (!taskModal) {
          return;
        }
        taskModal.classList.remove("is-testing-pending", "is-testing-overdue");
        taskModal.classList.add(mode === "overdue" ? "is-testing-overdue" : "is-testing-pending");
        window.clearTimeout(taskModal._futureTaskFxTimer || 0);
        taskModal._futureTaskFxTimer = window.setTimeout(() => {
          taskModal.classList.remove("is-testing-pending", "is-testing-overdue");
        }, 4800);
      };

      let spaceTaskConfirmModal = null;
      let spaceTaskConfirmTitle = null;
      let spaceTaskConfirmBody = null;
      let spaceTaskConfirmApproveButton = null;
      let spaceTaskConfirmResolve = null;

      const closeSpaceTaskConfirmModal = (approved = false) => {
        if (!spaceTaskConfirmModal) {
          return;
        }
        spaceTaskConfirmModal.classList.remove("is-open");
        spaceTaskConfirmModal.setAttribute("aria-hidden", "true");
        const resolve = spaceTaskConfirmResolve;
        spaceTaskConfirmResolve = null;
        if (typeof resolve === "function") {
          resolve(Boolean(approved));
        }
      };

      const ensureSpaceTaskConfirmModal = () => {
        if (spaceTaskConfirmModal && document.body.contains(spaceTaskConfirmModal)) {
          return spaceTaskConfirmModal;
        }
        const modal = document.createElement("div");
        modal.className = "ft-task-confirm-modal";
        modal.setAttribute("role", "dialog");
        modal.setAttribute("aria-modal", "true");
        modal.setAttribute("aria-hidden", "true");
        modal.tabIndex = -1;
        const card = document.createElement("div");
        card.className = "ft-task-confirm-card";
        const title = document.createElement("h3");
        title.className = "ft-task-confirm-title";
        const body = document.createElement("p");
        body.className = "ft-task-confirm-body";
        const actions = document.createElement("div");
        actions.className = "ft-task-confirm-actions";
        const cancelButton = document.createElement("button");
        cancelButton.type = "button";
        cancelButton.className = "ft-task-confirm-button is-cancel";
        cancelButton.textContent = "Cancel";
        const approveButton = document.createElement("button");
        approveButton.type = "button";
        approveButton.className = "ft-task-confirm-button is-approve";
        approveButton.textContent = "Confirm";
        cancelButton.addEventListener("click", () => closeSpaceTaskConfirmModal(false));
        approveButton.addEventListener("click", () => closeSpaceTaskConfirmModal(true));
        modal.addEventListener("click", (event) => {
          if (event.target === modal) {
            closeSpaceTaskConfirmModal(false);
          }
        });
        modal.addEventListener("keydown", (event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            closeSpaceTaskConfirmModal(false);
          }
        });
        actions.appendChild(cancelButton);
        actions.appendChild(approveButton);
        card.appendChild(title);
        card.appendChild(body);
        card.appendChild(actions);
        modal.appendChild(card);
        document.body.appendChild(modal);
        spaceTaskConfirmModal = modal;
        spaceTaskConfirmTitle = title;
        spaceTaskConfirmBody = body;
        spaceTaskConfirmApproveButton = approveButton;
        return modal;
      };

      const confirmSpaceTaskMutation = async (options = {}) => {
        ensureSpaceTaskConfirmModal();
        if (!spaceTaskConfirmModal || !spaceTaskConfirmTitle || !spaceTaskConfirmBody || !spaceTaskConfirmApproveButton) {
          return true;
        }
        if (typeof spaceTaskConfirmResolve === "function") {
          try {
            spaceTaskConfirmResolve(false);
          } catch (error) {
          }
        }
        spaceTaskConfirmTitle.textContent = clean(options.title || "") || "Confirm";
        spaceTaskConfirmBody.textContent = clean(options.body || "") || "Please confirm this action.";
        spaceTaskConfirmApproveButton.textContent = clean(options.confirmLabel || "") || "Confirm";
        spaceTaskConfirmModal.classList.add("is-open");
        spaceTaskConfirmModal.setAttribute("aria-hidden", "false");
        window.setTimeout(() => {
          try {
            spaceTaskConfirmApproveButton.focus({ preventScroll: true });
          } catch (error) {
          }
        }, 30);
        return await new Promise((resolve) => {
          spaceTaskConfirmResolve = resolve;
        });
      };

      // Added 2026-07-23: Admin Common actions choose a target without mixing viewer and owner scope.
      let adminVaultTargetModal = null;
      let adminVaultTargetResolve = null;
      const closeAdminVaultTargetPicker = (value = "") => {
        if (adminVaultTargetModal) {
          adminVaultTargetModal.classList.remove("is-open");
          adminVaultTargetModal.setAttribute("aria-hidden", "true");
        }
        const resolve = adminVaultTargetResolve;
        adminVaultTargetResolve = null;
        if (typeof resolve === "function") resolve(value && typeof value === "object" ? value : clean(value));
      };
      // Added 2026-07-23: one target/destination picker for Common Add and Assign actions.
      const openAdminVaultTargetPicker = async (options = {}) => {
        if (!currentAuthIsAdmin) return "";
        if (typeof adminVaultTargetResolve === "function") closeAdminVaultTargetPicker("");
        if (!adminVaultTargetModal || !document.body.contains(adminVaultTargetModal)) {
          const modal = document.createElement("div");
          modal.className = "ft-admin-target-modal";
          modal.setAttribute("role", "dialog");
          modal.setAttribute("aria-modal", "true");
          modal.setAttribute("aria-hidden", "true");
          const card = document.createElement("div");
          card.className = "ft-admin-target-card";
          const header = document.createElement("div");
          header.className = "ft-admin-target-header";
          const heading = document.createElement("div");
          heading.className = "ft-admin-target-heading";
          const kicker = document.createElement("span");
          kicker.className = "ft-admin-target-kicker";
          kicker.textContent = "COMMON LIBRARY";
          const title = document.createElement("h3");
          title.className = "ft-admin-target-title";
          title.id = "ft-admin-target-title";
          heading.append(kicker, title);
          const closeButton = document.createElement("button");
          closeButton.type = "button";
          closeButton.className = "ft-admin-target-close";
          closeButton.setAttribute("aria-label", "Close target picker");
          closeButton.title = "Close";
          closeButton.innerHTML = "<span aria-hidden=\"true\">&times;</span>";
          header.append(heading, closeButton);
          const body = document.createElement("p");
          body.className = "ft-admin-target-body";
          const choices = document.createElement("div");
          choices.className = "ft-admin-target-choices";
          const selfButton = document.createElement("button");
          selfButton.type = "button";
          selfButton.className = "ft-admin-target-choice";
          selfButton.dataset.targetKind = "self";
          selfButton.textContent = "My account";
          const userButton = document.createElement("button");
          userButton.type = "button";
          userButton.className = "ft-admin-target-choice";
          userButton.dataset.targetKind = "user";
          userButton.textContent = "Another user";
          choices.append(selfButton, userButton);
          const search = document.createElement("input");
          search.type = "search";
          search.className = "ft-admin-target-search";
          search.placeholder = "Search user...";
          search.autocomplete = "off";
          const list = document.createElement("div");
          list.className = "ft-admin-target-list";
          const pager = document.createElement("div");
          pager.className = "ft-admin-target-pager";
          const summary = document.createElement("div");
          summary.className = "ft-admin-target-summary";
          summary.setAttribute("aria-live", "polite");
          summary.innerHTML = "<span class=\"ft-admin-target-summary-icon\" aria-hidden=\"true\"></span><div class=\"ft-admin-target-summary-content\"><small>SELECTED TARGET</small><strong></strong></div>";
          const destinationLabel = document.createElement("label");
          destinationLabel.className = "ft-admin-target-destination-label";
          destinationLabel.textContent = "Destination folder";
          const destination = document.createElement("select");
          destination.className = "ft-admin-target-destination";
          destinationLabel.appendChild(destination);
          const footer = document.createElement("div");
          footer.className = "ft-admin-target-footer";
          const cancel = document.createElement("button");
          cancel.type = "button";
          cancel.className = "ft-task-confirm-button is-cancel";
          cancel.textContent = "Cancel";
          const confirm = document.createElement("button");
          confirm.type = "button";
          confirm.className = "ft-task-confirm-button";
          confirm.textContent = "Continue";
          confirm.disabled = true;
          footer.append(cancel, confirm);
          cancel.addEventListener("click", () => closeAdminVaultTargetPicker(""));
          closeButton.addEventListener("click", () => closeAdminVaultTargetPicker(""));
          modal.addEventListener("click", (event) => {
            if (event.target === modal) closeAdminVaultTargetPicker("");
          });
          modal.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeAdminVaultTargetPicker("");
          });
          card.append(header, body, choices, search, list, pager, summary, destinationLabel, footer);
          modal.appendChild(card);
          document.body.appendChild(modal);
          adminVaultTargetModal = modal;
          modal.setAttribute("aria-labelledby", title.id);
          modal._futureAdminTarget = {
            title, body, selfButton, userButton, search, list, pager, summary,
            destination, destinationLabel, confirm, closeButton,
          };
        }
        const controls = adminVaultTargetModal._futureAdminTarget;
        const isAdd = clean(options.action || "").toLowerCase() === "add";
        controls.title.textContent = clean(options.title || "Choose target");
        controls.body.textContent = clean(options.body || "Choose who receives this action.");
        controls.destinationLabel.hidden = !isAdd;
        controls.destination.hidden = !isAdd;
        controls.search.value = "";
        controls.list.textContent = "";
        controls.pager.textContent = "";
        adminVaultTargetModal.classList.add("is-open");
        adminVaultTargetModal.setAttribute("aria-hidden", "false");
        let targetMode = "self";
        let selectedUser = clean(currentAuthUsername);
        let page = 1;
        let requestToken = 0;
        let folderToken = 0;
        const updateSummary = () => {
          const strong = controls.summary.querySelector("strong");
          if (strong) strong.textContent = selectedUser ? `@${selectedUser}` : "Choose a user";
          controls.summary.classList.toggle("is-ready", Boolean(selectedUser));
          controls.confirm.textContent = isAdd
            ? (selectedUser ? `Add to @${selectedUser}` : "Choose a user")
            : (selectedUser ? `Assign to @${selectedUser}` : "Choose a user");
          controls.confirm.disabled = !selectedUser;
        };
        const setChoice = (mode) => {
          targetMode = mode === "user" ? "user" : "self";
          controls.selfButton.classList.toggle("is-active", targetMode === "self");
          controls.userButton.classList.toggle("is-active", targetMode === "user");
          controls.search.hidden = targetMode !== "user";
          controls.list.hidden = targetMode !== "user";
          controls.pager.hidden = targetMode !== "user";
          if (targetMode === "self") {
            selectedUser = clean(currentAuthUsername);
            void loadFolders(selectedUser);
          } else {
            selectedUser = "";
            void renderUsers();
          }
          updateSummary();
        };
        const loadFolders = async (user) => {
          if (!isAdd) return;
          const token = ++folderToken;
          controls.destination.textContent = "";
          const root = document.createElement("option");
          root.value = clean(user);
          root.textContent = "Vault root";
          controls.destination.appendChild(root);
          try {
            const result = await fetchServerJson(`/server-data/vault-folders?user=${encodeURIComponent(user)}`);
            if (token !== folderToken) return;
            const rows = Array.isArray(result.payload && result.payload.folders) ? result.payload.folders : [];
            const byId = new Map(rows.map((row) => [clean(row.vault_folder_id), row]));
            const pathFor = (row) => {
              const parts = [];
              let current = row;
              let guard = 0;
              while (current && guard++ < rows.length + 1) {
                const name = clean(current.display_name);
                if (name && clean(current.folder_type).toUpperCase() !== "ROOT" && clean(current.parent_folder_id)) {
                  parts.unshift(name);
                }
                current = byId.get(clean(current.parent_folder_id));
              }
              return parts.join(" / ");
            };
            rows.filter((row) => clean(row.vault_folder_id) && !/^vault-root-/i.test(clean(row.vault_folder_id))).forEach((row) => {
              const option = document.createElement("option");
              option.value = clean(row.vault_folder_id);
              option.dataset.path = pathFor(row);
              option.textContent = pathFor(row) || clean(row.display_name) || "Folder";
              controls.destination.appendChild(option);
            });
            updateSummary();
          } catch (error) {
            const option = document.createElement("option");
            option.value = clean(user);
            option.textContent = "Vault root (folder list unavailable)";
            controls.destination.replaceChildren(option);
            updateSummary();
          }
        };
        const renderUsers = async () => {
          const token = ++requestToken;
          controls.list.textContent = "Loading users...";
          try {
            const query = new URLSearchParams({ picker: "1", search: controls.search.value.trim(), page: String(page), page_size: "10" });
            const result = await fetchServerJson(`/auth/admin-users?${query.toString()}`);
            if (token !== requestToken) return;
            const payload = result.payload || {};
            const users = Array.isArray(payload.users) ? payload.users : [];
            controls.list.textContent = "";
            if (!users.length) controls.list.textContent = "No matching users.";
            users.forEach((user) => {
              const button = document.createElement("button");
              button.type = "button";
              button.className = "ft-admin-target-user";
              button.classList.toggle("is-active", clean(user.username).toLowerCase() === selectedUser.toLowerCase());
              button.innerHTML = `<strong></strong><span></span>`;
              button.querySelector("strong").textContent = `@${clean(user.username)}`;
              button.querySelector("span").textContent = clean(user.full_name || (user.is_admin ? "Admin" : "Learner"));
              button.addEventListener("click", () => {
                selectedUser = clean(user.username);
                controls.list.querySelectorAll(".ft-admin-target-user").forEach((item) => item.classList.remove("is-active"));
                button.classList.add("is-active");
                void loadFolders(selectedUser);
                updateSummary();
              });
              controls.list.appendChild(button);
            });
            const pages = Math.max(1, Number(payload.pages || payload.total_pages || 1));
            controls.pager.textContent = `Page ${page}/${pages} - ${Number(payload.total || 0)} users`;
            if (pages > 1) {
              const previous = document.createElement("button");
              previous.type = "button";
              previous.textContent = "Previous";
              previous.disabled = page <= 1;
              previous.addEventListener("click", () => { page -= 1; void renderUsers(); });
              const next = document.createElement("button");
              next.type = "button";
              next.textContent = "Next";
              next.disabled = page >= pages;
              next.addEventListener("click", () => { page += 1; void renderUsers(); });
              controls.pager.prepend(previous);
              controls.pager.append(next);
            }
          } catch (error) {
            if (token === requestToken) controls.list.textContent = error && error.message ? error.message : "Could not load users.";
          }
        };
        controls.selfButton.onclick = () => setChoice("self");
        controls.userButton.onclick = () => setChoice("user");
        controls.search.oninput = () => {
          window.clearTimeout(controls.search._futureSearchTimer || 0);
          controls.search._futureSearchTimer = window.setTimeout(() => { page = 1; void renderUsers(); }, 180);
        };
        controls.destination.onchange = updateSummary;
        controls.confirm.onclick = () => {
          if (!selectedUser || controls.confirm.disabled) return;
          const selectedOption = controls.destination.options[controls.destination.selectedIndex];
          const destinationPath = isAdd
            ? (selectedOption && selectedOption.dataset.path ? `${selectedUser}/${selectedOption.dataset.path}` : selectedUser)
            : selectedUser;
          closeAdminVaultTargetPicker({ username: selectedUser, destination: destinationPath });
        };
        controls.selfButton.textContent = isAdd ? "My Vault" : "Assign to myself";
        controls.userButton.textContent = isAdd ? "Another user's Vault" : "Assign to a user";
        setChoice("self");
        if (targetMode === "user") await renderUsers();
        window.setTimeout(() => {
          const focusTarget = targetMode === "user" ? controls.search : controls.confirm;
          try {
            focusTarget.focus({ preventScroll: true });
          } catch (error) {
          }
        }, 30);
        return await new Promise((resolve) => { adminVaultTargetResolve = resolve; });
      };

      const addLessonTask = async (owner, entry = {}, triggerButton = null, options = {}) => {
        const targetUser = clean(owner);
        const path = normalizeServerPathValue(entry.path);
        if (!targetUser || !path) {
          return;
        }
        const approved = options.skipConfirm === true || await confirmSpaceTaskMutation({
          title: "Add Task",
          body: `Add ${clean(entry.name || path)} to ${targetUser}'s task board?`,
          confirmLabel: "Add task",
        });
        if (!approved) {
          return;
        }
        if (triggerButton) {
          triggerButton.disabled = true;
          triggerButton.textContent = "Adding";
        }
        try {
          const result = await fetchServerJson("/lesson-tasks", {
            method: "POST",
            body: JSON.stringify({
              action: "add",
              user: targetUser,
              path,
              effective_path: normalizeServerPathValue(entry.effective_path || ""),
              link_target: normalizeServerPathValue(entry.link_target || ""),
              title: clean(entry.title || ""),
              name: clean(entry.name || path),
              folder_id: clean(entry.folder_id || entry.folderId || ""),
              folder_path: normalizeServerPathValue(entry.folder_path || entry.folder || ""),
            }),
            headers: { "Content-Type": "application/json" },
          });
          clearServerBrowserListCacheForOwner(targetUser);
          clearLessonTaskPanelCacheForOwner(targetUser);
          const visibleOwner = clean(currentTaskPayload && currentTaskPayload.task_owner || serverTaskOwnerContext || currentAuthUsername);
          if (!visibleOwner || authUsernameMatches(visibleOwner, targetUser)) {
            serverTaskOwnerContext = targetUser;
          }
          applyLessonTaskMutation(result.payload, targetUser, "upsert");
          setLoadStatus("Task synced to learner board.");
        } catch (error) {
          if (triggerButton) {
            triggerButton.disabled = Boolean(entry.task);
            triggerButton.textContent = entry.task ? "In tasks" : "Add task";
          }
          setLoadStatus(error && error.message ? error.message : "Could not add lesson task.", true);
        }
      };

      const updateLessonTaskSeverity = async (owner, task = {}, severity = "normal") => {
        const targetUser = clean(owner);
        if (!targetUser) {
          return;
        }
        try {
          const result = await fetchServerJson("/lesson-tasks", {
            method: "POST",
            body: JSON.stringify({
              action: "severity",
              user: targetUser,
              id: task.id || "",
              path: task.path || "",
              severity,
            }),
            headers: { "Content-Type": "application/json" },
          });
          clearServerBrowserListCacheForOwner(targetUser);
          clearLessonTaskPanelCacheForOwner(targetUser);
          window.__ftLessonTaskMutationBurstUntil = Date.now() + 3000;
          applyLessonTaskMutation(result.payload, targetUser, "upsert");
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "Could not update task severity.", true);
        }
      };

      const removeLessonTask = async (owner, task = {}) => {
        const targetUser = clean(owner);
        if (!targetUser) {
          return;
        }
        const folderGroup = lessonTaskFolderGroupFromTask(task);
        const visibleRows = lessonTaskDisplayRows(currentTaskPayload);
        const groupRows = folderGroup.folderBacked
          ? visibleRows.filter((item) => lessonTaskFolderGroupFromTask(item).key === folderGroup.key)
          : visibleRows.filter((item) => taskIdentityMatches(item, clean(task.id || ""), normalizeTaskPath(task.path || "")));
        const removeCount = Math.max(1, groupRows.length);
        const approved = await confirmSpaceTaskMutation({
          title: folderGroup.folderBacked ? "Remove Folder Group" : "Remove Task",
          body: folderGroup.folderBacked
            ? `Remove folder "${folderGroup.folderName || folderGroup.folderPath}" và ${removeCount} file khỏi Space Task?`
            : `Remove "${clean(task.title || task.name || task.path || "this task")}" khỏi Space Task?`,
          confirmLabel: folderGroup.folderBacked ? `Remove ${removeCount} files` : "Remove task",
        });
        if (!approved) {
          return;
        }
        try {
          const result = await fetchServerJson("/lesson-tasks", {
            method: "POST",
            body: JSON.stringify({
              action: "remove",
              user: targetUser,
              id: task.id || "",
              path: task.path || "",
              folder_group_key: folderGroup.key,
              folder_id: folderGroup.folderId,
              folder_path: folderGroup.folderPath,
              space_task: Boolean(task.space_task),
              baseRevision: clean(currentTaskPayload.space_task && currentTaskPayload.space_task.updated_rev || ""),
            }),
            headers: { "Content-Type": "application/json" },
          });
          clearServerBrowserListCacheForOwner(targetUser);
          clearLessonTaskPanelCacheForOwner(targetUser);
          applyLessonTaskMutation(result.payload, targetUser, "remove");
          setLoadStatus(folderGroup.folderBacked
            ? `Removed folder ${folderGroup.folderName || folderGroup.folderPath}: ${Number(result.payload.removed_count || removeCount)} files.`
            : "Task removed from Space Task.");
        } catch (error) {
          setLoadStatus(error && error.message ? error.message : "Could not remove lesson task.", true);
        }
      };

      const classifyServerJsonError = (error, path = "") => {
        if (!error) return { kind: "unknown", label: "unknown" };
        const msg = clean(error.message || "").toLowerCase();
        if (error.isServerApplicationError) return { kind: "server_app", label: "server-app-error" };
        if (error.isHttpError) return { kind: "http", label: `http-${error.httpStatus || "?"}` };
        if (error.isTimeoutError || msg.includes("timed out") || msg.includes("timeout")) return { kind: "timeout", label: "timeout" };
        if (
          error.isNetworkError ||
          msg.includes("failed to fetch") ||
          msg.includes("network") ||
          msg.includes("networkerror") ||
          msg.includes("net::") ||
          msg.includes("load failed") ||
          msg.includes("aborted") ||
          msg.includes("offline") ||
          !navigator.onLine
        ) return { kind: "network", label: "network" };
        return { kind: "client", label: "client-error" };
      };

        const fetchServerJson = async (path, options = {}) => {
        const errors = [];
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        const requestedTimeoutMs = Number(options && options.timeoutMs || 0);
          const useRequestTimeout = requestedTimeoutMs > 0 || String(path || "").startsWith("/server-data/list");
          const requestTimeoutMs = requestedTimeoutMs > 0 ? requestedTimeoutMs : 90000;
          const fetchOptions = { ...(options || {}) };
          delete fetchOptions.timeoutMs;
          const ifNoneMatch = clean(fetchOptions.ifNoneMatch || "");
          const notModifiedPayload = fetchOptions.notModifiedPayload && typeof fetchOptions.notModifiedPayload === "object"
            ? fetchOptions.notModifiedPayload
            : null;
          const canRevalidate = Boolean(ifNoneMatch && notModifiedPayload);
          delete fetchOptions.ifNoneMatch;
          delete fetchOptions.notModifiedPayload;
          const requestCacheMode = clean(fetchOptions.cache || "") || "no-store";
          for (const base of candidates) {
          try {
            const headers = await antiRobotHeaders(base, fetchOptions.headers || {});
            if (authToken) {
              headers.Authorization = `Bearer ${authToken}`;
            }
            const completionTraceId = clean(window.__ftCompletionTraceId || "");
            if (completionTraceId && Number(window.__ftCompletionTraceUntil || 0) > Date.now()) {
              headers["X-Future-Completion-Trace"] = completionTraceId;
            }
            if (canRevalidate) {
              headers["If-None-Match"] = ifNoneMatch;
            }
              let response = useRequestTimeout
                ? await fetchWithTimeout(`${base}${path}`, { ...fetchOptions, headers, mode: "cors", cache: requestCacheMode }, requestTimeoutMs)
                : await fetch(`${base}${path}`, { ...fetchOptions, headers, mode: "cors", cache: requestCacheMode });
            if (response.status === 304 && !notModifiedPayload) {
              delete headers["If-None-Match"];
              response = useRequestTimeout
                ? await fetchWithTimeout(`${base}${path}`, { ...fetchOptions, headers, mode: "cors", cache: "no-store" }, requestTimeoutMs)
                : await fetch(`${base}${path}`, { ...fetchOptions, headers, mode: "cors", cache: "no-store" });
            }
            const responseEtag = clean(response.headers && response.headers.get ? response.headers.get("ETag") : "");
            const topPending = clean(response.headers && response.headers.get ? response.headers.get("X-Future-Top-Pending") : "") === "1";
            const topRevision = Math.max(0, Math.floor(Number(response.headers && response.headers.get ? response.headers.get("X-Future-Top-Revision") : 0) || 0));
            const topPublishedRevision = Math.max(0, Math.floor(Number(response.headers && response.headers.get ? response.headers.get("X-Future-Top-Published-Revision") : 0) || 0));
            const topRetryMs = Math.max(0, Math.floor(Number(response.headers && response.headers.get ? response.headers.get("X-Future-Top-Retry-Ms") : 0) || 0));
            if (response.status === 304 && notModifiedPayload) {
              return { base, payload: notModifiedPayload, notModified: true, etag: responseEtag || ifNoneMatch, topPending, topRevision, topPublishedRevision, topRetryMs };
            }
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.ok === false) {
              const error = new Error(clean(payload.error) || `Server loi ${response.status}`);
              error.isHttpError = !response.ok;
              error.httpStatus = response.status;
              if (payload && (payload.ok === false || clean(payload.error))) {
                error.isServerApplicationError = true;
              }
              throw error;
            }
            return { base, payload, etag: responseEtag, topPending, topRevision, topPublishedRevision, topRetryMs };
          } catch (error) {
            if (error && error.isServerApplicationError) {
              throw error;
            }
            // Tag network/timeout errors for downstream classifiers.
            const msg = clean((error && error.message) || "").toLowerCase();
            if (!error.isHttpError) {
              if (msg.includes("timed out") || msg.includes("timeout")) {
                error.isTimeoutError = true;
              } else if (
                msg.includes("failed to fetch") || msg.includes("networkerror") ||
                msg.includes("net::") || msg.includes("load failed") || !navigator.onLine
              ) {
                error.isNetworkError = true;
              }
            }
            errors.push(`${base}: ${error && error.message ? error.message : error}`);
          }
        }
        const finalError = new Error(`Khong mo duoc server data. Da thu: ${errors.join(" | ")}`);
        finalError.isNetworkError = !navigator.onLine;
        throw finalError;
      };

      const SERVER_FILE_TEXT_CACHE_NAME = "future-server-file-text-v1";
      const SERVER_FILE_TEXT_CACHE_SCHEMA = "1";
      const SERVER_FILE_TEXT_MEMORY_MAX = 64;
      const SERVER_FILE_TEXT_PERSISTENT_MAX = 128;
      const serverFileTextMemoryCache = new Map();
      let serverFileTextPersistentWrites = 0;

      const serverFileTextCacheIdentity = (path = "") => [
        SERVER_FILE_TEXT_CACHE_SCHEMA,
        clean(currentAuthUsername || "").toLowerCase(),
        clean(path || ""),
      ].join("|");

      const serverFileTextCacheRequestUrl = (path = "") => {
        const identity = serverFileTextCacheIdentity(path);
        return `${window.location.origin || "http://future.local"}/__future_server_file_text_cache__/${encodeURIComponent(identity)}`;
      };

      const rememberServerFileTextMemory = (path = "", row = null) => {
        if (!row || typeof row.text !== "string" || !row.text.length || !clean(row.etag || "")) {
          return;
        }
        const key = serverFileTextCacheIdentity(path);
        serverFileTextMemoryCache.set(key, { text: row.text, etag: clean(row.etag), at: Date.now() });
        if (serverFileTextMemoryCache.size > SERVER_FILE_TEXT_MEMORY_MAX) {
          const ordered = Array.from(serverFileTextMemoryCache.entries()).sort((a, b) => Number(a[1].at || 0) - Number(b[1].at || 0));
          ordered.slice(0, Math.max(1, ordered.length - SERVER_FILE_TEXT_MEMORY_MAX)).forEach(([oldKey]) => serverFileTextMemoryCache.delete(oldKey));
        }
      };

      const readServerFileTextCache = async (path = "") => {
        const key = serverFileTextCacheIdentity(path);
        const memory = serverFileTextMemoryCache.get(key);
        if (memory && typeof memory.text === "string" && memory.text.length && clean(memory.etag || "")) {
          memory.at = Date.now();
          return { text: memory.text, etag: clean(memory.etag), source: "memory" };
        }
        if (typeof caches === "undefined") {
          return null;
        }
        try {
          const cache = await caches.open(SERVER_FILE_TEXT_CACHE_NAME);
          const response = await cache.match(serverFileTextCacheRequestUrl(path));
          if (!response || clean(response.headers.get("X-Future-Cache-Schema")) !== SERVER_FILE_TEXT_CACHE_SCHEMA) {
            return null;
          }
          const etag = clean(response.headers.get("X-Future-Source-Etag"));
          if (!etag) {
            return null;
          }
          const text = await response.text();
          if (!text.length) {
            await cache.delete(serverFileTextCacheRequestUrl(path));
            return null;
          }
          const row = { text, etag, source: "persistent" };
          rememberServerFileTextMemory(path, row);
          return row;
        } catch (error) {
          return null;
        }
      };

      const persistServerFileTextCache = async (path = "", row = null) => {
        if (!row || typeof row.text !== "string" || !row.text.length || !clean(row.etag || "")) {
          return;
        }
        rememberServerFileTextMemory(path, row);
        if (typeof caches === "undefined") {
          return;
        }
        try {
          const cache = await caches.open(SERVER_FILE_TEXT_CACHE_NAME);
          await cache.put(serverFileTextCacheRequestUrl(path), new Response(row.text, {
            headers: {
              "Content-Type": "text/plain; charset=utf-8",
              "X-Future-Cache-Schema": SERVER_FILE_TEXT_CACHE_SCHEMA,
              "X-Future-Source-Etag": clean(row.etag),
            },
          }));
          serverFileTextPersistentWrites += 1;
          if (serverFileTextPersistentWrites % 16 === 0) {
            const keys = await cache.keys();
            await Promise.all(keys.slice(0, Math.max(0, keys.length - SERVER_FILE_TEXT_PERSISTENT_MAX)).map((request) => cache.delete(request)));
          }
        } catch (error) {
          // CacheStorage is optional; the authenticated network path remains authoritative.
        }
      };

      const fetchServerTextFromBase = async (base, path, timeoutMs = 9000, cachedRow = null) => {
        const numericTimeoutMs = Number(timeoutMs);
        const useTimeout = Number.isFinite(numericTimeoutMs) ? numericTimeoutMs > 0 : true;
        const controller = useTimeout && typeof AbortController !== "undefined" ? new AbortController() : null;
        const timer = controller && useTimeout
          ? window.setTimeout(() => {
            try {
              controller.abort();
            } catch (error) {
              // The request is already settled.
            }
          }, Math.max(1500, Number.isFinite(numericTimeoutMs) ? numericTimeoutMs : 9000))
          : 0;
        try {
          const headers = {};
          if (authToken) {
            headers.Authorization = `Bearer ${authToken}`;
          }
          if (cachedRow && typeof cachedRow.text === "string" && cachedRow.text.length && clean(cachedRow.etag || "")) {
            headers["If-None-Match"] = clean(cachedRow.etag);
          }
          let response = await fetch(`${base}${path}`, {
            headers,
            mode: "cors",
            cache: "no-store",
            ...(controller ? { signal: controller.signal } : {}),
          });
          if (response.status === 304) {
            if (cachedRow && typeof cachedRow.text === "string" && cachedRow.text.length) {
              return { base, text: cachedRow.text, etag: clean(response.headers.get("ETag")) || clean(cachedRow.etag), notModified: true };
            }
            delete headers["If-None-Match"];
            response = await fetch(`${base}${path}`, {
              headers,
              mode: "cors",
              cache: "no-store",
              ...(controller ? { signal: controller.signal } : {}),
            });
          }
          if (!response.ok) {
            const message = await response.text().catch(() => "");
            throw new Error(clean(message) || `Server loi ${response.status}`);
          }
          return {
            base,
            text: decodeUtf8Buffer(await response.arrayBuffer()),
            etag: clean(response.headers.get("ETag")),
            notModified: false,
          };
        } finally {
          if (timer) {
            window.clearTimeout(timer);
          }
        }
      };

      const fetchServerText = async (path) => {
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        const errors = [];
        const isServerFileRequest = clean(path).startsWith("/server-data/file");
        const cachedRow = isServerFileRequest ? await readServerFileTextCache(path) : null;
        const serverFileTimeout = isServerFileRequest ? 0 : 90000;
        const serverFileParallelTimeout = isServerFileRequest ? 0 : 9000;
        const requestFromBase = async (base, timeoutMs) => {
          const result = await fetchServerTextFromBase(base, path, timeoutMs, cachedRow);
          if (isServerFileRequest && result && !result.notModified && clean(result.etag || "")) {
            void persistServerFileTextCache(path, { text: result.text, etag: result.etag });
          }
          return result;
        };
        if (candidates.length <= 1) {
          try {
            return await requestFromBase(candidates[0], serverFileTimeout);
          } catch (error) {
            if (isServerFileRequest && cachedRow && typeof cachedRow.text === "string" && cachedRow.text.length) {
              return { base: "local-cache", text: cachedRow.text, etag: clean(cachedRow.etag), notModified: true, offlineCache: true };
            }
            throw new Error(`Khong tai duoc file tu server. Da thu: ${candidates[0]}: ${error && error.message ? error.message : error}`);
          }
        }
        if (isServerFileRequest) {
          for (const base of candidates) {
            try {
              return await requestFromBase(base, serverFileTimeout);
            } catch (error) {
              errors.push(`${base}: ${error && error.message ? error.message : error}`);
            }
          }
          if (cachedRow && typeof cachedRow.text === "string" && cachedRow.text.length) {
            return { base: "local-cache", text: cachedRow.text, etag: clean(cachedRow.etag), notModified: true, offlineCache: true };
          }
          throw new Error(`Khong tai duoc file tu server. Da thu: ${errors.join(" | ")}`);
        }
        return await new Promise((resolve, reject) => {
          let pending = candidates.length;
          let settled = false;
          candidates.forEach((base) => {
            requestFromBase(base, serverFileParallelTimeout)
              .then((result) => {
                if (settled) {
                  return;
                }
                settled = true;
                resolve(result);
              })
              .catch((error) => {
                errors.push(`${base}: ${error && error.message ? error.message : error}`);
              })
              .finally(() => {
                pending -= 1;
                if (!settled && pending <= 0) {
                  reject(new Error(`Khong tai duoc file tu server. Da thu: ${errors.join(" | ")}`));
                }
              });
          });
        });
      };

      const fetchProgressJsonFromBase = async (base, path, timeoutMs = 7000, cachedRow = null) => {
        const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
        const timer = controller
          ? window.setTimeout(() => {
            try {
              controller.abort();
            } catch (error) {
              // The request is already settled.
            }
          }, Math.max(1200, Number(timeoutMs) || 7000))
          : 0;
        try {
          const headers = {};
          if (authToken) {
            headers.Authorization = `Bearer ${authToken}`;
          }
          if (cachedRow && cachedRow.payload && clean(cachedRow.etag || "")) {
            headers["If-None-Match"] = clean(cachedRow.etag);
          }
          let response = await fetch(`${base}${path}`, {
            headers,
            mode: "cors",
            cache: "no-store",
            ...(controller ? { signal: controller.signal } : {}),
          });
          if (response.status === 304) {
            if (cachedRow && cachedRow.payload && typeof cachedRow.payload === "object") {
              return {
                base,
                payload: cachedRow.payload,
                etag: clean(response.headers.get("ETag")) || clean(cachedRow.etag),
                notModified: true,
              };
            }
            delete headers["If-None-Match"];
            response = await fetch(`${base}${path}`, {
              headers,
              mode: "cors",
              cache: "no-store",
              ...(controller ? { signal: controller.signal } : {}),
            });
          }
          const payload = await response.json().catch(() => ({}));
          if (!response.ok || payload.ok === false) {
            throw new Error(clean(payload.error) || `Server loi ${response.status}`);
          }
          return { base, payload, etag: clean(response.headers.get("ETag")), notModified: false };
        } finally {
          if (timer) {
            window.clearTimeout(timer);
          }
        }
      };

      const fetchProgressJsonFast = async (path, cachedRow = null) => {
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        if (candidates.length <= 1) {
          return await fetchProgressJsonFromBase(candidates[0], path, 9000, cachedRow);
        }
        const errors = [];
        if (/^\/space-(?:v|w|q)\/progress(?:\?|$)/i.test(clean(path))) {
          // Added 2026-07-20: use the current origin first and probe legacy progress servers only after a real failure.
          for (const base of candidates) {
            try {
              return await fetchProgressJsonFromBase(base, path, 9000, cachedRow);
            } catch (error) {
              errors.push(`${base}: ${error && error.message ? error.message : error}`);
            }
          }
          throw new Error(`Khong tai duoc progress. Da thu: ${errors.join(" | ")}`);
        }
        return await new Promise((resolve, reject) => {
          let pending = candidates.length;
          let settled = false;
          candidates.forEach((base) => {
            fetchProgressJsonFromBase(base, path, 7000, cachedRow)
              .then((result) => {
                if (settled) {
                  return;
                }
                settled = true;
                resolve(result);
              })
              .catch((error) => {
                errors.push(`${base}: ${error && error.message ? error.message : error}`);
              })
              .finally(() => {
                pending -= 1;
                if (!settled && pending <= 0) {
                  reject(new Error(`Khong tai duoc progress. Da thu: ${errors.join(" | ")}`));
                }
              });
          });
        });
      };

      const serverLessonProgressSpaceForPath = (path = "", extension = "") => {
        const suffix = clean(extension || (String(path || "").match(/\.[^.\\/]+$/) || [""])[0]).toLowerCase();
        if (suffix === ".space_v" || suffix === ".space_b") {
          return "Space_V";
        }
        if (suffix === ".space_q") {
          return "Space_Q";
        }
        if (suffix === ".space_p") {
          return "Space_P";
        }
        if (suffix === ".space_s") {
          return "Space_S";
        }
        if (suffix === ".space_l") {
          return "Space_L";
        }
        if (suffix === ".pdf" || suffix === ".space_pdf") {
          return "Space_PDF";
        }
        if (suffix === ".space_picture" || isSpacePictureExtension(suffix)) {
          return "Space_Picture";
        }
        if (suffix === ".space_w" || suffix === ".txt") {
          return "Space_W";
        }
        return "";
      };

      const fetchServerProgressForEntry = async (entry = {}) => {
        const filePath = clean(entry && entry.path);
        const space = serverLessonProgressSpaceForPath(filePath, entry && entry.extension);
        if (!filePath || !space) {
          return { space, payload: {} };
        }
        const rawLessonId = clean(entry && (entry.lesson_id || entry.lessonId || entry.file_id || entry.fileId || entry.identity) || "");
        const lessonId = rawLessonId.toLowerCase().startsWith("ftg-lesson-") ? rawLessonId : "";
        const identityRevision = clean(entry && (entry.identity_revision || entry.identityRevision || entry.server_revision || entry.serverRevision || entry.revision) || "0") || "0";
        const cacheTarget = lessonId
          ? `id:${lessonId.toLowerCase()}`
          : `path:${normalizeServerPathValue(filePath).toLowerCase()}`;
        const cacheKey = [
          clean(currentAuthUsername || ""),
          currentAuthIsAdmin ? "admin" : "user",
          space,
          cacheTarget,
          identityRevision,
        ].join("|");
        const cached = serverLessonProgressPrefetchCache.get(cacheKey);
        if (cached && cached.promise && Date.now() - Number(cached.at || 0) <= SERVER_LESSON_PROGRESS_PREFETCH_TTL_MS) {
          return cached.promise;
        }
        if (typeof lessonVaultProgressSnapshotForPaths === "function") {
          const snapshot = lessonVaultProgressSnapshotForPaths([
            lessonId ? `id:${lessonId.toLowerCase()}` : "",
            filePath,
            entry && entry.effective_path,
            entry && entry.effectivePath,
            entry && entry.canonical_path,
            entry && entry.normalized_path,
            entry && entry.link_target,
            entry && entry.linkTarget,
          ]);
          if (snapshot && typeof snapshot === "object") {
            const snapshotPromise = Promise.resolve({ space, payload: snapshot, etag: "lesson-vault-progress-snapshot" });
            serverLessonProgressPrefetchCache.set(cacheKey, { at: Date.now(), promise: snapshotPromise });
            return snapshotPromise;
          }
        }
        const endpoint = space === "Space_V" ? "/space-v/progress" : (space === "Space_Q" ? "/space-q/progress" : (space === "Space_P" || space === "Space_S" || space === "Space_L" ? "/space-p/progress" : (space === "Space_PDF" || space === "Space_Picture" ? "/space-pdf/progress" : "/space-w/progress")));
        const query = new URLSearchParams();
        query.set("path", filePath);
        if (lessonId) {
          query.set("identity", lessonId);
          query.set("lesson_id", lessonId);
        }
        const promise = fetchProgressJsonFast(`${endpoint}?${query.toString()}`)
          .then((result) => ({
            space,
            payload: result && result.payload ? result.payload : {},
            etag: clean(result && result.etag || ""),
          }))
          .catch((error) => {
            serverLessonProgressPrefetchCache.delete(cacheKey);
            throw error;
          });
        serverLessonProgressPrefetchCache.set(cacheKey, { at: Date.now(), promise });
        if (serverLessonProgressPrefetchCache.size > 80) {
          const ordered = Array.from(serverLessonProgressPrefetchCache.entries()).sort((a, b) => Number(a[1].at || 0) - Number(b[1].at || 0));
          ordered.slice(0, Math.max(1, ordered.length - 60)).forEach(([key]) => serverLessonProgressPrefetchCache.delete(key));
        }
        return promise;
      };

      const scheduleServerLessonProgressPrefetch = (entry = {}, delayMs = 320) => {
        if (Date.now() < Number(window.__ftLessonVaultProgressHydrationPausedUntil || 0)) {
          return;
        }
        if (serverLessonProgressPrefetchTimer) {
          window.clearTimeout(serverLessonProgressPrefetchTimer);
          serverLessonProgressPrefetchTimer = 0;
        }
        const filePath = normalizeServerPathValue(entry && entry.path);
        if (!filePath) {
          return;
        }
        serverLessonProgressPrefetchTimer = window.setTimeout(() => {
          serverLessonProgressPrefetchTimer = 0;
          if (Date.now() < Number(window.__ftLessonVaultProgressHydrationPausedUntil || 0)) {
            return;
          }
          if (serverBrowserBusy || normalizeTaskPath(serverBrowserFocusedFilePath) !== normalizeTaskPath(filePath)) {
            return;
          }
          void fetchServerProgressForEntry(entry).catch(() => {});
        }, Math.max(120, Number(delayMs) || 320));
      };

      const serverSpaceVStatsUserForContext = (fallbackUser = "") => {
        if (currentAuthIsAdmin) {
          return clean(fallbackUser || serverTaskOwnerContext || currentAuthUsername);
        }
        return clean(currentAuthUsername || fallbackUser || "");
      };

      const fileSupportsVocabularyStats = (entry = {}) => {
        const extension = clean(entry && entry.extension).toLowerCase();
        const path = clean(entry && entry.path).toLowerCase();
        return [".space_v", ".space_b", ".space_w", ".space_q", ".space_p", ".space_s", ".space_l"].includes(extension)
          || /\.(space_v|space_b|space_w|space_q|space_p|space_s|space_l)$/i.test(path);
      };

      const clearSpaceVFileStatsChips = (rowNode) => {
        if (!rowNode) {
          document.querySelectorAll(".ft-space-v-new-chip").forEach((node) => node.remove());
          return;
        }
        const chips = rowNode.querySelector(".ft-server-chip-row, .ft-task-meta");
        if (!chips) {
          return;
        }
        chips.querySelectorAll(".ft-space-v-new-chip").forEach((node) => node.remove());
      };

      // Added 2026-07-28: replay the task-focus burst after dynamic New/Earn chips enter the DOM.
      const replayTaskFocusedStatsChipBurst = (rowNode) => {
        if (!rowNode || !rowNode.classList.contains("is-task-focus")) {
          return;
        }
        window.clearTimeout(rowNode._futureTaskFocusBurstTimer || 0);
        rowNode.classList.remove("is-task-focus-burst");
        void rowNode.offsetWidth;
        rowNode.classList.add("is-task-focus-burst");
        rowNode._futureTaskFocusBurstTimer = window.setTimeout(() => {
          rowNode.classList.remove("is-task-focus-burst");
          rowNode._futureTaskFocusBurstTimer = 0;
        }, 2400);
      };

      const renderSpaceVFileStatsChip = (rowNode, stats = null, label = "", options = {}) => {
        if (!rowNode || !stats || typeof stats !== "object") {
          return;
        }
        const chips = rowNode.querySelector(".ft-server-chip-row, .ft-task-meta");
        if (!chips) {
          return;
        }
        const newWords = Math.max(0, Math.floor(Number(stats.new_words || 0) || 0));
        const totalWords = Math.max(0, Math.floor(Number(stats.total_words || 0) || 0));
        const opts = options && typeof options === "object" ? options : {};
        const ownerLabel = opts.showLabel === false ? "" : clean(label || stats.label || "");
        const spaceLabel = clean(stats.space || opts.space || "lesson").replace(/^Space_/, "Space ");
        const prefix = ownerLabel ? `${ownerLabel}: ` : "";
        const chip = createServerChip(
          newWords ? `${prefix}New ${newWords}/${totalWords}` : `${prefix}0 New / ${totalWords}`,
          newWords ? "total" : "learned",
        );
        chip.classList.add("ft-space-v-new-chip");
        chip.title = `${ownerLabel || clean(stats.user || "User")} has ${newWords} new vocabulary word${newWords === 1 ? "" : "s"} in this ${spaceLabel} file.`;
        chips.appendChild(chip);
        const earnable = stats.top_earnable && typeof stats.top_earnable === "object"
          ? stats.top_earnable
          : (stats.topEarnable && typeof stats.topEarnable === "object" ? stats.topEarnable : {});
        [
          ["day", "today"],
          ["week", "this week"],
          ["month", "this month"],
        ].forEach(([scope, labelText]) => {
          const count = Math.max(0, Math.floor(Number(earnable[scope] || 0) || 0));
          const earnChip = createServerChip(`${prefix}Earn ${count}/${totalWords} ${labelText}`, count ? "vocab-top" : "learned");
          earnChip.classList.add("ft-space-v-new-chip", `is-top-${scope}`);
          earnChip.title = `${ownerLabel || clean(stats.user || "User")} can add ${count} unique word${count === 1 ? "" : "s"} from this file to the ${labelText} leaderboard. Words already counted in this period are not counted again.`;
          chips.appendChild(earnChip);
        });
      };

      const fetchSpaceVFileStatsForUser = async (entry = {}, user = "") => {
        const filePath = normalizeServerPathValue(entry.path || "");
        const targetUser = clean(user || currentAuthUsername || "");
        if (!filePath || !targetUser) {
          return null;
        }
        const cacheKey = `${clean(currentAuthUsername || "").toLowerCase()}|${targetUser.toLowerCase()}|${filePath.toLowerCase()}`;
        const cached = serverSpaceVFileStatsCache.get(cacheKey);
        if (cached && cached.payload && Date.now() - Number(cached.at || 0) < 15000) {
          return cached.payload;
        }
        // Added 2026-07-06: send link aliases so server stats can resolve copied/task Space_V entries without broad scans.
        const aliases = [
          entry.effective_path,
          entry.link_target,
          entry.linked_path,
          entry.original_path,
          entry.source_path,
          entry.path,
        ].map((path) => normalizeServerPathValue(path)).filter(Boolean);
        const result = await fetchServerJson("/vocab/file-stats", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            path: filePath,
            user: targetUser,
            effective_path: normalizeServerPathValue(entry.effective_path || ""),
            link_target: normalizeServerPathValue(entry.link_target || ""),
            linked_path: normalizeServerPathValue(entry.linked_path || ""),
            aliases,
          }),
        });
        const payload = result && result.payload ? result.payload : {};
        serverSpaceVFileStatsCache.set(cacheKey, { at: Date.now(), payload });
        if (typeof writeSpaceVFileStatsLocalCache === "function") {
          writeSpaceVFileStatsLocalCache(entry, targetUser, payload);
        }
        return payload;
      };

      const announceSpaceVFileStats = async (entry = {}, rowNode = null, targetUser = "") => {
        if (!authToken || !fileSupportsVocabularyStats(entry)) {
          return null;
        }
        const filePath = normalizeServerPathValue(entry.path || "");
        const learnerUser = serverSpaceVStatsUserForContext(targetUser);
        const adminUser = clean(currentAuthUsername || "");
        const dualAdminView = Boolean(currentAuthIsAdmin && adminUser && learnerUser && adminUser.toLowerCase() !== learnerUser.toLowerCase());
        if (!filePath || !learnerUser) {
          return null;
        }
        clearSpaceVFileStatsChips();
        clearSpaceVFileStatsChips(rowNode);
        const spaceLabel = clean(entry.space || entry.space_label || entry.extension || "lesson").replace(/^\./, "").replace(/_/g, " ").toUpperCase();
        const cachedLearnerStats = typeof readSpaceVFileStatsLocalCache === "function"
          ? readSpaceVFileStatsLocalCache(entry, learnerUser)
          : null;
        const cachedAdminStats = dualAdminView && typeof readSpaceVFileStatsLocalCache === "function"
          ? readSpaceVFileStatsLocalCache(entry, adminUser)
          : null;
        let renderedCachedStats = false;
        if (dualAdminView && cachedAdminStats) {
          renderSpaceVFileStatsChip(rowNode, cachedAdminStats, "Admin", { showLabel: true });
          renderedCachedStats = true;
        }
        if (cachedLearnerStats) {
          renderSpaceVFileStatsChip(rowNode, cachedLearnerStats, learnerUser, { showLabel: dualAdminView });
          renderedCachedStats = true;
        }
        if (!renderedCachedStats) {
          renderSpaceVFileStatsChip(rowNode, { new_words: 0, total_words: Number(entry.word_count || entry.words || 0) || 0, space: spaceLabel }, "Checking");
        }
        replayTaskFocusedStatsChipBurst(rowNode);
        const localStatsReady = (stats) => Boolean(stats && stats.localEstimate && Number(stats.total_words || 0) > 0);
        if (dualAdminView ? (localStatsReady(cachedAdminStats) && localStatsReady(cachedLearnerStats)) : localStatsReady(cachedLearnerStats)) {
          const rows = dualAdminView
            ? [
              { user: adminUser, label: "Admin", stats: cachedAdminStats },
              { user: learnerUser, label: learnerUser, stats: cachedLearnerStats },
            ]
            : [{ user: learnerUser, label: learnerUser, stats: cachedLearnerStats }];
          const parts = rows.map((row) => {
            const stats = row.stats || {};
            const newWords = Number(stats.new_words || 0) || 0;
            const totalWords = Number(stats.total_words || 0) || 0;
            const earnable = stats.top_earnable && typeof stats.top_earnable === "object"
              ? stats.top_earnable
              : (stats.topEarnable && typeof stats.topEarnable === "object" ? stats.topEarnable : {});
            const dayEarn = Math.max(0, Math.floor(Number(earnable.day || 0) || 0));
            const weekEarn = Math.max(0, Math.floor(Number(earnable.week || 0) || 0));
            const monthEarn = Math.max(0, Math.floor(Number(earnable.month || 0) || 0));
            return `${row.label}: ${newWords}/${totalWords} new | earn ${dayEarn}/${totalWords} today, ${weekEarn}/${totalWords} week, ${monthEarn}/${totalWords} month`;
          });
          setLoadStatus(`${spaceLabel} selected. ${parts.join(" | ")}. Local word-key preview.`);
          return rows.length === 1 ? rows[0].stats : { admin: rows[0].stats, learner: rows[1].stats };
        }
        // Added 2026-07-28: fetch only compact keys for this file on a cold cache, then calculate every chip locally.
        try {
          const resolvedEntry = await fetchVocabFileKeyMap(entry, learnerUser);
          const learnerStats = typeof statsFromEntryVocabWordKeys === "function"
            ? statsFromEntryVocabWordKeys(resolvedEntry, learnerUser)
            : null;
          const resolvedStats = learnerStats || (resolvedEntry.vocab_stats && typeof resolvedEntry.vocab_stats === "object" ? resolvedEntry.vocab_stats : null);
          if (resolvedStats) {
            writeSpaceVFileStatsLocalCache(resolvedEntry, learnerUser, resolvedStats);
            clearSpaceVFileStatsChips(rowNode);
            renderSpaceVFileStatsChip(rowNode, resolvedStats, learnerUser, { showLabel: dualAdminView });
            replayTaskFocusedStatsChipBurst(rowNode);
            const earn = resolvedStats.top_earnable || {};
            setLoadStatus(`${spaceLabel} selected. ${resolvedStats.new_words}/${resolvedStats.total_words} new | earn ${earn.day || 0}/${resolvedStats.total_words} today, ${earn.week || 0}/${resolvedStats.total_words} week, ${earn.month || 0}/${resolvedStats.total_words} month.${learnerStats ? " Local word-key preview." : " Server key check."}`);
            return resolvedStats;
          }
        } catch (error) {
          // Keep file selection usable when a cold-cache metadata request fails.
        }
        if (!renderedCachedStats) {
          clearSpaceVFileStatsChips(rowNode);
          setLoadStatus(`${spaceLabel} selected. Use Let's go to open this lesson.`);
        } else {
          setLoadStatus(`${spaceLabel} selected. Showing cached local vocabulary stats for ${learnerUser}.`);
        }
        return cachedLearnerStats || null;
      };

      const questionInventoryUserKey = () => clean(currentAuthUsername || (authUser && authUser.value) || "guest").toLowerCase() || "guest";

      const questionInventoryStorageKey = () => `future_question_inventory:${questionInventoryUserKey()}`;

      const defaultQuestionInventoryState = () => ({
        version: 1,
        items: {},
        events: [],
        pending: [],
        updated_at: "",
      });

      const normalizeQuestionInventoryState = (value = {}) => {
        const source = value && typeof value === "object" ? value : {};
        const items = {};
        const rawItems = source.items && typeof source.items === "object" ? source.items : {};
        Object.entries(rawItems).forEach(([key, item]) => {
          const data = item && typeof item === "object" ? item : {};
          const id = clean(data.id || key || "crystal").toLowerCase() || "crystal";
          items[id] = {
            id,
            name: clean(data.name || data.title || questionRewardConfig.crystal.name || "Prism Crystal"),
            use: preserveQuestionText(data.use || data.purpose || data.description || questionRewardConfig.crystal.use || ""),
            quantity: Math.max(0, Math.floor(Number(data.quantity ?? data.count ?? 0) || 0)),
            updated_at: clean(data.updated_at || data.updatedAt || ""),
          };
        });
        const events = Array.isArray(source.events) ? source.events.map(clean).filter(Boolean).slice(-512) : [];
        const pending = Array.isArray(source.pending) ? source.pending.filter((entry) => entry && typeof entry === "object").slice(-500) : [];
        return {
          version: 1,
          items,
          events,
          pending,
          updated_at: clean(source.updated_at || source.updatedAt || ""),
        };
      };

      const readLocalQuestionInventory = () => {
        try {
          return normalizeQuestionInventoryState(JSON.parse(localStorage.getItem(questionInventoryStorageKey()) || "{}"));
        } catch (error) {
          return defaultQuestionInventoryState();
        }
      };

      const writeLocalQuestionInventory = (state) => {
        questionInventoryState = normalizeQuestionInventoryState(state);
        try {
          localStorage.setItem(questionInventoryStorageKey(), JSON.stringify(questionInventoryState));
        } catch (error) {
        }
        updateQuestionInventoryHud();
        return questionInventoryState;
      };

      const mergeQuestionInventoryState = (baseState, nextState) => {
        const base = normalizeQuestionInventoryState(baseState);
        const next = normalizeQuestionInventoryState(nextState);
        Object.entries(next.items).forEach(([id, item]) => {
          const current = base.items[id] || { id, name: item.name, use: item.use, quantity: 0 };
          base.items[id] = {
            id,
            name: item.name || current.name,
            use: item.use || current.use,
            quantity: Math.max(Number(current.quantity || 0), Number(item.quantity || 0)),
            updated_at: item.updated_at || current.updated_at || "",
          };
        });
        const eventSet = new Set([...(base.events || []), ...(next.events || [])].map(clean).filter(Boolean));
        base.events = Array.from(eventSet).slice(-512);
        base.pending = Array.isArray(base.pending) ? base.pending : [];
        base.updated_at = next.updated_at || base.updated_at || "";
        return base;
      };

      // Added 2026-07-20: an award delta is canonical, so duplicate retries undo optimistic over-counts.
      const applyQuestionInventoryDelta = (baseState, deltaState) => {
        const base = normalizeQuestionInventoryState(baseState);
        const delta = normalizeQuestionInventoryState(deltaState);
        Object.entries(delta.items).forEach(([id, item]) => {
          base.items[id] = { ...item };
        });
        base.events = Array.from(new Set([...(base.events || []), ...(delta.events || [])].map(clean).filter(Boolean))).slice(-512);
        base.updated_at = delta.updated_at || base.updated_at || "";
        return base;
      };

      const ensureQuestionInventoryHud = () => {
        if (questionInventoryHud && questionInventoryHud.isConnected) {
          return questionInventoryHud;
        }
        questionInventoryHud = document.createElement("aside");
        questionInventoryHud.className = "ft-crystal-inventory";
        questionInventoryHud.setAttribute("aria-live", "polite");
        questionInventoryHud.innerHTML = `
          <span class="ft-crystal-inventory-flare" aria-hidden="true"></span>
          <span class="ft-crystal-inventory-rays" aria-hidden="true"></span>
          <span class="ft-crystal-inventory-stage" aria-hidden="true">
            <span class="ft-crystal-inventory-halo"></span>
            <span class="ft-crystal-inventory-gem"></span>
            <span class="ft-crystal-inventory-sparks">
              <i></i><i></i><i></i><i></i><i></i><i></i>
            </span>
          </span>
          <span class="ft-crystal-inventory-count" data-crystal-count>0</span>
          <span class="ft-crystal-inventory-body">
            <span class="ft-crystal-inventory-tier" data-crystal-tier>Prism tier</span>
            <span class="ft-crystal-inventory-kicker">Reward obtained</span>
            <span class="ft-crystal-inventory-name" data-crystal-name>Prism Crystal</span>
            <span class="ft-crystal-inventory-use" data-crystal-use>Stores learning energy for future item upgrades.</span>
          </span>
        `;
        document.body.appendChild(questionInventoryHud);
        return questionInventoryHud;
      };

      function questionInventoryCrystalSummary() {
        const crystalConfig = questionRewardConfig && questionRewardConfig.crystal ? questionRewardConfig.crystal : normalizeQuestionRewards({}).crystal;
        const state = questionInventoryState || readLocalQuestionInventory();
        const configuredId = clean(crystalConfig.id || "crystal").toLowerCase() || "crystal";
        const crystal = (state.items && (state.items[configuredId] || state.items.crystal)) || {};
        return {
          id: clean(crystal.id || configuredId || "crystal").toLowerCase() || "crystal",
          name: clean(crystal.name || crystalConfig.name || "Prism Crystal"),
          use: preserveQuestionText(crystal.use || crystalConfig.use || "Stores learning energy for future item upgrades."),
          quantity: Math.max(0, Math.floor(Number(crystal.quantity || 0) || 0)),
        };
      }

      const inventoryCrystalToneForId = (id = "") => {
        const key = clean(id).toLowerCase();
        if (key === "space_q_spellbook_gold" || key === "leaderboard_space_q_crystal") return "bookgold";
        if (key === "space_q_spellbook_silver") return "booksilver";
        if (key === "space_p_bow_gold" || key === "paragraph_crystal_golden") return "bowgold";
        if (key === "space_p_bow_silver") return "bowsilver";
        if (key === "space_s_sax_gold") return "saxgold";
        if (key === "space_s_sax_silver") return "saxsilver";
        if (key === "space_l_sword_gold") return "swordgold";
        if (key === "space_l_sword_silver") return "swordsilver";
        if (key.includes("cup_gold") || key.includes("cupgold")) return "cupgold";
        if (key.includes("cup_iron") || key.includes("cupiron")) return "cupiron";
        if (key === "vocab_crystal_blue" || key === "vocab_crystal_green") return "easy";
        if (key === "vocab_crystal_yellow" || key === "leaderboard_space_v_crystal" || key === "leaderboard_crystal_rare" || key === "crystal" || key.includes("space_v") || key.includes("spacev")) return "spacev";
        if (key === "leaderboard_crystal_easy") return "easy";
        if (key.includes("gold")) return "golden";
        if (key.includes("yellow")) return "yellow";
        if (key.includes("blue")) return "blue";
        if (key.includes("green")) return "green";
        if (key.includes("badge")) return "badge";
        if (key.includes("rare")) return "rare";
        if (key.includes("easy") || key.includes("review")) return "easy";
        if (key.includes("space_q") || key.includes("spaceq")) return "spaceq";
        if (key.includes("space_w") || key.includes("spacew")) return "spacew";
        if (key.includes("space_v") || key.includes("spacev")) return "spacev";
        return "prism";
      };

      const inventoryItemsForDisplay = () => {
        const state = questionInventoryState || readLocalQuestionInventory();
        const items = Object.values((state && state.items) || {})
          .map((item) => ({
            id: clean(item.id || "crystal").toLowerCase() || "crystal",
            name: canonicalRewardName(item.id, item.name),
            use: canonicalRewardUse(item.id, item.use),
            quantity: Math.max(0, Math.floor(Number(item.quantity || 0) || 0)),
          }))
          .filter((item) => item.quantity > 0);
        if (!items.length) {
          items.push(questionInventoryCrystalSummary());
        }
        return mergeRewardDisplayItems(items).sort((a, b) => {
          const order = ["space_q_spellbook_gold", "leaderboard_space_q_crystal", "space_q_spellbook_silver", "space_p_bow_gold", "paragraph_crystal_golden", "space_p_bow_silver", "space_s_sax_gold", "space_s_sax_silver", "space_l_sword_gold", "space_l_sword_silver", "space_w_cup_gold", "space_w_cup_iron", "leaderboard_space_v_crystal", "leaderboard_crystal_rare", "leaderboard_crystal_easy", "vocab_crystal_yellow", "vocab_crystal_blue", "vocab_crystal_green", "crystal"];
          return (order.indexOf(a.id) < 0 ? 99 : order.indexOf(a.id)) - (order.indexOf(b.id) < 0 ? 99 : order.indexOf(b.id));
        });
      };

      function resetCurrentMissionCrystalAwards() {
        currentMissionCrystalAwards = {};
      }

      function recordCurrentMissionCrystalAward(item = null) {
        if (!item || typeof item !== "object") {
          return;
        }
        const id = clean(item.id || "crystal").toLowerCase() || "crystal";
        const current = currentMissionCrystalAwards[id] || {
          id,
          name: canonicalRewardName(id, item.name),
          use: canonicalRewardUse(id, item.use),
          quantity: 0,
        };
        currentMissionCrystalAwards[id] = {
          ...current,
          id,
          name: canonicalRewardName(id, item.name || current.name),
          use: canonicalRewardUse(id, item.use || current.use),
          quantity: Math.max(0, Math.floor(Number(current.quantity || 0) || 0)) + 1,
        };
      }

      function currentMissionCrystalItemsForDisplay() {
        const merged = mergeRewardDisplayItems(
          Object.values(currentMissionCrystalAwards || {}).map((item) => ({
            id: clean(item && item.id || "crystal").toLowerCase() || "crystal",
            name: canonicalRewardName(item && item.id, item && item.name),
            use: canonicalRewardUse(item && item.id, item && item.use),
            quantity: Math.max(0, Math.floor(Number(item && item.quantity || 0) || 0)),
          }))
        );
        return merged
          .filter((item) => item.quantity > 0)
          .sort((a, b) => {
            const order = ["space_q_spellbook_gold", "leaderboard_space_q_crystal", "space_q_spellbook_silver", "space_p_bow_gold", "paragraph_crystal_golden", "space_p_bow_silver", "space_s_sax_gold", "space_s_sax_silver", "space_l_sword_gold", "space_l_sword_silver", "space_w_cup_gold", "space_w_cup_iron", "leaderboard_space_v_crystal", "leaderboard_crystal_rare", "leaderboard_crystal_easy", "vocab_crystal_yellow", "vocab_crystal_blue", "vocab_crystal_green", "crystal"];
            return (order.indexOf(a.id) < 0 ? 99 : order.indexOf(a.id)) - (order.indexOf(b.id) < 0 ? 99 : order.indexOf(b.id));
          });
      }

      function renderQuestionInventoryInfo(item = null) {
        if (!inventoryInfo) {
          return;
        }
        const data = item || questionInventoryCrystalSummary();
        inventoryInfo.innerHTML = "";
        const kicker = document.createElement("span");
        kicker.className = "ft-inventory-info-kicker";
        kicker.textContent = "Inventory item";
        const name = document.createElement("span");
        name.className = "ft-inventory-info-name";
        name.textContent = canonicalRewardName(data && data.id, data && data.name);
        const use = document.createElement("span");
        use.className = "ft-inventory-info-use";
        use.textContent = preserveQuestionText(data.use) || "Stores learning energy for future item upgrades.";
        const count = document.createElement("span");
        count.className = "ft-inventory-info-count";
        count.textContent = `Owned x${Math.max(0, Math.floor(Number(data.quantity || 0) || 0))}`;
        inventoryInfo.append(kicker, name, use, count);
      }

      function renderQuestionInventoryPopup() {
        if (!inventoryGrid) {
          return;
        }
        const items = inventoryItemsForDisplay();
        const slots = 24;
        inventoryGrid.innerHTML = "";
        for (let index = 0; index < slots; index += 1) {
          const item = items[index] || null;
          const slot = document.createElement(item ? "button" : "span");
          if (item) {
            slot.type = "button";
          }
          slot.className = "ft-inventory-slot";
          if (item) {
            const tone = inventoryCrystalToneForId(item.id);
            slot.setAttribute("aria-label", `${item.name}, owned ${item.quantity}`);
            slot.classList.add("has-item");
            slot.innerHTML = `
              <span class="ft-inventory-gem ${tone ? `is-${tone}` : ""}" aria-hidden="true"></span>
              <span class="ft-inventory-slot-count">x${item.quantity}</span>
            `;
            const showItem = () => renderQuestionInventoryInfo(item);
            slot.addEventListener("mouseenter", showItem);
            slot.addEventListener("focus", showItem);
          } else {
            slot.setAttribute("aria-hidden", "true");
          }
          inventoryGrid.appendChild(slot);
        }
        renderQuestionInventoryInfo(items[0] || questionInventoryCrystalSummary());
      }

      function renderCompletionCrystalSummary() {
        if (!completeCrystalGrid) {
          return;
        }
        const items = currentMissionCrystalItemsForDisplay();
        const total = items.reduce((sum, item) => sum + Math.max(0, Math.floor(Number(item.quantity || 0) || 0)), 0);
        if (completeCrystalTotalNode) {
          completeCrystalTotalNode.textContent = total.toLocaleString("en-US");
        }
        completeCrystalGrid.innerHTML = "";
        if (!items.length) {
          const empty = document.createElement("div");
          empty.className = "ft-complete-crystal-empty";
          empty.textContent = "No crystals earned in this file run.";
          completeCrystalGrid.appendChild(empty);
          return;
        }
        items.slice(0, 8).forEach((item, index) => {
          const card = document.createElement("article");
          card.className = "ft-complete-crystal-item";
          card.style.setProperty("--crystal-index", String(index));
          const tone = inventoryCrystalToneForId(item.id);
          const gem = document.createElement("span");
          gem.className = `ft-inventory-gem ft-complete-crystal-gem ${tone ? `is-${tone}` : ""}`;
          gem.setAttribute("aria-hidden", "true");
          const body = document.createElement("span");
          const name = document.createElement("span");
          name.className = "ft-complete-crystal-name";
          name.textContent = canonicalRewardName(item && item.id, item && item.name);
          const count = document.createElement("span");
          count.className = "ft-complete-crystal-count";
          count.textContent = `x${Math.max(0, Math.floor(Number(item.quantity || 0) || 0)).toLocaleString("en-US")}`;
          body.append(name, count);
          card.append(gem, body);
          completeCrystalGrid.appendChild(card);
        });
      }

      function openQuestionInventoryPopup() {
        if (!inventoryModal) {
          return;
        }
        questionInventoryState = readLocalQuestionInventory();
        renderQuestionInventoryPopup();
        inventoryModal.classList.add("is-open");
        inventoryModal.setAttribute("aria-hidden", "false");
        if (userMenu) {
          userMenu.classList.remove("is-open");
        }
        if (userButton) {
          userButton.setAttribute("aria-expanded", "false");
        }
        if (authToken) {
          void loadQuestionInventory();
        }
      }

      function closeQuestionInventoryPopup() {
        if (!inventoryModal) {
          return;
        }
        inventoryModal.classList.remove("is-open");
        inventoryModal.setAttribute("aria-hidden", "true");
      }

      const formatCupWords = (value) => {
        const total = Math.max(0, Math.floor(Number(value || 0) || 0));
        return total.toLocaleString("en-US");
      };

      const normalizeCupType = (value = "space_v") => {
        const safe = clean(value).toLowerCase().replace(/[-\s]+/g, "_");
        if (["space_v", "space_w", "space_q", "space_p", "space_s", "space_l"].includes(safe)) return safe;
        if (safe === "v" || safe === "spacev") return "space_v";
        if (safe === "w" || safe === "spacew") return "space_w";
        if (safe === "q" || safe === "spaceq") return "space_q";
        if (safe === "p" || safe === "spacep") return "space_p";
        if (safe === "s" || safe === "spaces") return "space_s";
        if (safe === "l" || safe === "spacel") return "space_l";
        return "space_v";
      };

      const cupTypeConfig = (type = currentCupType) => ({
        space_v: {
          label: "Vocabulary",
          title: "Top Vocabulary",
          empty: "completed vocabulary activity",
          subtitle: "Ranked by completed vocabulary growth.",
        },
        space_w: {
          label: "Four-Skill Writing",
          title: "Top Four-Skill Writing",
          empty: "completed four-skill writing activity",
          subtitle: "Ranked by total nodes in completed four-skill writing files.",
        },
        space_q: {
          label: "English Q&A",
          title: "Top English Q&A",
          empty: "completed English Q&A activity",
          subtitle: "Ranked by completed question nodes, including child and nested nodes.",
        },
        space_p: {
          label: "Paragraph Writing",
          title: "Top Paragraph Writing",
          empty: "completed paragraph writing activity",
          subtitle: "Ranked by total nodes in completed paragraph writing files.",
        },
        space_s: {
          label: "Paragraph Speaking",
          title: "Top Paragraph Speaking",
          empty: "completed paragraph speaking activity",
          subtitle: "Ranked by total nodes in completed paragraph speaking files.",
        },
        space_l: {
          label: "Paragraph Listening",
          title: "Top Paragraph Listening",
          empty: "completed paragraph listening activity",
          subtitle: "Ranked by total nodes in completed paragraph listening files.",
        },
      }[normalizeCupType(type)] || {
        label: "Vocabulary",
        title: "Top Vocabulary",
        empty: "completed activity",
        subtitle: "Ranked by completed progress.",
      });

      const cupTypeLabel = (type = currentCupType) => cupTypeConfig(type).label;
      const cupTypeTitle = (type = currentCupType) => cupTypeConfig(type).title;
      const cupTypeIconClass = (type = currentCupType) => `ft-cup-type-icon is-${normalizeCupType(type).replace("_", "-")}`;

      const clampNumber = (value, min, max) => Math.min(Math.max(value, min), max);

      const ensureCupTypeMenuLayer = () => {
        if (!cupTypeMenu || !document.body || cupTypeMenu.parentElement === document.body) return;
        document.body.appendChild(cupTypeMenu);
      };

      const updateCupTypeMenuPlacement = () => {
        if (!cupTypeMenu || !cupTypeButton || !cupTypeMenu.classList.contains("is-open")) return;
        ensureCupTypeMenuLayer();
        const gap = 8;
        const margin = 12;
        const viewportWidth = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
        const viewportHeight = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
        const buttonRect = cupTypeButton.getBoundingClientRect();
        const menuWidth = Math.min(392, Math.max(260, viewportWidth - (margin * 2)));
        const spaceBelow = viewportHeight - buttonRect.bottom - margin;
        const spaceAbove = buttonRect.top - margin;
        const placeAbove = spaceBelow < 250 && spaceAbove > spaceBelow;
        const availableHeight = Math.max(180, (placeAbove ? spaceAbove : spaceBelow) - gap);
        const menuHeight = Math.min(466, availableHeight);
        const left = clampNumber(buttonRect.right - menuWidth, margin, viewportWidth - menuWidth - margin);
        const top = placeAbove
          ? clampNumber(buttonRect.top - gap - menuHeight, margin, viewportHeight - menuHeight - margin)
          : clampNumber(buttonRect.bottom + gap, margin, viewportHeight - menuHeight - margin);
        cupTypeMenu.classList.toggle("is-above", placeAbove);
        cupTypeMenu.style.width = `${menuWidth}px`;
        cupTypeMenu.style.maxHeight = `${menuHeight}px`;
        cupTypeMenu.style.left = `${left}px`;
        cupTypeMenu.style.top = `${top}px`;
      };

      const setCupTypeMenuOpen = (open = false) => {
        if (!cupTypePicker || !cupTypeButton) return;
        const nextOpen = Boolean(open);
        if (nextOpen) {
          ensureCupTypeMenuLayer();
        }
        cupTypePicker.classList.toggle("is-open", nextOpen);
        if (cupTypeMenu) {
          cupTypeMenu.classList.toggle("is-open", nextOpen);
          cupTypeMenu.setAttribute("aria-hidden", nextOpen ? "false" : "true");
          if (!nextOpen) {
            cupTypeMenu.classList.remove("is-above");
          }
        }
        cupTypeButton.setAttribute("aria-expanded", open ? "true" : "false");
        if (nextOpen) {
          updateCupTypeMenuPlacement();
        }
      };

      const updateCupTypePicker = () => {
        const safeType = normalizeCupType(currentCupType);
        const config = cupTypeConfig(safeType);
        if (cupTypeSelect) {
          cupTypeSelect.value = safeType;
        }
        if (cupTypeCurrentLabel) {
          cupTypeCurrentLabel.textContent = config.label;
        }
        if (cupTypeButton) {
          const icon = cupTypeButton.querySelector(".ft-cup-type-icon");
          if (icon) icon.className = cupTypeIconClass(safeType);
        }
        cupTypeOptions.forEach((option) => {
          const active = normalizeCupType(option.dataset.cupType || "") === safeType;
          option.classList.toggle("is-selected", active);
          option.setAttribute("aria-selected", active ? "true" : "false");
        });
      };

      const selectCupType = (type = "space_v", reload = true) => {
        const nextType = normalizeCupType(type);
        if (nextType === currentCupType && reload) {
          setCupTypeMenuOpen(false);
          updateCupTypePicker();
          return;
        }
        currentCupType = nextType;
        cupPendingCompletion = null;
        cupLeaderboardCache = { at: 0, type: currentCupType, boards: {}, users: [], viewers: cupLeaderboardCache.viewers || [], myStatuses: cupLeaderboardCache.myStatuses || {}, chat: cupLeaderboardCache.chat || [], reactionOptions: cupLeaderboardCache.reactionOptions || [] };
        setCupTypeMenuOpen(false);
        closeCupViewerPopover();
        updateCupTypePicker();
        renderCupLeaderboard([], currentCupScope);
        if (reload) {
          void loadCupLeaderboard(true);
        }
      };

      const cupScoreUnit = (type = currentCupType) => normalizeCupType(type) === "space_v" ? "word" : "point";

      const cupWordLabel = (value, type = currentCupType) => {
        const total = Math.max(0, Math.floor(Number(value || 0) || 0));
        const unit = cupScoreUnit(type);
        return `${formatCupWords(total)} ${total === 1 ? unit : `${unit}s`}`;
      };

      const normalizeAvatarGender = (value = "") => {
        const gender = clean(value).toLowerCase();
        return ["male", "female", "other"].includes(gender) ? gender : "other";
      };

      const cupAvatarDefaultMarkup = () => `
        <svg class="ft-cup-avatar-default" viewBox="0 0 64 64" focusable="false" aria-hidden="true">
          <path class="avatar-hair" d="M17 31c0-11 6.4-19 15-19s15 8 15 19c0 9-3.3 17-15 17S17 40 17 31Z" fill="currentColor" opacity=".18"/>
          <path d="M18.5 50c2.5-8.8 8.1-13 13.5-13s11 4.2 13.5 13" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          <path d="M22 27c0-7.3 4.3-12.4 10-12.4S42 19.7 42 27s-4.3 12.4-10 12.4S22 34.3 22 27Z" fill="none" stroke="currentColor" stroke-width="4" stroke-linejoin="round"/>
          <path class="avatar-jaw" d="M22.5 25.5c5.7-2.7 13.3-2.7 19 0" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".62"/>
        </svg>`;

      const CUP_AVATAR_PRELOAD_CACHE = new Set();

      const preloadCupAvatarUrl = (avatarPath = "") => {
        const url = avatarPath ? resolveServerAssetUrl(clean(avatarPath)) : "";
        if (!url || CUP_AVATAR_PRELOAD_CACHE.has(url)) {
          return;
        }
        CUP_AVATAR_PRELOAD_CACHE.add(url);
        if (CUP_AVATAR_PRELOAD_CACHE.size > 180) {
          const first = CUP_AVATAR_PRELOAD_CACHE.values().next().value;
          if (first) {
            CUP_AVATAR_PRELOAD_CACHE.delete(first);
          }
        }
        const image = new Image();
        image.decoding = "async";
        image.src = url;
      };

      const preloadCupLeaderboardAssets = (boards = {}, viewers = [], chat = []) => {
        const rows = [];
        ["day", "total", "week", "month"].forEach((scope) => {
          const boardRows = boards && Array.isArray(boards[scope]) ? boards[scope] : [];
          rows.push(...boardRows.slice(0, scope === "day" ? 12 : 8));
        });
        if (Array.isArray(viewers)) {
          rows.push(...viewers.slice(0, 24));
        }
        if (Array.isArray(chat)) {
          rows.push(...chat.slice(-24));
        }
        rows.forEach((item) => {
          if (!item || typeof item !== "object") {
            return;
          }
          preloadCupAvatarUrl(item.avatar || item.avatarUrl || item.avatar_url || "");
        });
      };

      const CUP_LEADERBOARD_PREWARM_INFLIGHT = new Map();
      const CUP_LEADERBOARD_PENDING_REFRESH_TIMERS = new Map();
      const CUP_LEADERBOARD_HTTP_CACHE_SCHEMA_VERSION = 1;

      // Added 2026-07-29: a warm node-space Top may return the previous shared
      // snapshot while the bounded server batch is pending; revalidate once at
      // the server-provided deadline instead of polling every second per user.
      const scheduleCupLeaderboardPendingRefresh = (type = "space_v", scope = "day", retryMs = 0) => {
        const safeType = normalizeCupType(type);
        if (safeType === "space_v") return;
        const safeScope = ["total", "day", "week", "month"].includes(clean(scope)) ? clean(scope) : "day";
        const key = `${safeType}:${safeScope}`;
        const previous = CUP_LEADERBOARD_PENDING_REFRESH_TIMERS.get(key);
        if (previous) window.clearTimeout(previous);
        const timer = window.setTimeout(() => {
          CUP_LEADERBOARD_PENDING_REFRESH_TIMERS.delete(key);
          void prewarmCupLeaderboard({ type: safeType, scope: safeScope, force: true });
        }, Math.max(100, Math.min(2200, Number(retryMs) || 1080)));
        CUP_LEADERBOARD_PENDING_REFRESH_TIMERS.set(key, timer);
      };

      const normalizeCupLeaderboardPayload = (payload = {}, fallbackType = currentCupType) => {
        const boardType = normalizeCupType(payload.board_type || payload.type || fallbackType || currentCupType);
        const boards = payload.boards && typeof payload.boards === "object"
          ? payload.boards
          : { total: Array.isArray(payload.users) ? payload.users : [] };
        const normalizedBoards = {
          total: normalizeCupRows(boards.total || payload.users || [], "total"),
          day: normalizeCupRows(boards.day || [], "day"),
          week: normalizeCupRows(boards.week || [], "week"),
          month: normalizeCupRows(boards.month || [], "month"),
        };
        return {
          boardType,
          boards: normalizedBoards,
          users: normalizedBoards.total,
          viewers: normalizeCupViewers(payload.viewers || payload.leaderboard_viewers || []),
          myStatuses: payload.my_statuses && typeof payload.my_statuses === "object" ? payload.my_statuses : {},
          chat: normalizeCupChatRows(payload.world_chat || payload.chat || []),
          reactionOptions: normalizeCupReactionOptions(payload.reaction_options || payload.reactions || []),
          rewardConfig: normalizeCupRewardConfig(payload.rewards || payload.leaderboard_rewards || cupRewardConfig),
        };
      };

      // Added 2026-07-20: revalidate final leaderboard bytes instead of downloading the same large payload again.
      const fetchCupLeaderboardPayload = async (type = "space_v", scope = "day") => {
        const safeType = normalizeCupType(type);
        const safeScope = ["total", "day", "week", "month"].includes(clean(scope)) ? clean(scope) : "day";
        const candidate = cupLeaderboardHttpCache.get(safeType);
        const cached = candidate &&
          Number(candidate.schema_version || 0) === CUP_LEADERBOARD_HTTP_CACHE_SCHEMA_VERSION &&
          candidate.payload && typeof candidate.payload === "object"
          ? candidate
          : null;
        if (candidate && !cached) {
          cupLeaderboardHttpCache.delete(safeType);
        }
        const result = await fetchServerJson(
          `/vocab/leaderboard?limit=80&double_check=0&scope=${encodeURIComponent(safeScope)}&type=${encodeURIComponent(safeType)}`,
          {
            cache: "no-cache",
            ifNoneMatch: clean(cached && cached.etag),
            notModifiedPayload: cached && cached.payload && typeof cached.payload === "object" ? cached.payload : null,
          }
        );
        if (result && result.payload && typeof result.payload === "object") {
          cupLeaderboardHttpCache.set(safeType, {
            schema_version: CUP_LEADERBOARD_HTTP_CACHE_SCHEMA_VERSION,
            etag: clean(result.etag || (cached && cached.etag)),
            payload: result.payload,
          });
        }
        if (result && result.topPending) {
          scheduleCupLeaderboardPendingRefresh(safeType, safeScope, result.topRetryMs);
        }
        return result;
      };

      const prewarmCupLeaderboard = async (options = {}) => {
        const opts = options && typeof options === "object" ? options : {};
        const scope = ["total", "day", "week", "month"].includes(clean(opts.scope || "")) ? clean(opts.scope) : "day";
        const type = normalizeCupType(opts.type || opts.boardType || currentCupType);
        const force = Boolean(opts.force);
        const now = Date.now();
        const cacheType = normalizeCupType(cupLeaderboardCache.type || currentCupType);
        const cachedRows = cacheType === type && cupLeaderboardCache.boards && cupLeaderboardCache.boards[scope];
        if (!force && Array.isArray(cachedRows) && cachedRows.length && now - cupLeaderboardCache.at < 30000) {
          preloadCupLeaderboardAssets(cupLeaderboardCache.boards || {}, cupLeaderboardCache.viewers || [], cupLeaderboardCache.chat || []);
          return true;
        }
        const inflightKey = `${type}:${scope}:${force ? "force" : "warm"}`;
        if (CUP_LEADERBOARD_PREWARM_INFLIGHT.has(inflightKey)) {
          return CUP_LEADERBOARD_PREWARM_INFLIGHT.get(inflightKey);
        }
        const task = (async () => {
          try {
            const result = await fetchCupLeaderboardPayload(type, scope);
            const normalized = normalizeCupLeaderboardPayload(result.payload || {}, type);
            preloadCupLeaderboardAssets(normalized.boards, normalized.viewers, normalized.chat);
            cupLeaderboardCache = {
              at: Date.now(),
              type: normalized.boardType,
              boards: normalized.boards,
              users: normalized.users,
              viewers: normalized.viewers,
              myStatuses: normalized.myStatuses,
              chat: normalized.chat,
              reactionOptions: normalized.reactionOptions,
            };
            cupRewardConfig = normalized.rewardConfig;
            if ((normalized.boards[scope] || []).some((item) => clean(item && item.username).toLowerCase() === clean(cupPendingCompletion && cupPendingCompletion.username).toLowerCase())) {
              cupPendingCompletion = null;
            }
            if (
              cupModal &&
              cupModal.classList.contains("is-open") &&
              normalizeCupType(currentCupType) === normalized.boardType &&
              currentCupScope === scope
            ) {
              renderCupWorldChat(normalized.chat);
              renderCupLeaderboard(normalized.boards[scope] || [], scope, { softRefresh: true });
            }
            return true;
          } catch (_error) {
            return false;
          } finally {
            CUP_LEADERBOARD_PREWARM_INFLIGHT.delete(inflightKey);
          }
        })();
        CUP_LEADERBOARD_PREWARM_INFLIGHT.set(inflightKey, task);
        return task;
      };

      window.prewarmCupLeaderboard = prewarmCupLeaderboard;

      const makeCupAvatar = (item = {}, mode = "row") => {
        const avatar = document.createElement("span");
        avatar.className = `ft-cup-avatar is-${mode} is-${normalizeAvatarGender(item.gender || item.profileGender || item.profile_gender)}`;
        const avatarUsername = clean(item.username || item.user || "");
        avatar.setAttribute("aria-hidden", avatarUsername ? "false" : "true");
        if (avatarUsername) {
          avatar.classList.add("is-profile-clickable");
          avatar.dataset.profileUsername = avatarUsername;
          avatar.setAttribute("role", "button");
          avatar.setAttribute("tabindex", "0");
          avatar.title = `Open ${profileDisplayName(item)} profile`;
          avatar.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            void openPublicProfileCard(avatarUsername);
          });
          avatar.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              event.stopPropagation();
              void openPublicProfileCard(avatarUsername);
            }
          });
        }
        const img = document.createElement("img");
        img.alt = "";
        const avatarPath = clean(item.avatar || item.avatarUrl || item.avatar_url || "");
        const url = avatarPath ? resolveServerAssetUrl(avatarPath) : "";
        if (url) {
          avatar.classList.add("has-image");
          img.decoding = "async";
          img.loading = mode === "podium" ? "eager" : "lazy";
          img.src = url;
          img.addEventListener("error", () => {
            avatar.classList.remove("has-image");
            img.removeAttribute("src");
            if (!avatar.querySelector(".ft-cup-avatar-default")) {
              avatar.insertAdjacentHTML("beforeend", cupAvatarDefaultMarkup());
            }
          }, { once: true });
        }
        avatar.appendChild(img);
        if (!url) {
          avatar.insertAdjacentHTML("beforeend", cupAvatarDefaultMarkup());
        }
        return avatar;
      };

      const makeCupScore = (value, scope = "total") => {
        const score = document.createElement("div");
        score.className = "ft-cup-row-score";
        score.append(document.createTextNode(formatCupWords(value)));
        const unit = document.createElement("small");
        unit.textContent = ` ${cupScoreUnit()}s`;
        score.append(unit);
        return score;
      };

      const cupScopeLabel = (scope = "total") => {
        if (scope === "day") return "Today";
        if (scope === "week") return "This week";
        if (scope === "month") return "This month";
        return "Total";
      };

      const cupTopTenTitle = (scope = "total") => {
        const label = cupTypeTitle().replace(/^Top\s+/i, "");
        if (scope === "day") return `Top 10 ${label} Today`;
        if (scope === "week") return `Top 10 ${label} This Week`;
        if (scope === "month") return `Top 10 ${label} This Month`;
        return `Top 10 ${label} Overall`;
      };

      const cupTopTenSubtitle = (scope = "total") => {
        if (currentCupType === "space_v") {
          if (scope === "day") return "Daily ranking counts unique vocabulary practiced today.";
          if (scope === "week") return "Weekly ranking counts unique vocabulary practiced this week.";
          if (scope === "month") return "Monthly ranking counts unique vocabulary practiced this month.";
          return "All-time ranking follows total completed vocabulary growth.";
        }
        const base = cupTypeConfig().subtitle;
        if (scope === "day") return `${base} Today's completed files only.`;
        if (scope === "week") return `${base} Completed files from this week only.`;
        if (scope === "month") return `${base} Completed files from this month only.`;
        return `${base} Lifetime completed progress.`;
      };

      const makeCupListHeading = (scope = currentCupScope) => {
        const head = document.createElement("div");
        head.className = "ft-cup-list-heading";
        const title = document.createElement("div");
        title.className = "ft-cup-list-title";
        title.textContent = cupTopTenTitle(scope);
        const subtitle = document.createElement("div");
        subtitle.className = "ft-cup-list-subtitle";
        subtitle.textContent = cupTopTenSubtitle(scope);
        head.append(title, subtitle);
        return head;
      };

      const cupRankMotionClass = (item = {}) => {
        const direction = clean(item && item.rankMove && item.rankMove.direction);
        const delta = Math.max(0, Math.floor(Number(item && item.rankMove && item.rankMove.delta || 0) || 0));
        if (direction === "up" && delta > 0) return "is-rank-up";
        if (direction === "down" && delta > 0) return "is-rank-down";
        if (direction === "new") return "is-rank-new";
        return "";
      };

      const cupScoreForScope = (item, scope = "total") => {
        if (!item || typeof item !== "object") return 0;
        if (item.score !== undefined) return Math.max(0, Math.floor(Number(item.score) || 0));
        if (item.scoreWords !== undefined) return Math.max(0, Math.floor(Number(item.scoreWords) || 0));
        if (scope === "day") return Math.max(0, Math.floor(Number(item.today_words ?? item.todayWords ?? 0) || 0));
        if (scope === "week") return Math.max(0, Math.floor(Number(item.week_words ?? item.weekWords ?? 0) || 0));
        if (scope === "month") return Math.max(0, Math.floor(Number(item.month_words ?? item.monthWords ?? 0) || 0));
        return Math.max(0, Math.floor(Number(item.total_words ?? item.totalWords ?? item.words) || 0));
      };

      const normalizeCupRows = (rows, scope = "total") => (Array.isArray(rows) ? rows : [])
        .map((item, index) => {
          const rankMove = item && typeof item.rank_move === "object" ? item.rank_move : item && typeof item.rankMove === "object" ? item.rankMove : {};
          const placeholder = Boolean(item && (item.placeholder || item.is_placeholder || item.fallback || item.preview));
          const direction = placeholder && !clean(rankMove.direction || "") ? "preview" : clean(rankMove.direction || "");
          return {
            rank: Math.max(1, Math.floor(Number(item && item.rank) || index + 1)),
            username: clean(item && item.username),
            displayName: clean((item && (item.display_name || item.displayName || item.full_name)) || (item && item.username) || "Learner"),
            gender: normalizeAvatarGender(item && (item.gender || item.profile_gender || item.profileGender)),
            avatar: clean(item && (item.avatar || item.avatar_url || item.avatarUrl || "")),
            placeholder,
            totalWords: Math.max(0, Math.floor(Number(item && (item.total_words ?? item.totalWords ?? item.words)) || 0)),
            scoreWords: cupScoreForScope(item, scope),
            pending: Boolean(item && item.pending),
            todayWords: Math.max(0, Math.floor(Number(item && (item.today_words ?? item.todayWords ?? 0)) || 0)),
            weekWords: Math.max(0, Math.floor(Number(item && (item.week_words ?? item.weekWords ?? 0)) || 0)),
            monthWords: Math.max(0, Math.floor(Number(item && (item.month_words ?? item.monthWords ?? 0)) || 0)),
            rankMove: {
              direction,
              delta: Math.max(0, Math.floor(Number(rankMove.delta || 0) || 0)),
              previousRank: Math.max(0, Math.floor(Number(rankMove.previous_rank ?? rankMove.previousRank ?? 0) || 0)),
              currentRank: Math.max(0, Math.floor(Number(rankMove.current_rank ?? rankMove.currentRank ?? 0) || 0)),
            },
            updatedAt: clean(item && (item.updated_at || item.updatedAt)),
            social: item && typeof item.social === "object" ? {
              status: clean(item.social.status || ""),
              statusUpdatedAt: clean(item.social.status_updated_at || item.social.statusUpdatedAt || ""),
              reactions: item.social.reactions && typeof item.social.reactions === "object" ? item.social.reactions : {},
              myReactions: Array.isArray(item.social.my_reactions)
                ? item.social.my_reactions.map(clean).filter(Boolean)
                : (clean(item.social.my_reaction || item.social.myReaction) ? [clean(item.social.my_reaction || item.social.myReaction)] : []),
            } : { status: "", statusUpdatedAt: "", reactions: {}, myReactions: [] },
          };
        })
        .filter((item) => item.username && item.username.toLowerCase() !== "testuser" && (item.scoreWords > 0 || item.placeholder))
        .sort((a, b) => (a.rank - b.rank) || (b.scoreWords - a.scoreWords))
        .slice(0, 500);

      // Added 2026-07-29: keep the committed learner visible before the
      // server's coalesced board snapshot publishes its official rank.
      const mergePendingCupRow = (rows, scope = currentCupScope) => {
        const normalized = Array.isArray(rows) ? rows.slice() : [];
        const pending = cupPendingCompletion && typeof cupPendingCompletion === "object" ? cupPendingCompletion : null;
        const username = clean(pending && pending.username).toLowerCase();
        if (!pending || !username || username !== clean(currentAuthUsername).toLowerCase()) return normalized;
        if (normalized.some((item) => clean(item && item.username).toLowerCase() === username)) return normalized;
        const scoreKey = scope === "day" ? "today_words" : scope === "week" ? "week_words" : scope === "month" ? "month_words" : "total_words";
        const score = Math.max(0, Math.floor(Number(pending[scoreKey] || 0) || 0));
        if (score <= 0) return normalized;
        const rank = 1 + normalized.filter((item) => Number(item && item.scoreWords || 0) > score).length;
        const pendingRow = normalizeCupRows([{
          ...pending,
          rank,
          score,
          scoreWords: score,
          rank_move: { direction: "new", delta: 0 },
        }], scope)[0];
        if (pendingRow) normalized.push(pendingRow);
        return normalized.sort((a, b) => (a.rank - b.rank) || (b.scoreWords - a.scoreWords));
      };

      const normalizeCupViewers = (rows) => (Array.isArray(rows) ? rows : [])
        .map((item) => ({
          username: clean(item && item.username),
          displayName: clean((item && (item.display_name || item.displayName || item.full_name)) || (item && item.username) || "Learner"),
          gender: normalizeAvatarGender(item && (item.gender || item.profile_gender || item.profileGender)),
          avatar: clean(item && (item.avatar || item.avatar_url || item.avatarUrl || "")),
          viewedAt: clean(item && (item.viewed_at || item.viewedAt || "")),
          lastScope: clean(item && (item.last_scope || item.lastScope || "")) || "total",
          views: Math.max(0, Math.floor(Number(item && item.views) || 0)),
        }))
        .filter((item) => item.username && item.username.toLowerCase() !== "testuser");

      const closeCupViewerPopover = () => {
        if (!cupViewerPopover) {
          return;
        }
        cupViewerPopover.classList.remove("is-open");
        cupViewerPopover.setAttribute("aria-hidden", "true");
      };

      const formatCupViewerTime = (value = "") => {
        const raw = clean(value);
        if (!raw) return "recently";
        const parsed = Date.parse(raw.replace(" ", "T"));
        if (!Number.isFinite(parsed)) return raw;
        const diffMs = Date.now() - parsed;
        const diffMin = Math.max(0, Math.floor(diffMs / 60000));
        if (diffMin < 1) return "just now";
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffHour = Math.floor(diffMin / 60);
        if (diffHour < 24) return `${diffHour}h ago`;
        const diffDay = Math.floor(diffHour / 24);
        return `${diffDay}d ago`;
      };

      const renderCupViewerPopover = (viewers = cupLeaderboardCache.viewers || []) => {
        if (!cupViewerList) {
          return;
        }
        const normalized = normalizeCupViewers(viewers);
        cupViewerList.innerHTML = "";
        if (!normalized.length) {
          const empty = document.createElement("div");
          empty.className = "ft-cup-empty";
          empty.textContent = "No viewer has opened this board yet.";
          cupViewerList.appendChild(empty);
          return;
        }
        normalized.forEach((item) => {
          const row = document.createElement("article");
          row.className = "ft-cup-viewer-row";
          const meta = document.createElement("div");
          const name = document.createElement("div");
          name.className = "ft-cup-viewer-name";
          name.textContent = item.displayName;
          const user = document.createElement("div");
          user.className = "ft-cup-viewer-user";
          user.textContent = `@${item.username}`;
          meta.append(name, user);
          const time = document.createElement("span");
          time.className = "ft-cup-viewer-time";
          time.textContent = formatCupViewerTime(item.viewedAt);
          row.append(makeCupAvatar(item, "viewer"), meta, time);
          cupViewerList.appendChild(row);
        });
      };

      const openCupViewerPopover = (viewers = cupLeaderboardCache.viewers || []) => {
        if (!cupViewerPopover) {
          return;
        }
        renderCupViewerPopover(viewers);
        cupViewerPopover.classList.add("is-open");
        cupViewerPopover.setAttribute("aria-hidden", "false");
      };

      const renderCupViewers = (viewers = cupLeaderboardCache.viewers || []) => {
        if (!cupViewers) {
          return;
        }
        const normalized = normalizeCupViewers(viewers);
        cupViewers.innerHTML = "";
        cupViewers.classList.toggle("is-visible", Boolean(normalized.length));
        if (!normalized.length) {
          closeCupViewerPopover();
          return;
        }
        const label = document.createElement("span");
        label.className = "ft-cup-viewers-label";
        label.textContent = "Viewed top";
        const stack = document.createElement("div");
        stack.className = "ft-cup-viewer-stack";
        normalized.slice(0, 5).forEach((item) => {
          const avatar = makeCupAvatar(item, "viewer");
          avatar.title = `${item.displayName} @${item.username}`;
          stack.appendChild(avatar);
        });
        if (normalized.length > 5) {
          const more = document.createElement("button");
          more.className = "ft-cup-viewer-more";
          more.type = "button";
          more.textContent = `+${normalized.length - 5}`;
          more.addEventListener("click", (event) => {
            event.stopPropagation();
            openCupViewerPopover(normalized);
          });
          stack.appendChild(more);
        } else {
          stack.addEventListener("click", (event) => {
            event.stopPropagation();
            openCupViewerPopover(normalized);
          });
        }
        cupViewers.append(label, stack);
      };

      const formatCupChatTime = (value = "") => {
        const text = clean(value);
        if (!text) {
          return "";
        }
        const parsed = new Date(text.replace(" ", "T"));
        if (Number.isNaN(parsed.getTime())) {
          return text.slice(11, 16) || text;
        }
        return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      };

      const normalizeCupChatRows = (items = []) => Array.isArray(items)
        ? items.map((item) => {
          const source = item && typeof item === "object" ? item : {};
          return {
            id: clean(source.id || ""),
            username: clean(source.username || ""),
            displayName: clean(source.display_name || source.displayName || source.username || "Learner"),
            avatar: clean(source.avatar || ""),
            message: clean(source.message || ""),
            createdAt: clean(source.created_at || source.createdAt || ""),
          };
        }).filter((item) => item.message).slice(-100)
        : [];

      let cupWorldChatPollTimer = 0;
      let cupWorldChatPollInFlight = false;
      let cupWorldChatPollStopped = true;
      let cupWorldChatRevision = 0;
      let cupWorldChatPollOpenedCount = 0;
      let cupWorldChatPollClosedCount = 0;
      let cupWorldChatPollScheduleCount = 0;
      let cupWorldChatPollSkipCount = 0;
      const CUP_WORLD_CHAT_POLL_MS = 1000;

      const syncCupWorldChatDebug = () => {
        if (!window) {
          return;
        }
        window.__futureWorldChatDebug = {
          openCount: cupWorldChatPollOpenedCount,
          closeCount: cupWorldChatPollClosedCount,
          scheduleCount: cupWorldChatPollScheduleCount,
          skipCount: cupWorldChatPollSkipCount,
          stopped: cupWorldChatPollStopped,
          inFlight: cupWorldChatPollInFlight,
          timerActive: Boolean(cupWorldChatPollTimer),
          revision: cupWorldChatRevision,
          open: Boolean(cupModal && cupModal.classList && cupModal.classList.contains("is-open")),
        };
      };

      const cupChatMessageId = (item = {}) => Math.max(0, Math.floor(Number(item && item.id || 0) || 0));

      const mergeCupChatRows = (existing = [], incoming = [], reset = false) => {
        const source = reset ? [] : normalizeCupChatRows(existing);
        const byId = new Map();
        source.forEach((item) => {
          const id = cupChatMessageId(item);
          if (id) byId.set(id, item);
        });
        normalizeCupChatRows(incoming).forEach((item) => {
          const id = cupChatMessageId(item);
          if (id) byId.set(id, item);
        });
        return [...byId.values()].sort((a, b) => cupChatMessageId(a) - cupChatMessageId(b)).slice(-100);
      };

      const updateCupWorldChatSnapshot = (messages = [], reset = false, revision = 0) => {
        const merged = mergeCupChatRows(cupLeaderboardCache.chat || [], messages, reset);
        cupLeaderboardCache.chat = merged;
        cupWorldChatRevision = Math.max(
          Number(revision || 0) || 0,
          ...merged.map((item) => cupChatMessageId(item))
        );
        renderCupWorldChat(merged);
      };

      const loadCupWorldChat = async () => {
        try {
          const result = await fetchServerJson("/vocab/leaderboard/chat?limit=100");
          const payload = result && result.payload ? result.payload : {};
          updateCupWorldChatSnapshot(payload.messages || [], true, payload.revision);
        } catch (error) {
          if (cupStatus) {
            cupStatus.textContent = error && error.message ? error.message : "Could not load World Chat.";
          }
        }
      };

      const stopCupWorldChatPolling = () => {
        cupWorldChatPollStopped = true;
        if (cupWorldChatPollTimer) {
          window.clearTimeout(cupWorldChatPollTimer);
          cupWorldChatPollTimer = 0;
        }
        cupWorldChatPollClosedCount += 1;
        syncCupWorldChatDebug();
      };

      const scheduleCupWorldChatPolling = (delay = CUP_WORLD_CHAT_POLL_MS) => {
        if (cupWorldChatPollStopped || !cupModal || !cupModal.classList.contains("is-open") || document.hidden) {
          cupWorldChatPollSkipCount += 1;
          syncCupWorldChatDebug();
          return;
        }
        if (cupWorldChatPollTimer) {
          cupWorldChatPollSkipCount += 1;
          syncCupWorldChatDebug();
          return;
        }
        cupWorldChatPollScheduleCount += 1;
        syncCupWorldChatDebug();
        cupWorldChatPollTimer = window.setTimeout(async () => {
          cupWorldChatPollTimer = 0;
          if (cupWorldChatPollStopped || !cupModal || !cupModal.classList.contains("is-open") || document.hidden) {
            syncCupWorldChatDebug();
            return;
          }
          if (cupWorldChatPollInFlight) {
            scheduleCupWorldChatPolling(CUP_WORLD_CHAT_POLL_MS);
            return;
          }
          cupWorldChatPollInFlight = true;
          try {
            const result = await fetchServerJson(`/vocab/leaderboard/chat?limit=100&after_id=${encodeURIComponent(String(cupWorldChatRevision || 0))}`);
            const payload = (result && result.payload) || {};
            if (payload.changed || payload.reset) {
              updateCupWorldChatSnapshot(payload.messages || [], Boolean(payload.reset), payload.revision);
            } else if (payload.revision !== undefined) {
              cupWorldChatRevision = Math.max(cupWorldChatRevision || 0, Number(payload.revision || 0) || 0);
            }
          } catch (_error) {
            // Keep the last verified snapshot; the next visible poll retries.
          } finally {
            cupWorldChatPollInFlight = false;
            syncCupWorldChatDebug();
            scheduleCupWorldChatPolling(CUP_WORLD_CHAT_POLL_MS);
          }
        }, Math.max(CUP_WORLD_CHAT_POLL_MS, Math.floor(Number(delay || CUP_WORLD_CHAT_POLL_MS) || CUP_WORLD_CHAT_POLL_MS)));
      };

      const startCupWorldChatPolling = () => {
        stopCupWorldChatPolling();
        cupWorldChatPollStopped = false;
        cupWorldChatPollOpenedCount += 1;
        syncCupWorldChatDebug();
        void loadCupWorldChat().finally(() => scheduleCupWorldChatPolling(CUP_WORLD_CHAT_POLL_MS));
      };

      const renderCupWorldChat = (messages = cupLeaderboardCache.chat || []) => {
        if (!cupWorldChatLog) {
          return;
        }
        const rows = normalizeCupChatRows(messages);
        const nearBottom = cupWorldChatLog.scrollHeight - cupWorldChatLog.scrollTop - cupWorldChatLog.clientHeight < 64;
        cupWorldChatLog.innerHTML = "";
        if (!rows.length) {
          const empty = document.createElement("div");
          empty.className = "ft-cup-empty";
          empty.textContent = "World Chat is waiting for the first signal.";
          cupWorldChatLog.appendChild(empty);
          return;
        }
        rows.forEach((item) => {
          const row = document.createElement("article");
          row.className = "ft-cup-world-message";
          if (clean(activeWorldUsername()).toLowerCase() === item.username.toLowerCase()) {
            row.classList.add("is-mine");
          }
          const avatar = makeCupAvatar({
            username: item.username,
            displayName: item.displayName,
            avatar: item.avatar,
            gender: "other",
          }, "row");
          const body = document.createElement("div");
          const meta = document.createElement("div");
          meta.className = "ft-cup-world-message-meta";
          const name = document.createElement("span");
          name.textContent = item.displayName || item.username || "Learner";
          const time = document.createElement("time");
          time.textContent = formatCupChatTime(item.createdAt);
          meta.append(name, time);
          const text = document.createElement("div");
          text.className = "ft-cup-world-message-text";
          text.textContent = item.message;
          body.append(meta, text);
          row.append(avatar, body);
          cupWorldChatLog.appendChild(row);
        });
        if (nearBottom) {
          cupWorldChatLog.scrollTop = cupWorldChatLog.scrollHeight;
        }
      };

      const sendCupWorldChat = async () => {
        if (!cupWorldChatInput || !cupWorldChatSend) {
          return;
        }
        const message = clean(cupWorldChatInput.value || "");
        if (!message) {
          return;
        }
        cupWorldChatSend.disabled = true;
        const operationId = `world-chat-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
        try {
          const result = await fetchServerJson("/vocab/leaderboard/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, world_chat_operation_id: operationId, ...activeWorldActorPayload() }),
          });
          const payload = result && result.payload ? result.payload : {};
          const messages = normalizeCupChatRows(payload.messages || []);
          updateCupWorldChatSnapshot(messages, true, payload.revision);
          cupWorldChatInput.value = "";
          if (cupWorldChatLog) {
            cupWorldChatLog.scrollTop = cupWorldChatLog.scrollHeight;
          }
          if (!cupWorldChatPollStopped) {
            if (cupWorldChatPollTimer) {
              window.clearTimeout(cupWorldChatPollTimer);
              cupWorldChatPollTimer = 0;
            }
            scheduleCupWorldChatPolling(CUP_WORLD_CHAT_POLL_MS);
          }
        } catch (error) {
          if (cupStatus) {
            cupStatus.textContent = error && error.message ? error.message : "Could not send World Chat message.";
          }
        } finally {
          cupWorldChatSend.disabled = false;
        }
      };

      const makeCupRankMove = (move = {}) => {
        const direction = clean(move.direction || "");
        const delta = Math.max(0, Math.floor(Number(move.delta || 0) || 0));
        const node = document.createElement("span");
        node.className = "ft-cup-rank-move";
        const setRankDelta = () => {
          const icon = document.createElement("span");
          icon.className = "ft-cup-rank-icon";
          icon.setAttribute("aria-hidden", "true");
          const value = document.createElement("span");
          value.className = "ft-cup-rank-delta";
          value.textContent = String(delta);
          node.replaceChildren(icon, value);
        };
        if (direction === "up" && delta > 0) {
          node.classList.add("is-up");
          node.setAttribute("aria-label", `Rank up ${delta}`);
          setRankDelta();
        } else if (direction === "down" && delta > 0) {
          node.classList.add("is-down");
          node.setAttribute("aria-label", `Rank down ${delta}`);
          setRankDelta();
        } else if (direction === "new") {
          node.classList.add("is-new");
          node.textContent = "NEW";
        } else if (direction === "preview") {
          node.classList.add("is-preview");
          node.textContent = "READY";
        } else {
          node.textContent = "STAY";
        }
        return node;
      };

      const makeCupTodayBadge = (todayWords = 0) => {
        const total = Math.max(0, Math.floor(Number(todayWords || 0) || 0));
        const badge = document.createElement("span");
        badge.className = "ft-cup-today";
        badge.title = `Today: ${cupWordLabel(total)}`;
        if (!total) {
          badge.classList.add("is-zero");
          badge.textContent = `0 ${cupScoreUnit()}s today`;
        } else {
          const icon = document.createElement("span");
          icon.className = "ft-cup-today-icon";
          icon.setAttribute("aria-hidden", "true");
          const text = document.createElement("span");
          text.className = "ft-cup-today-text";
          text.textContent = `Today +${cupWordLabel(total)}`;
          badge.append(icon, text);
        }
        return badge;
      };

      const defaultCupReactionOptions = [
        { key: "love", label: "Love", mark: "\u{1F495}" },
        { key: "burn", label: "Fire heart", mark: "\u2764\uFE0F\u200D\u{1F525}" },
        { key: "devil", label: "Mischief", mark: "\u{1F608}" },
        { key: "frost", label: "Cool", mark: "\u{1F976}" },
      ];

      const normalizeCupReactionOptions = (items = []) => {
        const source = Array.isArray(items) && items.length ? items : defaultCupReactionOptions;
        const seen = new Set();
        return source.map((item, index) => {
          const raw = item && typeof item === "object" ? item : { mark: String(item || "") };
          const mark = clean(raw.mark || raw.emoji || "");
          const label = clean(raw.label || mark || `Reaction ${index + 1}`);
          const key = clean(raw.key || label || `reaction-${index + 1}`)
            .toLowerCase()
            .replace(/[^a-z0-9_-]+/g, "-")
            .replace(/^-+|-+$/g, "") || `reaction-${index + 1}`;
          if (!mark || seen.has(key)) {
            return null;
          }
          seen.add(key);
          return { key, label, mark };
        }).filter(Boolean).slice(0, 12);
      };

      const getCupReactionOptions = () => normalizeCupReactionOptions(cupLeaderboardCache.reactionOptions || []);

      const CUP_STATUS_WORD_LIMIT = 30;
      const cupStatusWordCount = (value = "") => clean(value).split(/\s+/).filter(Boolean).length;

      const validateCupStatusInput = (showMessage = false) => {
        if (!cupStatusInput) {
          return true;
        }
        const count = cupStatusWordCount(cupStatusInput.value || "");
        const overLimit = count > CUP_STATUS_WORD_LIMIT;
        cupStatusInput.classList.toggle("is-over-limit", overLimit);
        if (overLimit && showMessage && cupStatus) {
          cupStatus.textContent = `Status is limited to ${CUP_STATUS_WORD_LIMIT} words. Current: ${count}.`;
        }
        return !overLimit;
      };

      const updateCupStatusComposer = () => {
        if (!cupStatusComposer || !cupStatusInput) {
          return;
        }
        const statuses = cupLeaderboardCache.myStatuses && typeof cupLeaderboardCache.myStatuses === "object"
          ? cupLeaderboardCache.myStatuses
          : {};
        cupStatusInput.value = clean(statuses[currentCupScope] || "");
        validateCupStatusInput(false);
        const signedIn = Boolean(clean(currentAuthUsername));
        cupStatusInput.disabled = !signedIn;
        if (cupStatusSave) {
          cupStatusSave.disabled = !signedIn;
        }
      };

      const saveCupStatus = async () => {
        if (!cupStatusInput || !cupStatusSave) {
          return;
        }
        if (!clean(currentAuthUsername)) {
          if (cupStatus) {
            cupStatus.textContent = "Please sign in before setting a top signal.";
          }
          return;
        }
        const statusText = clean(cupStatusInput.value || "");
        if (!validateCupStatusInput(true)) {
          return;
        }
        cupStatusSave.disabled = true;
        cupStatusSave.textContent = "Saving";
        if (cupStatus) {
          cupStatus.textContent = statusText ? "Saving your top signal..." : "Clearing your top signal...";
        }
        try {
          const result = await fetchServerJson("/vocab/leaderboard/status", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scope: currentCupScope, status: statusText }),
          });
          const payload = result.payload || {};
          if (!cupLeaderboardCache.myStatuses || typeof cupLeaderboardCache.myStatuses !== "object") {
            cupLeaderboardCache.myStatuses = {};
          }
          cupLeaderboardCache.myStatuses[currentCupScope] = clean(payload.status || statusText);
          cupLeaderboardCache.at = 0;
          await loadCupLeaderboard(true);
          if (cupStatus) {
            cupStatus.textContent = statusText ? "Top signal updated." : "Top signal cleared.";
          }
        } catch (error) {
          if (cupStatus) {
            cupStatus.textContent = error && error.message ? error.message : "Could not save top signal.";
          }
        } finally {
          cupStatusSave.textContent = "Set";
          cupStatusSave.disabled = !clean(currentAuthUsername);
        }
      };

      const makeCupReactionSummary = (item = {}) => {
        const social = item.social || {};
        const counts = social.reactions && typeof social.reactions === "object" ? social.reactions : {};
        const options = getCupReactionOptions();
        const mine = new Set(Array.isArray(social.myReactions) ? social.myReactions : []);
        const entries = options.map((config) => {
          const count = Math.max(0, Math.floor(Number(counts[config.key] || 0) || 0));
          return { ...config, count };
        }).filter((entry) => entry.count > 0);
        const total = entries.reduce((sum, entry) => sum + entry.count, 0);
        entries.sort((a, b) => b.count - a.count);
        const selected = options.find((config) => mine.has(config.key)) || null;
        const summary = document.createElement("button");
        summary.type = "button";
        summary.className = "ft-cup-reaction-summary";
        if (!total) {
          summary.classList.add("is-empty");
        }
        if (selected) {
          summary.classList.add("is-mine");
        }
        summary.title = `${total} ${total === 1 ? "reaction" : "reactions"}`;
        const icons = document.createElement("span");
        icons.className = "ft-cup-reaction-summary-icons";
        const visibleEntries = entries.length
          ? entries.slice(0, 3)
          : options.slice(0, 3).map((entry) => ({ ...entry, count: 0 }));
        visibleEntries.forEach((entry) => {
          const icon = document.createElement("span");
          icon.className = "ft-cup-reaction-summary-icon";
          if (!entry.count) {
            icon.classList.add("is-ghost");
          }
          icon.textContent = entry.mark;
          icon.title = entry.count ? `${entry.label}: ${entry.count}` : entry.label;
          icons.appendChild(icon);
        });
        const count = document.createElement("span");
        count.className = "ft-cup-reaction-summary-count";
        count.textContent = total ? String(total) : "React";
        summary.append(icons, count);
        summary.addEventListener("click", (event) => {
          event.stopPropagation();
          const card = summary.closest(".ft-cup-social");
          if (card) {
            card.classList.toggle("is-react-open");
          }
        });
        return summary;
      };

      const makeCupReactionBar = (item = {}) => {
        const bar = document.createElement("div");
        bar.className = "ft-cup-reactions";
        const social = item.social || {};
        const counts = social.reactions && typeof social.reactions === "object" ? social.reactions : {};
        const mine = new Set(Array.isArray(social.myReactions) ? social.myReactions : []);
        getCupReactionOptions().forEach((config) => {
          const key = config.key;
          const button = document.createElement("button");
          button.type = "button";
          button.className = "ft-cup-reaction";
          if (mine.has(key)) {
            button.classList.add("is-active");
          }
          const count = Math.max(0, Math.floor(Number(counts[key] || 0) || 0));
          button.textContent = config.mark;
          button.title = `${config.label}${count ? ` | ${count}` : ""}`;
          button.setAttribute("aria-label", button.title);
          button.addEventListener("click", async (event) => {
            event.stopPropagation();
            if (!clean(currentAuthUsername) || clean(currentAuthUsername).toLowerCase() === clean(item.username).toLowerCase()) {
              return;
            }
            button.disabled = true;
            const socialCard = button.closest(".ft-cup-social");
            if (socialCard) {
              socialCard.classList.add("is-react-busy");
            }
            try {
              const result = await fetchServerJson("/vocab/leaderboard/react", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scope: currentCupScope, target: item.username, reaction: key }),
              });
              const socialResult = result.payload && result.payload.social ? result.payload.social : result.social;
              if (socialResult && item.social) {
                item.social = {
                  status: item.social.status,
                  statusUpdatedAt: item.social.statusUpdatedAt,
                  reactions: socialResult.reactions || {},
                  myReactions: Array.isArray(socialResult.my_reactions)
                    ? socialResult.my_reactions
                    : (clean(socialResult.my_reaction || socialResult.myReaction) ? [clean(socialResult.my_reaction || socialResult.myReaction)] : []),
                };
              }
              cupLeaderboardCache.at = 0;
              if (socialCard) {
                socialCard.classList.remove("is-react-open");
              }
              void loadCupLeaderboard(true);
            } catch (error) {
              if (cupStatus) {
                cupStatus.textContent = error && error.message ? error.message : "Could not send reaction.";
              }
            } finally {
              button.disabled = false;
              if (socialCard) {
                socialCard.classList.remove("is-react-busy");
              }
            }
          });
          bar.appendChild(button);
        });
        return bar;
      };

      const makeCupSocialCard = (item = {}, mode = "podium") => {
        const status = clean(item && item.social && item.social.status || "");
        if (!status) {
          return null;
        }
        const card = document.createElement("aside");
        card.className = `ft-cup-social is-${mode}`;
        const kicker = document.createElement("div");
        kicker.className = "ft-cup-social-kicker";
        kicker.textContent = "Status";
        const text = document.createElement("div");
        text.className = "ft-cup-social-text";
        text.textContent = status;
        const summary = makeCupReactionSummary(item);
        if (summary && !summary.classList.contains("is-empty")) {
          card.classList.add("has-reactions");
        }
        card.append(kicker, text, summary, makeCupReactionBar(item));
        return card;
      };

      const makeCupSocialAlert = () => {
        const node = document.createElement("button");
        node.type = "button";
        node.className = "ft-cup-social-alert";
        node.textContent = "!";
        node.title = "Hover to read this learner status.";
        return node;
      };

      const positionCupSocialBubble = (bubble = null, card = null) => {
        if (!bubble || !card || !cupPodium) {
          return;
        }
        const avatar = card.querySelector(".ft-cup-avatar");
        if (!avatar) {
          return;
        }
        const podiumRect = cupPodium.getBoundingClientRect();
        const avatarRect = avatar.getBoundingClientRect();
        const rank = Math.max(1, Math.min(3, Number(card.dataset.rank || 1) || 1));
        const preferredWidth = rank === 1 ? 180 : 160;
        const width = Math.max(140, Math.min(preferredWidth, Math.max(140, cupPodium.clientWidth * 0.24)));
        bubble.style.width = `${width}px`;
        const avatarX = avatarRect.right - podiumRect.left - Math.max(8, avatarRect.width * 0.14);
        const avatarY = avatarRect.top - podiumRect.top + Math.max(8, avatarRect.height * 0.14);
        let x = avatarX + 22;
        let y = avatarY - 104;
        const maxX = Math.max(6, cupPodium.clientWidth - width - 6);
        x = Math.max(6, Math.min(x, maxX));
        y = Math.max(-102, y);
        bubble.style.left = `${Math.round(x)}px`;
        bubble.style.top = `${Math.round(y)}px`;
        const bubbleHeight = Math.max(44, bubble.offsetHeight || 64);
        const targetX = Math.max(x + 20, Math.min(avatarX + 26, x + width - 20));
        const targetY = y + bubbleHeight - 8;
        const tailRank = clean(bubble.dataset.rank || "");
        const tailUsername = clean(bubble.dataset.username || "").toLowerCase();
        const tail = Array.from(cupPodium.querySelectorAll(".ft-cup-social-tail")).find((node) => (
          clean(node.dataset.rank || "") === tailRank
          && clean(node.dataset.username || "").toLowerCase() === tailUsername
        ));
        if (tail) {
          const minX = Math.min(avatarX, targetX) - 10;
          const minY = Math.min(avatarY, targetY) - 12;
          const tailWidth = Math.max(24, Math.abs(targetX - avatarX) + 22);
          const tailHeight = Math.max(30, Math.abs(targetY - avatarY) + 24);
          tail.style.left = `${Math.round(minX)}px`;
          tail.style.top = `${Math.round(minY)}px`;
          tail.setAttribute("width", String(Math.ceil(tailWidth)));
          tail.setAttribute("height", String(Math.ceil(tailHeight)));
          tail.setAttribute("viewBox", `0 0 ${Math.ceil(tailWidth)} ${Math.ceil(tailHeight)}`);
          const sx = avatarX - minX;
          const sy = avatarY - minY;
          const tx = targetX - minX;
          const ty = targetY - minY;
          const dx = tx - sx;
          const curveLift = Math.max(18, Math.min(46, Math.abs(ty - sy) * 0.38));
          const c1x = sx + dx * 0.18;
          const c1y = sy - curveLift;
          const c2x = tx - dx * 0.28;
          const c2y = ty + Math.max(8, curveLift * 0.28);
          const dot = (t, lift, radius) => {
            const px = sx + (tx - sx) * t;
            const py = sy + (ty - sy) * t - lift;
            return `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="${radius}"></circle>`;
          };
          tail.innerHTML = `
            <path d="M ${sx.toFixed(1)} ${sy.toFixed(1)} C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${tx.toFixed(1)} ${ty.toFixed(1)}"></path>
            ${dot(0.20, 10, 2.2)}
            ${dot(0.52, 18, 3.6)}
            ${dot(0.82, 12, 5.2)}
          `;
        }
      };

      const positionCupSocialBubbles = () => {
        if (!cupPodium) {
          return;
        }
        const cards = Array.from(cupPodium.querySelectorAll(".ft-cup-podium-card"));
        cupPodium.querySelectorAll(".ft-cup-social").forEach((bubble) => {
          const rank = clean(bubble.dataset.rank || "");
          const username = clean(bubble.dataset.username || "").toLowerCase();
          const card = cards.find((node) => (
            clean(node.dataset.rank || "") === rank
            && clean(node.dataset.username || "").toLowerCase() === username
          ));
          if (card) {
            positionCupSocialBubble(bubble, card);
          }
        });
      };

      const makeCupTrophy = (rank = 1, scope = "total") => {
        const safeRank = Math.max(1, Math.min(3, Math.floor(Number(rank || 1) || 1)));
        const safeScope = ["total", "day", "week", "month"].includes(scope) ? scope : "total";
        const trophy = document.createElement("div");
        trophy.className = `ft-cup-trophy is-rank-${safeRank} is-scope-${safeScope}`;
        trophy.setAttribute("aria-hidden", "true");
        const paths = {
          total: {
            1: `
              <path class="cup-core" d="M13 9h22l-2 12c-.9 5.1-4.4 8-9 8s-8.1-2.9-9-8L13 9Z"/>
              <path class="cup-line" d="M13 12H7.6c-.9 0-1.6.8-1.4 1.7 1 5.9 4.2 9.1 9.8 9.6M35 12h5.4c.9 0 1.6.8 1.4 1.7-1 5.9-4.2 9.1-9.8 9.6M24 29v7M16 40h16M18.5 36h11"/>
              <path class="cup-line" d="M24 4l2.1 3.6 4.1.6-3 2.8.7 4-3.9-2-3.9 2 .7-4-3-2.8 4.1-.6L24 4Z"/>
              <circle class="cup-spark" cx="10" cy="7" r="1.4"/><circle class="cup-spark" cx="39" cy="28" r="1.2"/>
            `,
            2: `
              <path class="cup-core" d="M14 10h20l-4.2 16H18.2L14 10Z"/>
              <path class="cup-line" d="M14.8 14H8.5l1.9 7.7c.8 3.1 3.2 5 7 5.4M33.2 14h6.3l-1.9 7.7c-.8 3.1-3.2 5-7 5.4M24 27v7M17.5 39h13M19.5 34.5h9"/>
              <path class="cup-line" d="M17 10l3.5-4h7L31 10M18.8 17h10.4M20 21h8"/>
              <circle class="cup-spark" cx="38" cy="9" r="1.3"/><circle class="cup-spark" cx="12" cy="31" r="1"/>
            `,
            3: `
              <path class="cup-core" d="M16.5 9h15L36 17l-4.5 13h-15L12 17l4.5-8Z"/>
              <path class="cup-line" d="M16.5 9 24 17l7.5-8M12 17h24M16.5 30 24 17l7.5 13M24 30v5.5M18 40h12"/>
              <path class="cup-line" d="M12.6 15H7.7c-.9 0-1.5.8-1.2 1.7 1.2 4.1 3.7 6.7 7.6 7.8M35.4 15h4.9c.9 0 1.5.8 1.2 1.7-1.2 4.1-3.7 6.7-7.6 7.8"/>
              <circle class="cup-spark" cx="10" cy="28" r="1.1"/><circle class="cup-spark" cx="36" cy="8" r="1.2"/>
            `,
          },
          day: {
            1: `
              <path class="cup-core" d="M13 12h22l-2.8 15H15.8L13 12Z"/>
              <path class="cup-line" d="M17 17h14M19 22h10M24 27v8M16 40h16M13 15H7.5c-.8 0-1.4.7-1.2 1.5 1 4.6 3.8 7.3 8.5 8M35 15h5.5c.8 0 1.4.7 1.2 1.5-1 4.6-3.8 7.3-8.5 8"/>
              <path class="cup-line" d="M24 4v5M17.5 6.5 20 10M30.5 6.5 28 10M14 11.5 9.5 9.8M34 11.5l4.5-1.7"/>
              <circle class="cup-spark" cx="24" cy="8.5" r="1.4"/><circle class="cup-spark" cx="39" cy="30" r="1.2"/>
            `,
            2: `
              <path class="cup-core" d="M15 11h18l3 9-6.5 11h-11L12 20l3-9Z"/>
              <path class="cup-line" d="M15 11h18M12 20h24M18.5 31 24 20l5.5 11M24 31v5M18 41h12M13 15H8l1.6 6.6c.8 3.1 3 4.9 6.3 5.4M35 15h5l-1.6 6.6c-.8 3.1-3 4.9-6.3 5.4"/>
              <path class="cup-line" d="M24 5v5M19 7l2 3M29 7l-2 3"/>
              <circle class="cup-spark" cx="38" cy="9" r="1.1"/><circle class="cup-spark" cx="10" cy="30" r="1"/>
            `,
            3: `
              <path class="cup-core" d="M16 12h16l3.2 8-4.8 10H17.6l-4.8-10L16 12Z"/>
              <path class="cup-line" d="M16 12 24 19l8-7M12.8 20h22.4M17.6 30 24 19l6.4 11M24 30v6M18 41h12M13 16H8l1.5 6c.8 3 2.8 4.8 6 5.4M35 16h5l-1.5 6c-.8 3-2.8 4.8-6 5.4"/>
              <path class="cup-line" d="M24 5v4M20 7.2l1.8 2.2M28 7.2l-1.8 2.2"/>
              <circle class="cup-spark" cx="10" cy="9" r="1"/><circle class="cup-spark" cx="39" cy="29" r="1.1"/>
            `,
          },
          week: {
            1: `
              <path class="cup-core" d="M10 13h28l-5.5 16h-17L10 13Z"/>
              <path class="cup-line" d="M14 13 24 5l10 8M18.5 18h11M20.5 23h7M24 29v7M16.5 40h15"/>
              <path class="cup-line" d="M11 16H6.5c-.8 0-1.4.7-1.2 1.5 1.1 4.4 3.7 7.1 8.2 8M37 16h4.5c.8 0 1.4.7 1.2 1.5-1.1 4.4-3.7 7.1-8.2 8"/>
              <path class="cup-line" d="M24 9v7M20.5 12.5h7"/>
              <circle class="cup-spark" cx="8" cy="9" r="1.2"/><circle class="cup-spark" cx="40" cy="31" r="1.3"/>
            `,
            2: `
              <path class="cup-core" d="M13 10h22l-3 17-8 5-8-5-3-17Z"/>
              <path class="cup-line" d="M17 15h14M18.5 20h11M24 32v5M17 41h14M12.8 14H7l1.8 8.2c.7 3.1 2.9 4.9 6.3 5.4M35.2 14H41l-1.8 8.2c-.7 3.1-2.9 4.9-6.3 5.4"/>
              <path class="cup-line" d="M24 5l3.2 5h-6.4L24 5Z"/>
              <circle class="cup-spark" cx="38" cy="8" r="1.1"/><circle class="cup-spark" cx="12" cy="33" r="1"/>
            `,
            3: `
              <path class="cup-core" d="M15 12h18l3 8-7 10H19l-7-10 3-8Z"/>
              <path class="cup-line" d="M15 12h18M12 20h24M19 30l5-10 5 10M24 30v6M18 41h12M13.2 16H7.8l1.6 6.5c.8 3.2 3 5 6.3 5.4M34.8 16h5.4l-1.6 6.5c-.8 3.2-3 5-6.3 5.4"/>
              <circle class="cup-spark" cx="10" cy="9" r="1"/><circle class="cup-spark" cx="39" cy="30" r="1.1"/>
            `,
          },
          month: {
            1: `
              <path class="cup-core" d="M12 10h24l-3.5 18H15.5L12 10Z"/>
              <path class="cup-line" d="M15 10 24 5l9 5M18 16h12M20 22h8M24 28v8M16 40h16M12 14H7c-.8 0-1.4.7-1.2 1.5 1 4.8 3.9 7.7 8.7 8.5M36 14h5c.8 0 1.4.7 1.2 1.5-1 4.8-3.9 7.7-8.7 8.5"/>
              <path class="cup-line" d="M24 4c5.2 5.2 5.2 10.2 0 15-5.2-4.8-5.2-9.8 0-15Z"/>
              <circle class="cup-spark" cx="9" cy="31" r="1.2"/><circle class="cup-spark" cx="40" cy="8" r="1.3"/>
            `,
            2: `
              <path class="cup-core" d="M14 9h20v16l-10 6-10-6V9Z"/>
              <path class="cup-line" d="M17 15h14M18.5 20.5h11M24 31v6M17 41h14M14 13H8l2 8c.8 3 2.9 4.8 6.3 5.2M34 13h6l-2 8c-.8 3-2.9 4.8-6.3 5.2"/>
              <path class="cup-line" d="M20 8c1.5-2.2 3-3.3 4-3.3s2.5 1.1 4 3.3"/>
              <circle class="cup-spark" cx="37" cy="32" r="1.1"/><circle class="cup-spark" cx="11" cy="8" r="1"/>
            `,
            3: `
              <path class="cup-core" d="M16 10h16l4 7-4 13H16l-4-13 4-7Z"/>
              <path class="cup-line" d="M16 10 24 18l8-8M12 17h24M16 30l8-12 8 12M24 30v6M18 41h12M12.8 15H8l1.5 6c.8 3.2 3 5.1 6.3 5.8M35.2 15H40l-1.5 6c-.8 3.2-3 5.1-6.3 5.8"/>
              <circle class="cup-spark" cx="9" cy="29" r="1"/><circle class="cup-spark" cx="39" cy="9" r="1.1"/>
            `,
          },
        };
        trophy.innerHTML = `<svg viewBox="0 0 48 48" focusable="false">${paths[safeScope][safeRank]}</svg>`;
        return trophy;
      };

      const defaultCupRewardConfig = () => ({
        total: {
          title: "Hall Champion",
          claim_window: "Honor reward preview for the all-time leaderboard.",
          ranks: {
            1: { badge: true, rare: 12, easy: 36, space_q: 12, space_q_silver: 12, space_p: 12, space_p_silver: 12, space_s: 12, space_s_silver: 12, space_w: 12, space_w_silver: 12, space_l: 12, space_l_silver: 12, space_v: 12 },
            2: { badge: false, rare: 8, easy: 24, space_q: 8, space_q_silver: 8, space_p: 8, space_p_silver: 8, space_s: 8, space_s_silver: 8, space_w: 8, space_w_silver: 8, space_l: 8, space_l_silver: 8, space_v: 8 },
            3: { badge: false, rare: 5, easy: 16, space_q: 5, space_q_silver: 5, space_p: 5, space_p_silver: 5, space_s: 5, space_s_silver: 5, space_w: 5, space_w_silver: 5, space_l: 5, space_l_silver: 5, space_v: 5 },
          },
        },
        day: {
          title: "Daily Champion",
          claim_window: "Claim during the next day only.",
          ranks: {
            1: { badge: true, rare: 5, easy: 15, space_q: 3, space_q_silver: 3, space_p: 3, space_p_silver: 3, space_s: 3, space_s_silver: 3, space_w: 3, space_w_silver: 3, space_l: 3, space_l_silver: 3, space_v: 3 },
            2: { badge: false, rare: 3, easy: 10, space_q: 2, space_q_silver: 2, space_p: 2, space_p_silver: 2, space_s: 2, space_s_silver: 2, space_w: 2, space_w_silver: 2, space_l: 2, space_l_silver: 2, space_v: 2 },
            3: { badge: false, rare: 2, easy: 6, space_q: 1, space_q_silver: 1, space_p: 1, space_p_silver: 1, space_s: 1, space_s_silver: 1, space_w: 1, space_w_silver: 1, space_l: 1, space_l_silver: 1, space_v: 1 },
          },
        },
        week: {
          title: "Weekly Champion",
          claim_window: "Claim during the next week only.",
          ranks: {
            1: { badge: true, rare: 18, easy: 54, space_q: 9, space_q_silver: 9, space_p: 9, space_p_silver: 9, space_s: 9, space_s_silver: 9, space_w: 9, space_w_silver: 9, space_l: 9, space_l_silver: 9, space_v: 9 },
            2: { badge: false, rare: 12, easy: 36, space_q: 6, space_q_silver: 6, space_p: 6, space_p_silver: 6, space_s: 6, space_s_silver: 6, space_w: 6, space_w_silver: 6, space_l: 6, space_l_silver: 6, space_v: 6 },
            3: { badge: false, rare: 8, easy: 24, space_q: 4, space_q_silver: 4, space_p: 4, space_p_silver: 4, space_s: 4, space_s_silver: 4, space_w: 4, space_w_silver: 4, space_l: 4, space_l_silver: 4, space_v: 4 },
          },
        },
        month: {
          title: "Monthly Champion",
          claim_window: "Claim during the next month only.",
          ranks: {
            1: { badge: true, rare: 60, easy: 180, space_q: 30, space_q_silver: 30, space_p: 30, space_p_silver: 30, space_s: 30, space_s_silver: 30, space_w: 30, space_w_silver: 30, space_l: 30, space_l_silver: 30, space_v: 30 },
            2: { badge: false, rare: 40, easy: 120, space_q: 20, space_q_silver: 20, space_p: 20, space_p_silver: 20, space_s: 20, space_s_silver: 20, space_w: 20, space_w_silver: 20, space_l: 20, space_l_silver: 20, space_v: 20 },
            3: { badge: false, rare: 25, easy: 80, space_q: 12, space_q_silver: 12, space_p: 12, space_p_silver: 12, space_s: 12, space_s_silver: 12, space_w: 12, space_w_silver: 12, space_l: 12, space_l_silver: 12, space_v: 12 },
          },
        },
      });

      const normalizeCupRewardConfig = (config = {}) => {
        const defaults = defaultCupRewardConfig();
        const source = config && typeof config === "object" ? config : {};
        const output = {};
        ["total", "day", "week", "month"].forEach((scope) => {
          const data = source[scope] && typeof source[scope] === "object" ? source[scope] : {};
          const base = defaults[scope];
          const ranks = {};
          [1, 2, 3].forEach((rank) => {
            const rawRanks = data.ranks && typeof data.ranks === "object" ? data.ranks : {};
            const raw = rawRanks[String(rank)] || rawRanks[rank] || {};
            ranks[rank] = {
              badge: Boolean(raw.badge ?? base.ranks[rank].badge),
              rare: Math.max(0, Math.floor(Number(raw.rare ?? base.ranks[rank].rare) || 0)),
              easy: Math.max(0, Math.floor(Number(raw.easy ?? base.ranks[rank].easy) || 0)),
              space_q: Math.max(0, Math.floor(Number(raw.space_q ?? raw.spaceQ ?? base.ranks[rank].space_q) || 0)),
              space_q_silver: Math.max(0, Math.floor(Number(raw.space_q_silver ?? raw.spaceQSilver ?? base.ranks[rank].space_q_silver) || 0)),
              space_p: Math.max(0, Math.floor(Number(raw.space_p ?? raw.spaceP ?? base.ranks[rank].space_p) || 0)),
              space_p_silver: Math.max(0, Math.floor(Number(raw.space_p_silver ?? raw.spacePSilver ?? base.ranks[rank].space_p_silver) || 0)),
              space_s: Math.max(0, Math.floor(Number(raw.space_s ?? raw.spaceS ?? base.ranks[rank].space_s) || 0)),
              space_s_silver: Math.max(0, Math.floor(Number(raw.space_s_silver ?? raw.spaceSSilver ?? base.ranks[rank].space_s_silver) || 0)),
              space_w: Math.max(0, Math.floor(Number(raw.space_w ?? raw.spaceW ?? base.ranks[rank].space_w) || 0)),
              space_w_silver: Math.max(0, Math.floor(Number(raw.space_w_silver ?? raw.spaceWSilver ?? base.ranks[rank].space_w_silver) || 0)),
              space_l: Math.max(0, Math.floor(Number(raw.space_l ?? raw.spaceL ?? base.ranks[rank].space_l) || 0)),
              space_l_silver: Math.max(0, Math.floor(Number(raw.space_l_silver ?? raw.spaceLSilver ?? base.ranks[rank].space_l_silver) || 0)),
              space_v: Math.max(0, Math.floor(Number(raw.space_v ?? raw.spaceV ?? base.ranks[rank].space_v) || 0)),
            };
          });
          output[scope] = {
            title: clean(data.title || base.title),
            claim_window: clean(data.claim_window || data.claimWindow || base.claim_window),
            ranks,
          };
        });
        return output;
      };

      const cupRewardForScope = (scope = currentCupScope) => {
        const safeScope = ["total", "day", "week", "month"].includes(scope) ? scope : "total";
        return normalizeCupRewardConfig(cupRewardConfig)[safeScope] || normalizeCupRewardConfig({}).total;
      };

      const makeCupRewardItem = (kind, name, count) => {
        const item = document.createElement("div");
        item.className = "ft-cup-reward-item";
        const gem = document.createElement("span");
        gem.className = `ft-cup-reward-gem ${kind ? `is-${kind}` : ""}`;
        const label = document.createElement("span");
        label.className = "ft-cup-reward-item-name";
        label.textContent = name;
        const amount = document.createElement("strong");
        amount.className = "ft-cup-reward-item-count";
        amount.textContent = count === null ? "earned" : `x${formatCupWords(count)}`;
        item.append(gem, label, amount);
        return item;
      };

      const closeCupRewardPopup = () => {
        if (!cupRewardModal) {
          return;
        }
        cupRewardModal.classList.remove("is-open");
        cupRewardModal.setAttribute("aria-hidden", "true");
      };

      const openCupRewardPopup = (scope = currentCupScope, rows = []) => {
        if (!cupRewardModal || !cupRewardBody) {
          return;
        }
        const safeScope = ["total", "day", "week", "month"].includes(scope) ? scope : "total";
        const reward = cupRewardForScope(safeScope);
        const winners = normalizeCupRows(rows, safeScope).slice(0, 3);
        cupRewardBody.innerHTML = "";
        if (cupRewardTitle) {
          cupRewardTitle.textContent = `${reward.title || cupScopeLabel(safeScope)} Rewards`;
        }
        const hero = document.createElement("section");
        hero.className = "ft-cup-reward-hero";
        const emblem = document.createElement("div");
        emblem.className = "ft-cup-reward-emblem";
        emblem.appendChild(makeCupTrophy(1, safeScope).querySelector("svg").cloneNode(true));
        const copy = document.createElement("div");
        copy.className = "ft-cup-reward-copy";
        const headline = document.createElement("strong");
        const topName = winners[0] ? winners[0].displayName : "Top winner";
        headline.textContent = `${topName} leads ${cupScopeLabel(safeScope).toLowerCase()}`;
        const detail = document.createElement("span");
        detail.textContent = reward.claim_window || "Reward claim window follows the selected leaderboard period.";
        const note = document.createElement("span");
        note.textContent = "Rare crystals honor first-time vocabulary, review crystals honor practice, and Space_Q, Space_P, Space_S, Space_L, Space_W, Space_V rewards stay visible here in both gold and silver forms.";
        copy.append(headline, detail, note);
        hero.append(emblem, copy);
        const grid = document.createElement("div");
        grid.className = "ft-cup-reward-grid";
        [1, 2, 3].forEach((rank) => {
          const row = winners.find((item) => item.rank === rank) || null;
          const rankReward = (reward.ranks && (reward.ranks[rank] || reward.ranks[String(rank)])) || { badge: rank === 1, rare: 0, easy: 0, space_q: 0, space_q_silver: 0, space_p: 0, space_p_silver: 0, space_s: 0, space_s_silver: 0, space_w: 0, space_w_silver: 0, space_l: 0, space_l_silver: 0, space_v: 0 };
          const card = document.createElement("article");
          card.className = `ft-cup-reward-rank is-rank-${rank}`;
          const title = document.createElement("div");
          title.className = "ft-cup-reward-rank-title";
          title.textContent = row ? `Rank #${rank} | ${row.displayName}` : `Rank #${rank}`;
          const items = document.createElement("div");
          items.className = "ft-cup-reward-items";
          if (rankReward.badge) {
            items.appendChild(makeCupRewardItem("badge", `${reward.title || cupScopeLabel(safeScope)} badge`, null));
          }
          const goldenAxeCount = Math.max(0, Number(rankReward.rare || 0) || 0) + Math.max(0, Number(rankReward.space_v || 0) || 0);
          if (goldenAxeCount > 0) {
            items.appendChild(makeCupRewardItem("space-v", "Golden Axe", goldenAxeCount));
          }
          if (Number(rankReward.easy || 0) > 0) {
            items.appendChild(makeCupRewardItem("easy", "Silver Axe", rankReward.easy));
          }
          if (Number(rankReward.space_q || 0) > 0) {
            items.appendChild(makeCupRewardItem("bookgold", "Golden Magic Book", rankReward.space_q));
          }
          if (Number(rankReward.space_q_silver || 0) > 0) {
            items.appendChild(makeCupRewardItem("booksilver", "Silver Magic Book", rankReward.space_q_silver));
          }
          if (Number(rankReward.space_p || 0) > 0) {
            items.appendChild(makeCupRewardItem("bowgold", "Golden Magic Bow", rankReward.space_p));
          }
          if (Number(rankReward.space_p_silver || 0) > 0) {
            items.appendChild(makeCupRewardItem("bowsilver", "Silver Magic Bow", rankReward.space_p_silver));
          }
          if (Number(rankReward.space_s || 0) > 0) {
            items.appendChild(makeCupRewardItem("saxgold", "Golden Devil Wings", rankReward.space_s));
          }
          if (Number(rankReward.space_s_silver || 0) > 0) {
            items.appendChild(makeCupRewardItem("saxsilver", "Silver Devil Wings", rankReward.space_s_silver));
          }
          if (Number(rankReward.space_w || 0) > 0) {
            items.appendChild(makeCupRewardItem("cupgold", "Golden Mastery Cup", rankReward.space_w));
          }
          if (Number(rankReward.space_w_silver || 0) > 0) {
            items.appendChild(makeCupRewardItem("cupiron", "Silver Practice Cup", rankReward.space_w_silver));
          }
          if (Number(rankReward.space_l || 0) > 0) {
            items.appendChild(makeCupRewardItem("swordgold", "Golden Great Sword", rankReward.space_l));
          }
          if (Number(rankReward.space_l_silver || 0) > 0) {
            items.appendChild(makeCupRewardItem("swordsilver", "Silver Great Sword", rankReward.space_l_silver));
          }
          card.append(title, items);
          grid.appendChild(card);
        });
        cupRewardBody.append(hero, grid);
        cupRewardModal.classList.add("is-open");
        cupRewardModal.setAttribute("aria-hidden", "false");
      };

      const updateCupTabs = () => {
        cupTabs.forEach((button) => {
          const active = clean(button.dataset.cupScope || "total") === currentCupScope;
          button.classList.toggle("is-active", active);
          button.setAttribute("aria-selected", active ? "true" : "false");
        });
        updateCupTypePicker();
      };

      const stopCupLeaderboardRefresh = () => {
        if (cupLeaderboardRefreshTimer) {
          window.clearTimeout(cupLeaderboardRefreshTimer);
          cupLeaderboardRefreshTimer = 0;
        }
      };

      const scheduleCupLeaderboardRefresh = () => {
        stopCupLeaderboardRefresh();
        if (!cupModal || !cupModal.classList.contains("is-open")) {
          return;
        }
        cupLeaderboardRefreshTimer = window.setTimeout(() => {
          cupLeaderboardRefreshTimer = 0;
          void loadCupLeaderboard(true);
        }, 30000);
      };

      const renderCupLeaderboard = (rows, scope = currentCupScope, options = {}) => {
        if (!cupPodium || !cupList || !cupStatus) {
          return;
        }
        currentCupScope = ["total", "day", "week", "month"].includes(scope) ? scope : "total";
        const renderOptions = options && typeof options === "object" ? options : {};
        const previousScope = clean(cupPodium.dataset.scope || "");
        const hadRenderedBoard = Boolean(
          cupPodium.querySelector(".ft-cup-podium-card") ||
          cupList.querySelector(".ft-cup-row")
        );
        const softRefresh = renderOptions.softRefresh !== undefined
          ? Boolean(renderOptions.softRefresh)
          : Boolean(hadRenderedBoard && previousScope === currentCupScope);
        if (cupModal) {
          cupModal.classList.toggle("is-soft-refresh", softRefresh);
        }
        updateCupTabs();
        updateCupStatusComposer();
        renderCupWorldChat(cupLeaderboardCache.chat || []);
        const users = mergePendingCupRow(normalizeCupRows(rows, currentCupScope), currentCupScope);
        const visibleUsers = users.slice(0, 10);
        const pendingUsername = clean(cupPendingCompletion && cupPendingCompletion.username).toLowerCase();
        const currentUsername = clean(currentAuthUsername).toLowerCase();
        const currentUserRow = users.find((item) => clean(item && item.username).toLowerCase() === currentUsername) || null;
        const maxWords = Math.max(1, ...users.map((item) => item.scoreWords));
        // Added 2026-07-30: reuse one row renderer for the pinned learner card
        // and the independently scrolling official Top 10 list.
        const makeCupLeaderboardRow = (item, pinnedSelf = false) => {
          const row = document.createElement("article");
          row.className = "ft-cup-row";
          const motionClass = cupRankMotionClass(item);
          if (motionClass) {
            row.classList.add(motionClass);
          }
          if (item.placeholder) {
            row.classList.add("is-preview");
          }
          if (item.pending) {
            row.classList.add("is-pending");
          }
          if (currentUsername === item.username.toLowerCase()) {
            row.classList.add("is-current");
          }
          if (pinnedSelf) {
            row.classList.add("is-pinned-self");
          }
          row.style.setProperty("--rank", String(item.rank));
          row.style.setProperty("--score-width", `${Math.max(6, Math.min(100, Math.round((item.scoreWords / maxWords) * 100)))}%`);
          const rankWrap = document.createElement("div");
          rankWrap.className = "ft-cup-rank-wrap";
          const rank = document.createElement("span");
          rank.className = "ft-cup-row-rank";
          rank.textContent = item.pending ? `~${item.rank}` : String(item.rank);
          rankWrap.append(rank, makeCupRankMove(item.rankMove));
          const meta = document.createElement("div");
          meta.className = "ft-cup-row-meta";
          const name = document.createElement("div");
          name.className = "ft-cup-row-name";
          name.textContent = item.displayName;
          const period = document.createElement("div");
          period.className = "ft-cup-period";
          period.textContent = item.pending
            ? `${cupWordLabel(item.scoreWords)} committed; official rank pending`
            : item.placeholder
            ? `Waiting for the first ${cupTypeConfig().empty}`
            : currentCupScope === "total"
            ? `${cupWordLabel(item.totalWords)} completed overall`
            : `${cupWordLabel(item.scoreWords)} in ${cupScopeLabel(currentCupScope).toLowerCase()}`;
          const bar = document.createElement("div");
          bar.className = "ft-cup-row-bar";
          bar.appendChild(document.createElement("span"));
          meta.appendChild(name);
          if (currentCupScope !== "day") {
            meta.appendChild(makeCupTodayBadge(item.todayWords));
          }
          meta.append(period, bar);
          row.append(rankWrap, makeCupAvatar(item, "row"), meta, makeCupScore(item.scoreWords, currentCupScope));
          return row;
        };
        if (cupTitle) {
          cupTitle.textContent = cupTopTenTitle(currentCupScope);
        }
        cupPodium.innerHTML = "";
        cupPodium.dataset.scope = currentCupScope;
        cupList.innerHTML = "";
        cupList.classList.toggle("has-pinned-self", Boolean(currentUserRow));
        if (currentUserRow) {
          const pinned = document.createElement("section");
          pinned.className = "ft-cup-self-rank";
          const pinnedLabel = document.createElement("div");
          pinnedLabel.className = "ft-cup-self-rank-label";
          pinnedLabel.innerHTML = '<span aria-hidden="true"></span><strong>Your rank</strong><small>Live on this board</small>';
          pinned.append(pinnedLabel, makeCupLeaderboardRow(currentUserRow, true));
          cupList.appendChild(pinned);
        }
        cupList.appendChild(makeCupListHeading(currentCupScope));
        const scrollRows = document.createElement("div");
        scrollRows.className = "ft-cup-scroll-rows";
        cupList.appendChild(scrollRows);
        renderCupViewers(cupLeaderboardCache.viewers || []);
        if (!users.length) {
          const empty = document.createElement("div");
          empty.className = "ft-cup-empty";
          empty.textContent = `No ${cupTypeConfig().empty} on the ${cupScopeLabel(currentCupScope).toLowerCase()} board yet.`;
          scrollRows.appendChild(empty);
          cupStatus.textContent = `${cupTypeTitle()} updates after learners complete files.`;
          return;
        }
        users.slice(0, 3).forEach((item) => {
          const card = document.createElement("article");
          card.className = `ft-cup-podium-card is-rank-${Math.max(1, Math.min(3, item.rank))}`;
          card.dataset.rank = String(item.rank);
          card.dataset.username = item.username;
          const motionClass = cupRankMotionClass(item);
          if (motionClass) {
            card.classList.add(motionClass);
          }
          if (item.placeholder) {
            card.classList.add("is-preview");
          }
          card.style.setProperty("--rank", String(item.rank));
          const rank = document.createElement("span");
          rank.className = "ft-cup-podium-rank";
          rank.textContent = `#${item.rank}`;
          const move = makeCupRankMove(item.rankMove);
          const name = document.createElement("div");
          name.className = "ft-cup-podium-name";
          name.textContent = item.displayName;
          const score = document.createElement("div");
          score.className = "ft-cup-podium-score";
          score.append(document.createTextNode(formatCupWords(item.scoreWords)));
          const unit = document.createElement("small");
          unit.textContent = ` ${cupScoreUnit()}s`;
          score.append(unit);
          card.append(rank, move, makeCupTrophy(item.rank, currentCupScope), makeCupAvatar(item, "podium"), name);
          if (currentCupScope !== "day") {
            card.appendChild(makeCupTodayBadge(item.todayWords));
          }
          card.appendChild(score);
          if (item.rank === 1) {
            const rewardButton = document.createElement("button");
            rewardButton.className = "ft-cup-reward-button";
            rewardButton.type = "button";
            rewardButton.textContent = "Reward";
            rewardButton.addEventListener("click", (event) => {
              event.stopPropagation();
              openCupRewardPopup(currentCupScope, users);
            });
            card.appendChild(rewardButton);
          }
          cupPodium.appendChild(card);
        });
        const socialLayer = document.createElement("div");
        socialLayer.className = "ft-cup-social-layer";
        users.slice(0, 3).forEach((item) => {
          const socialCard = makeCupSocialCard(item, "podium");
          if (!socialCard) {
            return;
          }
          const socialTail = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          socialTail.classList.add("ft-cup-social-tail");
          socialTail.dataset.rank = String(item.rank);
          socialTail.dataset.username = item.username;
          socialCard.dataset.rank = String(item.rank);
          socialCard.dataset.username = item.username;
          socialCard.addEventListener("click", (event) => {
            event.stopPropagation();
            socialCard.classList.toggle("is-react-open");
          });
          socialLayer.appendChild(socialTail);
          socialLayer.appendChild(socialCard);
        });
        cupPodium.appendChild(socialLayer);
        window.requestAnimationFrame(positionCupSocialBubbles);
        visibleUsers.forEach((item) => {
          scrollRows.appendChild(makeCupLeaderboardRow(item));
        });
        const previewOnly = users.every((item) => item.placeholder);
        cupStatus.textContent = pendingUsername
          ? "Your committed score is shown immediately; official rank will replace it after the board batch."
          : previewOnly
          ? `No ${cupTypeConfig().empty} yet; showing learners ready for the ${cupScopeLabel(currentCupScope).toLowerCase()} board.`
          : `${cupTypeTitle()} is ranked by ${cupScopeLabel(currentCupScope).toLowerCase()} progress.`;
      };

      const loadCupLeaderboard = async (force = false) => {
        if (!cupStatus) {
          return;
        }
        const now = Date.now();
        const cacheType = normalizeCupType(cupLeaderboardCache.type || currentCupType);
        const cachedRows = cacheType === currentCupType && cupLeaderboardCache.boards && cupLeaderboardCache.boards[currentCupScope];
        if (!force && Array.isArray(cachedRows) && cachedRows.length && now - cupLeaderboardCache.at < 30000) {
          preloadCupLeaderboardAssets(cupLeaderboardCache.boards || {}, cupLeaderboardCache.viewers || [], cupLeaderboardCache.chat || []);
          renderCupLeaderboard(cachedRows, currentCupScope);
          scheduleCupLeaderboardRefresh();
          return;
        }
        cupStatus.textContent = `Scanning ${cupTypeTitle().toLowerCase()}...`;
        try {
          const result = await fetchCupLeaderboardPayload(currentCupType, currentCupScope);
          const normalized = normalizeCupLeaderboardPayload(result.payload || {}, currentCupType);
          currentCupType = normalized.boardType;
          cupRewardConfig = normalized.rewardConfig;
          preloadCupLeaderboardAssets(normalized.boards, normalized.viewers, normalized.chat);
            cupLeaderboardCache = {
              at: Date.now(),
              type: currentCupType,
            boards: normalized.boards,
            users: normalized.users,
            viewers: normalized.viewers,
            myStatuses: normalized.myStatuses,
            chat: normalized.chat,
              reactionOptions: normalized.reactionOptions,
            };
            if ((normalized.boards[currentCupScope] || []).some((item) => clean(item && item.username).toLowerCase() === clean(cupPendingCompletion && cupPendingCompletion.username).toLowerCase())) {
              cupPendingCompletion = null;
            }
            renderCupLeaderboard(normalized.boards[currentCupScope] || [], currentCupScope);
        } catch (error) {
          const fallback = (cupLeaderboardCache.boards && cupLeaderboardCache.boards[currentCupScope]) || (currentCupScope === "total" ? cupLeaderboardCache.users : []) || [];
          renderCupLeaderboard(fallback, currentCupScope);
          cupStatus.textContent = error && error.message ? error.message : "Could not load leaderboard.";
        } finally {
          scheduleCupLeaderboardRefresh();
        }
      };

      const openCupLeaderboard = (options = {}) => {
        if (!cupModal) {
          return;
        }
        const opts = options && typeof options === "object" ? options : {};
        const requestedScope = clean(opts.scope || "");
        if (["total", "day", "week", "month"].includes(requestedScope)) {
          currentCupScope = requestedScope;
        }
        currentCupType = normalizeCupType(opts.type || opts.boardType || currentCupType);
        cupPendingCompletion = opts.pendingUser && typeof opts.pendingUser === "object" ? opts.pendingUser : cupPendingCompletion;
        cupCloseContinuation = typeof opts.onClose === "function" ? opts.onClose : null;
        cupModal.classList.add("is-open");
        cupModal.setAttribute("aria-hidden", "false");
        setMobileToolsOpen(false);
        if (cupStatus) {
          cupStatus.textContent = `Scanning ${cupTypeTitle().toLowerCase()}...`;
        }
        if (cupPodium) {
          cupPodium.innerHTML = "";
        }
        if (cupViewers) {
          cupViewers.innerHTML = "";
          cupViewers.classList.remove("is-visible");
        }
        if (cupList) {
          cupList.innerHTML = "";
        }
        renderCupWorldChat(cupLeaderboardCache.chat || []);
        const cachedRows = normalizeCupType(cupLeaderboardCache.type || currentCupType) === currentCupType
          ? ((cupLeaderboardCache.boards && cupLeaderboardCache.boards[currentCupScope]) || (currentCupScope === "total" ? cupLeaderboardCache.users : []) || [])
          : [];
        if (cachedRows && cachedRows.length) {
          preloadCupLeaderboardAssets(cupLeaderboardCache.boards || {}, cupLeaderboardCache.viewers || [], cupLeaderboardCache.chat || []);
          renderCupLeaderboard(cachedRows, currentCupScope);
        }
        const freshCache = cachedRows && cachedRows.length && Date.now() - cupLeaderboardCache.at < 5000;
        window.setTimeout(() => {
          void loadCupLeaderboard(!freshCache);
        }, freshCache ? 160 : 0);
        startCupWorldChatPolling();
      };

      const openCupLeaderboardAfterVocabularyComplete = () => {
        if (!cupModal) {
          return Promise.resolve(false);
        }
        return new Promise((resolve) => {
          openCupLeaderboard({
            scope: "day",
            type: "space_v",
            onClose: () => resolve(true),
          });
        });
      };

      const closeCupLeaderboard = () => {
        if (!cupModal) {
          return;
        }
        const continuation = cupCloseContinuation;
        cupCloseContinuation = null;
        stopCupLeaderboardRefresh();
        setCupTypeMenuOpen(false);
        closeCupViewerPopover();
        cupModal.classList.remove("is-open");
        cupModal.setAttribute("aria-hidden", "true");
        stopCupWorldChatPolling();
        syncCupWorldChatDebug();
        if (typeof continuation === "function") {
          window.setTimeout(() => {
            continuation();
          }, 180);
        }
      };

      document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
          stopCupWorldChatPolling();
          return;
        }
        if (cupModal && cupModal.classList.contains("is-open")) {
          startCupWorldChatPolling();
        }
      });

      syncCupWorldChatDebug();

      const inventoryCrystalTierLabel = (tone = "") => {
        switch (clean(tone).toLowerCase()) {
          case "spacev": return "Golden Axe";
          case "easy": return "Silver Axe";
          case "bookgold": return "Golden Magic Book";
          case "booksilver": return "Silver Magic Book";
          case "bowgold": return "Golden Magic Bow";
          case "bowsilver": return "Silver Magic Bow";
          case "saxgold": return "Golden Devil Wings";
          case "saxsilver": return "Silver Devil Wings";
          case "swordgold": return "Golden Great Sword";
          case "swordsilver": return "Silver Great Sword";
          case "cupgold": return "Golden Mastery Cup";
          case "cupiron": return "Silver Practice Cup";
          case "golden": return "Mythic tier";
          case "yellow": return "Legendary tier";
          case "blue": return "Epic tier";
          case "green": return "Rare tier";
          case "rare": return "Rare tier";
          case "spaceq": return "Space_Q tier";
          case "spacew": return "Space_W tier";
          case "badge": return "Champion badge";
          default: return "Reward";
        }
      };

      const renderQuestionInventoryHudItem = (item = null) => {
        const hud = ensureQuestionInventoryHud();
        const crystal = item || questionInventoryHudPreviewItem || questionInventoryCrystalSummary();
        const countNode = hud.querySelector("[data-crystal-count]");
        const nameNode = hud.querySelector("[data-crystal-name]");
        const useNode = hud.querySelector("[data-crystal-use]");
        const tierNode = hud.querySelector("[data-crystal-tier]");
        const gemNode = hud.querySelector(".ft-crystal-inventory-gem");
        const tone = inventoryCrystalToneForId(crystal.id);
        hud.classList.remove("is-yellow", "is-blue", "is-green", "is-golden", "is-spacev", "is-spaceq", "is-spacew", "is-easy", "is-rare", "is-cupgold", "is-cupiron", "is-bookgold", "is-booksilver", "is-bowgold", "is-bowsilver", "is-saxgold", "is-saxsilver", "is-swordgold", "is-swordsilver", "is-badge", "is-prism");
        if (tone) {
          hud.classList.add(`is-${tone}`);
        }
        if (gemNode) {
          gemNode.classList.remove("is-yellow", "is-blue", "is-green", "is-golden", "is-spacev", "is-spaceq", "is-spacew", "is-easy", "is-rare", "is-cupgold", "is-cupiron", "is-bookgold", "is-booksilver", "is-bowgold", "is-bowsilver", "is-saxgold", "is-saxsilver", "is-swordgold", "is-swordsilver", "is-badge", "is-prism");
          if (tone) {
            gemNode.classList.add(`is-${tone}`);
          }
        }
        if (tierNode) {
          tierNode.textContent = inventoryCrystalTierLabel(tone);
        }
        if (countNode) {
          countNode.textContent = String(crystal.quantity);
        }
        if (nameNode) {
          nameNode.textContent = crystal.name;
        }
        if (useNode) {
          useNode.textContent = crystal.use;
        }
        return hud;
      };

      const updateQuestionInventoryHud = (item = null) => {
        if (item || questionInventoryHudPreviewItem || (questionInventoryHud && questionInventoryHud.classList.contains("is-live"))) {
          renderQuestionInventoryHudItem(item || questionInventoryHudPreviewItem);
        }
        if (inventoryModal && inventoryModal.classList.contains("is-open")) {
          renderQuestionInventoryPopup();
        }
      };

      const hideQuestionInventoryAwardHud = () => {
        if (questionInventoryHudTimer) {
          window.clearTimeout(questionInventoryHudTimer);
          questionInventoryHudTimer = 0;
        }
        questionInventoryHudPreviewItem = null;
        if (questionInventoryHud) {
          questionInventoryHud.classList.remove("is-live");
        }
      };

      const showQuestionInventoryAwardHud = (item = null) => {
        if (!item) {
          return;
        }
        const previewId = clean(item.id || "crystal").toLowerCase() || "crystal";
        questionInventoryHudPreviewItem = {
          id: previewId,
          name: canonicalRewardName(previewId, item.name),
          use: canonicalRewardUse(previewId, item.use),
          quantity: Math.max(0, Math.floor(Number(item.quantity || 0) || 0)),
        };
        const hud = renderQuestionInventoryHudItem(questionInventoryHudPreviewItem);
        hud.classList.remove("is-live", "is-celebrating");
        void hud.offsetWidth;
        hud.classList.add("is-live", "is-celebrating");
        window.setTimeout(() => {
          if (hud) {
            hud.classList.remove("is-celebrating");
          }
        }, 1500);
        if (questionInventoryHudTimer) {
          window.clearTimeout(questionInventoryHudTimer);
        }
        questionInventoryHudTimer = window.setTimeout(() => {
          questionInventoryHudTimer = 0;
          questionInventoryHudPreviewItem = null;
          if (questionInventoryHud) {
            questionInventoryHud.classList.remove("is-live");
          }
        }, 2000);
      };

      const setQuestionInventoryHudVisible = (visible) => {
        if (!visible) {
          hideQuestionInventoryAwardHud();
        } else {
          ensureQuestionInventoryHud();
        }
      };

      const questionRewardLessonIdentity = () => {
        const source = currentLessonSource || {};
        return clean(source.path || source.name || source.title || (questionPayload && questionPayload.title) || "space-q");
      };

      const questionRewardEventKey = (kind = "root", path = "") => {
        const node = questionCurrentNode || {};
        const item = currentQuestionItem ? currentQuestionItem() : null;
        const nodeIndex = Math.max(0, Math.floor(Number(currentNodeIndex || 0) || 0));
        const questionOrderIndex = (
          Array.isArray(questionCurrentQuestionOrder)
          && Number.isFinite(Number(questionQuestionIndex))
          && questionQuestionIndex >= 0
          && questionQuestionIndex < questionCurrentQuestionOrder.length
        )
          ? Math.max(0, Math.floor(Number(questionCurrentQuestionOrder[questionQuestionIndex]) || 0))
          : Math.max(0, Math.floor(Number(questionQuestionIndex || 0) || 0));
        const raw = [
          questionRewardLessonIdentity(),
          clean(node.id || node.root || (questionCardData(node, "root") || {}).text || `node-${nodeIndex + 1}`),
          nodeIndex,
          questionOrderIndex,
          clean(item && (item.id || item.question || item.answer) || "question"),
          clean(kind || "root"),
          clean(path || ""),
        ].join("|");
        return `space-q:${hashSpaceWText(raw)}`;
      };

      const animateQuestionCrystalReward = (sourceNode = null, tone = "") => {
        const rect = sourceNode && sourceNode.getBoundingClientRect ? sourceNode.getBoundingClientRect() : null;
        const x = rect && rect.width ? rect.left + rect.width / 2 : (window.innerWidth || 0) / 2;
        const y = rect && rect.height ? rect.top + rect.height / 2 : (window.innerHeight || 0) / 2;
        const burst = document.createElement("span");
        burst.className = "ft-crystal-burst";
        const safeTone = inventoryCrystalToneForId(tone);
        if (safeTone) {
          burst.classList.add(`is-${safeTone}`);
        }
        burst.style.setProperty("--crystal-x", `${x}px`);
        burst.style.setProperty("--crystal-y", `${y}px`);
        burst.setAttribute("aria-hidden", "true");
        document.body.appendChild(burst);
        window.setTimeout(() => {
          if (burst.parentNode) {
            burst.parentNode.removeChild(burst);
          }
        }, 1500);
      };

      const queueQuestionInventorySync = (delay = 1200) => {
        if (questionInventorySyncTimer) {
          window.clearTimeout(questionInventorySyncTimer);
        }
        questionInventorySyncTimer = window.setTimeout(() => {
          questionInventorySyncTimer = 0;
          void flushQuestionInventoryQueue();
        }, Math.max(0, Number(delay) || 0));
      };

      const loadQuestionInventory = async () => {
        questionInventoryState = readLocalQuestionInventory();
        updateQuestionInventoryHud();
        if (!authToken) {
          return questionInventoryState;
        }
        try {
          const result = await fetchServerJson("/inventory?response=compact-v1");
          const serverInventory = result.payload && result.payload.inventory ? result.payload.inventory : {};
          questionInventoryState = writeLocalQuestionInventory(mergeQuestionInventoryState(questionInventoryState, serverInventory));
          queueQuestionInventorySync(260);
        } catch (error) {
        }
        return questionInventoryState;
      };

      async function flushQuestionInventoryQueue() {
        if (questionInventorySyncBusy || !authToken) {
          return false;
        }
        questionInventoryState = readLocalQuestionInventory();
        const pending = Array.isArray(questionInventoryState.pending) ? questionInventoryState.pending.slice() : [];
        if (!pending.length) {
          updateQuestionInventoryHud();
          return true;
        }
        questionInventorySyncBusy = true;
        const remaining = [];
        try {
          for (const entry of pending) {
            try {
              const result = await fetchServerJson("/inventory/award?response=delta-v1", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(entry),
              });
              const serverInventory = result.payload && result.payload.inventory ? result.payload.inventory : {};
              questionInventoryState = clean(result.payload && result.payload.response_schema) === "inventory-delta-v1"
                ? applyQuestionInventoryDelta(questionInventoryState, serverInventory)
                : result.payload && result.payload.awarded === false
                ? normalizeQuestionInventoryState({ ...serverInventory, pending: questionInventoryState.pending })
                : mergeQuestionInventoryState(questionInventoryState, serverInventory);
            } catch (error) {
              remaining.push(entry);
            }
          }
          questionInventoryState.pending = remaining;
          writeLocalQuestionInventory(questionInventoryState);
        } finally {
          questionInventorySyncBusy = false;
        }
        if (remaining.length) {
          queueQuestionInventorySync(8000);
        }
        return !remaining.length;
      }

      const awardInventoryItemOnce = (eventKey, itemConfig = {}, sourceNode = null, options = {}) => {
        const key = clean(eventKey);
        if (!key) {
          return false;
        }
        questionInventoryState = readLocalQuestionInventory();
        const seen = new Set([...(questionInventoryState.events || []), ...Array.from(questionCrystalAwardedKeys)].map(clean).filter(Boolean));
        if (seen.has(key)) {
          return false;
        }
        questionCrystalAwardedKeys.add(key);
        questionInventoryState.events = Array.from(new Set([...(questionInventoryState.events || []), key])).slice(-512);
        const crystal = itemConfig && typeof itemConfig === "object" && clean(itemConfig.id)
          ? itemConfig
          : (questionRewardConfig && questionRewardConfig.crystal ? questionRewardConfig.crystal : normalizeQuestionRewards({}).crystal);
        const itemId = clean(crystal.id || "crystal").toLowerCase() || "crystal";
        const canonicalName = canonicalRewardName(itemId, crystal.name);
        const canonicalUse = canonicalRewardUse(itemId, crystal.use);
        const current = questionInventoryState.items[itemId] || {
          id: itemId,
          name: canonicalName,
          use: canonicalUse,
          quantity: 0,
        };
        questionInventoryState.items[itemId] = {
          ...current,
          id: itemId,
          name: canonicalName,
          use: canonicalUse,
          quantity: Math.max(0, Math.floor(Number(current.quantity || 0) || 0)) + 1,
          updated_at: new Date().toISOString(),
        };
        const awardPayload = {
          event_id: key,
          quantity: 1,
          item: questionInventoryState.items[itemId],
          lesson: questionRewardLessonIdentity(),
        };
        questionInventoryState.pending = [...(questionInventoryState.pending || []), awardPayload].slice(-500);
        writeLocalQuestionInventory(questionInventoryState);
        recordCurrentMissionCrystalAward(questionInventoryState.items[itemId]);
        showQuestionInventoryAwardHud(questionInventoryState.items[itemId]);
        animateQuestionCrystalReward(sourceNode, options.tone || itemId);
        if (typeof options.feedback === "function") {
          options.feedback(questionInventoryState.items[itemId]);
        } else {
          setQuestionFeedback(`Reward obtained: ${canonicalRewardName(itemId, questionInventoryState.items[itemId].name)}`, "ok");
        }
        queueQuestionInventorySync(authToken ? 120 : 4000);
        return true;
      };

      const awardQuestionCrystalOnce = (eventKey, sourceNode = null) => {
        const crystal = questionRewardConfig && questionRewardConfig.crystal ? questionRewardConfig.crystal : normalizeQuestionRewards({}).crystal;
        return awardInventoryItemOnce(eventKey, crystal, sourceNode, {
          tone: clean(crystal.id || "crystal"),
        });
      };

      const questionNodeBookConfig = (variant = "gold") => {
        const rewards = questionRewardConfig && typeof questionRewardConfig === "object" ? questionRewardConfig : normalizeQuestionRewards({});
        if (variant === "silver") {
          return (rewards.node_review && typeof rewards.node_review === "object")
            ? rewards.node_review
            : normalizeQuestionRewards({}).node_review;
        }
        return (rewards.node_new && typeof rewards.node_new === "object")
          ? rewards.node_new
          : normalizeQuestionRewards({}).node_new;
      };

      const questionBookRewardVariant = (variant = "") => (
        clean(variant || (questionReviewRunActive ? "silver" : "gold")) === "silver" ? "silver" : "gold"
      );

      const questionBookRewardEventKey = (options = {}) => {
        const variant = questionBookRewardVariant(options && options.variant);
        const kind = clean(options && options.kind) || "question";
        const path = clean(options && options.path) || "";
        return questionRewardEventKey(`book:${kind}:${variant}`, path);
      };

      const awardQuestionBookOnce = (sourceNode = null, options = {}) => {
        const variant = questionBookRewardVariant(options && options.variant);
        const config = questionNodeBookConfig(variant);
        const tone = variant === "silver" ? "booksilver" : "bookgold";
        return awardInventoryItemOnce(questionBookRewardEventKey(options), config, sourceNode, {
          tone,
          feedback: typeof (options && options.feedback) === "function" ? options.feedback : (() => {}),
        });
      };

      const hideVocabPreflightGate = () => {
        if (vocabPreflightGate) {
          vocabPreflightGate.hidden = true;
        }
        vocabPreflightBusy = false;
        if (vocabPreflightLearn) {
          vocabPreflightLearn.disabled = false;
        }
        if (vocabPreflightSkip) {
          vocabPreflightSkip.disabled = false;
        }
      };

      const normalizeVocabPreflightPath = (path = "") => clean(path).replace(/\\/g, "/");

      const forgetVocabPreflightDecisionForPath = (path = "") => {
        const sourcePath = normalizeVocabPreflightPath(path);
        if (!sourcePath) {
          return;
        }
        spaceWVocabSkipPaths.delete(sourcePath);
        spaceWVocabClearedPaths.delete(sourcePath);
        if (normalizeVocabPreflightPath(spaceWVocabBuildGuardPath) === sourcePath) {
          spaceWVocabBuildGuardPath = "";
        }
      };

      const resetVocabPreflightSessionMemory = () => {
        vocabPreflightBuildToken += 1;
        spaceWVocabBuildGuardPath = "";
        spaceWVocabSkipPaths = new Set();
        spaceWVocabClearedPaths = new Set();
      };

      const setVocabPreflightStatus = (message = "", isError = false) => {
        if (!vocabPreflightStatus) {
          return;
        }
        vocabPreflightStatus.textContent = message;
        vocabPreflightStatus.classList.toggle("is-error", Boolean(isError));
      };

      const setVocabPreflightBusy = (busy, message = "") => {
        vocabPreflightBusy = Boolean(busy);
        if (vocabPreflightLearn) {
          vocabPreflightLearn.disabled = vocabPreflightBusy;
        }
        if (vocabPreflightSkip) {
          vocabPreflightSkip.disabled = vocabPreflightBusy;
        }
        if (message) {
          setVocabPreflightStatus(message);
        }
      };

      const showVocabPreflightGate = (payload = {}, mode = "preflight") => {
        if (!vocabPreflightGate) {
          return;
        }
        vocabPreflightState = { ...(payload || {}), mode };
        const pending = Array.isArray(payload.pending_files) ? payload.pending_files : [];
        const files = Array.isArray(payload.files) ? payload.files : pending;
        const pendingOriginal = pendingSpaceWAfterVocabulary || {};
        const spaceLabel = vocabPreflightSpaceLabel(payload.space || pendingOriginal.space || "Space_W");
        const newCount = Number(payload.new_count || 0) || 0;
        const pendingCount = Number(payload.pending_count || files.length || pending.length || 0) || 0;
        const filesNeeded = Number(payload.files_needed || pendingCount || files.length || 0) || 0;
        if (vocabPreflightCount) {
          vocabPreflightCount.textContent = String(mode === "queue" ? pendingCount : newCount);
        }
        if (vocabPreflightFiles) {
          const count = mode === "queue" ? pendingCount : (pendingCount || filesNeeded);
          vocabPreflightFiles.textContent = count === 1 ? "1 pack" : `${count} packs`;
        }
        if (vocabPreflightRemaining) {
          vocabPreflightRemaining.textContent = mode === "queue"
            ? `${pendingCount} remaining before ${spaceLabel}`
            : (pendingCount ? "Mission queue ready" : `${newCount} new words`);
        }
        if (vocabPreflightTitle) {
          vocabPreflightTitle.textContent = mode === "queue" ? "Vocabulary pack synced" : "New words detected";
        }
        if (vocabPreflightText) {
          vocabPreflightText.textContent = mode === "queue"
            ? `This vocabulary pack is complete. Continue the next queued pack, or open the ${spaceLabel} lesson now.`
            : `The server found ${newCount} new ${newCount === 1 ? "word" : "words"} for this ${spaceLabel} mission. Learn them first for a cleaner run.`;
        }
        if (vocabPreflightLearn) {
          vocabPreflightLearn.textContent = mode === "queue" ? "Continue next vocabulary pack" : "Learn vocabulary first";
        }
        if (vocabPreflightSkip) {
          vocabPreflightSkip.textContent = mode === "queue" ? `Open ${spaceLabel} now` : "Skip vocabulary and continue";
        }
        setVocabPreflightStatus("");
        setVocabPreflightBusy(false);
        vocabPreflightGate.hidden = false;
        window.setTimeout(() => {
          try {
            vocabPreflightLearn && vocabPreflightLearn.focus({ preventScroll: true });
          } catch (error) {
          }
        }, 40);
      };

      const vocabPreflightSpaceLabel = (value = "") => {
        const raw = clean(value).toLowerCase();
        if (raw.includes("space_q") || raw === "q") {
          return "Space_Q";
        }
        if (raw.includes("space_p") || raw.includes("paragraph") || raw === "p") {
          return "Space_P";
        }
        if (raw.includes("space_s") || raw === "s") {
          return "Space_S";
        }
        if (raw.includes("space_l") || raw === "l") {
          return "Space_L";
        }
        return "Space_W";
      };

      const vocabPreflightPayloadSpace = (payload = {}, path = "") => {
        const sourcePath = normalizeVocabPreflightPath(path);
        const payloadSpaceMode = clean(payload && (payload.space_mode || payload.spaceMode || payload.mode || payload.sm || "")).toLowerCase();
        if (/\.space_l$/i.test(sourcePath) || payloadSpaceMode === "space_l") {
          return "Space_L";
        }
        if (/\.space_q$/i.test(sourcePath) || payloadSpaceMode === "space_q" || isQuestionPayload(payload)) {
          return "Space_Q";
        }
        if (/\.space_s$/i.test(sourcePath)) {
          return "Space_S";
        }
        if (payloadSpaceMode === "space_s") {
          return "Space_S";
        }
        if (isParagraphPayload(payload) || /\.space_p$/i.test(sourcePath)) {
          return "Space_P";
        }
        return "Space_W";
      };

      const shouldRunSpaceWVocabPreflight = (payload = {}) => {
        const path = normalizeVocabPreflightPath(currentLessonSource && currentLessonSource.path);
        if (!authToken || !currentAuthUsername || !path || !/\.space_[wqpsl]$/i.test(path)) {
          return false;
        }
        if (spaceWVocabSkipPaths.has(path) || spaceWVocabClearedPaths.has(path)) {
          return false;
        }
        if (isVocabularyPayload(payload)) {
          return false;
        }
        return true;
      };

      const runSpaceWVocabPreflight = async (payload, selectedVoiceValue = "", resumeOptions = {}) => {
        const source = { ...(currentLessonSource || {}) };
        const sourcePath = normalizeVocabPreflightPath(source.path);
        const spaceLabel = vocabPreflightPayloadSpace(payload, sourcePath);
        const scanToken = ++vocabPreflightBuildToken;
        pendingSpaceWAfterVocabulary = { payload, selectedVoiceValue, source, space: spaceLabel, resumeOptions: { ...(resumeOptions || {}) } };
        setLoadStatus(`Scanning ${spaceLabel} vocabulary mission...`);
        try {
          const result = await fetchServerJson("/vocab/scan-space-w?response=compact-v1", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            timeoutMs: 30000,
            body: JSON.stringify({ path: sourcePath }),
          });
          if (scanToken !== vocabPreflightBuildToken || normalizeVocabPreflightPath(currentLessonSource && currentLessonSource.path) !== sourcePath) {
            return;
          }
          const scan = result.payload || {};
          const pendingCount = Number(scan.pending_count || 0) || 0;
          const newCount = Number(scan.new_count || 0) || 0;
          if (!pendingCount && !newCount) {
            spaceWVocabClearedPaths.add(sourcePath);
            pendingSpaceWAfterVocabulary = null;
            if (isQuestionPayload(payload)) {
              await enterQuestionPayloadNow(payload, { ...(resumeOptions || {}), allowDuringVocabBuild: true });
            } else if (isParagraphPayload(payload)) {
              await enterParagraphPayloadNow(payload, { ...(resumeOptions || {}), allowDuringVocabBuild: true });
            } else {
              await startTranslationLessonPayload(payload, selectedVoiceValue);
            }
            return;
          }
          loadGate.classList.add("is-hidden");
          showVocabPreflightGate(scan, "preflight");
        } catch (error) {
          if (scanToken !== vocabPreflightBuildToken || normalizeVocabPreflightPath(currentLessonSource && currentLessonSource.path) !== sourcePath) {
            return;
          }
          setLoadStatus(`Vocabulary preflight skipped: ${error && error.message ? error.message : error}`, true);
          pendingSpaceWAfterVocabulary = null;
          spaceWVocabSkipPaths.add(sourcePath);
          if (isQuestionPayload(payload)) {
            await enterQuestionPayloadNow(payload, { ...(resumeOptions || {}), allowDuringVocabBuild: true });
          } else if (isParagraphPayload(payload)) {
            await enterParagraphPayloadNow(payload, { ...(resumeOptions || {}), allowDuringVocabBuild: true });
          } else {
            await startTranslationLessonPayload(payload, selectedVoiceValue, { allowDuringVocabBuild: true });
          }
        }
      };

      const loadVocabularyMissionFile = async (fileRecord = {}) => {
        const path = clean(fileRecord.path);
        if (!path) {
          throw new Error("Vocabulary mission file is missing.");
        }
        setVocabPreflightBusy(true, "Loading vocabulary pack...");
        const result = await fetchServerText(`/server-data/file?path=${encodeURIComponent(path)}`);
        const text = String(result.text || "").replace(/^\uFEFF/, "");
        const payload = await decodeFuturePayload(text);
        setCurrentLessonSource({
          source: "server",
          path,
          name: clean(fileRecord.name) || path.split("/").pop(),
          study: fileRecord.study || null,
        }, payload);
        rememberServerFile({
          ...fileRecord,
          path,
        }, { syncNow: true });
        hideVocabPreflightGate();
        await enterVocabularyPayloadNow(payload);
      };

