"use client";

import { motion } from "framer-motion";
import { Eye, EyeOff, FolderOpen, Key, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { CustomModelRegistry } from "@/components/config/CustomModelRegistry";
import { RuntimePolicyPanel } from "@/components/config/RuntimePolicyPanel";
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
            <Key className="h-4 w-4 text-white" />
            <h2 className="text-sm font-medium tracking-tight text-white">API Keys</h2>
          </div>
          <p className="mt-1 text-xs text-[#888]">
            Provider settings sync with the Global Config widget. Current:{" "}
            <span className="text-white">{config.provider}</span>
          </p>

          <label className="label-caps mt-4 block">API Key</label>
          <div className="relative mt-1.5">
            <input
              type={showKey ? "text" : "password"}
              value={draft.apiKey}
              onChange={(e) => setDraftApiKey(e.target.value)}
              placeholder="sk-or-v1-..."
              className="input-vercel pr-10 font-mono"
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#666] hover:text-white"
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
            <FolderOpen className="h-4 w-4 text-white" />
            <h2 className="text-sm font-medium tracking-tight text-white">Local Paths</h2>
          </div>
          <p className="mt-1 text-xs text-[#888]">
            Configure CLI installation and data directories
          </p>

          <label className="label-caps mt-4 block">CLI Project Path</label>
          <input
            type="text"
            value={cliPath}
            onChange={(e) => setCliPath(e.target.value)}
            className="input-vercel mt-1.5 font-mono"
          />

          <label className="label-caps mt-4 block">History File</label>
          <input
            type="text"
            value={historyPath}
            onChange={(e) => setHistoryPath(e.target.value)}
            className="input-vercel mt-1.5 font-mono"
          />
        </GlassCard>

        <RuntimePolicyPanel />

        <CustomModelRegistry />

        <motion.button
          type="button"
          disabled={isSaving}
          whileTap={{ scale: 0.97 }}
          onClick={() => void handleSave()}
          className="btn-vercel-primary w-full rounded-lg disabled:opacity-70"
        >
          <Save className="h-4 w-4" />
          {isSaving ? "Connecting…" : saved ? "Saved!" : "Save Configuration"}
        </motion.button>
      </motion.div>
    </AppShell>
  );
}
