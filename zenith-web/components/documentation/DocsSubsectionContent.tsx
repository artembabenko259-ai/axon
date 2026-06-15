"use client";

import type { DocAnimation, DocExample, DocFailureMode } from "@/lib/docs-types";
import { DocsMarkdown } from "@/components/documentation/DocsMarkdown";
import { StepsTable } from "@/components/documentation/StepsTable";
import { BeforeAfter } from "@/components/documentation/BeforeAfter";
import { AnimationPlaceholder } from "@/components/documentation/AnimationPlaceholder";
import { TerminalSandbox } from "@/components/documentation/TerminalSandbox";

function FailureModeBlock({ failureMode }: { failureMode: DocFailureMode }) {
  return (
    <div className="my-6 rounded-xl border border-red-400/25 bg-red-500/5 p-4">
      <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-red-400">
        Failure Mode — {failureMode.title}
      </p>
      <DocsMarkdown content={failureMode.markdown} />
    </div>
  );
}

function ExamplesBlock({ examples }: { examples: DocExample[] }) {
  return (
    <div className="my-6 space-y-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-cyan-400/80">
        Practical Examples ({examples.length})
      </p>
      {examples.map((ex, i) => (
        <div
          key={i}
          className="rounded-xl border border-white/6 bg-white/[0.02] p-4"
        >
          <h6 className="mb-2 text-sm font-medium text-foreground">
            {ex.title}
          </h6>
          <DocsMarkdown content={ex.markdown} />
        </div>
      ))}
    </div>
  );
}

function AnimationsBlock({ animations }: { animations: DocAnimation[] }) {
  return (
    <div className="space-y-4">
      {animations.map((anim) => (
        <AnimationPlaceholder key={anim.id} {...anim} />
      ))}
    </div>
  );
}

export function DocsSubsectionContent({
  subsection,
}: {
  subsection: {
    page?: number;
    eli5?: string;
    theoreticalFoundation?: string;
    markdown?: string;
    examples?: DocExample[];
    failureMode?: DocFailureMode;
    beforeAfter?: { before: { title: string; content: string }; after: { title: string; content: string } };
    stepsTable?: { title?: string; headers: { step: string; what: string; who: string }; rows: { step: string; what: string; who: string }[] };
    animation?: DocAnimation;
    animations?: DocAnimation[];
    sandbox?: { title?: string; placeholder: string; button?: string; initial?: string; scenarios: Record<string, string> };
  };
}) {
  return (
    <article className="space-y-4">
      {subsection.page != null && (
        <p className="font-mono text-[10px] text-muted/60">
          Page {subsection.page}
        </p>
      )}

      {subsection.eli5 && (
        <div className="rounded-xl border border-purple-400/20 bg-purple-500/5 p-4">
          <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-purple-300">
            ELI5 — Explain Like I&apos;m Five
          </p>
          <p className="text-sm leading-relaxed text-foreground/90">
            {subsection.eli5}
          </p>
        </div>
      )}

      {subsection.theoreticalFoundation && (
        <div className="rounded-xl border border-indigo-400/20 bg-indigo-500/5 p-4">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-indigo-300">
            Theoretical Foundation — Why This Exists
          </p>
          <DocsMarkdown content={subsection.theoreticalFoundation} />
        </div>
      )}

      {subsection.beforeAfter && <BeforeAfter {...subsection.beforeAfter} />}

      {subsection.markdown && (
        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted">
            Practical Deep-Dive
          </p>
          <DocsMarkdown content={subsection.markdown} />
        </div>
      )}

      {subsection.examples && subsection.examples.length > 0 && (
        <ExamplesBlock examples={subsection.examples} />
      )}

      {subsection.stepsTable && (
        <StepsTable
          title={subsection.stepsTable.title}
          headers={subsection.stepsTable.headers}
          rows={subsection.stepsTable.rows}
        />
      )}

      {subsection.failureMode && (
        <FailureModeBlock failureMode={subsection.failureMode} />
      )}

      {subsection.animation && <AnimationPlaceholder {...subsection.animation} />}

      {subsection.animations && subsection.animations.length > 0 && (
        <AnimationsBlock animations={subsection.animations} />
      )}

      {subsection.sandbox && <TerminalSandbox {...subsection.sandbox} />}
    </article>
  );
}
