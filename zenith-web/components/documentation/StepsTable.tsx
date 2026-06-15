"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface StepsTableProps {
  title?: string;
  headers: { step: string; what: string; who: string };
  rows: { step: string; what: string; who: string }[];
}

export function StepsTable({ title, headers, rows }: StepsTableProps) {
  return (
    <div className="my-6">
      {title && (
        <h5 className="mb-3 text-xs font-semibold uppercase tracking-wider text-cyan-400/80">
          {title}
        </h5>
      )}
      <div className="overflow-x-auto rounded-xl border border-white/8">
        <table className="w-full min-w-[520px] border-collapse text-left text-xs">
          <thead>
            <tr className="bg-white/5 text-foreground">
              <th className="border-b border-white/8 px-3 py-2.5 font-semibold">
                {headers.step}
              </th>
              <th className="border-b border-white/8 px-3 py-2.5 font-semibold">
                {headers.what}
              </th>
              <th className="border-b border-white/8 px-3 py-2.5 font-semibold">
                {headers.who}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                className="border-b border-white/5 transition-colors hover:bg-cyan-500/[0.03]"
              >
                <td className="px-3 py-2.5 font-mono text-cyan-300/90">
                  {row.step}
                </td>
                <td className="px-3 py-2.5 text-muted">{row.what}</td>
                <td className="px-3 py-2.5 text-muted/80">{row.who}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
