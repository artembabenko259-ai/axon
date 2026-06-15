"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  formatUptime,
  METRICS_HISTORY_LEN,
  pushHistory,
  sessionElapsedSeconds,
} from "@/lib/metrics";

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  source: "web" | "terminal";
  timestamp: number;
}

export interface BridgeStats {
  tokens: number;
  cost: number;
}

interface BridgeContextValue {
  messages: ChatMessage[];
  connected: boolean;
  stats: BridgeStats;
  activeModel: string;
  uptimeLabel: string;
  tokenSeries: number[];
  uptimeSeries: number[];
  sendMessage: (text: string) => void;
  sendSetModel: (model: string) => void;
  clearMessages: () => void;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8765";
const SESSION_START_KEY = "axon-cli-session-start";
const BRIDGE_TOKEN_KEY = "axon-bridge-token";
const CHAT_MESSAGES_KEY = "axon-web-chat";

async function resolveBridgeToken(): Promise<string> {
  if (typeof window === "undefined") return "";
  const cached = localStorage.getItem(BRIDGE_TOKEN_KEY);
  if (cached) return cached;
  try {
    const res = await fetch("/api/runtime");
    if (!res.ok) return "";
    const data = (await res.json()) as { policy?: { bridge_token?: string } };
    const token = data.policy?.bridge_token?.trim() ?? "";
    if (token) localStorage.setItem(BRIDGE_TOKEN_KEY, token);
    return token;
  } catch {
    return "";
  }
}

const BridgeContext = createContext<BridgeContextValue | null>(null);

function normalizeRole(role?: string): ChatRole {
  if (role === "user") return "user";
  if (role === "system") return "system";
  return "assistant";
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}k`;
  return String(tokens);
}

export function formatBridgeStats(stats: BridgeStats): {
  tokensLabel: string;
  costLabel: string;
} {
  return {
    tokensLabel: formatTokens(stats.tokens),
    costLabel: `$${stats.cost.toFixed(4)}`,
  };
}

function toSessionStartMs(value: unknown): number | null {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n < 1e12 ? Math.round(n * 1000) : Math.round(n);
}

function readStoredSessionStart(): number | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(SESSION_START_KEY);
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

function storeSessionStart(ms: number) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(SESSION_START_KEY, String(ms));
}

export function BridgeProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState<BridgeStats>({ tokens: 0, cost: 0 });
  const [activeModel, setActiveModel] = useState("");
  const [sessionStartedAtMs, setSessionStartedAtMs] = useState<number | null>(
    null,
  );
  const [uptimeLabel, setUptimeLabel] = useState("00:00:00");
  const [tokenSeries, setTokenSeries] = useState<number[]>([]);
  const [uptimeSeries, setUptimeSeries] = useState<number[]>([]);
  const [pendingApproval, setPendingApproval] = useState<{
    id: string;
    tool: string;
    detail: string;
  } | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const seenIds = useRef<Set<string>>(new Set());
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionStartedAtRef = useRef<number | null>(null);
  const statsRef = useRef(stats);

  useEffect(() => {
    statsRef.current = stats;
  }, [stats]);

  const applySessionStart = useCallback((ms: number | null) => {
    if (!ms) return;
    const stored = readStoredSessionStart();
    const next = stored ? Math.min(stored, ms) : ms;
    sessionStartedAtRef.current = next;
    setSessionStartedAtMs(next);
    storeSessionStart(next);
  }, []);

  const sampleMetrics = useCallback(() => {
    const start = sessionStartedAtRef.current;
    if (!start) return;

    const elapsed = sessionElapsedSeconds(start);
    const tokens = statsRef.current.tokens;

    setUptimeSeries((prev) => pushHistory(prev, elapsed, METRICS_HISTORY_LEN));
    setTokenSeries((prev) => pushHistory(prev, tokens, METRICS_HISTORY_LEN));
  }, []);

  const applyStats = useCallback(
    (tokens: number, cost: number, sessionStart?: unknown) => {
      setStats({ tokens, cost });
      const startMs = toSessionStartMs(sessionStart);
      if (startMs) applySessionStart(startMs);
    },
    [applySessionStart],
  );

  const appendMessage = useCallback((msg: ChatMessage) => {
    if (seenIds.current.has(msg.id)) return;
    seenIds.current.add(msg.id);
    setMessages((prev) => [...prev, msg]);
  }, []);

  const sendRaw = useCallback((payload: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      void (async () => {
        const token = await resolveBridgeToken();
        if (token) {
          ws.send(JSON.stringify({ type: "auth", token }));
        }
      })();
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, 2000);
    };

    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as {
          type?: string;
          id?: string;
          role?: string;
          content?: string;
          text?: string;
          source?: "web" | "terminal";
          tokens?: number;
          cost?: number;
          session_started_at?: number;
          model?: string;
          tool?: string;
          detail?: string;
          delta?: string;
          status?: string;
          policy?: { bridge_token?: string };
        };

        if (data.type === "auth_required") {
          setConnected(false);
          return;
        }

        if (data.type === "auth_failed") {
          setConnected(false);
          appendMessage({
            id: `auth-fail-${Date.now()}`,
            role: "system",
            content:
              data.content ??
              "Bridge auth failed — open /config and save runtime policy.",
            source: "terminal",
            timestamp: Date.now(),
          });
          return;
        }

        if (data.type === "connected") {
          setConnected(true);
          if (data.policy?.bridge_token) {
            localStorage.setItem(BRIDGE_TOKEN_KEY, data.policy.bridge_token);
          }
          applyStats(
            Number(data.tokens ?? 0),
            Number(data.cost ?? 0),
            data.session_started_at,
          );
          appendMessage({
            id: `sys-${Date.now()}`,
            role: "system",
            content: data.content ?? "Bridge connected",
            source: "terminal",
            timestamp: Date.now(),
          });
          return;
        }

        if (data.type === "approval_request") {
          const approvalId = data.id;
          if (approvalId) {
            setPendingApproval({
              id: approvalId,
              tool: data.tool ?? "tool",
              detail: data.detail ?? "",
            });
          } else {
            appendMessage({
              id: `approval-${Date.now()}`,
              role: "system",
              content: `⚠ Confirm in AXON terminal: ${data.tool ?? "tool"} — ${data.detail ?? ""}`,
              source: "terminal",
              timestamp: Date.now(),
            });
          }
          return;
        }

        if (data.type === "error") {
          appendMessage({
            id: `err-${Date.now()}`,
            role: "system",
            content: data.content ?? "Bridge error",
            source: "terminal",
            timestamp: Date.now(),
          });
          return;
        }

        if (data.type === "stream_start") {
          const id = data.id ?? `stream-${Date.now()}`;
          seenIds.current.add(id);
          setMessages((prev) => [
            ...prev,
            {
              id,
              role: "assistant",
              content: "",
              source: data.source ?? "terminal",
              timestamp: Date.now(),
            },
          ]);
          return;
        }

        if (data.type === "stream_delta" && data.id) {
          const delta = data.delta ?? "";
          setMessages((prev) =>
            prev.map((m) =>
              m.id === data.id ? { ...m, content: m.content + delta } : m,
            ),
          );
          return;
        }

        if (data.type === "stream_end" && data.id) {
          const text = data.text ?? "";
          setMessages((prev) =>
            prev.map((m) =>
              m.id === data.id ? { ...m, content: text || m.content } : m,
            ),
          );
          return;
        }

        if (data.type === "tool_event") {
          appendMessage({
            id: `tool-${Date.now()}`,
            role: "system",
            content: `[${data.status ?? "event"}] ${data.tool ?? "tool"}${data.detail ? ` — ${data.detail}` : ""}`,
            source: "terminal",
            timestamp: Date.now(),
          });
          return;
        }

        if (data.type === "stats") {
          applyStats(
            Number(data.tokens ?? 0),
            Number(data.cost ?? 0),
            data.session_started_at,
          );
          return;
        }

        if (data.type === "model" && data.model) {
          setActiveModel(data.model);
          return;
        }

        if (data.type === "chat") {
          const content = (data.text ?? data.content ?? "").trim();
          if (!content || content === "Thinking...") return;

          appendMessage({
            id: data.id ?? `${data.source ?? "terminal"}-${Date.now()}`,
            role: normalizeRole(data.role),
            content,
            source: data.source ?? "terminal",
            timestamp: Date.now(),
          });
        }
      } catch {
        /* ignore malformed payloads */
      }
    };
  }, [appendMessage, applyStats]);

  useEffect(() => {
    const stored = readStoredSessionStart();
    if (stored) {
      sessionStartedAtRef.current = stored;
      setSessionStartedAtMs(stored);
    }
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  useEffect(() => {
    if (!sessionStartedAtMs) return;

    const tick = () => {
      setUptimeLabel(formatUptime(sessionElapsedSeconds(sessionStartedAtMs)));
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [sessionStartedAtMs]);

  useEffect(() => {
    if (!sessionStartedAtMs) return;

    sampleMetrics();
    const interval = setInterval(sampleMetrics, 10_000);
    return () => clearInterval(interval);
  }, [sessionStartedAtMs, sampleMetrics]);

  useEffect(() => {
    if (!sessionStartedAtMs) return;
    sampleMetrics();
  }, [stats.tokens, sessionStartedAtMs, sampleMetrics]);

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      const id = `web-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const msg: ChatMessage = {
        id,
        role: "user",
        content: trimmed,
        source: "web",
        timestamp: Date.now(),
      };

      seenIds.current.add(id);
      setMessages((prev) => [...prev, msg]);
      sendRaw({ type: "chat", text: trimmed });
    },
    [sendRaw],
  );

  const sendSetModel = useCallback(
    (model: string) => {
      const trimmed = model.trim();
      if (!trimmed) return;
      sendRaw({ type: "set_model", model: trimmed });
    },
    [sendRaw],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    seenIds.current.clear();
  }, []);

  const respondApproval = useCallback(
    (decision: "once" | "session" | "deny") => {
      if (!pendingApproval) return;
      sendRaw({
        type: "approval_response",
        id: pendingApproval.id,
        decision,
      });
      setPendingApproval(null);
    },
    [pendingApproval, sendRaw],
  );

  useEffect(() => {
    const raw = sessionStorage.getItem(CHAT_MESSAGES_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as ChatMessage[];
      if (Array.isArray(parsed)) setMessages(parsed);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    sessionStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(messages));
  }, [messages]);

  const value = useMemo(
    () => ({
      messages,
      connected,
      stats,
      activeModel,
      uptimeLabel,
      tokenSeries,
      uptimeSeries,
      sendMessage,
      sendSetModel,
      clearMessages,
    }),
    [
      messages,
      connected,
      stats,
      activeModel,
      uptimeLabel,
      tokenSeries,
      uptimeSeries,
      sendMessage,
      sendSetModel,
      clearMessages,
    ],
  );

  return (
    <BridgeContext.Provider value={value}>
      {children}
      {pendingApproval ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl border border-white/10 bg-[#0a0a0a] p-5 shadow-2xl">
            <h3 className="text-sm font-semibold text-white">Approve tool</h3>
            <p className="mt-2 text-xs text-[#a1a1aa]">
              {pendingApproval.tool} — {pendingApproval.detail}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-vercel-primary text-xs"
                onClick={() => respondApproval("once")}
              >
                Allow once
              </button>
              <button
                type="button"
                className="rounded-full border border-white/20 px-3 py-1.5 text-xs text-white"
                onClick={() => respondApproval("session")}
              >
                Session
              </button>
              <button
                type="button"
                className="rounded-full border border-red-500/40 px-3 py-1.5 text-xs text-red-300"
                onClick={() => respondApproval("deny")}
              >
                Deny
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </BridgeContext.Provider>
  );
}

export function useWebSocket() {
  const ctx = useContext(BridgeContext);
  if (!ctx) {
    throw new Error("useWebSocket must be used within BridgeProvider");
  }
  return ctx;
}

export const useChat = useWebSocket;
export const ChatProvider = BridgeProvider;
