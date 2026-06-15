"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Send, Wifi, WifiOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChat } from "@/context/ChatContext";
import { EASE_OUT, TAP_PRESS } from "@/lib/motion";
import { cn } from "@/lib/utils";

const bubbleVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: EASE_OUT },
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
    <div className="flex h-[calc(100dvh-10rem)] min-h-[400px] flex-col overflow-hidden rounded-xl border border-white/[0.06] bg-[#0a0a0a] sm:h-[calc(100dvh-8rem)]">
      <div className="flex items-center justify-between border-b border-white/[0.06] bg-[#111] px-4 py-3 sm:px-5">
        <div>
          <p className="label-caps">Bridge</p>
          <h2 className="text-sm font-medium tracking-tight text-white">Chat</h2>
        </div>
        <div
          className={cn(
            "flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[10px] tabular-nums",
            connected
              ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400"
              : "border-red-500/20 bg-red-500/10 text-red-400",
          )}
        >
          {connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {connected ? "connected" : "reconnecting"}
        </div>
      </div>

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
                    "max-w-[92%] rounded-xl px-4 py-3 sm:max-w-[75%]",
                    isUser && "border border-white/20 bg-white text-black",
                    msg.role === "assistant" && "border border-white/[0.06] bg-[#111]",
                    isSystem && "border border-white/[0.06] bg-transparent px-3 py-1.5 text-[10px] text-[#71717a]",
                  )}
                >
                  {!isSystem && (
                    <p className="mb-1 font-mono text-[9px] uppercase tracking-wider text-[#666]">
                      {msg.source === "terminal" ? "terminal" : "web"} · {msg.role}
                    </p>
                  )}
                  {isUser || isSystem ? (
                    <p
                      className={cn(
                        "text-sm leading-relaxed",
                        isUser ? "text-black" : "text-[#888]",
                      )}
                    >
                      {msg.content}
                    </p>
                  ) : (
                    <div className="prose-vercel prose prose-invert prose-sm max-w-none text-sm leading-relaxed [&_code]:rounded [&_code]:bg-white/10 [&_code]:px-1 [&_p]:my-1">
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

      <form
        onSubmit={handleSubmit}
        className="border-t border-white/[0.08] bg-[#141418] p-3 sm:p-4"
      >
        <div className="flex items-center gap-2 rounded-lg border border-white/[0.08] bg-black px-3 py-2 focus-within:border-white/20">
          <span className="font-mono text-[#71717a]">›</span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message AXON…"
            className="min-w-0 flex-1 bg-transparent py-1.5 text-sm text-white outline-none placeholder:text-[#555]"
          />
          <motion.button
            type="submit"
            disabled={!input.trim() || !connected}
            whileTap={TAP_PRESS}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-white text-black hover:bg-white/90 disabled:opacity-30"
            aria-label="Send message"
          >
            <Send className="h-3.5 w-3.5" />
          </motion.button>
        </div>
      </form>
    </div>
  );
}
