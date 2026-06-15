"use client";

import { cn } from "@/lib/utils";
import { DOCS_LANGS, DOCS_LANG_LABELS } from "@/lib/docs-locales";
import { useDocsLocale } from "@/context/DocsLocaleContext";
import type { DocsLang } from "@/lib/docs-types";

export function DocsLangSwitcher({ className }: { className?: string }) {
  const { lang, setLang } = useDocsLocale();

  return (
    <div
      className={cn(
        "flex items-center gap-1 rounded-lg border border-white/8 bg-white/3 p-0.5",
        className,
      )}
      role="group"
      aria-label="Documentation language"
    >
      {DOCS_LANGS.map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => setLang(code as DocsLang)}
          className={cn(
            "rounded-md px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition-all",
            lang === code
              ? "bg-cyan-500/20 text-cyan-400 ring-1 ring-cyan-400/30"
              : "text-muted hover:text-foreground",
          )}
        >
          {DOCS_LANG_LABELS[code]}
        </button>
      ))}
    </div>
  );
}
