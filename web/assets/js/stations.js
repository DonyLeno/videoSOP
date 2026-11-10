// 产线内工位 2.5D 平面示意图：新增、拖动定位、删除、双击编辑。
import { authFetch, getToken, notify, withMediaToken } from './core.js';
import { t } from './i18n.js';
import { currentScope, setScopeStation } from './scope.js';

const C = Math.cos(Math.PI / 6);
const K = 0.5 * 0.9;
const SCALE = 3.4;
const OX = 410;
const OY = 150;
const TILE_MAX_W = 16;
const TILE_RATIO = 14 / 16;
const EXTRUDE = 9;
const FLOOR = 100;
const LINE_SPAN = 72;

let stationsCache = [];
let videosCache = [];
let canManage = false;
let selectedId = null;
let bound = false;
let dragState = null;
let editingId = null;

function iso(x, y, z = 0) {
  return {
    x: OX + (x - y) * C * SCALE,
    y: OY + (x + y) * K * SCALE - z
  };
}

function points(list) {
  return list.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
}

function clampPlane(value) {
  return Math.min(Math.max(value, 0), FLOOR);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function buildFloor() {
  const corners = [
    iso(0, 0),
    iso(FLOOR, 0),
    iso(FLOOR, FLOOR),
    iso(0, FLOOR)
  ];
  const lines = [];
  for (let v = 0; v <= FLOOR; v += 10) {
    const a = iso(v, 0);
    const b = iso(v, FLOOR);
    lines.push(`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" class="station-grid-line" />`);
    const c = iso(0, v);
    const d = iso(FLOOR, v);
    lines.push(`<line x1="${c.x}" y1="${c.y}" x2="${d.x}" y2="${d.y}" class="station-grid-line" />`);
  }
  return `<g class="station-floor">
    <polygon points="${points(corners)}" class="station-floor-fill" />
    ${lines.join('')}
    <polygon points="${points(corners)}" class="station-floor-outline" />
  </g>`;
}

function tileMetrics() {
  const count = Math.max(1, stationsCache.length);
  const step = count > 1 ? LINE_SPAN / (count - 1) : TILE_MAX_W;
  const width = Math.min(TILE_MAX_W, Math.max(5, step * 0.9));
  return { width, height: width * TILE_RATIO };
}

function buildStation(station) {
  const { width, height } = tileMetrics();
  const x = clampPlane(Number(station.pos_x) || 0);
  const y = clampPlane(Number(station.pos_y) || 0);
  const x2 = clampPlane(x + width);
  const y2 = clampPlane(y + height);
  const top = [
    iso(x2, y, EXTRUDE),
    iso(x2, y2, EXTRUDE),
    iso(x, y2, EXTRUDE),
    iso(x, y, EXTRUDE)
  ];
  const right = [iso(x2, y, EXTRUDE), iso(x2, y2, EXTRUDE), iso(x2, y2, 0), iso(x2, y, 0)];
  const front = [iso(x2, y2, EXTRUDE), iso(x, y2, EXTRUDE), iso(x, y2, 0), iso(x2, y2, 0)];
  const label = iso(x + (x2 - x) / 2, y + (y2 - y) / 2, EXTRUDE + 4);
  const active = String(station.id) === String(selectedId) ? ' is-selected' : '';
  const videoCount = Number(station.video_count || 0);
  return `<g class="station-node${active}" data-station-id="${station.id}" tabindex="0" role="button">
    <title>${escapeHtml(station.name || '')} (${escapeHtml(station.code || '')}) · ${t('station_video_count', { count: videoCount })}</title>
    <polygon points="${points(right)}" class="station-side station-side-right" />
    <polygon points="${points(front)}" class="station-side station-side-front" />
    <polygon points="${points(top)}" class="station-top" />
    <text x="${label.x}" y="${label.y - 6}" text-anchor="middle" class="station-label">${escapeHtml(station.name || '')}</text>
    <text x="${label.x}" y="${label.y + 8}" text-anchor="middle" class="station-sub">${t('station_video_count', { count: videoCount })}</text>
  </g>`;
}

function draw() {
  const svg = document.getElementById('stationPlanSvg');
  if (!svg) return;
  const sorted = stationsCache
    .slice()
    .sort((a, b) => Number(a.pos_x) + Number(a.pos_y) - (Number(b.pos_x) + Number(b.pos_y)));
  svg.innerHTML = buildFloor() + sorted.map(buildStation).join('');
  const count = document.getElementById('stationPlanCount');
  if (count) count.textContent = String(stationsCache.length);
  const empty = document.getElementById('stationPlanEmpty');
  if (empty) empty.style.display = stationsCache.length ? 'none' : 'block';
  const delBtn = document.getElementById('btnDeleteStation');
  if (delBtn) delBtn.disabled = !canManage || !selectedId;
  const editBtn = document.getElementById('btnEditStation');
  if (editBtn) editBtn.disabled = !canManage || !selectedId;
  const addBtn = document.getElementById('btnAddStation');
  if (addBtn) addBtn.disabled = !canManage;
}

export function renderStationPlan(workspace) {
  const panel = document.getElementById('stationPlanPanel');
  const svg = document.getElementById('stationPlanSvg');
  if (!panel || !svg) return;
  const scoped = Boolean(currentScope.line_id);
  panel.style.display = scoped ? 'block' : 'none';
  if (!scoped) {
    stationsCache = [];
    videosCache = [];
    selectedId = null;
    svg.innerHTML = '';
    return;
  }
  stationsCache = Array.isArray(workspace?.stations) ? workspace.stations.slice() : [];
  videosCache = Array.isArray(workspace?.videos) ? workspace.videos.slice() : [];
  canManage = Boolean(workspace?.can_manage);
  if (
    selectedId &&
    !stationsCache.some((station) => String(station.id) === String(selectedId))
  ) {
    selectedId = null;
  }
  if (
    editingId &&
    !stationsCache.some((station) => String(station.id) === String(editingId))
  ) {
    closeStationEdit();
  }
  if (!selectedId && currentScope.station_id) {
    const matched = stationsCache.some(
      (station) => String(station.id) === String(currentScope.station_id)
    );
    if (matched) selectedId = Number(currentScope.station_id);
    else setScopeStation(null);
  }
  draw();
}

function syncUploadSelect() {
  const select = document.getElementById('uploadStationSelect');
  if (select) select.value = selectedId ? String(selectedId) : '';
}

function selectStation(stationId) {
  const nextId = stationId ? Number(stationId) : null;
  // 选中项未变化时不重绘，避免双击时第一次点击销毁节点导致 dblclick 丢失
  if (String(nextId) === String(selectedId)) return;
  selectedId = nextId;
  if (selectedId) setScopeStation(selectedId);
  else setScopeStation(null);
  syncUploadSelect();
  draw();
}

function localPoint(svg, event) {
  const pt = svg.createSVGPoint();
  pt.x = event.clientX;
  pt.y = event.clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return { x: 0, y: 0 };
  const local = pt.matrixTransform(ctm.inverse());
  return { x: local.x, y: local.y };
}

async function persistPosition(station) {
  try {
    const res = await authFetch('/api/stations/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        station_id: station.id,
        pos_x: Number(station.pos_x),
        pos_y: Number(station.pos_y)
      })
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      notify(data.details || data.detail || data.error || t('station_move_failed'));
      await window.refreshProjectWorkspace?.();
    }
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  }
}

function handlePointerDown(event) {
  const svg = document.getElementById('stationPlanSvg');
  const node = event.target.closest ? event.target.closest('[data-station-id]') : null;
  if (!svg) return;
  if (!node) {
    if (selectedId) selectStation(null);
    return;
  }
  const stationId = Number(node.dataset.stationId);
  const station = stationsCache.find((item) => String(item.id) === String(stationId));
  if (!station) return;
  selectStation(stationId);
  if (!canManage) return;
  // 不在这里 preventDefault，避免浏览器抑制后续 mouse/dblclick 事件
  const start = localPoint(svg, event);
  dragState = {
    station,
    startLocal: start,
    startX: Number(station.pos_x) || 0,
    startY: Number(station.pos_y) || 0,
    moved: false
  };
  if (svg.setPointerCapture) {
    try {
      svg.setPointerCapture(event.pointerId);
    } catch (_) {
      // 忽略指针捕获失败
    }
  }
}

function handlePointerMove(event) {
  const svg = document.getElementById('stationPlanSvg');
  if (!dragState || !svg) return;
  event.preventDefault();
  const local = localPoint(svg, event);
  const dxSvg = local.x - dragState.startLocal.x;
  const dySvg = local.y - dragState.startLocal.y;
  if (Math.abs(dxSvg) + Math.abs(dySvg) > 2) dragState.moved = true;
  const dxPlane = (dxSvg / (C * SCALE) + dySvg / (K * SCALE)) / 2;
  const dyPlane = (dySvg / (K * SCALE) - dxSvg / (C * SCALE)) / 2;
  dragState.station.pos_x = Math.round(clampPlane(dragState.startX + dxPlane) * 10) / 10;
  dragState.station.pos_y = Math.round(clampPlane(dragState.startY + dyPlane) * 10) / 10;
  draw();
}

function handlePointerUp() {
  if (!dragState) return;
  const { station, moved } = dragState;
  dragState = null;
  if (moved) persistPosition(station);
}

async function addStation() {
  if (!currentScope.line_id) {
    notify(t('station_line_required'));
    return;
  }
  const btn = document.getElementById('btnAddStation');
  if (btn) btn.disabled = true;
  try {
    const res = await authFetch('/api/stations/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ line_id: Number(currentScope.line_id) })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      notify(data.details || data.detail || data.error || t('station_add_failed'));
      if (res.status === 401 || res.status === 403 || res.status === 404) {
        await window.refreshProjectWorkspace?.();
      }
      return;
    }
    selectedId = Number(data.station_id) || null;
    if (selectedId) {
      setScopeStation(selectedId);
      syncUploadSelect();
    }
    await window.refreshProjectWorkspace?.();
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function deleteStation() {
  if (!selectedId) {
    notify(t('station_select_required'));
    return;
  }
  const station = stationsCache.find((item) => String(item.id) === String(selectedId));
  if (!station) return;
  if (!window.confirm(t('station_delete_confirm', { name: station.name || '' }))) return;
  try {
    const res = await authFetch('/api/stations/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ station_id: selectedId })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      notify(data.details || data.error || t('station_delete_failed'));
      return;
    }
    selectedId = null;
    setScopeStation(null);
    syncUploadSelect();
    await window.refreshProjectWorkspace?.();
    notify(t('station_deleted'));
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  }
}

function formatVideoDuration(seconds) {
  const total = Number(seconds);
  if (!Number.isFinite(total) || total <= 0) return '-';
  const m = Math.floor(total / 60);
  const s = Math.floor(total % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function formatVideoSize(bytes) {
  const size = Number(bytes);
  if (!Number.isFinite(size) || size <= 0) return '-';
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function formatVideoTime(value) {
  const text = String(value || '');
  return text ? text.slice(0, 16) : '-';
}

function renderStationVideos(stationId) {
  const list = document.getElementById('stationVideoList');
  if (!list) return;
  const videos = videosCache
    .filter((video) => String(video.station_id) === String(stationId))
    .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
  if (!videos.length) {
    list.innerHTML = `<div class="station-video-empty">${escapeHtml(t('station_no_videos'))}</div>`;
    return;
  }
  list.innerHTML = videos
    .map(
      (video) => `<div class="station-video-item" data-video-id="${video.id}"
        data-video-path="${escapeHtml(video.stored_path || '')}"
        data-video-name="${escapeHtml(video.filename)}"
        title="${escapeHtml(t('station_video_play_hint'))}">
        <span class="station-video-name">${escapeHtml(video.filename)}</span>
        <span class="station-video-meta">${formatVideoDuration(video.duration_sec)} · ${formatVideoSize(video.size_bytes)} · ${escapeHtml(formatVideoTime(video.created_at))}</span>
        ${canManage ? `<button type="button" class="station-video-delete" data-video-delete="${video.id}" data-video-name="${escapeHtml(video.filename)}">${escapeHtml(t('delete'))}</button>` : ''}
      </div>`
    )
    .join('');
}

async function playStationVideo(videoId, path, name) {
  const modal = document.getElementById('stationVideoPreview');
  const player = document.getElementById('stationVideoPlayer');
  if (!modal || !player) return;
  const title = document.getElementById('stationVideoPreviewTitle');
  if (title) title.textContent = name || t('video_preview_title');
  modal.classList.add('open');
  player.removeAttribute('src');
  player.load();

  let playPath = path || '';
  if (videoId) {
    try {
      const res = await authFetch('/api/videos/ensure_playable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: videoId })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.path) playPath = data.path;
    } catch (e) {
      console.warn('[station-video] ensure_playable failed', e);
    }
  }
  if (!playPath) {
    notify(t('station_video_play_failed'));
    return;
  }
  player.src = withMediaToken('/' + String(playPath).replace(/^\/+/, ''));
  const started = player.play();
  if (started && typeof started.catch === 'function') started.catch(() => {});
}

function closeStationVideoPreview() {
  const modal = document.getElementById('stationVideoPreview');
  const player = document.getElementById('stationVideoPlayer');
  if (player) {
    player.pause();
    player.removeAttribute('src');
    player.load();
  }
  if (modal) modal.classList.remove('open');
}

async function deleteStationVideo(videoId, name) {
  if (!canManage || !videoId) return;
  if (!window.confirm(t('station_video_delete_confirm', { name: name || '' }))) return;
  try {
    const res = await authFetch('/api/videos/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      notify(data.details || data.error || t('station_video_delete_failed'));
      return;
    }
    notify(t('station_video_deleted'));
    await window.refreshProjectWorkspace?.();
    if (editingId) renderStationVideos(editingId);
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  }
}

function stationModal() {
  return document.getElementById('stationEditModal');
}

function resetStationUploadUI() {
  const bar = document.getElementById('stationUploadProgressBar');
  if (bar) bar.style.width = '0%';
  const status = document.getElementById('stationUploadStatus');
  if (status) status.textContent = '';
  const input = document.getElementById('stationVideoInput');
  if (input) input.value = '';
}

function openStationEdit(stationId) {
  const station = stationsCache.find((item) => String(item.id) === String(stationId));
  const modal = stationModal();
  if (!station || !modal) return;
  editingId = Number(station.id);
  const title = document.getElementById('stationEditTitle');
  if (title) title.textContent = t('station_edit_title');
  const nameInput = document.getElementById('stationNameInput');
  const descInput = document.getElementById('stationDescInput');
  const sopInput = document.getElementById('stationSopInput');
  if (nameInput) {
    nameInput.value = station.name || '';
    nameInput.disabled = !canManage;
  }
  if (descInput) {
    descInput.value = station.description || '';
    descInput.disabled = !canManage;
  }
  if (sopInput) {
    sopInput.value = station.sop_content || '';
    sopInput.disabled = !canManage;
  }
  const uploadGroup = document.getElementById('stationUploadGroup');
  if (uploadGroup) uploadGroup.style.display = canManage ? 'block' : 'none';
  const saveBtn = document.getElementById('btnSaveStation');
  if (saveBtn) saveBtn.style.display = canManage ? '' : 'none';
  resetStationUploadUI();
  renderStationVideos(editingId);
  modal.classList.add('open');
  if (canManage && nameInput) nameInput.focus();
}

function closeStationEdit() {
  const modal = stationModal();
  if (modal) modal.classList.remove('open');
  editingId = null;
  resetStationUploadUI();
}

async function saveStationEdit() {
  if (!editingId || !canManage) return;
  const nameInput = document.getElementById('stationNameInput');
  const descInput = document.getElementById('stationDescInput');
  const sopInput = document.getElementById('stationSopInput');
  const name = (nameInput?.value || '').trim();
  if (!name) {
    notify(t('station_name_required'));
    if (nameInput) nameInput.focus();
    return;
  }
  const saveBtn = document.getElementById('btnSaveStation');
  if (saveBtn) saveBtn.disabled = true;
  try {
    const res = await authFetch('/api/stations/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        station_id: editingId,
        name,
        description: descInput?.value || '',
        sop_content: sopInput?.value || ''
      })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      notify(data.details || data.detail || data.error || t('station_save_failed'));
      return;
    }
    closeStationEdit();
    notify(t('station_saved'));
    await window.refreshProjectWorkspace?.();
  } catch (e) {
    console.error(e);
    notify(t('network_error'));
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

function uploadStationVideo() {
  if (!canManage || !editingId) return;
  const input = document.getElementById('stationVideoInput');
  const file = input && input.files ? input.files[0] : null;
  if (!file) {
    notify(t('station_upload_select_file'));
    return;
  }
  const projectId = currentScope.project_id;
  const lineId = currentScope.line_id;
  if (!projectId || !lineId) {
    notify(t('station_line_required'));
    return;
  }
  const bar = document.getElementById('stationUploadProgressBar');
  const status = document.getElementById('stationUploadStatus');
  if (bar) bar.style.width = '0%';
  if (status) status.textContent = t('upload_in_progress');
  const xhr = new XMLHttpRequest();
  const query =
    '?project_id=' + encodeURIComponent(projectId) +
    '&line_id=' + encodeURIComponent(lineId) +
    '&station_id=' + encodeURIComponent(editingId);
  xhr.open('POST', '/api/upload' + query, true);
  const token = getToken();
  if (token) xhr.setRequestHeader('Authorization', 'Bearer ' + token);
  xhr.setRequestHeader('Content-Type', 'application/octet-stream');
  xhr.setRequestHeader('X-Filename', encodeURIComponent(file.name));
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable && bar) {
      bar.style.width = Math.round((event.loaded / event.total) * 100) + '%';
    }
  };
  xhr.onerror = () => {
    if (status) status.textContent = '';
    notify(t('upload_failed', { error: t('network_error') }));
  };
  xhr.onreadystatechange = async () => {
    if (xhr.readyState !== 4) return;
    if (xhr.status === 200) {
      if (bar) bar.style.width = '100%';
      if (status) status.textContent = t('upload_success');
      const inputEl = document.getElementById('stationVideoInput');
      if (inputEl) inputEl.value = '';
      notify(t('upload_success'));
      await window.refreshProjectWorkspace?.();
      if (editingId) renderStationVideos(editingId);
      return;
    }
    let message = 'HTTP ' + xhr.status;
    try {
      const data = JSON.parse(xhr.responseText || '{}');
      message = data.details || data.detail || data.error || message;
    } catch (_) {
      // 保持默认错误信息
    }
    if (status) status.textContent = '';
    notify(t('upload_failed', { error: message }));
  };
  xhr.send(file);
}

function resolveStationIdAt(event) {
  // 优先从事件目标向上查找；pointer capture 或覆盖层导致命不中时再按坐标兜底
  const target = event.target;
  let node = target && target.closest ? target.closest('[data-station-id]') : null;
  if (!node && typeof document.elementFromPoint === 'function') {
    const el = document.elementFromPoint(event.clientX, event.clientY);
    node = el && el.closest ? el.closest('[data-station-id]') : null;
  }
  return node ? Number(node.dataset.stationId) : null;
}

export function setupStationPlanUI() {
  if (bound) return;
  bound = true;
  const svg = document.getElementById('stationPlanSvg');
  if (svg) {
    svg.addEventListener('pointerdown', handlePointerDown);
    svg.addEventListener('pointermove', handlePointerMove);
    svg.addEventListener('pointerup', handlePointerUp);
    svg.addEventListener('pointercancel', handlePointerUp);
    // 兼容键盘操作与不触发 pointerdown 的点击（如自动化工具）。
    svg.addEventListener('click', (event) => {
      const node = event.target.closest ? event.target.closest('[data-station-id]') : null;
      if (node) selectStation(Number(node.dataset.stationId));
    });
    svg.addEventListener('dblclick', (event) => {
      const stationId = resolveStationIdAt(event);
      if (!stationId) return;
      event.preventDefault();
      selectStation(stationId);
      openStationEdit(stationId);
    });
    svg.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const node = event.target.closest ? event.target.closest('[data-station-id]') : null;
      if (!node) return;
      event.preventDefault();
      const stationId = Number(node.dataset.stationId);
      selectStation(stationId);
      if (event.key === 'Enter') openStationEdit(stationId);
    });
  }
  const addBtn = document.getElementById('btnAddStation');
  if (addBtn) addBtn.addEventListener('click', addStation);
  const editBtn = document.getElementById('btnEditStation');
  if (editBtn) {
    editBtn.addEventListener('click', () => {
      if (!selectedId) {
        notify(t('station_select_required'));
        return;
      }
      openStationEdit(selectedId);
    });
  }
  const delBtn = document.getElementById('btnDeleteStation');
  if (delBtn) delBtn.addEventListener('click', deleteStation);

  const modal = stationModal();
  if (modal) {
    // 挂到 body，避免被产线面板的层叠上下文裁剪
    if (modal.parentElement !== document.body) document.body.appendChild(modal);
    modal.addEventListener('click', (event) => {
      if (event.target === modal) closeStationEdit();
    });
  }
  const cancelBtn = document.getElementById('btnCancelStation');
  if (cancelBtn) cancelBtn.addEventListener('click', closeStationEdit);
  const saveBtn = document.getElementById('btnSaveStation');
  if (saveBtn) saveBtn.addEventListener('click', saveStationEdit);
  const fileInput = document.getElementById('stationVideoInput');
  if (fileInput) {
    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length) uploadStationVideo();
    });
  }
  const videoList = document.getElementById('stationVideoList');
  if (videoList) {
    videoList.addEventListener('dblclick', (event) => {
      if (event.target.closest('.station-video-delete')) return;
      const item = event.target.closest('.station-video-item');
      if (!item) return;
      playStationVideo(Number(item.dataset.videoId), item.dataset.videoPath, item.dataset.videoName);
    });
    videoList.addEventListener('click', (event) => {
      const delBtn = event.target.closest('[data-video-delete]');
      if (!delBtn) return;
      event.stopPropagation();
      deleteStationVideo(Number(delBtn.dataset.videoDelete), delBtn.dataset.videoName);
    });
  }
  const previewModal = document.getElementById('stationVideoPreview');
  if (previewModal) {
    if (previewModal.parentElement !== document.body) document.body.appendChild(previewModal);
    previewModal.addEventListener('click', (event) => {
      if (event.target === previewModal) closeStationVideoPreview();
    });
  }
  const closePreviewBtn = document.getElementById('btnCloseVideoPreview');
  if (closePreviewBtn) closePreviewBtn.addEventListener('click', closeStationVideoPreview);
  document.addEventListener('keydown', (event) => {
    const el = stationModal();
    if (event.key !== 'Escape') return;
    const preview = document.getElementById('stationVideoPreview');
    if (preview && preview.classList.contains('open')) {
      closeStationVideoPreview();
      return;
    }
    if (el && el.classList.contains('open')) closeStationEdit();
  });
}
