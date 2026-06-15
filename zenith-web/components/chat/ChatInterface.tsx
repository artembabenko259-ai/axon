"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Send, Wifi, WifiOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "@/context/ChatContext";
import { cn } from "@/lib/utils";

const bubbleVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const },
  },
};

export function ChatInterface() {
  const { messages, connected, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <div className="flex h-[calc(100dvh-10rem)] min-h-[400px] flex-col overflow-hidden rounded-2xl border border-white/[0.06] bg-[#0a0a0a] sm:h-[calc(100dvh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] bg-[#111111] px-4 py-3 sm:px-5">
        <div>
          <h2 className="font-display text-sm font-medium text-white">Chat</h2>
          <p className="text-[10px] text-muted">Synced with terminal via WebSocket</p>
        </div>
        <div
          className={cn(
            "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px]",
            connected
              ? "bg-emerald-500/10 text-emerald-400"
              : "bg-red-500/10 text-red-400",
          )}
        >
          {connected ? (
            <Wifi className="h-3 w-3" />
          ) : (
            <WifiOff className="h-3 w-3" />
          )}
          {connected ? "Connected" : "Reconnecting…"}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-3 overflow-y-auto px-3 py-4 logs-scroll sm:px-5"
      >
        <AnimatePresence initial={false}>
          {messages.map((msg) => {
            const isUser = msg.role === "user";
            const isSystem = msg.role === "system";

            return (
              <motion.div
                key={msg.id}
                variants={bubbleVariants}
                initial="hidden"
                animate="visible"
                className={cn(
                  "flex",
                  isUser ? "justify-end" : "justify-start",
                  isSystem && "justify-center",
                )}
              >
                <div
                  className={cn(
                    "max-w-[92%] rounded-2xl px-4 py-3 sm:max-w-[75%]",
                    isUser &&
                      "bg-gradient-to-br from-cyan-500/20 to-indigo-500/20 ring-1 ring-cyan-400/20",
                    msg.role === "assistant" &&
                      "glass backdrop-blur-md ring-1 ring-white/8",
                    isSystem &&
                      "bg-white/3 px-3 py-1.5 text-[10px] text-muted",
                  )}
                >
                  {!isSystem && (
                    <p className="mb-1 text-[9px] uppercase tracking-wider text-muted">
                      {msg.source === "terminal" ? "Terminal" : "Web"} ·{" "}
                      {msg.role}
                    </p>
                  )}
                  {isUser || isSystem ? (
                    <p
                      className={cn(
                        "text-sm leading-relaxed",
                        isUser ? "text-white" : "text-muted",
                      )}
                    >
                      {msg.content}
                    </p>
                  ) : (
                    <div className="prose prose-invert prose-sm max-w-none text-sm leading-relaxed [&_code]:rounded [&_code]:bg-white/10 [&_code]:px-1 [&_p]:my-1">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-white/[0.06] bg-[#111111] p-3 sm:p-4"
      >
        <div className="flex items-center gap-2 rounded-xl border border-white/8 bg-[#0a0a0a] px-3 py-2 ring-1 ring-transparent transition-all focus-within:border-cyan-400/25 focus-within:ring-cyan-400/15">
          <span className="text-cyan-400">❯</span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message AXON…"
            className="min-w-0 flex-1 bg-transparent py-1.5 text-sm text-foreground outline-none placeholder:text-muted/50"
          />
          <motion.button
            type="submit"
            disabled={!input.trim() || !connected}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-400 transition-all hover:bg-cyan-500/30 disabled:opacity-40"
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </motion.button>
        </div>
      </form>
    </div>
  );
}
