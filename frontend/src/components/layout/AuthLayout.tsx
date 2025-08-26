import React from 'react';
import { Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import { TrendingUp, Shield, Zap, Target, BarChart3, Bot } from 'lucide-react';

const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left side - Auth Form */}
      <div className="flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-20 xl:px-24">
        <div className="mx-auto w-full max-w-sm lg:w-96">
          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center space-x-3 mb-8"
          >
            <div className="p-2 bg-primary/10 rounded-lg">
              <TrendingUp className="h-8 w-8 text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold">CryptoUniverse</h2>
              <p className="text-sm text-muted-foreground">AI Money Manager</p>
            </div>
          </motion.div>

          {/* Auth Form */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Outlet />
          </motion.div>

          {/* Footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mt-8 text-center"
          >
            <p className="text-xs text-muted-foreground">
              © 2024 CryptoUniverse Enterprise. All rights reserved.
            </p>
          </motion.div>
        </div>
      </div>

      {/* Right side - Marketing/Features */}
      <div className="hidden lg:block relative bg-gradient-to-br from-primary/5 to-chart-1/5 border-l border-border">
        <div className="absolute inset-0 bg-grid-pattern opacity-5" />
        
        <div className="relative flex flex-col justify-center h-full p-12">
          {/* Hero Section */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            <div className="space-y-2">
              <h1 className="text-4xl font-bold tracking-tight">
                Enterprise AI Trading Platform
              </h1>
              <p className="text-xl text-muted-foreground">
                Automated cryptocurrency trading powered by advanced AI algorithms
              </p>
            </div>

            {/* Feature highlights */}
            <div className="space-y-4">
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
                className="flex items-center space-x-3"
              >
                <div className="p-2 bg-profit/10 rounded-lg">
                  <Bot className="h-6 w-6 text-profit" />
                </div>
                <div>
                  <h3 className="font-semibold">AI-Powered Trading</h3>
                  <p className="text-sm text-muted-foreground">
                    Multi-model consensus with GPT-4, Claude, and Gemini
                  </p>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 }}
                className="flex items-center space-x-3"
              >
                <div className="p-2 bg-chart-1/10 rounded-lg">
                  <Shield className="h-6 w-6 text-chart-1" />
                </div>
                <div>
                  <h3 className="font-semibold">Enterprise Security</h3>
                  <p className="text-sm text-muted-foreground">
                    Bank-level encryption with multi-factor authentication
                  </p>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
                className="flex items-center space-x-3"
              >
                <div className="p-2 bg-warning/10 rounded-lg">
                  <Zap className="h-6 w-6 text-warning" />
                </div>
                <div>
                  <h3 className="font-semibold">Real-Time Execution</h3>
                  <p className="text-sm text-muted-foreground">
                    Lightning-fast trades across multiple exchanges
                  </p>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 }}
                className="flex items-center space-x-3"
              >
                <div className="p-2 bg-chart-2/10 rounded-lg">
                  <Target className="h-6 w-6 text-chart-2" />
                </div>
                <div>
                  <h3 className="font-semibold">Risk Management</h3>
                  <p className="text-sm text-muted-foreground">
                    Advanced portfolio protection and position sizing
                  </p>
                </div>
              </motion.div>
            </div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="grid grid-cols-3 gap-6 pt-8 border-t border-border/50"
            >
              <div className="text-center">
                <div className="text-2xl font-bold text-profit">99.9%</div>
                <div className="text-xs text-muted-foreground">Uptime</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-chart-1">$100M+</div>
                <div className="text-xs text-muted-foreground">Assets Under Management</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-chart-2">24/7</div>
                <div className="text-xs text-muted-foreground">Trading</div>
              </div>
            </motion.div>

            {/* Testimonial */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
              className="pt-8 border-t border-border/50"
            >
              <blockquote className="text-sm italic text-muted-foreground">
                "CryptoUniverse's AI trading platform has revolutionized our investment strategy. 
                The autonomous features and risk management are unparalleled."
              </blockquote>
              <cite className="text-xs font-medium mt-2 block">
                — Sarah Chen, Portfolio Manager at Hedge Fund Alpha
              </cite>
            </motion.div>
          </motion.div>

          {/* Decorative elements */}
          <div className="absolute top-10 right-10 opacity-10">
            <BarChart3 className="h-32 w-32" />
          </div>
          <div className="absolute bottom-10 left-10 opacity-10">
            <TrendingUp className="h-24 w-24" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;