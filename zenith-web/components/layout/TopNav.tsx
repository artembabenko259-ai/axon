"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, LayoutDashboard, Menu, MessageSquare, Settings, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { BridgeStatus } from "@/components/ui/BridgeStatus";
import { ThemeSwitcher } from "@/components/ui/ThemeSwitcher";
import { ConfigWidget } from "@/components/config/ConfigWidget";
import { TAP_PRESS } from "@/lib/motion";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/docs", label: "Documentation", icon: BookOpen },
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
      <header className="glass flex h-14 items-center justify-between px-4 sm:px-6 lg:px-8">
        <h1 className="text-sm font-semibold tracking-tight text-white">{title}</h1>
        <div className="flex items-center gap-2">
          <BridgeStatus variant="compact" className="hidden sm:flex" />
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== "/" && pathname.startsWith(`${item.href}/`));
              return (
                <Link key={item.href} href={item.href}>
                  <span
                    className={cn(
                      "rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                      active
                        ? "nav-link-active text-[#fafafa]"
                        : "text-[#71717a] hover:text-[#a1a1aa]",
                    )}
                  >
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </nav>
          <ThemeSwitcher />
          <ConfigWidget />
          <motion.button
            type="button"
            whileTap={TAP_PRESS}
            onClick={() => setMobileOpen(!mobileOpen)}
            className="rounded-lg p-2 text-[#a1a1aa] hover:bg-white/[0.05] md:hidden"
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </motion.button>
        </div>
      </header>

      {mobileOpen && (
        <nav className="border-b border-white/[0.06] bg-black p-2 md:hidden">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className="block rounded-lg px-3 py-2.5 text-sm text-[#a1a1aa] hover:bg-white/[0.05] hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </>
  );
}
