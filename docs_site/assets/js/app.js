/**
 * AXON Docs — bootstrap entry point.
 */
(async function () {
  const pageId = document.body.dataset.page || 'intro';

  await AxonI18n.init();

  function paint() {
    const t = AxonI18n.data;
    const app = document.getElementById('axon-app');
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
