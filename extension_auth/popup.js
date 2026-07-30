document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const id = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + id).classList.add('active');
  });
});

function setStep(n) {
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById('step' + i);
    el.classList.remove('active', 'done');
    if (i < n)  el.classList.add('done');
    if (i === n) el.classList.add('active');
  }
}
setStep(0);

const btnStartAuth  = document.getElementById('btnStartAuth');
const authBtnIcon   = document.getElementById('authBtnIcon');
const authBtnText   = document.getElementById('authBtnText');
const statusTxt     = document.getElementById('statusTxt');
const urlBox        = document.getElementById('urlBox');
const urlField      = document.getElementById('urlField');
const urlStatus     = document.getElementById('urlStatus');
const waitingHint   = document.getElementById('waitingHint');

async function initAuthURL() {
  chrome.runtime.sendMessage({ type: 'GET_AUTH_URL' }, resp => {
    if (resp && resp.ok && resp.url) {
      showURL(resp.url, false);
      setStep(1);
    }
  });
}

function showURL(url, opened) {
  urlField.value = url;
  urlBox.classList.add('show');
  urlStatus.textContent = opened ? '（已打开，等待授权完成）' : '（已生成，点下方按钮打开）';
  chrome.runtime.sendMessage({ type: 'GET_VERIFIER' }, resp => {
    if (resp && resp.verifier) {
      document.getElementById('inVerifier').value = resp.verifier;
    }
  });
}

btnStartAuth.addEventListener('click', () => {
  btnStartAuth.disabled = true;
  authBtnIcon.textContent = '...';
  authBtnText.textContent = '生成中...';

  chrome.runtime.sendMessage({ type: 'START_AUTH' }, resp => {
    btnStartAuth.disabled = false;
    authBtnIcon.textContent = '[OK]';
    authBtnText.textContent = '已打开授权页，等待登录完成';

    if (resp && resp.ok) {
      showURL(resp.url, true);
      setStep(2);
      waitingHint.classList.add('show');
      statusTxt.textContent = '等待回调';
      startPolling();
    } else {
      authBtnIcon.textContent = '[X]';
      authBtnText.textContent = '发起失败，点击重试';
      showToast('[X] ' + (resp?.error || '失败'));
    }
  });
});

document.getElementById('btnOpenURL').addEventListener('click', () => {
  const url = urlField.value;
  if (!url) return;
  chrome.runtime.sendMessage({ type: 'OPEN_URL', url }, () => {
    setStep(2);
    waitingHint.classList.add('show');
    urlStatus.textContent = '（已打开，等待授权完成）';
    statusTxt.textContent = '等待回调';
    startPolling();
  });
});

document.getElementById('btnCopyURL').addEventListener('click', () => {
  navigator.clipboard.writeText(urlField.value).then(() => showToast('授权 URL 已复制'));
});

document.getElementById('btnRegen').addEventListener('click', () => {
  if (!confirm('重新生成将使当前授权 URL 失效，确定吗？')) return;
  chrome.runtime.sendMessage({ type: 'GET_AUTH_URL', forceNew: true }, resp => {
    if (resp && resp.ok) {
      showURL(resp.url, false);
      setStep(1);
      waitingHint.classList.remove('show');
      statusTxt.textContent = '就绪';
      showToast('已重新生成新的授权 URL');
    }
  });
});

let pollTimer = null;
let prevCount = 0;

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  setStep(3);
  let polls = 0;
  pollTimer = setInterval(() => {
    polls++;
    loadTokens(delta => {
      if (delta > 0) {
        clearInterval(pollTimer);
        pollTimer = null;
        setStep(4);
        authBtnIcon.textContent = '[OK]';
        authBtnText.textContent = 'Token 已获取！点击可再次发起';
        waitingHint.classList.remove('show');
        statusTxt.textContent = '已完成';
        showToast('Token 获取成功！');
      }
    });
    if (polls > 180) {
      clearInterval(pollTimer);
      pollTimer = null;
      waitingHint.classList.remove('show');
      authBtnText.textContent = '等待超时，点击重新发起';
      authBtnIcon.textContent = '[!]';
      statusTxt.textContent = '超时';
      showToast('超时，请重新发起');
    }
  }, 1000);
}

let allTokens = [];

function loadTokens(onNew) {
  chrome.runtime.sendMessage({ type: 'GET_TOKENS' }, resp => {
    if (!resp) return;
    allTokens = resp.tokens || [];
    const n = allTokens.length;
    document.getElementById('tokenCount').textContent = n;
    renderTokenList(allTokens);

    const pb = document.getElementById('pendingBox');
    const pv = document.getElementById('pendingVal');
    if (resp.pendingCode) {
      pb.style.display = 'block';
      pv.textContent = resp.pendingCode;
      const ic = document.getElementById('inCode');
      if (!ic.value) ic.value = resp.pendingCode;
      if (resp.pendingVerifier) {
        const iv = document.getElementById('inVerifier');
        if (!iv.value) iv.value = resp.pendingVerifier;
      }
    } else {
      pb.style.display = 'none';
    }

    if (onNew && n > prevCount) onNew(n - prevCount);
    prevCount = n;
  });
}

window.copyPending = function() {
  navigator.clipboard.writeText(document.getElementById('pendingVal').textContent)
    .then(() => showToast('已复制授权码'));
};

function renderTokenList(tokens) {
  const list = document.getElementById('tokenList');
  if (!tokens.length) {
    list.innerHTML = '<div class="empty">' +
      '<div class="ei">[ ]</div>' +
      '<div class="et">暂无已保存的 Token<br><small>点击上方「生成授权 URL 并打开」开始</small></div>' +
      '</div>';
    return;
  }
  list.innerHTML = tokens.map((t, i) => {
    const scopes = (t.scope||'').split(' ').filter(Boolean);
    const h = t.expires_in ? Math.round(t.expires_in/3600) : '?';
    const ts = t.capturedAt ? new Date(t.capturedAt).toLocaleString('zh-CN') : '-';
    const src = {auto_callback:'自动拦截', manual:'手动换取', page_capture:'页面捕获', invite_callback:'邀请回调'}[t.source] || t.source;
    return '<div class="tcard">' +
      '<div class="thead" onclick="tog(this)">' +
        '<div class="tnum">' + (i+1) + '</div>' +
        '<div class="tmeta">' +
          '<div class="ttime">' + ts + '</div>' +
          '<div class="tsrc">' + src + ' / 有效 ' + h + 'h</div>' +
        '</div>' +
        '<div class="tact">' +
          '<button class="bi" onclick="event.stopPropagation();exOne(' + t.id + ')" title="导出">[E]</button>' +
          '<button class="bi" onclick="event.stopPropagation();cpOne(' + t.id + ')" title="复制">[C]</button>' +
        '</div>' +
      '</div>' +
      '<div class="tfields">' +
        rf('access_token',t.access_token,'ACCESS TOKEN','tg') +
        (t.refresh_token?rf('refresh_token',t.refresh_token,'REFRESH TOKEN','tb'):'') +
        (t.id_token?rf('id_token',t.id_token,'ID TOKEN','ta'):'') +
        (scopes.length?'<div class="frow"><div class="flbl">Scope</div>' +
          '<div class="spills">' + scopes.map(s=>'<span class="sp">' + s + '</span>').join('') + '</div></div>':'') +
      '</div>' +
    '</div>';
  }).join('');
}

function rf(key, val, label, cls) {
  if (!val) return '';
  const long = val.length > 60;
  return '<div class="frow">' +
    '<div class="flbl">' + label + ' <span class="tag ' + cls + '">' + key + '</span>' +
    (long?'<span class="etg" onclick="exv(this)">展开</span>':'') +
    '</div>' +
    '<div class="fval" data-f="' + enc(val) + '" onclick="cpv(this)">' + esc(val) + '</div>' +
  '</div>';
}

function enc(s){ return encodeURIComponent(s); }
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

window.tog = h => {
  const f = h.nextElementSibling;
  f.style.display = f.style.display === 'none' ? '' : 'none';
};
window.exv = btn => {
  const fv = btn.closest('.frow').querySelector('.fval');
  btn.textContent = fv.classList.toggle('ex') ? '收起' : '展开';
};
window.cpv = el => {
  navigator.clipboard.writeText(decodeURIComponent(el.dataset.f || el.textContent)).then(() => {
    el.classList.add('cp'); setTimeout(()=>el.classList.remove('cp'),1500);
    showToast('已复制');
  });
};

function fmt(t, i) {
  const ts = t.capturedAt ? new Date(t.capturedAt).toLocaleString('zh-CN') : '-';
  const h  = t.expires_in ? Math.round(t.expires_in/3600) : '?';
  return ['='.repeat(64),
    '# Token #' + (i+1) + '  ' + ts + '  有效期 ' + h + 'h  来源:' + (t.source||'?'),
    '='.repeat(64),'',
    '[access_token]',  t.access_token  ||'(空)','',
    '[refresh_token]', t.refresh_token ||'(空)','',
    '[id_token]',      t.id_token      ||'(空)','',
    '[token_type]',    t.token_type    ||'bearer','',
    '[scope]',         t.scope         ||'','',
    '='.repeat(64),''
  ].join('\n');
}

function dl(content, name, mime) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([content],{type:mime}));
  a.download = name; a.click();
}

document.getElementById('btnExportAll').addEventListener('click', () => {
  if (!allTokens.length) { showToast('暂无 Token'); return; }
  dl(allTokens.map(fmt).join('\n'), 'openai_tokens_' + Date.now() + '.txt', 'text/plain');
  showToast('已导出 ' + allTokens.length + ' 个 Token');
});
document.getElementById('btnExportJSON').addEventListener('click', () => {
  if (!allTokens.length) { showToast('暂无 Token'); return; }
  dl(JSON.stringify(allTokens,null,2), 'openai_tokens_' + Date.now() + '.json', 'application/json');
  showToast('已导出 JSON');
});
window.exOne = id => {
  const t = allTokens.find(x=>x.id===id); if(!t) return;
  dl(fmt(t,allTokens.indexOf(t)), 'token_' + id + '.txt', 'text/plain');
  showToast('已导出');
};
window.cpOne = id => {
  const t = allTokens.find(x=>x.id===id); if(!t) return;
  navigator.clipboard.writeText(fmt(t,allTokens.indexOf(t))).then(()=>showToast('已复制'));
};

document.getElementById('btnClear').addEventListener('click', () => {
  if (!confirm('确认清除所有 Token 记录？')) return;
  chrome.runtime.sendMessage({type:'CLEAR_TOKENS'}, () => {
    allTokens=[]; prevCount=0;
    renderTokenList([]);
    document.getElementById('tokenCount').textContent='0';
    setStep(0);
    statusTxt.textContent='就绪';
    showToast('已清除');
  });
});

document.getElementById('btnManual').addEventListener('click', () => {
  const code     = document.getElementById('inCode').value.trim();
  const verifier = document.getElementById('inVerifier').value.trim();
  const clientId = document.getElementById('inClientId').value.trim();
  const redirect = document.getElementById('inRedirect').value.trim();
  if (!code)     { showToast('请填写 Authorization Code'); return; }
  if (!verifier) { showToast('请填写 Code Verifier'); return; }
  const btn = document.getElementById('btnManual');
  btn.textContent='换取中...'; btn.disabled=true;
  chrome.runtime.sendMessage({type:'MANUAL_EXCHANGE',code,verifier,clientId,redirectUri:redirect}, resp => {
    btn.textContent='手动换取 Token'; btn.disabled=false;
    if (resp?.ok) {
      showToast('成功！');
      document.querySelector('[data-tab="tokens"]').click();
      chrome.runtime.sendMessage({type:'CLEAR_PENDING'});
      loadTokens();
    } else {
      showToast('[X] ' + (resp?.error||'失败').slice(0,60));
    }
  });
});

function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent=msg; el.classList.add('show');
  setTimeout(()=>el.classList.remove('show'),2500);
}

var invServerUrl     = document.getElementById('invServerUrl');
var invApiKey        = document.getElementById('invApiKey');
var invServerStatus  = document.getElementById('invServerStatus');
var linuxDoStatus    = document.getElementById('linuxDoStatus');
var invActiveStatus  = document.getElementById('invActiveStatus');
var btnInviteStart   = document.getElementById('btnInviteStart');
var btnInviteSaveCfg = document.getElementById('btnInviteSaveCfg');
var btnInviteTestConn = document.getElementById('btnInviteTestConn');
var btnInviteCancel  = document.getElementById('btnInviteCancel');
var btnLinuxDoLogin  = document.getElementById('btnLinuxDoLogin');
var btnLinuxDoLogout = document.getElementById('btnLinuxDoLogout');
var _inviteConfigLoaded = false;

function serverOriginFromInput(value) {
  try {
    var raw = String(value || '').trim();
    var withScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw) ? raw : 'http://' + raw;
    return new URL(withScheme).origin;
  } catch (e) {
    return '';
  }
}

function ensureInviteServerPermission(serverUrl, done) {
  var origin = serverOriginFromInput(serverUrl);
  if (!origin || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) return done(true);
  if (!chrome.permissions) return done(true);

  var pattern = origin + '/*';
  chrome.permissions.contains({ origins: [pattern] }, function (hasPermission) {
    if (hasPermission) return done(true);
    chrome.permissions.request({ origins: [pattern] }, function (granted) {
      done(!!granted);
    });
  });
}

function renderInviteServerStatus(resp) {
  if (!resp.serverOnline) {
    invServerStatus.textContent = '[X] Server 离线' + (resp.error ? ' - ' + resp.error : '');
    invServerStatus.style.color = 'var(--er)';
    linuxDoStatus.textContent = 'LinuxDo登录: Server 不可用';
    linuxDoStatus.style.color = 'var(--dim)';
    return;
  }
  invServerStatus.textContent = '[OK] Server 在线' + (resp.ready ? '，就绪' : ' - 配置未完成，请检查服务端 .env');
  invServerStatus.style.color = resp.ready ? 'var(--g2)' : 'var(--g3)';

  if (!resp.loginConfigured) {
    linuxDoStatus.textContent = 'LinuxDo登录: 后端未配置 LINUXDO_CLIENT_SECRET';
    linuxDoStatus.style.color = 'var(--g3)';
    return;
  }
  if (resp.loggedIn) {
    var user = resp.linuxDoUser || {};
    linuxDoStatus.textContent = 'LinuxDo登录: 已登录 ' + (user.username || user.name || user.email || user.id || '');
    linuxDoStatus.style.color = 'var(--g2)';
  } else {
    linuxDoStatus.textContent = 'LinuxDo登录: 未登录，登录后无需 API Key';
    linuxDoStatus.style.color = 'var(--g3)';
  }
}

async function loadInviteConfig() {
  chrome.runtime.sendMessage({ type: 'INVITE_GET_CONFIG' }, function (resp) {
    if (!resp || !resp.ok) return;
    var cfg = resp.config;
    if (!_inviteConfigLoaded) {
      invServerUrl.value = cfg.inviteServerUrl || 'https://oai.yunxi668.cn';
      invApiKey.value    = cfg.inviteApiKey    || '';
      _inviteConfigLoaded = true;
    }

    renderInviteServerStatus(resp);

    chrome.storage.session.get('inviteSessionId', function (s) {
      if (s.inviteSessionId) {
        invActiveStatus.style.display = 'block';
        btnInviteCancel.style.display = 'block';
        btnInviteStart.textContent = '交换运行中，点击重新发起';
        if (!window._inviteSessionPollTimer) {
          window._inviteSessionPollTimer = setInterval(function () {
            pollInviteSession(s.inviteSessionId);
          }, 5000);
          pollInviteSession(s.inviteSessionId);
        }
      } else {
        invActiveStatus.style.display = 'none';
        btnInviteCancel.style.display = 'none';
        btnInviteStart.textContent = '启动 Token 交换';
        clearInvitePoll();
      }
    });
  });
}

btnInviteSaveCfg.addEventListener('click', function () {
  btnInviteSaveCfg.textContent = '保存中...';
  var config = {
    inviteServerUrl: invServerUrl.value.trim(),
    inviteApiKey:    invApiKey.value.trim()
  };
  ensureInviteServerPermission(config.inviteServerUrl, function (granted) {
    if (!granted) {
      showToast('[X] 未授予远程 server 访问权限');
      btnInviteSaveCfg.textContent = '保存配置';
      return;
    }
    chrome.runtime.sendMessage({ type: 'INVITE_CONFIG_SAVE', config: config }, function (resp) {
      if (resp && resp.ok) {
        showToast('配置已保存');
        loadInviteConfig();
      } else {
        showToast('[X] ' + (resp?.error || '保存失败').slice(0, 80));
      }
      btnInviteSaveCfg.textContent = '保存配置';
    });
  });
});

btnInviteTestConn.addEventListener('click', function () {
  btnInviteTestConn.textContent = '测试中...';
  chrome.runtime.sendMessage({ type: 'INVITE_GET_CONFIG' }, function (resp) {
    if (resp && resp.serverOnline) {
      showToast('Server 在线' + (resp.loggedIn ? '，LinuxDo已登录' : '，LinuxDo未登录'));
    } else {
      showToast('[X] Server 离线或无法连接');
    }
    btnInviteTestConn.textContent = '测试连接';
    loadInviteConfig();
  });
});

btnInviteStart.addEventListener('click', function () {
  btnInviteStart.disabled = true;
  btnInviteStart.textContent = '保存配置并生成中...';

  var config = {
    inviteServerUrl: invServerUrl.value.trim(),
    inviteApiKey:    invApiKey.value.trim()
  };
  ensureInviteServerPermission(config.inviteServerUrl, function (granted) {
    if (!granted) {
      btnInviteStart.disabled = false;
      btnInviteStart.textContent = '启动 Token 交换';
      showToast('[X] 未授予远程 server 访问权限');
      return;
    }
    chrome.runtime.sendMessage({ type: 'INVITE_CONFIG_SAVE', config: config }, function (saveResp) {
      if (!saveResp || !saveResp.ok) {
        btnInviteStart.disabled = false;
        btnInviteStart.textContent = '启动 Token 交换';
        showToast('[X] ' + (saveResp?.error || '保存配置失败').slice(0, 80));
        return;
      }
      chrome.runtime.sendMessage({ type: 'INVITE_START_AUTH' }, function (resp) {
      btnInviteStart.disabled = false;

      if (resp && resp.ok) {
        var inviteSessionId = resp.session_id;
        chrome.storage.session.set({ inviteSessionId: inviteSessionId });

        showURL(resp.url, true);
        setStep(2);
        waitingHint.classList.add('show');
        statusTxt.textContent = '邀请模式: 等待回调';
        urlStatus.textContent = '（邀请模式已激活，phone-otp 将自动跳转）';

        invActiveStatus.style.display = 'block';
        btnInviteCancel.style.display = 'block';
        btnInviteStart.textContent = '已发起，点击重新发起';

        showToast('邀请模式已激活');
        startPolling();

        pollInviteSession(inviteSessionId);
        window._inviteSessionPollTimer = setInterval(function () {
          pollInviteSession(inviteSessionId);
        }, 5000);
      } else {
        showToast('[X] ' + (resp?.error || '发起失败'));
        btnInviteStart.textContent = '启动 Token 交换';
        loadInviteConfig();
      }
      });
    });
  });
});

function pollInviteSession(sessionId) {
  if (!sessionId) return;
  chrome.runtime.sendMessage({ type: 'INVITE_GET_CONFIG' }, function (cfgResp) {
    if (!cfgResp || !cfgResp.ok || !cfgResp.config) return;
    var cfg = cfgResp.config;
    if (!cfg.inviteServerUrl) return;

    try {
      var baseUrl = serverOriginFromInput(cfg.inviteServerUrl);
      var headers = {};
      if (cfg.inviteApiKey) headers['X-Api-Key'] = cfg.inviteApiKey;
      fetch(baseUrl + '/api/invite-session/' + sessionId + '/status', {
        credentials: 'include',
        headers: headers,
        cache: 'no-store'
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (!data.ok) return;
        var done = data.status === 'token_exchanged' || data.status === 'kicked' || data.status === 'cancelled' || data.status === 'error';
        if (done) {
          clearInvitePoll();
          invActiveStatus.textContent = data.status === 'token_exchanged' || data.status === 'kicked'
            ? '流程已完成 - Token 已获取'
            : '流程已结束: ' + data.status;
          invActiveStatus.style.color = data.status === 'token_exchanged' || data.status === 'kicked' ? 'var(--g2)' : 'var(--g3)';
          invActiveStatus.style.display = 'block';
          btnInviteCancel.style.display = 'none';
          btnInviteStart.textContent = '启动 Token 交换';
        }
      }).catch(function () {});
    } catch (e) {}
  });
}

function saveInviteConfigBeforeAuth(done) {
  var config = {
    inviteServerUrl: invServerUrl.value.trim(),
    inviteApiKey:    invApiKey.value.trim()
  };
  ensureInviteServerPermission(config.inviteServerUrl, function (granted) {
    if (!granted) return done(new Error('未授予远程 server 访问权限'));
    chrome.runtime.sendMessage({ type: 'INVITE_CONFIG_SAVE', config: config }, function (resp) {
      if (!resp || !resp.ok) return done(new Error((resp && resp.error) || '保存配置失败'));
      done(null);
    });
  });
}

btnLinuxDoLogin.addEventListener('click', function () {
  btnLinuxDoLogin.textContent = '打开中...';
  saveInviteConfigBeforeAuth(function (err) {
    if (err) {
      btnLinuxDoLogin.textContent = 'LinuxDo登录';
      showToast('[X] ' + err.message.slice(0, 80));
      return;
    }
    chrome.runtime.sendMessage({ type: 'LINUXDO_LOGIN' }, function (resp) {
      btnLinuxDoLogin.textContent = 'LinuxDo登录';
      if (resp && resp.ok) {
        showToast('已打开 LinuxDo登录页');
        setTimeout(loadInviteConfig, 1500);
      } else {
        showToast('[X] ' + (resp?.error || '打开登录失败').slice(0, 80));
      }
    });
  });
});

btnLinuxDoLogout.addEventListener('click', function () {
  btnLinuxDoLogout.textContent = '退出中...';
  chrome.runtime.sendMessage({ type: 'LINUXDO_LOGOUT' }, function (resp) {
    btnLinuxDoLogout.textContent = '退出登录';
    if (resp && resp.ok) {
      showToast('已退出 LinuxDo登录');
      loadInviteConfig();
    } else {
      showToast('[X] ' + (resp?.error || '退出失败').slice(0, 80));
    }
  });
});

function clearInvitePoll() {
  if (window._inviteSessionPollTimer) {
    clearInterval(window._inviteSessionPollTimer);
    window._inviteSessionPollTimer = null;
  }
}

btnInviteCancel.addEventListener('click', function () {
  clearInvitePoll();
  chrome.runtime.sendMessage({ type: 'INVITE_CANCEL' }, function () {
    invActiveStatus.style.display = 'none';
    btnInviteCancel.style.display = 'none';
    btnInviteStart.textContent = '启动 Token 交换';
    showToast('邀请模式已取消');
  });
});

initAuthURL();
loadTokens();
loadInviteConfig();
setInterval(loadTokens, 2000);
setInterval(loadInviteConfig, 5000);
