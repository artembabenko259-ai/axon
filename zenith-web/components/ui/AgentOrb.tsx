"use client";

import { motion } from "framer-motion";
import { EASE_OUT } from "@/lib/motion";

export type OrbStatus = "ready" | "thinking" | "streaming" | "idle" | "switching";

interface AgentOrbProps {
  size?: "sm" | "md" | "lg";
  status?: OrbStatus;
  label?: string;
  isSwitching?: boolean;
}

const sizeMap = {
  sm: "h-20 w-20",
  md: "h-32 w-32",
  lg: "h-44 w-44",
};

export function AgentOrb({
  size = "md",
  label = "AXON",
  isSwitching = false,
}: AgentOrbProps) {
  return (
    <div className="relative flex flex-col items-center overflow-hidden">
      <motion.div
        className={sizeMap[size]}
        animate={isSwitching ? { rotate: 360 } : { rotate: 0 }}
        transition={isSwitching ? { duration: 0.8, ease: EASE_OUT } : { duration: 0.2 }}
      >
        <div className="relative flex h-full w-full items-center justify-center rounded-full border border-white/10 bg-[#0a0a0a]">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-white">
            <span className="text-sm font-bold text-black">{label.charAt(0)}</span>
          </div>
        </div>
      </motion.div>
      <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.2em] text-[#71717a]">
        {label}
      </p>
    </div>
  );
}
