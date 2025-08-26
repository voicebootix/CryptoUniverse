# 🚀 CryptoUniverse Enterprise AI Money Manager - Deployment Guide

## 📋 **System Requirements**

### **Minimum Requirements**
- **OS**: Linux (Ubuntu 20.04+), macOS, Windows 10+
- **Python**: 3.11 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB minimum, 100GB recommended
- **CPU**: 2 cores minimum, 4 cores recommended

### **External Services**
- **PostgreSQL**: 15+ (Primary database)
- **Redis**: 7+ (Caching and session management)
- **Internet Connection**: Required for market data APIs

---

## 🔧 **Installation Guide**

### **1. Clone Repository**
```bash
git clone https://github.com/yourusername/cryptouniverse-enterprise.git
cd cryptouniverse-enterprise
```

### **2. Environment Setup**
```bash
# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **3. Database Setup**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb cryptouniverse
sudo -u postgres createuser cryptouser --pwprompt

# Grant permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cryptouniverse TO cryptouser;"
```

### **4. Redis Setup**
```bash
# Install Redis
sudo apt install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### **5. Environment Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (REQUIRED)
nano .env
```

**🔑 Required Environment Variables:**
```bash
# Must be configured
SECRET_KEY="your-super-secret-key-change-this"
DATABASE_URL="postgresql+asyncpg://cryptouser:yourpassword@localhost:5432/cryptouniverse"
REDIS_URL="redis://localhost:6379/0"
```

---

## 🚦 **Development Startup**

### **Quick Start**
```bash
# Activate virtual environment
source venv/bin/activate

# Start the application
python start.py
```

### **Manual Startup (Alternative)**
```bash
# Start with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### **Access Application**
- **API Documentation**: http://localhost:8000/api/docs
- **Alternative Docs**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health
- **System Status**: http://localhost:8000/api/v1/status

---

## 🏭 **Production Deployment**

### **1. Production Environment Setup**
```bash
# Set production environment
export ENVIRONMENT=production
export DEBUG=false

# Update .env file
ENVIRONMENT=production
DEBUG=false
SECRET_KEY="your-production-secret-key"
```

### **2. Using Docker (Recommended)**
```bash
# Build Docker image
docker build -t cryptouniverse-enterprise .

# Run with Docker Compose
docker-compose up -d
```

### **3. Using Gunicorn (Alternative)**
```bash
# Production server
ENVIRONMENT=production python start.py
```

### **4. Nginx Configuration** (Optional)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## 🔐 **Security Configuration**

### **API Keys Setup**
Users will configure their own exchange API keys via the web interface:

1. **Login to Admin Panel**: `/api/docs`
2. **Navigate to Exchange Management**: `/api/v1/exchanges/connect`
3. **Add Exchange API Keys**: Per-user encrypted storage

### **Rate Limiting**
The system includes conservative rate limiting to prevent exchange bans:
- **Binance**: 1200 calls/minute
- **Kraken**: 60 calls/minute  
- **KuCoin**: 100 calls/10 seconds

### **Security Headers**
```bash
# Enable in production
SECURE_HEADERS=true
HSTS_MAX_AGE=31536000
```

---

## 📊 **Market Data Configuration**

### **Free APIs (No Keys Required)**
The system uses free market data APIs:
- **CoinGecko**: 50 calls/minute (free tier)
- **CoinCap**: 100 calls/minute (free tier)
- **Exchange Rate API**: Free currency rates

### **Optional: Premium APIs**
For higher rate limits, add API keys:
```bash
COINGECKO_API_KEY="your-premium-key"
```

---

## 🎯 **AI Services Setup** (Optional)

### **AI Integration**
Add your AI API keys for enhanced trading intelligence:
```bash
OPENAI_API_KEY="your-openai-key"
CLAUDE_API_KEY="your-claude-key"
GEMINI_API_KEY="your-gemini-key"
```

### **AI Features**
- **Multi-model consensus** trading decisions
- **Market sentiment analysis**
- **Technical analysis automation**
- **Risk assessment**

---

## 📱 **Supabase Integration** (Optional)

### **Real-time Analytics**
```bash
SUPABASE_URL="your-supabase-url"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-service-key"
```

### **Benefits**
- Real-time portfolio updates
- Trading analytics dashboard
- User activity tracking
- Data backup and recovery

---

## 🔍 **System Monitoring**

### **Health Checks**
```bash
# System health
curl http://localhost:8000/health

# API status
curl http://localhost:8000/api/v1/status

# Background services
curl http://localhost:8000/metrics
```

### **Logs**
```bash
# Application logs
tail -f logs/app.log

# Error logs
tail -f logs/error.log
```

### **Performance Monitoring**
The system includes built-in monitoring:
- **CPU/Memory usage** alerts
- **Database connection** health
- **Redis connection** status
- **External API** availability

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **Database Connection Failed**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U cryptouser -d cryptouniverse
```

#### **Redis Connection Failed**
```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping
```

#### **API Rate Limits**
```bash
# Check rate limit status
curl http://localhost:8000/api/v1/admin/system/status
```

#### **Background Services Not Starting**
```bash
# Check service logs
tail -f logs/background.log

# Manual service restart
curl -X POST http://localhost:8000/api/v1/admin/system/configure
```

### **Performance Issues**
```bash
# Check system resources
htop

# Monitor API response times
curl -w "@curl-format.txt" http://localhost:8000/api/v1/status
```

---

## 🎛️ **Admin Configuration**

### **Default Admin User**
Create admin user via API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "full_name": "Admin User",
    "role": "admin"
  }'
```

### **Background Service Configuration**
Access admin panel to configure:
- **Service intervals** (how often autonomous trading runs)
- **Rate limits** per exchange
- **System maintenance** mode
- **User management** functions

---

## 📋 **Features Checklist**

### **✅ Core Features Ready**
- [x] **User Authentication** (JWT with MFA support)
- [x] **Exchange Integration** (Binance, Kraken, KuCoin)
- [x] **Manual Trading** (Buy/Sell orders)
- [x] **Autonomous Trading** (AI-driven trading)
- [x] **Simulation Mode** (Risk-free testing)
- [x] **Portfolio Management** (Real-time tracking)
- [x] **Rate Limiting** (Exchange ban protection)
- [x] **Real Market Data** (Free API integration)
- [x] **Background Services** (24/7 monitoring)
- [x] **Admin Panel** (System management)

### **✅ Enterprise Features**
- [x] **Multi-tenant** (Multiple users/organizations)
- [x] **Role-based Access** (Admin/Trader/Viewer)
- [x] **Credit System** ($0.10 per credit = $1 profit)
- [x] **Audit Logging** (Compliance ready)
- [x] **System Monitoring** (Health checks)
- [x] **API Documentation** (Swagger/ReDoc)

---

## 🚀 **Next Steps After Deployment**

### **1. Initial Setup**
1. Start the application
2. Create admin user account
3. Configure exchange API keys
4. Test simulation mode trading
5. Enable autonomous trading

### **2. User Onboarding**
1. Register user accounts
2. Connect exchange accounts
3. Set trading preferences
4. Start with simulation mode
5. Graduate to live trading

### **3. Monitoring & Maintenance**
1. Monitor system health
2. Review trading performance
3. Adjust autonomous settings
4. Scale resources as needed
5. Update market data symbols

---

## 📞 **Support**

### **Documentation**
- **API Docs**: Available at `/api/docs` when running
- **System Health**: Monitor at `/health`
- **Metrics**: View at `/metrics`

### **Logs**
- **Application**: `logs/app.log`
- **Errors**: `logs/error.log`  
- **Trading**: `logs/trading.log`
- **Background**: `logs/background.log`

### **Community**
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Comprehensive guides and examples
- **Updates**: Regular feature releases and security updates

---

**🎉 Your AI Money Manager is now ready for production use!**

**⚠️ Important**: Always start with simulation mode to test the system before using real money.
