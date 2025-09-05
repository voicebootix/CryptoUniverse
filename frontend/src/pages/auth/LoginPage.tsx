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
        <div className="min-h-screen flex flex-col items-center justify-center px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-md"
          >
            {/* Form */}
            <form 
              onSubmit={handleSubmit(onSubmit)} 
              className="space-y-6"
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
              <div>
                <Label htmlFor="email">Email Address</Label>
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
                />
              </div>

              {/* Password Input */}
              <div>
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    {...register("password")}
                    placeholder="••••••••••"
                    label="Password"
                    error={errors.password?.message}
                    aria-required="true"
                    aria-invalid={errors.password ? "true" : "false"}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-1/2 -translate-y-1/2"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
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
                    label="Remember me"
                    aria-label="Remember me on this device"
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
                className="w-full"
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
                className="w-full"
                onClick={handleGoogleLogin}
                label="Continue with Google"
              >
                <img
                  src="/google.svg"
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
      </Container>
    </div>
  );
};

export default LoginPage;