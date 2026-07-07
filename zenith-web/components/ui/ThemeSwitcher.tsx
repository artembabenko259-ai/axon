"use client";

import { Moon, Hexagon, Crosshair } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

export function ThemeSwitcher() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <button
        type="button"
        className="h-8 w-8 rounded-md border border-white/[0.08] bg-[#0a0a0a]"
        aria-label="Toggle theme"
      />
    );
  }

  const themes = ["base", "shard", "dart"] as const;
  const currentTheme = (theme as typeof themes[number]) || "base";

  const toggleTheme = () => {
    const currentIndex = themes.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  const getThemeDetails = (t: typeof themes[number]) => {
    switch (t) {
      case "shard":
        return {
          icon: <Hexagon className="h-3.5 w-3.5 text-[var(--brand)]" />,
          label: "AXON Shard Theme",
          borderClass: "hover:border-[var(--brand)]/45 hover:bg-[var(--brand)]/10",
        };
      case "dart":
        return {
          icon: <Crosshair className="h-3.5 w-3.5 text-[var(--brand)] animate-pulse" />,
          label: "AXON Dart Theme",
          borderClass: "hover:border-[var(--brand)]/45 hover:bg-[var(--brand)]/10",
        };
      case "base":
      default:
        return {
          icon: <Moon className="h-3.5 w-3.5 text-[var(--brand)]" />,
          label: "AXON Zenith Theme",
          borderClass: "hover:border-[var(--brand)]/45 hover:bg-[var(--brand)]/10",
        };
    }
  };

  const details = getThemeDetails(currentTheme);

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-md border border-white/[0.08] bg-black/40 transition-all duration-300",
        "text-white/60 hover:text-white",
        details.borderClass
      )}
      aria-label={details.label}
      title={details.label}
    >
      {details.icon}
    </button>
  );
}
