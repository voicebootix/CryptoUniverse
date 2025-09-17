import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FlaskConical,
  Play,
  Pause,
  Square as Stop,
  Settings,
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart,
  Target,
  Clock,
  Users,
  DollarSign,
  Percent,
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Plus,
  Edit,
  Trash2,
  Copy,
  Eye,
  Download,
  Filter,
  Search,
  Calendar,
  Zap,
  Award,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  BookOpen,
  Globe
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Progress } from '@/components/ui/progress';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ScatterChart,
  Scatter
} from 'recharts';

// Helper function for type-safe HTTP status extraction
const getHttpStatus = (err: unknown): number | undefined => {
  if (err && typeof err === 'object' && 'response' in err) {
    const response = (err as any).response;
    if (response && typeof response.status === 'number') {
      return response.status;
    }
  }
  return undefined;
};

interface ABTestVariant {
  id: string;
  name: string;
  description: string;
  strategy_code: string;
  parameters: Record<string, any>;
  allocation_percentage: number;
  is_control: boolean;
  status: 'draft' | 'running' | 'paused' | 'completed' | 'failed';
  
  // Performance Metrics
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  avg_trade_duration: number;
  profit_factor: number;
  volatility: number;
  
  // Statistical Significance
  p_value: number;
  confidence_level: number;
  statistical_significance: 'significant' | 'not_significant' | 'inconclusive';
  
  // User Metrics
  active_users: number;
  user_satisfaction: number;
  
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

interface ABTest {
  id: string;
  name: string;
  description: string;
  hypothesis: string;
  success_metric: string;
  status: 'draft' | 'running' | 'paused' | 'completed' | 'failed';
  
  // Test Configuration
  min_sample_size: number;
  confidence_level: number;
  test_duration_days: number;
  traffic_allocation: number; // Percentage of users in the test
  
  // Results
  total_participants: number;
  winning_variant_id?: string;
  statistical_power: number;
  effect_size: number;
  
  variants: ABTestVariant[];
  
  created_at: string;
  started_at?: string;
  completed_at?: string;
  created_by: string;
}

interface ABTestMetrics {
  total_tests: number;
  running_tests: number;
  completed_tests: number;
  successful_optimizations: number;
  avg_improvement: number;
  total_participants: number;
}

const ABTestingLab: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState<'overview' | 'tests' | 'create' | 'results'>('overview');
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  
  // Form state for new test creation
  const [testForm, setTestForm] = useState({
    name: '',
    description: '',
    hypothesis: '',
    success_metric: 'total_return',
    min_sample_size: 1000,
    confidence_level: 95,
    test_duration_days: 30,
    traffic_allocation: 20
  });

  const [newVariant, setNewVariant] = useState({
    name: '',
    description: '',
    allocation_percentage: 50,
    parameters: {} as Record<string, any>
  });

  const [expandedTests, setExpandedTests] = useState<Set<string>>(new Set());

  const queryClient = useQueryClient();

  // Fetch AB testing metrics
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useQuery({
    queryKey: ['ab-testing-metrics'],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/ab-testing/metrics');
        return response.data as ABTestMetrics;
      } catch (error: any) {
        // If endpoint doesn't exist or is not implemented, provide mock data
        const status = getHttpStatus(error);
        if (status === 405 || status === 404 || status === 501) {
          console.log(`A/B testing metrics endpoint not implemented (${status}), using mock data`);
          const mockMetrics: ABTestMetrics = {
            total_tests: 0,
            running_tests: 0,
            completed_tests: 0,
            successful_optimizations: 0,
            avg_improvement: 0,
            total_participants: 0
          };
          return mockMetrics;
        }
        throw error;
      }
    },
    refetchInterval: 60000
  });

  // Fetch AB tests
  const { data: tests, isLoading: testsLoading, error: testsError } = useQuery({
    queryKey: ['ab-tests', filterStatus],
    queryFn: async () => {
      try {
        const response = await apiClient.get('/ab-testing/tests', {
          params: { status: filterStatus !== 'all' ? filterStatus : undefined }
        });
        return response.data.tests as ABTest[];
      } catch (error: any) {
        // If endpoint doesn't exist or is not implemented, provide empty test list
        const status = getHttpStatus(error);
        if (status === 405 || status === 404 || status === 501) {
          console.log(`A/B testing tests endpoint not implemented (${status}), using empty data`);
          return [];
        }
        throw error;
      }
    },
    refetchInterval: 30000
  });

  // Create AB test mutation
  const createTestMutation = useMutation({
    mutationFn: async (testData: typeof testForm & { variants: ABTestVariant[] }) => {
      const response = await apiClient.post('/ab-testing/tests', testData);
      return response.data;
    },
    onSuccess: () => {
      toast.success('AB test created successfully');
      queryClient.invalidateQueries({ queryKey: ['ab-tests'] });
      queryClient.invalidateQueries({ queryKey: ['ab-testing-metrics'] });
      setSelectedTab('tests');
      // Reset form
      setTestForm({
        name: '',
        description: '',
        hypothesis: '',
        success_metric: 'total_return',
        min_sample_size: 1000,
        confidence_level: 95,
        test_duration_days: 30,
        traffic_allocation: 20
      });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to create AB test');
    }
  });

  // Start/pause/stop test mutations
  const startTestMutation = useMutation({
    mutationFn: async (testId: string) => {
      const response = await apiClient.post(`/ab-testing/tests/${testId}/start`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('AB test started successfully');
      queryClient.invalidateQueries({ queryKey: ['ab-tests'] });
    }
  });

  const pauseTestMutation = useMutation({
    mutationFn: async (testId: string) => {
      const response = await apiClient.post(`/ab-testing/tests/${testId}/pause`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('AB test paused');
      queryClient.invalidateQueries({ queryKey: ['ab-tests'] });
    }
  });

  const stopTestMutation = useMutation({
    mutationFn: async (testId: string) => {
      const response = await apiClient.post(`/ab-testing/tests/${testId}/stop`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('AB test stopped');
      queryClient.invalidateQueries({ queryKey: ['ab-tests'] });
    }
  });

  const getStatusColor = (status: ABTest['status']) => {
    switch (status) {
      case 'draft': return 'bg-gray-500';
      case 'running': return 'bg-green-500';
      case 'paused': return 'bg-yellow-500';
      case 'completed': return 'bg-blue-500';
      case 'failed': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: ABTest['status']) => {
    switch (status) {
      case 'draft': return <Edit className="h-4 w-4" />;
      case 'running': return <Play className="h-4 w-4" />;
      case 'paused': return <Pause className="h-4 w-4" />;
      case 'completed': return <CheckCircle className="h-4 w-4" />;
      case 'failed': return <XCircle className="h-4 w-4" />;
      default: return <Settings className="h-4 w-4" />;
    }
  };

  const getSignificanceColor = (significance: ABTestVariant['statistical_significance']) => {
    switch (significance) {
      case 'significant': return 'text-green-600';
      case 'not_significant': return 'text-red-600';
      case 'inconclusive': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  };

  const filteredTests = tests?.filter(test =>
    test.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    test.description.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const toggleTestExpansion = (testId: string) => {
    const newExpanded = new Set(expandedTests);
    if (newExpanded.has(testId)) {
      newExpanded.delete(testId);
    } else {
      newExpanded.add(testId);
    }
    setExpandedTests(newExpanded);
  };

  if (metricsError || testsError) {
    // Check if this is an authentication or implementation error (type-safe)
    const metricsStatus = getHttpStatus(metricsError);
    const testsStatus = getHttpStatus(testsError);
    const isAuthError = metricsStatus === 401 ||
                       testsStatus === 401 ||
                       metricsStatus === 500 ||
                       testsStatus === 500;
    const isNotImplemented = (metricsStatus && [405, 404, 501].includes(metricsStatus)) ||
                          (testsStatus && [405, 404, 501].includes(testsStatus));

    return (
      <div className="p-6">
        <Card>
          <CardContent className="text-center p-12">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load AB Testing Data</h3>
            <p className="text-muted-foreground mb-4">
              {isAuthError
                ? "Authentication service is currently unavailable. Please try again later or contact support."
                : isNotImplemented
                ? "A/B Testing endpoints are not yet implemented. This feature is coming soon!"
                : "Unable to fetch AB testing information. Please try again."
              }
            </p>
            <div className="space-y-2">
              <Button onClick={() => queryClient.invalidateQueries()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
              {isAuthError && (
                <p className="text-xs text-muted-foreground">
                  Error: {metricsStatus || testsStatus} - Authentication service error
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <FlaskConical className="h-8 w-8 text-purple-600" />
            A/B Testing Lab
          </h2>
          <p className="text-muted-foreground">
            Optimize your trading strategies through scientific experimentation
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries()}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          
          <Button
            onClick={() => setSelectedTab('create')}
            className="bg-purple-600 hover:bg-purple-700"
          >
            <Plus className="h-4 w-4 mr-2" />
            Create Test
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      {!metricsLoading && metrics && (
        <div className="grid gap-4 md:grid-cols-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Tests</p>
                  <p className="text-2xl font-bold">{metrics.total_tests}</p>
                </div>
                <FlaskConical className="h-6 w-6 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Running Tests</p>
                  <p className="text-2xl font-bold text-green-600">{metrics.running_tests}</p>
                </div>
                <Play className="h-6 w-6 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Completed Tests</p>
                  <p className="text-2xl font-bold text-blue-600">{metrics.completed_tests}</p>
                </div>
                <CheckCircle className="h-6 w-6 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Successful Optimizations</p>
                  <p className="text-2xl font-bold text-green-600">{metrics.successful_optimizations}</p>
                </div>
                <Target className="h-6 w-6 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg Improvement</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatPercentage(metrics.avg_improvement)}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Participants</p>
                  <p className="text-2xl font-bold">{formatNumber(metrics.total_participants)}</p>
                </div>
                <Users className="h-6 w-6 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs value={selectedTab} onValueChange={setSelectedTab as any} className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tests">My Tests</TabsTrigger>
          <TabsTrigger value="create">Create Test</TabsTrigger>
          <TabsTrigger value="results">Results</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* What is A/B Testing */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-blue-500" />
                  What is A/B Testing?
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  A/B testing allows you to compare multiple versions of your trading strategies 
                  to determine which performs better. By splitting your users into different groups 
                  and measuring performance metrics, you can make data-driven optimizations.
                </p>
                
                <div className="space-y-3">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                    <div>
                      <div className="font-medium text-sm">Scientific Approach</div>
                      <div className="text-xs text-muted-foreground">
                        Use statistical significance to validate improvements
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                    <div>
                      <div className="font-medium text-sm">Risk Management</div>
                      <div className="text-xs text-muted-foreground">
                        Test changes on a small portion of users first
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                    <div>
                      <div className="font-medium text-sm">Continuous Optimization</div>
                      <div className="text-xs text-muted-foreground">
                        Iteratively improve your strategies over time
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Best Practices */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lightbulb className="h-5 w-5 text-yellow-500" />
                  Best Practices
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                    <div className="font-medium text-sm text-blue-900">Clear Hypothesis</div>
                    <div className="text-xs text-blue-700">
                      Always start with a clear, testable hypothesis about what you expect to improve
                    </div>
                  </div>
                  
                  <div className="p-3 bg-green-50 border border-green-200 rounded">
                    <div className="font-medium text-sm text-green-900">Sufficient Sample Size</div>
                    <div className="text-xs text-green-700">
                      Ensure you have enough users and time to reach statistical significance
                    </div>
                  </div>
                  
                  <div className="p-3 bg-purple-50 border border-purple-200 rounded">
                    <div className="font-medium text-sm text-purple-900">Single Variable</div>
                    <div className="text-xs text-purple-700">
                      Test one change at a time to isolate the impact of each variation
                    </div>
                  </div>
                  
                  <div className="p-3 bg-orange-50 border border-orange-200 rounded">
                    <div className="font-medium text-sm text-orange-900">Monitor Closely</div>
                    <div className="text-xs text-orange-700">
                      Watch for unexpected behavior and be ready to stop tests if needed
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Common Test Types */}
          <Card>
            <CardHeader>
              <CardTitle>Common A/B Test Types for Trading Strategies</CardTitle>
              <CardDescription>Popular optimization scenarios and what to test</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Settings className="h-5 w-5 text-blue-500" />
                    <div className="font-medium">Parameter Optimization</div>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    Test different values for strategy parameters like stop-loss levels, 
                    take-profit targets, or position sizing rules.
                  </p>
                  <div className="text-xs text-blue-600">
                    Example: 2% vs 3% stop-loss
                  </div>
                </div>

                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-5 w-5 text-green-500" />
                    <div className="font-medium">Timing Optimization</div>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    Compare different entry/exit timing mechanisms or trading time windows 
                    to optimize execution.
                  </p>
                  <div className="text-xs text-green-600">
                    Example: Market open vs mid-day trading
                  </div>
                </div>

                <div className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="h-5 w-5 text-purple-500" />
                    <div className="font-medium">Signal Filtering</div>
                  </div>
                  <p className="text-sm text-muted-foreground mb-3">
                    Test different filtering mechanisms to improve signal quality 
                    and reduce false positives.
                  </p>
                  <div className="text-xs text-purple-600">
                    Example: Volume filter vs no filter
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* My Tests */}
        <TabsContent value="tests" className="space-y-6">
          {/* Filters */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-4">
                <div className="relative flex-1 max-w-sm">
                  <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search tests..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
                
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Tests</SelectItem>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="running">Running</SelectItem>
                    <SelectItem value="paused">Paused</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Tests List */}
          <div className="space-y-4">
            {testsLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <Card key={i}>
                    <CardContent className="p-6 animate-pulse">
                      <div className="space-y-2">
                        <div className="h-4 bg-muted rounded w-1/4" />
                        <div className="h-3 bg-muted rounded w-3/4" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : filteredTests.length === 0 ? (
              <Card>
                <CardContent className="text-center p-12">
                  <FlaskConical className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Tests Found</h3>
                  <p className="text-muted-foreground mb-4">
                    {searchQuery || filterStatus !== 'all' 
                      ? 'No tests match your search criteria.'
                      : 'You haven\'t created any A/B tests yet.'
                    }
                  </p>
                  <Button onClick={() => setSelectedTab('create')}>
                    Create Your First Test
                  </Button>
                </CardContent>
              </Card>
            ) : (
              filteredTests.map((test) => (
                <Card key={test.id} className="relative">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-lg">{test.name}</h3>
                          <div className={`p-1 rounded-full ${getStatusColor(test.status)}`}>
                            {getStatusIcon(test.status)}
                          </div>
                          <Badge className={getStatusColor(test.status) + ' text-white'}>
                            {test.status.toUpperCase()}
                          </Badge>
                        </div>
                        
                        <p className="text-sm text-muted-foreground mb-3">{test.description}</p>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                          <span>Created {formatRelativeTime(new Date(test.created_at))}</span>
                          {test.started_at && <span>• Started {formatRelativeTime(new Date(test.started_at))}</span>}
                          <span>• {test.variants.length} variants</span>
                          <span>• {formatNumber(test.total_participants)} participants</span>
                        </div>

                        <div className="flex items-center gap-2 mb-4">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => toggleTestExpansion(test.id)}
                          >
                            {expandedTests.has(test.id) ? (
                              <>
                                <ChevronUp className="h-4 w-4 mr-1" />
                                Hide Details
                              </>
                            ) : (
                              <>
                                <ChevronDown className="h-4 w-4 mr-1" />
                                View Details
                              </>
                            )}
                          </Button>
                          
                          {test.status === 'draft' && (
                            <Button
                              size="sm"
                              onClick={() => startTestMutation.mutate(test.id)}
                              disabled={startTestMutation.isPending}
                            >
                              <Play className="h-4 w-4 mr-1" />
                              Start Test
                            </Button>
                          )}
                          
                          {test.status === 'running' && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => pauseTestMutation.mutate(test.id)}
                                disabled={pauseTestMutation.isPending}
                              >
                                <Pause className="h-4 w-4 mr-1" />
                                Pause
                              </Button>
                              
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => stopTestMutation.mutate(test.id)}
                                disabled={stopTestMutation.isPending}
                              >
                                <Stop className="h-4 w-4 mr-1" />
                                Stop
                              </Button>
                            </>
                          )}
                          
                          {test.status === 'paused' && (
                            <Button
                              size="sm"
                              onClick={() => startTestMutation.mutate(test.id)}
                              disabled={startTestMutation.isPending}
                            >
                              <Play className="h-4 w-4 mr-1" />
                              Resume
                            </Button>
                          )}
                        </div>
                      </div>
                      
                      {/* Quick Results */}
                      {test.status === 'completed' && test.winning_variant_id && (
                        <div className="text-right">
                          <div className="text-sm text-muted-foreground">Winner</div>
                          <div className="font-medium text-green-600">
                            {test.variants.find(v => v.id === test.winning_variant_id)?.name}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {formatPercentage(test.effect_size)} improvement
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Expanded Details */}
                    {expandedTests.has(test.id) && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-6 pt-6 border-t space-y-4"
                      >
                        <div className="grid gap-4 md:grid-cols-2">
                          <div>
                            <h5 className="font-medium mb-2">Test Configuration</h5>
                            <div className="space-y-1 text-sm text-muted-foreground">
                              <div>Hypothesis: {test.hypothesis}</div>
                              <div>Success Metric: {test.success_metric.replace('_', ' ')}</div>
                              <div>Duration: {test.test_duration_days} days</div>
                              <div>Traffic Allocation: {test.traffic_allocation}%</div>
                              <div>Min Sample Size: {formatNumber(test.min_sample_size)}</div>
                              <div>Confidence Level: {test.confidence_level}%</div>
                            </div>
                          </div>

                          <div>
                            <h5 className="font-medium mb-2">Test Results</h5>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Participants:</span>
                                <span>{formatNumber(test.total_participants)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Statistical Power:</span>
                                <span>{formatPercentage(test.statistical_power)}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Effect Size:</span>
                                <span className={test.effect_size >= 0 ? 'text-green-600' : 'text-red-600'}>
                                  {formatPercentage(test.effect_size)}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Variants Performance */}
                        <div>
                          <h5 className="font-medium mb-3">Variant Performance</h5>
                          <div className="grid gap-3 md:grid-cols-2">
                            {test.variants.map((variant) => (
                              <div key={variant.id} className="p-3 border rounded-lg">
                                <div className="flex items-center justify-between mb-2">
                                  <div className="font-medium">{variant.name}</div>
                                  <div className="flex items-center gap-2">
                                    {variant.is_control && (
                                      <Badge variant="outline" className="text-xs">Control</Badge>
                                    )}
                                    <Badge variant="outline" className="text-xs">
                                      {variant.allocation_percentage}%
                                    </Badge>
                                  </div>
                                </div>
                                
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                  <div>
                                    <span className="text-muted-foreground">Return:</span>
                                    <span className={`ml-2 font-medium ${variant.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      {formatPercentage(variant.total_return)}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Sharpe:</span>
                                    <span className="ml-2 font-medium">{variant.sharpe_ratio.toFixed(2)}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Users:</span>
                                    <span className="ml-2 font-medium">{formatNumber(variant.active_users)}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Significance:</span>
                                    <span className={`ml-2 text-xs font-medium ${getSignificanceColor(variant.statistical_significance)}`}>
                                      {variant.statistical_significance}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>

        {/* Create Test */}
        <TabsContent value="create" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Create New A/B Test</CardTitle>
              <CardDescription>
                Set up a new experiment to test strategy variations and optimize performance
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="test-name">Test Name *</Label>
                  <Input
                    id="test-name"
                    placeholder="e.g., Stop Loss Optimization"
                    value={testForm.name}
                    onChange={(e) => setTestForm(prev => ({ ...prev, name: e.target.value }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="success-metric">Success Metric</Label>
                  <Select
                    value={testForm.success_metric}
                    onValueChange={(value) => setTestForm(prev => ({ ...prev, success_metric: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="total_return">Total Return</SelectItem>
                      <SelectItem value="sharpe_ratio">Sharpe Ratio</SelectItem>
                      <SelectItem value="win_rate">Win Rate</SelectItem>
                      <SelectItem value="max_drawdown">Max Drawdown</SelectItem>
                      <SelectItem value="profit_factor">Profit Factor</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description *</Label>
                <Textarea
                  id="description"
                  placeholder="Describe what you're testing and why..."
                  rows={3}
                  value={testForm.description}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setTestForm(prev => ({ ...prev, description: e.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="hypothesis">Hypothesis *</Label>
                <Textarea
                  id="hypothesis"
                  placeholder="e.g., Reducing stop loss from 3% to 2% will improve risk-adjusted returns..."
                  rows={2}
                  value={testForm.hypothesis}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setTestForm(prev => ({ ...prev, hypothesis: e.target.value }))}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Test Duration (days)</Label>
                  <div className="space-y-2">
                    <Slider
                      value={[testForm.test_duration_days]}
                      onValueChange={([value]) => setTestForm(prev => ({ ...prev, test_duration_days: value }))}
                      min={7}
                      max={90}
                      step={1}
                    />
                    <div className="text-sm text-muted-foreground text-center">
                      {testForm.test_duration_days} days
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Traffic Allocation (%)</Label>
                  <div className="space-y-2">
                    <Slider
                      value={[testForm.traffic_allocation]}
                      onValueChange={([value]) => setTestForm(prev => ({ ...prev, traffic_allocation: value }))}
                      min={5}
                      max={50}
                      step={5}
                    />
                    <div className="text-sm text-muted-foreground text-center">
                      {testForm.traffic_allocation}% of users
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="min-sample-size">Minimum Sample Size</Label>
                  <Input
                    id="min-sample-size"
                    type="number"
                    value={testForm.min_sample_size}
                    onChange={(e) => setTestForm(prev => ({ ...prev, min_sample_size: parseInt(e.target.value) || 1000 }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confidence-level">Confidence Level (%)</Label>
                  <Select
                    value={testForm.confidence_level.toString()}
                    onValueChange={(value) => setTestForm(prev => ({ ...prev, confidence_level: parseInt(value) }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="90">90%</SelectItem>
                      <SelectItem value="95">95%</SelectItem>
                      <SelectItem value="99">99%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <div>
                    <h5 className="font-medium text-yellow-800">Important Notes</h5>
                    <div className="text-sm text-yellow-700 mt-1 space-y-1">
                      <p>• You'll need to define test variants and their parameters in the next step</p>
                      <p>• Ensure your hypothesis is specific and measurable</p>
                      <p>• Larger sample sizes provide more reliable results</p>
                      <p>• Consider market conditions that might affect your test</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-6">
                <div className="text-sm text-muted-foreground">
                  * Required fields must be completed
                </div>
                <Button
                  onClick={() => {
                    if (!testForm.name || !testForm.description || !testForm.hypothesis) {
                      toast.error('Please fill in all required fields');
                      return;
                    }
                    // This would open a variant configuration modal/step
                    toast.info('Variant configuration step would open here');
                  }}
                  disabled={!testForm.name || !testForm.description || !testForm.hypothesis}
                >
                  <ArrowRight className="h-4 w-4 mr-2" />
                  Configure Variants
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Results */}
        <TabsContent value="results" className="space-y-6">
          <Card>
            <CardContent className="text-center p-12">
              <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Advanced Results Analytics</h3>
              <p className="text-muted-foreground mb-4">
                Detailed results analysis and statistical insights will be available here once you have completed tests.
              </p>
              <Button variant="outline">
                View Documentation
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ABTestingLab;