/**
 * AXON Docs — i18n loader and language persistence.
 */
(function (global) {
  const STORAGE_KEY = 'axon-docs-lang';
  let translations = null;
  let lang = localStorage.getItem(STORAGE_KEY) || 'en';
  const listeners = [];

  async function load(langCode) {
    const res = await fetch(`i18n/${langCode}.json`);
    if (!res.ok) throw new Error(`Failed to load i18n/${langCode}.json`);
    translations = await res.json();
    lang = langCode;
    localStorage.setItem(STORAGE_KEY, langCode);
    document.documentElement.lang = langCode === 'ua' ? 'uk' : langCode;
    return translations;
  }

  function t(key) {
    if (!translations) return key;
    const parts = key.split('.');
    let cur = translations;
    for (const p of parts) {
      if (cur == null) return key;
      cur = cur[p];
    }
    return cur ?? key;
  }

  function onChange(fn) {
    listeners.push(fn);
  }

  async function setLanguage(code) {
    await load(code);
    listeners.forEach((fn) => fn(translations, code));
  }

  async function init() {
    try {
      await load(lang);
    } catch {
      try {
        await load('en');
      } catch (err) {
        console.warn("Failed to load i18n via fetch. Falling back to offline translations.", err);
        translations = global.AxonFallbackEN || null;
      }
    }
    return translations;
  }

  global.AxonI18n = {
    init,
    load,
    setLanguage,
    onChange,
    t,
    get lang() { return lang; },
    get data() { return translations; },
  };
})(window);
