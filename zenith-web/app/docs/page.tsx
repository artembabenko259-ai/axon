"use client";

import { motion } from "framer-motion";
import { AppShell } from "@/components/layout/AppShell";
import { DocumentationPanel } from "@/components/documentation/DocumentationPanel";
import { DocsLocaleProvider } from "@/context/DocsLocaleContext";

export default function DocsPage() {
  return (
    <DocsLocaleProvider>
      <AppShell title="Documentation">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35 }}
          className="flex flex-1 flex-col"
        >
          <DocumentationPanel />
        </motion.div>
      </AppShell>
    </DocsLocaleProvider>
  );
}
