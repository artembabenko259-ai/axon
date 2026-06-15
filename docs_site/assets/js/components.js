/**
 * AXON Docs — reusable UI components (code blocks, terminal, sections).
 */
(function (global) {
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function codeBlock(source, language = 'text', label = '') {
    const id = 'code-' + Math.random().toString(36).slice(2, 9);
    const highlighted = global.Prism
      ? global.Prism.highlight(source, global.Prism.languages[language] || global.Prism.languages.text, language)
      : escapeHtml(source);

    return `
      <div class="code-block" data-code-id="${id}">
        <div class="code-block-header">
          <span>${escapeHtml(label || language)}</span>
          <button type="button" class="copy-btn" data-copy="${id}" aria-label="Copy">Copy</button>
        </div>
        <pre><code id="${id}" class="language-${language}">${highlighted}</code></pre>
      </div>`;
  }

  function bindCopyButtons(root) {
    root.querySelectorAll('.copy-btn[data-copy]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const code = document.getElementById(btn.dataset.copy);
        if (!code) return;
        try {
          await navigator.clipboard.writeText(code.textContent);
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          setTimeout(() => {
            btn.textContent = 'Copy';
            btn.classList.remove('copied');
          }, 2000);
        } catch { /* ignore */ }
      });
    });
  }

  function section(title, bodyHtml, id = '') {
    return `
      <section class="doc-section" ${id ? `id="${id}"` : ''}>
        <h2>${escapeHtml(title)}</h2>
        ${bodyHtml}
      </section>`;
  }

  function callout(text, type = 'info') {
    return `<div class="callout ${type}">${text}</div>`;
  }

  function paragraphs(items) {
    return (items || []).map((p) => `<p>${p}</p>`).join('');
  }

  function list(items, ordered = false) {
    const tag = ordered ? 'ol' : 'ul';
    return `<${tag}>${(items || []).map((i) => `<li>${i}</li>`).join('')}</${tag}>`;
  }

  function tryTerminal(config) {
    const id = 'try-' + Math.random().toString(36).slice(2, 9);
    const scenariosB64 = btoa(unescape(encodeURIComponent(JSON.stringify(config.scenarios || {}))));
    return `
      <div class="try-terminal" data-try-id="${id}" data-scenarios-b64="${scenariosB64}">
        <div class="try-terminal-header">
          <div class="try-terminal-dots"><span></span><span></span><span></span></div>
          <span>${escapeHtml(config.title || 'Try it')}</span>
        </div>
        <div class="try-terminal-body">
          <div class="try-terminal-output" id="${id}-out">${escapeHtml(config.initial || '$ axon\nAXON v1.0.0 — Ready\n')}</div>
          <div class="try-terminal-input-row">
            <span class="try-terminal-prompt">❯</span>
            <input type="text" class="try-terminal-input" id="${id}-in"
              placeholder="${escapeHtml(config.placeholder || '/help')}" autocomplete="off" />
          </div>
          <button type="button" class="try-terminal-run" data-try-run="${id}">
            ${escapeHtml(config.button || 'Run command')}
          </button>
        </div>
      </div>`;
  }

  function bindTryTerminals(root) {
    root.querySelectorAll('[data-try-run]').forEach((btn) => {
      const id = btn.dataset.tryRun;
      const terminal = btn.closest('.try-terminal');
      let scenarios = {};
      try {
        const raw = terminal.dataset.scenariosB64 || '';
        scenarios = JSON.parse(decodeURIComponent(escape(atob(raw))));
      } catch { /* ignore */ }
      const input = document.getElementById(`${id}-in`);
      const output = document.getElementById(`${id}-out`);

      const run = () => {
        const cmd = (input.value || '').trim();
        if (!cmd) return;
        const response = scenarios[cmd] || scenarios['*'] || 'AXON: Unknown command. Type /help.';
        const prev = output.textContent;
        output.textContent = prev + `\n❯ ${cmd}\n${response}\n`;
        input.value = '';
        output.scrollTop = output.scrollHeight;
      };

      btn.addEventListener('click', run);
      input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') run();
      });
    });
  }

  function commandTable(rows, headers) {
    const body = rows.map(
      (r) => `
      <tr>
        <td><code>${escapeHtml(r.command)}</code></td>
        <td>${r.description}</td>
        <td>${r.example || '—'}</td>
      </tr>`
    ).join('');

    return `
      <div class="doc-table-wrap">
        <table class="doc-table">
          <thead>
            <tr>
              <th>${escapeHtml(headers?.command || 'Command')}</th>
              <th>${escapeHtml(headers?.description || 'Description')}</th>
              <th>${escapeHtml(headers?.example || 'Example')}</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>
      </div>`;
  }

  function commandExampleCard(title, inputCode, outputCode) {
    return `
      <div class="cmd-example">
        <h4>${escapeHtml(title)}</h4>
        ${codeBlock(inputCode, 'bash', 'Input')}
        ${codeBlock(outputCode, 'text', 'Output')}
      </div>`;
  }

  function hero(title, lead) {
    return `
      <header class="axon-hero">
        <h1>${escapeHtml(title)}</h1>
        <p class="lead">${lead}</p>
      </header>`;
  }

  function initPage(root) {
    bindCopyButtons(root);
    bindTryTerminals(root);
  }

  global.AxonComponents = {
    escapeHtml,
    codeBlock,
    section,
    callout,
    paragraphs,
    list,
    tryTerminal,
    commandTable,
    commandExampleCard,
    hero,
    initPage,
    bindCopyButtons,
  };
})(window);
