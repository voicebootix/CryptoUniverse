import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  Zap,
  Target,
  BarChart3,
  PieChart,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Wallet,
  Bot,
  ArrowUpRight,
  ArrowDownRight,
  Eye,
  Play,
  Pause,
  Settings,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore, useUser } from '@/store/authStore';
import { formatCurrency, formatPercentage, formatNumber, getColorForChange, getBackgroundColorForChange } from '@/lib/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart as RechartsPieChart, Pie, Cell, BarChart, Bar } from 'recharts';
import { usePortfolioStore } from '@/hooks/usePortfolio';

// Mock data for charts and tables that are not yet connected
const performanceData = [
  { time: '00:00', value: 52800 },
  { time: '04:00', value: 53100 },
  { time: '08:00', value: 52900 },
  { time: '12:00', value: 53800 },
  { time: '16:00', value: 54100 },
  { time: '20:00', value: 54250 },
];

const marketData = [
  { symbol: 'BTC', price: 50000, change: 2.5, volume: '2.1B' },
  { symbol: 'ETH', price: 2400, change: -1.2, volume: '1.8B' },
  { symbol: 'SOL', price: 50, change: 5.8, volume: '450M' },
  { symbol: 'ADA', price: 0.45, change: 3.2, volume: '320M' },
  { symbol: 'DOT', price: 8.50, change: -0.8, volume: '180M' },
];

const recentTrades = [
  {
    id: 1,
    symbol: 'BTC',
    side: 'buy' as const,
    amount: 0.1,
    price: 49800,
    time: '2 min ago',
    status: 'completed' as const,
    pnl: 120.50,
  },
  {
    id: 2,
    symbol: 'ETH',
    side: 'sell' as const,
    amount: 2.0,
    price: 2420,
    time: '15 min ago',
    status: 'completed' as const,
    pnl: -45.20,
  },
  {
    id: 3,
    symbol: 'SOL',
    side: 'buy' as const,
    amount: 50,
    price: 48.50,
    time: '1 hour ago',
    status: 'pending' as const,
    pnl: 0,
  },
];

const COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6'];

const TradingDashboard: React.FC = () => {
  const user = useUser();
  const { 
    totalValue,
    availableBalance,
    totalPnL,
    dailyPnL,
    dailyPnLPercent,
    totalPnLPercent,
    positions,
    performanceHistory,
    marketData,
    recentTrades,
    isLoading,
    error,
    fetchPortfolio,
    fetchStatus,
    fetchMarketData,
    fetchRecentTrades,
  } = usePortfolioStore();
  
  const [autonomousMode, setAutonomousMode] = useState(false);

  useEffect(() => {
    fetchPortfolio();
    fetchStatus();
    fetchMarketData();
    fetchRecentTrades();
  }, [fetchPortfolio, fetchStatus, fetchMarketData, fetchRecentTrades]);

  const handleRefresh = async () => {
    await Promise.all([fetchPortfolio(), fetchStatus(), fetchMarketData(), fetchRecentTrades()]);
  };

  const toggleAutonomousMode = () => {
    setAutonomousMode(!autonomousMode);
  };

  const pieChartData = positions.map((position, index) => ({
    name: position.symbol,
    value: position.value,
    color: COLORS[index % COLORS.length],
  }));

  if (isLoading && totalValue === 0) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-2xl">Loading Portfolio...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-2xl text-red-500">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trading Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your portfolio and execute trades with AI assistance
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Autonomous Mode Toggle */}
          <Button
            variant={autonomousMode ? "profit" : "outline"}
            onClick={toggleAutonomousMode}
            className="gap-2"
          >
            <Bot className="h-4 w-4" />
            {autonomousMode ? 'Autonomous ON' : 'Manual Mode'}
          </Button>

          {/* Refresh Button */}
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Status Banner */}
      {user?.simulation_mode && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-warning/10 border border-warning/30 rounded-lg"
        >
          <div className="flex items-center gap-3">
            <Eye className="h-5 w-5 text-warning" />
            <div>
              <p className="font-medium text-warning">Simulation Mode Active</p>
              <p className="text-sm text-muted-foreground">
                You're trading with virtual funds. No real money is at risk.
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
              <Wallet className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(totalValue)}
              </div>
              <div className={`flex items-center text-sm ${getColorForChange(dailyPnL)}`}>
                {dailyPnL > 0 ? (
                  <ArrowUpRight className="h-4 w-4 mr-1" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 mr-1" />
                )}
                {formatCurrency(Math.abs(dailyPnL))} (
                {formatPercentage(Math.abs(dailyPnLPercent))}) today
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Available Balance</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(availableBalance)}
              </div>
              <p className="text-xs text-muted-foreground">
                Ready for new positions
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${getColorForChange(totalPnL)}`}>
                {totalPnL > 0 ? '+' : ''}
                {formatCurrency(totalPnL)}
              </div>
              <div className={`flex items-center text-sm ${getColorForChange(totalPnL)}`}>
                {totalPnL > 0 ? (
                  <TrendingUp className="h-4 w-4 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 mr-1" />
                )}
                {formatPercentage(Math.abs(totalPnLPercent))} return
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="trading-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">AI Status</CardTitle>
              <Bot className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <div className={`h-3 w-3 rounded-full ${autonomousMode ? 'bg-profit animate-pulse' : 'bg-muted'}`} />
                <span className="text-sm font-medium">
                  {autonomousMode ? 'Active' : 'Standby'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {autonomousMode ? 'AI is monitoring markets' : 'Manual trading mode'}
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Charts and Analytics */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Portfolio Performance Chart */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Portfolio Performance
              </CardTitle>
              <CardDescription>24-hour portfolio value trend</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={performanceHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="time"
                      stroke="#9CA3AF"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#9CA3AF"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1F2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                      }}
                      formatter={(value: any) => [formatCurrency(value), 'Portfolio Value']}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#22c55e"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Portfolio Allocation */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="h-5 w-5" />
                Portfolio Allocation
              </CardTitle>
              <CardDescription>Current position distribution</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      dataKey="value"
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: any) => [formatCurrency(value), 'Value']}
                      contentStyle={{
                        backgroundColor: '#1F2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                      }}
                    />
                  </RechartsPieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-4">
                {pieChartData.map((item, index) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-sm font-medium">{item.name}</span>
                    <span className="text-sm text-muted-foreground ml-auto">
                      {formatCurrency(item.value)}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Positions and Market Data */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Current Positions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="lg:col-span-2"
        >
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5" />
                Current Positions
              </CardTitle>
              <CardDescription>Active trading positions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {positions.map((position) => (
                  <div
                    key={position.symbol}
                    className="flex items-center justify-between p-4 rounded-lg border bg-muted/30"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{position.symbol}</span>
                          <Badge variant="outline" className="text-xs">
                            {position.side.toUpperCase()}
                          </Badge>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {position.name}
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="flex items-center gap-4">
                        <div>
                          <div className="font-medium">
                            {formatNumber(position.amount)} @ {formatCurrency(position.price)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Value: {formatCurrency(position.value)}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`font-medium ${getColorForChange(position.change24h)}`}>
                            {position.change24h > 0 ? '+' : ''}
                            {formatPercentage(position.change24h)}
                          </div>
                          <div className={`text-sm ${getColorForChange(position.unrealizedPnL)}`}>
                            {position.unrealizedPnL > 0 ? '+' : ''}
                            {formatCurrency(position.unrealizedPnL)}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Market Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          <Card className="trading-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Market Overview
              </CardTitle>
              <CardDescription>Top cryptocurrency prices</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {marketData.map((market) => (
                  <div
                    key={market.symbol}
                    className="flex items-center justify-between p-3 rounded-lg border bg-muted/20"
                  >
                    <div>
                      <div className="font-medium">{market.symbol}</div>
                      <div className="text-xs text-muted-foreground">
                        Vol: {market.volume}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {formatCurrency(market.price)}
                      </div>
                      <div className={`text-sm ${getColorForChange(market.change)}`}>
                        {market.change > 0 ? '+' : ''}
                        {formatPercentage(market.change)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent Trading Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
      >
        <Card className="trading-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Recent Trading Activity
            </CardTitle>
            <CardDescription>Latest trades and orders</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentTrades.map((trade) => (
                <div
                  key={trade.id}
                  className="flex items-center justify-between p-4 rounded-lg border bg-muted/20"
                >
                  <div className="flex items-center gap-4">
                    <Badge
                      variant={trade.side === 'buy' ? 'profit' : 'loss'}
                      className="uppercase"
                    >
                      {trade.side}
                    </Badge>
                    <div>
                      <div className="font-medium">
                        {formatNumber(trade.amount)} {trade.symbol}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        @ {formatCurrency(trade.price)}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="flex items-center gap-2">
                        {trade.status === 'completed' ? (
                          <CheckCircle className="h-4 w-4 text-profit" />
                        ) : (
                          <Clock className="h-4 w-4 text-warning" />
                        )}
                        <span className="text-sm capitalize">{trade.status}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {trade.time}
                      </div>
                    </div>
                    {trade.status === 'completed' && (
                      <div className={`text-right ${getColorForChange(trade.pnl)}`}>
                        <div className="font-medium">
                          {trade.pnl > 0 ? '+' : ''}
                          {formatCurrency(trade.pnl)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default TradingDashboard;
