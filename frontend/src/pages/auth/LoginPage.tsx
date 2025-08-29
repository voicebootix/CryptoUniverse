import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Eye, 
  EyeOff, 
  Loader2, 
  Shield, 
  AlertCircle, 
  TrendingUp, 
  Bot, 
  Zap, 
  Globe, 
  Lock, 
  CheckCircle,
  ArrowRight,
  Sparkles,
  BarChart3,
  Crown,
  Star,
  Award,
  Target
} from 'lucide-react';
import { useAuthStore, useMfaRequired, useAuthError, useAuthLoading } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient } from '@/lib/api/client';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  mfa_code: z.string().optional(),
  remember_me: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

const LoginPage: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [showMfaInput, setShowMfaInput] = useState(false);
  const navigate = useNavigate();
  
  const login = useAuthStore((state) => state.login);
  const clearError = useAuthStore((state) => state.clearError);
  const mfaRequired = useMfaRequired();
  const error = useAuthError();
  const isLoading = useAuthLoading();

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      remember_me: false,
    },
  });

  const email = watch('email');
  const password = watch('password');

  const handleGoogleLogin = async () => {
    try {
      const response = await apiClient.post('/auth/oauth/url', {
        provider: 'google',
        redirect_url: window.location.origin + '/auth/callback'
      });

      if (response.status !== 200) {
        throw new Error('Failed to get OAuth URL');
      }

      const data = response.data;
      
      // Redirect to Google OAuth
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('Google login error:', error);
      // You might want to set an error state here
    }
  };

  React.useEffect(() => {
    if (mfaRequired) {
      setShowMfaInput(true);
    }
  }, [mfaRequired]);

  React.useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        clearError();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data);
      if (!mfaRequired) {
        navigate('/dashboard');
      }
    } catch (err) {
      // Error is handled by the store
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="min-h-screen flex">
        {/* Left Side - Branding & Features */}
        <div className="hidden lg:flex lg:flex-col lg:justify-center flex-1 relative overflow-hidden">
          {/* Background Effects */}
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 via-purple-600 to-violet-700" />
          <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/30 via-purple-500/20 to-pink-500/30" />
          <div className="absolute top-10 left-10 w-72 h-72 bg-gradient-to-r from-blue-400/40 to-cyan-400/40 rounded-full blur-3xl animate-pulse" />
          <div className="absolute bottom-10 right-10 w-80 h-80 bg-gradient-to-l from-purple-400/40 to-pink-400/40 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-gradient-to-r from-violet-400/20 to-purple-400/20 rounded-full blur-3xl" />
          
          {/* Content Container */}
          <div className="relative z-10 h-full flex flex-col justify-center px-6 py-8">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="w-full"
            >
              {/* Logo & Title */}
              <div className="mb-8">
                <div className="flex items-center mb-4">
                  <div className="w-14 h-14 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mr-4">
                    <TrendingUp className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h1 className="text-3xl font-bold text-white">CryptoUniverse</h1>
                    <p className="text-blue-200 text-base">Enterprise AI Trading Platform v2.0.1</p>
                  </div>
                </div>
                <p className="text-lg text-gray-300 leading-relaxed">
                  Automated cryptocurrency trading powered by advanced AI algorithms
                </p>
              </div>

              {/* Feature Highlights */}
              <div className="space-y-4">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.6 }}
                  className="flex items-center space-x-3 p-3 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20"
                >
                  <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-sm">AI-Powered Trading</h3>
                    <p className="text-gray-300 text-xs">Multi-model consensus with GPT-4, Claude, and Gemini</p>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5, duration: 0.6 }}
                  className="flex items-center space-x-3 p-3 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20"
                >
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-lg flex items-center justify-center">
                    <Globe className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-sm">Multi-Exchange Support</h3>
                    <p className="text-gray-300 text-xs">Trade across 8+ major exchanges with arbitrage scanning</p>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7, duration: 0.6 }}
                  className="flex items-center space-x-3 p-3 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20"
                >
                  <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-sm">Advanced Analytics</h3>
                    <p className="text-gray-300 text-xs">Institutional-grade risk management and reporting</p>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.9, duration: 0.6 }}
                  className="flex items-center space-x-3 p-3 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20"
                >
                  <div className="w-10 h-10 bg-gradient-to-r from-orange-500 to-red-600 rounded-lg flex items-center justify-center">
                    <Crown className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-sm">25+ Trading Strategies</h3>
                    <p className="text-gray-300 text-xs">Professional strategies from DeFi to arbitrage</p>
                  </div>
                </motion.div>
              </div>

              {/* Stats */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.1, duration: 0.6 }}
                className="mt-6 grid grid-cols-3 gap-4"
              >
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">$2.8M+</div>
                  <div className="text-sm text-gray-400">Assets Under Management</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">73.2%</div>
                  <div className="text-sm text-gray-400">Win Rate</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">2.87</div>
                  <div className="text-sm text-gray-400">Sharpe Ratio</div>
                </div>
              </motion.div>

              {/* Trust Indicators */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.3, duration: 0.6 }}
                className="mt-6 p-4 bg-white/10 backdrop-blur-sm rounded-lg border border-white/20"
              >
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-white font-semibold">Protected by enterprise-grade security</h4>
                  <Shield className="w-6 h-6 text-green-400" />
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-300">
                  <div className="flex items-center space-x-1">
                    <Lock className="w-4 h-4" />
                    <span>256-bit SSL</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <CheckCircle className="w-4 h-4" />
                    <span>SOC 2 Compliant</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Shield className="w-4 h-4" />
                    <span>Bank-level Security</span>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          </div>
        </div>

        {/* Right Side - Login Form */}
        <div className="flex flex-col justify-center flex-1 px-4 py-12 sm:px-6 lg:px-8 xl:px-12">
          <div className="w-full max-w-sm mx-auto lg:w-96">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="bg-white shadow-xl rounded-2xl p-8">
                {/* Mobile Header */}
                <div className="text-center mb-8 lg:hidden">
                  <div className="flex items-center justify-center mb-6">
                    <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center mr-3">
                      <TrendingUp className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h1 className="text-2xl font-bold text-gray-900">CryptoUniverse</h1>
                      <p className="text-sm text-gray-600">Enterprise AI Trading</p>
                    </div>
                  </div>
                </div>

                {/* Desktop Header */}
                <div className="hidden lg:block text-center mb-8">
                  <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome back</h2>
                  <p className="text-gray-600">Sign in to your AI trading dashboard</p>
                </div>

                {/* Error Alert */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6"
                  >
                    <Alert className="border-red-200 bg-red-50">
                      <AlertCircle className="h-4 w-4 text-red-600" />
                      <AlertDescription className="text-red-700">
                        {error}
                      </AlertDescription>
                    </Alert>
                  </motion.div>
                )}

                {/* MFA Alert */}
                {mfaRequired && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6"
                  >
                    <Alert className="border-blue-200 bg-blue-50">
                      <Shield className="h-4 w-4 text-blue-600" />
                      <AlertDescription className="text-blue-700">
                        Please enter your MFA code to complete login
                      </AlertDescription>
                    </Alert>
                  </motion.div>
                )}

                {/* Login Form */}
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                  {/* Email Field */}
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-sm font-medium text-gray-700">
                      Email address
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="Enter your email"
                      className="h-11 bg-white border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                      {...register('email')}
                    />
                    {errors.email && (
                      <p className="text-sm text-red-600">{errors.email.message}</p>
                    )}
                  </div>

                  {/* Password Field */}
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                      Password
                    </Label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Enter your password"
                        className="h-11 bg-white border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 pr-12 transition-all"
                        {...register('password')}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                      >
                        {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                      </button>
                    </div>
                    {errors.password && (
                      <p className="text-sm text-red-600">{errors.password.message}</p>
                    )}
                  </div>

                  {/* MFA Field */}
                  {showMfaInput && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="space-y-2"
                    >
                      <Label htmlFor="mfa_code" className="text-sm font-medium text-gray-700">
                        MFA Code
                      </Label>
                      <Input
                        id="mfa_code"
                        type="text"
                        placeholder="Enter your MFA code"
                        className="h-12 bg-white border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                        {...register('mfa_code')}
                      />
                      {errors.mfa_code && (
                        <p className="text-sm text-red-600">{errors.mfa_code.message}</p>
                      )}
                    </motion.div>
                  )}

                  {/* Remember Me & Forgot Password */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="remember_me"
                        checked={watch('remember_me')}
                        onCheckedChange={(checked) => setValue('remember_me', checked as boolean)}
                      />
                      <Label htmlFor="remember_me" className="text-sm text-gray-600">
                        Remember me
                      </Label>
                    </div>
                    <Link
                      to="/auth/forgot-password"
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                      Forgot password?
                    </Link>
                  </div>

                  {/* Sign In Button */}
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full h-11 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
                  >
                    {isLoading ? (
                      <div className="flex items-center space-x-2">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>Signing in...</span>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <span>Sign in</span>
                        <ArrowRight className="w-5 h-5" />
                      </div>
                    )}
                  </Button>

                  {/* Divider */}
                  <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-gray-300" />
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="px-2 bg-white text-gray-500">Or continue with</span>
                    </div>
                  </div>

                  {/* Google Sign In */}
                  <Button
                    type="button"
                    onClick={handleGoogleLogin}
                    variant="outline"
                    className="w-full h-11 border-gray-200 hover:bg-gray-50 text-gray-700 font-medium transition-all duration-200 hover:border-gray-300"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-5 h-5 bg-white rounded-full flex items-center justify-center">
                        <span className="text-lg font-bold text-blue-600">G</span>
                      </div>
                      <span>Continue with Google</span>
                    </div>
                  </Button>
                </form>

                {/* Sign Up Link */}
                <div className="mt-8 text-center">
                  <p className="text-gray-600">
                    Don't have an account?{' '}
                    <Link
                      to="/auth/register"
                      className="text-blue-600 hover:text-blue-800 font-semibold"
                    >
                      Sign up for free
                    </Link>
                  </p>
                </div>

                {/* Footer */}
                <div className="mt-8 pt-6 border-t border-gray-200 text-center">
                  <p className="text-xs text-gray-500">
                    © 2024 CryptoUniverse Enterprise. All rights reserved.
                  </p>
                  <div className="mt-2 text-xs text-gray-400">
                    <span className="mr-4">🔒 256-bit SSL</span>
                    <span className="mr-4">✓ SOC 2 Compliant</span>
                    <span>🛡️ Bank-level Security</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;