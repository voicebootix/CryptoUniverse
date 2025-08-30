import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Container } from '@/components/ui/container';
import { Alert, AlertDescription } from '@/components/ui/alert';

const OAuthCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string>('');
  
  const setUser = useAuthStore((state) => state.setUser);
  const setTokens = useAuthStore((state) => state.setTokens);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        // Handle OAuth errors
        if (error) {
          setStatus('error');
          setError(`OAuth error: ${error}`);
          return;
        }

        // Validate required parameters
        if (!code || !state) {
          setStatus('error');
          setError('Missing required OAuth parameters');
          return;
        }

        // Get API base URL
        const API_BASE_URL = import.meta.env.VITE_API_URL || (
          import.meta.env.PROD 
            ? 'https://cryptouniverse.onrender.com/api/v1'
            : 'http://localhost:8000/api/v1'
        );

        // Exchange code for tokens
        const response = await fetch(`${API_BASE_URL}/auth/oauth/callback/google?code=${code}&state=${state}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'OAuth authentication failed');
        }

        const data = await response.json();

        // Store tokens and user data
        setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          token_type: data.token_type || 'bearer'
        });
        setUser(data.user);

        setStatus('success');

        // Redirect to dashboard after a brief success message
        setTimeout(() => {
          navigate('/dashboard', { replace: true });
        }, 2000);

      } catch (err) {
        console.error('OAuth callback error:', err);
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Authentication failed');
      }
    };

    handleOAuthCallback();
  }, [searchParams, navigate, setUser, setTokens]);

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

      <div className="relative z-10 min-h-screen flex items-center justify-center px-4">
        <Container>
          <div className="max-w-md mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-12 shadow-2xl text-center"
            >
              {status === 'loading' && (
                <>
                  <motion.div
                    className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-6"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <Loader2 className="w-8 h-8 text-white" />
                  </motion.div>
                  <h2 className="text-2xl font-bold text-white mb-4">
                    Completing Sign In
                  </h2>
                  <p className="text-gray-300">
                    Please wait while we complete your authentication...
                  </p>
                </>
              )}

              {status === 'success' && (
                <>
                  <motion.div
                    className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.5, type: "spring" }}
                  >
                    <CheckCircle className="w-8 h-8 text-white" />
                  </motion.div>
                  <h2 className="text-2xl font-bold text-white mb-4">
                    Welcome to CryptoUniverse!
                  </h2>
                  <p className="text-gray-300">
                    Authentication successful. Redirecting to your dashboard...
                  </p>
                </>
              )}

              {status === 'error' && (
                <>
                  <motion.div
                    className="w-16 h-16 bg-gradient-to-r from-red-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-6"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.5, type: "spring" }}
                  >
                    <AlertCircle className="w-8 h-8 text-white" />
                  </motion.div>
                  <h2 className="text-2xl font-bold text-white mb-4">
                    Authentication Failed
                  </h2>
                  <Alert className="border-red-500/30 bg-red-500/10 backdrop-blur-sm text-red-300 mb-6">
                    <AlertCircle className="h-4 w-4 text-red-400" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                  <motion.button
                    className="w-full bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 text-white font-bold py-3 px-6 rounded-2xl transition-all duration-300"
                    onClick={() => navigate('/auth/login')}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    Return to Login
                  </motion.button>
                </>
              )}
            </motion.div>
          </div>
        </Container>
      </div>
    </div>
  );
};

export default OAuthCallbackPage;