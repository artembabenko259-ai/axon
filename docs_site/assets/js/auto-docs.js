/**
 * AXON Docs — auto-generated section from docs.json.
 */
(function (global) {
  async function loadDocsJson() {
    try {
      const res = await fetch('data/docs.json');
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  function renderAutoDocs(docs, t) {
    const root = document.getElementById('auto-docs-root');
    if (!root || !docs) {
      if (root) {
        const msg = window.location.protocol === 'file:'
          ? 'Project index is unavailable in offline file mode. Start the local documentation server (<code>python scripts/serve_docs.py</code>) to load your project data.'
          : (t?.autoDocs?.unavailable || 'Run /docs in AXON to generate project index.');
        root.innerHTML = `<p class="text-muted">${msg}</p>`;
      }
      return;
    }

    const stats = docs.stats || {};
    root.innerHTML = `
      <div class="callout tip">
        <strong>${docs.project}</strong> — ${stats.file_count || 0} files,
        ${stats.python_count || 0} Python modules,
        ${stats.class_count || 0} classes,
        ${stats.function_count || 0} symbols
        <br><small>Generated: ${new Date(docs.generated_at).toLocaleString()}</small>
      </div>
      <div class="auto-docs-grid" id="auto-docs-grid"></div>
      <div class="auto-docs-detail hidden" id="auto-docs-detail"></div>`;

    const grid = document.getElementById('auto-docs-grid');
    const pyFiles = Object.entries(docs.files || {})
      .filter(([, f]) => f.kind === 'python')
      .slice(0, 24);

    pyFiles.forEach(([path, file]) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'auto-docs-card';
      card.innerHTML = `
        <div class="name">🐍 ${file.name}</div>
        <div class="meta">${path}</div>`;
      card.addEventListener('click', () => showFileDetail(docs, path, t));
      grid.appendChild(card);
    });

    const link = document.createElement('a');
    link.href = 'explorer.html';
    link.className = 'auto-docs-card';
    link.target = '_blank';
    link.innerHTML = `
      <div class="name">📚 Full AST Explorer</div>
      <div class="meta">Open interactive docs.json viewer</div>`;
    grid.appendChild(link);
  }

  function showFileDetail(docs, path, t) {
    const detail = document.getElementById('auto-docs-detail');
    if (!detail) return;
    const file = docs.files[path];
    if (!file) return;

    let html = `<h3>${file.name}</h3><p>${file.summary || ''}</p>`;
    if (file.module_docstring) {
      html += `<p><em>${file.module_docstring}</em></p>`;
    }

    (file.functions || []).forEach((fn) => {
      html += `<p><code>${fn.signature}</code></p>`;
      if (fn.docstring) html += `<p>${fn.docstring}</p>`;
    });

    (file.classes || []).forEach((cls) => {
      html += `<h4>class ${cls.name}</h4>`;
      if (cls.docstring) html += `<p>${cls.docstring}</p>`;
      (cls.methods || []).forEach((m) => {
        html += `<p><code>${m.signature}</code></p>`;
      });
    });

    detail.classList.remove('hidden');
    detail.innerHTML = html;
    detail.scrollIntoView({ behavior: 'smooth' });
  }

  async function init(t) {
    const docs = await loadDocsJson();
    renderAutoDocs(docs, t);
  }

  global.AxonAutoDocs = { init, loadDocsJson, renderAutoDocs };
})(window);
