import { NextRequest, NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

const CONFIG_PATH = path.join(process.cwd(), "..", "config.json");

const DEFAULT_CONFIG = {
  openrouter_api_key: "",
  model: "meta-llama/llama-3.1-8b-instruct",
  provider: "openrouter",
};

type SharedConfig = typeof DEFAULT_CONFIG;

async function readConfig(): Promise<SharedConfig> {
  try {
    const raw = await fs.readFile(CONFIG_PATH, "utf-8");
    const parsed = JSON.parse(raw) as Partial<SharedConfig>;
    return { ...DEFAULT_CONFIG, ...parsed };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

async function writeConfig(config: SharedConfig): Promise<void> {
  await fs.writeFile(CONFIG_PATH, JSON.stringify(config, null, 2), "utf-8");
}

export async function GET() {
  const config = await readConfig();

  return NextResponse.json({
    model: config.model,
    provider: config.provider,
    hasApiKey: Boolean(config.openrouter_api_key?.trim()),
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

    const current = await readConfig();
    const next: SharedConfig = {
      ...current,
      openrouter_api_key:
        body.apiKey?.trim() ??
        body.openrouter_api_key?.trim() ??
        current.openrouter_api_key,
      model: body.model?.trim() || current.model,
      provider: body.provider || current.provider,
    };

    await writeConfig(next);

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
