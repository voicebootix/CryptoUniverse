# CryptoUniverse Enterprise API Documentation

## Overview
CryptoUniverse Enterprise is a multi-tenant AI-powered cryptocurrency trading platform with enterprise-grade features. This API provides comprehensive trading, portfolio management, market analysis, and administrative capabilities.

**Base URL:** `https://your-domain.com/api/v1`
**API Version:** v1
**Authentication:** JWT Bearer Token + API Keys

---

## Authentication

### Base URLs
- **Production:** `https://cryptouniverse.onrender.com/api/v1`
- **Development:** `http://localhost:8000/api/v1`

### Authentication Methods
1. **JWT Tokens** (Primary)
2. **API Keys** (For automated systems)
3. **OAuth2** (Google integration)

### Headers Required
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

---

## Core API Endpoints

### 1. Authentication Endpoints (`/auth`)

#### POST `/api/v1/auth/login`
**Description:** Authenticate user and return JWT tokens
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "mfa_code": "123456" // Optional - required if MFA enabled
}
```
**Response:** JWT tokens (access_token, refresh_token)

#### POST `/api/v1/auth/register`
**Description:** Register new user account
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe",
  "tenant_id": "optional_tenant_id"
}
```

#### POST `/api/v1/auth/refresh`
**Description:** Refresh JWT access token
```json
{
  "refresh_token": "your_refresh_token"
}
```

#### GET `/api/v1/auth/me`
**Description:** Get current user information
**Authentication:** Required

#### POST `/api/v1/auth/logout`
**Description:** Logout and invalidate tokens
**Authentication:** Required

### 2. Trading Endpoints (`/trading`)

#### POST `/api/v1/trading/execute`
**Description:** Execute manual trade
```json
{
  "symbol": "BTCUSDT",
  "action": "buy", // buy, sell
  "amount": 0.001,
  "price": 45000.00, // Optional for market orders
  "order_type": "market", // market, limit
  "exchange": "binance"
}
```
**Authentication:** Required

#### POST `/api/v1/trading/autonomous/start`
**Description:** Start autonomous trading mode
```json
{
  "mode": "conservative", // conservative, balanced, aggressive, beast_mode
  "max_daily_trades": 10,
  "risk_level": 0.02,
  "allowed_symbols": ["BTCUSDT", "ETHUSDT"]
}
```
**Authentication:** Required

#### GET `/api/v1/trading/portfolio`
**Description:** Get current portfolio status
**Authentication:** Required
**Response:** Portfolio balance, positions, P&L, risk metrics

#### GET `/api/v1/trading/status`
**Description:** Get trading system status
**Authentication:** Required

#### GET `/api/v1/trading/recent-trades`
**Description:** Get recent trading history
**Query Parameters:**
- `limit`: Number of trades (default: 50)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol

#### POST `/api/v1/trading/stop-all`
**Description:** Emergency stop all trading activities
**Authentication:** Required (Admin role recommended)

### 3. Market Analysis Endpoints (`/market`)

#### GET `/api/v1/market/realtime-prices`
**Description:** Get real-time cryptocurrency prices
**Query Parameters:**
- `symbols`: Comma-separated list (e.g., "BTC,ETH,SOL")
```
GET /api/v1/market/realtime-prices?symbols=BTC,ETH,SOL
```

#### POST `/api/v1/market/technical-analysis`
**Description:** Get technical analysis for symbols
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT"],
  "timeframes": ["1h", "4h", "1d"],
  "indicators": ["RSI", "MACD", "EMA"]
}
```

#### POST `/api/v1/market/sentiment-analysis`
**Description:** Get market sentiment analysis
```json
{
  "symbols": ["BTC", "ETH"],
  "sources": ["twitter", "news", "reddit"]
}
```

#### GET `/api/v1/market/trending-coins`
**Description:** Get trending cryptocurrencies
**Query Parameters:**
- `limit`: Number of coins (1-50, default: 10)

#### GET `/api/v1/market/volatility-analysis`
**Description:** Get volatility analysis
**Query Parameters:**
- `symbols`: Comma-separated list

### 4. Exchange Management (`/exchanges`)

#### GET `/api/v1/exchanges/supported`
**Description:** Get list of supported exchanges
**Response:** Available exchanges (Binance, Kraken, KuCoin, Coinbase)

#### POST `/api/v1/exchanges/connect`
**Description:** Connect exchange account
```json
{
  "exchange": "binance",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "testnet": false
}
```
**Authentication:** Required

#### GET `/api/v1/exchanges/accounts`
**Description:** Get connected exchange accounts
**Authentication:** Required

#### DELETE `/api/v1/exchanges/{exchange_id}`
**Description:** Disconnect exchange account
**Authentication:** Required

### 5. Trading Strategies (`/strategies`)

#### GET `/api/v1/strategies/available`
**Description:** Get available trading strategies
**Authentication:** Required
**Response:** 25+ professional trading strategies

#### POST `/api/v1/strategies/execute`
**Description:** Execute trading strategy
```json
{
  "function": "momentum_strategy",
  "params": {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "risk_level": 0.02
  }
}
```

#### GET `/api/v1/strategies/marketplace`
**Description:** Get strategy marketplace
**Authentication:** Required

#### POST `/api/v1/strategies/{strategy_id}/activate`
**Description:** Activate trading strategy
**Authentication:** Required

#### GET `/api/v1/strategies/{strategy_id}/performance`
**Description:** Get strategy performance metrics
**Authentication:** Required

### 6. Credits System (`/credits`)

#### GET `/api/v1/credits/balance`
**Description:** Get credit balance
**Authentication:** Required

#### POST `/api/v1/credits/purchase`
**Description:** Purchase credits
```json
{
  "amount": 100,
  "payment_method": "stripe"
}
```

#### GET `/api/v1/credits/history`
**Description:** Get credit transaction history
**Authentication:** Required

### 7. API Key Management (`/api-keys`)

#### POST `/api/v1/api-keys`
**Description:** Create new API key
```json
{
  "name": "Trading Bot Key",
  "permissions": ["trading", "portfolio"],
  "expires_in_days": 90
}
```
**Authentication:** Required

#### GET `/api/v1/api-keys`
**Description:** List user's API keys
**Authentication:** Required

#### POST `/api/v1/api-keys/{key_id}/rotate`
**Description:** Rotate API key
**Authentication:** Required

### 8. Chat AI System (`/chat`)

#### POST `/api/v1/chat/message`
**Description:** Send message to AI assistant
```json
{
  "message": "What's the market outlook for Bitcoin?",
  "session_id": "optional_session_id"
}
```
**Authentication:** Required

### 9. Paper Trading (`/paper-trading`)

#### POST `/api/v1/paper-trading/setup`
**Description:** Setup paper trading account
```json
{
  "virtual_balance": 10000,
  "reset_portfolio": false
}
```

#### POST `/api/v1/paper-trading/execute`
**Description:** Execute paper trade
```json
{
  "symbol": "BTCUSDT",
  "action": "buy",
  "amount": 0.001,
  "order_type": "market"
}
```

#### GET `/api/v1/paper-trading/performance`
**Description:** Get paper trading performance
**Authentication:** Required

### 10. Telegram Integration (`/telegram`)

#### POST `/api/v1/telegram/connect`
**Description:** Connect Telegram account
```json
{
  "user_id": 123456789,
  "chat_id": 987654321,
  "username": "trading_user"
}
```

#### POST `/api/v1/telegram/send-message`
**Description:** Send message via Telegram
```json
{
  "message": "Portfolio update: +5.2% today",
  "chat_id": 123456789
}
```

### 11. Admin Endpoints (`/admin`) - Admin Role Required

#### GET `/api/v1/admin/users`
**Description:** Get all users (Admin only)
**Authentication:** Required (Admin role)

#### GET `/api/v1/admin/system/health`
**Description:** Get system health status
**Authentication:** Required (Admin role)

#### POST `/api/v1/admin/system/config`
**Description:** Update system configuration
**Authentication:** Required (Admin role)

---

## System Endpoints

### GET `/health`
**Description:** Comprehensive health check
**Authentication:** None
**Response:** System health, database, Redis, background services status

### GET `/metrics`
**Description:** System metrics for monitoring
**Authentication:** None

### GET `/api/v1/status`
**Description:** API status and feature overview
**Authentication:** None

---

## Error Handling

### Standard HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Rate Limited
- `500` - Internal Server Error

### Error Response Format
```json
{
  "error": "Detailed error message",
  "status_code": 400,
  "path": "/api/v1/trading/execute",
  "timestamp": 1634567890
}
```

---

## Rate Limiting

- **Login:** 5 attempts per 5 minutes per IP
- **API Calls:** 1000 requests per minute per user
- **Trading:** 100 trades per minute per user
- **Refresh Token:** 5 refreshes per minute per user

---

## WebSocket Endpoints

### `/ws/portfolio`
Real-time portfolio updates

### `/ws/trades`
Real-time trade notifications

### `/ws/market`
Real-time market data

---

## Testing Information

### Test Credentials
- **Email:** test@cryptouniverse.com
- **Password:** TestPassword123!

### Test Mode
Enable simulation/paper trading mode for safe testing:
```json
{
  "enable": true,
  "virtual_balance": 10000
}
```

### Postman Collection
A comprehensive Postman collection is available with pre-configured requests for all endpoints.

---

## Security Features

- **JWT Authentication** with refresh tokens
- **Rate Limiting** per endpoint
- **API Key Rotation** capabilities  
- **MFA Support** (Two-Factor Authentication)
- **OAuth2 Integration** (Google)
- **CORS Configuration** for web applications
- **Request Logging** and audit trails

---

## Production Deployment

### Environment Variables Required
```
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url
REDIS_URL=your_redis_url
ENVIRONMENT=production
ALLOWED_HOSTS=your-domain.com
```

### Performance Specifications
- **Response Time:** < 200ms average
- **Throughput:** 10,000+ requests/minute
- **Uptime:** 99.9% SLA
- **Multi-tenant:** Supports enterprise clients

---

For additional support or advanced features, contact: support@cryptouniverse.com
