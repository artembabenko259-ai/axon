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
  const {
    config,
    draft,
    hasServerApiKey,
    setDraftApiKey,
    saveAndConnect,
    isSaving,
  } = useConfig();
  const [showKey, setShowKey] = useState(false);
  const [paths, setPaths] = useState({
    config: "",
    data_dir: "",
    sessions: "",
    history: "",
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetch("/api/config")
      .then((res) => res.json())
      .then((data: { paths?: typeof paths }) => {
        if (data.paths) setPaths(data.paths);
      })
      .catch(() => undefined);
  }, []);

  const handleSave = async () => {
    setError("");
    if (draft.provider === "openrouter" && !hasServerApiKey && !draft.apiKey.trim()) {
      setError("Paste your OpenRouter API key first.");
      return;
    }

    const ok = await saveAndConnect();
    if (!ok) {
      setError("Could not save configuration. Check that AXON can write to AppData.");
      return;
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const keyPlaceholder = hasServerApiKey
    ? "Key saved — paste a new value to replace"
    : "sk-or-v1-...";

  return (
    <AppShell title="Configuration">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mx-auto flex w-full max-w-2xl flex-col gap-4"
      >
        <GlassCard delay={0}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Key className="h-4 w-4 text-white" />
              <h2 className="text-sm font-medium tracking-tight text-white">API Keys</h2>
            </div>
            <span
              className={
                hasServerApiKey
                  ? "rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-300"
                  : "rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-200"
              }
            >
              {hasServerApiKey ? "Configured" : "Required"}
            </span>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-[#888]">
            This is the easiest way to connect AXON. Keys are stored locally in{" "}
            <code className="text-[#ccc]">config.json</code> — the CLI reads the same file.
            Get a key at{" "}
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

          <label className="label-caps mt-4 block">OpenRouter API Key</label>
          <div className="relative mt-1.5">
            <input
              type={showKey ? "text" : "password"}
              value={draft.apiKey}
              onChange={(e) => setDraftApiKey(e.target.value)}
              placeholder={keyPlaceholder}
              className="input-vercel pr-10 font-mono"
              autoComplete="off"
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
          <p className="mt-2 text-[11px] text-[#666]">
            Provider: <span className="text-white">{config.provider}</span> · also editable in the{" "}
            <button
              type="button"
              onClick={() => window.dispatchEvent(new CustomEvent("axon-open-config-widget"))}
              className="text-cyan-300 hover:underline"
            >
              header widget
            </button>
          </p>
          {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}
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
          {isSaving ? "Saving…" : saved ? "Saved!" : "Save API Key"}
        </motion.button>

        <p className="text-center text-xs text-[#666]">
          After saving, run <code className="text-[#aaa]">axon doctor</code> in the terminal to verify.
        </p>
      </motion.div>
    </AppShell>
  );
}
