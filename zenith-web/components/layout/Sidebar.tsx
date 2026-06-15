"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  LayoutDashboard,
  MessageSquare,
  Settings,
  Sparkles,
} from "lucide-react";
import { BridgeStatus } from "@/components/ui/BridgeStatus";
import { TAP_PRESS } from "@/lib/motion";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/docs", label: "Documentation", icon: BookOpen },
  { href: "/marketplace", label: "Marketplace", icon: Sparkles },
  { href: "/config", label: "Config", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-[240px] shrink-0 flex-col border-r border-white/[0.06] bg-black lg:flex">
      <div className="flex h-14 items-center gap-2.5 border-b border-white/[0.06] px-5">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-5 w-5 items-center justify-center rounded bg-white">
            <span className="text-[9px] font-bold text-black">A</span>
          </div>
          <span className="text-sm font-semibold tracking-tight text-white">AXON</span>
        </Link>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 p-3">
        {navItems.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(`${item.href}/`));
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <motion.span
                whileTap={TAP_PRESS}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
                  active
                    ? "bg-white text-black"
                    : "text-[#a1a1aa] hover:bg-white/[0.05] hover:text-white",
                )}
              >
                <Icon className="h-4 w-4" strokeWidth={1.75} />
                {item.label}
              </motion.span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/[0.06] p-4">
        <BridgeStatus />
      </div>
    </aside>
  );
}
