import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/components/ui/use-toast';
import { Link } from 'react-router-dom';
import { apiClient } from '@/lib/api/client';
import { isAxiosError, type AxiosError } from 'axios';

const formSchema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  confirm_password: z.string(),
  terms_agreed: z.boolean().refine((val) => val === true, {
    message: 'You must agree to the terms of service',
  }),
}).refine((data) => data.password === data.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
});

type FormData = z.infer<typeof formSchema>;

export default function RegistrationForm() {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      terms_agreed: false,
    },
  });

  const onSubmit = async (data: FormData) => {
    try {
      setIsLoading(true);
      setError('');

      // Send only the data that backend expects
      const registrationData = {
        email: data.email,
        password: data.password,
        full_name: data.full_name,
        role: 'TRADER' // Default role
      };

      // Debug logging (dev only) - mask sensitive data
      if (import.meta.env.DEV) {
        console.log('Registration attempt:', {
          email: registrationData.email,
          full_name: registrationData.full_name,
          role: registrationData.role,
          password: '****' // Never log actual password
        });
      }
      
      const response = await apiClient.post('/auth/register', registrationData);
      
      // Success logging without sensitive response data
      if (import.meta.env.DEV) {
        console.log('Registration successful for user:', registrationData.email);
      }

      toast({
        title: 'Success',
        description: 'Registration successful! Please check your email to verify your account.',
      });

    } catch (err: unknown) {
      let errorMessage = 'An unexpected error occurred';
      
      // Type-safe axios error handling
      if (isAxiosError(err)) {
        // Dev-only logging - never log full error in production
        if (import.meta.env.DEV) {
          console.error('Registration request failed:', {
            status: err.response?.status,
            statusText: err.response?.statusText,
            url: err.config?.url
          });
        }
        
        // Handle 422 validation errors specifically
        if (err.response?.status === 422 && err.response?.data?.detail) {
          const validationErrors = err.response.data.detail;
          
          // TEMPORARY: Force log validation errors for debugging (will remove after fix)
          console.error('=== REGISTRATION VALIDATION ERROR DEBUG ===');
          console.error('Full validation errors:', validationErrors);
          console.error('=== END DEBUG ===');
          
          // Dev-only: log validation error details (safe metadata only)
          if (import.meta.env.DEV) {
            console.error('Validation errors:', validationErrors.map((error: any) => ({
              field: error.loc ? error.loc.join('.') : 'unknown',
              message: error.msg
            })));
          }
          
          // Extract user-friendly validation messages
          if (Array.isArray(validationErrors) && validationErrors.length > 0) {
            errorMessage = validationErrors.map((error: any) => 
              `${error.loc ? error.loc.join('.') + ': ' : ''}${error.msg}`
            ).join(', ');
          } else {
            errorMessage = 'Validation failed';
          }
        } else if (err.response?.data?.detail) {
          // Other API errors with detail
          errorMessage = typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : 'Server error occurred';
        } else if (err.message) {
          // Network or other axios errors
          errorMessage = err.message;
        }
      } else {
        // Non-axios errors
        if (import.meta.env.DEV) {
          console.error('Non-axios error during registration:', String(err));
        }
        errorMessage = 'Registration failed. Please try again.';
      }
      
      setError(errorMessage);
      toast({
        variant: 'destructive',
        title: 'Registration Failed',
        description: errorMessage,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">
          Create an Account
        </h1>
        <p className="text-sm text-muted-foreground">
          Join CryptoUniverse and start your trading journey
        </p>
      </div>

      {error && (
        <Alert variant="destructive" data-testid="global-error">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <Input
            {...register('full_name')}
            placeholder="Enter your full name"
            data-testid="full-name-input"
            disabled={isLoading}
          />
          {errors.full_name && (
            <p className="text-sm text-destructive" data-testid="full-name-error">
              {errors.full_name.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Input
            {...register('email')}
            type="email"
            placeholder="Enter your email"
            data-testid="email-input"
            disabled={isLoading}
          />
          {errors.email && (
            <p className="text-sm text-destructive" data-testid="email-error">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Input
            {...register('password')}
            type="password"
            placeholder="Enter your password"
            data-testid="password-input"
            disabled={isLoading}
          />
          <p className="text-xs text-muted-foreground">
            Password must be at least 8 characters with uppercase, lowercase, and number
          </p>
          {errors.password && (
            <p className="text-sm text-destructive" data-testid="password-error">
              {errors.password.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Input
            {...register('confirm_password')}
            type="password"
            placeholder="Confirm your password"
            data-testid="confirm-password-input"
            disabled={isLoading}
          />
          {errors.confirm_password && (
            <p className="text-sm text-destructive" data-testid="confirm-password-error">
              {errors.confirm_password.message}
            </p>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <Checkbox
            id="terms_agreed"
            checked={watch('terms_agreed')}
            onCheckedChange={(checked) => setValue('terms_agreed', checked as boolean)}
            data-testid="terms-checkbox"
            disabled={isLoading}
          />
          <label
            htmlFor="terms_agreed"
            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            I agree to the <Link to="/terms" className="underline">Terms of Service</Link>
          </label>
        </div>
        {errors.terms_agreed && (
            <p className="text-sm text-destructive" data-testid="terms-error">
              {errors.terms_agreed.message}
            </p>
        )}

        <Button
          type="submit"
          className="w-full"
          disabled={isLoading}
          data-testid="submit-button"
        >
          {isLoading ? 'Creating Account...' : 'Create Account'}
        </Button>
      </form>
    </div>
  );
}
