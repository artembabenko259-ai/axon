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
    const openWidget = () => setIsOpen(true);
    window.addEventListener("axon-open-config-widget", openWidget);
    return () => window.removeEventListener("axon-open-config-widget", openWidget);
  }, [setIsOpen]);

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
  const showEndpoint =
    draft.provider === "ollama" || draft.provider === "custom";

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
          "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition-all duration-200",
          isOpen
            ? "border-white/20 bg-white/[0.05] text-white"
            : "border-white/[0.08] text-[#888] hover:border-white/15 hover:text-white",
          config.isConnected && !isOpen && "border-emerald-500/20",
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
        <Plug className="h-3.5 w-3.5" />
        <span className="hidden font-medium sm:inline">
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
              "absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-white/[0.08] bg-black/90 p-4 backdrop-blur-md",
              "shadow-[0_16px_48px_rgba(0,0,0,0.8)]",
            )}
          >
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-md border border-white/[0.08] bg-[#111]">
                <KeyRound className="h-3.5 w-3.5 text-white" />
              </div>
              <div>
                <p className="text-xs font-medium text-white">Global Config</p>
                <p className="text-[10px] text-[#666]">
                  Provider credentials &amp; endpoint
                </p>
              </div>
            </div>

            <label className="label-caps">Provider</label>
            <div className="relative mt-1.5">
              <select
                value={draft.provider}
                onChange={(e) =>
                  setDraftProvider(e.target.value as ProviderType)
                }
                className="input-vercel mt-1.5 appearance-none pr-8"
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
                  <label className="label-caps mt-4 block">API Key</label>
                  <input
                    type="password"
                    value={draft.apiKey}
                    onChange={(e) => setDraftApiKey(e.target.value)}
                    placeholder={
                      draft.provider === "custom" ? "sk-..." : "sk-or-v1-..."
                    }
                    className="input-vercel mt-1.5 font-mono"
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
                  <label className="label-caps mt-4 flex items-center gap-1.5">
                    <Server className="h-3 w-3" />
                    Endpoint URL
                  </label>
                  <input
                    type="url"
                    value={draft.endpointUrl}
                    onChange={(e) => setDraftEndpointUrl(e.target.value)}
                    placeholder={
                      draft.provider === "custom"
                        ? "https://api.example.com/v1"
                        : "http://127.0.0.1:11434/v1"
                    }
                    className="input-vercel mt-1.5 font-mono"
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
                "btn-vercel-primary mt-5 w-full rounded-lg",
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
