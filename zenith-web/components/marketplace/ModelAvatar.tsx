"use client";

import { cn } from "@/lib/utils";

const PROVIDER_COLORS: Record<string, string> = {
  anthropic: "from-orange-500/80 to-amber-600/80",
  openai: "from-emerald-500/80 to-teal-600/80",
  meta: "from-blue-500/80 to-indigo-600/80",
  google: "from-sky-500/80 to-blue-600/80",
  qwen: "from-purple-500/80 to-violet-600/80",
  mistralai: "from-rose-500/80 to-pink-600/80",
  deepseek: "from-cyan-500/80 to-blue-600/80",
  cohere: "from-lime-500/80 to-green-600/80",
};

interface ModelAvatarProps {
  provider: string;
  name: string;
  size?: "sm" | "md";
}

export function ModelAvatar({ provider, name, size = "sm" }: ModelAvatarProps) {
  const gradient =
    PROVIDER_COLORS[provider.toLowerCase()] ??
    "from-slate-500/80 to-slate-600/80";
  const initial = (name || provider).charAt(0).toUpperCase();
  const dim = size === "sm" ? "h-8 w-8 text-xs" : "h-10 w-10 text-sm";

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-lg bg-gradient-to-br font-display font-semibold text-white ring-1 ring-white/10",
        gradient,
        dim,
      )}
    >
      {initial}
    </div>
  );
}
