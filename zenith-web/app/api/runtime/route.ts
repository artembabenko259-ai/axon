import fs from "fs/promises";
import os from "os";
import path from "path";
import { NextRequest, NextResponse } from "next/server";

function runtimePolicyPath(): string {
  const base =
    process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming");
  return path.join(base, "AXON", "runtime_policy.json");
}

export interface RuntimePolicyPayload {
  autonomy_enabled: boolean;
  autopilot_enabled?: boolean;
  autopilot_enabled_at?: string;
  web_control_enabled: boolean;
  terminal_control_enabled: boolean;
  require_desktop_confirmation: boolean;
  allow_parallel_agents: boolean;
  bridge_auth_enabled: boolean;
  bridge_token: string;
  bridge_pin: string;
  telegram_bot_token?: string;
  telegram_chat_id?: string;
}

const DEFAULT_POLICY: RuntimePolicyPayload = {
  autonomy_enabled: false,
  web_control_enabled: true,
  terminal_control_enabled: true,
  require_desktop_confirmation: true,
  allow_parallel_agents: false,
  bridge_auth_enabled: true,
  bridge_token: "",
  bridge_pin: "",
  telegram_bot_token: "",
  telegram_chat_id: "",
};

async function readPolicy(): Promise<RuntimePolicyPayload> {
  try {
    const raw = await fs.readFile(runtimePolicyPath(), "utf-8");
    return { ...DEFAULT_POLICY, ...(JSON.parse(raw) as RuntimePolicyPayload) };
  } catch {
    return { ...DEFAULT_POLICY };
  }
}

async function writePolicy(policy: RuntimePolicyPayload): Promise<void> {
  const filePath = runtimePolicyPath();
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(policy, null, 2), "utf-8");
}

export async function GET() {
  const policy = await readPolicy();
  return NextResponse.json({
    policy,
    policy_path: runtimePolicyPath(),
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Partial<RuntimePolicyPayload>;
    const current = await readPolicy();
    const next: RuntimePolicyPayload = {
      autonomy_enabled: body.autonomy_enabled ?? current.autonomy_enabled,
      autopilot_enabled:
        body.autopilot_enabled === false
          ? false
          : body.autopilot_enabled ?? current.autopilot_enabled ?? false,
      autopilot_enabled_at:
        body.autopilot_enabled === false ? "" : body.autopilot_enabled_at ?? current.autopilot_enabled_at ?? "",
      web_control_enabled:
        body.web_control_enabled ?? current.web_control_enabled,
      terminal_control_enabled:
        body.terminal_control_enabled ?? current.terminal_control_enabled,
      require_desktop_confirmation:
        body.require_desktop_confirmation ??
        current.require_desktop_confirmation,
      allow_parallel_agents:
        body.allow_parallel_agents ?? current.allow_parallel_agents,
      bridge_auth_enabled:
        body.bridge_auth_enabled ?? current.bridge_auth_enabled,
      bridge_token: body.bridge_token ?? current.bridge_token,
      bridge_pin: body.bridge_pin ?? current.bridge_pin,
      telegram_bot_token: body.telegram_bot_token !== undefined ? body.telegram_bot_token : current.telegram_bot_token,
      telegram_chat_id: body.telegram_chat_id !== undefined ? body.telegram_chat_id : current.telegram_chat_id,
    };

    await writePolicy(next);

    return NextResponse.json({ ok: true, policy: next });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to save runtime policy";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
