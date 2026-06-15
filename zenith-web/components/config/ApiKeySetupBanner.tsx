"use client";

import { motion } from "framer-motion";
import { ArrowRight, KeyRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useConfig } from "@/context/ConfigContext";

export function ApiKeySetupBanner() {
  const pathname = usePathname();
  const { hasServerApiKey, config } = useConfig();

  if (pathname === "/config" || hasServerApiKey || config.isConnected) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 rounded-xl border border-amber-500/25 bg-amber-500/[0.06] px-4 py-3 sm:px-5"
    >
      <div className="flex flex-wrap items-start gap-3 sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/10">
            <KeyRound className="h-4 w-4 text-amber-200" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-white">Connect OpenRouter</p>
            <p className="mt-0.5 text-xs leading-relaxed text-[#a1a1aa]">
              Paste your API key here — AXON saves it to{" "}
              <code className="text-[#d4d4d8]">%APPDATA%\AXON\config.json</code>{" "}
              on this PC. Get a key at{" "}
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-300 hover:underline"
              >
                openrouter.ai/keys
              </a>
              .
            </p>
          </div>
        </div>
        <Link
          href="/config"
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-medium text-white transition hover:border-white/20 hover:bg-white/[0.08]"
        >
          Add API key
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </motion.div>
  );
}
