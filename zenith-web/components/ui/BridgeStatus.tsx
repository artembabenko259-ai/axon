"use client";

import { formatBridgeStats, useChat } from "@/context/ChatContext";
import { cn } from "@/lib/utils";

interface BridgeStatusProps {
  variant?: "pill" | "compact" | "inline";
  className?: string;
}

function statusDot(connected: boolean, reconnecting?: boolean) {
  if (connected) return "live-dot-on bg-[var(--brand)]";
  if (reconnecting) return "bg-amber-500";
  return "bg-rose-500";
}

export function BridgeStatus({
  variant = "pill",
  className,
}: BridgeStatusProps) {
  const { connected, stats, uptimeLabel } = useChat();
  const { tokensLabel, costLabel } = formatBridgeStats(stats);
  const reconnecting = !connected;

  if (variant === "inline") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 font-mono text-[10px] text-white/45",
          className,
        )}
      >
        <span
          className={cn(
            "live-dot h-1.5 w-1.5 rounded-full",
            statusDot(connected, reconnecting),
          )}
        />
        {connected ? "live" : reconnecting ? "reconnecting" : "offline"}
      </span>
    );
  }

  if (variant === "compact") {
    return (
      <div
        className={cn(
          "flex items-center gap-2 font-mono text-[10px] text-white/45",
          className,
        )}
      >
        <span
          className={cn(
            "live-dot h-1.5 w-1.5 rounded-full",
            statusDot(connected, reconnecting),
          )}
        />
        <span className={connected ? "text-white/70" : "text-white/35"}>
          {connected ? uptimeLabel : "no agent"}
        </span>
      </div>
    );
  }

  return (
    <div className={cn("lunar-card p-4", className)}>
      <div className="label-mono mb-2">Bridge</div>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "h-2 w-2 rounded-full",
            statusDot(connected, reconnecting),
            connected && "glow-cyan",
          )}
        />
        <span className="font-mono text-xs text-white/80">
          {connected
            ? "Bridge connected"
            : reconnecting
              ? "Reconnecting…"
              : "Bridge offline"}
        </span>
      </div>
      <div className="mt-2 truncate font-mono text-[10px] text-white/40">
        ws://127.0.0.1:8765
      </div>
      {connected ? (
        <p className="mt-2 truncate font-mono text-[10px] tabular-nums text-white/45">
          {uptimeLabel} · {tokensLabel} · {costLabel}
        </p>
      ) : (
        <p className="mt-2 text-[10px] text-white/35">
          Run <span className="font-mono text-white/55">axon tui</span> to sync
        </p>
      )}
    </div>
  );
}
