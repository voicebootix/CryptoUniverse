import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Power,
  Brain,
  Zap,
  Shield,
  Target,
  Activity,
  Clock,
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Play,
  Pause,
  Square,
  Settings,
  Eye,
  Gauge,
  Cpu,
  Globe,
  ArrowUpRight,
  ArrowDownRight,
  Flame,
  Crown,
  Timer,
  BarChart3,
  Layers,
  Crosshair,
  Sparkles
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

// Trading Modes from backend MasterController
const TRADING_MODES = [
  {
    id: 'conservative',
    name: 'Conservative',
    icon: Shield,
    color: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    description: 'Low risk, steady gains',
    dailyTarget: 1.5,
    monthlyTarget: 30.0,
    maxDrawdown: 5.0,
    minWinRate: 70.0,
    maxLeverage: 1.0
  },
  {
    id: 'balanced',
    name: 'Balanced',
    icon: Target,
    color: 'bg-green-500/10 text-green-500 border-green-500/20',
    description: 'Optimal risk-reward ratio',
    dailyTarget: 3.5,
    monthlyTarget: 70.0,
    maxDrawdown: 10.0,
    minWinRate: 65.0,
    maxLeverage: 3.0
  },
  {
    id: 'aggressive',
    name: 'Aggressive',
    icon: Zap,
    color: 'bg-orange-500/10 text-orange-500 border-orange-500/20',
    description: 'Higher risk, higher rewards',
    dailyTarget: 7.5,
    monthlyTarget: 200.0,
    maxDrawdown: 20.0,
    minWinRate: 55.0,
    maxLeverage: 5.0
  },
  {
    id: 'beast_mode',
    name: 'Beast Mode',
    icon: Flame,
    color: 'bg-red-500/10 text-red-500 border-red-500/20',
    description: 'Maximum performance',
    dailyTarget: 15.0,
    monthlyTarget: 500.0,
    maxDrawdown: 35.0,
    minWinRate: 50.0,
    maxLeverage: 10.0
  }
];

// Trading Cycles from backend MasterController
const TRADING_CYCLES = [
  {
    id: 'arbitrage_hunter',
    name: 'Arbitrage Hunter',
    description: 'Cross-exchange arbitrage opportunities',
    icon: Target,
    color: 'text-green-500'
  },
  {
    id: 'momentum_futures',
    name: 'Momentum Futures',
    description: 'High-frequency momentum trading',
    icon: Zap,
    color: 'text-blue-500'
  },
  {
    id: 'portfolio_optimization',
    name: 'Portfolio Optimization',
    description: 'Dynamic portfolio rebalancing',
    icon: Layers,
    color: 'text-purple-500'
  },
  {
    id: 'deep_analysis',
    name: 'Deep Analysis',
    description: 'AI-powered market analysis',
    icon: Brain,
    color: 'text-orange-500'
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
  last_update: string;
}

interface MarketOverview {
  total_portfolio_value: number;
  daily_pnl: number;
  daily_pnl_percentage: number;
  active_positions: number;
  available_balance: number;
  total_volume_24h: number;
  arbitrage_opportunities: number;
}

const MasterControllerCenter: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [marketOverview, setMarketOverview] = useState<MarketOverview | null>(null);
  const [selectedMode, setSelectedMode] = useState('balanced');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [performanceData, setPerformanceData] = useState<any[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isInitialized, setIsInitialized] = useState(false);
  
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchSystemStatus();
    fetchMarketOverview();
    
    // Set up real-time updates every 5 seconds
    intervalRef.current = setInterval(() => {
      fetchSystemStatus();
      fetchMarketOverview();
    }, 5000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const response = await apiClient.get('/trading/status');
      if (response.data.success) {
        setSystemStatus(response.data.data);
        setLastUpdate(new Date());
        
        // Sync selectedMode with backend current_mode on first load
        if (!isInitialized && response.data.data.current_mode) {
          setSelectedMode(response.data.data.current_mode);
          setIsInitialized(true);
        }
        
        // Update performance chart data
        if (response.data.data.performance_metrics) {
          setPerformanceData(prev => [
            ...prev.slice(-23), // Keep last 24 data points
            {
              time: new Date().toLocaleTimeString(),
              profit: response.data.data.performance_metrics.total_profit_usd,
              trades: response.data.data.performance_metrics.trades_executed,
              successRate: response.data.data.performance_metrics.success_rate
            }
          ]);
        }
      }
    } catch (err: any) {
      console.error('Failed to fetch system status:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to fetch system status';
      setError(`API Error: ${errorMsg} (${err.response?.status || 'Network Error'})`);
    }
  };

  const fetchMarketOverview = async () => {
    try {
      const response = await apiClient.get('/trading/market-overview');
      if (response.data.success) {
        setMarketOverview(response.data.data);
      }
    } catch (err: any) {
      console.error('Failed to fetch market overview:', err);
    }
  };

  const handleToggleAutonomous = async () => {
    try {
      setIsLoading(true);
      const endpoint = systemStatus?.autonomous_enabled ? '/trading/autonomous/stop' : '/trading/autonomous/start';
      
      let payload = {};
      if (!systemStatus?.autonomous_enabled && systemStatus?.current_mode) {
        // When starting, use the backend's current mode
        payload = { mode: systemStatus.current_mode };
      }
      
      const response = await apiClient.post(endpoint, payload);
      
      if (response.data.success) {
        await fetchSystemStatus();
      }
    } catch (err: any) {
      setError('Failed to toggle autonomous mode');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleSimulation = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.post('/trading/simulation/toggle');
      if (response.data.success) {
        await fetchSystemStatus();
      }
    } catch (err: any) {
      setError('Failed to toggle simulation mode');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmergencyStop = async () => {
    const confirmed = window.confirm(
      'EMERGENCY STOP ALL TRADING\n\n' +
      'This will immediately halt all trading activities, cancel pending orders, and stop all autonomous operations.\n\n' +
      'Are you absolutely sure you want to proceed?'
    );
    
    if (!confirmed) return;

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

  const handleModeChange = async (newMode: string) => {
    try {
      setIsLoading(true);
      setSelectedMode(newMode);
      
      // If autonomous is active, restart with new mode
      if (systemStatus?.autonomous_enabled) {
        await apiClient.post('/trading/autonomous/start', {
          mode: newMode
        });
        await fetchSystemStatus();
      }
    } catch (err: any) {
      setError('Failed to change trading mode');
    } finally {
      setIsLoading(false);
    }
  };

  const getEmergencyLevelColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'normal': return 'text-green-500 bg-green-500/10';
      case 'warning': return 'text-yellow-500 bg-yellow-500/10';
      case 'critical': return 'text-orange-500 bg-orange-500/10';
      case 'emergency': return 'text-red-500 bg-red-500/10';
      default: return 'text-gray-500 bg-gray-500/10';
    }
  };

  if (!systemStatus || !marketOverview) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Loading Master Controller...</p>
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
            <Crown className="h-8 w-8 text-yellow-500" />
            Master Controller Command Center
          </h1>
          <p className="text-muted-foreground">
            $100M Autonomous Hedge Fund Brain - 5-Phase Execution Flow
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-2">
            <Clock className="h-4 w-4" />
            Last updated: {lastUpdate.toLocaleTimeString()}
          </Badge>
          <Button
            variant="outline"
            onClick={() => {
              fetchSystemStatus();
              fetchMarketOverview();
            }}
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

      {/* System Status Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className={`border-l-4 ${systemStatus.is_active ? 'border-l-green-500 bg-green-500/5' : 'border-l-red-500 bg-red-500/5'}`}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Status</CardTitle>
              <Power className={`h-4 w-4 ${systemStatus.is_active ? 'text-green-500' : 'text-red-500'}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {systemStatus.is_active ? 'ACTIVE' : 'INACTIVE'}
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Badge className={getEmergencyLevelColor(systemStatus.emergency_level)}>
                  {systemStatus.emergency_level?.toUpperCase() || 'NORMAL'}
                </Badge>
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
              <CardTitle className="text-sm font-medium">Total Portfolio</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(marketOverview.total_portfolio_value)}
              </div>
              <div className="flex items-center text-sm">
                {marketOverview.daily_pnl >= 0 ? (
                  <ArrowUpRight className="h-4 w-4 text-green-500 mr-1" />
                ) : (
                  <ArrowDownRight className="h-4 w-4 text-red-500 mr-1" />
                )}
                <span className={marketOverview.daily_pnl >= 0 ? 'text-green-500' : 'text-red-500'}>
                  {formatCurrency(marketOverview.daily_pnl)} ({formatPercentage(marketOverview.daily_pnl_percentage)})
                </span>
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
              <div className="text-sm text-muted-foreground">
                {systemStatus.performance_metrics.trades_executed} trades executed
              </div>
              <Progress 
                value={systemStatus.performance_metrics.success_rate} 
                className="mt-2 h-2" 
              />
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
              <CardTitle className="text-sm font-medium">Active Cycles</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {systemStatus.active_cycles?.length || 0}
              </div>
              <div className="text-sm text-muted-foreground">
                {systemStatus.performance_metrics.cycles_executed} total executed
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Main Control Interface */}
      <Tabs defaultValue="control" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="control">Control Panel</TabsTrigger>
          <TabsTrigger value="cycles">Trading Cycles</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="modes">Trading Modes</TabsTrigger>
        </TabsList>

        {/* Control Panel Tab */}
        <TabsContent value="control" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* System Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  System Controls
                </CardTitle>
                <CardDescription>Master controller system operations</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="autonomous-enabled-switch" className="font-medium">Autonomous Mode</Label>
                    <p className="text-sm text-muted-foreground">
                      Enable AI-driven autonomous trading
                    </p>
                  </div>
                  <Switch
                    id="autonomous-enabled-switch"
                    checked={systemStatus.autonomous_enabled}
                    onCheckedChange={handleToggleAutonomous}
                    disabled={isLoading}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="simulation-mode-switch" className="font-medium">Simulation Mode</Label>
                    <p className="text-sm text-muted-foreground">
                      Run in simulation without real trades
                    </p>
                  </div>
                  <Switch
                    id="simulation-mode-switch"
                    checked={systemStatus.simulation_mode}
                    onCheckedChange={handleToggleSimulation}
                    disabled={isLoading}
                  />
                </div>

                <div className="pt-4 border-t">
                  <Button
                    variant="destructive"
                    onClick={handleEmergencyStop}
                    disabled={isLoading}
                    className="w-full gap-2"
                  >
                    <Square className="h-4 w-4" />
                    EMERGENCY STOP ALL
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Performance Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Real-time Performance
                </CardTitle>
                <CardDescription>Live profit and success rate tracking</CardDescription>
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
                        stroke="#22c55e"
                        fill="url(#profitGradient)"
                        strokeWidth={2}
                      />
                      <defs>
                        <linearGradient id="profitGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Trading Cycles Tab */}
        <TabsContent value="cycles" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            {TRADING_CYCLES.map((cycle) => {
              const activeCycle = systemStatus.active_cycles?.find(ac => ac.cycle_type === cycle.id);
              const isActive = !!activeCycle;
              
              return (
                <motion.div
                  key={cycle.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <Card className={`${isActive ? 'ring-2 ring-green-500/50 bg-green-500/5' : ''}`}>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <div className="flex items-center gap-3">
                        <cycle.icon className={`h-6 w-6 ${cycle.color}`} />
                        <div>
                          <CardTitle className="text-base">{cycle.name}</CardTitle>
                          <CardDescription className="text-xs">
                            {cycle.description}
                          </CardDescription>
                        </div>
                      </div>
                      <Badge variant={isActive ? "default" : "secondary"}>
                        {isActive ? 'ACTIVE' : 'IDLE'}
                      </Badge>
                    </CardHeader>
                    <CardContent>
                      {activeCycle ? (
                        <div className="space-y-2">
                          <div className="flex justify-between text-sm">
                            <span>Duration:</span>
                            <span className="font-mono">{activeCycle.duration}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span>Profit:</span>
                            <span className={`font-mono ${activeCycle.profit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              {formatCurrency(activeCycle.profit)}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span>Trades:</span>
                            <span className="font-mono">{activeCycle.trades}</span>
                          </div>
                        </div>
                      ) : (
                        <div className="text-sm text-muted-foreground">
                          Cycle inactive - waiting for optimal conditions
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Profit</p>
                    <p className="text-2xl font-bold text-green-500">
                      {formatCurrency(systemStatus.performance_metrics.total_profit_usd)}
                    </p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>

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
                    <p className="text-sm font-medium text-muted-foreground">Loss Streak</p>
                    <p className="text-2xl font-bold text-red-500">
                      {systemStatus.performance_metrics.consecutive_losses}
                    </p>
                  </div>
                  <TrendingDown className="h-8 w-8 text-red-500" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Trading Modes Tab */}
        <TabsContent value="modes" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            {TRADING_MODES.map((mode) => {
              const isSelected = selectedMode === mode.id;
              const isCurrentMode = systemStatus.current_mode === mode.id;
              
              return (
                <motion.div
                  key={mode.id}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  <Card 
                    className={`cursor-pointer transition-all ${
                      isCurrentMode ? 'ring-2 ring-green-500/50 bg-green-500/5' : 
                      isSelected ? 'ring-2 ring-blue-500/50 bg-blue-500/5' : 
                      'hover:bg-muted/50'
                    }`}
                    onClick={() => handleModeChange(mode.id)}
                  >
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${mode.color}`}>
                          <mode.icon className="h-6 w-6" />
                        </div>
                        <div>
                          <CardTitle className="text-base">{mode.name}</CardTitle>
                          <CardDescription className="text-xs">
                            {mode.description}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex flex-col gap-1">
                        {isCurrentMode && <Badge variant="default">ACTIVE</Badge>}
                        {isSelected && !isCurrentMode && <Badge variant="secondary">SELECTED</Badge>}
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Daily Target:</span>
                          <span className="ml-2 font-mono text-green-500">
                            {formatPercentage(mode.dailyTarget)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Max Drawdown:</span>
                          <span className="ml-2 font-mono text-red-500">
                            {formatPercentage(mode.maxDrawdown)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Min Win Rate:</span>
                          <span className="ml-2 font-mono text-blue-500">
                            {formatPercentage(mode.minWinRate)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Max Leverage:</span>
                          <span className="ml-2 font-mono">
                            {mode.maxLeverage}x
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MasterControllerCenter;