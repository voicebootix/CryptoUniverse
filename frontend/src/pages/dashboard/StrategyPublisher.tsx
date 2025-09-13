import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Upload,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  Eye,
  DollarSign,
  Percent,
  TrendingUp,
  Shield,
  FileText,
  Settings,
  Send,
  Edit,
  Trash2,
  Copy,
  Star,
  Award,
  Users,
  Activity,
  Calendar,
  BookOpen,
  Lightbulb,
  Target,
  Zap,
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
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber, formatRelativeTime } from '@/lib/utils';

interface StrategySubmission {
  id: string;
  name: string;
  description: string;
  category: string;
  risk_level: 'low' | 'medium' | 'high';
  expected_return_range: [number, number];
  required_capital: number;
  pricing_model: 'free' | 'one_time' | 'subscription' | 'profit_share';
  price_amount?: number;
  profit_share_percentage?: number;
  status: 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected' | 'published';
  created_at: string;
  submitted_at?: string;
  reviewed_at?: string;
  published_at?: string;
  reviewer_feedback?: string;
  rejection_reason?: string;
  
  // Strategy Performance Data
  backtest_results: {
    total_return: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    total_trades: number;
    profit_factor: number;
    period_days: number;
  };
  
  // Validation Results
  validation_results: {
    is_valid: boolean;
    security_score: number;
    performance_score: number;
    code_quality_score: number;
    overall_score: number;
  };
  
  // Publishing Details
  tags: string[];
  target_audience: string[];
  complexity_level: 'beginner' | 'intermediate' | 'advanced';
  documentation_quality: number;
  support_level: 'basic' | 'standard' | 'premium';
}

interface PublishingRequirements {
  min_backtest_period: number;
  min_sharpe_ratio: number;
  min_win_rate: number;
  max_drawdown: number;
  min_total_trades: number;
  min_security_score: number;
  min_code_quality_score: number;
  min_overall_score: number;
  required_documentation: string[];
}

const StrategyPublisher: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState<'submissions' | 'create' | 'requirements'>('submissions');
  const [selectedSubmission, setSelectedSubmission] = useState<string | null>(null);
  
  // Form state for new submission
  const [submissionForm, setSubmissionForm] = useState({
    name: '',
    description: '',
    category: 'algorithmic',
    risk_level: 'medium' as 'low' | 'medium' | 'high',
    expected_return_range: [0, 0] as [number, number],
    required_capital: 1000,
    pricing_model: 'profit_share' as 'free' | 'one_time' | 'subscription' | 'profit_share',
    price_amount: 0,
    profit_share_percentage: 25,
    tags: [] as string[],
    target_audience: [] as string[],
    complexity_level: 'intermediate' as 'beginner' | 'intermediate' | 'advanced',
    support_level: 'standard' as 'basic' | 'standard' | 'premium'
  });

  const queryClient = useQueryClient();

  // Fetch user's strategy submissions
  const { data: submissions, isLoading: submissionsLoading, error: submissionsError } = useQuery({
    queryKey: ['strategy-submissions'],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/publisher/submissions');
      return response.data.submissions as StrategySubmission[];
    },
    refetchInterval: 30000
  });

  // Fetch publishing requirements
  const { data: requirements, isLoading: requirementsLoading } = useQuery({
    queryKey: ['publishing-requirements'],
    queryFn: async () => {
      const response = await apiClient.get('/strategies/publisher/requirements');
      return response.data.requirements as PublishingRequirements;
    }
  });

  // Submit strategy for review
  const submitStrategyMutation = useMutation({
    mutationFn: async (data: typeof submissionForm & { strategy_id: string }) => {
      const response = await apiClient.post('/strategies/publisher/submit', data);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Strategy submitted for review successfully');
      queryClient.invalidateQueries({ queryKey: ['strategy-submissions'] });
      setSubmissionForm({
        name: '',
        description: '',
        category: 'algorithmic',
        risk_level: 'medium',
        expected_return_range: [0, 0],
        required_capital: 1000,
        pricing_model: 'profit_share',
        price_amount: 0,
        profit_share_percentage: 25,
        tags: [],
        target_audience: [],
        complexity_level: 'intermediate',
        support_level: 'standard'
      });
      setSelectedTab('submissions');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to submit strategy');
    }
  });

  // Withdraw submission
  const withdrawSubmissionMutation = useMutation({
    mutationFn: async (submissionId: string) => {
      const response = await apiClient.post(`/strategies/publisher/withdraw/${submissionId}`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Submission withdrawn successfully');
      queryClient.invalidateQueries({ queryKey: ['strategy-submissions'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to withdraw submission');
    }
  });

  // Update submission
  const updateSubmissionMutation = useMutation({
    mutationFn: async ({ submissionId, updates }: { submissionId: string; updates: Partial<StrategySubmission> }) => {
      const response = await apiClient.put(`/strategies/publisher/submissions/${submissionId}`, updates);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Submission updated successfully');
      queryClient.invalidateQueries({ queryKey: ['strategy-submissions'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to update submission');
    }
  });

  const getStatusColor = (status: StrategySubmission['status']) => {
    switch (status) {
      case 'draft': return 'bg-gray-500';
      case 'submitted': return 'bg-blue-500';
      case 'under_review': return 'bg-yellow-500';
      case 'approved': return 'bg-green-500';
      case 'rejected': return 'bg-red-500';
      case 'published': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status: StrategySubmission['status']) => {
    switch (status) {
      case 'draft': return <Edit className="h-4 w-4" />;
      case 'submitted': return <Send className="h-4 w-4" />;
      case 'under_review': return <Clock className="h-4 w-4" />;
      case 'approved': return <CheckCircle className="h-4 w-4" />;
      case 'rejected': return <XCircle className="h-4 w-4" />;
      case 'published': return <Globe className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  const handleSubmitStrategy = async () => {
    if (!submissionForm.name || !submissionForm.description) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    try {
      // This would be connected to a strategy ID from the IDE
      await submitStrategyMutation.mutateAsync({
        ...submissionForm,
        strategy_id: 'temp-strategy-id' // Would come from strategy IDE
      });
    } catch (error) {
      // Error handling is already in the mutation
      console.error('Submission failed:', error);
    }
  };

  const checkRequirementsMet = (submission: StrategySubmission, requirements: PublishingRequirements) => {
    if (!requirements) return false;
    
    const backtest = submission.backtest_results;
    const validation = submission.validation_results;
    
    return (
      backtest.period_days >= requirements.min_backtest_period &&
      backtest.sharpe_ratio >= requirements.min_sharpe_ratio &&
      backtest.win_rate >= requirements.min_win_rate &&
      backtest.max_drawdown <= requirements.max_drawdown &&
      backtest.total_trades >= requirements.min_total_trades &&
      validation.security_score >= requirements.min_security_score &&
      validation.code_quality_score >= requirements.min_code_quality_score &&
      validation.overall_score >= requirements.min_overall_score
    );
  };

  if (submissionsError) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="text-center p-12">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Failed to Load Submissions</h3>
            <p className="text-muted-foreground mb-4">
              {submissionsError instanceof Error ? submissionsError.message : 'Unable to fetch strategy submissions'}
            </p>
            <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['strategy-submissions'] })}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
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
          <h2 className="text-3xl font-bold tracking-tight">Strategy Publisher</h2>
          <p className="text-muted-foreground">
            Submit your trading strategies for review and earn from your published strategies
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['strategy-submissions'] })}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      <Tabs value={selectedTab} onValueChange={setSelectedTab as any} className="space-y-6">
        <TabsList>
          <TabsTrigger value="submissions">My Submissions</TabsTrigger>
          <TabsTrigger value="create">Submit New Strategy</TabsTrigger>
          <TabsTrigger value="requirements">Publishing Requirements</TabsTrigger>
        </TabsList>

        {/* My Submissions */}
        <TabsContent value="submissions" className="space-y-6">
          {submissionsLoading ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3].map(i => (
                <Card key={i}>
                  <CardContent className="p-6">
                    <div className="space-y-4 animate-pulse">
                      <div className="h-4 bg-muted rounded w-3/4" />
                      <div className="h-3 bg-muted rounded w-full" />
                      <div className="h-3 bg-muted rounded w-5/6" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : !submissions || submissions.length === 0 ? (
            <Card>
              <CardContent className="text-center p-12">
                <Upload className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Strategy Submissions</h3>
                <p className="text-muted-foreground mb-4">
                  You haven't submitted any strategies for review yet. Create your first strategy in the IDE and submit it for publication.
                </p>
                <Button onClick={() => setSelectedTab('create')}>
                  Submit Your First Strategy
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {submissions.map((submission) => (
                <Card key={submission.id} className="relative">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-lg">{submission.name}</CardTitle>
                        <CardDescription>{submission.description}</CardDescription>
                      </div>
                      <div className="flex items-center gap-2 ml-2">
                        <div className={`p-2 rounded-full ${getStatusColor(submission.status)}`}>
                          {getStatusIcon(submission.status)}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">{submission.category}</Badge>
                      <Badge variant="outline">{submission.risk_level} risk</Badge>
                      <Badge variant="outline">{submission.complexity_level}</Badge>
                    </div>
                  </CardHeader>
                  
                  <CardContent>
                    <div className="space-y-4">
                      {/* Performance Metrics */}
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="text-muted-foreground">Return:</span>
                          <span className="ml-2 font-medium text-green-500">
                            {formatPercentage(submission.backtest_results.total_return)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Sharpe:</span>
                          <span className="ml-2 font-medium">
                            {submission.backtest_results.sharpe_ratio.toFixed(2)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Win Rate:</span>
                          <span className="ml-2 font-medium text-green-500">
                            {formatPercentage(submission.backtest_results.win_rate)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Trades:</span>
                          <span className="ml-2 font-medium">
                            {submission.backtest_results.total_trades}
                          </span>
                        </div>
                      </div>

                      {/* Overall Score */}
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Overall Score</span>
                          <span className="font-medium">
                            {submission.validation_results.overall_score}/100
                          </span>
                        </div>
                        <Progress value={submission.validation_results.overall_score} />
                      </div>

                      {/* Pricing */}
                      <div className="text-sm">
                        {submission.pricing_model === 'profit_share' ? (
                          <span className="text-muted-foreground">
                            {submission.profit_share_percentage}% profit share
                          </span>
                        ) : submission.pricing_model === 'free' ? (
                          <span className="text-green-500">Free</span>
                        ) : (
                          <span className="text-muted-foreground">
                            {formatCurrency(submission.price_amount || 0)}
                          </span>
                        )}
                      </div>

                      {/* Status and Actions */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <Badge className={getStatusColor(submission.status) + ' text-white'}>
                            {submission.status.replace('_', ' ').toUpperCase()}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(new Date(submission.created_at))}
                          </span>
                        </div>

                        {/* Feedback/Rejection Reason */}
                        {submission.status === 'rejected' && submission.rejection_reason && (
                          <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                            <strong>Rejection Reason:</strong> {submission.rejection_reason}
                          </div>
                        )}

                        {submission.status === 'approved' && submission.reviewer_feedback && (
                          <div className="p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
                            <strong>Reviewer Feedback:</strong> {submission.reviewer_feedback}
                          </div>
                        )}

                        {/* Requirements Check */}
                        {requirements && (
                          <div className="text-xs">
                            {checkRequirementsMet(submission, requirements) ? (
                              <span className="text-green-500 flex items-center gap-1">
                                <CheckCircle className="h-3 w-3" />
                                Meets all requirements
                              </span>
                            ) : (
                              <span className="text-red-500 flex items-center gap-1">
                                <XCircle className="h-3 w-3" />
                                Does not meet requirements
                              </span>
                            )}
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex gap-2 pt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1"
                            onClick={() => setSelectedSubmission(submission.id)}
                          >
                            <Eye className="h-3 w-3 mr-1" />
                            View
                          </Button>
                          
                          {(submission.status === 'draft' || submission.status === 'rejected') && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                // Edit submission logic
                              }}
                            >
                              <Edit className="h-3 w-3 mr-1" />
                              Edit
                            </Button>
                          )}
                          
                          {submission.status === 'submitted' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => withdrawSubmissionMutation.mutate(submission.id)}
                              disabled={withdrawSubmissionMutation.isPending}
                            >
                              <Trash2 className="h-3 w-3 mr-1" />
                              Withdraw
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Submit New Strategy */}
        <TabsContent value="create" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Submit New Strategy for Review</CardTitle>
              <CardDescription>
                Fill out the details for your strategy submission. Ensure all requirements are met for faster approval.
              </CardDescription>
            </CardHeader>
            
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="strategy-name">Strategy Name *</Label>
                  <Input
                    id="strategy-name"
                    placeholder="e.g., Advanced Momentum Strategy"
                    value={submissionForm.name}
                    onChange={(e) => setSubmissionForm(prev => ({ ...prev, name: e.target.value }))}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Select
                    value={submissionForm.category}
                    onValueChange={(value) => setSubmissionForm(prev => ({ ...prev, category: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="algorithmic">Algorithmic</SelectItem>
                      <SelectItem value="momentum">Momentum</SelectItem>
                      <SelectItem value="mean_reversion">Mean Reversion</SelectItem>
                      <SelectItem value="arbitrage">Arbitrage</SelectItem>
                      <SelectItem value="scalping">Scalping</SelectItem>
                      <SelectItem value="swing">Swing Trading</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Strategy Description *</Label>
                <Textarea
                  id="description"
                  placeholder="Provide a detailed description of your strategy, its approach, and key features..."
                  rows={4}
                  value={submissionForm.description}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setSubmissionForm(prev => ({ ...prev, description: e.target.value }))}
                />
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Risk Level</Label>
                  <Select
                    value={submissionForm.risk_level}
                    onValueChange={(value: 'low' | 'medium' | 'high') => setSubmissionForm(prev => ({ ...prev, risk_level: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low Risk</SelectItem>
                      <SelectItem value="medium">Medium Risk</SelectItem>
                      <SelectItem value="high">High Risk</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Complexity Level</Label>
                  <Select
                    value={submissionForm.complexity_level}
                    onValueChange={(value: 'beginner' | 'intermediate' | 'advanced') => setSubmissionForm(prev => ({ ...prev, complexity_level: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="beginner">Beginner</SelectItem>
                      <SelectItem value="intermediate">Intermediate</SelectItem>
                      <SelectItem value="advanced">Advanced</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="required-capital">Required Capital (USD)</Label>
                  <Input
                    id="required-capital"
                    type="number"
                    value={submissionForm.required_capital}
                    onChange={(e) => setSubmissionForm(prev => ({ ...prev, required_capital: parseInt(e.target.value) || 0 }))}
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h4 className="font-medium">Pricing Model</h4>
                <Select
                  value={submissionForm.pricing_model}
                  onValueChange={(value: 'free' | 'one_time' | 'subscription' | 'profit_share') => setSubmissionForm(prev => ({ ...prev, pricing_model: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="free">Free Strategy</SelectItem>
                    <SelectItem value="one_time">One-time Purchase</SelectItem>
                    <SelectItem value="subscription">Monthly Subscription</SelectItem>
                    <SelectItem value="profit_share">Profit Sharing</SelectItem>
                  </SelectContent>
                </Select>

                {submissionForm.pricing_model === 'profit_share' && (
                  <div className="space-y-2">
                    <Label htmlFor="profit-share">Profit Share Percentage (%)</Label>
                    <Input
                      id="profit-share"
                      type="number"
                      min="1"
                      max="50"
                      value={submissionForm.profit_share_percentage}
                      onChange={(e) => setSubmissionForm(prev => ({ ...prev, profit_share_percentage: parseInt(e.target.value) || 25 }))}
                    />
                    <p className="text-xs text-muted-foreground">
                      Users will pay {submissionForm.profit_share_percentage}% of their profits from using your strategy
                    </p>
                  </div>
                )}

                {(submissionForm.pricing_model === 'one_time' || submissionForm.pricing_model === 'subscription') && (
                  <div className="space-y-2">
                    <Label htmlFor="price">
                      Price ({submissionForm.pricing_model === 'subscription' ? 'per month' : 'one-time'})
                    </Label>
                    <Input
                      id="price"
                      type="number"
                      min="1"
                      value={submissionForm.price_amount}
                      onChange={(e) => setSubmissionForm(prev => ({ ...prev, price_amount: parseFloat(e.target.value) || 0 }))}
                    />
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-6">
                <div className="text-sm text-muted-foreground">
                  * Required fields must be completed before submission
                </div>
                <Button
                  onClick={handleSubmitStrategy}
                  disabled={submitStrategyMutation.isPending || !submissionForm.name || !submissionForm.description}
                >
                  {submitStrategyMutation.isPending ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4 mr-2" />
                  )}
                  {submitStrategyMutation.isPending ? 'Submitting...' : 'Submit for Review'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Publishing Requirements */}
        <TabsContent value="requirements" className="space-y-6">
          {requirementsLoading ? (
            <Card>
              <CardContent className="p-6 space-y-4 animate-pulse">
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-3 bg-muted rounded w-full" />
                <div className="h-3 bg-muted rounded w-5/6" />
              </CardContent>
            </Card>
          ) : requirements ? (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-blue-500" />
                    Publishing Requirements
                  </CardTitle>
                  <CardDescription>
                    Your strategy must meet all these requirements to be approved for publication
                  </CardDescription>
                </CardHeader>
                
                <CardContent className="space-y-6">
                  <div className="grid gap-6 md:grid-cols-2">
                    {/* Performance Requirements */}
                    <div className="space-y-4">
                      <h4 className="font-medium flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-green-500" />
                        Performance Requirements
                      </h4>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Minimum Backtest Period:</span>
                          <span className="font-medium">{requirements.min_backtest_period} days</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Minimum Sharpe Ratio:</span>
                          <span className="font-medium">{requirements.min_sharpe_ratio}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Minimum Win Rate:</span>
                          <span className="font-medium">{formatPercentage(requirements.min_win_rate)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Maximum Drawdown:</span>
                          <span className="font-medium text-red-500">{formatPercentage(requirements.max_drawdown)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Minimum Total Trades:</span>
                          <span className="font-medium">{requirements.min_total_trades}</span>
                        </div>
                      </div>
                    </div>

                    {/* Quality Requirements */}
                    <div className="space-y-4">
                      <h4 className="font-medium flex items-center gap-2">
                        <Star className="h-4 w-4 text-yellow-500" />
                        Quality Requirements
                      </h4>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Minimum Security Score:</span>
                          <span className="font-medium">{requirements.min_security_score}/100</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Minimum Code Quality Score:</span>
                          <span className="font-medium">{requirements.min_code_quality_score}/100</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Minimum Overall Score:</span>
                          <span className="font-medium">{requirements.min_overall_score}/100</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* Documentation Requirements */}
                  <div className="space-y-4">
                    <h4 className="font-medium flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-purple-500" />
                      Required Documentation
                    </h4>
                    <div className="grid gap-2 md:grid-cols-2">
                      {requirements.required_documentation.map((doc, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span>{doc}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Lightbulb className="h-5 w-5 text-blue-500 mt-0.5" />
                      <div>
                        <h5 className="font-medium text-blue-900">Tips for Approval</h5>
                        <p className="text-sm text-blue-700 mt-1">
                          Strategies with comprehensive backtesting, clear documentation, and robust risk management 
                          have higher approval rates. Consider running extended backtests and including detailed 
                          explanations of your strategy's logic.
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardContent className="text-center p-12">
                <AlertTriangle className="h-12 w-12 text-orange-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Requirements Not Available</h3>
                <p className="text-muted-foreground">
                  Unable to load publishing requirements. Please try again later.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default StrategyPublisher;