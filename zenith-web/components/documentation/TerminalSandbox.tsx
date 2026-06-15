"use client";

import { useCallback, useState } from "react";
import { Play } from "lucide-react";
import type { DocSandbox } from "@/lib/docs-types";
import { cn } from "@/lib/utils";

export function TerminalSandbox({
  title,
  placeholder,
  button = "Run",
  initial = "$ axon\nAXON v1.0.0 — Ready\n",
  scenarios,
}: DocSandbox) {
  const [input, setInput] = useState("");
  const [output, setOutput] = useState(initial);

  const run = useCallback(() => {
    const cmd = input.trim();
    if (!cmd) return;
    const response =
      scenarios[cmd] ?? scenarios["*"] ?? "AXON: Unknown input. Try the suggested command.";
    setOutput((prev) => `${prev}\n❯ ${cmd}\n${response}\n`);
    setInput("");
  }, [input, scenarios]);

  return (
    <div className="my-6 overflow-hidden rounded-xl border border-white/8 bg-[#0a0a0f] shadow-lg shadow-black/40">
      <div className="flex items-center justify-between border-b border-white/6 bg-[#111] px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
        </div>
        <span className="text-[10px] text-muted">
          {title ?? "Terminal Sandbox"}
        </span>
      </div>
      <div className="min-h-[140px] whitespace-pre-wrap p-4 font-mono text-[11px] leading-relaxed text-muted">
        {output}
      </div>
      <div className="flex items-center gap-2 border-t border-white/6 bg-[#0d0d0d] p-3">
        <span className="text-cyan-400">❯</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent font-mono text-xs text-foreground outline-none placeholder:text-muted/40"
        />
        <button
          type="button"
          onClick={run}
          className={cn(
            "flex items-center gap-1 rounded-lg px-3 py-1.5 text-[10px] font-semibold",
            "bg-cyan-500/15 text-cyan-400 ring-1 ring-cyan-400/25 transition-colors hover:bg-cyan-500/25",
          )}
        >
          <Play className="h-3 w-3" />
          {button}
        </button>
      </div>
    </div>
  );
}
