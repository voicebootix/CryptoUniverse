import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3,
  Brain,
  Shield,
  TrendingUp,
  Activity,
  CheckCircle,
  AlertCircle,
  Clock,
  Zap,
  ChevronRight,
  Loader
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { formatPercentage } from '@/lib/utils';

export enum ExecutionPhase {
  IDLE = 'idle',
  ANALYSIS = 'analysis',
  CONSENSUS = 'consensus', 
  VALIDATION = 'validation',
  EXECUTION = 'execution',
  MONITORING = 'monitoring',
  COMPLETED = 'completed'
}

interface PhaseMetrics {
  timeSpent: number; // seconds
  decisionsMade: number;
  confidence: number;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'skipped';
}

interface PhaseData {
  phase: ExecutionPhase;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  details?: string[];
  metrics?: PhaseMetrics;
  canOverride?: boolean;
}

interface PhaseProgressVisualizerProps {
  currentPhase: ExecutionPhase;
  phaseHistory: PhaseData[];
  onPhaseOverride?: (phase: ExecutionPhase) => void;
  isCompact?: boolean;
  showMetrics?: boolean;
  allowManualControl?: boolean;
}

const phaseDefinitions: Record<ExecutionPhase, Omit<PhaseData, 'metrics'>> = {
  [ExecutionPhase.IDLE]: {
    phase: ExecutionPhase.IDLE,
    title: 'Ready',
    description: 'System idle, waiting for instructions',
    icon: <Clock className="h-5 w-5" />,
    color: 'text-gray-500'
  },
  [ExecutionPhase.ANALYSIS]: {
    phase: ExecutionPhase.ANALYSIS,
    title: 'Market Analysis',
    description: 'Scanning markets, identifying patterns and opportunities',
    icon: <BarChart3 className="h-5 w-5" />,
    color: 'text-blue-500',
    details: [
      'Technical indicators analysis',
      'Volume and liquidity assessment',
      'Cross-exchange price comparison',
      'Sentiment analysis'
    ],
    canOverride: true
  },
  [ExecutionPhase.CONSENSUS]: {
    phase: ExecutionPhase.CONSENSUS,
    title: 'AI Consensus',
    description: 'Multiple AI models evaluating the opportunity',
    icon: <Brain className="h-5 w-5" />,
    color: 'text-purple-500',
    details: [
      'GPT-4 analysis and scoring',
      'Claude evaluation and reasoning',
      'Gemini market assessment',
      'Weighted consensus calculation'
    ],
    canOverride: false
  },
  [ExecutionPhase.VALIDATION]: {
    phase: ExecutionPhase.VALIDATION,
    title: 'Risk Validation',
    description: 'Checking risk parameters and position sizing',
    icon: <Shield className="h-5 w-5" />,
    color: 'text-yellow-500',
    details: [
      'Portfolio exposure limits',
      'Risk/reward ratio validation',
      'Stop-loss and take-profit levels',
      'Circuit breaker checks'
    ],
    canOverride: true
  },
  [ExecutionPhase.EXECUTION]: {
    phase: ExecutionPhase.EXECUTION,
    title: 'Trade Execution',
    description: 'Placing and managing orders on exchanges',
    icon: <TrendingUp className="h-5 w-5" />,
    color: 'text-green-500',
    details: [
      'Order placement',
      'Slippage minimization',
      'Smart order routing',
      'Execution confirmation'
    ],
    canOverride: false
  },
  [ExecutionPhase.MONITORING]: {
    phase: ExecutionPhase.MONITORING,
    title: 'Position Monitoring',
    description: 'Tracking performance and managing position',
    icon: <Activity className="h-5 w-5" />,
    color: 'text-indigo-500',
    details: [
      'Real-time P&L tracking',
      'Market condition monitoring',
      'Stop-loss/take-profit management',
      'Exit strategy optimization'
    ],
    canOverride: true
  },
  [ExecutionPhase.COMPLETED]: {
    phase: ExecutionPhase.COMPLETED,
    title: 'Completed',
    description: 'Trade cycle completed successfully',
    icon: <CheckCircle className="h-5 w-5" />,
    color: 'text-green-600'
  }
};

const PhaseProgressVisualizer: React.FC<PhaseProgressVisualizerProps> = ({
  currentPhase,
  phaseHistory = [],
  onPhaseOverride,
  isCompact = false,
  showMetrics = true,
  allowManualControl = true
}) => {
  const phases = [
    ExecutionPhase.ANALYSIS,
    ExecutionPhase.CONSENSUS,
    ExecutionPhase.VALIDATION,
    ExecutionPhase.EXECUTION,
    ExecutionPhase.MONITORING
  ];

  const getCurrentPhaseIndex = () => {
    const index = phases.indexOf(currentPhase);
    return index === -1 ? -1 : index;
  };

  const getPhaseStatus = (phase: ExecutionPhase) => {
    const phaseIndex = phases.indexOf(phase);
    const currentIndex = getCurrentPhaseIndex();
    
    if (currentPhase === ExecutionPhase.COMPLETED) return 'completed';
    if (phaseIndex < currentIndex) return 'completed';
    if (phaseIndex === currentIndex) return 'active';
    return 'pending';
  };

  const getPhaseProgress = () => {
    if (currentPhase === ExecutionPhase.IDLE) return 0;
    if (currentPhase === ExecutionPhase.COMPLETED) return 100;
    
    const currentIndex = getCurrentPhaseIndex();
    if (currentIndex === -1) return 0;
    
    return ((currentIndex + 1) / phases.length) * 100;
  };

  const renderCompactView = () => (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Zap className="h-4 w-4 text-primary" />
            5-Phase Execution
          </CardTitle>
          {currentPhase !== ExecutionPhase.IDLE && (
            <Badge variant="outline" className="text-xs">
              {getPhaseProgress().toFixed(0)}% Complete
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Progress value={getPhaseProgress()} className="h-2" />
        
        <div className="flex items-center justify-between gap-1">
          {phases.map((phase, index) => {
            const status = getPhaseStatus(phase);
            const phaseInfo = phaseDefinitions[phase];
            const isActive = status === 'active';
            const isCompleted = status === 'completed';
            
            return (
              <React.Fragment key={phase}>
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ 
                    scale: isActive ? 1.1 : 1, 
                    opacity: 1 
                  }}
                  className={`relative ${index > 0 ? 'flex-1' : ''}`}
                >
                  <div className="flex items-center">
                    {index > 0 && (
                      <div className={`h-0.5 w-full mr-1 transition-colors ${
                        isCompleted ? 'bg-primary' : 'bg-muted'
                      }`} />
                    )}
                    
                    <div
                      className={`
                        w-8 h-8 rounded-full flex items-center justify-center transition-all
                        ${isActive ? 'bg-primary text-primary-foreground ring-2 ring-primary/20' :
                          isCompleted ? 'bg-primary/20 text-primary' :
                          'bg-muted text-muted-foreground'}
                      `}
                    >
                      {isCompleted ? (
                        <CheckCircle className="h-4 w-4" />
                      ) : isActive ? (
                        <Loader className="h-4 w-4 animate-spin" />
                      ) : (
                        <span className="text-xs font-medium">{index + 1}</span>
                      )}
                    </div>
                  </div>
                  
                  {isActive && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute top-10 left-1/2 transform -translate-x-1/2 z-10"
                    >
                      <div className="bg-popover text-popover-foreground rounded-lg shadow-lg p-2 min-w-[120px]">
                        <p className="text-xs font-medium">{phaseInfo.title}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Processing...
                        </p>
                      </div>
                    </motion.div>
                  )}
                </motion.div>
                
                {index === phases.length - 1 && status !== 'pending' && (
                  <div className={`h-0.5 flex-1 ml-1 transition-colors ${
                    currentPhase === ExecutionPhase.COMPLETED ? 'bg-primary' : 'bg-muted'
                  }`} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );

  const renderDetailedView = () => (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            5-Phase Execution Framework
          </CardTitle>
          <div className="flex items-center gap-2">
            {currentPhase !== ExecutionPhase.IDLE && (
              <Badge variant="outline">
                Phase {getCurrentPhaseIndex() + 1} of 5
              </Badge>
            )}
            <Badge variant="secondary">
              {getPhaseProgress().toFixed(0)}% Complete
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={getPhaseProgress()} className="h-2" />
        
        <div className="space-y-3">
          {phases.map((phase, index) => {
            const status = getPhaseStatus(phase);
            const phaseInfo = phaseDefinitions[phase];
            const historyData = phaseHistory.find(h => h.phase === phase);
            const metrics = historyData?.metrics;
            const isActive = status === 'active';
            const isCompleted = status === 'completed';
            
            return (
              <motion.div
                key={phase}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`
                  relative border rounded-lg p-4 transition-all
                  ${isActive ? 'border-primary bg-primary/5' :
                    isCompleted ? 'border-green-500/20 bg-green-500/5' :
                    'border-muted bg-muted/20'}
                `}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className={`
                      p-2 rounded-lg transition-colors
                      ${isActive ? 'bg-primary/10' :
                        isCompleted ? 'bg-green-500/10' :
                        'bg-muted'}
                    `}>
                      <div className={phaseInfo.color}>
                        {phaseInfo.icon}
                      </div>
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold">
                          Phase {index + 1}: {phaseInfo.title}
                        </h4>
                        {isActive && (
                          <Badge variant="default" className="text-xs animate-pulse">
                            Active
                          </Badge>
                        )}
                        {isCompleted && (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        )}
                      </div>
                      
                      <p className="text-sm text-muted-foreground mt-1">
                        {phaseInfo.description}
                      </p>
                      
                      {isActive && phaseInfo.details && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          className="mt-3 space-y-1"
                        >
                          {phaseInfo.details.map((detail, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-sm">
                              <div className="w-1 h-1 rounded-full bg-primary" />
                              <span className="text-muted-foreground">{detail}</span>
                            </div>
                          ))}
                        </motion.div>
                      )}
                      
                      {showMetrics && metrics && (
                        <div className="flex items-center gap-4 mt-3">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">
                              {metrics.timeSpent}s
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Zap className="h-3 w-3 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">
                              {metrics.decisionsMade} decisions
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Activity className="h-3 w-3 text-muted-foreground" />
                            <span className="text-xs text-muted-foreground">
                              {formatPercentage(metrics.confidence)} confidence
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {allowManualControl && phaseInfo.canOverride && isActive && (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onPhaseOverride?.(phase)}
                      >
                        Skip
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onPhaseOverride?.(phase)}
                      >
                        Override
                      </Button>
                    </div>
                  )}
                </div>
                
                {index < phases.length - 1 && (
                  <div className="absolute -bottom-3 left-8 w-0.5 h-6 bg-muted" />
                )}
              </motion.div>
            );
          })}
        </div>
        
        {currentPhase === ExecutionPhase.COMPLETED && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-lg"
          >
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <div>
                <p className="font-semibold text-green-600">Trade Cycle Completed Successfully</p>
                <p className="text-sm text-muted-foreground mt-1">
                  All 5 phases executed. Position is now being monitored.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </CardContent>
    </Card>
  );

  return isCompact ? renderCompactView() : renderDetailedView();
};

export default PhaseProgressVisualizer;