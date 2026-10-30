import { brandReplace, currentLang, t } from './i18n.js';
import { formatRole } from './format.js';
import { loadUserList } from './users.js';
import { clearScope } from './scope.js';
import { pollTaskStatus } from './detection.js';
import { currentStats, renderStats } from './review.js';

export async function fetchVersion() {
  try {
    const res = await fetch('/api/version');
    if (res.ok) {
      const data = await res.json();
      const el = document.getElementById('currentVersion');
      if (el && data.version) {
        el.dataset.version = String(data.version);
        el.textContent = data.version;
      }
    }
  } catch {}
}

export function notify(message) {
  const modal = document.getElementById('notifyModal');
  const title = document.getElementById('notifyTitle');
  const body = document.getElementById('notifyMessage');
  const ok = document.getElementById('btnNotifyOk');
  if (!modal || !body || !ok) return;
  if (title) title.textContent = t('notify_title');
  body.textContent = String(message ?? '');
  modal.classList.add('open');
  ok.onclick = () => {
    modal.classList.remove('open');
  };
  modal.onclick = (e) => {
    if (e.target === modal) modal.classList.remove('open');
  };
  document.addEventListener(
    'keydown',
    (e) => {
      if (e.key !== 'Enter') return;
      ok.click();
    },
    { once: true }
  );
}

export function getToken() {
  try {
    return localStorage.getItem('auth_token') || '';
  } catch {
    return '';
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem('auth_token', token);
    else localStorage.removeItem('auth_token');
  } catch {}
}

export function withMediaToken(url) {
  const token = getToken();
  if (!token) return url;
  const sep = url.includes('?') ? '&' : '?';
  return url + sep + 'token=' + encodeURIComponent(token);
}

export function setLoginActive(active) {
  document.body.classList.toggle('login-active', Boolean(active));
  if (active) {
    document.querySelectorAll('.modal').forEach((el) => el.classList.remove('active'));
    document.querySelectorAll('.modal-overlay').forEach((el) => el.classList.remove('open'));
  }
}

export function getThemeColor(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback || '';
}

export function applyTheme(theme) {
  const normalized = theme === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', normalized);
  try {
    localStorage.setItem('ui_theme', normalized);
  } catch {}
  if (typeof renderStats === 'function') {
    renderStats(currentStats);
  }
}

export function bindEnterToButton(container, button) {
  if (!container || !button) return;
  const inputs = container.querySelectorAll('input, select');
  inputs.forEach((el) => {
    el.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      button.click();
    });
  });
}

export let currentUser = null;

export function updateSidebarUserText() {
  const nameEl = document.getElementById('sidebarUser');
  if (!nameEl) return;
  if (!currentUser) {
    nameEl.textContent = t('not_logged_in');
    return;
  }
  nameEl.textContent = `${currentUser.username} (${formatRole(currentUser.role)})`;
}

export function updateAdminUI() {
  const navUsers = document.getElementById('navUsers');
  const viewUsers = document.getElementById('view-users');
  const navCalc = document.getElementById('navCalculator');
  const estimateBtn = document.getElementById('btnEstimateCost');
  const costDiv = document.getElementById('costEstimate');
  const createProjectBtn = document.getElementById('btnCreateProject');
  const isAdmin = currentUser && currentUser.role === 'admin';
  if (navUsers) navUsers.style.display = isAdmin ? 'block' : 'none';
  if (viewUsers) viewUsers.style.display = isAdmin ? '' : 'none';
  if (navCalc) navCalc.style.display = isAdmin ? 'block' : 'none';
  if (createProjectBtn) createProjectBtn.style.display = isAdmin ? 'inline-block' : 'none';
  if (estimateBtn) estimateBtn.style.display = 'none';
  if (!isAdmin && costDiv) costDiv.style.display = 'none';
  if (!isAdmin) {
    const view = document.getElementById('view-users');
    const viewCalc = document.getElementById('view-calculator');
    if (
      (view && view.classList.contains('active')) ||
      (viewCalc && viewCalc.classList.contains('active'))
    ) {
      switchTab('projects');
    }
  }
}

export async function authFetch(url, options = {}) {
  const opts = { ...options };
  opts.headers = { ...(opts.headers || {}) };
  const tokenAtRequest = getToken();
  if (tokenAtRequest) opts.headers['Authorization'] = 'Bearer ' + tokenAtRequest;
  if (!opts.headers['X-UI-Lang']) opts.headers['X-UI-Lang'] = currentLang || 'zh';
  const res = await fetch(url, opts);
  if (res.status === 401) {
    const tokenNow = getToken();
    if (tokenAtRequest && tokenNow && tokenNow === tokenAtRequest) {
      setToken('');
      setLoginActive(true);
    }
  }
  return res;
}

export async function refreshMe() {
  const nameEl = document.getElementById('sidebarUser');
  const btnLogin = document.getElementById('btnShowLogin');
  const btnLogout = document.getElementById('btnLogout');
  const token = getToken();
  if (!token) {
    if (btnLogin) btnLogin.style.display = 'inline-block';
    if (btnLogout) btnLogout.style.display = 'none';
    currentUser = null;
    clearScope();
    updateSidebarUserText();
    updateAdminUI();
    setLoginActive(true);
    return;
  }
  try {
    const res = await authFetch('/api/me');
    if (!res.ok) throw new Error('not ok');
    const data = await res.json();
    const user = (data && data.user) || null;
    if (user) {
      currentUser = user;
      updateSidebarUserText();
      if (btnLogin) btnLogin.style.display = 'none';
      if (btnLogout) btnLogout.style.display = 'inline-block';
      updateAdminUI();
      await window.loadProjectSidebar?.();

      const detectModel = document.getElementById('detectModel');
      if (detectModel) {
        const preferredModel = (currentUser.model || 'kimi-2.5').trim();
        const hasOption = Array.from(detectModel.options || []).some((opt) => opt.value === preferredModel);
        if (!hasOption && preferredModel) {
          const dynamicOption = document.createElement('option');
          dynamicOption.value = preferredModel;
          dynamicOption.textContent = preferredModel;
          detectModel.appendChild(dynamicOption);
        }
        detectModel.value = preferredModel || 'kimi-2.5';
      }

      setLoginActive(false);
      await window.restoreProjectView?.();
      return;
    }
  } catch {}
  currentUser = null;
  clearScope();
  updateSidebarUserText();
  if (btnLogin) btnLogin.style.display = 'inline-block';
  if (btnLogout) btnLogout.style.display = 'none';
  updateAdminUI();
  setLoginActive(true);
}

export function setupAuthUI() {
  const btnShowLogin = document.getElementById('btnShowLogin');
  const btnConfirm = document.getElementById('btnConfirmLogin');
  const btnLogout = document.getElementById('btnLogout');
  const err = document.getElementById('loginError');
  const loginPage = document.getElementById('loginPage');
  if (btnShowLogin)
    btnShowLogin.onclick = () => {
      if (err) err.textContent = '';
      setLoginActive(true);
    };
  bindEnterToButton(loginPage, btnConfirm);
  if (btnConfirm)
    btnConfirm.onclick = async () => {
      if (err) err.textContent = '';
      const usernameEl = document.getElementById('loginUsername');
      const passwordEl = document.getElementById('loginPassword');
      const u = (usernameEl ? usernameEl.value : '').trim();
      const p = passwordEl ? passwordEl.value : '';
      try {
        const res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (!res.ok) {
          if (err)
            err.textContent =
              data && data.error ? `${t('login_failed')}: ${data.error}` : t('login_failed');
          return;
        }
        setToken(data.token);
        await refreshMe();
      } catch {
        if (err) err.textContent = t('network_error');
      }
    };
  if (btnLogout)
    btnLogout.onclick = async () => {
      try {
        await authFetch('/api/logout', { method: 'POST' });
      } catch {}
      setToken('');
      await refreshMe();
    };
  refreshMe().then(() => pollTaskStatus());
}

export function appendLog(container, text) {
  const thumbnailStart = '[THUMBNAIL]';
  const thumbnailEnd = '[THUMBNAIL_END]';

  let processedText = text;
  const startIdx = text.indexOf(thumbnailStart);
  if (startIdx !== -1) {
    const endIdx = text.indexOf(thumbnailEnd, startIdx);
    if (endIdx !== -1) {
      const base64Data = text.substring(startIdx + thumbnailStart.length, endIdx);
      const thumbnailImg = document.getElementById('detectThumbnail');
      const thumbnailContainer = document.getElementById('thumbnailContainer');
      if (thumbnailImg && thumbnailContainer) {
        thumbnailImg.src = 'data:image/jpeg;base64,' + base64Data;
        thumbnailContainer.style.display = 'block';
      }
      processedText = text.substring(0, startIdx) + text.substring(endIdx + thumbnailEnd.length);
    }
  }

  if (processedText) {
    container.appendChild(document.createTextNode(brandReplace(processedText)));
  }
}

export function setLog(el, text) {
  if (!el) return;
  el.textContent = brandReplace(text);
}

export function isMobile() {
  return window.matchMedia && window.matchMedia('(max-width: 768px)').matches;
}

export function setSidebarToggleIcon() {
  const btn = document.getElementById('sidebarToggle');
  if (!btn) return;
  if (isMobile()) {
    btn.textContent = '✕';
    return;
  }
  btn.textContent = document.body.classList.contains('sidebar-collapsed') ? '⟩' : '⟨';
}

export function setSidebarCollapsed(nextCollapsed) {
  document.body.classList.toggle('sidebar-collapsed', Boolean(nextCollapsed));
  try {
    localStorage.setItem('sidebar_collapsed', nextCollapsed ? '1' : '0');
  } catch {}
  setSidebarDrawerOpen(false);
  setSidebarToggleIcon();
}

export function setSidebarDrawerOpen(nextOpen) {
  document.body.classList.toggle('sidebar-drawer-open', Boolean(nextOpen));
  setSidebarToggleIcon();
}

export function initSidebar() {
  let collapsed = false;
  try {
    collapsed = localStorage.getItem('sidebar_collapsed') === '1';
  } catch {}
  if (isMobile()) {
    document.body.classList.remove('sidebar-collapsed');
    setSidebarDrawerOpen(false);
  } else {
    setSidebarCollapsed(collapsed);
    setSidebarDrawerOpen(false);
  }
  setSidebarToggleIcon();

  const btn = document.getElementById('sidebarToggle');
  const overlay = document.getElementById('sidebarOverlay');
  const menuButtons = document.querySelectorAll('[data-menu-button]');
  if (btn) {
    btn.addEventListener('click', () => {
      if (isMobile()) {
        setSidebarDrawerOpen(false);
        return;
      }
      if (document.body.classList.contains('sidebar-collapsed')) {
        setSidebarCollapsed(false);
        return;
      }
      setSidebarCollapsed(true);
    });
  }
  menuButtons.forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isOpen = document.body.classList.contains('sidebar-drawer-open');
      if (isOpen) {
        setSidebarDrawerOpen(false);
        return;
      }
      setTimeout(() => setSidebarDrawerOpen(true), 0);
    });
  });
  if (overlay) {
    overlay.addEventListener('click', () => {
      setSidebarDrawerOpen(false);
    });
  }
  window.addEventListener('resize', () => initSidebar());
}
export function switchTab(tabId) {
  document.querySelectorAll('.nav-item').forEach((el) => el.classList.remove('active'));
  const navTarget = Array.from(document.querySelectorAll('.nav-item')).find(
    (el) => el.dataset.tab === tabId
  );
  if (navTarget) navTarget.classList.add('active');

  document.querySelectorAll('.page-view').forEach((el) => el.classList.remove('active'));
  const view = document.getElementById('view-' + tabId);
  if (view) view.classList.add('active');

  if (tabId === 'projects') window.renderProjectsPage?.();
  if (tabId === 'users') loadUserList();
  if (tabId === 'settings') fetchVersion();
  setSidebarDrawerOpen(false);
}
