"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Menu, MessageSquare, Settings, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { ThemeSwitcher } from "@/components/ui/ThemeSwitcher";
import { ConfigWidget } from "@/components/config/ConfigWidget";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/marketplace", label: "Marketplace", icon: Sparkles },
  { href: "/config", label: "Config", icon: Settings },
];

interface TopNavProps {
  title?: string;
}

export function TopNav({ title = "Control Panel" }: TopNavProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <motion.header
        initial={{ y: -12, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.35 }}
        className="glass-strong sticky top-0 z-40 flex items-center justify-between rounded-2xl px-4 py-3 lg:px-6"
      >
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 lg:hidden">
            <Sparkles className="h-4 w-4 text-cyan-400" />
            <span className="font-display text-xs font-semibold tracking-widest">
              AXON
            </span>
          </Link>
          <div className="hidden h-4 w-px bg-white/10 lg:block" />
          <h1 className="font-display text-sm font-medium text-white/90">
            {title}
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => {
              const active = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href}>
                  <motion.span
                    whileHover={{ y: -1 }}
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs transition-colors",
                      active
                        ? "bg-white/8 text-cyan-400"
                        : "text-muted hover:text-foreground",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {item.label}
                  </motion.span>
                </Link>
              );
            })}
          </nav>

          <ThemeSwitcher />
          <ConfigWidget />

          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className="rounded-lg p-2 text-muted hover:bg-white/5 md:hidden"
            aria-label="Toggle menu"
          >
            {mobileOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </motion.header>

      {mobileOpen && (
        <motion.nav
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="glass-strong mt-2 overflow-hidden rounded-2xl p-2 md:hidden"
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm text-foreground hover:bg-white/5"
              >
                <Icon className="h-4 w-4 text-cyan-400" />
                {item.label}
              </Link>
            );
          })}
        </motion.nav>
      )}
    </>
  );
}
