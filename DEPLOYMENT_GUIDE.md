# 🚀 CryptoUniverse Deployment Guide

## Critical Environment Variables Required

Your application is failing to start because these **REQUIRED** environment variables are missing:

### 🔐 **IMMEDIATE ACTION NEEDED**

Set these environment variables in your deployment platform:

```bash
# CRITICAL - App won't start without these:
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random-32-chars-minimum
DATABASE_URL=postgresql://username:password@hostname:5432/database_name
```

---

## 🛠 **Platform-Specific Setup**

### **Render.com**
1. Go to your Render dashboard
2. Select your service
3. Go to **Environment** tab
4. Add these variables:

```bash
SECRET_KEY=crypto-universe-secret-key-2024-production-32-chars-min
DATABASE_URL=postgresql://user:password@dpg-xxxxx-a.oregon-postgres.render.com/database_name
REDIS_URL=redis://red-xxxxx:6379
```

### **Railway**
```bash
railway variables set SECRET_KEY=your-secret-key-here
railway variables set DATABASE_URL=postgresql://...
```

### **Heroku**
```bash
heroku config:set SECRET_KEY=your-secret-key-here
heroku config:set DATABASE_URL=postgresql://...
```

### **Digital Ocean App Platform**
Add in App Spec or Environment Variables section.

---

## 🔑 **How to Generate SECRET_KEY**

```python
# Run this in Python to generate a secure secret key:
import secrets
print(secrets.token_urlsafe(32))
```

Or use this one (change it!):
```bash
SECRET_KEY=crypto-universe-2024-super-secret-key-production-trading-system-secure
```

---

## 🗄 **Database Setup**

### **Option 1: Render PostgreSQL (Recommended)**
1. Create PostgreSQL database on Render
2. Copy the **External Database URL** 
3. Set as `DATABASE_URL` environment variable

### **Option 2: Supabase**
1. Create project at supabase.com
2. Get connection string from Settings → Database
3. Format: `postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:5432/postgres`

### **Option 3: Railway PostgreSQL**
1. Add PostgreSQL plugin
2. Use provided `DATABASE_URL`

---

## 🚀 **Minimal Working Configuration**

**Set ONLY these 2 variables to get started:**

```bash
SECRET_KEY=crypto-universe-2024-production-secret-key-minimum-32-characters
DATABASE_URL=postgresql://username:password@hostname:5432/dbname
```

**Optional but recommended:**
```bash
REDIS_URL=redis://hostname:6379
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-key
```

---

## ✅ **Verify Deployment**

After setting variables:
1. **Redeploy** your service
2. Check logs for successful startup
3. Visit your app URL
4. You should see FastAPI docs at `/docs`

---

## 🎯 **Quick Fix Commands**

If using **Render**, add these in Environment Variables:

```bash
SECRET_KEY = crypto-universe-production-secret-2024-trading-system-secure
DATABASE_URL = postgresql://your_db_connection_string_here
ENVIRONMENT = production
DEBUG = false
PORT = 10000
```

**Your crypto trading system is ready once these are set! 💎🚀**
