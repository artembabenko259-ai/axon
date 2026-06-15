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
  sendMessage: (text: string) => void;
  sendSetModel: (model: string) => void;
  clearMessages: () => void;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8765";

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

export function BridgeProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const [stats, setStats] = useState<BridgeStats>({ tokens: 0, cost: 0 });
  const [activeModel, setActiveModel] = useState("");
  const wsRef = useRef<WebSocket | null>(null);
  const seenIds = useRef<Set<string>>(new Set());
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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

    ws.onopen = () => setConnected(true);

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
          model?: string;
        };

        if (data.type === "connected") {
          appendMessage({
            id: `sys-${Date.now()}`,
            role: "system",
            content: data.content ?? "Bridge connected",
            source: "terminal",
            timestamp: Date.now(),
          });
          if (data.model) setActiveModel(data.model);
          return;
        }

        if (data.type === "stats") {
          setStats({
            tokens: Number(data.tokens ?? 0),
            cost: Number(data.cost ?? 0),
          });
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
  }, [appendMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

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
      setActiveModel(trimmed);
      sendRaw({ type: "set_model", model: trimmed });
    },
    [sendRaw],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    seenIds.current.clear();
  }, []);

  const value = useMemo(
    () => ({
      messages,
      connected,
      stats,
      activeModel,
      sendMessage,
      sendSetModel,
      clearMessages,
    }),
    [
      messages,
      connected,
      stats,
      activeModel,
      sendMessage,
      sendSetModel,
      clearMessages,
    ],
  );

  return (
    <BridgeContext.Provider value={value}>{children}</BridgeContext.Provider>
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
