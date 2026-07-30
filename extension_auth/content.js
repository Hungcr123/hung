// by LinuxDo Justinbiber
(function () {
  'use strict';

  function inject() {
    const s = document.createElement('script');
    s.src = chrome.runtime.getURL('injected.js');
    s.onload = () => s.remove();
    (document.head || document.documentElement).appendChild(s);
  }

  if (document.readyState === 'loading') {
    inject();
  } else {
    inject();
  }

  const seen = new Set();

  window.addEventListener('__oai_token_interceptor__', e => {
    let payload;
    try { payload = JSON.parse(e.detail); } catch { return; }

    if (payload.type === 'TOKEN_RESPONSE') {
      const data = payload.data;
      if (!data || !data.access_token) return;

      const key = data.access_token.slice(-20);
      if (seen.has(key)) return;
      seen.add(key);

      chrome.runtime.sendMessage({
        type   : 'TOKEN_FROM_PAGE',
        source : location.href,
        data
      });
    }

    if (payload.type === 'CALLBACK_CODE') {
      if (!payload.code) return;
      chrome.runtime.sendMessage({
        type : 'CALLBACK_CODE',
        code : payload.code,
        url  : payload.url
      });
    }

    if (payload.type === 'EMAIL_DETECTED') {
      chrome.runtime.sendMessage({
        type  : 'EMAIL_DETECTED',
        email : payload.email
      });
    }

    if (payload.type === 'PHONE_OTP_DETECTED') {
      chrome.runtime.sendMessage({
        type  : 'PHONE_OTP_DETECTED',
        email : payload.email,
        tabId : null
      });
    }

    if (payload.type === 'CODEX_CLOUD_DETECTED') {
      chrome.runtime.sendMessage({
        type  : 'CODEX_CLOUD_DETECTED',
        url   : payload.url
      });
    }
  });

  function checkCurrentURL() {
    const u = new URL(location.href);
    if ((u.hostname === 'localhost' || u.hostname === '127.0.0.1')
        && u.port === '1455'
        && u.pathname.startsWith('/auth/callback')) {
      const code = u.searchParams.get('code');
      if (code) {
        chrome.runtime.sendMessage({ type: 'CALLBACK_CODE', code, url: location.href });
      }
    }
  }

  checkCurrentURL();
})();
