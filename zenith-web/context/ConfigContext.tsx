"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ProviderType = "openrouter" | "ollama" | "custom";

export interface AIConfig {
  provider: ProviderType;
  apiKey: string;
  endpointUrl: string;
  isConnected: boolean;
}

interface ConfigContextValue {
  config: AIConfig;
  draft: AIConfig;
  hasServerApiKey: boolean;
  isOpen: boolean;
  isSaving: boolean;
  setIsOpen: (open: boolean) => void;
  setDraftProvider: (provider: ProviderType) => void;
  setDraftApiKey: (key: string) => void;
  setDraftEndpointUrl: (url: string) => void;
  saveAndConnect: () => Promise<boolean>;
  getRequestConfig: () => {
    baseUrl: string;
    apiKey: string | null;
    provider: ProviderType;
  };
}

const STORAGE_KEY = "axon-ai-config";

const DEFAULT_ENDPOINTS: Record<ProviderType, string> = {
  openrouter: "https://openrouter.ai/api/v1",
  ollama: "http://localhost:11434",
  custom: "",
};

const defaultConfig: AIConfig = {
  provider: "openrouter",
  apiKey: "",
  endpointUrl: DEFAULT_ENDPOINTS.openrouter,
  isConnected: false,
};

const ConfigContext = createContext<ConfigContextValue | null>(null);

function loadStoredConfig(): AIConfig {
  if (typeof window === "undefined") return defaultConfig;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultConfig;
    const parsed = JSON.parse(raw) as AIConfig;
    return { ...defaultConfig, ...parsed };
  } catch {
    return defaultConfig;
  }
}

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<AIConfig>(defaultConfig);
  const [draft, setDraft] = useState<AIConfig>(defaultConfig);
  const [hasServerApiKey, setHasServerApiKey] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = loadStoredConfig();

    void fetch("/api/config")
      .then((res) => res.json())
      .then(
        (data: {
          model?: string;
          provider?: ProviderType;
          hasApiKey?: boolean;
        }) => {
          const provider = data.provider ?? stored.provider;
          const hasKey = Boolean(data.hasApiKey);
          const merged: AIConfig = {
            ...defaultConfig,
            ...stored,
            provider,
            isConnected: hasKey || stored.isConnected,
            endpointUrl:
              provider === "openrouter"
                ? DEFAULT_ENDPOINTS.openrouter
                : stored.endpointUrl,
          };
          setHasServerApiKey(hasKey);
          setConfig(merged);
          setDraft(merged);
          setHydrated(true);
        },
      )
      .catch(() => {
        setConfig(stored);
        setDraft(stored);
        setHydrated(true);
      });
  }, []);

  const setDraftProvider = useCallback((provider: ProviderType) => {
    setDraft((prev) => ({
      ...prev,
      provider,
      endpointUrl:
        provider === "ollama"
          ? prev.endpointUrl || DEFAULT_ENDPOINTS.ollama
          : provider === "openrouter"
            ? DEFAULT_ENDPOINTS.openrouter
            : "",
    }));
  }, []);

  const setDraftApiKey = useCallback((apiKey: string) => {
    setDraft((prev) => ({ ...prev, apiKey }));
  }, []);

  const setDraftEndpointUrl = useCallback((endpointUrl: string) => {
    setDraft((prev) => ({ ...prev, endpointUrl }));
  }, []);

  const getRequestConfig = useCallback(() => {
    const { provider, apiKey, endpointUrl } = config;

    if (provider === "openrouter") {
      return {
        baseUrl: DEFAULT_ENDPOINTS.openrouter,
        apiKey: apiKey || null,
        provider,
      };
    }

    if (provider === "ollama") {
      return {
        baseUrl: endpointUrl || DEFAULT_ENDPOINTS.ollama,
        apiKey: null,
        provider,
      };
    }

    return {
      baseUrl: endpointUrl || "",
      apiKey: apiKey || null,
      provider,
    };
  }, [config]);

  const saveAndConnect = useCallback(async () => {
    setIsSaving(true);
    try {
      const response = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...(draft.apiKey.trim() ? { apiKey: draft.apiKey.trim() } : {}),
          provider: draft.provider,
        }),
      });

      const payload = (await response.json()) as {
        ok?: boolean;
        hasApiKey?: boolean;
        error?: string;
      };

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Failed to save configuration");
      }

      const hasKey = Boolean(payload.hasApiKey);
      const next: AIConfig = {
        ...draft,
        apiKey: "",
        isConnected: hasKey,
        endpointUrl:
          draft.provider === "openrouter"
            ? DEFAULT_ENDPOINTS.openrouter
            : draft.endpointUrl,
      };

      setHasServerApiKey(hasKey);
      setConfig(next);
      setDraft(next);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setIsOpen(false);
      return true;
    } catch (error) {
      console.error(error);
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [draft]);

  const value = useMemo<ConfigContextValue>(
    () => ({
      config: hydrated ? config : defaultConfig,
      draft,
      hasServerApiKey,
      isOpen,
      isSaving,
      setIsOpen,
      setDraftProvider,
      setDraftApiKey,
      setDraftEndpointUrl,
      saveAndConnect,
      getRequestConfig,
    }),
    [
      config,
      draft,
      hasServerApiKey,
      hydrated,
      isOpen,
      isSaving,
      saveAndConnect,
      getRequestConfig,
    ],
  );

  return (
    <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>
  );
}

export function useConfig() {
  const ctx = useContext(ConfigContext);
  if (!ctx) {
    throw new Error("useConfig must be used within ConfigProvider");
  }
  return ctx;
}
