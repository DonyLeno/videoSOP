import { applyLanguage, currentLang, t } from './i18n.js';
import { applyTheme, authFetch, currentUser, notify } from './core.js';


export function setupSettingsUI() {
  const themeSelect = document.getElementById('settingsTheme');
  const langSelect = document.getElementById('settingsLang');
  let storedTheme = '';
  try {
    storedTheme = localStorage.getItem('ui_theme') || '';
  } catch {}
  const initialTheme = storedTheme === 'light' ? 'light' : 'dark';
  applyTheme(initialTheme);
  if (themeSelect) {
    themeSelect.value = initialTheme;
    themeSelect.addEventListener('change', () => {
      applyTheme(themeSelect.value);
    });
  }
  if (langSelect) {
    langSelect.value = currentLang;
    langSelect.addEventListener('change', () => {
      applyLanguage(langSelect.value);
    });
  }

  const dangerPanel = document.getElementById('settingsDangerPanel');
  const btnClearAll = document.getElementById('btnClearAllContent');
  if (dangerPanel && currentUser) {
    dangerPanel.style.display = currentUser.role === 'admin' ? 'block' : 'none';
  }
  if (btnClearAll) {
    btnClearAll.addEventListener('click', async () => {
      if (!window.confirm(t('settings_clear_all_confirm'))) return;
      btnClearAll.disabled = true;
      try {
        const res = await authFetch('/api/content/clear', { method: 'POST' });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          notify(data.details || data.error || t('settings_clear_all_failed'));
          return;
        }
        notify(t('settings_clear_all_done'));
        setTimeout(() => window.location.reload(), 800);
      } catch (e) {
        notify(e.message || t('settings_clear_all_failed'));
      } finally {
        btnClearAll.disabled = false;
      }
    });
  }
}

export function setupCalculatorUI() {
  const btnCalc = document.getElementById('btnDoCalculate');
  if (!btnCalc) return;
  btnCalc.addEventListener('click', () => {
    const inputTokens = parseFloat(document.getElementById('calcInputTokens')?.value) || 0;
    const outputTokens = parseFloat(document.getElementById('calcOutputTokens')?.value) || 0;

    const inputPricePer1k = 0.004;
    const outputPricePer1k = 0.021;

    const inputCost = (inputTokens / 1000) * inputPricePer1k;
    const outputCost = (outputTokens / 1000) * outputPricePer1k;
    const totalCost = inputCost + outputCost;

    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };
    setText('resInputCost', '¥' + inputCost.toFixed(4));
    setText('resOutputCost', '¥' + outputCost.toFixed(4));
    setText('resTotalCost', '¥' + totalCost.toFixed(4));

    const res = document.getElementById('calcResult');
    if (res) res.style.display = 'block';
  });
}
