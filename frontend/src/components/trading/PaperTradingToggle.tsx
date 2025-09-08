import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  DollarSign,
  AlertTriangle,
  Info,
  Check,
  X,
  TrendingUp,
  Shield,
  Sparkles
} from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { apiClient } from '@/lib/api/client';
import { paperTradingApi } from '@/lib/api/tradingApi';
import { formatCurrency, formatPercentage } from '@/lib/utils';

interface PaperTradingStats {
  totalTrades: number;
  winRate: number;
  totalProfit: number;
  bestTrade: number;
  worstTrade: number;
  readyForLive: boolean;
}

interface PaperTradingToggleProps {
  isCompact?: boolean;
  onModeChange?: (isPaperTrading: boolean) => void;
  className?: string;
}

const PaperTradingToggle: React.FC<PaperTradingToggleProps> = ({
  isCompact = false,
  onModeChange,
  className = ''
}) => {
  const [isPaperTrading, setIsPaperTrading] = useState(true);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showStatsDialog, setShowStatsDialog] = useState(false);
  const [paperStats, setPaperStats] = useState<PaperTradingStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    loadTradingMode();
    loadPaperStats();
  }, []);

  const loadTradingMode = async () => {
    try {
      const response = await paperTradingApi.getTradingMode();
      setIsPaperTrading(response.isPaperTrading);
    } catch (error) {
      console.error('Failed to load trading mode:', error);
    }
  };

  const loadPaperStats = async () => {
    try {
      const stats = await paperTradingApi.getStats();
      setPaperStats(stats);
    } catch (error) {
      console.error('Failed to load paper trading stats:', error);
    }
  };

  const handleToggle = async (checked: boolean) => {
    if (checked) {
      // Switching to paper trading (safe)
      await switchToPaperTrading();
    } else {
      // Switching to live trading (needs confirmation)
      setShowConfirmDialog(true);
    }
  };

  const switchToPaperTrading = async () => {
    setIsLoading(true);
    try {
      await paperTradingApi.setTradingMode(true);
      setIsPaperTrading(true);
      onModeChange?.(true);
      toast({
        title: 'Switched to Paper Trading',
        description: 'You are now using virtual money for practice.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to switch trading mode',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const switchToLiveTrading = async () => {
    setIsLoading(true);
    try {
      await paperTradingApi.setTradingMode(false);
      setIsPaperTrading(false);
      onModeChange?.(false);
      setShowConfirmDialog(false);
      toast({
        title: 'Switched to Live Trading',
        description: 'You are now trading with real money. Trade responsibly!',
        variant: 'default',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to switch to live trading',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderCompactToggle = () => (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={`flex items-center gap-2 ${className}`}>
            <Badge
              variant={isPaperTrading ? 'secondary' : 'default'}
              className="cursor-pointer"
              onClick={() => setShowStatsDialog(true)}
            >
              {isPaperTrading ? (
                <>
                  <FileText className="h-3 w-3 mr-1" />
                  Paper
                </>
              ) : (
                <>
                  <DollarSign className="h-3 w-3 mr-1" />
                  Live
                </>
              )}
            </Badge>
            <Switch
              checked={isPaperTrading}
              onCheckedChange={handleToggle}
              disabled={isLoading}
              className="h-5 w-10"
            />
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p className="font-semibold">
            {isPaperTrading ? 'Paper Trading Mode' : 'Live Trading Mode'}
          </p>
          <p className="text-xs">
            {isPaperTrading 
              ? 'Practice with virtual money'
              : 'Trading with real money'}
          </p>
          {paperStats && isPaperTrading && (
            <p className="text-xs mt-1">
              {paperStats.totalTrades} trades • {formatPercentage(paperStats.winRate)} win rate
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );

  const renderFullToggle = () => (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            {isPaperTrading ? (
              <>
                <FileText className="h-4 w-4" />
                Paper Trading Mode
              </>
            ) : (
              <>
                <DollarSign className="h-4 w-4" />
                Live Trading Mode
              </>
            )}
          </CardTitle>
          <Switch
            checked={isPaperTrading}
            onCheckedChange={handleToggle}
            disabled={isLoading}
          />
        </div>
        <CardDescription>
          {isPaperTrading 
            ? 'Practice risk-free with virtual money'
            : 'Trading with real money - be careful!'}
        </CardDescription>
      </CardHeader>
      
      {paperStats && (
        <CardContent className="pt-0">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground">Total Trades</p>
              <p className="font-semibold">{paperStats.totalTrades}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Win Rate</p>
              <p className="font-semibold text-green-500">
                {formatPercentage(paperStats.winRate)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Virtual Profit</p>
              <p className={`font-semibold ${paperStats.totalProfit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {formatCurrency(paperStats.totalProfit)}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Ready for Live</p>
              <p className="font-semibold">
                {paperStats.readyForLive ? (
                  <Badge variant="default" className="text-xs">Yes</Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">Not Yet</Badge>
                )}
              </p>
            </div>
          </div>
          
          {isPaperTrading && (
            <Button
              variant="outline"
              size="sm"
              className="w-full mt-3"
              onClick={() => setShowStatsDialog(true)}
            >
              View Detailed Stats
            </Button>
          )}
        </CardContent>
      )}
    </Card>
  );

  return (
    <>
      {isCompact ? renderCompactToggle() : renderFullToggle()}

      {/* Confirmation Dialog for Live Trading */}
      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Switch to Live Trading?
            </DialogTitle>
            <DialogDescription>
              You're about to switch from paper trading to live trading with real money.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>Warning:</strong> Live trading involves real financial risk. 
                You could lose money. Only trade with funds you can afford to lose.
              </AlertDescription>
            </Alert>
            
            {paperStats && (
              <div className="space-y-2">
                <h4 className="font-semibold text-sm">Your Paper Trading Performance:</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Trades:</span>
                    <span className="font-medium">{paperStats.totalTrades}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Win Rate:</span>
                    <span className="font-medium text-green-500">
                      {formatPercentage(paperStats.winRate)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Virtual Profit:</span>
                    <span className={`font-medium ${paperStats.totalProfit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatCurrency(paperStats.totalProfit)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Best Trade:</span>
                    <span className="font-medium text-green-500">
                      {formatCurrency(paperStats.bestTrade)}
                    </span>
                  </div>
                </div>
                
                {!paperStats.readyForLive && (
                  <Alert className="mt-3">
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Recommendation:</strong> Continue paper trading until you have 
                      at least 50 trades with a 60%+ win rate.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            )}
            
            <div className="space-y-2">
              <h4 className="font-semibold text-sm">Confirm you understand:</h4>
              <div className="space-y-2">
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" className="mt-0.5" />
                  <span>I understand I will be trading with real money</span>
                </label>
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" className="mt-0.5" />
                  <span>I accept the risk of financial loss</span>
                </label>
                <label className="flex items-start gap-2 text-sm">
                  <input type="checkbox" className="mt-0.5" />
                  <span>I have configured my exchange API keys</span>
                </label>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowConfirmDialog(false)}
            >
              Stay in Paper Trading
            </Button>
            <Button
              variant="default"
              onClick={switchToLiveTrading}
              disabled={isLoading}
              className="bg-orange-600 hover:bg-orange-700"
            >
              <DollarSign className="h-4 w-4 mr-2" />
              Switch to Live Trading
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Paper Trading Stats Dialog */}
      <Dialog open={showStatsDialog} onOpenChange={setShowStatsDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Paper Trading Performance
            </DialogTitle>
            <DialogDescription>
              Your practice trading statistics and progress
            </DialogDescription>
          </DialogHeader>
          
          {paperStats && (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Total Trades</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">{paperStats.totalTrades}</p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Win Rate</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold text-green-500">
                      {formatPercentage(paperStats.winRate)}
                    </p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Virtual Profit</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className={`text-2xl font-bold ${paperStats.totalProfit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatCurrency(paperStats.totalProfit)}
                    </p>
                  </CardContent>
                </Card>
              </div>
              
              <Separator />
              
              <div className="space-y-3">
                <h4 className="font-semibold">Progress to Live Trading</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {paperStats.totalTrades >= 50 ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <X className="h-4 w-4 text-gray-400" />
                    )}
                    <span className="text-sm">Complete 50+ trades (currently {paperStats.totalTrades})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {paperStats.winRate >= 0.6 ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <X className="h-4 w-4 text-gray-400" />
                    )}
                    <span className="text-sm">Achieve 60%+ win rate (currently {formatPercentage(paperStats.winRate)})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {paperStats.totalProfit > 0 ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <X className="h-4 w-4 text-gray-400" />
                    )}
                    <span className="text-sm">Be profitable overall (currently {formatCurrency(paperStats.totalProfit)})</span>
                  </div>
                </div>
                
                {paperStats.readyForLive ? (
                  <Alert className="bg-green-500/10 border-green-500/20">
                    <Sparkles className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Congratulations!</strong> You're ready for live trading based on your performance.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      Keep practicing! You need more experience before switching to live trading.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
              
              <Separator />
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Best Trade</p>
                  <p className="font-semibold text-green-500">
                    +{formatCurrency(paperStats.bestTrade)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Worst Trade</p>
                  <p className="font-semibold text-red-500">
                    {formatCurrency(paperStats.worstTrade)}
                  </p>
                </div>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowStatsDialog(false)}>
              Close
            </Button>
            {paperStats?.readyForLive && isPaperTrading && (
              <Button
                onClick={() => {
                  setShowStatsDialog(false);
                  setShowConfirmDialog(true);
                }}
                className="bg-green-600 hover:bg-green-700"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Switch to Live Trading
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default PaperTradingToggle;