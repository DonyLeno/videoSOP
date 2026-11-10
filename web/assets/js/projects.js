// 项目中心与项目工作区：视频、检测、结果、设置全部围绕当前项目展开。
import { authFetch, currentUser, notify, switchTab } from './core.js';
import { formatTime } from './format.js';
import { t } from './i18n.js';
import { currentScope, getStoredScope, setProjectScope, setScopeLine, setScopeStation } from './scope.js';
import { loadVideoList } from './detection.js';
import { loadResultList } from './review.js';
import { openLineModal, renderProjectSettings, setupProjectSettingsUI } from './org.js';
import { renderStationPlan, setupStationPlanUI } from './stations.js';

export let projectsCache = [];
export let activeProjectId = null;
export let projectWorkspace = null;

let currentProjectTab = 'overview';

const PROJECT_TREE_KEY = 'sidebar_projects_expanded';
let projectsExpanded = true;
try {
  const stored = localStorage.getItem(PROJECT_TREE_KEY);
  if (stored !== null) projectsExpanded = stored !== '0';
} catch (_) {
  // localStorage 不可用时默认展开
}

function applyProjectTreeState() {
  const list = document.getElementById('sidebarProjectList');
  const toggle = document.getElementById('sidebarProjectToggle');
  const root = document.getElementById('sidebarProjectsRoot');
  const count = document.getElementById('sidebarProjectCount');
  if (list) list.classList.toggle('is-collapsed', !projectsExpanded);
  if (root) root.classList.toggle('is-collapsed', !projectsExpanded);
  if (toggle) {
    toggle.setAttribute('aria-expanded', String(projectsExpanded));
    toggle.setAttribute('title', t(projectsExpanded ? 'project_tree_collapse' : 'project_tree_expand'));
  }
  if (count) {
    count.textContent = projectsCache.length ? String(projectsCache.length) : '';
    count.style.display = projectsCache.length ? 'inline-flex' : 'none';
  }
}

function setProjectsExpanded(expanded) {
  projectsExpanded = Boolean(expanded);
  try {
    localStorage.setItem(PROJECT_TREE_KEY, projectsExpanded ? '1' : '0');
  } catch (_) {
    // 忽略存储失败
  }
  applyProjectTreeState();
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatDuration(seconds) {
  const total = Number(seconds);
  if (!Number.isFinite(total) || total <= 0) return '-';
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = Math.floor(total % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function projectStatusText(status) {
  return status === 'archived' ? t('status_archived') : t('status_active');
}

function taskStatusText(status) {
  const map = {
    pending: 'task_pending',
    running: 'task_running',
    succeeded: 'task_completed',
    completed: 'task_completed',
    failed: 'task_failed',
    canceled: 'task_canceled'
  };
  return t(map[status] || 'task_not_started');
}

function resultStatusForVideo(video) {
  if (video.latest_result) {
    return `<span class="pill pill-success">${t('project_status_has_result')}</span>`;
  }
  const status = video.latest_task && video.latest_task.status;
  if (status === 'running' || status === 'pending') {
    return `<span class="pill pill-warning">${t('task_running')}</span>`;
  }
  if (status === 'failed') {
    return `<span class="pill pill-danger">${t('task_failed')}</span>`;
  }
  return `<span class="pill">${t('task_not_started')}</span>`;
}

export function renderProjectSidebar() {
  const root = document.getElementById('sidebarProjectList');
  if (!root) return;
  applyProjectTreeState();
  if (!projectsCache.length) {
    root.innerHTML = `<div class="sidebar-project-empty">${t('projects_empty_sidebar')}</div>`;
    return;
  }
  root.innerHTML = projectsCache
    .map((project) => {
      const active = String(project.id) === String(activeProjectId);
      return `<button type="button" class="sidebar-project-item ${active ? 'active' : ''}" data-project-id="${project.id}">
        <span class="sidebar-project-name">${escapeHtml(project.name)}</span>
        <span class="sidebar-project-code">${escapeHtml(project.code || '')}</span>
      </button>`;
    })
    .join('');
  root.querySelectorAll('[data-project-id]').forEach((el) => {
    el.addEventListener('click', () => openProject(Number(el.dataset.projectId)));
  });
}

export function renderProjectsPage() {
  const root = document.getElementById('projectCards');
  if (!root) return;
  const createBtn = document.getElementById('btnCreateProject');
  if (createBtn) {
    createBtn.style.display = currentUser && currentUser.role === 'admin' ? 'inline-block' : 'none';
  }
  const meta = document.getElementById('projectsMeta');
  if (meta) meta.textContent = t('projects_count', { count: projectsCache.length });

  const empty = document.getElementById('projectsEmpty');
  if (!projectsCache.length) {
    root.innerHTML = '';
    if (empty) empty.style.display = 'block';
    return;
  }
  if (empty) empty.style.display = 'none';
  root.innerHTML = projectsCache
    .map((project) => {
      const archived = project.status === 'archived';
      const canDelete =
        currentUser && (currentUser.role === 'admin' || project.my_role === 'owner');
      return `<article class="project-card ${archived ? 'is-archived' : ''}" data-project-id="${project.id}">
        <div class="project-card-top">
          <span class="project-card-code">${escapeHtml(project.code || t('project_no_code'))}</span>
          <span class="org-badge ${archived ? 'is-archived' : ''}">${projectStatusText(project.status)}</span>
        </div>
        <div class="project-card-name">${escapeHtml(project.name)}</div>
        <div class="project-card-desc">${escapeHtml(project.description || t('project_no_desc'))}</div>
        <div class="project-card-footer">
          <span class="project-card-role">${escapeHtml(t('project_my_role'))}: ${escapeHtml(project.my_role || (currentUser && currentUser.role === 'admin' ? t('role_admin') : '-'))}</span>
          <div class="project-card-actions">
            ${canDelete ? `<button class="btn btn-small btn-danger" type="button" data-project-delete="${project.id}">${t('project_delete')}</button>` : ''}
            <span class="btn btn-small ${archived ? '' : 'btn-primary'}">${t('project_enter')}</span>
          </div>
        </div>
      </article>`;
    })
    .join('');
  root.querySelectorAll('[data-project-id]').forEach((el) => {
    el.addEventListener('click', () => openProject(Number(el.dataset.projectId)));
  });
  root.querySelectorAll('[data-project-delete]').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.stopPropagation();
      deleteProject(Number(btn.dataset.projectDelete));
    });
  });
}

export async function loadProjectSidebar() {
  if (!currentUser) {
    projectsCache = [];
    activeProjectId = null;
    renderProjectSidebar();
    return;
  }
  try {
    const res = await authFetch('/api/projects');
    const data = await res.json();
    projectsCache = Array.isArray(data.projects) ? data.projects : [];
  } catch (e) {
    console.error(e);
    projectsCache = [];
  }
  if (activeProjectId && !projectsCache.some((p) => String(p.id) === String(activeProjectId))) {
    activeProjectId = null;
  }
  renderProjectSidebar();
  renderProjectsPage();
}

export async function restoreProjectView() {
  if (!currentUser) return;
  await loadProjectSidebar();
  const stored = getStoredScope();
  if (stored.project_id && projectsCache.some((p) => String(p.id) === String(stored.project_id))) {
    await openProject(stored.project_id, stored.line_id);
    return;
  }
  openProjectsPage();
}

export function openProjectsPage() {
  activeProjectId = null;
  projectWorkspace = null;
  setProjectScope(null, null);
  renderProjectSidebar();
  renderProjectsPage();
  switchTab('projects');
}

export async function openProject(projectId, lineId = null) {
  const project = projectsCache.find((p) => String(p.id) === String(projectId));
  if (!project) {
    notify(t('project_not_found'));
    return;
  }
  activeProjectId = Number(project.id);
  setProjectScope(activeProjectId, lineId);
  switchTab('project');
  const navProjects = document.querySelector('.nav-item[data-tab="projects"]');
  if (navProjects) navProjects.classList.add('active');
  const title = document.getElementById('projectTitle');
  if (title) title.textContent = project.name;
  const badge = document.getElementById('projectStatusBadge');
  if (badge) {
    badge.textContent = projectStatusText(project.status);
    badge.style.display = 'inline-block';
    badge.classList.toggle('is-archived', project.status === 'archived');
  }
  switchProjectTab('overview');
  await loadProjectWorkspace();
  renderProjectSidebar();
}

export async function loadProjectWorkspace() {
  if (!activeProjectId || !currentUser) return;
  try {
    const query =
      '/api/project_workspace?project_id=' +
      encodeURIComponent(activeProjectId) +
      (currentScope.line_id ? '&line_id=' + encodeURIComponent(currentScope.line_id) : '');
    const res = await authFetch(query);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      notify(err.details || err.error || t('project_load_failed'));
      if (res.status === 403 || res.status === 404) openProjectsPage();
      return;
    }
    projectWorkspace = await res.json();
    renderProjectHeader();
    renderOverview();
    renderLines();
    renderStationPlan(projectWorkspace);
    renderUploadStation();
    renderVideoLibrary();
    renderProjectSettings(projectWorkspace);
    if (currentProjectTab === 'detection') await loadVideoList();
    if (currentProjectTab === 'results') await loadResultList();
  } catch (e) {
    console.error(e);
    notify(t('project_load_failed'));
  }
}

function renderProjectHeader() {
  if (!projectWorkspace) return;
  const project = projectWorkspace.project || {};
  const title = document.getElementById('projectTitle');
  if (title) title.textContent = project.name || '';
  const badge = document.getElementById('projectStatusBadge');
  if (badge) {
    badge.textContent = projectStatusText(project.status);
    badge.style.display = 'inline-block';
    badge.classList.toggle('is-archived', project.status === 'archived');
  }
  const canManage = Boolean(projectWorkspace.can_manage);
  const settingsBtn = document.getElementById('btnProjectSettings');
  const settingsTab = document.getElementById('projectSettingsTab');
  if (settingsBtn) settingsBtn.style.display = canManage ? 'inline-block' : 'none';
  if (settingsTab) settingsTab.style.display = canManage ? 'inline-block' : 'none';
  const createLineBtn = document.getElementById('btnCreateProjectLine');
  if (createLineBtn) createLineBtn.style.display = canManage ? 'inline-flex' : 'none';
  if (!canManage && currentProjectTab === 'settings') switchProjectTab('overview');

  const currentLine = (projectWorkspace.lines || []).find(
    (line) => String(line.id) === String(currentScope.line_id)
  );
  const crumb = document.getElementById('projectLineCrumb');
  if (crumb) {
    crumb.textContent = currentLine ? `/ ${currentLine.name || ''}` : '';
    crumb.style.display = currentLine ? 'inline' : 'none';
  }

  const lineSelect = document.getElementById('projectLineSelect');
  if (lineSelect) {
    const lines = projectWorkspace.lines || [];
    lineSelect.innerHTML =
      `<option value="">${t('project_all_lines')}</option>` +
      lines
        .map((line) => `<option value="${line.id}">${escapeHtml(line.name)}</option>`)
        .join('');
    const lineId = currentScope.line_id;
    if (lineId && lines.some((line) => String(line.id) === String(lineId))) {
      lineSelect.value = String(lineId);
    } else {
      if (lineId) setScopeLine(null);
      lineSelect.value = '';
    }
  }
}

function renderOverview() {
  if (!projectWorkspace) return;
  const stats = projectWorkspace.stats || {};
  const set = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = String(value ?? 0);
  };
  set('projectStatVideos', stats.video_count);
  set('projectStatTasks', stats.task_count);
  set('projectStatResults', stats.result_count);
  set('projectStatLines', stats.line_count);
  const running = document.getElementById('projectStatRunning');
  if (running) {
    const count = Number(stats.running_task_count || 0);
    running.textContent = count > 0 ? t('project_running_count', { count }) : t('project_running_none');
    running.classList.toggle('is-running', count > 0);
  }

  const videos = projectWorkspace.videos || [];
  const recentVideos = videos.slice(0, 5);
  const videoBody = document.getElementById('projectRecentVideos');
  const videoEmpty = document.getElementById('projectRecentVideosEmpty');
  if (videoBody) {
    videoBody.innerHTML = recentVideos
      .map(
        (video) => `<tr>
          <td class="table-main">${escapeHtml(video.filename)}</td>
          <td>${escapeHtml(video.line_name || t('project_all_lines'))}</td>
          <td>${formatTime(video.created_at)}</td>
          <td class="table-actions">
            <button class="btn btn-small" type="button" data-overview-detect="${escapeHtml(video.filename)}">${t('project_detect')}</button>
            ${
              video.latest_result
                ? `<button class="btn btn-small" type="button" data-overview-result="${escapeHtml(video.latest_result.md_path)}" data-overview-video="${escapeHtml(video.latest_result.video_copy_path || '')}">${t('project_view_result')}</button>`
                : ''
            }
          </td>
        </tr>`
      )
      .join('');
    if (videoEmpty) videoEmpty.style.display = recentVideos.length ? 'none' : 'block';
    bindOverviewActions(videoBody);
  }

  const results = projectWorkspace.results || [];
  const recentResults = results.slice(0, 5);
  const resultBody = document.getElementById('projectRecentResults');
  const resultEmpty = document.getElementById('projectRecentResultsEmpty');
  if (resultBody) {
    resultBody.innerHTML = recentResults
      .map(
        (result) => `<tr>
          <td class="table-main">${escapeHtml(result.display_name)}</td>
          <td>${escapeHtml(result.video_name || '-')}</td>
          <td>${formatTime(result.created_at)}</td>
          <td class="table-actions">
            <button class="btn btn-small" type="button" data-overview-result="${escapeHtml(result.md_path)}" data-overview-video="${escapeHtml(result.video_copy_path || '')}">${t('project_view_result')}</button>
          </td>
        </tr>`
      )
      .join('');
    if (resultEmpty) resultEmpty.style.display = recentResults.length ? 'none' : 'block';
    bindOverviewActions(resultBody);
  }

  const runningPanel = document.getElementById('projectRunningPanel');
  const runningBody = document.getElementById('projectRunningBody');
  const runningTasks = (projectWorkspace.tasks || []).filter(
    (task) => task.status === 'running' || task.status === 'pending'
  );
  if (runningPanel && runningBody) {
    runningPanel.style.display = runningTasks.length ? 'block' : 'none';
    runningBody.innerHTML = runningTasks
      .map(
        (task) => `<div class="project-running-row">
          <span class="pill pill-warning">${taskStatusText(task.status)}</span>
          <span class="table-main">${escapeHtml(task.username || '')}</span>
          <span>${escapeHtml(task.phase || '')}</span>
          <span>${formatTime(task.created_at)}</span>
        </div>`
      )
      .join('');
  }
}

function bindOverviewActions(root) {
  if (!root) return;
  root.querySelectorAll('[data-overview-detect]').forEach((btn) => {
    btn.addEventListener('click', () => startDetectionForVideo(btn.dataset.overviewDetect));
  });
  root.querySelectorAll('[data-overview-result]').forEach((btn) => {
    btn.addEventListener('click', () =>
      openResult(btn.dataset.overviewResult, btn.dataset.overviewVideo)
    );
  });
}

function renderVideoLibrary() {
  if (!projectWorkspace) return;
  const body = document.getElementById('projectVideoBody');
  const empty = document.getElementById('projectVideoEmpty');
  const count = document.getElementById('projectVideoCount');
  const search = document.getElementById('projectVideoSearch');
  if (!body) return;
  const keyword = String(search ? search.value : '').trim().toLowerCase();
  const videos = (projectWorkspace.videos || []).filter((video) =>
    keyword ? String(video.filename || '').toLowerCase().includes(keyword) : true
  );
  if (count) count.textContent = String(videos.length);
  if (empty) empty.style.display = videos.length ? 'none' : 'block';

  body.innerHTML = videos
    .map(
      (video) => `<tr>
        <td class="table-main">${escapeHtml(video.filename)}</td>
        <td>${escapeHtml(video.line_name || t('project_all_lines'))}</td>
        <td>${escapeHtml(video.station_name || '-')}</td>
        <td>${formatDuration(video.duration_sec)}</td>
        <td>${escapeHtml(video.uploaded_by || '-')}</td>
        <td>${formatTime(video.created_at)}</td>
        <td>${resultStatusForVideo(video)}</td>
        <td class="table-actions">
          <button class="btn btn-small" type="button" data-video-detect="${escapeHtml(video.filename)}">${t('project_detect')}</button>
          ${
            video.latest_result
              ? `<button class="btn btn-small" type="button" data-video-result="${escapeHtml(video.latest_result.md_path)}" data-video-result-video="${escapeHtml(video.latest_result.video_copy_path || '')}">${t('project_view_result')}</button>`
              : ''
          }
        </td>
      </tr>`
    )
    .join('');

  body.querySelectorAll('[data-video-detect]').forEach((btn) => {
    btn.addEventListener('click', () => startDetectionForVideo(btn.dataset.videoDetect));
  });
  body.querySelectorAll('[data-video-result]').forEach((btn) => {
    btn.addEventListener('click', () =>
      openResult(btn.dataset.videoResult, btn.dataset.videoResultVideo)
    );
  });
}

function renderLines() {
  const grid = document.getElementById('projectLinesGrid');
  if (!grid || !projectWorkspace) return;
  const lines = projectWorkspace.lines || [];
  const canManage = Boolean(projectWorkspace.can_manage);
  const count = document.getElementById('projectLineCount');
  if (count) count.textContent = String(lines.length);
  const empty = document.getElementById('projectLinesEmpty');
  if (empty) empty.style.display = lines.length ? 'none' : 'block';
  const exitBtn = document.getElementById('btnExitLine');
  if (exitBtn) exitBtn.style.display = currentScope.line_id ? 'inline-flex' : 'none';

  if (!lines.length) {
    grid.innerHTML = '';
    return;
  }

  grid.innerHTML = lines
    .map((line) => {
      const active = String(line.id) === String(currentScope.line_id);
      const stats = line.stats || {};
      return `<article class="line-card ${active ? 'is-active' : ''}" data-line-id="${line.id}">
        <div class="line-card-top">
          <span class="line-card-code">${escapeHtml(line.code || '')}</span>
          <span class="org-badge">${projectStatusText(line.status)}</span>
        </div>
        <div class="line-card-name">${escapeHtml(line.name || '')}</div>
        <div class="line-card-desc">${escapeHtml(line.process_desc || t('project_no_desc'))}</div>
        <div class="line-card-stats">
          <span>${t('project_line_videos', { count: Number(stats.video_count || 0) })}</span>
          <span>${t('project_line_results', { count: Number(stats.result_count || 0) })}</span>
          <span>${t('project_line_tasks', { count: Number(stats.task_count || 0) })}</span>
          <span>${t('project_line_stations', { count: Number(stats.station_count || 0) })}</span>
        </div>
        <div class="line-card-actions">
          <button class="btn btn-small ${active ? '' : 'btn-primary'}" type="button" data-line-enter="${line.id}">${active ? t('project_line_current') : t('project_line_enter')}</button>
          ${canManage ? `<button class="btn btn-small" type="button" data-line-edit="${line.id}">${t('edit')}</button>` : ''}
          ${canManage ? `<button class="btn btn-small btn-danger" type="button" data-line-delete="${line.id}">${t('project_line_delete')}</button>` : ''}
        </div>
      </article>`;
    })
    .join('');

  grid.querySelectorAll('[data-line-enter]').forEach((btn) => {
    btn.addEventListener('click', () => enterLine(Number(btn.dataset.lineEnter)));
  });
  grid.querySelectorAll('[data-line-edit]').forEach((btn) => {
    btn.addEventListener('click', () => openLineModal(Number(btn.dataset.lineEdit)));
  });
  grid.querySelectorAll('[data-line-delete]').forEach((btn) => {
    btn.addEventListener('click', () => deleteLine(Number(btn.dataset.lineDelete)));
  });
}

function renderUploadStation() {
  const wrapper = document.getElementById('uploadStationWrapper');
  const select = document.getElementById('uploadStationSelect');
  if (!wrapper || !select) return;
  const stations = currentScope.line_id ? projectWorkspace?.stations || [] : [];
  if (!stations.length) {
    wrapper.style.display = 'none';
    select.innerHTML = '';
    if (currentScope.station_id) setScopeStation(null);
    return;
  }
  wrapper.style.display = 'block';
  const selected = currentScope.station_id;
  select.innerHTML =
    `<option value="">${t('station_select_placeholder')}</option>` +
    stations
      .map(
        (station) =>
          `<option value="${station.id}">${escapeHtml(station.name || station.code || '')}</option>`
      )
      .join('');
  if (selected && stations.some((station) => String(station.id) === String(selected))) {
    select.value = String(selected);
  } else {
    select.value = '';
    if (selected) setScopeStation(null);
  }
}

export async function enterLine(lineId) {
  const line = (projectWorkspace?.lines || []).find(
    (item) => String(item.id) === String(lineId)
  );
  if (!line) {
    notify(t('project_line_not_found'));
    return;
  }
  setScopeLine(line.id);
  switchProjectTab('videos');
  await loadProjectWorkspace();
}

export async function exitLine() {
  setScopeLine(null);
  await loadProjectWorkspace();
  switchProjectTab('lines');
}

async function deleteProject(projectId) {
  const project = projectsCache.find((item) => String(item.id) === String(projectId));
  if (!project) return;
  if (!window.confirm(t('project_delete_confirm', { name: project.name || '' }))) return;
  try {
    const res = await authFetch('/api/projects/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: Number(projectId) })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      notify(data.details || data.error || t('project_delete_failed'));
      return;
    }
    if (String(activeProjectId) === String(projectId)) {
      openProjectsPage();
    } else {
      await loadProjectSidebar();
    }
    notify(t('project_deleted'));
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  }
}

async function deleteLine(lineId) {
  const line = (projectWorkspace?.lines || []).find(
    (item) => String(item.id) === String(lineId)
  );
  if (!line) return;
  if (!window.confirm(t('project_line_delete_confirm', { name: line.name || '' }))) return;
  try {
    const res = await authFetch('/api/lines/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ line_id: Number(lineId) })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      notify(data.details || data.error || t('project_line_delete_failed'));
      return;
    }
    if (String(currentScope.line_id) === String(lineId)) setScopeLine(null);
    await loadProjectWorkspace();
    notify(t('project_line_deleted'));
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  }
}

export async function startDetectionForVideo(filename) {
  switchProjectTab('detection');
  const sel = document.getElementById('detectVideoSelect');
  if (!sel) return;
  const value = 'data/' + filename;
  const exists = Array.from(sel.options || []).some((opt) => opt.value === value);
  if (!exists) await loadVideoList();
  sel.value = value;
  sel.dispatchEvent(new Event('change'));
}

export async function openResult(resultPath, videoPath = '') {
  switchProjectTab('results');
  await loadResultList();
  const resSel = document.getElementById('reviewResultSelect');
  const vidSel = document.getElementById('reviewVideoSelect');
  if (!resSel) return;
  if (videoPath && vidSel && Array.from(vidSel.options).some((opt) => opt.value === videoPath)) {
    vidSel.value = videoPath;
    vidSel.dispatchEvent(new Event('change'));
  }
  if (resultPath && Array.from(resSel.options).some((opt) => opt.value === resultPath)) {
    resSel.value = resultPath;
    resSel.dispatchEvent(new Event('change'));
  }
}

export function switchProjectTab(tab) {
  if (!activeProjectId) return;
  const canManage = Boolean(projectWorkspace && projectWorkspace.can_manage);
  if (tab === 'settings' && !canManage) tab = 'overview';
  currentProjectTab = tab;
  document.querySelectorAll('.project-tab').forEach((el) => {
    el.classList.toggle('active', el.dataset.projectTab === tab);
  });
  document.querySelectorAll('.project-panel').forEach((el) => {
    el.classList.toggle('active', el.id === 'project-panel-' + tab);
  });
  document.body.classList.remove('sidebar-drawer-open');
  if (tab === 'detection') loadVideoList();
  if (tab === 'results') loadResultList();
  if (tab === 'videos') renderVideoLibrary();
  if (tab === 'lines') renderLines();
}

export async function refreshProjectWorkspace() {
  await loadProjectWorkspace();
}

export function refreshProjectLanguage() {
  renderProjectSidebar();
  const projectsView = document.getElementById('view-projects');
  if (projectsView && projectsView.classList.contains('active')) renderProjectsPage();
  if (activeProjectId && projectWorkspace) {
    renderProjectHeader();
    renderOverview();
    renderLines();
    renderStationPlan(projectWorkspace);
    renderUploadStation();
    renderVideoLibrary();
    renderProjectSettings(projectWorkspace);
  }
}

export function setupProjectUI() {
  const projectToggle = document.getElementById('sidebarProjectToggle');
  if (projectToggle) {
    projectToggle.addEventListener('click', (event) => {
      event.stopPropagation();
      setProjectsExpanded(!projectsExpanded);
    });
  }
  applyProjectTreeState();
  const refreshBtn = document.getElementById('btnRefreshProject');
  if (refreshBtn) refreshBtn.addEventListener('click', () => refreshProjectWorkspace());
  const settingsBtn = document.getElementById('btnProjectSettings');
  if (settingsBtn) settingsBtn.addEventListener('click', () => switchProjectTab('settings'));
  const lineSelect = document.getElementById('projectLineSelect');
  if (lineSelect) {
    lineSelect.addEventListener('change', async () => {
      setScopeLine(lineSelect.value ? Number(lineSelect.value) : null);
      await loadProjectWorkspace();
    });
  }
  const search = document.getElementById('projectVideoSearch');
  if (search) search.addEventListener('input', renderVideoLibrary);
  const createLineBtn = document.getElementById('btnCreateProjectLine');
  if (createLineBtn) createLineBtn.addEventListener('click', () => openLineModal(null));
  const exitLineBtn = document.getElementById('btnExitLine');
  if (exitLineBtn) exitLineBtn.addEventListener('click', exitLine);
  const uploadStationSelect = document.getElementById('uploadStationSelect');
  if (uploadStationSelect) {
    uploadStationSelect.addEventListener('change', () => {
      setScopeStation(uploadStationSelect.value ? Number(uploadStationSelect.value) : null);
      renderStationPlan(projectWorkspace);
    });
  }
  setupStationPlanUI();
  setupProjectSettingsUI();

  window.openProjectsPage = openProjectsPage;
  window.openProject = openProject;
  window.switchProjectTab = switchProjectTab;
  window.enterLine = enterLine;
  window.exitLine = exitLine;
  window.startDetectionForVideo = startDetectionForVideo;
  window.openResult = openResult;
  window.refreshProjectWorkspace = refreshProjectWorkspace;
  window.loadProjectSidebar = loadProjectSidebar;
  window.restoreProjectView = restoreProjectView;
  window.renderProjectsPage = renderProjectsPage;
  window.refreshProjectLanguage = refreshProjectLanguage;
}
