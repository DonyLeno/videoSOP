// 产线内工位 2.5D 平面示意图：新增、拖动定位、删除。
import { authFetch, notify } from './core.js';
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
let canManage = false;
let selectedId = null;
let bound = false;
let dragState = null;

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
    selectedId = null;
    svg.innerHTML = '';
    return;
  }
  stationsCache = Array.isArray(workspace?.stations) ? workspace.stations.slice() : [];
  canManage = Boolean(workspace?.can_manage);
  if (
    selectedId &&
    !stationsCache.some((station) => String(station.id) === String(selectedId))
  ) {
    selectedId = null;
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
  selectedId = stationId ? Number(stationId) : null;
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
  event.preventDefault();
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
    svg.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      const node = event.target.closest ? event.target.closest('[data-station-id]') : null;
      if (!node) return;
      event.preventDefault();
      selectStation(Number(node.dataset.stationId));
    });
  }
  const addBtn = document.getElementById('btnAddStation');
  if (addBtn) addBtn.addEventListener('click', addStation);
  const delBtn = document.getElementById('btnDeleteStation');
  if (delBtn) delBtn.addEventListener('click', deleteStation);
}
