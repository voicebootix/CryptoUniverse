# 🚀 CryptoUniverse Enterprise - Setup Guide

## Quick Start (5 Minutes)

### **Prerequisites**
```bash
- Python 3.11+
- PostgreSQL 15+  
- Redis 7+
- Git
```

### **1. Clone & Setup Environment**
```bash
# Clone the repository
git clone <your-repo-url>
cd cryptouniverse-enterprise

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Environment Configuration**
```bash
# Copy environment template
cp env.template .env

# Edit .env file with your settings
# Minimum required settings:
DATABASE_URL=postgresql://username:password@localhost:5432/cryptouniverse
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here-change-in-production

# Optional but recommended:
OPENAI_API_KEY=your-openai-key
BINANCE_API_KEY=your-binance-key
BINANCE_SECRET_KEY=your-binance-secret
```

### **3. Database Setup**
```bash
# Install and start PostgreSQL
# Create database
createdb cryptouniverse_enterprise

# Run database migrations (when ready)
# alembic upgrade head
```

### **4. Start Redis**
```bash
# Install and start Redis
redis-server
```

### **5. Run the Application**
```bash
# Development mode
python main.py

# Production mode  
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### **6. Access the Application**
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health
- **System Status**: http://localhost:8000/metrics

---

## 🔧 **Development Setup**

### **Code Quality Tools**
```bash
# Format code
black .
isort .

# Type checking
mypy .

# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

### **Database Migrations**
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## 🐳 **Docker Setup (Recommended)**

### **Docker Compose**
```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/cryptouniverse
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: cryptouniverse_enterprise
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    
volumes:
  postgres_data:
```

### **Run with Docker**
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

---

## 🌐 **Deployment Options**

### **1. Render (Recommended for MVP)**
```bash
# Deploy to Render
# 1. Connect GitHub repo
# 2. Set environment variables
# 3. Deploy automatically
```

### **2. Digital Ocean**
```bash
# Deploy to Digital Ocean App Platform
# 1. Create new app
# 2. Connect GitHub repo
# 3. Configure environment variables
```

### **3. AWS/GCP (Enterprise)**
```bash
# Deploy with Docker to cloud platforms
# Use managed PostgreSQL and Redis
# Set up load balancers and auto-scaling
```

---

## 📊 **Monitoring & Observability**

### **Health Monitoring**
```bash
# System health
curl http://localhost:8000/health

# Performance metrics
curl http://localhost:8000/metrics

# Service status
curl http://localhost:8000/api/v1/system/status
```

### **Logging**
```bash
# View application logs
tail -f logs/app.log

# View access logs
tail -f logs/access.log

# View error logs
tail -f logs/error.log
```

---

## 🧪 **Testing**

### **Run Tests**
```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# Load testing
locust -f tests/load_test.py

# API testing
pytest tests/api/
```

---

## 🔐 **Security Setup**

### **Environment Variables**
```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set strong database passwords
# Use environment-specific configs
# Never commit .env files
```

### **API Security**
```bash
# Enable HTTPS in production
# Use proper JWT secrets
# Set up rate limiting
# Configure CORS properly
```

---

## 📈 **Performance Tuning**

### **Database**
```sql
-- Create indexes for performance
CREATE INDEX idx_users_email_active ON users(email, is_active);
CREATE INDEX idx_trades_user_symbol ON trades(user_id, symbol);
CREATE INDEX idx_positions_status ON positions(status);
```

### **Redis**
```bash
# Configure Redis for performance
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### **Application**
```python
# Use connection pooling
# Enable response caching
# Optimize database queries
# Use async/await properly
```

---

## 🆘 **Troubleshooting**

### **Common Issues**

**Database Connection Error**
```bash
# Check PostgreSQL is running
pg_ctl status
# Check connection string in .env
# Verify database exists
```

**Redis Connection Error**
```bash
# Check Redis is running
redis-cli ping
# Should return PONG
```

**Import Errors**
```bash
# Ensure virtual environment is active
which python
# Should show venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### **Performance Issues**
```bash
# Check database query performance
# Enable SQL query logging
DATABASE_ECHO=true

# Monitor Redis memory usage
redis-cli info memory

# Check application metrics
curl http://localhost:8000/metrics
```

---

## 📞 **Support**

### **Documentation**
- **API Docs**: `/api/docs` (when running)
- **Code Documentation**: In-line comments and docstrings
- **Architecture Guide**: `MIGRATION_PROGRESS.md`

### **Development**
- **Code Formatting**: Black + isort
- **Type Checking**: mypy
- **Testing**: pytest
- **Logging**: structlog

### **Deployment**
- **Docker**: Multi-stage builds
- **CI/CD**: GitHub Actions ready
- **Monitoring**: Health checks + metrics
- **Security**: JWT + rate limiting

---

## 🎯 **Next Steps**

1. **Complete Core Services** - Finish migrating Flowise logic
2. **API Endpoints** - Create RESTful APIs
3. **Frontend Dashboard** - React/Vue.js interface
4. **Testing Suite** - Comprehensive test coverage
5. **Production Deployment** - Scale to production

**Your enterprise crypto trading platform is ready to scale! 🚀**
