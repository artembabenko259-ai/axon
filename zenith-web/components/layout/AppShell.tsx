import { type ReactNode } from "react";
import { ApiKeySetupBanner } from "@/components/config/ApiKeySetupBanner";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

interface AppShellProps {
  children: ReactNode;
  title?: string;
}

export function AppShell({ children, title }: AppShellProps) {
  return (
    <div className="lunar-bg axon-canvas flex min-h-screen min-h-dvh">
      <Sidebar />
      <div className="relative z-[1] flex min-h-0 min-w-0 flex-1 flex-col">
        <TopNav title={title} />
        <main className="relative flex min-h-0 flex-1 flex-col px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <ApiKeySetupBanner />
          {children}
        </main>
      </div>
    </div>
  );
}
