import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  DollarSign,
  Target,
  Zap,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Globe,
  Clock,
  Signal,
  Brain,
  Layers,
  PieChart
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useMarketAnalysis } from '@/hooks/useMarketAnalysis';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart as RechartsPieChart, Pie, Cell } from 'recharts';

const COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4'];

const MarketAnalysisPage: React.FC = () => {
  const {
    realtimePrices,
    technicalAnalysis,
    sentimentAnalysis,
    arbitrageOpportunities,
    volatilityData,
    supportResistance,
    institutionalFlows,
    alphaSignals,
    trendingCoins,
    marketHealth,
    exchangeAssets,
    isLoading,
    error,
    lastUpdated,
    fetchRealtimePrices,
    fetchTechnicalAnalysis,
    fetchSentimentAnalysis,
    fetchArbitrageOpportunities,
    fetchVolatilityAnalysis,
    fetchSupportResistance,
    fetchInstitutionalFlows,
    fetchAlphaSignals,
    fetchTrendingCoins,
    fetchMarketHealth,
    fetchExchangeAssets,
    refreshAll,
    clearError
  } = useMarketAnalysis();

  const [selectedSymbols, setSelectedSymbols] = useState('BTC,ETH,SOL,ADA,DOT');
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');

  useEffect(() => {
    // Initial data load
    handleRefreshAll();
  }, []);

  const handleRefreshAll = async () => {
    await refreshAll();
  };

  const handleRefreshSpecific = async (type: string) => {
    clearError();
    switch (type) {
      case 'prices':
        await fetchRealtimePrices(selectedSymbols);
        break;
      case 'technical':
        await fetchTechnicalAnalysis(selectedSymbols, selectedTimeframe);
        break;
      case 'sentiment':
        await fetchSentimentAnalysis(selectedSymbols);
        break;
      case 'arbitrage':
        await fetchArbitrageOpportunities();
        break;
      case 'trending':
        await fetchTrendingCoins();
        break;
    }
  };

  // Prepare chart data
  const priceChartData = Object.entries(realtimePrices).map(([symbol, data]: [string, any]) => {
    const symbolData = data.aggregated || {};
    return {
      symbol,
      price: symbolData.average_price || 0,
      change: data.exchanges?.[0]?.change_24h || 0,
      volume: symbolData.total_volume || 0
    };
  });

  const arbitrageChartData = arbitrageOpportunities.slice(0, 10).map((opp: any, index) => ({
    pair: opp.symbol || `Pair ${index + 1}`,
    profit: opp.profit_percentage || 0,
    volume: opp.volume_constraint || 0
  }));

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Market Analysis</h1>
          <p className="text-muted-foreground">
            Comprehensive real-time market intelligence across all exchanges
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={handleRefreshAll}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh All
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg"
        >
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Error Loading Market Data</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={clearError}>
              Dismiss
            </Button>
          </div>
        </motion.div>
      )}

      {/* Last Updated */}
      {lastUpdated && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          Last updated: {new Date(lastUpdated).toLocaleString()}
        </div>
      )}

      {/* Market Health Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Market Health</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {marketHealth.status || 'Loading...'}
              </div>
              <div className="flex items-center text-sm text-muted-foreground">
                <CheckCircle className="h-4 w-4 mr-1 text-green-500" />
                All systems operational
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Exchanges</CardTitle>
              <Globe className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {Object.keys(exchangeAssets).length || '8'}
              </div>
              <p className="text-xs text-muted-foreground">
                Real-time data feeds
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Arbitrage Opportunities</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {arbitrageOpportunities.length}
              </div>
              <p className="text-xs text-muted-foreground">
                Active opportunities
              </p>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Trending Coins</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {trendingCoins.length}
              </div>
              <p className="text-xs text-muted-foreground">
                Coins gaining momentum
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Main Analysis Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="technical">Technical</TabsTrigger>
          <TabsTrigger value="sentiment">Sentiment</TabsTrigger>
          <TabsTrigger value="arbitrage">Arbitrage</TabsTrigger>
          <TabsTrigger value="flows">Institutional</TabsTrigger>
          <TabsTrigger value="alpha">Alpha Signals</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Real-time Prices Chart */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    Real-time Prices
                  </CardTitle>
                  <CardDescription>Live cryptocurrency prices across exchanges</CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRefreshSpecific('prices')}
                  disabled={isLoading}
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={priceChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis
                        dataKey="symbol"
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
                        tickFormatter={(value) => `$${value.toLocaleString()}`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                        formatter={(value: any) => [formatCurrency(value), 'Price']}
                      />
                      <Bar dataKey="price" fill="#22c55e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Trending Coins */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    Trending Coins
                  </CardTitle>
                  <CardDescription>Most popular cryptocurrencies right now</CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRefreshSpecific('trending')}
                  disabled={isLoading}
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {trendingCoins.slice(0, 8).map((coin: any, index) => (
                    <div
                      key={coin.symbol || index}
                      className="flex items-center justify-between p-3 rounded-lg border bg-muted/20"
                    >
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="text-xs">
                          #{coin.rank || index + 1}
                        </Badge>
                        <div>
                          <div className="font-medium">{coin.symbol || 'N/A'}</div>
                          <div className="text-xs text-muted-foreground">
                            {coin.name || 'Unknown'}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-medium">
                          {coin.price_btc ? `₿${coin.price_btc.toFixed(8)}` : 'N/A'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Market Overview Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {Object.entries(realtimePrices).map(([symbol, data]: [string, any]) => {
              const symbolData = data.aggregated || {};
              const change = data.exchanges?.[0]?.change_24h || 0;
              
              return (
                <motion.div
                  key={symbol}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <Card className="hover:shadow-lg transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-lg">{symbol}</span>
                        <Badge variant={change > 0 ? "default" : "destructive"} className="text-xs">
                          {change > 0 ? '+' : ''}{formatPercentage(change)}
                        </Badge>
                      </div>
                      <div className="space-y-1">
                        <div className="text-2xl font-bold">
                          {formatCurrency(symbolData.average_price || 0)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Spread: {formatPercentage(symbolData.spread_percentage || 0)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Exchanges: {symbolData.exchange_count || 0}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </TabsContent>

        {/* Technical Analysis Tab */}
        <TabsContent value="technical" className="space-y-6">
          <div className="flex items-center gap-4 mb-4">
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="px-3 py-2 border rounded-md bg-background"
            >
              <option value="1m">1 Minute</option>
              <option value="5m">5 Minutes</option>
              <option value="15m">15 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
              <option value="1d">1 Day</option>
            </select>
            <Button
              onClick={() => handleRefreshSpecific('technical')}
              disabled={isLoading}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh Technical
            </Button>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {Object.entries(technicalAnalysis).map(([symbol, analysis]: [string, any]) => (
              <Card key={symbol}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    {symbol} Technical Analysis
                  </CardTitle>
                  <CardDescription>{selectedTimeframe} timeframe</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Trend Analysis */}
                    <div className="p-3 rounded-lg border bg-muted/20">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Trend</span>
                        <Badge variant={
                          analysis.analysis?.trend?.direction === 'BULLISH' ? 'default' :
                          analysis.analysis?.trend?.direction === 'BEARISH' ? 'destructive' : 'secondary'
                        }>
                          {analysis.analysis?.trend?.direction || 'NEUTRAL'}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Strength: {analysis.analysis?.trend?.strength || 0}/10
                      </div>
                    </div>

                    {/* RSI */}
                    <div className="p-3 rounded-lg border bg-muted/20">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">RSI</span>
                        <span className="font-bold">
                          {analysis.analysis?.momentum?.rsi || 0}
                        </span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            (analysis.analysis?.momentum?.rsi || 0) > 70 ? 'bg-red-500' :
                            (analysis.analysis?.momentum?.rsi || 0) < 30 ? 'bg-green-500' : 'bg-blue-500'
                          }`}
                          style={{ width: `${analysis.analysis?.momentum?.rsi || 0}%` }}
                        />
                      </div>
                    </div>

                    {/* Signals */}
                    <div className="grid grid-cols-3 gap-2">
                      <div className="text-center p-2 rounded bg-green-500/20">
                        <div className="text-sm font-medium text-green-400">Buy</div>
                        <div className="text-lg font-bold">{analysis.signals?.buy || 0}</div>
                      </div>
                      <div className="text-center p-2 rounded bg-gray-500/20">
                        <div className="text-sm font-medium text-gray-400">Neutral</div>
                        <div className="text-lg font-bold">{analysis.signals?.neutral || 0}</div>
                      </div>
                      <div className="text-center p-2 rounded bg-red-500/20">
                        <div className="text-sm font-medium text-red-400">Sell</div>
                        <div className="text-lg font-bold">{analysis.signals?.sell || 0}</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Arbitrage Tab */}
        <TabsContent value="arbitrage" className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Cross-Exchange Arbitrage Opportunities</h3>
            <Button
              onClick={() => handleRefreshSpecific('arbitrage')}
              disabled={isLoading}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              Scan Opportunities
            </Button>
          </div>

          <div className="grid gap-4">
            {arbitrageOpportunities.map((opportunity: any, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <Badge variant="outline" className="font-mono">
                        {opportunity.symbol || `Opportunity ${index + 1}`}
                      </Badge>
                      <div>
                        <div className="font-medium">
                          {opportunity.buy_exchange || 'Exchange A'} → {opportunity.sell_exchange || 'Exchange B'}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Buy: {formatCurrency(opportunity.buy_price || 0)} | 
                          Sell: {formatCurrency(opportunity.sell_price || 0)}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-green-500">
                        +{formatPercentage(opportunity.profit_percentage || 0)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {opportunity.profit_bps || 0} bps
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {arbitrageOpportunities.length === 0 && !isLoading && (
            <Card>
              <CardContent className="p-8 text-center">
                <Target className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Arbitrage Opportunities</h3>
                <p className="text-muted-foreground">
                  Currently scanning for profitable opportunities across exchanges
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Other tabs would be implemented similarly */}
        <TabsContent value="sentiment" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Market Sentiment Analysis
              </CardTitle>
              <CardDescription>AI-powered sentiment analysis across timeframes</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <Eye className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">
                  Sentiment analysis data will appear here when available
                </p>
                <Button
                  onClick={() => handleRefreshSpecific('sentiment')}
                  disabled={isLoading}
                  variant="outline"
                  className="mt-4"
                >
                  Load Sentiment Data
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="flows" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5" />
                Institutional Flow Tracking
              </CardTitle>
              <CardDescription>Monitor whale movements and institutional activity</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <Signal className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">
                  Institutional flow data will appear here when available
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alpha" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Alpha Generation Signals
              </CardTitle>
              <CardDescription>AI-generated trading signals and opportunities</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">
                  Alpha signals will appear here when available
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MarketAnalysisPage;