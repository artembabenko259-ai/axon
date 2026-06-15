"use client";

import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  delay?: number;
  layoutId?: string;
}

export function GlassCard({
  children,
  className,
  hover = true,
  delay = 0,
  layoutId,
}: GlassCardProps) {
  return (
    <motion.div
      layout
      layoutId={layoutId}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1], layout: { duration: 0.35 } }}
      whileHover={
        hover
          ? {
              y: -2,
              borderColor: "rgba(255,255,255,0.16)",
              transition: { duration: 0.2 },
            }
          : undefined
      }
      className={cn(
        "glass rounded-2xl p-5 transition-all duration-300",
        "hover:backdrop-blur-[28px] hover:bg-white/[0.06]",
        hover && "cursor-default",
        className,
      )}
    >
      {children}
    </motion.div>
  );
}
