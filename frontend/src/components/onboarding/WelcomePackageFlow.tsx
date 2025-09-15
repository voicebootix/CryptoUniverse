import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Gift,
  Star,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  TrendingUp,
  Target,
  Zap,
  Gem,
  Crown,
  Sparkles,
  DollarSign,
  Activity,
  Shield,
  Brain,
  Rocket,
  BarChart3,
  Trophy,
  Users,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { apiClient } from '@/lib/api/client';
import { toast } from 'sonner';
import { formatCurrency, formatPercentage, formatNumber } from '@/lib/utils';

interface WelcomePackage {
  package_id: string;
  name: string;
  description: string;
  credit_amount: number;
  profit_potential: number;
  included_strategies: Array<{
    strategy_id: string;
    name: string;
    description: string;
    category: string;
    win_rate: number;
    estimated_monthly_return: number;
    risk_level: string;
    is_ai_powered: boolean;
    features: string[];
  }>;
  total_value_usd: number;
  is_eligible: boolean;
  expires_at?: string;
}

interface OnboardingProgress {
  current_step: number;
  total_steps: number;
  steps_completed: string[];
  next_step: string;
}

const WelcomePackageFlow: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [onboardingCompleted, setOnboardingCompleted] = useState(false);

  // Fetch welcome package details
  const { data: welcomePackage, isLoading, error } = useQuery({
    queryKey: ['welcome-package'],
    queryFn: async () => {
      const response = await apiClient.get('/onboarding/welcome-package');
      return response.data as WelcomePackage;
    },
    retry: 2,
    staleTime: 5 * 60 * 1000 // 5 minutes
  });

  // Check onboarding status
  const { data: onboardingStatus } = useQuery({
    queryKey: ['onboarding-progress'],
    queryFn: async () => {
      const response = await apiClient.get('/onboarding/progress');
      return response.data as OnboardingProgress;
    },
    retry: 2
  });

  // Claim welcome package mutation
  const claimPackageMutation = useMutation({
    mutationFn: async (data: { selected_strategies: string[] }) => {
      const response = await apiClient.post('/onboarding/claim-welcome-package', data);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Welcome package claimed! ${data.credits_granted} credits added to your account.`);
      queryClient.invalidateQueries({ queryKey: ['user-credits'] });
      queryClient.invalidateQueries({ queryKey: ['user-strategy-portfolio'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding-progress'] });
      setOnboardingCompleted(true);
      setShowConfirmationModal(false);
      
      // Navigate to strategies after short delay
      setTimeout(() => {
        navigate('/dashboard/my-strategies');
      }, 2000);
    },
    onError: (error: any) => {
      toast.error(`Failed to claim package: ${error.response?.data?.detail || error.message}`);
    }
  });

  const getStrategyIcon = (category: string) => {
    const icons: Record<string, React.ReactNode> = {
      'derivatives': <Rocket className="h-6 w-6 text-orange-500" />,
      'spot': <TrendingUp className="h-6 w-6 text-green-500" />,
      'algorithmic': <Brain className="h-6 w-6 text-blue-500" />,
      'portfolio': <Target className="h-6 w-6 text-purple-500" />,
      'ai_powered': <Sparkles className="h-6 w-6 text-pink-500" />
    };
    return icons[category.toLowerCase()] || <BarChart3 className="h-6 w-6 text-gray-500" />;
  };

  const getRiskColor = (risk: string) => {
    const colors: Record<string, string> = {
      'very_low': 'text-green-600 bg-green-100',
      'low': 'text-green-500 bg-green-50',
      'medium': 'text-yellow-600 bg-yellow-100',
      'high': 'text-orange-600 bg-orange-100',
      'very_high': 'text-red-600 bg-red-100'
    };
    return colors[risk.toLowerCase()] || 'text-gray-600 bg-gray-100';
  };

  const handleStrategyToggle = (strategyId: string, maxSelections: number = 3) => {
    setSelectedStrategies(prev => {
      if (prev.includes(strategyId)) {
        return prev.filter(id => id !== strategyId);
      } else if (prev.length < maxSelections) {
        return [...prev, strategyId];
      } else {
        toast.warning(`You can select up to ${maxSelections} strategies for your welcome package.`);
        return prev;
      }
    });
  };

  const canProceed = () => {
    if (currentStep === 1) return true;
    if (currentStep === 2) return selectedStrategies.length >= 1 && selectedStrategies.length <= 3;
    if (currentStep === 3) return selectedStrategies.length >= 1;
    return false;
  };

  const handleNext = () => {
    if (currentStep < 3) {
      setCurrentStep(prev => prev + 1);
    } else {
      setShowConfirmationModal(true);
    }
  };

  const handleComplete = () => {
    if (selectedStrategies.length === 0) {
      toast.error('Please select at least one strategy to continue.');
      return;
    }
    
    claimPackageMutation.mutate({
      selected_strategies: selectedStrategies
    });
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <Card className="max-w-md">
          <CardContent className="text-center p-8">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Welcome Package Unavailable</h3>
            <p className="text-muted-foreground mb-4">
              {error instanceof Error ? error.message : 'Unable to load welcome package'}
            </p>
            <Button onClick={() => queryClient.invalidateQueries({ queryKey: ['welcome-package'] })}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto mb-4" />
          <p className="text-muted-foreground">Loading your welcome package...</p>
        </div>
      </div>
    );
  }

  if (onboardingCompleted) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-green-50 to-blue-50">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="text-center"
        >
          <div className="w-24 h-24 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <Trophy className="h-12 w-12 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-green-700 mb-2">Welcome to CryptoUniverse!</h1>
          <p className="text-green-600 mb-6">
            Your strategies are now active and ready to generate profits.
          </p>
          <Button onClick={() => navigate('/dashboard/my-strategies')} size="lg">
            View My Strategies
          </Button>
        </motion.div>
      </div>
    );
  }

  if (!welcomePackage?.is_eligible) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <Card className="max-w-md">
          <CardContent className="text-center p-8">
            <Gift className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Welcome Package Already Claimed</h3>
            <p className="text-muted-foreground mb-4">
              You've already claimed your welcome package. Head to your dashboard to manage your strategies.
            </p>
            <Button onClick={() => navigate('/dashboard')}>
              Go to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4"
          >
            <Gift className="h-8 w-8 text-white" />
          </motion.div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Welcome to CryptoUniverse!
          </h1>
          <p className="text-muted-foreground text-lg">
            Let's get you started with our exclusive welcome package
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Step {currentStep} of 3</span>
            <span className="text-sm text-muted-foreground">{Math.round((currentStep / 3) * 100)}% Complete</span>
          </div>
          <Progress value={(currentStep / 3) * 100} className="h-2" />
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.3 }}
          >
            {/* Step 1: Welcome Package Overview */}
            {currentStep === 1 && welcomePackage && (
              <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-purple-50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-3 text-2xl">
                    <Crown className="h-8 w-8 text-yellow-500" />
                    {welcomePackage.name}
                  </CardTitle>
                  <CardDescription className="text-lg">
                    {welcomePackage.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Package Benefits */}
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="text-center p-6 bg-white rounded-lg border border-green-200">
                      <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <DollarSign className="h-6 w-6 text-green-600" />
                      </div>
                      <h3 className="font-semibold text-green-700 mb-2">Free Credits</h3>
                      <div className="text-2xl font-bold text-green-600">
                        {formatNumber(welcomePackage.credit_amount)}
                      </div>
                      <p className="text-sm text-green-600">Credits to get started</p>
                    </div>

                    <div className="text-center p-6 bg-white rounded-lg border border-blue-200">
                      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Target className="h-6 w-6 text-blue-600" />
                      </div>
                      <h3 className="font-semibold text-blue-700 mb-2">Earning Potential</h3>
                      <div className="text-2xl font-bold text-blue-600">
                        {formatCurrency(welcomePackage.profit_potential)}
                      </div>
                      <p className="text-sm text-blue-600">Profit capacity unlocked</p>
                    </div>

                    <div className="text-center p-6 bg-white rounded-lg border border-purple-200">
                      <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Gem className="h-6 w-6 text-purple-600" />
                      </div>
                      <h3 className="font-semibold text-purple-700 mb-2">Premium Strategies</h3>
                      <div className="text-2xl font-bold text-purple-600">
                        {welcomePackage.included_strategies.length}
                      </div>
                      <p className="text-sm text-purple-600">AI-powered strategies</p>
                    </div>
                  </div>

                  {/* Value Proposition */}
                  <div className="p-6 bg-gradient-to-r from-yellow-50 to-orange-50 border border-orange-200 rounded-lg">
                    <div className="flex items-start gap-4">
                      <Sparkles className="h-8 w-8 text-orange-500 mt-1" />
                      <div>
                        <h4 className="font-semibold text-orange-800 mb-2">Revolutionary Profit-Sharing Model</h4>
                        <p className="text-orange-700 text-sm leading-relaxed">
                          Unlike traditional platforms, you only pay when you make money! 
                          Pay 25% of your profits to the platform, and that payment becomes credits 
                          to unlock even more profitable strategies. It's a win-win system designed 
                          to align our success with yours.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Total Value */}
                  <div className="text-center p-6 bg-gradient-to-r from-green-100 to-blue-100 rounded-lg">
                    <p className="text-muted-foreground mb-2">Total Package Value</p>
                    <div className="text-4xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                      {formatCurrency(welcomePackage.total_value_usd)}
                    </div>
                    <Badge className="mt-2 bg-green-500 text-white">
                      <Gift className="h-3 w-3 mr-1" />
                      100% FREE
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Step 2: Strategy Selection */}
            {currentStep === 2 && welcomePackage && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Star className="h-6 w-6 text-yellow-500" />
                      Choose Your Strategies (Select up to 3)
                    </CardTitle>
                    <CardDescription>
                      Select the trading strategies you want to activate with your welcome package.
                      Each strategy uses different approaches to generate profits.
                    </CardDescription>
                  </CardHeader>
                </Card>

                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                  {welcomePackage.included_strategies.map((strategy) => (
                    <motion.div
                      key={strategy.strategy_id}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <Card
                        className={`cursor-pointer transition-all h-full ${
                          selectedStrategies.includes(strategy.strategy_id)
                            ? 'border-2 border-blue-500 bg-blue-50'
                            : 'border hover:border-gray-300'
                        }`}
                        onClick={() => handleStrategyToggle(strategy.strategy_id)}
                      >
                        <CardHeader>
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              {getStrategyIcon(strategy.category)}
                              <div>
                                <CardTitle className="text-lg">{strategy.name}</CardTitle>
                                <div className="flex items-center gap-2 mt-1">
                                  <Badge variant="outline">{strategy.category}</Badge>
                                  {strategy.is_ai_powered && (
                                    <Badge className="bg-pink-100 text-pink-700">
                                      <Brain className="h-3 w-3 mr-1" />
                                      AI
                                    </Badge>
                                  )}
                                </div>
                              </div>
                            </div>
                            {selectedStrategies.includes(strategy.strategy_id) && (
                              <CheckCircle className="h-6 w-6 text-blue-500 flex-shrink-0" />
                            )}
                          </div>
                        </CardHeader>

                        <CardContent className="space-y-4">
                          <p className="text-sm text-muted-foreground">
                            {strategy.description}
                          </p>

                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <div className="text-muted-foreground">Win Rate</div>
                              <div className="font-bold text-green-500">
                                {formatPercentage(strategy.win_rate)}
                              </div>
                            </div>
                            <div>
                              <div className="text-muted-foreground">Est. Monthly Return</div>
                              <div className="font-bold text-blue-500">
                                {formatPercentage(strategy.estimated_monthly_return)}
                              </div>
                            </div>
                          </div>

                          <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(strategy.risk_level)}`}>
                            <Shield className="h-3 w-3 mr-1" />
                            {strategy.risk_level.replace('_', ' ')} Risk
                          </div>

                          {strategy.features && strategy.features.length > 0 && (
                            <div>
                              <div className="text-xs text-muted-foreground mb-2">Features:</div>
                              <div className="flex flex-wrap gap-1">
                                {strategy.features.slice(0, 3).map((feature, index) => (
                                  <Badge key={index} variant="secondary" className="text-xs">
                                    {feature}
                                  </Badge>
                                ))}
                                {strategy.features.length > 3 && (
                                  <Badge variant="secondary" className="text-xs">
                                    +{strategy.features.length - 3} more
                                  </Badge>
                                )}
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>

                <div className="text-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-700">
                    <Users className="h-4 w-4 inline mr-1" />
                    {selectedStrategies.length} of 3 strategies selected
                    {selectedStrategies.length === 0 && " • Select at least 1 strategy to continue"}
                  </p>
                </div>
              </div>
            )}

            {/* Step 3: Review & Confirm */}
            {currentStep === 3 && welcomePackage && (
              <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50 to-blue-50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-2xl">
                    <CheckCircle className="h-8 w-8 text-green-500" />
                    Review Your Selection
                  </CardTitle>
                  <CardDescription>
                    Confirm your choices and activate your welcome package
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Selected Strategies */}
                  <div>
                    <h4 className="font-semibold mb-4">Selected Strategies ({selectedStrategies.length})</h4>
                    <div className="space-y-3">
                      {selectedStrategies.map(strategyId => {
                        const strategy = welcomePackage.included_strategies.find(s => s.strategy_id === strategyId);
                        if (!strategy) return null;
                        
                        return (
                          <div key={strategyId} className="flex items-center gap-3 p-4 bg-white rounded-lg border">
                            {getStrategyIcon(strategy.category)}
                            <div className="flex-1">
                              <div className="font-medium">{strategy.name}</div>
                              <div className="text-sm text-muted-foreground">
                                {strategy.category} • Win Rate: {formatPercentage(strategy.win_rate)}
                              </div>
                            </div>
                            <Badge className={getRiskColor(strategy.risk_level)}>
                              {strategy.risk_level.replace('_', ' ')}
                            </Badge>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Package Summary */}
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="text-center p-4 bg-green-100 rounded-lg">
                      <div className="text-2xl font-bold text-green-700">
                        {formatNumber(welcomePackage.credit_amount)}
                      </div>
                      <div className="text-sm text-green-600">Free Credits</div>
                    </div>
                    <div className="text-center p-4 bg-blue-100 rounded-lg">
                      <div className="text-2xl font-bold text-blue-700">
                        {formatCurrency(welcomePackage.profit_potential)}
                      </div>
                      <div className="text-sm text-blue-600">Earning Potential</div>
                    </div>
                    <div className="text-center p-4 bg-purple-100 rounded-lg">
                      <div className="text-2xl font-bold text-purple-700">
                        {selectedStrategies.length}
                      </div>
                      <div className="text-sm text-purple-600">Active Strategies</div>
                    </div>
                  </div>

                  {/* Next Steps */}
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <h4 className="font-medium text-yellow-800 mb-2">What happens next?</h4>
                    <ul className="text-sm text-yellow-700 space-y-1">
                      <li>• Your selected strategies will be activated immediately</li>
                      <li>• {welcomePackage.credit_amount} credits will be added to your account</li>
                      <li>• You can start trading and earning profits right away</li>
                      <li>• Pay only when you make money (25% profit share)</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between mt-8">
          <Button
            variant="outline"
            onClick={() => setCurrentStep(prev => Math.max(1, prev - 1))}
            disabled={currentStep === 1}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>

          <Button
            onClick={handleNext}
            disabled={!canProceed()}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white"
            size="lg"
          >
            {currentStep === 3 ? 'Claim Welcome Package' : 'Continue'}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Confirmation Modal */}
        <Dialog open={showConfirmationModal} onOpenChange={setShowConfirmationModal}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Activate Welcome Package?</DialogTitle>
              <DialogDescription>
                This will activate your selected strategies and add credits to your account.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Gift className="h-5 w-5 text-green-600" />
                  <span className="font-medium text-green-800">You will receive:</span>
                </div>
                <ul className="text-sm text-green-700 space-y-1">
                  <li>• {welcomePackage?.credit_amount} free credits</li>
                  <li>• {formatCurrency(welcomePackage?.profit_potential || 0)} earning potential</li>
                  <li>• {selectedStrategies.length} premium AI strategies</li>
                </ul>
              </div>
              
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={() => setShowConfirmationModal(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleComplete}
                  disabled={claimPackageMutation.isPending}
                  className="flex-1 bg-gradient-to-r from-green-500 to-blue-500"
                >
                  {claimPackageMutation.isPending ? 'Activating...' : 'Activate Package'}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default WelcomePackageFlow;