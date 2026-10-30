import { currentLang, t } from './i18n.js';
import { authFetch, bindEnterToButton, getThemeColor, notify, withMediaToken } from './core.js';
import { scopeQueryString } from './scope.js';
import { refreshDynamicText } from './detection.js';


export let elVideo = null;
export let elActions = null;
export let elNowPlaying = null;
export let elActionCount = null;
export let elActiveAction = null;

export let currentActions = [];
export let currentActionEls = [];
export let activeIndex = -1;
export let currentJsonPath = '';
export let currentActionsHeaders = [];
export let actionCountOverride = null;
export let currentCycleSelection = null;

export let clipStartSec = null;
export let clipEndSec = null;
export let clipEnforcing = false;
export let elTimeline = null;
export let elTimelineSegments = null;
export let elTimelinePlayhead = null;
export let elTimelineHandles = null;
export let currentTimelineSegEls = [];
export let currentTimelineHandleEls = [];
export let isTimelineDragging = false;
export let timelinePointerId = null;
export let isBoundaryDragging = false;
export let boundaryPointerId = null;
export let draggingBoundary = null;

export let actionDurationColIndex = -1;
export let actionTimeColIndex = -1;
export let isSavingActions = false;

export function formatSecondsShort(sec) {
  const s = Number(sec);
  if (!Number.isFinite(s) || s < 0) return '-';
  const total = Math.floor(s);
  const hh = Math.floor(total / 3600);
  const mm = Math.floor((total % 3600) / 60);
  const ss = total % 60;
  const pad = (n) => String(n).padStart(2, '0');
  if (hh > 0) return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
  return `${pad(mm)}:${pad(ss)}`;
}

export function getClipBounds() {
  if (clipStartSec === null || clipEndSec === null) return null;
  const s = Number(clipStartSec);
  const e = Number(clipEndSec);
  if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) return null;
  return { start: s, end: e };
}

export function parseTimeFlexible(x) {
  let s = String(x || '').trim();
  if (!s) return NaN;
  s = s.replace(/[()（）]/g, '').trim();
  s = s.replace(/[^\d:.\-]/g, '');
  if (!s) return NaN;
  if (/^\d+(\.\d+)?$/.test(s)) return Number(s);
  const parts = s.split(':').map((p) => p.trim()).filter(Boolean);
  if (parts.length === 2) {
    const aStr = parts[0];
    const bStr = parts[1];
    const a = Number(aStr);
    if (!Number.isFinite(a)) return NaN;
    if (bStr.includes('.')) {
      const b = Number(bStr);
      if (!Number.isFinite(b)) return NaN;
      return a * 60 + b;
    }
    const b = Number(bStr);
    if (!Number.isFinite(b)) return NaN;
    if (a <= 2 && b >= 0 && b <= 59) return a * 60 + b;
    if (b >= 0 && b <= 99) return a + b / 100;
    return a * 60 + b;
  }
  if (parts.length === 3) {
    const h = Number(parts[0]);
    const m = Number(parts[1]);
    const sec = Number(parts[2]);
    if (!Number.isFinite(h) || !Number.isFinite(m) || !Number.isFinite(sec)) return NaN;
    return h * 3600 + m * 60 + sec;
  }
  return NaN;
}

export function parseStartEndFromTimeRange(text) {
  const tr = String(text || '').trim();
  if (!tr) return null;
  const normalized = tr.replace(/–|—|~|～|至|to/gi, '-');
  const parts = normalized.split('-').map((x) => x.trim()).filter(Boolean);
  if (parts.length >= 2) {
    const s = parseTimeFlexible(parts[0]);
    const e = parseTimeFlexible(parts[1]);
    if (Number.isFinite(s) && Number.isFinite(e) && e > s) return { s, e };
  }
  const tokens = tr.match(/\d+(?::\d+(?:\.\d+)?)?|\d+\.\d+/g) || [];
  if (tokens.length >= 2) {
    const s = parseTimeFlexible(tokens[0]);
    const e = parseTimeFlexible(tokens[1]);
    if (Number.isFinite(s) && Number.isFinite(e) && e > s) return { s, e };
  }
  return null;
}

export function normalizeActionTimeFields(act) {
  if (!act || typeof act !== 'object') return;
  let s = Number.parseFloat(act.start_time);
  let e = Number.parseFloat(act.end_time);
  if (!Number.isFinite(s)) s = parseTimeFlexible(act.start_time);
  if (!Number.isFinite(e)) e = parseTimeFlexible(act.end_time);
  if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
    const pair = parseStartEndFromTimeRange(act.time_range);
    if (pair) {
      s = pair.s;
      e = pair.e;
    }
  }
  if (Number.isFinite(s) && Number.isFinite(e) && e > s) {
    act.start_time = s;
    act.end_time = e;
  }
}

export function getActionsTimeRange(actions) {
  const list = Array.isArray(actions) ? actions : [];

  let minStart = Infinity;
  let maxEnd = -Infinity;
  for (const act of list) {
    let s = Number.parseFloat(act?.start_time);
    let e = Number.parseFloat(act?.end_time);
    if (!Number.isFinite(s)) s = parseTimeFlexible(act?.start_time);
    if (!Number.isFinite(e)) e = parseTimeFlexible(act?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
      const pair = parseStartEndFromTimeRange(act?.time_range);
      if (pair) {
        s = pair.s;
        e = pair.e;
      }
    }
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) continue;
    minStart = Math.min(minStart, s);
    maxEnd = Math.max(maxEnd, e);
  }
  if (!Number.isFinite(minStart) || !Number.isFinite(maxEnd) || maxEnd <= minStart) return null;
  return { start: Math.max(0, minStart), end: Math.max(0, maxEnd) };
}

export function computeCycleSelectionFromTable(headers, rows, actions) {
  const hs = Array.isArray(headers) ? headers : [];
  const rs = Array.isArray(rows) ? rows : [];
  const as = Array.isArray(actions) ? actions : [];
  if (!hs.length || !rs.length || !as.length) return null;

  const cycleColIndex = hs.findIndex((h) => /^(cycle|循环|週期)$/i.test(String(h || '').trim()));
  if (cycleColIndex < 0) return null;

  const seqColIndex = hs.findIndex((h) => /^(序号|编号|No\.?|Index)$/i.test(String(h || '').trim()));
  const normSeq = (v) => String(v ?? '').replace(/\D/g, '');

  const actionIndexBySeq = new Map();
  for (let i = 0; i < as.length; i++) {
    const seq = normSeq(as[i]?.index ?? i + 1);
    if (seq) actionIndexBySeq.set(seq, i);
  }

  const canIndexByRow = rs.length > 0 && rs.length === as.length;
  const byCycle = new Map();

  for (let rowIdx = 0; rowIdx < rs.length; rowIdx++) {
    const cells = Array.isArray(rs[rowIdx]) ? rs[rowIdx] : [];
    let cycleKey = String(cells[cycleColIndex] ?? '').trim();
    if (!cycleKey) cycleKey = '1';

    let actionIdx = -1;
    let seq = '';
    if (canIndexByRow) {
      actionIdx = rowIdx;
    } else {
      const seqCell =
        seqColIndex >= 0 && cells.length > seqColIndex ? cells[seqColIndex] : cells.length ? cells[0] : '';
      seq = normSeq(seqCell);
      const mapped = seq ? actionIndexBySeq.get(seq) : undefined;
      actionIdx = Number.isFinite(mapped) ? mapped : -1;
    }
    if (!Number.isFinite(actionIdx) || actionIdx < 0 || actionIdx >= as.length) continue;

    const act = as[actionIdx];
    if (act && typeof act === 'object') normalizeActionTimeFields(act);
    let s = Number.parseFloat(act?.start_time);
    let e = Number.parseFloat(act?.end_time);
    if (!Number.isFinite(s)) s = parseTimeFlexible(act?.start_time);
    if (!Number.isFinite(e)) e = parseTimeFlexible(act?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) continue;

    let st = byCycle.get(cycleKey);
    if (!st) {
      st = {
        min: Number.POSITIVE_INFINITY,
        max: Number.NEGATIVE_INFINITY,
        actionIdxSet: new Set(),
        seqSet: new Set()
      };
      byCycle.set(cycleKey, st);
    }
    st.min = Math.min(st.min, s);
    st.max = Math.max(st.max, e);
    st.actionIdxSet.add(actionIdx);
    if (!seq) seq = normSeq(act?.index);
    if (seq) st.seqSet.add(seq);
  }

  const durations = [];
  for (const [cycleKey, st] of byCycle.entries()) {
    if (Number.isFinite(st.min) && Number.isFinite(st.max) && st.max > st.min) {
      durations.push({ cycleKey, dur: st.max - st.min, st });
    }
  }
  if (!durations.length) return null;

  const cycleOne = durations.find((x) => normSeq(x.cycleKey) === '1');
  if (cycleOne) {
    return {
      cycleKey: cycleOne.cycleKey,
      range: { start: Math.max(0, cycleOne.st.min), end: Math.max(0, cycleOne.st.max) },
      actionIdxSet: cycleOne.st.actionIdxSet,
      seqSet: cycleOne.st.seqSet
    };
  }

  const mean = durations.reduce((sum, x) => sum + x.dur, 0) / durations.length;
  durations.sort((a, b) => {
    const da = Math.abs(a.dur - mean);
    const db = Math.abs(b.dur - mean);
    if (da !== db) return da - db;
    if (a.dur !== b.dur) return a.dur - b.dur;
    return String(a.cycleKey).localeCompare(String(b.cycleKey));
  });

  const best = durations[0];
  return {
    cycleKey: best.cycleKey,
    range: { start: Math.max(0, best.st.min), end: Math.max(0, best.st.max) },
    actionIdxSet: best.st.actionIdxSet,
    seqSet: best.st.seqSet
  };
}

export function setClipRange(startSec, endSec, { seek = true } = {}) {
  const s = Number(startSec);
  const e = Number(endSec);
  if (!Number.isFinite(s) || !Number.isFinite(e)) return false;
  if (e <= s) return false;
  clipStartSec = Math.max(0, s);
  clipEndSec = Math.max(0, e);
  updateTimelinePlayhead();
  if (seek && window.seekVideo) window.seekVideo(clipStartSec, { play: false });
  return true;
}

export function clearClipRange() {
  clipStartSec = null;
  clipEndSec = null;
  updateTimelinePlayhead();
}

export function updateActionComputedFields(act) {
  if (!act || typeof act !== 'object') return;
  const s = Number.parseFloat(act.start_time);
  const e = Number.parseFloat(act.end_time);
  if (!Number.isFinite(s) || !Number.isFinite(e)) return;
  const d = Math.max(0, e - s);
  act.duration = d.toFixed(1);
  act.time_range = `${s.toFixed(2)} - ${e.toFixed(2)}`;
}

export function updateActionRowTimeCells(index) {
  if (!Number.isFinite(index)) return;
  const row = currentActionEls[index];
  if (!row) return;
  const act = currentActions[index];
  if (!act) return;

  const children = row.children ? Array.from(row.children) : [];
  if (actionDurationColIndex >= 0 && children[actionDurationColIndex]) {
    const v = act.duration || '';
    children[actionDurationColIndex].textContent = v;
    children[actionDurationColIndex].title = v;
  }
  if (actionTimeColIndex >= 0 && children[actionTimeColIndex]) {
    const v = act.time_range || '';
    children[actionTimeColIndex].textContent = v;
    children[actionTimeColIndex].title = v;
  }
}

export async function persistActionsUpdate({ silentSuccess = false } = {}) {
  if (isSavingActions) return;
  const resultFile = currentJsonPath || document.getElementById('reviewResultSelect')?.value;
  if (!resultFile) {
    notify(t('result_not_found'));
    return;
  }

  isSavingActions = true;
  try {
    const res = await authFetch('/api/update_result', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ json_path: resultFile, actions: currentActions })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || t('unknown_error'));
    }
    const payload = await res.json().catch(() => ({}));
    const parsed = payload && payload.data ? payload.data : null;
    if (parsed && typeof parsed === 'object') {
      if (Array.isArray(parsed.actions)) currentActions = parsed.actions;
      if (parsed.actions_table && parsed.actions_table.headers && parsed.actions_table.rows) {
        renderActionsTable(parsed.actions_table, currentActions);
      } else {
        renderActions(currentActions);
      }
      refreshStationCompareChart();
      // 阶段 3：编辑可能改变动作区间，刷新缩略图（签名变化时后端自动重建）
      fetchResultThumbs(resultFile);
      renderVaNvaStats(currentActions);
      if (!silentSuccess) notify(t('save_success'));
      return;
    }
    refreshStationCompareChart();
    fetchResultThumbs(resultFile);
    renderVaNvaStats(currentActions);
    if (!silentSuccess) notify(t('save_success'));
  } catch (e) {
    notify(t('save_failed_with_error', { error: e.message }));
    console.error(e);
  } finally {
    isSavingActions = false;
  }
}

export function clampToClip(t) {
  const x = Number(t);
  if (!Number.isFinite(x)) return x;
  if (clipStartSec === null || clipEndSec === null) return x;
  return Math.min(Number(clipEndSec), Math.max(Number(clipStartSec), x));
}

export function enforceClipRange() {
  if (!elVideo) return;
  if (clipStartSec === null || clipEndSec === null) return;
  if (!Number.isFinite(clipStartSec) || !Number.isFinite(clipEndSec)) return;
  if (clipEnforcing) return;
  const s = Number(clipStartSec);
  const e = Number(clipEndSec);
  const t = Number(elVideo.currentTime);
  if (!Number.isFinite(t)) return;
  clipEnforcing = true;
  try {
    if (t < s) {
      elVideo.currentTime = s;
      return;
    }
    if (t > e) {
      try {
        elVideo.pause();
      } catch {}
      elVideo.currentTime = e;
    }
  } finally {
    clipEnforcing = false;
  }
}

export function updateTimelinePlayhead() {
  if (!elTimelinePlayhead) return;
  if (!elVideo) {
    elTimelinePlayhead.style.left = '0%';
    return;
  }

  const bounds = getClipBounds();
  if (!bounds) {
    elTimelinePlayhead.style.left = '0%';
    return;
  }

  const t = clampToClip(elVideo.currentTime);
  const denom = bounds.end - bounds.start;
  if (!(denom > 0)) {
    elTimelinePlayhead.style.left = '0%';
    return;
  }

  const pct = ((t - bounds.start) / denom) * 100;
  elTimelinePlayhead.style.left = Math.max(0, Math.min(100, pct)) + '%';
}

export function hashStringToHue(input) {
  const s = String(input || '');
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0;
  }
  return h % 360;
}

export function colorForAction(action, idx) {
  const base = (action && (action.label || action.therblig || action.value_added)) || '';
  const baseTrimmed = String(base || '').trim();
  const n = Number.isFinite(Number(idx)) ? Number(idx) : 0;
  const hue = baseTrimmed ? (hashStringToHue(`${baseTrimmed}#${n}`) + n * 47) % 360 : (n * 137.508) % 360;
  return `hsl(${hue}, 70%, 55%)`;
}

export function updateTimelineActive(index) {
  for (let i = 0; i < currentTimelineSegEls.length; i++) {
    const el = currentTimelineSegEls[i];
    if (!el) continue;
    if (i === index) el.classList.add('active');
    else el.classList.remove('active');
  }
}

export function renderActionTimeline(actions) {
  if (!elTimelineSegments) return;
  if (elTimeline && !elTimelineHandles) {
    elTimelineHandles = document.getElementById('actionTimelineHandles');
    if (!elTimelineHandles) {
      elTimelineHandles = document.createElement('div');
      elTimelineHandles.id = 'actionTimelineHandles';
      elTimelineHandles.className = 'action-timeline-handles';
      if (elTimelinePlayhead && elTimelinePlayhead.parentNode === elTimeline) {
        elTimeline.insertBefore(elTimelineHandles, elTimelinePlayhead);
      } else {
        elTimeline.appendChild(elTimelineHandles);
      }
    }
  }

  const list = Array.isArray(actions) ? actions : [];
  currentTimelineSegEls = [];
  currentTimelineHandleEls = [];
  elTimelineSegments.innerHTML = '';
  if (elTimelineHandles) elTimelineHandles.innerHTML = '';

  const range =
    currentCycleSelection &&
    currentCycleSelection.range &&
    Number.isFinite(currentCycleSelection.range.start) &&
    Number.isFinite(currentCycleSelection.range.end) &&
    currentCycleSelection.range.end > currentCycleSelection.range.start
      ? currentCycleSelection.range
      : getActionsTimeRange(list);
  if (!range) {
    clearClipRange();
    updateTimelinePlayhead();
    return;
  }

  const shouldSeek =
    !elVideo ||
    clipStartSec === null ||
    clipEndSec === null ||
    !Number.isFinite(elVideo.currentTime) ||
    elVideo.currentTime < range.start ||
    elVideo.currentTime > range.end;
  setClipRange(range.start, range.end, { seek: shouldSeek });

  const denom = range.end - range.start;
  if (!(denom > 0)) {
    updateTimelinePlayhead();
    return;
  }

  for (let idx = 0; idx < list.length; idx++) {
    const allow =
      currentCycleSelection && currentCycleSelection.actionIdxSet instanceof Set
        ? currentCycleSelection.actionIdxSet
        : null;
    if (allow && !allow.has(idx)) {
      currentTimelineSegEls.push(null);
      continue;
    }
    const act = list[idx];
    const s = Number.parseFloat(act?.start_time);
    const e = Number.parseFloat(act?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
      currentTimelineSegEls.push(null);
      continue;
    }

    const leftPct = ((Math.max(range.start, s) - range.start) / denom) * 100;
    const widthPct = ((Math.min(range.end, e) - Math.max(range.start, s)) / denom) * 100;
    if (!(widthPct > 0)) {
      currentTimelineSegEls.push(null);
      continue;
    }

    const seg = document.createElement('div');
    seg.className = 'action-timeline-segment';
    seg.dataset.index = String(idx);
    seg.style.left = leftPct + '%';
    seg.style.width = widthPct + '%';
    const segColor = colorForAction(act, idx);
    seg.style.background = segColor;
    seg.style.backgroundColor = segColor;
    const label = act?.label ? String(act.label) : '';
    seg.title = `${idx + 1} ${label} ${formatSecondsShort(s)} - ${formatSecondsShort(e)}`;
    elTimelineSegments.appendChild(seg);
    currentTimelineSegEls.push(seg);
  }

  if (elTimelineHandles) {
    const allow =
      currentCycleSelection && currentCycleSelection.actionIdxSet instanceof Set
        ? currentCycleSelection.actionIdxSet
        : null;
    const idxs = allow
      ? Array.from(allow)
          .map((x) => Number(x))
          .filter((x) => Number.isFinite(x) && x >= 0 && x < list.length)
          .sort((a, b) => a - b)
      : null;
    if (idxs && idxs.length >= 2) {
      for (let k = 0; k < idxs.length - 1; k++) {
        const leftIdx = idxs[k];
        const rightIdx = idxs[k + 1];
        const a = list[leftIdx];
        const b = list[rightIdx];
        const s1 = Number.parseFloat(a?.start_time);
        const e1 = Number.parseFloat(a?.end_time);
        const s2 = Number.parseFloat(b?.start_time);
        const e2 = Number.parseFloat(b?.end_time);
        if (!Number.isFinite(s1) || !Number.isFinite(e1) || !Number.isFinite(s2) || !Number.isFinite(e2)) continue;
        if (!(e1 > s1) || !(e2 > s2)) continue;
        const boundary = Number.isFinite(e1) ? e1 : s2;
        if (!Number.isFinite(boundary) || boundary <= range.start || boundary >= range.end) continue;

        const leftPct = ((boundary - range.start) / denom) * 100;
        const h = document.createElement('div');
        h.className = 'action-timeline-handle';
        h.dataset.leftIndex = String(leftIdx);
        h.dataset.rightIndex = String(rightIdx);
        h.style.left = leftPct + '%';
        h.title = `${leftIdx + 1} / ${rightIdx + 1} ${formatSecondsShort(boundary)}`;
        elTimelineHandles.appendChild(h);
        currentTimelineHandleEls.push(h);
      }
    } else {
      for (let i = 0; i < list.length - 1; i++) {
        const a = list[i];
        const b = list[i + 1];
        const s1 = Number.parseFloat(a?.start_time);
        const e1 = Number.parseFloat(a?.end_time);
        const s2 = Number.parseFloat(b?.start_time);
        const e2 = Number.parseFloat(b?.end_time);
        if (!Number.isFinite(s1) || !Number.isFinite(e1) || !Number.isFinite(s2) || !Number.isFinite(e2)) continue;
        if (!(e1 > s1) || !(e2 > s2)) continue;
        const boundary = Number.isFinite(e1) ? e1 : s2;
        if (!Number.isFinite(boundary) || boundary <= range.start || boundary >= range.end) continue;

        const leftPct = ((boundary - range.start) / denom) * 100;
        const h = document.createElement('div');
        h.className = 'action-timeline-handle';
        h.dataset.leftIndex = String(i);
        h.dataset.rightIndex = String(i + 1);
        h.style.left = leftPct + '%';
        h.title = `${i + 1} / ${i + 2} ${formatSecondsShort(boundary)}`;
        elTimelineHandles.appendChild(h);
        currentTimelineHandleEls.push(h);
      }
    }
  }

  updateTimelineActive(activeIndex);
  updateTimelinePlayhead();
}

export function seekFromTimelineClientX(clientX, { play } = {}) {
  if (!elTimeline || !elVideo || !window.seekVideo) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const rect = elTimeline.getBoundingClientRect();
  const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
  const pct = rect.width > 0 ? x / rect.width : 0;
  const t = bounds.start + pct * (bounds.end - bounds.start);
  const shouldPlay = typeof play === 'boolean' ? play : !elVideo.paused;
  window.seekVideo(t, { play: shouldPlay });
}

export function updateTimelineSegmentStyle(idx) {
  const seg = currentTimelineSegEls[idx];
  if (!seg) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const denom = bounds.end - bounds.start;
  if (!(denom > 0)) return;

  const act = currentActions[idx];
  const s = Number.parseFloat(act?.start_time);
  const e = Number.parseFloat(act?.end_time);
  if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) return;

  const leftPct = ((Math.max(bounds.start, s) - bounds.start) / denom) * 100;
  const widthPct = ((Math.min(bounds.end, e) - Math.max(bounds.start, s)) / denom) * 100;
  seg.style.left = leftPct + '%';
  seg.style.width = Math.max(0, widthPct) + '%';
  const segColor = colorForAction(act, idx);
  seg.style.background = segColor;
  seg.style.backgroundColor = segColor;
  const label = act?.label ? String(act.label) : '';
  seg.title = `${idx + 1} ${label} ${formatSecondsShort(s)} - ${formatSecondsShort(e)}`;
}

export function updateTimelineHandleStyle(handleEl, boundaryTime) {
  if (!handleEl) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const denom = bounds.end - bounds.start;
  if (!(denom > 0)) return;
  const pct = ((boundaryTime - bounds.start) / denom) * 100;
  handleEl.style.left = Math.max(0, Math.min(100, pct)) + '%';
  handleEl.title = `${Number(handleEl.dataset.leftIndex || 0) + 1} / ${
    Number(handleEl.dataset.rightIndex || 1) + 1
  } ${formatSecondsShort(boundaryTime)}`;
}

export function setBoundaryTime(leftIdx, rightIdx, boundaryTime) {
  const a = currentActions[leftIdx];
  const b = currentActions[rightIdx];
  if (!a || !b) return;

  a.end_time = boundaryTime;
  b.start_time = boundaryTime;
  updateActionComputedFields(a);
  updateActionComputedFields(b);
  updateActionRowTimeCells(leftIdx);
  updateActionRowTimeCells(rightIdx);
  updateTimelineSegmentStyle(leftIdx);
  updateTimelineSegmentStyle(rightIdx);
  updateTimelinePlayhead();
}

export function adjustBoundaryFromClientX(clientX) {
  if (!draggingBoundary || !elTimeline) return;
  const bounds = getClipBounds();
  if (!bounds) return;
  const rect = elTimeline.getBoundingClientRect();
  const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
  const pct = rect.width > 0 ? x / rect.width : 0;
  const raw = bounds.start + pct * (bounds.end - bounds.start);

  const leftIdx = draggingBoundary.leftIdx;
  const rightIdx = draggingBoundary.rightIdx;
  const a = currentActions[leftIdx];
  const b = currentActions[rightIdx];
  if (!a || !b) return;

  const aStart = Number.parseFloat(a.start_time);
  const bEnd = Number.parseFloat(b.end_time);
  if (!Number.isFinite(aStart) || !Number.isFinite(bEnd)) return;

  const minGap = 0.1;
  const minT = Math.max(bounds.start, aStart + minGap);
  const maxT = Math.min(bounds.end, bEnd - minGap);
  if (!(maxT > minT)) return;
  const t = Math.max(minT, Math.min(maxT, raw));

  setBoundaryTime(leftIdx, rightIdx, t);
  updateTimelineHandleStyle(draggingBoundary.el, t);
}

export async function loadResultList() {
  const resSel = document.getElementById('reviewResultSelect');
  const vidSel = document.getElementById('reviewVideoSelect');
  if (!resSel || !vidSel) return;
  try {
    const res = await authFetch('/api/list_results' + scopeQueryString());
    const data = await res.json();

    const oldRes = resSel.value;
    const oldVid = vidSel.value;

    resSel.innerHTML = `<option value="">${t('review_select_result')}</option>`;
    vidSel.innerHTML = `<option value="">${t('review_select_video')}</option>`;

    (data.files || []).forEach((f) => {
      const opt = document.createElement('option');
      opt.value = 'result/' + f;
      opt.textContent = f;
      if (f.endsWith('.json') || f.endsWith('.md')) resSel.appendChild(opt);
      else if (f.endsWith('.mp4')) vidSel.appendChild(opt.cloneNode(true));
    });

    if (oldRes) {
      resSel.value = oldRes;
      currentJsonPath = oldRes;
    }
    if (oldVid) vidSel.value = oldVid;
  } catch (e) {
    console.error(e);
  }
}

export function autoSelectResultByVideoPrefix(videoPath) {
  const resSel = document.getElementById('reviewResultSelect');
  if (!resSel) return;
  if (!videoPath) return;

  const videoFile = String(videoPath).split('/').pop() || '';
  const videoBase = videoFile.replace(/\.[^.]+$/, '');
  if (!videoBase) return;

  const targetPrefix = currentLang === 'en' ? 'en_' + videoBase : videoBase;

  let best = null;
  let bestScore = -1;
  let bestLen = -1;

  for (const opt of Array.from(resSel.options)) {
    const val = opt.value || '';
    if (!val || (!val.endsWith('.json') && !val.endsWith('.md'))) continue;
    const resFile = String(val).split('/').pop() || '';
    const resBase = resFile.replace(/\.[^.]+$/, '');
    if (!resBase) continue;

    let score = 0;

    // 1. Language match
    if (resBase === targetPrefix) score += 100;
    else if (resBase.startsWith(targetPrefix)) score += 50;

    // 2. Fallback match (Original logic components)
    if (resBase === videoBase) score += 20;
    else if (resBase.startsWith(videoBase)) score += 10;
    else if (videoBase.startsWith(resBase)) score += 5;

    // 3. File type preference
    if (val.endsWith('.md')) score += 2;

    if (score > 0) {
      if (score > bestScore) {
        bestScore = score;
        best = opt;
        bestLen = resBase.length;
      } else if (score === bestScore) {
        if (resBase.length > bestLen) {
          best = opt;
          bestLen = resBase.length;
        }
      }
    }
  }

  if (!best) {
    resSel.value = '';
    currentJsonPath = '';
    notify(t('no_matching_result', { name: videoFile }));
    return;
  }

  if (resSel.value !== best.value) {
    resSel.value = best.value;
    currentJsonPath = best.value;
    resSel.dispatchEvent(new Event('change'));
  }
}

export function renderMdView(data) {
  const md = document.getElementById('mdResultView');
  const legacy = document.getElementById('legacyStatsView');
  if (md) md.style.display = 'flex';
  if (legacy) legacy.style.display = 'none';

  if (md) md.style.display = 'grid';

  const escapeHtml = (s) =>
    String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const safeLink = (href) => {
    const u = String(href || '').trim();
    if (!u) return '';
    const lower = u.toLowerCase();
    if (lower.startsWith('javascript:') || lower.startsWith('data:')) return '';
    return u;
  };

  const mdToHtml = (input) => {
    const text = String(input || '');
    const lines = text.replace(/\r\n/g, '\n').split('\n');
    let out = '';
    let inCode = false;
    let codeBuf = [];
    let inUl = false;
    let inOl = false;
    let inBlockquote = false;
    const flushLists = () => {
      if (inUl) {
        out += '</ul>';
        inUl = false;
      }
      if (inOl) {
        out += '</ol>';
        inOl = false;
      }
    };
    const closeBlockquote = () => {
      if (inBlockquote) {
        out += '</blockquote>';
        inBlockquote = false;
      }
    };
    const inline = (s) => {
      let x = escapeHtml(s);
      x = x.replace(/`([^`]+)`/g, (_m, c) => `<code>${escapeHtml(c)}</code>`);
      x = x.replace(/\*\*([^*]+)\*\*/g, (_m, c) => `<strong>${escapeHtml(c)}</strong>`);
      x = x.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, txt, href) => {
        const safe = safeLink(href);
        if (!safe) return escapeHtml(txt);
        return `<a href="${escapeHtml(safe)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
          txt
        )}</a>`;
      });
      return x;
    };

    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      const line = raw.replace(/\t/g, '  ');

      if (line.trim().startsWith('```')) {
        if (!inCode) {
          flushLists();
          closeBlockquote();
          inCode = true;
          codeBuf = [];
        } else {
          const code = codeBuf.join('\n');
          out += `<pre><code>${escapeHtml(code)}</code></pre>`;
          inCode = false;
          codeBuf = [];
        }
        continue;
      }

      if (inCode) {
        codeBuf.push(raw);
        continue;
      }

      const trimmed = line.trim();
      if (!trimmed) {
        flushLists();
        closeBlockquote();
        continue;
      }

      if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
        flushLists();
        closeBlockquote();
        out += '<hr />';
        continue;
      }

      const bq = trimmed.startsWith('>') ? trimmed.replace(/^>\s?/, '') : null;
      if (bq !== null) {
        flushLists();
        if (!inBlockquote) {
          out += '<blockquote>';
          inBlockquote = true;
        }
        out += `<p>${inline(bq)}</p>`;
        continue;
      }
      closeBlockquote();

      const h = trimmed.match(/^(#{1,3})\s+(.*)$/);
      if (h) {
        flushLists();
        const level = h[1].length;
        out += `<h${level}>${inline(h[2])}</h${level}>`;
        continue;
      }

      const ol = trimmed.match(/^(\d+)\.\s+(.*)$/);
      if (ol) {
        if (inUl) {
          out += '</ul>';
          inUl = false;
        }
        if (!inOl) {
          out += '<ol>';
          inOl = true;
        }
        out += `<li>${inline(ol[2])}</li>`;
        continue;
      }

      const ul = trimmed.match(/^[-*]\s+(.*)$/);
      if (ul) {
        if (inOl) {
          out += '</ol>';
          inOl = false;
        }
        if (!inUl) {
          out += '<ul>';
          inUl = true;
        }
        out += `<li>${inline(ul[1])}</li>`;
        continue;
      }

      flushLists();
      out += `<p>${inline(trimmed)}</p>`;
    }

    if (inCode) {
      out += `<pre><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`;
    }
    flushLists();
    closeBlockquote();
    return out || `<p>${escapeHtml(t('no_content'))}</p>`;
  };

  const setMd = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = mdToHtml(value || t('no_content'));
  };
  setMd('mdOverview', data.overview || '');
  setMd('mdDeepDive', data.deep_dive || '');
  setMd('mdKaizen', data.kaizen || '');
}

export const STATION_COMPARE_MAX = 12;
export const stationCompareCache = new Map();
export const stationCompareVisibleByPath = new Map();
export let stationCompareLastItems = [];
export let stationCompareRenderSeq = 0;

export function _stationLabelFromPath(resultPath) {
  const file = String(resultPath || '').split('/').pop() || '';
  const base = file.replace(/\.[^.]+$/, '');
  const cleaned = base.replace(/_\d{2}\.\d{2}\.\d{2}\.\d{2}$/, '');
  return cleaned || base || file || String(resultPath || '');
}

export function _hashColor(key) {
  const s = String(key || 'unknown');
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  return `hsl(${hue} 65% 55%)`;
}

export function _isStationCompareVisible(path) {
  const key = String(path || '');
  if (!key) return true;
  const v = stationCompareVisibleByPath.get(key);
  return v !== false;
}

export function _renderStationCompareControls(items) {
  const root = document.getElementById('stationCompareControls');
  if (!root) return;
  root.innerHTML = '';

  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  if (list.length === 0) {
    root.style.display = 'none';
    return;
  }
  root.style.display = 'flex';

  for (const item of list) {
    const label = document.createElement('label');
    label.className = 'station-compare-toggle';
    label.title = item.label || '';

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = _isStationCompareVisible(item.path);
    input.addEventListener('change', () => {
      stationCompareVisibleByPath.set(String(item.path || ''), Boolean(input.checked));
      const filtered = (stationCompareLastItems || []).filter((x) => _isStationCompareVisible(x?.path));
      _renderStationCompareChart(filtered);
    });

    const span = document.createElement('span');
    span.textContent = item.label || '';

    label.appendChild(input);
    label.appendChild(span);
    root.appendChild(label);
  }
}

export function _normalizeActionsForCompare(actions) {
  const out = [];
  for (const raw of actions || []) {
    if (raw && typeof raw === 'object') normalizeActionTimeFields(raw);
    let s = Number.parseFloat(raw?.start_time);
    let e = Number.parseFloat(raw?.end_time);
    if (!Number.isFinite(s)) s = parseTimeFlexible(raw?.start_time);
    if (!Number.isFinite(e)) e = parseTimeFlexible(raw?.end_time);
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) {
      const pair = parseStartEndFromTimeRange(raw?.time_range);
      if (pair) {
        s = pair.s;
        e = pair.e;
      }
    }
    if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) continue;
    out.push({
      index: String(raw?.index ?? ''),
      label: String(raw?.label ?? ''),
      start: s,
      end: e
    });
  }
  out.sort((a, b) => a.start - b.start);
  return out;
}

export function _extractActionsFromResultDetails(data) {
  if (data && typeof data === 'object') {
    const isMd = data.overview !== undefined || data.deep_dive !== undefined || data.kaizen !== undefined;
    if (isMd) return Array.isArray(data.actions) ? data.actions : [];
    if (Array.isArray(data.actions)) return data.actions;
    if (data.model_output && Array.isArray(data.model_output.actions)) return data.model_output.actions;
    if (data.output && Array.isArray(data.output.actions)) return data.output.actions;
  }
  if (Array.isArray(data)) return data;
  return [];
}

export async function _fetchStationCompareItem(resultPath) {
  const key = String(resultPath || '');
  if (!key) return null;
  if (stationCompareCache.has(key)) return stationCompareCache.get(key);
  const apiUrl = '/api/result_details?path=' + encodeURIComponent(key) + '&ts=' + Date.now();
  const res = await authFetch(apiUrl);
  if (!res.ok) return null;
  const data = await res.json().catch(() => null);
  const actionsRaw = _extractActionsFromResultDetails(data);
  const table =
    data &&
    typeof data === 'object' &&
    data.actions_table &&
    Array.isArray(data.actions_table.headers) &&
    Array.isArray(data.actions_table.rows)
      ? data.actions_table
      : null;
  const sel = table ? computeCycleSelectionFromTable(table.headers, table.rows, actionsRaw) : null;
  const normSeq = (v) => String(v ?? '').replace(/\D/g, '');
  const actionsFiltered =
    sel && (sel.actionIdxSet instanceof Set || sel.seqSet instanceof Set)
      ? actionsRaw.filter((a, i) => {
          if (sel.actionIdxSet instanceof Set && sel.actionIdxSet.has(i)) return true;
          if (sel.seqSet instanceof Set) {
            const s = normSeq(a?.index);
            return s ? sel.seqSet.has(s) : false;
          }
          return false;
        })
      : actionsRaw;
  const actions = _normalizeActionsForCompare(actionsFiltered);
  const item = { path: key, label: _stationLabelFromPath(key), actions };
  stationCompareCache.set(key, item);
  return item;
}

export function _renderStationCompareChart(items) {
  const root = document.getElementById('stationCompareChart');
  if (!root) return;

  const chartHeight = 420;
  const list = Array.isArray(items) ? items.filter(Boolean) : [];
  const valid = list.filter((x) => Array.isArray(x.actions) && x.actions.length > 0);
  if (valid.length === 0) {
    root.innerHTML = `<div style="color: var(--muted); font-size: 13px;">${t('no_content')}</div>`;
    return;
  }

  const ranges = valid.map((x) => {
    const minS = x.actions.reduce((m, a) => Math.min(m, a.start), Number.POSITIVE_INFINITY);
    const maxE = x.actions.reduce((m, a) => Math.max(m, a.end), 0);
    return Math.max(0, maxE - minS);
  });
  const globalMax = Math.max(0.1, ...ranges);

  const axis = document.createElement('div');
  axis.className = 'station-compare-axis';
  axis.style.height = `${chartHeight}px`;

  for (let i = 0; i <= 4; i++) {
    const pct = i / 4;
    const tSec = globalMax * pct;

    const tick = document.createElement('div');
    tick.className = 'station-compare-axis-tick';
    tick.style.bottom = `${pct * 100}%`;
    tick.textContent = `${tSec.toFixed(1)}s`;
    axis.appendChild(tick);

    const line = document.createElement('div');
    line.className = 'station-compare-axis-line';
    line.style.bottom = `${pct * 100}%`;
    axis.appendChild(line);
  }

  const bars = document.createElement('div');
  bars.className = 'station-compare-bars';
  bars.style.height = `${chartHeight}px`;

  for (const item of valid.slice(0, STATION_COMPARE_MAX)) {
    const station = document.createElement('div');
    station.className = 'station-compare-station';

    const bar = document.createElement('div');
    bar.className = 'station-compare-bar';
    bar.style.height = `${chartHeight}px`;

    const acts = item.actions;
    const minS = acts.reduce((m, a) => Math.min(m, a.start), Number.POSITIVE_INFINITY);
    const maxE = acts.reduce((m, a) => Math.max(m, a.end), 0);
    const total = Math.max(0, maxE - minS);

    const segments = [];
    let cursor = 0;
    for (const a of acts) {
      const s = Math.max(0, a.start - minS);
      const e = Math.max(s, a.end - minS);
      if (s > cursor) segments.push({ kind: 'gap', start: cursor, end: s });
      segments.push({ kind: 'act', start: s, end: e, label: a.label, index: a.index });
      cursor = Math.max(cursor, e);
    }
    if (globalMax > cursor) segments.push({ kind: 'gap', start: cursor, end: globalMax });

    const heights = [];
    let sum = 0;
    for (const seg of segments) {
      const d = Math.max(0, seg.end - seg.start);
      let h = Math.round((d / globalMax) * chartHeight);
      if (seg.kind === 'act' && d > 0 && h < 1) h = 1;
      heights.push(h);
      sum += h;
    }

    if (sum > chartHeight) {
      let excess = sum - chartHeight;
      for (let i = 0; i < segments.length && excess > 0; i++) {
        const minH = segments[i].kind === 'act' ? 1 : 0;
        const reducible = Math.max(0, heights[i] - minH);
        const take = Math.min(reducible, excess);
        heights[i] -= take;
        excess -= take;
      }
    } else if (sum < chartHeight && heights.length) {
      heights[heights.length - 1] += chartHeight - sum;
    }

    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const d = Math.max(0, seg.end - seg.start);
      const h = heights[i];
      if (h <= 0) continue;
      const el = document.createElement('div');
      el.className = 'station-compare-seg' + (seg.kind === 'gap' ? ' gap' : '');
      el.style.height = `${h}px`;
      if (seg.kind === 'act') {
        const key = String(seg.label || seg.index || '');
        el.style.background = _hashColor(key);
        el.title = `${seg.index ? seg.index + ' ' : ''}${seg.label || ''}\n${seg.start.toFixed(
          2
        )}s - ${seg.end.toFixed(2)}s (${d.toFixed(2)}s)`;
      }
      bar.appendChild(el);
    }

    const label = document.createElement('div');
    label.className = 'station-compare-label';
    label.title = item.label;
    label.textContent = item.label;

    station.appendChild(bar);
    station.appendChild(label);
    bars.appendChild(station);
  }

  const wrapper = document.createElement('div');
  wrapper.className = 'station-compare';
  wrapper.appendChild(axis);
  wrapper.appendChild(bars);

  root.innerHTML = '';
  root.appendChild(wrapper);
}

export async function refreshStationCompareChart() {
  const root = document.getElementById('stationCompareChart');
  if (!root) return;
  const resSel = document.getElementById('reviewResultSelect');
  if (!resSel) return;

  const seq = ++stationCompareRenderSeq;
  const elControls = document.getElementById('stationCompareControls');
  const pathsMd = Array.from(resSel.options)
    .map((o) => o.value || '')
    .filter((v) => v && v.endsWith('.md'));
  const pathsJson = Array.from(resSel.options)
    .map((o) => o.value || '')
    .filter((v) => v && v.endsWith('.json'));

  const paths = (currentLang === 'en' ? pathsMd.filter((v) => v.split('/').pop().startsWith('en_')) : pathsMd.filter((v) => !v.split('/').pop().startsWith('en_'))).slice(0, STATION_COMPARE_MAX);
  if (paths.length === 0) {
    // Fallback to all MD or all JSON if no language-specific MD files found
    const allPaths = (pathsMd.length ? pathsMd : pathsJson).slice(0, STATION_COMPARE_MAX);
    paths.push(...allPaths);
  }

  for (const p of paths) {
    const key = String(p || '');
    if (key && !stationCompareVisibleByPath.has(key)) stationCompareVisibleByPath.set(key, true);
  }

  const currentPath = currentJsonPath || resSel.value;
  if (currentPath && Array.isArray(currentActions) && currentActions.length) {
    const actionsAll = _normalizeActionsForCompare(currentActions);
    const r =
      currentCycleSelection &&
      currentCycleSelection.range &&
      Number.isFinite(currentCycleSelection.range.start) &&
      Number.isFinite(currentCycleSelection.range.end) &&
      currentCycleSelection.range.end > currentCycleSelection.range.start
        ? currentCycleSelection.range
        : null;
    const actions = r ? actionsAll.filter((a) => a.start >= r.start && a.end <= r.end) : actionsAll;
    stationCompareCache.set(String(currentPath), {
      path: String(currentPath),
      label: _stationLabelFromPath(currentPath),
      actions
    });
  }

  root.innerHTML = `<div style="color: var(--muted); font-size: 13px;">${t('loading')}</div>`;
  if (elControls) elControls.innerHTML = '';
  const items = [];
  for (const p of paths) {
    try {
      const item = await _fetchStationCompareItem(p);
      if (item) items.push(item);
    } catch {}
    if (seq !== stationCompareRenderSeq) return;
  }

  if (seq !== stationCompareRenderSeq) return;
  stationCompareLastItems = items;
  _renderStationCompareControls(items);
  const filtered = items.filter((x) => _isStationCompareVisible(x?.path));
  _renderStationCompareChart(filtered);
}

export function renderLegacyView() {
  const md = document.getElementById('mdResultView');
  const legacy = document.getElementById('legacyStatsView');
  if (md) md.style.display = 'none';
  if (legacy) legacy.style.display = 'none';
}

export function getDefaultActionsHeaders() {
  return [
    t('action_index'),
    t('action_desc'),
    t('therblig_type'),
    t('is_process'),
    t('is_move'),
    t('is_check'),
    t('is_wait'),
    t('estimated_duration'),
    t('value_added'),
    t('hands'),
    t('time_range'),
    t('variation_source')
  ];
}

export function renderDefaultActionsHeader() {
  const elHeader = document.getElementById('actionsListHeader');
  if (!elHeader) return;
  elHeader.innerHTML = '';
  
  const headers = getDefaultActionsHeaders();
  if (headers.length !== 12) {
      elHeader.style.gridTemplateColumns = `repeat(${headers.length}, minmax(100px, 1fr))`;
  } else {
      elHeader.style.removeProperty('grid-template-columns');
  }

  headers.forEach(h => {
    const div = document.createElement('div');
    div.textContent = h;
    elHeader.appendChild(div);
  });
}

export function renderActionsTable(table, actions) {
  const elHeader = document.getElementById('actionsListHeader');
  const elList = document.getElementById('actionsList');
  if (!elHeader || !elList) return;

  elHeader.innerHTML = '';
  elList.innerHTML = '';

  currentActions = Array.isArray(actions) ? actions : [];
  currentActionEls = new Array(currentActions.length).fill(null);
  activeIndex = -1;
  actionCountOverride = null;
  currentActions.forEach(normalizeActionTimeFields);

  const normSeq = (v) => String(v ?? '').replace(/\D/g, '');
  const actionIndexBySeq = new Map();
  for (let i = 0; i < currentActions.length; i++) {
    const seq = normSeq(currentActions[i]?.index ?? i + 1);
    if (seq) actionIndexBySeq.set(seq, i);
  }

  const rawHeaders =
    table && Array.isArray(table.headers) && table.headers.length > 0
      ? table.headers
      : getDefaultActionsHeaders();
  const headersRaw = Array.isArray(rawHeaders) ? [...rawHeaders] : [...getDefaultActionsHeaders()];
  const rowsRaw = table && Array.isArray(table.rows) ? table.rows : [];
  const canIndexByRow = Array.isArray(rowsRaw) && rowsRaw.length > 0 && rowsRaw.length === currentActions.length;

  const cycleColIndexRaw = headersRaw.findIndex((h) => /^(cycle|循环|週期)$/i.test(String(h || '').trim()));
  const seqColIndexRaw = headersRaw.findIndex((h) => /^(序号|编号|No\.?|Index)$/i.test(String(h || '').trim()));
  currentCycleSelection = computeCycleSelectionFromTable(headersRaw, rowsRaw, currentActions);
  let selectedCycle = currentCycleSelection ? String(currentCycleSelection.cycleKey || '') : '';
  if (cycleColIndexRaw >= 0 && Array.isArray(rowsRaw) && rowsRaw.length) {
    const hasNonNumericCycle = rowsRaw.some((row) => {
      const cells = Array.isArray(row) ? row : [];
      const rawCycle = String(cells[cycleColIndexRaw] ?? '').trim();
      return rawCycle && !normSeq(rawCycle);
    });
    if (hasNonNumericCycle) selectedCycle = '';
  }

  let headers = headersRaw;
  const rows = rowsRaw;
  if (cycleColIndexRaw >= 0) {
    headers = headersRaw.filter((_h, i) => i !== cycleColIndexRaw);
  }
  currentActionsHeaders = headers;
    
  actionDurationColIndex = headers.findIndex((h) => /耗时|duration/i.test(String(h || '')));
  actionTimeColIndex =
    headers.findIndex((h) => /(时间区间|时间段|time\s*range)/i.test(String(h || ''))) >= 0
      ? headers.findIndex((h) => /(时间区间|时间段|time\s*range)/i.test(String(h || '')))
      : headers.findIndex((h) => /时间|time/i.test(String(h || '')));
  const seqColIndex = headers.findIndex((h) => /^(序号|编号|No\.?|Index)$/i.test(String(h || '').trim()));
  
  // Calculate max columns from data to ensure we display everything
  let maxCols = headers.length;
  const rowsForDisplay =
    cycleColIndexRaw >= 0 && Array.isArray(rows) ? rows.map((r) => (Array.isArray(r) ? r.filter((_c, i) => i !== cycleColIndexRaw) : [])) : rows;
  rowsForDisplay.forEach((r) => {
      if (Array.isArray(r) && r.length > maxCols) maxCols = r.length;
  });
  
  // Extend headers if needed
  if (maxCols > headers.length) {
      const diff = maxCols - headers.length;
      for (let i = 0; i < diff; i++) {
          headers.push(`Col ${headers.length + 1}`);
      }
  }

  let gridTemplate;
  const buildFixedGridTemplate = (headersList, colCount) => {
    const n = Math.max(0, Number(colCount) || 0);
    if (!n) return '';
    const smallCol = '56px';
    const cols = [];
    for (let i = 0; i < n; i++) {
      const h = String((headersList && headersList[i]) || '').trim();
      if (/^(cycle|循环|週期)$/i.test(h)) {
        cols.push(smallCol);
        continue;
      }
      if (/^(序号|编号|No\.?|Index)$/i.test(h)) {
        cols.push(smallCol);
        continue;
      }
      if (/(动作描述|motion description|description)/i.test(h)) {
        cols.push('320px');
        continue;
      }
      if (/(动素|therblig)/i.test(h)) {
        cols.push('200px');
        continue;
      }
      if (/(耗时|duration|time\s*\(s\)|est\.\s*duration)/i.test(h)) {
        cols.push('120px');
        continue;
      }
      if (/(时间区间|时间段|time\s*range)/i.test(h)) {
        cols.push('180px');
        continue;
      }
      if (/(增值|VA\/NVA|value)/i.test(h)) {
        cols.push('120px');
        continue;
      }
      if (/(左右手|hand)/i.test(h)) {
        cols.push('90px');
        continue;
      }
      if (/(波动来源|variation)/i.test(h)) {
        cols.push('160px');
        continue;
      }
      if (/^(是否加工|process|是否搬运|transport|是否检查|inspect|是否等待|wait|是否存储|store)$/i.test(h)) {
        cols.push('90px');
        continue;
      }
      cols.push('140px');
    }
    return cols.join(' ');
  };

  gridTemplate = buildFixedGridTemplate(headers, maxCols);

  // 阶段 3：首列为动作首帧缩略图列
  gridTemplate = '64px ' + gridTemplate;
  headers.unshift(t('action_thumb'));
  maxCols += 1;
  
  elHeader.style.display = 'grid';
  elHeader.style.gridTemplateColumns = gridTemplate;
  elHeader.style.width = 'max-content';
  elHeader.style.minWidth = 'max-content';

  headers.forEach(h => {
    const div = document.createElement('div');
    div.textContent = h;
    div.title = h;
    div.style.padding = '8px';
    div.style.fontWeight = 'bold';
    div.style.borderRight = '1px solid var(--border)';
    elHeader.appendChild(div);
  });
  
  let renderedCount = 0;
  rowsForDisplay.forEach((cellsDisplay, idx) => {
    const cellsRaw = Array.isArray(rows) && Array.isArray(rows[idx]) ? rows[idx] : [];
    const rowDiv = document.createElement('div');
    rowDiv.className = 'action-item';
    rowDiv.dataset.index = String(idx);
    let actionIdx = -1;
    let cycleKey = '';
    if (cycleColIndexRaw >= 0) {
      cycleKey = String((cellsRaw && cellsRaw.length ? cellsRaw[cycleColIndexRaw] : '') ?? '').trim();
      if (!cycleKey) cycleKey = '1';
    }
    if (canIndexByRow && idx < currentActions.length) {
      actionIdx = idx;
    } else {
      const seqCell =
        seqColIndexRaw >= 0 && cellsRaw && cellsRaw.length > seqColIndexRaw
          ? cellsRaw[seqColIndexRaw]
          : cellsRaw && cellsRaw.length
          ? cellsRaw[0]
          : '';
      const seq = normSeq(seqCell);
      const mapped = seq ? actionIndexBySeq.get(seq) : undefined;
      actionIdx = Number.isFinite(mapped) ? mapped : idx;
    }
    if (!Number.isFinite(actionIdx) || actionIdx < 0 || actionIdx >= currentActions.length) actionIdx = -1;
    rowDiv.dataset.actionIndex = String(actionIdx);
    rowDiv.style.display = 'grid';
    rowDiv.style.gridTemplateColumns = gridTemplate;
    rowDiv.style.width = 'max-content';
    
    const action = actionIdx >= 0 ? currentActions[actionIdx] : null;
    if (action && cycleKey) action.cycle = cycleKey;
    if (action) currentActionEls[actionIdx] = rowDiv;
    if (selectedCycle && cycleColIndexRaw >= 0 && normSeq(cycleKey) !== normSeq(selectedCycle)) return;
    rowDiv.onclick = () => {
      if (actionIdx >= 0) {
        const act = currentActions[actionIdx];
        if (act) {
          normalizeActionTimeFields(act);
          const t = Number.parseFloat(act.start_time);
          if (window.seekVideo && Number.isFinite(t)) window.seekVideo(t, { play: true });
        }
      }
      document.querySelectorAll('.action-item').forEach((el) => el.classList.remove('active'));
      rowDiv.classList.add('active');
    };
    
    // Ensure we render all cells, even if they exceed original header count
    // Pad with empty strings if row is shorter than maxCols
    const renderCells = Array.isArray(cellsDisplay) ? [...cellsDisplay] : [];
    while (renderCells.length < maxCols - 1) {
        renderCells.push('');
    }
    // 阶段 3：首格为缩略图占位（由 applyThumbsToRows 异步填充）
    renderCells.unshift('');

    renderCells.forEach((cellText, cellIdx) => {
      const cellDiv = document.createElement('div');
      cellDiv.className = 'col-content';
      if (cellIdx === 0) {
        cellDiv.className = 'col-content action-thumb-cell';
        cellDiv.dataset.actionIndex = String(actionIdx);
      } else {
        cellDiv.textContent = cellText;
        cellDiv.title = cellText;
      }
      cellDiv.style.padding = '8px';
      cellDiv.style.borderRight = '1px solid var(--border)';
      cellDiv.style.overflow = 'hidden';
      cellDiv.style.textOverflow = 'ellipsis';
      rowDiv.appendChild(cellDiv);
    });

    elList.appendChild(rowDiv);
    currentActionEls.push(rowDiv);
    renderedCount += 1;
  });

  elList.style.width = 'max-content';
  elList.style.minWidth = 'max-content';
  
  // Ensure container scrolls
  const panelBody = document.querySelector('.actions-panel-body');
  if (panelBody) {
      panelBody.style.overflowX = 'auto';
      panelBody.style.maxWidth = '100%';
      panelBody.style.display = 'block'; 
  }

  if (selectedCycle) actionCountOverride = renderedCount;
  renderActionTimeline(currentActions);
  enforceClipRange();
  refreshDynamicText();
  applyThumbsToRows();
}

export function renderActions(actions) {
   if (!actions) return;
   const rows = actions.map(act => {
       return [
           act.index || '',
           act.label || '',
           act.therblig || '',
           act.is_process || '',
           act.is_move || '',
           act.is_check || '',
           act.is_wait || '',
           act.duration || '',
           act.value_added || '',
           act.hands || '',
           act.time_range || '',
           act.variation || ''
       ];
   });
   renderActionsTable({ headers: getDefaultActionsHeaders(), rows: rows }, actions);
}

// ---------------------------------------------------------------------------
// 阶段 3：动作首帧缩略图
// ---------------------------------------------------------------------------

export let currentThumbs = [];
export let currentThumbsPath = '';

export async function fetchResultThumbs(path) {
  if (!path) return;
  currentThumbsPath = path;
  try {
    const res = await authFetch('/api/result_thumbs?path=' + encodeURIComponent(path));
    if (!res.ok) throw new Error('status ' + res.status);
    const data = await res.json();
    if (path !== currentThumbsPath) return;
    currentThumbs = Array.isArray(data.thumbs) ? data.thumbs : [];
  } catch (e) {
    console.warn('thumbs unavailable:', e);
    currentThumbs = [];
  }
  applyThumbsToRows();
}

export function buildThumbPlaceholder() {
  const ph = document.createElement('div');
  ph.className = 'action-thumb action-thumb-placeholder';
  ph.textContent = '—';
  return ph;
}

export function applyThumbsToRows() {
  document.querySelectorAll('#actionsList .action-item').forEach((row) => {
    const cell = row.querySelector('.action-thumb-cell');
    if (!cell) return;
    const idx = Number(cell.dataset.actionIndex);
    cell.innerHTML = '';
    if (Number.isFinite(idx) && currentThumbs[idx]) {
      const img = document.createElement('img');
      img.className = 'action-thumb';
      img.loading = 'lazy';
      img.alt = '';
      img.src = withMediaToken('/' + currentThumbs[idx]);
      img.onerror = () => {
        if (img.parentNode) img.replaceWith(buildThumbPlaceholder());
      };
      cell.appendChild(img);
    } else {
      cell.appendChild(buildThumbPlaceholder());
    }
  });
}

// ---------------------------------------------------------------------------
// 阶段 3：VA / NVA 增值统计
// ---------------------------------------------------------------------------

export const VANVA_COLORS = {
  va: '#4caf50',
  nva: '#ef5350',
  nnva: '#ffa726',
  unknown: '#90a4ae'
};

export let vanvaChartInstance = null;

export function classifyVaNva(value) {
  const v = String(value ?? '').trim().toLowerCase();
  if (!v) return 'unknown';
  if (v.includes('必要') || v.includes('nnva') || v.includes('necessary')) return 'nnva';
  if (v.includes('非增值') || v === 'nva' || v.includes('non-value') || v.includes('non value')) return 'nva';
  if (v.includes('增值') || v === 'va' || v.includes('value-added') || v.includes('value added')) return 'va';
  return 'unknown';
}

export function renderVaNvaStats(actions) {
  const panel = document.getElementById('vanvaPanel');
  if (!panel) return;
  const list = Array.isArray(actions) ? actions : [];

  const buckets = { va: 0, nva: 0, nnva: 0, unknown: 0 };
  const counts = { va: 0, nva: 0, nnva: 0, unknown: 0 };
  let total = 0;
  for (const act of list) {
    const s = Number.parseFloat(act?.start_time);
    const e = Number.parseFloat(act?.end_time);
    const dur = Number.isFinite(s) && Number.isFinite(e) ? Math.max(0, e - s) : 0;
    const key = classifyVaNva(act?.value_added);
    buckets[key] += dur;
    counts[key] += 1;
    total += dur;
  }

  if (!total) {
    panel.style.display = 'none';
    if (vanvaChartInstance) {
      try { vanvaChartInstance.destroy(); } catch {}
      vanvaChartInstance = null;
    }
    return;
  }

  panel.style.display = 'block';
  const keys = ['va', 'nva', 'nnva', 'unknown'];
  const labels = {
    va: t('vanva_va'),
    nva: t('vanva_nva'),
    nnva: t('vanva_nnva'),
    unknown: t('vanva_unknown')
  };

  const canvas = document.getElementById('vanvaChart');
  if (canvas && typeof Chart !== 'undefined') {
    const ctx = canvas.getContext('2d');
    if (vanvaChartInstance) {
      try { vanvaChartInstance.destroy(); } catch {}
      vanvaChartInstance = null;
    }
    vanvaChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: keys.map((k) => labels[k]),
        datasets: [
          {
            data: keys.map((k) => Number(buckets[k].toFixed(2))),
            backgroundColor: keys.map((k) => VANVA_COLORS[k]),
            borderColor: 'rgba(0,0,0,0.12)',
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        animation: false,
        cutout: '58%',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => {
                const k = keys[item.dataIndex];
                const pct = total > 0 ? ((buckets[k] / total) * 100).toFixed(1) : '0';
                return `${item.label}: ${buckets[k].toFixed(1)}s (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }

  const legend = document.getElementById('vanvaLegend');
  if (legend) {
    legend.innerHTML = '';
    keys.forEach((k) => {
      const pct = total > 0 ? ((buckets[k] / total) * 100).toFixed(1) : '0';
      const rowEl = document.createElement('div');
      rowEl.className = 'vanva-legend-row';
      rowEl.innerHTML = `
        <span class="vanva-legend-dot" style="background:${VANVA_COLORS[k]}"></span>
        <span class="vanva-legend-name">${labels[k]}</span>
        <span class="vanva-legend-meta">${counts[k]} ${t('vanva_actions_unit')} · ${buckets[k].toFixed(1)}s · ${pct}%</span>
      `;
      legend.appendChild(rowEl);
    });
    const totalRow = document.createElement('div');
    totalRow.className = 'vanva-legend-row vanva-legend-total';
    totalRow.innerHTML = `
      <span class="vanva-legend-dot" style="background:transparent"></span>
      <span class="vanva-legend-name">${t('vanva_total')}</span>
      <span class="vanva-legend-meta">${total.toFixed(1)}s</span>
    `;
    legend.appendChild(totalRow);
  }
}

// ---------------------------------------------------------------------------
// 阶段 3：动作表 CSV 导出（所见即所得）
// ---------------------------------------------------------------------------

export function exportActionsCsv() {
  const headerEl = document.getElementById('actionsListHeader');
  const listEl = document.getElementById('actionsList');
  if (!headerEl || !listEl || !currentActions.length) {
    notify(t('no_result_selected'));
    return;
  }

  const headers = Array.from(headerEl.querySelectorAll('div'))
    .map((el) => el.textContent || '')
    .slice(1); // 跳过缩略图列
  const rows = Array.from(listEl.querySelectorAll('.action-item')).map((row) =>
    Array.from(row.querySelectorAll('.col-content'))
      .filter((el) => !el.classList.contains('action-thumb-cell'))
      .map((el) => el.textContent || '')
  );

  const esc = (v) => {
    const s = String(v ?? '');
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const lines = [headers.map(esc).join(',')];
  rows.forEach((r) => lines.push(r.map(esc).join(',')));
  const csv = '\uFEFF' + lines.join('\r\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const base = (currentJsonPath || 'actions')
    .split('/')
    .pop()
    .replace(/\.[^.]+$/, '');
  a.href = url;
  a.download = `${base}_actions.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// 阶段 3：修订历史（留痕 + 回滚）
// ---------------------------------------------------------------------------

export async function showRevisionHistory() {
  if (!currentJsonPath) {
    notify(t('no_result_selected'));
    return;
  }
  const modal = document.getElementById('revisionModal');
  const listEl = document.getElementById('revisionList');
  if (!modal || !listEl) return;
  modal.classList.add('open');
  listEl.innerHTML = `<div style="color:var(--muted)">loading...</div>`;
  try {
    const res = await authFetch('/api/result_revisions?path=' + encodeURIComponent(currentJsonPath));
    const data = await res.json();
    const revisions = Array.isArray(data.revisions) ? data.revisions : [];
    if (!revisions.length) {
      listEl.innerHTML = `<div style="color:var(--muted)">${t('revision_none')}</div>`;
      return;
    }
    listEl.innerHTML = '';
    revisions.forEach((rev) => {
      const rowEl = document.createElement('div');
      rowEl.className = 'revision-row';
      const note = String(rev.revision_note || '');
      const noteText = note.startsWith('before_restore#')
        ? `${t('revision_history')} #${note.split('#')[1]}`
        : t('edit_action');
      rowEl.innerHTML = `
        <div class="revision-meta">
          <span class="revision-id">#${rev.id}</span>
          <span class="revision-time">${String(rev.created_at || '')}</span>
          <span class="revision-user">${String(rev.created_by || '')}</span>
          <span class="revision-count">${rev.action_count} ${t('vanva_actions_unit')}</span>
          <span class="revision-note">${noteText}</span>
        </div>
      `;
      const btn = document.createElement('button');
      btn.className = 'btn revision-restore-btn';
      btn.textContent = t('revision_restore');
      btn.onclick = async () => {
        if (!window.confirm(t('revision_restore_confirm'))) return;
        await restoreRevision(rev.id);
      };
      rowEl.appendChild(btn);
      listEl.appendChild(rowEl);
    });
  } catch (e) {
    listEl.innerHTML = `<div style="color:var(--danger,#ef5350)">${t('revision_load_failed', { error: e.message })}</div>`;
  }
}

export async function restoreRevision(revisionId) {
  try {
    const res = await authFetch('/api/result_revisions/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision_id: revisionId })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'status ' + res.status);
    notify(t('revision_restored'));
    const sel = document.getElementById('reviewResultSelect');
    if (sel && sel.value) {
      sel.dispatchEvent(new Event('change'));
    }
    showRevisionHistory();
  } catch (e) {
    notify(t('revision_load_failed', { error: e.message }));
  }
}

export let chartInstance = null;
export let chartCountLabelPluginRegistered = false;
export let currentStats = null;

export function computeActionTypeStats(actions) {
  const byLabel = new Map();
  for (const act of actions || []) {
    const label = act && act.label ? String(act.label) : '';
    if (!label) continue;
    const start = Number.parseFloat(act.start_time);
    const end = Number.parseFloat(act.end_time);
    const duration = Number.isFinite(start) && Number.isFinite(end) ? Math.max(0, end - start) : 0;

    let item = byLabel.get(label);
    if (!item) {
      item = { label, count: 0, totalDuration: 0 };
      byLabel.set(label, item);
    }
    item.count += 1;
    item.totalDuration += duration;
  }
  return Array.from(byLabel.values()).map((x) => ({
    label: x.label,
    count: x.count,
    avgDuration: x.count > 0 ? x.totalDuration / x.count : 0
  }));
}

export const countLabelPlugin = {
  id: 'countLabelPlugin',
  afterDatasetsDraw(chart) {
    const opts =
      (chart && chart.options && chart.options.plugins && chart.options.plugins.countLabelPlugin) ||
      {};
    const counts = Array.isArray(opts.counts) ? opts.counts : [];
    const datasetIndex = Number.isFinite(opts.datasetIndex) ? opts.datasetIndex : 0;
    const meta = chart.getDatasetMeta(datasetIndex);
    if (!meta || !meta.data) return;

    const ctx = chart.ctx;
    ctx.save();
    ctx.fillStyle = opts.color || 'rgba(255,255,255,0.9)';
    ctx.font = opts.font || '12px ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';

    meta.data.forEach((bar, idx) => {
      const count = counts[idx];
      if (count === undefined || count === null) return;
      const x = bar.x;
      const y = bar.y - 4;
      ctx.fillText(String(count), x, y);
    });

    ctx.restore();
  }
};

export function renderStats(stats) {
  currentStats = stats || null;
  try {
    const canvas = document.getElementById('actionChart');

    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext('2d');

    if (!stats) {
      if (chartInstance) {
        try {
          chartInstance.destroy();
        } catch {}
        chartInstance = null;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const statTotal = document.getElementById('statTotal');
      const statTypes = document.getElementById('statTypes');
      const statAvg = document.getElementById('statAvg');
      if (statTotal) statTotal.textContent = '-';
      if (statTypes) statTypes.textContent = '-';
      if (statAvg) statAvg.textContent = '-';
      return;
    }

    if (chartInstance) {
      try {
        chartInstance.destroy();
      } catch (e) {
        console.error('Destroy failed', e);
      }
    }

    if (typeof Chart === 'undefined') {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    if (!chartCountLabelPluginRegistered && typeof Chart.register === 'function') {
      Chart.register(countLabelPlugin);
      chartCountLabelPluginRegistered = true;
    }

    const perType = computeActionTypeStats(currentActions);
    const chartText = getThemeColor('--chart-text', 'rgba(255,255,255,0.92)');
    const chartAxis = getThemeColor('--chart-axis', 'rgba(255,255,255,0.85)');
    if (perType.length > 0) {
      const labels = perType.map((t) => t.label);
      const avgDurations = perType.map((t) => Number(t.avgDuration.toFixed(2)));
      const counts = perType.map((t) => t.count);

      chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: t('avg_duration_seconds'),
              data: avgDurations,
              backgroundColor: 'rgba(122, 162, 255, 0.6)',
              borderColor: 'rgba(122, 162, 255, 1)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: false,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: {
              labels: { color: chartText }
            },
            countLabelPlugin: {
              counts,
              datasetIndex: 0,
              color: chartText
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { color: chartText },
              title: { display: true, text: t('avg_duration_seconds'), color: chartAxis }
            },
            x: { ticks: { color: chartText } }
          }
        }
      });
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      chartInstance = null;
    }

    const statTotal = document.getElementById('statTotal');
    const statTypes = document.getElementById('statTypes');
    const statAvg = document.getElementById('statAvg');
    if (statTotal) statTotal.textContent = stats.total_actions || stats.action_count || '-';
    if (statTypes)
      statTypes.textContent = stats.unique_action_type_count || stats.unique_action_types || '-';
    if (statAvg)
      statAvg.textContent = (stats.avg_action_duration || stats.average_duration || 0).toFixed(1) + 's';
  } catch (e) {
    console.error(e);
  }
}

export function renderAdvice(advice) {
  const container = document.getElementById('adviceList');
  if (!container) return;
  if (advice && Array.isArray(advice) && advice.length > 0) {
    container.innerHTML = advice
      .map(
        (item) => `
            <div class="advice-item">${item}</div>
        `
      )
      .join('');
  } else {
    container.innerHTML = `<div style="color:var(--muted)">${t('no_advice_data')}</div>`;
  }
}

export function syncActiveAction(scrollOnChange) {
  if (!elVideo || !elNowPlaying) return;
  const t = elVideo.currentTime;
  elNowPlaying.textContent = new Date(t * 1000).toISOString().substr(14, 5);

  let found = -1;
  const allow =
    currentCycleSelection && currentCycleSelection.actionIdxSet instanceof Set
      ? currentCycleSelection.actionIdxSet
      : null;
  for (let i = 0; i < currentActions.length; i++) {
    if (allow && !allow.has(i)) continue;
    const act = currentActions[i];
    const start = parseTimeFlexible(act.start_time);
    const end = parseTimeFlexible(act.end_time);
    if (t >= start && t <= end) {
      found = i;
      break;
    }
  }

  for (let i = 0; i < currentActionEls.length; i++) {
    const el = currentActionEls[i];
    if (el) el.classList.remove('active');
  }

  if (found !== -1 && currentActionEls[found]) {
    currentActionEls[found].classList.add('active');
    if (scrollOnChange && found !== activeIndex) {
      currentActionEls[found].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (elActiveAction) elActiveAction.textContent = currentActions[found]?.label || '-';
  } else {
    if (elActiveAction) elActiveAction.textContent = '-';
  }

  updateTimelineActive(found);
  activeIndex = found;
}

export function setupReviewUI() {
  elVideo = document.getElementById('video');
  elActions = document.getElementById('actionsList');
  elNowPlaying = document.getElementById('nowPlaying');
  elActionCount = document.getElementById('actionCount');
  elActiveAction = document.getElementById('activeAction');

  if (elVideo) {
    window.seekVideo = (t, { play = true } = {}) => {
      if (!elVideo) return;
      const target = clampToClip(t);
      if (!Number.isFinite(target)) return;
      try {
        elVideo.currentTime = target;
      } catch {}
      if (play) {
        try {
          const p = elVideo.play();
          if (p && typeof p.catch === 'function') p.catch(() => {});
        } catch {}
      }
    };

    elVideo.addEventListener('timeupdate', () => {
      syncActiveAction(true);
      enforceClipRange();
      updateTimelinePlayhead();
    });
    elVideo.addEventListener('seeked', () => {
      enforceClipRange();
      updateTimelinePlayhead();
    });
    elVideo.addEventListener('loadedmetadata', () => {
      const d = Number(elVideo.duration);
      if (Number.isFinite(d) && d > 0 && clipStartSec !== null && clipEndSec !== null) {
        const s0 = Number(clipStartSec);
        const e0 = Number(clipEndSec);
        if (Number.isFinite(s0) && Number.isFinite(e0) && e0 > s0) {
          clipStartSec = Math.max(0, Math.min(d, s0));
          clipEndSec = Math.max(Number(clipStartSec) + 0.001, Math.min(d, e0));
        }
      }
      if (clipStartSec !== null && Number.isFinite(clipStartSec)) {
        try {
          elVideo.currentTime = Number(clipStartSec);
        } catch {}
      }
      enforceClipRange();
      updateTimelinePlayhead();
    });
  }

  const resultSel = document.getElementById('reviewResultSelect');
  if (resultSel) {
    resultSel.addEventListener('change', async (e) => {
      if (!e.target.value) return;
      try {
        clearClipRange();
        currentJsonPath = e.target.value;
        const apiUrl =
          '/api/result_details?path=' + encodeURIComponent(e.target.value) + '&ts=' + Date.now();

        const res = await authFetch(apiUrl);
        if (!res.ok)
          throw new Error(t('load_failed_with_status', { url: apiUrl, status: res.status }));
        const data = await res.json();

        const isMd = data.overview !== undefined || data.deep_dive !== undefined || data.kaizen !== undefined;

        if (isMd) {
          renderMdView(data);
          if (data.actions_table && data.actions_table.headers && data.actions_table.rows) {
            renderActionsTable(data.actions_table, data.actions || []);
          } else {
            renderActions(data.actions || []);
          }
        } else {
          renderLegacyView();

          let actions = null;
          let stats = null;
          if (Array.isArray(data)) {
            actions = data;
          } else if (data && typeof data === 'object') {
            if (Array.isArray(data.actions)) actions = data.actions;
            else if (data.model_output && Array.isArray(data.model_output.actions))
              actions = data.model_output.actions;
            else if (data.output && Array.isArray(data.output.actions)) actions = data.output.actions;

            stats = data.stats || (data.model_output && data.model_output.stats) || data.computed_stats || null;
          }

          if (!actions) {
            const keys = data && typeof data === 'object' ? Object.keys(data).join(', ') : String(typeof data);
            throw new Error(t('unknown_json_format', { keys }));
          }

          renderActions(actions);
          renderStats(stats);
          renderAdvice(data.advice || (data.model_output && data.model_output.advice) || null);
        }

        renderActionTimeline(currentActions);
        enforceClipRange();
        updateTimelinePlayhead();
        refreshStationCompareChart();

        // 阶段 3：结果查看增强 —— 缩略图 + VA/NVA 统计
        currentThumbs = [];
        fetchResultThumbs(currentJsonPath);
        renderVaNvaStats(currentActions);

        const view = document.getElementById('project-panel-results') || document.getElementById('view-project');
        if (view) view.scrollTop = 0;
      } catch (e) {
        notify(t('load_result_failed', { error: e.message }));
      }
    });
  }

  const videoSel = document.getElementById('reviewVideoSelect');
  if (videoSel) {
    videoSel.addEventListener('change', (e) => {
      if (e.target.value && elVideo) {
        elVideo.src = withMediaToken('/' + e.target.value);
        const name = document.getElementById('videoName');
        if (name) name.textContent = e.target.value;
        autoSelectResultByVideoPrefix(e.target.value);
      }
    });
  }

  elTimeline = document.getElementById('actionTimeline');
  elTimelineSegments = document.getElementById('actionTimelineSegments');
  elTimelinePlayhead = document.getElementById('actionTimelinePlayhead');

  if (elTimeline) {
    const onPointerMove = (e) => {
      if (isBoundaryDragging) {
        adjustBoundaryFromClientX(e.clientX);
        return;
      }
      if (!isTimelineDragging) return;
      seekFromTimelineClientX(e.clientX);
    };
    const onPointerUp = (e) => {
      if (isBoundaryDragging) {
        isBoundaryDragging = false;
        if (boundaryPointerId !== null) {
          try {
            elTimeline.releasePointerCapture(boundaryPointerId);
          } catch {}
        }
        boundaryPointerId = null;
        adjustBoundaryFromClientX(e.clientX);
        draggingBoundary = null;
        persistActionsUpdate({ silentSuccess: true });
        return;
      }
      if (!isTimelineDragging) return;
      isTimelineDragging = false;
      if (timelinePointerId !== null) {
        try {
          elTimeline.releasePointerCapture(timelinePointerId);
        } catch {}
      }
      timelinePointerId = null;
      seekFromTimelineClientX(e.clientX);
    };

    elTimeline.addEventListener('pointerdown', (e) => {
      if (!elTimeline) return;
      const handle = e.target && e.target.closest ? e.target.closest('.action-timeline-handle') : null;
      if (handle) {
        const leftIdx = Number(handle.dataset.leftIndex);
        const rightIdx = Number(handle.dataset.rightIndex);
        if (!Number.isFinite(leftIdx) || !Number.isFinite(rightIdx)) return;
        isBoundaryDragging = true;
        boundaryPointerId = e.pointerId;
        draggingBoundary = { leftIdx, rightIdx, el: handle };
        try {
          elTimeline.setPointerCapture(e.pointerId);
        } catch {}
        adjustBoundaryFromClientX(e.clientX);
        return;
      }
      const seg = e.target && e.target.closest ? e.target.closest('.action-timeline-segment') : null;
      if (seg) {
        const idx = Number(seg.dataset.index);
        const act = Number.isFinite(idx) ? currentActions[idx] : null;
        if (act) normalizeActionTimeFields(act);
        const t = act ? Number.parseFloat(act.start_time) : NaN;
        if (window.seekVideo && Number.isFinite(t)) window.seekVideo(t, { play: true });
        return;
      }
      isTimelineDragging = true;
      timelinePointerId = e.pointerId;
      try {
        elTimeline.setPointerCapture(e.pointerId);
      } catch {}
      seekFromTimelineClientX(e.clientX);
    });
    elTimeline.addEventListener('pointermove', onPointerMove);
    elTimeline.addEventListener('pointerup', onPointerUp);
    elTimeline.addEventListener('pointercancel', onPointerUp);
  }

  renderActionTimeline(currentActions);
  updateTimelinePlayhead();

  const elContextMenu = document.getElementById('contextMenu');
  const elEditModal = document.getElementById('editModal');
  const btnEditAction = document.getElementById('btnEditAction');
  const btnAddAction = document.getElementById('btnAddAction');
  const btnDeleteAction = document.getElementById('btnDeleteAction');
  const btnCancelEdit = document.getElementById('btnCancelEdit');
  const btnSaveEdit = document.getElementById('btnSaveEdit');
  bindEnterToButton(elEditModal, btnSaveEdit);

  // 阶段 3：修订历史弹窗
  const btnCloseRevisions = document.getElementById('btnCloseRevisions');
  const revisionModal = document.getElementById('revisionModal');
  if (btnCloseRevisions && revisionModal) {
    btnCloseRevisions.onclick = () => revisionModal.classList.remove('open');
    revisionModal.addEventListener('click', (e) => {
      if (e.target === revisionModal) revisionModal.classList.remove('open');
    });
  }

  let editingActionIndex = -1;
  const minActionGap = 0.1;

  function hideContextMenu() {
    if (!elContextMenu) return;
    elContextMenu.style.display = 'none';
  }

  function showContextMenu(x, y, index) {
    if (!elContextMenu) return;
    editingActionIndex = index;
    elContextMenu.style.display = 'block';
    elContextMenu.style.left = '0px';
    elContextMenu.style.top = '0px';

    const w = elContextMenu.offsetWidth;
    const h = elContextMenu.offsetHeight;
    const maxX = window.scrollX + window.innerWidth - w - 8;
    const maxY = window.scrollY + window.innerHeight - h - 8;
    const nextX = Math.max(window.scrollX + 8, Math.min(x, maxX));
    const nextY = Math.max(window.scrollY + 8, Math.min(y, maxY));
    elContextMenu.style.left = nextX + 'px';
    elContextMenu.style.top = nextY + 'px';

    if (btnDeleteAction) {
      const disabled = currentActions.length <= 1;
      btnDeleteAction.classList.toggle('disabled', disabled);
      btnDeleteAction.setAttribute('aria-disabled', disabled ? 'true' : 'false');
    }
  }

  if (elActions) {
    elActions.addEventListener('contextmenu', (e) => {
      const item = e.target.closest('.action-item');
      if (!item) return;
      e.preventDefault();
      const idx = Number(item.dataset.actionIndex ?? item.dataset.index);
      if (!Number.isFinite(idx) || idx < 0 || idx >= currentActions.length) return;
      showContextMenu(e.pageX, e.pageY, idx);
    });
  }

  document.addEventListener('click', (e) => {
    if (!elContextMenu) return;
    if (elContextMenu.style.display === 'block' && !elContextMenu.contains(e.target)) {
      hideContextMenu();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    hideContextMenu();
    if (elEditModal) elEditModal.classList.remove('open');
    const notifyModal = document.getElementById('notifyModal');
    if (notifyModal) notifyModal.classList.remove('open');
    const revModal = document.getElementById('revisionModal');
    if (revModal) revModal.classList.remove('open');
  });

  if (elContextMenu) {
    elContextMenu.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }

  function openEditModal(index) {
    if (index < 0 || index >= currentActions.length) return;
    editingActionIndex = index;
    const act = currentActions[index];

    hideContextMenu();

    normalizeActionTimeFields(act);

    const setVal = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.value = value ?? '';
    };

    setVal('editIndex', act.index || index + 1);
    setVal('editStartTime', act.start_time !== undefined ? act.start_time : '');
    setVal('editEndTime', act.end_time !== undefined ? act.end_time : '');
    setVal('editLabel', act.label || '');
    setVal('editIsProcess', act.is_process || '');
    setVal('editIsMove', act.is_move || '');
    setVal('editIsCheck', act.is_check || '');
    setVal('editIsWait', act.is_wait || '');
    setVal('editIsStore', act.is_store || '');
    setVal('editValueAdded', act.value_added || '');
    setVal('editVariation', act.variation || '');
    const handsText =
      String(act.hands ?? '').trim() ||
      (String(act.left_hand ?? '').trim() || String(act.right_hand ?? '').trim()
        ? `${String(act.left_hand ?? '').trim()} / ${String(act.right_hand ?? '').trim()}`.trim()
        : '');
    setVal('editHands', handsText);

    if (elEditModal) elEditModal.classList.add('open');
  }

  if (btnEditAction)
    btnEditAction.onclick = () => {
      openEditModal(editingActionIndex);
    };

  function updateActionTimeRange(act) {
    if (!act) return;
    normalizeActionTimeFields(act);
    const startNum = parseFloat(act.start_time);
    const endNum = parseFloat(act.end_time);
    if (Number.isFinite(startNum)) act.start_time = startNum;
    if (Number.isFinite(endNum)) act.end_time = endNum;
    updateActionComputedFields(act);
  }

  function normalizeAddRange(startValue, endValue, minStart, maxEnd) {
    let start = Number.isFinite(startValue) ? startValue : 0;
    let end = Number.isFinite(endValue) ? endValue : start + minActionGap;
    const safeMin = Number.isFinite(minStart) ? minStart : start;
    const safeMax = Number.isFinite(maxEnd) ? maxEnd : end;
    if (!(end > start)) {
      start = Math.max(safeMin, Math.min(safeMax - minActionGap, start));
      end = Math.min(safeMax, start + minActionGap);
    }
    if (!Number.isFinite(start)) start = 0;
    if (!Number.isFinite(end)) end = start + minActionGap;
    return { start, end, min: safeMin, max: safeMax };
  }

  function rebuildActionIndexes() {
    currentActions.forEach((act, idx) => {
      if (act && typeof act === 'object') {
        act.index = String(idx + 1);
      }
    });
  }

  function buildNewAction(prev, next) {
    if (prev) normalizeActionTimeFields(prev);
    if (next) normalizeActionTimeFields(next);
    const prevStart = parseFloat(prev?.start_time);
    const prevEnd = parseFloat(prev?.end_time);
    const nextStart = parseFloat(next?.start_time);
    const nextEnd = parseFloat(next?.end_time);
    const range = normalizeAddRange(prevEnd, nextStart, prevStart, nextEnd);
    const cycleValue =
      String(
        (prev && prev.cycle) ||
          (next && next.cycle) ||
          (currentCycleSelection ? currentCycleSelection.cycleKey : '') ||
          '1'
      ).trim() || '1';
    const action = {
      index: '',
      label: '',
      is_process: '',
      is_move: '',
      is_check: '',
      is_wait: '',
      is_store: '',
      value_added: '',
      hands: '',
      variation: '',
      cycle: cycleValue,
      start_time: range.start,
      end_time: range.end
    };
    updateActionComputedFields(action);
    return action;
  }

  if (btnAddAction)
    btnAddAction.onclick = async () => {
      if (editingActionIndex === -1) return;
      hideContextMenu();

      const insertIndex = Math.min(
        Math.max(0, editingActionIndex + 1),
        Math.max(0, currentActions.length - 1)
      );
      const prev = currentActions[Math.max(0, insertIndex - 1)];
      const next = currentActions[insertIndex];
      const newAction = buildNewAction(prev, next);
      currentActions.splice(insertIndex, 0, newAction);
      rebuildActionIndexes();
      await persistActionsUpdate({ silentSuccess: true });
      openEditModal(insertIndex);
    };

  if (btnDeleteAction)
    btnDeleteAction.onclick = async () => {
      if (editingActionIndex === -1) return;
      if (currentActions.length <= 1) {
        notify(t('cannot_delete_last_action'));
        return;
      }
      hideContextMenu();

      const removed = currentActions.splice(editingActionIndex, 1)[0];
      normalizeActionTimeFields(removed || {});

      const next = currentActions[editingActionIndex];
      const prev = currentActions[editingActionIndex - 1];
      if (next) {
        normalizeActionTimeFields(next);
        const removedStart = parseFloat(removed?.start_time);
        const nextEnd = parseFloat(next.end_time);
        if (Number.isFinite(removedStart)) {
          const adjusted = Number.isFinite(nextEnd)
            ? Math.min(removedStart, nextEnd - minActionGap)
            : removedStart;
          next.start_time = adjusted;
          updateActionTimeRange(next);
        }
      } else if (prev) {
        normalizeActionTimeFields(prev);
        const removedEnd = parseFloat(removed?.end_time);
        const prevStart = parseFloat(prev.start_time);
        if (Number.isFinite(removedEnd)) {
          const adjusted = Number.isFinite(prevStart)
            ? Math.max(removedEnd, prevStart + minActionGap)
            : removedEnd;
          prev.end_time = adjusted;
          updateActionTimeRange(prev);
        }
      }

      rebuildActionIndexes();
      await persistActionsUpdate();
    };

  if (btnCancelEdit)
    btnCancelEdit.onclick = () => {
      if (elEditModal) elEditModal.classList.remove('open');
    };

  if (btnSaveEdit)
    btnSaveEdit.onclick = async () => {
      if (editingActionIndex === -1) return;

      const act = currentActions[editingActionIndex];
      const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : '';
      };

      const st = parseFloat(getVal('editStartTime'));
      const et = parseFloat(getVal('editEndTime'));

      // Validate time range against adjacent actions
      if (editingActionIndex > 0) {
        const prev = currentActions[editingActionIndex - 1];
        if (prev && Number.isFinite(parseFloat(prev.start_time))) {
          if (st < parseFloat(prev.start_time)) {
            notify(t('start_time_earlier_than_prev', { time: prev.start_time }));
            return;
          }
        }
      }

      if (editingActionIndex < currentActions.length - 1) {
        const next = currentActions[editingActionIndex + 1];
        if (next && Number.isFinite(parseFloat(next.end_time))) {
          if (et > parseFloat(next.end_time)) {
            notify(t('end_time_later_than_next', { time: next.end_time }));
            return;
          }
        }
      }

      if (Number.isFinite(st)) act.start_time = st;
      if (Number.isFinite(et)) act.end_time = et;
      
      // Ensure start <= end for current action
      if (act.start_time > act.end_time) {
        notify(t('start_time_later_than_end_time'));
        return;
      }
      updateActionComputedFields(act);

      // Update previous action's end time
      if (editingActionIndex > 0) {
        const prev = currentActions[editingActionIndex - 1];
        if (prev) {
          prev.end_time = act.start_time;
          updateActionComputedFields(prev);
        }
      }

      // Update next action's start time
      if (editingActionIndex < currentActions.length - 1) {
        const next = currentActions[editingActionIndex + 1];
        if (next) {
          next.start_time = act.end_time;
          updateActionComputedFields(next);
        }
      }

      act.label = getVal('editLabel');
      act.is_process = getVal('editIsProcess');
      act.is_move = getVal('editIsMove');
      act.is_check = getVal('editIsCheck');
      act.is_wait = getVal('editIsWait');
      act.is_store = getVal('editIsStore');
      act.value_added = getVal('editValueAdded');
      act.hands = getVal('editHands');
      act.variation = getVal('editVariation');

      if (elEditModal) elEditModal.classList.remove('open');
      await persistActionsUpdate();
    };
}
