/**
 * Enterprise Arbitrage Type Definitions
 * Unified interface for cross-platform arbitrage data handling
 */

// Backend API Response Format (snake_case)
export interface ArbitrageOpportunityAPI {
  id?: string;
  opportunity_id?: string;
  symbol: string;
  buy_exchange: string;
  sell_exchange: string;
  buy_price: number;
  sell_price: number;
  profit_percentage: number;
  profit_bps: number;
  volume_constraint: number;
  execution_complexity: string;
  min_volume?: number;
  confidence?: number;
  risk_score?: number;
  timestamp: string;
}

// Frontend Display Format (camelCase)
export interface ArbitrageOpportunity {
  id: string;
  pair: string;
  buyExchange: string;
  sellExchange: string;
  buyPrice: number;
  sellPrice: number;
  spread: number;
  spreadPct: number;
  volume: number;
  profit: number;
  risk: 'low' | 'medium' | 'high';
  timestamp: string;
  // Enterprise robustness fields
  confidence?: number;
  minVolume?: number;
  riskScore?: number;
}

// Data transformation utilities
export class ArbitrageDataTransformer {
  /**
   * Transform API response to frontend format with enterprise-grade field mapping
   */
  static transformFromAPI(apiData: ArbitrageOpportunityAPI): ArbitrageOpportunity {
    // Enterprise ID resolution - handle multiple possible ID fields
    const id = apiData.id || 
               apiData.opportunity_id || 
               `${apiData.symbol}_${apiData.buy_exchange}_${apiData.sell_exchange}_${Date.now()}`;

    // Risk assessment mapping
    const riskScore = apiData.risk_score || 5;
    let risk: 'low' | 'medium' | 'high' = 'medium';
    if (riskScore <= 3) risk = 'low';
    else if (riskScore >= 7) risk = 'high';

    // Calculate derived fields
    const spread = apiData.sell_price - apiData.buy_price;
    const spreadPct = apiData.profit_percentage || (spread / apiData.buy_price * 100);
    
    return {
      id,
      pair: apiData.symbol,
      buyExchange: apiData.buy_exchange,
      sellExchange: apiData.sell_exchange,
      buyPrice: apiData.buy_price,
      sellPrice: apiData.sell_price,
      spread,
      spreadPct,
      volume: apiData.min_volume || apiData.volume_constraint || 0,
      profit: (spreadPct / 100) * apiData.buy_price * (apiData.min_volume || 1),
      risk,
      timestamp: apiData.timestamp,
      confidence: apiData.confidence,
      minVolume: apiData.min_volume,
      riskScore: apiData.risk_score
    };
  }

  /**
   * Transform multiple opportunities with error handling
   */
  static transformArrayFromAPI(apiDataArray: ArbitrageOpportunityAPI[]): ArbitrageOpportunity[] {
    if (!Array.isArray(apiDataArray)) {
      console.warn('ArbitrageDataTransformer: Expected array but received:', typeof apiDataArray);
      return [];
    }

    return apiDataArray.map((item, index) => {
      try {
        return this.transformFromAPI(item);
      } catch (error) {
        console.error(`ArbitrageDataTransformer: Failed to transform item at index ${index}:`, error, item);
        // Return a safe fallback
        return {
          id: `error_${index}_${Date.now()}`,
          pair: 'UNKNOWN',
          buyExchange: 'UNKNOWN',
          sellExchange: 'UNKNOWN',
          buyPrice: 0,
          sellPrice: 0,
          spread: 0,
          spreadPct: 0,
          volume: 0,
          profit: 0,
          risk: 'high' as const,
          timestamp: new Date().toISOString()
        };
      }
    });
  }
}

export default ArbitrageOpportunity;
