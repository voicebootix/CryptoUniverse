import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiClient } from '@/lib/api/client';
import type { MarketOpportunity } from '@/types/trading';
import { toast } from '@/components/ui/use-toast';

type ScanStatus = 'idle' | 'initiated' | 'scanning' | 'completed' | 'failed';

type PollingTimer = ReturnType<typeof setInterval> | null;

type OpportunityDiscoveryOptions = {
  force_refresh?: boolean;
  include_strategy_recommendations?: boolean;
  filter_by_risk_level?: string | null;
  min_profit_potential?: number | null;
  max_required_capital?: number | null;
  preferred_timeframes?: string[] | null;
  opportunity_type?: string[] | null;
  strategy_types?: string[] | null;
};

type DiscoveryResponse = {
  success: boolean;
  scan_id: string;
  status: string;
  message?: string;
  results_url?: string;
  poll_url?: string;
};

type StatusResponse = {
  status: ScanStatus;
  progress?: {
    strategies_completed?: number;
    total_strategies?: number;
    percentage?: number;
  };
  results_ready?: boolean;
  next_poll_seconds?: number;
  message?: string;
};

type ResultsResponse = {
  success: boolean;
  opportunities: MarketOpportunity[];
  total_opportunities: number;
  scan_id: string;
  last_updated: string;
};

export interface OpportunityDiscoveryState {
  scanId: string | null;
  status: ScanStatus;
  isScanning: boolean;
  progress: StatusResponse['progress'];
  results: MarketOpportunity[];
  totalOpportunities: number;
  lastUpdated: string | null;
  error: string | null;
  discover: (options?: OpportunityDiscoveryOptions) => Promise<void>;
  refreshStatus: (scanId?: string, fetchResultsOnComplete?: boolean) => Promise<void>;
  reset: () => void;
}

const DEFAULT_SCAN_ID = 'opportunity_scan_default';
const POLLING_INTERVAL_MS = 3000;

const extractErrorCode = (error: any): string | undefined => {
  return (
    error?.code ||
    error?.response?.data?.code ||
    error?.response?.data?.error_code ||
    error?.response?.data?.detail?.code
  );
};

const extractScanId = (error: any): string | undefined => {
  return (
    error?.response?.data?.scan_id ||
    error?.response?.data?.scanId ||
    error?.response?.data?.existing_scan_id ||
    error?.scan_id ||
    error?.scanId
  );
};

export const useOpportunityDiscovery = (): OpportunityDiscoveryState => {
  const [scanId, setScanId] = useState<string | null>(null);
  const [status, setStatus] = useState<ScanStatus>('idle');
  const [progress, setProgress] = useState<StatusResponse['progress']>();
  const [results, setResults] = useState<MarketOpportunity[]>([]);
  const [totalOpportunities, setTotalOpportunities] = useState<number>(0);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingTimerRef = useRef<PollingTimer>(null);
  const currentScanRef = useRef<string | null>(null);

  const clearPolling = useCallback(() => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
  }, []);

  const fetchResults = useCallback(
    async (activeScanId: string) => {
      try {
        const { data } = await apiClient.get<ResultsResponse>(`/opportunities/results/${activeScanId}`);
        if (data?.success !== false) {
          setResults(data?.opportunities ?? []);
          setTotalOpportunities(data?.total_opportunities ?? data?.opportunities?.length ?? 0);
          setLastUpdated(data?.last_updated ?? new Date().toISOString());
          setStatus('completed');
          setError(null);
        } else {
          throw new Error(data?.message || 'Failed to fetch opportunity results');
        }
      } catch (err: any) {
        const message =
          err?.response?.data?.message ||
          err?.message ||
          'Unable to fetch opportunity discovery results';
        setError(message);
        toast({
          title: 'Failed to load opportunity results',
          description: message,
          variant: 'destructive'
        });
      } finally {
        clearPolling();
      }
    },
    [clearPolling]
  );

  const refreshStatus = useCallback(
    async (nextScanId?: string, fetchResultsOnComplete = true) => {
      const activeScanId = nextScanId ?? currentScanRef.current ?? scanId ?? DEFAULT_SCAN_ID;
      if (!activeScanId) {
        return;
      }

      try {
        const { data } = await apiClient.get<StatusResponse>(`/opportunities/status/${activeScanId}`);
        if (!data) {
          return;
        }

        setStatus(data.status ?? 'scanning');
        setProgress(data.progress);
        setError(null);

        if (data.status === 'completed' || data.results_ready) {
          if (fetchResultsOnComplete) {
            await fetchResults(activeScanId);
          } else {
            clearPolling();
          }
        } else if (data.status === 'failed') {
          clearPolling();
        }
      } catch (err: any) {
        if (err?.response?.status === 404) {
          // Scan may have expired, stop polling
          clearPolling();
          setStatus('failed');
          setError('Scan not found or expired');
        } else {
          const message = err?.response?.data?.message || err?.message || 'Failed to refresh opportunity scan status';
          setError(message);
        }
      }
    },
    [clearPolling, fetchResults, scanId]
  );

  const startStatusPolling = useCallback(
    (activeScanId: string) => {
      clearPolling();
      pollingTimerRef.current = setInterval(async () => {
        await refreshStatus(activeScanId, false);
      }, POLLING_INTERVAL_MS);
    },
    [clearPolling, refreshStatus]
  );

  const discover = useCallback(
    async (options?: OpportunityDiscoveryOptions) => {
      setStatus('initiated');
      setError(null);
      setResults([]);
      setProgress(undefined);

      const payload = {
        force_refresh: options?.force_refresh ?? false,
        include_strategy_recommendations: options?.include_strategy_recommendations ?? true,
        filter_by_risk_level: options?.filter_by_risk_level,
        min_profit_potential: options?.min_profit_potential,
        max_required_capital: options?.max_required_capital,
        preferred_timeframes: options?.preferred_timeframes,
        opportunity_type: options?.opportunity_type ?? options?.strategy_types,
      };

      try {
        const { data } = await apiClient.post<DiscoveryResponse>('/opportunities/discover', payload);
        const newScanId = data?.scan_id ?? DEFAULT_SCAN_ID;

        setScanId(newScanId);
        currentScanRef.current = newScanId;
        setStatus((data?.status as ScanStatus) ?? 'initiated');
        setError(null);
        startStatusPolling(newScanId);
        toast({
          title: 'Opportunity discovery started',
          description: 'Scanning your strategies for new opportunities.',
        });
      } catch (err: any) {
        const errorCode = extractErrorCode(err);
        const derivedScanId = extractScanId(err);
        const effectiveScanId = derivedScanId ?? currentScanRef.current ?? scanId ?? DEFAULT_SCAN_ID;

        if (errorCode === 'SCAN_IN_PROGRESS') {
          setStatus('scanning');
          setScanId(effectiveScanId);
          currentScanRef.current = effectiveScanId;
          startStatusPolling(effectiveScanId);
          toast({
            title: 'Scan already running',
            description: 'Resuming progress on the active opportunity scan.',
          });
          return;
        }

        const message =
          err?.response?.data?.message ||
          err?.message ||
          'Failed to initiate opportunity discovery';
        setError(message);
        setStatus('failed');
        toast({
          title: 'Failed to start opportunity discovery',
          description: message,
          variant: 'destructive'
        });
      }
    },
    [scanId, startStatusPolling]
  );

  const reset = useCallback(() => {
    clearPolling();
    setScanId(null);
    setStatus('idle');
    setProgress(undefined);
    setResults([]);
    setTotalOpportunities(0);
    setLastUpdated(null);
    setError(null);
    currentScanRef.current = null;
  }, [clearPolling]);

  useEffect(() => () => clearPolling(), [clearPolling]);

  const state = useMemo<OpportunityDiscoveryState>(
    () => ({
      scanId,
      status,
      isScanning: status === 'scanning' || status === 'initiated',
      progress,
      results,
      totalOpportunities,
      lastUpdated,
      error,
      discover,
      refreshStatus,
      reset,
    }),
    [discover, error, lastUpdated, progress, refreshStatus, results, scanId, status, totalOpportunities]
  );

  return state;
};

