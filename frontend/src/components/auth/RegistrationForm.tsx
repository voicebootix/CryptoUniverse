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

const formSchema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters'),
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
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
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      setIsLoading(true);
      setError('');

      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to register');
      }

      toast({
        title: 'Success',
        description: 'Registration successful! Please check your email to verify your account.',
      });

    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
      toast({
        variant: 'destructive',
        title: 'Error',
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
            {...register('terms_agreed')}
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
