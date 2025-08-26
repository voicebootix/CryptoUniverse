import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp } from 'lucide-react';

const TradingPage: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[400px] text-center space-y-4"
    >
      <TrendingUp className="h-16 w-16 text-primary" />
      <h2 className="text-2xl font-bold">Advanced Trading Interface</h2>
      <p className="text-muted-foreground max-w-md">
        The advanced trading interface with order books, charts, and professional trading tools is coming soon.
      </p>
    </motion.div>
  );
};

export default TradingPage;
