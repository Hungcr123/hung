

      const ensurePdfModeStyle = () => {
        if (document.getElementById("ft-pdf-space-style")) {
          return;
        }
        const style = document.createElement("style");
        style.id = "ft-pdf-space-style";
        style.textContent = `
          .ft-pdf-space {
            position: fixed;
            inset: 0;
            z-index: 145;
            display: grid;
            place-items: stretch;
            padding: clamp(70px, 8vh, 92px) clamp(14px, 3vw, 32px) clamp(18px, 3vh, 32px);
            background:
              radial-gradient(circle at 18% 8%, rgba(255, 176, 77, 0.16), transparent 32%),
              radial-gradient(circle at 88% 24%, rgba(78, 245, 218, 0.15), transparent 30%),
              linear-gradient(135deg, rgba(4, 7, 16, 0.96), rgba(8, 14, 28, 0.94));
            color: #efffff;
          }
          .ft-pdf-space.is-hidden { display: none; }
          .ft-pdf-shell {
            min-height: 0;
            display: grid;
            grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.55fr);
            gap: clamp(14px, 2vw, 24px);
          }
          .ft-pdf-space.is-ghost-console-hidden .ft-pdf-shell {
            grid-template-columns: minmax(0, 1fr);
          }
          .ft-pdf-space.is-ghost-console-floating .ft-pdf-shell {
            grid-template-columns: minmax(0, 1fr);
          }
          .ft-pdf-space.is-ghost-console-hidden .ft-pdf-ocr-card {
            display: none;
          }
          .ft-pdf-card,
          .ft-pdf-ocr-card {
            position: relative;
            min-height: 0;
            overflow: hidden;
            border: 1px solid rgba(126, 255, 232, 0.28);
            border-radius: 18px;
            background:
              linear-gradient(135deg, rgba(10, 19, 34, 0.92), rgba(12, 24, 42, 0.78)),
              repeating-linear-gradient(90deg, rgba(255,255,255,0.035) 0 1px, transparent 1px 17px);
            box-shadow: 0 28px 80px rgba(0, 0, 0, 0.46), inset 0 0 38px rgba(64, 255, 225, 0.08);
            backdrop-filter: blur(16px);
          }
          .ft-pdf-card::before,
          .ft-pdf-ocr-card::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            border-radius: inherit;
            background:
              linear-gradient(90deg, rgba(255, 177, 81, 0.7), transparent 24%, transparent 76%, rgba(77, 255, 225, 0.62)) top / 100% 1px no-repeat,
              linear-gradient(180deg, rgba(77, 255, 225, 0.42), transparent 42%, rgba(255, 177, 81, 0.38)) right / 1px 100% no-repeat;
          }
          .ft-pdf-card {
            display: grid;
            grid-template-rows: auto auto minmax(0, 1fr);
          }
          .ft-pdf-ocr-card.is-floating {
            position: fixed;
            z-index: 2190;
            left: max(12px, 2vw);
            top: clamp(92px, 12vh, 132px);
            width: min(420px, calc(100vw - 24px));
            max-width: calc(100vw - 24px);
            max-height: calc(100vh - 24px);
          }
          .ft-pdf-ocr-card.is-dragging,
          .ft-pdf-translation-card.is-dragging {
            box-shadow: 0 30px 90px rgba(0, 0, 0, 0.58), 0 0 34px rgba(255, 198, 83, 0.2), inset 0 0 26px rgba(70, 255, 226, 0.08);
          }
          .ft-pdf-topline,
          .ft-pdf-toolbar,
          .ft-pdf-ocr-head,
          .ft-pdf-ocr-actions,
          .ft-pdf-agent-row {
            position: relative;
            z-index: 1;
          }
          .ft-pdf-topline {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr) auto;
            align-items: center;
            gap: 12px;
            padding: 18px 20px 10px;
          }
          .ft-pdf-kicker,
          .ft-pdf-page-meta,
          .ft-pdf-status,
          .ft-pdf-vocab-stats {
            font-size: 11px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: rgba(168, 255, 241, 0.82);
          }
          .ft-pdf-title {
            margin: 0;
            min-width: 0;
            color: #ffffff;
            font-size: clamp(18px, 1.7vw, 28px);
            line-height: 1.12;
            overflow-wrap: anywhere;
            text-shadow: 0 0 20px rgba(106, 255, 230, 0.22);
          }
          .ft-pdf-toolbar {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            padding: 8px 20px 14px;
          }
          .ft-pdf-page-controls {
            display: inline-flex;
            align-items: center;
            gap: 8px;
          }
          .ft-pdf-button,
          .ft-pdf-goto-input,
          .ft-pdf-agent-input {
            border: 1px solid rgba(126, 255, 232, 0.34);
            background: linear-gradient(135deg, rgba(9, 20, 36, 0.92), rgba(16, 31, 50, 0.72));
            color: #ecfffd;
            box-shadow: inset 0 0 16px rgba(82, 255, 228, 0.08), 0 10px 26px rgba(0, 0, 0, 0.25);
          }
          .ft-pdf-button {
            position: relative;
            min-height: 38px;
            padding: 0 14px;
            border-radius: 12px;
            cursor: pointer;
            letter-spacing: 0.04em;
            isolation: isolate;
          }
          .ft-pdf-button:hover,
          .ft-pdf-button.is-active {
            border-color: rgba(255, 187, 90, 0.76);
            box-shadow: 0 0 28px rgba(255, 178, 72, 0.22), inset 0 0 20px rgba(255, 178, 72, 0.12);
          }
          .ft-pdf-quality-toggle {
            min-width: 46px;
            padding: 0 12px;
            font-weight: 950;
            color: #fff5d8;
            border-color: rgba(255, 209, 118, 0.58);
            background:
              radial-gradient(circle at 50% 34%, rgba(255, 220, 136, 0.18), transparent 58%),
              linear-gradient(135deg, rgba(255, 181, 68, 0.18), rgba(70, 240, 215, 0.09)),
              rgba(8, 18, 32, 0.88);
          }
          .ft-pdf-quality-toggle.is-active {
            color: #ffffff;
            border-color: rgba(70, 255, 230, 0.74);
            box-shadow:
              0 0 28px rgba(70, 240, 215, 0.2),
              inset 0 0 20px rgba(255, 208, 118, 0.13);
          }
          .ft-pdf-button[data-pdf-tool-kind],
          .ft-pdf-compact-action[data-pdf-tool-kind] {
            --pdf-tool-pulse: #ffd166;
            --pdf-tool-pulse-2: #46f0d7;
            --pdf-tool-pulse-glow: rgba(255, 209, 102, 0.34);
            --pdf-tool-active-bg: rgba(255, 209, 102, 0.22);
            overflow: hidden;
            transition: border-color 160ms ease, background 160ms ease, color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
          }
          .ft-pdf-button[data-pdf-tool-kind="eraser"],
          .ft-pdf-compact-action[data-pdf-tool-kind="eraser"] {
            --pdf-tool-pulse: #ff84a2;
            --pdf-tool-pulse-2: #46f0d7;
            --pdf-tool-pulse-glow: rgba(255, 132, 162, 0.36);
            --pdf-tool-active-bg: rgba(255, 132, 162, 0.24);
          }
          .ft-pdf-button[data-pdf-tool-kind="text"],
          .ft-pdf-compact-action[data-pdf-tool-kind="text"] {
            --pdf-tool-pulse: #bf5af2;
            --pdf-tool-pulse-2: #ffd166;
            --pdf-tool-pulse-glow: rgba(191, 90, 242, 0.38);
            --pdf-tool-active-bg: rgba(191, 90, 242, 0.24);
          }
          .ft-pdf-button[data-pdf-tool-kind="audio"],
          .ft-pdf-compact-action[data-pdf-tool-kind="audio"] {
            --pdf-tool-pulse: #5ee7ff;
            --pdf-tool-pulse-2: #ffd166;
            --pdf-tool-pulse-glow: rgba(94, 231, 255, 0.38);
            --pdf-tool-active-bg: rgba(94, 231, 255, 0.24);
          }
          .ft-pdf-button[data-pdf-tool-kind].is-active,
          .ft-pdf-compact-action[data-pdf-tool-kind].is-active {
            border-color: color-mix(in srgb, var(--pdf-tool-pulse), #ffffff 18%);
            color: #ffffff;
            background:
              radial-gradient(circle at 24% 24%, color-mix(in srgb, var(--pdf-tool-pulse), transparent 42%), transparent 42%),
              linear-gradient(135deg, var(--pdf-tool-active-bg), color-mix(in srgb, var(--pdf-tool-pulse-2), transparent 88%)),
              rgba(7, 18, 30, 0.96);
            box-shadow:
              0 0 0 1px color-mix(in srgb, var(--pdf-tool-pulse), transparent 44%),
              0 0 24px var(--pdf-tool-pulse-glow),
              inset 0 0 24px color-mix(in srgb, var(--pdf-tool-pulse), transparent 78%);
          }
          .ft-pdf-button[data-pdf-tool-kind].is-active::before,
          .ft-pdf-compact-action[data-pdf-tool-kind].is-active::before {
            content: "";
            position: absolute;
            inset: 3px;
            z-index: -1;
            border-radius: inherit;
            border: 1px solid color-mix(in srgb, var(--pdf-tool-pulse), transparent 22%);
            background:
              linear-gradient(120deg, transparent 0 18%, color-mix(in srgb, var(--pdf-tool-pulse), transparent 28%) 34%, transparent 52%),
              radial-gradient(circle at 50% 105%, color-mix(in srgb, var(--pdf-tool-pulse), transparent 24%), transparent 46%);
            opacity: 0.92;
            transform: none;
            animation: ftPdfToolActiveSheen 1.65s ease-in-out infinite;
          }
          .ft-pdf-button.is-tool-pulse,
          .ft-pdf-compact-action.is-tool-pulse {
            animation: ftPdfToolButtonPulse 620ms cubic-bezier(0.16, 0.9, 0.2, 1);
          }
          .ft-pdf-button.is-tool-off-pulse,
          .ft-pdf-compact-action.is-tool-off-pulse {
            animation-name: ftPdfToolButtonRelease;
          }
          .ft-pdf-button.is-tool-pulse::after,
          .ft-pdf-compact-action.is-tool-pulse::after {
            content: "";
            position: absolute;
            inset: -18%;
            z-index: 0;
            border-radius: inherit;
            background:
              conic-gradient(from 0deg, transparent 0 14%, color-mix(in srgb, var(--pdf-tool-pulse), transparent 18%) 18% 28%, transparent 34% 58%, color-mix(in srgb, var(--pdf-tool-pulse-2), transparent 28%) 64% 74%, transparent 82%),
              radial-gradient(circle at 50% 50%, color-mix(in srgb, var(--pdf-tool-pulse), transparent 48%), transparent 42%);
            opacity: 0;
            pointer-events: auto;
            mix-blend-mode: screen;
            animation: ftPdfToolButtonAura 620ms ease-out;
          }
          .ft-pdf-button.is-tool-pulse[data-pdf-tool-kind="pen"]::after,
          .ft-pdf-compact-action.is-tool-pulse[data-pdf-tool-kind="pen"]::after {
            background:
              radial-gradient(circle at 12% 72%, rgba(255, 209, 102, 0.96) 0 4px, transparent 5px),
              linear-gradient(112deg, transparent 0 16%, rgba(255, 209, 102, 0.9) 21% 28%, rgba(70, 240, 215, 0.62) 30% 34%, transparent 39% 100%),
              conic-gradient(from 80deg, transparent, rgba(255, 209, 102, 0.28), transparent 52%);
            animation-name: ftPdfToolInkCharge;
          }
          .ft-pdf-button.is-tool-pulse[data-pdf-tool-kind="eraser"]::after,
          .ft-pdf-compact-action.is-tool-pulse[data-pdf-tool-kind="eraser"]::after {
            background:
              repeating-linear-gradient(105deg, transparent 0 9px, rgba(255, 132, 162, 0.54) 10px 13px, rgba(70, 240, 215, 0.34) 14px 17px),
              radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.24), transparent 44%);
            animation-name: ftPdfToolEraserSweep;
          }
          .ft-pdf-button.is-tool-pulse[data-pdf-tool-kind="text"]::after,
          .ft-pdf-compact-action.is-tool-pulse[data-pdf-tool-kind="text"]::after {
            background:
              linear-gradient(90deg, transparent 0 46%, rgba(255, 255, 255, 0.98) 48% 52%, transparent 54%),
              radial-gradient(circle at 52% 50%, rgba(191, 90, 242, 0.62), transparent 42%),
              linear-gradient(180deg, rgba(255, 209, 102, 0.26), transparent);
            animation-name: ftPdfToolTextFlash;
          }
          .ft-pdf-compact-action.is-tool-pulse svg {
            position: relative;
            z-index: 1;
            transform-origin: center;
          }
          .ft-pdf-button.is-tool-pulse {
            color: #ffffff;
          }
          .ft-pdf-compact-action.is-tool-pulse[data-pdf-tool-kind="pen"] svg {
            animation: ftPdfToolPenNib 560ms ease-out;
          }
          .ft-pdf-compact-action.is-tool-pulse[data-pdf-tool-kind="eraser"] svg {
            animation: ftPdfToolEraserRub 560ms ease-in-out;
          }
          .ft-pdf-compact-action.is-tool-pulse[data-pdf-tool-kind="text"] svg {
            animation: ftPdfToolTextCaret 560ms ease-out;
          }
          .ft-pdf-button.is-tool-pulse[data-pdf-tool-kind="pen"] {
            animation-name: ftPdfToolPenButton;
          }
          .ft-pdf-button.is-tool-pulse[data-pdf-tool-kind="eraser"] {
            animation-name: ftPdfToolEraserButton;
          }
          .ft-pdf-button.is-tool-pulse[data-pdf-tool-kind="text"] {
            animation-name: ftPdfToolTextButton;
          }
          .ft-pdf-button.is-browser-ocr,
          .ft-pdf-compact-action.is-browser-ocr {
            border-color: rgba(80, 205, 255, 0.82);
            background:
              radial-gradient(circle at 50% 22%, rgba(80, 205, 255, 0.28), transparent 48%),
              linear-gradient(135deg, rgba(11, 32, 55, 0.94), rgba(10, 18, 35, 0.84));
            box-shadow: 0 0 22px rgba(80, 205, 255, 0.24), inset 0 0 18px rgba(80, 205, 255, 0.12);
          }
          .ft-pdf-button.is-cache-ocr,
          .ft-pdf-compact-action.is-cache-ocr {
            border-color: rgba(92, 255, 172, 0.82);
            background:
              radial-gradient(circle at 50% 22%, rgba(92, 255, 172, 0.26), transparent 48%),
              linear-gradient(135deg, rgba(8, 48, 37, 0.95), rgba(10, 24, 31, 0.84));
            box-shadow: 0 0 22px rgba(34, 197, 94, 0.22), inset 0 0 18px rgba(92, 255, 172, 0.11);
          }
          .ft-pdf-ocr-engine-popover {
            position: fixed;
            z-index: 230;
            display: grid;
            gap: 6px;
            min-width: 178px;
            padding: 8px;
            border: 1px solid rgba(126, 255, 232, 0.42);
            border-radius: 12px;
            background:
              linear-gradient(135deg, rgba(8, 18, 34, 0.98), rgba(12, 28, 48, 0.96));
            box-shadow: 0 20px 58px rgba(0, 0, 0, 0.42), inset 0 0 26px rgba(80, 205, 255, 0.08);
            color: #ecfffd;
          }
          .ft-pdf-ocr-engine-popover.is-hidden {
            display: none;
          }
          .ft-pdf-ocr-engine-title {
            padding: 4px 6px 6px;
            color: rgba(168, 255, 241, 0.76);
            font-size: 10px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
          }
          .ft-pdf-ocr-engine-option {
            display: grid;
            grid-template-columns: 20px minmax(0, 1fr);
            align-items: center;
            gap: 7px;
            width: 100%;
            min-height: 34px;
            border: 1px solid rgba(126, 255, 232, 0.18);
            border-radius: 9px;
            background: rgba(255, 255, 255, 0.045);
            color: inherit;
            cursor: pointer;
            text-align: left;
          }
          .ft-pdf-ocr-engine-option:hover,
          .ft-pdf-ocr-engine-option.is-active {
            border-color: rgba(255, 187, 90, 0.78);
            background: rgba(255, 187, 90, 0.14);
          }
          .ft-pdf-ocr-engine-check {
            text-align: center;
            color: #ffd166;
            font-size: 13px;
          }
          .ft-pdf-ocr-engine-label {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 12px;
            letter-spacing: 0.04em;
          }
          @keyframes ftPdfToolButtonPulse {
            0% { transform: translateY(0) scale(1); filter: brightness(1); }
            42% { transform: translateY(-1px) scale(1.045); filter: brightness(1.24) saturate(1.28); }
            100% { transform: translateY(0) scale(1); filter: brightness(1); }
          }
          @keyframes ftPdfToolButtonRelease {
            0% { transform: scale(1.035); filter: brightness(1.16); }
            100% { transform: scale(1); filter: brightness(1); }
          }
          @keyframes ftPdfToolPenButton {
            0% { transform: translate(-1px, 1px) rotate(-0.4deg) scale(1); }
            44% { transform: translate(1px, -1px) rotate(0.7deg) scale(1.045); }
            100% { transform: translate(0, 0) rotate(0deg) scale(1); }
          }
          @keyframes ftPdfToolEraserButton {
            0%, 100% { transform: translateX(0) scale(1); }
            22% { transform: translateX(-2px) rotate(-0.8deg) scale(1.025); }
            52% { transform: translateX(2px) rotate(0.8deg) scale(1.045); }
            76% { transform: translateX(-1px) rotate(-0.35deg) scale(1.018); }
          }
          @keyframes ftPdfToolTextButton {
            0% { transform: scaleX(0.98) scaleY(1); }
            38% { transform: scaleX(1.03) scaleY(1.055); }
            100% { transform: scaleX(1) scaleY(1); }
          }
          @keyframes ftPdfToolActiveSheen {
            0%, 100% { opacity: 0.72; filter: brightness(1); }
            50% { opacity: 1; filter: brightness(1.18); }
          }
          @keyframes ftPdfToolButtonAura {
            0% { opacity: 0; transform: rotate(-18deg) scale(0.62); }
            35% { opacity: 0.92; transform: rotate(80deg) scale(1); }
            100% { opacity: 0; transform: rotate(190deg) scale(1.16); }
          }
          @keyframes ftPdfToolInkCharge {
            0% { opacity: 0; transform: translateX(-48%) scale(0.72); }
            38% { opacity: 0.94; }
            100% { opacity: 0; transform: translateX(42%) scale(1.08); }
          }
          @keyframes ftPdfToolEraserSweep {
            0% { opacity: 0; transform: translateX(-44%) skewX(-12deg); }
            34% { opacity: 0.92; }
            100% { opacity: 0; transform: translateX(44%) skewX(-12deg); }
          }
          @keyframes ftPdfToolTextFlash {
            0% { opacity: 0; transform: scaleY(0.52); }
            32% { opacity: 0.95; transform: scaleY(1.08); }
            100% { opacity: 0; transform: scaleY(1.18); }
          }
          @keyframes ftPdfToolPenNib {
            0% { transform: translate(-1px, 1px) rotate(-5deg); }
            46% { transform: translate(1px, -1px) rotate(6deg); }
            100% { transform: translate(0, 0) rotate(0deg); }
          }
          @keyframes ftPdfToolEraserRub {
            0%, 100% { transform: translateX(0) rotate(0deg); }
            25% { transform: translateX(-2px) rotate(-4deg); }
            58% { transform: translateX(2px) rotate(4deg); }
          }
          @keyframes ftPdfToolTextCaret {
            0% { transform: scaleY(0.86); filter: brightness(1); }
            38% { transform: scaleY(1.12); filter: brightness(1.28); }
            100% { transform: scaleY(1); filter: brightness(1); }
          }
          .ft-pdf-button.is-console-toggle {
            border-color: rgba(70, 240, 215, 0.42);
            color: #dffdf8;
            background:
              linear-gradient(135deg, rgba(70, 240, 215, 0.12), rgba(255, 178, 72, 0.08)),
              rgba(9, 20, 36, 0.84);
          }
          .ft-pdf-button.is-console-toggle.is-active {
            border-color: rgba(255, 190, 91, 0.78);
            color: #fff2c9;
          }
          .ft-pdf-button.ft-pdf-ai-assist-toggle {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            min-width: 0;
            padding: 0 10px 0 8px;
            border-color: rgba(255, 211, 126, 0.34);
            color: rgba(255, 241, 202, 0.9);
            letter-spacing: 0;
            background:
              radial-gradient(circle at 24% 24%, rgba(255, 211, 126, 0.18), transparent 36%),
              linear-gradient(135deg, rgba(255, 211, 126, 0.1), rgba(70, 240, 215, 0.07)),
              rgba(8, 18, 30, 0.8);
            overflow: hidden;
          }
          .ft-pdf-button.ft-pdf-ai-assist-toggle.is-active {
            border-color: rgba(70, 240, 215, 0.58);
            color: #f7fffb;
            background:
              radial-gradient(circle at 22% 18%, rgba(255, 255, 255, 0.52), transparent 23%),
              linear-gradient(135deg, rgba(255, 211, 111, 0.34), rgba(70, 240, 215, 0.24)),
              rgba(7, 26, 34, 0.94);
            box-shadow:
              0 0 0 1px rgba(70, 240, 215, 0.2),
              0 0 22px rgba(70, 240, 215, 0.24),
              inset 0 0 18px rgba(255, 211, 111, 0.12);
          }
          .ft-pdf-ai-assist-icon {
            position: relative;
            display: inline-grid;
            place-items: center;
            width: 26px;
            height: 26px;
            flex: 0 0 auto;
            border-radius: 50%;
            background:
              radial-gradient(circle at 50% 50%, rgba(70, 240, 215, 0.22), transparent 62%),
              rgba(4, 12, 20, 0.56);
            box-shadow: inset 0 0 12px rgba(70, 240, 215, 0.12);
          }
          .ft-pdf-ai-assist-icon svg {
            width: 20px;
            height: 20px;
            display: block;
          }
          .ft-pdf-ai-assist-icon::after {
            content: "";
            position: absolute;
            right: 1px;
            bottom: 2px;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: rgba(255, 118, 118, 0.86);
            box-shadow: 0 0 10px rgba(255, 118, 118, 0.46);
          }
          .ft-pdf-ai-assist-toggle.is-active .ft-pdf-ai-assist-icon::after {
            background: #72ffbe;
            box-shadow: 0 0 12px rgba(114, 255, 190, 0.64);
            animation: ftPdfAiAssistPulse 1.35s ease-in-out infinite;
          }
          .ft-pdf-ai-assist-copy {
            font-size: 12px;
            font-weight: 950;
            white-space: nowrap;
          }
          .ft-pdf-ai-assist-count {
            min-width: 30px;
            padding: 3px 6px;
            border-radius: 999px;
            color: #07131d;
            background: rgba(255, 231, 138, 0.9);
            font-size: 11px;
            font-weight: 950;
            line-height: 1;
          }
          .ft-pdf-ai-assist-toggle:not(.is-active) .ft-pdf-ai-assist-count {
            color: rgba(238, 255, 252, 0.72);
            background: rgba(126, 255, 232, 0.12);
          }
          @keyframes ftPdfAiAssistPulse {
            0%, 100% { transform: scale(1); filter: brightness(1); }
            50% { transform: scale(1.22); filter: brightness(1.2); }
          }
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle *,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle::before,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle::after,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-icon::before,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-icon::after,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-notice-toggle,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-notice-toggle *,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-notice-toggle::before,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-notice-toggle::after,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle *,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle::before,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle::after,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-icon::before,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-icon::after,
          html.ft-pdf-static-motion .ft-pdf-ai-notice-toggle,
          html.ft-pdf-static-motion .ft-pdf-ai-notice-toggle *,
          html.ft-pdf-static-motion .ft-pdf-ai-notice-toggle::before,
          html.ft-pdf-static-motion .ft-pdf-ai-notice-toggle::after {
            animation: none !important;
            transition: none !important;
            filter: none !important;
            will-change: auto !important;
          }
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-active .ft-pdf-ai-assist-icon::after,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-icon::after,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-active .ft-pdf-ai-assist-icon::after,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-icon::after {
            width: 7px !important;
            height: 7px !important;
            transform: none !important;
            opacity: 1 !important;
          }
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-active,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-tool-pulse,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-tool-on-pulse,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-tool-off-pulse,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-active,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-tool-pulse,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-tool-on-pulse,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-tool-off-pulse {
            animation: none !important;
            transition: none !important;
            transform: none !important;
            filter: none !important;
            box-shadow: inset 0 0 10px rgba(70, 240, 215, 0.08) !important;
            background: rgba(8, 18, 30, 0.86) !important;
          }
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-active,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-active {
            border-color: rgba(70, 240, 215, 0.58) !important;
            color: #f7fffb !important;
          }
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-tool-pulse::after,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-tool-on-pulse::after,
          html.ft-lesson-vault-motion-off .ft-pdf-ai-assist-toggle.is-tool-off-pulse::after,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-tool-pulse::after,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-tool-on-pulse::after,
          html.ft-pdf-static-motion .ft-pdf-ai-assist-toggle.is-tool-off-pulse::after {
            content: none !important;
            display: none !important;
            animation: none !important;
            transition: none !important;
            box-shadow: none !important;
          }
          #ft-pdf-pin-page-toggle.is-active,
          #ft-pdf-compact-pin-page.is-active,
          #ft-pdf-pin-image-toggle.is-active,
          #ft-pdf-compact-pin-image.is-active,
          #ft-pdf-local-image-toggle.is-active,
          #ft-pdf-compact-local-image.is-active {
            border-color: rgba(70, 240, 215, 0.86);
            color: #eafffb;
            background:
              radial-gradient(circle at 24% 22%, rgba(70, 240, 215, 0.26), transparent 42%),
              linear-gradient(135deg, rgba(70, 240, 215, 0.18), rgba(255, 209, 102, 0.14)),
              rgba(8, 20, 32, 0.96);
            box-shadow:
              0 0 0 1px rgba(70, 240, 215, 0.28),
              0 0 24px rgba(70, 240, 215, 0.24),
              inset 0 0 22px rgba(255, 209, 102, 0.1);
          }
          #ft-pdf-pin-page-toggle.is-current-page,
          #ft-pdf-compact-pin-page.is-current-page {
            border-color: rgba(255, 209, 102, 0.92);
            color: #fff4d0;
            box-shadow:
              0 0 0 1px rgba(255, 209, 102, 0.34),
              0 0 28px rgba(255, 209, 102, 0.28),
              inset 0 0 22px rgba(70, 240, 215, 0.1);
          }
          .ft-pdf-button.is-speak-training-hint {
            border-color: rgba(255, 211, 112, 0.92);
            color: #fff4c7;
            background:
              linear-gradient(135deg, rgba(255, 179, 63, 0.2), rgba(66, 255, 226, 0.12)),
              linear-gradient(180deg, rgba(255,255,255,0.08), transparent);
            box-shadow:
              0 0 30px rgba(255, 178, 65, 0.26),
              0 0 54px rgba(74, 255, 226, 0.12),
              inset 0 0 24px rgba(255, 213, 113, 0.14);
            animation: ftPdfSpeakTrainingNudge 1.05s ease-in-out infinite;
          }
          .ft-pdf-button.is-speak-training-hint::before {
            content: "";
            position: absolute;
            inset: -8px;
            z-index: -1;
            border-radius: 16px;
            border: 1px solid rgba(255, 211, 112, 0.42);
            background:
              radial-gradient(circle at 20% 30%, rgba(255, 214, 116, 0.34), transparent 22%),
              radial-gradient(circle at 80% 70%, rgba(77, 255, 230, 0.24), transparent 26%);
            opacity: 0.78;
            animation: ftPdfSpeakTrainingAura 1.05s ease-in-out infinite;
            pointer-events: none;
          }
          .ft-pdf-button.is-speak-training-hint::after {
            content: "";
            position: absolute;
            left: 12%;
            right: 12%;
            bottom: -7px;
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, transparent, rgba(255, 223, 143, 0.9), rgba(80, 255, 231, 0.72), transparent);
            box-shadow: 0 0 16px rgba(255, 208, 100, 0.45);
            animation: ftPdfSpeakTrainingScan 0.9s ease-in-out infinite;
            pointer-events: none;
          }
          @keyframes ftPdfSpeakTrainingNudge {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-7px); }
          }
          @keyframes ftPdfSpeakTrainingAura {
            0%, 100% { opacity: 0.32; transform: scale(0.96); }
            50% { opacity: 0.88; transform: scale(1.05); }
          }
          @keyframes ftPdfSpeakTrainingScan {
            0%, 100% { opacity: 0.35; transform: scaleX(0.52); }
            50% { opacity: 1; transform: scaleX(1); }
          }
          .ft-pdf-goto-input {
            width: 78px;
            min-height: 38px;
            border-radius: 12px;
            padding: 0 12px;
            text-align: center;
            font-weight: 900;
            color: #fff1c7;
            border-color: rgba(255, 188, 90, 0.48);
            background:
              linear-gradient(135deg, rgba(255, 175, 64, 0.14), rgba(70, 240, 215, 0.08)),
              rgba(8, 18, 32, 0.84);
          }
          .ft-pdf-goto-input:focus {
            outline: none;
            border-color: rgba(255, 211, 126, 0.88);
            box-shadow:
              0 0 0 2px rgba(255, 188, 90, 0.14),
              0 0 24px rgba(255, 170, 64, 0.22),
              inset 0 0 18px rgba(70, 240, 215, 0.1);
          }
          .ft-pdf-status {
            margin-left: auto;
            text-transform: none;
            letter-spacing: 0.06em;
            color: rgba(255, 222, 153, 0.9);
          }
          .ft-pdf-status.is-busy {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            color: #ffe8b9;
            text-shadow: 0 0 14px rgba(255, 181, 72, 0.34), 0 0 24px rgba(79, 255, 226, 0.18);
          }
          .ft-pdf-status.is-busy::before {
            content: "";
            width: 19px;
            height: 19px;
            border-radius: 40% 62% 44% 58%;
            border: 1px solid rgba(255, 209, 128, 0.78);
            background:
              radial-gradient(circle at 36% 34%, rgba(255, 244, 194, 0.95) 0 12%, transparent 13%),
              radial-gradient(circle at 66% 58%, rgba(83, 255, 226, 0.8) 0 10%, transparent 11%),
              linear-gradient(135deg, rgba(255, 161, 52, 0.28), rgba(24, 44, 58, 0.14));
            box-shadow:
              0 0 18px rgba(255, 184, 75, 0.38),
              inset 0 0 14px rgba(90, 255, 230, 0.16);
            animation: ftPdfVocabForgeCore 1.28s ease-in-out infinite;
          }
          .ft-pdf-status.is-busy::after {
            content: "";
            width: 34px;
            height: 9px;
            border-radius: 999px;
            background:
              linear-gradient(90deg, transparent, rgba(255, 203, 118, 0.92), rgba(81, 255, 231, 0.78), transparent);
            box-shadow: 0 0 16px rgba(255, 182, 80, 0.28);
            animation: ftPdfVocabForgeBeam 1.05s cubic-bezier(.2, .74, .24, 1) infinite;
          }
          .ft-pdf-button.is-busy,
          .ft-pdf-button:disabled.is-busy {
            cursor: progress;
            color: #fff3c7;
            border-color: rgba(255, 197, 105, 0.86);
            background:
              linear-gradient(135deg, rgba(255, 158, 48, 0.22), rgba(53, 255, 224, 0.1)),
              linear-gradient(180deg, rgba(255,255,255,0.08), transparent);
            box-shadow:
              0 0 26px rgba(255, 170, 64, 0.25),
              inset 0 0 22px rgba(255, 208, 116, 0.13);
            opacity: 0.94;
            animation: ftPdfVocabBusyButton 1.18s ease-in-out infinite;
          }
          .ft-pdf-button.is-busy::after {
            content: "";
            position: absolute;
            inset: 5px 8px;
            border-radius: 9px;
            background:
              linear-gradient(105deg, transparent 0 34%, rgba(255,255,255,0.42) 46%, transparent 58% 100%);
            transform: translateX(-120%);
            animation: ftPdfVocabBusySweep 1.22s cubic-bezier(.2, .76, .16, 1) infinite;
            pointer-events: none;
          }
          @keyframes ftPdfVocabForgeCore {
            0%, 100% { transform: rotate(-8deg) scale(0.94); filter: saturate(1); }
            45% { transform: rotate(12deg) scale(1.08); filter: saturate(1.45); }
            70% { transform: rotate(2deg) scale(0.98); }
          }
          @keyframes ftPdfVocabForgeBeam {
            0% { opacity: 0.25; transform: scaleX(0.35); }
            48% { opacity: 1; transform: scaleX(1); }
            100% { opacity: 0.28; transform: scaleX(0.48); }
          }
          @keyframes ftPdfVocabBusyButton {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-2px); }
          }
          @keyframes ftPdfVocabBusySweep {
            0% { transform: translateX(-130%); opacity: 0; }
            20% { opacity: 0.75; }
            100% { transform: translateX(130%); opacity: 0; }
          }
          .ft-pdf-vocab-stats {
            position: relative;
            z-index: 1;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            min-height: 34px;
            padding: 0 12px;
            border: 1px solid rgba(255, 185, 87, 0.34);
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(255, 165, 54, 0.12), rgba(53, 245, 218, 0.08));
            color: #ffe2a9;
            box-shadow: inset 0 0 18px rgba(255, 177, 71, 0.08), 0 0 22px rgba(255, 177, 71, 0.08);
            text-transform: none;
            letter-spacing: 0.06em;
          }
          .ft-pdf-stage {
            position: relative;
            z-index: 1;
            min-height: 0;
            overflow: auto;
            padding: 16px 18px 20px;
            cursor: grab;
            touch-action: none;
          }
          .ft-pdf-stage-loader {
            position: absolute;
            left: 52%;
            top: 50%;
            z-index: 5;
            display: none;
            width: min(920px, calc(100% - 64px));
            min-height: min(42vh, 320px);
            align-items: center;
            justify-content: stretch;
            gap: 0;
            padding: 14px 16px;
            color: #efffff;
            background: transparent;
            box-shadow: none;
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
            transform: translate(-50%, -50%) scale(0.985);
            pointer-events: auto;
          }
          .ft-pdf-space.is-rendering-page .ft-pdf-stage-loader {
            display: flex;
            animation: ftPdfStageLoaderIn 260ms cubic-bezier(.16,.84,.22,1) both;
          }
          .ft-pdf-space.is-rendering-page .ft-pdf-page-wrap {
            visibility: hidden;
          }
          .ft-pdf-page-wrap.is-empty {
            display: none;
          }
          .ft-pdf-stage-loader-core {
            position: relative;
            justify-self: start;
            width: 44px;
            aspect-ratio: 1;
            border-radius: 50%;
            background:
              radial-gradient(circle, rgba(236, 255, 249, 0.98) 0 3px, transparent 4px),
              radial-gradient(circle at 50% 50%, rgba(70, 255, 230, 0.2), rgba(6, 25, 39, 0.95) 62%, rgba(2, 9, 18, 1));
            box-shadow:
              0 0 0 2px rgba(255, 255, 255, 0.66),
              0 0 0 7px rgba(2, 8, 15, 0.74),
              0 0 24px rgba(70, 255, 230, 0.28),
              inset 0 0 20px rgba(70, 240, 215, 0.14);
          }
          .ft-pdf-stage-loader-core::before,
          .ft-pdf-stage-loader-core::after {
            content: "";
            position: absolute;
            inset: 7px;
            border-radius: inherit;
            border: 2px solid transparent;
            border-top-color: rgba(76, 255, 231, 0.94);
            border-right-color: rgba(255, 201, 91, 0.7);
            animation: ftPdfStageLoaderOrbit 1s linear infinite;
          }
          .ft-pdf-stage-loader-core::after {
            inset: 17px;
            border-width: 1px;
            border-top-color: rgba(255, 238, 176, 0.82);
            border-right-color: rgba(80, 255, 231, 0.62);
            animation-duration: 0.68s;
            animation-direction: reverse;
          }
          .ft-pdf-stage-loader-copy {
            min-width: 0;
            box-sizing: border-box;
            display: grid;
            align-content: center;
            gap: 8px;
            width: min(34vw, 320px);
            max-width: 320px;
            min-height: 118px;
            align-self: center;
            padding: 18px 22px;
            overflow: hidden;
            border: 1px solid rgba(80, 255, 231, 0.4);
            border-radius: 16px;
            background:
              radial-gradient(circle at 18% 18%, rgba(255, 210, 116, 0.14), transparent 36%),
              linear-gradient(135deg, rgba(70, 240, 215, 0.15), rgba(255, 178, 72, 0.07)),
              rgba(4, 14, 25, 0.9);
            box-shadow:
              0 20px 54px rgba(0, 0, 0, 0.42),
              0 0 28px rgba(70, 240, 215, 0.14),
              inset 0 0 20px rgba(70, 240, 215, 0.07);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
          }
          .ft-pdf-stage-loader-preview {
            position: relative;
            display: grid;
            place-items: center;
            width: min(44vw, 520px);
            min-width: 260px;
            min-height: min(36vh, 280px);
            overflow: hidden;
            border: 1px solid rgba(78, 255, 231, 0.42);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(80, 255, 231, 0.12), rgba(255, 209, 116, 0.06)),
              rgba(2, 9, 18, 0.82);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            box-shadow:
              0 18px 42px rgba(0, 0, 0, 0.34),
              0 0 34px rgba(80, 255, 231, 0.16),
              inset 0 0 24px rgba(80, 255, 231, 0.08);
          }
          .ft-pdf-stage-loader-preview::before {
            content: "";
            position: absolute;
            inset: 10px;
            border-radius: 10px;
            pointer-events: auto;
            opacity: 0;
          }
          .ft-pdf-stage-loader.is-thumbnail-charging .ft-pdf-stage-loader-preview::before {
            opacity: 1;
            border: 1px solid rgba(80, 255, 231, 0.28);
            background:
              radial-gradient(circle at 18% 26%, rgba(80, 255, 231, 0.26), transparent 26%),
              radial-gradient(circle at 78% 72%, rgba(255, 208, 116, 0.18), transparent 30%);
            animation: ftPdfPreviewCharge 1.05s ease-in-out infinite;
          }
          .ft-pdf-stage-loader-arc {
            position: relative;
            display: block;
            flex: 0 0 72px;
            height: 118px;
            align-self: center;
            margin: 0 20px;
            opacity: 0;
          }
          .ft-pdf-stage-loader-arc::before,
          .ft-pdf-stage-loader-arc::after {
            content: "";
            position: absolute;
            left: 0;
            top: 50%;
            width: 100%;
            height: 2px;
            border-radius: 999px;
            clip-path: none;
            background:
              linear-gradient(90deg, rgba(80, 255, 231, 0), rgba(80, 255, 231, 0.95), rgba(255, 238, 176, 0.96), rgba(80, 255, 231, 0));
            filter:
              drop-shadow(0 0 7px rgba(80, 255, 231, 0.9))
              drop-shadow(0 0 18px rgba(255, 218, 128, 0.36));
            transform-origin: left center;
          }
          .ft-pdf-stage-loader-arc::after {
            top: 50%;
            height: 54px;
            opacity: 0.78;
            border-radius: 999px;
            background:
              radial-gradient(circle at 8% 50%, rgba(80, 255, 231, 0.95) 0 2px, transparent 4px),
              radial-gradient(circle at 38% 18%, rgba(255, 238, 176, 0.78) 0 1px, transparent 3px),
              radial-gradient(circle at 62% 78%, rgba(80, 255, 231, 0.74) 0 1px, transparent 3px),
              radial-gradient(circle at 92% 50%, rgba(255, 238, 176, 0.86) 0 2px, transparent 4px);
            filter:
              drop-shadow(0 0 8px rgba(80, 255, 231, 0.7))
              drop-shadow(0 0 18px rgba(80, 255, 231, 0.22));
            transform: translateY(-50%);
          }
          .ft-pdf-stage-loader.is-thumbnail-charging .ft-pdf-stage-loader-arc {
            opacity: 1;
          }
          .ft-pdf-stage-loader.is-thumbnail-charging .ft-pdf-stage-loader-arc::before {
            animation: ftPdfPreviewSpark 0.86s cubic-bezier(.2,.78,.2,1) infinite;
          }
          .ft-pdf-stage-loader.is-thumbnail-charging .ft-pdf-stage-loader-arc::after {
            animation: ftPdfPreviewSparkAlt 1.18s ease-in-out infinite;
          }
          .ft-pdf-stage-loader-thumb {
            display: none;
            width: 100%;
            height: 100%;
            max-width: calc(100% - 18px);
            max-height: calc(100% - 18px);
            object-fit: contain;
            justify-self: center;
            padding: 4px;
            border: 1px solid rgba(255, 236, 184, 0.26);
            border-radius: 12px;
            background: rgba(4, 12, 20, 0.72);
            box-shadow:
              0 14px 30px rgba(0, 0, 0, 0.32),
              0 0 22px rgba(80, 255, 231, 0.12);
          }
          .ft-pdf-stage-loader-thumb.is-visible {
            display: block;
          }
          .ft-pdf-stage-loader-copy strong {
            font-size: 13px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #fff1c3;
          }
          .ft-pdf-stage-loader-copy span {
            max-width: 100%;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            color: rgba(224, 255, 250, 0.84);
            font-size: 12px;
            font-weight: 800;
          }
          .ft-pdf-load-meter {
            position: relative;
            display: block;
            width: 100%;
            max-width: 100%;
            height: 9px;
            overflow: hidden;
            border: 1px solid rgba(80, 255, 231, 0.38);
            border-radius: 999px;
            background:
              linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px) 0 0 / 18px 100%,
              rgba(4, 13, 24, 0.78);
            box-shadow:
              inset 0 0 14px rgba(80, 255, 231, 0.09),
              0 0 18px rgba(80, 255, 231, 0.12);
          }
          .ft-pdf-load-meter i {
            position: absolute;
            inset: 0 auto 0 0;
            width: var(--pdf-load-progress, 0%);
            min-width: 0;
            border-radius: inherit;
            background:
              linear-gradient(90deg, rgba(80, 255, 231, 0.18), rgba(80, 255, 231, 0.94), rgba(255, 211, 116, 0.82)),
              repeating-linear-gradient(115deg, rgba(255,255,255,0.24) 0 4px, transparent 4px 10px);
            box-shadow:
              0 0 18px rgba(80, 255, 231, 0.38),
              0 0 28px rgba(255, 196, 91, 0.18);
            transition: width 120ms linear;
          }
          .ft-pdf-load-meter i::after {
            content: "";
            position: absolute;
            top: -5px;
            right: -10px;
            width: 22px;
            height: 20px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255,255,255,0.96) 0 2px, rgba(255, 221, 139, 0.88) 3px, rgba(80, 255, 231, 0.38) 8px, transparent 70%);
            filter: blur(0.2px);
            animation: ftPdfLoadPulse 0.9s ease-in-out infinite;
          }
          .ft-pdf-load-meter-copy {
            display: block;
            max-width: 100%;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            color: rgba(255, 230, 177, 0.86) !important;
            font-size: 11px !important;
            letter-spacing: 0.08em;
          }
          .ft-pdf-stage-loader-copy::after {
            content: none;
          }
          @keyframes ftPdfStageLoaderIn {
            from { opacity: 0; transform: translate(-50%, -48%) scale(0.95); filter: blur(5px); }
            to { opacity: 1; transform: translate(-50%, -50%) scale(1); filter: blur(0); }
          }
          @keyframes ftPdfPreviewCharge {
            0% { opacity: 0.42; filter: brightness(0.9); }
            45% { opacity: 1; }
            100% { opacity: 0.68; filter: brightness(1.22); }
          }
          @keyframes ftPdfPreviewSpark {
            0%, 100% { transform: translateY(-50%) scaleX(0.18); opacity: 0; }
            18% { transform: translateY(-50%) scaleX(1); opacity: 0.96; }
            38% { transform: translateY(-50%) scaleX(0.58); opacity: 0.34; }
            64% { transform: translateY(-50%) scaleX(0.92); opacity: 0.78; }
          }
          @keyframes ftPdfPreviewSparkAlt {
            0%, 100% { transform: translateY(-50%) scale(0.86); opacity: 0.18; }
            42% { transform: translateY(-50%) scale(1.08); opacity: 0.84; }
            70% { transform: translateY(-50%) scale(0.92); opacity: 0.32; }
          }
          @keyframes ftPdfStageLoaderOrbit {
            to { transform: rotate(360deg); }
          }
          @keyframes ftPdfStageLoaderScan {
            0% { opacity: 0; transform: translateX(-36%); }
            35% { opacity: 1; }
            100% { opacity: 0; transform: translateX(36%); }
          }
          @keyframes ftPdfLoadPulse {
            0%, 100% { opacity: 0.52; transform: scale(0.78); }
            50% { opacity: 1; transform: scale(1.18); }
          }
          .ft-pdf-navigator {
            --pdf-nav-x: 0px;
            --pdf-nav-y: 0px;
            --pdf-nav-power: 0;
            --pdf-nav-angle: 0deg;
            position: fixed;
            right: clamp(14px, 2vw, 24px);
            bottom: clamp(14px, 2vw, 24px);
            z-index: 172;
            width: clamp(52px, 5.4vw, 68px);
            aspect-ratio: 1;
            border: 1px solid rgba(255, 223, 150, 0.86);
            border-radius: 50%;
            padding: 0;
            display: grid;
            place-items: center;
            color: #f8fffb;
            background:
              radial-gradient(circle at 34% 24%, rgba(255, 246, 208, 0.28), transparent 0 10%, rgba(255, 186, 76, 0.18) 11% 21%, transparent 22%),
              radial-gradient(circle at 58% 62%, rgba(79, 255, 231, 0.18), transparent 0 22%, transparent 30%),
              repeating-radial-gradient(circle at 50% 50%, rgba(80, 255, 231, 0.08) 0 1px, transparent 2px 9px),
              radial-gradient(circle at 50% 50%, rgba(10, 33, 49, 0.98) 0 58%, rgba(5, 14, 28, 0.99) 59% 100%);
            box-shadow:
              0 0 0 2px rgba(255, 255, 255, 0.72),
              0 0 0 6px rgba(2, 8, 15, 0.78),
              0 0 30px rgba(70, 255, 230, 0.22),
              0 0 24px rgba(255, 177, 69, 0.24),
              0 18px 42px rgba(0, 0, 0, 0.56),
              inset 0 0 0 1px rgba(255, 246, 208, 0.14),
              inset 0 0 24px rgba(70, 240, 215, 0.12);
            cursor: crosshair;
            user-select: none;
            touch-action: none;
            overflow: hidden;
            transform: translate3d(0, 0, 0);
            transition: transform 180ms ease, filter 180ms ease, opacity 180ms ease;
          }
          .ft-pdf-space.is-hidden .ft-pdf-navigator {
            display: none;
          }
          .ft-pdf-navigator:hover,
          .ft-pdf-navigator.is-active,
          .ft-pdf-navigator.is-coasting {
            filter: brightness(1.16) saturate(1.18);
            transform: translate3d(0, -2px, 0) scale(1.04);
          }
          .ft-pdf-navigator::before,
          .ft-pdf-navigator::after {
            content: "";
            position: absolute;
            pointer-events: none;
            border-radius: 50%;
          }
          .ft-pdf-navigator::before {
            inset: 12%;
            border: 1px solid rgba(236, 255, 249, 0.44);
            background:
              linear-gradient(90deg, transparent 0 47%, rgba(255, 244, 204, 0.62) 48% 52%, transparent 53%),
              linear-gradient(180deg, transparent 0 47%, rgba(70, 255, 230, 0.52) 48% 52%, transparent 53%);
            transform: rotateX(64deg) rotateZ(-18deg);
            box-shadow: 0 0 16px rgba(255, 180, 66, 0.24), inset 0 0 12px rgba(70, 255, 230, 0.08);
          }
          .ft-pdf-navigator::after {
            inset: -10%;
            border: 1px dashed rgba(255, 219, 148, 0.48);
            animation: ftPdfNavigatorOrbit 8s linear infinite;
          }
          .ft-pdf-navigator.is-active::after,
          .ft-pdf-navigator.is-coasting::after {
            animation-duration: 4.8s;
          }
          .ft-pdf-navigator-grid {
            position: absolute;
            inset: 18%;
            border-radius: 50%;
            background:
              linear-gradient(90deg, transparent 0 47%, rgba(255, 246, 208, 0.34) 48% 52%, transparent 53%),
              linear-gradient(180deg, transparent 0 47%, rgba(255, 246, 208, 0.3) 48% 52%, transparent 53%),
              repeating-linear-gradient(0deg, transparent 0 7px, rgba(255, 188, 84, 0.16) 8px 9px, transparent 10px 15px),
              repeating-linear-gradient(90deg, transparent 0 7px, rgba(70, 240, 215, 0.16) 8px 9px, transparent 10px 15px);
            mask-image: radial-gradient(circle, black 0 68%, transparent 72%);
            opacity: 0.72;
            pointer-events: none;
          }
          .ft-pdf-navigator-ring {
            position: absolute;
            border-radius: 50%;
            border: 1px solid rgba(255, 206, 122, 0.24);
            pointer-events: none;
            filter: drop-shadow(0 0 8px rgba(255, 179, 64, 0.2));
          }
          .ft-pdf-navigator-ring.is-a {
            inset: 8%;
            transform: rotateX(68deg) rotateZ(32deg);
            animation: ftPdfNavigatorRingA 6.2s linear infinite;
          }
          .ft-pdf-navigator-ring.is-b {
            inset: 23%;
            border-color: rgba(70, 240, 215, 0.28);
            transform: rotateX(64deg) rotateZ(-38deg);
            animation: ftPdfNavigatorRingB 5.4s linear infinite reverse;
          }
          .ft-pdf-navigator-vector {
            position: absolute;
            left: 50%;
            top: 50%;
            width: calc(10px + var(--pdf-nav-power) * 18px);
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, rgba(255, 246, 208, 0.94), rgba(255, 182, 69, 0.88), transparent);
            box-shadow: 0 0 12px rgba(255, 174, 61, 0.48);
            opacity: calc(0.22 + var(--pdf-nav-power) * 0.62);
            transform: translateY(-50%) rotate(var(--pdf-nav-angle));
            transform-origin: left center;
            pointer-events: none;
          }
          .ft-pdf-navigator-core {
            position: absolute;
            width: 19%;
            aspect-ratio: 1;
            border-radius: 50%;
            background: rgba(255, 248, 218, 0.96);
            box-shadow:
              0 0 10px rgba(255, 246, 208, 0.8),
              0 0 22px rgba(255, 174, 61, 0.58);
            pointer-events: none;
          }
          .ft-pdf-navigator-dot {
            position: absolute;
            left: calc(50% + var(--pdf-nav-x));
            top: calc(50% + var(--pdf-nav-y));
            width: 7px;
            aspect-ratio: 1;
            border-radius: 50%;
            background: rgba(70, 255, 230, 0.98);
            box-shadow:
              0 0 0 2px rgba(3, 12, 22, 0.84),
              0 0 12px rgba(70, 255, 230, 0.86),
              0 0 20px rgba(255, 184, 73, 0.4);
            transform: translate(-50%, -50%);
            pointer-events: none;
          }
          @keyframes ftPdfNavigatorOrbit {
            to { transform: rotate(360deg); }
          }
          @keyframes ftPdfNavigatorRingA {
            to { transform: rotateX(68deg) rotateZ(392deg); }
          }
          @keyframes ftPdfNavigatorRingB {
            to { transform: rotateX(64deg) rotateZ(-398deg); }
          }
          .ft-pdf-stage.is-panning {
            cursor: grabbing;
            user-select: none;
          }
          .ft-pdf-console-close {
            width: 34px;
            height: 34px;
            border: 1px solid rgba(255, 188, 84, 0.42);
            border-radius: 12px;
            display: inline-grid;
            place-items: center;
            color: #fff1c7;
            background:
              linear-gradient(135deg, rgba(255, 174, 64, 0.14), rgba(70, 240, 215, 0.08)),
              rgba(8, 18, 32, 0.86);
            box-shadow: inset 0 0 14px rgba(255, 184, 73, 0.1), 0 0 18px rgba(255, 184, 73, 0.1);
            cursor: pointer;
            font-size: 18px;
            font-weight: 900;
            line-height: 1;
          }
          .ft-pdf-console-close:hover,
          .ft-pdf-console-close:focus-visible {
            outline: none;
            border-color: rgba(255, 211, 126, 0.86);
            box-shadow:
              0 0 22px rgba(255, 180, 66, 0.22),
              inset 0 0 16px rgba(70, 240, 215, 0.1);
          }
          .ft-pdf-page-wrap {
            position: relative;
            width: max-content;
            max-width: 100%;
            margin: 0 auto;
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.04);
            box-shadow: 0 18px 60px rgba(0, 0, 0, 0.42), 0 0 0 1px rgba(126, 255, 232, 0.18);
            overflow: hidden;
          }
          .ft-pdf-page-wrap.is-selecting { cursor: crosshair; }
          .ft-pdf-page-wrap.is-shift-selecting::after {
            content: "ADD REGION";
            position: absolute;
            right: 14px;
            top: 14px;
            z-index: 8;
            pointer-events: none;
            padding: 7px 12px;
            border-radius: 999px;
            border: 1px solid rgba(255, 187, 76, 0.72);
            background:
              linear-gradient(135deg, rgba(12, 20, 24, 0.86), rgba(33, 18, 10, 0.78)),
              radial-gradient(circle at 20% 30%, rgba(102, 255, 231, 0.24), transparent 44%);
            color: #ffe6b0;
            font: 900 10px/1 "Orbitron", "Inter", sans-serif;
            letter-spacing: 1.4px;
            text-shadow: 0 0 10px rgba(255, 166, 55, 0.72);
            box-shadow:
              0 10px 30px rgba(0, 0, 0, 0.46),
              0 0 0 1px rgba(0, 0, 0, 0.56),
              0 0 24px rgba(255, 146, 42, 0.38),
              inset 0 0 18px rgba(77, 255, 232, 0.1);
            animation: ftPdfShiftBadgePulse 1.45s ease-in-out infinite;
          }
          .ft-pdf-image {
            display: block;
            max-width: min(100%, 980px);
            height: auto;
            user-select: none;
            -webkit-touch-callout: none;
            -webkit-user-drag: none;
            background: #fff;
          }
          .ft-pdf-image:not([src]),
          .ft-pdf-image[src=""] {
            display: none;
          }
          .ft-pdf-draw-canvas {
            position: absolute;
            left: 0;
            top: 0;
            z-index: 5;
            width: 1px;
            height: 1px;
            pointer-events: auto;
            touch-action: none;
            opacity: 1;
            transition: opacity 0.18s ease;
          }
          .ft-pdf-space.is-pen-active .ft-pdf-draw-canvas {
            pointer-events: auto;
            cursor: crosshair;
          }
          .ft-pdf-space.is-text-active .ft-pdf-draw-canvas {
            pointer-events: auto;
            cursor: text;
          }
          .ft-pdf-space.is-eraser-active .ft-pdf-draw-canvas {
            pointer-events: auto;
            cursor: none;
          }
          .ft-pdf-audio-layer {
            position: absolute;
            inset: 0;
            z-index: 8;
            pointer-events: none;
          }
          .ft-pdf-audio-layer[hidden] {
            display: none;
          }
          .ft-pdf-audio-marker {
            position: absolute;
            left: 0;
            top: 0;
            max-width: min(220px, calc(100% - 12px));
            min-height: 36px;
            padding: 0 12px 0 10px;
            border: 1px solid rgba(126, 255, 232, 0.42);
            border-radius: 12px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transform: translate(-50%, -50%);
            pointer-events: auto;
            cursor: pointer;
            background:
              radial-gradient(circle at 22% 22%, rgba(255, 219, 133, 0.24), transparent 44%),
              linear-gradient(135deg, rgba(9, 23, 37, 0.96), rgba(16, 30, 49, 0.9));
            color: #efffff;
            box-shadow:
              0 14px 34px rgba(0, 0, 0, 0.34),
              0 0 22px rgba(70, 240, 215, 0.14),
              inset 0 0 0 1px rgba(255, 255, 255, 0.04);
            transition:
              transform 160ms ease,
              border-color 160ms ease,
              box-shadow 160ms ease,
              background 160ms ease,
              opacity 160ms ease;
          }
          .ft-pdf-space.is-audio-insert-active .ft-pdf-audio-layer,
          .ft-pdf-space.is-audio-move-active .ft-pdf-audio-layer,
          .ft-pdf-space.is-audio-dragging .ft-pdf-audio-layer {
            pointer-events: auto;
          }
          .ft-pdf-space.is-pen-active .ft-pdf-audio-layer,
          .ft-pdf-space.is-text-active .ft-pdf-audio-layer,
          .ft-pdf-space.is-eraser-active .ft-pdf-audio-layer {
            pointer-events: none !important;
          }
          .ft-pdf-space.is-pen-active .ft-pdf-audio-marker,
          .ft-pdf-space.is-text-active .ft-pdf-audio-marker,
          .ft-pdf-space.is-eraser-active .ft-pdf-audio-marker {
            pointer-events: none !important;
          }
          .ft-pdf-audio-marker:hover,
          .ft-pdf-audio-marker:focus-visible {
            outline: none;
            border-color: rgba(255, 196, 98, 0.92);
            transform: translate(-50%, calc(-50% - 1px));
            box-shadow:
              0 18px 40px rgba(0, 0, 0, 0.4),
              0 0 26px rgba(255, 196, 98, 0.18),
              0 0 18px rgba(70, 240, 215, 0.14);
          }
          .ft-pdf-audio-marker.is-empty {
            border-style: dashed;
            border-color: rgba(255, 132, 162, 0.72);
            color: #ffd7df;
            background:
              radial-gradient(circle at 20% 20%, rgba(255, 132, 162, 0.22), transparent 42%),
              linear-gradient(135deg, rgba(36, 13, 23, 0.96), rgba(30, 19, 28, 0.9));
          }
          .ft-pdf-audio-marker.is-playing {
            border-color: rgba(255, 214, 118, 0.94);
            color: #fff8db;
            background:
              radial-gradient(circle at 22% 22%, rgba(255, 214, 118, 0.32), transparent 42%),
              linear-gradient(135deg, rgba(34, 26, 10, 0.96), rgba(16, 32, 33, 0.92));
            box-shadow:
              0 16px 38px rgba(0, 0, 0, 0.42),
              0 0 28px rgba(255, 214, 118, 0.26),
              0 0 20px rgba(70, 240, 215, 0.18);
          }
          .ft-pdf-audio-marker.is-playing .ft-pdf-audio-marker-icon {
            color: #fff3c6;
            text-shadow: 0 0 14px rgba(255, 214, 118, 0.4);
          }
          .ft-pdf-audio-marker-glyph {
            display: inline-grid;
            place-items: center;
            width: 12px;
            font-size: 11px;
            line-height: 1;
          }
          .ft-pdf-audio-marker-wave {
            display: inline-flex;
            align-items: flex-end;
            gap: 2px;
            height: 12px;
            opacity: 0;
            transform: translateY(1px);
          }
          .ft-pdf-audio-marker-wave i {
            width: 2px;
            height: 4px;
            border-radius: 999px;
            background: linear-gradient(180deg, rgba(255, 245, 197, 0.92), rgba(72, 255, 228, 0.7));
            transform-origin: center bottom;
            transform: scaleY(0.35);
            opacity: 0.45;
          }
          .ft-pdf-audio-marker.is-playing .ft-pdf-audio-marker-wave {
            opacity: 1;
          }
          .ft-pdf-audio-marker.is-playing .ft-pdf-audio-marker-wave i {
            animation: ftPdfAudioWavePulse 900ms ease-in-out infinite;
            animation-delay: calc(var(--wave-index, 0) * 90ms);
          }
          .ft-pdf-audio-marker.is-paused .ft-pdf-audio-marker-wave,
          .ft-pdf-audio-marker.is-paused .ft-pdf-audio-marker-wave i {
            animation-play-state: paused;
          }
          .ft-pdf-audio-marker.is-move-target {
            border-color: rgba(94, 255, 231, 0.94);
            box-shadow:
              0 16px 38px rgba(0, 0, 0, 0.42),
              0 0 30px rgba(94, 255, 231, 0.24),
              inset 0 0 18px rgba(94, 255, 231, 0.1);
          }
          .ft-pdf-audio-marker.is-image-always {
            max-width: none;
            min-height: 44px;
            padding: 0;
            overflow: visible;
            border-radius: 10px;
            background: rgba(5, 14, 24, 0.28);
            border-color: rgba(126, 255, 232, 0.52);
          }
          .ft-pdf-audio-marker.is-image-always .ft-pdf-audio-marker-image {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: contain;
            border-radius: 9px;
            background: rgba(2, 8, 14, 0.72);
            box-shadow: 0 12px 34px rgba(0, 0, 0, 0.38);
            pointer-events: none;
          }
          .ft-pdf-audio-marker-image-resize {
            position: absolute;
            right: -8px;
            bottom: -8px;
            width: 18px;
            height: 18px;
            border-radius: 7px;
            border: 1px solid rgba(255, 245, 213, 0.88);
            background: linear-gradient(135deg, rgba(255, 214, 118, 0.98), rgba(70, 240, 215, 0.9));
            box-shadow: 0 0 0 2px rgba(3, 10, 18, 0.68), 0 0 18px rgba(70, 240, 215, 0.22);
            cursor: nwse-resize;
            pointer-events: auto;
          }
          .ft-pdf-audio-marker-icon {
            display: inline-grid;
            place-items: center;
            width: 18px;
            height: 18px;
            flex: 0 0 18px;
            color: #fff5d5;
            font-size: 11px;
            line-height: 1;
            text-shadow: 0 0 12px rgba(255, 214, 118, 0.34);
          }
          .ft-pdf-audio-marker-label {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 0.04em;
          }
          .ft-pdf-audio-marker.is-playing,
          .ft-pdf-audio-marker.is-ended {
            flex-wrap: wrap;
            max-width: min(496px, calc(100% - 12px));
            padding: 6px 10px 7px;
            align-items: center;
          }
          .ft-pdf-audio-marker-panel {
            display: none;
            align-items: center;
            gap: 6px;
            flex-basis: 100%;
            width: 100%;
            margin-top: 5px;
            padding: 0;
            pointer-events: auto;
          }
          .ft-pdf-audio-marker.is-playing .ft-pdf-audio-marker-panel,
          .ft-pdf-audio-marker.is-ended .ft-pdf-audio-marker-panel {
            display: flex;
          }
          .ft-pdf-audio-marker-progress {
            position: relative;
            flex: 1 1 auto;
            width: auto;
            min-width: 96px;
            height: 12px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
            overflow: visible;
            cursor: pointer;
            touch-action: none;
          }
          .ft-pdf-audio-marker-progress-fill {
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 0%;
            border-radius: inherit;
            background: linear-gradient(90deg, rgba(255, 214, 118, 0.95), rgba(126, 255, 232, 0.9));
            box-shadow: 0 0 8px rgba(255, 214, 118, 0.4);
            transition: width 120ms linear;
          }
          .ft-pdf-audio-marker-progress-pin {
            position: absolute;
            left: 0;
            top: 50%;
            z-index: 2;
            width: 18px;
            height: 24px;
            border-radius: 999px;
            border: 1px solid rgba(255, 245, 213, 0.95);
            background:
              radial-gradient(circle at 50% 42%, #fff5d5 0 3px, transparent 4px),
              linear-gradient(180deg, rgba(255, 196, 98, 0.98), rgba(255, 121, 77, 0.88));
            box-shadow:
              0 0 0 2px rgba(9, 23, 37, 0.62),
              0 0 14px rgba(255, 196, 98, 0.48);
            cursor: grab;
            opacity: 0.72;
            transform: translate(-50%, -50%) scale(0.92);
            transition: opacity 140ms ease, transform 140ms ease, box-shadow 140ms ease;
            touch-action: none;
          }
          .ft-pdf-audio-marker-progress-pin::after {
            content: "";
            position: absolute;
            left: 50%;
            top: 100%;
            width: 2px;
            height: 8px;
            border-radius: 999px;
            background: rgba(255, 245, 213, 0.9);
            transform: translateX(-50%);
          }
          .ft-pdf-audio-marker-progress-pin-time {
            position: absolute;
            left: 50%;
            bottom: calc(100% + 6px);
            padding: 2px 5px;
            border-radius: 999px;
            border: 1px solid rgba(255, 245, 213, 0.68);
            background: rgba(9, 23, 37, 0.9);
            color: #fff5d5;
            font-size: 9px;
            font-weight: 900;
            line-height: 1;
            white-space: nowrap;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.26);
            transform: translateX(-50%);
            pointer-events: none;
          }
          .ft-pdf-audio-marker-progress-pin.is-set,
          .ft-pdf-audio-marker-progress-pin:hover {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
          .ft-pdf-audio-marker-progress-pin:active {
            cursor: grabbing;
            box-shadow:
              0 0 0 3px rgba(9, 23, 37, 0.7),
              0 0 20px rgba(255, 196, 98, 0.62);
          }
          .ft-pdf-audio-marker-time {
            font-size: 9.5px;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            color: rgba(255, 248, 219, 0.92);
            letter-spacing: 0.02em;
            white-space: nowrap;
            flex: 0 0 auto;
          }
          .ft-pdf-audio-marker-video-wrap {
            display: block;
            flex: 0 0 100%;
            width: 100%;
            margin: 0 0 5px;
            border: 1px solid rgba(126, 255, 232, 0.3);
            border-radius: 8px;
            overflow: hidden;
            background: rgba(2, 8, 14, 0.84);
            box-shadow: inset 0 0 18px rgba(126, 255, 232, 0.08);
          }
          .ft-pdf-audio-marker-video {
            display: block;
            width: 100%;
            max-height: 180px;
            object-fit: contain;
            background: #02070c;
          }
          .ft-pdf-audio-video-popover {
            position: fixed;
            z-index: 25000;
            border: 1px solid rgba(126, 255, 232, 0.36);
            border-radius: 12px;
            background:
              linear-gradient(145deg, rgba(7, 16, 26, 0.96), rgba(5, 8, 15, 0.98)),
              radial-gradient(circle at 100% 0, rgba(255, 196, 98, 0.12), transparent 40%);
            box-shadow:
              0 24px 80px rgba(0, 0, 0, 0.48),
              0 0 32px rgba(126, 255, 232, 0.14),
              inset 0 0 24px rgba(126, 255, 232, 0.06);
            overflow: hidden;
            color: #fff5d5;
          }
          .ft-pdf-audio-video-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            padding: 9px 10px;
            border-bottom: 1px solid rgba(126, 255, 232, 0.18);
            background: rgba(4, 12, 20, 0.88);
          }
          .ft-pdf-audio-video-title {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 12px;
            font-weight: 950;
            letter-spacing: 0.03em;
          }
          .ft-pdf-audio-video-close {
            display: inline-grid;
            place-items: center;
            width: 24px;
            height: 24px;
            border: 1px solid rgba(255, 122, 122, 0.42);
            border-radius: 7px;
            background: rgba(40, 10, 14, 0.68);
            color: #ffd7d7;
            cursor: pointer;
          }
          .ft-pdf-audio-video-open {
            flex: 0 0 auto;
            border: 1px solid rgba(126, 255, 232, 0.36);
            border-radius: 7px;
            padding: 5px 8px;
            color: #aef6ec;
            background: rgba(8, 28, 35, 0.72);
            font-size: 11px;
            font-weight: 900;
            text-decoration: none;
          }
          .ft-pdf-audio-video-body {
            padding: 10px;
          }
          .ft-pdf-audio-video-body .ft-pdf-audio-marker-video {
            width: 100%;
            max-height: min(62vh, 520px);
            border-radius: 9px;
            background: #02070c;
          }
          .ft-pdf-audio-popup-image {
            display: block;
            max-width: min(72vw, 860px);
            max-height: min(68vh, 680px);
            object-fit: contain;
            border-radius: 12px;
            background: rgba(2, 8, 14, 0.88);
          }
          .ft-pdf-audio-web-frame {
            display: block;
            width: 100%;
            height: min(62vh, 520px);
            border: 0;
            border-radius: 9px;
            background: #02070c;
          }
          .ft-pdf-audio-video-connector {
            position: fixed;
            z-index: 24999;
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, rgba(255, 196, 98, 0.9), rgba(126, 255, 232, 0.55));
            box-shadow: 0 0 14px rgba(126, 255, 232, 0.28);
            transform-origin: 0 50%;
            pointer-events: none;
          }
          .ft-pdf-audio-video-connector.is-hidden {
            display: none;
          }
          .ft-pdf-audio-marker-btn {
            display: inline-grid;
            place-items: center;
            width: 18px;
            height: 18px;
            padding: 0;
            border: 1px solid rgba(126, 255, 232, 0.4);
            border-radius: 6px;
            background: rgba(9, 23, 37, 0.6);
            color: #fff5d5;
            font-size: 11px;
            line-height: 1;
            cursor: pointer;
            transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
            flex: 0 0 auto;
          }
          .ft-pdf-audio-marker-btn:hover {
            border-color: rgba(255, 196, 98, 0.92);
            background: rgba(34, 26, 10, 0.7);
            transform: translateY(-1px);
          }
          .ft-pdf-audio-marker-btn.is-pause {
            border-color: rgba(255, 196, 98, 0.55);
            background: rgba(40, 24, 6, 0.78);
            color: #ffd27a;
          }
          .ft-pdf-audio-marker-btn.is-pause:hover {
            border-color: rgba(255, 196, 98, 1);
            background: rgba(60, 36, 8, 0.88);
          }
          .ft-pdf-audio-marker-btn.is-replay {
            border-color: rgba(126, 255, 232, 0.45);
            color: #aef6ec;
          }
          .ft-pdf-audio-marker-btn.is-pin-replay {
            border-color: rgba(255, 214, 118, 0.52);
            color: #ffe7a8;
            background: rgba(38, 28, 9, 0.66);
          }
          .ft-pdf-audio-marker-btn.is-reset {
            border-color: rgba(255, 122, 122, 0.45);
            color: #ffc2c2;
          }
          .ft-pdf-audio-marker.is-ended .ft-pdf-audio-marker-progress-fill {
            width: 100% !important;
          }
          .ft-pdf-space.is-audio-insert-active .ft-pdf-page-wrap,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-image,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-audio-layer {
            cursor: copy;
          }
          .ft-pdf-space.is-audio-insert-active .ft-pdf-audio-marker {
            cursor: copy;
          }
          .ft-pdf-space.is-audio-move-active .ft-pdf-audio-marker.is-move-target {
            cursor: grab;
          }
          .ft-pdf-space.is-audio-dragging .ft-pdf-audio-marker.is-move-target {
            cursor: grabbing;
            transform: translate(-50%, -50%) scale(1.04);
          }
          .ft-pdf-audio-connector {
            position: fixed;
            z-index: 2147483209;
            min-width: 24px;
            min-height: 24px;
            pointer-events: auto;
            overflow: visible;
          }
          .ft-pdf-audio-connector.is-hidden {
            display: none;
          }
          .ft-pdf-audio-connector svg {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            overflow: visible;
          }
          .ft-pdf-audio-connector-line,
          .ft-pdf-audio-connector-glow {
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
          }
          .ft-pdf-audio-connector-line {
            stroke: url(#ft-pdf-audio-connector-gradient);
            stroke-width: 2.4;
            filter: url(#ft-pdf-audio-connector-glow);
            stroke-dasharray: 10 7;
            animation: ftPdfAudioConnectorFlow 1.25s linear infinite;
          }
          .ft-pdf-audio-connector-glow {
            stroke: rgba(70, 240, 215, 0.34);
            stroke-width: 8;
            opacity: 0.62;
          }
          .ft-pdf-audio-connector::before,
          .ft-pdf-audio-connector::after {
            content: "";
            position: absolute;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            pointer-events: auto;
            transform: translate(-50%, -50%);
            background:
              radial-gradient(circle, #fff9d9 0 18%, rgba(255, 214, 118, 0.98) 19% 48%, rgba(70, 240, 215, 0.72) 49% 72%, transparent 73%);
            box-shadow:
              0 0 12px rgba(255, 214, 118, 0.54),
              0 0 18px rgba(70, 240, 215, 0.34);
            animation: ftPdfAudioConnectorNode 1.3s ease-in-out infinite;
          }
          .ft-pdf-audio-connector::before {
            left: var(--ft-audio-connector-start-x, 0px);
            top: var(--ft-audio-connector-start-y, 0px);
          }
          .ft-pdf-audio-connector::after {
            left: var(--ft-audio-connector-end-x, 100%);
            top: var(--ft-audio-connector-end-y, 100%);
            animation-delay: 150ms;
          }
          .ft-pdf-audio-popover {
            position: fixed;
            z-index: 2147483210;
            width: min(430px, calc(100vw - 24px));
            display: grid;
            gap: 12px;
            padding: 14px;
            border: 1px solid rgba(126, 255, 232, 0.38);
            border-radius: 18px;
            background:
              radial-gradient(circle at 16% 10%, rgba(255, 214, 118, 0.18), transparent 28%),
              radial-gradient(circle at 84% 16%, rgba(70, 240, 215, 0.14), transparent 26%),
              linear-gradient(135deg, rgba(8, 17, 31, 0.98), rgba(14, 28, 46, 0.96));
            box-shadow:
              0 24px 64px rgba(0, 0, 0, 0.5),
              0 0 32px rgba(70, 240, 215, 0.12),
              inset 0 0 22px rgba(70, 240, 215, 0.06);
            backdrop-filter: blur(18px);
          }
          .ft-pdf-audio-popover.is-dragging {
            box-shadow:
              0 30px 80px rgba(0, 0, 0, 0.56),
              0 0 34px rgba(255, 214, 118, 0.14),
              inset 0 0 22px rgba(70, 240, 215, 0.06);
          }
          .ft-pdf-audio-popover.is-hidden {
            display: none;
          }
          .ft-pdf-audio-popover.is-audio-mode-video .ft-pdf-audio-text-field,
          .ft-pdf-audio-popover.is-audio-mode-video .ft-pdf-audio-voice-row,
          .ft-pdf-audio-popover.is-audio-mode-url .ft-pdf-audio-text-field,
          .ft-pdf-audio-popover.is-audio-mode-url .ft-pdf-audio-voice-row,
          .ft-pdf-audio-popover.is-audio-mode-image .ft-pdf-audio-text-field,
          .ft-pdf-audio-popover.is-audio-mode-image .ft-pdf-audio-voice-row,
          .ft-pdf-audio-popover.is-audio-mode-text .ft-pdf-audio-link-field {
            display: none;
          }
          .ft-pdf-audio-popover:not(.is-audio-mode-image) .ft-pdf-audio-display-field,
          .ft-pdf-audio-popover:not(.is-audio-mode-image) [data-pdf-audio-command="pasteImage"] {
            display: none;
          }
          .ft-pdf-audio-popover-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            cursor: grab;
            user-select: none;
          }
          .ft-pdf-audio-popover.is-dragging .ft-pdf-audio-popover-head {
            cursor: grabbing;
          }
          .ft-pdf-audio-popover-head span {
            color: #fff6da;
            font-size: 12px;
            font-weight: 950;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .ft-pdf-audio-popover-head button {
            width: 32px;
            height: 32px;
            padding: 0;
            border: 1px solid rgba(255, 132, 162, 0.34);
            border-radius: 10px;
            background: rgba(255, 97, 116, 0.1);
            color: #ffb4c2;
            cursor: pointer;
          }
          .ft-pdf-audio-popover-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }
          .ft-pdf-audio-popover-grid .is-wide {
            grid-column: 1 / -1;
          }
          .ft-pdf-audio-popover-grid label {
            min-width: 0;
            display: grid;
            gap: 6px;
          }
          .ft-pdf-audio-popover-grid label.is-wide {
            grid-column: 1 / -1;
          }
          .ft-pdf-audio-popover-grid span {
            color: rgba(180, 255, 239, 0.74);
            font-size: 10px;
            font-weight: 900;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-audio-popover-grid input,
          .ft-pdf-audio-popover-grid textarea,
          .ft-pdf-audio-popover-grid select {
            width: 100%;
            min-width: 0;
            border: 1px solid rgba(126, 255, 232, 0.26);
            border-radius: 12px;
            padding: 10px 12px;
            background:
              linear-gradient(135deg, rgba(7, 17, 29, 0.96), rgba(16, 29, 44, 0.9));
            color: #efffff;
            box-shadow: inset 0 0 16px rgba(70, 240, 215, 0.05);
          }
          .ft-pdf-audio-popover-grid textarea {
            min-height: 112px;
            resize: vertical;
          }
          .ft-pdf-audio-popover-grid input:focus,
          .ft-pdf-audio-popover-grid textarea:focus,
          .ft-pdf-audio-popover-grid select:focus {
            outline: none;
            border-color: rgba(255, 214, 118, 0.86);
            box-shadow:
              0 0 0 2px rgba(255, 214, 118, 0.12),
              0 0 18px rgba(255, 214, 118, 0.16),
              inset 0 0 18px rgba(70, 240, 215, 0.08);
          }
          .ft-pdf-audio-mode-switch {
            display: inline-flex;
            gap: 8px;
            padding: 4px;
            border: 1px solid rgba(126, 255, 232, 0.22);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(7, 17, 29, 0.94), rgba(12, 24, 38, 0.88));
          }
          .ft-pdf-audio-mode-switch button {
            min-height: 34px;
            padding: 0 14px;
            border: 1px solid transparent;
            border-radius: 10px;
            background: transparent;
            color: rgba(226, 255, 249, 0.82);
            cursor: pointer;
            font-weight: 900;
            letter-spacing: 0.04em;
          }
          .ft-pdf-audio-mode-switch button.is-active {
            border-color: rgba(255, 214, 118, 0.72);
            color: #fff4c7;
            background:
              radial-gradient(circle at 25% 20%, rgba(255, 214, 118, 0.26), transparent 42%),
              linear-gradient(135deg, rgba(255, 174, 64, 0.12), rgba(70, 240, 215, 0.08)),
              rgba(6, 16, 26, 0.96);
            box-shadow:
              0 0 18px rgba(255, 214, 118, 0.12),
              inset 0 0 18px rgba(70, 240, 215, 0.08);
          }
          .ft-pdf-audio-voice-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 10px;
            align-items: end;
          }
          .ft-pdf-audio-voice-field {
            min-width: 0;
          }
          .ft-pdf-audio-voice-shell {
            position: relative;
          }
          .ft-pdf-audio-voice-trigger {
            width: 100%;
            min-height: 62px;
            padding: 10px 12px;
            border: 1px solid rgba(126, 255, 232, 0.28);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(6, 16, 28, 0.98), rgba(13, 27, 44, 0.94)),
              radial-gradient(circle at 84% 18%, rgba(255, 214, 118, 0.14), transparent 32%);
            color: #efffff;
            text-align: left;
            cursor: pointer;
            display: grid;
            align-content: center;
            gap: 4px;
            box-shadow: inset 0 0 16px rgba(70, 240, 215, 0.06), 0 8px 24px rgba(0, 0, 0, 0.18);
          }
          .ft-pdf-audio-voice-trigger span {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 13px;
            font-weight: 900;
          }
          .ft-pdf-audio-voice-trigger small {
            color: rgba(168, 255, 241, 0.72);
            font-size: 10px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-audio-voice-trigger:hover,
          .ft-pdf-audio-voice-trigger:focus-visible {
            outline: none;
            border-color: rgba(255, 214, 118, 0.86);
            box-shadow:
              0 0 0 2px rgba(255, 214, 118, 0.12),
              0 0 20px rgba(255, 214, 118, 0.14),
              inset 0 0 18px rgba(70, 240, 215, 0.08);
          }
          .ft-pdf-audio-voice-list {
            position: absolute;
            left: 0;
            right: 0;
            top: calc(100% + 8px);
            z-index: 6;
            display: grid;
            gap: 6px;
            max-height: 250px;
            padding: 10px;
            overflow: auto;
            border: 1px solid rgba(126, 255, 232, 0.34);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(6, 14, 25, 0.98), rgba(10, 22, 36, 0.96)),
              radial-gradient(circle at 18% 16%, rgba(255, 214, 118, 0.12), transparent 28%);
            box-shadow: 0 20px 52px rgba(0, 0, 0, 0.42), inset 0 0 22px rgba(70, 240, 215, 0.06);
          }
          .ft-pdf-audio-voice-list.is-hidden {
            display: none;
          }
          .ft-pdf-audio-voice-option {
            width: 100%;
            min-height: 42px;
            padding: 8px 10px;
            border: 1px solid rgba(126, 255, 232, 0.16);
            border-radius: 11px;
            background: rgba(255, 255, 255, 0.03);
            color: #efffff;
            cursor: pointer;
            display: grid;
            gap: 3px;
            text-align: left;
          }
          .ft-pdf-audio-voice-option:hover,
          .ft-pdf-audio-voice-option.is-active {
            border-color: rgba(255, 214, 118, 0.82);
            background:
              radial-gradient(circle at 24% 24%, rgba(255, 214, 118, 0.16), transparent 40%),
              linear-gradient(135deg, rgba(255, 174, 64, 0.1), rgba(70, 240, 215, 0.07)),
              rgba(8, 18, 29, 0.96);
          }
          .ft-pdf-audio-voice-name {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 12px;
            font-weight: 900;
          }
          .ft-pdf-audio-voice-meta {
            color: rgba(168, 255, 241, 0.68);
            font-size: 10px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-audio-mic {
            min-width: 108px;
            min-height: 62px;
            padding: 8px 12px;
            border: 1px solid rgba(104, 243, 226, 0.32);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(8, 20, 33, 0.96), rgba(15, 29, 45, 0.92)),
              radial-gradient(circle at 20% 20%, rgba(104, 243, 226, 0.12), transparent 36%);
            color: #dbfff7;
            font-weight: 950;
            cursor: pointer;
            box-shadow: inset 0 0 16px rgba(70, 240, 215, 0.08), 0 8px 22px rgba(0, 0, 0, 0.22);
          }
          .ft-pdf-audio-mic.is-recording {
            border-color: rgba(255, 214, 118, 0.92);
            color: #fff4c7;
            background:
              radial-gradient(circle at 22% 22%, rgba(255, 214, 118, 0.18), transparent 36%),
              linear-gradient(135deg, rgba(30, 22, 10, 0.98), rgba(10, 28, 28, 0.94));
            box-shadow:
              0 0 22px rgba(255, 214, 118, 0.18),
              inset 0 0 16px rgba(255, 214, 118, 0.08);
            animation: ftPdfAudioMicPulse 1s ease-in-out infinite;
          }
          .ft-pdf-audio-mic.is-busy {
            opacity: 0.8;
          }
          .ft-pdf-audio-popover-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
          }
          .ft-pdf-audio-popover-actions button {
            min-height: 36px;
            padding: 0 12px;
            border: 1px solid rgba(126, 255, 232, 0.28);
            border-radius: 12px;
            background:
              linear-gradient(135deg, rgba(11, 26, 42, 0.96), rgba(18, 33, 49, 0.9));
            color: #efffff;
            font-weight: 900;
            cursor: pointer;
          }
          .ft-pdf-audio-popover-actions button:hover,
          .ft-pdf-audio-popover-actions button:focus-visible {
            outline: none;
            border-color: rgba(255, 214, 118, 0.86);
            box-shadow: 0 0 18px rgba(255, 214, 118, 0.14);
          }
          .ft-pdf-audio-popover-actions button.is-danger {
            border-color: rgba(255, 97, 116, 0.38);
            color: #ffd1d8;
            background:
              linear-gradient(135deg, rgba(52, 12, 20, 0.96), rgba(39, 15, 27, 0.92));
          }
          .ft-pdf-audio-popover-actions button.is-link-action {
            border-color: rgba(104, 243, 226, 0.34);
          }
          .ft-pdf-audio-popover-actions button.is-local-server {
            border-color: rgba(255, 196, 98, 0.42);
            color: #ffe7b0;
            background: linear-gradient(135deg, rgba(42, 30, 10, 0.96), rgba(28, 28, 16, 0.92));
            flex: 1 1 100%;
          }
          .ft-pdf-audio-popover-actions button.is-local-server.is-active {
            border-color: rgba(255, 214, 118, 0.95);
            color: #fff6d8;
            box-shadow: 0 0 16px rgba(255, 214, 118, 0.22), inset 0 0 12px rgba(255, 214, 118, 0.12);
            background: linear-gradient(135deg, rgba(58, 42, 14, 0.98), rgba(40, 32, 14, 0.94));
          }
          .ft-pdf-audio-popover-status {
            min-height: 40px;
            padding: 10px 12px;
            border: 1px solid rgba(126, 255, 232, 0.2);
            border-radius: 12px;
            display: flex;
            align-items: center;
            color: rgba(224, 255, 249, 0.9);
            background:
              linear-gradient(135deg, rgba(255, 255, 255, 0.04), rgba(70, 240, 215, 0.03)),
              rgba(4, 14, 23, 0.76);
          }
          .ft-pdf-audio-popover-status.is-error {
            border-color: rgba(255, 97, 116, 0.44);
            color: #ffd3db;
            background:
              linear-gradient(135deg, rgba(255, 97, 116, 0.14), rgba(27, 8, 13, 0.82)),
              rgba(4, 14, 23, 0.76);
          }
          .ft-pdf-audio-popover-status.is-busy {
            border-color: rgba(255, 214, 118, 0.52);
            color: #fff2c8;
            background:
              linear-gradient(135deg, rgba(255, 214, 118, 0.12), rgba(70, 240, 215, 0.06)),
              rgba(4, 14, 23, 0.78);
          }
          @keyframes ftPdfAudioWavePulse {
            0%, 100% { transform: scaleY(0.38); opacity: 0.45; }
            50% { transform: scaleY(1.45); opacity: 1; }
          }
          @keyframes ftPdfAudioMicPulse {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-1px); }
          }
          @keyframes ftPdfAudioConnectorFlow {
            0% { stroke-dashoffset: 0; }
            100% { stroke-dashoffset: -34; }
          }
          @keyframes ftPdfAudioConnectorNode {
            0%, 100% { transform: translate(-50%, -50%) scale(0.92); opacity: 0.82; }
            50% { transform: translate(-50%, -50%) scale(1.08); opacity: 1; }
          }
          .ft-pdf-pen-popover {
            position: fixed;
            top: 78px;
            left: 50%;
            z-index: 2147483200;
            display: grid;
            grid-template-columns: repeat(6, 28px);
            align-items: center;
            gap: 9px;
            padding: 10px 12px;
            border: 1px solid rgba(126, 255, 232, 0.35);
            border-radius: 12px;
            background:
              linear-gradient(135deg, rgba(9, 18, 31, 0.96), rgba(18, 25, 28, 0.94)),
              radial-gradient(circle at 18% 0%, rgba(255, 209, 102, 0.2), transparent 38%);
            box-shadow:
              0 20px 52px rgba(0, 0, 0, 0.44),
              inset 0 0 0 1px rgba(255, 255, 255, 0.04);
            opacity: 0;
            pointer-events: none;
            transform: translate(-50%, -8px) scale(0.96);
            transition: opacity 0.16s ease, transform 0.16s ease;
          }
          .ft-pdf-pen-popover.is-visible {
            opacity: 1;
            pointer-events: auto;
            transform: translate(0, 0) scale(1);
          }
          .ft-pdf-pen-color {
            width: 28px;
            height: 28px;
            border: 1px solid rgba(255, 255, 255, 0.36);
            border-radius: 50%;
            background: var(--pen-color, #ffd166);
            cursor: pointer;
            box-shadow: 0 0 16px color-mix(in srgb, var(--pen-color, #ffd166) 42%, transparent);
          }
          .ft-pdf-pen-color.is-active {
            outline: 2px solid rgba(255, 255, 255, 0.88);
            outline-offset: 2px;
          }
          .ft-pdf-pen-clear {
            grid-column: 1 / -1;
            min-height: 30px;
            padding: 0 11px;
            border: 1px solid rgba(255, 211, 126, 0.5);
            border-radius: 8px;
            background: rgba(255, 211, 126, 0.12);
            color: #ffe7ad;
            font: 800 11px/1 "Inter", sans-serif;
            cursor: pointer;
          }
          .ft-pdf-pen-clear:hover,
          .ft-pdf-pen-clear:focus-visible {
            outline: none;
            border-color: rgba(255, 211, 126, 0.86);
            box-shadow: 0 0 18px rgba(255, 190, 76, 0.2);
          }
          .ft-pdf-pen-size,
          .ft-pdf-eraser-size,
          .ft-pdf-text-size {
            grid-column: 1 / -1;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #dffdf6;
            font: 800 11px/1 "Inter", sans-serif;
          }
          .ft-pdf-pen-size input,
          .ft-pdf-eraser-size input,
          .ft-pdf-text-size input {
            width: 100%;
          }
          .ft-pdf-text-popover {
            position: fixed;
            top: 78px;
            left: 50%;
            z-index: 2147483200;
            display: grid;
            grid-template-columns: repeat(4, 30px);
            align-items: center;
            gap: 9px;
            padding: 10px 12px;
            border: 1px solid rgba(126, 255, 232, 0.35);
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(9, 18, 31, 0.96), rgba(18, 25, 28, 0.94));
            box-shadow: 0 20px 52px rgba(0, 0, 0, 0.44), inset 0 0 0 1px rgba(255, 255, 255, 0.04);
            opacity: 0;
            pointer-events: none;
            transform: translate(0, -8px) scale(0.96);
            transition: opacity 0.16s ease, transform 0.16s ease;
          }
          .ft-pdf-eraser-popover {
            position: fixed;
            top: 78px;
            left: 50%;
            z-index: 2147483200;
            display: grid;
            grid-template-columns: 180px;
            gap: 9px;
            padding: 10px 12px;
            border: 1px solid rgba(255, 132, 162, 0.45);
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(20, 8, 18, 0.96), rgba(18, 25, 28, 0.94));
            box-shadow: 0 20px 52px rgba(0, 0, 0, 0.44), inset 0 0 0 1px rgba(255, 255, 255, 0.04);
            opacity: 0;
            pointer-events: none;
            transform: translate(0, -8px) scale(0.96);
            transition: opacity 0.16s ease, transform 0.16s ease;
          }
          .ft-pdf-eraser-popover.is-visible {
            opacity: 1;
            pointer-events: auto;
            transform: translate(0, 0) scale(1);
          }
          .ft-pdf-eraser-size {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #ffe6ef;
            font: 800 11px/1 "Inter", sans-serif;
          }
          .ft-pdf-text-popover.is-visible {
            opacity: 1;
            pointer-events: auto;
            transform: translate(0, 0) scale(1);
          }
          .ft-pdf-pin-popover {
            position: fixed;
            top: 78px;
            left: 50%;
            z-index: 2147483200;
            display: grid;
            grid-template-columns: repeat(2, minmax(128px, 1fr));
            gap: 10px;
            width: min(340px, calc(100vw - 24px));
            padding: 10px;
            border: 1px solid rgba(70, 240, 215, 0.42);
            border-radius: 12px;
            background:
              radial-gradient(circle at 18% 0%, rgba(70, 240, 215, 0.16), transparent 38%),
              linear-gradient(135deg, rgba(8, 18, 30, 0.97), rgba(16, 24, 30, 0.95));
            box-shadow: 0 20px 52px rgba(0,0,0,0.48), inset 0 0 0 1px rgba(255,255,255,0.04);
            opacity: 0;
            pointer-events: none;
            transform: translate(0, -8px) scale(0.96);
            transition: opacity 0.16s ease, transform 0.16s ease;
          }
          .ft-pdf-pin-popover.is-visible {
            opacity: 1;
            pointer-events: auto;
            transform: translate(0, 0) scale(1);
          }
          .ft-pdf-pin-preview {
            min-height: 96px;
            padding: 7px;
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 10px;
            background: rgba(4, 12, 20, 0.76);
            color: #eafffb;
            display: grid;
            grid-template-rows: 72px auto;
            gap: 6px;
            cursor: pointer;
            text-align: left;
          }
          .ft-pdf-pin-preview.is-active {
            border-color: rgba(255, 209, 102, 0.9);
            box-shadow: 0 0 18px rgba(255, 209, 102, 0.24), inset 0 0 18px rgba(70, 240, 215, 0.12);
          }
          .ft-pdf-pin-preview img {
            width: 100%;
            height: 72px;
            object-fit: contain;
            border-radius: 7px;
            background: rgba(255,255,255,0.06);
          }
          .ft-pdf-pin-preview span,
          .ft-pdf-pin-empty {
            color: #dffdf6;
            font: 800 11px/1.2 "Inter", sans-serif;
          }
          .ft-pdf-pin-empty {
            grid-column: 1 / -1;
            padding: 12px;
            border-radius: 10px;
            background: rgba(70, 240, 215, 0.08);
            text-align: center;
          }
          .ft-pdf-local-image-popover {
            position: fixed;
            top: 82px;
            left: 50%;
            z-index: 2147483201;
            width: min(420px, calc(100vw - 24px));
            padding: 12px;
            border: 1px solid rgba(126, 255, 232, 0.34);
            border-radius: 14px;
            background:
              radial-gradient(circle at 16% 0%, rgba(255, 209, 102, 0.18), transparent 34%),
              radial-gradient(circle at 92% 18%, rgba(70, 240, 215, 0.18), transparent 38%),
              linear-gradient(135deg, rgba(6, 14, 25, 0.98), rgba(13, 24, 37, 0.96));
            box-shadow: 0 24px 64px rgba(0,0,0,0.52), inset 0 0 0 1px rgba(255,255,255,0.045);
            opacity: 0;
            pointer-events: none;
            transform: translate(0, -8px) scale(0.96);
            transition: opacity 0.16s ease, transform 0.16s ease;
          }
          .ft-pdf-local-image-popover.is-visible {
            opacity: 1;
            pointer-events: auto;
            transform: translate(0, 0) scale(1);
          }
          .ft-pdf-local-image-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 10px;
            color: #f3fffc;
            font: 900 12px/1.1 "Inter", sans-serif;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .ft-pdf-local-return {
            min-height: 30px;
            padding: 0 12px;
            border: 1px solid rgba(255, 209, 102, 0.5);
            border-radius: 9px;
            background: rgba(255, 209, 102, 0.12);
            color: #fff8df;
            font: 900 11px/1 "Inter", sans-serif;
            cursor: pointer;
          }
          .ft-pdf-local-image-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }
          .ft-pdf-local-image-slot {
            min-height: 118px;
            display: grid;
            grid-template-rows: 88px auto;
            gap: 7px;
            padding: 7px;
            border: 1px solid rgba(255,255,255,0.16);
            border-radius: 12px;
            background: rgba(4, 12, 22, 0.78);
            color: #eafffb;
            cursor: pointer;
            text-align: left;
            overflow: hidden;
          }
          .ft-pdf-local-image-slot:hover,
          .ft-pdf-local-image-slot.is-active {
            border-color: rgba(70, 240, 215, 0.82);
            box-shadow: 0 0 22px rgba(70, 240, 215, 0.2), inset 0 0 18px rgba(70, 240, 215, 0.1);
          }
          .ft-pdf-local-image-slot img {
            width: 100%;
            height: 88px;
            object-fit: contain;
            border-radius: 8px;
            background:
              linear-gradient(45deg, rgba(255,255,255,0.055) 25%, transparent 25% 50%, rgba(255,255,255,0.055) 50% 75%, transparent 75%) 0 0 / 16px 16px,
              rgba(255,255,255,0.04);
          }
          .ft-pdf-local-image-slot.is-empty {
            place-items: center;
            text-align: center;
            border-style: dashed;
            color: rgba(236, 255, 253, 0.72);
          }
          .ft-pdf-local-empty-mark {
            display: grid;
            place-items: center;
            width: 52px;
            height: 52px;
            border-radius: 12px;
            border: 1px solid rgba(70, 240, 215, 0.35);
            background: rgba(70, 240, 215, 0.08);
            font: 900 28px/1 "Inter", sans-serif;
          }
          .ft-pdf-local-slot-label,
          .ft-pdf-local-image-help {
            color: rgba(225, 255, 249, 0.78);
            font: 800 11px/1.25 "Inter", sans-serif;
          }
          .ft-pdf-local-image-help {
            margin-top: 10px;
            color: rgba(255, 244, 210, 0.78);
          }
          .ft-pdf-pinned-region-float {
            position: fixed;
            right: 28px;
            top: 88px;
            z-index: 2147483100;
            width: min(420px, calc(100vw - 28px));
            max-height: min(72vh, 620px);
            display: grid;
            grid-template-rows: auto minmax(80px, 1fr);
            border: 1px solid rgba(70, 240, 215, 0.52);
            border-radius: 14px;
            background:
              radial-gradient(circle at 20% 0%, rgba(255, 209, 102, 0.18), transparent 38%),
              linear-gradient(135deg, rgba(5, 14, 24, 0.97), rgba(15, 24, 32, 0.94));
            box-shadow:
              0 26px 70px rgba(0,0,0,0.54),
              0 0 34px rgba(70, 240, 215, 0.18),
              inset 0 0 0 1px rgba(255,255,255,0.05);
            overflow: hidden;
            opacity: 1;
            transform: translateY(0) scale(1);
            transition: opacity 0.16s ease, transform 0.16s ease;
          }
          .ft-pdf-pinned-region-float.is-hidden {
            opacity: 0;
            pointer-events: none;
            transform: translateY(-10px) scale(0.96);
          }
          .ft-pdf-pinned-region-float.is-dragging {
            cursor: grabbing;
            transition: none;
          }
          .ft-pdf-pinned-region-float.is-resizing {
            cursor: nwse-resize;
            transition: none;
          }
          .ft-pdf-pinned-region-head {
            min-height: 38px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            padding: 8px 10px;
            color: #eafffb;
            font: 900 12px/1 "Inter", sans-serif;
            background: linear-gradient(90deg, rgba(70,240,215,0.16), rgba(255,209,102,0.12));
            cursor: grab;
            user-select: none;
          }
          .ft-pdf-pinned-region-head button {
            width: 26px;
            height: 26px;
            border: 1px solid rgba(255, 209, 102, 0.52);
            border-radius: 8px;
            background: rgba(255, 209, 102, 0.1);
            color: #fff2c8;
            font-weight: 900;
            cursor: pointer;
          }
          .ft-pdf-pinned-region-float img {
            display: block;
            width: 100%;
            height: auto;
            max-height: calc(min(72vh, 620px) - 38px);
            object-fit: contain;
            background: rgba(255,255,255,0.04);
          }
          .ft-pdf-pinned-region-resize {
            position: absolute;
            right: 0;
            bottom: 0;
            width: 22px;
            height: 22px;
            cursor: nwse-resize;
            border-top-left-radius: 12px;
            background:
              linear-gradient(135deg, transparent 0 42%, rgba(70,240,215,0.95) 43% 50%, transparent 51%),
              linear-gradient(135deg, transparent 0 61%, rgba(255,209,102,0.92) 62% 69%, transparent 70%),
              rgba(5, 14, 24, 0.58);
            box-shadow: -4px -4px 14px rgba(70, 240, 215, 0.16);
            z-index: 2;
          }
          .ft-pdf-pinned-region-resize:hover {
            background:
              linear-gradient(135deg, transparent 0 38%, rgba(70,240,215,1) 39% 48%, transparent 49%),
              linear-gradient(135deg, transparent 0 58%, rgba(255,209,102,1) 59% 68%, transparent 69%),
              rgba(70, 240, 215, 0.12);
          }
          .ft-pdf-text-color {
            width: 30px;
            height: 30px;
            border: 1px solid rgba(255, 255, 255, 0.36);
            border-radius: 50%;
            background: var(--text-color, #fff);
            cursor: pointer;
          }
          .ft-pdf-text-color.is-active {
            outline: 2px solid rgba(255, 255, 255, 0.88);
            outline-offset: 2px;
          }
          .ft-pdf-text-font {
            grid-column: 1 / -1;
            min-height: 32px;
            border-radius: 8px;
            border: 1px solid rgba(126, 255, 232, 0.28);
            background: rgba(4, 12, 20, 0.94);
            color: #eafffb;
            font-weight: 800;
          }
          .ft-pdf-text-style {
            min-height: 30px;
            border: 1px solid rgba(126, 255, 232, 0.34);
            border-radius: 8px;
            background: rgba(126, 255, 232, 0.1);
            color: #eafffb;
            font: 900 13px/1 "Inter", sans-serif;
            cursor: pointer;
          }
          .ft-pdf-text-style.is-active {
            border-color: rgba(255, 211, 126, 0.86);
            background: rgba(255, 211, 126, 0.2);
            color: #ffe7ad;
          }
          .ft-pdf-text-draft {
            position: absolute;
            display: block;
            z-index: 8;
            min-width: 20px;
            min-height: 42px;
            border: 0;
            background: transparent;
            box-shadow: none;
            overflow: visible;
            user-select: none;
          }
          .ft-pdf-text-draft-body {
            min-width: 20px;
            min-height: 28px;
            box-sizing: border-box;
            padding: 0;
            border: 1px solid rgba(126, 255, 232, 0.72);
            border-radius: 8px;
            background: rgba(6, 14, 24, 0.52);
            box-shadow: 0 12px 30px rgba(0,0,0,0.32), 0 0 18px rgba(70,240,215,0.18);
            outline: none;
            white-space: pre-wrap;
            line-height: 1.16;
            overflow: auto;
            cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='24' viewBox='0 0 18 24'%3E%3Cpath d='M9 3v18M5 3h8M5 21h8' stroke='%23ffd166' stroke-width='2.2' stroke-linecap='round'/%3E%3Cpath d='M9 3v18M5 3h8M5 21h8' stroke='%23000' stroke-width='4.2' stroke-linecap='round' opacity='.42'/%3E%3Cpath d='M9 3v18M5 3h8M5 21h8' stroke='%23ffd166' stroke-width='2.2' stroke-linecap='round'/%3E%3C/svg%3E") 9 12, text;
            caret-color: #ffd166;
            text-shadow: 0 1px 2px rgba(0,0,0,0.72), 0 0 1px rgba(255,255,255,0.35);
            user-select: text;
            -webkit-user-select: text;
            touch-action: auto;
          }
          .ft-pdf-text-draft-control {
            position: absolute;
            bottom: -38px;
            width: 30px;
            height: 30px;
            border: 1px solid rgba(126,255,232,0.5);
            border-radius: 10px;
            background:
              radial-gradient(circle at 30% 24%, rgba(255,255,255,0.18), transparent 38%),
              linear-gradient(145deg, rgba(17, 34, 51, 0.96), rgba(5, 13, 24, 0.94));
            box-shadow: 0 12px 26px rgba(0,0,0,0.32), inset 0 0 0 1px rgba(255,255,255,0.08);
            backdrop-filter: blur(10px);
            transform: translateX(-50%);
            user-select: none;
            touch-action: none;
          }
          .ft-pdf-text-draft-control::before,
          .ft-pdf-text-draft-control::after {
            content: "";
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
          }
          .ft-pdf-text-draft-control:hover,
          .ft-pdf-text-draft-control:focus-visible {
            outline: none;
            border-color: rgba(255,211,126,0.74);
            transform: translateX(-50%) translateY(-1px);
            box-shadow: 0 14px 30px rgba(0,0,0,0.36), 0 0 0 2px rgba(255,211,126,0.18), inset 0 0 0 1px rgba(255,255,255,0.12);
          }
          .ft-pdf-text-draft-resize {
            left: calc(50% - 34px);
            cursor: nesw-resize;
          }
          .ft-pdf-text-draft-resize:hover,
          .ft-pdf-text-draft-resize:focus-visible {
            transform: translateX(-50%) translateY(-1px);
          }
          .ft-pdf-text-draft-resize::before {
            width: 14px;
            height: 14px;
            border-left: 2px solid rgba(126,255,232,0.95);
            border-bottom: 2px solid rgba(126,255,232,0.95);
            border-radius: 0 0 0 4px;
          }
          .ft-pdf-text-draft-resize::after {
            width: 8px;
            height: 2px;
            background: rgba(255,211,126,0.95);
            box-shadow: 0 -5px 0 rgba(255,211,126,0.78);
            transform: translate(-20%, -15%) rotate(-45deg);
          }
          .ft-pdf-text-draft-move {
            left: 50%;
            cursor: move;
          }
          .ft-pdf-text-draft-move:hover,
          .ft-pdf-text-draft-move:focus-visible {
            transform: translateX(-50%) translateY(-1px);
          }
          .ft-pdf-text-draft-move::before {
            width: 17px;
            height: 17px;
            border-left: 2px solid rgba(126,255,232,0.95);
            border-right: 2px solid rgba(126,255,232,0.95);
            border-top: 2px solid rgba(255,211,126,0.9);
            border-bottom: 2px solid rgba(255,211,126,0.9);
            border-radius: 6px;
          }
          .ft-pdf-text-draft-move::after {
            width: 3px;
            height: 3px;
            border-radius: 50%;
            background: rgba(255,255,255,0.92);
            box-shadow:
              -7px 0 0 rgba(255,255,255,0.72),
              7px 0 0 rgba(255,255,255,0.72),
              0 -7px 0 rgba(255,255,255,0.72),
              0 7px 0 rgba(255,255,255,0.72);
          }
          .ft-pdf-text-draft-box-resize {
            left: calc(50% + 34px);
            cursor: nwse-resize;
          }
          .ft-pdf-text-draft-box-resize::before {
            width: 15px;
            height: 15px;
            border-right: 2px solid rgba(126,255,232,0.95);
            border-bottom: 2px solid rgba(126,255,232,0.95);
            border-radius: 0 0 4px 0;
          }
          .ft-pdf-text-draft-box-resize::after {
            width: 7px;
            height: 7px;
            border-right: 2px solid rgba(255,255,255,0.86);
            border-bottom: 2px solid rgba(255,255,255,0.86);
            transform: translate(-80%, -20%);
          }
          .ft-pdf-text-draft-submit {
            left: 50%;
            bottom: -74px;
            transform: translateX(-50%);
            cursor: pointer;
            border-color: rgba(48,209,88,0.64);
            background:
              radial-gradient(circle at 30% 24%, rgba(255,255,255,0.2), transparent 38%),
              linear-gradient(145deg, rgba(24, 76, 45, 0.96), rgba(5, 26, 17, 0.94));
          }
          .ft-pdf-text-draft-submit:hover,
          .ft-pdf-text-draft-submit:focus-visible {
            transform: translateX(-50%) translateY(-1px);
            border-color: rgba(168,255,94,0.82);
          }
          .ft-pdf-text-draft-submit::before {
            width: 9px;
            height: 5px;
            border-left: 2px solid rgba(255,255,255,0.95);
            border-bottom: 2px solid rgba(255,255,255,0.95);
            transform: translate(-50%, -58%) rotate(-45deg);
          }
          .ft-pdf-text-draft-submit::after {
            width: 12px;
            height: 12px;
            border: 1px solid rgba(168,255,94,0.6);
            border-radius: 5px;
          }
          .ft-pdf-text-selection-popover {
            position: fixed;
            z-index: 10050;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 10px;
            border: 1px solid rgba(126,255,232,0.4);
            border-radius: 12px;
            background: rgba(7, 13, 24, 0.94);
            box-shadow: 0 18px 44px rgba(0,0,0,0.34), 0 0 22px rgba(70,240,215,0.16);
            backdrop-filter: blur(14px);
          }
          .ft-pdf-text-selection-section {
            display: grid;
            gap: 7px;
          }
          .ft-pdf-text-selection-section + .ft-pdf-text-selection-section {
            padding-top: 10px;
            border-top: 1px solid rgba(126,255,232,0.22);
          }
          .ft-pdf-text-selection-label {
            color: rgba(223,253,246,0.82);
            font: 800 10px/1 "Inter", sans-serif;
            letter-spacing: 0;
            text-transform: uppercase;
          }
          .ft-pdf-text-selection-grid {
            display: grid;
            grid-template-columns: repeat(6, 22px);
            gap: 8px;
          }
          .ft-pdf-text-selection-color {
            width: 22px;
            height: 22px;
            border: 1px solid rgba(255,255,255,0.34);
            border-radius: 7px;
            background: var(--pdf-text-selection-color, #ffffff);
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.18), 0 8px 18px rgba(0,0,0,0.22);
            cursor: pointer;
          }
          .ft-pdf-text-selection-color.is-active {
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.2), 0 0 0 2px rgba(255,211,126,0.76), 0 8px 18px rgba(0,0,0,0.24);
          }
          .ft-pdf-text-selection-color.is-disabled,
          .ft-pdf-text-selection-color:disabled {
            opacity: 0.34;
            cursor: not-allowed;
            filter: grayscale(0.45);
          }
          .ft-pdf-text-selection-color:hover,
          .ft-pdf-text-selection-color:focus-visible {
            outline: none;
            transform: translateY(-1px) scale(1.06);
            box-shadow: inset 0 0 0 1px rgba(0,0,0,0.2), 0 0 0 2px rgba(126,255,232,0.5), 0 10px 22px rgba(0,0,0,0.28);
          }
          .ft-pdf-selection {
            position: absolute;
            display: none;
            z-index: 7;
            border: 2px solid rgba(255, 176, 62, 0.96);
            border-radius: 12px;
            background: transparent;
            box-shadow:
              0 0 0 1px rgba(0, 0, 0, 0.92),
              0 0 0 4px rgba(0, 0, 0, 0.38),
              0 0 0 6px rgba(255, 176, 62, 0.24),
              0 8px 28px rgba(0, 0, 0, 0.46),
              0 0 24px rgba(255, 147, 40, 0.42),
              inset 0 0 10px rgba(255, 181, 72, 0.08);
            pointer-events: none;
            overflow: visible;
          }
          .ft-pdf-selection.is-visible {
            display: block;
            pointer-events: auto;
            cursor: pointer;
            animation: none;
          }
          .ft-pdf-space.is-pen-active .ft-pdf-selection.is-visible,
          .ft-pdf-space.is-text-active .ft-pdf-selection.is-visible,
          .ft-pdf-space.is-eraser-active .ft-pdf-selection.is-visible,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-selection.is-visible,
          .ft-pdf-space.is-pen-active .ft-pdf-selection.is-visible::before,
          .ft-pdf-space.is-text-active .ft-pdf-selection.is-visible::before,
          .ft-pdf-space.is-eraser-active .ft-pdf-selection.is-visible::before,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-selection.is-visible::before,
          .ft-pdf-space.is-pen-active .ft-pdf-selection.is-visible::after,
          .ft-pdf-space.is-text-active .ft-pdf-selection.is-visible::after,
          .ft-pdf-space.is-eraser-active .ft-pdf-selection.is-visible::after,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-selection.is-visible::after {
            pointer-events: none !important;
          }
          .ft-pdf-selection.is-visible.ft-pdf-selection-extra {
            pointer-events: auto;
            opacity: 0.82;
            filter: saturate(0.92) brightness(0.96);
          }
          .ft-pdf-selection.is-visible.is-hitbox-only:not(.is-twin-building):not(.is-tech-burst):not(.is-materializing) {
            border-color: transparent;
            background: transparent;
            box-shadow: none;
            filter: none;
            opacity: 1;
          }
          .ft-pdf-selection.is-visible.is-hitbox-only:not(.is-twin-building):not(.is-tech-burst):not(.is-materializing)::before,
          .ft-pdf-selection.is-visible.is-hitbox-only:not(.is-twin-building):not(.is-tech-burst):not(.is-materializing)::after {
            display: none;
          }
          .ft-pdf-selection-svg {
            position: absolute;
            left: 0;
            top: 0;
            z-index: 5;
            pointer-events: none;
            overflow: visible;
          }
          .ft-pdf-selection-svg path {
            fill: none;
            vector-effect: non-scaling-stroke;
            stroke-linejoin: round;
            stroke-linecap: round;
            stroke-miterlimit: 2;
          }
          .ft-pdf-selection-svg .is-fill {
            fill: rgba(255, 170, 54, 0.035);
            stroke: none;
            filter: drop-shadow(0 0 18px rgba(72, 255, 232, 0.08));
          }
          .ft-pdf-selection-svg .is-shadow {
            stroke: rgba(0, 0, 0, 0.9);
            stroke-width: 10;
            opacity: 0.82;
            filter:
              drop-shadow(0 6px 12px rgba(0, 0, 0, 0.28))
              drop-shadow(0 0 5px rgba(0, 0, 0, 0.55));
          }
          .ft-pdf-selection-svg .is-glow {
            stroke: rgba(255, 168, 46, 0.54);
            stroke-width: 9;
            filter:
              drop-shadow(0 0 10px rgba(255, 146, 42, 0.52))
              drop-shadow(0 0 18px rgba(69, 255, 232, 0.18));
          }
          .ft-pdf-selection-svg .is-rail {
            stroke: rgba(12, 22, 24, 0.92);
            stroke-width: 4.4;
            filter:
              drop-shadow(0 0 1px rgba(0, 0, 0, 0.96))
              drop-shadow(0 0 7px rgba(255, 151, 42, 0.18));
          }
          .ft-pdf-selection-svg .is-main {
            stroke: rgba(255, 188, 82, 0.98);
            stroke-width: 2.35;
            filter:
              drop-shadow(0 0 1px rgba(0, 0, 0, 0.95))
              drop-shadow(0 0 8px rgba(255, 146, 42, 0.62));
          }
          .ft-pdf-selection-svg .is-cyan {
            stroke: rgba(86, 255, 232, 0.62);
            stroke-width: 1.25;
            stroke-dasharray: 74 150;
            stroke-dashoffset: 34;
            filter: drop-shadow(0 0 8px rgba(94, 255, 232, 0.35));
          }
          .ft-pdf-selection-svg .is-trace {
            stroke: rgba(255, 247, 210, 0.98);
            stroke-width: 3.2;
            stroke-dasharray: 0 340;
            stroke-dashoffset: 0;
            filter:
              drop-shadow(0 0 6px rgba(255, 235, 180, 0.76))
              drop-shadow(0 0 12px rgba(255, 137, 42, 0.44));
            opacity: 0;
          }
          .ft-pdf-selection-svg.is-union-pulse .is-shadow {
            animation: ftPdfUnionShadowPulse 2.05s ease-in-out 1;
          }
          .ft-pdf-selection-svg.is-union-pulse .is-fill {
            animation: ftPdfUnionFillPulse 2.05s ease-in-out 1;
          }
          .ft-pdf-selection-svg.is-union-pulse .is-main {
            animation: ftPdfUnionHoloMain 2.05s ease-in-out 1;
          }
          .ft-pdf-selection-svg.is-union-pulse .is-glow {
            animation: ftPdfUnionGlowPulse 2.05s ease-in-out 1;
          }
          .ft-pdf-selection-svg.is-union-pulse .is-cyan {
            animation: ftPdfUnionCyanOrbit 2.05s linear 1;
          }
          .ft-pdf-selection-svg.is-union-pulse .is-trace {
            animation: ftPdfUnionElectronOrbit 2.05s linear 1;
          }
          @keyframes ftPdfUnionShadowPulse {
            0%, 100% {
              stroke-width: 10;
              opacity: 0.82;
              filter: none;
            }
            28%, 72% {
              stroke-width: 14;
              opacity: 0.95;
              filter:
                drop-shadow(0 10px 18px rgba(0, 0, 0, 0.42))
                drop-shadow(0 0 8px rgba(0, 0, 0, 0.72));
            }
          }
          @keyframes ftPdfUnionFillPulse {
            0%, 100% {
              fill: rgba(255, 170, 54, 0.035);
              filter: drop-shadow(0 0 18px rgba(72, 255, 232, 0.08));
            }
            32%, 64% {
              fill: rgba(255, 170, 54, 0.055);
              filter:
                drop-shadow(0 0 18px rgba(255, 166, 48, 0.14))
                drop-shadow(0 0 24px rgba(72, 255, 232, 0.12));
            }
          }
          @keyframes ftPdfUnionHoloMain {
            0%, 100% {
              filter:
                drop-shadow(0 0 1px rgba(0, 0, 0, 0.95))
                drop-shadow(0 0 8px rgba(255, 146, 42, 0.62));
              opacity: 1;
            }
            34%, 68% {
              filter:
                drop-shadow(0 0 1px rgba(0, 0, 0, 0.95))
                drop-shadow(0 0 12px rgba(255, 214, 125, 0.72))
                drop-shadow(0 0 18px rgba(86, 255, 232, 0.3));
              opacity: 1;
            }
          }
          @keyframes ftPdfUnionGlowPulse {
            0%, 100% {
              stroke-width: 8;
              opacity: 1;
              filter:
                drop-shadow(0 0 9px rgba(255, 146, 42, 0.5))
                drop-shadow(0 0 18px rgba(69, 255, 232, 0.22));
            }
            38%, 66% {
              stroke-width: 11;
              opacity: 1;
              filter:
                drop-shadow(0 0 13px rgba(255, 176, 66, 0.68))
                drop-shadow(0 0 24px rgba(69, 255, 232, 0.34));
            }
          }
          @keyframes ftPdfUnionCyanOrbit {
            0% { stroke-dasharray: 12 210; stroke-dashoffset: 42; opacity: 0; }
            8% { opacity: 0.86; }
            58% { stroke-dasharray: 92 118; stroke-dashoffset: -180; opacity: 0.72; }
            100% { stroke-dasharray: 18 220; stroke-dashoffset: -330; opacity: 0.36; }
          }
          @keyframes ftPdfUnionElectronOrbit {
            0% { stroke-dasharray: 0 340; stroke-dashoffset: 0; opacity: 0; }
            6% { stroke-dasharray: 34 210; opacity: 0.98; }
            42% { stroke-dasharray: 54 160; stroke-dashoffset: -220; opacity: 1; }
            76% { stroke-dasharray: 30 220; stroke-dashoffset: -420; opacity: 0.75; }
            100% { stroke-dasharray: 0 340; stroke-dashoffset: -560; opacity: 0; }
          }
          .ft-pdf-page-wrap.is-shift-selecting,
          .ft-pdf-page-wrap.is-shift-selecting * {
            cursor: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'%3E%3Cdefs%3E%3Cfilter id='g'%3E%3CfeGaussianBlur stdDeviation='1.1' result='b'/%3E%3CfeMerge%3E%3CfeMergeNode in='b'/%3E%3CfeMergeNode in='SourceGraphic'/%3E%3C/feMerge%3E%3C/filter%3E%3C/defs%3E%3Cpath d='M16 3v8M16 21v8M3 16h8M21 16h8' stroke='%2300ffe0' stroke-width='2.2' stroke-linecap='round' filter='url(%23g)'/%3E%3Ccircle cx='16' cy='16' r='8.5' fill='none' stroke='%23ff9d32' stroke-width='1.9'/%3E%3Cpath d='M16 10.5l2.5 3.8 4.4 1.2-3.6 2.8.2 4.6-3.5-2.6-4.3 1.6 1.4-4.4-2.9-3.5 4.6-.1z' fill='%23fff3c4' stroke='%23ff7a2a' stroke-width='.7'/%3E%3Ccircle cx='16' cy='16' r='2.1' fill='%23001416' stroke='%2300ffe0' stroke-width='1.2'/%3E%3C/svg%3E") 16 16, crosshair !important;
          }
          .ft-pdf-selection-point {
            position: absolute;
            left: 0;
            top: 0;
            width: 22px;
            height: 22px;
            display: none;
            border-radius: 50%;
            transform: translate(-50%, -50%) scale(0.72);
            pointer-events: none;
            z-index: 6;
            background:
              radial-gradient(circle at 50% 50%, rgba(255, 250, 220, 0.98) 0 12%, rgba(255, 178, 60, 0.95) 13% 26%, rgba(255, 94, 38, 0.8) 27% 40%, transparent 42%),
              conic-gradient(from 0deg, rgba(255, 210, 112, 0.98), rgba(85, 255, 232, 0.92), rgba(255, 107, 54, 0.98), rgba(255, 210, 112, 0.98));
            box-shadow:
              0 0 0 1px rgba(0, 0, 0, 0.82),
              0 0 0 5px rgba(0, 0, 0, 0.28),
              0 0 22px rgba(255, 149, 42, 0.72),
              0 0 38px rgba(95, 255, 231, 0.34);
            opacity: 0;
          }
          .ft-pdf-selection-point.is-visible {
            display: block;
            opacity: 1;
            animation: ftPdfSelectionPointLock 1.35s cubic-bezier(.2,.8,.22,1) infinite;
          }
          .ft-pdf-selection-point.is-visible::before,
          .ft-pdf-selection-point.is-visible::after {
            content: "";
            position: absolute;
            inset: -10px;
            border-radius: inherit;
            border: 1px solid rgba(255, 205, 117, 0.56);
            filter: drop-shadow(0 0 8px rgba(255, 154, 52, 0.45));
          }
          .ft-pdf-selection-point.is-visible::after {
            inset: -18px;
            border-color: rgba(101, 255, 233, 0.34);
            animation: ftPdfSelectionPointWave 1.35s ease-out infinite;
          }
          .ft-pdf-build-point {
            position: absolute;
            width: 42px;
            height: 42px;
            z-index: 9;
            pointer-events: none;
            border-radius: 50%;
            opacity: 0;
            transform: translate(-50%, -50%);
            border: 1px solid rgba(255, 202, 104, 0.74);
            background:
              radial-gradient(circle at 50% 50%, #fff8d7 0 8%, rgba(255, 191, 75, 0.96) 9% 16%, transparent 17%),
              radial-gradient(circle at 50% 50%, transparent 0 34%, rgba(255, 194, 86, 0.9) 35% 38%, transparent 39%),
              radial-gradient(circle at 50% 50%, transparent 0 52%, rgba(82, 255, 232, 0.62) 53% 56%, transparent 57%),
              linear-gradient(90deg, transparent 0 45%, rgba(82, 255, 232, 0.55) 46% 54%, transparent 55%),
              linear-gradient(0deg, transparent 0 45%, rgba(255, 157, 42, 0.5) 46% 54%, transparent 55%);
            box-shadow:
              0 0 0 1px rgba(0, 0, 0, 0.88),
              0 0 0 5px rgba(0, 0, 0, 0.22),
              0 0 24px rgba(255, 157, 42, 0.84),
              0 0 50px rgba(73, 255, 232, 0.42);
            animation: ftPdfBuildPointCore 0.82s cubic-bezier(.16,.86,.2,1) 1 forwards;
          }
          .ft-pdf-build-point::before,
          .ft-pdf-build-point::after {
            content: "";
            position: absolute;
            inset: -15px;
            border-radius: 50%;
            border: 1.5px dashed rgba(255, 198, 93, 0.78);
            box-shadow:
              0 0 0 4px rgba(0, 0, 0, 0.16),
              0 0 14px rgba(255, 150, 42, 0.46),
              inset 0 0 12px rgba(83, 255, 232, 0.15);
            animation: ftPdfBuildPointRing 0.82s ease-out 1 forwards;
          }
          .ft-pdf-build-point::after {
            inset: -27px;
            border-width: 1px;
            border-style: dotted;
            border-color: rgba(83, 255, 232, 0.52);
            background:
              radial-gradient(circle, transparent 0 62%, rgba(83, 255, 232, 0.1) 63% 66%, transparent 67%),
              linear-gradient(90deg, transparent 0 47%, rgba(255, 210, 112, 0.22) 48% 52%, transparent 53%),
              linear-gradient(0deg, transparent 0 47%, rgba(83, 255, 232, 0.2) 48% 52%, transparent 53%);
            animation: ftPdfBuildPointHalo 0.82s ease-out 1 forwards;
          }
          .ft-pdf-build-line {
            position: absolute;
            left: 0;
            top: 0;
            height: 3px;
            width: 0;
            z-index: 8;
            pointer-events: none;
            transform-origin: 0 50%;
            border-radius: 999px;
            background:
              linear-gradient(90deg, transparent 0%, rgba(255, 246, 214, 0.98) 18%, rgba(255, 166, 47, 0.95) 42%, rgba(74, 255, 232, 0.9) 72%, transparent 100%);
            box-shadow:
              0 0 0 1px rgba(0, 0, 0, 0.62),
              0 0 14px rgba(255, 160, 42, 0.56),
              0 0 26px rgba(74, 255, 232, 0.34);
            opacity: 0;
            animation: ftPdfBuildLineConnect 0.82s cubic-bezier(.16,.86,.2,1) 1 forwards;
          }
          .ft-pdf-build-line::before,
          .ft-pdf-build-line::after {
            content: "";
            position: absolute;
            inset: -5px 0;
            border-radius: inherit;
            background:
              linear-gradient(90deg, transparent, rgba(255, 195, 77, 0.26), rgba(72, 255, 232, 0.22), transparent);
            filter: blur(3px);
          }
          .ft-pdf-build-line::after {
            inset: -9px 0;
            filter: blur(8px);
            opacity: 0.62;
          }
          .ft-pdf-selection.is-visible::before,
          .ft-pdf-selection.is-visible::after {
            content: "";
            position: absolute;
            pointer-events: none;
          }
          .ft-pdf-selection.is-visible::before {
            inset: -7px;
            border-radius: 18px;
            background:
              linear-gradient(90deg, #ffe0a3, #ff8d32) left top / 64px 3px no-repeat,
              linear-gradient(180deg, #ffe0a3, #ff8d32) left top / 3px 64px no-repeat,
              linear-gradient(270deg, #61ffe7, #ffe0a3) right top / 64px 3px no-repeat,
              linear-gradient(180deg, #61ffe7, #ffe0a3) right top / 3px 64px no-repeat,
              linear-gradient(90deg, #61ffe7, #ffe0a3) left bottom / 64px 3px no-repeat,
              linear-gradient(0deg, #61ffe7, #ffe0a3) left bottom / 3px 64px no-repeat,
              linear-gradient(270deg, #ffe0a3, #ff8d32) right bottom / 64px 3px no-repeat,
              linear-gradient(0deg, #ffe0a3, #ff8d32) right bottom / 3px 64px no-repeat,
              linear-gradient(90deg, rgba(255, 176, 62, 0.95), transparent 42%) left 12px top / 42% 1px no-repeat,
              linear-gradient(90deg, transparent 58%, rgba(255, 214, 137, 0.82)) right 12px bottom / 42% 1px no-repeat;
            filter:
              drop-shadow(0 2px 5px rgba(0, 0, 0, 0.72))
              drop-shadow(0 0 10px rgba(255, 153, 42, 0.44));
            opacity: 0.96;
            transform: translateZ(0);
            animation: none;
          }
          .ft-pdf-selection.is-visible::after {
            content: "";
            inset: -4px;
            border-radius: 15px;
            background:
              linear-gradient(90deg, transparent, rgba(255, 246, 214, 0.95) 28%, rgba(255, 142, 42, 0.96) 48%, transparent 74%) top / 38% 3px no-repeat,
              linear-gradient(180deg, transparent, rgba(255, 246, 214, 0.95) 28%, rgba(255, 142, 42, 0.96) 48%, transparent 74%) right / 3px 38% no-repeat,
              linear-gradient(270deg, transparent, rgba(255, 246, 214, 0.95) 28%, rgba(255, 142, 42, 0.96) 48%, transparent 74%) bottom / 38% 3px no-repeat,
              linear-gradient(0deg, transparent, rgba(255, 246, 214, 0.95) 28%, rgba(255, 142, 42, 0.96) 48%, transparent 74%) left / 3px 38% no-repeat;
            opacity: 0;
            filter:
              drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65))
              drop-shadow(0 0 9px rgba(255, 153, 42, 0.48));
            animation: none;
          }
          .ft-pdf-selection.is-visible.is-materializing {
            animation: ftPdfSelectionQuantumLock 0.94s cubic-bezier(.17,.84,.24,1) 1 !important;
            background:
              radial-gradient(circle at 50% 50%, rgba(255, 182, 70, 0.08), transparent 58%),
              linear-gradient(135deg, rgba(28, 255, 231, 0.045), rgba(255, 151, 42, 0.04));
            transform-origin: center;
          }
          .ft-pdf-selection.is-visible.is-materializing::before {
            animation: ftPdfSelectionCornerTrace 0.94s cubic-bezier(.17,.84,.24,1) 1 !important;
          }
          .ft-pdf-selection.is-visible.is-materializing::after {
            animation: ftPdfSelectionElectronTrace 0.94s linear 1 !important;
          }
          .ft-pdf-selection.is-visible.is-twin-building {
            animation: ftPdfSelectionTwinLock 0.82s cubic-bezier(.16,.86,.2,1) 1 !important;
            background:
              radial-gradient(circle at 0 0, rgba(255, 188, 72, 0.13), transparent 36%),
              radial-gradient(circle at 100% 100%, rgba(79, 255, 232, 0.12), transparent 38%),
              linear-gradient(135deg, rgba(255, 138, 42, 0.035), rgba(65, 255, 232, 0.035));
          }
          .ft-pdf-selection.is-visible.is-twin-building::before {
            animation: ftPdfSelectionTwinRails 0.82s cubic-bezier(.16,.86,.2,1) 1 !important;
          }
          .ft-pdf-selection.is-visible.is-twin-building::after {
            animation: ftPdfSelectionTwinElectron 0.82s linear 1 !important;
          }
          @keyframes ftPdfBuildPointCore {
            0% { opacity: 0; transform: translate(-50%, -50%) scale(0.18) rotate(-80deg); filter: brightness(1.6) saturate(1.35); }
            14% { opacity: 1; transform: translate(-50%, -50%) scale(1.18) rotate(72deg); filter: brightness(1.45) saturate(1.26); }
            34% { opacity: 1; transform: translate(-50%, -50%) scale(0.88) rotate(210deg); filter: brightness(1.18) saturate(1.14); }
            58% { opacity: 0.72; transform: translate(-50%, -50%) scale(1.18) rotate(360deg); filter: brightness(1.22) saturate(1.16); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(0.08) rotate(520deg); filter: brightness(1); }
          }
          @keyframes ftPdfBuildPointRing {
            0% { opacity: 0; transform: scale(0.18) rotate(0deg); }
            18% { opacity: 0.98; }
            62% { opacity: 0.56; transform: scale(1.34) rotate(190deg); }
            100% { opacity: 0; transform: scale(1.86) rotate(300deg); }
          }
          @keyframes ftPdfBuildPointHalo {
            0% { opacity: 0; transform: scale(0.12) rotate(45deg); }
            14% { opacity: 0.78; }
            56% { opacity: 0.38; transform: scale(1.26) rotate(-160deg); }
            100% { opacity: 0; transform: scale(2.08) rotate(-320deg); }
          }
          @keyframes ftPdfBuildLineConnect {
            0% { opacity: 0; clip-path: inset(0 100% 0 0); filter: brightness(1.2); }
            16% { opacity: 0.92; clip-path: inset(0 72% 0 0); filter: brightness(1.45); }
            48% { opacity: 1; clip-path: inset(0 0 0 0); filter: brightness(1.28); }
            68% { opacity: 0.48; clip-path: inset(0 0 0 0); filter: brightness(1.08); }
            100% { opacity: 0; clip-path: inset(0 0 0 100%); filter: brightness(1); }
          }
          @keyframes ftPdfSelectionTwinLock {
            0% {
              opacity: 0.18;
              border-color: rgba(255, 191, 79, 0);
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.84),
                0 0 14px rgba(255, 165, 42, 0.16);
            }
            34% {
              opacity: 1;
              border-color: rgba(82, 255, 232, 0.95);
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.92),
                0 0 0 5px rgba(0, 0, 0, 0.38),
                0 0 0 8px rgba(82, 255, 232, 0.23),
                0 12px 34px rgba(0, 0, 0, 0.54),
                0 0 44px rgba(82, 255, 232, 0.52),
                inset 0 0 20px rgba(255, 180, 72, 0.1);
            }
            66% {
              border-color: rgba(255, 180, 64, 1);
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.92),
                0 0 0 4px rgba(0, 0, 0, 0.38),
                0 0 0 7px rgba(255, 176, 62, 0.28),
                0 10px 30px rgba(0, 0, 0, 0.48),
                0 0 38px rgba(255, 147, 40, 0.58),
                inset 0 0 18px rgba(82, 255, 232, 0.1);
            }
            100% {
              opacity: 1;
              border-color: rgba(255, 176, 62, 0.96);
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.92),
                0 0 0 4px rgba(0, 0, 0, 0.38),
                0 0 0 6px rgba(255, 176, 62, 0.24),
                0 8px 28px rgba(0, 0, 0, 0.46),
                0 0 24px rgba(255, 147, 40, 0.42),
                inset 0 0 10px rgba(255, 181, 72, 0.08);
            }
          }
          @keyframes ftPdfSelectionTwinRails {
            0% {
              opacity: 0;
              background-size:
                0 3px, 3px 0,
                0 3px, 3px 0,
                0 3px, 3px 0,
                0 3px, 3px 0,
                0 1px, 0 1px;
              filter: drop-shadow(0 0 2px rgba(255, 165, 42, 0.18));
            }
            18% {
              opacity: 1;
              background-size:
                38px 3px, 3px 38px,
                38px 3px, 3px 38px,
                38px 3px, 3px 38px,
                38px 3px, 3px 38px,
                18% 1px, 18% 1px;
            }
            50% {
              opacity: 1;
              background-size:
                74px 3px, 3px 74px,
                74px 3px, 3px 74px,
                74px 3px, 3px 74px,
                74px 3px, 3px 74px,
                52% 1px, 52% 1px;
              filter:
                drop-shadow(0 2px 5px rgba(0, 0, 0, 0.72))
                drop-shadow(0 0 18px rgba(255, 165, 42, 0.7));
            }
            100% {
              opacity: 0.96;
              background-size:
                64px 3px, 3px 64px,
                64px 3px, 3px 64px,
                64px 3px, 3px 64px,
                64px 3px, 3px 64px,
                42% 1px, 42% 1px;
            }
          }
          @keyframes ftPdfSelectionTwinElectron {
            0% {
              opacity: 0;
              background-size: 6% 3px, 3px 6%, 6% 3px, 3px 6%;
              background-position: left top, right top, right bottom, left bottom;
            }
            20% {
              opacity: 1;
              background-size: 24% 3px, 3px 24%, 24% 3px, 3px 24%;
            }
            54% {
              opacity: 1;
              background-size: 54% 3px, 3px 54%, 54% 3px, 3px 54%;
              background-position: right top, right bottom, left bottom, left top;
            }
            100% {
              opacity: 0;
              background-size: 18% 3px, 3px 18%, 18% 3px, 3px 18%;
              background-position: right top, right bottom, left bottom, left top;
            }
          }
          @keyframes ftPdfSelectionQuantumLock {
            0% {
              opacity: 0.18;
              border-color: rgba(79, 255, 232, 0.18);
              transform: scale(0.996);
              filter: brightness(1.28) saturate(1.2);
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.78),
                0 0 0 3px rgba(0, 0, 0, 0.24),
                0 0 16px rgba(84, 255, 229, 0.28),
                inset 0 0 20px rgba(84, 255, 229, 0.08);
            }
            22% {
              opacity: 1;
              border-color: rgba(91, 255, 234, 0.92);
              transform: scale(1.002);
              filter: brightness(1.34) saturate(1.28);
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.92),
                0 0 0 4px rgba(0, 0, 0, 0.36),
                0 0 0 7px rgba(83, 255, 232, 0.22),
                0 10px 30px rgba(0, 0, 0, 0.5),
                0 0 38px rgba(83, 255, 232, 0.48),
                inset 0 0 18px rgba(255, 181, 72, 0.12);
            }
            58% {
              border-color: rgba(255, 185, 71, 0.98);
              transform: scale(1.001);
              filter: brightness(1.16) saturate(1.12);
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.92),
                0 0 0 4px rgba(0, 0, 0, 0.38),
                0 0 0 7px rgba(255, 184, 66, 0.28),
                0 12px 32px rgba(0, 0, 0, 0.5),
                0 0 34px rgba(255, 148, 42, 0.54),
                inset 0 0 18px rgba(83, 255, 232, 0.1);
            }
            100% {
              opacity: 1;
              transform: scale(1);
              filter: none;
            }
          }
          @keyframes ftPdfSelectionCornerTrace {
            0% {
              opacity: 0;
              background-size:
                0 3px, 3px 0,
                0 3px, 3px 0,
                0 3px, 3px 0,
                0 3px, 3px 0,
                0 1px, 0 1px;
              filter: drop-shadow(0 0 2px rgba(87, 255, 233, 0.15));
            }
            38% {
              opacity: 1;
              background-size:
                64px 3px, 3px 64px,
                64px 3px, 3px 64px,
                64px 3px, 3px 64px,
                64px 3px, 3px 64px,
                42% 1px, 42% 1px;
              filter:
                drop-shadow(0 2px 5px rgba(0, 0, 0, 0.72))
                drop-shadow(0 0 16px rgba(90, 255, 233, 0.62));
            }
            100% {
              opacity: 0.96;
            }
          }
          @keyframes ftPdfSelectionElectronTrace {
            0% {
              opacity: 0;
              background-size: 8% 3px, 3px 8%, 8% 3px, 3px 8%;
              background-position: left top, right top, right bottom, left bottom;
            }
            18% {
              opacity: 1;
            }
            70% {
              opacity: 0.98;
              background-size: 46% 3px, 3px 46%, 46% 3px, 3px 46%;
              background-position: right top, right bottom, left bottom, left top;
            }
            100% {
              opacity: 0;
              background-size: 18% 3px, 3px 18%, 18% 3px, 3px 18%;
              background-position: right top, right bottom, left bottom, left top;
            }
          }
          @keyframes ftPdfShiftBadgePulse {
            0%, 100% {
              transform: translateY(0) scale(1);
              filter: brightness(1);
            }
            46% {
              transform: translateY(-2px) scale(1.035);
              filter: brightness(1.22);
            }
          }
          @keyframes ftPdfGhostEyeIdlePulse {
            0%, 7%, 100% { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.92), 0 0 0 4px rgba(0, 0, 0, 0.38), 0 0 0 6px rgba(255, 176, 62, 0.24), 0 8px 28px rgba(0, 0, 0, 0.46), 0 0 24px rgba(255, 147, 40, 0.42), inset 0 0 10px rgba(255, 181, 72, 0.08); }
            2.5% { box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.92), 0 0 0 4px rgba(0, 0, 0, 0.42), 0 0 0 7px rgba(255, 190, 84, 0.34), 0 10px 32px rgba(0, 0, 0, 0.5), 0 0 34px rgba(255, 159, 42, 0.58), inset 0 0 16px rgba(255, 181, 72, 0.14); }
          }
          @keyframes ftPdfSelectionPointLock {
            0%, 100% { transform: translate(-50%, -50%) scale(0.76) rotate(0deg); filter: brightness(1); }
            42% { transform: translate(-50%, -50%) scale(1.02) rotate(135deg); filter: brightness(1.34); }
            68% { transform: translate(-50%, -50%) scale(0.88) rotate(220deg); filter: brightness(1.12); }
          }
          @keyframes ftPdfSelectionPointWave {
            0% { opacity: 0.72; transform: scale(0.42); }
            72%, 100% { opacity: 0; transform: scale(1.35); }
          }
          @keyframes ftPdfGhostEyeCornerIdle {
            0%, 8%, 100% { opacity: 0.96; transform: scale(1); }
            2.5% { opacity: 1; transform: scale(1.012); }
          }
          @keyframes ftPdfGhostEyeElectronOrbit {
            0% { opacity: 0; background-position: -42% 0, 100% -42%, 142% 100%, 0 142%; filter: hue-rotate(0deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 9px rgba(255, 153, 42, 0.48)); }
            1%, 4% { opacity: 1; }
            5% { opacity: 0; background-position: 142% 0, 100% 142%, -42% 100%, 0 -42%; filter: hue-rotate(0deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 12px rgba(255, 153, 42, 0.58)); }
            5.1%, 24.9% { opacity: 0; }
            25% { opacity: 0; background-position: -42% 0, 100% -42%, 142% 100%, 0 142%; filter: hue-rotate(62deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 9px rgba(255, 153, 42, 0.48)); }
            26%, 29% { opacity: 1; }
            30% { opacity: 0; background-position: 142% 0, 100% 142%, -42% 100%, 0 -42%; filter: hue-rotate(62deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 12px rgba(255, 153, 42, 0.58)); }
            30.1%, 49.9% { opacity: 0; }
            50% { opacity: 0; background-position: -42% 0, 100% -42%, 142% 100%, 0 142%; filter: hue-rotate(142deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 9px rgba(255, 153, 42, 0.48)); }
            51%, 54% { opacity: 1; }
            55% { opacity: 0; background-position: 142% 0, 100% 142%, -42% 100%, 0 -42%; filter: hue-rotate(142deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 12px rgba(255, 153, 42, 0.58)); }
            55.1%, 74.9% { opacity: 0; }
            75% { opacity: 0; background-position: -42% 0, 100% -42%, 142% 100%, 0 142%; filter: hue-rotate(235deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 9px rgba(255, 153, 42, 0.48)); }
            76%, 79% { opacity: 1; }
            80% { opacity: 0; background-position: 142% 0, 100% 142%, -42% 100%, 0 -42%; filter: hue-rotate(235deg) drop-shadow(0 1px 4px rgba(0, 0, 0, 0.65)) drop-shadow(0 0 12px rgba(255, 153, 42, 0.58)); }
            80.1%, 100% { opacity: 0; }
          }
          @keyframes ftPdfGhostEyeBurstPulse {
            0%, 100% {
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.92),
                0 0 0 4px rgba(0, 0, 0, 0.38),
                0 0 0 6px rgba(255, 176, 62, 0.24),
                0 8px 28px rgba(0, 0, 0, 0.46),
                0 0 24px rgba(255, 147, 40, 0.42),
                inset 0 0 10px rgba(255, 181, 72, 0.08);
              filter: brightness(1);
            }
            18%, 72% {
              box-shadow:
                0 0 0 1px rgba(0, 0, 0, 0.95),
                0 0 0 4px rgba(0, 0, 0, 0.45),
                0 0 0 7px rgba(255, 206, 124, 0.38),
                0 10px 34px rgba(0, 0, 0, 0.52),
                0 0 38px rgba(255, 159, 42, 0.62),
                0 0 18px rgba(97, 255, 231, 0.22),
                inset 0 0 18px rgba(255, 181, 72, 0.16);
              filter: brightness(1.14) saturate(1.08);
            }
          }
          @keyframes ftPdfGhostEyeCornerBurst {
            0%, 100% {
              opacity: 0.92;
              transform: scale(1);
              filter:
                hue-rotate(0deg)
                drop-shadow(0 2px 5px rgba(0, 0, 0, 0.72))
                drop-shadow(0 0 10px rgba(255, 153, 42, 0.44));
            }
            32%, 68% {
              opacity: 1;
              transform: scale(1.018);
              filter:
                hue-rotate(36deg)
                drop-shadow(0 2px 6px rgba(0, 0, 0, 0.76))
                drop-shadow(0 0 16px rgba(255, 184, 78, 0.64))
                drop-shadow(0 0 10px rgba(97, 255, 231, 0.28));
            }
          }
          @keyframes ftPdfGhostEyeElectronBurst {
            0% {
              opacity: 0;
              background-position: -46% 0, 100% -46%, 146% 100%, 0 146%;
              filter:
                hue-rotate(0deg)
                drop-shadow(0 1px 4px rgba(0, 0, 0, 0.68))
                drop-shadow(0 0 9px rgba(255, 153, 42, 0.5));
            }
            10%, 88% {
              opacity: 1;
            }
            50% {
              background-position: 52% 0, 100% 52%, 48% 100%, 0 48%;
              filter:
                hue-rotate(82deg)
                drop-shadow(0 1px 5px rgba(0, 0, 0, 0.7))
                drop-shadow(0 0 13px rgba(97, 255, 231, 0.44))
                drop-shadow(0 0 10px rgba(255, 188, 86, 0.46));
            }
            100% {
              opacity: 0;
              background-position: 146% 0, 100% 146%, -46% 100%, 0 -46%;
              filter:
                hue-rotate(170deg)
                drop-shadow(0 1px 4px rgba(0, 0, 0, 0.68))
                drop-shadow(0 0 12px rgba(255, 153, 42, 0.58));
            }
          }
          .ft-pdf-ocr-card {
            display: grid;
            grid-template-rows: auto minmax(0, 1fr) auto auto;
            padding: 18px;
          }
          .ft-pdf-ocr-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding-bottom: 12px;
            cursor: grab;
            user-select: none;
            -webkit-user-select: none;
            touch-action: none;
          }
          .ft-pdf-ocr-card.is-dragging .ft-pdf-ocr-head,
          .ft-pdf-translation-card.is-dragging .ft-pdf-translation-head {
            cursor: grabbing;
          }
          .ft-pdf-ocr-head .ft-pdf-kicker {
            margin-left: auto;
          }
          .ft-pdf-ocr-head h3 {
            margin: 0;
            font-size: clamp(18px, 1.6vw, 24px);
          }
          .ft-pdf-ocr-body {
            position: relative;
            z-index: 1;
            min-height: 0;
            overflow: hidden;
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            gap: 10px;
          }
          .ft-pdf-ocr-tabs {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            padding: 5px;
            border: 1px solid rgba(126, 255, 232, 0.18);
            border-radius: 16px;
            background: linear-gradient(135deg, rgba(3, 12, 24, 0.76), rgba(17, 33, 48, 0.5));
            box-shadow: inset 0 0 18px rgba(70, 255, 226, 0.05);
          }
          .ft-pdf-ocr-tab {
            min-height: 40px;
            border: 1px solid rgba(126, 255, 232, 0.12);
            border-radius: 12px;
            background: rgba(5, 16, 30, 0.62);
            color: rgba(215, 255, 248, 0.75);
            cursor: pointer;
            font-size: 12px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-ocr-tab.is-active {
            color: #fff5cc;
            border-color: rgba(255, 206, 92, 0.56);
            background:
              linear-gradient(135deg, rgba(255, 184, 67, 0.16), rgba(70, 255, 226, 0.09)),
              radial-gradient(circle at 20% 0%, rgba(255, 218, 126, 0.18), transparent 42%);
            box-shadow: 0 0 18px rgba(255, 194, 79, 0.12), inset 0 0 14px rgba(70, 255, 226, 0.07);
          }
          .ft-pdf-ocr-panels {
            position: relative;
            z-index: 1;
            min-height: 0;
            display: grid;
          }
          .ft-pdf-ocr-panel {
            min-height: 0;
            display: none;
            grid-template-rows: auto minmax(0, 1fr);
          }
          .ft-pdf-ocr-panel.is-active {
            display: grid;
          }
          .ft-pdf-ocr-text,
          .ft-pdf-explore-input {
            position: relative;
            z-index: 1;
            min-height: 0;
            max-height: 100%;
            overflow: auto;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            border-radius: 14px;
            padding: 10px;
            border: 1px solid rgba(126, 255, 232, 0.2);
            background: rgba(2, 8, 18, 0.42);
            color: #f4fffb;
            line-height: 1.55;
            font-size: clamp(20px, 1.35vw, 25px);
          }
          .ft-pdf-text-label {
            position: relative;
            z-index: 1;
            display: block;
            margin: 0 0 8px;
            color: rgba(168, 255, 241, 0.86);
            font-size: 11px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
          }
          .ft-pdf-explore-input {
            width: 100%;
            resize: none;
            outline: none;
          }
          .ft-pdf-explore-input:focus {
            border-color: rgba(255, 187, 90, 0.74);
            box-shadow: 0 0 24px rgba(255, 178, 72, 0.14), inset 0 0 18px rgba(255, 178, 72, 0.08);
          }
          .ft-pdf-ocr-text {
            user-select: none;
            -webkit-user-select: none;
            -webkit-touch-callout: none;
          }
          .ft-pdf-translation-card {
            position: fixed;
            z-index: 2195;
            left: max(18px, 3vw);
            top: clamp(92px, 12vh, 132px);
            width: min(clamp(420px, 44vw, 760px), calc(100vw - 36px));
            max-height: min(76vh, 760px);
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            gap: 12px;
            padding: 22px;
            border: 1px solid rgba(255, 209, 99, 0.44);
            border-radius: 20px;
            background:
              linear-gradient(135deg, rgba(18, 26, 42, 0.96), rgba(5, 14, 28, 0.92)),
              radial-gradient(circle at 10% 0%, rgba(255, 198, 83, 0.2), transparent 38%),
              radial-gradient(circle at 95% 18%, rgba(82, 255, 228, 0.11), transparent 36%);
            color: #fff1bd;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.52), 0 0 30px rgba(255, 198, 83, 0.16), inset 0 0 26px rgba(70, 255, 226, 0.06);
            backdrop-filter: blur(14px);
          }
          .ft-pdf-translation-card.is-hidden {
            display: none;
          }
          .ft-pdf-translation-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            cursor: grab;
            user-select: none;
            -webkit-user-select: none;
            touch-action: none;
          }
          .ft-pdf-translation-title {
            margin: 0;
            color: #ffd985;
            font-size: 18px;
            letter-spacing: 0.16em;
            text-transform: uppercase;
          }
          .ft-pdf-translation-close {
            width: 42px;
            height: 42px;
            border: 1px solid rgba(255, 222, 132, 0.44);
            border-radius: 13px;
            background: rgba(255, 206, 96, 0.1);
            color: #ffe7b0;
            cursor: pointer;
            font-size: 20px;
          }
          .ft-pdf-translation {
            min-height: 0;
            overflow: auto;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            border: 1px solid rgba(126, 255, 232, 0.16);
            border-radius: 16px;
            padding: 18px;
            background: linear-gradient(135deg, rgba(4, 13, 27, 0.74), rgba(21, 34, 52, 0.56));
            color: #ffe9b8;
            font-size: clamp(24px, 1.8vw, 32px);
            line-height: 1.48;
          }
          .ft-pdf-button[hidden],
          #ft-pdf-audio-toggle[hidden],
          #ft-pdf-compact-audio[hidden] {
            display: none !important;
          }
          @media (max-width: 840px) {
            .ft-pdf-audio-popover-grid {
              grid-template-columns: minmax(0, 1fr);
            }
            .ft-pdf-audio-voice-row {
              grid-template-columns: minmax(0, 1fr);
            }
            .ft-pdf-audio-mic {
              min-height: 44px;
            }
          }
          .ft-pdf-word-token {
            border-radius: 5px;
            transition: background 140ms ease, color 140ms ease, box-shadow 140ms ease;
          }
          .ft-pdf-word-token[data-word-key] {
            cursor: help;
          }
          .ft-pdf-word-token.is-new {
            color: #fff8cf;
            background: linear-gradient(180deg, rgba(255, 223, 89, 0.28), rgba(255, 180, 54, 0.18));
            box-shadow: 0 0 0 1px rgba(255, 221, 89, 0.28), 0 0 14px rgba(255, 205, 68, 0.18);
          }
          .ft-pdf-phrase-token {
            position: relative;
            display: inline;
            padding: 1px 5px 2px;
            margin: 0 1px;
            border-radius: 7px;
            color: #effefa;
            background:
              linear-gradient(180deg, rgba(64, 244, 214, 0.18), rgba(7, 28, 39, 0.1)),
              linear-gradient(90deg, rgba(255, 190, 96, 0.2), transparent 40%, rgba(64, 244, 214, 0.18));
            box-shadow:
              0 0 0 1px rgba(94, 255, 230, 0.28),
              0 0 16px rgba(64, 244, 214, 0.13),
              inset 0 -1px 0 rgba(255, 190, 96, 0.42);
            -webkit-box-decoration-break: clone;
            box-decoration-break: clone;
          }
          .ft-pdf-phrase-token::after {
            content: "";
            position: absolute;
            left: 4px;
            right: 4px;
            bottom: 0;
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, #ffbc5f, #55f6dc, #a7ff8a);
            box-shadow: 0 0 12px rgba(255, 190, 96, 0.42);
            opacity: 0.82;
            pointer-events: none;
          }
          .ft-pdf-phrase-token.is-phrasal-verb {
            background:
              linear-gradient(180deg, rgba(255, 167, 88, 0.24), rgba(44, 18, 8, 0.12)),
              linear-gradient(90deg, rgba(255, 205, 104, 0.26), transparent 42%, rgba(255, 92, 137, 0.16));
            box-shadow:
              0 0 0 1px rgba(255, 190, 96, 0.34),
              0 0 18px rgba(255, 151, 72, 0.18),
              inset 0 -1px 0 rgba(255, 232, 151, 0.5);
          }
          .ft-pdf-phrase-token.is-new {
            color: #fff8cf;
            box-shadow:
              0 0 0 1px rgba(255, 221, 89, 0.34),
              0 0 20px rgba(255, 194, 70, 0.22),
              inset 0 -1px 0 rgba(255, 248, 180, 0.5);
          }
          .ft-pdf-word-token:hover {
            color: #ffffff;
            background: rgba(82, 255, 227, 0.16);
            box-shadow: 0 0 0 1px rgba(126, 255, 232, 0.28), 0 0 18px rgba(126, 255, 232, 0.16);
          }
          .ft-pdf-word-detail {
            position: fixed;
            z-index: 2200;
            width: min(clamp(420px, 50vw, 920px), calc(100vw - 28px));
            max-height: min(78vh, 720px);
            overflow: hidden;
            display: grid;
            grid-template-rows: auto minmax(0, 1fr) auto;
            pointer-events: none;
            border: 1px solid rgba(255, 209, 99, 0.42);
            border-radius: 20px;
            padding: 22px;
            background:
              linear-gradient(135deg, rgba(18, 26, 42, 0.94), rgba(5, 14, 28, 0.9)),
              radial-gradient(circle at 12% 0%, rgba(255, 198, 83, 0.18), transparent 38%);
            color: #f8fffb;
            font-size: 22px;
            box-shadow: 0 20px 58px rgba(0, 0, 0, 0.42), inset 0 0 24px rgba(255, 204, 88, 0.08);
            backdrop-filter: blur(14px);
          }
          .ft-pdf-word-detail.is-pinned {
            pointer-events: auto;
            border-color: rgba(255, 226, 126, 0.66);
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.5), 0 0 30px rgba(255, 200, 85, 0.18), inset 0 0 28px rgba(255, 204, 88, 0.1);
          }
          .ft-pdf-word-detail.is-hidden {
            display: none;
          }
          .ft-pdf-word-detail-close {
            position: absolute;
            top: 12px;
            right: 14px;
            width: 42px;
            height: 42px;
            border-radius: 13px;
            border: 1px solid rgba(255, 222, 132, 0.44);
            background: rgba(255, 206, 96, 0.1);
            color: #ffe7b0;
            cursor: pointer;
            font-size: 20px;
          }
          .ft-pdf-word-detail-close:hover {
            border-color: rgba(255, 222, 132, 0.78);
            box-shadow: 0 0 18px rgba(255, 208, 102, 0.2);
          }
          .ft-pdf-word-detail-title {
            margin: 0 0 16px;
            color: #ffdc85;
            font-size: 18px;
            letter-spacing: 0.16em;
            text-transform: uppercase;
          }
          .ft-pdf-word-detail-top {
            min-width: 0;
          }
          .ft-pdf-word-detail-word {
            margin: 0 0 7px;
            font-size: 20px;
            font-weight: 700;
            color: #ffffff;
          }
          .ft-pdf-word-head-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: 14px;
            margin: 0 0 12px;
          }
          .ft-pdf-word-main {
            min-width: 0;
            display: flex;
            align-items: baseline;
            gap: 12px;
            flex-wrap: wrap;
          }
          .ft-pdf-word-lemma {
            color: #ffffff;
            font-size: 38px;
            font-weight: 800;
            letter-spacing: 0.01em;
          }
          .ft-pdf-word-pron-inline {
            color: #ffe3a1;
            font-size: 25px;
            font-weight: 700;
            opacity: 0.94;
          }
          .ft-pdf-word-detail-results {
            min-height: 0;
            overflow: auto;
            display: flex;
            flex-direction: row-reverse;
            flex-wrap: wrap;
            align-items: stretch;
            gap: 16px;
            padding-right: 4px;
          }
          .ft-pdf-word-detail-entry {
            position: relative;
            flex: 1 1 100%;
            min-width: 0;
            display: flex;
            flex-direction: column;
            padding: 16px 18px;
            border: 1px solid rgba(126, 255, 232, 0.18);
            border-radius: 16px;
            background:
              linear-gradient(135deg, rgba(16, 32, 52, 0.82), rgba(5, 14, 28, 0.7)),
              radial-gradient(circle at 12% 0%, rgba(255, 199, 91, 0.14), transparent 42%);
            box-shadow: inset 0 0 22px rgba(76, 255, 229, 0.06), 0 12px 34px rgba(0, 0, 0, 0.24);
          }
          .ft-pdf-word-detail-results.is-multiple .ft-pdf-word-detail-entry {
            flex: 0 1 calc(50% - 8px);
            max-width: calc(50% - 8px);
          }
          .ft-pdf-word-detail-entry + .ft-pdf-word-detail-entry {
            margin-top: 0;
            padding-top: 16px;
          }
          .ft-pdf-word-detail-entry + .ft-pdf-word-detail-entry::before {
            content: "";
            position: absolute;
            inset: 0 auto auto 0;
            width: 36%;
            height: 1px;
            background: linear-gradient(90deg, rgba(255, 211, 112, 0.7), transparent);
            box-shadow: 0 0 12px rgba(255, 211, 112, 0.18);
          }
          .ft-pdf-word-detail-source {
            margin: 0 0 14px;
            color: rgba(255, 224, 145, 0.74);
            font-size: 18px;
            letter-spacing: 0.08em;
          }
          .ft-pdf-word-detail-surface {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: 12px;
            margin: 0 0 18px;
            padding: 14px 16px;
            border: 1px solid rgba(255, 198, 83, 0.28);
            border-radius: 16px;
            background: linear-gradient(135deg, rgba(255, 190, 72, 0.12), rgba(70, 255, 226, 0.06));
            color: #fff0bf;
            font-size: 24px;
          }
          .ft-pdf-word-detail-surface-main {
            min-width: 0;
            display: grid;
            gap: 6px;
          }
          .ft-pdf-word-detail-surface-ipa {
            display: inline-flex;
            flex-wrap: wrap;
            gap: 7px;
            align-items: center;
            color: rgba(255, 246, 205, 0.88);
            font-size: 16px;
            letter-spacing: 0.02em;
            text-transform: none;
          }
          .ft-pdf-word-detail-surface-ipa b {
            color: rgba(255, 186, 82, 0.94);
            font-weight: 900;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .ft-pdf-word-detail-surface span {
            color: rgba(160, 255, 239, 0.8);
            font-size: 15px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-word-detail-surface .ft-pdf-word-detail-surface-ipa,
          .ft-pdf-word-detail-surface .ft-pdf-word-detail-surface-ipa span {
            color: rgba(255, 246, 205, 0.9);
            font-size: 16px;
            letter-spacing: 0.02em;
            text-transform: none;
          }
          .ft-pdf-word-page-tabs {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 7px;
          }
          .ft-pdf-word-page-tab {
            min-height: 34px;
            padding: 0 10px;
            border: 1px solid rgba(126, 255, 232, 0.18);
            border-radius: 11px;
            background: rgba(4, 15, 28, 0.64);
            color: rgba(220, 255, 249, 0.76);
            cursor: pointer;
            font-size: 11px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
          }
          .ft-pdf-word-page-tab.is-active {
            border-color: rgba(255, 211, 110, 0.66);
            color: #fff3c7;
            background: linear-gradient(135deg, rgba(255, 191, 80, 0.16), rgba(72, 255, 225, 0.08));
            box-shadow: 0 0 16px rgba(255, 199, 88, 0.13), inset 0 0 12px rgba(72, 255, 225, 0.06);
          }
          .ft-pdf-word-detail-page {
            display: none;
            min-width: 0;
          }
          .ft-pdf-word-detail-page.is-active {
            display: grid;
            gap: 12px;
          }
          .ft-pdf-word-agent-shared {
            display: grid;
            gap: 10px;
            color: rgba(239, 255, 251, 0.9);
            font-size: 19px;
            line-height: 1.42;
          }
          .ft-pdf-word-agent-shared-title {
            color: #ffd47d;
            font-size: 13px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-word-agent-shared-body {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
          }
          .ft-pdf-word-audio-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            justify-content: flex-end;
            margin: 0;
          }
          .ft-pdf-word-audio-button {
            min-width: 60px;
            min-height: 44px;
            border-radius: 13px;
            border: 1px solid rgba(126, 255, 232, 0.28);
            background: linear-gradient(135deg, rgba(42, 255, 222, 0.12), rgba(255, 189, 84, 0.1));
            color: #eafffb;
            cursor: pointer;
            font-size: 18px;
            letter-spacing: 0.08em;
          }
          .ft-pdf-word-audio-button:hover {
            border-color: rgba(255, 218, 124, 0.72);
            box-shadow: 0 0 18px rgba(255, 207, 102, 0.18), inset 0 0 12px rgba(66, 255, 226, 0.08);
          }
          .ft-pdf-word-add-button {
            min-width: 74px;
            flex: 0 0 100%;
            max-width: 104px;
            margin-left: auto;
            border-color: rgba(255, 201, 92, 0.48);
            background:
              linear-gradient(135deg, rgba(255, 188, 70, 0.2), rgba(255, 98, 118, 0.08)),
              radial-gradient(circle at 22% 18%, rgba(255, 238, 166, 0.24), transparent 38%);
            color: #fff0bd;
            font-weight: 800;
          }
          .ft-pdf-word-add-button:hover {
            border-color: rgba(255, 228, 132, 0.86);
            box-shadow: 0 0 22px rgba(255, 188, 70, 0.22), inset 0 0 14px rgba(255, 218, 102, 0.1);
          }
          .ft-pdf-word-add-button.is-added,
          .ft-pdf-word-add-button:disabled {
            cursor: default;
            opacity: 0.82;
            border-color: rgba(101, 255, 183, 0.45);
            background:
              linear-gradient(135deg, rgba(64, 255, 180, 0.16), rgba(255, 213, 96, 0.08)),
              radial-gradient(circle at 22% 18%, rgba(115, 255, 210, 0.2), transparent 40%);
            color: #c9ffe8;
          }
          .ft-pdf-word-detail-grid {
            display: grid;
            gap: 10px;
            font-size: 22px;
            line-height: 1.38;
            color: rgba(235, 255, 250, 0.9);
          }
          .ft-pdf-word-detail-grid span {
            color: rgba(160, 255, 239, 0.82);
          }
          .ft-pdf-word-detail-grid-row {
            display: grid;
            grid-template-columns: auto minmax(0, 1fr) auto;
            gap: 8px;
            align-items: start;
          }
          .ft-pdf-word-detail-value {
            min-width: 0;
            color: rgba(238, 255, 251, 0.94);
            overflow-wrap: anywhere;
          }
          .ft-pdf-word-qmdict-edit {
            border: 1px solid rgba(255, 200, 91, 0.42);
            border-radius: 9px;
            padding: 5px 9px;
            background:
              linear-gradient(135deg, rgba(255, 171, 57, 0.2), rgba(44, 255, 227, 0.08)),
              radial-gradient(circle at 20% 20%, rgba(255, 232, 142, 0.24), transparent 48%);
            color: #ffe2a0;
            cursor: pointer;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            box-shadow: inset 0 0 12px rgba(255, 207, 103, 0.08);
          }
          .ft-pdf-word-qmdict-edit:hover {
            border-color: rgba(255, 224, 136, 0.78);
            box-shadow: 0 0 16px rgba(255, 184, 64, 0.24), inset 0 0 14px rgba(94, 255, 226, 0.1);
          }
          .ft-pdf-word-qmdict-edit.is-busy {
            opacity: 0.62;
            pointer-events: none;
          }
          .ft-pdf-word-detail-rich {
            display: grid;
            gap: 9px;
            margin-top: 12px;
            font-size: 19px;
            line-height: 1.42;
            color: rgba(244, 255, 251, 0.9);
          }
          .ft-pdf-word-detail-rich-row {
            display: grid;
            gap: 3px;
            padding: 9px 10px;
            border: 1px solid rgba(255, 209, 99, 0.16);
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(255, 200, 83, 0.08), rgba(63, 255, 224, 0.045));
          }
          .ft-pdf-word-detail-rich-row b {
            color: #ffd47d;
            font-size: 13px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-word-detail-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
          }
          .ft-pdf-word-detail-chip {
            padding: 5px 8px;
            border: 1px solid rgba(116, 255, 231, 0.22);
            border-radius: 999px;
            color: #eafffb;
            background: rgba(40, 255, 223, 0.07);
            box-shadow: inset 0 0 10px rgba(66, 255, 226, 0.05);
          }
          .ft-pdf-word-example-row {
            display: grid;
            gap: 4px;
            padding: 8px 9px;
            border: 1px solid rgba(114, 255, 230, 0.18);
            border-radius: 10px;
            background:
              linear-gradient(135deg, rgba(29, 255, 216, 0.075), rgba(255, 185, 72, 0.07)),
              radial-gradient(circle at 4% 10%, rgba(255, 222, 127, 0.12), transparent 42%);
          }
          .ft-pdf-word-example-row strong {
            color: #fff3c4;
            font-size: 18px;
            line-height: 1.35;
          }
          .ft-pdf-word-example-row small {
            color: rgba(192, 255, 239, 0.86);
            font-size: 15px;
            line-height: 1.35;
          }
          .ft-pdf-word-detail-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 9px;
            justify-content: flex-end;
          }
          .ft-pdf-word-detail-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-top: 14px;
            padding-top: 12px;
            border-top: 1px solid rgba(255, 209, 99, 0.18);
            background: linear-gradient(180deg, rgba(5, 14, 28, 0), rgba(5, 14, 28, 0.42));
          }
          .ft-pdf-word-detail-footer-note {
            color: rgba(166, 255, 239, 0.72);
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .ft-pdf-word-agent-button {
            min-height: 42px;
            padding: 0 13px;
            border: 1px solid rgba(255, 215, 118, 0.38);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(255, 180, 76, 0.16), rgba(55, 255, 223, 0.08)),
              linear-gradient(90deg, transparent, rgba(255, 229, 142, 0.1), transparent);
            color: #fff3ca;
            cursor: pointer;
            font-size: 14px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            box-shadow: inset 0 0 14px rgba(255, 209, 99, 0.06), 0 0 16px rgba(255, 200, 83, 0.08);
          }
          .ft-pdf-word-agent-button:hover {
            border-color: rgba(255, 231, 146, 0.74);
            color: #ffffff;
            box-shadow: 0 0 22px rgba(255, 207, 102, 0.18), inset 0 0 16px rgba(64, 255, 225, 0.08);
          }
          .ft-pdf-ocr-actions,
          .ft-pdf-agent-row {
            display: flex;
            gap: 6px;
            align-items: center;
            flex-wrap: wrap;
            padding-top: 6px;
          }
          .ft-pdf-ocr-actions {
            flex-wrap: wrap;
            overflow: visible;
            max-width: 100%;
            padding: 2px 0;
          }
          .ft-pdf-ocr-actions .ft-pdf-button,
          .ft-pdf-ocr-actions .ft-pdf-voice-select {
            flex: 0 1 auto;
            min-height: 24px;
            padding: 3px 10px;
            border-radius: 8px;
            font-size: 12px;
            line-height: 1.1;
            letter-spacing: 0;
          }
          .ft-pdf-agent-row .ft-pdf-button,
          .ft-pdf-agent-row .ft-pdf-voice-select {
            min-height: 24px;
            padding: 3px 10px;
            border-radius: 8px;
            font-size: 12px;
            line-height: 1.1;
            letter-spacing: 0;
          }
          .ft-pdf-ocr-actions .ft-pdf-button[data-pdf-action="translate"],
          .ft-pdf-agent-row .ft-pdf-button[data-pdf-action="ask"] {
            min-width: 86px;
            padding-left: 12px;
            padding-right: 12px;
            border-color: rgba(55, 232, 205, 0.76);
            color: #f7fffd;
            background:
              linear-gradient(135deg, rgba(16, 185, 129, 0.34), rgba(37, 99, 235, 0.28)),
              rgba(7, 17, 28, 0.82);
            box-shadow:
              0 0 0 1px rgba(255, 255, 255, 0.12) inset,
              0 0 18px rgba(45, 212, 191, 0.2),
              0 0 28px rgba(37, 99, 235, 0.12);
            font-weight: 800;
          }
          .ft-pdf-ocr-actions .ft-pdf-button[data-pdf-action="translate"] {
            border-color: rgba(250, 204, 21, 0.82);
            background:
              linear-gradient(135deg, rgba(250, 204, 21, 0.32), rgba(20, 184, 166, 0.24)),
              rgba(11, 18, 28, 0.84);
            box-shadow:
              0 0 0 1px rgba(255, 255, 255, 0.12) inset,
              0 0 18px rgba(250, 204, 21, 0.22),
              0 0 26px rgba(20, 184, 166, 0.12);
          }
          .ft-pdf-ocr-actions .ft-pdf-button[data-pdf-action="translate"]:hover,
          .ft-pdf-agent-row .ft-pdf-button[data-pdf-action="ask"]:hover,
          .ft-pdf-ocr-actions .ft-pdf-button[data-pdf-action="translate"]:focus-visible,
          .ft-pdf-agent-row .ft-pdf-button[data-pdf-action="ask"]:focus-visible {
            transform: translateY(-1px);
            filter: brightness(1.08) saturate(1.08);
            box-shadow:
              0 0 0 1px rgba(255, 255, 255, 0.18) inset,
              0 0 22px rgba(45, 212, 191, 0.28),
              0 0 34px rgba(250, 204, 21, 0.16);
          }
          .ft-pdf-agent-input {
            flex: 1 1 180px;
            min-height: 40px;
            border-radius: 13px;
            padding: 0 13px;
          }
          .ft-pdf-agent-input-shell {
            flex: 1 1 220px;
            min-width: min(100%, 220px);
          }
          .ft-pdf-agent-input-shell .ft-pdf-agent-input {
            width: 100%;
            padding-right: 172px;
          }
          .ft-pdf-agent-input-shell .ft-vietnamese-typing-toggle {
            top: 5px;
            right: 6px;
            height: 30px;
          }
          .ft-pdf-agent-input-shell .ft-pdf-agent-clear-input {
            right: 54px;
            min-width: 56px;
            color: rgba(255, 232, 174, 0.92);
            border-color: rgba(255, 209, 99, 0.34);
            background:
              linear-gradient(135deg, rgba(255, 209, 99, 0.12), rgba(104, 243, 226, 0.08)),
              rgba(5, 13, 26, 0.82);
          }
          .ft-pdf-agent-input-shell .ft-zipformer-vi-input-mic {
            right: 118px;
          }
          .ft-pdf-agent-mode-toggle {
            min-width: 132px;
            border-color: rgba(255, 209, 99, 0.42);
            color: #fff2c3;
            background:
              linear-gradient(135deg, rgba(255, 185, 72, 0.16), rgba(77, 255, 225, 0.1)),
              rgba(5, 13, 26, 0.76);
          }
          .ft-pdf-agent-mode-toggle[aria-pressed="false"] {
            border-color: rgba(104, 243, 226, 0.42);
            color: rgba(188, 255, 243, 0.94);
            background:
              linear-gradient(135deg, rgba(77, 255, 225, 0.12), rgba(96, 165, 250, 0.1)),
              rgba(5, 13, 26, 0.76);
          }
          .ft-pdf-agent-input-preview {
            position: fixed;
            z-index: 2240;
            display: grid;
            gap: 9px;
            max-height: min(70vh, calc(100vh - 28px));
            padding: 13px;
            pointer-events: none;
            opacity: 0;
            transform: translateY(12px) scale(0.985);
            transform-origin: right bottom;
            border: 1px solid rgba(104, 243, 226, 0.34);
            border-radius: 16px;
            background:
              linear-gradient(145deg, rgba(6, 17, 29, 0.97), rgba(5, 12, 24, 0.94)),
              radial-gradient(circle at 12% 0%, rgba(104, 243, 226, 0.14), transparent 38%),
              radial-gradient(circle at 92% 12%, rgba(255, 209, 99, 0.13), transparent 34%);
            box-shadow:
              0 22px 70px rgba(0, 0, 0, 0.46),
              0 0 28px rgba(104, 243, 226, 0.12),
              inset 0 0 22px rgba(104, 243, 226, 0.05);
            backdrop-filter: blur(14px);
            transition: opacity 160ms ease, transform 180ms ease;
          }
          .ft-pdf-agent-input-preview.is-visible {
            opacity: 1;
            transform: translateY(0) scale(1);
            pointer-events: auto;
          }
          .ft-pdf-agent-input-preview-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            color: rgba(192, 255, 243, 0.82);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-agent-input-preview-head b {
            color: #fff1bd;
            font-size: 10px;
            white-space: nowrap;
          }
          .ft-pdf-agent-input-preview-body {
            position: relative;
            display: block;
            box-sizing: border-box;
            width: 100%;
            overflow: auto;
            max-height: 238px;
            min-height: 64px;
            padding: 10px 11px;
            border: 1px solid rgba(104, 243, 226, 0.16);
            border-radius: 10px;
            background:
              linear-gradient(135deg, rgba(104, 243, 226, 0.08), rgba(255, 209, 99, 0.035)),
              rgba(1, 8, 17, 0.42);
            color: #f4fffd;
            font-family: inherit;
            font-size: 15px;
            font-weight: 760;
            line-height: 1.48;
            overflow-wrap: anywhere;
            white-space: pre-wrap;
            text-shadow: 0 0 10px rgba(104, 243, 226, 0.13);
            cursor: text;
            outline: none;
            resize: none;
            scrollbar-color: rgba(104, 243, 226, 0.5) rgba(1, 8, 17, 0.34);
          }
          textarea.ft-pdf-agent-input-preview-body {
            min-height: 92px;
          }
          .ft-pdf-agent-input-preview-body:focus {
            border-color: rgba(255, 209, 99, 0.58);
            box-shadow:
              0 0 0 2px rgba(255, 209, 99, 0.12),
              0 0 24px rgba(104, 243, 226, 0.16),
              inset 0 0 16px rgba(255, 209, 99, 0.06);
          }
          .ft-pdf-agent-input-preview-text {
            white-space: pre-wrap;
            overflow-wrap: anywhere;
          }
          .ft-pdf-agent-input-preview-live-char {
            color: #fff1bd;
            text-shadow:
              0 0 10px rgba(255, 209, 99, 0.72),
              0 0 18px rgba(104, 243, 226, 0.34);
            background: linear-gradient(180deg, transparent 58%, rgba(255, 209, 99, 0.32) 0);
            filter: brightness(1.08);
          }
          .ft-pdf-agent-input-preview-caret {
            display: inline-block;
            width: 7px;
            height: 1.1em;
            margin-left: 3px;
            vertical-align: -0.16em;
            background: linear-gradient(180deg, #68f3e2, #ffd163);
            box-shadow: 0 0 12px rgba(104, 243, 226, 0.58);
            opacity: 0.72;
            transform: scaleY(0.86);
          }
          .ft-pdf-agent-input-preview-body.is-typing .ft-pdf-agent-input-preview-live-char {
            animation: ftPdfAgentInputLiveChar 520ms ease-in-out infinite alternate;
          }
          .ft-pdf-agent-input-preview-body.is-typing .ft-pdf-agent-input-preview-caret {
            animation: ftPdfAgentInputCaret 520ms ease-in-out infinite;
          }
          .ft-pdf-agent-input-preview-body.is-idle .ft-pdf-agent-input-preview-caret {
            display: none;
          }
          .ft-pdf-agent-input-preview-body.is-idle .ft-pdf-agent-input-preview-live-char {
            color: inherit;
            background: none;
            filter: none;
            text-shadow: inherit;
            animation: none;
          }
          .ft-pdf-agent-input-preview-empty {
            color: rgba(192, 255, 243, 0.66);
            font-size: 14px;
            font-weight: 850;
          }
          @keyframes ftPdfAgentInputLiveChar {
            from {
              filter: brightness(1);
            }
            to {
              filter: brightness(1.3);
            }
          }
          @keyframes ftPdfAgentInputCaret {
            0%, 100% { opacity: 0.28; transform: scaleY(0.76); }
            50% { opacity: 1; transform: scaleY(1); }
          }
          .ft-pdf-agent-modal {
            position: fixed;
            inset: 0;
            z-index: 2230;
            display: grid;
            place-items: center;
            padding: clamp(16px, 3vw, 34px);
            background:
              radial-gradient(circle at 50% 40%, rgba(255, 183, 72, 0.14), transparent 34%),
              radial-gradient(circle at 78% 20%, rgba(77, 255, 225, 0.12), transparent 28%),
              rgba(1, 5, 14, 0.62);
            backdrop-filter: blur(12px);
          }
          .ft-pdf-agent-modal.is-hidden {
            display: none;
          }
          .ft-pdf-agent-card {
            position: relative;
            width: min(780px, calc(100vw - 30px));
            max-height: min(82vh, 760px);
            display: grid;
            grid-template-rows: auto minmax(0, 1fr) auto;
            overflow: hidden;
            border: 1px solid rgba(255, 198, 84, 0.38);
            border-radius: 22px;
            background:
              linear-gradient(145deg, rgba(9, 18, 34, 0.97), rgba(5, 13, 27, 0.96)),
              radial-gradient(circle at 12% 0%, rgba(255, 190, 74, 0.16), transparent 38%),
              radial-gradient(circle at 92% 16%, rgba(72, 255, 226, 0.12), transparent 34%);
            box-shadow:
              0 34px 110px rgba(0, 0, 0, 0.58),
              0 0 44px rgba(255, 183, 72, 0.12),
              inset 0 0 34px rgba(76, 255, 227, 0.07);
            animation: ftPdfAgentCardIn 360ms cubic-bezier(.18,.86,.22,1) both;
          }
          .ft-pdf-agent-card::before,
          .ft-pdf-agent-card::after {
            content: "";
            position: absolute;
            pointer-events: none;
          }
          .ft-pdf-agent-card::before {
            inset: 0;
            border-radius: inherit;
            background:
              linear-gradient(90deg, rgba(255, 210, 105, 0.82), transparent 18%, transparent 78%, rgba(84, 255, 228, 0.64)) top / 100% 1px no-repeat,
              linear-gradient(90deg, rgba(84, 255, 228, 0.54), transparent 34%, rgba(255, 210, 105, 0.48)) bottom / 100% 1px no-repeat,
              linear-gradient(180deg, rgba(255, 210, 105, 0.42), transparent 42%, rgba(84, 255, 228, 0.36)) right / 1px 100% no-repeat;
          }
          .ft-pdf-agent-card::after {
            inset: 10px;
            border-radius: 18px;
            background:
              repeating-linear-gradient(90deg, rgba(255,255,255,0.035) 0 1px, transparent 1px 22px),
              linear-gradient(120deg, transparent, rgba(255, 204, 98, 0.08), transparent);
            opacity: 0.72;
          }
          .ft-pdf-agent-head,
          .ft-pdf-agent-content,
          .ft-pdf-agent-foot {
            position: relative;
            z-index: 1;
          }
          .ft-pdf-agent-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            padding: 20px 22px 12px;
          }
          .ft-pdf-agent-kicker {
            margin: 0 0 5px;
            color: rgba(255, 218, 138, 0.86);
            font-size: 11px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
          }
          .ft-pdf-agent-title {
            margin: 0;
            color: #ffffff;
            font-size: clamp(22px, 2.1vw, 32px);
            line-height: 1.1;
            text-shadow: 0 0 24px rgba(255, 190, 74, 0.18);
          }
          .ft-pdf-agent-close {
            width: 42px;
            height: 42px;
            border-radius: 13px;
            border: 1px solid rgba(255, 218, 132, 0.42);
            background: linear-gradient(135deg, rgba(255, 192, 82, 0.13), rgba(64, 255, 226, 0.08));
            color: #ffe8b0;
            cursor: pointer;
            font-size: 20px;
            box-shadow: inset 0 0 16px rgba(255, 196, 82, 0.08);
          }
          .ft-pdf-agent-head-actions {
            display: flex;
            align-items: center;
            gap: 9px;
          }
          .ft-pdf-agent-back {
            display: none;
            min-height: 38px;
            padding: 0 13px;
            border-radius: 13px;
            border: 1px solid rgba(126, 255, 232, 0.34);
            background: linear-gradient(135deg, rgba(76, 255, 227, 0.12), rgba(255, 194, 84, 0.09));
            color: #dffff8;
            cursor: pointer;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 11px;
            box-shadow: inset 0 0 14px rgba(76, 255, 227, 0.07);
          }
          .ft-pdf-agent-card.has-history-back .ft-pdf-agent-back {
            display: inline-flex;
            align-items: center;
          }
          .ft-pdf-agent-back:hover {
            border-color: rgba(255, 218, 132, 0.62);
            box-shadow: 0 0 18px rgba(255, 197, 84, 0.14), inset 0 0 16px rgba(76, 255, 227, 0.08);
          }
          .ft-pdf-agent-content {
            min-height: 0;
            margin: 0 22px 16px;
            padding: 18px;
            overflow: auto;
            border: 1px solid rgba(126, 255, 232, 0.2);
            border-radius: 18px;
            background:
              linear-gradient(135deg, rgba(4, 12, 25, 0.74), rgba(13, 27, 45, 0.64)),
              radial-gradient(circle at 8% 0%, rgba(255, 199, 92, 0.1), transparent 36%);
            color: rgba(244, 255, 252, 0.94);
            font-size: clamp(15px, 1.2vw, 18px);
            line-height: 1.68;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            box-shadow: inset 0 0 28px rgba(65, 255, 226, 0.06);
          }
          .ft-pdf-agent-content::-webkit-scrollbar {
            width: 8px;
          }
          .ft-pdf-agent-content::-webkit-scrollbar-thumb {
            border-radius: 99px;
            background: linear-gradient(180deg, rgba(255, 199, 92, 0.78), rgba(80, 255, 225, 0.54));
          }
          .ft-pdf-agent-card.is-loading .ft-pdf-agent-content {
            color: rgba(255, 231, 181, 0.88);
          }
          .ft-pdf-agent-history-list {
            display: grid;
            gap: 12px;
          }
          .ft-pdf-agent-history-row {
            display: grid;
            gap: 6px;
            width: 100%;
            padding: 13px 14px;
            border: 1px solid rgba(126, 255, 232, 0.2);
            border-radius: 15px;
            background:
              linear-gradient(135deg, rgba(255, 190, 74, 0.1), rgba(76, 255, 227, 0.07)),
              rgba(3, 12, 24, 0.62);
            color: #efffff;
            text-align: left;
            cursor: pointer;
            box-shadow: inset 0 0 18px rgba(76, 255, 227, 0.05);
          }
          .ft-pdf-agent-history-row:hover {
            border-color: rgba(255, 210, 105, 0.58);
            box-shadow: 0 0 22px rgba(255, 190, 74, 0.14), inset 0 0 18px rgba(76, 255, 227, 0.07);
          }
          .ft-pdf-agent-history-title {
            color: #fff0bf;
            font-size: 15px;
            font-weight: 800;
            overflow-wrap: anywhere;
          }
          .ft-pdf-agent-history-meta {
            color: rgba(168, 255, 241, 0.72);
            font-size: 11px;
            letter-spacing: 0.08em;
          }
          .ft-pdf-agent-history-preview {
            color: rgba(240, 255, 252, 0.86);
            font-size: 13px;
            line-height: 1.45;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
          }
          .ft-pdf-agent-history-empty {
            padding: 28px 16px;
            border: 1px dashed rgba(126, 255, 232, 0.22);
            border-radius: 16px;
            color: rgba(230, 255, 251, 0.72);
            text-align: center;
          }
          .ft-pdf-agent-loader {
            display: none;
            align-items: center;
            gap: 12px;
            color: rgba(255, 226, 166, 0.9);
            letter-spacing: 0.08em;
          }
          .ft-pdf-agent-card.is-loading .ft-pdf-agent-loader {
            display: inline-flex;
          }
          .ft-pdf-agent-brain {
            position: relative;
            width: 54px;
            height: 44px;
            display: grid;
            place-items: center;
            color: #ffd27a;
          }
          .ft-pdf-agent-brain::before {
            content: "";
            position: absolute;
            inset: -7px -8px;
            border-radius: 50%;
            border: 1px solid rgba(255, 210, 105, 0.28);
            box-shadow: 0 0 24px rgba(255, 200, 85, 0.18), inset 0 0 18px rgba(76, 255, 227, 0.08);
            animation: ftPdfBrainHalo 1.35s ease-in-out infinite;
          }
          .ft-pdf-agent-brain svg {
            position: relative;
            z-index: 1;
            width: 46px;
            height: 36px;
            overflow: visible;
            filter: drop-shadow(0 0 12px rgba(255, 208, 113, 0.36));
          }
          .ft-pdf-agent-brain path,
          .ft-pdf-agent-brain circle {
            fill: none;
            stroke: currentColor;
            stroke-linecap: round;
            stroke-linejoin: round;
          }
          .ft-pdf-agent-brain path {
            stroke-width: 2.2;
            stroke-dasharray: 36 18;
            animation: ftPdfBrainTrace 1.1s linear infinite;
          }
          .ft-pdf-agent-brain circle {
            fill: #53ffe0;
            stroke: rgba(83, 255, 224, 0.55);
            animation: ftPdfBrainNode 1.05s ease-in-out infinite;
          }
          .ft-pdf-agent-brain circle:nth-of-type(2) { animation-delay: 120ms; }
          .ft-pdf-agent-brain circle:nth-of-type(3) { animation-delay: 240ms; }
          .ft-pdf-agent-brain circle:nth-of-type(4) { animation-delay: 360ms; }
          .ft-pdf-agent-loader-copy {
            display: grid;
            gap: 2px;
          }
          .ft-pdf-agent-loader-copy strong {
            color: #fff1c2;
            font-size: 12px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
          }
          .ft-pdf-agent-loader-copy b {
            color: #7dffe8;
            font-size: 18px;
            letter-spacing: 0.08em;
            text-shadow: 0 0 14px rgba(83, 255, 224, 0.28);
          }
          .ft-pdf-agent-foot {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 0 22px 20px;
            color: rgba(168, 255, 241, 0.78);
            font-size: 12px;
            letter-spacing: 0.08em;
          }
          @keyframes ftPdfAgentCardIn {
            from { opacity: 0; transform: translateY(18px) scale(0.96); filter: blur(6px); }
            to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
          }
          @keyframes ftPdfBrainTrace {
            to { stroke-dashoffset: -54; }
          }
          @keyframes ftPdfBrainNode {
            0%, 100% { opacity: 0.45; transform: scale(0.78); }
            50% { opacity: 1; transform: scale(1.18); }
          }
          @keyframes ftPdfBrainHalo {
            0%, 100% { opacity: 0.48; transform: scale(0.92); }
            50% { opacity: 1; transform: scale(1.04); }
          }
          .ft-pdf-speak-modal {
            position: fixed;
            left: var(--ft-pdf-speak-left, 10px);
            top: var(--ft-pdf-speak-top, 68px);
            z-index: 2240;
            display: block;
            width: calc(100vw - 20px);
            height: calc(100vh - 78px);
            max-height: calc(100vh - 78px);
            padding: 0;
            background: transparent;
            pointer-events: none;
          }
          .ft-pdf-speak-modal.is-hidden {
            display: none;
          }
          .ft-pdf-speak-card {
            position: relative;
            width: 100%;
            height: 100%;
            max-height: inherit;
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            overflow: hidden;
            border: 1px solid rgba(255, 194, 84, 0.46);
            border-radius: 18px;
            background:
              linear-gradient(145deg, rgba(8, 18, 34, 0.98), rgba(4, 11, 24, 0.97)),
              radial-gradient(circle at 8% 0%, rgba(255, 182, 64, 0.16), transparent 34%),
              radial-gradient(circle at 92% 12%, rgba(62, 255, 225, 0.12), transparent 32%);
            box-shadow: 0 30px 82px rgba(0,0,0,0.56), 0 0 38px rgba(255, 188, 74, 0.16), inset 0 0 32px rgba(76, 255, 228, 0.07);
            animation: ftPdfAgentCardIn 340ms cubic-bezier(.18,.86,.22,1) both;
            pointer-events: auto;
          }
          .ft-pdf-speak-card::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            border-radius: inherit;
            background:
              linear-gradient(90deg, rgba(255, 214, 124, 0.78), transparent 20%, transparent 74%, rgba(85, 255, 230, 0.54)) top / 100% 1px no-repeat,
              linear-gradient(180deg, rgba(255, 214, 124, 0.44), transparent 44%, rgba(85, 255, 230, 0.35)) right / 1px 100% no-repeat,
              repeating-linear-gradient(90deg, transparent 0 28px, rgba(255,255,255,0.035) 28px 29px);
          }
          .ft-pdf-speak-head,
          .ft-pdf-speak-body {
            position: relative;
            z-index: 1;
          }
          .ft-pdf-speak-head {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            padding: 16px 20px 10px;
            text-align: left;
          }
          .ft-pdf-speak-kicker {
            margin: 0 0 4px;
            color: rgba(255, 218, 138, 0.86);
            font-size: 11px;
            letter-spacing: 0.18em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-title {
            margin: 0;
            color: #ffffff;
            font-size: clamp(22px, 2vw, 30px);
            line-height: 1.1;
          }
          .ft-pdf-speak-close {
            position: static;
            transform: none;
            width: 42px;
            height: 42px;
            border-radius: 13px;
            border: 1px solid rgba(255, 218, 132, 0.42);
            background: linear-gradient(135deg, rgba(255, 192, 82, 0.13), rgba(64, 255, 226, 0.08));
            color: #ffe8b0;
            cursor: pointer;
            font-size: 20px;
          }
          .ft-pdf-speak-body {
            min-height: 0;
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            gap: 16px;
            padding: 0 20px 20px;
            overflow: hidden;
          }
          .ft-pdf-speak-practice-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.62fr) minmax(280px, 0.72fr);
            gap: 16px;
            min-height: 0;
          }
          .ft-pdf-speak-reference-panel {
            display: grid;
            gap: 10px;
            padding: 11px 12px;
            border: 1px solid rgba(255, 204, 103, 0.24);
            border-radius: 16px;
            background:
              linear-gradient(135deg, rgba(255, 184, 76, 0.1), rgba(71, 255, 231, 0.055)),
              rgba(4, 12, 25, 0.66);
            box-shadow: inset 0 0 24px rgba(255, 187, 78, 0.06);
          }
          .ft-pdf-speak-reference-tools {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
          }
          .ft-pdf-speak-reference-title {
            color: rgba(255, 224, 154, 0.92);
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 0.14em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-reference-voice {
            min-width: min(360px, 100%);
            min-height: 50px;
            border-radius: 13px;
            border: 1px solid rgba(255, 216, 120, 0.42);
            background: rgba(3, 12, 24, 0.84);
            color: #fff5d6;
            font-size: 20px;
          }
          .ft-pdf-speak-reference-voice option.is-priority {
            color: #ffd47a;
            background: #111a24;
            font-weight: 900;
          }
          .ft-pdf-speak-reference-text,
          .ft-pdf-speak-reference-ipa {
            display: block;
            min-height: 34px;
            max-height: 220px;
            overflow: auto;
            padding: 9px 12px;
            border: 1px solid rgba(126, 255, 232, 0.14);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(8, 22, 39, 0.72), rgba(5, 12, 24, 0.54)),
              radial-gradient(circle at 8% 0%, rgba(255, 202, 88, 0.1), transparent 36%);
            color: rgba(241, 255, 252, 0.96);
            font-size: 30px;
            line-height: 1.5;
            white-space: normal;
            word-break: break-word;
          }
          .ft-pdf-speak-reference-ipa {
            opacity: 0.92;
            color: rgba(190, 255, 245, 0.9);
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 26px;
          }
          .ft-pdf-speak-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 14px;
            min-height: 0;
          }
          .ft-pdf-speak-wave-panel,
          .ft-pdf-speak-feedback-panel {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(126, 255, 232, 0.2);
            border-radius: 18px;
            background:
              linear-gradient(135deg, rgba(4, 12, 25, 0.76), rgba(13, 27, 45, 0.62)),
              radial-gradient(circle at 8% 0%, rgba(255, 199, 92, 0.1), transparent 36%);
            box-shadow: inset 0 0 22px rgba(76, 255, 228, 0.06);
          }
          .ft-pdf-speak-wave-panel {
            display: grid;
            gap: 12px;
            padding: 16px;
            align-content: start;
          }
          .ft-pdf-speak-wave-panel.is-processing::before {
            content: none;
            display: none;
            position: absolute;
            left: 50%;
            top: 22px;
            z-index: 2;
            width: 62px;
            height: 82px;
            transform: translateX(-50%);
            border: 4px solid rgba(255, 214, 126, 0.9);
            border-left-width: 10px;
            border-bottom-color: transparent;
            border-radius: 58% 42% 46% 58% / 54% 46% 54% 46%;
            box-shadow: 0 0 24px rgba(255, 196, 83, 0.34), inset 0 0 18px rgba(96, 255, 230, 0.12);
            animation: ftPdfSpeakEarListen 1.15s ease-in-out infinite;
            pointer-events: none;
          }
          .ft-pdf-speak-wave-panel.is-processing::after {
            content: none;
            display: none;
            position: absolute;
            left: 50%;
            top: 38px;
            z-index: 2;
            width: 118px;
            height: 50px;
            transform: translateX(-50%);
            border-radius: 999px;
            background:
              radial-gradient(circle at 50% 50%, rgba(255, 224, 142, 0.45) 0 3px, transparent 4px),
              repeating-radial-gradient(circle at 50% 50%, rgba(85, 255, 230, 0.42) 0 2px, transparent 2px 14px);
            mask: linear-gradient(90deg, transparent, #000 20%, #000 80%, transparent);
            opacity: 0.78;
            animation: ftPdfSpeakListenRings 1.15s ease-in-out infinite;
            pointer-events: none;
          }
          @keyframes ftPdfSpeakEarListen {
            0%, 100% { opacity: 0.68; filter: drop-shadow(0 0 6px rgba(255, 196, 83, 0.22)); transform: translateX(-50%) scale(0.96); }
            50% { opacity: 1; filter: drop-shadow(0 0 18px rgba(255, 196, 83, 0.48)); transform: translateX(-50%) scale(1.04); }
          }
          @keyframes ftPdfSpeakListenRings {
            0% { opacity: 0.18; transform: translateX(-50%) scaleX(0.58); }
            55% { opacity: 0.9; transform: translateX(-50%) scaleX(1); }
            100% { opacity: 0.18; transform: translateX(-50%) scaleX(1.16); }
          }
          .ft-pdf-speak-canvas {
            width: 100%;
            height: 148px;
            border-radius: 16px;
            border: 1px solid rgba(255, 205, 95, 0.26);
            background:
              radial-gradient(circle at 18% 35%, rgba(255, 190, 76, 0.13), transparent 34%),
              radial-gradient(circle at 78% 50%, rgba(72, 255, 229, 0.12), transparent 38%),
              linear-gradient(180deg, rgba(255, 202, 94, 0.07), transparent),
              repeating-linear-gradient(90deg, rgba(255,255,255,0.045) 0 1px, transparent 1px 20px),
              rgba(2, 8, 18, 0.78);
          }
          .ft-pdf-speak-wave-panel.is-processing .ft-pdf-speak-canvas {
            border-color: rgba(255, 219, 128, 0.52);
            box-shadow:
              0 0 28px rgba(255, 189, 69, 0.16),
              inset 0 0 26px rgba(88, 255, 230, 0.12);
            animation: ftPdfSpeakCanvasListenGlow 1.2s ease-in-out infinite;
          }
          .ft-pdf-speak-listen-indicator {
            display: none;
            position: relative;
            overflow: hidden;
            align-items: center;
            justify-content: center;
            gap: 16px;
            min-height: 122px;
            padding: 12px 14px;
            border-radius: 18px;
            border: 1px solid rgba(255, 215, 118, 0.34);
            background:
              radial-gradient(circle at 18% 50%, rgba(255, 204, 91, 0.18), transparent 34%),
              radial-gradient(circle at 78% 42%, rgba(73, 255, 228, 0.16), transparent 36%),
              linear-gradient(135deg, rgba(255, 188, 72, 0.1), rgba(76, 255, 228, 0.08));
            color: rgba(255, 236, 190, 0.94);
            box-shadow:
              inset 0 0 26px rgba(255, 201, 91, 0.08),
              inset 0 0 38px rgba(74, 255, 228, 0.06);
          }
          .ft-pdf-speak-listen-indicator::before {
            content: "";
            position: absolute;
            inset: 8px;
            border-radius: 14px;
            border: 1px solid rgba(255, 222, 142, 0.12);
            background:
              linear-gradient(90deg, transparent 0 42%, rgba(255, 226, 150, 0.16) 50%, transparent 58%),
              repeating-linear-gradient(0deg, transparent 0 12px, rgba(96, 255, 231, 0.06) 12px 13px);
            opacity: 0.62;
            animation: ftPdfSpeakListenGrid 2.2s linear infinite;
            pointer-events: none;
          }
          .ft-pdf-speak-listen-indicator::after {
            content: "";
            position: absolute;
            inset: -20% -12%;
            background:
              conic-gradient(from 180deg, transparent 0 34%, rgba(255, 215, 118, 0.2) 39%, transparent 45% 72%, rgba(80, 255, 230, 0.16) 78%, transparent 86%);
            opacity: 0.48;
            animation: ftPdfSpeakListenSweep 3.6s linear infinite;
            pointer-events: none;
          }
          .ft-pdf-speak-wave-panel.is-processing .ft-pdf-speak-listen-indicator,
          .ft-pdf-speak-wave-panel.is-listening .ft-pdf-speak-listen-indicator {
            display: flex !important;
          }
          .ft-pdf-speak-ear-core {
            position: relative;
            display: inline-grid;
            place-items: center;
            width: 96px;
            height: 96px;
            flex: 0 0 96px;
            z-index: 1;
          }
          .ft-pdf-speak-ear-orbit {
            position: absolute;
            inset: 3px;
            border-radius: 50%;
            border: 1px solid rgba(255, 223, 143, 0.3);
            box-shadow: 0 0 22px rgba(255, 199, 82, 0.15);
            animation: ftPdfSpeakEarOrbit 2.2s linear infinite;
          }
          .ft-pdf-speak-ear-orbit.is-secondary {
            inset: 13px;
            border-color: rgba(82, 255, 229, 0.28);
            animation-duration: 1.55s;
            animation-direction: reverse;
          }
          .ft-pdf-speak-ear-spark {
            position: absolute;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #ffe49b;
            box-shadow: 0 0 14px rgba(255, 219, 128, 0.78);
            animation: ftPdfSpeakEarSpark 1.25s ease-in-out infinite;
          }
          .ft-pdf-speak-ear-spark.is-a { left: 4px; top: 48%; }
          .ft-pdf-speak-ear-spark.is-b { right: 8px; top: 24%; animation-delay: 0.28s; background: #67ffe6; }
          .ft-pdf-speak-ear-svg {
            position: relative;
            z-index: 1;
            width: 78px;
            height: 78px;
            flex: 0 0 auto;
            filter:
              drop-shadow(0 0 12px rgba(255, 198, 80, 0.38))
              drop-shadow(0 0 22px rgba(76, 255, 228, 0.16));
            animation: ftPdfSpeakEarPulse 1.05s ease-in-out infinite;
          }
          .ft-pdf-speak-ear-svg path,
          .ft-pdf-speak-ear-svg circle {
            fill: none;
            stroke: rgba(255, 224, 142, 0.94);
            stroke-width: 5;
            stroke-linecap: round;
            stroke-linejoin: round;
          }
          .ft-pdf-speak-ear-svg path:nth-child(n+4) {
            stroke: rgba(91, 255, 229, 0.78);
            stroke-width: 3.5;
            animation: ftPdfSpeakListenRings 1.05s ease-in-out infinite;
            transform-origin: 50% 50%;
          }
          .ft-pdf-speak-listen-copy {
            position: relative;
            z-index: 1;
            display: grid;
            gap: 4px;
            min-width: 0;
          }
          .ft-pdf-speak-listen-copy strong {
            color: #ffe6a6;
            font-size: 22px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-listen-copy span {
            color: rgba(202, 255, 244, 0.78);
            font-size: 16px;
          }
          .ft-pdf-speak-ear-meter {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            align-items: end;
            gap: 4px;
            width: min(240px, 100%);
            height: 24px;
            margin-top: 5px;
          }
          .ft-pdf-speak-ear-meter i {
            display: block;
            min-height: 5px;
            border-radius: 999px;
            background: linear-gradient(180deg, #ffe49b, #62ffe5);
            box-shadow: 0 0 12px rgba(255, 216, 118, 0.34);
            animation: ftPdfSpeakMeter 0.82s ease-in-out infinite;
          }
          .ft-pdf-speak-ear-meter i:nth-child(2) { animation-delay: 0.08s; }
          .ft-pdf-speak-ear-meter i:nth-child(3) { animation-delay: 0.16s; }
          .ft-pdf-speak-ear-meter i:nth-child(4) { animation-delay: 0.24s; }
          .ft-pdf-speak-ear-meter i:nth-child(5) { animation-delay: 0.32s; }
          .ft-pdf-speak-ear-meter i:nth-child(6) { animation-delay: 0.4s; }
          .ft-pdf-speak-ear-meter i:nth-child(7) { animation-delay: 0.48s; }
          @keyframes ftPdfSpeakEarPulse {
            0%, 100% { opacity: 0.76; transform: scale(0.96) rotate(-1deg); }
            50% { opacity: 1; transform: scale(1.06) rotate(1deg); }
          }
          @keyframes ftPdfSpeakEarOrbit {
            0% { transform: rotate(0deg) scale(0.98); opacity: 0.42; }
            50% { transform: rotate(180deg) scale(1.04); opacity: 0.9; }
            100% { transform: rotate(360deg) scale(0.98); opacity: 0.42; }
          }
          @keyframes ftPdfSpeakEarSpark {
            0%, 100% { opacity: 0.25; transform: translateY(8px) scale(0.72); }
            50% { opacity: 1; transform: translateY(-8px) scale(1.12); }
          }
          @keyframes ftPdfSpeakMeter {
            0%, 100% { height: 20%; opacity: 0.48; }
            45% { height: 95%; opacity: 1; }
            70% { height: 48%; opacity: 0.78; }
          }
          @keyframes ftPdfSpeakListenGrid {
            0% { background-position: -80px 0, 0 0; }
            100% { background-position: 120px 0, 0 26px; }
          }
          @keyframes ftPdfSpeakListenSweep {
            0% { transform: rotate(0deg) scale(1); }
            100% { transform: rotate(360deg) scale(1); }
          }
          @keyframes ftPdfSpeakCanvasListenGlow {
            0%, 100% { filter: saturate(1) brightness(1); }
            50% { filter: saturate(1.22) brightness(1.14); }
          }
          .ft-pdf-speak-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
          }
          .ft-pdf-speak-control {
            min-height: 52px;
            padding: 0 18px;
            border-radius: 14px;
            border: 1px solid rgba(255, 215, 118, 0.36);
            background: linear-gradient(135deg, rgba(255, 180, 76, 0.16), rgba(55, 255, 223, 0.08));
            color: #fff3ca;
            cursor: pointer;
            font-size: 18px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-control:disabled {
            opacity: 0.45;
            cursor: not-allowed;
          }
          .ft-pdf-speak-control.is-recording {
            color: #ffffff;
            border-color: rgba(255, 105, 96, 0.86);
            box-shadow: 0 0 24px rgba(255, 80, 70, 0.22), inset 0 0 16px rgba(255, 80, 70, 0.12);
          }
          .ft-pdf-speak-mode-toggle {
            min-height: 52px;
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 0 14px;
            border-radius: 16px;
            border: 1px solid rgba(96, 255, 224, 0.34);
            background:
              linear-gradient(135deg, rgba(14, 32, 48, 0.9), rgba(8, 14, 28, 0.82)),
              radial-gradient(circle at 18% 18%, rgba(111, 255, 232, 0.18), transparent 38%);
            color: #eafff9;
            cursor: pointer;
            box-shadow: 0 0 22px rgba(74, 255, 223, 0.13), inset 0 0 18px rgba(74, 255, 223, 0.08);
          }
          .ft-pdf-speak-mode-toggle:disabled {
            opacity: 0.58;
            cursor: not-allowed;
          }
          .ft-pdf-speak-mode-toggle.is-browser {
            border-color: rgba(255, 184, 77, 0.52);
            background:
              linear-gradient(135deg, rgba(43, 25, 12, 0.9), rgba(16, 15, 25, 0.84)),
              radial-gradient(circle at 18% 18%, rgba(255, 184, 77, 0.18), transparent 38%);
            box-shadow: 0 0 22px rgba(255, 184, 77, 0.16), inset 0 0 18px rgba(255, 184, 77, 0.1);
          }
          .ft-pdf-speak-mode-led {
            width: 14px;
            height: 14px;
            border-radius: 999px;
            background: #66ffe8;
            box-shadow: 0 0 0 5px rgba(102, 255, 232, 0.12), 0 0 20px rgba(102, 255, 232, 0.75);
          }
          .ft-pdf-speak-mode-toggle.is-browser .ft-pdf-speak-mode-led {
            background: #ffbd5e;
            box-shadow: 0 0 0 5px rgba(255, 189, 94, 0.12), 0 0 20px rgba(255, 189, 94, 0.72);
          }
          .ft-pdf-speak-mode-copy {
            display: grid;
            gap: 2px;
            text-align: left;
            line-height: 1.05;
          }
          .ft-pdf-speak-mode-copy strong {
            font-size: 12px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-mode-copy small {
            color: rgba(230, 255, 249, 0.76);
            font-size: 10px;
            letter-spacing: 0.04em;
          }
          .ft-pdf-speak-status {
            min-height: 38px;
            color: rgba(224, 255, 249, 0.88);
            font-size: 22px;
            line-height: 1.45;
          }
          .ft-pdf-speak-status.is-error { color: #ffb199; }
          .ft-pdf-speak-status.is-ok { color: #9dffd1; }
          .ft-pdf-speak-feedback-panel {
            min-height: 390px;
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            padding: 16px;
          }
          .ft-pdf-speak-score-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 10px;
          }
          .ft-pdf-speak-score {
            color: #ffd47d;
            font-size: 34px;
            font-weight: 900;
            text-shadow: 0 0 22px rgba(255, 197, 84, 0.2);
          }
          .ft-pdf-speak-transcript {
            display: none;
          }
          .ft-pdf-speak-feedback {
            min-height: 0;
            overflow: hidden;
            display: grid;
            gap: 12px;
            color: rgba(245, 255, 253, 0.94);
            font-size: 28px;
            line-height: 1.6;
          }
          .ft-pdf-speak-line {
            opacity: 0;
            transform: translateY(8px);
            animation: ftPdfSpeakLineIn 420ms cubic-bezier(.18,.86,.22,1) forwards;
          }
          .ft-pdf-speak-section {
            display: grid;
            gap: 8px;
            padding: 10px;
            border: 1px solid rgba(126, 255, 232, 0.14);
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(8, 21, 36, 0.72), rgba(4, 11, 24, 0.52));
          }
          .ft-pdf-speak-section-title {
            color: rgba(255, 218, 138, 0.92);
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 0.14em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-report {
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            gap: 11px;
            height: 100%;
            min-height: 0;
          }
          .ft-pdf-speak-report-notes {
            display: block;
            white-space: normal;
          }
          .ft-pdf-speak-note-part {
            display: inline;
            margin-right: 10px;
            line-height: 1.72;
          }
          .ft-pdf-speak-note-score { color: rgba(184, 255, 241, 0.92); }
          .ft-pdf-speak-note-primary { color: rgba(255, 221, 135, 0.98); }
          .ft-pdf-speak-note-secondary { color: rgba(157, 220, 255, 0.95); }
          .ft-pdf-speak-note-light { color: rgba(179, 255, 196, 0.94); }
          .ft-pdf-speak-note-fix { color: rgba(255, 168, 138, 0.98); }
          .ft-pdf-speak-note-general { color: rgba(237, 255, 250, 0.92); }
          .ft-pdf-speak-feedback-word {
            display: inline-block;
            margin: 0 2px;
            padding: 0 5px;
            border-radius: 8px;
            color: #fff2bf;
            background: rgba(255, 190, 72, 0.14);
            box-shadow: inset 0 -1px 0 rgba(255, 213, 112, 0.5), 0 0 10px rgba(255, 190, 72, 0.1);
            font-weight: 900;
          }
          .ft-pdf-speak-report-line {
            position: relative;
            padding: 11px 12px;
            border: 1px solid rgba(126, 255, 232, 0.13);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(7, 20, 35, 0.74), rgba(4, 10, 22, 0.52)),
              radial-gradient(circle at 0% 50%, rgba(255, 198, 82, 0.1), transparent 36%);
            box-shadow: inset 0 0 18px rgba(85, 255, 230, 0.045);
          }
          .ft-pdf-speak-report-line:last-child {
            min-height: 0;
            overflow: auto;
          }
          .ft-pdf-speak-report-line::before {
            content: "";
            position: absolute;
            left: 0;
            top: 11px;
            bottom: 11px;
            width: 2px;
            border-radius: 4px;
            background: linear-gradient(180deg, rgba(255, 204, 94, 0.95), rgba(87, 255, 225, 0.6));
            box-shadow: 0 0 14px rgba(255, 196, 75, 0.28);
          }
          .ft-pdf-speak-report-label {
            display: inline-block;
            margin-right: 8px;
            color: rgba(255, 218, 138, 0.96);
            font-size: 18px;
            font-weight: 900;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-report-body {
            color: rgba(244, 255, 253, 0.95);
            font-size: 28px;
            line-height: 1.72;
            word-break: break-word;
          }
          .ft-pdf-speak-inline-token {
            display: inline;
            border-radius: 6px;
            padding: 0 2px;
            color: inherit;
            transition: color 160ms ease, background 160ms ease, box-shadow 160ms ease;
          }
          .ft-pdf-speak-inline-token.has-speak-marker {
            display: inline-grid;
            grid-template-rows: 18px 15px auto;
            justify-items: center;
            align-items: center;
            vertical-align: bottom;
            margin: 1px 2px 2px;
            padding: 1px 2px 2px;
            line-height: 1.22;
          }
          .ft-pdf-speak-marker {
            min-width: 16px;
            height: 16px;
            border-radius: 999px;
            display: grid;
            place-items: center;
            font-size: 12px;
            font-weight: 950;
            line-height: 1;
            pointer-events: none;
          }
          .ft-pdf-speak-marker-stress {
            grid-row: 1;
            min-width: 18px;
            height: 18px;
            font-size: 15px;
          }
          .ft-pdf-speak-marker-result {
            grid-row: 2;
          }
          .ft-pdf-speak-marker-word {
            grid-row: 3;
            display: inline-block;
            white-space: nowrap;
          }
          .ft-pdf-speak-inline-token.is-result-ok .ft-pdf-speak-marker-result {
            color: #dffff0;
            background: rgba(44, 255, 151, 0.26);
            border: 1px solid rgba(94, 255, 176, 0.55);
            box-shadow: 0 0 12px rgba(82, 255, 165, 0.24);
          }
          .ft-pdf-speak-inline-token.is-stress-ok .ft-pdf-speak-marker-stress {
            color: #e8fff4;
            background: rgba(44, 255, 151, 0.22);
            border: 1px solid rgba(94, 255, 176, 0.5);
            box-shadow: 0 0 13px rgba(82, 255, 165, 0.22);
          }
          .ft-pdf-speak-inline-token.is-result-bad .ft-pdf-speak-marker-result {
            color: #ffe3dc;
            background: rgba(255, 80, 70, 0.25);
            border: 1px solid rgba(255, 128, 102, 0.58);
            box-shadow: 0 0 12px rgba(255, 82, 70, 0.22);
          }
          .ft-pdf-speak-inline-token.needs-stress-up .ft-pdf-speak-marker-stress {
            color: #ffe7bd;
            background: rgba(255, 170, 55, 0.24);
            border: 1px solid rgba(255, 195, 90, 0.58);
            box-shadow: 0 0 14px rgba(255, 163, 55, 0.24);
          }
          .ft-pdf-speak-inline-token.needs-stress-down .ft-pdf-speak-marker-stress {
            color: #ffe2d9;
            background: rgba(255, 72, 106, 0.24);
            border: 1px solid rgba(255, 112, 142, 0.56);
            box-shadow: 0 0 14px rgba(255, 76, 112, 0.24);
          }
          .ft-pdf-speak-inline-token.is-miss {
            color: #ffd8ca;
            background: transparent;
            box-shadow: inset 0 -2px 0 rgba(255, 111, 86, 0.38);
          }
          .ft-pdf-speak-inline-token.is-ok {
            color: #bfffe0;
            background: transparent;
          }
          .ft-pdf-speak-inline-token.is-extra {
            color: #fff0bf;
            background: transparent;
            box-shadow: inset 0 -2px 0 rgba(255, 195, 75, 0.35);
          }
          .ft-pdf-speak-inline-token.is-primary-stress {
            color: #fff1b8;
            box-shadow: inset 0 -2px 0 rgba(255, 206, 91, 0.78);
          }
          .ft-pdf-speak-inline-token.is-secondary-stress {
            color: #c9fff6;
            box-shadow: inset 0 -2px 0 rgba(89, 255, 226, 0.48);
          }
          .ft-pdf-speak-inline-token.is-speaking {
            color: #ffffff;
            background: linear-gradient(135deg, rgba(255, 195, 75, 0.32), rgba(89, 255, 229, 0.16));
            box-shadow: 0 0 18px rgba(255, 190, 74, 0.32), inset 0 0 12px rgba(255, 245, 193, 0.12);
          }
          .ft-pdf-speak-words {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
          }
          .ft-pdf-speak-word {
            position: relative;
            display: inline-grid;
            gap: 3px;
            padding: 7px 9px;
            border: 1px solid rgba(126, 255, 232, 0.2);
            border-radius: 12px;
            background: rgba(50, 255, 224, 0.07);
            color: #eafffb;
          }
          .ft-pdf-speak-word.is-miss {
            border-color: rgba(255, 122, 92, 0.55);
            background: rgba(255, 94, 67, 0.1);
            color: #ffe1d6;
          }
          .ft-pdf-speak-word.is-ok {
            border-color: rgba(93, 255, 169, 0.42);
            background: rgba(85, 255, 156, 0.08);
          }
          .ft-pdf-speak-word.is-extra {
            border-color: rgba(255, 214, 116, 0.5);
            background: rgba(255, 183, 68, 0.1);
            color: #fff2c7;
          }
          .ft-pdf-speak-word.is-primary-stress {
            box-shadow: inset 0 -2px 0 rgba(255, 206, 91, 0.8), 0 0 18px rgba(255, 188, 75, 0.12);
          }
          .ft-pdf-speak-word.is-secondary-stress {
            box-shadow: inset 0 -2px 0 rgba(89, 255, 226, 0.5);
          }
          .ft-pdf-speak-word.is-speaking {
            border-color: rgba(255, 236, 156, 0.95);
            color: #fff;
            background: linear-gradient(135deg, rgba(255, 195, 75, 0.28), rgba(89, 255, 229, 0.14));
            box-shadow: 0 0 22px rgba(255, 190, 74, 0.28), inset 0 0 14px rgba(255, 245, 193, 0.12);
            transform: translateY(-1px);
          }
          .ft-pdf-speak-word em {
            color: rgba(181, 255, 244, 0.78);
            font-size: 10px;
            font-style: normal;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .ft-pdf-speak-word small {
            color: rgba(255, 214, 130, 0.82);
            font-size: 11px;
          }
          @keyframes ftPdfSpeakLineIn {
            to { opacity: 1; transform: translateY(0); }
          }
          .ft-pdf-voice-select {
            min-height: 38px;
            border-radius: 12px;
            padding: 0 10px;
            border: 1px solid rgba(126, 255, 232, 0.34);
            background: rgba(3, 12, 24, 0.72);
            color: #ecfffd;
          }
          .ft-pdf-unlearned-modal {
            position: fixed;
            inset: 0;
            z-index: 2220;
            display: grid;
            place-items: center;
            padding: 20px;
            background: radial-gradient(circle at 50% 35%, rgba(255, 190, 70, 0.12), transparent 34%), rgba(1, 5, 14, 0.58);
            backdrop-filter: blur(10px);
          }
          .ft-pdf-unlearned-modal.is-hidden {
            display: none;
          }
          .ft-pdf-unlearned-card {
            position: relative;
            width: min(720px, calc(100vw - 28px));
            max-height: min(78vh, 720px);
            display: grid;
            grid-template-rows: auto minmax(0, 1fr) auto;
            border: 1px solid rgba(126, 255, 232, 0.28);
            border-radius: 18px;
            background:
              linear-gradient(135deg, rgba(12, 23, 39, 0.96), rgba(5, 12, 26, 0.94)),
              radial-gradient(circle at 8% 10%, rgba(255, 195, 78, 0.16), transparent 34%);
            box-shadow: 0 30px 90px rgba(0, 0, 0, 0.52), inset 0 0 36px rgba(70, 255, 226, 0.08);
            overflow: hidden;
          }
          .ft-pdf-unlearned-card::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
              linear-gradient(90deg, rgba(255, 196, 80, 0.7), transparent 26%, transparent 74%, rgba(86, 255, 226, 0.56)) top / 100% 1px no-repeat,
              linear-gradient(180deg, rgba(86, 255, 226, 0.36), transparent 48%, rgba(255, 196, 80, 0.32)) right / 1px 100% no-repeat;
          }
          .ft-pdf-unlearned-head,
          .ft-pdf-unlearned-actions {
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 16px 18px;
          }
          .ft-pdf-unlearned-title {
            margin: 0;
            font-size: 22px;
          }
          .ft-pdf-unlearned-subtitle {
            margin: 4px 0 0;
            color: rgba(174, 255, 242, 0.72);
            font-size: 12px;
            letter-spacing: 0.08em;
          }
          .ft-pdf-unlearned-list {
            position: relative;
            z-index: 1;
            overflow: auto;
            display: grid;
            gap: 10px;
            padding: 0 18px 12px;
          }
          .ft-pdf-unlearned-row {
            display: grid;
            grid-template-columns: minmax(110px, 0.45fr) minmax(0, 1fr) auto;
            gap: 12px;
            align-items: center;
            min-height: 64px;
            padding: 11px 12px;
            border: 1px solid rgba(126, 255, 232, 0.18);
            border-radius: 14px;
            background: linear-gradient(135deg, rgba(126, 255, 232, 0.08), rgba(255, 191, 80, 0.08));
          }
          .ft-pdf-unlearned-word {
            color: #fff3c6;
            font-weight: 800;
            letter-spacing: 0.02em;
          }
          .ft-pdf-unlearned-meta {
            color: rgba(236, 255, 251, 0.82);
            font-size: 12px;
            line-height: 1.35;
          }
          .ft-pdf-unlearned-empty {
            padding: 26px 16px;
            text-align: center;
            color: rgba(222, 255, 248, 0.68);
            border: 1px dashed rgba(126, 255, 232, 0.22);
            border-radius: 14px;
          }
          .ft-pdf-navigator::after,
          .ft-pdf-navigator-ring.is-a,
          .ft-pdf-navigator-ring.is-b {
            animation: none !important;
          }
          .ft-pdf-navigator:hover::after,
          .ft-pdf-navigator.is-active::after,
          .ft-pdf-navigator.is-coasting::after {
            animation: ftPdfNavigatorOrbit 8s linear infinite !important;
          }
          .ft-pdf-navigator.is-active::after,
          .ft-pdf-navigator.is-coasting::after {
            animation-duration: 4.8s !important;
          }
          .ft-pdf-navigator:hover .ft-pdf-navigator-ring.is-a,
          .ft-pdf-navigator.is-active .ft-pdf-navigator-ring.is-a,
          .ft-pdf-navigator.is-coasting .ft-pdf-navigator-ring.is-a {
            animation: ftPdfNavigatorRingA 6.2s linear infinite !important;
          }
          .ft-pdf-navigator:hover .ft-pdf-navigator-ring.is-b,
          .ft-pdf-navigator.is-active .ft-pdf-navigator-ring.is-b,
          .ft-pdf-navigator.is-coasting .ft-pdf-navigator-ring.is-b {
            animation: ftPdfNavigatorRingB 5.4s linear infinite reverse !important;
          }
          .ft-pdf-selection.is-visible.is-tech-burst:not(.is-hitbox-only) {
            animation: ftPdfGhostEyeBurstPulse 3s ease-in-out 1 !important;
          }
          .ft-pdf-selection.is-visible.is-tech-burst:not(.is-hitbox-only)::before {
            animation: ftPdfGhostEyeCornerBurst 2.6s ease-in-out 1 !important;
          }
          .ft-pdf-selection.is-visible.is-tech-burst:not(.is-hitbox-only)::after {
            animation: ftPdfGhostEyeElectronBurst 2.6s linear 1 !important;
          }
          .ft-pdf-selection.is-visible:not(.is-hitbox-only):hover {
            animation: ftPdfGhostEyeBurstPulse 3s ease-in-out infinite !important;
          }
          .ft-pdf-selection.is-visible:not(.is-hitbox-only):hover::before {
            animation: ftPdfGhostEyeCornerBurst 3s ease-in-out infinite !important;
          }
          .ft-pdf-selection.is-visible:not(.is-hitbox-only):hover::after {
            animation: ftPdfGhostEyeElectronBurst 3s linear infinite !important;
          }
          html.ft-space-pdf-mode .ft-ai-agent-button:not(.is-booting):not(.is-active):not(:hover):not(:focus-visible)::before,
          html.ft-space-pdf-mode .ft-ai-agent-button:not(.is-booting):not(.is-active):not(:hover):not(:focus-visible)::after,
          html.ft-space-pdf-mode .ft-mobile-animation-button.is-active:not(:hover):not(:focus-visible)::before,
          html.ft-space-pdf-mode .ft-mobile-animation-button.is-active:not(:hover):not(:focus-visible)::after {
            animation: none !important;
          }
          .ft-pdf-ai-notice-layer {
            position: absolute;
            inset: 0;
            z-index: 12;
            pointer-events: none;
          }
          .ft-pdf-ai-notice-layer[hidden] {
            display: none;
          }
          .ft-pdf-ai-notice-hitbox {
            position: absolute;
            display: block;
            padding: 0;
            border: 0;
            border-radius: 10px;
            background: transparent;
            cursor: help;
            opacity: 1;
            pointer-events: auto;
            overflow: hidden;
          }
          .ft-pdf-ai-notice-mini-fireball {
            position: absolute;
            left: var(--notice-mini-start-x, 12%);
            top: var(--notice-mini-start-y, 12%);
            z-index: 2;
            width: clamp(22px, 5vmin, 54px);
            height: clamp(22px, 5vmin, 54px);
            pointer-events: none;
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.42);
            transform-origin: 50% 80%;
            filter: drop-shadow(0 0 10px rgba(255, 145, 64, 0.42));
            animation: ftPdfAiNoticeMiniFireball var(--notice-mini-cycle, 12000ms) cubic-bezier(0.2, 0.82, 0.2, 1) var(--notice-mini-delay, 0ms) infinite;
          }
          .ft-pdf-ai-notice-mini-fireball .ft-world-fireball {
            width: 100%;
            height: 100%;
            animation: ftPdfAiNoticeMiniWiggle 720ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-mini-fireball .ft-world-fireball::before {
            width: 42%;
            height: 58%;
            left: 12%;
            top: -34%;
          }
          .ft-pdf-ai-notice-mini-fireball .ft-world-fireball::after {
            width: 34%;
            height: 48%;
            right: 9%;
            top: -26%;
          }
          .ft-pdf-ai-notice-hitbox:hover,
          .ft-pdf-ai-notice-hitbox:focus-visible {
            opacity: 1;
            background:
              radial-gradient(circle at 50% 50%, rgba(255, 225, 128, 0.13), transparent 58%),
              linear-gradient(135deg, rgba(126, 255, 232, 0.08), rgba(255, 211, 126, 0.08));
            box-shadow:
              inset 0 0 0 1px rgba(126, 255, 232, 0.42),
              0 0 18px rgba(255, 211, 126, 0.28);
          }
          .ft-pdf-ai-notice-hitbox:hover .ft-pdf-ai-notice-mini-fireball,
          .ft-pdf-ai-notice-hitbox:focus-visible .ft-pdf-ai-notice-mini-fireball {
            left: 18%;
            top: 18%;
            opacity: 1;
            animation: ftPdfAiNoticeMiniHover 900ms ease-in-out infinite;
            transform: translate(-50%, -50%) scale(0.94);
          }
          .ft-pdf-ai-notice-layer.is-admin-visible .ft-pdf-ai-notice-hitbox {
            opacity: 1;
            border: 1px solid rgba(126, 255, 232, 0.62);
            background:
              linear-gradient(135deg, rgba(72, 255, 230, 0.08), rgba(255, 211, 126, 0.08)),
              repeating-linear-gradient(90deg, rgba(126,255,232,0.16) 0 1px, transparent 1px 9px);
            box-shadow:
              0 0 0 1px rgba(3, 9, 18, 0.72),
              0 0 22px rgba(70, 240, 215, 0.28),
              inset 0 0 22px rgba(255, 211, 126, 0.08);
            animation: ftPdfAiNoticeRegionFloat 2.8s ease-in-out infinite;
          }
          .ft-pdf-ai-notice-layer.is-admin-visible .ft-pdf-ai-notice-hitbox::before {
            content: attr(data-notice-index);
            position: absolute;
            left: 7px;
            top: 7px;
            min-width: 24px;
            height: 22px;
            display: grid;
            place-items: center;
            border-radius: 8px;
            background: rgba(8, 19, 30, 0.86);
            color: #aafff1;
            font: 900 11px/1 "Orbitron", "Inter", sans-serif;
            box-shadow: 0 0 16px rgba(126, 255, 232, 0.28);
          }
          .ft-pdf-ai-notice-layer.is-admin-visible .ft-pdf-ai-notice-hitbox::after {
            content: "";
            position: absolute;
            inset: 5px;
            border-radius: 8px;
            border: 1px dashed rgba(255, 225, 128, 0.45);
            pointer-events: auto;
          }
          .ft-pdf-ai-notice-layer.is-admin-visible .ft-pdf-ai-notice-hitbox:hover,
          .ft-pdf-ai-notice-layer.is-admin-visible .ft-pdf-ai-notice-hitbox.is-active {
            border-color: rgba(255, 225, 128, 0.9);
            background:
              linear-gradient(135deg, rgba(255, 225, 128, 0.12), rgba(126, 255, 232, 0.12)),
              repeating-linear-gradient(90deg, rgba(255,225,128,0.2) 0 1px, transparent 1px 9px);
            box-shadow:
              0 0 0 1px rgba(3, 9, 18, 0.82),
              0 0 32px rgba(255, 211, 126, 0.36),
              inset 0 0 28px rgba(126, 255, 232, 0.12);
          }
          .ft-pdf-ai-notice-hitbox:focus-visible {
            opacity: 1;
            outline: 2px solid rgba(255, 211, 126, 0.92);
            outline-offset: 2px;
            background: rgba(255, 211, 126, 0.08);
          }
          .ft-pdf-space.is-pen-active .ft-pdf-ai-notice-layer,
          .ft-pdf-space.is-text-active .ft-pdf-ai-notice-layer,
          .ft-pdf-space.is-eraser-active .ft-pdf-ai-notice-layer,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-ai-notice-layer,
          .ft-pdf-space.is-pen-active .ft-pdf-ai-notice-hitbox,
          .ft-pdf-space.is-text-active .ft-pdf-ai-notice-hitbox,
          .ft-pdf-space.is-eraser-active .ft-pdf-ai-notice-hitbox,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-ai-notice-hitbox,
          .ft-pdf-space.is-pen-active .ft-pdf-ai-notice-hitbox::before,
          .ft-pdf-space.is-text-active .ft-pdf-ai-notice-hitbox::before,
          .ft-pdf-space.is-eraser-active .ft-pdf-ai-notice-hitbox::before,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-ai-notice-hitbox::before,
          .ft-pdf-space.is-pen-active .ft-pdf-ai-notice-hitbox::after,
          .ft-pdf-space.is-text-active .ft-pdf-ai-notice-hitbox::after,
          .ft-pdf-space.is-eraser-active .ft-pdf-ai-notice-hitbox::after,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-ai-notice-hitbox::after,
          .ft-pdf-space.is-pen-active .ft-pdf-ai-notice-mini-fireball,
          .ft-pdf-space.is-text-active .ft-pdf-ai-notice-mini-fireball,
          .ft-pdf-space.is-eraser-active .ft-pdf-ai-notice-mini-fireball,
          .ft-pdf-space.is-audio-insert-active .ft-pdf-ai-notice-mini-fireball {
            pointer-events: none !important;
          }
          @keyframes ftPdfAiNoticeMiniFireball {
            0%, 38% {
              left: var(--notice-mini-start-x, 12%);
              top: var(--notice-mini-start-y, 12%);
              opacity: 0;
              transform: translate(-50%, -50%) scale(0.38) rotate(-8deg);
            }
            43% {
              opacity: 1;
              transform: translate(-50%, -50%) scale(0.86) rotate(4deg);
            }
            56% {
              left: var(--notice-mini-mid-x, 50%);
              top: var(--notice-mini-mid-y, 44%);
              opacity: 1;
              transform: translate(-50%, -50%) scale(1) rotate(-5deg);
            }
            70% {
              left: var(--notice-mini-end-x, 82%);
              top: var(--notice-mini-end-y, 72%);
              opacity: 1;
              transform: translate(-50%, -50%) scale(0.9) rotate(6deg);
            }
            78%, 100% {
              left: var(--notice-mini-end-x, 82%);
              top: var(--notice-mini-end-y, 72%);
              opacity: 0;
              transform: translate(-50%, -50%) scale(0.36) rotate(10deg);
            }
          }
          @keyframes ftPdfAiNoticeMiniWiggle {
            0%, 100% { transform: translateY(0) rotate(-4deg) scaleX(var(--world-facing, 1)); }
            50% { transform: translateY(-4px) rotate(5deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiNoticeMiniHover {
            0%, 100% { transform: translate(-50%, -50%) scale(0.9) rotate(-5deg); }
            50% { transform: translate(-50%, -58%) scale(1) rotate(6deg); }
          }
          .ft-pdf-ai-notice-modal {
            position: fixed;
            inset: 0;
            z-index: 2147483300;
            display: grid;
            place-items: center;
            padding: 24px;
            background: rgba(2, 6, 14, 0.46);
            backdrop-filter: blur(10px);
            overflow: auto;
          }
          .ft-pdf-ai-question-modal {
            align-items: start;
            place-items: start center;
            padding: 76px 5px 24px;
          }
          .ft-pdf-ai-notice-modal.is-hidden {
            display: none;
          }
          .ft-pdf-ai-notice-card {
            width: min(920px, calc(100vw - 32px));
            max-height: calc(100vh - 42px);
            display: grid;
            grid-template-rows: auto minmax(0, 1fr) auto;
            gap: 14px;
            padding: 18px;
            overflow: hidden;
            border: 1px solid rgba(126, 255, 232, 0.34);
            border-radius: 18px;
            background:
              linear-gradient(135deg, rgba(9, 20, 34, 0.98), rgba(16, 32, 48, 0.94)),
              radial-gradient(circle at 12% 10%, rgba(255, 194, 96, 0.18), transparent 34%);
            box-shadow: 0 28px 90px rgba(0, 0, 0, 0.58), inset 0 0 28px rgba(78, 245, 218, 0.08);
          }
          .ft-pdf-ai-question-card {
            width: calc(100vw - 10px);
            max-height: calc(100vh - 104px);
            overflow: hidden;
            grid-template-rows: auto minmax(0, 1fr) auto;
          }
          @media (max-width: 720px) {
            .ft-pdf-ai-question-modal {
              padding: 68px 5px 12px;
            }
            .ft-pdf-ai-question-card {
              width: calc(100vw - 10px);
              max-height: calc(100vh - 86px);
            }
          }
          .ft-pdf-ai-notice-head,
          .ft-pdf-ai-notice-actions,
          .ft-pdf-ai-notice-history-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
          }
          .ft-pdf-ai-notice-head h3 {
            margin: 4px 0 0;
            color: #fff;
            font-size: 22px;
            line-height: 1.1;
          }
          .ft-pdf-ai-notice-grid {
            min-height: 0;
            display: grid;
            grid-template-columns: minmax(260px, 0.95fr) minmax(280px, 1.05fr);
            gap: 14px;
            overflow: auto;
            padding-right: 4px;
          }
          .ft-pdf-ai-notice-editor,
          .ft-pdf-ai-notice-history {
            min-height: 0;
            display: grid;
            gap: 9px;
          }
          .ft-pdf-ai-notice-editor > span,
          .ft-pdf-ai-notice-history-head span {
            color: rgba(222, 255, 248, 0.82);
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .ft-pdf-ai-notice-editor textarea {
            min-height: 340px;
            resize: vertical;
            padding: 14px;
            border: 1px solid rgba(126, 255, 232, 0.28);
            border-radius: 14px;
            background: rgba(4, 11, 20, 0.72);
            color: #f3fffd;
            line-height: 1.5;
            outline: none;
          }
          .ft-pdf-ai-notice-voice-text,
          .ft-pdf-ai-notice-display-mode {
            min-height: 44px;
            resize: none;
            padding: 10px 12px;
            border: 1px solid rgba(126, 255, 232, 0.28);
            border-radius: 12px;
            background: rgba(4, 11, 20, 0.72);
            color: #f3fffd;
            line-height: 1.35;
            outline: none;
          }
          .ft-pdf-ai-notice-voice-text {
            min-height: 44px;
            resize: none;
          }
          .ft-pdf-ai-notice-display-mode {
            min-height: 44px;
            resize: none;
          }
          .ft-pdf-ai-notice-editor textarea:focus,
          .ft-pdf-ai-notice-voice-text:focus,
          .ft-pdf-ai-notice-display-mode:focus {
            border-color: rgba(255, 211, 126, 0.82);
            box-shadow: 0 0 0 3px rgba(255, 211, 126, 0.12);
          }
          .ft-pdf-ai-notice-history-list {
            min-height: 0;
            max-height: 390px;
            overflow: auto;
            display: grid;
            align-content: start;
            gap: 8px;
            padding-right: 4px;
          }
          .ft-pdf-ai-notice-history-row {
            display: grid;
            gap: 5px;
            width: 100%;
            padding: 11px 12px;
            border: 1px solid rgba(126, 255, 232, 0.22);
            border-radius: 12px;
            background: rgba(7, 18, 31, 0.78);
            color: #ecfffd;
            text-align: left;
            cursor: pointer;
          }
          .ft-pdf-ai-notice-history-row:hover {
            border-color: rgba(255, 211, 126, 0.62);
            transform: translateY(-1px);
          }
          .ft-pdf-ai-notice-history-row strong {
            font-size: 13px;
            color: #ffffff;
          }
          .ft-pdf-ai-notice-history-row span,
          .ft-pdf-ai-notice-history-empty,
          .ft-pdf-ai-notice-status {
            color: rgba(222, 255, 248, 0.72);
            font-size: 12px;
            line-height: 1.45;
            white-space: pre-line;
          }
          .ft-pdf-ai-notice-status[data-tone="ok"] { color: #8dffd9; }
          .ft-pdf-ai-notice-status[data-tone="error"] { color: #ff9fb2; }
          .ft-pdf-ai-question-grid {
            min-height: 0;
            overflow: auto;
            overscroll-behavior: contain;
            padding-right: 4px;
            display: grid;
            grid-template-columns: minmax(190px, 0.56fr) minmax(260px, 0.9fr) minmax(320px, 1.1fr);
            gap: 14px;
          }
          .ft-pdf-ai-question-node-panel,
          .ft-pdf-ai-question-answer-editor,
          .ft-pdf-ai-question-answer-list {
            min-height: 0;
            display: grid;
            align-content: start;
            gap: 10px;
          }
          .ft-pdf-ai-question-node-list {
            min-height: 0;
            max-height: 420px;
            overflow: auto;
            display: grid;
            align-content: start;
            gap: 8px;
            padding-right: 4px;
          }
          .ft-pdf-ai-question-node-list.is-right-drag-active {
            cursor: grabbing;
          }
          .ft-pdf-ai-question-node-actions {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 6px;
            min-width: 0;
            flex-wrap: wrap;
          }
          .ft-pdf-ai-question-node-actions .ft-pdf-button {
            min-height: 30px;
            padding: 6px 9px;
            font-size: 11px;
          }
          .ft-pdf-ai-question-node-nav {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr)) minmax(58px, 0.85fr) repeat(2, minmax(0, 1fr));
            gap: 6px;
            min-width: 0;
            padding: 8px;
            border: 1px solid rgba(126, 255, 232, 0.16);
            border-radius: 10px;
            background: rgba(5, 18, 28, 0.62);
          }
          .ft-pdf-ai-question-node-nav .ft-pdf-button {
            min-width: 0;
            min-height: 30px;
            padding: 6px 7px;
            font-size: 10px;
          }
          .ft-pdf-ai-question-node-nav input {
            width: 100%;
            min-width: 0;
            min-height: 30px;
            border: 1px solid rgba(126, 255, 232, 0.26);
            border-radius: 8px;
            background: rgba(8, 16, 28, 0.9);
            color: #f3fffd;
            text-align: center;
            font-size: 12px;
            font-weight: 900;
            outline: none;
          }
          .ft-pdf-ai-question-node-nav input:focus {
            border-color: rgba(255, 211, 126, 0.82);
            box-shadow: 0 0 0 3px rgba(255, 211, 126, 0.12);
          }
          .ft-pdf-ai-question-random-row,
          .ft-pdf-ai-question-region-name-row {
            display: grid;
            gap: 6px;
            padding: 9px;
            border: 1px solid rgba(255, 166, 110, 0.22);
            border-radius: 12px;
            background:
              linear-gradient(135deg, rgba(54, 9, 16, 0.7), rgba(14, 20, 31, 0.64)),
              radial-gradient(circle at 0 0, rgba(255, 174, 100, 0.13), transparent 44%);
          }
          .ft-pdf-ai-question-region-name-row {
            border-color: rgba(126, 255, 232, 0.2);
            background:
              linear-gradient(135deg, rgba(7, 31, 35, 0.72), rgba(14, 20, 31, 0.64)),
              radial-gradient(circle at 100% 0, rgba(126, 255, 232, 0.12), transparent 44%);
          }
          .ft-pdf-ai-question-random-row span,
          .ft-pdf-ai-question-region-name-row span {
            color: rgba(255, 229, 198, 0.88);
            font-size: 11px;
            font-weight: 850;
            text-transform: uppercase;
          }
          .ft-pdf-ai-question-region-name-row span {
            color: rgba(218, 255, 252, 0.9);
          }
          .ft-pdf-ai-question-random-row select,
          .ft-pdf-ai-question-region-name-row input {
            width: 100%;
            min-width: 0;
            border: 1px solid rgba(255, 213, 142, 0.28);
            border-radius: 9px;
            background: rgba(11, 18, 29, 0.92);
            color: #fff7e7;
            padding: 7px 9px;
            font-weight: 800;
          }
          .ft-pdf-ai-question-region-name-row input {
            border-color: rgba(126, 255, 232, 0.28);
            color: #edfffd;
          }
          .ft-pdf-ai-question-region-name-row input:focus {
            border-color: rgba(126, 255, 232, 0.78);
            box-shadow: 0 0 0 3px rgba(126, 255, 232, 0.12);
            outline: none;
          }
          .ft-pdf-ai-question-pin-row {
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
            padding: 8px 9px;
            border: 1px solid rgba(74, 255, 183, 0.24);
            border-radius: 9px;
            background: rgba(10, 32, 30, 0.62);
            color: rgba(218, 255, 244, 0.92);
            font-size: 12px;
            font-weight: 850;
          }
          .ft-pdf-ai-question-pin-row input {
            width: 17px;
            height: 17px;
            accent-color: #46ffc0;
            flex: 0 0 auto;
          }
          .ft-pdf-ai-question-pin-row span {
            min-width: 0;
            overflow-wrap: anywhere;
          }
          .ft-pdf-ai-question-editor-fields {
            align-content: start;
            gap: 9px;
          }
          .ft-pdf-ai-question-field {
            display: grid;
            gap: 6px;
            min-width: 0;
          }
          .ft-pdf-ai-question-field-label {
            min-width: 0;
          }
          .ft-pdf-ai-question-editor-fields textarea {
            box-sizing: border-box;
            width: 100%;
            min-width: 0;
            max-width: 100%;
          }
          .ft-pdf-ai-question-editor-fields #ft-pdf-ai-question-input {
            min-height: 82px;
          }
          .ft-pdf-ai-question-editor-fields #ft-pdf-ai-question-intro {
            min-height: 72px;
          }
          .ft-pdf-ai-question-node {
            display: grid;
            gap: 5px;
            width: 100%;
            padding: 10px 11px;
            border: 1px solid rgba(126, 255, 232, 0.22);
            border-radius: 12px;
            background:
              linear-gradient(135deg, rgba(7, 18, 31, 0.86), rgba(20, 10, 28, 0.7)),
              radial-gradient(circle at 100% 0, rgba(255, 211, 126, 0.1), transparent 42%);
            color: #ecfffd;
            text-align: left;
            cursor: pointer;
            transition: transform 140ms ease, opacity 140ms ease, border-color 140ms ease, box-shadow 140ms ease, filter 140ms ease;
          }
          .ft-pdf-ai-question-node.is-dragging {
            opacity: 0.36;
            transform: translateX(8px) scale(0.965);
            filter: saturate(0.75);
          }
          .ft-pdf-ai-question-node.is-right-dragging {
            border-style: dashed;
            border-color: rgba(255, 218, 153, 0.6);
            box-shadow:
              10px 10px 0 rgba(0, 0, 0, 0.2),
              0 0 22px rgba(255, 218, 153, 0.13);
          }
          .ft-pdf-ai-question-node.is-drop-target {
            border-color: #46ffc0;
            transform: translateY(7px);
            box-shadow:
              0 -7px 0 rgba(70, 255, 192, 0.86),
              0 0 0 1px rgba(74, 255, 183, 0.3),
              0 0 20px rgba(74, 255, 183, 0.16);
          }
          .ft-pdf-ai-question-node.is-goto-highlight {
            border: 2px dashed #5b0000;
            box-shadow:
              0 0 0 2px rgba(255, 218, 153, 0.16),
              0 0 18px rgba(91, 0, 0, 0.34),
              inset 0 0 16px rgba(91, 0, 0, 0.18);
          }
          .ft-pdf-ai-question-node:hover,
          .ft-pdf-ai-question-node.is-active {
            border-color: rgba(255, 211, 126, 0.68);
            box-shadow:
              0 0 0 1px rgba(255, 211, 126, 0.08),
              inset 0 0 18px rgba(255, 211, 126, 0.08);
          }
          .ft-pdf-ai-question-node.is-pinned {
            border-color: rgba(74, 255, 183, 0.88);
            box-shadow:
              0 0 0 1px rgba(74, 255, 183, 0.24),
              0 0 18px rgba(74, 255, 183, 0.14),
              inset 0 0 18px rgba(74, 255, 183, 0.08);
          }
          .ft-pdf-ai-question-node.is-pinned.is-active,
          .ft-pdf-ai-question-node.is-pinned:hover {
            border-color: #46ffc0;
            box-shadow:
              0 0 0 1px rgba(74, 255, 183, 0.34),
              0 0 20px rgba(74, 255, 183, 0.18),
              inset 0 0 18px rgba(255, 211, 126, 0.1);
          }
          .ft-pdf-ai-question-node strong {
            display: flex;
            align-items: center;
            gap: 6px;
            min-width: 0;
            color: #fff;
            font-size: 13px;
          }
          .ft-pdf-ai-question-node-title {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .ft-pdf-ai-question-node strong em {
            flex: 0 0 auto;
            padding: 2px 5px;
            border: 1px solid rgba(74, 255, 183, 0.5);
            border-radius: 6px;
            background: rgba(32, 126, 96, 0.28);
            color: #b9ffe8;
            font-size: 9px;
            font-style: normal;
            font-weight: 950;
            letter-spacing: 0;
          }
          .ft-pdf-ai-question-node > span {
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            color: rgba(222, 255, 248, 0.72);
            font-size: 12px;
            line-height: 1.35;
          }
          .ft-pdf-ai-question-image-editor {
            display: grid;
            gap: 8px;
            min-width: 0;
            padding: 9px;
            border: 1px solid rgba(255, 178, 116, 0.2);
            border-radius: 8px;
            background: linear-gradient(135deg, rgba(35, 4, 10, 0.74), rgba(8, 18, 30, 0.68));
          }
          .ft-pdf-ai-question-image-src {
            width: 100%;
            min-width: 0;
            border: 1px solid rgba(255, 213, 142, 0.28);
            border-radius: 8px;
            background: rgba(11, 18, 29, 0.92);
            color: #fff7e7;
            padding: 8px 9px;
            font-size: 12px;
            font-weight: 750;
          }
          .ft-pdf-ai-question-image-tools {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
          }
          .ft-pdf-ai-question-image-preview {
            margin: 0;
            min-height: 86px;
            max-height: 180px;
            border: 1px solid rgba(126, 255, 232, 0.2);
            border-radius: 8px;
            background:
              linear-gradient(135deg, rgba(7, 18, 31, 0.86), rgba(40, 6, 13, 0.72)),
              radial-gradient(circle at 100% 0, rgba(255, 211, 126, 0.1), transparent 42%);
            overflow: hidden;
            display: grid;
            place-items: center;
          }
          .ft-pdf-ai-question-image-preview[hidden] {
            display: none;
          }
          .ft-pdf-ai-question-image-preview img {
            display: block;
            width: 100%;
            max-height: 180px;
            object-fit: contain;
          }
          .ft-pdf-ai-question-image-preview.is-broken {
            border-color: rgba(255, 94, 118, 0.56);
          }
          .ft-pdf-ai-question-highlight-palette {
            position: fixed;
            z-index: 2600;
            width: 264px;
            padding: 10px;
            border: 1px solid rgba(255, 218, 160, 0.38);
            border-radius: 12px;
            background:
              linear-gradient(145deg, rgba(31, 6, 14, 0.96), rgba(8, 18, 30, 0.96)),
              radial-gradient(circle at 0 0, rgba(255, 231, 138, 0.14), transparent 45%);
            box-shadow: 0 18px 42px rgba(0, 0, 0, 0.46), inset 0 0 0 1px rgba(255,255,255,0.04);
            color: #fff5de;
          }
          .ft-pdf-ai-question-highlight-palette strong {
            display: block;
            margin-bottom: 8px;
            color: rgba(255, 238, 205, 0.86);
            font-size: 11px;
            font-weight: 950;
            text-transform: uppercase;
          }
          .ft-pdf-ai-question-highlight-swatches,
          .ft-pdf-ai-question-highlight-saved {
            display: grid;
            grid-template-columns: repeat(10, 1fr);
            gap: 7px;
          }
          .ft-pdf-ai-question-highlight-saved {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.1);
          }
          .ft-pdf-ai-question-highlight-saved:empty {
            display: none;
          }
          .ft-pdf-ai-question-highlight-custom {
            display: grid;
            grid-template-columns: 44px 1fr 1fr;
            gap: 7px;
            margin-top: 9px;
          }
          .ft-pdf-ai-notice-format-row {
            display: grid;
            grid-template-columns: 34px 34px minmax(84px, 1fr) 58px;
            gap: 7px;
            margin: 0 0 9px;
          }
          .ft-pdf-ai-notice-format-row select {
            min-width: 0;
            height: 30px;
            padding: 0 8px;
            border: 1px solid rgba(255,255,255,0.22);
            border-radius: 9px;
            background: rgba(255,255,255,0.08);
            color: #fff5de;
            font-size: 11px;
            font-weight: 850;
            outline: none;
          }
          .ft-pdf-ai-question-highlight-custom input[type="color"] {
            width: 44px;
            height: 30px;
            padding: 0;
            border: 1px solid rgba(255,255,255,0.22);
            border-radius: 9px;
            background: rgba(255,255,255,0.08);
            cursor: pointer;
          }
          .ft-pdf-ai-question-highlight-palette button {
            min-width: 0;
            width: 100%;
            height: 30px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 9px;
            background:
              radial-gradient(circle at 34% 28%, rgba(255,255,255,0.56), transparent 26%),
              linear-gradient(135deg, var(--swatch), rgba(5, 8, 18, 0.94));
            box-shadow: 0 6px 14px rgba(0,0,0,0.28), 0 0 16px rgba(255, 231, 138, 0.12);
            cursor: pointer;
          }
          .ft-pdf-ai-question-highlight-custom button {
            color: #fff5de;
            font-size: 11px;
            font-weight: 900;
            background:
              linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04)),
              linear-gradient(135deg, rgba(139,0,22,0.42), rgba(12,22,36,0.78));
          }
          .ft-pdf-ai-notice-format-row button {
            color: #fff5de;
            font-size: 12px;
            font-weight: 950;
            background:
              linear-gradient(145deg, rgba(255,255,255,0.14), rgba(255,255,255,0.045)),
              linear-gradient(135deg, rgba(255, 231, 138, 0.18), rgba(12,22,36,0.82));
          }
          .ft-pdf-ai-question-highlight-palette button:hover,
          .ft-pdf-ai-question-highlight-palette button:focus-visible {
            transform: translateY(-1px) scale(1.06);
            outline: none;
            border-color: rgba(255, 231, 138, 0.72);
          }
          .ft-pdf-ai-question-highlight-field {
            position: relative;
            display: block;
            min-height: 40px;
            text-transform: none;
            letter-spacing: 0;
          }
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-field.is-notice {
            min-height: 340px;
          }
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-field.is-notice-focus {
            min-height: 142px;
            height: 142px;
            align-self: start;
            overflow: hidden;
          }
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-field.is-notice-focus textarea.ft-pdf-ai-notice-focus-text,
          .ft-pdf-ai-notice-editor textarea#ft-pdf-ai-notice-focus-text {
            min-height: 0 !important;
            height: 142px !important;
            max-height: 142px !important;
            resize: none !important;
            overflow-y: auto;
          }
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-field,
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-field span {
            color: inherit;
            font-size: inherit;
            font-weight: inherit;
            letter-spacing: 0;
            text-transform: none;
          }
          .ft-pdf-ai-question-highlight-field textarea {
            position: relative;
            z-index: 2;
            width: 100%;
          }
          .ft-pdf-ai-question-highlight-field.has-highlight textarea,
          .ft-pdf-ai-question-highlight-field.has-highlight textarea.ft-pdf-ai-question-intro-text {
            background: rgba(3, 10, 18, 0.72);
            color: transparent !important;
            -webkit-text-fill-color: transparent !important;
            caret-color: #ffe78a;
            text-shadow: none !important;
          }
          .ft-pdf-ai-question-highlight-field.has-highlight textarea::selection {
            color: transparent;
            -webkit-text-fill-color: transparent;
            background: rgba(126, 255, 232, 0.72);
          }
          .ft-pdf-ai-question-highlight-overlay {
            position: absolute;
            z-index: 3;
            inset: 0;
            display: block;
            pointer-events: none;
            padding: 14px;
            border: 1px solid transparent;
            color: transparent;
            font: inherit;
            font-size: 13px;
            font-weight: 500;
            line-height: 1.5;
            white-space: pre-wrap;
            overflow: hidden;
            overflow-wrap: anywhere;
            text-shadow: none;
          }
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-overlay {
            color: #f3fffd;
            -webkit-text-fill-color: currentColor;
          }
          .ft-pdf-ai-question-highlight-field.is-intro .ft-pdf-ai-question-highlight-overlay {
            padding: 10px 11px;
            line-height: 1.45;
          }
          .ft-pdf-ai-question-highlight-overlay .ft-pdf-ai-question-highlight,
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-overlay .ft-pdf-ai-question-highlight,
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-overlay .ft-pdf-ai-notice-highlight {
            display: inline;
            color: var(--ai-hl);
            font-weight: inherit;
            padding: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            text-shadow: 0 0 7px color-mix(in srgb, var(--ai-hl) 38%, transparent);
            -webkit-box-decoration-break: clone;
            box-decoration-break: clone;
          }
          .ft-pdf-ai-notice-editor .ft-pdf-ai-question-highlight-overlay .ft-pdf-ai-notice-highlight {
            color: var(--ai-notice-hl, #ffe78a);
            text-shadow: 0 0 7px color-mix(in srgb, var(--ai-notice-hl, #ffe78a) 38%, transparent);
          }
          .ft-pdf-ai-question-text-preview {
            min-height: 0;
            margin: 6px 0 2px;
            padding: 7px 9px;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            background:
              linear-gradient(145deg, rgba(255,255,255,0.07), rgba(255,255,255,0.025)),
              rgba(5, 10, 18, 0.32);
            color: rgba(225, 242, 255, 0.86);
            font-size: 12px;
            line-height: 1.45;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
          }
          .ft-pdf-ai-question-text-preview.is-empty {
            display: none;
          }
          .ft-pdf-ai-question-answer-list {
            max-height: 420px;
            overflow: auto;
            padding-right: 4px;
          }
          .ft-pdf-ai-question-answer-row {
            display: grid;
            gap: 8px;
            padding: 10px;
            border: 1px solid rgba(126, 255, 232, 0.2);
            border-radius: 14px;
            background: rgba(5, 14, 24, 0.72);
          }
          .ft-pdf-ai-question-answer-row.is-correct {
            border-color: rgba(122, 255, 181, 0.46);
            box-shadow: inset 0 0 18px rgba(122, 255, 181, 0.08);
          }
          .ft-pdf-ai-question-answer-main,
          .ft-pdf-ai-question-explain-tools {
            display: flex;
            align-items: stretch;
            gap: 8px;
          }
          .ft-pdf-ai-question-explain-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            color: #ffe78a;
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 0;
            text-transform: uppercase;
          }
          .ft-pdf-ai-question-explain-close {
            display: grid;
            place-items: center;
            width: 24px;
            height: 24px;
            border: 1px solid rgba(255, 231, 138, 0.32);
            border-radius: 8px;
            background: rgba(255, 231, 138, 0.12);
            color: #ffe78a;
            font-weight: 950;
            cursor: pointer;
          }
          .ft-pdf-ai-question-answer-text,
          .ft-pdf-ai-question-explain-text,
          .ft-pdf-ai-question-intro-text,
          .ft-pdf-ai-question-intro-voice,
          .ft-pdf-ai-question-explain-mode,
          .ft-pdf-ai-question-explain-voice {
            width: 100%;
            min-width: 0;
            border: 1px solid rgba(126, 255, 232, 0.22);
            border-radius: 12px;
            background: rgba(3, 10, 18, 0.76);
            color: #f3fffd;
            outline: none;
          }
          .ft-pdf-ai-question-answer-text,
          .ft-pdf-ai-question-explain-text,
          .ft-pdf-ai-question-intro-text {
            padding: 10px 11px;
            min-height: 40px;
            resize: none;
            overflow: hidden;
            line-height: 1.45;
          }
          .ft-pdf-ai-question-card .ft-pdf-ai-notice-editor textarea {
            min-height: 56px;
            resize: none;
            overflow: hidden;
          }
          .ft-pdf-ai-question-intro-text {
            min-height: 52px;
          }
          .ft-pdf-ai-question-highlight-field.has-highlight .ft-pdf-ai-question-intro-text {
            color: transparent !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: none !important;
          }
          .ft-pdf-ai-question-intro-voice,
          .ft-pdf-ai-question-explain-mode,
          .ft-pdf-ai-question-explain-voice {
            min-height: 36px;
            padding: 7px 9px;
          }
          .ft-pdf-ai-question-correct,
          .ft-pdf-ai-question-remove {
            flex: 0 0 auto;
            min-width: 64px;
            border: 1px solid rgba(126, 255, 232, 0.24);
            border-radius: 11px;
            background: rgba(9, 22, 36, 0.88);
            color: #dffdf7;
            font-weight: 800;
            cursor: pointer;
          }
          .ft-pdf-ai-question-correct[aria-pressed="true"] {
            border-color: rgba(122, 255, 181, 0.7);
            color: #8dffd9;
            background: rgba(23, 70, 45, 0.52);
          }
          .ft-pdf-ai-question-remove {
            min-width: 32px;
            color: #ffb8c2;
          }
          .ft-pdf-ai-question-explain {
            display: none;
          }
          .ft-pdf-ai-question-answer-row.is-expanded .ft-pdf-ai-question-explain {
            position: fixed;
            left: var(--ai-question-popup-left, 50vw);
            top: var(--ai-question-popup-top, 20vh);
            z-index: 2385;
            width: min(var(--ai-question-popup-width, 340px), calc(100vw - 24px));
            display: grid;
            gap: 8px;
            padding: 11px;
            border: 1px solid rgba(126, 255, 232, 0.42);
            border-radius: 14px;
            background:
              linear-gradient(135deg, rgba(5, 16, 28, 0.96), rgba(20, 24, 43, 0.94)),
              repeating-linear-gradient(0deg, rgba(255,255,255,0.035) 0 1px, transparent 1px 8px);
            box-shadow:
              0 22px 54px rgba(0, 0, 0, 0.44),
              inset 0 0 24px rgba(126, 255, 232, 0.08);
            animation: ftPdfAiExplainPopupIn 180ms cubic-bezier(.16,.86,.2,1) both;
          }
          .ft-pdf-ai-question-answer-row.is-expanded .ft-pdf-ai-question-explain::before {
            content: "";
            position: absolute;
            left: -8px;
            top: 22px;
            width: 14px;
            height: 14px;
            border-left: 1px solid rgba(126, 255, 232, 0.42);
            border-bottom: 1px solid rgba(126, 255, 232, 0.42);
            background: rgba(7, 18, 31, 0.96);
            transform: rotate(45deg);
          }
          @keyframes ftPdfAiExplainPopupIn {
            from { opacity: 0; transform: translate3d(8px, -6px, 0) scale(0.98); }
            to { opacity: 1; transform: translate3d(0, 0, 0) scale(1); }
          }
          .ft-pdf-ai-question-region {
            position: absolute;
            overflow: visible;
            pointer-events: none;
            z-index: 3;
          }
          .ft-pdf-ai-question-clickbox {
            position: absolute;
            z-index: 4;
            display: block;
            padding: 0;
            border: 0;
            border-radius: 10px;
            background: transparent;
            cursor: pointer;
            pointer-events: auto;
          }
          .ft-pdf-ai-question-clickbox:focus-visible {
            outline: 2px solid rgba(255, 231, 138, 0.94);
            outline-offset: 2px;
          }
          .ft-pdf-ai-question-path {
            fill: transparent;
            stroke: transparent;
            stroke-width: 2.4;
            stroke-dasharray: 8 5;
            vector-effect: non-scaling-stroke;
            cursor: pointer;
            opacity: 0;
            filter: none;
            animation: none;
            transition:
              opacity 180ms ease,
              fill 180ms ease,
              stroke 180ms ease,
              filter 180ms ease;
          }
          .ft-pdf-ai-question-region.is-hovering .ft-pdf-ai-question-path {
            opacity: 1;
            fill: rgba(255, 211, 126, 0.16);
            stroke: rgba(255, 244, 185, 0.96);
            filter: drop-shadow(0 0 12px rgba(255, 211, 126, 0.28));
            animation: ftPdfAiQuestionDash 2.4s linear infinite;
          }
          .ft-pdf-ai-question-badge {
            display: grid;
            place-items: center;
            width: auto;
            min-width: 22px;
            height: 22px;
            padding: 0 7px;
            border-radius: 8px;
            background: linear-gradient(135deg, #ffe78a, #ff87aa);
            color: #1d0b18;
            font-weight: 950;
            font-size: 12px;
            line-height: 1;
            box-shadow:
              0 0 0 1px rgba(29, 11, 24, 0.55),
              0 4px 12px rgba(29, 11, 24, 0.34);
            transition: transform 180ms ease, box-shadow 180ms ease;
          }
          .ft-pdf-ai-question-badge.has-score {
            background: linear-gradient(135deg, #c7ffdc, #ffe78a 48%, #ff87aa);
          }
          .ft-pdf-ai-question-badge.has-score::before {
            content: attr(data-score);
          }
          .ft-pdf-ai-question-badge.has-score {
            color: transparent;
            font-size: 0;
          }
          .ft-pdf-ai-question-badge.has-score::before {
            color: #1d0b18;
            font-size: 11px;
            line-height: 1;
          }
          .ft-pdf-ai-question-region.is-hovering .ft-pdf-ai-question-badge {
            transform: translateY(-1px) scale(1.04);
            box-shadow:
              0 0 0 1px rgba(29, 11, 24, 0.58),
              0 0 18px rgba(255, 211, 126, 0.5),
              0 8px 20px rgba(29, 11, 24, 0.38);
          }
          @keyframes ftPdfAiQuestionDash {
            to { stroke-dashoffset: -26; }
          }
          .ft-pdf-ai-question-panel {
            position: fixed;
            left: 18px;
            bottom: 18px;
            z-index: 2330;
            --ft-mishika-card-w: 250px;
            --ft-mishika-card-h: 390px;
            --ft-mishika-dialogue-x: 358px;
            --ft-mishika-dialogue-y: 58px;
            --ft-mishika-dialogue-shift-y: 0px;
            --ft-mishika-dialogue-min-w: min(33vw, calc(100vw - var(--ft-mishika-dialogue-x) - 318px));
            --ft-mishika-dialogue-max-w: min(50vw, calc(100vw - var(--ft-mishika-dialogue-x) - 318px));
            --ft-mishika-transcript-gap: 16px;
            --ft-mishika-transcript-x: calc(var(--ft-mishika-dialogue-x) + var(--ft-mishika-dialogue-max-w) + var(--ft-mishika-transcript-gap));
            --ft-mishika-transcript-w: min(300px, calc(100vw - var(--ft-mishika-transcript-x) - 34px));
            --ft-mishika-connector-x: 0px;
            --ft-mishika-connector-y: 72px;
            --ft-mishika-image-max-h: min(34vh, 260px);
            --ft-mishika-answer-max-h: none;
            width: calc(100vw - 28px);
            min-height: 452px;
            max-width: calc(100vw - 28px);
            bottom: var(--ft-mishika-panel-bottom, 18px);
            pointer-events: none;
            perspective: 900px;
            transform-origin: 8% 100%;
            animation: ftPdfMikasaStageBurst 540ms cubic-bezier(.16,.86,.2,1) both;
          }
          .ft-pdf-ai-question-panel.is-hidden {
            display: none;
          }
          .ft-pdf-ai-question-panel.is-minimized {
            display: none;
          }
          .ft-pdf-ai-question-panel.is-closing {
            pointer-events: none;
            animation: ftPdfMikasaPanelOut 520ms cubic-bezier(.22,.72,.16,1) both;
          }
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-dialogue-stack {
            pointer-events: none;
            animation: ftPdfMikasaNodeOut 340ms cubic-bezier(.22,.72,.16,1) both;
          }
          .ft-pdf-ai-question-panel:not(.is-tail-ready) .ft-pdf-ai-question-dialogue-stack {
            opacity: 0;
            transform: translateY(18px) scale(0.96);
          }
          .ft-pdf-ai-question-panel.is-tail-ready .ft-pdf-ai-question-dialogue-stack {
            animation: ftPdfMikasaDialogueBurst 440ms cubic-bezier(.16,.86,.2,1) both;
          }
          .ft-pdf-ai-question-panel.is-tail-ready.is-switching .ft-pdf-ai-question-dialogue-stack {
            pointer-events: none;
            animation: ftPdfMikasaNodeOut 340ms cubic-bezier(.22,.72,.16,1) both;
          }
          .ft-pdf-ai-question-mikasa-card {
            position: relative;
            z-index: 3;
            width: var(--ft-mishika-card-w);
            min-height: var(--ft-mishika-card-h);
            overflow: hidden;
            display: grid;
            grid-template-rows: 30px 28px minmax(0, 1fr);
            padding: 8px 10px 10px;
            border: 3px solid rgba(255, 80, 20, 0.62);
            border-radius: 16px;
            background:
              linear-gradient(135deg, rgba(58, 0, 0, 0.78), rgba(32, 0, 0, 0.62)),
              radial-gradient(circle at 48% 55%, rgba(255, 104, 48, 0.22), transparent 58%);
            box-shadow:
              0 0 34px rgba(255, 60, 0, 0.42),
              0 24px 58px rgba(0, 0, 0, 0.48),
              inset 0 0 28px rgba(255, 115, 52, 0.14);
            pointer-events: auto;
            transform-origin: 10% 100%;
            animation: ftPdfMikasaWindowBurst 560ms cubic-bezier(.16,.86,.2,1) both;
          }
          .ft-pdf-ai-question-mikasa-card::before {
            content: "";
            position: absolute;
            top: -18%;
            bottom: -18%;
            left: -42%;
            width: 34%;
            pointer-events: none;
            background: linear-gradient(90deg, transparent, rgba(255, 190, 110, 0.62), transparent);
            filter: blur(1px);
            transform: skewX(-15deg);
            animation: ftPdfMikasaWindowShine 2.45s linear infinite 420ms;
          }
          .ft-pdf-ai-question-character-title {
            position: relative;
            z-index: 2;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            min-width: 0;
            padding: 0 2px 8px 4px;
            color: #ffad83;
            font-size: 18px;
            font-weight: 900;
          }
          .ft-pdf-ai-question-character-name::before {
            content: "";
            display: inline-block;
            width: 9px;
            height: 9px;
            margin-right: 7px;
            border-radius: 999px;
            background: #ff6f34;
            box-shadow: 0 0 14px rgba(255, 111, 52, 0.95);
          }
          .ft-pdf-ai-question-character-controls {
            display: flex;
            gap: 6px;
          }
          .ft-pdf-ai-question-character-controls button {
            position: relative;
            display: block;
            width: 24px;
            height: 24px;
            padding: 0;
            border: 1px solid rgba(255, 150, 100, 0.42);
            border-radius: 6px;
            background: rgba(200, 60, 0, 0.68);
            box-shadow: inset 0 0 10px rgba(255, 160, 90, 0.14);
          }
          .ft-pdf-ai-question-character-controls button {
            cursor: pointer;
          }
          .ft-pdf-ai-question-character-controls button:hover,
          .ft-pdf-ai-question-character-controls button:focus-visible {
            border-color: rgba(255, 231, 138, 0.82);
            background: linear-gradient(135deg, rgba(255, 231, 138, 0.92), rgba(255, 103, 68, 0.92));
            box-shadow: 0 0 18px rgba(255, 126, 74, 0.48), inset 0 0 10px rgba(255, 255, 255, 0.18);
            outline: none;
          }
          .ft-pdf-ai-question-character-controls button::before,
          .ft-pdf-ai-question-character-controls button::after {
            display: grid;
            place-items: center;
            width: 100%;
            height: 100%;
            color: white;
            font-size: 14px;
            font-style: normal;
            font-weight: 950;
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-close]::before { content: "x"; }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-minimize]::before { content: "-"; }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-save-progress]::before {
            content: "";
            position: absolute;
            left: 6px;
            top: 5px;
            width: 12px;
            height: 14px;
            border-radius: 3px;
            background: linear-gradient(180deg, #fff5cc 0 22%, #5a0b13 23% 42%, #fff9dc 43% 100%);
            box-shadow: 0 0 8px rgba(255, 221, 144, 0.48), inset 0 -3px 0 rgba(79, 0, 12, 0.28);
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-save-progress]::after {
            content: "";
            position: absolute;
            left: 9px;
            bottom: 5px;
            width: 6px;
            height: 3px;
            border-radius: 2px;
            background: #6d0c17;
            box-shadow: 0 -6px 0 rgba(255, 230, 160, 0.7);
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-save-progress][data-tone="saving"] {
            animation: ftPdfAiQuestionSavePulse 780ms ease-in-out infinite;
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-save-progress][data-tone="saved"] {
            border-color: rgba(190, 255, 181, 0.86);
            background: linear-gradient(135deg, rgba(45, 128, 62, 0.92), rgba(122, 210, 100, 0.74));
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-save-progress][data-tone="error"] {
            border-color: rgba(255, 177, 177, 0.9);
            background: linear-gradient(135deg, rgba(118, 10, 28, 0.98), rgba(210, 42, 55, 0.86));
          }
          @keyframes ftPdfAiQuestionSavePulse {
            0%, 100% { filter: brightness(1); transform: translateY(0); }
            50% { filter: brightness(1.28); transform: translateY(-1px); }
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::before,
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::after {
            content: "";
            position: absolute;
            top: 6px;
            width: 4px;
            height: 12px;
            border-radius: 999px;
            background: linear-gradient(180deg, #fff7c7, #ffffff 48%, #ffd096);
            box-shadow: 0 0 8px rgba(255, 222, 150, 0.68);
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::before { left: 7px; }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::after { right: 7px; }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle].is-active {
            border-color: rgba(255, 235, 166, 0.9);
            background: linear-gradient(135deg, rgba(92, 18, 30, 0.96), rgba(170, 40, 48, 0.92));
            box-shadow: 0 0 18px rgba(150, 18, 34, 0.45), inset 0 0 12px rgba(255, 235, 166, 0.16);
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle].is-active::before,
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle].is-active::after {
            background: linear-gradient(180deg, #fff9da, #ffd38e);
            box-shadow: 0 0 10px rgba(255, 217, 134, 0.86);
          }
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle].is-active,
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle].is-active::before,
          .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle].is-active::after,
          .ft-pdf-ai-question-panel.is-animation-pause-requested .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle],
          .ft-pdf-ai-question-panel.is-animation-pause-requested .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::before,
          .ft-pdf-ai-question-panel.is-animation-pause-requested .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::after,
          .ft-pdf-ai-question-panel.is-animation-paused .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle],
          .ft-pdf-ai-question-panel.is-animation-paused .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::before,
          .ft-pdf-ai-question-panel.is-animation-paused .ft-pdf-ai-question-character-controls button[data-pdf-ai-question-animation-toggle]::after {
            animation: none !important;
            transition: none !important;
            transform: none !important;
            filter: none !important;
            will-change: auto !important;
          }
          .ft-pdf-ai-question-score {
            position: relative;
            z-index: 2;
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 8px;
            min-height: 24px;
            padding: 0 3px 5px;
            pointer-events: none;
          }
          .ft-pdf-ai-question-score b,
          .ft-pdf-ai-question-score i {
            display: grid;
            place-items: center;
            min-width: 16px;
            height: 20px;
            padding: 0 2px;
            font-size: 13px;
            font-weight: 950;
            line-height: 1;
            font-style: normal;
            background: transparent;
            text-shadow: 0 0 10px currentColor, 0 1px 5px rgba(0, 0, 0, 0.72);
          }
          .ft-pdf-ai-question-score b {
            color: #ffb24a;
          }
          .ft-pdf-ai-question-score i {
            color: #ffffff;
          }
          .ft-pdf-ai-question-dialogue-stack {
            position: absolute;
            left: var(--ft-mishika-dialogue-x);
            top: calc(var(--ft-mishika-dialogue-y) + var(--ft-mishika-dialogue-shift-y));
            z-index: 5;
            width: fit-content;
            min-width: var(--ft-mishika-dialogue-min-w);
            max-width: var(--ft-mishika-dialogue-max-w);
            display: grid;
            gap: 12px;
            padding-top: 0;
            pointer-events: auto;
            transform-origin: 0 100%;
            isolation: isolate;
          }
          .ft-pdf-ai-question-image-frame {
            position: relative;
            z-index: 2;
            margin: 0;
            width: min(100%, 430px);
            max-height: var(--ft-mishika-image-max-h);
            border: 0;
            border-radius: 8px;
            background: transparent;
            box-shadow: none;
            overflow: visible;
            display: grid;
            place-items: center;
          }
          .ft-pdf-ai-question-image-frame[hidden] {
            display: none;
          }
          .ft-pdf-ai-question-image-frame::before {
            content: none;
          }
          .ft-pdf-ai-question-image-frame img {
            display: block;
            width: 100%;
            max-height: var(--ft-mishika-image-max-h);
            object-fit: contain;
            position: relative;
            z-index: 1;
            border: 1px solid rgba(255, 159, 122, 0.32);
            border-radius: 8px;
            background: rgba(18, 0, 2, 0.46);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.24);
          }
          .ft-pdf-ai-question-mini-return {
            position: fixed;
            left: 18px;
            bottom: 18px;
            z-index: 2332;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            min-height: 42px;
            padding: 7px 12px 7px 8px;
            border: 1px solid rgba(255,231,138,0.56);
            border-radius: 999px;
            color: #fff6d8;
            background:
              radial-gradient(circle at 22% 22%, rgba(255,255,255,0.28), transparent 28%),
              linear-gradient(135deg, rgba(126,255,232,0.18), rgba(255,135,170,0.18)),
              rgba(8,18,31,0.92);
            box-shadow: 0 14px 34px rgba(0,0,0,0.34), 0 0 24px rgba(255,231,138,0.16);
            font-weight: 950;
            cursor: pointer;
            backdrop-filter: blur(10px);
          }
          .ft-pdf-ai-question-mini-return.is-hidden {
            display: none;
          }
          .ft-pdf-ai-question-mini-return span {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background:
              radial-gradient(circle at 50% 42%, rgba(255,231,138,0.95) 0 18%, transparent 19%),
              radial-gradient(circle at 50% 50%, rgba(255,135,170,0.78), rgba(126,255,232,0.72));
            box-shadow: inset 0 0 10px rgba(255,255,255,0.18), 0 0 16px rgba(126,255,232,0.28);
          }
          .ft-pdf-ai-question-mini-return b {
            font-size: 12px;
            letter-spacing: 0.02em;
          }
          .ft-pdf-ai-question-window-actions {
            display: inline-flex;
            align-items: center;
            gap: 8px;
          }
          .ft-pdf-ai-question-editor-minimize {
            font-size: 22px;
            line-height: 1;
            padding-bottom: 4px;
          }
          .ft-pdf-ai-question-editor-mini-return {
            position: fixed;
            left: 18px;
            bottom: 72px;
            z-index: 2333;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            min-height: 42px;
            padding: 7px 13px 7px 8px;
            border: 1px solid rgba(126, 255, 232, 0.5);
            border-radius: 999px;
            color: #f5fffb;
            background:
              radial-gradient(circle at 22% 22%, rgba(255,255,255,0.22), transparent 28%),
              linear-gradient(135deg, rgba(126,255,232,0.18), rgba(255,231,138,0.14)),
              rgba(9,18,31,0.93);
            box-shadow: 0 14px 34px rgba(0,0,0,0.34), 0 0 24px rgba(126,255,232,0.16);
            font-weight: 950;
            cursor: pointer;
            backdrop-filter: blur(10px);
          }
          .ft-pdf-ai-question-editor-mini-return.is-hidden {
            display: none;
          }
          .ft-pdf-ai-question-editor-mini-return span {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background:
              radial-gradient(circle at 50% 42%, rgba(126,255,232,0.95) 0 18%, transparent 19%),
              radial-gradient(circle at 50% 50%, rgba(255,231,138,0.78), rgba(126,255,232,0.72));
            box-shadow: inset 0 0 10px rgba(255,255,255,0.18), 0 0 16px rgba(126,255,232,0.28);
          }
          .ft-pdf-ai-question-editor-mini-return b {
            font-size: 12px;
            letter-spacing: 0.02em;
          }
          .ft-pdf-ai-question-flame-ring {
            position: absolute;
            inset: 0;
            z-index: 1;
            pointer-events: none;
            overflow: visible;
            transform-style: preserve-3d;
            contain: layout style;
          }
          .ft-pdf-ai-question-flame-chain {
            position: absolute;
            width: 1px;
            height: 1px;
            overflow: visible;
            transform-style: preserve-3d;
          }
          .ft-pdf-ai-question-flame-chain.is-top-left {
            left: 18px;
            top: 12px;
          }
          .ft-pdf-ai-question-flame-chain.is-bottom-right {
            right: 18px;
            bottom: 12px;
          }
          .ft-pdf-ai-question-flame-chain.is-back {
            z-index: 0;
            opacity: 0.62;
            transform: translateZ(-8px);
          }
          .ft-pdf-ai-question-flame-chain.is-front {
            z-index: 4;
            transform: translateZ(10px);
          }
          .ft-pdf-ai-question-flame-chain i {
            position: absolute;
            left: var(--x);
            top: var(--y);
            width: 11px;
            height: 5px;
            border-radius: 78% 16% 76% 20%;
            background:
              radial-gradient(ellipse at 28% 48%, rgba(194, 42, 34, 0.5) 0 10%, transparent 11%),
              linear-gradient(105deg, #120002 0%, #330008 32%, #6e0011 64%, #160003 100%);
            box-shadow:
              0 1px 3px rgba(0, 0, 0, 0.5),
              0 0 5px rgba(88, 0, 15, 0.74);
            opacity: 0;
            transform: translate(-50%, -50%) rotate(var(--r)) scale(var(--s));
            transform-origin: 18% 50%;
            animation:
              ftPdfMikasaFlameChipIn 520ms cubic-bezier(.2,.86,.22,1) calc(520ms + var(--d)) both,
              ftPdfMikasaFlameChipFlicker 1380ms ease-in-out calc(980ms + var(--d)) infinite;
          }
          .ft-pdf-ai-question-flame-chain i::before,
          .ft-pdf-ai-question-flame-chain i::after {
            content: "";
            position: absolute;
            pointer-events: none;
          }
          .ft-pdf-ai-question-flame-chain i::before {
            right: -4px;
            top: 0;
            width: 7px;
            height: 4px;
            border-radius: 82% 8% 80% 18%;
            background: linear-gradient(105deg, #5b000d, #130002 84%);
            transform: rotate(-16deg) skewX(-20deg);
          }
          .ft-pdf-ai-question-flame-chain i::after {
            left: 2px;
            top: 1px;
            width: 4px;
            height: 2px;
            border-radius: 999px;
            background: rgba(145, 18, 24, 0.7);
            filter: blur(0.2px);
          }
          .ft-pdf-ai-question-flame-chain.is-back i {
            filter: blur(0.25px);
            opacity: 0.72;
          }
          .ft-pdf-ai-question-flame-chain.is-front i {
            box-shadow:
              0 1px 4px rgba(0, 0, 0, 0.46),
              0 0 7px rgba(92, 0, 15, 0.82);
          }
          .ft-pdf-ai-question-panel.is-animation-paused .ft-pdf-ai-question-flame-chain i,
          .ft-pdf-ai-question-panel.is-animation-paused .ft-pdf-ai-question-tail-seal,
          .ft-pdf-ai-question-panel.is-animation-paused .ft-pdf-ai-question-tail-seal::before,
          .ft-pdf-ai-question-panel.is-animation-paused .ft-pdf-ai-question-tail-seal::after {
            animation-play-state: paused !important;
          }
          .ft-pdf-ai-question-mikasa {
            position: relative;
            z-index: 1;
            width: 100%;
            height: 342px;
            overflow: hidden;
            border-radius: 12px;
            background: transparent;
            filter:
              drop-shadow(0 16px 24px rgba(0, 0, 0, 0.42))
              drop-shadow(0 0 18px rgba(126, 255, 232, 0.16));
          }
          .ft-pdf-ai-question-mikasa::before {
            content: "";
            position: absolute;
            left: 12px;
            right: 12px;
            bottom: 2px;
            height: 12px;
            border-radius: 50%;
            background: radial-gradient(ellipse at center, rgba(0,0,0,0.34), transparent 70%);
            filter: blur(1px);
          }
          .ft-pdf-ai-question-mikasa img {
            position: absolute;
            left: 50%;
            bottom: 0;
            width: 270px;
            height: 350px;
            object-fit: contain;
            object-position: center bottom;
            pointer-events: none;
            transform: translateX(-50%);
            opacity: 0;
            animation: ftPdfMikasaGifRise 420ms cubic-bezier(.16,.86,.2,1) 220ms both;
          }
          .ft-pdf-ai-question-panel.is-speaking .ft-pdf-ai-question-character-name::before {
            animation: ftPdfMikasaSpeakPulse 620ms ease-in-out infinite;
          }
          @keyframes ftPdfMikasaSpeakPulse {
            0%, 100% { transform: scale(1); box-shadow: 0 0 14px rgba(255, 111, 52, 0.95); }
            50% { transform: scale(1.22); box-shadow: 0 0 22px rgba(255, 214, 124, 0.9); }
          }
          .ft-pdf-ai-question-bubble {
            position: relative;
            z-index: 2;
            min-height: 112px;
            padding: 13px 14px;
            border: 1px solid rgba(139, 0, 0, 0.78);
            border-radius: 13px;
            background:
              linear-gradient(135deg, rgba(31, 0, 0, 0.96), rgba(66, 5, 8, 0.92)),
              radial-gradient(circle at 100% 0, rgba(255, 92, 58, 0.16), transparent 42%),
              repeating-linear-gradient(0deg, rgba(255,178,116,0.04) 0 1px, transparent 1px 8px);
            color: #f5fffd;
            box-shadow:
              0 18px 42px rgba(0,0,0,0.34),
              0 0 0 1px rgba(255, 148, 112, 0.16),
              0 0 30px rgba(139, 0, 0, 0.32),
              inset 0 0 22px rgba(255,116,56,0.1);
            overflow: visible;
          }
          .ft-pdf-ai-question-bubble::before,
          .ft-pdf-ai-question-bubble::after {
            content: "";
            position: absolute;
            pointer-events: none;
          }
          .ft-pdf-ai-question-bubble::before {
            left: 12px;
            right: 58px;
            top: 0;
            height: 3px;
            background: linear-gradient(90deg, rgba(255, 238, 210, 0.94), rgba(139, 0, 0, 0.92), rgba(255, 119, 84, 0.76));
            box-shadow: 0 0 12px rgba(139, 0, 0, 0.72);
          }
          .ft-pdf-ai-question-bubble::after {
            right: 0;
            top: 0;
            width: 48px;
            height: 34px;
            background: linear-gradient(135deg, transparent 0 42%, rgba(255, 238, 210, 0.95) 43% 46%, rgba(139, 0, 0, 0.96) 47% 54%, transparent 55%);
          }
          .ft-pdf-ai-question-bubble strong {
            position: relative;
            z-index: 5;
            display: block;
            margin-bottom: 5px;
            color: #ffe78a;
          }
          .ft-pdf-ai-question-bubble span {
            position: relative;
            z-index: 5;
            display: block;
            white-space: pre-wrap;
            line-height: 1.45;
          }
          .ft-pdf-ai-question-bubble span.is-typing,
          .ft-pdf-ai-question-bubble span.is-typing-done {
            text-shadow:
              0 0 9px rgba(126, 255, 232, 0.12),
              0 0 16px rgba(255, 231, 138, 0.1);
          }
          .ft-pdf-ai-question-bubble span.is-vapor-reading {
            animation: ftPdfAiQuestionVaporText 1640ms ease-in-out infinite;
            text-shadow:
              0 -0.04em 0.2em rgba(255, 235, 220, 0.18),
              0 -0.18em 0.5em rgba(255, 92, 86, 0.28),
              0 -0.36em 0.84em rgba(255, 168, 82, 0.16);
            filter: saturate(1.16);
            isolation: isolate;
          }
          .ft-pdf-ai-question-bubble span.is-vapor-reading::before,
          .ft-pdf-ai-question-bubble span.is-vapor-reading::after {
            content: attr(data-vapor-text);
            position: absolute;
            inset: 0;
            z-index: 7;
            pointer-events: none;
            white-space: inherit;
            line-height: inherit;
            font: inherit;
            color: transparent;
            background:
              radial-gradient(circle at 7% 94%, rgba(255, 245, 220, 0.98) 0 1.4px, transparent 3.2px),
              radial-gradient(circle at 18% 79%, rgba(255, 82, 86, 0.88) 0 1.8px, transparent 4.2px),
              radial-gradient(circle at 29% 91%, rgba(255, 173, 84, 0.86) 0 1.2px, transparent 3px),
              radial-gradient(circle at 43% 73%, rgba(255, 45, 92, 0.76) 0 1.6px, transparent 3.8px),
              radial-gradient(circle at 57% 96%, rgba(255, 222, 132, 0.82) 0 1.3px, transparent 3.4px),
              radial-gradient(circle at 71% 81%, rgba(226, 24, 58, 0.78) 0 1.7px, transparent 4px),
              radial-gradient(circle at 83% 93%, rgba(255, 120, 80, 0.9) 0 1.2px, transparent 3.2px),
              radial-gradient(circle at 94% 77%, rgba(255, 212, 180, 0.76) 0 1.5px, transparent 3.6px);
            background-size: 121px 61px, 163px 73px, 139px 57px, 187px 82px, 129px 69px, 171px 66px, 151px 78px, 197px 88px;
            -webkit-background-clip: text;
            background-clip: text;
            opacity: 0;
            filter: none;
            mix-blend-mode: screen;
            animation: ftPdfAiQuestionLycanVaporA 1510ms cubic-bezier(.19, .72, .26, 1) infinite;
          }
          .ft-pdf-ai-question-bubble span.is-vapor-reading::after {
            opacity: 0;
            background:
              radial-gradient(circle at 11% 88%, rgba(255, 126, 82, 0.88) 0 1.5px, transparent 4px),
              radial-gradient(circle at 24% 95%, rgba(255, 215, 150, 0.78) 0 1px, transparent 3.2px),
              radial-gradient(circle at 36% 74%, rgba(190, 12, 46, 0.82) 0 1.8px, transparent 4.4px),
              radial-gradient(circle at 53% 90%, rgba(255, 65, 118, 0.76) 0 1.2px, transparent 3.6px),
              radial-gradient(circle at 68% 70%, rgba(255, 154, 74, 0.86) 0 1.6px, transparent 4.1px),
              radial-gradient(circle at 79% 98%, rgba(255, 238, 214, 0.76) 0 1px, transparent 3px),
              radial-gradient(circle at 93% 83%, rgba(255, 31, 69, 0.72) 0 1.7px, transparent 4.2px);
            background-size: 149px 72px, 127px 58px, 173px 84px, 137px 63px, 159px 74px, 119px 55px, 181px 86px;
            filter: none;
            animation: ftPdfAiQuestionLycanVaporB 1970ms cubic-bezier(.23, .64, .18, 1) 230ms infinite;
          }
          @keyframes ftPdfAiQuestionVaporText {
            0%, 100% {
              filter: saturate(1.1) brightness(1);
              text-shadow:
                0 -0.04em 0.18em rgba(255, 238, 226, 0.13),
                0 -0.18em 0.46em rgba(255, 82, 86, 0.18),
                0 -0.34em 0.72em rgba(255, 150, 72, 0.1);
            }
            48% {
              filter: saturate(1.26) brightness(1.08);
              text-shadow:
                0 -0.08em 0.24em rgba(255, 238, 226, 0.24),
                0 -0.26em 0.64em rgba(255, 72, 82, 0.32),
                0 -0.52em 0.98em rgba(255, 174, 76, 0.2);
            }
          }
          @keyframes ftPdfAiQuestionLycanVaporA {
            0% {
              opacity: 0;
              transform: translate3d(-0.02em, 0.34em, 0) scale(0.92) rotate(-0.8deg);
              background-position: 0 48px, 23px 52px, 51px 44px, 77px 60px, 93px 46px, 129px 54px, 149px 42px, 174px 58px;
            }
            13% {
              opacity: 0.9;
            }
            31% {
              opacity: 0.38;
              transform: translate3d(0.08em, -0.14em, 0) scale(1.03) rotate(0.6deg);
              background-position: 9px 12px, 34px 3px, 61px 16px, 84px -1px, 108px 11px, 137px 0, 165px 18px, 190px 4px;
            }
            57% {
              opacity: 0.7;
              transform: translate3d(-0.06em, -0.54em, 0) scale(1.12) rotate(-0.4deg);
            }
            100% {
              opacity: 0;
              transform: translate3d(0.14em, -1.08em, 0) scale(1.2) rotate(0.9deg);
              background-position: 17px -38px, 45px -51px, 69px -29px, 96px -58px, 119px -34px, 147px -47px, 171px -26px, 203px -62px;
            }
          }
          @keyframes ftPdfAiQuestionLycanVaporB {
            0% {
              opacity: 0;
              transform: translate3d(0.06em, 0.42em, 0) scale(0.88) rotate(0.7deg);
              background-position: 18px 56px, 41px 48px, 63px 62px, 86px 50px, 112px 66px, 132px 52px, 158px 60px;
            }
            19% {
              opacity: 0.74;
              transform: translate3d(-0.08em, 0.02em, 0) scale(1.02) rotate(-0.5deg);
            }
            43% {
              opacity: 0.22;
              background-position: 7px 18px, 31px 4px, 55px 28px, 80px 8px, 101px 26px, 127px 12px, 151px 30px;
            }
            69% {
              opacity: 0.58;
              transform: translate3d(0.1em, -0.7em, 0) scale(1.16) rotate(0.4deg);
            }
            100% {
              opacity: 0;
              transform: translate3d(-0.14em, -1.22em, 0) scale(1.26) rotate(-1deg);
              background-position: -2px -46px, 24px -31px, 47px -60px, 72px -38px, 94px -67px, 121px -35px, 144px -58px;
            }
          }
          .ft-pdf-ai-question-active-vapor {
            position: absolute;
            z-index: 9;
            display: block;
            pointer-events: none;
            border-radius: 999px;
            background:
              radial-gradient(circle at 8% 78%, rgba(255, 242, 224, 0.96) 0 1.7px, transparent 3.8px),
              radial-gradient(circle at 21% 58%, rgba(255, 55, 88, 0.92) 0 2px, transparent 4.6px),
              radial-gradient(circle at 36% 72%, rgba(255, 172, 74, 0.88) 0 1.5px, transparent 4px),
              radial-gradient(circle at 52% 46%, rgba(210, 18, 54, 0.88) 0 2.1px, transparent 4.8px),
              radial-gradient(circle at 68% 74%, rgba(255, 226, 142, 0.8) 0 1.4px, transparent 3.8px),
              radial-gradient(circle at 84% 54%, rgba(255, 82, 72, 0.88) 0 1.9px, transparent 4.6px);
            background-size: 52px 38px, 67px 44px, 58px 35px, 74px 50px, 49px 37px, 71px 46px;
            filter: none;
            mix-blend-mode: screen;
            opacity: 0;
            animation: ftPdfAiQuestionActiveVapor 820ms cubic-bezier(.18,.72,.22,1) infinite;
          }
          @keyframes ftPdfAiQuestionActiveVapor {
            0% {
              opacity: 0;
              transform: translate3d(0, 0.3em, 0) scale(0.9);
              background-position: 0 24px, 12px 28px, 24px 22px, 36px 30px, 48px 24px, 60px 28px;
            }
            18% {
              opacity: 0.96;
            }
            46% {
              opacity: 0.48;
              transform: translate3d(0.08em, -0.28em, 0) scale(1.08);
              background-position: 8px 2px, 20px -8px, 31px 5px, 44px -5px, 54px 7px, 68px -7px;
            }
            100% {
              opacity: 0;
              transform: translate3d(-0.05em, -0.92em, 0) scale(1.22);
              background-position: 16px -28px, 28px -40px, 39px -22px, 52px -44px, 63px -24px, 76px -38px;
            }
          }
          .ft-pdf-ai-question-highlight {
            display: inline;
            color: var(--ai-hl);
            padding: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            text-shadow:
              0 0 6px rgba(255, 231, 138, 0.18),
              0 0 12px rgba(126, 255, 232, 0.08);
            -webkit-box-decoration-break: clone;
            box-decoration-break: clone;
          }
          .ft-pdf-ai-question-bubble span.ft-pdf-ai-question-highlight {
            display: inline;
            white-space: inherit;
            line-height: inherit;
          }
          .ft-pdf-ai-question-type-live {
            display: inline-block;
            color: inherit;
            vertical-align: baseline;
            transform-origin: 50% 72%;
            text-shadow:
              0 0 9px rgba(255, 231, 138, 0.38),
              0 0 16px rgba(126, 255, 232, 0.14);
            animation: ftPdfAiQuestionLiveGlyph 320ms cubic-bezier(0.16, 0.86, 0.2, 1) both;
            will-change: transform, opacity, filter;
          }
          @keyframes ftPdfAiQuestionLiveGlyph {
            0% {
              opacity: 0.5;
              transform: translateY(0.12em) scale(0.9);
              filter: blur(0.35px) brightness(1.18);
            }
            58% {
              opacity: 1;
              transform: translateY(-0.04em) scale(1.07);
              filter: blur(0) brightness(1.14);
            }
            100% {
              opacity: 1;
              transform: translateY(0) scale(1);
              filter: brightness(1);
            }
          }
          .ft-pdf-ai-question-type-live-word {
            position: relative;
            display: inline;
            color: inherit;
            animation: ftPdfAiQuestionLiveWord 460ms ease-out both;
            will-change: opacity, filter;
          }
          .ft-pdf-ai-question-type-unrevealed {
            opacity: 0;
          }
          .ft-pdf-ai-question-type-comet-char {
            position: relative;
            display: inline-block;
            --ai-type-comet: #7effe8;
            color: #ffffff;
            vertical-align: baseline;
            isolation: isolate;
            filter:
              drop-shadow(0 0 10px rgba(255, 255, 255, 0.44))
              drop-shadow(0 0 20px color-mix(in srgb, var(--ai-type-comet) 52%, transparent));
            animation: ftPdfAiQuestionCometHead 620ms cubic-bezier(.18, .78, .22, 1) infinite;
          }
          .ft-pdf-ai-question-type-comet-glyph {
            position: relative;
            z-index: 2;
            display: inline-block;
            color: #ffffff;
            text-shadow:
              0 0 8px rgba(255, 255, 255, 0.86),
              0 0 16px rgba(236, 255, 249, 0.76),
              0 0 28px color-mix(in srgb, var(--ai-type-comet) 72%, transparent);
            animation: ftPdfAiQuestionCometGlyph 520ms ease-in-out infinite;
          }
          .ft-pdf-ai-question-type-comet-glyph::before,
          .ft-pdf-ai-question-type-comet-glyph::after {
            content: "";
            position: absolute;
            z-index: -1;
            width: 0.16em;
            height: 0.16em;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.94);
            box-shadow:
              0 0 0.22em rgba(255, 255, 255, 0.76),
              0 0 0.52em color-mix(in srgb, var(--ai-type-comet) 66%, transparent);
            pointer-events: none;
            mix-blend-mode: screen;
            opacity: 0;
          }
          .ft-pdf-ai-question-type-comet-glyph::before {
            right: -0.24em;
            top: -0.28em;
            animation: ftPdfAiQuestionFireflyA 1180ms cubic-bezier(.2, .76, .18, 1) infinite;
          }
          .ft-pdf-ai-question-type-comet-glyph::after {
            right: -0.02em;
            bottom: -0.18em;
            width: 0.12em;
            height: 0.12em;
            animation: ftPdfAiQuestionFireflyB 1420ms cubic-bezier(.22, .72, .16, 1) 140ms infinite;
          }
          .ft-pdf-ai-question-type-comet-particles {
            position: absolute;
            left: -2.2em;
            top: 50%;
            z-index: 0;
            width: 2.5em;
            height: 1.5em;
            pointer-events: none;
            transform: translateY(-50%);
            mix-blend-mode: screen;
            overflow: visible;
          }
          .ft-pdf-ai-question-type-comet-particles::before,
          .ft-pdf-ai-question-type-comet-particles::after {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: 999px;
            background:
              radial-gradient(circle at 92% 48%, rgba(255,255,255,0.96) 0 0.08em, transparent 0.13em),
              radial-gradient(circle at 72% 26%, color-mix(in srgb, var(--ai-type-comet) 70%, transparent) 0 0.07em, transparent 0.12em),
              radial-gradient(circle at 54% 68%, rgba(236,255,249,0.58) 0 0.06em, transparent 0.11em),
              radial-gradient(circle at 34% 36%, color-mix(in srgb, var(--ai-type-comet) 48%, transparent) 0 0.05em, transparent 0.1em);
            filter:
              blur(0.2px)
              drop-shadow(0 0 8px rgba(255,255,255,0.24))
              drop-shadow(0 0 12px color-mix(in srgb, var(--ai-type-comet) 32%, transparent));
            opacity: 0;
          }
          .ft-pdf-ai-question-type-comet-particles::before {
            animation: ftPdfAiQuestionFireflyTrailA 980ms linear infinite;
          }
          .ft-pdf-ai-question-type-comet-particles::after {
            animation: ftPdfAiQuestionFireflyTrailB 1260ms linear infinite;
          }
          @keyframes ftPdfAiQuestionLiveWord {
            0% {
              opacity: 0;
              filter: blur(0.4px) brightness(1.18);
              text-shadow: 0 0 0 rgba(255, 255, 255, 0);
            }
            62% {
              opacity: 1;
              filter: blur(0) brightness(1.12);
              text-shadow:
                0 0 9px rgba(255, 255, 255, 0.28),
                0 0 16px rgba(126, 255, 232, 0.16);
            }
            100% {
              opacity: 1;
              filter: brightness(1);
              text-shadow:
                0 0 6px rgba(255, 255, 255, 0.14),
                0 0 12px rgba(126, 255, 232, 0.08);
            }
          }
          @keyframes ftPdfAiQuestionLightChalk {
            0% {
              opacity: 0;
              transform: translate(0, 0) scale(0.42);
            }
            28% {
              opacity: 0.86;
            }
            100% {
              opacity: 0;
              transform: translate(0.24em, -0.54em) scale(1.05);
            }
          }
          @keyframes ftPdfAiQuestionCometHead {
            0%, 100% {
              transform: translateY(0) scale(1);
              filter:
                drop-shadow(0 0 9px rgba(255, 255, 255, 0.34))
                drop-shadow(0 0 18px color-mix(in srgb, var(--ai-type-comet) 42%, transparent));
            }
            48% {
              transform: translateY(-0.035em) scale(1.055);
              filter:
                drop-shadow(0 0 13px rgba(255, 255, 255, 0.54))
                drop-shadow(0 0 26px color-mix(in srgb, var(--ai-type-comet) 56%, transparent));
            }
          }
          @keyframes ftPdfAiQuestionCometGlyph {
            0%, 100% {
              filter: saturate(1.18) brightness(1.08);
            }
            52% {
              filter: saturate(1.42) brightness(1.28);
            }
          }
          @keyframes ftPdfAiQuestionFireflyA {
            0% {
              opacity: 0;
              transform: translate(0, 0) scale(0.42);
            }
            26% {
              opacity: 0.88;
            }
            100% {
              opacity: 0;
              transform: translate(0.36em, -0.42em) scale(1.05);
            }
          }
          @keyframes ftPdfAiQuestionFireflyB {
            0% {
              opacity: 0;
              transform: translate(0, 0) scale(0.44);
            }
            30% {
              opacity: 0.78;
            }
            100% {
              opacity: 0;
              transform: translate(0.18em, 0.34em) scale(0.92);
            }
          }
          @keyframes ftPdfAiQuestionFireflyTrailA {
            0% {
              opacity: 0;
              transform: translateX(0.28em) translateY(0) scale(0.82);
            }
            25% {
              opacity: 0.88;
            }
            100% {
              opacity: 0;
              transform: translateX(-0.44em) translateY(-0.16em) scale(1.08);
            }
          }
          @keyframes ftPdfAiQuestionFireflyTrailB {
            0% {
              opacity: 0;
              transform: translateX(0.2em) translateY(0.06em) scale(0.74);
            }
            34% {
              opacity: 0.68;
            }
            100% {
              opacity: 0;
              transform: translateX(-0.62em) translateY(0.18em) scale(1);
            }
          }
          .ft-pdf-ai-question-type-caret {
            display: inline-block;
            width: 0.42em;
            height: 0.42em;
            margin-left: 0.22em;
            vertical-align: 0.02em;
            border-radius: 999px;
            background: rgba(255, 231, 138, 0.92);
            box-shadow:
              0 0 8px rgba(255, 231, 138, 0.58),
              0 0 14px rgba(126, 255, 232, 0.2);
            animation: ftPdfAiQuestionTypeCaret 820ms ease-in-out infinite;
          }
          .ft-pdf-ai-question-type-caret.is-soft {
            opacity: 0.52;
          }
          @keyframes ftPdfAiQuestionTypeCaret {
            0%, 100% { opacity: 0.28; transform: scale(0.72); }
            48% { opacity: 1; transform: scale(1); }
          }
          .ft-pdf-ai-question-connector {
            position: absolute;
            left: var(--ft-mishika-connector-x);
            top: var(--ft-mishika-connector-y);
            z-index: 2;
            width: min(760px, calc(100vw - var(--ft-mishika-connector-x) - 38px));
            height: 360px;
            pointer-events: none;
            filter:
              drop-shadow(0 0 12px rgba(139, 0, 18, 0.74))
              drop-shadow(0 0 22px rgba(255, 72, 130, 0.16));
            animation: ftPdfAiConnectorLayerIn 260ms ease-out 180ms both;
          }
          .ft-pdf-ai-question-connector::before {
            content: "";
            position: absolute;
            left: 117px;
            right: auto;
            top: 294px;
            width: 18px;
            height: 18px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(255, 220, 194, 0.96), rgba(130, 0, 21, 0.92) 48%, rgba(40, 0, 8, 0.12) 72%);
            box-shadow:
              0 0 18px rgba(139, 0, 18, 0.88),
              0 0 28px rgba(255, 85, 140, 0.22);
            animation: ftPdfAiTailRootPulse 1.4s ease-in-out infinite;
          }
          .ft-pdf-ai-question-connector-svg,
          .ft-pdf-ai-question-tail,
          .ft-pdf-ai-question-tail-curl,
          .ft-pdf-ai-question-connector-node,
          .ft-pdf-ai-question-tail-link,
          .ft-pdf-ai-question-tail-seal,
          .ft-pdf-ai-question-tail-dust {
            position: absolute;
            display: block;
          }
          .ft-pdf-ai-question-connector-svg {
            inset: 0;
            width: 100%;
            height: 360px;
            overflow: visible;
          }
          .ft-pdf-ai-question-tail,
          .ft-pdf-ai-question-tail-curl {
            position: static;
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
            vector-effect: non-scaling-stroke;
          }
          .ft-pdf-ai-question-tail.is-glow {
            stroke: rgba(80, 0, 16, 0.46);
            stroke-width: 17;
            stroke-dasharray: 1;
            stroke-dashoffset: 1;
            filter: blur(3.2px);
            animation: ftPdfAiTailReach 660ms cubic-bezier(.18,.88,.22,1) 210ms both;
          }
          .ft-pdf-ai-question-tail.is-core {
            stroke: rgba(84, 0, 14, 0.92);
            stroke-width: 4.8;
            stroke-dasharray: 1;
            stroke-dashoffset: 1;
            filter:
              drop-shadow(0 0 6px rgba(139, 0, 18, 0.74))
              drop-shadow(0 0 14px rgba(255, 76, 130, 0.16));
            animation: ftPdfAiTailReach 640ms cubic-bezier(.18,.88,.22,1) calc(240ms + var(--tail-delay, 0ms)) both;
          }
          .ft-pdf-ai-question-tail.is-trace {
            stroke: rgba(255, 170, 188, 0.82);
            stroke-width: 1.8;
            stroke-dasharray: 0.026 0.073;
            stroke-dashoffset: 0.025;
            opacity: 0;
            filter: drop-shadow(0 0 5px rgba(255, 112, 150, 0.36));
            animation:
              ftPdfAiTailTraceIn 180ms ease-out 880ms both,
              ftPdfAiTailChainFlow 1.9s linear 880ms infinite;
          }
          .ft-pdf-ai-question-tail.is-tail-1 { --tail-delay: 70ms; opacity: 0.82; }
          .ft-pdf-ai-question-tail.is-tail-2 { --tail-delay: 110ms; opacity: 0.76; }
          .ft-pdf-ai-question-tail.is-tail-3 { --tail-delay: 150ms; opacity: 0.72; }
          .ft-pdf-ai-question-tail.is-tail-4 { --tail-delay: 190ms; opacity: 0.68; }
          .ft-pdf-ai-question-tail.is-tail-5 { --tail-delay: 230ms; opacity: 0.64; }
          .ft-pdf-ai-question-tail.is-glow:not(.is-main) {
            stroke-width: 14;
            opacity: 0.58;
          }
          .ft-pdf-ai-question-tail.is-trace:not(.is-main) {
            opacity: 0;
            stroke-width: 1.55;
            stroke-dasharray: 0.022 0.076;
          }
          .ft-pdf-ai-question-tail.is-spark {
            stroke: rgba(255, 220, 194, 0.76);
            stroke-width: 1.4;
            stroke-dasharray: 0.015 0.075;
            opacity: 0;
            animation:
              ftPdfAiTailTraceIn 180ms ease-out 1040ms both,
              ftPdfAiTailChainFlow 1.35s linear 1040ms infinite;
          }
          .ft-pdf-ai-question-tail-curl {
            stroke: rgba(92, 0, 16, 0.92);
            stroke-width: 4.2;
            stroke-dasharray: 1;
            stroke-dashoffset: 1;
            opacity: 0;
            filter:
              drop-shadow(0 0 7px rgba(139, 0, 18, 0.72))
              drop-shadow(0 0 12px rgba(255, 92, 140, 0.2));
          }
          .ft-pdf-ai-question-tail-curl.is-visible {
            animation: ftPdfAiTailCurlReach 420ms cubic-bezier(.16,.86,.2,1) calc(820ms + var(--curl-delay, 0ms)) both;
          }
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail.is-core,
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail.is-glow {
            animation: ftPdfAiTailRetract 360ms cubic-bezier(.42,0,.22,1) both;
          }
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail.is-trace,
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail.is-spark,
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail-curl {
            animation: ftPdfAiTailTraceOut 260ms ease both;
          }
          .ft-pdf-ai-question-tail-curl.is-main { --curl-delay: 0ms; stroke-width: 4.6; }
          .ft-pdf-ai-question-tail-curl.is-tail-1 { --curl-delay: 60ms; }
          .ft-pdf-ai-question-tail-curl.is-tail-2 { --curl-delay: 80ms; }
          .ft-pdf-ai-question-tail-curl.is-tail-3 { --curl-delay: 100ms; }
          .ft-pdf-ai-question-tail-curl.is-tail-4 { --curl-delay: 120ms; opacity: 0; }
          .ft-pdf-ai-question-tail-curl.is-tail-5 { --curl-delay: 140ms; opacity: 0; }
          .ft-pdf-ai-question-tail-link {
            left: var(--x);
            top: var(--y);
            z-index: 2;
            --twist: 0deg;
            width: 24px;
            height: 11px;
            border: 2px solid rgba(88, 0, 15, 0.98);
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(255, 220, 190, 0.2), rgba(82, 0, 14, 0.06));
            box-shadow:
              inset 0 0 0 1px rgba(255, 190, 170, 0.14),
              0 1px 4px rgba(0, 0, 0, 0.28),
              0 0 9px rgba(139, 0, 18, 0.44);
            opacity: 0;
            transform: translate(-50%, -50%) rotate(calc(var(--r) + var(--twist))) scale(0.34);
            transform-origin: center;
            animation:
              ftPdfAiTailLinkReach 430ms cubic-bezier(.16,.86,.2,1) calc(300ms + var(--d, 0ms)) both,
              ftPdfAiTailLinkGlow 1.9s ease-in-out calc(980ms + var(--d, 0ms)) infinite;
          }
          .ft-pdf-ai-question-tail-link:not(.is-main) {
            width: 23px;
            height: 10px;
            border-width: 1.9px;
            opacity: 0;
            box-shadow:
              inset 0 0 0 1px rgba(255, 190, 170, 0.13),
              0 1px 4px rgba(0, 0, 0, 0.25),
              0 0 9px rgba(139, 0, 18, 0.4);
          }
          .ft-pdf-ai-question-tail-link.is-main {
            border-color: rgba(70, 0, 14, 1);
            background:
              linear-gradient(135deg, rgba(255, 222, 196, 0.26), rgba(74, 0, 16, 0.08)),
              radial-gradient(circle at 35% 35%, rgba(255, 236, 212, 0.32), transparent 48%);
          }
          .ft-pdf-ai-question-tail-link.is-curl {
            z-index: 4;
            width: 20px;
            height: 9px;
            border-width: 1.8px;
            border-color: rgba(96, 0, 18, 0.98);
            background:
              linear-gradient(135deg, rgba(255, 222, 196, 0.24), rgba(70, 0, 14, 0.08)),
              radial-gradient(circle at 32% 35%, rgba(255, 236, 212, 0.36), transparent 50%);
            box-shadow:
              inset 0 0 0 1px rgba(255, 190, 170, 0.16),
              0 1px 4px rgba(0, 0, 0, 0.26),
              0 0 11px rgba(139, 0, 18, 0.48);
            animation: none;
          }
          .ft-pdf-ai-question-tail-link.is-curl.is-visible {
            animation:
              ftPdfAiTailLinkReach 360ms cubic-bezier(.16,.86,.2,1) calc(860ms + var(--d, 0ms)) both,
              ftPdfAiTailLinkGlow 1.7s ease-in-out calc(1240ms + var(--d, 0ms)) infinite;
          }
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail-link,
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail-seal,
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-tail-dust,
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-connector-node {
            animation: ftPdfAiTailBitsOut 300ms cubic-bezier(.42,0,.22,1) both;
          }
          .ft-pdf-ai-question-tail-link.is-curl::before {
            content: "";
            position: absolute;
            left: 50%;
            top: 50%;
            width: 3px;
            height: 3px;
            border-radius: 999px;
            background: rgba(255, 218, 184, 0.9);
            box-shadow: 0 0 8px rgba(255, 166, 130, 0.55);
            transform: translate(-50%, -50%);
          }
          .ft-pdf-ai-question-tail-link:nth-of-type(2n) {
            --twist: 78deg;
            border-color: rgba(116, 4, 24, 0.98);
          }
          .ft-pdf-ai-question-tail-link::after {
            content: "";
            position: absolute;
            inset: 1px 5px auto 5px;
            height: 1px;
            border-radius: 999px;
            background: rgba(255, 196, 182, 0.44);
          }
          .ft-pdf-ai-question-tail-seal {
            left: var(--x);
            top: var(--y);
            z-index: 7;
            width: 58px;
            height: 58px;
            border-radius: 999px;
            opacity: 0;
            pointer-events: none;
            transform: translate(-50%, -50%) rotate(var(--r, 0deg)) scale(calc(0.34 * var(--s, 1)));
            transform-origin: center;
            background:
              radial-gradient(circle, rgba(255, 232, 212, 0.22) 0 4%, transparent 5% 100%),
              repeating-conic-gradient(from 8deg, rgba(255, 188, 174, 0.78) 0 5deg, transparent 5deg 18deg),
              radial-gradient(circle, transparent 0 36%, rgba(116, 0, 22, 0.9) 37% 39%, transparent 40% 55%, rgba(70, 0, 14, 0.82) 56% 59%, transparent 60% 100%);
            border: 1px solid rgba(116, 0, 22, 0.72);
            box-shadow:
              inset 0 0 0 1px rgba(255, 178, 166, 0.14),
              0 0 14px rgba(139, 0, 18, 0.58),
              0 0 32px rgba(255, 80, 130, 0.16);
          }
          .ft-pdf-ai-question-tail-seal::before,
          .ft-pdf-ai-question-tail-seal::after {
            content: "";
            position: absolute;
            inset: 9px;
            border-radius: inherit;
            opacity: 0.92;
            pointer-events: none;
          }
          .ft-pdf-ai-question-tail-seal::before {
            background:
              linear-gradient(90deg, transparent 47%, rgba(255, 198, 184, 0.74) 48% 52%, transparent 53%),
              linear-gradient(0deg, transparent 47%, rgba(255, 198, 184, 0.66) 48% 52%, transparent 53%),
              repeating-conic-gradient(from 22deg, transparent 0 28deg, rgba(255, 154, 160, 0.56) 28deg 31deg, transparent 31deg 45deg);
            border: 1px solid rgba(128, 0, 25, 0.86);
            box-shadow:
              inset 0 0 10px rgba(139, 0, 18, 0.5),
              0 0 10px rgba(255, 92, 140, 0.22);
            animation: ftPdfAiTailSealSpin 2.8s linear infinite;
          }
          .ft-pdf-ai-question-tail-seal::after {
            inset: 18px;
            background:
              conic-gradient(from 45deg, transparent 0 20%, rgba(255, 202, 178, 0.72) 20% 24%, transparent 24% 50%, rgba(255, 202, 178, 0.58) 50% 54%, transparent 54% 100%),
              radial-gradient(circle, rgba(255, 222, 194, 0.8) 0 12%, rgba(112, 0, 22, 0.62) 13% 32%, transparent 33% 100%);
            border: 1px solid rgba(255, 150, 150, 0.42);
            filter: drop-shadow(0 0 6px rgba(255, 86, 130, 0.34));
            animation: ftPdfAiTailSealCounterSpin 2.1s linear infinite;
          }
          .ft-pdf-ai-question-tail-seal.is-visible {
            animation:
              ftPdfAiTailSealIn 520ms cubic-bezier(.16,.88,.2,1) var(--d, 980ms) both,
              ftPdfAiTailSealPulse 1.8s ease-in-out calc(var(--d, 980ms) + 520ms) infinite;
          }
          .ft-pdf-ai-question-tail-dust {
            left: 0;
            top: 0;
            z-index: 9;
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(255, 252, 222, 1), rgba(255, 151, 166, 0.86) 38%, rgba(255, 72, 122, 0.28) 62%, transparent 76%);
            box-shadow:
              0 0 10px rgba(255, 235, 202, 0.88),
              0 0 20px rgba(255, 96, 136, 0.5),
              0 0 30px rgba(139, 0, 18, 0.28);
            opacity: 0;
            offset-distance: 0%;
            offset-rotate: auto;
            transform: translate(-50%, -50%) scale(0.4);
            animation: ftPdfAiTailDust 720ms cubic-bezier(.18,.78,.18,1) var(--d, 0ms) both;
          }
          .ft-pdf-ai-question-tail-dust:nth-of-type(2n) {
            width: 5px;
            height: 5px;
            filter: blur(0.2px);
          }
          .ft-pdf-ai-question-tail-dust.is-main {
            offset-path: path("M 126 306 C 164 252 218 214 254 166 C 292 116 326 58 396 32");
          }
          .ft-pdf-ai-question-tail-dust.is-tail-1 {
            offset-path: path("M 126 306 C 196 338 282 352 356 326 C 430 300 486 322 566 282");
          }
          .ft-pdf-ai-question-tail-dust.is-tail-2 {
            offset-path: path("M 126 306 C 204 284 270 246 350 252 C 444 258 510 212 644 184");
          }
          .ft-pdf-ai-question-tail-dust.is-tail-3 {
            offset-path: path("M 126 306 C 178 230 240 180 326 150 C 414 120 474 76 594 72");
          }
          .ft-pdf-ai-question-tail-dust.is-tail-4 {
            offset-path: path("M 126 306 C 82 258 42 212 58 154 C 76 88 36 56 12 28");
          }
          .ft-pdf-ai-question-tail-dust.is-tail-5 {
            offset-path: path("M 126 306 C 78 332 24 330 10 286 C -8 228 40 194 88 168");
          }
          .ft-pdf-ai-question-connector-node {
            width: 11px;
            height: 11px;
            border-radius: 999px;
            background: rgba(255, 238, 224, 0.98);
            border: 2px solid rgba(139, 0, 0, 0.92);
            box-shadow:
              0 0 10px rgba(139, 0, 0, 0.88),
              0 0 16px rgba(255, 194, 84, 0.2);
            animation: ftPdfAiConnectorPulse 480ms ease-in-out 580ms 2;
          }
          .ft-pdf-ai-question-connector-node.is-source {
            left: 121px;
            top: 298px;
          }
          .ft-pdf-ai-question-connector-node.is-target {
            left: 392px;
            top: 28px;
            width: 9px;
            height: 9px;
            background: rgba(255, 132, 98, 0.96);
          }
          @keyframes ftPdfAiConnectorPulse {
            0%, 100% { transform: scale(0.82); opacity: 0.58; }
            50% { transform: scale(1.18); opacity: 1; }
          }
          @keyframes ftPdfAiConnectorLayerIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes ftPdfAiTailRootPulse {
            0%, 100% { transform: scale(0.86); opacity: 0.72; }
            45% { transform: scale(1.18); opacity: 1; }
            68% { transform: scale(0.98); opacity: 0.92; }
          }
          @keyframes ftPdfAiTailReach {
            from { stroke-dashoffset: 1; }
            to { stroke-dashoffset: 0; }
          }
          @keyframes ftPdfAiTailRetract {
            from { stroke-dashoffset: 0; opacity: 0.9; }
            to { stroke-dashoffset: 1; opacity: 0; }
          }
          @keyframes ftPdfAiTailCurlReach {
            0% {
              opacity: 0;
              stroke-dashoffset: 1;
            }
            18% {
              opacity: 0.9;
            }
            100% {
              opacity: 0.92;
              stroke-dashoffset: 0;
            }
          }
          @keyframes ftPdfAiTailTraceIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes ftPdfAiTailTraceOut {
            from { opacity: 1; stroke-dashoffset: 0; }
            to { opacity: 0; stroke-dashoffset: 1; }
          }
          @keyframes ftPdfAiTailChainFlow {
            from { stroke-dashoffset: 0.025; }
            to { stroke-dashoffset: -0.075; }
          }
          @keyframes ftPdfAiTailBitsOut {
            from {
              opacity: 1;
              transform: translate(-50%, -50%) rotate(calc(var(--r, 0deg) + var(--twist, 0deg))) scale(var(--s, 1));
              filter: blur(0);
            }
            to {
              opacity: 0;
              transform: translate(-50%, -50%) rotate(calc(var(--r, 0deg) + var(--twist, 0deg) - 18deg)) scale(0.22);
              filter: blur(4px);
            }
          }
          @keyframes ftPdfAiTailLinkReach {
            from {
              opacity: 0;
              transform: translate(-50%, -50%) rotate(calc(var(--r) + var(--twist))) scale(0.18);
            }
            42% {
              opacity: 0.8;
              transform: translate(-50%, -50%) rotate(calc(var(--r) + var(--twist) - 6deg)) scale(0.86);
            }
            68% {
              opacity: 1;
              transform: translate(-50%, -50%) rotate(calc(var(--r) + var(--twist) + 5deg)) scale(1.12);
            }
            to {
              opacity: 1;
              transform: translate(-50%, -50%) rotate(calc(var(--r) + var(--twist))) scale(1);
            }
          }
          @keyframes ftPdfAiTailLinkGlow {
            0%, 100% { filter: brightness(0.94) drop-shadow(0 0 0 rgba(255, 80, 130, 0)); }
            50% { filter: brightness(1.16) drop-shadow(0 0 5px rgba(255, 80, 130, 0.3)); }
          }
          @keyframes ftPdfAiTailSealIn {
            0% {
              opacity: 0;
              transform: translate(-50%, -50%) rotate(calc(var(--r, 0deg) - 36deg)) scale(calc(0.18 * var(--s, 1)));
              filter: blur(3px);
            }
            52% {
              opacity: 1;
              transform: translate(-50%, -50%) rotate(calc(var(--r, 0deg) + 8deg)) scale(calc(1.12 * var(--s, 1)));
              filter: blur(0);
            }
            100% {
              opacity: 0.94;
              transform: translate(-50%, -50%) rotate(var(--r, 0deg)) scale(var(--s, 1));
              filter: blur(0);
            }
          }
          @keyframes ftPdfAiTailSealPulse {
            0%, 100% {
              opacity: 0.74;
              box-shadow:
                inset 0 0 0 1px rgba(255, 178, 166, 0.14),
                0 0 12px rgba(139, 0, 18, 0.46),
                0 0 26px rgba(255, 80, 130, 0.12);
            }
            48% {
              opacity: 1;
              box-shadow:
                inset 0 0 0 1px rgba(255, 210, 190, 0.24),
                0 0 20px rgba(139, 0, 18, 0.74),
                0 0 44px rgba(255, 80, 130, 0.26);
            }
          }
          @keyframes ftPdfAiTailSealSpin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes ftPdfAiTailSealCounterSpin {
            from { transform: rotate(0deg) scale(0.92); }
            to { transform: rotate(-360deg) scale(0.92); }
          }
          @keyframes ftPdfAiTailDust {
            0% {
              opacity: 0;
              offset-distance: 2%;
              transform: translate(-50%, -50%) scale(0.35);
            }
            18% {
              opacity: 0.95;
              transform: translate(-50%, -50%) scale(1);
            }
            76% {
              opacity: 0.72;
              offset-distance: 84%;
              transform: translate(-50%, -50%) scale(0.66);
            }
            100% {
              opacity: 0;
              offset-distance: 100%;
              transform: translate(-50%, -50%) scale(0.18);
            }
          }
          .ft-pdf-ai-question-answer-stage {
            position: relative;
            z-index: 2;
            display: grid;
            gap: 9px;
            margin-top: 8px;
            max-height: var(--ft-mishika-answer-max-h);
            overflow: visible;
          }
          .ft-pdf-ai-question-panel.is-viewport-constrained .ft-pdf-ai-question-answer-stage {
            overflow: auto;
            overscroll-behavior: contain;
            scrollbar-width: thin;
          }
          .ft-pdf-ai-question-answer-stage.is-waiting {
            min-height: 84px;
          }
          .ft-pdf-ai-question-info-node {
            display: grid;
            justify-items: end;
            padding: 12px 2px 0;
            opacity: 0;
            transform: translateX(-18px) rotateY(-14deg);
            animation: ftPdfAiAnswerIn 420ms cubic-bezier(.16,.86,.2,1) forwards;
          }
          .ft-pdf-ai-question-gate {
            display: grid;
            gap: 9px;
          }
          .ft-pdf-ai-question-gate-choice {
            display: grid;
            grid-template-columns: 32px minmax(0, 1fr);
            grid-template-areas:
              "mark label"
              "mark detail";
            align-items: center;
            gap: 2px 10px;
            min-height: 58px;
            padding: 10px 12px;
            border: 1px solid rgba(255,231,138,0.32);
            border-radius: 14px;
            color: #f9fffd;
            background:
              radial-gradient(circle at 18% 22%, rgba(255,231,138,0.16), transparent 34%),
              linear-gradient(135deg, rgba(126,255,232,0.1), rgba(255,135,170,0.08)),
              rgba(5,15,26,0.86);
            box-shadow: 0 14px 32px rgba(0,0,0,0.24);
            text-align: left;
            cursor: pointer;
            opacity: 0;
            transform: translateX(-18px) rotateY(-14deg);
            animation: ftPdfAiAnswerIn 420ms cubic-bezier(.16,.86,.2,1) forwards;
            animation-delay: calc(var(--answer-index, 0) * 72ms);
          }
          .ft-pdf-ai-question-gate-choice:hover,
          .ft-pdf-ai-question-gate-choice:focus-visible {
            border-color: rgba(126,255,232,0.76);
            background:
              radial-gradient(circle at 18% 22%, rgba(255,231,138,0.28), transparent 35%),
              linear-gradient(135deg, rgba(126,255,232,0.22), rgba(255,135,170,0.14)),
              rgba(7,22,34,0.94);
            box-shadow: 0 0 24px rgba(126,255,232,0.2), 0 16px 34px rgba(0,0,0,0.28);
            outline: none;
          }
          .ft-pdf-ai-question-gate-choice span {
            grid-area: mark;
            display: grid;
            place-items: center;
            width: 28px;
            height: 28px;
            border-radius: 9px;
            color: #1d0b18;
            background: linear-gradient(135deg, #ffe78a, #7effe8);
            font-weight: 950;
          }
          .ft-pdf-ai-question-gate-choice b {
            grid-area: label;
            min-width: 0;
            font-size: 14px;
            font-weight: 950;
          }
          .ft-pdf-ai-question-gate-choice em {
            grid-area: detail;
            min-width: 0;
            color: rgba(243,255,253,0.7);
            font-size: 12px;
            font-style: normal;
            font-weight: 800;
          }
          .ft-pdf-ai-question-answer,
          .ft-pdf-ai-question-input-answer,
          .ft-pdf-ai-question-speak-answer {
            border: 1px solid rgba(126, 255, 232, 0.26);
            border-radius: 14px;
            background: rgba(5, 15, 26, 0.84);
            color: #f3fffd;
            box-shadow: 0 16px 36px rgba(0,0,0,0.26);
          }
          .ft-pdf-ai-question-answer {
            display: grid;
            grid-template-columns: 30px minmax(0, 1fr);
            align-items: center;
            gap: 9px;
            min-height: 48px;
            padding: 9px 11px;
            text-align: left;
            cursor: pointer;
            opacity: 0;
            transform: translateX(-18px) rotateY(-14deg);
            animation: ftPdfAiAnswerIn 420ms cubic-bezier(.16,.86,.2,1) forwards;
            animation-delay: calc(var(--answer-index, 0) * 72ms);
          }
          .ft-pdf-ai-question-input-answer {
            display: grid;
            grid-template-columns: minmax(130px, 1fr) 58px 58px auto auto;
            align-items: stretch;
            gap: 8px;
            min-height: 50px;
            padding: 9px;
            position: relative;
            opacity: 0;
            transform: translateX(-18px) rotateY(-14deg);
            animation: ftPdfAiAnswerIn 420ms cubic-bezier(.16,.86,.2,1) forwards;
          }
          .ft-pdf-ai-question-speak-answer {
            display: grid;
            gap: 10px;
            min-height: 88px;
            padding: 12px;
            position: relative;
            opacity: 0;
            transform: translateX(-18px) rotateY(-14deg);
            animation: ftPdfAiAnswerIn 420ms cubic-bezier(.16,.86,.2,1) forwards;
            overflow: hidden;
          }
          .ft-pdf-ai-question-speak-answer::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
              radial-gradient(circle at 18% 20%, rgba(126,255,232,0.16), transparent 30%),
              linear-gradient(115deg, transparent 0 38%, rgba(126,255,232,0.08) 46%, transparent 56% 100%);
            opacity: 0.72;
          }
          .ft-pdf-ai-question-speak-head {
            display: grid;
            grid-template-columns: 64px minmax(0, 1fr) auto;
            align-items: center;
            gap: 8px;
            position: relative;
            z-index: 1;
          }
          .ft-pdf-ai-question-speak-head button {
            min-height: 34px;
            border: 1px solid rgba(126,255,232,0.24);
            border-radius: 11px;
            background: rgba(3,10,18,0.82);
            color: #7effe8;
            font-weight: 900;
            cursor: pointer;
          }
          .ft-pdf-ai-question-speak-head button[hidden] {
            display: none;
          }
          .ft-pdf-ai-question-show-answer {
            min-width: 92px;
            padding: 0 10px;
            color: #ffe78a !important;
            border-color: rgba(255,231,138,0.42) !important;
            background:
              linear-gradient(135deg, rgba(255,231,138,0.12), rgba(126,255,232,0.1)),
              rgba(3,10,18,0.86) !important;
            box-shadow: 0 0 16px rgba(255,231,138,0.12);
          }
          .ft-pdf-ai-question-show-answer.is-ready {
            animation: ftPdfAiAnswerPulse 1380ms ease-in-out infinite;
          }
          .ft-pdf-ai-question-speak-answer.is-listening .ft-pdf-ai-question-speak-head button {
            border-color: rgba(255,231,138,0.78);
            color: #09131d;
            background: linear-gradient(135deg, #ffe78a, #7effe8);
            box-shadow: 0 0 20px rgba(126,255,232,0.34);
          }
          .ft-pdf-ai-question-speak-head span {
            color: rgba(243,255,253,0.78);
            font-size: 12px;
            font-weight: 850;
            min-width: 0;
          }
          .ft-pdf-ai-question-speak-live {
            display: none;
          }
          .ft-pdf-ai-question-speak-tokens {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            position: relative;
            z-index: 1;
          }
          .ft-pdf-ai-question-speak-tokens span {
            display: inline-grid;
            place-items: center;
            min-width: 34px;
            min-height: 30px;
            padding: 5px 10px;
            border: 1px solid rgba(126,255,232,0.16);
            border-radius: 8px;
            background:
              linear-gradient(180deg, rgba(255,255,255,0.09), rgba(255,255,255,0.03)),
              rgba(3,10,18,0.78);
            color: transparent;
            font-size: 12px;
            font-weight: 900;
            text-shadow: 0 0 10px rgba(126,255,232,0.18);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.035), 0 8px 18px rgba(0,0,0,0.18);
            transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, color 180ms ease, box-shadow 180ms ease;
          }
          .ft-pdf-ai-question-speak-answer.is-listening .ft-pdf-ai-question-speak-tokens span,
          .ft-pdf-ai-question-speak-answer.is-pristine .ft-pdf-ai-question-speak-tokens span {
            opacity: 0.72;
          }
          .ft-pdf-ai-question-speak-tokens span.is-hit {
            border-color: rgba(122,255,181,0.86);
            background:
              radial-gradient(circle at 28% 18%, rgba(255,255,255,0.42), transparent 26%),
              linear-gradient(135deg, rgba(32,162,95,0.96), rgba(11,92,61,0.94));
            color: #eafff3;
            text-shadow: 0 1px 0 rgba(0,0,0,0.24);
            transform: translateY(-2px);
            box-shadow: 0 0 18px rgba(122,255,181,0.34), 0 10px 20px rgba(0,0,0,0.24);
          }
          .ft-pdf-ai-question-speak-answer.is-answer-revealed .ft-pdf-ai-question-speak-tokens span {
            border-color: rgba(255,231,138,0.82);
            background:
              radial-gradient(circle at 26% 18%, rgba(255,255,255,0.38), transparent 28%),
              linear-gradient(135deg, rgba(255,231,138,0.92), rgba(126,255,232,0.86));
            color: #07131d;
            text-shadow: none;
            box-shadow: 0 0 18px rgba(255,231,138,0.26), 0 10px 20px rgba(0,0,0,0.24);
          }
          .ft-pdf-ai-question-speak-answer::after {
            content: attr(data-score);
            position: absolute;
            right: 10px;
            bottom: -20px;
            color: rgba(243,255,253,0.72);
            font-size: 11px;
            font-weight: 850;
          }
          .ft-pdf-ai-question-speak-answer.is-holding {
            border-color: rgba(255,231,138,0.68);
            box-shadow: 0 16px 36px rgba(0,0,0,0.26), 0 0 28px rgba(255,231,138,0.18);
          }
          .ft-pdf-ai-question-theory-answer {
            gap: 12px;
          }
          .ft-pdf-ai-question-theory-counter {
            justify-self: end;
            min-width: 38px;
            display: inline-grid;
            place-items: center;
            padding: 5px 8px;
            border: 1px solid rgba(255,231,138,0.34);
            border-radius: 10px;
            background: rgba(255,231,138,0.1);
            color: #ffe78a;
            font-size: 11px;
            font-weight: 950;
            line-height: 1;
            box-shadow: inset 0 0 12px rgba(255,231,138,0.06);
          }
          .ft-pdf-ai-question-theory-counter.is-complete {
            border-color: rgba(122,255,181,0.72);
            background: rgba(16,62,42,0.58);
            color: #bfffd4;
            box-shadow: 0 0 16px rgba(122,255,181,0.22), inset 0 0 12px rgba(122,255,181,0.08);
          }
          .ft-pdf-ai-question-theory-lines {
            display: grid;
            gap: 9px;
            position: relative;
            z-index: 1;
          }
          .ft-pdf-ai-question-theory-line {
            display: grid;
            grid-template-columns: 28px minmax(0, 1fr) auto;
            gap: 8px;
            align-items: start;
            padding: 8px;
            border: 1px solid rgba(126,255,232,0.12);
            border-radius: 10px;
            background: rgba(3,10,18,0.46);
            animation: ftPdfAiAnswerIn 320ms cubic-bezier(.16,.86,.2,1) both;
            animation-delay: calc(var(--theory-index, 0) * 55ms);
          }
          .ft-pdf-ai-question-theory-line.is-line-pass {
            border-color: rgba(122,255,181,0.52);
            background: rgba(16,62,42,0.42);
          }
          .ft-pdf-ai-question-theory-line b {
            display: grid;
            place-items: center;
            width: 24px;
            height: 24px;
            border-radius: 8px;
            background: rgba(126,255,232,0.12);
            color: #7effe8;
            font-size: 11px;
          }
          .ft-pdf-ai-question-theory-line p {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 0;
          }
          .ft-pdf-ai-question-theory-line em {
            align-self: start;
            min-width: 42px;
            padding: 5px 7px;
            border-radius: 8px;
            background: rgba(255,255,255,0.065);
            color: rgba(243,255,253,0.74);
            font-size: 11px;
            font-style: normal;
            font-weight: 900;
            text-align: center;
          }
          .ft-pdf-ai-question-theory-line.is-line-pass em {
            background: rgba(122,255,181,0.16);
            color: #bfffd4;
          }
          .ft-pdf-ai-question-theory-line span {
            display: inline-grid;
            place-items: center;
            min-height: 27px;
            padding: 4px 9px;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px;
            background: rgba(255,255,255,0.055);
            color: rgba(243,255,253,0.86);
            font-size: 12px;
            font-weight: 900;
            transition: transform 180ms ease, color 180ms ease, background 180ms ease, box-shadow 180ms ease;
          }
          .ft-pdf-ai-question-theory-answer.is-theory-hidden .ft-pdf-ai-question-theory-line span {
            color: transparent;
            background:
              linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.025)),
              rgba(3,10,18,0.84);
          }
          .ft-pdf-ai-question-theory-line span.is-hit,
          .ft-pdf-ai-question-theory-answer.is-theory-hidden .ft-pdf-ai-question-theory-line span.is-hit {
            border-color: rgba(122,255,181,0.86);
            background:
              radial-gradient(circle at 28% 18%, rgba(255,255,255,0.4), transparent 26%),
              linear-gradient(135deg, rgba(32,162,95,0.96), rgba(11,92,61,0.94));
            color: #eafff3;
            transform: translateY(-1px);
            box-shadow: 0 0 16px rgba(122,255,181,0.32), 0 8px 16px rgba(0,0,0,0.22);
          }
          .ft-pdf-ai-question-transcript-card {
            display: grid;
            gap: 8px;
            position: absolute;
            left: var(--ft-mishika-transcript-x);
            top: calc(var(--ft-mishika-dialogue-y) + 138px);
            z-index: 8;
            width: var(--ft-mishika-transcript-w);
            max-height: min(230px, calc(100vh - 190px));
            overflow: auto;
            pointer-events: auto;
            padding: 10px;
            border: 1px solid rgba(255,231,138,0.18);
            border-radius: 10px;
            background:
              radial-gradient(circle at 20% 12%, rgba(255,231,138,0.14), transparent 34%),
              rgba(3,10,18,0.78);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.035), 0 16px 34px rgba(0,0,0,0.28), 0 0 22px rgba(255,231,138,0.08);
            opacity: 0;
            transform: translateX(14px) scale(0.96);
            animation: ftPdfAiTranscriptPanelIn 320ms cubic-bezier(.16,.86,.2,1) 120ms both;
          }
          .ft-pdf-ai-question-panel.is-switching .ft-pdf-ai-question-transcript-card,
          .ft-pdf-ai-question-panel.is-closing .ft-pdf-ai-question-transcript-card {
            pointer-events: none;
            animation: ftPdfAiTranscriptPanelOut 220ms ease both;
          }
          .ft-pdf-ai-question-transcript-card.is-empty {
            opacity: 0.74;
          }
          .ft-pdf-ai-question-transcript-card strong {
            color: #ffe78a;
            font-size: 11px;
            letter-spacing: 0;
            text-transform: uppercase;
          }
          .ft-pdf-ai-question-transcript-card section {
            display: grid;
            gap: 5px;
            padding: 7px;
            border: 1px solid rgba(126,255,232,0.12);
            border-radius: 9px;
            background: rgba(255,255,255,0.045);
          }
          .ft-pdf-ai-question-transcript-card section.is-active {
            border-color: rgba(122,255,181,0.42);
            background: rgba(16,62,42,0.34);
          }
          .ft-pdf-ai-question-transcript-card section b {
            color: rgba(126,255,232,0.78);
            font-size: 10px;
            text-transform: uppercase;
          }
          .ft-pdf-ai-question-transcript-card section div {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
          }
          .ft-pdf-ai-question-transcript-card span {
            display: inline-grid;
            place-items: center;
            min-height: 24px;
            padding: 3px 7px;
            border-radius: 7px;
            background: rgba(126,255,232,0.1);
            color: rgba(243,255,253,0.9);
            font-size: 11px;
            font-weight: 850;
            animation: ftPdfAiTranscriptBlockIn 180ms ease both;
          }
          .ft-pdf-ai-question-transcript-card p,
          .ft-pdf-ai-question-transcript-card i {
            margin: 0;
            color: rgba(243,255,253,0.55);
            font-size: 11px;
            font-style: normal;
            font-weight: 800;
          }
          @keyframes ftPdfAiTranscriptBlockIn {
            from { opacity: 0; transform: translateY(4px) scale(0.96); }
            to { opacity: 1; transform: translateY(0) scale(1); }
          }
          @keyframes ftPdfAiTranscriptPanelIn {
            from { opacity: 0; transform: translateX(14px) scale(0.96); }
            to { opacity: 1; transform: translateX(0) scale(1); }
          }
          @keyframes ftPdfAiTranscriptPanelOut {
            from { opacity: 1; transform: translateX(0) scale(1); }
            to { opacity: 0; transform: translateX(14px) scale(0.96); }
          }
          @media (max-width: 1180px) and (min-width: 761px) {
            .ft-pdf-ai-question-transcript-card {
              left: var(--ft-mishika-dialogue-x);
              right: auto;
              top: auto;
              bottom: 8px;
              width: min(50vw, var(--ft-mishika-dialogue-max-w));
              max-height: 118px;
            }
          }
          @media (max-width: 760px) {
            .ft-pdf-ai-question-transcript-card {
              left: 10px;
              right: 10px;
              top: auto;
              bottom: 8px;
              width: auto;
              max-height: 130px;
            }
          }
          .ft-pdf-ai-question-input-answer textarea,
          .ft-pdf-ai-question-input-answer button,
          .ft-pdf-ai-question-input-answer select,
          .ft-pdf-ai-question-type,
          .ft-pdf-ai-question-match-percent {
            min-width: 0;
            border: 1px solid rgba(126,255,232,0.24);
            border-radius: 11px;
            background: rgba(3,10,18,0.82);
            color: #f3fffd;
            outline: none;
          }
          .ft-pdf-ai-question-input-answer textarea,
          .ft-pdf-ai-question-input-answer select,
          .ft-pdf-ai-question-type,
          .ft-pdf-ai-question-match-percent {
            padding: 9px 10px;
          }
          .ft-pdf-ai-question-input-answer textarea {
            width: 100%;
            min-height: 42px;
            max-height: 180px;
            resize: none;
            overflow: auto;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            line-height: 1.35;
            font: inherit;
          }
          .ft-pdf-ai-question-input-feedback {
            grid-column: 1 / -1;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            min-height: 28px;
            padding: 6px 7px;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            background: rgba(3,10,18,0.46);
          }
          .ft-pdf-ai-question-input-feedback[hidden] {
            display: none;
          }
          .ft-pdf-ai-question-input-feedback span {
            display: inline-grid;
            place-items: center;
            min-height: 24px;
            padding: 3px 8px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 900;
            line-height: 1.1;
          }
          .ft-pdf-ai-question-input-feedback span.is-hit {
            border: 1px solid rgba(122,255,181,0.72);
            background: rgba(16,62,42,0.76);
            color: #bfffd4;
          }
          .ft-pdf-ai-question-input-feedback span.is-extra {
            border: 1px solid rgba(255,122,146,0.82);
            background: rgba(94,18,34,0.84);
            color: #ffd2da;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.045), 0 0 14px rgba(255,74,108,0.16);
          }
          .ft-pdf-ai-question-input-answer button {
            padding: 0 14px;
            color: #ffe78a;
            font-weight: 900;
            cursor: pointer;
          }
          .ft-pdf-ai-question-input-answer button[hidden] {
            display: none;
          }
          .ft-pdf-ai-question-input-answer button[data-ai-question-mic] {
            padding: 0 10px;
            color: #7effe8;
          }
          .ft-pdf-ai-question-input-answer.is-listening button[data-ai-question-mic] {
            border-color: rgba(255,231,138,0.78);
            color: #09131d;
            background: linear-gradient(135deg, #ffe78a, #7effe8);
            box-shadow: 0 0 20px rgba(126,255,232,0.34);
          }
          .ft-pdf-ai-question-input-answer::after {
            content: attr(data-score);
            position: absolute;
            right: 10px;
            bottom: -20px;
            color: rgba(243,255,253,0.72);
            font-size: 11px;
            font-weight: 850;
          }
          .ft-pdf-ai-question-input-answer.is-correct {
            border-color: rgba(122,255,181,0.82);
            background: rgba(16, 62, 42, 0.88);
          }
          .ft-pdf-ai-question-speak-answer.is-correct {
            border-color: rgba(122,255,181,0.82);
            background: rgba(16, 62, 42, 0.88);
          }
          .ft-pdf-ai-question-input-answer.is-wrong,
          .ft-pdf-ai-question-speak-answer.is-wrong {
            border-color: rgba(255,135,170,0.82);
            background: rgba(72, 22, 36, 0.88);
          }
          .ft-pdf-ai-question-answer span {
            display: grid;
            place-items: center;
            width: 28px;
            height: 28px;
            border-radius: 9px;
            background: rgba(255, 231, 138, 0.16);
            color: #ffe78a;
            font-weight: 950;
          }
          .ft-pdf-ai-question-answer b {
            font-size: 13px;
            line-height: 1.35;
          }
          .ft-pdf-ai-question-answer.is-picked.is-correct {
            border-color: rgba(122,255,181,0.82);
            background: rgba(16, 62, 42, 0.88);
          }
          .ft-pdf-ai-question-answer.is-picked.is-wrong {
            border-color: rgba(255,135,170,0.82);
            background: rgba(72, 22, 36, 0.88);
          }
          .ft-pdf-ai-question-next {
            justify-self: end;
            display: inline-grid;
            grid-template-columns: auto auto;
            align-items: center;
            gap: 8px;
            min-height: 38px;
            padding: 8px 12px;
            border: 1px solid rgba(255, 231, 138, 0.52);
            border-radius: 13px;
            background:
              radial-gradient(circle at 18% 20%, rgba(255,231,138,0.34), transparent 34%),
              linear-gradient(135deg, rgba(78, 8, 20, 0.96), rgba(14, 5, 14, 0.94));
            color: #fff7d0;
            box-shadow: 0 14px 34px rgba(0,0,0,0.3), 0 0 24px rgba(126, 12, 28, 0.42);
            cursor: pointer;
            font-weight: 950;
            opacity: 0;
            transform: translateY(10px) scale(0.94);
            animation: ftPdfAiAnswerIn 360ms cubic-bezier(.16,.86,.2,1) forwards;
          }
          .ft-pdf-ai-question-next b {
            display: grid;
            place-items: center;
            min-width: 38px;
            height: 22px;
            border-radius: 999px;
            background: rgba(255, 231, 138, 0.16);
            color: #ffe78a;
            font-size: 11px;
          }
          .ft-pdf-ai-question-next:hover {
            border-color: rgba(255, 231, 138, 0.92);
            transform: translateY(0) scale(1.02);
            filter: brightness(1.12);
          }
          .ft-pdf-ai-question-next-reserve {
            justify-self: end;
            min-height: 38px;
            width: 118px;
            pointer-events: none;
            visibility: hidden;
          }
          @keyframes ftPdfMikasaWindowBurst {
            0% { opacity: 0; transform: translateY(22px) rotateX(18deg) scale(0.22, 0.06); clip-path: inset(50% 45% 50% 0 round 16px); filter: brightness(1.6); }
            44% { opacity: 1; transform: translateY(-2px) rotateX(0deg) scale(1.05, 0.78); clip-path: inset(8% 5% 8% 0 round 16px); filter: brightness(1.22); }
            72% { transform: translateY(0) scale(0.98, 1.03); }
            100% { opacity: 1; transform: translateY(0) rotateX(0deg) scale(1); clip-path: inset(0 0 0 0 round 16px); filter: brightness(1); }
          }
          @keyframes ftPdfMikasaStageBurst {
            0% { opacity: 0; transform: translateY(26px) scale(0.78); }
            48% { opacity: 1; transform: translateY(-3px) scale(1.015); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
          }
          @keyframes ftPdfMikasaPanelOut {
            0% { opacity: 1; transform: translate(0, 0) scale(1); filter: blur(0); }
            100% { opacity: 0; transform: translate(-26px, 22px) scale(0.88); filter: blur(8px); }
          }
          @keyframes ftPdfMikasaNodeOut {
            0% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
            100% { opacity: 0; transform: translateY(16px) scale(0.94); filter: blur(5px); }
          }
          @keyframes ftPdfMikasaGifRise {
            from { opacity: 0; transform: translateX(-50%) translateY(20px) scale(0.94); filter: brightness(1.4) saturate(1.2); }
            to { opacity: 1; transform: translateX(-50%) translateY(0) scale(1); filter: brightness(1) saturate(1); }
          }
          @keyframes ftPdfMikasaWindowShine {
            from { left: -42%; opacity: 0; }
            14% { opacity: 1; }
            42% { opacity: 0.75; }
            to { left: 118%; opacity: 0; }
          }
          @keyframes ftPdfMikasaConnectorDraw {
            from { opacity: 0; transform: scaleX(0.05); transform-origin: left center; }
            to { opacity: 1; transform: scaleX(1); transform-origin: left center; }
          }
          @keyframes ftPdfMikasaDialogueBurst {
            from { opacity: 0; transform: translateX(-18px) scale(0.96); }
            to { opacity: 1; transform: translateX(0) scale(1); }
          }
          @keyframes ftPdfMikasaFlameChipIn {
            0% {
              opacity: 0;
              transform: translate(-50%, -50%) rotate(calc(var(--r) - 18deg)) scale(0.12);
            }
            66% {
              opacity: 1;
              transform: translate(-50%, -50%) rotate(calc(var(--r) + 5deg)) scale(calc(var(--s) * 1.08));
            }
            100% {
              opacity: 1;
              transform: translate(-50%, -50%) rotate(var(--r)) scale(var(--s));
            }
          }
          @keyframes ftPdfMikasaFlameChipFlicker {
            0%, 100% {
              opacity: 0.9;
              filter: saturate(0.95);
            }
            34% {
              opacity: 1;
              transform: translate(-50%, -50%) rotate(calc(var(--r) - 2deg)) scale(calc(var(--s) * 1.05));
              filter: saturate(1.16) brightness(1.08);
            }
            68% {
              opacity: 0.84;
              transform: translate(-50%, -50%) rotate(calc(var(--r) + 1deg)) scale(calc(var(--s) * 0.96));
              filter: saturate(0.88) brightness(0.96);
            }
          }
          @keyframes ftPdfAiAnswerIn {
            to { opacity: 1; transform: translateX(0) rotateY(0deg); }
          }
          @keyframes ftPdfAiAnswerPulse {
            0%, 100% { box-shadow: 0 0 14px rgba(255,231,138,0.12); transform: translateY(0); }
            50% { box-shadow: 0 0 22px rgba(255,231,138,0.28), 0 0 16px rgba(126,255,232,0.18); transform: translateY(-1px); }
          }
          @media (max-width: 760px) {
            .ft-pdf-ai-question-grid {
              grid-template-columns: minmax(0, 1fr);
            }
            .ft-pdf-ai-question-panel {
              left: 10px;
              right: 10px;
              bottom: var(--ft-mishika-panel-bottom, 10px);
              width: auto;
              min-height: 0;
              display: grid;
              gap: 8px;
            }
            .ft-pdf-ai-question-mikasa-card {
              width: auto;
              min-height: 250px;
            }
            .ft-pdf-ai-question-dialogue-stack {
              position: relative;
              left: auto;
              top: auto;
              width: auto;
            }
            .ft-pdf-ai-question-flame-ring {
              inset: 0;
            }
            .ft-pdf-ai-question-flame-chain.is-top-left {
              left: 14px;
              top: 10px;
            }
            .ft-pdf-ai-question-flame-chain.is-bottom-right {
              right: 14px;
              bottom: 10px;
            }
            .ft-pdf-ai-question-flame-chain i {
              width: 9px;
              height: 4px;
            }
            .ft-pdf-ai-question-mikasa {
              height: 190px;
            }
            .ft-pdf-ai-question-mikasa img {
              width: 190px;
              height: 190px;
            }
            .ft-pdf-ai-question-connector { display: none; }
          }
          .ft-pdf-ai-notice-fireball {
            --pdf-ai-bubble-base: min(320px, calc(100vw - 34px));
            --pdf-ai-bubble-width: var(--pdf-ai-bubble-base);
            position: fixed;
            left: 0;
            top: 0;
            z-index: 2320;
            width: min(calc(var(--pdf-ai-bubble-width) + 20px), calc(100vw - 28px));
            display: grid;
            grid-template-rows: auto auto;
            justify-items: center;
            align-items: end;
            gap: 18px;
            pointer-events: none;
            transform: translate3d(var(--pdf-ai-fireball-x, 24px), var(--pdf-ai-fireball-y, calc(100vh - 180px)), 0) scale(1);
            transition: opacity 220ms ease, filter 260ms ease;
            will-change: transform, opacity;
          }
          .ft-pdf-ai-notice-fireball.is-hidden {
            opacity: 0;
            pointer-events: none;
            transform: translate3d(var(--pdf-ai-fireball-x, 24px), calc(var(--pdf-ai-fireball-y, 70vh) + 18px), 0) scale(0.86);
          }
          .ft-pdf-ai-notice-fireball:not(.is-hidden) {
            opacity: 1;
            pointer-events: none;
            transform: translate3d(var(--pdf-ai-fireball-x, 24px), var(--pdf-ai-fireball-y, calc(100vh - 180px)), 0) scale(1);
          }
          .ft-pdf-ai-notice-fireball .ft-world-fireball {
            width: 74px;
            height: 74px;
            pointer-events: auto;
            transform: scaleX(var(--world-facing, 1));
            transform-origin: 50% 88%;
            animation: ftPdfAiFireballIdle 2.8s ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-entering .ft-world-fireball,
          .ft-pdf-ai-notice-fireball.is-roaming .ft-world-fireball {
            animation: ftPdfAiFireballRun 620ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-speaking .ft-world-fireball {
            animation: ftPdfAiFireballTalk 520ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-jumping .ft-world-fireball {
            animation: ftPdfAiFireballJump 480ms cubic-bezier(0.2, 0.9, 0.2, 1) 1;
          }
          .ft-pdf-ai-notice-bubble {
            position: relative;
            width: var(--pdf-ai-bubble-width);
            min-height: 62px;
            max-height: min(50vh, calc(100vh - 32px));
            overflow: auto;
            overflow-x: hidden;
            padding: 44px 118px 34px 28px;
            scroll-padding: 24px 28px 34px 24px;
            border: 1px solid rgba(132, 255, 246, 0.72);
            border-radius: 22px 22px 24px 16px;
            clip-path: polygon(0 18px, 18px 0, calc(100% - 18px) 0, 100% 18px, 100% calc(100% - 28px), calc(100% - 20px) 100%, 18px 100%, 0 calc(100% - 18px));
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 0.96) 0 34px, transparent 34px) 14px 14px / 78px 3px no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.86) 0 34px, transparent 34px) 14px 14px / 3px 78px no-repeat,
              linear-gradient(270deg, rgba(245, 82, 255, 0.86) 0 34px, transparent 34px) calc(100% - 14px) 14px / 78px 3px no-repeat,
              linear-gradient(180deg, rgba(245, 82, 255, 0.72) 0 34px, transparent 34px) calc(100% - 17px) 14px / 3px 78px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.70) 0 34px, transparent 34px) 14px calc(100% - 17px) / 78px 3px no-repeat,
              linear-gradient(0deg, rgba(245, 82, 255, 0.58) 0 34px, transparent 34px) 14px calc(100% - 92px) / 3px 78px no-repeat,
              linear-gradient(270deg, rgba(126, 255, 232, 0.86) 0 34px, transparent 34px) calc(100% - 14px) calc(100% - 17px) / 78px 3px no-repeat,
              linear-gradient(0deg, rgba(126, 255, 232, 0.74) 0 34px, transparent 34px) calc(100% - 17px) calc(100% - 92px) / 3px 78px no-repeat,
              linear-gradient(180deg, rgba(160, 255, 248, 0.16), transparent 26px) 0 0 / 100% 100% no-repeat,
              linear-gradient(0deg, rgba(245, 82, 255, 0.12), transparent 30px) 0 100% / 100% 100% no-repeat,
              repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.045) 0 1px, transparent 1px 7px),
              radial-gradient(circle at calc(100% - 90px) 48px, rgba(94, 255, 245, 0.22), transparent 0 18px, rgba(94, 255, 245, 0.12) 19px 31px, transparent 32px),
              radial-gradient(circle at calc(100% - 90px) 48px, transparent 0 34px, rgba(245, 82, 255, 0.14) 35px 36px, transparent 37px),
              linear-gradient(90deg, rgba(94, 255, 245, 0.92), rgba(94, 255, 245, 0.18) 34%, transparent 35%) 18px 15px / calc(100% - 96px) 3px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.78), rgba(245, 82, 255, 0.16) 44%, transparent 45%) 18px 24px / 44% 2px no-repeat,
              linear-gradient(90deg, rgba(94, 255, 245, 0.12), transparent 14%, transparent 82%, rgba(245, 82, 255, 0.18)) 0 42px / 100% 1px no-repeat,
              radial-gradient(circle at 12% 10%, rgba(94, 255, 245, 0.18), transparent 30%),
              radial-gradient(circle at 86% 0%, rgba(245, 82, 255, 0.22), transparent 30%),
              linear-gradient(145deg, rgba(7, 21, 36, 0.94), rgba(4, 10, 22, 0.96) 64%, rgba(7, 24, 38, 0.94));
            color: #f5fffc;
            line-height: 1.45;
            font-size: 14px;
            backdrop-filter: blur(14px) saturate(1.35);
            box-shadow:
              0 20px 48px rgba(0, 0, 0, 0.34),
              0 0 0 1px rgba(255, 255, 255, 0.10),
              0 0 28px rgba(93, 232, 255, 0.28),
              0 0 46px rgba(245, 82, 255, 0.12),
              inset 0 1px 0 rgba(255, 255, 255, 0.22),
              inset 0 26px 30px rgba(126, 255, 232, 0.08),
              inset 0 -30px 34px rgba(4, 8, 18, 0.72),
              inset 0 0 28px rgba(99, 248, 255, 0.10);
            transform-origin: 50% 100%;
            pointer-events: auto;
            cursor: grab;
            touch-action: none;
            user-select: none;
            -webkit-user-select: none;
            scrollbar-width: none;
            -ms-overflow-style: none;
            -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 12px, #000 calc(100% - 12px), transparent 100%);
            mask-image: linear-gradient(to bottom, transparent 0, #000 12px, #000 calc(100% - 12px), transparent 100%);
          }
          .ft-pdf-ai-notice-bubble::-webkit-scrollbar {
            width: 0;
            height: 0;
          }
          .ft-pdf-ai-notice-bubble::before {
            content: "";
            position: absolute;
            inset: 8px;
            z-index: 0;
            border-radius: 18px 18px 20px 12px;
            border: 1px solid rgba(126, 255, 232, 0.18);
            background:
              radial-gradient(circle at calc(100% - 74px) 44px, rgba(94, 255, 245, 0.20), transparent 0 12px, rgba(94, 255, 245, 0.10) 13px 26px, transparent 27px),
              radial-gradient(circle at calc(100% - 74px) 44px, transparent 0 31px, rgba(245, 82, 255, 0.14) 32px 33px, transparent 34px),
              linear-gradient(90deg, rgba(126, 255, 232, 0.42) 0 30px, transparent 30px calc(100% - 46px), rgba(245, 82, 255, 0.34) calc(100% - 46px) 100%) 0 0 / 100% 1px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.26) 0 34px, transparent 34px calc(100% - 30px), rgba(126, 255, 232, 0.40) calc(100% - 30px) 100%) 0 100% / 100% 1px no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.28) 0 24px, transparent 24px calc(100% - 24px), rgba(126, 255, 232, 0.16) calc(100% - 24px) 100%) 0 0 / 1px 100% no-repeat,
              linear-gradient(180deg, rgba(245, 82, 255, 0.18) 0 24px, transparent 24px calc(100% - 24px), rgba(126, 255, 232, 0.30) calc(100% - 24px) 100%) 100% 0 / 1px 100% no-repeat,
              linear-gradient(90deg, transparent, rgba(124, 255, 244, 0.10), transparent) 0 0 / 180% 100% no-repeat;
            opacity: 0.70;
            pointer-events: none;
            animation: ftPdfAiNoticeBubbleScan 5.4s linear infinite;
            box-shadow: none;
          }
          .ft-pdf-ai-notice-fireball.is-dragging {
            transition: none;
            filter: drop-shadow(0 16px 22px rgba(0, 0, 0, 0.26));
          }
          .ft-pdf-ai-notice-fireball.is-dragging .ft-pdf-ai-notice-bubble {
            cursor: grabbing;
            animation: ftPdfAiBubbleCarry 520ms ease-in-out infinite alternate;
          }
          .ft-pdf-ai-notice-fireball.is-dragging .ft-pdf-ai-notice-bubble::after {
            transform: translateX(-50%) rotate(45deg) scaleY(1.22);
            transform-origin: 50% 0%;
          }
          .ft-pdf-ai-notice-fireball.is-dragging .ft-world-fireball {
            animation: ftPdfAiFireballCarried 620ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-dragging .ft-world-smile {
            transform: translateX(-50%) scaleX(0.92) translateY(1px);
          }
          .ft-pdf-ai-notice-fireball.is-dragging .ft-world-eye {
            transform: translateY(-1px) scaleY(1.08);
          }
          .ft-pdf-ai-notice-fireball.is-dragging .ft-pdf-ai-notice-leg.is-left {
            animation: ftPdfAiFireballDanglingLeft 520ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-dragging .ft-pdf-ai-notice-leg.is-right {
            animation: ftPdfAiFireballDanglingRight 520ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-flinging {
            transition: none;
            filter: drop-shadow(0 20px 28px rgba(0, 0, 0, 0.28));
          }
          .ft-pdf-ai-notice-fireball.is-flinging .ft-pdf-ai-notice-bubble {
            animation: ftPdfAiBubbleFling 1040ms cubic-bezier(0.12, 0.78, 0.18, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-flinging .ft-world-fireball {
            animation: ftPdfAiFireballFling 1180ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-flinging .ft-pdf-ai-notice-leg.is-left {
            animation: ftPdfAiFireballDanglingLeft 620ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-flinging .ft-pdf-ai-notice-leg.is-right {
            animation: ftPdfAiFireballDanglingRight 620ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-ricochet {
            transition: none;
            filter: drop-shadow(0 22px 30px rgba(0, 0, 0, 0.3));
          }
          .ft-pdf-ai-notice-fireball.is-ricochet .ft-pdf-ai-notice-bubble {
            animation: ftPdfAiBubbleRicochet 460ms cubic-bezier(0.18, 0.78, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-ricochet .ft-world-fireball {
            animation: ftPdfAiFireballRicochet 460ms cubic-bezier(0.18, 0.78, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-ricochet .ft-pdf-ai-notice-leg.is-left,
          .ft-pdf-ai-notice-fireball.is-ricochet .ft-pdf-ai-notice-leg.is-right {
            animation: ftPdfAiFireballLegFlip 420ms ease-in-out both;
          }
          .ft-pdf-ai-notice-fireball.is-falling {
            transition: none;
            filter: drop-shadow(0 26px 34px rgba(0, 0, 0, 0.34));
          }
          .ft-pdf-ai-notice-fireball.is-falling .ft-pdf-ai-notice-bubble {
            animation: ftPdfAiBubbleFall 640ms cubic-bezier(0.12, 0.72, 0.18, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-falling .ft-world-fireball {
            animation: ftPdfAiFireballFall 640ms cubic-bezier(0.12, 0.72, 0.18, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-falling .ft-pdf-ai-notice-leg.is-left,
          .ft-pdf-ai-notice-fireball.is-falling .ft-pdf-ai-notice-leg.is-right {
            animation: ftPdfAiFireballLegFall 640ms cubic-bezier(0.12, 0.72, 0.18, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-recovering {
            transition: none;
            filter: drop-shadow(0 14px 22px rgba(0, 0, 0, 0.26));
          }
          .ft-pdf-ai-notice-fireball.is-recovering .ft-world-fireball {
            animation: ftPdfAiFireballRecover 780ms cubic-bezier(0.2, 0.8, 0.25, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-recovering .ft-pdf-ai-notice-bubble {
            animation: ftPdfAiBubbleRecover 780ms cubic-bezier(0.2, 0.8, 0.25, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-recovering .ft-pdf-ai-notice-leg.is-left,
          .ft-pdf-ai-notice-fireball.is-recovering .ft-pdf-ai-notice-leg.is-right {
            animation: ftPdfAiFireballLegRecover 780ms cubic-bezier(0.2, 0.8, 0.25, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-recovering .ft-world-smile {
            transform: translateX(-50%) scaleX(0.9);
            filter: brightness(1.04);
          }
          .ft-pdf-ai-notice-fireball.is-bubble-held:not(.is-dragging):not(.is-roaming):not(.is-speaking) .ft-world-fireball {
            animation: ftPdfAiFireballBubbleHeld 5.8s ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-bubble-held:not(.is-dragging):not(.is-roaming):not(.is-speaking) .ft-pdf-ai-notice-leg.is-left {
            animation: ftPdfAiFireballTinyStepLeft 720ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-bubble-held:not(.is-dragging):not(.is-roaming):not(.is-speaking) .ft-pdf-ai-notice-leg.is-right {
            animation: ftPdfAiFireballTinyStepRight 720ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-bubble-held:not(.is-dragging):not(.is-roaming):not(.is-speaking) .ft-world-smile {
            transform: translateX(-50%) scaleX(1.12);
            filter: brightness(1.12);
          }
          .ft-pdf-ai-notice-fireball.is-bubble-pop .ft-pdf-ai-notice-bubble {
            animation: ftPdfAiBubbleBloom 520ms cubic-bezier(0.16, 0.86, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-page-turning .ft-pdf-ai-notice-bubble {
            animation: ftPdfAiBubblePageTurn 520ms cubic-bezier(0.2, 0.9, 0.2, 1) both;
          }
          .ft-pdf-ai-notice-bubble::before {
            content: "";
            position: absolute;
            inset: -7px;
            border-radius: 20px 20px 22px 14px;
            border: 1px solid rgba(126, 255, 232, 0.22);
            background:
              radial-gradient(circle at calc(100% - 74px) 52px, rgba(94, 255, 245, 0.20), transparent 0 12px, rgba(94, 255, 245, 0.10) 13px 26px, transparent 27px),
              radial-gradient(circle at calc(100% - 74px) 52px, transparent 0 31px, rgba(245, 82, 255, 0.14) 32px 33px, transparent 34px),
              linear-gradient(90deg, rgba(126, 255, 232, 0.62) 0 34px, transparent 34px calc(100% - 46px), rgba(245, 82, 255, 0.42) calc(100% - 46px) 100%) 0 0 / 100% 2px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.36) 0 42px, transparent 42px calc(100% - 34px), rgba(126, 255, 232, 0.58) calc(100% - 34px) 100%) 0 100% / 100% 2px no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.54) 0 30px, transparent 30px calc(100% - 42px), rgba(126, 255, 232, 0.26) calc(100% - 42px) 100%) 0 0 / 2px 100% no-repeat,
              linear-gradient(180deg, rgba(245, 82, 255, 0.26) 0 42px, transparent 42px calc(100% - 30px), rgba(126, 255, 232, 0.54) calc(100% - 30px) 100%) 100% 0 / 2px 100% no-repeat,
              linear-gradient(135deg, rgba(126, 255, 232, 0.74) 0 12px, transparent 12px) 8px 8px / 18px 18px no-repeat,
              linear-gradient(225deg, rgba(126, 255, 232, 0.74) 0 12px, transparent 12px) calc(100% - 26px) 8px / 18px 18px no-repeat,
              linear-gradient(45deg, rgba(245, 82, 255, 0.52) 0 12px, transparent 12px) 8px calc(100% - 26px) / 18px 18px no-repeat,
              linear-gradient(315deg, rgba(126, 255, 232, 0.74) 0 12px, transparent 12px) calc(100% - 26px) calc(100% - 26px) / 18px 18px no-repeat,
              linear-gradient(90deg, transparent, rgba(124, 255, 244, 0.14), transparent) 0 0 / 180% 100% no-repeat;
            pointer-events: none;
            box-shadow:
              0 0 0 1px rgba(255, 255, 255, 0.04),
              0 0 18px rgba(94, 249, 255, 0.20);
          }
          .ft-pdf-ai-notice-bubble::after {
            content: "";
            position: absolute;
            left: clamp(28px, var(--pdf-ai-bubble-tail-left, 36px), calc(100% - 32px));
            bottom: -12px;
            width: 30px;
            height: 24px;
            border-right: 1px solid rgba(126, 255, 232, 0.48);
            border-bottom: 1px solid rgba(126, 255, 232, 0.48);
            background:
              radial-gradient(circle at 38% 38%, rgba(94, 255, 245, 0.32), transparent 58%),
              linear-gradient(135deg, rgba(14, 35, 58, 0.96), rgba(32, 125, 145, 0.72));
            box-shadow:
              6px 8px 14px rgba(0, 0, 0, 0.18),
              0 0 14px rgba(94, 249, 255, 0.24);
            transform: translateX(-50%) rotate(35deg) skew(-12deg, -6deg);
            transform-origin: 50% 50%;
            border-bottom-right-radius: 12px;
            border-top-left-radius: 4px;
          }
          .ft-pdf-ai-notice-bubble-frame {
            position: absolute;
            inset: -8px;
            z-index: 0;
            display: block;
            border-radius: 26px 26px 28px 18px;
            pointer-events: none;
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 1) 0 34px, transparent 34px) 0 0 / 92px 3px no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.88) 0 34px, transparent 34px) 0 0 / 3px 92px no-repeat,
              linear-gradient(270deg, rgba(245, 82, 255, 0.90) 0 34px, transparent 34px) 100% 0 / 92px 3px no-repeat,
              linear-gradient(180deg, rgba(245, 82, 255, 0.72) 0 34px, transparent 34px) 100% 0 / 3px 92px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.78) 0 34px, transparent 34px) 0 100% / 92px 3px no-repeat,
              linear-gradient(0deg, rgba(245, 82, 255, 0.62) 0 34px, transparent 34px) 0 100% / 3px 92px no-repeat,
              linear-gradient(270deg, rgba(126, 255, 232, 0.94) 0 34px, transparent 34px) 100% 100% / 92px 3px no-repeat,
              linear-gradient(0deg, rgba(126, 255, 232, 0.76) 0 34px, transparent 34px) 100% 100% / 3px 92px no-repeat,
              linear-gradient(135deg, rgba(94, 255, 245, 0.92) 0 16px, transparent 16px) 0 0 / 68px 68px no-repeat,
              linear-gradient(315deg, rgba(94, 255, 245, 0.62) 0 16px, transparent 16px) 100% 100% / 68px 68px no-repeat,
              linear-gradient(225deg, rgba(245, 82, 255, 0.70) 0 12px, transparent 12px) 100% 0 / 56px 56px no-repeat,
              linear-gradient(45deg, rgba(245, 82, 255, 0.44) 0 12px, transparent 12px) 0 100% / 56px 56px no-repeat,
              radial-gradient(circle at calc(100% - 58px) 58%, transparent 0 8px, rgba(94, 255, 245, 0.72) 9px 10px, transparent 11px),
              radial-gradient(circle at calc(100% - 58px) 58%, transparent 0 18px, rgba(94, 255, 245, 0.34) 19px 20px, transparent 21px),
              radial-gradient(circle at calc(100% - 58px) 58%, transparent 0 29px, rgba(245, 82, 255, 0.26) 30px 31px, transparent 32px),
              conic-gradient(from 18deg at calc(100% - 58px) 58%, transparent 0 16%, rgba(94, 255, 245, 0.36) 16% 18%, transparent 18% 52%, rgba(245, 82, 255, 0.30) 52% 54%, transparent 54% 100%),
              linear-gradient(30deg, transparent 47%, rgba(94, 255, 245, 0.38) 48% 52%, transparent 53%) calc(100% - 94px) calc(50% + 7px) / 62px 38px no-repeat,
              linear-gradient(90deg, rgba(94, 255, 245, 0.54), transparent 32%) 24px 6px / 34% 2px no-repeat,
              linear-gradient(90deg, transparent 68%, rgba(94, 255, 245, 0.52)) 0 calc(100% - 6px) / 100% 2px no-repeat;
            clip-path: polygon(0 18px, 18px 0, calc(100% - 22px) 0, 100% 22px, 100% calc(100% - 18px), calc(100% - 18px) 100%, 22px 100%, 0 calc(100% - 22px));
            box-shadow:
              0 0 0 1px rgba(104, 255, 238, 0.18),
              0 0 18px rgba(104, 255, 238, 0.18),
              0 0 34px rgba(245, 82, 255, 0.10);
            opacity: 0.92;
            animation: ftPdfAiNoticeFramePulse 3.8s ease-in-out infinite;
          }
          .ft-pdf-ai-notice-bubble-frame::before,
          .ft-pdf-ai-notice-bubble-frame::after {
            content: "";
            position: absolute;
            pointer-events: none;
          }
          .ft-pdf-ai-notice-bubble-frame::before {
            top: 48px;
            right: 26px;
            width: 92px;
            height: 46px;
            border: 1px solid rgba(94, 255, 245, 0.22);
            border-radius: 50%;
            background:
              radial-gradient(circle at 50% 50%, transparent 0 13px, rgba(94, 255, 245, 0.68) 14px 15px, transparent 16px),
              radial-gradient(circle at 50% 50%, transparent 0 20px, rgba(245, 82, 255, 0.20) 21px 22px, transparent 23px),
              linear-gradient(90deg, rgba(245, 82, 255, 0.18), transparent 70%);
            box-shadow:
              inset 0 0 14px rgba(94, 255, 245, 0.08),
              0 0 18px rgba(94, 249, 255, 0.14);
            opacity: 0.78;
          }
          .ft-pdf-ai-notice-bubble-frame::after {
            right: 34px;
            left: auto;
            bottom: 28px;
            width: 76px;
            height: 38px;
            background:
              linear-gradient(to top, rgba(245, 82, 255, 0.60) 0 42%, transparent 42%) 0 12px / 5px 22px no-repeat,
              linear-gradient(to top, rgba(94, 255, 245, 0.60) 0 74%, transparent 74%) 11px 6px / 5px 28px no-repeat,
              linear-gradient(to top, rgba(245, 82, 255, 0.46) 0 58%, transparent 58%) 22px 10px / 5px 24px no-repeat,
              linear-gradient(to top, rgba(94, 255, 245, 0.48) 0 88%, transparent 88%) 33px 2px / 5px 32px no-repeat,
              linear-gradient(to top, rgba(245, 82, 255, 0.38) 0 50%, transparent 50%) 44px 12px / 5px 22px no-repeat,
              radial-gradient(circle at 50% 50%, rgba(94, 255, 245, 0.12), transparent 64%);
            opacity: 0.78;
          }
          .ft-pdf-ai-notice-bubble > span {
            position: relative;
            z-index: 2;
            display: block;
            white-space: pre-wrap;
            tab-size: 2;
            padding: 18px 24px 34px 22px;
            border: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
          }
          .ft-pdf-ai-notice-highlight {
            display: inline;
            color: var(--ai-notice-hl, #ffe78a);
            text-shadow:
              0 0 10px color-mix(in srgb, var(--ai-notice-hl, #ffe78a) 42%, transparent),
              0 1px 0 rgba(0, 0, 0, 0.52);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble {
            max-width: min(620px, calc(100vw - 34px));
            min-height: clamp(320px, 48vh, 620px);
            padding: 46px clamp(168px, 34%, 230px) 48px 38px;
            scroll-padding: 34px 38px 42px 34px;
            max-height: var(--pdf-ai-bubble-max-height, min(90vh, calc(100vh - 18px)));
            overflow: visible !important;
            border-radius: 24px 24px 26px 18px;
            clip-path: none;
            background:
              linear-gradient(180deg, rgba(184, 255, 248, 0.18), transparent 32px) 0 0 / 100% 100% no-repeat,
              linear-gradient(0deg, rgba(245, 82, 255, 0.13), transparent 36px) 0 100% / 100% 100% no-repeat,
              radial-gradient(circle at calc(100% - 84px) 58px, rgba(94, 255, 245, 0.24), transparent 0 18px, rgba(94, 255, 245, 0.13) 19px 34px, transparent 35px),
              radial-gradient(circle at calc(100% - 84px) 58px, transparent 0 38px, rgba(245, 82, 255, 0.16) 39px 40px, transparent 41px),
              repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.040) 0 1px, transparent 1px 8px),
              linear-gradient(145deg, rgba(7, 24, 37, 0.93), rgba(3, 11, 22, 0.96) 62%, rgba(7, 24, 38, 0.94));
            box-shadow:
              0 22px 54px rgba(0, 0, 0, 0.36),
              0 0 34px rgba(93, 232, 255, 0.24),
              0 0 56px rgba(245, 82, 255, 0.11),
              inset 0 0 0 1px rgba(190, 255, 250, 0.20),
              inset 0 22px 28px rgba(126, 255, 232, 0.08),
              inset 0 -34px 38px rgba(4, 8, 18, 0.76);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-hologram-card,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble-frame,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble::before {
            animation-name: ftPdfAiNoticeImagePopupIn;
            animation-duration: 420ms;
            animation-timing-function: cubic-bezier(0.16, 0.86, 0.22, 1);
            animation-fill-mode: both;
            animation-iteration-count: 1;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-hologram-card {
            animation:
              ftPdfAiNoticeImagePopupIn 420ms cubic-bezier(0.16, 0.86, 0.22, 1) both,
              ftPdfAiNoticeImageCardIdle 5.2s ease-in-out 460ms infinite;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-image-character img {
            animation: ftPdfAiNoticeImageFloat 5.2s ease-in-out 460ms infinite;
          }
          .ft-pdf-ai-notice-holo-connector {
            display: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector {
            position: absolute;
            z-index: 13;
            left: clamp(154px, 17vw, 218px);
            bottom: clamp(54px, 7vw, 82px);
            display: block;
            width: clamp(170px, 22vw, 260px);
            height: clamp(92px, 12vw, 132px);
            pointer-events: none;
            opacity: 0.74;
            filter:
              drop-shadow(0 0 18px rgba(94, 255, 245, 0.22))
              drop-shadow(0 0 24px rgba(245, 82, 255, 0.10));
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector::before {
            content: "";
            position: absolute;
            inset: 40% 8% auto 6%;
            height: 2px;
            background:
              linear-gradient(90deg, transparent, rgba(126, 255, 232, 0.80) 12%, rgba(245, 82, 255, 0.62) 50%, rgba(126, 255, 232, 0.72) 88%, transparent),
              repeating-linear-gradient(90deg, transparent 0 14px, rgba(255, 255, 255, 0.34) 14px 16px, transparent 16px 28px);
            box-shadow: 0 0 18px rgba(126, 255, 232, 0.34);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector::after {
            content: "";
            position: absolute;
            left: 16%;
            right: 14%;
            top: 28%;
            height: 48%;
            clip-path: polygon(0 44%, 14% 25%, 34% 25%, 48% 46%, 67% 46%, 82% 26%, 100% 26%, 100% 68%, 82% 68%, 67% 56%, 47% 56%, 34% 78%, 14% 78%, 0 58%);
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 0.08), rgba(126, 255, 232, 0.20), rgba(245, 82, 255, 0.12), rgba(126, 255, 232, 0.10));
            box-shadow: inset 0 0 0 1px rgba(126, 255, 232, 0.22);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector i {
            position: absolute;
            display: block;
            pointer-events: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-a,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-b {
            border-radius: 50%;
            background:
              radial-gradient(circle, transparent 0 24%, rgba(4, 16, 27, 0.96) 25% 31%, transparent 32%),
              radial-gradient(circle at 50% 50%, rgba(126, 255, 232, 0.14), transparent 61%),
              repeating-conic-gradient(from 0deg, rgba(126, 255, 232, 0.88) 0 7deg, rgba(7, 24, 38, 0.02) 7deg 16deg),
              repeating-conic-gradient(from 4deg, rgba(245, 82, 255, 0.32) 0 2deg, transparent 2deg 16deg),
              radial-gradient(circle, transparent 0 64%, rgba(245, 82, 255, 0.34) 65% 68%, transparent 69%),
              radial-gradient(circle, rgba(126, 255, 232, 0.20), transparent 72%);
            box-shadow:
              inset 0 0 0 1px rgba(126, 255, 232, 0.30),
              inset 0 0 0 8px rgba(3, 12, 22, 0.68),
              0 0 18px rgba(126, 255, 232, 0.24);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-a::before,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-b::before,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-a::after,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-b::after {
            content: "";
            position: absolute;
            inset: 50% auto auto 50%;
            transform-origin: 0 0;
            pointer-events: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-a::before,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-b::before {
            width: 52%;
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(126, 255, 232, 0.82), transparent);
            transform: translate(-50%, -50%) rotate(0deg);
            box-shadow: 0 0 8px rgba(126, 255, 232, 0.34);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-a::after,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-b::after {
            width: 2px;
            height: 52%;
            background: linear-gradient(180deg, transparent, rgba(245, 82, 255, 0.74), transparent);
            transform: translate(-50%, -50%) rotate(0deg);
            box-shadow: 0 0 8px rgba(245, 82, 255, 0.26);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-a {
            left: 0;
            top: 12%;
            width: 58px;
            height: 58px;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-gear-b {
            right: 8%;
            bottom: 6%;
            width: 42px;
            height: 42px;
            opacity: 0.82;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-link-line {
            left: 20%;
            right: 18%;
            top: 54%;
            height: 18px;
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 0.72) 0 18px, transparent 18px 24px, rgba(245, 82, 255, 0.58) 24px 48px, transparent 48px 56px, rgba(126, 255, 232, 0.52) 56px 100%),
              linear-gradient(180deg, transparent 0 8px, rgba(126, 255, 232, 0.62) 8px 10px, transparent 10px);
            opacity: 0.76;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-holo-connector .is-data-dots {
            left: 32%;
            right: 30%;
            top: 18%;
            height: 34px;
            background:
              radial-gradient(circle at 0 50%, rgba(126, 255, 232, 0.92) 0 2px, transparent 3px),
              radial-gradient(circle at 33% 50%, rgba(245, 82, 255, 0.82) 0 2px, transparent 3px),
              radial-gradient(circle at 66% 50%, rgba(126, 255, 232, 0.78) 0 2px, transparent 3px),
              radial-gradient(circle at 100% 50%, rgba(245, 82, 255, 0.72) 0 2px, transparent 3px);
            opacity: 0.80;
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector {
            animation: ftPdfAiNoticeConnectorBoot 720ms cubic-bezier(0.16, 0.86, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-gear-a {
            animation: ftPdfAiNoticeGearClockwise 720ms cubic-bezier(0.16, 0.86, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-gear-b {
            animation: ftPdfAiNoticeGearCounter 720ms cubic-bezier(0.16, 0.86, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-gear-a::before,
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-gear-b::before {
            animation: ftPdfAiNoticeGearClockwise 720ms cubic-bezier(0.16, 0.86, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-gear-a::after,
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-gear-b::after {
            animation: ftPdfAiNoticeGearCounter 720ms cubic-bezier(0.16, 0.86, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-link-line,
          .ft-pdf-ai-notice-fireball.is-image-character.is-entering .ft-pdf-ai-notice-holo-connector .is-data-dots {
            animation: ftPdfAiNoticeConnectorSignal 720ms ease-out both;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble::before {
            inset: 13px;
            border-radius: 22px 22px 24px 16px;
            border: 1px solid rgba(148, 255, 247, 0.22);
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 0.98) 0 28px, transparent 28px 42px, rgba(126, 255, 232, 0.38) 42px 48px, transparent 48px) 0 0 / 118px 3px no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.86) 0 28px, transparent 28px 42px, rgba(126, 255, 232, 0.32) 42px 48px, transparent 48px) 0 0 / 3px 118px no-repeat,
              linear-gradient(270deg, rgba(245, 82, 255, 0.92) 0 28px, transparent 28px 42px, rgba(245, 82, 255, 0.34) 42px 48px, transparent 48px) 100% 0 / 118px 3px no-repeat,
              linear-gradient(180deg, rgba(245, 82, 255, 0.76) 0 28px, transparent 28px 42px, rgba(245, 82, 255, 0.30) 42px 48px, transparent 48px) 100% 0 / 3px 118px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.78) 0 28px, transparent 28px 42px, rgba(245, 82, 255, 0.32) 42px 48px, transparent 48px) 0 100% / 118px 3px no-repeat,
              linear-gradient(0deg, rgba(245, 82, 255, 0.62) 0 28px, transparent 28px 42px, rgba(245, 82, 255, 0.26) 42px 48px, transparent 48px) 0 100% / 3px 118px no-repeat,
              linear-gradient(270deg, rgba(126, 255, 232, 0.94) 0 28px, transparent 28px 42px, rgba(126, 255, 232, 0.34) 42px 48px, transparent 48px) 100% 100% / 118px 3px no-repeat,
              linear-gradient(0deg, rgba(126, 255, 232, 0.78) 0 28px, transparent 28px 42px, rgba(126, 255, 232, 0.28) 42px 48px, transparent 48px) 100% 100% / 3px 118px no-repeat,
              radial-gradient(circle at 16px 16px, rgba(126, 255, 232, 0.55), transparent 0 3px, rgba(126, 255, 232, 0.22) 4px 9px, transparent 10px),
              radial-gradient(circle at calc(100% - 16px) 16px, rgba(245, 82, 255, 0.46), transparent 0 3px, rgba(245, 82, 255, 0.20) 4px 9px, transparent 10px),
              radial-gradient(circle at 16px calc(100% - 16px), rgba(245, 82, 255, 0.42), transparent 0 3px, rgba(245, 82, 255, 0.18) 4px 9px, transparent 10px),
              radial-gradient(circle at calc(100% - 16px) calc(100% - 16px), rgba(126, 255, 232, 0.46), transparent 0 3px, rgba(126, 255, 232, 0.20) 4px 9px, transparent 10px),
              linear-gradient(90deg, transparent, rgba(124, 255, 244, 0.10), transparent) 0 0 / 180% 100% no-repeat;
            box-shadow:
              inset 0 0 0 1px rgba(255, 255, 255, 0.045),
              inset 0 0 26px rgba(94, 255, 245, 0.055),
              0 0 20px rgba(94, 249, 255, 0.18);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble::after {
            left: -13px;
            width: 30px;
            height: 22px;
            transform: translateX(-50%) rotate(28deg) skew(-18deg, -8deg);
            border-right: 0;
            border-left: 1px solid rgba(135, 255, 245, 0.64);
            border-bottom-left-radius: 14px;
            border-top-right-radius: 4px;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble-frame {
            inset: 8px;
            border-radius: 24px 24px 26px 18px;
            opacity: 0.96;
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 1) 0 30px, transparent 30px) 0 0 / 76px 2px no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.92) 0 30px, transparent 30px) 0 0 / 2px 76px no-repeat,
              linear-gradient(270deg, rgba(245, 82, 255, 0.90) 0 30px, transparent 30px) 100% 0 / 76px 2px no-repeat,
              linear-gradient(180deg, rgba(245, 82, 255, 0.78) 0 30px, transparent 30px) 100% 0 / 2px 76px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.72) 0 30px, transparent 30px) 0 100% / 76px 2px no-repeat,
              linear-gradient(0deg, rgba(245, 82, 255, 0.62) 0 30px, transparent 30px) 0 100% / 2px 76px no-repeat,
              linear-gradient(270deg, rgba(126, 255, 232, 0.90) 0 30px, transparent 30px) 100% 100% / 76px 2px no-repeat,
              linear-gradient(0deg, rgba(126, 255, 232, 0.74) 0 30px, transparent 30px) 100% 100% / 2px 76px no-repeat,
              radial-gradient(circle at calc(100% - 62px) 58px, transparent 0 8px, rgba(94, 255, 245, 0.66) 9px 10px, transparent 11px),
              radial-gradient(circle at calc(100% - 62px) 58px, transparent 0 18px, rgba(245, 82, 255, 0.24) 19px 20px, transparent 21px);
            box-shadow:
              inset 0 0 0 1px rgba(160, 255, 248, 0.12),
              inset 0 0 24px rgba(94, 255, 245, 0.045),
              0 0 18px rgba(104, 255, 238, 0.18);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble > span {
            display: block;
            margin: 0;
            min-height: clamp(210px, 34vh, 420px);
            max-height: calc(var(--pdf-ai-bubble-max-height, min(90vh, calc(100vh - 18px))) - 104px);
            overflow-y: auto;
            overflow-x: hidden;
            scrollbar-width: none;
            -ms-overflow-style: none;
            padding: 30px 28px 36px 26px;
            border-radius: 18px;
            background:
              linear-gradient(180deg, rgba(3, 18, 31, 0.28), rgba(3, 12, 24, 0.12)),
              linear-gradient(90deg, rgba(94, 255, 245, 0.045), transparent 18%, transparent 82%, rgba(245, 82, 255, 0.045));
            box-shadow: inset 0 0 0 1px rgba(146, 255, 247, 0.08);
            -webkit-mask-image: none;
            mask-image: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-bubble > span::-webkit-scrollbar {
            width: 0;
            height: 0;
          }
          .ft-pdf-ai-notice-focus-hud {
            display: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud {
            position: absolute;
            z-index: 3;
            top: clamp(74px, 17%, 116px);
            right: 24px;
            display: grid;
            align-content: start;
            width: clamp(144px, 30%, 214px);
            min-height: clamp(138px, 28%, 260px);
            padding: 15px 13px 46px;
            gap: 9px;
            border-radius: 0;
            clip-path: polygon(10px 0, calc(100% - 10px) 0, 100% 10px, 100% calc(100% - 10px), calc(100% - 10px) 100%, 10px 100%, 0 calc(100% - 10px), 0 10px);
            color: rgba(226, 255, 252, 0.94);
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 0.34) 0 2px, transparent 2px) 0 0 / 100% 100% no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.20), transparent 34px),
              linear-gradient(315deg, rgba(245, 82, 255, 0.16), transparent 38%),
              repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.050) 0 1px, transparent 1px 8px),
              rgba(2, 14, 27, 0.50);
            box-shadow:
              inset 0 0 0 1px rgba(146, 255, 247, 0.24),
              inset 0 0 0 2px rgba(245, 82, 255, 0.055),
              inset 0 0 24px rgba(94, 255, 245, 0.065),
              0 0 22px rgba(94, 255, 245, 0.18);
            pointer-events: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud[hidden],
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud.is-empty {
            display: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud::before,
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud::after {
            content: "";
            position: absolute;
            inset: 5px;
            border-radius: 0;
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 1) 0 24px, transparent 24px) 0 0 / 54px 2px no-repeat,
              linear-gradient(180deg, rgba(126, 255, 232, 0.92) 0 24px, transparent 24px) 0 0 / 2px 54px no-repeat,
              linear-gradient(270deg, rgba(245, 82, 255, 0.90) 0 24px, transparent 24px) 100% 0 / 54px 2px no-repeat,
              linear-gradient(180deg, rgba(245, 82, 255, 0.74) 0 24px, transparent 24px) 100% 0 / 2px 54px no-repeat,
              linear-gradient(90deg, rgba(245, 82, 255, 0.76) 0 24px, transparent 24px) 0 100% / 54px 2px no-repeat,
              linear-gradient(0deg, rgba(245, 82, 255, 0.62) 0 24px, transparent 24px) 0 100% / 2px 54px no-repeat,
              linear-gradient(270deg, rgba(126, 255, 232, 0.94) 0 24px, transparent 24px) 100% 100% / 54px 2px no-repeat,
              linear-gradient(0deg, rgba(126, 255, 232, 0.78) 0 24px, transparent 24px) 100% 100% / 2px 54px no-repeat,
              linear-gradient(90deg, transparent 0 44%, rgba(126, 255, 232, 0.18) 44% 56%, transparent 56%) 0 29px / 100% 1px no-repeat;
            pointer-events: none;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud::after {
            inset: auto 12px 10px 12px;
            height: 28px;
            border-radius: 0;
            background:
              linear-gradient(90deg, rgba(126, 255, 232, 0.18) 0 1px, transparent 1px 8px) 0 0 / 100% 100% no-repeat,
              linear-gradient(180deg, transparent 0 6px, rgba(126, 255, 232, 0.70) 6px 8px, transparent 8px) 0 0 / 100% 100% no-repeat,
              linear-gradient(90deg, rgba(126, 255, 232, 0.72) 0 12px, transparent 12px 16px, rgba(245, 82, 255, 0.62) 16px 36px, transparent 36px 40px, rgba(126, 255, 232, 0.46) 40px 58px, transparent 58px) 0 13px / 100% 2px no-repeat,
              linear-gradient(90deg, transparent 0 8px, rgba(126, 255, 232, 0.46) 8px 10px, transparent 10px 22px, rgba(245, 82, 255, 0.42) 22px 24px, transparent 24px 40px, rgba(126, 255, 232, 0.34) 40px 42px, transparent 42px) 0 21px / 100% 2px no-repeat;
            opacity: 0.82;
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud b {
            position: relative;
            z-index: 1;
            width: max-content;
            padding: 2px 7px 3px;
            border: 1px solid rgba(126, 255, 232, 0.28);
            border-radius: 0;
            clip-path: polygon(5px 0, 100% 0, 100% calc(100% - 5px), calc(100% - 5px) 100%, 0 100%, 0 5px);
            background: rgba(4, 20, 35, 0.58);
            font-size: 9px;
            font-weight: 800;
            letter-spacing: 0;
            color: rgba(126, 255, 232, 0.96);
            text-shadow: 0 0 12px rgba(126, 255, 232, 0.46);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud small {
            position: relative;
            z-index: 1;
            max-height: none;
            overflow: visible;
            font-size: 10px;
            line-height: 1.38;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            color: rgba(241, 255, 253, 0.88);
            padding-left: 6px;
            border-left: 1px solid rgba(126, 255, 232, 0.30);
          }
          .ft-pdf-ai-notice-fireball.is-image-character .ft-pdf-ai-notice-focus-hud i {
            position: relative;
            z-index: 1;
            width: 52px;
            height: 18px;
            align-self: end;
            background:
              linear-gradient(180deg, transparent 0 12px, rgba(126, 255, 232, 0.76) 12px 14px, transparent 14px),
              linear-gradient(90deg, transparent 0 6px, rgba(245, 82, 255, 0.62) 6px 12px, transparent 12px 17px, rgba(126, 255, 232, 0.68) 17px 26px, transparent 26px 31px, rgba(245, 82, 255, 0.48) 31px 40px, transparent 40px);
            filter: drop-shadow(0 0 7px rgba(126, 255, 232, 0.42));
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-hologram-card {
            border-color: rgba(255, 82, 98, 0.76);
            background:
              linear-gradient(90deg, rgba(255, 82, 98, 0.92), transparent 34%) 14px 13px / calc(100% - 72px) 2px no-repeat,
              linear-gradient(90deg, rgba(255, 176, 92, 0.74), transparent 44%) 14px 20px / 48% 2px no-repeat,
              radial-gradient(circle at 82% 8%, rgba(255, 82, 98, 0.24), transparent 28%),
              radial-gradient(circle at 10% 4%, rgba(126, 255, 232, 0.14), transparent 34%),
              linear-gradient(145deg, rgba(38, 6, 14, 0.88), rgba(12, 4, 10, 0.94));
            box-shadow:
              0 22px 48px rgba(0, 0, 0, 0.36),
              0 0 32px rgba(255, 66, 92, 0.28),
              inset 0 0 0 1px rgba(255, 190, 170, 0.20);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-image-character::before {
            background:
              radial-gradient(circle, transparent 0 44%, rgba(255, 82, 98, 0.42) 45% 46%, transparent 47%),
              repeating-conic-gradient(from 0deg, rgba(255, 82, 98, 0.54) 0 8deg, transparent 8deg 18deg);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-image-character img {
            filter:
              drop-shadow(0 16px 22px rgba(0, 0, 0, 0.32))
              drop-shadow(0 0 22px rgba(255, 74, 98, 0.30));
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-bubble {
            background:
              linear-gradient(180deg, rgba(255, 118, 120, 0.20), transparent 34px) 0 0 / 100% 100% no-repeat,
              linear-gradient(0deg, rgba(255, 176, 92, 0.13), transparent 38px) 0 100% / 100% 100% no-repeat,
              radial-gradient(circle at calc(100% - 84px) 58px, rgba(255, 82, 98, 0.25), transparent 0 18px, rgba(255, 82, 98, 0.13) 19px 34px, transparent 35px),
              radial-gradient(circle at calc(100% - 84px) 58px, transparent 0 38px, rgba(255, 176, 92, 0.18) 39px 40px, transparent 41px),
              repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.040) 0 1px, transparent 1px 8px),
              linear-gradient(145deg, rgba(36, 6, 14, 0.94), rgba(12, 4, 10, 0.97) 62%, rgba(38, 8, 16, 0.95));
            box-shadow:
              0 22px 54px rgba(0, 0, 0, 0.38),
              0 0 34px rgba(255, 66, 92, 0.30),
              0 0 56px rgba(255, 176, 92, 0.12),
              inset 0 0 0 1px rgba(255, 196, 176, 0.23),
              inset 0 22px 28px rgba(255, 82, 98, 0.08),
              inset 0 -34px 38px rgba(12, 3, 8, 0.78);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-bubble::before,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-bubble-frame,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-holo-connector::before,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-holo-connector::after,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-holo-connector .is-link-line,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-holo-connector .is-data-dots,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-holo-connector .is-gear-a,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-holo-connector .is-gear-b,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-focus-hud::before,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-focus-hud::after,
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-focus-hud i {
            filter: hue-rotate(128deg) saturate(1.45);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-bubble::after {
            border-left-color: rgba(255, 118, 120, 0.70);
            background: rgba(36, 6, 14, 0.88);
            box-shadow: 0 0 14px rgba(255, 82, 98, 0.30);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-bubble > span {
            background:
              linear-gradient(180deg, rgba(34, 6, 14, 0.34), rgba(12, 4, 10, 0.14)),
              linear-gradient(90deg, rgba(255, 82, 98, 0.060), transparent 20%, transparent 80%, rgba(255, 176, 92, 0.052));
            box-shadow: inset 0 0 0 1px rgba(255, 148, 132, 0.10);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-focus-hud {
            background:
              linear-gradient(90deg, rgba(255, 82, 98, 0.34) 0 2px, transparent 2px) 0 0 / 100% 100% no-repeat,
              linear-gradient(180deg, rgba(255, 82, 98, 0.22), transparent 34px),
              linear-gradient(315deg, rgba(255, 176, 92, 0.16), transparent 38%),
              repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.050) 0 1px, transparent 1px 8px),
              rgba(28, 5, 13, 0.55);
            box-shadow:
              inset 0 0 0 1px rgba(255, 148, 132, 0.26),
              inset 0 0 0 2px rgba(255, 176, 92, 0.055),
              inset 0 0 24px rgba(255, 82, 98, 0.075),
              0 0 22px rgba(255, 82, 98, 0.20);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-focus-hud b {
            border-color: rgba(255, 128, 120, 0.32);
            background: rgba(34, 6, 14, 0.64);
            color: rgba(255, 156, 140, 0.98);
            text-shadow: 0 0 12px rgba(255, 82, 98, 0.46);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-theme-red .ft-pdf-ai-notice-focus-hud small {
            border-left-color: rgba(255, 128, 120, 0.34);
          }
          .ft-pdf-ai-notice-fireball.is-image-character.is-image-closing .ft-pdf-ai-notice-hologram-card,
          .ft-pdf-ai-notice-fireball.is-image-character.is-image-closing .ft-pdf-ai-notice-bubble {
            animation: ftPdfAiNoticeImagePopupOut 340ms cubic-bezier(0.42, 0, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-counter {
            position: relative;
            z-index: 1;
            display: none;
            width: max-content;
            margin: 9px 0 0 auto;
            padding: 2px 8px;
            border: 1px solid rgba(126, 255, 232, 0.22);
            border-radius: 999px;
            background: rgba(7, 18, 30, 0.44);
            color: #9fffee;
            font-size: 11px;
            font-weight: 800;
            line-height: 1.35;
            letter-spacing: 0;
            box-shadow: 0 0 12px rgba(126, 255, 232, 0.14);
          }
          @keyframes ftPdfAiNoticeImagePopupIn {
            0% {
              opacity: 0;
              transform: translate3d(-10px, 8px, 0) scale(0.965);
              filter: blur(8px) saturate(1.4);
            }
            58% {
              opacity: 1;
              transform: translate3d(2px, -2px, 0) scale(1.012);
              filter: blur(0) saturate(1.18);
            }
            100% {
              opacity: 1;
              transform: translate3d(0, 0, 0) scale(1);
              filter: none;
            }
          }
          @keyframes ftPdfAiNoticeImagePopupOut {
            0% {
              opacity: 1;
              transform: translate3d(0, 0, 0) scale(1);
              filter: blur(0) saturate(1.12);
            }
            100% {
              opacity: 0;
              transform: translate3d(-8px, 10px, 0) scale(0.965);
              filter: blur(8px) saturate(1.5);
            }
          }
          @keyframes ftPdfAiNoticeImageCardIdle {
            0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
            50% { transform: translate3d(0, -4px, 0) scale(1.006); }
          }
          .ft-pdf-ai-notice-fireball.has-pages .ft-pdf-ai-notice-counter {
            display: block;
          }
          .ft-pdf-ai-notice-last-char {
            color: #ffe78a;
            font-weight: 900;
            text-shadow:
              0 0 9px rgba(255, 231, 138, 0.78),
              0 0 18px rgba(126, 255, 232, 0.28);
            animation: ftPdfAiFireballLastChar 520ms ease-in-out infinite alternate;
          }
          .ft-pdf-ai-notice-fireball.is-speaking .ft-pdf-ai-notice-bubble::after {
            content: "";
          }
          .ft-pdf-ai-notice-fireball.is-speaking .ft-pdf-ai-notice-bubble span::after {
            content: "";
            display: inline-block;
            width: 7px;
            height: 1em;
            margin-left: 4px;
            vertical-align: -0.15em;
            background: #ffe78a;
            box-shadow: 0 0 12px rgba(255, 231, 138, 0.55);
            animation: ftPdfAiFireballCaret 620ms steps(2, end) infinite;
          }
          .ft-pdf-ai-notice-leg {
            position: absolute;
            bottom: -7px;
            z-index: -1;
            width: 13px;
            height: 22px;
            border-radius: 10px 10px 12px 12px;
            background: linear-gradient(180deg, #ffe091, #ff7b3b 56%, #6efcea);
            box-shadow: 0 0 10px rgba(255, 125, 59, 0.42);
            transform-origin: 50% 6%;
            opacity: 0.92;
          }
          .ft-pdf-ai-notice-leg.is-left {
            left: 18px;
          }
          .ft-pdf-ai-notice-leg.is-right {
            right: 16px;
          }
          .ft-pdf-ai-notice-run-wheel {
            position: absolute;
            bottom: -10px;
            z-index: -2;
            width: 26px;
            height: 26px;
            border-radius: 50%;
            opacity: 0;
            transform: scale(0.72);
            background:
              conic-gradient(from 0deg, rgba(255, 235, 150, 0.95), rgba(255, 116, 52, 0.88), rgba(111, 252, 234, 0.92), rgba(255, 235, 150, 0.95));
            box-shadow:
              0 0 16px rgba(255, 137, 65, 0.46),
              0 0 18px rgba(111, 252, 234, 0.22);
          }
          .ft-pdf-ai-notice-run-wheel::before {
            content: "";
            position: absolute;
            inset: 6px;
            border-radius: inherit;
            background: rgba(12, 25, 33, 0.84);
          }
          .ft-pdf-ai-notice-run-wheel.is-left {
            left: 4px;
          }
          .ft-pdf-ai-notice-run-wheel.is-right {
            right: 2px;
          }
          .ft-pdf-ai-notice-fireball.is-long-run .ft-pdf-ai-notice-run-wheel {
            opacity: 0.95;
            animation: ftPdfAiFireballRunWheel 360ms linear infinite;
          }
          .ft-pdf-ai-notice-fireball.is-roaming .ft-world-smile {
            transform: translateX(-50%) scaleX(1.22);
            filter: brightness(1.18);
          }
          .ft-pdf-ai-notice-fireball.is-entering .ft-pdf-ai-notice-leg.is-left,
          .ft-pdf-ai-notice-fireball.is-roaming .ft-pdf-ai-notice-leg.is-left {
            animation: ftPdfAiFireballLegLeft 520ms ease-in-out infinite;
          }
          .ft-pdf-ai-notice-fireball.is-entering .ft-pdf-ai-notice-leg.is-right,
          .ft-pdf-ai-notice-fireball.is-roaming .ft-pdf-ai-notice-leg.is-right {
            animation: ftPdfAiFireballLegRight 520ms ease-in-out infinite;
          }
          @keyframes ftPdfAiBubbleBloom {
            0% { opacity: 0.35; transform: translateY(16px) scale(0.88); filter: blur(1px); }
            68% { opacity: 1; transform: translateY(-7px) scale(1.035); filter: blur(0); }
            100% { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
          }
          @keyframes ftPdfAiBubblePageTurn {
            0% { opacity: 0.58; transform: translateY(12px) rotateX(-9deg) scale(0.96); }
            58% { opacity: 1; transform: translateY(-7px) rotateX(2deg) scale(1.025); }
            100% { opacity: 1; transform: translateY(0) rotateX(0deg) scale(1); }
          }
          @keyframes ftPdfAiBubbleCarry {
            0% { transform: translateY(-3px) rotate(-1.4deg) scale(1.01); }
            100% { transform: translateY(1px) rotate(1.4deg) scale(0.995); }
          }
          @keyframes ftPdfAiBubbleFling {
            0% { transform: translateY(-1px) rotate(-0.8deg) scale(1.003); }
            58% { transform: translateY(1px) rotate(0.55deg) scale(0.999); }
            100% { transform: translateY(0) rotate(0deg) scale(1); }
          }
          @keyframes ftPdfAiBubbleRicochet {
            0% { transform: translateY(0) rotate(0deg) scale(1); }
            52% { transform: translateY(4px) rotate(-7deg) scale(0.96); }
            100% { transform: translateY(-2px) rotate(5deg) scale(1.01); }
          }
          @keyframes ftPdfAiBubbleFall {
            0% { transform: translateY(0) rotate(0deg) scale(1); opacity: 1; }
            72% { transform: translateY(8px) rotate(-8deg) scale(0.96); opacity: 1; }
            100% { transform: translateY(12px) rotate(-14deg) scale(0.91); opacity: 0.96; }
          }
          @keyframes ftPdfAiFireballIdle {
            0%, 100% { transform: translateY(0) rotate(0deg) scaleX(var(--world-facing, 1)); }
            50% { transform: translateY(-5px) rotate(1.6deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballFling {
            0%, 100% { transform: translate(0, 6px) rotate(-2.5deg) scaleX(var(--world-facing, 1)); }
            48% { transform: translate(6px, 10px) rotate(2.5deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballRicochet {
            0% { transform: translate(0, 4px) rotate(-3deg) scaleX(var(--world-facing, 1)); }
            56% { transform: translate(5px, 12px) rotate(28deg) scaleX(var(--world-facing, 1)); }
            100% { transform: translate(-2px, 6px) rotate(12deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballFall {
            0% { transform: translate(0, 0) rotate(16deg) scaleX(var(--world-facing, 1)); }
            74% { transform: translate(2px, 10px) rotate(88deg) scaleX(var(--world-facing, 1)); }
            100% { transform: translate(0, 16px) rotate(116deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballCarried {
            0%, 100% { transform: translateY(7px) rotate(-8deg) scaleX(var(--world-facing, 1)); }
            45% { transform: translateY(12px) rotate(7deg) scaleX(var(--world-facing, 1)); }
            72% { transform: translateY(9px) rotate(2deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballDanglingLeft {
            0%, 100% { transform: rotate(18deg) translateY(2px); }
            50% { transform: rotate(-12deg) translateY(7px); }
          }
          @keyframes ftPdfAiFireballDanglingRight {
            0%, 100% { transform: rotate(-18deg) translateY(7px); }
            50% { transform: rotate(12deg) translateY(2px); }
          }
          @keyframes ftPdfAiFireballLegFlip {
            0% { transform: rotate(0deg) translateY(0); }
            50% { transform: rotate(-34deg) translateY(10px); }
            100% { transform: rotate(22deg) translateY(4px); }
          }
          @keyframes ftPdfAiFireballLegFall {
            0% { transform: rotate(18deg) translateY(2px); }
            100% { transform: rotate(88deg) translateY(14px); }
          }
          @keyframes ftPdfAiFireballRecover {
            0% { transform: translate(0, 16px) rotate(116deg) scaleX(var(--world-facing, 1)); }
            18% { transform: translate(-4px, 12px) rotate(92deg) scaleX(var(--world-facing, 1)); }
            34% { transform: translate(5px, 8px) rotate(62deg) scaleX(var(--world-facing, 1)); }
            50% { transform: translate(-5px, 4px) rotate(32deg) scaleX(var(--world-facing, 1)); }
            66% { transform: translate(4px, 0) rotate(12deg) scaleX(var(--world-facing, 1)); }
            80% { transform: translate(-3px, -7px) rotate(-6deg) scaleX(var(--world-facing, 1)); }
            92% { transform: translate(2px, -2px) rotate(3deg) scaleX(var(--world-facing, 1)); }
            100% { transform: translate(0, 0) rotate(0deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiBubbleRecover {
            0% { transform: translateY(12px) rotate(-14deg) scale(0.92); opacity: 0.96; }
            40% { transform: translateY(-3px) rotate(4deg) scale(1.02); opacity: 1; }
            70% { transform: translateY(2px) rotate(-2deg) scale(0.99); opacity: 1; }
            100% { transform: translateY(0) rotate(0deg) scale(1); opacity: 1; }
          }
          @keyframes ftPdfAiFireballLegRecover {
            0% { transform: rotate(88deg) translateY(14px); }
            50% { transform: rotate(-20deg) translateY(-2px); }
            100% { transform: rotate(0deg) translateY(0); }
          }
          @keyframes ftPdfAiFireballBubbleHeld {
            0%, 100% { transform: translate(-88px, 8px) rotate(-4deg) scaleX(var(--world-facing, 1)); }
            16% { transform: translate(-34px, 24px) rotate(3deg) scaleX(var(--world-facing, 1)); }
            34% { transform: translate(82px, 4px) rotate(5deg) scaleX(var(--world-facing, 1)); }
            52% { transform: translate(104px, 28px) rotate(-2deg) scaleX(var(--world-facing, 1)); }
            70% { transform: translate(20px, 18px) rotate(2deg) scaleX(var(--world-facing, 1)); }
            86% { transform: translate(-96px, 2px) rotate(-5deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballTinyStepLeft {
            0%, 100% { transform: rotate(-8deg) translateY(0); }
            50% { transform: rotate(13deg) translateY(4px); }
          }
          @keyframes ftPdfAiFireballTinyStepRight {
            0%, 100% { transform: rotate(10deg) translateY(4px); }
            50% { transform: rotate(-12deg) translateY(0); }
          }
          @keyframes ftPdfAiFireballRun {
            0%, 100% { transform: translate(0, 0) rotate(-5deg) scaleX(var(--world-facing, 1)); }
            35% { transform: translate(5px, -7px) rotate(5deg) scaleX(var(--world-facing, 1)); }
            68% { transform: translate(-2px, -3px) rotate(-2deg) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballTalk {
            0%, 100% { transform: translateY(0) rotate(-1deg) scaleX(var(--world-facing, 1)); filter: brightness(1); }
            50% { transform: translateY(-4px) rotate(2deg) scaleX(var(--world-facing, 1)); filter: brightness(1.14); }
          }
          @keyframes ftPdfAiFireballJump {
            0% { transform: translateY(0) scaleX(var(--world-facing, 1)); }
            48% { transform: translateY(-12px) rotate(2deg) scaleX(var(--world-facing, 1)); }
            100% { transform: translateY(0) scaleX(var(--world-facing, 1)); }
          }
          @keyframes ftPdfAiFireballCaret {
            0%, 45% { opacity: 1; }
            46%, 100% { opacity: 0; }
          }
          @keyframes ftPdfAiFireballLastChar {
            from { filter: brightness(1); transform: translateY(0); }
            to { filter: brightness(1.26); transform: translateY(-1px); }
          }
          @keyframes ftPdfAiFireballLegLeft {
            0%, 100% { transform: rotate(18deg) translateY(0); }
            50% { transform: rotate(-24deg) translateY(4px); }
          }
          @keyframes ftPdfAiFireballLegRight {
            0%, 100% { transform: rotate(-20deg) translateY(4px); }
            50% { transform: rotate(24deg) translateY(0); }
          }
          @keyframes ftPdfAiFireballRunWheel {
            from { transform: scale(0.82) rotate(0deg); }
            to { transform: scale(0.82) rotate(360deg); }
          }
          .ft-pdf-ai-notice-portal {
            position: fixed;
            left: 50%;
            top: 50%;
            width: 220px;
            height: 220px;
            margin-left: -110px;
            margin-top: -110px;
            border-radius: 50%;
            pointer-events: none;
            z-index: 2319;
            opacity: 0;
            transform: scale(0.18);
            mix-blend-mode: screen;
            background:
              radial-gradient(circle at 50% 50%, rgba(8, 10, 22, 0.96) 0%, rgba(8, 10, 22, 0.9) 22%, rgba(36, 16, 70, 0.78) 38%, rgba(8, 10, 22, 0.4) 56%, rgba(126, 255, 232, 0.18) 70%, rgba(255, 211, 126, 0.08) 84%, transparent 100%);
            box-shadow:
              0 0 60px rgba(126, 255, 232, 0.32),
              0 0 140px rgba(126, 255, 232, 0.18),
              inset 0 0 40px rgba(126, 255, 232, 0.18);
            will-change: transform, opacity;
          }
          .ft-pdf-ai-notice-portal::before {
            content: "";
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background:
              conic-gradient(from 0deg, rgba(126, 255, 232, 0) 0deg, rgba(126, 255, 232, 0.7) 30deg, rgba(255, 211, 126, 0) 60deg, rgba(255, 211, 126, 0.7) 110deg, rgba(255, 90, 198, 0) 140deg, rgba(255, 90, 198, 0.6) 180deg, rgba(126, 255, 232, 0) 220deg, rgba(126, 255, 232, 0.6) 260deg, rgba(126, 255, 232, 0) 320deg);
            mask: radial-gradient(circle at 50% 50%, transparent 38%, #000 56%, transparent 84%);
            -webkit-mask: radial-gradient(circle at 50% 50%, transparent 38%, #000 56%, transparent 84%);
            animation: ftPdfAiPortalSpin 1.8s linear infinite;
            filter: blur(0.4px);
          }
          .ft-pdf-ai-notice-portal::after {
            content: "";
            position: absolute;
            inset: 22%;
            border-radius: 50%;
            background: radial-gradient(circle at 50% 50%, rgba(0, 0, 0, 0.96) 0%, rgba(0, 0, 0, 0.8) 60%, transparent 100%);
            box-shadow: inset 0 0 30px rgba(126, 255, 232, 0.45);
          }
          .ft-pdf-ai-notice-portal.is-opening {
            opacity: 1;
            transform: scale(1);
            animation: ftPdfAiPortalOpen 480ms cubic-bezier(0.16, 0.86, 0.22, 1) both;
          }
          .ft-pdf-ai-notice-portal.is-closing {
            animation: ftPdfAiPortalClose 460ms cubic-bezier(0.5, 0, 0.75, 0) both;
          }
          .ft-pdf-ai-notice-portal.is-peak::before {
            animation-duration: 0.6s;
            filter: blur(0.6px) saturate(1.35);
          }
          .ft-pdf-ai-notice-portal.is-peak::after {
            box-shadow:
              inset 0 0 40px rgba(126, 255, 232, 0.85),
              inset 0 0 80px rgba(255, 211, 126, 0.35);
          }
          @keyframes ftPdfAiPortalOpen {
            0% { opacity: 0; transform: scale(0.18) rotate(0deg); filter: blur(8px); }
            35% { opacity: 1; transform: scale(0.7) rotate(20deg); filter: blur(2px); }
            72% { opacity: 1; transform: scale(1.18) rotate(45deg); filter: blur(0); }
            100% { opacity: 1; transform: scale(1) rotate(60deg); filter: blur(0); }
          }
          @keyframes ftPdfAiPortalClose {
            0% { opacity: 1; transform: scale(1) rotate(60deg); filter: blur(0); }
            100% { opacity: 0; transform: scale(0.16) rotate(110deg); filter: blur(6px); }
          }
          @keyframes ftPdfAiPortalSpin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes ftPdfAiNoticeRegionFloat {
            0%, 100% { filter: brightness(1); }
            50% { filter: brightness(1.16); }
          }
          @keyframes ftPdfAiNoticeFramePulse {
            0%, 100% {
              transform: translate3d(0, 0, 0) scale(1);
              opacity: 0.86;
              filter: saturate(1.04) brightness(1);
            }
            50% {
              transform: translate3d(0, -1px, 0) scale(1.01);
              opacity: 1;
              filter: saturate(1.18) brightness(1.08);
            }
          }
          @media (max-width: 900px) {
            .ft-pdf-space { padding: 62px 10px 14px; }
            .ft-pdf-shell { grid-template-columns: 1fr; grid-template-rows: minmax(52vh, 1fr) minmax(260px, 38vh); }
            .ft-pdf-topline { grid-template-columns: 1fr; }
            .ft-pdf-status { width: 100%; margin-left: 0; }
            .ft-pdf-image { max-width: none; }
            .ft-pdf-word-detail { width: calc(100vw - 28px); }
            .ft-pdf-translation-card {
              left: 14px;
              right: 14px;
              top: 76px;
              width: auto;
              max-height: 70vh;
            }
            .ft-pdf-word-detail-results.is-multiple .ft-pdf-word-detail-entry {
              flex-basis: 100%;
              max-width: 100%;
            }
            .ft-pdf-word-detail-surface {
              grid-template-columns: 1fr;
            }
            .ft-pdf-word-page-tabs {
              justify-content: flex-start;
            }
          .ft-pdf-word-detail-footer {
            align-items: stretch;
            flex-direction: column;
          }
          .ft-pdf-speak-modal {
            width: calc(100vw - 28px);
            max-height: 82vh;
          }
          .ft-pdf-speak-card {
            width: 100%;
            max-height: inherit;
          }
          .ft-pdf-speak-body {
            overflow: auto;
          }
          .ft-pdf-speak-practice-grid {
            grid-template-columns: 1fr;
          }
          .ft-pdf-speak-grid {
            grid-template-columns: 1fr;
          }
          .ft-pdf-speak-feedback-panel {
            min-height: 340px;
          }
          .ft-pdf-unlearned-row { grid-template-columns: 1fr; }
          .ft-pdf-ai-notice-grid {
            grid-template-columns: 1fr;
          }
          .ft-pdf-ai-notice-editor textarea {
            min-height: 220px;
          }
          .ft-pdf-ai-notice-fireball {
            --pdf-ai-bubble-base: min(272px, calc(100vw - 28px));
            width: min(calc(var(--pdf-ai-bubble-width) + 18px), calc(100vw - 24px));
          }
          .ft-pdf-ai-notice-fireball .ft-world-fireball {
            width: 58px;
            height: 58px;
          }
          .ft-pdf-ai-notice-bubble {
            width: var(--pdf-ai-bubble-width);
            max-height: none;
            font-size: 13px;
          }
        }
        .ft-pdf-page-history-popup {
          position: fixed;
          z-index: 200;
          min-width: 140px;
          max-width: 220px;
          background: #1a1a2e;
          border: 1px solid rgba(100, 200, 255, 0.35);
          border-radius: 8px;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
          padding: 4px 0;
          font-family: inherit;
          font-size: 13px;
          overflow: hidden;
        }
        .ft-pdf-page-history-head {
          padding: 6px 12px 4px;
          font-size: 11px;
          font-weight: 600;
          color: rgba(180, 220, 255, 0.7);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border-bottom: 1px solid rgba(100, 200, 255, 0.12);
        }
        .ft-pdf-page-history-list {
          max-height: 320px;
          overflow-y: auto;
        }
        .ft-pdf-page-history-item {
          display: flex;
          align-items: center;
          gap: 8px;
          width: 100%;
          padding: 5px 12px;
          background: none;
          border: none;
          color: #c8d8e8;
          font-size: 13px;
          text-align: left;
          cursor: pointer;
          font-family: inherit;
          transition: background 80ms;
        }
        .ft-pdf-page-history-item:hover,
        .ft-pdf-page-history-item:focus-visible {
          background: rgba(100, 200, 255, 0.12);
          color: #fff;
          outline: none;
        }
        .ft-pdf-page-history-item.is-current .ft-pdf-page-history-label {
          color: #5bf;
          font-weight: 600;
        }
        .ft-pdf-page-history-item.is-current::after {
          content: " \\25C0";
          font-size: 10px;
          margin-left: auto;
          opacity: 0.6;
        }
        .ft-pdf-page-history-item.is-pinned .ft-pdf-page-history-label {
          color: #ffe066;
        }
        .ft-pdf-page-history-item.is-current.is-pinned::after {
          display: none;
        }
        .ft-pdf-page-history-pinmark {
          margin-left: auto;
          flex-shrink: 0;
          font-size: 12px;
        }
        .ft-pdf-page-history-audiomark {
          flex-shrink: 0;
          font-size: 12px;
          margin-left: 4px;
        }
        `;
        document.head.appendChild(style);
      };

      function nudgePdfSpeakTrainingButton() {
        if (!pdfEls || !pdfEls.speakTrainingOpen || pdfEls.speakTrainingOpen.hidden) {
          return;
        }
        if (pdfSpeakTrainingNudgeTimer) {
          window.clearTimeout(pdfSpeakTrainingNudgeTimer);
          pdfSpeakTrainingNudgeTimer = 0;
        }
        const button = pdfEls.speakTrainingOpen;
        button.classList.remove("is-speak-training-hint");
        void button.offsetWidth;
        button.classList.add("is-speak-training-hint");
        pdfSpeakTrainingNudgeTimer = window.setTimeout(() => {
          button.classList.remove("is-speak-training-hint");
          pdfSpeakTrainingNudgeTimer = 0;
        }, 5000);
      }

      function setPdfOcrTab(tab = "found") {
        const previous = pdfState.ocrTab;
        const next = clean(tab) === "explore" ? "explore" : "found";
        pdfState.ocrTab = next;
        if (pdfEls && Array.isArray(pdfEls.ocrTabs)) {
          pdfEls.ocrTabs.forEach((button) => {
            const active = clean(button.getAttribute("data-pdf-tab")) === next;
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-selected", active ? "true" : "false");
          });
        }
        if (pdfEls && Array.isArray(pdfEls.ocrPanels)) {
          pdfEls.ocrPanels.forEach((panel) => {
            const active = clean(panel.getAttribute("data-pdf-panel")) === next;
            panel.classList.toggle("is-active", active);
            panel.setAttribute("aria-hidden", active ? "false" : "true");
          });
        }
        if (pdfEls && pdfEls.speakTrainingOpen) {
          pdfEls.speakTrainingOpen.hidden = next !== "explore";
          if (next === "explore" && previous !== "explore") {
            nudgePdfSpeakTrainingButton();
          } else if (next !== "explore") {
            pdfEls.speakTrainingOpen.classList.remove("is-speak-training-hint");
          }
        }
        if (previous !== next && pdfModeActive && pdfState && pdfState.path) {
          schedulePdfProgressSave(300);
        }
      }

      function openPdfTranslationPopup(text = "") {
        if (!pdfEls || !pdfEls.translationCard || !pdfEls.translation) {
          return;
        }
        pdfEls.translation.textContent = preserveQuestionText(text || "No translation returned.");
        pdfEls.translationCard.classList.remove("is-hidden");
        pdfEls.translationCard.setAttribute("aria-hidden", "false");
        window.requestAnimationFrame(() => {
          applyPdfTranslationFloatingState();
        });
        if (pdfModeActive && pdfState && pdfState.path) {
          schedulePdfProgressSave(450);
        }
      }

      function closePdfTranslationPopup() {
        if (!pdfEls || !pdfEls.translationCard) {
          return;
        }
        pdfEls.translationCard.classList.add("is-hidden");
        pdfEls.translationCard.setAttribute("aria-hidden", "true");
        if (pdfModeActive && pdfState && pdfState.path) {
          schedulePdfProgressSave(450);
        }
      }

      const pdfSpeakTrainingText = () => preserveQuestionText(
        (pdfEls && pdfEls.exploreInput ? pdfEls.exploreInput.value : "")
        || pdfState.ocrText
        || ""
      ).trim();

      const setPdfSpeakTrainingStatus = (message = "", kind = "") => {
        if (!pdfEls || !pdfEls.speakStatus) {
          return;
        }
        pdfEls.speakStatus.textContent = message || "";
        pdfEls.speakStatus.classList.toggle("is-error", kind === "error");
        pdfEls.speakStatus.classList.toggle("is-ok", kind === "ok");
      };

      const readPdfSpeakTrainingAiCheckPreference = () => {
        try {
          const value = localStorage.getItem(PDF_SPEAK_AI_CHECK_KEY);
          if (value === "0" || value === "off" || value === "browser") return false;
          if (value === "1" || value === "on" || value === "ai") return true;
        } catch (error) {
        }
        return true;
      };

      const writePdfSpeakTrainingAiCheckPreference = (enabled) => {
        try {
          localStorage.setItem(PDF_SPEAK_AI_CHECK_KEY, enabled ? "1" : "0");
        } catch (error) {
        }
      };

      const syncPdfSpeakTrainingCheckModeUi = () => {
        if (!pdfEls) {
          return;
        }
        const serverForcedBrowser = Boolean(pdfSpeakTraining.serverManaged || speakAiCheckVoiceServerAllowsWhisper === false);
        const browserMode = serverForcedBrowser || !pdfSpeakTraining.aiCheckVoice;
        if (pdfEls.speakModeToggle) {
          pdfEls.speakModeToggle.classList.toggle("is-browser", browserMode);
          pdfEls.speakModeToggle.setAttribute("aria-pressed", (!serverForcedBrowser && pdfSpeakTraining.aiCheckVoice) ? "true" : "false");
          pdfEls.speakModeToggle.title = serverForcedBrowser
            ? "Server Whisper is OFF. Ghost Eye will use browser live voice check."
            : (pdfSpeakTraining.aiCheckVoice
            ? "AI check voice ON: send recording to server speech analysis."
            : (pdfSpeakTraining.aiCheckVoiceFallbackActive ? "Whisper connection failed. This session is using browser live voice check." : "AI check voice OFF: use browser live speech recognition."));
        }
        if (pdfEls.speakModeLabel) {
          pdfEls.speakModeLabel.textContent = serverForcedBrowser
            ? "SERVER OFF - browser"
            : (pdfSpeakTraining.aiCheckVoice
            ? "ON - Whisper"
            : (pdfSpeakTraining.aiCheckVoiceFallbackActive ? "FALLBACK - browser" : "OFF - browser"));
        }
      };

      const setPdfSpeakTrainingAiCheckVoice = (enabled, persist = true) => {
        pdfSpeakTraining.aiCheckVoice = Boolean(enabled);
        if (persist) {
          writePdfSpeakTrainingAiCheckPreference(pdfSpeakTraining.aiCheckVoice);
        }
        syncPdfSpeakTrainingCheckModeUi();
        updatePdfSpeakTrainingControls();
      };

      pdfSpeakTraining.aiCheckVoice = readPdfSpeakTrainingAiCheckPreference();

      const updatePdfSpeakTrainingControls = () => {
        if (!pdfEls) {
          return;
        }
        const recording = Boolean(pdfSpeakTraining.recorder && pdfSpeakTraining.recorder.state === "recording");
        const browserRecording = Boolean(pdfSpeakTraining.recognitionActive);
        if (pdfEls.speakRecord) {
          pdfEls.speakRecord.disabled = Boolean(pdfSpeakTraining.busy);
          pdfEls.speakRecord.classList.toggle("is-recording", recording || browserRecording);
          pdfEls.speakRecord.textContent = browserRecording ? "Stop Mic" : (recording ? "Stop & Score" : "Record");
        }
        if (pdfEls.speakReplay) {
          pdfEls.speakReplay.disabled = !pdfSpeakTraining.blob || Boolean(pdfSpeakTraining.busy) || recording || browserRecording;
          pdfEls.speakReplay.textContent = pdfSpeakTraining.mode === "playing" ? "Stop" : "Replay";
        }
        if (pdfEls.speakModeToggle) {
          pdfEls.speakModeToggle.disabled = Boolean(pdfSpeakTraining.serverManaged || speakAiCheckVoiceServerAllowsWhisper === false || pdfSpeakTraining.busy || recording || browserRecording);
        }
        syncPdfSpeakTrainingCheckModeUi();
      };

      const closePdfSpeakTrainingAudioContext = () => {
        if (pdfSpeakTraining.frame) {
          window.cancelAnimationFrame(pdfSpeakTraining.frame);
          pdfSpeakTraining.frame = 0;
        }
        try {
          if (pdfSpeakTraining.source && typeof pdfSpeakTraining.source.disconnect === "function") {
            pdfSpeakTraining.source.disconnect();
          }
        } catch (error) {
        }
        pdfSpeakTraining.source = null;
        pdfSpeakTraining.analyser = null;
        const ctx = pdfSpeakTraining.audioContext;
        pdfSpeakTraining.audioContext = null;
        if (ctx && typeof ctx.close === "function" && ctx.state !== "closed") {
          const closed = ctx.close();
          if (closed && typeof closed.catch === "function") {
            closed.catch(() => {});
          }
        }
      };

      const stopPdfSpeakTrainingStream = () => {
        if (pdfSpeakTraining.stream) {
          try {
            pdfSpeakTraining.stream.getTracks().forEach((track) => track.stop());
          } catch (error) {
          }
        }
        pdfSpeakTraining.stream = null;
      };

      const applyPdfSpeakTrainingServerVoiceSetting = (allowsWhisper) => {
        const allows = allowsWhisper !== false;
        const wasManaged = Boolean(pdfSpeakTraining.serverManaged);
        pdfSpeakTraining.serverAllowsWhisper = allows;
        pdfSpeakTraining.serverManaged = !allows;
        if (!allows) {
          pdfSpeakTraining.aiCheckVoiceFallbackActive = false;
          pdfSpeakTraining.aiCheckVoice = false;
        } else if (wasManaged && !pdfSpeakTraining.aiCheckVoiceFallbackActive) {
          pdfSpeakTraining.aiCheckVoice = readPdfSpeakTrainingAiCheckPreference();
        }
        syncPdfSpeakTrainingCheckModeUi();
        updatePdfSpeakTrainingControls();
      };

      const maybeReplayPdfSpeakTrainingLocalRecording = () => {
        if (!pdfSpeakTraining.blob || !pdfEls || !pdfEls.speakModal || pdfEls.speakModal.classList.contains("is-hidden")) {
          return;
        }
        window.setTimeout(() => {
          if (!pdfSpeakTraining.busy && pdfSpeakTraining.blob && pdfSpeakTraining.mode === "ready") {
            void replayPdfSpeakTraining();
          }
        }, 360);
      };

      const stopPdfSpeakTrainingBrowserLocalRecording = (options = {}) => {
        const autoReplay = Boolean(options && options.autoReplay);
        pdfSpeakTraining.browserLocalAutoReplay = autoReplay;
        const recorder = pdfSpeakTraining.recorder;
        if (recorder && recorder.state === "recording") {
          try {
            recorder.stop();
            return;
          } catch (error) {
          }
        }
        pdfSpeakTraining.browserLocalRecording = false;
        stopPdfSpeakTrainingStream();
        if (autoReplay) {
          maybeReplayPdfSpeakTrainingLocalRecording();
        }
      };

      const drawPdfSpeakTrainingWave = (progress = -1) => {
        const canvas = pdfEls && pdfEls.speakCanvas;
        if (!canvas) {
          return;
        }
        const rect = canvas.getBoundingClientRect();
        const width = Math.max(320, Math.round(rect.width || canvas.width || 720));
        const height = Math.max(150, Math.round(rect.height || canvas.height || 240));
        if (canvas.width !== width || canvas.height !== height) {
          canvas.width = width;
          canvas.height = height;
        }
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          return;
        }
        ctx.clearRect(0, 0, width, height);
        const now = performance.now();
        const centerY = height * 0.5;
        const drawRoundRect = (x, y, w, h, r) => {
          if (ctx.roundRect) {
            ctx.beginPath();
            ctx.roundRect(x, y, w, h, r);
            ctx.fill();
            return;
          }
          const rr = Math.min(r, Math.abs(w) * 0.5, Math.abs(h) * 0.5);
          ctx.beginPath();
          ctx.moveTo(x + rr, y);
          ctx.lineTo(x + w - rr, y);
          ctx.quadraticCurveTo(x + w, y, x + w, y + rr);
          ctx.lineTo(x + w, y + h - rr);
          ctx.quadraticCurveTo(x + w, y + h, x + w - rr, y + h);
          ctx.lineTo(x + rr, y + h);
          ctx.quadraticCurveTo(x, y + h, x, y + h - rr);
          ctx.lineTo(x, y + rr);
          ctx.quadraticCurveTo(x, y, x + rr, y);
          ctx.fill();
        };
        const backdrop = ctx.createRadialGradient(width * 0.5, centerY, 0, width * 0.5, centerY, Math.max(width, height) * 0.7);
        backdrop.addColorStop(0, "rgba(255, 204, 94, 0.08)");
        backdrop.addColorStop(0.46, "rgba(51, 255, 226, 0.055)");
        backdrop.addColorStop(1, "rgba(1, 7, 16, 0.1)");
        ctx.fillStyle = backdrop;
        ctx.fillRect(0, 0, width, height);
        const gradient = ctx.createLinearGradient(0, 0, width, height);
        gradient.addColorStop(0, "rgba(255, 190, 76, 0.88)");
        gradient.addColorStop(0.48, "rgba(255, 226, 140, 0.72)");
        gradient.addColorStop(1, "rgba(78, 255, 226, 0.76)");
        ctx.strokeStyle = "rgba(126, 255, 232, 0.12)";
        ctx.lineWidth = 1;
        for (let y = 0; y < height; y += 32) {
          ctx.beginPath();
          ctx.moveTo(0, y + 0.5);
          ctx.lineTo(width, y + 0.5);
          ctx.stroke();
        }
        ctx.strokeStyle = "rgba(255, 223, 142, 0.22)";
        ctx.beginPath();
        ctx.moveTo(0, centerY + 0.5);
        ctx.lineTo(width, centerY + 0.5);
        ctx.stroke();
        ctx.strokeStyle = "rgba(126, 255, 232, 0.07)";
        for (let x = 0; x < width; x += 42) {
          ctx.beginPath();
          ctx.moveTo(x + 0.5, 0);
          ctx.lineTo(x + 0.5, height);
          ctx.stroke();
        }
        const bars = 88;
        const gap = 3;
        const barWidth = Math.max(2, (width - (gap * (bars - 1))) / bars);
        let levels = [];
        if (pdfSpeakTraining.analyser) {
          const size = pdfSpeakTraining.analyser.frequencyBinCount || 512;
          const data = new Uint8Array(size);
          pdfSpeakTraining.analyser.getByteFrequencyData(data);
          for (let i = 0; i < bars; i += 1) {
            const idx = Math.floor((i / bars) * data.length);
            levels.push((data[idx] || 0) / 255);
          }
        } else if (pdfSpeakTraining.rows && pdfSpeakTraining.rows.length) {
          for (let i = 0; i < bars; i += 1) {
            const idx = Math.floor((i / Math.max(1, bars - 1)) * (pdfSpeakTraining.rows.length - 1));
            levels.push(Number(pdfSpeakTraining.rows[idx] || 0));
          }
        } else {
          const t = performance.now() * 0.003;
          for (let i = 0; i < bars; i += 1) {
            levels.push(pdfSpeakTraining.mode === "processing" ? (0.22 + Math.abs(Math.sin(t + i * 0.28)) * 0.54) : 0.08);
          }
        }
        if (pdfSpeakTraining.mode === "processing") {
          const t = performance.now() * 0.0042;
          const sweep = (t * 0.42) % 1;
          levels = levels.map((level, index) => {
            const ratio = bars > 1 ? index / (bars - 1) : 0;
            const distance = Math.abs(ratio - sweep);
            const scan = Math.max(0, 1 - distance * 8);
            const pulse = 0.26 + Math.abs(Math.sin(t * 2.4 + index * 0.36)) * 0.46;
            const recorded = Number(level || 0) * (0.54 + Math.abs(Math.sin(t * 1.6 + index * 0.11)) * 0.38);
            return Math.min(1, Math.max(recorded, pulse + scan * 0.32));
          });
        }
        const barGradient = ctx.createLinearGradient(0, centerY - height * 0.38, 0, centerY + height * 0.38);
        barGradient.addColorStop(0, "rgba(255, 226, 145, 0.96)");
        barGradient.addColorStop(0.5, "rgba(255, 182, 70, 0.74)");
        barGradient.addColorStop(1, "rgba(73, 255, 229, 0.86)");
        ctx.save();
        ctx.fillStyle = barGradient;
        ctx.shadowBlur = pdfSpeakTraining.mode === "processing" ? 18 : 10;
        ctx.shadowColor = "rgba(255, 202, 91, 0.32)";
        levels.forEach((level, index) => {
          const boost = pdfSpeakTraining.mode === "processing" ? (0.96 + Math.sin(now * 0.009 + index * 0.24) * 0.08) : 1;
          const value = Math.min(1, Math.max(0.035, Number(level || 0) * boost));
          const h = Math.max(6, value * (height * 0.76));
          const x = index * (barWidth + gap);
          const y = centerY - h / 2;
          ctx.globalAlpha = 0.38 + Math.min(0.62, value * 0.86);
          drawRoundRect(x, y, barWidth, h, Math.min(8, barWidth * 0.9));
          if (value > 0.62 || (pdfSpeakTraining.mode === "processing" && index % 9 === 0)) {
            ctx.globalAlpha = 0.24 + value * 0.28;
            ctx.fillStyle = "rgba(255, 240, 178, 0.88)";
            ctx.fillRect(x - 1, y - 4, barWidth + 2, 2);
            ctx.fillRect(x - 1, y + h + 2, barWidth + 2, 2);
            ctx.fillStyle = barGradient;
          }
        });
        ctx.restore();
        const lineGradient = ctx.createLinearGradient(0, 0, width, 0);
        lineGradient.addColorStop(0, "rgba(255, 209, 112, 0.2)");
        lineGradient.addColorStop(0.5, "rgba(255, 246, 190, 0.86)");
        lineGradient.addColorStop(1, "rgba(80, 255, 232, 0.28)");
        ctx.save();
        ctx.strokeStyle = lineGradient;
        ctx.lineWidth = 2;
        ctx.shadowBlur = 14;
        ctx.shadowColor = "rgba(255, 226, 145, 0.38)";
        ctx.beginPath();
        levels.forEach((level, index) => {
          const x = index * (barWidth + gap) + barWidth * 0.5;
          const waveY = centerY - (Number(level || 0) - 0.34) * height * 0.38;
          if (index === 0) ctx.moveTo(x, waveY);
          else ctx.lineTo(x, waveY);
        });
        ctx.stroke();
        ctx.restore();
        ctx.globalAlpha = 1;
        if (pdfSpeakTraining.mode === "processing") {
          const scanX = (now * 0.15) % (width + 130) - 65;
          const beam = ctx.createLinearGradient(scanX - 64, 0, scanX + 64, 0);
          beam.addColorStop(0, "rgba(255, 202, 96, 0)");
          beam.addColorStop(0.5, "rgba(255, 231, 156, 0.32)");
          beam.addColorStop(1, "rgba(88, 255, 230, 0)");
          ctx.fillStyle = beam;
          ctx.fillRect(Math.max(0, scanX - 66), 0, 132, height);
          ctx.strokeStyle = "rgba(255, 225, 145, 0.62)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(scanX, 8);
          ctx.lineTo(scanX, height - 8);
          ctx.stroke();
          for (let i = 0; i < 6; i += 1) {
            const px = (scanX - 120 + i * 38 + Math.sin(now * 0.004 + i) * 16 + width) % width;
            const py = centerY + Math.sin(now * 0.006 + i * 1.7) * height * 0.34;
            ctx.fillStyle = i % 2 ? "rgba(84, 255, 230, 0.86)" : "rgba(255, 224, 137, 0.88)";
            ctx.shadowBlur = 16;
            ctx.shadowColor = ctx.fillStyle;
            ctx.beginPath();
            ctx.arc(px, py, 2.4 + (i % 3) * 0.55, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.shadowBlur = 0;
        }
        if (progress >= 0) {
          const px = Math.max(0, Math.min(width, width * progress));
          ctx.fillStyle = "rgba(255, 224, 136, 0.18)";
          ctx.fillRect(0, 0, px, height);
          ctx.strokeStyle = "rgba(255, 224, 136, 0.9)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(px, 0);
          ctx.lineTo(px, height);
          ctx.stroke();
        }
        if (["recording", "processing", "playing"].includes(pdfSpeakTraining.mode)) {
          pdfSpeakTraining.frame = window.requestAnimationFrame(() => {
            let nextProgress = -1;
            if (pdfSpeakTraining.mode === "playing" && pdfSpeakTraining.audio && pdfSpeakTraining.audio.duration) {
              nextProgress = pdfSpeakTraining.audio.currentTime / Math.max(0.1, pdfSpeakTraining.audio.duration);
            }
            drawPdfSpeakTrainingWave(nextProgress);
          });
        }
      };

      const setPdfSpeakTrainingMode = (mode = "idle") => {
        pdfSpeakTraining.mode = mode;
        if (pdfEls && pdfEls.speakModal) {
          pdfEls.speakModal.querySelectorAll(".ft-pdf-speak-wave-panel").forEach((node) => {
            node.classList.toggle("is-processing", mode === "processing");
            node.classList.toggle("is-recording", mode === "recording");
            node.classList.toggle("is-playing", mode === "playing");
          });
          if (mode === "processing") {
            setPdfSpeakListeningIndicator(true, "Listening", "Server is analyzing your voice...");
          } else if (!pdfSpeakTraining.referenceAudioWarming) {
            setPdfSpeakListeningIndicator(false);
          }
        }
        if (pdfSpeakTraining.frame) {
          window.cancelAnimationFrame(pdfSpeakTraining.frame);
          pdfSpeakTraining.frame = 0;
        }
        drawPdfSpeakTrainingWave(mode === "ready" ? 0 : -1);
        updatePdfSpeakTrainingControls();
      };

      const preparePdfSpeakTrainingWaveFromBlob = async (blob) => {
        pdfSpeakTraining.rows = [];
        if (!blob || !blob.size) {
          drawPdfSpeakTrainingWave();
          return;
        }
        try {
          const buffer = await decodeAudioBlob(blob);
          pdfSpeakTraining.rows = audioRmsRows(buffer).map((row) => Number(row.level || 0));
        } catch (error) {
          pdfSpeakTraining.rows = [];
        }
        if (pdfSpeakTraining.busy || pdfSpeakTraining.mode === "processing") {
          drawPdfSpeakTrainingWave(-1);
        } else {
          setPdfSpeakTrainingMode("ready");
        }
      };

      const resetPdfSpeakTrainingRecording = () => {
        if (pdfSpeakTraining.recognitionActive || pdfSpeakTraining.recognition) {
          stopPdfSpeakTrainingBrowserRecognition(false);
        }
        closePdfSpeakTrainingAudioContext();
        stopPdfSpeakTrainingStream();
        if (pdfSpeakTraining.audio) {
          try {
            pdfSpeakTraining.audio.pause();
            pdfSpeakTraining.audio.removeAttribute("src");
            pdfSpeakTraining.audio.load();
          } catch (error) {
          }
        }
        pdfSpeakTraining.audio = null;
        if (pdfSpeakTraining.referenceAudio) {
          try { pdfSpeakTraining.referenceAudio.pause(); } catch (error) {}
          pdfSpeakTraining.referenceAudio = null;
        }
        if (pdfSpeakTraining.referenceFrame) {
          window.cancelAnimationFrame(pdfSpeakTraining.referenceFrame);
          pdfSpeakTraining.referenceFrame = 0;
        }
        if (pdfSpeakTraining.transcriptFrame) {
          window.cancelAnimationFrame(pdfSpeakTraining.transcriptFrame);
          pdfSpeakTraining.transcriptFrame = 0;
        }
        setPdfSpeakReferenceHighlight(-1);
        setPdfSpeakTranscriptHighlight(-1);
        if (pdfSpeakTraining.url) {
          try { URL.revokeObjectURL(pdfSpeakTraining.url); } catch (error) {}
        }
        pdfSpeakTraining.url = "";
        pdfSpeakTraining.blob = null;
        pdfSpeakTraining.rows = [];
        pdfSpeakTraining.chunks = [];
        pdfSpeakTraining.busy = false;
        pdfSpeakTraining.cancelStop = false;
        pdfSpeakTraining.transcriptTokens = [];
        pdfSpeakTraining.transcriptTimeline = [];
        pdfSpeakTraining.referenceHighlightIndex = -1;
        pdfSpeakTraining.transcriptHighlightIndex = -1;
        if (pdfEls) {
          if (pdfEls.speakScore) {
            pdfEls.speakScore.textContent = "0%";
          }
          if (pdfEls.speakTranscript) {
            pdfEls.speakTranscript.textContent = "Bạn nói là: đang ghi âm...";
          }
          if (pdfEls.speakFeedback) {
            pdfEls.speakFeedback.textContent = "Listening now. Results will appear after you stop recording.";
          }
          if (pdfEls.speakReferenceText) {
            renderPdfSpeakInlineText(pdfEls.speakReferenceText, pdfSpeakTraining.referenceText || pdfSpeakTrainingText(), pdfSpeakTraining.referenceTokens || [], { prefix: "ref" });
          }
          if (pdfEls.speakReferenceIpa) {
            renderPdfSpeakInlineText(pdfEls.speakReferenceIpa, pdfSpeakTraining.referenceIpa || "", pdfSpeakTraining.referenceTokens || [], { prefix: "ipa", ipaMode: true });
          }
        }
        setPdfSpeakTrainingMode("idle");
        updatePdfSpeakTrainingControls();
      };

      const pdfSpeakPlainTokens = (text = "") => clean(text).split(/\s+/).filter(Boolean).map((token) => ({
        expected: token.replace(/^[^A-Za-z0-9']+|[^A-Za-z0-9']+$/g, "") || token,
        ok: false,
      }));

      const pdfSpeakTokenKey = (value = "") => clean(value)
        .toLowerCase()
        .replace(/[\u2018\u2019`]/g, "'")
        .replace(/^[^a-z0-9']+|[^a-z0-9']+$/gi, "")
        .replace(/[^a-z0-9']/gi, "");

      const pdfSpeakRowToken = (row = {}) => clean(row.expected || row.word || row.text || row.spoken || "");

      const pdfSpeakExpectedRows = () => {
        const text = pdfSpeakTraining.referenceText || pdfSpeakTrainingText();
        const source = Array.isArray(pdfSpeakTraining.referenceTokens) && pdfSpeakTraining.referenceTokens.length
          ? pdfSpeakTraining.referenceTokens
          : pdfSpeakPlainTokens(text);
        return source.map((row, index) => {
          const token = clean(pdfSpeakRowToken(row));
          return {
            ...row,
            expected: token || clean(row.expected || row.word || row.text || ""),
            index,
          };
        }).filter((row) => pdfSpeakTokenKey(row.expected));
      };

      const scorePdfSpeakTrainingBrowserTranscript = (rawInput = "") => {
        const expectedRows = pdfSpeakExpectedRows();
        const spokenItems = (clean(rawInput).match(/[A-Za-z0-9]+(?:['\u2019][A-Za-z0-9]+)?/g) || [])
          .map((token) => ({ text: token, norm: pdfSpeakTokenKey(token) }))
          .filter((item) => item.norm);
        const spokenCounts = new Map();
        spokenItems.forEach((item) => {
          spokenCounts.set(item.norm, (spokenCounts.get(item.norm) || 0) + 1);
        });
        const expectedCounts = new Map();
        expectedRows.forEach((row) => {
          const key = pdfSpeakTokenKey(row.expected);
          if (key) {
            expectedCounts.set(key, (expectedCounts.get(key) || 0) + 1);
          }
        });
        const details = expectedRows.map((row, index) => {
          const key = pdfSpeakTokenKey(row.expected);
          const remaining = spokenCounts.get(key) || 0;
          const ok = remaining > 0;
          if (ok) {
            spokenCounts.set(key, remaining - 1);
          }
          return {
            ...row,
            expected: clean(row.expected),
            spoken: ok ? clean(row.expected) : "",
            ok,
            similarity: ok ? 100 : 0,
            index,
          };
        });
        const transcriptRows = spokenItems.map((item, index) => {
          const remaining = expectedCounts.get(item.norm) || 0;
          const ok = remaining > 0;
          if (ok) {
            expectedCounts.set(item.norm, remaining - 1);
          }
          return {
            expected: item.text,
            word: item.text,
            text: item.text,
            spoken: item.text,
            ok,
            extra: !ok,
            similarity: ok ? 100 : 0,
            index,
          };
        });
        const correct = details.filter((row) => row.ok).length;
        const total = details.length;
        const score = total ? Math.round((correct / total) * 100) : 0;
        return {
          expectedRows,
          spokenItems,
          transcriptRows,
          details,
          correct,
          total,
          score,
          text: clean(rawInput),
          transcript: clean(rawInput),
          feedback: `Browser live check: ${correct}/${total} tokens detected.`,
        };
      };
