import { type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

interface AppShellProps {
  children: ReactNode;
  title?: string;
}

export function AppShell({ children, title }: AppShellProps) {
  return (
    <div className="flex min-h-screen gap-4 p-4 lg:p-6">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <TopNav title={title} />
        <main className="flex flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}
