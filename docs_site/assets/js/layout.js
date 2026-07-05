/**
 * AXON Docs — shared layout shell (nav, lang switcher, footer).
 */
(function (global) {
  const PAGES = [
    { id: 'intro', href: 'index.html', icon: '📖' },
    { id: 'commands', href: 'commands.html', icon: '⌨️' },
    { id: 'skills', href: 'skills.html', icon: '🧩' },
    { id: 'capabilities', href: 'capabilities.html', icon: '⚡' },
  ];

  function currentPage() {
    const path = window.location.pathname.split('/').pop() || 'index.html';
    if (path === 'index.html' || path === '') return 'intro';
    return path.replace('.html', '');
  }

  function renderLayout(container, t) {
    const page = currentPage();
    const nav = PAGES.map(
      (p) => `
      <a href="${p.href}" class="${page === p.id ? 'active' : ''}" data-nav="${p.id}">
        <span class="nav-icon">${p.icon}</span>
        <span data-i18n="nav.${p.id}">${t.nav[p.id]}</span>
      </a>`
    ).join('');

    container.innerHTML = `
      <aside class="axon-sidebar" id="axon-sidebar">
        <div class="axon-logo">
          <div class="axon-logo-mark">AX</div>
          <div>
            <h1>AXON</h1>
            <span data-i18n="meta.subtitle">${t.meta.subtitle}</span>
          </div>
        </div>
        <nav class="axon-nav">${nav}</nav>
        ${window.location.protocol === 'file:' ? `
          <div style="margin: 15px; padding: 12px; border-radius: 8px; background: rgba(220,100,0,0.08); border: 1px solid rgba(220,100,0,0.25); font-size: 11px; line-height: 1.4; color: #ffb066;">
            <div style="font-weight: 600; margin-bottom: 4px; display: flex; items-center: center; gap: 4px;">⚠️ Offline Mode</div>
            Using offline fallback. Start local server to load other languages/data:<br>
            <code style="display: block; font-family: monospace; background: rgba(0,0,0,0.2); padding: 4px; border-radius: 4px; margin-top: 6px; font-size: 10px; word-break: break-all;">python scripts/serve_docs.py</code>
          </div>
        ` : ''}
        <div class="axon-lang-switcher" id="lang-switcher">
          <button type="button" data-lang="en" class="${global.AxonI18n?.lang === 'en' ? 'active' : ''}">EN</button>
          <button type="button" data-lang="ru" class="${global.AxonI18n?.lang === 'ru' ? 'active' : ''}">RU</button>
          <button type="button" data-lang="ua" class="${global.AxonI18n?.lang === 'ua' ? 'active' : ''}">UA</button>
        </div>
      </aside>
      <div class="axon-main">
        <div class="axon-content" id="page-root"></div>
        <footer class="axon-footer axon-content">
          <span data-i18n="meta.footer">${t.meta.footer}</span>
        </footer>
      </div>`;

    document.getElementById('lang-switcher')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-lang]');
      if (!btn) return;
      global.AxonI18n?.setLanguage(btn.dataset.lang);
    });
  }

  global.AxonLayout = { renderLayout, currentPage, PAGES };
})(window);
