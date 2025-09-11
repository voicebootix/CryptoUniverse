import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  ChevronDown,
  ChevronUp,
  Wallet,
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  Globe,
  CheckCircle,
  AlertTriangle,
  CreditCard,
  Zap,
  RefreshCw
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useGlobalPaperModeStore } from '@/store/globalPaperModeStore';
import { useExchanges } from '@/hooks/useExchanges';
import { usePortfolioStore } from '@/hooks/usePortfolio';
import { apiClient } from '@/lib/api/client';
import PaperTradingToggle from '@/components/trading/PaperTradingToggle';

interface CreditInfo {
  total: number;
  used: number;
  remaining: number;
  nextRefresh: string;
}

const SophisticatedHeaderWidgets: React.FC = () => {
  const navigate = useNavigate();
  const { isPaperMode, paperStats, paperBalance } = useGlobalPaperModeStore();
  const { exchanges, aggregatedStats } = useExchanges();
  const { totalValue, dailyPnL, totalPnL, positions, fetchPortfolio, fetchStatus, fetchMarketData } = usePortfolioStore();

  // Credits query
  const { data: credits } = useQuery({
    queryKey: ['user-credits'],
    queryFn: async () => {
      const response = await apiClient.get('/credits/balance');
      return response.data.data;
    },
    refetchInterval: 30000
  });

  // Fetch portfolio data on component mount
  useEffect(() => {
    fetchPortfolio();
    fetchStatus();
    fetchMarketData();
  }, [fetchPortfolio, fetchStatus, fetchMarketData]);

  // Calculate portfolio metrics
  const portfolioValue = isPaperMode ? paperBalance : totalValue;
  const portfolioPnL = isPaperMode ? (paperStats?.totalProfit || 0) : totalPnL;
  const dailyPnLValue = isPaperMode ? ((paperStats?.totalProfit || 0) * 0.1) : dailyPnL;

  return (
    <div className="flex items-center gap-4">
      {/* Global Paper Mode Toggle */}
      <PaperTradingToggle isCompact />

      {/* Balance Widget with Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2 px-3 py-2 h-auto">
            <div className="flex items-center gap-2">
              <Wallet className="h-4 w-4 text-muted-foreground" />
              <div className="flex flex-col items-start">
                <span className="text-sm font-semibold">
                  {formatCurrency(portfolioValue)}
                </span>
                <span className="text-xs text-muted-foreground">
                  {isPaperMode ? 'Paper Balance' : 'Total Value'}
                </span>
              </div>
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </div>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-80 p-0" align="start">
          <Card className="border-0 shadow-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Wallet className="h-4 w-4" />
                Portfolio Overview
                {isPaperMode && (
                  <Badge variant="outline" className="text-xs">Paper Mode</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Balance Breakdown */}
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Value</span>
                  <span className="text-sm font-medium">{formatCurrency(portfolioValue)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Available Balance</span>
                  <span className="text-sm font-medium">
                    {formatCurrency(portfolioValue * 0.8)}
                  </span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total P&L</span>
                  <span className={`text-sm font-medium ${
                    portfolioPnL >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {portfolioPnL >= 0 ? '+' : ''}{formatCurrency(portfolioPnL)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Today's P&L</span>
                  <span className={`text-sm font-medium ${
                    dailyPnLValue >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {dailyPnLValue >= 0 ? '+' : ''}{formatCurrency(dailyPnLValue)}
                  </span>
                </div>
              </div>

              {/* Top Positions */}
              {positions.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-2">
                    <span className="text-xs font-medium text-muted-foreground uppercase">
                      Top Positions
                    </span>
                    {positions.slice(0, 3).map((position) => (
                      <div key={position.symbol} className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-primary rounded-full" />
                          <span className="text-sm">{position.symbol}</span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium">
                            {formatCurrency(position.value)}
                          </div>
                          <div className={`text-xs ${
                            position.change24h >= 0 ? 'text-green-500' : 'text-red-500'
                          }`}>
                            {formatPercentage(position.change24h)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              <Separator />
              <Button 
                variant="outline" 
                size="sm" 
                className="w-full"
                onClick={() => navigate('/dashboard/portfolio')}
              >
                View Full Portfolio
              </Button>
            </CardContent>
          </Card>
        </DropdownMenuContent>
      </DropdownMenu>

      <Separator orientation="vertical" className="h-8" />

      {/* Exchange Connections Widget */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2 px-3 py-2 h-auto">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <div className="flex flex-col items-start">
                <span className="text-sm font-semibold">
                  {aggregatedStats.connectedCount} Connected
                </span>
                <span className="text-xs text-muted-foreground">
                  Exchanges
                </span>
              </div>
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </div>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-80 p-0" align="start">
          <Card className="border-0 shadow-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Globe className="h-4 w-4" />
                Exchange Connections
              </CardTitle>
              <CardDescription>
                {aggregatedStats.connectedCount} of {aggregatedStats.totalCount} exchanges connected
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Connected Exchanges */}
              <div className="space-y-3">
                {exchanges.filter(ex => ex.is_active).map((exchange) => (
                  <div key={exchange.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
                          <span className="text-xs font-bold">
                            {exchange.exchange.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 border-2 border-background rounded-full" />
                      </div>
                      <div>
                        <div className="text-sm font-medium capitalize">
                          {exchange.exchange}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {exchange.nickname || 'Main Account'}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">
                        {exchange.balance ? formatCurrency(exchange.balance) : '---'}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {exchange.latency || '---'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Aggregated Stats */}
              {aggregatedStats.connectedCount > 0 && (
                <>
                  <Separator />
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div>
                      <div className="text-lg font-bold text-green-500">
                        {formatCurrency(aggregatedStats.totalBalance)}
                      </div>
                      <div className="text-xs text-muted-foreground">Total Balance</div>
                    </div>
                    <div>
                      <div className="text-lg font-bold">
                        {aggregatedStats.totalTrades24h}
                      </div>
                      <div className="text-xs text-muted-foreground">Trades Today</div>
                    </div>
                  </div>
                </>
              )}

              <Separator />
              <Button variant="outline" size="sm" className="w-full">
                Manage Exchanges
              </Button>
            </CardContent>
          </Card>
        </DropdownMenuContent>
      </DropdownMenu>

      <Separator orientation="vertical" className="h-8" />

      {/* Credits Widget */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2 px-3 py-2 h-auto">
            <div className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
              <div className="flex flex-col items-start">
                <span className="text-sm font-semibold">
                  {credits?.remaining || 250}
                </span>
                <span className="text-xs text-muted-foreground">
                  Credits
                </span>
              </div>
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </div>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-80 p-0" align="start">
          <Card className="border-0 shadow-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <CreditCard className="h-4 w-4" />
                Trading Credits
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Credit Breakdown */}
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Total Credits</span>
                  <span className="text-sm font-medium">{credits?.total || 500}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Used This Month</span>
                  <span className="text-sm font-medium">{credits?.used || 250}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Remaining</span>
                  <span className="text-sm font-medium text-green-500">
                    {credits?.remaining || 250}
                  </span>
                </div>
              </div>

              {/* Usage Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Usage</span>
                  <span>{Math.round(((credits?.used || 250) / (credits?.total || 500)) * 100)}%</span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full"
                    style={{
                      width: `${((credits?.used || 250) / (credits?.total || 500)) * 100}%`
                    }}
                  />
                </div>
              </div>

              {/* Next Refresh */}
              <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg">
                <RefreshCw className="h-4 w-4 text-muted-foreground" />
                <div>
                  <div className="text-sm font-medium">Next Refresh</div>
                  <div className="text-xs text-muted-foreground">
                    {credits?.nextRefresh || '1st of next month'}
                  </div>
                </div>
              </div>

              <Separator />
              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" size="sm">
                  View Usage
                </Button>
                <Button variant="default" size="sm">
                  <Zap className="h-3 w-3 mr-1" />
                  Buy More
                </Button>
              </div>
            </CardContent>
          </Card>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};

export default SophisticatedHeaderWidgets;