"use client";

import { formatBridgeStats, useChat } from "@/context/ChatContext";
import { cn } from "@/lib/utils";

interface BridgeStatusProps {
  variant?: "pill" | "compact" | "inline";
  className?: string;
}

export function BridgeStatus({
  variant = "pill",
  className,
}: BridgeStatusProps) {
  const { connected, stats, uptimeLabel } = useChat();
  const { tokensLabel, costLabel } = formatBridgeStats(stats);

  if (variant === "inline") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 font-mono text-[10px] text-[#71717a]",
          className,
        )}
      >
        <span
          className={cn(
            "live-dot h-1.5 w-1.5 rounded-full",
            connected ? "live-dot-on" : "bg-zinc-600",
          )}
        />
        {connected ? "live" : "offline"}
      </span>
    );
  }

  if (variant === "compact") {
    return (
      <div
        className={cn(
          "flex items-center gap-2 font-mono text-[10px] text-[#71717a]",
          className,
        )}
      >
        <span
          className={cn(
            "live-dot h-1.5 w-1.5 rounded-full",
            connected ? "live-dot-on" : "bg-zinc-600",
          )}
        />
        <span className={connected ? "text-[#a1a1aa]" : "text-[#52525b]"}>
          {connected ? uptimeLabel : "no agent"}
        </span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-white/[0.06] bg-[#0a0a0a] px-3 py-2",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "live-dot h-1.5 w-1.5 rounded-full",
              connected ? "live-dot-on" : "bg-zinc-600",
            )}
          />
          <span className="text-[11px] font-medium text-[#a1a1aa]">
            {connected ? "Bridge live" : "Bridge offline"}
          </span>
        </div>
        <span className="font-mono text-[10px] text-[#52525b]">:8765</span>
      </div>
      {connected ? (
        <p className="mt-1.5 truncate font-mono text-[10px] tabular-nums text-[#71717a]">
          {uptimeLabel} · {tokensLabel} · {costLabel}
        </p>
      ) : (
        <p className="mt-1.5 text-[10px] text-[#52525b]">
          Start AXON CLI to sync
        </p>
      )}
    </div>
  );
}
