import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  BarChart3,
  TrendingUp,
  TrendingDown,
  ArrowLeft,
  Play,
  Pause,
  RefreshCw,
  Calendar,
  DollarSign,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  Brain,
  Zap,
  Award,
  Rocket,
  LineChart,
  PieChart,
  Settings,
  Download,
  Filter,
  Search,
  ChevronDown,
  Sparkles,
  Shield,
  Calculator,
  Gauge
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';
import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ScatterChart,
  Scatter
} from 'recharts';

interface BacktestConfiguration {
  strategy_function: string;
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  parameters?: Record<string, any>;
}

interface BacktestResult {
  backtest_id: string;
  strategy_function: string;
  symbol: string;
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  initial_capital: number;
  final_capital: number;
  performance_metrics: {
    total_return_percent: number;
    win_rate_percent: number;
    total_trades: number;
    profitable_trades: number;
    average_trade_return: number;
    best_trade: number;
    worst_trade: number;
    max_drawdown_percent: number;
    volatility_percent: number;
    sharpe_ratio: number;
    calmar_ratio: number;
    profit_factor: number;
  };
  trade_history: Array<{
    trade_id: string;
    date: string;
    symbol: string;
    action: string;
    quantity: number;
    entry_price: number;
    exit_price?: number;
    pnl_usd: number;
    confidence: number;
    status: string;
  }>;
  daily_returns: number[];
  statistical_significance: {
    significant: boolean;
    p_value?: number;
    t_statistic?: number;
    mean_return?: number;
    std_deviation?: number;
    sample_size?: number;
    confidence_interval?: {
      lower_bound: number;
      upper_bound: number;
    };
  };
  status: 'completed' | 'running' | 'failed';
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

interface ABTestResult {
  ab_test_id: string;
  strategy_function: string;
  symbol: string;
  test_period: string;
  variant_a: {
    parameters: Record<string, any>;
    performance: any;
  };
  variant_b: {
    parameters: Record<string, any>;
    performance: any;
  };
  comparison: {
    winner: string;
    improvement_percentage: number;
    return_improvement: number;
    winrate_improvement: number;
    sharpe_improvement: number;
    risk_adjusted_improvement: number;
  };
  statistical_significance: {
    significant: boolean;
    p_value: number;
    interpretation: string;
  };
  recommendation: {
    recommendation: string;
    confidence: string;
    deployment_ready: boolean;
    continue_testing: boolean;
  };
}

const BacktestingLab: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('backtest');
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [selectedResult, setSelectedResult] = useState<BacktestResult | null>(null);
  const [showResultModal, setShowResultModal] = useState(false);

  // Backtest configuration state
  const [backtestConfig, setBacktestConfig] = useState<BacktestConfiguration>({
    strategy_function: '',
    symbol: 'BTC',
    start_date: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 90 days ago
    end_date: new Date().toISOString().split('T')[0], // today
    initial_capital: 10000,
    parameters: {}
  });

  // Fetch available strategies for backtesting
  const { data: availableStrategies } = useQuery({
    queryKey: ['available-strategies-for-backtest'],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/available-for-backtest');
      return response.data.strategies;
    },
    retry: 2
  });

  // Fetch backtest history
  const { data: backtestHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['backtest-history'],
    queryFn: async () => {
      const response = await apiClient.get('/backtesting/history', {
        params: { limit: 20 }
      });
      return response.data.backtests as BacktestResult[];
    },
    refetchInterval: 10000, // Refresh every 10 seconds for running backtests
    retry: 2
  });

  // Fetch running backtests
  const { data: runningBacktests } = useQuery({
    queryKey: ['running-backtests'],
    queryFn: async () => {
      const response = await apiClient.get('/backtesting/running');
      return response.data.backtests as BacktestResult[];
    },
    refetchInterval: 5000, // Check every 5 seconds
    retry: 2
  });

  // Run backtest mutation
  const runBacktestMutation = useMutation({
    mutationFn: async (config: BacktestConfiguration) => {
      const response = await apiClient.post('/backtesting/run', config);
      return response.data as BacktestResult;
    },
    onSuccess: (data) => {
      toast.success('Backtest started successfully');
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
      queryClient.invalidateQueries({ queryKey: ['running-backtests'] });
      setShowConfigModal(false);
    },
    onError: (error: any) => {
      toast.error(`Backtest failed: ${error.response?.data?.detail || error.message}`);
    }
  });

  // Run A/B test mutation
  const runABTestMutation = useMutation({
    mutationFn: async (config: any) => {
      const response = await apiClient.post('/backtesting/ab-test', config);
      return response.data as ABTestResult;
    },
    onSuccess: (data) => {
      toast.success('A/B test started successfully');
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
    },
    onError: (error: any) => {
      toast.error(`A/B test failed: ${error.response?.data?.detail || error.message}`);
    }
  });

  const handleRunBacktest = () => {
    if (!backtestConfig.strategy_function) {
      toast.error('Please select a strategy to backtest');
      return;
    }

    const daysDiff = Math.floor((new Date(backtestConfig.end_date).getTime() - new Date(backtestConfig.start_date).getTime()) / (1000 * 60 * 60 * 24));
    if (daysDiff < 90) {
      toast.error('Backtest period must be at least 90 days for statistical significance');
      return;
    }

    runBacktestMutation.mutate(backtestConfig);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-700"><CheckCircle className="h-3 w-3 mr-1" />Completed</Badge>;
      case 'running':
        return <Badge className="bg-blue-100 text-blue-700"><Clock className="h-3 w-3 mr-1" />Running</Badge>;
      case 'failed':
        return <Badge className="bg-red-100 text-red-700"><AlertTriangle className="h-3 w-3 mr-1" />Failed</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getPerformanceColor = (value: number) => {
    if (value > 0) return 'text-green-500';
    if (value < 0) return 'text-red-500';
    return 'text-gray-500';
  };

  const symbols = ['BTC', 'ETH', 'ADA', 'DOT', 'SOL', 'AVAX', 'MATIC', 'LINK'];

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
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
              <Brain className="h-8 w-8 text-blue-500" />
              Backtesting Laboratory
            </h1>
            <p className="text-muted-foreground">
              Validate strategies with historical data before deployment
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {runningBacktests && runningBacktests.length > 0 && (
            <Badge variant="outline" className="animate-pulse">
              <Activity className="h-4 w-4 mr-2" />
              {runningBacktests.length} Running
            </Badge>
          )}
          <Button
            onClick={() => setShowConfigModal(true)}
            className="bg-gradient-to-r from-blue-500 to-purple-600"
          >
            <Rocket className="h-4 w-4 mr-2" />
            New Backtest
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="backtest">Strategy Backtesting</TabsTrigger>
          <TabsTrigger value="results">Results History</TabsTrigger>
          <TabsTrigger value="abtest">A/B Testing</TabsTrigger>
          <TabsTrigger value="analytics">Performance Analytics</TabsTrigger>
        </TabsList>

        {/* Strategy Backtesting */}
        <TabsContent value="backtest" className="space-y-6">
          {/* Running Backtests */}
          {runningBacktests && runningBacktests.length > 0 && (
            <Card className="border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-blue-700">
                  <Activity className="h-5 w-5" />
                  Running Backtests ({runningBacktests.length})
                </CardTitle>
                <CardDescription className="text-blue-600">
                  These backtests are currently being processed
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {runningBacktests.map((backtest) => (
                    <div key={backtest.backtest_id} className="flex items-center justify-between p-4 bg-white rounded-lg border">
                      <div className="flex items-center gap-3">
                        <div className="animate-spin">
                          <RefreshCw className="h-5 w-5 text-blue-500" />
                        </div>
                        <div>
                          <div className="font-medium">{backtest.strategy_function}</div>
                          <div className="text-sm text-muted-foreground">
                            {backtest.symbol} • {formatRelativeTime(backtest.created_at)}
                          </div>
                        </div>
                      </div>
                      <Badge className="bg-blue-100 text-blue-700">
                        <Clock className="h-3 w-3 mr-1" />
                        Processing...
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Quick Backtest Cards */}
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {availableStrategies?.slice(0, 6).map((strategy: any) => (
              <Card key={strategy.strategy_id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    {strategy.is_ai_powered ? (
                      <Brain className="h-5 w-5 text-purple-500" />
                    ) : (
                      <BarChart3 className="h-5 w-5 text-blue-500" />
                    )}
                    {strategy.name}
                  </CardTitle>
                  <CardDescription>{strategy.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{strategy.category}</Badge>
                    {strategy.is_ai_powered && (
                      <Badge className="bg-purple-100 text-purple-700">
                        <Sparkles className="h-3 w-3 mr-1" />
                        AI
                      </Badge>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-muted-foreground">Complexity</div>
                      <div className="font-medium">{strategy.complexity_score}/10</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Risk Level</div>
                      <div className="font-medium capitalize">{strategy.risk_level?.replace('_', ' ')}</div>
                    </div>
                  </div>

                  <Button
                    onClick={() => {
                      setBacktestConfig(prev => ({
                        ...prev,
                        strategy_function: strategy.function_name
                      }));
                      setSelectedStrategy(strategy.name);
                      setShowConfigModal(true);
                    }}
                    className="w-full"
                    size="sm"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Run Backtest
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Educational Content */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Award className="h-5 w-5 text-yellow-500" />
                Why Backtesting Matters
              </CardTitle>
              <CardDescription>
                Understanding the importance of strategy validation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-3">
                <div className="text-center p-6 bg-blue-50 rounded-lg">
                  <Shield className="h-12 w-12 text-blue-500 mx-auto mb-4" />
                  <h4 className="font-semibold text-blue-700 mb-2">Risk Validation</h4>
                  <p className="text-sm text-blue-600">
                    Test strategies with 90+ days of historical data to identify potential risks before real deployment
                  </p>
                </div>

                <div className="text-center p-6 bg-green-50 rounded-lg">
                  <Calculator className="h-12 w-12 text-green-500 mx-auto mb-4" />
                  <h4 className="font-semibold text-green-700 mb-2">Statistical Significance</h4>
                  <p className="text-sm text-green-600">
                    Our backtests include t-tests, p-values, and confidence intervals for scientific validation
                  </p>
                </div>

                <div className="text-center p-6 bg-purple-50 rounded-lg">
                  <Gauge className="h-12 w-12 text-purple-500 mx-auto mb-4" />
                  <h4 className="font-semibold text-purple-700 mb-2">Performance Metrics</h4>
                  <p className="text-sm text-purple-600">
                    Comprehensive analysis including Sharpe ratio, max drawdown, win rate, and profit factor
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Results History */}
        <TabsContent value="results" className="space-y-6">
          {historyLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="space-y-2">
                        <div className="h-4 bg-muted rounded w-48" />
                        <div className="h-3 bg-muted rounded w-32" />
                      </div>
                      <div className="h-6 bg-muted rounded w-20" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : backtestHistory && backtestHistory.length > 0 ? (
            <div className="space-y-4">
              {backtestHistory.map((result) => (
                <Card
                  key={result.backtest_id}
                  className="hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => {
                    setSelectedResult(result);
                    setShowResultModal(true);
                  }}
                >
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                          {result.strategy_function.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-semibold">{result.strategy_function}</div>
                          <div className="text-sm text-muted-foreground">
                            {result.symbol} • {result.period.days} days • {formatRelativeTime(result.created_at)}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-6">
                        {result.status === 'completed' && result.performance_metrics && (
                          <div className="grid grid-cols-3 gap-6 text-center">
                            <div>
                              <div className="text-xs text-muted-foreground">Return</div>
                              <div className={`font-bold ${getPerformanceColor(result.performance_metrics.total_return_percent)}`}>
                                {formatPercentage(result.performance_metrics.total_return_percent)}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">Win Rate</div>
                              <div className="font-bold text-green-500">
                                {formatPercentage(result.performance_metrics.win_rate_percent)}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">Sharpe</div>
                              <div className="font-bold text-blue-500">
                                {result.performance_metrics.sharpe_ratio.toFixed(2)}
                              </div>
                            </div>
                          </div>
                        )}
                        
                        <div className="flex items-center gap-3">
                          {getStatusBadge(result.status)}
                          {result.statistical_significance?.significant && (
                            <Badge className="bg-yellow-100 text-yellow-700">
                              <Award className="h-3 w-3 mr-1" />
                              Significant
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <BarChart3 className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Backtests Yet</h3>
                <p className="text-muted-foreground mb-4">
                  Run your first backtest to validate a strategy's performance
                </p>
                <Button onClick={() => setShowConfigModal(true)}>
                  <Rocket className="h-4 w-4 mr-2" />
                  Start Backtesting
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* A/B Testing */}
        <TabsContent value="abtest" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-orange-500" />
                A/B Strategy Testing
              </CardTitle>
              <CardDescription>
                Compare different strategy parameters to find optimal configurations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Zap className="h-8 w-8 text-orange-500" />
                </div>
                <h4 className="font-semibold mb-2">A/B Testing Coming Soon</h4>
                <p className="text-muted-foreground mb-4">
                  Advanced parameter optimization and statistical comparison tools are being developed
                </p>
                <Button variant="outline" disabled>
                  <Settings className="h-4 w-4 mr-2" />
                  Configure A/B Test
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Analytics */}
        <TabsContent value="analytics" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Backtest Performance Analytics</CardTitle>
              <CardDescription>Aggregate analysis of all your backtests</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                <PieChart className="h-12 w-12 mx-auto mb-4" />
                <p>Analytics dashboard will show aggregated performance metrics across all backtests</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Configuration Modal */}
      <Dialog open={showConfigModal} onOpenChange={setShowConfigModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Configure Backtest</DialogTitle>
            <DialogDescription>
              {selectedStrategy ? `Set up backtest parameters for ${selectedStrategy}` : 'Configure your strategy backtest parameters'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Strategy Selection */}
            <div className="space-y-2">
              <Label htmlFor="strategy">Strategy</Label>
              <Select value={backtestConfig.strategy_function} onValueChange={(value) => 
                setBacktestConfig(prev => ({ ...prev, strategy_function: value }))
              }>
                <SelectTrigger>
                  <SelectValue placeholder="Select strategy to backtest" />
                </SelectTrigger>
                <SelectContent>
                  {availableStrategies?.map((strategy: any) => (
                    <SelectItem key={strategy.strategy_id} value={strategy.function_name}>
                      {strategy.name} ({strategy.category})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Symbol and Period */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Symbol</Label>
                <Select value={backtestConfig.symbol} onValueChange={(value) => 
                  setBacktestConfig(prev => ({ ...prev, symbol: value }))
                }>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {symbols.map(symbol => (
                      <SelectItem key={symbol} value={symbol}>
                        {symbol}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="capital">Initial Capital ($)</Label>
                <Input
                  type="number"
                  value={backtestConfig.initial_capital}
                  onChange={(e) => setBacktestConfig(prev => ({ 
                    ...prev, 
                    initial_capital: parseInt(e.target.value) || 10000 
                  }))}
                  min="1000"
                  max="1000000"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start">Start Date</Label>
                <Input
                  type="date"
                  value={backtestConfig.start_date}
                  onChange={(e) => setBacktestConfig(prev => ({ ...prev, start_date: e.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="end">End Date</Label>
                <Input
                  type="date"
                  value={backtestConfig.end_date}
                  onChange={(e) => setBacktestConfig(prev => ({ ...prev, end_date: e.target.value }))}
                />
              </div>
            </div>

            {/* Validation Info */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-start gap-3">
                <CheckCircle className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-900">Backtest Requirements</h4>
                  <ul className="text-sm text-blue-700 mt-1 space-y-1">
                    <li>• Minimum 90 days of historical data for statistical significance</li>
                    <li>• Real market data from multiple exchanges</li>
                    <li>• Statistical significance testing included</li>
                    <li>• Comprehensive performance metrics calculated</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setShowConfigModal(false)}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handleRunBacktest}
                disabled={runBacktestMutation.isPending}
                className="flex-1"
              >
                {runBacktestMutation.isPending ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Backtest
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Result Details Modal */}
      <Dialog open={showResultModal} onOpenChange={setShowResultModal}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          {selectedResult && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <BarChart3 className="h-6 w-6" />
                  {selectedResult.strategy_function} Backtest Results
                </DialogTitle>
                <DialogDescription>
                  {selectedResult.symbol} • {selectedResult.period.start_date} to {selectedResult.period.end_date} ({selectedResult.period.days} days)
                </DialogDescription>
              </DialogHeader>

              {selectedResult.status === 'completed' && selectedResult.performance_metrics ? (
                <div className="space-y-6">
                  {/* Key Metrics */}
                  <div className="grid gap-4 md:grid-cols-4">
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className={`text-2xl font-bold ${getPerformanceColor(selectedResult.performance_metrics.total_return_percent)}`}>
                        {formatPercentage(selectedResult.performance_metrics.total_return_percent)}
                      </div>
                      <div className="text-sm text-muted-foreground">Total Return</div>
                    </div>
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-500">
                        {formatPercentage(selectedResult.performance_metrics.win_rate_percent)}
                      </div>
                      <div className="text-sm text-muted-foreground">Win Rate</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold">
                        {selectedResult.performance_metrics.sharpe_ratio.toFixed(2)}
                      </div>
                      <div className="text-sm text-muted-foreground">Sharpe Ratio</div>
                    </div>
                    <div className="text-center p-4 bg-red-50 rounded-lg">
                      <div className="text-2xl font-bold text-red-500">
                        {formatPercentage(selectedResult.performance_metrics.max_drawdown_percent)}
                      </div>
                      <div className="text-sm text-muted-foreground">Max Drawdown</div>
                    </div>
                  </div>

                  {/* Detailed Metrics */}
                  <div className="grid gap-6 md:grid-cols-2">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Trading Statistics</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Total Trades:</span>
                            <span className="font-medium">{selectedResult.performance_metrics.total_trades}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Profitable Trades:</span>
                            <span className="font-medium text-green-500">{selectedResult.performance_metrics.profitable_trades}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Average Trade Return:</span>
                            <span className={`font-medium ${getPerformanceColor(selectedResult.performance_metrics.average_trade_return)}`}>
                              {formatCurrency(selectedResult.performance_metrics.average_trade_return)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Best Trade:</span>
                            <span className="font-medium text-green-500">
                              {formatCurrency(selectedResult.performance_metrics.best_trade)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Worst Trade:</span>
                            <span className="font-medium text-red-500">
                              {formatCurrency(selectedResult.performance_metrics.worst_trade)}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Risk Metrics</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Volatility:</span>
                            <span className="font-medium">{formatPercentage(selectedResult.performance_metrics.volatility_percent)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Calmar Ratio:</span>
                            <span className="font-medium">{selectedResult.performance_metrics.calmar_ratio.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Profit Factor:</span>
                            <span className={`font-medium ${selectedResult.performance_metrics.profit_factor > 1 ? 'text-green-500' : 'text-red-500'}`}>
                              {selectedResult.performance_metrics.profit_factor.toFixed(2)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Initial Capital:</span>
                            <span className="font-medium">{formatCurrency(selectedResult.initial_capital)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Final Capital:</span>
                            <span className={`font-medium ${getPerformanceColor(selectedResult.final_capital - selectedResult.initial_capital)}`}>
                              {formatCurrency(selectedResult.final_capital)}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Statistical Significance */}
                  {selectedResult.statistical_significance && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Calculator className="h-5 w-5" />
                          Statistical Analysis
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="space-y-3 text-sm">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Statistically Significant:</span>
                              <Badge className={selectedResult.statistical_significance.significant ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}>
                                {selectedResult.statistical_significance.significant ? 'Yes' : 'No'}
                              </Badge>
                            </div>
                            {selectedResult.statistical_significance.p_value && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">P-Value:</span>
                                <span className="font-medium">{selectedResult.statistical_significance.p_value.toFixed(4)}</span>
                              </div>
                            )}
                            {selectedResult.statistical_significance.sample_size && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Sample Size:</span>
                                <span className="font-medium">{selectedResult.statistical_significance.sample_size} trades</span>
                              </div>
                            )}
                          </div>
                          
                          <div className="space-y-3 text-sm">
                            {selectedResult.statistical_significance.mean_return && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Mean Return:</span>
                                <span className="font-medium">{selectedResult.statistical_significance.mean_return.toFixed(4)}</span>
                              </div>
                            )}
                            {selectedResult.statistical_significance.std_deviation && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Std Deviation:</span>
                                <span className="font-medium">{selectedResult.statistical_significance.std_deviation.toFixed(4)}</span>
                              </div>
                            )}
                            {selectedResult.statistical_significance.confidence_interval && (
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">95% CI:</span>
                                <span className="font-medium">
                                  [{selectedResult.statistical_significance.confidence_interval.lower_bound.toFixed(4)}, 
                                   {selectedResult.statistical_significance.confidence_interval.upper_bound.toFixed(4)}]
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Recent Trades */}
                  {selectedResult.trade_history && selectedResult.trade_history.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Recent Trades Sample</CardTitle>
                        <CardDescription>Last {selectedResult.trade_history.length} trades from the backtest</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {selectedResult.trade_history.slice(0, 10).map((trade) => (
                            <div key={trade.trade_id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                              <div className="flex items-center gap-3">
                                <Badge variant="outline" className={trade.action === 'buy' ? 'text-green-600' : 'text-red-600'}>
                                  {trade.action.toUpperCase()}
                                </Badge>
                                <div>
                                  <div className="font-medium">{trade.symbol}</div>
                                  <div className="text-sm text-muted-foreground">
                                    {new Date(trade.date).toLocaleDateString()} • Qty: {trade.quantity.toFixed(4)}
                                  </div>
                                </div>
                              </div>
                              <div className="text-right">
                                <div className={`font-bold ${getPerformanceColor(trade.pnl_usd)}`}>
                                  {formatCurrency(trade.pnl_usd)}
                                </div>
                                <div className="text-sm text-muted-foreground">
                                  {trade.confidence}% confidence
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              ) : selectedResult.status === 'failed' ? (
                <div className="text-center py-12">
                  <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Backtest Failed</h3>
                  <p className="text-muted-foreground">
                    {selectedResult.error_message || 'An error occurred during backtesting'}
                  </p>
                </div>
              ) : (
                <div className="text-center py-12">
                  <RefreshCw className="h-16 w-16 text-blue-500 mx-auto mb-4 animate-spin" />
                  <h3 className="text-lg font-semibold mb-2">Backtest Running</h3>
                  <p className="text-muted-foreground">
                    This backtest is currently being processed. Results will appear here when complete.
                  </p>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BacktestingLab;