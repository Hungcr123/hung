// by LinuxDo Justinbiber

function b64url(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'');
}
async function newVerifier() { return b64url(crypto.getRandomValues(new Uint8Array(32))); }
async function mkChallenge(v) {
  return b64url(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(v)));
}
function newState() { return b64url(crypto.getRandomValues(new Uint8Array(32))); }

const CLIENT_ID    = 'app_EMoamEEZ73f0CkXaXp7hrann';
const REDIRECT_URI = 'http://localhost:1455/auth/callback';
const AUTH_BASE    = 'https://auth.openai.com/oauth/authorize';
const TOKEN_URL    = 'https://auth.openai.com/oauth/token';
const SCOPE        = 'openid profile email offline_access';

const INVITE_KEYS = ['inviteServerUrl','inviteApiKey'];
const INVITE_DEFAULTS = {
  inviteServerUrl: 'https://oai.yunxi668.cn',
  inviteApiKey: ''
};

const WEAK_INVITE_KEYS = new Set(['change-me', 'change-me-to-a-random-string', 'changeme', 'password', 'secret', 'test']);

function normalizeInviteServerUrl(value) {
  const raw = String(value || '').trim();
  const withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : `http://${raw}`;
  const url = new URL(withScheme);
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Server URL must be HTTP/HTTPS');
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol === 'http:' && !local) throw new Error('Remote Server URL must use HTTPS');
  return url.origin;
}

function isStrongInviteApiKey(key) {
  const value = String(key || '').trim();
  return value.length >= 24 && !WEAK_INVITE_KEYS.has(value.toLowerCase());
}

async function getInviteConfig() {
  const stored = await chrome.storage.local.get(INVITE_KEYS);
  const cfg = {};
  INVITE_KEYS.forEach(k => { cfg[k] = stored[k] !== undefined ? stored[k] : INVITE_DEFAULTS[k]; });
  return cfg;
}

async function getInviteServerStatus(cfg) {
  const baseUrl = normalizeInviteServerUrl(cfg.inviteServerUrl);
  const status = {
    serverOnline: false,
    authConfigured: false,
    loginConfigured: false,
    loggedIn: false,
    linuxDoUser: null,
    workspaceName: '',
    workspaceId: '',
    apiKeyConfigured: false,
    ready: false,
    missing: [],
    weak: [],
    proxyConfigured: false,
    autoKick: false,
    kickDelayMs: 0,
    activeInvites: [],
    optional: {},
    loginError: ''
  };

  const healthRes = await fetch(baseUrl + '/api/health?t=' + Date.now(), { cache: 'no-store' });
  const health = await healthRes.json();
  if (!healthRes.ok || !health.ok) throw new Error(health.error || ('HTTP ' + healthRes.status));

  status.serverOnline = true;
  status.authConfigured = !!health.auth_configured;
  status.loginConfigured = !!health.linuxdo_oauth_configured;
  status.workspaceName = health.workspace || '';
  status.workspaceId = health.workspace_id || '';
  status.apiKeyConfigured = !!health.api_key_configured;
  status.ready = !!health.ready;
  status.missing = health.missing || [];
  status.weak = health.weak || [];
  status.proxyConfigured = !!health.proxy_configured;
  status.autoKick = !!health.auto_kick;
  status.kickDelayMs = health.kick_delay_ms || 0;

  try {
    const meRes = await fetch(baseUrl + '/api/auth/me?t=' + Date.now(), {
      credentials: 'include',
      cache: 'no-store'
    });
    const me = await meRes.json();
    if (meRes.ok && me.ok) {
      status.loggedIn = !!(me.logged_in || me.authenticated);
      status.linuxDoUser = me.user || null;
      status.loginConfigured = !!me.linuxdo_oauth_configured;
      if (!status.loggedIn) status.loginError = 'auth cookie missing or not sent';
    } else {
      status.loginError = 'auth/me HTTP ' + meRes.status;
    }
  } catch (e) {
    status.loginError = e.message;
  }

  if (status.loggedIn || isStrongInviteApiKey(cfg.inviteApiKey)) {
    try {
      const headers = {};
      if (!status.loggedIn && isStrongInviteApiKey(cfg.inviteApiKey)) headers['X-Api-Key'] = cfg.inviteApiKey;
      const res = await fetch(baseUrl + '/api/status?t=' + Date.now(), {
        credentials: 'include',
        headers,
        cache: 'no-store'
      });
      const data = await res.json();
      if (res.ok && data.ok && data.config) {
        status.authConfigured = !!data.config.auth_configured;
        status.workspaceName = data.config.workspace_name || status.workspaceName;
        status.workspaceId = data.config.workspace_id || status.workspaceId;
        status.apiKeyConfigured = !!data.config.api_key_configured;
        status.ready = !!data.config.ready;
        status.missing = data.config.missing || [];
        status.weak = data.config.weak || [];
        status.proxyConfigured = !!data.config.proxy_configured;
        status.autoKick = !!data.config.auto_kick;
        status.kickDelayMs = data.config.kick_delay_ms || 0;
        status.activeInvites = data.active_invites || [];
        status.optional = data.config.optional || {};
      }
    } catch (e) {
      status.statusError = e.message;
    }
  }

  return status;
}

const tabIdToSessionId = new Map();

async function hasLinuxDoSession(baseUrl) {
  try {
    const res = await fetch(baseUrl + '/api/auth/me?t=' + Date.now(), {
      credentials: 'include',
      cache: 'no-store'
    });
    const data = await res.json().catch(() => ({}));
    return !!(res.ok && data.ok && (data.logged_in || data.authenticated));
  } catch {
    return false;
  }
}

async function inviteServerCall(path, body) {
  const cfg = await getInviteConfig();
  const baseUrl = normalizeInviteServerUrl(cfg.inviteServerUrl);
  const url = baseUrl + path;
  const headers = { 'Content-Type': 'application/json' };
  const loggedIn = await hasLinuxDoSession(baseUrl);
  if (!loggedIn && isStrongInviteApiKey(cfg.inviteApiKey)) headers['X-Api-Key'] = cfg.inviteApiKey;
  const options = {
    method: body ? 'POST' : 'GET',
    credentials: 'include',
    headers
  };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(url, options);
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; }
  catch { throw new Error('Server response is not JSON (' + res.status + ')'); }
  if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}

async function buildAuthURL(forceNew = false) {
  const existing = await chrome.storage.session.get(['pkce_verifier','pkce_state','pkce_ch','pkce_ts']);
  const age = Date.now() - (existing.pkce_ts || 0);
  const FIVE_MIN = 5 * 60 * 1000;

  let verifier, ch, state;

  if (!forceNew && existing.pkce_verifier && existing.pkce_ch && age < FIVE_MIN) {
    verifier = existing.pkce_verifier;
    ch       = existing.pkce_ch;
    state    = existing.pkce_state;
  } else {
    verifier = await newVerifier();
    ch       = await mkChallenge(verifier);
    state    = newState();
    await chrome.storage.session.set({
      pkce_verifier : verifier,
      pkce_ch       : ch,
      pkce_state    : state,
      pkce_ts       : Date.now()
    });
  }

  const p = new URLSearchParams({
    response_type              : 'code',
    client_id                  : CLIENT_ID,
    redirect_uri               : REDIRECT_URI,
    scope                      : SCOPE,
    code_challenge             : ch,
    code_challenge_method      : 'S256',
    state,
    id_token_add_organizations : 'true',
    codex_cli_simplified_flow  : 'true',
    originator                 : 'codex_cli_rs'
  });
  return AUTH_BASE + '?' + p;
}

let tokens = [];

async function loadTokens() {
  const r = await chrome.storage.local.get('tokens');
  tokens = r.tokens || [];
  setBadge(tokens.length);
}

async function storeToken(data, source) {
  const key = (data.access_token||'').slice(-30);
  if (key && tokens.some(t => t.access_token.slice(-30) === key)) return null;

  const entry = {
    id           : Date.now(),
    capturedAt   : new Date().toISOString(),
    source,
    access_token : data.access_token  || '',
    refresh_token: data.refresh_token || '',
    id_token     : data.id_token      || '',
    token_type   : data.token_type    || 'bearer',
    scope        : data.scope         || '',
    expires_in   : data.expires_in    || 0
  };
  tokens.unshift(entry);
  if (tokens.length > 20) tokens = tokens.slice(0,20);
  await chrome.storage.local.set({ tokens });
  setBadge(tokens.length);
  return entry;
}

function setBadge(n) {
  chrome.action.setBadgeText({ text: n > 0 ? String(n) : '' });
  chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
}

async function exchangeToken(code, verifier) {
  const res = await fetch(TOKEN_URL, {
    method : 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept'      : 'application/json',
      'User-Agent'  : 'OpenAI-Codex-CLI/1.0'
    },
    body: new URLSearchParams({
      grant_type    : 'authorization_code',
      client_id     : CLIENT_ID,
      code,
      redirect_uri  : REDIRECT_URI,
      code_verifier : verifier
    }).toString()
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); }
  catch { throw new Error('Parse failed (' + res.status + '): ' + text.slice(0,150)); }
  if (!res.ok) throw new Error('HTTP ' + res.status + ': ' + (data.error_description||data.error||text.slice(0,100)));
  if (!data.access_token) throw new Error('No access_token in response');
  return data;
}

const handledCodes = new Set();

async function handleCallbackURL(url) {
  let u; try { u = new URL(url); } catch { return; }
  if (!['localhost','127.0.0.1'].includes(u.hostname)) return;
  if (u.port !== '1455') return;
  if (!u.pathname.startsWith('/auth/callback')) return;

  const code = u.searchParams.get('code');
  if (!code) return;
  if (handledCodes.has(code.slice(0,30))) return;
  handledCodes.add(code.slice(0,30));
  setTimeout(() => handledCodes.delete(code.slice(0,30)), 120000);

  await doExchange(code);
}

async function doExchange(code) {
  const inviteSess = await chrome.storage.session.get('inviteSessionId');
  if (inviteSess.inviteSessionId) {
    try {
      const result = await inviteServerCall('/api/invite-session/' + inviteSess.inviteSessionId + '/event',
        { type: 'code_captured', code });

      if (result.token && result.token.access_token) {
        await storeToken(result.token, 'invite_callback');
        notify('Token obtained!', 'Click extension icon to view and export');
      }

      await chrome.storage.session.remove('inviteSessionId');
      tabIdToSessionId.clear();
      return;
    } catch (err) {
      console.error('[Invite] Server code exchange failed:', err.message);
      notify('Exchange failed', err.message.slice(0,100));
      return;
    }
  }

  const sess = await chrome.storage.session.get(['pkce_verifier','pkce_state']);
  if (!sess.pkce_verifier) {
    await chrome.storage.local.set({ pendingCode: code });
    return;
  }
  try {
    const data = await exchangeToken(code, sess.pkce_verifier);
    await storeToken(data, 'auto_callback');
    await chrome.storage.session.remove(['pkce_verifier','pkce_state','pkce_ts']);
    await chrome.storage.local.remove(['pendingCode','pendingVerifier']);
    notify('Token obtained!', 'Click extension icon to view and export');
  } catch (err) {
    await chrome.storage.local.set({ pendingCode: code, pendingVerifier: sess.pkce_verifier });
    notify('Exchange failed', err.message.slice(0,100));
  }
}

chrome.webNavigation.onBeforeNavigate.addListener(
  d => { if (d.frameId===0) handleCallbackURL(d.url); }
);
chrome.tabs.onUpdated.addListener((id, info) => {
  if (info.url) handleCallbackURL(info.url);
});

function notify(title, message) {
  chrome.notifications.create('oai'+Date.now(), {
    type:'basic', iconUrl:'icons/icon48.png', title, message
  });
}

chrome.runtime.onMessage.addListener((msg, sender, send) => {
  run(msg, sender).then(send).catch(e => send({ ok:false, error:e.message }));
  return true;
});

async function run(msg, sender) {
  switch (msg.type) {

    case 'START_AUTH': {
      const url = await buildAuthURL(msg.forceNew || false);
      await chrome.tabs.create({ url });
      return { ok: true, url };
    }

    case 'GET_AUTH_URL': {
      const url = await buildAuthURL(msg.forceNew || false);
      return { ok: true, url };
    }

    case 'TOKEN_FROM_PAGE': {
      if (!msg.data || !msg.data.access_token) return { ok:false };
      const entry = await storeToken(msg.data, 'page_capture');

      const sess = await chrome.storage.session.get('inviteSessionId');
      if (sess.inviteSessionId) {
        try {
          await inviteServerCall('/api/invite-session/' + sess.inviteSessionId + '/event',
            { type: 'token_captured', data: msg.data });
        } catch (e) { console.error('[Invite] token_captured event failed:', e.message); }
        await chrome.storage.session.remove('inviteSessionId');
        tabIdToSessionId.clear();
      }

      return { ok: !!entry };
    }

    case 'CALLBACK_CODE': {
      if (!msg.code) return { ok:false };
      if (handledCodes.has(msg.code.slice(0,30))) return { ok:true };
      handledCodes.add(msg.code.slice(0,30));
      setTimeout(() => handledCodes.delete(msg.code.slice(0,30)), 120000);
      await doExchange(msg.code);
      return { ok:true };
    }

    case 'GET_TOKENS': {
      const r = await chrome.storage.local.get(['tokens','pendingCode','pendingVerifier']);
      return { ok:true, tokens:r.tokens||[], pendingCode:r.pendingCode||'', pendingVerifier:r.pendingVerifier||'' };
    }

    case 'MANUAL_EXCHANGE': {
      if (!msg.code || !msg.verifier) throw new Error('code and verifier are required');
      const data = await exchangeToken(msg.code, msg.verifier);
      await storeToken(data, 'manual');
      await chrome.storage.local.remove(['pendingCode','pendingVerifier']);
      return { ok:true };
    }

    case 'CLEAR_TOKENS': {
      tokens = [];
      await chrome.storage.local.set({ tokens:[] });
      setBadge(0);
      return { ok:true };
    }

    case 'CLEAR_PENDING':
      await chrome.storage.local.remove(['pendingCode','pendingVerifier']);
      return { ok:true };

    case 'OPEN_URL': {
      if (!msg.url) throw new Error('No URL');
      await chrome.tabs.create({ url: msg.url });
      return { ok: true };
    }

    case 'GET_VERIFIER': {
      const s = await chrome.storage.session.get('pkce_verifier');
      return { ok: true, verifier: s.pkce_verifier || '' };
    }

    case 'LINUXDO_LOGIN': {
      const cfg = await getInviteConfig();
      const loginUrl = normalizeInviteServerUrl(cfg.inviteServerUrl) + '/api/auth/login';
      await chrome.tabs.create({ url: loginUrl });
      return { ok: true, url: loginUrl };
    }

    case 'LINUXDO_LOGOUT': {
      const cfg = await getInviteConfig();
      const res = await fetch(normalizeInviteServerUrl(cfg.inviteServerUrl) + '/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
      return { ok: true };
    }

    case 'INVITE_CONFIG_SAVE': {
      const config = {
        inviteServerUrl: normalizeInviteServerUrl(msg.config && msg.config.inviteServerUrl),
        inviteApiKey: String((msg.config && msg.config.inviteApiKey) || '').trim()
      };
      await chrome.storage.local.set(config);
      return { ok: true };
    }

    case 'INVITE_GET_CONFIG': {
      const cfg = await getInviteConfig();
      let status = null;
      try {
        status = await getInviteServerStatus(cfg);
      } catch(e) {
        status = { serverOnline: false, error: e.message };
      }
      return { ok: true, config: cfg, ...status };
    }

    case 'INVITE_START_AUTH': {
      const cfg = await getInviteConfig();
      const status = await getInviteServerStatus(cfg);
      if (!status.serverOnline) throw new Error('Invite server is offline');
      if (!status.loggedIn && !isStrongInviteApiKey(cfg.inviteApiKey)) {
        throw new Error('Please login with Linux.do first');
      }
      if (!status.ready) {
        throw new Error('Invite server config incomplete: ' + [...status.missing, ...status.weak].join(', '));
      }

      const sessionResp = await inviteServerCall('/api/invite-session/start', {});
      const sessionId = sessionResp.session_id;
      const oauthUrl = sessionResp.oauth_url;

      await chrome.storage.session.set({ inviteSessionId: sessionId });

      const tab = await chrome.tabs.create({ url: oauthUrl });
      tabIdToSessionId.set(tab.id, sessionId);

      return { ok: true, url: oauthUrl, session_id: sessionId, inviteMode: true };
    }

    case 'EMAIL_DETECTED': {
      const tabId = (sender && sender.tab) ? sender.tab.id : null;
      const stored = await chrome.storage.session.get('inviteSessionId');
      const sessionId = (tabId && tabIdToSessionId.get(tabId)) || stored.inviteSessionId;
      if (sessionId && msg.email) {
        try {
          await inviteServerCall('/api/invite-session/' + sessionId + '/event',
            { type: 'email_detected', email: msg.email });
        } catch (e) { console.error('[Invite] email_detected event failed:', e.message); }
      }
      return { ok: true };
    }

    case 'PHONE_OTP_DETECTED': {
      const email = msg.email;
      if (!email) return { ok: false, error: 'No email provided' };

      const tabId = (sender && sender.tab) ? sender.tab.id : null;
      const stored = await chrome.storage.session.get('inviteSessionId');
      const sessionId = (tabId && tabIdToSessionId.get(tabId)) || stored.inviteSessionId;

      if (!sessionId) {
        return { ok: false, error: 'No active invite session' };
      }

      try {
        const result = await inviteServerCall('/api/invite-session/' + sessionId + '/event',
          { type: 'phone_otp', email });

        if (result.action === 'redirect' && result.url) {
          if (tabId) {
            await chrome.tabs.update(tabId, { url: result.url });
          } else {
            const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
            if (tabs[0]) await chrome.tabs.update(tabs[0].id, { url: result.url });
          }
        }

        return { ok: true, action: result.action };
      } catch (e) {
        console.error('[Invite] phone_otp event failed:', e.message);
        return { ok: false, error: e.message };
      }
    }

    case 'CODEX_CLOUD_DETECTED': {
      const tabId = (sender && sender.tab) ? sender.tab.id : null;
      const stored = await chrome.storage.session.get('inviteSessionId');
      const sessionId = (tabId && tabIdToSessionId.get(tabId)) || stored.inviteSessionId;

      if (!sessionId) {
        return { ok: false, error: 'No active invite session' };
      }

      try {
        const result = await inviteServerCall('/api/invite-session/' + sessionId + '/event',
          { type: 'codex_cloud' });

        if (result.action === 'redirect' && result.url) {
          if (tabId) {
            await chrome.tabs.update(tabId, { url: result.url });
          }
        }

        return { ok: true, action: result.action };
      } catch (e) {
        console.error('[Invite] codex_cloud event failed:', e.message);
        return { ok: false, error: e.message };
      }
    }

    case 'INVITE_CANCEL': {
      const stored = await chrome.storage.session.get('inviteSessionId');
      if (stored.inviteSessionId) {
        try {
          await inviteServerCall('/api/invite-session/' + stored.inviteSessionId + '/event',
            { type: 'cancelled' });
        } catch (e) {}
      }
      await chrome.storage.session.remove('inviteSessionId');
      tabIdToSessionId.clear();
      return { ok: true };
    }

    default: throw new Error('Unknown: '+msg.type);
  }
}

chrome.runtime.onInstalled.addListener(loadTokens);
chrome.runtime.onStartup.addListener(loadTokens);
loadTokens();
