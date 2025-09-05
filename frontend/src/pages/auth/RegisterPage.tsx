import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Container } from '@/components/ui/container';
import RegistrationForm from '@/components/auth/RegistrationForm';
import { useAuthStore } from '@/store/authStore';
import { apiClient } from '@/lib/api/client';

const RegisterPage: React.FC = () => {
  const clearError = useAuthStore((state) => state.clearError);

  const handleGoogleSignUp = async () => {
    try {
      clearError();

      const response = await apiClient.post("/auth/oauth/url", {
        provider: "google",
        is_signup: true,
      });

      if (response.status !== 200) {
        throw new Error("Failed to get OAuth URL");
      }

      sessionStorage.setItem("oauth_intent", "signup");
      window.location.href = response.data.authorization_url;
    } catch (error) {
      console.error("Google signup error:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 text-white">
      <Container>
        <div className="grid grid-cols-1 md:grid-cols-2 min-h-screen">
          {/* Left Side: Create Account */}
          <div className="flex flex-col items-center justify-center p-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="w-full max-w-md"
            >
              <div className="space-y-2 text-center mb-6">
                <h1 className="text-2xl font-semibold tracking-tight">
                  Create Account
                </h1>
                <p className="text-sm text-muted-foreground">
                  Join CryptoUniverse and start your trading journey
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={handleGoogleSignUp}
              >
                <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                Sign up with Google
              </Button>

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">Or register with email</span>
                </div>
              </div>

              <RegistrationForm />

              <div className="text-center mt-4">
                <p className="text-sm text-muted-foreground">
                  Already have an account?{" "}
                  <Link to="/auth/login" className="text-primary hover:underline">
                    Sign in here
                  </Link>
                </p>
              </div>
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
                <div>
                    <h3 className="text-lg font-semibold">AI-Powered Trading</h3>
                    <p className="text-muted-foreground">Multi-model consensus with GPT-4, Claude, and Gemini</p>
                </div>
                <div>
                    <h3 className="text-lg font-semibold">Enterprise Security</h3>
                    <p className="text-muted-foreground">Bank-level encryption with multi-factor authentication</p>
                </div>
                <div>
                    <h3 className="text-lg font-semibold">Real-Time Execution</h3>
                    <p className="text-muted-foreground">Lightning-fast trades across multiple exchanges</p>
                </div>
                <div>
                    <h3 className="text-lg font-semibold">Risk Management</h3>
                    <p className="text-muted-foreground">Advanced portfolio protection and position sizing</p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </Container>
    </div>
  );
};

export default RegisterPage;
