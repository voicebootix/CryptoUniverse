import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  BarChart3,
  Activity,
  Zap,
  Brain,
  Shield,
  Clock,
  RefreshCw,
  Play,
  Settings,
  Eye,
  AlertTriangle,
  CheckCircle,
  Crosshair,
  LineChart,
  PieChart,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { useUser } from '@/store/authStore';
import { useExchanges } from '@/hooks/useExchanges';
import { useStrategies } from '@/hooks/useStrategies';
import { formatCurrency } from '@/lib/utils';

interface ManualTradeRequest {
  symbol: string;
  action: 'buy' | 'sell';
  amount: number;
  orderType: 'market' | 'limit' | 'stop';
  price?: number;
  stopLoss?: number;
  takeProfit?: number;
  exchange?: string;
  leverage?: number;
}

interface AIAssistanceRequest {
  symbol: string;
  analysisType: 'opportunity' | 'risk' | 'market' | 'portfolio';
  timeframe: string;
  includeConsensus: boolean;
}

const ManualTradingPage: React.FC = () => {
  const user = useUser();
  const { exchanges, aggregatedStats } = useExchanges();
  const { availableStrategies, actions: strategyActions } = useStrategies();
  
  const [activeTab, setActiveTab] = useState('trade');
  const [tradeForm, setTradeForm] = useState<ManualTradeRequest>({
    symbol: 'BTC/USDT',
    action: 'buy',
    amount: 1000,
    orderType: 'market',
    exchange: 'auto'
  });
  
  const [aiAssistance, setAiAssistance] = useState<AIAssistanceRequest>({
    symbol: 'BTC/USDT',
    analysisType: 'opportunity',
    timeframe: '1h',
    includeConsensus: true
  });
  
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  const handleTradeSubmit = async () => {
    try {
      setIsExecuting(true);
      
      // Call your existing trading API
      const response = await fetch('/api/v1/trading/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          symbol: tradeForm.symbol,
          action: tradeForm.action,
          amount: tradeForm.amount,
          order_type: tradeForm.orderType,
          price: tradeForm.price,
          stop_loss: tradeForm.stopLoss,
          take_profit: tradeForm.takeProfit,
          exchange: tradeForm.exchange === 'auto' ? undefined : tradeForm.exchange,
          leverage: tradeForm.leverage
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Trading API error: ${response.status} ${errorText}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        // Trade executed successfully
        console.log('Trade executed:', result);
      }
      
    } catch (error) {
      console.error('Trade execution failed:', error);
    } finally {
      setIsExecuting(false);
    }
  };

  const requestAIAnalysis = async () => {
    try {
      setIsAnalyzing(true);
      
      // Call your existing AI consensus service
      const response = await fetch('/api/v1/strategies/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          function: 'market_analysis',
          symbol: aiAssistance.symbol,
          parameters: {
            analysis_type: aiAssistance.analysisType,
            timeframe: aiAssistance.timeframe,
            include_consensus: aiAssistance.includeConsensus
          },
          simulation_mode: true
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`AI analysis API error: ${response.status} ${errorText}`);
      }
      
      const result = await response.json();
      setAiAnalysis(result);
      
    } catch (error) {
      console.error('AI analysis failed:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Manual Trading</h1>
          <p className="text-muted-foreground">
            Professional trading interface with AI assistance and risk management
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="px-3 py-1">
            {aggregatedStats.connectedCount} Exchanges Connected
          </Badge>
          <Badge variant="outline" className="px-3 py-1">
            {formatCurrency(aggregatedStats.totalBalance)} Available
          </Badge>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="trade">Execute Trade</TabsTrigger>
          <TabsTrigger value="analysis">AI Analysis</TabsTrigger>
          <TabsTrigger value="strategies">Strategy Assist</TabsTrigger>
          <TabsTrigger value="risk">Risk Management</TabsTrigger>
        </TabsList>

        {/* Manual Trade Execution */}
        <TabsContent value="trade" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Trade Form */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="w-5 h-5" />
                    Execute Trade
                  </CardTitle>
                  <CardDescription>
                    Manual trade execution with real-time validation and AI assistance
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Trading Pair</Label>
                      <Select 
                        value={tradeForm.symbol} 
                        onValueChange={(value) => setTradeForm(prev => ({ ...prev, symbol: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select trading pair" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="BTC/USDT">BTC/USDT</SelectItem>
                          <SelectItem value="ETH/USDT">ETH/USDT</SelectItem>
                          <SelectItem value="SOL/USDT">SOL/USDT</SelectItem>
                          <SelectItem value="ADA/USDT">ADA/USDT</SelectItem>
                          <SelectItem value="DOT/USDT">DOT/USDT</SelectItem>
                          <SelectItem value="MATIC/USDT">MATIC/USDT</SelectItem>
                          <SelectItem value="LINK/USDT">LINK/USDT</SelectItem>
                          <SelectItem value="UNI/USDT">UNI/USDT</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Action</Label>
                      <Select 
                        value={tradeForm.action} 
                        onValueChange={(value) => setTradeForm(prev => ({ ...prev, action: value as 'buy' | 'sell' }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="buy">
                            <div className="flex items-center gap-2">
                              <ArrowUpRight className="w-4 h-4 text-green-500" />
                              Buy / Long
                            </div>
                          </SelectItem>
                          <SelectItem value="sell">
                            <div className="flex items-center gap-2">
                              <ArrowDownRight className="w-4 h-4 text-red-500" />
                              Sell / Short
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Order Type</Label>
                      <Select 
                        value={tradeForm.orderType} 
                        onValueChange={(value) => setTradeForm(prev => ({ ...prev, orderType: value as any }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="market">Market Order</SelectItem>
                          <SelectItem value="limit">Limit Order</SelectItem>
                          <SelectItem value="stop">Stop Order</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label>Exchange</Label>
                      <Select 
                        value={tradeForm.exchange} 
                        onValueChange={(value) => setTradeForm(prev => ({ ...prev, exchange: value }))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">Auto-Select Best</SelectItem>
                          {exchanges.filter(ex => ex.is_active).map(exchange => (
                            <SelectItem key={exchange.id} value={exchange.exchange}>
                              {exchange.exchange.charAt(0).toUpperCase() + exchange.exchange.slice(1)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Amount (USD)</Label>
                      <Input
                        type="number"
                        value={tradeForm.amount}
                        onChange={(e) => setTradeForm(prev => ({ ...prev, amount: parseFloat(e.target.value) || 0 }))}
                        placeholder="Enter amount in USD"
                      />
                    </div>

                    {tradeForm.orderType === 'limit' && (
                      <div className="space-y-2">
                        <Label>Limit Price</Label>
                        <Input
                          type="number"
                          value={tradeForm.price || ''}
                          onChange={(e) => setTradeForm(prev => ({ ...prev, price: parseFloat(e.target.value) || undefined }))}
                          placeholder="Enter limit price"
                        />
                      </div>
                    )}
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Stop Loss (%)</Label>
                      <Input
                        type="number"
                        value={tradeForm.stopLoss || ''}
                        onChange={(e) => setTradeForm(prev => ({ ...prev, stopLoss: parseFloat(e.target.value) || undefined }))}
                        placeholder="Optional stop loss %"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Take Profit (%)</Label>
                      <Input
                        type="number"
                        value={tradeForm.takeProfit || ''}
                        onChange={(e) => setTradeForm(prev => ({ ...prev, takeProfit: parseFloat(e.target.value) || undefined }))}
                        placeholder="Optional take profit %"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t">
                    <Button variant="outline">
                      <Eye className="w-4 h-4 mr-2" />
                      Preview
                    </Button>
                    <Button 
                      onClick={handleTradeSubmit}
                      disabled={isExecuting}
                      className={`px-8 ${tradeForm.action === 'buy' 
                        ? 'bg-green-600 hover:bg-green-700' 
                        : 'bg-red-600 hover:bg-red-700'
                      }`}
                    >
                      {isExecuting ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          Executing...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-2" />
                          Execute {tradeForm.action.toUpperCase()}
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Real-time Market Data */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    {tradeForm.symbol} Market
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center space-y-2">
                    <div className="text-3xl font-bold">$95,487</div>
                    <div className="flex items-center justify-center gap-2">
                      <TrendingUp className="w-4 h-4 text-green-500" />
                      <span className="text-green-500 font-medium">+2.34%</span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-muted-foreground">24h High</div>
                      <div className="font-medium">$96,250</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">24h Low</div>
                      <div className="font-medium">$93,180</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Volume</div>
                      <div className="font-medium">2.1B</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Spread</div>
                      <div className="font-medium">0.02%</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Order Book</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {/* Simplified order book */}
                  <div className="space-y-1">
                    {[
                      { price: 95495, amount: 0.15, side: 'sell' },
                      { price: 95490, amount: 0.23, side: 'sell' },
                      { price: 95487, amount: 0.45, side: 'sell' },
                    ].map((order, idx) => (
                      <div key={idx} className="flex justify-between text-xs">
                        <span className="text-red-500">${order.price}</span>
                        <span>{order.amount}</span>
                      </div>
                    ))}
                  </div>
                  <div className="border-t pt-1">
                    {[
                      { price: 95485, amount: 0.34, side: 'buy' },
                      { price: 95480, amount: 0.28, side: 'buy' },
                      { price: 95475, amount: 0.19, side: 'buy' },
                    ].map((order, idx) => (
                      <div key={idx} className="flex justify-between text-xs">
                        <span className="text-green-500">${order.price}</span>
                        <span>{order.amount}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* AI Analysis */}
        <TabsContent value="analysis" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="w-5 h-5" />
                  AI Market Analysis
                </CardTitle>
                <CardDescription>
                  Get AI-powered analysis using GPT-4, Claude, and Gemini consensus
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Symbol</Label>
                    <Select 
                      value={aiAssistance.symbol} 
                      onValueChange={(value) => setAiAssistance(prev => ({ ...prev, symbol: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="BTC/USDT">BTC/USDT</SelectItem>
                        <SelectItem value="ETH/USDT">ETH/USDT</SelectItem>
                        <SelectItem value="SOL/USDT">SOL/USDT</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Analysis Type</Label>
                    <Select 
                      value={aiAssistance.analysisType} 
                      onValueChange={(value) => setAiAssistance(prev => ({ ...prev, analysisType: value as any }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="opportunity">Opportunity Analysis</SelectItem>
                        <SelectItem value="risk">Risk Assessment</SelectItem>
                        <SelectItem value="market">Market Sentiment</SelectItem>
                        <SelectItem value="portfolio">Portfolio Review</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Include AI Consensus</Label>
                    <p className="text-sm text-muted-foreground">
                      Use GPT-4 + Claude + Gemini for validation
                    </p>
                  </div>
                  <Switch
                    checked={aiAssistance.includeConsensus}
                    onCheckedChange={(checked) => setAiAssistance(prev => ({ ...prev, includeConsensus: checked }))}
                  />
                </div>

                <Button 
                  onClick={requestAIAnalysis}
                  disabled={isAnalyzing}
                  className="w-full"
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Brain className="w-4 h-4 mr-2" />
                      Get AI Analysis
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* AI Analysis Results */}
            <Card>
              <CardHeader>
                <CardTitle>Analysis Results</CardTitle>
              </CardHeader>
              <CardContent>
                {aiAnalysis ? (
                  <div className="space-y-4">
                    <div className="p-4 bg-blue-50 rounded-lg">
                      <h4 className="font-medium text-blue-900 mb-2">AI Consensus</h4>
                      <p className="text-sm text-blue-700">
                        {aiAnalysis.execution_result?.ai_reasoning || 'Analysis completed successfully'}
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-muted-foreground">Confidence</div>
                        <div className="text-lg font-bold">
                          {aiAnalysis.execution_result?.confidence || 0}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-muted-foreground">Risk Score</div>
                        <div className="text-lg font-bold">
                          {aiAnalysis.execution_result?.risk_score || 0}/100
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Brain className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Request AI analysis to get insights</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Strategy Assistance */}
        <TabsContent value="strategies" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Object.entries(availableStrategies).slice(0, 6).map(([key, strategy]) => (
              <Card key={key} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader>
                  <CardTitle className="text-lg">{strategy.name}</CardTitle>
                  <CardDescription className="capitalize">{strategy.category}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4">
                    {strategy.description}
                  </p>
                  
                  <div className="space-y-2 mb-4">
                    <div className="flex justify-between text-sm">
                      <span>Risk Level</span>
                      <Badge variant="outline">{strategy.risk_level}</Badge>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Min Capital</span>
                      <span className="font-medium">${strategy.min_capital.toLocaleString()}</span>
                    </div>
                  </div>

                  <Button size="sm" className="w-full">
                    <Play className="w-3 h-3 mr-2" />
                    Execute Strategy
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Risk Management */}
        <TabsContent value="risk" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  Risk Limits
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Max Position Size (%)</Label>
                  <Slider
                    value={[10]}
                    max={50}
                    min={1}
                    step={1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>1%</span>
                    <span>10%</span>
                    <span>50%</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Daily Loss Limit (%)</Label>
                  <Slider
                    value={[5]}
                    max={20}
                    min={1}
                    step={0.5}
                    className="w-full"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto Stop Loss</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically set stop losses on all trades
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Current Risk Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Portfolio Risk</div>
                    <div className="text-lg font-bold text-green-500">Low</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Margin Used</div>
                    <div className="text-lg font-bold">0%</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Daily P&L</div>
                    <div className="text-lg font-bold text-green-500">+2.34%</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Max Drawdown</div>
                    <div className="text-lg font-bold">-1.2%</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
};

export default ManualTradingPage;