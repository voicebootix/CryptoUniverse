import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ChatMessage {
  id: string;
  content: string;
  type: 'user' | 'assistant';
  timestamp: string;
  mode?: ChatMode;
  metadata?: any;
  confidence?: number;
}

export interface PendingChatAction {
  type: string;
  data: any;
  messageId: string;
}

export enum ChatMode {
  TRADING = 'trading',     // Full trading workflow (main tab)
  QUICK = 'quick',         // Quick questions (widget)
  ANALYSIS = 'analysis',   // Portfolio analysis
  SUPPORT = 'support'      // Help & support
}

interface DecisionApprovalResult {
  success: boolean;
  decision_id: string;
  execution_result?: any;
  message?: string;
  error?: string;
}

interface ChatState {
  // Session Management
  sessionId: string | null;
  messages: ChatMessage[];
  currentMode: ChatMode;
  isLoading: boolean;
  
  // UI State
  isWidgetOpen: boolean;
  isWidgetMinimized: boolean;
  unreadCount: number;
  
  // Decision Management
  pendingDecision: {
    id: string;
    message: ChatMessage;
    timestamp: string;
  } | null;
  pendingAction: PendingChatAction | null;
  
  // Actions
  setSessionId: (sessionId: string) => void;
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setCurrentMode: (mode: ChatMode) => void;
  setIsLoading: (loading: boolean) => void;
  
  // Widget Actions
  toggleWidget: () => void;
  toggleMinimize: () => void;
  markAsRead: () => void;
  
  // Chat Actions
  sendMessage: (content: string) => Promise<void>;
  initializeSession: () => Promise<void>;
  clearChat: () => void;
  
  // Decision Actions
  approveDecision: (decisionId: string, approved: boolean) => Promise<DecisionApprovalResult>;
  clearPendingDecision: () => void;
  clearPendingAction: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      // Initial State
      sessionId: null,
      messages: [],
      currentMode: ChatMode.TRADING,
      isLoading: false,
      isWidgetOpen: false,
      isWidgetMinimized: false,
      unreadCount: 0,
      pendingDecision: null,
      pendingAction: null,
      
      // Session Management
      setSessionId: (sessionId) => set({ sessionId }),
      
      addMessage: (message) => set((state) => ({
        messages: [...state.messages, message].sort((a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        ),
        unreadCount: state.isWidgetMinimized || !state.isWidgetOpen ? state.unreadCount + 1 : state.unreadCount
      })),
      
      setMessages: (messages) => set({ messages }),
      
      setCurrentMode: (mode) => set({ currentMode: mode }),
      
      setIsLoading: (loading) => set({ isLoading: loading }),
      
      // Widget UI Actions
      toggleWidget: () => set((state) => ({
        isWidgetOpen: !state.isWidgetOpen,
        unreadCount: !state.isWidgetOpen ? 0 : state.unreadCount
      })),
      
      toggleMinimize: () => set((state) => ({
        isWidgetMinimized: !state.isWidgetMinimized,
        unreadCount: !state.isWidgetMinimized ? 0 : state.unreadCount
      })),
      
      markAsRead: () => set({ unreadCount: 0 }),
      
      // Chat Actions
      sendMessage: async (content: string) => {
        const { sessionId, messages, currentMode } = get();

        // Add user message immediately with unique timestamp
        const userTimestamp = new Date();
        const userMessage: ChatMessage = {
          id: `user-${Date.now()}`,
          content,
          type: 'user',
          timestamp: userTimestamp.toISOString(),
          mode: currentMode
        };

        set((state) => ({
          messages: [...state.messages, userMessage].sort((a, b) =>
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          ),
          isLoading: true
        }));

        try {
          // Import API client dynamically to avoid circular dependencies
          const { apiClient } = await import('@/lib/api/client');

          // Create session if needed
          let currentSessionId = sessionId;
          if (!currentSessionId) {
            const sessionResponse = await apiClient.post('/chat/session/new', {});
            if (sessionResponse.data.success) {
              currentSessionId = sessionResponse.data.session_id;
              set({ sessionId: currentSessionId });
            }
          }

          // Get token for SSE authentication
          const token = localStorage.getItem('auth_token');
          if (!token) {
            throw new Error('No authentication token found');
          }

          // Build SSE URL without token (use headers instead)
          const baseURL = apiClient.defaults.baseURL || '';
          const params = new URLSearchParams({
            message: content,
            session_id: currentSessionId || '',
            conversation_mode: currentMode || 'live_trading'
          });

          const url = `${baseURL}/unified-chat/stream?${params.toString()}`;

          // Create placeholder message for streaming content
          const streamingMessageId = `streaming-${Date.now()}`;
          const streamingMessage: ChatMessage = {
            id: streamingMessageId,
            content: '',
            type: 'assistant',
            timestamp: new Date(userTimestamp.getTime() + 100).toISOString(),
            mode: currentMode,
            metadata: { streaming: true }
          };

          set((state) => ({
            messages: [...state.messages, streamingMessage].sort((a, b) =>
              new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
            )
          }));

          // Use fetch-event-source for header-based authentication
          const { fetchEventSource } = await import('@microsoft/fetch-event-source');
          
          let fullContent = '';
          let streamMetadata: any = {};
          let streamCompleted = false;
          let abortController = new AbortController();

          // Set timeout for SSE connection (3 minutes)
          const timeoutId = setTimeout(() => {
            if (!streamCompleted) {
              abortController.abort();

              // Remove streaming message
              set((state) => ({
                messages: state.messages.filter(msg => msg.id !== streamingMessageId),
                isLoading: false
              }));

              const timeoutMessage: ChatMessage = {
                id: `timeout-${Date.now()}`,
                content: "The request took too long. Please try again.",
                type: 'assistant',
                timestamp: new Date(userTimestamp.getTime() + 200).toISOString(),
                mode: currentMode
              };

              get().addMessage(timeoutMessage);
            }
          }, 180000); // 3 minutes

          await fetchEventSource(url, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Accept': 'text/event-stream',
            },
            signal: abortController.signal,
            
            onopen: async (response) => {
              if (response.ok) {
                console.log('SSE connection opened');
              } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
                // Client error - don't retry
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
              }
            },

            onmessage: (event) => {
              try {
                const data = JSON.parse(event.data);
                console.log('[SSE] Received event:', data.type, 'Content length:', fullContent.length);

                switch (data.type) {
                  case 'processing':
                  case 'progress': {
                    // Optional: Update UI with progress message
                    console.log('[SSE] Progress:', data.content || data.progress?.message);
                    break;
                  }

                  case 'response':
                  case 'chunk': {
                    // Accumulate content chunks
                    if (data.content) {
                      fullContent += data.content;
                      console.log('[SSE] Accumulated content:', fullContent.length, 'chars');
                      
                      // Update the streaming message with accumulated content
                      set((state) => ({
                        messages: state.messages.map(msg =>
                          msg.id === streamingMessageId
                            ? { ...msg, content: fullContent }
                            : msg
                        )
                      }));
                    }

                    // Store metadata if provided
                    if (data.metadata) {
                      streamMetadata = { ...streamMetadata, ...data.metadata };
                    }
                    break;
                  }

                  case 'persona_enriched': {
                    // Handle persona-enriched content
                    // If replaces_previous is true, replace the entire content
                    if (data.replaces_previous && data.content) {
                      fullContent = data.content;
                    } else if (data.content) {
                      // Otherwise append the persona content
                      fullContent += data.content;
                    }
                    
                    // Update the streaming message
                    set((state) => ({
                      messages: state.messages.map(msg =>
                        msg.id === streamingMessageId
                          ? { ...msg, content: fullContent }
                          : msg
                      )
                    }));
                    
                    // Store persona metadata
                    if (data.personality) {
                      streamMetadata = { ...streamMetadata, personality: data.personality };
                    }
                    break;
                  }

                  case 'complete': {
                    console.log('[SSE] Stream complete! Total content:', fullContent.length, 'chars');
                    streamCompleted = true;
                    clearTimeout(timeoutId);
                    abortController.abort(); // Close connection

                    // Finalize the message with all metadata
                    console.log('[SSE] Finalizing message with ID:', streamingMessageId);
                    set((state) => ({
                      messages: state.messages.map(msg =>
                        msg.id === streamingMessageId
                          ? {
                              ...msg,
                              content: fullContent,
                              confidence: data.confidence || streamMetadata.confidence,
                              metadata: {
                                ...streamMetadata,
                                streaming: false,
                                intent: data.intent || streamMetadata.intent,
                                requires_approval: data.requires_approval,
                                decision_id: data.decision_id,
                                ai_analysis: data.ai_analysis
                              }
                            }
                          : msg
                      ),
                      isLoading: false,
                      pendingAction: null
                    }));

                    // Handle approval requests
                    if (data.requires_approval && data.decision_id) {
                      const finalMessage = get().messages.find(m => m.id === streamingMessageId);
                      if (finalMessage) {
                        set((state) => ({
                          ...state,
                          pendingDecision: {
                            id: data.decision_id,
                            message: finalMessage,
                            timestamp: new Date().toISOString()
                          }
                        }));
                      }
                    }

                    // Handle action requirements
                    if (data.requires_action && data.action_data) {
                      set({
                        pendingAction: {
                          type: data.action_data.type,
                          data: data.action_data,
                          messageId: streamingMessageId
                        }
                      });
                    }
                    break;
                  }

                  case 'error': {
                    streamCompleted = true;
                    clearTimeout(timeoutId);
                    abortController.abort();

                    // Remove streaming message and show error
                    set((state) => ({
                      messages: state.messages.filter(msg => msg.id !== streamingMessageId),
                      isLoading: false
                    }));

                    const errorMessage: ChatMessage = {
                      id: `error-${Date.now()}`,
                      content: data.error || "I'm having trouble processing your request. Please try again.",
                      type: 'assistant',
                      timestamp: new Date(userTimestamp.getTime() + 200).toISOString(),
                      mode: currentMode
                    };

                    get().addMessage(errorMessage);
                    break;
                  }
                }
              } catch (error) {
                console.error('Failed to parse SSE data:', error);
              }
            },

            onerror: (error) => {
              console.error('SSE connection error:', error);
              console.error('Error details:', {
                message: error.message,
                type: error.constructor.name,
                streamCompleted,
                chunksReceived: fullContent.length
              });
              
              if (!streamCompleted) {
                streamCompleted = true;
                clearTimeout(timeoutId);
                abortController.abort();

                // Remove streaming message
                set((state) => ({
                  messages: state.messages.filter(msg => msg.id !== streamingMessageId),
                  isLoading: false
                }));

                const errorMessage: ChatMessage = {
                  id: `error-${Date.now()}`,
                  content: "I'm having trouble connecting right now. Please try again in a moment.",
                  type: 'assistant',
                  timestamp: new Date(userTimestamp.getTime() + 200).toISOString(),
                  mode: currentMode
                };

                get().addMessage(errorMessage);
              }
              
              // Don't retry on error
              throw error;
            },

            openWhenHidden: true,
          });

        } catch (error) {
          console.error('Failed to send message:', error);

          const errorMessage: ChatMessage = {
            id: `error-${Date.now()}`,
            content: "I'm having trouble connecting right now. Please try again in a moment.",
            type: 'assistant',
            timestamp: new Date(userTimestamp.getTime() + 200).toISOString(), // Ensure error comes after user message
            mode: currentMode
          };

          // Use addMessage to handle unread count and timestamp ordering
          get().addMessage(errorMessage);
          set({ isLoading: false });
        }
      },
      
      initializeSession: async () => {
        try {
          const { apiClient } = await import('@/lib/api/client');
          const sessionResponse = await apiClient.post('/chat/session/new', {});
          
          if (sessionResponse.data.success) {
            const sessionId = sessionResponse.data.session_id;
            set({ sessionId });
            
            // Add welcome message based on current mode
            const { currentMode } = get();
            const welcomeMessage: ChatMessage = {
              id: 'welcome',
              content: getWelcomeMessage(currentMode),
              type: 'assistant',
              timestamp: new Date().toISOString(),
              mode: currentMode,
              metadata: {
                enhanced_chat: true,
                unified_ai: true,
                interface_type: currentMode
              }
            };

            // Initialize with welcome message
            set({ messages: [] });
            get().addMessage(welcomeMessage);
          }
        } catch (error) {
          console.error('Failed to initialize session:', error);
          
          // Fallback welcome message
          const { currentMode } = get();
          const welcomeMessage: ChatMessage = {
            id: 'welcome',
            content: getWelcomeMessage(currentMode),
            type: 'assistant',
            timestamp: new Date().toISOString(),
            mode: currentMode
          };

          // Initialize with fallback welcome message
          set({ messages: [] });
          get().addMessage(welcomeMessage);
        }
      },
      
      clearChat: () => set({
        messages: [],
        sessionId: null,
        unreadCount: 0,
        pendingDecision: null,
        pendingAction: null
      }),
      
      // Decision Actions
      approveDecision: async (decisionId: string, approved: boolean) => {
        try {
          const { apiClient } = await import('@/lib/api/client');

          const response = await apiClient.post('/chat/decision/approve', {
            decision_id: decisionId,
            approved: approved,
            modifications: {}
          });

          if (response.data.success) {
            // Add execution result message
            const executionMessage: ChatMessage = {
              id: `execution-${Date.now()}`,
              content: approved
                ? `✅ Decision executed successfully: ${response.data.message}`
                : `❌ Decision cancelled`,
              type: 'assistant',
              timestamp: new Date().toISOString(),
              metadata: {
                decision_result: true,
                execution_result: response.data.execution_result
              }
            };

            // Use addMessage to handle unread count and timestamp ordering
            get().addMessage(executionMessage);
            set({ pendingDecision: null });

            return response.data;
          }

          throw new Error(response.data.message || 'Decision approval failed');
        } catch (error) {
          console.error('Failed to approve decision:', error);

          const errorMessage: ChatMessage = {
            id: `error-${Date.now()}`,
            content: "Failed to process your decision. Please try again.",
            type: 'assistant',
            timestamp: new Date().toISOString()
          };

          // Use addMessage to handle unread count and timestamp ordering
          get().addMessage(errorMessage);

          throw error;
        }
      },
      
      clearPendingDecision: () => set({ pendingDecision: null }),

      clearPendingAction: () => set({ pendingAction: null })
    }),
    {
      name: 'chat-store',
      partialize: (state) => ({
        sessionId: state.sessionId,
        messages: state.messages,
        currentMode: state.currentMode,
        pendingDecision: state.pendingDecision,
        pendingAction: state.pendingAction
      })
    }
  )
);

function getWelcomeMessage(mode: ChatMode): string {
  switch (mode) {
    case ChatMode.TRADING:
      return `Welcome to CryptoUniverse! I'm your AI Money Manager. I'll guide you through our sophisticated 5-phase trading process. How would you like to start?`;
    
    case ChatMode.QUICK:
      return `Hi! I'm here to help with quick questions about your portfolio, market insights, or trading. What can I help you with?`;
    
    case ChatMode.ANALYSIS:
      return `Ready to analyze your portfolio! I can help with performance reviews, risk assessment, and optimization strategies.`;
    
    case ChatMode.SUPPORT:
      return `I'm here to help! Ask me about platform features, account settings, or any issues you're experiencing.`;
    
    default:
      return `Hello! I'm your AI assistant. How can I help you today?`;
  }
}