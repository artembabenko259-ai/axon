"use client";

import { ArrowRight } from "lucide-react";
import type { DocBeforeAfter } from "@/lib/docs-types";

export function BeforeAfter({ before, after }: DocBeforeAfter) {
  return (
    <div className="my-6 grid gap-4 md:grid-cols-[1fr_auto_1fr]">
      <div className="rounded-xl border border-red-400/20 bg-red-500/5 p-4">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-red-400">
          Before — {before.title}
        </p>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">
          {before.content}
        </p>
      </div>
      <div className="hidden items-center justify-center md:flex">
        <ArrowRight className="h-5 w-5 text-cyan-400/60" />
      </div>
      <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/5 p-4">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
          After — {after.title}
        </p>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">
          {after.content}
        </p>
      </div>
    </div>
  );
}
