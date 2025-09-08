import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  AlertTriangle,
  Info,
  Zap,
  Shield
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

interface ManualTradingPanelProps {
  isPaperMode: boolean;
  onExecuteTrade: (tradeData: any) => Promise<void>;
  isExecuting: boolean;
  aiSuggestions?: any;
}

const ManualTradingPanel: React.FC<ManualTradingPanelProps> = ({
  isPaperMode,
  onExecuteTrade,
  isExecuting,
  aiSuggestions
}) => {
  const { toast } = useToast();
  
  // Form state
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [amount, setAmount] = useState('');
  const [price, setPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [leverage, setLeverage] = useState('1');
  
  // Market data
  const [marketPrice, setMarketPrice] = useState<number>(0);
  const [availableBalance, setAvailableBalance] = useState<number>(0);
  const [tradingPairs, setTradingPairs] = useState<string[]>([]);

  useEffect(() => {
    fetchMarketData();
    fetchBalance();
    fetchTradingPairs();
  }, [symbol, isPaperMode]);

  const fetchMarketData = async () => {
    try {
      const response = await apiClient.get(`/api/v1/market/price/${symbol}`);
      if (response.data.success) {
        setMarketPrice(response.data.data.price);
        if (orderType === 'market') {
          setPrice(response.data.data.price.toString());
        }
      }
    } catch (error) {
      console.error('Failed to fetch market price:', error);
    }
  };

  const fetchBalance = async () => {
    try {
      const endpoint = isPaperMode 
        ? '/api/v1/paper-trading/balance'
        : '/api/v1/portfolio/balance';
      
      const response = await apiClient.get(endpoint);
      if (response.data.success) {
        setAvailableBalance(response.data.data.availableBalance);
      }
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    }
  };

  const fetchTradingPairs = async () => {
    try {
      const response = await apiClient.get('/api/v1/market/pairs');
      if (response.data.success) {
        setTradingPairs(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch trading pairs:', error);
      // Use default pairs as fallback
      setTradingPairs(['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']);
    }
  };

  const calculateTotal = () => {
    const qty = parseFloat(amount) || 0;
    const prc = parseFloat(price) || marketPrice || 0;
    const lev = parseFloat(leverage) || 1;
    return qty * prc / lev;
  };

  const validateOrder = () => {
    if (!amount || parseFloat(amount) <= 0) {
      toast({
        title: "Invalid Amount",
        description: "Please enter a valid amount",
        variant: "destructive"
      });
      return false;
    }

    if (orderType === 'limit' && (!price || parseFloat(price) <= 0)) {
      toast({
        title: "Invalid Price",
        description: "Please enter a valid limit price",
        variant: "destructive"
      });
      return false;
    }

    const total = calculateTotal();
    if (total > availableBalance) {
      toast({
        title: "Insufficient Balance",
        description: `You need ${formatCurrency(total)} but only have ${formatCurrency(availableBalance)}`,
        variant: "destructive"
      });
      return false;
    }

    return true;
  };

  const handleSubmit = async () => {
    if (!validateOrder()) return;

    const tradeData = {
      symbol,
      side,
      orderType,
      amount: parseFloat(amount),
      price: orderType === 'limit' ? parseFloat(price) : marketPrice,
      leverage: parseFloat(leverage),
      stopLoss: stopLoss ? parseFloat(stopLoss) : undefined,
      takeProfit: takeProfit ? parseFloat(takeProfit) : undefined,
      source: 'manual'
    };

    await onExecuteTrade(tradeData);
  };

  const applyAISuggestion = () => {
    if (!aiSuggestions) return;

    setSymbol(aiSuggestions.symbol || symbol);
    setSide(aiSuggestions.side || side);
    setAmount(aiSuggestions.amount?.toString() || amount);
    setPrice(aiSuggestions.price?.toString() || price);
    setStopLoss(aiSuggestions.stopLoss?.toString() || '');
    setTakeProfit(aiSuggestions.takeProfit?.toString() || '');

    toast({
      title: "AI Suggestion Applied",
      description: "Trade parameters updated with AI recommendations",
      duration: 3000
    });
  };

  return (
    <div className="space-y-4">
      {/* AI Suggestion Alert */}
      {aiSuggestions && (
        <Alert className="border-blue-500 bg-blue-500/10">
          <Zap className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>
              AI suggests: {aiSuggestions.side} {aiSuggestions.amount} {aiSuggestions.symbol}
              at {formatCurrency(aiSuggestions.price)}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={applyAISuggestion}
              className="ml-4"
            >
              Apply
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Order Type Tabs */}
      <Tabs value={orderType} onValueChange={(v) => setOrderType(v as 'market' | 'limit')}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="market">Market Order</TabsTrigger>
          <TabsTrigger value="limit">Limit Order</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Buy/Sell Toggle */}
      <div className="grid grid-cols-2 gap-2">
        <Button
          variant={side === 'buy' ? 'default' : 'outline'}
          onClick={() => setSide('buy')}
          className={side === 'buy' ? 'bg-green-600 hover:bg-green-700' : ''}
        >
          <TrendingUp className="h-4 w-4 mr-2" />
          Buy
        </Button>
        <Button
          variant={side === 'sell' ? 'default' : 'outline'}
          onClick={() => setSide('sell')}
          className={side === 'sell' ? 'bg-red-600 hover:bg-red-700' : ''}
        >
          <TrendingDown className="h-4 w-4 mr-2" />
          Sell
        </Button>
      </div>

      {/* Trading Pair Selection */}
      <div className="space-y-2">
        <Label>Trading Pair</Label>
        <Select value={symbol} onValueChange={setSymbol}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {tradingPairs.map(pair => (
              <SelectItem key={pair} value={pair}>
                {pair}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Amount Input */}
      <div className="space-y-2">
        <Label>Amount</Label>
        <div className="relative">
          <Input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            step="0.001"
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2">
            <Badge variant="outline">{symbol.split('/')[0]}</Badge>
          </div>
        </div>
      </div>

      {/* Price Input (for limit orders) */}
      {orderType === 'limit' && (
        <div className="space-y-2">
          <Label>Limit Price</Label>
          <div className="relative">
            <Input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={marketPrice.toString()}
              step="0.01"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2">
              <Badge variant="outline">USDT</Badge>
            </div>
          </div>
        </div>
      )}

      {/* Risk Management */}
      <Card>
        <CardContent className="pt-4 space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Shield className="h-4 w-4" />
            Risk Management (Optional)
          </div>
          
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Stop Loss %</Label>
              <Input
                type="number"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                placeholder="5"
                step="0.1"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Take Profit %</Label>
              <Input
                type="number"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                placeholder="10"
                step="0.1"
              />
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Leverage</Label>
            <Select value={leverage} onValueChange={setLeverage}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 5, 10, 20].map(lev => (
                  <SelectItem key={lev} value={lev.toString()}>
                    {lev}x
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Order Summary */}
      <Card className="bg-muted/50">
        <CardContent className="pt-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span>Market Price:</span>
            <span className="font-medium">{formatCurrency(marketPrice)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Order Total:</span>
            <span className="font-medium">{formatCurrency(calculateTotal())}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Available Balance:</span>
            <span className="font-medium">{formatCurrency(availableBalance)}</span>
          </div>
          <Separator />
          <div className="flex justify-between font-medium">
            <span>After Trade:</span>
            <span>{formatCurrency(availableBalance - calculateTotal())}</span>
          </div>
        </CardContent>
      </Card>

      {/* Submit Button */}
      <Button
        className="w-full"
        size="lg"
        onClick={handleSubmit}
        disabled={isExecuting || !amount}
      >
        {isExecuting ? (
          <>Processing...</>
        ) : (
          <>
            {side === 'buy' ? 'Buy' : 'Sell'} {amount || '0'} {symbol.split('/')[0]}
          </>
        )}
      </Button>

      {/* Paper Mode Notice */}
      {isPaperMode && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            This is a paper trade using virtual funds
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};

export default ManualTradingPanel;