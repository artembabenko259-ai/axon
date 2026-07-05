"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Terminal } from "lucide-react";
import { AgentOrb } from "@/components/ui/AgentOrb";
import { BridgeStatus } from "@/components/ui/BridgeStatus";
import { ConfigWidget } from "@/components/config/ConfigWidget";
import { Sparkline } from "@/components/ui/Sparkline";
import { formatBridgeStats, useChat } from "@/context/ChatContext";
import { useModel } from "@/context/ModelContext";
import { EASE_OUT } from "@/lib/motion";
import { normalizeSparkline } from "@/lib/metrics";

const pillars = [
  {
    n: "01",
    label: "Monitor",
    title: "Live telemetry",
    desc: "Uptime, tokens, and cost streamed from your running CLI agent.",
    href: "/dashboard",
  },
  {
    n: "02",
    label: "Orchestrate",
    title: "Model marketplace",
    desc: "OpenRouter pricing, enable models, hot-swap without restart.",
    href: "/marketplace",
  },
  {
    n: "03",
    label: "Configure",
    title: "Provider setup",
    desc: "OpenRouter, Ollama, custom endpoints — synced with the bridge.",
    href: "/config",
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.45, ease: EASE_OUT },
  }),
};

export function LandingHero() {
  const chatCtx = useChat();
  const modelCtx = useModel();

  const connected = chatCtx?.connected ?? false;
  const isStreaming = chatCtx?.isStreaming ?? false;
  const stats = chatCtx?.stats ?? { tokens: 0, cost: 0 };
  const activeModel = chatCtx?.activeModel ?? "";
  const activeModelId = modelCtx?.activeModelId ?? "";
  const uptimeLabel = chatCtx?.uptimeLabel ?? "00:00:00";
  const tokenSeries = chatCtx?.tokenSeries ?? [];
  const uptimeSeries = chatCtx?.uptimeSeries ?? [];

  const { tokensLabel, costLabel } = formatBridgeStats(stats);

  const modelName = (activeModel || activeModelId || "").split("/").pop() ?? "—";
  const orbStatus = !connected ? "idle" : isStreaming ? "streaming" : "ready";

  return (
    <div className="lunar-bg axon-canvas relative min-h-screen text-[#E6F0FF]">
      <header className="glass relative z-10 sticky top-0 flex h-16 items-center justify-between px-6 lg:px-12">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-white/[0.04]">
            <Image src="/axon-icon.svg" alt="AXON" width={20} height={20} />
          </div>
          <div className="leading-tight">
            <span className="text-sm font-bold tracking-[0.18em]">AXON</span>
            <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.28em] text-white/40">
              Zenith
            </span>
          </div>
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-white/55 md:flex">
          <Link href="/docs" className="transition-colors hover:text-white">
            Docs
          </Link>
          <Link href="/marketplace" className="transition-colors hover:text-white">
            Models
          </Link>
          <Link href="/chat" className="transition-colors hover:text-white">
            Chat
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <ConfigWidget />
          <Link
            href="/dashboard"
            className="btn-lunar-primary ml-1 hidden sm:inline-flex"
          >
            Dashboard
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-6 pb-28 pt-14 lg:px-12 lg:pt-20">
        <div className="grid items-center gap-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10">
          <div>
            <motion.div custom={0} variants={fadeUp} initial="hidden" animate="show">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 font-mono text-[11px] text-white/55">
                <Terminal className="h-3 w-3" />
                lunar panel · v1.0.1
                <BridgeStatus
                  variant="inline"
                  className="ml-1 border-l border-white/10 pl-2"
                />
              </span>
            </motion.div>

            <motion.h1
              custom={1}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="mt-7 text-[2.75rem] font-semibold leading-[1.02] tracking-[-0.04em] sm:text-6xl lg:text-[4rem]"
            >
              <span className="text-gradient-hero">Command your agent</span>
              <br />
              <span className="text-white/90">from the void.</span>
            </motion.h1>

            <motion.p
              custom={2}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="mt-6 max-w-lg text-base leading-relaxed text-white/55"
            >
              Zenith is the local control plane for AXON — monitor sessions,
              switch models, approve tools, and sync chat with your terminal.
            </motion.p>

            <motion.div
              custom={3}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="mt-9 flex flex-wrap items-center gap-3"
            >
              <Link href="/dashboard" className="btn-lunar-primary">
                Open Dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/chat" className="btn-lunar-secondary">
                Open Chat
              </Link>
            </motion.div>

            <motion.div
              custom={4}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="mt-12 flex flex-wrap gap-8 border-t border-white/[0.08] pt-8"
            >
              {[
                { k: "Bridge", v: connected ? "<50ms" : "—" },
                { k: "Models", v: "500+" },
                { k: "Agent", v: connected ? "live" : "waiting" },
              ].map((item) => (
                <div key={item.k}>
                  <p className="font-mono text-xl font-medium tabular-nums text-white">
                    {item.v}
                  </p>
                  <p className="mt-1 text-xs text-white/40">{item.k}</p>
                </div>
              ))}
            </motion.div>
          </div>

          <motion.div
            custom={5}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="relative"
          >
            <div className="landing-preview-ring lunar-card overflow-hidden">
              <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
                <span className="font-mono text-[11px] text-white/45">
                  zenith — live preview
                </span>
                <BridgeStatus variant="inline" />
              </div>

              <div className="flex flex-col items-center border-b border-white/[0.06] py-8">
                <AgentOrb size="md" status={orbStatus} />
              </div>

              <div className="grid gap-px bg-white/[0.04] p-px sm:grid-cols-2">
                {[
                  {
                    l: "Model",
                    v: modelName,
                    spark: false,
                    series: [] as number[],
                    id: "",
                  },
                  {
                    l: "Uptime",
                    v: connected ? uptimeLabel : "—",
                    spark: true,
                    series: normalizeSparkline(uptimeSeries),
                    id: "landing-uptime",
                  },
                  {
                    l: "Tokens",
                    v: connected ? tokensLabel : "—",
                    spark: true,
                    series: normalizeSparkline(tokenSeries),
                    id: "landing-tokens",
                  },
                  {
                    l: "Cost",
                    v: connected ? costLabel : "—",
                    spark: false,
                    series: [] as number[],
                    id: "",
                  },
                ].map((m) => (
                  <div key={m.l} className="bg-[#050813]/60 px-4 py-4">
                    <p className="label-mono">{m.l}</p>
                    <p className="mt-2 truncate font-mono text-sm tabular-nums text-white">
                      {m.v}
                    </p>
                    {m.spark ? (
                      <div className="mt-3 opacity-80">
                        <Sparkline
                          data={m.series}
                          fillId={m.id}
                          stroke="rgba(93, 228, 255, 0.55)"
                        />
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        <div className="relative z-10 mt-24 space-y-3">
          {pillars.map((item, i) => (
            <motion.div
              key={item.label}
              custom={6 + i}
              variants={fadeUp}
              initial="hidden"
              animate="show"
            >
              <Link
                href={item.href}
                className="group lunar-card lunar-card-hover flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-start gap-5">
                  <span className="pillar-num font-mono text-xs text-white/35 transition-colors group-hover:text-[#5DE4FF]">
                    {item.n}
                  </span>
                  <div>
                    <p className="label-mono">{item.label}</p>
                    <h3 className="mt-1 text-base font-medium text-white">
                      {item.title}
                    </h3>
                    <p className="mt-2 max-w-xl text-sm leading-relaxed text-white/50">
                      {item.desc}
                    </p>
                  </div>
                </div>
                <span className="inline-flex shrink-0 items-center gap-1 text-xs text-white/40 transition-colors group-hover:text-[#5DE4FF]">
                  Explore
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </span>
              </Link>
            </motion.div>
          ))}
        </div>
      </main>

      <footer className="relative z-10 border-t border-white/[0.08] py-8 text-center text-xs text-white/40">
        AXON Zenith — local-first AI control plane
      </footer>
    </div>
  );
}
