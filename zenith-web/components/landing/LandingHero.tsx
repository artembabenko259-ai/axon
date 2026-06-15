"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, Shield, Sparkles, Zap } from "lucide-react";
import { ThemeSwitcher } from "@/components/ui/ThemeSwitcher";
import { ConfigWidget } from "@/components/config/ConfigWidget";
import { AgentOrb } from "@/components/ui/AgentOrb";
import { GlassCard } from "@/components/ui/GlassCard";

const features = [
  {
    icon: Sparkles,
    title: "Multi-Model",
    desc: "Switch between Claude, GPT, Qwen, and Llama in one panel.",
  },
  {
    icon: Zap,
    title: "Live Streaming",
    desc: "Watch agent responses and tool calls in real time.",
  },
  {
    icon: Shield,
    title: "Local Skills",
    desc: "Function-calling plugins for system info and file access.",
  },
];

export function LandingHero() {
  return (
    <div className="relative flex min-h-screen flex-col">
      {/* Top nav */}
      <motion.nav
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="glass-strong mx-4 mt-4 flex items-center justify-between rounded-2xl px-5 py-3 lg:mx-8 lg:mt-6"
      >
        <div className="flex items-center gap-2.5">
          <Sparkles className="h-4 w-4 text-cyan-400" />
          <span className="font-display text-sm font-semibold tracking-[0.25em] text-white">
            AXON
          </span>
        </div>
        <div className="flex items-center gap-3">
          <ThemeSwitcher />
          <ConfigWidget />
          <Link
            href="/dashboard"
            className="hidden text-xs text-muted transition-colors hover:text-foreground sm:block"
          >
            Dashboard
          </Link>
          <Link href="/dashboard">
            <motion.span
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 rounded-full bg-gradient-to-r from-cyan-500/20 to-purple-500/20 px-4 py-2 text-xs font-medium text-white ring-1 ring-white/10 transition-all hover:ring-cyan-400/30"
            >
              Launch Panel
              <ArrowRight className="h-3.5 w-3.5" />
            </motion.span>
          </Link>
        </div>
      </motion.nav>

      {/* Hero */}
      <main className="flex flex-1 flex-col items-center justify-center px-4 pb-20 pt-12 lg:px-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <AgentOrb size="lg" status="ready" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="mt-10 max-w-2xl text-center"
        >
          <p className="text-[10px] uppercase tracking-[0.4em] text-cyan-400/80">
            AI Command Interface
          </p>
          <h1 className="mt-4 font-display text-4xl font-light tracking-tight sm:text-5xl lg:text-6xl">
            <span className="text-gradient">Intelligence</span>
            <br />
            <span className="text-white/90">at your command.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-md text-sm leading-relaxed text-muted">
            A premium control panel for your terminal AI agent. Monitor status,
            orchestrate models, and configure skills — all from one glass-dark
            interface.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Link href="/dashboard">
            <motion.span
              whileHover={{ scale: 1.03, boxShadow: "0 0 30px rgba(34,211,238,0.2)" }}
              whileTap={{ scale: 0.97 }}
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-cyan-500 to-indigo-500 px-6 py-3 text-sm font-medium text-white shadow-lg shadow-cyan-500/20"
            >
              Open Dashboard
              <ArrowRight className="h-4 w-4" />
            </motion.span>
          </Link>
          <Link href="/config">
            <motion.span
              whileHover={{ scale: 1.02 }}
              className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm text-muted ring-1 ring-white/10 transition-all hover:text-foreground hover:ring-white/20"
            >
              Configure
            </motion.span>
          </Link>
        </motion.div>

        {/* Feature cards */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.6 }}
          className="mt-20 grid w-full max-w-4xl gap-4 sm:grid-cols-3"
        >
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <GlassCard key={feature.title} delay={0.8 + index * 0.1}>
                <Icon className="h-5 w-5 text-cyan-400" />
                <h3 className="mt-3 font-display text-sm font-medium text-white">
                  {feature.title}
                </h3>
                <p className="mt-1.5 text-xs leading-relaxed text-muted">
                  {feature.desc}
                </p>
              </GlassCard>
            );
          })}
        </motion.div>
      </main>

      {/* Footer strip */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="border-t border-white/5 py-4 text-center text-[10px] tracking-wider text-muted"
      >
        AXON v1.0.0 — Terminal AI Control Panel
      </motion.footer>
    </div>
  );
}
