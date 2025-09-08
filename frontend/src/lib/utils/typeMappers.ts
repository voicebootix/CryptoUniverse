/**
 * Type Mappers - Convert between API DTOs (snake_case) and Frontend Types (camelCase)
 */

import {
  TradeExecutionResponseDTO,
  TradeExecutionResponse,
  PositionDTO,
  Position,
  MarketDataDTO,
  MarketData,
  MarketOpportunityDTO,
  MarketOpportunity,
  AIConsensusResultDTO,
  AIConsensusResult,
} from '@/types/trading';

// Trade Execution Response Mapper
export const mapTradeExecutionResponse = (dto: TradeExecutionResponseDTO): TradeExecutionResponse => ({
  success: dto.success,
  tradeId: dto.trade_id,
  action: dto.action,
  symbol: dto.symbol,
  amount: dto.amount,
  price: dto.price,
  fees: dto.fees,
  timestamp: dto.timestamp,
  status: dto.status,
  error: dto.error,
});

// Position Mapper
export const mapPosition = (dto: PositionDTO): Position => ({
  id: dto.id,
  symbol: dto.symbol,
  amount: dto.amount,
  entryPrice: dto.entry_price,
  currentPrice: dto.current_price,
  pnl: dto.pnl,
  pnlPercentage: dto.pnl_percentage,
  openedAt: dto.opened_at,
  stopLoss: dto.stop_loss,
  takeProfit: dto.take_profit,
});

// Market Data Mapper
export const mapMarketData = (dto: MarketDataDTO): MarketData => ({
  symbol: dto.symbol,
  price: dto.price,
  change24h: dto.change_24h,
  changePercentage24h: dto.change_percentage_24h,
  volume24h: dto.volume_24h,
  high24h: dto.high_24h,
  low24h: dto.low_24h,
  marketCap: dto.market_cap,
  lastUpdated: dto.last_updated,
});

// Market Opportunity Mapper
export const mapMarketOpportunity = (dto: MarketOpportunityDTO): MarketOpportunity => ({
  id: dto.id,
  type: dto.type,
  symbol: dto.symbol,
  confidence: dto.confidence,
  expectedProfit: dto.expected_profit,
  riskLevel: dto.risk_level,
  timeWindow: dto.time_window,
  description: dto.description,
  signals: dto.signals,
});

// AI Consensus Result Mapper
export const mapAIConsensusResult = (dto: AIConsensusResultDTO): AIConsensusResult => ({
  consensus: dto.consensus,
  confidence: dto.confidence,
  models: dto.models,
  weightedScore: dto.weighted_score,
  riskAssessment: dto.risk_assessment,
  recommendedPositionSize: dto.recommended_position_size,
});

// Array mappers for convenience
export const mapTradeExecutionResponses = (dtos: TradeExecutionResponseDTO[]): TradeExecutionResponse[] =>
  dtos.map(mapTradeExecutionResponse);

export const mapPositions = (dtos: PositionDTO[]): Position[] =>
  dtos.map(mapPosition);

export const mapMarketDataArray = (dtos: MarketDataDTO[]): MarketData[] =>
  dtos.map(mapMarketData);

export const mapMarketOpportunities = (dtos: MarketOpportunityDTO[]): MarketOpportunity[] =>
  dtos.map(mapMarketOpportunity);

export const mapAIConsensusResults = (dtos: AIConsensusResultDTO[]): AIConsensusResult[] =>
  dtos.map(mapAIConsensusResult);

// Reverse mappers (frontend to API)
export const mapToTradeExecutionResponseDTO = (model: TradeExecutionResponse): TradeExecutionResponseDTO => ({
  success: model.success,
  trade_id: model.tradeId,
  action: model.action,
  symbol: model.symbol,
  amount: model.amount,
  price: model.price,
  fees: model.fees,
  timestamp: model.timestamp,
  status: model.status,
  error: model.error,
});

export const mapToPositionDTO = (model: Position): PositionDTO => ({
  id: model.id,
  symbol: model.symbol,
  amount: model.amount,
  entry_price: model.entryPrice,
  current_price: model.currentPrice,
  pnl: model.pnl,
  pnl_percentage: model.pnlPercentage,
  opened_at: model.openedAt,
  stop_loss: model.stopLoss,
  take_profit: model.takeProfit,
});

export const mapToMarketDataDTO = (model: MarketData): MarketDataDTO => ({
  symbol: model.symbol,
  price: model.price,
  change_24h: model.change24h,
  change_percentage_24h: model.changePercentage24h,
  volume_24h: model.volume24h,
  high_24h: model.high24h,
  low_24h: model.low24h,
  market_cap: model.marketCap,
  last_updated: model.lastUpdated,
});

export const mapToMarketOpportunityDTO = (model: MarketOpportunity): MarketOpportunityDTO => ({
  id: model.id,
  type: model.type,
  symbol: model.symbol,
  confidence: model.confidence,
  expected_profit: model.expectedProfit,
  risk_level: model.riskLevel,
  time_window: model.timeWindow,
  description: model.description,
  signals: model.signals,
});

export const mapToAIConsensusResultDTO = (model: AIConsensusResult): AIConsensusResultDTO => ({
  consensus: model.consensus,
  confidence: model.confidence,
  models: model.models,
  weighted_score: model.weightedScore,
  risk_assessment: model.riskAssessment,
  recommended_position_size: model.recommendedPositionSize,
});