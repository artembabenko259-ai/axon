"use client";

import { motion } from "framer-motion";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

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

export function AgentOrb({
  size = "md",
  status = "ready",
  isSwitching = false,
}: AgentOrbProps) {
  const { theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const resolved = isSwitching ? "switching" : status;
  const px = sizePx[size];
  const isThinking = resolved === "thinking" || resolved === "switching";
  const activeTheme = mounted ? theme : "base";

  const getThemeState = () => {
    switch (activeTheme) {
      case "shard":
        return {
          label: isThinking ? "SHARD THINKING" : resolved === "streaming" ? "SHARD STREAMING" : "SHARD ACTIVE",
          accent: "text-[var(--brand)] font-bold tracking-[0.2em]",
          halo: "moon-ready",
        };
      case "dart":
        return {
          label: isThinking ? "DECOMPILING" : resolved === "streaming" ? "ANALYST STREAM" : "DECOMPILER READY",
          accent: "text-[var(--brand)] font-bold tracking-[0.22em] animate-pulse",
          halo: "moon-ready",
        };
      case "base":
      default:
        switch (resolved) {
          case "thinking":
            return { label: "THINKING", accent: "text-amber-400", halo: "moon-thinking" };
          case "switching":
            return { label: "SWITCHING", accent: "text-amber-400", halo: "moon-thinking" };
          case "streaming":
            return { label: "STREAMING", accent: "text-[var(--brand)]", halo: "moon-streaming" };
          case "idle":
            return { label: "IDLE", accent: "text-slate-500", halo: "moon-ready" };
          case "ready":
          default:
            return { label: "READY", accent: "text-white", halo: "moon-ready" };
        }
    }
  };

  const ts = getThemeState();

  const renderCore = () => {
    if (activeTheme === "shard") {
      return (
        <motion.div
          className="relative flex items-center justify-center"
          style={{ width: px, height: px }}
        >
          <motion.svg
            width={px - 20}
            height={px - 20}
            viewBox="0 0 100 100"
            animate={{
              y: [0, -6, 0],
              filter: isThinking
                ? [
                    "drop-shadow(0 0 15px rgba(245,158,11,0.5))",
                    "drop-shadow(0 0 30px rgba(245,158,11,0.95))",
                    "drop-shadow(0 0 15px rgba(245,158,11,0.5))",
                  ]
                : "drop-shadow(0 0 20px rgba(245,158,11,0.6))",
            }}
            transition={{
              y: { duration: 3.5, repeat: Infinity, ease: "easeInOut" },
              filter: { duration: 1.8, repeat: Infinity, ease: "easeInOut" },
            }}
          >
            <polygon points="50,5 75,35 50,50" fill="#fcd34d" opacity="0.95" />
            <polygon points="50,5 25,35 50,50" fill="#f59e0b" opacity="0.85" />
            <polygon points="75,35 50,95 50,50" fill="#d97706" opacity="0.9" />
            <polygon points="25,35 50,95 50,50" fill="#78350f" opacity="0.8" />
            <line x1="50" y1="5" x2="50" y2="95" stroke="#ffffff" strokeWidth="0.5" opacity="0.25" />
            <line x1="25" y1="35" x2="75" y2="35" stroke="#ffffff" strokeWidth="0.5" opacity="0.2" />
          </motion.svg>
        </motion.div>
      );
    }

    if (activeTheme === "dart") {
      return (
        <motion.div
          className="relative flex items-center justify-center"
          style={{ width: px, height: px }}
        >
          <motion.svg
            width={px - 20}
            height={px - 20}
            viewBox="0 0 100 100"
            animate={{
              scale: isThinking ? [1, 1.05, 1] : [1, 1.02, 1],
              rotate: isThinking ? [0, 5, -5, 0] : [0, 1, -1, 0],
            }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="drop-shadow-[0_0_25px_rgba(244,63,94,0.7)]"
          >
            <circle cx="50" cy="50" r="45" stroke="#9f1239" strokeWidth="1" strokeDasharray="3 3" fill="none" />
            <circle cx="50" cy="50" r="35" stroke="#f43f5e" strokeWidth="0.75" opacity="0.25" fill="none" />
            
            <polygon points="50,15 78,68 50,55" fill="#f43f5e" />
            <polygon points="50,15 22,68 50,55" fill="#be123c" />
            <polygon points="50,55 78,68 50,78" fill="#9f1239" />
            <polygon points="50,55 22,68 50,78" fill="#881337" />
            
            <circle cx="50" cy="55" r="4.5" fill="#ffffff" className="animate-pulse" />
          </motion.svg>
        </motion.div>
      );
    }

    return (
      <motion.div
        layout
        className={`relative rounded-full ${ts.halo}`}
        style={{
          width: px,
          height: px,
          background: "var(--orb-gradient)",
        }}
      >
        {isThinking ? (
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background:
                "radial-gradient(circle at 78% 50%, transparent 0%, transparent 45%, rgba(6,8,14,0.96) 47%)",
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
    );
  };

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
          borderColor: "var(--border)",
        }}
      />
      <div
        className="orbit-slow absolute"
        style={{ width: px + 48, height: px + 48 }}
      >
        <div 
          className={cn(
            "absolute -top-1 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-[var(--brand)]",
            activeTheme === "base" && "glow-cyan"
          )} 
        />
      </div>

      {renderCore()}

      <div className={`label-mono mt-5 ${ts.accent}`}>{ts.label}</div>
    </div>
  );
}
