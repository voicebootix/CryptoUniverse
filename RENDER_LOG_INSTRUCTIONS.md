# How to Access Render Logs for CryptoUniverse

## Quick Access Links
1. **Dashboard**: https://dashboard.render.com
2. **Your Service**: Look for `cryptouniverse` or similar
3. **Direct Logs**: `https://dashboard.render.com/web/srv-[YOUR-SERVICE-ID]/logs`

## Finding Your Service ID
Your Render service URL format: `https://dashboard.render.com/web/srv-XXXXXXXX`
The `srv-XXXXXXXX` part is your service ID.

## What We're Looking For

### Error 1: Admin Endpoints (500)
```
AttributeError: 'AsyncSession' object has no attribute 'query'
File "/app/api/v1/endpoints/admin.py", line XXX
```

### Error 2: Telegram (500)  
```
NameError: name 'self' is not defined
File "/app/api/v1/endpoints/telegram.py", line XXX
```

### Error 3: Trade Model (500)
```
AttributeError: type object 'Trade' has no attribute 'amount'
File "/app/api/v1/endpoints/admin.py", line XXX
```

## Using Render CLI (Optional)
If you want to install Render CLI for future use:
```bash
# Install Render CLI
curl -sSL https://render.com/install.sh | bash

# Login
render login

# Tail logs
render logs --tail --service cryptouniverse
```

## API Access (With API Key)
1. Get API key from: https://dashboard.render.com/account/api-keys
2. Set environment variable: `export RENDER_API_KEY=your_key_here`
3. Use the fetch_render_logs.sh script we created

## Common Log Filters
- **Errors only**: Search for "ERROR" or "500"
- **Startup issues**: Search for "Starting" or "Uvicorn"
- **Database**: Search for "postgresql" or "database"
- **Recent**: Use time filter for last 1 hour

Once you can see the logs, share any error tracebacks and I'll create precise fixes for each issue.