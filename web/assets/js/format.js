import { t } from './i18n.js';
import { getToken, setLoginActive, setToken } from './core.js';
import { scopeQueryString } from './scope.js';

export function formatBytes(bytes) {
  if (!bytes) return '-';
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) return mb.toFixed(2) + ' MB';
  return (mb / 1024).toFixed(2) + ' GB';
}

export function formatRole(role) {
  return role === 'admin' ? t('role_admin') : t('role_user');
}

export function formatModel(model) {
  if (!model) return '-';
  const map = {
    'kimi-2.5': 'GeniviewK2.5'
  };
  return map[model] || model;
}

export function formatStatus(status) {
  return status === 'inactive' ? t('status_inactive') : t('status_active');
}

export function formatTime(value) {
  if (!value) return '-';
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return String(value);
  return dt.toLocaleString();
}

export function maskApiKey(value) {
  const raw = (value || '').trim();
  if (!raw) return '-';
  const head = raw.slice(0, 8);
  return `${head}******`;
}

export function uploadVideoWithProgress(file, barEl, textEl) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload' + scopeQueryString(), true);
    const token = getToken();
    if (token) xhr.setRequestHeader('Authorization', 'Bearer ' + token);
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.setRequestHeader('X-Filename', encodeURIComponent(file.name));
    xhr.upload.onprogress = function (e) {
      if (e.lengthComputable && barEl) {
        const pct = Math.round((e.loaded / e.total) * 100);
        barEl.style.width = pct + '%';
      }
      if (textEl) textEl.textContent = t('upload_in_progress');
    };
    xhr.onerror = function () {
      reject(new Error(t('network_error')));
    };
    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          try {
            const data = JSON.parse(xhr.responseText || '{}');
            if (barEl) barEl.style.width = '100%';
            resolve(data);
          } catch (err) {
            reject(err);
          }
        } else if (xhr.status === 401) {
          setToken('');
          setLoginActive(true);
          reject(new Error(t('not_logged_in_or_expired')));
        } else if (xhr.status === 0) {
          reject(new Error(t('upload_timeout')));
        } else {
          reject(new Error('HTTP ' + xhr.status));
        }
      }
    };
    xhr.send(file);
  });
}
export function getBaseName(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  const parts = text.split('/');
  return parts[parts.length - 1] || text;
}
