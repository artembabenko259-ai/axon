/**
 * AXON Docs — page renderers driven by i18n JSON.
 */
(function (global) {
  const C = () => global.AxonComponents;

  function renderIntro(t) {
    const d = t.intro;
    let html = C().hero(d.title, d.lead);

    d.sections.forEach((sec) => {
      let body = C().paragraphs(sec.paragraphs);
      if (sec.list) body += C().list(sec.list, sec.ordered);
      if (sec.callout) body += C().callout(sec.callout.text, sec.callout.type || 'info');
      (sec.code || []).forEach((c) => { body += C().codeBlock(c.source, c.lang, c.label); });
      html += C().section(sec.title, body, sec.id);
    });

    if (d.tryTerminal) {
      html += C().section(d.tryTerminal.title, C().tryTerminal(d.tryTerminal));
    }

    if (t.autoDocs) {
      html += C().section(
        t.autoDocs.title,
        C().paragraphs(t.autoDocs.paragraphs) +
          '<div id="auto-docs-root"></div>'
      );
    }

    return html;
  }

  function renderCommands(t) {
    const d = t.commands;
    let html = C().hero(d.title, d.lead);
    html += C().section(
      d.reference.title,
      C().paragraphs(d.reference.paragraphs) +
        C().commandTable(d.reference.rows, d.reference.headers)
    );

    (d.examples || []).forEach((ex) => {
      html += C().commandExampleCard(ex.title, ex.input, ex.output);
    });

    d.sections.forEach((sec) => {
      let body = C().paragraphs(sec.paragraphs);
      if (sec.list) body += C().list(sec.list);
      (sec.code || []).forEach((c) => { body += C().codeBlock(c.source, c.lang, c.label); });
      html += C().section(sec.title, body, sec.id);
    });

    if (d.tryTerminal) {
      html += C().section(d.tryTerminal.title, C().tryTerminal(d.tryTerminal));
    }

    return html;
  }

  function renderSkills(t) {
    const d = t.skills;
    let html = C().hero(d.title, d.lead);

    d.sections.forEach((sec) => {
      let body = C().paragraphs(sec.paragraphs);
      if (sec.list) body += C().list(sec.list, sec.ordered);
      if (sec.callout) body += C().callout(sec.callout.text, sec.callout.type || 'info');
      (sec.code || []).forEach((c) => { body += C().codeBlock(c.source, c.lang, c.label); });
      html += C().section(sec.title, body, sec.id);
    });

    if (d.tryTerminal) {
      html += C().section(d.tryTerminal.title, C().tryTerminal(d.tryTerminal));
    }

    return html;
  }

  function renderCapabilities(t) {
    const d = t.capabilities;
    let html = C().hero(d.title, d.lead);

    d.sections.forEach((sec) => {
      let body = C().paragraphs(sec.paragraphs);
      if (sec.list) body += C().list(sec.list, sec.ordered);
      if (sec.callout) body += C().callout(sec.callout.text, sec.callout.type || 'info');
      (sec.code || []).forEach((c) => { body += C().codeBlock(c.source, c.lang, c.label); });
      html += C().section(sec.title, body, sec.id);
    });

    return html;
  }

  const RENDERERS = {
    intro: renderIntro,
    commands: renderCommands,
    skills: renderSkills,
    capabilities: renderCapabilities,
  };

  function renderPage(pageId, translations) {
    const fn = RENDERERS[pageId];
    if (!fn) return '<p>Page not found.</p>';
    return fn(translations);
  }

  global.AxonRenderer = { renderPage, RENDERERS };
})(window);
