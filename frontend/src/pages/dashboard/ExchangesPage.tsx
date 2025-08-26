import React from 'react';
import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';

const ExchangesPage: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[400px] text-center space-y-4"
    >
      <BarChart3 className="h-16 w-16 text-primary" />
      <h2 className="text-2xl font-bold">Exchange Management</h2>
      <p className="text-muted-foreground max-w-md">
        Connect and manage your exchange API keys, view balances, and configure trading preferences.
      </p>
    </motion.div>
  );
};

export default ExchangesPage;
