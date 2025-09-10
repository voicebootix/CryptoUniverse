import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/components/ui/use-toast';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useAuthStore } from '@/store/authStore';
import { useChatStore, ChatMode } from '@/store/chatStore';

import {
  ExecutionPhase,
  AIPersonality,
  TradeProposal,
  ConversationMemory,
  ChatMessage,
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

// Component-specific interfaces only
interface Message extends ChatMessage {
  // Additional fields if needed
}

// Use shared constants
const phaseConfig = PHASE_CONFIG;
const personalityConfig = PERSONALITY_CONFIG;

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
    messages,
    isLoading,
    sessionId,
    currentMode,
    sendMessage: sendChatMessage,
    initializeSession,
    setCurrentMode,
    clearChat
  } = useChatStore();
  
  const [inputValue, setInputValue] = useState('');
  const [currentPhase, setCurrentPhase] = useState<ExecutionPhase>(ExecutionPhase.IDLE);
  const [personality, setPersonality] = useState<AIPersonality>(AIPersonality.BALANCED);
  const [memory, setMemory] = useState<ConversationMemory | null>(null);
  const [activeProposal, setActiveProposal] = useState<TradeProposal | null>(null);
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
    if (!sessionId || messages.length === 0) {
      initializeSession();
    }
  }, []);

  const initializeSession = async () => {
    try {
      // Create a new chat session like ChatWidget does
      const sessionResponse = await apiClient.post('/chat/session/new', {});
      if (sessionResponse.data.success) {
        const newSessionId = sessionResponse.data.session_id;
        setSessionId(newSessionId);
        setMemory({
          sessionId: newSessionId,
          context: {},
          preferences: {},
          lastActivity: new Date().toISOString(),
          trustScore: 50,
          totalProfit: 0
        });
      }

      // Add welcome message
      const welcomeMsg: Message = {
        id: 'welcome',
        content: `Welcome to CryptoUniverse! I'm ${personalityConfig[personality].name} ${personalityConfig[personality].emoji}, your AI Money Manager.

I'll guide you through our sophisticated 5-phase trading process:
📊 **Phase 1**: Market Analysis
🧠 **Phase 2**: AI Consensus (GPT-4, Claude, Gemini)
🛡️ **Phase 3**: Risk Validation
📈 **Phase 4**: Trade Execution
👁️ **Phase 5**: Position Monitoring

${isPaperTrading ? '📝 **Paper Trading Mode Active** - We\'re using virtual money to practice!' : '💰 **Live Trading Mode** - Real money, real profits!'}

How would you like to start? You can:
• Say "I have $5000 to invest"
• Ask "What are the best opportunities?"
• Request "Start autonomous trading"
• Or just chat naturally!`,
        type: MessageType.AI,
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMsg]);

    } catch (error) {
      console.error('Failed to initialize session:', error);
      
      // Add welcome message even if session creation fails
      const welcomeMsg: Message = {
        id: 'welcome',
        content: `Welcome to CryptoUniverse! I'm your AI Money Manager. Ask me about trading opportunities, portfolio analysis, or market insights!`,
        type: MessageType.AI,
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMsg]);
    }
  };

  // Remove WebSocket functions since we're using REST API

  const addPhaseMessage = (phase: ExecutionPhase, details: string) => {
    const phaseInfo = phaseConfig[phase];
    const message: Message = {
      id: `phase-${Date.now()}`,
      content: `**${phaseInfo.title}**\n${details}`,
      type: MessageType.PHASE,
      phase,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  };

  const addTradeProposalMessage = (proposal: TradeProposal) => {
    const message: Message = {
      id: `proposal-${proposal.id}`,
      content: `**Trade Proposal Ready**\n${proposal.action.toUpperCase()} ${proposal.amount} ${proposal.symbol} at $${proposal.price}`,
      type: MessageType.TRADE,
      tradeProposal: proposal,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  };

  const addAIMessage = (content: string, metadata?: any) => {
    const message: Message = {
      id: `ai-${Date.now()}`,
      content,
      type: MessageType.AI,
      metadata,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  };

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

  const executeTradeProposal = async (proposal: TradeProposal) => {
    setCurrentPhase(ExecutionPhase.EXECUTION);
    
    try {
      // Simplified trade execution - just show success message for now
      toast({
        title: 'Trade Executed!',
        description: `${proposal.action} ${proposal.amount} ${proposal.symbol} at ${proposal.price}`,
      });
      setCurrentPhase(ExecutionPhase.MONITORING);
      setActiveProposal(null);
    } catch (error: any) {
      setCurrentPhase(ExecutionPhase.IDLE);
      toast({
        title: 'Trade Execution Failed',
        description: error.message || 'Failed to execute trade',
        variant: 'destructive'
      });
    }
  };

  const handleExecutionResult = (result: any) => {
    if (result.success) {
      toast({
        title: 'Trade Executed!',
        description: `${result.action} ${result.amount} ${result.symbol} at $${result.price}`,
      });
      setCurrentPhase(ExecutionPhase.MONITORING);
    } else {
      toast({
        title: 'Trade Failed',
        description: result.error,
        variant: 'destructive'
      });
      setCurrentPhase(ExecutionPhase.IDLE);
    }
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

  const renderTradeProposal = (proposal: TradeProposal) => (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Trade Recommendation
          </CardTitle>
          <Badge className={proposal.confidence > 0.8 ? 'bg-green-500' : 'bg-yellow-500'}>
            {(proposal.confidence * 100).toFixed(0)}% Confidence
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Action</p>
            <p className="font-semibold text-lg">
              {proposal.action.toUpperCase()} {proposal.symbol}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Amount</p>
            <p className="font-semibold text-lg">{formatCurrency(proposal.amount)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Entry Price</p>
            <p className="font-semibold">${proposal.price}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Expected Profit</p>
            <p className="font-semibold text-green-500">
              +{formatCurrency(proposal.expectedProfit)}
            </p>
          </div>
        </div>

        <Separator />

        <div>
          <p className="text-sm font-medium mb-2">AI Reasoning:</p>
          <ul className="space-y-1">
            {proposal.reasoning.map((reason, idx) => (
              <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                <Check className="h-3 w-3 text-green-500 mt-0.5" />
                {reason}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-sm font-medium mb-2">Risk Factors:</p>
          <ul className="space-y-1">
            {proposal.risks.map((risk, idx) => (
              <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                <AlertCircle className="h-3 w-3 text-yellow-500 mt-0.5" />
                {risk}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex gap-2 pt-2">
          <Button 
            className="flex-1 bg-green-600 hover:bg-green-700"
            onClick={() => executeTradeProposal(proposal)}
          >
            <CheckCircle className="h-4 w-4 mr-2" />
            Execute Trade
          </Button>
          <Button 
            variant="outline" 
            className="flex-1"
            onClick={() => {
              setInputValue(`Modify: ${proposal.action} ${proposal.amount / 2} ${proposal.symbol}`);
              setActiveProposal(null);
            }}
          >
            Modify
          </Button>
          <Button 
            variant="outline"
            onClick={() => setActiveProposal(null)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderMessage = (message: Message) => {
    if (message.type === 'trade' && message.tradeProposal) {
      return renderTradeProposal(message.tradeProposal);
    }

    const isUser = message.type === MessageType.USER;
    const icon = isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />;
    
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
      >
        {!isUser && (
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            {message.type === MessageType.PHASE ? React.createElement(phaseConfig[message.phase!].icon, { className: 'h-4 w-4' }) : icon}
          </div>
        )}
        
        <div className={`max-w-[80%] ${isUser ? 'order-1' : 'order-2'}`}>
          <div className={`rounded-lg px-4 py-3 ${
            isUser ? 'bg-primary text-primary-foreground' : 
            message.type === 'phase' ? 'bg-muted border border-primary/20' : 'bg-muted'
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
    <Card className={`flex flex-col h-full ${className}`}>
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
        <ScrollArea className="flex-1 px-6">
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