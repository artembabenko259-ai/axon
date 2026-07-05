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

export type ProviderType = "openrouter" | "ollama" | "custom" | "antigravity";


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
  ollama: "http://127.0.0.1:11434/v1",
  custom: "",
  antigravity: "google-antigravity-sdk",
};

function endpointForProvider(
  provider: ProviderType,
  data: {
    ollamaBaseUrl?: string;
    customBaseUrl?: string;
    storedEndpoint?: string;
  },
): string {
  if (provider === "openrouter") {
    return DEFAULT_ENDPOINTS.openrouter;
  }
  if (provider === "antigravity") {
    return DEFAULT_ENDPOINTS.antigravity;
  }
  if (provider === "ollama") {
    return data.ollamaBaseUrl || data.storedEndpoint || DEFAULT_ENDPOINTS.ollama;
  }
  return data.customBaseUrl || data.storedEndpoint || "";
}

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
          ollamaBaseUrl?: string;
          customBaseUrl?: string;
        }) => {
          const provider = data.provider ?? stored.provider;
          const hasKey = Boolean(data.hasApiKey);
          const merged: AIConfig = {
            ...defaultConfig,
            ...stored,
            provider,
            isConnected: hasKey || stored.isConnected,
            endpointUrl: endpointForProvider(provider, {
              ollamaBaseUrl: data.ollamaBaseUrl,
              customBaseUrl: data.customBaseUrl,
              storedEndpoint: stored.endpointUrl,
            }),
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
        provider === "openrouter"
          ? DEFAULT_ENDPOINTS.openrouter
          : provider === "antigravity"
            ? DEFAULT_ENDPOINTS.antigravity
            : provider === "ollama"
              ? prev.endpointUrl || DEFAULT_ENDPOINTS.ollama
              : prev.endpointUrl || "",
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

    if (provider === "antigravity") {
      return {
        baseUrl: DEFAULT_ENDPOINTS.antigravity,
        apiKey: "sdk",
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
          endpointUrl: draft.endpointUrl.trim(),
          ollamaBaseUrl:
            draft.provider === "ollama" ? draft.endpointUrl.trim() : undefined,
          customBaseUrl:
            draft.provider === "custom" ? draft.endpointUrl.trim() : undefined,
        }),
      });

      const payload = (await response.json()) as {
        ok?: boolean;
        hasApiKey?: boolean;
        provider?: ProviderType;
        ollamaBaseUrl?: string;
        customBaseUrl?: string;
        error?: string;
      };

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Failed to save configuration");
      }

      const hasKey = Boolean(payload.hasApiKey);
      const next: AIConfig = {
        ...draft,
        apiKey: "",
        provider: payload.provider ?? draft.provider,
        isConnected: hasKey,
        endpointUrl: endpointForProvider(payload.provider ?? draft.provider, {
          ollamaBaseUrl: payload.ollamaBaseUrl,
          customBaseUrl: payload.customBaseUrl,
          storedEndpoint: draft.endpointUrl,
        }),
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
