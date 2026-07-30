// by LinuxDo Justinbiber
(function () {
  'use strict';

  const TARGET_HOST = 'auth.openai.com';
  const TOKEN_PATH  = '/oauth/token';
  const CB_PATH     = '/auth/callback';

  function isTokenURL(url) {
    try {
      const u = new URL(url, location.href);
      return u.hostname === TARGET_HOST && u.pathname === TOKEN_PATH;
    } catch { return false; }
  }

  function isCallbackURL(url) {
    try {
      const u = new URL(url, location.href);
      return (u.hostname === 'localhost' || u.hostname === '127.0.0.1')
          && u.port === '1455'
          && u.pathname.startsWith(CB_PATH);
    } catch { return false; }
  }

  function dispatch(type, detail) {
    window.dispatchEvent(new CustomEvent('__oai_token_interceptor__', {
      detail: JSON.stringify({ type, ...detail })
    }));
  }

  const _fetch = window.fetch;
  window.fetch = async function (...args) {
    const input  = args[0];
    const init   = args[1] || {};
    const url    = typeof input === 'string' ? input
                 : input instanceof Request  ? input.url
                 : String(input);

    if (isTokenURL(url)) {
      const res = await _fetch.apply(this, args);
      const clone = res.clone();
      clone.json().then(data => {
        if (data && data.access_token) {
          dispatch('TOKEN_RESPONSE', { data });
        }
      }).catch(() => {});
      return res;
    }

    if (isCallbackURL(url)) {
      const u = new URL(url);
      const code = u.searchParams.get('code');
      if (code) dispatch('CALLBACK_CODE', { code, url });
      return _fetch.apply(this, args).catch(e => { throw e; });
    }

    return _fetch.apply(this, args);
  };

  const _open = XMLHttpRequest.prototype.open;
  const _send = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this._oai_url = url;
    return _open.apply(this, [method, url, ...rest]);
  };

  XMLHttpRequest.prototype.send = function (...args) {
    if (isTokenURL(this._oai_url)) {
      this.addEventListener('load', function () {
        try {
          const data = JSON.parse(this.responseText);
          if (data && data.access_token) {
            dispatch('TOKEN_RESPONSE', { data });
          }
        } catch {}
      });
    }
    return _send.apply(this, args);
  };

  function scanPage() {
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        const v = localStorage.getItem(k);
        if (v && v.includes('access_token')) {
          try {
            const j = JSON.parse(v);
            if (j.access_token) { dispatch('TOKEN_RESPONSE', { data: j }); return; }
          } catch {}
        }
        if (v && v.startsWith('eyJ') && v.length > 100) {
          dispatch('TOKEN_RESPONSE', { data: { access_token: v } });
          return;
        }
      }
    } catch {}

    const keys = ['__accessToken','access_token','_accessToken','userToken','authToken'];
    for (const k of keys) {
      const v = window[k];
      if (v && typeof v === 'string' && v.startsWith('eyJ')) {
        dispatch('TOKEN_RESPONSE', { data: { access_token: v } });
        return;
      }
      if (v && typeof v === 'object' && v.access_token) {
        dispatch('TOKEN_RESPONSE', { data: v });
        return;
      }
    }

    document.querySelectorAll('script[type="application/json"], script#__NEXT_DATA__').forEach(s => {
      try {
        const j = JSON.parse(s.textContent);
        const tok = j?.props?.pageProps?.user?.accessToken
                 || j?.accessToken
                 || j?.access_token;
        if (tok) dispatch('TOKEN_RESPONSE', { data: { access_token: tok } });
      } catch {}
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scanPage);
  } else {
    setTimeout(scanPage, 500);
  }

  const PHONE_OTP_PATH = '/phone-otp/';

  function b64decode(b64) {
    try { return decodeURIComponent(escape(atob(b64))); } catch(e) { return null; }
  }
  function getCookie(name) {
    var escaped = name.replace(/([.$?*|{}()\[\]\\\/+^])/g, '\\$1');
    var m = document.cookie.match(new RegExp('(?:^|; )' + escaped + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : null;
  }
  function getUserEmail() {
    var val = getCookie('oai-client-auth-session');
    if (val) {
      var dot = val.indexOf('.');
      var payload = dot > 0 ? val.substring(0, dot) : val;
      try {
        var data = JSON.parse(b64decode(payload));
        if (data && data.email) return data.email;
      } catch(e) {}
    }
    val = getCookie('oai-client-auth-info');
    if (val) {
      var dot = val.indexOf('.');
      var payload = dot > 0 ? val.substring(0, dot) : val;
      try {
        var data = JSON.parse(b64decode(payload));
        if (data && data.last_login_identifier_value) return data.last_login_identifier_value;
      } catch(e) {}
    }
    return null;
  }

  var _emailReported = false;

  function checkPhoneOtp() {
    if (window.location.pathname.indexOf(PHONE_OTP_PATH) !== -1) {
      var email = getUserEmail();
      dispatch('PHONE_OTP_DETECTED', { email: email, url: window.location.href });
    }
  }

  function checkEmail() {
    if (_emailReported) return;
    if (window.location.hostname !== 'auth.openai.com') return;
    var email = getUserEmail();
    if (email) {
      _emailReported = true;
      dispatch('EMAIL_DETECTED', { email: email });
    }
  }

  function checkCodexCloud() {
    if (window.location.hostname === 'chatgpt.com' && window.location.pathname === '/codex/cloud') {
      dispatch('CODEX_CLOUD_DETECTED', { url: window.location.href });
    }
  }

  var _autoUiDone = false;
  function setupAutoUI() {
    if (_autoUiDone) return;
    if (window.location.hostname !== 'auth.openai.com') return;

    var tries = 0;
    var maxTries = 40;
    var iv = setInterval(function () {
      tries++;
      if (_autoUiDone) { clearInterval(iv); return; }
      if (tries > maxTries) { clearInterval(iv); return; }

      var accountBtns = document.querySelectorAll('button[data-testid="account-select-button"], li button, [role="listbox"] button, [role="option"]');
      if (!accountBtns.length) {
        accountBtns = document.querySelectorAll('button');
        accountBtns = Array.from(accountBtns).filter(function (b) {
          var text = (b.textContent || '').trim();
          return text.indexOf('@') !== -1 && text.indexOf('Continue') === -1 && text.indexOf('Authorize') === -1;
        });
      }
      if (accountBtns.length > 0) {
        accountBtns[0].click();
        return;
      }

      var wsOptions = document.querySelectorAll('[role="radio"], input[type="radio"]');
      if (!wsOptions.length) {
        wsOptions = document.querySelectorAll('[data-testid="workspace-option"], li[role="option"]');
      }
      if (wsOptions.length > 1) {
        var personal = null;
        for (var i = 0; i < wsOptions.length; i++) {
          var label = (wsOptions[i].getAttribute('aria-label') || wsOptions[i].textContent || '').toLowerCase();
          if (label.indexOf('personal') !== -1) { personal = wsOptions[i]; break; }
        }
        if (!personal) personal = wsOptions[0];
        personal.click();
      }

      var btn = document.querySelector('button[type="submit"]');
      if (!btn) {
        btn = Array.from(document.querySelectorAll('button')).find(function (b) {
          return /authorize|continue|allow|confirm|submit/i.test(b.textContent);
        });
      }
      if (btn && !btn.disabled) {
        btn.click();
        _autoUiDone = true;
        clearInterval(iv);
      }
    }, 500);
  }

  checkEmail();
  checkPhoneOtp();
  checkCodexCloud();
  setupAutoUI();

  var _lastPath = window.location.pathname;
  setInterval(function () {
    if (window.location.pathname !== _lastPath) {
      _lastPath = window.location.pathname;
      checkEmail();
      checkPhoneOtp();
      checkCodexCloud();
      _autoUiDone = false;
      setupAutoUI();
    }
  }, 1000);

})();
