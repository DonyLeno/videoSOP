import { t } from './i18n.js';
import { authFetch, bindEnterToButton, currentUser, notify, refreshMe } from './core.js';
import { formatBytes, formatModel, formatRole, formatStatus, formatTime, getBaseName, maskApiKey } from './format.js';
import { formatSecondsShort } from './review.js';

let userCache = {};

export async function loadUserList() {
  if (!currentUser || currentUser.role !== 'admin') return;
  const body = document.getElementById('userTableBody');
  const empty = document.getElementById('userEmpty');
  if (!body || !empty) return;
  body.innerHTML = '';
  empty.style.display = 'none';
  try {
    const res = await authFetch('/api/users');
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data && data.error ? data.error : t('load_failed'));
    }
    const users = data.users || [];
    userCache = {};
    if (!users.length) {
      empty.style.display = 'block';
      return;
    }
    users.forEach((u) => {
      userCache[u.username] = u;
      const tr = document.createElement('tr');
      const statusClass = u.status === 'inactive' ? 'user-pill inactive' : 'user-pill active';
      tr.innerHTML = `
        <td>${u.username}</td>
        <td>${formatRole(u.role)}</td>
        <td>${formatModel(u.model)}</td>
        <td>${u.email || '-'}</td>
        <td>${maskApiKey(u.api_key)}</td>
        <td><span class="${statusClass}">${formatStatus(u.status)}</span></td>
        <td>${formatTime(u.created_at)}</td>
        <td>${formatBytes(u.data_usage)}</td>
        <td>
          <button class="btn btn-small" data-action="edit-user" data-username="${u.username}">${t(
            'edit'
          )}</button>
          <button class="btn btn-small" data-action="view-history" data-username="${u.username}">检测历史</button>
          ${
            u.username !== (currentUser && currentUser.username)
              ? `<button class="btn btn-small btn-danger-outline" data-action="revoke-sessions" data-username="${u.username}" title="${t('revoke_sessions_title')}">${t('revoke_sessions')}</button>`
              : ''
          }
        </td>
      `;
      body.appendChild(tr);
    });
  } catch (e) {
    notify(t('user_list_load_failed', { error: e.message }));
  }
}

export async function revokeUserSessions(username) {
  if (!username) return;
  if (!window.confirm(t('revoke_sessions_confirm', { username }))) return;
  try {
    const res = await authFetch('/api/users/revoke_sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || 'status ' + res.status);
    notify(t('revoke_sessions_done', { username, count: data.revoked ?? 0 }));
  } catch (e) {
    notify(t('revoke_sessions_failed', { error: e.message }));
  }
}


export function formatTokenTotal(item) {
  if (!item) return '-';
  const total = Number(item.token_total);
  if (Number.isFinite(total) && total > 0) return String(Math.round(total));
  const parts = [item.token_input, item.token_output, item.token_thinking]
    .map((v) => Number(v))
    .filter((v) => Number.isFinite(v) && v > 0);
  if (!parts.length) return '-';
  return String(Math.round(parts.reduce((a, b) => a + b, 0)));
}

export function renderUserHistory(items) {
  const body = document.getElementById('userHistoryBody');
  const empty = document.getElementById('userHistoryEmpty');
  if (!body || !empty) return;
  body.innerHTML = '';
  empty.style.display = 'none';
  if (!items || !items.length) {
    empty.style.display = 'block';
    return;
  }
  items.forEach((item) => {
    const tr = document.createElement('tr');
    const name =
      item.video_name ||
      getBaseName(item.video_path) ||
      getBaseName(item.result_path) ||
      '-';
    const duration = formatSecondsShort(item.video_seconds);
    tr.innerHTML = `
      <td>${formatTime(item.created_at)}</td>
      <td>${name}</td>
      <td>${duration}</td>
      <td>${formatModel(item.model)}</td>
      <td>${formatTokenTotal(item)}</td>
    `;
    body.appendChild(tr);
  });
}

export async function openUserHistoryModal(username) {
  const modal = document.getElementById('userHistoryModal');
  const title = document.getElementById('userHistoryTitle');
  const body = document.getElementById('userHistoryBody');
  const empty = document.getElementById('userHistoryEmpty');
  if (!modal || !body || !empty) return;
  if (title) title.textContent = username ? `检测历史 - ${username}` : '检测历史';
  body.innerHTML = `<tr><td colspan="5">加载中...</td></tr>`;
  empty.style.display = 'none';
  modal.classList.add('open');
  try {
    const res = await authFetch(`/api/user_history?username=${encodeURIComponent(username || '')}`);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data && data.error ? data.error : t('load_failed'));
    }
    renderUserHistory(data.items || []);
  } catch (e) {
    body.innerHTML = '';
    empty.style.display = 'block';
    notify(t('load_failed') + ': ' + (e.message || ''));
  }
}

export function closeUserHistoryModal() {
  const modal = document.getElementById('userHistoryModal');
  if (modal) modal.classList.remove('open');
}

export function openUserModal(mode, user) {
  const modal = document.getElementById('userModal');
  const title = document.getElementById('userModalTitle');
  const usernameEl = document.getElementById('userFormUsername');
  const passwordEl = document.getElementById('userFormPassword');
  const passwordLabel = document.getElementById('userFormPasswordLabel');
  const emailEl = document.getElementById('userFormEmail');
  const apiKeyEl = document.getElementById('userFormApiKey');
  const roleEl = document.getElementById('userFormRole');
  const modelEl = document.getElementById('userFormModel');
  const statusEl = document.getElementById('userFormStatus');
  const err = document.getElementById('userFormError');
  if (
    !modal ||
    !title ||
    !usernameEl ||
    !passwordEl ||
    !emailEl ||
    !apiKeyEl ||
    !roleEl ||
    !modelEl ||
    !statusEl ||
    !err
  )
    return;
  err.textContent = '';
  modal.dataset.mode = mode;
  if (mode === 'edit' && user) {
    title.textContent = t('user_edit');
    usernameEl.value = user.username || '';
    usernameEl.readOnly = true;
    passwordEl.value = '';
    if (passwordLabel) passwordLabel.textContent = t('user_new_password_optional');
    emailEl.value = user.email || '';
    apiKeyEl.value = user.api_key || '';
    roleEl.value = user.role || 'user';
    modelEl.value = user.model || 'kimi-2.5';
    statusEl.value = user.status || 'active';
  } else {
    title.textContent = t('user_create');
    usernameEl.value = '';
    usernameEl.readOnly = false;
    passwordEl.value = '';
    if (passwordLabel) passwordLabel.textContent = t('user_password');
    emailEl.value = '';
    apiKeyEl.value = '';
    roleEl.value = 'user';
    modelEl.value = 'kimi-2.5';
    statusEl.value = 'active';
  }
  modal.classList.add('open');
}

export function closeUserModal() {
  const modal = document.getElementById('userModal');
  if (modal) modal.classList.remove('open');
}

export function setupUserManagement() {
  const btnCreate = document.getElementById('btnCreateUser');
  const btnRefresh = document.getElementById('btnRefreshUsers');
  const btnCancel = document.getElementById('btnUserCancel');
  const btnSave = document.getElementById('btnUserSave');
  const btnHistoryClose = document.getElementById('btnUserHistoryClose');
  const table = document.getElementById('userTable');
  if (btnCreate) btnCreate.onclick = () => openUserModal('create');
  if (btnRefresh) btnRefresh.onclick = () => loadUserList();
  if (btnCancel) btnCancel.onclick = () => closeUserModal();
  if (btnHistoryClose) btnHistoryClose.onclick = () => closeUserHistoryModal();
  if (table) {
    table.addEventListener('click', (e) => {
      const btnEdit = e.target.closest('[data-action="edit-user"]');
      const btnHistory = e.target.closest('[data-action="view-history"]');
      const btnRevoke = e.target.closest('[data-action="revoke-sessions"]');
      if (!btnEdit && !btnHistory && !btnRevoke) return;
      const username = (btnEdit || btnHistory || btnRevoke).getAttribute('data-username');
      if (btnEdit) {
        const user = userCache[username] || null;
        if (user) openUserModal('edit', user);
        return;
      }
      if (btnRevoke) {
        revokeUserSessions(username);
        return;
      }
      openUserHistoryModal(username);
    });
  }
  const modal = document.getElementById('userModal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeUserModal();
    });
  }
  const historyModal = document.getElementById('userHistoryModal');
  if (historyModal) {
    historyModal.addEventListener('click', (e) => {
      if (e.target === historyModal) closeUserHistoryModal();
    });
  }
  bindEnterToButton(modal, btnSave);
  if (btnSave) {
    btnSave.onclick = async () => {
      const modal = document.getElementById('userModal');
      const err = document.getElementById('userFormError');
      const usernameEl = document.getElementById('userFormUsername');
      const passwordEl = document.getElementById('userFormPassword');
      const emailEl = document.getElementById('userFormEmail');
      const apiKeyEl = document.getElementById('userFormApiKey');
      const roleEl = document.getElementById('userFormRole');
      const modelEl = document.getElementById('userFormModel');
      const statusEl = document.getElementById('userFormStatus');
      if (
        !modal ||
        !err ||
        !usernameEl ||
        !passwordEl ||
        !emailEl ||
        !apiKeyEl ||
        !roleEl ||
        !modelEl ||
        !statusEl
      )
        return;
      err.textContent = '';
      const mode = modal.dataset.mode || 'create';
      const username = usernameEl.value.trim();
      const password = passwordEl.value;
      const email = emailEl.value.trim();
      const apiKey = apiKeyEl.value.trim();
      const role = roleEl.value;
      const model = modelEl.value;
      const status = statusEl.value;
      try {
        let res;
        if (mode === 'edit') {
          res = await authFetch('/api/users/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              username,
              email,
              api_key: apiKey,
              role,
              model,
              status,
              new_password: password || ''
            })
          });
        } else {
          res = await authFetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              username,
              password,
              email,
              api_key: apiKey,
              role,
              model,
              status
            })
          });
        }
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data && data.error ? data.error : t('save_failed'));
        }
        closeUserModal();
        await loadUserList();
        await refreshMe();
      } catch (e) {
        err.textContent = e.message || t('save_failed');
      }
    };
  }
}

// =====================================================================
// 阶段 2：作用域（项目/产线）与组织管理
// =====================================================================
