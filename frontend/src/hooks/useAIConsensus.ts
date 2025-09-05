import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useToast } from '@/components/ui/use-toast';
import { useWebSocket } from '@/hooks/useWebSocket';

export interface AIModelResponse {
  provider: string;
  confidence: number;
  reasoning: string;
  cost: number;
  response_time: number;
}

export interface AIConsensusResult {
  success: boolean;
  consensus_score: number;
  recommendation: string;
  reasoning: string;
  confidence_threshold_met: boolean;
  model_responses: AIModelResponse[];
  cost_summary: {
    total_cost: number;
    models_used: number;
  };
  timestamp: string;
}

export interface AIModelWeights {
  gpt4: number;
  claude: number;
  gemini: number;
}

export interface AIModelStatus {
  ai_models_status: Record<string, string>;
  performance_metrics: Record<string, any>;
  cost_report: {
    total_cost_usd: number;
    requests_today: number;
    cost_by_model: Record<string, number>;
  };
  circuit_breaker_status: Record<string, any>;
}

export interface OpportunityAnalysisRequest {
  symbol: string;
  analysis_type: string;
  timeframe: string;
  confidence_threshold?: number;
  ai_models?: string;
  include_risk_metrics?: boolean;
}

export interface TradeValidationRequest {
  trade_data: Record<string, any>;
  confidence_threshold?: number;
  ai_models?: string;
  execution_urgency?: string;
}

export interface RiskAssessmentRequest {
  portfolio_data: Record<string, any>;
  confidence_threshold?: number;
  ai_models?: string;
  risk_type?: string;
  stress_test?: boolean;
}

export interface PortfolioReviewRequest {
  portfolio_data: Record<string, any>;
  confidence_threshold?: number;
  ai_models?: string;
  review_type?: string;
  benchmark?: string;
}

export interface MarketAnalysisRequest {
  symbols: string[];
  confidence_threshold?: number;
  ai_models?: string;
  analysis_depth?: string;
  include_sentiment?: boolean;
}

export interface ConsensusDecisionRequest {
  decision_context: Record<string, any>;
  confidence_threshold?: number;
  ai_models?: string;
  decision_type?: string;
  execution_timeline?: string;
}

export const useAIConsensus = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [consensusHistory, setConsensusHistory] = useState<any[]>([]);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Real-time AI consensus updates via WebSocket
  const { lastMessage, connectionStatus } = useWebSocket('/ws/ai-consensus', {
    onMessage: (data) => {
      if (data.type === 'ai_consensus_update') {
        // Update consensus history - safe property access
        const consensusData = data.data || {};
        setConsensusHistory(prev => [
          ...prev.slice(-49), // Keep last 49 entries
          {
            time: new Date().toLocaleTimeString(),
            consensus: consensusData.consensus_score || 0,
            recommendation: consensusData.recommendation || 'HOLD',
            function: consensusData.function || 'unknown',
            timestamp: consensusData.timestamp || new Date().toISOString()
          }
        ]);

        // Show AI explanation toast - safe property access
        if (consensusData.explanation) {
          toast({
            title: "🤖 AI Money Manager",
            description: consensusData.explanation,
            duration: 5000,
          });
        }

        // Invalidate related queries
        queryClient.invalidateQueries({ queryKey: ['ai-consensus-status'] });
      }
    }
  });

  // Get real-time AI status
  const { 
    data: aiStatus, 
    isLoading: statusLoading, 
    error: statusError 
  } = useQuery<AIModelStatus>({
    queryKey: ['ai-consensus-status'],
    queryFn: () => apiClient.get('/ai-consensus/status/real-time').then(res => res.data),
    refetchInterval: 5000, // Refresh every 5 seconds
    retry: 3,
  });

  // Get user's AI model weights
  const { 
    data: userWeights, 
    isLoading: weightsLoading 
  } = useQuery({
    queryKey: ['ai-model-weights'],
    queryFn: () => apiClient.get('/ai-consensus/models/weights').then(res => res.data),
    retry: 2,
  });

  // Get user's cost summary
  const { data: costSummary } = useQuery({
    queryKey: ['ai-cost-summary'],
    queryFn: () => apiClient.get('/ai-consensus/cost-summary').then(res => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Analyze opportunity mutation
  const analyzeOpportunityMutation = useMutation({
    mutationFn: (request: OpportunityAnalysisRequest) =>
      apiClient.post('/ai-consensus/analyze-opportunity', request).then(res => res.data),
    onMutate: () => {
      setIsAnalyzing(true);
      toast({
        title: "Analysis Started",
        description: "AI models are analyzing the opportunity...",
      });
    },
    onSuccess: (data) => {
      toast({
        title: "✅ Analysis Complete",
        description: `Consensus: ${data?.result?.opportunity_analysis?.consensus_score || 'N/A'}% confidence`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Analysis Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    },
    onSettled: () => {
      setIsAnalyzing(false);
    }
  });

  // Validate trade mutation
  const validateTradeMutation = useMutation({
    mutationFn: (request: TradeValidationRequest) =>
      apiClient.post('/ai-consensus/validate-trade', request).then(res => res.data),
    onMutate: () => {
      setIsAnalyzing(true);
      toast({
        title: "Validating Trade",
        description: "AI models are validating your trade...",
      });
    },
    onSuccess: (data) => {
      const validation = data?.result?.trade_validation;
      toast({
        title: validation?.approval_status === 'APPROVED' ? "✅ Trade Approved" : "⚠️ Trade Needs Review",
        description: `Validation Score: ${validation?.validation_score || 'N/A'}%`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Validation Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    },
    onSettled: () => {
      setIsAnalyzing(false);
    }
  });

  // Risk assessment mutation
  const riskAssessmentMutation = useMutation({
    mutationFn: (request: RiskAssessmentRequest) =>
      apiClient.post('/ai-consensus/risk-assessment', request).then(res => res.data),
    onMutate: () => {
      setIsAnalyzing(true);
      toast({
        title: "Assessing Risk",
        description: "AI models are analyzing portfolio risk...",
      });
    },
    onSuccess: (data) => {
      const assessment = data?.result?.risk_assessment;
      toast({
        title: "🛡️ Risk Assessment Complete",
        description: `Risk Level: ${assessment?.risk_level || 'N/A'} (${assessment?.risk_score || 'N/A'}%)`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Risk Assessment Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    },
    onSettled: () => {
      setIsAnalyzing(false);
    }
  });

  // Portfolio review mutation
  const portfolioReviewMutation = useMutation({
    mutationFn: (request: PortfolioReviewRequest) =>
      apiClient.post('/ai-consensus/portfolio-review', request).then(res => res.data),
    onMutate: () => {
      setIsAnalyzing(true);
      toast({
        title: "Reviewing Portfolio",
        description: "AI models are analyzing your portfolio...",
      });
    },
    onSuccess: (data) => {
      const review = data?.result?.portfolio_review;
      toast({
        title: "📊 Portfolio Review Complete",
        description: `Score: ${review?.portfolio_score || 'N/A'}% - ${review?.rebalancing_urgency || 'N/A'} rebalancing urgency`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Portfolio Review Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    },
    onSettled: () => {
      setIsAnalyzing(false);
    }
  });

  // Market analysis mutation
  const marketAnalysisMutation = useMutation({
    mutationFn: (request: MarketAnalysisRequest) =>
      apiClient.post('/ai-consensus/market-analysis', request).then(res => res.data),
    onMutate: () => {
      setIsAnalyzing(true);
      toast({
        title: "Analyzing Market",
        description: "AI models are analyzing market conditions...",
      });
    },
    onSuccess: (data) => {
      const analysis = data?.result?.market_analysis;
      toast({
        title: "📈 Market Analysis Complete",
        description: `Market Strength: ${analysis?.market_strength || 'N/A'}% - ${analysis?.entry_timing || 'N/A'} timing`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Market Analysis Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    },
    onSettled: () => {
      setIsAnalyzing(false);
    }
  });

  // Consensus decision mutation
  const consensusDecisionMutation = useMutation({
    mutationFn: (request: ConsensusDecisionRequest) =>
      apiClient.post('/ai-consensus/consensus-decision', request).then(res => res.data),
    onMutate: () => {
      setIsAnalyzing(true);
      toast({
        title: "Making Final Decision",
        description: "AI models are making consensus decision...",
      });
    },
    onSuccess: (data) => {
      const decision = data?.result?.consensus_decision;
      toast({
        title: "🎯 Final Decision Made",
        description: `Recommendation: ${decision?.final_recommendation || 'N/A'} - ${decision?.confidence_level || 'N/A'} confidence`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Decision Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    },
    onSettled: () => {
      setIsAnalyzing(false);
    }
  });

  // Update AI model weights mutation
  const updateWeightsMutation = useMutation({
    mutationFn: (weights: { ai_model_weights: AIModelWeights; autonomous_frequency_minutes?: number }) =>
      apiClient.post('/ai-consensus/models/weights', weights).then(res => res.data),
    onSuccess: () => {
      toast({
        title: "✅ AI Settings Updated",
        description: "Your AI model weights have been updated successfully",
      });
      queryClient.invalidateQueries({ queryKey: ['ai-model-weights'] });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Update Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    }
  });

  // Emergency stop mutation
  const emergencyStopMutation = useMutation({
    mutationFn: () => apiClient.post('/ai-consensus/emergency/stop').then(res => res.data),
    onSuccess: () => {
      toast({
        title: "🚨 Emergency Stop Activated",
        description: "All AI operations have been halted",
        variant: "destructive"
      });
      queryClient.invalidateQueries({ queryKey: ['ai-consensus-status'] });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Emergency Stop Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    }
  });

  // Resume operations mutation
  const resumeOperationsMutation = useMutation({
    mutationFn: () => apiClient.post('/ai-consensus/emergency/resume').then(res => res.data),
    onSuccess: () => {
      toast({
        title: "✅ Operations Resumed",
        description: "AI operations have been resumed successfully",
      });
      queryClient.invalidateQueries({ queryKey: ['ai-consensus-status'] });
    },
    onError: (error: any) => {
      toast({
        title: "❌ Resume Failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive"
      });
    }
  });

  // Convenience methods
  const analyzeOpportunity = (request: OpportunityAnalysisRequest) => {
    return analyzeOpportunityMutation.mutateAsync(request);
  };

  const validateTrade = (request: TradeValidationRequest) => {
    return validateTradeMutation.mutateAsync(request);
  };

  const assessRisk = (request: RiskAssessmentRequest) => {
    return riskAssessmentMutation.mutateAsync(request);
  };

  const reviewPortfolio = (request: PortfolioReviewRequest) => {
    return portfolioReviewMutation.mutateAsync(request);
  };

  const analyzeMarket = (request: MarketAnalysisRequest) => {
    return marketAnalysisMutation.mutateAsync(request);
  };

  const makeConsensusDecision = (request: ConsensusDecisionRequest) => {
    return consensusDecisionMutation.mutateAsync(request);
  };

  const updateModelWeights = (weights: AIModelWeights, frequency?: number) => {
    return updateWeightsMutation.mutateAsync({
      ai_model_weights: weights,
      autonomous_frequency_minutes: frequency
    });
  };

  const emergencyStop = () => {
    return emergencyStopMutation.mutateAsync();
  };

  const resumeOperations = () => {
    return resumeOperationsMutation.mutateAsync();
  };

  return {
    // Data
    aiStatus,
    userWeights,
    costSummary,
    consensusHistory,
    connectionStatus,
    
    // Loading states
    isAnalyzing,
    statusLoading,
    weightsLoading,
    
    // Error states
    statusError,
    
    // Actions
    analyzeOpportunity,
    validateTrade,
    assessRisk,
    reviewPortfolio,
    analyzeMarket,
    makeConsensusDecision,
    updateModelWeights,
    emergencyStop,
    resumeOperations,
    
    // Mutation objects (for advanced usage)
    mutations: {
      analyzeOpportunity: analyzeOpportunityMutation,
      validateTrade: validateTradeMutation,
      riskAssessment: riskAssessmentMutation,
      portfolioReview: portfolioReviewMutation,
      marketAnalysis: marketAnalysisMutation,
      consensusDecision: consensusDecisionMutation,
      updateWeights: updateWeightsMutation,
      emergencyStop: emergencyStopMutation,
      resumeOperations: resumeOperationsMutation,
    }
  };
};