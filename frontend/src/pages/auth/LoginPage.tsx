import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Eye,
  EyeOff,
  Loader2,
  Shield,
  AlertCircle,
  TrendingUp,
  Mail,
  KeyRound,
  ArrowRight,
} from "lucide-react";
import {
  useAuthStore,
  useMfaRequired,
  useAuthError,
  useAuthLoading,
} from "@/store/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { apiClient } from "@/lib/api/client";
import { Container } from "@/components/ui/container";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
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
      // Let backend handle the callback URL
      const response = await apiClient.post("/auth/oauth/url", {
        provider: "google",
        is_signup: false,
      });

      if (response.status !== 200) {
        throw new Error("Failed to get OAuth URL");
      }

      const data = response.data;

      // Store login intent in session storage
      sessionStorage.setItem("oauth_intent", "login");

      // Redirect to Google OAuth
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error("Google login error:", error);
      // Show user-friendly error message
      alert("Backend server is not running. Please start the backend server first.");
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
        navigate("/dashboard");
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
            ease: "easeInOut",
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
            ease: "easeInOut",
          }}
        />
      </div>

      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="pt-8 pb-8"
        >
          <Container>
            <div className="flex items-center">
              <motion.div
                className="w-12 h-12 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg mr-4"
                whileHover={{ scale: 1.05 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
              >
                <TrendingUp className="w-6 h-6 text-white" />
              </motion.div>
              <div>
                <h1 className="text-2xl font-bold">
                  CryptoUniverse
                </h1>
                <p className="text-sm text-blue-300">
                  AI Money Manager
                </p>
              </div>
            </div>
          </Container>
        </motion.header>

                {/* Main Content */}
        <main className="flex-1 flex items-center justify-center px-4">
          <div className="w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
            
            {/* Left Side - Welcome & Info + Enterprise Features */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="space-y-8 text-center lg:text-left"
            >
              <div>
                <h2 className="text-4xl lg:text-5xl font-bold leading-tight">
                  <span className="text-white">Welcome to AI-Powered</span>
                  <br />
                  <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                    Trading
                  </span>
                </h2>
                <p className="text-lg text-gray-300 leading-relaxed mt-4">
                  Advanced cryptocurrency trading with multi-model AI consensus and institutional-grade security.
                </p>
              </div>

              {/* Enterprise Features - In Left Side */}
              <div className="space-y-6">
                <div>
                  <h3 className="text-2xl font-bold leading-tight mb-4">
                    <span className="text-white">Enterprise AI Trading Platform</span>
                  </h3>
                  <p className="text-gray-300 text-sm">
                    Automated cryptocurrency trading powered by advanced AI algorithms
                  </p>
                </div>

                <div className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <div className="w-4 h-4 bg-green-500 rounded-full"></div>
                    </div>
                    <div>
                      <h4 className="text-white font-semibold text-sm">AI-Powered Trading</h4>
                      <p className="text-gray-400 text-xs">Multi-modal consensus with GPT-4, Claude, and Gemini</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Shield className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <h4 className="text-white font-semibold text-sm">Enterprise Security</h4>
                      <p className="text-gray-400 text-xs">Bank-level encryption with multi-factor authentication</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <div className="w-4 h-4 bg-yellow-500 rounded-full"></div>
                    </div>
                    <div>
                      <h4 className="text-white font-semibold text-sm">Real-Time Execution</h4>
                      <p className="text-gray-400 text-xs">Lightning-fast trades across multiple exchanges</p>
                    </div>
                  </div>

                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center flex-shrink-0">
                      <div className="w-4 h-4 bg-green-500 rounded-full"></div>
                    </div>
                    <div>
                      <h4 className="text-white font-semibold text-sm">Risk Management</h4>
                      <p className="text-gray-400 text-xs">Advanced portfolio protection and position sizing</p>
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/10">
                  <div className="text-center">
                    <div className="text-lg font-bold text-green-400">99.9%</div>
                    <div className="text-xs text-gray-400">Uptime</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-blue-400">$100M+</div>
                    <div className="text-xs text-gray-400">Assets Under Management</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-purple-400">24/7</div>
                    <div className="text-xs text-gray-400">Trading</div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Right Side - Login Form + Enterprise Features */}
            <div className="space-y-8">
              {/* Login Form */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="w-full max-w-md mx-auto"
              >
              <div className="relative bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-8 shadow-2xl">
                <div className="text-center mb-8">
                  <div className="flex justify-center mb-4">
                    <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                      <KeyRound className="w-8 h-8 text-white" />
                    </div>
                      </div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">
                        Welcome Back
                      </h2>
                  <p className="text-gray-300 text-base">
                        Sign in to your AI trading dashboard
                      </p>
                </div>

                    {/* Alerts */}
                    <AnimatePresence>
                      {error && (
                        <motion.div
                          initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                      animate={{ opacity: 1, height: "auto", marginBottom: 16 }}
                          exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                      <Alert variant="destructive" className="bg-red-500/10 border-red-500/30 text-red-300">
                        <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{error}</AlertDescription>
                          </Alert>
                        </motion.div>
                      )}
                      {mfaRequired && (
                        <motion.div
                          initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                      animate={{ opacity: 1, height: "auto", marginBottom: 16 }}
                          exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          <Alert className="border-blue-500/30 bg-blue-500/10 backdrop-blur-sm text-blue-300">
                            <Shield className="h-4 w-4 text-blue-400" />
                            <AlertDescription>
                          Please enter your MFA code.
                            </AlertDescription>
                          </Alert>
                        </motion.div>
                      )}
                    </AnimatePresence>

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-6">
                  <div>
                    <Label htmlFor="email">Email Address</Label>
                    <Input id="email" type="email" autoComplete="email" {...register("email")} placeholder="admin@cryptouniverse.com" />
                    {errors.email && <p className="text-red-400 text-sm mt-1">{errors.email.message}</p>}
                        </div>

                      {/* Password Field */}
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-white font-semibold flex items-center space-x-2">
                      <KeyRound className="w-5 h-5 text-purple-400" />
                          <span>Password</span>
                        </Label>
                        <div className="relative group">
                          <Input
                            id="password"
                            type={showPassword ? "text" : "password"}
                            autoComplete="current-password"
                        placeholder="••••••••••••"
                        className="h-12 bg-white/10 border-white/20 focus:border-purple-500 focus:bg-white/15 text-white placeholder:text-gray-400 rounded-xl pr-10 transition-all duration-300 text-base px-4"
                            {...register("password")}
                          />
                          <motion.button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-white transition-colors duration-200"
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            {showPassword ? (
                          <EyeOff className="w-5 h-5" />
                            ) : (
                          <Eye className="w-5 h-5" />
                            )}
                          </motion.button>
                        </div>
                        <AnimatePresence>
                          {errors.password && (
                            <motion.p
                              initial={{ opacity: 0, y: -10 }}
                              animate={{ opacity: 1, y: 0 }}
                              exit={{ opacity: 0, y: -10 }}
                          className="text-sm text-red-400 flex items-center space-x-2 pt-1"
                            >
                              <AlertCircle className="w-4 h-4" />
                              <span>{errors.password.message}</span>
                            </motion.p>
                          )}
                        </AnimatePresence>
                  </div>

                      {/* MFA Field */}
                      <AnimatePresence>
                        {showMfaInput && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.3 }}
                        className="space-y-2"
                      >
                        <Label htmlFor="mfa_code" className="text-white font-semibold flex items-center space-x-2">
                          <Shield className="w-5 h-5 text-green-400" />
                              <span>MFA Code</span>
                            </Label>
                            <div className="relative group">
                              <Input
                                id="mfa_code"
                                type="text"
                            placeholder="Enter 6-digit code"
                            className="h-12 bg-white/10 border-white/20 focus:border-green-500 focus:bg-white/15 text-white placeholder:text-gray-400 rounded-xl transition-all duration-300 text-base px-4"
                                {...register("mfa_code")}
                              />
                            </div>
                            {errors.mfa_code && (
                          <p className="text-sm text-red-400 flex items-center space-x-2 pt-1">
                                <AlertCircle className="w-4 h-4" />
                                <span>{errors.mfa_code.message}</span>
                          </p>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Remember Me & Forgot Password */}
                  <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center space-x-2">
                          <Checkbox
                            id="remember_me"
                            checked={watch("remember_me")}
                        onCheckedChange={(checked) => setValue("remember_me", checked as boolean)}
                        className="border-white/30 data-[state=checked]:bg-blue-500 data-[state=checked]:border-blue-500"
                      />
                      <Label htmlFor="remember_me" className="text-gray-300 font-medium">
                            Remember me
                          </Label>
                        </div>
                        <span className="text-sm text-gray-500">
                          Forgot password? Contact support
                        </span>
                  </div>

                      {/* Sign In Button */}
                  <div className="pt-4">
                        <Button
                          type="submit"
                          disabled={isLoading}
                      className="w-full h-12 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 text-white font-bold text-base rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98]"
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
                  </div>
                    </form>

                    {/* Divider */}
                <div className="relative my-6">
                      <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-white/20" />
                      </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-4 bg-slate-800/60 backdrop-blur-sm text-gray-300 rounded-full">
                          Or continue with
                        </span>
                      </div>
                </div>

                    {/* Social Login & Sign Up */}
                <div className="space-y-4">
                      {/* Google Sign In */}
                      <Button
                        type="button"
                        onClick={handleGoogleLogin}
                        variant="outline"
                    className="w-full h-12 bg-white/5 border-white/20 hover:bg-white/10 text-white rounded-xl transition-all duration-300 font-medium"
                  >
                    <div className="flex items-center justify-center space-x-3">
                      <svg className="w-5 h-5" viewBox="0 0 48 48">
                        <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"></path>
                        <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"></path>
                        <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"></path>
                        <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"></path>
                          </svg>
                      <span>Continue with Google</span>
                        </div>
                      </Button>

                      {/* Sign Up Link */}
                  <div className="text-center pt-2">
                    <p className="text-sm text-gray-400">
                      Don't have an account?{" "}
                        <Button
                        variant="link"
                        className="p-0 h-auto text-sm text-blue-400 hover:text-blue-300 font-semibold"
                          onClick={() => navigate("/auth/register")}
                        >
                        Sign up
                        </Button>
                    </p>
                      </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default LoginPage;
