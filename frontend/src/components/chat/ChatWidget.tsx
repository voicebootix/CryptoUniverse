import React, { useState, useEffect, useRef, useMemo } from 'react';
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
import { useChatStore, ChatMode } from '@/store/chatStore';

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
  // Use shared chat store
  const {
    messages,
    isLoading,
    sessionId,
    currentMode,
    isWidgetOpen,
    isWidgetMinimized,
    unreadCount,
    sendMessage: sendChatMessage,
    initializeSession,
    setCurrentMode,
    toggleWidget,
    toggleMinimize,
    markAsRead
  } = useChatStore();
  
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Memoized sorted messages to prevent state mutation during render
  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => {
      // Primary: Compare timestamps numerically
      const aTime = new Date(a.timestamp).getTime();
      const bTime = new Date(b.timestamp).getTime();
      if (aTime !== bTime) return aTime - bTime;

      // Tie-breaker 1: User messages come before others
      if (a.type === 'user' && b.type !== 'user') return -1;
      if (b.type === 'user' && a.type !== 'user') return 1;

      // Tie-breaker 2: Compare by id string
      return a.id.localeCompare(b.id);
    });
  }, [messages]);

  // Initialize session when widget opens
  useEffect(() => {
    if (isWidgetOpen && (!sessionId || messages.length === 0)) {
      setCurrentMode(ChatMode.QUICK);
      initializeSession();
    }
  }, [isWidgetOpen]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current && isWidgetOpen && !isWidgetMinimized) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isWidgetOpen, isWidgetMinimized]);

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const messageContent = inputValue;
    setInputValue('');
    
    try {
      await sendChatMessage(messageContent);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Widget controls now use shared store
  const handleToggleWidget = () => {
    toggleWidget();
  };

  const handleToggleMinimize = () => {
    toggleMinimize();
  };

  return (
    <>
      {/* Chat Widget */}
      <AnimatePresence>
        {isWidgetOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            className={`fixed bottom-20 right-4 z-50 max-w-[calc(100vw-2rem)] ${className}`}
          >
            <Card className={`w-80 max-w-[calc(100vw-2rem)] sm:w-80 w-[calc(100vw-2rem)] ${isWidgetMinimized ? 'h-14' : 'h-[500px] max-h-[80vh]'} transition-all duration-300 shadow-lg border bg-card/95 backdrop-blur-sm border-border/50 overflow-hidden`}>
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
                    onClick={handleToggleMinimize}
                  >
                    {isWidgetMinimized ? <Maximize2 className="h-3 w-3" /> : <Minimize2 className="h-3 w-3" />}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={handleToggleWidget}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              </CardHeader>

              {/* Chat Content */}
              {!isWidgetMinimized && (
                <CardContent className="flex flex-col p-0 h-[calc(100%-56px)] overflow-hidden">
                  <div className="flex flex-col h-full">
                  {/* Messages */}
                  <ScrollArea className="flex-1 px-4 h-[calc(100%-60px)] overflow-y-auto" style={{ scrollBehavior: 'smooth' }}>
                    <div className="space-y-3 py-2 min-h-full">
                      {sortedMessages.map((message) => (
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
                            className={`max-w-[85%] min-w-0 rounded-lg px-3 py-2 text-xs shadow-sm break-words word-break: break-word ${
                              message.type === 'user'
                                ? 'bg-primary text-primary-foreground border border-primary/20'
                                : 'bg-muted/90 backdrop-blur-sm'
                            }`}
                          >
                            <div className="break-all whitespace-pre-wrap hyphens-auto" style={{ wordBreak: 'break-word', overflowWrap: 'anywhere' }}>{message.content}</div>
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
                          <div className="bg-muted/90 backdrop-blur-sm rounded-lg px-3 py-2 text-xs shadow-sm">
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

                      {/* Scroll anchor */}
                      <div ref={messagesEndRef} />
                    </div>
                  </ScrollArea>

                  {/* Input */}
                  <div className="p-3 border-t bg-background/90 backdrop-blur-sm shrink-0">
                    <div className="flex gap-2">
                      <Input
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type your message here..."
                        disabled={isLoading}
                        className="flex-1 text-xs bg-background border-border/60 focus:border-primary/50 placeholder:text-muted-foreground/70 min-w-0"
                      />
                      <Button
                        onClick={sendMessage}
                        disabled={!inputValue.trim() || isLoading}
                        size="sm"
                        className="px-3 py-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                      >
                        <Send className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  </div>
                </CardContent>
              )}
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Action Button */}
      {!isWidgetOpen && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="fixed bottom-6 right-4 z-50"
        >
          <Button
            onClick={handleToggleWidget}
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