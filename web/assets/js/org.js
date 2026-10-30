// 项目设置：项目信息、产线/SOP、成员管理，全部作用于当前项目。
import { authFetch, currentUser, notify } from './core.js';
import { t } from './i18n.js';

let settingsData = null;
let editingLineId = null;

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function roleText(role) {
  const map = {
    owner: 'role_owner',
    editor: 'role_editor',
    viewer: 'role_viewer',
    admin: 'role_admin'
  };
  return t(map[role] || 'role_viewer');
}

function statusText(status) {
  return status === 'archived' ? t('status_archived') : t('status_active');
}

function projectId() {
  return settingsData && settingsData.project ? settingsData.project.id : null;
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('open');
}

// 弹窗原本嵌在隐藏的项目页签里，position: fixed 也无法显示，统一挂到 body 下
function mountModalToBody(id) {
  const modal = document.getElementById(id);
  if (modal && modal.parentElement !== document.body) document.body.appendChild(modal);
}

async function readJson(res) {
  try {
    return await res.json();
  } catch (_) {
    return {};
  }
}

export function renderProjectSettings(data) {
  settingsData = data;
  if (!data) return;
  const project = data.project || {};
  const canManage = Boolean(data.can_manage);
  const isAdmin = currentUser && currentUser.role === 'admin';

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value || '-';
  };
  setText('psProjectName', project.name);
  setText('psProjectCode', project.code);
  setText('psProjectStatus', statusText(project.status));
  setText('psProjectRole', roleText(project.my_role || (isAdmin ? 'admin' : 'viewer')));
  setText('psProjectDesc', project.description);

  const editBtn = document.getElementById('btnEditProject');
  if (editBtn) editBtn.style.display = isAdmin ? 'inline-block' : 'none';

  const createLineBtn = document.getElementById('btnCreateLine');
  if (createLineBtn) createLineBtn.style.display = canManage ? 'inline-block' : 'none';

  const addMember = document.getElementById('projectMemberAdd');
  if (addMember) addMember.style.display = canManage ? 'flex' : 'none';

  renderLines(data.lines || [], canManage);
  renderMembers(data.members || [], canManage);
}

function renderLines(lines, canManage) {
  const body = document.getElementById('psLineBody');
  const empty = document.getElementById('psLineEmpty');
  if (!body) return;
  if (empty) empty.style.display = lines.length ? 'none' : 'block';
  body.innerHTML = lines
    .map(
      (line) => `<tr>
        <td class="table-main">${escapeHtml(line.name)}</td>
        <td>${escapeHtml(line.code)}</td>
        <td>${escapeHtml(line.process_desc || '-')}</td>
        <td>${line.has_sop ? `<span class="pill pill-success">${t('project_sop_configured')}</span>` : `<span class="pill">${t('project_sop_default')}</span>`}</td>
        <td class="table-actions">
          ${
            canManage
              ? `<button class="btn btn-small" type="button" data-edit-line="${line.id}">${t('edit')}</button>`
              : '-'
          }
        </td>
      </tr>`
    )
    .join('');
  if (canManage) {
    body.querySelectorAll('[data-edit-line]').forEach((btn) => {
      btn.addEventListener('click', () => openLineModal(Number(btn.dataset.editLine)));
    });
  }
}

function renderMembers(members, canManage) {
  const body = document.getElementById('psMemberBody');
  const empty = document.getElementById('psMemberEmpty');
  const count = document.getElementById('psMemberCount');
  if (count) count.textContent = String(members.length);
  if (!body) return;
  if (empty) empty.style.display = members.length ? 'none' : 'block';
  body.innerHTML = members
    .map(
      (member) => `<tr>
        <td class="table-main">${escapeHtml(member.username)}</td>
        <td>${roleText(member.role)}</td>
        <td>${member.created_at ? escapeHtml(String(member.created_at)) : '-'}</td>
        <td class="table-actions">
          ${
            canManage
              ? `<button class="btn btn-small btn-danger" type="button" data-remove-member="${escapeHtml(member.username)}">${t('project_remove_member')}</button>`
              : '-'
          }
        </td>
      </tr>`
    )
    .join('');
  if (canManage) {
    body.querySelectorAll('[data-remove-member]').forEach((btn) => {
      btn.addEventListener('click', () => removeMember(btn.dataset.removeMember));
    });
  }
}

function openCreateProjectModal() {
  const modal = document.getElementById('projectModal');
  if (!modal) return;
  const name = document.getElementById('projectNameInput');
  const code = document.getElementById('projectCodeInput');
  const desc = document.getElementById('projectDescInput');
  const status = document.getElementById('projectStatusInput');
  const title = document.getElementById('projectModalTitle');
  modal.dataset.mode = 'create';
  modal.dataset.projectId = '';
  if (title) title.textContent = t('project_create');
  if (name) name.value = '';
  if (code) {
    code.value = '';
    code.disabled = false;
  }
  if (desc) desc.value = '';
  if (status) status.value = 'active';
  modal.classList.add('open');
}

function openEditProjectModal() {
  if (!settingsData || !settingsData.project) return;
  const project = settingsData.project;
  const modal = document.getElementById('projectModal');
  if (!modal) return;
  const name = document.getElementById('projectNameInput');
  const code = document.getElementById('projectCodeInput');
  const desc = document.getElementById('projectDescInput');
  const status = document.getElementById('projectStatusInput');
  const title = document.getElementById('projectModalTitle');
  modal.dataset.mode = 'edit';
  modal.dataset.projectId = String(project.id);
  if (title) title.textContent = t('org_edit_project');
  if (name) name.value = project.name || '';
  if (code) {
    code.value = project.code || '';
    code.disabled = true;
  }
  if (desc) desc.value = project.description || '';
  if (status) status.value = project.status || 'active';
  modal.classList.add('open');
}

async function saveProject() {
  const modal = document.getElementById('projectModal');
  if (!modal) return;
  const mode = modal.dataset.mode || 'edit';
  const name = (document.getElementById('projectNameInput')?.value || '').trim();
  const code = (document.getElementById('projectCodeInput')?.value || '').trim();
  const description = (document.getElementById('projectDescInput')?.value || '').trim();
  const status = document.getElementById('projectStatusInput')?.value || 'active';
  if (!name) {
    notify(t('project_name_required'));
    return;
  }
  const btn = document.getElementById('btnSaveProject');
  if (btn) btn.disabled = true;
  try {
    let res;
    if (mode === 'create') {
      if (!code) {
        notify(t('project_code_required'));
        return;
      }
      res = await authFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, name, description })
      });
    } else {
      const pid = Number(modal.dataset.projectId || projectId());
      res = await authFetch('/api/projects/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: pid, name, description, status })
      });
    }
    const data = await readJson(res);
    if (!res.ok) {
      notify(data.details || data.error || t('save_failed'));
      return;
    }
    closeModal('projectModal');
    if (mode === 'create') {
      await window.loadProjectSidebar?.();
      if (data.project_id) await window.openProject?.(Number(data.project_id));
      notify(t('project_created'));
    } else {
      await window.refreshProjectWorkspace?.();
      await window.loadProjectSidebar?.();
      notify(t('saved'));
    }
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  } finally {
    if (btn) btn.disabled = false;
  }
}

export function openLineModal(lineId = null) {
  const modal = document.getElementById('lineModal');
  if (!modal) return;
  editingLineId = lineId;
  const title = document.getElementById('lineModalTitle');
  const name = document.getElementById('lineNameInput');
  const code = document.getElementById('lineCodeInput');
  const desc = document.getElementById('lineDescInput');
  const sop = document.getElementById('lineSopInput');
  const stationGroup = document.getElementById('lineStationGroup');
  const stationInput = document.getElementById('lineStationInput');
  const line = (settingsData?.lines || []).find((item) => String(item.id) === String(lineId));
  if (lineId && !line) return;
  if (title) title.textContent = line ? t('line_edit') : t('line_create');
  if (name) name.value = line ? line.name || '' : '';
  if (code) {
    code.value = line ? line.code || '' : '';
    code.disabled = Boolean(line);
  }
  if (desc) desc.value = line ? line.process_desc || '' : '';
  if (sop) sop.value = line ? line.sop_content || '' : '';
  if (stationGroup) stationGroup.style.display = line ? 'none' : 'block';
  if (stationInput) stationInput.value = line ? '' : '4';
  modal.classList.add('open');
}

async function saveLine() {
  const pid = projectId();
  if (!pid) return;
  const name = (document.getElementById('lineNameInput')?.value || '').trim();
  const code = (document.getElementById('lineCodeInput')?.value || '').trim();
  const processDesc = (document.getElementById('lineDescInput')?.value || '').trim();
  const sopContent = document.getElementById('lineSopInput')?.value || '';
  const stationRaw = document.getElementById('lineStationInput')?.value;
  const stationCount = editingLineId ? 0 : Number.parseInt(stationRaw || '0', 10) || 0;
  if (!name || (!editingLineId && !code)) {
    notify(t('line_code_name_required'));
    return;
  }
  const btn = document.getElementById('btnSaveLine');
  if (btn) btn.disabled = true;
  try {
    const payload = {
      name,
      process_desc: processDesc,
      sop_content: sopContent
    };
    let res;
    if (editingLineId) {
      res = await authFetch('/api/lines/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, line_id: editingLineId })
      });
    } else {
      res = await authFetch('/api/lines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, project_id: pid, code, station_count: stationCount })
      });
    }
    const data = await readJson(res);
    if (!res.ok) {
      notify(data.details || data.error || t('save_failed'));
      return;
    }
    closeModal('lineModal');
    await window.refreshProjectWorkspace?.();
    notify(t('saved'));
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function addMember() {
  const pid = projectId();
  if (!pid) return;
  const usernameEl = document.getElementById('psMemberUsername');
  const roleEl = document.getElementById('psMemberRole');
  const username = (usernameEl?.value || '').trim();
  const role = roleEl?.value || 'viewer';
  if (!username) {
    notify(t('project_member_username_required'));
    return;
  }
  const btn = document.getElementById('btnAddMember');
  if (btn) btn.disabled = true;
  try {
    const res = await authFetch('/api/members', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: pid, username, role })
    });
    const data = await readJson(res);
    if (!res.ok) {
      notify(data.details || data.error || t('save_failed'));
      return;
    }
    if (usernameEl) usernameEl.value = '';
    await window.refreshProjectWorkspace?.();
    notify(t('project_member_added'));
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function removeMember(username) {
  const pid = projectId();
  if (!pid || !username) return;
  if (!window.confirm(t('project_remove_member_confirm', { username }))) return;
  try {
    const res = await authFetch('/api/members/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: pid, username })
    });
    const data = await readJson(res);
    if (!res.ok) {
      notify(data.details || data.error || t('save_failed'));
      return;
    }
    await window.refreshProjectWorkspace?.();
    notify(t('project_member_removed'));
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  }
}

export function setupProjectSettingsUI() {
  mountModalToBody('projectModal');
  mountModalToBody('lineModal');
  const createBtn = document.getElementById('btnCreateProject');
  if (createBtn) createBtn.addEventListener('click', openCreateProjectModal);
  const editBtn = document.getElementById('btnEditProject');
  if (editBtn) editBtn.addEventListener('click', openEditProjectModal);
  const saveProjectBtn = document.getElementById('btnSaveProject');
  if (saveProjectBtn) saveProjectBtn.addEventListener('click', saveProject);
  const cancelProjectBtn = document.getElementById('btnCancelProject');
  if (cancelProjectBtn) cancelProjectBtn.addEventListener('click', () => closeModal('projectModal'));
  const createLineBtn = document.getElementById('btnCreateLine');
  if (createLineBtn) createLineBtn.addEventListener('click', () => openLineModal(null));
  const saveLineBtn = document.getElementById('btnSaveLine');
  if (saveLineBtn) saveLineBtn.addEventListener('click', saveLine);
  const cancelLineBtn = document.getElementById('btnCancelLine');
  if (cancelLineBtn) cancelLineBtn.addEventListener('click', () => closeModal('lineModal'));
  const addMemberBtn = document.getElementById('btnAddMember');
  if (addMemberBtn) addMemberBtn.addEventListener('click', addMember);

  ['projectModal', 'lineModal'].forEach((id) => {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal(id);
    });
  });
}
