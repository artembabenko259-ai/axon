"use client";

import { motion } from "framer-motion";
import { Activity, Clock, Coins, Cpu } from "lucide-react";
import { Sparkline } from "@/components/ui/Sparkline";
import { EASE_OUT, TAP_PRESS } from "@/lib/motion";
import { normalizeSparkline } from "@/lib/metrics";
import { cn } from "@/lib/utils";

interface StatusCardProps {
  status: string;
  model: string;
  uptime: string;
  tokensUsed: string;
  sessionCost: string;
  tokenSeries: number[];
  uptimeSeries: number[];
}

export function StatusCards({
  status,
  model,
  uptime,
  tokensUsed,
  sessionCost,
  tokenSeries,
  uptimeSeries,
}: StatusCardProps) {
  const cards = [
    {
      label: "Agent",
      value: status,
      icon: Activity,
      accent: "text-brand",
      dot: "bg-brand",
      sparkline: false as const,
      fillId: "",
      series: [] as number[],
      stroke: "",
    },
    {
      label: "Active model",
      value: model,
      icon: Cpu,
      accent: "text-moonlight",
      dot: "bg-white/50",
      sparkline: false as const,
      fillId: "",
      series: [] as number[],
      stroke: "",
    },
    {
      label: "Uptime",
      value: uptime,
      icon: Clock,
      accent: "text-moonlight",
      dot: "bg-white/35",
      sparkline: true as const,
      fillId: "uptime-spark-fill",
      series: normalizeSparkline(uptimeSeries),
      stroke: "var(--brand)",
    },
    {
      label: "Tokens · Cost",
      value: `${tokensUsed} · ${sessionCost}`,
      icon: Coins,
      accent: "text-moonlight",
      dot: "bg-brand/60",
      sparkline: true as const,
      fillId: "tokens-spark-fill",
      series: normalizeSparkline(tokenSeries),
      stroke: "var(--brand)",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card, index) => {
        const Icon = card.icon;
        return (
          <motion.div
            key={card.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05, duration: 0.45, ease: EASE_OUT }}
            whileHover={{ y: -2, transition: { duration: 0.2, ease: EASE_OUT } }}
            whileTap={TAP_PRESS}
            className={cn(
              "lunar-card lunar-card-hover overflow-hidden p-4",
              card.sparkline && "flex flex-col",
            )}
          >
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1">
                <p className="label-mono">{card.label}</p>
                <p
                  className={cn(
                    "mt-2 truncate font-mono text-lg font-medium tabular-nums tracking-tight",
                    card.accent,
                  )}
                >
                  {card.value}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full shadow-[0_0_6px_currentColor]",
                    card.dot,
                  )}
                />
                <Icon className="h-4 w-4 text-white/40" strokeWidth={1.75} />
              </div>
            </div>
            {card.sparkline ? (
              <div className="mt-3 -mb-1 opacity-90">
                <Sparkline
                  data={card.series}
                  fillId={card.fillId}
                  stroke={card.stroke}
                />
              </div>
            ) : null}
          </motion.div>
        );
      })}
    </div>
  );
}
