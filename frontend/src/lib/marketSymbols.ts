import { apiClient } from '@/lib/api/client';

const DEFAULT_SYMBOLS = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'MATIC', 'LINK', 'UNI'];
const DISCOVERY_CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const FALLBACK_CACHE_TTL_MS = 60 * 1000; // 1 minute for fallback
const CACHE_SYMBOL_LIMIT = 32;

let cachedSymbols: string[] = [...DEFAULT_SYMBOLS];
let cacheExpiry = 0;
let inflightPromise: Promise<string[]> | null = null;

const normalizeSymbol = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  let symbol = value.trim().toUpperCase();
  if (!symbol) {
    return null;
  }

  if (symbol.includes('/')) {
    symbol = symbol.split('/', 1)[0];
  }

  if (symbol.includes('-')) {
    symbol = symbol.split('-', 1)[0];
  }

  return symbol || null;
};

const extractSymbolsFromDiscovery = (payload: any): string[] => {
  const discovery = payload?.asset_discovery ?? payload?.data?.asset_discovery ?? payload;
  const detailedResults = discovery?.detailed_results ?? {};
  const symbolVolume = new Map<string, number>();

  if (detailedResults && typeof detailedResults === 'object') {
    Object.values(detailedResults).forEach((exchangeData: any) => {
      if (!exchangeData || typeof exchangeData !== 'object') {
        return;
      }

      const spotData = exchangeData.asset_types?.spot ?? {};
      const volumeLeaders = Array.isArray(spotData?.volume_leaders) ? spotData.volume_leaders : [];

      volumeLeaders.forEach((leader: any) => {
        if (!leader || typeof leader !== 'object') {
          return;
        }

        const baseAsset = leader.base_asset ?? leader.symbol ?? leader.asset;
        const symbol = normalizeSymbol(baseAsset);
        if (!symbol) {
          return;
        }

        const volumeCandidate = leader.volume_24h ?? leader.volume_usd ?? leader.volume ?? 0;
        const volume = Number(volumeCandidate) || 0;
        const current = symbolVolume.get(symbol);
        if (current === undefined || volume > current) {
          symbolVolume.set(symbol, volume);
        }
      });

      const baseAssets = Array.isArray(spotData?.base_assets) ? spotData.base_assets : [];
      baseAssets.forEach((asset: unknown) => {
        const symbol = normalizeSymbol(asset);
        if (symbol && !symbolVolume.has(symbol)) {
          symbolVolume.set(symbol, 0);
        }
      });
    });
  }

  if (!symbolVolume.size) {
    const crossSummary = discovery?.cross_exchange_summary ?? {};
    const commonAssets = Array.isArray(crossSummary?.common_assets) ? crossSummary.common_assets : [];
    commonAssets.forEach((asset: unknown) => {
      const symbol = normalizeSymbol(asset);
      if (symbol && !symbolVolume.has(symbol)) {
        symbolVolume.set(symbol, 0);
      }
    });
  }

  return Array.from(symbolVolume.entries())
    .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))
    .map(([symbol]) => symbol)
    .filter(Boolean);
};

const updateCache = (symbols: string[], ttlMs: number) => {
  const uniqueSymbols = Array.from(new Set(symbols.map((symbol) => symbol.toUpperCase())));
  cachedSymbols = uniqueSymbols.slice(0, CACHE_SYMBOL_LIMIT);
  cacheExpiry = Date.now() + ttlMs;
};

const fetchAndCacheSymbols = async (): Promise<string[]> => {
  try {
    const response = await apiClient.get('/market-analysis/exchange-assets', {
      params: { exchanges: 'all', asset_types: 'spot' },
    });

    const discoveredSymbols = extractSymbolsFromDiscovery(response.data);

    if (discoveredSymbols.length) {
      updateCache(discoveredSymbols, DISCOVERY_CACHE_TTL_MS);
    } else {
      console.warn('Market symbol discovery returned no symbols; using fallback list.');
      updateCache(DEFAULT_SYMBOLS, FALLBACK_CACHE_TTL_MS);
    }
  } catch (error) {
    console.warn('Failed to fetch discovered market symbols; using fallback list.', error);
    updateCache(DEFAULT_SYMBOLS, FALLBACK_CACHE_TTL_MS);
  } finally {
    inflightPromise = null;
  }

  return cachedSymbols;
};

export const getMarketOverviewSymbols = async (limit = 12): Promise<string[]> => {
  const now = Date.now();

  if (cachedSymbols.length && cacheExpiry > now) {
    return cachedSymbols.slice(0, limit);
  }

  if (!inflightPromise) {
    inflightPromise = fetchAndCacheSymbols();
  }

  try {
    const symbols = await inflightPromise;
    if (!symbols.length) {
      return DEFAULT_SYMBOLS.slice(0, limit);
    }

    return symbols.slice(0, limit);
  } catch (error) {
    console.warn('Market symbol discovery promise rejected; using fallback list.', error);
    return DEFAULT_SYMBOLS.slice(0, limit);
  }
};
