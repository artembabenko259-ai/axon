"use client";

import { Moon, Sun } from "lucide-react";
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

  const isBlack = theme === "black";

  return (
    <button
      type="button"
      onClick={() => setTheme(isBlack ? "base" : "black")}
      className={cn(
        "flex h-8 w-8 items-center justify-center rounded-md border border-white/[0.08] bg-[#0a0a0a] transition-colors",
        "text-[#a1a1aa] hover:border-white/[0.15] hover:text-white",
      )}
      aria-label={isBlack ? "Switch to Base theme" : "Switch to Black theme"}
      title={isBlack ? "Base theme" : "Black theme"}
    >
      {isBlack ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
    </button>
  );
}
