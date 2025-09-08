import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot,
  Brain,
  Zap,
  Target,
  TrendingUp,
  Shield,
  Clock,
  DollarSign,
  Activity,
  Settings,
  Play,
  Pause,
  BarChart3,
  AlertTriangle,
  CheckCircle,
  Rocket,
  Crown,
  Flame,
  Timer,
  Cpu,
  Eye,
  Sparkles,
  LineChart
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { useUser } from '@/store/authStore';
import { formatCurrency, formatPercentage } from '@/lib/utils';

interface AIConfig {
  intensity: 'hibernation' | 'conservative' | 'active' | 'aggressive' | 'hyperactive';
  targetDailyReturn: number;
  maxDailyLoss: number;
  riskTolerance: number;
  autoCompound: boolean;
  emergencyStopLoss: number;
  preferredStrategies: string[];
  marketRegimes: string[];
}

const defaultConfig: AIConfig = {
  intensity: 'active',
  targetDailyReturn: 5.0,
  maxDailyLoss: 3.0,
  riskTolerance: 70,
  autoCompound: true,
  emergencyStopLoss: 15.0,
  preferredStrategies: ['momentum', 'arbitrage', 'breakout'],
  marketRegimes: ['trending_bull', 'range_bound', 'high_volatility']
};

const intensityConfigs = {
  hibernation: {
    title: 'Hibernation',
    description: 'Ultra-conservative, 0-2 trades/day',
    icon: Clock,
    color: 'bg-gray-500',
    dailyTarget: '0.5-1%',
    tradesPerDay: '0-2',
    riskLevel: 'Minimal',
    estimatedReturn: '15-30% annually'
  },
  conservative: {
    title: 'Conservative',
    description: 'Low risk, steady growth, 3-8 trades/day',
    icon: Shield,
    color: 'bg-blue-500',
    dailyTarget: '1-2%',
    tradesPerDay: '3-8',
    riskLevel: 'Low',
    estimatedReturn: '50-100% annually'
  },
  active: {
    title: 'Active',
    description: 'Balanced approach, 10-25 trades/day',
    icon: Activity,
    color: 'bg-green-500',
    dailyTarget: '2-5%',
    tradesPerDay: '10-25',
    riskLevel: 'Medium',
    estimatedReturn: '100-300% annually'
  },
  aggressive: {
    title: 'Aggressive',
    description: 'High risk/reward, 30-60 trades/day',
    icon: Flame,
    color: 'bg-orange-500',
    dailyTarget: '5-15%',
    tradesPerDay: '30-60',
    riskLevel: 'High',
    estimatedReturn: '300-800% annually'
  },
  hyperactive: {
    title: 'Hyperactive',
    description: 'Maximum aggression, 100+ trades/day',
    icon: Rocket,
    color: 'bg-red-500',
    dailyTarget: '10-25%',
    tradesPerDay: '100+',
    riskLevel: 'Extreme',
    estimatedReturn: '500-2000% annually'
  }
};

const AutonomousAI: React.FC = () => {
  const user = useUser();
  const [config, setConfig] = useState<AIConfig>(defaultConfig);
  const [isActive, setIsActive] = useState(false);
  const [sessionMetrics, setSessionMetrics] = useState({
    tradesExecuted: 0,
    totalPnL: 0,
    currentDrawdown: 0,
    winRate: 0,
    activeStrategies: 3,
    lastTradeAt: null as string | null
  });

  const handleConfigChange = (key: keyof AIConfig, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleIntensityChange = (intensity: AIConfig['intensity']) => {
    const intensityConfig = intensityConfigs[intensity];
    setConfig(prev => ({
      ...prev,
      intensity,
      targetDailyReturn: intensity === 'hibernation' ? 0.5 : 
                        intensity === 'conservative' ? 1.5 :
                        intensity === 'active' ? 3.5 :
                        intensity === 'aggressive' ? 7.5 : 15.0,
      maxDailyLoss: intensity === 'hibernation' ? 1.0 :
                   intensity === 'conservative' ? 2.0 :
                   intensity === 'active' ? 5.0 :
                   intensity === 'aggressive' ? 10.0 : 20.0
    }));
  };

  const startAutonomousTrading = async () => {
    try {
      // API call to start autonomous trading
      setIsActive(true);
      // Real implementation would call ${import.meta.env.VITE_API_URL}/autonomous/start
    } catch (error) {
      console.error('Failed to start autonomous trading:', error);
    }
  };

  const stopAutonomousTrading = async () => {
    try {
      setIsActive(false);
      // Real implementation would call ${import.meta.env.VITE_API_URL}/autonomous/stop
    } catch (error) {
      console.error('Failed to stop autonomous trading:', error);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-8"
    >
      {/* Header */}
      <div className="text-center space-y-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="flex justify-center"
        >
          <div className="relative">
            <Brain className="w-16 h-16 text-blue-500" />
            {isActive && (
              <div className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full animate-pulse" />
            )}
          </div>
        </motion.div>
        
        <div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Autonomous AI Manager
          </h1>
          <p className="text-xl text-muted-foreground mt-2">
            Next-generation AI that trades 24/7 while you sleep
          </p>
          <p className="text-sm text-muted-foreground">
            Real-time event-driven • Multi-strategy execution • Intelligent market adaptation
          </p>
          <p className="text-xs text-muted-foreground/70 mt-3 border-t border-muted/20 pt-2">
            ⚠️ Risk Notice: All investments carry risk of loss. Past performance does not guarantee future results. 
            Consider your financial situation and consult a financial advisor before trading.
          </p>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card className={`border-2 ${isActive ? 'border-green-500 bg-green-50' : 'border-gray-200'}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Status</CardTitle>
            <Bot className={`h-4 w-4 ${isActive ? 'text-green-500' : 'text-gray-500'}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isActive ? 'ACTIVE' : 'SLEEPING'}
            </div>
            <p className="text-xs text-muted-foreground">
              {isActive ? 'Monitoring markets in real-time' : 'Click start to activate'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Today's Performance</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              +{formatPercentage(sessionMetrics.totalPnL)}
            </div>
            <p className="text-xs text-muted-foreground">
              {sessionMetrics.tradesExecuted} trades executed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Trading Intensity</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">
              {config.intensity}
            </div>
            <p className="text-xs text-muted-foreground">
              {intensityConfigs[config.intensity].tradesPerDay} trades/day
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPercentage(sessionMetrics.winRate)}
            </div>
            <p className="text-xs text-muted-foreground">
              {sessionMetrics.activeStrategies} strategies active
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Control Panel */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* AI Configuration */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Cpu className="w-5 h-5" />
                AI Configuration
              </CardTitle>
              <CardDescription>
                Configure your AI's trading personality and risk parameters
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Trading Intensity */}
              <div className="space-y-4">
                <Label className="text-base font-medium">Trading Intensity</Label>
                <div className="grid gap-3">
                  {Object.entries(intensityConfigs).map(([key, intensityConfig]) => {
                    const IconComponent = intensityConfig.icon;
                    return (
                      <motion.div
                        key={key}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                          config.intensity === key 
                            ? 'border-blue-500 bg-blue-50' 
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => handleIntensityChange(key as AIConfig['intensity'])}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`p-2 rounded ${intensityConfig.color} text-white`}>
                              <IconComponent className="w-4 h-4" />
                            </div>
                            <div>
                              <h4 className="font-semibold">{intensityConfig.title}</h4>
                              <p className="text-sm text-muted-foreground">{intensityConfig.description}</p>
                            </div>
                          </div>
                          <div className="text-right text-sm">
                            <div className="font-medium">{intensityConfig.dailyTarget}</div>
                            <div className="text-muted-foreground">{intensityConfig.tradesPerDay}</div>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </div>

              {/* Risk Parameters */}
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-3">
                  <Label>Target Daily Return: {config.targetDailyReturn}%</Label>
                  <Slider
                    value={[config.targetDailyReturn]}
                    onValueChange={([value]) => handleConfigChange('targetDailyReturn', value)}
                    max={25}
                    min={0.5}
                    step={0.5}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>0.5% (Safe)</span>
                    <span>25% (BEAST MODE)</span>
                  </div>
                </div>

                <div className="space-y-3">
                  <Label>Max Daily Loss: {config.maxDailyLoss}%</Label>
                  <Slider
                    value={[config.maxDailyLoss]}
                    onValueChange={([value]) => handleConfigChange('maxDailyLoss', value)}
                    max={20}
                    min={1}
                    step={0.5}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>1% (Conservative)</span>
                    <span>20% (High Risk)</span>
                  </div>
                </div>
              </div>

              {/* Advanced Settings */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Auto-Compound Profits</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically reinvest profits to increase position sizes
                    </p>
                  </div>
                  <Switch
                    checked={config.autoCompound}
                    onCheckedChange={(checked) => handleConfigChange('autoCompound', checked)}
                  />
                </div>

                <div className="space-y-3">
                  <Label>Emergency Stop Loss: {config.emergencyStopLoss}%</Label>
                  <Slider
                    value={[config.emergencyStopLoss]}
                    onValueChange={([value]) => handleConfigChange('emergencyStopLoss', value)}
                    max={50}
                    min={5}
                    step={1}
                    className="w-full"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Control Panel */}
        <div className="space-y-6">
          {/* Main Control */}
          <Card className={`border-2 ${isActive ? 'border-green-500' : 'border-gray-200'}`}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5" />
                AI Control
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center space-y-4">
                <div className={`w-20 h-20 rounded-full mx-auto flex items-center justify-center ${
                  isActive ? 'bg-green-100 border-4 border-green-500' : 'bg-gray-100 border-4 border-gray-300'
                }`}>
                  <Bot className={`w-10 h-10 ${isActive ? 'text-green-500' : 'text-gray-500'}`} />
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold">
                    {isActive ? 'AI ACTIVE' : 'AI SLEEPING'}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {isActive 
                      ? 'Monitoring markets and executing trades'
                      : 'Ready to start autonomous trading'
                    }
                  </p>
                </div>

                <Button
                  size="lg"
                  className={`w-full ${
                    isActive 
                      ? 'bg-red-500 hover:bg-red-600' 
                      : 'bg-gradient-to-r from-green-600 to-blue-600'
                  }`}
                  onClick={isActive ? stopAutonomousTrading : startAutonomousTrading}
                >
                  {isActive ? (
                    <>
                      <Pause className="w-4 h-4 mr-2" />
                      Stop AI
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Start AI
                    </>
                  )}
                </Button>
              </div>

              {isActive && (
                <div className="space-y-3 pt-4 border-t">
                  <div className="flex justify-between text-sm">
                    <span>Session Duration</span>
                    <span className="font-medium">2h 34m</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Next Analysis</span>
                    <span className="font-medium">12 seconds</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Active Strategies</span>
                    <span className="font-medium">{sessionMetrics.activeStrategies}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Real-time Metrics */}
          {isActive && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Real-time Metrics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm">Today's P&L</span>
                    <span className={`font-medium ${sessionMetrics.totalPnL >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {formatCurrency(sessionMetrics.totalPnL)}
                    </span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-sm">Win Rate</span>
                    <span className="font-medium">{formatPercentage(sessionMetrics.winRate)}</span>
                  </div>
                  
                  <div className="flex justify-between">
                    <span className="text-sm">Trades Today</span>
                    <span className="font-medium">{sessionMetrics.tradesExecuted}</span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-sm">Current Drawdown</span>
                    <span className={`font-medium ${sessionMetrics.currentDrawdown > 5 ? 'text-red-500' : 'text-green-500'}`}>
                      {formatPercentage(sessionMetrics.currentDrawdown)}
                    </span>
                  </div>
                </div>

                <div className="pt-3 border-t">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span>Live monitoring 8 exchanges</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Strategy Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            Strategy Selection
          </CardTitle>
          <CardDescription>
            Choose which strategies your AI should use
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[
              { id: 'momentum', name: 'Momentum Trading', description: 'Follow strong trends', risk: 'Medium' },
              { id: 'arbitrage', name: 'Arbitrage', description: 'Price differences across exchanges', risk: 'Low' },
              { id: 'breakout', name: 'Breakout', description: 'Trade breakouts from ranges', risk: 'Medium-High' },
              { id: 'mean_reversion', name: 'Mean Reversion', description: 'Counter-trend trading', risk: 'Medium' },
              { id: 'scalping', name: 'Scalping', description: 'High-frequency micro profits', risk: 'High' },
              { id: 'options', name: 'Options', description: 'Derivatives strategies', risk: 'Very High' }
            ].map((strategy) => (
              <div
                key={strategy.id}
                className={`p-4 border rounded-lg cursor-pointer transition-all ${
                  config.preferredStrategies.includes(strategy.id)
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => {
                  const newStrategies = config.preferredStrategies.includes(strategy.id)
                    ? config.preferredStrategies.filter(s => s !== strategy.id)
                    : [...config.preferredStrategies, strategy.id];
                  handleConfigChange('preferredStrategies', newStrategies);
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium">{strategy.name}</h4>
                  <Badge variant={config.preferredStrategies.includes(strategy.id) ? "default" : "outline"}>
                    {strategy.risk}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{strategy.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Real-time Activity Feed */}
      {isActive && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Live Activity Feed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {/* Real-time activity would be populated here */}
              <div className="flex items-center gap-3 text-sm">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                <span className="text-muted-foreground">12:34:56</span>
                <span>Momentum strategy detected BTC breakout above $95,500</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span className="text-muted-foreground">12:34:52</span>
                <span>Executed BUY 0.05 BTC at $95,487 (+$127 profit target)</span>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <div className="w-2 h-2 bg-yellow-500 rounded-full" />
                <span className="text-muted-foreground">12:34:48</span>
                <span>Arbitrage opportunity detected: 0.3% BTC spread</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
};

export default AutonomousAI;