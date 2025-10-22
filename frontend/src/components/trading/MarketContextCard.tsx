import React from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  DollarSign,
  Users,
  Zap,
  AlertCircle,
  Check
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';

interface MarketIndicator {
  name: string;
  value: number | string;
  signal?: 'bullish' | 'bearish' | 'neutral';
  description?: string;
}

interface ExchangeInfo {
  name: string;
  price: number;
  volume: number;
  isBest?: boolean;
}

interface MarketContextData {
  symbol: string;
  price: number;
  change24h: number;
  changePercent24h: number;
  volume24h: number;
  high24h?: number;
  low24h?: number;
  marketCap?: number;
  indicators?: MarketIndicator[];
  sentiment?: {
    overall: 'bullish' | 'bearish' | 'neutral';
    score: number;
    description?: string;
  };
  fearGreedIndex?: {
    value: number;
    classification: string;
  };
  exchanges?: ExchangeInfo[];
  lastUpdate?: string;
}

interface MarketContextCardProps {
  marketData?: MarketContextData;
  isLoading?: boolean;
  onRefresh?: () => void;
  compact?: boolean;
}

const SENTIMENT_CONFIG = {
  bullish: {
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    icon: TrendingUp,
    emoji: '🟢',
    label: 'Bullish'
  },
  bearish: {
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    icon: TrendingDown,
    emoji: '🔴',
    label: 'Bearish'
  },
  neutral: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    icon: Activity,
    emoji: '🟡',
    label: 'Neutral'
  }
};

const getFearGreedColor = (value: number): string => {
  if (value <= 25) return 'text-red-500';
  if (value <= 45) return 'text-orange-500';
  if (value <= 55) return 'text-yellow-500';
  if (value <= 75) return 'text-green-500';
  return 'text-emerald-500';
};

const getRSISignal = (rsi: number): { signal: 'bullish' | 'bearish' | 'neutral'; label: string } => {
  if (rsi >= 70) return { signal: 'bearish', label: 'Overbought' };
  if (rsi <= 30) return { signal: 'bullish', label: 'Oversold' };
  return { signal: 'neutral', label: 'Neutral' };
};

export const MarketContextCard: React.FC<MarketContextCardProps> = ({
  marketData,
  isLoading = false,
  onRefresh,
  compact = false
}) => {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-5 w-5 animate-pulse text-blue-500" />
            Market Context
          </CardTitle>
          <CardDescription>Loading market data...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-muted animate-pulse rounded" />
              <div className="h-2 bg-muted animate-pulse rounded w-3/4" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!marketData) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-5 w-5 text-muted-foreground" />
            Market Context
          </CardTitle>
          <CardDescription>No market data available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              Select a trading pair to view market context
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isPositiveChange = marketData.changePercent24h >= 0;
  const sentimentConfig = marketData.sentiment
    ? SENTIMENT_CONFIG[marketData.sentiment.overall]
    : SENTIMENT_CONFIG.neutral;
  const SentimentIcon = sentimentConfig.icon;

  if (compact) {
    return (
      <Card>
        <CardContent className="pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold">{marketData.symbol}</span>
            <Badge variant={isPositiveChange ? 'default' : 'destructive'} className="gap-1">
              {isPositiveChange ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {formatPercentage(marketData.changePercent24h / 100)}
            </Badge>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Price</span>
            <span className="text-xl font-bold">{formatCurrency(marketData.price)}</span>
          </div>
          {marketData.sentiment && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Sentiment</span>
              <Badge variant="outline" className={cn('gap-1', sentimentConfig.color)}>
                {sentimentConfig.emoji} {sentimentConfig.label}
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                {marketData.symbol} Market Context
              </CardTitle>
              <CardDescription>Live market data and technical indicators</CardDescription>
            </div>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Refresh market data"
              >
                <Activity className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Price and Change */}
          <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-3xl font-bold">{formatCurrency(marketData.price)}</div>
                <div className={cn(
                  'flex items-center gap-1 text-sm font-medium',
                  isPositiveChange ? 'text-green-500' : 'text-red-500'
                )}>
                  {isPositiveChange ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  {formatCurrency(Math.abs(marketData.change24h))} ({formatPercentage(Math.abs(marketData.changePercent24h) / 100)})
                </div>
              </div>
              {marketData.sentiment && (
                <Badge
                  variant="outline"
                  className={cn('gap-2 py-2 px-3', sentimentConfig.borderColor, sentimentConfig.bgColor)}
                >
                  <SentimentIcon className={cn('h-4 w-4', sentimentConfig.color)} />
                  <div className="flex flex-col items-start">
                    <span className="text-xs text-muted-foreground">Sentiment</span>
                    <span className={cn('font-semibold', sentimentConfig.color)}>
                      {sentimentConfig.label}
                    </span>
                  </div>
                </Badge>
              )}
            </div>

            {/* 24h Range */}
            {marketData.high24h && marketData.low24h && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>24h Low: {formatCurrency(marketData.low24h)}</span>
                  <span>24h High: {formatCurrency(marketData.high24h)}</span>
                </div>
                <Progress
                  value={
                    ((marketData.price - marketData.low24h) /
                      (marketData.high24h - marketData.low24h)) *
                    100
                  }
                  className="h-2"
                />
              </div>
            )}
          </div>

          <Separator />

          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <DollarSign className="h-3 w-3" />
                24h Volume
              </div>
              <div className="text-sm font-semibold">
                {marketData.volume24h >= 1e9
                  ? `$${(marketData.volume24h / 1e9).toFixed(2)}B`
                  : marketData.volume24h >= 1e6
                  ? `$${(marketData.volume24h / 1e6).toFixed(2)}M`
                  : formatCurrency(marketData.volume24h)}
              </div>
            </div>
            {marketData.marketCap && (
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Users className="h-3 w-3" />
                  Market Cap
                </div>
                <div className="text-sm font-semibold">
                  {marketData.marketCap >= 1e9
                    ? `$${(marketData.marketCap / 1e9).toFixed(2)}B`
                    : `$${(marketData.marketCap / 1e6).toFixed(2)}M`}
                </div>
              </div>
            )}
          </div>

          {/* Technical Indicators */}
          {marketData.indicators && marketData.indicators.length > 0 && (
            <>
              <Separator />
              <div className="space-y-3">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-500" />
                  Technical Indicators
                </h4>
                {marketData.indicators.map((indicator, index) => {
                  const isRSI = indicator.name.toLowerCase().includes('rsi');
                  const rsiValue = isRSI ? Number(indicator.value) : null;
                  const rsiSignal = rsiValue !== null ? getRSISignal(rsiValue) : null;
                  const signalConfig = indicator.signal ? SENTIMENT_CONFIG[indicator.signal] : null;

                  return (
                    <div key={index} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{indicator.name}</span>
                        {indicator.description && (
                          <span className="text-xs text-muted-foreground">({indicator.description})</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{indicator.value}</span>
                        {(signalConfig || rsiSignal) && (
                          <Badge
                            variant="outline"
                            className={cn(
                              'text-xs',
                              rsiSignal
                                ? SENTIMENT_CONFIG[rsiSignal.signal].color
                                : signalConfig?.color
                            )}
                          >
                            {rsiSignal ? rsiSignal.label : indicator.signal?.toUpperCase()}
                          </Badge>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}

          {/* Fear & Greed Index */}
          {marketData.fearGreedIndex && (
            <>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Fear & Greed Index</span>
                  <span className={cn('font-semibold', getFearGreedColor(marketData.fearGreedIndex.value))}>
                    {marketData.fearGreedIndex.value} - {marketData.fearGreedIndex.classification}
                  </span>
                </div>
                <Progress value={marketData.fearGreedIndex.value} className="h-2" />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Extreme Fear</span>
                  <span>Extreme Greed</span>
                </div>
              </div>
            </>
          )}

          {/* Exchange Comparison */}
          {marketData.exchanges && marketData.exchanges.length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h4 className="text-sm font-medium">
                  {marketData.exchanges.length} {marketData.exchanges.length === 1 ? 'Exchange' : 'Exchanges'}
                </h4>
                <div className="space-y-2">
                  {marketData.exchanges.map((exchange, index) => (
                    <div
                      key={index}
                      className={cn(
                        'flex items-center justify-between rounded-md border p-2 text-sm',
                        exchange.isBest && 'border-green-500/30 bg-green-500/5'
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{exchange.name}</span>
                        {exchange.isBest && (
                          <Badge variant="outline" className="text-xs text-green-500 gap-1">
                            <Check className="h-3 w-3" />
                            Best Price
                          </Badge>
                        )}
                      </div>
                      <div className="flex flex-col items-end">
                        <span className="font-semibold">{formatCurrency(exchange.price)}</span>
                        <span className="text-xs text-muted-foreground">
                          Vol: {exchange.volume >= 1e6 ? `$${(exchange.volume / 1e6).toFixed(1)}M` : formatCurrency(exchange.volume)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Last Update */}
          {marketData.lastUpdate && (
            <p className="text-center text-xs text-muted-foreground">
              Last updated: {new Date(marketData.lastUpdate).toLocaleTimeString()}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default MarketContextCard;
