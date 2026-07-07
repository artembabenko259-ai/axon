"use client";

// Reading this as: landing page and dashboard for developer AI tool, with a minimalist dark-tech titanium and ice-blue language, leaning toward Tailwind v4 utility-first + modern typography + fluid motion.
// DESIGN_VARIANCE: 7
// MOTION_INTENSITY: 6
// VISUAL_DENSITY: 4

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Terminal, Cpu, Database, KeyRound, Check } from "lucide-react";
import { AgentOrb } from "@/components/ui/AgentOrb";
import { BridgeStatus } from "@/components/ui/BridgeStatus";
import { ConfigWidget } from "@/components/config/ConfigWidget";
import { Sparkline } from "@/components/ui/Sparkline";
import { formatBridgeStats, useChat } from "@/context/ChatContext";
import { useModel } from "@/context/ModelContext";
import { EASE_OUT } from "@/lib/motion";
import { normalizeSparkline } from "@/lib/metrics";

const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.04, duration: 0.25, ease: [0.16, 1, 0.3, 1] as const },
  }),
};

export function LandingHero() {
  const chatCtx = useChat();
  const modelCtx = useModel();

  const connected = chatCtx?.connected ?? false;
  const isStreaming = chatCtx?.isStreaming ?? false;
  const stats = chatCtx?.stats ?? { tokens: 0, cost: 0 };
  const uptimeLabel = chatCtx?.uptimeLabel ?? "00:00:00";
  const tokenSeries = chatCtx?.tokenSeries ?? [];
  const uptimeSeries = chatCtx?.uptimeSeries ?? [];
  const activeModel = chatCtx?.activeModel ?? "";
  const activeModelId = modelCtx?.activeModelId ?? "";

  const { tokensLabel, costLabel } = formatBridgeStats(stats);
  const modelName = (activeModel || activeModelId || "").split("/").pop() ?? "—";
  const orbStatus = !connected ? "idle" : isStreaming ? "streaming" : "ready";

  return (
    <div className="lunar-bg axon-canvas relative min-h-screen text-[#cbd5e1] overflow-x-hidden">
      {/* Sticky Header Navigation */}
      <header className="glass relative z-10 sticky top-0 flex h-16 items-center justify-between px-6 lg:px-12">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-white/[0.04]">
            <Image src="/axon-icon.svg" alt="AXON" width={20} height={20} />
          </div>
          <div className="leading-tight">
            <span className="text-sm font-bold tracking-[0.18em] text-white">AXON</span>
            <span className="ml-2 font-mono text-[9px] uppercase tracking-[0.25em] text-white/40">
              Zenith
            </span>
          </div>
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-white/60 md:flex">
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

      {/* Main Container */}
      <main className="relative z-10 mx-auto max-w-6xl px-6 pb-28 pt-10 lg:px-12 lg:pt-16">
        
        {/* Asymmetric Hero section */}
        <div className="grid items-center gap-14 lg:grid-cols-[1.1fr_0.9fr] lg:gap-12">
          
          {/* Left Column: Headline and CTAs */}
          <div>
            <motion.div custom={0} variants={fadeUp} initial="hidden" animate="show">
              <span className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-3 py-0.5 font-mono text-[10.5px] text-white/60">
                <Terminal className="h-3 w-3 text-sky-400" />
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
              className="mt-6 text-[2.5rem] font-semibold leading-[1.05] tracking-[-0.04em] sm:text-5xl lg:text-[3.75rem]"
            >
              <span className="text-gradient-hero">Command your agent</span>
              <br />
              <span className="text-white/95">from the void.</span>
            </motion.h1>

            <motion.p
              custom={2}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="mt-5 max-w-md text-base leading-relaxed text-slate-400"
            >
              Zenith is the local control plane for AXON — monitor sessions,
              switch models, approve tools, and sync chat with your terminal.
            </motion.p>

            <motion.div
              custom={3}
              variants={fadeUp}
              initial="hidden"
              animate="show"
              className="mt-8 flex flex-wrap items-center gap-3.5"
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
              className="mt-12 flex flex-wrap gap-8 border-t border-white/[0.06] pt-8"
            >
              {[
                { k: "Bridge Ping", v: connected ? "<50ms" : "—" },
                { k: "Models Available", v: "500+" },
                { k: "Agent Engine", v: connected ? "live" : "waiting" },
              ].map((item) => (
                <div key={item.k}>
                  <p className="font-mono text-xl font-medium tabular-nums text-white">
                    {item.v}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{item.k}</p>
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right Column: Interactive Telemetry Preview */}
          <motion.div
            custom={5}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="relative"
          >
            <div className="landing-preview-ring lunar-card overflow-hidden">
              <div className="flex items-center justify-between border-b border-white/[0.05] px-5 py-3.5">
                <span className="font-mono text-[10.5px] text-white/40">
                  zenith — telemetry cockpit
                </span>
                <BridgeStatus variant="inline" />
              </div>

              <div className="flex flex-col items-center border-b border-white/[0.05] py-8 bg-black/40">
                <AgentOrb size="md" status={orbStatus} />
              </div>

              <div className="grid gap-px bg-white/[0.05] p-px sm:grid-cols-2">
                {[
                  {
                    l: "Active Model",
                    v: modelName,
                    spark: false,
                    series: [] as number[],
                    id: "",
                  },
                  {
                    l: "CLI Uptime",
                    v: connected ? uptimeLabel : "—",
                    spark: true,
                    series: normalizeSparkline(uptimeSeries),
                    id: "landing-uptime",
                  },
                  {
                    l: "Tokens Streamed",
                    v: connected ? tokensLabel : "—",
                    spark: true,
                    series: normalizeSparkline(tokenSeries),
                    id: "landing-tokens",
                  },
                  {
                    l: "Session Cost",
                    v: connected ? costLabel : "—",
                    spark: false,
                    series: [] as number[],
                    id: "",
                  },
                ].map((m) => (
                  <div key={m.l} className="bg-[#050508]/80 px-5 py-4">
                    <p className="label-mono">{m.l}</p>
                    <p className="mt-2 truncate font-mono text-sm tabular-nums text-white">
                      {m.v}
                    </p>
                    {m.spark ? (
                      <div className="mt-3 opacity-90">
                        <Sparkline
                          data={m.series}
                          fillId={m.id}
                          stroke="var(--brand)"
                        />
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>

        {/* 3-Column Bento Grid representing real visual previews of each pillar */}
        <div className="relative z-10 mt-24 grid md:grid-cols-3 gap-6">
          
          {/* Card 1: Monitor */}
          <motion.div
            custom={6}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="lunar-card lunar-card-hover p-6 flex flex-col justify-between min-h-[300px]"
          >
            <div>
              <span className="flex h-7 w-7 items-center justify-center rounded bg-sky-500/5 border border-sky-500/10">
                <Cpu className="h-4 w-4 text-sky-400" />
              </span>
              <p className="label-mono mt-4">01 · Telemetry</p>
              <h3 className="mt-1 text-base font-semibold text-white">Live Monitoring</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                Uptime, tokens, and resource consumption streamed from your local CLI.
              </p>
            </div>
            
            {/* Visual Telemetry Grid */}
            <div className="mt-6 border border-white/5 rounded bg-black/45 p-3 flex flex-col gap-2 font-mono text-[11px]">
              <div className="flex justify-between border-b border-white/5 pb-1 text-slate-500">
                <span>Metric</span>
                <span>Active Status</span>
              </div>
              <div className="flex justify-between text-emerald-400">
                <span>CLI Bridge</span>
                <span>ONLINE (&lt;4ms)</span>
              </div>
              <div className="flex justify-between text-white/70">
                <span>CPU Usage</span>
                <span>12.4%</span>
              </div>
              <div className="flex justify-between text-white/70">
                <span>Memory</span>
                <span>154.2 MB</span>
              </div>
            </div>
          </motion.div>

          {/* Card 2: Orchestrate */}
          <motion.div
            custom={7}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="lunar-card lunar-card-hover p-6 flex flex-col justify-between min-h-[300px]"
          >
            <div>
              <span className="flex h-7 w-7 items-center justify-center rounded bg-purple-500/5 border border-purple-500/10">
                <Database className="h-4 w-4 text-purple-400" />
              </span>
              <p className="label-mono mt-4">02 · Orchestrate</p>
              <h3 className="mt-1 text-base font-semibold text-white">Model Marketplace</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                OpenRouter pricing models, enable custom providers, and hot-swap dynamically.
              </p>
            </div>
            
            {/* Visual Switcher preview */}
            <div className="mt-6 border border-white/5 rounded bg-black/45 p-3 flex flex-col gap-2 font-mono text-[11px]">
              <div className="flex justify-between border-b border-white/5 pb-1 text-slate-500">
                <span>Provider Models</span>
                <span>Selected</span>
              </div>
              <div className="flex justify-between items-center text-white">
                <span>claude-3-5-sonnet</span>
                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
                  <Check className="h-3.5 w-3.5" />
                </span>
              </div>
              <div className="flex justify-between items-center text-white/50">
                <span>gpt-4o-mini</span>
                <span className="text-[9.5px] border border-white/5 bg-white/5 px-1.5 py-0.5 rounded text-white/40">enabled</span>
              </div>
              <div className="flex justify-between items-center text-white/50">
                <span>gemini-1.5-pro</span>
                <span className="text-[9.5px] border border-white/5 bg-white/5 px-1.5 py-0.5 rounded text-white/40">enabled</span>
              </div>
            </div>
          </motion.div>

          {/* Card 3: Configure */}
          <motion.div
            custom={8}
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="lunar-card lunar-card-hover p-6 flex flex-col justify-between min-h-[300px]"
          >
            <div>
              <span className="flex h-7 w-7 items-center justify-center rounded bg-amber-500/5 border border-amber-500/10">
                <KeyRound className="h-4 w-4 text-amber-400" />
              </span>
              <p className="label-mono mt-4">03 · Configure</p>
              <h3 className="mt-1 text-base font-semibold text-white">Provider Setup</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                Ollama, OpenRouter, and custom endpoints — securely synced with the CLI bridge.
              </p>
            </div>
            
            {/* Visual Setup Preview */}
            <div className="mt-6 border border-white/5 rounded bg-black/45 p-3 flex flex-col gap-2 font-mono text-[10.5px]">
              <div className="flex flex-col gap-1">
                <span className="text-slate-500">API Provider:</span>
                <span className="text-white border border-white/5 bg-white/5 px-2 py-1 rounded">OpenRouter API</span>
              </div>
              <div className="flex flex-col gap-1 mt-1">
                <span className="text-slate-500">Bearer Token:</span>
                <span className="text-white border border-white/5 bg-white/5 px-2 py-1 rounded">sk-or-•••••••••••••</span>
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      <footer className="relative z-10 border-t border-white/[0.05] py-8 text-center text-xs text-slate-500 bg-black/40">
        AXON Zenith — local-first AI control plane
      </footer>
    </div>
  );
}
