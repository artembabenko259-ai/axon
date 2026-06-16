"use client";

import { motion, LayoutGroup } from "framer-motion";
import { cn } from "@/lib/utils";
import { EASE_OUT, TAP_PRESS } from "@/lib/motion";
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
      <div className="space-y-2">
        {allModels.map((model, index) => {
          const active = current === model.id;
          return (
            <motion.button
              key={model.id}
              type="button"
              layout
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.4, ease: EASE_OUT, layout: { duration: 0.3 } }}
              whileHover={{ y: -2, transition: { duration: 0.2, ease: EASE_OUT } }}
              whileTap={TAP_PRESS}
              onClick={() => handleSelect(model.id)}
              className={cn(
                "group relative w-full overflow-hidden rounded-lg border px-3 py-2.5 text-left transition-colors duration-200",
                active
                  ? "border-[#5DE4FF]/35 bg-[#5DE4FF]/8"
                  : "border-white/[0.06] hover:border-white/15 hover:bg-white/[0.03]",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-mono text-xs text-white/85">
                  {model.id}
                </span>
                {active ? (
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#5DE4FF]">
                    active
                  </span>
                ) : (
                  <span className="text-[10px] text-white/35">select</span>
                )}
              </div>
            </motion.button>
          );
        })}
      </div>
    </LayoutGroup>
  );
}
