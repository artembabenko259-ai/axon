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
import { useChat } from "@/context/ChatContext";
import { useModel } from "@/context/ModelContext";

export default function DashboardPage() {
  const { activeModelId, isSwitching } = useModel();
  const { messages } = useChat();
  const [status, setStatus] = useState<"ready" | "thinking" | "streaming">(
    "ready",
  );
  const [uptime, setUptime] = useState("00:00:00");

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (!last) return;
    if (last.role === "assistant" && last.source === "terminal") {
      setStatus("ready");
    }
  }, [messages]);

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - start) / 1000);
      const h = String(Math.floor(elapsed / 3600)).padStart(2, "0");
      const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
      const s = String(elapsed % 60).padStart(2, "0");
      setUptime(`${h}:${m}:${s}`);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const shortModel = activeModelId.split("/").pop() ?? activeModelId;

  return (
    <AppShell title="Dashboard">
      <LayoutGroup>
        <motion.div
          layout
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="flex flex-1 flex-col gap-4"
        >
          <StaggerGrid className="flex flex-col gap-4">
            <StaggerItem>
              <StatusCards
                status={status === "ready" ? "Ready" : status}
                model={shortModel}
                uptime={uptime}
                tokensUsed="4.2k"
              />
            </StaggerItem>

            <div className="grid gap-4 lg:grid-cols-5">
              <StaggerItem className="lg:col-span-2">
                <GlassCard
                  layoutId="orb-card"
                  className="flex flex-col items-center justify-center !py-10"
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
                    className="mt-6 max-w-[200px] truncate text-center text-xs text-muted"
                  >
                    Active:{" "}
                    <span className="text-cyan-400">{shortModel}</span>
                  </motion.p>
                  <p className="mt-1 text-center text-[10px] capitalize text-muted">
                    {isSwitching ? "Switching model…" : `Agent is ${status}`}
                  </p>
                </GlassCard>
              </StaggerItem>

              <StaggerItem className="lg:col-span-3">
                <GlassCard layoutId="model-grid" delay={0.15}>
                  <h2 className="font-display text-sm font-medium text-white">
                    Model Selection
                  </h2>
                  <p className="mt-1 text-xs text-muted">
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
