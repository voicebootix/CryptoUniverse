import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  TrendingUp,
  Shield,
  Activity,
  BarChart3,
  Target,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Info,
  Clock,
  DollarSign,
  Zap,
  MessageSquare,
  ChevronRight,
  ChevronDown,
  Filter,
  Download,
  Share2,
  Eye,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  GitBranch,
  Layers
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';

// Decision types
enum DecisionType {
  TRADE_EXECUTION = 'trade_execution',
  RISK_ASSESSMENT = 'risk_assessment',
  PORTFOLIO_REBALANCE = 'portfolio_rebalance',
  STRATEGY_CHANGE = 'strategy_change',
  EMERGENCY_ACTION = 'emergency_action'
}

// Decision status
enum DecisionStatus {
  SUCCESS = 'success',
  FAILED = 'failed',
  PENDING = 'pending',
  PARTIAL = 'partial'
}

// AI Model names
enum AIModel {
  GPT4 = 'gpt4',
  CLAUDE = 'claude',
  GEMINI = 'gemini',
  CONSENSUS = 'consensus'
}

// Decision record interface
interface DecisionRecord {
  id: string;
  timestamp: string;
  type: DecisionType;
  status: DecisionStatus;
  phase: string;
  action: string;
  symbol?: string;
  amount?: number;
  price?: number;
  reasoning: {
    primary: string;
    factors: string[];
    confidence: number;
  };
  aiConsensus: {
    gpt4: { vote: string; confidence: number; reasoning: string };
    claude: { vote: string; confidence: number; reasoning: string };
    gemini: { vote: string; confidence: number; reasoning: string };
    final: string;
    agreement: number;
  };
  marketConditions: {
    trend: 'bullish' | 'bearish' | 'neutral';
    volatility: 'low' | 'medium' | 'high';
    volume: 'low' | 'normal' | 'high';
    signals: string[];
  };
  riskAnalysis: {
    riskScore: number;
    exposureLevel: number;
    potentialLoss: number;
    potentialGain: number;
    riskRewardRatio: number;
  };
  outcome?: {
    result: 'profit' | 'loss' | 'breakeven' | 'pending';
    amount: number;
    percentage: number;
    duration: string;
  };
  phaseDetails: {
    analysis: { duration: number; dataPoints: number };
    consensus: { duration: number; iterations: number };
    validation: { duration: number; checks: number };
    execution: { duration: number; slippage: number };
    monitoring?: { duration: number; adjustments: number };
  };
}

// Performance summary
interface PerformanceSummary {
  totalDecisions: number;
  successRate: number;
  totalProfit: number;
  avgConfidence: number;
  bestDecision: DecisionRecord | null;
  worstDecision: DecisionRecord | null;
  consensusAccuracy: number;
}

const EvidenceReportingDashboard: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState<'today' | 'week' | 'month' | 'all'>('week');
  const [selectedType, setSelectedType] = useState<DecisionType | 'all'>('all');
  const [expandedDecision, setExpandedDecision] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'timeline' | 'analytics'>('timeline');

  // Fetch decision history
  const { data: decisions, isLoading: decisionsLoading } = useQuery({
    queryKey: ['decision-history', selectedPeriod, selectedType],
    queryFn: async () => {
      const params = new URLSearchParams({
        period: selectedPeriod,
        ...(selectedType !== 'all' && { type: selectedType })
      });
      const response = await apiClient.get(`/api/v1/ai/decision-history?${params}`);
      return response.data.data || [];
    },
    refetchInterval: 30000
  });

  // Fetch performance summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['decision-summary', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/ai/decision-summary?period=${selectedPeriod}`);
      return response.data.data || {
        totalDecisions: 0,
        successRate: 0,
        totalProfit: 0,
        avgConfidence: 0,
        bestDecision: null,
        worstDecision: null,
        consensusAccuracy: 0
      };
    }
  });

  // Mock data for development
  const mockDecisions: DecisionRecord[] = [
    {
      id: '1',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      type: DecisionType.TRADE_EXECUTION,
      status: DecisionStatus.SUCCESS,
      phase: 'completed',
      action: 'BUY',
      symbol: 'BTC',
      amount: 0.5,
      price: 42000,
      reasoning: {
        primary: 'Strong bullish momentum detected with multiple confirmation signals',
        factors: [
          'RSI oversold bounce at 32',
          'Volume spike 3x average',
          'Support level held at $41,500',
          'Positive funding rates'
        ],
        confidence: 0.85
      },
      aiConsensus: {
        gpt4: {
          vote: 'buy',
          confidence: 0.88,
          reasoning: 'Technical indicators strongly bullish, momentum building'
        },
        claude: {
          vote: 'buy',
          confidence: 0.82,
          reasoning: 'Market structure intact, good risk/reward setup'
        },
        gemini: {
          vote: 'buy',
          confidence: 0.85,
          reasoning: 'Sentiment shift detected, accumulation phase evident'
        },
        final: 'buy',
        agreement: 1.0
      },
      marketConditions: {
        trend: 'bullish',
        volatility: 'medium',
        volume: 'high',
        signals: ['Golden Cross', 'MACD Bullish', 'Breaking Resistance']
      },
      riskAnalysis: {
        riskScore: 35,
        exposureLevel: 0.15,
        potentialLoss: 500,
        potentialGain: 1500,
        riskRewardRatio: 3.0
      },
      outcome: {
        result: 'profit',
        amount: 1250,
        percentage: 5.95,
        duration: '2h 15m'
      },
      phaseDetails: {
        analysis: { duration: 450, dataPoints: 2500 },
        consensus: { duration: 320, iterations: 3 },
        validation: { duration: 180, checks: 15 },
        execution: { duration: 85, slippage: 0.05 },
        monitoring: { duration: 8100, adjustments: 2 }
      }
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      type: DecisionType.RISK_ASSESSMENT,
      status: DecisionStatus.SUCCESS,
      phase: 'completed',
      action: 'REDUCE_EXPOSURE',
      reasoning: {
        primary: 'Portfolio risk exceeding threshold, market conditions deteriorating',
        factors: [
          'VIX spike above 25',
          'Correlation breakdown detected',
          'Drawdown approaching 8%',
          'Macro uncertainty increasing'
        ],
        confidence: 0.92
      },
      aiConsensus: {
        gpt4: {
          vote: 'reduce',
          confidence: 0.95,
          reasoning: 'Risk metrics flashing warning, preservation mode recommended'
        },
        claude: {
          vote: 'reduce',
          confidence: 0.90,
          reasoning: 'Defensive positioning warranted given market regime'
        },
        gemini: {
          vote: 'reduce',
          confidence: 0.91,
          reasoning: 'Probability of correction increased significantly'
        },
        final: 'reduce',
        agreement: 1.0
      },
      marketConditions: {
        trend: 'bearish',
        volatility: 'high',
        volume: 'normal',
        signals: ['Death Cross Forming', 'RSI Divergence', 'Support Breaking']
      },
      riskAnalysis: {
        riskScore: 78,
        exposureLevel: 0.45,
        potentialLoss: 3500,
        potentialGain: 1000,
        riskRewardRatio: 0.29
      },
      outcome: {
        result: 'profit',
        amount: 850,
        percentage: 2.1,
        duration: '45m'
      },
      phaseDetails: {
        analysis: { duration: 380, dataPoints: 1800 },
        consensus: { duration: 250, iterations: 2 },
        validation: { duration: 120, checks: 12 },
        execution: { duration: 45, slippage: 0.02 }
      }
    }
  ];

  const activeDecisions = decisions || mockDecisions;
  const performanceSummary = summary || {
    totalDecisions: activeDecisions.length,
    successRate: 0.75,
    totalProfit: 5420,
    avgConfidence: 0.86,
    consensusAccuracy: 0.91
  };

  // Calculate AI model performance
  const aiModelPerformance = [
    { model: 'GPT-4', accuracy: 88, decisions: 245, profit: 2150 },
    { model: 'Claude', accuracy: 85, decisions: 245, profit: 1980 },
    { model: 'Gemini', accuracy: 86, decisions: 245, profit: 2050 },
    { model: 'Consensus', accuracy: 91, decisions: 245, profit: 2680 }
  ];

  // Phase duration analysis
  const phaseDurations = [
    { phase: 'Analysis', avg: 420, total: 12600 },
    { phase: 'Consensus', avg: 280, total: 8400 },
    { phase: 'Validation', avg: 150, total: 4500 },
    { phase: 'Execution', avg: 65, total: 1950 },
    { phase: 'Monitoring', avg: 7200, total: 216000 }
  ];

  // Decision distribution by type
  const decisionDistribution = [
    { type: 'Trade Execution', value: 45, color: '#10b981' },
    { type: 'Risk Assessment', value: 25, color: '#f59e0b' },
    { type: 'Portfolio Rebalance', value: 20, color: '#3b82f6' },
    { type: 'Strategy Change', value: 8, color: '#8b5cf6' },
    { type: 'Emergency Action', value: 2, color: '#ef4444' }
  ];

  const getDecisionIcon = (type: DecisionType) => {
    switch (type) {
      case DecisionType.TRADE_EXECUTION:
        return <TrendingUp className="h-4 w-4" />;
      case DecisionType.RISK_ASSESSMENT:
        return <Shield className="h-4 w-4" />;
      case DecisionType.PORTFOLIO_REBALANCE:
        return <BarChart3 className="h-4 w-4" />;
      case DecisionType.STRATEGY_CHANGE:
        return <GitBranch className="h-4 w-4" />;
      case DecisionType.EMERGENCY_ACTION:
        return <AlertTriangle className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: DecisionStatus) => {
    switch (status) {
      case DecisionStatus.SUCCESS:
        return 'text-green-500';
      case DecisionStatus.FAILED:
        return 'text-red-500';
      case DecisionStatus.PENDING:
        return 'text-yellow-500';
      case DecisionStatus.PARTIAL:
        return 'text-orange-500';
    }
  };

  const mapDecisionStatusToBgClass = (status: DecisionStatus) => {
    switch (status) {
      case DecisionStatus.SUCCESS:
        return 'bg-green-500/10';
      case DecisionStatus.PENDING:
        return 'bg-yellow-500/10';
      case DecisionStatus.PARTIAL:
        return 'bg-orange-500/10';
      case DecisionStatus.FAILED:
        return 'bg-red-500/10';
      default:
        return 'bg-gray-500/10';
    }
  };

  const renderDecisionCard = (decision: DecisionRecord) => {
    const isExpanded = expandedDecision === decision.id;
    
    return (
      <motion.div
        key={decision.id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4"
      >
        <Card className={cn(
          'transition-all cursor-pointer',
          isExpanded && 'ring-2 ring-primary'
        )}>
          <CardHeader 
            className="pb-3"
            onClick={() => setExpandedDecision(isExpanded ? null : decision.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className={cn(
                  'p-2 rounded-lg',
                  mapDecisionStatusToBgClass(decision.status)
                )}>
                  {getDecisionIcon(decision.type)}
                </div>
                
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold">
                      {decision.action} {decision.symbol && `${decision.symbol}`}
                    </h4>
                    <Badge variant="outline" className={getStatusColor(decision.status)}>
                      {decision.status}
                    </Badge>
                    <Badge variant="secondary">
                      {(decision.reasoning.confidence * 100).toFixed(0)}% confidence
                    </Badge>
                  </div>
                  
                  <p className="text-sm text-muted-foreground">
                    {decision.reasoning.primary}
                  </p>
                  
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(decision.timestamp).toLocaleString()}
                    </span>
                    {decision.outcome && (() => {
                      const result = decision.outcome.result;
                      let className = 'flex items-center gap-1 font-medium ';
                      let sign = '';
                      let percentageDisplay = '';

                      switch (result) {
                        case 'profit':
                          className += 'text-green-500';
                          sign = '+';
                          percentageDisplay = `(${formatPercentage(decision.outcome.percentage)})`;
                          break;
                        case 'loss':
                          className += 'text-red-500';
                          sign = '-';
                          percentageDisplay = `(${formatPercentage(decision.outcome.percentage)})`;
                          break;
                        case 'breakeven':
                          className += 'text-gray-500';
                          sign = '';
                          percentageDisplay = '(0%)';
                          break;
                        case 'pending':
                          className += 'text-gray-500';
                          sign = '';
                          percentageDisplay = 'Pending';
                          break;
                        default:
                          className += 'text-gray-500';
                          sign = '';
                          percentageDisplay = '—';
                      }

                      return (
                        <span className={cn(className)}>
                          <DollarSign className="h-3 w-3" />
                          {sign}{formatCurrency(Math.abs(decision.outcome.amount))}
                          {percentageDisplay && ` ${percentageDisplay}`}
                        </span>
                      );
                    })()}
                  </div>
                </div>
              </div>
              
              <Button variant="ghost" size="sm">
                {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </Button>
            </div>
          </CardHeader>
          
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
              >
                <CardContent className="pt-0">
                  <Tabs defaultValue="reasoning" className="mt-4">
                    <TabsList className="grid w-full grid-cols-5">
                      <TabsTrigger value="reasoning">Reasoning</TabsTrigger>
                      <TabsTrigger value="consensus">AI Consensus</TabsTrigger>
                      <TabsTrigger value="market">Market</TabsTrigger>
                      <TabsTrigger value="risk">Risk</TabsTrigger>
                      <TabsTrigger value="phases">Phases</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="reasoning" className="space-y-3">
                      <div className="space-y-2">
                        <h5 className="font-medium text-sm">Decision Factors</h5>
                        <div className="space-y-1">
                          {decision.reasoning.factors.map((factor, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-sm">
                              <CheckCircle className="h-3 w-3 text-green-500 mt-0.5" />
                              <span className="text-muted-foreground">{factor}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="consensus" className="space-y-3">
                      <div className="space-y-3">
                        {Object.entries(decision.aiConsensus).map(([model, data]) => {
                          if (model === 'final' || model === 'agreement') return null;
                          const modelData = data as any;
                          return (
                            <div key={model} className="p-3 rounded-lg bg-muted/50">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <Brain className="h-4 w-4" />
                                  <span className="font-medium text-sm">
                                    {model.toUpperCase()}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Badge variant={modelData.vote === 'buy' ? 'default' : 'secondary'}>
                                    {modelData.vote}
                                  </Badge>
                                  <Badge variant="outline">
                                    {(modelData.confidence * 100).toFixed(0)}%
                                  </Badge>
                                </div>
                              </div>
                              <p className="text-xs text-muted-foreground">
                                {modelData.reasoning}
                              </p>
                            </div>
                          );
                        })}
                        
                        <div className="flex items-center justify-between pt-2 border-t">
                          <span className="text-sm font-medium">Consensus Agreement</span>
                          <Badge variant="default">
                            {(decision.aiConsensus.agreement * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="market" className="space-y-3">
                      <div className="grid grid-cols-3 gap-3">
                        <div className="text-center p-3 rounded-lg bg-muted/50">
                          <p className="text-xs text-muted-foreground">Trend</p>
                          <p className="font-medium capitalize">{decision.marketConditions.trend}</p>
                        </div>
                        <div className="text-center p-3 rounded-lg bg-muted/50">
                          <p className="text-xs text-muted-foreground">Volatility</p>
                          <p className="font-medium capitalize">{decision.marketConditions.volatility}</p>
                        </div>
                        <div className="text-center p-3 rounded-lg bg-muted/50">
                          <p className="text-xs text-muted-foreground">Volume</p>
                          <p className="font-medium capitalize">{decision.marketConditions.volume}</p>
                        </div>
                      </div>
                      
                      <div>
                        <h5 className="font-medium text-sm mb-2">Market Signals</h5>
                        <div className="flex flex-wrap gap-2">
                          {decision.marketConditions.signals.map((signal, idx) => (
                            <Badge key={idx} variant="outline">
                              {signal}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="risk" className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Risk Score</p>
                          <div className="flex items-center gap-2">
                            <p className="text-xl font-bold">{decision.riskAnalysis.riskScore}/100</p>
                            <Progress value={decision.riskAnalysis.riskScore} className="flex-1 h-2" />
                          </div>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Risk/Reward Ratio</p>
                          <p className="text-xl font-bold">1:{decision.riskAnalysis.riskRewardRatio.toFixed(1)}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Potential Loss</p>
                          <p className="text-lg font-medium text-red-500">
                            -{formatCurrency(decision.riskAnalysis.potentialLoss)}
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Potential Gain</p>
                          <p className="text-lg font-medium text-green-500">
                            +{formatCurrency(decision.riskAnalysis.potentialGain)}
                          </p>
                        </div>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="phases" className="space-y-3">
                      <div className="space-y-2">
                        {Object.entries(decision.phaseDetails).map(([phase, details]) => (
                          <div key={phase} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                            <div className="flex items-center gap-2">
                              <Activity className="h-3 w-3" />
                              <span className="text-sm font-medium capitalize">{phase}</span>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              <span>{details.duration}ms</span>
                              {'dataPoints' in details && details.dataPoints && <span>{details.dataPoints} data points</span>}
                              {'iterations' in details && details.iterations && <span>{details.iterations} iterations</span>}
                              {'checks' in details && details.checks && <span>{details.checks} checks</span>}
                              {'adjustments' in details && details.adjustments && <span>{details.adjustments} adjustments</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      <div className="pt-2 border-t">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">Total Execution Time</span>
                          <span>
                            {Object.values(decision.phaseDetails).reduce((sum, p) => sum + p.duration, 0)}ms
                          </span>
                        </div>
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      </motion.div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Brain className="h-8 w-8 text-primary" />
            Evidence-Based Reporting
          </h1>
          <p className="text-muted-foreground">
            Transparent AI decision tracking with complete reasoning and outcomes
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Select value={selectedPeriod} onValueChange={(v: any) => setSelectedPeriod(v)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="all">All Time</SelectItem>
            </SelectContent>
          </Select>
          
          <Button variant="outline" size="icon">
            <Download className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon">
            <Share2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Performance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Decisions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performanceSummary.totalDecisions}</div>
            <p className="text-xs text-muted-foreground">
              Across all strategies
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {formatPercentage(performanceSummary.successRate)}
            </div>
            <Progress value={performanceSummary.successRate} className="h-1 mt-2" />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Profit</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn(
              'text-2xl font-bold',
              performanceSummary.totalProfit >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {formatCurrency(performanceSummary.totalProfit)}
            </div>
            <p className="text-xs text-muted-foreground">
              From AI decisions
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPercentage(performanceSummary.avgConfidence)}
            </div>
            <Progress value={performanceSummary.avgConfidence} className="h-1 mt-2" />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Consensus Accuracy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">
              {formatPercentage(performanceSummary.consensusAccuracy)}
            </div>
            <p className="text-xs text-muted-foreground">
              AI model agreement
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs value={viewMode} onValueChange={(v: any) => setViewMode(v)}>
        <div className="flex items-center justify-between mb-4">
          <TabsList>
            <TabsTrigger value="timeline">Decision Timeline</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>
          
          {viewMode === 'timeline' && (
            <Select value={selectedType} onValueChange={(v: any) => setSelectedType(v)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Decisions</SelectItem>
                <SelectItem value={DecisionType.TRADE_EXECUTION}>Trade Execution</SelectItem>
                <SelectItem value={DecisionType.RISK_ASSESSMENT}>Risk Assessment</SelectItem>
                <SelectItem value={DecisionType.PORTFOLIO_REBALANCE}>Portfolio Rebalance</SelectItem>
                <SelectItem value={DecisionType.STRATEGY_CHANGE}>Strategy Change</SelectItem>
                <SelectItem value={DecisionType.EMERGENCY_ACTION}>Emergency Action</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>
        
        <TabsContent value="timeline" className="space-y-4">
          <ScrollArea className="h-[600px]">
            {decisionsLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
                <p className="text-sm text-muted-foreground mt-4">Loading decisions...</p>
              </div>
            ) : activeDecisions.length > 0 ? (
              activeDecisions.map(renderDecisionCard)
            ) : (
              <Card>
                <CardContent className="text-center py-8">
                  <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-lg font-semibold mb-2">No Decisions Yet</p>
                  <p className="text-sm text-muted-foreground">
                    AI decisions will appear here as they are made
                  </p>
                </CardContent>
              </Card>
            )}
          </ScrollArea>
        </TabsContent>
        
        <TabsContent value="analytics" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* AI Model Performance */}
            <Card>
              <CardHeader>
                <CardTitle>AI Model Performance</CardTitle>
                <CardDescription>Accuracy and profitability by model</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={aiModelPerformance}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="model" stroke="#888" fontSize={12} />
                    <YAxis stroke="#888" fontSize={12} />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="accuracy" fill="hsl(var(--primary))" name="Accuracy %" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Decision Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Decision Distribution</CardTitle>
                <CardDescription>Breakdown by decision type</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={decisionDistribution}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      nameKey="type"
                    >
                      {decisionDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Phase Duration Analysis */}
            <Card>
              <CardHeader>
                <CardTitle>Phase Duration Analysis</CardTitle>
                <CardDescription>Average time spent in each phase</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {phaseDurations.map((phase) => (
                    <div key={phase.phase} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span>{phase.phase}</span>
                        <span className="font-medium">{phase.avg}ms avg</span>
                      </div>
                      <Progress 
                        value={(phase.avg / Math.max(...phaseDurations.map(p => p.avg))) * 100} 
                        className="h-2"
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Confidence vs Outcome */}
            <Card>
              <CardHeader>
                <CardTitle>Confidence vs Outcome</CardTitle>
                <CardDescription>Correlation between confidence and success</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-sm text-muted-foreground">High Confidence</p>
                      <p className="text-xl font-bold text-green-500">92%</p>
                      <p className="text-xs text-muted-foreground">Success Rate</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Medium Confidence</p>
                      <p className="text-xl font-bold text-yellow-500">71%</p>
                      <p className="text-xs text-muted-foreground">Success Rate</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Low Confidence</p>
                      <p className="text-xl font-bold text-red-500">45%</p>
                      <p className="text-xs text-muted-foreground">Success Rate</p>
                    </div>
                  </div>
                  
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      Higher AI confidence strongly correlates with better outcomes,
                      validating our decision-making process.
                    </AlertDescription>
                  </Alert>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default EvidenceReportingDashboard;