"use client";

import { motion } from "framer-motion";
import { Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { GlassCard } from "@/components/ui/GlassCard";

interface ToolEvent {
  id: string;
  tool: string;
  status: string;
  detail: string;
  at: number;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8765";

export function ToolTracePanel() {
  const [events, setEvents] = useState<ToolEvent[]>([]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const connect = async () => {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("axon-bridge-token")
          : "";
      ws = new WebSocket(WS_URL);
      ws.onopen = () => {
        if (token) ws?.send(JSON.stringify({ type: "auth", token }));
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data as string) as {
            type?: string;
            tool?: string;
            status?: string;
            detail?: string;
          };
          if (data.type !== "tool_event") return;
          setEvents((prev) =>
            [
              {
                id: `${Date.now()}-${Math.random()}`,
                tool: data.tool ?? "tool",
                status: data.status ?? "event",
                detail: data.detail ?? "",
                at: Date.now(),
              },
              ...prev,
            ].slice(0, 30),
          );
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        timer = setTimeout(connect, 2000);
      };
    };

    void connect();
    return () => {
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return (
    <GlassCard delay={0.2}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Wrench className="h-4 w-4 text-brand" />
          <h2 className="text-sm font-medium text-white">Tool trace</h2>
        </div>
        <span className="font-mono text-[11px] text-white/40">
          {events.length} calls
        </span>
      </div>
      <div className="mt-3 max-h-48 space-y-2 overflow-y-auto text-xs">
        {events.length === 0 ? (
          <p className="text-[#71717a]">Waiting for tool events from CLI…</p>
        ) : (
          events.map((ev) => (
            <motion.div
              key={ev.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded border border-white/[0.06] bg-black/40 px-2 py-1.5 font-mono"
            >
              <span className="text-white">{ev.tool}</span>
              <span className="text-[#71717a]"> · {ev.status}</span>
              {ev.detail ? (
                <p className="mt-1 truncate text-[#a1a1aa]">{ev.detail}</p>
              ) : null}
            </motion.div>
          ))
        )}
      </div>
    </GlassCard>
  );
}
