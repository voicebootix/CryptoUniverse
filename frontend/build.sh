#!/bin/bash

# Production build script for CryptoUniverse Frontend on Render

set -e

echo "🚀 Building CryptoUniverse Frontend for Production..."

# Set Node.js environment
export NODE_ENV=production

# Install dependencies
echo "📦 Installing dependencies..."
npm ci --production=false

# Type check
echo "🔍 Running type checks..."
npm run type-check

# Lint check
echo "🧹 Running linter..."
npm run lint

# Build the application
echo "🏗️ Building application..."
npm run build

# Verify build output
echo "✅ Verifying build output..."
if [ ! -d "dist" ]; then
    echo "❌ Build failed: dist directory not found"
    exit 1
fi

if [ ! -f "dist/index.html" ]; then
    echo "❌ Build failed: index.html not found"
    exit 1
fi

# Calculate build size
BUILD_SIZE=$(du -sh dist | cut -f1)
echo "📊 Build size: $BUILD_SIZE"

# List build assets
echo "📁 Build assets:"
find dist -type f -name "*.js" -o -name "*.css" | head -10

echo "🎉 Frontend build completed successfully!"
echo "📦 Output directory: ./dist"
echo "🌐 Ready for static site deployment!"

# Optional: Run preview server for testing
if [ "$RUN_PREVIEW" = "true" ]; then
    echo "🔍 Starting preview server..."
    npm run preview
fi
