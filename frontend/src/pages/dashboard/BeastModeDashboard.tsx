import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Flame,
  Zap,
  Rocket,
  Crown,
  Swords,
  Timer,
  Bot,
  Play,
  Pause,
  Settings,
  Target,
  TrendingUp,
  TrendingDown,
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
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  Gauge,
  Power,
  Crosshair,
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
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Trading Modes Configuration
const tradingModes = [
  {
    id: 'conservative',
    name: 'Conservative',
    icon: Shield,
    color: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    description: 'Low risk, steady gains',
    maxRisk: 2,
    avgReturn: '8-12%',
    features: ['Stop losses', 'Position limits', 'Risk management']
  },
  {
    id: 'balanced',
    name: 'Balanced',
    icon: Target,
    color: 'bg-green-500/10 text-green-500 border-green-500/20',
    description: 'Optimal risk-reward ratio',
    maxRisk: 5,
    avgReturn: '15-25%',
    features: ['AI consensus', 'Dynamic sizing', 'Multi-timeframe']
  },
  {
    id: 'aggressive',
    name: 'Aggressive',
    icon: Zap,
    color: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    description: 'Higher risk, higher rewards',
    maxRisk: 10,
    avgReturn: '30-50%',
    features: ['Leverage trading', 'Momentum plays', 'Quick execution']
  },
  {
    id: 'beast_mode',
    name: 'Beast Mode',
    icon: Flame,
    color: 'bg-red-500/10 text-red-500 border-red-500/20',
    description: 'Maximum performance, institutional-grade',
    maxRisk: 20,
    avgReturn: '50-100%+',
    features: ['HFT algorithms', 'Derivatives', 'AI-driven arbitrage']
  }
];

// Trading Cycles
const tradingCycles = [
  {
    name: 'Arbitrage Cycle',
    status: 'active',
    duration: '15s',
    profit: '+$247.50',
    trades: 23,
    success: 95.7,
    icon: Zap,
    color: 'text-green-500',
    description: 'Cross-exchange price differences'
  },
  {
    name: 'Momentum Cycle',
    status: 'active',
    duration: '4m',
    profit: '+$1,247.25',
    trades: 8,
    success: 87.5,
    icon: TrendingUp,
    color: 'text-blue-500',
    description: 'Trend following with AI confirmation'
  },
  {
    name: 'Portfolio Rebalance',
    status: 'pending',
    duration: '1h',
    profit: '+$0.00',
    trades: 0,
    success: 0,
    icon: BarChart3,
    color: 'text-yellow-500',
    description: 'Risk-adjusted portfolio optimization'
  },
  {
    name: 'Deep Analysis',
    status: 'analyzing',
    duration: '30m',
    profit: '+$0.00',
    trades: 0,
    success: 0,
    icon: Brain,
    color: 'text-purple-500',
    description: 'Multi-AI consensus and market sentiment'
  }
];

// Live Trading Activity
const liveActivity = [
  {
    id: 1,
    type: 'BUY',
    symbol: 'BTC/USDT',
    amount: 0.25,
    price: 51250.00,
    time: '10:45:23',
    profit: '+$125.50',
    status: 'completed',
    confidence: 94,
    strategy: 'Momentum'
  },
  {
    id: 2,
    type: 'SELL',
    symbol: 'ETH/USDT',
    amount: 5.0,
    price: 2420.00,
    time: '10:44:15',
    profit: '+$75.25',
    status: 'completed',
    confidence: 87,
    strategy: 'Arbitrage'
  },
  {
    id: 3,
    type: 'BUY',
    symbol: 'SOL/USDT',
    amount: 50.0,
    price: 52.30,
    time: '10:43:42',
    profit: '+$47.80',
    status: 'pending',
    confidence: 91,
    strategy: 'Mean Reversion'
  },
  {
    id: 4,
    type: 'SELL',
    symbol: 'AVAX/USDT',
    amount: 25.0,
    price: 28.75,
    time: '10:42:18',
    profit: '-$15.25',
    status: 'completed',
    confidence: 76,
    strategy: 'Risk Management'
  }
];

// Performance data
const performanceData = [
  { time: '09:00', profit: 0, trades: 0 },
  { time: '09:15', profit: 125, trades: 3 },
  { time: '09:30', profit: 347, trades: 8 },
  { time: '09:45', profit: 892, trades: 15 },
  { time: '10:00', profit: 1247, trades: 23 },
  { time: '10:15', profit: 1456, trades: 28 },
  { time: '10:30', profit: 1789, trades: 34 },
  { time: '10:45', profit: 2147, trades: 41 },
];

const BeastModeDashboard: React.FC = () => {
  const user = useUser();
  const [selectedMode, setSelectedMode] = useState('beast_mode');
  const [isActive, setIsActive] = useState(true);
  const [riskLevel, setRiskLevel] = useState([15]);
  const [targetProfit, setTargetProfit] = useState([25]);
  const [maxDrawdown, setMaxDrawdown] = useState([5]);

  const currentMode = tradingModes.find(mode => mode.id === selectedMode);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'pending': return 'bg-yellow-500';
      case 'analyzing': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const getTradeTypeColor = (type: string) => {
    return type === 'BUY' ? 'text-green-500' : 'text-red-500';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Flame className="h-8 w-8 text-red-500" />
            Beast Mode Dashboard
            <Crown className="h-6 w-6 text-yellow-500" />
          </h1>
          <p className="text-muted-foreground">
            Autonomous $100M hedge fund brain - Maximum performance mode
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant={isActive ? "destructive" : "default"}
            onClick={() => setIsActive(!isActive)}
            className="gap-2"
          >
            {isActive ? (
              <>
                <Pause className="h-4 w-4" />
                Stop Beast Mode
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Activate Beast Mode
              </>
            )}
          </Button>

          <Button variant="outline" className="gap-2">
            <Settings className="h-4 w-4" />
            Configure
          </Button>
        </div>
      </div>

      {/* Beast Mode Status */}
      {isActive && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="relative overflow-hidden rounded-lg border border-red-500/20 bg-gradient-to-r from-red-500/5 to-orange-500/5 p-6"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <Flame className="h-12 w-12 text-red-500" />
                <div className="absolute -top-1 -right-1">
                  <div className="h-3 w-3 bg-red-500 rounded-full animate-pulse"></div>
                </div>
              </div>
              <div>
                <h3 className="text-xl font-bold text-red-500">BEAST MODE ACTIVE</h3>
                <p className="text-sm text-muted-foreground">
                  Autonomous trading at maximum performance
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-green-500">+$2,147.50</div>
              <div className="text-sm text-muted-foreground">Today's P&L</div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Cycles</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">2/4</div>
            <p className="text-xs text-muted-foreground">
              Arbitrage & Momentum running
            </p>
            <div className="flex gap-1 mt-2">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <div className="h-2 w-2 rounded-full bg-yellow-500"></div>
              <div className="h-2 w-2 rounded-full bg-blue-500"></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">91.5%</div>
            <p className="text-xs text-muted-foreground">
              +2.3% from yesterday
            </p>
            <Progress value={91.5} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Trade Time</CardTitle>
            <Timer className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2.3s</div>
            <p className="text-xs text-muted-foreground">
              Lightning fast execution
            </p>
            <Badge variant="secondary" className="mt-2">HFT Active</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Risk Level</CardTitle>
            <Gauge className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-500">{riskLevel[0]}%</div>
            <p className="text-xs text-muted-foreground">
              Managed exposure
            </p>
            <Progress value={riskLevel[0]} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="cycles">Trading Cycles</TabsTrigger>
          <TabsTrigger value="activity">Live Activity</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Performance Chart</CardTitle>
                <CardDescription>
                  Real-time P&L and trade count
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={performanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="profit" stroke="#10b981" strokeWidth={2} name="Profit ($)" />
                    <Line type="monotone" dataKey="trades" stroke="#3b82f6" strokeWidth={2} name="Trades" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Trading Mode</CardTitle>
                <CardDescription>
                  Current autonomous configuration
                </CardDescription>
              </CardHeader>
              <CardContent>
                {currentMode && (
                  <div className="space-y-4">
                    <div className={`p-4 rounded-lg border ${currentMode.color}`}>
                      <div className="flex items-center gap-3">
                        <currentMode.icon className="h-8 w-8" />
                        <div>
                          <h3 className="font-bold text-lg">{currentMode.name}</h3>
                          <p className="text-sm opacity-80">{currentMode.description}</p>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-muted-foreground">Max Risk</div>
                        <div className="font-medium">{currentMode.maxRisk}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Avg Return</div>
                        <div className="font-medium">{currentMode.avgReturn}</div>
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-muted-foreground mb-2">Features</div>
                      <div className="flex flex-wrap gap-2">
                        {currentMode.features.map((feature, index) => (
                          <Badge key={index} variant="secondary">
                            {feature}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="cycles" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tradingCycles.map((cycle, index) => (
              <motion.div
                key={cycle.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <cycle.icon className={`h-5 w-5 ${cycle.color}`} />
                        <CardTitle className="text-lg">{cycle.name}</CardTitle>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className={`h-2 w-2 rounded-full ${getStatusColor(cycle.status)}`}></div>
                        <Badge variant="secondary" className="capitalize">
                          {cycle.status}
                        </Badge>
                      </div>
                    </div>
                    <CardDescription>{cycle.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-muted-foreground">Duration</div>
                        <div className="font-medium">{cycle.duration}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Profit</div>
                        <div className="font-medium text-green-500">{cycle.profit}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Trades</div>
                        <div className="font-medium">{cycle.trades}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Success</div>
                        <div className="font-medium">{cycle.success}%</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="activity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Live Trading Activity</CardTitle>
              <CardDescription>
                Real-time trade execution and results
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {liveActivity.map((trade) => (
                  <div key={trade.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded ${trade.type === 'BUY' ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                        {trade.type === 'BUY' ? (
                          <ArrowUpRight className={`h-4 w-4 ${getTradeTypeColor(trade.type)}`} />
                        ) : (
                          <ArrowDownRight className={`h-4 w-4 ${getTradeTypeColor(trade.type)}`} />
                        )}
                      </div>
                      <div>
                        <div className="font-medium">{trade.symbol}</div>
                        <div className="text-sm text-muted-foreground">
                          {trade.strategy} • {trade.time}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-medium ${trade.profit.startsWith('+') ? 'text-green-500' : 'text-red-500'}`}>
                        {trade.profit}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {trade.confidence}% confidence
                      </div>
                    </div>
                    <Badge variant={trade.status === 'completed' ? 'default' : 'secondary'}>
                      {trade.status}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Risk Management</CardTitle>
                <CardDescription>
                  Configure risk parameters for Beast Mode
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Risk Level: {riskLevel[0]}%</Label>
                  <Slider
                    value={riskLevel}
                    onValueChange={setRiskLevel}
                    max={25}
                    min={1}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Target Profit: {targetProfit[0]}%</Label>
                  <Slider
                    value={targetProfit}
                    onValueChange={setTargetProfit}
                    max={100}
                    min={5}
                    step={5}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Max Drawdown: {maxDrawdown[0]}%</Label>
                  <Slider
                    value={maxDrawdown}
                    onValueChange={setMaxDrawdown}
                    max={20}
                    min={1}
                    step={1}
                    className="w-full"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Strategy Configuration</CardTitle>
                <CardDescription>
                  Enable/disable trading strategies
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">High-Frequency Trading</div>
                    <div className="text-sm text-muted-foreground">Sub-second execution</div>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Arbitrage Trading</div>
                    <div className="text-sm text-muted-foreground">Cross-exchange opportunities</div>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Derivatives Trading</div>
                    <div className="text-sm text-muted-foreground">Futures and options</div>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">AI Consensus</div>
                    <div className="text-sm text-muted-foreground">Multi-AI decision making</div>
                  </div>
                  <Switch defaultChecked />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default BeastModeDashboard;
