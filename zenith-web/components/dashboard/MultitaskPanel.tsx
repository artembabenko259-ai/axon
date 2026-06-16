"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  Circle,
  Loader2,
  Target,
  XCircle,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { useChat, type MultitaskState } from "@/context/ChatContext";

function phaseLabel(phase: string): string {
  switch (phase) {
    case "decompose_start":
      return "Decomposing goal…";
    case "decompose_done":
      return "Running subtasks";
    case "subtask_status":
      return "Subtasks in progress";
    case "synthesis_done":
      return "Complete";
    default:
      return phase.replace(/_/g, " ");
  }
}

function StatusIcon({ status }: { status: MultitaskState["subtasks"][number]["status"] }) {
  switch (status) {
    case "running":
      return <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-yellow-400" />;
    case "done":
      return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />;
    case "failed":
      return <XCircle className="h-3.5 w-3.5 shrink-0 text-red-400" />;
    default:
      return <Circle className="h-3.5 w-3.5 shrink-0 text-[#52525b]" />;
  }
}

export function MultitaskPanel() {
  const { multitask, connected } = useChat();

  const doneCount =
    multitask?.subtasks.filter((task) => task.status === "done").length ?? 0;
  const totalCount = multitask?.subtasks.length ?? 0;

  return (
    <GlassCard delay={0.18}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-[#5DE4FF]" />
          <h2 className="text-sm font-medium text-white">Orchestrator</h2>
        </div>
        {multitask ? (
          <span className="font-mono text-[10px] uppercase tracking-wide text-white/40">
            {phaseLabel(multitask.phase)}
          </span>
        ) : (
          <span className="font-mono text-[11px] text-white/40">multitask</span>
        )}
      </div>

      {!connected ? (
        <p className="mt-3 text-xs text-white/45">Waiting for bridge connection…</p>
      ) : !multitask ? (
        <p className="mt-3 text-xs text-white/45">
          Run <span className="font-mono text-white/70">/multitask</span> in the CLI
          to see live progress here.
        </p>
      ) : (
        <div className="mt-3 space-y-3">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-[#71717a]">Goal</p>
            <p className="mt-1 text-xs leading-relaxed text-white">{multitask.goal}</p>
          </div>

          {totalCount > 0 ? (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-[10px] uppercase tracking-wide text-[#71717a]">
                  Subtasks
                </p>
                <p className="text-[10px] text-[#71717a]">
                  {doneCount}/{totalCount} done
                </p>
              </div>
              <div className="max-h-52 space-y-1.5 overflow-y-auto logs-scroll pr-1">
                {multitask.subtasks.map((task) => (
                  <motion.div
                    key={task.id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex items-start gap-2 rounded border border-white/[0.06] bg-black/40 px-2 py-1.5 text-xs"
                  >
                    <StatusIcon status={task.status} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-white">
                        {task.id}. {task.title}
                      </p>
                      <p className="mt-0.5 font-mono text-[10px] text-[#71717a]">
                        {task.agent}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          ) : null}

          {multitask.phase === "decompose_start" ? (
            <p className="text-xs text-[#a1a1aa]">Planning parallel work…</p>
          ) : null}

          {multitask.synthesis ? (
            <div className="rounded border border-cyan-500/20 bg-cyan-500/5 px-2 py-2">
              <p className="text-[10px] uppercase tracking-wide text-cyan-300/80">
                Synthesis
              </p>
              <p className="mt-1 max-h-32 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-[#d4d4d8] logs-scroll">
                {multitask.synthesis}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </GlassCard>
  );
}
