import React, { useState } from 'react';
import { Zap, DollarSign, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { formatCurrency } from '@/lib/utils';
import type { Opportunity } from './types';

interface BatchExecuteButtonProps {
  opportunities: Opportunity[];
  maxBatch?: number;
  executionCostPerTrade: number;
  availableCredits: number;
  onExecuteBatch: (opportunityIds: string[]) => void;
  isExecuting?: boolean;
}

export const BatchExecuteButton: React.FC<BatchExecuteButtonProps> = ({
  opportunities,
  maxBatch = 5,
  executionCostPerTrade,
  availableCredits,
  onExecuteBatch,
  isExecuting = false
}) => {
  const [showConfirmation, setShowConfirmation] = useState(false);

  // Filter to only non-expired, validated opportunities
  const eligibleOpportunities = opportunities
    .filter(opp => {
      const isExpired = new Date(opp.expires_at) < new Date();
      return !isExpired && opp.aiValidated;
    })
    .slice(0, maxBatch);

  const totalCost = eligibleOpportunities.length * executionCostPerTrade;
  const totalPositionSize = eligibleOpportunities.reduce((sum, opp) => sum + opp.suggested_position_size, 0);
  const totalPotentialGain = eligibleOpportunities.reduce((sum, opp) => sum + opp.potential_gain, 0);
  const totalMaxRisk = eligibleOpportunities.reduce((sum, opp) => sum + opp.max_risk, 0);
  const canAfford = availableCredits >= totalCost;

  const handleConfirm = () => {
    const ids = eligibleOpportunities.map(opp => opp.id);
    onExecuteBatch(ids);
    setShowConfirmation(false);
  };

  if (eligibleOpportunities.length === 0) {
    return null;
  }

  return (
    <>
      <Button
        size="lg"
        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        onClick={() => setShowConfirmation(true)}
        disabled={isExecuting || !canAfford}
      >
        {isExecuting ? (
          <>
            <Zap className="mr-2 h-5 w-5 animate-pulse" />
            Executing Batch...
          </>
        ) : (
          <>
            <Zap className="mr-2 h-5 w-5" />
            Execute Top {eligibleOpportunities.length} Validated
            <Badge variant="secondary" className="ml-2">
              <DollarSign className="h-3 w-3" />
              {totalCost} credits
            </Badge>
          </>
        )}
      </Button>

      {!canAfford && (
        <p className="text-xs text-center text-red-500 mt-2">
          <AlertCircle className="inline h-3 w-3 mr-1" />
          Insufficient credits. Need {totalCost}, have {availableCredits}
        </p>
      )}

      {/* Confirmation Dialog */}
      <AlertDialog open={showConfirmation} onOpenChange={setShowConfirmation}>
        <AlertDialogContent className="max-w-2xl">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-purple-500" />
              Execute Batch of {eligibleOpportunities.length} Trades
            </AlertDialogTitle>
            <AlertDialogDescription>
              You are about to execute {eligibleOpportunities.length} AI-validated trades simultaneously.
              Review the details below before confirming.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-4">
            {/* Summary Cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg border bg-muted/50 p-3 space-y-1">
                <p className="text-xs text-muted-foreground">Total Position Size</p>
                <p className="text-lg font-bold">{formatCurrency(totalPositionSize)}</p>
              </div>
              <div className="rounded-lg border bg-green-500/10 border-green-500/30 p-3 space-y-1">
                <p className="text-xs text-muted-foreground">Potential Gain</p>
                <p className="text-lg font-bold text-green-500">+{formatCurrency(totalPotentialGain)}</p>
              </div>
              <div className="rounded-lg border bg-red-500/10 border-red-500/30 p-3 space-y-1">
                <p className="text-xs text-muted-foreground">Max Risk</p>
                <p className="text-lg font-bold text-red-500">-{formatCurrency(totalMaxRisk)}</p>
              </div>
            </div>

            <Separator />

            {/* Trades List */}
            <div className="space-y-2 max-h-64 overflow-y-auto">
              <p className="text-sm font-medium">Trades to Execute:</p>
              {eligibleOpportunities.map((opp, idx) => (
                <div key={opp.id} className="rounded-md border bg-muted/30 p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{idx + 1}</Badge>
                      <span className="font-semibold">{opp.symbol}</span>
                      <Badge variant={opp.side === 'buy' ? 'default' : 'destructive'}>
                        {opp.side.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{formatCurrency(opp.suggested_position_size)}</p>
                      <p className="text-xs text-muted-foreground">{opp.strategy}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
                    <span>Entry: {formatCurrency(opp.entry_price)}</span>
                    <span>SL: {formatCurrency(opp.stop_loss)}</span>
                    <span>TP: {formatCurrency(opp.take_profit)}</span>
                    <span className="text-purple-500 font-medium">{opp.validation?.consensus_score}% consensus</span>
                  </div>
                </div>
              ))}
            </div>

            <Separator />

            {/* Cost Breakdown */}
            <div className="rounded-lg border bg-muted/50 p-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Credit Cost:</span>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">
                    {eligibleOpportunities.length} trades × {executionCostPerTrade} credits
                  </span>
                  <span className="font-bold">{totalCost} credits</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Available Credits:</span>
                <span className="font-bold">{availableCredits} credits</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="font-medium">After Execution:</span>
                <span className={`font-bold ${availableCredits - totalCost < 10 ? 'text-red-500' : ''}`}>
                  {availableCredits - totalCost} credits remaining
                </span>
              </div>
            </div>

            {/* Warning */}
            <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3 text-xs space-y-1">
              <p className="font-medium text-yellow-600 flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                Important Notes:
              </p>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-1">
                <li>All trades will be executed simultaneously with current market prices</li>
                <li>Trades cannot be cancelled once confirmed</li>
                <li>Make sure you have sufficient balance in your exchange accounts</li>
                <li>Network delays or exchange issues may affect execution</li>
              </ul>
            </div>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirm}
              className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
            >
              <Zap className="mr-2 h-4 w-4" />
              Confirm & Execute
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default BatchExecuteButton;
