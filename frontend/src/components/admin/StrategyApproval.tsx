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
  status: 'submitted' | 'under_review' | 'changes_requested' | 'approved' | 'rejected';
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

const StrategyApproval: React.FC = () => {
  const [selectedStatus, setSelectedStatus] = useState<string>('submitted');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState<PendingStrategy | null>(null);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject' | 'request_changes'>('approve');
  const [reviewComment, setReviewComment] = useState('');
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);

  const queryClient = useQueryClient();

  // Fetch review statistics
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['admin-review-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/admin/strategies/review-stats');
      return response.data as ReviewStats;
    },
    refetchInterval: 60000
  });

  // Fetch pending strategies
  const { data: strategies, isLoading: strategiesLoading, error: strategiesError } = useQuery({
    queryKey: ['admin-pending-strategies', selectedStatus],
    queryFn: async () => {
      const response = await apiClient.get('/admin/strategies/pending', {
        params: { status: selectedStatus !== 'all' ? selectedStatus : undefined }
      });
      return response.data.strategies as PendingStrategy[];
    },
    refetchInterval: 30000
  });

  // Review strategy mutation
  const reviewStrategyMutation = useMutation({
    mutationFn: async (data: {
      strategyId: string;
      action: 'approve' | 'reject' | 'request_changes';
      comment?: string;
    }) => {
      const response = await apiClient.post(`/admin/strategies/${data.strategyId}/review`, {
        action: data.action,
        comment: data.comment
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      toast.success(`Strategy ${variables.action === 'approve' ? 'approved' : variables.action === 'reject' ? 'rejected' : 'returned for changes'} successfully`);
      queryClient.invalidateQueries({ queryKey: ['admin-pending-strategies'] });
      queryClient.invalidateQueries({ queryKey: ['admin-review-stats'] });
      setReviewDialogOpen(false);
      setSelectedStrategy(null);
      setReviewComment('');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to process review');
    }
  });

  // Assign strategy mutation
  const assignStrategyMutation = useMutation({
    mutationFn: async (data: { strategyId: string; reviewerId: string }) => {
      const response = await apiClient.post(`/admin/strategies/${data.strategyId}/assign`, {
        reviewer_id: data.reviewerId
      });
      return response.data;
    },
    onSuccess: () => {
      toast.success('Strategy assigned successfully');
      queryClient.invalidateQueries({ queryKey: ['admin-pending-strategies'] });
      queryClient.invalidateQueries({ queryKey: ['admin-review-stats'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to assign strategy');
    }
  });

  const getStatusColor = (status: PendingStrategy['status']) => {
    switch (status) {
      case 'submitted': return 'bg-blue-500';
      case 'under_review': return 'bg-yellow-500';
      case 'changes_requested': return 'bg-orange-500';
      case 'approved': return 'bg-green-500';
      case 'rejected': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: PendingStrategy['status']) => {
    switch (status) {
      case 'submitted': return <Upload className="h-4 w-4" />;
      case 'under_review': return <Clock className="h-4 w-4" />;
      case 'changes_requested': return <Edit className="h-4 w-4" />;
      case 'approved': return <CheckCircle className="h-4 w-4" />;
      case 'rejected': return <XCircle className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
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

  const handleReviewStrategy = (strategy: PendingStrategy, action: 'approve' | 'reject' | 'request_changes') => {
    setSelectedStrategy(strategy);
    setReviewAction(action);
    setReviewDialogOpen(true);
  };

  const handleViewDetails = (strategy: PendingStrategy) => {
    setSelectedStrategy(strategy);
    setDetailsDialogOpen(true);
  };

  const submitReview = () => {
    if (!selectedStrategy) return;
    
    reviewStrategyMutation.mutate({
      strategyId: selectedStrategy.id,
      action: reviewAction,
      comment: reviewComment
    });
  };

  if (statsError || strategiesError) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="text-center p-12">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load Strategy Reviews</h3>
            <p className="text-muted-foreground mb-4">
              Unable to fetch strategy approval data. Please try again.
            </p>
            <Button onClick={() => queryClient.invalidateQueries()}>
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold tracking-tight">Strategy Approval</h3>
          <p className="text-muted-foreground">
            Review and approve submitted strategies for publication
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={() => queryClient.invalidateQueries()}>
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
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="submitted">Submitted</SelectItem>
                <SelectItem value="under_review">Under Review</SelectItem>
                <SelectItem value="changes_requested">Changes Requested</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
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
              <p className="text-muted-foreground">
                {searchQuery || selectedStatus !== 'all' 
                  ? 'No strategies match your search criteria.'
                  : 'No strategies are currently pending review.'
                }
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
                        {strategy.status.replace('_', ' ').toUpperCase()}
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
                        onClick={() => handleViewDetails(strategy)}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        View Details
                      </Button>
                      
                      {strategy.status === 'submitted' || strategy.status === 'under_review' ? (
                        <>
                          <Button
                            size="sm"
                            onClick={() => handleReviewStrategy(strategy, 'approve')}
                            className="bg-green-600 hover:bg-green-700"
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Approve
                          </Button>
                          
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleReviewStrategy(strategy, 'request_changes')}
                          >
                            <Edit className="h-4 w-4 mr-1" />
                            Request Changes
                          </Button>
                          
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleReviewStrategy(strategy, 'reject')}
                            className="border-red-200 text-red-600 hover:bg-red-50"
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
                        <Badge variant="outline" className={
                          strategy.status === 'approved' ? 'text-green-600' : 'text-red-600'
                        }>
                          {strategy.status === 'approved' ? 'Approved' : 'Rejected'}
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
      <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
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
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setReviewComment(e.target.value)}
                  rows={4}
                />
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setReviewDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={submitReview}
              disabled={reviewStrategyMutation.isPending || (reviewAction !== 'approve' && !reviewComment.trim())}
              className={
                reviewAction === 'approve' ? 'bg-green-600 hover:bg-green-700' :
                reviewAction === 'reject' ? 'bg-red-600 hover:bg-red-700' :
                'bg-orange-600 hover:bg-orange-700'
              }
            >
              {reviewStrategyMutation.isPending ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : reviewAction === 'approve' ? (
                <CheckCircle className="h-4 w-4 mr-2" />
              ) : reviewAction === 'reject' ? (
                <XCircle className="h-4 w-4 mr-2" />
              ) : (
                <Edit className="h-4 w-4 mr-2" />
              )}
              {reviewAction === 'approve' ? 'Approve Strategy' :
               reviewAction === 'reject' ? 'Reject Strategy' : 'Request Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Strategy Details Dialog */}
      <Dialog open={detailsDialogOpen} onOpenChange={setDetailsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Strategy Details</DialogTitle>
            <DialogDescription>
              {selectedStrategy && (
                <>Complete information for "{selectedStrategy.name}"</>
              )}
            </DialogDescription>
          </DialogHeader>
          
          {selectedStrategy && (
            <Tabs defaultValue="overview" className="space-y-4">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="performance">Performance</TabsTrigger>
                <TabsTrigger value="validation">Validation</TabsTrigger>
                <TabsTrigger value="documentation">Documentation</TabsTrigger>
                <TabsTrigger value="history">Review History</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Basic Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Publisher:</span>
                        <span className="font-medium">{selectedStrategy.publisher_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Category:</span>
                        <span className="font-medium">{selectedStrategy.category}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Risk Level:</span>
                        <span className="font-medium capitalize">{selectedStrategy.risk_level}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Complexity:</span>
                        <span className="font-medium capitalize">{selectedStrategy.complexity_level}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Required Capital:</span>
                        <span className="font-medium">{formatCurrency(selectedStrategy.required_capital)}</span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Trading Configuration</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Max Positions:</span>
                        <span className="font-medium">{selectedStrategy.max_positions}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Trading Pairs:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {selectedStrategy.trading_pairs.map((pair, i) => (
                            <Badge key={i} variant="outline" className="text-xs">{pair}</Badge>
                          ))}
                        </div>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Timeframes:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {selectedStrategy.timeframes.map((tf, i) => (
                            <Badge key={i} variant="outline" className="text-xs">{tf}</Badge>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Description</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm">{selectedStrategy.description}</p>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="performance" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Backtest Results</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total Return:</span>
                        <span className={`font-bold ${selectedStrategy.backtest_results.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercentage(selectedStrategy.backtest_results.total_return)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Sharpe Ratio:</span>
                        <span className="font-medium">{selectedStrategy.backtest_results.sharpe_ratio.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Max Drawdown:</span>
                        <span className="font-medium text-red-600">
                          {formatPercentage(selectedStrategy.backtest_results.max_drawdown)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Win Rate:</span>
                        <span className="font-medium text-green-600">
                          {formatPercentage(selectedStrategy.backtest_results.win_rate)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total Trades:</span>
                        <span className="font-medium">{selectedStrategy.backtest_results.total_trades}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Profit Factor:</span>
                        <span className="font-medium">{selectedStrategy.backtest_results.profit_factor.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Volatility:</span>
                        <span className="font-medium">{formatPercentage(selectedStrategy.backtest_results.volatility)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Test Period:</span>
                        <span className="font-medium">{selectedStrategy.backtest_results.period_days} days</span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Risk Assessment</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Risk Level</span>
                          <Badge variant="outline" className={
                            selectedStrategy.risk_level === 'low' ? 'text-green-600' :
                            selectedStrategy.risk_level === 'medium' ? 'text-yellow-600' : 'text-red-600'
                          }>
                            {selectedStrategy.risk_level.toUpperCase()}
                          </Badge>
                        </div>
                        <Progress 
                          value={
                            selectedStrategy.risk_level === 'low' ? 25 :
                            selectedStrategy.risk_level === 'medium' ? 50 : 75
                          } 
                        />
                      </div>
                      
                      <div className="text-xs text-muted-foreground">
                        Risk assessment based on volatility, drawdown, and trading frequency
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="validation" className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Quality Scores</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Overall Score</span>
                          <span className={`font-bold ${getPriorityColor(selectedStrategy.validation_results.overall_score)}`}>
                            {selectedStrategy.validation_results.overall_score}/100
                          </span>
                        </div>
                        <Progress value={selectedStrategy.validation_results.overall_score} />
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Security Score</span>
                          <span className="font-medium">{selectedStrategy.validation_results.security_score}/100</span>
                        </div>
                        <Progress value={selectedStrategy.validation_results.security_score} />
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Performance Score</span>
                          <span className="font-medium">{selectedStrategy.validation_results.performance_score}/100</span>
                        </div>
                        <Progress value={selectedStrategy.validation_results.performance_score} />
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Code Quality Score</span>
                          <span className="font-medium">{selectedStrategy.validation_results.code_quality_score}/100</span>
                        </div>
                        <Progress value={selectedStrategy.validation_results.code_quality_score} />
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Validation Issues</CardTitle>
                    </CardHeader>
                    <CardContent>
                      {selectedStrategy.validation_results.issues.length === 0 ? (
                        <div className="text-center py-4 text-green-600">
                          <CheckCircle className="h-8 w-8 mx-auto mb-2" />
                          <div className="text-sm">No validation issues found</div>
                        </div>
                      ) : (
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                          {selectedStrategy.validation_results.issues.map((issue, i) => (
                            <div key={i} className={`p-2 rounded text-xs border ${
                              issue.type === 'error' ? 'border-red-200 bg-red-50 text-red-700' :
                              issue.type === 'warning' ? 'border-yellow-200 bg-yellow-50 text-yellow-700' :
                              'border-blue-200 bg-blue-50 text-blue-700'
                            }`}>
                              <div className="flex items-center gap-1 mb-1">
                                <Badge variant="outline" className="text-xs">
                                  {issue.type.toUpperCase()}
                                </Badge>
                                <Badge variant="outline" className="text-xs">
                                  {issue.severity.toUpperCase()}
                                </Badge>
                                {issue.line && (
                                  <span className="text-xs text-muted-foreground">Line {issue.line}</span>
                                )}
                              </div>
                              <div>{issue.message}</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="documentation" className="space-y-4">
                <div className="space-y-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">README</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-sm whitespace-pre-wrap font-mono text-xs bg-muted p-4 rounded max-h-64 overflow-y-auto">
                        {selectedStrategy.documentation.readme || 'No README provided'}
                      </div>
                    </CardContent>
                  </Card>

                  {selectedStrategy.documentation.changelog && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Changelog</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-sm whitespace-pre-wrap font-mono text-xs bg-muted p-4 rounded max-h-32 overflow-y-auto">
                          {selectedStrategy.documentation.changelog}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="history" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Review History</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {selectedStrategy.review_history.length === 0 ? (
                      <div className="text-center py-4 text-muted-foreground">
                        <Clock className="h-8 w-8 mx-auto mb-2" />
                        <div className="text-sm">No review history yet</div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {selectedStrategy.review_history.map((entry, i) => (
                          <div key={i} className="flex items-start gap-3 p-3 bg-muted/50 rounded">
                            <div className={`p-1 rounded-full ${
                              entry.action === 'approved' ? 'bg-green-500' :
                              entry.action === 'rejected' ? 'bg-red-500' :
                              entry.action === 'changes_requested' ? 'bg-orange-500' :
                              'bg-blue-500'
                            }`}>
                              {entry.action === 'approved' && <CheckCircle className="h-3 w-3 text-white" />}
                              {entry.action === 'rejected' && <XCircle className="h-3 w-3 text-white" />}
                              {entry.action === 'changes_requested' && <Edit className="h-3 w-3 text-white" />}
                              {(entry.action === 'assigned' || entry.action === 'reviewed') && <User className="h-3 w-3 text-white" />}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center justify-between">
                                <div className="font-medium text-sm">
                                  {entry.action.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {formatRelativeTime(new Date(entry.timestamp))}
                                </div>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                by {entry.reviewer}
                              </div>
                              {entry.comment && (
                                <div className="text-sm mt-1 p-2 bg-background rounded">
                                  {entry.comment}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
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

export default StrategyApproval;