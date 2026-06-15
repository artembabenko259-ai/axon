"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import type { DocAnimation } from "@/lib/docs-types";

export function AnimationPlaceholder({ id, title, description, trigger }: DocAnimation) {
  return (
    <motion.div
      id={`anim-${id}`}
      initial={{ opacity: 0, scale: 0.98 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5 }}
      className="my-6 overflow-hidden rounded-xl border border-dashed border-cyan-400/30 bg-gradient-to-br from-cyan-500/5 to-purple-500/5 p-5"
      data-animation-trigger={trigger}
    >
      <div className="mb-3 flex items-center gap-2">
        <motion.div
          animate={{ rotate: [0, 8, -8, 0] }}
          transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
        >
          <Sparkles className="h-4 w-4 text-cyan-400" />
        </motion.div>
        <span className="text-xs font-semibold text-cyan-400">{title}</span>
        <span className="ml-auto rounded bg-white/5 px-2 py-0.5 font-mono text-[9px] text-muted">
          trigger: {trigger}
        </span>
      </div>
      <p className="text-sm leading-relaxed text-muted">{description}</p>
      <div className="mt-4 flex h-16 items-center justify-center gap-2 rounded-lg bg-black/30">
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="h-2 w-2 rounded-full bg-cyan-400/70"
            animate={{ opacity: [0.3, 1, 0.3], y: [0, -6, 0] }}
            transition={{
              repeat: Infinity,
              duration: 1.2,
              delay: i * 0.2,
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}
