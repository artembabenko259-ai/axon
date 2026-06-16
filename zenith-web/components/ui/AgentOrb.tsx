"use client";

import { motion } from "framer-motion";

export type OrbStatus =
  | "ready"
  | "thinking"
  | "streaming"
  | "idle"
  | "switching";

interface AgentOrbProps {
  size?: "sm" | "md" | "lg";
  status?: OrbStatus;
  isSwitching?: boolean;
}

const sizePx = { sm: 120, md: 180, lg: 220 } as const;

const STATE = {
  ready: { halo: "moon-ready", label: "READY", accent: "text-[#E6F0FF]" },
  idle: { halo: "moon-ready", label: "IDLE", accent: "text-[#E6F0FF]/70" },
  thinking: { halo: "moon-thinking", label: "THINKING", accent: "text-[#F4C77B]" },
  switching: { halo: "moon-thinking", label: "SWITCHING", accent: "text-[#F4C77B]" },
  streaming: { halo: "moon-streaming", label: "STREAMING", accent: "text-[#5DE4FF]" },
} as const;

export function AgentOrb({
  size = "md",
  status = "ready",
  isSwitching = false,
}: AgentOrbProps) {
  const resolved = isSwitching ? "switching" : status;
  const px = sizePx[size];
  const s = STATE[resolved] ?? STATE.ready;
  const isThinking = resolved === "thinking" || resolved === "switching";

  return (
    <div
      className="relative flex flex-col items-center justify-center"
      data-testid="agent-orb"
      data-state={resolved}
    >
      <div
        className="orbit-slow absolute rounded-full border border-dashed"
        style={{
          width: px + 48,
          height: px + 48,
          borderColor: "rgba(180,200,240,0.14)",
        }}
      />
      <div
        className="orbit-slow absolute"
        style={{ width: px + 48, height: px + 48 }}
      >
        <div className="absolute -top-1 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-[#5DE4FF] glow-cyan" />
      </div>

      <motion.div
        layout
        className={`relative rounded-full ${s.halo}`}
        style={{
          width: px,
          height: px,
          background:
            "radial-gradient(circle at 32% 32%, #f4f8ff 0%, #d8e3f5 28%, #9bafcc 58%, #4a5e80 86%, #283449 100%)",
        }}
      >
        {isThinking ? (
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background:
                "radial-gradient(circle at 78% 50%, transparent 0%, transparent 45%, rgba(5,8,19,0.96) 47%)",
            }}
          />
        ) : null}
        <div className="absolute inset-0 overflow-hidden rounded-full">
          <div
            className="absolute rounded-full bg-black/15"
            style={{ width: 18, height: 18, top: "26%", left: "22%" }}
          />
          <div
            className="absolute rounded-full bg-black/10"
            style={{ width: 12, height: 12, top: "58%", left: "38%" }}
          />
          <div
            className="absolute rounded-full bg-black/15"
            style={{ width: 24, height: 24, top: "48%", left: "60%" }}
          />
          <div
            className="absolute rounded-full bg-black/10"
            style={{ width: 8, height: 8, top: "20%", left: "62%" }}
          />
          <div
            className="absolute rounded-full bg-black/10"
            style={{ width: 14, height: 14, top: "70%", left: "20%" }}
          />
        </div>
        <div
          className="absolute inset-0 rounded-full"
          style={{ boxShadow: "inset 2px 2px 0 rgba(255,255,255,0.18)" }}
        />
      </motion.div>

      <div className={`label-mono mt-5 ${s.accent}`}>{s.label}</div>
    </div>
  );
}
