#!/bin/sh

# Frontend Docker entrypoint script for CryptoUniverse Enterprise

set -e

echo "🚀 Starting CryptoUniverse Frontend Service..."

# Function to wait for backend service
wait_for_backend() {
    echo "⏳ Waiting for backend service to be ready..."
    
    # Use explicit BACKEND_HOST or fallback
    if [ "${VITE_API_URL:0:1}" = "/" ]; then
        # Using relative API URL, get host from environment
        BACKEND_HOST=${BACKEND_HOST:-localhost:8000}
    else
        # Extract host from absolute API URL
        BACKEND_HOST=${VITE_API_URL#http://}
        BACKEND_HOST=${BACKEND_HOST#https://}
        BACKEND_HOST=${BACKEND_HOST%%/*}
    fi
    BACKEND_PORT=${BACKEND_HOST##*:}
    BACKEND_HOST=${BACKEND_HOST%:*}
    
    # Default port if not specified
    if [ "$BACKEND_PORT" = "$BACKEND_HOST" ]; then
        BACKEND_PORT=8000
    fi
    
    # Wait for backend to be available
    timeout=60
    while [ $timeout -gt 0 ]; do
        if nc -z "$BACKEND_HOST" "$BACKEND_PORT" 2>/dev/null; then
            echo "✅ Backend service is ready!"
            break
        fi
        
        echo "⏳ Backend not ready yet, waiting... ($timeout seconds remaining)"
        sleep 2
        timeout=$((timeout - 2))
    done
    
    if [ $timeout -le 0 ]; then
        echo "❌ Backend service failed to start within timeout"
        exit 1
    fi
}

# Function to replace environment variables in built files
replace_env_vars() {
    echo "🔧 Configuring environment variables..."
    
    # Find all JS files in the build output
    find /usr/share/nginx/html -name "*.js" -type f -exec sed -i "s|__VITE_API_URL__|${VITE_API_URL:-http://localhost:8000/api/v1}|g" {} \;
    find /usr/share/nginx/html -name "*.js" -type f -exec sed -i "s|__VITE_WS_URL__|${VITE_WS_URL:-ws://localhost:8000/ws}|g" {} \;
    find /usr/share/nginx/html -name "*.js" -type f -exec sed -i "s|__VITE_APP_NAME__|${VITE_APP_NAME:-CryptoUniverse Enterprise}|g" {} \;
    find /usr/share/nginx/html -name "*.js" -type f -exec sed -i "s|__VITE_APP_VERSION__|${VITE_APP_VERSION:-2.0.0}|g" {} \;
    
    echo "✅ Environment variables configured"
}

# Function to validate nginx configuration
validate_nginx_config() {
    echo "🔍 Validating nginx configuration..."
    
    if nginx -t; then
        echo "✅ Nginx configuration is valid"
    else
        echo "❌ Nginx configuration is invalid"
        exit 1
    fi
}

# Function to setup logging
setup_logging() {
    echo "📝 Setting up logging..."
    
    # Create log directory
    mkdir -p /var/log/nginx
    
    # Link nginx logs to stdout/stderr for Docker
    ln -sf /dev/stdout /var/log/nginx/access.log
    ln -sf /dev/stderr /var/log/nginx/error.log
    
    echo "✅ Logging configured"
}

# Function to optimize for production
optimize_for_production() {
    if [ "$NODE_ENV" = "production" ]; then
        echo "🚀 Applying production optimizations..."
        
        # Set nginx worker processes based on CPU cores
        WORKER_PROCESSES=$(nproc)
        sed -i "s/worker_processes auto;/worker_processes $WORKER_PROCESSES;/" /etc/nginx/nginx.conf
        
        # Enable additional optimizations
        echo "worker_rlimit_nofile 65535;" >> /etc/nginx/nginx.conf
        
        echo "✅ Production optimizations applied"
    fi
}

# Function to create health check endpoint
create_health_check() {
    echo "❤️ Setting up health check..."
    
    # Create a simple health check file
    cat > /usr/share/nginx/html/health.json << EOF
{
    "status": "healthy",
    "service": "cryptouniverse-frontend",
    "version": "${VITE_APP_VERSION:-2.0.0}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    echo "✅ Health check endpoint created"
}

# Main execution
main() {
    echo "🌟 CryptoUniverse Enterprise Frontend Service"
    echo "==============================================="
    
    # Wait for dependencies
    if [ "${WAIT_FOR_BACKEND:-true}" = "true" ]; then
        wait_for_backend
    fi
    
    # Configure the application
    replace_env_vars
    setup_logging
    validate_nginx_config
    optimize_for_production
    create_health_check
    
    echo "🎉 Frontend service ready!"
    echo "📡 API URL: ${VITE_API_URL:-http://localhost:8000/api/v1}"
    echo "🔌 WebSocket URL: ${VITE_WS_URL:-ws://localhost:8000/ws}"
    echo "🌐 Frontend URL: http://localhost:3000"
    echo "==============================================="
    
    # Execute the main command
    exec "$@"
}

# Handle signals gracefully
trap 'echo "🛑 Shutting down frontend service..."; exit 0' TERM INT

# Run main function
main "$@"
