import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  Shield,
  Target,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';
import type { Opportunity } from './types';

interface OpportunityCardProps {
  opportunity: Opportunity;
  onValidate: (opportunityId: string) => void;
  onApplyToForm: (opportunity: Opportunity) => void;
  isValidating?: boolean;
  portfolioValue: number;
}

export const OpportunityCard: React.FC<OpportunityCardProps> = ({
  opportunity,
  onValidate,
  onApplyToForm,
  isValidating = false,
  portfolioValue
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const SideIcon = opportunity.side === 'buy' ? TrendingUp : TrendingDown;
  const sideColor = opportunity.side === 'buy' ? 'text-green-500' : 'text-red-500';
  const sideBg = opportunity.side === 'buy' ? 'bg-green-500/10' : 'bg-red-500/10';

  const positionPercent = useMemo(() => {
    return portfolioValue > 0 ? (opportunity.suggested_position_size / portfolioValue) * 100 : 0;
  }, [opportunity.suggested_position_size, portfolioValue]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <Card className={cn(
        "border transition-all",
        "bg-muted/30",
        "hover:border-muted-foreground/30"
      )}>
        <CardContent className="pt-4 space-y-4">
          {/* Warning Badge */}
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1 text-yellow-600 border-yellow-600/50">
              <AlertTriangle className="h-3 w-3" />
              Not AI-Validated
            </Badge>
          </div>

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

            {/* Confidence Score */}
            <div className="text-right">
              <div className="text-2xl font-bold text-muted-foreground">
                {opportunity.confidence}%
              </div>
              <p className="text-xs text-muted-foreground">Confidence</p>
            </div>
          </div>

          {/* Validation Reason */}
          {opportunity.validationReason && (
            <div className="rounded-md bg-yellow-500/10 border border-yellow-500/30 p-3 text-xs">
              <p className="font-medium text-yellow-600 mb-1">Why not validated:</p>
              <p className="text-muted-foreground">{opportunity.validationReason}</p>
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
              <p className="font-semibold">1:{opportunity.risk_reward_ratio.toFixed(2)}</p>
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

          {/* Position Size Info */}
          <div className="rounded-lg border bg-muted/50 p-3 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Suggested Position</span>
              <span className="font-semibold">{formatCurrency(opportunity.suggested_position_size)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">% of Portfolio</span>
              <span className="font-semibold">{formatPercentage(positionPercent)}</span>
            </div>
          </div>

          {/* Risk/Reward Display */}
          <div className="grid grid-cols-2 gap-3">
            <div className={cn(
              "rounded-lg border p-3 space-y-1",
              "border-red-500/20 bg-red-500/5"
            )}>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Shield className="h-3 w-3" />
                Max Risk
              </div>
              <p className="text-base font-bold text-red-500">
                -{formatCurrency(opportunity.max_risk)}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatPercentage(opportunity.max_risk_percent)} of portfolio
              </p>
            </div>

            <div className={cn(
              "rounded-lg border p-3 space-y-1",
              "border-green-500/20 bg-green-500/5"
            )}>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Target className="h-3 w-3" />
                Potential Gain
              </div>
              <p className="text-base font-bold text-green-500">
                +{formatCurrency(opportunity.potential_gain)}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatPercentage(opportunity.potential_gain_percent)} of portfolio
              </p>
            </div>
          </div>

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
                  <p className="text-xs font-medium text-muted-foreground">Strategy Reasoning:</p>
                  <p className="text-sm">{opportunity.reasoning}</p>
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
              variant="outline"
              className="flex-1"
              onClick={() => onValidate(opportunity.id)}
              disabled={isValidating}
            >
              {isValidating ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Validating...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Validate Now (2 credits)
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => onApplyToForm(opportunity)}
              disabled={isValidating}
            >
              Apply to Form
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default OpportunityCard;
