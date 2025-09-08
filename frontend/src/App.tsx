import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
// import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from '@/components/ui/toaster';
import { useAuthStore, useIsAuthenticated } from '@/store/authStore';

// Layout Components
import AuthLayout from '@/components/layout/AuthLayout';
import DashboardLayout from '@/components/layout/DashboardLayout';

// Auth Pages
import LoginPage from '@/pages/auth/LoginPage';
import RegisterPage from '@/pages/auth/RegisterPage';
import OAuthCallbackPage from '@/pages/auth/OAuthCallbackPage';
import ForgotPasswordPage from '@/pages/auth/ForgotPasswordPage';

// Dashboard Pages
import TradingDashboard from '@/pages/dashboard/TradingDashboard';
import AICommandCenter from '@/pages/dashboard/AICommandCenter';
import AIChatPage from '@/pages/dashboard/AIChatPage';
import BeastModeDashboard from '@/pages/dashboard/BeastModeDashboard';
import StrategyMarketplace from '@/pages/dashboard/StrategyMarketplace';
import MultiExchangeHub from '@/pages/dashboard/MultiExchangeHub';
import CreditBillingCenter from '@/pages/dashboard/CreditBillingCenter';
import ProfitSharingCenter from '@/pages/dashboard/ProfitSharingCenter';
import CopyTradingNetwork from '@/pages/dashboard/CopyTradingNetwork';
import TelegramCenter from '@/pages/dashboard/TelegramCenter';
import AdvancedAnalytics from '@/pages/dashboard/AdvancedAnalytics';
import TradingPage from '@/pages/dashboard/TradingPage';
import PortfolioPage from '@/pages/dashboard/PortfolioPage';
import AutonomousPage from '@/pages/dashboard/AutonomousPage';
import ExchangesPage from '@/pages/dashboard/ExchangesPage';
import SettingsPage from '@/pages/dashboard/SettingsPage';
import AdminPage from '@/pages/dashboard/AdminPage';
import MarketAnalysisPage from '@/pages/dashboard/MarketAnalysisPage';
import MasterControllerCenter from '@/pages/dashboard/MasterControllerCenter';
import TrustJourneyDashboard from '@/pages/dashboard/TrustJourneyDashboard';
import EvidenceReportingDashboard from '@/pages/dashboard/EvidenceReportingDashboard';

// Loading Component
const LoadingScreen: React.FC = () => (
  <div className="min-h-screen bg-background flex items-center justify-center">
    <div className="flex flex-col items-center space-y-4">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      <p className="text-muted-foreground">Loading CryptoUniverse...</p>
    </div>
  </div>
);

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useIsAuthenticated();
  
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />;
  }
  
  return <>{children}</>;
};

// Public Route Component (redirect if authenticated)
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useIsAuthenticated();
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (renamed from cacheTime)
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

const App: React.FC = () => {
  const isAuthenticated = useIsAuthenticated();
  const user = useAuthStore((state) => state.user);
  const tokens = useAuthStore((state) => state.tokens);

  // TODO: Initialize WebSocket connection for authenticated users
  // This will be implemented once the basic API client is working

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-background text-foreground">
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            
            {/* Login page with custom layout */}
            <Route path="/auth/login" element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            } />
            
            {/* Other auth routes with AuthLayout */}
            <Route path="/auth/*" element={
              <PublicRoute>
                <AuthLayout />
              </PublicRoute>
            }>
              <Route path="register" element={<RegisterPage />} />
              <Route path="callback" element={<OAuthCallbackPage />} />
              <Route path="forgot-password" element={<ForgotPasswordPage />} />
              <Route path="*" element={<Navigate to="/auth/login" replace />} />
            </Route>

            {/* Protected Routes */}
            <Route path="/dashboard/*" element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }>
              {/* Main Dashboard */}
              <Route index element={<TradingDashboard />} />
              
              {/* Master Controller */}
              <Route path="master-controller" element={<MasterControllerCenter />} />
              
              {/* AI Command Center */}
              <Route path="ai-command" element={<AICommandCenter />} />
              
              {/* AI Chat Manager */}
              <Route path="ai-chat" element={<AIChatPage />} />
              
              {/* Beast Mode Dashboard */}
              <Route path="beast-mode" element={<BeastModeDashboard />} />
              
                          {/* Strategy Marketplace */}
            <Route path="strategies" element={<StrategyMarketplace />} />
            
            {/* Trust Journey */}
            <Route path="trust-journey" element={<TrustJourneyDashboard />} />
            
            {/* Evidence Reporting */}
            <Route path="evidence" element={<EvidenceReportingDashboard />} />
            
            {/* Multi-Exchange Hub */}
            <Route path="exchanges-hub" element={<MultiExchangeHub />} />
            
            {/* Credit & Billing */}
            <Route path="billing" element={<ProfitSharingCenter />} />
            <Route path="credits" element={<ProfitSharingCenter />} />
            
            {/* Copy Trading Network */}
            <Route path="copy-trading" element={<CopyTradingNetwork />} />
            
            {/* Telegram Center */}
            <Route path="telegram" element={<TelegramCenter />} />
            
            {/* Advanced Analytics */}
            <Route path="analytics" element={<AdvancedAnalytics />} />
            
            {/* Market Analysis */}
            <Route path="market-analysis" element={<MarketAnalysisPage />} />
            
            {/* Trading */}
            <Route path="trading" element={<TradingPage />} />
              
              {/* Portfolio */}
              <Route path="portfolio" element={<PortfolioPage />} />
              
              {/* Autonomous Trading */}
              <Route path="autonomous" element={<AutonomousPage />} />
              
              {/* Exchange Management */}
              <Route path="exchanges" element={<ExchangesPage />} />
              
              {/* Settings */}
              <Route path="settings" element={<SettingsPage />} />
              
              {/* Admin Panel (Admin only) */}
              <Route path="admin" element={
                user?.role === 'admin' ? <AdminPage /> : <Navigate to="/dashboard" replace />
              } />
              
              {/* Catch all */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>

            {/* Catch all other routes */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>

          {/* Global Toast Notifications */}
          <Toaster />
        </div>
      </Router>

      {/* React Query DevTools (only in development) */}
      {/* {import.meta.env.DEV && (
        <ReactQueryDevtools initialIsOpen={false} position="bottom-right" />
      )} */}
    </QueryClientProvider>
  );
};

export default App;