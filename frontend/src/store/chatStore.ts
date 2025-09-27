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

          // Get latest messages including the just-added user message for AI context
          const latestMessages = get().messages;

          // Send message through enhanced chat endpoint (now uses unified AI manager)
          const response = await apiClient.post('/chat/message', {
            message: content,
            session_id: currentSessionId,
            mode: currentMode,
            context: {
              previous_messages: latestMessages.slice(-5), // Last 5 messages including user message
              current_tab: window.location.pathname,
              platform: 'web',
              conversation_continuity: true
            }
          });
          
          if (response.data.success) {
            // Clamp AI timestamp to ensure it's at least userTimestamp + 100ms (handles server clock skew)
            const serverTimestamp = new Date(response.data.timestamp || 0).getTime();
            const minAiTimestamp = userTimestamp.getTime() + 100;
            const aiTimestamp = new Date(Math.max(serverTimestamp, minAiTimestamp));

            const assistantMessage: ChatMessage = {
              id: response.data.message_id || `ai-${Date.now() + 1}`,
              content: response.data.content,
              type: 'assistant',
              timestamp: aiTimestamp.toISOString(),
              mode: currentMode,
              confidence: response.data.confidence, // Move confidence to top level for UI access
              metadata: {
                ...response.data.metadata,
                intent: response.data.intent,
                requires_approval: response.data.requires_approval,
                decision_id: response.data.decision_id,
                ai_analysis: response.data.ai_analysis
              }
            };

            // Use addMessage to handle unread count and timestamp ordering
            get().addMessage(assistantMessage);
            set({ isLoading: false });
            
            // Handle approval requests
            if (response.data.requires_approval && response.data.decision_id) {
              // Store decision ID for potential approval
              set((state) => ({
                ...state,
                pendingDecision: {
                  id: response.data.decision_id,
                  message: assistantMessage,
                  timestamp: new Date().toISOString()
                }
              }));
            }
          } else {
            throw new Error('Failed to get AI response');
          }
          
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
        pendingDecision: null
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
      
      clearPendingDecision: () => set({ pendingDecision: null })
    }),
    {
      name: 'chat-store',
      partialize: (state) => ({
        sessionId: state.sessionId,
        messages: state.messages,
        currentMode: state.currentMode,
        pendingDecision: state.pendingDecision
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