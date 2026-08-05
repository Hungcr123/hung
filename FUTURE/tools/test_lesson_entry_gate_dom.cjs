"use strict";

const assert = require("assert");
const { chromium } = require("playwright");

const base = process.env.FUTURE_GATE_DOM_BASE || "http://127.0.0.1:8877";
const browserPath = process.env.FUTURE_BROWSER_EXE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const runViewport = async (browser, viewport) => {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  try {
    await page.goto(`${base}/login?ft_gate_probe=1`, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(() => Boolean(window.__ftLessonEntryGateProbe), null, { timeout: 30000 });
    const paragraphContracts = await page.evaluate(async () => ({
      preload: await window.__ftLessonEntryGateProbe.paragraphPreloadSpaces(),
      childResume: window.__ftLessonEntryGateProbe.paragraphChildResume(),
      snapshot: window.__ftLessonEntryGateProbe.snapshotCheckpointContract(),
      spaceQResume: window.__ftLessonEntryGateProbe.spaceQResumeContract(),
      spaceQProgressPaths: window.__ftLessonEntryGateProbe.spaceQProgressPathsContract(),
    }));
    assert.deepStrictEqual(paragraphContracts.preload, [true, true, true], "P/L/S preload family was rejected");
    assert.deepStrictEqual(paragraphContracts.childResume, [true, true, true], "P/L/S child checkpoint was not resumable");
    assert.deepStrictEqual(paragraphContracts.snapshot, { compact: false, full: true }, "compact Vault progress was treated as a full checkpoint");
    assert.deepStrictEqual(paragraphContracts.spaceQResume, {
      activeRun: true,
      resumeAvailable: true,
      currentIndex: 2,
      questionIndex: 1,
      runId: "space-q-probe-run",
    }, "Space_Q active checkpoint did not survive normalization/navigation");
    assert(paragraphContracts.spaceQProgressPaths.includes("space:space_q:id:ftg-lesson-probe"), "Space_Q DOM patch omitted the canonical lesson ID");
    assert(paragraphContracts.spaceQProgressPaths.includes("common/probe.Space_Q"), "Space_Q DOM patch omitted the visible Lesson Vault path");
    assert(paragraphContracts.spaceQProgressPaths.includes("common/effective-probe.Space_Q"), "Space_Q DOM patch omitted the effective Space Task path");
    const spaceQTaskProgress = await page.evaluate(() => window.__ftLessonEntryGateProbe.spaceQTaskProgressContract());
    assert(spaceQTaskProgress.available, "Space_Q Space Task DOM probe was unavailable");
    assert.strictEqual(spaceQTaskProgress.progressText, "2/48", "Space Task dataset kept stale Space_Q progress after the direct Exit patch");
    assert.strictEqual(spaceQTaskProgress.progressPercent, "4", "Space Task percent did not follow the direct Space_Q Exit patch");
    assert(spaceQTaskProgress.visibleText.includes("2/48"), `Space Task ring did not render 2/48: ${spaceQTaskProgress.visibleText}`);
    const pdfCacheTimeout = await page.evaluate(() => window.__ftLessonEntryGateProbe.pdfCacheTimeout());
    assert.strictEqual(pdfCacheTimeout.result, "timeout", "stalled Cache API operation did not release the PDF loader");
    assert(pdfCacheTimeout.elapsedMs >= 900 && pdfCacheTimeout.elapsedMs < 1800, `PDF cache timeout was not bounded: ${pdfCacheTimeout.elapsedMs}ms`);
    const token = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Space_Q DOM gate"));
    assert(token > 0, "gate probe did not start");
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-moving"), null, { timeout: 3000 });
    const closingCircuitAnimation = await page.evaluate(() => getComputedStyle(document.querySelector(".ft-entry-door-circuit-traces path")).animationName);
    assert.strictEqual(closingCircuitAnimation, "none", "Gate 1 circuit animation kept running while the primary doors closed");
    const vaultCloseDeferred = await page.evaluate(() => window.__ftLessonEntryGateProbe.deferVaultClose());
    assert(vaultCloseDeferred, "Lesson Vault closed before primary gate finished sealing");
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    await page.waitForFunction(() => !document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-moving"), null, { timeout: 3000 });
    await page.waitForFunction(() => document.querySelector("#ft-server-browser")?.hidden === true, null, { timeout: 5000 });
    const sealed = await page.evaluate(() => {
      const gate = document.querySelector("#ft-lesson-entry-gate");
      const frame = document.querySelector("#ft-entry-gate-frame");
      const rect = gate.getBoundingClientRect();
      const style = getComputedStyle(gate);
      const frameStyle = getComputedStyle(frame);
      const secondaryStyle = getComputedStyle(document.querySelector(".ft-entry-gate2-panel"));
      const atomicLogos = Array.from(document.querySelectorAll(".ft-entry-door-atomic-logo"));
      const radiationIcon = document.querySelector(".ft-entry-radiation-icon");
      const radiationHost = document.querySelector(".ft-entry-door-atomic-logo.is-radiation");
      const techGrid = document.querySelector(".ft-entry-tech-grid");
      const circuitTrace = document.querySelector(".ft-entry-door-circuit-traces path");
      const alertPanel = document.querySelector(".ft-entry-alert-panel");
      const rightDoor = document.querySelector(".ft-entry-primary-door.is-right")?.getBoundingClientRect();
      const centerConsole = document.querySelector(".ft-entry-center-console")?.getBoundingClientRect();
      const chipCenter = (node) => {
        if (!node) return null;
        const nodeRect = node.getBoundingClientRect();
        return { x: nodeRect.left + (nodeRect.width / 2), y: nodeRect.top + (nodeRect.height / 2) };
      };
      return {
        hidden: gate.hidden,
        width: rect.width,
        height: rect.height,
        fixed: style.position === "fixed",
        zIndex: Number(style.zIndex || 0),
        transparent: style.backgroundColor === "rgba(0, 0, 0, 0)" && frameStyle.backgroundColor === "rgba(0, 0, 0, 0)",
        motionFrozen: document.documentElement.classList.contains("ft-lesson-entry-motion-freeze"),
        primarySealed: frame.classList.contains("is-primary-sealed"),
        secondaryHidden: secondaryStyle.visibility === "hidden",
        vaultReleasedAfterSeal: document.querySelector("#ft-server-browser")?.hidden === true,
        atomicLogoCount: atomicLogos.length,
        atomicLogoWidths: atomicLogos.map((node) => Math.round(node.getBoundingClientRect().width)),
        radiationIconCount: document.querySelectorAll(".ft-entry-radiation-icon").length,
        radiationAnimationName: radiationIcon ? getComputedStyle(radiationIcon).animationName : "",
        radiationScanAnimationName: radiationHost ? getComputedStyle(radiationHost, "::after").animationName : "",
        alertPanelCount: document.querySelectorAll(".ft-entry-alert-panel").length,
        alertTriangleCount: document.querySelectorAll(".ft-entry-alert-triangle").length,
        warningMarkCount: document.querySelectorAll(".ft-entry-alert-tri-inner > strong").length,
        techGridCount: document.querySelectorAll(".ft-entry-tech-grid").length,
        techGridBackground: techGrid ? getComputedStyle(techGrid).backgroundImage : "",
        circuitBoardCount: document.querySelectorAll(".ft-entry-door-circuit-board").length,
        circuitTraceCount: document.querySelectorAll(".ft-entry-door-circuit-traces path").length,
        circuitTraceAnimationName: circuitTrace ? getComputedStyle(circuitTrace).animationName : "",
        chipCenters: [chipCenter(radiationHost), chipCenter(alertPanel)],
        consoleAttachedToRightDoor: Boolean(rightDoor && centerConsole && centerConsole.left >= rightDoor.left && centerConsole.right <= rightDoor.right),
      };
    });
    assert(!sealed.hidden && sealed.fixed && sealed.primarySealed, "primary gate did not seal full-screen");
    assert(Math.abs(sealed.width - viewport.width) <= 1, `gate width ${sealed.width} != ${viewport.width}`);
    assert(Math.abs(sealed.height - viewport.height) <= 1, `gate height ${sealed.height} != ${viewport.height}`);
    assert(sealed.zIndex >= 2147483000, `gate z-index is too low: ${sealed.zIndex}`);
    assert(sealed.transparent && sealed.secondaryHidden && sealed.vaultReleasedAfterSeal, "Lesson Vault must hand off only after gate 1 seals");
    assert.strictEqual(sealed.atomicLogoCount, 1, "Gate 1 must retain the left radiation logo wrapper");
    assert.strictEqual(sealed.radiationIconCount, 1, "Left Gate 1 must use the source radiation icon");
    assert.strictEqual(sealed.radiationAnimationName, "ftEntryRadiationPulse", "Source radiation glow pulse is not running");
    assert.strictEqual(sealed.radiationScanAnimationName, "ftEntryRadiationScan", "Source radiation scan is not running");
    assert.strictEqual(sealed.alertPanelCount, 1, "Right Gate 1 must import the complete alert panel");
    assert.strictEqual(sealed.alertTriangleCount, 1, "Right Gate 1 alert panel must retain its warning triangle");
    assert.strictEqual(sealed.warningMarkCount, 1, "Right Gate 1 alert panel must have one exclamation mark");
    assert.strictEqual(sealed.techGridCount, 2, "Both Gate 1 doors must retain their technical background layer");
    assert(sealed.techGridBackground.includes("repeating-linear-gradient"), "Gate 1 background did not switch to diagonal stripes");
    assert.strictEqual(sealed.circuitBoardCount, 2, "Both Gate 1 chips must have a circuit board layer");
    assert.strictEqual(sealed.circuitTraceCount, 16, "Gate 1 circuit routes are incomplete");
    assert.strictEqual(sealed.circuitTraceAnimationName, "ftEntryCircuitData", "Gate 1 circuit data flow is not running");
    assert(sealed.consoleAttachedToRightDoor, "Gate 1 console is not fully mounted inside the right door");
    assert(sealed.chipCenters.every((point) => point && Math.abs(point.y - (viewport.height / 2)) <= viewport.height * 0.08), `Gate 1 chips are not vertically centered: ${JSON.stringify(sealed.chipCenters)}`);
    assert(Math.abs(sealed.chipCenters[0].x - (viewport.width * 0.25)) <= viewport.width * 0.08, `Left Gate 1 chip is off-center: ${JSON.stringify(sealed.chipCenters[0])}`);
    assert(Math.abs(sealed.chipCenters[1].x - (viewport.width * 0.75)) <= viewport.width * 0.08, `Right Gate 1 chip is off-center: ${JSON.stringify(sealed.chipCenters[1])}`);
    assert(sealed.atomicLogoWidths.every((width) => width >= (viewport.width <= 600 ? 112 : 128)), `Gate 1 radiation logo is not doubled: ${sealed.atomicLogoWidths}`);
    assert(sealed.motionFrozen, "Lesson Vault motion was not frozen during gate transition");
    await page.evaluate((value) => {
      window.__ftLessonEntryGateDecisionPromise = window.__ftLessonEntryGateProbe.armDecisionDelayedContinue(value);
    }, token);
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-open")?.hidden === false || document.querySelector("#ft-entry-gate-continue")?.hidden === false, null, { timeout: 10000 });
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-continue")?.hidden === false, null, { timeout: 5000 });
    const decision = await page.evaluate(() => ({
      primarySealed: document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"),
      secondaryHidden: getComputedStyle(document.querySelector(".ft-entry-gate2-panel")).visibility === "hidden",
      openVisible: document.querySelector("#ft-entry-gate-open")?.hidden === false,
      continueVisible: document.querySelector("#ft-entry-gate-continue")?.hidden === false,
      exitVisible: document.querySelector("#ft-entry-gate-exit")?.hidden === false,
      pdfStreamHidden: document.querySelector("#ft-entry-pdf-stream")?.hidden === true,
    }));
    assert(decision.primarySealed && decision.secondaryHidden && decision.openVisible && decision.continueVisible && decision.exitVisible, "manual Space choice was not held on sealed gate 1");
    assert(decision.pdfStreamHidden, "ordinary Space showed the PDF stream monitor");
    await page.click("#ft-entry-gate-open");
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-moving"), null, { timeout: 10000 });
    const openingCircuitAnimation = await page.evaluate(() => getComputedStyle(document.querySelector(".ft-entry-door-circuit-traces path")).animationName);
    assert.strictEqual(openingCircuitAnimation, "none", "Gate 1 circuit animation kept running while the primary doors opened");
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-secondary-open"), null, { timeout: 10000 });
    const active = await page.evaluate(() => ({
      status: document.querySelector("#ft-entry-gate2-status")?.textContent || "",
      primaryOpen: document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-open"),
      secondaryReady: document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-secondary-ready"),
      secondaryOpen: document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-secondary-open"),
      motionFrozen: document.documentElement.classList.contains("ft-lesson-entry-motion-freeze"),
    }));
    assert.strictEqual(active.status, "ACTIVE");
    assert(active.primaryOpen && active.secondaryReady && active.secondaryOpen, "two-stage gate did not open in order");
    assert(active.motionFrozen, "Lesson Vault motion resumed before gate finished opening");
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 5000 });
    const motionFreezeCleared = await page.evaluate(() => !document.documentElement.classList.contains("ft-lesson-entry-motion-freeze"));
    assert(motionFreezeCleared, "Lesson Vault motion freeze was not released after gate");
    const mediaToken = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Space_PDF media choice"));
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    await page.evaluate((value) => window.__ftLessonEntryGateProbe.armMediaDecision(value, 7), mediaToken);
    await page.waitForFunction(() => (
      document.querySelector("#ft-entry-gate-open")?.hidden === false &&
      document.querySelector("#ft-entry-gate-continue")?.hidden === true
    ), null, { timeout: 5000 });
    const mediaMode = "continue";
    await page.click("#ft-entry-gate-open");
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 10000 });
    const mediaChoice = await page.evaluate(() => window.__ftLessonEntryMediaProbe);
    assert.deepStrictEqual(mediaChoice, {
      choice: mediaMode,
      page: mediaMode === "continue" ? 7 : 1,
      activated: true,
    }, "PDF/Picture New/Continue or post-gate activation barrier failed");
    const autoToken = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Space_PDF auto Continue"));
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    await page.evaluate((value) => window.__ftLessonEntryGateProbe.armMediaDecision(value, 7), autoToken);
    await page.waitForFunction(() => window.__ftLessonEntryMediaProbe?.choice === "continue", null, { timeout: 5000 });
    const autoMediaChoice = await page.evaluate(() => window.__ftLessonEntryMediaProbe);
    assert.strictEqual(autoMediaChoice.choice, "continue", "PDF gate did not auto-select Continue after one second without input");
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 10000 });
    const pdfProgress = await page.evaluate(() => window.__ftLessonEntryPdfProgressProbe);
    assert.deepStrictEqual(pdfProgress, [
      { percent: "37%", chunk: "CHUNK 2/6 · 37%", graphProgress: "37%", ringOffset: "435.425", hidden: false, withinViewport: true },
      { percent: "82%", chunk: "CHUNK 5/6 · 82%", graphProgress: "82%", ringOffset: "124.407", hidden: false, withinViewport: true },
      { percent: "100%", chunk: "CHUNK 6/6 · 100%", graphProgress: "100%", ringOffset: "0", hidden: false, withinViewport: true },
    ], "gate 1 PDF stream monitor did not render real byte/chunk progress");
    const pdfProgressRoute = await page.evaluate(() => window.__ftPdfProgressRoute);
    assert.strictEqual(pdfProgressRoute, "gate", "gated PDF progress leaked back to the legacy PDF loader");
    const pdfOverallProgress = await page.evaluate(() => window.__ftLessonEntryPdfOverallProbe);
    assert.deepStrictEqual(pdfOverallProgress, [37, 82, 100, 0, 100], "PDF network progress did not complete before the separate local graph reset");
    const pdfHub = await page.evaluate(() => ({
      rings: document.querySelectorAll("#ft-entry-pdf-stream-graph circle").length,
      centered: (() => {
        const graph = document.querySelector("#ft-entry-pdf-stream-graph")?.getBoundingClientRect();
        const panel = document.querySelector("#ft-entry-pdf-stream")?.getBoundingClientRect();
        return Boolean(graph && panel && Math.abs((graph.left + graph.width / 2) - (panel.left + panel.width / 2)) <= 1);
      })(),
    }));
    assert.deepStrictEqual(pdfHub, { rings: 5, centered: true }, "PDF HUD graph was not restored and centered");
    const cancelToken = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Gate 1 exit choice"));
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    await page.evaluate((value) => window.__ftLessonEntryGateProbe.armDecision(value), cancelToken);
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-exit")?.hidden === false, null, { timeout: 5000 });
    await page.click("#ft-entry-gate-exit");
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 5000 });
    const gateExitChoice = await page.evaluate(() => ({
      ...window.__ftLessonEntryGateExitChoiceResult,
      vaultVisible: document.querySelector("#ft-server-browser")?.hidden === false,
    }));
    assert.deepStrictEqual(gateExitChoice, { primaryOpened: true, secondaryOpened: false, vaultVisible: true }, "gate 1 Exit did not return directly to Lesson Vault");
    const vocabToken = await page.evaluate(() => window.__ftLessonEntryGateProbe.begin("Space_W vocabulary alert"));
    await page.waitForFunction(() => document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-primary-sealed"), null, { timeout: 5000 });
    const vocabAlertStarted = await page.evaluate((value) => window.__ftLessonEntryGateProbe.vocabAlert(value), vocabToken);
    assert(vocabAlertStarted, "gate 2 vocabulary alert did not start");
    await page.waitForFunction(() => document.querySelector("#ft-entry-vocab-alert")?.hidden === false, null, { timeout: 5000 });
    const vocabAlert = await page.evaluate(() => ({
      count: document.querySelector("#ft-entry-vocab-alert-count")?.textContent || "",
      packs: document.querySelector("#ft-entry-vocab-alert-packs")?.textContent || "",
      secondaryOpen: document.querySelector("#ft-entry-gate-frame")?.classList.contains("is-secondary-open"),
    }));
    assert.strictEqual(vocabAlert.count, "48 NEW WORDS");
    assert.strictEqual(vocabAlert.packs, "2 PACKS");
    assert(!vocabAlert.secondaryOpen, "gate 2 opened before the vocabulary route was selected");
    await page.evaluate((value) => window.__ftLessonEntryGateProbe.cancel(value, "Vocabulary alert probe complete"), vocabToken);
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 5000 });
    const exitStarted = await page.evaluate(() => window.__ftLessonEntryGateProbe.exit("Space_Q exit gate"));
    assert(exitStarted, "exit gate probe did not start");
    await page.waitForFunction(() => Boolean(window.__ftLessonExitGateProbeResult), null, { timeout: 5000 });
    const exit = await page.evaluate(() => window.__ftLessonExitGateProbeResult);
    assert(exit.primarySealed && exit.secondaryClosed, "exit did not close gate 2 before sealing gate 1");
    await page.waitForFunction(() => document.querySelector("#ft-lesson-entry-gate")?.hidden === true, null, { timeout: 5000 });
    assert.deepStrictEqual(errors, [], `frontend errors: ${errors.join(" | ")}`);
    return { viewport, paragraphContracts, spaceQTaskProgress, pdfCacheTimeout, sealed, decision, active, mediaChoice, pdfProgress, pdfProgressRoute, pdfOverallProgress, pdfHub, gateExitChoice, vocabAlert, exit, motionFreezeCleared };
  } finally {
    await context.close();
  }
};

(async () => {
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  try {
    const desktop = await runViewport(browser, { width: 1440, height: 900 });
    const mobile = await runViewport(browser, { width: 390, height: 844 });
    console.log(JSON.stringify({ ok: true, desktop, mobile }));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
