import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Opportunity,
  OpportunityApiError,
  OpportunityDiscoveryRequest,
  OpportunityDiscoveryResponse,
  OpportunityOnboardingParams,
  OpportunityOnboardingResponse,
  OpportunityScanInitiation,
  OpportunityScanProgress,
  OpportunityScanStatusResponse,
  OpportunityUserStatus,
  opportunityApi,
} from '@/lib/api/opportunityApi';

interface UseOpportunityDiscoveryOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
  pollInterval?: number;
}

type FetchScanResultsFn = (
  scanId?: string | null,
  options?: { suppressErrors?: boolean }
) => Promise<void>;

type FetchScanStatusFn = (scanId: string) => Promise<void>;

interface UseOpportunityDiscoveryReturn {
  userStatus: OpportunityUserStatus | null;
  scanStatus: OpportunityScanStatusResponse | null;
  scanResults: OpportunityDiscoveryResponse | null;
  opportunities: Opportunity[];
  totalOpportunities: number;
  scanProgress: OpportunityScanProgress | null;
  isDiscovering: boolean;
  isScanning: boolean;
  isOnboarded: boolean;
  needsOnboarding: boolean;
  hasActiveScan: boolean;
  error: string | null;
  discoverOpportunities: (payload?: OpportunityDiscoveryRequest) => Promise<OpportunityScanInitiation | null>;
  triggerOnboarding: (params?: OpportunityOnboardingParams) => Promise<OpportunityOnboardingResponse | null>;
  clearScan: () => void;
  refreshAll: () => Promise<void>;
}

const STORAGE_KEY = 'cryptouniverse:opportunity-scan-id';
const DEFAULT_REFRESH_INTERVAL = 30_000;
const DEFAULT_POLL_INTERVAL = 5_000;
const DEFAULT_SCAN_ID = 'latest';

const isBrowser = typeof window !== 'undefined';

const getStoredScanId = (): string | null => {
  if (!isBrowser) {
    return null;
  }

  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to read stored scan id', error);
    return null;
  }
};

const storeScanId = (scanId: string | null): void => {
  if (!isBrowser) {
    return;
  }

  try {
    if (scanId) {
      window.localStorage.setItem(STORAGE_KEY, scanId);
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch (error) {
    console.warn('Failed to store scan id', error);
  }
};

export const useOpportunityDiscovery = (
  options: UseOpportunityDiscoveryOptions = {}
): UseOpportunityDiscoveryReturn => {
  const [userStatus, setUserStatus] = useState<OpportunityUserStatus | null>(null);
  const [scanStatus, setScanStatus] = useState<OpportunityScanStatusResponse | null>(null);
  const [scanResults, setScanResults] = useState<OpportunityDiscoveryResponse | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [totalOpportunities, setTotalOpportunities] = useState<number>(0);
  const [scanProgress, setScanProgress] = useState<OpportunityScanProgress | null>(null);
  const [activeScanId, setActiveScanId] = useState<string | null>(() => getStoredScanId());
  const [isDiscovering, setIsDiscovering] = useState<boolean>(false);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [needsOnboarding, setNeedsOnboarding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const pollInterval = options.pollInterval ?? DEFAULT_POLL_INTERVAL;
  const refreshInterval = options.refreshInterval ?? DEFAULT_REFRESH_INTERVAL;
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef<boolean>(false);

  const isOnboarded = useMemo(() => Boolean(userStatus?.onboarding_status?.onboarded), [userStatus]);
  const hasActiveScan = useMemo(() => isScanning, [isScanning]);

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const updateScanState = useCallback((scanId: string | null, scanning: boolean) => {
    setActiveScanId(scanId);
    storeScanId(scanId);
    setIsScanning(scanning);
  }, []);

  const clearScan = useCallback(() => {
    clearPollTimer();
    updateScanState(null, false);
    setScanStatus(null);
    setScanResults(null);
    setScanProgress(null);
    setOpportunities([]);
    setTotalOpportunities(0);
    setError(null);
  }, [clearPollTimer, updateScanState]);

  const fetchUserStatus = useCallback(async () => {
    try {
      const status = await opportunityApi.getUserStatus();
      setUserStatus(status);
      setNeedsOnboarding(!status.onboarding_status?.onboarded);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch user status';
      setError(message);
    }
  }, []);

  const fetchScanResults = useCallback<FetchScanResultsFn>(async (
    scanId: string | null = null,
    { suppressErrors = false }: { suppressErrors?: boolean } = {}
  ) => {
    const effectiveScanId = scanId || activeScanId || DEFAULT_SCAN_ID;

    if (!effectiveScanId) {
      return;
    }

    try {
      const results = await opportunityApi.getScanResults(effectiveScanId);
      setScanResults(results);
      setOpportunities(results.opportunities);
      setTotalOpportunities(results.total_opportunities);
      setScanProgress(null);
      setScanStatus({
        success: true,
        status: 'complete',
        scan_id: results.scan_id,
        total_opportunities: results.total_opportunities,
        message: 'Scan completed successfully',
      });
      updateScanState(results.scan_id, false);
      setError(null);
    } catch (err) {
      if (err instanceof OpportunityApiError) {
        if (err.code === 'SCAN_IN_PROGRESS') {
          setIsScanning(true);
          return;
        }

        if (err.code === 'SCAN_NOT_FOUND') {
          if (!suppressErrors) {
            setError(err.message);
          }
          updateScanState(null, false);
          return;
        }
      }

      if (!suppressErrors) {
        const message = err instanceof Error ? err.message : 'Failed to fetch scan results';
        setError(message);
      }
    }
  }, [activeScanId, updateScanState]);

  const fetchScanStatus = useCallback<FetchScanStatusFn>(async (scanId: string) => {
    try {
      const status = await opportunityApi.getScanStatus(scanId);
      setScanStatus(status);

      if (status.scan_id && status.scan_id !== activeScanId) {
        updateScanState(status.scan_id, status.status === 'scanning');
      } else {
        setIsScanning(status.status === 'scanning');
      }

      if (status.progress) {
        setScanProgress(status.progress);
      }

      if (status.status === 'scanning' && status.partial_results) {
        setOpportunities(status.partial_results);
        setTotalOpportunities(status.partial_results.length);
      }

      if (status.status === 'complete') {
        clearPollTimer();
        await fetchScanResults(status.scan_id ?? scanId, { suppressErrors: true });
      }

      if (status.status === 'failed') {
        clearPollTimer();
        if (status.message) {
          setError(status.message);
        }
      }

      if (status.status === 'not_found') {
        clearPollTimer();
        updateScanState(null, false);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch scan status';
      setError(message);
    }
  }, [activeScanId, clearPollTimer, fetchScanResults, updateScanState]);

  const startStatusPolling = useCallback((scanId: string) => {
    clearPollTimer();

    pollTimerRef.current = setInterval(() => {
      fetchScanStatus(scanId).catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Failed to poll scan status';
        setError(message);
      });
    }, pollInterval);
  }, [clearPollTimer, fetchScanStatus, pollInterval]);

  const discoverOpportunities = useCallback(async (
    payload: OpportunityDiscoveryRequest = {}
  ): Promise<OpportunityScanInitiation | null> => {
    setIsDiscovering(true);
    setError(null);

    try {
      const response = await opportunityApi.discoverOpportunities(payload);
      const scanId = response.scan_id;

      updateScanState(scanId, true);
      setScanStatus({
        success: response.success,
        status: response.status === 'initiated' ? 'scanning' : response.status,
        scan_id: response.scan_id,
        message: response.message,
        progress: response.progress,
        total_opportunities: response.progress?.opportunities_found_so_far,
        results_url: response.results_url,
      });
      setScanProgress(response.progress ?? null);
      setOpportunities([]);
      setTotalOpportunities(0);

      if (scanId) {
        startStatusPolling(scanId);
      }

      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to initiate opportunity discovery';
      setError(message);
      return null;
    } finally {
      setIsDiscovering(false);
    }
  }, [startStatusPolling, updateScanState]);

  const triggerOnboarding = useCallback(async (
    params: OpportunityOnboardingParams = {}
  ): Promise<OpportunityOnboardingResponse | null> => {
    setIsDiscovering(true);
    setError(null);

    try {
      const response = await opportunityApi.triggerOnboarding(params);
      await fetchUserStatus();
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to trigger onboarding';
      setError(message);
      return null;
    } finally {
      setIsDiscovering(false);
    }
  }, [fetchUserStatus]);

  const refreshAll = useCallback(async () => {
    await fetchUserStatus();

    if (activeScanId) {
      await fetchScanStatus(activeScanId);
      await fetchScanResults(activeScanId, { suppressErrors: true });
    } else {
      await fetchScanResults(DEFAULT_SCAN_ID, { suppressErrors: true });
    }
  }, [activeScanId, fetchScanResults, fetchScanStatus, fetchUserStatus]);

  useEffect(() => {
    if (mountedRef.current) {
      return;
    }

    mountedRef.current = true;

    fetchUserStatus();
    fetchScanResults(DEFAULT_SCAN_ID, { suppressErrors: true });

    if (activeScanId) {
      startStatusPolling(activeScanId);
    }

    return () => {
      mountedRef.current = false;
      clearPollTimer();
    };
  }, [activeScanId, clearPollTimer, fetchScanResults, fetchUserStatus, startStatusPolling]);

  useEffect(() => {
    if (!options.autoRefresh) {
      return;
    }

    const interval = setInterval(() => {
      refreshAll().catch((err) => {
        const message = err instanceof Error ? err.message : 'Failed to refresh opportunity discovery data';
        setError(message);
      });
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [options.autoRefresh, refreshAll, refreshInterval]);

  return {
    userStatus,
    scanStatus,
    scanResults,
    opportunities,
    totalOpportunities,
    scanProgress,
    isDiscovering,
    isScanning,
    isOnboarded,
    needsOnboarding,
    hasActiveScan,
    error,
    discoverOpportunities,
    triggerOnboarding,
    clearScan,
    refreshAll,
  };
};
