import type { ProviderType } from "@/context/ConfigContext";

export interface AIRequestConfig {
  baseUrl: string;
  apiKey: string | null;
  provider: ProviderType;
  headers: Record<string, string>;
}

/** Build fetch headers/URL from global config for AI API calls. */
export function buildAIRequest(config: {
  baseUrl: string;
  apiKey: string | null;
  provider: ProviderType;
}): AIRequestConfig {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (config.apiKey) {
    headers.Authorization = `Bearer ${config.apiKey}`;
  }

  if (config.provider === "openrouter") {
    headers["HTTP-Referer"] = "https://axon-cli.local";
    headers["X-Title"] = "AXON Control Panel";
  }

  return {
    baseUrl: config.baseUrl.replace(/\/$/, ""),
    apiKey: config.apiKey,
    provider: config.provider,
    headers,
  };
}

/** Example helper — all app AI requests should call useConfig().getRequestConfig() first. */
export async function fetchChatCompletion(
  requestConfig: AIRequestConfig,
  body: Record<string, unknown>,
): Promise<Response> {
  const url =
    requestConfig.provider === "ollama"
      ? `${requestConfig.baseUrl}/api/chat`
      : `${requestConfig.baseUrl}/chat/completions`;

  return fetch(url, {
    method: "POST",
    headers: requestConfig.headers,
    body: JSON.stringify(body),
  });
}
