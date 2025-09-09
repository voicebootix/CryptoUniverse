import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  TrendingUp,
  FileText,
  Trophy,
  BarChart3,
  Activity,
  DollarSign,
  Percent,
  Clock,
  Target,
  Shield
} from 'lucide-react';

// Import existing dashboard components
import EvidenceReportingDashboard from './EvidenceReportingDashboard';
import TrustJourneyDashboard from './TrustJourneyDashboard';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { usePaperModeStore } from '@/store/paperModeStore';

// Analytics Overview Component
const AnalyticsOverview: React.FC = () => {
  const { isPaperMode } = usePaperModeStore();
  
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['performance-metrics', isPaperMode],
    queryFn: async () => {
      const endpoint = isPaperMode 
        ? '/paper-trading/stats'
        : '/portfolio/performance';
      const response = await apiClient.get(endpoint);
      return response.data.data;
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-3">
              <div className="h-4 bg-muted rounded w-1/2" />
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-muted rounded w-3/4" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const stats = [
    {
      title: 'Total Profit',
      value: formatCurrency(metrics?.totalProfit || 0),
      change: metrics?.profitChange || 0,
      icon: <DollarSign className="h-4 w-4" />,
      color: metrics?.totalProfit >= 0 ? 'text-green-500' : 'text-red-500'
    },
    {
      title: 'Win Rate',
      value: formatPercentage(metrics?.winRate || 0),
      change: metrics?.winRateChange || 0,
      icon: <Percent className="h-4 w-4" />,
      color: 'text-blue-500'
    },
    {
      title: 'Total Trades',
      value: metrics?.totalTrades || 0,
      change: metrics?.tradesChange || 0,
      icon: <Activity className="h-4 w-4" />,
      color: 'text-purple-500'
    },
    {
      title: 'Avg Trade Time',
      value: `${metrics?.avgTradeTime || 0}m`,
      change: metrics?.timeChange || 0,
      icon: <Clock className="h-4 w-4" />,
      color: 'text-orange-500'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <span className={stat.color}>{stat.icon}</span>
                {stat.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${stat.color}`}>
                {stat.value}
              </div>
              {stat.change !== 0 && (
                <p className="text-xs text-muted-foreground mt-1">
                  <span className={stat.change > 0 ? 'text-green-500' : 'text-red-500'}>
                    {stat.change > 0 ? '+' : ''}{stat.change}%
                  </span>
                  {' '}from last period
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Detailed Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Strategy Performance
            </CardTitle>
            <CardDescription>
              Performance breakdown by trading strategy
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {metrics?.strategyPerformance?.map((strategy: any, index: number) => (
                <div key={index} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{strategy.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {strategy.trades} trades
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold ${strategy.profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatCurrency(strategy.profit)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatPercentage(strategy.winRate)} win rate
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Risk Metrics
            </CardTitle>
            <CardDescription>
              Risk management and exposure analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Max Drawdown</span>
                <span className="font-bold text-red-500">
                  {formatPercentage(metrics?.maxDrawdown || 0)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Sharpe Ratio</span>
                <span className="font-bold">
                  {metrics?.sharpeRatio?.toFixed(2) || '0.00'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Risk/Reward</span>
                <span className="font-bold">
                  1:{metrics?.riskRewardRatio?.toFixed(2) || '0.00'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Profit Factor</span>
                <span className="font-bold text-green-500">
                  {metrics?.profitFactor?.toFixed(2) || '0.00'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

const PerformanceHub: React.FC = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const { isPaperMode } = usePaperModeStore();

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <BarChart3 className="h-8 w-8 text-primary" />
          Performance Hub
        </h1>
        <p className="text-muted-foreground mt-1">
          Track your {isPaperMode ? 'paper' : 'real'} trading performance and progress
        </p>
      </div>

      {/* Tabbed Interface */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="evidence" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Evidence
          </TabsTrigger>
          <TabsTrigger value="trust" className="flex items-center gap-2">
            <Trophy className="h-4 w-4" />
            Trust Journey
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <AnalyticsOverview />
        </TabsContent>

        <TabsContent value="evidence" className="mt-6">
          <EvidenceReportingDashboard />
        </TabsContent>

        <TabsContent value="trust" className="mt-6">
          <TrustJourneyDashboard />
        </TabsContent>

        <TabsContent value="analytics" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Advanced Analytics</CardTitle>
              <CardDescription>
                Deep dive into your trading patterns and performance metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Import advanced analytics content from AdvancedAnalytics.tsx if needed */}
              <div className="h-96 flex items-center justify-center text-muted-foreground">
                Advanced analytics charts and metrics will be displayed here
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default PerformanceHub;