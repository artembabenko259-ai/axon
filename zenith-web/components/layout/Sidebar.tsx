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
  Terminal,
} from "lucide-react";
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
    <motion.aside
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="glass-strong hidden h-full w-56 shrink-0 flex-col rounded-2xl p-4 lg:flex"
    >
      <Link href="/" className="mb-8 flex items-center gap-2.5 px-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400/20 to-purple-500/20 ring-1 ring-white/10">
          <Sparkles className="h-4 w-4 text-cyan-400" />
        </div>
        <span className="font-display text-sm font-semibold tracking-widest text-white">
          AXON
        </span>
      </Link>

      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(`${item.href}/`));
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <motion.span
                whileHover={{ x: 2 }}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                  active
                    ? "bg-white/8 text-white"
                    : "text-muted hover:bg-white/5 hover:text-foreground",
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4",
                    active ? "text-cyan-400" : "text-muted",
                  )}
                />
                {item.label}
              </motion.span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-xl border border-white/6 bg-white/3 p-3">
        <div className="flex items-center gap-2 text-xs text-muted">
          <Terminal className="h-3.5 w-3.5" />
          CLI v1.0.0
        </div>
        <p className="mt-1 text-[10px] text-muted/70">Connected locally</p>
      </div>
    </motion.aside>
  );
}
