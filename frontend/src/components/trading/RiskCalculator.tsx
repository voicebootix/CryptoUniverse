import React, { useMemo } from 'react';
import { Shield, AlertTriangle, TrendingUp, TrendingDown, Target, DollarSign, Percent } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';

interface RiskCalculatorData {
  portfolioValue: number;
  availableBalance: number;
  proposedAmount: number;
  entryPrice: number;
  stopLoss?: number;
  takeProfit?: number;
  leverage?: number;
}

interface RiskCalculatorProps {
  data: RiskCalculatorData;
  onAdjust?: (adjustments: Partial<RiskCalculatorData>) => void;
  compact?: boolean;
}

interface RiskMetrics {
  positionSize: number;
  positionSizePercent: number;
  maxLoss: number;
  maxLossPercent: number;
  potentialGain: number;
  potentialGainPercent: number;
  riskRewardRatio: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  leveragedExposure: number;
}

const RISK_LEVEL_CONFIG = {
  LOW: {
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    icon: Shield,
    label: 'Low Risk',
    emoji: '✅'
  },
  MEDIUM: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    icon: Shield,
    label: 'Medium Risk',
    emoji: '⚠️'
  },
  HIGH: {
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    icon: AlertTriangle,
    label: 'High Risk',
    emoji: '⚠️'
  },
  CRITICAL: {
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    icon: AlertTriangle,
    label: 'Critical Risk',
    emoji: '🚨'
  }
};

export const RiskCalculator: React.FC<RiskCalculatorProps> = ({
  data,
  onAdjust,
  compact = false
}) => {
  const metrics = useMemo((): RiskMetrics => {
    const leverage = data.leverage || 1;
    const positionSize = data.proposedAmount;
    const positionSizePercent = data.portfolioValue > 0
      ? (positionSize / data.portfolioValue) * 100
      : 0;

    const leveragedExposure = positionSize * leverage;

    // Calculate max loss (if stop loss is set)
    let maxLoss = 0;
    let maxLossPercent = 0;
    if (data.stopLoss && data.stopLoss > 0) {
      const lossPerUnit = Math.abs(data.entryPrice - data.stopLoss);
      const units = positionSize / data.entryPrice;
      maxLoss = lossPerUnit * units * leverage;
      maxLossPercent = data.portfolioValue > 0 ? (maxLoss / data.portfolioValue) * 100 : 0;
    } else {
      // Assume 5% default risk if no stop loss
      maxLoss = positionSize * 0.05 * leverage;
      maxLossPercent = positionSizePercent * 0.05 * leverage;
    }

    // Calculate potential gain (if take profit is set)
    let potentialGain = 0;
    let potentialGainPercent = 0;
    if (data.takeProfit && data.takeProfit > 0) {
      const gainPerUnit = Math.abs(data.takeProfit - data.entryPrice);
      const units = positionSize / data.entryPrice;
      potentialGain = gainPerUnit * units * leverage;
      potentialGainPercent = data.portfolioValue > 0 ? (potentialGain / data.portfolioValue) * 100 : 0;
    } else {
      // Assume 10% default gain if no take profit
      potentialGain = positionSize * 0.10 * leverage;
      potentialGainPercent = positionSizePercent * 0.10 * leverage;
    }

    // Calculate risk/reward ratio
    const riskRewardRatio = maxLoss > 0 ? potentialGain / maxLoss : 0;

    // Determine risk level
    let riskLevel: RiskMetrics['riskLevel'] = 'LOW';
    if (maxLossPercent >= 15 || positionSizePercent >= 50 || leverage >= 10) {
      riskLevel = 'CRITICAL';
    } else if (maxLossPercent >= 10 || positionSizePercent >= 35 || leverage >= 5) {
      riskLevel = 'HIGH';
    } else if (maxLossPercent >= 5 || positionSizePercent >= 20 || leverage >= 3) {
      riskLevel = 'MEDIUM';
    }

    return {
      positionSize,
      positionSizePercent,
      maxLoss,
      maxLossPercent,
      potentialGain,
      potentialGainPercent,
      riskRewardRatio,
      riskLevel,
      leveragedExposure
    };
  }, [data]);

  const riskConfig = RISK_LEVEL_CONFIG[metrics.riskLevel];
  const RiskIcon = riskConfig.icon;
  const isGoodRiskReward = metrics.riskRewardRatio >= 1.5;

  if (compact) {
    return (
      <Card className={cn('border', riskConfig.borderColor, riskConfig.bgColor)}>
        <CardContent className="pt-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Risk/Reward</span>
            <Badge variant={isGoodRiskReward ? 'default' : 'destructive'}>
              1:{metrics.riskRewardRatio.toFixed(2)}
            </Badge>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Max Loss</span>
            <span className="font-semibold text-red-500">
              -{formatCurrency(metrics.maxLoss)}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Potential Gain</span>
            <span className="font-semibold text-green-500">
              +{formatCurrency(metrics.potentialGain)}
            </span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('border-2', riskConfig.borderColor)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <RiskIcon className={cn('h-5 w-5', riskConfig.color)} />
          Risk Calculator
        </CardTitle>
        <CardDescription>
          Automated risk/reward analysis for this trade
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Risk Level Badge */}
        <div className={cn('rounded-lg border-2 p-4', riskConfig.borderColor, riskConfig.bgColor)}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{riskConfig.emoji}</span>
              <div>
                <div className={cn('text-lg font-bold', riskConfig.color)}>
                  {riskConfig.label}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatPercentage(metrics.positionSizePercent / 100)} of portfolio
                </div>
              </div>
            </div>
            {metrics.riskLevel === 'CRITICAL' && (
              <Badge variant="destructive" className="gap-1">
                <AlertTriangle className="h-3 w-3" />
                Review Required
              </Badge>
            )}
          </div>
        </div>

        <Separator />

        {/* Position Size */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Position Size</span>
            <span className="font-semibold">{formatCurrency(metrics.positionSize)}</span>
          </div>
          <Progress value={metrics.positionSizePercent} className="h-2" />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{formatPercentage(metrics.positionSizePercent / 100)} of portfolio</span>
            {metrics.positionSizePercent > 25 && (
              <span className="text-orange-500">High concentration</span>
            )}
          </div>
        </div>

        {data.leverage && data.leverage > 1 && (
          <div className="rounded-md bg-muted/50 p-3 space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Leveraged Exposure</span>
              <Badge variant="outline" className="text-xs">
                {data.leverage}x Leverage
              </Badge>
            </div>
            <div className="text-xl font-bold">
              {formatCurrency(metrics.leveragedExposure)}
            </div>
            {data.leverage >= 5 && (
              <p className="text-xs text-orange-500">
                High leverage increases both potential gains and losses
              </p>
            )}
          </div>
        )}

        <Separator />

        {/* Risk/Reward Ratio */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Risk/Reward Ratio</span>
            <Badge
              variant={isGoodRiskReward ? 'default' : 'destructive'}
              className={cn(
                'gap-1',
                isGoodRiskReward ? 'bg-green-600' : ''
              )}
            >
              {isGoodRiskReward && <Target className="h-3 w-3" />}
              1:{metrics.riskRewardRatio.toFixed(2)}
            </Badge>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {/* Max Loss */}
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 space-y-2">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingDown className="h-3 w-3" />
                Max Loss
              </div>
              <div className="text-xl font-bold text-red-500">
                -{formatCurrency(metrics.maxLoss)}
              </div>
              <div className="text-xs text-muted-foreground">
                {formatPercentage(metrics.maxLossPercent / 100)} of portfolio
              </div>
              {data.stopLoss && (
                <div className="text-xs text-muted-foreground">
                  Stop: {formatCurrency(data.stopLoss)}
                </div>
              )}
            </div>

            {/* Potential Gain */}
            <div className="rounded-lg border border-green-500/30 bg-green-500/5 p-3 space-y-2">
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingUp className="h-3 w-3" />
                Potential Gain
              </div>
              <div className="text-xl font-bold text-green-500">
                +{formatCurrency(metrics.potentialGain)}
              </div>
              <div className="text-xs text-muted-foreground">
                {formatPercentage(metrics.potentialGainPercent / 100)} of portfolio
              </div>
              {data.takeProfit && (
                <div className="text-xs text-muted-foreground">
                  Target: {formatCurrency(data.takeProfit)}
                </div>
              )}
            </div>
          </div>

          {!isGoodRiskReward && (
            <div className="rounded-md bg-yellow-500/10 border border-yellow-500/30 p-3 text-xs text-yellow-600">
              <p className="font-medium">⚠️ Suboptimal Risk/Reward</p>
              <p className="mt-1 text-muted-foreground">
                Consider adjusting your take profit target or stop loss for a better risk/reward ratio (target: 1.5 or higher)
              </p>
            </div>
          )}
        </div>

        <Separator />

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-muted-foreground">Available Balance</span>
            <div className="font-semibold mt-1">{formatCurrency(data.availableBalance)}</div>
          </div>
          <div>
            <span className="text-muted-foreground">Entry Price</span>
            <div className="font-semibold mt-1">{formatCurrency(data.entryPrice)}</div>
          </div>
        </div>

        {/* Warnings */}
        {(metrics.riskLevel === 'HIGH' || metrics.riskLevel === 'CRITICAL') && (
          <div className={cn(
            'rounded-lg border p-3 text-xs space-y-1',
            metrics.riskLevel === 'CRITICAL'
              ? 'border-red-500/30 bg-red-500/10 text-red-500'
              : 'border-orange-500/30 bg-orange-500/10 text-orange-500'
          )}>
            <p className="font-medium flex items-center gap-1">
              <AlertTriangle className="h-4 w-4" />
              {metrics.riskLevel === 'CRITICAL' ? 'Critical Risk Detected' : 'High Risk Warning'}
            </p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              {metrics.positionSizePercent > 30 && (
                <li>Position size exceeds 30% of portfolio</li>
              )}
              {metrics.maxLossPercent > 10 && (
                <li>Potential loss exceeds 10% of portfolio</li>
              )}
              {data.leverage && data.leverage >= 5 && (
                <li>High leverage ({data.leverage}x) amplifies risk</li>
              )}
              {!data.stopLoss && (
                <li>No stop loss set - consider adding protection</li>
              )}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RiskCalculator;
