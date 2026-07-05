import { NextRequest, NextResponse } from "next/server";
import {
  axonConfigPath,
  axonDataDir,
  axonHistoryPath,
  axonSessionsDir,
  readAxonConfig,
  writeAxonConfig,
} from "@/lib/axon-paths";

const DEFAULT_CONFIG = {
  openrouter_api_key: "",
  model: "meta-llama/llama-3.1-8b-instruct",
  provider: "openrouter",
  ollama_base_url: "http://127.0.0.1:11434/v1",
  custom_base_url: "",
  custom_api_key: "",
  antigravity_api_key: "",
};

type SharedConfig = typeof DEFAULT_CONFIG;

function isConfigured(config: any): boolean {
  const provider = (config.provider || "openrouter").toLowerCase();
  if (provider === "antigravity") {
    return Boolean(config.antigravity_api_key?.trim());
  }
  if (provider === "ollama") {
    return Boolean(config.ollama_base_url?.trim());
  }
  if (provider === "custom") {
    return Boolean(
      config.custom_base_url?.trim() && config.custom_api_key?.trim(),
    );
  }
  if (config.custom_providers && config.custom_providers[provider]) {
    const p = config.custom_providers[provider];
    return Boolean(p.base_url?.trim() && p.api_key?.trim());
  }
  return Boolean(config.openrouter_api_key?.trim());
}

export async function GET() {
  const config = (await readAxonConfig()) as SharedConfig;

  return NextResponse.json({
    model: config.model,
    provider: config.provider,
    hasApiKey: isConfigured(config),
    ollamaBaseUrl: config.ollama_base_url,
    customBaseUrl: config.custom_base_url,
    hasOpenRouterKey: Boolean(config.openrouter_api_key?.trim()),
    hasCustomKey: Boolean(config.custom_api_key?.trim()),
    hasAntigravityKey: Boolean(config.antigravity_api_key?.trim()),
    paths: {
      config: axonConfigPath(),
      data_dir: axonDataDir(),
      sessions: axonSessionsDir(),
      history: axonHistoryPath(),
    },
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      apiKey?: string;
      openrouter_api_key?: string;
      custom_api_key?: string;
      antigravity_api_key?: string;
      model?: string;
      provider?: string;
      endpointUrl?: string;
      ollamaBaseUrl?: string;
      customBaseUrl?: string;
    };

    const current = (await readAxonConfig()) as SharedConfig;
    const provider = (body.provider || current.provider || "openrouter").toLowerCase();

    const incomingKey =
      body.apiKey !== undefined
        ? body.apiKey.trim()
        : body.openrouter_api_key?.trim();

    const next: SharedConfig = {
      ...current,
      model: body.model?.trim() || current.model,
      provider,
      ollama_base_url:
        body.ollamaBaseUrl?.trim() ||
        (provider === "ollama" && body.endpointUrl?.trim()
          ? body.endpointUrl.trim()
          : current.ollama_base_url),
      custom_base_url:
        body.customBaseUrl?.trim() ||
        (provider === "custom" && body.endpointUrl?.trim()
          ? body.endpointUrl.trim()
          : current.custom_base_url),
    };

    if (provider === "openrouter" && incomingKey) {
      next.openrouter_api_key = incomingKey;
    } else if (provider === "antigravity") {
      if (incomingKey) {
        next.antigravity_api_key = incomingKey;
      }
      if (body.antigravity_api_key?.trim()) {
        next.antigravity_api_key = body.antigravity_api_key.trim();
      }
    } else if (provider === "custom") {
      if (incomingKey) {
        next.custom_api_key = incomingKey;
      }
      if (body.custom_api_key?.trim()) {
        next.custom_api_key = body.custom_api_key.trim();
      }
    } else if (provider === "openrouter" && body.openrouter_api_key?.trim()) {
      next.openrouter_api_key = body.openrouter_api_key.trim();
    }

    await writeAxonConfig(next);

    return NextResponse.json({
      ok: true,
      model: next.model,
      provider: next.provider,
      hasApiKey: isConfigured(next),
      ollamaBaseUrl: next.ollama_base_url,
      customBaseUrl: next.custom_base_url,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to save configuration";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
