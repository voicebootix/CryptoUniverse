import React from 'react';
import { motion } from 'framer-motion';
import {
  Target,
  Brain,
  BarChart3,
  Shield,
  Equal,
  Sparkles,
  Activity,
  Loader,
  DollarSign
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn, formatCurrency } from '@/lib/utils';

interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: typeof Brain;
  color: string;
  gradientFrom?: string;
  cost?: number;
  isLoading?: boolean;
  disabled?: boolean;
  requiresCredits?: boolean;
}

interface QuickActionBarProps {
  onScanOpportunities?: () => void;
  onGetAIOpinion?: () => void;
  onValidateTrade?: () => void;
  onAssessRisk?: () => void;
  onRebalancePortfolio?: () => void;
  onFinalConsensus?: () => void;
  loadingActions?: Set<string>;
  disabledActions?: Set<string>;
  availableCredits?: number;
  compact?: boolean;
  vertical?: boolean;
}

const DEFAULT_ACTIONS: QuickAction[] = [
  {
    id: 'scan_opportunities',
    label: 'Scan Opportunities',
    description: 'AI-powered market scanning across all exchanges',
    icon: Target,
    color: 'text-blue-500',
    gradientFrom: 'from-blue-500',
    cost: 3,
    requiresCredits: true
  },
  {
    id: 'get_ai_opinion',
    label: 'Get AI Opinion',
    description: 'Multi-model consensus on current market conditions',
    icon: Brain,
    color: 'text-purple-500',
    gradientFrom: 'from-purple-500',
    cost: 2,
    requiresCredits: true
  },
  {
    id: 'validate_trade',
    label: 'Validate Trade',
    description: 'Verify trade parameters with AI consensus',
    icon: Sparkles,
    color: 'text-green-500',
    gradientFrom: 'from-green-500',
    cost: 2,
    requiresCredits: true
  },
  {
    id: 'assess_risk',
    label: 'Assess Risk',
    description: 'Comprehensive portfolio risk analysis',
    icon: Shield,
    color: 'text-yellow-500',
    gradientFrom: 'from-yellow-500',
    cost: 2,
    requiresCredits: true
  },
  {
    id: 'rebalance_portfolio',
    label: 'Rebalance Portfolio',
    description: 'AI-recommended portfolio rebalancing strategy',
    icon: Activity,
    color: 'text-orange-500',
    gradientFrom: 'from-orange-500',
    cost: 3,
    requiresCredits: true
  },
  {
    id: 'final_consensus',
    label: 'Final Consensus',
    description: 'Get final decision with highest confidence threshold',
    icon: Equal,
    color: 'text-indigo-500',
    gradientFrom: 'from-indigo-500',
    cost: 4,
    requiresCredits: true
  }
];

export const QuickActionBar: React.FC<QuickActionBarProps> = ({
  onScanOpportunities,
  onGetAIOpinion,
  onValidateTrade,
  onAssessRisk,
  onRebalancePortfolio,
  onFinalConsensus,
  loadingActions = new Set(),
  disabledActions = new Set(),
  availableCredits,
  compact = false,
  vertical = false
}) => {
  const actionHandlers: Record<string, (() => void) | undefined> = {
    scan_opportunities: onScanOpportunities,
    get_ai_opinion: onGetAIOpinion,
    validate_trade: onValidateTrade,
    assess_risk: onAssessRisk,
    rebalance_portfolio: onRebalancePortfolio,
    final_consensus: onFinalConsensus
  };

  const handleAction = (actionId: string) => {
    const handler = actionHandlers[actionId];
    if (handler && !loadingActions.has(actionId) && !disabledActions.has(actionId)) {
      handler();
    }
  };

  const canAfford = (cost: number = 0) => {
    if (availableCredits === undefined) return true;
    return availableCredits >= cost;
  };

  const actions = DEFAULT_ACTIONS.filter((action) => {
    return actionHandlers[action.id] !== undefined;
  }).map((action) => ({
    ...action,
    isLoading: loadingActions.has(action.id),
    disabled: disabledActions.has(action.id) || (action.requiresCredits && !canAfford(action.cost || 0))
  }));

  if (compact) {
    return (
      <div className={cn(
        'flex gap-2',
        vertical ? 'flex-col' : 'flex-wrap'
      )}>
        {actions.map((action) => {
          const ActionIcon = action.icon;
          const insufficientCredits = action.requiresCredits && !canAfford(action.cost || 0);

          return (
            <TooltipProvider key={action.id}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAction(action.id)}
                    disabled={action.disabled || action.isLoading}
                    className={cn(
                      'gap-2',
                      insufficientCredits && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {action.isLoading ? (
                      <Loader className="h-4 w-4 animate-spin" />
                    ) : (
                      <ActionIcon className={cn('h-4 w-4', action.color)} />
                    )}
                    {action.label}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <div className="space-y-1">
                    <p>{action.description}</p>
                    {action.cost && (
                      <p className="text-xs text-muted-foreground">
                        Cost: {action.cost} credits
                      </p>
                    )}
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          );
        })}
      </div>
    );
  }

  return (
    <Card className="p-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold">Quick AI Actions</h3>
            <p className="text-xs text-muted-foreground">
              One-click access to AI-powered trading features
            </p>
          </div>
          {availableCredits !== undefined && (
            <Badge variant="outline" className="gap-1">
              <DollarSign className="h-3 w-3" />
              {availableCredits} Credits
            </Badge>
          )}
        </div>

        <div className={cn(
          'grid gap-3',
          vertical ? 'grid-cols-1' : 'grid-cols-2 lg:grid-cols-3'
        )}>
          {actions.map((action, index) => {
            const ActionIcon = action.icon;
            const insufficientCredits = action.requiresCredits && !canAfford(action.cost || 0);

            return (
              <motion.div
                key={action.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <button
                  onClick={() => handleAction(action.id)}
                  disabled={action.disabled || action.isLoading}
                  className={cn(
                    'w-full rounded-lg border bg-card p-4 text-left transition-all hover:border-primary/50 hover:shadow-md',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    action.isLoading && 'border-primary/50 shadow-md',
                    insufficientCredits && 'border-red-500/30 bg-red-500/5'
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        {action.isLoading ? (
                          <Loader className={cn('h-5 w-5 animate-spin', action.color)} />
                        ) : (
                          <ActionIcon className={cn('h-5 w-5', action.color)} />
                        )}
                        <span className="font-semibold text-sm">{action.label}</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {action.description}
                      </p>
                    </div>
                    {action.cost && (
                      <Badge
                        variant={insufficientCredits ? 'destructive' : 'outline'}
                        className="text-xs shrink-0"
                      >
                        {action.cost}
                      </Badge>
                    )}
                  </div>

                  {action.isLoading && (
                    <div className="mt-3 pt-3 border-t">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="h-1.5 flex-1 bg-muted rounded-full overflow-hidden">
                          <motion.div
                            className={cn('h-full rounded-full bg-gradient-to-r', action.gradientFrom ?? 'from-primary', 'to-primary')}
                            initial={{ width: '0%' }}
                            animate={{ width: '100%' }}
                            transition={{ duration: 2, ease: 'easeInOut', repeat: Infinity }}
                          />
                        </div>
                        <span>Analyzing...</span>
                      </div>
                    </div>
                  )}

                  {insufficientCredits && !action.isLoading && (
                    <div className="mt-3 pt-3 border-t border-red-500/20">
                      <p className="text-xs text-red-500">
                        Insufficient credits. Need {action.cost}, have {availableCredits}
                      </p>
                    </div>
                  )}
                </button>
              </motion.div>
            );
          })}
        </div>
      </div>
    </Card>
  );
};

export default QuickActionBar;
