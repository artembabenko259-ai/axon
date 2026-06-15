"use client";

import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { EASE_OUT, TAP_PRESS } from "@/lib/motion";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  interactive?: boolean;
  delay?: number;
  layoutId?: string;
}

export function GlassCard({
  children,
  className,
  hover = true,
  interactive = false,
  delay = 0,
  layoutId,
}: GlassCardProps) {
  return (
    <motion.div
      layout
      layoutId={layoutId}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.45,
        delay,
        ease: EASE_OUT,
        layout: { duration: 0.35, ease: EASE_OUT },
      }}
      whileHover={
        hover ? { y: -2, transition: { duration: 0.2, ease: EASE_OUT } } : undefined
      }
      whileTap={interactive ? TAP_PRESS : undefined}
      className={cn("panel p-5", hover && "card-interactive", className)}
    >
      {children}
    </motion.div>
  );
}
