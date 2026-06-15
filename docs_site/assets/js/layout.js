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
