"use client";

import { motion, LayoutGroup } from "framer-motion";
import { cn } from "@/lib/utils";
import { useModel } from "@/context/ModelContext";

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  description: string;
  isCustom?: boolean;
}

export const DEFAULT_MODELS: ModelOption[] = [
  {
    id: "anthropic/claude-3.5-sonnet",
    name: "Claude 3.5",
    provider: "Anthropic",
    description: "Balanced reasoning & speed",
  },
  {
    id: "openai/gpt-4o",
    name: "GPT-4o",
    provider: "OpenAI",
    description: "Multimodal flagship",
  },
  {
    id: "qwen/qwen-2.5-coder-32b-instruct",
    name: "Qwen Coder",
    provider: "Qwen",
    description: "Code & CLI optimized",
  },
  {
    id: "meta-llama/llama-3.1-8b-instruct",
    name: "Llama 3.1",
    provider: "Meta",
    description: "Fast local default",
  },
];

interface ModelSelectorProps {
  selected?: string;
  onSelect?: (id: string) => void;
}

export function ModelSelector({ selected, onSelect }: ModelSelectorProps) {
  const { activeModelId, allModels, setActiveModel } = useModel();
  const current = selected ?? activeModelId;
  const handleSelect = onSelect ?? setActiveModel;

  return (
    <LayoutGroup>
      <div className="grid gap-3 sm:grid-cols-2">
        {allModels.map((model, index) => {
          const active = current === model.id;
          return (
            <motion.button
              key={model.id}
              type="button"
              layout
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, layout: { duration: 0.3 } }}
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={() => handleSelect(model.id)}
              className={cn(
                "glass rounded-xl p-4 text-left transition-all duration-200",
                "hover:backdrop-blur-[24px]",
                active
                  ? "border-cyan-400/30 bg-cyan-400/5 ring-1 ring-cyan-400/20"
                  : "hover:border-white/12 hover:bg-white/5",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-display text-sm font-medium text-white">
                  {model.name}
                </span>
                <div className="flex items-center gap-1.5">
                  {model.isCustom && (
                    <span className="rounded-md bg-purple-500/15 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-purple-300">
                      Custom
                    </span>
                  )}
                  {active && (
                    <motion.span
                      layoutId="model-active-dot"
                      className="h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]"
                    />
                  )}
                </div>
              </div>
              <p className="mt-0.5 text-[10px] uppercase tracking-wider text-muted">
                {model.provider}
              </p>
              <p className="mt-2 line-clamp-2 text-xs text-muted">
                {model.description}
              </p>
            </motion.button>
          );
        })}
      </div>
    </LayoutGroup>
  );
}
