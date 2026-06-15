import fs from "fs/promises";
import os from "os";
import path from "path";

export function axonDataDir(): string {
  const base =
    process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming");
  return path.join(base, "AXON");
}

export function axonConfigPath(): string {
  return path.join(axonDataDir(), "config.json");
}

export function axonRuntimePolicyPath(): string {
  return path.join(axonDataDir(), "runtime_policy.json");
}

export function axonSessionsDir(): string {
  return path.join(axonDataDir(), "sessions");
}

export function axonHistoryPath(): string {
  return path.join(os.homedir(), ".axon_history");
}

export async function readAxonConfig(): Promise<Record<string, string>> {
  const defaults = {
    openrouter_api_key: "",
    model: "meta-llama/llama-3.1-8b-instruct",
    provider: "openrouter",
  };
  try {
    const raw = await fs.readFile(axonConfigPath(), "utf-8");
    return { ...defaults, ...(JSON.parse(raw) as Record<string, string>) };
  } catch {
    const legacy = path.join(process.cwd(), "..", "config.json");
    try {
      const raw = await fs.readFile(legacy, "utf-8");
      const parsed = { ...defaults, ...(JSON.parse(raw) as Record<string, string>) };
      await fs.mkdir(axonDataDir(), { recursive: true });
      await fs.writeFile(axonConfigPath(), JSON.stringify(parsed, null, 2), "utf-8");
      return parsed;
    } catch {
      return defaults;
    }
  }
}

export async function writeAxonConfig(config: Record<string, string>): Promise<void> {
  await fs.mkdir(axonDataDir(), { recursive: true });
  await fs.writeFile(axonConfigPath(), JSON.stringify(config, null, 2), "utf-8");
}
