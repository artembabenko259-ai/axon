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

interface ChatContextValue {
  messages: ChatMessage[];
  connected: boolean;
  sendMessage: (content: string) => void;
  clearMessages: () => void;
}

const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8765";

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const seenIds = useRef<Set<string>>(new Set());
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const appendMessage = useCallback((msg: ChatMessage) => {
    if (seenIds.current.has(msg.id)) return;
    seenIds.current.add(msg.id);
    setMessages((prev) => [...prev, msg]);
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as {
          type?: string;
          id?: string;
          role?: ChatRole;
          content?: string;
          source?: "web" | "terminal";
        };

        if (data.type === "connected") {
          appendMessage({
            id: `sys-${Date.now()}`,
            role: "system",
            content: data.content ?? "Bridge connected",
            source: "terminal",
            timestamp: Date.now(),
          });
          return;
        }

        if (data.type === "chat" && data.content) {
          appendMessage({
            id: data.id ?? `${data.source}-${Date.now()}`,
            role: data.role ?? "user",
            content: data.content,
            source: data.source ?? "terminal",
            timestamp: Date.now(),
          });
        }
      } catch {
        /* ignore malformed */
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

  const sendMessage = useCallback((content: string) => {
    const trimmed = content.trim();
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

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "chat",
          id,
          role: "user",
          content: trimmed,
          source: "web",
        }),
      );
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    seenIds.current.clear();
  }, []);

  const value = useMemo(
    () => ({ messages, connected, sendMessage, clearMessages }),
    [messages, connected, sendMessage, clearMessages],
  );

  return (
    <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
