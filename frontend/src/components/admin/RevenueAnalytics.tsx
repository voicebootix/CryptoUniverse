import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Users,
  CreditCard,
  BarChart3,
  PieChart,
  Target,
  Activity,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Percent,
  Globe,
  Zap,
  Award,
  RefreshCw,
  Download,
  Filter,
  Eye,
  AlertTriangle,
  CheckCircle,
  Clock,
  Coins,
  Wallet,
  ShoppingCart,
  UserCheck,
  TrendingUp as Growth,
  Building,
  Crown,
  Star
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  ComposedChart,
  ResponsiveContainer as RechartsResponsiveContainer
} from 'recharts';

interface RevenueMetrics {
  // Revenue Overview
  total_revenue: number;
  monthly_revenue: number;
  revenue_growth: number;
  arr: number; // Annual Recurring Revenue
  mrr: number; // Monthly Recurring Revenue
  
  // User Metrics
  total_users: number;
  active_users: number;
  premium_users: number;
  user_growth_rate: number;
  churn_rate: number;
  
  // Strategy Metrics
  total_strategies: number;
  published_strategies: number;
  strategy_publishers: number;
  avg_strategy_price: number;
  
  // Transaction Metrics
  total_transactions: number;
  transaction_volume: number;
  avg_transaction_value: number;
  
  // Profit Sharing Metrics
  total_profit_shared: number;
  profit_share_revenue: number;
  avg_profit_share_per_user: number;
  
  // Credit System Metrics
  total_credits_issued: number;
  total_credits_used: number;
  credit_conversion_rate: number;
  avg_credits_per_user: number;
}

interface RevenueBreakdown {
  revenue_stream: string;
  amount: number;
  percentage: number;
  growth: number;
  color: string;
}

interface UserSegment {
  segment: string;
  user_count: number;
  revenue_contribution: number;
  avg_revenue_per_user: number;
  churn_rate: number;
  growth_rate: number;
}

interface GeographicRevenue {
  country: string;
  country_code: string;
  revenue: number;
  user_count: number;
  avg_revenue_per_user: number;
  growth_rate: number;
}

interface RevenueTimeSeries {
  date: string;
  total_revenue: number;
  profit_share_revenue: number;
  subscription_revenue: number;
  one_time_revenue: number;
  credit_revenue: number;
  new_users: number;
  active_users: number;
  transactions: number;
}

interface TopPerformers {
  strategies: Array<{
    id: string;
    name: string;
    publisher: string;
    revenue: number;
    users: number;
    growth_rate: number;
  }>;
  publishers: Array<{
    id: string;
    name: string;
    total_revenue: number;
    total_strategies: number;
    avg_rating: number;
    growth_rate: number;
  }>;
  users: Array<{
    id: string;
    name: string;
    total_spent: number;
    active_strategies: number;
    join_date: string;
    lifetime_value: number;
  }>;
}

const RevenueAnalytics: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d' | 'ytd' | 'all'>('30d');
  const [selectedMetric, setSelectedMetric] = useState<'revenue' | 'users' | 'strategies'>('revenue');

  // Fetch revenue metrics
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useQuery({
    queryKey: ['admin-revenue-metrics', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/admin/revenue/metrics', {
        params: { period: selectedPeriod }
      });
      return response.data as RevenueMetrics;
    },
    refetchInterval: 60000
  });

  // Fetch revenue breakdown
  const { data: breakdown, isLoading: breakdownLoading } = useQuery({
    queryKey: ['admin-revenue-breakdown', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/admin/revenue/breakdown', {
        params: { period: selectedPeriod }
      });
      return response.data.breakdown as RevenueBreakdown[];
    },
    refetchInterval: 60000
  });

  // Fetch user segments
  const { data: segments, isLoading: segmentsLoading } = useQuery({
    queryKey: ['admin-user-segments', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/admin/revenue/user-segments', {
        params: { period: selectedPeriod }
      });
      return response.data.segments as UserSegment[];
    },
    refetchInterval: 300000
  });

  // Fetch geographic revenue
  const { data: geographic, isLoading: geoLoading } = useQuery({
    queryKey: ['admin-geographic-revenue', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/admin/revenue/geographic', {
        params: { period: selectedPeriod }
      });
      return response.data.countries as GeographicRevenue[];
    },
    refetchInterval: 300000
  });

  // Fetch revenue time series
  const { data: timeSeries, isLoading: timeSeriesLoading } = useQuery({
    queryKey: ['admin-revenue-timeseries', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/admin/revenue/timeseries', {
        params: { period: selectedPeriod }
      });
      return response.data.timeseries as RevenueTimeSeries[];
    },
    refetchInterval: 300000
  });

  // Fetch top performers
  const { data: topPerformers, isLoading: topPerformersLoading } = useQuery({
    queryKey: ['admin-top-performers', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/admin/revenue/top-performers', {
        params: { period: selectedPeriod }
      });
      return response.data as TopPerformers;
    },
    refetchInterval: 300000
  });

  const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'];

  const exportRevenueData = () => {
    if (!metrics || !breakdown) return;
    
    const data = {
      overview: metrics,
      breakdown: breakdown,
      segments: segments,
      geographic: geographic,
      timeSeries: timeSeries,
      topPerformers: topPerformers
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `revenue-analytics-${selectedPeriod}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (metricsError) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="text-center p-12">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load Revenue Data</h3>
            <p className="text-muted-foreground mb-4">
              {metricsError instanceof Error ? metricsError.message : 'Unable to fetch revenue analytics'}
            </p>
            <Button onClick={() => window.location.reload()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (metricsLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-8 bg-muted rounded w-64 animate-pulse" />
            <div className="h-4 bg-muted rounded w-48 animate-pulse" />
          </div>
          <div className="h-10 bg-muted rounded w-32 animate-pulse" />
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map(i => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="space-y-2">
                  <div className="h-4 bg-muted rounded w-24 animate-pulse" />
                  <div className="h-8 bg-muted rounded w-20 animate-pulse" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold tracking-tight">Revenue Analytics</h3>
          <p className="text-muted-foreground">
            Comprehensive revenue insights and business intelligence
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Select value={selectedPeriod} onValueChange={setSelectedPeriod as any}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="90d">Last 90 Days</SelectItem>
              <SelectItem value="ytd">Year to Date</SelectItem>
              <SelectItem value="all">All Time</SelectItem>
            </SelectContent>
          </Select>
          
          <Button variant="outline" onClick={exportRevenueData}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Revenue</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(metrics?.total_revenue || 0)}
                </p>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">Monthly:</span>
                  <span className="text-green-600">{formatCurrency(metrics?.monthly_revenue || 0)}</span>
                </div>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
            </div>
            
            {metrics?.revenue_growth !== undefined && (
              <div className="mt-2 flex items-center">
                {metrics.revenue_growth >= 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-green-500" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-red-500" />
                )}
                <span className={`text-sm font-medium ${metrics.revenue_growth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {formatPercentage(Math.abs(metrics.revenue_growth))} vs last period
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Monthly Recurring Revenue</p>
                <p className="text-2xl font-bold text-blue-600">
                  {formatCurrency(metrics?.mrr || 0)}
                </p>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">ARR:</span>
                  <span className="text-blue-600">{formatCurrency(metrics?.arr || 0)}</span>
                </div>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <TrendingUp className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Users</p>
                <p className="text-2xl font-bold">{formatNumber(metrics?.active_users || 0)}</p>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">Premium:</span>
                  <span className="text-purple-600">{formatNumber(metrics?.premium_users || 0)}</span>
                </div>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <Users className="h-6 w-6 text-purple-600" />
              </div>
            </div>
            
            {metrics?.user_growth_rate !== undefined && (
              <div className="mt-2 flex items-center">
                <Growth className="h-4 w-4 text-green-500" />
                <span className="text-sm font-medium text-green-500">
                  {formatPercentage(metrics.user_growth_rate)} growth
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Avg Transaction Value</p>
                <p className="text-2xl font-bold text-orange-600">
                  {formatCurrency(metrics?.avg_transaction_value || 0)}
                </p>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">Volume:</span>
                  <span className="text-orange-600">{formatCurrency(metrics?.transaction_volume || 0)}</span>
                </div>
              </div>
              <div className="p-3 bg-orange-100 rounded-full">
                <ShoppingCart className="h-6 w-6 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Additional KPIs */}
      <div className="grid gap-4 md:grid-cols-6">
        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {formatCurrency(metrics?.total_profit_shared || 0)}
              </div>
              <div className="text-xs text-muted-foreground">Total Profit Shared</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {formatNumber(metrics?.total_strategies || 0)}
              </div>
              <div className="text-xs text-muted-foreground">Total Strategies</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {formatNumber(metrics?.strategy_publishers || 0)}
              </div>
              <div className="text-xs text-muted-foreground">Active Publishers</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {formatPercentage(metrics?.churn_rate || 0)}
              </div>
              <div className="text-xs text-muted-foreground">Churn Rate</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-indigo-600">
                {formatNumber(metrics?.total_credits_issued || 0)}
              </div>
              <div className="text-xs text-muted-foreground">Credits Issued</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-pink-600">
                {formatPercentage(metrics?.credit_conversion_rate || 0)}
              </div>
              <div className="text-xs text-muted-foreground">Credit Conversion</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Revenue Overview</TabsTrigger>
          <TabsTrigger value="segments">User Segments</TabsTrigger>
          <TabsTrigger value="geographic">Geographic</TabsTrigger>
          <TabsTrigger value="top-performers">Top Performers</TabsTrigger>
        </TabsList>

        {/* Revenue Overview */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Revenue Time Series */}
            <Card>
              <CardHeader>
                <CardTitle>Revenue Trends</CardTitle>
                <CardDescription>Track revenue growth over time by stream</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={timeSeries || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip formatter={(value) => [formatCurrency(value as number), '']} />
                      <Area
                        type="monotone"
                        dataKey="profit_share_revenue"
                        stackId="1"
                        stroke="#22c55e"
                        fill="#22c55e"
                        fillOpacity={0.8}
                      />
                      <Area
                        type="monotone"
                        dataKey="subscription_revenue"
                        stackId="1"
                        stroke="#3b82f6"
                        fill="#3b82f6"
                        fillOpacity={0.8}
                      />
                      <Area
                        type="monotone"
                        dataKey="one_time_revenue"
                        stackId="1"
                        stroke="#f59e0b"
                        fill="#f59e0b"
                        fillOpacity={0.8}
                      />
                      <Area
                        type="monotone"
                        dataKey="credit_revenue"
                        stackId="1"
                        stroke="#ef4444"
                        fill="#ef4444"
                        fillOpacity={0.8}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Revenue Breakdown Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Revenue Stream Breakdown</CardTitle>
                <CardDescription>Revenue distribution by source</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPieChart>
                      <Pie
                        data={breakdown?.map((item, index) => ({
                          name: item.revenue_stream.replace('_', ' ').toUpperCase(),
                          value: item.amount,
                          fill: COLORS[index % COLORS.length]
                        })) || []}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${formatCurrency(value)}`}
                      >
                        {breakdown?.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => [formatCurrency(value as number), '']} />
                    </RechartsPieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Revenue Stream Details */}
          <Card>
            <CardHeader>
              <CardTitle>Revenue Stream Performance</CardTitle>
              <CardDescription>Detailed breakdown of each revenue source</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {breakdown?.map((stream, index) => (
                  <div key={stream.revenue_stream} className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div 
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <div>
                        <div className="font-medium">
                          {stream.revenue_stream.replace('_', ' ').toUpperCase()}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {formatPercentage(stream.percentage)} of total revenue
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="font-bold text-green-600">
                        {formatCurrency(stream.amount)}
                      </div>
                      <div className={`text-sm flex items-center ${stream.growth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {stream.growth >= 0 ? (
                          <ArrowUpRight className="h-3 w-3 mr-1" />
                        ) : (
                          <ArrowDownRight className="h-3 w-3 mr-1" />
                        )}
                        {formatPercentage(Math.abs(stream.growth))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* User Segments */}
        <TabsContent value="segments" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>User Segment Analysis</CardTitle>
              <CardDescription>Revenue contribution and behavior by user segment</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {segmentsLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3, 4].map(i => (
                      <div key={i} className="p-4 bg-muted/50 rounded-lg animate-pulse">
                        <div className="space-y-2">
                          <div className="h-4 bg-muted rounded w-1/4" />
                          <div className="h-3 bg-muted rounded w-3/4" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : segments?.map((segment, index) => (
                  <div key={segment.segment} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded">
                          {segment.segment === 'premium' && <Crown className="h-5 w-5 text-yellow-600" />}
                          {segment.segment === 'active' && <UserCheck className="h-5 w-5 text-green-600" />}
                          {segment.segment === 'casual' && <Users className="h-5 w-5 text-blue-600" />}
                          {segment.segment === 'churned' && <AlertTriangle className="h-5 w-5 text-red-600" />}
                        </div>
                        <div>
                          <div className="font-medium text-lg capitalize">{segment.segment} Users</div>
                          <div className="text-sm text-muted-foreground">
                            {formatNumber(segment.user_count)} users
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className="font-bold text-green-600 text-xl">
                          {formatCurrency(segment.revenue_contribution)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {formatCurrency(segment.avg_revenue_per_user)} per user
                        </div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Churn Rate:</span>
                        <div className={`font-medium ${segment.churn_rate > 0.1 ? 'text-red-600' : 'text-green-600'}`}>
                          {formatPercentage(segment.churn_rate)}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Growth Rate:</span>
                        <div className={`font-medium ${segment.growth_rate >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercentage(segment.growth_rate)}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Revenue Share:</span>
                        <div className="font-medium text-blue-600">
                          {formatPercentage((segment.revenue_contribution / (metrics?.total_revenue || 1)) * 100)}
                        </div>
                      </div>
                    </div>
                  </div>
                )) || []}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Geographic */}
        <TabsContent value="geographic" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Revenue by Geography</CardTitle>
              <CardDescription>Global revenue distribution and user metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {geoLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3, 4, 5].map(i => (
                      <div key={i} className="p-4 bg-muted/50 rounded-lg animate-pulse">
                        <div className="space-y-2">
                          <div className="h-4 bg-muted rounded w-1/4" />
                          <div className="h-3 bg-muted rounded w-3/4" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : geographic?.slice(0, 10).map((country, index) => (
                  <div key={country.country} className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                        {index + 1}
                      </div>
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          <span className="text-2xl">{country.country_code}</span>
                          {country.country}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {formatNumber(country.user_count)} users
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="font-bold text-green-600">
                        {formatCurrency(country.revenue)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatCurrency(country.avg_revenue_per_user)} per user
                      </div>
                      <div className={`text-xs flex items-center ${country.growth_rate >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {country.growth_rate >= 0 ? (
                          <ArrowUpRight className="h-3 w-3 mr-1" />
                        ) : (
                          <ArrowDownRight className="h-3 w-3 mr-1" />
                        )}
                        {formatPercentage(Math.abs(country.growth_rate))}
                      </div>
                    </div>
                  </div>
                )) || []}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Top Performers */}
        <TabsContent value="top-performers" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Top Strategies */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-yellow-500" />
                  Top Strategies
                </CardTitle>
                <CardDescription>Highest revenue generating strategies</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPerformersLoading ? (
                    <div className="space-y-3">
                      {[1, 2, 3].map(i => (
                        <div key={i} className="p-3 bg-muted/50 rounded animate-pulse">
                          <div className="space-y-2">
                            <div className="h-3 bg-muted rounded w-3/4" />
                            <div className="h-3 bg-muted rounded w-1/2" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : topPerformers?.strategies.slice(0, 5).map((strategy, index) => (
                    <div key={strategy.id} className="p-3 border rounded">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium text-sm">{strategy.name}</div>
                        <Badge variant="outline" className="text-xs">#{index + 1}</Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mb-2">
                        by {strategy.publisher}
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-green-600 font-medium">
                          {formatCurrency(strategy.revenue)}
                        </span>
                        <span className="text-muted-foreground">
                          {formatNumber(strategy.users)} users
                        </span>
                      </div>
                    </div>
                  )) || []}
                </div>
              </CardContent>
            </Card>

            {/* Top Publishers */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="h-5 w-5 text-purple-500" />
                  Top Publishers
                </CardTitle>
                <CardDescription>Highest earning strategy publishers</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPerformersLoading ? (
                    <div className="space-y-3">
                      {[1, 2, 3].map(i => (
                        <div key={i} className="p-3 bg-muted/50 rounded animate-pulse">
                          <div className="space-y-2">
                            <div className="h-3 bg-muted rounded w-3/4" />
                            <div className="h-3 bg-muted rounded w-1/2" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : topPerformers?.publishers.slice(0, 5).map((publisher, index) => (
                    <div key={publisher.id} className="p-3 border rounded">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium text-sm">{publisher.name}</div>
                        <Badge variant="outline" className="text-xs">#{index + 1}</Badge>
                      </div>
                      <div className="flex justify-between text-xs text-muted-foreground mb-1">
                        <span>{publisher.total_strategies} strategies</span>
                        <span className="flex items-center gap-1">
                          <Star className="h-3 w-3 text-yellow-500 fill-current" />
                          {publisher.avg_rating.toFixed(1)}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-green-600 font-medium">
                          {formatCurrency(publisher.total_revenue)}
                        </span>
                        <span className={`text-xs ${publisher.growth_rate >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {formatPercentage(publisher.growth_rate)}
                        </span>
                      </div>
                    </div>
                  )) || []}
                </div>
              </CardContent>
            </Card>

            {/* Top Users */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Crown className="h-5 w-5 text-gold-500" />
                  Top Users
                </CardTitle>
                <CardDescription>Highest spending platform users</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {topPerformersLoading ? (
                    <div className="space-y-3">
                      {[1, 2, 3].map(i => (
                        <div key={i} className="p-3 bg-muted/50 rounded animate-pulse">
                          <div className="space-y-2">
                            <div className="h-3 bg-muted rounded w-3/4" />
                            <div className="h-3 bg-muted rounded w-1/2" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : topPerformers?.users.slice(0, 5).map((user, index) => (
                    <div key={user.id} className="p-3 border rounded">
                      <div className="flex items-center justify-between mb-2">
                        <div className="font-medium text-sm">{user.name}</div>
                        <Badge variant="outline" className="text-xs">#{index + 1}</Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mb-2">
                        {user.active_strategies} active strategies • Joined {formatRelativeTime(user.join_date)}
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-green-600 font-medium">
                          {formatCurrency(user.total_spent)}
                        </span>
                        <span className="text-purple-600 text-xs">
                          LTV: {formatCurrency(user.lifetime_value)}
                        </span>
                      </div>
                    </div>
                  )) || []}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default RevenueAnalytics;