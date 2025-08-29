import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Alert, AlertDescription } from '@/components/ui/alert';

const OAuthCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  
  const setUser = useAuthStore((state) => state.setUser);
  const setTokens = useAuthStore((state) => state.setTokens);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');
      const provider = window.location.pathname.includes('google') ? 'google' : 'google'; // Default to google for now

      // Handle OAuth error
      if (error) {
        setStatus('error');
        setError(`OAuth error: ${error}`);
        return;
      }

      // Check for required parameters
      if (!code || !state) {
        setStatus('error');
        setError('Missing OAuth parameters');
        return;
      }

      try {
        // Send callback data to backend  
        const API_BASE_URL = import.meta.env.VITE_API_URL || (
          import.meta.env.PROD 
            ? 'https://cryptouniverse.onrender.com/api/v1'
            : 'http://localhost:8000/api/v1'
        );
        const response = await fetch(`${API_BASE_URL}/auth/oauth/callback/${provider}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code,
            state,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'OAuth authentication failed');
        }

        const data = await response.json();
        
        // Store authentication data
        setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          token_type: data.token_type || 'bearer',
          expires_in: 3600 // 1 hour default
        });
        setUser(data.user);
        
        setStatus('success');
        
        // Redirect to dashboard after short delay
        setTimeout(() => {
          navigate('/dashboard');
        }, 2000);
        
      } catch (error) {
        console.error('OAuth callback error:', error);
        setStatus('error');
        setError(error instanceof Error ? error.message : 'Authentication failed');
      }
    };

    handleOAuthCallback();
  }, [searchParams, navigate, setUser, setTokens]);

  const handleRetry = () => {
    navigate('/auth/login');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary/20 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md"
      >
        <div className="bg-card rounded-lg border shadow-lg p-8">
          <div className="text-center space-y-6">
            {status === 'loading' && (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="mx-auto w-12 h-12 text-primary"
                >
                  <Loader2 className="w-full h-full" />
                </motion.div>
                <div>
                  <h2 className="text-2xl font-bold mb-2">Authenticating...</h2>
                  <p className="text-muted-foreground">
                    Please wait while we complete your Google sign-in.
                  </p>
                </div>
              </>
            )}

            {status === 'success' && (
              <>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                  className="mx-auto w-12 h-12 text-green-500"
                >
                  <CheckCircle className="w-full h-full" />
                </motion.div>
                <div>
                  <h2 className="text-2xl font-bold mb-2 text-green-600">Success!</h2>
                  <p className="text-muted-foreground">
                    You've been successfully authenticated. Redirecting to your dashboard...
                  </p>
                </div>
              </>
            )}

            {status === 'error' && (
              <>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                  className="mx-auto w-12 h-12 text-destructive"
                >
                  <XCircle className="w-full h-full" />
                </motion.div>
                <div>
                  <h2 className="text-2xl font-bold mb-2 text-destructive">Authentication Failed</h2>
                  <p className="text-muted-foreground mb-4">
                    We couldn't complete your Google sign-in.
                  </p>
                  
                  {error && (
                    <Alert variant="destructive" className="mb-4">
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}
                  
                  <button
                    onClick={handleRetry}
                    className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
                  >
                    Try Again
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default OAuthCallbackPage;
