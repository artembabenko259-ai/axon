"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { SkillsMasteryPage } from "@/components/documentation/SkillsMasteryPage";
import { DocsLocaleProvider, useDocsLocale } from "@/context/DocsLocaleContext";
import { getSkillsMasteryLocale } from "@/lib/skills-mastery-locales";

function SkillsMasteryBackLink() {
  const { lang } = useDocsLocale();
  const backLabel = getSkillsMasteryLocale(lang).meta.backToBible;

  return (
    <div className="mb-3 px-1">
      <Link
        href="/docs"
        className="inline-flex items-center gap-1.5 text-xs text-muted transition-colors hover:text-cyan-400"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        {backLabel}
      </Link>
    </div>
  );
}

export default function SkillsMasteryRoute() {
  return (
    <DocsLocaleProvider>
      <AppShell title="Skills Mastery">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.35 }}
          className="flex flex-1 flex-col"
        >
          <SkillsMasteryBackLink />
          <SkillsMasteryPage />
        </motion.div>
      </AppShell>
    </DocsLocaleProvider>
  );
}
