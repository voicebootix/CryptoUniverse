import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
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
  BarChart3,
  Mail,
  KeyRound,
  Sparkles,
  Star,
  Zap,
} from 'lucide-react';
import { useAuthStore, useMfaRequired, useAuthError, useAuthLoading } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient } from '@/lib/api/client';
import { Container } from '@/components/ui/container';

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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 text-white">
      {/* Background Effects */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-purple-600/10 to-pink-600/5" />
        <motion.div
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/8 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.3, 0.4, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/8 rounded-full blur-3xl"
          animate={{
            scale: [1.1, 1, 1.1],
            opacity: [0.4, 0.3, 0.4],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      </div>

      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="pt-8 pb-8"
        >
          <Container>
            <div className="flex items-center justify-center">
              <motion.div
                className="w-16 h-16 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-2xl flex items-center justify-center shadow-lg mr-4"
                whileHover={{ scale: 1.05 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
              >
                <TrendingUp className="w-8 h-8 text-white" />
              </motion.div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-blue-100 to-purple-200 bg-clip-text text-transparent">
                  CryptoUniverse
                </h1>
                <p className="text-blue-300 text-lg font-medium">
                  Enterprise AI Trading v2.0.1
                </p>
              </div>
            </div>
          </Container>
        </motion.div>

        {/* Main Content - Centered Layout */}
        <div className="flex-1 flex items-center justify-center px-4 py-8">
          <div className="w-full max-w-6xl mx-auto">
            <div className="grid lg:grid-cols-5 gap-12 items-center">
              
              {/* Left Side - Feature Summary */}
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="lg:col-span-2 space-y-8"
              >
                {/* Hero Text */}
                <div className="space-y-4">
                  <motion.h2
                    className="text-3xl lg:text-4xl font-bold leading-tight"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.6 }}
                  >
                    <span className="text-white">Welcome to</span>
                    <br />
                    <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                      AI-Powered Trading
                    </span>
                  </motion.h2>
                  <motion.p
                    className="text-lg text-gray-300 leading-relaxed"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.6 }}
                  >
                    Advanced cryptocurrency trading with multi-model AI consensus and institutional-grade security.
                  </motion.p>
                </div>

                {/* Quick Features */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5, duration: 0.6 }}
                  className="space-y-4"
                >
                  {[
                    { icon: Bot, title: "AI-Powered Trading", color: "text-green-400" },
                    { icon: Globe, title: "Multi-Exchange Support", color: "text-blue-400" },
                    { icon: Shield, title: "Enterprise Security", color: "text-purple-400" }
                  ].map((feature, index) => (
                    <div key={index} className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center">
                        <feature.icon className={`w-4 h-4 ${feature.color}`} />
                      </div>
                      <span className="text-gray-300 font-medium">{feature.title}</span>
                    </div>
                  ))}
                </motion.div>

                {/* Stats */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.6, duration: 0.6 }}
                  className="grid grid-cols-3 gap-4 p-6 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10"
                >
                  {[
                    { value: "99.9%", label: "Uptime", color: "text-green-400" },
                    { value: "$100M+", label: "AUM", color: "text-blue-400" },
                    { value: "24/7", label: "Trading", color: "text-purple-400" }
                  ].map((stat, index) => (
                    <div key={index} className="text-center">
                      <div className={`text-xl font-bold ${stat.color} mb-1`}>{stat.value}</div>
                      <div className="text-xs text-gray-400">{stat.label}</div>
                    </div>
                  ))}
                </motion.div>
              </motion.div>

              {/* Right Side - Login Form (Centered & Larger) */}
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="lg:col-span-3 flex justify-center"
              >
                <div className="w-full max-w-lg">
                  {/* Glassmorphism Container */}
                  <div className="relative bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-12 shadow-2xl">
                    
                    {/* Form Header */}
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.6, duration: 0.6 }}
                      className="text-center mb-12"
                    >
                      <div className="flex items-center justify-center mb-6">
                        <motion.div
                          className="w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center shadow-2xl"
                          whileHover={{ rotate: 5, scale: 1.05 }}
                          transition={{ type: "spring", stiffness: 400, damping: 17 }}
                        >
                          <KeyRound className="w-12 h-12 text-white" />
                        </motion.div>
                      </div>
                      <h2 className="text-4xl font-bold text-white mb-4">Welcome Back</h2>
                      <p className="text-gray-300 text-xl">Sign in to your AI trading dashboard</p>
                    </motion.div>

                    {/* Alerts */}
                    <AnimatePresence>
                      {error && (
                        <motion.div
                          initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                          animate={{ opacity: 1, height: "auto", marginBottom: 24 }}
                          exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          <Alert className="border-red-500/30 bg-red-500/10 backdrop-blur-sm text-red-300">
                            <AlertCircle className="h-4 w-4 text-red-400" />
                            <AlertDescription>{error}</AlertDescription>
                          </Alert>
                        </motion.div>
                      )}

                      {mfaRequired && (
                        <motion.div
                          initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                          animate={{ opacity: 1, height: "auto", marginBottom: 24 }}
                          exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          <Alert className="border-blue-500/30 bg-blue-500/10 backdrop-blur-sm text-blue-300">
                            <Shield className="h-4 w-4 text-blue-400" />
                            <AlertDescription>Please enter your MFA code to complete login.</AlertDescription>
                          </Alert>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Login Form */}
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
                      
                      {/* Email Field */}
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.7, duration: 0.5 }}
                        className="space-y-4"
                      >
                        <Label htmlFor="email" className="text-white font-semibold text-lg flex items-center space-x-3">
                          <Mail className="w-6 h-6 text-blue-400" />
                          <span>Email Address</span>
                        </Label>
                        <div className="relative group">
                          <Input
                            id="email"
                            type="email"
                            placeholder="Enter your email address"
                            className="h-16 bg-white/10 border-white/20 focus:border-blue-500 focus:bg-white/15 text-white placeholder:text-gray-400 rounded-2xl transition-all duration-300 text-lg px-6"
                            {...register('email')}
                          />
                          <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-blue-500/10 via-transparent to-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                        </div>
                        <AnimatePresence>
                          {errors.email && (
                            <motion.p
                              initial={{ opacity: 0, y: -10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                              className="text-sm text-red-400 flex items-center space-x-2"
                            >
                              <AlertCircle className="w-4 h-4" />
                              <span>{errors.email.message}</span>
                            </motion.p>
                          )}
                        </AnimatePresence>
                      </motion.div>

                      {/* Password Field */}
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.8, duration: 0.5 }}
                        className="space-y-4"
                      >
                        <Label htmlFor="password" className="text-white font-semibold text-lg flex items-center space-x-3">
                          <KeyRound className="w-6 h-6 text-purple-400" />
                          <span>Password</span>
                        </Label>
                        <div className="relative group">
                          <Input
                            id="password"
                            type={showPassword ? 'text' : 'password'}
                            placeholder="Enter your password"
                            className="h-16 bg-white/10 border-white/20 focus:border-purple-500 focus:bg-white/15 text-white placeholder:text-gray-400 rounded-2xl pr-16 transition-all duration-300 text-lg px-6"
                            {...register('password')}
                          />
                          <motion.button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute inset-y-0 right-0 flex items-center pr-5 text-gray-400 hover:text-white transition-colors duration-200"
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            {showPassword ? <EyeOff className="w-6 h-6" /> : <Eye className="w-6 h-6" />}
                          </motion.button>
                          <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-purple-500/10 via-transparent to-pink-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                        </div>
                        <AnimatePresence>
                          {errors.password && (
                            <motion.p
                              initial={{ opacity: 0, y: -10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                              className="text-sm text-red-400 flex items-center space-x-2"
                            >
                              <AlertCircle className="w-4 h-4" />
                              <span>{errors.password.message}</span>
                            </motion.p>
                          )}
                        </AnimatePresence>
                      </motion.div>

                      {/* MFA Field */}
                      <AnimatePresence>
                        {showMfaInput && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.3 }}
                            className="space-y-4"
                          >
                            <Label htmlFor="mfa_code" className="text-white font-semibold text-lg flex items-center space-x-3">
                              <Shield className="w-6 h-6 text-green-400" />
                              <span>MFA Code</span>
                            </Label>
                            <div className="relative group">
                              <Input
                                id="mfa_code"
                                type="text"
                                placeholder="Enter your MFA code"
                                className="h-16 bg-white/10 border-white/20 focus:border-green-500 focus:bg-white/15 text-white placeholder:text-gray-400 rounded-2xl transition-all duration-300 text-lg px-6"
                                {...register('mfa_code')}
                              />
                              <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-green-500/10 via-transparent to-emerald-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                            </div>
                            {errors.mfa_code && (
                              <motion.p
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="text-sm text-red-400 flex items-center space-x-2"
                              >
                                <AlertCircle className="w-4 h-4" />
                                <span>{errors.mfa_code.message}</span>
                              </motion.p>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Remember Me & Forgot Password */}
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.9, duration: 0.5 }}
                        className="flex items-center justify-between pt-4"
                      >
                        <div className="flex items-center space-x-4">
                          <Checkbox
                            id="remember_me"
                            checked={watch('remember_me')}
                            onCheckedChange={(checked) => setValue('remember_me', checked as boolean)}
                            className="border-white/30 data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500 w-5 h-5"
                          />
                          <Label htmlFor="remember_me" className="text-gray-300 font-medium text-lg">
                            Remember me
                          </Label>
                        </div>
                        <Link
                          to="/auth/forgot-password"
                          className="text-blue-400 hover:text-blue-300 font-semibold text-lg transition-colors duration-200"
                        >
                          Forgot password?
                        </Link>
                      </motion.div>

                      {/* Sign In Button */}
                      <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 1, duration: 0.5 }}
                      >
                        <Button
                          type="submit"
                          disabled={isLoading}
                          className="w-full h-16 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 text-white font-bold text-xl rounded-2xl shadow-2xl hover:shadow-3xl transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
                        >
                          {isLoading ? (
                            <div className="flex items-center justify-center space-x-3">
                              <Loader2 className="w-7 h-7 animate-spin" />
                              <span>Signing in...</span>
                            </div>
                          ) : (
                            <div className="flex items-center justify-center space-x-3">
                              <span>Sign in</span>
                              <ArrowRight className="w-6 h-6" />
                            </div>
                          )}
                        </Button>
                      </motion.div>
                    </form>

                    {/* Divider */}
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 1.1, duration: 0.5 }}
                      className="relative my-10"
                    >
                      <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-white/30" />
                      </div>
                      <div className="relative flex justify-center">
                        <span className="px-6 bg-white/10 backdrop-blur-sm text-gray-300 text-lg font-medium rounded-full">
                          Or continue with
                        </span>
                      </div>
                    </motion.div>

                    {/* Social Login & Sign Up */}
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 1.2, duration: 0.5 }}
                      className="space-y-6"
                    >
                      {/* Google Sign In */}
                      <Button
                        type="button"
                        onClick={handleGoogleLogin}
                        variant="outline"
                        className="w-full h-16 bg-white/10 border-white/30 hover:bg-white/20 text-white rounded-2xl transition-all duration-300 hover:scale-[1.02] text-lg font-semibold"
                      >
                        <div className="flex items-center justify-center space-x-4">
                          <svg className="w-7 h-7" viewBox="0 0 48 48">
                            <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"></path>
                            <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"></path>
                            <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"></path>
                            <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"></path>
                          </svg>
                          <span className="font-medium">Continue with Google</span>
                        </div>
                      </Button>

                      {/* Sign Up Link */}
                      <div className="text-center pt-6">
                        <p className="text-gray-300 text-lg mb-5">
                          Don't have an account?
                        </p>
                        <Button
                          variant="outline"
                          className="w-full h-16 border-white/30 hover:bg-white/15 text-white rounded-2xl transition-all duration-300 hover:scale-[1.02] text-lg font-semibold"
                          onClick={() => navigate('/auth/register')}
                        >
                          <div className="flex items-center justify-center space-x-3">
                            <Star className="w-6 h-6" />
                            <span>Create new account</span>
                          </div>
                        </Button>
                      </div>
                    </motion.div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;