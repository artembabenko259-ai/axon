"use client";

import { motion } from "framer-motion";
import { AppShell } from "@/components/layout/AppShell";
import { ChatInterface } from "@/components/chat/ChatInterface";

export default function ChatPage() {
  return (
    <AppShell title="Chat">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col"
      >
        <ChatInterface />
      </motion.div>
    </AppShell>
  );
}
