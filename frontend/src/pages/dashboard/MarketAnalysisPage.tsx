import React, { useState, useEffect, useMemo } from 'react';
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
  PieChart,
  Gauge
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useMarketAnalysis } from '@/hooks/useMarketAnalysis';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart as RechartsPieChart, Pie, Cell } from 'recharts';

const COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4'];

// Safe number formatting helper
const safeToFixed = (value: any, decimals: number): string | undefined => {
  const num = typeof value === 'string' ? parseFloat(value) : Number(value);
  return !isNaN(num) && isFinite(num) ? num.toFixed(decimals) : undefined;
};

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

  // Transform institutional flows array into symbol-keyed object
  const flowsByAsset = useMemo(() => {
    if (!Array.isArray(institutionalFlows)) return {};
    
    return institutionalFlows.reduce((acc: any, flow: any) => {
      const asset = flow.asset || flow.symbol || 'UNKNOWN';
      
      // Normalize flow into transactions array
      let transactions: any[];
      if (Array.isArray(flow.transactions)) {
        transactions = flow.transactions;
      } else if (flow.volume !== undefined || flow.amount !== undefined) {
        // Flow itself is an event-level item, wrap as single transaction
        transactions = [flow];
      } else {
        transactions = [];
      }
      
      // Initialize asset accumulator if missing
      if (!acc[asset]) {
        acc[asset] = {
          total_count: 0,
          running_net_sum: 0,
          running_abs_sum: 0,
          all_transactions: []
        };
      }
      
      // Process each transaction
      transactions.forEach((tx: any) => {
        const volume = tx.volume || tx.amount || 0;
        const isInflow = tx.type === 'inflow' || tx.direction === 'inflow';
        const absVolume = Math.abs(volume);
        
        // Update running totals
        acc[asset].total_count += 1;
        acc[asset].running_net_sum += isInflow ? absVolume : -absVolume;
        acc[asset].running_abs_sum += absVolume;
        
        // Add normalized transaction
        acc[asset].all_transactions.push({
          direction: isInflow ? 'inflow' : 'outflow',
          amount: absVolume,
          exchange: tx.exchange || 'Unknown Exchange',
          timestamp: tx.timestamp || tx.time || new Date().toISOString(),
          market_impact: tx.impact || tx.market_impact || 'Low'
        });
      });
      
      return acc;
    }, {});
  }, [institutionalFlows]);

  // Post-process accumulated data
  const processedFlowsByAsset = useMemo(() => {
    const processed: any = {};
    
    Object.entries(flowsByAsset).forEach(([asset, data]: [string, any]) => {
      const { total_count, running_net_sum, running_abs_sum, all_transactions } = data;
      
      // Compute final metrics
      const average_size = total_count > 0 ? running_abs_sum / total_count : 0;
      const net_flow = running_net_sum;
      
      // Sort transactions by amount and get top 5
      const large_transactions = all_transactions
        .sort((a: any, b: any) => b.amount - a.amount)
        .slice(0, 5);
      
      processed[asset] = {
        total_flows: total_count,
        summary: {
          net_flow,
          average_size
        },
        large_transactions
      };
    });
    
    return processed;
  }, [flowsByAsset]);

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
        await fetchRealtimePrices([selectedSymbols]);
        break;
      case 'technical':
        await fetchTechnicalAnalysis(selectedSymbols);
        break;
      case 'sentiment':
        await fetchSentimentAnalysis([selectedSymbols]);
        break;
      case 'arbitrage':
        await fetchArbitrageOpportunities();
        break;
      case 'trending':
        await fetchTrendingCoins();
        break;
      case 'flows':
        await fetchInstitutionalFlows();
        break;
      case 'alpha':
        await fetchAlphaSignals();
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
                {marketHealth?.status || 'Loading...'}
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
                  {trendingCoins.slice(0, 8).map((coin: any, index: number) => (
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

        {/* Sentiment Analysis Tab */}
        <TabsContent value="sentiment" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Market Sentiment Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  Market Sentiment Analysis
                </CardTitle>
                <CardDescription>AI-powered sentiment analysis across timeframes</CardDescription>
              </CardHeader>
              <CardContent>
                {sentimentAnalysis && Object.keys(sentimentAnalysis).length > 0 ? (
                  <div className="space-y-4">
                    {Object.entries(sentimentAnalysis).map(([symbol, analysis]: [string, any]) => (
                      <div key={symbol} className="p-4 rounded-lg border bg-muted/20">
                        <div className="flex items-center justify-between mb-3">
                          <span className="font-bold text-lg">{symbol}</span>
                          <Badge variant={
                            analysis.overall_sentiment?.label === 'VERY_BULLISH' ? 'default' :
                            analysis.overall_sentiment?.label === 'BULLISH' ? 'default' :
                            analysis.overall_sentiment?.label === 'BEARISH' ? 'destructive' :
                            analysis.overall_sentiment?.label === 'VERY_BEARISH' ? 'destructive' : 'secondary'
                          }>
                            {analysis.overall_sentiment?.label || 'NEUTRAL'}
                          </Badge>
                        </div>
                        
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Sentiment Score</span>
                            <span className="font-mono">
                              {safeToFixed(analysis.overall_sentiment?.score, 3) || '0.000'}
                            </span>
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-muted-foreground">Confidence</span>
                            <span className="font-mono">
                              {safeToFixed(analysis.overall_sentiment?.confidence, 1) || '0.0'}%
                            </span>
                          </div>

                          {/* Timeframe Breakdown */}
                          {analysis.timeframe_breakdown && (
                            <div className="space-y-2">
                              <span className="text-sm font-medium">Timeframe Analysis:</span>
                              {Object.entries(analysis.timeframe_breakdown).map(([timeframe, data]: [string, any]) => (
                                <div key={timeframe} className="flex items-center justify-between text-sm">
                                  <span className="text-muted-foreground">{timeframe}:</span>
                                  <div className="flex items-center gap-2">
                                    <Badge variant={
                                      data.label === 'VERY_BULLISH' || data.label === 'BULLISH' ? 'default' :
                                      data.label === 'BEARISH' || data.label === 'VERY_BEARISH' ? 'destructive' : 'secondary'
                                    }>
                                      {data.label}
                                    </Badge>
                                    <span className="font-mono">{safeToFixed(data.score, 3) || '-'}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground mb-4">
                      Load AI-powered sentiment analysis
                    </p>
                    <Button
                      onClick={() => handleRefreshSpecific('sentiment')}
                      disabled={isLoading}
                      variant="outline"
                    >
                      {isLoading ? (
                        <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <Brain className="h-4 w-4 mr-2" />
                      )}
                      Analyze Market Sentiment
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Fear & Greed Index */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Gauge className="h-5 w-5" />
                  Fear & Greed Index
                </CardTitle>
                <CardDescription>Market emotion and sentiment indicator</CardDescription>
              </CardHeader>
              <CardContent>
                {sentimentAnalysis?.market_sentiment?.fear_greed_index ? (
                  <div className="space-y-4">
                    <div className="text-center">
                      <div className="text-4xl font-bold mb-2">
                        {Math.round(sentimentAnalysis.market_sentiment.fear_greed_index.fear_greed_index)}
                      </div>
                      <Badge variant={
                        sentimentAnalysis.market_sentiment.fear_greed_index.label === 'GREED' ? 'default' :
                        sentimentAnalysis.market_sentiment.fear_greed_index.label === 'FEAR' ? 'destructive' : 'secondary'
                      }>
                        {sentimentAnalysis.market_sentiment.fear_greed_index.label}
                      </Badge>
                    </div>
                    
                    <div className="w-full bg-muted rounded-full h-3">
                      <div
                        className={`h-3 rounded-full ${
                          sentimentAnalysis.market_sentiment.fear_greed_index.fear_greed_index > 50 ? 'bg-green-500' : 'bg-red-500'
                        }`}
                        style={{ 
                          width: `${sentimentAnalysis.market_sentiment.fear_greed_index.fear_greed_index}%` 
                        }}
                      />
                    </div>

                    <div className="text-sm text-muted-foreground text-center">
                      {sentimentAnalysis.market_sentiment.fear_greed_index.interpretation}
                    </div>

                    {/* Components Breakdown */}
                    {sentimentAnalysis.market_sentiment.fear_greed_index.components && (
                      <div className="space-y-2">
                        <span className="text-sm font-medium">Components:</span>
                        {Object.entries(sentimentAnalysis.market_sentiment.fear_greed_index.components).map(([component, value]: [string, any]) => (
                          <div key={component} className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground capitalize">
                              {component.replace('_', ' ')}:
                            </span>
                            <span className="font-mono">{Math.round(value)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Gauge className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">
                      Fear & Greed data will appear after sentiment analysis
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="flows" className="space-y-6">
          <div className="grid gap-6">
            {/* Institutional Flows Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  Institutional Flow Tracking
                </CardTitle>
                <CardDescription>Monitor whale movements and institutional activity</CardDescription>
              </CardHeader>
              <CardContent>
                {processedFlowsByAsset && Object.keys(processedFlowsByAsset).length > 0 ? (
                  <div className="space-y-4">
                    {Object.entries(processedFlowsByAsset).map(([symbol, flows]: [string, any]) => (
                      <div key={symbol} className="p-4 rounded-lg border bg-muted/20">
                        <div className="flex items-center justify-between mb-3">
                          <span className="font-bold text-lg">{symbol}</span>
                          <Badge variant="outline">
                            {flows.total_flows || 0} flows detected
                          </Badge>
                        </div>
                        
                        {flows.large_transactions && flows.large_transactions.length > 0 ? (
                          <div className="space-y-3">
                            <span className="text-sm font-medium">Large Transactions:</span>
                            {flows.large_transactions.slice(0, 5).map((tx: any, index: number) => (
                              <div key={index} className="flex items-center justify-between p-3 rounded border bg-background/50">
                                <div className="flex items-center gap-3">
                                  <Badge variant={tx.direction === 'inflow' ? 'default' : 'destructive'}>
                                    {tx.direction === 'inflow' ? 'IN' : 'OUT'}
                                  </Badge>
                                  <div>
                                    <div className="font-medium">
                                      {formatCurrency(tx.amount || 0)}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                      {tx.exchange || 'Unknown Exchange'}
                                    </div>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <div className="text-sm font-mono">
                                    {tx.timestamp ? new Date(tx.timestamp).toLocaleTimeString() : 'Recent'}
                                  </div>
                                  <div className="text-xs text-muted-foreground">
                                    Impact: {tx.market_impact || 'Low'}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-sm text-muted-foreground">
                            No significant institutional flows detected recently
                          </div>
                        )}

                        {/* Flow Summary */}
                        {flows.summary && (
                          <div className="mt-4 pt-4 border-t">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">Net Flow:</span>
                                <span className={`ml-2 font-mono ${
                                  flows.summary.net_flow >= 0 ? 'text-green-500' : 'text-red-500'
                                }`}>
                                  {formatCurrency(flows.summary.net_flow || 0)}
                                </span>
                              </div>
                              <div>
                                <span className="text-muted-foreground">Avg Size:</span>
                                <span className="ml-2 font-mono">
                                  {formatCurrency(flows.summary.average_size || 0)}
                                </span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Layers className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground mb-4">
                      Load institutional flow tracking data
                    </p>
                    <Button
                      onClick={() => handleRefreshSpecific('flows')}
                      disabled={isLoading}
                      variant="outline"
                    >
                      {isLoading ? (
                        <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <Layers className="h-4 w-4 mr-2" />
                      )}
                      Track Institutional Flows
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="alpha" className="space-y-6">
          <div className="grid gap-6">
            {/* Alpha Signals Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Alpha Generation Signals
                </CardTitle>
                <CardDescription>AI-generated trading signals and opportunities</CardDescription>
              </CardHeader>
              <CardContent>
                {alphaSignals && alphaSignals.length > 0 ? (
                  <div className="space-y-4">
                    {alphaSignals.map((signal: any, index: number) => (
                      <div key={index} className="p-4 rounded-lg border bg-muted/20">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <Badge variant="outline" className="font-mono">
                              {signal.symbol || `Signal ${index + 1}`}
                            </Badge>
                            <Badge variant={
                              signal.direction?.toLowerCase() === 'long' ? 'default' : 
                              signal.direction?.toLowerCase() === 'short' ? 'destructive' : 'secondary'
                            }>
                              {signal.direction?.toUpperCase() || 'NEUTRAL'}
                            </Badge>
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold text-green-500">
                              {signal.confidence ? `${Math.round(signal.confidence)}%` : 'N/A'}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Confidence
                            </div>
                          </div>
                        </div>

                        <div className="space-y-3">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-muted-foreground">Entry Price:</span>
                              <span className="ml-2 font-mono text-blue-500">
                                {signal.entry_price ? formatCurrency(signal.entry_price) : 'Market'}
                              </span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Target Price:</span>
                              <span className="ml-2 font-mono text-green-500">
                                {signal.target_price ? formatCurrency(signal.target_price) : 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Stop Loss:</span>
                              <span className="ml-2 font-mono text-red-500">
                                {signal.stop_loss ? formatCurrency(signal.stop_loss) : 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Risk/Reward:</span>
                              <span className="ml-2 font-mono">
                                {signal.risk_reward_ratio ? `1:${signal.risk_reward_ratio.toFixed(2)}` : 'N/A'}
                              </span>
                            </div>
                          </div>

                          {signal.reasoning && (
                            <div className="pt-3 border-t">
                              <span className="text-sm font-medium">AI Reasoning:</span>
                              <p className="text-sm text-muted-foreground mt-1">
                                {signal.reasoning}
                              </p>
                            </div>
                          )}

                          {signal.strategies && signal.strategies.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                              {signal.strategies.map((strategy: string, idx: number) => (
                                <Badge key={idx} variant="secondary" className="text-xs">
                                  {strategy}
                                </Badge>
                              ))}
                            </div>
                          )}

                          <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>
                              Generated: {signal.generated_at ? new Date(signal.generated_at).toLocaleString() : 'Recent'}
                            </span>
                            <span>
                              Expires: {signal.expires_at ? new Date(signal.expires_at).toLocaleString() : '24h'}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Zap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground mb-4">
                      Generate AI-powered alpha signals
                    </p>
                    <Button
                      onClick={() => handleRefreshSpecific('alpha')}
                      disabled={isLoading}
                      variant="outline"
                    >
                      {isLoading ? (
                        <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                      ) : (
                        <Zap className="h-4 w-4 mr-2" />
                      )}
                      Generate Alpha Signals
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MarketAnalysisPage;