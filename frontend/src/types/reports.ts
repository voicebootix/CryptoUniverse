import type { ArbitrageOpportunity } from "@/types/arbitrage";

export type ReportFormat = "csv" | "json" | "pdf";

export interface ExchangeReport {
  exchange_id: string;
  name: string;
  balance: number;
  pnl_24h: number;
  trades_24h: number;
  win_rate: number;
  connection_status: string;
  last_sync: string;
}

export interface TradingReport {
  timestamp: string;
  total_balance: number;
  total_pnl_24h: number;
  total_volume_24h: number;
  overall_win_rate: number;
  active_positions: number;
  exchanges: ExchangeReport[];
  arbitrage_opportunities: ArbitrageOpportunity[];
  performance_metrics: {
    exchange_name: string;
    trades: number;
    win_rate: number;
    avg_profit: number;
    volume: number;
  }[];
}

export interface ReportGenerationOptions {
  format: ReportFormat;
  include_sensitive_data: boolean;
  time_range: "24h" | "7d" | "30d" | "all";
  sections: ("overview" | "exchanges" | "arbitrage" | "performance")[];
}
