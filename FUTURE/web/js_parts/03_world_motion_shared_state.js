

      const renderSharedWorldTrainingPlayerVitals = (stats = {}, arena = {}) => {
        const key = (clean(activeWorldUsername() || currentAuthUsername || "learner") || "learner").toLowerCase();
        const node = sharedWorldNodes.get(key) || (ensureSharedWorldSelfNode() || {}).node;
        if (!node) {
          return;
        }
        renderSharedWorldLevel(node, stats);
        let vitals = node.querySelector(".ft-world-training-vitals");
        if (!vitals) {
          vitals = document.createElement("div");
          vitals.className = "ft-world-training-vitals";
          node.appendChild(vitals);
        }
        const hp = Math.max(0, Math.floor(Number(arena.player_hp || arena.playerHp || stats.max_hp || 100) || 0));
        const maxHp = Math.max(1, Math.floor(Number(stats.max_hp || stats.maxHp || 100) || 100));
        const mana = Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0));
        const maxMana = Math.max(1, Math.floor(Number(stats.max_mana || stats.maxMana || 60) || 60));
        vitals.innerHTML = `
          <span class="ft-world-training-vital" title="HP ${hp}/${maxHp}"><i style="--bar:${sharedWorldTrainingPercent(hp, maxHp)};--bar-a:#ff675d;--bar-b:#ffd166;--bar-glow:rgba(255,103,93,.36)"></i></span>
          <span class="ft-world-training-vital" title="Mana ${mana}/${maxMana}"><i style="--bar:${sharedWorldTrainingPercent(mana, maxMana)};--bar-a:#46f0d7;--bar-b:#7cfff0;--bar-glow:rgba(70,240,215,.36)"></i></span>
        `;
      };

      const renderSharedWorldTrainingStats = (stats = {}, arena = {}) => {
        if (!worldTrainingStats) {
          return;
        }
        const hp = Math.max(0, Math.floor(Number(arena.player_hp || arena.playerHp || stats.max_hp || 100) || 0));
        const maxHp = Math.max(1, Math.floor(Number(stats.max_hp || stats.maxHp || 100) || 100));
        const mana = Math.max(0, Math.floor(Number(arena.player_mana || arena.playerMana || 0) || 0));
        const maxMana = Math.max(1, Math.floor(Number(stats.max_mana || stats.maxMana || 60) || 60));
        const points = Math.max(0, Math.floor(Number(stats.available_points || stats.availablePoints || 0) || 0));
        const rows = sharedWorldTrainingStatRows(stats);
        worldTrainingStats.innerHTML = `
          <div class="ft-world-training-stat-title">Character core</div>
          <div class="ft-world-training-player-bars">
            <div class="ft-world-training-bar" style="--bar:${sharedWorldTrainingPercent(hp, maxHp)};--bar-a:#ff675d;--bar-b:#ffd166"><span>HP ${hp}/${maxHp}</span><span></span></div>
            <div class="ft-world-training-bar" style="--bar:${sharedWorldTrainingPercent(mana, maxMana)};--bar-a:#46f0d7;--bar-b:#7cfff0"><span>Mana ${mana}/${maxMana}</span><span></span></div>
          </div>
          <div class="ft-world-training-stat-title">Lv ${Math.max(1, Math.floor(Number(stats.level || 1) || 1))} upgrade points: ${points}</div>
          <div class="ft-world-training-upgrades">
            ${rows.map(([key, label, value, title]) => `
              <div class="ft-world-training-upgrade">
                <span><b>${label}</b><small title="${title}"> ${Math.max(0, Math.floor(Number(value || 0) || 0))}</small></span>
                <button type="button" data-world-training-stat="${key}" ${points <= 0 ? "disabled" : ""}>+</button>
              </div>
            `).join("")}
          </div>
        `;
        renderSharedWorldTrainingLoadoutPanel();
        renderSharedWorldTrainingQuickSkill();
        renderSharedWorldTrainingPlayerVitals(stats, arena);
      };

      const renderSharedWorldTrainingSlimes = (arena = {}) => {
        const host = sharedWorldTrainingSlimeHost();
        if (!host) {
          return;
        }
        const selectedId = clean(arena.selected_id || arena.selectedId || "");
        const slimes = Array.isArray(arena.slimes) ? arena.slimes : [];
        [worldTrainingSlimes, worldTrainingMapSlimes].forEach((node) => {
          if (node && node !== host) {
            node.innerHTML = "";
          }
        });
        const seen = new Set();
        slimes.forEach((slime, index) => {
          const row = slime && typeof slime === "object" ? slime : {};
          const hp = Math.max(0, Math.floor(Number(row.hp || 0) || 0));
          const maxHp = Math.max(1, Math.floor(Number(row.max_hp || row.maxHp || hp || 1) || 1));
          const mana = Math.max(0, Math.floor(Number(row.mana || row.mp || 0) || 0));
          const maxMana = Math.max(1, Math.floor(Number(row.max_mana || row.maxMana || 1) || 1));
          const id = clean(row.id || `slime_${index + 1}`);
          if (!id) {
            return;
          }
          seen.add(id);
          const x = Math.max(4, Math.min(96, sharedWorldClamp(row.tx != null ? row.tx : row.x) * 100));
          const y = Math.max(8, Math.min(72, sharedWorldClamp(row.ty != null ? row.ty : row.y) * 100));
          let button = Array.from(host.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset.slimeId || "") === id);
          const previousX = Number(button && button.dataset.slimeX);
          const previousY = Number(button && button.dataset.slimeY);
          if (!button) {
            button = document.createElement("button");
            button.type = "button";
            button.className = "ft-world-training-slime";
            host.appendChild(button);
          }
          button.dataset.slimeId = id;
          button.dataset.slimeX = x.toFixed(2);
          button.dataset.slimeY = y.toFixed(2);
          button.style.setProperty("--slime-x", x.toFixed(2));
          button.style.setProperty("--slime-y", y.toFixed(2));
          button.title = `${clean(row.name || "Slime")} Lv ${Math.max(1, Math.floor(Number(row.level || 1) || 1))} - click to target`;
          const isSelected = id === selectedId;
          button.classList.toggle("is-selected", isSelected);
          button.classList.toggle("is-defeated", hp <= 0);
          const moved = Number.isFinite(previousX) && Number.isFinite(previousY) && (Math.abs(previousX - x) > 0.5 || Math.abs(previousY - y) > 0.5);
          if (moved && hp > 0) {
            button.classList.add("is-hopping");
            window.clearTimeout(button._worldTrainingHopTimer);
            button._worldTrainingHopTimer = window.setTimeout(() => {
              button.classList.remove("is-hopping");
              button._worldTrainingHopTimer = 0;
            }, 1120);
          }
          const qMeta = sharedWorldTrainingQuestionVisualMeta(row.question);
          button.classList.remove("is-kind-word", "is-kind-sentence", "is-kind-audio", "is-kind-translate", "is-enemy-fangbeast");
          button.classList.add(qMeta.kindClass || "is-kind-word");
          if (qMeta.enemyClass) {
            button.classList.add(qMeta.enemyClass);
          }
          button.innerHTML = `
            <span class="ft-world-training-slime-bubble"><b>${qMeta.main}</b><small>${qMeta.meta}</small></span>
            <span class="ft-world-training-slime-focus-arrow" aria-hidden="true"></span>
            <span class="ft-world-training-slime-crest" aria-hidden="true"></span>
            <span class="ft-world-training-slime-core" aria-hidden="true"></span>
            <span class="ft-world-training-slime-fangs" aria-hidden="true"></span>
            <span class="ft-world-training-slime-stun" aria-hidden="true"></span>
            <span class="ft-world-training-slime-name"><b>${clean(row.name || "Slime")}</b><span>Lv ${Math.max(1, Math.floor(Number(row.level || 1) || 1))}</span></span>
            <span class="ft-world-training-mini-bars">
              <span class="ft-world-training-mini-bar" title="HP"><i style="--bar:${sharedWorldTrainingPercent(hp, maxHp)};--bar-a:#ff675d;--bar-b:#ffd166"></i></span>
              <span class="ft-world-training-mini-bar" title="Mana"><i style="--bar:${sharedWorldTrainingPercent(mana, maxMana)};--bar-a:#46f0d7;--bar-b:#7cfff0"></i></span>
            </span>
          `;
          window.requestAnimationFrame(() => {
            const bubble = button.querySelector(".ft-world-training-slime-bubble");
            if (!bubble) {
              return;
            }
            const bubbleHeight = Math.max(32, Number(bubble.offsetHeight || 0));
            button.style.setProperty("--slime-arrow-top", `${Math.round(-bubbleHeight - 24)}px`);
          });
        });
        Array.from(host.querySelectorAll("[data-slime-id]")).forEach((node) => {
          if (!seen.has(clean(node.dataset.slimeId || ""))) {
            node.remove();
          }
        });
      };

      const syncSharedWorldTrainingFocusedSlimeAnchor = (slime = null, options = {}) => {
        if (!slime || sharedWorldMapMode !== "training" || !sharedWorldTrainingIsActive()) {
          return;
        }
        const row = slime && typeof slime === "object" ? slime : {};
        const hp = Math.max(0, Math.floor(Number(row.hp || 0) || 0));
        const id = clean(row.id || "");
        if (!id || hp <= 0) {
          return;
        }
        const force = Boolean(options && options.force);
        const now = Date.now();
        if (!force && now - sharedWorldTrainingAnchorSyncAt < 900) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        const anchorX = sharedWorldClamp(self.tx != null ? self.tx : self.x);
        const anchorY = sharedWorldClamp(self.ty != null ? self.ty : self.y);
        const currentAnchorX = sharedWorldClamp(row.focus_anchor_x != null ? row.focus_anchor_x : row.focusAnchorX, anchorX);
        const currentAnchorY = sharedWorldClamp(row.focus_anchor_y != null ? row.focus_anchor_y : row.focusAnchorY, anchorY);
        const moved = Math.hypot(anchorX - currentAnchorX, anchorY - currentAnchorY) > 0.012;
        if (!force && !moved) {
          return;
        }
        sharedWorldTrainingAnchorSyncAt = now;
        const arenaWidth = Math.max(1, Number(worldArena && worldArena.scrollWidth || 1800));
        const arenaHeight = Math.max(1, Number(worldArena && worldArena.scrollHeight || 1160));
        const radiusX = Math.max(0.025, Math.min(0.18, 200 / arenaWidth));
        const radiusY = Math.max(0.035, Math.min(0.22, 200 / arenaHeight));
        const angle = Math.random() * Math.PI * 2;
        const spread = 0.45 + Math.random() * 0.55;
        const targetX = sharedWorldClamp(anchorX + Math.cos(angle) * radiusX * spread, anchorX);
        const targetY = sharedWorldClamp(anchorY + Math.sin(angle) * radiusY * spread, anchorY);
        row.focus_anchor_x = anchorX;
        row.focus_anchor_y = anchorY;
        row.tx = targetX;
        row.ty = targetY;
        const host = sharedWorldTrainingSlimeHost();
        const node = host && Array.from(host.querySelectorAll("[data-slime-id]"))
          .find((item) => clean(item.dataset.slimeId || "") === id);
        if (node) {
          const x = Math.max(4, Math.min(96, targetX * 100));
          const y = Math.max(8, Math.min(72, targetY * 100));
          node.dataset.slimeX = x.toFixed(2);
          node.dataset.slimeY = y.toFixed(2);
          node.style.setProperty("--slime-x", x.toFixed(2));
          node.style.setProperty("--slime-y", y.toFixed(2));
        }
      };

      const stepSharedWorldTrainingLocalSlimes = () => {
        if (!sharedWorldTrainingIsActive()) {
          return;
        }
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : {};
        const slimes = Array.isArray(arena.slimes) ? arena.slimes : [];
        if (!slimes.length) {
          return;
        }
        const now = Date.now();
        slimes.forEach((slime) => {
          const row = slime && typeof slime === "object" ? slime : {};
          const id = clean(row.id || "");
          const hp = Math.max(0, Math.floor(Number(row.hp || 0) || 0));
          if (!id || hp <= 0) {
            return;
          }
          if (!Number.isFinite(Number(row._localMoveAt || 0))) {
            row._localMoveAt = now + 600 + Math.random() * 2600;
            return;
          }
          if (now < Number(row._localMoveAt || 0)) {
            return;
          }
          row._localMoveAt = now + 2600 + Math.random() * 4200;
          const baseX = sharedWorldClamp(row.tx != null ? row.tx : row.x);
          const baseY = sharedWorldClamp(row.ty != null ? row.ty : row.y);
          const angle = Math.random() * Math.PI * 2;
          const distanceX = 0.025 + Math.random() * 0.035;
          const distanceY = 0.018 + Math.random() * 0.03;
          row.tx = sharedWorldClamp(baseX + Math.cos(angle) * distanceX, baseX);
          row.ty = sharedWorldClamp(baseY + Math.sin(angle) * distanceY, baseY);
        });
        renderSharedWorldTrainingSlimes(arena);
      };

      const startSharedWorldTrainingLocalMotion = () => {
        stopSharedWorldTrainingLocalMotion();
        stepSharedWorldTrainingLocalSlimes();
        sharedWorldTrainingLocalMotionTimer = window.setInterval(stepSharedWorldTrainingLocalSlimes, 700);
      };

      const stopSharedWorldTrainingLocalMotion = () => {
        if (sharedWorldTrainingLocalMotionTimer) {
          window.clearInterval(sharedWorldTrainingLocalMotionTimer);
          sharedWorldTrainingLocalMotionTimer = 0;
        }
      };

      const renderSharedWorldTrainingLog = (arena = {}) => {
        if (!worldTrainingLog) {
          return;
        }
        const log = Array.isArray(arena.log) ? arena.log : [];
        worldTrainingLog.innerHTML = "";
        log.slice(-10).reverse().forEach((item) => {
          const row = item && typeof item === "object" ? item : {};
          const node = document.createElement("div");
          const type = clean(row.type || "");
          node.classList.toggle("is-hit", type === "hit" || type === "clear");
          node.classList.toggle("is-hurt", type === "hurt" || type === "restore");
          node.textContent = clean(row.text || row.message || "Practice log updated.");
          worldTrainingLog.appendChild(node);
        });
      };

      const createSharedWorldTrainingGhostSlime = (event = {}, options = {}) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return null;
        }
        const x = Math.max(4, Math.min(96, sharedWorldClamp(event.slime_x != null ? event.slime_x : event.slimeX, 0.5) * 100));
        const y = Math.max(8, Math.min(72, sharedWorldClamp(event.slime_y != null ? event.slime_y : event.slimeY, 0.5) * 100));
        const defeated = options && Object.prototype.hasOwnProperty.call(options, "defeated") ? Boolean(options.defeated) : true;
        const ghost = document.createElement("span");
        ghost.className = `ft-world-training-slime ${defeated ? "is-defeated" : "is-hurt"}`;
        ghost.dataset.slimeId = clean(event.slime_id || event.slimeId || "defeated-slime");
        ghost.dataset.slimeX = x.toFixed(2);
        ghost.dataset.slimeY = y.toFixed(2);
        ghost.style.setProperty("--slime-x", x.toFixed(2));
        ghost.style.setProperty("--slime-y", y.toFixed(2));
        ghost.innerHTML = `
          <span class="ft-world-training-slime-core" aria-hidden="true"></span>
          <span class="ft-world-training-slime-name"><b>${escapeHtml(clean(event.slime_name || event.slimeName || "Slime"))}</b><span>Lv ${Math.max(1, Math.floor(Number(event.slime_level || event.slimeLevel || 1) || 1))}</span></span>
        `;
        effectHost.appendChild(ghost);
        window.setTimeout(() => ghost.remove(), defeated ? 1550 : 1220);
        return ghost;
      };

      const sharedWorldTrainingEffectSize = () => {
        const effectHost = sharedWorldTrainingEffectHost();
        const fallback = worldTrainingField || worldArena;
        return {
          host: effectHost,
          width: Math.max(1, Number((effectHost && effectHost.clientWidth) || (fallback && fallback.clientWidth) || (worldArena && worldArena.scrollWidth) || 1)),
          height: Math.max(1, Number((effectHost && effectHost.clientHeight) || (fallback && fallback.clientHeight) || (worldArena && worldArena.scrollHeight) || 1)),
        };
      };

      const sharedWorldTrainingPointFromNormalized = (x = 0.5, y = 0.5) => {
        const size = sharedWorldTrainingEffectSize();
        return {
          x: sharedWorldClamp(x, 0.5) * size.width,
          y: sharedWorldClamp(y, 0.5) * size.height,
        };
      };

      const sharedWorldTrainingNodePoint = (node, yRatio = 0.32) => {
        const size = sharedWorldTrainingEffectSize();
        if (!node || !size.host) {
          return { x: size.width * 0.5, y: size.height * 0.5 };
        }
        const rawX = Number(node.dataset && node.dataset.slimeX);
        const rawY = Number(node.dataset && node.dataset.slimeY);
        if (Number.isFinite(rawX) && Number.isFinite(rawY)) {
          return {
            x: Math.max(0, Math.min(size.width, (rawX / 100) * size.width)),
            y: Math.max(0, Math.min(size.height, (rawY / 100) * size.height)),
          };
        }
        const hostRect = size.host.getBoundingClientRect();
        const rect = node.getBoundingClientRect();
        return {
          x: rect.left + rect.width * 0.5 - hostRect.left,
          y: rect.top + rect.height * yRatio - hostRect.top,
        };
      };

      const sharedWorldTrainingSelfPoint = () => {
        const key = (clean(activeWorldUsername() || currentAuthUsername || "learner") || "learner").toLowerCase();
        const pos = sharedWorldPositions.get(key);
        if (pos && Number.isFinite(Number(pos.x)) && Number.isFinite(Number(pos.y))) {
          return sharedWorldTrainingPointFromNormalized(pos.x, pos.y);
        }
        const selfNode = sharedWorldNodes.get(key);
        return sharedWorldTrainingNodePoint(selfNode, 0.38);
      };

      const sharedWorldTrainingEventTargetPoint = (event = {}, target = null) => {
        const xValue = event.slime_x != null ? event.slime_x : event.slimeX;
        const yValue = event.slime_y != null ? event.slime_y : event.slimeY;
        if (Number.isFinite(Number(xValue)) && Number.isFinite(Number(yValue))) {
          return sharedWorldTrainingPointFromNormalized(Number(xValue), Number(yValue));
        }
        return sharedWorldTrainingNodePoint(target, 0.34);
      };

      // Added 2026-07-08: keeps normal attacks varied while using only client-side animation work.
      const sharedWorldTrainingAttackStyle = (event = {}) => {
        const raw = clean(event.attack_style || event.attackStyle || "").toLowerCase();
        if (["bolt", "arc", "sky", "slash", "nova"].includes(raw)) {
          return raw;
        }
        const seed = clean(event.event_id || event.eventId || event.slime_id || event.slimeId || Date.now());
        let hash = 0;
        for (let index = 0; index < seed.length; index += 1) {
          hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
        }
        return ["bolt", "arc", "sky", "slash", "nova"][hash % 5];
      };

      // Added 2026-07-08: makes hits push slimes away from the caster and briefly stun strong hits.
      const applySharedWorldTrainingSlimeImpactPhysics = (target = null, event = {}, options = {}) => {
        if (!target) {
          return;
        }
        const start = sharedWorldTrainingSelfPoint();
        const end = sharedWorldTrainingEventTargetPoint(event, target);
        const dx = end.x - start.x;
        const dy = end.y - start.y;
        const length = Math.max(1, Math.hypot(dx, dy));
        const power = Math.max(12, Math.min(34, Number(options.power || (event.critical || event.criticalHit ? 30 : 20)) || 20));
        const knockX = (dx / length) * power;
        const knockY = Math.max(-18, Math.min(18, (dy / length) * power * 0.45 - 8));
        const rotate = Math.max(-18, Math.min(18, (dx / length) * 14));
        target.style.setProperty("--slime-knock-x", `${knockX.toFixed(1)}px`);
        target.style.setProperty("--slime-knock-y", `${knockY.toFixed(1)}px`);
        target.style.setProperty("--slime-recoil-x", `${(knockX * 0.22).toFixed(1)}px`);
        target.style.setProperty("--slime-hit-rotate", `${rotate.toFixed(1)}deg`);
        target.style.setProperty("--slime-recoil-rotate", `${(rotate * -0.32).toFixed(1)}deg`);
        target.classList.remove("is-knocked", "is-stunned");
        void target.offsetWidth;
        target.classList.add("is-knocked");
        const stun = Boolean(options.stun || event.critical || event.criticalHit || event.slime_defeated || event.slimeDefeated);
        if (stun) {
          target.classList.add("is-stunned");
        }
        window.setTimeout(() => target.classList.remove("is-knocked"), 740);
        if (stun) {
          window.setTimeout(() => target.classList.remove("is-stunned"), 1280);
        }
      };

      const triggerSharedWorldTrainingSkyFireball = (event = {}, target = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !target) {
          return;
        }
        const end = sharedWorldTrainingEventTargetPoint(event, target);
        const critical = Boolean(event.critical || event.criticalHit);
        const sky = document.createElement("span");
        sky.className = `ft-world-training-sky-fireball${critical ? " is-critical" : ""}`;
        sky.style.setProperty("--sky-x", `${end.x}px`);
        sky.style.setProperty("--sky-y", `${Math.max(84, end.y - 18)}px`);
        effectHost.appendChild(sky);
        window.setTimeout(() => sky.remove(), critical ? 1420 : 1220);
      };

      const triggerSharedWorldTrainingDirectSkill = (event = {}, target = null, attackStyle = "bolt") => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !event || !event.correct) {
          return;
        }
        const skill = event.skill && typeof event.skill === "object" ? event.skill : {};
        const critical = Boolean(event.critical || event.criticalHit);
        const tone = clean(skill.tone || skill.id || "fireball").toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "fireball";
        const name = clean(skill.name || "Fire Skill");
        const style = ["bolt", "arc", "slash", "nova"].includes(clean(attackStyle).toLowerCase()) ? clean(attackStyle).toLowerCase() : "bolt";
        const start = sharedWorldTrainingSelfPoint();
        const end = sharedWorldTrainingEventTargetPoint(event, target);
        const sx = start.x;
        const sy = start.y - 12;
        const tx = end.x;
        const ty = end.y - 18;
        const dx = tx - sx;
        const dy = ty - sy;
        const distance = Math.max(68, Math.hypot(dx, dy));
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;
        const shot = document.createElement("span");
        shot.className = `ft-world-training-skill-shot is-${tone} is-attack-${style}${critical ? " is-critical" : ""}`;
        shot.style.setProperty("--skill-start-x", `${sx}px`);
        shot.style.setProperty("--skill-start-y", `${sy}px`);
        shot.style.setProperty("--skill-distance", `${distance}px`);
        shot.style.setProperty("--skill-angle", `${angle}deg`);
        shot.style.setProperty("--skill-end-x", `${tx}px`);
        shot.style.setProperty("--skill-end-y", `${ty}px`);
        shot.style.setProperty("--skill-mid-x", `${(sx + tx) / 2}px`);
        shot.style.setProperty("--skill-mid-y", `${(sy + ty) / 2 - Math.min(96, distance * 0.22)}px`);
        shot.innerHTML = `<span class="ft-world-training-skill-label">${critical ? `CRITICAL x2 - ${name}` : name}</span>`;
        effectHost.appendChild(shot);
        window.setTimeout(() => shot.remove(), critical ? 1540 : 1280);
      };

      const triggerSharedWorldTrainingSkill = (event = {}, target = null) => {
        if (!event || !event.correct) {
          return;
        }
        const self = ensureSharedWorldSelfNode();
        if (self && self.node) {
          self.node.classList.remove("is-training-cast", "is-training-critical-cast");
          void self.node.offsetWidth;
          self.node.classList.add("is-training-cast");
          if (event.critical || event.criticalHit) {
            self.node.classList.add("is-training-critical-cast");
          }
          const clearCast = () => {
            self.node.classList.remove("is-training-cast", "is-training-critical-cast");
          };
          window.setTimeout(clearCast, event.critical || event.criticalHit ? 1180 : 960);
        }
        const style = sharedWorldTrainingAttackStyle(event);
        if (style === "sky") {
          triggerSharedWorldTrainingSkyFireball(event, target);
        } else {
          triggerSharedWorldTrainingDirectSkill(event, target, style);
        }
      };

      const triggerSharedWorldTrainingEarthquake = (event = {}) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return;
        }
        const playerX = Number(event.player_x != null ? event.player_x : event.playerX);
        const playerY = Number(event.player_y != null ? event.player_y : event.playerY);
        const center = Number.isFinite(playerX) && Number.isFinite(playerY)
          ? sharedWorldTrainingPointFromNormalized(playerX, playerY)
          : sharedWorldTrainingSelfPoint();
        const radius = Math.max(120, Math.floor(Number(event.radius_px || event.radiusPx || 400) || 400));
        const quake = document.createElement("span");
        quake.className = "ft-world-training-earthquake";
        quake.style.setProperty("--quake-x", `${center.x}px`);
        quake.style.setProperty("--quake-y", `${center.y}px`);
        quake.style.setProperty("--quake-radius", `${radius}px`);
        const core = document.createElement("span");
        core.className = "ft-world-training-quake-core";
        quake.appendChild(core);
        for (let index = 0; index < 18; index += 1) {
          const crack = document.createElement("span");
          crack.className = "ft-world-training-quake-crack";
          const angle = index * 20 + (index % 3 === 0 ? -8 : (index % 3 === 1 ? 6 : 13));
          const length = Math.max(105, radius * (0.45 + (index % 5) * 0.055));
          crack.style.setProperty("--crack-angle", `${angle}deg`);
          crack.style.setProperty("--crack-length", `${length}px`);
          crack.style.setProperty("--crack-y", `${(index % 2 ? 1 : -1) * (6 + (index % 4) * 3)}px`);
          crack.style.setProperty("--crack-delay", `${index * 22}ms`);
          crack.style.setProperty("--branch-left", `${34 + (index % 4) * 8}%`);
          crack.style.setProperty("--branch-left-b", `${56 + (index % 3) * 7}%`);
          crack.style.setProperty("--branch-length", `${34 + (index % 5) * 8}px`);
          crack.style.setProperty("--branch-length-b", `${28 + (index % 4) * 7}px`);
          crack.style.setProperty("--branch-a", `${(index % 2 ? 1 : -1) * (28 + (index % 3) * 8)}deg`);
          crack.style.setProperty("--branch-b", `${(index % 2 ? -1 : 1) * (32 + (index % 4) * 6)}deg`);
          quake.appendChild(crack);
        }
        for (let index = 0; index < 22; index += 1) {
          const chip = document.createElement("span");
          chip.className = "ft-world-training-quake-chip";
          const angle = index * (360 / 22) + (index % 2 ? 7 : -5);
          chip.style.setProperty("--chip-angle", `${angle}deg`);
          chip.style.setProperty("--chip-distance", `${Math.max(80, radius * (0.28 + (index % 6) * 0.035))}px`);
          chip.style.setProperty("--chip-lift", `${-8 - (index % 5) * 5}px`);
          chip.style.setProperty("--chip-size", `${5 + (index % 4) * 2}px`);
          chip.style.setProperty("--chip-delay", `${80 + index * 18}ms`);
          quake.appendChild(chip);
        }
        effectHost.appendChild(quake);
        const self = ensureSharedWorldSelfNode();
        if (self && self.node) {
          self.node.classList.add("is-earthquake-cast");
          window.setTimeout(() => self.node.classList.remove("is-earthquake-cast"), 1120);
        }
        const affected = Array.isArray(event.affected) ? event.affected : [];
        affected.forEach((row, index) => {
          const targetId = clean(row && (row.slime_id || row.slimeId) || "");
          const host = sharedWorldTrainingSlimeHost();
          let target = host && Array.from(host.querySelectorAll("[data-slime-id]"))
            .find((node) => clean(node.dataset.slimeId || "") === targetId);
          if (!target) {
            target = createSharedWorldTrainingGhostSlime(row, { defeated: Boolean(row && (row.slime_defeated || row.slimeDefeated)) });
          }
          const point = sharedWorldTrainingEventTargetPoint(row, target);
          const damage = Math.max(0, Math.floor(Number(row && row.damage || event.damage || 0) || 0));
          window.setTimeout(() => {
            if (target) {
              target.classList.add("is-hit");
              applySharedWorldTrainingSlimeImpactPhysics(target, row, { stun: true, power: 28 });
              window.setTimeout(() => target.classList.remove("is-hit"), 720);
            }
            showSharedWorldTrainingImpactBurst(point, "critical");
            showSharedWorldTrainingDamageFloatAtPoint(point, `-${damage} HP`, "critical", { y: -18 });
            if (row && (row.slime_defeated || row.slimeDefeated)) {
              showSharedWorldTrainingDamageFloatAtPoint(point, "SLIME DOWN", "defeat", { y: -58 });
            }
          }, 280 + index * 70);
        });
        window.setTimeout(() => quake.remove(), 1850);
      };

      const showSharedWorldTrainingDamageFloatAtPoint = (point = {}, text = "", tone = "", offset = {}) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !clean(text)) {
          return;
        }
        const x = Math.max(0, Number(point.x || 0) + Number(offset.x || 0));
        const y = Math.max(0, Number(point.y || 0) + Number(offset.y || 0));
        const damage = document.createElement("span");
        damage.className = `ft-world-training-damage-float ${tone ? `is-${tone}` : ""}`;
        damage.style.setProperty("--damage-x", `${x}px`);
        damage.style.setProperty("--damage-y", `${y}px`);
        damage.textContent = text;
        effectHost.appendChild(damage);
        window.setTimeout(() => damage.remove(), tone === "defeat" ? 1650 : (tone === "critical" ? 1580 : 1300));
      };

      const showSharedWorldTrainingDamageFloat = (node, text = "", tone = "", offset = {}) => {
        if (!node || !clean(text)) {
          return;
        }
        const point = sharedWorldTrainingNodePoint(node, tone === "player" ? 0.38 : 0.32);
        showSharedWorldTrainingDamageFloatAtPoint(point, text, tone, offset);
      };

      const showSharedWorldTrainingImpactBurst = (point = {}, tone = "") => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return;
        }
        const burst = document.createElement("span");
        burst.className = `ft-world-training-impact-burst ${tone ? `is-${tone}` : ""}`;
        burst.style.setProperty("--impact-x", `${Math.max(0, Number(point.x || 0))}px`);
        burst.style.setProperty("--impact-y", `${Math.max(0, Number(point.y || 0))}px`);
        effectHost.appendChild(burst);
        window.setTimeout(() => burst.remove(), tone === "critical" ? 1160 : 920);
      };

      const sharedWorldTrainingCrystalItemTone = (item = {}) => {
        const id = clean(item && (item.id || item.item_id || item.itemId) || "").toLowerCase();
        if (id === "space_q_spellbook_gold" || id === "leaderboard_space_q_crystal") return "bookgold";
        if (id === "space_q_spellbook_silver") return "booksilver";
        if (id === "space_p_bow_gold" || id === "paragraph_crystal_golden") return "bowgold";
        if (id === "space_p_bow_silver") return "bowsilver";
        if (id === "space_s_sax_gold") return "saxgold";
        if (id === "space_s_sax_silver") return "saxsilver";
        if (id === "space_l_sword_gold") return "swordgold";
        if (id === "space_l_sword_silver") return "swordsilver";
        if (/gold|yellow/.test(id)) return "golden";
        if (/blue/.test(id)) return "blue";
        if (/green/.test(id)) return "green";
        if (/paragraph|purple|prism|crystal$/.test(id)) return "purple";
        return "";
      };

      const showSharedWorldTrainingCorpse = (event = {}, target = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost) {
          return null;
        }
        const point = sharedWorldTrainingEventTargetPoint(event, target);
        const question = clean(event.question_prompt || event.questionPrompt || "");
        const expected = clean(event.expected_answer || event.expectedAnswer || event.answer || "");
        const userAnswer = clean(event.user_answer || event.userAnswer || "");
        const userAnswerHtml = sharedWorldTrainingAnswerTokenHtml(userAnswer, expected);
        const corpse = document.createElement("span");
        corpse.className = "ft-world-training-corpse";
        corpse.style.setProperty("--corpse-x", `${point.x}px`);
        corpse.style.setProperty("--corpse-y", `${point.y}px`);
        corpse.innerHTML = `
          <span class="ft-world-training-corpse-card">
            ${question ? `<b>Question</b><span>${escapeHtml(question)}</span>` : ""}
            <b>Correct answer</b>
            <span>${escapeHtml(expected || "Answer cleared")}</span>
            <b>Your answer</b>
            <span class="is-user">${userAnswerHtml}</span>
          </span>
          <span class="ft-world-training-corpse-core" aria-hidden="true"></span>
        `;
        effectHost.appendChild(corpse);
        window.setTimeout(() => corpse.remove(), 10200);
        return corpse;
      };

      const appendSharedWorldTrainingHistory = (event = {}) => {
        if (!worldTrainingHistoryList) {
          return;
        }
        const defeated = Boolean(event.slime_defeated || event.slimeDefeated);
        const type = clean(event.type || "").toLowerCase();
        const hurt = type === "hurt" || event.correct === false;
        const slimeName = clean(event.slime_name || event.slimeName || "Slime");
        const question = clean(event.question_prompt || event.questionPrompt || "");
        const expected = clean(event.expected_answer || event.expectedAnswer || event.answer || "");
        const userAnswer = clean(event.user_answer || event.userAnswer || "");
        const damage = Math.max(0, Math.floor(Number(event.damage || 0) || 0));
        const healAmount = Math.max(0, Math.floor(Number(event.heal_amount || event.healAmount || 0) || 0));
        const accuracy = Math.max(0, Math.min(100, Math.round(Number(event.accuracy_percent || event.accuracyPercent || event.score?.percent || 0) || 0)));
        const userAnswerHtml = sharedWorldTrainingAnswerTokenHtml(userAnswer, expected);
        const title = defeated ? `${slimeName} defeated` : hurt ? `${slimeName} countered` : `${slimeName} hit`;
        if (worldTrainingHistoryTitle) {
          worldTrainingHistoryTitle.textContent = `${title}${damage ? (hurt ? ` - ${damage} HP lost` : ` - ${damage} damage`) : ""}${healAmount ? ` | +${healAmount} HP` : ""}`;
        }
        if (worldTrainingHistory) {
          worldTrainingHistory.setAttribute("aria-hidden", "false");
        }
        worldTrainingHistoryList.innerHTML = "";
        const article = document.createElement("article");
        article.innerHTML = `
          <b>${escapeHtml(title)}</b>
          ${question ? `<span>${escapeHtml(question)}</span>` : ""}
          ${expected ? `<b>Correct answer</b><span class="is-correct">${escapeHtml(expected)}</span>` : ""}
          <b>Your answer</b><span class="is-user">${userAnswerHtml}</span>
          ${accuracy ? `<b>Result</b><span>${escapeHtml(`${accuracy}% accuracy`)}</span>` : ""}
          ${healAmount ? `<b>Critical recovery</b><span class="is-correct">${escapeHtml(`+${healAmount} HP`)}</span>` : ""}
          ${hurt && damage ? `<b>Counter</b><span>${escapeHtml(`-${damage} HP`)}</span>` : ""}
        `;
        worldTrainingHistoryList.prepend(article);
      };

      const stopSharedWorldTrainingLootWatch = () => {
        if (sharedWorldTrainingLootTimer) {
          window.clearInterval(sharedWorldTrainingLootTimer);
          sharedWorldTrainingLootTimer = 0;
        }
      };

      const collectSharedWorldTrainingLoot = (dropKey = "", reason = "auto") => {
        const record = sharedWorldTrainingLootDrops.get(dropKey);
        if (!record || record.collecting) {
          return false;
        }
        record.collecting = true;
        const node = record.node;
        const target = sharedWorldTrainingSelfPoint();
        if (node) {
          node.classList.add("is-collecting");
          node.style.setProperty("--loot-target-x", `${target.x}px`);
          node.style.setProperty("--loot-target-y", `${target.y}px`);
        }
        const item = record.item && typeof record.item === "object" ? record.item : { id: "crystal", name: canonicalRewardName("crystal", "Reward Item") };
        window.setTimeout(() => {
          try {
            awardInventoryItemOnce(record.eventKey, item, node || null, {
              tone: item.id || "crystal",
              feedback: () => setSharedWorldStatus(`Item collected${reason === "near" ? " nearby" : ""}: ${clean(canonicalRewardName(item.id, item.name))}`, "ok"),
            });
          } catch (error) {
            setSharedWorldStatus("Item collected, inventory sync will retry soon.", "ok");
          }
          if (node && node.parentNode) {
            node.parentNode.removeChild(node);
          }
          sharedWorldTrainingLootDrops.delete(dropKey);
          if (!sharedWorldTrainingLootDrops.size) {
            stopSharedWorldTrainingLootWatch();
          }
        }, 700);
        return true;
      };

      const startSharedWorldTrainingLootWatch = () => {
        if (sharedWorldTrainingLootTimer) {
          return;
        }
        sharedWorldTrainingLootTimer = window.setInterval(() => {
          if (!sharedWorldTrainingLootDrops.size || sharedWorldMapMode !== "training") {
            stopSharedWorldTrainingLootWatch();
            return;
          }
          const selfPoint = sharedWorldTrainingSelfPoint();
          sharedWorldTrainingLootDrops.forEach((record, key) => {
            if (!record || record.collecting) return;
            if (Math.hypot((record.x || 0) - selfPoint.x, (record.y || 0) - selfPoint.y) <= 20) {
              collectSharedWorldTrainingLoot(key, "near");
            }
          });
        }, 260);
      };

      const spawnSharedWorldTrainingLootDrops = (event = {}, target = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        const drops = Array.isArray(event.crystal_drops) ? event.crystal_drops : (Array.isArray(event.crystalDrops) ? event.crystalDrops : []);
        if (!effectHost || !drops.length) {
          return;
        }
        const base = sharedWorldTrainingEventTargetPoint(event, target);
        drops.slice(0, 3).forEach((drop, index) => {
          const row = drop && typeof drop === "object" ? drop : {};
          const item = row.item && typeof row.item === "object" ? row.item : row;
          const dropKey = clean(row.id || `${event.event_id || event.eventId || Date.now()}_${index}`);
          const eventKey = `qm-city-training-loot:${dropKey}:${clean(item.id || "crystal")}`;
          if (!dropKey || sharedWorldTrainingLootDrops.has(dropKey)) {
            return;
          }
          const angle = (-80 + index * 80 + Math.random() * 28) * Math.PI / 180;
          const radius = 34 + Math.random() * 24;
          const x = Math.max(10, base.x + Math.cos(angle) * radius);
          const y = Math.max(10, base.y + Math.sin(angle) * radius + 16);
          const node = document.createElement("span");
          const tone = sharedWorldTrainingCrystalItemTone(item);
          node.className = `ft-world-training-loot ${tone ? `is-${tone}` : ""}`;
          node.style.setProperty("--loot-x", `${x}px`);
          node.style.setProperty("--loot-y", `${y}px`);
          node.title = clean(canonicalRewardName(item.id, item.name));
          effectHost.appendChild(node);
          sharedWorldTrainingLootDrops.set(dropKey, { node, item, eventKey, x, y, collecting: false });
          window.setTimeout(() => collectSharedWorldTrainingLoot(dropKey, "auto"), 10000);
        });
        startSharedWorldTrainingLootWatch();
      };

      const triggerSharedWorldTrainingCounterLeap = (event = {}, slimeNode = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !slimeNode) {
          return;
        }
        const start = sharedWorldTrainingEventTargetPoint(event, slimeNode);
        const end = sharedWorldTrainingSelfPoint();
        const leap = document.createElement("span");
        leap.className = "ft-world-training-counter-leap";
        leap.style.setProperty("--leap-start-x", `${start.x - 36}px`);
        leap.style.setProperty("--leap-start-y", `${start.y - 31}px`);
        leap.style.setProperty("--leap-end-x", `${end.x - 36}px`);
        leap.style.setProperty("--leap-end-y", `${end.y - 31}px`);
        leap.style.setProperty("--leap-mid-x", `${(start.x + end.x) / 2 - 36}px`);
        leap.style.setProperty("--leap-mid-y", `${(start.y + end.y) / 2 - 92}px`);
        effectHost.appendChild(leap);
        showSharedWorldTrainingImpactBurst(end, "player");
        showSharedWorldTrainingDamageFloatAtPoint(end, `-${Math.max(0, Math.floor(Number(event.damage || 0) || 0))} HP`, "player", { y: -28 });
        const slimeManaGain = Math.max(0, Math.floor(Number(event.slime_mana_gain || event.slimeManaGain || 0) || 0));
        if (slimeManaGain) {
          showSharedWorldTrainingDamageFloatAtPoint(start, `+${slimeManaGain} MP`, "mana", { y: -40 });
        }
        window.setTimeout(() => leap.remove(), 1120);
      };

      const triggerSharedWorldTrainingSlimeSpit = (event = {}, slimeNode = null) => {
        const effectHost = sharedWorldTrainingEffectHost();
        if (!effectHost || !slimeNode) {
          return;
        }
        const start = sharedWorldTrainingEventTargetPoint(event, slimeNode);
        const end = sharedWorldTrainingSelfPoint();
        const spit = document.createElement("span");
        spit.className = "ft-world-training-slime-spit";
        spit.style.setProperty("--spit-start-x", `${start.x - 19}px`);
        spit.style.setProperty("--spit-start-y", `${start.y - 16}px`);
        spit.style.setProperty("--spit-end-x", `${end.x - 19}px`);
        spit.style.setProperty("--spit-end-y", `${end.y - 16}px`);
        effectHost.appendChild(spit);
        const damage = Math.max(0, Math.floor(Number(event.damage || 0) || 0));
        window.setTimeout(() => {
          showSharedWorldTrainingImpactBurst(end, "player");
          showSharedWorldTrainingDamageFloatAtPoint(end, `-${damage} HP`, "player", { y: -28 });
        }, 650);
        const slimeManaGain = Math.max(0, Math.floor(Number(event.slime_mana_gain || event.slimeManaGain || 0) || 0));
        if (slimeManaGain) {
          showSharedWorldTrainingDamageFloatAtPoint(start, `+${slimeManaGain} MP`, "mana", { y: -40 });
        }
        window.setTimeout(() => spit.remove(), 940);
      };

      const flashSharedWorldTrainingEvent = (event = {}) => {
        const row = event && typeof event === "object" ? event : {};
        const eventId = clean(row.event_id || row.eventId || row.id || "");
        const eventKey = eventId || `${clean(row.type)}:${clean(row.slime_id || row.slimeId)}:${clean(row.damage)}:${clean(row.answer)}:${clean(row.slime_hp || row.slimeHp)}:${row.critical ? "critical" : "normal"}`;
        const host = sharedWorldTrainingSlimeHost();
        if (!host || !clean(row.type) || sharedWorldTrainingLastEventKey === eventKey) {
          return;
        }
        if (clean(row.type).toLowerCase() === "select") {
          sharedWorldTrainingLastEventKey = eventKey;
          return;
        }
        if (clean(row.type).toLowerCase() === "skill") {
          sharedWorldTrainingLastEventKey = eventKey;
          playEffectSound("true");
          triggerSharedWorldTrainingEarthquake(row);
          return;
        }
        sharedWorldTrainingLastEventKey = eventKey;
        const targetId = clean(row.slime_id || row.slimeId || "");
        let target = Array.from(host.querySelectorAll("[data-slime-id]"))
          .find((node) => clean(node.dataset.slimeId || "") === targetId);
        if (!target && row.correct) {
          target = createSharedWorldTrainingGhostSlime(row);
        } else if (!target && clean(row.type) === "hurt") {
          target = createSharedWorldTrainingGhostSlime(row, { defeated: false });
        }
        if (target) {
          target.classList.remove("is-hit", "is-hurt");
          void target.offsetWidth;
          if (row.correct) {
            playEffectSound("true");
            const damage = Math.max(0, Math.floor(Number(row.damage || 0) || 0));
            const critical = Boolean(row.critical || row.criticalHit);
            const earned = Math.max(0, Math.floor(Number(row.earned_words || row.earnedWords || row.exp || 0) || 0));
            const manaGain = Math.max(0, Math.floor(Number(row.mana_gain || row.manaGain || 0) || 0));
            const healAmount = Math.max(0, Math.floor(Number(row.heal_amount || row.healAmount || 0) || 0));
            const targetPoint = sharedWorldTrainingEventTargetPoint(row, target);
            const selfPoint = sharedWorldTrainingSelfPoint();
            const answerLabel = clean(row.expected_answer || row.expectedAnswer || row.read_text || row.readText || row.answer || sharedWorldTrainingSpeech.expectedText || "");
            if (answerLabel) {
              showSharedWorldTrainingDamageFloatAtPoint(selfPoint, answerLabel.length > 72 ? `${answerLabel.slice(0, 69)}...` : answerLabel, "answer", { y: -104 });
            }
            appendSharedWorldTrainingHistory(row);
            triggerSharedWorldTrainingSkill(row, target);
            const showHitFeedback = () => {
              applySharedWorldTrainingSlimeImpactPhysics(target, row, { stun: critical });
              showSharedWorldTrainingImpactBurst(targetPoint, critical ? "critical" : "");
              showSharedWorldTrainingDamageFloatAtPoint(targetPoint, critical ? `CRITICAL x2 -${damage} HP` : `-${damage} HP`, critical ? "critical" : "", { y: critical ? -26 : -18 });
              if (manaGain) {
                showSharedWorldTrainingDamageFloatAtPoint(selfPoint, `+${manaGain} MP`, "mana", { y: -44 });
              }
              if (healAmount) {
                showSharedWorldTrainingDamageFloatAtPoint(selfPoint, `+${healAmount} HP`, "heal", { y: -58 });
              }
              if (earned) {
                showSharedWorldTrainingDamageFloatAtPoint(selfPoint, `+${earned} EXP`, "exp", { y: healAmount ? -92 : -78 });
              }
              if (row.slime_defeated || row.slimeDefeated || clean(row.type) === "clear") {
                showSharedWorldTrainingDamageFloatAtPoint(targetPoint, "SLIME DOWN", "defeat", { y: -62 });
                showSharedWorldTrainingCorpse(row, target);
                spawnSharedWorldTrainingLootDrops(row, target);
              }
            };
            if (sharedWorldTrainingAttackStyle(row) === "sky") {
              window.setTimeout(showHitFeedback, 640);
            } else {
              showHitFeedback();
            }
          } else {
            playEffectSound("false");
            appendSharedWorldTrainingHistory(row);
            triggerSharedWorldTrainingSlimeSpit(row, target);
          }
          target.classList.add(row.correct ? "is-hit" : "is-hurt");
          window.setTimeout(() => target.classList.remove("is-hit", "is-hurt"), 720);
        }
      };

      const renderSharedWorldTraining = (payload = {}) => {
        const training = payload.training && typeof payload.training === "object" ? payload.training : payload;
        sharedWorldTrainingState = { training };
        const stats = training.stats && typeof training.stats === "object" ? training.stats : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : {};
        const selected = worldTrainingSelectedSlime();
        const selectedQuestion = selected && selected.question && typeof selected.question === "object" ? selected.question : null;
        const question = selected ? (selectedQuestion || (arena.question && typeof arena.question === "object" ? arena.question : {})) : {};
        const selectedId = clean(selected && selected.id || arena.selected_id || arena.selectedId || "");
        const trainingEvent = (training.event && typeof training.event === "object") ? training.event : ((payload.event && typeof payload.event === "object") ? payload.event : null);
        if (trainingEvent) {
          flashSharedWorldTrainingEvent(trainingEvent);
          if (training && typeof training === "object") {
            delete training.event;
          }
        }
        renderSharedWorldTrainingStats(stats, arena);
        renderSharedWorldTrainingSlimes(arena);
        renderSharedWorldTrainingLog(arena);
        if (worldTrainingTarget) {
          const selectedName = selected ? `${clean(selected.name || "Slime")} Lv ${Math.max(1, Math.floor(Number(selected.level || 1) || 1))}` : "Choose a slime";
          worldTrainingTarget.textContent = selectedName;
        }
        if (worldTrainingQuestion) {
          const isSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsSpeech(question);
          const isServerSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsServerSpeech(question);
          const isAudioQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsAudioInput(question);
          worldTrainingQuestion.classList.toggle("is-speech-question", isSpeechQuestion);
          worldTrainingQuestion.classList.toggle("is-server-speech-question", isServerSpeechQuestion);
          worldTrainingQuestion.classList.toggle("is-audio-question", isAudioQuestion);
          if (!isAudioQuestion && sharedWorldTrainingAudioKey) {
            sharedWorldTrainingAudioKey = "";
            stopSharedWorldTrainingAudio();
          }
          if (!selected) {
            worldTrainingQuestion.textContent = "Choose a slime to start training.";
          } else if (isSpeechQuestion) {
            const readText = sharedWorldTrainingSpeechText(question);
            const ipa = clean(question.ipa || question.ipa_uk || question.ipaUk || question.ipa_us || question.ipaUs || "");
            const hideReadText = sharedWorldTrainingQuestionIsViPromptSpeech(question);
            const promptText = clean(question.prompt || (hideReadText ? "Speak the English answer from the Vietnamese cue." : "Read this aloud."));
            const cueText = clean(question.meaning || question.translation || question.vietnamese || "");
            const promptLabel = hideReadText ? "Speak the English answer from this Vietnamese cue." : promptText;
            const primaryReadText = hideReadText ? (cueText || promptText) : readText;
            worldTrainingQuestion.innerHTML = `
              <span class="ft-world-training-read-card${hideReadText ? " is-vi-cue" : ""}">
                <span>${escapeHtml(promptLabel)}</span>
                ${primaryReadText ? `<span class="ft-world-training-read-text">${escapeHtml(primaryReadText)}</span>` : ""}
                ${ipa && !hideReadText ? `<span class="ft-world-training-read-ipa">${escapeHtml(ipa)}</span>` : ""}
                <span class="ft-world-training-read-status" data-training-read-status></span>
              </span>
            `;
            renderSharedWorldTrainingSpeechStatus(question, selectedId);
          } else if (isServerSpeechQuestion) {
            const sourceText = clean(question.source_text || question.sourceText || "");
            const promptText = clean(question.prompt || "Speak the Vietnamese translation for this English sentence.");
            worldTrainingQuestion.innerHTML = `
              <span class="ft-world-training-read-card is-vi-cue is-server-speech">
                <span>${escapeHtml(promptText)}</span>
                <span class="ft-world-training-read-text">${escapeHtml(sourceText || "English sentence is loading.")}</span>
                <span class="ft-world-training-read-status" data-training-server-speech-status></span>
              </span>
            `;
            renderSharedWorldTrainingServerSpeechStatus(question, selectedId);
          } else if (sharedWorldTrainingQuestionIsTranslateVi(question)) {
            const sourceText = clean(question.source_text || question.sourceText || "");
            const promptText = clean(question.prompt || "Translate this sentence to Vietnamese.");
            worldTrainingQuestion.innerHTML = `
              <span class="ft-world-training-read-card is-vi-cue is-translate-vi">
                <span>${escapeHtml(promptText)}</span>
                ${sourceText ? `<span class="ft-world-training-read-text">${escapeHtml(sourceText)}</span>` : ""}
                <span class="ft-world-training-read-status" data-training-server-speech-status></span>
              </span>
            `;
            renderSharedWorldTrainingServerSpeechStatus(question, selectedId);
          } else if (isAudioQuestion) {
            worldTrainingQuestion.innerHTML = `
              <span class="ft-world-training-audio-card">
                <span class="ft-world-training-audio-orb" aria-hidden="true"></span>
                <span class="ft-world-training-audio-copy">
                  <b>${escapeHtml(clean(question.prompt || "Listen and type the English answer."))}</b>
                  <small>${escapeHtml(clean(question.type || "Audio dictation"))}</small>
                </span>
                <button class="ft-world-training-audio-play" type="button" data-training-audio-play aria-label="Replay audio">Play</button>
              </span>
            `;
            maybePlaySharedWorldTrainingAudioQuestion(question, selectedId);
          } else {
            worldTrainingQuestion.textContent = clean(question.prompt || "The practice gate is preparing a new word.");
          }
        }
        if (worldTrainingAnswer) {
          const speechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsSpeech(question);
          const serverSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsServerSpeech(question);
          const translateQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsTranslateVi(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const localSpeechQuestion = speechQuestion && !browserSpeechQuestion;
          const legacyServerSpeechQuestion = serverSpeechQuestion && !browserSpeechQuestion;
          worldTrainingAnswer.disabled = localSpeechQuestion || legacyServerSpeechQuestion;
          worldTrainingAnswer.dataset.vietnameseTypingActive = (translateQuestion || serverSpeechQuestion) && !speechQuestion ? "1" : "0";
          worldTrainingAnswer.placeholder = browserSpeechQuestion
            ? "Press Ctrl or Mic, speak Vietnamese, press Ctrl again..."
            : (localSpeechQuestion
              ? "Use your microphone. Read until all tokens are detected."
              : (legacyServerSpeechQuestion ? "Press Ctrl, speak Vietnamese, press Ctrl again..." : (translateQuestion ? "Nhap ban dich tieng Viet..." : "Type the English answer...")));
        }
        if (worldTrainingAnswerForm) {
          const speechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsSpeech(question);
          const serverSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsServerSpeech(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const localSpeechQuestion = speechQuestion && !browserSpeechQuestion;
          const legacyServerSpeechQuestion = serverSpeechQuestion && !browserSpeechQuestion;
          worldTrainingAnswerForm.classList.toggle("is-speech-mode", speechQuestion || serverSpeechQuestion);
          worldTrainingAnswerForm.classList.toggle("is-browser-speech-mode", browserSpeechQuestion);
          worldTrainingAnswerForm.classList.toggle("is-legacy-speech-mode", legacyServerSpeechQuestion);
          worldTrainingAnswerForm.classList.toggle("is-local-speech-mode", localSpeechQuestion);
          worldTrainingAnswerForm.setAttribute("aria-hidden", localSpeechQuestion ? "true" : "false");
        }
        if (worldTrainingViToggle) {
          const translateQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsTranslateVi(question);
          const serverSpeechQuestion = Boolean(selected) && sharedWorldTrainingQuestionIsServerSpeech(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const showVietnameseTypingToggle = Boolean(translateQuestion || (serverSpeechQuestion && browserSpeechQuestion));
          worldTrainingViToggle.hidden = !showVietnameseTypingToggle;
          worldTrainingViToggle.setAttribute("aria-hidden", showVietnameseTypingToggle ? "false" : "true");
        }
        if (worldTrainingSubmit) {
          const speechQuestion = selected && sharedWorldTrainingQuestionIsSpeech(question);
          const serverSpeechQuestion = selected && sharedWorldTrainingQuestionIsServerSpeech(question);
          const browserSpeechQuestion = sharedWorldTrainingUsesBrowserSpeechInput(question);
          const browserSpeechInputActive = Boolean(
            typeof browserSpeechInputRecognition !== "undefined"
            && browserSpeechInputRecognition
            && typeof browserSpeechInputTarget !== "undefined"
            && browserSpeechInputTarget === worldTrainingAnswer
          );
          const localSpeechQuestion = speechQuestion && !browserSpeechQuestion;
          const legacyServerSpeechQuestion = serverSpeechQuestion && !browserSpeechQuestion;
          worldTrainingSubmit.hidden = true;
          worldTrainingSubmit.setAttribute("aria-hidden", "true");
          worldTrainingSubmit.disabled = !selected || sharedWorldTrainingLoading || localSpeechQuestion || legacyServerSpeechQuestion || (browserSpeechQuestion && browserSpeechInputActive);
          worldTrainingSubmit.textContent = localSpeechQuestion || legacyServerSpeechQuestion
            ? (localSpeechQuestion ? "Mic live" : "Ctrl mic")
            : (browserSpeechQuestion ? (browserSpeechInputActive ? "Mic recording" : "Speech strike") : (selected && sharedWorldTrainingQuestionIsTranslateVi(question) ? "Translate strike" : "Strike"));
        }
        if (trainingEvent) {
          if (trainingEvent.cleared) {
            setSharedWorldStatus("Practice field cleared. A fresh set of slimes is ready.", "ok");
          } else if (trainingEvent.player_defeated || trainingEvent.return_to_city) {
            setSharedWorldStatus("Your fire core fainted. Returning to QM-City center.", "error");
            window.setTimeout(() => {
              if (sharedWorldTrainingIsActive()) {
                closeSharedWorldTraining();
              }
            }, 950);
          } else if (clean(trainingEvent.type).toLowerCase() === "skill") {
            const affected = Array.isArray(trainingEvent.affected) ? trainingEvent.affected.length : 0;
            const skillName = clean(trainingEvent.skill && trainingEvent.skill.name) || "Skill";
            const manaCost = Math.max(0, Math.floor(Number(trainingEvent.mana_cost || trainingEvent.manaCost || 0) || 0));
            setSharedWorldStatus(`${skillName} shook the field: ${affected} slime${affected === 1 ? "" : "s"} hit${trainingEvent.damage ? `, ${trainingEvent.damage} damage each` : ""}${manaCost ? ` · -${manaCost} MP` : ""}.`, "ok");
          } else if (trainingEvent.correct) {
            const earned = Math.max(0, Math.floor(Number(trainingEvent.earned_words || trainingEvent.earnedWords || 0) || 0));
            const healAmount = Math.max(0, Math.floor(Number(trainingEvent.heal_amount || trainingEvent.healAmount || 0) || 0));
            const skillName = clean(trainingEvent.skill && trainingEvent.skill.name) || "Training hit";
            const critical = Boolean(trainingEvent.critical || trainingEvent.criticalHit);
            setSharedWorldStatus(`${skillName} landed${critical ? " Critical x2" : ""}${trainingEvent.damage ? `: ${trainingEvent.damage} damage` : ""}${healAmount ? ` | +${healAmount} HP` : ""}${earned ? ` | +${earned} EXP` : ""}.`, "ok");
          } else if (trainingEvent.type === "hurt") {
            setSharedWorldStatus(`Slime countered${trainingEvent.damage ? `: ${trainingEvent.damage} damage` : ""}.`, "error");
          }
        }
        const selectedAlive = Boolean(selected && Math.max(0, Math.floor(Number(selected.hp || 0) || 0)) > 0);
        const questionOpen = Boolean(worldTrainingModal && worldTrainingModal.classList.contains("is-question-open"));
        const browserSpeechInputActive = Boolean(
          typeof browserSpeechInputRecognition !== "undefined"
          && browserSpeechInputRecognition
          && typeof browserSpeechInputTarget !== "undefined"
          && browserSpeechInputTarget === worldTrainingAnswer
        );
        if (selectedAlive && questionOpen && sharedWorldTrainingQuestionIsSpeech(question) && !sharedWorldTrainingUsesBrowserSpeechInput(question)) {
          maybeStartSharedWorldTrainingSpeech(question, selectedId);
        } else if (!selected || !sharedWorldTrainingQuestionIsSpeech(question) || sharedWorldTrainingUsesBrowserSpeechInput(question)) {
          sharedWorldTrainingAutoSpeechKey = "";
          if (sharedWorldTrainingSpeech.active && sharedWorldTrainingUsesBrowserSpeechInput(question) && !browserSpeechInputActive) {
            stopSharedWorldTrainingSpeech({ clearOverhead: false });
          } else if (!sharedWorldTrainingSpeech.active) {
            const holdUntil = Number(sharedWorldTrainingSpeech.holdUntil || 0);
            const holdActive = holdUntil && Date.now() < holdUntil;
            const heldExpected = clean(sharedWorldTrainingSpeech.expectedText || "");
            const heldTranscript = clean(`${sharedWorldTrainingSpeech.transcript || ""} ${sharedWorldTrainingSpeech.chunk || ""}`);
            if (holdActive && heldExpected && heldTranscript) {
              const passRatio = sharedWorldTrainingSpeech.passRatio || sharedWorldTrainingSpeechPassRatio(question, heldExpected);
              const heldQuestion = clean(sharedWorldTrainingSpeech.scoringLanguage || "") === "vi"
                ? { training_kind: "translate_vi_speech", server_speech: true }
                : question;
              const result = typeof sharedWorldTrainingSpeechScoreBundle === "function"
                ? sharedWorldTrainingSpeechScoreBundle(heldQuestion, heldTranscript, heldExpected, passRatio)
                : scoreSharedWorldTrainingSpeech(heldTranscript, heldExpected, passRatio);
              renderSharedWorldTrainingSpeechOverhead(heldTranscript, result);
            } else {
              sharedWorldTrainingSpeech.expectedText = "";
              sharedWorldTrainingSpeech.passRatio = 1;
              sharedWorldTrainingSpeech.holdUntil = 0;
              sharedWorldTrainingSpeech.scoringLanguage = "";
              clearSharedWorldTrainingSpeechOverhead();
            }
          }
        }
        if (selectedAlive && questionOpen && sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)) {
          renderSharedWorldTrainingServerSpeechStatus(question, selectedId);
        } else if (!selected || !sharedWorldTrainingQuestionSupportsVietnameseSpeech(question)) {
          if (sharedWorldTrainingServerSpeech.active && !sharedWorldTrainingServerSpeech.busy) {
            cancelSharedWorldTrainingServerSpeech();
          }
          sharedWorldTrainingServerSpeechCtrlCandidate = "";
        }
      };

      const stopSharedWorldTrainingPolling = () => {
        if (sharedWorldTrainingPollTimer) {
          window.clearInterval(sharedWorldTrainingPollTimer);
          sharedWorldTrainingPollTimer = 0;
        }
      };

      const startSharedWorldTrainingPolling = () => {
        stopSharedWorldTrainingPolling();
      };

      const loadSharedWorldTraining = async (focusInput = false, options = {}) => {
        if (!authToken || !sharedWorldTrainingIsActive()) {
          return;
        }
        const quiet = Boolean(options && options.quiet);
        const requestSeq = ++sharedWorldTrainingRequestSeq;
        if (!quiet) {
          setSharedWorldTrainingBusy(true);
        }
        try {
          const response = await fetchAuthJson(`/world/training/state?ts=${Date.now()}&refresh=1`, { timeoutMs: 0, silentTimeout: true });
          if (requestSeq !== sharedWorldTrainingRequestSeq) {
            return;
          }
          const result = response && response.payload ? response.payload : response;
          renderSharedWorldTraining(result);
          if (focusInput && worldTrainingAnswer) {
            worldTrainingAnswer.focus();
          }
        } catch (error) {
          if (!quiet) {
            setSharedWorldStatus(error && error.message ? error.message : "Could not load practice gate.", "error");
          }
        } finally {
          if (!quiet && requestSeq === sharedWorldTrainingRequestSeq) {
            setSharedWorldTrainingBusy(false);
          }
        }
      };

      const postSharedWorldTraining = async (path, body = {}, focusInput = true) => {
        if (!authToken) {
          return;
        }
        setSharedWorldTrainingBusy(true);
        try {
          const response = await fetchAuthJson(path, {
            method: "POST",
            timeoutMs: 0,
            body: JSON.stringify(body || {}),
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorldTraining(result);
          if (focusInput && worldTrainingAnswer) {
            worldTrainingAnswer.focus();
          }
          return result;
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Practice gate action failed.", "error");
          return null;
        } finally {
          setSharedWorldTrainingBusy(false);
        }
      };

      const openSharedWorldTraining = () => {
        if (!authToken) {
          showLoginGate("Hay dang nhap de mo khu luyen tap.");
          return;
        }
        const activeBattle = sharedWorldBattleState && sharedWorldBattleState.battle && clean(sharedWorldBattleState.battle.status) === "active";
        if (activeBattle) {
          setSharedWorldStatus("Finish the current battle before entering Slime Training Field.", "error");
          return;
        }
        sharedWorldMapMode = "training";
        sharedWorldTrainingExitArmed = true;
        sharedWorldTrainingAutoSpeechKey = "";
        sharedWorldTrainingAudioKey = "";
        sharedWorldTrainingAnchorSyncAt = 0;
        sharedWorldTrainingState = null;
        stopSharedWorldPolling();
        stopSharedWorldBattlePolling();
        clearSharedWorldFollowTarget();
        setSharedWorldPickingPosition(false);
        if (worldCard) {
          worldCard.classList.add("is-training-map");
        }
        if (worldTitle) {
          worldTitle.textContent = "Slime Training Field";
        }
        if (worldTrainingField) {
          worldTrainingField.setAttribute("aria-hidden", "false");
        }
        if (worldTrainingModal) {
          worldTrainingModal.classList.add("is-open");
          worldTrainingModal.setAttribute("aria-hidden", "false");
        }
        if (worldTrainingMapSlimes) {
          worldTrainingMapSlimes.innerHTML = "";
        }
        if (worldTrainingTarget) {
          worldTrainingTarget.textContent = "Loading slime field";
        }
        if (worldTrainingQuestion) {
          worldTrainingQuestion.textContent = "Refreshing your training slimes...";
        }
        if (worldTrainingHistoryTitle) {
          worldTrainingHistoryTitle.textContent = "No training hit yet";
        }
        if (worldTrainingHistoryList) {
          worldTrainingHistoryList.innerHTML = '<article class="is-empty">Hit or defeat a slime to review the question, correct answer, and your answer here.</article>';
        }
        setSharedWorldTrainingQuestionOpen(false);
        setSharedWorldSelfPosition(sharedWorldTrainingEntryPoint, { center: true, smooth: false });
        setSharedWorldStatus("Slime Training Field opened. Move on the map, select a slime, then answer in English.", "ok");
        startSharedWorldTrainingLocalMotion();
        startSharedWorldTrainingPolling();
        void loadSharedWorldTraining(false);
      };

      const closeSharedWorldTraining = (options = {}) => {
        const wasTraining = sharedWorldMapMode === "training";
        const returnToCityGate = Boolean(options && options.returnToCityGate);
        hideSharedWorldMoveMarker(false);
        sharedWorldMapMode = "city";
        if (worldCard) {
          worldCard.classList.remove("is-training-map");
        }
        if (worldTitle) {
          worldTitle.textContent = "QM-City";
        }
        if (worldTrainingField) {
          worldTrainingField.setAttribute("aria-hidden", "true");
        }
        if (worldTrainingModal) {
          worldTrainingModal.classList.remove("is-open");
          worldTrainingModal.setAttribute("aria-hidden", "true");
        }
        if (worldTrainingMapSlimes) {
          worldTrainingMapSlimes.innerHTML = "";
        }
        setSharedWorldTrainingQuestionOpen(false);
        sharedWorldTrainingRequestSeq += 1;
        sharedWorldTrainingLoading = false;
        sharedWorldTrainingAutoSpeechKey = "";
        sharedWorldTrainingAnchorSyncAt = 0;
        if (sharedWorldTrainingSkillCooldownTimer) {
          window.clearInterval(sharedWorldTrainingSkillCooldownTimer);
          sharedWorldTrainingSkillCooldownTimer = 0;
        }
        stopSharedWorldTrainingSpeech();
        stopSharedWorldTrainingPolling();
        stopSharedWorldTrainingLocalMotion();
        stopSharedWorldTrainingLootWatch();
        sharedWorldTrainingLootDrops.forEach((record) => {
          if (record && record.node && record.node.parentNode) {
            record.node.parentNode.removeChild(record.node);
          }
        });
        sharedWorldTrainingLootDrops.clear();
        const trainingEffectHost = sharedWorldTrainingEffectHost();
        if (trainingEffectHost) {
          trainingEffectHost.querySelectorAll(".ft-world-training-corpse").forEach((node) => node.remove());
        }
        setSharedWorldTrainingBusy(false);
        if (wasTraining && worldModal && worldModal.classList.contains("is-open")) {
          if (returnToCityGate) {
            sharedWorldNeedInitialCenter = false;
            const self = setSharedWorldSelfPosition(sharedWorldCityTrainingGatePoint, { center: true, smooth: false });
            if (self && self.point) {
              void moveSharedWorldPlayer(self.point);
            } else {
              void refreshSharedWorld();
            }
          } else {
            sharedWorldNeedInitialCenter = true;
            void refreshSharedWorld();
          }
          void refreshSharedWorldBattle();
          startSharedWorldPolling();
          startSharedWorldBattlePolling();
          setSharedWorldStatus(returnToCityGate ? "Returned through the QM-City training gate." : "Returned to QM-City center.", "ok");
        }
      };

      const selectSharedWorldTrainingSlime = (slimeId = "") => {
        const id = clean(slimeId);
        if (!id) {
          return;
        }
        const selected = worldTrainingSelectedSlime();
        const selectedId = clean(selected && selected.id || "");
        const selectedQuestion = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        if (sharedWorldTrainingSpeech.active) {
          if (selectedId === id && sharedWorldTrainingQuestionIsSpeech(selectedQuestion)) {
            setSharedWorldTrainingQuestionOpen(true);
            restartSharedWorldTrainingSpeech(selectedQuestion, id);
            return;
          }
          stopSharedWorldTrainingSpeech();
          sharedWorldTrainingAutoSpeechKey = "";
          clearSharedWorldTrainingSpeechOverhead();
        }
        if (sharedWorldTrainingServerSpeech.active) {
          if (selectedId === id && sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)) {
            setSharedWorldTrainingQuestionOpen(true);
            renderSharedWorldTrainingServerSpeechStatus(selectedQuestion, id);
            return;
          }
          cancelSharedWorldTrainingServerSpeech();
        }
        setSharedWorldTrainingQuestionOpen(true);
        if (selectedId === id && sharedWorldTrainingQuestionIsSpeech(selectedQuestion)) {
          restartSharedWorldTrainingSpeech(selectedQuestion, id);
          return;
        }
        const training = sharedWorldTrainingState && sharedWorldTrainingState.training ? sharedWorldTrainingState.training : {};
        const arena = training.arena && typeof training.arena === "object" ? training.arena : null;
        const slimes = arena && Array.isArray(arena.slimes) ? arena.slimes : [];
        const targetSlime = slimes.find((item) => clean(item && item.id) === id);
        if (!arena || !targetSlime) {
          void loadSharedWorldTraining(true);
          return;
        }
        arena.selected_id = id;
        arena.selectedId = id;
        arena.question = targetSlime.question && typeof targetSlime.question === "object" ? targetSlime.question : {};
        renderSharedWorldTraining({ training });
        if (worldTrainingAnswer) {
          worldTrainingAnswer.focus();
        }
      };

      const submitSharedWorldTrainingAnswer = () => {
        const selected = worldTrainingSelectedSlime();
        const selectedQuestion = selected && selected.question && typeof selected.question === "object" ? selected.question : {};
        const browserSpeechQuestion = selected && sharedWorldTrainingUsesBrowserSpeechInput(selectedQuestion);
        const browserSpeechInputActive = Boolean(
          typeof browserSpeechInputRecognition !== "undefined"
          && browserSpeechInputRecognition
          && typeof browserSpeechInputTarget !== "undefined"
          && browserSpeechInputTarget === worldTrainingAnswer
        );
        if (browserSpeechQuestion && browserSpeechInputActive) {
          setSharedWorldTrainingQuestionOpen(true);
          renderSharedWorldTrainingServerSpeechStatus(selectedQuestion, selected.id);
          setSharedWorldStatus("Mic is still recording. Press Ctrl or the mic button again to stop and score.", "error");
          return;
        }
        if (sharedWorldTrainingSpeech.active && !browserSpeechQuestion) {
          setSharedWorldStatus("Mic challenge is active. Read the shown text before the slime timer ends.", "error");
          return;
        }
        if ((sharedWorldTrainingServerSpeech.active || sharedWorldTrainingServerSpeech.busy) && !browserSpeechQuestion) {
          setSharedWorldStatus("Vietnamese speech challenge is active. Press Ctrl again to stop and score.", "error");
          return;
        }
        if (selected && sharedWorldTrainingQuestionIsServerSpeech(selectedQuestion) && !browserSpeechQuestion) {
          setSharedWorldTrainingQuestionOpen(true);
          renderSharedWorldTrainingServerSpeechStatus(selectedQuestion, selected.id);
          setSharedWorldStatus("Press Ctrl to record the Vietnamese translation for this slime.", "error");
          return;
        }
        const answer = clean(worldTrainingAnswer && worldTrainingAnswer.value);
        if (!answer) {
          setSharedWorldTrainingQuestionOpen(true);
          setSharedWorldStatus(
            sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)
              ? "Speak or type the Vietnamese answer before striking the slime."
              : "Type the English answer before striking the slime.",
            "error"
          );
          if (worldTrainingAnswer) {
            worldTrainingAnswer.focus();
          }
          return;
        }
        if (worldTrainingAnswer) {
          worldTrainingAnswer.value = "";
        }
        if (browserSpeechQuestion && (sharedWorldTrainingQuestionIsSpeech(selectedQuestion) || sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion))) {
          const expectedText = sharedWorldTrainingSpeechText(selectedQuestion);
          const passRatio = sharedWorldTrainingSpeechPassRatio(selectedQuestion, expectedText);
          const score = typeof sharedWorldTrainingSpeechScoreBundle === "function"
            ? sharedWorldTrainingSpeechScoreBundle(selectedQuestion, answer, expectedText, passRatio)
            : scoreSharedWorldTrainingSpeech(answer, expectedText, passRatio);
          const vietnameseSpeechPayload = sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)
            ? { server_speech: true, speech_language: "vi", browser_speech: true, browserSpeech: true }
            : {};
          void postSharedWorldTraining("/world/training/answer", {
            answer,
            slime_id: selected ? clean(selected.id) : "",
            ...vietnameseSpeechPayload,
            local_speech_passed: Boolean(score.passed),
            local_speech_percent: Math.max(0, Math.min(100, Number(score && score.score || 0) || 0)),
            local_speech_correct: Math.max(0, Number(score && score.correct || 0) || 0),
            local_speech_total: Math.max(0, Number(score && score.total || 0) || 0),
            local_speech_reason: score.passed ? "browser_speech_input" : "browser_speech_partial",
            local_speech_expected: expectedText,
          }, true);
          return;
        }
        const speechPayload = browserSpeechQuestion && (
          sharedWorldTrainingQuestionSupportsVietnameseSpeech(selectedQuestion)
          || sharedWorldTrainingQuestionIsTranslateVi(selectedQuestion)
        )
          ? { server_speech: true, speech_language: "vi" }
          : {};
        void postSharedWorldTraining("/world/training/answer", { answer, slime_id: selected ? clean(selected.id) : "", ...speechPayload }, true);
      };

      const upgradeSharedWorldTrainingStat = (stat = "") => {
        const key = clean(stat);
        if (!key) {
          return;
        }
        void postSharedWorldTraining("/world/training/upgrade", { stat: key }, false);
      };

      const upgradeSharedWorldTrainingSkill = (skillId = "") => {
        const key = clean(skillId || "earthquake");
        if (!key) {
          return;
        }
        void postSharedWorldTraining("/world/training/upgrade", { skill: key }, false);
      };

      const startSharedWorldTrainingSkillCooldown = (skillId = "earthquake", seconds = 10) => {
        const key = clean(skillId || "earthquake") || "earthquake";
        sharedWorldTrainingSkillCooldownUntil.set(key, Date.now() + Math.max(1, Number(seconds || 10)) * 1000);
        renderSharedWorldTrainingQuickSkill();
      };

      const castSharedWorldTrainingSkill = async (skillId = "earthquake") => {
        const key = clean(skillId || "earthquake") || "earthquake";
        if (sharedWorldTrainingLoading) {
          setSharedWorldStatus("Training action is still resolving.", "error");
          return;
        }
        const cooldownUntil = Number(sharedWorldTrainingSkillCooldownUntil.get(key) || 0);
        const remaining = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
        if (remaining > 0) {
          setSharedWorldStatus(`Skill cooling down: ${remaining}s.`, "error");
          renderSharedWorldTrainingQuickSkill();
          return;
        }
        const skill = sharedWorldTrainingSkillById(key);
        const radiusPx = Math.max(1, Math.floor(Number(skill.radius_px || skill.radiusPx || 400) || 400));
        const size = sharedWorldTrainingEffectSize();
        const pos = getSharedWorldSelfPosition();
        const host = sharedWorldTrainingSlimeHost();
        const slimePositions = host ? Array.from(host.querySelectorAll("[data-slime-id]")).map((node) => ({
          id: clean(node.dataset && node.dataset.slimeId || ""),
          x: sharedWorldClamp((Number(node.dataset && node.dataset.slimeX) || 50) / 100),
          y: sharedWorldClamp((Number(node.dataset && node.dataset.slimeY) || 50) / 100),
        })).filter((row) => row.id) : [];
        const result = await postSharedWorldTraining("/world/training/skill", {
          skill: key,
          player_x: sharedWorldClamp(pos.x),
          player_y: sharedWorldClamp(pos.y),
          radius_x: Math.max(0.02, Math.min(1, radiusPx / Math.max(1, size.width))),
          radius_y: Math.max(0.02, Math.min(1, radiusPx / Math.max(1, size.height))),
          slime_positions: slimePositions,
        }, false);
        if (result && result.training) {
          const event = result.training.event && typeof result.training.event === "object" ? result.training.event : {};
          startSharedWorldTrainingSkillCooldown(key, Math.max(1, Number(event.cooldown_seconds || event.cooldownSeconds || 10) || 10));
        }
      };

      const resetSharedWorldTraining = () => {
        void postSharedWorldTraining("/world/training/reset", {}, true);
      };

      const sharedWorldCommandListOpen = () => Boolean(worldCommandList && !worldCommandList.hasAttribute("hidden"));

      const sharedWorldTargetLabel = (target) => clean(target && (target.displayName || target.display_name || target.username));

      const sharedWorldInviteProfileLabel = (invite = {}, side = "from") => {
        const row = invite && typeof invite === "object" ? invite : {};
        const profile = row[`${side}_profile`] || row[`${side}Profile`] || {};
        const direct = row[`${side}_display_name`] || row[`${side}DisplayName`] || "";
        const username = clean(row[side] || "");
        const rosterRow = username ? sharedWorldRoster.get(username.toLowerCase()) : null;
        return clean(direct)
          || clean(profile && (profile.display_name || profile.displayName || profile.full_name || profile.fullName))
          || sharedWorldTargetLabel(rosterRow)
          || username
          || "learner";
      };

      const sharedWorldGenderSymbol = (gender = "") => {
        const key = clean(gender).toLowerCase();
        if (key === "female") return "♀︎";
        if (key === "male") return "♂︎";
        return "◇︎";
      };

      const sharedWorldNameKey = (value = "") => clean(value)
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\u0111/g, "d")
        .replace(/\u0110/g, "d")
        .replace(/đ/g, "d")
        .replace(/[^a-z0-9]+/g, " ")
        .trim();

      const setSharedWorldGameListOpen = (open = false) => {
        if (!worldGameButton || !worldGameList) {
          return;
        }
        if (open) {
          worldGameList.removeAttribute("hidden");
        } else {
          worldGameList.setAttribute("hidden", "");
        }
        worldGameButton.setAttribute("aria-expanded", open ? "true" : "false");
      };

      const sharedWorldBattleUserKey = (value = "") => clean(value).toLowerCase();

      const sharedWorldBattlePercent = (value) => {
        const number = Math.max(0, Math.min(100, Math.round(Number(value) || 0)));
        return `${number}%`;
      };

      const sharedWorldBattleGameLabel = (id = "") => {
        const key = clean(id || "fireball_vocab");
        if (key === "fireball_vocab") {
          return "Fireball Vocabulary Battle";
        }
        return key.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
      };

      const sharedWorldBattleMoveLabel = (effect = "", damage = 0) => {
        const key = clean(effect).toLowerCase();
        const strongDamage = Math.max(0, Math.round(Number(damage) || 0)) >= 30;
        if (key === "inferno" || key === "triple" || strongDamage) return "Inferno x3";
        if (key === "laser") return "Laser Beam";
        if (key === "meteor") return "Meteor Strike";
        if (key === "shield") return "Crystal Guard";
        if (key === "drain") return "Mana Drain";
        if (key === "phoenix" || key === "heal") return "Phoenix Pulse";
        if (key === "fire" || key === "fireball") return "Fireball";
        return key ? key.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) : "Fireball";
      };

      const stopSharedWorldBattleCountdown = () => {
        if (sharedWorldBattleTimer) {
          window.clearInterval(sharedWorldBattleTimer);
          sharedWorldBattleTimer = 0;
        }
      };

      const queueSharedWorldBattleVisualTimeout = (callback, delayMs = 0) => {
        const id = window.setTimeout(() => {
          sharedWorldBattleVisualTimers.delete(id);
          if (!worldModal || !worldModal.classList.contains("is-open")) {
            return;
          }
          callback();
        }, Math.max(0, Math.round(Number(delayMs) || 0)));
        sharedWorldBattleVisualTimers.add(id);
        return id;
      };

      const clearSharedWorldBattleVisualState = () => {
        sharedWorldBattleVisualTimers.forEach((id) => window.clearTimeout(id));
        sharedWorldBattleVisualTimers.clear();
        if (worldBattleCard) {
          worldBattleCard.classList.remove(
            "is-casting-left",
            "is-casting-right",
            "is-attack-fire",
            "is-attack-laser",
            "is-attack-meteor",
            "is-attack-inferno"
          );
          worldBattleCard.querySelectorAll(".ft-world-battle-heal-burst").forEach((node) => node.remove());
        }
        [worldBattleLeft, worldBattleRight].forEach((node) => {
          if (!node) {
            return;
          }
          if (node._worldBattleSpeechTimer) {
            window.clearTimeout(node._worldBattleSpeechTimer);
            node._worldBattleSpeechTimer = 0;
          }
          node.classList.remove(
            "is-speaking",
            "is-skill-heal",
            "is-skill-shield",
            "is-skill-drain",
            "is-skill-inferno",
            "is-hit",
            "is-loot-loss",
            "is-loot-gain",
            "is-turn-jump"
          );
          const callout = node.querySelector(".ft-world-battle-callout");
          if (callout) {
            callout.textContent = "";
          }
        });
      };

      const updateSharedWorldBattleCountdown = () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active") {
          if (worldBattleTimer) {
            worldBattleTimer.textContent = "--";
          }
          stopSharedWorldBattleCountdown();
          return;
        }
        const deadlineEpoch = Number(battle.deadline_epoch || battle.deadlineEpoch || 0);
        const serverEpoch = Number(battle.server_epoch || battle.serverEpoch || 0);
        const nowEpoch = serverEpoch > 0 ? serverEpoch + ((Date.now() - Number(sharedWorldBattleState && sharedWorldBattleState.receivedAt || Date.now())) / 1000) : Date.now() / 1000;
        const remaining = deadlineEpoch > 0 ? Math.max(0, Math.ceil(deadlineEpoch - nowEpoch)) : 30;
        if (worldBattleTimer) {
          worldBattleTimer.textContent = String(remaining).padStart(2, "0");
        }
        if (remaining <= 0) {
          window.setTimeout(() => {
            if (worldModal && worldModal.classList.contains("is-open")) {
              void refreshSharedWorldBattle();
            }
          }, 450);
        }
      };

      const startSharedWorldBattleCountdown = () => {
        stopSharedWorldBattleCountdown();
        updateSharedWorldBattleCountdown();
        sharedWorldBattleTimer = window.setInterval(updateSharedWorldBattleCountdown, 1000);
      };

      const sharedWorldBattlePlayersForView = (battle = {}) => {
        const players = Array.isArray(battle.players) ? battle.players.map((item) => clean(item)).filter(Boolean) : [];
        const me = clean(activeWorldUsername());
        const self = players.find((item) => sharedWorldBattleUserKey(item) === sharedWorldBattleUserKey(me)) || players[0] || me;
        const opponent = players.find((item) => sharedWorldBattleUserKey(item) !== sharedWorldBattleUserKey(self)) || players[1] || "";
        return { self, opponent };
      };

      const renderSharedWorldBattlePlayer = (node, battle = {}, username = "", side = "left") => {
        if (!node) {
          return;
        }
        const userKey = clean(username);
        const profiles = battle.profiles && typeof battle.profiles === "object" ? battle.profiles : {};
        const profile = profiles[userKey] || profiles[sharedWorldBattleUserKey(userKey)] || {};
        const displayName = clean(profile.display_name || profile.displayName || userKey || "Learner");
        const avatar = clean(profile.avatar || "");
        const avatarUrl = avatar ? resolveServerAssetUrl(avatar) : "";
        const hp = Math.max(0, Math.min(100, Math.round(Number((battle.hp || {})[userKey] ?? 100) || 0)));
        const mp = Math.max(0, Math.min(100, Math.round(Number((battle.mp || {})[userKey] ?? 0) || 0)));
        const turn = sharedWorldBattleUserKey(battle.turn) === sharedWorldBattleUserKey(userKey);
        node.classList.toggle("is-turn", turn);
        node.classList.toggle("is-left", side === "left");
        node.classList.toggle("is-right", side !== "left");
        node.classList.toggle("is-healthy", hp >= 70);
        node.classList.toggle("is-wounded", hp < 70 && hp >= 40);
        node.classList.toggle("is-critical", hp < 40);
        node.style.setProperty("--battle-hit-x-pre", side === "left" ? "10px" : "-10px");
        node.style.setProperty("--battle-hit-x-full", side === "left" ? "-46px" : "46px");
        node.style.setProperty("--battle-hit-x-land", side === "left" ? "-28px" : "28px");
        node.style.setProperty("--battle-hit-x-recoil", side === "left" ? "8px" : "-8px");
        node.style.setProperty("--battle-hit-rotate-pre", side === "left" ? "10deg" : "-10deg");
        node.style.setProperty("--battle-hit-rotate-full", side === "left" ? "-18deg" : "18deg");
        node.style.setProperty("--battle-hit-rotate-land", side === "left" ? "-13deg" : "13deg");
        node.style.setProperty("--battle-hit-rotate-recoil", side === "left" ? "5deg" : "-5deg");
        node.style.setProperty("--battle-smoke-x-a", side === "left" ? "8px" : "-8px");
        node.style.setProperty("--battle-smoke-x-b", side === "left" ? "16px" : "-16px");
        node.style.setProperty("--battle-smoke-x-c", side === "left" ? "28px" : "-28px");
        const hpTier = Math.max(0, Math.min(9, Math.floor((100 - hp) / 10)));
        for (let index = 0; index < 10; index += 1) {
          node.classList.toggle(`is-hp-tier-${index}`, index === hpTier);
        }
        node.classList.toggle("is-self-turn", turn && side === "left");
        const facing = side === "right" ? "-1" : "1";
        const renderKey = [userKey, displayName, avatarUrl, side].join("|");
        if (node.dataset.battlePlayerRenderKey !== renderKey || !node.querySelector(".ft-world-fireball")) {
          node.dataset.battlePlayerRenderKey = renderKey;
          node.innerHTML = `
            <div class="ft-world-battle-player-head">
              <div class="ft-world-battle-avatar">
                <span>${escapeHtml(displayName.slice(0, 1).toUpperCase() || "?")}</span>
                ${avatarUrl ? `<img src="${escapeHtml(avatarUrl)}" alt="" onerror="this.style.display='none'">` : ""}
              </div>
              <div class="ft-world-battle-name">
                <strong title="${escapeHtml(displayName)}">${escapeHtml(displayName)}</strong>
                <span>${turn ? "Active caster" : "Battle ready"}</span>
              </div>
            </div>
            <div class="ft-world-battle-character" aria-hidden="true">
              <span class="ft-world-battle-you-mark">YOU</span>
              <span class="ft-world-battle-callout"></span>
              <div class="ft-world-fireball" style="--world-facing:${facing}">
                <span class="ft-world-eye is-left"></span>
                <span class="ft-world-eye is-right"></span>
                <span class="ft-world-cheek is-left"></span>
                <span class="ft-world-cheek is-right"></span>
                <span class="ft-world-smile"></span>
                <span class="ft-world-bandage"></span>
                <span class="ft-world-bump"></span>
                <span class="ft-world-sweat"></span>
                <span class="ft-world-bruise"></span>
                <span class="ft-world-dizzy">x</span>
                <span class="ft-world-soot"></span>
                <span class="ft-world-crack"></span>
                <span class="ft-world-tear is-left"></span>
                <span class="ft-world-tear is-right"></span>
                <span class="ft-world-battle-crystal-loot is-gain"><b>+1</b></span>
                <span class="ft-world-battle-crystal-loot is-loss"><b>-1</b></span>
              </div>
            </div>
            <div class="ft-world-battle-stats">
              <div class="ft-world-battle-meter is-hp">
                <div class="ft-world-battle-meter-label"><span>HP</span><b></b></div>
                <div class="ft-world-battle-meter-track"><span></span></div>
              </div>
              <div class="ft-world-battle-meter is-mp">
                <div class="ft-world-battle-meter-label"><span>MP</span><b></b></div>
                <div class="ft-world-battle-meter-track"><span></span></div>
              </div>
            </div>
          `;
        }
        const fireball = node.querySelector(".ft-world-fireball");
        if (fireball) {
          fireball.style.setProperty("--world-facing", facing);
        }
        const statusNode = node.querySelector(".ft-world-battle-name span");
        if (statusNode) {
          statusNode.textContent = turn ? "Active caster" : "Battle ready";
        }
        const hpMeter = node.querySelector(".ft-world-battle-meter.is-hp");
        if (hpMeter) {
          hpMeter.style.setProperty("--meter-value", sharedWorldBattlePercent(hp));
          const hpValue = hpMeter.querySelector(".ft-world-battle-meter-label b");
          if (hpValue) hpValue.textContent = `${hp}/100`;
        }
        const mpMeter = node.querySelector(".ft-world-battle-meter.is-mp");
        if (mpMeter) {
          mpMeter.style.setProperty("--meter-value", sharedWorldBattlePercent(mp));
          const mpValue = mpMeter.querySelector(".ft-world-battle-meter-label b");
          if (mpValue) mpValue.textContent = `${mp}/100`;
        }
      };

      const sharedWorldBattleNodeForUser = (username = "", battle = {}) => {
        const { self, opponent } = sharedWorldBattlePlayersForView(battle || {});
        if (sharedWorldBattleUserKey(username) === sharedWorldBattleUserKey(self)) {
          return worldBattleLeft;
        }
        if (sharedWorldBattleUserKey(username) === sharedWorldBattleUserKey(opponent)) {
          return worldBattleRight;
        }
        return null;
      };

      const triggerSharedWorldBattleSpeech = (username = "", label = "", duration = 2050) => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(username, battle || {});
        if (!node) {
          return;
        }
        const callout = node.querySelector(".ft-world-battle-callout");
        if (callout) {
          callout.textContent = clean(label) || "Cast";
        }
        if (node._worldBattleSpeechTimer) {
          window.clearTimeout(node._worldBattleSpeechTimer);
          node._worldBattleSpeechTimer = 0;
        }
        node.classList.remove("is-speaking");
        void node.offsetWidth;
        node.classList.add("is-speaking");
        node._worldBattleSpeechTimer = window.setTimeout(() => {
          node.classList.remove("is-speaking");
          if (callout) {
            callout.textContent = "";
          }
          node._worldBattleSpeechTimer = 0;
        }, Math.max(900, Math.round(Number(duration) || 2050)));
      };

      const triggerSharedWorldBattleCast = (attacker = "", effect = "fireball", damage = 0) => {
        if (!worldBattleCard) {
          return;
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const { self } = sharedWorldBattlePlayersForView(battle || {});
        const castClass = sharedWorldBattleUserKey(attacker) === sharedWorldBattleUserKey(self)
          ? "is-casting-left"
          : "is-casting-right";
        const effectKey = clean(effect).toLowerCase();
        const strongDamage = Math.max(0, Math.round(Number(damage) || 0)) >= 30;
        const effectClass = effectKey === "inferno" || effectKey === "triple" || strongDamage
          ? "is-attack-inferno"
          : (effectKey === "laser" ? "is-attack-laser" : (effectKey === "meteor" ? "is-attack-meteor" : "is-attack-fire"));
        triggerSharedWorldBattleSpeech(attacker, sharedWorldBattleMoveLabel(effectKey, damage), effectClass === "is-attack-inferno" ? 2300 : 1900);
        worldBattleCard.classList.remove("is-casting-left", "is-casting-right", "is-attack-fire", "is-attack-laser", "is-attack-meteor", "is-attack-inferno");
        void worldBattleCard.offsetWidth;
        worldBattleCard.classList.add(castClass);
        worldBattleCard.classList.add(effectClass);
        const clearDelay = effectClass === "is-attack-inferno" ? 1280 : (effectClass === "is-attack-meteor" ? 980 : 850);
        queueSharedWorldBattleVisualTimeout(() => {
          if (worldBattleCard) {
                worldBattleCard.classList.remove(castClass);
                worldBattleCard.classList.remove(effectClass);
          }
        }, clearDelay);
      };

      const triggerSharedWorldBattleHealBurst = (caster = "") => {
        if (!worldBattleCard) {
          return;
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(caster, battle || {});
        if (!node) {
          return;
        }
        const anchor = node.querySelector(".ft-world-battle-character") || node;
        const cardRect = worldBattleCard.getBoundingClientRect();
        const anchorRect = anchor.getBoundingClientRect();
        const burst = document.createElement("div");
        burst.className = "ft-world-battle-heal-burst";
        burst.style.setProperty("--heal-left", `${anchorRect.left - cardRect.left + (anchorRect.width / 2)}px`);
        burst.style.setProperty("--heal-top", `${anchorRect.top - cardRect.top + 8}px`);
        burst.innerHTML = "<b>++++</b>";
        worldBattleCard.appendChild(burst);
        queueSharedWorldBattleVisualTimeout(() => {
          burst.remove();
        }, 3100);
      };

      const triggerSharedWorldBattleSkill = (entry = {}) => {
        const row = entry && typeof entry === "object" ? entry : {};
        const caster = clean(row.caster || row.attacker || "");
        const target = clean(row.target || "");
        const effect = clean(row.effect || row.skill || "").toLowerCase();
        const className = effect === "heal" || effect === "phoenix"
          ? "is-skill-heal"
          : (effect === "shield" ? "is-skill-shield" : (effect === "drain" ? "is-skill-drain" : "is-skill-inferno"));
        if (caster) {
          triggerSharedWorldBattleSpeech(caster, sharedWorldBattleMoveLabel(effect || row.skill || "inferno", 0), className === "is-skill-heal" ? 2500 : 1900);
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const casterNode = sharedWorldBattleNodeForUser(caster, battle || {});
        const targetNode = sharedWorldBattleNodeForUser(target, battle || {});
        const pulse = (node) => {
          if (!node) return;
          node.classList.remove(className);
          void node.offsetWidth;
          node.classList.add(className);
          queueSharedWorldBattleVisualTimeout(() => node.classList.remove(className), className === "is-skill-heal" ? 3200 : 1060);
        };
        pulse(casterNode);
        if (className === "is-skill-heal") {
          triggerSharedWorldBattleHealBurst(caster);
        }
        if (effect === "drain") {
          queueSharedWorldBattleVisualTimeout(() => pulse(targetNode), 90);
        }
      };

      const triggerSharedWorldBattleHit = (target = "") => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(target, battle || {});
        if (!node) {
          return;
        }
        node.classList.remove("is-hit");
        void node.offsetWidth;
        node.classList.add("is-hit");
        queueSharedWorldBattleVisualTimeout(() => {
          node.classList.remove("is-hit");
        }, 780);
      };

      const triggerSharedWorldBattleLoot = (attacker = "", target = "", loot = {}) => {
        const data = loot && typeof loot === "object" ? loot : {};
        const moved = Math.max(0, Math.round(Number(data.transferred || 0) || 0));
        if (moved <= 0) {
          return;
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const attackerNode = sharedWorldBattleNodeForUser(attacker, battle || {});
        const targetNode = sharedWorldBattleNodeForUser(target, battle || {});
        if (targetNode) {
          targetNode.classList.remove("is-loot-loss");
          void targetNode.offsetWidth;
          targetNode.classList.add("is-loot-loss");
          queueSharedWorldBattleVisualTimeout(() => targetNode.classList.remove("is-loot-loss"), 920);
        }
        if (attackerNode) {
          queueSharedWorldBattleVisualTimeout(() => {
            attackerNode.classList.remove("is-loot-gain");
            void attackerNode.offsetWidth;
            attackerNode.classList.add("is-loot-gain");
            queueSharedWorldBattleVisualTimeout(() => attackerNode.classList.remove("is-loot-gain"), 1220);
          }, 220);
        }
      };

      const triggerSharedWorldBattleTurnJump = (username = "") => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const node = sharedWorldBattleNodeForUser(username, battle || {});
        if (!node) {
          return;
        }
        node.classList.remove("is-turn-jump");
        void node.offsetWidth;
        node.classList.add("is-turn-jump");
        queueSharedWorldBattleVisualTimeout(() => {
          node.classList.remove("is-turn-jump");
        }, 1040);
      };

      const sharedWorldBattleHitEventFromLog = (item = {}) => {
        const row = item && typeof item === "object" ? item : {};
        let attacker = clean(row.attacker || "");
        let target = clean(row.target || "");
        let effect = clean(row.effect || "");
        let damage = Math.max(0, Math.round(Number(row.damage) || 0));
        const loot = row.loot && typeof row.loot === "object" ? row.loot : {};
        const text = clean(row.text || "");
        if ((!attacker || !target) && text) {
          const match = text.match(/^(.+?)\s+hit\s+(.+?)(?:\s+with\s+([a-z_-]+))?\s+for\s+(\d+)/i);
          if (match) {
            attacker = attacker || clean(match[1]);
            target = target || clean(match[2]);
            effect = effect || clean(match[3]);
            damage = damage || Math.max(0, Math.round(Number(match[4]) || 0));
          }
        }
        if (!effect && /laser/i.test(text)) {
          effect = "laser";
        }
        if (!effect && (/inferno/i.test(text) || damage >= 30)) {
          effect = "inferno";
        }
        return { attacker, target, effect: effect || "fireball", damage, loot };
      };

      const renderSharedWorldBattleLog = (battle = {}) => {
        if (!worldBattleLog) {
          return;
        }
        const logs = Array.isArray(battle.log) ? battle.log.slice(-8) : [];
        worldBattleLog.innerHTML = "";
        logs.forEach((item) => {
          const row = document.createElement("div");
          row.textContent = clean(item && item.text) || "Battle event.";
          worldBattleLog.appendChild(row);
        });
        const last = logs[logs.length - 1] || null;
        const key = last ? `${clean(battle.id)}|${clean(last.event_id || last.eventId || "") || `${clean(last.seq)}|${clean(last.at)}|${clean(last.type)}|${clean(last.text)}`}` : "";
        if (key && key !== sharedWorldBattleLastLogKey) {
          sharedWorldBattleLastLogKey = key;
          if (clean(last.type) === "hit") {
            const { attacker, target, effect, damage, loot } = sharedWorldBattleHitEventFromLog(last);
            triggerSharedWorldBattleCast(attacker, effect, damage);
            triggerSharedWorldBattleHit(target);
            triggerSharedWorldBattleLoot(attacker, target, loot);
          } else if (clean(last.type) === "skill") {
            triggerSharedWorldBattleSkill(last);
          }
        }
      };

      const renderSharedWorldBattleQuestionText = (battle = {}, question = {}, status = "active", phase = "question", self = "") => {
        if (!worldBattleQuestion) {
          return;
        }
        const putPlain = (text = "") => {
          worldBattleQuestion.classList.remove("has-structured");
          worldBattleQuestion.textContent = text;
        };
        if (status === "finished") {
          const reward = battle.reward && typeof battle.reward === "object" ? battle.reward : {};
          const moved = Math.max(0, Math.round(Number(reward.transferred || 0) || 0));
          putPlain(clean(battle.message) || `Battle complete. Crystal transfer: ${moved}.`);
          return;
        }
        if (phase === "reveal") {
          putPlain(`Correct answer: ${clean(question.answer_text || "") || "..."}`);
          return;
        }
        const meaning = clean(question.meaning || "");
        const wordType = clean(question.type || "");
        const questionKind = clean(question.training_kind || question.trainingKind || question.kind || question.battle_kind || question.battleKind || "").toLowerCase();
        const promptText = clean(question.prompt || "The referee is preparing a word.");
        if (!meaning && !wordType && !questionKind && !sharedWorldTrainingQuestionIsAudioInput(question)) {
          putPlain(promptText);
          return;
        }
        worldBattleQuestion.classList.add("has-structured");
        worldBattleQuestion.innerHTML = "";
        const card = document.createElement("span");
        card.className = "ft-world-battle-question-card";
        const line = document.createElement("span");
        line.className = "ft-world-battle-question-line";
        line.textContent = promptText;
        const chips = document.createElement("span");
        chips.className = "ft-world-battle-question-chips";
        if (questionKind) {
          const chip = document.createElement("span");
          chip.className = "ft-world-battle-question-chip is-kind";
          const label = document.createElement("b");
          label.textContent = "Mode";
          const value = document.createElement("span");
          value.textContent = questionKind.replace(/_/g, " ");
          chip.append(label, value);
          chips.appendChild(chip);
        }
        if (wordType) {
          const chip = document.createElement("span");
          chip.className = "ft-world-battle-question-chip is-type";
          const label = document.createElement("b");
          label.textContent = "Loai tu";
          const value = document.createElement("span");
          value.textContent = wordType;
          chip.append(label, value);
          chips.appendChild(chip);
        }
        if (meaning) {
          const chip = document.createElement("span");
          chip.className = "ft-world-battle-question-chip is-meaning";
          const label = document.createElement("b");
          label.textContent = "Nghia";
          const value = document.createElement("span");
          value.textContent = meaning;
          chip.append(label, value);
          chips.appendChild(chip);
        }
        if (sharedWorldTrainingQuestionIsAudioInput(question)) {
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className = "ft-world-battle-question-chip is-audio";
          const label = document.createElement("b");
          label.textContent = "Audio";
          const value = document.createElement("span");
          value.textContent = "Play";
          chip.append(label, value);
          chip.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            void playSharedWorldTrainingAudioQuestion(question);
          });
          chips.appendChild(chip);
        }
        card.append(line, chips);
        worldBattleQuestion.appendChild(card);
      };

      const sharedWorldBattleAnswerPlaceholder = (question = {}, phase = "question", canAnswer = false) => {
        if (phase === "reveal") {
          return "Correct answer is being revealed...";
        }
        if (!canAnswer) {
          return "Wait for your turn...";
        }
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || row.battle_kind || row.battleKind || "").toLowerCase();
        if (kind === "translate_vi" || kind === "translate_vi_speech" || row.server_speech || row.serverSpeech) {
          return "Type the Vietnamese answer...";
        }
        if (kind === "audio_word" || kind === "audio_sentence" || clean(row.audio_text || row.audioText)) {
          return "Listen, then type the English answer...";
        }
        if (kind === "read_word" || kind === "read_sentence" || kind === "speak_vi_word" || kind === "speak_vi_sentence" || row.local_speech || row.localSpeech) {
          return "Type the spoken English answer...";
        }
        if (kind === "sentence") {
          return "Type the English sentence...";
        }
        return "Type the English answer...";
      };

      const sharedWorldBattleQuestionSupportsSpeechInput = (question = {}) => {
        const row = question && typeof question === "object" ? question : {};
        const kind = clean(row.training_kind || row.trainingKind || row.kind || row.battle_kind || row.battleKind || "").toLowerCase();
        return Boolean(
          kind === "translate_vi"
          || kind === "translate_vi_speech"
          || kind === "read_word"
          || kind === "read_sentence"
          || kind === "speak_vi_word"
          || kind === "speak_vi_sentence"
          || row.server_speech
          || row.serverSpeech
          || row.local_speech
          || row.localSpeech
          || clean(row.read_text || row.readText)
        );
      };

      const setSharedWorldBattleResultOpen = (open = false) => {
        if (!worldBattleResult) {
          return;
        }
        const active = Boolean(open);
        worldBattleResult.classList.toggle("is-open", active);
        worldBattleResult.setAttribute("aria-hidden", active ? "false" : "true");
      };

      const renderSharedWorldBattleResult = (battle = {}, self = "") => {
        if (!worldBattleResult) {
          return;
        }
        const winner = clean(battle.winner || "");
        const loser = clean(battle.loser || "");
        const selfWins = sharedWorldBattleUserKey(winner) === sharedWorldBattleUserKey(self);
        const profiles = battle.profiles && typeof battle.profiles === "object" ? battle.profiles : {};
        const winnerProfile = profiles[winner] || profiles[sharedWorldBattleUserKey(winner)] || {};
        const loserProfile = profiles[loser] || profiles[sharedWorldBattleUserKey(loser)] || {};
        const winnerName = clean(winnerProfile.display_name || winnerProfile.displayName || winner || "Winner");
        const loserName = clean(loserProfile.display_name || loserProfile.displayName || loser || "Opponent");
        const reward = battle.reward && typeof battle.reward === "object" ? battle.reward : {};
        const moved = Math.max(0, Math.round(Number(reward.transferred || 0) || 0));
        worldBattleResult.classList.toggle("is-loss", !selfWins);
        if (worldBattleResultKicker) {
          worldBattleResultKicker.textContent = selfWins ? "Arena victory" : "Arena defeat";
        }
        if (worldBattleResultTitle) {
          worldBattleResultTitle.textContent = selfWins ? "Victory" : "Defeat";
        }
        if (worldBattleResultCopy) {
          const transfer = moved ? `${moved} crystal${moved === 1 ? "" : "s"} moved from ${loserName} to ${winnerName}.` : "No crystals were transferred.";
          worldBattleResultCopy.textContent = `${winnerName} wins this Fireball Vocabulary Battle. ${transfer}`;
        }
        if (worldBattleResultReward) {
          worldBattleResultReward.innerHTML = "";
          const items = Array.isArray(reward.items) ? reward.items : [];
          if (items.length) {
            items.forEach((item) => {
              const pill = document.createElement("span");
              const quantity = Math.max(0, Math.round(Number(item && item.quantity) || 0));
              pill.textContent = `${selfWins ? "+" : "-"}${quantity} ${clean(item && item.name) || "Crystal"}`;
              worldBattleResultReward.appendChild(pill);
            });
          } else {
            const pill = document.createElement("span");
            pill.textContent = moved ? `${selfWins ? "+" : "-"}${moved} battle crystal${moved === 1 ? "" : "s"}` : "No crystal moved";
            worldBattleResultReward.appendChild(pill);
          }
        }
        setSharedWorldBattleResultOpen(true);
      };

      const dismissSharedWorldBattleResult = () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (battle && clean(battle.id)) {
          sharedWorldBattleDismissedFinishedId = clean(battle.id);
        }
        setSharedWorldBattleResultOpen(false);
        if (worldBattleModal) {
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
        }
        if (worldBattleAnswerForm) {
          worldBattleAnswerForm.classList.remove("is-your-turn");
        }
        void refreshSharedWorld();
      };

      const hardCloseSharedWorldBattleUi = () => {
        stopSharedWorldBattleCountdown();
        stopSharedWorldBattlePolling();
        clearSharedWorldBattleVisualState();
        sharedWorldBattleLoading = false;
        sharedWorldBattleLoadingAt = 0;
        sharedWorldBattleRequestSeq += 1;
        sharedWorldBattleFinishing = false;
        sharedWorldBattleInviteId = "";
        sharedWorldBattleLastLogKey = "";
        sharedWorldBattleLastTurnKey = "";
        sharedWorldBattleState = null;
        sharedWorldActiveBattlePairs = [];
        sharedWorldBattleLinkNodes.clear();
        if (worldBattleLinks) {
          worldBattleLinks.innerHTML = "";
        }
        if (worldInvitePanel) {
          worldInvitePanel.hidden = true;
        }
        setSharedWorldBattleResultOpen(false);
        if (worldBattleModal) {
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
        }
        if (worldBattleAnswerForm) {
          worldBattleAnswerForm.classList.remove("is-your-turn");
        }
        if (worldBattleAnswer) {
          worldBattleAnswer.disabled = true;
          worldBattleAnswer.value = "";
          worldBattleAnswer.dataset.turnKey = "";
        }
        if (worldBattleSubmit) {
          worldBattleSubmit.disabled = true;
        }
        if (worldBattleSpeechMic) {
          worldBattleSpeechMic.hidden = true;
          worldBattleSpeechMic.disabled = true;
        }
        try {
          if (
            typeof browserSpeechInputTarget !== "undefined"
            && browserSpeechInputTarget === worldBattleAnswer
            && typeof cancelBrowserMultilingualInputDictation === "function"
          ) {
            cancelBrowserMultilingualInputDictation();
          }
        } catch (error) {
        }
      };

      const renderSharedWorldBattle = (payload = {}) => {
        if (!worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        sharedWorldBattleState = payload && typeof payload === "object" ? payload : null;
        if (sharedWorldBattleState) {
          sharedWorldBattleState.receivedAt = Date.now();
        }
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        const activeBattle = battle && clean(battle.id);
        if (worldInvitePanel) {
          const incoming = !activeBattle && Array.isArray(sharedWorldBattleState && sharedWorldBattleState.incoming_invites)
            ? sharedWorldBattleState.incoming_invites[0]
            : null;
          if (incoming) {
            sharedWorldBattleInviteId = clean(incoming.id);
            if (worldInviteTitle) {
              worldInviteTitle.textContent = clean(incoming.game_name || incoming.gameName) || sharedWorldBattleGameLabel(incoming.game);
            }
            if (worldInviteCopy) {
              worldInviteCopy.textContent = `${sharedWorldInviteProfileLabel(incoming, "from")} asks: ${clean(incoming.message) || "Would you like to battle?"}`;
            }
            worldInvitePanel.hidden = false;
          } else {
            sharedWorldBattleInviteId = "";
            worldInvitePanel.hidden = true;
          }
        }
        if (!activeBattle && Array.isArray(sharedWorldBattleState && sharedWorldBattleState.outgoing_invites) && sharedWorldBattleState.outgoing_invites.length) {
          const outgoing = sharedWorldBattleState.outgoing_invites[0] || {};
          setSharedWorldStatus(`Battle invite pending for ${sharedWorldInviteProfileLabel(outgoing, "to")}.`, "ok");
        }
        if (!worldBattleModal) {
          return;
        }
        if (!activeBattle) {
          setSharedWorldBattleResultOpen(false);
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
          if (worldBattleAnswerForm) {
            worldBattleAnswerForm.classList.remove("is-your-turn");
          }
          stopSharedWorldBattleCountdown();
          stopSharedWorldBattlePolling();
          return;
        }
        if (clean(battle.status) === "finished" && sharedWorldBattleDismissedFinishedId === clean(battle.id)) {
          setSharedWorldBattleResultOpen(false);
          worldBattleModal.classList.remove("is-open");
          worldBattleModal.setAttribute("aria-hidden", "true");
          if (worldBattleAnswerForm) {
            worldBattleAnswerForm.classList.remove("is-your-turn");
          }
          stopSharedWorldBattleCountdown();
          stopSharedWorldBattlePolling();
          return;
        }
        if (clean(battle.status) === "active") {
          sharedWorldBattleDismissedFinishedId = "";
        }
        worldBattleModal.classList.add("is-open");
        worldBattleModal.setAttribute("aria-hidden", "false");
        const { self, opponent } = sharedWorldBattlePlayersForView(battle);
        renderSharedWorldBattlePlayer(worldBattleLeft, battle, self, "left");
        renderSharedWorldBattlePlayer(worldBattleRight, battle, opponent, "right");
        const question = battle.question && typeof battle.question === "object" ? battle.question : {};
        const status = clean(battle.status || "active");
        const canAnswer = status === "active" && Boolean(question.can_answer);
        const phase = clean(battle.phase || "question");
        const turnJumpKey = `${clean(battle.id)}|${clean(battle.turn)}|${phase}|${clean(question.created_at || "")}`;
        if (status === "active" && clean(battle.turn) && phase !== "reveal" && turnJumpKey !== sharedWorldBattleLastTurnKey) {
          sharedWorldBattleLastTurnKey = turnJumpKey;
          triggerSharedWorldBattleTurnJump(battle.turn);
        }
        const turnName = clean(((battle.profiles || {})[battle.turn] || {}).display_name || battle.turn || "");
        if (worldBattlePhase) {
          if (status === "finished") {
            worldBattlePhase.textContent = clean(battle.winner) === self ? "Victory secured" : "Battle finished";
          } else if (phase === "reveal") {
            worldBattlePhase.textContent = "Answer reveal - next turn soon";
          } else if (canAnswer) {
            worldBattlePhase.textContent = phase === "steal" ? "Steal chance - answer now" : "Your turn - cast the word";
          } else {
            worldBattlePhase.textContent = `Waiting for ${turnName || "opponent"}`;
          }
        }
        renderSharedWorldBattleQuestionText(battle, question, status, phase, self);
        if (worldBattleAnswer) {
          worldBattleAnswer.disabled = !canAnswer;
          worldBattleAnswer.placeholder = sharedWorldBattleAnswerPlaceholder(question, phase, canAnswer);
          const turnKey = `${clean(battle.id)}|${clean(battle.turn)}|${phase}|${clean(question.created_at)}`;
          if (canAnswer && worldBattleAnswer.dataset.turnKey !== turnKey) {
            worldBattleAnswer.dataset.turnKey = turnKey;
            worldBattleAnswer.value = "";
            window.setTimeout(() => worldBattleAnswer && worldBattleAnswer.focus(), 60);
          }
        }
        if (worldBattleSubmit) {
          worldBattleSubmit.disabled = !canAnswer;
        }
        if (worldBattleSpeechMic) {
          const showSpeechMic = canAnswer && sharedWorldBattleQuestionSupportsSpeechInput(question);
          worldBattleSpeechMic.hidden = !showSpeechMic;
          worldBattleSpeechMic.disabled = !showSpeechMic;
          worldBattleSpeechMic.title = showSpeechMic ? "Speak this battle answer" : "Speech answer unavailable for this question";
        }
        if (worldBattleAnswerForm) {
          worldBattleAnswerForm.classList.toggle("is-your-turn", canAnswer);
          worldBattleAnswerForm.classList.toggle("is-speech-ready", Boolean(canAnswer && sharedWorldBattleQuestionSupportsSpeechInput(question)));
        }
        const selfMp = Math.max(0, Math.round(Number((battle.mp || {})[self] || 0) || 0));
        if (worldBattleSkills) {
          worldBattleSkills.querySelectorAll("[data-world-skill]").forEach((button) => {
            button.disabled = status !== "active" || selfMp < 100;
            button.title = selfMp >= 100 ? "Cast this full-mana skill." : "Requires 100 MP.";
          });
        }
        renderSharedWorldBattleLog(battle);
        if (status === "active") {
          sharedWorldBattleFinishing = false;
          setSharedWorldBattleResultOpen(false);
          startSharedWorldBattleCountdown();
        } else {
          stopSharedWorldBattleCountdown();
          stopSharedWorldBattlePolling();
          renderSharedWorldBattleResult(battle, self);
        }
      };

      const refreshSharedWorldBattle = async () => {
        if (!authToken || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        const now = Date.now();
        if (sharedWorldBattleLoading && now - sharedWorldBattleLoadingAt < 900) {
          return;
        }
        sharedWorldBattleLoading = true;
        sharedWorldBattleLoadingAt = now;
        const requestSeq = ++sharedWorldBattleRequestSeq;
        try {
          const response = await fetchAuthJson(`/world/battle/state${activeWorldActorQuery()}`, { timeoutMs: 0 });
          if (requestSeq !== sharedWorldBattleRequestSeq || !worldModal || !worldModal.classList.contains("is-open")) {
            return;
          }
          const result = response && response.payload ? response.payload : response;
          renderSharedWorldBattle(result);
        } catch (error) {
          const message = error && error.message ? error.message : "";
          scheduleSharedWorldReconnect(message || "Could not load battle state.");
        } finally {
          if (requestSeq === sharedWorldBattleRequestSeq) {
            sharedWorldBattleLoading = false;
            sharedWorldBattleLoadingAt = 0;
          }
        }
      };

      const sendSharedWorldBattleInvite = async (game = "fireball_vocab", message = "") => {
        const target = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
        if (!target || clean(target.username).toLowerCase() === clean(activeWorldUsername()).toLowerCase()) {
          setSharedWorldStatus("Select another learner before sending a battle invite.", "error");
          return;
        }
        if (target.isPlaying) {
          setSharedWorldStatus(`${sharedWorldTargetLabel(target)} is already playing a battle. Choose another learner.`, "error");
          return;
        }
        const approachPoint = sharedWorldNearTargetPoint(target);
        if (approachPoint) {
          void moveSharedWorldPlayer(approachPoint);
        }
        const body = {
          target: clean(target.username),
          game: clean(game || "fireball_vocab"),
          message: clean(message) || "Would you like to play Fireball Vocabulary Battle with me?",
          ...activeWorldActorPayload(),
        };
        try {
          const response = await fetchAuthJson("/world/battle/invite", {
            method: "POST",
            body: JSON.stringify(body),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorldBattle(result);
          if (result && result.battle) {
            setSharedWorldStatus("Battle accepted automatically. Arena opened.", "ok");
          } else {
            setSharedWorldStatus(`Battle invite sent to ${sharedWorldTargetLabel(target)}.`, "ok");
          }
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not send battle invite.", "error");
        }
      };

      const respondSharedWorldBattleInvite = async (accept = false) => {
        if (!sharedWorldBattleInviteId) {
          return;
        }
        try {
          const response = await fetchAuthJson("/world/battle/respond", {
            method: "POST",
            body: JSON.stringify({ invite_id: sharedWorldBattleInviteId, accept: Boolean(accept), ...activeWorldActorPayload() }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorldBattle(result);
          if (result && result.forced_accept) {
            setSharedWorldStatus("Second decline rule triggered. Battle started automatically.", "ok");
          } else {
            setSharedWorldStatus(accept ? "Battle accepted." : "Battle declined. The next different invite will auto-accept.", accept ? "ok" : "");
          }
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not respond to battle invite.", "error");
        }
      };

      const submitSharedWorldBattleAnswer = async () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active" || !worldBattleAnswer) {
          return;
        }
        const answer = clean(worldBattleAnswer.value);
        worldBattleAnswer.value = "";
        try {
          const response = await fetchAuthJson("/world/battle/answer", {
            method: "POST",
            body: JSON.stringify({ battle_id: clean(battle.id), answer, ...activeWorldActorPayload() }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorldBattle(result);
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not cast answer.", "error");
        }
      };

      const castSharedWorldBattleSkill = async (skill = "") => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active") {
          return;
        }
        try {
          const response = await fetchAuthJson("/world/battle/skill", {
            method: "POST",
            body: JSON.stringify({ battle_id: clean(battle.id), skill: clean(skill), ...activeWorldActorPayload() }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          renderSharedWorldBattle(result);
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not cast skill.", "error");
        }
      };

      const forfeitSharedWorldBattle = async (silent = false) => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active") {
          return;
        }
        try {
          const response = await fetchAuthJson("/world/battle/forfeit", {
            method: "POST",
            body: JSON.stringify({ battle_id: clean(battle.id), ...activeWorldActorPayload() }),
            timeoutMs: 20000,
          });
          const result = response && response.payload ? response.payload : response;
          if (silent) {
            sharedWorldBattleState = result;
          } else {
            renderSharedWorldBattle(result);
          }
          if (!silent) {
            setSharedWorldStatus("Battle forfeited. Wager transferred to the opponent.", "error");
          }
        } catch (error) {
          if (!silent) {
            setSharedWorldStatus(error && error.message ? error.message : "Could not forfeit battle.", "error");
          }
        }
      };

      const forfeitSharedWorldBattleOnUnload = () => {
        const battle = sharedWorldBattleState && sharedWorldBattleState.battle;
        if (!battle || clean(battle.status) !== "active" || !authToken) {
          return;
        }
        const candidates = WHISPER_SERVER_CANDIDATES.length ? WHISPER_SERVER_CANDIDATES : [WHISPER_SERVER_URL];
        const base = candidates[0] || "";
        if (!base) {
          return;
        }
        try {
          fetch(`${base}/world/battle/forfeit`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${authToken}`,
              ...(antiRobotToken ? { [ANTI_ROBOT_HEADER]: antiRobotToken } : {}),
            },
            body: JSON.stringify({ battle_id: clean(battle.id), ...activeWorldActorPayload() }),
            keepalive: true,
            mode: "cors",
          });
        } catch (error) {
          // Best-effort forfeit on tab close.
        }
      };

      const sharedWorldSkinArtClass = (skin = {}) => `is-${clean(skin.id || skin.name).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "neon-orb"}`;

      const sharedWorldCrystalQuantity = () => {
        const inventory = sharedWorldInventory && sharedWorldInventory.inventory ? sharedWorldInventory.inventory : sharedWorldInventory;
        const items = inventory && inventory.items && typeof inventory.items === "object" ? inventory.items : {};
        const item = items[sharedWorldVocabularyCrystalId] || items.space_v_crystal || items.vocabulary_crystal || {};
        return Math.max(0, Math.round(Number(item.quantity || item.count || 0) || 0));
      };

      const sharedWorldInventoryToneForId = (id = "") => {
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

      const REWARD_ITEM_DISPLAY = {
        crystal: { name: "Golden Axe", use: "Forged by defeating vocabulary slimes and clean answers." },
        vocab_crystal_yellow: { name: "Golden Axe", use: "Forged when a new vocabulary word is learned cleanly." },
        vocab_crystal_blue: { name: "Silver Axe", use: "Forged when a word returns after 10 drills and 5 shuffle rounds and is answered correctly." },
        vocab_crystal_green: { name: "Silver Axe", use: "Forged by correctly recalling vocabulary already stored in memory." },
        leaderboard_space_v_crystal: { name: "Golden Axe", use: "Awarded for Space_V leaderboard standing." },
        leaderboard_crystal_rare: { name: "Golden Axe", use: "Awarded from leaderboard ranks for strong first-time vocabulary progress." },
        leaderboard_crystal_easy: { name: "Silver Axe", use: "Awarded from leaderboard ranks for steady vocabulary review progress." },
        leaderboard_space_q_crystal: { name: "Golden Magic Book", use: "Awarded from Space_Q leaderboard ranks." },
        space_q_spellbook_gold: { name: "Golden Magic Book", use: "Earned by completing a new Space_Q node correctly and awarded from Space_Q leaderboard ranks." },
        space_q_spellbook_silver: { name: "Silver Magic Book", use: "Earned by completing a Space_Q review node correctly." },
        paragraph_crystal_golden: { name: "Golden Magic Bow", use: "Legacy Space_P reward now displayed as a Golden Magic Bow." },
        space_p_bow_gold: { name: "Golden Magic Bow", use: "Earned by completing a new Space_P sentence correctly and awarded from Space_P leaderboard ranks." },
        space_p_bow_silver: { name: "Silver Magic Bow", use: "Earned by correctly recalling a Space_P sentence during review." },
        space_s_sax_gold: { name: "Golden Devil Wings", use: "Earned by reading a new Space_S speaking sentence correctly and awarded from Space_S leaderboard ranks." },
        space_s_sax_silver: { name: "Silver Devil Wings", use: "Earned by correctly recalling a Space_S speaking sentence during review and awarded from Space_S leaderboard ranks." },
        space_l_sword_gold: { name: "Golden Great Sword", use: "Earned by completing a new Space_L listening sentence correctly and awarded from Space_L leaderboard ranks." },
        space_l_sword_silver: { name: "Silver Great Sword", use: "Earned by correctly recalling a Space_L listening sentence during review and awarded from Space_L leaderboard ranks." },
        space_w_cup_gold: { name: "Golden Mastery Cup", use: "Earned when a new Space_W sentence is answered correctly the first time." },
        space_w_cup_iron: { name: "Silver Practice Cup", use: "Earned by correctly recalling a Space_W sentence during review." },
      };
      const mergeRewardDisplayItems = (list) => {
        const merged = [];
        const byName = new Map();
        (Array.isArray(list) ? list : []).forEach((it) => {
          const name = clean(it && it.name) || "Reward Item";
          if (byName.has(name)) {
            byName.get(name).quantity += Math.max(0, Math.floor(Number(it.quantity || 0) || 0));
          } else {
            const copy = { ...it, quantity: Math.max(0, Math.floor(Number(it.quantity || 0) || 0)) };
            byName.set(name, copy);
            merged.push(copy);
          }
        });
        return merged;
      };
      const canonicalRewardName = (id, fallback) => {
        const key = clean(id).toLowerCase();
        return (REWARD_ITEM_DISPLAY[key] && REWARD_ITEM_DISPLAY[key].name) || clean(fallback) || "Reward Item";
      };
      const canonicalRewardUse = (id, fallback) => {
        const key = clean(id).toLowerCase();
        return (REWARD_ITEM_DISPLAY[key] && REWARD_ITEM_DISPLAY[key].use) || preserveQuestionText(fallback) || "Stores learning energy for future item upgrades.";
      };

      const sharedWorldInventoryItemsForDisplay = () => {
        const inventory = sharedWorldInventory && sharedWorldInventory.inventory ? sharedWorldInventory.inventory : sharedWorldInventory;
        const items = Object.values((inventory && inventory.items) || {})
          .map((item) => ({
            id: clean(item && (item.id || item.item_id) || "crystal").toLowerCase() || "crystal",
            name: canonicalRewardName(item && (item.id || item.item_id), item && item.name),
            use: canonicalRewardUse(item && (item.id || item.item_id), item && (item.use || item.description)),
            quantity: Math.max(0, Math.floor(Number(item && (item.quantity || item.count) || 0) || 0)),
          }))
          .filter((item) => item.quantity > 0);
        if (!items.length) {
          items.push({
            id: sharedWorldVocabularyCrystalId,
            name: "Vocabulary Crystal",
            use: "Currency for QM-City transformations.",
            quantity: 0,
          });
        }
        return mergeRewardDisplayItems(items).sort((a, b) => {
          const order = ["space_q_spellbook_gold", "leaderboard_space_q_crystal", "space_q_spellbook_silver", "space_p_bow_gold", "paragraph_crystal_golden", "space_p_bow_silver", "space_s_sax_gold", "space_s_sax_silver", "space_l_sword_gold", "space_l_sword_silver", "space_w_cup_gold", "space_w_cup_iron", "leaderboard_space_v_crystal", "leaderboard_crystal_rare", "leaderboard_crystal_easy", "vocab_crystal_yellow", "vocab_crystal_blue", "vocab_crystal_green", "crystal"];
          return (order.indexOf(a.id) < 0 ? 99 : order.indexOf(a.id)) - (order.indexOf(b.id) < 0 ? 99 : order.indexOf(b.id));
        });
      };

      const renderSharedWorldInventoryInfo = (item = null) => {
        if (!worldInventoryInfo) {
          return;
        }
        const data = item || sharedWorldInventoryItemsForDisplay()[0];
        worldInventoryInfo.innerHTML = "";
        const kicker = document.createElement("span");
        kicker.className = "ft-inventory-info-kicker";
        kicker.textContent = "QM-City currency";
        const name = document.createElement("span");
        name.className = "ft-inventory-info-name";
        name.textContent = clean(data && data.name) || "Vocabulary Crystal";
        const use = document.createElement("span");
        use.className = "ft-inventory-info-use";
        use.textContent = preserveQuestionText(data && data.use) || "Currency for QM-City transformations.";
        const count = document.createElement("span");
        count.className = "ft-inventory-info-count";
        count.textContent = `Owned x${Math.max(0, Math.floor(Number(data && data.quantity || 0) || 0))}`;
        worldInventoryInfo.append(kicker, name, use, count);
      };

      const renderSharedWorldInventoryPanel = () => {
        if (worldCrystalCount) {
          const count = sharedWorldCrystalQuantity();
          worldCrystalCount.textContent = `${count} vocabulary crystal${count === 1 ? "" : "s"} available for transformations.`;
        }
        if (!worldInventoryGrid) {
          return;
        }
        const items = sharedWorldInventoryItemsForDisplay();
        worldInventoryGrid.innerHTML = "";
        for (let index = 0; index < 24; index += 1) {
          const item = items[index] || null;
          const slot = document.createElement(item ? "button" : "span");
          if (item) {
            slot.type = "button";
          }
          slot.className = "ft-inventory-slot";
          if (item) {
            const tone = sharedWorldInventoryToneForId(item.id);
            slot.classList.add("has-item");
            slot.setAttribute("aria-label", `${item.name}, owned ${item.quantity}`);
            slot.innerHTML = `
              <span class="ft-inventory-gem ${tone ? `is-${tone}` : ""}" aria-hidden="true"></span>
              <span class="ft-inventory-slot-count">x${item.quantity}</span>
            `;
            const showItem = () => renderSharedWorldInventoryInfo(item);
            slot.addEventListener("mouseenter", showItem);
            slot.addEventListener("focus", showItem);
            slot.addEventListener("click", showItem);
          } else {
            slot.setAttribute("aria-hidden", "true");
          }
          worldInventoryGrid.appendChild(slot);
        }
        renderSharedWorldInventoryInfo(items[0]);
      };

      const renderSharedWorldPocketInfo = (item = null) => {
        if (!worldPocketInfo) {
          return;
        }
        const data = item || sharedWorldInventoryItemsForDisplay()[0];
        worldPocketInfo.innerHTML = "";
        const kicker = document.createElement("span");
        kicker.className = "ft-inventory-info-kicker";
        kicker.textContent = "Crystal inventory";
        const name = document.createElement("span");
        name.className = "ft-inventory-info-name";
        name.textContent = clean(data && data.name) || "Vocabulary Crystal";
        const use = document.createElement("span");
        use.className = "ft-inventory-info-use";
        use.textContent = preserveQuestionText(data && data.use) || "Currency for QM-City transformations.";
        const count = document.createElement("span");
        count.className = "ft-inventory-info-count";
        count.textContent = `Owned x${Math.max(0, Math.floor(Number(data && data.quantity || 0) || 0))}`;
        worldPocketInfo.append(kicker, name, use, count);
      };

      const renderSharedWorldInventoryModal = () => {
        if (worldLoadoutName) {
          const fullName = clean(currentAuthProfile && (currentAuthProfile.full_name || currentAuthProfile.fullName || currentAuthProfile.display_name || currentAuthProfile.displayName));
          worldLoadoutName.textContent = fullName || clean(currentAuthUsername) || "Character";
        }
        if (worldPocketCount) {
          const count = sharedWorldCrystalQuantity();
          worldPocketCount.textContent = `${count} vocabulary crystal${count === 1 ? "" : "s"} available.`;
        }
        if (!worldPocketGrid) {
          return;
        }
        const items = sharedWorldInventoryItemsForDisplay();
        worldPocketGrid.innerHTML = "";
        for (let index = 0; index < 25; index += 1) {
          const item = items[index] || null;
          const slot = document.createElement(item ? "button" : "span");
          if (item) {
            slot.type = "button";
          }
          slot.className = "ft-inventory-slot";
          if (item) {
            const tone = sharedWorldInventoryToneForId(item.id);
            slot.classList.add("has-item");
            slot.setAttribute("aria-label", `${item.name}, owned ${item.quantity}`);
            slot.innerHTML = `
              <span class="ft-inventory-gem ${tone ? `is-${tone}` : ""}" aria-hidden="true"></span>
              <span class="ft-inventory-slot-count">x${item.quantity}</span>
            `;
            const showItem = () => renderSharedWorldPocketInfo(item);
            slot.addEventListener("mouseenter", showItem);
            slot.addEventListener("focus", showItem);
            slot.addEventListener("click", showItem);
          } else {
            slot.setAttribute("aria-hidden", "true");
          }
          worldPocketGrid.appendChild(slot);
        }
        renderSharedWorldPocketInfo(items[0]);
        renderSharedWorldTrainingLoadoutPanel();
      };

      const openSharedWorldInventory = async () => {
        setSharedWorldCloseMenuOpen(false);
        renderSharedWorldInventoryModal();
        if (worldInventoryModal) {
          worldInventoryModal.classList.add("is-open");
          worldInventoryModal.setAttribute("aria-hidden", "false");
        }
        void loadSharedWorldInventory();
        void loadSharedWorldTrainingInventorySnapshot();
      };

      const closeSharedWorldInventory = () => {
        if (worldInventoryModal) {
          worldInventoryModal.classList.remove("is-open");
          worldInventoryModal.setAttribute("aria-hidden", "true");
        }
      };

      const loadSharedWorldInventory = async () => {
        if (!authToken) {
          return null;
        }
        try {
          const response = await fetchAuthJson("/inventory");
          sharedWorldInventory = response && response.payload ? response.payload : response;
          renderSharedWorldShop();
          renderSharedWorldInventoryModal();
          return sharedWorldInventory;
        } catch (error) {
          sharedWorldInventory = null;
          renderSharedWorldShop();
          renderSharedWorldInventoryModal();
          return null;
        }
      };

      const loadSharedWorldTrainingInventorySnapshot = async () => {
        if (!authToken) {
          return null;
        }
        try {
          const response = await fetchAuthJson("/world/training/state", { timeoutMs: 0, silentTimeout: true });
          const result = response && response.payload ? response.payload : response;
          if (result && result.training) {
            sharedWorldTrainingState = { training: result.training };
            renderSharedWorldTrainingLoadoutPanel();
            renderSharedWorldTrainingQuickSkill();
          }
          return result;
        } catch (error) {
          renderSharedWorldTrainingLoadoutPanel();
          renderSharedWorldTrainingQuickSkill();
          return null;
        }
      };

      const normalizeSharedWorldKeyboardPass = (payload = {}) => {
        const source = payload && typeof payload === "object" ? payload : {};
        return {
          enabled: Boolean(source.enabled),
          expires_at: clean(source.expires_at || source.expiresAt || ""),
          remaining_seconds: Math.max(0, Math.floor(Number(source.remaining_seconds || source.remainingSeconds || 0) || 0)),
          cost: Math.max(1, Math.floor(Number(source.cost || 10) || 10)),
        };
      };

      const sharedWorldKeyboardRemainingMs = () => {
        const expires = Date.parse(sharedWorldKeyboardPass.expires_at || "");
        if (Number.isFinite(expires)) {
          return Math.max(0, expires - Date.now());
        }
        return Math.max(0, Number(sharedWorldKeyboardPass.remaining_seconds || 0) * 1000);
      };

      const sharedWorldArrowMoveAllowed = () => true;

      const formatSharedWorldCountdown = (ms = 0) => {
        const total = Math.max(0, Math.ceil(ms / 1000));
        const minutes = Math.floor(total / 60);
        const seconds = total % 60;
        return `${minutes}:${String(seconds).padStart(2, "0")}`;
      };

      const renderSharedWorldKeyboardPass = () => {
        if (!worldKeypassButton) {
          return;
        }
        worldKeypassButton.hidden = true;
        worldKeypassButton.setAttribute("aria-hidden", "true");
        const remaining = sharedWorldKeyboardRemainingMs();
        const active = currentAuthIsAdmin || remaining > 0;
        worldKeypassButton.classList.toggle("is-active", active);
        worldKeypassButton.disabled = sharedWorldKeyboardPassBuying;
        if (worldKeypassTitle) {
          worldKeypassTitle.textContent = currentAuthIsAdmin ? "Admin Arrows" : active ? "Arrow Pass" : "Buy Arrows";
        }
        if (worldKeypassStatus) {
          worldKeypassStatus.textContent = currentAuthIsAdmin
            ? "Unlocked for admin"
            : active
              ? `Active ${formatSharedWorldCountdown(remaining)}`
              : `${sharedWorldKeyboardPass.cost || 10} random crystals / 1 hour`;
        }
      };

      const startSharedWorldKeyboardPassTimer = () => {
        if (sharedWorldKeyboardPassTimer) {
          window.clearInterval(sharedWorldKeyboardPassTimer);
        }
        sharedWorldKeyboardPassTimer = window.setInterval(renderSharedWorldKeyboardPass, 1000);
      };

      const stopSharedWorldKeyboardPassTimer = () => {
        if (sharedWorldKeyboardPassTimer) {
          window.clearInterval(sharedWorldKeyboardPassTimer);
          sharedWorldKeyboardPassTimer = 0;
        }
      };

      const loadSharedWorldKeyboardPass = async () => {
        if (!authToken) {
          return;
        }
        try {
          const response = await fetchAuthJson("/world/keyboard-pass");
          const payload = response && response.payload ? response.payload : response;
          sharedWorldKeyboardPass = normalizeSharedWorldKeyboardPass(payload.keyboard_pass || payload.keyboardPass || {});
          renderSharedWorldKeyboardPass();
        } catch (error) {
          renderSharedWorldKeyboardPass();
        }
      };

      const buySharedWorldKeyboardPass = async () => {
        if (!authToken || currentAuthIsAdmin || sharedWorldKeyboardPassBuying || sharedWorldKeyboardRemainingMs() > 0) {
          renderSharedWorldKeyboardPass();
          return;
        }
        sharedWorldKeyboardPassBuying = true;
        renderSharedWorldKeyboardPass();
        try {
          const response = await fetchAuthJson("/world/keyboard-pass", { method: "POST", body: JSON.stringify({}) });
          const payload = response && response.payload ? response.payload : response;
          sharedWorldKeyboardPass = normalizeSharedWorldKeyboardPass(payload.keyboard_pass || payload.keyboardPass || {});
          if (payload.inventory) {
            sharedWorldInventory = { inventory: payload.inventory };
            renderSharedWorldShop();
            renderSharedWorldInventoryModal();
          } else {
            void loadSharedWorldInventory();
          }
          setSharedWorldStatus("Arrow movement unlocked for 1 hour.", "ok");
        } catch (error) {
          setSharedWorldStatus(error && error.message ? error.message : "Could not buy arrow movement.", "error");
        } finally {
          sharedWorldKeyboardPassBuying = false;
          renderSharedWorldKeyboardPass();
        }
      };

      const sharedWorldFindSkin = (query = "") => {
        const key = sharedWorldNameKey(query);
        if (!key) return null;
        return normalizeSharedWorldSkins(sharedWorldSkinSettings).find((skin) => sharedWorldNameKey(skin.name) === key || sharedWorldNameKey(skin.id) === key)
          || normalizeSharedWorldSkins(sharedWorldSkinSettings).find((skin) => sharedWorldNameKey(skin.name).includes(key) || key.includes(sharedWorldNameKey(skin.name)))
          || null;
      };

      const showSharedWorldWitchBubble = (message = "", durationMs = 5200) => {
        if (!worldWitchBubble) {
          return;
        }
        window.clearTimeout(sharedWorldWitchBubbleTimer);
        worldWitchBubble.textContent = clean(message);
        worldWitchBubble.classList.toggle("is-visible", Boolean(clean(message)));
        if (durationMs > 0) {
          sharedWorldWitchBubbleTimer = window.setTimeout(() => {
            worldWitchBubble.classList.remove("is-visible");
          }, durationMs);
        }
      };

      const renderSharedWorldShop = () => {
        if (!worldSkinList) {
          return;
        }
        const skins = normalizeSharedWorldSkins(sharedWorldSkinSettings);
        worldSkinList.textContent = "";
        skins.forEach((skin) => {
          const card = document.createElement("section");
          card.className = "ft-world-skin-card";
          card.dataset.skinId = skin.id;
          const art = document.createElement("div");
          art.className = `ft-world-skin-art ${sharedWorldSkinArtClass(skin)}`;
          if (skin.image) {
            art.style.backgroundImage = `url("${skin.image.replace(/"/g, "%22")}")`;
            art.style.backgroundSize = "cover";
            art.style.backgroundPosition = "center";
          }
          const name = document.createElement("div");
          name.className = "ft-world-skin-name";
          name.textContent = skin.name;
          const meta = document.createElement("div");
          meta.className = "ft-world-skin-meta";
          meta.textContent = `${skin.price} vocabulary crystals`;
          const desc = document.createElement("div");
          desc.className = "ft-world-skin-desc";
          desc.textContent = skin.description || "Ask the witch for the price and transformation details.";
          card.append(art, name, meta, desc);
          card.addEventListener("click", () => {
            if (worldShopInput) {
              worldShopInput.value = `how much is ${skin.name}`;
              worldShopInput.focus();
            }
          });
          worldSkinList.appendChild(card);
        });
        renderSharedWorldInventoryPanel();
      };

      const openSharedWorldSkinShop = async () => {
        renderSharedWorldShop();
        if (worldSkinShop) {
          worldSkinShop.classList.add("is-open");
          worldSkinShop.setAttribute("aria-hidden", "false");
        }
        void loadSharedWorldInventory();
        if (worldShopInput) {
          window.setTimeout(() => worldShopInput.focus(), 80);
        }
      };

      const closeSharedWorldSkinShop = () => {
        if (worldSkinShop) {
          worldSkinShop.classList.remove("is-open");
          worldSkinShop.setAttribute("aria-hidden", "true");
        }
      };

      const sharedWorldWitchSpeechBody = (text = "") => {
        const raw = clean(text).replace(/^\s*(mystic\s+witch|witch|phu\s+thuy|wizard|mage)\s*[,:\-]\s*/i, "");
        return raw;
      };

      const sharedWorldWitchShapeRequest = (text = "") => {
        const value = sharedWorldNameKey(sharedWorldWitchSpeechBody(text));
        const hasShopVerb = /\b(change|transform|switch|buy|purchase|shop|store|build|make|create|craft|open|need|want|wand|like)\b/.test(value);
        const hasShopObject = /\b(shape|form|skin|appearance|shop|store|buy|purchase|build|make|create|craft|something|thing|transformation)\b/.test(value);
        return hasShopVerb && hasShopObject;
      };

      const sharedWorldWitchPriceRequest = (text = "") => {
        const raw = sharedWorldWitchSpeechBody(text);
        const match = raw.match(/(?:how\s+much\s+(?:is|for)|price\s+of|cost\s+of|how\s+much\s+does)\s+(.+?)(?:\s+cost)?\??$/i);
        return match ? clean(match[1]) : "";
      };

      const primeSharedWorldWitchCommand = () => {
        if (!worldCommandInput) {
          return;
        }
        const current = clean(worldCommandInput.value);
        if (!current || /^move\s+to\b/i.test(current) || /^witch\s*[,:\-]/i.test(current) || /^mystic\s+witch\s*[,:\-]/i.test(current)) {
          worldCommandInput.value = "Mystic Witch, ";
        } else if (!/^(mystic\s+witch|witch)\s*[,:\-]/i.test(current)) {
          worldCommandInput.value = `Mystic Witch, ${current}`;
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const primeSharedWorldPlayerCommand = (target = null) => {
        if (!worldCommandInput || !target) {
          return;
        }
        const label = sharedWorldTargetLabel(target);
        if (!label) {
          return;
        }
        const current = clean(worldCommandInput.value);
        if (!current || /^move\s+to\b/i.test(current) || /^follow\b/i.test(current)) {
          worldCommandInput.value = `move to ${label}`;
        } else {
          worldCommandInput.value = `${current} ${label}`.trim();
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const handleSharedWorldWitchText = (text = "") => {
        const priceTarget = sharedWorldWitchPriceRequest(text);
        if (priceTarget) {
          const skin = sharedWorldFindSkin(priceTarget);
          const reply = skin
            ? `${skin.name} costs ${skin.price} vocabulary crystals.`
            : "I cannot find that form yet. Please choose a skin from the list.";
          showSharedWorldWitchBubble(reply, 6800);
          if (worldShopReply) {
            worldShopReply.textContent = reply;
          }
          return true;
        }
        if (sharedWorldWitchShapeRequest(text)) {
          if (sharedWorldSelectedTargetKey !== "witch" && !(worldSkinShop && worldSkinShop.classList.contains("is-open"))) {
            setSharedWorldStatus("Move to Mystic Witch first, then ask for transformation.", "error");
            showSharedWorldWitchBubble("Come closer first. Use: move to witch", 5200);
            return true;
          }
          showSharedWorldWitchBubble("All right. Which form do you want to transform into?", 5200);
          window.clearTimeout(sharedWorldShopOpenTimer);
          sharedWorldShopOpenTimer = window.setTimeout(() => {
            void openSharedWorldSkinShop();
          }, 2200);
          return true;
        }
        return false;
      };

      const renderSharedWorldSelectedTarget = () => {
        const target = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
        if (!worldTargetChip) {
          return;
        }
        if (!target) {
          worldTargetChip.hidden = true;
          worldTargetChip.textContent = "";
          worldTargetChip.removeAttribute("data-target-key");
          return;
        }
        const label = sharedWorldTargetLabel(target);
        worldTargetChip.hidden = false;
        worldTargetChip.dataset.targetKey = sharedWorldSelectedTargetKey;
        worldTargetChip.textContent = target.isPlaying ? `Playing: ${label}` : `Target: ${label}`;
        worldTargetChip.title = target.isPlaying ? `${label} is already in a battle` : `Insert ${label} into command`;
      };

      const syncSharedWorldNpcRoster = () => {
        if (!worldWitch) {
          return;
        }
        const witch = {
          username: "witch",
          displayName: "Mystic Witch",
          x: 0.74,
          y: 0.34,
          tx: 0.74,
          ty: 0.34,
          npc: "witch",
        };
        sharedWorldRoster.set("witch", witch);
        worldWitch.classList.toggle("is-target-selected", sharedWorldSelectedTargetKey === "witch");
      };

      const selectSharedWorldTarget = (username = "") => {
        const key = clean(username).toLowerCase();
        const me = clean(activeWorldUsername()).toLowerCase();
        if (!key || key === me) {
          setSharedWorldStatus("Select another player before using target commands.", "error");
          return;
        }
        const target = sharedWorldRoster.get(key);
        if (!target) {
          return;
        }
        sharedWorldSelectedTargetKey = key;
        sharedWorldNodes.forEach((node, itemKey) => {
          node.classList.toggle("is-target-selected", itemKey === key);
        });
        if (worldWitch) {
          worldWitch.classList.toggle("is-target-selected", key === "witch");
        }
        renderSharedWorldSelectedTarget();
        if (key === "witch") {
          showSharedWorldWitchBubble("What do you need from me?", 6500);
        }
        setSharedWorldStatus(`${sharedWorldTargetLabel(target)} selected. Use Interact commands such as move to ${sharedWorldTargetLabel(target)}.`, "ok");
        return target;
      };

      const insertSharedWorldTargetIntoCommand = () => {
        const target = sharedWorldSelectedTargetKey ? sharedWorldRoster.get(sharedWorldSelectedTargetKey) : null;
        if (!target || !worldCommandInput) {
          return;
        }
        const label = sharedWorldTargetLabel(target);
        const value = clean(worldCommandInput.value);
        if (!value || /^move\s+to\b/i.test(value)) {
          worldCommandInput.value = `move to ${label}`;
        } else {
          worldCommandInput.value = `${value} ${label}`.trim();
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const renderSharedWorldPositionPoint = () => {
        if (worldPositionChip) {
          if (!sharedWorldSelectedPoint) {
            worldPositionChip.hidden = true;
            worldPositionChip.textContent = "";
          } else {
            const x = Math.round(sharedWorldSelectedPoint.x * 100);
            const y = Math.round(sharedWorldSelectedPoint.y * 100);
            worldPositionChip.hidden = false;
            worldPositionChip.textContent = `Point: ${x}/${y}`;
            worldPositionChip.title = `Insert point ${x} ${y} into command`;
          }
        }
        if (worldPointMarker) {
          if (!sharedWorldSelectedPoint) {
            worldPointMarker.classList.remove("is-visible");
          } else {
            worldPointMarker.style.setProperty("--point-x", `${(sharedWorldSelectedPoint.x * 100).toFixed(2)}%`);
            worldPointMarker.style.setProperty("--point-y", `${(sharedWorldSelectedPoint.y * 100).toFixed(2)}%`);
            worldPointMarker.classList.add("is-visible");
          }
        }
      };

      const showSharedWorldMoveMarker = (point = {}) => {
        if (!worldMoveMarker || !point) {
          return;
        }
        if (sharedWorldMoveMarkerHideTimer) {
          window.clearTimeout(sharedWorldMoveMarkerHideTimer);
          sharedWorldMoveMarkerHideTimer = 0;
        }
        sharedWorldMoveMarkerPoint = {
          x: sharedWorldClamp(point.x),
          y: sharedWorldClamp(point.y),
        };
        worldMoveMarker.style.setProperty("--move-x", `${(sharedWorldMoveMarkerPoint.x * 100).toFixed(2)}%`);
        worldMoveMarker.style.setProperty("--move-y", `${(sharedWorldMoveMarkerPoint.y * 100).toFixed(2)}%`);
        worldMoveMarker.classList.remove("is-visible", "is-arrived");
        void worldMoveMarker.offsetWidth;
        worldMoveMarker.classList.add("is-visible");
      };

      const hideSharedWorldMoveMarker = (arrived = false) => {
        sharedWorldMoveMarkerPoint = null;
        if (!worldMoveMarker) {
          return;
        }
        if (sharedWorldMoveMarkerHideTimer) {
          window.clearTimeout(sharedWorldMoveMarkerHideTimer);
          sharedWorldMoveMarkerHideTimer = 0;
        }
        if (arrived && worldMoveMarker.classList.contains("is-visible")) {
          worldMoveMarker.classList.remove("is-arrived");
          void worldMoveMarker.offsetWidth;
          worldMoveMarker.classList.add("is-arrived");
          sharedWorldMoveMarkerHideTimer = window.setTimeout(() => {
            worldMoveMarker.classList.remove("is-visible", "is-arrived");
            sharedWorldMoveMarkerHideTimer = 0;
          }, 430);
          return;
        }
        worldMoveMarker.classList.remove("is-visible", "is-arrived");
      };

      const updateSharedWorldMoveMarkerArrival = () => {
        if (!sharedWorldMoveMarkerPoint) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        const x = sharedWorldClamp(self.x);
        const y = sharedWorldClamp(self.y);
        const tx = sharedWorldClamp(self.tx, x);
        const ty = sharedWorldClamp(self.ty, y);
        const nearCurrent = Math.hypot(x - sharedWorldMoveMarkerPoint.x, y - sharedWorldMoveMarkerPoint.y) < 0.012;
        const nearTarget = Math.hypot(tx - sharedWorldMoveMarkerPoint.x, ty - sharedWorldMoveMarkerPoint.y) < 0.004;
        const queueActive = sharedWorldHasPath(clean(activeWorldUsername()).toLowerCase());
        if (nearCurrent && nearTarget && !queueActive) {
          hideSharedWorldMoveMarker(true);
        }
      };

      const setSharedWorldPickingPosition = (enabled) => {
        sharedWorldPickingPosition = Boolean(enabled);
        if (worldStage) {
          worldStage.classList.toggle("is-picking-position", sharedWorldPickingPosition);
        }
        if (worldPointButton) {
          worldPointButton.classList.toggle("is-active", sharedWorldPickingPosition);
          worldPointButton.textContent = sharedWorldPickingPosition ? "Pick..." : "Point";
        }
        if (sharedWorldPickingPosition) {
          setSharedWorldStatus("Click a position inside QM-City, then use the Point block with move to.", "ok");
        }
      };

      const sharedWorldPointFromArenaEvent = (event) => {
        if (!worldArena) {
          return null;
        }
        const rect = worldArena.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          return null;
        }
        return {
          x: sharedWorldClamp((event.clientX - rect.left) / rect.width),
          y: sharedWorldClamp((event.clientY - rect.top) / rect.height),
        };
      };

      const selectSharedWorldPositionPoint = (point) => {
        if (!point) {
          return;
        }
        sharedWorldSelectedPoint = {
          x: sharedWorldClamp(point.x),
          y: sharedWorldClamp(point.y),
        };
        renderSharedWorldPositionPoint();
        setSharedWorldPickingPosition(false);
        setSharedWorldStatus(`Point selected: ${Math.round(sharedWorldSelectedPoint.x * 100)} / ${Math.round(sharedWorldSelectedPoint.y * 100)}.`, "ok");
      };

      const sharedWorldMapPointerBlocked = (target) => Boolean(
        target
        && target.closest
        && target.closest([
          "button",
          "input",
          "textarea",
          "select",
          "[contenteditable='true']",
          ".ft-world-player",
          ".ft-world-npc",
          ".ft-world-witch",
          "[data-slime-id]",
          "#ft-world-training-modal",
          "#ft-world-training-exit-gate",
          "#ft-world-command-lane",
          ".ft-world-command-lane",
          ".ft-world-dock",
          ".ft-world-close-menu",
          ".ft-world-status",
          ".ft-world-skin-shop",
          ".ft-world-inventory-modal",
        ].join(","))
      );

      const moveSharedWorldToMapPoint = (point = {}) => {
        if (!point) {
          return;
        }
        clearSharedWorldFollowTarget();
        showSharedWorldMoveMarker(point);
        void moveSharedWorldPlayer({
          x: sharedWorldClamp(point.x),
          y: sharedWorldClamp(point.y),
        });
      };

      const beginSharedWorldStagePan = (event) => {
        if (!worldStage || !worldModal || !worldModal.classList.contains("is-open") || sharedWorldPickingPosition) {
          return;
        }
        if (event.button != null && event.button !== 0) {
          return;
        }
        if (sharedWorldMapPointerBlocked(event.target)) {
          return;
        }
        sharedWorldStageDrag = {
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          scrollLeft: worldStage.scrollLeft,
          scrollTop: worldStage.scrollTop,
          moved: false,
        };
        try {
          if (typeof worldStage.setPointerCapture === "function" && event.pointerId != null) {
            worldStage.setPointerCapture(event.pointerId);
          }
        } catch (error) {}
      };

      const updateSharedWorldStagePan = (event) => {
        if (!worldStage || !sharedWorldStageDrag || (event.pointerId != null && sharedWorldStageDrag.pointerId !== event.pointerId)) {
          return;
        }
        const dx = event.clientX - sharedWorldStageDrag.startX;
        const dy = event.clientY - sharedWorldStageDrag.startY;
        if (!sharedWorldStageDrag.moved && Math.hypot(dx, dy) < 5) {
          return;
        }
        sharedWorldStageDrag.moved = true;
        worldStage.scrollLeft = sharedWorldStageDrag.scrollLeft - dx;
        worldStage.scrollTop = sharedWorldStageDrag.scrollTop - dy;
        event.preventDefault();
      };

      const endSharedWorldStagePan = (event) => {
        if (!worldStage || !sharedWorldStageDrag || (event.pointerId != null && sharedWorldStageDrag.pointerId !== event.pointerId)) {
          return;
        }
        const didMove = Boolean(sharedWorldStageDrag.moved);
        try {
          if (typeof worldStage.releasePointerCapture === "function" && event.pointerId != null) {
            worldStage.releasePointerCapture(event.pointerId);
          }
        } catch (error) {}
        sharedWorldStageDrag = null;
        if (didMove) {
          sharedWorldSuppressNextMapClick = true;
          window.setTimeout(() => {
            sharedWorldSuppressNextMapClick = false;
          }, 120);
        }
      };

      const handleSharedWorldStageClick = (event) => {
        if (!worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        if (sharedWorldSuppressNextMapClick) {
          event.preventDefault();
          event.stopPropagation();
          sharedWorldSuppressNextMapClick = false;
          return;
        }
        if (sharedWorldMapPointerBlocked(event.target)) {
          return;
        }
        const point = sharedWorldPointFromArenaEvent(event);
        if (!point) {
          return;
        }
        event.preventDefault();
        event.stopPropagation();
        if (sharedWorldPickingPosition) {
          selectSharedWorldPositionPoint(point);
          return;
        }
        if (sharedWorldMapMode === "training") {
          setSharedWorldTrainingQuestionOpen(false);
        }
        moveSharedWorldToMapPoint(point);
      };

      const insertSharedWorldPositionIntoCommand = () => {
        if (!sharedWorldSelectedPoint || !worldCommandInput) {
          return;
        }
        const x = Math.round(sharedWorldSelectedPoint.x * 100);
        const y = Math.round(sharedWorldSelectedPoint.y * 100);
        const value = clean(worldCommandInput.value);
        if (!value || /^move\s+to\b/i.test(value)) {
          worldCommandInput.value = `move to ${x} ${y}`;
        } else {
          worldCommandInput.value = `${value} ${x} ${y}`.trim();
        }
        worldCommandInput.focus();
        worldCommandInput.setSelectionRange(worldCommandInput.value.length, worldCommandInput.value.length);
      };

      const resolveSharedWorldTarget = (name = "") => {
        const query = sharedWorldNameKey(name);
        if (!query) {
          return null;
        }
        const rows = Array.from(sharedWorldRoster.values());
        return rows.find((item) => sharedWorldNameKey(item.username) === query || sharedWorldNameKey(sharedWorldTargetLabel(item)) === query)
          || rows.find((item) => sharedWorldNameKey(sharedWorldTargetLabel(item)).includes(query) || sharedWorldNameKey(item.username).includes(query))
          || null;
      };

      const sharedWorldNearTargetPoint = (target) => {
        if (!target) {
          return null;
        }
        const targetX = sharedWorldClamp(target.tx != null ? target.tx : target.x);
        const targetY = sharedWorldClamp(target.ty != null ? target.ty : target.y);
        const self = getSharedWorldSelfPosition();
        let dx = sharedWorldClamp(self.x) - targetX;
        let dy = sharedWorldClamp(self.y) - targetY;
        let distance = Math.hypot(dx, dy);
        if (distance < 0.02) {
          let seed = 0;
          clean(target.username || target.displayName || "").split("").forEach((char) => {
            seed += char.charCodeAt(0);
          });
          const angle = ((seed % 360) / 180) * Math.PI;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          distance = 1;
        }
        const gap = 0.18;
        return {
          x: sharedWorldClamp(targetX + (dx / distance) * gap),
          y: sharedWorldClamp(targetY + (dy / distance) * gap),
        };
      };

      const clearSharedWorldFollowTarget = () => {
        sharedWorldFollowTargetKey = "";
        sharedWorldFollowMoveAt = 0;
      };

      const updateSharedWorldFollowTarget = () => {
        if (!sharedWorldFollowTargetKey || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        const target = sharedWorldRoster.get(sharedWorldFollowTargetKey);
        const me = clean(activeWorldUsername()).toLowerCase();
        if (!target || clean(target.username).toLowerCase() === me) {
          clearSharedWorldFollowTarget();
          return;
        }
        const now = Date.now();
        if (now - sharedWorldFollowMoveAt < 900) {
          return;
        }
        const point = sharedWorldNearTargetPoint(target);
        if (!point) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        if (Math.hypot(sharedWorldClamp(self.tx, self.x) - point.x, sharedWorldClamp(self.ty, self.y) - point.y) < 0.018) {
          return;
        }
        sharedWorldFollowMoveAt = now;
        void moveSharedWorldPlayer(point);
      };

      const createSharedWorldNode = (username = "") => {
        const node = document.createElement("div");
        node.className = "ft-world-player";
        node.dataset.username = username;
        node.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const target = selectSharedWorldTarget(node.dataset.username || "");
          if (target) {
            primeSharedWorldPlayerCommand(target);
          }
        });
        node.innerHTML = `
          <span class="ft-world-target-arrow" aria-hidden="true"></span>
          <div class="ft-world-rank-badge" hidden></div>
          <div class="ft-world-playing-badge" aria-hidden="true">Playing</div>
          <div class="ft-world-top-tooltip" hidden></div>
          <div class="ft-world-bubble"></div>
          <div class="ft-world-level" aria-hidden="true">
            <span class="ft-world-level-badge">Lv 1</span>
            <span class="ft-world-exp-bar"><span></span></span>
            <span class="ft-world-exp-text">0/25</span>
          </div>
          <div class="ft-world-fireball" aria-hidden="true">
            <span class="ft-world-eye is-left"></span>
            <span class="ft-world-eye is-right"></span>
            <span class="ft-world-cheek is-left"></span>
            <span class="ft-world-cheek is-right"></span>
            <span class="ft-world-smile"></span>
          </div>
          <div class="ft-world-name-row">
            <div class="ft-world-name"></div>
            <span class="ft-world-gender" title="other">◇</span>
          </div>
        `;
        return node;
      };

      const renderSharedWorldName = (node, displayName = "", gender = "") => {
        const nameNode = node && node.querySelector ? node.querySelector(".ft-world-name") : null;
        if (!nameNode) {
          return;
        }
        nameNode.innerHTML = "";
        const label = document.createElement("span");
        label.className = "ft-world-name-label";
        label.textContent = clean(displayName) || "Learner";
        nameNode.append(label);
        const genderNode = node.querySelector(".ft-world-gender");
        if (!genderNode) {
          return;
        }
        const genderKey = clean(gender).toLowerCase();
        genderNode.className = `ft-world-gender ${genderKey === "female" ? "is-female" : genderKey === "other" ? "is-other" : ""}`;
        genderNode.textContent = sharedWorldGenderSymbol(genderKey);
        genderNode.title = genderKey || "other";
      };

      const renderSharedWorldLevel = (node, level = {}) => {
        if (!node || !node.querySelector) {
          return;
        }
        const data = level && typeof level === "object" ? level : {};
        const badge = node.querySelector(".ft-world-level-badge");
        const bar = node.querySelector(".ft-world-exp-bar");
        const text = node.querySelector(".ft-world-exp-text");
        const currentLevel = Math.max(1, Math.floor(Number(data.level || 1) || 1));
        const exp = Math.max(0, Math.floor(Number(data.exp || 0) || 0));
        const currentExp = Math.max(0, Math.floor(Number(data.current_exp || data.currentExp || 0) || 0));
        const nextExp = Math.max(currentExp, Math.floor(Number(data.next_exp || data.nextExp || currentExp) || currentExp));
        const maxLevel = Boolean(data.max_level || data.maxLevel);
        let progress = Number(data.progress);
        if (!Number.isFinite(progress)) {
          progress = maxLevel ? 1 : ((nextExp > currentExp) ? (exp - currentExp) / (nextExp - currentExp) : 0);
        }
        progress = Math.max(0, Math.min(1, progress));
        if (badge) {
          badge.textContent = `Lv ${currentLevel}`;
        }
        if (bar) {
          bar.style.setProperty("--level-progress", `${(progress * 100).toFixed(1)}%`);
        }
        if (text) {
          text.textContent = maxLevel ? `${exp} MAX` : `${exp}/${nextExp}`;
        }
      };

      const renderSharedWorldTopMeta = (node, player = {}) => {
        if (!node || !node.querySelector) {
          return;
        }
        const badge = node.querySelector(".ft-world-rank-badge");
        const tooltip = node.querySelector(".ft-world-top-tooltip");
        const monthlyBadge = player && typeof player.monthly_badge === "object" ? player.monthly_badge : {};
        const titleRows = Array.isArray(player.top_titles) ? player.top_titles : [];
        if (badge) {
          const scopeRank = { month: 3, week: 2, day: 1 };
          const champions = titleRows
            .filter((item) => item && Math.floor(Number(item.rank || 0) || 0) === 1 && scopeRank[clean(item.scope).toLowerCase()])
            .sort((x, y) => (scopeRank[clean(y.scope).toLowerCase()] || 0) - (scopeRank[clean(x.scope).toLowerCase()] || 0));
          let best = champions[0] || null;
          let scope = best ? clean(best.scope).toLowerCase() : "";
          let label = best ? clean(best.label || best.title || "") : "";
          let period = "";
          if (!best) {
            label = clean(monthlyBadge.label || monthlyBadge.title || "");
            scope = label ? clean(monthlyBadge.scope || "month").toLowerCase() : "";
            period = clean(monthlyBadge.period_key || "");
          }
          badge.classList.remove("is-day", "is-week", "is-month");
          if (label) {
            if (scope === "day" || scope === "week" || scope === "month") {
              badge.classList.add(`is-${scope}`);
            }
            badge.hidden = false;
            badge.title = best ? `${label} - ${Math.max(0, Math.floor(Number(best.score || 0) || 0))} words` : period;
            badge.innerHTML = `
              <span class="ft-world-rank-crown" aria-hidden="true">
                <svg viewBox="0 0 24 20" focusable="false">
                  <path fill="currentColor" d="M2.6 6.2 6 11 12 3.2 18 11l3.4-4.8c.7-1 2.2-.4 2 .8l-1.7 9.3c-.1.7-.7 1.2-1.4 1.2H4.7c-.7 0-1.3-.5-1.4-1.2L1.6 7c-.2-1.2 1.3-1.8 2-.8Z"/>
                  <circle cx="2.7" cy="5" r="1.5" fill="currentColor"/>
                  <circle cx="12" cy="2.4" r="1.7" fill="currentColor"/>
                  <circle cx="21.3" cy="5" r="1.5" fill="currentColor"/>
                </svg>
              </span>
              <span class="ft-world-rank-label"></span>
            `;
            const labelNode = badge.querySelector(".ft-world-rank-label");
            if (labelNode) {
              labelNode.textContent = label;
            }
          } else {
            badge.hidden = true;
            badge.title = "";
            badge.innerHTML = "";
          }
        }
        if (!tooltip) {
          return;
        }
        const rows = Array.isArray(player.top_titles) ? player.top_titles : [];
        tooltip.innerHTML = "";
        if (!rows.length) {
          tooltip.hidden = true;
          return;
        }
        tooltip.hidden = false;
        rows.slice(0, 3).forEach((item) => {
          const line = document.createElement("div");
          line.className = "ft-world-top-line";
          const title = document.createElement("span");
          title.textContent = clean(item.label || item.title || item.scope || "Top");
          const score = document.createElement("b");
          score.textContent = `${Math.max(0, Math.floor(Number(item.score || 0) || 0))}`;
          line.append(title, score);
          tooltip.appendChild(line);
        });
      };

      const applySharedWorldNodePosition = (node, x, y) => {
        if (!node) {
          return;
        }
        node.style.setProperty("--world-x", `${(sharedWorldClamp(x) * 100).toFixed(2)}%`);
        node.style.setProperty("--world-y", `${(sharedWorldClamp(y) * 100).toFixed(2)}%`);
      };

      const sharedWorldHasPath = (key = "") => {
        const safeKey = clean(key).toLowerCase();
        const queue = sharedWorldPathQueues.get(safeKey);
        return Array.isArray(queue) && queue.length > 0;
      };

      const clearSharedWorldPath = (key = "") => {
        const safeKey = clean(key).toLowerCase();
        if (!safeKey) {
          return;
        }
        sharedWorldPathQueues.delete(safeKey);
        const pos = sharedWorldPositions.get(safeKey);
        if (pos && Array.isArray(pos.path)) {
          pos.path = [];
        }
      };

      const sharedWorldMakeOrthogonalPath = (start = {}, target = {}) => {
        const startX = sharedWorldClamp(start.x);
        const startY = sharedWorldClamp(start.y);
        const targetX = sharedWorldClamp(target.x);
        const targetY = sharedWorldClamp(target.y);
        const dx = targetX - startX;
        const dy = targetY - startY;
        const points = [];
        const pushPoint = (x, y) => {
          const point = { x: sharedWorldClamp(x), y: sharedWorldClamp(y) };
          const last = points[points.length - 1];
          if (!last || Math.hypot(last.x - point.x, last.y - point.y) > 0.002) {
            points.push(point);
          }
        };
        if (Math.abs(dx) < 0.002 || Math.abs(dy) < 0.002) {
          pushPoint(targetX, targetY);
        } else if (Math.abs(dx) >= Math.abs(dy)) {
          pushPoint(targetX, startY);
          pushPoint(targetX, targetY);
        } else {
          pushPoint(startX, targetY);
          pushPoint(targetX, targetY);
        }
        return points;
      };

      const setSharedWorldOrthogonalPath = (key = "", target = {}) => {
        const safeKey = clean(key).toLowerCase();
        if (!safeKey || !target) {
          return null;
        }
        let pos = sharedWorldPositions.get(safeKey);
        if (!pos) {
          pos = { x: target.x, y: target.y, tx: target.x, ty: target.y };
          sharedWorldPositions.set(safeKey, pos);
        }
        const destination = {
          x: sharedWorldClamp(target.x),
          y: sharedWorldClamp(target.y),
        };
        const path = sharedWorldMakeOrthogonalPath({ x: pos.x, y: pos.y }, destination);
        pos.tx = destination.x;
        pos.ty = destination.y;
        pos.path = path.slice();
        if (path.length) {
          sharedWorldPathQueues.set(safeKey, path);
        } else {
          sharedWorldPathQueues.delete(safeKey);
        }
        return pos;
      };

      const sharedWorldMotionTargetFor = (key = "", pos = {}) => {
        const safeKey = clean(key).toLowerCase();
        const queue = Array.isArray(pos.path) && pos.path.length
          ? pos.path
          : sharedWorldPathQueues.get(safeKey);
        if (Array.isArray(queue) && queue.length) {
          return queue[0];
        }
        return {
          x: sharedWorldClamp(pos.tx, pos.x),
          y: sharedWorldClamp(pos.ty, pos.y),
        };
      };

      const advanceSharedWorldPathIfReached = (key = "", pos = {}) => {
        const safeKey = clean(key).toLowerCase();
        const queue = Array.isArray(pos.path) && pos.path.length
          ? pos.path
          : sharedWorldPathQueues.get(safeKey);
        if (!Array.isArray(queue) || !queue.length) {
          return false;
        }
        queue.shift();
        if (queue.length) {
          pos.path = queue;
          sharedWorldPathQueues.set(safeKey, queue);
          return true;
        }
        pos.path = [];
        sharedWorldPathQueues.delete(safeKey);
        pos.x = sharedWorldClamp(pos.tx, pos.x);
        pos.y = sharedWorldClamp(pos.ty, pos.y);
        return false;
      };

      const syncSharedWorldBattleLinks = () => {
        if (!worldBattleLinks || !worldArena) {
          return;
        }
        const pairs = Array.isArray(sharedWorldActiveBattlePairs) ? sharedWorldActiveBattlePairs : [];
        const activeKeys = new Set();
        pairs.forEach((pair) => {
          const row = pair && typeof pair === "object" ? pair : {};
          const players = Array.isArray(row.players)
            ? row.players.map((item) => clean(item).toLowerCase()).filter(Boolean)
            : [];
          if (players.length < 2) {
            return;
          }
          const first = players[0];
          const second = players[1];
          const posA = sharedWorldPositions.get(first);
          const posB = sharedWorldPositions.get(second);
          if (!posA || !posB) {
            return;
          }
          const key = clean(row.id) || players.slice(0, 2).sort().join(":");
          activeKeys.add(key);
          let link = sharedWorldBattleLinkNodes.get(key);
          if (!link) {
            link = document.createElement("div");
            link.className = "ft-world-battle-link";
            const label = document.createElement("b");
            label.textContent = "Playing";
            link.appendChild(label);
            sharedWorldBattleLinkNodes.set(key, link);
            worldBattleLinks.appendChild(link);
          }
          const x1 = sharedWorldClamp(posA.x) * worldArena.scrollWidth;
          const y1 = sharedWorldClamp(posA.y) * worldArena.scrollHeight;
          const x2 = sharedWorldClamp(posB.x) * worldArena.scrollWidth;
          const y2 = sharedWorldClamp(posB.y) * worldArena.scrollHeight;
          const dx = x2 - x1;
          const dy = y2 - y1;
          const length = Math.max(18, Math.hypot(dx, dy));
          const angle = Math.atan2(dy, dx) * 180 / Math.PI;
          link.style.left = `${x1}px`;
          link.style.top = `${y1}px`;
          link.style.width = `${length}px`;
          link.style.transform = `translateY(-50%) rotate(${angle}deg)`;
        });
        Array.from(sharedWorldBattleLinkNodes.entries()).forEach(([key, node]) => {
          if (!activeKeys.has(key)) {
            node.remove();
            sharedWorldBattleLinkNodes.delete(key);
          }
        });
      };

      const setSharedWorldFacing = (node, dx = 0) => {
        if (!node || Math.abs(dx) < 0.006) {
          return;
        }
        const nextFacing = dx < 0 ? "left" : "right";
        const now = Date.now();
        if (node.dataset.facing === nextFacing) {
          return;
        }
        if (Number(node.dataset.facingAt || 0) && now - Number(node.dataset.facingAt || 0) < 320) {
          return;
        }
        node.dataset.facing = nextFacing;
        node.dataset.facingAt = String(now);
        node.classList.toggle("is-facing-left", nextFacing === "left");
      };

      const sharedWorldUseLocalSelfMotion = (key = "") => {
        const me = clean(activeWorldUsername()).toLowerCase();
        if (!me || clean(key).toLowerCase() !== me) {
          return false;
        }
        return sharedWorldHeldArrows.size > 0
          || sharedWorldKeyboardSyncing
          || Boolean(sharedWorldKeyboardQueuedPoint)
          || sharedWorldHasPath(me)
          || (Date.now() - sharedWorldLocalMoveAt < 1800);
      };

      const centerSharedWorldViewportOn = (x = 0.5, y = 0.5, smooth = false) => {
        if (!worldStage || !worldArena) {
          return;
        }
        const left = sharedWorldClamp(x) * worldArena.scrollWidth - worldStage.clientWidth / 2;
        const top = sharedWorldClamp(y) * worldArena.scrollHeight - worldStage.clientHeight / 2;
        worldStage.scrollTo({
          left: Math.max(0, Math.min(worldArena.scrollWidth - worldStage.clientWidth, left)),
          top: Math.max(0, Math.min(worldArena.scrollHeight - worldStage.clientHeight, top)),
          behavior: smooth ? "smooth" : "auto",
        });
      };

      const ensureSharedWorldSelfVisible = (smooth = true) => {
        if (!worldStage || !worldArena || sharedWorldFollowSelf || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        const self = getSharedWorldSelfPosition();
        const x = sharedWorldClamp(self.x) * worldArena.scrollWidth;
        const y = sharedWorldClamp(self.y) * worldArena.scrollHeight;
        const margin = Math.max(92, Math.min(worldStage.clientWidth, worldStage.clientHeight) * 0.16);
        const left = worldStage.scrollLeft;
        const top = worldStage.scrollTop;
        const right = left + worldStage.clientWidth;
        const bottom = top + worldStage.clientHeight;
        const outside = x < left + margin || x > right - margin || y < top + margin || y > bottom - margin;
        if (!outside) {
          return;
        }
        const now = Date.now();
        if (now - sharedWorldAutoLocateAt < 900) {
          return;
        }
        sharedWorldAutoLocateAt = now;
        centerSharedWorldViewportOn(self.x, self.y, smooth);
      };

      const scheduleSharedWorldMotion = () => {
        if (sharedWorldMotionFrame || !worldModal || !worldModal.classList.contains("is-open")) {
          return;
        }
        sharedWorldMotionLastAt = performance.now();
        sharedWorldMotionFrame = window.requestAnimationFrame(stepSharedWorldMotion);
      };

      const stepSharedWorldMotion = (now) => {
        sharedWorldMotionFrame = 0;
        const dt = Math.min(40, Math.max(8, now - (sharedWorldMotionLastAt || now)));
        sharedWorldMotionLastAt = now;
        const rows = Array.from(sharedWorldPositions.entries());
        let moving = false;
        let selfMoving = false;
        const meKey = clean(activeWorldUsername()).toLowerCase();
        rows.forEach(([key, pos]) => {
          const motionTarget = sharedWorldMotionTargetFor(key, pos);
          let dx = sharedWorldClamp(motionTarget.x, pos.x) - sharedWorldClamp(pos.x);
          let dy = sharedWorldClamp(motionTarget.y, pos.y) - sharedWorldClamp(pos.y);
          const targetDx = dx;
          const dist = Math.hypot(dx, dy);
          if (dist > 0.0014) {
            const speed = 0.00018 + Math.min(0.00008, dist * 0.00085);
            const step = Math.min(dist, dt * speed);
            pos.x = sharedWorldClamp(pos.x + (dx / dist) * step);
            pos.y = sharedWorldClamp(pos.y + (dy / dist) * step);
            moving = true;
            if (key === meKey) {
              selfMoving = true;
              sharedWorldLocalMoveAt = Date.now();
            }
          } else {
            pos.x = sharedWorldClamp(motionTarget.x, pos.x);
            pos.y = sharedWorldClamp(motionTarget.y, pos.y);
            if (advanceSharedWorldPathIfReached(key, pos)) {
              moving = true;
              if (key === meKey) {
                selfMoving = true;
                sharedWorldLocalMoveAt = Date.now();
              }
            } else {
              pos.x = sharedWorldClamp(pos.tx, pos.x);
              pos.y = sharedWorldClamp(pos.ty, pos.y);
            }
          }
          const node = sharedWorldNodes.get(key);
          setSharedWorldFacing(node, targetDx);
          applySharedWorldNodePosition(node, pos.x, pos.y);
        });
        if (sharedWorldFollowSelf) {
          scheduleSharedWorldFollowCenter();
        } else if (selfMoving) {
          ensureSharedWorldSelfVisible(true);
        }
        if (selfMoving && sharedWorldMapMode === "training") {
          maybeExitSharedWorldTrainingByGate();
        }
        updateSharedWorldMoveMarkerArrival();
        syncSharedWorldBattleLinks();
        if (moving && worldModal && worldModal.classList.contains("is-open")) {
          sharedWorldMotionFrame = window.requestAnimationFrame(stepSharedWorldMotion);
        }
      };
