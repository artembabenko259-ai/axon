"use client";

import { ConfigProvider } from "@/context/ConfigContext";
import { ChatProvider } from "@/context/ChatContext";
import { ModelProvider } from "@/context/ModelContext";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import { type ReactNode } from "react";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <ConfigProvider>
        <ModelProvider>
          <ChatProvider>{children}</ChatProvider>
        </ModelProvider>
      </ConfigProvider>
    </ThemeProvider>
  );
}
