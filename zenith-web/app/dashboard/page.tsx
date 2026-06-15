"use client";

import { motion, LayoutGroup } from "framer-motion";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { LogsConsole } from "@/components/dashboard/LogsConsole";
import { ModelSelector } from "@/components/dashboard/ModelSelector";
import { StatusCards } from "@/components/dashboard/StatusCards";
import { ModelMarketplace } from "@/components/marketplace/ModelMarketplace";
import { AgentOrb } from "@/components/ui/AgentOrb";
import { GlassCard } from "@/components/ui/GlassCard";
import { StaggerGrid, StaggerItem } from "@/components/ui/StaggerGrid";
import { useChat, formatBridgeStats } from "@/context/ChatContext";
import { useModel } from "@/context/ModelContext";

export default function DashboardPage() {
  const { activeModelId, isSwitching } = useModel();
  const { messages, connected, stats, uptimeLabel, tokenSeries, uptimeSeries } =
    useChat();
  const { tokensLabel, costLabel } = formatBridgeStats(stats);
  const [status, setStatus] = useState<"ready" | "thinking" | "streaming">(
    "ready",
  );

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (!last) return;
    if (last.role === "assistant" && last.source === "terminal") {
      setStatus("ready");
    }
  }, [messages]);

  const shortModel = activeModelId.split("/").pop() ?? activeModelId;

  return (
    <AppShell title="Dashboard">
      <LayoutGroup>
        <motion.div
          layout
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="flex flex-1 flex-col gap-6"
        >
          <StaggerGrid className="flex flex-col gap-6">
            <StaggerItem>
              <div className="mb-2">
                <p className="label-caps">Overview</p>
                <h2 className="text-lg font-semibold tracking-tight text-white">Dashboard</h2>
                <p className="mt-1 text-sm text-[#a1a1aa]">
                  Real-time agent metrics and model orchestration
                </p>
              </div>
              <StatusCards
                status={
                  connected
                    ? status === "ready"
                      ? "Ready"
                      : status
                    : "Reconnecting…"
                }
                model={shortModel}
                uptime={uptimeLabel}
                tokensUsed={tokensLabel}
                sessionCost={costLabel}
                tokenSeries={tokenSeries}
                uptimeSeries={uptimeSeries}
              />
            </StaggerItem>

            <div className="grid gap-4 lg:grid-cols-5">
              <StaggerItem className="lg:col-span-2">
                <GlassCard
                  layoutId="orb-card"
                  className="flex flex-col items-center justify-center !py-12"
                  delay={0.1}
                >
                  <AgentOrb
                    size="md"
                    status={status}
                    isSwitching={isSwitching}
                  />
                  <motion.p
                    key={activeModelId}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 max-w-[200px] truncate text-center text-xs text-[#71717a]"
                  >
                    Active:{" "}
                    <span className="text-white">{shortModel}</span>
                  </motion.p>
                  <p className="mt-1 text-center text-[10px] capitalize text-[#71717a]">
                    {isSwitching ? "Switching model…" : `Agent is ${status}`}
                  </p>
                </GlassCard>
              </StaggerItem>

              <StaggerItem className="lg:col-span-3">
                <GlassCard layoutId="model-grid" delay={0.15}>
                  <p className="label-caps">Inference</p>
                  <h2 className="mt-1 text-sm font-semibold tracking-tight text-white">
                    Model Selection
                  </h2>
                  <p className="mt-1 text-xs text-[#a1a1aa]">
                    Default and custom models — click to activate
                  </p>
                  <div className="mt-4 max-h-64 overflow-y-auto logs-scroll pr-1">
                    <ModelSelector />
                  </div>
                </GlassCard>
              </StaggerItem>
            </div>

            <StaggerItem>
              <motion.div layout>
                <ModelMarketplace />
              </motion.div>
            </StaggerItem>

            <StaggerItem>
              <LogsConsole />
            </StaggerItem>
          </StaggerGrid>
        </motion.div>
      </LayoutGroup>
    </AppShell>
  );
}
