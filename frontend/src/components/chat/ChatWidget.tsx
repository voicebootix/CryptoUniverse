import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquare,
  X,
  Minimize2,
  Maximize2,
  Send,
  Bot,
  User,
  Loader
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant';
  timestamp: string;
  confidence?: number;
}

interface ChatWidgetProps {
  className?: string;
}

const ChatWidget: React.FC<ChatWidgetProps> = ({ className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize with welcome message when opened
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        content: '👋 Hi! I\'m your AI money manager. Ask me about your portfolio, trading, or market opportunities!',
        type: 'assistant',
        timestamp: new Date().toISOString(),
        confidence: 1.0
      };
      setMessages([welcomeMessage]);
    }
  }, [isOpen, messages.length]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

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
      // Use real chat API
      const { apiClient } = await import('@/lib/api/client');
      
      // Create session if needed
      if (!sessionId) {
        const sessionResponse = await apiClient.post('/chat/session/new', {});
        if (sessionResponse.data.success) {
          setSessionId(sessionResponse.data.session_id);
        }
      }
      
      // Send message to real API
      const response = await apiClient.post('/chat/message', {
        message: userMessage.content,
        session_id: sessionId
      });

      if (response.data.success) {
        const assistantMessage: ChatMessage = {
          id: response.data.message_id,
          content: response.data.content,
          type: 'assistant',
          timestamp: response.data.timestamp,
          confidence: response.data.confidence || 0.8
        };
      
        setMessages(prev => [...prev, assistantMessage]);
        
        if (isMinimized) {
          setUnreadCount(prev => prev + 1);
        }
      } else {
        throw new Error('Failed to get AI response');
      }
      
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add fallback message
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: "I'm having trouble connecting right now. Please try again in a moment.",
        type: 'assistant',
        timestamp: new Date().toISOString(),
        confidence: 0.5
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleWidget = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      setUnreadCount(0);
    }
  };

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
    if (!isMinimized) {
      setUnreadCount(0);
    }
  };

  return (
    <>
      {/* Chat Widget */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            className={`fixed bottom-20 right-6 z-50 ${className}`}
          >
            <Card className={`w-80 ${isMinimized ? 'h-14' : 'h-96'} transition-all duration-300 shadow-lg border`}>
              {/* Header */}
              <CardHeader className="flex flex-row items-center justify-between space-y-0 py-3 px-4">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm">AI Money Manager</CardTitle>
                  {unreadCount > 0 && (
                    <Badge variant="destructive" className="text-xs px-1.5 py-0.5">
                      {unreadCount}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={toggleMinimize}
                  >
                    {isMinimized ? <Maximize2 className="h-3 w-3" /> : <Minimize2 className="h-3 w-3" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={toggleWidget}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </CardHeader>

              {/* Chat Content */}
              {!isMinimized && (
                <CardContent className="flex flex-col h-80 p-0">
                  {/* Messages */}
                  <ScrollArea className="flex-1 px-4">
                    <div className="space-y-3 py-2">
                      {messages.map((message) => (
                        <div
                          key={message.id}
                          className={`flex gap-2 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          {message.type === 'assistant' && (
                            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                              <Bot className="h-3 w-3 text-primary" />
                            </div>
                          )}
                          
                          <div
                            className={`max-w-[85%] rounded-lg px-3 py-2 text-xs ${
                              message.type === 'user'
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted'
                            }`}
                          >
                            <div>{message.content}</div>
                            <div className="flex items-center justify-between mt-1 gap-2">
                              <span className="text-xs opacity-70">
                                {new Date(message.timestamp).toLocaleTimeString()}
                              </span>
                              {message.confidence && (
                                <Badge variant="outline" className="text-xs px-1 py-0">
                                  {(message.confidence * 100).toFixed(0)}%
                                </Badge>
                              )}
                            </div>
                          </div>
                          
                          {message.type === 'user' && (
                            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                              <User className="h-3 w-3 text-primary-foreground" />
                            </div>
                          )}
                        </div>
                      ))}
                      
                      {isLoading && (
                        <div className="flex gap-2">
                          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                            <Loader className="h-3 w-3 animate-spin text-primary" />
                          </div>
                          <div className="bg-muted rounded-lg px-3 py-2 text-xs">
                            <div className="flex items-center gap-1">
                              <div className="flex space-x-1">
                                <div className="w-1 h-1 bg-primary/60 rounded-full animate-bounce"></div>
                                <div className="w-1 h-1 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                <div className="w-1 h-1 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                              </div>
                              <span className="text-muted-foreground">Thinking...</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </ScrollArea>

                  {/* Input */}
                  <div className="p-3 border-t">
                    <div className="flex gap-2">
                      <Input
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Ask about your portfolio..."
                        disabled={isLoading}
                        className="text-xs"
                      />
                      <Button
                        onClick={sendMessage}
                        disabled={!inputValue.trim() || isLoading}
                        size="sm"
                        className="px-2"
                      >
                        <Send className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Action Button */}
      {!isOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="fixed bottom-6 right-6 z-50"
        >
          <Button
            onClick={toggleWidget}
            className="h-12 w-12 rounded-full shadow-lg relative"
          >
            <MessageSquare className="h-5 w-5" />
            {unreadCount > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-2 -right-2 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
              >
                {unreadCount}
              </Badge>
            )}
          </Button>
        </motion.div>
      )}
    </>
  );
};

export default ChatWidget;