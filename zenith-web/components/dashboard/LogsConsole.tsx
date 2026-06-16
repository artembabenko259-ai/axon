"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Terminal } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { EASE_OUT } from "@/lib/motion";
import { useConfig } from "@/context/ConfigContext";

interface LogEntry {
  id: string;
  timestamp: string;
  level: "info" | "success" | "warn" | "system";
  message: string;
}

const initialLogs: LogEntry[] = [
  {
    id: "1",
    timestamp: "02:31:04",
    level: "system",
    message: "AXON CLI initialized — v1.0.0",
  },
  {
    id: "2",
    timestamp: "02:31:05",
    level: "info",
    message: "Model loaded: meta-llama/llama-3.1-8b-instruct",
  },
  {
    id: "3",
    timestamp: "02:31:05",
    level: "success",
    message: "Markdown skills loaded from .axon/skills/",
  },
  {
    id: "4",
    timestamp: "02:31:06",
    level: "info",
    message: "OpenRouter client connected",
  },
  {
    id: "5",
    timestamp: "02:31:06",
    level: "system",
    message: "Status: Ready — awaiting input",
  },
];

const levelColors = {
  info: "text-zinc-400",
  success: "text-emerald-400",
  warn: "text-amber-400",
  system: "text-zinc-500",
};

const liveMessages = [
  "Heartbeat ping — agent healthy",
  "Context window: 12 messages",
  "Tool schema synced (2 skills)",
  "Streaming buffer ready",
];

export function LogsConsole() {
  const { config, getRequestConfig } = useConfig();
  const [logs, setLogs] = useState<LogEntry[]>(initialLogs);
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevConnected = useRef(config.isConnected);

  useEffect(() => {
    if (config.isConnected && !prevConnected.current) {
      const req = getRequestConfig();
      setLogs((prev) => [
        ...prev,
        {
          id: `connect-${Date.now()}`,
          timestamp: new Date().toTimeString().slice(0, 8),
          level: "success",
          message: `Connected via ${config.provider} → ${req.baseUrl}`,
        },
      ]);
    }
    prevConnected.current = config.isConnected;
  }, [config.isConnected, config.provider, getRequestConfig]);

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const ts = now.toTimeString().slice(0, 8);
      const msg =
        liveMessages[Math.floor(Math.random() * liveMessages.length)];
      setLogs((prev) => [
        ...prev.slice(-20),
        {
          id: `${Date.now()}`,
          timestamp: ts,
          level: "info",
          message: msg,
        },
      ]);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <GlassCard hover={false} className="flex flex-col overflow-hidden !p-0">
      <div className="flex items-center gap-2 border-b border-white/5 px-4 py-3">
        <Terminal className="h-4 w-4 text-zinc-500" strokeWidth={1.75} />
        <span className="label-caps">Live logs</span>
        <motion.span
          animate={{ opacity: [1, 0.4, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="ml-auto flex items-center gap-1.5 font-mono text-[10px] font-medium uppercase tracking-wider text-[#5DE4FF]"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-[#5DE4FF] glow-cyan" />
          LIVE
        </motion.span>
      </div>

      <div
        ref={scrollRef}
        className="logs-scroll h-48 overflow-y-auto px-4 py-3 font-mono text-xs sm:h-56"
      >
        <AnimatePresence initial={false}>
          {logs.map((log) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: EASE_OUT }}
              className="flex gap-3 border-b border-white/[0.03] py-1.5 leading-relaxed last:border-0"
            >
              <span className="shrink-0 text-zinc-600">{log.timestamp}</span>
              <span
                className={`shrink-0 uppercase ${levelColors[log.level]}`}
              >
                [{log.level}]
              </span>
              <span className="text-zinc-400">{log.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </GlassCard>
  );
}
