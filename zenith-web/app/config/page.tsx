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
  const [paths, setPaths] = useState({
    config: "",
    data_dir: "",
    sessions: "",
    history: "",
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    void fetch("/api/config")
      .then((res) => res.json())
      .then((data: { paths?: typeof paths }) => {
        if (data.paths) setPaths(data.paths);
      })
      .catch(() => undefined);
  }, []);

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
            AXON stores config and sessions in your user profile (read-only)
          </p>

          <label className="label-caps mt-4 block">Config</label>
          <p className="input-vercel mt-1.5 font-mono text-xs text-[#a1a1aa]">
            {paths.config || "—"}
          </p>

          <label className="label-caps mt-4 block">Data directory</label>
          <p className="input-vercel mt-1.5 font-mono text-xs text-[#a1a1aa]">
            {paths.data_dir || "—"}
          </p>

          <label className="label-caps mt-4 block">Sessions</label>
          <p className="input-vercel mt-1.5 font-mono text-xs text-[#a1a1aa]">
            {paths.sessions || "—"}
          </p>

          <label className="label-caps mt-4 block">Input history</label>
          <p className="input-vercel mt-1.5 font-mono text-xs text-[#a1a1aa]">
            {paths.history || "—"}
          </p>
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
