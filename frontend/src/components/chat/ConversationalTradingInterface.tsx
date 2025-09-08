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
import { apiClient } from '@/lib/api/client';
import { conversationalTradingApi, getWebSocketUrl } from '@/lib/api/tradingApi';
import { useAuthStore } from '@/store/authStore';

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
}

const ConversationalTradingInterface: React.FC<ConversationalTradingInterfaceProps> = ({
  className = '',
  isExpanded = false,
  onToggleExpand,
  isPaperTrading = false
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<ExecutionPhase>(ExecutionPhase.IDLE);
  const [personality, setPersonality] = useState<AIPersonality>(AIPersonality.BALANCED);
  const [memory, setMemory] = useState<ConversationMemory | null>(null);
  const [activeProposal, setActiveProposal] = useState<TradeProposal | null>(null);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
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

  // Initialize session with memory
  useEffect(() => {
    initializeSession();
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []);

  const initializeSession = async () => {
    try {
      // Load conversation memory
      const memoryResponse = await conversationalTradingApi.getMemory();
      if (memoryResponse.data.memory) {
        setMemory(memoryResponse.data.memory);
        
        // Add continuation message
        const continuationMsg: Message = {
          id: 'continuation',
          content: `Welcome back! I remember our last conversation about ${memoryResponse.data.memory.context.lastTopic || 'your portfolio'}. Your trust score is ${memoryResponse.data.memory.trustScore}/100. Let's continue where we left off.`,
          type: 'ai',
          timestamp: new Date().toISOString()
        };
        setMessages([continuationMsg]);
      } else {
        // New user welcome
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
      }

      // Initialize WebSocket
      initializeWebSocket();
    } catch (error) {
      console.error('Failed to initialize session:', error);
    }
  };

  const initializeWebSocket = () => {
    const wsUrl = getWebSocketUrl('/chat/ws');
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setIsConnected(true);
      ws.send(JSON.stringify({
        type: 'init',
        personality,
        isPaperTrading,
        userId: user?.id
      }));
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };
    
    ws.onclose = () => {
      setIsConnected(false);
    };
    
    setWebsocket(ws);
  };

  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'phase_update':
        setCurrentPhase(data.phase);
        addPhaseMessage(data.phase, data.details);
        break;
      
      case 'trade_proposal':
        setActiveProposal(data.proposal);
        addTradeProposalMessage(data.proposal);
        break;
      
      case 'ai_response':
        addAIMessage(data.content, data.metadata);
        break;
      
      case 'execution_result':
        handleExecutionResult(data);
        break;
    }
  };

  const addPhaseMessage = (phase: ExecutionPhase, details: string) => {
    const phaseInfo = phaseConfig[phase];
    const message: Message = {
      id: `phase-${Date.now()}`,
      content: `**${phaseInfo.title}**\n${details}`,
      type: 'phase',
      phase,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  };

  const addTradeProposalMessage = (proposal: TradeProposal) => {
    const message: Message = {
      id: `proposal-${proposal.id}`,
      content: `**Trade Proposal Ready**\n${proposal.action.toUpperCase()} ${proposal.amount} ${proposal.symbol} at $${proposal.price}`,
      type: 'trade',
      tradeProposal: proposal,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  };

  const addAIMessage = (content: string, metadata?: any) => {
    const message: Message = {
      id: `ai-${Date.now()}`,
      content,
      type: 'ai',
      metadata,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, message]);
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content: inputValue,
      type: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({
        type: 'user_message',
        content: inputValue,
        personality,
        isPaperTrading
      }));
    } else {
      // Fallback to REST API
      try {
        const response = await conversationalTradingApi.sendMessage(
          inputValue,
          personality,
          isPaperTrading,
          memory
        );
        
        handleWebSocketMessage(response);
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to send message',
          variant: 'destructive'
        });
      }
    }
    
    setIsLoading(false);
  };

  const executeTradeProposal = async (proposal: TradeProposal) => {
    setCurrentPhase(ExecutionPhase.EXECUTION);
    
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({
        type: 'execute_trade',
        proposal,
        isPaperTrading
      }));
    }
    
    setActiveProposal(null);
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
            {phaseConfig[currentPhase].icon}
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
            {message.type === 'phase' ? phaseConfig[message.phase!].icon : icon}
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