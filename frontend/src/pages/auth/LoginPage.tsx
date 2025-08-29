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
  Globe,
  Lock,
  CheckCircle,
  ArrowRight,
  BarChart3
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

  const handleGoogleLogin = async () => {
    try {
      const response = await apiClient.post('/auth/oauth/url', {
        provider: 'google',
        redirect_url: window.location.origin + '/auth/callback',
      });

      if (response.status !== 200) throw new Error('Failed to get OAuth URL');

      const data = response.data;
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('Google login error:', error);
    }
  };

  React.useEffect(() => {
    if (mfaRequired) setShowMfaInput(true);
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
      if (!mfaRequired) navigate('/dashboard');
    } catch {}
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center px-4 sm:px-6">
      <div className="w-full max-w-6xl h-auto md:max-h-[90vh] flex flex-col md:grid md:grid-cols-2 rounded-2xl shadow-2xl overflow-hidden bg-gray-800 border border-gray-700">

        {/* Left Panel: Hidden on small screens */}
        <div className="hidden md:flex flex-col justify-between p-10 bg-gradient-to-br from-purple-900 via-indigo-900 to-black relative overflow-hidden">
          {/* Background FX */}
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-purple-600/10 to-pink-600/10" />
          <div className="absolute top-20 left-20 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
          <div className="absolute bottom-20 right-20 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl animate-pulse" />

          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="relative z-10"
          >
            <div className="mb-12">
              <div className="flex items-center mb-6">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mr-4 shadow-lg">
                  <TrendingUp className="w-8 h-8 text-white" />
                </div>
                <div>
                  <h1 className="text-4xl font-bold text-white tracking-wider">CryptoUniverse</h1>
                  <p className="text-blue-200 text-lg">Enterprise AI Trading v2.0.1</p>
                </div>
              </div>
              <p className="text-xl text-gray-300 leading-relaxed">
                Automated cryptocurrency trading powered by advanced AI algorithms.
              </p>
            </div>

            <div className="space-y-6">
              <FeatureCard
                icon={<Bot className="w-6 h-6 text-white" />}
                bgColor="from-green-500 to-emerald-600"
                title="AI-Powered Trading"
                description="Multi-model consensus with GPT-4, Claude, and Gemini"
                delay={0.3}
              />
              <FeatureCard
                icon={<Globe className="w-6 h-6 text-white" />}
                bgColor="from-blue-500 to-cyan-600"
                title="Multi-Exchange Support"
                description="Trade across 8+ major exchanges with arbitrage scanning"
                delay={0.5}
              />
              <FeatureCard
                icon={<BarChart3 className="w-6 h-6 text-white" />}
                bgColor="from-purple-500 to-pink-600"
                title="Advanced Analytics"
                description="Institutional-grade risk management and reporting"
                delay={0.7}
              />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.0, duration: 0.6 }}
            className="relative z-10 mt-12 p-6 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10"
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
            </div>
          </motion.div>
        </div>

        {/* Right Panel: Login */}
        <div className="flex flex-col justify-center p-6 sm:p-10 bg-gray-800 overflow-y-auto w-full">
          <div className="w-full max-w-md mx-auto">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
              <div className="bg-gray-900 shadow-xl rounded-2xl p-8 border border-gray-700">
                <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold text-white mb-2">Welcome Back</h2>
                  <p className="text-gray-400">Sign in to your AI trading dashboard</p>
                </div>

                {error && (
                  <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
                    <Alert className="border-red-500/50 bg-red-500/10 text-red-300">
                      <AlertCircle className="h-4 w-4 text-red-400" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  </motion.div>
                )}

                {mfaRequired && (
                  <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
                    <Alert className="border-blue-500/50 bg-blue-500/10 text-blue-300">
                      <Shield className="h-4 w-4 text-blue-400" />
                      <AlertDescription>Please enter your 2FA code to continue.</AlertDescription>
                    </Alert>
                  </motion.div>
                )}

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                  <div>
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" type="email" {...register('email')} placeholder="you@example.com" />
                    {errors.email && <p className="text-sm text-red-400 mt-1">{errors.email.message}</p>}
                  </div>

                  <div className="relative">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      {...register('password')}
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-9 text-gray-400 hover:text-gray-200"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                    {errors.password && <p className="text-sm text-red-400 mt-1">{errors.password.message}</p>}
                  </div>

                  {showMfaInput && (
                    <div>
                      <Label htmlFor="mfa_code">2FA Code</Label>
                      <Input id="mfa_code" {...register('mfa_code')} placeholder="123456" />
                    </div>
                  )}

                  <div className="flex items-center space-x-2">
                    <Checkbox id="remember_me" onCheckedChange={(checked) => setValue('remember_me', !!checked)} />
                    <Label htmlFor="remember_me">Remember me</Label>
                  </div>

                  <Button type="submit" className="w-full mt-2" disabled={isLoading}>
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    Login
                  </Button>

                  <div className="flex items-center justify-between text-sm text-gray-400 mt-4">
                    <Link to="/forgot-password" className="hover:text-white">
                      Forgot password?
                    </Link>
                    <Link to="/register" className="hover:text-white flex items-center space-x-1">
                      <span>Create account</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </form>

                <div className="mt-8 text-center">
                  <p className="text-gray-400 mb-3">Or sign in with</p>
                  <Button variant="outline" className="w-full" onClick={handleGoogleLogin}>
                    <img src="/google-icon.svg" alt="Google" className="w-5 h-5 mr-2" />
                    Sign in with Google
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

const FeatureCard: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
  bgColor: string;
  delay: number;
}> = ({ icon, title, description, bgColor, delay }) => (
  <motion.div
    initial={{ opacity: 0, x: -30 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ duration: 0.6, delay }}
    className={`flex items-start space-x-4 p-4 bg-gradient-to-r ${bgColor} rounded-xl shadow-md`}
  >
    <div className="p-2 bg-black/20 rounded-md">{icon}</div>
    <div>
      <h4 className="text-white font-semibold text-lg">{title}</h4>
      <p className="text-gray-100 text-sm">{description}</p>
    </div>
  </motion.div>
);

export default LoginPage;
