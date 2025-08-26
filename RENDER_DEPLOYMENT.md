# 🚀 CryptoUniverse Enterprise - Render Deployment Guide

## Quick Deployment Steps

1. **Create Render Account**: Sign up at [render.com](https://render.com)
2. **Connect Repository**: Link your GitHub repository to Render
3. **Use Blueprint**: Upload the `render.yaml` file to deploy all services at once
4. **Configure Environment Variables**: Set the required environment variables (see below)

## 📋 Required Environment Variables for Render Dashboard

### 🔐 Security & Authentication
```
SECRET_KEY=your-super-secure-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
API_KEY_EXPIRE_DAYS=365
```

### 🌐 Application Settings
```
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-frontend-domain.com,https://app.your-domain.com
ALLOWED_HOSTS=your-render-app.onrender.com,your-custom-domain.com
```

### 🤖 AI Service API Keys
```
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
GOOGLE_AI_API_KEY=your-google-ai-api-key-here
```

### 💰 Exchange API Keys (Production)
**⚠️ IMPORTANT: Use paper trading/testnet keys initially!**

```
# Binance
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret-key

# Kraken  
KRAKEN_API_KEY=your-kraken-api-key
KRAKEN_SECRET_KEY=your-kraken-secret-key

# KuCoin
KUCOIN_API_KEY=your-kucoin-api-key
KUCOIN_SECRET_KEY=your-kucoin-secret-key
KUCOIN_PASSPHRASE=your-kucoin-passphrase
```

### 💳 Stripe Payment Processing
```
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_PUBLISHABLE_KEY=pk_live_your_publishable_key
```

### 📱 Telegram Integration
```
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

### 📊 Trading Configuration
```
DEFAULT_SIMULATION_MODE=true
MAX_POSITION_SIZE_PERCENT=5.0
DEFAULT_STOP_LOSS_PERCENT=3.0
DEFAULT_TAKE_PROFIT_PERCENT=8.0
COPY_TRADING_FEE_PERCENT=30.0
MIN_STRATEGY_TRACK_RECORD_DAYS=30
MAX_COPY_TRADING_RISK_PERCENT=15.0
```

## 🏗️ Service Architecture

Your deployment includes:

### 1. **Web Service** (`cryptouniverse-enterprise`)
- Main FastAPI application
- Handles API requests and WebSocket connections
- Auto-scaling based on traffic

### 2. **Background Worker** (`cryptouniverse-worker`)  
- Processes trading signals and market analysis
- Handles AI consensus calculations
- Executes background tasks

### 3. **Scheduler** (`cryptouniverse-scheduler`)
- Runs periodic tasks (market updates, cleanup)
- Manages scheduled trading strategies
- System maintenance tasks

### 4. **PostgreSQL Database** (`cryptouniverse-db`)
- Primary data storage
- User accounts, trading history, analytics
- Automatic backups included

### 5. **Redis Cache** (`cryptouniverse-redis`)
- Session storage and caching
- Task queue for Celery workers
- Real-time data storage

## 🔧 Deployment Process

1. **Fork/Clone**: Ensure your code is in a GitHub repository
2. **Blueprint**: Use the `render.yaml` file for one-click deployment
3. **Environment Variables**: Add all required variables in Render dashboard
4. **Database**: PostgreSQL will be automatically provisioned
5. **Redis**: Redis instance will be automatically provisioned
6. **Deploy**: Services will automatically deploy and connect

## 🏥 Health Monitoring

- **Health Endpoint**: `/health` - Comprehensive system health check
- **Metrics Endpoint**: `/metrics` - System performance metrics
- **Automatic Restarts**: Unhealthy services restart automatically
- **Logs**: Structured logging with request tracing

## 🔒 Security Features

- ✅ Non-root container user
- ✅ Environment-based configuration
- ✅ Rate limiting middleware
- ✅ CORS protection
- ✅ Request logging and monitoring
- ✅ Multi-tenant isolation
- ✅ API key authentication

## 🚨 Important Notes

### Before Going Live:
1. **Test with Paper Trading**: Set `DEFAULT_SIMULATION_MODE=true`
2. **Start Small**: Use minimal position sizes
3. **Monitor Closely**: Watch logs and metrics
4. **Backup Strategy**: Ensure database backups are configured

### Scaling:
- **Web Service**: Auto-scales based on CPU/memory
- **Workers**: Scale manually based on trading volume
- **Database**: Upgrade plan as data grows
- **Redis**: Upgrade for high-frequency trading

### Cost Optimization:
- Start with **Starter** plans (~$25/month total)
- Scale to **Standard** as you grow (~$75/month)
- **Pro** plans for high-volume trading (~$200/month)

## 📞 Support

- **Application Logs**: Available in Render dashboard
- **Database Metrics**: Monitor via Render PostgreSQL dashboard  
- **Health Checks**: Automatic monitoring and alerting
- **Email Support**: support@cryptouniverse.com

---

**Ready to deploy?** Upload `render.yaml` to your Render dashboard and let the magic happen! 🎉
