#!/usr/bin/env bash
# Render build script - ensures clean Python deployment
set -e

echo "🧹 Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

echo "📦 Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "🔍 Verifying critical files..."
DISCOVERY_FILE="app/services/user_opportunity_discovery.py"
if [ -f "$DISCOVERY_FILE" ]; then
    LINE_COUNT=$(wc -l < "$DISCOVERY_FILE")
    echo "✅ $DISCOVERY_FILE exists ($LINE_COUNT lines)"

    # Verify critical methods exist
    if grep -q "_scan_funding_arbitrage_pro_opportunities" "$DISCOVERY_FILE"; then
        echo "✅ Pro strategy methods found"
    else
        echo "❌ ERROR: Pro strategy methods missing!"
        exit 1
    fi
else
    echo "❌ ERROR: $DISCOVERY_FILE not found!"
    exit 1
fi

echo "🔧 Running database migrations..."
alembic upgrade head || echo "⚠️  Migration failed or already up to date"

echo "✅ Build complete!"
