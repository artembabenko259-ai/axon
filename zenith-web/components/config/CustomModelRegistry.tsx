"use client";

import { motion } from "framer-motion";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { GlassCard } from "@/components/ui/GlassCard";
import { useModel } from "@/context/ModelContext";

export function CustomModelRegistry() {
  const { customModels, addCustomModel, removeCustomModel } = useModel();
  const [modelId, setModelId] = useState("");
  const [friendlyName, setFriendlyName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const handleAdd = () => {
    const id = modelId.trim();
    const name = friendlyName.trim();
    const desc = description.trim();

    if (!id || !name) {
      setError("Model ID and Friendly Name are required.");
      return;
    }
    if (!id.includes("/")) {
      setError("Model ID should include provider prefix (e.g. anthropic/claude-3-opus).");
      return;
    }

    addCustomModel({ id, friendlyName: name, description: desc });
    setModelId("");
    setFriendlyName("");
    setDescription("");
    setError("");
  };

  return (
    <GlassCard delay={0.15}>
      <div className="flex items-center gap-2">
        <Plus className="h-4 w-4 text-purple-400" />
        <h2 className="font-display text-sm font-medium text-white">
          Custom Model Registry
        </h2>
      </div>
      <p className="mt-1 text-xs text-muted">
        Add custom models — they appear in the dashboard Model Selection grid.
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="text-[10px] uppercase tracking-wider text-muted">
            Model ID
          </label>
          <input
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            placeholder="anthropic/claude-3-opus"
            className="mt-1 w-full rounded-xl border border-white/8 bg-white/4 px-3 py-2.5 font-mono text-sm outline-none focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted">
            Friendly Name
          </label>
          <input
            value={friendlyName}
            onChange={(e) => setFriendlyName(e.target.value)}
            placeholder="Claude Opus"
            className="mt-1 w-full rounded-xl border border-white/8 bg-white/4 px-3 py-2.5 text-sm outline-none focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
          />
        </div>
        <div>
          <label className="text-[10px] uppercase tracking-wider text-muted">
            Description
          </label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Most capable reasoning model"
            className="mt-1 w-full rounded-xl border border-white/8 bg-white/4 px-3 py-2.5 text-sm outline-none focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
          />
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

      <motion.button
        type="button"
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        onClick={handleAdd}
        className="mt-4 flex items-center gap-2 rounded-xl bg-white/6 px-4 py-2.5 text-xs font-medium text-white ring-1 ring-white/10 transition-all hover:ring-cyan-400/25"
      >
        <Plus className="h-3.5 w-3.5" />
        Add Model
      </motion.button>

      {customModels.length > 0 && (
        <ul className="mt-4 space-y-2 border-t border-white/6 pt-4">
          {customModels.map((model) => (
            <li
              key={model.id}
              className="flex items-center justify-between gap-3 rounded-xl bg-white/3 px-3 py-2.5"
            >
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-white">
                  {model.friendlyName}
                </p>
                <p className="truncate font-mono text-[10px] text-muted">
                  {model.id}
                </p>
              </div>
              <button
                type="button"
                onClick={() => removeCustomModel(model.id)}
                className="shrink-0 rounded-lg p-1.5 text-muted hover:bg-red-500/10 hover:text-red-400"
                aria-label={`Remove ${model.friendlyName}`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </GlassCard>
  );
}
