import { applyLanguage, getStoredLang, t } from './i18n.js';
import { fetchVersion, initSidebar, notify, setupAuthUI, switchTab } from './core.js';
import { setupUserManagement } from './users.js';
import { setupProjectUI } from './projects.js';
import { setupDetectionUI } from './detection.js';
import { exportActionsCsv, loadResultList, setupReviewUI, showRevisionHistory } from './review.js';
import { setupCalculatorUI, setupSettingsUI } from './settings.js';

// HTML 内联事件桥接：模块作用域函数挂到 window（index.html / partials 的内联 onclick 需要）
// 必须放在模块顶层尽早执行，避免后续任何初始化异常导致侧边栏点击失效
Object.assign(window, {
  switchTab,
  loadResultList,
  exportActionsCsv,
  showRevisionHistory,
});

async function loadPartials() {
  // 支持嵌套 include：项目工作区会继续加载检测、结果、设置面板
  for (let depth = 0; depth < 5; depth += 1) {
    const targets = Array.from(document.querySelectorAll('[data-include]'));
    if (!targets.length) return;
    await Promise.all(
      targets.map(async (el) => {
        const url = el.getAttribute('data-include');
        if (!url) return;
        el.removeAttribute('data-include');
        const res = await fetch(url, { cache: 'no-cache' });
        if (!res.ok)
          throw new Error(t('load_failed_with_status', { url, status: res.status }));
        el.innerHTML = await res.text();
      })
    );
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await loadPartials();
  } catch (e) {
    console.error(e);
    notify(t('page_load_failed', { error: e.message }));
  }

  applyLanguage(getStoredLang());
  initSidebar();
  setupProjectUI();
  setupUserManagement();
  setupDetectionUI();
  setupReviewUI();
  setupSettingsUI();
  setupCalculatorUI();
  setupAuthUI();
});

