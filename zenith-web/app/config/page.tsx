"use client";

import { motion } from "framer-motion";
import { Eye, EyeOff, FolderOpen, Key, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { CustomModelRegistry } from "@/components/config/CustomModelRegistry";
import { AppShell } from "@/components/layout/AppShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { useConfig } from "@/context/ConfigContext";

export default function ConfigPage() {
  const { config, draft, setDraftApiKey, saveAndConnect, isSaving } = useConfig();
  const [showKey, setShowKey] = useState(false);
  const [cliPath, setCliPath] = useState("C:\\Users\\User\\Desktop\\CLI");
  const [historyPath, setHistoryPath] = useState("~/.cli_history");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSaved(config.isConnected);
  }, [config.isConnected]);

  const handleSave = async () => {
    await saveAndConnect();
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <AppShell title="Configuration">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mx-auto flex w-full max-w-2xl flex-col gap-4"
      >
        <GlassCard delay={0}>
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-cyan-400" />
            <h2 className="font-display text-sm font-medium text-white">
              API Keys
            </h2>
          </div>
          <p className="mt-1 text-xs text-muted">
            Provider settings sync with the Global Config widget. Current:{" "}
            <span className="text-cyan-400">{config.provider}</span>
          </p>

          <label className="mt-4 block text-[10px] uppercase tracking-wider text-muted">
            API Key
          </label>
          <div className="relative mt-1.5">
            <input
              type={showKey ? "text" : "password"}
              value={draft.apiKey}
              onChange={(e) => setDraftApiKey(e.target.value)}
              placeholder="sk-or-v1-..."
              className="w-full rounded-xl border border-white/8 bg-white/4 px-4 py-3 pr-10 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted/50 focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-foreground"
              aria-label={showKey ? "Hide key" : "Show key"}
            >
              {showKey ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </GlassCard>

        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-purple-400" />
            <h2 className="font-display text-sm font-medium text-white">
              Local Paths
            </h2>
          </div>
          <p className="mt-1 text-xs text-muted">
            Configure CLI installation and data directories
          </p>

          <label className="mt-4 block text-[10px] uppercase tracking-wider text-muted">
            CLI Project Path
          </label>
          <input
            type="text"
            value={cliPath}
            onChange={(e) => setCliPath(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-white/8 bg-white/4 px-4 py-3 font-mono text-sm text-foreground outline-none transition-all focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
          />

          <label className="mt-4 block text-[10px] uppercase tracking-wider text-muted">
            History File
          </label>
          <input
            type="text"
            value={historyPath}
            onChange={(e) => setHistoryPath(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-white/8 bg-white/4 px-4 py-3 font-mono text-sm text-foreground outline-none transition-all focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
          />
        </GlassCard>

        <CustomModelRegistry />

        <motion.button
          type="button"
          disabled={isSaving}
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={() => void handleSave()}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500/80 to-indigo-500/80 py-3 text-sm font-medium text-white shadow-lg shadow-cyan-500/10 transition-all hover:shadow-cyan-500/20 disabled:opacity-70"
        >
          <Save className="h-4 w-4" />
          {isSaving ? "Connecting…" : saved ? "Saved!" : "Save Configuration"}
        </motion.button>
      </motion.div>
    </AppShell>
  );
}
