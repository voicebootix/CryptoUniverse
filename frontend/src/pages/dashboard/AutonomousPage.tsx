import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot,
  Play,
  Pause,
  Settings,
  Target,
  TrendingUp,
  Shield,
  Clock,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Activity,
  BarChart3,
  Zap,
  RefreshCw,
  Eye,
  Sliders,
  Brain,
  Cpu,
  Flame,
  Rocket,
  Crown,
  Swords,
  Timer,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { useUser } from '@/store/authStore';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';

interface AutonomousConfig {
  mode: 'conservative' | 'balanced' | 'aggressive' | 'beast_mode';
  maxDailyLossPct: number;
  maxPositionSizePct: number;
  allowedSymbols: string[];
  excludedSymbols: string[];
  tradingHours: {
    start: string;
    end: string;
  };
  riskTolerance: number;
  targetProfitPct: number;
  stopLossPct: number;
  enableArbitrage: boolean;
  enableMomentum: boolean;
  enableMeanReversion: boolean;
  enableHFT: boolean;
}

const defaultConfig: AutonomousConfig = {
  mode: 'balanced',
  maxDailyLossPct: 5.0,
  maxPositionSizePct: 10.0,
  allowedSymbols: ['BTC', 'ETH', 'SOL', 'ADA', 'DOT'],
  excludedSymbols: [],
  tradingHours: {
    start: '00:00',
    end: '23:59',
  },
  riskTolerance: 50,
  targetProfitPct: 2.0,
  stopLossPct: 1.5,
  enableArbitrage: true,
  enableMomentum: true,
  enableMeanReversion: false,
  enableHFT: false,
};

const modeDescriptions = {
  conservative: {
    title: 'Conservative',
    description: 'Low risk, steady returns with minimal volatility',
    color: 'bg-blue-500',
    estimatedTrades: '2-5 per day',
    riskLevel: 'Low',
  },
  balanced: {
    title: 'Balanced',
    description: 'Moderate risk with balanced growth potential',
    color: 'bg-green-500',
    estimatedTrades: '5-15 per day',
    riskLevel: 'Medium',
  },
  aggressive: {
    title: 'Aggressive',
    description: 'Higher risk for potentially greater returns',
    color: 'bg-orange-500',
    estimatedTrades: '15-30 per day',
    riskLevel: 'High',
  },
  beast_mode: {
    title: 'Beast Mode',
    description: 'Maximum performance with high-frequency trading',
    color: 'bg-red-500',
    estimatedTrades: '50+ per day',
    riskLevel: 'Very High',
  },
};

const availableSymbols = [
  'BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'MATIC', 'LINK', 'UNI', 'AVAX', 'ATOM',
  'NEAR', 'FTM', 'ALGO', 'XTZ', 'EGLD', 'SAND', 'MANA', 'CRV', 'AAVE', 'COMP',
];

const AutonomousPage: React.FC = () => {
  const user = useUser();
  const [isActive, setIsActive] = useState(false);
  const [config, setConfig] = useState<AutonomousConfig>(defaultConfig);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionStats, setSessionStats] = useState({
    duration: '2h 34m',
    tradesExecuted: 12,
    totalPnL: 245.67,
    winRate: 83.3,
    bestTrade: 45.30,
    worstTrade: -12.10,
  });

  const handleStart = async () => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      setIsActive(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      setIsActive(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfigChange = <K extends keyof AutonomousConfig>(
    key: K,
    value: AutonomousConfig[K]
  ) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const currentMode = modeDescriptions[config.mode];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Bot className="h-8 w-8 text-primary" />
            Autonomous Trading
          </h1>
          <p className="text-muted-foreground">
            AI-powered automated trading with advanced risk management
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge
            variant={isActive ? 'profit' : 'outline'}
            className="px-3 py-1"
          >
            {isActive ? 'Active' : 'Inactive'}
          </Badge>
          
          {isActive ? (
            <Button
              variant="destructive"
              onClick={handleStop}
              disabled={isLoading}
              className="gap-2"
            >
              <Pause className="h-4 w-4" />
              {isLoading ? 'Stopping...' : 'Stop Trading'}
            </Button>
          ) : (
            <Button
              variant="profit"
              onClick={handleStart}
              disabled={isLoading}
              className="gap-2"
            >
              <Play className="h-4 w-4" />
              {isLoading ? 'Starting...' : 'Start Trading'}
            </Button>
          )}
        </div>
      </div>

      {/* Status Banner */}
      {user?.simulation_mode && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-warning/10 border border-warning/30 rounded-lg"
        >
          <div className="flex items-center gap-3">
            <Eye className="h-5 w-5 text-warning" />
            <div>
              <p className="font-medium text-warning">Simulation Mode Active</p>
              <p className="text-sm text-muted-foreground">
                Autonomous trading is running in simulation mode with virtual funds.
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Main Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="configuration">Configuration</TabsTrigger>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Status Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card className="trading-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">AI Status</CardTitle>
                  <Brain className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <div className={`h-3 w-3 rounded-full ${isActive ? 'bg-profit animate-pulse' : 'bg-muted'}`} />
                    <span className="text-lg font-bold">
                      {isActive ? 'Active' : 'Standby'}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {isActive ? 'AI is monitoring markets' : 'Ready to start trading'}
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="trading-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Trading Mode</CardTitle>
                  <Settings className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-bold">{currentMode.title}</div>
                  <div className="flex items-center gap-2 text-xs">
                    <div className={`w-2 h-2 rounded-full ${currentMode.color}`} />
                    <span className="text-muted-foreground">{currentMode.riskLevel} Risk</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card className="trading-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Session P&L</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-bold text-profit">
                    +{formatCurrency(sessionStats.totalPnL)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Win rate: {formatPercentage(sessionStats.winRate)}
                  </p>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card className="trading-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Trades Today</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-bold">{sessionStats.tradesExecuted}</div>
                  <p className="text-xs text-muted-foreground">
                    Duration: {sessionStats.duration}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* AI Insights */}
          <div className="grid gap-6 lg:grid-cols-2">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card className="trading-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Cpu className="h-5 w-5" />
                    AI Market Analysis
                  </CardTitle>
                  <CardDescription>Real-time market sentiment and opportunities</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-profit/10 border border-profit/30 rounded-lg">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-5 w-5 text-profit" />
                        <div>
                          <p className="font-medium">BTC Bullish Signal</p>
                          <p className="text-sm text-muted-foreground">Strong momentum detected</p>
                        </div>
                      </div>
                      <Badge variant="profit">High Confidence</Badge>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-warning/10 border border-warning/30 rounded-lg">
                      <div className="flex items-center gap-3">
                        <AlertTriangle className="h-5 w-5 text-warning" />
                        <div>
                          <p className="font-medium">ETH Volatility Alert</p>
                          <p className="text-sm text-muted-foreground">Increased market uncertainty</p>
                        </div>
                      </div>
                      <Badge variant="warning">Medium</Badge>
                    </div>

                    <div className="flex items-center justify-between p-3 bg-chart-1/10 border border-chart-1/30 rounded-lg">
                      <div className="flex items-center gap-3">
                        <Target className="h-5 w-5 text-chart-1" />
                        <div>
                          <p className="font-medium">SOL Arbitrage Opportunity</p>
                          <p className="text-sm text-muted-foreground">Price difference detected</p>
                        </div>
                      </div>
                      <Badge variant="outline">Low Risk</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 }}
            >
              <Card className="trading-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    Strategy Performance
                  </CardTitle>
                  <CardDescription>Active strategy performance metrics</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Momentum Trading</span>
                        <span className="text-sm text-profit">+12.5%</span>
                      </div>
                      <Progress value={85} className="h-2" />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Arbitrage</span>
                        <span className="text-sm text-profit">+8.3%</span>
                      </div>
                      <Progress value={65} className="h-2" />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Mean Reversion</span>
                        <span className="text-sm text-loss">-2.1%</span>
                      </div>
                      <Progress value={25} className="h-2" />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">High Frequency</span>
                        <span className="text-sm text-profit">+5.7%</span>
                      </div>
                      <Progress value={45} className="h-2" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </TabsContent>

        {/* Configuration Tab */}
        <TabsContent value="configuration" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Trading Mode */}
            <Card className="trading-card">
              <CardHeader>
                <CardTitle>Trading Mode</CardTitle>
                <CardDescription>Select your preferred trading strategy</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3">
                  {Object.entries(modeDescriptions).map(([key, mode]) => (
                    <div
                      key={key}
                      className={`p-4 rounded-lg border cursor-pointer transition-all ${
                        config.mode === key
                          ? 'border-primary bg-primary/5'
                          : 'border-muted hover:border-muted-foreground/50'
                      }`}
                      onClick={() => handleConfigChange('mode', key as any)}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${mode.color}`} />
                        <div className="flex-1">
                          <h4 className="font-medium">{mode.title}</h4>
                          <p className="text-sm text-muted-foreground">{mode.description}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs">
                            <span>{mode.estimatedTrades}</span>
                            <span>•</span>
                            <span>{mode.riskLevel} Risk</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Risk Management */}
            <Card className="trading-card">
              <CardHeader>
                <CardTitle>Risk Management</CardTitle>
                <CardDescription>Configure risk parameters and limits</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Max Daily Loss (%)</Label>
                  <div className="px-3">
                    <Slider
                      value={[config.maxDailyLossPct]}
                      onValueChange={([value]) => handleConfigChange('maxDailyLossPct', value)}
                      max={20}
                      min={1}
                      step={0.5}
                      className="w-full"
                    />
                  </div>
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>1%</span>
                    <span className="font-medium">{config.maxDailyLossPct}%</span>
                    <span>20%</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Max Position Size (%)</Label>
                  <div className="px-3">
                    <Slider
                      value={[config.maxPositionSizePct]}
                      onValueChange={([value]) => handleConfigChange('maxPositionSizePct', value)}
                      max={50}
                      min={1}
                      step={1}
                      className="w-full"
                    />
                  </div>
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>1%</span>
                    <span className="font-medium">{config.maxPositionSizePct}%</span>
                    <span>50%</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Risk Tolerance</Label>
                  <div className="px-3">
                    <Slider
                      value={[config.riskTolerance]}
                      onValueChange={([value]) => handleConfigChange('riskTolerance', value)}
                      max={100}
                      min={1}
                      step={5}
                      className="w-full"
                    />
                  </div>
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>Conservative</span>
                    <span className="font-medium">{config.riskTolerance}</span>
                    <span>Aggressive</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Asset Selection */}
            <Card className="trading-card">
              <CardHeader>
                <CardTitle>Asset Selection</CardTitle>
                <CardDescription>Choose which cryptocurrencies to trade</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Allowed Symbols</Label>
                  <div className="flex flex-wrap gap-2">
                    {availableSymbols.map((symbol) => (
                      <Badge
                        key={symbol}
                        variant={config.allowedSymbols.includes(symbol) ? "default" : "outline"}
                        className="cursor-pointer"
                        onClick={() => {
                          if (config.allowedSymbols.includes(symbol)) {
                            handleConfigChange(
                              'allowedSymbols',
                              config.allowedSymbols.filter(s => s !== symbol)
                            );
                          } else {
                            handleConfigChange(
                              'allowedSymbols',
                              [...config.allowedSymbols, symbol]
                            );
                          }
                        }}
                      >
                        {symbol}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Target Profit (%)</Label>
                    <Input
                      type="number"
                      value={config.targetProfitPct}
                      onChange={(e) => handleConfigChange('targetProfitPct', parseFloat(e.target.value) || 0)}
                      min={0.1}
                      max={10}
                      step={0.1}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Stop Loss (%)</Label>
                    <Input
                      type="number"
                      value={config.stopLossPct}
                      onChange={(e) => handleConfigChange('stopLossPct', parseFloat(e.target.value) || 0)}
                      min={0.1}
                      max={5}
                      step={0.1}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Trading Hours */}
            <Card className="trading-card">
              <CardHeader>
                <CardTitle>Trading Schedule</CardTitle>
                <CardDescription>Set active trading hours (24/7 by default)</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Start Time</Label>
                    <Input
                      type="time"
                      value={config.tradingHours.start}
                      onChange={(e) => handleConfigChange('tradingHours', {
                        ...config.tradingHours,
                        start: e.target.value
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>End Time</Label>
                    <Input
                      type="time"
                      value={config.tradingHours.end}
                      onChange={(e) => handleConfigChange('tradingHours', {
                        ...config.tradingHours,
                        end: e.target.value
                      })}
                    />
                  </div>
                </div>

                <div className="p-4 bg-muted/30 rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    <Clock className="h-4 w-4 inline mr-2" />
                    Active trading window: {config.tradingHours.start} - {config.tradingHours.end} UTC
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Strategies Tab */}
        <TabsContent value="strategies" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="trading-card">
              <CardHeader>
                <CardTitle>Trading Strategies</CardTitle>
                <CardDescription>Enable/disable specific trading algorithms</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">Arbitrage Trading</Label>
                      <p className="text-sm text-muted-foreground">
                        Exploit price differences across exchanges
                      </p>
                    </div>
                    <Switch
                      checked={config.enableArbitrage}
                      onCheckedChange={(checked) => handleConfigChange('enableArbitrage', checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">Momentum Trading</Label>
                      <p className="text-sm text-muted-foreground">
                        Follow strong price trends and momentum
                      </p>
                    </div>
                    <Switch
                      checked={config.enableMomentum}
                      onCheckedChange={(checked) => handleConfigChange('enableMomentum', checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">Mean Reversion</Label>
                      <p className="text-sm text-muted-foreground">
                        Trade on price reversals to the mean
                      </p>
                    </div>
                    <Switch
                      checked={config.enableMeanReversion}
                      onCheckedChange={(checked) => handleConfigChange('enableMeanReversion', checked)}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">High-Frequency Trading</Label>
                      <p className="text-sm text-muted-foreground">
                        Rapid trades on micro price movements
                      </p>
                    </div>
                    <Switch
                      checked={config.enableHFT}
                      onCheckedChange={(checked) => handleConfigChange('enableHFT', checked)}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="trading-card">
              <CardHeader>
                <CardTitle>AI Models</CardTitle>
                <CardDescription>Multi-model consensus configuration</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-profit rounded-full" />
                      <div>
                        <p className="font-medium">GPT-4</p>
                        <p className="text-sm text-muted-foreground">Market analysis & sentiment</p>
                      </div>
                    </div>
                    <Badge variant="profit">Active</Badge>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-profit rounded-full" />
                      <div>
                        <p className="font-medium">Claude</p>
                        <p className="text-sm text-muted-foreground">Risk assessment</p>
                      </div>
                    </div>
                    <Badge variant="profit">Active</Badge>
                  </div>

                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 bg-profit rounded-full" />
                      <div>
                        <p className="font-medium">Gemini</p>
                        <p className="text-sm text-muted-foreground">Technical analysis</p>
                      </div>
                    </div>
                    <Badge variant="profit">Active</Badge>
                  </div>

                  <div className="p-3 bg-primary/10 border border-primary/30 rounded-lg">
                    <p className="text-sm">
                      <Brain className="h-4 w-4 inline mr-2" />
                      Consensus accuracy: <span className="font-medium">94.7%</span>
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-6">
          <div className="grid gap-6">
            <Card className="trading-card">
              <CardHeader>
                <CardTitle>Session Statistics</CardTitle>
                <CardDescription>Current trading session performance</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="text-center p-4 bg-muted/30 rounded-lg">
                    <div className="text-2xl font-bold text-profit">
                      +{formatCurrency(sessionStats.totalPnL)}
                    </div>
                    <p className="text-sm text-muted-foreground">Total P&L</p>
                  </div>
                  <div className="text-center p-4 bg-muted/30 rounded-lg">
                    <div className="text-2xl font-bold">
                      {formatPercentage(sessionStats.winRate)}
                    </div>
                    <p className="text-sm text-muted-foreground">Win Rate</p>
                  </div>
                  <div className="text-center p-4 bg-muted/30 rounded-lg">
                    <div className="text-2xl font-bold text-profit">
                      +{formatCurrency(sessionStats.bestTrade)}
                    </div>
                    <p className="text-sm text-muted-foreground">Best Trade</p>
                  </div>
                  <div className="text-center p-4 bg-muted/30 rounded-lg">
                    <div className="text-2xl font-bold text-loss">
                      {formatCurrency(sessionStats.worstTrade)}
                    </div>
                    <p className="text-sm text-muted-foreground">Worst Trade</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AutonomousPage;
