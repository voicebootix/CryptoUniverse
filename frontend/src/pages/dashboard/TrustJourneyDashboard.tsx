import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  Shield,
  Award,
  Target,
  DollarSign,
  BarChart3,
  ChevronRight,
  Lock,
  Unlock,
  CheckCircle,
  AlertTriangle,
  Info,
  Trophy,
  Zap,
  Star,
  Activity,
  ArrowUp,
  ArrowDown,
  Clock,
  Users,
  Sparkles
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { formatCurrency, formatPercentage, cn } from '@/lib/utils';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';

// Trust Levels
enum TrustLevel {
  BEGINNER = 'beginner',
  INTERMEDIATE = 'intermediate',
  ADVANCED = 'advanced',
  EXPERT = 'expert'
}

// Trust Level Configuration
const trustLevelConfig = {
  [TrustLevel.BEGINNER]: {
    name: 'Beginner',
    icon: <Shield className="h-5 w-5" />,
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/20',
    minScore: 0,
    maxScore: 29,
    positionLimit: 100,
    features: ['Paper Trading', 'Basic Strategies', 'Manual Trading'],
    badge: '🌱'
  },
  [TrustLevel.INTERMEDIATE]: {
    name: 'Intermediate',
    icon: <Target className="h-5 w-5" />,
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
    minScore: 30,
    maxScore: 59,
    positionLimit: 1000,
    features: ['Live Trading', 'Advanced Strategies', 'Semi-Autonomous'],
    badge: '🎯'
  },
  [TrustLevel.ADVANCED]: {
    name: 'Advanced',
    icon: <Award className="h-5 w-5" />,
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20',
    minScore: 60,
    maxScore: 89,
    positionLimit: 10000,
    features: ['Full Autonomous', 'All Strategies', 'Higher Limits'],
    badge: '🚀'
  },
  [TrustLevel.EXPERT]: {
    name: 'Expert',
    icon: <Trophy className="h-5 w-5" />,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/20',
    minScore: 90,
    maxScore: 100,
    positionLimit: 100000,
    features: ['Unlimited Trading', 'Strategy Creation', 'Revenue Sharing'],
    badge: '👑'
  }
};

// Milestones
interface ApiMilestone {
  id: string;
  title: string;
  description: string;
  requirement: string;
  progress: number;
  target: number;
  completed: boolean;
  reward: string;
  iconKey: string;
}

interface Milestone {
  id: string;
  title: string;
  description: string;
  requirement: string;
  progress: number;
  target: number;
  completed: boolean;
  reward: string;
  icon: React.ReactNode;
}

// Icon mapping for milestones
const iconByKey: Record<string, React.ReactNode> = {
  'trophy': <Trophy className="h-5 w-5" />,
  'target': <Target className="h-5 w-5" />,
  'shield': <Shield className="h-5 w-5" />,
  'zap': <Zap className="h-5 w-5" />,
  'star': <Star className="h-5 w-5" />,
  'activity': <Activity className="h-5 w-5" />,
  'trending-up': <TrendingUp className="h-5 w-5" />,
  'dollar-sign': <DollarSign className="h-5 w-5" />,
  'bar-chart': <BarChart3 className="h-5 w-5" />,
  'users': <Users className="h-5 w-5" />,
  'sparkles': <Sparkles className="h-5 w-5" />,
  'award': <Award className="h-5 w-5" />,
  'check-circle': <CheckCircle className="h-5 w-5" />
};

// Map API milestones to UI milestones with proper icons
const mapMilestones = (apiMilestones: ApiMilestone[]): Milestone[] => {
  return apiMilestones.map(m => ({
    ...m,
    icon: iconByKey[m.iconKey] || <Target className="h-5 w-5" />
  }));
};

// Performance Metrics
interface PerformanceMetrics {
  winRate: number;
  avgProfit: number;
  totalTrades: number;
  successfulTrades: number;
  riskScore: number;
  consistencyScore: number;
  profitFactor: number;
  sharpeRatio: number;
}

const TrustJourneyDashboard: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState<'week' | 'month' | 'all'>('month');
  const [showDetails, setShowDetails] = useState(false);

  // Fetch trust score data
  const { data: trustData, isLoading: trustLoading } = useQuery({
    queryKey: ['trust-score'],
    queryFn: async () => {
      const response = await apiClient.get('/user/trust-score');
      return response.data.data || {
        score: 0,
        level: TrustLevel.BEGINNER,
        totalTrades: 0,
        successfulTrades: 0,
        totalProfit: 0,
        positionLimit: 100
      };
    },
    refetchInterval: 60000 // Refresh every minute
  });

  // Fetch performance history
  const { data: performanceHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['performance-history', selectedPeriod],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/user/performance-history?period=${selectedPeriod}`);
      return response.data.data || [];
    }
  });

  // Fetch milestones
  const { data: milestones, isLoading: milestonesLoading } = useQuery({
    queryKey: ['trust-milestones'],
    queryFn: async () => {
      const response = await apiClient.get('/user/milestones');
      return mapMilestones(response.data.data || []);
    }
  });

  const getCurrentLevel = (score: number): TrustLevel => {
    if (score >= 90) return TrustLevel.EXPERT;
    if (score >= 60) return TrustLevel.ADVANCED;
    if (score >= 30) return TrustLevel.INTERMEDIATE;
    return TrustLevel.BEGINNER;
  };

  const getNextLevel = (currentLevel: TrustLevel): TrustLevel | null => {
    switch (currentLevel) {
      case TrustLevel.BEGINNER:
        return TrustLevel.INTERMEDIATE;
      case TrustLevel.INTERMEDIATE:
        return TrustLevel.ADVANCED;
      case TrustLevel.ADVANCED:
        return TrustLevel.EXPERT;
      default:
        return null;
    }
  };

  const currentLevel = trustData ? getCurrentLevel(trustData.score) : TrustLevel.BEGINNER;
  const nextLevel = getNextLevel(currentLevel);
  const levelConfig = trustLevelConfig[currentLevel];
  const nextLevelConfig = nextLevel ? trustLevelConfig[nextLevel] : null;

  // Calculate progress to next level
  const progressToNextLevel = trustData && nextLevelConfig
    ? ((trustData.score - levelConfig.minScore) / (nextLevelConfig.minScore - levelConfig.minScore)) * 100
    : 100;

  // Mock performance metrics (replace with real data)
  const performanceMetrics: PerformanceMetrics = {
    winRate: trustData?.successfulTrades / Math.max(trustData?.totalTrades, 1) || 0,
    avgProfit: trustData?.totalProfit / Math.max(trustData?.totalTrades, 1) || 0,
    totalTrades: trustData?.totalTrades || 0,
    successfulTrades: trustData?.successfulTrades || 0,
    riskScore: 75,
    consistencyScore: 82,
    profitFactor: 1.8,
    sharpeRatio: 1.2
  };

  // Mock milestones data
  const defaultMilestones: Milestone[] = [
    {
      id: '1',
      title: 'First Trade',
      description: 'Complete your first trade',
      requirement: '1 trade',
      progress: Math.min(performanceMetrics.totalTrades, 1),
      target: 1,
      completed: performanceMetrics.totalTrades >= 1,
      reward: '+5 Trust Score',
      icon: <TrendingUp className="h-4 w-4" />
    },
    {
      id: '2',
      title: 'Profitable Trader',
      description: 'Achieve overall profitability',
      requirement: 'Positive P&L',
      progress: trustData?.totalProfit > 0 ? 1 : 0,
      target: 1,
      completed: trustData?.totalProfit > 0,
      reward: '+10 Trust Score',
      icon: <DollarSign className="h-4 w-4" />
    },
    {
      id: '3',
      title: 'Consistent Winner',
      description: 'Maintain 60% win rate',
      requirement: '60% win rate',
      progress: Math.min(Math.max(performanceMetrics.winRate * 100, 0), 100),
      target: 60,
      completed: performanceMetrics.winRate >= 0.6,
      reward: '+15 Trust Score',
      icon: <Trophy className="h-4 w-4" />
    },
    {
      id: '4',
      title: 'Risk Manager',
      description: 'Complete 50 trades without major loss',
      requirement: '50 safe trades',
      progress: Math.min(performanceMetrics.totalTrades, 50),
      target: 50,
      completed: performanceMetrics.totalTrades >= 50,
      reward: 'Unlock Advanced Strategies',
      icon: <Shield className="h-4 w-4" />
    }
  ];

  const activeMilestones = milestones || defaultMilestones;

  // Mock performance chart data
  const chartData = performanceHistory || [
    { date: 'Mon', profit: 120, trades: 5, winRate: 60 },
    { date: 'Tue', profit: 250, trades: 8, winRate: 75 },
    { date: 'Wed', profit: 180, trades: 6, winRate: 66 },
    { date: 'Thu', profit: 420, trades: 10, winRate: 80 },
    { date: 'Fri', profit: 380, trades: 9, winRate: 77 },
    { date: 'Sat', profit: 520, trades: 12, winRate: 83 },
    { date: 'Sun', profit: 480, trades: 11, winRate: 81 }
  ];

  // Radar chart data for skills
  const skillsData = [
    { skill: 'Trading', value: performanceMetrics.winRate * 100 },
    { skill: 'Risk Mgmt', value: performanceMetrics.riskScore },
    { skill: 'Consistency', value: performanceMetrics.consistencyScore },
    { skill: 'Profit', value: Math.min(performanceMetrics.profitFactor * 50, 100) },
    { skill: 'Strategy', value: (trustData?.score || 0) },
    { skill: 'Discipline', value: 70 }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Shield className="h-8 w-8 text-primary" />
            Trust Journey
          </h1>
          <p className="text-muted-foreground">
            Build trust, unlock features, and increase your trading limits
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Badge variant="outline" className={cn('text-lg px-4 py-2', levelConfig.color)}>
            {levelConfig.badge} {levelConfig.name}
          </Badge>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon">
                  <Info className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent className="max-w-sm">
                <p className="font-semibold mb-2">How Trust Score Works</p>
                <p className="text-sm">
                  Your trust score increases based on successful trades, consistent profits,
                  risk management, and time on the platform. Higher trust unlocks more features
                  and increases your position limits.
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Current Level Card */}
      <Card className={cn('border-2', levelConfig.borderColor)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {levelConfig.icon}
              <div>
                <CardTitle className="text-2xl">
                  Trust Score: {trustData?.score || 0}/100
                </CardTitle>
                <CardDescription>
                  Current Level: {levelConfig.name}
                </CardDescription>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Position Limit</p>
              <p className="text-2xl font-bold">{formatCurrency(levelConfig.positionLimit)}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {nextLevelConfig && (
            <>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Progress to {nextLevelConfig.name}</span>
                  <span className="font-medium">
                    {trustData?.score || 0}/{nextLevelConfig.minScore}
                  </span>
                </div>
                <Progress value={progressToNextLevel} className="h-3" />
                <p className="text-xs text-muted-foreground">
                  {nextLevelConfig.minScore - (trustData?.score || 0)} points needed for next level
                </p>
              </div>
              
              <Separator />
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium mb-2">Current Features</p>
                  <div className="space-y-1">
                    {levelConfig.features.map((feature, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <p className="text-sm font-medium mb-2">Next Level Unlocks</p>
                  <div className="space-y-1">
                    {nextLevelConfig.features.map((feature, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Lock className="h-3 w-3" />
                        <span>{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPercentage(performanceMetrics.winRate * 100)}
            </div>
            <Progress value={performanceMetrics.winRate * 100} className="h-1 mt-2" />
            <p className="text-xs text-muted-foreground mt-2">
              {performanceMetrics.successfulTrades}/{performanceMetrics.totalTrades} trades
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Total Profit</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn(
              'text-2xl font-bold',
              (trustData?.totalProfit || 0) >= 0 ? 'text-green-500' : 'text-red-500'
            )}>
              {formatCurrency(trustData?.totalProfit || 0)}
            </div>
            <div className="flex items-center gap-1 mt-2">
              {(trustData?.totalProfit || 0) >= 0 ? (
                <ArrowUp className="h-3 w-3 text-green-500" />
              ) : (
                <ArrowDown className="h-3 w-3 text-red-500" />
              )}
              <span className="text-xs text-muted-foreground">
                Avg: {formatCurrency(performanceMetrics.avgProfit)}/trade
              </span>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Risk Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {performanceMetrics.riskScore}/100
            </div>
            <Progress value={performanceMetrics.riskScore} className="h-1 mt-2" />
            <p className="text-xs text-muted-foreground mt-2">
              Sharpe Ratio: {performanceMetrics.sharpeRatio.toFixed(2)}
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Consistency</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {performanceMetrics.consistencyScore}%
            </div>
            <Progress value={performanceMetrics.consistencyScore} className="h-1 mt-2" />
            <p className="text-xs text-muted-foreground mt-2">
              Profit Factor: {performanceMetrics.profitFactor.toFixed(2)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts and Milestones */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Chart */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Performance History</CardTitle>
              <Tabs value={selectedPeriod} onValueChange={(v) => setSelectedPeriod(v as any)}>
                <TabsList className="h-8">
                  <TabsTrigger value="week" className="text-xs">Week</TabsTrigger>
                  <TabsTrigger value="month" className="text-xs">Month</TabsTrigger>
                  <TabsTrigger value="all" className="text-xs">All</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="date" stroke="#888" fontSize={12} />
                <YAxis stroke="#888" fontSize={12} />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--background))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px'
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="profit"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Skills Radar */}
        <Card>
          <CardHeader>
            <CardTitle>Trading Skills</CardTitle>
            <CardDescription>Your performance across key metrics</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={skillsData}>
                <PolarGrid stroke="#333" />
                <PolarAngleAxis dataKey="skill" stroke="#888" fontSize={12} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#888" fontSize={10} />
                <Radar
                  name="Skills"
                  dataKey="value"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.3}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Milestones */}
      <Card>
        <CardHeader>
          <CardTitle>Milestones & Achievements</CardTitle>
          <CardDescription>Complete milestones to increase your trust score</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeMilestones.map((milestone) => (
              <div
                key={milestone.id}
                className={cn(
                  'p-4 rounded-lg border transition-all',
                  milestone.completed
                    ? 'bg-green-500/5 border-green-500/20'
                    : 'bg-muted/50 border-border'
                )}
              >
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'p-2 rounded-lg',
                    milestone.completed ? 'bg-green-500/10' : 'bg-muted'
                  )}>
                    {milestone.icon}
                  </div>
                  
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="font-semibold">{milestone.title}</h4>
                      {milestone.completed && (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      )}
                    </div>
                    
                    <p className="text-sm text-muted-foreground mb-2">
                      {milestone.description}
                    </p>
                    
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span>{milestone.requirement}</span>
                        <span className="font-medium">
                          {milestone.progress}/{milestone.target}
                        </span>
                      </div>
                      <Progress
                        value={milestone.target === 0 ? (milestone.completed ? 100 : 0) : Math.min((milestone.progress / milestone.target) * 100, 100)}
                        className="h-1"
                      />
                      <div className="flex items-center gap-1">
                        <Sparkles className="h-3 w-3 text-yellow-500" />
                        <span className="text-xs font-medium">{milestone.reward}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Trust Building Tips */}
      <Alert>
        <Zap className="h-4 w-4" />
        <AlertTitle>Tips to Increase Trust Score</AlertTitle>
        <AlertDescription className="mt-2">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
            <div className="flex items-start gap-2">
              <CheckCircle className="h-3 w-3 text-green-500 mt-0.5" />
              <span className="text-sm">Maintain consistent profitability</span>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-3 w-3 text-green-500 mt-0.5" />
              <span className="text-sm">Use proper risk management</span>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-3 w-3 text-green-500 mt-0.5" />
              <span className="text-sm">Complete paper trading milestones</span>
            </div>
            <div className="flex items-start gap-2">
              <CheckCircle className="h-3 w-3 text-green-500 mt-0.5" />
              <span className="text-sm">Diversify your trading strategies</span>
            </div>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
};

export default TrustJourneyDashboard;