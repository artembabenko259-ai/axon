"use client";

import { Lightbulb } from "lucide-react";
import type { ReactNode } from "react";

interface ProTipProps {
  title?: string;
  children: ReactNode;
}

export function ProTip({ title = "Pro Tip", children }: ProTipProps) {
  return (
    <aside className="my-6 rounded-xl border border-amber-400/25 bg-gradient-to-r from-amber-500/[0.08] to-transparent p-4 pl-4 ring-1 ring-amber-400/10 sm:border-l-4 sm:pl-5">
      <div className="mb-2 flex items-center gap-2">
        <Lightbulb className="h-4 w-4 shrink-0 text-amber-400" />
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-400">
          {title}
        </p>
      </div>
      <div className="text-sm leading-relaxed text-foreground/90">{children}</div>
    </aside>
  );
}
