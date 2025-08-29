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
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('Google login error:', error);
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
    <div className="min-h-screen bg-gray-900 text-white flex">
      {/* Left Side - Branding & Features */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-8 lg:p-12 bg-gradient-to-br from-purple-900 via-indigo-900 to-black relative overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-purple-600/10 to-pink-600/10" />
        <div className="absolute top-20 left-20 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 right-20 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl animate-pulse" />

        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="relative z-10"
        >
          {/* Logo & Title */}
          <div className="mb-6 md:mb-8 lg:mb-12">
            <div className="flex items-center mb-4 md:mb-6 lg:mb-8">
              <div className="w-12 h-12 md:w-14 md:h-14 lg:w-16 lg:h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mr-3 md:mr-3 lg:mr-4 shadow-lg">
                <TrendingUp className="w-6 h-6 md:w-7 md:h-7 lg:w-8 lg:h-8 text-white" />
              </div>
              <div className="min-w-0 flex-1">
                <h1 className="text-xl md:text-2xl lg:text-4xl font-bold text-white tracking-wide lg:tracking-wider">CryptoUniverse</h1>
                <p className="text-blue-200 text-sm md:text-base lg:text-lg">Enterprise AI Trading v2.0.1</p>
              </div>
            </div>
            <p className="text-base md:text-lg lg:text-xl text-gray-300 leading-relaxed">
              Automated cryptocurrency trading powered by advanced AI algorithms.
            </p>
          </div>
          {/* Feature Highlights */}
          <div className="space-y-3 md:space-y-4 lg:space-y-6">
            <FeatureCard
              icon={<Bot className="w-4 h-4 md:w-5 md:h-5 lg:w-6 lg:h-6 text-white" />}
              bgColor="from-green-500 to-emerald-600"
              title="AI-Powered Trading"
              description="Multi-model consensus with GPT-4, Claude, and Gemini"
              delay={0.3}
            />
            <FeatureCard
              icon={<Globe className="w-4 h-4 md:w-5 md:h-5 lg:w-6 lg:h-6 text-white" />}
              bgColor="from-blue-500 to-cyan-600"
              title="Multi-Exchange Support"
              description="Trade across 8+ major exchanges with arbitrage scanning"
              delay={0.5}
            />
            <FeatureCard
              icon={<BarChart3 className="w-4 h-4 md:w-5 md:h-5 lg:w-6 lg:h-6 text-white" />}
              bgColor="from-purple-500 to-pink-600"
              title="Advanced Analytics"
              description="Institutional-grade risk management and reporting"
              delay={0.7}
            />
          </div>
        </motion.div>
        {/* Trust Indicators */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0, duration: 0.6 }}
          className="relative z-10 mt-6 md:mt-8 lg:mt-12 p-3 md:p-4 lg:p-6 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10"
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

      {/* Right Side - Login Form */}
      <div className="flex flex-col justify-center w-full lg:w-1/2 p-8 lg:p-10 bg-gray-800">
        <div className="w-full max-w-sm md:max-w-md lg:max-w-lg xl:max-w-xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="bg-gray-900 shadow-xl rounded-2xl p-6 lg:p-8 border border-gray-700">
              {/* Header */}
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-white mb-2">Welcome Back</h2>
                <p className="text-gray-400">Sign in to your AI trading dashboard</p>
              </div>
              {/* Error Alert */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-6"
                >
                  <Alert className="border-red-500/50 bg-red-500/10 text-red-300">
                    <AlertCircle className="h-4 w-4 text-red-400" />
                    <AlertDescription>
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
                  <Alert className="border-blue-500/50 bg-blue-500/10 text-blue-300">
                    <Shield className="h-4 w-4 text-blue-400" />
                    <AlertDescription>
                      Please enter your MFA code to complete login.
                    </AlertDescription>
                  </Alert>
                </motion.div>
              )}
              {/* Login Form */}
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                {/* Email Field */}
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-sm font-medium text-gray-300">
                    Email address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    className="h-11 bg-gray-700 border-gray-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all text-white"
                    {...register('email')}
                  />
                  {errors.email && (
                    <p className="text-sm text-red-400">{errors.email.message}</p>
                  )}
                </div>
                {/* Password Field */}
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-sm font-medium text-gray-300">
                    Password
                  </Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter your password"
                      className="h-11 bg-gray-700 border-gray-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 pr-12 transition-all text-white"
                      {...register('password')}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-white"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  {errors.password && (
                    <p className="text-sm text-red-400">{errors.password.message}</p>
                  )}
                </div>
                {/* MFA Field */}
                {showMfaInput && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="space-y-2"
                  >
                    <Label htmlFor="mfa_code" className="text-sm font-medium text-gray-300">
                      MFA Code
                    </Label>
                    <Input
                      id="mfa_code"
                      type="text"
                      placeholder="Enter your MFA code"
                      className="h-12 bg-gray-700 border-gray-600 focus:border-blue-500 focus:ring-blue-500 text-white"
                      {...register('mfa_code')}
                    />
                    {errors.mfa_code && (
                      <p className="text-sm text-red-400">{errors.mfa_code.message}</p>
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
                      className="border-gray-500"
                    />
                    <Label htmlFor="remember_me" className="text-sm text-gray-400">
                      Remember me
                    </Label>
                  </div>
                  <Link
                    to="/auth/forgot-password"
                    className="text-sm text-blue-400 hover:text-blue-300 font-medium"
                  >
                    Forgot password?
                  </Link>
                </div>
                {/* Sign In Button */}
                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full h-11 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center space-x-2">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Signing in...</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center space-x-2">
                      <span>Sign in</span>
                      <ArrowRight className="w-5 h-5" />
                    </div>
                  )}
                </Button>
                {/* Divider */}
                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-600" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-gray-900 text-gray-400">Or continue with</span>
                  </div>
                </div>
                {/* Google Sign In */}
                <Button
                  type="button"
                  onClick={handleGoogleLogin}
                  variant="outline"
                  className="w-full h-11 bg-gray-800 border-gray-600 hover:bg-gray-700 text-gray-300 font-medium transition-all duration-200 hover:border-gray-500"
                >
                  <div className="flex items-center justify-center space-x-3">
                    <svg className="w-5 h-5" viewBox="0 0 48 48">
                      <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12
	c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24
	c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"></path>
                      <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657
	C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"></path>
                      <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36
	c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"></path>
                      <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571
	c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"></path>
                    </svg>
                    <span>Continue with Google</span>
                  </div>
                </Button>
              </form>
              {/* Sign Up Link */}
              <div className="mt-8 text-center">
                <p className="text-gray-400">
                  Don't have an account?{' '}
                  <Link
                    to="/auth/register"
                    className="text-blue-400 hover:text-blue-300 font-semibold"
                  >
                    Sign up for free
                  </Link>
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

interface FeatureCardProps {
  icon: React.ReactNode;
  bgColor: string;
  title: string;
  description: string;
  delay: number;
}

const FeatureCard: React.FC<FeatureCardProps> = ({ icon, bgColor, title, description, delay }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.6 }}
    className="flex items-center space-x-2 md:space-x-3 lg:space-x-4 p-2 md:p-3 lg:p-4 bg-white/5 backdrop-blur-sm rounded-xl border border-white/10"
  >
    <div className={`w-8 h-8 md:w-10 md:h-10 lg:w-12 lg:h-12 bg-gradient-to-r ${bgColor} rounded-lg flex items-center justify-center shadow-md flex-shrink-0`}>
      {icon}
    </div>
    <div className="min-w-0 flex-1">
      <h3 className="text-white font-semibold text-xs md:text-sm lg:text-base">{title}</h3>
      <p className="text-gray-300 text-xs md:text-xs lg:text-sm leading-tight">{description}</p>
    </div>
  </motion.div>
);

export default LoginPage;
