import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Bot,
  User,
  Loader,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Brain,
  Shield,
  Target,
  BarChart3,
  Activity,
  ChevronRight,
  Clock,
  DollarSign,
  Sparkles,
  AlertCircle,
  Check,
  X,
  RefreshCw,
  Maximize2,
  Minimize2,
  MessageSquare,
  Zap
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useToast } from '@/components/ui/use-toast';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useAuthStore } from '@/store/authStore';
import { useChatStore, ChatMode, ChatMessage as BaseChatMessage } from '@/store/chatStore';

import {
  ExecutionPhase,
  AIPersonality,
  MessageType,
  PHASE_CONFIG,
  PERSONALITY_CONFIG,
  API_ENDPOINTS,
  WS_EVENTS,
  TIMEOUTS
} from '@/constants/trading';

// Server phase string to enum mapping
const serverPhaseToEnum = (serverPhase: string): ExecutionPhase => {
  const phaseMap: Record<string, ExecutionPhase> = {
    'idle': ExecutionPhase.IDLE,
    'analysis': ExecutionPhase.ANALYSIS,
    'consensus': ExecutionPhase.CONSENSUS,
    'validation': ExecutionPhase.VALIDATION,
    'execution': ExecutionPhase.EXECUTION,
    'monitoring': ExecutionPhase.MONITORING,
    'completed': ExecutionPhase.COMPLETED,
  };

  return phaseMap[serverPhase?.toLowerCase()] || ExecutionPhase.IDLE;
};

// Extended message interface for trading features
interface ExtendedChatMessage extends Omit<BaseChatMessage, 'type'> {
  type: 'user' | 'assistant' | 'phase' | 'trade' | 'ai';
  phase?: ExecutionPhase;
  tradeProposal?: TradeProposal;
  metadata?: any;
}

interface Message extends ExtendedChatMessage {
  // Additional fields if needed
}

// Use shared constants
const phaseConfig = PHASE_CONFIG;
const personalityConfig = PERSONALITY_CONFIG;

interface PendingTradeDetails {
  decisionId: string;
  action?: string;
  symbol?: string;
  orderType?: string;
  confidence?: number;
  price?: number;
  quantity?: number;
  positionSizeUsd?: number;
  stopLoss?: number;
  takeProfit?: number;
  simulation?: boolean;
  reasoning: string[];
  risks: string[];
  analysis?: string;
  riskScore?: number;
}

interface ConversationalTradingInterfaceProps {
  className?: string;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  isPaperTrading?: boolean;
  onTradeExecuted?: (tradeData: any) => void;
  sessionId?: string;
}

const ConversationalTradingInterface: React.FC<ConversationalTradingInterfaceProps> = ({
  className = '',
  isExpanded = false,
  onToggleExpand,
  isPaperTrading = false
}) => {
  // Use shared chat store
  const {
    messages: baseMessages,
    isLoading,
    sessionId,
    currentMode,
    sendMessage: sendChatMessage,
    initializeSession,
    setCurrentMode,
    pendingDecision,
    approveDecision,
    clearPendingDecision
  } = useChatStore();
  
  // Overlay state for local-only messages (phase, trade, ai messages)
  const [overlays, setOverlays] = useState<ExtendedChatMessage[]>([]);
  
  // Compose final messages from base messages + overlays
  const messages = useMemo(() => {
    const mappedBaseMessages: ExtendedChatMessage[] = baseMessages.map(msg => ({
      ...msg,
      type: msg.type as 'user' | 'assistant' | 'phase' | 'trade' | 'ai'
    }));
    
    // Merge base messages with overlays, avoiding duplicates by ID
    const allMessages = [...mappedBaseMessages];
    const existingIds = new Set(mappedBaseMessages.map(msg => msg.id));
    
    overlays.forEach(overlay => {
      if (!existingIds.has(overlay.id)) {
        allMessages.push(overlay);
      }
    });
    
    // Sort by timestamp to maintain chronological order
    return allMessages.sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [baseMessages, overlays]);
  
  const [inputValue, setInputValue] = useState('');
  const [currentPhase, setCurrentPhase] = useState<ExecutionPhase>(ExecutionPhase.IDLE);
  const [personality, setPersonality] = useState<AIPersonality>(AIPersonality.BALANCED);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionAction, setDecisionAction] = useState<'approve' | 'decline' | null>(null);
  // Remove WebSocket connection state since we're using REST API
  const [isConnected] = useState(true); // Always connected via REST API
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const user = useAuthStore((state) => state.user);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Remove WebSocket config updates since we're using REST API

  // Remove WebSocket ref since we're using REST API

  // Initialize session and set trading mode
  useEffect(() => {
    setCurrentMode(ChatMode.TRADING);
    if (!sessionId || baseMessages.length === 0) {
      initializeSession();
    }
  }, [setCurrentMode, sessionId, baseMessages.length, initializeSession]);

  // Remove WebSocket functions since we're using REST API

  const addPhaseMessage = (phase: ExecutionPhase, details: string) => {
    const phaseInfo = phaseConfig[phase];
    const message: ExtendedChatMessage = {
      id: `phase-${Date.now()}`,
      content: `**${phaseInfo.title}**\n${details}`,
      type: 'phase',
      phase,
      timestamp: new Date().toISOString()
    };
    setOverlays(prev => [...prev, message]);
  };

  const addAIMessage = (content: string, metadata?: any) => {
    const message: ExtendedChatMessage = {
      id: `ai-${Date.now()}`,
      content,
      type: 'ai',
      metadata,
      timestamp: new Date().toISOString()
    };
    setOverlays(prev => [...prev, message]);
  };

  const pendingTradeDetails = useMemo<PendingTradeDetails | null>(() => {
    if (!pendingDecision?.message) {
      return null;
    }

    const metadata = pendingDecision.message.metadata ?? {};
    const recommendation = metadata.recommendation ?? {};
    const riskAssessment = metadata.risk_assessment ?? recommendation.risk_assessment ?? {};

    const parseNumber = (value: any): number | undefined => {
      if (value === null || value === undefined) {
        return undefined;
      }
      const numeric = typeof value === 'number' ? value : parseFloat(value);
      return Number.isFinite(numeric) ? numeric : undefined;
    };

    const normalizeStringArray = (value: any): string[] => {
      if (Array.isArray(value)) {
        return value
          .map(item => (typeof item === 'string' ? item.trim() : `${item}`.trim()))
          .filter(Boolean);
      }
      if (typeof value === 'string') {
        return value
          .split(/\r?\n|;/)
          .map(item => item.trim())
          .filter(Boolean);
      }
      return [];
    };

    const actionRaw = recommendation.action ?? recommendation.side ?? metadata.action;
    const symbolRaw = recommendation.symbol ?? recommendation.asset ?? recommendation.pair ?? metadata.symbol;

    const orderTypeRaw = recommendation.order_type ?? recommendation.orderType;
    const confidenceRaw =
      metadata.confidence ?? pendingDecision.message.confidence ?? recommendation.confidence;

    let simulationFlag = metadata.simulation_mode ?? recommendation.simulation_mode;
    if (typeof simulationFlag === 'string') {
      simulationFlag = !['false', '0', 'off', 'no'].includes(simulationFlag.toLowerCase());
    }

    const quantityValue =
      parseNumber(
        recommendation.quantity ??
          recommendation.units ??
          (recommendation.amount_unit === 'contracts' ? recommendation.amount : undefined)
      ) ?? undefined;

    const positionSizeUsdValue =
      parseNumber(
        recommendation.position_size_usd ??
          recommendation.amount_usd ??
          (recommendation.amount_unit && recommendation.amount_unit !== 'contracts'
            ? recommendation.amount
            : undefined)
      ) ?? undefined;

    const analysisText =
      metadata.ai_analysis ?? recommendation.analysis ?? pendingDecision.message.content;

    const confidence =
      typeof confidenceRaw === 'number'
        ? confidenceRaw > 1
          ? confidenceRaw / 100
          : confidenceRaw
        : undefined;

    return {
      decisionId: pendingDecision.id,
      action: typeof actionRaw === 'string' ? actionRaw.toUpperCase() : undefined,
      symbol: typeof symbolRaw === 'string' ? symbolRaw.toUpperCase() : undefined,
      orderType:
        typeof orderTypeRaw === 'string'
          ? orderTypeRaw.toUpperCase()
          : undefined,
      confidence,
      price: parseNumber(recommendation.price ?? recommendation.entry_price),
      quantity: quantityValue,
      positionSizeUsd: positionSizeUsdValue,
      stopLoss: parseNumber(recommendation.stop_loss ?? recommendation.stopLoss),
      takeProfit: parseNumber(recommendation.take_profit ?? recommendation.takeProfit),
      simulation: typeof simulationFlag === 'boolean' ? simulationFlag : undefined,
      reasoning: normalizeStringArray(
        metadata.reasoning ?? recommendation.reasoning ?? recommendation.reasons
      ),
      risks: normalizeStringArray(
        riskAssessment.alerts ?? riskAssessment.highlights ?? riskAssessment.notes
      ),
      analysis: typeof analysisText === 'string' ? analysisText : undefined,
      riskScore: parseNumber(riskAssessment.score ?? riskAssessment.overall_score),
    };
  }, [pendingDecision]);

  const memory = useMemo(() => {
    const metadata = pendingDecision?.message?.metadata;
    if (!metadata) {
      return null;
    }

    return metadata.memory ?? null;
  }, [pendingDecision]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const messageContent = inputValue;
    setInputValue('');
    
    try {
      await sendChatMessage(messageContent);
    } catch (error: any) {
      console.error('Failed to send message:', error);
      toast({
        title: 'Error',
        description: 'Failed to send message',
        variant: 'destructive'
      });
    }
  };

  const handleDecision = async (approved: boolean) => {
    if (!pendingDecision) {
      return;
    }

    setDecisionError(null);
    setDecisionAction(approved ? 'approve' : 'decline');

    if (approved) {
      setCurrentPhase(ExecutionPhase.EXECUTION);
    }

    setDecisionLoading(true);

    try {
      const result = await approveDecision(pendingDecision.id, approved);

      if (approved) {
        const description = result?.message || 'Monitoring exchange execution...';
        toast({
          title: 'Trade execution requested',
          description,
        });
        setCurrentPhase(ExecutionPhase.MONITORING);
      } else {
        toast({
          title: 'Recommendation declined',
          description: 'The AI will adjust the strategy based on your feedback.',
        });
        clearPendingDecision();
        setCurrentPhase(ExecutionPhase.IDLE);
      }
    } catch (error: any) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        'Failed to process decision';
      setDecisionError(message);
      toast({
        title: 'Decision processing failed',
        description: message,
        variant: 'destructive',
      });
      setCurrentPhase(ExecutionPhase.IDLE);
    } finally {
      setDecisionLoading(false);
      setDecisionAction(null);
    }
  };

  const handleModifyDecision = () => {
    if (!pendingTradeDetails) {
      return;
    }

    const actionText = pendingTradeDetails.action || 'Adjust';
    const symbolText = pendingTradeDetails.symbol ? ` ${pendingTradeDetails.symbol}` : '';

    let sizingText = '';
    if (pendingTradeDetails.positionSizeUsd) {
      sizingText = ` to ${formatCurrency(pendingTradeDetails.positionSizeUsd)}`;
    } else if (pendingTradeDetails.quantity) {
      sizingText = ` to ${pendingTradeDetails.quantity}`;
    }

    setInputValue(`Modify: ${actionText}${symbolText}${sizingText}`.trim());
  };

  const renderPhaseIndicator = () => (
    <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg">
      <div className="flex-1">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {React.createElement(phaseConfig[currentPhase].icon, { className: 'h-4 w-4' })}
            <span className={`text-sm font-medium ${phaseConfig[currentPhase].color}`}>
              {phaseConfig[currentPhase].title}
            </span>
          </div>
          <Badge variant="outline" className="text-xs">
            {phaseConfig[currentPhase].progress}%
          </Badge>
        </div>
        <Progress value={phaseConfig[currentPhase].progress} className="h-1" />
        <p className="text-xs text-muted-foreground mt-1">
          {phaseConfig[currentPhase].description}
        </p>
      </div>
    </div>
  );

  const renderMessage = (message: ExtendedChatMessage) => {
    const isUser = message.type === 'user';
    const icon = isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />;
    
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
      >
        {!isUser && (
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            {message.type === 'phase' && message.phase ? React.createElement(phaseConfig[message.phase].icon, { className: 'h-4 w-4' }) : icon}
          </div>
        )}
        
        <div className={`max-w-[85%] ${isUser ? 'order-1' : 'order-2'}`}>
          <div className={`rounded-lg px-4 py-3 shadow-sm ${
            isUser ? 'bg-primary text-primary-foreground border border-primary/20' :
            message.type === 'phase' ? 'bg-muted/90 border border-primary/20 backdrop-blur-sm' : 'bg-muted/90 backdrop-blur-sm'
          }`}>
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs opacity-70">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
              {message.phase && (
                <Badge variant="outline" className="text-xs">
                  {message.phase}
                </Badge>
              )}
            </div>
          </div>
        </div>
        
        {isUser && (
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center order-2">
            <User className="h-4 w-4 text-primary-foreground" />
          </div>
        )}
      </motion.div>
    );
  };

  return (
    <Card className={`flex flex-col h-full bg-card/95 backdrop-blur-sm border border-border/50 shadow-lg ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain className="h-5 w-5 text-primary" />
            <div>
              <CardTitle className="text-lg">Conversational Trading</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={isPaperTrading ? 'secondary' : 'default'} className="text-xs">
                  {isPaperTrading ? '📝 Paper Trading' : '💰 Live Trading'}
                </Badge>
                <Badge variant="outline" className={`text-xs ${personalityConfig[personality].color}`}>
                  {personalityConfig[personality].emoji} {personalityConfig[personality].name}
                </Badge>
                <div className="flex items-center gap-1">
                  <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className="text-xs text-muted-foreground">
                    {isConnected ? 'Connected' : 'Offline'}
                  </span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => initializeSession()}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            {onToggleExpand && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleExpand}
              >
                {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      {currentPhase !== ExecutionPhase.IDLE && (
        <div className="px-6">
          {renderPhaseIndicator()}
        </div>
      )}

      <CardContent className="flex-1 flex flex-col p-0">
        <ScrollArea className="flex-1 px-6 messages-container" style={{ maxHeight: '50vh' }}>
          <div className="space-y-4 py-4">
            <AnimatePresence>
              {messages.map((message) => (
                <div key={message.id}>
                  {renderMessage(message)}
                </div>
              ))}
            </AnimatePresence>
            
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3"
              >
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Loader className="h-4 w-4 animate-spin text-primary" />
                </div>
                <div className="bg-muted rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {currentPhase !== ExecutionPhase.IDLE 
                        ? `Processing ${phaseConfig[currentPhase].title}...`
                        : 'AI is thinking...'}
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {pendingTradeDetails && (
          <div className="px-6 pb-4">
            <Card className="border-primary/30 bg-primary/5">
              <CardHeader className="space-y-1">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Sparkles className="h-5 w-5 text-primary" />
                    {pendingTradeDetails.action && pendingTradeDetails.symbol
                      ? `${pendingTradeDetails.action} ${pendingTradeDetails.symbol}`
                      : 'Trade recommendation'}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    {typeof pendingTradeDetails.riskScore === 'number' && (
                      <Badge variant="outline" className="text-xs">
                        Risk {pendingTradeDetails.riskScore.toFixed(1)}
                      </Badge>
                    )}
                    {typeof pendingTradeDetails.confidence === 'number' && (
                      <Badge className={pendingTradeDetails.confidence >= 0.75 ? 'bg-green-600' : 'bg-amber-500'}>
                        {(pendingTradeDetails.confidence * 100).toFixed(0)}% Confidence
                      </Badge>
                    )}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Decision ID: <span className="font-mono">{pendingTradeDetails.decisionId}</span>
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Order Type</p>
                    <p className="text-sm font-medium">
                      {(pendingTradeDetails.orderType || 'MARKET').toUpperCase()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">Mode</p>
                    <p className="text-sm font-medium">
                      {pendingTradeDetails.simulation === false ? 'Live trading' : 'Simulation'}
                    </p>
                  </div>
                  {typeof pendingTradeDetails.price === 'number' && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Entry Price</p>
                      <p className="text-sm font-medium">${pendingTradeDetails.price.toFixed(2)}</p>
                    </div>
                  )}
                  {typeof pendingTradeDetails.positionSizeUsd === 'number' && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Position Size</p>
                      <p className="text-sm font-medium">{formatCurrency(pendingTradeDetails.positionSizeUsd)}</p>
                    </div>
                  )}
                  {typeof pendingTradeDetails.quantity === 'number' && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Quantity</p>
                      <p className="text-sm font-medium">{pendingTradeDetails.quantity}</p>
                    </div>
                  )}
                  {typeof pendingTradeDetails.stopLoss === 'number' && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Stop Loss</p>
                      <p className="text-sm font-medium">${pendingTradeDetails.stopLoss.toFixed(2)}</p>
                    </div>
                  )}
                  {typeof pendingTradeDetails.takeProfit === 'number' && (
                    <div>
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Take Profit</p>
                      <p className="text-sm font-medium">${pendingTradeDetails.takeProfit.toFixed(2)}</p>
                    </div>
                  )}
                </div>

                {pendingTradeDetails.analysis && (
                  <Alert className="bg-primary/10 border-primary/40">
                    <AlertTitle>AI Analysis</AlertTitle>
                    <AlertDescription className="whitespace-pre-wrap text-sm">
                      {pendingTradeDetails.analysis}
                    </AlertDescription>
                  </Alert>
                )}

                {pendingTradeDetails.reasoning.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Why the AI likes this setup</p>
                    <ul className="space-y-1">
                      {pendingTradeDetails.reasoning.map((reason, index) => (
                        <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                          <Check className="h-4 w-4 text-green-500 mt-0.5" />
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {pendingTradeDetails.risks.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Risk considerations</p>
                    <ul className="space-y-1">
                      {pendingTradeDetails.risks.map((risk, index) => (
                        <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5" />
                          {risk}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {decisionError && (
                  <Alert variant="destructive">
                    <AlertTitle>Unable to process decision</AlertTitle>
                    <AlertDescription>{decisionError}</AlertDescription>
                  </Alert>
                )}

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                    <Button
                      className="flex-1 sm:flex-none bg-green-600 hover:bg-green-700"
                      onClick={() => handleDecision(true)}
                      disabled={decisionLoading}
                    >
                      {decisionLoading && decisionAction === 'approve' ? (
                        <Loader className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <CheckCircle className="h-4 w-4 mr-2" />
                      )}
                      Approve & Execute
                    </Button>
                    <Button
                      variant="outline"
                      className="flex-1 sm:flex-none"
                      onClick={() => handleDecision(false)}
                      disabled={decisionLoading}
                    >
                      {decisionLoading && decisionAction === 'decline' ? (
                        <Loader className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <X className="h-4 w-4 mr-2" />
                      )}
                      Decline
                    </Button>
                  </div>
                  <Button
                    variant="ghost"
                    className="justify-start sm:justify-center"
                    onClick={handleModifyDecision}
                  >
                    <MessageSquare className="h-4 w-4 mr-2" />
                    Ask for changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <Separator />

        <div className="p-4">
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Say 'I have $5000 to invest' or 'Find me opportunities'..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="gap-2"
            >
              {isLoading ? <Loader className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Send
            </Button>
          </div>
          
          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2 mt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('I have $5000 to invest')}
              className="text-xs"
            >
              💰 Start Investing
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Find the best opportunities now')}
              className="text-xs"
            >
              🔍 Find Opportunities
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Show my portfolio performance')}
              className="text-xs"
            >
              📊 Portfolio
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Start autonomous trading')}
              className="text-xs"
            >
              🤖 Go Autonomous
            </Button>
          </div>

          {/* Personality Selector */}
          <div className="flex items-center gap-2 mt-3 pt-3 border-t">
            <span className="text-xs text-muted-foreground">AI Mode:</span>
            <div className="flex gap-1">
              {Object.entries(personalityConfig).map(([key, config]) => (
                <Button
                  key={key}
                  variant={personality === key ? 'default' : 'ghost'}
                  size="sm"
                  className="h-7 px-2"
                  onClick={() => setPersonality(key as AIPersonality)}
                  title={config.description}
                >
                  <span className="text-xs">{config.emoji}</span>
                </Button>
              ))}
            </div>
            {memory && (
              <Badge variant="outline" className="ml-auto text-xs">
                Trust: {memory.trustScore}/100
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ConversationalTradingInterface;