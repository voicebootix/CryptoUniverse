import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Loader2, Shield, AlertCircle } from 'lucide-react';
import { useAuthStore, useMfaRequired, useAuthError, useAuthLoading } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';

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
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
        <p className="text-muted-foreground">
          Sign in to your account to access your AI trading dashboard
        </p>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-2"
        >
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </motion.div>
      )}

      {mfaRequired && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-2"
        >
          <Alert>
            <Shield className="h-4 w-4" />
            <AlertDescription>
              Two-factor authentication is required. Please enter your authentication code.
            </AlertDescription>
          </Alert>
        </motion.div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <Input
            id="email"
            type="email"
            placeholder="Enter your email"
            disabled={isLoading || mfaRequired}
            {...register('email')}
            className={errors.email ? 'border-destructive' : ''}
          />
          {errors.email && (
            <p className="text-sm text-destructive">{errors.email.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Enter your password"
              disabled={isLoading || mfaRequired}
              {...register('password')}
              className={errors.password ? 'border-destructive pr-10' : 'pr-10'}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              disabled={isLoading || mfaRequired}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && (
            <p className="text-sm text-destructive">{errors.password.message}</p>
          )}
        </div>

        {(showMfaInput || mfaRequired) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="space-y-2"
          >
            <Label htmlFor="mfa_code">Authentication Code</Label>
            <Input
              id="mfa_code"
              type="text"
              placeholder="Enter 6-digit code"
              maxLength={6}
              disabled={isLoading}
              {...register('mfa_code')}
              className={errors.mfa_code ? 'border-destructive' : ''}
              autoComplete="one-time-code"
            />
            {errors.mfa_code && (
              <p className="text-sm text-destructive">{errors.mfa_code.message}</p>
            )}
            <p className="text-xs text-muted-foreground">
              Enter the 6-digit code from your authenticator app
            </p>
          </motion.div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="remember_me"
              checked={watch('remember_me')}
              onCheckedChange={(checked) => setValue('remember_me', checked as boolean)}
              disabled={isLoading}
            />
            <Label htmlFor="remember_me" className="text-sm">
              Remember me
            </Label>
          </div>

          <Link
            to="/auth/forgot-password"
            className="text-sm text-primary hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <Button
          type="submit"
          className="w-full trading-button"
          disabled={isLoading || (!email || !password) || (mfaRequired && !watch('mfa_code'))}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Signing in...
            </>
          ) : mfaRequired ? (
            'Verify & Sign In'
          ) : (
            'Sign In'
          )}
        </Button>
      </form>

      {/* Social login options (future enhancement) */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Enterprise Security
          </span>
        </div>
      </div>

      <div className="text-center text-sm text-muted-foreground space-y-2">
        <p>Protected by enterprise-grade security</p>
        <div className="flex justify-center items-center space-x-4 text-xs">
          <span className="flex items-center">
            <Shield className="h-3 w-3 mr-1" />
            256-bit SSL
          </span>
          <span>•</span>
          <span>SOC 2 Compliant</span>
          <span>•</span>
          <span>Bank-level Security</span>
        </div>
      </div>

      {/* Demo credentials for development */}
      {import.meta.env.DEV && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="p-4 bg-muted/50 rounded-lg border border-dashed"
        >
          <p className="text-xs text-muted-foreground mb-2 font-medium">
            Development Demo Credentials:
          </p>
          <div className="text-xs space-y-1 font-mono">
            <p>Email: admin@cryptouniverse.com</p>
            <p>Password: AdminPass123!</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setValue('email', 'admin@cryptouniverse.com');
              setValue('password', 'AdminPass123!');
            }}
            className="mt-2 text-xs text-primary hover:underline"
          >
            Fill demo credentials
          </button>
        </motion.div>
      )}
    </div>
  );
};

export default LoginPage;