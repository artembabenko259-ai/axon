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
};

type SharedConfig = typeof DEFAULT_CONFIG;

export async function GET() {
  const config = await readAxonConfig();

  return NextResponse.json({
    model: config.model,
    provider: config.provider,
    hasApiKey: Boolean(config.openrouter_api_key?.trim()),
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
      model?: string;
      provider?: string;
    };

    const incomingKey =
      body.apiKey !== undefined
        ? body.apiKey.trim()
        : body.openrouter_api_key?.trim();

    const current = (await readAxonConfig()) as SharedConfig;
    const next: SharedConfig = {
      ...current,
      openrouter_api_key: incomingKey
        ? incomingKey
        : current.openrouter_api_key,
      model: body.model?.trim() || current.model,
      provider: body.provider || current.provider,
    };

    await writeAxonConfig(next);

    return NextResponse.json({
      ok: true,
      model: next.model,
      hasApiKey: Boolean(next.openrouter_api_key),
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to save configuration";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
