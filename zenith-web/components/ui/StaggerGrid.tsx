"use client";

import { motion } from "framer-motion";
import { type ReactNode } from "react";
import { entranceContainer, entranceItem } from "@/lib/motion";

interface StaggerGridProps {
  children: ReactNode;
  className?: string;
}

export function StaggerGrid({ children, className }: StaggerGridProps) {
  return (
    <motion.div
      variants={entranceContainer}
      initial="hidden"
      animate="show"
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div layout variants={entranceItem} className={className}>
      {children}
    </motion.div>
  );
}
