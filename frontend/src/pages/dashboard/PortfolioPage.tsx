import React from 'react';
import { motion } from 'framer-motion';
import { Wallet } from 'lucide-react';

const PortfolioPage: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[400px] text-center space-y-4"
    >
      <Wallet className="h-16 w-16 text-primary" />
      <h2 className="text-2xl font-bold">Portfolio Analytics</h2>
      <p className="text-muted-foreground max-w-md">
        Detailed portfolio analytics, performance tracking, and risk assessment tools are coming soon.
      </p>
    </motion.div>
  );
};

export default PortfolioPage;
