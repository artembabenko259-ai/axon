/**
 * AXON Docs — bootstrap entry point.
 */
(async function () {
  const pageId = document.body.dataset.page || 'intro';

  await AxonI18n.init();

  function paint() {
    const t = AxonI18n.data;
    const app = document.getElementById('axon-app');
    if (!t) {
      app.innerHTML = `
        <div style="max-width: 500px; margin: 100px auto; padding: 30px; border-radius: 12px; background: #12151c; border: 1px solid #1e2430; color: #e8ecf4; font-family: system-ui, sans-serif; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          <div style="font-size: 40px; margin-bottom: 20px;">⚠️</div>
          <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 10px; color: #ffb066;">Documentation Loading Blocked</h2>
          <p style="font-size: 14px; color: #8b95a8; line-height: 1.6; margin-bottom: 20px;">
            Your browser's security policy blocks loading translation files directly via the <code>file://</code> protocol.
          </p>
          <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 12px; color: #4466ff; margin-bottom: 20px; text-align: left; border: 1px solid rgba(68,102,255,0.2);">
            python scripts/serve_docs.py
          </div>
          <p style="font-size: 12px; color: #8b95a8;">
            Please run the command above to start the documentation server and open <a href="http://localhost:8000" style="color: #4466ff; text-decoration: underline;">http://localhost:8000</a>.
          </p>
        </div>
      `;
      return;
    }
    AxonLayout.renderLayout(app, t);

    const root = document.getElementById('page-root');
    root.innerHTML = AxonRenderer.renderPage(pageId, t);
    AxonComponents.initPage(root);

    if (pageId === 'intro') {
      AxonAutoDocs.init(t);
    }

    document.title = `${t.meta.title} — ${t[pageId]?.title || pageId}`;
  }

  AxonI18n.onChange(() => paint());
  paint();
})();
