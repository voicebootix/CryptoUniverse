import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import axios, { AxiosError } from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ArrowLeft,
  Activity,
  TrendingUp,
  TrendingDown,
  Play,
  Pause,
  Settings,
  BarChart3,
  DollarSign,
  Zap,
  Target,
  Clock,
  CheckCircle,
  AlertTriangle,
  Star,
  Crown,
  Gem,
  RefreshCw,
  Eye,
  MoreVertical,
  Calendar,
  Award,
  Shield,
  Rocket
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface UserStrategy {
  strategy_id: string;
  name: string;
  category: string;
  is_ai_strategy: boolean;
  publisher_name?: string;

  // Status & Subscription
  is_active: boolean;
  subscription_type: 'welcome' | 'purchased' | 'trial';
  activated_at: string;
  expires_at?: string;

  // Pricing
  credit_cost_monthly: number;
  credit_cost_per_execution: number;

  // Performance Metrics
  total_trades: number;
  winning_trades: number;
  win_rate: number;
  total_pnl_usd: number;
  best_trade_pnl: number;
  worst_trade_pnl: number;
  current_drawdown: number;
  max_drawdown: number;
  sharpe_ratio?: number;

  // Risk & Configuration
  risk_level: string;
  allocation_percentage: number;
  max_position_size: number;
  stop_loss_percentage: number;

  // Recent Performance
  last_7_days_pnl: number;
  last_30_days_pnl: number;
  recent_trades: Array<{
    trade_id: string;
    symbol: string;
    side: string;
    pnl_usd: number;
    executed_at: string;
  }>;
}

interface PortfolioSummary {
  total_strategies: number;
  active_strategies: number;
  welcome_strategies: number;
  purchased_strategies: number;
  total_portfolio_value: number;
  total_pnl_usd: number;
  total_pnl_percentage: number;
  monthly_credit_cost: number;
  next_billing_date?: string;
  profit_potential_used: number;
  profit_potential_remaining: number;
}

interface UserStrategyPortfolio {
  summary: PortfolioSummary;
  strategies: UserStrategy[];
}

const MyStrategies: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedStrategy, setSelectedStrategy] = useState<UserStrategy | null>(null);
  const [showStrategyDetails, setShowStrategyDetails] = useState(false);
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'paused'>('all');

  // Fetch user's strategy portfolio
  const { data: portfolio, isLoading: portfolioLoading, error: portfolioError } = useQuery<UserStrategyPortfolio, AxiosError>({
    queryKey: ['user-strategy-portfolio'],
    queryFn: async () => {
      try {
        const response = await apiClient.get<UserStrategyPortfolio>('/strategies/my-portfolio');
        return response.data;
      } catch (error: unknown) {
        console.error('Failed to fetch portfolio:', error);
        // Return empty portfolio if endpoint not found
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          return {
            summary: {
              total_strategies: 0,
              active_strategies: 0,
              welcome_strategies: 0,
              purchased_strategies: 0,
              total_portfolio_value: 0,
              total_pnl_usd: 0,
              total_pnl_percentage: 0,
              monthly_credit_cost: 0,
              profit_potential_used: 0,
              profit_potential_remaining: 100
            },
            strategies: []
          };
        }
        throw error;
      }
    },
    refetchInterval: 30000,
    retry: 2,
    staleTime: 15000
  });

  // Strategy toggle mutation
  const toggleStrategyMutation = useMutation({
    mutationFn: async ({ strategyId, active }: { strategyId: string; active: boolean }) => {
      const response = await apiClient.post(`/strategies/${strategyId}/toggle`, {
        is_active: active
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      toast.success(`Strategy ${variables.active ? 'activated' : 'paused'} successfully`);
      queryClient.invalidateQueries({ queryKey: ['user-strategy-portfolio'] });
    },
    onError: (error: unknown) => {
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail || error.message
        : 'Failed to update strategy';
      toast.error(`Failed to update strategy: ${message}`);
    }
  });

  // Strategy configuration update mutation
  const updateStrategyConfigMutation = useMutation({
    mutationFn: async ({ strategyId, config }: { strategyId: string; config: any }) => {
      const response = await apiClient.put(`/strategies/${strategyId}/config`, {
        parameters: config
      });
      return response.data;
    },
    onSuccess: () => {
      toast.success('Strategy configuration updated successfully');
      queryClient.invalidateQueries({ queryKey: ['user-strategy-portfolio'] });
    },
    onError: (error: unknown) => {
      const message = axios.isAxiosError(error)
        ? error.response?.data?.detail || error.message
        : 'Failed to update configuration';
      toast.error(`Failed to update configuration: ${message}`);
    }
  });

  const getStrategyIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'derivatives': return <Rocket className="h-5 w-5" />;
      case 'spot': return <TrendingUp className="h-5 w-5" />;
      case 'algorithmic': return <Activity className="h-5 w-5" />;
      case 'portfolio': return <Target className="h-5 w-5" />;
      default: return <BarChart3 className="h-5 w-5" />;
    }
  };

  const getTierBadge = (subscriptionType: string) => {
    switch (subscriptionType) {
      case 'welcome':
        return <Badge className="bg-green-500 text-white"><Star className="h-3 w-3 mr-1" />Free</Badge>;
      case 'purchased':
        return <Badge className="bg-blue-500 text-white"><Crown className="h-3 w-3 mr-1" />Pro</Badge>;
      case 'trial':
        return <Badge className="bg-orange-500 text-white"><Clock className="h-3 w-3 mr-1" />Trial</Badge>;
      default:
        return <Badge variant="secondary">Basic</Badge>;
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low': case 'very_low': return 'text-green-500';
      case 'medium': return 'text-yellow-500';
      case 'high': case 'very_high': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const filteredStrategies = portfolio?.strategies?.filter(strategy => {
    if (filterStatus === 'all') return true;
    if (filterStatus === 'active') return strategy.is_active;
    if (filterStatus === 'paused') return !strategy.is_active;
    return true;
  }) || [];

  const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'];

  if (portfolioError) {
    let errorMessage = 'Unable to load your strategies. Please try again later.';
    let isNetworkError = false;
    let isServerError = false;
    let isTimeoutError = false;

    if (axios.isAxiosError(portfolioError)) {
      // Check for network errors (request made but no response)
      if (portfolioError.request && !portfolioError.response) {
        isNetworkError = true;
        errorMessage = 'Network connection error. Please check your internet connection.';
      }
      // Check for timeout errors
      else if (portfolioError.code === 'ECONNABORTED') {
        isTimeoutError = true;
        errorMessage = 'Request timed out. The server may be starting up. Please try again.';
      }
      // Check for server errors (5xx)
      else if (portfolioError.response?.status && portfolioError.response.status >= 500) {
        isServerError = true;
        errorMessage = 'Server error. Our servers are experiencing issues.';
      }
      // Other axios errors
      else {
        errorMessage = portfolioError.response?.data?.detail || portfolioError.message;
      }
    } else if (portfolioError instanceof Error) {
      errorMessage = portfolioError.message;
    }

    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">
            {isNetworkError ? 'Connection Problem' : isTimeoutError ? 'Request Timeout' : 'Failed to Load Strategies'}
          </h3>
          <p className="text-muted-foreground mb-4">
            {isNetworkError
              ? 'Please check your internet connection and try again.'
              : isServerError
              ? 'Our servers are experiencing issues. Please try again in a few moments.'
              : isTimeoutError
              ? 'The server is taking longer than expected. Please wait and try again.'
              : errorMessage}
          </p>
          <div className="flex gap-2 justify-center">
            <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['user-strategy-portfolio'] })}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
            <Button variant="outline" onClick={() => navigate('/dashboard/strategies')}>
              Browse Strategies
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
        <div>
          <h1 className="text-3xl font-bold">My Trading Strategies</h1>
          <p className="text-muted-foreground">Manage your active trading strategy portfolio</p>
        </div>
        <div className="ml-auto">
          <Button 
            onClick={() => navigate('/dashboard/strategies')}
            className="bg-gradient-to-r from-blue-500 to-purple-600"
          >
            <Gem className="h-4 w-4 mr-2" />
            Browse Marketplace
          </Button>
        </div>
      </div>

      {portfolioLoading ? (
        <div className="space-y-6">
          {/* Loading skeleton */}
          <div className="grid gap-4 md:grid-cols-4">
            {[1, 2, 3, 4].map(i => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <div className="h-4 bg-muted rounded animate-pulse" />
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-muted rounded animate-pulse" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ) : portfolio ? (
        <>
          {/* Portfolio Summary */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Strategies</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{portfolio.summary.active_strategies}</div>
                <p className="text-xs text-muted-foreground">
                  of {portfolio.summary.total_strategies} total
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Portfolio P&L</CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${portfolio.summary.total_pnl_usd >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {formatCurrency(portfolio.summary.total_pnl_usd)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatPercentage(portfolio.summary.total_pnl_percentage)} return
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Monthly Cost</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatNumber(portfolio.summary.monthly_credit_cost)} credits
                </div>
                <p className="text-xs text-muted-foreground">
                  {portfolio.summary.welcome_strategies} free strategies
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Profit Potential</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-500">
                  {formatCurrency(portfolio.summary.profit_potential_remaining)}
                </div>
                <p className="text-xs text-muted-foreground">
                  of {formatCurrency(portfolio.summary.profit_potential_used + portfolio.summary.profit_potential_remaining)} available
                </p>
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="strategies" className="space-y-4">
            <div className="flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="strategies">Strategies ({filteredStrategies.length})</TabsTrigger>
                <TabsTrigger value="performance">Performance</TabsTrigger>
                <TabsTrigger value="settings">Settings</TabsTrigger>
              </TabsList>
              
              <div className="flex items-center gap-2">
                <Button
                  variant={filterStatus === 'all' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterStatus('all')}
                >
                  All
                </Button>
                <Button
                  variant={filterStatus === 'active' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterStatus('active')}
                >
                  Active
                </Button>
                <Button
                  variant={filterStatus === 'paused' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilterStatus('paused')}
                >
                  Paused
                </Button>
              </div>
            </div>

            <TabsContent value="strategies" className="space-y-4">
              {filteredStrategies.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {filteredStrategies.map((strategy) => (
                    <Card 
                      key={strategy.strategy_id} 
                      className="hover:shadow-lg transition-shadow cursor-pointer"
                      onClick={() => {
                        setSelectedStrategy(strategy);
                        setShowStrategyDetails(true);
                      }}
                    >
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {getStrategyIcon(strategy.category)}
                            <div>
                              <CardTitle className="text-lg">{strategy.name}</CardTitle>
                              <CardDescription className="capitalize">
                                {strategy.category} • {strategy.publisher_name || 'CryptoUniverse AI'}
                              </CardDescription>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            {getTierBadge(strategy.subscription_type)}
                            <Switch
                              checked={strategy.is_active}
                              onCheckedChange={(checked) => {
                                toggleStrategyMutation.mutate({
                                  strategyId: strategy.strategy_id,
                                  active: checked
                                });
                              }}
                              onClick={(e) => e.stopPropagation()}
                            />
                          </div>
                        </div>
                      </CardHeader>
                      
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <div className="text-muted-foreground">Win Rate</div>
                            <div className="font-bold text-green-500">{formatPercentage(strategy.win_rate)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Total P&L</div>
                            <div className={`font-bold ${strategy.total_pnl_usd >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              {formatCurrency(strategy.total_pnl_usd)}
                            </div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Trades</div>
                            <div className="font-bold">{formatNumber(strategy.total_trades)}</div>
                          </div>
                          <div>
                            <div className="text-muted-foreground">Risk</div>
                            <div className={`font-bold ${getRiskColor(strategy.risk_level)}`}>
                              {strategy.risk_level.charAt(0).toUpperCase() + strategy.risk_level.slice(1)}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>7D P&L</span>
                            <span className={strategy.last_7_days_pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                              {formatCurrency(strategy.last_7_days_pnl)}
                            </span>
                          </div>
                          <Progress value={Math.max(0, strategy.win_rate)} className="h-2" />
                        </div>

                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">
                            Cost: {strategy.credit_cost_monthly > 0 ? `${strategy.credit_cost_monthly} credits/mo` : 'Free'}
                          </span>
                          <Badge variant={strategy.is_active ? 'default' : 'secondary'}>
                            {strategy.is_active ? 'Active' : 'Paused'}
                          </Badge>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No strategies found</h3>
                  <p className="text-muted-foreground mb-4">
                    {filterStatus === 'all' 
                      ? "You don't have any trading strategies yet" 
                      : `No ${filterStatus} strategies found`}
                  </p>
                  <Button onClick={() => navigate('/dashboard/strategy-marketplace')}>
                    Browse Strategy Marketplace
                  </Button>
                </div>
              )}
            </TabsContent>

            <TabsContent value="performance" className="space-y-4">
              <div className="grid gap-6 lg:grid-cols-2">
                {/* Portfolio Performance Chart */}
                <Card>
                  <CardHeader>
                    <CardTitle>Portfolio Performance</CardTitle>
                    <CardDescription>P&L over time across all strategies</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64 flex items-center justify-center text-muted-foreground">
                      <BarChart3 className="h-8 w-8 mr-2" />
                      Performance chart will be implemented with real data
                    </div>
                  </CardContent>
                </Card>

                {/* Strategy Allocation */}
                <Card>
                  <CardHeader>
                    <CardTitle>Strategy Allocation</CardTitle>
                    <CardDescription>Portfolio distribution by strategy</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={filteredStrategies.map(s => ({
                              name: s.name,
                              value: Math.abs(s.total_pnl_usd) || 1,
                              pnl: s.total_pnl_usd
                            }))}
                            cx="50%"
                            cy="50%"
                            innerRadius={40}
                            outerRadius={80}
                            dataKey="value"
                          >
                            {filteredStrategies.map((_, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value, name, props) => [
                            formatCurrency((props.payload as any)?.pnl || 0),
                            name
                          ]} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Top Performing Strategies */}
              <Card>
                <CardHeader>
                  <CardTitle>Strategy Performance Ranking</CardTitle>
                  <CardDescription>Ranked by total P&L performance</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Rank</TableHead>
                        <TableHead>Strategy</TableHead>
                        <TableHead>Win Rate</TableHead>
                        <TableHead>Total P&L</TableHead>
                        <TableHead>7D P&L</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {[...filteredStrategies]
                        .sort((a, b) => b.total_pnl_usd - a.total_pnl_usd)
                        .map((strategy, index) => (
                          <TableRow key={strategy.strategy_id}>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <span className="font-bold">#{index + 1}</span>
                                {index < 3 && <Award className="h-4 w-4 text-yellow-500" />}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                {getStrategyIcon(strategy.category)}
                                <div>
                                  <div className="font-medium">{strategy.name}</div>
                                  <div className="text-sm text-muted-foreground">{strategy.category}</div>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>{formatPercentage(strategy.win_rate)}</TableCell>
                            <TableCell>
                              <span className={strategy.total_pnl_usd >= 0 ? 'text-green-500' : 'text-red-500'}>
                                {formatCurrency(strategy.total_pnl_usd)}
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className={strategy.last_7_days_pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                                {formatCurrency(strategy.last_7_days_pnl)}
                              </span>
                            </TableCell>
                            <TableCell>
                              <Badge variant={strategy.is_active ? 'default' : 'secondary'}>
                                {strategy.is_active ? 'Active' : 'Paused'}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="settings" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Portfolio Settings</CardTitle>
                  <CardDescription>Global settings for your strategy portfolio</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">Auto-rebalance Portfolio</div>
                        <div className="text-sm text-muted-foreground">
                          Automatically adjust strategy allocations based on performance
                        </div>
                      </div>
                      <Switch />
                    </div>
                    
                    <Separator />
                    
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">Emergency Stop</div>
                        <div className="text-sm text-muted-foreground">
                          Pause all strategies if portfolio drawdown exceeds threshold
                        </div>
                      </div>
                      <Switch />
                    </div>
                    
                    <Separator />
                    
                    <div className="space-y-2">
                      <div className="font-medium">Risk Management</div>
                      <div className="text-sm text-muted-foreground mb-2">
                        Maximum portfolio risk allocation
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Conservative (20%)</span>
                          <span>Aggressive (80%)</span>
                        </div>
                        <div className="px-3">
                          <div className="h-2 bg-muted rounded-full relative">
                            <div 
                              className="h-2 bg-primary rounded-full" 
                              style={{ width: '50%' }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Strategy Details Modal */}
          <Dialog open={showStrategyDetails} onOpenChange={setShowStrategyDetails}>
            <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
              {selectedStrategy && (
                <>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-3">
                      {getStrategyIcon(selectedStrategy.category)}
                      {selectedStrategy.name}
                      {getTierBadge(selectedStrategy.subscription_type)}
                    </DialogTitle>
                    <DialogDescription>
                      {selectedStrategy.category} strategy • {selectedStrategy.publisher_name || 'CryptoUniverse AI'}
                    </DialogDescription>
                  </DialogHeader>
                  
                  <div className="space-y-6">
                    {/* Performance Metrics */}
                    <div className="grid gap-4 md:grid-cols-4">
                      <div className="text-center p-4 bg-muted/50 rounded-lg">
                        <div className="text-2xl font-bold text-green-500">
                          {formatPercentage(selectedStrategy.win_rate)}
                        </div>
                        <div className="text-sm text-muted-foreground">Win Rate</div>
                      </div>
                      <div className="text-center p-4 bg-muted/50 rounded-lg">
                        <div className={`text-2xl font-bold ${selectedStrategy.total_pnl_usd >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {formatCurrency(selectedStrategy.total_pnl_usd)}
                        </div>
                        <div className="text-sm text-muted-foreground">Total P&L</div>
                      </div>
                      <div className="text-center p-4 bg-muted/50 rounded-lg">
                        <div className="text-2xl font-bold">
                          {formatNumber(selectedStrategy.total_trades)}
                        </div>
                        <div className="text-sm text-muted-foreground">Total Trades</div>
                      </div>
                      <div className="text-center p-4 bg-muted/50 rounded-lg">
                        <div className="text-2xl font-bold text-orange-500">
                          {formatPercentage(selectedStrategy.max_drawdown)}
                        </div>
                        <div className="text-sm text-muted-foreground">Max Drawdown</div>
                      </div>
                    </div>

                    {/* Recent Trades */}
                    <div>
                      <h4 className="font-semibold mb-3">Recent Trades</h4>
                      <div className="space-y-2">
                        {selectedStrategy.recent_trades?.slice(0, 5).map((trade) => (
                          <div key={trade.trade_id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                            <div className="flex items-center gap-3">
                              <Badge variant="outline">{trade.side.toUpperCase()}</Badge>
                              <span className="font-medium">{trade.symbol}</span>
                            </div>
                            <div className="text-right">
                              <div className={`font-medium ${trade.pnl_usd >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                {formatCurrency(trade.pnl_usd)}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                {formatRelativeTime(new Date(trade.executed_at))}
                              </div>
                            </div>
                          </div>
                        )) || (
                          <div className="text-center py-4 text-muted-foreground">
                            No recent trades available
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Strategy Controls */}
                    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                      <div>
                        <div className="font-medium">Strategy Status</div>
                        <div className="text-sm text-muted-foreground">
                          {selectedStrategy.is_active ? 'Currently active and trading' : 'Paused - no new trades'}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          onClick={() => {
                            // Navigate to strategy configuration
                            navigate(`/dashboard/strategies/${selectedStrategy.strategy_id}/config`);
                          }}
                        >
                          <Settings className="h-4 w-4 mr-2" />
                          Configure
                        </Button>
                        <Switch
                          checked={selectedStrategy.is_active}
                          onCheckedChange={(checked) => {
                            toggleStrategyMutation.mutate({
                              strategyId: selectedStrategy.strategy_id,
                              active: checked
                            });
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </>
              )}
            </DialogContent>
          </Dialog>
        </>
      ) : null}
    </div>
  );
};

export default MyStrategies;