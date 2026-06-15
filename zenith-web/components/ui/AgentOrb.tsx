"use client";

import { motion } from "framer-motion";

export type OrbStatus = "ready" | "thinking" | "streaming" | "idle" | "switching";

interface AgentOrbProps {
  size?: "sm" | "md" | "lg";
  status?: OrbStatus;
  label?: string;
  isSwitching?: boolean;
}

const sizeMap = {
  sm: "h-24 w-24",
  md: "h-40 w-40",
  lg: "h-56 w-56",
};

const orbitRadius = { sm: 48, md: 80, lg: 112 };

const statusColors: Record<OrbStatus, string> = {
  ready: "from-cyan-400/80 via-indigo-500/60 to-purple-500/80",
  idle: "from-slate-500/50 via-indigo-500/40 to-purple-500/50",
  thinking: "from-amber-400/70 via-indigo-500/70 to-purple-500/80",
  streaming: "from-cyan-300/90 via-blue-500/70 to-purple-400/90",
  switching: "from-purple-400/90 via-cyan-500/70 to-indigo-500/90",
};

const pulseConfig: Record<
  OrbStatus,
  { duration: number; scale: [number, number, number] }
> = {
  idle: { duration: 5, scale: [1, 1.03, 1] },
  ready: { duration: 4.5, scale: [1, 1.04, 1] },
  thinking: { duration: 1.2, scale: [1, 1.08, 1] },
  streaming: { duration: 0.8, scale: [1, 1.1, 1] },
  switching: { duration: 0.6, scale: [1, 1.06, 1] },
};

export function AgentOrb({
  size = "md",
  status = "ready",
  label = "AXON",
  isSwitching = false,
}: AgentOrbProps) {
  const effectiveStatus: OrbStatus = isSwitching ? "switching" : status;
  const pulse = pulseConfig[effectiveStatus];
  const radius = orbitRadius[size];

  return (
    <div className="relative flex flex-col items-center gap-4">
      <motion.div
        className={sizeMap[size]}
        animate={
          isSwitching
            ? { rotate: [0, 180, 360] }
            : { rotate: 0 }
        }
        transition={
          isSwitching
            ? { duration: 0.8, ease: [0.22, 1, 0.36, 1] }
            : { duration: 0.3 }
        }
      >
        <motion.div
          className="absolute inset-0 rounded-full"
          animate={{
            scale: pulse.scale,
            opacity:
              effectiveStatus === "streaming" || effectiveStatus === "thinking"
                ? [0.5, 0.9, 0.5]
                : [0.35, 0.65, 0.35],
          }}
          transition={{
            duration: pulse.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          style={{
            background:
              "radial-gradient(circle, rgba(34,211,238,0.18) 0%, transparent 70%)",
          }}
        />

        <motion.div
          className="absolute inset-2 rounded-full border border-white/10"
          animate={{
            scale: pulse.scale,
            borderColor:
              effectiveStatus === "streaming"
                ? [
                    "rgba(34,211,238,0.2)",
                    "rgba(34,211,238,0.5)",
                    "rgba(34,211,238,0.2)",
                  ]
                : [
                    "rgba(255,255,255,0.08)",
                    "rgba(34,211,238,0.25)",
                    "rgba(255,255,255,0.08)",
                  ],
          }}
          transition={{
            duration: pulse.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />

        <motion.div
          className={`relative h-full w-full rounded-full bg-gradient-to-br ${statusColors[effectiveStatus]} neon-ring`}
          animate={{ scale: pulse.scale }}
          transition={{
            duration: pulse.duration,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <div className="absolute inset-0 rounded-full bg-gradient-to-t from-transparent via-white/5 to-white/15" />
          <div className="absolute inset-[30%] rounded-full bg-white/10 blur-md" />
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-display text-xs font-semibold tracking-[0.3em] text-white/90">
              {label}
            </span>
          </div>
        </motion.div>

        <motion.div
          className="absolute h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.8)]"
          animate={{ rotate: 360 }}
          transition={{
            duration:
              effectiveStatus === "streaming"
                ? 3
                : effectiveStatus === "thinking"
                  ? 5
                  : 10,
            repeat: Infinity,
            ease: "linear",
          }}
          style={{
            top: "50%",
            left: "50%",
            marginTop: -4,
            marginLeft: -4,
            transformOrigin: `${radius}px 4px`,
          }}
        />
      </motion.div>
    </div>
  );
}
