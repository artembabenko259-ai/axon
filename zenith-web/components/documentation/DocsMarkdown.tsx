"use client";

import { useCallback, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

function CodeBlock({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className ?? "");
  const code = String(children).replace(/\n$/, "");
  const isBlock = match || code.includes("\n");

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }, [code]);

  if (!isBlock) {
    return (
      <code
        className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[0.85em] text-cyan-300/90"
        {...props}
      >
        {children}
      </code>
    );
  }

  return (
    <div className="group relative my-4 overflow-hidden rounded-xl border border-white/8 bg-[#0a0a0f]">
      <div className="flex items-center justify-between border-b border-white/6 bg-white/3 px-3 py-1.5">
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
          {match?.[1] ?? "code"}
        </span>
        <button
          type="button"
          onClick={copy}
          className="flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] text-muted transition-colors hover:bg-white/5 hover:text-cyan-400"
          aria-label="Copy code"
        >
          {copied ? (
            <Check className="h-3 w-3 text-emerald-400" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-xs leading-relaxed">
        <code className={cn("font-mono text-foreground/90", className)} {...props}>
          {children}
        </code>
      </pre>
    </div>
  );
}

interface DocsMarkdownProps {
  content: string;
  className?: string;
}

export function DocsMarkdown({ content, className }: DocsMarkdownProps) {
  return (
    <div
      className={cn(
        "docs-prose text-sm leading-relaxed text-muted",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h3 className="mb-3 mt-6 font-display text-base font-semibold text-white first:mt-0">
              {children}
            </h3>
          ),
          h2: ({ children }) => (
            <h4 className="mb-2 mt-5 font-display text-sm font-semibold text-cyan-400">
              {children}
            </h4>
          ),
          h3: ({ children }) => (
            <h5 className="mb-2 mt-4 text-sm font-medium text-foreground">
              {children}
            </h5>
          ),
          p: ({ children }) => (
            <p className="mb-3 last:mb-0">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="mb-4 list-disc space-y-1.5 pl-5">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-4 list-decimal space-y-1.5 pl-5">{children}</ol>
          ),
          li: ({ children }) => <li className="text-muted">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-4 border-l-2 border-cyan-400/50 bg-cyan-500/5 py-2 pl-4 text-sm italic text-foreground/80">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-xl border border-white/8">
              <table className="w-full min-w-[480px] border-collapse text-left text-xs">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-white/5 text-foreground">{children}</thead>
          ),
          th: ({ children }) => (
            <th className="border-b border-white/8 px-3 py-2 font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-white/6 px-3 py-2 text-muted">
              {children}
            </td>
          ),
          tr: ({ children }) => (
            <tr className="transition-colors hover:bg-white/[0.02]">
              {children}
            </tr>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-cyan-400 underline-offset-2 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          ),
          code: CodeBlock,
          pre: ({ children }) => <>{children}</>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
