import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  DollarSign,
  TrendingUp,
  Users,
  Eye,
  Star,
  Download,
  Calendar,
  Award,
  Activity,
  BarChart3,
  PieChart,
  Clock,
  Target,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  ArrowUpRight,
  ArrowDownRight,
  Percent,
  CreditCard,
  Wallet,
  Globe,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Filter,
  Search,
  FileText,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
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
  Bar
} from 'recharts';

interface PublisherStats {
  total_earnings: number;
  monthly_earnings: number;
  earnings_growth: number;
  total_subscribers: number;
  active_subscribers: number;
  subscriber_growth: number;
  total_strategies: number;
  published_strategies: number;
  pending_strategies: number;
  avg_strategy_rating: number;
  total_reviews: number;
  total_downloads: number;
}

interface StrategyEarnings {
  strategy_id: string;
  strategy_name: string;
  category: string;
  pricing_model: 'free' | 'one_time' | 'subscription' | 'profit_share';
  price_amount: number;
  profit_share_percentage: number;
  
  // User metrics
  total_users: number;
  active_users: number;
  churned_users: number;
  
  // Financial metrics
  total_earnings: number;
  monthly_earnings: number;
  average_monthly_per_user: number;
  
  // Performance metrics
  avg_rating: number;
  total_reviews: number;
  total_downloads: number;
  
  // Usage statistics
  avg_daily_trades_per_user: number;
  avg_monthly_return: number;
  user_satisfaction_score: number;
  
  published_at: string;
  last_updated: string;
}

interface EarningsHistory {
  date: string;
  total_earnings: number;
  profit_share_earnings: number;
  subscription_earnings: number;
  one_time_earnings: number;
  new_subscribers: number;
}

interface UserReview {
  id: string;
  strategy_id: string;
  strategy_name: string;
  user_name: string;
  rating: number;
  review_text: string;
  created_at: string;
  verified_purchase: boolean;
  helpful_votes: number;
}

interface PayoutRequest {
  id: string;
  amount: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  requested_at: string;
  processed_at?: string;
  payment_method: string;
  transaction_id?: string;
}

const PublisherDashboard: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d' | 'ytd' | 'all'>('30d');
  const [selectedStrategy, setSelectedStrategy] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch publisher statistics
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['publisher-stats', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/publisher/stats', {
        params: { period: selectedPeriod }
      });
      return response.data as PublisherStats;
    },
    refetchInterval: 60000
  });

  // Fetch strategy earnings
  const { data: strategyEarnings, isLoading: earningsLoading } = useQuery({
    queryKey: ['publisher-strategy-earnings', selectedPeriod, selectedStrategy],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/publisher/strategy-earnings', {
        params: {
          period: selectedPeriod,
          strategy_id: selectedStrategy !== 'all' ? selectedStrategy : undefined
        }
      });
      return response.data.strategies as StrategyEarnings[];
    },
    refetchInterval: 60000
  });

  // Fetch earnings history
  const { data: earningsHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['publisher-earnings-history', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/publisher/earnings-history', {
        params: { period: selectedPeriod }
      });
      return response.data.earnings as EarningsHistory[];
    },
    refetchInterval: 300000 // 5 minutes
  });

  // Fetch strategy reviews summary (simplified)
  const { data: reviewsData, isLoading: reviewsLoading } = useQuery({
    queryKey: ['publisher-reviews'],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/publisher/reviews');
      return response.data;
    },
    refetchInterval: 300000
  });

  // Use actual strategy review summaries from backend
  const strategyReviews = reviewsData?.reviews || [];
  const overallRating = reviewsData?.overall_rating || 0;
  const totalReviews = reviewsData?.total_reviews || 0;

  // Fetch payout history
  const { data: payoutsData, isLoading: payoutsLoading } = useQuery({
    queryKey: ['publisher-payouts'],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/publisher/payouts');
      return response.data;
    },
    refetchInterval: 60000
  });

  // Map payouts using only real backend fields, show "—" for missing data
  const payouts = payoutsData?.payouts?.map((payout: any, index: number) => ({
    // Use backend id if available, otherwise show placeholder
    id: payout.id || "—",
    amount: payout.amount,
    status: payout.status,
    // Map date fields from backend
    requested_at: payout.date || payout.requested_at || "—",
    processed_at: payout.processed_at || (payout.status === 'completed' ? payout.date : "—"),
    // Use backend payment method or show placeholder
    payment_method: payout.method || payout.payment_method || "—",
    // Use backend transaction ID or show placeholder
    transaction_id: payout.transaction_id || "—"
  })) || [];

  const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  const filteredEarnings = strategyEarnings?.filter(strategy =>
    strategy.strategy_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    strategy.category.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const totalEarningsByModel = strategyEarnings?.reduce((acc, strategy) => {
    acc[strategy.pricing_model] = (acc[strategy.pricing_model] || 0) + strategy.total_earnings;
    return acc;
  }, {} as Record<string, number>) || {};

  const exportEarningsData = () => {
    if (!strategyEarnings) return;
    
    const csvData = strategyEarnings.map(strategy => ({
      'Strategy Name': strategy.strategy_name,
      Category: strategy.category,
      'Pricing Model': strategy.pricing_model,
      'Total Users': strategy.total_users,
      'Active Users': strategy.active_users,
      'Total Earnings': strategy.total_earnings,
      'Monthly Earnings': strategy.monthly_earnings,
      'Average Rating': strategy.avg_rating,
      'Total Reviews': strategy.total_reviews,
      'Total Downloads': strategy.total_downloads,
      'Published Date': strategy.published_at
    }));

    const csv = [
      Object.keys(csvData[0]).join(','),
      ...csvData.map(row => Object.values(row).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `publisher-earnings-${selectedPeriod}-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (statsError) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="text-center p-12">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load Publisher Data</h3>
            <p className="text-muted-foreground mb-4">
              {statsError instanceof Error ? statsError.message : 'Unable to fetch publisher dashboard data'}
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

  if (statsLoading) {
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
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Publisher Dashboard</h2>
          <p className="text-muted-foreground">
            Track your strategy performance, earnings, and user engagement
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
          
          <Button variant="outline" onClick={exportEarningsData}>
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
                <p className="text-sm font-medium text-muted-foreground">Total Earnings</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(stats?.total_earnings || 0)}
                </p>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">Monthly:</span>
                  <span className="text-green-600">{formatCurrency(stats?.monthly_earnings || 0)}</span>
                </div>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
            </div>
            
            {stats?.earnings_growth !== undefined && (
              <div className="mt-2 flex items-center">
                {stats.earnings_growth >= 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-green-500" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-red-500" />
                )}
                <span className={`text-sm font-medium ${stats.earnings_growth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {formatPercentage(Math.abs(stats.earnings_growth))} vs last period
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Subscribers</p>
                <p className="text-2xl font-bold">{formatNumber(stats?.total_subscribers || 0)}</p>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">Active:</span>
                  <span className="text-blue-600">{formatNumber(stats?.active_subscribers || 0)}</span>
                </div>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
            </div>
            
            {stats?.subscriber_growth !== undefined && (
              <div className="mt-2 flex items-center">
                {stats.subscriber_growth >= 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-green-500" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-red-500" />
                )}
                <span className={`text-sm font-medium ${stats.subscriber_growth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {formatPercentage(Math.abs(stats.subscriber_growth))} vs last period
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Published Strategies</p>
                <p className="text-2xl font-bold">{stats?.published_strategies || 0}</p>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">Pending:</span>
                  <span className="text-yellow-600">{stats?.pending_strategies || 0}</span>
                </div>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <FileText className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Average Rating</p>
                <div className="flex items-center gap-2">
                  <p className="text-2xl font-bold">{stats?.avg_strategy_rating?.toFixed(1) || '0.0'}</p>
                  <Star className="h-5 w-5 text-yellow-500 fill-current" />
                </div>
                <div className="flex items-center text-xs text-muted-foreground">
                  <span className="mr-1">Reviews:</span>
                  <span>{formatNumber(stats?.total_reviews || 0)}</span>
                </div>
              </div>
              <div className="p-3 bg-yellow-100 rounded-full">
                <Award className="h-6 w-6 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="earnings" className="space-y-6">
        <TabsList>
          <TabsTrigger value="earnings">Earnings Overview</TabsTrigger>
          <TabsTrigger value="strategies">Strategy Performance</TabsTrigger>
          <TabsTrigger value="reviews">User Reviews</TabsTrigger>
          <TabsTrigger value="payouts">Payouts</TabsTrigger>
        </TabsList>

        {/* Earnings Overview */}
        <TabsContent value="earnings" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Earnings Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Earnings Over Time</CardTitle>
                <CardDescription>Track your earnings growth and trends</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={earningsHistory || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip formatter={(value) => [formatCurrency(value as number), 'Earnings']} />
                      <Area
                        type="monotone"
                        dataKey="total_earnings"
                        stackId="1"
                        stroke="#22c55e"
                        fill="#22c55e"
                        fillOpacity={0.8}
                      />
                      <Area
                        type="monotone"
                        dataKey="profit_share_earnings"
                        stackId="1"
                        stroke="#3b82f6"
                        fill="#3b82f6"
                        fillOpacity={0.8}
                      />
                      <Area
                        type="monotone"
                        dataKey="subscription_earnings"
                        stackId="1"
                        stroke="#f59e0b"
                        fill="#f59e0b"
                        fillOpacity={0.8}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Earnings by Model */}
            <Card>
              <CardHeader>
                <CardTitle>Earnings by Pricing Model</CardTitle>
                <CardDescription>Revenue breakdown by pricing strategy</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPieChart>
                      <Pie
                        data={Object.entries(totalEarningsByModel).map(([model, earnings]) => ({
                          name: model.replace('_', ' ').toUpperCase(),
                          value: earnings,
                          fill: COLORS[Object.keys(totalEarningsByModel).indexOf(model) % COLORS.length]
                        }))}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${formatCurrency(value)}`}
                      >
                        {Object.entries(totalEarningsByModel).map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => [formatCurrency(value as number), 'Earnings']} />
                    </RechartsPieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Earnings Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Earnings Summary</CardTitle>
              <CardDescription>Detailed breakdown of your revenue streams</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(totalEarningsByModel).map(([model, earnings]) => (
                  <div key={model} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded">
                        {model === 'profit_share' && <Percent className="h-4 w-4 text-primary" />}
                        {model === 'subscription' && <Calendar className="h-4 w-4 text-primary" />}
                        {model === 'one_time' && <CreditCard className="h-4 w-4 text-primary" />}
                        {model === 'free' && <Globe className="h-4 w-4 text-primary" />}
                      </div>
                      <div>
                        <div className="font-medium">{model.replace('_', ' ').toUpperCase()}</div>
                        <div className="text-sm text-muted-foreground">
                          {strategyEarnings?.filter(s => s.pricing_model === model).length || 0} strategies
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-green-600">{formatCurrency(earnings)}</div>
                      <div className="text-sm text-muted-foreground">
                        {formatPercentage((earnings / (stats?.total_earnings || 1)) * 100)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Strategy Performance */}
        <TabsContent value="strategies" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Strategy Performance</span>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
                    <Input
                      placeholder="Search strategies..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 w-64"
                    />
                  </div>
                </div>
              </CardTitle>
            </CardHeader>
            
            <CardContent>
              <div className="space-y-4">
                {earningsLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="p-4 bg-muted/50 rounded-lg animate-pulse">
                        <div className="space-y-2">
                          <div className="h-4 bg-muted rounded w-1/4" />
                          <div className="h-3 bg-muted rounded w-3/4" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : filteredEarnings.length === 0 ? (
                  <div className="text-center p-12">
                    <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No Strategies Found</h3>
                    <p className="text-muted-foreground">
                      {searchQuery ? 'No strategies match your search criteria.' : 'You have no published strategies yet.'}
                    </p>
                  </div>
                ) : (
                  filteredEarnings.map((strategy) => (
                    <div key={strategy.strategy_id} className="p-4 border rounded-lg space-y-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3">
                            <h4 className="font-semibold text-lg">{strategy.strategy_name}</h4>
                            <Badge variant="outline">{strategy.category}</Badge>
                            <Badge variant="outline">{strategy.pricing_model.replace('_', ' ')}</Badge>
                          </div>
                          <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                            <span>Published {formatRelativeTime(new Date(strategy.published_at))}</span>
                            <span>•</span>
                            <div className="flex items-center gap-1">
                              <Star className="h-3 w-3 text-yellow-500 fill-current" />
                              <span>{strategy.avg_rating.toFixed(1)} ({strategy.total_reviews} reviews)</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="text-right">
                          <div className="text-xl font-bold text-green-600">
                            {formatCurrency(strategy.total_earnings)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {formatCurrency(strategy.monthly_earnings)}/month
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Total Users:</span>
                          <div className="font-medium">{formatNumber(strategy.total_users)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Active Users:</span>
                          <div className="font-medium text-green-600">{formatNumber(strategy.active_users)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Downloads:</span>
                          <div className="font-medium">{formatNumber(strategy.total_downloads)}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Avg Monthly Return:</span>
                          <div className="font-medium text-blue-600">
                            {formatPercentage(strategy.avg_monthly_return)}
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>User Satisfaction</span>
                          <span>{strategy.user_satisfaction_score}/100</span>
                        </div>
                        <Progress value={strategy.user_satisfaction_score} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reviews Summary */}
        <TabsContent value="reviews" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Reviews Summary</CardTitle>
              <CardDescription>Overview of reviews across all your published strategies</CardDescription>
            </CardHeader>

            <CardContent>
              <div className="space-y-6">
                {reviewsLoading ? (
                  <div className="space-y-4 animate-pulse">
                    <div className="h-20 bg-muted rounded" />
                    <div className="h-40 bg-muted rounded" />
                  </div>
                ) : !strategyReviews || strategyReviews.length === 0 ? (
                  <div className="text-center p-12">
                    <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No Reviews Yet</h3>
                    <p className="text-muted-foreground">
                      Your published strategies haven't received any reviews yet.
                    </p>
                  </div>
                ) : (
                  <>
                    {/* Overall Review Stats */}
                    <div className="grid gap-4 md:grid-cols-3">
                      <Card>
                        <CardContent className="p-4 text-center">
                          <div className="flex items-center justify-center gap-2 mb-2">
                            <Star className="h-5 w-5 text-yellow-500 fill-current" />
                            <span className="text-2xl font-bold">{overallRating.toFixed(1)}</span>
                          </div>
                          <p className="text-sm text-muted-foreground">Overall Rating</p>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardContent className="p-4 text-center">
                          <div className="text-2xl font-bold mb-2">{totalReviews}</div>
                          <p className="text-sm text-muted-foreground">Total Reviews</p>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardContent className="p-4 text-center">
                          <div className="text-2xl font-bold mb-2">{strategyReviews.length}</div>
                          <p className="text-sm text-muted-foreground">Reviewed Strategies</p>
                        </CardContent>
                      </Card>
                    </div>

                    {/* Strategy-by-Strategy Breakdown */}
                    <div>
                      <h4 className="font-medium mb-4">Reviews by Strategy</h4>
                      <div className="space-y-3">
                        {strategyReviews.map((strategy: any, index: number) => (
                          <div key={index} className="p-4 border rounded-lg">
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <h5 className="font-medium">{strategy.strategy_name}</h5>
                                <div className="flex items-center gap-3 mt-1">
                                  <div className="flex items-center gap-1">
                                    <Star className="h-4 w-4 text-yellow-500 fill-current" />
                                    <span className="font-medium">{strategy.average_rating.toFixed(1)}</span>
                                  </div>
                                  <span className="text-sm text-muted-foreground">
                                    {strategy.total_reviews} review{strategy.total_reviews !== 1 ? 's' : ''}
                                  </span>
                                </div>
                              </div>
                              <div className="text-right">
                                <Progress
                                  value={(strategy.average_rating / 5) * 100}
                                  className="w-20"
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Payouts */}
        <TabsContent value="payouts" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Payout History</span>
                <Button variant="outline" size="sm">
                  <Wallet className="h-4 w-4 mr-2" />
                  Request Payout
                </Button>
              </CardTitle>
              <CardDescription>
                Track your payout requests and payment history
              </CardDescription>
            </CardHeader>
            
            <CardContent>
              <div className="space-y-4">
                {payoutsLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="p-4 bg-muted/50 rounded-lg animate-pulse">
                        <div className="space-y-2">
                          <div className="h-4 bg-muted rounded w-1/4" />
                          <div className="h-3 bg-muted rounded w-3/4" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : !payouts || payouts.length === 0 ? (
                  <div className="text-center p-12">
                    <CreditCard className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No Payouts Yet</h3>
                    <p className="text-muted-foreground">
                      You haven't requested any payouts yet. Request your first payout when ready.
                    </p>
                  </div>
                ) : (
                  payouts.map((payout) => (
                    <div key={payout.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div>
                        <div className="font-medium">{formatCurrency(payout.amount)}</div>
                        <div className="text-sm text-muted-foreground">
                          Requested {formatRelativeTime(new Date(payout.requested_at))}
                          {payout.processed_at && ` • Processed ${formatRelativeTime(new Date(payout.processed_at))}`}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {payout.payment_method}
                          {payout.transaction_id && payout.transaction_id !== "—" && ` • ${payout.transaction_id}`}
                        </div>
                      </div>
                      
                      <Badge
                        variant={
                          payout.status === 'completed' ? 'default' :
                          payout.status === 'processing' ? 'secondary' :
                          payout.status === 'failed' ? 'destructive' : 'outline'
                        }
                      >
                        {payout.status.toUpperCase()}
                      </Badge>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default PublisherDashboard;