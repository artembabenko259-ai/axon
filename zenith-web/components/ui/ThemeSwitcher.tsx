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
        className="h-8 w-8 rounded-lg border border-white/8 bg-white/4"
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
        "flex h-8 w-8 items-center justify-center rounded-lg border transition-all duration-300",
        "border-white/8 bg-white/4 backdrop-blur-md",
        "hover:border-white/14 hover:bg-white/8",
        isBlack && "border-white/12 bg-white/6",
      )}
      aria-label={isBlack ? "Switch to Base theme" : "Switch to Black theme"}
      title={isBlack ? "Base theme" : "Black theme"}
    >
      {isBlack ? (
        <Sun className="h-3.5 w-3.5 text-amber-300/90" />
      ) : (
        <Moon className="h-3.5 w-3.5 text-muted" />
      )}
    </button>
  );
}
