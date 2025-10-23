import React, { useState, useMemo, useEffect } from 'react';
import { X, Sparkles, AlertCircle, DollarSign, Download } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { ValidatedOpportunityCard } from './ValidatedOpportunityCard';
import { OpportunityCard } from './OpportunityCard';
import { OpportunityFilters } from './OpportunityFilters';
import { BatchExecuteButton } from './BatchExecuteButton';
import type { Opportunity, OpportunitiesDrawerState, OpportunityFilter, OpportunitySort } from './types';

interface OpportunitiesDrawerProps {
  state: OpportunitiesDrawerState;
  onClose: () => void;
  onExecuteTrade: (opportunityId: string, positionSize: number) => Promise<void>;
  onExecuteBatch: (opportunityIds: string[]) => Promise<void>;
  onValidateOpportunity: (opportunityId: string) => Promise<void>;
  onApplyToForm: (opportunity: Opportunity) => void;
  availableCredits: number;
  portfolioValue: number;
}

export const OpportunitiesDrawer: React.FC<OpportunitiesDrawerProps> = ({
  state,
  onClose,
  onExecuteTrade,
  onExecuteBatch,
  onValidateOpportunity,
  onApplyToForm,
  availableCredits,
  portfolioValue
}) => {
  const [activeFilter, setActiveFilter] = useState<OpportunityFilter>('validated');
  const [sortBy, setSortBy] = useState<OpportunitySort>('confidence');

  // Reset filter when drawer opens
  useEffect(() => {
    if (state.open) {
      setActiveFilter('validated');
    }
  }, [state.open]);

  // Filter opportunities
  const filteredOpportunities = useMemo(() => {
    if (!state.data) return { validated: [], nonValidated: [] };

    const { validated, nonValidated } = state.data;

    const filterByConfidence = (opportunities: Opportunity[]) => {
      switch (activeFilter) {
        case 'validated':
          return opportunities.filter(opp => opp.aiValidated);
        case 'high':
          return opportunities.filter(opp => opp.confidence > 80);
        case 'medium':
          return opportunities.filter(opp => opp.confidence >= 60 && opp.confidence <= 80);
        case 'low':
          return opportunities.filter(opp => opp.confidence < 60);
        case 'all':
        default:
          return opportunities;
      }
    };

    const sortOpportunities = (opportunities: Opportunity[]) => {
      return [...opportunities].sort((a, b) => {
        switch (sortBy) {
          case 'potential_gain':
            return b.potential_gain - a.potential_gain;
          case 'risk_reward':
            return b.risk_reward_ratio - a.risk_reward_ratio;
          case 'confidence':
          default:
            return b.confidence - a.confidence;
        }
      });
    };

    const allOpportunities = [...validated, ...nonValidated];
    const filtered = filterByConfidence(allOpportunities);
    const sorted = sortOpportunities(filtered);

    // Separate back into validated and non-validated after filtering/sorting
    return {
      validated: sorted.filter(opp => opp.aiValidated),
      nonValidated: sorted.filter(opp => !opp.aiValidated)
    };
  }, [state.data, activeFilter, sortBy]);

  const handleExecute = async (opportunityId: string, positionSize: number) => {
    await onExecuteTrade(opportunityId, positionSize);
  };

  const handleBatchExecute = async (opportunityIds: string[]) => {
    await onExecuteBatch(opportunityIds);
  };

  const handleValidate = async (opportunityId: string) => {
    await onValidateOpportunity(opportunityId);
  };

  const handleExport = () => {
    if (!state.data) return;

    const data = {
      scan_timestamp: new Date().toISOString(),
      validated_count: state.data.validatedCount,
      total_count: state.data.totalCount,
      scan_cost: state.data.scanCost,
      opportunities: [...state.data.validated, ...state.data.nonValidated].map(opp => ({
        symbol: opp.symbol,
        side: opp.side,
        strategy: opp.strategy,
        confidence: opp.confidence,
        ai_validated: opp.aiValidated,
        consensus_score: opp.validation?.consensus_score,
        entry_price: opp.entry_price,
        stop_loss: opp.stop_loss,
        take_profit: opp.take_profit,
        position_size: opp.suggested_position_size,
        max_risk: opp.max_risk,
        potential_gain: opp.potential_gain,
        risk_reward_ratio: opp.risk_reward_ratio
      }))
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `opportunities-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!state.data) return null;

  return (
    <Sheet open={state.open} onOpenChange={onClose}>
      <SheetContent side="right" className="w-full sm:max-w-4xl p-0 flex flex-col">
        <SheetHeader className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <div>
              <SheetTitle className="flex items-center gap-2 text-xl">
                <Sparkles className="h-5 w-5 text-purple-500" />
                AI Opportunity Scan Results
              </SheetTitle>
              <SheetDescription className="mt-1">
                Found {state.data.totalCount} opportunities | {state.data.validatedCount} AI-Validated
              </SheetDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Cost Summary */}
          <div className="flex items-center gap-4 mt-4 text-sm">
            <div className="flex items-center gap-1 text-muted-foreground">
              <DollarSign className="h-3 w-3" />
              <span>Scan cost: {state.data.scanCost} credits</span>
            </div>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-1 text-muted-foreground">
              <span>Available: {availableCredits} credits</span>
            </div>
            <Button variant="outline" size="sm" onClick={handleExport} className="ml-auto">
              <Download className="mr-2 h-3 w-3" />
              Export
            </Button>
          </div>
        </SheetHeader>

        {/* Filters */}
        <div className="px-6 py-4 border-b">
          <OpportunityFilters
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            sortBy={sortBy}
            onSortChange={setSortBy}
            validatedCount={state.data.validatedCount}
            totalCount={state.data.totalCount}
          />
        </div>

        {/* Opportunities List */}
        <ScrollArea className="flex-1 px-6">
          <div className="space-y-6 py-6">
            {/* AI Validated Section */}
            {filteredOpportunities.validated.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="h-px flex-1 bg-gradient-to-r from-purple-500 to-blue-500" />
                  <Badge className="bg-gradient-to-r from-purple-600 to-blue-600 text-white gap-1">
                    <Sparkles className="h-3 w-3" />
                    AI MONEY AGENT VALIDATED - READY TO EXECUTE
                  </Badge>
                  <div className="h-px flex-1 bg-gradient-to-r from-blue-500 to-purple-500" />
                </div>

                <div className="space-y-4">
                  {filteredOpportunities.validated.map((opportunity) => (
                    <ValidatedOpportunityCard
                      key={opportunity.id}
                      opportunity={opportunity}
                      onExecute={handleExecute}
                      onApplyToForm={onApplyToForm}
                      isExecuting={state.executing.has(opportunity.id)}
                      portfolioValue={portfolioValue}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Non-Validated Section */}
            {filteredOpportunities.nonValidated.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <div className="h-px flex-1 bg-border" />
                  <Badge variant="outline" className="gap-1 text-yellow-600 border-yellow-600/50">
                    <AlertCircle className="h-3 w-3" />
                    OTHER OPPORTUNITIES (Not AI-Validated)
                  </Badge>
                  <div className="h-px flex-1 bg-border" />
                </div>

                <div className="space-y-4">
                  {filteredOpportunities.nonValidated.map((opportunity) => (
                    <OpportunityCard
                      key={opportunity.id}
                      opportunity={opportunity}
                      onValidate={handleValidate}
                      onApplyToForm={onApplyToForm}
                      isValidating={state.validating.has(opportunity.id)}
                      portfolioValue={portfolioValue}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* No Results */}
            {filteredOpportunities.validated.length === 0 && filteredOpportunities.nonValidated.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No opportunities match your filter</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Try adjusting your filters or run a new scan
                </p>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Batch Execute Footer */}
        {filteredOpportunities.validated.length > 0 && (
          <div className="px-6 py-4 border-t bg-muted/30">
            <BatchExecuteButton
              opportunities={filteredOpportunities.validated}
              maxBatch={5}
              executionCostPerTrade={state.data.executionCostPerTrade}
              availableCredits={availableCredits}
              onExecuteBatch={handleBatchExecute}
              isExecuting={state.executing.size > 0}
            />
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};

export default OpportunitiesDrawer;
