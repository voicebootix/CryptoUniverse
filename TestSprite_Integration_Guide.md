# TestSprite Integration Guide for CryptoUniverse API

## Quick Start for TestSprite

### 1. API Documentation Files Created
- **`CryptoUniverse_API_Documentation.md`** - Complete API reference
- **`CryptoUniverse_TestSprite_API_List.json`** - Structured API list for TestSprite
- **`TestSprite_Integration_Guide.md`** - This integration guide

### 2. Using with TestSprite Dashboard

#### Step 1: Basic API Information
```
API Name: CryptoUniverse Enterprise API
API Endpoint: https://cryptouniverse.onrender.com/api/v1
Authentication Type: Bearer Token (JWT)
```

#### Step 2: Upload API Documentation
- Use the `CryptoUniverse_TestSprite_API_List.json` file
- This contains 35+ endpoints with complete testing specifications
- Includes authentication details, request/response formats, and test data

#### Step 3: Authentication Setup
```json
{
  "login_endpoint": "https://cryptouniverse.onrender.com/api/v1/auth/login",
  "test_credentials": {
    "email": "test@cryptouniverse.com", 
    "password": "TestPassword123!"
  },
  "token_header": "Authorization: Bearer {token}"
}
```

### 3. Key Testing Areas

#### Core Functionality Tests
1. **Authentication Flow**
   - Login → Get Token → Access Protected Endpoints → Refresh → Logout

2. **Trading System**
   - Enable Simulation Mode
   - Execute Manual Trades
   - Start/Stop Autonomous Trading
   - Portfolio Management

3. **Market Data**
   - Real-time Prices
   - Technical Analysis
   - Sentiment Analysis
   - Trending Coins

4. **Exchange Integration**
   - Connect Exchange (Testnet)
   - Manage Accounts
   - Verify Connectivity

#### Safety Features
- **Simulation Mode**: Always enable before trading tests
- **Rate Limiting**: 1000 requests/minute, 100 trades/minute
- **Emergency Stop**: Test emergency trading halt functionality

### 4. TestSprite Configuration

#### For Backend Testing
```
Local Port: 8000 (if running locally)
Project Path: /path/to/CryptoUniverse
Test Scope: codebase
Type: backend
```

#### Essential Test Scenarios
1. **Authentication & Security**
   - JWT token lifecycle
   - Rate limiting enforcement
   - Invalid credential handling
   - Permission-based access

2. **Trading Operations**
   - Manual trade execution
   - Autonomous mode activation
   - Portfolio balance updates
   - Risk management limits

3. **Market Data Integration**
   - Real-time price feeds
   - Technical indicator calculations
   - Sentiment analysis accuracy
   - Cross-exchange comparisons

4. **System Reliability**
   - Health check endpoints
   - Error handling
   - Graceful degradation
   - Recovery mechanisms

### 5. Test Data Requirements

#### User Accounts
```json
{
  "test_user": {
    "email": "test@cryptouniverse.com",
    "password": "TestPassword123!",
    "role": "user"
  },
  "admin_user": {
    "email": "admin@cryptouniverse.com", 
    "password": "AdminPass123!",
    "role": "admin"
  }
}
```

#### Trading Test Data
```json
{
  "test_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
  "test_exchanges": ["binance_testnet", "kraken_sandbox"],
  "test_amounts": [0.001, 0.01, 0.1],
  "risk_levels": [0.01, 0.02, 0.05]
}
```

### 6. Expected Performance Metrics

#### Response Times (Target)
- Authentication: < 500ms
- Trading Execution: < 1000ms
- Market Data: < 200ms
- Portfolio Updates: < 300ms

#### Success Rates
- API Endpoints: > 99%
- Trading Operations: > 95%
- Market Data: > 99.5%

### 7. Error Testing Scenarios

#### Authentication Errors
- Invalid credentials
- Expired tokens
- Missing permissions
- Rate limit exceeded

#### Trading Errors  
- Insufficient balance
- Invalid symbols
- Exchange connectivity issues
- Risk limit violations

#### System Errors
- Database connectivity
- Redis cache failures
- Third-party API timeouts
- High load conditions

### 8. Monitoring & Alerts

#### Health Endpoints
- `/health` - System health
- `/metrics` - Performance metrics
- `/api/v1/status` - API status

#### Key Metrics to Monitor
- Response times
- Error rates
- Trading success rates
- User authentication patterns

### 9. Production vs Development

#### Development Environment
```
Base URL: http://localhost:8000/api/v1
Database: SQLite (local)
Mode: Development with detailed logs
```

#### Production Environment
```
Base URL: https://cryptouniverse.onrender.com/api/v1
Database: PostgreSQL
Mode: Production with optimized performance
```

### 10. TestSprite Recommendations

#### Test Priorities (High to Low)
1. **Critical**: Authentication, Core Trading, Emergency Stops
2. **High**: Portfolio Management, Market Data, Exchange Integration
3. **Medium**: AI Chat, Paper Trading, Analytics
4. **Low**: Admin Functions, Advanced Features

#### Test Frequency
- **Smoke Tests**: Every deployment
- **Regression Tests**: Weekly
- **Performance Tests**: Monthly
- **Security Tests**: Quarterly

### 11. Support & Troubleshooting

#### Common Issues
- **401 Unauthorized**: 
  - Ensure JWT token is obtained via `/auth/login` first
  - Token must be fresh (8 hour expiry) 
  - Use exact format: `Authorization: Bearer {access_token}`
  - Verify test user exists and is active
- **429 Rate Limited**: Implement backoff strategy
- **500 Server Error**: Check system health endpoint

#### Debug Information
- Enable request logging in development
- Use `/health` endpoint for system status
- Check application logs for detailed errors

#### Contact Information
- **Technical Support**: support@cryptouniverse.com
- **Documentation**: Available in `/api/docs` (development only)
- **Status Page**: Check health endpoints for real-time status

---

## Files Summary

1. **CryptoUniverse_API_Documentation.md**: Comprehensive API documentation
2. **CryptoUniverse_TestSprite_API_List.json**: Structured API list for TestSprite import
3. **TestSprite_Integration_Guide.md**: This integration guide

Upload the JSON file to TestSprite and reference the markdown documentation for detailed endpoint information. The integration guide provides context for effective testing strategies.
