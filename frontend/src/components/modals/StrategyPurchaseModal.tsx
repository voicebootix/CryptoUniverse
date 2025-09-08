import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  X,
  ShoppingCart,
  CreditCard,
  DollarSign,
  Zap,
  Star,
  Shield,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Users,
  Clock,
  Target,
} from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { formatCurrency, formatPercentage } from '@/lib/utils';

interface StrategyPurchaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategy: any;
}

const StrategyPurchaseModal: React.FC<StrategyPurchaseModalProps> = ({
  isOpen,
  onClose,
  strategy
}) => {
  const [purchasing, setPurchasing] = useState(false);
  const [purchaseComplete, setPurchaseComplete] = useState(false);

  // Mock credit balance
  const userCredits = 15;
  const strategyCost = strategy?.credit_cost || 25;
  const canAfford = userCredits >= strategyCost;

  const handlePurchase = async () => {
    if (!canAfford) return;
    
    setPurchasing(true);
    
    // Simulate purchase
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    setPurchasing(false);
    setPurchaseComplete(true);
    
    // Auto close after success
    setTimeout(() => {
      onClose();
    }, 2000);
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'Low': return 'text-green-500 bg-green-500/10';
      case 'Medium': return 'text-yellow-500 bg-yellow-500/10';
      case 'High': return 'text-red-500 bg-red-500/10';
      default: return 'text-gray-500 bg-gray-500/10';
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'basic': return 'bg-gray-500';
      case 'pro': return 'bg-blue-500';
      case 'enterprise': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  if (purchaseComplete) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-md">
          <div className="text-center py-8">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="mx-auto mb-4 h-16 w-16 rounded-full bg-green-500/10 flex items-center justify-center"
            >
              <CheckCircle className="h-8 w-8 text-green-500" />
            </motion.div>
            <h3 className="text-lg font-semibold mb-2">Purchase Successful!</h3>
            <p className="text-muted-foreground mb-4">
              {strategy?.name} has been added to your strategies
            </p>
            <Button onClick={onClose} className="w-full">
              Continue Trading
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <ShoppingCart className="h-5 w-5" />
            Purchase Strategy
          </DialogTitle>
          <DialogDescription>
            Unlock professional trading strategies with proven performance
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Strategy Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-3 rounded ${strategy?.color}`}>
                    <strategy?.icon className="h-6 w-6" />
                  </div>
                  <div>
                    <CardTitle className="text-xl">{strategy?.name}</CardTitle>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="secondary" className="capitalize">
                        {strategy?.category}
                      </Badge>
                      <Badge className={`text-white ${getTierColor(strategy?.tier)}`}>
                        {strategy?.tier}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{strategyCost}</div>
                  <div className="text-sm text-muted-foreground">Credits</div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">
                {strategy?.description}
              </p>

              {/* Performance Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <div className="text-lg font-bold text-green-500">{strategy?.winRate}%</div>
                  <div className="text-xs text-muted-foreground">Win Rate</div>
                </div>
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <div className="text-lg font-bold">{strategy?.avgReturn}</div>
                  <div className="text-xs text-muted-foreground">Avg Return</div>
                </div>
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <div className={`text-lg font-bold px-2 py-1 rounded ${getRiskColor(strategy?.riskLevel)}`}>
                    {strategy?.riskLevel}
                  </div>
                  <div className="text-xs text-muted-foreground">Risk Level</div>
                </div>
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <div className="text-lg font-bold">{strategy?.activeUsers?.toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">Users</div>
                </div>
              </div>

              {/* Strategy Features */}
              <div className="space-y-2">
                <h4 className="font-semibold flex items-center gap-2">
                  <Star className="h-4 w-4" />
                  Key Features
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {strategy?.features?.map((feature: string, index: number) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* What You Get */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                What You Get
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-green-500/10">
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  </div>
                  <div>
                    <div className="font-medium">Full Strategy Access</div>
                    <div className="text-sm text-muted-foreground">Execute unlimited trades with this strategy</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-blue-500/10">
                    <Shield className="h-4 w-4 text-blue-500" />
                  </div>
                  <div>
                    <div className="font-medium">Risk Management</div>
                    <div className="text-sm text-muted-foreground">Built-in stop-loss and take-profit controls</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-purple-500/10">
                    <Target className="h-4 w-4 text-purple-500" />
                  </div>
                  <div>
                    <div className="font-medium">Performance Analytics</div>
                    <div className="text-sm text-muted-foreground">Detailed trade analysis and reporting</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-orange-500/10">
                    <Users className="h-4 w-4 text-orange-500" />
                  </div>
                  <div>
                    <div className="font-medium">Community Access</div>
                    <div className="text-sm text-muted-foreground">Join strategy-specific Discord channel</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Credit Balance */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5" />
                Credit Balance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-2">
                <span className="text-muted-foreground">Available Credits:</span>
                <span className="text-2xl font-bold">{userCredits}</span>
              </div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-muted-foreground">Strategy Cost:</span>
                <span className="text-xl font-semibold">-{strategyCost}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between mt-4">
                <span className="font-medium">Remaining Credits:</span>
                <span className={`text-xl font-bold ${canAfford ? 'text-green-500' : 'text-red-500'}`}>
                  {userCredits - strategyCost}
                </span>
              </div>

              {!canAfford && (
                <div className="mt-4 p-3 rounded bg-red-500/10 border border-red-500/20">
                  <div className="flex items-center gap-2 text-red-500">
                    <AlertCircle className="h-4 w-4" />
                    <span className="font-medium">Insufficient Credits</span>
                  </div>
                  <p className="text-sm text-red-500 mt-1">
                    You need {strategyCost - userCredits} more credits to purchase this strategy.
                  </p>
                  <Button variant="outline" size="sm" className="mt-2">
                    Buy More Credits
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="flex justify-between pt-4 border-t">
          <Button variant="outline" onClick={onClose} disabled={purchasing}>
            Cancel
          </Button>
          <Button 
            onClick={handlePurchase} 
            disabled={!canAfford || purchasing}
            className="min-w-[120px]"
          >
            {purchasing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Processing...
              </>
            ) : (
              <>
                <ShoppingCart className="h-4 w-4 mr-2" />
                Purchase for {strategyCost} Credits
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default StrategyPurchaseModal;