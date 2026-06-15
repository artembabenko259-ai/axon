"use client";

import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { DocsLangSwitcher } from "@/components/documentation/DocsLangSwitcher";
import { DocsSubsectionContent } from "@/components/documentation/DocsSubsectionContent";
import { useDocsLocale } from "@/context/DocsLocaleContext";
import { cn } from "@/lib/utils";

export function DocumentationPanel() {
  const { locale } = useDocsLocale();
  const [sectionIdx, setSectionIdx] = useState(0);
  const [subIdx, setSubIdx] = useState(0);

  useEffect(() => {
    setSectionIdx(0);
    setSubIdx(0);
  }, [locale]);

  const currentSection = locale.sections[sectionIdx];
  const currentSub = currentSection?.subsections[subIdx];

  const flatPages = useMemo(() => {
    const pages: { sectionIdx: number; subIdx: number }[] = [];
    locale.sections.forEach((sec, si) => {
      sec.subsections.forEach((_, subi) => {
        pages.push({ sectionIdx: si, subIdx: subi });
      });
    });
    return pages;
  }, [locale.sections]);

  const currentPageIdx = useMemo(
    () =>
      flatPages.findIndex(
        (p) => p.sectionIdx === sectionIdx && p.subIdx === subIdx,
      ),
    [flatPages, sectionIdx, subIdx],
  );

  const goPage = useCallback(
    (delta: number) => {
      const next = currentPageIdx + delta;
      if (next < 0 || next >= flatPages.length) return;
      const p = flatPages[next];
      setSectionIdx(p.sectionIdx);
      setSubIdx(p.subIdx);
    },
    [currentPageIdx, flatPages],
  );

  const selectSection = useCallback(
    (si: number) => {
      setSectionIdx(si);
      setSubIdx(0);
    },
    [],
  );

  return (
    <div className="flex h-[calc(100dvh-10rem)] min-h-[520px] flex-col overflow-hidden rounded-2xl border border-white/[0.06] bg-[#0a0a0a] sm:h-[calc(100dvh-8rem)]">
      {/* Book header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] bg-gradient-to-r from-[#111] to-[#0d0d12] px-4 py-3 sm:px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400/25 to-purple-500/25 ring-1 ring-white/10">
            <BookOpen className="h-5 w-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="font-display text-sm font-semibold tracking-wide text-white">
              {locale.meta.title}
            </h2>
            <p className="text-[10px] text-muted">
              {locale.meta.bookSubtitle}
              {locale.meta.totalPages != null && (
                <span className="ml-2 font-mono text-cyan-400/70">
                  · {locale.meta.totalPages} pages
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DocsLangSwitcher />
          <a
            href="/docs/skills"
            className="rounded-lg border border-purple-400/25 bg-purple-500/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-purple-300 transition-colors hover:bg-purple-500/20"
          >
            Skills Mastery →
          </a>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* Chapter sidebar — book spine */}
        <nav className="hidden w-56 shrink-0 flex-col border-r border-white/[0.06] bg-[#08080c] md:flex">
          <div className="border-b border-white/5 px-4 py-3">
            <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-muted">
              Chapters
              {locale.meta.chapterCount != null && (
                <span className="ml-1 text-muted/60">
                  ({locale.sections.length})
                </span>
              )}
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 logs-scroll">
            {locale.sections.map((section, si) => (
              <div key={section.id} className="mb-2">
                <button
                  type="button"
                  onClick={() => selectSection(si)}
                  className={cn(
                    "w-full rounded-lg px-3 py-2 text-left transition-all",
                    sectionIdx === si
                      ? "bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-400/20"
                      : "text-muted hover:bg-white/5 hover:text-foreground",
                  )}
                >
                  <span className="font-mono text-[10px] text-muted/60">
                    Ch. {section.chapter}
                  </span>
                  <p className="text-xs font-medium">{section.title}</p>
                </button>
                {sectionIdx === si && (
                  <div className="mt-1 space-y-0.5 border-l border-cyan-400/20 pl-3 ml-2">
                    {section.subsections.map((sub, subi) => (
                      <button
                        key={sub.id}
                        type="button"
                        onClick={() => {
                          setSectionIdx(si);
                          setSubIdx(subi);
                        }}
                        className={cn(
                          "block w-full py-1.5 text-left text-[11px] transition-colors",
                          subIdx === subi
                            ? "text-cyan-300"
                            : "text-muted/70 hover:text-muted",
                        )}
                      >
                        <span className="font-mono text-[9px] text-muted/50 mr-1">
                          p.{sub.page ?? subi + 1}
                        </span>
                        {sub.title}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </nav>

        {/* Book page */}
        <div className="relative flex min-w-0 flex-1 flex-col">
          <div className="flex gap-1 overflow-x-auto border-b border-white/[0.06] bg-[#111] p-2 md:hidden logs-scroll">
            {locale.sections.map((section, si) => (
              <button
                key={section.id}
                type="button"
                onClick={() => selectSection(si)}
                className={cn(
                  "shrink-0 rounded-lg px-3 py-1.5 text-[10px]",
                  sectionIdx === si
                    ? "bg-cyan-500/20 text-cyan-400"
                    : "text-muted",
                )}
              >
                Ch.{section.chapter}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-6 logs-scroll sm:px-8 sm:py-8">
            <div className="mx-auto max-w-2xl">
              {/* Page chrome */}
              <div className="mb-6 flex items-center justify-between border-b border-white/5 pb-4">
                <div>
                  <p className="font-mono text-[10px] text-cyan-400/70">
                    Chapter {currentSection?.chapter} · Page{" "}
                    {currentPageIdx + 1} of {flatPages.length}
                  </p>
                  <h3 className="mt-1 font-display text-xl font-semibold text-white">
                    {currentSection?.title}
                  </h3>
                  <p className="mt-0.5 text-xs text-muted">{currentSection?.lead}</p>
                </div>
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={`${sectionIdx}-${subIdx}-${locale.meta.title}`}
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ duration: 0.3 }}
                  className="rounded-2xl border border-white/[0.04] bg-white/[0.02] p-5 sm:p-7"
                >
                  {currentSub && (
                    <>
                      <h4 className="mb-5 font-display text-base font-medium text-cyan-400">
                        {currentSub.title}
                      </h4>
                      <DocsSubsectionContent subsection={currentSub} />
                    </>
                  )}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>

          {/* Page turn controls */}
          <div className="flex items-center justify-between border-t border-white/[0.06] bg-[#111] px-4 py-2">
            <button
              type="button"
              onClick={() => goPage(-1)}
              disabled={currentPageIdx <= 0}
              className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs text-muted transition-colors hover:bg-white/5 hover:text-foreground disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <span className="font-mono text-[10px] text-muted">
              {currentSub?.title}
            </span>
            <button
              type="button"
              onClick={() => goPage(1)}
              disabled={currentPageIdx >= flatPages.length - 1}
              className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs text-muted transition-colors hover:bg-white/5 hover:text-foreground disabled:opacity-30"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
