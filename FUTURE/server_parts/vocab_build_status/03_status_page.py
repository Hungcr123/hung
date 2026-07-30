# Loaded by FUTURE.server_parts.10_vocab_build_status into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def status_page() -> str:
    title = html.escape("Future Whisper Server")
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071015;
      --panel: rgba(12, 25, 34, 0.82);
      --line: rgba(104, 243, 226, 0.28);
      --cyan: #68f3e2;
      --pink: #ff71ce;
      --green: #7cffb2;
      --yellow: #ffd166;
      --red: #ff7a90;
      --text: #f3fbff;
      --muted: #9bb4bd;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      min-height: 100vh;
      margin: 0;
      display: grid;
      place-items: center;
      padding: 28px;
      background:
        radial-gradient(circle at 18% 12%, rgba(255, 113, 206, 0.18), transparent 28%),
        radial-gradient(circle at 86% 22%, rgba(104, 243, 226, 0.2), transparent 32%),
        linear-gradient(135deg, #05070c, var(--bg) 46%, #101020);
      color: var(--text);
      font-family: Inter, Segoe UI, system-ui, -apple-system, sans-serif;
    }}
    main {{
      width: min(1180px, 100%);
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(180deg, rgba(19, 42, 52, 0.9), rgba(7, 16, 21, 0.92));
      box-shadow: 0 28px 90px rgba(0, 0, 0, 0.48), 0 0 60px rgba(104, 243, 226, 0.12);
      overflow: hidden;
    }}
    .top {{
      padding: 28px;
      border-bottom: 1px solid rgba(104, 243, 226, 0.18);
      display: flex;
      gap: 18px;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(26px, 4vw, 42px);
      line-height: 1;
      letter-spacing: 0;
    }}
    .sub {{
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }}
    .pill {{
      min-width: 132px;
      padding: 12px 16px;
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 999px;
      color: var(--yellow);
      background: rgba(255, 209, 102, 0.1);
      text-align: center;
      font-weight: 900;
      box-shadow: 0 0 28px rgba(255, 209, 102, 0.1);
    }}
    .pill.ready {{
      color: var(--green);
      background: rgba(124, 255, 178, 0.1);
      box-shadow: 0 0 30px rgba(124, 255, 178, 0.16);
    }}
    .pill.error {{
      color: var(--red);
      background: rgba(255, 122, 144, 0.1);
      box-shadow: 0 0 30px rgba(255, 122, 144, 0.16);
    }}
    .dashboard-status-stack {{
      display: grid;
      justify-items: end;
      gap: 8px;
      min-width: 158px;
    }}
    .dashboard-freshness {{
      min-width: 142px;
      min-height: 30px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      border: 1px solid rgba(104, 243, 226, 0.34);
      border-radius: 999px;
      padding: 0 12px;
      color: #061115;
      background:
        radial-gradient(circle at 18% 50%, rgba(255, 255, 255, 0.82), transparent 18%),
        linear-gradient(135deg, rgba(104, 243, 226, 0.96), rgba(162, 255, 203, 0.92));
      box-shadow:
        0 0 0 1px rgba(5, 20, 24, 0.24),
        0 0 24px rgba(104, 243, 226, 0.22);
      font-size: 11px;
      font-weight: 950;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .dashboard-freshness::before {{
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: #063018;
      box-shadow: 0 0 14px rgba(10, 78, 42, 0.38);
    }}
    .dashboard-freshness.is-old {{
      color: rgba(226, 240, 240, 0.86);
      border-color: rgba(255, 255, 255, 0.14);
      background: rgba(255, 255, 255, 0.07);
      box-shadow: inset 0 0 18px rgba(255, 255, 255, 0.035);
    }}
    .dashboard-freshness.is-old::before {{
      background: rgba(226, 240, 240, 0.62);
      box-shadow: none;
    }}
    .dashboard-warm-log {{
      max-width: 260px;
      min-height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: flex-end;
      gap: 7px;
      border: 1px solid rgba(104, 243, 226, 0.16);
      border-radius: 999px;
      padding: 0 10px;
      color: rgba(204, 234, 236, 0.86);
      background: rgba(1, 8, 12, 0.36);
      box-shadow: inset 0 0 18px rgba(104, 243, 226, 0.035);
      font-size: 11px;
      font-weight: 850;
      line-height: 1.2;
      text-align: right;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .dashboard-warm-log::before {{
      content: "";
      width: 8px;
      height: 8px;
      flex: 0 0 auto;
      border-radius: 999px;
      background: var(--yellow);
      box-shadow: 0 0 14px rgba(255, 209, 102, 0.35);
      animation: pulse 1.8s infinite;
    }}
    .dashboard-warm-log.is-ready {{
      color: var(--green);
      border-color: rgba(124, 255, 178, 0.2);
      background: rgba(124, 255, 178, 0.075);
    }}
    .dashboard-warm-log.is-ready::before {{
      background: var(--green);
      box-shadow: 0 0 14px rgba(124, 255, 178, 0.38);
      animation: none;
    }}
    .actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 16px;
    }}
    .tabs {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      padding: 14px 22px 0;
      border-top: 1px solid rgba(104, 243, 226, 0.08);
      overflow: visible;
    }}
    .tab {{
      min-height: 38px;
      border: 1px solid rgba(104, 243, 226, 0.26);
      border-radius: 999px;
      padding: 0 14px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.045);
      font-weight: 950;
      cursor: pointer;
    }}
    .tab.is-active {{
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
    }}
    .tab-panel[hidden] {{ display: none !important; }}
    .action {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 0 16px;
      border: 1px solid rgba(104, 243, 226, 0.4);
      border-radius: 999px;
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
      font-size: 13px;
      font-weight: 950;
      font-family: inherit;
      text-decoration: none;
      box-shadow: 0 0 28px rgba(104, 243, 226, 0.18);
      cursor: pointer;
    }}
    .copy {{
      margin-top: 12px;
      min-height: 38px;
      border: 1px solid rgba(104, 243, 226, 0.38);
      border-radius: 12px;
      color: var(--cyan);
      background: rgba(104, 243, 226, 0.08);
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;
    }}
    .pending-list {{
      display: grid;
      gap: 10px;
    }}
    .pending-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 8px;
      align-items: center;
      padding: 10px;
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.045);
    }}
    .pending-name {{
      min-width: 0;
      font-size: 13px;
      line-height: 1.35;
    }}
    .pending-action {{
      min-height: 34px;
      border: 1px solid rgba(104, 243, 226, 0.34);
      border-radius: 11px;
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;
    }}
    .pending-action.reject {{
      color: var(--red);
      background: rgba(255, 122, 144, 0.09);
    }}
    .online-users {{
      display: grid;
      gap: 12px;
      padding: 22px;
    }}
    .dashboard-log-panel {{
      display: grid;
      gap: 12px;
      padding: 22px;
    }}
    .dashboard-log-toolbar {{
      display: grid;
      grid-template-columns: 160px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
    }}
    .dashboard-log-input {{
      min-height: 38px;
      min-width: 0;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 12px;
      padding: 0 12px;
      color: var(--text);
      background: rgba(1, 8, 12, 0.62);
      outline: none;
      font: 850 13px/1 Inter, Segoe UI, system-ui, sans-serif;
    }}
    .dashboard-log-list {{
      display: grid;
      gap: 10px;
    }}
    .dashboard-log-list[hidden] {{
      display: none !important;
    }}
    .dashboard-log-row {{
      display: grid;
      grid-template-columns: 160px minmax(120px, 0.45fr) minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      padding: 11px 12px;
      border: 1px solid rgba(104, 243, 226, 0.16);
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.045);
    }}
    .dashboard-log-time {{
      color: var(--cyan);
      font-size: 12px;
      font-weight: 950;
    }}
    .dashboard-log-user {{
      color: var(--yellow);
      font-size: 13px;
      font-weight: 950;
      word-break: break-word;
    }}
    .dashboard-log-detail {{
      color: var(--text);
      font-size: 13px;
      line-height: 1.42;
      font-weight: 820;
      word-break: break-word;
    }}
    .dashboard-log-list.worker-list {{
      min-width: 0;
      overflow: visible;
      padding-right: 8px;
    }}
    .dashboard-log-row.worker-row {{
      grid-template-columns: minmax(72px, 0.14fr) minmax(160px, 0.22fr) minmax(0, 1fr);
      padding-right: 18px;
    }}
    .dashboard-log-row.worker-row .dashboard-log-detail {{
      min-width: 0;
      white-space: normal;
      overflow-wrap: anywhere;
      word-break: normal;
    }}
    .dashboard-log-row.worker-machine-row {{
      background: rgba(125, 211, 252, 0.12);
      border-color: rgba(125, 211, 252, 0.34);
      margin-top: 8px;
    }}
    .dashboard-log-row.worker-instance-row {{
      margin-left: 18px;
      border-left-color: rgba(250, 204, 21, 0.34);
    }}
    .worker-log-toggle {{
      margin: 8px 0 12px;
      min-height: 34px;
      padding: 0 12px;
      font-size: 12px;
    }}
    .gmail-panel {{
      padding: 18px;
    }}
    .gmail-mailbox {{
      display: grid;
      gap: 14px;
    }}
    .gmail-topbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 18px;
      border: 1px solid rgba(104, 243, 226, 0.22);
      border-radius: 18px;
      background: linear-gradient(135deg, rgba(104, 243, 226, 0.12), rgba(255, 113, 206, 0.08));
    }}
    .gmail-title {{
      font-size: 24px;
      font-weight: 950;
      letter-spacing: 0;
    }}
    .gmail-subtitle,
    .gmail-expiry {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .gmail-status {{
      min-height: 36px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 12px;
      border: 1px solid rgba(124, 255, 178, 0.24);
      border-radius: 999px;
      color: var(--green);
      background: rgba(124, 255, 178, 0.08);
      font-size: 12px;
      font-weight: 850;
      text-align: center;
    }}
    .gmail-status.is-error {{
      color: var(--red);
      border-color: rgba(255, 122, 144, 0.3);
      background: rgba(255, 122, 144, 0.08);
    }}
    .gmail-address-card {{
      display: grid;
      gap: 12px;
      padding: 16px;
      border: 1px solid rgba(104, 243, 226, 0.2);
      border-radius: 18px;
      background: rgba(5, 12, 18, 0.5);
    }}
    .gmail-address-line {{
      display: grid;
      grid-template-columns: minmax(120px, 0.82fr) auto minmax(180px, 1fr);
      gap: 8px;
      align-items: center;
    }}
    .gmail-local-input,
    .gmail-domain-input {{
      min-height: 46px;
      width: 100%;
      min-width: 0;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 14px;
      padding: 0 14px;
      color: var(--text);
      background: rgba(0, 0, 0, 0.22);
      font: inherit;
      font-weight: 800;
      outline: none;
    }}
    .gmail-at {{
      color: var(--cyan);
      font-weight: 950;
      font-size: 18px;
    }}
    .gmail-preview-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .gmail-preview-row code {{
      flex: 1 1 260px;
      min-height: 38px;
      display: inline-flex;
      align-items: center;
      padding: 0 12px;
      border: 1px solid rgba(255, 209, 102, 0.22);
      border-radius: 12px;
      color: var(--yellow);
      background: rgba(255, 209, 102, 0.08);
      overflow-wrap: anywhere;
    }}
    .gmail-history-panel[hidden],
    .gmail-history-list[hidden] {{
      display: none !important;
    }}
    .gmail-history-panel {{
      display: grid;
      gap: 8px;
    }}
    .gmail-history-search {{
      min-height: 40px;
      width: 100%;
      border: 1px solid rgba(104, 243, 226, 0.24);
      border-radius: 12px;
      padding: 0 12px;
      color: var(--text);
      background: rgba(0, 0, 0, 0.22);
      font: inherit;
      font-weight: 800;
      outline: none;
    }}
    .gmail-history-list {{
      display: grid;
      gap: 8px;
      max-height: 190px;
      overflow: auto;
      padding: 10px;
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 14px;
      background: rgba(0, 0, 0, 0.18);
    }}
    .gmail-history-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      min-height: 38px;
      padding: 0 10px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      color: var(--text);
      background: rgba(255, 255, 255, 0.045);
      cursor: pointer;
      text-align: left;
      font: inherit;
    }}
    .gmail-history-row:hover,
    .gmail-history-row.is-active {{
      border-color: rgba(104, 243, 226, 0.3);
      background: rgba(104, 243, 226, 0.08);
    }}
    .gmail-history-address {{
      min-width: 0;
      overflow: hidden;
      color: var(--yellow);
      font-weight: 900;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .gmail-history-meta {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }}
    .gmail-config-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      padding: 14px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.035);
    }}
    .gmail-config-strip .notice-save {{
      min-height: 38px;
    }}
    .gmail-config-strip[hidden],
    .gmail-alias-chips[hidden] {{
      display: none !important;
    }}
    .gmail-alias-chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      min-height: 42px;
      align-items: center;
    }}
    .gmail-chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      max-width: 100%;
      padding: 0 10px;
      border: 1px solid rgba(104, 243, 226, 0.22);
      border-radius: 999px;
      color: var(--text);
      background: rgba(104, 243, 226, 0.07);
      font-size: 12px;
    }}
    .gmail-chip button {{
      min-height: 24px;
      border-radius: 999px;
      padding: 0 8px;
      border: 1px solid rgba(255, 122, 144, 0.35);
      color: var(--red);
      background: rgba(255, 122, 144, 0.08);
      cursor: pointer;
    }}
    .gmail-layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(300px, 0.95fr);
      gap: 14px;
      align-items: stretch;
    }}
    .gmail-inbox,
    .gmail-reader {{
      min-width: 0;
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 18px;
      background: rgba(5, 12, 18, 0.46);
      overflow: hidden;
    }}
    .gmail-section-head {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      padding: 14px;
      border-bottom: 1px solid rgba(104, 243, 226, 0.14);
      color: var(--text);
      font-weight: 900;
    }}
    .gmail-section-head span:last-child {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .gmail-table-head,
    .gmail-message-row {{
      display: grid;
      grid-template-columns: 86px minmax(0, 1fr) 92px 76px;
      gap: 8px;
      align-items: center;
      padding: 10px 12px;
    }}
    .gmail-table-head {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 900;
      text-transform: uppercase;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }}
    .gmail-message-list {{
      display: grid;
      max-height: 460px;
      overflow: auto;
    }}
    .gmail-message-row {{
      border: 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
      color: var(--text);
      background: transparent;
      cursor: pointer;
      text-align: left;
      font: inherit;
    }}
    .gmail-message-row:hover,
    .gmail-message-row.is-active {{
      background: rgba(104, 243, 226, 0.08);
    }}
    .gmail-message-row .gmail-time {{
      color: var(--cyan);
      font-size: 12px;
    }}
    .gmail-message-row .gmail-sender {{
      min-width: 0;
      overflow: hidden;
      color: var(--text);
      font-size: 13px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .gmail-message-row .gmail-code {{
      color: var(--yellow);
      font-weight: 950;
      text-align: center;
    }}
    .gmail-message-row .gmail-code.is-copyable,
    .gmail-reader-code strong.is-copyable {{
      cursor: pointer;
      text-decoration: underline;
      text-decoration-style: dotted;
      text-underline-offset: 4px;
    }}
    .gmail-message-row .gmail-code.is-copyable:hover,
    .gmail-reader-code strong.is-copyable:hover {{
      color: #fff2a8;
    }}
    .gmail-message-row .gmail-action {{
      color: var(--green);
      font-size: 12px;
      font-weight: 900;
      text-align: right;
    }}
    .gmail-empty {{
      padding: 18px;
      color: var(--muted);
      font-size: 13px;
    }}
    .gmail-reader {{
      padding: 16px;
      display: grid;
      gap: 12px;
      align-content: start;
    }}
    .gmail-back {{
      justify-self: start;
      min-height: 32px;
      padding: 0 12px;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 999px;
      color: var(--cyan);
      background: rgba(104, 243, 226, 0.08);
      cursor: pointer;
      font-weight: 900;
    }}
    .gmail-reader-subject {{
      color: var(--text);
      font-size: 20px;
      font-weight: 950;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }}
    .gmail-reader-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      color: var(--muted);
      font-size: 12px;
    }}
    .gmail-reader-code {{
      display: grid;
      gap: 6px;
      padding: 14px;
      border: 1px solid rgba(255, 209, 102, 0.24);
      border-radius: 16px;
      background: rgba(255, 209, 102, 0.08);
    }}
    .gmail-reader-code span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .gmail-reader-code strong {{
      color: var(--yellow);
      font-size: 30px;
      line-height: 1;
      letter-spacing: 0;
    }}
    .gmail-reader-body {{
      min-height: 220px;
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      color: var(--text);
      font: 13px/1.5 Consolas, ui-monospace, monospace;
    }}
    .reward-settings-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .reward-settings-card {{
      border: 1px solid rgba(255, 209, 102, 0.22);
      border-radius: 18px;
      padding: 14px;
      background:
        radial-gradient(circle at 18% 0, rgba(255, 209, 102, 0.14), transparent 42%),
        rgba(255, 255, 255, 0.045);
      box-shadow: inset 0 0 24px rgba(104, 243, 226, 0.05);
    }}
    .reward-settings-title {{
      color: var(--yellow);
      font-size: 13px;
      font-weight: 950;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .reward-settings-row {{
      display: grid;
      grid-template-columns: 70px repeat(6, minmax(48px, 1fr)) 70px;
      gap: 8px;
      align-items: center;
      padding: 8px 0;
      border-top: 1px solid rgba(104, 243, 226, 0.12);
    }}
    .reward-settings-row.is-header {{
      padding: 6px 0 4px;
      color: rgba(239, 254, 250, 0.62);
      font-size: 10px;
      font-weight: 950;
      letter-spacing: 0.12em;
      text-align: center;
      text-transform: uppercase;
    }}
    .reward-rank-label {{
      color: var(--cyan);
      font-size: 12px;
      font-weight: 950;
    }}
    .level-settings-list {{
      display: grid;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .level-settings-row {{
      display: grid;
      grid-template-columns: 92px minmax(140px, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 10px;
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 16px;
      background:
        linear-gradient(135deg, rgba(104, 243, 226, 0.08), rgba(255, 173, 80, 0.055)),
        rgba(1, 8, 12, 0.52);
      box-shadow: inset 0 0 18px rgba(104, 243, 226, 0.045);
    }}
    .level-settings-row.is-header {{
      border-color: rgba(255, 209, 102, 0.2);
      color: rgba(239, 254, 250, 0.68);
      background: rgba(255, 255, 255, 0.03);
      font-size: 10px;
      font-weight: 950;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .level-settings-input {{
      width: 100%;
      min-height: 38px;
      border: 1px solid rgba(104, 243, 226, 0.3);
      border-radius: 12px;
      padding: 0 10px;
      color: var(--text);
      background: rgba(1, 8, 12, 0.72);
      outline: none;
      font: 950 14px/1 Inter, Segoe UI, system-ui, sans-serif;
      text-align: center;
    }}
    .level-settings-remove {{
      min-height: 34px;
      border: 1px solid rgba(255, 101, 132, 0.32);
      border-radius: 10px;
      color: #ffdbe3;
      background: rgba(255, 101, 132, 0.11);
      font-size: 11px;
      font-weight: 950;
      cursor: pointer;
    }}
    .reward-badge-label {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 850;
      text-align: center;
    }}
    .reward-settings-input {{
      min-height: 36px;
      min-width: 0;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 12px;
      color: var(--text);
      background: rgba(1, 8, 12, 0.68);
      text-align: center;
      font: 950 14px/1 Inter, Segoe UI, system-ui, sans-serif;
      outline: none;
    }}
    .online-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 10px;
      align-items: stretch;
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 16px;
      padding: 12px;
      background: rgba(255, 255, 255, 0.045);
    }}
    .online-controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .online-identity {{
      flex: 1 1 220px;
      min-width: 180px;
      padding: 9px 11px;
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 13px;
      background:
        linear-gradient(135deg, rgba(104, 243, 226, 0.08), transparent 62%),
        rgba(1, 8, 12, 0.46);
      box-shadow: inset 0 0 18px rgba(104, 243, 226, 0.05);
    }}
    .online-actions {{
      flex: 2 1 540px;
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
      min-width: 0;
    }}
    .online-actions .pending-action {{
      min-height: 34px;
      padding: 0 12px;
      white-space: nowrap;
    }}
    .online-actions .admin-password-input {{
      flex: 0 1 150px;
      width: 150px;
      min-width: 118px;
      max-width: 170px;
      min-height: 34px;
      padding: 0 10px;
      font-size: 13px;
      text-align: left;
      border-radius: 10px;
    }}
    .online-name {{ font-weight: 950; }}
    .online-meta {{ margin-top: 0; color: var(--muted); font-size: 12px; font-weight: 800; }}
    .online-realtime {{
      padding: 9px 11px;
      border: 1px solid rgba(255, 209, 102, 0.24);
      border-radius: 13px;
      color: var(--yellow);
      background:
        linear-gradient(90deg, rgba(255, 209, 102, 0.11), rgba(104, 243, 226, 0.045)),
        rgba(1, 8, 12, 0.54);
      box-shadow: inset 0 0 22px rgba(255, 209, 102, 0.045);
      font-size: 12px;
      line-height: 1.4;
      font-weight: 920;
      word-break: break-word;
    }}
    .online-realtime.is-idle {{
      color: var(--muted);
      border-color: rgba(104, 243, 226, 0.16);
      background: rgba(1, 8, 12, 0.36);
      box-shadow: none;
    }}
    .online-details {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(180px, 240px);
      gap: 8px 14px;
      align-items: start;
    }}
    .online-details-text {{
      min-width: 0;
      padding: 8px 10px;
      border: 1px solid rgba(104, 243, 226, 0.12);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.032);
    }}
    .online-activity {{
      margin-top: 8px;
      padding: 8px 10px;
      border: 1px solid rgba(255, 209, 102, 0.22);
      border-radius: 12px;
      color: var(--yellow);
      background: rgba(255, 209, 102, 0.07);
      font-size: 12px;
      line-height: 1.4;
      font-weight: 900;
      word-break: break-word;
    }}
    .online-dot {{
      width: 9px;
      height: 9px;
      display: inline-block;
      margin-right: 7px;
      border-radius: 999px;
      background: var(--green);
      box-shadow: 0 0 14px rgba(124, 255, 178, 0.46);
      vertical-align: 1px;
    }}
    .online-dot.off {{
      background: var(--muted);
      box-shadow: none;
    }}
    .online-screen-preview {{
      width: min(240px, 100%);
      aspect-ratio: 16 / 9;
      margin-top: 0;
      justify-self: end;
      border: 1px solid rgba(104, 243, 226, 0.24);
      border-radius: 10px;
      display: grid;
      place-items: center;
      overflow: hidden;
      color: var(--muted);
      background:
        linear-gradient(90deg, rgba(104, 243, 226, 0.06) 1px, transparent 1px),
        linear-gradient(0deg, rgba(104, 243, 226, 0.06) 1px, transparent 1px),
        rgba(1, 8, 12, 0.72);
      background-size: 18px 18px;
      cursor: pointer;
      font-size: 11px;
      font-weight: 900;
    }}
    .online-screen-preview img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
      background: #02080b;
    }}
    .online-screen-preview.is-live {{
      border-color: rgba(255, 209, 102, 0.48);
      box-shadow: 0 0 24px rgba(255, 209, 102, 0.12);
    }}
    .online-screen-preview-note {{
      grid-column: 2;
      justify-self: end;
      margin-top: 0;
      color: var(--muted);
      font-size: 11px;
      font-weight: 850;
    }}
    .chat-badge {{
      min-width: 24px;
      height: 24px;
      display: inline-grid;
      place-items: center;
      border-radius: 999px;
      color: #061115;
      background: var(--yellow);
      font-size: 12px;
      font-weight: 950;
    }}
    .chat-badge.is-empty {{ color: var(--muted); background: rgba(255,255,255,0.08); }}
    .admin-chat-modal {{
      position: fixed;
      inset: 0;
      z-index: 20;
      display: none;
      place-items: center;
      padding: 18px;
      background: rgba(0, 0, 0, 0.58);
    }}
    .admin-chat-modal.is-open {{ display: grid; }}
    .admin-chat-card {{
      width: min(760px, 100%);
      border: 1px solid rgba(104, 243, 226, 0.34);
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(14, 31, 39, 0.96), rgba(4, 11, 16, 0.98));
      box-shadow: 0 28px 90px rgba(0,0,0,0.52);
      overflow: hidden;
    }}
    .admin-chat-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(104, 243, 226, 0.16);
      font-weight: 950;
    }}
    .admin-chat-log {{
      min-height: 260px;
      max-height: 420px;
      overflow: auto;
      display: grid;
      align-content: start;
      gap: 8px;
      padding: 14px;
    }}
    .admin-msg {{
      max-width: 82%;
      border: 1px solid rgba(104, 243, 226, 0.2);
      border-radius: 14px;
      padding: 9px 11px;
      background: rgba(255,255,255,0.055);
      font-size: 13px;
      line-height: 1.45;
      font-weight: 800;
    }}
    .admin-msg.is-admin {{
      justify-self: end;
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
    }}
    .admin-msg-text {{
      white-space: pre-wrap;
    }}
    .admin-attachments {{
      display: grid;
      justify-items: start;
      gap: 8px;
      margin-top: 8px;
    }}
    .admin-thumb {{
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 12px;
      padding: 0;
      overflow: hidden;
      background: transparent;
      cursor: pointer;
      line-height: 0;
    }}
    .admin-thumb img {{
      width: auto;
      height: auto;
      max-width: min(240px, 56vw);
      max-height: 250px;
      object-fit: contain;
      display: block;
      border-radius: 11px;
    }}
    .admin-file {{
      display: inline-flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      min-height: 38px;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 12px;
      padding: 8px 10px;
      color: inherit;
      background: rgba(1, 8, 12, 0.18);
      text-decoration: none;
      font-size: 12px;
      font-weight: 900;
    }}
    .admin-audio-clip {{
      display: grid;
      gap: 7px;
      max-width: min(300px, 58vw);
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 12px;
      padding: 8px;
      background: rgba(1, 8, 12, 0.18);
    }}
    .admin-audio-clip audio {{
      width: 100%;
      min-width: 200px;
    }}
    .admin-audio-download {{
      color: inherit;
      font-size: 11px;
      font-weight: 900;
      text-decoration: none;
    }}
    .admin-read-state {{
      margin-top: 6px;
      font-size: 10px;
      font-weight: 950;
      letter-spacing: 0.08em;
      opacity: 0.72;
      text-transform: uppercase;
    }}
    .admin-chat-compose {{
      display: grid;
      gap: 11px;
      padding: 14px;
      border-top: 1px solid rgba(104, 243, 226, 0.16);
    }}
    .admin-chat-tools {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .admin-chat-row {{
      display: grid;
      grid-template-columns: minmax(170px, 0.34fr) minmax(0, 1fr) auto auto;
      gap: 10px;
      align-items: stretch;
    }}
    .admin-chat-select {{
      width: 100%;
      min-height: 48px;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 14px;
      color: var(--text);
      background: rgba(1, 8, 12, 0.78);
      padding: 0 10px;
      font: 850 12px/1.35 Inter, Segoe UI, system-ui, sans-serif;
      outline: none;
    }}
    .admin-chat-small-note {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .admin-chat-speech-mode {{
      min-height: 34px;
      border: 1px solid rgba(104, 243, 226, 0.34);
      border-radius: 11px;
      color: var(--muted);
      background: rgba(1, 8, 12, 0.72);
      padding: 0 10px;
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;
    }}
    .admin-chat-translate.is-active {{
      border-color: rgba(104, 243, 226, 0.72);
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
    }}
    .admin-chat-audio-toggle {{
      min-height: 48px;
      border: 1px solid rgba(104, 243, 226, 0.34);
      border-radius: 14px;
      color: var(--muted);
      background: rgba(1, 8, 12, 0.72);
      font-size: 12px;
      font-weight: 950;
      cursor: pointer;
      white-space: nowrap;
    }}
    .admin-chat-audio-toggle.is-on {{
      border-color: rgba(104, 243, 226, 0.72);
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
    }}
    .stream-audio-mode {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 8px;
    }}
    .stream-mode-button {{
      min-height: 38px;
      border: 1px solid rgba(104, 243, 226, 0.34);
      border-radius: 12px;
      color: var(--muted);
      background: rgba(1, 8, 12, 0.72);
      padding: 0 13px;
      font-size: 12px;
      font-weight: 950;
      cursor: pointer;
    }}
    .stream-mode-button.is-active {{
      border-color: rgba(104, 243, 226, 0.78);
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
    }}
    .stream-mode-note {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }}
    .admin-chat-attach {{
      min-height: 34px;
      border: 1px solid rgba(104, 243, 226, 0.34);
      border-radius: 11px;
      color: var(--cyan);
      background: rgba(104, 243, 226, 0.08);
      font-size: 12px;
      font-weight: 900;
      cursor: pointer;
    }}
    .admin-chat-attach.is-recording {{
      color: #061115;
      border-color: rgba(255, 122, 144, 0.82);
      background: linear-gradient(135deg, #ff7a90, #ffd166);
    }}
    .admin-chat-attach.is-busy {{
      opacity: 0.74;
      cursor: wait;
    }}
    .admin-chat-row .notice-input {{
      min-height: 58px;
      padding: 10px 12px;
    }}
    .admin-chat-input-vi {{
      border-color: rgba(74, 222, 128, 0.42);
      background: rgba(4, 28, 20, 0.72);
    }}
    .admin-chat-input-en {{
      border-color: rgba(96, 165, 250, 0.42);
      background: rgba(8, 18, 38, 0.72);
    }}
    .admin-chat-row .notice-input::placeholder {{
      color: rgba(225, 248, 246, 0.52);
    }}
    .admin-image-viewer {{
      position: fixed;
      inset: 0;
      z-index: 42;
      display: none;
      place-items: center;
      padding: 18px;
      background: rgba(0, 0, 0, 0.82);
      backdrop-filter: blur(7px);
    }}
    .admin-image-viewer.is-open {{ display: grid; }}
    .admin-image-viewer img {{
      max-width: min(100%, 1200px);
      max-height: calc(100vh - 92px);
      object-fit: contain;
      border-radius: 14px;
      box-shadow: 0 24px 90px rgba(0, 0, 0, 0.62);
      background: #061115;
      cursor: grab;
      transform-origin: center center;
      user-select: none;
      touch-action: none;
      will-change: transform;
    }}
    .admin-image-viewer img.is-dragging {{ cursor: grabbing; }}
    .admin-image-tools {{
      position: fixed;
      top: 16px;
      right: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      z-index: 43;
    }}
    .admin-image-close,
    .admin-image-download,
    .admin-image-zoom {{
      min-height: 38px;
      border: 1px solid rgba(104, 243, 226, 0.4);
      border-radius: 12px;
      padding: 0 12px;
      color: var(--text);
      background: rgba(1, 8, 12, 0.82);
      font-size: 12px;
      font-weight: 950;
      cursor: pointer;
      text-decoration: none;
    }}
    .admin-image-download {{
      display: inline-flex;
      align-items: center;
    }}
    .admin-screen-modal {{
      place-items: stretch;
      padding: 0;
      background: #02080b;
    }}
    .admin-screen-modal.is-open {{
      display: block;
    }}
    .admin-screen-card {{
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      display: block;
      border: 0;
      border-radius: 0;
      background: #02080b;
      box-shadow: none;
      overflow: hidden;
    }}
    .admin-screen-card .admin-chat-head {{
      position: fixed;
      top: 14px;
      left: 14px;
      right: 14px;
      z-index: 6;
      padding: 0;
      border: 0;
      pointer-events: none;
    }}
    .admin-screen-card .admin-chat-head > span {{
      min-height: 36px;
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(104, 243, 226, 0.24);
      border-radius: 999px;
      padding: 0 13px;
      color: rgba(241, 253, 255, 0.92);
      background: rgba(1, 8, 12, 0.62);
      box-shadow: 0 14px 34px rgba(0, 0, 0, 0.34);
      backdrop-filter: blur(12px);
      font-size: 12px;
      font-weight: 950;
      pointer-events: auto;
    }}
    .admin-screen-head-tools {{
      position: fixed;
      right: 14px;
      bottom: 14px;
      z-index: 7;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      pointer-events: auto;
    }}
    .admin-screen-head-tools .notice-save,
    .admin-screen-head-tools .pending-action {{
      min-height: 34px;
      border-radius: 999px;
      border: 1px solid rgba(228, 255, 249, 0.86);
      padding: 0 12px;
      color: #031014;
      background: linear-gradient(135deg, rgba(240, 255, 252, 0.96), rgba(112, 255, 230, 0.9));
      box-shadow:
        0 12px 30px rgba(0, 0, 0, 0.34),
        0 0 0 1px rgba(10, 30, 34, 0.28),
        0 0 22px rgba(104, 243, 226, 0.28);
      backdrop-filter: blur(10px);
      font-size: 11px;
      font-weight: 950;
      text-shadow: none;
    }}
    .admin-screen-head-tools .pending-action.reject {{
      border-color: rgba(255, 223, 230, 0.92);
      color: #24070c;
      background: linear-gradient(135deg, rgba(255, 247, 249, 0.98), rgba(255, 130, 154, 0.92));
      box-shadow:
        0 12px 30px rgba(0, 0, 0, 0.34),
        0 0 20px rgba(255, 112, 142, 0.28);
    }}
    .admin-screen-head-tools .notice-save:hover,
    .admin-screen-head-tools .notice-save:focus-visible,
    .admin-screen-head-tools .pending-action:hover,
    .admin-screen-head-tools .pending-action:focus-visible {{
      transform: translateY(-1px);
      filter: brightness(1.05);
    }}
    .admin-screen-view {{
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      min-width: 100vw;
      min-height: 100vh;
      display: block;
      margin: 0;
      border: 0;
      border-radius: 0;
      background:
        linear-gradient(90deg, rgba(104, 243, 226, 0.05) 1px, transparent 1px),
        linear-gradient(0deg, rgba(104, 243, 226, 0.05) 1px, transparent 1px),
        #02080b;
      background-size: 24px 24px;
      overflow: hidden;
      cursor: crosshair;
      touch-action: none;
    }}
    .admin-screen-view video,
    .admin-screen-view img {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      max-width: 100%;
      max-height: 100%;
      display: block;
      object-fit: contain;
      border-radius: 0;
      box-shadow: none;
      background: #02080b;
    }}
    .admin-screen-view img {{
      display: none;
    }}
    .admin-screen-card:fullscreen {{
      width: 100vw;
      height: 100vh;
      border-radius: 0;
    }}
    .admin-screen-card:fullscreen .admin-screen-view {{
      max-height: none;
      height: 100vh;
    }}
    .admin-screen-card:fullscreen .admin-screen-view video,
    .admin-screen-card:fullscreen .admin-screen-view img {{
      max-height: 100vh;
    }}
    .admin-screen-status {{
      position: fixed;
      left: 14px;
      bottom: 14px;
      z-index: 6;
      max-width: min(720px, calc(100vw - 28px));
      min-height: 30px;
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(104, 243, 226, 0.2);
      border-radius: 999px;
      padding: 0 12px;
      color: rgba(204, 234, 236, 0.9);
      background: rgba(1, 8, 12, 0.58);
      box-shadow: 0 14px 34px rgba(0, 0, 0, 0.34);
      backdrop-filter: blur(12px);
      font-size: 12px;
      font-weight: 850;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    html.admin-paint-performance-mode body > :not(.admin-paint-modal),
    html.admin-paint-performance-mode body > :not(.admin-paint-modal) *,
    html.admin-paint-performance-mode body > :not(.admin-paint-modal) *::before,
    html.admin-paint-performance-mode body > :not(.admin-paint-modal) *::after {{
      animation-play-state: paused !important;
      transition: none !important;
      scroll-behavior: auto !important;
      will-change: auto !important;
    }}
    html.admin-paint-performance-mode .admin-paint-modal,
    html.admin-paint-performance-mode .admin-paint-modal *,
    html.admin-paint-performance-mode .admin-paint-modal *::before,
    html.admin-paint-performance-mode .admin-paint-modal *::after {{
      animation-play-state: running !important;
    }}
    .admin-paint-card {{
      width: min(980px, calc(100vw - 28px));
      height: min(760px, calc(100vh - 28px));
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr) auto;
    }}
    .admin-paint-card:fullscreen {{
      width: 100vw;
      height: 100vh;
      border-radius: 0;
    }}
    .admin-paint-tools {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid rgba(104, 243, 226, 0.16);
      align-items: center;
    }}
    .admin-paint-tool.is-active {{
      border-color: rgba(104, 243, 226, 0.72);
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
    }}
    .admin-paint-color,
    .admin-paint-size,
    .admin-paint-text {{
      min-height: 34px;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 11px;
      color: var(--text);
      background: rgba(1, 8, 12, 0.72);
      font: 850 12px/1.35 Inter, Segoe UI, system-ui, sans-serif;
    }}
    .admin-paint-color {{ width: 56px; }}
    .admin-paint-size {{ width: 142px; }}
    .admin-paint-text {{
      width: min(210px, 100%);
      flex: 1 1 160px;
      padding: 0 10px;
    }}
    .admin-paint-zoom-label {{
      min-height: 34px;
      display: inline-flex;
      align-items: center;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 11px;
      padding: 0 10px;
      color: #a2ffcb;
      background: rgba(104, 243, 226, 0.08);
      font-size: 12px;
      font-weight: 900;
    }}
    .admin-paint-stage {{
      position: relative;
      min-height: 0;
      display: grid;
      place-items: center;
      padding: 14px;
      background:
        linear-gradient(90deg, rgba(104, 243, 226, 0.045) 1px, transparent 1px),
        linear-gradient(0deg, rgba(104, 243, 226, 0.045) 1px, transparent 1px),
        rgba(1, 8, 12, 0.82);
      background-size: 20px 20px;
      overflow: auto;
    }}
    .admin-paint-canvas {{
      width: 100%;
      height: 100%;
      min-height: 0;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 14px;
      background:
        linear-gradient(rgba(15, 23, 42, 0.055) 1px, transparent 1px),
        linear-gradient(90deg, rgba(15, 23, 42, 0.055) 1px, transparent 1px),
        #f7fff9;
      background-size: 24px 24px;
      display: block;
      touch-action: none;
      cursor: crosshair;
    }}
    .admin-paint-remote-cursor {{
      position: absolute;
      z-index: 6;
      left: 0;
      top: 0;
      width: 1px;
      height: 1px;
      pointer-events: none;
      opacity: 0;
      transform: translate3d(-9999px, -9999px, 0);
      transition: opacity 120ms ease, transform 80ms linear;
      color: var(--cyan);
      filter:
        drop-shadow(0 0 1px rgba(0, 0, 0, 0.9))
        drop-shadow(0 0 10px rgba(104, 243, 226, 0.82))
        drop-shadow(0 0 18px rgba(255, 209, 102, 0.42));
    }}
    .admin-paint-remote-cursor.is-visible {{ opacity: 1; }}
    .admin-paint-remote-cursor::before {{
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      width: 24px;
      height: 30px;
      clip-path: polygon(0 0, 0 26px, 7px 20px, 11px 30px, 17px 27px, 13px 18px, 24px 18px);
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(104, 243, 226, 0.86) 48%, rgba(255, 209, 102, 0.88));
      box-shadow:
        inset 0 0 0 1px rgba(2, 8, 12, 0.72),
        0 0 0 1px rgba(255, 255, 255, 0.82),
        0 0 18px rgba(104, 243, 226, 0.66);
    }}
    .admin-paint-remote-cursor::after {{
      content: "";
      position: absolute;
      left: -9px;
      top: -9px;
      width: 25px;
      height: 25px;
      border: 1px solid rgba(104, 243, 226, 0.68);
      border-radius: 999px;
      background:
        radial-gradient(circle, rgba(255, 255, 255, 0.55) 0 2px, transparent 3px),
        conic-gradient(from 80deg, transparent, rgba(255, 209, 102, 0.46), transparent 42%, rgba(104, 243, 226, 0.54), transparent 78%);
      animation: adminPaintRemoteCursorPulse 1600ms ease-in-out infinite;
    }}
    .admin-paint-remote-label {{
      position: absolute;
      left: 16px;
      top: 28px;
      min-width: 78px;
      max-width: 180px;
      padding: 5px 9px;
      border: 1px solid rgba(104, 243, 226, 0.74);
      border-radius: 999px;
      color: #f3fbff;
      background: linear-gradient(135deg, rgba(2, 8, 12, 0.9), rgba(5, 25, 31, 0.84));
      box-shadow:
        0 0 0 1px rgba(0, 0, 0, 0.72),
        0 0 16px rgba(104, 243, 226, 0.36);
      font-size: 11px;
      font-weight: 950;
      line-height: 1;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.88);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    @keyframes adminPaintRemoteCursorPulse {{
      0%, 100% {{ opacity: 0.62; transform: scale(0.82) rotate(0deg); }}
      50% {{ opacity: 1; transform: scale(1.08) rotate(18deg); }}
    }}
    .admin-paint-text-editor {{
      position: absolute;
      z-index: 3;
      min-width: 150px;
      min-height: 46px;
      max-width: min(420px, calc(100% - 28px));
      border: 2px solid rgba(255, 142, 72, 0.82);
      border-radius: 12px;
      padding: 8px 10px;
      color: #061115;
      background: rgba(247, 255, 249, 0.96);
      box-shadow: 0 18px 50px rgba(0, 0, 0, 0.32);
      resize: both;
      outline: none;
      font-family: Inter, Segoe UI, system-ui, sans-serif;
      font-weight: 900;
      line-height: 1.18;
    }}
    .admin-paint-status {{
      min-height: 18px;
      padding: 0 14px 14px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 850;
    }}
    .notice-editor {{
      display: grid;
      gap: 12px;
    }}
    .notice-input {{
      width: 100%;
      min-height: 124px;
      resize: vertical;
      border: 1px solid rgba(104, 243, 226, 0.28);
      border-radius: 16px;
      padding: 14px;
      color: var(--text);
      background:
        linear-gradient(90deg, rgba(104, 243, 226, 0.055) 1px, transparent 1px),
        rgba(1, 8, 12, 0.62);
      background-size: 18px 100%;
      outline: none;
      font: 800 14px/1.5 Inter, Segoe UI, system-ui, sans-serif;
      box-shadow: inset 0 0 22px rgba(104, 243, 226, 0.06);
    }}
    .notice-input:focus {{
      border-color: rgba(104, 243, 226, 0.62);
      box-shadow: 0 0 28px rgba(104, 243, 226, 0.12), inset 0 0 22px rgba(104, 243, 226, 0.08);
    }}
    .notice-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .notice-save {{
      min-height: 38px;
      border: 1px solid rgba(104, 243, 226, 0.38);
      border-radius: 12px;
      color: #061115;
      background: linear-gradient(135deg, var(--cyan), #a2ffcb);
      font-size: 12px;
      font-weight: 950;
      cursor: pointer;
    }}
    .notice-state {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 850;
    }}
    .qmdict-audio-progress {{
      grid-column: 1 / -1;
      display: grid;
      gap: 7px;
      padding: 10px 12px;
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 14px;
      background:
        linear-gradient(135deg, rgba(104, 243, 226, 0.08), rgba(162, 255, 203, 0.04)),
        rgba(1, 8, 12, 0.56);
      box-shadow: inset 0 0 18px rgba(104, 243, 226, 0.05);
    }}
    .qmdict-audio-progress[hidden] {{
      display: none;
    }}
    .qmdict-audio-bar {{
      position: relative;
      height: 9px;
      overflow: hidden;
      border-radius: 999px;
      border: 1px solid rgba(104, 243, 226, 0.34);
      background:
        linear-gradient(90deg, rgba(255,255,255,0.07) 1px, transparent 1px) 0 0 / 18px 100%,
        rgba(0, 0, 0, 0.28);
    }}
    .qmdict-audio-bar i {{
      position: absolute;
      inset: 0 auto 0 0;
      width: var(--qmdict-audio-progress, 0%);
      border-radius: inherit;
      background:
        linear-gradient(90deg, rgba(104, 243, 226, 0.16), rgba(104, 243, 226, 0.94), rgba(162, 255, 203, 0.92)),
        repeating-linear-gradient(115deg, rgba(255,255,255,0.24) 0 4px, transparent 4px 10px);
      box-shadow: 0 0 20px rgba(104, 243, 226, 0.36);
      transition: width 180ms linear;
    }}
    .qmdict-audio-progress.is-running .qmdict-audio-bar i::after {{
      content: "";
      position: absolute;
      top: -6px;
      right: -12px;
      width: 24px;
      height: 20px;
      border-radius: 50%;
      background: radial-gradient(circle, #fff 0 2px, rgba(162,255,203,0.9) 3px, rgba(104,243,226,0.36) 9px, transparent 70%);
      animation: qmdictAudioPulse 0.9s ease-in-out infinite;
    }}
    .qmdict-audio-copy {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 850;
      overflow-wrap: anywhere;
    }}
    @keyframes qmdictAudioPulse {{
      0%, 100% {{ opacity: 0.48; transform: scale(0.82); }}
      50% {{ opacity: 1; transform: scale(1.2); }}
    }}
    .notice-preview {{
      display: grid;
      gap: 8px;
      padding: 10px;
      border: 1px solid rgba(104, 243, 226, 0.14);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.035);
    }}
    .notice-preview-line {{
      padding: 8px 10px;
      border-left: 2px solid rgba(104, 243, 226, 0.62);
      border-radius: 10px;
      color: var(--text);
      background: linear-gradient(90deg, rgba(104, 243, 226, 0.09), transparent);
      font-size: 13px;
      line-height: 1.45;
      font-weight: 850;
    }}
    .setting-editor {{
      display: grid;
      gap: 12px;
    }}
    .setting-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(260px, 340px);
      gap: 12px;
      align-items: end;
    }}
    .setting-copy {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      font-weight: 750;
    }}
    .setting-input {{
      width: 100%;
      min-height: 46px;
      border: 1px solid rgba(104, 243, 226, 0.32);
      border-radius: 14px;
      padding: 0 12px;
      color: var(--text);
      background: rgba(1, 8, 12, 0.68);
      outline: none;
      font: 950 18px/1 Inter, Segoe UI, system-ui, sans-serif;
      text-align: center;
      box-shadow: inset 0 0 18px rgba(104, 243, 226, 0.06);
    }}
    .setting-input:focus {{
      border-color: rgba(104, 243, 226, 0.64);
      box-shadow: 0 0 28px rgba(104, 243, 226, 0.12), inset 0 0 18px rgba(104, 243, 226, 0.08);
    }}
    .cpu-guard-control {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
      gap: 8px;
      align-items: stretch;
    }}
    .setting-row > .notice-state,
    .setting-row > .qmdict-audio-progress {{
      grid-column: 1 / -1;
    }}
    .setting-row > .notice-input,
    .setting-row > .setting-input,
    .setting-row > .cpu-guard-control {{
      min-width: 0;
      width: 100%;
    }}
    .setting-row > .notice-input {{
      min-height: 86px;
    }}
    .worker-capacity-row {{
      grid-template-columns: minmax(0, 1fr);
      gap: 10px;
      align-items: stretch;
    }}
    .worker-capacity-row .cpu-guard-control {{
      width: 100%;
      min-width: 0;
      grid-template-columns: repeat(4, minmax(72px, 96px)) minmax(150px, 190px);
      justify-content: end;
      align-items: stretch;
    }}
    .worker-limit-field {{
      min-width: 0;
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 950;
      text-align: center;
      text-transform: uppercase;
    }}
    .worker-limit-field span {{
      min-height: 14px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .worker-limit-help {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      font-weight: 800;
      overflow-wrap: anywhere;
    }}
    .worker-capacity-row .setting-input,
    .worker-capacity-row .notice-save {{
      min-width: 0;
    }}
    #distributed-worker-command {{
      display: block;
      max-width: 100%;
      white-space: normal;
      overflow-wrap: anywhere;
      word-break: normal;
    }}
    .cpu-guard-toggle {{
      position: relative;
      overflow: hidden;
      min-height: 46px;
      color: #061115;
      background:
        linear-gradient(135deg, rgba(104, 243, 226, 0.94), rgba(162, 255, 203, 0.96));
      box-shadow:
        0 0 0 1px rgba(255, 255, 255, 0.16) inset,
        0 0 22px rgba(104, 243, 226, 0.22);
    }}
    .cpu-guard-toggle::after {{
      content: "";
      position: absolute;
      inset: 4px;
      border: 1px solid rgba(2, 8, 12, 0.28);
      clip-path: polygon(0 0, 86% 0, 100% 42%, 100% 100%, 14% 100%, 0 58%);
      pointer-events: none;
    }}
    .cpu-guard-toggle.is-off {{
      color: #ffd9c2;
      background:
        linear-gradient(135deg, rgba(25, 10, 8, 0.98), rgba(92, 28, 18, 0.92));
      box-shadow:
        0 0 0 1px rgba(255, 142, 72, 0.24) inset,
        0 0 22px rgba(255, 142, 72, 0.18);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      padding: 22px;
    }}
    .card {{
      border: 1px solid rgba(104, 243, 226, 0.18);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.045);
      padding: 16px;
      min-height: 94px;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }}
    .value {{
      margin-top: 10px;
      word-break: break-word;
      font-size: 15px;
      line-height: 1.45;
      font-weight: 800;
    }}
    .wide {{ grid-column: 1 / -1; }}
    code {{
      color: var(--cyan);
      font-family: Consolas, ui-monospace, monospace;
      font-size: 13px;
    }}
    .pulse {{
      width: 12px;
      height: 12px;
      display: inline-block;
      margin-right: 8px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 0 rgba(104, 243, 226, 0.4);
      animation: none;
      vertical-align: -1px;
    }}
    .pill.is-busy .pulse,
    .pill.error .pulse {{
      animation: pulse 1.3s infinite;
    }}
    @keyframes pulse {{
      0% {{ box-shadow: 0 0 0 0 rgba(104, 243, 226, 0.42); }}
      70% {{ box-shadow: 0 0 0 12px rgba(104, 243, 226, 0); }}
      100% {{ box-shadow: 0 0 0 0 rgba(104, 243, 226, 0); }}
    }}
    @media (max-width: 640px) {{
      body {{ padding: 14px; }}
      .top {{ padding: 22px; }}
      .grid {{ grid-template-columns: 1fr; padding: 16px; }}
      .gmail-panel {{ padding: 14px; }}
      .gmail-topbar {{ align-items: stretch; flex-direction: column; }}
      .gmail-address-line,
      .gmail-config-strip,
      .gmail-layout {{ grid-template-columns: 1fr; }}
      .gmail-at {{ display: none; }}
      .gmail-table-head {{ display: none; }}
      .gmail-message-row {{ grid-template-columns: 64px minmax(0, 1fr) 72px; }}
      .gmail-message-row .gmail-action {{ display: none; }}
      .dashboard-log-panel {{ padding: 16px; }}
      .dashboard-log-toolbar,
      .dashboard-log-row {{ grid-template-columns: 1fr; }}
      .dashboard-log-row.worker-row {{ grid-template-columns: 1fr; padding-right: 12px; }}
      .worker-capacity-row .cpu-guard-control {{ grid-template-columns: repeat(2, minmax(72px, 1fr)); justify-content: stretch; }}
      .worker-capacity-row .cpu-guard-apply {{ grid-column: 1 / -1; }}
      .setting-row {{ grid-template-columns: 1fr; }}
      .online-users {{ padding: 16px; }}
      .online-actions {{ justify-content: flex-start; flex: 1 1 100%; }}
      .online-actions .pending-action {{ flex: 1 1 104px; }}
      .online-actions .admin-password-input {{ flex: 1 1 132px; width: auto; max-width: 180px; }}
      .online-details {{ grid-template-columns: 1fr; }}
      .online-screen-preview {{ width: 100%; justify-self: stretch; }}
      .online-screen-preview-note {{ grid-column: auto; justify-self: start; }}
      .reward-settings-grid {{ grid-template-columns: 1fr; }}
      .reward-settings-row {{ grid-template-columns: 1fr 1fr; }}
      .admin-chat-row {{ grid-template-columns: 1fr; }}
      .admin-chat-audio-toggle {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="top">
      <div>
        <h1>Future Whisper</h1>
        <p class="sub">Live server dashboard for Future learning, voice scoring, chat, screen, and stream tools.</p>
        <div class="actions">
          <button class="action" id="kill-other-servers" type="button">Kill old Future servers</button>
          <button class="action is-danger" id="clean-close-all-runtime" type="button">Close server + tunnel</button>
          <button class="action" id="frontend-update-clients" type="button">Update clients</button>
          <button class="action" id="dashboard-close-server" type="button">Close server</button>
        </div>
      </div>
      <div class="dashboard-status-stack">
        <div class="dashboard-freshness" id="dashboard-freshness">NEW | 60s</div>
        <div class="pill" id="status"><span class="pulse"></span>Checking</div>
        <div class="dashboard-warm-log" id="dashboard-warm-log">Warm queue starting...</div>
      </div>
    </section>
    <nav class="tabs" aria-label="Server tabs">
      <button class="tab is-active" id="tab-main" type="button">Server</button>
      <button class="tab" id="tab-users" type="button">Online users <span class="chat-badge is-empty" id="tab-chat-badge">0</span></button>
      <button class="tab" id="tab-login-log" type="button">Login log</button>
      <button class="tab" id="tab-learning-log" type="button">Learning log</button>
      <button class="tab" id="tab-admins" type="button">Admins</button>
      <button class="tab" id="tab-password-reset" type="button">Password resets <span class="chat-badge is-empty" id="tab-password-reset-badge">0</span></button>
      <button class="tab" id="tab-security" type="button">Security <span class="chat-badge is-empty" id="tab-security-badge">!</span></button>
      <button class="tab" id="tab-email-routing" type="button">Gmail</button>
      <button class="tab" id="tab-workers" type="button">Workers</button>
      <button class="tab" id="tab-rewards" type="button">Top rewards</button>
      <button class="tab" id="tab-qm-city" type="button">QM-City</button>
      <button class="tab" id="tab-qm-city-npc" type="button">QM-City NPC</button>
      <button class="tab" id="tab-qm-city-levels" type="button">QM-City levels</button>
    </nav>
    <section class="grid tab-panel" id="panel-main">
      <div class="card">
        <div class="label">Model</div>
        <div class="value" id="model">small</div>
      </div>
      <div class="card">
        <div class="label">Language</div>
        <div class="value" id="language">en</div>
      </div>
      <div class="card wide">
        <div class="label">Model path</div>
        <div class="value" id="model-ref">Loading...</div>
      </div>
      <div class="card wide">
        <div class="label">Public learning link</div>
        <div class="value"><code id="public-url">Building Cloudflare Tunnel...</code></div>
        <button class="copy" id="copy-public" type="button">Copy learning link</button>
      </div>
      <div class="card">
        <div class="label">Endpoint</div>
        <div class="value"><code id="endpoint"></code></div>
      </div>
      <div class="card">
        <div class="label">Queue</div>
        <div class="value" id="queue-status">0 waiting</div>
      </div>
      <div class="card">
        <div class="label">Jobs</div>
        <div class="value" id="queue-jobs">0 done / 0 failed</div>
      </div>
      <div class="card">
        <div class="label">CPU guard</div>
        <div class="value" id="cpu-guard-status">Loading...</div>
      </div>
      <div class="card wide">
        <div class="label">Learning activity</div>
        <div class="value" id="learning-event">No completed lesson yet.</div>
      </div>
      <div class="card">
        <div class="label">Uptime</div>
        <div class="value" id="uptime">0s</div>
      </div>
      <div class="card wide">
        <div class="label">Server message</div>
        <div class="value" id="message">Server is starting...</div>
      </div>
      <div class="card wide">
        <div class="label">Mic receive mode</div>
        <div class="stream-audio-mode" id="admin-stream-audio-mode">
          <button class="stream-mode-button" type="button" data-admin-stream-mode="relay">Relay</button>
          <button class="stream-mode-button" type="button" data-admin-stream-mode="inbound">Inbound</button>
        </div>
        <div class="stream-mode-note" id="admin-stream-mode-note">Relay: user mic goes through server. Inbound: direct WebRTC track.</div>
      </div>
      <div class="card wide">
        <div class="label">AI System login feed</div>
        <div class="notice-editor">
          <textarea class="notice-input" id="announcement-input" maxlength="1400" spellcheck="false" placeholder="Enter one announcement per line. Example: Class starts at 19:30 today."></textarea>
          <div class="notice-actions">
            <button class="notice-save" id="announcement-save" type="button">Save announcements</button>
            <span class="notice-state" id="announcement-state">Loading announcements...</span>
          </div>
          <div class="notice-preview" id="announcement-preview"></div>
        </div>
      </div>
      <div class="card wide">
        <div class="label">Learning settings</div>
        <div class="setting-editor">
          <div class="setting-row">
            <div class="setting-copy">
              Word scoring hint orbit duration. The hologram clock reveals the next word after one full cycle.
            </div>
            <input class="setting-input" id="hint-cycle-input" type="number" min="5" max="180" step="1" value="30" aria-label="Hint orbit seconds">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Space_P auto hint duration. Paragraph Rewrite reveals the next hidden token after this timer.
            </div>
            <input class="setting-input" id="paragraph-hint-input" type="number" min="3" max="300" step="1" value="30" aria-label="Space_P hint seconds">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Question Root hologram globe lines. One English HUD line per row, maximum 4 lines.
            </div>
            <textarea class="notice-input" id="question-hud-input" maxlength="420" spellcheck="false" placeholder="MISSION NODE ONLINE&#10;ORBITAL MEMORY LINK&#10;QUESTION SIGNAL READY"></textarea>
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Chat attachment limit per user. When a conversation exceeds this total, old images and files are pruned.
            </div>
            <input class="setting-input" id="chat-attachment-limit-input" type="number" min="1" max="4096" step="10" value="100" aria-label="Chat attachment limit MB">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Heavy action quota per user. Applies to translate, OCR, TTS, Gemini, and Ghost Eye actions only; admin, builders, and workers are exempt.
            </div>
            <input class="setting-input" id="heavy-user-quota-input" type="number" min="1" max="120" step="1" value="5" aria-label="Heavy action quota per minute">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Minimum seconds between heavy actions for the same user and job group. Real users get a retry message, not a logout.
            </div>
            <input class="setting-input" id="heavy-user-interval-input" type="number" min="0" max="60" step="1" value="5" aria-label="Heavy action interval seconds">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              AI Agent notice voice. Detailed mode only speaks one short signal sentence with this voice to keep the server light.
            </div>
            <input class="setting-input" id="ai-agent-notice-voice-input" type="text" maxlength="160" spellcheck="false" value="kokoro:am_michael" aria-label="AI Agent notice voice">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Space_W Speak scoring source. On allows users to choose server Whisper or browser check; Off forces browser live voice check for everyone.
            </div>
            <div class="cpu-guard-control">
              <button class="notice-save cpu-guard-toggle is-on" id="space-w-ai-check-toggle" type="button" aria-pressed="true">Whisper On</button>
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Leaderboard reaction icons. One reaction per line. Use label|icon so the top status bubble can open exactly this reaction set.
            </div>
            <textarea class="notice-input" id="leaderboard-reactions-input" maxlength="520" spellcheck="false" placeholder="Love|💕⃝&#10;Fire heart|❤️‍🔥&#10;Mischief|😈&#10;Cool|🥶"></textarea>
          </div>
          <div class="setting-row cpu-guard-row">
            <div class="setting-copy">
              Adaptive CPU guard. Heavy jobs keep running normally until CPU reaches this threshold, then the server queues them to protect light requests.
            </div>
            <div class="cpu-guard-control">
              <input class="setting-input" id="cpu-threshold-input" type="number" min="45" max="98" step="1" value="90" aria-label="CPU queue threshold percent">
              <button class="notice-save cpu-guard-toggle is-on" id="cpu-guard-toggle" type="button" aria-pressed="true">CPU Guard On</button>
              <button class="notice-save cpu-guard-apply" id="cpu-guard-apply" type="button">Apply Limit</button>
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              QmDict UK/US word audio. Re-download Sound of Text audio for every word in QmDict and overwrite broken UK/US files.
            </div>
            <div class="cpu-guard-control">
              <button class="notice-save cpu-guard-apply" id="qmdict-word-audio-refresh" type="button">Refresh QmDict UK/US Audio</button>
              <button class="notice-save cpu-guard-apply" id="qmdict-meaning-audio-refresh" type="button">Refresh Vietnamese SOT Audio</button>
              <button class="notice-save cpu-guard-apply" id="qmdict-word-audio-retry" type="button">Retry Failed Audio</button>
              <button class="notice-save cpu-guard-apply" id="qmdict-reload" type="button">Reload QmDict</button>
            </div>
            <span class="notice-state" id="qmdict-reload-state">QmDict status is idle.</span>
            <div class="qmdict-audio-progress" id="qmdict-audio-progress" hidden>
              <span class="qmdict-audio-bar"><i id="qmdict-audio-progress-fill"></i></span>
              <span class="qmdict-audio-copy" id="qmdict-audio-progress-copy">Vietnamese audio refresh is idle.</span>
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Lesson Vault manifest. Reload the cached server-data tree after adding, moving, or deleting files in C:\\server data.
            </div>
            <div class="cpu-guard-control">
              <button class="notice-save cpu-guard-apply" id="server-data-manifest-refresh" type="button">Refresh Manifest</button>
            </div>
            <span class="notice-state" id="server-data-manifest-state">Manifest refresh is idle.</span>
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Cloudflare Tunnel public domain. Example: qm-tech.io.vn. When saved, the server creates or updates the DNS route for this hostname.
            </div>
            <input class="setting-input" id="cloudflare-hostname-input" type="text" maxlength="253" spellcheck="false" placeholder="qm-tech.io.vn" aria-label="Cloudflare public domain">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Cloudflare named tunnel. Keep this stable so the domain always points to the same tunnel.
            </div>
            <input class="setting-input" id="cloudflare-tunnel-name-input" type="text" maxlength="80" spellcheck="false" value="future-whisper" aria-label="Cloudflare tunnel name">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Hosted client obfuscation password. Leave blank to keep the current key; changing it rebuilds the hosted HTML cache.
            </div>
            <input class="setting-input" id="hosted-client-secret-input" type="password" maxlength="96" autocomplete="new-password" placeholder="New obfuscation password" aria-label="Hosted client obfuscation password">
          </div>
          <div class="notice-actions">
            <button class="notice-save" id="settings-save" type="button">Save settings</button>
            <span class="notice-state" id="settings-state">Loading settings...</span>
          </div>
        </div>
      </div>
      <div class="card wide">
        <div class="label">Pending registrations</div>
        <div class="value pending-list" id="pending-users">Checking...</div>
      </div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-password-reset" hidden>
      <div class="card wide">
        <div class="label">Password reset requests</div>
        <div class="setting-copy">User requests appear here for admin approval. Set a new password or reject the request.</div>
      </div>
      <div class="value pending-list" id="password-reset-users">Checking...</div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-security" hidden>
      <div class="card wide">
        <div class="label">Security / poll pressure</div>
        <div class="setting-copy">Light RAM-only poll pressure and block alerts. Use Block 10m only when one user or IP is clearly flooding.</div>
      </div>
      <div class="dashboard-log-list" id="security-poll-list">No poll pressure detected.</div>
    </section>
    <section class="online-users tab-panel" id="panel-users" hidden>
      <div class="card wide">
        <div class="label">Online users</div>
        <div class="value" id="online-users">Checking...</div>
      </div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-login-log" hidden>
      <div class="card wide">
        <div class="label">Login history</div>
        <div class="dashboard-log-toolbar">
          <input class="dashboard-log-input" id="login-log-date" type="date" aria-label="Login log date">
          <input class="dashboard-log-input" id="login-log-search" type="search" placeholder="Search user or device..." aria-label="Search login log">
          <button class="notice-save" id="login-log-refresh" type="button">Refresh</button>
        </div>
      </div>
      <div class="dashboard-log-list" id="login-log-list">Choose a date or search to load login history.</div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-learning-log" hidden>
      <div class="card wide">
        <div class="label">Completed lessons</div>
        <div class="dashboard-log-toolbar">
          <input class="dashboard-log-input" id="learning-log-date" type="date" aria-label="Learning log date">
          <input class="dashboard-log-input" id="learning-log-search" type="search" placeholder="Search user, file, or title..." aria-label="Search learning log">
          <button class="notice-save" id="learning-log-refresh" type="button">Refresh</button>
        </div>
      </div>
      <div class="dashboard-log-list" id="learning-log-list">Choose a date or search to load completed lessons.</div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-admins" hidden>
      <div class="card wide">
        <div class="label">Admin access</div>
        <div class="setting-copy">Admin users can browse common lessons and every user's server-data folder. Their study runs are recorded separately as admin runs.</div>
        <div class="dashboard-log-toolbar">
          <input class="dashboard-log-input" id="admin-user-search" type="search" placeholder="Search username, name, or data..." aria-label="Search admin users">
        </div>
      </div>
      <div class="dashboard-log-list" id="admin-user-list">Loading admin users...</div>
    </section>
    <section class="gmail-panel tab-panel" id="panel-email-routing" hidden>
      <div class="gmail-mailbox">
        <div class="gmail-topbar">
          <div>
            <div class="gmail-title">Future Gmail</div>
            <div class="gmail-subtitle">Secure domain inbox for OTP and routed messages</div>
          </div>
          <div class="gmail-status" id="email-routing-state">Connecting...</div>
        </div>
        <div class="gmail-readiness" id="email-routing-readiness">
          <div class="gmail-ready-summary">
            <span class="gmail-ready-badge" id="email-routing-ready-badge">Checking</span>
            <div>
              <div class="gmail-ready-title" id="email-routing-ready-title">Checking mail setup</div>
              <div class="gmail-ready-copy" id="email-routing-ready-copy">Future is checking Cloudflare MX, public webhook, and inbox state.</div>
            </div>
          </div>
          <div class="gmail-ready-grid">
            <div class="gmail-ready-card" id="email-routing-ready-mx-card">
              <span>Cloudflare MX</span>
              <strong id="email-routing-ready-mx">Checking</strong>
              <small id="email-routing-ready-mx-detail">DNS lookup pending</small>
            </div>
            <div class="gmail-ready-card" id="email-routing-ready-webhook-card">
              <span>Future Webhook</span>
              <strong id="email-routing-ready-webhook">Checking</strong>
              <small id="email-routing-ready-webhook-detail">Secret and public endpoint</small>
            </div>
            <div class="gmail-ready-card" id="email-routing-ready-worker-card">
              <span>Worker Route</span>
              <strong id="email-routing-ready-worker">Manual</strong>
              <small id="email-routing-ready-worker-detail">Send to Worker must stay Active</small>
            </div>
            <div class="gmail-ready-card" id="email-routing-ready-inbox-card">
              <span>Inbox</span>
              <strong id="email-routing-ready-inbox">0 messages</strong>
              <small id="email-routing-ready-inbox-detail">Waiting for incoming mail</small>
            </div>
          </div>
        </div>
        <div class="gmail-address-card">
          <div class="gmail-address-line">
            <input class="gmail-local-input" id="email-routing-alias-input" type="text" maxlength="90" spellcheck="false" placeholder="admin" aria-label="Gmail alias">
            <span class="gmail-at">@</span>
            <input class="gmail-domain-input" id="email-routing-domain-input" type="text" maxlength="253" spellcheck="false" placeholder="qm-tech.io.vn" aria-label="Gmail routing domain">
          </div>
          <div class="gmail-preview-row">
            <code id="email-routing-current-address">admin@qm-tech.io.vn</code>
            <button class="notice-save" id="email-routing-random" type="button">Random</button>
            <button class="notice-save" id="email-routing-copy" type="button">Copy</button>
            <button class="notice-save" id="email-routing-create-alias" type="button">Create mail</button>
            <button class="notice-save" id="email-routing-address-history" type="button">Received aliases</button>
            <button class="notice-save" id="email-routing-refresh" type="button">Refresh</button>
          </div>
          <div class="gmail-history-panel" id="email-routing-address-history-panel" hidden>
            <input class="gmail-history-search" id="email-routing-address-search" type="search" maxlength="90" spellcheck="false" placeholder="Search received aliases" aria-label="Search received aliases">
            <div class="gmail-history-list" id="email-routing-received-address-list"></div>
          </div>
          <div class="gmail-expiry">Future keeps the newest inbound messages in the server inbox.</div>
        </div>
        <div class="gmail-config-strip" hidden>
          <input class="setting-input" id="email-routing-default-destination-input" type="email" maxlength="90" spellcheck="false" placeholder="Forward Gmail destination" aria-label="Default Gmail destination">
          <input class="setting-input" id="email-routing-alias-destination-input" type="email" maxlength="90" spellcheck="false" placeholder="Alias forward destination" aria-label="Alias forward destination">
          <input class="setting-input" id="email-routing-alias-name-input" type="text" maxlength="256" spellcheck="false" placeholder="Rule name" aria-label="Alias rule name">
          <input class="setting-input" id="email-routing-account-id-input" type="text" maxlength="120" spellcheck="false" placeholder="Cloudflare Account ID" aria-label="Cloudflare Account ID">
          <input class="setting-input" id="email-routing-zone-id-input" type="text" maxlength="120" spellcheck="false" placeholder="Cloudflare Zone ID" aria-label="Cloudflare Zone ID">
          <input class="setting-input" id="email-routing-api-token-input" type="password" maxlength="512" autocomplete="new-password" placeholder="Cloudflare API token" aria-label="Cloudflare API token">
          <input class="setting-input" id="email-routing-inbound-secret-input" type="text" maxlength="160" spellcheck="false" placeholder="Webhook secret" aria-label="Gmail inbound webhook secret">
          <button class="notice-save" id="email-routing-save" type="button">Save settings</button>
          <button class="notice-save" id="email-routing-verify-destination" type="button">Verify Gmail</button>
          <button class="notice-save" id="email-routing-create-route" type="button">Create Cloudflare route</button>
          <button class="notice-save" id="email-routing-regenerate-secret" type="button">New secret</button>
          <button class="notice-save" id="email-routing-worker" type="button">Worker script</button>
          <button class="notice-save" id="email-routing-open-full" type="button">Full page</button>
        </div>
        <div class="gmail-alias-chips" id="email-routing-alias-list" hidden>Loading Gmail addresses...</div>
        <div class="gmail-layout">
          <section class="gmail-inbox">
            <div class="gmail-section-head">
              <span>Your Inbox</span>
              <span id="email-routing-message-count">0 emails</span>
            </div>
            <div class="gmail-table-head">
              <span>Time</span>
              <span>Sender</span>
              <span>OTP Code</span>
              <span>Action</span>
            </div>
            <div class="gmail-message-list" id="email-routing-message-list">Loading inbound messages...</div>
          </section>
          <section class="gmail-reader">
            <button class="gmail-back" id="email-routing-reader-back" type="button">Back</button>
            <div class="gmail-reader-subject" id="email-routing-reader-subject">Subject</div>
            <div class="gmail-reader-meta">
              <span id="email-routing-reader-sender">Sender</span>
              <span id="email-routing-reader-time">Time</span>
            </div>
            <div class="gmail-reader-code">
              <span>Verification Code</span>
              <strong id="email-routing-reader-code">-</strong>
            </div>
            <pre class="gmail-reader-body" id="email-routing-reader-body">Select an email to read it.</pre>
          </section>
        </div>
      </div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-rewards" hidden>
      <div class="card wide">
        <div class="label">Leaderboard reward settings</div>
        <div class="setting-copy">Set rare first-learn crystals and easy review crystals for the leaderboard reward chamber. Rank #1 receives the badge; ranks #2 and #3 receive fewer crystals without a badge.</div>
      </div>
      <div class="reward-settings-grid" id="reward-settings-grid">Loading reward settings...</div>
      <div class="card wide">
        <div class="notice-actions">
          <button class="notice-save" id="reward-settings-save" type="button">Save reward settings</button>
          <button class="notice-save" id="leaderboard-reset-day" type="button">Reset day top</button>
          <button class="notice-save" id="leaderboard-reset-week" type="button">Reset week top</button>
          <button class="notice-save" id="leaderboard-reset-month" type="button">Reset month top</button>
          <button class="notice-save" id="space-leaderboard-reset-today-test" type="button">Reset Space Top Today test</button>
          <span class="notice-state" id="reward-settings-state">Loading rewards...</span>
        </div>
      </div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-workers" hidden>
      <div class="card wide">
        <div class="label">Distributed workers</div>
        <div class="setting-copy">Remote machines can help this server with Translate, TTS, STT, and Gemini by polling for jobs over the public learning link.</div>
        <div class="notice-actions">
          <button class="notice-save" id="distributed-worker-copy-command" type="button">Copy command</button>
          <span class="notice-state" id="distributed-worker-state">Waiting for worker data...</span>
        </div>
        <div class="value"><code id="distributed-worker-command">Loading command...</code></div>
        <div class="setting-row worker-capacity-row">
          <div class="setting-copy">
            Worker capacity. The server shares work across online workers first and uses local processing only when these lanes are full.
          </div>
          <div class="cpu-guard-control">
            <label class="worker-limit-field" title="Maximum translation jobs the whole worker pool may run at the same time. Used by builders, notices, PDF/Picture translate, and lesson tools.">
              <span>Translate</span>
              <input class="setting-input" id="distributed-worker-limit-translate" type="number" min="0" max="64" step="1" value="4" aria-label="Translate worker jobs">
            </label>
            <label class="worker-limit-field" title="Maximum voice/TTS jobs the worker pool may run at the same time. Used by Space V/W/P/Q/S/L audio, Ghost AI voice, notices, and AI Question audio.">
              <span>Voice</span>
              <input class="setting-input" id="distributed-worker-limit-tts" type="number" min="0" max="64" step="1" value="4" aria-label="TTS worker jobs">
            </label>
            <label class="worker-limit-field" title="Maximum speech-to-text jobs the worker pool may run at the same time. Used by Whisper/STT pronunciation and speaking checks.">
              <span>STT</span>
              <input class="setting-input" id="distributed-worker-limit-stt" type="number" min="0" max="64" step="1" value="4" aria-label="STT worker jobs">
            </label>
            <label class="worker-limit-field" title="Maximum Gemini jobs the worker pool may run at the same time. Workers ask Server 2 for the key only when processing a Gemini job.">
              <span>Gemini</span>
              <input class="setting-input" id="distributed-worker-limit-gemini" type="number" min="0" max="64" step="1" value="4" aria-label="Gemini worker jobs">
            </label>
            <label class="worker-limit-field" title="Maximum IPA/phonemize jobs the worker pool may run at the same time. Used by Space builders for IPA and spaCy-assisted analysis.">
              <span>IPA</span>
              <input class="setting-input" id="distributed-worker-limit-phonemize" type="number" min="0" max="64" step="1" value="8" aria-label="IPA phonemize worker jobs">
            </label>
            <label class="worker-limit-field" title="Maximum FutureWorkerAuto instances that one client machine should run. Default is 2 to prevent runaway worker windows.">
              <span>Worker apps/machine</span>
              <input class="setting-input" id="distributed-worker-machine-limit" type="number" min="1" max="32" step="1" value="2" aria-label="Worker instances per machine">
            </label>
            <button class="notice-save cpu-guard-apply" id="distributed-worker-limit-save" type="button">Save worker limit</button>
          </div>
          <div class="worker-limit-help">
            Lane numbers are global pool limits. Keep worker apps per machine at 1; raise lanes to use more CPU without opening duplicate worker windows. If every matching worker lane is busy, Server 2 uses its local fallback so the request still completes.
          </div>
        </div>
      </div>
      <div class="card wide">
        <div class="label">Worker list</div>
        <div class="dashboard-log-list" id="distributed-worker-list">No workers connected.</div>
      </div>
      <div class="card wide">
        <div class="label">Worker logs</div>
        <button class="notice-save worker-log-toggle" id="distributed-worker-log-toggle" type="button">Hide worker logs</button>
        <div class="dashboard-log-list" id="distributed-worker-log-list">No worker logs yet.</div>
      </div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-qm-city" hidden>
      <div class="card wide">
        <div class="label">QM-City chat gate</div>
        <div class="setting-copy">Controls the English-only chat validator for the QM-City shared world. Messages with Vietnamese accents are always rejected.</div>
      </div>
      <div class="card wide">
        <div class="setting-editor">
          <div class="setting-row">
            <div class="setting-copy">
              Minimum valid English word ratio. Example: 50 means at least half of detected word tokens must be valid English vocabulary.
            </div>
            <input class="setting-input" id="qm-city-min-english-input" type="number" min="1" max="100" step="1" value="50" aria-label="QM-City minimum English percent">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Consecutive invalid token limit. Example: 4 rejects messages with four invalid word tokens in a row.
            </div>
            <input class="setting-input" id="qm-city-invalid-run-input" type="number" min="1" max="20" step="1" value="4" aria-label="QM-City invalid token run limit">
          </div>
          <div class="setting-row">
            <div class="setting-copy">
              Transformation skins. One skin per line: name|price|image path or URL|description. The shop uses Space_V vocabulary crystals as currency.
            </div>
            <textarea class="notice-input" id="qm-city-skins-input" maxlength="6000" spellcheck="false" placeholder="Slime|35||A soft crystal slime form.&#10;Cloud|45||A floating cloud spirit form."></textarea>
          </div>
          <div class="notice-actions">
            <button class="notice-save" id="qm-city-save" type="button">Save QM-City</button>
            <span class="notice-state" id="qm-city-state">Loading QM-City settings...</span>
          </div>
        </div>
      </div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-qm-city-npc" hidden>
      <div class="card wide">
        <div class="label">QM-City NPC racers</div>
        <div class="setting-copy">Controls QM-City background characters. Top racers come from <code>C:/server data/NPC_TOP</code>; city residents are 10 lightweight resident characters that keep the city alive when racers are off.</div>
      </div>
      <div class="card wide">
        <div class="setting-editor">
          <div class="setting-row">
            <div class="setting-copy">Choose city population mode. Off now means city residents only; racers already online leave gradually instead of vanishing together.</div>
            <button class="admin-chat-audio-toggle" id="qm-city-npc-enabled-toggle" type="button" aria-pressed="true">NPC city on</button>
            <button class="admin-chat-audio-toggle" id="qm-city-npc-mix-toggle" type="button" aria-pressed="false">Mix</button>
          </div>
          <div class="setting-row">
            <div class="setting-copy">Spawn chance percent when real users are in QM-City.</div>
            <input class="setting-input" id="qm-city-npc-spawn-chance-input" type="number" min="0" max="100" step="1" value="55" aria-label="NPC spawn chance percent">
          </div>
          <div class="setting-row">
            <div class="setting-copy">Active NPC range. The server keeps a random target inside this range when NPC spawning succeeds.</div>
            <div class="dashboard-log-toolbar">
              <input class="setting-input" id="qm-city-npc-min-active-input" type="number" min="0" max="5" step="1" value="1" aria-label="Minimum active NPCs">
              <input class="setting-input" id="qm-city-npc-max-active-input" type="number" min="1" max="8" step="1" value="5" aria-label="Maximum active NPCs">
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-copy">Online session duration in minutes. Each NPC leaves automatically after a random duration in this range.</div>
            <div class="dashboard-log-toolbar">
              <input class="setting-input" id="qm-city-npc-online-min-input" type="number" min="5" max="180" step="1" value="20" aria-label="NPC minimum online minutes">
              <input class="setting-input" id="qm-city-npc-online-max-input" type="number" min="5" max="240" step="1" value="40" aria-label="NPC maximum online minutes">
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-copy">Battle intelligence. First value is the chance NPC answers its own question correctly; second is chance NPC steals after the opponent misses.</div>
            <div class="dashboard-log-toolbar">
              <input class="setting-input" id="qm-city-npc-answer-input" type="number" min="0" max="100" step="1" value="58" aria-label="NPC answer correct percent">
              <input class="setting-input" id="qm-city-npc-steal-input" type="number" min="0" max="100" step="1" value="34" aria-label="NPC steal correct percent">
            </div>
          </div>
          <div class="setting-row">
            <div class="setting-copy">Random battle invite chance and cooldown. NPCs never spam the same moment; each active NPC rolls after its cooldown.</div>
            <div class="dashboard-log-toolbar">
              <input class="setting-input" id="qm-city-npc-invite-input" type="number" min="0" max="100" step="1" value="8" aria-label="NPC invite chance percent">
              <input class="setting-input" id="qm-city-npc-invite-min-input" type="number" min="15" max="900" step="1" value="70" aria-label="NPC minimum invite cooldown seconds">
              <input class="setting-input" id="qm-city-npc-invite-max-input" type="number" min="20" max="1200" step="1" value="180" aria-label="NPC maximum invite cooldown seconds">
            </div>
          </div>
          <div class="notice-actions">
            <button class="notice-save" id="qm-city-npc-save" type="button">Save NPC settings</button>
            <span class="notice-state" id="qm-city-npc-state">Loading NPC settings...</span>
          </div>
        </div>
      </div>
    </section>
    <section class="dashboard-log-panel tab-panel" id="panel-qm-city-levels" hidden>
      <div class="card wide">
        <div class="label">QM-City level curve</div>
        <div class="setting-copy">Each level uses total vocabulary EXP. EXP is measured from learned vocabulary count, so spending crystals does not reduce the character level.</div>
      </div>
      <div class="card wide">
        <div class="level-settings-list" id="qm-city-level-list">Loading levels...</div>
        <div class="notice-actions">
          <button class="notice-save" id="qm-city-level-add" type="button">Add level</button>
          <button class="notice-save" id="qm-city-level-save" type="button">Save levels</button>
          <span class="notice-state" id="qm-city-level-state">Loading levels...</span>
        </div>
      </div>
    </section>
  </main>
  <div class="admin-chat-modal" id="admin-chat-modal">
    <section class="admin-chat-card">
      <div class="admin-chat-head">
        <span id="admin-chat-title">Chat</span>
        <button class="pending-action reject" id="admin-chat-close" type="button">Close</button>
      </div>
      <div class="admin-chat-log" id="admin-chat-log"></div>
      <div class="admin-chat-compose">
        <div class="admin-chat-tools">
          <button class="notice-save admin-chat-translate" id="admin-chat-translate" type="button">Translate to English</button>
          <button class="admin-chat-attach" id="admin-chat-attach" type="button">Attach file</button>
          <button class="admin-chat-attach" id="admin-chat-mic" type="button">Mic</button>
          <select class="admin-chat-speech-mode" id="admin-chat-speech-mode" aria-label="Admin chat speech input mode" title="Speech input mode">
            <option value="browser">Browser VI+EN</option>
            <option value="zipformer">Zipformer VI</option>
          </select>
          <button class="admin-chat-attach" id="admin-chat-text-mic" type="button" aria-pressed="false">Text Mic</button>
          <button class="admin-chat-attach" id="admin-chat-voice-send" type="button" hidden>Send voice</button>
          <button class="admin-chat-attach" id="admin-chat-voice-cancel" type="button" hidden>Cancel</button>
          <input id="admin-chat-file" type="file" multiple hidden>
          <span class="admin-chat-small-note" id="admin-chat-voice-state">Loading voices...</span>
        </div>
        <div class="admin-chat-row">
          <select class="admin-chat-select" id="admin-chat-vi-voice" aria-label="Vietnamese voice"></select>
          <textarea class="notice-input admin-chat-input-vi" id="admin-chat-input" rows="2" maxlength="1200" placeholder="Vietnamese message..."></textarea>
          <button class="admin-chat-audio-toggle is-on" id="admin-chat-vi-audio-toggle" type="button" aria-pressed="true">VI audio on</button>
          <button class="notice-save" id="admin-chat-send" type="button">Send Vietnamese</button>
        </div>
        <div class="admin-chat-row">
          <select class="admin-chat-select" id="admin-chat-en-voice" aria-label="English voice"></select>
          <textarea class="notice-input admin-chat-input-en" id="admin-chat-en-input" rows="2" maxlength="1200" placeholder="English message..."></textarea>
          <button class="admin-chat-audio-toggle is-on" id="admin-chat-en-audio-toggle" type="button" aria-pressed="true">EN audio on</button>
          <button class="notice-save" id="admin-chat-en-send" type="button">Send English</button>
        </div>
      </div>
    </section>
  </div>
  <div class="admin-image-viewer" id="admin-image-viewer">
    <div class="admin-image-tools" aria-label="Image viewer tools">
      <button class="admin-image-zoom" id="admin-image-zoom-out" type="button">Zoom -</button>
      <button class="admin-image-zoom" id="admin-image-zoom-reset" type="button">100%</button>
      <button class="admin-image-zoom" id="admin-image-zoom-in" type="button">Zoom +</button>
      <a class="admin-image-download" id="admin-image-download" href="#" download>Download</a>
      <button class="admin-image-close" id="admin-image-close" type="button">Close</button>
    </div>
    <img id="admin-image-viewer-img" alt="">
  </div>
  <div class="admin-chat-modal admin-screen-modal" id="admin-screen-modal">
    <section class="admin-chat-card admin-screen-card" id="admin-screen-card">
      <div class="admin-chat-head">
        <span id="admin-screen-title">Screen preview</span>
        <div class="admin-screen-head-tools">
          <button class="notice-save" id="admin-screen-mic" type="button">Mic stream</button>
          <button class="notice-save" id="admin-screen-fullscreen" type="button">Fullscreen</button>
          <button class="pending-action reject" id="admin-screen-close" type="button">Close</button>
        </div>
      </div>
      <div class="admin-screen-view" id="admin-screen-view">
        <video id="admin-screen-video" autoplay playsinline muted></video>
        <img id="admin-screen-img" alt="User screen preview">
      </div>
      <div class="admin-screen-status" id="admin-screen-status">Waiting for user permission...</div>
    </section>
  </div>
  <div class="admin-chat-modal admin-paint-modal" id="admin-paint-modal">
    <section class="admin-chat-card admin-paint-card" id="admin-paint-card">
      <div class="admin-chat-head">
        <span id="admin-paint-title">Paint board</span>
        <button class="pending-action reject" id="admin-paint-close" type="button">Close</button>
      </div>
      <div class="admin-paint-tools" aria-label="Admin paint tools">
        <button class="pending-action admin-paint-tool" type="button" data-admin-paint-mode="select">Select</button>
        <button class="pending-action admin-paint-tool is-active" type="button" data-admin-paint-mode="pen">Pen</button>
        <button class="pending-action admin-paint-tool" type="button" data-admin-paint-mode="eraser">Eraser</button>
        <button class="pending-action admin-paint-tool" type="button" data-admin-paint-mode="text">Text</button>
        <button class="pending-action reject" id="admin-paint-clear" type="button">Clear</button>
        <input class="admin-paint-color" id="admin-paint-color" type="color" value="#0f172a" aria-label="Paint color">
        <input class="admin-paint-size" id="admin-paint-size" type="range" min="2" max="34" value="6" aria-label="Paint size">
        <input class="admin-paint-text" id="admin-paint-text" type="text" maxlength="160" placeholder="Text" aria-label="Paint text">
        <button class="pending-action" id="admin-paint-image" type="button">Picture</button>
        <button class="pending-action" id="admin-paint-paste" type="button">Paste</button>
        <button class="pending-action reject" id="admin-paint-delete" type="button">Delete</button>
        <button class="pending-action" id="admin-paint-zoom-out" type="button">Zoom -</button>
        <span class="admin-paint-zoom-label" id="admin-paint-zoom-label">100%</span>
        <button class="pending-action" id="admin-paint-zoom-in" type="button">Zoom +</button>
        <button class="pending-action" id="admin-paint-fullscreen" type="button">Full</button>
        <button class="pending-action" id="admin-paint-tab" type="button">New tab</button>
        <input id="admin-paint-image-file" type="file" accept="image/*" hidden>
      </div>
      <div class="admin-paint-stage">
        <canvas class="admin-paint-canvas" id="admin-paint-canvas" aria-label="Connected user paint board"></canvas>
      </div>
      <div class="admin-paint-status" id="admin-paint-status">Paint sync waiting.</div>
    </section>
  </div>
  <script>
    const statusNode = document.getElementById("status");
    const dashboardFreshnessNode = document.getElementById("dashboard-freshness");
    const dashboardWarmLogNode = document.getElementById("dashboard-warm-log");
    const modelNode = document.getElementById("model");
    const languageNode = document.getElementById("language");
    const modelRefNode = document.getElementById("model-ref");
    const publicUrlNode = document.getElementById("public-url");
    const copyPublicButton = document.getElementById("copy-public");
    const killOtherServersButton = document.getElementById("kill-other-servers");
    const cleanCloseAllRuntimeButton = document.getElementById("clean-close-all-runtime");
    const frontendUpdateClientsButton = document.getElementById("frontend-update-clients");
    const closeServerButton = document.getElementById("dashboard-close-server");
    const endpointNode = document.getElementById("endpoint");
    const queueStatusNode = document.getElementById("queue-status");
    const queueJobsNode = document.getElementById("queue-jobs");
    const cpuGuardStatusNode = document.getElementById("cpu-guard-status");
    const learningEventNode = document.getElementById("learning-event");
    const uptimeNode = document.getElementById("uptime");
    const messageNode = document.getElementById("message");
    const securityPollList = document.getElementById("security-poll-list");
    const adminStreamModeButtons = Array.from(document.querySelectorAll("[data-admin-stream-mode]"));
    const adminStreamModeNote = document.getElementById("admin-stream-mode-note");
    const pendingUsersNode = document.getElementById("pending-users");
    const passwordResetUsersNode = document.getElementById("password-reset-users");
    const announcementInput = document.getElementById("announcement-input");
    const announcementSave = document.getElementById("announcement-save");
    const announcementState = document.getElementById("announcement-state");
    const announcementPreview = document.getElementById("announcement-preview");
    const hintCycleInput = document.getElementById("hint-cycle-input");
    const paragraphHintInput = document.getElementById("paragraph-hint-input");
    const questionHudInput = document.getElementById("question-hud-input");
    const chatAttachmentLimitInput = document.getElementById("chat-attachment-limit-input");
    const heavyUserQuotaInput = document.getElementById("heavy-user-quota-input");
    const heavyUserIntervalInput = document.getElementById("heavy-user-interval-input");
    const aiAgentNoticeVoiceInput = document.getElementById("ai-agent-notice-voice-input");
    const spaceWAiCheckToggle = document.getElementById("space-w-ai-check-toggle");
    const leaderboardReactionsInput = document.getElementById("leaderboard-reactions-input");
    const cpuThresholdInput = document.getElementById("cpu-threshold-input");
    const cpuGuardToggle = document.getElementById("cpu-guard-toggle");
    const cpuGuardApply = document.getElementById("cpu-guard-apply");
    const qmdictReload = document.getElementById("qmdict-reload");
    const spaceVRepair = document.getElementById("space-v-repair");
    const qmdictWordAudioRefresh = document.getElementById("qmdict-word-audio-refresh");
    const qmdictMeaningAudioRefresh = document.getElementById("qmdict-meaning-audio-refresh");
    const qmdictWordAudioRetry = document.getElementById("qmdict-word-audio-retry");
    const qmdictReloadState = document.getElementById("qmdict-reload-state");
    const serverDataManifestRefresh = document.getElementById("server-data-manifest-refresh");
    const serverDataManifestState = document.getElementById("server-data-manifest-state");
    const qmdictAudioProgress = document.getElementById("qmdict-audio-progress");
    const qmdictAudioProgressFill = document.getElementById("qmdict-audio-progress-fill");
    const qmdictAudioProgressCopy = document.getElementById("qmdict-audio-progress-copy");
    const cloudflareHostnameInput = document.getElementById("cloudflare-hostname-input");
    const cloudflareTunnelNameInput = document.getElementById("cloudflare-tunnel-name-input");
    const hostedClientSecretInput = document.getElementById("hosted-client-secret-input");
    const settingsSave = document.getElementById("settings-save");
    const settingsState = document.getElementById("settings-state");
    const tabMain = document.getElementById("tab-main");
    const tabUsers = document.getElementById("tab-users");
    const tabLoginLog = document.getElementById("tab-login-log");
  const tabLearningLog = document.getElementById("tab-learning-log");
  const tabAdmins = document.getElementById("tab-admins");
  const tabPasswordReset = document.getElementById("tab-password-reset");
  const tabSecurity = document.getElementById("tab-security");
  const tabEmailRouting = document.getElementById("tab-email-routing");
    const tabWorkers = document.getElementById("tab-workers");
    const tabRewards = document.getElementById("tab-rewards");
    const tabQmCity = document.getElementById("tab-qm-city");
    const tabQmCityNpc = document.getElementById("tab-qm-city-npc");
    const tabQmCityLevels = document.getElementById("tab-qm-city-levels");
    const panelMain = document.getElementById("panel-main");
    const panelUsers = document.getElementById("panel-users");
    const panelLoginLog = document.getElementById("panel-login-log");
  const panelLearningLog = document.getElementById("panel-learning-log");
  const panelAdmins = document.getElementById("panel-admins");
  const panelPasswordReset = document.getElementById("panel-password-reset");
  const panelSecurity = document.getElementById("panel-security");
  const panelEmailRouting = document.getElementById("panel-email-routing");
    const panelWorkers = document.getElementById("panel-workers");
    const panelRewards = document.getElementById("panel-rewards");
    const panelQmCity = document.getElementById("panel-qm-city");
    const panelQmCityNpc = document.getElementById("panel-qm-city-npc");
    const panelQmCityLevels = document.getElementById("panel-qm-city-levels");
    const qmCityMinEnglishInput = document.getElementById("qm-city-min-english-input");
    const qmCityInvalidRunInput = document.getElementById("qm-city-invalid-run-input");
    const qmCitySkinsInput = document.getElementById("qm-city-skins-input");
    const qmCitySave = document.getElementById("qm-city-save");
    const qmCityState = document.getElementById("qm-city-state");
    const qmCityNpcEnabledToggle = document.getElementById("qm-city-npc-enabled-toggle");
    const qmCityNpcMixToggle = document.getElementById("qm-city-npc-mix-toggle");
    const qmCityNpcSpawnChanceInput = document.getElementById("qm-city-npc-spawn-chance-input");
    const qmCityNpcMinActiveInput = document.getElementById("qm-city-npc-min-active-input");
    const qmCityNpcMaxActiveInput = document.getElementById("qm-city-npc-max-active-input");
    const qmCityNpcOnlineMinInput = document.getElementById("qm-city-npc-online-min-input");
    const qmCityNpcOnlineMaxInput = document.getElementById("qm-city-npc-online-max-input");
    const qmCityNpcAnswerInput = document.getElementById("qm-city-npc-answer-input");
    const qmCityNpcStealInput = document.getElementById("qm-city-npc-steal-input");
    const qmCityNpcInviteInput = document.getElementById("qm-city-npc-invite-input");
    const qmCityNpcInviteMinInput = document.getElementById("qm-city-npc-invite-min-input");
    const qmCityNpcInviteMaxInput = document.getElementById("qm-city-npc-invite-max-input");
    const qmCityNpcSave = document.getElementById("qm-city-npc-save");
    const qmCityNpcState = document.getElementById("qm-city-npc-state");
    const qmCityLevelList = document.getElementById("qm-city-level-list");
    const qmCityLevelAdd = document.getElementById("qm-city-level-add");
    const qmCityLevelSave = document.getElementById("qm-city-level-save");
    const qmCityLevelState = document.getElementById("qm-city-level-state");
    const rewardSettingsGrid = document.getElementById("reward-settings-grid");
    const rewardSettingsSave = document.getElementById("reward-settings-save");
    const leaderboardResetDay = document.getElementById("leaderboard-reset-day");
    const leaderboardResetWeek = document.getElementById("leaderboard-reset-week");
    const leaderboardResetMonth = document.getElementById("leaderboard-reset-month");
    const spaceLeaderboardResetTodayTest = document.getElementById("space-leaderboard-reset-today-test");
    const rewardSettingsState = document.getElementById("reward-settings-state");
    const loginLogDate = document.getElementById("login-log-date");
    const loginLogSearch = document.getElementById("login-log-search");
    const loginLogRefresh = document.getElementById("login-log-refresh");
    const loginLogList = document.getElementById("login-log-list");
    const learningLogDate = document.getElementById("learning-log-date");
    const learningLogSearch = document.getElementById("learning-log-search");
  const learningLogRefresh = document.getElementById("learning-log-refresh");
  const learningLogList = document.getElementById("learning-log-list");
  const adminUserList = document.getElementById("admin-user-list");
  const adminUserSearch = document.getElementById("admin-user-search");
  const emailRoutingDomainInput = document.getElementById("email-routing-domain-input");
    const emailRoutingCurrentAddress = document.getElementById("email-routing-current-address");
    const emailRoutingRandom = document.getElementById("email-routing-random");
    const emailRoutingCopy = document.getElementById("email-routing-copy");
    const emailRoutingDefaultDestinationInput = document.getElementById("email-routing-default-destination-input");
    const emailRoutingAccountIdInput = document.getElementById("email-routing-account-id-input");
    const emailRoutingZoneIdInput = document.getElementById("email-routing-zone-id-input");
    const emailRoutingApiTokenInput = document.getElementById("email-routing-api-token-input");
    const emailRoutingInboundSecretInput = document.getElementById("email-routing-inbound-secret-input");
    const emailRoutingSave = document.getElementById("email-routing-save");
    const emailRoutingVerifyDestination = document.getElementById("email-routing-verify-destination");
    const emailRoutingRegenerateSecret = document.getElementById("email-routing-regenerate-secret");
    const emailRoutingRefresh = document.getElementById("email-routing-refresh");
    const emailRoutingWorker = document.getElementById("email-routing-worker");
    const emailRoutingOpenFull = document.getElementById("email-routing-open-full");
    const emailRoutingState = document.getElementById("email-routing-state");
    const emailRoutingAliasInput = document.getElementById("email-routing-alias-input");
    const emailRoutingAliasDestinationInput = document.getElementById("email-routing-alias-destination-input");
    const emailRoutingAliasNameInput = document.getElementById("email-routing-alias-name-input");
    const emailRoutingCreateAlias = document.getElementById("email-routing-create-alias");
    const emailRoutingCreateRoute = document.getElementById("email-routing-create-route");
    const emailRoutingAddressHistory = document.getElementById("email-routing-address-history");
    const emailRoutingAddressHistoryPanel = document.getElementById("email-routing-address-history-panel");
    const emailRoutingAddressSearch = document.getElementById("email-routing-address-search");
    const emailRoutingReceivedAddressList = document.getElementById("email-routing-received-address-list");
    const emailRoutingAliasList = document.getElementById("email-routing-alias-list");
    const emailRoutingMessageCount = document.getElementById("email-routing-message-count");
    const emailRoutingMessageList = document.getElementById("email-routing-message-list");
    const emailRoutingReaderBack = document.getElementById("email-routing-reader-back");
    const emailRoutingReaderSubject = document.getElementById("email-routing-reader-subject");
    const emailRoutingReaderSender = document.getElementById("email-routing-reader-sender");
    const emailRoutingReaderTime = document.getElementById("email-routing-reader-time");
    const emailRoutingReaderCode = document.getElementById("email-routing-reader-code");
    const emailRoutingReaderBody = document.getElementById("email-routing-reader-body");
    const distributedWorkerCopyCommand = document.getElementById("distributed-worker-copy-command");
    const distributedWorkerState = document.getElementById("distributed-worker-state");
    const distributedWorkerCommand = document.getElementById("distributed-worker-command");
    const distributedWorkerList = document.getElementById("distributed-worker-list");
    const distributedWorkerLimitTranslate = document.getElementById("distributed-worker-limit-translate");
    const distributedWorkerLimitTts = document.getElementById("distributed-worker-limit-tts");
    const distributedWorkerLimitStt = document.getElementById("distributed-worker-limit-stt");
    const distributedWorkerLimitGemini = document.getElementById("distributed-worker-limit-gemini");
    const distributedWorkerLimitPhonemize = document.getElementById("distributed-worker-limit-phonemize");
    const distributedWorkerMachineLimit = document.getElementById("distributed-worker-machine-limit");
    const distributedWorkerLimitSave = document.getElementById("distributed-worker-limit-save");
    const distributedWorkerLogToggle = document.getElementById("distributed-worker-log-toggle");
    const distributedWorkerLogList = document.getElementById("distributed-worker-log-list");
  if (distributedWorkerList) distributedWorkerList.classList.add("worker-list");
  const tabChatBadge = document.getElementById("tab-chat-badge");
  const tabPasswordResetBadge = document.getElementById("tab-password-reset-badge");
  const tabSecurityBadge = document.getElementById("tab-security-badge");
  const onlineUsersNode = document.getElementById("online-users");
    const adminChatModal = document.getElementById("admin-chat-modal");
    const adminChatTitle = document.getElementById("admin-chat-title");
    const adminChatClose = document.getElementById("admin-chat-close");
    const adminChatLog = document.getElementById("admin-chat-log");
    const adminChatInput = document.getElementById("admin-chat-input");
    const adminChatSend = document.getElementById("admin-chat-send");
    const adminChatTranslate = document.getElementById("admin-chat-translate");
    const adminChatAttach = document.getElementById("admin-chat-attach");
    const adminChatMic = document.getElementById("admin-chat-mic");
    const adminChatSpeechMode = document.getElementById("admin-chat-speech-mode");
    const adminChatTextMic = document.getElementById("admin-chat-text-mic");
    const adminChatVoiceSend = document.getElementById("admin-chat-voice-send");
    const adminChatVoiceCancel = document.getElementById("admin-chat-voice-cancel");
    const adminChatFile = document.getElementById("admin-chat-file");
    const adminChatVoiceState = document.getElementById("admin-chat-voice-state");
    const adminChatViVoice = document.getElementById("admin-chat-vi-voice");
    const adminChatViAudioToggle = document.getElementById("admin-chat-vi-audio-toggle");
    const adminChatEnInput = document.getElementById("admin-chat-en-input");
    const adminChatEnVoice = document.getElementById("admin-chat-en-voice");
    const adminChatEnAudioToggle = document.getElementById("admin-chat-en-audio-toggle");
    const adminChatEnSend = document.getElementById("admin-chat-en-send");
    const adminImageViewer = document.getElementById("admin-image-viewer");
    const adminImageViewerImg = document.getElementById("admin-image-viewer-img");
    const adminImageClose = document.getElementById("admin-image-close");
    const adminImageDownload = document.getElementById("admin-image-download");
    const adminImageZoomOut = document.getElementById("admin-image-zoom-out");
    const adminImageZoomReset = document.getElementById("admin-image-zoom-reset");
    const adminImageZoomIn = document.getElementById("admin-image-zoom-in");
    const adminScreenModal = document.getElementById("admin-screen-modal");
    const adminScreenCard = document.getElementById("admin-screen-card");
    const adminScreenTitle = document.getElementById("admin-screen-title");
    const adminScreenClose = document.getElementById("admin-screen-close");
    const adminScreenFullscreen = document.getElementById("admin-screen-fullscreen");
    const adminScreenMic = document.getElementById("admin-screen-mic");
    const adminScreenView = document.getElementById("admin-screen-view");
    const adminScreenVideo = document.getElementById("admin-screen-video");
    const adminScreenImg = document.getElementById("admin-screen-img");
    const adminScreenStatus = document.getElementById("admin-screen-status");
    const adminPaintModal = document.getElementById("admin-paint-modal");
    const adminPaintCard = document.getElementById("admin-paint-card");
    const adminPaintTitle = document.getElementById("admin-paint-title");
    const adminPaintClose = document.getElementById("admin-paint-close");
    const adminPaintCanvas = document.getElementById("admin-paint-canvas");
    const adminPaintModeButtons = Array.from(document.querySelectorAll("[data-admin-paint-mode]"));
    const adminPaintClear = document.getElementById("admin-paint-clear");
    const adminPaintImage = document.getElementById("admin-paint-image");
    const adminPaintPaste = document.getElementById("admin-paint-paste");
    const adminPaintDelete = document.getElementById("admin-paint-delete");
    const adminPaintZoomOut = document.getElementById("admin-paint-zoom-out");
    const adminPaintZoomIn = document.getElementById("admin-paint-zoom-in");
    const adminPaintZoomLabel = document.getElementById("admin-paint-zoom-label");
    const adminPaintFullscreen = document.getElementById("admin-paint-fullscreen");
    const adminPaintTab = document.getElementById("admin-paint-tab");
    const adminPaintImageFile = document.getElementById("admin-paint-image-file");
    const adminPaintColor = document.getElementById("admin-paint-color");
    const adminPaintSize = document.getElementById("admin-paint-size");
    const adminPaintText = document.getElementById("admin-paint-text");
    const adminPaintStatus = document.getElementById("admin-paint-status");
    let adminChatState = {{ users: [], online_count: 0 }};
    let adminChatUser = "";
    const adminClearChatArmed = new Map();
    let adminTranslateEnabled = false;
    let adminTranslateTimer = 0;
    let adminChatViAudioEnabled = localStorage.getItem("future_admin_chat_vi_audio") !== "0";
    let adminChatEnAudioEnabled = localStorage.getItem("future_admin_chat_en_audio") !== "0";
    let adminChatVoices = {{ vi: [], en: [] }};
    const adminChatPlayedAudioIds = new Set();
    let adminChatRenderedUser = "";
    let adminChatRenderedSignature = "";
    let adminChatRecorder = null;
    let adminChatRecordStream = null;
    let adminChatRecordChunks = [];
    let adminChatRecordBlob = null;
    let adminChatRecordInput = null;
    let adminChatRecordStartedAt = 0;
    let adminChatRecordTimer = 0;
    let adminChatRecordCanceled = false;
    let adminChatTextRecognition = null;
    let adminChatTextInput = null;
    let adminChatTextBaseValue = "";
    let adminChatTextFinalText = "";
    let adminChatTextInterimText = "";
    let adminChatTextStartedAt = 0;
    let adminChatTextTimer = 0;
    const adminScreenPreviewCache = new Map();
    let adminStreamSession = null;
    let adminStreamUser = "";
    let adminStreamRecorder = null;
    let adminStreamMedia = null;
    let adminStreamSegmentTimer = 0;
    let adminStreamRecordChunks = [];
    let adminStreamLastChunkId = 0;
    let adminStreamAudioChain = Promise.resolve();
    let adminStreamAudioQueue = [];
    let adminStreamAudioPlaying = false;
    let adminStreamCurrentAudio = null;
    let adminStreamRelayMediaSource = null;
    let adminStreamRelaySourceBuffer = null;
    let adminStreamRelayObjectUrl = "";
    let adminStreamRelayPendingBuffers = [];
    let adminStreamRelayMime = "";
    let adminStreamRelayOpening = false;
    let adminStreamRelayDropped = 0;
    let adminStreamAudioUnlocked = false;
    let adminStreamChunkPolling = false;
    let adminStreamPeer = null;
    let adminStreamRemoteAudio = null;
    let adminStreamInboundStream = null;
    let adminStreamInboundTrack = null;
    let adminStreamRemoteCandidateId = 0;
    let adminStreamOfferSent = false;
    let adminStreamAnswerSet = false;
    let adminStreamPeerStartedAt = 0;
    let adminScreenUser = "";
    let adminScreenSession = null;
    let adminScreenFrameId = 0;
    let adminScreenFrameSeenAt = 0;
    let adminScreenPollTimer = 0;
    let adminScreenPeer = null;
    let adminScreenRemoteCandidateId = 0;
    let adminScreenOfferSent = false;
    let adminScreenAnswerSet = false;
    let adminScreenPeerStartedAt = 0;
    let adminScreenControlChannel = null;
    let adminScreenControlQueue = [];
    let adminScreenControlTimer = 0;
    let adminScreenControlSending = false;
    let adminScreenControlLastSentAt = 0;
    let adminScreenPointerDown = null;
    let adminPaintUser = "";
    let adminPaintRevision = 0;
    let adminPaintMode = "pen";
    let adminPaintPointer = null;
    let adminPaintPollTimer = 0;
    let adminPaintPollInFlight = false;
    let adminPaintLastRemoteCursorAt = 0;
    let adminPaintLastPollChangedAt = 0;
    let adminPaintSendTimer = 0;
    let adminPaintCursorTimer = 0;
    let adminPaintCursorSending = false;
    let adminPaintLastCursorSentAt = 0;
    let adminPaintLocalCursor = null;
    let adminPaintRemoteCursor = null;
    let adminPaintRemoteCursorNode = null;
    let adminPaintApplyingRemote = false;
    let adminPaintSending = false;
    let adminPaintBufferCanvas = null;
    let adminPaintSelection = null;
    let adminPaintTextEditor = null;
    let adminPaintZoom = 1;
    const adminPaintAutoUser = new URLSearchParams(window.location.search || "").get("paint_user") || "";
    const ADMIN_PAINT_BOARD_WIDTH = 1200;
    const ADMIN_PAINT_BOARD_HEIGHT = 720;
    const adminImageViewerState = {{
      zoom: 1,
      x: 0,
      y: 0,
      dragging: false,
      pointerId: 0,
      startX: 0,
      startY: 0,
      originX: 0,
      originY: 0,
    }};
    let dashboardSession = "";
    try {{
      dashboardSession = sessionStorage.getItem("future-dashboard-session") || "";
    }} catch (error) {{
    }}
    if (!dashboardSession) {{
      dashboardSession = (window.crypto && crypto.randomUUID)
        ? crypto.randomUUID()
        : `${{Date.now()}}-${{Math.random().toString(16).slice(2)}}`;
      try {{
        sessionStorage.setItem("future-dashboard-session", dashboardSession);
      }} catch (error) {{
      }}
    }}
    const DASHBOARD_VISIBLE_POLL_MS = 30000;
    const DASHBOARD_HIDDEN_POLL_MS = 600000;
    const DASHBOARD_FOCUS_MIN_REQUEST_MS = 30000;
    const dashboardPollIsFocused = () => Boolean(!document.hidden && (!document.hasFocus || document.hasFocus()));
    const dashboardBasePollDelay = () => dashboardPollIsFocused() ? DASHBOARD_VISIBLE_POLL_MS : DASHBOARD_HIDDEN_POLL_MS;
    let dashboardPingTimer = 0;
    let dashboardPingControl = null;
    let dashboardClosedSignalSent = false;
    let dashboardRetired = false;
    const closeRetiredDashboard = (reason) => {{
      if (dashboardRetired) return;
      dashboardRetired = true;
      if (dashboardPingControl && typeof dashboardPingControl.stop === "function") dashboardPingControl.stop();
      if (dashboardPingTimer) window.clearTimeout(dashboardPingTimer);
      if (messageNode) {{
        messageNode.textContent = reason || "Closing old dashboard session...";
      }}
      try {{
        window.close();
      }} catch (error) {{
      }}
      window.setTimeout(() => {{
        try {{
          location.replace("about:blank");
        }} catch (error) {{
        }}
      }}, 350);
    }};
    const handleDashboardControlPayload = (payload) => {{
      if (!payload || typeof payload !== "object") return;
      const activeSession = String(payload.dashboard_session || "");
      if (payload.close_dashboard && activeSession && activeSession !== dashboardSession) {{
        closeRetiredDashboard("Closing old dashboard session...");
      }}
    }};
    window.addEventListener("storage", (event) => {{
      if (event.key !== "future-dashboard-control" || !event.newValue) return;
      try {{
        const payload = JSON.parse(event.newValue);
        if (payload && payload.type === "close-old-dashboards" && payload.keep && payload.keep !== dashboardSession) {{
          closeRetiredDashboard("Closing old dashboard session...");
        }}
      }} catch (error) {{
      }}
    }});
    const broadcastDashboardControl = (payload) => {{
      try {{
        localStorage.setItem("future-dashboard-control", JSON.stringify({{ ...payload, at: Date.now() }}));
        localStorage.removeItem("future-dashboard-control");
      }} catch (error) {{
      }}
    }};
    const dashboardSignal = (action) => {{
      const payload = JSON.stringify({{ session: dashboardSession, action }});
      if (action === "close") {{
        if (dashboardClosedSignalSent) return;
        dashboardClosedSignalSent = true;
        try {{
          if (navigator.sendBeacon) {{
            const blob = new Blob([payload], {{ type: "application/json" }});
            navigator.sendBeacon("/dashboard/close", blob);
            return;
          }}
        }} catch (error) {{
        }}
      }}
      return fetch(`/dashboard/${{action}}`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: payload,
        keepalive: action === "close",
      }})
        .then((response) => response.json().catch(() => ({{}})))
        .then(handleDashboardControlPayload)
        .catch(() => {{}});
    }};
    dashboardSignal("open");
    let dashboardCloseSent = false;
    window.addEventListener("pagehide", () => {{
      if (dashboardPingControl && typeof dashboardPingControl.stop === "function") dashboardPingControl.stop();
      window.clearTimeout(dashboardPingTimer);
      if (!dashboardCloseSent) {{
        dashboardCloseSent = true;
        dashboardSignal("close");
      }}
    }});
    if (killOtherServersButton) {{
      killOtherServersButton.addEventListener("click", async () => {{
        if (!window.confirm("Kill every other Future server process and its child dashboard windows? Current dashboard stays open.")) {{
          return;
        }}
        killOtherServersButton.disabled = true;
        const previousLabel = killOtherServersButton.textContent;
        killOtherServersButton.textContent = "Killing...";
        setTextIfChanged(messageNode, "Killing old Future server processes...");
        try {{
          const response = await fetch("/dashboard/kill-other-servers", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ session: dashboardSession }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not kill old Future servers.");
          }}
          broadcastDashboardControl({{ type: "close-old-dashboards", keep: dashboardSession }});
          const killed = Array.isArray(payload.killed) ? payload.killed : [];
          const failed = Array.isArray(payload.failed) ? payload.failed : [];
          const stale = Array.isArray(payload.stale_pid_files) ? payload.stale_pid_files : [];
          const killedPids = killed.map((row) => row && row.pid).filter(Boolean).join(", ");
          const failedPids = failed.map((row) => row && row.pid).filter(Boolean).join(", ");
          const stalePids = stale.map((row) => row && row.pid).filter(Boolean).join(", ");
          const text = killed.length
            ? `Killed old Future server PID${{killed.length > 1 ? "s" : ""}}: ${{killedPids}}${{failed.length ? ` | failed: ${{failedPids}}` : ""}}`
            : (failed.length ? `No server killed. Failed: ${{failedPids}}` : (stale.length ? `No running old server found. Cleared stale PID${{stale.length > 1 ? "s" : ""}}: ${{stalePids}}` : "No old Future server process found."));
          setTextIfChanged(messageNode, text);
        }} catch (error) {{
          setTextIfChanged(messageNode, String(error && error.message ? error.message : error));
        }} finally {{
          killOtherServersButton.disabled = false;
          killOtherServersButton.textContent = previousLabel || "Kill old Future servers";
        }}
      }});
    }}
    if (cleanCloseAllRuntimeButton) {{
      cleanCloseAllRuntimeButton.addEventListener("click", async () => {{
        if (!window.confirm("Close Future Server 2 and Cloudflare Tunnel now? Persistent STT/voice workers will stay running for the next server.")) {{
          return;
        }}
        cleanCloseAllRuntimeButton.disabled = true;
        const previousLabel = cleanCloseAllRuntimeButton.textContent;
        cleanCloseAllRuntimeButton.textContent = "Closing...";
        setTextIfChanged(messageNode, "Closing Future server and Cloudflare Tunnel...");
        try {{
          const response = await fetch("/dashboard/clean-close-all", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ session: dashboardSession }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not close all Future runtime processes.");
          }}
          const targets = Array.isArray(payload.targets) ? payload.targets : [];
          const pids = targets.map((row) => row && row.pid).filter(Boolean).join(", ");
          setTextIfChanged(messageNode, pids ? `Close accepted. Closing server/tunnel PID(s): ${{pids}}` : "Close accepted. Server will exit now.");
          broadcastDashboardControl({{ type: "close-old-dashboards", keep: "" }});
        }} catch (error) {{
          setTextIfChanged(messageNode, String(error && error.message ? error.message : error));
          cleanCloseAllRuntimeButton.disabled = false;
          cleanCloseAllRuntimeButton.textContent = previousLabel || "Close server + tunnel";
        }}
      }});
    }}
    if (frontendUpdateClientsButton) {{
      frontendUpdateClientsButton.addEventListener("click", async () => {{
        frontendUpdateClientsButton.disabled = true;
        const previousLabel = frontendUpdateClientsButton.textContent;
        frontendUpdateClientsButton.textContent = "Updating...";
        setTextIfChanged(messageNode, "Broadcasting client reload request...");
        try {{
          const response = await fetch("/frontend-version/bump", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ reason: "dashboard_update" }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not update connected clients.");
          }}
          setTextIfChanged(messageNode, `Client reload token updated: ${{payload.token || "ok"}}`);
        }} catch (error) {{
          setTextIfChanged(messageNode, String(error && error.message ? error.message : error));
        }} finally {{
          frontendUpdateClientsButton.disabled = false;
          frontendUpdateClientsButton.textContent = previousLabel || "Update clients";
        }}
      }});
    }}
    if (closeServerButton) {{
      closeServerButton.addEventListener("click", async () => {{
        if (!window.confirm("Close this Future server and disconnect every connected client?")) {{
          return;
        }}
        closeServerButton.disabled = true;
        if (killOtherServersButton) killOtherServersButton.disabled = true;
        if (frontendUpdateClientsButton) frontendUpdateClientsButton.disabled = true;
        const previousLabel = closeServerButton.textContent;
        closeServerButton.textContent = "Closing...";
        setTextIfChanged(messageNode, "Requesting Future server shutdown...");
        if (dashboardPingControl && typeof dashboardPingControl.stop === "function") dashboardPingControl.stop();
        window.clearTimeout(dashboardPingTimer);
        dashboardCloseSent = true;
        try {{
          const response = await fetch("/dashboard/shutdown", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ session: dashboardSession }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not close the Future server.");
          }}
          setTextIfChanged(messageNode, "Server shutdown requested. This dashboard will disconnect in a moment.");
        }} catch (error) {{
          setTextIfChanged(messageNode, String(error && error.message ? error.message : error));
          dashboardCloseSent = false;
          if (killOtherServersButton) killOtherServersButton.disabled = false;
          if (frontendUpdateClientsButton) frontendUpdateClientsButton.disabled = false;
          closeServerButton.disabled = false;
          closeServerButton.textContent = previousLabel || "Close server";
          return;
        }}
        window.setTimeout(() => {{
          try {{
            window.close();
          }} catch (error) {{
          }}
        }}, 120);
      }});
    }}
    endpointNode.textContent = `${{location.origin}}/transcribe`;
    const fmt = (seconds) => {{
      const value = Math.max(0, Math.floor(seconds || 0));
      const m = Math.floor(value / 60);
      const s = value % 60;
      return m ? `${{m}}m ${{s}}s` : `${{s}}s`;
    }};
    const setTextIfChanged = (node, value) => {{
      if (!node) return;
      const text = String(value ?? "");
      if (node.textContent !== text) node.textContent = text;
    }};
    const dashboardUserColorForKey = (key = "") => {{
      const source = String(key || "").trim().toLowerCase();
      const palette = ["#7dd3fc", "#86efac", "#facc15", "#f0abfc", "#fb7185", "#38bdf8", "#a7f3d0", "#fdba74", "#c4b5fd", "#5eead4"];
      if (!source || source === "-") return "#e5e7eb";
      if (source === "server") return "#f8fafc";
      let hash = 0;
      for (let index = 0; index < source.length; index += 1) hash = ((hash * 33) + source.charCodeAt(index)) >>> 0;
      return palette[hash % palette.length];
    }};
    const colorDashboardUserNode = (node, key = "") => {{
      if (!node) return;
      node.style.color = dashboardUserColorForKey(key);
    }};
    const WORKER_LOG_VISIBLE_KEY = "future-dashboard-worker-log-visible";
    let distributedWorkerLogsVisible = localStorage.getItem(WORKER_LOG_VISIBLE_KEY) !== "0";
    // Added 2026-07-15: keeps the server console worker-poll filter synced with the dashboard toggle.
    const syncDistributedWorkerLogVisibility = (visible) => {{
      fetch("/dashboard/worker-log-visibility", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ visible: !!visible }}),
      }}).catch(() => {{}});
    }};
    const renderDistributedWorkerLogToggle = () => {{
      if (distributedWorkerLogToggle) {{
        setTextIfChanged(distributedWorkerLogToggle, distributedWorkerLogsVisible ? "Hide worker logs" : "Show worker logs");
        distributedWorkerLogToggle.setAttribute("aria-pressed", distributedWorkerLogsVisible ? "true" : "false");
      }}
      if (distributedWorkerLogList) {{
        distributedWorkerLogList.hidden = !distributedWorkerLogsVisible;
      }}
    }};
    if (distributedWorkerLogToggle) {{
      distributedWorkerLogToggle.addEventListener("click", () => {{
        distributedWorkerLogsVisible = !distributedWorkerLogsVisible;
        localStorage.setItem(WORKER_LOG_VISIBLE_KEY, distributedWorkerLogsVisible ? "1" : "0");
        renderDistributedWorkerLogToggle();
        syncDistributedWorkerLogVisibility(distributedWorkerLogsVisible);
      }});
      renderDistributedWorkerLogToggle();
      syncDistributedWorkerLogVisibility(distributedWorkerLogsVisible);
    }}
    let dashboardStatusSignature = "";
    const dashboardOpenedAt = Date.now();
    const updateDashboardFreshness = () => {{
      if (!dashboardFreshnessNode) return;
      const elapsed = Math.max(0, Math.floor((Date.now() - dashboardOpenedAt) / 1000));
      const remaining = Math.max(0, 60 - elapsed);
      const isNew = remaining > 0;
      const nextText = isNew ? `NEW | ${{remaining}}s` : "OLD";
      dashboardFreshnessNode.classList.toggle("is-old", !isNew);
      setTextIfChanged(dashboardFreshnessNode, nextText);
      dashboardFreshnessNode.title = isNew
        ? `Dashboard opened recently. NEW for ${{remaining}} second${{remaining === 1 ? "" : "s"}}.`
        : "Dashboard has been open for more than one minute.";
    }};
    updateDashboardFreshness();
    window.setInterval(updateDashboardFreshness, 1000);
    const setDashboardStatus = (label, classes = []) => {{
      if (!statusNode) return;
      const cleanClasses = Array.isArray(classes) ? classes.filter(Boolean) : [];
      const signature = `${{label}}|${{cleanClasses.join(" ")}}`;
      if (dashboardStatusSignature === signature) return;
      dashboardStatusSignature = signature;
      statusNode.className = `pill ${{cleanClasses.join(" ")}}`.trim();
      statusNode.innerHTML = `<span class="pulse"></span>${{label}}`;
    }};
    const renderDashboardWarmLog = (state = {{}}) => {{
      if (!dashboardWarmLogNode) return;
      const ready = Boolean(state.warm_ready);
      const status = String(state.warm_status || (ready ? "Warm ready" : "Warm queue running...")).trim();
      dashboardWarmLogNode.classList.toggle("is-ready", ready);
      setTextIfChanged(dashboardWarmLogNode, ready ? "Warm ready" : status);
      dashboardWarmLogNode.title = ready
        ? "Background warm tasks are ready."
        : status;
    }};
    const normalizeWorkerJobLimits = (value = {{}}) => {{
      const source = value && typeof value === "object" ? value : {{}};
      const limit = (key, fallback) => {{
        const number = Math.round(Number(source[key]));
        return Number.isFinite(number) ? Math.max(0, Math.min(64, number)) : fallback;
      }};
      return {{
        translate: limit("translate", 4),
        tts: limit("tts", 4),
        stt: limit("stt", 4),
        gemini: limit("gemini", 4),
        phonemize: limit("phonemize", 8),
      }};
    }};
    const renderWorkerJobLimitInputs = (limits = {{}}) => {{
      const normalized = normalizeWorkerJobLimits(limits);
      const pairs = [
        [distributedWorkerLimitTranslate, normalized.translate],
        [distributedWorkerLimitTts, normalized.tts],
        [distributedWorkerLimitStt, normalized.stt],
        [distributedWorkerLimitGemini, normalized.gemini],
        [distributedWorkerLimitPhonemize, normalized.phonemize],
      ];
      pairs.forEach(([input, value]) => {{
        if (input && document.activeElement !== input) input.value = String(value);
      }});
    }};
    const normalizeWorkerMachineLimit = (value) => {{
      const number = Math.round(Number(value));
      return Number.isFinite(number) ? Math.max(1, Math.min(32, number)) : 1;
    }};
    const renderWorkerMachineLimitInput = (value) => {{
      if (distributedWorkerMachineLimit && document.activeElement !== distributedWorkerMachineLimit) {{
        distributedWorkerMachineLimit.value = String(normalizeWorkerMachineLimit(value));
      }}
    }};
    const renderDistributedWorkers = (payload = {{}}) => {{
      if (!distributedWorkerList) return;
      const workers = Array.isArray(payload.workers) ? payload.workers : [];
      const logs = Array.isArray(payload.logs) ? payload.logs : [];
      const stats = payload.stats || {{}};
      const limits = normalizeWorkerJobLimits(payload.job_limits || {{}});
      const machineLimit = normalizeWorkerMachineLimit(payload.machine_limit);
      const activeByKind = payload.active_by_kind || {{}};
      const command = String(payload.command || "");
      renderWorkerJobLimitInputs(limits);
      renderWorkerMachineLimitInput(machineLimit);
      if (distributedWorkerCommand) setTextIfChanged(distributedWorkerCommand, command || "Open dashboard on the server machine to see the tokenized command.");
      if (distributedWorkerState) {{
        const online = Number(payload.online || 0);
        const queued = Number(payload.queued || 0);
        const claimed = Number(payload.claimed || 0);
        const laneText = `T ${{Number(activeByKind.translate || 0)}}/${{limits.translate}} | Voice ${{Number(activeByKind.tts || 0)}}/${{limits.tts}} | STT ${{Number(activeByKind.stt || 0)}}/${{limits.stt}} | Gemini ${{Number(activeByKind.gemini || 0)}}/${{limits.gemini}} | IPA ${{Number(activeByKind.phonemize || 0)}}/${{limits.phonemize}}`;
        setTextIfChanged(
          distributedWorkerState,
          `${{online}} online | max ${{machineLimit}}/machine | ${{queued}} queued | ${{claimed}} running | ${{laneText}} | done ${{Number(stats.completed || 0)}} | failed ${{Number(stats.failed || 0)}} | token ${{payload.token_hint || "ready"}}`
        );
      }}
      distributedWorkerList.textContent = "";
      if (!workers.length) {{
        const empty = document.createElement("div");
        empty.className = "dashboard-log-row worker-row";
        empty.textContent = "No workers connected. Learners download the worker package from the WORKER button in the user frontend.";
        distributedWorkerList.appendChild(empty);
        return;
      }}
      const workerKinds = ["translate", "tts", "stt", "gemini", "phonemize"];
      const workerKindLabel = {{ translate: "T", tts: "Voice", stt: "STT", gemini: "Gemini", phonemize: "IPA" }};
      const workerLoadText = (active = {{}}, caps = {{}}) => workerKinds
        .map((kind) => `${{workerKindLabel[kind]}} ${{Array.isArray(active[kind]) ? active[kind].length : 0}}/${{Number(caps[kind] || 0)}}`)
        .join(" | ");
      const workerJobText = (active = {{}}) => workerKinds
        .flatMap((kind) => (Array.isArray(active[kind]) ? active[kind] : []).map((jobId) => `${{workerKindLabel[kind]}}:${{jobId}}`))
        .join(", ");
      const groups = new Map();
      workers.forEach((worker) => {{
        const machineKey = String(worker.client_ip || worker.name || worker.owner_user || "unknown-machine");
        const ownerKey = String(worker.owner_user || "");
        const groupKey = `${{machineKey}}|${{ownerKey}}`;
        if (!groups.has(groupKey)) {{
          groups.set(groupKey, {{
            machine: machineKey,
            owner: ownerKey,
            workers: [],
            active: {{ translate: 0, tts: 0, stt: 0, gemini: 0, phonemize: 0 }},
            caps: {{ translate: 0, tts: 0, stt: 0, gemini: 0, phonemize: 0 }},
            completed: 0,
            failed: 0,
          }});
        }}
        const group = groups.get(groupKey);
        group.workers.push(worker);
        const caps = normalizeWorkerJobLimits(worker.max_jobs_by_kind || {{}});
        const active = worker.active_jobs && typeof worker.active_jobs === "object" ? worker.active_jobs : {{}};
        workerKinds.forEach((kind) => {{
          group.active[kind] += Array.isArray(active[kind]) ? active[kind].length : 0;
          group.caps[kind] += Number(caps[kind] || 0);
        }});
        group.completed += Number(worker.completed || 0);
        group.failed += Number(worker.failed || 0);
      }});
      Array.from(groups.values()).sort((a, b) => {{
        const busyDiff = workerKinds.reduce((sum, kind) => sum + b.active[kind] - a.active[kind], 0);
        if (busyDiff) return busyDiff;
        return String(a.machine).localeCompare(String(b.machine));
      }}).forEach((group) => {{
        const groupRow = document.createElement("div");
        groupRow.className = "dashboard-log-row worker-row worker-machine-row";
        const groupState = document.createElement("div");
        groupState.className = "dashboard-log-time";
        const groupBusy = workerKinds.reduce((sum, kind) => sum + group.active[kind], 0);
        groupState.textContent = groupBusy ? "Active" : "Ready";
        const groupName = document.createElement("div");
        groupName.className = "dashboard-log-user";
        groupName.textContent = `Machine ${{group.machine}}`;
        colorDashboardUserNode(groupName, group.owner || group.machine);
        const groupDetail = document.createElement("div");
        groupDetail.className = "dashboard-log-detail";
        const owner = group.owner ? `owner ${{group.owner}} | ` : "";
        groupDetail.textContent = `${{owner}}${{group.workers.length}} worker${{group.workers.length === 1 ? "" : "s"}} | ${{workerLoadText(Object.fromEntries(workerKinds.map((kind) => [kind, Array(group.active[kind]).fill("job")])), group.caps)}} | done ${{group.completed}} / failed ${{group.failed}}`;
        groupRow.append(groupState, groupName, groupDetail);
        distributedWorkerList.appendChild(groupRow);
        group.workers.sort((a, b) => String(a.worker_id || "").localeCompare(String(b.worker_id || ""))).forEach((worker) => {{
        const row = document.createElement("div");
        row.className = "dashboard-log-row worker-row worker-instance-row";
        const at = document.createElement("div");
        at.className = "dashboard-log-time";
        at.textContent = worker.busy ? "Busy" : String(worker.status || "offline");
        const name = document.createElement("div");
        name.className = "dashboard-log-user";
        name.textContent = String(worker.name || worker.worker_id || "worker");
        colorDashboardUserNode(name, worker.owner_user || worker.name || worker.worker_id || "");
        const detail = document.createElement("div");
        detail.className = "dashboard-log-detail";
        const caps = Array.isArray(worker.capabilities) ? worker.capabilities.join(", ") : "";
        const busyKinds = Array.isArray(worker.busy_kinds) ? worker.busy_kinds.join(",") : "";
        const maxJobs = normalizeWorkerJobLimits(worker.max_jobs_by_kind || {{}});
        const active = worker.active_jobs && typeof worker.active_jobs === "object" ? worker.active_jobs : {{}};
        const laneCaps = workerLoadText(active, maxJobs);
        const lastSeen = Number(worker.last_seen_seconds || 0);
        const currentJob = workerJobText(active) || (worker.current_job ? String(worker.current_job) : "");
        const ip = worker.client_ip ? ` | ${{worker.client_ip}}` : "";
        const err = worker.last_error ? ` | error: ${{worker.last_error}}` : "";
        const owner = worker.owner_user ? ` | owner ${{worker.owner_user}}` : "";
        const jobPart = currentJob ? ` | doing ${{currentJob}}` : "";
        const features = worker.features && typeof worker.features === "object" ? worker.features : {{}};
        const kviBase = features.tts_kokoro_vi_cuda ? "Kokoro VI CUDA" : "Kokoro VI";
        const kvi = features.tts_kokoro_vi
          ? (features.tts_kokoro_vi_warm ? `${{kviBase}} warm` : `${{kviBase}} ready`)
          : "Kokoro VI missing";
        const kviError = !features.tts_kokoro_vi && features.kokoro_vi_error ? ` (${{features.kokoro_vi_error}})` : "";
        const kviPython = features.kokoro_vi_python ? ` | py ${{features.kokoro_vi_python}}` : "";
        const ipaWarm = features.phonemize_warm || features.spacy_warm ? ` | IPA ${{features.phonemize_warm ? "phonetic warm" : "phonetic cold"}} / ${{features.spacy_warm ? "spaCy warm" : "spaCy cold"}}` : "";
        detail.textContent = `${{caps || "no caps"}} | ${{laneCaps}} | ${{kvi}}${{kviError}}${{kviPython}}${{ipaWarm}}${{busyKinds ? ` | busy ${{busyKinds}}` : ""}}${{owner}} | seen ${{lastSeen}}s ago | done ${{Number(worker.completed || 0)}} / failed ${{Number(worker.failed || 0)}}${{jobPart}}${{ip}}${{err}}`;
        row.append(at, name, detail);
        distributedWorkerList.appendChild(row);
        }});
      }});
      if (distributedWorkerLogList) {{
        renderDistributedWorkerLogToggle();
        if (!distributedWorkerLogsVisible) return;
        distributedWorkerLogList.textContent = "";
        if (!logs.length) {{
          const emptyLog = document.createElement("div");
          emptyLog.className = "dashboard-log-row";
          emptyLog.textContent = "No worker logs yet.";
          distributedWorkerLogList.appendChild(emptyLog);
        }} else {{
          logs.slice().reverse().forEach((item) => {{
            const row = document.createElement("div");
            row.className = "dashboard-log-row";
            const at = document.createElement("div");
            at.className = "dashboard-log-time";
            at.textContent = String(item.time || "");
            const name = document.createElement("div");
            name.className = "dashboard-log-user";
            name.textContent = String(item.name || item.worker_id || "worker");
            colorDashboardUserNode(name, item.owner_user || item.name || item.worker_id || "");
            const detail = document.createElement("div");
            detail.className = "dashboard-log-detail";
            const owner = item.owner_user ? `owner ${{item.owner_user}} | ` : "";
            const ip = item.client_ip ? `${{item.client_ip}} | ` : "";
            const version = item.version ? `v${{item.version}} | ` : "";
            const job = item.job_id ? `${{item.kind || "job"}} ${{item.job_id}} | ` : (item.kind ? `${{item.kind}} | ` : "");
            const error = item.error ? ` | error: ${{String(item.error || "").slice(0, 900)}}` : "";
            detail.textContent = `${{owner}}${{ip}}${{version}}${{job}}${{String(item.message || "")}}${{error}}`;
            row.append(at, name, detail);
            distributedWorkerLogList.appendChild(row);
          }});
        }}
      }}
    }};
    const blockSecurityPollIdentity = async (type, identity) => {{
      if (!type || !identity) return;
      try {{
        const response = await fetch("/dashboard/security/block", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ type, identity, minutes: 10 }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not block this poller.");
        }}
        if (messageNode) messageNode.textContent = `Blocked ${{type}} ${{identity}} for 10 minutes.`;
        renderSecurityPoll(payload.security_poll || {{}}, payload.security_alerts || []);
      }} catch (error) {{
        if (messageNode) messageNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    // Added 2026-07-09: keeps the Security dashboard tab visibly marked only when poll pressure needs attention.
    const renderSecurityBadge = (payload = {{}}, alerts = []) => {{
      if (!tabSecurityBadge) return;
      const alertCount = Array.isArray(alerts) ? alerts.length : 0;
      const pressureCount = Array.isArray(payload.top) ? payload.top.length : 0;
      const hasWarning = Boolean(payload.poll_cpu_alert) || alertCount > 0;
      tabSecurityBadge.textContent = hasWarning ? "!" : String(pressureCount || 0);
      tabSecurityBadge.classList.toggle("is-empty", !hasWarning && pressureCount <= 0);
      tabSecurityBadge.title = hasWarning
        ? `${{alertCount}} security alert(s), poll CPU ${{Number(payload.poll_cpu_percent || 0).toFixed(1)}}%`
        : "No security warning.";
    }};
    const renderSecurityPoll = (payload = {{}}, alerts = []) => {{
      if (!securityPollList) return;
      renderSecurityBadge(payload, alerts);
      securityPollList.textContent = "";
      const rows = Array.isArray(payload.top) ? payload.top : [];
      const cpu = Number(payload.poll_cpu_percent || 0) || 0;
      const total = Number(payload.total_recent || 0) || 0;
      const header = document.createElement("div");
      header.className = "dashboard-log-row";
      const h1 = document.createElement("span");
      h1.className = "dashboard-log-time";
      h1.textContent = payload.poll_cpu_alert ? "ALERT" : "OK";
      const h2 = document.createElement("span");
      h2.className = "dashboard-log-user";
      h2.textContent = "poll";
      const h3 = document.createElement("span");
      h3.className = "dashboard-log-detail";
      h3.textContent = `${{payload.poll_cpu_alert ? "Poll CPU high" : "Poll normal"}} | CPU ${{cpu.toFixed(1)}}% | recent ${{total}}`;
      header.append(h1, h2, h3);
      securityPollList.appendChild(header);
      if (!rows.length) {{
        const empty = document.createElement("div");
        empty.className = "dashboard-log-row";
        empty.innerHTML = '<span class="dashboard-log-time">No data</span><span class="dashboard-log-user">-</span><span class="dashboard-log-detail">No active poll pressure.</span>';
        securityPollList.appendChild(empty);
      }} else {{
        rows.forEach((item) => {{
          const row = document.createElement("div");
          row.className = "dashboard-log-row worker-row";
          const at = document.createElement("span");
          at.className = "dashboard-log-time";
          at.textContent = item.last_seen || "";
          const who = document.createElement("span");
          who.className = "dashboard-log-user";
          const type = item.identity_type || (item.username ? "user" : "ip");
          const identity = item.identity || item.username || item.ip || "";
          who.textContent = `${{type}}:${{identity}}`;
          const detail = document.createElement("span");
          detail.className = "dashboard-log-detail";
          detail.textContent = `${{item.method || ""}} ${{item.path || ""}} | count/min ${{item.count || 0}} | ip ${{item.ip || ""}} `;
          const button = document.createElement("button");
          button.className = "pending-action reject";
          button.type = "button";
          button.textContent = "Block 10m";
          button.addEventListener("click", () => blockSecurityPollIdentity(type, identity));
          detail.appendChild(button);
          row.append(at, who, detail);
          securityPollList.appendChild(row);
        }});
      }}
      (Array.isArray(alerts) ? alerts.slice(0, 4) : []).forEach((item) => {{
        const row = document.createElement("div");
        row.className = "dashboard-log-row worker-row";
        const at = document.createElement("span");
        at.className = "dashboard-log-time";
        at.textContent = item.last_seen || "";
        const who = document.createElement("span");
        who.className = "dashboard-log-user";
        who.textContent = item.ip || "";
        const detail = document.createElement("span");
        detail.className = "dashboard-log-detail";
        detail.textContent = `${{item.reason || ""}} | ${{item.path || ""}} | blocked hits ${{item.count || 0}}`;
        row.append(at, who, detail);
        securityPollList.appendChild(row);
      }});
    }};
    const render = (state) => {{
      renderDashboardWarmLog(state || {{}});
      renderDistributedWorkers(state.distributed_workers || {{}});
      renderSecurityPoll(state.security_poll || {{}}, state.security_alerts || []);
      setTextIfChanged(modelNode, state.model_name || "small");
      setTextIfChanged(languageNode, state.language || "en");
      setTextIfChanged(modelRefNode, state.model_ref || (state.loading ? "Loading model..." : "No model path"));
      const publicAppUrl = state.public_app_url || "";
      const tunnelStatus = state.tunnel_status || "not_started";
      const tunnelError = state.tunnel_error || "";
      const pending = Number(state.queue_pending || 0);
      const active = Boolean(state.queue_active);
      const total = Number(state.queue_total || 0);
      const completed = Number(state.queue_completed || 0);
      const failed = Number(state.queue_failed || 0);
      const timeout = Number(state.queue_timeout || 0);
      const lastWait = Number(state.queue_last_wait_ms || 0);
      const lastRun = Number(state.queue_last_process_ms || 0);
      const activeSeconds = active ? Math.max(0, Math.floor(Date.now() / 1000 - Number(state.queue_active_started_at || 0))) : 0;
      setTextIfChanged(queueStatusNode, active
        ? `Running ${{state.queue_active_id || ""}} (${{activeSeconds}}s) | waiting ${{pending}}`
        : `Idle | waiting ${{pending}} | last wait ${{lastWait}}ms | last run ${{lastRun}}ms`);
      setTextIfChanged(queueJobsNode, `${{completed}} done / ${{failed}} failed / ${{timeout}} timeout / ${{total}} total`);
      const workload = state.workload || {{}};
      const heavyQueues = workload.queues || {{}};
      const heavyPending = Object.values(heavyQueues).reduce((sum, item) => sum + Number((item && item.pending) || 0), 0);
      const heavyActive = Object.values(heavyQueues).reduce((sum, item) => sum + Number((item && item.active) || 0), 0);
      setTextIfChanged(cpuGuardStatusNode, `${{workload.cpu_guard_enabled === false ? "Off" : "On"}} | CPU ${{Number(workload.cpu_percent || 0).toFixed(0)}}% / ${{Number(workload.cpu_queue_threshold || 90)}}% | heavy ${{heavyActive}} active, ${{heavyPending}} wait`);
      const learning = state.last_learning_event || {{}};
      setTextIfChanged(learningEventNode, learning.user
        ? `${{learning.user}} completed ${{learning.file || learning.path || "lesson"}} | user ${{learning.user_count || 1}} time(s) | file ${{learning.total || state.learning_total || 1}} time(s) | ${{learning.at || ""}}`
        : `Total completions: ${{Number(state.learning_total || 0)}}`);
      if (publicAppUrl) {{
        setTextIfChanged(publicUrlNode, publicAppUrl);
        copyPublicButton.disabled = false;
      }} else {{
        setTextIfChanged(publicUrlNode, tunnelStatus === "missing"
          ? "cloudflared.exe is missing"
          : tunnelStatus === "restarting" ? "Tunnel is restarting..." : tunnelStatus === "stopped"
            ? "Tunnel stopped"
            : "Building Cloudflare Tunnel...");
        copyPublicButton.disabled = true;
      }}
      setTextIfChanged(uptimeNode, fmt(Date.now() / 1000 - Number(state.started_at || 0)));
      if (state.last_error) {{
        setDashboardStatus("Error", ["error"]);
        setTextIfChanged(messageNode, state.last_error);
      }} else if (tunnelStatus === "restarting") {{
        setDashboardStatus("Tunnel", ["is-busy"]);
        setTextIfChanged(messageNode, tunnelError || "Cloudflare Tunnel is retrying automatically. Keep the server window open.");
      }} else if (tunnelError && !publicAppUrl) {{
        setDashboardStatus("Online");
        setTextIfChanged(messageNode, tunnelError);
      }} else if (active || pending > 0) {{
        setDashboardStatus("Queue", ["is-busy"]);
        setTextIfChanged(messageNode, active
          ? `Voice scoring job ${{state.queue_active_id || ""}} is running. ${{pending}} request(s) waiting.`
          : `Waiting to process ${{pending}} request(s).`);
      }} else if (state.ready) {{
        setDashboardStatus("Ready", ["ready"]);
        setTextIfChanged(messageNode, "Server is ready to receive audio from the Speak popup.");
      }} else if (state.loading) {{
        setDashboardStatus("Loading", ["is-busy"]);
        setTextIfChanged(messageNode, "Warming the small model in the background. This can take a little time.");
      }} else {{
        setDashboardStatus("Online");
        setTextIfChanged(messageNode, "Server is waiting. The small model will load when the Speak popup sends the first recording.");
      }}
    }};
    copyPublicButton.addEventListener("click", async () => {{
      const text = publicUrlNode.textContent || "";
      if (!/^https?:\/\//.test(text)) {{
        return;
      }}
      try {{
        await navigator.clipboard.writeText(text);
        copyPublicButton.textContent = "Copied";
        window.setTimeout(() => copyPublicButton.textContent = "Copy learning link", 1200);
      }} catch (error) {{
        window.prompt("Copy this link:", text);
      }}
    }});
    if (distributedWorkerCopyCommand) distributedWorkerCopyCommand.addEventListener("click", async () => {{
      const text = distributedWorkerCommand ? distributedWorkerCommand.textContent || "" : "";
      if (!text) return;
      try {{
        await navigator.clipboard.writeText(text);
        distributedWorkerCopyCommand.textContent = "Copied";
        window.setTimeout(() => distributedWorkerCopyCommand.textContent = "Copy command", 1200);
      }} catch (error) {{
        window.prompt("Copy this command:", text);
      }}
    }});
    const noticeFirstUpper = (value) => {{
      const raw = String(value || "").replace(/\s+/g, " ").trim();
      if (!raw) return "";
      const chars = Array.from(raw);
      for (let index = 0; index < chars.length; index += 1) {{
        const char = chars[index];
        if (char.toLocaleLowerCase("vi-VN") !== char.toLocaleUpperCase("vi-VN")) {{
          chars[index] = char.toLocaleUpperCase("vi-VN");
          return chars.join("");
        }}
      }}
      return raw;
    }};
    const noticeLines = (text) => String(text || "")
      .replace(/\\r\\n/g, "\\n")
      .replace(/\\r/g, "\\n")
      .split("\\n")
      .map(noticeFirstUpper)
      .filter(Boolean)
      .slice(0, 8);
    const renderAnnouncementPreview = (items) => {{
      const rows = Array.isArray(items) ? items : noticeLines(announcementInput.value);
      announcementPreview.textContent = "";
      if (!rows.length) {{
        const empty = document.createElement("div");
        empty.className = "notice-preview-line";
        empty.textContent = "No announcement yet. Login will show the default system status.";
        announcementPreview.appendChild(empty);
        return;
      }}
      rows.forEach((item) => {{
        const line = document.createElement("div");
        line.className = "notice-preview-line";
        line.textContent = item;
        announcementPreview.appendChild(line);
      }});
    }};
    const loadAnnouncements = async () => {{
      try {{
        const response = await fetch("/announcements?ts=" + Date.now(), {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not load announcements.");
        }}
        const text = payload.raw || (Array.isArray(payload.items) ? payload.items.join("\\n") : "");
        if (document.activeElement !== announcementInput) {{
          announcementInput.value = text;
        }}
        renderAnnouncementPreview(payload.items || noticeLines(text));
        announcementState.textContent = payload.updated_at ? "Updated: " + payload.updated_at : "Default announcement.";
      }} catch (error) {{
        announcementState.textContent = String(error && error.message ? error.message : error);
        renderAnnouncementPreview([]);
      }}
    }};
    if (announcementInput) {{
      announcementInput.addEventListener("input", () => {{
        renderAnnouncementPreview(noticeLines(announcementInput.value));
        announcementState.textContent = "Unsaved.";
      }});
    }}
    if (announcementSave) {{
      announcementSave.addEventListener("click", async () => {{
        announcementSave.disabled = true;
        announcementState.textContent = "Saving...";
        try {{
          const response = await fetch("/announcements", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ text: announcementInput.value || "" }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not save announcements.");
          }}
          announcementInput.value = payload.raw || "";
          renderAnnouncementPreview(payload.items || noticeLines(announcementInput.value));
          announcementState.textContent = "Saved. Login will update automatically.";
        }} catch (error) {{
          announcementState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          announcementSave.disabled = false;
        }}
      }});
    }}
    const normalizeHintSeconds = (value) => {{
      const parsed = Math.round(Number(value || 30));
      if (!Number.isFinite(parsed)) return 30;
      return Math.max(5, Math.min(180, parsed));
    }};
    const normalizeParagraphHintSeconds = (value) => {{
      const parsed = Math.round(Number(value || 30));
      if (!Number.isFinite(parsed)) return 30;
      return Math.max(3, Math.min(300, parsed));
    }};
    const normalizeChatAttachmentLimitMb = (value) => {{
      const parsed = Math.round(Number(value || 100));
      if (!Number.isFinite(parsed)) return 100;
      return Math.max(1, Math.min(4096, parsed));
    }};
    const normalizeHeavyUserQuota = (value) => {{
      const parsed = Math.round(Number(value || 5));
      if (!Number.isFinite(parsed)) return 5;
      return Math.max(1, Math.min(120, parsed));
    }};
    const normalizeHeavyUserInterval = (value) => {{
      const parsed = Math.round(Number(value || 5));
      if (!Number.isFinite(parsed)) return 5;
      return Math.max(0, Math.min(60, parsed));
    }};
    let cpuGuardEnabled = true;
    let spaceWAiCheckVoiceEnabled = true;
    const normalizeCpuThreshold = (value) => {{
      const parsed = Math.round(Number(value || 90));
      if (!Number.isFinite(parsed)) return 90;
      return Math.max(45, Math.min(98, parsed));
    }};
    const normalizeQmCityPercent = (value) => {{
      const parsed = Math.round(Number(value || 50));
      if (!Number.isFinite(parsed)) return 50;
      return Math.max(1, Math.min(100, parsed));
    }};
    const normalizeQmCityInvalidRun = (value) => {{
      const parsed = Math.round(Number(value || 4));
      if (!Number.isFinite(parsed)) return 4;
      return Math.max(1, Math.min(20, parsed));
    }};
    const clampDashboardInt = (value, fallback, min, max) => {{
      const parsed = Math.round(Number(value ?? fallback));
      if (!Number.isFinite(parsed)) return Number(fallback);
      return Math.max(Number(min), Math.min(Number(max), parsed));
    }};
    let qmCityNpcEnabled = true;
    let qmCityNpcMode = "top";
    const normalizeQmCityNpcMode = (source = {{}}) => {{
      const raw = String(source.mode ?? source.source_mode ?? source.sourceMode ?? source.npc_mode ?? source.npcMode ?? "").trim().toLowerCase();
      if (["mixed", "mix", "all", "both", "top+city", "city+top"].includes(raw)) return "mixed";
      if (["city", "citizen", "citizens", "resident", "residents", "off", "default"].includes(raw)) return "city";
      if (["top", "tops", "racer", "racers", "npc_top", "npc-top", "on"].includes(raw)) return "top";
      return source.enabled === false ? "city" : "top";
    }};
    const normalizeQmCityNpcSettings = (value = {{}}) => {{
      const source = value && typeof value === "object" ? value : {{}};
      const minActive = clampDashboardInt(source.min_active ?? source.minActive ?? 1, 1, 0, 5);
      const maxActive = Math.max(minActive, clampDashboardInt(source.max_active ?? source.maxActive ?? 5, 5, 1, 8));
      const onlineMin = clampDashboardInt(source.online_min_minutes ?? source.onlineMinMinutes ?? 20, 20, 5, 180);
      const onlineMax = Math.max(onlineMin, clampDashboardInt(source.online_max_minutes ?? source.onlineMaxMinutes ?? 40, 40, 5, 240));
      const inviteMin = clampDashboardInt(source.invite_cooldown_min_seconds ?? source.inviteCooldownMinSeconds ?? 70, 70, 15, 900);
      const inviteMax = Math.max(inviteMin, clampDashboardInt(source.invite_cooldown_max_seconds ?? source.inviteCooldownMaxSeconds ?? 180, 180, 20, 1200));
      const mode = normalizeQmCityNpcMode(source);
      return {{
        enabled: mode !== "city",
        mode,
        spawn_chance_percent: clampDashboardInt(source.spawn_chance_percent ?? source.spawnChancePercent ?? 55, 55, 0, 100),
        min_active: minActive,
        max_active: maxActive,
        online_min_minutes: onlineMin,
        online_max_minutes: onlineMax,
        answer_correct_percent: clampDashboardInt(source.answer_correct_percent ?? source.answerCorrectPercent ?? 58, 58, 0, 100),
        steal_correct_percent: clampDashboardInt(source.steal_correct_percent ?? source.stealCorrectPercent ?? 34, 34, 0, 100),
        invite_chance_percent: clampDashboardInt(source.invite_chance_percent ?? source.inviteChancePercent ?? 8, 8, 0, 100),
        invite_cooldown_min_seconds: inviteMin,
        invite_cooldown_max_seconds: inviteMax,
      }};
    }};
    const renderQmCityNpcToggle = () => {{
      const topMode = qmCityNpcMode === "top";
      const cityMode = qmCityNpcMode === "city";
      const mixedMode = qmCityNpcMode === "mixed";
      if (qmCityNpcEnabledToggle) {{
        qmCityNpcEnabledToggle.classList.toggle("is-on", topMode || mixedMode);
        qmCityNpcEnabledToggle.setAttribute("aria-pressed", topMode || mixedMode ? "true" : "false");
        qmCityNpcEnabledToggle.textContent = cityMode ? "City residents" : topMode ? "Top racers" : "Top + residents";
      }}
      if (qmCityNpcMixToggle) {{
        qmCityNpcMixToggle.classList.toggle("is-on", mixedMode);
        qmCityNpcMixToggle.setAttribute("aria-pressed", mixedMode ? "true" : "false");
        qmCityNpcMixToggle.textContent = mixedMode ? "Mixed on" : "Mix";
      }}
    }};
    const collectQmCityNpcSettings = () => normalizeQmCityNpcSettings({{
      enabled: qmCityNpcEnabled,
      mode: qmCityNpcMode,
      spawn_chance_percent: qmCityNpcSpawnChanceInput ? qmCityNpcSpawnChanceInput.value : 55,
      min_active: qmCityNpcMinActiveInput ? qmCityNpcMinActiveInput.value : 1,
      max_active: qmCityNpcMaxActiveInput ? qmCityNpcMaxActiveInput.value : 5,
      online_min_minutes: qmCityNpcOnlineMinInput ? qmCityNpcOnlineMinInput.value : 20,
      online_max_minutes: qmCityNpcOnlineMaxInput ? qmCityNpcOnlineMaxInput.value : 40,
      answer_correct_percent: qmCityNpcAnswerInput ? qmCityNpcAnswerInput.value : 58,
      steal_correct_percent: qmCityNpcStealInput ? qmCityNpcStealInput.value : 34,
      invite_chance_percent: qmCityNpcInviteInput ? qmCityNpcInviteInput.value : 8,
      invite_cooldown_min_seconds: qmCityNpcInviteMinInput ? qmCityNpcInviteMinInput.value : 70,
      invite_cooldown_max_seconds: qmCityNpcInviteMaxInput ? qmCityNpcInviteMaxInput.value : 180,
    }});
    const renderQmCityNpcSettings = (settings = {{}}) => {{
      const npc = normalizeQmCityNpcSettings(settings);
      qmCityNpcEnabled = npc.enabled !== false;
      qmCityNpcMode = npc.mode || (qmCityNpcEnabled ? "top" : "city");
      renderQmCityNpcToggle();
      const pairs = [
        [qmCityNpcSpawnChanceInput, npc.spawn_chance_percent],
        [qmCityNpcMinActiveInput, npc.min_active],
        [qmCityNpcMaxActiveInput, npc.max_active],
        [qmCityNpcOnlineMinInput, npc.online_min_minutes],
        [qmCityNpcOnlineMaxInput, npc.online_max_minutes],
        [qmCityNpcAnswerInput, npc.answer_correct_percent],
        [qmCityNpcStealInput, npc.steal_correct_percent],
        [qmCityNpcInviteInput, npc.invite_chance_percent],
        [qmCityNpcInviteMinInput, npc.invite_cooldown_min_seconds],
        [qmCityNpcInviteMaxInput, npc.invite_cooldown_max_seconds],
      ];
      pairs.forEach(([node, value]) => {{
        if (node && document.activeElement !== node) node.value = String(value);
      }});
      if (qmCityNpcState) {{
        const label = npc.mode === "mixed" ? "Mixed racers + residents" : npc.mode === "city" ? "City residents only" : "Top racers";
        qmCityNpcState.textContent = `${{label}} | spawn ${{npc.spawn_chance_percent}}% | racers ${{npc.min_active}}-${{npc.max_active}} | answer ${{npc.answer_correct_percent}}% | steal ${{npc.steal_correct_percent}}%`;
      }}
      return npc;
    }};
    const defaultQmCitySkins = () => ([
      {{ id: "slime", name: "Slime", price: 35, image: "", description: "A soft crystal slime form with elastic motion." }},
      {{ id: "cloud", name: "Cloud", price: 45, image: "", description: "A floating cloud spirit form with vapor trails." }},
      {{ id: "star-fox", name: "Star Fox", price: 60, image: "", description: "A quick cosmic fox form for bright movement." }},
      {{ id: "crystal-golem", name: "Crystal Golem", price: 80, image: "", description: "A heavy prism golem form with strong crystal armor." }},
      {{ id: "moon-cat", name: "Moon Cat", price: 55, image: "", description: "A quiet moon cat form with soft neon ears." }},
      {{ id: "ember-dragon", name: "Ember Dragon", price: 95, image: "", description: "A small dragon form with ember wings." }},
      {{ id: "aqua-sprite", name: "Aqua Sprite", price: 50, image: "", description: "A water sprite form with flowing blue light." }},
      {{ id: "thunder-cub", name: "Thunder Cub", price: 70, image: "", description: "A storm cub form with electric sparks." }},
      {{ id: "leaf-spirit", name: "Leaf Spirit", price: 42, image: "", description: "A forest spirit form with living leaf marks." }},
      {{ id: "neon-orb", name: "Neon Orb", price: 65, image: "", description: "A clean neon orb form with a hologram core." }},
    ]);
    const normalizeQmCitySkins = (items = []) => {{
      const source = Array.isArray(items) && items.length ? items : defaultQmCitySkins();
      return source.map((item, index) => {{
        const raw = item && typeof item === "object" ? item : {{}};
        const name = String(raw.name || raw.title || `Skin ${{index + 1}}`).trim().slice(0, 80);
        if (!name) return null;
        const id = String(raw.id || name).toLowerCase().replace(/[^a-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 64) || `skin-${{index + 1}}`;
        const price = Math.max(0, Math.min(999999, Math.round(Number(raw.price ?? raw.cost ?? 50) || 0)));
        return {{
          id,
          name,
          price,
          image: String(raw.image || raw.image_url || raw.imageUrl || "").trim().slice(0, 600),
          description: String(raw.description || raw.desc || "").trim().slice(0, 300),
        }};
      }}).filter(Boolean).slice(0, 24);
    }};
    const qmCitySkinsToText = (items = []) => normalizeQmCitySkins(items)
      .map((item) => `${{item.name}}|${{item.price}}|${{item.image || ""}}|${{item.description || ""}}`)
      .join("\\n");
    const qmCitySkinsFromText = (text = "") => normalizeQmCitySkins(
      String(text || "")
        .split(/\\r?\\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line, index) => {{
          const parts = line.split("|");
          return {{
            name: (parts.shift() || `Skin ${{index + 1}}`).trim(),
            price: (parts.shift() || "50").trim(),
            image: (parts.shift() || "").trim(),
            description: parts.join("|").trim(),
          }};
        }})
    );
    const defaultQmCityLevels = () => ([
      {{ level: 1, total_exp: 0 }},
      {{ level: 2, total_exp: 25 }},
      {{ level: 3, total_exp: 75 }},
      {{ level: 4, total_exp: 150 }},
      {{ level: 5, total_exp: 300 }},
      {{ level: 6, total_exp: 500 }},
      {{ level: 7, total_exp: 800 }},
      {{ level: 8, total_exp: 1200 }},
      {{ level: 9, total_exp: 1700 }},
      {{ level: 10, total_exp: 2400 }},
    ]);
    const normalizeQmCityLevels = (items = []) => {{
      const source = Array.isArray(items) && items.length ? items : defaultQmCityLevels();
      const seen = new Set();
      const rows = [];
      source.forEach((item, index) => {{
        const raw = item && typeof item === "object" ? item : {{}};
        let level = Math.round(Number(raw.level ?? raw.lvl ?? (index + 1)) || (index + 1));
        let totalExp = Math.round(Number(raw.total_exp ?? raw.totalExp ?? raw.exp ?? raw.xp ?? 0) || 0);
        level = Math.max(1, Math.min(999, level));
        totalExp = Math.max(0, Math.min(100000000, totalExp));
        if (seen.has(level)) return;
        seen.add(level);
        rows.push({{ level, total_exp: totalExp }});
      }});
      if (!rows.some((row) => row.level === 1)) rows.push({{ level: 1, total_exp: 0 }});
      rows.sort((a, b) => a.level - b.level);
      let previous = 0;
      return rows.slice(0, 100).map((row) => {{
        const totalExp = row.level === 1 ? 0 : Math.max(previous, row.total_exp);
        previous = totalExp;
        return {{ level: row.level, total_exp: totalExp }};
      }});
    }};
    const renderQmCityLevels = (items = []) => {{
      if (!qmCityLevelList) return;
      const rows = normalizeQmCityLevels(items);
      qmCityLevelList.textContent = "";
      const header = document.createElement("div");
      header.className = "level-settings-row is-header";
      header.innerHTML = "<span>Level</span><span>Total EXP</span><span>Action</span>";
      qmCityLevelList.appendChild(header);
      rows.forEach((item) => {{
        const row = document.createElement("div");
        row.className = "level-settings-row";
        row.dataset.levelRow = "1";
        const levelInput = document.createElement("input");
        levelInput.className = "level-settings-input";
        levelInput.type = "number";
        levelInput.min = "1";
        levelInput.max = "999";
        levelInput.step = "1";
        levelInput.value = String(item.level);
        levelInput.dataset.levelField = "level";
        const expInput = document.createElement("input");
        expInput.className = "level-settings-input";
        expInput.type = "number";
        expInput.min = "0";
        expInput.max = "100000000";
        expInput.step = "1";
        expInput.value = String(item.total_exp);
        expInput.dataset.levelField = "total_exp";
        const remove = document.createElement("button");
        remove.className = "level-settings-remove";
        remove.type = "button";
        remove.textContent = item.level === 1 ? "Base" : "Remove";
        remove.disabled = item.level === 1;
        remove.addEventListener("click", () => {{
          row.remove();
          if (qmCityLevelState) qmCityLevelState.textContent = "Unsaved level curve.";
        }});
        [levelInput, expInput].forEach((input) => input.addEventListener("input", () => {{
          if (qmCityLevelState) qmCityLevelState.textContent = "Unsaved level curve.";
        }}));
        row.append(levelInput, expInput, remove);
        qmCityLevelList.appendChild(row);
      }});
    }};
    const collectQmCityLevels = () => normalizeQmCityLevels(
      Array.from(qmCityLevelList ? qmCityLevelList.querySelectorAll(".level-settings-row[data-level-row]") : [])
        .map((row, index) => {{
          const levelInput = row.querySelector('[data-level-field="level"]');
          const expInput = row.querySelector('[data-level-field="total_exp"]');
          return {{
            level: levelInput ? levelInput.value : (index + 1),
            total_exp: expInput ? expInput.value : 0,
          }};
        }})
    );
    const renderCpuGuardToggle = () => {{
      if (!cpuGuardToggle) return;
      cpuGuardToggle.textContent = cpuGuardEnabled ? "CPU Guard On" : "CPU Guard Off";
      cpuGuardToggle.classList.toggle("is-on", cpuGuardEnabled);
      cpuGuardToggle.classList.toggle("is-off", !cpuGuardEnabled);
      cpuGuardToggle.setAttribute("aria-pressed", cpuGuardEnabled ? "true" : "false");
    }};
    const renderSpaceWAiCheckToggle = () => {{
      if (!spaceWAiCheckToggle) return;
      spaceWAiCheckToggle.textContent = spaceWAiCheckVoiceEnabled ? "Whisper On" : "Whisper Off";
      spaceWAiCheckToggle.classList.toggle("is-on", spaceWAiCheckVoiceEnabled);
      spaceWAiCheckToggle.classList.toggle("is-off", !spaceWAiCheckVoiceEnabled);
      spaceWAiCheckToggle.setAttribute("aria-pressed", spaceWAiCheckVoiceEnabled ? "true" : "false");
      spaceWAiCheckToggle.title = spaceWAiCheckVoiceEnabled
        ? "Space_W users may choose server Whisper or browser check."
        : "All Space_W users are forced to browser live voice check.";
    }};
    const normalizeCloudflareHostname = (value) => {{
      const raw = String(value || "").trim();
      if (!raw) return "";
      try {{
        const url = raw.includes("://") ? new URL(raw) : new URL("https://" + raw);
        return String(url.hostname || "").replace(/^\.+|\.+$/g, "").toLowerCase();
      }} catch (error) {{
        return raw.split("/")[0].split("?")[0].split("#")[0].replace(/^\.+|\.+$/g, "").toLowerCase();
      }}
    }};
    const normalizeCloudflareTunnelName = (value) => {{
      return String(value || "future-whisper").trim().replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^[.-]+|[.-]+$/g, "").slice(0, 80) || "future-whisper";
    }};
    const rewardScopes = [
      {{ key: "day", label: "Daily" }},
      {{ key: "week", label: "Weekly" }},
      {{ key: "month", label: "Monthly" }},
      {{ key: "total", label: "Hall" }},
    ];
    const defaultRewardSettings = () => ({{
      day: {{ title: "Daily Champion", claim_window: "Claim during the next day only.", ranks: {{ 1: {{ badge: true, rare: 5, easy: 15, space_q: 3, space_q_silver: 3, space_p: 3, space_p_silver: 3, space_s: 3, space_s_silver: 3, space_w: 3, space_w_silver: 3, space_l: 3, space_l_silver: 3, space_v: 3 }}, 2: {{ badge: false, rare: 3, easy: 10, space_q: 2, space_q_silver: 2, space_p: 2, space_p_silver: 2, space_s: 2, space_s_silver: 2, space_w: 2, space_w_silver: 2, space_l: 2, space_l_silver: 2, space_v: 2 }}, 3: {{ badge: false, rare: 2, easy: 6, space_q: 1, space_q_silver: 1, space_p: 1, space_p_silver: 1, space_s: 1, space_s_silver: 1, space_w: 1, space_w_silver: 1, space_l: 1, space_l_silver: 1, space_v: 1 }} }} }},
      week: {{ title: "Weekly Champion", claim_window: "Claim during the next week only.", ranks: {{ 1: {{ badge: true, rare: 18, easy: 54, space_q: 9, space_q_silver: 9, space_p: 9, space_p_silver: 9, space_s: 9, space_s_silver: 9, space_w: 9, space_w_silver: 9, space_l: 9, space_l_silver: 9, space_v: 9 }}, 2: {{ badge: false, rare: 12, easy: 36, space_q: 6, space_q_silver: 6, space_p: 6, space_p_silver: 6, space_s: 6, space_s_silver: 6, space_w: 6, space_w_silver: 6, space_l: 6, space_l_silver: 6, space_v: 6 }}, 3: {{ badge: false, rare: 8, easy: 24, space_q: 4, space_q_silver: 4, space_p: 4, space_p_silver: 4, space_s: 4, space_s_silver: 4, space_w: 4, space_w_silver: 4, space_l: 4, space_l_silver: 4, space_v: 4 }} }} }},
      month: {{ title: "Monthly Champion", claim_window: "Claim during the next month only.", ranks: {{ 1: {{ badge: true, rare: 60, easy: 180, space_q: 30, space_q_silver: 30, space_p: 30, space_p_silver: 30, space_s: 30, space_s_silver: 30, space_w: 30, space_w_silver: 30, space_l: 30, space_l_silver: 30, space_v: 30 }}, 2: {{ badge: false, rare: 40, easy: 120, space_q: 20, space_q_silver: 20, space_p: 20, space_p_silver: 20, space_s: 20, space_s_silver: 20, space_w: 20, space_w_silver: 20, space_l: 20, space_l_silver: 20, space_v: 20 }}, 3: {{ badge: false, rare: 25, easy: 80, space_q: 12, space_q_silver: 12, space_p: 12, space_p_silver: 12, space_s: 12, space_s_silver: 12, space_w: 12, space_w_silver: 12, space_l: 12, space_l_silver: 12, space_v: 12 }} }} }},
      total: {{ title: "Hall Champion", claim_window: "Honor reward preview for the all-time leaderboard.", ranks: {{ 1: {{ badge: true, rare: 12, easy: 36, space_q: 12, space_q_silver: 12, space_p: 12, space_p_silver: 12, space_s: 12, space_s_silver: 12, space_w: 12, space_w_silver: 12, space_l: 12, space_l_silver: 12, space_v: 12 }}, 2: {{ badge: false, rare: 8, easy: 24, space_q: 8, space_q_silver: 8, space_p: 8, space_p_silver: 8, space_s: 8, space_s_silver: 8, space_w: 8, space_w_silver: 8, space_l: 8, space_l_silver: 8, space_v: 8 }}, 3: {{ badge: false, rare: 5, easy: 16, space_q: 5, space_q_silver: 5, space_p: 5, space_p_silver: 5, space_s: 5, space_s_silver: 5, space_w: 5, space_w_silver: 5, space_l: 5, space_l_silver: 5, space_v: 5 }} }} }},
    }});
    const normalizeRewardSettings = (config = {{}}) => {{
      const defaults = defaultRewardSettings();
      const source = config && typeof config === "object" ? config : {{}};
      const output = {{}};
      rewardScopes.forEach((scope) => {{
        const base = defaults[scope.key];
        const data = source[scope.key] && typeof source[scope.key] === "object" ? source[scope.key] : {{}};
        const ranks = {{}};
        [1, 2, 3].forEach((rank) => {{
          const rawRanks = data.ranks && typeof data.ranks === "object" ? data.ranks : {{}};
          const raw = rawRanks[String(rank)] || rawRanks[rank] || {{}};
          ranks[rank] = {{
            badge: rank === 1 ? Boolean(raw.badge ?? base.ranks[rank].badge) : false,
            rare: Math.max(0, Math.min(9999, Math.round(Number(raw.rare ?? base.ranks[rank].rare) || 0))),
            easy: Math.max(0, Math.min(9999, Math.round(Number(raw.easy ?? base.ranks[rank].easy) || 0))),
            space_q: Math.max(0, Math.min(9999, Math.round(Number(raw.space_q ?? raw.spaceQ ?? base.ranks[rank].space_q) || 0))),
            space_q_silver: Math.max(0, Math.min(9999, Math.round(Number(raw.space_q_silver ?? raw.spaceQSilver ?? base.ranks[rank].space_q_silver) || 0))),
            space_p: Math.max(0, Math.min(9999, Math.round(Number(raw.space_p ?? raw.spaceP ?? base.ranks[rank].space_p) || 0))),
            space_p_silver: Math.max(0, Math.min(9999, Math.round(Number(raw.space_p_silver ?? raw.spacePSilver ?? base.ranks[rank].space_p_silver) || 0))),
            space_s: Math.max(0, Math.min(9999, Math.round(Number(raw.space_s ?? raw.spaceS ?? base.ranks[rank].space_s) || 0))),
            space_s_silver: Math.max(0, Math.min(9999, Math.round(Number(raw.space_s_silver ?? raw.spaceSSilver ?? base.ranks[rank].space_s_silver) || 0))),
            space_w: Math.max(0, Math.min(9999, Math.round(Number(raw.space_w ?? raw.spaceW ?? base.ranks[rank].space_w) || 0))),
            space_w_silver: Math.max(0, Math.min(9999, Math.round(Number(raw.space_w_silver ?? raw.spaceWSilver ?? base.ranks[rank].space_w_silver) || 0))),
            space_l: Math.max(0, Math.min(9999, Math.round(Number(raw.space_l ?? raw.spaceL ?? base.ranks[rank].space_l) || 0))),
            space_l_silver: Math.max(0, Math.min(9999, Math.round(Number(raw.space_l_silver ?? raw.spaceLSilver ?? base.ranks[rank].space_l_silver) || 0))),
            space_v: Math.max(0, Math.min(9999, Math.round(Number(raw.space_v ?? raw.spaceV ?? base.ranks[rank].space_v) || 0))),
          }};
        }});
        output[scope.key] = {{
          title: String(data.title || base.title || scope.label).slice(0, 80),
          claim_window: String(data.claim_window || data.claimWindow || base.claim_window || "").slice(0, 180),
          ranks,
        }};
      }});
      return output;
    }};
    const normalizeLeaderboardReactionSettings = (items = []) => {{
      const source = Array.isArray(items) && items.length
        ? items
        : [
          {{ key: "love", label: "Love", mark: "💕⃝" }},
          {{ key: "burn", label: "Fire heart", mark: "❤️‍🔥" }},
          {{ key: "devil", label: "Mischief", mark: "😈" }},
          {{ key: "frost", label: "Cool", mark: "🥶" }},
        ];
      return source.map((item, index) => {{
        const raw = item && typeof item === "object" ? item : {{ mark: String(item || "") }};
        const mark = String(raw.mark || raw.emoji || "").trim();
        const label = String(raw.label || mark || `Reaction ${{index + 1}}`).trim();
        const keySeed = String(raw.key || label || `reaction-${{index + 1}}`).toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
        return {{ key: keySeed || `reaction-${{index + 1}}`, label: label.slice(0, 48), mark: mark.slice(0, 16) }};
      }}).filter((item) => item.mark).slice(0, 12);
    }};
    const reactionSettingsToText = (items = []) => normalizeLeaderboardReactionSettings(items)
      .map((item) => `${{item.label}}|${{item.mark}}`)
      .join("\\n");
    const reactionSettingsFromText = (text = "") => normalizeLeaderboardReactionSettings(
      String(text || "")
        .split(/\\r?\\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line, index) => {{
          const parts = line.split("|");
          const label = (parts.length > 1 ? parts.shift() : `Reaction ${{index + 1}}`).trim();
          const mark = parts.join("|").trim() || line;
          return {{ label, mark }};
        }})
    );
    const renderRewardSettings = (config = {{}}) => {{
      if (!rewardSettingsGrid) return;
      const rewards = normalizeRewardSettings(config);
      rewardSettingsGrid.innerHTML = "";
      rewardScopes.forEach((scope) => {{
        const data = rewards[scope.key];
        const card = document.createElement("section");
        card.className = "reward-settings-card";
        const title = document.createElement("div");
        title.className = "reward-settings-title";
        title.textContent = `${{scope.label}} rewards`;
        card.appendChild(title);
        const header = document.createElement("div");
        header.className = "reward-settings-row is-header";
        ["Rank", "Rare", "Review", "QG", "QS", "PG", "PS", "SG", "SS", "WG", "WS", "V", "Badge"].forEach((text) => {{
          const cell = document.createElement("span");
          cell.textContent = text;
          header.appendChild(cell);
        }});
        card.appendChild(header);
        const makeRewardInput = (rank, kind, value, label) => {{
          const input = document.createElement("input");
          input.className = "reward-settings-input";
          input.type = "number";
          input.min = "0";
          input.max = "9999";
          input.step = "1";
          input.value = String(value || 0);
          input.dataset.rewardScope = scope.key;
          input.dataset.rewardRank = String(rank);
          input.dataset.rewardKind = kind;
          input.title = label;
          input.setAttribute("aria-label", `${{scope.label}} top ${{rank}} ${{label}}`);
          return input;
        }};
        [1, 2, 3].forEach((rank) => {{
          const row = document.createElement("div");
          row.className = "reward-settings-row";
          const rankLabel = document.createElement("span");
          rankLabel.className = "reward-rank-label";
          rankLabel.textContent = `Top ${{rank}}`;
          const rare = makeRewardInput(rank, "rare", data.ranks[rank].rare, "rare first-learn crystals");
          const easy = makeRewardInput(rank, "easy", data.ranks[rank].easy, "review crystals");
          const spaceQ = makeRewardInput(rank, "space_q", data.ranks[rank].space_q, "Space_Q magic books");
          const spaceQSilver = makeRewardInput(rank, "space_q_silver", data.ranks[rank].space_q_silver, "Space_Q silver magic books");
          const spaceP = makeRewardInput(rank, "space_p", data.ranks[rank].space_p, "Space_P magic bows");
          const spacePSilver = makeRewardInput(rank, "space_p_silver", data.ranks[rank].space_p_silver, "Space_P silver magic bows");
          const spaceS = makeRewardInput(rank, "space_s", data.ranks[rank].space_s, "Space_S golden devil wings");
          const spaceSSilver = makeRewardInput(rank, "space_s_silver", data.ranks[rank].space_s_silver, "Space_S silver devil wings");
          const spaceW = makeRewardInput(rank, "space_w", data.ranks[rank].space_w, "Space_W golden mastery cups");
          const spaceWSilver = makeRewardInput(rank, "space_w_silver", data.ranks[rank].space_w_silver, "Space_W silver practice cups");
          const spaceL = makeRewardInput(rank, "space_l", data.ranks[rank].space_l, "Space_L golden great swords");
          const spaceLSilver = makeRewardInput(rank, "space_l_silver", data.ranks[rank].space_l_silver, "Space_L silver great swords");
          const spaceV = makeRewardInput(rank, "space_v", data.ranks[rank].space_v, "Space_V common crystals");
          const badge = document.createElement("span");
          badge.className = "reward-badge-label";
          badge.textContent = rank === 1 ? "Badge" : "No badge";
          row.append(rankLabel, rare, easy, spaceQ, spaceQSilver, spaceP, spacePSilver, spaceS, spaceSSilver, spaceW, spaceWSilver, spaceL, spaceLSilver, spaceV, badge);
          card.appendChild(row);
        }});
        rewardSettingsGrid.appendChild(card);
      }});
    }};
    const collectRewardSettings = () => {{
      const rewards = normalizeRewardSettings();
      if (!rewardSettingsGrid) return rewards;
      Array.from(rewardSettingsGrid.querySelectorAll("[data-reward-scope]")).forEach((input) => {{
        const scope = input.dataset.rewardScope;
        const rank = input.dataset.rewardRank;
        const kind = input.dataset.rewardKind;
        if (!rewards[scope] || !rewards[scope].ranks[rank]) return;
        rewards[scope].ranks[rank][kind] = Math.max(0, Math.min(9999, Math.round(Number(input.value || 0) || 0)));
      }});
      rewardScopes.forEach((scope) => {{
        if (rewards[scope.key] && rewards[scope.key].ranks) {{
          rewards[scope.key].ranks[1].badge = true;
          rewards[scope.key].ranks[2].badge = false;
          rewards[scope.key].ranks[3].badge = false;
        }}
      }});
      return rewards;
    }};
    let qmdictStatusTimer = 0;
    const scheduleQmDictStatusPoll = () => {{
      if (qmdictStatusTimer) {{
        window.clearTimeout(qmdictStatusTimer);
      }}
      qmdictStatusTimer = window.setTimeout(() => {{
        qmdictStatusTimer = 0;
        void loadQmDictStatus();
      }}, 2200);
    }};
    const renderQmDictStatus = (reload = {{}}, audio = {{}}, repair = {{}}, wordAudio = {{}}) => {{
      if (!qmdictReloadState) return;
      const entries = Number(reload.entries || 0);
      const loadedAt = String(reload.loaded_at || "");
      const running = Boolean(audio && audio.running);
      const scheduled = Boolean(audio && audio.scheduled);
      const wordAudioRunning = Boolean(wordAudio && wordAudio.running);
      const wordAudioTotal = Number(wordAudio && wordAudio.total || 0) || 0;
      const wordAudioDone = Number(wordAudio && wordAudio.done || 0) || 0;
      const wordAudioRefreshed = Number(wordAudio && wordAudio.refreshed || 0) || 0;
      const wordAudioFailed = Number(wordAudio && wordAudio.failed || 0) || 0;
      const wordAudioWorkers = Number(wordAudio && wordAudio.workers || 0) || 0;
      const wordAudioLast = String(wordAudio && wordAudio.last_word || "");
      const wordAudioVoice = String(wordAudio && wordAudio.last_voice || "");
      const repairRunning = Boolean(repair && repair.running);
      const repairTotal = Number(repair && repair.total || 0) || 0;
      const repairDone = Number(repair && repair.done || 0) || 0;
      const repairChanged = Number(repair && repair.changed || 0) || 0;
      const repairAudioChanged = Number(repair && repair.audio_changed || 0) || 0;
      const repairFailed = Number(repair && repair.failed || 0) || 0;
      const phase = String(audio && audio.phase || "");
      const scanTotal = Number(audio && audio.scan_total || 0) || 0;
      const scanDone = Number(audio && audio.scan_done || 0) || 0;
      const workers = Number(audio && audio.workers || 0) || 0;
      const cleanupTotal = Number(audio && audio.cleanup_total || 0) || 0;
      const cleanupDone = Number(audio && audio.cleanup_done || 0) || 0;
      const cleanupDeleted = Number(audio && audio.cleanup_deleted || 0) || 0;
      const total = Number(audio && audio.total || 0) || 0;
      const done = Number(audio && audio.done || 0) || 0;
      const cached = Number(audio && audio.cached || 0) || 0;
      const missing = Number(audio && audio.missing || 0) || 0;
      const downloaded = Number(audio && audio.downloaded || 0) || 0;
      const failed = Number(audio && audio.failed || 0) || 0;
      const activeTotal = phase === "scanning" ? scanTotal : phase === "cleaning" ? cleanupTotal : total;
      const activeDone = phase === "scanning" ? scanDone : phase === "cleaning" ? cleanupDone : done;
      const audioPercent = activeTotal > 0 ? Math.max(0, Math.min(100, Math.round((activeDone / activeTotal) * 100))) : (running ? 1 : 0);
      const repairPercent = repairTotal > 0 ? Math.max(0, Math.min(100, Math.round((repairDone / repairTotal) * 100))) : (repairRunning ? 1 : 0);
      const wordAudioPercent = wordAudioTotal > 0 ? Math.max(0, Math.min(100, Math.round((wordAudioDone / wordAudioTotal) * 100))) : (wordAudioRunning ? 1 : 0);
      const percent = wordAudioRunning ? wordAudioPercent : repairRunning ? repairPercent : audioPercent;
      const runningCopy = scheduled
        ? " | audio scan scheduled..."
        : phase === "scanning"
        ? " | checking local Vietnamese audio..."
        : phase === "cleaning"
          ? " | deleting orphan Vietnamese audio..."
          : phase === "downloading"
            ? " | downloading missing Vietnamese audio..."
            : " | Vietnamese audio refreshing...";
      const repairCopy = repairRunning
        ? ` | repairing Space_V ${{repairDone}}/${{repairTotal || "..."}}`
        : repairTotal
          ? ` | Space_V repaired ${{repairDone}}/${{repairTotal}} | audio ${{repairAudioChanged}} | failed ${{repairFailed}}`
          : "";
      const wordAudioCopy = wordAudioRunning
        ? ` | refreshing UK/US audio ${{wordAudioDone}}/${{wordAudioTotal || "..."}}`
        : wordAudioTotal
          ? ` | UK/US audio refreshed ${{wordAudioRefreshed}}/${{wordAudioTotal}} | failed ${{wordAudioFailed}}`
          : "";
      qmdictReloadState.textContent = `QmDict ${{entries || "unknown"}} entries${{loadedAt ? ` | loaded ${{loadedAt}}` : ""}}${{wordAudioCopy}}${{running || scheduled ? runningCopy : ""}}${{repairCopy}}`;
      if (qmdictAudioProgress) {{
        const shouldShow = wordAudioRunning || wordAudioTotal > 0 || String(wordAudio && wordAudio.completed_at || "") || repairRunning || running || scheduled || repairTotal > 0 || total > 0 || String(audio && audio.completed_at || "");
        qmdictAudioProgress.hidden = !shouldShow;
        qmdictAudioProgress.classList.toggle("is-running", wordAudioRunning || repairRunning || running || scheduled);
        qmdictAudioProgress.style.setProperty("--qmdict-audio-progress", `${{percent}}%`);
      }}
      if (qmdictAudioProgressFill) {{
        qmdictAudioProgressFill.style.width = `${{percent}}%`;
      }}
      if (qmdictAudioProgressCopy) {{
        const last = String(audio && audio.last_meaning || "");
        const wordLastCopy = wordAudioLast ? ` | ${{wordAudioLast}}${{wordAudioVoice ? ` (${{wordAudioVoice}})` : ""}}` : "";
        const status = wordAudioRunning
          ? `Refreshing QmDict UK/US audio: ${{wordAudioDone}}/${{wordAudioTotal || "..."}} (${{percent}}%) | workers ${{wordAudioWorkers || "..."}} | refreshed ${{wordAudioRefreshed}} | failed ${{wordAudioFailed}}${{wordLastCopy}}`
          : wordAudioTotal > 0
            ? `QmDict UK/US audio ready: refreshed ${{wordAudioRefreshed}}/${{wordAudioTotal}} | failed ${{wordAudioFailed}}${{wordLastCopy}}`
            : scheduled
          ? "QmDict reloaded. Audio scan will start in the background."
          : repairRunning
            ? `Repairing Space_V audio links: ${{repairDone}}/${{repairTotal || "..."}} | changed ${{repairChanged}} | audio ${{repairAudioChanged}} | failed ${{repairFailed}}`
          : running
          ? phase === "scanning"
            ? `Checking local audio: ${{scanDone}}/${{scanTotal || "..."}} (${{percent}}%) | cached ${{cached}} | missing ${{missing}}${{last ? ` | ${{last}}` : ""}}`
            : phase === "cleaning"
              ? `Cleaning orphan Vietnamese audio: ${{cleanupDone}}/${{cleanupTotal || "..."}} (${{percent}}%) | deleted ${{cleanupDeleted}}`
              : `Downloading missing audio: ${{done}}/${{total || "..."}} (${{percent}}%) | workers ${{workers || "..."}} | scanned ${{scanDone}} | cached ${{cached}} | missing ${{missing}} | downloaded ${{downloaded}} | failed ${{failed}}${{last ? ` | ${{last}}` : ""}}`
          : scanTotal > 0
            ? `Vietnamese audio ready: scanned ${{scanTotal}} | cached ${{cached}} | missing ${{missing}} | downloaded ${{downloaded}} | failed ${{failed}} | deleted orphan ${{cleanupDeleted}}`
            : "Vietnamese audio refresh is idle.";
        qmdictAudioProgressCopy.textContent = status;
      }}
      if (wordAudioRunning || running || scheduled || repairRunning) {{
        scheduleQmDictStatusPoll();
      }}
    }};
    const loadQmDictStatus = async () => {{
      try {{
        const response = await fetch("/qmdict/reload-status?ts=" + Date.now(), {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not load QmDict status.");
        }}
        renderQmDictStatus(payload.qmdict_reload || {{}}, payload.qmdict_audio_refresh || {{}}, payload.space_v_repair || {{}}, payload.qmdict_word_audio_refresh || {{}});
      }} catch (error) {{
        if (qmdictReloadState) qmdictReloadState.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const loadSettings = async () => {{
      try {{
        const response = await fetch("/settings?ts=" + Date.now(), {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Khong tai duoc settings.");
        }}
        const seconds = normalizeHintSeconds(payload.word_hint_cycle_seconds);
        if (hintCycleInput && document.activeElement !== hintCycleInput) {{
          hintCycleInput.value = String(seconds);
        }}
        const paragraphSeconds = normalizeParagraphHintSeconds(payload.paragraph_hint_seconds);
        if (paragraphHintInput && document.activeElement !== paragraphHintInput) {{
          paragraphHintInput.value = String(paragraphSeconds);
        }}
        if (questionHudInput && document.activeElement !== questionHudInput) {{
          const lines = Array.isArray(payload.question_hud_lines) ? payload.question_hud_lines : [];
          questionHudInput.value = lines.length ? lines.join("\\n") : String(payload.question_hud_text || "");
        }}
        const chatLimitMb = normalizeChatAttachmentLimitMb(payload.chat_attachment_limit_mb);
        if (chatAttachmentLimitInput && document.activeElement !== chatAttachmentLimitInput) {{
          chatAttachmentLimitInput.value = String(chatLimitMb);
        }}
        const heavyUserQuota = normalizeHeavyUserQuota(payload.heavy_user_quota_per_minute);
        if (heavyUserQuotaInput && document.activeElement !== heavyUserQuotaInput) {{
          heavyUserQuotaInput.value = String(heavyUserQuota);
        }}
        const heavyUserInterval = normalizeHeavyUserInterval(payload.heavy_user_min_interval_seconds);
        if (heavyUserIntervalInput && document.activeElement !== heavyUserIntervalInput) {{
          heavyUserIntervalInput.value = String(heavyUserInterval);
        }}
        if (aiAgentNoticeVoiceInput && document.activeElement !== aiAgentNoticeVoiceInput) {{
          aiAgentNoticeVoiceInput.value = String(payload.ai_agent_notice_voice || "kokoro:am_michael");
        }}
        spaceWAiCheckVoiceEnabled = payload.space_w_ai_check_voice_enabled !== false;
        renderSpaceWAiCheckToggle();
        if (leaderboardReactionsInput && document.activeElement !== leaderboardReactionsInput) {{
          leaderboardReactionsInput.value = reactionSettingsToText(payload.leaderboard_reactions || []);
        }}
        const cpuThreshold = normalizeCpuThreshold(payload.cpu_queue_threshold_percent);
        cpuGuardEnabled = payload.cpu_guard_enabled !== false;
        if (cpuThresholdInput && document.activeElement !== cpuThresholdInput) {{
          cpuThresholdInput.value = String(cpuThreshold);
        }}
        renderCpuGuardToggle();
        renderWorkerJobLimitInputs(payload.distributed_worker_job_limits || {{}});
        renderWorkerMachineLimitInput(payload.distributed_worker_machine_limit);
        const cfHostname = normalizeCloudflareHostname(payload.cloudflare_public_hostname || "");
        if (cloudflareHostnameInput && document.activeElement !== cloudflareHostnameInput) {{
          cloudflareHostnameInput.value = cfHostname;
        }}
        const cfTunnelName = normalizeCloudflareTunnelName(payload.cloudflare_tunnel_name || "future-whisper");
        if (cloudflareTunnelNameInput && document.activeElement !== cloudflareTunnelNameInput) {{
          cloudflareTunnelNameInput.value = cfTunnelName;
        }}
        if (hostedClientSecretInput && document.activeElement !== hostedClientSecretInput) {{
          hostedClientSecretInput.value = "";
          hostedClientSecretInput.placeholder = payload.hosted_client_secret_set
            ? "Password key is set. Type a new one to rotate."
            : "No password key set. Type one to enable.";
        }}
        renderQmDictStatus(payload.qmdict_reload || {{}}, payload.qmdict_audio_refresh || {{}}, payload.space_v_repair || {{}}, payload.qmdict_word_audio_refresh || {{}});
        if (!rewardSettingsGrid || !rewardSettingsGrid.contains(document.activeElement)) {{
          renderRewardSettings(payload.leaderboard_rewards || {{}});
        }}
        const qmCityPercent = normalizeQmCityPercent(payload.qm_city_chat_min_english_percent);
        if (qmCityMinEnglishInput && document.activeElement !== qmCityMinEnglishInput) {{
          qmCityMinEnglishInput.value = String(qmCityPercent);
        }}
        const qmCityRun = normalizeQmCityInvalidRun(payload.qm_city_chat_invalid_run_limit);
        if (qmCityInvalidRunInput && document.activeElement !== qmCityInvalidRunInput) {{
          qmCityInvalidRunInput.value = String(qmCityRun);
        }}
        const qmCitySkins = normalizeQmCitySkins(payload.qm_city_skins || []);
        if (qmCitySkinsInput && document.activeElement !== qmCitySkinsInput) {{
          qmCitySkinsInput.value = qmCitySkinsToText(qmCitySkins);
        }}
        renderQmCityNpcSettings(payload.qm_city_npc || {{}});
        const qmCityLevels = normalizeQmCityLevels(payload.qm_city_levels || []);
        if (qmCityLevelList && !qmCityLevelList.contains(document.activeElement)) {{
          renderQmCityLevels(qmCityLevels);
        }}
        if (qmCityState) {{
          qmCityState.textContent = payload.updated_at
            ? `Loaded: ${{payload.updated_at}} | English ${{qmCityPercent}}% | invalid run ${{qmCityRun}} | skins ${{qmCitySkins.length}}`
            : `Default: English ${{qmCityPercent}}% | invalid run ${{qmCityRun}} | skins ${{qmCitySkins.length}}`;
        }}
        if (qmCityLevelState) {{
          qmCityLevelState.textContent = payload.updated_at
            ? `Loaded: ${{payload.updated_at}} | levels ${{qmCityLevels.length}}`
            : `Default level curve | levels ${{qmCityLevels.length}}`;
        }}
        if (rewardSettingsState) rewardSettingsState.textContent = payload.updated_at ? `Loaded: ${{payload.updated_at}}` : "Default rewards.";
        const obfState = payload.hosted_client_secret_set ? "client key set" : "default client key";
        const cfState = cfHostname ? `domain ${{cfHostname}} via ${{cfTunnelName}}` : "quick trycloudflare link";
        const cpuState = `${{cpuGuardEnabled ? "CPU guard" : "CPU guard off"}} ${{cpuThreshold}}%`;
        const speakState = spaceWAiCheckVoiceEnabled ? "Space_W Whisper on" : "Space_W browser check";
        if (settingsState) {{
          settingsState.textContent = payload.updated_at
            ? `Saved: ${{payload.updated_at}} | W ${{seconds}}s | P ${{paragraphSeconds}}s | chat ${{chatLimitMb}} MB | AI ${{payload.ai_agent_notice_voice || "kokoro:am_michael"}} | ${{speakState}} | ${{cpuState}} | ${{cfState}} | ${{obfState}}`
            : `Default: W ${{seconds}}s | P ${{paragraphSeconds}}s | chat ${{chatLimitMb}} MB | AI ${{payload.ai_agent_notice_voice || "kokoro:am_michael"}} | ${{speakState}} | ${{cpuState}} | ${{cfState}} | ${{obfState}}`;
        }}
      }} catch (error) {{
        if (settingsState) {{
          settingsState.textContent = String(error && error.message ? error.message : error);
        }}
      }}
    }};
    if (hintCycleInput) {{
      hintCycleInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved.";
      }});
    }}
    if (paragraphHintInput) {{
      paragraphHintInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved.";
      }});
    }}
    if (questionHudInput) {{
      questionHudInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved.";
      }});
    }}
    if (chatAttachmentLimitInput) {{
      chatAttachmentLimitInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved.";
      }});
    }}
    if (aiAgentNoticeVoiceInput) {{
      aiAgentNoticeVoiceInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved AI Agent voice.";
      }});
    }}
    if (spaceWAiCheckToggle) {{
      spaceWAiCheckToggle.addEventListener("click", () => {{
        spaceWAiCheckVoiceEnabled = !spaceWAiCheckVoiceEnabled;
        renderSpaceWAiCheckToggle();
        if (settingsState) settingsState.textContent = "Saving Space_W Speak scoring source...";
        if (settingsSave && !settingsSave.disabled) {{
          settingsSave.click();
        }} else if (settingsState) {{
          settingsState.textContent = "Unsaved Space_W Speak scoring source.";
        }}
      }});
    }}
    if (leaderboardReactionsInput) {{
      leaderboardReactionsInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved leaderboard reactions.";
      }});
    }}
    const applyCpuGuardLimit = async () => {{
      if (cpuGuardApply) cpuGuardApply.disabled = true;
      if (settingsState) settingsState.textContent = "Applying CPU guard...";
      try {{
        const cpuThreshold = normalizeCpuThreshold(cpuThresholdInput ? cpuThresholdInput.value : 90);
        const response = await fetch("/settings", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            cpu_guard_enabled: Boolean(cpuGuardEnabled),
            cpu_queue_threshold_percent: cpuThreshold,
          }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not apply CPU guard.");
        }}
        cpuGuardEnabled = payload.cpu_guard_enabled !== false;
        const savedCpuThreshold = normalizeCpuThreshold(payload.cpu_queue_threshold_percent);
        if (cpuThresholdInput) cpuThresholdInput.value = String(savedCpuThreshold);
        renderCpuGuardToggle();
        if (settingsState) {{
          settingsState.textContent = `${{cpuGuardEnabled ? "CPU guard enabled" : "CPU guard disabled"}} at ${{savedCpuThreshold}}%.`;
        }}
      }} catch (error) {{
        if (settingsState) settingsState.textContent = String(error && error.message ? error.message : error);
      }} finally {{
        if (cpuGuardApply) cpuGuardApply.disabled = false;
      }}
    }};
    if (cpuThresholdInput) {{
      cpuThresholdInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved CPU guard.";
      }});
      cpuThresholdInput.addEventListener("blur", () => {{
        cpuThresholdInput.value = String(normalizeCpuThreshold(cpuThresholdInput.value));
      }});
    }}
    if (cpuGuardToggle) {{
      cpuGuardToggle.addEventListener("click", () => {{
        cpuGuardEnabled = !cpuGuardEnabled;
        renderCpuGuardToggle();
        if (settingsState) settingsState.textContent = "Unsaved CPU guard.";
      }});
    }}
    if (cpuGuardApply) {{
      cpuGuardApply.addEventListener("click", () => void applyCpuGuardLimit());
    }}
    if (distributedWorkerLimitSave) {{
      distributedWorkerLimitSave.addEventListener("click", async () => {{
        distributedWorkerLimitSave.disabled = true;
        if (distributedWorkerState) distributedWorkerState.textContent = "Saving worker limits...";
        try {{
          const limits = normalizeWorkerJobLimits({{
            translate: distributedWorkerLimitTranslate ? distributedWorkerLimitTranslate.value : 8,
            tts: distributedWorkerLimitTts ? distributedWorkerLimitTts.value : 4,
            stt: distributedWorkerLimitStt ? distributedWorkerLimitStt.value : 4,
            gemini: distributedWorkerLimitGemini ? distributedWorkerLimitGemini.value : 8,
            phonemize: distributedWorkerLimitPhonemize ? distributedWorkerLimitPhonemize.value : 8,
          }});
          const machineLimit = normalizeWorkerMachineLimit(distributedWorkerMachineLimit ? distributedWorkerMachineLimit.value : 1);
          const response = await fetch("/settings", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              distributed_worker_job_limits: limits,
              distributed_worker_machine_limit: machineLimit,
            }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not save worker limits.");
          }}
          renderWorkerJobLimitInputs(payload.distributed_worker_job_limits || limits);
          renderWorkerMachineLimitInput(payload.distributed_worker_machine_limit || machineLimit);
          if (distributedWorkerState) distributedWorkerState.textContent = "Worker limits saved.";
        }} catch (error) {{
          if (distributedWorkerState) distributedWorkerState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          distributedWorkerLimitSave.disabled = false;
        }}
      }});
    }}
    const startQmDictWordAudioRefresh = async (mode = "all", button = null) => {{
      if (button) button.disabled = true;
      if (qmdictReloadState) {{
        qmdictReloadState.textContent = mode === "failed"
          ? "Retrying failed QmDict UK/US audio..."
          : "Refreshing all QmDict UK/US audio...";
      }}
      try {{
        const response = await fetch("/qmdict/word-audio-refresh", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ mode }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not start QmDict UK/US audio refresh.");
        }}
        renderQmDictStatus({{}}, {{}}, {{}}, payload.word_audio_refresh || {{}});
        scheduleQmDictStatusPoll();
      }} catch (error) {{
        if (qmdictReloadState) qmdictReloadState.textContent = String(error && error.message ? error.message : error);
      }} finally {{
        if (button) button.disabled = false;
      }}
    }};
    const startQmDictMeaningAudioRefresh = async (button = null) => {{
      if (button) button.disabled = true;
      if (qmdictReloadState) {{
        qmdictReloadState.textContent = "Refreshing QmDict Vietnamese SOT audio...";
      }}
      try {{
        const response = await fetch("/qmdict/meaning-audio-refresh", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ mode: "dashboard-vietnamese-sot-refresh" }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not start Vietnamese SOT audio refresh.");
        }}
        renderQmDictStatus({{}}, payload.audio_refresh || {{}}, {{}}, payload.qmdict_word_audio_refresh || {{}});
        scheduleQmDictStatusPoll();
      }} catch (error) {{
        if (qmdictReloadState) qmdictReloadState.textContent = String(error && error.message ? error.message : error);
      }} finally {{
        if (button) button.disabled = false;
      }}
    }};
    if (qmdictReload) {{
      qmdictReload.addEventListener("click", async () => {{
        qmdictReload.disabled = true;
        if (qmdictReloadState) qmdictReloadState.textContent = "Reloading QmDict...";
        try {{
          const response = await fetch("/qmdict/reload", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{}}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not reload QmDict.");
          }}
          renderQmDictStatus(payload.qmdict_reload || {{}}, payload.audio_refresh || {{}}, payload.space_v_repair || {{}}, payload.qmdict_word_audio_refresh || {{}});
        }} catch (error) {{
          if (qmdictReloadState) qmdictReloadState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          qmdictReload.disabled = false;
        }}
      }});
    }}
    if (spaceVRepair) {{
      spaceVRepair.addEventListener("click", async () => {{
        spaceVRepair.disabled = true;
        if (qmdictReloadState) qmdictReloadState.textContent = "Repairing Space_V audio links...";
        try {{
          const response = await fetch("/space-v/repair-qmdict", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{}}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not repair Space_V files.");
          }}
          renderQmDictStatus({{}}, {{}}, payload.repair || {{}}, payload.qmdict_word_audio_refresh || {{}});
        }} catch (error) {{
          if (qmdictReloadState) qmdictReloadState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          spaceVRepair.disabled = false;
        }}
      }});
    }}
    if (qmdictMeaningAudioRefresh) {{
      qmdictMeaningAudioRefresh.addEventListener("click", () => void startQmDictMeaningAudioRefresh(qmdictMeaningAudioRefresh));
    }}
    if (qmdictWordAudioRefresh) {{
      qmdictWordAudioRefresh.addEventListener("click", () => void startQmDictWordAudioRefresh("all", qmdictWordAudioRefresh));
    }}
    if (qmdictWordAudioRetry) {{
      qmdictWordAudioRetry.addEventListener("click", () => void startQmDictWordAudioRefresh("failed", qmdictWordAudioRetry));
    }}
    if (serverDataManifestRefresh) {{
      serverDataManifestRefresh.addEventListener("click", async () => {{
        serverDataManifestRefresh.disabled = true;
        if (serverDataManifestState) serverDataManifestState.textContent = "Refreshing Lesson Vault manifest...";
        try {{
          const response = await fetch("/server-data/manifest-refresh", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{}}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not refresh manifest.");
          }}
          const entries = Number(payload.entry_count || 0);
          const folders = Number(payload.folder_count || 0);
          try {{
            localStorage.setItem("future_server_data_manifest_refreshed_at", String(Date.now()));
            if (payload.signature) localStorage.setItem("future_server_data_manifest_signature", String(payload.signature));
          }} catch (error) {{}}
          if (serverDataManifestState) {{
            serverDataManifestState.textContent = `Manifest refreshed: ${{entries.toLocaleString()}} items in ${{folders.toLocaleString()}} folders.`;
          }}
        }} catch (error) {{
          if (serverDataManifestState) serverDataManifestState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          serverDataManifestRefresh.disabled = false;
        }}
      }});
    }}
    if (cloudflareHostnameInput) {{
      cloudflareHostnameInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved Cloudflare domain.";
      }});
      cloudflareHostnameInput.addEventListener("blur", () => {{
        cloudflareHostnameInput.value = normalizeCloudflareHostname(cloudflareHostnameInput.value);
      }});
    }}
    if (cloudflareTunnelNameInput) {{
      cloudflareTunnelNameInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = "Unsaved Cloudflare tunnel.";
      }});
      cloudflareTunnelNameInput.addEventListener("blur", () => {{
        cloudflareTunnelNameInput.value = normalizeCloudflareTunnelName(cloudflareTunnelNameInput.value);
      }});
    }}
    if (hostedClientSecretInput) {{
      hostedClientSecretInput.addEventListener("input", () => {{
        if (settingsState) settingsState.textContent = hostedClientSecretInput.value
          ? "Unsaved obfuscation password."
          : "Unsaved.";
      }});
    }}
    if (rewardSettingsGrid) {{
      rewardSettingsGrid.addEventListener("input", () => {{
        if (rewardSettingsState) rewardSettingsState.textContent = "Unsaved reward settings.";
      }});
    }}
    [qmCityMinEnglishInput, qmCityInvalidRunInput, qmCitySkinsInput].forEach((node) => {{
      if (!node) return;
      node.addEventListener("input", () => {{
        if (qmCityState) qmCityState.textContent = "Unsaved QM-City settings.";
      }});
    }});
    if (qmCityMinEnglishInput) {{
      qmCityMinEnglishInput.addEventListener("blur", () => {{
        qmCityMinEnglishInput.value = String(normalizeQmCityPercent(qmCityMinEnglishInput.value));
      }});
    }}
    if (qmCityInvalidRunInput) {{
      qmCityInvalidRunInput.addEventListener("blur", () => {{
        qmCityInvalidRunInput.value = String(normalizeQmCityInvalidRun(qmCityInvalidRunInput.value));
      }});
    }}
    const saveQmCityNpcSettings = async (reason = "manual") => {{
      if (qmCityNpcSave) qmCityNpcSave.disabled = true;
      if (qmCityNpcEnabledToggle) qmCityNpcEnabledToggle.disabled = true;
      if (qmCityNpcMixToggle) qmCityNpcMixToggle.disabled = true;
      if (qmCityNpcState) qmCityNpcState.textContent = reason === "toggle"
        ? `Saving QM-City NPC mode ${{qmCityNpcMode}}...`
        : "Saving NPC city settings...";
      try {{
        const npc = collectQmCityNpcSettings();
        const response = await fetch("/settings", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ qm_city_npc: npc }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not save NPC city settings.");
        }}
        const savedNpc = renderQmCityNpcSettings(payload.qm_city_npc || npc);
        if (qmCityNpcState) {{
          const sync = payload.qm_city_npc_mode_sync || payload.qmCityNpcModeSync || {{}};
          const scheduled = Number(sync.scheduled_retire || sync.scheduledRetire || 0) || 0;
          const cleared = Number(sync.cleared_retire || sync.clearedRetire || 0) || 0;
          const removed = Number(sync.removed || 0) || 0;
          const label = savedNpc.mode === "mixed" ? "Mixed racers + residents" : savedNpc.mode === "city" ? "City residents only" : "Top racers";
          const suffix = scheduled || cleared || removed ? ` | removed ${{removed}} | retire scheduled ${{scheduled}} | restored ${{cleared}}` : "";
          qmCityNpcState.textContent = `Saved: ${{payload.updated_at || "now"}} | ${{label}} | spawn ${{savedNpc.spawn_chance_percent}}% | racers ${{savedNpc.min_active}}-${{savedNpc.max_active}} | answer ${{savedNpc.answer_correct_percent}}% | steal ${{savedNpc.steal_correct_percent}}%${{suffix}}`;
        }}
        return savedNpc;
      }} catch (error) {{
        if (qmCityNpcState) qmCityNpcState.textContent = String(error && error.message ? error.message : error);
        throw error;
      }} finally {{
        if (qmCityNpcSave) qmCityNpcSave.disabled = false;
        if (qmCityNpcEnabledToggle) qmCityNpcEnabledToggle.disabled = false;
        if (qmCityNpcMixToggle) qmCityNpcMixToggle.disabled = false;
      }}
    }};
    if (qmCityNpcEnabledToggle) {{
      qmCityNpcEnabledToggle.addEventListener("click", () => {{
        qmCityNpcMode = qmCityNpcMode === "city" ? "top" : "city";
        qmCityNpcEnabled = qmCityNpcMode !== "city";
        renderQmCityNpcToggle();
        void saveQmCityNpcSettings("toggle").catch(() => {{}});
      }});
    }}
    if (qmCityNpcMixToggle) {{
      qmCityNpcMixToggle.addEventListener("click", () => {{
        qmCityNpcMode = "mixed";
        qmCityNpcEnabled = true;
        renderQmCityNpcToggle();
        void saveQmCityNpcSettings("toggle").catch(() => {{}});
      }});
    }}
    [qmCityNpcSpawnChanceInput, qmCityNpcMinActiveInput, qmCityNpcMaxActiveInput, qmCityNpcOnlineMinInput, qmCityNpcOnlineMaxInput, qmCityNpcAnswerInput, qmCityNpcStealInput, qmCityNpcInviteInput, qmCityNpcInviteMinInput, qmCityNpcInviteMaxInput].forEach((node) => {{
      if (!node) return;
      node.addEventListener("input", () => {{
        if (qmCityNpcState) qmCityNpcState.textContent = "Unsaved NPC city settings.";
      }});
      node.addEventListener("blur", () => renderQmCityNpcSettings(collectQmCityNpcSettings()));
    }});
    if (qmCityNpcSave) {{
      qmCityNpcSave.addEventListener("click", async () => {{
        await saveQmCityNpcSettings("manual").catch(() => {{}});
      }});
    }}
    if (qmCitySave) {{
      qmCitySave.addEventListener("click", async () => {{
        qmCitySave.disabled = true;
        if (qmCityState) qmCityState.textContent = "Saving QM-City settings...";
        try {{
          const percent = normalizeQmCityPercent(qmCityMinEnglishInput ? qmCityMinEnglishInput.value : 50);
          const invalidRun = normalizeQmCityInvalidRun(qmCityInvalidRunInput ? qmCityInvalidRunInput.value : 4);
          const skins = qmCitySkinsFromText(qmCitySkinsInput ? qmCitySkinsInput.value : "");
          const response = await fetch("/settings", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              qm_city_chat_min_english_percent: percent,
              qm_city_chat_invalid_run_limit: invalidRun,
              qm_city_skins: skins,
            }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not save QM-City settings.");
          }}
          const savedPercent = normalizeQmCityPercent(payload.qm_city_chat_min_english_percent);
          const savedRun = normalizeQmCityInvalidRun(payload.qm_city_chat_invalid_run_limit);
          const savedSkins = normalizeQmCitySkins(payload.qm_city_skins || skins);
          if (qmCityMinEnglishInput) qmCityMinEnglishInput.value = String(savedPercent);
          if (qmCityInvalidRunInput) qmCityInvalidRunInput.value = String(savedRun);
          if (qmCitySkinsInput) qmCitySkinsInput.value = qmCitySkinsToText(savedSkins);
          if (qmCityState) qmCityState.textContent = `Saved: ${{payload.updated_at || "now"}} | English ${{savedPercent}}% | invalid run ${{savedRun}} | skins ${{savedSkins.length}}`;
        }} catch (error) {{
          if (qmCityState) qmCityState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          qmCitySave.disabled = false;
        }}
      }});
    }}
    if (qmCityLevelAdd) {{
      qmCityLevelAdd.addEventListener("click", () => {{
        const rows = collectQmCityLevels();
        const last = rows[rows.length - 1] || {{ level: 1, total_exp: 0 }};
        const nextLevel = Math.min(999, Math.max(2, Number(last.level || 1) + 1));
        const previousStep = rows.length >= 2
          ? Math.max(25, Number(last.total_exp || 0) - Number(rows[rows.length - 2].total_exp || 0))
          : 25;
        rows.push({{ level: nextLevel, total_exp: Number(last.total_exp || 0) + previousStep }});
        renderQmCityLevels(rows);
        if (qmCityLevelState) qmCityLevelState.textContent = "Unsaved level curve.";
      }});
    }}
    if (qmCityLevelSave) {{
      qmCityLevelSave.addEventListener("click", async () => {{
        qmCityLevelSave.disabled = true;
        if (qmCityLevelState) qmCityLevelState.textContent = "Saving level curve...";
        try {{
          const levels = collectQmCityLevels();
          const response = await fetch("/settings", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ qm_city_levels: levels }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not save QM-City levels.");
          }}
          const savedLevels = normalizeQmCityLevels(payload.qm_city_levels || levels);
          renderQmCityLevels(savedLevels);
          if (qmCityLevelState) qmCityLevelState.textContent = `Saved: ${{payload.updated_at || "now"}} | levels ${{savedLevels.length}}`;
        }} catch (error) {{
          if (qmCityLevelState) qmCityLevelState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          qmCityLevelSave.disabled = false;
        }}
      }});
    }}
    if (rewardSettingsSave) {{
      rewardSettingsSave.addEventListener("click", async () => {{
        rewardSettingsSave.disabled = true;
        if (rewardSettingsState) rewardSettingsState.textContent = "Saving rewards...";
        try {{
          const response = await fetch("/settings", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ leaderboard_rewards: collectRewardSettings() }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Could not save reward settings.");
          }}
          renderRewardSettings(payload.leaderboard_rewards || {{}});
          if (rewardSettingsState) rewardSettingsState.textContent = `Saved rewards: ${{payload.updated_at || "now"}}`;
        }} catch (error) {{
          if (rewardSettingsState) rewardSettingsState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          rewardSettingsSave.disabled = false;
        }}
      }});
    }}
    const resetLeaderboardScope = async (scope, button) => {{
      if (!scope || !button) return;
      const label = scope === "day" ? "day" : (scope === "week" ? "week" : "month");
      if (!window.confirm(`Reset ${{label}} vocabulary top now? Total leaderboard is not affected.`)) {{
        return;
      }}
      button.disabled = true;
      if (rewardSettingsState) rewardSettingsState.textContent = `Resetting ${{label}} top...`;
      try {{
        const response = await fetch("/vocab/leaderboard/reset", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ scopes: [scope] }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || `Could not reset ${{label}} top.`);
        }}
        if (rewardSettingsState) {{
          rewardSettingsState.textContent = `Reset ${{(payload.scopes || [scope]).join(", ")}} top at ${{payload.reset_at || "now"}}.`;
        }}
      }} catch (error) {{
        if (rewardSettingsState) rewardSettingsState.textContent = String(error && error.message ? error.message : error);
      }} finally {{
        button.disabled = false;
      }}
    }};
    const resetSpaceLeaderboardTodayTest = async (button) => {{
      if (!button) return;
      if (!window.confirm("Reset Space_W/Q/P/S/L Top Today test credit now? Users can relearn the same file and earn today's Space Top points again. Total points are not duplicated.")) {{
        return;
      }}
      button.disabled = true;
      if (rewardSettingsState) rewardSettingsState.textContent = "Resetting Space lesson Top Today test credit...";
      try {{
        const response = await fetch("/space-leaderboard/reset-today-test", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ board_types: ["space_w", "space_q", "space_p", "space_s", "space_l"] }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not reset Space lesson Top Today test credit.");
        }}
        if (rewardSettingsState) {{
          rewardSettingsState.textContent = `Reset Space Top Today test: ${{payload.removed_entries || 0}} entries, ${{payload.touched_users || 0}} users, bucket ${{payload.bucket || "today"}}.`;
        }}
      }} catch (error) {{
        if (rewardSettingsState) rewardSettingsState.textContent = String(error && error.message ? error.message : error);
      }} finally {{
        button.disabled = false;
      }}
    }};
    if (leaderboardResetDay) {{
      leaderboardResetDay.addEventListener("click", () => resetLeaderboardScope("day", leaderboardResetDay));
    }}
    if (leaderboardResetWeek) {{
      leaderboardResetWeek.addEventListener("click", () => resetLeaderboardScope("week", leaderboardResetWeek));
    }}
    if (leaderboardResetMonth) {{
      leaderboardResetMonth.addEventListener("click", () => resetLeaderboardScope("month", leaderboardResetMonth));
    }}
    if (spaceLeaderboardResetTodayTest) {{
      spaceLeaderboardResetTodayTest.addEventListener("click", () => resetSpaceLeaderboardTodayTest(spaceLeaderboardResetTodayTest));
    }}
    if (settingsSave) {{
      settingsSave.addEventListener("click", async () => {{
        settingsSave.disabled = true;
        if (settingsState) settingsState.textContent = "Saving...";
        try {{
          const seconds = normalizeHintSeconds(hintCycleInput ? hintCycleInput.value : 30);
          const paragraphSeconds = normalizeParagraphHintSeconds(paragraphHintInput ? paragraphHintInput.value : 30);
          const hudLines = String(questionHudInput && questionHudInput.value || "")
            .split(/\\r?\\n|[|;]/)
            .map((line) => line.trim())
            .filter(Boolean)
            .slice(0, 4);
          const chatLimitMb = normalizeChatAttachmentLimitMb(chatAttachmentLimitInput ? chatAttachmentLimitInput.value : 100);
          const heavyUserQuota = normalizeHeavyUserQuota(heavyUserQuotaInput ? heavyUserQuotaInput.value : 5);
          const heavyUserInterval = normalizeHeavyUserInterval(heavyUserIntervalInput ? heavyUserIntervalInput.value : 5);
          const aiAgentNoticeVoice = String(aiAgentNoticeVoiceInput && aiAgentNoticeVoiceInput.value || "kokoro:am_michael").trim() || "kokoro:am_michael";
          const leaderboardReactions = reactionSettingsFromText(leaderboardReactionsInput ? leaderboardReactionsInput.value : "");
          const cpuThreshold = normalizeCpuThreshold(cpuThresholdInput ? cpuThresholdInput.value : 90);
          const cfHostname = normalizeCloudflareHostname(cloudflareHostnameInput ? cloudflareHostnameInput.value : "");
          const cfTunnelName = normalizeCloudflareTunnelName(cloudflareTunnelNameInput ? cloudflareTunnelNameInput.value : "future-whisper");
          const savePayload = {{
            word_hint_cycle_seconds: seconds,
            paragraph_hint_seconds: paragraphSeconds,
            question_hud_lines: hudLines,
            chat_attachment_limit_mb: chatLimitMb,
            heavy_user_quota_per_minute: heavyUserQuota,
            heavy_user_min_interval_seconds: heavyUserInterval,
            ai_agent_notice_voice: aiAgentNoticeVoice,
            space_w_ai_check_voice_enabled: Boolean(spaceWAiCheckVoiceEnabled),
            leaderboard_reactions: leaderboardReactions,
            cpu_guard_enabled: Boolean(cpuGuardEnabled),
            cpu_queue_threshold_percent: cpuThreshold,
            cloudflare_public_hostname: cfHostname,
            cloudflare_tunnel_name: cfTunnelName,
          }};
          if (hostedClientSecretInput && hostedClientSecretInput.value) {{
            savePayload.hosted_client_secret = hostedClientSecretInput.value;
          }}
          const response = await fetch("/settings", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(savePayload),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) {{
            throw new Error(payload.error || "Khong luu duoc settings.");
          }}
          const saved = normalizeHintSeconds(payload.word_hint_cycle_seconds);
          if (hintCycleInput) hintCycleInput.value = String(saved);
          const savedParagraph = normalizeParagraphHintSeconds(payload.paragraph_hint_seconds);
          if (paragraphHintInput) paragraphHintInput.value = String(savedParagraph);
          if (questionHudInput) {{
            const lines = Array.isArray(payload.question_hud_lines) ? payload.question_hud_lines : hudLines;
            questionHudInput.value = lines.join("\\n");
          }}
          const savedChatLimitMb = normalizeChatAttachmentLimitMb(payload.chat_attachment_limit_mb);
          if (chatAttachmentLimitInput) chatAttachmentLimitInput.value = String(savedChatLimitMb);
          const savedHeavyUserQuota = normalizeHeavyUserQuota(payload.heavy_user_quota_per_minute);
          const savedHeavyUserInterval = normalizeHeavyUserInterval(payload.heavy_user_min_interval_seconds);
          if (heavyUserQuotaInput) heavyUserQuotaInput.value = String(savedHeavyUserQuota);
          if (heavyUserIntervalInput) heavyUserIntervalInput.value = String(savedHeavyUserInterval);
          if (aiAgentNoticeVoiceInput) aiAgentNoticeVoiceInput.value = String(payload.ai_agent_notice_voice || aiAgentNoticeVoice || "kokoro:am_michael");
          spaceWAiCheckVoiceEnabled = payload.space_w_ai_check_voice_enabled !== false;
          renderSpaceWAiCheckToggle();
          if (leaderboardReactionsInput) leaderboardReactionsInput.value = reactionSettingsToText(payload.leaderboard_reactions || leaderboardReactions);
          const savedCpuThreshold = normalizeCpuThreshold(payload.cpu_queue_threshold_percent);
          cpuGuardEnabled = payload.cpu_guard_enabled !== false;
          if (cpuThresholdInput) cpuThresholdInput.value = String(savedCpuThreshold);
          renderCpuGuardToggle();
          const savedCfHostname = normalizeCloudflareHostname(payload.cloudflare_public_hostname || "");
          const savedCfTunnelName = normalizeCloudflareTunnelName(payload.cloudflare_tunnel_name || cfTunnelName);
          if (cloudflareHostnameInput) cloudflareHostnameInput.value = savedCfHostname;
          if (cloudflareTunnelNameInput) cloudflareTunnelNameInput.value = savedCfTunnelName;
          if (hostedClientSecretInput) {{
            hostedClientSecretInput.value = "";
            hostedClientSecretInput.placeholder = payload.hosted_client_secret_set
              ? "Password key is set. Type a new one to rotate."
              : "No password key set. Type one to enable.";
          }}
          const obfState = payload.hosted_client_secret_set ? "client key set" : "default client key";
          const cfState = savedCfHostname ? `domain ${{savedCfHostname}} via ${{savedCfTunnelName}}` : "quick trycloudflare link";
          const cpuState = `${{cpuGuardEnabled ? "CPU guard" : "CPU guard off"}} ${{savedCpuThreshold}}%`;
          const speakState = spaceWAiCheckVoiceEnabled ? "Space_W Whisper on" : "Space_W browser check";
          if (settingsState) settingsState.textContent = `Saved: ${{payload.updated_at || "now"}} | W ${{saved}}s | P ${{savedParagraph}}s | chat ${{savedChatLimitMb}} MB | heavy ${{savedHeavyUserQuota}}/min + ${{savedHeavyUserInterval}}s | AI ${{payload.ai_agent_notice_voice || aiAgentNoticeVoice}} | ${{speakState}} | ${{cpuState}} | ${{cfState}} | ${{obfState}}`;
        }} catch (error) {{
          if (settingsState) settingsState.textContent = String(error && error.message ? error.message : error);
        }} finally {{
          settingsSave.disabled = false;
        }}
      }});
    }}
    const todayLocalDate = () => {{
      const now = new Date();
      const y = now.getFullYear();
      const m = String(now.getMonth() + 1).padStart(2, "0");
      const d = String(now.getDate()).padStart(2, "0");
      return `${{y}}-${{m}}-${{d}}`;
    }};
    if (loginLogDate && !loginLogDate.value) loginLogDate.value = todayLocalDate();
    if (learningLogDate && !learningLogDate.value) learningLogDate.value = todayLocalDate();
    let emailRoutingLoaded = false;
    let emailRoutingMessages = [];
    let emailRoutingReceivedAddressRows = [];
    let emailRoutingSelectedId = "";
    const setEmailRoutingState = (message, error = false) => {{
      if (!emailRoutingState) return;
      emailRoutingState.textContent = message || "";
      emailRoutingState.classList.toggle("is-error", Boolean(error));
    }};
    const emailRoutingPost = async (path, payload = {{}}) => {{
      const response = await fetch(path, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      const data = await response.json().catch(() => ({{}}));
      if (!response.ok || data.ok === false) throw new Error(data.error || "Email routing request failed.");
      return data;
    }};
    const emailRoutingDomain = () => String(emailRoutingDomainInput && emailRoutingDomainInput.value || "qm-tech.io.vn").trim().toLowerCase().replace(/^@+/, "") || "qm-tech.io.vn";
    const emailRoutingLocal = () => String(emailRoutingAliasInput && emailRoutingAliasInput.value || "admin").trim().toLowerCase().replace(/@.*$/, "").replace(/[^a-z0-9._%+-]/g, "") || "admin";
    const emailRoutingAddress = () => `${{emailRoutingLocal()}}@${{emailRoutingDomain()}}`;
    const updateEmailRoutingAddressPreview = () => {{
      const address = emailRoutingAddress();
      if (emailRoutingCurrentAddress) emailRoutingCurrentAddress.textContent = address;
      return address;
    }};
    const setEmailRoutingAddress = (address) => {{
      const raw = String(address || "").trim().toLowerCase().replace(/^mailto:/, "");
      const match = raw.match(/^([^@\\s]+)@([^@\\s]+)$/);
      if (match) {{
        if (emailRoutingAliasInput) emailRoutingAliasInput.value = match[1].replace(/[^a-z0-9._%+-]/g, "");
        if (emailRoutingDomainInput) emailRoutingDomainInput.value = match[2].replace(/^@+/, "");
      }}
      return updateEmailRoutingAddressPreview();
    }};
    const randomEmailRoutingLocal = () => {{
      const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789";
      let out = "mail";
      for (let index = 0; index < 8; index += 1) out += alphabet[Math.floor(Math.random() * alphabet.length)];
      return out;
    }};
    const emailRoutingTime = (value) => {{
      const raw = String(value || "");
      const parsed = raw ? new Date(raw) : null;
      if (parsed && !Number.isNaN(parsed.getTime())) {{
        return parsed.toLocaleTimeString([], {{ hour: "2-digit", minute: "2-digit" }});
      }}
      return raw.replace("T", " ").replace("Z", "").slice(11, 16) || "-";
    }};
    const emailRoutingOtp = (item = {{}}) => {{
      const text = `${{item.title || ""}} ${{item.subject || ""}} ${{item.content || ""}} ${{item.text || ""}} ${{item.snippet || ""}}`;
      const match = text.match(/\\b\\d{{4,8}}\\b/);
      return match ? match[0] : "-";
    }};
    const copyEmailRoutingOtp = async (otp, node) => {{
      const text = String(otp || "").trim();
      if (!text || text === "-") return;
      try {{
        await navigator.clipboard.writeText(text);
        if (node) {{
          const previous = node.textContent;
          node.textContent = "Copied";
          window.setTimeout(() => {{ node.textContent = previous; }}, 900);
        }}
        setEmailRoutingState(`Copied code ${{text}}.`);
      }} catch (error) {{
        setEmailRoutingState("Could not copy code. Select it manually.", true);
      }}
    }};
    const emailRoutingReceivedAddresses = (items = []) => {{
      const map = new Map();
      (Array.isArray(items) ? items : []).forEach((item) => {{
        const address = String(item.to || item.recipient || "").trim().toLowerCase();
        if (!/^[^@\\s]+@[^@\\s]+$/.test(address)) return;
        const latest = String(item.received_at || "");
        const row = map.get(address) || {{ address, count: 0, latest: "", title: "" }};
        row.count += 1;
        if (!row.latest || latest > row.latest) {{
          row.latest = latest;
          row.title = item.title || item.subject || "";
        }}
        map.set(address, row);
      }});
      return Array.from(map.values()).sort((left, right) => {{
        const byTime = String(right.latest || "").localeCompare(String(left.latest || ""));
        return byTime || left.address.localeCompare(right.address);
      }});
    }};
    const emailRoutingAliasSearchScore = (address, query) => {{
      const hay = String(address || "").trim().toLowerCase();
      const needle = String(query || "").trim().toLowerCase().replace(/\\s+/g, "");
      if (!needle) return {{ match: true, score: 0 }};
      const directIndex = hay.indexOf(needle);
      if (directIndex >= 0) {{
        return {{ match: true, score: 100000 + (needle.length * 1200) - directIndex }};
      }}
      let needleIndex = 0;
      let lastMatch = -2;
      let currentRun = 0;
      let bestRun = 0;
      let gapPenalty = 0;
      let score = 0;
      for (let hayIndex = 0; hayIndex < hay.length && needleIndex < needle.length; hayIndex += 1) {{
        if (hay[hayIndex] !== needle[needleIndex]) continue;
        if (hayIndex === lastMatch + 1) {{
          currentRun += 1;
        }} else {{
          if (lastMatch >= 0) gapPenalty += Math.max(0, hayIndex - lastMatch - 1);
          currentRun = 1;
        }}
        bestRun = Math.max(bestRun, currentRun);
        score += 120 + (currentRun * 35) - Math.max(0, hayIndex - needleIndex);
        lastMatch = hayIndex;
        needleIndex += 1;
      }}
      if (needleIndex < needle.length) return {{ match: false, score: -Infinity }};
      const local = hay.split("@")[0] || hay;
      if (needle.length <= 2 && bestRun < needle.length && !local.startsWith(needle[0])) {{
        return {{ match: false, score: -Infinity }};
      }}
      const prefixBonus = local.startsWith(needle[0]) ? 320 : hay.startsWith(needle[0]) ? 160 : 0;
      return {{ match: true, score: score + (bestRun * 650) + prefixBonus - (gapPenalty * 12) - hay.length }};
    }};
    const renderEmailRoutingReceivedAddresses = (items = emailRoutingReceivedAddressRows) => {{
      if (!emailRoutingReceivedAddressList) return;
      const query = emailRoutingAddressSearch ? emailRoutingAddressSearch.value : "";
      const hasQuery = Boolean(String(query || "").trim());
      const sourceRows = Array.isArray(items) && items.length
        ? items
        : emailRoutingReceivedAddresses(emailRoutingMessages);
      const rows = sourceRows
        .map((item) => ({{ ...item, search: emailRoutingAliasSearchScore(item.address, query) }}))
        .filter((item) => item.search.match)
        .sort((left, right) => {{
          if (hasQuery) {{
            const byScore = Number(right.search.score || 0) - Number(left.search.score || 0);
            if (byScore) return byScore;
          }}
          const byTime = String(right.latest || "").localeCompare(String(left.latest || ""));
          return byTime || left.address.localeCompare(right.address);
        }});
      const current = emailRoutingAddress().toLowerCase();
      emailRoutingReceivedAddressList.textContent = "";
      if (!rows.length) {{
        const empty = document.createElement("div");
        empty.className = "gmail-empty";
        empty.textContent = hasQuery ? "No received aliases match this search." : "No received aliases yet.";
        emailRoutingReceivedAddressList.appendChild(empty);
        return;
      }}
      rows.forEach((item) => {{
        const button = document.createElement("button");
        button.type = "button";
        button.className = "gmail-history-row" + (item.address === current ? " is-active" : "");
        const address = document.createElement("span");
        address.className = "gmail-history-address";
        address.textContent = item.address;
        const meta = document.createElement("span");
        meta.className = "gmail-history-meta";
        meta.textContent = `${{item.count}} mail${{item.count === 1 ? "" : "s"}}`;
        button.title = item.title || item.address;
        button.append(address, meta);
        button.addEventListener("click", () => {{
          const selected = setEmailRoutingAddress(item.address);
          emailRoutingSelectedId = "";
          if (emailRoutingAddressHistoryPanel) emailRoutingAddressHistoryPanel.hidden = true;
          else if (emailRoutingReceivedAddressList) emailRoutingReceivedAddressList.hidden = true;
          renderEmailRoutingMessages({{ messages: emailRoutingMessages, received_addresses: emailRoutingReceivedAddressRows }});
          setEmailRoutingState(`Showing ${{selected}}.`);
        }});
        emailRoutingReceivedAddressList.appendChild(button);
      }});
    }};
    const renderEmailRoutingAliases = (payload = {{}}) => {{
      if (!emailRoutingAliasList) return;
      emailRoutingAliasList.textContent = "";
      const liveRules = payload.live && Array.isArray(payload.live.rules) ? payload.live.rules : [];
      const localAliases = Array.isArray(payload.aliases) ? payload.aliases : [];
      const rows = liveRules.length
        ? liveRules.map((item) => ({{
            id: item.id || "",
            address: item.address || "",
            destination: Array.isArray(item.destinations) ? item.destinations.join(", ") : "",
            enabled: Boolean(item.enabled),
          }}))
        : localAliases.map((item) => ({{
            id: item.rule_id || "",
            address: item.address || "",
            destination: item.destination || "",
            enabled: item.enabled !== false,
          }}));
      if (!rows.length) {{
        const empty = document.createElement("span");
        empty.className = "gmail-chip";
        empty.textContent = "No Gmail addresses yet";
        emailRoutingAliasList.appendChild(empty);
        return;
      }}
      rows.forEach((item) => {{
        const chip = document.createElement("span");
        chip.className = "gmail-chip";
        const label = document.createElement("span");
        label.textContent = item.address || "";
        chip.appendChild(label);
        if (item.id) {{
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = "x";
          button.title = "Delete this Cloudflare routing rule";
          button.addEventListener("click", async () => {{
            if (!window.confirm(`Delete ${{item.address || "this alias"}}?`)) return;
            button.disabled = true;
            try {{
              const next = await emailRoutingPost("/dashboard/email-routing/delete-rule", {{ rule_id: item.id, address: item.address || "" }});
              setEmailRoutingState("Alias deleted.");
              applyEmailRoutingState(next);
            }} catch (error) {{
              setEmailRoutingState(String(error && error.message ? error.message : error), true);
              button.disabled = false;
            }}
          }});
          chip.appendChild(button);
        }}
        emailRoutingAliasList.appendChild(chip);
      }});
    }};
    const renderEmailRoutingMessages = (payload = {{}}) => {{
      if (!emailRoutingMessageList) return;
      emailRoutingMessageList.textContent = "";
      const allRows = Array.isArray(payload.messages) ? payload.messages : emailRoutingMessages;
      emailRoutingMessages = allRows;
      emailRoutingReceivedAddressRows = Array.isArray(payload.received_addresses) && payload.received_addresses.length
        ? payload.received_addresses
        : emailRoutingReceivedAddresses(allRows);
      renderEmailRoutingReceivedAddresses(emailRoutingReceivedAddressRows);
      const address = updateEmailRoutingAddressPreview();
      const addressKey = address.toLowerCase();
      const rows = allRows.filter((item) => String(item.to || item.recipient || "").toLowerCase() === addressKey);
      if (emailRoutingMessageCount) emailRoutingMessageCount.textContent = `${{rows.length}} email${{rows.length === 1 ? "" : "s"}}`;
      if (!rows.length) {{
        const empty = document.createElement("div");
        empty.className = "gmail-empty";
        empty.textContent = `No inbound messages for ${{address}} yet.`;
        emailRoutingMessageList.appendChild(empty);
        renderEmailRoutingMessage(null);
        return;
      }}
      if (!emailRoutingSelectedId || !rows.some((item) => String(item.id || "") === emailRoutingSelectedId)) {{
        emailRoutingSelectedId = String(rows[0].id || "");
      }}
      rows.forEach((item) => {{
        const row = document.createElement("button");
        row.className = "gmail-message-row" + (String(item.id || "") === emailRoutingSelectedId ? " is-active" : "");
        row.type = "button";
        const time = document.createElement("div");
        time.className = "gmail-time";
        time.textContent = emailRoutingTime(item.received_at);
        const sender = document.createElement("div");
        sender.className = "gmail-sender";
        sender.textContent = item.from || "unknown sender";
        const code = document.createElement("div");
        code.className = "gmail-code";
        const otp = emailRoutingOtp(item);
        code.textContent = otp !== "-" ? otp : (item.title || item.subject || "No subject");
        code.title = item.title || item.subject || "";
        if (otp !== "-") {{
          code.classList.add("is-copyable");
          code.title = "Click to copy this code";
          code.setAttribute("role", "button");
          code.tabIndex = 0;
          code.addEventListener("click", (event) => {{
            event.stopPropagation();
            void copyEmailRoutingOtp(otp, code);
          }});
          code.addEventListener("keydown", (event) => {{
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            event.stopPropagation();
            void copyEmailRoutingOtp(otp, code);
          }});
        }}
        const action = document.createElement("div");
        action.className = "gmail-action";
        action.textContent = "View";
        row.addEventListener("click", () => {{
          emailRoutingSelectedId = String(item.id || "");
          renderEmailRoutingMessages({{ messages: emailRoutingMessages, received_addresses: emailRoutingReceivedAddressRows }});
          renderEmailRoutingMessage(item);
        }});
        row.append(time, sender, code, action);
        emailRoutingMessageList.appendChild(row);
      }});
      renderEmailRoutingMessage(rows.find((item) => String(item.id || "") === emailRoutingSelectedId) || rows[0]);
    }};
    const renderEmailRoutingMessage = (item) => {{
      const safe = item || {{}};
      if (emailRoutingReaderSubject) emailRoutingReaderSubject.textContent = safe.title || safe.subject || "No email selected";
      if (emailRoutingReaderSender) emailRoutingReaderSender.textContent = safe.from ? `From: ${{safe.from}}` : "From: -";
      if (emailRoutingReaderTime) emailRoutingReaderTime.textContent = safe.received_at ? String(safe.received_at).replace("T", " ").replace("Z", "") : "Time: -";
      if (emailRoutingReaderCode) {{
        const otp = item ? emailRoutingOtp(safe) : "-";
        emailRoutingReaderCode.textContent = otp;
        emailRoutingReaderCode.classList.toggle("is-copyable", otp !== "-");
        emailRoutingReaderCode.title = otp !== "-" ? "Click to copy this code" : "";
        emailRoutingReaderCode.tabIndex = otp !== "-" ? 0 : -1;
        emailRoutingReaderCode.onclick = otp !== "-" ? () => copyEmailRoutingOtp(otp, emailRoutingReaderCode) : null;
        emailRoutingReaderCode.onkeydown = otp !== "-" ? (event) => {{
          if (event.key !== "Enter" && event.key !== " ") return;
          event.preventDefault();
          void copyEmailRoutingOtp(otp, emailRoutingReaderCode);
        }} : null;
      }}
      if (emailRoutingReaderBody) emailRoutingReaderBody.textContent = item ? (safe.content || safe.snippet || safe.text || "") : "Select an email to read it.";
    }};
    const applyEmailRoutingState = (payload = {{}}) => {{
      if (emailRoutingDomainInput) emailRoutingDomainInput.value = payload.domain || "";
      if (emailRoutingDefaultDestinationInput) emailRoutingDefaultDestinationInput.value = payload.default_destination || "";
      if (emailRoutingAccountIdInput) emailRoutingAccountIdInput.value = payload.account_id || "";
      if (emailRoutingZoneIdInput) emailRoutingZoneIdInput.value = payload.zone_id || "";
      if (emailRoutingApiTokenInput) emailRoutingApiTokenInput.value = "";
      if (emailRoutingInboundSecretInput) emailRoutingInboundSecretInput.value = payload.inbound_secret || "";
      updateEmailRoutingAddressPreview();
      renderEmailRoutingAliases(payload);
      renderEmailRoutingMessages(payload);
      const token = payload.token_saved ? `token ${{payload.token_source || "saved"}} ${{payload.token_hint || ""}}` : "token missing";
      const inbox = payload.inbound_secret_hint ? ` | webhook ${{payload.inbound_secret_hint}}` : "";
      setEmailRoutingState(`${{payload.domain || "gmail"}} | ${{token}}${{inbox}}`);
    }};
    const loadEmailRouting = async (live = false) => {{
      if (!emailRoutingAliasList && !emailRoutingMessageList) return;
      setEmailRoutingState(live ? "Refreshing Cloudflare email..." : "Loading email routing...");
      try {{
        const url = `/dashboard/email-routing/state?ts=${{Date.now()}}${{live ? "&live=1" : ""}}`;
        const response = await fetch(url, {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not load email routing.");
        emailRoutingLoaded = true;
        applyEmailRoutingState(payload);
        if (payload.live_error) setEmailRoutingState(payload.live_error, true);
      }} catch (error) {{
        setEmailRoutingState(String(error && error.message ? error.message : error), true);
      }}
    }};
    const saveEmailRouting = async (regenerateSecret = false) => {{
      if (!emailRoutingSave) return;
      const button = regenerateSecret ? emailRoutingRegenerateSecret : emailRoutingSave;
      if (button) button.disabled = true;
      setEmailRoutingState("Saving email routing...");
      try {{
        const payload = {{
          domain: emailRoutingDomainInput ? emailRoutingDomainInput.value : "",
          default_destination: emailRoutingDefaultDestinationInput ? emailRoutingDefaultDestinationInput.value : "",
          account_id: emailRoutingAccountIdInput ? emailRoutingAccountIdInput.value : "",
          zone_id: emailRoutingZoneIdInput ? emailRoutingZoneIdInput.value : "",
          api_token: emailRoutingApiTokenInput ? emailRoutingApiTokenInput.value : "",
          inbound_secret: emailRoutingInboundSecretInput ? emailRoutingInboundSecretInput.value : "",
          regenerate_inbound_secret: Boolean(regenerateSecret),
        }};
        const saved = await emailRoutingPost("/dashboard/email-routing/config", payload);
        applyEmailRoutingState(saved);
        setEmailRoutingState(regenerateSecret ? "Webhook secret regenerated." : "Email settings saved.");
      }} catch (error) {{
        setEmailRoutingState(String(error && error.message ? error.message : error), true);
      }} finally {{
        if (button) button.disabled = false;
      }}
    }};
    const verifyEmailRoutingDestination = async () => {{
      if (!emailRoutingVerifyDestination) return;
      emailRoutingVerifyDestination.disabled = true;
      setEmailRoutingState("Sending Gmail verification...");
      try {{
        const payload = {{ destination: emailRoutingDefaultDestinationInput ? emailRoutingDefaultDestinationInput.value : "" }};
        const saved = await emailRoutingPost("/dashboard/email-routing/destination", payload);
        applyEmailRoutingState(saved);
        setEmailRoutingState("Cloudflare verification email sent.");
      }} catch (error) {{
        setEmailRoutingState(String(error && error.message ? error.message : error), true);
      }} finally {{
        emailRoutingVerifyDestination.disabled = false;
      }}
    }};
    const selectEmailRoutingAddress = () => {{
      const address = updateEmailRoutingAddressPreview();
      emailRoutingSelectedId = "";
      renderEmailRoutingMessages({{ messages: emailRoutingMessages, received_addresses: emailRoutingReceivedAddressRows }});
      setEmailRoutingState(`Watching ${{address}}. External mail arrives here after Cloudflare catch-all/Worker is active.`);
    }};
    const createEmailRoutingRoute = async () => {{
      if (!emailRoutingCreateRoute) return;
      emailRoutingCreateRoute.disabled = true;
      setEmailRoutingState("Creating Cloudflare route...");
      try {{
        const payload = {{
          address: updateEmailRoutingAddressPreview(),
          destination: emailRoutingAliasDestinationInput ? emailRoutingAliasDestinationInput.value : "",
          name: emailRoutingAliasNameInput ? emailRoutingAliasNameInput.value : "",
        }};
        const saved = await emailRoutingPost("/dashboard/email-routing/alias", payload);
        applyEmailRoutingState(saved);
        setEmailRoutingState(`Created Cloudflare route for ${{saved.address || payload.address}}.`);
      }} catch (error) {{
        setEmailRoutingState(String(error && error.message ? error.message : error), true);
      }} finally {{
        emailRoutingCreateRoute.disabled = false;
      }}
    }};
    const createEmailRoutingAlias = () => {{
      if (!emailRoutingCreateAlias) return;
      emailRoutingCreateAlias.disabled = true;
      try {{
        selectEmailRoutingAddress();
      }} catch (error) {{
        setEmailRoutingState(String(error && error.message ? error.message : error), true);
      }} finally {{
        emailRoutingCreateAlias.disabled = false;
      }}
    }};
    const dashboardTabs = [
      {{ name: "main", tab: tabMain, panel: panelMain }},
      {{ name: "users", tab: tabUsers, panel: panelUsers }},
      {{ name: "login", tab: tabLoginLog, panel: panelLoginLog }},
      {{ name: "learning", tab: tabLearningLog, panel: panelLearningLog }},
      {{ name: "admins", tab: tabAdmins, panel: panelAdmins }},
      {{ name: "password-reset", tab: tabPasswordReset, panel: panelPasswordReset }},
      {{ name: "security", tab: tabSecurity, panel: panelSecurity }},
      {{ name: "email-routing", tab: tabEmailRouting, panel: panelEmailRouting }},
      {{ name: "workers", tab: tabWorkers, panel: panelWorkers }},
      {{ name: "rewards", tab: tabRewards, panel: panelRewards }},
      {{ name: "qm-city", tab: tabQmCity, panel: panelQmCity }},
      {{ name: "qm-city-npc", tab: tabQmCityNpc, panel: panelQmCityNpc }},
      {{ name: "qm-city-levels", tab: tabQmCityLevels, panel: panelQmCityLevels }},
    ];
    let activeDashboardTab = "main";
    const deleteDashboardUserData = async (username, button) => {{
      const safeUser = String(username || "").trim();
      if (!safeUser) return;
      const confirmName = window.prompt(`Delete all private data for user "${{safeUser}}"? Type the username to confirm.`);
      if (confirmName !== safeUser) {{
        if (messageNode) messageNode.textContent = "User deletion cancelled.";
        return;
      }}
      if (button) button.disabled = true;
      if (messageNode) messageNode.textContent = `Deleting private data for ${{safeUser}}...`;
      try {{
        const response = await fetch("/dashboard/users/delete", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ username: safeUser, confirm: confirmName }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not delete user data.");
        const deleted = payload.deleted || {{}};
        const paths = Number(deleted.deleted_path_count || 0);
        const states = Number(deleted.state_changes || 0);
        const sessions = Number(deleted.revoked_sessions || 0);
        const errors = Array.isArray(deleted.errors) ? deleted.errors.filter(Boolean) : [];
        if (messageNode) {{
          messageNode.textContent = errors.length
            ? `Deleted ${{safeUser}} with warnings: ${{errors.join(" | ")}}`
            : `Deleted ${{safeUser}}: ${{paths}} path(s), ${{states}} state group(s), ${{sessions}} session(s).`;
        }}
        await loadAdminUsers();
        try {{ await pollChatAdmin(); }} catch (error) {{}}
      }} catch (error) {{
        if (messageNode) messageNode.textContent = String(error && error.message ? error.message : error);
        if (button) button.disabled = false;
      }}
    }};
    let adminUserRowsCache = [];
    // Added 2026-07-09: keeps admin account search client-side so filtering never hits the server.
    const renderAdminUsers = (rows = adminUserRowsCache) => {{
      if (!adminUserList) return;
      adminUserList.textContent = "";
      const query = String(adminUserSearch && adminUserSearch.value || "").trim().toLowerCase();
      const list = Array.isArray(rows) ? rows : [];
      const filtered = query
        ? list.filter((item) => {{
          const flags = Array.isArray(item && item.data_flags) ? item.data_flags.join(" ") : "";
          const haystack = [
            item && item.username,
            item && item.full_name,
            flags,
            item && item.is_admin ? "admin" : "learner",
            item && item.login_blocked ? "blocked login blocked-login chan dang nhap" : "",
            item && item.has_account ? "account" : "",
            item && item.has_data ? "data" : "",
          ].join(" ").toLowerCase();
          return haystack.includes(query);
        }})
        : list;
      if (!list.length) {{
        adminUserList.textContent = "No users found.";
        return;
      }}
      if (!filtered.length) {{
        adminUserList.textContent = "No matching users.";
        return;
      }}
      filtered.forEach((item) => {{
          const row = document.createElement("div");
          row.className = "dashboard-log-row";
          const name = document.createElement("div");
          name.className = "dashboard-log-user";
          name.textContent = item.username || "";
          const info = document.createElement("div");
          info.className = "dashboard-log-detail";
          const flags = Array.isArray(item.data_flags) ? item.data_flags.filter(Boolean) : [];
          info.textContent = `${{item.full_name || (item.is_admin ? "Admin enabled" : "Learner")}}${{item.login_blocked ? " | login blocked" : ""}}${{flags.length ? ` | data: ${{flags.join(", ")}}` : ""}}`;
          const actions = document.createElement("div");
          actions.className = "online-actions";
          const passwordInput = document.createElement("input");
          passwordInput.className = "setting-input admin-password-input";
          passwordInput.type = "text";
          passwordInput.placeholder = "New password";
          passwordInput.autocomplete = "off";
          passwordInput.spellcheck = false;
          passwordInput.title = "Admin reset: at least 4 characters. Numbers are optional.";
          const passwordButton = document.createElement("button");
          passwordButton.className = "pending-action";
          passwordButton.type = "button";
          passwordButton.textContent = "Change password";
          passwordButton.title = "Change this user's password immediately.";
          passwordButton.addEventListener("click", async () => {{
            const nextPassword = String(passwordInput.value || "");
            passwordButton.disabled = true;
            passwordInput.disabled = true;
            try {{
              const save = await fetch("/dashboard/users/password", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ username: item.username || "", password: nextPassword }}),
              }});
              const saved = await save.json().catch(() => ({{}}));
              if (!save.ok || saved.ok === false) throw new Error(saved.error || "Could not change password.");
              passwordInput.value = "";
              if (messageNode) messageNode.textContent = `Password changed for ${{item.username || ""}}.`;
            }} catch (error) {{
              if (messageNode) messageNode.textContent = String(error && error.message ? error.message : error);
            }} finally {{
              passwordButton.disabled = false;
              passwordInput.disabled = false;
            }}
          }});
          const button = document.createElement("button");
          button.className = "pending-action" + (item.is_admin ? " reject" : "");
          button.type = "button";
          button.textContent = item.is_admin ? "Remove admin" : "Make admin";
          button.addEventListener("click", async () => {{
            button.disabled = true;
            try {{
              const save = await fetch("/dashboard/admins", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ username: item.username || "", enabled: !item.is_admin }}),
              }});
              const saved = await save.json().catch(() => ({{}}));
              if (!save.ok || saved.ok === false) throw new Error(saved.error || "Could not update admin.");
              await loadAdminUsers();
            }} catch (error) {{
              messageNode.textContent = String(error && error.message ? error.message : error);
              button.disabled = false;
            }}
          }});
          const blockButton = document.createElement("button");
          blockButton.className = "pending-action" + (item.login_blocked ? "" : " reject");
          blockButton.type = "button";
          blockButton.textContent = item.login_blocked ? "Unblock login" : "Block login";
          blockButton.title = item.login_blocked
            ? "Allow this user to log in again."
            : "Block this user from logging in and revoke active sessions.";
          blockButton.disabled = !item.has_account;
          blockButton.addEventListener("click", async () => {{
            blockButton.disabled = true;
            try {{
              const save = await fetch("/dashboard/users/block-login", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{ username: item.username || "", blocked: !item.login_blocked }}),
              }});
              const saved = await save.json().catch(() => ({{}}));
              if (!save.ok || saved.ok === false) throw new Error(saved.error || "Could not update login block.");
              const revoked = Number(saved.revoked_sessions || 0);
              if (messageNode) {{
                messageNode.textContent = saved.login_blocked
                  ? `Login blocked for ${{item.username || ""}}${{revoked ? `; revoked ${{revoked}} session(s)` : ""}}.`
                  : `Login unblocked for ${{item.username || ""}}.`;
              }}
              await loadAdminUsers();
            }} catch (error) {{
              messageNode.textContent = String(error && error.message ? error.message : error);
              blockButton.disabled = false;
            }}
          }});
          const deleteButton = document.createElement("button");
          deleteButton.className = "pending-action reject";
          deleteButton.type = "button";
          deleteButton.textContent = "Delete user data";
          deleteButton.title = "Delete this user's account, progress, private server-data folder, profile media, chat attachments, and related learning state.";
          deleteButton.disabled = !item.has_data && !item.has_account;
          deleteButton.addEventListener("click", () => void deleteDashboardUserData(item.username || "", deleteButton));
          actions.append(passwordInput, passwordButton, button, blockButton, deleteButton);
          row.append(name, info, actions);
          adminUserList.appendChild(row);
        }});
    }};
    const loadAdminUsers = async () => {{
      if (!adminUserList) return;
      adminUserList.textContent = "Loading...";
      try {{
        const response = await fetch("/dashboard/admins?ts=" + Date.now(), {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not load admins.");
        adminUserRowsCache = Array.isArray(payload.users) ? payload.users : [];
        renderAdminUsers(adminUserRowsCache);
      }} catch (error) {{
        adminUserList.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    if (adminUserSearch) {{
      adminUserSearch.addEventListener("input", () => renderAdminUsers(adminUserRowsCache));
    }}
    const renderDashboardLogRows = (node, rows, mode) => {{
      if (!node) return;
      node.textContent = "";
      const list = Array.isArray(rows) ? rows : [];
      if (!list.length) {{
        const empty = document.createElement("div");
        empty.className = "dashboard-log-row";
        empty.innerHTML = '<span class="dashboard-log-time">No data</span><span class="dashboard-log-user">-</span><span class="dashboard-log-detail">No matching records in the last 31 days.</span>';
        node.appendChild(empty);
        return;
      }}
      list.forEach((item) => {{
        const row = document.createElement("div");
        row.className = "dashboard-log-row";
        const at = document.createElement("div");
        at.className = "dashboard-log-time";
        at.textContent = String(item.at || "").replace("T", " ").replace("Z", "");
        const user = document.createElement("div");
        user.className = "dashboard-log-user";
        user.textContent = item.user || item.username || "";
        const detail = document.createElement("div");
        detail.className = "dashboard-log-detail";
        if (mode === "login") {{
          const client = item.client ? ` | IP: ${{item.client}}` : "";
          const agent = item.user_agent ? ` | ${{item.user_agent}}` : "";
          detail.textContent = `Logged in${{client}}${{agent}}`;
        }} else {{
          const file = item.file || item.title || item.path || "lesson";
          const count = item.user_count ? ` | user runs: ${{item.user_count}}` : "";
          const total = item.total ? ` | file runs: ${{item.total}}` : "";
          const nodes = item.nodes ? ` | nodes: ${{item.nodes}}` : "";
          detail.textContent = `Completed ${{file}}${{nodes}}${{count}}${{total}}`;
        }}
        row.append(at, user, detail);
        node.appendChild(row);
      }});
    }};
    const loadDashboardLog = async (mode) => {{
      const isLogin = mode === "login";
      const dateInput = isLogin ? loginLogDate : learningLogDate;
      const searchInput = isLogin ? loginLogSearch : learningLogSearch;
      const listNode = isLogin ? loginLogList : learningLogList;
      if (!listNode) return;
      listNode.textContent = "Loading...";
      try {{
        const query = new URLSearchParams();
        if (dateInput && dateInput.value) query.set("date", dateInput.value);
        if (searchInput && searchInput.value) query.set("search", searchInput.value);
        query.set("limit", "1000");
        const endpoint = isLogin ? "/dashboard/login-log" : "/dashboard/learning-log";
        const response = await fetch(`${{endpoint}}?${{query.toString()}}`, {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          throw new Error(payload.error || "Could not load log.");
        }}
        renderDashboardLogRows(listNode, payload.rows || [], mode);
      }} catch (error) {{
        listNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const showDashboardTab = (name) => {{
      activeDashboardTab = name || "main";
      dashboardTabs.forEach((item) => {{
        if (item.panel) item.panel.hidden = item.name !== activeDashboardTab;
        if (item.tab) item.tab.classList.toggle("is-active", item.name === activeDashboardTab);
      }});
      if (activeDashboardTab === "login") void loadDashboardLog("login");
      if (activeDashboardTab === "learning") void loadDashboardLog("learning");
      if (activeDashboardTab === "admins") void loadAdminUsers();
      if (activeDashboardTab === "password-reset") void pollPendingUsers();
      if (activeDashboardTab === "security") void poll();
      if (activeDashboardTab === "email-routing") void loadEmailRouting(!emailRoutingLoaded);
      if (activeDashboardTab === "rewards") void loadSettings();
      if (activeDashboardTab === "qm-city") void loadSettings();
      if (activeDashboardTab === "qm-city-npc") void loadSettings();
      if (activeDashboardTab === "qm-city-levels") void loadSettings();
      if (activeDashboardTab === "users") {{
        adminOnlineRenderedSignature = "";
        void pollChatAdmin();
        renderOnlineUsers(adminChatState.users || [], adminChatState);
        void pollAdminScreenPreviews();
      }}
    }};
    if (tabMain) tabMain.addEventListener("click", () => showDashboardTab("main"));
    if (tabUsers) tabUsers.addEventListener("click", () => showDashboardTab("users"));
    if (tabLoginLog) tabLoginLog.addEventListener("click", () => showDashboardTab("login"));
    if (tabLearningLog) tabLearningLog.addEventListener("click", () => showDashboardTab("learning"));
    if (tabAdmins) tabAdmins.addEventListener("click", () => showDashboardTab("admins"));
    if (tabPasswordReset) tabPasswordReset.addEventListener("click", () => showDashboardTab("password-reset"));
    if (tabSecurity) tabSecurity.addEventListener("click", () => showDashboardTab("security"));
    if (tabEmailRouting) tabEmailRouting.addEventListener("click", () => showDashboardTab("email-routing"));
    if (tabWorkers) tabWorkers.addEventListener("click", () => showDashboardTab("workers"));
    if (tabRewards) tabRewards.addEventListener("click", () => showDashboardTab("rewards"));
    if (tabQmCity) tabQmCity.addEventListener("click", () => showDashboardTab("qm-city"));
    if (tabQmCityNpc) tabQmCityNpc.addEventListener("click", () => showDashboardTab("qm-city-npc"));
    if (tabQmCityLevels) tabQmCityLevels.addEventListener("click", () => showDashboardTab("qm-city-levels"));
    if (loginLogRefresh) loginLogRefresh.addEventListener("click", () => loadDashboardLog("login"));
    if (learningLogRefresh) learningLogRefresh.addEventListener("click", () => loadDashboardLog("learning"));
    [emailRoutingAliasInput, emailRoutingDomainInput].forEach((node) => node && node.addEventListener("input", () => {{
      emailRoutingSelectedId = "";
      renderEmailRoutingMessages({{ messages: emailRoutingMessages, received_addresses: emailRoutingReceivedAddressRows }});
    }}));
    if (emailRoutingRandom) emailRoutingRandom.addEventListener("click", () => {{
      if (emailRoutingAliasInput) emailRoutingAliasInput.value = randomEmailRoutingLocal();
      selectEmailRoutingAddress();
    }});
    if (emailRoutingCopy) emailRoutingCopy.addEventListener("click", async () => {{
      const address = updateEmailRoutingAddressPreview();
      try {{
        await navigator.clipboard.writeText(address);
        setEmailRoutingState(`Copied ${{address}}`);
      }} catch (error) {{
        setEmailRoutingState(address);
      }}
    }});
    if (emailRoutingAddressHistory) emailRoutingAddressHistory.addEventListener("click", () => {{
      const panel = emailRoutingAddressHistoryPanel || emailRoutingReceivedAddressList;
      if (!panel) return;
      renderEmailRoutingReceivedAddresses(emailRoutingReceivedAddressRows);
      panel.hidden = !panel.hidden;
      if (!panel.hidden && emailRoutingAddressSearch) emailRoutingAddressSearch.focus();
    }});
    if (emailRoutingAddressSearch) emailRoutingAddressSearch.addEventListener("input", () => {{
      renderEmailRoutingReceivedAddresses(emailRoutingReceivedAddressRows);
    }});
    if (emailRoutingReaderBack) emailRoutingReaderBack.addEventListener("click", () => {{
      emailRoutingSelectedId = "";
      renderEmailRoutingMessages({{ messages: emailRoutingMessages, received_addresses: emailRoutingReceivedAddressRows }});
    }});
    if (emailRoutingSave) emailRoutingSave.addEventListener("click", () => saveEmailRouting(false));
    if (emailRoutingRegenerateSecret) emailRoutingRegenerateSecret.addEventListener("click", () => saveEmailRouting(true));
    if (emailRoutingVerifyDestination) emailRoutingVerifyDestination.addEventListener("click", () => verifyEmailRoutingDestination());
    if (emailRoutingRefresh) emailRoutingRefresh.addEventListener("click", () => loadEmailRouting(true));
    if (emailRoutingWorker) emailRoutingWorker.addEventListener("click", () => window.open("/dashboard/email-routing/worker.js", "_blank", "noopener"));
    if (emailRoutingOpenFull) emailRoutingOpenFull.addEventListener("click", () => window.open("/dashboard/email-routing", "_blank", "noopener"));
    if (emailRoutingCreateAlias) emailRoutingCreateAlias.addEventListener("click", () => createEmailRoutingAlias());
    if (emailRoutingCreateRoute) emailRoutingCreateRoute.addEventListener("click", () => createEmailRoutingRoute());
    [loginLogDate, loginLogSearch].forEach((node) => node && node.addEventListener("change", () => loadDashboardLog("login")));
    [learningLogDate, learningLogSearch].forEach((node) => node && node.addEventListener("change", () => loadDashboardLog("learning")));
    const renderAdminVoiceSelect = (select, items, fallbackKey, fallbackLabel = "") => {{
      if (!select) return;
      const rows = Array.isArray(items) && items.length
        ? items
        : (fallbackKey ? [{{ key: fallbackKey, label: fallbackLabel || fallbackKey }}] : []);
      const previous = select.value || fallbackKey || "";
      select.textContent = "";
      rows.forEach((item) => {{
        const option = document.createElement("option");
        option.value = item.key || "";
        option.textContent = item.label || item.key || "Voice";
        select.appendChild(option);
      }});
      if (previous && rows.some((item) => item.key === previous)) {{
        select.value = previous;
      }} else if (fallbackKey && rows.some((item) => item.key === fallbackKey)) {{
        select.value = fallbackKey;
      }}
    }};
    const loadAdminChatVoices = async () => {{
      if (adminChatVoiceState) adminChatVoiceState.textContent = "Loading voices...";
      try {{
        const response = await fetch("/chat/admin/voices?ts=" + Date.now(), {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not load voices.");
        adminChatVoices = {{ vi: payload.vi || [], en: payload.en || [] }};
        renderAdminVoiceSelect(adminChatViVoice, adminChatVoices.vi, "edge:vi-VN-NamMinhNeural", "Edge | Vietnamese VN | Nam Minh");
        renderAdminVoiceSelect(adminChatEnVoice, adminChatVoices.en, "male-us", "People | Male US");
        if (adminChatVoiceState) {{
          const suffix = payload.error ? ` | ${{payload.error}}` : "";
          adminChatVoiceState.textContent = `${{adminChatVoices.vi.length}} Vietnamese voices | ${{adminChatVoices.en.length}} English voices${{suffix}}`;
        }}
      }} catch (error) {{
        adminChatVoices = {{
          vi: [
            {{ label: "Edge | Vietnamese VN | Nam Minh", key: "edge:vi-VN-NamMinhNeural" }},
            {{ label: "Edge | Vietnamese VN | Hoai My", key: "edge:vi-VN-HoaiMyNeural" }},
          ],
          en: [{{ label: "People | Male US", key: "male-us" }}],
        }};
        renderAdminVoiceSelect(adminChatViVoice, adminChatVoices.vi, "edge:vi-VN-NamMinhNeural", "Edge | Vietnamese VN | Nam Minh");
        renderAdminVoiceSelect(adminChatEnVoice, adminChatVoices.en, "male-us", "People | Male US");
        if (adminChatVoiceState) adminChatVoiceState.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const renderAdminChatAudioToggles = () => {{
      if (adminChatViAudioToggle) {{
        adminChatViAudioToggle.classList.toggle("is-on", adminChatViAudioEnabled);
        adminChatViAudioToggle.textContent = adminChatViAudioEnabled ? "VI audio on" : "VI audio off";
        adminChatViAudioToggle.setAttribute("aria-pressed", adminChatViAudioEnabled ? "true" : "false");
      }}
      if (adminChatEnAudioToggle) {{
        adminChatEnAudioToggle.classList.toggle("is-on", adminChatEnAudioEnabled);
        adminChatEnAudioToggle.textContent = adminChatEnAudioEnabled ? "EN audio on" : "EN audio off";
        adminChatEnAudioToggle.setAttribute("aria-pressed", adminChatEnAudioEnabled ? "true" : "false");
      }}
    }};
    const setAdminTranslateEnabled = (enabled) => {{
      adminTranslateEnabled = Boolean(enabled);
      if (adminChatTranslate) {{
        adminChatTranslate.classList.toggle("is-active", adminTranslateEnabled);
        adminChatTranslate.textContent = adminTranslateEnabled ? "Translate to English: On" : "Translate to English";
      }}
    }};
    const translateAdminDraft = async () => {{
      const text = String(adminChatInput && adminChatInput.value || "").trim();
      if (!text || !adminChatEnInput) return;
      if (adminChatVoiceState) adminChatVoiceState.textContent = "Translating...";
      try {{
        const response = await fetch("/chat/admin/translate", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ text }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not translate.");
        adminChatEnInput.value = payload.translation || "";
        if (adminChatVoiceState) adminChatVoiceState.textContent = "Translation ready.";
      }} catch (error) {{
        if (adminChatVoiceState) adminChatVoiceState.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const queueAdminTranslate = () => {{
      if (!adminTranslateEnabled) return;
      window.clearTimeout(adminTranslateTimer);
      adminTranslateTimer = window.setTimeout(() => {{
        translateAdminDraft();
      }}, 520);
    }};
    if (adminChatTranslate) {{
      adminChatTranslate.addEventListener("click", () => {{
        setAdminTranslateEnabled(!adminTranslateEnabled);
        if (adminTranslateEnabled) translateAdminDraft();
      }});
    }}
    if (adminChatInput) adminChatInput.addEventListener("input", queueAdminTranslate);
    const adminChatUserRecord = (username) => (adminChatState.users || []).find((item) => item.username === username) || null;
    const adminChatAttachments = (item = {{}}) => {{
      const rows = Array.isArray(item.attachments) ? [...item.attachments] : [];
      if (item.attachment && typeof item.attachment === "object") rows.push(item.attachment);
      return rows.filter((row) => row && (row.path || row.url));
    }};
    const adminChatRowsSignature = (rows = []) => {{
      const source = Array.isArray(rows) ? rows : [];
      return source.map((item) => {{
        const audioPath = item.audio_path || (item.audio && item.audio.path) || "";
        const attachments = adminChatAttachments(item)
          .map((attachment) => [
            attachment.id || "",
            attachment.path || attachment.url || "",
            attachment.name || "",
            attachment.mime || "",
            attachment.size || "",
          ].join(":"))
          .join(",");
        return [
          item.id || "",
          item.sender || "",
          item.text || "",
          item.peer_read ? "1" : "0",
          audioPath,
          attachments,
        ].join("|");
      }}).join("||");
    }};
    const adminAttachmentUrl = (attachment = {{}}, download = false) => {{
      const raw = String(download
        ? attachment.download_url || attachment.downloadUrl || attachment.url || attachment.path || ""
        : attachment.url || attachment.path || "");
      if (!raw) return "";
      if (/^https?:\\/\\//i.test(raw) || raw.startsWith("data:") || raw.startsWith("blob:")) return raw;
      if (raw.startsWith("/")) return raw;
      return `/chat/attachment?path=${{encodeURIComponent(raw)}}${{download ? "&download=1" : ""}}`;
    }};
    const formatAdminAttachmentSize = (size) => {{
      const value = Number(size || 0);
      if (!value) return "";
      if (value >= 1024 * 1024) return `${{(value / (1024 * 1024)).toFixed(value >= 10 * 1024 * 1024 ? 0 : 1)}} MB`;
      if (value >= 1024) return `${{Math.round(value / 1024)}} KB`;
      return `${{value}} B`;
    }};
    const applyAdminImageTransform = () => {{
      if (!adminImageViewerImg) return;
      adminImageViewerImg.style.transform = `translate(${{adminImageViewerState.x}}px, ${{adminImageViewerState.y}}px) scale(${{adminImageViewerState.zoom}})`;
      if (adminImageZoomReset) adminImageZoomReset.textContent = `${{Math.round(adminImageViewerState.zoom * 100)}}%`;
    }};
    const resetAdminImageTransform = () => {{
      adminImageViewerState.zoom = 1;
      adminImageViewerState.x = 0;
      adminImageViewerState.y = 0;
      adminImageViewerState.dragging = false;
      if (adminImageViewerImg) adminImageViewerImg.classList.remove("is-dragging");
      applyAdminImageTransform();
    }};
    const setAdminImageZoom = (zoom) => {{
      adminImageViewerState.zoom = Math.max(0.25, Math.min(6, Number(zoom) || 1));
      applyAdminImageTransform();
    }};
    const openAdminImageViewer = (src, downloadSrc = "", name = "") => {{
      if (!adminImageViewer || !adminImageViewerImg) {{
        window.open(src, "_blank", "noopener");
        return;
      }}
      resetAdminImageTransform();
      adminImageViewerImg.src = src;
      adminImageViewerImg.alt = name || "Chat image";
      if (adminImageDownload) {{
        adminImageDownload.href = downloadSrc || src;
        adminImageDownload.setAttribute("download", name || "chat-image");
      }}
      adminImageViewer.classList.add("is-open");
    }};
    const closeAdminImageViewer = () => {{
      if (!adminImageViewer) return;
      resetAdminImageTransform();
      adminImageViewer.classList.remove("is-open");
      if (adminImageViewerImg) adminImageViewerImg.removeAttribute("src");
    }};
    const beginAdminImageDrag = (event) => {{
      if (!adminImageViewerImg || !adminImageViewer || !adminImageViewer.classList.contains("is-open")) return;
      event.preventDefault();
      event.stopPropagation();
      adminImageViewerState.dragging = true;
      adminImageViewerState.pointerId = event.pointerId;
      adminImageViewerState.startX = event.clientX;
      adminImageViewerState.startY = event.clientY;
      adminImageViewerState.originX = adminImageViewerState.x;
      adminImageViewerState.originY = adminImageViewerState.y;
      adminImageViewerImg.classList.add("is-dragging");
      try {{ adminImageViewerImg.setPointerCapture(event.pointerId); }} catch (error) {{}}
    }};
    const moveAdminImageDrag = (event) => {{
      if (!adminImageViewerState.dragging) return;
      event.preventDefault();
      adminImageViewerState.x = adminImageViewerState.originX + event.clientX - adminImageViewerState.startX;
      adminImageViewerState.y = adminImageViewerState.originY + event.clientY - adminImageViewerState.startY;
      applyAdminImageTransform();
    }};
    const endAdminImageDrag = (event) => {{
      if (!adminImageViewerState.dragging) return;
      adminImageViewerState.dragging = false;
      if (adminImageViewerImg) {{
        adminImageViewerImg.classList.remove("is-dragging");
        try {{ adminImageViewerImg.releasePointerCapture(event.pointerId); }} catch (error) {{}}
      }}
    }};
    const setAdminPaintStatus = (message) => {{
      if (adminPaintStatus) adminPaintStatus.textContent = message || "";
    }};
    const adminPaintCtx = () => adminPaintCanvas ? adminPaintCanvas.getContext("2d") : null;
    const adminPaintBufferCtx = () => {{
      if (!adminPaintBufferCanvas) {{
        adminPaintBufferCanvas = document.createElement("canvas");
        adminPaintBufferCanvas.width = ADMIN_PAINT_BOARD_WIDTH;
        adminPaintBufferCanvas.height = ADMIN_PAINT_BOARD_HEIGHT;
      }}
      return adminPaintBufferCanvas.getContext("2d");
    }};
    const adminPaintEnsureBuffer = () => {{
      if (!adminPaintBufferCanvas) {{
        adminPaintBufferCanvas = document.createElement("canvas");
      }}
      if (adminPaintBufferCanvas.width === ADMIN_PAINT_BOARD_WIDTH && adminPaintBufferCanvas.height === ADMIN_PAINT_BOARD_HEIGHT) return;
      const previous = adminPaintBufferCanvas;
      const next = document.createElement("canvas");
      next.width = ADMIN_PAINT_BOARD_WIDTH;
      next.height = ADMIN_PAINT_BOARD_HEIGHT;
      const ctx = next.getContext("2d");
      if (ctx && previous.width && previous.height) {{
        ctx.drawImage(previous, 0, 0, previous.width, previous.height, 0, 0, next.width, next.height);
      }}
      adminPaintBufferCanvas = next;
    }};
    const drawAdminPaintGrid = (ctx, width, height) => {{
      ctx.fillStyle = "#f7fff9";
      ctx.fillRect(0, 0, width, height);
      ctx.strokeStyle = "rgba(15, 23, 42, 0.055)";
      ctx.lineWidth = 1;
      for (let x = 24; x < width; x += 24) {{
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }}
      for (let y = 24; y < height; y += 24) {{
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }}
    }};
    const adminPaintClamp = (value, min, max) => Math.max(min, Math.min(max, value));
    const adminPaintSelectionBounds = () => adminPaintSelection
      ? {{ x: adminPaintSelection.x, y: adminPaintSelection.y, w: adminPaintSelection.w, h: adminPaintSelection.h }}
      : null;
    const adminPaintPointInBounds = (point, bounds, pad = 0) => Boolean(bounds
      && point.x >= bounds.x - pad
      && point.y >= bounds.y - pad
      && point.x <= bounds.x + bounds.w + pad
      && point.y <= bounds.y + bounds.h + pad);
    const adminPaintHandleBounds = (bounds) => ({{
      x: bounds.x + bounds.w - 8,
      y: bounds.y + bounds.h - 8,
      w: 16,
      h: 16,
    }});
    const adminPaintRect = (start, end) => {{
      const x = Math.min(start.x, end.x);
      const y = Math.min(start.y, end.y);
      const w = Math.abs(end.x - start.x);
      const h = Math.abs(end.y - start.y);
      return {{ x, y, w, h }};
    }};
    const adminPaintSelectionCanvas = (imageData) => {{
      const canvas = document.createElement("canvas");
      canvas.width = imageData.width;
      canvas.height = imageData.height;
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.putImageData(imageData, 0, 0);
      return canvas;
    }};
    const createAdminPaintSelection = (rect) => {{
      adminPaintEnsureBuffer();
      if (!adminPaintBufferCanvas) return;
      const safeRect = {{
        x: Math.round(adminPaintClamp(rect.x, 0, adminPaintBufferCanvas.width)),
        y: Math.round(adminPaintClamp(rect.y, 0, adminPaintBufferCanvas.height)),
        w: Math.round(Math.max(0, rect.w)),
        h: Math.round(Math.max(0, rect.h)),
      }};
      safeRect.w = Math.min(safeRect.w, adminPaintBufferCanvas.width - safeRect.x);
      safeRect.h = Math.min(safeRect.h, adminPaintBufferCanvas.height - safeRect.y);
      if (safeRect.w < 5 || safeRect.h < 5) {{
        adminPaintSelection = null;
        return;
      }}
      const ctx = adminPaintBufferCtx();
      if (!ctx) return;
      const imageData = ctx.getImageData(safeRect.x, safeRect.y, safeRect.w, safeRect.h);
      ctx.clearRect(safeRect.x, safeRect.y, safeRect.w, safeRect.h);
      adminPaintSelection = {{
        ...safeRect,
        canvas: adminPaintSelectionCanvas(imageData),
        kind: "region",
      }};
    }};
    const renderAdminPaintSelection = (ctx) => {{
      const selection = adminPaintSelection;
      if (!selection) return;
      if (selection.canvas) {{
        ctx.drawImage(selection.canvas, selection.x, selection.y, selection.w, selection.h);
      }}
      ctx.save();
      ctx.setLineDash([7, 5]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#ff8e48";
      ctx.strokeRect(selection.x, selection.y, selection.w, selection.h);
      ctx.setLineDash([]);
      const handle = adminPaintHandleBounds(selection);
      ctx.fillStyle = "#ff8e48";
      ctx.strokeStyle = "#061112";
      ctx.fillRect(handle.x, handle.y, handle.w, handle.h);
      ctx.strokeRect(handle.x, handle.y, handle.w, handle.h);
      ctx.restore();
    }};
    const renderAdminPaintDraftRect = (ctx) => {{
      if (!adminPaintPointer || adminPaintPointer.type !== "select-region") return;
      const rect = adminPaintRect(adminPaintPointer.start, adminPaintPointer.current || adminPaintPointer.start);
      if (rect.w < 2 || rect.h < 2) return;
      ctx.save();
      ctx.setLineDash([7, 5]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#46f0d7";
      ctx.fillStyle = "rgba(70, 240, 215, 0.08)";
      ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
      ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
      ctx.restore();
    }};
    const commitAdminPaintSelection = () => {{
      if (!adminPaintSelection || !adminPaintSelection.canvas) {{
        adminPaintSelection = null;
        return;
      }}
      adminPaintEnsureBuffer();
      const ctx = adminPaintBufferCtx();
      if (ctx && adminPaintBufferCanvas) {{
        ctx.drawImage(
          adminPaintSelection.canvas,
          Math.round(adminPaintSelection.x),
          Math.round(adminPaintSelection.y),
          Math.round(adminPaintSelection.w),
          Math.round(adminPaintSelection.h)
        );
      }}
      adminPaintSelection = null;
    }};
    const updateAdminPaintZoomLabel = () => {{
      if (adminPaintZoomLabel) adminPaintZoomLabel.textContent = `${{Math.round(adminPaintZoom * 100)}}%`;
    }};
    const setAdminPaintZoom = (nextZoom) => {{
      adminPaintZoom = adminPaintClamp(Number(nextZoom || 1), 0.35, 3);
      updateAdminPaintZoomLabel();
      resizeAdminPaintCanvas();
      if (adminPaintCanvas && adminPaintCanvas.parentElement) {{
        const stage = adminPaintCanvas.parentElement;
        stage.scrollLeft = Math.max(0, (stage.scrollWidth - stage.clientWidth) / 2);
        stage.scrollTop = Math.max(0, (stage.scrollHeight - stage.clientHeight) / 2);
      }}
    }};
    const adminPaintExportCanvas = () => {{
      adminPaintEnsureBuffer();
      if (!adminPaintBufferCanvas) return null;
      const canvas = document.createElement("canvas");
      canvas.width = adminPaintBufferCanvas.width;
      canvas.height = adminPaintBufferCanvas.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.drawImage(adminPaintBufferCanvas, 0, 0);
      if (adminPaintSelection && adminPaintSelection.canvas) {{
        ctx.drawImage(
          adminPaintSelection.canvas,
          Math.round(adminPaintSelection.x),
          Math.round(adminPaintSelection.y),
          Math.round(adminPaintSelection.w),
          Math.round(adminPaintSelection.h)
        );
      }}
      return canvas;
    }};
    const fitAdminPaintCanvasElement = () => {{
      if (!adminPaintCanvas || !adminPaintCanvas.parentElement) return;
      const stage = adminPaintCanvas.parentElement;
      const rect = stage.getBoundingClientRect();
      if (rect.width < 20 || rect.height < 20) return;
      const styles = window.getComputedStyle(stage);
      const padX = Number.parseFloat(styles.paddingLeft || "0") + Number.parseFloat(styles.paddingRight || "0");
      const padY = Number.parseFloat(styles.paddingTop || "0") + Number.parseFloat(styles.paddingBottom || "0");
      const availableWidth = Math.max(1, rect.width - padX);
      const availableHeight = Math.max(1, rect.height - padY);
      const ratio = ADMIN_PAINT_BOARD_WIDTH / ADMIN_PAINT_BOARD_HEIGHT;
      let cssWidth = availableWidth;
      let cssHeight = cssWidth / ratio;
      if (cssHeight > availableHeight) {{
        cssHeight = availableHeight;
        cssWidth = cssHeight * ratio;
      }}
      cssWidth *= adminPaintZoom;
      cssHeight *= adminPaintZoom;
      adminPaintCanvas.style.width = `${{Math.max(1, Math.floor(cssWidth))}}px`;
      adminPaintCanvas.style.height = `${{Math.max(1, Math.floor(cssHeight))}}px`;
    }};
    const resizeAdminPaintCanvas = () => {{
      if (!adminPaintCanvas) return;
      fitAdminPaintCanvasElement();
      const rect = adminPaintCanvas.getBoundingClientRect();
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      const cssWidth = Math.max(1, rect.width || adminPaintCanvas.clientWidth || 900);
      const cssHeight = Math.max(1, rect.height || adminPaintCanvas.clientHeight || 560);
      const nextWidth = Math.max(1, Math.round(cssWidth * dpr));
      const nextHeight = Math.max(1, Math.round(cssHeight * dpr));
      if (adminPaintCanvas.width !== nextWidth || adminPaintCanvas.height !== nextHeight) {{
        adminPaintCanvas.width = nextWidth;
        adminPaintCanvas.height = nextHeight;
      }}
      adminPaintEnsureBuffer();
      const ctx = adminPaintCtx();
      if (!ctx) return;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, adminPaintCanvas.width, adminPaintCanvas.height);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawAdminPaintGrid(ctx, cssWidth, cssHeight);
      if (adminPaintBufferCanvas) {{
        ctx.drawImage(adminPaintBufferCanvas, 0, 0, adminPaintBufferCanvas.width, adminPaintBufferCanvas.height, 0, 0, cssWidth, cssHeight);
      }}
      const boardWidth = adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH;
      const boardHeight = adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT;
      ctx.save();
      ctx.scale(cssWidth / Math.max(1, boardWidth), cssHeight / Math.max(1, boardHeight));
      renderAdminPaintSelection(ctx);
      renderAdminPaintDraftRect(ctx);
      ctx.restore();
      positionAdminPaintRemoteCursor();
    }};
    const adminPaintPoint = (event) => {{
      adminPaintEnsureBuffer();
      const rect = adminPaintCanvas.getBoundingClientRect();
      const boardWidth = adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH;
      const boardHeight = adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT;
      return {{
        x: Math.max(0, Math.min(boardWidth, (event.clientX - rect.left) * boardWidth / Math.max(1, rect.width))),
        y: Math.max(0, Math.min(boardHeight, (event.clientY - rect.top) * boardHeight / Math.max(1, rect.height))),
      }};
    }};
    const ensureAdminPaintRemoteCursorNode = () => {{
      if (adminPaintRemoteCursorNode && adminPaintRemoteCursorNode.isConnected) return adminPaintRemoteCursorNode;
      const stage = adminPaintCanvas && adminPaintCanvas.parentElement;
      if (!stage) return null;
      const node = document.createElement("div");
      node.className = "admin-paint-remote-cursor";
      node.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.className = "admin-paint-remote-label";
      label.textContent = adminPaintUser || "User";
      node.appendChild(label);
      stage.appendChild(node);
      adminPaintRemoteCursorNode = node;
      return node;
    }};
    const hideAdminPaintRemoteCursor = () => {{
      if (adminPaintRemoteCursorNode) adminPaintRemoteCursorNode.classList.remove("is-visible");
    }};
    const positionAdminPaintRemoteCursor = () => {{
      const cursor = adminPaintRemoteCursor;
      const node = ensureAdminPaintRemoteCursorNode();
      if (!node || !adminPaintCanvas || !cursor || !cursor.visible) {{
        hideAdminPaintRemoteCursor();
        return;
      }}
      const canvasRect = adminPaintCanvas.getBoundingClientRect();
      if (canvasRect.width < 2 || canvasRect.height < 2) {{
        hideAdminPaintRemoteCursor();
        return;
      }}
      const boardWidth = Number(cursor.width || 0) || (adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH);
      const boardHeight = Number(cursor.height || 0) || (adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT);
      const x = adminPaintClamp(Number(cursor.x || 0), 0, boardWidth) * canvasRect.width / Math.max(1, boardWidth);
      const y = adminPaintClamp(Number(cursor.y || 0), 0, boardHeight) * canvasRect.height / Math.max(1, boardHeight);
      const left = adminPaintCanvas.offsetLeft + x;
      const top = adminPaintCanvas.offsetTop + y;
      const label = node.querySelector(".admin-paint-remote-label");
      if (label) {{
        const mode = String(cursor.mode || "").trim();
        const name = String(cursor.label || adminPaintUser || "User").trim() || "User";
        label.textContent = `${{name}}${{mode ? " | " + mode : ""}}`;
      }}
      node.style.transform = `translate3d(${{left.toFixed(1)}}px, ${{top.toFixed(1)}}px, 0)`;
      node.classList.add("is-visible");
    }};
    const renderAdminPaintRemoteCursor = (cursor = null) => {{
      adminPaintRemoteCursor = cursor && cursor.visible ? cursor : null;
      positionAdminPaintRemoteCursor();
    }};
    const adminPaintCursorPayload = (point, visible = true) => {{
      adminPaintEnsureBuffer();
      const boardWidth = adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH;
      const boardHeight = adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT;
      return {{
        x: adminPaintClamp(Number(point && point.x || 0), 0, boardWidth),
        y: adminPaintClamp(Number(point && point.y || 0), 0, boardHeight),
        width: boardWidth,
        height: boardHeight,
        visible: Boolean(visible),
        mode: adminPaintMode || "paint",
        label: "Admin",
      }};
    }};
    const sendAdminPaintCursor = async () => {{
      if (!adminPaintUser || !adminPaintLocalCursor || adminPaintCursorSending) return;
      if (adminScreenUser === adminPaintUser && adminScreenControlChannelOpen()) return;
      adminPaintCursorSending = true;
      adminPaintLastCursorSentAt = Date.now();
      try {{
        await fetch("/paint/admin/cursor", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ username: adminPaintUser, cursor: adminPaintLocalCursor }}),
        }});
      }} catch (error) {{
      }} finally {{
        adminPaintCursorSending = false;
      }}
    }};
    const scheduleAdminPaintCursorSync = (delay = 20) => {{
      if (!adminPaintUser || !adminPaintLocalCursor) return;
      const elapsed = Date.now() - adminPaintLastCursorSentAt;
      const wait = Math.max(delay, 220 - elapsed, 0);
      window.clearTimeout(adminPaintCursorTimer);
      adminPaintCursorTimer = window.setTimeout(() => void sendAdminPaintCursor(), wait);
    }};
    const updateAdminPaintLocalCursor = (event, visible = true) => {{
      if (!adminPaintCanvas || !adminPaintUser) return;
      const point = visible ? adminPaintPoint(event) : (adminPaintLocalCursor || {{ x: 0, y: 0 }});
      adminPaintLocalCursor = adminPaintCursorPayload(point, visible);
      scheduleAdminPaintCursorSync(visible ? 120 : 0);
    }};
    const setAdminPaintMode = (mode) => {{
      const nextMode = ["select", "pen", "eraser", "text"].includes(mode) ? mode : "pen";
      if (adminPaintTextEditor && nextMode !== "text") {{
        commitAdminPaintTextEditor();
      }}
      if (adminPaintSelection && nextMode !== "select") {{
        commitAdminPaintSelection();
        scheduleAdminPaintSync(120);
      }}
      adminPaintMode = nextMode;
      adminPaintModeButtons.forEach((button) => {{
        const active = button.dataset.adminPaintMode === adminPaintMode;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      }});
      resizeAdminPaintCanvas();
    }};
    const clearAdminPaintCanvas = () => {{
      cancelAdminPaintTextEditor();
      adminPaintSelection = null;
      adminPaintEnsureBuffer();
      const ctx = adminPaintBufferCtx();
      if (ctx && adminPaintBufferCanvas) {{
        ctx.clearRect(0, 0, adminPaintBufferCanvas.width, adminPaintBufferCanvas.height);
      }}
      resizeAdminPaintCanvas();
    }};
    const deleteAdminPaintSelection = () => {{
      if (!adminPaintSelection) {{
        setAdminPaintStatus("Select or insert a picture first.");
        return;
      }}
      adminPaintSelection = null;
      adminPaintPointer = null;
      resizeAdminPaintCanvas();
      scheduleAdminPaintSync(80);
    }};
    const addAdminPaintImageFromDataUrl = (dataUrl) => {{
      const source = String(dataUrl || "");
      if (!source.startsWith("data:image/")) {{
        setAdminPaintStatus("Clipboard does not contain an image.");
        return;
      }}
      commitAdminPaintSelection();
      adminPaintEnsureBuffer();
      const image = new Image();
      image.onload = () => {{
        const boardWidth = adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH;
        const boardHeight = adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT;
        const maxWidth = boardWidth * 0.7;
        const maxHeight = boardHeight * 0.7;
        const naturalWidth = Math.max(1, image.naturalWidth || image.width || maxWidth);
        const naturalHeight = Math.max(1, image.naturalHeight || image.height || maxHeight);
        const scale = Math.min(1, maxWidth / naturalWidth, maxHeight / naturalHeight);
        const width = Math.max(24, Math.round(naturalWidth * scale));
        const height = Math.max(24, Math.round(naturalHeight * scale));
        const canvas = document.createElement("canvas");
        canvas.width = naturalWidth;
        canvas.height = naturalHeight;
        const ctx = canvas.getContext("2d");
        if (ctx) ctx.drawImage(image, 0, 0, naturalWidth, naturalHeight);
        adminPaintSelection = {{
          x: Math.round((boardWidth - width) / 2),
          y: Math.round((boardHeight - height) / 2),
          w: width,
          h: height,
          canvas,
          kind: "image",
        }};
        setAdminPaintMode("select");
        resizeAdminPaintCanvas();
        scheduleAdminPaintSync(120);
        setAdminPaintStatus("Picture inserted. Drag it or pull the corner to resize.");
      }};
      image.onerror = () => setAdminPaintStatus("Could not load picture.");
      image.src = source;
    }};
    const addAdminPaintImageFile = (file) => {{
      if (!file || !String(file.type || "").startsWith("image/")) {{
        setAdminPaintStatus("Choose an image file.");
        return;
      }}
      const reader = new FileReader();
      reader.onload = () => addAdminPaintImageFromDataUrl(String(reader.result || ""));
      reader.onerror = () => setAdminPaintStatus("Could not read picture.");
      reader.readAsDataURL(file);
    }};
    const pasteAdminPaintImageFromClipboard = async () => {{
      if (navigator.clipboard && navigator.clipboard.read) {{
        try {{
          const items = await navigator.clipboard.read();
          for (const item of items) {{
            const imageType = item.types.find((type) => String(type || "").startsWith("image/"));
            if (imageType) {{
              const blob = await item.getType(imageType);
              addAdminPaintImageFile(blob);
              return;
            }}
          }}
        }} catch (error) {{
        }}
      }}
      setAdminPaintStatus("Copy an image, then press Ctrl+V while Paint is open.");
    }};
    const drawAdminPaintLine = (from, to, eraser = false) => {{
      adminPaintEnsureBuffer();
      const ctx = adminPaintBufferCtx();
      if (!ctx) return;
      const size = Math.max(1, Number(adminPaintSize && adminPaintSize.value || 6));
      ctx.save();
      ctx.globalCompositeOperation = eraser ? "destination-out" : "source-over";
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.lineWidth = eraser ? Math.max(14, size * 2.4) : size;
      ctx.strokeStyle = adminPaintColor && adminPaintColor.value || "#0f172a";
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
      ctx.restore();
      resizeAdminPaintCanvas();
    }};
    const adminPaintTextLines = (text) => {{
      const raw = String(text == null ? "" : text).replace(/\\r/g, "");
      const lines = raw.split("\\n").slice(0, 8);
      return lines.length ? lines : ["Text"];
    }};
    const adminPaintCurrentTextSize = () => adminPaintClamp(14 + Math.max(1, Number(adminPaintSize && adminPaintSize.value || 6)) * 2.2, 16, 82);
    const drawAdminPaintTextToBuffer = (options = {{}}) => {{
      const text = String(options.text == null ? "" : options.text).trim();
      if (!text) return;
      adminPaintEnsureBuffer();
      const ctx = adminPaintBufferCtx();
      if (!ctx) return;
      const size = Math.max(10, Number(options.size || adminPaintCurrentTextSize()));
      ctx.save();
      ctx.fillStyle = options.color || adminPaintColor && adminPaintColor.value || "#0f172a";
      ctx.font = `900 ${{size}}px Inter, Segoe UI, system-ui, sans-serif`;
      ctx.textBaseline = "top";
      adminPaintTextLines(text).forEach((line, index) => {{
        ctx.fillText(line || " ", Number(options.x || 0), Number(options.y || 0) + index * size * 1.24);
      }});
      ctx.restore();
      resizeAdminPaintCanvas();
    }};
    const cancelAdminPaintTextEditor = () => {{
      if (adminPaintTextEditor) {{
        adminPaintTextEditor.remove();
        adminPaintTextEditor = null;
      }}
    }};
    const commitAdminPaintTextEditor = () => {{
      const editor = adminPaintTextEditor;
      if (!editor) return;
      adminPaintTextEditor = null;
      const text = String(editor.value || "").trim();
      if (text) {{
        drawAdminPaintTextToBuffer({{
          text,
          x: Number(editor.dataset.paintX || 0),
          y: Number(editor.dataset.paintY || 0),
          color: editor.dataset.paintColor || adminPaintColor && adminPaintColor.value || "#0f172a",
          size: Number(editor.dataset.paintSize || adminPaintCurrentTextSize()),
        }});
        if (adminPaintText) adminPaintText.value = text;
      }}
      editor.remove();
      resizeAdminPaintCanvas();
      scheduleAdminPaintSync(120);
    }};
    const showAdminPaintTextEditor = (point) => {{
      commitAdminPaintSelection();
      cancelAdminPaintTextEditor();
      if (!adminPaintCanvas) return;
      const stage = adminPaintCanvas.parentElement;
      if (!stage) return;
      const canvasRect = adminPaintCanvas.getBoundingClientRect();
      const stageRect = stage.getBoundingClientRect();
      const size = adminPaintCurrentTextSize();
      adminPaintEnsureBuffer();
      const boardWidth = adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH;
      const boardHeight = adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT;
      const displayX = point.x * canvasRect.width / Math.max(1, boardWidth);
      const displayY = point.y * canvasRect.height / Math.max(1, boardHeight);
      const displaySize = adminPaintClamp(size * Math.min(
        canvasRect.width / Math.max(1, boardWidth),
        canvasRect.height / Math.max(1, boardHeight)
      ), 12, 72);
      const editor = document.createElement("textarea");
      editor.className = "admin-paint-text-editor";
      editor.value = String(adminPaintText && adminPaintText.value || "").trim();
      editor.placeholder = "Type text";
      editor.dataset.paintX = String(point.x);
      editor.dataset.paintY = String(point.y);
      editor.dataset.paintColor = adminPaintColor && adminPaintColor.value || "#0f172a";
      editor.dataset.paintSize = String(size);
      editor.style.left = `${{adminPaintClamp(canvasRect.left - stageRect.left + displayX + stage.scrollLeft, 12, Math.max(12, stage.scrollWidth - 180))}}px`;
      editor.style.top = `${{adminPaintClamp(canvasRect.top - stageRect.top + displayY + stage.scrollTop, 12, Math.max(12, stage.scrollHeight - 76))}}px`;
      editor.style.fontSize = `${{displaySize}}px`;
      editor.style.color = editor.dataset.paintColor;
      ["pointerdown", "mousedown", "click", "touchstart"].forEach((name) => {{
        editor.addEventListener(name, (event) => event.stopPropagation());
      }});
      editor.addEventListener("keydown", (event) => {{
        event.stopPropagation();
        if (event.key === "Enter" && !event.shiftKey) {{
          event.preventDefault();
          commitAdminPaintTextEditor();
        }} else if (event.key === "Escape") {{
          event.preventDefault();
          cancelAdminPaintTextEditor();
          resizeAdminPaintCanvas();
        }}
      }});
      editor.addEventListener("input", () => {{
        if (adminPaintText) adminPaintText.value = editor.value;
      }});
      editor.addEventListener("blur", () => {{
        window.setTimeout(() => {{
          if (adminPaintTextEditor === editor) commitAdminPaintTextEditor();
        }}, 80);
      }});
      stage.appendChild(editor);
      adminPaintTextEditor = editor;
      editor.focus({{ preventScroll: true }});
      editor.select();
      window.setTimeout(() => editor.focus({{ preventScroll: true }}), 30);
    }};
    const adminPaintSnapshot = () => {{
      const exportCanvas = adminPaintExportCanvas();
      return exportCanvas ? exportCanvas.toDataURL("image/png") : "";
    }};
    const sendAdminPaintSnapshot = async () => {{
      if (!adminPaintUser || !adminPaintCanvas || adminPaintSending || adminPaintApplyingRemote) return;
      adminPaintSending = true;
      try {{
        const response = await fetch("/paint/admin/sync", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            username: adminPaintUser,
            data: adminPaintSnapshot(),
            width: ADMIN_PAINT_BOARD_WIDTH,
            height: ADMIN_PAINT_BOARD_HEIGHT,
          }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not sync paint.");
        if (payload.state) adminPaintRevision = Math.max(adminPaintRevision, Number(payload.state.revision || 0));
        if (payload.users) {{
          adminChatState = {{ users: payload.users || [], online_count: Number(payload.online_count || 0) }};
          renderOnlineUsers(adminChatState.users, adminChatState);
        }}
        setAdminPaintStatus(`Paint synced rev ${{adminPaintRevision || 0}}.`);
      }} catch (error) {{
        setAdminPaintStatus(String(error && error.message ? error.message : error));
      }} finally {{
        adminPaintSending = false;
      }}
    }};
    const scheduleAdminPaintSync = (delay = 180) => {{
      window.clearTimeout(adminPaintSendTimer);
      adminPaintSendTimer = window.setTimeout(() => void sendAdminPaintSnapshot(), delay);
    }};
    const applyAdminPaintState = (state = {{}}) => {{
      const revision = Number(state.revision || 0);
      if (!revision || revision <= adminPaintRevision || adminPaintPointer || adminPaintSelection || adminPaintTextEditor) return;
      adminPaintRevision = revision;
      adminPaintApplyingRemote = true;
      const data = String(state.data || "");
      if (!data) {{
        clearAdminPaintCanvas();
        adminPaintApplyingRemote = false;
        setAdminPaintStatus(`Paint rev ${{revision}}.`);
        return;
      }}
      const image = new Image();
      image.onload = () => {{
        adminPaintEnsureBuffer();
        const ctx = adminPaintBufferCtx();
        if (ctx && adminPaintBufferCanvas) {{
          ctx.clearRect(0, 0, adminPaintBufferCanvas.width, adminPaintBufferCanvas.height);
          ctx.drawImage(image, 0, 0, adminPaintBufferCanvas.width, adminPaintBufferCanvas.height);
        }}
        resizeAdminPaintCanvas();
        adminPaintApplyingRemote = false;
        setAdminPaintStatus(`Paint rev ${{revision}} from ${{state.updated_by || "user"}}.`);
      }};
      image.onerror = () => {{
        adminPaintApplyingRemote = false;
        setAdminPaintStatus("Could not load remote paint.");
      }};
      image.src = data;
    }};
    const adminPaintPollDelay = (changed = false) => {{
      if (!dashboardPollIsFocused()) return DASHBOARD_HIDDEN_POLL_MS;
      if (changed) return 320;
      const recent = Date.now() - Math.max(Number(adminPaintLastPollChangedAt || 0), Number(adminPaintLastRemoteCursorAt || 0));
      return recent < 2500 ? 450 : 1200;
    }};
    const adminPaintCoveredByScreenWebRtc = () => Boolean(
      adminPaintUser
      && adminScreenUser === adminPaintUser
      && adminScreenSession
      && adminScreenSession.state === "active"
      && adminScreenControlChannelOpen()
    );
    const scheduleAdminPaintPoll = (delay = 0) => {{
      if (!adminPaintUser) return;
      window.clearTimeout(adminPaintPollTimer);
      adminPaintPollTimer = window.setTimeout(() => void pollAdminPaint({{ scheduleNext: true }}), Math.max(250, Number(delay) || 0));
    }};
    const pollAdminPaint = async (options = {{}}) => {{
      if (!adminPaintUser || adminPaintPollInFlight) return;
      if (adminPaintCoveredByScreenWebRtc()) {{
        if (options && options.scheduleNext && adminPaintUser) {{
          scheduleAdminPaintPoll(3000);
        }}
        return;
      }}
      adminPaintPollInFlight = true;
      let changed = false;
      try {{
        const response = await fetch(`/paint/admin/state?username=${{encodeURIComponent(adminPaintUser)}}&after=${{encodeURIComponent(String(adminPaintRevision || 0))}}`, {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not poll paint.");
        if (payload.state) {{
          const previousRevision = Number(adminPaintRevision || 0);
          const userCursor = payload.state.cursors && payload.state.cursors.user;
          const cursorAt = Number(userCursor && userCursor.updated_at || 0);
          if (cursorAt && cursorAt !== adminPaintLastRemoteCursorAt) {{
            adminPaintLastRemoteCursorAt = cursorAt;
            changed = true;
          }}
          renderAdminPaintRemoteCursor(payload.state.cursors && payload.state.cursors.user);
          applyAdminPaintState(payload.state);
          if (Number(adminPaintRevision || 0) !== previousRevision) {{
            changed = true;
          }}
          if (changed) adminPaintLastPollChangedAt = Date.now();
        }}
      }} catch (error) {{
        setAdminPaintStatus(String(error && error.message ? error.message : error));
      }} finally {{
        adminPaintPollInFlight = false;
        if (options && options.scheduleNext && adminPaintUser) {{
          scheduleAdminPaintPoll(adminPaintPollDelay(changed));
        }}
      }}
    }};
    const stopAdminPaintPolling = () => {{
      if (adminPaintPollTimer) {{
        window.clearTimeout(adminPaintPollTimer);
        adminPaintPollTimer = 0;
      }}
      adminPaintPollInFlight = false;
    }};
    const startAdminPaintPolling = () => {{
      stopAdminPaintPolling();
      void pollAdminPaint({{ scheduleNext: true }});
    }};
    document.addEventListener("visibilitychange", () => {{
      if (!adminPaintUser) return;
      scheduleAdminPaintPoll(dashboardPollIsFocused() ? 0 : DASHBOARD_HIDDEN_POLL_MS);
    }});
    window.addEventListener("focus", () => {{
      if (adminPaintUser) scheduleAdminPaintPoll(0);
    }});
    window.addEventListener("blur", () => {{
      if (adminPaintUser) scheduleAdminPaintPoll(DASHBOARD_HIDDEN_POLL_MS);
    }});
    const openAdminPaint = (itemOrUsername) => {{
      const username = typeof itemOrUsername === "string" ? itemOrUsername : (itemOrUsername && itemOrUsername.username || "");
      if (!username) return;
      adminPaintUser = username;
      adminPaintRevision = 0;
      adminPaintSelection = null;
      cancelAdminPaintTextEditor();
      if (adminPaintTitle) adminPaintTitle.textContent = `Paint with ${{username}}`;
      document.documentElement.classList.add("admin-paint-performance-mode");
      if (adminPaintModal) adminPaintModal.classList.add("is-open");
      if (typeof pollChatAdmin === "function") void pollChatAdmin();
      window.requestAnimationFrame(() => {{
        resizeAdminPaintCanvas();
        clearAdminPaintCanvas();
        startAdminPaintPolling();
      }});
      setAdminPaintStatus("Paint sync connecting...");
    }};
    const closeAdminPaint = () => {{
      if (adminPaintTextEditor) {{
        commitAdminPaintTextEditor();
      }}
      if (adminPaintSelection) {{
        commitAdminPaintSelection();
        scheduleAdminPaintSync(80);
      }}
      if (adminPaintModal) adminPaintModal.classList.remove("is-open");
      document.documentElement.classList.remove("admin-paint-performance-mode");
      stopAdminPaintPolling();
      adminPaintLocalCursor = adminPaintCursorPayload(adminPaintLocalCursor || {{ x: 0, y: 0 }}, false);
      window.clearTimeout(adminPaintCursorTimer);
      void sendAdminPaintCursor();
      hideAdminPaintRemoteCursor();
      adminPaintUser = "";
      adminPaintPointer = null;
    }};
    const toggleAdminPaintFullscreen = async () => {{
      const target = adminPaintCard || adminPaintModal;
      if (!target) return;
      try {{
        if (document.fullscreenElement) {{
          await document.exitFullscreen();
        }} else if (target.requestFullscreen) {{
          await target.requestFullscreen();
        }}
      }} catch (error) {{
        setAdminPaintStatus(String(error && error.message ? error.message : error));
      }}
      window.setTimeout(resizeAdminPaintCanvas, 80);
    }};
    const openAdminPaintInTab = () => {{
      if (!adminPaintUser) return;
      try {{
        const url = new URL(window.location.href);
        url.searchParams.set("paint_user", adminPaintUser);
        const next = window.open(url.toString(), "_blank", "noopener");
        if (!next) setAdminPaintStatus("Browser blocked the new tab.");
      }} catch (error) {{
        setAdminPaintStatus(String(error && error.message ? error.message : error));
      }}
    }};
    const handleAdminPaintPointerDown = (event) => {{
      if (!adminPaintCanvas || !adminPaintUser) return;
      event.preventDefault();
      resizeAdminPaintCanvas();
      const point = adminPaintPoint(event);
      if (adminPaintMode === "select") {{
        const selectionBounds = adminPaintSelectionBounds();
        const handleBounds = selectionBounds ? adminPaintHandleBounds(selectionBounds) : null;
        if (handleBounds && adminPaintPointInBounds(point, handleBounds, 2)) {{
          adminPaintPointer = {{
            type: "resize-selection",
            start: point,
            origin: {{
              x: adminPaintSelection.x,
              y: adminPaintSelection.y,
              w: adminPaintSelection.w,
              h: adminPaintSelection.h,
            }},
          }};
          try {{ adminPaintCanvas.setPointerCapture(event.pointerId); }} catch (error) {{}}
          return;
        }}
        if (selectionBounds && adminPaintPointInBounds(point, selectionBounds, 0)) {{
          adminPaintPointer = {{
            type: "move-selection",
            start: point,
            origin: {{ x: adminPaintSelection.x, y: adminPaintSelection.y }},
          }};
          try {{ adminPaintCanvas.setPointerCapture(event.pointerId); }} catch (error) {{}}
          return;
        }}
        if (adminPaintSelection) {{
          commitAdminPaintSelection();
          scheduleAdminPaintSync(120);
        }}
        adminPaintPointer = {{ type: "select-region", start: point, current: point }};
        resizeAdminPaintCanvas();
        try {{ adminPaintCanvas.setPointerCapture(event.pointerId); }} catch (error) {{}}
        return;
      }}
      if (adminPaintSelection) {{
        commitAdminPaintSelection();
        scheduleAdminPaintSync(120);
      }}
      if (adminPaintMode === "text") {{
        showAdminPaintTextEditor(point);
        return;
      }}
      adminPaintPointer = {{ type: "draw", last: point, eraser: adminPaintMode === "eraser" }};
      drawAdminPaintLine(point, point, adminPaintPointer.eraser);
      try {{ adminPaintCanvas.setPointerCapture(event.pointerId); }} catch (error) {{}}
    }};
    const handleAdminPaintPointerMove = (event) => {{
      if (!adminPaintPointer || !adminPaintCanvas) return;
      event.preventDefault();
      const point = adminPaintPoint(event);
      if (adminPaintPointer.type === "move-selection" && adminPaintSelection) {{
        const dx = point.x - adminPaintPointer.start.x;
        const dy = point.y - adminPaintPointer.start.y;
        const maxX = Math.max(0, (adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH) - adminPaintSelection.w);
        const maxY = Math.max(0, (adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT) - adminPaintSelection.h);
        adminPaintSelection.x = adminPaintClamp(adminPaintPointer.origin.x + dx, 0, maxX);
        adminPaintSelection.y = adminPaintClamp(adminPaintPointer.origin.y + dy, 0, maxY);
        resizeAdminPaintCanvas();
        scheduleAdminPaintSync(180);
        return;
      }}
      if (adminPaintPointer.type === "resize-selection" && adminPaintSelection) {{
        const dx = point.x - adminPaintPointer.start.x;
        const dy = point.y - adminPaintPointer.start.y;
        const origin = adminPaintPointer.origin || adminPaintSelection;
        const maxW = Math.max(12, (adminPaintBufferCanvas ? adminPaintBufferCanvas.width : ADMIN_PAINT_BOARD_WIDTH) - origin.x);
        const maxH = Math.max(12, (adminPaintBufferCanvas ? adminPaintBufferCanvas.height : ADMIN_PAINT_BOARD_HEIGHT) - origin.y);
        adminPaintSelection.w = adminPaintClamp(origin.w + dx, 12, maxW);
        adminPaintSelection.h = adminPaintClamp(origin.h + dy, 12, maxH);
        resizeAdminPaintCanvas();
        scheduleAdminPaintSync(180);
        return;
      }}
      if (adminPaintPointer.type === "select-region") {{
        adminPaintPointer.current = point;
        resizeAdminPaintCanvas();
        return;
      }}
      drawAdminPaintLine(adminPaintPointer.last || point, point, Boolean(adminPaintPointer.eraser));
      adminPaintPointer.last = point;
    }};
    const handleAdminPaintPointerEnd = (event) => {{
      if (!adminPaintPointer) return;
      const pointerType = adminPaintPointer.type;
      if (pointerType === "select-region") {{
        const rect = adminPaintRect(adminPaintPointer.start, adminPaintPointer.current || adminPaintPointer.start);
        createAdminPaintSelection(rect);
        resizeAdminPaintCanvas();
      }}
      try {{ adminPaintCanvas.releasePointerCapture(event.pointerId); }} catch (error) {{}}
      adminPaintPointer = null;
      scheduleAdminPaintSync();
    }};
    const scrollAdminChatToBottom = () => {{
      if (!adminChatLog) return;
      const apply = () => {{ adminChatLog.scrollTop = adminChatLog.scrollHeight; }};
      apply();
      window.requestAnimationFrame(apply);
      window.setTimeout(apply, 80);
      window.setTimeout(apply, 260);
    }};
    const renderAdminAttachments = (msg, item = {{}}, scrollOnImageLoad = false) => {{
      const attachments = adminChatAttachments(item);
      if (!attachments.length) return;
      const wrap = document.createElement("div");
      wrap.className = "admin-attachments";
      attachments.forEach((attachment) => {{
        const name = String(attachment.name || "attachment");
        const src = adminAttachmentUrl(attachment);
        const downloadSrc = adminAttachmentUrl(attachment, true) || src;
        const mime = String(attachment.mime || "");
        const isImage = String(attachment.kind || "").toLowerCase() === "image" || mime.startsWith("image/");
        const isAudio = String(attachment.kind || "").toLowerCase() === "audio" || mime.startsWith("audio/");
        if (isImage) {{
          const button = document.createElement("button");
          button.type = "button";
          button.className = "admin-thumb";
          button.title = name;
          const img = document.createElement("img");
          if (scrollOnImageLoad) {{
            img.addEventListener("load", scrollAdminChatToBottom, {{ once: true }});
          }}
          img.src = src;
          img.alt = name;
          button.appendChild(img);
          button.addEventListener("click", (event) => {{
            event.stopPropagation();
            openAdminImageViewer(src, downloadSrc, name);
          }});
          wrap.appendChild(button);
        }} else if (isAudio) {{
          const audioWrap = document.createElement("div");
          audioWrap.className = "admin-audio-clip";
          audioWrap.addEventListener("click", (event) => event.stopPropagation());
          const audio = document.createElement("audio");
          audio.controls = true;
          audio.preload = "metadata";
          audio.src = src;
          audio.addEventListener("click", (event) => event.stopPropagation());
          const link = document.createElement("a");
          link.className = "admin-audio-download";
          link.href = downloadSrc;
          link.download = name;
          link.target = "_blank";
          link.rel = "noopener";
          link.addEventListener("click", (event) => event.stopPropagation());
          const size = formatAdminAttachmentSize(attachment.size);
          link.textContent = size ? `${{name}} | ${{size}}` : name;
          audioWrap.append(audio, link);
          wrap.appendChild(audioWrap);
        }} else {{
          const link = document.createElement("a");
          link.className = "admin-file";
          link.href = downloadSrc;
          link.download = name;
          link.target = "_blank";
          link.rel = "noopener";
          const size = formatAdminAttachmentSize(attachment.size);
          link.textContent = size ? `${{name}} | ${{size}}` : name;
          wrap.appendChild(link);
        }}
      }});
      msg.appendChild(wrap);
    }};
    const renderAdminChatLog = (username, autoplayMessageIds = null, options = {{}}) => {{
      const record = adminChatUserRecord(username);
      const rows = record && Array.isArray(record.messages) ? record.messages : [];
      const autoplayIds = autoplayMessageIds instanceof Set ? autoplayMessageIds : null;
      const shouldScroll = Boolean(options && options.scroll);
      adminChatRenderedUser = username || "";
      adminChatRenderedSignature = adminChatRowsSignature(rows);
      adminChatLog.textContent = "";
      if (!rows.length) {{
        const empty = document.createElement("div");
        empty.className = "admin-msg";
        empty.textContent = "No messages yet.";
        adminChatLog.appendChild(empty);
        if (shouldScroll) scrollAdminChatToBottom();
        return;
      }}
      rows.forEach((item) => {{
        const msg = document.createElement("div");
        msg.className = "admin-msg" + (item.sender === "admin" ? " is-admin" : "");
        const voiceLabel = item.voice_label || (item.audio && item.audio.label) || "";
        const text = document.createElement("div");
        text.className = "admin-msg-text";
        text.textContent = `${{item.sender === "admin" ? "Admin" : username}}: ${{item.text || ""}}${{voiceLabel ? " | " + voiceLabel : ""}}`;
        msg.appendChild(text);
        renderAdminAttachments(msg, item, shouldScroll);
        if (item.sender === "admin") {{
          const readState = document.createElement("div");
          readState.className = "admin-read-state";
          readState.textContent = item.peer_read ? "Seen" : "Sent";
          msg.appendChild(readState);
        }}
        const audioPath = item.audio_path || (item.audio && item.audio.path) || "";
        if (audioPath) {{
          msg.title = "Click to play voice";
          msg.addEventListener("click", () => {{
            const audio = new Audio(`/server-data/asset?path=${{encodeURIComponent(audioPath)}}`);
            audio.play().catch(() => {{}});
          }});
          const audioId = `${{item.id || ""}}:${{audioPath}}`;
          if (item.sender === "user" && autoplayIds && autoplayIds.has(Number(item.id || 0)) && !adminChatPlayedAudioIds.has(audioId) && adminChatModal.classList.contains("is-open")) {{
            adminChatPlayedAudioIds.add(audioId);
            const audio = new Audio(`/server-data/asset?path=${{encodeURIComponent(audioPath)}}`);
            audio.play().catch(() => {{}});
          }}
        }}
        adminChatLog.appendChild(msg);
      }});
      if (shouldScroll) scrollAdminChatToBottom();
    }};
    const openAdminChat = async (username) => {{
      adminChatUser = username || "";
      if (!adminChatUser) return;
      adminChatTitle.textContent = `Chat with ${{adminChatUser}}`;
      adminChatModal.classList.add("is-open");
      renderAdminChatLog(adminChatUser);
      try {{
        await fetch("/chat/admin/read", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ username: adminChatUser }}),
        }});
      }} catch (error) {{
      }}
      pollChatAdmin();
    }};
    const closeAdminChat = () => {{
      cancelAdminChatVoice();
      adminChatModal.classList.remove("is-open");
      adminChatUser = "";
    }};
    if (adminChatClose) adminChatClose.addEventListener("click", closeAdminChat);
    if (adminChatModal) adminChatModal.addEventListener("click", (event) => {{
      if (event.target === adminChatModal) closeAdminChat();
    }});
    const sendAdminChat = async (mode = "vi") => {{
      const english = mode === "en";
      const input = english ? adminChatEnInput : adminChatInput;
      const button = english ? adminChatEnSend : adminChatSend;
      const voiceSelect = english ? adminChatEnVoice : adminChatViVoice;
      const audioEnabled = english ? adminChatEnAudioEnabled : adminChatViAudioEnabled;
      const text = String(input && input.value || "").trim();
      if (!adminChatUser || !text) return;
      if (button) button.disabled = true;
      if (adminChatVoiceState) adminChatVoiceState.textContent = audioEnabled ? "Creating voice..." : "Sending text...";
      try {{
        const response = await fetch("/chat/admin/send", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            username: adminChatUser,
            text,
            audio_enabled: Boolean(audioEnabled),
            voice: voiceSelect ? voiceSelect.value : "",
            translated_from: english && adminChatInput ? adminChatInput.value : "",
          }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not send chat.");
        if (input) input.value = "";
        if (!english && adminChatEnInput && adminTranslateEnabled) adminChatEnInput.value = "";
        adminChatState = {{ users: payload.users || [], online_count: Number(payload.online_count || 0) }};
        renderOnlineUsers(adminChatState.users, adminChatState);
        renderAdminChatLog(adminChatUser, null, {{ scroll: true }});
        if (adminChatVoiceState) adminChatVoiceState.textContent = audioEnabled ? "Voice message sent." : "Text message sent.";
      }} catch (error) {{
        const message = String(error && error.message ? error.message : error);
        messageNode.textContent = message;
        if (adminChatVoiceState) adminChatVoiceState.textContent = message;
      }} finally {{
        if (button) button.disabled = false;
      }}
    }};
    const currentAdminAttachInput = () => {{
      if (document.activeElement === adminChatEnInput) return adminChatEnInput;
      return adminChatInput || adminChatEnInput;
    }};
    const appendAdminSpeechTextToInput = (input, text) => {{
      const value = String(text || "").replace(/\s+/g, " ").trim();
      if (!input || !value) return false;
      const current = String(input.value || "");
      const start = typeof input.selectionStart === "number" ? input.selectionStart : current.length;
      const end = typeof input.selectionEnd === "number" ? input.selectionEnd : start;
      const needsSpaceBefore = start > 0 && current[start - 1] && !/\s/.test(current[start - 1]);
      const needsSpaceAfter = end < current.length && current[end] && !/\s/.test(current[end]);
      const inserted = `${{needsSpaceBefore ? " " : ""}}${{value}}${{needsSpaceAfter ? " " : ""}}`;
      input.value = `${{current.slice(0, start)}}${{inserted}}${{current.slice(end)}}`;
      const cursor = start + inserted.length;
      if (typeof input.setSelectionRange === "function") input.setSelectionRange(cursor, cursor);
      input.dispatchEvent(new Event("input", {{ bubbles: true }}));
      input.dispatchEvent(new Event("change", {{ bubbles: true }}));
      input.focus();
      return true;
    }};
    const adminChatTextSpeechMode = () => String(adminChatSpeechMode && adminChatSpeechMode.value || "browser").trim().toLowerCase() === "zipformer" ? "zipformer" : "browser";
    const adminChatTextRecognitionCtor = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;
    const setAdminChatTextMicUi = (state = "idle", message = "") => {{
      const recording = state === "recording";
      const busy = state === "sending";
      if (adminChatTextMic) {{
        adminChatTextMic.textContent = recording ? "Stop text" : (busy ? "..." : "Text Mic");
        adminChatTextMic.classList.toggle("is-recording", recording);
        adminChatTextMic.classList.toggle("is-busy", busy);
        adminChatTextMic.setAttribute("aria-pressed", recording ? "true" : "false");
        adminChatTextMic.disabled = busy;
      }}
      if (message && adminChatVoiceState) adminChatVoiceState.textContent = message;
    }};
    const stopAdminChatTextTimer = () => {{
      if (adminChatTextTimer) {{
        window.clearInterval(adminChatTextTimer);
        adminChatTextTimer = 0;
      }}
    }};
    const adminChatTextDraft = () => String(`${{adminChatTextFinalText || ""}} ${{adminChatTextInterimText || ""}}`).replace(/\s+/g, " ").trim();
    const renderAdminChatTextDraft = () => {{
      const input = adminChatTextInput;
      if (!input) return false;
      const text = adminChatTextDraft();
      const base = String(adminChatTextBaseValue || "");
      const spacer = base && text && !/\s$/.test(base) ? " " : "";
      input.value = `${{base}}${{spacer}}${{text}}`.trimStart();
      if (typeof input.setSelectionRange === "function") input.setSelectionRange(input.value.length, input.value.length);
      input.dispatchEvent(new Event("input", {{ bubbles: true }}));
      input.dispatchEvent(new Event("change", {{ bubbles: true }}));
      input.focus();
      return Boolean(text);
    }};
    const resetAdminChatTextSpeech = (keepDraft = true) => {{
      stopAdminChatTextTimer();
      if (keepDraft) renderAdminChatTextDraft();
      adminChatTextRecognition = null;
      adminChatTextInput = null;
      adminChatTextBaseValue = "";
      adminChatTextFinalText = "";
      adminChatTextInterimText = "";
      adminChatTextStartedAt = 0;
      setAdminChatTextMicUi("idle", "");
    }};
    const stopAdminBrowserTextSpeech = () => {{
      const recognition = adminChatTextRecognition;
      if (!recognition) return false;
      try {{
        recognition.stop();
        return true;
      }} catch (error) {{
        try {{ recognition.abort(); }} catch (innerError) {{}}
        resetAdminChatTextSpeech(true);
        return false;
      }}
    }};
    const startAdminBrowserTextSpeech = () => {{
      const input = currentAdminAttachInput();
      const RecognitionCtor = adminChatTextRecognitionCtor();
      if (!RecognitionCtor) {{
        setAdminChatTextMicUi("idle", "Browser VI+EN speech recognition is unavailable here.");
        return;
      }}
      if (adminChatTextRecognition) {{
        stopAdminBrowserTextSpeech();
        return;
      }}
      const recognition = new RecognitionCtor();
      adminChatTextRecognition = recognition;
      adminChatTextInput = input;
      adminChatTextBaseValue = String(input && input.value || "");
      adminChatTextFinalText = "";
      adminChatTextInterimText = "";
      adminChatTextStartedAt = Date.now();
      recognition.lang = "vi-VN";
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.onresult = (event) => {{
        let finalText = "";
        let interim = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {{
          const result = event.results[index];
          const text = String(result && result[0] && result[0].transcript || "").replace(/\s+/g, " ").trim();
          if (!text) continue;
          if (result.isFinal) finalText = `${{finalText}} ${{text}}`.trim();
          else interim = `${{interim}} ${{text}}`.trim();
        }}
        if (finalText) adminChatTextFinalText = `${{adminChatTextFinalText}} ${{finalText}}`.trim();
        adminChatTextInterimText = interim;
        renderAdminChatTextDraft();
        setAdminChatTextMicUi("recording", "Browser VI+EN listening...");
      }};
      recognition.onerror = (event) => {{
        const code = String(event && event.error || "").trim();
        if (code && code !== "no-speech" && adminChatVoiceState) adminChatVoiceState.textContent = `Browser VI+EN: ${{code}}`;
      }};
      recognition.onend = () => {{
        const heard = renderAdminChatTextDraft();
        resetAdminChatTextSpeech(true);
        if (adminChatVoiceState) adminChatVoiceState.textContent = heard ? "Browser VI+EN added text." : "Browser VI+EN did not hear clear text.";
      }};
      try {{
        recognition.start();
      }} catch (error) {{
        resetAdminChatTextSpeech(false);
        if (adminChatVoiceState) adminChatVoiceState.textContent = String(error && error.message ? error.message : error);
        return;
      }}
      setAdminChatTextMicUi("recording", "Browser VI+EN listening...");
      adminChatTextTimer = window.setInterval(() => {{
        const seconds = Math.max(0, Math.round((Date.now() - adminChatTextStartedAt) / 1000));
        setAdminChatTextMicUi("recording", `Browser VI+EN listening... ${{seconds}}s`);
      }}, 500);
    }};
    const startAdminZipformerTextSpeech = async () => {{
      const input = currentAdminAttachInput();
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {{
        if (adminChatVoiceState) adminChatVoiceState.textContent = "Browser does not support recording.";
        return;
      }}
      setAdminChatTextMicUi("recording", "Recording Zipformer VI text...");
      let stream = null;
      let recorder = null;
      const chunks = [];
      try {{
        stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        const mimeType = adminChatRecorderMimeType();
        recorder = new MediaRecorder(stream, mimeType ? {{ mimeType }} : undefined);
        recorder.addEventListener("dataavailable", (event) => {{
          if (event.data && event.data.size) chunks.push(event.data);
        }});
        recorder.addEventListener("stop", async () => {{
          try {{
            setAdminChatTextMicUi("sending", "Recognizing with Zipformer VI...");
            const type = recorder.mimeType || mimeType || "audio/webm";
            const blob = new Blob(chunks, {{ type }});
            if (!blob.size) throw new Error("No audio captured.");
            const file = await adminChatVoiceUploadFile(blob);
            const form = new FormData();
            form.append("audio", file, file.name || `admin-chat-zipformer-${{Date.now()}}.wav`);
            form.append("source", "future_admin_chat_text_mic");
            form.append("language", "vi");
            const response = await fetch("/transcribe-zipformer-vi", {{ method: "POST", body: form }});
            const payload = await response.json().catch(() => ({{}}));
            if (!response.ok || payload.ok === false) throw new Error(payload.error || "Zipformer VI failed.");
            const text = String(payload.text || payload.transcript || "").replace(/\s+/g, " ").trim();
            if (!appendAdminSpeechTextToInput(input, text)) throw new Error("Zipformer VI did not hear clear text.");
            if (adminChatVoiceState) adminChatVoiceState.textContent = "Zipformer VI added text.";
          }} catch (error) {{
            if (adminChatVoiceState) adminChatVoiceState.textContent = String(error && error.message ? error.message : error);
          }} finally {{
            if (stream) stream.getTracks().forEach((track) => track.stop());
            setAdminChatTextMicUi("idle", "");
          }}
        }});
        recorder.start();
        window.setTimeout(() => {{
          if (recorder && recorder.state === "recording") recorder.stop();
        }}, 5000);
      }} catch (error) {{
        if (stream) stream.getTracks().forEach((track) => track.stop());
        setAdminChatTextMicUi("idle", String(error && error.message ? error.message : error));
      }}
    }};
    const toggleAdminChatTextSpeech = () => {{
      if (adminChatTextSpeechMode() === "zipformer") {{
        void startAdminZipformerTextSpeech();
        return;
      }}
      startAdminBrowserTextSpeech();
    }};
    const uploadAdminChatFiles = async (fileList, sourceInput = null, options = {{}}) => {{
      const files = Array.from(fileList || []).filter(Boolean);
      if (!adminChatUser || !files.length) return;
      const input = sourceInput || currentAdminAttachInput();
      const includeDraft = options.includeDraft !== false;
      const draft = includeDraft ? String(input && input.value || "").trim() : "";
      if (adminChatAttach) adminChatAttach.disabled = true;
      if (adminChatVoiceState) adminChatVoiceState.textContent = options.status || `Uploading ${{files.length}} file${{files.length > 1 ? "s" : ""}}...`;
      try {{
        for (let index = 0; index < files.length; index += 1) {{
          const form = new FormData();
          form.append("username", adminChatUser);
          form.append("file", files[index], files[index].name || `attachment-${{index + 1}}`);
          if (index === 0 && draft) {{
            form.append("text", draft);
            const voiceSelect = input === adminChatEnInput ? adminChatEnVoice : adminChatViVoice;
            const audioEnabled = input === adminChatEnInput ? adminChatEnAudioEnabled : adminChatViAudioEnabled;
            form.append("audio_enabled", audioEnabled ? "1" : "0");
            form.append("voice", voiceSelect ? voiceSelect.value : "");
          }}
          const response = await fetch("/chat/admin/upload", {{
            method: "POST",
            body: form,
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not upload attachment.");
          adminChatState = {{ users: payload.users || [], online_count: Number(payload.online_count || 0) }};
        }}
        if (input && draft) input.value = "";
        renderOnlineUsers(adminChatState.users, adminChatState);
        renderAdminChatLog(adminChatUser, null, {{ scroll: true }});
        if (adminChatVoiceState) adminChatVoiceState.textContent = "Attachment sent.";
        return true;
      }} catch (error) {{
        const message = String(error && error.message ? error.message : error);
        messageNode.textContent = message;
        if (adminChatVoiceState) adminChatVoiceState.textContent = message;
        return false;
      }} finally {{
        if (adminChatAttach) adminChatAttach.disabled = false;
        if (adminChatFile) adminChatFile.value = "";
      }}
    }};
    const adminChatRecorderMimeType = () => {{
      if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== "function") return "";
      return [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
      ].find((mime) => MediaRecorder.isTypeSupported(mime)) || "";
    }};
    const adminChatAudioExtension = (mime = "") => {{
      const value = String(mime || "").toLowerCase();
      if (value.includes("mp4") || value.includes("m4a")) return "m4a";
      if (value.includes("ogg")) return "ogg";
      if (value.includes("wav")) return "wav";
      return "webm";
    }};
    const encodeAdminChatWav = (audioBuffer) => {{
      const channels = Math.min(2, Math.max(1, audioBuffer.numberOfChannels || 1));
      const sampleRate = audioBuffer.sampleRate || 44100;
      const frames = audioBuffer.length || 0;
      const bytesPerSample = 2;
      const blockAlign = channels * bytesPerSample;
      const dataSize = frames * blockAlign;
      const buffer = new ArrayBuffer(44 + dataSize);
      const view = new DataView(buffer);
      const writeString = (offset, value) => {{
        for (let i = 0; i < value.length; i += 1) {{
          view.setUint8(offset + i, value.charCodeAt(i));
        }}
      }};
      writeString(0, "RIFF");
      view.setUint32(4, 36 + dataSize, true);
      writeString(8, "WAVE");
      writeString(12, "fmt ");
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true);
      view.setUint16(22, channels, true);
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * blockAlign, true);
      view.setUint16(32, blockAlign, true);
      view.setUint16(34, bytesPerSample * 8, true);
      writeString(36, "data");
      view.setUint32(40, dataSize, true);
      const channelData = Array.from({{ length: channels }}, (_, index) => audioBuffer.getChannelData(index));
      let offset = 44;
      for (let frame = 0; frame < frames; frame += 1) {{
        for (let channel = 0; channel < channels; channel += 1) {{
          const sample = Math.max(-1, Math.min(1, channelData[channel][frame] || 0));
          view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
          offset += bytesPerSample;
        }}
      }}
      return new Blob([buffer], {{ type: "audio/wav" }});
    }};
    const adminChatVoiceUploadFile = async (blob) => {{
      const fallbackExtension = adminChatAudioExtension(blob && blob.type);
      const fallback = () => new File([blob], `voice-message-${{Date.now()}}.${{fallbackExtension}}`, {{ type: (blob && blob.type) || "audio/webm" }});
      try {{
        const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextCtor || !blob || typeof blob.arrayBuffer !== "function") {{
          return fallback();
        }}
        const context = new AudioContextCtor();
        try {{
          const sourceBuffer = await blob.arrayBuffer();
          const audioBuffer = await new Promise((resolve, reject) => {{
            const result = context.decodeAudioData(sourceBuffer.slice(0), resolve, reject);
            if (result && typeof result.then === "function") {{
              result.then(resolve, reject);
            }}
          }});
          const wavBlob = encodeAdminChatWav(audioBuffer);
          return new File([wavBlob], `voice-message-${{Date.now()}}.wav`, {{ type: "audio/wav" }});
        }} finally {{
          if (typeof context.close === "function") {{
            context.close().catch(() => {{}});
          }}
        }}
      }} catch (error) {{
        return fallback();
      }}
    }};
    const stopAdminChatRecordTimer = () => {{
      if (adminChatRecordTimer) {{
        window.clearInterval(adminChatRecordTimer);
        adminChatRecordTimer = 0;
      }}
    }};
    const setAdminChatRecordUi = (state = "idle", message = "") => {{
      const recording = state === "recording";
      const ready = state === "ready";
      if (adminChatMic) {{
        adminChatMic.textContent = recording ? "Stop mic" : "Mic";
        adminChatMic.classList.toggle("is-recording", recording);
        adminChatMic.disabled = state === "sending";
      }}
      if (adminChatVoiceSend) {{
        adminChatVoiceSend.hidden = !ready;
        adminChatVoiceSend.disabled = state === "sending";
      }}
      if (adminChatVoiceCancel) {{
        adminChatVoiceCancel.hidden = !(ready || recording);
        adminChatVoiceCancel.disabled = state === "sending";
      }}
      if (message && adminChatVoiceState) adminChatVoiceState.textContent = message;
    }};
    const stopAdminChatRecording = () => {{
      if (adminChatRecorder && adminChatRecorder.state === "recording") {{
        adminChatRecorder.stop();
      }}
    }};
    const cancelAdminChatVoice = () => {{
      adminChatRecordCanceled = true;
      if (adminChatRecorder && adminChatRecorder.state === "recording") {{
        adminChatRecorder.stop();
      }}
      if (adminChatRecordStream) {{
        adminChatRecordStream.getTracks().forEach((track) => track.stop());
      }}
      adminChatRecorder = null;
      adminChatRecordStream = null;
      adminChatRecordChunks = [];
      adminChatRecordBlob = null;
      adminChatRecordInput = null;
      adminChatRecordStartedAt = 0;
      stopAdminChatRecordTimer();
      setAdminChatRecordUi("idle", "");
    }};
    const startAdminChatRecording = async () => {{
      if (!adminChatUser) {{
        if (adminChatVoiceState) adminChatVoiceState.textContent = "Choose a user first.";
        return;
      }}
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {{
        if (adminChatVoiceState) adminChatVoiceState.textContent = "Browser does not support message recording.";
        return;
      }}
      cancelAdminChatVoice();
      try {{
        const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        const mimeType = adminChatRecorderMimeType();
        const recorder = new MediaRecorder(stream, mimeType ? {{ mimeType }} : undefined);
        adminChatRecorder = recorder;
        adminChatRecordStream = stream;
        adminChatRecordChunks = [];
        adminChatRecordBlob = null;
        adminChatRecordInput = currentAdminAttachInput();
        adminChatRecordStartedAt = Date.now();
        adminChatRecordCanceled = false;
        recorder.addEventListener("dataavailable", (event) => {{
          if (event.data && event.data.size) adminChatRecordChunks.push(event.data);
        }});
        recorder.addEventListener("stop", () => {{
          stopAdminChatRecordTimer();
          if (adminChatRecordCanceled) {{
            adminChatRecordCanceled = false;
            return;
          }}
          const type = recorder.mimeType || mimeType || "audio/webm";
          adminChatRecordBlob = new Blob(adminChatRecordChunks, {{ type }});
          if (adminChatRecordStream) adminChatRecordStream.getTracks().forEach((track) => track.stop());
          adminChatRecordStream = null;
          adminChatRecorder = null;
          if (adminChatRecordBlob && adminChatRecordBlob.size) {{
            const seconds = Math.max(1, Math.round((Date.now() - adminChatRecordStartedAt) / 1000));
            setAdminChatRecordUi("ready", `Voice ready (${{seconds}}s). Press Send voice or Cancel.`);
          }} else {{
            cancelAdminChatVoice();
            if (adminChatVoiceState) adminChatVoiceState.textContent = "No audio to send.";
          }}
        }});
        recorder.start();
        setAdminChatRecordUi("recording", "Recording voice... press Stop mic when done.");
        adminChatRecordTimer = window.setInterval(() => {{
          const seconds = Math.max(0, Math.round((Date.now() - adminChatRecordStartedAt) / 1000));
          setAdminChatRecordUi("recording", `Recording voice... ${{seconds}}s`);
        }}, 500);
      }} catch (error) {{
        cancelAdminChatVoice();
        if (adminChatVoiceState) adminChatVoiceState.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const sendAdminChatVoice = async () => {{
      const blob = adminChatRecordBlob;
      if (!blob || !blob.size) {{
        if (adminChatVoiceState) adminChatVoiceState.textContent = "No voice recording is ready.";
        return;
      }}
      setAdminChatRecordUi("sending", "Preparing voice...");
      try {{
        const file = await adminChatVoiceUploadFile(blob);
        const sent = await uploadAdminChatFiles([file], adminChatRecordInput || currentAdminAttachInput(), {{
          includeDraft: false,
          status: "Sending voice...",
        }});
        if (sent) {{
          adminChatRecordBlob = null;
          adminChatRecordChunks = [];
          setAdminChatRecordUi("idle", "Voice sent.");
        }} else {{
          setAdminChatRecordUi("ready", "Voice is still ready. Try Send voice again.");
        }}
      }} catch (error) {{
        setAdminChatRecordUi("ready", String(error && error.message ? error.message : error));
      }}
    }};
    const handleAdminChatPaste = (event) => {{
      if (!adminChatModal || !adminChatModal.classList.contains("is-open") || !event.clipboardData || event.defaultPrevented || event.futureChatPasteHandled) return;
      const files = Array.from(event.clipboardData.files || []).filter((file) => file && file.size);
      if (!files.length) return;
      event.futureChatPasteHandled = true;
      event.preventDefault();
      uploadAdminChatFiles(files, event.target === adminChatEnInput ? adminChatEnInput : adminChatInput);
    }};
    if (adminChatAttach && adminChatFile) {{
      adminChatAttach.addEventListener("click", () => adminChatFile.click());
      adminChatFile.addEventListener("change", () => uploadAdminChatFiles(adminChatFile.files, currentAdminAttachInput()));
    }}
    if (adminChatMic) adminChatMic.addEventListener("click", () => {{
      if (adminChatRecorder && adminChatRecorder.state === "recording") {{
        stopAdminChatRecording();
      }} else {{
        void startAdminChatRecording();
      }}
    }});
    if (adminChatSpeechMode) {{
      adminChatSpeechMode.value = localStorage.getItem("future_admin_chat_speech_mode") || "browser";
      adminChatSpeechMode.addEventListener("change", () => {{
        localStorage.setItem("future_admin_chat_speech_mode", adminChatTextSpeechMode());
      }});
    }}
    if (adminChatTextMic) adminChatTextMic.addEventListener("click", toggleAdminChatTextSpeech);
    if (adminChatVoiceSend) adminChatVoiceSend.addEventListener("click", () => void sendAdminChatVoice());
    if (adminChatVoiceCancel) adminChatVoiceCancel.addEventListener("click", cancelAdminChatVoice);
    if (adminChatViAudioToggle) adminChatViAudioToggle.addEventListener("click", () => {{
      adminChatViAudioEnabled = !adminChatViAudioEnabled;
      localStorage.setItem("future_admin_chat_vi_audio", adminChatViAudioEnabled ? "1" : "0");
      renderAdminChatAudioToggles();
    }});
    if (adminChatEnAudioToggle) adminChatEnAudioToggle.addEventListener("click", () => {{
      adminChatEnAudioEnabled = !adminChatEnAudioEnabled;
      localStorage.setItem("future_admin_chat_en_audio", adminChatEnAudioEnabled ? "1" : "0");
      renderAdminChatAudioToggles();
    }});
    if (adminChatSend) adminChatSend.addEventListener("click", () => sendAdminChat("vi"));
    if (adminChatEnSend) adminChatEnSend.addEventListener("click", () => sendAdminChat("en"));
    if (adminChatInput) adminChatInput.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" && !event.shiftKey) {{
        event.preventDefault();
        sendAdminChat("vi");
      }}
    }});
    if (adminChatEnInput) adminChatEnInput.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" && !event.shiftKey) {{
        event.preventDefault();
        sendAdminChat("en");
      }}
    }});
    if (adminChatInput) adminChatInput.addEventListener("paste", handleAdminChatPaste);
    if (adminChatEnInput) adminChatEnInput.addEventListener("paste", handleAdminChatPaste);
    if (adminChatModal) adminChatModal.addEventListener("paste", handleAdminChatPaste);
    if (adminImageClose) adminImageClose.addEventListener("click", closeAdminImageViewer);
    if (adminImageZoomOut) adminImageZoomOut.addEventListener("click", (event) => {{
      event.stopPropagation();
      setAdminImageZoom(adminImageViewerState.zoom / 1.25);
    }});
    if (adminImageZoomIn) adminImageZoomIn.addEventListener("click", (event) => {{
      event.stopPropagation();
      setAdminImageZoom(adminImageViewerState.zoom * 1.25);
    }});
    if (adminImageZoomReset) adminImageZoomReset.addEventListener("click", (event) => {{
      event.stopPropagation();
      resetAdminImageTransform();
    }});
    if (adminImageViewer) adminImageViewer.addEventListener("click", (event) => {{
      if (event.target === adminImageViewer) closeAdminImageViewer();
    }});
    if (adminImageViewer) adminImageViewer.addEventListener("wheel", (event) => {{
      if (!adminImageViewer.classList.contains("is-open")) return;
      event.preventDefault();
      setAdminImageZoom(adminImageViewerState.zoom * (event.deltaY < 0 ? 1.12 : 1 / 1.12));
    }}, {{ passive: false }});
    if (adminImageViewerImg) {{
      adminImageViewerImg.addEventListener("pointerdown", beginAdminImageDrag);
      adminImageViewerImg.addEventListener("pointermove", moveAdminImageDrag);
      adminImageViewerImg.addEventListener("pointerup", endAdminImageDrag);
      adminImageViewerImg.addEventListener("pointercancel", endAdminImageDrag);
      adminImageViewerImg.addEventListener("click", (event) => event.stopPropagation());
    }}
    const streamFileToDataUrl = (blob) => new Promise((resolve, reject) => {{
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => reject(reader.error || new Error("Could not read stream audio."));
      reader.readAsDataURL(blob);
    }});
    const streamDataUrlToBytes = (dataUrl = "") => {{
      const raw = String(dataUrl || "");
      const comma = raw.indexOf(",");
      if (comma < 0) return null;
      const base64 = raw.slice(comma + 1);
      try {{
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {{
          bytes[index] = binary.charCodeAt(index);
        }}
        return bytes;
      }} catch (error) {{
        return null;
      }}
    }};
    const streamMimeFromDataUrl = (dataUrl = "", fallback = "audio/webm;codecs=opus") => {{
      const match = String(dataUrl || "").match(/^data:([^;,]+(?:;codecs=[^;,]+)?)/i);
      return match && match[1] ? match[1] : fallback;
    }};
    const ADMIN_STREAM_AUDIO_MODE_KEY = "future_admin_stream_audio_mode";
    const normalizeAdminStreamAudioMode = (value) => String(value || "").toLowerCase() === "inbound" ? "inbound" : "relay";
    let adminStreamAudioMode = normalizeAdminStreamAudioMode(localStorage.getItem(ADMIN_STREAM_AUDIO_MODE_KEY) || "relay");
    const stopAdminStreamRelayBuffer = () => {{
      adminStreamRelayPendingBuffers = [];
      adminStreamRelaySourceBuffer = null;
      adminStreamRelayOpening = false;
      if (adminStreamRelayMediaSource) {{
        try {{
          if (adminStreamRelayMediaSource.readyState === "open") adminStreamRelayMediaSource.endOfStream();
        }} catch (error) {{}}
      }}
      adminStreamRelayMediaSource = null;
      adminStreamRelayMime = "";
      if (adminStreamRemoteAudio) {{
        try {{ adminStreamRemoteAudio.pause(); }} catch (error) {{}}
        if (adminStreamRemoteAudio.src && adminStreamRelayObjectUrl && adminStreamRemoteAudio.src === adminStreamRelayObjectUrl) {{
          adminStreamRemoteAudio.removeAttribute("src");
          try {{ adminStreamRemoteAudio.load(); }} catch (error) {{}}
        }}
      }}
      if (adminStreamRelayObjectUrl) {{
        try {{ URL.revokeObjectURL(adminStreamRelayObjectUrl); }} catch (error) {{}}
      }}
      adminStreamRelayObjectUrl = "";
    }};
    const pumpAdminStreamRelayBuffer = () => {{
      const buffer = adminStreamRelaySourceBuffer;
      if (!buffer || buffer.updating || !adminStreamRelayPendingBuffers.length) return;
      try {{
        buffer.appendBuffer(adminStreamRelayPendingBuffers.shift());
      }} catch (error) {{
        adminStreamRelayDropped += Math.max(1, adminStreamRelayPendingBuffers.length);
        adminStreamRelayPendingBuffers = [];
      }}
    }};
    const ensureAdminStreamRelayBuffer = (mime = "audio/webm;codecs=opus") => {{
      const wantedMime = String(mime || "audio/webm;codecs=opus");
      if (!window.MediaSource || typeof MediaSource.isTypeSupported !== "function" || !MediaSource.isTypeSupported(wantedMime)) {{
        return false;
      }}
      if (adminStreamRelayMediaSource && adminStreamRelayMime === wantedMime && adminStreamRelaySourceBuffer) {{
        return true;
      }}
      stopAdminStreamRelayBuffer();
      adminStreamRelayMime = wantedMime;
      adminStreamRelayMediaSource = new MediaSource();
      adminStreamRelayOpening = true;
      const audio = ensureAdminStreamRemoteAudio();
      audio.srcObject = null;
      adminStreamRelayObjectUrl = URL.createObjectURL(adminStreamRelayMediaSource);
      audio.src = adminStreamRelayObjectUrl;
      audio.muted = false;
      audio.volume = 1;
      audio.play().catch(() => {{
        messageNode.textContent = "Admin browser blocked stream audio. Click Stream once on this page.";
      }});
      adminStreamRelayMediaSource.addEventListener("sourceopen", () => {{
        if (!adminStreamRelayMediaSource || adminStreamRelaySourceBuffer) return;
        try {{
          adminStreamRelaySourceBuffer = adminStreamRelayMediaSource.addSourceBuffer(wantedMime);
          adminStreamRelaySourceBuffer.mode = "sequence";
          adminStreamRelaySourceBuffer.addEventListener("updateend", pumpAdminStreamRelayBuffer);
          adminStreamRelayOpening = false;
          pumpAdminStreamRelayBuffer();
        }} catch (error) {{
          stopAdminStreamRelayBuffer();
        }}
      }}, {{ once: true }});
      return true;
    }};
    const stopAdminStreamCurrentRelayAudio = () => {{
      stopAdminStreamRelayBuffer();
      if (!adminStreamCurrentAudio) return;
      try {{
        adminStreamCurrentAudio.pause();
        adminStreamCurrentAudio.removeAttribute("src");
        adminStreamCurrentAudio.load();
      }} catch (error) {{}}
      adminStreamCurrentAudio = null;
      adminStreamAudioPlaying = false;
    }};
    const drainAdminStreamAudioQueue = () => {{
      if (adminStreamAudioPlaying) return;
      const chunk = adminStreamAudioQueue.shift();
      if (!chunk) return;
      const data = String(chunk.data || "");
      if (!data) {{
        drainAdminStreamAudioQueue();
        return;
      }}
      const audio = new Audio(data);
      adminStreamCurrentAudio = audio;
      adminStreamAudioPlaying = true;
      audio.autoplay = true;
      audio.playsInline = true;
      audio.preload = "auto";
      audio.volume = 1;
      const finish = () => {{
        if (adminStreamCurrentAudio === audio) adminStreamCurrentAudio = null;
        adminStreamAudioPlaying = false;
        drainAdminStreamAudioQueue();
      }};
      audio.onended = finish;
      audio.onerror = () => {{
        messageNode.textContent = "Admin stream audio chunk error.";
        finish();
      }};
      audio.play().catch(() => {{
        messageNode.textContent = "Admin browser blocked stream audio. Click Stream once on this page.";
        finish();
      }});
    }};
    const playAdminStreamChunk = (chunk = {{}}) => {{
      if (adminStreamAudioMode !== "relay") return;
      if (!chunk || !chunk.data) return;
      const mime = streamMimeFromDataUrl(chunk.data, chunk.mime || "audio/webm;codecs=opus");
      const bytes = streamDataUrlToBytes(chunk.data);
      if (bytes && ensureAdminStreamRelayBuffer(mime)) {{
        adminStreamRelayPendingBuffers.push(bytes);
        if (adminStreamRelayPendingBuffers.length > 18) {{
          const dropCount = adminStreamRelayPendingBuffers.length - 12;
          adminStreamRelayPendingBuffers.splice(0, dropCount);
          adminStreamRelayDropped += dropCount;
        }}
        pumpAdminStreamRelayBuffer();
        return;
      }}
      adminStreamAudioQueue.push(chunk);
      if (adminStreamAudioQueue.length > 3) {{
        const dropCount = adminStreamAudioQueue.length - 2;
        adminStreamAudioQueue.splice(0, dropCount);
        adminStreamRelayDropped += dropCount;
      }}
      drainAdminStreamAudioQueue();
    }};
    const unlockAdminStreamAudio = () => {{
      if (adminStreamAudioUnlocked) return;
      adminStreamAudioUnlocked = true;
      try {{
        const audio = new Audio("data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=");
        audio.volume = 0;
        audio.play().catch(() => {{
          adminStreamAudioUnlocked = false;
        }});
      }} catch (error) {{
        adminStreamAudioUnlocked = false;
      }}
    }};
    document.addEventListener("pointerdown", unlockAdminStreamAudio, {{ passive: true }});
    const adminWebRtcConfig = {{
      iceServers: [
        {{ urls: "stun:stun.l.google.com:19302" }},
        {{ urls: "stun:global.stun.twilio.com:3478" }},
      ],
    }};
    const ensureAdminStreamRemoteAudio = () => {{
      if (!adminStreamRemoteAudio) {{
        adminStreamRemoteAudio = document.createElement("audio");
        adminStreamRemoteAudio.autoplay = true;
        adminStreamRemoteAudio.playsInline = true;
        adminStreamRemoteAudio.controls = false;
        adminStreamRemoteAudio.style.display = "none";
        document.body.appendChild(adminStreamRemoteAudio);
      }}
      return adminStreamRemoteAudio;
    }};
    const renderAdminStreamAudioMode = () => {{
      adminStreamModeButtons.forEach((button) => {{
        const active = button.dataset.adminStreamMode === adminStreamAudioMode;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      }});
      if (adminStreamModeNote) {{
        adminStreamModeNote.textContent = adminStreamAudioMode === "inbound"
          ? "Inbound: admin listens to the direct WebRTC track. If audio drops, switch back to Relay."
          : "Relay: admin nghe qua server, on dinh hon qua mang khac nhau.";
      }}
    }};
    const stopAdminStreamInboundAudio = () => {{
      if (adminStreamRemoteAudio) {{
        try {{ adminStreamRemoteAudio.pause(); }} catch (error) {{}}
        adminStreamRemoteAudio.srcObject = null;
      }}
      if (adminStreamInboundTrack) {{
        try {{ adminStreamInboundTrack.enabled = false; }} catch (error) {{}}
      }}
    }};
    const playAdminStreamInboundAudio = () => {{
      if (!adminStreamInboundStream) {{
        messageNode.textContent = "Inbound selected. Waiting for WebRTC audio track from user.";
        return;
      }}
      if (adminStreamInboundTrack) {{
        try {{ adminStreamInboundTrack.enabled = true; }} catch (error) {{}}
      }}
      const audio = ensureAdminStreamRemoteAudio();
      audio.srcObject = adminStreamInboundStream;
      audio.muted = false;
      audio.volume = 1;
      audio.play().then(() => {{
        messageNode.textContent = "Listening via inbound WebRTC.";
      }}).catch(() => {{
        messageNode.textContent = "Inbound selected, browser blocked audio. Click Stream once on this page.";
      }});
    }};
    const applyAdminStreamAudioMode = () => {{
      renderAdminStreamAudioMode();
      if (adminStreamAudioMode === "inbound") {{
        adminStreamAudioQueue = [];
        stopAdminStreamCurrentRelayAudio();
        playAdminStreamInboundAudio();
      }} else {{
        stopAdminStreamInboundAudio();
        if (adminStreamSession && adminStreamSession.state === "active") {{
          messageNode.textContent = "Listening via relay.";
        }}
      }}
    }};
    adminStreamModeButtons.forEach((button) => {{
      button.addEventListener("click", () => {{
        adminStreamAudioMode = normalizeAdminStreamAudioMode(button.dataset.adminStreamMode);
        localStorage.setItem(ADMIN_STREAM_AUDIO_MODE_KEY, adminStreamAudioMode);
        unlockAdminStreamAudio();
        applyAdminStreamAudioMode();
      }});
    }});
    renderAdminStreamAudioMode();
    const sendAdminWebRtcSignal = async (type, data) => {{
      if (!adminStreamSession || !adminStreamUser || !type || !data) return;
      await fetch("/stream/admin/signal", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          username: adminStreamUser,
          session: adminStreamSession.id,
          type,
          data,
        }}),
      }});
    }};
    const stopAdminStreamMedia = () => {{
      if (adminStreamSegmentTimer) {{
        window.clearTimeout(adminStreamSegmentTimer);
        adminStreamSegmentTimer = 0;
      }}
      if (adminStreamRecorder && adminStreamRecorder.state !== "inactive") {{
        try {{ adminStreamRecorder.stop(); }} catch (error) {{}}
      }}
      adminStreamRecorder = null;
      adminStreamRecordChunks = [];
      adminStreamAudioChain = Promise.resolve();
      stopAdminStreamCurrentRelayAudio();
      adminStreamAudioQueue = [];
      adminStreamLastChunkId = 0;
      adminStreamRelayDropped = 0;
      adminStreamChunkPolling = false;
      adminStreamInboundStream = null;
      adminStreamInboundTrack = null;
      if (adminStreamMedia) {{
        adminStreamMedia.getTracks().forEach((track) => track.stop());
      }}
      adminStreamMedia = null;
      if (adminStreamPeer) {{
        try {{ adminStreamPeer.close(); }} catch (error) {{}}
      }}
      adminStreamPeer = null;
      adminStreamRemoteCandidateId = 0;
      adminStreamOfferSent = false;
      adminStreamAnswerSet = false;
      adminStreamPeerStartedAt = 0;
      if (adminStreamRemoteAudio) {{
        adminStreamRemoteAudio.srcObject = null;
      }}
    }};
    const postAdminStreamChunk = async (blob) => {{
      if (!adminStreamSession || !adminStreamUser || !blob || !blob.size) return;
      const data = await streamFileToDataUrl(blob);
      await fetch("/stream/admin/chunk", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          username: adminStreamUser,
          session: adminStreamSession.id,
          data,
          mime: blob.type || "audio/webm",
        }}),
      }});
    }};
    const pollAdminStreamChunks = async () => {{
      if (adminStreamAudioMode !== "relay") return;
      if (adminStreamChunkPolling || !adminStreamSession || !adminStreamUser || adminStreamSession.state !== "active") return;
      adminStreamChunkPolling = true;
      try {{
        const response = await fetch(`/stream/admin/poll?username=${{encodeURIComponent(adminStreamUser)}}&session=${{encodeURIComponent(adminStreamSession.id)}}&after=${{encodeURIComponent(String(adminStreamLastChunkId || 0))}}`, {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) return;
        if (payload.session && payload.session.state && payload.session.state !== "active") {{
          await handleAdminStreamSession(adminStreamUser, payload.session);
          return;
        }}
        const chunks = Array.isArray(payload.chunks) ? payload.chunks : [];
        chunks.forEach((chunk) => {{
          adminStreamLastChunkId = Math.max(adminStreamLastChunkId, Number(chunk.id || 0));
        }});
        const playableChunks = chunks.slice(-2);
        adminStreamRelayDropped += Math.max(0, chunks.length - playableChunks.length);
        playableChunks.forEach((chunk) => {{
          playAdminStreamChunk(chunk);
        }});
        if (chunks.length) {{
          messageNode.textContent = `Receiving user mic relay: ${{adminStreamLastChunkId}} | dropped old: ${{adminStreamRelayDropped}}`;
        }}
      }} catch (error) {{
      }} finally {{
        adminStreamChunkPolling = false;
      }}
    }};
    const adminStreamPeerState = () => adminStreamPeer ? (adminStreamPeer.connectionState || adminStreamPeer.iceConnectionState || "") : "";
    const adminStreamNeedsReconnect = () => {{
      const state = adminStreamPeerState();
      return Boolean(adminStreamPeer && ["failed", "disconnected", "closed"].includes(state));
    }};
    const startAdminStreamMedia = async () => {{
      if (!adminStreamSession || adminStreamPeer) return;
      if (!window.RTCPeerConnection) {{
        messageNode.textContent = "Browser khong ho tro WebRTC.";
        return;
      }}
      adminStreamPeer = new RTCPeerConnection(adminWebRtcConfig);
      adminStreamPeerStartedAt = Date.now();
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {{
        try {{
          adminStreamMedia = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        }} catch (error) {{
          adminStreamMedia = null;
          messageNode.textContent = "Khong mo duoc mic admin, dang nghe mot chieu.";
        }}
      }}
      if (adminStreamMedia) {{
        adminStreamMedia.getAudioTracks().forEach((track) => adminStreamPeer.addTrack(track, adminStreamMedia));
      }} else {{
        try {{
          adminStreamPeer.addTransceiver("audio", {{ direction: "recvonly" }});
        }} catch (error) {{
        }}
      }}
      adminStreamPeer.addEventListener("icecandidate", (event) => {{
        if (event.candidate) {{
          sendAdminWebRtcSignal("candidate", event.candidate.toJSON()).catch(() => {{}});
        }}
      }});
      adminStreamPeer.addEventListener("track", (event) => {{
        adminStreamInboundTrack = event.track || null;
        adminStreamInboundStream = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
        try {{
          if (event.track) event.track.enabled = adminStreamAudioMode === "inbound";
        }} catch (error) {{}}
        applyAdminStreamAudioMode();
      }});
      adminStreamPeer.addEventListener("connectionstatechange", () => {{
        if (adminStreamPeer) messageNode.textContent = `WebRTC: ${{adminStreamPeer.connectionState}}`;
      }});
      const offer = await adminStreamPeer.createOffer({{ offerToReceiveAudio: true }});
      await adminStreamPeer.setLocalDescription(offer);
      await sendAdminWebRtcSignal("offer", adminStreamPeer.localDescription.toJSON());
      adminStreamOfferSent = true;
      messageNode.textContent = "WebRTC offer sent.";
    }};
    const handleAdminStreamSession = async (username, session = {{}}) => {{
      const nextId = session && session.id ? session.id : "";
      if (nextId && adminStreamSession && adminStreamSession.id && adminStreamSession.id !== nextId) {{
        stopAdminStreamMedia();
      }}
      if (session && session.id) {{
        if (!adminStreamSession || adminStreamSession.id !== session.id) {{
          adminStreamLastChunkId = 0;
          adminStreamAudioChain = Promise.resolve();
        }}
        adminStreamUser = username || session.username || adminStreamUser;
        adminStreamSession = session;
      }} else {{
        adminStreamSession = null;
        adminStreamUser = "";
      }}
      if (adminStreamSession && adminStreamSession.state === "active") {{
        if (adminStreamNeedsReconnect()) {{
          stopAdminStreamMedia();
        }}
        try {{
          await startAdminStreamMedia();
        }} catch (error) {{
          messageNode.textContent = String(error && error.message ? error.message : error);
        }}
      }} else if (!adminStreamSession || ["ended", "rejected", "error"].includes(adminStreamSession.state)) {{
        stopAdminStreamMedia();
      }}
    }};
    const pollAdminStream = async () => {{
      if (!adminStreamSession || !adminStreamUser || adminStreamSession.state !== "active") return;
      void pollAdminStreamChunks();
      if (!adminStreamPeer) return;
      try {{
        const response = await fetch(`/stream/admin/signal?username=${{encodeURIComponent(adminStreamUser)}}&session=${{encodeURIComponent(adminStreamSession.id)}}&after=${{encodeURIComponent(String(adminStreamRemoteCandidateId))}}`, {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not poll WebRTC.");
        if (payload.session && payload.session.state !== "active") {{
          await handleAdminStreamSession(adminStreamUser, payload.session);
          return;
        }}
        if (payload.answer && !adminStreamAnswerSet) {{
          await adminStreamPeer.setRemoteDescription(new RTCSessionDescription(payload.answer));
          adminStreamAnswerSet = true;
        }}
        const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
        for (const item of candidates) {{
          if (item.candidate && adminStreamAnswerSet) {{
            adminStreamRemoteCandidateId = Math.max(adminStreamRemoteCandidateId, Number(item.id || 0));
            try {{
              await adminStreamPeer.addIceCandidate(new RTCIceCandidate(item.candidate));
            }} catch (error) {{
            }}
          }}
        }}
      }} catch (error) {{
      }}
    }};
    let adminStreamPollTimer = 0;
    const adminStreamPollDelay = () => {{
      if (!dashboardPollIsFocused()) return DASHBOARD_HIDDEN_POLL_MS;
      return adminStreamSession && adminStreamSession.state === "active" ? 900 : DASHBOARD_VISIBLE_POLL_MS;
    }};
    const scheduleAdminStreamPoll = (delayMs = adminStreamPollDelay()) => {{
      if (adminStreamPollTimer) {{
        window.clearTimeout(adminStreamPollTimer);
      }}
      adminStreamPollTimer = window.setTimeout(async () => {{
        adminStreamPollTimer = 0;
        await pollAdminStream();
        scheduleAdminStreamPoll();
      }}, Math.max(700, Number(delayMs) || adminStreamPollDelay()));
    }};
    document.addEventListener("visibilitychange", () => scheduleAdminStreamPoll(dashboardPollIsFocused() ? 1200 : DASHBOARD_HIDDEN_POLL_MS));
    window.addEventListener("focus", () => scheduleAdminStreamPoll(1200));
    window.addEventListener("blur", () => scheduleAdminStreamPoll(DASHBOARD_HIDDEN_POLL_MS));
    scheduleAdminStreamPoll(1200);
    const requestOrAcceptAdminStream = async (item) => {{
      const username = item && item.username || "";
      if (!username) return;
      unlockAdminStreamAudio();
      const session = item.stream || null;
      try {{
        let response;
        if (session && session.state === "pending_admin") {{
          response = await fetch("/stream/admin/action", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ username, session: session.id, action: "accept" }}),
          }});
        }} else if (session && session.state === "active") {{
          if (adminStreamUser === username && adminStreamSession && adminStreamSession.id === session.id && adminStreamNeedsReconnect()) {{
            stopAdminStreamMedia();
          }}
          await handleAdminStreamSession(username, session);
          updateAdminScreenMicButton();
          return;
        }} else {{
          response = await fetch("/stream/admin/request", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ username }}),
          }});
        }}
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not start stream.");
        adminChatState = {{ users: payload.users || adminChatState.users || [], online_count: Number(payload.online_count || adminChatState.online_count || 0) }};
        renderOnlineUsers(adminChatState.users, adminChatState);
        await handleAdminStreamSession(username, payload.session || {{}});
      }} catch (error) {{
        messageNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const stopAdminScreenTransport = () => {{
      if (adminScreenPollTimer) {{
        window.clearTimeout(adminScreenPollTimer);
        adminScreenPollTimer = 0;
      }}
      if (adminScreenPeer) {{
        try {{ adminScreenPeer.close(); }} catch (error) {{}}
      }}
      adminScreenPeer = null;
      adminScreenRemoteCandidateId = 0;
      adminScreenOfferSent = false;
      adminScreenAnswerSet = false;
      adminScreenPeerStartedAt = 0;
      if (adminScreenControlChannel) {{
        try {{ adminScreenControlChannel.close(); }} catch (error) {{}}
      }}
      adminScreenControlChannel = null;
      adminScreenFrameId = 0;
      adminScreenFrameSeenAt = 0;
      if (adminScreenVideo) {{
        adminScreenVideo.srcObject = null;
        adminScreenVideo.style.display = "block";
      }}
      if (adminScreenImg) {{
        adminScreenImg.removeAttribute("src");
        adminScreenImg.style.display = "";
      }}
      adminScreenControlQueue = [];
      adminScreenControlSending = false;
      if (adminScreenControlTimer) {{
        window.clearTimeout(adminScreenControlTimer);
        adminScreenControlTimer = 0;
      }}
    }};
    const adminScreenClamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, Number(value) || 0));
    const adminScreenWebRtcLive = () => Boolean(
      adminScreenVideo
      && adminScreenVideo.srcObject
      && adminScreenVideo.style.display !== "none"
      && adminScreenPeer
      && ["connected", "completed"].includes(adminScreenPeer.connectionState || adminScreenPeer.iceConnectionState || ""),
    );
    const adminScreenActiveMedia = () => {{
      const videoReady = adminScreenVideo && adminScreenVideo.style.display !== "none" && adminScreenVideo.srcObject;
      if (videoReady) return adminScreenVideo;
      const imageReady = adminScreenImg && adminScreenImg.style.display !== "none" && adminScreenImg.getAttribute("src");
      if (imageReady) return adminScreenImg;
      return null;
    }};
    const adminScreenControlPoint = (event) => {{
      const media = adminScreenActiveMedia();
      if (!media) return null;
      const rect = media.getBoundingClientRect();
      if (!rect.width || !rect.height) return null;
      return {{
        x: adminScreenClamp((event.clientX - rect.left) / rect.width, 0, 1),
        y: adminScreenClamp((event.clientY - rect.top) / rect.height, 0, 1),
      }};
    }};
    const adminScreenCommandIsHover = (command) => Boolean(command && command.type === "cursor" && command.dispatch === false && command.visible !== false);
    const adminScreenCommandIsImportant = (command) => Boolean(command && !adminScreenCommandIsHover(command));
    const adminScreenControlChannelOpen = () => Boolean(adminScreenControlChannel && adminScreenControlChannel.readyState === "open");
    const adminScreenCompactControlQueue = (items = []) => {{
      const compacted = [];
      let latestHover = null;
      (Array.isArray(items) ? items : []).forEach((command) => {{
        if (adminScreenCommandIsHover(command)) {{
          latestHover = command;
          return;
        }}
        if (latestHover) {{
          compacted.push(latestHover);
          latestHover = null;
        }}
        if (command) compacted.push(command);
      }});
      if (latestHover) compacted.push(latestHover);
      return compacted;
    }};
    const sendAdminScreenControlDataChannel = (commands = []) => {{
      if (!adminScreenControlChannelOpen() || !Array.isArray(commands) || !commands.length) return false;
      try {{
        adminScreenControlChannel.send(JSON.stringify({{ type: "screen-control", commands }}));
        return true;
      }} catch (error) {{
        return false;
      }}
    }};
    const adminScreenPollDelay = () => dashboardPollIsFocused() ? 900 : DASHBOARD_HIDDEN_POLL_MS;
    const scheduleAdminScreenWebRtcPoll = (delay = adminScreenPollDelay()) => {{
      if (!adminScreenSession || adminScreenSession.state !== "active") return;
      if (adminScreenPollTimer) window.clearTimeout(adminScreenPollTimer);
      adminScreenPollTimer = window.setTimeout(async () => {{
        adminScreenPollTimer = 0;
        await pollAdminScreenWebRtc();
        scheduleAdminScreenWebRtcPoll();
      }}, Math.max(700, Number(delay) || adminScreenPollDelay()));
    }};
    document.addEventListener("visibilitychange", () => scheduleAdminScreenWebRtcPoll(dashboardPollIsFocused() ? 900 : DASHBOARD_HIDDEN_POLL_MS));
    window.addEventListener("focus", () => scheduleAdminScreenWebRtcPoll(900));
    window.addEventListener("blur", () => scheduleAdminScreenWebRtcPoll(DASHBOARD_HIDDEN_POLL_MS));
    const sendAdminScreenControlQueue = async () => {{
      if (adminScreenControlSending || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active" || !adminScreenControlQueue.length) return;
      adminScreenControlSending = true;
      adminScreenControlLastSentAt = Date.now();
      adminScreenControlQueue = adminScreenCompactControlQueue(adminScreenControlQueue).slice(-80);
      const commands = adminScreenControlQueue.splice(0, 24);
      if (sendAdminScreenControlDataChannel(commands)) {{
        adminScreenControlSending = false;
        if (adminScreenControlQueue.length) {{
          window.clearTimeout(adminScreenControlTimer);
          adminScreenControlTimer = window.setTimeout(() => void sendAdminScreenControlQueue(), 16);
        }}
        return;
      }}
      const httpCommands = commands.filter((command) => !(command && command.type === "cursor" && command.dispatch === false));
      if (!httpCommands.length) {{
        adminScreenControlSending = false;
        if (adminScreenControlQueue.length) {{
          window.clearTimeout(adminScreenControlTimer);
          adminScreenControlTimer = window.setTimeout(() => void sendAdminScreenControlQueue(), 120);
        }}
        return;
      }}
      const hasHttpImportant = httpCommands.some(adminScreenCommandIsImportant);
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timeout = controller ? window.setTimeout(() => controller.abort(), hasHttpImportant ? 2200 : 1400) : 0;
      try {{
        const response = await fetch("/screen/admin/control", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          signal: controller ? controller.signal : undefined,
          body: JSON.stringify({{
            username: adminScreenUser,
            session: adminScreenSession.id,
            commands: httpCommands,
          }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not send screen control.");
        if (payload.session && payload.session.id) adminScreenSession = payload.session;
      }} catch (error) {{
        const retryCommands = httpCommands.filter(adminScreenCommandIsImportant);
        adminScreenControlQueue = retryCommands.concat(adminScreenControlQueue).slice(-80);
        if (hasHttpImportant && adminScreenStatus) adminScreenStatus.textContent = String(error && error.message ? error.message : error);
      }} finally {{
        if (timeout) window.clearTimeout(timeout);
        adminScreenControlSending = false;
        if (adminScreenControlQueue.length) {{
          window.clearTimeout(adminScreenControlTimer);
          adminScreenControlTimer = window.setTimeout(() => void sendAdminScreenControlQueue(), hasHttpImportant ? 35 : 250);
        }}
      }}
    }};
    const queueAdminScreenControl = (command, urgent = false) => {{
      if (!adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active" || !command) return;
      if (!urgent && adminScreenCommandIsHover(command)) {{
        for (let index = adminScreenControlQueue.length - 1; index >= 0; index -= 1) {{
          if (adminScreenCommandIsHover(adminScreenControlQueue[index])) {{
            adminScreenControlQueue.splice(index, 1);
            break;
          }}
        }}
      }}
      adminScreenControlQueue.push(command);
      adminScreenControlQueue = adminScreenCompactControlQueue(adminScreenControlQueue).slice(-80);
      const elapsed = Date.now() - Number(adminScreenControlLastSentAt || 0);
      const delay = urgent ? 0 : (adminScreenControlChannelOpen() ? Math.max(8, 33 - elapsed, 0) : Math.max(80, 250 - elapsed, 0));
      window.clearTimeout(adminScreenControlTimer);
      adminScreenControlTimer = window.setTimeout(() => void sendAdminScreenControlQueue(), delay);
    }};
    const queueAdminScreenPointerControl = (event, type, options = {{}}) => {{
      const point = adminScreenControlPoint(event);
      if (!point) return false;
      queueAdminScreenControl({{
        type,
        x: point.x,
        y: point.y,
        visible: options.visible !== false,
        button: Number(event.button || 0),
        buttons: Number(event.buttons || 0),
        ctrl: Boolean(event.ctrlKey),
        alt: Boolean(event.altKey),
        shift: Boolean(event.shiftKey),
        meta: Boolean(event.metaKey),
        dispatch: options.dispatch !== false,
      }}, Boolean(options.urgent));
      return true;
    }};
    const queueAdminScreenCursorHidden = () => {{
      queueAdminScreenControl({{ type: "cursor", visible: false, dispatch: false }}, true);
    }};
    const queueAdminScreenKeyControl = (event, type) => {{
      if (!adminScreenModal || !adminScreenModal.classList.contains("is-open") || !adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active") return false;
      const target = event.target;
      if (target && target !== adminScreenView && target !== adminScreenVideo && target !== adminScreenImg) return false;
      queueAdminScreenControl({{
        type,
        key: event.key || "",
        code: event.code || "",
        repeat: Boolean(event.repeat),
        ctrl: Boolean(event.ctrlKey),
        alt: Boolean(event.altKey),
        shift: Boolean(event.shiftKey),
        meta: Boolean(event.metaKey),
      }}, true);
      return true;
    }};
    const updateAdminScreenMicButton = () => {{
      if (!adminScreenMic) return;
      const record = adminScreenUser ? adminChatUserRecord(adminScreenUser) : null;
      const streamState = record && record.stream && record.stream.state
        ? record.stream.state
        : (adminStreamUser === adminScreenUser && adminStreamSession ? adminStreamSession.state || "" : "");
      adminScreenMic.textContent = streamState === "active"
        ? "Mic on"
        : streamState === "pending_admin"
          ? "Accept mic"
          : streamState === "pending_user"
            ? "Waiting mic"
            : "Mic stream";
    }};
    const updateAdminScreenStatus = (session = adminScreenSession) => {{
      if (!adminScreenStatus) return;
      const state = session && session.state || "";
      if (state === "active") {{
        const rtcState = adminScreenPeer ? (adminScreenPeer.connectionState || adminScreenPeer.iceConnectionState || "connecting") : "starting";
        adminScreenStatus.textContent = adminScreenAnswerSet
          ? `Realtime screen WebRTC: ${{rtcState}}.`
          : "Realtime screen: waiting for direct WebRTC video...";
      }} else if (state === "pending_user") {{
        adminScreenStatus.textContent = "Waiting for user to click Screen and choose the browser/tab.";
      }} else if (state) {{
        adminScreenStatus.textContent = `Screen preview ${{state}}.`;
      }} else {{
        adminScreenStatus.textContent = "No screen preview session.";
      }}
      updateAdminScreenMicButton();
    }};
    const sendAdminScreenWebRtcSignal = async (type, data) => {{
      if (!adminScreenSession || !adminScreenUser || !type || !data) return;
      await fetch("/screen/admin/signal", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{
          username: adminScreenUser,
          session: adminScreenSession.id,
          type,
          data,
        }}),
      }});
    }};
    const adminScreenPeerState = () => adminScreenPeer ? (adminScreenPeer.connectionState || adminScreenPeer.iceConnectionState || "") : "";
    const adminScreenNeedsReconnect = () => {{
      const state = adminScreenPeerState();
      const waited = Date.now() - Number(adminScreenPeerStartedAt || 0);
      const noVideoYet = !adminScreenVideo || !adminScreenVideo.srcObject;
      return Boolean(adminScreenPeer && (["failed", "disconnected", "closed"].includes(state) || (noVideoYet && waited > 8000)));
    }};
    const startAdminScreenWebRtc = async () => {{
      if (!adminScreenSession || adminScreenSession.state !== "active" || adminScreenPeer) return;
      if (!window.RTCPeerConnection) {{
        if (adminScreenStatus) adminScreenStatus.textContent = "Browser khong ho tro WebRTC.";
        return;
      }}
      adminScreenPeer = new RTCPeerConnection(adminWebRtcConfig);
      adminScreenPeerStartedAt = Date.now();
      try {{
        adminScreenControlChannel = adminScreenPeer.createDataChannel("screen-control", {{ ordered: true }});
        adminScreenControlChannel.addEventListener("open", () => updateAdminScreenStatus(adminScreenSession || {{}}));
        adminScreenControlChannel.addEventListener("close", () => {{
          if (adminScreenControlChannel && adminScreenControlChannel.readyState === "closed") {{
            adminScreenControlChannel = null;
          }}
          updateAdminScreenStatus(adminScreenSession || {{}});
        }});
      }} catch (error) {{
        adminScreenControlChannel = null;
      }}
      try {{
        adminScreenPeer.addTransceiver("video", {{ direction: "recvonly" }});
      }} catch (error) {{
      }}
      adminScreenPeer.addEventListener("icecandidate", (event) => {{
        if (event.candidate) {{
          sendAdminScreenWebRtcSignal("candidate", event.candidate.toJSON()).catch(() => {{}});
        }}
      }});
      adminScreenPeer.addEventListener("track", (event) => {{
        const stream = event.streams && event.streams[0] ? event.streams[0] : new MediaStream([event.track]);
        if (adminScreenVideo) {{
          adminScreenVideo.srcObject = stream;
          adminScreenVideo.style.display = "block";
          if (adminScreenImg) {{
            adminScreenImg.style.display = "none";
          }}
          adminScreenVideo.play().catch(() => {{
            if (adminScreenStatus) adminScreenStatus.textContent = "Screen connected, browser blocked autoplay.";
          }});
        }}
      }});
      adminScreenPeer.addEventListener("connectionstatechange", () => updateAdminScreenStatus(adminScreenSession || {{}}));
      const offer = await adminScreenPeer.createOffer({{ offerToReceiveVideo: true }});
      await adminScreenPeer.setLocalDescription(offer);
      await sendAdminScreenWebRtcSignal("offer", adminScreenPeer.localDescription.toJSON());
      adminScreenOfferSent = true;
      updateAdminScreenStatus(adminScreenSession || {{}});
    }};
    const pollAdminScreenWebRtc = async () => {{
      if (!adminScreenUser || !adminScreenSession || adminScreenSession.state !== "active" || !adminScreenPeer) return;
      try {{
        const response = await fetch(`/screen/admin/signal?username=${{encodeURIComponent(adminScreenUser)}}&session=${{encodeURIComponent(adminScreenSession.id)}}&after=${{encodeURIComponent(String(adminScreenRemoteCandidateId))}}`, {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not poll screen WebRTC.");
        if (payload.session && payload.session.state !== "active") {{
          await handleAdminScreenSession(adminScreenUser, payload.session);
          return;
        }}
        if (payload.answer && !adminScreenAnswerSet) {{
          await adminScreenPeer.setRemoteDescription(new RTCSessionDescription(payload.answer));
          adminScreenAnswerSet = true;
        }}
        const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
        for (const item of candidates) {{
          if (item.candidate && adminScreenAnswerSet) {{
            adminScreenRemoteCandidateId = Math.max(adminScreenRemoteCandidateId, Number(item.id || 0));
            try {{
              await adminScreenPeer.addIceCandidate(new RTCIceCandidate(item.candidate));
            }} catch (error) {{
            }}
          }}
        }}
        updateAdminScreenStatus(adminScreenSession || {{}});
      }} catch (error) {{
        if (adminScreenStatus) adminScreenStatus.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const pollAdminScreenFrame = async () => {{
      adminScreenFrameId = 0;
      adminScreenFrameSeenAt = 0;
    }};
    const handleAdminScreenSession = async (username, session = {{}}) => {{
      const nextId = session && session.id ? session.id : "";
      if (nextId && adminScreenSession && adminScreenSession.id && adminScreenSession.id !== nextId) {{
        stopAdminScreenTransport();
      }}
      if (session && session.id) {{
        adminScreenUser = username || session.username || adminScreenUser;
        adminScreenSession = session;
      }} else {{
        adminScreenSession = null;
      }}
      if (adminScreenSession && adminScreenSession.state === "active") {{
        if (adminScreenNeedsReconnect()) {{
          stopAdminScreenTransport();
          adminScreenUser = username || session.username || adminScreenUser;
          adminScreenSession = session;
        }}
        try {{
          await startAdminScreenWebRtc();
          if (!adminScreenPollTimer) scheduleAdminScreenWebRtcPoll();
        }} catch (error) {{
          if (adminScreenStatus) adminScreenStatus.textContent = String(error && error.message ? error.message : error);
        }}
      }} else if (!adminScreenSession || ["ended", "rejected", "error"].includes(adminScreenSession.state || "")) {{
        stopAdminScreenTransport();
      }}
      updateAdminScreenStatus(adminScreenSession || {{}});
    }};
    const openAdminScreen = (username, session = {{}}) => {{
      adminScreenUser = username || (session && session.username) || "";
      if (adminScreenTitle) adminScreenTitle.textContent = `Screen preview: ${{adminScreenUser || "user"}}`;
      if (adminScreenModal) adminScreenModal.classList.add("is-open");
      if (typeof pollChatAdmin === "function") void pollChatAdmin();
      if (session && session.state === "active" && adminScreenUser === (username || session.username || "") && adminScreenNeedsReconnect()) {{
        stopAdminScreenTransport();
      }}
      void handleAdminScreenSession(adminScreenUser, session || {{}});
      updateAdminScreenStatus(session || {{}});
    }};
    const hideAdminScreen = async () => {{
      queueAdminScreenCursorHidden();
      if (document.fullscreenElement) {{
        try {{ await document.exitFullscreen(); }} catch (error) {{}}
      }}
      if (adminScreenModal) adminScreenModal.classList.remove("is-open");
      updateAdminScreenStatus(adminScreenSession || {{}});
    }};
    const stopAdminUserLive = async (itemOrUsername) => {{
      const username = typeof itemOrUsername === "string"
        ? itemOrUsername
        : (itemOrUsername && itemOrUsername.username || "");
      if (!username) return;
      const record = typeof itemOrUsername === "string"
        ? (adminChatUserRecord(username) || {{ username }})
        : (itemOrUsername || {{ username }});
      const screenSession = (record.screen && record.screen.id)
        ? record.screen
        : (adminScreenUser === username ? adminScreenSession : null);
      const streamSession = (record.stream && record.stream.id)
        ? record.stream
        : (adminStreamUser === username ? adminStreamSession : null);
      try {{
        let latestUsers = null;
        if (screenSession && screenSession.id && ["pending_user", "active"].includes(screenSession.state || "")) {{
          const response = await fetch("/screen/admin/action", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ username, session: screenSession.id, action: "end" }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not stop screen.");
          latestUsers = payload.users || latestUsers;
        }}
        if (streamSession && streamSession.id && ["pending_admin", "pending_user", "active"].includes(streamSession.state || "")) {{
          const response = await fetch("/stream/admin/action", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ username, session: streamSession.id, action: "end" }}),
          }});
          const payload = await response.json().catch(() => ({{}}));
          if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not stop stream.");
          latestUsers = payload.users || latestUsers;
        }}
        if (adminScreenUser === username) {{
          stopAdminScreenTransport();
          if (adminScreenModal) adminScreenModal.classList.remove("is-open");
          adminScreenSession = null;
          adminScreenUser = "";
        }}
        if (adminStreamUser === username) {{
          await handleAdminStreamSession("", {{}});
        }}
        if (latestUsers) {{
          adminChatState = {{ users: latestUsers, online_count: Number(adminChatState.online_count || 0) }};
          renderOnlineUsers(adminChatState.users, adminChatState);
        }} else {{
          pollChatAdmin();
        }}
      }} catch (error) {{
        messageNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const clearAdminUserChat = async (itemOrUsername) => {{
      const username = typeof itemOrUsername === "string"
        ? itemOrUsername
        : (itemOrUsername && itemOrUsername.username || "");
      if (!username) return;
      const now = Date.now();
      const armedAt = Number(adminClearChatArmed.get(username) || 0);
      if (now - armedAt > 3500) {{
        adminClearChatArmed.set(username, now);
        messageNode.textContent = `Click Clear again within 3 seconds to delete chat data for ${{username}}.`;
        return;
      }}
      adminClearChatArmed.delete(username);
      try {{
        const response = await fetch("/chat/admin/clear", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ username }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not clear chat.");
        adminChatState = {{ users: payload.users || [], online_count: Number(payload.online_count || 0) }};
        if (adminChatUser === username) {{
          adminChatUser = "";
          if (adminChatModal) adminChatModal.classList.remove("is-open");
        }}
        renderOnlineUsers(adminChatState.users, adminChatState);
        messageNode.textContent = `Cleared ${{payload.removed_messages || 0}} messages, ${{payload.removed_attachments || 0}} attachments, ${{payload.removed_audio || 0}} audio files for ${{username}}.`;
      }} catch (error) {{
        messageNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const respondSpeakSkipRequest = async (item, action = "accept") => {{
      const username = item && item.username || "";
      const request = item && item.speak_skip || null;
      if (!username || !request || !request.id) return;
      try {{
        const response = await fetch("/space-w/speak-skip/respond", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ username, id: request.id, action }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not respond to Speak skip.");
        adminChatState = {{ users: payload.users || [], online_count: Number(payload.online_count || 0) }};
        renderOnlineUsers(adminChatState.users, adminChatState);
        messageNode.textContent = `Speak skip ${{payload.request && payload.request.status || action}} for ${{username}}.`;
      }} catch (error) {{
        messageNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    if (adminScreenClose) adminScreenClose.addEventListener("click", () => void hideAdminScreen());
    if (adminScreenModal) adminScreenModal.addEventListener("click", (event) => {{
      if (event.target === adminScreenModal) void hideAdminScreen();
    }});
    if (adminPaintClose) adminPaintClose.addEventListener("click", closeAdminPaint);
    if (adminPaintModal) adminPaintModal.addEventListener("click", (event) => {{
      if (event.target === adminPaintModal) closeAdminPaint();
    }});
    adminPaintModeButtons.forEach((button) => {{
      button.addEventListener("click", () => setAdminPaintMode(button.dataset.adminPaintMode || "pen"));
    }});
    if (adminPaintClear) adminPaintClear.addEventListener("click", () => {{
      clearAdminPaintCanvas();
      scheduleAdminPaintSync(80);
    }});
    if (adminPaintDelete) adminPaintDelete.addEventListener("click", deleteAdminPaintSelection);
    if (adminPaintImage) adminPaintImage.addEventListener("click", () => {{
      if (adminPaintImageFile) adminPaintImageFile.click();
    }});
    if (adminPaintImageFile) adminPaintImageFile.addEventListener("change", () => {{
      const file = adminPaintImageFile.files && adminPaintImageFile.files[0];
      if (file) addAdminPaintImageFile(file);
      adminPaintImageFile.value = "";
    }});
    if (adminPaintPaste) adminPaintPaste.addEventListener("click", () => void pasteAdminPaintImageFromClipboard());
    if (adminPaintZoomOut) adminPaintZoomOut.addEventListener("click", () => setAdminPaintZoom(adminPaintZoom / 1.18));
    if (adminPaintZoomIn) adminPaintZoomIn.addEventListener("click", () => setAdminPaintZoom(adminPaintZoom * 1.18));
    if (adminPaintFullscreen) adminPaintFullscreen.addEventListener("click", () => void toggleAdminPaintFullscreen());
    if (adminPaintTab) adminPaintTab.addEventListener("click", openAdminPaintInTab);
    if (adminPaintCanvas) {{
      adminPaintCanvas.addEventListener("pointerdown", handleAdminPaintPointerDown);
      adminPaintCanvas.addEventListener("pointermove", handleAdminPaintPointerMove);
      adminPaintCanvas.addEventListener("pointerup", handleAdminPaintPointerEnd);
      adminPaintCanvas.addEventListener("pointercancel", handleAdminPaintPointerEnd);
      adminPaintCanvas.addEventListener("pointerenter", (event) => updateAdminPaintLocalCursor(event, true));
      adminPaintCanvas.addEventListener("pointermove", (event) => updateAdminPaintLocalCursor(event, true));
      adminPaintCanvas.addEventListener("pointerleave", (event) => updateAdminPaintLocalCursor(event, false));
      if (window.ResizeObserver) {{
        const adminPaintResizeObserver = new ResizeObserver(() => {{
          if (adminPaintModal && adminPaintModal.classList.contains("is-open")) resizeAdminPaintCanvas();
        }});
        adminPaintResizeObserver.observe(adminPaintCanvas);
      }}
    }}
    document.addEventListener("fullscreenchange", () => {{
      if (adminPaintModal && adminPaintModal.classList.contains("is-open")) {{
        window.setTimeout(resizeAdminPaintCanvas, 80);
      }}
    }});
    document.addEventListener("paste", (event) => {{
      if (!adminPaintModal || !adminPaintModal.classList.contains("is-open")) return;
      const items = Array.from(event.clipboardData && event.clipboardData.items || []);
      const imageItem = items.find((item) => item && String(item.type || "").startsWith("image/"));
      if (!imageItem) return;
      event.preventDefault();
      const file = imageItem.getAsFile();
      if (file) addAdminPaintImageFile(file);
    }});
    document.addEventListener("keydown", (event) => {{
      if ((event.key === "Delete" || event.key === "Backspace") && adminPaintModal && adminPaintModal.classList.contains("is-open") && adminPaintSelection && !adminPaintTextEditor) {{
        event.preventDefault();
        deleteAdminPaintSelection();
      }}
    }});
    if (adminScreenView) {{
      adminScreenView.tabIndex = 0;
      adminScreenView.addEventListener("pointerenter", (event) => {{
        queueAdminScreenPointerControl(event, "cursor", {{ dispatch: false }});
      }});
      adminScreenView.addEventListener("pointermove", (event) => {{
        const isDragging = Boolean(event.buttons);
        queueAdminScreenPointerControl(event, isDragging ? "pointermove" : "cursor", {{ dispatch: isDragging, urgent: isDragging }});
      }});
      adminScreenView.addEventListener("pointerleave", () => {{
        queueAdminScreenCursorHidden();
      }});
      adminScreenView.addEventListener("pointerdown", (event) => {{
        if (event.button !== 0 && event.button !== 1 && event.button !== 2) return;
        if (!queueAdminScreenPointerControl(event, "pointerdown", {{ urgent: true }})) return;
        event.preventDefault();
        adminScreenPointerDown = {{ x: event.clientX, y: event.clientY, button: event.button }};
        try {{ adminScreenView.focus({{ preventScroll: true }}); }} catch (error) {{ adminScreenView.focus(); }}
        try {{ adminScreenView.setPointerCapture(event.pointerId); }} catch (error) {{}}
      }});
      adminScreenView.addEventListener("pointerup", (event) => {{
        queueAdminScreenPointerControl(event, "pointerup", {{ urgent: true }});
        try {{ adminScreenView.releasePointerCapture(event.pointerId); }} catch (error) {{}}
      }});
      adminScreenView.addEventListener("click", (event) => {{
        const moved = adminScreenPointerDown ? Math.hypot(event.clientX - adminScreenPointerDown.x, event.clientY - adminScreenPointerDown.y) : 0;
        adminScreenPointerDown = null;
        if (moved <= 6) {{
          queueAdminScreenPointerControl(event, "click", {{ urgent: true }});
        }}
      }});
      adminScreenView.addEventListener("contextmenu", (event) => {{
        event.preventDefault();
        event.stopPropagation();
        const point = adminScreenControlPoint(event);
        if (!point) return;
        try {{ adminScreenView.focus({{ preventScroll: true }}); }} catch (error) {{ adminScreenView.focus(); }}
        queueAdminScreenControl({{
          type: "click",
          x: point.x,
          y: point.y,
          visible: true,
          button: 2,
          buttons: 0,
          ctrl: Boolean(event.ctrlKey),
          alt: Boolean(event.altKey),
          shift: Boolean(event.shiftKey),
          meta: Boolean(event.metaKey),
        }}, true);
      }});
      adminScreenView.addEventListener("dblclick", (event) => {{
        queueAdminScreenPointerControl(event, "dblclick", {{ urgent: true }});
      }});
      adminScreenView.addEventListener("wheel", (event) => {{
        const point = adminScreenControlPoint(event);
        if (!point) return;
        event.preventDefault();
        queueAdminScreenControl({{
          type: "wheel",
          x: point.x,
          y: point.y,
          visible: true,
          delta_x: event.deltaX,
          delta_y: event.deltaY,
          ctrl: Boolean(event.ctrlKey),
          alt: Boolean(event.altKey),
          shift: Boolean(event.shiftKey),
          meta: Boolean(event.metaKey),
        }}, true);
      }}, {{ passive: false }});
      adminScreenView.addEventListener("keydown", (event) => {{
        if (queueAdminScreenKeyControl(event, "keydown")) event.preventDefault();
      }});
      adminScreenView.addEventListener("keyup", (event) => {{
        if (queueAdminScreenKeyControl(event, "keyup")) event.preventDefault();
      }});
    }}
    if (adminScreenFullscreen) adminScreenFullscreen.addEventListener("click", async () => {{
      const target = adminScreenCard || adminScreenView || adminScreenModal;
      try {{
        if (document.fullscreenElement) {{
          await document.exitFullscreen();
        }} else if (target && target.requestFullscreen) {{
          await target.requestFullscreen();
        }}
      }} catch (error) {{
        if (adminScreenStatus) adminScreenStatus.textContent = String(error && error.message ? error.message : error);
      }}
    }});
    if (adminScreenMic) adminScreenMic.addEventListener("click", () => {{
      if (!adminScreenUser) return;
      const record = adminChatUserRecord(adminScreenUser) || {{ username: adminScreenUser, stream: adminStreamUser === adminScreenUser ? adminStreamSession : {{}} }};
      void requestOrAcceptAdminStream(record).then(updateAdminScreenMicButton);
    }});
    const requestAdminMicIfNeeded = async (username, streamSession = null) => {{
      const state = streamSession && streamSession.state || "";
      if (!username || ["pending_admin", "pending_user", "active"].includes(state)) return;
      try {{
        const response = await fetch("/stream/admin/request", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ username }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not request mic stream.");
        adminChatState = {{ users: payload.users || adminChatState.users || [], online_count: Number(payload.online_count || adminChatState.online_count || 0) }};
        renderOnlineUsers(adminChatState.users, adminChatState);
        if (payload.session) {{
          await handleAdminStreamSession(username, payload.session);
        }}
        updateAdminScreenMicButton();
      }} catch (error) {{
        messageNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const requestOrOpenAdminScreen = async (item) => {{
      const username = item && item.username || "";
      if (!username) return;
      const session = item.screen || null;
      if (session && session.id && ["pending_user", "active"].includes(session.state || "")) {{
        openAdminScreen(username, session);
        void requestAdminMicIfNeeded(username, item.stream || null);
        return;
      }}
      try {{
        const response = await fetch("/screen/admin/request", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ username }}),
        }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not request screen.");
        adminChatState = {{ users: payload.users || adminChatState.users || [], online_count: Number(payload.online_count || adminChatState.online_count || 0) }};
        renderOnlineUsers(adminChatState.users, adminChatState);
        openAdminScreen(username, payload.session || {{}});
        const nextRecord = adminChatUserRecord(username) || item || {{}};
        void requestAdminMicIfNeeded(username, nextRecord.stream || null);
      }} catch (error) {{
        messageNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const screenPreviewKey = (item = {{}}) => `${{item.username || ""}}:${{item.screen && item.screen.id || ""}}`;
    let adminOnlineRenderedSignature = "";
    const dashboardModalOpen = () => Boolean(
      (adminChatModal && adminChatModal.classList.contains("is-open"))
      || (adminScreenModal && adminScreenModal.classList.contains("is-open"))
      || (adminPaintModal && adminPaintModal.classList.contains("is-open"))
      || adminStreamSession
    );
    // Added 2026-07-01: online presence comes from authenticated user requests, while live tools still poll faster.
    // Updated 2026-07-09: keep the Online tab count fresh even while another dashboard tab is open.
    const shouldPollChatAdminState = () => Boolean(dashboardPollIsFocused());
    const adminOnlineSignature = (items, state = adminChatState) => {{
      const rows = Array.isArray(items) ? items : [];
      const onlineTotal = Number(state && state.online_count || rows.filter((item) => item && item.online).length || 0);
      const parts = rows.map((item) => {{
        const stream = item.stream || {{}};
        const screen = item.screen || {{}};
        const activity = item.activity || {{}};
        const paint = item.paint || {{}};
        const speakSkip = item.speak_skip || {{}};
        const messages = Array.isArray(item.messages) ? item.messages : [];
        const lastMessage = messages.length ? messages[messages.length - 1] : (item.last_message || {{}});
        const preview = adminScreenPreviewCache.get(screenPreviewKey(item)) || {{}};
        return [
          item.username || "",
          item.online ? "1" : "0",
          Number(item.unread || 0),
          stream.id || "",
          stream.state || "",
          screen.id || "",
          screen.state || "",
          Number(screen.frame_id || 0),
          Number(preview.frameId || 0),
          activity.status || "",
          activity.space || "",
          activity.title || "",
          activity.path || "",
          Number(activity.nodeIndex || 0),
          Number(activity.nodeCount || 0),
          Number(paint.revision || 0),
          speakSkip.status || "",
          speakSkip.id || "",
          Number(speakSkip.nodeIndex || 0),
          Number(lastMessage.id || 0),
          lastMessage.peer_read ? "1" : "0",
        ].join("~");
      }});
      return `${{onlineTotal}}::${{parts.join("||")}}`;
    }};
    const pollAdminScreenPreviews = async () => {{
      if (document.hidden || activeDashboardTab !== "users") return;
      const changed = adminScreenPreviewCache.size > 0;
      adminScreenPreviewCache.clear();
      if (changed) {{
        renderOnlineUsers(adminChatState.users || [], adminChatState);
      }}
    }};
    const renderOnlineUsers = (items, state = adminChatState) => {{
      const rows = Array.isArray(items) ? items : [];
      const unreadTotal = rows.reduce((sum, item) => sum + Number(item.unread || 0), 0);
      const onlineTotal = Number(state && state.online_count || rows.filter((item) => item && item.online).length || 0);
      if (tabChatBadge) {{
        setTextIfChanged(tabChatBadge, onlineTotal);
        tabChatBadge.classList.toggle("is-empty", onlineTotal <= 0);
        tabChatBadge.title = unreadTotal
          ? `${{onlineTotal}} online | ${{unreadTotal}} unread chat message(s)`
          : `${{onlineTotal}} online user(s)`;
      }}
      if (activeDashboardTab !== "users") return;
      const signature = adminOnlineSignature(rows, state);
      if (signature === adminOnlineRenderedSignature) return;
      adminOnlineRenderedSignature = signature;
      onlineUsersNode.textContent = "";
      if (!rows.length) {{
        onlineUsersNode.textContent = "No online users yet.";
        return;
      }}
      rows.forEach((item) => {{
        const row = document.createElement("div");
        row.className = "online-row";
        const controls = document.createElement("div");
        controls.className = "online-controls";
        const identity = document.createElement("div");
        identity.className = "online-identity";
        const actions = document.createElement("div");
        actions.className = "online-actions";
        const realtimeNode = document.createElement("div");
        const details = document.createElement("div");
        details.className = "online-details";
        const detailsText = document.createElement("div");
        detailsText.className = "online-details-text";
        const name = document.createElement("div");
        name.className = "online-name";
        name.innerHTML = `<span class="online-dot ${{item.online ? "" : "off"}}"></span>${{item.username || ""}}`;
        const meta = document.createElement("div");
        meta.className = "online-meta";
        const screenStateForMeta = item.screen && item.screen.state || "";
        const screenFrameIdForMeta = Number(item.screen && item.screen.frame_id || 0);
        const activity = item.activity || {{}};
        const activityParts = [];
        if (activity.status) activityParts.push(activity.status);
        if (activity.space) activityParts.push(activity.space);
        if (activity.title) activityParts.push(activity.title);
        const nodeCount = Number(activity.nodeCount || 0);
        const nodeIndex = Number(activity.nodeIndex || 0);
        if (nodeCount > 0) activityParts.push(`node ${{Math.min(nodeCount, nodeIndex + 1)}}/${{nodeCount}}`);
        if (activity.path) activityParts.push(activity.path);
        meta.textContent = `Last seen: ${{item.last_seen || ""}}${{screenStateForMeta ? ` | Screen: ${{screenStateForMeta}} | WebRTC direct` : ""}}`;
        realtimeNode.className = "online-realtime" + (activityParts.length ? "" : " is-idle");
        realtimeNode.textContent = activityParts.length
          ? `Realtime: ${{activityParts.join(" | ")}}`
          : "Realtime: idle";
        identity.appendChild(name);
        detailsText.appendChild(meta);
        details.appendChild(detailsText);
        const activeScreen = item.screen && item.screen.id && (["pending_user", "active"].includes(item.screen.state || "") || Number(item.screen.frame_id || 0) > 0);
        if (activeScreen) {{
          const preview = document.createElement("button");
          preview.className = "online-screen-preview";
          preview.type = "button";
          preview.title = "Open realtime screen preview";
          const cached = adminScreenPreviewCache.get(screenPreviewKey(item));
          if (cached && cached.data) {{
            preview.classList.add("is-live");
            const image = document.createElement("img");
            image.alt = `${{item.username || "User"}} screen preview`;
            image.src = cached.data;
            preview.appendChild(image);
          }} else {{
          preview.textContent = "Open direct screen";
          }}
          preview.addEventListener("click", () => requestOrOpenAdminScreen(item));
          details.appendChild(preview);
          const note = document.createElement("div");
          note.className = "online-screen-preview-note";
          note.textContent = "WebRTC direct only";
          details.appendChild(note);
        }}
        const unread = Number(item.unread || 0);
        const chat = document.createElement("button");
        chat.className = "pending-action";
        chat.type = "button";
        chat.textContent = "Chat";
        chat.addEventListener("click", () => openAdminChat(item.username || ""));
        const notify = document.createElement("button");
        notify.className = "pending-action" + (unread ? " accept" : "");
        notify.type = "button";
        notify.textContent = unread ? `Notification ${{unread}}` : "Notification";
        notify.disabled = !unread;
        notify.addEventListener("click", () => openAdminChat(item.username || ""));
        const speakSkip = item.speak_skip || {{}};
        const speakSkipPending = speakSkip && speakSkip.status === "pending";
        const speakSkipButton = document.createElement("button");
        speakSkipButton.className = "pending-action" + (speakSkipPending ? " accept" : "");
        speakSkipButton.type = "button";
        speakSkipButton.textContent = speakSkipPending ? "Accept Speak skip" : "Speak skip";
        speakSkipButton.disabled = !speakSkipPending;
        speakSkipButton.title = speakSkipPending
          ? `Node ${{Number(speakSkip.nodeIndex || 0) + 1}} | ${{speakSkip.title || "Space_W"}}`
          : "No pending Speak error report";
        speakSkipButton.addEventListener("click", () => void respondSpeakSkipRequest(item, "accept"));
        const stream = document.createElement("button");
        const streamState = item.stream && item.stream.state || "";
        stream.className = "pending-action" + (streamState === "active" ? " accept" : "");
        stream.type = "button";
        stream.textContent = streamState === "active"
          ? "Stream on"
          : streamState === "pending_admin"
            ? "Accept stream"
            : streamState === "pending_user"
              ? "Waiting stream"
              : "Stream";
        stream.disabled = !item.online || streamState === "pending_user";
        stream.addEventListener("click", () => requestOrAcceptAdminStream(item));
        const screen = document.createElement("button");
        const screenState = item.screen && item.screen.state || "";
        screen.className = "pending-action" + (screenState === "active" ? " accept" : "");
        screen.type = "button";
        screen.textContent = screenState === "active"
          ? "Screen on"
          : screenState === "pending_user"
            ? "Waiting screen"
            : "Screen";
        screen.disabled = !item.online && !screenState;
        screen.addEventListener("click", () => requestOrOpenAdminScreen(item));
        const paint = document.createElement("button");
        const paintRevision = Number(item.paint && item.paint.revision || 0);
        paint.className = "pending-action" + (paintRevision ? " accept" : "");
        paint.type = "button";
        paint.textContent = paintRevision ? `Paint ${{paintRevision}}` : "Paint";
        paint.disabled = !item.username;
        paint.title = "Open connected paint board";
        paint.addEventListener("click", () => openAdminPaint(item));
        const off = document.createElement("button");
        const hasLiveScreen = screenState && ["pending_user", "active"].includes(screenState);
        const hasLiveStream = streamState && ["pending_admin", "pending_user", "active"].includes(streamState);
        off.className = "pending-action reject";
        off.type = "button";
        off.textContent = "Off";
        off.disabled = !(hasLiveScreen || hasLiveStream);
        off.title = "Stop screen preview and mic stream for this user";
        off.addEventListener("click", () => void stopAdminUserLive(item));
        const clearChat = document.createElement("button");
        clearChat.className = "pending-action reject";
        clearChat.type = "button";
        clearChat.textContent = "Clear";
        clearChat.title = "Clear this user's chat messages, attachments, and chat voice files";
        clearChat.addEventListener("click", () => void clearAdminUserChat(item));
        actions.append(chat, notify, speakSkipButton, stream, screen, paint, off, clearChat);
        controls.append(identity, actions);
        row.append(controls, realtimeNode, details);
        onlineUsersNode.appendChild(row);
      }});
    }};
    const pollChatAdmin = async () => {{
      if (!shouldPollChatAdminState()) return;
      try {{
        const previousChatRecord = adminChatUser && adminChatModal && adminChatModal.classList.contains("is-open")
          ? adminChatUserRecord(adminChatUser)
          : null;
        const previousChatIds = new Set(
          previousChatRecord && Array.isArray(previousChatRecord.messages)
            ? previousChatRecord.messages.map((item) => Number(item.id || 0)).filter(Boolean)
            : []
        );
        const chatStateQuery = new URLSearchParams({{ ts: String(Date.now()) }});
        chatStateQuery.set("activity", activeDashboardTab === "users" ? "1" : "0");
        if (adminChatUser && adminChatModal && adminChatModal.classList.contains("is-open")) {{
          chatStateQuery.set("messages_for", adminChatUser);
          chatStateQuery.set("activity", "1");
        }}
        const response = await fetch("/chat/admin/state?" + chatStateQuery.toString(), {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) throw new Error(payload.error || "Could not load chat.");
        adminChatState = {{ users: payload.users || [], online_count: Number(payload.online_count || 0) }};
        renderOnlineUsers(adminChatState.users, adminChatState);
        const streamRows = adminChatState.users || [];
        const streamRecord = adminStreamSession
          ? streamRows.find((item) => item.stream && item.stream.id === adminStreamSession.id)
          : streamRows.find((item) => item.stream && item.stream.id && item.stream.state === "active");
        if (streamRecord && streamRecord.stream) {{
          await handleAdminStreamSession(streamRecord.username || "", streamRecord.stream);
        }} else if (adminStreamSession) {{
          await handleAdminStreamSession("", {{}});
        }}
        if (adminScreenUser && adminScreenModal && adminScreenModal.classList.contains("is-open")) {{
          const screenRecord = (adminChatState.users || []).find((item) => item.username === adminScreenUser);
          if (screenRecord && screenRecord.screen && screenRecord.screen.id) {{
            await handleAdminScreenSession(screenRecord.username || adminScreenUser, screenRecord.screen);
          }}
        }}
        if (adminChatUser && adminChatModal.classList.contains("is-open")) {{
          const record = adminChatUserRecord(adminChatUser);
          const rows = record && Array.isArray(record.messages) ? record.messages : [];
          const newUserMessageIds = new Set(rows
            .filter((item) => item && item.sender === "user" && Number(item.id || 0) && !previousChatIds.has(Number(item.id || 0)))
            .map((item) => Number(item.id || 0)));
          const nextSignature = adminChatRowsSignature(rows);
          if (adminChatRenderedUser !== adminChatUser || adminChatRenderedSignature !== nextSignature) {{
            renderAdminChatLog(adminChatUser, newUserMessageIds, {{ scroll: Boolean(newUserMessageIds.size) }});
          }}
          if (newUserMessageIds.size) {{
            fetch("/chat/admin/read", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ username: adminChatUser }}),
            }}).catch(() => {{}});
          }}
        }}
      }} catch (error) {{
        if (onlineUsersNode) onlineUsersNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const renderPendingUsers = (items) => {{
      pendingUsersNode.textContent = "";
      const rows = Array.isArray(items) ? items : [];
      if (!rows.length) {{
        pendingUsersNode.textContent = "Khong co dang ky dang cho.";
        return;
      }}
      rows.forEach((item) => {{
        const row = document.createElement("div");
        row.className = "pending-row";
        const name = document.createElement("div");
        name.className = "pending-name";
        name.textContent = `${{item.username || ""}} | ${{item.full_name || ""}} | ${{item.gender || ""}} | ${{item.birth_date || ""}}`;
        const accept = document.createElement("button");
        accept.className = "pending-action";
        accept.type = "button";
        accept.textContent = "Chap nhan";
        const reject = document.createElement("button");
        reject.className = "pending-action reject";
        reject.type = "button";
        reject.textContent = "Tu choi";
        const send = async (action) => {{
          accept.disabled = true;
          reject.disabled = true;
          try {{
            const response = await fetch("/auth/approve", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{ username: item.username, action }}),
            }});
            const payload = await response.json().catch(() => ({{}}));
            if (!response.ok || payload.ok === false) {{
              throw new Error(payload.error || "Khong duyet duoc.");
            }}
            renderPendingUsers(payload.pending || []);
          }} catch (error) {{
            messageNode.textContent = String(error && error.message ? error.message : error);
            accept.disabled = false;
            reject.disabled = false;
          }}
        }};
        accept.addEventListener("click", () => send("accept"));
        reject.addEventListener("click", () => send("reject"));
        row.append(name, accept, reject);
        pendingUsersNode.appendChild(row);
      }});
    }};
    // Added 2026-07-09: mirrors pending password reset count onto the dedicated dashboard tab.
    const renderPasswordResetBadge = (count) => {{
      if (!tabPasswordResetBadge) return;
      const total = Math.max(0, Number(count || 0) || 0);
      tabPasswordResetBadge.textContent = String(total);
      tabPasswordResetBadge.classList.toggle("is-empty", total <= 0);
      tabPasswordResetBadge.title = total ? `${{total}} password reset request(s) pending` : "No password reset requests.";
    }};
    const renderPasswordResetUsers = (items) => {{
      if (!passwordResetUsersNode) return;
      passwordResetUsersNode.textContent = "";
      const rows = Array.isArray(items) ? items : [];
      renderPasswordResetBadge(rows.length);
      if (!rows.length) {{
        passwordResetUsersNode.textContent = "Khong co yeu cau doi mat khau.";
        return;
      }}
      rows.forEach((item) => {{
        const row = document.createElement("div");
        row.className = "pending-row";
        const name = document.createElement("div");
        name.className = "pending-name";
        const email = item.email || item.email_alias || "";
        name.textContent = `${{item.username || ""}} | ${{item.full_name || ""}} | ${{email}} | ${{item.requested_at || ""}}`;
        const accept = document.createElement("button");
        accept.className = "pending-action";
        accept.type = "button";
        accept.textContent = "Cho phep doi";
        accept.title = "Cho phep user nay tu dat mat khau moi tren frontend.";
        const reject = document.createElement("button");
        reject.className = "pending-action reject";
        reject.type = "button";
        reject.textContent = "Tu choi";
        const send = async (action) => {{
          accept.disabled = true;
          reject.disabled = true;
          try {{
            const body = {{ username: item.username, action }};
            const response = await fetch("/auth/password-reset/admin", {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify(body),
            }});
            const payload = await response.json().catch(() => ({{}}));
            if (!response.ok || payload.ok === false) {{
              throw new Error(payload.error || "Khong duyet duoc doi mat khau.");
            }}
            renderPasswordResetUsers(payload.password_resets || []);
            renderPendingUsers(payload.pending || []);
            if (messageNode) messageNode.textContent = action === "reject" ? "Da tu choi yeu cau doi mat khau." : "Da cho phep user tu dat mat khau moi.";
          }} catch (error) {{
            if (messageNode) messageNode.textContent = String(error && error.message ? error.message : error);
            accept.disabled = false;
            reject.disabled = false;
          }}
        }};
        accept.addEventListener("click", () => send("accept"));
        reject.addEventListener("click", () => send("reject"));
        row.append(name, accept, reject);
        passwordResetUsersNode.appendChild(row);
      }});
    }};
    const pollPendingUsers = async () => {{
      try {{
        const response = await fetch("/auth/pending?ts=" + Date.now(), {{ cache: "no-store" }});
        const payload = await response.json().catch(() => ({{}}));
        if (!response.ok || payload.ok === false) {{
          pendingUsersNode.textContent = payload.error || "Chi may server moi xem duoc danh sach nay.";
          if (passwordResetUsersNode) passwordResetUsersNode.textContent = payload.error || "Chi may server moi xem duoc danh sach nay.";
          return;
        }}
        renderPendingUsers(payload.pending || []);
        renderPasswordResetUsers(payload.password_resets || []);
      }} catch (error) {{
        pendingUsersNode.textContent = String(error && error.message ? error.message : error);
        if (passwordResetUsersNode) passwordResetUsersNode.textContent = String(error && error.message ? error.message : error);
      }}
    }};
    const poll = async () => {{
      try {{
        const response = await fetch("/health?view=dashboard-v1&ts=" + Date.now(), {{ cache: "no-store" }});
        render(await response.json());
      }} catch (error) {{
        setDashboardStatus("Disconnected", ["error"]);
        setTextIfChanged(messageNode, String(error && error.message ? error.message : error));
      }}
    }};
    const startAdaptiveDashboardLoop = (fn, delayFor, options = {{}}) => {{
      let timer = 0;
      let running = false;
      let stopped = false;
      let lastStartedAt = 0;
      const minFocusDelay = Number(options.minFocusDelayMs || DASHBOARD_FOCUS_MIN_REQUEST_MS || 30000);
      const schedule = (delay, immediate = false) => {{
        if (stopped) return;
        window.clearTimeout(timer);
        timer = window.setTimeout(tick, immediate ? Math.max(0, Number(delay || 0)) : Math.max(800, Number(delay || 10000)));
      }};
      const tick = async () => {{
        if (stopped) return;
        if (running) {{
          schedule(delayFor());
          return;
        }}
        running = true;
        lastStartedAt = Date.now();
        try {{
          await fn();
        }} finally {{
          running = false;
          schedule(delayFor());
        }}
      }};
      const reset = () => {{
        if (stopped) return;
        if (dashboardPollIsFocused()) {{
          const elapsed = Date.now() - lastStartedAt;
          schedule(Math.max(0, minFocusDelay - elapsed), true);
          return;
        }}
        schedule(delayFor());
      }};
      const stop = () => {{
        stopped = true;
        window.clearTimeout(timer);
      }};
      document.addEventListener("visibilitychange", reset);
      window.addEventListener("focus", reset);
      window.addEventListener("blur", reset);
      window.addEventListener("pagehide", stop, {{ once: true }});
      if (options.immediate) {{
        void tick();
      }} else {{
        schedule(delayFor());
      }}
      return {{ reset, stop }};
    }};
    const healthPollDelay = () => dashboardPollIsFocused() ? dashboardBasePollDelay() : DASHBOARD_HIDDEN_POLL_MS;
    const announcementPollDelay = () => dashboardPollIsFocused() ? dashboardBasePollDelay() : DASHBOARD_HIDDEN_POLL_MS;
    const settingsPollDelay = () => dashboardPollIsFocused() ? dashboardBasePollDelay() : DASHBOARD_HIDDEN_POLL_MS;
    const pendingUsersPollDelay = () => dashboardPollIsFocused() ? dashboardBasePollDelay() : DASHBOARD_HIDDEN_POLL_MS;
    const dashboardPingDelay = () => dashboardPollIsFocused() ? dashboardBasePollDelay() : DASHBOARD_HIDDEN_POLL_MS;
    const chatPollDelay = () => {{
      if (!shouldPollChatAdminState()) return DASHBOARD_HIDDEN_POLL_MS;
      if (dashboardModalOpen() && dashboardPollIsFocused()) return 1800;
      if (activeDashboardTab !== "users") return Math.max(dashboardBasePollDelay(), 5000);
      return dashboardBasePollDelay();
    }};
    const screenPreviewPollDelay = () => dashboardBasePollDelay();
    poll();
    loadAnnouncements();
    loadSettings();
    pollPendingUsers();
    if (shouldPollChatAdminState()) pollChatAdmin();
    if (adminPaintAutoUser) {{
      window.setTimeout(() => openAdminPaint(adminPaintAutoUser), 450);
    }}
    renderAdminChatAudioToggles();
    loadAdminChatVoices();
    dashboardPingControl = startAdaptiveDashboardLoop(() => dashboardSignal("ping"), dashboardPingDelay);
    startAdaptiveDashboardLoop(poll, healthPollDelay);
    startAdaptiveDashboardLoop(loadAnnouncements, announcementPollDelay);
    startAdaptiveDashboardLoop(loadSettings, settingsPollDelay);
    startAdaptiveDashboardLoop(pollPendingUsers, pendingUsersPollDelay);
    startAdaptiveDashboardLoop(pollChatAdmin, chatPollDelay);
    startAdaptiveDashboardLoop(pollAdminScreenPreviews, screenPreviewPollDelay);
  </script>
</body>
</html>"""
