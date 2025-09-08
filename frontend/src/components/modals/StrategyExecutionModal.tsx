import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Play,
  Pause,
  Settings,
  DollarSign,
  TrendingUp,
  Shield,
  Clock,
  Target,
  AlertTriangle,
  Info,
  CheckCircle,
  Zap,
} from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { formatCurrency, formatPercentage } from '@/lib/utils';

interface StrategyExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  strategy: any;
  executing: boolean;
}

const StrategyExecutionModal: React.FC<StrategyExecutionModalProps> = ({
  isOpen,
  onClose,
  strategy,
  executing
}) => {
  const [allocation, setAllocation] = useState(1000);
  const [leverage, setLeverage] = useState(1);
  const [paperMode, setPaperMode] = useState(true);
  const [stopLoss, setStopLoss] = useState(5);
  const [takeProfit, setTakeProfit] = useState(15);
  const [executionPhase, setExecutionPhase] = useState(0);

  const phases = [
    { name: 'Analysis', icon: TrendingUp, status: 'pending' },
    { name: 'Consensus', icon: Target, status: 'pending' },
    { name: 'Validation', icon: Shield, status: 'pending' },
    { name: 'Execution', icon: Play, status: 'pending' },
    { name: 'Monitoring', icon: Clock, status: 'pending' }
  ];

  const handleExecute = async () => {
    if (!strategy) return;
    
    // Simulate 5-phase execution
    for (let i = 0; i < phases.length; i++) {
      setExecutionPhase(i);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    // Complete execution
    setExecutionPhase(5);
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'Low': return 'text-green-500';
      case 'Medium': return 'text-yellow-500';
      case 'High': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const expectedReturn = (allocation * (parseFloat(strategy?.avgReturn?.split('-')[1] || '0') / 100)) * leverage;
  const maxLoss = allocation * (stopLoss / 100) * leverage;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className={`p-2 rounded ${strategy?.color}`}>
              <strategy?.icon className="h-5 w-5" />
            </div>
            Execute Strategy: {strategy?.name}
          </DialogTitle>
          <DialogDescription>
            Configure and execute your trading strategy with AI-powered 5-phase validation
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="configure" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="configure">Configure</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
            <TabsTrigger value="execution">Execute</TabsTrigger>
          </TabsList>

          <TabsContent value="configure" className="space-y-6">
            {/* Strategy Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  Strategy Overview
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-muted/50 rounded-lg">
                    <div className="text-2xl font-bold text-green-500">{strategy?.winRate}%</div>
                    <div className="text-sm text-muted-foreground">Win Rate</div>
                  </div>
                  <div className="text-center p-4 bg-muted/50 rounded-lg">
                    <div className="text-2xl font-bold">{strategy?.avgReturn}</div>
                    <div className="text-sm text-muted-foreground">Avg Return</div>
                  </div>
                  <div className="text-center p-4 bg-muted/50 rounded-lg">
                    <div className={`text-2xl font-bold ${getRiskColor(strategy?.riskLevel)}`}>
                      {strategy?.riskLevel}
                    </div>
                    <div className="text-sm text-muted-foreground">Risk Level</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Configuration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Position Configuration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="allocation">Capital Allocation</Label>
                    <Input
                      id="allocation"
                      type="number"
                      value={allocation}
                      onChange={(e) => setAllocation(Number(e.target.value))}
                      min={strategy?.minCapital}
                    />
                    <div className="text-xs text-muted-foreground">
                      Minimum: {formatCurrency(strategy?.minCapital)}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Leverage: {leverage}x</Label>
                    <Slider
                      value={[leverage]}
                      onValueChange={(value) => setLeverage(value[0])}
                      max={parseFloat(strategy?.maxLeverage?.replace('x', '') || '1')}
                      min={1}
                      step={0.5}
                      className="w-full"
                    />
                    <div className="text-xs text-muted-foreground">
                      Max: {strategy?.maxLeverage}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="paper-mode"
                      checked={paperMode}
                      onCheckedChange={setPaperMode}
                    />
                    <Label htmlFor="paper-mode">Paper Trading Mode</Label>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Risk Management</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Stop Loss: {stopLoss}%</Label>
                    <Slider
                      value={[stopLoss]}
                      onValueChange={(value) => setStopLoss(value[0])}
                      max={20}
                      min={1}
                      step={0.5}
                      className="w-full"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Take Profit: {takeProfit}%</Label>
                    <Slider
                      value={[takeProfit]}
                      onValueChange={(value) => setTakeProfit(value[0])}
                      max={50}
                      min={5}
                      step={1}
                      className="w-full"
                    />
                  </div>

                  <div className="pt-4 space-y-2 border-t">
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Expected Return:</span>
                      <span className="text-sm font-medium text-green-500">
                        +{formatCurrency(expectedReturn)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-muted-foreground">Max Loss:</span>
                      <span className="text-sm font-medium text-red-500">
                        -{formatCurrency(maxLoss)}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="analysis" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Performance Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-muted-foreground">Active Users</div>
                      <div className="font-medium">{strategy?.activeUsers?.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Timeframe</div>
                      <div className="font-medium">{strategy?.timeframe}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Min Capital</div>
                      <div className="font-medium">{formatCurrency(strategy?.minCapital)}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">Max Leverage</div>
                      <div className="font-medium">{strategy?.maxLeverage}</div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="font-semibold">Key Features:</h4>
                    <div className="flex flex-wrap gap-2">
                      {strategy?.features?.map((feature: string, index: number) => (
                        <Badge key={index} variant="secondary">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="execution" className="space-y-6">
            {/* 5-Phase Progress */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  5-Phase AI Execution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {phases.map((phase, index) => (
                    <div key={phase.name} className="flex items-center gap-3">
                      <div className={`p-2 rounded-full border-2 ${
                        index < executionPhase ? 'bg-green-500 border-green-500' :
                        index === executionPhase ? 'bg-primary border-primary animate-pulse' :
                        'bg-muted border-muted'
                      }`}>
                        <phase.icon className={`h-4 w-4 ${
                          index <= executionPhase ? 'text-white' : 'text-muted-foreground'
                        }`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{phase.name}</span>
                          {index < executionPhase && (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          )}
                        </div>
                        <Progress 
                          value={index < executionPhase ? 100 : index === executionPhase ? 60 : 0} 
                          className="h-2 mt-1" 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Execution Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Execution Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Allocation:</span>
                      <span className="font-medium">{formatCurrency(allocation)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Leverage:</span>
                      <span className="font-medium">{leverage}x</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Mode:</span>
                      <Badge variant={paperMode ? 'secondary' : 'destructive'}>
                        {paperMode ? 'Paper' : 'Live'}
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Stop Loss:</span>
                      <span className="font-medium text-red-500">{stopLoss}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Take Profit:</span>
                      <span className="font-medium text-green-500">{takeProfit}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Expected Return:</span>
                      <span className="font-medium text-green-500">
                        +{formatCurrency(expectedReturn)}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <div className="flex justify-between pt-4 border-t">
          <Button variant="outline" onClick={onClose} disabled={executing}>
            Cancel
          </Button>
          <Button onClick={handleExecute} disabled={executing || executionPhase > 0}>
            {executing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Executing...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Execute Strategy
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default StrategyExecutionModal;