import React from 'react';
import { motion } from 'framer-motion';
import { Brain, TrendingUp, TrendingDown, Minus, DollarSign, Sparkles, CheckCircle, Clock } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface AIModelResponse {
  model: string;
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  score: number;
  reasoning?: string;
  status?: 'analyzing' | 'completed' | 'failed';
}

interface AIConsensusData {
  consensus_score: number;
  recommendation: 'BUY' | 'SELL' | 'HOLD';
  confidence_threshold_met: boolean;
  model_responses: AIModelResponse[];
  cost_summary?: {
    total_cost: number;
    breakdown?: Record<string, number>;
  };
  reasoning?: string;
  timestamp?: string;
}

interface AIConsensusCardProps {
  consensusData?: AIConsensusData;
  isAnalyzing?: boolean;
  onApplyRecommendation?: () => void;
  onViewDetails?: () => void;
  compact?: boolean;
}

const AI_MODEL_ICONS = {
  gpt4: '🤖',
  claude: '🧠',
  gemini: '✨'
};

const AI_MODEL_COLORS = {
  gpt4: 'text-green-500',
  claude: 'text-purple-500',
  gemini: 'text-blue-500'
};

const RECOMMENDATION_CONFIG = {
  BUY: {
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    icon: TrendingUp,
    label: 'BUY'
  },
  SELL: {
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    icon: TrendingDown,
    label: 'SELL'
  },
  HOLD: {
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    icon: Minus,
    label: 'HOLD'
  }
};

export const AIConsensusCard: React.FC<AIConsensusCardProps> = ({
  consensusData,
  isAnalyzing = false,
  onApplyRecommendation,
  onViewDetails,
  compact = false
}) => {
  const getModelDisplayName = (model: string): string => {
    const normalized = model.toLowerCase();
    if (normalized.includes('gpt') || normalized.includes('openai')) return 'GPT-4';
    if (normalized.includes('claude')) return 'Claude';
    if (normalized.includes('gemini')) return 'Gemini';
    return model;
  };

  const getModelKey = (model: string): keyof typeof AI_MODEL_ICONS => {
    const normalized = model.toLowerCase();
    if (normalized.includes('gpt') || normalized.includes('openai')) return 'gpt4';
    if (normalized.includes('claude')) return 'claude';
    if (normalized.includes('gemini')) return 'gemini';
    return 'gpt4';
  };

  const getConfidenceLabel = (confidence: number): { label: string; color: string } => {
    if (confidence >= 85) return { label: 'VERY STRONG', color: 'text-green-600' };
    if (confidence >= 75) return { label: 'STRONG', color: 'text-green-500' };
    if (confidence >= 65) return { label: 'MODERATE', color: 'text-yellow-500' };
    if (confidence >= 50) return { label: 'WEAK', color: 'text-orange-500' };
    return { label: 'VERY WEAK', color: 'text-red-500' };
  };

  const getAgreementCount = (): number => {
    if (!consensusData?.model_responses) return 0;
    const mainRecommendation = consensusData.recommendation;
    return consensusData.model_responses.filter(
      (model) => model.recommendation === mainRecommendation
    ).length;
  };

  if (isAnalyzing) {
    return (
      <Card className="border-purple-500/30 bg-gradient-to-br from-purple-500/5 to-blue-500/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-5 w-5 animate-pulse text-purple-500" />
            AI Consensus Analysis
          </CardTitle>
          <CardDescription>Consulting multiple AI models...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {['GPT-4', 'Claude', 'Gemini'].map((model, index) => (
            <div key={model} className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className="text-lg">{AI_MODEL_ICONS[getModelKey(model)]}</span>
                  {model}
                </span>
                <Clock className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
              <Progress value={33 * (index + 1)} className="h-1.5" />
            </div>
          ))}
          <p className="text-center text-xs text-muted-foreground">
            Analyzing market conditions and generating recommendations...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!consensusData) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-5 w-5 text-muted-foreground" />
            AI Consensus Analysis
          </CardTitle>
          <CardDescription>Run AI analysis to get multi-model recommendations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <Sparkles className="h-12 w-12 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              No analysis available yet. Click "Get AI Opinion" to consult GPT-4, Claude, and Gemini.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const recommendation = consensusData.recommendation;
  const config = RECOMMENDATION_CONFIG[recommendation];
  const confidenceData = getConfidenceLabel(consensusData.consensus_score);
  const agreementCount = getAgreementCount();
  const totalModels = consensusData.model_responses?.length || 3;
  const RecommendationIcon = config.icon;

  if (compact) {
    return (
      <Card className={cn('border', config.borderColor, config.bgColor)}>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <RecommendationIcon className={cn('h-6 w-6', config.color)} />
              <div>
                <div className="flex items-center gap-2">
                  <span className={cn('text-lg font-bold', config.color)}>{config.label}</span>
                  <Badge variant="outline" className="text-xs">
                    {agreementCount}/{totalModels} Agree
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatPercentage(consensusData.consensus_score / 100)} Confidence
                </p>
              </div>
            </div>
            {onApplyRecommendation && (
              <Button size="sm" variant="outline" onClick={onApplyRecommendation}>
                Apply
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Card className={cn('border-2', config.borderColor, config.bgColor)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            AI Consensus Analysis
          </CardTitle>
          <CardDescription>
            Multi-model analysis from GPT-4, Claude, and Gemini
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Model Responses */}
          <div className="space-y-3">
            {consensusData.model_responses?.map((model) => {
              const modelKey = getModelKey(model.model);
              const modelConfig = RECOMMENDATION_CONFIG[model.recommendation];
              const ModelIcon = modelConfig.icon;

              return (
                <div key={model.model} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{AI_MODEL_ICONS[modelKey]}</span>
                      <span className={cn('text-sm font-medium', AI_MODEL_COLORS[modelKey])}>
                        {getModelDisplayName(model.model)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <ModelIcon className={cn('h-4 w-4', modelConfig.color)} />
                      <span className={cn('text-sm font-semibold', modelConfig.color)}>
                        {model.recommendation}
                      </span>
                      {model.status === 'completed' && (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      )}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Progress value={model.confidence} className="h-2" />
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Confidence</span>
                      <span className="font-medium">{formatPercentage(model.confidence / 100)}</span>
                    </div>
                  </div>
                  {model.reasoning && !compact && (
                    <p className="text-xs text-muted-foreground italic line-clamp-2">
                      {model.reasoning}
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          <Separator />

          {/* Final Consensus */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Final Consensus</span>
              <Badge variant="outline" className={cn('gap-1', config.color)}>
                {agreementCount}/{totalModels} Models Agree
              </Badge>
            </div>

            <div className={cn('rounded-lg border-2 p-4', config.borderColor, config.bgColor)}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <RecommendationIcon className={cn('h-8 w-8', config.color)} />
                  <div>
                    <div className={cn('text-2xl font-bold', config.color)}>
                      {config.label}
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">Confidence:</span>
                      <span className={cn('font-semibold', confidenceData.color)}>
                        {confidenceData.label}
                      </span>
                      <span className="text-muted-foreground">
                        ({formatPercentage(consensusData.consensus_score / 100)})
                      </span>
                    </div>
                  </div>
                </div>
                {consensusData.confidence_threshold_met && (
                  <div className="flex flex-col items-end gap-1">
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle className="mr-1 h-3 w-3" />
                      Threshold Met
                    </Badge>
                  </div>
                )}
              </div>

              {consensusData.reasoning && (
                <p className="mt-3 text-sm text-muted-foreground border-t pt-3">
                  {consensusData.reasoning}
                </p>
              )}
            </div>
          </div>

          {/* Cost Summary */}
          {consensusData.cost_summary && (
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-xs">
              <div className="flex items-center gap-2 text-muted-foreground">
                <DollarSign className="h-3 w-3" />
                Analysis Cost
              </div>
              <span className="font-medium">
                {formatCurrency(consensusData.cost_summary.total_cost)}
              </span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            {onApplyRecommendation && (
              <Button
                className="flex-1"
                onClick={onApplyRecommendation}
                disabled={!consensusData.confidence_threshold_met}
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Apply Recommendation
              </Button>
            )}
            {onViewDetails && (
              <Button variant="outline" onClick={onViewDetails}>
                View Details
              </Button>
            )}
          </div>

          {/* Timestamp */}
          {consensusData.timestamp && (
            <p className="text-center text-xs text-muted-foreground">
              Analysis completed at {new Date(consensusData.timestamp).toLocaleTimeString()}
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};

export default AIConsensusCard;
