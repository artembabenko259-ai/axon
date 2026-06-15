"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_MODELS,
  type ModelOption,
} from "@/components/dashboard/ModelSelector";
import { useWebSocket } from "@/context/ChatContext";

export interface CustomModel {
  id: string;
  friendlyName: string;
  description: string;
}

const CUSTOM_MODELS_KEY = "axon-custom-models";
const MODEL_STORAGE_KEY = "axon-active-model";
const ENABLED_STORAGE_KEY = "axon-model-enabled";
const DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct";

interface ModelContextValue {
  activeModelId: string;
  enabledModels: Record<string, boolean>;
  customModels: CustomModel[];
  allModels: ModelOption[];
  isSwitching: boolean;
  setActiveModel: (modelId: string) => void;
  toggleModelEnabled: (modelId: string) => void;
  isModelEnabled: (modelId: string) => boolean;
  addCustomModel: (model: CustomModel) => void;
  removeCustomModel: (id: string) => void;
}

const ModelContext = createContext<ModelContextValue | null>(null);

function loadActiveModel(): string {
  if (typeof window === "undefined") return DEFAULT_MODEL;
  return localStorage.getItem(MODEL_STORAGE_KEY) ?? DEFAULT_MODEL;
}

function loadEnabledModels(): Record<string, boolean> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(ENABLED_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function loadCustomModels(): CustomModel[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CUSTOM_MODELS_KEY);
    return raw ? (JSON.parse(raw) as CustomModel[]) : [];
  } catch {
    return [];
  }
}

function customToOption(model: CustomModel): ModelOption {
  const provider = model.id.split("/")[0] ?? "custom";
  return {
    id: model.id,
    name: model.friendlyName,
    provider: provider.charAt(0).toUpperCase() + provider.slice(1),
    description: model.description,
    isCustom: true,
  };
}

export function ModelProvider({ children }: { children: ReactNode }) {
  const { sendSetModel, activeModel: bridgeModel } = useWebSocket();
  const [activeModelId, setActiveModelId] = useState(DEFAULT_MODEL);
  const [enabledModels, setEnabledModels] = useState<Record<string, boolean>>(
    {},
  );
  const [customModels, setCustomModels] = useState<CustomModel[]>([]);
  const [isSwitching, setIsSwitching] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const lastUserPickRef = useRef<string | null>(null);

  useEffect(() => {
    setActiveModelId(loadActiveModel());
    setEnabledModels(loadEnabledModels());
    setCustomModels(loadCustomModels());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!bridgeModel) return;
    if (bridgeModel === activeModelId) return;
    if (lastUserPickRef.current && bridgeModel === DEFAULT_MODEL) return;

    setActiveModelId(bridgeModel);
    localStorage.setItem(MODEL_STORAGE_KEY, bridgeModel);
  }, [bridgeModel, activeModelId]);

  const allModels = useMemo(() => {
    const custom = customModels.map(customToOption);
    const defaultIds = new Set(DEFAULT_MODELS.map((m) => m.id));
    const uniqueCustom = custom.filter((m) => !defaultIds.has(m.id));
    return [...DEFAULT_MODELS, ...uniqueCustom];
  }, [customModels]);

  const setActiveModel = useCallback(
    (modelId: string) => {
      if (modelId === activeModelId) return;

      lastUserPickRef.current = modelId;
      setIsSwitching(true);
      setActiveModelId(modelId);
      localStorage.setItem(MODEL_STORAGE_KEY, modelId);
      setEnabledModels((prev) => {
        const next = { ...prev, [modelId]: true };
        localStorage.setItem(ENABLED_STORAGE_KEY, JSON.stringify(next));
        return next;
      });
      sendSetModel(modelId);
      setTimeout(() => setIsSwitching(false), 800);
    },
    [activeModelId, sendSetModel],
  );

  const toggleModelEnabled = useCallback((modelId: string) => {
    setEnabledModels((prev) => {
      const next = { ...prev, [modelId]: !(prev[modelId] ?? true) };
      localStorage.setItem(ENABLED_STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const isModelEnabled = useCallback(
    (modelId: string) => enabledModels[modelId] ?? true,
    [enabledModels],
  );

  const addCustomModel = useCallback((model: CustomModel) => {
    setCustomModels((prev) => {
      const filtered = prev.filter((m) => m.id !== model.id);
      const next = [...filtered, model];
      localStorage.setItem(CUSTOM_MODELS_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const removeCustomModel = useCallback((id: string) => {
    setCustomModels((prev) => {
      const next = prev.filter((m) => m.id !== id);
      localStorage.setItem(CUSTOM_MODELS_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const value = useMemo<ModelContextValue>(
    () => ({
      activeModelId: hydrated ? activeModelId : DEFAULT_MODEL,
      enabledModels,
      customModels,
      allModels,
      isSwitching,
      setActiveModel,
      toggleModelEnabled,
      isModelEnabled,
      addCustomModel,
      removeCustomModel,
    }),
    [
      activeModelId,
      allModels,
      customModels,
      enabledModels,
      hydrated,
      isSwitching,
      setActiveModel,
      toggleModelEnabled,
      isModelEnabled,
      addCustomModel,
      removeCustomModel,
    ],
  );

  return (
    <ModelContext.Provider value={value}>{children}</ModelContext.Provider>
  );
}

export function useModel() {
  const ctx = useContext(ModelContext);
  if (!ctx) throw new Error("useModel must be used within ModelProvider");
  return ctx;
}
