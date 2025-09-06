import React, { useState, useEffect } from "react";
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
  Bot,
  Lock,
  Zap,
  BarChart3,
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
import { getPublicAssetUrl } from "@/lib/utils/assets";
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

  // Sync MFA input visibility with store state
  useEffect(() => {
    setShowMfaInput(mfaRequired);
  }, [mfaRequired]);

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
      const response = await apiClient.post("/auth/oauth/url", {
        provider: "google",
        is_signup: false,
      });

      if (response.status === 200) {
        sessionStorage.setItem("oauth_intent", "login");
        window.location.href = response.data.authorization_url;
      }
    } catch (error: any) {
      console.error("Google login error:", error);
      if (error.response?.status === 404) {
        alert("OAuth service is temporarily unavailable. Please try again later.");
      } else if (error.response?.status === 401) {
        alert("Authentication failed. Please check your credentials.");
      } else if (!error.response && error.message.includes('Network Error')) {
        alert("Unable to connect to the server. Please check your internet connection.");
      } else {
        alert("An error occurred during login. Please try again later.");
      }
    }
  };

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
      <Container>
        <div className="grid grid-cols-1 md:grid-cols-2 min-h-screen">
          {/* Left Side: Login Form */}
          <div className="flex flex-col items-center justify-center p-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="w-full max-w-md"
            >
              {/* Logo and Title */}
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold text-white">
                  Welcome Back
                </h2>
                <p className="text-gray-400 mt-2">Sign in to your account</p>
              </div>

              {/* Form with styled box */}
              <form 
                onSubmit={handleSubmit(onSubmit)} 
                className="space-y-6 bg-white/5 backdrop-blur-xl p-8 rounded-2xl border border-white/10 shadow-2xl"
                role="form"
                aria-label="Login Form"
              >
                {/* Error Alert */}
                    <AnimatePresence>
                      {error && (
                        <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                  >
                    <Alert 
                      variant="destructive" 
                      className="bg-red-500/10 border-red-500/30"
                      role="alert"
                    >
                        <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{error}</AlertDescription>
                          </Alert>
                        </motion.div>
                      )}
                    </AnimatePresence>

                {/* Email Input */}
                    <div className="space-y-2">
                      <Label htmlFor="email" className="text-gray-300 flex items-center gap-2">
                        <Mail className="h-4 w-4 text-blue-400" />
                        Email Address
                      </Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    {...register("email")}
                    placeholder="admin@cryptouniverse.com"
                    label="Email Address"
                    error={errors.email?.message}
                    aria-required="true"
                    aria-invalid={errors.email ? "true" : "false"}
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-500 focus:border-blue-400 focus:ring-blue-400"
                  />
                          </div>

                {/* Password Input */}
                <div className="space-y-2">
                  <Label htmlFor="password" className="text-gray-300 flex items-center gap-2">
                    <KeyRound className="h-4 w-4 text-purple-400" />
                    Password
                  </Label>
                  <div className="relative">
                            <Input
                              id="password"
                              type={showPassword ? "text" : "password"}
                              autoComplete="current-password"
                              {...register("password")}
                      placeholder="••••••••••"
                      aria-required="true"
                      aria-invalid={errors.password ? "true" : "false"}
                      aria-describedby="password-error"
                      className="bg-white/10 border-white/20 text-white placeholder:text-gray-500 focus:border-purple-400 focus:ring-purple-400 pr-10"
                            />
                    <Button
                              type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-2 top-1/2 -translate-y-1/2"
                              onClick={() => setShowPassword(!showPassword)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                          </div>
                  {errors.password && (
                    <p id="password-error" className="text-sm text-destructive mt-1">
                      {errors.password.message}
                    </p>
                  )}
                  </div>

                {/* MFA Input */}
                        <AnimatePresence>
                          {showMfaInput && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }}
                  >
                    <Label htmlFor="mfa_code">MFA Code</Label>
                                <Input
                                  id="mfa_code"
                                  type="text"
                        {...register("mfa_code")}
                              placeholder="Enter 6-digit code"
                        label="MFA Code"
                        error={errors.mfa_code?.message}
                        aria-required={showMfaInput}
                        aria-invalid={errors.mfa_code ? "true" : "false"}
                              />
                            </motion.div>
                          )}
                        </AnimatePresence>

                        {/* Remember Me & Forgot Password */}
                <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                            <Checkbox
                              id="remember_me"
                              checked={watch("remember_me")}
                          onCheckedChange={(checked) => setValue("remember_me", checked as boolean)}
                      />
                    <Label 
                      htmlFor="remember_me" 
                      className="text-sm text-gray-400"
                    >
                              Remember me
                            </Label>
                          </div>
                  <Link
                    to="/auth/forgot-password"
                    className="text-sm text-blue-400 hover:text-blue-300"
                    aria-label="Forgot your password? Click to reset"
                  >
                    Forgot password?
                  </Link>
                    </div>

                {/* Submit Button */}
                        <Button
                          type="submit"
                          disabled={isLoading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-lg transition-all duration-300 transform hover:scale-105"
                loading={isLoading}
                label={isLoading ? "Signing in..." : "Sign in"}
                        >
                          {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              <span>Signing in...</span>
                  </>
                          ) : (
                  <>
                              <span>Sign in</span>
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                          )}
                        </Button>

                {/* OAuth Divider */}
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

                      {/* Google Sign In */}
                      <Button
                        type="button"
                variant="outline"
                className="w-full bg-white/10 border-white/20 hover:bg-white/20 text-white transition-all duration-300"
                        onClick={handleGoogleLogin}
                label="Continue with Google"
              >
                <img
                  src={getPublicAssetUrl('google.svg')}
                  alt="Google"
                  className="w-5 h-5 mr-2"
                  aria-hidden="true"
                />
                Continue with Google
                      </Button>

                      {/* Sign Up Link */}
              <div className="text-center mt-4">
                <span className="text-sm text-gray-400">
                      Don't have an account?{" "}
                  <Link
                    to="/auth/register"
                    className="text-blue-400 hover:text-blue-300"
                    aria-label="Create a new account"
                        >
                        Sign up
                  </Link>
                </span>
                      </div>
              </form>
            </motion.div>
          </div>

          {/* Right Side: Platform Details */}
          <div className="hidden md:flex flex-col items-center justify-center p-8 bg-slate-800/50">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="w-full max-w-md"
            >
              <h1 className="text-4xl font-bold">Enterprise AI Trading Platform</h1>
              <p className="text-muted-foreground mt-4">
                Automated cryptocurrency trading powered by advanced AI algorithms
              </p>
              <div className="space-y-6 mt-8">
                <div className="flex items-start space-x-3">
                  <div className="p-2 rounded-lg bg-blue-500/20">
                    <Bot className="h-6 w-6 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-nowrap">AI-Powered Trading</h3>
                    <p className="text-muted-foreground text-sm text-nowrap">Multi-model consensus with GPT-4, Claude, and Gemini</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="p-2 rounded-lg bg-purple-500/20">
                    <Lock className="h-6 w-6 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-nowrap">Enterprise Security</h3>
                    <p className="text-muted-foreground text-sm text-nowrap">Bank-level encryption with multi-factor authentication</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="p-2 rounded-lg bg-green-500/20">
                    <Zap className="h-6 w-6 text-green-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-nowrap">Real-Time Execution</h3>
                    <p className="text-muted-foreground text-sm text-nowrap">Lightning-fast trades across multiple exchanges</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="p-2 rounded-lg bg-orange-500/20">
                    <BarChart3 className="h-6 w-6 text-orange-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-nowrap">Risk Management</h3>
                    <p className="text-muted-foreground text-sm text-nowrap">Advanced portfolio protection and position sizing</p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 mt-8">
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-400">99.9%</p>
                  <p className="text-sm text-muted-foreground">Uptime</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-blue-400">$100M+</p>
                  <p className="text-sm text-muted-foreground">Assets Under Management</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-400">24/7</p>
                  <p className="text-sm text-muted-foreground">Trading</p>
                </div>
              </div>

              <div className="mt-8 p-4 border border-white/10 rounded-lg bg-white/5">
                <p className="text-sm italic text-muted-foreground">
                  "CryptoUniverse's AI trading platform has revolutionized our investment strategy. The autonomous features and risk management are unparalleled."
                </p>
                <p className="text-sm font-semibold mt-2">— Sarah Chen, Portfolio Manager at Hedge Fund Alpha</p>
              </div>
            </motion.div>
          </div>
        </div>
      </Container>
    </div>
  );
};

export default LoginPage;