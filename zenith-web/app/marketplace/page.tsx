"use client";

import { motion } from "framer-motion";
import { AppShell } from "@/components/layout/AppShell";
import { ModelMarketplace } from "@/components/marketplace/ModelMarketplace";

export default function MarketplacePage() {
  return (
    <AppShell title="Model Marketplace">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <ModelMarketplace />
      </motion.div>
    </AppShell>
  );
}
