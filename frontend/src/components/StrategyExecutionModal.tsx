import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  X,
  Play,
  Settings,
  AlertTriangle,
  CheckCircle,
  Target,
  DollarSign,
  TrendingUp,
  Shield,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { useStrategies, StrategyExecuteRequest, AvailableStrategy } from '@/hooks/useStrategies';

interface StrategyExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategy: AvailableStrategy & { id: string };
  executing: boolean;
}

const StrategyExecutionModal: React.FC<StrategyExecutionModalProps> = ({
  isOpen,
  onClose,
  strategy,
  executing
}) => {
  const { actions } = useStrategies();
  const [formData, setFormData] = useState({
    symbol: 'BTC/USDT',
    simulation_mode: true,
    position_size: 1000,
    leverage: 1,
    stop_loss: 5.0,
    take_profit: 10.0,
    timeframe: '1h',
    risk_level: 'medium'
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleExecute = async () => {
    try {
      // Validate form
      const newErrors: Record<string, string> = {};
      
      if (!formData.symbol.trim()) {
        newErrors.symbol = 'Symbol is required';
      }
      
      if (formData.position_size <= 0) {
        newErrors.position_size = 'Position size must be positive';
      }
      
      setErrors(newErrors);
      if (Object.keys(newErrors).length > 0) return;

      // Prepare execution request
      const executeRequest: StrategyExecuteRequest = {
        function: strategy.id,
        symbol: formData.symbol,
        simulation_mode: formData.simulation_mode,
        parameters: {
          position_size_usd: formData.position_size,
          leverage: formData.leverage,
          stop_loss_pct: formData.stop_loss,
          take_profit_pct: formData.take_profit,
          timeframe: formData.timeframe,
          risk_level: formData.risk_level,
          // Add strategy-specific parameters
          ...getStrategySpecificParams()
        }
      };

      // Execute strategy
      await actions.executeStrategy(executeRequest);
      
      // Close modal on success
      onClose();
      
    } catch (error) {
      console.error('Strategy execution failed:', error);
    }
  };

  const getStrategySpecificParams = () => {
    // Return strategy-specific parameters based on strategy type
    const baseParams: Record<string, any> = {};
    
    switch (strategy.category) {
      case 'derivatives':
        if (strategy.id.includes('futures')) {
          baseParams.contract_type = 'perpetual';
          baseParams.margin_type = 'isolated';
        }
        if (strategy.id.includes('options')) {
          baseParams.strike_offset = 0.05;
          baseParams.expiry_days = 30;
        }
        break;
        
      case 'spot':
        baseParams.order_type = 'market';
        baseParams.slippage_tolerance = 0.1;
        break;
        
      case 'algorithmic':
        if (strategy.id.includes('pairs')) {
          baseParams.correlation_threshold = 0.8;
          baseParams.spread_threshold = 2.0;
        }
        if (strategy.id.includes('scalping')) {
          baseParams.tick_size = 0.01;
          baseParams.hold_time_seconds = 60;
        }
        break;
    }
    
    return baseParams;
  };

  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'low': return 'text-green-500';
      case 'medium': return 'text-yellow-500';
      case 'high': return 'text-orange-500';
      case 'very high': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <Card className="p-6 bg-white">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-3">
                <Target className="w-6 h-6 text-blue-500" />
                Execute {strategy.name}
              </h2>
              <p className="text-gray-600 mt-1">{strategy.description}</p>
              <div className="flex items-center gap-4 mt-2">
                <Badge variant="outline" className="capitalize">
                  {strategy.category}
                </Badge>
                <Badge variant="outline" className={getRiskColor(strategy.risk_level)}>
                  {strategy.risk_level} Risk
                </Badge>
                <Badge variant="outline">
                  Min: ${strategy.min_capital.toLocaleString()}
                </Badge>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="hover:bg-gray-100"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>

          {/* Strategy Info */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Card className="p-4 bg-blue-50 border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-blue-600" />
                <span className="font-medium text-blue-900">Expected Return</span>
              </div>
              <p className="text-sm text-blue-700">
                Based on historical performance and market conditions
              </p>
            </Card>
            
            <Card className="p-4 bg-amber-50 border-amber-200">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4 text-amber-600" />
                <span className="font-medium text-amber-900">Risk Management</span>
              </div>
              <p className="text-sm text-amber-700">
                Automated stop-loss and position sizing
              </p>
            </Card>
            
            <Card className="p-4 bg-green-50 border-green-200">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-green-600" />
                <span className="font-medium text-green-900">Execution Speed</span>
              </div>
              <p className="text-sm text-green-700">
                Sub-second execution with real exchange APIs
              </p>
            </Card>
          </div>

          {/* Configuration Form */}
          <div className="space-y-6">
            {/* Basic Configuration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="symbol">Trading Symbol</Label>
                  <Select value={formData.symbol} onValueChange={(value) => setFormData(prev => ({ ...prev, symbol: value }))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select symbol" />
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
                  {errors.symbol && (
                    <p className="text-sm text-red-600 mt-1">{errors.symbol}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="position_size">Position Size (USD)</Label>
                  <Input
                    id="position_size"
                    type="number"
                    min="100"
                    max="50000"
                    step="100"
                    value={formData.position_size}
                    onChange={(e) => setFormData(prev => ({ ...prev, position_size: parseFloat(e.target.value) || 0 }))}
                    className={errors.position_size ? 'border-red-500' : ''}
                  />
                  {errors.position_size && (
                    <p className="text-sm text-red-600 mt-1">{errors.position_size}</p>
                  )}
                </div>

                {strategy.category === 'derivatives' && (
                  <div>
                    <Label htmlFor="leverage">Leverage</Label>
                    <div className="space-y-2">
                      <Slider
                        value={[formData.leverage]}
                        onValueChange={([value]) => setFormData(prev => ({ ...prev, leverage: value }))}
                        max={20}
                        min={1}
                        step={1}
                        className="w-full"
                      />
                      <div className="flex justify-between text-sm text-gray-500">
                        <span>1x</span>
                        <span className="font-medium">{formData.leverage}x</span>
                        <span>20x</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <Label htmlFor="stop_loss">Stop Loss (%)</Label>
                  <Input
                    id="stop_loss"
                    type="number"
                    min="0.5"
                    max="20"
                    step="0.5"
                    value={formData.stop_loss}
                    onChange={(e) => setFormData(prev => ({ ...prev, stop_loss: parseFloat(e.target.value) || 5 }))}
                  />
                </div>

                <div>
                  <Label htmlFor="take_profit">Take Profit (%)</Label>
                  <Input
                    id="take_profit"
                    type="number"
                    min="1"
                    max="50"
                    step="1"
                    value={formData.take_profit}
                    onChange={(e) => setFormData(prev => ({ ...prev, take_profit: parseFloat(e.target.value) || 10 }))}
                  />
                </div>

                <div>
                  <Label htmlFor="timeframe">Timeframe</Label>
                  <Select value={formData.timeframe} onValueChange={(value) => setFormData(prev => ({ ...prev, timeframe: value }))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select timeframe" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1m">1 Minute</SelectItem>
                      <SelectItem value="5m">5 Minutes</SelectItem>
                      <SelectItem value="15m">15 Minutes</SelectItem>
                      <SelectItem value="1h">1 Hour</SelectItem>
                      <SelectItem value="4h">4 Hours</SelectItem>
                      <SelectItem value="1d">1 Day</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            {/* Simulation Mode Toggle */}
            <div className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="simulation">Simulation Mode</Label>
                  <p className="text-sm text-gray-600">
                    {formData.simulation_mode 
                      ? "Test strategy with virtual funds (recommended)" 
                      : "Execute with real funds and exchange APIs"
                    }
                  </p>
                </div>
                <Switch
                  id="simulation"
                  checked={formData.simulation_mode}
                  onCheckedChange={(checked) => setFormData(prev => ({ ...prev, simulation_mode: checked }))}
                />
              </div>
              
              {!formData.simulation_mode && (
                <div className="mt-3 p-3 bg-amber-100 border border-amber-300 rounded">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-amber-800">Live Trading Mode</p>
                      <p className="text-sm text-amber-700">
                        This will execute real trades using your connected exchange accounts. 
                        Credits will be deducted for each execution.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Risk Summary */}
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium mb-3">Execution Summary</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Symbol</span>
                  <p className="font-medium">{formData.symbol}</p>
                </div>
                <div>
                  <span className="text-gray-500">Position Size</span>
                  <p className="font-medium">${formData.position_size.toLocaleString()}</p>
                </div>
                <div>
                  <span className="text-gray-500">Max Risk</span>
                  <p className="font-medium text-red-500">
                    ${(formData.position_size * formData.stop_loss / 100).toFixed(2)}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500">Mode</span>
                  <p className={`font-medium ${formData.simulation_mode ? 'text-blue-500' : 'text-green-500'}`}>
                    {formData.simulation_mode ? 'Simulation' : 'Live Trading'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-6 border-t">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button 
              onClick={handleExecute}
              disabled={executing}
              className="px-8 bg-gradient-to-r from-blue-600 to-purple-600 text-white"
            >
              {executing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Execute Strategy
                </>
              )}
            </Button>
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default StrategyExecutionModal;