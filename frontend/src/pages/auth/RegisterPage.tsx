import React from 'react';
import { motion } from 'framer-motion';

const RegisterPage: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="text-center"
    >
      <h2 className="text-2xl font-bold">Register</h2>
      <p className="text-muted-foreground mt-2">
        Registration is currently by invitation only. Please contact your administrator.
      </p>
    </motion.div>
  );
};

export default RegisterPage;
