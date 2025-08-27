import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Zap,
  Target,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Bot,
  Cpu,
  Eye,
  BarChart3,
  RefreshCw,
  Play,
  Pause,
  Settings,
  Sparkles,
  Shield,
  ArrowUpRight,
  ArrowDownRight,
  Loader,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';

// AI Model Performance Data
const aiModels = [
  {
    name: 'GPT-4 Turbo',
    provider: 'OpenAI',
    status: 'active',
    confidence: 87,
    accuracy: 94.2,
    latency: 1.2,
    cost: 0.03,
    signals: 142,
    wins: 134,
    recommendation: 'BUY',
    reasoning: 'Strong bullish momentum with breakout confirmation above $51,200 resistance',
    icon: '🧠',
    color: '#10b981'
  },
  {
    name: 'Claude-3 Opus',
    provider: 'Anthropic',
    status: 'active',
    confidence: 91,
    accuracy: 96.8,
    latency: 0.8,
    cost: 0.015,
    signals: 156,
    wins: 151,
    recommendation: 'BUY',
    reasoning: 'Technical indicators align with institutional accumulation patterns',
    icon: '🎯',
    color: '#3b82f6'
  },
  {
    name: 'Gemini Pro',
    provider: 'Google',
    status: 'active',
    confidence: 83,
    accuracy: 91.5,
    latency: 1.5,
    cost: 0.01,
    signals: 128,
    wins: 117,
    recommendation: 'HOLD',
    reasoning: 'Mixed signals suggest consolidation before next major move',
    icon: '⚡',
    color: '#f59e0b'
  }
];

// Consensus History Data
const consensusHistory = [
  { time: '09:00', consensus: 85, gpt4: 87, claude: 91, gemini: 83, price: 50800 },
  { time: '09:15', consensus: 88, gpt4: 89, claude: 92, gemini: 84, price: 51200 },
  { time: '09:30', consensus: 91, gpt4: 93, claude: 94, gemini: 86, price: 51650 },
  { time: '09:45', consensus: 87, gpt4: 85, claude: 93, gemini: 84, price: 51400 },
  { time: '10:00', consensus: 89, gpt4: 87, claude: 95, gemini: 85, price: 51800 },
];

// Market Analysis Data
const marketAnalysis = {
  sentiment: 'Bullish',
  momentum: 'Strong',
  volatility: 'Moderate',
  volume: 'Above Average',
  trend: 'Upward',
  support: 50200,
  resistance: 52500,
  nextTarget: 54000,
  riskLevel: 'Medium',
  timeframe: '4H',
  lastUpdate: new Date().toLocaleTimeString()
};

// Radar Chart Data
const radarData = [
  { metric: 'Accuracy', GPT4: 94, Claude: 97, Gemini: 92 },
  { metric: 'Speed', GPT4: 85, Claude: 95, Gemini: 80 },
  { metric: 'Cost Efficiency', GPT4: 70, Claude: 85, Gemini: 95 },
  { metric: 'Consensus', GPT4: 87, Claude: 91, Gemini: 83 },
  { metric: 'Risk Assessment', GPT4: 90, Claude: 94, Gemini: 88 },
  { metric: 'Signal Quality', GPT4: 89, Claude: 93, Gemini: 85 },
];

const AICommandCenter: React.FC = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [consensusScore, setConsensusScore] = useState(89);
  const [autoMode, setAutoMode] = useState(true);
  const [selectedTimeframe, setSelectedTimeframe] = useState('4H');

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    // Simulate AI analysis
    await new Promise(resolve => setTimeout(resolve, 3000));
    setIsAnalyzing(false);
    setConsensusScore(Math.floor(Math.random() * 20) + 80);
  };

  const getConsensusColor = (score: number) => {
    if (score >= 90) return 'text-green-500';
    if (score >= 70) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getRecommendationColor = (rec: string) => {
    if (rec === 'BUY') return 'bg-green-500/10 text-green-500 border-green-500/20';
    if (rec === 'SELL') return 'bg-red-500/10 text-red-500 border-red-500/20';
    return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Brain className="h-8 w-8 text-primary" />
            AI Command Center
          </h1>
          <p className="text-muted-foreground">
            Multi-AI consensus engine with institutional-grade decision making
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant={autoMode ? "default" : "outline"}
            onClick={() => setAutoMode(!autoMode)}
            className="gap-2"
          >
            <Bot className="h-4 w-4" />
            {autoMode ? 'Auto Mode ON' : 'Manual Mode'}
          </Button>

          <Button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className="gap-2"
          >
            {isAnalyzing ? (
              <Loader className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
          </Button>
        </div>
      </div>

      {/* Consensus Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="relative overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Consensus Score</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getConsensusColor(consensusScore)}`}>
              {consensusScore}%
            </div>
            <p className="text-xs text-muted-foreground">
              +2.3% from last hour
            </p>
            <Progress value={consensusScore} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Models</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">3/3</div>
            <p className="text-xs text-muted-foreground">
              All systems operational
            </p>
            <div className="flex gap-1 mt-2">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.17s</div>
            <p className="text-xs text-muted-foreground">
              -0.2s from last hour
            </p>
            <Badge variant="secondary" className="mt-2">Excellent</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cost Efficiency</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$0.02</div>
            <p className="text-xs text-muted-foreground">
              Per analysis cycle
            </p>
            <Badge variant="secondary" className="mt-2">Optimized</Badge>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="models" className="space-y-4">
        <TabsList>
          <TabsTrigger value="models">AI Models</TabsTrigger>
          <TabsTrigger value="consensus">Consensus History</TabsTrigger>
          <TabsTrigger value="analysis">Market Analysis</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="models" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {aiModels.map((model, index) => (
              <motion.div
                key={model.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="relative overflow-hidden">
                  <div 
                    className="absolute top-0 left-0 w-full h-1" 
                    style={{ backgroundColor: model.color }}
                  />
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{model.icon}</span>
                        <div>
                          <CardTitle className="text-lg">{model.name}</CardTitle>
                          <CardDescription>{model.provider}</CardDescription>
                        </div>
                      </div>
                      <Badge 
                        variant="secondary"
                        className={getRecommendationColor(model.recommendation)}
                      >
                        {model.recommendation}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Confidence</span>
                        <span className="font-medium">{model.confidence}%</span>
                      </div>
                      <Progress value={model.confidence} />
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-muted-foreground">Accuracy</div>
                        <div className="font-medium">{model.accuracy}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Latency</div>
                        <div className="font-medium">{model.latency}s</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Signals</div>
                        <div className="font-medium">{model.signals}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Win Rate</div>
                        <div className="font-medium">{((model.wins / model.signals) * 100).toFixed(1)}%</div>
                      </div>
                    </div>

                    <div className="p-3 bg-muted rounded-lg">
                      <div className="text-sm font-medium mb-1">Analysis</div>
                      <div className="text-xs text-muted-foreground">
                        {model.reasoning}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="consensus" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Consensus Score History</CardTitle>
              <CardDescription>
                Real-time consensus tracking across all AI models
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={consensusHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[70, 100]} />
                  <Tooltip />
                  <Line type="monotone" dataKey="consensus" stroke="#8884d8" strokeWidth={3} name="Consensus" />
                  <Line type="monotone" dataKey="gpt4" stroke="#10b981" strokeWidth={2} name="GPT-4" />
                  <Line type="monotone" dataKey="claude" stroke="#3b82f6" strokeWidth={2} name="Claude" />
                  <Line type="monotone" dataKey="gemini" stroke="#f59e0b" strokeWidth={2} name="Gemini" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analysis" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Market Analysis</CardTitle>
                <CardDescription>
                  Current market conditions and AI assessment
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="text-sm text-muted-foreground">Sentiment</div>
                    <Badge variant="secondary" className="bg-green-500/10 text-green-500">
                      {marketAnalysis.sentiment}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm text-muted-foreground">Momentum</div>
                    <Badge variant="secondary">
                      {marketAnalysis.momentum}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm text-muted-foreground">Volatility</div>
                    <Badge variant="secondary">
                      {marketAnalysis.volatility}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm text-muted-foreground">Volume</div>
                    <Badge variant="secondary">
                      {marketAnalysis.volume}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Support</span>
                    <span className="font-medium">{formatCurrency(marketAnalysis.support)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Resistance</span>
                    <span className="font-medium">{formatCurrency(marketAnalysis.resistance)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Next Target</span>
                    <span className="font-medium text-green-500">{formatCurrency(marketAnalysis.nextTarget)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>AI Model Comparison</CardTitle>
                <CardDescription>
                  Performance metrics across all models
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="metric" />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} />
                    <Radar name="GPT-4" dataKey="GPT4" stroke="#10b981" fill="#10b981" fillOpacity={0.1} />
                    <Radar name="Claude" dataKey="Claude" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.1} />
                    <Radar name="Gemini" dataKey="Gemini" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.1} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Daily Performance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">+$2,847</div>
                <p className="text-sm text-muted-foreground">AI-driven profits today</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Success Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">94.2%</div>
                <p className="text-sm text-muted-foreground">Consensus accuracy</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Total Signals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">426</div>
                <p className="text-sm text-muted-foreground">Generated today</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AICommandCenter;
