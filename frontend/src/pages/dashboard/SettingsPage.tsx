import React from 'react';
import { motion } from 'framer-motion';
import { Settings } from 'lucide-react';

const SettingsPage: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center min-h-[400px] text-center space-y-4"
    >
      <Settings className="h-16 w-16 text-primary" />
      <h2 className="text-2xl font-bold">User Settings</h2>
      <p className="text-muted-foreground max-w-md">
        Manage your account settings, security preferences, and trading configurations.
      </p>
    </motion.div>
  );
};

export default SettingsPage;
