import React from 'react';
import { Outlet, Link, useLocation, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useIsAuthenticated } from '@/store/authStore';
import { TrendingUp, Shield, Zap, Globe, ArrowLeft } from 'lucide-react';

const AuthLayout: React.FC = () => {
  const isAuthenticated = useIsAuthenticated();
  const location = useLocation();

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding and features */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary via-chart-1 to-chart-2 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 dot-pattern opacity-20" />
        
        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center p-12 text-white">
          {/* Logo and brand */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mb-12"
          >
            <Link to="/" className="flex items-center space-x-3 mb-6">
              <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
                <TrendingUp className="h-8 w-8" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">CryptoUniverse</h1>
                <p className="text-sm opacity-90">Enterprise AI Money Manager</p>
              </div>
            </Link>
            
            <h2 className="text-4xl font-bold mb-4 leading-tight">
              Your AI-Powered
              <br />
              <span className="gradient-text">Trading Revolution</span>
            </h2>
            <p className="text-xl opacity-90 max-w-md">
              Experience autonomous trading with enterprise-grade security and real-time market intelligence.
            </p>
          </motion.div>

          {/* Feature highlights */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="space-y-6"
          >
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
                <Zap className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Autonomous Trading</h3>
                <p className="opacity-80">AI-driven strategies that work 24/7</p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
                <Shield className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Enterprise Security</h3>
                <p className="opacity-80">Bank-level encryption and MFA protection</p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
                <Globe className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Multi-Exchange</h3>
                <p className="opacity-80">Trade across Binance, Kraken, KuCoin & more</p>
              </div>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-12 grid grid-cols-3 gap-6"
          >
            <div className="text-center">
              <div className="text-2xl font-bold">$100M+</div>
              <div className="text-sm opacity-80">Assets Under Management</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">99.9%</div>
              <div className="text-sm opacity-80">Uptime Guarantee</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">24/7</div>
              <div className="text-sm opacity-80">AI Trading</div>
            </div>
          </motion.div>
        </div>

        {/* Decorative elements */}
        <div className="absolute -bottom-32 -right-32 w-64 h-64 bg-white/5 rounded-full" />
        <div className="absolute -top-16 -left-16 w-32 h-32 bg-white/5 rounded-full" />
      </div>

      {/* Right side - Auth form */}
      <div className="flex-1 flex flex-col justify-center px-6 py-12 lg:px-12">
        <div className="mx-auto w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden mb-8">
            <Link to="/" className="flex items-center space-x-2">
              <TrendingUp className="h-8 w-8 text-primary" />
              <span className="text-2xl font-bold">CryptoUniverse</span>
            </Link>
          </div>

          {/* Back to home button */}
          <div className="mb-6">
            <Link
              to="/"
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to home
            </Link>
          </div>

          {/* Auth form */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Outlet />
          </motion.div>

          {/* Footer links */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-8 text-center text-sm text-muted-foreground"
          >
            {location.pathname.includes('login') ? (
              <p>
                Don't have an account?{' '}
                <Link to="/auth/register" className="text-primary hover:underline">
                  Sign up
                </Link>
              </p>
            ) : location.pathname.includes('register') ? (
              <p>
                Already have an account?{' '}
                <Link to="/auth/login" className="text-primary hover:underline">
                  Sign in
                </Link>
              </p>
            ) : null}

            <div className="mt-4 flex justify-center space-x-6">
              <Link to="/terms" className="hover:text-foreground transition-colors">
                Terms of Service
              </Link>
              <Link to="/privacy" className="hover:text-foreground transition-colors">
                Privacy Policy
              </Link>
              <Link to="/support" className="hover:text-foreground transition-colors">
                Support
              </Link>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;