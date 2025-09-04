import React, { useState, useEffect, useRef } from 'react';
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
  Layers,
  Signal,
  Globe,
  Square
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
import { apiClient } from '@/lib/api/client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

// Beast Mode Configuration - Maximum Performance Settings
const BEAST_MODE_CONFIG = {
  dailyTarget: 15.0,
  monthlyTarget: 500.0,
  maxDrawdown: 35.0,
  minWinRate: 50.0,
  maxLeverage: 10.0,
  maxPositionSize: 25.0,
  aggressiveRebalancing: true,
  hftEnabled: true,
  derivativesEnabled: true,
  maxConcurrentTrades: 50
};

// HFT Algorithms Available in Beast Mode
const HFT_ALGORITHMS = [
  {
    name: 'Lightning Arbitrage',
    description: 'Sub-second cross-exchange arbitrage',
    avgExecutionTime: '150ms',
    successRate: 94.2,
    icon: Zap,
    color: 'text-yellow-500'
  },
  {
    name: 'Momentum Scalping',
    description: 'High-frequency momentum capture',
    avgExecutionTime: '300ms',
    successRate: 87.8,
    icon: TrendingUp,
    color: 'text-green-500'
  },
  {
    name: 'Market Making',
    description: 'Automated liquidity provision',
    avgExecutionTime: '50ms',
    successRate: 92.1,
    icon: Target,
    color: 'text-blue-500'
  },
  {
    name: 'Statistical Arbitrage',
    description: 'Mean reversion algorithms',
    avgExecutionTime: '500ms',
    successRate: 89.3,
    icon: BarChart3,
    color: 'text-purple-500'
  }
];

interface SystemStatus {
  is_active: boolean;
  current_mode: string;
  autonomous_enabled: boolean;
  simulation_mode: boolean;
  performance_metrics: {
    cycles_executed: number;
    trades_executed: number;
    total_profit_usd: number;
    success_rate: number;
    uptime_hours: number;
    consecutive_wins: number;
    consecutive_losses: number;
  };
  active_cycles: Array<{
    cycle_type: string;
    status: string;
    duration: string;
    profit: number;
    trades: number;
  }>;
  emergency_level: string;
}

interface RecentTrade {
  id: string;
  symbol: string;
  side: string;
  amount: number;
  price: number;
  profit_loss: number;
  timestamp: string;
  exchange: string;
  strategy: string;
}

interface ArbitrageOpportunity {
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  buy_price: number;
  sell_price: number;
  profit_percentage: number;
  profit_bps: number;
  volume_constraint: number;
  confidence: number;
}

const BeastModeDashboard: React.FC = () => {
  const user = useUser();
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [recentTrades, setRecentTrades] = useState<RecentTrade[]>([]);
  const [arbitrageOpps, setArbitrageOpps] = useState<ArbitrageOpportunity[]>([]);
  const [selectedMode, setSelectedMode] = useState('beast_mode');
  const [isActive, setIsActive] = useState(false);
  const [riskLevel, setRiskLevel] = useState([75]);
  const [maxDrawdown, setMaxDrawdown] = useState([35]);
  const [leverageLimit, setLeverageLimit] = useState([10]);
  const [performanceData, setPerformanceData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchSystemData();
    
    // Set up real-time updates every 2 seconds for Beast Mode
    intervalRef.current = setInterval(() => {
      fetchSystemData();
    }, 2000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const fetchSystemData = async () => {
    try {
      await Promise.all([
        fetchSystemStatus(),
        fetchRecentTrades(),
        fetchArbitrageOpportunities()
      ]);
      setLastUpdate(new Date());
    } catch (err: any) {
      console.error('Failed to fetch system data:', err);
      setError('Failed to fetch system data');
    }
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await apiClient.get('/trading/status');
      if (response.data.success) {
        setSystemStatus(response.data.data);
        setIsActive(response.data.data.is_active);
        
        // Update performance chart data
        if (response.data.data.performance_metrics) {
          setPerformanceData(prev => [
            ...prev.slice(-47), // Keep last 48 data points
            {
              time: new Date().toLocaleTimeString(),
              profit: response.data.data.performance_metrics.total_profit_usd,
              trades: response.data.data.performance_metrics.trades_executed,
              success: response.data.data.performance_metrics.success_rate,
              volume: Math.random() * 1000000 + 500000 // Mock volume for visualization
            }
          ]);
        }
      }
    } catch (err: any) {
      console.error('Failed to fetch system status:', err);
    }
  };

  const fetchRecentTrades = async () => {
    try {
      const response = await apiClient.get('/trading/recent-trades', {
        params: { limit: 20 }
      });
      if (response.data.success) {
        setRecentTrades(response.data.data.trades || []);
      }
    } catch (err: any) {
      console.error('Failed to fetch recent trades:', err);
    }
  };

  const fetchArbitrageOpportunities = async () => {
    try {
      const response = await apiClient.get('/trading/arbitrage/opportunities');
      if (response.data.success) {
        setArbitrageOpps(response.data.data.opportunities || []);
      }
    } catch (err: any) {
      console.error('Failed to fetch arbitrage opportunities:', err);
    }
  };

  const handleToggleBeastMode = async () => {
    try {
      setIsLoading(true);
      const endpoint = isActive ? '/trading/autonomous/stop' : '/trading/autonomous/start';
      const response = await apiClient.post(endpoint, {
        mode: 'beast_mode',
        risk_level: riskLevel[0],
        max_drawdown: maxDrawdown[0],
        max_leverage: leverageLimit[0]
      });
      
      if (response.data.success) {
        await fetchSystemStatus();
      }
    } catch (err: any) {
      setError('Failed to toggle Beast Mode');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmergencyStop = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.post('/trading/stop-all');
      if (response.data.success) {
        await fetchSystemStatus();
      }
    } catch (err: any) {
      setError('Failed to execute emergency stop');
    } finally {
      setIsLoading(false);
    }
  };

  if (!systemStatus) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Flame className="h-12 w-12 animate-pulse mx-auto mb-4 text-red-500" />
          <p className="text-muted-foreground">Loading Beast Mode...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Flame className="h-8 w-8 text-red-500" />
            Beast Mode Dashboard
            <Badge variant="destructive" className="ml-2">MAXIMUM PERFORMANCE</Badge>
          </h1>
          <p className="text-muted-foreground">
            High-frequency trading with AI-driven arbitrage and derivatives
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-2">
            <Activity className="h-4 w-4" />
            {lastUpdate.toLocaleTimeString()}
          </Badge>
          <Button
            variant="outline"
            onClick={() => fetchSystemData()}
            disabled={isLoading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-destructive/10 border border-destructive/30 rounded-lg"
        >
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium text-destructive">System Alert</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => setError(null)}>
              Dismiss
            </Button>
          </div>
        </motion.div>
      )}

      {/* Beast Mode Status & Controls */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className={`border-l-4 ${isActive ? 'border-l-red-500 bg-red-500/5' : 'border-l-gray-500 bg-gray-500/5'}`}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Beast Mode Status</CardTitle>
              <Flame className={`h-4 w-4 ${isActive ? 'text-red-500' : 'text-gray-500'}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isActive ? 'UNLEASHED' : 'DORMANT'}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <Switch
                  checked={isActive}
                  onCheckedChange={handleToggleBeastMode}
                  disabled={isLoading}
                />
                <span className="text-sm text-muted-foreground">
                  {isActive ? 'Active' : 'Inactive'}
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Profit</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-500">
                {formatCurrency(systemStatus.performance_metrics.total_profit_usd)}
              </div>
              <div className="text-sm text-muted-foreground">
                Target: {formatPercentage(BEAST_MODE_CONFIG.dailyTarget)} daily
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatPercentage(systemStatus.performance_metrics.success_rate)}
              </div>
              <Progress 
                value={systemStatus.performance_metrics.success_rate} 
                className="mt-2 h-2" 
              />
              <div className="text-sm text-muted-foreground mt-1">
                {systemStatus.performance_metrics.trades_executed} trades
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Algorithms</CardTitle>
              <Bot className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {HFT_ALGORITHMS.length}
              </div>
              <div className="text-sm text-muted-foreground">
                HFT algorithms running
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Main Dashboard */}
      <Tabs defaultValue="performance" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="algorithms">HFT Algorithms</TabsTrigger>
          <TabsTrigger value="arbitrage">Live Arbitrage</TabsTrigger>
          <TabsTrigger value="controls">Beast Controls</TabsTrigger>
        </TabsList>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Real-time Performance Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Real-time Performance
                </CardTitle>
                <CardDescription>Live profit tracking and trade execution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={performanceData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis
                        dataKey="time"
                        stroke="#9CA3AF"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="#9CA3AF"
                        fontSize={12}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1F2937',
                          border: '1px solid #374151',
                          borderRadius: '8px',
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="profit"
                        stroke="#ef4444"
                        fill="url(#beastGradient)"
                        strokeWidth={2}
                      />
                      <defs>
                        <linearGradient id="beastGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Recent Trades */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Live Trade Feed
                </CardTitle>
                <CardDescription>Real-time trade execution stream</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-[300px] overflow-y-auto">
                  {recentTrades.length > 0 ? (
                    recentTrades.slice(0, 10).map((trade, index) => (
                      <motion.div
                        key={trade.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="flex items-center justify-between p-3 rounded border bg-muted/20"
                      >
                        <div className="flex items-center gap-3">
                          <Badge variant={trade.side === 'buy' ? 'default' : 'destructive'}>
                            {trade.side.toUpperCase()}
                          </Badge>
                          <div>
                            <div className="font-medium">{trade.symbol}</div>
                            <div className="text-xs text-muted-foreground">
                              {trade.exchange} • {trade.strategy}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-sm">
                            {formatCurrency(trade.price)}
                          </div>
                          <div className={`text-xs font-mono ${
                            trade.profit_loss >= 0 ? 'text-green-500' : 'text-red-500'
                          }`}>
                            {trade.profit_loss >= 0 ? '+' : ''}{formatCurrency(trade.profit_loss)}
                          </div>
                        </div>
                      </motion.div>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No recent trades available</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Performance Metrics */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Uptime</p>
                    <p className="text-2xl font-bold">
                      {formatNumber(systemStatus.performance_metrics.uptime_hours)}h
                    </p>
                  </div>
                  <Clock className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Win Streak</p>
                    <p className="text-2xl font-bold text-green-500">
                      {systemStatus.performance_metrics.consecutive_wins}
                    </p>
                  </div>
                  <Sparkles className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Cycles</p>
                    <p className="text-2xl font-bold">
                      {systemStatus.performance_metrics.cycles_executed}
                    </p>
                  </div>
                  <Cpu className="h-8 w-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Emergency</p>
                    <p className="text-2xl font-bold">
                      {systemStatus.emergency_level.toUpperCase()}
                    </p>
                  </div>
                  <Shield className="h-8 w-8 text-yellow-500" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* HFT Algorithms Tab */}
        <TabsContent value="algorithms" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            {HFT_ALGORITHMS.map((algorithm, index) => (
              <motion.div
                key={algorithm.name}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="hover:shadow-lg transition-shadow">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <div className="flex items-center gap-3">
                      <algorithm.icon className={`h-6 w-6 ${algorithm.color}`} />
                      <div>
                        <CardTitle className="text-base">{algorithm.name}</CardTitle>
                        <CardDescription className="text-xs">
                          {algorithm.description}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant="default">ACTIVE</Badge>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Execution Time:</span>
                        <span className="ml-2 font-mono text-blue-500">
                          {algorithm.avgExecutionTime}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Success Rate:</span>
                        <span className="ml-2 font-mono text-green-500">
                          {formatPercentage(algorithm.successRate)}
                        </span>
                      </div>
                    </div>
                    <Progress 
                      value={algorithm.successRate} 
                      className="mt-3 h-2" 
                    />
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </TabsContent>

        {/* Live Arbitrage Tab */}
        <TabsContent value="arbitrage" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Live Arbitrage Opportunities
              </CardTitle>
              <CardDescription>Real-time cross-exchange arbitrage detection</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {arbitrageOpps.length > 0 ? (
                  arbitrageOpps.slice(0, 8).map((opp, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="flex items-center justify-between p-4 rounded-lg border bg-muted/20 hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <Badge variant="outline" className="font-mono">
                          {opp.symbol}
                        </Badge>
                        <div>
                          <div className="font-medium">
                            {opp.buy_exchange} → {opp.sell_exchange}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Buy: {formatCurrency(opp.buy_price)} | Sell: {formatCurrency(opp.sell_price)}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-green-500">
                          +{formatPercentage(opp.profit_percentage)}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {opp.profit_bps} bps • {Math.round(opp.confidence)}% conf
                        </div>
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <div className="text-center py-8">
                    <Zap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">
                      Scanning for arbitrage opportunities...
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Beast Controls Tab */}
        <TabsContent value="controls" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Risk Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Beast Mode Controls
                </CardTitle>
                <CardDescription>Maximum performance configuration</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <Label className="text-sm font-medium">Risk Level: {riskLevel[0]}%</Label>
                  <Slider
                    value={riskLevel}
                    onValueChange={setRiskLevel}
                    max={100}
                    min={50}
                    step={5}
                    className="mt-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Higher risk = Higher potential returns
                  </p>
                </div>

                <div>
                  <Label className="text-sm font-medium">Max Drawdown: {maxDrawdown[0]}%</Label>
                  <Slider
                    value={maxDrawdown}
                    onValueChange={setMaxDrawdown}
                    max={50}
                    min={10}
                    step={5}
                    className="mt-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Maximum acceptable portfolio decline
                  </p>
                </div>

                <div>
                  <Label className="text-sm font-medium">Leverage Limit: {leverageLimit[0]}x</Label>
                  <Slider
                    value={leverageLimit}
                    onValueChange={setLeverageLimit}
                    max={20}
                    min={1}
                    step={1}
                    className="mt-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Maximum leverage for positions
                  </p>
                </div>

                <div className="pt-4 border-t space-y-3">
                  <Button
                    variant={isActive ? "destructive" : "default"}
                    onClick={handleToggleBeastMode}
                    disabled={isLoading}
                    className="w-full gap-2"
                  >
                    {isActive ? (
                      <>
                        <Pause className="h-4 w-4" />
                        Stop Beast Mode
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        Unleash Beast Mode
                      </>
                    )}
                  </Button>

                  <Button
                    variant="outline"
                    onClick={handleEmergencyStop}
                    disabled={isLoading}
                    className="w-full gap-2 border-red-500 text-red-500 hover:bg-red-500 hover:text-white"
                  >
                    <Square className="h-4 w-4" />
                    EMERGENCY STOP ALL
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Beast Mode Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Crown className="h-5 w-5" />
                  Beast Mode Specifications
                </CardTitle>
                <CardDescription>Maximum performance parameters</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Daily Target:</span>
                      <span className="ml-2 font-mono text-green-500">
                        {formatPercentage(BEAST_MODE_CONFIG.dailyTarget)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Monthly Target:</span>
                      <span className="ml-2 font-mono text-green-500">
                        {formatPercentage(BEAST_MODE_CONFIG.monthlyTarget)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Max Position:</span>
                      <span className="ml-2 font-mono">
                        {formatPercentage(BEAST_MODE_CONFIG.maxPositionSize)}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Concurrent Trades:</span>
                      <span className="ml-2 font-mono">
                        {BEAST_MODE_CONFIG.maxConcurrentTrades}
                      </span>
                    </div>
                  </div>

                  <div className="pt-4 border-t">
                    <h4 className="font-medium mb-3">Enabled Features:</h4>
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">High-Frequency Trading</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">Derivatives Trading</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">Aggressive Rebalancing</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">Multi-Exchange Arbitrage</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span className="text-sm">AI-Driven Market Making</span>
                      </div>
                    </div>
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

export default BeastModeDashboard;