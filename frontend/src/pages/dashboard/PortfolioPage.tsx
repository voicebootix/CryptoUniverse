import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Activity,
  BarChart3,
  PieChart,
  RefreshCw,
  AlertTriangle,
  Target,
  ArrowUpRight,
  ArrowDownRight,
  Calendar,
  Filter,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { usePortfolioStore } from '@/hooks/usePortfolio';
import { formatCurrency, formatPercentage, formatNumber, getColorForChange } from '@/lib/utils';
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
  Area,
  AreaChart,
} from 'recharts';

const COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4'];

const PortfolioPage: React.FC = () => {
  const { 
    totalValue,
    availableBalance,
    totalPnL,
    dailyPnL,
    dailyPnLPercent,
    totalPnLPercent,
    positions,
    performanceHistory,
    isLoading,
    error,
    fetchPortfolio,
    fetchStatus,
  } = usePortfolioStore();

  const [timeframe, setTimeframe] = useState('24h');

  useEffect(() => {
    fetchPortfolio();
    fetchStatus();
  }, [fetchPortfolio, fetchStatus]);

  const handleRefresh = async () => {
    await Promise.all([fetchPortfolio(), fetchStatus()]);
  };

  // Prepare chart data
  const pieChartData = positions.map((position, index) => ({
    name: position.symbol,
    value: position.value,
    percentage: totalValue > 0 ? (position.value / totalValue) * 100 : 0,
    color: COLORS[index % COLORS.length],
  }));

  // Mock performance data for different timeframes (would be real in production)
  const getPerformanceData = (timeframe: string) => {
    const baseValue = totalValue;
    const dataPoints = timeframe === '24h' ? 24 : timeframe === '7d' ? 7 : 30;
    const volatility = 0.05; // 5% volatility
    
    return Array.from({ length: dataPoints }, (_, i) => {
      const change = (Math.random() - 0.5) * volatility;
      return {
        time: timeframe === '24h' ? `${i}:00` : `Day ${i + 1}`,
        value: baseValue * (1 + change * (i / dataPoints)),
        pnl: (Math.random() - 0.5) * 1000,
      };
    });
  };

  const performanceData = getPerformanceData(timeframe);

  if (isLoading && totalValue === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-lg">Loading portfolio analytics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center space-y-4">
        <AlertTriangle className="h-16 w-16 text-red-500" />
        <h2 className="text-2xl font-bold">Error Loading Portfolio</h2>
        <p className="text-muted-foreground max-w-md">{error}</p>
        <Button onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6 p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Portfolio Analytics</h1>
          <p className="text-muted-foreground">
            Comprehensive analysis of your trading portfolio
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1 bg-secondary rounded-lg p-1">
            {['24h', '7d', '30d'].map((tf) => (
              <Button
                key={tf}
                size="sm"
                variant={timeframe === tf ? 'default' : 'ghost'}
                onClick={() => setTimeframe(tf)}
                className="px-3 py-1"
              >
                {tf}
              </Button>
            ))}
          </div>
          <Button onClick={handleRefresh} size="sm" variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Portfolio Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalValue)}</div>
            <p className="text-xs text-muted-foreground">
              Available: {formatCurrency(availableBalance)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily P&L</CardTitle>
            {dailyPnL >= 0 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getColorForChange(dailyPnL)}`}>
              {formatCurrency(dailyPnL)}
            </div>
            <p className={`text-xs ${getColorForChange(dailyPnLPercent)}`}>
              {formatPercentage(dailyPnLPercent)} today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getColorForChange(totalPnL)}`}>
              {formatCurrency(totalPnL)}
            </div>
            <p className={`text-xs ${getColorForChange(totalPnLPercent)}`}>
              {formatPercentage(totalPnLPercent)} overall
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{positions.length}</div>
            <p className="text-xs text-muted-foreground">
              Across {new Set(positions.map(p => p.symbol.split('/')[0])).size} assets
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Performance */}
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Performance</CardTitle>
            <CardDescription>
              Value over time ({timeframe})
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip formatter={(value) => [formatCurrency(Number(value)), 'Value']} />
                  <Area 
                    type="monotone" 
                    dataKey="value" 
                    stroke="#22c55e" 
                    fill="#22c55e" 
                    fillOpacity={0.2} 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Asset Allocation */}
        <Card>
          <CardHeader>
            <CardTitle>Asset Allocation</CardTitle>
            <CardDescription>
              Portfolio distribution by asset
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] flex items-center justify-center">
              {pieChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percentage }) => `${name} ${percentage.toFixed(1)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [formatCurrency(Number(value)), 'Value']} />
                  </RechartsPieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center text-muted-foreground">
                  <PieChart className="h-12 w-12 mx-auto mb-2" />
                  <p>No positions to display</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Positions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Current Positions</CardTitle>
          <CardDescription>
            Detailed breakdown of your portfolio positions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {positions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Asset</th>
                    <th className="text-right p-2">Amount</th>
                    <th className="text-right p-2">Value (USD)</th>
                    <th className="text-right p-2">Price</th>
                    <th className="text-right p-2">24h Change</th>
                    <th className="text-right p-2">Allocation</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((position, index) => (
                    <tr key={position.symbol} className="border-b hover:bg-muted/50">
                      <td className="p-2">
                        <div className="flex items-center space-x-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          <div>
                            <div className="font-medium">{position.symbol}</div>
                            <div className="text-sm text-muted-foreground">{position.name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="text-right p-2 font-mono">
                        {formatNumber(position.amount, 6)}
                      </td>
                      <td className="text-right p-2 font-mono">
                        {formatCurrency(position.value)}
                      </td>
                      <td className="text-right p-2 font-mono">
                        {formatCurrency(position.price)}
                      </td>
                      <td className={`text-right p-2 font-mono ${getColorForChange(position.change24h)}`}>
                        {formatPercentage(position.change24h)}
                      </td>
                      <td className="text-right p-2 font-mono">
                        {totalValue > 0 ? formatPercentage((position.value / totalValue) * 100) : '0%'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Wallet className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No positions found</p>
              <p className="text-sm">Connect an exchange to see your portfolio</p>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default PortfolioPage;
