"use client";

import { motion } from "framer-motion";
import { Activity, Cpu, Zap } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";

interface StatusCardProps {
  status: string;
  model: string;
  uptime: string;
  tokensUsed: string;
  sessionCost: string;
}

export function StatusCards({
  status,
  model,
  uptime,
  tokensUsed,
  sessionCost,
}: StatusCardProps) {
  const cards = [
    {
      label: "Agent Status",
      value: status,
      icon: Activity,
      accent: "text-success",
      dot: "bg-success",
    },
    {
      label: "Active Model",
      value: model,
      icon: Cpu,
      accent: "text-cyan-400",
      dot: "bg-cyan-400",
    },
    {
      label: "Session Uptime",
      value: uptime,
      icon: Zap,
      accent: "text-purple-400",
      dot: "bg-purple-400",
    },
    {
      label: "Tokens / Cost",
      value: `${tokensUsed} · ${sessionCost}`,
      icon: Zap,
      accent: "text-foreground",
      dot: "bg-white/40",
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card, index) => {
        const Icon = card.icon;
        return (
          <GlassCard key={card.label} delay={index * 0.05} className="!p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted">
                  {card.label}
                </p>
                <motion.p
                  key={card.value}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`mt-1 font-display text-lg font-medium ${card.accent}`}
                >
                  {card.value}
                </motion.p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${card.dot} shadow-[0_0_6px_currentColor]`}
                />
                <Icon className="h-4 w-4 text-muted" />
              </div>
            </div>
          </GlassCard>
        );
      })}
    </div>
  );
}
