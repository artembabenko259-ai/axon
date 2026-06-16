"use client";

import { motion } from "framer-motion";
import Image from "next/image";
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
    <aside
      className="relative z-10 hidden w-[240px] shrink-0 flex-col border-r border-white/[0.08] lg:flex"
      style={{
        background:
          "linear-gradient(180deg, rgba(8,12,24,0.85) 0%, rgba(5,8,19,0.95) 100%)",
        backdropFilter: "blur(8px)",
      }}
    >
      <Link
        href="/"
        className="flex items-center gap-3 px-6 pb-6 pt-7"
      >
        <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04]">
          <Image
            src="/axon-icon.svg"
            alt="AXON"
            width={24}
            height={24}
            className="h-6 w-6"
          />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-bold tracking-[0.22em]">AXON</div>
          <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/45">
            Zenith
          </div>
        </div>
      </Link>

      <nav className="flex flex-1 flex-col gap-1 px-3">
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
                  "group flex items-center gap-3 rounded-xl border px-4 py-2.5 text-sm transition-colors",
                  active
                    ? "border-white/15 bg-white/[0.05] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                    : "border-transparent text-white/65 hover:bg-white/[0.03] hover:text-white",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                <span className="font-medium tracking-tight">{item.label}</span>
              </motion.span>
            </Link>
          );
        })}
      </nav>

      <div className="m-3">
        <BridgeStatus variant="pill" />
      </div>
    </aside>
  );
}
