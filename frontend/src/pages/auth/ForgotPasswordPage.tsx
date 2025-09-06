import React from 'react';
import { motion } from 'framer-motion';
import { Container } from '@/components/ui/container';
import { PasswordResetForm } from '@/components/auth/PasswordResetForm';

const ForgotPasswordPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 text-white">
      <Container>
        <div className="min-h-screen flex flex-col items-center justify-center px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-md"
          >
            <h1 className="text-2xl font-bold text-center mb-6">Reset Password</h1>
            <PasswordResetForm />
          </motion.div>
        </div>
      </Container>
    </div>
  );
};

export default ForgotPasswordPage;