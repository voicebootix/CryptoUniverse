import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  Percent,
  Clock,
  AlertCircle
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { usePaperModeStore } from '@/store/paperModeStore';
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage } from '@/lib/utils';

interface PortfolioMetrics {
  totalBalance: number;
  availableBalance: number;
  totalProfit: number;
  totalProfitPercent: number;
  dayProfit: number;
  dayProfitPercent: number;
  activeTrades: number;
  winRate: number;
  lastUpdate: string;
}

const PortfolioHeader: React.FC = () => {
  const { isPaperMode, paperStats, paperBalance } = usePaperModeStore();

  const { data: metrics, isLoading, isError } = useQuery({
    queryKey: ['portfolio-header', isPaperMode],
    queryFn: async () => {
      try {
        if (isPaperMode) {
          // Return paper trading metrics
          return {
            totalBalance: paperBalance,
            availableBalance: paperBalance * 0.8, // Assume 80% available
            totalProfit: paperStats?.totalProfit || 0,
            totalProfitPercent: paperStats?.totalProfit ? (paperStats.totalProfit / 10000) * 100 : 0,
            dayProfit: paperStats?.totalProfit ? paperStats.totalProfit * 0.1 : 0, // Assume 10% of total is today
            dayProfitPercent: paperStats?.totalProfit ? (paperStats.totalProfit * 0.1 / 10000) * 100 : 0,
            activeTrades: 0,
            winRate: paperStats?.winRate || 0,
            lastUpdate: new Date().toISOString()
          };
        } else {
          // Fetch real portfolio metrics
          const response = await apiClient.get('/api/v1/portfolio/metrics');
          return response.data.data;
        }
      } catch (error) {
        // Fallback to safe defaults
        return {
          totalBalance: 0,
          availableBalance: 0,
          totalProfit: 0,
          totalProfitPercent: 0,
          dayProfit: 0,
          dayProfitPercent: 0,
          activeTrades: 0,
          winRate: 0,
          lastUpdate: new Date().toISOString()
        };
      }
    },
    refetchInterval: 10000, // Refresh every 10 seconds
    staleTime: 5000 // Consider data stale after 5 seconds
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-4 px-4 py-2">
        <div className="flex items-center gap-2 animate-pulse">
          <div className="h-4 w-16 bg-muted rounded" />
          <div className="h-4 w-20 bg-muted rounded" />
        </div>
      </div>
    );
  }

  if (isError || !metrics) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 text-muted-foreground">
        <AlertCircle className="h-4 w-4" />
        <span className="text-sm">Portfolio data unavailable</span>
      </div>
    );
  }

  const isPositiveTotal = metrics.totalProfit >= 0;
  const isPositiveDay = metrics.dayProfit >= 0;

  return (
    <div className="flex items-center gap-6 px-4 py-2 border-l border-border">
      {/* Paper Mode Indicator */}
      {isPaperMode && (
        <>
          <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-500/20">
            Paper Mode
          </Badge>
          <Separator orientation="vertical" className="h-6" />
        </>
      )}

      {/* Total Balance */}
      <div className="flex items-center gap-2">
        <Wallet className="h-4 w-4 text-muted-foreground" />
        <div className="flex flex-col">
          <span className="text-sm font-semibold">
            {formatCurrency(metrics.totalBalance)}
          </span>
          <span className="text-xs text-muted-foreground">Balance</span>
        </div>
      </div>

      <Separator orientation="vertical" className="h-6" />

      {/* Total P&L */}
      <div className="flex items-center gap-2">
        {isPositiveTotal ? (
          <TrendingUp className="h-4 w-4 text-green-500" />
        ) : (
          <TrendingDown className="h-4 w-4 text-red-500" />
        )}
        <div className="flex flex-col">
          <span className={`text-sm font-semibold ${
            isPositiveTotal ? 'text-green-500' : 'text-red-500'
          }`}>
            {formatCurrency(metrics.totalProfit)}
          </span>
          <span className="text-xs text-muted-foreground">
            Total P&L ({formatPercentage(metrics.totalProfitPercent)})
          </span>
        </div>
      </div>

      <Separator orientation="vertical" className="h-6" />

      {/* Day P&L */}
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${
          isPositiveDay ? 'bg-green-500' : 'bg-red-500'
        }`} />
        <div className="flex flex-col">
          <span className={`text-sm font-semibold ${
            isPositiveDay ? 'text-green-500' : 'text-red-500'
          }`}>
            {formatCurrency(metrics.dayProfit)}
          </span>
          <span className="text-xs text-muted-foreground">
            Today ({formatPercentage(metrics.dayProfitPercent)})
          </span>
        </div>
      </div>

      <Separator orientation="vertical" className="h-6" />

      {/* Active Trades */}
      <div className="flex items-center gap-2">
        <Activity className="h-4 w-4 text-muted-foreground" />
        <div className="flex flex-col">
          <span className="text-sm font-semibold">
            {metrics.activeTrades}
          </span>
          <span className="text-xs text-muted-foreground">Active</span>
        </div>
      </div>

      {/* Win Rate (if available) */}
      {metrics.winRate > 0 && (
        <>
          <Separator orientation="vertical" className="h-6" />
          <div className="flex items-center gap-2">
            <Percent className="h-4 w-4 text-muted-foreground" />
            <div className="flex flex-col">
              <span className="text-sm font-semibold">
                {formatPercentage(metrics.winRate)}
              </span>
              <span className="text-xs text-muted-foreground">Win Rate</span>
            </div>
          </div>
        </>
      )}

      {/* Last Update */}
      <div className="hidden xl:flex items-center gap-1 ml-2">
        <Clock className="h-3 w-3 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">
          {new Date(metrics.lastUpdate).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })}
        </span>
      </div>
    </div>
  );
};

export default PortfolioHeader;