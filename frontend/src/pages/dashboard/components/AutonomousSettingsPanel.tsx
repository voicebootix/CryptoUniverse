import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Bot,
  Shield,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  Settings,
  Zap,
  Activity,
  Target,
  Clock,
  Info,
  Save,
  RefreshCw
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

interface AutonomousSettings {
  enabled: boolean;
  maxPositionSize: number;
  maxDailyLoss: number;
  targetProfit: number;
  riskLevel: 'conservative' | 'moderate' | 'aggressive';
  tradingPairs: string[];
  strategies: string[];
  stopLossPercent: number;
  takeProfitPercent: number;
  maxConcurrentTrades: number;
  tradeFrequency: 'low' | 'medium' | 'high';
  rebalanceEnabled: boolean;
  rebalanceThreshold: number;
}

interface AutonomousSettingsPanelProps {
  isPaperMode: boolean;
  isEnabled: boolean;
  onToggle: () => void;
}

const AutonomousSettingsPanel: React.FC<AutonomousSettingsPanelProps> = ({
  isPaperMode,
  isEnabled,
  onToggle
}) => {
  const { toast } = useToast();
  const [settings, setSettings] = useState<AutonomousSettings>({
    enabled: isEnabled,
    maxPositionSize: 1000,
    maxDailyLoss: 100,
    targetProfit: 50,
    riskLevel: 'moderate',
    tradingPairs: ['BTC/USDT', 'ETH/USDT'],
    strategies: ['momentum', 'mean_reversion'],
    stopLossPercent: 5,
    takeProfitPercent: 10,
    maxConcurrentTrades: 3,
    tradeFrequency: 'medium',
    rebalanceEnabled: true,
    rebalanceThreshold: 10
  });

  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    fetchSettings();
    if (isEnabled) {
      fetchStats();
    }
  }, [isEnabled]);

  const fetchSettings = async () => {
    try {
      const response = await apiClient.get('/api/v1/autonomous/settings');
      if (response.data.success) {
        setSettings(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch autonomous settings:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const endpoint = isPaperMode 
        ? '/api/v1/paper-trading/autonomous-stats'
        : '/api/v1/autonomous/stats';
      
      const response = await apiClient.get(endpoint);
      if (response.data.success) {
        setStats(response.data.data);
      }
    } catch (error) {
      console.error('Failed to fetch autonomous stats:', error);
    }
  };

  const saveSettings = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/v1/autonomous/settings', {
        ...settings,
        paperMode: isPaperMode
      });

      if (response.data.success) {
        toast({
          title: "Settings Saved",
          description: "Your autonomous trading settings have been updated",
          duration: 3000
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save settings. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const resetToDefaults = () => {
    setSettings({
      enabled: false,
      maxPositionSize: 1000,
      maxDailyLoss: 100,
      targetProfit: 50,
      riskLevel: 'moderate',
      tradingPairs: ['BTC/USDT', 'ETH/USDT'],
      strategies: ['momentum', 'mean_reversion'],
      stopLossPercent: 5,
      takeProfitPercent: 10,
      maxConcurrentTrades: 3,
      tradeFrequency: 'medium',
      rebalanceEnabled: true,
      rebalanceThreshold: 10
    });

    toast({
      title: "Settings Reset",
      description: "Settings have been reset to defaults",
      duration: 3000
    });
  };

  const riskProfiles = {
    conservative: {
      color: 'text-green-500',
      description: 'Lower risk, steady returns',
      icon: <Shield className="h-4 w-4" />
    },
    moderate: {
      color: 'text-yellow-500',
      description: 'Balanced risk and reward',
      icon: <Activity className="h-4 w-4" />
    },
    aggressive: {
      color: 'text-red-500',
      description: 'Higher risk, higher potential',
      icon: <Zap className="h-4 w-4" />
    }
  };

  return (
    <div className="space-y-4 h-full overflow-y-auto">
      {/* Status Card */}
      <Card className={isEnabled ? 'border-green-500' : ''}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bot className={`h-6 w-6 ${isEnabled ? 'text-green-500 animate-pulse' : ''}`} />
              <div>
                <CardTitle>Autonomous Trading</CardTitle>
                <CardDescription>
                  {isEnabled ? 'AI is actively trading' : 'AI trading is paused'}
                </CardDescription>
              </div>
            </div>
            <Button
              variant={isEnabled ? 'destructive' : 'default'}
              onClick={onToggle}
            >
              {isEnabled ? 'Stop' : 'Start'} Trading
            </Button>
          </div>
        </CardHeader>

        {stats && isEnabled && (
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-green-500">
                  {formatCurrency(stats.totalProfit)}
                </p>
                <p className="text-xs text-muted-foreground">Total Profit</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">
                  {stats.totalTrades}
                </p>
                <p className="text-xs text-muted-foreground">Trades Made</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold">
                  {formatPercentage(stats.winRate)}
                </p>
                <p className="text-xs text-muted-foreground">Win Rate</p>
              </div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* Risk Profile Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Risk Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(riskProfiles).map(([level, profile]) => (
              <Button
                key={level}
                variant={settings.riskLevel === level ? 'default' : 'outline'}
                onClick={() => setSettings({ ...settings, riskLevel: level as any })}
                className="flex flex-col h-auto py-3"
              >
                <div className={`flex items-center gap-2 ${profile.color}`}>
                  {profile.icon}
                  <span className="capitalize">{level}</span>
                </div>
                <span className="text-xs mt-1 text-muted-foreground">
                  {profile.description}
                </span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Position & Loss Limits */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Position & Risk Limits
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Max Position Size</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={settings.maxPositionSize}
                onChange={(e) => setSettings({
                  ...settings,
                  maxPositionSize: parseFloat(e.target.value)
                })}
                className="flex-1"
              />
              <span className="text-sm text-muted-foreground">USDT</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Max Daily Loss</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={settings.maxDailyLoss}
                onChange={(e) => setSettings({
                  ...settings,
                  maxDailyLoss: parseFloat(e.target.value)
                })}
                className="flex-1"
              />
              <span className="text-sm text-muted-foreground">USDT</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Target Daily Profit</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={settings.targetProfit}
                onChange={(e) => setSettings({
                  ...settings,
                  targetProfit: parseFloat(e.target.value)
                })}
                className="flex-1"
              />
              <span className="text-sm text-muted-foreground">USDT</span>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Max Concurrent Trades</Label>
            <Select 
              value={settings.maxConcurrentTrades.toString()}
              onValueChange={(v) => setSettings({
                ...settings,
                maxConcurrentTrades: parseInt(v)
              })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 5, 10].map(num => (
                  <SelectItem key={num} value={num.toString()}>
                    {num} {num === 1 ? 'trade' : 'trades'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Risk Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Risk Management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Stop Loss</Label>
              <span className="text-sm font-medium">{settings.stopLossPercent}%</span>
            </div>
            <Slider
              value={[settings.stopLossPercent]}
              onValueChange={([v]) => setSettings({ ...settings, stopLossPercent: v })}
              min={1}
              max={20}
              step={0.5}
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Take Profit</Label>
              <span className="text-sm font-medium">{settings.takeProfitPercent}%</span>
            </div>
            <Slider
              value={[settings.takeProfitPercent]}
              onValueChange={([v]) => setSettings({ ...settings, takeProfitPercent: v })}
              min={1}
              max={50}
              step={1}
            />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              <Label htmlFor="rebalance">Auto-Rebalance</Label>
            </div>
            <Switch
              id="rebalance"
              checked={settings.rebalanceEnabled}
              onCheckedChange={(checked) => setSettings({
                ...settings,
                rebalanceEnabled: checked
              })}
            />
          </div>

          {settings.rebalanceEnabled && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm">Rebalance Threshold</Label>
                <span className="text-sm font-medium">{settings.rebalanceThreshold}%</span>
              </div>
              <Slider
                value={[settings.rebalanceThreshold]}
                onValueChange={([v]) => setSettings({ ...settings, rebalanceThreshold: v })}
                min={5}
                max={30}
                step={1}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Trade Frequency */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Trading Frequency
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={settings.tradeFrequency}
            onValueChange={(v) => setSettings({
              ...settings,
              tradeFrequency: v as any
            })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="low">
                <div>
                  <div className="font-medium">Low Frequency</div>
                  <div className="text-xs text-muted-foreground">1-3 trades per day</div>
                </div>
              </SelectItem>
              <SelectItem value="medium">
                <div>
                  <div className="font-medium">Medium Frequency</div>
                  <div className="text-xs text-muted-foreground">4-10 trades per day</div>
                </div>
              </SelectItem>
              <SelectItem value="high">
                <div>
                  <div className="font-medium">High Frequency</div>
                  <div className="text-xs text-muted-foreground">10+ trades per day</div>
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Paper Mode Notice */}
      {isPaperMode && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            These settings apply to paper trading. Test your configuration risk-free!
          </AlertDescription>
        </Alert>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button
          className="flex-1"
          onClick={saveSettings}
          disabled={isLoading}
        >
          <Save className="h-4 w-4 mr-2" />
          Save Settings
        </Button>
        <Button
          variant="outline"
          onClick={resetToDefaults}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Reset
        </Button>
      </div>
    </div>
  );
};

export default AutonomousSettingsPanel;