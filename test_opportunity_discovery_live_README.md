# Live Opportunity Discovery Test

This script tests the opportunity discovery system on the live deployment at `cryptouniverse.onrender.com`.

## Security

**No hardcoded credentials** - The script reads credentials from environment variables to prevent accidental exposure of sensitive information.

## Setup

1. Set the required environment variables:
   ```bash
   export TEST_ADMIN_EMAIL="admin@cryptouniverse.com"
   export TEST_ADMIN_PASSWORD="AdminPass123!"
   ```

2. Run the test:
   ```bash
   # Option 1: Using python3
   python3 test_opportunity_discovery_live.py
   
   # Option 2: Direct execution (script is executable)
   ./test_opportunity_discovery_live.py
   ```

## What the Test Does

1. **Login Test**: Verifies authentication works
2. **Portfolio Test**: Checks if user has active strategies
3. **Opportunity Discovery**: Tests the `/opportunities/discover` endpoint
4. **Chat Integration**: Tests the chat system's opportunity discovery
5. **Admin Access**: Verifies admin strategy access

## Expected Results

- ✅ Login should succeed
- ✅ Opportunity discovery should return 200 status
- ✅ Chat should respond with sophisticated AI analysis
- ⚠️ May find 0 opportunities due to technical issues (asyncio.timeout fix needed)

## Troubleshooting

If you get "Missing required environment variables" error, make sure you've set both `TEST_ADMIN_EMAIL` and `TEST_ADMIN_PASSWORD` environment variables.

If opportunities are 0, this indicates the strategy scanning system needs the asyncio.timeout compatibility fix.