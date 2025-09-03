export interface ExchangeSettings {
  // Connection Parameters
  timeout_seconds: number;
  rate_limit_per_minute: number;
  max_retries: number;
  connection_pool_size: number;

  // Arbitrage Automation
  auto_execute_arbitrage: boolean;
  min_profit_threshold: number;
  max_position_size: number;
  risk_level: "conservative" | "moderate" | "aggressive";

  // Trading Preferences
  default_order_type: "market" | "limit";
  max_slippage_percent: number;
  order_routing_priority: "speed" | "cost" | "balanced";
  enable_smart_routing: boolean;

  // Data Refresh
  price_update_interval: number;
  balance_update_interval: number;
  orderbook_depth: number;
  enable_real_time: boolean;

  // UI/UX Preferences
  default_view: "grid" | "table" | "chart";
  show_advanced_metrics: boolean;
  enable_sound_notifications: boolean;
  theme_mode: "dark" | "light" | "auto";

  // Security Settings
  show_api_keys: boolean;
  enable_audit_logging: boolean;
  require_2fa_for_trades: boolean;
  session_timeout_minutes: number;
}

// Default settings constant
export const DEFAULT_EXCHANGE_SETTINGS: ExchangeSettings = {
  // Connection Parameters
  timeout_seconds: 30,
  rate_limit_per_minute: 100,
  max_retries: 3,
  connection_pool_size: 5,

  // Arbitrage Automation
  auto_execute_arbitrage: false,
  min_profit_threshold: 0.5,
  max_position_size: 10000,
  risk_level: "moderate",

  // Trading Preferences
  default_order_type: "market",
  max_slippage_percent: 1.0,
  order_routing_priority: "balanced",
  enable_smart_routing: true,

  // Data Refresh
  price_update_interval: 5,
  balance_update_interval: 30,
  orderbook_depth: 20,
  enable_real_time: true,

  // UI/UX Preferences
  default_view: "grid",
  show_advanced_metrics: false,
  enable_sound_notifications: true,
  theme_mode: "dark",

  // Security Settings
  show_api_keys: false,
  enable_audit_logging: true,
  require_2fa_for_trades: false,
  session_timeout_minutes: 60,
};
