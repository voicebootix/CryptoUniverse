import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { PieChart, TrendingUp, TrendingDown, AlertTriangle, Info } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';

interface Position {
  symbol: string;
  amount: number;
  value: number;
  percentage: number;
}

interface PortfolioState {
  totalValue: number;
  positions: Position[];
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY HIGH';
}

interface TradeImpact {
  symbol: string;
  action: 'buy' | 'sell';
  amount: number;
  estimatedCost: number;
}

interface PortfolioImpactPreviewProps {
  currentPortfolio: PortfolioState;
  proposedTrade?: TradeImpact;
  compact?: boolean;
}

const RISK_LEVEL_CONFIG = {
  LOW: {
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    label: 'Low Risk'
  },
  MEDIUM: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    label: 'Medium Risk'
  },
  HIGH: {
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    label: 'High Risk'
  },
  'VERY HIGH': {
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    label: 'Very High Risk'
  }
};

const SYMBOL_COLORS = [
  'bg-blue-500',
  'bg-purple-500',
  'bg-green-500',
  'bg-yellow-500',
  'bg-pink-500',
  'bg-indigo-500',
  'bg-red-500',
  'bg-cyan-500'
];

export const PortfolioImpactPreview: React.FC<PortfolioImpactPreviewProps> = ({
  currentPortfolio,
  proposedTrade,
  compact = false
}) => {
  const projectedPortfolio = useMemo((): PortfolioState => {
    if (!proposedTrade) return currentPortfolio;

    const newTotalValue =
      proposedTrade.action === 'buy'
        ? currentPortfolio.totalValue
        : currentPortfolio.totalValue;

    const updatedPositions = [...currentPortfolio.positions];
    const existingPositionIndex = updatedPositions.findIndex(
      (p) => p.symbol === proposedTrade.symbol
    );

    if (proposedTrade.action === 'buy') {
      if (existingPositionIndex >= 0) {
        updatedPositions[existingPositionIndex] = {
          ...updatedPositions[existingPositionIndex],
          value: updatedPositions[existingPositionIndex].value + proposedTrade.estimatedCost,
          amount: updatedPositions[existingPositionIndex].amount + proposedTrade.amount
        };
      } else {
        updatedPositions.push({
          symbol: proposedTrade.symbol,
          amount: proposedTrade.amount,
          value: proposedTrade.estimatedCost,
          percentage: 0
        });
      }
    } else if (proposedTrade.action === 'sell' && existingPositionIndex >= 0) {
      const position = updatedPositions[existingPositionIndex];
      const newValue = Math.max(0, position.value - proposedTrade.estimatedCost);
      const newAmount = Math.max(0, position.amount - proposedTrade.amount);

      if (newValue === 0 || newAmount === 0) {
        updatedPositions.splice(existingPositionIndex, 1);
      } else {
        updatedPositions[existingPositionIndex] = {
          ...position,
          value: newValue,
          amount: newAmount
        };
      }
    }

    // Recalculate percentages
    const totalValue = updatedPositions.reduce((sum, p) => sum + p.value, 0);
    const positionsWithPercentages = updatedPositions.map((p) => ({
      ...p,
      percentage: totalValue > 0 ? (p.value / totalValue) * 100 : 0
    }));

    // Determine new risk level based on concentration
    const maxConcentration = Math.max(...positionsWithPercentages.map((p) => p.percentage), 0);
    let newRiskLevel: PortfolioState['riskLevel'] = 'LOW';
    if (maxConcentration > 60) newRiskLevel = 'VERY HIGH';
    else if (maxConcentration > 45) newRiskLevel = 'HIGH';
    else if (maxConcentration > 30) newRiskLevel = 'MEDIUM';

    return {
      totalValue: newTotalValue,
      positions: positionsWithPercentages,
      riskLevel: newRiskLevel
    };
  }, [currentPortfolio, proposedTrade]);

  const impactMetrics = useMemo(() => {
    if (!proposedTrade) return null;

    const currentConfig = RISK_LEVEL_CONFIG[currentPortfolio.riskLevel];
    const projectedConfig = RISK_LEVEL_CONFIG[projectedPortfolio.riskLevel];
    const riskIncreased = ['LOW', 'MEDIUM', 'HIGH', 'VERY HIGH'].indexOf(projectedPortfolio.riskLevel) >
      ['LOW', 'MEDIUM', 'HIGH', 'VERY HIGH'].indexOf(currentPortfolio.riskLevel);

    const positionChanges = currentPortfolio.positions.map((currentPos) => {
      const projectedPos = projectedPortfolio.positions.find((p) => p.symbol === currentPos.symbol);
      const percentageChange = projectedPos
        ? projectedPos.percentage - currentPos.percentage
        : -currentPos.percentage;

      return {
        symbol: currentPos.symbol,
        currentPercentage: currentPos.percentage,
        projectedPercentage: projectedPos?.percentage || 0,
        change: percentageChange
      };
    });

    // Add new positions
    projectedPortfolio.positions.forEach((projectedPos) => {
      if (!currentPortfolio.positions.find((p) => p.symbol === projectedPos.symbol)) {
        positionChanges.push({
          symbol: projectedPos.symbol,
          currentPercentage: 0,
          projectedPercentage: projectedPos.percentage,
          change: projectedPos.percentage
        });
      }
    });

    return {
      riskIncreased,
      currentRiskConfig: currentConfig,
      projectedRiskConfig: projectedConfig,
      positionChanges: positionChanges.sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
    };
  }, [currentPortfolio, projectedPortfolio, proposedTrade]);

  if (compact) {
    return (
      <Card>
        <CardContent className="pt-4 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Portfolio Value</span>
            <div className="flex items-center gap-2">
              <span className="font-medium">{formatCurrency(currentPortfolio.totalValue)}</span>
              {proposedTrade && (
                <>
                  <span className="text-muted-foreground">→</span>
                  <span className="font-medium">{formatCurrency(projectedPortfolio.totalValue)}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Risk Level</span>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={RISK_LEVEL_CONFIG[currentPortfolio.riskLevel].color}>
                {RISK_LEVEL_CONFIG[currentPortfolio.riskLevel].label}
              </Badge>
              {proposedTrade && impactMetrics?.riskIncreased && (
                <>
                  <span className="text-muted-foreground">→</span>
                  <Badge variant="outline" className={RISK_LEVEL_CONFIG[projectedPortfolio.riskLevel].color}>
                    {RISK_LEVEL_CONFIG[projectedPortfolio.riskLevel].label}
                  </Badge>
                </>
              )}
            </div>
          </div>
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
          <CardTitle className="flex items-center gap-2">
            <PieChart className="h-5 w-5 text-blue-500" />
            Portfolio Impact Preview
          </CardTitle>
          <CardDescription>
            {proposedTrade ? 'See how this trade will affect your portfolio' : 'Current portfolio allocation'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Total Value Comparison */}
          <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Total Portfolio Value</span>
              {proposedTrade && impactMetrics?.riskIncreased && (
                <Badge variant="outline" className="text-orange-500 gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Risk Increase
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3 text-2xl font-bold">
              <span>{formatCurrency(currentPortfolio.totalValue)}</span>
              {proposedTrade && (
                <>
                  <TrendingUp className="h-5 w-5 text-muted-foreground" />
                  <span className={cn(
                    projectedPortfolio.totalValue >= currentPortfolio.totalValue
                      ? 'text-green-500'
                      : 'text-red-500'
                  )}>
                    {formatCurrency(projectedPortfolio.totalValue)}
                  </span>
                </>
              )}
            </div>
          </div>

          <Separator />

          {/* Position Allocation */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium">Position Allocation</h4>

            {proposedTrade && impactMetrics ? (
              <div className="space-y-3">
                {impactMetrics.positionChanges.map((change, index) => (
                  <div key={change.symbol} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <div
                          className={cn('h-3 w-3 rounded-full', SYMBOL_COLORS[index % SYMBOL_COLORS.length])}
                        />
                        <span className="font-medium">{change.symbol}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">
                          {formatPercentage(change.currentPercentage)}
                        </span>
                        <span className="text-muted-foreground">→</span>
                        <span className={cn(
                          'font-medium',
                          change.change > 0 ? 'text-green-500' : 'text-red-500'
                        )}>
                          {formatPercentage(change.projectedPercentage)}
                        </span>
                        <span className={cn(
                          'text-xs',
                          change.change > 0 ? 'text-green-500' : 'text-red-500'
                        )}>
                          ({change.change > 0 ? '+' : ''}{formatPercentage(change.change)})
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Progress value={change.currentPercentage} className="h-2 flex-1 opacity-50" />
                      <Progress value={change.projectedPercentage} className="h-2 flex-1" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {currentPortfolio.positions.map((position, index) => (
                  <div key={position.symbol} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <div
                          className={cn('h-3 w-3 rounded-full', SYMBOL_COLORS[index % SYMBOL_COLORS.length])}
                        />
                        <span className="font-medium">{position.symbol}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-muted-foreground">{formatCurrency(position.value)}</span>
                        <span className="font-medium">{formatPercentage(position.percentage)}</span>
                      </div>
                    </div>
                    <Progress value={position.percentage} className="h-2" />
                  </div>
                ))}
              </div>
            )}
          </div>

          <Separator />

          {/* Risk Assessment */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium">Risk Assessment</h4>
            <div className="flex items-center gap-3">
              <Badge
                variant="outline"
                className={cn('flex-1 justify-center py-2', currentPortfolio.riskLevel === projectedPortfolio.riskLevel ? '' : 'opacity-50')}
              >
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs text-muted-foreground">Current</span>
                  <span className={RISK_LEVEL_CONFIG[currentPortfolio.riskLevel].color}>
                    {RISK_LEVEL_CONFIG[currentPortfolio.riskLevel].label}
                  </span>
                </div>
              </Badge>
              {proposedTrade && currentPortfolio.riskLevel !== projectedPortfolio.riskLevel && (
                <>
                  <TrendingUp className={cn(
                    'h-5 w-5',
                    impactMetrics?.riskIncreased ? 'text-orange-500' : 'text-green-500'
                  )} />
                  <Badge
                    variant="outline"
                    className={cn('flex-1 justify-center py-2')}
                  >
                    <div className="flex flex-col items-center gap-1">
                      <span className="text-xs text-muted-foreground">Projected</span>
                      <span className={RISK_LEVEL_CONFIG[projectedPortfolio.riskLevel].color}>
                        {RISK_LEVEL_CONFIG[projectedPortfolio.riskLevel].label}
                      </span>
                    </div>
                  </Badge>
                </>
              )}
            </div>
          </div>

          {/* Warning if risk increases significantly */}
          {proposedTrade && impactMetrics?.riskIncreased && (
            <div className="flex gap-2 rounded-lg border border-orange-500/30 bg-orange-500/10 p-3 text-sm">
              <Info className="h-4 w-4 text-orange-500 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium text-orange-500">Risk Level Increase</p>
                <p className="text-xs text-muted-foreground">
                  This trade will increase your portfolio risk level. Consider adjusting position size
                  or reviewing your risk management strategy.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default PortfolioImpactPreview;
