"use client";

import { motion } from "framer-motion";
import {
  BookOpen,
  Brain,
  Layers,
  Pipette,
  Sparkles,
  Wrench,
} from "lucide-react";
import { BeforeAfter } from "@/components/documentation/BeforeAfter";
import { DocsMarkdown } from "@/components/documentation/DocsMarkdown";
import { DocsLangSwitcher } from "@/components/documentation/DocsLangSwitcher";
import { ProTip } from "@/components/documentation/ProTip";
import { TerminalSandbox } from "@/components/documentation/TerminalSandbox";
import { useDocsLocale } from "@/context/DocsLocaleContext";
import { getSkillsMasteryLocale } from "@/lib/skills-mastery-locales";
import type { SkillsMasteryLocale, SkillsMasterySection } from "@/lib/skills-mastery-types";
import { cn } from "@/lib/utils";

const SECTION_ICONS = {
  philosophy: Brain,
  anatomy: Layers,
  creation: Sparkles,
  patterns: Pipette,
  troubleshooting: Wrench,
  "try-it": Sparkles,
} as const;

function CodePanel({ label, children }: { label: string; children: string }) {
  return (
    <div className="my-5 overflow-hidden rounded-xl border border-white/[0.08] bg-[#050508] shadow-inner shadow-black/50">
      <div className="border-b border-white/[0.06] bg-[#111] px-4 py-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-cyan-400/70">
          {label}
        </span>
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-[11px] leading-relaxed text-emerald-300/90 sm:text-xs">
        <code>{children}</code>
      </pre>
    </div>
  );
}

function SectionHeading({
  id,
  icon: Icon,
  eyebrow,
  title,
  lead,
}: {
  id: string;
  icon: typeof Brain;
  eyebrow: string;
  title: string;
  lead: string;
}) {
  return (
    <header id={id} className="scroll-mt-24 border-b border-white/5 pb-6">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-400/80">
        {eyebrow}
      </p>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400/20 to-purple-500/20 ring-1 ring-white/10">
          <Icon className="h-5 w-5 text-cyan-400" />
        </div>
        <div>
          <h2 className="font-display text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {title}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
            {lead}
          </p>
        </div>
      </div>
    </header>
  );
}

function CodePanels({
  panels,
  code,
}: {
  panels: { label: string; codeKey: string }[];
  code: Record<string, string>;
}) {
  return (
    <>
      {panels.map((panel) => (
        <CodePanel key={panel.codeKey} label={panel.label}>
          {code[panel.codeKey] ?? ""}
        </CodePanel>
      ))}
    </>
  );
}

function MasterySection({
  section,
  locale,
}: {
  section: SkillsMasterySection;
  locale: SkillsMasteryLocale;
}) {
  const Icon = SECTION_ICONS[section.id as keyof typeof SECTION_ICONS] ?? Sparkles;
  const { code, labels } = locale;

  return (
    <section className="mb-16 space-y-6">
      <SectionHeading
        id={section.id}
        icon={Icon}
        eyebrow={section.eyebrow}
        title={section.title}
        lead={section.lead}
      />

      {section.paragraphs && (
        <div className="space-y-4">
          {section.paragraphs.map((p, i) => (
            <p key={i} className="text-sm leading-[1.75] text-muted sm:text-[15px]">
              {p}
            </p>
          ))}
        </div>
      )}

      {section.intro && (
        <p className="text-sm leading-[1.75] text-muted sm:text-[15px]">
          {section.intro}
        </p>
      )}

      {section.id === "patterns" && section.proTip && (
        <ProTip title={section.proTip.title}>{section.proTip.body}</ProTip>
      )}

      {section.beforeAfter && (
        <BeforeAfter
          before={section.beforeAfter.before}
          after={section.beforeAfter.after}
        />
      )}

      {section.proTip && section.beforeAfter && (
        <ProTip title={section.proTip.title}>{section.proTip.body}</ProTip>
      )}

      {section.designPrinciple && (
        <div className="rounded-xl border border-indigo-400/20 bg-indigo-500/5 p-5">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-indigo-300">
            {section.designPrinciple.label}
          </p>
          <p className="text-sm leading-relaxed text-foreground/90">
            {section.designPrinciple.body}
          </p>
        </div>
      )}

      {section.id === "anatomy" && section.codePanels?.[0] && (
        <CodePanel label={section.codePanels[0].label}>
          {code[section.codePanels[0].codeKey]}
        </CodePanel>
      )}

      {section.subsectionTitle && (
        <h3 className="font-display text-lg font-semibold text-white">
          {section.subsectionTitle}
        </h3>
      )}

      {section.id === "anatomy" && section.codePanels?.[1] && (
        <CodePanel label={section.codePanels[1].label}>
          {code[section.codePanels[1].codeKey]}
        </CodePanel>
      )}

      {section.id !== "anatomy" && section.id !== "patterns" && section.codePanels && (
        <CodePanels panels={section.codePanels} code={code} />
      )}

      {section.cards && (
        <div className="grid gap-4 sm:grid-cols-2">
          {section.cards.map((card, i) => (
            <div
              key={card.title}
              className={cn(
                "rounded-xl border p-4",
                i === 0
                  ? "border-cyan-400/20 bg-cyan-500/5"
                  : "border-purple-400/20 bg-purple-500/5",
              )}
            >
              <h4
                className={cn(
                  "mb-2 text-sm font-semibold",
                  i === 0 ? "text-cyan-400" : "text-purple-400",
                )}
              >
                {card.title}
              </h4>
              <p className="text-xs leading-relaxed text-muted">{card.body}</p>
            </div>
          ))}
        </div>
      )}

      {section.proTip && section.id === "anatomy" && (
        <ProTip title={section.proTip.title}>{section.proTip.body}</ProTip>
      )}

      {section.steps && (
        <ol className="space-y-4">
          {section.steps.map((item) => (
            <li
              key={item.step}
              className="flex gap-4 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4"
            >
              <span className="font-mono text-2xl font-bold text-cyan-400/40">
                {item.step}
              </span>
              <div>
                <h4 className="font-display font-semibold text-white">
                  {item.title}
                </h4>
                <p className="mt-1 text-sm leading-relaxed text-muted">
                  {item.body}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}

      {section.ioTable && (
        <>
          <h3 className="font-display text-base font-semibold text-cyan-400">
            {section.ioTable.title}
          </h3>
          <div className="overflow-x-auto rounded-xl border border-white/8">
            <table className="w-full min-w-[560px] border-collapse text-left text-xs">
              <thead>
                <tr className="bg-white/5 text-foreground">
                  {section.ioTable.headers.map((h) => (
                    <th
                      key={h}
                      className="border-b border-white/8 px-4 py-3 font-semibold"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="text-muted">
                {section.ioTable.rows.map((row, i) => (
                  <tr
                    key={i}
                    className="border-b border-white/5 transition-colors hover:bg-cyan-500/[0.03]"
                  >
                    {row.cells.map((cell, j) => (
                      <td
                        key={j}
                        className={cn(
                          "px-4 py-3",
                          j === 0 && "font-mono text-cyan-300/90",
                        )}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {section.id === "creation" && section.codePanels && (
        <CodePanels panels={section.codePanels} code={code} />
      )}

      {section.multiStepTitle && (
        <h3 className="font-display text-base font-semibold text-white">
          {section.multiStepTitle}
        </h3>
      )}

      {section.multiStepIntro && (
        <p className="text-sm leading-relaxed text-muted">
          {section.multiStepIntro}
        </p>
      )}

      {section.id === "patterns" && section.codePanels && (
        <CodePanels panels={section.codePanels} code={code} />
      )}

      {section.pipingMentalModelTitle && section.pipingTableMarkdown && (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
          <h4 className="mb-3 text-sm font-semibold text-foreground">
            {section.pipingMentalModelTitle}
          </h4>
          <DocsMarkdown content={section.pipingTableMarkdown} />
        </div>
      )}

      {section.troubleshootingRows && (
        <div className="overflow-x-auto rounded-xl border border-red-400/15">
          <table className="w-full min-w-[600px] border-collapse text-left text-xs">
            <thead>
              <tr className="bg-red-500/10 text-red-300">
                {labels.troubleshootingHeaders.map((h) => (
                  <th
                    key={h}
                    className="border-b border-red-400/20 px-4 py-3 font-semibold"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-muted">
              {section.troubleshootingRows.map((row, i) => (
                <tr
                  key={i}
                  className="border-b border-white/5 transition-colors hover:bg-red-500/[0.03]"
                >
                  {row.cells.map((cell, j) => (
                    <td
                      key={j}
                      className={cn(
                        "px-4 py-3",
                        j === 0 && "font-mono text-red-400/80",
                        j === 1 && "text-foreground/90",
                        j === 3 && "text-emerald-400/80",
                      )}
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {section.proTip && section.id === "troubleshooting" && (
        <ProTip title={section.proTip.title}>{section.proTip.body}</ProTip>
      )}

      {section.templateLabel && (
        <div className="rounded-xl border-2 border-dashed border-cyan-400/30 bg-cyan-500/[0.04] p-5">
          <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-cyan-400">
            {section.templateLabel}
          </p>
          <pre className="overflow-x-auto font-mono text-[11px] leading-relaxed text-foreground/90 sm:text-xs">
            {code.skillTemplate}
          </pre>
        </div>
      )}

      {section.sandbox && (
        <>
          <TerminalSandbox
            title={section.sandbox.title}
            placeholder={section.sandbox.placeholder}
            initial={section.sandbox.initial}
            scenarios={section.sandbox.scenarios}
          />
          <p className="text-center text-xs text-muted/70">
            {section.sandbox.footer}
          </p>
        </>
      )}
    </section>
  );
}

export function SkillsMasteryPage() {
  const { lang } = useDocsLocale();
  const data = getSkillsMasteryLocale(lang);

  return (
    <div className="flex h-[calc(100dvh-10rem)] min-h-[520px] flex-col overflow-hidden rounded-2xl border border-white/[0.06] bg-[#0a0a0a] sm:h-[calc(100dvh-8rem)]">
      <div className="border-b border-white/[0.06] bg-gradient-to-r from-[#111] via-[#0d0d14] to-[#111] px-5 py-6 sm:px-8">
        <div className="mx-auto flex max-w-5xl flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400/30 to-purple-500/30 ring-1 ring-white/10">
              <BookOpen className="h-7 w-7 text-cyan-400" />
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-purple-400/80">
                {data.meta.moduleLabel}
              </p>
              <h1 className="mt-1 font-display text-2xl font-bold text-white sm:text-3xl">
                {data.meta.title}
              </h1>
              <p className="mt-2 max-w-xl text-sm text-muted">{data.meta.lead}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <DocsLangSwitcher />
            <div className="flex items-center gap-2 rounded-xl border border-cyan-400/20 bg-cyan-500/5 px-3 py-2">
              <Sparkles className="h-4 w-4 text-cyan-400" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300">
                {data.meta.badge}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <nav className="hidden w-52 shrink-0 flex-col border-r border-white/[0.06] bg-[#08080c] lg:flex">
          <div className="border-b border-white/5 px-4 py-3">
            <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-muted">
              {data.meta.tocTitle}
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-3 logs-scroll">
            <ul className="space-y-1">
              {data.toc.map((item) => (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    className="block rounded-lg px-3 py-2 text-xs text-muted transition-colors hover:bg-white/5 hover:text-cyan-400"
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </nav>

        <div className="flex-1 overflow-y-auto logs-scroll">
          <motion.article
            key={lang}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mx-auto max-w-3xl px-5 py-8 sm:px-10 sm:py-12"
          >
            {data.sections.map((section) => (
              <MasterySection key={section.id} section={section} locale={data} />
            ))}
          </motion.article>
        </div>
      </div>
    </div>
  );
}
