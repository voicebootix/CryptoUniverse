import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  AlertTriangle,
  RefreshCw,
  Filter,
  Search,
  MoreHorizontal,
  FileText,
  User,
  Calendar,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Star,
  Award,
  Shield,
  Play,
  Code,
  Activity,
  Target,
  DollarSign,
  Users,
  Percent,
  MessageSquare,
  Send,
  Edit,
  Trash2,
  Download,
  Upload,
  BookOpen,
  Lightbulb,
  Settings,
  Zap,
  Globe,
  Crown
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';

interface PendingStrategy {
  id: string;
  name: string;
  description: string;
  category: string;
  publisher_id: string;
  publisher_name: string;
  publisher_email: string;

  // Strategy Details
  risk_level: 'low' | 'medium' | 'high';
  complexity_level: 'beginner' | 'intermediate' | 'advanced';
  expected_return_range: [number, number];
  required_capital: number;
  max_positions: number;
  trading_pairs: string[];
  timeframes: string[];
  tags: string[];

  // Pricing
  pricing_model: 'free' | 'one_time' | 'subscription' | 'profit_share';
  price_amount?: number;
  profit_share_percentage?: number;

  // Status and Timeline
  status: 'submitted' | 'under_review' | 'changes_requested' | 'approved' | 'rejected' | 'published';
  submitted_at: string;
  assigned_reviewer?: string;
  review_started_at?: string;
  review_due_date?: string;

  // Performance Data
  backtest_results: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    total_trades: number;
    profit_factor: number;
    volatility: number;
    period_days: number;
  };

  // Validation Results
  validation_results: {
    is_valid: boolean;
    security_score: number;
    performance_score: number;
    code_quality_score: number;
    overall_score: number;
    issues: Array<{
      type: 'error' | 'warning' | 'info';
      severity: 'high' | 'medium' | 'low';
      message: string;
      line?: number;
    }>;
  };

  // Review History
  review_history: Array<{
    reviewer: string;
    action: 'assigned' | 'reviewed' | 'approved' | 'rejected' | 'changes_requested';
    timestamp: string;
    comment?: string;
  }>;

  // Documentation
  documentation: {
    readme: string;
    changelog: string;
    examples: string[];
    api_reference: string;
  };

  created_at: string;
  updated_at: string;
}

interface ReviewStats {
  total_pending: number;
  under_review: number;
  approved_today: number;
  rejected_today: number;
  avg_review_time_hours: number;
  my_assigned: number;
}

const StrategyApprovalDebug: React.FC = () => {
  const [selectedStatus, setSelectedStatus] = useState<string>('submitted');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState<PendingStrategy | null>(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject' | 'request_changes'>('approve');
  const [reviewComment, setReviewComment] = useState('');
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);

  const queryClient = useQueryClient();

  // Add initial debug info
  console.log('🚀 [StrategyApprovalDebug] Component initializing', {
    apiBaseURL: import.meta.env.VITE_API_URL,
    currentTime: new Date().toISOString(),
    environment: import.meta.env.VITE_ENV || 'development'
  });

  // Fetch review statistics with debugging
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['admin-review-stats'],
    queryFn: async () => {
      console.log('📊 [StrategyApprovalDebug] Fetching review stats...');
      try {
        const response = await apiClient.get('/admin/strategies/review-stats');
        console.log('✅ [StrategyApprovalDebug] Review stats fetched successfully:', response.data);
        return response.data as ReviewStats;
      } catch (error: unknown) {
        console.error('❌ [StrategyApprovalDebug] Review stats fetch failed:', error);
        throw error;
      }
    },
    refetchInterval: 60000
  });

  // Fetch pending strategies with debugging
  const { data: strategies, isLoading: strategiesLoading, error: strategiesError } = useQuery({
    queryKey: ['admin-pending-strategies', selectedStatus],
    queryFn: async () => {
      console.log('📋 [StrategyApprovalDebug] Fetching pending strategies with status:', selectedStatus);
      try {
        const params = selectedStatus !== 'all' ? { status_filter: selectedStatus } : undefined;
        const response = await apiClient.get('/admin/strategies/pending', {
          params
        });
        console.log('✅ [StrategyApprovalDebug] Pending strategies fetched successfully:', {
          count: response.data.strategies?.length || 0,
          data: response.data
        });
        return response.data.strategies as PendingStrategy[];
      } catch (error: unknown) {
        console.error('❌ [StrategyApprovalDebug] Pending strategies fetch failed:', error);
        throw error;
      }
    },
    refetchInterval: 30000
  });

  // Review strategy mutation with extensive debugging
  const reviewStrategyMutation = useMutation({
    mutationFn: async (data: {
      strategyId: string;
      action: 'approve' | 'reject' | 'request_changes';
      comment?: string;
    }) => {
      console.log('🔄 [StrategyApprovalDebug] Starting mutation with data:', data);
      console.log('📡 [StrategyApprovalDebug] Making API request to:', `/admin/strategies/${data.strategyId}/review`);
      console.log('📦 [StrategyApprovalDebug] Request payload:', { action: data.action, comment: data.comment });

      try {
        const response = await apiClient.post(`/admin/strategies/${data.strategyId}/review`, {
          action: data.action,
          comment: data.comment
        });
        console.log('✅ [StrategyApprovalDebug] Mutation API call successful:', response.data);
        return response.data;
      } catch (error: unknown) {
        console.error('❌ [StrategyApprovalDebug] Mutation API call failed:', error);

        // Enhanced error logging with proper type casting
        const axiosError = error as any; // Cast to any for axios error properties
        if (axiosError.response) {
          console.error('🔍 [StrategyApprovalDebug] Error response status:', axiosError.response.status);
          console.error('🔍 [StrategyApprovalDebug] Error response data:', axiosError.response.data);
          console.error('🔍 [StrategyApprovalDebug] Error response headers:', axiosError.response.headers);
        } else if (axiosError.request) {
          console.error('🔍 [StrategyApprovalDebug] No response received:', axiosError.request);
        } else {
          console.error('🔍 [StrategyApprovalDebug] Request setup error:', axiosError.message || String(error));
        }

        throw error;
      }
    },
    onMutate: (variables) => {
      console.log('🟡 [StrategyApprovalDebug] Mutation starting...', variables);
    },
    onSuccess: (data, variables) => {
      console.log('🎉 [StrategyApprovalDebug] Mutation successful!', { data, variables });
      toast.success(`Strategy ${variables.action === 'approve' ? 'approved' : variables.action === 'reject' ? 'rejected' : 'returned for changes'} successfully`);
      queryClient.invalidateQueries({ queryKey: ['admin-pending-strategies'] });
      queryClient.invalidateQueries({ queryKey: ['admin-review-stats'] });
      setReviewDialogOpen(false);
      setSelectedStrategy(null);
      setReviewComment('');
    },
    onError: (error: any, variables) => {
      console.error('💥 [StrategyApprovalDebug] Mutation failed!', { error, variables });
      console.error('💥 [StrategyApprovalDebug] Full error object:', JSON.stringify(error, null, 2));

      let errorMessage = 'Failed to process review';
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }

      console.error('💥 [StrategyApprovalDebug] Showing error toast:', errorMessage);
      toast.error(errorMessage);
    },
    onSettled: (data, error, variables) => {
      console.log('🏁 [StrategyApprovalDebug] Mutation completed (settled)', { data, error, variables });
    }
  });

  const handleReviewStrategy = (strategy: PendingStrategy, action: 'approve' | 'reject' | 'request_changes') => {
    console.log('🎯 [StrategyApprovalDebug] handleReviewStrategy called', {
      strategyId: strategy.id,
      strategyName: strategy.name,
      action,
      currentReviewAction: reviewAction,
      dialogOpen: reviewDialogOpen,
      timestamp: new Date().toISOString()
    });

    setSelectedStrategy(strategy);
    setReviewAction(action);
    setReviewDialogOpen(true);

    console.log('🎯 [StrategyApprovalDebug] State updated after handleReviewStrategy', {
      selectedStrategyId: strategy.id,
      reviewAction: action,
      reviewDialogOpen: true
    });
  };

  const submitReview = () => {
    console.log('🚀 [StrategyApprovalDebug] submitReview called', {
      selectedStrategy: selectedStrategy?.id,
      selectedStrategyName: selectedStrategy?.name,
      reviewAction,
      reviewComment,
      mutationPending: reviewStrategyMutation.isPending,
      timestamp: new Date().toISOString()
    });

    if (!selectedStrategy) {
      console.error('❌ [StrategyApprovalDebug] No selectedStrategy found - cannot proceed');
      toast.error('No strategy selected. Please try again.');
      return;
    }

    const mutationData = {
      strategyId: selectedStrategy.id,
      action: reviewAction,
      comment: reviewComment
    };

    console.log('📤 [StrategyApprovalDebug] About to call reviewStrategyMutation.mutate with:', mutationData);

    try {
      reviewStrategyMutation.mutate(mutationData);
      console.log('✅ [StrategyApprovalDebug] reviewStrategyMutation.mutate called successfully');
    } catch (error: unknown) {
      console.error('💥 [StrategyApprovalDebug] reviewStrategyMutation.mutate threw error:', error);
    }
  };

  const getStatusColor = (status: PendingStrategy['status']) => {
    switch (status) {
      case 'submitted': return 'bg-blue-500';
      case 'under_review': return 'bg-yellow-500';
      case 'changes_requested': return 'bg-orange-500';
      case 'approved':
      case 'published':
        return 'bg-green-500';
      case 'rejected': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: PendingStrategy['status']) => {
    switch (status) {
      case 'submitted': return <Upload className="h-4 w-4" />;
      case 'under_review': return <Clock className="h-4 w-4" />;
      case 'changes_requested': return <Edit className="h-4 w-4" />;
      case 'approved':
      case 'published':
        return <CheckCircle className="h-4 w-4" />;
      case 'rejected': return <XCircle className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  const getStatusLabel = (status: PendingStrategy['status']) => {
    if (status === 'published') {
      return 'Published';
    }
    return status.replace('_', ' ').toUpperCase();
  };

  const getPriorityColor = (score: number) => {
    if (score >= 85) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const filteredStrategies = strategies?.filter(strategy =>
    strategy.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    strategy.publisher_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    strategy.category.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // Log current state for debugging
  console.log('🔍 [StrategyApprovalDebug] Current component state:', {
    selectedStatus,
    searchQuery,
    selectedStrategyId: selectedStrategy?.id,
    reviewDialogOpen,
    reviewAction,
    reviewComment,
    strategiesCount: strategies?.length || 0,
    filteredStrategiesCount: filteredStrategies.length,
    statsLoading,
    strategiesLoading,
    mutationPending: reviewStrategyMutation.isPending
  });

  if (statsError || strategiesError) {
    console.error('❌ [StrategyApprovalDebug] Component errors:', { statsError, strategiesError });

    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="text-center p-12">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load Strategy Reviews</h3>
            <p className="text-muted-foreground mb-4">
              Unable to fetch strategy approval data. Check console for detailed errors.
            </p>
            <div className="mb-4 p-4 bg-red-50 rounded-lg text-left">
              <p className="text-sm font-medium">Debug Information:</p>
              <p className="text-xs text-red-600">Stats Error: {statsError ? String(statsError) : 'None'}</p>
              <p className="text-xs text-red-600">Strategies Error: {strategiesError ? String(strategiesError) : 'None'}</p>
            </div>
            <Button onClick={() => {
              console.log('🔄 [StrategyApprovalDebug] Retry button clicked - invalidating queries');
              queryClient.invalidateQueries();
            }}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Debug Information Card */}
      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle className="text-blue-800">🐛 Debug Mode Active</CardTitle>
          <CardDescription className="text-blue-600">
            Enhanced logging enabled. Check browser console for detailed information.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <strong>API Base URL:</strong> {import.meta.env.VITE_API_URL || 'Default'}
            </div>
            <div>
              <strong>Environment:</strong> {import.meta.env.VITE_ENV || 'development'}
            </div>
            <div>
              <strong>Strategies Loaded:</strong> {strategies?.length || 0}
            </div>
            <div>
              <strong>Mutation Status:</strong> {reviewStrategyMutation.isPending ? 'Pending' : 'Idle'}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold tracking-tight">Strategy Approval (Debug Mode)</h3>
          <p className="text-muted-foreground">
            Review and approve submitted strategies for publication - with enhanced debugging
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => {
            console.log('🔄 [StrategyApprovalDebug] Refresh button clicked');
            queryClient.invalidateQueries();
          }}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Review Stats */}
      {!statsLoading && stats && (
        <div className="grid gap-4 md:grid-cols-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Pending</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.total_pending}</p>
                </div>
                <FileText className="h-6 w-6 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Under Review</p>
                  <p className="text-2xl font-bold text-yellow-600">{stats.under_review}</p>
                </div>
                <Clock className="h-6 w-6 text-yellow-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Approved Today</p>
                  <p className="text-2xl font-bold text-green-600">{stats.approved_today}</p>
                </div>
                <CheckCircle className="h-6 w-6 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Rejected Today</p>
                  <p className="text-2xl font-bold text-red-600">{stats.rejected_today}</p>
                </div>
                <XCircle className="h-6 w-6 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Avg Review Time</p>
                  <p className="text-2xl font-bold">{stats.avg_review_time_hours}h</p>
                </div>
                <Activity className="h-6 w-6 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">My Assigned</p>
                  <p className="text-2xl font-bold text-purple-600">{stats.my_assigned}</p>
                </div>
                <User className="h-6 w-6 text-purple-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search strategies..."
                value={searchQuery}
                onChange={(e) => {
                  console.log('🔍 [StrategyApprovalDebug] Search query changed:', e.target.value);
                  setSearchQuery(e.target.value);
                }}
                className="pl-9"
              />
            </div>

            <Select value={selectedStatus} onValueChange={(value) => {
              console.log('🔍 [StrategyApprovalDebug] Status filter changed:', value);
              setSelectedStatus(value);
            }}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="submitted">Submitted</SelectItem>
                <SelectItem value="under_review">Under Review</SelectItem>
                <SelectItem value="changes_requested">Changes Requested</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="published">Published</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="all">All Strategies</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Strategies List */}
      <div className="space-y-4">
        {strategiesLoading ? (
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
        ) : filteredStrategies.length === 0 ? (
          <Card>
            <CardContent className="text-center p-12">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Strategies Found</h3>
              <p className="text-muted-foreground mb-4">
                {searchQuery || selectedStatus !== 'all'
                  ? 'No strategies match your search criteria.'
                  : 'No strategies are currently pending review.'
                }
              </p>
              <p className="text-xs text-blue-600">
                Debug: Total strategies loaded: {strategies?.length || 0}
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredStrategies.map((strategy) => (
            <Card key={strategy.id} className="relative">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-semibold text-lg">{strategy.name}</h4>
                      <div className={`p-1 rounded-full ${getStatusColor(strategy.status)}`}>
                        {getStatusIcon(strategy.status)}
                      </div>
                      <Badge className={getStatusColor(strategy.status) + ' text-white'}>
                        {getStatusLabel(strategy.status)}
                      </Badge>
                      <Badge variant="outline" className="text-xs text-blue-600">
                        ID: {strategy.id}
                      </Badge>
                    </div>

                    <p className="text-sm text-muted-foreground mb-3">{strategy.description}</p>

                    <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3" />
                        {strategy.publisher_name}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        Submitted {formatRelativeTime(new Date(strategy.submitted_at))}
                      </span>
                      <span className="flex items-center gap-1">
                        <Target className="h-3 w-3" />
                        {strategy.category}
                      </span>
                      <Badge variant="outline">{strategy.complexity_level}</Badge>
                    </div>

                    {/* Performance Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-4">
                      <div>
                        <span className="text-muted-foreground">Return:</span>
                        <span className={`ml-2 font-medium ${strategy.backtest_results.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercentage(strategy.backtest_results.total_return)}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Sharpe:</span>
                        <span className="ml-2 font-medium">{strategy.backtest_results.sharpe_ratio.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Win Rate:</span>
                        <span className="ml-2 font-medium text-green-600">
                          {formatPercentage(strategy.backtest_results.win_rate)}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Trades:</span>
                        <span className="ml-2 font-medium">{strategy.backtest_results.total_trades}</span>
                      </div>
                    </div>

                    {/* Validation Score */}
                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between text-sm">
                        <span>Overall Quality Score</span>
                        <span className={`font-medium ${getPriorityColor(strategy.validation_results.overall_score)}`}>
                          {strategy.validation_results.overall_score}/100
                        </span>
                      </div>
                      <Progress value={strategy.validation_results.overall_score} />

                      {strategy.validation_results.issues.length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          {strategy.validation_results.issues.filter(i => i.type === 'error').length} errors, {' '}
                          {strategy.validation_results.issues.filter(i => i.type === 'warning').length} warnings
                        </div>
                      )}
                    </div>

                    {/* Pricing */}
                    <div className="text-sm mb-4">
                      <span className="text-muted-foreground">Pricing:</span>
                      {strategy.pricing_model === 'profit_share' ? (
                        <span className="ml-2 font-medium text-blue-600">
                          {strategy.profit_share_percentage}% profit share
                        </span>
                      ) : strategy.pricing_model === 'free' ? (
                        <span className="ml-2 font-medium text-green-600">Free</span>
                      ) : (
                        <span className="ml-2 font-medium">
                          {formatCurrency(strategy.price_amount || 0)} ({strategy.pricing_model.replace('_', ' ')})
                        </span>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          console.log('👁️ [StrategyApprovalDebug] View Details clicked for strategy:', strategy.id);
                          setSelectedStrategy(strategy);
                          setDetailsDialogOpen(true);
                        }}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        View Details
                      </Button>

                      {strategy.status === 'submitted' || strategy.status === 'under_review' ? (
                        <>
                          <Button
                            size="sm"
                            onClick={() => {
                              console.log('✅ [StrategyApprovalDebug] Approve button clicked for strategy:', strategy.id, strategy.name);
                              handleReviewStrategy(strategy, 'approve');
                            }}
                            className="bg-green-600 hover:bg-green-700"
                            disabled={reviewStrategyMutation.isPending}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            {reviewStrategyMutation.isPending ? 'Processing...' : 'Approve'}
                          </Button>

                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              console.log('📝 [StrategyApprovalDebug] Request Changes clicked for strategy:', strategy.id);
                              handleReviewStrategy(strategy, 'request_changes');
                            }}
                            disabled={reviewStrategyMutation.isPending}
                          >
                            <Edit className="h-4 w-4 mr-1" />
                            Request Changes
                          </Button>

                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              console.log('❌ [StrategyApprovalDebug] Reject button clicked for strategy:', strategy.id);
                              handleReviewStrategy(strategy, 'reject');
                            }}
                            className="border-red-200 text-red-600 hover:bg-red-50"
                            disabled={reviewStrategyMutation.isPending}
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Reject
                          </Button>
                        </>
                      ) : strategy.status === 'changes_requested' ? (
                        <Badge variant="outline" className="text-orange-600">
                          Waiting for publisher response
                        </Badge>
                      ) : (
                        <Badge
                          variant="outline"
                          className={
                            strategy.status === 'approved' || strategy.status === 'published'
                              ? 'text-green-600'
                              : 'text-red-600'
                          }
                        >
                          {strategy.status === 'published'
                            ? 'Published'
                            : strategy.status === 'approved'
                              ? 'Approved'
                              : 'Rejected'}
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Priority Indicator */}
                  <div className="text-right">
                    <div className={`text-2xl font-bold ${getPriorityColor(strategy.validation_results.overall_score)}`}>
                      {strategy.validation_results.overall_score}
                    </div>
                    <div className="text-xs text-muted-foreground">Quality Score</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Review Dialog */}
      <Dialog open={reviewDialogOpen} onOpenChange={(open) => {
        console.log('🔄 [StrategyApprovalDebug] Review dialog open changed:', open);
        setReviewDialogOpen(open);
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {reviewAction === 'approve' ? 'Approve Strategy' :
               reviewAction === 'reject' ? 'Reject Strategy' : 'Request Changes'}
            </DialogTitle>
            <DialogDescription>
              {selectedStrategy && (
                <>
                  Review "{selectedStrategy.name}" by {selectedStrategy.publisher_name}
                  <br />
                  <span className="text-xs text-blue-600">Strategy ID: {selectedStrategy.id}</span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          {selectedStrategy && (
            <div className="space-y-4">
              {/* Strategy Summary */}
              <Card>
                <CardContent className="p-4">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Overall Score:</span>
                      <span className={`font-medium ${getPriorityColor(selectedStrategy.validation_results.overall_score)}`}>
                        {selectedStrategy.validation_results.overall_score}/100
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Security Score:</span>
                      <span className="font-medium">{selectedStrategy.validation_results.security_score}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Performance Score:</span>
                      <span className="font-medium">{selectedStrategy.validation_results.performance_score}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Code Quality Score:</span>
                      <span className="font-medium">{selectedStrategy.validation_results.code_quality_score}/100</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Debug Information */}
              <Card className="border-blue-200 bg-blue-50">
                <CardContent className="p-4">
                  <div className="text-xs space-y-1">
                    <div><strong>Action:</strong> {reviewAction}</div>
                    <div><strong>Mutation Status:</strong> {reviewStrategyMutation.isPending ? 'Pending' : 'Ready'}</div>
                    <div><strong>Dialog Open:</strong> {reviewDialogOpen ? 'Yes' : 'No'}</div>
                    <div><strong>Comment Length:</strong> {reviewComment.length} chars</div>
                  </div>
                </CardContent>
              </Card>

              {/* Review Comment */}
              <div className="space-y-2">
                <Label htmlFor="review-comment">
                  {reviewAction === 'approve' ? 'Approval Notes (Optional)' :
                   reviewAction === 'reject' ? 'Rejection Reason *' : 'Change Requests *'}
                </Label>
                <Textarea
                  id="review-comment"
                  placeholder={
                    reviewAction === 'approve' ? 'Add any notes about the approval...' :
                    reviewAction === 'reject' ? 'Explain why this strategy is being rejected...' :
                    'Describe what changes are needed...'
                  }
                  value={reviewComment}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => {
                    console.log('💬 [StrategyApprovalDebug] Review comment changed:', e.target.value.length, 'characters');
                    setReviewComment(e.target.value);
                  }}
                  rows={4}
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => {
              console.log('❌ [StrategyApprovalDebug] Cancel button clicked in dialog');
              setReviewDialogOpen(false);
            }}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                console.log('🚀 [StrategyApprovalDebug] Submit button clicked in dialog');
                submitReview();
              }}
              disabled={reviewStrategyMutation.isPending || (reviewAction !== 'approve' && !reviewComment.trim())}
              className={
                reviewAction === 'approve' ? 'bg-green-600 hover:bg-green-700' :
                reviewAction === 'reject' ? 'bg-red-600 hover:bg-red-700' :
                'bg-orange-600 hover:bg-orange-700'
              }
            >
              {reviewStrategyMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : reviewAction === 'approve' ? (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Approve Strategy
                </>
              ) : reviewAction === 'reject' ? (
                <>
                  <XCircle className="h-4 w-4 mr-2" />
                  Reject Strategy
                </>
              ) : (
                <>
                  <Edit className="h-4 w-4 mr-2" />
                  Request Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Details Dialog - Simplified for space */}
      <Dialog open={detailsDialogOpen} onOpenChange={setDetailsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Strategy Details (Debug)</DialogTitle>
            <DialogDescription>
              {selectedStrategy && (
                <>Complete information for "{selectedStrategy.name}" (ID: {selectedStrategy.id})</>
              )}
            </DialogDescription>
          </DialogHeader>

          {selectedStrategy && (
            <div className="space-y-4 max-h-96 overflow-y-auto">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Basic Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div><strong>ID:</strong> {selectedStrategy.id}</div>
                  <div><strong>Name:</strong> {selectedStrategy.name}</div>
                  <div><strong>Publisher:</strong> {selectedStrategy.publisher_name}</div>
                  <div><strong>Category:</strong> {selectedStrategy.category}</div>
                  <div><strong>Status:</strong> {selectedStrategy.status}</div>
                  <div><strong>Risk Level:</strong> {selectedStrategy.risk_level}</div>
                  <div><strong>Complexity:</strong> {selectedStrategy.complexity_level}</div>
                </CardContent>
              </Card>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailsDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default StrategyApprovalDebug;