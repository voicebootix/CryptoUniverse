import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Store,
  TrendingUp,
  TrendingDown,
  Zap,
  Target,
  BarChart3,
  Activity,
  Shield,
  Clock,
  DollarSign,
  Star,
  Play,
  Eye,
  Filter,
  Search,
  ChevronDown,
  ArrowUpRight,
  ArrowDownRight,
  Layers,
  Cpu,
  Brain,
  Crown,
  Rocket,
  Bot,
  Sparkles,
  LineChart as LineChartIcon,
  CheckCircle,
  ShoppingCart,
  Users,
  AlertTriangle,
  RefreshCw,
  ArrowLeft,
  Gem,
  Award,
  TrendingUp as TrendUp
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface MarketplaceStrategy {
  strategy_id: string;
  name: string;
  description: string;
  category: string;
  subcategory?: string;
  
  // Publisher Info
  publisher_id: string;
  publisher_name: string;
  publisher_verified: boolean;
  publisher_avatar_url?: string;
  
  // Pricing & Access
  credit_cost_monthly: number;
  credit_cost_per_execution: number;
  pricing_model: 'monthly' | 'per_execution' | 'free';
  tier: 'free' | 'basic' | 'pro' | 'enterprise';
  
  // Performance Metrics (Real from backend)
  total_subscribers: number;
  win_rate: number;
  total_trades: number;
  avg_return_per_trade: number;
  max_drawdown: number;
  sharpe_ratio?: number;
  volatility: number;
  
  // Risk Assessment
  risk_level: 'very_low' | 'low' | 'medium' | 'high' | 'very_high';
  complexity_score: number;
  min_account_balance: number;
  
  // Availability & Status
  is_active: boolean;
  is_backtested: boolean;
  backtest_required_days: number;
  last_performance_update: string;
  
  // User Status
  user_has_purchased: boolean;
  user_can_afford: boolean;
  requires_higher_tier: boolean;
  
  // Performance History
  performance_chart: Array<{
    date: string;
    cumulative_return: number;
    daily_return: number;
  }>;
  
  // Tags & Features
  tags: string[];
  features: string[];
  supported_exchanges: string[];
  min_trade_amount: number;
}

interface MarketplaceFilters {
  search: string;
  category: string;
  risk_level: string;
  pricing_model: string;
  min_win_rate: number;
  max_credit_cost: number;
  sort_by: 'performance' | 'popularity' | 'newest' | 'price_low' | 'price_high';
}

interface UserCredits {
  available_credits: number;
  total_credits: number;
  profit_potential: number;
}

const StrategyMarketplace: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [selectedStrategy, setSelectedStrategy] = useState<MarketplaceStrategy | null>(null);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [filters, setFilters] = useState<MarketplaceFilters>({
    search: '',
    category: 'all',
    risk_level: 'all',
    pricing_model: 'all',
    min_win_rate: 0,
    max_credit_cost: 1000,
    sort_by: 'performance'
  });

  // Fetch marketplace strategies with real API
  const { data: strategies, isLoading: strategiesLoading, error: strategiesError } = useQuery({
    queryKey: ['marketplace-strategies', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      
      if (filters.search) params.append('search', filters.search);
      if (filters.category !== 'all') params.append('category', filters.category);
      if (filters.risk_level !== 'all') params.append('risk_level', filters.risk_level);
      if (filters.pricing_model !== 'all') params.append('pricing_model', filters.pricing_model);
      if (filters.min_win_rate > 0) params.append('min_win_rate', filters.min_win_rate.toString());
      if (filters.max_credit_cost < 1000) params.append('max_credit_cost', filters.max_credit_cost.toString());
      params.append('sort_by', filters.sort_by);
      params.append('include_performance', 'true');
      
      const response = await apiClient.get(`/strategies/marketplace?${params}`);
      return response.data.strategies as MarketplaceStrategy[];
    },
    refetchInterval: 60000, // Refresh every minute
    retry: 2,
    staleTime: 30000
  });

  // Fetch user credits
  const { data: userCredits } = useQuery({
    queryKey: ['user-credits'],
    queryFn: async () => {
      const response = await apiClient.get('/credits/balance');
      return response.data as UserCredits;
    },
    refetchInterval: 30000,
    retry: 2
  });

  // Purchase strategy mutation
  const purchaseStrategyMutation = useMutation({
    mutationFn: async (strategyId: string) => {
      const response = await apiClient.post(`/strategies/purchase`, { strategy_id: strategyId });
      return response.data;
    },
    onSuccess: (data, strategyId) => {
      toast.success(`Strategy purchased successfully! ${data.credits_deducted} credits deducted.`);
      queryClient.invalidateQueries({ queryKey: ['marketplace-strategies'] });
      queryClient.invalidateQueries({ queryKey: ['user-credits'] });
      queryClient.invalidateQueries({ queryKey: ['user-strategy-portfolio'] });
      setShowStrategyModal(false);
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || error.message;
      toast.error(`Purchase failed: ${message}`);
    }
  });

  const getStrategyIcon = (category: string) => {
    const icons: Record<string, React.ReactNode> = {
      'derivatives': <Rocket className="h-5 w-5 text-orange-500" />,
      'spot': <TrendingUp className="h-5 w-5 text-green-500" />,
      'algorithmic': <Bot className="h-5 w-5 text-blue-500" />,
      'portfolio': <Target className="h-5 w-5 text-purple-500" />,
      'ai_powered': <Brain className="h-5 w-5 text-pink-500" />,
      'arbitrage': <Activity className="h-5 w-5 text-yellow-500" />
    };
    return icons[category.toLowerCase()] || <BarChart3 className="h-5 w-5 text-gray-500" />;
  };

  const getTierBadge = (tier: string) => {
    const configs = {
      free: { variant: 'secondary' as const, icon: Star, label: 'Free' },
      basic: { variant: 'outline' as const, icon: Zap, label: 'Basic' },
      pro: { variant: 'default' as const, icon: Crown, label: 'Pro' },
      enterprise: { variant: 'destructive' as const, icon: Gem, label: 'Enterprise' }
    };
    
    const config = configs[tier as keyof typeof configs] || configs.basic;
    const Icon = config.icon;
    
    return (
      <Badge variant={config.variant} className="flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {config.label}
      </Badge>
    );
  };

  const getRiskColor = (risk: string) => {
    const colors: Record<string, string> = {
      very_low: 'text-green-600',
      low: 'text-green-500',
      medium: 'text-yellow-500',
      high: 'text-orange-500',
      very_high: 'text-red-500'
    };
    return colors[risk] || 'text-gray-500';
  };

  const handlePurchaseStrategy = (strategy: MarketplaceStrategy) => {
    if (strategy.user_has_purchased) {
      toast.info('You already own this strategy');
      return;
    }
    
    if (!strategy.user_can_afford) {
      const requiredCredits = strategy.pricing_model === 'per_execution' 
        ? strategy.credit_cost_per_execution 
        : strategy.credit_cost_monthly || 0;
      toast.error(`Insufficient credits. You need ${requiredCredits} credits but only have ${userCredits?.available_credits || 0}.`);
      return;
    }
    
    if (strategy.requires_higher_tier) {
      toast.error('This strategy requires a higher subscription tier');
      return;
    }
    
    purchaseStrategyMutation.mutate(strategy.strategy_id);
  };

  if (strategiesError) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center py-12">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to Load Marketplace</h3>
          <p className="text-muted-foreground mb-4">
            {strategiesError instanceof Error ? strategiesError.message : 'Unable to fetch strategies'}
          </p>
          <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['marketplace-strategies'] })}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
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
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Store className="h-8 w-8 text-primary" />
              Strategy Marketplace
            </h1>
            <p className="text-muted-foreground">
              Discover and purchase professional trading strategies
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {userCredits && (
            <div className="text-right">
              <div className="text-sm text-muted-foreground">Available Credits</div>
              <div className="text-lg font-bold text-green-500">
                {formatNumber(userCredits.available_credits)}
              </div>
            </div>
          )}
          <Button onClick={() => navigate('/dashboard/my-strategies')}>
            <Eye className="h-4 w-4 mr-2" />
            My Strategies
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filter Strategies</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-6">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search strategies..."
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="pl-10"
              />
            </div>
            
            <Select value={filters.category} onValueChange={(value) => setFilters(prev => ({ ...prev, category: value }))}>
              <SelectTrigger>
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                <SelectItem value="derivatives">Derivatives</SelectItem>
                <SelectItem value="spot">Spot Trading</SelectItem>
                <SelectItem value="algorithmic">Algorithmic</SelectItem>
                <SelectItem value="portfolio">Portfolio</SelectItem>
                <SelectItem value="ai_powered">AI Powered</SelectItem>
                <SelectItem value="arbitrage">Arbitrage</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={filters.risk_level} onValueChange={(value) => setFilters(prev => ({ ...prev, risk_level: value }))}>
              <SelectTrigger>
                <SelectValue placeholder="Risk Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Risk Levels</SelectItem>
                <SelectItem value="very_low">Very Low</SelectItem>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="very_high">Very High</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={filters.pricing_model} onValueChange={(value) => setFilters(prev => ({ ...prev, pricing_model: value }))}>
              <SelectTrigger>
                <SelectValue placeholder="Pricing" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Pricing</SelectItem>
                <SelectItem value="free">Free</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="per_execution">Per Trade</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={filters.sort_by} onValueChange={(value) => setFilters(prev => ({ ...prev, sort_by: value as any }))}>
              <SelectTrigger>
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="performance">Best Performance</SelectItem>
                <SelectItem value="popularity">Most Popular</SelectItem>
                <SelectItem value="newest">Newest</SelectItem>
                <SelectItem value="price_low">Price: Low to High</SelectItem>
                <SelectItem value="price_high">Price: High to Low</SelectItem>
              </SelectContent>
            </Select>
            
            <Button
              variant="outline"
              onClick={() => setFilters({
                search: '',
                category: 'all',
                risk_level: 'all',
                pricing_model: 'all',
                min_win_rate: 0,
                max_credit_cost: 1000,
                sort_by: 'performance'
              })}
            >
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Strategy Grid */}
      {strategiesLoading ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-6 bg-muted rounded" />
                <div className="h-4 bg-muted rounded w-3/4" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-4 bg-muted rounded" />
                  <div className="h-4 bg-muted rounded w-1/2" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : strategies && strategies.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {strategies.map((strategy) => (
            <motion.div
              key={strategy.strategy_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Card 
                className="hover:shadow-lg transition-all cursor-pointer h-full"
                onClick={() => {
                  setSelectedStrategy(strategy);
                  setShowStrategyModal(true);
                }}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      {getStrategyIcon(strategy.category)}
                      <div>
                        <CardTitle className="text-lg">{strategy.name}</CardTitle>
                        <CardDescription>
                          by {strategy.publisher_name}
                          {strategy.publisher_verified && (
                            <CheckCircle className="inline h-4 w-4 ml-1 text-blue-500" />
                          )}
                        </CardDescription>
                      </div>
                    </div>
                    {getTierBadge(strategy.tier)}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{strategy.category}</Badge>
                    <Badge variant="outline" className={getRiskColor(strategy.risk_level)}>
                      {strategy.risk_level.replace('_', ' ')} risk
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {strategy.description}
                  </p>

                  {/* Performance Metrics */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-muted-foreground">Win Rate</div>
                      <div className="font-bold text-green-500">
                        {formatPercentage(strategy.win_rate)}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Subscribers</div>
                      <div className="font-bold">{formatNumber(strategy.total_subscribers)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Avg Return</div>
                      <div className="font-bold text-blue-500">
                        {formatPercentage(strategy.avg_return_per_trade)}
                      </div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Max Drawdown</div>
                      <div className="font-bold text-red-500">
                        {formatPercentage(strategy.max_drawdown)}
                      </div>
                    </div>
                  </div>

                  {/* Performance Chart */}
                  {strategy.performance_chart && strategy.performance_chart.length > 0 && (
                    <div className="h-20">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={strategy.performance_chart}>
                          <Line
                            type="monotone"
                            dataKey="cumulative_return"
                            stroke="#22c55e"
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <Separator />

                  {/* Pricing and Action */}
                  <div className="flex items-center justify-between">
                    <div>
                      {strategy.pricing_model === 'free' ? (
                        <span className="text-lg font-bold text-green-500">Free</span>
                      ) : strategy.pricing_model === 'monthly' ? (
                        <div>
                          <span className="text-lg font-bold">
                            {formatNumber(strategy.credit_cost_monthly)} credits
                          </span>
                          <span className="text-sm text-muted-foreground">/month</span>
                        </div>
                      ) : (
                        <div>
                          <span className="text-lg font-bold">
                            {formatNumber(strategy.credit_cost_per_execution)} credits
                          </span>
                          <span className="text-sm text-muted-foreground">/trade</span>
                        </div>
                      )}
                    </div>
                    
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!strategy.user_can_afford) {
                          navigate('/dashboard/credits/purchase');
                        } else {
                          handlePurchaseStrategy(strategy);
                        }
                      }}
                      disabled={strategy.user_has_purchased || purchaseStrategyMutation.isPending}
                      className={strategy.user_has_purchased ? 'bg-green-500' : ''}
                    >
                      {strategy.user_has_purchased ? (
                        <>
                          <CheckCircle className="h-4 w-4 mr-2" />
                          Owned
                        </>
                      ) : purchaseStrategyMutation.isPending ? (
                        'Purchasing...'
                      ) : !strategy.user_can_afford ? (
                        <>
                          <DollarSign className="h-4 w-4 mr-2" />
                          Need Credits
                        </>
                      ) : (
                        <>
                          <ShoppingCart className="h-4 w-4 mr-2" />
                          {strategy.pricing_model === 'free' ? 'Add' : 'Purchase'}
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Store className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No strategies found</h3>
          <p className="text-muted-foreground mb-4">
            Try adjusting your filters or search terms
          </p>
          <Button
            onClick={() => setFilters(prev => ({ ...prev, search: '', category: 'all', risk_level: 'all' }))}
          >
            Clear Filters
          </Button>
        </div>
      )}

      {/* Strategy Details Modal */}
      <Dialog open={showStrategyModal} onOpenChange={setShowStrategyModal}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          {selectedStrategy && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  {getStrategyIcon(selectedStrategy.category)}
                  {selectedStrategy.name}
                  {getTierBadge(selectedStrategy.tier)}
                </DialogTitle>
                <DialogDescription>
                  by {selectedStrategy.publisher_name}
                  {selectedStrategy.publisher_verified && (
                    <CheckCircle className="inline h-4 w-4 ml-1 text-blue-500" />
                  )}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6">
                <p className="text-muted-foreground">{selectedStrategy.description}</p>

                {/* Key Metrics */}
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="text-center p-4 bg-muted/50 rounded-lg">
                    <div className="text-2xl font-bold text-green-500">
                      {formatPercentage(selectedStrategy.win_rate)}
                    </div>
                    <div className="text-sm text-muted-foreground">Win Rate</div>
                  </div>
                  <div className="text-center p-4 bg-muted/50 rounded-lg">
                    <div className="text-2xl font-bold">
                      {formatNumber(selectedStrategy.total_subscribers)}
                    </div>
                    <div className="text-sm text-muted-foreground">Subscribers</div>
                  </div>
                  <div className="text-center p-4 bg-muted/50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-500">
                      {formatPercentage(selectedStrategy.avg_return_per_trade)}
                    </div>
                    <div className="text-sm text-muted-foreground">Avg Return</div>
                  </div>
                  <div className="text-center p-4 bg-muted/50 rounded-lg">
                    <div className="text-2xl font-bold text-red-500">
                      {formatPercentage(selectedStrategy.max_drawdown)}
                    </div>
                    <div className="text-sm text-muted-foreground">Max Drawdown</div>
                  </div>
                </div>

                {/* Performance Chart */}
                {selectedStrategy.performance_chart && selectedStrategy.performance_chart.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-3">Performance History</h4>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={selectedStrategy.performance_chart}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="date" />
                          <YAxis />
                          <Tooltip />
                          <Line
                            type="monotone"
                            dataKey="cumulative_return"
                            stroke="#22c55e"
                            strokeWidth={2}
                            name="Cumulative Return"
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Strategy Details */}
                <div className="grid gap-6 md:grid-cols-2">
                  <div>
                    <h4 className="font-semibold mb-3">Strategy Details</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Category:</span>
                        <span>{selectedStrategy.category}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Risk Level:</span>
                        <span className={getRiskColor(selectedStrategy.risk_level)}>
                          {selectedStrategy.risk_level.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total Trades:</span>
                        <span>{formatNumber(selectedStrategy.total_trades)}</span>
                      </div>
                      {(selectedStrategy.sharpe_ratio !== null && selectedStrategy.sharpe_ratio !== undefined && Number.isFinite(selectedStrategy.sharpe_ratio)) && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Sharpe Ratio:</span>
                          <span>{selectedStrategy.sharpe_ratio.toFixed(2)}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Min Account:</span>
                        <span>{formatCurrency(selectedStrategy.min_account_balance)}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-semibold mb-3">Features</h4>
                    <div className="space-y-2">
                      {selectedStrategy.features.map((feature, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Tags */}
                {selectedStrategy.tags && selectedStrategy.tags.length > 0 && (
                  <div>
                    <h4 className="font-semibold mb-3">Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedStrategy.tags.map((tag, index) => (
                        <Badge key={index} variant="outline">{tag}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Purchase Section */}
                <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                  <div>
                    <div className="font-semibold">
                      {selectedStrategy.pricing_model === 'free' ? 'Free Strategy' : 
                       selectedStrategy.pricing_model === 'monthly' 
                         ? `${formatNumber(selectedStrategy.credit_cost_monthly)} credits/month`
                         : `${formatNumber(selectedStrategy.credit_cost_per_execution)} credits/trade`}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {selectedStrategy.user_has_purchased ? 'You own this strategy' :
                       !selectedStrategy.user_can_afford ? (() => {
                         const requiredCredits = selectedStrategy.pricing_model === 'per_execution' 
                           ? selectedStrategy.credit_cost_per_execution 
                           : selectedStrategy.credit_cost_monthly || 0;
                         return `Need ${requiredCredits - (userCredits?.available_credits || 0)} more credits`;
                       })() :
                       selectedStrategy.requires_higher_tier ? 'Requires higher subscription tier' :
                       'Ready to purchase'}
                    </div>
                  </div>
                  
                  <Button
                    onClick={() => handlePurchaseStrategy(selectedStrategy)}
                    disabled={selectedStrategy.user_has_purchased || !selectedStrategy.user_can_afford || purchaseStrategyMutation.isPending}
                    className={selectedStrategy.user_has_purchased ? 'bg-green-500' : ''}
                    size="lg"
                  >
                    {selectedStrategy.user_has_purchased ? (
                      <>
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Owned
                      </>
                    ) : purchaseStrategyMutation.isPending ? (
                      'Purchasing...'
                    ) : !selectedStrategy.user_can_afford ? (
                      'Insufficient Credits'
                    ) : (
                      <>
                        <ShoppingCart className="h-4 w-4 mr-2" />
                        {selectedStrategy.pricing_model === 'free' ? 'Add to Portfolio' : 'Purchase Strategy'}
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StrategyMarketplace;