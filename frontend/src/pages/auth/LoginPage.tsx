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

const MotionDiv = ({ children, delay = 0, ...props }: { children: React.ReactNode; delay?: number; [key: string]: any }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.5 }}
    {...props}
  >
    {children}
  </motion.div>
);

const FeatureItem = ({ icon: Icon, title, color }: { icon: React.ComponentType<{ className?: string }>; title: string; color: string }) => (
  <div className="flex items-center space-x-3">
    <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center">
      <Icon className={`w-4 h-4 ${color}`} />
    </div>
    <span className="text-gray-300 font-medium">{title}</span>
  </div>
);

const StatItem = ({ value, label, color }: { value: string; label: string; color: string }) => (
  <div className="text-center">
    <div className={`text-xl font-bold ${color} mb-1`}>{value}</div>
    <div className="text-xs text-gray-400">{label}</div>
  </div>
);

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
      <div className="absolute inset-0 overflow-hidden">
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
            ease: 'easeInOut',
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
            ease: 'easeInOut',
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
                transition={{ type: 'spring', stiffness: 400, damping: 17 }}
              >
                <TrendingUp className="w-8 h-8 text-white" />
              </motion.div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-blue-100 to-purple-200 bg-clip-text text-transparent">
                  CryptoUniverse
                </h1>
                <p className="text-blue-300 text-lg font-medium">Enterprise AI Trading v2.0.1</p>
              </div>
            </div>
          </Container>
        </motion.div>

        {/* Main Content */}
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="w-full max-w-7xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-20 items-center">
              {/* Left Side - Feature Summary */}
              <motion.div
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="space-y-10 pr-10"
              >
                <div className="space-y-6">
                  <motion.h2
                    className="text-4xl lg:text-5xl font-bold leading-tight"
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
                    className="text-xl text-gray-300 leading-relaxed max-w-lg"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4, duration: 0.6 }}
                  >
                    Advanced cryptocurrency trading with multi-model AI consensus, institutional-grade security, and real-time market analysis.
                  </motion.p>
                </div>

                <MotionDiv delay={0.5} className="space-y-6">
                  <div className="flex items-start space-x-4">
                    <div className="w-14 h-14 bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <h3 className="text-white font-semibold text-xl mb-2">AI-Powered Trading</h3>
                      <p className="text-gray-400 leading-relaxed">Multi-model consensus with GPT-4, Claude, and Gemini for superior trading decisions.</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-4">
                    <div className="w-14 h-14 bg-gradient-to-r from-blue-500 to-cyan-600 rounded-xl flex items-center justify-center flex-shrink-0 mt-1">
                      <Globe className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <h3 className="text-white font-semibold text-xl mb-2">Multi-Exchange Support</h3>
                      <p className="text-gray-400 leading-relaxed">Trade across 8+ major exchanges with advanced arbitrage scanning capabilities.</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-4">
                    <div className="w-14 h-14 bg-gradient-to-r from-purple-500 to-pink-600 rounded-xl flex items-center justify-center flex-shrink-0 mt-1">
                      <Shield className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <h3 className="text-white font-semibold text-xl mb-2">Enterprise Security</h3>
                      <p className="text-gray-400 leading-relaxed">Bank-level encryption with multi-factor authentication and SOC 2 compliance.</p>
                    </div>
                  </div>
                </MotionDiv>

                <MotionDiv delay={0.6} className="relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 rounded-3xl blur-xl" />
                  <div className="relative grid grid-cols-3 gap-6 p-8 bg-white/5 backdrop-blur-sm rounded-3xl border border-white/10">
                    <div className="text-center">
                      <CheckCircle className="w-10 h-10 text-green-400 mx-auto mb-3" />
                      <div className="text-3xl font-bold text-green-400 mb-2">99.9%</div>
                      <div className="text-sm text-gray-400 font-medium">Uptime</div>
                    </div>
                    <div className="text-center">
                      <TrendingUp className="w-10 h-10 text-blue-400 mx-auto mb-3" />
                      <div className="text-3xl font-bold text-blue-400 mb-2">$100M+</div>
                      <div className="text-sm text-gray-400 font-medium">Assets Under Management</div>
                    </div>
                    <div className="text-center">
                      <Zap className="w-10 h-10 text-purple-400 mx-auto mb-3" />
                      <div className="text-3xl font-bold text-purple-400 mb-2">24/7</div>
                      <div className="text-sm text-gray-400 font-medium">Trading</div>
                    </div>
                  </div>
                </MotionDiv>
              </motion.div>

              {/* Right Side - Login Form */}
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="flex justify-center"
              >
                <div className="w-full max-w-xl">
                  <div className="relative bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-12 shadow-2xl">
                    <MotionDiv delay={0.6} className="text-center mb-12">
                      <div className="flex items-center justify-center mb-6">
                        <motion.div
                          className="w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center shadow-2xl"
                          whileHover={{ rotate: 5, scale: 1.05 }}
                          transition={{ type: 'spring', stiffness: 400, damping: 17 }}
                        >
                          <KeyRound className="w-12 h-12 text-white" />
                        </motion.div>
                      </div>
                      <h2 className="text-4xl font-bold text-white mb-4">Welcome Back</h2>
                      <p className="text-gray-300 text-xl">Sign in to your AI trading dashboard</p>
                    </MotionDiv>

                    {/* Alerts */}
                    <AnimatePresence>
                      {error && (
                        <motion.div
                          initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                          animate={{ opacity: 1, height: 'auto', marginBottom: 24 }}
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
                          animate={{ opacity: 1, height: 'auto', marginBottom: 24 }}
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
                      <MotionDiv delay={0.7} className="space-y-4">
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
                            aria-invalid={!!errors.email}
                            aria-describedby="email-error"
                          />
                        </div>
                        <AnimatePresence>
                          {errors.email && (
                            <motion.p
                              id="email-error"
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
                      </MotionDiv>

                      <MotionDiv delay={0.8} className="space-y-4">
                        <Label htmlFor="password" className="text-white font-semibold text-lg flex items-center space-x-3">
                          <KeyRound className="w-6 h-6 text-purple-400" />
                          <span>Password</span>
                        </Label>
                        <div className="relative">
                          <Input
                            id="password"
                            type={showPassword ? 'text' : 'password'}
                            placeholder="Enter your password"
                            className="h-16 bg-white/10 border-white/20 focus:border-purple-500 focus:bg-white/15 text-white placeholder:text-gray-400 rounded-2xl pr-16 transition-all duration-300 text-lg px-6"
                            {...register('password')}
                            aria-invalid={!!errors.password}
                            aria-describedby="password-error"
                          />
                          <motion.button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute inset-y-0 right-0 flex items-center pr-5 text-gray-400 hover:text-white transition-colors duration-200"
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                            aria-label={showPassword ? 'Hide password' : 'Show password'}
                          >
                            {showPassword ? <EyeOff className="w-6 h-6" /> : <Eye className="w-6 h-6" />}
                          </motion.button>
                        </div>
                        <AnimatePresence>
                          {errors.password && (
                            <motion.p
                              id="password-error"
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
                      </MotionDiv>

                      <AnimatePresence>
                        {showMfaInput && (
                          <MotionDiv delay={0.9} className="space-y-4">
                            <Label htmlFor="mfa_code" className="text-white font-semibold text-lg flex items-center space-x-3">
                              <Shield className="w-6 h-6 text-green-400" />
                              <span>MFA Code</span>
                            </Label>
                            <Input
                              id="mfa_code"
                              type="text"
                              placeholder="Enter your MFA code"
                              className="h-16 bg-white/10 border-white/20 focus:border-green-500 focus:bg-white/15 text-white placeholder:text-gray-400 rounded-2xl transition-all duration-300 text-lg px-6"
                              {...register('mfa_code')}
                              aria-invalid={!!errors.mfa_code}
                              aria-describedby="mfa-error"
                            />
                            {errors.mfa_code && (
                              <motion.p
                                id="mfa-error"
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="text-sm text-red-400 flex items-center space-x-2"
                              >
                                <AlertCircle className="w-4 h-4" />
                                <span>{errors.mfa_code.message}</span>
                              </motion.p>
                            )}
                          </MotionDiv>
                        )}
                      </AnimatePresence>

                      <MotionDiv delay={1} className="flex items-center justify-between pt-4">
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
                      </MotionDiv>

                      <MotionDiv delay={1.1}>
                        <Button
                          type="submit"
                          disabled={isLoading}
                          className="w-full h-16 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 text-white font-bold text-xl rounded-2xl shadow-2xl hover:shadow-3xl transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
                          aria-live="polite"
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
                      </MotionDiv>
                    </form>

                    <MotionDiv delay={1.2} className="relative my-10">
                      <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-white/30" />
                      </div>
                      <div className="relative flex justify-center">
                        <span className="px-6 bg-white/10 backdrop-blur-sm text-gray-300 text-lg font-medium rounded-full">
                          Or continue with
                        </span>
                      </div>
                    </MotionDiv>

                    <MotionDiv delay={1.3} className="space-y-6">
                      <Button
                        type="button"
                        onClick={handleGoogleLogin}
                        variant="outline"
                        className="w-full h-16 bg-white/10 border-white/30 hover:bg-white/20 text-white rounded-2xl transition-all duration-300 hover:scale-[1.02] text-lg font-semibold"
                        aria-label="Sign in with Google"
                      >
                        <div className="flex items-center justify-center space-x-4">
                          <svg className="w-7 h-7" viewBox="0 0 48 48">
                            <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z" />
                            <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z" />
                            <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z" />
                            <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z" />
                          </svg>
                          <span>Continue with Google</span>
                        </div>
                      </Button>

                      <div className="text-center pt-6">
                        <p className="text-gray-300 text-lg mb-5">Don't have an account?</p>
                        <Button
                          variant="outline"
                          className="w-full h-16 border-white/30 hover:bg-white/15 text-white rounded-2xl transition-all duration-300 hover:scale-[1.02] text-lg font-semibold"
                          onClick={() => navigate('/auth/register')}
                          aria-label="Create new account"
                        >
                          <div className="flex items-center justify-center space-x-3">
                            <Star className="w-6 h-6" />
                            <span>Create new account</span>
                          </div>
                        </Button>
                      </div>
                    </MotionDiv>
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
