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
        <Plus className="h-4 w-4 text-white" />
        <h2 className="text-sm font-medium tracking-tight text-white">
          Custom Model Registry
        </h2>
      </div>
      <p className="mt-1 text-xs text-[#888]">
        Add custom models — they appear in the dashboard Model Selection grid.
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="label-caps">Model ID</label>
          <input
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            placeholder="anthropic/claude-3-opus"
            className="input-vercel mt-1 font-mono"
          />
        </div>
        <div>
          <label className="label-caps">Friendly Name</label>
          <input
            value={friendlyName}
            onChange={(e) => setFriendlyName(e.target.value)}
            placeholder="Claude Opus"
            className="input-vercel mt-1"
          />
        </div>
        <div>
          <label className="label-caps">Description</label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Most capable reasoning model"
            className="input-vercel mt-1"
          />
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}

      <motion.button
        type="button"
        whileTap={{ scale: 0.97 }}
        onClick={handleAdd}
        className="btn-vercel-secondary mt-4 rounded-lg text-xs"
      >
        <Plus className="h-3.5 w-3.5" />
        Add Model
      </motion.button>

      {customModels.length > 0 && (
        <ul className="mt-4 space-y-2 border-t border-white/[0.06] pt-4">
          {customModels.map((model) => (
            <li
              key={model.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-white/[0.06] bg-[#111] px-3 py-2.5"
            >
              <div className="min-w-0">
                <p className="truncate text-xs font-medium text-white">
                  {model.friendlyName}
                </p>
                <p className="truncate font-mono text-[10px] text-[#666]">
                  {model.id}
                </p>
              </div>
              <button
                type="button"
                onClick={() => removeCustomModel(model.id)}
                className="shrink-0 rounded-md p-1.5 text-[#666] hover:bg-red-500/10 hover:text-red-400"
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
