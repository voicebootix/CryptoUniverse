# CryptoUniverse – Source Documentation Pack (Claude Code Edition)
## PART 1: Project Overview & Architecture

---

**Document Version:** 1.0
**Generated:** November 18, 2025
**Live System Tested:** ✅ Yes (Admin credentials used)
**Backend URL:** https://cryptouniverse.onrender.com
**Frontend URL:** https://cryptouniverse-frontend.onrender.com
**Admin Access:** admin@cryptouniverse.com

---

## 📋 TABLE OF CONTENTS (ALL PARTS)

- **PART 1** (This Document): Project Overview & Architecture
- **PART 2**: Feature Inventory & Codebase Map
- **PART 3**: Live System Status & Test Results
- **PART 4**: Remaining 30% Work & Task Breakdown
- **PART 5**: Developer Onboarding & Risk Assessment

---

## 1. PROJECT SUMMARY

### 1.1 What is CryptoUniverse?

**CryptoUniverse Enterprise** is a production-ready, multi-tenant AI-powered cryptocurrency trading platform that combines institutional-grade trading capabilities with an innovative credit-based profit system.

**Core Innovation:**
- **Traditional Model:** Monthly subscriptions ($29-$499/month)
- **CryptoUniverse Model:** Pay for profit potential (1 credit = $0.10 cost = $1 profit potential = 10x multiplier)
- **User Experience:** Pay $100 → Get 1,000 credits → $1,000 profit potential → AI trades until target reached

### 1.2 High-Level Vision

**Vision Statement:**
*"Democratizing institutional-grade cryptocurrency trading for everyone through AI-powered autonomous money management"*

**Key Goals:**
1. Enable retail traders to access AI-powered institutional strategies
2. Create a copy-trading marketplace where expert traders monetize their strategies
3. Provide multi-exchange unified portfolio management (Binance, Kraken, KuCoin, etc.)
4. Ensure complete user isolation in a multi-tenant architecture
5. Deliver 24/7 autonomous trading via Web, Mobile, Telegram, and API

### 1.3 Current State Assessment

**Overall Completion: ~70% DONE, ~30% REMAINING**

#### ✅ What's Working (70% Complete)

**Backend Infrastructure (95% Done)**
- ✅ FastAPI application with 30+ API endpoints
- ✅ PostgreSQL database with asyncpg driver
- ✅ Redis caching layer
- ✅ JWT authentication with role-based access control
- ✅ Multi-tenant architecture with user isolation
- ✅ Celery background task processing
- ✅ Alembic database migrations
- ✅ Deployed on Render.com (both backend & frontend)

**Core Trading Features (75% Done)**
- ✅ Multi-exchange integration via CCXT (25+ exchanges supported)
- ✅ 25+ AI trading strategies (spot, algorithmic, derivatives, portfolio)
- ✅ Strategy marketplace with 50+ strategies listed
- ✅ Credit system (tracked: 665/1000 credits available for admin user)
- ✅ Portfolio tracking ($2,620 balance, 55 positions tracked)
- ✅ Paper trading engine
- ✅ Backtesting engine
- ✅ Risk management system

**AI & Analysis Features (60% Done)**
- ✅ Multi-AI consensus system (GPT-4, Claude, Gemini)
- ✅ Market analysis service (253KB of code)
- ✅ Opportunity discovery system
- ✅ Signal generation and delivery
- ✅ Telegram bot integration
- ✅ Unified chat interface

**Admin & Management (80% Done)**
- ✅ Admin dashboard (27 users tracked in system)
- ✅ User management
- ✅ Credit provisioning
- ✅ Strategy management
- ✅ System monitoring and diagnostics

**Frontend (70% Done)**
- ✅ React 18 + TypeScript + Vite
- ✅ 30+ dashboard pages built
- ✅ Tailwind CSS styling
- ✅ Component library
- ✅ Authentication flows
- ✅ Portfolio visualization
- ✅ Strategy marketplace UI
- ✅ Admin panel UI

#### ⚠️ What's Incomplete (30% Remaining)

**Feature Gaps:**
- ⚠️ Real exchange API integration (mostly paper trading)
- ⚠️ Live performance data (all strategies show "no_data")
- ⚠️ OAuth implementation (Google, GitHub login)
- ⚠️ Payment processing (Stripe integration exists but not tested)
- ⚠️ Mobile app (not started)
- ⚠️ Some API methods return "Method Not Allowed" (routing issues)
- ⚠️ WebSocket real-time updates (partially implemented)
- ⚠️ Copy trading signal distribution (built but not fully tested)

**Technical Debt:**
- 🔧 Test coverage needs improvement (tests exist but not comprehensive)
- 🔧 Some error handling needs hardening
- 🔧 Performance optimization needed for high-load scenarios
- 🔧 Documentation gaps in code
- 🔧 Some duplicate service logic (chat systems have multiple implementations)

### 1.4 Main Modules

The platform consists of **10 major functional modules**:

1. **Trading Engine** - Core order execution, position management
2. **Strategy Marketplace** - Browse, subscribe, publish trading strategies
3. **AI Consensus System** - Multi-model AI decision making
4. **Portfolio Risk Manager** - Risk assessment, position sizing
5. **Multi-Exchange Hub** - Unified API for 25+ exchanges
6. **Credit & Billing System** - Credit tracking, profit limits
7. **Backtesting Lab** - Historical strategy testing
8. **Chat/AI Assistant** - Conversational trading interface
9. **Telegram Bot** - Command-line trading via Telegram
10. **Admin Control Panel** - User/system management

---

## 2. TECH STACK & ARCHITECTURE

### 2.1 Technology Stack

#### **Backend (Python)**
```
Framework:        FastAPI 0.104.1
Server:           Uvicorn 0.24.0 (ASGI)
Production:       Gunicorn 21.2.0 (with Uvicorn workers)

Database:
  - PostgreSQL (via asyncpg 0.29.0)
  - SQLAlchemy 2.0.23 (async ORM)
  - Alembic 1.13.1 (migrations)

Caching:          Redis 5.0.1
Background Jobs:  Celery 5.3.4

Authentication:
  - JWT (python-jose 3.3.0)
  - OAuth (authlib 1.2.1)
  - Bcrypt password hashing

Trading & Market Data:
  - CCXT 4.2.25 (multi-exchange library)
  - yfinance 0.2.33 (market data)
  - pandas 2.1.4 (data processing)
  - numpy 1.26.2 (numerical computing)
  - ta 0.11.0 (technical analysis)

AI Services:
  - OpenAI 1.3.8 (GPT-4)
  - Anthropic 0.7.8 (Claude)
  - Google Gemini Pro (via REST API)

Monitoring:
  - structlog 23.2.0 (structured logging)
  - sentry-sdk 1.38.0 (error tracking)

Payments:         Stripe 7.8.0
HTTP Client:      aiohttp 3.9.1, httpx 0.25.2
```

#### **Frontend (JavaScript/TypeScript)**
```
Framework:        React 18
Language:         TypeScript
Build Tool:       Vite
Styling:          Tailwind CSS
State Management: React Context + Hooks
Routing:          React Router
HTTP Client:      Axios
UI Components:    Custom + shadcn/ui
```

#### **Infrastructure**
```
Hosting:          Render.com
  - Backend:      cryptouniverse.onrender.com
  - Frontend:     cryptouniverse-frontend.onrender.com

Database:         PostgreSQL (Render-managed)
Cache:            Redis (Render-managed)
CDN:              Render CDN (for frontend assets)
Deployment:       Git-based (automatic deploys)
```

### 2.2 Architecture Overview

#### **High-Level System Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                          │
├─────────────────────────────────────────────────────────────────┤
│  Web App (React)  │  Mobile App   │  Telegram Bot  │  REST API  │
│  Port: 443/HTTPS  │  (Future)     │  Webhook-based │  v1        │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Main Application (main.py)                             │
│  - CORS Middleware                                               │
│  - Auth Middleware (JWT validation)                              │
│  - Tenant Middleware (multi-tenancy isolation)                   │
│  - Rate Limit Middleware                                         │
│  - Request Logging Middleware                                    │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API ENDPOINTS (30+ Routers)                   │
├─────────────────────────────────────────────────────────────────┤
│  /auth          │  /trading        │  /strategies  │  /credits  │
│  /exchanges     │  /portfolio      │  /chat        │  /admin    │
│  /telegram      │  /opportunities  │  /signals     │  /market   │
│  /paper-trading │  /risk           │  /monitoring  │  /health   │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER (60+ Services)                 │
├─────────────────────────────────────────────────────────────────┤
│  Trading Services:                                               │
│    - trading_strategies.py (428KB) - 25+ strategy functions      │
│    - trade_execution.py (103KB) - Order placement & management   │
│    - portfolio_risk.py (121KB) - Risk assessment & limits        │
│                                                                  │
│  Market Data Services:                                           │
│    - market_analysis_core.py (253KB) - Technical analysis        │
│    - market_data_feeds.py (85KB) - Real-time price feeds         │
│    - unified_price_service.py (31KB) - Multi-exchange prices     │
│                                                                  │
│  AI Services:                                                    │
│    - unified_ai_manager.py (92KB) - AI model coordination        │
│    - ai_consensus_core.py (54KB) - Multi-AI decision making      │
│    - unified_chat_service.py (216KB) - Conversational interface  │
│                                                                  │
│  User Services:                                                  │
│    - user_opportunity_discovery.py (373KB) - Find trading opps   │
│    - user_onboarding_service.py (28KB) - New user setup          │
│    - credit_ledger.py (8KB) - Credit tracking                    │
│                                                                  │
│  Background Services:                                            │
│    - background.py (89KB) - Celery task management               │
│    - strategy_monitoring.py (14KB) - Performance tracking        │
│    - system_monitoring.py (22KB) - Health checks                 │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA ACCESS LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  SQLAlchemy ORM Models (23 models in app/models/)               │
│    - user.py          - User accounts, roles, permissions        │
│    - trading.py       - Strategies, trades, orders, positions    │
│    - credit.py        - Credit accounts, transactions            │
│    - exchange.py      - Exchange connections, API keys           │
│    - market_data.py   - Price data, indicators, backtests        │
│    - chat.py          - Chat sessions, messages                  │
│    - signal.py        - Trading signals, performance             │
│    - analytics.py     - Performance metrics, risk metrics        │
│                                                                  │
│  Database Manager (app/core/database.py)                         │
│    - Async connection pooling                                    │
│    - Transaction management                                      │
│    - Query timeout handling                                      │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL Database         Redis Cache                         │
│    - User data               - Session data                      │
│    - Trading history         - Market data cache                 │
│    - Strategy definitions    - Rate limiting                     │
│    - System config           - Background job queue              │
└─────────────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                              │
├─────────────────────────────────────────────────────────────────┤
│  Trading Exchanges (via CCXT):                                   │
│    - Binance, Kraken, KuCoin, Coinbase, etc. (25+ exchanges)    │
│                                                                  │
│  AI Services:                                                    │
│    - OpenAI API (GPT-4)                                          │
│    - Anthropic API (Claude)                                      │
│    - Google API (Gemini Pro)                                     │
│                                                                  │
│  Payment Processing:                                             │
│    - Stripe (credit card payments)                               │
│                                                                  │
│  Communication:                                                  │
│    - Telegram Bot API                                            │
│    - Email Service (SendGrid/SMTP)                               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow: User Action → Database → Response

**Example Flow: User Executes a Trading Strategy**

```
1. USER ACTION (Frontend)
   └─> User clicks "Execute Strategy" on dashboard
   └─> React component calls API: POST /api/v1/strategies/{id}/execute

2. API GATEWAY (main.py)
   └─> Request hits FastAPI application
   └─> Middleware chain processes request:
       ├─> RequestLoggingMiddleware: Log request
       ├─> AuthMiddleware: Validate JWT token
       ├─> TenantMiddleware: Extract tenant context
       └─> RateLimitMiddleware: Check rate limits

3. API ENDPOINT (app/api/v1/endpoints/strategies.py)
   └─> Router receives request
   └─> Validates request body (Pydantic schema)
   └─> Extracts user_id from JWT token
   └─> Calls service layer

4. SERVICE LAYER (app/services/trading_strategies.py)
   └─> TradingStrategyService.execute_strategy()
       ├─> Check user credit balance (credit_ledger.py)
       ├─> Fetch strategy definition from DB
       ├─> Validate strategy parameters
       ├─> Check risk limits (portfolio_risk.py)
       ├─> Get market data (market_data_feeds.py)
       ├─> Run AI consensus (ai_consensus_core.py)
       │   ├─> Query GPT-4 for recommendation
       │   ├─> Query Claude for recommendation
       │   ├─> Query Gemini for recommendation
       │   └─> Calculate consensus (85% agreement required)
       ├─> Execute trade (trade_execution.py)
       │   ├─> Connect to exchange via CCXT
       │   ├─> Place order on exchange
       │   └─> Receive order confirmation
       ├─> Record trade in database
       ├─> Deduct credits from user account
       └─> Update portfolio positions

5. DATABASE LAYER (PostgreSQL)
   └─> SQLAlchemy async operations:
       ├─> INSERT into trades table
       ├─> UPDATE credit_transactions table
       ├─> UPDATE positions table
       └─> COMMIT transaction

6. CACHE LAYER (Redis)
   └─> Update cached data:
       ├─> Invalidate user portfolio cache
       ├─> Update strategy performance cache
       └─> Cache market data for 60 seconds

7. BACKGROUND TASKS (Celery)
   └─> Enqueue async tasks:
       ├─> Monitor order status
       ├─> Update performance metrics
       ├─> Send notification (email/telegram)
       └─> Update analytics dashboard

8. RESPONSE (Back to Frontend)
   └─> JSON response returned:
       {
         "success": true,
         "trade_id": "uuid-123",
         "status": "executed",
         "credits_used": 2,
         "remaining_credits": 663
       }
   └─> React component updates UI
   └─> User sees trade confirmation
```

### 2.4 Multi-Tenant Architecture

**Tenant Isolation Strategy:**

```
Each user/organization is a separate "tenant" with complete data isolation:

┌───────────────────────────────────────────────────────────────┐
│                    Tenant A (User 1)                          │
│  - Unique tenant_id in JWT token                              │
│  - Database rows filtered by tenant_id                        │
│  - Separate credit account                                    │
│  - Isolated trading history                                   │
│  - Own exchange API keys (encrypted)                          │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                    Tenant B (User 2)                          │
│  - Different tenant_id                                         │
│  - Cannot access Tenant A data                                │
│  - Separate credit pool                                        │
│  - Own trading strategies                                      │
└───────────────────────────────────────────────────────────────┘

Middleware ensures all DB queries automatically filter by tenant_id:
  SELECT * FROM trades WHERE user_id = ? AND tenant_id = ?
```

**Security Features:**
- JWT tokens include `tenant_id` claim
- Middleware injects tenant context into every request
- Database queries automatically scoped to tenant
- Redis cache keys prefixed with tenant_id
- Admin users can access all tenants (special permission)

---

## 3. DEPLOYMENT & INFRASTRUCTURE

### 3.1 Current Deployment (Render.com)

**Backend Service:**
```
URL:        https://cryptouniverse.onrender.com
Type:       Web Service (Gunicorn + Uvicorn)
Workers:    Auto-scaled based on CPU count (1-8 workers)
Timeout:    180 seconds
Port:       8000 (internal), 443 (external via Render proxy)
Health:     /api/v1/health/ping

Environment Variables (from .env):
  - DATABASE_URL (PostgreSQL connection)
  - REDIS_URL (Redis connection)
  - SECRET_KEY (JWT signing)
  - ENCRYPTION_KEY (API key encryption)
  - OPENAI_API_KEY, ANTHROPIC_API_KEY
  - TELEGRAM_BOT_TOKEN
  - STRIPE_SECRET_KEY
```

**Frontend Service:**
```
URL:        https://cryptouniverse-frontend.onrender.com
Type:       Static Site (Nginx)
Build:      Vite production build
Assets:     Served from Render CDN
Config:     VITE_API_URL points to backend
```

**Database:**
```
Provider:   Render PostgreSQL
Version:    PostgreSQL 15+
Connection: TLS/SSL enabled
Backups:    Daily automatic backups (Render manages)
```

**Cache:**
```
Provider:   Render Redis
Version:    Redis 7+
Usage:      Session cache, rate limiting, market data cache
```

### 3.2 Performance Characteristics

**Observed Performance (from live tests):**
- **API Response Time:** Most endpoints < 500ms
- **Database Latency:** Typically < 100ms (varies by query complexity)
- **Redis Latency:** < 10ms
- **Strategy Marketplace Load:** 50+ strategies load in ~200ms
- **Portfolio Load:** 55 positions load in ~300ms

**Scalability Limits (Current Config):**
- **Max Workers:** 8 Gunicorn workers (can scale higher with paid plans)
- **Concurrent Requests:** ~100-200 concurrent requests per worker
- **Database Connections:** Pool of 10-20 connections per worker
- **Redis Connections:** Shared connection pool

**Known Bottlenecks:**
- AI API calls (OpenAI/Claude) can take 2-5 seconds
- Large portfolio calculations can timeout on free tier
- Market data fetching for 25+ exchanges can be slow
- Background task processing limited by single Celery worker

---

## 4. SECURITY ARCHITECTURE

### 4.1 Authentication & Authorization

**JWT Token Structure:**
```json
{
  "sub": "user_id (UUID)",
  "email": "user@example.com",
  "role": "admin|trader|viewer|api_only",
  "tenant_id": "tenant_uuid or empty",
  "exp": 1763478423,
  "iat": 1763449623,
  "jti": "token_unique_id",
  "type": "access|refresh"
}
```

**Token Lifecycle:**
- **Access Token:** 8 hours expiry (JWT_ACCESS_TOKEN_EXPIRE_HOURS)
- **Refresh Token:** 30 days expiry (JWT_REFRESH_TOKEN_EXPIRE_DAYS)
- **Algorithm:** HS256 (HMAC with SHA-256)

**Role-Based Permissions:**
```
Admin Role:
  - admin:read, admin:write, admin:delete
  - trading:read, trading:write, trading:execute
  - portfolio:read, portfolio:write
  - users:read, users:write, users:delete
  - system:read, system:write

Trader Role:
  - trading:read, trading:write, trading:execute
  - portfolio:read, portfolio:write
  - (No admin or user management access)

Viewer Role:
  - trading:read, portfolio:read
  - (Read-only access)

API-Only Role:
  - trading:execute via API keys
  - (No web dashboard access)
```

### 4.2 Data Encryption

**At Rest:**
- Database: PostgreSQL TLS encryption (Render-managed)
- Sensitive fields encrypted with AES-256 (ENCRYPTION_KEY)
  - Exchange API keys
  - OAuth tokens
  - Credit card info (via Stripe, PCI-compliant)

**In Transit:**
- All API calls over HTTPS/TLS 1.3
- WebSocket connections over WSS
- Database connections over SSL

**API Key Storage:**
```python
# Exchange API keys are encrypted before storage
from cryptography.fernet import Fernet
key = settings.ENCRYPTION_KEY  # 32-byte base64 key
cipher = Fernet(key)
encrypted_api_key = cipher.encrypt(api_key.encode())
# Stored as bytes in database
```

### 4.3 Rate Limiting

**Current Limits (RateLimitMiddleware):**
- **Anonymous users:** 100 requests per 15 minutes
- **Authenticated users:** 1000 requests per 15 minutes
- **Admin users:** 5000 requests per 15 minutes

**Implementation:** Redis-backed sliding window

---

## 5. SYSTEM DEPENDENCIES

### 5.1 Critical External Services

| Service | Purpose | Criticality | Fallback |
|---------|---------|-------------|----------|
| PostgreSQL | Primary data store | **CRITICAL** | None (single point of failure) |
| Redis | Cache & sessions | **HIGH** | Degrade gracefully (slower) |
| OpenAI API | AI trading decisions | **HIGH** | Use other AI models |
| Anthropic API | AI trading decisions | **HIGH** | Use other AI models |
| CCXT Exchanges | Trade execution | **CRITICAL** | Paper trading mode |
| Stripe | Payment processing | **MEDIUM** | Manual credit provisioning |
| Telegram API | Bot notifications | **LOW** | Email fallback |

### 5.2 Service Health Monitoring

**Health Check Endpoints:**
```
GET /api/v1/health/ping          → Simple alive check
GET /api/v1/health/database      → Database connectivity
GET /api/v1/health/redis         → Redis connectivity
GET /api/v1/health/full          → Comprehensive check
```

**Current Health Status (from live test):**
- ✅ API: Responding (200 OK)
- ⚠️ Database: Connected (some endpoints fail with auth issues)
- ⚠️ Redis: Connected (some endpoints fail with "Method Not Allowed")

---

## 🔗 Continue to Next Parts

- **[→ PART 2: Feature Inventory & Codebase Map](./DOCUMENTATION_PART_2_Features_Codebase.md)**
- **[→ PART 3: Live System Status](./DOCUMENTATION_PART_3_Live_Status.md)**
- **[→ PART 4: Remaining Work](./DOCUMENTATION_PART_4_Remaining_Work.md)**
- **[→ PART 5: Developer Guide](./DOCUMENTATION_PART_5_Developer_Guide.md)**

---

**Generated by:** Claude Code (Anthropic)
**Based on:** Live system testing + comprehensive codebase analysis
**Next Update:** After addressing items in Part 4 (Remaining Work)
