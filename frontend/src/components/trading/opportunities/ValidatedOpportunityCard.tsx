import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Sparkles,
  TrendingUp,
  TrendingDown,
  Shield,
  Target,
  DollarSign,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Zap,
  CheckCircle
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';
import type { Opportunity } from './types';

interface ValidatedOpportunityCardProps {
  opportunity: Opportunity;
  onExecute: (opportunityId: string, positionSize: number) => void;
  onApplyToForm: (opportunity: Opportunity) => void;
  isExecuting?: boolean;
  portfolioValue: number;
}

export const ValidatedOpportunityCard: React.FC<ValidatedOpportunityCardProps> = ({
  opportunity,
  onExecute,
  onApplyToForm,
  isExecuting = false,
  portfolioValue
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [positionSize, setPositionSize] = useState(opportunity.suggested_position_size);

  const SideIcon = opportunity.side === 'buy' ? TrendingUp : TrendingDown;
  const sideColor = opportunity.side === 'buy' ? 'text-green-500' : 'text-red-500';
  const sideBg = opportunity.side === 'buy' ? 'bg-green-500/10' : 'bg-red-500/10';

  // Calculate adjusted metrics based on position size
  const adjustedMetrics = useMemo(() => {
    const sizeRatio = positionSize / opportunity.suggested_position_size;
    return {
      maxRisk: opportunity.max_risk * sizeRatio,
      maxRiskPercent: portfolioValue > 0 ? (opportunity.max_risk * sizeRatio / portfolioValue) * 100 : 0,
      potentialGain: opportunity.potential_gain * sizeRatio,
      potentialGainPercent: portfolioValue > 0 ? (opportunity.potential_gain * sizeRatio / portfolioValue) * 100 : 0,
      positionPercent: portfolioValue > 0 ? (positionSize / portfolioValue) * 100 : 0
    };
  }, [positionSize, opportunity, portfolioValue]);

  // Check if expired
  const isExpired = useMemo(() => {
    return new Date(opportunity.expires_at) < new Date();
  }, [opportunity.expires_at]);

  const timeRemaining = useMemo(() => {
    const now = new Date();
    const expires = new Date(opportunity.expires_at);
    const diff = expires.getTime() - now.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    return { minutes, seconds, expired: diff <= 0 };
  }, [opportunity.expires_at]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative"
    >
      <Card className={cn(
        "border-2 transition-all",
        "bg-gradient-to-br from-purple-500/5 via-blue-500/5 to-green-500/5",
        "border-purple-500/30 hover:border-purple-500/50",
        "shadow-lg hover:shadow-xl",
        isExpired && "opacity-60 border-gray-500/30"
      )}>
        {/* AI Validated Badge */}
        <div className="absolute -top-3 left-4 z-10">
          <Badge className="bg-gradient-to-r from-purple-600 to-blue-600 text-white gap-1 px-3 py-1">
            <Sparkles className="h-3 w-3" />
            AI VALIDATED
          </Badge>
        </div>

        <CardContent className="pt-6 space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold">{opportunity.symbol}</h3>
                <Badge variant="outline" className={cn('gap-1', sideBg, sideColor)}>
                  <SideIcon className="h-3 w-3" />
                  {opportunity.side.toUpperCase()}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">{opportunity.strategy}</p>
            </div>

            {/* Consensus Score */}
            <div className="text-right">
              <div className="flex items-center gap-1">
                <span className="text-2xl font-bold text-purple-500">
                  {opportunity.validation?.consensus_score || opportunity.confidence}%
                </span>
                <CheckCircle className="h-5 w-5 text-green-500" />
              </div>
              <p className="text-xs text-muted-foreground">Consensus</p>
            </div>
          </div>

          {/* Model Agreement */}
          {opportunity.validation?.model_responses && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Models:</span>
              {opportunity.validation.model_responses.map((model, idx) => (
                <Badge key={idx} variant="outline" className="gap-1">
                  {model.model === 'gpt4' && '🤖'}
                  {model.model === 'claude' && '🧠'}
                  {model.model === 'gemini' && '✨'}
                  {model.recommendation === opportunity.side.toUpperCase() ? (
                    <CheckCircle className="h-3 w-3 text-green-500" />
                  ) : null}
                </Badge>
              ))}
            </div>
          )}

          <Separator />

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="space-y-1">
              <span className="text-muted-foreground">Entry Price</span>
              <p className="font-semibold">{formatCurrency(opportunity.entry_price)}</p>
            </div>
            <div className="space-y-1">
              <span className="text-muted-foreground">Risk/Reward</span>
              <p className="font-semibold text-green-500">1:{opportunity.risk_reward_ratio.toFixed(2)}</p>
            </div>
            <div className="space-y-1">
              <span className="text-muted-foreground">Stop Loss</span>
              <p className="font-semibold text-red-500">{formatCurrency(opportunity.stop_loss)}</p>
            </div>
            <div className="space-y-1">
              <span className="text-muted-foreground">Take Profit</span>
              <p className="font-semibold text-green-500">{formatCurrency(opportunity.take_profit)}</p>
            </div>
          </div>

          <Separator />

          {/* Position Sizing */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Position Size</span>
              <span className="text-muted-foreground">
                {formatCurrency(positionSize)} ({formatPercentage(adjustedMetrics.positionPercent)} of portfolio)
              </span>
            </div>
            <Slider
              value={[positionSize]}
              min={opportunity.suggested_position_size * 0.5}
              max={opportunity.suggested_position_size * 2}
              step={opportunity.suggested_position_size * 0.1}
              onValueChange={([value]) => setPositionSize(value)}
              className="cursor-pointer"
              disabled={isExecuting || isExpired}
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Min: {formatCurrency(opportunity.suggested_position_size * 0.5)}</span>
              <span>Suggested: {formatCurrency(opportunity.suggested_position_size)}</span>
              <span>Max: {formatCurrency(opportunity.suggested_position_size * 2)}</span>
            </div>
          </div>

          {/* Risk/Reward Display */}
          <div className="grid grid-cols-2 gap-3">
            <div className={cn(
              "rounded-lg border p-3 space-y-1",
              "border-red-500/30 bg-red-500/5"
            )}>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Shield className="h-3 w-3" />
                Max Risk
              </div>
              <p className="text-lg font-bold text-red-500">
                -{formatCurrency(adjustedMetrics.maxRisk)}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatPercentage(adjustedMetrics.maxRiskPercent)} of portfolio
              </p>
            </div>

            <div className={cn(
              "rounded-lg border p-3 space-y-1",
              "border-green-500/30 bg-green-500/5"
            )}>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Target className="h-3 w-3" />
                Potential Gain
              </div>
              <p className="text-lg font-bold text-green-500">
                +{formatCurrency(adjustedMetrics.potentialGain)}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatPercentage(adjustedMetrics.potentialGainPercent)} of portfolio
              </p>
            </div>
          </div>

          {/* Time Remaining */}
          {!isExpired ? (
            <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <AlertCircle className="h-3 w-3" />
              <span>
                Valid for: {timeRemaining.minutes}m {timeRemaining.seconds}s
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2 text-xs text-red-500">
              <AlertCircle className="h-3 w-3" />
              <span>Opportunity Expired - Rescan Required</span>
            </div>
          )}

          {/* Details Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
            className="w-full"
          >
            {showDetails ? (
              <>
                <ChevronUp className="mr-2 h-4 w-4" />
                Hide Details
              </>
            ) : (
              <>
                <ChevronDown className="mr-2 h-4 w-4" />
                Show Details
              </>
            )}
          </Button>

          {/* Expanded Details */}
          {showDetails && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="space-y-3 pt-3 border-t"
            >
              {opportunity.reasoning && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">AI Reasoning:</p>
                  <p className="text-sm">{opportunity.reasoning}</p>
                </div>
              )}

              {opportunity.validation?.reason && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Validation Notes:</p>
                  <p className="text-sm">{opportunity.validation.reason}</p>
                </div>
              )}

              {opportunity.indicators && Object.keys(opportunity.indicators).length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">Technical Indicators:</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(opportunity.indicators).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between">
                        <span className="text-muted-foreground">{key}:</span>
                        <span className="font-medium">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          <Separator />

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              onClick={() => onExecute(opportunity.id, positionSize)}
              disabled={isExecuting || isExpired}
            >
              {isExecuting ? (
                <>
                  <Zap className="mr-2 h-4 w-4 animate-pulse" />
                  Executing...
                </>
              ) : (
                <>
                  <Zap className="mr-2 h-4 w-4" />
                  Execute Trade
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => onApplyToForm(opportunity)}
              disabled={isExecuting}
            >
              Apply to Form
            </Button>
          </div>

          {/* Cost Note */}
          <p className="text-xs text-center text-muted-foreground">
            <DollarSign className="inline h-3 w-3" /> Execution will cost 2 credits
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default ValidatedOpportunityCard;
