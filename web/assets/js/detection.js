import { currentLang, t } from './i18n.js';
import { appendLog, authFetch, currentUser, getToken, notify, setLog, switchTab, updateSidebarUserText, withMediaToken } from './core.js';
import { uploadVideoWithProgress } from './format.js';
import { currentScope, scopeQueryString } from './scope.js';
import { actionCountOverride, autoSelectResultByVideoPrefix, currentActions, loadResultList } from './review.js';


export async function loadVideoList() {
  const sel = document.getElementById('detectVideoSelect');
  if (!sel) return;
  try {
    const res = await authFetch('/api/list_videos' + scopeQueryString());
    const data = await res.json();
    sel.innerHTML = `<option value="">${t('select_video_placeholder')}</option>`;
    (data.files || []).forEach((f) => {
      const opt = document.createElement('option');
      opt.value = 'data/' + f;
      opt.textContent = f;
      sel.appendChild(opt);
    });
  } catch (e) {
    sel.innerHTML = `<option>${t('load_failed')}</option>`;
    console.error(e);
  }
}

export let detectLogCollapsed = true;
export let renderedLogCount = 0;
export let isPolling = false;

export function updateDetectLogToggleText() {
  const detectLogToggle = document.getElementById('btnToggleDetectLog');
  if (!detectLogToggle) return;
  detectLogToggle.textContent = detectLogCollapsed ? t('expand_log') : t('collapse_log');
}

export function refreshDynamicText() {
  updateSidebarUserText();
  updateDetectLogToggleText();

  const videoSel = document.getElementById('reviewVideoSelect');
  const videoName = document.getElementById('videoName');
  if (videoName) {
    if (videoSel && videoSel.value) videoName.textContent = videoSel.value;
    else videoName.textContent = t('review_no_video');
  }

  const actionCount = document.getElementById('actionCount');
  if (actionCount)
    actionCount.textContent = String(
      Number.isFinite(actionCountOverride) ? actionCountOverride : currentActions.length || 0
    );

  const btnUpload = document.getElementById('btnUpload');
  if (btnUpload) btnUpload.textContent = btnUpload.disabled ? t('uploading') : t('upload');

  const uploadInput = document.getElementById('uploadInput');
  const uploadFileName = document.getElementById('uploadFileName');
  if (uploadFileName) {
    if (uploadInput && uploadInput.files && uploadInput.files.length > 0) {
      uploadFileName.textContent = uploadInput.files[0].name;
    } else {
      uploadFileName.textContent = t('file_not_selected');
    }
  }

  const btnStartDetect = document.getElementById('btnStartDetect');
  if (btnStartDetect)
    btnStartDetect.textContent = btnStartDetect.disabled ? t('processing_detect') : t('start_detect');

  const btnMergeKaizen = document.getElementById('btnMergeKaizen');
  if (btnMergeKaizen)
    btnMergeKaizen.textContent = btnMergeKaizen.disabled ? t('merging') : t('merge');
}

export function setupDetectionUI() {
  const btnUpload = document.getElementById('btnUpload');
  const btnChooseFile = document.getElementById('btnChooseFile');
  const uploadInput = document.getElementById('uploadInput');
  const uploadFileName = document.getElementById('uploadFileName');
  const modelSelect = document.getElementById('detectModel');
  const fpsInput = document.getElementById('detectFps');
  const costDiv = document.getElementById('costEstimate');
  const btnEstimateCost = document.getElementById('btnEstimateCost');
  const detectVideoSelect = document.getElementById('detectVideoSelect');
  const detectLogPanel = document.getElementById('detectLog');
  const detectLogToggle = document.getElementById('btnToggleDetectLog');

  let selectedVideoDuration = 0;

  const updateDetectLogVisibility = (forceShow = false) => {
    if (!detectLogPanel) return;
    if (forceShow) detectLogCollapsed = false;
    detectLogPanel.style.display = detectLogCollapsed ? 'none' : 'block';
    updateDetectLogToggleText();
  };

  updateDetectLogVisibility();

  if (detectLogToggle) {
    detectLogToggle.addEventListener('click', () => {
      detectLogCollapsed = !detectLogCollapsed;
      updateDetectLogVisibility();
    });
  }

  if (btnChooseFile && uploadInput) {
    btnChooseFile.addEventListener('click', () => {
      uploadInput.click();
    });
  }

  if (uploadInput && uploadFileName) {
    uploadInput.addEventListener('change', () => {
      if (uploadInput.files && uploadInput.files.length > 0) {
        uploadFileName.textContent = uploadInput.files[0].name;
      } else {
        uploadFileName.textContent = t('file_not_selected');
      }
    });
  }

  function updateCost() {
    if (!costDiv) return;
    if (selectedVideoDuration === 0) {
      notify(t('select_video_for_duration'));
      costDiv.style.display = 'none';
      return;
    }

    if (!modelSelect || !fpsInput) return;
    const opt = modelSelect.selectedOptions[0];
    const priceIn = parseFloat(opt.dataset.priceIn);
    const priceOut = parseFloat(opt.dataset.priceOut);

    const fps = Math.min(3, Math.max(0.5, parseFloat(fpsInput.value) || 2.0));
    const tokensPerFrame = 258;
    const promptTokens = 800;
    const effectiveDuration = Math.min(selectedVideoDuration, 180);
    const frames = Math.ceil(effectiveDuration * fps);
    const visionTokens = frames * tokensPerFrame;
    const inputTokens = visionTokens + promptTokens;

    const outputTokens = Math.max(
      0,
      parseInt(document.getElementById('estimateOutTokens')?.value || '0', 10) || 0
    );
    const thinkingTokens = Math.max(
      0,
      parseInt(document.getElementById('estimateThinkingTokens')?.value || '0', 10) || 0
    );
    const billableOutputTokens = outputTokens + thinkingTokens;

    const costIn = (inputTokens / 1000000) * priceIn;
    const costOut = (billableOutputTokens / 1000000) * priceOut;
    const totalCost = costIn + costOut;

    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = String(value);
    };

    setText('costValue', totalCost.toFixed(4));
    setText('costDuration', effectiveDuration.toFixed(1));
    setText('costTokensIn', Math.round(inputTokens));
    setText('costTokensOut', Math.round(outputTokens));
    setText('costTokensThink', Math.round(thinkingTokens));

    setText('costT', effectiveDuration.toFixed(3));
    setText('costFps', fps.toFixed(3));
    setText('costFrames', frames);
    setText('costFrames2', frames);
    setText('costTokPerFrame', tokensPerFrame);
    setText('costVisionTokens', visionTokens);
    setText('costVisionTokens2', visionTokens);
    setText('costPromptTokens', promptTokens);
    setText('costInTokens', inputTokens);
    setText('costInTokens2', inputTokens);
    setText('costOutTokens', outputTokens);
    setText('costThinkTokens', thinkingTokens);
    setText('costBillableOutTokens', billableOutputTokens);
    setText('costBillableOutTokens2', billableOutputTokens);
    setText('costPriceIn', priceIn.toFixed(4));
    setText('costPriceOut', priceOut.toFixed(4));
    setText('costInUSD', costIn.toFixed(6));
    setText('costOutUSD', costOut.toFixed(6));
    setText('costTotalUSD2', totalCost.toFixed(6));
    costDiv.style.display = 'block';
  }

  if (btnEstimateCost) btnEstimateCost.addEventListener('click', updateCost);

  if (detectVideoSelect) {
    detectVideoSelect.addEventListener('change', async () => {
      selectedVideoDuration = 0;
      if (costDiv) costDiv.style.display = 'none';

      if (!detectVideoSelect.value) return;

      try {
        const res = await authFetch(
          '/api/video_info?path=' + encodeURIComponent(detectVideoSelect.value)
        );
        if (!res.ok) return;
        const info = await res.json();
        const d = Number(info.duration);
        if (Number.isFinite(d) && d > 0) {
          selectedVideoDuration = d;
        }
      } catch {
        selectedVideoDuration = 0;
      }
    });
  }

  if (btnUpload && uploadInput) {
    btnUpload.addEventListener('click', async () => {
      const file = uploadInput.files[0];
      if (!file) {
        notify(t('select_file_first'));
        return;
      }
      const stationWrapper = document.getElementById('uploadStationWrapper');
      const stationSelect = document.getElementById('uploadStationSelect');
      if (
        stationWrapper &&
        stationWrapper.style.display !== 'none' &&
        stationSelect &&
        !stationSelect.value
      ) {
        notify(t('station_select_required'));
        return;
      }
      const progressWrapper = document.getElementById('uploadProgressWrapper');
      const uploadBar = document.getElementById('uploadVideoProgressBar');
      const uploadText = document.getElementById('uploadVideoProgressText');
      const frameBar = document.getElementById('frameProgressBar');
      const frameText = document.getElementById('frameProgressText');

      if (progressWrapper) {
        progressWrapper.style.display = 'block';
        if (uploadBar) uploadBar.style.width = '0%';
        if (uploadText) uploadText.textContent = t('upload_in_progress');
        if (frameBar) frameBar.style.width = '0%';
        if (frameText) frameText.textContent = '';
      }

      btnUpload.disabled = true;
      btnUpload.textContent = t('uploading');

      try {
        const data = await uploadVideoWithProgress(file, uploadBar, uploadText);

        if (data.status === 'success') {
          // 服务端已完成统一转码（180s/720p），检测阶段直接上传整段视频，无需前端抽帧
          if (frameBar) frameBar.style.width = '100%';
          if (frameText) frameText.textContent = t('upload_success');

          notify(t('upload_success'));
          await loadVideoList();
          await window.refreshProjectWorkspace?.();
          const sel = document.getElementById('detectVideoSelect');
          if (sel) {
            sel.value = data.path;
            sel.dispatchEvent(new Event('change'));
          }
        } else {
          notify(t('upload_failed', { error: JSON.stringify(data) }));
        }
      } catch (e) {
        notify(t('upload_error', { error: e.message }));
      } finally {
        btnUpload.disabled = false;
        btnUpload.textContent = t('upload');
        uploadInput.value = '';
        if (uploadFileName) uploadFileName.textContent = t('file_not_selected');
        if (progressWrapper) {
          progressWrapper.style.display = 'none';
        }
        if (uploadBar) {
          uploadBar.style.width = '0%';
        }
        if (uploadText) {
          uploadText.textContent = '';
        }
        if (frameBar) {
          frameBar.style.width = '0%';
        }
        if (frameText) {
          frameText.textContent = '';
        }
      }
    });
  }

  const btnStartDetect = document.getElementById('btnStartDetect');
  if (btnStartDetect) {
    btnStartDetect.addEventListener('click', async () => {
      const videoPath = document.getElementById('detectVideoSelect')?.value;
      const modelSelect = document.getElementById('detectModel');
      let model = modelSelect?.value || '';
      if (!model && currentUser && typeof currentUser.model === 'string') {
        model = currentUser.model.trim();
      }
      if (!model) {
        model = 'kimi-2.5';
      }
      const fpsRaw = parseFloat(document.getElementById('detectFps')?.value);
      const fps = Number.isFinite(fpsRaw) ? Math.min(3, Math.max(0.5, fpsRaw)) : 2.0;
      const log = document.getElementById('detectLog');
      const btn = document.getElementById('btnStartDetect');
      const thumbnailContainer = document.getElementById('thumbnailContainer');
      const thumbnailImg = document.getElementById('detectThumbnail');

      if (!videoPath) {
        notify(t('select_video_first'));
        return;
      }

      if (btn) {
        btn.disabled = true;
        btn.textContent = t('processing_detect');
      }
      if (thumbnailContainer) thumbnailContainer.style.display = 'none';
      if (thumbnailImg) thumbnailImg.src = '';

      setLog(
        log,
        t('task_start_log', {
          time: new Date().toLocaleTimeString(),
          video: videoPath,
          model,
          fps
        })
      );
      renderedLogCount = 0;
      if (log) log.scrollTop = log.scrollHeight;

      if (log) {
        appendLog(
          log,
          t('request_params_log', {
            params: JSON.stringify({
              video_path: videoPath,
              model,
              fps,
              ui_lang: currentLang || 'zh',
              project_id: currentScope.project_id || undefined,
              line_id: currentScope.line_id || undefined
            })
          })
        );
        log.scrollTop = log.scrollHeight;
      }

      const taskRunningBar = document.getElementById('taskRunningBar');
      if (taskRunningBar) taskRunningBar.style.display = 'flex';

      try {
        const uiLang = currentLang || 'zh';
        const res = await authFetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-UI-Lang': uiLang },
          body: JSON.stringify({
            video_path: videoPath,
            model,
            fps,
            ui_lang: uiLang,
            project_id: currentScope.project_id || undefined,
            line_id: currentScope.line_id || undefined
          })
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.details || err.error || t('unknown_error'));
        }
        const started = await res.json().catch(() => ({}));
        if (started && typeof started.resolved_model === 'string' && started.resolved_model.trim()) {
          model = started.resolved_model.trim();
        }
        if (log) {
          appendLog(
            log,
            `[INFO] UI Lang: ${uiLang}; Prompt: ${started.prompt_path || 'unknown'}; Resolved Model: ${model}\n`
          );
          log.scrollTop = log.scrollHeight;
        }

        pollTaskStatus();
      } catch (e) {
        if (log) {
          appendLog(log, `[ERROR] ${e.message}\n`);
          log.scrollTop = log.scrollHeight;
        }
        notify(t('start_failed', { error: e.message }));

        if (taskRunningBar) taskRunningBar.style.display = 'none';
        if (btn) {
          btn.disabled = false;
          btn.textContent = t('start_detect');
        }
      }
    });
  }
}

export function updateProgressUI(taskData) {
  const pBar = document.getElementById('detectionProgressBar');
  const pText = document.getElementById('detectionProgressText');
  if (taskData.progress && pBar && pText) {
    const { current, total } = taskData.progress;
    if (total > 0) {
      const pct = Math.min(100, Math.max(0, (current / total) * 100)).toFixed(1);
      pBar.style.width = pct + '%';
      const progressKey = taskData.progress_unit === 'request' ? 'detect_progress_request' : 'detect_progress';
      pText.textContent = t(progressKey, { current, total, pct });
    } else {
      pBar.style.width = '0%';
      pText.textContent = t('prepare_text');
    }
  }
}

export function applyTaskData(data) {
  const log = document.getElementById('detectLog');
  if (!log || !data.logs) return;

  if (data.logs.length < renderedLogCount) {
    log.textContent = '';
    renderedLogCount = 0;
  }

  if (data.logs.length > renderedLogCount) {
    const fragment = document.createDocumentFragment();
    const newLogs = data.logs.slice(renderedLogCount);

    newLogs.forEach((line) => {
      appendLog(fragment, line);
    });

    log.appendChild(fragment);
    renderedLogCount = data.logs.length;
    log.scrollTop = log.scrollHeight;
  }
}

export function handleTaskCompleted(data, log) {
  if (!(data.result && log)) return;

  appendLog(
    log,
    t('task_complete', {
      time: new Date().toLocaleTimeString(),
      json: data.result.json_path,
      video: data.result.video_path
    })
  );
  appendLog(log, t('jump_to_review'));
  log.scrollTop = log.scrollHeight;

  setTimeout(async () => {
    switchTab('project');
    window.switchProjectTab?.('results');
    await window.refreshProjectWorkspace?.();
    loadResultList().then(() => {
      const resultSel = document.getElementById('reviewResultSelect');
      const videoSel = document.getElementById('reviewVideoSelect');
      if (!resultSel || !videoSel) return;
      const targetVideoName = data.result.video_path.split(/[/\\]/).pop();

      // Select video, which triggers autoSelectResultByVideoPrefix (handling language preference)
      Array.from(videoSel.options).forEach((o) => {
        if (o.value.includes(targetVideoName)) videoSel.value = o.value;
      });
      videoSel.dispatchEvent(new Event('change'));
    });
  }, 1500);
}

export function handleTaskFailed(data, log) {
  const errorMsg = data.error_msg || t('unknown_error');
  if (log) {
    appendLog(log, `[ERROR] ${errorMsg}\n`);
    log.scrollTop = log.scrollHeight;
  }
  notify(`${t('process_failed_check_log')}\n${t('reason')}: ${errorMsg}`);
}

/**
 * SSE 任务事件流（EventSource 无法携带 Authorization 头，通过 ?token= 鉴权）。
 * onPayload 收到每个状态事件，返回 true 表示终态已处理、流可关闭。
 * 返回 Promise<boolean>：true = SSE 已接管至终态；false = 不可用/中途断开，需回退轮询。
 */
export function streamTaskStatus(onPayload) {
  return new Promise((resolve) => {
    if (typeof EventSource === 'undefined') {
      resolve(false);
      return;
    }
    const token = getToken();
    if (!token) {
      resolve(false);
      return;
    }

    let es;
    try {
      es = new EventSource(withMediaToken('/api/task_events'));
    } catch (e) {
      console.warn('EventSource unavailable, fallback to polling:', e);
      resolve(false);
      return;
    }

    let settled = false;
    const finish = (handled) => {
      if (settled) return;
      settled = true;
      try {
        es.close();
      } catch {}
      resolve(handled);
    };

    es.addEventListener('status', (ev) => {
      let payload;
      try {
        payload = JSON.parse(ev.data);
      } catch {
        return;
      }
      let done = false;
      try {
        done = Boolean(onPayload(payload));
      } catch (e) {
        console.error('SSE payload handler error:', e);
      }
      if (done) finish(true);
    });
    es.onerror = () => finish(false); // 连接失败/中断：回退轮询
  });
}

export async function pollTaskStatus() {
  if (isPolling) return;

  try {
    const res = await authFetch('/api/task_status');
    if (!res.ok) return;
    const data = await res.json();

    if (data.status === 'none') {
      renderedLogCount = 0;
      return;
    }

    const log = document.getElementById('detectLog');
    const btn = document.getElementById('btnStartDetect');
    const taskRunningBar = document.getElementById('taskRunningBar');

    applyTaskData(data);

    if (data.status !== 'running') {
      return;
    }

    isPolling = true;
    if (btn) {
      btn.disabled = true;
      btn.textContent = t('processing_detect');
    }
    if (taskRunningBar) taskRunningBar.style.display = 'flex';

    updateProgressUI(data);

    // 单个任务数据的统一处理：进度 UI + 增量日志 + 终态分支。返回 true 表示已到终态。
    const consumeTaskData = (taskData) => {
      if (!currentUser) return true;

      updateProgressUI(taskData);
      applyTaskData(taskData);

      if (taskData.status === 'completed') {
        handleTaskCompleted(taskData, log);
        return true;
      }
      if (taskData.status === 'failed') {
        handleTaskFailed(taskData, log);
        return true;
      }
      if (taskData.status === 'none') {
        return true;
      }
      return false;
    };

    // 优先走 SSE 推送；不可用或中途断开时回退 2s 轮询
    const sseHandled = await streamTaskStatus(consumeTaskData);
    if (sseHandled) return;

    while (true) {
      await new Promise((r) => setTimeout(r, 2000));

      if (!currentUser) break;

      const pollRes = await authFetch('/api/task_status');
      if (!pollRes.ok) break;
      const pollData = await pollRes.json();

      if (consumeTaskData(pollData)) break;
    }
  } catch (e) {
    console.error('Polling error:', e);
  } finally {
    isPolling = false;
    const btn = document.getElementById('btnStartDetect');
    const taskRunningBar = document.getElementById('taskRunningBar');
    if (btn) {
      btn.disabled = false;
      btn.textContent = t('start_detect');
    }
    if (taskRunningBar) taskRunningBar.style.display = 'none';
  }
}
