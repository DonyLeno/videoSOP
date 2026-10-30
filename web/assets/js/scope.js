// 项目作用域：UI 以项目为核心后，currentScope 表示“当前项目 + 可选产线 + 可选工位”。
export let currentScope = { project_id: null, line_id: null, station_id: null };

const PROJECT_KEY = 'active_project_id';
const LINE_KEY = 'active_line_id';
const STATION_KEY = 'active_station_id';

function persist() {
  try {
    localStorage.setItem(PROJECT_KEY, currentScope.project_id ? String(currentScope.project_id) : '');
    localStorage.setItem(LINE_KEY, currentScope.line_id ? String(currentScope.line_id) : '');
    localStorage.setItem(STATION_KEY, currentScope.station_id ? String(currentScope.station_id) : '');
  } catch (_) {
    // localStorage 不可用时仅保留内存状态
  }
}

export function scopeQueryString() {
  const parts = [];
  if (currentScope.project_id) parts.push('project_id=' + encodeURIComponent(currentScope.project_id));
  if (currentScope.line_id) parts.push('line_id=' + encodeURIComponent(currentScope.line_id));
  if (currentScope.station_id) parts.push('station_id=' + encodeURIComponent(currentScope.station_id));
  return parts.length ? '?' + parts.join('&') : '';
}

export function setProjectScope(projectId, lineId = null) {
  const pid = parseInt(projectId, 10) || null;
  const lid = lineId ? parseInt(lineId, 10) || null : null;
  currentScope = { project_id: pid, line_id: lid, station_id: null };
  persist();
}

export function setScopeLine(lineId, stationId = null) {
  currentScope.line_id = lineId ? parseInt(lineId, 10) || null : null;
  currentScope.station_id = stationId ? parseInt(stationId, 10) || null : null;
  persist();
}

export function setScopeStation(stationId) {
  currentScope.station_id = stationId ? parseInt(stationId, 10) || null : null;
  persist();
}

export function clearScope() {
  currentScope = { project_id: null, line_id: null, station_id: null };
  persist();
}

export function getStoredScope() {
  try {
    const pid = parseInt(localStorage.getItem(PROJECT_KEY) || '', 10) || null;
    const lid = parseInt(localStorage.getItem(LINE_KEY) || '', 10) || null;
    const sid = parseInt(localStorage.getItem(STATION_KEY) || '', 10) || null;
    return { project_id: pid, line_id: lid, station_id: sid };
  } catch (_) {
    return { project_id: null, line_id: null, station_id: null };
  }
}
