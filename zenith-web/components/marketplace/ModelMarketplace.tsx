"use client";

import { motion } from "framer-motion";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  Loader2,
  Search,
  Sparkles,
  Star,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ModelAvatar } from "@/components/marketplace/ModelAvatar";
import { useModel } from "@/context/ModelContext";
import {
  formatContext,
  formatPrice,
  type MarketplaceModel,
  type ModelCategory,
} from "@/lib/models";
import { cn } from "@/lib/utils";

const ROW_HEIGHT = 56;
const CATEGORIES: { id: ModelCategory; label: string }[] = [
  { id: "all", label: "All" },
  { id: "coding", label: "Coding" },
  { id: "general", label: "General" },
  { id: "fast", label: "Fast" },
];

const GRID_COLS =
  "grid grid-cols-[minmax(200px,2fr)_minmax(80px,1fr)_minmax(100px,1fr)_minmax(100px,1fr)_minmax(90px,0.8fr)_72px]";

export function ModelMarketplace() {
  const { activeModelId, setActiveModel, toggleModelEnabled, isModelEnabled } =
    useModel();

  const [models, setModels] = useState<MarketplaceModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<ModelCategory>("all");

  const parentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/models");
        const json = await res.json();
        if (!res.ok) throw new Error(json.error ?? "Failed to load models");
        if (!cancelled) setModels(json.models ?? []);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return models.filter((m) => {
      const matchesSearch =
        !q ||
        m.id.toLowerCase().includes(q) ||
        m.name.toLowerCase().includes(q) ||
        m.provider.toLowerCase().includes(q);

      const matchesCategory =
        category === "all" || m.categories.includes(category);

      return matchesSearch && matchesCategory;
    });
  }, [models, search, category]);

  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  const handleRowClick = useCallback(
    (modelId: string) => {
      setActiveModel(modelId);
    },
    [setActiveModel],
  );

  return (
    <div className="lunar-card flex flex-col overflow-hidden">
      <div className="border-b border-white/[0.06] px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="label-mono">Marketplace</p>
            <h2 className="mt-1 text-sm font-semibold tracking-tight text-white">
              Model Marketplace
            </h2>
            <p className="mt-0.5 text-xs text-white/45">
              {loading
                ? "Loading pricing from OpenRouter…"
                : `${filtered.length} models available`}
            </p>
          </div>

          <div className="relative w-full sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-600" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search models…"
              className="input-vercel pl-9"
            />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setCategory(cat.id)}
              className={cn(
                "rounded-md px-2.5 py-1 text-[10px] font-semibold uppercase tracking-widest transition-colors",
                category === cat.id
                  ? "bg-[#5DE4FF]/15 text-[#5DE4FF]"
                  : "text-white/40 hover:bg-white/[0.04] hover:text-white/70",
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Column headers */}
      <div className="overflow-x-auto">
        <div className="min-w-[640px]">
          <div
            className={cn(
              GRID_COLS,
              "border-b border-zinc-800/50 px-4 py-3 text-xs font-semibold uppercase tracking-widest text-zinc-500 sm:px-5",
            )}
          >
            <span>Model Name</span>
            <span>Context</span>
            <span className="text-right">Input $/1M</span>
            <span className="text-right">Output $/1M</span>
            <span className="text-center">Status</span>
            <span />
          </div>

          {/* Body */}
          <div
            ref={parentRef}
            className="relative h-[min(420px,50vh)] overflow-y-auto logs-scroll"
          >
        {loading && (
          <div className="flex h-full items-center justify-center gap-2 text-sm text-zinc-500">
            <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
            Fetching OpenRouter pricing…
          </div>
        )}

        {error && !loading && (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-red-400">
            {error}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="flex h-full items-center justify-center text-sm text-zinc-500">
            No models match your filters.
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              width: "100%",
              position: "relative",
            }}
          >
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const model = filtered[virtualRow.index];
              const enabled = isModelEnabled(model.id);
              const isActive = activeModelId === model.id;

              return (
                <motion.div
                  key={model.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => handleRowClick(model.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleRowClick(model.id);
                    }
                  }}
                  initial={false}
                  className={cn(
                    GRID_COLS,
                    "group absolute left-0 top-0 w-full cursor-pointer items-center border-b border-zinc-800/50 px-4 transition-colors duration-150 sm:px-5",
                    "hover:bg-zinc-900/50",
                    isActive && "bg-zinc-900/80",
                  )}
                  style={{
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  {/* Model name */}
                  <div className="flex min-w-0 items-center gap-3 py-2">
                    <ModelAvatar provider={model.provider} name={model.name} />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <p className="truncate text-xs font-medium text-zinc-100">
                          {model.name}
                        </p>
                        {model.isTrending && (
                          <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-zinc-400">
                            <TrendingUp className="h-2.5 w-2.5" />
                            Trending
                          </span>
                        )}
                        {model.isRecommended && (
                          <span className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-emerald-500/90">
                            <Star className="h-2.5 w-2.5" />
                            Value
                          </span>
                        )}
                      </div>
                      <p className="truncate font-mono text-[10px] text-zinc-600">
                        {model.id}
                      </p>
                    </div>
                  </div>

                  {/* Context */}
                  <span className="font-mono text-xs tabular-nums tracking-tight text-zinc-400">
                    {formatContext(model.contextWindow)}
                  </span>

                  {/* Input price */}
                  <span className="text-right font-mono text-xs tabular-nums tracking-tight text-zinc-300">
                    {formatPrice(model.inputPricePerMillion)}
                  </span>

                  {/* Output price */}
                  <span className="text-right font-mono text-xs tabular-nums tracking-tight text-zinc-300">
                    {formatPrice(model.outputPricePerMillion)}
                  </span>

                  {/* Status toggle */}
                  <div className="flex justify-center">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleModelEnabled(model.id);
                      }}
                      className={cn(
                        "relative h-4 w-7 rounded-full transition-colors duration-150",
                        enabled ? "bg-zinc-600" : "bg-zinc-800",
                      )}
                      aria-label={`Toggle ${model.name}`}
                    >
                      <motion.span
                        layout
                        className={cn(
                          "absolute top-0.5 h-3 w-3 rounded-full bg-zinc-200 shadow-sm transition-all",
                          enabled ? "left-[14px]" : "left-0.5",
                        )}
                      />
                    </button>
                  </div>

                  {/* Active indicator */}
                  <div className="flex justify-end">
                    {isActive && (
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="flex items-center gap-1 text-[10px] text-blue-400"
                      >
                        <Sparkles className="h-3 w-3" />
                      </motion.span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
          </div>
        </div>
      </div>
    </div>
  );
}
