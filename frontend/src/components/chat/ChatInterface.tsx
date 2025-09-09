import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '@/hooks/useWebSocket';
import {
  Send,
  Bot,
  User,
  Loader,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Brain,
  Zap,
  RefreshCw,
  Maximize2,
  Minimize2,
  Copy,
  ThumbsUp,
  ThumbsDown,
  Clock,
  DollarSign,
  BarChart3,
  Shield,
  Target
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { apiClient } from '@/lib/api/client';

interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant' | 'system' | 'trade_notification' | 'portfolio_update' | 'market_alert';
  timestamp: string;
  intent?: string;
  confidence?: number;
  metadata?: any;
}

interface ChatInterfaceProps {
  className?: string;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  className = '',
  isExpanded = false,
  onToggleExpand
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Initialize chat session
  useEffect(() => {
    initializeChatSession();
    // WebSocket cleanup is handled by the useWebSocket hook
  }, []);

  const initializeChatSession = async () => {
    try {
      // Create new chat session
      const response = await apiClient.post('/chat/session/new', {});

      if (response.data.success) {
        setSessionId(response.data.session_id);
        
        // Session created, WebSocket will connect automatically via hook
        
        // Add welcome message
        const welcomeMessage: ChatMessage = {
          id: 'welcome',
          content: `👋 Welcome to CryptoUniverse AI Money Manager!

I'm your comprehensive AI assistant for cryptocurrency portfolio management. I can help you with:

🔹 **Portfolio Analysis** - Review performance, allocation, and optimization
🔹 **Trade Execution** - Execute buy/sell orders with AI analysis  
🔹 **Risk Management** - Assess and mitigate portfolio risks
🔹 **Rebalancing** - Optimize your asset allocation
🔹 **Market Opportunities** - Discover new investment prospects
🔹 **Strategy Optimization** - Fine-tune your trading strategies

Just chat with me naturally! How can I help you manage your crypto investments today?`,
          type: 'assistant',
          timestamp: new Date().toISOString(),
          confidence: 1.0
        };
        
        setMessages([welcomeMessage]);
      }
    } catch (error) {
      // Failed to initialize chat session - handled by UI error state
      toast({
        title: 'Connection Error',
        description: 'Failed to initialize chat session. Please refresh the page.',
        variant: 'destructive',
      });
    }
  };

  // Use the shared WebSocket hook with proper authentication and reconnection
  const { lastMessage, connectionStatus, sendMessage: sendWsMessage } = useWebSocket(
    sessionId ? `/api/v1/chat/ws/${sessionId}` : '',
    {
      onOpen: () => {
        setIsConnected(true);
      },
      onClose: () => {
        setIsConnected(false);
      },
      onMessage: (data) => {
        if (data.type === 'chat_response') {
          const newMessage: ChatMessage = {
            id: data.message_id,
            content: data.content,
            type: 'assistant',
            timestamp: data.timestamp,
            intent: data.intent,
            confidence: data.confidence,
            metadata: data.metadata
          };
          
          setMessages(prev => [...prev, newMessage]);
          setIsLoading(false);
        } else if (data.type === 'connection_established') {
          // Chat connection established
        }
      },
      onError: () => {
        setIsConnected(false);
      },
      reconnectAttempts: 3,
      reconnectInterval: 2000
    }
  );

  // Update connection status based on WebSocket hook
  useEffect(() => {
    setIsConnected(connectionStatus === 'Open');
  }, [connectionStatus]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading || !sessionId) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputValue,
      type: 'user',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // TEMPORARY FIX: Force REST API only until WebSocket is fixed
      // TODO: Re-enable WebSocket after debugging
      if (false && isConnected && sendWsMessage) {
        // WebSocket disabled for debugging
        sendWsMessage({
          type: 'chat_message',
          message: inputValue,
          session_id: sessionId
        });
      } else {
        // Fallback to REST API
        const response = await apiClient.post('/chat/message', {
          message: inputValue,
          session_id: sessionId
        });

        if (response.data.success) {
          const assistantMessage: ChatMessage = {
            id: response.data.message_id,
            content: response.data.content,
            type: 'assistant',
            timestamp: response.data.timestamp,
            intent: response.data.intent,
            confidence: response.data.confidence,
            metadata: response.data.metadata
          };
          
          setMessages(prev => [...prev, assistantMessage]);
        } else {
          throw new Error('Failed to send message');
        }
        
        setIsLoading(false);
      }
    } catch (error) {
      // Failed to send message - show error to user
      toast({
        title: 'Message Failed',
        description: 'Unable to send message. Please check your connection.',
        variant: 'destructive',
      });
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getMessageIcon = (type: string, intent?: string) => {
    switch (type) {
      case 'user':
        return <User className="h-4 w-4" />;
      case 'assistant':
        switch (intent) {
          case 'trade_execution':
            return <TrendingUp className="h-4 w-4 text-green-500" />;
          case 'risk_assessment':
            return <Shield className="h-4 w-4 text-yellow-500" />;
          case 'portfolio_analysis':
            return <BarChart3 className="h-4 w-4 text-blue-500" />;
          case 'emergency_command':
            return <AlertTriangle className="h-4 w-4 text-red-500" />;
          default:
            return <Bot className="h-4 w-4 text-primary" />;
        }
      case 'trade_notification':
        return <DollarSign className="h-4 w-4 text-green-500" />;
      case 'portfolio_update':
        return <BarChart3 className="h-4 w-4 text-blue-500" />;
      case 'market_alert':
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      default:
        return <Brain className="h-4 w-4" />;
    }
  };

  const getConfidenceBadge = (confidence?: number) => {
    if (!confidence) return null;
    
    const getVariant = (score: number) => {
      if (score >= 0.9) return 'default';
      if (score >= 0.7) return 'secondary';
      return 'outline';
    };

    const getColor = (score: number) => {
      if (score >= 0.9) return 'text-green-500';
      if (score >= 0.7) return 'text-yellow-500';
      return 'text-red-500';
    };

    return (
      <Badge variant={getVariant(confidence)} className={`text-xs ${getColor(confidence)}`}>
        {(confidence * 100).toFixed(0)}% confidence
      </Badge>
    );
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied',
      description: 'Message copied to clipboard',
    });
  };

  const formatMessageContent = (content: string, metadata?: any) => {
    // Handle special formatting for different message types
    if (metadata?.trade_params) {
      return (
        <div className="space-y-3">
          <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
          {metadata.requires_confirmation && (
            <div className="flex gap-2 mt-4">
              <Button size="sm" className="bg-green-600 hover:bg-green-700">
                ✅ Execute Trade
              </Button>
              <Button size="sm" variant="outline">
                📋 More Details
              </Button>
              <Button size="sm" variant="outline">
                ❌ Cancel
              </Button>
            </div>
          )}
        </div>
      );
    }

    if (metadata?.emergency_mode) {
      return (
        <div className="space-y-3">
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
            <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />
          </div>
          {metadata.available_actions && (
            <div className="grid grid-cols-2 gap-2 mt-4">
              {metadata.available_actions.map((action: string) => (
                <Button key={action} size="sm" variant="outline" className="text-xs">
                  {action.replace('_', ' ').toUpperCase()}
                </Button>
              ))}
            </div>
          )}
        </div>
      );
    }

    // Default formatting with line breaks
    return <div dangerouslySetInnerHTML={{ __html: content.replace(/\n/g, '<br/>') }} />;
  };

  return (
    <Card className={`flex flex-col h-full ${className}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle className="text-lg">AI Money Manager</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-xs text-muted-foreground">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => initializeChatSession()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
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
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        {/* Messages Area */}
        <ScrollArea className="flex-1 px-6">
          <div className="space-y-4 py-4">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.type !== 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      {getMessageIcon(message.type, message.intent)}
                    </div>
                  )}
                  
                  <div className={`max-w-[80%] ${message.type === 'user' ? 'order-1' : 'order-2'}`}>
                    <div
                      className={`rounded-lg px-4 py-3 ${
                        message.type === 'user'
                          ? 'bg-primary text-primary-foreground ml-auto'
                          : 'bg-muted'
                      }`}
                    >
                      <div className="text-sm">
                        {formatMessageContent(message.content, message.metadata)}
                      </div>
                      
                      <div className="flex items-center justify-between mt-2 gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </span>
                          {message.intent && (
                            <Badge variant="outline" className="text-xs">
                              {message.intent.replace('_', ' ')}
                            </Badge>
                          )}
                          {getConfidenceBadge(message.confidence)}
                        </div>
                        
                        {message.type === 'assistant' && (
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={() => copyToClipboard(message.content)}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                            >
                              <ThumbsUp className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                            >
                              <ThumbsDown className="h-3 w-3" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {message.type === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center order-2">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                </motion.div>
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
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-sm text-muted-foreground">AI is thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        <Separator />

        {/* Input Area */}
        <div className="p-4">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me about your portfolio, trading, or market opportunities..."
                disabled={isLoading || !isConnected}
                className="pr-12"
              />
              {inputValue && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-1 top-1/2 transform -translate-y-1/2 h-8 w-8 p-0"
                  onClick={() => setInputValue('')}
                >
                  ×
                </Button>
              )}
            </div>
            
            <Button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading || !isConnected}
              className="gap-2"
            >
              {isLoading ? (
                <Loader className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          
          {/* Quick Action Buttons */}
          <div className="flex flex-wrap gap-2 mt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Show me my portfolio performance')}
              disabled={isLoading}
              className="text-xs"
            >
              📊 Portfolio
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('What are the best opportunities right now?')}
              disabled={isLoading}
              className="text-xs"
            >
              🔍 Opportunities
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Analyze the risk in my current positions')}
              disabled={isLoading}
              className="text-xs"
            >
              🛡️ Risk Analysis
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInputValue('Should I rebalance my portfolio?')}
              disabled={isLoading}
              className="text-xs"
            >
              ⚖️ Rebalance
            </Button>
          </div>
          
          {!isConnected && (
            <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Connection lost. Messages will be sent via API.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ChatInterface;