import React from 'react';
import { motion } from 'framer-motion';
import { Brain, DollarSign, TrendingUp, Zap, Activity, Award, Target, Sparkles } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';

interface AICallStats {
  type: string;
  count: number;
  totalCost: number;
  successRate?: number;
}

interface AIUsageData {
  remainingCredits: number;
  totalCredits: number;
  todayCalls: number;
  todayCost: number;
  profitGenerated: number;
  roi: number;
  callBreakdown?: AICallStats[];
  topPerformingModel?: string;
  avgResponseTime?: number;
}

interface AIUsageStatsProps {
  usageData?: AIUsageData;
  isLoading?: boolean;
  onPurchaseCredits?: () => void;
  compact?: boolean;
}

const CALL_TYPE_CONFIG: Record<string, { icon: typeof Brain; color: string; label: string }> = {
  opportunity_scan: {
    icon: Target,
    color: 'text-blue-500',
    label: 'Opportunity Scans'
  },
  trade_validation: {
    icon: Sparkles,
    color: 'text-purple-500',
    label: 'Trade Validations'
  },
  market_analysis: {
    icon: Activity,
    color: 'text-green-500',
    label: 'Market Analysis'
  },
  risk_assessment: {
    icon: Award,
    color: 'text-yellow-500',
    label: 'Risk Assessments'
  },
  portfolio_review: {
    icon: Brain,
    color: 'text-pink-500',
    label: 'Portfolio Reviews'
  },
  consensus_decision: {
    icon: Zap,
    color: 'text-orange-500',
    label: 'Consensus Decisions'
  }
};

export const AIUsageStats: React.FC<AIUsageStatsProps> = ({
  usageData,
  isLoading = false,
  onPurchaseCredits,
  compact = false
}) => {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-5 w-5 animate-pulse text-purple-500" />
            AI Usage Today
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-muted animate-pulse rounded" />
              <div className="h-2 bg-muted animate-pulse rounded w-2/3" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  if (!usageData) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-5 w-5 text-muted-foreground" />
            AI Usage Today
          </CardTitle>
          <CardDescription>No usage data available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <Zap className="h-12 w-12 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              Start using AI features to track your usage and ROI
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const creditUsagePercent = usageData.totalCredits > 0
    ? ((usageData.totalCredits - usageData.remainingCredits) / usageData.totalCredits) * 100
    : 0;

  const isLowCredits = usageData.remainingCredits < 100;
  const isCriticalCredits = usageData.remainingCredits < 50;

  if (compact) {
    return (
      <Card className={cn(
        isCriticalCredits && 'border-red-500/30 bg-red-500/5'
      )}>
        <CardContent className="pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Credits</span>
            <div className="flex items-center gap-2">
              <span className={cn(
                'text-lg font-bold',
                isCriticalCredits ? 'text-red-500' : isLowCredits ? 'text-yellow-500' : ''
              )}>
                {usageData.remainingCredits}
              </span>
              {(isLowCredits || isCriticalCredits) && onPurchaseCredits && (
                <button
                  onClick={onPurchaseCredits}
                  className="text-xs text-blue-500 hover:underline"
                >
                  Add More
                </button>
              )}
            </div>
          </div>
          {usageData.profitGenerated > 0 && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Today's ROI</span>
              <span className="font-semibold text-green-500">
                {usageData.roi.toFixed(1)}x
              </span>
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
      <Card className={cn(
        isCriticalCredits && 'border-red-500/30'
      )}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            Your AI Usage Today
          </CardTitle>
          <CardDescription>
            Track your AI calls, costs, and value generated
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Credits Overview */}
          <div className={cn(
            'rounded-lg border p-4 space-y-3',
            isCriticalCredits
              ? 'border-red-500/30 bg-red-500/5'
              : isLowCredits
              ? 'border-yellow-500/30 bg-yellow-500/5'
              : 'bg-muted/30'
          )}>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Remaining Credits</div>
                <div className={cn(
                  'text-3xl font-bold',
                  isCriticalCredits ? 'text-red-500' : isLowCredits ? 'text-yellow-500' : ''
                )}>
                  {usageData.remainingCredits}
                </div>
              </div>
              {onPurchaseCredits && (
                <button
                  onClick={onPurchaseCredits}
                  className={cn(
                    'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                    isCriticalCredits
                      ? 'bg-red-500 hover:bg-red-600 text-white'
                      : 'bg-primary hover:bg-primary/90 text-primary-foreground'
                  )}
                >
                  {isCriticalCredits ? 'Buy Now' : 'Add Credits'}
                </button>
              )}
            </div>
            <Progress value={100 - creditUsagePercent} className="h-2" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{usageData.totalCredits - usageData.remainingCredits} used</span>
              <span>{usageData.totalCredits} total</span>
            </div>
            {isCriticalCredits && (
              <div className="flex items-start gap-2 rounded-md bg-red-500/10 border border-red-500/20 p-2 text-xs text-red-500">
                <Zap className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <p>
                  <strong>Critical:</strong> Low credits remaining. Purchase more to continue using AI features.
                </p>
              </div>
            )}
          </div>

          <Separator />

          {/* Usage Breakdown */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Today's AI Calls: {usageData.todayCalls}</span>
              <span className="text-muted-foreground">
                Total Cost: {formatCurrency(usageData.todayCost)}
              </span>
            </div>

            <div className="space-y-2">
              {usageData.callBreakdown?.map((call, index) => {
                const config = CALL_TYPE_CONFIG[call.type] || {
                  icon: Brain,
                  color: 'text-gray-500',
                  label: call.type.replace(/_/g, ' ')
                };
                const CallIcon = config.icon;

                return (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-md border bg-muted/30 p-2 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <CallIcon className={cn('h-4 w-4', config.color)} />
                      <span>{config.label}</span>
                      <Badge variant="outline" className="text-xs">
                        {call.count}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      {call.successRate !== undefined && (
                        <span className={cn(
                          'font-medium',
                          call.successRate >= 90 ? 'text-green-500' : call.successRate >= 70 ? 'text-yellow-500' : 'text-red-500'
                        )}>
                          {formatPercentage(call.successRate)} success
                        </span>
                      )}
                      <span className="text-muted-foreground">{formatCurrency(call.totalCost)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <Separator />

          {/* ROI Metrics */}
          {usageData.profitGenerated > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium">Value Generated</h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border bg-green-500/5 border-green-500/20 p-3 space-y-1">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <DollarSign className="h-3 w-3" />
                    Profit Today
                  </div>
                  <div className="text-xl font-bold text-green-500">
                    +{formatCurrency(usageData.profitGenerated)}
                  </div>
                </div>
                <div className="rounded-lg border bg-blue-500/5 border-blue-500/20 p-3 space-y-1">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <TrendingUp className="h-3 w-3" />
                    ROI
                  </div>
                  <div className="text-xl font-bold text-blue-500">
                    {usageData.roi.toFixed(1)}x
                  </div>
                </div>
              </div>
              <div className="rounded-md bg-muted/50 p-3 text-xs text-center text-muted-foreground">
                For every $1 spent on AI, you've earned{' '}
                <span className="font-semibold text-green-500">
                  {formatCurrency(usageData.roi)}
                </span>
              </div>
            </div>
          )}

          {/* Additional Stats */}
          {(usageData.topPerformingModel || usageData.avgResponseTime) && (
            <>
              <Separator />
              <div className="grid grid-cols-2 gap-3 text-xs">
                {usageData.topPerformingModel && (
                  <div>
                    <span className="text-muted-foreground">Top Model</span>
                    <div className="font-semibold mt-1">{usageData.topPerformingModel}</div>
                  </div>
                )}
                {usageData.avgResponseTime && (
                  <div>
                    <span className="text-muted-foreground">Avg. Response</span>
                    <div className="font-semibold mt-1">{usageData.avgResponseTime.toFixed(1)}s</div>
                  </div>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default AIUsageStats;
