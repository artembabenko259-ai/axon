"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getDocsLocale, DOCS_LANGS } from "@/lib/docs-locales";
import type { DocsLang, DocsLocale } from "@/lib/docs-types";

const STORAGE_KEY = "axon-docs-lang";

interface DocsLocaleContextValue {
  lang: DocsLang;
  locale: DocsLocale;
  setLang: (lang: DocsLang) => void;
}

const DocsLocaleContext = createContext<DocsLocaleContextValue | null>(null);

function loadLang(): DocsLang {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && DOCS_LANGS.includes(stored as DocsLang)) {
    return stored as DocsLang;
  }
  return "en";
}

export function DocsLocaleProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<DocsLang>("en");

  useEffect(() => {
    setLangState(loadLang());
  }, []);

  const setLang = useCallback((next: DocsLang) => {
    setLangState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const locale = useMemo(() => getDocsLocale(lang), [lang]);

  const value = useMemo(
    () => ({ lang, locale, setLang }),
    [lang, locale, setLang],
  );

  return (
    <DocsLocaleContext.Provider value={value}>
      {children}
    </DocsLocaleContext.Provider>
  );
}

export function useDocsLocale() {
  const ctx = useContext(DocsLocaleContext);
  if (!ctx) {
    throw new Error("useDocsLocale must be used within DocsLocaleProvider");
  }
  return ctx;
}
