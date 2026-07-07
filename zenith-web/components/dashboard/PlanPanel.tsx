"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  Circle,
  ClipboardList,
  Loader2,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { useChat, type PlanTaskStatus } from "@/context/ChatContext";

function StatusIcon({ status }: { status: PlanTaskStatus }) {
  switch (status) {
    case "in-progress":
      return <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-yellow-400" />;
    case "done":
      return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />;
    default:
      return <Circle className="h-3.5 w-3.5 shrink-0 text-[#52525b]" />;
  }
}

export function PlanPanel() {
  const { plan, connected } = useChat();

  const doneCount =
    plan?.tasks.filter((task) => task.status === "done").length ?? 0;
  const totalCount = plan?.tasks.length ?? 0;

  return (
    <GlassCard delay={0.16}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-brand" />
          <h2 className="text-sm font-medium text-white">Plan mode</h2>
        </div>
        {plan ? (
          <span className="font-mono text-[10px] uppercase tracking-wide text-white/40">
            {doneCount}/{totalCount} done
          </span>
        ) : (
          <span className="font-mono text-[11px] text-white/40">F2 tasks</span>
        )}
      </div>

      {!connected ? (
        <p className="mt-3 text-xs text-white/45">Waiting for bridge connection…</p>
      ) : !plan ? (
        <p className="mt-3 text-xs text-white/45">
          Run <span className="font-mono text-white/70">/plan</span> or ask naturally
          to build a task board.
        </p>
      ) : (
        <div className="mt-3 space-y-3">
          {plan.goal ? (
            <div>
              <p className="text-[10px] uppercase tracking-wide text-[#71717a]">Goal</p>
              <p className="mt-1 text-xs leading-relaxed text-white">{plan.goal}</p>
            </div>
          ) : null}

          <div className="max-h-52 space-y-1.5 overflow-y-auto logs-scroll pr-1">
            {plan.tasks.map((task) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-2 rounded border border-white/[0.06] bg-black/40 px-2 py-1.5 text-xs"
              >
                <StatusIcon status={task.status} />
                <p className="min-w-0 flex-1 truncate text-white">
                  {task.id}. {task.name}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </GlassCard>
  );
}
