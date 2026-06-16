"use client";

import { motion } from "framer-motion";
import { RefreshCw, Shield, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { GlassCard } from "@/components/ui/GlassCard";

export interface RuntimePolicy {
  autonomy_enabled: boolean;
  openclaw_enabled?: boolean;
  openclaw_active?: boolean;
  process_elevated?: boolean;
  openclaw_enabled_at?: string;
  web_control_enabled: boolean;
  terminal_control_enabled: boolean;
  require_desktop_confirmation: boolean;
  allow_parallel_agents: boolean;
  bridge_auth_enabled: boolean;
  bridge_token: string;
  bridge_pin: string;
}

const DEFAULT: RuntimePolicy = {
  autonomy_enabled: false,
  web_control_enabled: true,
  terminal_control_enabled: true,
  require_desktop_confirmation: true,
  allow_parallel_agents: false,
  bridge_auth_enabled: true,
  bridge_token: "",
  bridge_pin: "",
};

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 rounded-lg border border-white/[0.06] bg-black/40 px-3 py-3">
      <span>
        <span className="block text-sm text-white">{label}</span>
        <span className="mt-1 block text-xs leading-relaxed text-[#71717a]">
          {hint}
        </span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 accent-white"
      />
    </label>
  );
}

export function RuntimePolicyPanel() {
  const [policy, setPolicy] = useState<RuntimePolicy>(DEFAULT);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch("/api/runtime");
    if (!res.ok) return;
    const data = (await res.json()) as { policy: RuntimePolicy };
    setPolicy({ ...DEFAULT, ...data.policy });
    if (data.policy.bridge_token) {
      localStorage.setItem("axon-bridge-token", data.policy.bridge_token);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/runtime", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(policy),
      });
      const data = (await res.json()) as { policy?: RuntimePolicy };
      if (data.policy) {
        setPolicy(data.policy);
        localStorage.setItem("axon-bridge-token", data.policy.bridge_token);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <GlassCard delay={0.15}>
      <div className="flex items-center gap-2">
        <Shield className="h-4 w-4 text-white" />
        <h2 className="text-sm font-medium tracking-tight text-white">
          Runtime & Security
        </h2>
      </div>
      <p className="mt-1 text-xs text-[#888]">
        Control autonomy, web/terminal access, and bridge pairing. Only edit via
        localhost.
      </p>

      <div className="mt-4 space-y-2">
        <Toggle
          label="Full autonomy"
          hint="Auto-approve write_file and execute_shell without prompts. Use only on trusted machines."
          checked={policy.autonomy_enabled}
          onChange={(v) => setPolicy((p) => ({ ...p, autonomy_enabled: v }))}
        />
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-3">
          <p className="text-sm text-white">OpenClaw</p>
          <p className="mt-1 text-xs leading-relaxed text-[#71717a]">
            Full autonomy when the CLI runs as Administrator. Enable with{" "}
            <span className="font-mono text-[#a1a1aa]">/claw on</span> or{" "}
            <span className="font-mono text-[#a1a1aa]">axon claw on</span> in an
            elevated terminal — not from the browser.
          </p>
          <p className="mt-2 font-mono text-xs text-[#a1a1aa]">
            policy: {policy.openclaw_enabled ? "on" : "off"} · active:{" "}
            {policy.openclaw_active ? "yes" : "no"} · admin:{" "}
            {policy.process_elevated ? "yes" : "no"}
          </p>
        </div>
        <Toggle
          label="Web control"
          hint="Allow commands from the browser dashboard (requires bridge token)."
          checked={policy.web_control_enabled}
          onChange={(v) => setPolicy((p) => ({ ...p, web_control_enabled: v }))}
        />
        <Toggle
          label="Terminal control"
          hint="Allow the AXON CLI prompt to run commands."
          checked={policy.terminal_control_enabled}
          onChange={(v) =>
            setPolicy((p) => ({ ...p, terminal_control_enabled: v }))
          }
        />
        <Toggle
          label="Desktop confirmation for web"
          hint="Dangerous web actions must be approved in the PC terminal (recommended)."
          checked={policy.require_desktop_confirmation}
          onChange={(v) =>
            setPolicy((p) => ({ ...p, require_desktop_confirmation: v }))
          }
        />
        <Toggle
          label="Parallel agents"
          hint="Allow multiple concurrent tasks from web and terminal (up to 3)."
          checked={policy.allow_parallel_agents}
          onChange={(v) =>
            setPolicy((p) => ({ ...p, allow_parallel_agents: v }))
          }
        />
        <Toggle
          label="Bridge token auth"
          hint="Require token on WebSocket connect — blocks unauthorized LAN clients."
          checked={policy.bridge_auth_enabled}
          onChange={(v) =>
            setPolicy((p) => ({ ...p, bridge_auth_enabled: v }))
          }
        />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="label-caps">Bridge PIN</p>
          <p className="mt-1 font-mono text-sm text-white">{policy.bridge_pin || "—"}</p>
        </div>
        <div>
          <p className="label-caps">Bridge token</p>
          <p className="mt-1 truncate font-mono text-[10px] text-[#71717a]">
            {policy.bridge_token || "Start AXON CLI to generate"}
          </p>
        </div>
      </div>

      <motion.button
        type="button"
        whileTap={{ scale: 0.98 }}
        onClick={() => void save()}
        disabled={saving}
        className="btn-vercel-primary mt-5 w-full sm:w-auto"
      >
        {saving ? (
          <>
            <RefreshCw className="h-4 w-4 animate-spin" />
            Saving…
          </>
        ) : saved ? (
          "Saved"
        ) : (
          <>
            <Zap className="h-4 w-4" />
            Save runtime policy
          </>
        )}
      </motion.button>
    </GlassCard>
  );
}
