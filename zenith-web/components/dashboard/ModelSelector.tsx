"use client";

import { motion, LayoutGroup } from "framer-motion";
import { cn } from "@/lib/utils";
import { EASE_OUT, TAP_PRESS } from "@/lib/motion";
import { useModel } from "@/context/ModelContext";
import { useConfig } from "@/context/ConfigContext";

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

export const ANTIGRAVITY_MODELS: ModelOption[] = [
  {
    id: "gemini-3.5-flash",
    name: "Gemini 3.5 Flash",
    provider: "Google",
    description: "Default model. High speed, balanced for agent tasks and coding.",
  },
  {
    id: "gemini-3.1-pro-high",
    name: "Gemini 3.1 Pro (high)",
    provider: "Google",
    description: "Advanced model for complex logic, planning, and large contexts.",
  },
  {
    id: "gemini-3.1-pro-low",
    name: "Gemini 3.1 Pro (low)",
    provider: "Google",
    description: "Speed-optimized Pro model for standard orchestration tasks.",
  },
  {
    id: "gemini-3-flash",
    name: "Gemini 3 Flash",
    provider: "Google",
    description: "Basic fast model for simple subtasks.",
  },
  {
    id: "claude-sonnet-4.6-thinking",
    name: "Claude Sonnet 4.6 (thinking)",
    provider: "Anthropic",
    description: "Deep step-by-step reasoning and coding.",
  },
  {
    id: "claude-opus-4.6-thinking",
    name: "Claude Opus 4.6 (thinking)",
    provider: "Anthropic",
    description: "Flagship heavy model for complex analysis.",
  },
  {
    id: "gpt-oss-120b",
    name: "GPT-OSS-120b",
    provider: "Open-Source",
    description: "Large open-source model available within ecosystem.",
  },
];

interface ModelSelectorProps {
  selected?: string;
  onSelect?: (id: string) => void;
}

export function ModelSelector({ selected, onSelect }: ModelSelectorProps) {
  const { activeModelId, allModels, setActiveModel } = useModel();
  const { config } = useConfig();
  const current = selected ?? activeModelId;
  const handleSelect = onSelect ?? setActiveModel;

  const displayModels = config.provider === "antigravity" ? ANTIGRAVITY_MODELS : allModels;

  return (
    <LayoutGroup>
      <div className="space-y-2">
        {displayModels.map((model, index) => {
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
                  ? "border-brand/35 bg-brand/8"
                  : "border-white/[0.06] hover:border-white/15 hover:bg-white/[0.03]",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-mono text-xs text-white/85">
                  {model.id}
                </span>
                {active ? (
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-brand">
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
