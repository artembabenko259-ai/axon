"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, KeyRound, Loader2, Plug, Server } from "lucide-react";
import { useEffect, useRef } from "react";
import { useConfig, type ProviderType } from "@/context/ConfigContext";
import { cn } from "@/lib/utils";

const PROVIDERS: { value: ProviderType; label: string }[] = [
  { value: "openrouter", label: "OpenRouter" },
  { value: "ollama", label: "Local Ollama" },
  { value: "custom", label: "Custom" },
];

export function ConfigWidget() {
  const {
    config,
    draft,
    isOpen,
    isSaving,
    setIsOpen,
    setDraftProvider,
    setDraftApiKey,
    setDraftEndpointUrl,
    saveAndConnect,
  } = useConfig();

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, setIsOpen]);

  const showApiKey =
    draft.provider === "openrouter" || draft.provider === "custom";
  const showEndpoint = draft.provider === "ollama";

  const providerLabel =
    PROVIDERS.find((p) => p.value === config.provider)?.label ?? "—";

  return (
    <div ref={containerRef} className="relative">
      <motion.button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={cn(
          "flex items-center gap-2 rounded-xl px-3 py-2 text-xs transition-all duration-300",
          "glass border",
          isOpen
            ? "border-cyan-400/40 shadow-[0_0_20px_rgba(34,211,238,0.15)] ring-1 ring-cyan-400/25"
            : "border-white/8 hover:border-white/14 hover:bg-white/5",
          config.isConnected && !isOpen && "border-emerald-400/20",
        )}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
      >
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            config.isConnected
              ? "bg-success shadow-[0_0_6px_rgba(52,211,153,0.8)]"
              : "bg-muted",
          )}
        />
        <Plug className="h-3.5 w-3.5 text-cyan-400" />
        <span className="hidden font-medium text-foreground/90 sm:inline">
          {providerLabel}
        </span>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="h-3.5 w-3.5 text-muted" />
        </motion.span>
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            role="dialog"
            aria-label="AI Provider Configuration"
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className={cn(
              "absolute right-0 top-full z-50 mt-2 w-80 rounded-2xl p-4",
              "glass-strong border border-cyan-400/20",
              "shadow-[0_16px_48px_rgba(0,0,0,0.5),0_0_24px_rgba(34,211,238,0.08)]",
            )}
          >
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-400/10 ring-1 ring-cyan-400/20">
                <KeyRound className="h-3.5 w-3.5 text-cyan-400" />
              </div>
              <div>
                <p className="font-display text-xs font-medium text-white">
                  Global Config
                </p>
                <p className="text-[10px] text-muted">
                  Provider credentials &amp; endpoint
                </p>
              </div>
            </div>

            <label className="block text-[10px] uppercase tracking-wider text-muted">
              Provider
            </label>
            <div className="relative mt-1.5">
              <select
                value={draft.provider}
                onChange={(e) =>
                  setDraftProvider(e.target.value as ProviderType)
                }
                className="w-full appearance-none rounded-xl border border-white/8 bg-white/4 px-3 py-2.5 pr-8 text-sm text-foreground outline-none transition-all focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
              >
                {PROVIDERS.map((p) => (
                  <option
                    key={p.value}
                    value={p.value}
                    className="bg-[#0d0d14] text-foreground"
                  >
                    {p.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            </div>

            <AnimatePresence mode="wait">
              {showApiKey && (
                <motion.div
                  key="api-key"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <label className="mt-4 block text-[10px] uppercase tracking-wider text-muted">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={draft.apiKey}
                    onChange={(e) => setDraftApiKey(e.target.value)}
                    placeholder="sk-or-v1-..."
                    className="mt-1.5 w-full rounded-xl border border-white/8 bg-white/4 px-3 py-2.5 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted/40 focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
                  />
                </motion.div>
              )}

              {showEndpoint && (
                <motion.div
                  key="endpoint"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <label className="mt-4 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted">
                    <Server className="h-3 w-3" />
                    Endpoint URL
                  </label>
                  <input
                    type="url"
                    value={draft.endpointUrl}
                    onChange={(e) => setDraftEndpointUrl(e.target.value)}
                    placeholder="http://localhost:11434"
                    className="mt-1.5 w-full rounded-xl border border-white/8 bg-white/4 px-3 py-2.5 font-mono text-sm text-foreground outline-none transition-all placeholder:text-muted/40 focus:border-cyan-400/30 focus:ring-1 focus:ring-cyan-400/20"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <motion.button
              type="button"
              disabled={isSaving}
              whileHover={!isSaving ? { scale: 1.01 } : undefined}
              whileTap={!isSaving ? { scale: 0.99 } : undefined}
              onClick={() => void saveAndConnect()}
              className={cn(
                "mt-5 flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium transition-all",
                "bg-gradient-to-r from-cyan-500/80 to-indigo-500/80 text-white",
                "shadow-lg shadow-cyan-500/10 hover:shadow-cyan-500/25",
                "disabled:cursor-not-allowed disabled:opacity-70",
              )}
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Connecting…
                </>
              ) : (
                <>
                  <Plug className="h-4 w-4" />
                  Save &amp; Connect
                </>
              )}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
