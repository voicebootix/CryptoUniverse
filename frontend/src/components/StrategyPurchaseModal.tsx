import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  X,
  Coins,
  Target,
  TrendingUp,
  Shield,
  CheckCircle,
  AlertTriangle,
  CreditCard,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useCredits } from '@/hooks/useCredits';
import { formatCurrency, formatNumber } from '@/lib/utils';

interface StrategyPurchaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategy: {
    id: string;
    name: string;
    description: string;
    category: string;
    risk_level: string;
    credit_cost: number;
    performance: string;
    min_capital: number;
  };
}

const StrategyPurchaseModal: React.FC<StrategyPurchaseModalProps> = ({
  isOpen,
  onClose,
  strategy
}) => {
  const { balance, actions } = useCredits();
  const [purchasing, setPurchasing] = useState(false);

  const handlePurchase = async () => {
    try {
      setPurchasing(true);
      await actions.purchaseStrategy(strategy.id, 'monthly');
      onClose();
    } catch (error) {
      console.error('Strategy purchase failed:', error);
    } finally {
      setPurchasing(false);
    }
  };

  const canAfford = balance.available_credits >= strategy.credit_cost;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-lg"
      >
        <Card className="p-6 bg-white">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold">{strategy.name}</h2>
              <p className="text-gray-600 mt-1">{strategy.description}</p>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="outline" className="capitalize">{strategy.category}</Badge>
                <Badge variant="outline">{strategy.risk_level} Risk</Badge>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="hover:bg-gray-100"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          {/* Strategy Details */}
          <div className="space-y-4 mb-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-green-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <TrendingUp className="w-4 h-4 text-green-600" />
                  <span className="font-medium text-green-900">Performance</span>
                </div>
                <div className="text-lg font-bold text-green-600">{strategy.performance}</div>
              </div>

              <div className="p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Coins className="w-4 h-4 text-blue-600" />
                  <span className="font-medium text-blue-900">Cost</span>
                </div>
                <div className="text-lg font-bold text-blue-600">{strategy.credit_cost} Credits</div>
              </div>

              <div className="p-3 bg-purple-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Target className="w-4 h-4 text-purple-600" />
                  <span className="font-medium text-purple-900">Min Capital</span>
                </div>
                <div className="text-lg font-bold text-purple-600">{formatCurrency(strategy.min_capital)}</div>
              </div>

              <div className="p-3 bg-orange-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Shield className="w-4 h-4 text-orange-600" />
                  <span className="font-medium text-orange-900">Risk Level</span>
                </div>
                <div className="text-lg font-bold text-orange-600 capitalize">{strategy.risk_level}</div>
              </div>
            </div>
          </div>

          {/* Credit Balance Check */}
          <div className="mb-6">
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
              <div>
                <span className="font-medium">Your Credit Balance</span>
                <p className="text-sm text-gray-600">Available for strategy purchases</p>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold">{formatNumber(balance.available_credits)} Credits</div>
                <div className="text-sm text-gray-600">${formatNumber(balance.remaining_potential)} earning potential</div>
              </div>
            </div>

            {!canAfford && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-800">Insufficient Credits</p>
                    <p className="text-sm text-red-700">
                      You need {strategy.credit_cost - balance.available_credits} more credits to purchase this strategy.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Purchase Actions */}
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            
            {canAfford ? (
              <Button 
                onClick={handlePurchase}
                disabled={purchasing}
                className="px-8 bg-gradient-to-r from-green-600 to-blue-600 text-white"
              >
                {purchasing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                    Purchasing...
                  </>
                ) : (
                  <>
                    <Coins className="w-4 h-4 mr-2" />
                    Purchase for {strategy.credit_cost} Credits
                  </>
                )}
              </Button>
            ) : (
              <Button 
                onClick={() => {
                  onClose();
                  // Navigate to credit purchase
                  window.location.href = '/dashboard/credits';
                }}
                className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 text-white"
              >
                <CreditCard className="w-4 h-4 mr-2" />
                Buy More Credits
              </Button>
            )}
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default StrategyPurchaseModal;