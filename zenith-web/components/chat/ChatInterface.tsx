"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Globe, Send, Terminal } from "lucide-react";
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

function SourceBadge({ source }: { source: "web" | "terminal" }) {
  const isWeb = source === "web";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.18em]",
        isWeb
          ? "border-[#5DE4FF]/25 bg-[#5DE4FF]/10 text-[#5DE4FF]"
          : "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
      )}
    >
      {isWeb ? <Globe className="h-2.5 w-2.5" /> : <Terminal className="h-2.5 w-2.5" />}
      {isWeb ? "WEB" : "TERM"}
    </span>
  );
}

export function ChatInterface() {
  const { messages, connected, isStreaming, sendMessage } = useChat();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !connected) return;
    sendMessage(input);
    setInput("");
  };

  const statusLabel = connected ? "connected" : "reconnecting";
  const statusColor = connected ? "text-[#5DE4FF]" : "text-amber-300";

  return (
    <div className="lunar-card flex h-full min-h-[min(640px,calc(100dvh-7rem))] flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-white/60" />
          <span className="label-mono">axon · sync chat</span>
        </div>
        <span className={cn("font-mono text-[11px]", statusColor)}>
          ● bridge {statusLabel}
        </span>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-6 logs-scroll">
        <AnimatePresence initial={false}>
          {messages.length === 0 ? (
            <div className="mt-12 text-center font-mono text-sm text-white/45">
              No messages yet — send one below.
              <br />
              <span className="text-xs text-white/30">
                Anything you type here also flows to the CLI.
              </span>
            </div>
          ) : null}
          {messages.map((msg, index) => {
            const isUser = msg.role === "user";
            const isSystem = msg.role === "system";
            const streaming =
              isStreaming &&
              msg.role === "assistant" &&
              index === messages.length - 1;

            if (isSystem) {
              return (
                <motion.div
                  key={msg.id}
                  variants={bubbleVariants}
                  initial="hidden"
                  animate="visible"
                  className="my-2 self-center font-mono text-[11px] text-white/40"
                >
                  {msg.content}
                </motion.div>
              );
            }

            return (
              <motion.div
                key={msg.id}
                variants={bubbleVariants}
                initial="hidden"
                animate="visible"
                className={cn("flex", isUser ? "justify-end" : "justify-start")}
              >
                <div className={cn("max-w-[78%]", !isUser && "w-full")}>
                  <div
                    className={cn(
                      "mb-1.5 flex items-center gap-2",
                      isUser && "justify-end",
                    )}
                  >
                    <span className="label-mono">{isUser ? "you" : "axon"}</span>
                    <SourceBadge source={msg.source} />
                    {streaming ? (
                      <span className="animate-pulse font-mono text-[10px] text-[#5DE4FF]">
                        streaming…
                      </span>
                    ) : null}
                  </div>
                  <div
                    className={cn(
                      "rounded-2xl border px-4 py-3",
                      isUser
                        ? "rounded-tr-sm border-[#5DE4FF]/25 bg-[#5DE4FF]/12"
                        : "rounded-tl-sm border-white/[0.08] bg-white/[0.025]",
                    )}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-white">
                        {msg.content}
                      </p>
                    ) : (
                      <div className="prose-axon">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content || "_…_"}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex gap-2 border-t border-white/[0.06] p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            connected
              ? "Type a message…"
              : "Bridge offline — messages won't send"
          }
          disabled={!connected}
          className="input-lunar flex-1 disabled:opacity-50"
        />
        <motion.button
          type="submit"
          disabled={!input.trim() || !connected}
          whileTap={TAP_PRESS}
          className="btn-lunar-primary shrink-0 px-4 disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
          Send
        </motion.button>
      </form>
    </div>
  );
}
