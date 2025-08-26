import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { useAuthStore, useIsAuthenticated } from '@/store/authStore';

// Layout components
import AuthLayout from '@/components/layout/AuthLayout';
import DashboardLayout from '@/components/layout/DashboardLayout';

// Auth pages
import LoginPage from '@/pages/auth/LoginPage';
import RegisterPage from '@/pages/auth/RegisterPage';
import ForgotPasswordPage from '@/pages/auth/ForgotPasswordPage';
import ResetPasswordPage from '@/pages/auth/ResetPasswordPage';
import VerifyEmailPage from '@/pages/auth/VerifyEmailPage';

// Dashboard pages
import DashboardPage from '@/pages/dashboard/DashboardPage';
import TradingPage from '@/pages/trading/TradingPage';
import PortfolioPage from '@/pages/portfolio/PortfolioPage';
import AutonomousPage from '@/pages/autonomous/AutonomousPage';
import ExchangesPage from '@/pages/exchanges/ExchangesPage';
import SettingsPage from '@/pages/settings/SettingsPage';
import AdminPage from '@/pages/admin/AdminPage';

// Landing page
import LandingPage from '@/pages/LandingPage';

// Error pages
import NotFoundPage from '@/pages/errors/NotFoundPage';
import ServerErrorPage from '@/pages/errors/ServerErrorPage';

// Loading component
import LoadingSpinner from '@/components/ui/LoadingSpinner';

// React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 10, // 10 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.status >= 400 && error?.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
    },
    mutations: {
      retry: 1,
    },
  },
});

// Protected route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useIsAuthenticated();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// Admin route wrapper
const AdminRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuthStore();
  
  if (!user || user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

// Main App component
const App: React.FC = () => {
  const { checkAuthStatus, isLoading } = useAuthStore();
  const isAuthenticated = useIsAuthenticated();

  // Check authentication status on app load
  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  // Show loading spinner during auth check
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-background text-foreground">
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            
            {/* Auth routes */}
            <Route path="/auth" element={<AuthLayout />}>
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route path="forgot-password" element={<ForgotPasswordPage />} />
              <Route path="reset-password" element={<ResetPasswordPage />} />
              <Route path="verify-email" element={<VerifyEmailPage />} />
            </Route>

            {/* Legacy auth routes (backward compatibility) */}
            <Route path="/login" element={<Navigate to="/auth/login" replace />} />
            <Route path="/register" element={<Navigate to="/auth/register" replace />} />

            {/* Protected dashboard routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              <Route index element={<DashboardPage />} />
              <Route path="trading" element={<TradingPage />} />
              <Route path="portfolio" element={<PortfolioPage />} />
              <Route path="autonomous" element={<AutonomousPage />} />
              <Route path="exchanges" element={<ExchangesPage />} />
              <Route path="settings" element={<SettingsPage />} />
              
              {/* Admin only routes */}
              <Route path="admin" element={
                <AdminRoute>
                  <AdminPage />
                </AdminRoute>
              } />
            </Route>

            {/* Error routes */}
            <Route path="/500" element={<ServerErrorPage />} />
            <Route path="/404" element={<NotFoundPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>

          {/* Global toast notifications */}
          <Toaster />
        </div>
      </Router>
    </QueryClientProvider>
  );
};

export default App;