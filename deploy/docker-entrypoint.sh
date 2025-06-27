#!/bin/bash
set -e

# Function to run as web user (only if we're not already web user)
run_as_web() {
    if [ "$(id -u)" = "1000" ]; then
        # We're already running as web user
        eval "$1"
    else
        # Switch to web user
        su - web -c "$1"
    fi
}

# Wait for the fco database to be ready
echo "Waiting for fco database to be ready..."
max_retries=30
retries=0
while [ $retries -lt $max_retries ]; do
    if PGPASSWORD=fco2025_x psql -h db -U web -d fco -c "SELECT 1" > /dev/null 2>&1; then
        echo "Database fco is ready!"
        break
    fi
    retries=$((retries+1))
    echo "Database fco not ready yet, retrying... ($retries/$max_retries)"
    sleep 2
done

if [ $retries -eq $max_retries ]; then
    echo "Error: Maximum retries reached. Database fco is not available."
    echo "Checking database container status..."
    docker ps | grep db
    echo "Checking database logs..."
    docker logs db
    exit 1
fi

# Run database migrations if needed
echo "Running database migrations..."
run_as_web "cd /opt/fair3r_custom_overlay && FAIR3R_CUSTOM_OVERLAY_CONTEXT=$FAIR3R_CUSTOM_OVERLAY_CONTEXT DB_IP=db /opt/env3/fair3r_custom_overlay/bin/alembic upgrade head"

# Handle Nginx configuration based on environment
if [ "$FAIR3R_CUSTOM_OVERLAY_CONTEXT" = "demo" ] || [ "$FAIR3R_CUSTOM_OVERLAY_CONTEXT" = "prod" ]; then
    echo "Setting up Nginx with HTTPS for $FAIR3R_CUSTOM_OVERLAY_CONTEXT environment..."
    
    # Generate SSL certificate
    echo "Generating SSL certificate..."
    /opt/fair3r_custom_overlay/deploy/generate_ssl_cert.sh
    
    # Copy appropriate Nginx configuration
    if [ "$FAIR3R_CUSTOM_OVERLAY_CONTEXT" = "demo" ]; then
        cp /opt/fair3r_custom_overlay/deploy/nginx_demo /etc/nginx/sites-available/default
    else
        cp /opt/fair3r_custom_overlay/deploy/nginx_prod /etc/nginx/sites-available/default
    fi
    
    # Test Nginx configuration
    nginx -t
    
    # Start Nginx in background
    echo "Starting Nginx..."
    nginx -g "daemon off;" &
    
    # Start Gunicorn for production/demo
    echo "Starting Gunicorn production server..."
    exec /opt/env3/fair3r_custom_overlay/bin/gunicorn --bind 127.0.0.1:8080 --workers 4 --worker-class sync --log-level=info --capture-output --enable-stdio-inheritance fair3r_custom_overlay_app:app
else
    # For dev and test environments, use simple Nginx or no Nginx
    if [ "$FAIR3R_CUSTOM_OVERLAY_CONTEXT" = "dev" ]; then
        echo "Starting Flask development server with hot reloading..."
        # Use Flask development server for hot reloading in dev mode
        exec /opt/env3/fair3r_custom_overlay/bin/python fair3r_custom_overlay_app.py
    else
        echo "Starting Gunicorn test server..."
        # Use Gunicorn for test mode (no Nginx)
        exec /opt/env3/fair3r_custom_overlay/bin/gunicorn --bind 0.0.0.0:8080 --log-level=debug --capture-output --enable-stdio-inheritance fair3r_custom_overlay_app:app
    fi
fi
