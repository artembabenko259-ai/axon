"use client";

import { motion, LayoutGroup } from "framer-motion";
import { AppShell } from "@/components/layout/AppShell";
import { LogsConsole } from "@/components/dashboard/LogsConsole";
import { ModelSelector } from "@/components/dashboard/ModelSelector";
import { StatusCards } from "@/components/dashboard/StatusCards";
import { ToolTracePanel } from "@/components/dashboard/ToolTracePanel";
import { MultitaskPanel } from "@/components/dashboard/MultitaskPanel";
import { ModelMarketplace } from "@/components/marketplace/ModelMarketplace";
import { AgentOrb, type OrbStatus } from "@/components/ui/AgentOrb";
import { GlassCard } from "@/components/ui/GlassCard";
import { StaggerGrid, StaggerItem } from "@/components/ui/StaggerGrid";
import { useChat, formatBridgeStats } from "@/context/ChatContext";
import { useModel } from "@/context/ModelContext";

function deriveOrbStatus(
  connected: boolean,
  isStreaming: boolean,
  isSwitching: boolean,
): OrbStatus {
  if (!connected) return "idle";
  if (isSwitching) return "switching";
  if (isStreaming) return "streaming";
  return "ready";
}

export default function DashboardPage() {
  const { activeModelId, isSwitching } = useModel();
  const {
    connected,
    isStreaming,
    stats,
    uptimeLabel,
    tokenSeries,
    uptimeSeries,
  } = useChat();
  const { tokensLabel, costLabel } = formatBridgeStats(stats);

  const orbStatus = deriveOrbStatus(connected, isStreaming, isSwitching);
  const shortModel = activeModelId.split("/").pop() ?? activeModelId;
  const statusLabel = connected
    ? isStreaming
      ? "Streaming"
      : isSwitching
        ? "Switching"
        : "Ready"
    : "Offline";

  return (
    <AppShell title="Dashboard">
      <LayoutGroup>
        <motion.div
          layout
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="mx-auto flex max-w-[1500px] flex-1 flex-col gap-6"
        >
          <StaggerGrid className="flex flex-col gap-6">
            <StaggerItem>
              <div className="mb-2">
                <p className="label-mono">Overview</p>
                <h2 className="text-lg font-semibold tracking-tight text-white">
                  Mission control
                </h2>
                <p className="mt-1 text-sm text-white/50">
                  Live agent telemetry, models, and orchestration
                </p>
              </div>
              <StatusCards
                status={statusLabel}
                model={shortModel}
                uptime={uptimeLabel}
                tokensUsed={tokensLabel}
                sessionCost={costLabel}
                tokenSeries={tokenSeries}
                uptimeSeries={uptimeSeries}
              />
            </StaggerItem>

            <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
              <StaggerItem>
                <GlassCard
                  layoutId="orb-card"
                  className="flex min-h-[320px] flex-col items-center justify-center !py-10"
                  delay={0.1}
                >
                  <AgentOrb
                    size="lg"
                    status={orbStatus}
                    isSwitching={isSwitching}
                  />
                  <motion.p
                    key={activeModelId}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 max-w-[240px] truncate text-center font-mono text-xs text-white/45"
                  >
                    Active:{" "}
                    <span className="text-[#E6F0FF]">{shortModel}</span>
                  </motion.p>
                </GlassCard>
              </StaggerItem>

              <StaggerItem>
                <GlassCard layoutId="model-grid" delay={0.15}>
                  <div className="flex items-center justify-between">
                    <p className="label-mono">Model selection</p>
                    <span className="font-mono text-[11px] text-white/40">
                      click = switch in CLI
                    </span>
                  </div>
                  <div className="mt-4 max-h-72 overflow-y-auto logs-scroll pr-1">
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

            <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
              <StaggerItem>
                <MultitaskPanel />
              </StaggerItem>
              <StaggerItem>
                <ToolTracePanel />
              </StaggerItem>
            </div>

            <StaggerItem>
              <LogsConsole />
            </StaggerItem>
          </StaggerGrid>
        </motion.div>
      </LayoutGroup>
    </AppShell>
  );
}
