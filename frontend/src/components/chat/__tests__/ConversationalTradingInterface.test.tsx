import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConversationalTradingInterface from '../ConversationalTradingInterface';
import type { ChatMessage } from '@/store/chatStore';
import { ChatMode } from '@/store/chatStore';

const mockApproveDecision = vi.fn();
const mockClearPendingDecision = vi.fn();
const mockSendMessage = vi.fn();
const mockInitializeSession = vi.fn();
const mockSetCurrentMode = vi.fn();

const toastSpy = vi.hoisted(() => vi.fn());

const useChatStoreMock = vi.hoisted(() => vi.fn());

vi.mock('@/store/chatStore', async () => {
  const actual = await vi.importActual<any>('@/store/chatStore');
  return {
    ...actual,
    useChatStore: useChatStoreMock,
  };
});

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({ user: { id: 'user-1', email: 'user@example.com' } })),
}));

vi.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({ toast: toastSpy, dismiss: vi.fn() }),
}));

const baseAssistantMessage: ChatMessage = {
  id: 'assistant-1',
  content: 'AI analysis content',
  type: 'assistant',
  timestamp: new Date('2024-01-01T00:00:00Z').toISOString(),
  mode: ChatMode.TRADING,
  metadata: {
    recommendation: {
      action: 'buy',
      symbol: 'BTCUSDT',
      price: 42000,
      quantity: 0.5,
      reasoning: ['Momentum breakout', 'High volume confirmation'],
    },
    risk_assessment: {
      score: 0.65,
      alerts: ['Volatility elevated'],
    },
    decision_id: 'decision-1',
  },
  confidence: 0.82,
};

const buildPendingDecision = (): { id: string; message: ChatMessage; timestamp: string } => ({
  id: 'decision-1',
  message: baseAssistantMessage,
  timestamp: new Date('2024-01-01T00:01:00Z').toISOString(),
});

type PendingDecisionState = {
  id: string;
  message: ChatMessage;
  timestamp: string;
};

type StoreState = {
  messages: ChatMessage[];
  isLoading: boolean;
  sessionId: string | null;
  currentMode: ChatMode;
  sendMessage: typeof mockSendMessage;
  initializeSession: typeof mockInitializeSession;
  setCurrentMode: typeof mockSetCurrentMode;
  pendingDecision: PendingDecisionState | null;
  approveDecision: typeof mockApproveDecision;
  clearPendingDecision: typeof mockClearPendingDecision;
};

const buildStoreState = (overrides: Partial<StoreState> = {}): StoreState => ({
  messages: overrides.messages ?? [baseAssistantMessage],
  isLoading: overrides.isLoading ?? false,
  sessionId: overrides.sessionId ?? 'session-123',
  currentMode: overrides.currentMode ?? ChatMode.TRADING,
  sendMessage: overrides.sendMessage ?? mockSendMessage,
  initializeSession: overrides.initializeSession ?? mockInitializeSession,
  setCurrentMode: overrides.setCurrentMode ?? mockSetCurrentMode,
  pendingDecision: overrides.pendingDecision ?? buildPendingDecision(),
  approveDecision: overrides.approveDecision ?? mockApproveDecision,
  clearPendingDecision: overrides.clearPendingDecision ?? mockClearPendingDecision,
});

const hydrateChatStore = (overrides: Partial<StoreState> = {}) => {
  const state = buildStoreState(overrides);
  useChatStoreMock.mockReturnValue(state);
  return state;
};

const renderComponent = () => render(<ConversationalTradingInterface />);

describe('ConversationalTradingInterface - decision handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hydrateChatStore();
    mockApproveDecision.mockResolvedValue({ success: true, message: 'Decision executed successfully' });
  });

  it('approves a pending decision and surfaces toast feedback', async () => {
    renderComponent();

    const approveButton = screen.getByRole('button', { name: /approve & execute/i });
    await userEvent.click(approveButton);

    await waitFor(() => expect(mockApproveDecision).toHaveBeenCalledWith('decision-1', true));
    await waitFor(() =>
      expect(toastSpy).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Trade execution requested' }),
      ),
    );
  });

  it('declines a pending decision and clears it from the queue', async () => {
    renderComponent();

    const declineButton = screen.getByRole('button', { name: /decline/i });
    await userEvent.click(declineButton);

    await waitFor(() => expect(mockApproveDecision).toHaveBeenCalledWith('decision-1', false));
    await waitFor(() => expect(mockClearPendingDecision).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(toastSpy).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Recommendation declined' }),
      ),
    );
  });

  it('surfaces backend errors when approval fails', async () => {
    mockApproveDecision.mockRejectedValueOnce(new Error('Exchange unavailable'));
    renderComponent();

    const approveButton = screen.getByRole('button', { name: /approve & execute/i });
    await userEvent.click(approveButton);

    expect(await screen.findByText(/Unable to process decision/i)).toBeInTheDocument();
    expect(screen.getByText(/Exchange unavailable/i)).toBeInTheDocument();
    expect(mockClearPendingDecision).not.toHaveBeenCalled();
  });
});
