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
      <div className="grid gap-3 sm:grid-cols-2">
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
                "group relative overflow-hidden rounded-lg border border-white/[0.06] bg-[#0a0a0a] p-4 text-left transition-colors duration-200",
                active
                  ? "border-white/15 bg-[#111]"
                  : "hover:border-white/10 hover:bg-[#111]",
              )}
            >
              <div
                aria-hidden
                className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
              >
                <div className="absolute -top-[40%] left-1/2 h-[120%] w-[140%] -translate-x-1/2 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.06),transparent_65%)]" />
              </div>
              <div className="relative">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium tracking-tight text-white">
                    {model.name}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {model.isCustom && (
                      <span className="label-caps !text-[9px] rounded-md border border-white/5 bg-zinc-950 px-1.5 py-0.5">
                        Custom
                      </span>
                    )}
                    {active && (
                      <motion.span
                        layoutId="model-active-dot"
                        className="h-1.5 w-1.5 rounded-full bg-white"
                      />
                    )}
                  </div>
                </div>
                <p className="label-caps mt-2 !text-[9px]">{model.provider}</p>
                <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-[#71717a]">
                  {model.description}
                </p>
              </div>
            </motion.button>
          );
        })}
      </div>
    </LayoutGroup>
  );
}
