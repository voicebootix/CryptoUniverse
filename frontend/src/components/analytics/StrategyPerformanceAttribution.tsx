import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  Activity,
  BarChart3,
  PieChart,
  Calendar,
  Award,
  AlertTriangle,
  RefreshCw,
  Download,
  Filter,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Percent,
  Clock,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  ComposedChart,
  Area,
  AreaChart
} from 'recharts';

interface StrategyAttribution {
  strategy_id: string;
  strategy_name: string;
  category: string;
  is_active: boolean;
  
  // Performance Metrics
  total_pnl_usd: number;
  total_pnl_percentage: number;
  contribution_to_portfolio: number; // Percentage of total portfolio profit
  
  // Trading Stats
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  
  // Risk Metrics
  volatility: number;
  max_drawdown: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  
  // Time-based Performance
  daily_pnl: Array<{
    date: string;
    pnl: number;
    cumulative_pnl: number;
  }>;
  
  // Trade Attribution
  recent_trades: Array<{
    trade_id: string;
    symbol: string;
    side: string;
    pnl_usd: number;
    executed_at: string;
    impact_on_portfolio: number; // Percentage impact on total portfolio
  }>;
  
  // Sector/Asset Attribution
  asset_breakdown: Array<{
    symbol: string;
    pnl_contribution: number;
    trade_count: number;
    win_rate: number;
  }>;
}

interface PortfolioAttribution {
  total_portfolio_pnl: number;
  total_portfolio_percentage: number;
  attribution_period: string;
  last_updated: string;
  
  strategy_attributions: StrategyAttribution[];
  
  // Portfolio-level metrics
  portfolio_metrics: {
    total_trades: number;
    overall_win_rate: number;
    portfolio_sharpe: number;
    portfolio_volatility: number;
    max_portfolio_drawdown: number;
  };
}

const StrategyPerformanceAttribution: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState<'7d' | '30d' | '90d' | 'ytd' | 'all'>('30d');
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'overview' | 'detailed'>('overview');

  // Fetch performance attribution data
  const { data: attribution, isLoading, error, refetch } = useQuery({
    queryKey: ['strategy-performance-attribution', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get('/analytics/strategy-attribution', {
        params: {
          period: selectedPeriod,
          include_trades: true,
          include_asset_breakdown: true
        }
      });
      return response.data as PortfolioAttribution;
    },
    refetchInterval: 60000, // Refresh every minute
    retry: 2,
    staleTime: 30000
  });

  const COLORS = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'];

  const getPnLColor = (value: number) => {
    if (value > 0) return 'text-green-500';
    if (value < 0) return 'text-red-500';
    return 'text-gray-500';
  };

  const exportPerformanceData = () => {
    if (!attribution) return;
    
    const csvData = attribution.strategy_attributions.map(strategy => ({
      Strategy: strategy.strategy_name,
      Category: strategy.category,
      'Total P&L': strategy.total_pnl_usd,
      'P&L %': strategy.total_pnl_percentage,
      'Portfolio Contribution %': strategy.contribution_to_portfolio,
      'Total Trades': strategy.total_trades,
      'Win Rate %': strategy.win_rate,
      'Sharpe Ratio': strategy.sharpe_ratio,
      'Max Drawdown %': strategy.max_drawdown,
      Status: strategy.is_active ? 'Active' : 'Paused'
    }));

    const csv = [
      Object.keys(csvData[0]).join(','),
      ...csvData.map(row => Object.values(row).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `strategy-attribution-${selectedPeriod}-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="text-center p-12">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load Performance Data</h3>
            <p className="text-muted-foreground mb-4">
              {error instanceof Error ? error.message : 'Unable to fetch performance attribution data'}
            </p>
            <Button onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
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

  if (!attribution || !attribution.strategy_attributions.length) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="text-center p-12">
            <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Performance Data</h3>
            <p className="text-muted-foreground">
              Start trading with strategies to see performance attribution analysis
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Strategy Performance Attribution</h2>
          <p className="text-muted-foreground">
            Analyze individual strategy contributions to your portfolio performance
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
          
          <Button variant="outline" onClick={exportPerformanceData}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          
          <Button variant="outline" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Portfolio Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Portfolio P&L</p>
                <p className={`text-2xl font-bold ${getPnLColor(attribution.total_portfolio_pnl)}`}>
                  {formatCurrency(attribution.total_portfolio_pnl)}
                </p>
              </div>
              <div className={`p-3 rounded-full ${attribution.total_portfolio_pnl >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                {attribution.total_portfolio_pnl >= 0 ? (
                  <TrendingUp className="h-6 w-6 text-green-600" />
                ) : (
                  <TrendingDown className="h-6 w-6 text-red-600" />
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Portfolio Return</p>
                <p className={`text-2xl font-bold ${getPnLColor(attribution.total_portfolio_percentage)}`}>
                  {formatPercentage(attribution.total_portfolio_percentage)}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <Percent className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Trades</p>
                <p className="text-2xl font-bold">{formatNumber(attribution.portfolio_metrics.total_trades)}</p>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <Activity className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Overall Win Rate</p>
                <p className="text-2xl font-bold text-green-500">
                  {formatPercentage(attribution.portfolio_metrics.overall_win_rate)}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <Target className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="contribution" className="space-y-6">
        <TabsList>
          <TabsTrigger value="contribution">Strategy Contribution</TabsTrigger>
          <TabsTrigger value="performance">Performance Metrics</TabsTrigger>
          <TabsTrigger value="trades">Trade Attribution</TabsTrigger>
          <TabsTrigger value="assets">Asset Breakdown</TabsTrigger>
        </TabsList>

        {/* Strategy Contribution */}
        <TabsContent value="contribution" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Profit Contribution by Strategy</CardTitle>
                <CardDescription>How much each strategy contributed to total profits</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RechartsPieChart>
                      <Pie
                        data={attribution.strategy_attributions.map(s => ({
                          name: s.strategy_name,
                          value: Math.abs(s.contribution_to_portfolio),
                          pnl: s.total_pnl_usd
                        }))}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                      >
                        {attribution.strategy_attributions.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value, name, props) => [
                        `${formatCurrency((props.payload as any)?.pnl || 0)}`,
                        name
                      ]} />
                    </RechartsPieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Strategy List */}
            <Card>
              <CardHeader>
                <CardTitle>Strategy Performance Ranking</CardTitle>
                <CardDescription>Ranked by total P&L contribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {attribution.strategy_attributions
                    .sort((a, b) => b.total_pnl_usd - a.total_pnl_usd)
                    .map((strategy, index) => (
                      <div key={strategy.strategy_id} className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white font-bold text-sm">
                            {index + 1}
                          </div>
                          <div>
                            <div className="font-medium">{strategy.strategy_name}</div>
                            <div className="text-sm text-muted-foreground">
                              {strategy.category} • {strategy.total_trades} trades
                            </div>
                          </div>
                        </div>
                        
                        <div className="text-right">
                          <div className={`font-bold ${getPnLColor(strategy.total_pnl_usd)}`}>
                            {formatCurrency(strategy.total_pnl_usd)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {formatPercentage(strategy.contribution_to_portfolio)} of total
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Performance Metrics */}
        <TabsContent value="performance" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            {attribution.strategy_attributions.map((strategy) => (
              <Card key={strategy.strategy_id}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{strategy.strategy_name}</span>
                    <Badge variant={strategy.is_active ? "default" : "secondary"}>
                      {strategy.is_active ? "Active" : "Paused"}
                    </Badge>
                  </CardTitle>
                  <CardDescription>{strategy.category} strategy</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Total P&L:</span>
                          <span className={`font-medium ${getPnLColor(strategy.total_pnl_usd)}`}>
                            {formatCurrency(strategy.total_pnl_usd)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Win Rate:</span>
                          <span className="font-medium text-green-500">
                            {formatPercentage(strategy.win_rate)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Sharpe Ratio:</span>
                          <span className="font-medium">{strategy.sharpe_ratio.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Max Drawdown:</span>
                          <span className="font-medium text-red-500">
                            {formatPercentage(strategy.max_drawdown)}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Avg Win:</span>
                          <span className="font-medium text-green-500">
                            {formatCurrency(strategy.average_win)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Avg Loss:</span>
                          <span className="font-medium text-red-500">
                            {formatCurrency(strategy.average_loss)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Largest Win:</span>
                          <span className="font-medium text-green-500">
                            {formatCurrency(strategy.largest_win)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Largest Loss:</span>
                          <span className="font-medium text-red-500">
                            {formatCurrency(strategy.largest_loss)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Performance Chart */}
                  {strategy.daily_pnl && strategy.daily_pnl.length > 0 && (
                    <div className="mt-6">
                      <div className="text-sm font-medium mb-2">Cumulative P&L</div>
                      <div className="h-32">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={strategy.daily_pnl}>
                            <Area
                              type="monotone"
                              dataKey="cumulative_pnl"
                              stroke="#22c55e"
                              fill="#22c55e"
                              fillOpacity={0.2}
                            />
                            <Tooltip formatter={(value: number) => [formatCurrency(value), 'Cumulative P&L']} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Trade Attribution */}
        <TabsContent value="trades" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Recent Trades by Strategy</CardTitle>
              <CardDescription>Latest trades and their impact on portfolio performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {attribution.strategy_attributions.map((strategy) => (
                  strategy.recent_trades && strategy.recent_trades.length > 0 && (
                    <div key={strategy.strategy_id}>
                      <h4 className="font-medium mb-3">{strategy.strategy_name}</h4>
                      <div className="space-y-2">
                        {strategy.recent_trades.slice(0, 5).map((trade) => (
                          <div key={trade.trade_id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                            <div className="flex items-center gap-3">
                              <Badge variant="outline" className={trade.side === 'buy' ? 'text-green-600' : 'text-red-600'}>
                                {trade.side.toUpperCase()}
                              </Badge>
                              <div>
                                <div className="font-medium">{trade.symbol}</div>
                                <div className="text-sm text-muted-foreground">
                                  {formatRelativeTime(new Date(trade.executed_at))}
                                </div>
                              </div>
                            </div>
                            
                            <div className="text-right">
                              <div className={`font-bold ${getPnLColor(trade.pnl_usd)}`}>
                                {formatCurrency(trade.pnl_usd)}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                {formatPercentage(trade.impact_on_portfolio)} portfolio impact
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Asset Breakdown */}
        <TabsContent value="assets" className="space-y-6">
          {attribution.strategy_attributions.map((strategy) => (
            strategy.asset_breakdown && strategy.asset_breakdown.length > 0 && (
              <Card key={`${strategy.strategy_id}-assets`}>
                <CardHeader>
                  <CardTitle>{strategy.strategy_name} - Asset Performance</CardTitle>
                  <CardDescription>Performance breakdown by trading pairs</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {strategy.asset_breakdown.map((asset) => (
                      <div key={`${strategy.strategy_id}-${asset.symbol}`} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="font-medium">{asset.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            {asset.trade_count} trades
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <div className={`font-bold ${getPnLColor(asset.pnl_contribution)}`}>
                              {formatCurrency(asset.pnl_contribution)}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {formatPercentage(asset.win_rate)} win rate
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default StrategyPerformanceAttribution;